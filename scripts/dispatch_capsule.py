# -*- coding: utf-8 -*-
"""Create and verify short-lived, content-addressed dispatch capsules.

This host-only tool reads Git and ordinary files.  It never invokes devices,
network clients, package managers, Git writes, or the provenance campaign.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence


SCHEMA_VERSION = 2
CONTINUATION_SCHEMA_VERSION = 3
SCOPED_CONTINUATION_SCHEMA_VERSION = 4
VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION = 5
INVARIANT_SCOPE_VERSION = 1
VERIFIER_OWNED_INVARIANT_SCOPE_VERSION = 2
CAPSULE_TYPE = "tc-runner.dispatch-entry"
TTL_SECONDS = 1800
CAPSULE_ROOT = Path(r"C:\tmp\tc-runner-dispatch-capsules")
GENERATOR_PATH = Path("scripts/dispatch_capsule.py")
UPSTREAM_REF = "origin/master"
LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LOWER_OID_RE = re.compile(r"^[0-9a-f]{40}$")
DIRECTIVE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MODULE_ROOT_KEYS = {
    "entry_bytes",
    "entry_relpath",
    "entry_sha256",
    "package_name",
    "package_version",
    "root_path",
}


class InputInvalid(ValueError):
    """The requested capsule cannot authorize execution."""


class InfrastructureFailure(RuntimeError):
    """A required Git, filesystem, clock, or hashing operation failed."""


def canonical_json_bytes(value: object) -> bytes:
    """Return the sole accepted capsule JSON representation."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_lower_sha256(value: object) -> bool:
    return isinstance(value, str) and LOWER_SHA256_RE.fullmatch(value) is not None


def _is_lower_oid(value: object) -> bool:
    return isinstance(value, str) and LOWER_OID_RE.fullmatch(value) is not None


def _is_non_bool_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_linklike(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        if hasattr(path, "is_junction") and path.is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(
            attributes
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError as exc:
        raise InfrastructureFailure(f"path stat failed: {path}") from exc


def _reject_linklike_path_chain(path: Path, *, label: str) -> None:
    """Reject any existing lexical path component that is a link/reparse point."""

    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    if not parts:
        raise InputInvalid(f"{label} path is invalid")
    current = Path(parts[0])
    candidates = [current]
    for part in parts[1:]:
        current /= part
        candidates.append(current)
    for candidate in candidates:
        if os.path.lexists(candidate) and _is_linklike(candidate):
            raise InputInvalid(f"{label} path chain is unsafe")


def _require_directory(path: Path, *, label: str) -> Path:
    _reject_linklike_path_chain(path, label=label)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise InfrastructureFailure(f"{label} could not be resolved") from exc
    if not resolved.is_dir() or _is_linklike(resolved):
        raise InputInvalid(f"{label} is not an ordinary directory")
    return resolved


def _relative_path(value: Path, *, label: str) -> str:
    raw = value.as_posix()
    pure = PurePosixPath(raw)
    if (
        not raw
        or value.is_absolute()
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or "\\" in raw
        or "\n" in raw
        or "\r" in raw
    ):
        raise InputInvalid(f"{label} must be an exact repo-relative path")
    return raw


def _normalize_invariant_scope(
    exact_paths: Sequence[Path],
    prefixes: Sequence[Path],
    verifier_owned_ignored_prefixes: Sequence[Path] | None = None,
) -> dict[str, Any]:
    normalized_exact = [
        _relative_path(path, label="invariant path")
        for path in exact_paths
    ]
    normalized_prefixes = [
        f"{_relative_path(path, label='invariant prefix')}/"
        for path in prefixes
    ]
    normalized_owned_prefixes = (
        [
            f"{_relative_path(path, label='verifier-owned ignored prefix')}/"
            for path in verifier_owned_ignored_prefixes
        ]
        if verifier_owned_ignored_prefixes is not None
        else []
    )
    if not normalized_exact and not normalized_prefixes:
        raise InputInvalid("invariant scope selectors are empty")
    if (
        verifier_owned_ignored_prefixes is not None
        and not normalized_owned_prefixes
    ):
        raise InputInvalid("verifier-owned ignored prefixes are empty")
    if len(normalized_exact) != len(set(normalized_exact)):
        raise InputInvalid("invariant paths contain duplicates")
    if len(normalized_prefixes) != len(set(normalized_prefixes)):
        raise InputInvalid("invariant prefixes contain duplicates")
    if len(normalized_owned_prefixes) != len(set(normalized_owned_prefixes)):
        raise InputInvalid("verifier-owned ignored prefixes contain duplicates")
    normalized_exact.sort(key=lambda value: value.encode("utf-8"))
    normalized_prefixes.sort(key=lambda value: value.encode("utf-8"))
    normalized_owned_prefixes.sort(key=lambda value: value.encode("utf-8"))
    for index, prefix in enumerate(normalized_prefixes):
        if any(
            other != prefix and prefix.startswith(other)
            for other in normalized_prefixes[:index]
        ):
            raise InputInvalid("invariant prefixes overlap")
    if any(
        exact.startswith(prefix)
        for exact in normalized_exact
        for prefix in normalized_prefixes
    ):
        raise InputInvalid("invariant path is redundant with prefix")
    for index, prefix in enumerate(normalized_owned_prefixes):
        if any(
            other != prefix and prefix.startswith(other)
            for other in normalized_owned_prefixes[:index]
        ):
            raise InputInvalid("verifier-owned ignored prefixes overlap")
    if any(
        owned.startswith(prefix) or prefix.startswith(owned)
        for owned in normalized_owned_prefixes
        for prefix in normalized_prefixes
    ):
        raise InputInvalid("verifier-owned ignored prefix overlaps invariant prefix")
    if any(
        exact.startswith(owned) or owned.startswith(f"{exact}/")
        for exact in normalized_exact
        for owned in normalized_owned_prefixes
    ):
        raise InputInvalid("verifier-owned ignored prefix overlaps invariant path")
    payload = {
        "exact_paths": normalized_exact,
        "prefixes": normalized_prefixes,
        "scope_version": (
            VERIFIER_OWNED_INVARIANT_SCOPE_VERSION
            if verifier_owned_ignored_prefixes is not None
            else INVARIANT_SCOPE_VERSION
        ),
    }
    if verifier_owned_ignored_prefixes is not None:
        payload["verifier_owned_ignored_prefixes"] = normalized_owned_prefixes
    return {
        **payload,
        "canonical_json_sha256": _sha256_bytes(
            canonical_json_bytes(payload)
        ),
    }


def _path_is_in_invariant_scope(
    relative: str,
    scope: dict[str, Any],
) -> bool:
    return relative in scope["exact_paths"] or any(
        relative.startswith(prefix) for prefix in scope["prefixes"]
    )


def _path_is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_capsule_root(
    repo: Path,
    capsule_root: Path,
    *,
    require_exists: bool,
) -> Path:
    lexical = Path(os.path.abspath(capsule_root))
    _reject_linklike_path_chain(lexical, label="capsule root")
    repo_resolved = repo.resolve(strict=True)
    if _path_is_within(lexical, repo_resolved):
        raise InputInvalid("capsule root must be outside repository")
    if lexical.exists():
        resolved = lexical.resolve(strict=True)
        if _path_is_within(resolved, repo_resolved):
            raise InputInvalid("capsule root resolves inside repository")
        if not resolved.is_dir() or _is_linklike(lexical):
            raise InputInvalid("capsule root is not an ordinary directory")
        return resolved
    if require_exists:
        raise InputInvalid("capsule root does not exist")
    parent = lexical.parent
    try:
        parent_resolved = parent.resolve(strict=True)
    except OSError as exc:
        raise InfrastructureFailure(
            "capsule root parent could not be resolved"
        ) from exc
    if (
        not parent_resolved.is_dir()
        or _is_linklike(parent_resolved)
        or _path_is_within(parent_resolved, repo_resolved)
    ):
        raise InputInvalid("capsule root parent is unsafe")
    return lexical


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_SYSTEM"] = os.devnull
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _run_git(
    repo: Path,
    *args: str,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-c", f"core.excludesFile={os.devnull}", *args],
            cwd=repo,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=_git_environment(),
        )
    except OSError as exc:
        raise InfrastructureFailure(
            f"git could not start: {' '.join(args)}"
        ) from exc


def _git(
    repo: Path,
    *args: str,
    input_bytes: bytes | None = None,
) -> bytes:
    process = _run_git(repo, *args, input_bytes=input_bytes)
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"git {' '.join(args)} exit {process.returncode}: {message}"
        )
    if process.stderr:
        message = process.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"git {' '.join(args)} emitted stderr: {message}"
        )
    return process.stdout


