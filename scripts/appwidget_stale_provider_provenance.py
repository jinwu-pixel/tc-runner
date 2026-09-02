"""Deterministic Git/source provenance for the BUG27084 harness."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
from typing import Any, Mapping, Sequence


HARNESS_PATHS = (
    "scripts/appwidget_stale_provider_cli.py",
    "scripts/appwidget_stale_provider_evidence.py",
    "scripts/appwidget_stale_provider_models.py",
    "scripts/appwidget_stale_provider_orchestrator.py",
    "scripts/appwidget_stale_provider_parsers.py",
    "scripts/appwidget_stale_provider_preflight.py",
    "scripts/appwidget_stale_provider_profiles.py",
    "scripts/appwidget_stale_provider_provenance.py",
    "scripts/appwidget_stale_provider_repro.py",
    "scripts/appwidget_stale_provider_state.py",
    "scripts/appwidget_stale_provider_transport.py",
)

_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_GIT_OID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class HarnessProvenanceError(RuntimeError):
    """The runtime harness cannot be given an exact, trustworthy identity."""


def _canonical_file_record(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != {"path", "size", "sha256"}:
        raise HarnessProvenanceError("harness file record schema mismatch")
    path = value.get("path")
    if not isinstance(path, str) or not path or "\\" in path:
        raise HarnessProvenanceError("harness path must be POSIX repo-relative")
    relative = PurePosixPath(path)
    if (
        relative.is_absolute()
        or PureWindowsPath(path).drive
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise HarnessProvenanceError("harness path must remain beneath the repository")
    size = value.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise HarnessProvenanceError("harness byte size must be a non-negative integer")
    sha256 = value.get("sha256")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise HarnessProvenanceError("harness SHA-256 must be uppercase hexadecimal")
    return {"path": relative.as_posix(), "sha256": sha256, "size": size}


def canonical_source_bytes(files: Sequence[Mapping[str, Any]]) -> bytes:
    """Serialize content identity without commits, paths outside the repo, or time."""
    records = sorted(
        (_canonical_file_record(value) for value in files),
        key=lambda value: value["path"],
    )
    paths = [record["path"] for record in records]
    if len(paths) != len(set(paths)):
        raise HarnessProvenanceError("harness file records contain duplicate paths")
    payload = {"files": records, "schema_version": 1}
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _git_bytes(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", "-C", str(root), *args),
            capture_output=True,
            check=False,
            text=False,
        )
    except OSError as exc:
        raise HarnessProvenanceError("Git could not inspect the harness") from exc
    if completed.returncode != 0:
        raise HarnessProvenanceError("Git could not establish harness provenance")
    return completed.stdout


def _git_text(root: Path, *args: str) -> str:
    try:
        return _git_bytes(root, *args).decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise HarnessProvenanceError("Git returned non-UTF-8 provenance output") from exc


def _checked_repository_root(repo_root: Path | str) -> Path:
    try:
        root = Path(repo_root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise HarnessProvenanceError("repository root does not exist") from exc
    if not root.is_dir():
        raise HarnessProvenanceError("repository root must be a directory")
    top_level = _git_text(root, "rev-parse", "--show-toplevel")
    try:
        discovered = Path(top_level).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise HarnessProvenanceError("Git repository root is invalid") from exc
    if discovered != root:
        raise HarnessProvenanceError("repository root must be the Git top level")
    return root


def _checked_oid(value: str, field: str) -> str:
    if not _GIT_OID_RE.fullmatch(value):
        raise HarnessProvenanceError(f"{field} is not a full Git object ID")
    return value


def inspect_harness(repo_root: Path | str) -> dict[str, Any]:
    """Return canonical HEAD source plus Git identity without gating dirtiness."""
    root = _checked_repository_root(repo_root)
    _git_text(root, "ls-files", "--error-unmatch", "--", *HARNESS_PATHS)
    repository_head = _checked_oid(
        _git_text(root, "rev-parse", "--verify", "HEAD^{commit}"),
        "repository HEAD",
    )
    harness_commit = _checked_oid(
        _git_text(root, "log", "-1", "--format=%H", "--", *HARNESS_PATHS),
        "harness commit",
    )
    scope_status = _git_text(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *HARNESS_PATHS,
    )
    scope_changes = scope_status.splitlines() if scope_status else []
    files: list[dict[str, Any]] = []
    for relative in HARNESS_PATHS:
        path = root.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file():
            raise HarnessProvenanceError("harness source must be a regular file")
        if not scope_changes:
            head_blob = _git_text(root, "rev-parse", f"HEAD:{relative}")
            worktree_blob = _git_text(
                root,
                "hash-object",
                f"--path={relative}",
                relative,
            )
            if worktree_blob != head_blob:
                scope_changes.append(f"WORKTREE_DIFFERS_FROM_HEAD {relative}")
        data = _git_bytes(root, "show", f"HEAD:{relative}")
        files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest().upper(),
                "size": len(data),
            }
        )
    source_bytes = canonical_source_bytes(files)
    return {
        "files": files,
        "harness_commit": harness_commit,
        "repository_head": repository_head,
        "schema_version": 1,
        "scope_changes": scope_changes,
        "scope_clean": not scope_changes,
        "source_digest_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
    }


def require_clean_harness(repo_root: Path | str) -> dict[str, Any]:
    provenance = inspect_harness(repo_root)
    if not provenance["scope_clean"]:
        raise HarnessProvenanceError("runtime harness scope differs from HEAD")
    return provenance


def validate_harness_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "files",
        "harness_commit",
        "repository_head",
        "schema_version",
        "scope_changes",
        "scope_clean",
        "source_digest_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise HarnessProvenanceError("harness provenance schema mismatch")
    if value.get("schema_version") != 1:
        raise HarnessProvenanceError("unsupported harness provenance schema")
    files_value = value.get("files")
    if not isinstance(files_value, list):
        raise HarnessProvenanceError("harness provenance files must be a list")
    files = sorted(
        (_canonical_file_record(item) for item in files_value),
        key=lambda item: item["path"],
    )
    if files != files_value:
        raise HarnessProvenanceError("harness file records are not canonical")
    if tuple(item["path"] for item in files) != HARNESS_PATHS:
        raise HarnessProvenanceError("harness file records differ from the exact scope")
    repository_head_value = value.get("repository_head")
    harness_commit_value = value.get("harness_commit")
    if not isinstance(repository_head_value, str):
        raise HarnessProvenanceError("repository head must be a string")
    if not isinstance(harness_commit_value, str):
        raise HarnessProvenanceError("harness commit must be a string")
    repository_head = _checked_oid(repository_head_value, "repository HEAD")
    harness_commit = _checked_oid(harness_commit_value, "harness commit")
    scope_clean = value.get("scope_clean")
    scope_changes = value.get("scope_changes")
    if not isinstance(scope_clean, bool):
        raise HarnessProvenanceError("harness scope_clean must be boolean")
    if not isinstance(scope_changes, list) or not all(
        isinstance(item, str) and item for item in scope_changes
    ):
        raise HarnessProvenanceError("harness scope_changes must be a string list")
    if scope_clean != (not scope_changes):
        raise HarnessProvenanceError("harness scope status is internally inconsistent")
    source_digest = value.get("source_digest_sha256")
    if not isinstance(source_digest, str) or not _SHA256_RE.fullmatch(source_digest):
        raise HarnessProvenanceError("harness source digest must be uppercase SHA-256")
    actual_digest = hashlib.sha256(canonical_source_bytes(files)).hexdigest().upper()
    if source_digest != actual_digest:
        raise HarnessProvenanceError(
            "harness source digest does not match file records"
        )
    return {
        "files": files,
        "harness_commit": harness_commit,
        "repository_head": repository_head,
        "schema_version": 1,
        "scope_changes": list(scope_changes),
        "scope_clean": scope_clean,
        "source_digest_sha256": source_digest,
    }


def provenance_mismatches(
    recorded: Mapping[str, Any], current: Mapping[str, Any]
) -> tuple[str, ...]:
    recorded_value = validate_harness_provenance(recorded)
    current_value = validate_harness_provenance(current)
    mismatches: list[str] = []
    if not recorded_value["scope_clean"]:
        mismatches.append("recorded_scope_clean")
    if not current_value["scope_clean"]:
        mismatches.append("scope_clean")
    for field in ("harness_commit", "source_digest_sha256"):
        if recorded_value[field] != current_value[field]:
            mismatches.append(field)
    return tuple(mismatches)


def require_compatible_harness(
    recorded: Mapping[str, Any], current: Mapping[str, Any]
) -> None:
    mismatches = provenance_mismatches(recorded, current)
    if mismatches:
        raise HarnessProvenanceError(
            "runtime harness provenance mismatch: " + ", ".join(mismatches)
        )