def _git_quiet(repo: Path, *args: str) -> bool:
    process = _run_git(repo, *args)
    if process.returncode not in (0, 1):
        message = process.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"git {' '.join(args)} exit {process.returncode}: {message}"
        )
    if process.stderr:
        message = process.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"git {' '.join(args)} emitted stderr: {message}"
        )
    return process.returncode == 0


def _git_text(repo: Path, *args: str) -> str:
    try:
        return _git(repo, *args).decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise InfrastructureFailure(
            f"git {' '.join(args)} emitted non-UTF-8"
        ) from exc


def measure_index(repo: Path) -> dict[str, int | str]:
    raw = _git(
        repo,
        "-c",
        "core.quotepath=false",
        "ls-files",
        "--stage",
        "-z",
    )
    entries = [entry for entry in raw.split(b"\0") if entry]
    return {
        "entry_count": len(entries),
        "raw_stage_z_sha256": _sha256_bytes(raw),
    }


def _ordinary_repo_file(repo: Path, relative: str) -> Path:
    candidate = repo / Path(relative)
    try:
        lexical = Path(os.path.abspath(candidate))
        lexical.relative_to(repo)
    except ValueError as exc:
        raise InputInvalid(f"path escapes repository: {relative}") from exc
    try:
        if (
            not lexical.is_file()
            or lexical.is_dir()
            or _is_linklike(lexical)
        ):
            raise InputInvalid(f"path is not an ordinary file: {relative}")
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise InfrastructureFailure(f"path read failed: {relative}") from exc
    if os.path.normcase(str(resolved)) != os.path.normcase(str(lexical)):
        raise InputInvalid(f"path resolves elsewhere: {relative}")
    return lexical


def measure_path_map(
    repo: Path,
    *,
    ignored: bool,
    invariant_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    args = [
        "-c",
        "core.quotepath=false",
        "ls-files",
        "--others",
    ]
    if ignored:
        args.append("--ignored")
    args.extend(["--exclude-standard", "-z"])
    raw = _git(repo, *args)
    paths: list[str] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            relative = item.decode("utf-8", "strict").replace("\\", "/")
        except UnicodeDecodeError as exc:
            raise InfrastructureFailure(
                "Git path list contains non-UTF-8 bytes"
            ) from exc
        _relative_path(Path(relative), label="Git path")
        paths.append(relative)
    if len(paths) != len(set(paths)):
        raise InputInvalid("Git path map contains duplicate paths")
    if (
        ignored
        and invariant_scope is not None
        and invariant_scope.get("scope_version")
        == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION
    ):
        owned_prefixes = invariant_scope[
            "verifier_owned_ignored_prefixes"
        ]
        paths = [
            path
            for path in paths
            if not any(path.startswith(prefix) for prefix in owned_prefixes)
        ]
    selected_paths = (
        paths
        if invariant_scope is None
        else [
            path
            for path in paths
            if _path_is_in_invariant_scope(path, invariant_scope)
        ]
    )
    for relative in selected_paths:
        _ordinary_repo_file(repo, relative)
    hash_input = "".join(
        f"{path}\n" for path in selected_paths
    ).encode("utf-8")
    hashes_raw = _git(
        repo,
        "hash-object",
        "--no-filters",
        "--stdin-paths",
        input_bytes=hash_input,
    )
    try:
        hashes = hashes_raw.decode("ascii", "strict").splitlines()
    except UnicodeDecodeError as exc:
        raise InfrastructureFailure(
            "git hash-object emitted non-ASCII"
        ) from exc
    if len(hashes) != len(selected_paths):
        raise InfrastructureFailure("path/hash cardinality mismatch")
    rows = [
        {
            "file_type": "file",
            "git_hash_object_no_filters": digest,
            "path": relative,
        }
        for relative, digest in zip(selected_paths, hashes, strict=True)
    ]
    if any(LOWER_OID_RE.fullmatch(row["git_hash_object_no_filters"]) is None
           for row in rows):
        raise InfrastructureFailure("git hash-object emitted invalid object id")
    rows.sort(key=lambda row: row["path"].encode("utf-8"))
    result = {
        "count": len(rows),
        "canonical_json_sha256": _sha256_bytes(
            canonical_json_bytes(rows)
        ),
        "rows": rows,
    }
    if invariant_scope is not None:
        result["excluded_count"] = len(paths) - len(selected_paths)
    return result


def _file_identity(
    repo: Path,
    relative_path: Path,
    *,
    label: str,
    expected_raw_sha256: str | None = None,
    allow_worktree_dirty: bool = False,
) -> dict[str, str]:
    relative = _relative_path(relative_path, label=label)
    if (
        expected_raw_sha256 is not None
        and LOWER_SHA256_RE.fullmatch(expected_raw_sha256) is None
    ):
        raise InputInvalid(
            f"{label} expected SHA-256 must be lowercase SHA-256"
        )
    tracked = _run_git(
        repo, "ls-files", "--error-unmatch", "--", relative
    )
    if tracked.returncode == 1:
        if expected_raw_sha256 is None:
            raise InputInvalid(f"{label} is not tracked: {relative}")
        untracked = _git(
            repo,
            "-c",
            "core.quotepath=false",
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            relative,
        )
        if untracked != relative.encode("utf-8") + b"\0":
            raise InputInvalid(
                f"{label} is not an unignored untracked file: {relative}"
            )
    elif tracked.returncode != 0:
        message = tracked.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"{label} tracking check failed: {message}"
        )
    if tracked.returncode == 0 and tracked.stderr:
        message = tracked.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"{label} tracking check emitted stderr: {message}"
        )
    path = _ordinary_repo_file(repo, relative)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InfrastructureFailure(f"{label} could not be read") from exc
    raw_sha256 = _sha256_bytes(raw)
    if (
        expected_raw_sha256 is not None
        and raw_sha256 != expected_raw_sha256
    ):
        raise InputInvalid(f"{label} SHA-256 mismatch")
    blob = _git_text(
        repo,
        "hash-object",
        "--no-filters",
        "--",
        relative,
    )
    if LOWER_OID_RE.fullmatch(blob) is None:
        raise InfrastructureFailure(f"{label} Git blob is invalid")
    if tracked.returncode == 0 and not allow_worktree_dirty:
        head_blob = _git_text(repo, "rev-parse", f"HEAD:{relative}")
        if blob != head_blob:
            raise InputInvalid(f"{label} worktree bytes differ from HEAD")
    return {
        "path": relative,
        "raw_sha256": raw_sha256,
        "git_blob_no_filters": blob,
    }


def _plain_token(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and "\\" not in value
        and "\n" not in value
        and "\r" not in value
        and not any(character.isspace() for character in value)
    )


def _ordinary_external_file(path: Path, *, label: str) -> Path:
    _reject_linklike_path_chain(path, label=label)
    if not path.is_file() or path.is_dir() or _is_linklike(path):
        raise InputInvalid(f"{label} is not an ordinary file")
    return path


def measure_module_root(
    repo: Path,
    root: Path,
    package_name: str,
) -> dict[str, Any]:
    if not _plain_token(package_name):
        raise InputInvalid("module package name is invalid")
    lexical = Path(os.path.abspath(root))
    _reject_linklike_path_chain(lexical, label="module root")
    repo_resolved = repo.resolve(strict=True)
    if _path_is_within(lexical, repo_resolved):
        raise InputInvalid("module root must be outside repository")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise InputInvalid("module root does not exist") from exc
    if _path_is_within(resolved, repo_resolved):
        raise InputInvalid("module root resolves inside repository")
    if not resolved.is_dir() or _is_linklike(lexical):
        raise InputInvalid("module root is not an ordinary directory")
    package_dir = resolved
    for part in package_name.split("/"):
        if part in {"", ".", ".."}:
            raise InputInvalid("module package name is invalid")
        package_dir = package_dir / part
    if not package_dir.is_dir() or _is_linklike(package_dir):
        raise InputInvalid("module package directory is not ordinary")
    manifest_path = _ordinary_external_file(
        package_dir / "package.json", label="module package.json"
    )
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise InfrastructureFailure(
            "module package.json could not be read"
        ) from exc
    try:
        manifest = json.loads(
            manifest_raw.decode("utf-8", "strict"),
            object_pairs_hook=_object_without_duplicates,
        )
    except InputInvalid:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputInvalid("module package.json is invalid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("name") != package_name:
        raise InputInvalid("module package name mismatch")
    version = manifest.get("version")
    if not _plain_token(version):
        raise InputInvalid("module package version is invalid")
    exports = manifest.get("exports")
    entry_export = exports.get(".") if isinstance(exports, dict) else None
    if (
        not isinstance(entry_export, str)
        or not entry_export.startswith("./")
        or len(entry_export) <= 2
    ):
        raise InputInvalid("module exports entry is unsupported")
    entry_relpath = _relative_path(
        Path(entry_export[2:]), label="module entry"
    )
    entry_path = _ordinary_external_file(
        package_dir / Path(entry_relpath), label="module entry"
    )
    try:
        entry_raw = entry_path.read_bytes()
    except OSError as exc:
        raise InfrastructureFailure("module entry could not be read") from exc
    if not entry_raw:
        raise InputInvalid("module entry is empty")
    return {
        "entry_bytes": len(entry_raw),
        "entry_relpath": entry_relpath,
        "entry_sha256": _sha256_bytes(entry_raw),
        "package_name": package_name,
        "package_version": version,
        "root_path": resolved.as_posix(),
    }


def _measure_module_specs(
    repo: Path,
    module_specs: Sequence[tuple[Path, str]],
) -> list[dict[str, Any]]:
    return [
        measure_module_root(repo, root, package_name)
        for root, package_name in module_specs
    ]


def measure_tracked_worktree(
    repo: Path,
    allowed_dirty_paths: Sequence[Path],
) -> dict[str, Any]:
    """Bind an exact unstaged tracked-file set and its current bytes."""

    normalized = [
        _relative_path(path, label="allowed dirty path")
        for path in allowed_dirty_paths
    ]
    if len(normalized) != len(set(normalized)):
        raise InputInvalid("allowed dirty paths contain duplicates")
    normalized.sort(key=lambda value: value.encode("utf-8"))
    raw = _git(
        repo,
        "-c",
        "core.quotepath=false",
        "diff-index",
        "--name-only",
        "-z",
        "HEAD",
        "--",
    )
    actual: list[str] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            relative = item.decode("utf-8", "strict").replace("\\", "/")
        except UnicodeDecodeError as exc:
            raise InfrastructureFailure(
                "tracked dirty path contains non-UTF-8 bytes"
            ) from exc
        _relative_path(Path(relative), label="tracked dirty path")
        actual.append(relative)
    actual.sort(key=lambda value: value.encode("utf-8"))
    if actual != normalized:
        raise InputInvalid("tracked dirty path set differs from authorization")
    rows: list[dict[str, str]] = []
    for relative in actual:
        tracked = _run_git(
            repo, "ls-files", "--error-unmatch", "--", relative
        )
        if tracked.returncode != 0 or tracked.stderr:
            raise InputInvalid(f"allowed dirty path is not tracked: {relative}")
        path = _ordinary_repo_file(repo, relative)
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise InfrastructureFailure(
                f"allowed dirty path could not be read: {relative}"
            ) from exc
        blob = _git_text(
            repo,
            "hash-object",
            "--no-filters",
            "--",
            relative,
        )
        if LOWER_OID_RE.fullmatch(blob) is None:
            raise InfrastructureFailure(
                f"allowed dirty path Git blob is invalid: {relative}"
            )
        rows.append(
            {
                "git_blob_no_filters": blob,
                "path": relative,
                "raw_sha256": _sha256_bytes(content),
            }
        )
    return {
        "count": len(rows),
        "canonical_json_sha256": _sha256_bytes(canonical_json_bytes(rows)),
        "rows": rows,
    }


def measure_repo_state(
    repo: Path,
    *,
    directive_path: Path,
    spec_path: Path,
    generator_path: Path,
    directive_sha256: str | None = None,
    spec_sha256: str | None = None,
    allowed_dirty_paths: Sequence[Path] | None = None,
    invariant_scope: dict[str, Any] | None = None,
    upstream_ref: str = UPSTREAM_REF,
) -> dict[str, Any]:
    repo = _require_directory(repo, label="repository")
    if upstream_ref != UPSTREAM_REF:
        raise InputInvalid(f"upstream ref must be {UPSTREAM_REF}")
    head = _git_text(repo, "rev-parse", "--verify", "HEAD")
    upstream = _git_text(repo, "rev-parse", "--verify", upstream_ref)
    if (
        LOWER_OID_RE.fullmatch(head) is None
        or LOWER_OID_RE.fullmatch(upstream) is None
    ):
        raise InfrastructureFailure("Git revision is not a full object id")
    counts = _git_text(
        repo,
        "rev-list",
        "--left-right",
        "--count",
        f"{upstream_ref}...HEAD",
    ).split()
    if len(counts) != 2 or any(not value.isdigit() for value in counts):
        raise InfrastructureFailure("ahead/behind output is invalid")
    behind, ahead = (int(value) for value in counts)
    index = measure_index(repo)
    tracked_worktree = (
        measure_tracked_worktree(repo, allowed_dirty_paths)
        if allowed_dirty_paths is not None
        else {"count": 0, "canonical_json_sha256": _sha256_bytes(b"[]"), "rows": []}
    )
    untracked = measure_path_map(
        repo,
        ignored=False,
        invariant_scope=invariant_scope,
    )
    ignored = measure_path_map(
        repo,
        ignored=True,
        invariant_scope=invariant_scope,
    )
    if invariant_scope is not None:
        selected = {
            row["path"] for row in untracked["rows"] + ignored["rows"]
        }
        for exact in invariant_scope["exact_paths"]:
            if exact not in selected:
                raise InputInvalid(
                    f"invariant path matches no untracked/ignored file: {exact}"
                )
        for prefix in invariant_scope["prefixes"]:
            if not any(path.startswith(prefix) for path in selected):
                raise InputInvalid(
                    f"invariant prefix matches no untracked/ignored file: {prefix}"
                )
    state = {
        "repo": {
            "root": repo.as_posix(),
            "upstream_ref": upstream_ref,
            "head_sha": head,
            "upstream_sha": upstream,
            "ahead": ahead,
            "behind": behind,
            "tracked_clean": _git_quiet(repo, "diff", "--quiet"),
            "staged_clean": _git_quiet(
                repo, "diff", "--cached", "--quiet"
            ),
        },
        "index": index,
        "untracked": (
            {
                "count": untracked["count"],
                "canonical_json_sha256":
                    untracked["canonical_json_sha256"],
                "excluded_count": untracked["excluded_count"],
            }
            if invariant_scope is not None
            else {
                "count": untracked["count"],
                "canonical_json_sha256":
                    untracked["canonical_json_sha256"],
                "excluded_paths": [],
            }
        ),
        "ignored": (
            {
                "count": ignored["count"],
                "canonical_json_sha256":
                    ignored["canonical_json_sha256"],
                "excluded_count": ignored["excluded_count"],
            }
            if invariant_scope is not None
            else {
                "count": ignored["count"],
                "canonical_json_sha256":
                    ignored["canonical_json_sha256"],
                "excluded_paths": [],
            }
        ),
        "identities": {
            "directive": _file_identity(
                repo,
                directive_path,
                label="directive",
                expected_raw_sha256=directive_sha256,
            ),
            "spec": _file_identity(
                repo,
                spec_path,
                label="spec",
                expected_raw_sha256=spec_sha256,
            ),
            "generator": _file_identity(
                repo,
                generator_path,
                label="generator",
                allow_worktree_dirty=(
                    _relative_path(generator_path, label="generator")
                    in {
                        _relative_path(path, label="allowed dirty path")
                        for path in (allowed_dirty_paths or ())
                    }
                ),
            ),
        },
    }
    if tracked_worktree["count"]:
        state["tracked_worktree"] = tracked_worktree
    if invariant_scope is not None:
        state["invariant_scope"] = invariant_scope
    return state


def _require_dispatchable(state: dict[str, Any]) -> None:
    repo = state["repo"]
    continuation = "tracked_worktree" in state
    if (
        repo["head_sha"] != repo["upstream_sha"]
        or repo["ahead"] != 0
        or repo["behind"] != 0
        or repo["staged_clean"] is not True
        or (continuation and repo["tracked_clean"] is not False)
        or (not continuation and repo["tracked_clean"] is not True)
    ):
        raise InputInvalid("repository is not dispatchable")


def _clock_value(now_fn: Callable[[], int]) -> int:
    try:
        value = now_fn()
    except Exception as exc:
        raise InfrastructureFailure("clock read failed") from exc
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InfrastructureFailure("clock returned invalid epoch seconds")
    return value


def _capsule_payload(
    directive_id: str,
    state: dict[str, Any],
    module_roots: list[dict[str, Any]],
    issued_at: int,
) -> dict[str, Any]:
    continuation = "tracked_worktree" in state
    scoped = "invariant_scope" in state
    payload = {
        "capsule_type": CAPSULE_TYPE,
        "directive_id": directive_id,
        "expires_at_epoch_s": issued_at + TTL_SECONDS,
        "identities": state["identities"],
        "ignored": state["ignored"],
        "index": state["index"],
        "issued_at_epoch_s": issued_at,
        "module_roots": module_roots,
        "repo": state["repo"],
        "schema_version": (
            VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION
            if scoped
            and state["invariant_scope"].get("scope_version")
            == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION
            else SCOPED_CONTINUATION_SCHEMA_VERSION
            if scoped
            else CONTINUATION_SCHEMA_VERSION
            if continuation
            else SCHEMA_VERSION
        ),
        "ttl_seconds": TTL_SECONDS,
        "untracked": state["untracked"],
    }
    if continuation:
        payload["tracked_worktree"] = state["tracked_worktree"]
    if scoped:
        payload["invariant_scope"] = state["invariant_scope"]
    return payload


def _publish_content_addressed(
    root: Path,
    raw: bytes,
    digest: str,
) -> Path:
    _reject_linklike_path_chain(root, label="capsule root")
    try:
        root.mkdir(parents=False, exist_ok=True)
    except OSError as exc:
        raise InfrastructureFailure("capsule root creation failed") from exc
    _reject_linklike_path_chain(root, label="capsule root")
    if not root.is_dir() or _is_linklike(root):
        raise InputInvalid("capsule root is not an ordinary directory")
    final = root / f"{digest}.json"
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=".dispatch-capsule-",
            suffix=".tmp",
            dir=root,
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, final)
        except FileExistsError as exc:
            raise InputInvalid("capsule target already exists") from exc
        except OSError as exc:
            raise InfrastructureFailure("capsule publish failed") from exc
        temporary.unlink()
        temporary = None
        try:
            published = final.read_bytes()
        except OSError as exc:
            raise InfrastructureFailure(
                "published capsule could not be read"
            ) from exc
        if published != raw or _sha256_bytes(published) != digest:
            raise InfrastructureFailure("published capsule verification failed")
        return final
    except Exception:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        # Never unlink a published pathname during exception cleanup.  Another
        # process could have replaced it after link creation; the failed
        # capture never prints or authorizes its digest.
        raise


def capture_capsule(
    *,
    repo: Path,
    capsule_root: Path,
    directive_id: str,
    directive_path: Path,
    spec_path: Path,
    directive_sha256: str | None = None,
    spec_sha256: str | None = None,
    generator_path: Path = GENERATOR_PATH,
    upstream_ref: str = UPSTREAM_REF,
    module_specs: Sequence[tuple[Path, str]] = (),
    allowed_dirty_paths: Sequence[Path] | None = None,
    tracked_worktree_sha256: str | None = None,
    invariant_paths: Sequence[Path] | None = None,
    invariant_prefixes: Sequence[Path] | None = None,
    verifier_owned_ignored_prefixes: Sequence[Path] | None = None,
    invariant_scope_sha256: str | None = None,
    now_fn: Callable[[], int] = lambda: int(time.time()),
) -> tuple[Path, str]:
    if DIRECTIVE_ID_RE.fullmatch(directive_id) is None:
        raise InputInvalid("directive ID is invalid")
    for label, expected_sha256 in (
        ("directive", directive_sha256),
        ("spec", spec_sha256),
    ):
        if (
            expected_sha256 is not None
            and LOWER_SHA256_RE.fullmatch(expected_sha256) is None
        ):
            raise InputInvalid(
                f"{label} expected SHA-256 must be lowercase SHA-256"
            )
    if allowed_dirty_paths is None:
        if tracked_worktree_sha256 is not None:
            raise InputInvalid(
                "tracked worktree expected SHA-256 requires allowed dirty paths"
            )
    elif tracked_worktree_sha256 is None:
        raise InputInvalid(
            "tracked worktree expected SHA-256 is required"
        )
    elif LOWER_SHA256_RE.fullmatch(tracked_worktree_sha256) is None:
        raise InputInvalid(
            "tracked worktree expected SHA-256 must be lowercase SHA-256"
        )
    scope_requested = (
        invariant_paths is not None
        or invariant_prefixes is not None
        or verifier_owned_ignored_prefixes is not None
    )
    invariant_scope: dict[str, Any] | None = None
    if scope_requested:
        if allowed_dirty_paths is None:
            raise InputInvalid(
                "invariant scope requires continuation dirty paths"
            )
        if invariant_scope_sha256 is None:
            raise InputInvalid(
                "invariant scope expected SHA-256 is required"
            )
        if LOWER_SHA256_RE.fullmatch(invariant_scope_sha256) is None:
            raise InputInvalid(
                "invariant scope expected SHA-256 must be lowercase SHA-256"
            )
        invariant_scope = _normalize_invariant_scope(
            invariant_paths or (),
            invariant_prefixes or (),
            verifier_owned_ignored_prefixes,
        )
        if (
            invariant_scope["canonical_json_sha256"]
            != invariant_scope_sha256
        ):
            raise InputInvalid("invariant scope SHA-256 mismatch")
    elif invariant_scope_sha256 is not None:
        raise InputInvalid(
            "invariant scope expected SHA-256 requires selectors"
        )
    repo_resolved = _require_directory(repo, label="repository")
    root = _validate_capsule_root(
        repo_resolved, capsule_root, require_exists=False
    )
    first_modules = _measure_module_specs(repo_resolved, module_specs)
    first = measure_repo_state(
        repo_resolved,
        directive_path=directive_path,
        spec_path=spec_path,
        generator_path=generator_path,
        directive_sha256=directive_sha256,
        spec_sha256=spec_sha256,
        allowed_dirty_paths=allowed_dirty_paths,
        invariant_scope=invariant_scope,
        upstream_ref=upstream_ref,
    )
    _require_dispatchable(first)
    if tracked_worktree_sha256 is not None and (
        first.get("tracked_worktree", {}).get("canonical_json_sha256")
        != tracked_worktree_sha256
    ):
        raise InputInvalid("tracked worktree SHA-256 mismatch")
    second = measure_repo_state(
        repo_resolved,
        directive_path=directive_path,
        spec_path=spec_path,
        generator_path=generator_path,
        directive_sha256=directive_sha256,
        spec_sha256=spec_sha256,
        allowed_dirty_paths=allowed_dirty_paths,
        invariant_scope=invariant_scope,
        upstream_ref=upstream_ref,
    )
    _require_dispatchable(second)
    if canonical_json_bytes(first) != canonical_json_bytes(second):
        raise InputInvalid("repository state changed during capture")
    second_modules = _measure_module_specs(repo_resolved, module_specs)
    if (
        canonical_json_bytes(first_modules)
        != canonical_json_bytes(second_modules)
    ):
        raise InputInvalid("module state changed during capture")
    issued_at = _clock_value(now_fn)
    raw = canonical_json_bytes(
        _capsule_payload(directive_id, second, second_modules, issued_at)
    )
    digest = _sha256_bytes(raw)
    return _publish_content_addressed(root, raw, digest), digest


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputInvalid(f"capsule contains duplicate key: {key}")
        result[key] = value
    return result


def _exact_keys(
    value: object,
    keys: set[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise InputInvalid(f"{label} schema is invalid")
    return value


def _validate_identity(value: object, *, label: str) -> None:
    item = _exact_keys(
        value,
        {"path", "raw_sha256", "git_blob_no_filters"},
        label=label,
    )
    if (
        not isinstance(item["path"], str)
        or not item["path"]
        or not _is_lower_sha256(item["raw_sha256"])
        or not _is_lower_oid(item["git_blob_no_filters"])
    ):
        raise InputInvalid(f"{label} fields are invalid")
    _relative_path(Path(item["path"]), label=f"{label}.path")


def _validate_capsule_schema(
    value: object,
    *,
    expected_directive_id: str,
    expected_directive_path: Path,
    expected_spec_path: Path,
    expected_upstream_ref: str,
    repo: Path,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputInvalid("capsule schema is invalid")
    schema_version = value.get("schema_version")
    continuation_versions = {
        CONTINUATION_SCHEMA_VERSION,
        SCOPED_CONTINUATION_SCHEMA_VERSION,
        VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION,
    }
    scoped_versions = {
        SCOPED_CONTINUATION_SCHEMA_VERSION,
        VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION,
    }
    if schema_version not in {
        SCHEMA_VERSION,
        *continuation_versions,
    }:
        raise InputInvalid("capsule fixed fields are invalid")
    capsule_keys = {
        "capsule_type",
        "directive_id",
        "expires_at_epoch_s",
        "identities",
        "ignored",
        "index",
        "issued_at_epoch_s",
        "module_roots",
        "repo",
        "schema_version",
        "ttl_seconds",
        "untracked",
    }
    if schema_version in continuation_versions:
        capsule_keys.add("tracked_worktree")
    if schema_version in scoped_versions:
        capsule_keys.add("invariant_scope")
    capsule = _exact_keys(
        value,
        capsule_keys,
        label="capsule",
    )
    if (
        not _is_non_bool_int(capsule["schema_version"])
        or capsule["schema_version"] not in {
            SCHEMA_VERSION,
            *continuation_versions,
        }
        or capsule["capsule_type"] != CAPSULE_TYPE
        or capsule["directive_id"] != expected_directive_id
        or not _is_non_bool_int(capsule["ttl_seconds"])
        or capsule["ttl_seconds"] != TTL_SECONDS
        or not _is_non_bool_int(capsule["issued_at_epoch_s"])
        or not _is_non_bool_int(capsule["expires_at_epoch_s"])
        or capsule["expires_at_epoch_s"]
        - capsule["issued_at_epoch_s"]
        != TTL_SECONDS
        or capsule["issued_at_epoch_s"] < 0
        or capsule["expires_at_epoch_s"] < 0
    ):
        raise InputInvalid("capsule fixed fields are invalid")
    repo_value = _exact_keys(
        capsule["repo"],
        {
            "root",
            "upstream_ref",
            "head_sha",
            "upstream_sha",
            "ahead",
            "behind",
            "tracked_clean",
            "staged_clean",
        },
        label="capsule.repo",
    )
    if (
        repo_value["root"] != repo.resolve(strict=True).as_posix()
        or repo_value["upstream_ref"] != expected_upstream_ref
        or not _is_lower_oid(repo_value["head_sha"])
        or not _is_lower_oid(repo_value["upstream_sha"])
        or not _is_non_bool_int(repo_value["ahead"])
        or repo_value["ahead"] < 0
        or not _is_non_bool_int(repo_value["behind"])
        or repo_value["behind"] < 0
        or not isinstance(repo_value["tracked_clean"], bool)
        or not isinstance(repo_value["staged_clean"], bool)
    ):
        raise InputInvalid("capsule.repo fields are invalid")
    index = _exact_keys(
        capsule["index"],
        {"entry_count", "raw_stage_z_sha256"},
        label="capsule.index",
    )
    if (
        not _is_non_bool_int(index["entry_count"])
        or index["entry_count"] < 0
        or not _is_lower_sha256(index["raw_stage_z_sha256"])
    ):
        raise InputInvalid("capsule.index fields are invalid")
    for name in ("untracked", "ignored"):
        mapping_keys = (
            {"count", "canonical_json_sha256", "excluded_count"}
            if schema_version in scoped_versions
            else {"count", "canonical_json_sha256", "excluded_paths"}
        )
        mapping = _exact_keys(
            capsule[name],
            mapping_keys,
            label=f"capsule.{name}",
        )
        if (
            not _is_non_bool_int(mapping["count"])
            or mapping["count"] < 0
            or not _is_lower_sha256(mapping["canonical_json_sha256"])
            or (
                schema_version in scoped_versions
                and (
                    not _is_non_bool_int(mapping["excluded_count"])
                    or mapping["excluded_count"] < 0
                )
            )
            or (
                schema_version not in scoped_versions
                and mapping["excluded_paths"] != []
            )
        ):
            raise InputInvalid(f"capsule.{name} fields are invalid")
    if schema_version in scoped_versions:
        scope_keys = {
            "canonical_json_sha256",
            "exact_paths",
            "prefixes",
            "scope_version",
        }
        if (
            schema_version
            == VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION
        ):
            scope_keys.add("verifier_owned_ignored_prefixes")
        scope = _exact_keys(
            capsule["invariant_scope"],
            scope_keys,
            label="capsule.invariant_scope",
        )
        expected_scope_version = (
            VERIFIER_OWNED_INVARIANT_SCOPE_VERSION
            if schema_version
            == VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION
            else INVARIANT_SCOPE_VERSION
        )
        if (
            scope["scope_version"] != expected_scope_version
            or not isinstance(scope["exact_paths"], list)
            or not isinstance(scope["prefixes"], list)
            or (
                schema_version
                == VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION
                and not isinstance(
                    scope["verifier_owned_ignored_prefixes"], list
                )
            )
            or not _is_lower_sha256(scope["canonical_json_sha256"])
        ):
            raise InputInvalid("capsule.invariant_scope fields are invalid")
        try:
            normalized_scope = _normalize_invariant_scope(
                tuple(Path(path) for path in scope["exact_paths"]),
                tuple(Path(prefix) for prefix in scope["prefixes"]),
                (
                    tuple(
                        Path(prefix)
                        for prefix in scope[
                            "verifier_owned_ignored_prefixes"
                        ]
                    )
                    if schema_version
                    == VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION
                    else None
                ),
            )
        except (TypeError, ValueError) as exc:
            raise InputInvalid(
                "capsule.invariant_scope fields are invalid"
            ) from exc
        if scope != normalized_scope:
            raise InputInvalid("capsule.invariant_scope is not canonical")
    if schema_version in continuation_versions:
        tracked_worktree = _exact_keys(
            capsule["tracked_worktree"],
            {"count", "canonical_json_sha256", "rows"},
            label="capsule.tracked_worktree",
        )
        rows = tracked_worktree["rows"]
        if (
            not _is_non_bool_int(tracked_worktree["count"])
            or tracked_worktree["count"] <= 0
            or not _is_lower_sha256(
                tracked_worktree["canonical_json_sha256"]
            )
            or not isinstance(rows, list)
            or len(rows) != tracked_worktree["count"]
        ):
            raise InputInvalid("capsule.tracked_worktree fields are invalid")
        paths: list[str] = []
        for row in rows:
            item = _exact_keys(
                row,
                {"git_blob_no_filters", "path", "raw_sha256"},
                label="capsule.tracked_worktree.rows[]",
            )
            if (
                not isinstance(item["path"], str)
                or not _is_lower_sha256(item["raw_sha256"])
                or not _is_lower_oid(item["git_blob_no_filters"])
            ):
                raise InputInvalid(
                    "capsule.tracked_worktree row fields are invalid"
                )
            paths.append(
                _relative_path(
                    Path(item["path"]),
                    label="capsule.tracked_worktree.rows[].path",
                )
            )
        if (
            paths != sorted(paths, key=lambda item: item.encode("utf-8"))
            or len(paths) != len(set(paths))
            or tracked_worktree["canonical_json_sha256"]
            != _sha256_bytes(canonical_json_bytes(rows))
            or repo_value["tracked_clean"] is not False
        ):
            raise InputInvalid("capsule.tracked_worktree is not canonical")
    elif repo_value["tracked_clean"] is not True:
        raise InputInvalid("clean capsule records a dirty worktree")
    modules = capsule["module_roots"]
    if not isinstance(modules, list):
        raise InputInvalid("capsule.module_roots is invalid")
    for item in modules:
        entry = _exact_keys(
            item,
            MODULE_ROOT_KEYS,
            label="capsule.module_roots[]",
        )
        if (
            not _is_non_bool_int(entry["entry_bytes"])
            or entry["entry_bytes"] <= 0
            or not isinstance(entry["entry_relpath"], str)
            or not entry["entry_relpath"]
            or not _is_lower_sha256(entry["entry_sha256"])
            or not _plain_token(entry["package_name"])
            or not _plain_token(entry["package_version"])
            or not isinstance(entry["root_path"], str)
            or not entry["root_path"]
            or "\\" in entry["root_path"]
            or "\n" in entry["root_path"]
            or "\r" in entry["root_path"]
        ):
            raise InputInvalid("capsule.module_roots[] fields are invalid")
        _relative_path(
            Path(entry["entry_relpath"]),
            label="capsule.module_roots[].entry_relpath",
        )
    identities = _exact_keys(
        capsule["identities"],
        {"directive", "spec", "generator"},
        label="capsule.identities",
    )
    for name in ("directive", "spec", "generator"):
        _validate_identity(
            identities[name],
            label=f"capsule.identities.{name}",
        )
    if identities["generator"]["path"] != GENERATOR_PATH.as_posix():
        raise InputInvalid("capsule generator path is invalid")
    if identities["directive"]["path"] != _relative_path(
        expected_directive_path, label="expected directive"
    ):
        raise InputInvalid("capsule directive path is invalid")
    if identities["spec"]["path"] != _relative_path(
        expected_spec_path, label="expected spec"
    ):
        raise InputInvalid("capsule spec path is invalid")
    return capsule


def _require_valid_ttl(capsule: dict[str, Any], now: int) -> None:
    if not (
        capsule["issued_at_epoch_s"]
        <= now
        < capsule["expires_at_epoch_s"]
    ):
        raise InputInvalid("capsule TTL is invalid")


def verify_capsule(
    *,
    repo: Path,
    capsule_root: Path,
    capsule_sha256: str,
    expected_directive_id: str,
    expected_directive_path: Path,
    expected_spec_path: Path,
    expected_upstream_ref: str = UPSTREAM_REF,
    now_fn: Callable[[], int] = lambda: int(time.time()),
) -> dict[str, Any]:
    if LOWER_SHA256_RE.fullmatch(capsule_sha256) is None:
        raise InputInvalid("capsule token must be lowercase SHA-256")
    if DIRECTIVE_ID_RE.fullmatch(expected_directive_id) is None:
        raise InputInvalid("directive ID is invalid")
    repo_resolved = _require_directory(repo, label="repository")
    root = _validate_capsule_root(
        repo_resolved, capsule_root, require_exists=True
    )
    path = root / f"{capsule_sha256}.json"
    if not path.is_file() or _is_linklike(path):
        raise InputInvalid("capsule is not an ordinary file")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InfrastructureFailure("capsule could not be read") from exc
    if _sha256_bytes(raw) != capsule_sha256:
        raise InputInvalid("capsule SHA-256 mismatch")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_object_without_duplicates,
        )
    except InputInvalid:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputInvalid("capsule JSON is invalid") from exc
    try:
        canonical = canonical_json_bytes(value)
    except (UnicodeEncodeError, ValueError) as exc:
        raise InputInvalid("capsule canonical JSON is invalid") from exc
    if canonical != raw:
        raise InputInvalid("capsule bytes are not canonical JSON")
    capsule = _validate_capsule_schema(
        value,
        expected_directive_id=expected_directive_id,
        expected_directive_path=expected_directive_path,
        expected_spec_path=expected_spec_path,
        expected_upstream_ref=expected_upstream_ref,
        repo=repo_resolved,
    )
    _require_valid_ttl(capsule, _clock_value(now_fn))
    identities = capsule["identities"]
    expected_state = {
        "repo": capsule["repo"],
        "index": capsule["index"],
        "untracked": capsule["untracked"],
        "ignored": capsule["ignored"],
        "identities": capsule["identities"],
    }
    allowed_dirty_paths: tuple[Path, ...] | None = None
    invariant_scope: dict[str, Any] | None = None
    if capsule["schema_version"] in {
        CONTINUATION_SCHEMA_VERSION,
        SCOPED_CONTINUATION_SCHEMA_VERSION,
        VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION,
    }:
        expected_state["tracked_worktree"] = capsule["tracked_worktree"]
        allowed_dirty_paths = tuple(
            Path(row["path"])
            for row in capsule["tracked_worktree"]["rows"]
        )
    if capsule["schema_version"] in {
        SCOPED_CONTINUATION_SCHEMA_VERSION,
        VERIFIER_OWNED_SCOPED_CONTINUATION_SCHEMA_VERSION,
    }:
        invariant_scope = capsule["invariant_scope"]
        expected_state["invariant_scope"] = invariant_scope
    for _snapshot_number in range(2):
        state = measure_repo_state(
            repo_resolved,
            directive_path=Path(identities["directive"]["path"]),
            spec_path=Path(identities["spec"]["path"]),
            generator_path=Path(identities["generator"]["path"]),
            directive_sha256=identities["directive"]["raw_sha256"],
            spec_sha256=identities["spec"]["raw_sha256"],
            allowed_dirty_paths=allowed_dirty_paths,
            invariant_scope=invariant_scope,
            upstream_ref=expected_upstream_ref,
        )
        if canonical_json_bytes(state) != canonical_json_bytes(expected_state):
            raise InputInvalid("live repository state differs from capsule")
        _require_dispatchable(state)
    _require_valid_ttl(capsule, _clock_value(now_fn))
    return capsule


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="capture or verify a dispatch entry capsule"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--repo", required=True)
    capture.add_argument("--directive-id", required=True)
    capture.add_argument("--directive", required=True)
    capture.add_argument("--directive-sha256")
    capture.add_argument("--spec", required=True)
    capture.add_argument("--spec-sha256")
    capture.add_argument("--allow-dirty-path", action="append")
    capture.add_argument("--tracked-worktree-sha256")
    capture.add_argument("--invariant-path", action="append")
    capture.add_argument("--invariant-prefix", action="append")
    capture.add_argument(
        "--verifier-owned-ignored-prefix",
        action="append",
    )
    capture.add_argument("--invariant-scope-sha256")
    capture.add_argument("--module-root", action="append", default=[])
    capture.add_argument("--module-package", action="append", default=[])
    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--capsule-sha256", required=True)
    verify.add_argument("--expected-directive-id", required=True)
    verify.add_argument("--expected-directive", required=True)
    verify.add_argument("--expected-spec", required=True)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    capsule_root: Path = CAPSULE_ROOT,
    now_fn: Callable[[], int] = lambda: int(time.time()),
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.mode == "capture":
            if len(args.module_root) != len(args.module_package):
                raise InputInvalid(
                    "--module-root and --module-package must be paired"
                )
            module_specs = tuple(
                (Path(root), package)
                for root, package in zip(
                    args.module_root, args.module_package, strict=True
                )
            )
            path, digest = capture_capsule(
                repo=Path(args.repo),
                capsule_root=capsule_root,
                directive_id=args.directive_id,
                directive_path=Path(args.directive),
                spec_path=Path(args.spec),
                directive_sha256=args.directive_sha256,
                spec_sha256=args.spec_sha256,
                module_specs=module_specs,
                allowed_dirty_paths=(
                    tuple(Path(path) for path in args.allow_dirty_path)
                    if args.allow_dirty_path is not None
                    else None
                ),
                tracked_worktree_sha256=args.tracked_worktree_sha256,
                invariant_paths=(
                    tuple(Path(path) for path in args.invariant_path)
                    if args.invariant_path is not None
                    else None
                ),
                invariant_prefixes=(
                    tuple(Path(path) for path in args.invariant_prefix)
                    if args.invariant_prefix is not None
                    else None
                ),
                verifier_owned_ignored_prefixes=(
                    tuple(
                        Path(path)
                        for path in args.verifier_owned_ignored_prefix
                    )
                    if args.verifier_owned_ignored_prefix is not None
                    else None
                ),
                invariant_scope_sha256=args.invariant_scope_sha256,
                now_fn=now_fn,
            )
            print(
                canonical_json_bytes(
                    {
                        "capsule_sha256": digest,
                        "path": path.as_posix(),
                    }
                ).decode("utf-8")
            )
        else:
            verify_capsule(
                repo=Path(args.repo),
                capsule_root=capsule_root,
                capsule_sha256=args.capsule_sha256,
                expected_directive_id=args.expected_directive_id,
                expected_directive_path=Path(args.expected_directive),
                expected_spec_path=Path(args.expected_spec),
                now_fn=now_fn,
            )
            print(
                canonical_json_bytes(
                    {
                        "capsule_sha256": args.capsule_sha256,
                        "status": "GREEN",
                    }
                ).decode("utf-8")
            )
        return 0
    except InputInvalid as exc:
        print(f"INPUT_INVALID: {exc}", file=sys.stderr)
        return 2
    except InfrastructureFailure as exc:
        print(f"INFRA_FAILURE: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(
            f"INFRA_FAILURE: unexpected {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
