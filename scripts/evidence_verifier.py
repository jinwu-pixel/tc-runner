# -*- coding: utf-8 -*-
"""Baseline-bound, fail-closed host evidence verifier.

The verifier has two modes:

* ``capture-baseline`` records Git state, collected pytest nodeids, and
  per-nodeid pytest outcomes.
* ``verify`` binds a capsule to those exact baseline bytes, remeasures the
  repository, emits a deterministic evidence bundle, and exits 0 only when
  checks C0 through C5 are all GREEN.

No command in this module performs Git writes, network access, or device IO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


SCHEMA_VERSION = 1
CHECK_IDS = ("C0", "C1", "C2", "C3", "C4", "C5")
HEX_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GLOB_CHARS = frozenset("*?[")


class InputInvalid(Exception):
    """The baseline or capsule cannot authorize measurement."""


class MeasurementError(Exception):
    """A required Git/pytest/IO measurement could not be completed."""


@dataclass
class CommandRecorder:
    cwd: Path
    steps: list[dict[str, Any]] = field(default_factory=list)

    def run(
        self,
        argv: list[str],
        *,
        display_argv: list[str] | None = None,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        shown = display_argv if display_argv is not None else argv
        try:
            proc = subprocess.run(
                argv,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                input=input_text,
                env=env,
                check=False,
            )
        except OSError as exc:
            self.steps.append(
                {
                    "command": list(shown),
                    "cwd": self.cwd.as_posix(),
                    "exit_code": None,
                }
            )
            raise MeasurementError(
                f"command could not start: {shown[0]}"
            ) from exc
        self.steps.append(
            {
                "command": list(shown),
                "cwd": self.cwd.as_posix(),
                "exit_code": proc.returncode,
            }
        )
        return proc


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_json(path: Path, value: Any) -> None:
    data = _canonical_bytes(value)
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        raise MeasurementError(f"could not write JSON output: {path}") from exc


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputInvalid(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputInvalid(f"cannot read JSON input: {path}") from exc
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputInvalid(f"invalid JSON input: {path}") from exc
    if not isinstance(value, dict):
        raise InputInvalid(f"JSON root must be an object: {path}")
    return value, raw


def _require_exact_keys(
    value: dict[str, Any],
    expected: Iterable[str],
    *,
    where: str,
) -> None:
    expected_set = set(expected)
    actual = set(value)
    missing = sorted(expected_set - actual)
    unknown = sorted(actual - expected_set)
    if missing or unknown:
        raise InputInvalid(
            f"{where} keys invalid; missing={missing}, unknown={unknown}"
        )


def _require_int(value: Any, *, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise InputInvalid(f"{where} must be an integer >= {minimum}")
    return value


def _require_string(value: Any, *, where: str, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise InputInvalid(f"{where} must be a non-empty string")
    return value


def _require_oid(value: Any, *, where: str) -> str:
    text = _require_string(value, where=where)
    if not HEX_RE.fullmatch(text):
        raise InputInvalid(f"{where} must be a Git object id")
    return text


def _require_sorted_unique_strings(value: Any, *, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InputInvalid(f"{where} must be a string list")
    if value != sorted(set(value)):
        raise InputInvalid(f"{where} must be sorted and unique")
    return list(value)


def _normalize_git_path(path: str) -> str:
    return path.replace("\\", "/")


def _validate_rel_path(path: Any, *, where: str, forbid_glob: bool = False) -> str:
    text = _require_string(path, where=where)
    if "\x00" in text:
        raise InputInvalid(f"{where} contains NUL")
    if "\\" in text:
        raise InputInvalid(f"{where} must use forward slashes")
    posix = PurePosixPath(text)
    windows = PureWindowsPath(text)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or text in {".", ".."}
        or ".." in posix.parts
        or any(part in {"", "."} for part in posix.parts)
    ):
        raise InputInvalid(f"{where} must be a canonical repo-relative path")
    if forbid_glob and (any(char in text for char in GLOB_CHARS) or text.endswith("/")):
        raise InputInvalid(f"{where} must be an exact file path, not a glob/prefix")
    return text


def _validate_path_list(
    value: Any,
    *,
    where: str,
    forbid_glob: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        raise InputInvalid(f"{where} must be a list")
    normalized = [
        _validate_rel_path(item, where=f"{where}[{index}]", forbid_glob=forbid_glob)
        for index, item in enumerate(value)
    ]
    if len(normalized) != len(set(normalized)):
        raise InputInvalid(f"{where} contains duplicate paths")
    if len({item.casefold() for item in normalized}) != len(normalized):
        raise InputInvalid(f"{where} contains case-colliding paths")
    return sorted(normalized)


def _repo_relative_path(path: Path, repo: Path) -> str | None:
    try:
        relative = path.resolve(strict=False).relative_to(repo.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return relative.as_posix()


def _require_repo_relative_path(
    path: Path,
    *,
    repo: Path,
    where: str,
) -> str:
    relative = _repo_relative_path(path, repo)
    if relative is None:
        raise InputInvalid(f"{where} must resolve inside the repository")
    return _validate_rel_path(relative, where=where, forbid_glob=True)


def _validate_output_path(
    path: Path,
    *,
    repo: Path,
    snapshot: dict[str, Any],
    evidence_paths: Iterable[str] | None,
    forbidden_paths: Iterable[Path] = (),
    forbidden_roots: Iterable[Path] = (),
) -> None:
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise InputInvalid("output path could not be resolved safely") from exc
    for forbidden in forbidden_paths:
        try:
            forbidden_resolved = forbidden.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise InputInvalid(
                "protected path could not be resolved safely"
            ) from exc
        if resolved == forbidden_resolved:
            raise InputInvalid("output path overlaps a protected input/tool path")
    for forbidden_root in forbidden_roots:
        try:
            root_resolved = forbidden_root.resolve(strict=False)
            resolved.relative_to(root_resolved)
        except ValueError:
            continue
        except (OSError, RuntimeError) as exc:
            raise InputInvalid(
                "protected root could not be resolved safely"
            ) from exc
        raise InputInvalid("output path must not be inside Git metadata")
    if resolved.exists() and resolved.is_dir():
        raise InputInvalid("output path must be a file")

    relative = _require_repo_relative_path(
        resolved,
        repo=repo,
        where="output path",
    )
    relative_casefold = relative.casefold()
    if relative_casefold == ".git" or relative_casefold.startswith(".git/"):
        raise InputInvalid("output path must not overwrite repository Git metadata")
    protected_tracked = {
        tracked.casefold()
        for tracked in (
            set(snapshot["index_entries"]) | set(snapshot["head_tree"])
        )
    }
    if relative_casefold in protected_tracked:
        raise InputInvalid("output path must not be Git tracked")
    if evidence_paths is not None and relative not in set(evidence_paths):
        raise InputInvalid(
            "repo-local output path must be an exact capsule evidence_path"
        )


def _git(
    recorder: CommandRecorder,
    *args: str,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    proc = recorder.run(["git", *args])
    if proc.returncode != 0 and not allow_failure:
        raise MeasurementError(f"git command failed: git {' '.join(args)}")
    return proc


def _repo_root(recorder: CommandRecorder) -> Path:
    proc = _git(recorder, "rev-parse", "--show-toplevel")
    root = Path(proc.stdout.strip()).resolve()
    if not root.is_dir():
        raise MeasurementError("Git repository root is not a directory")
    recorder.cwd = root
    return root


def _git_metadata_roots(
    recorder: CommandRecorder,
    repo: Path,
) -> tuple[Path, ...]:
    roots: list[Path] = []
    for option in ("--git-dir", "--git-common-dir"):
        raw = _git(recorder, "rev-parse", option).stdout.strip()
        if not raw:
            raise MeasurementError(f"git rev-parse {option} returned no path")
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = repo / candidate
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise MeasurementError(
                f"could not resolve Git metadata path for {option}"
            ) from exc
        roots.append(resolved)
    return tuple(dict.fromkeys(roots))


def _split_nul(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


def _parse_index_entries(output: str) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for record in _split_nul(output):
        try:
            prefix, raw_path = record.split("\t", 1)
            mode, oid, stage_text = prefix.split(" ", 2)
            stage = int(stage_text)
        except (ValueError, TypeError) as exc:
            raise MeasurementError("could not parse git ls-files -s output") from exc
        path = _normalize_git_path(raw_path)
        if path in entries:
            raise MeasurementError(f"multiple index stages are unsupported: {path}")
        entries[path] = {
            "mode": mode,
            "oid": oid,
            "stage": stage,
        }
    return entries


def _parse_index_tags(output: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for record in _split_nul(output):
        if len(record) < 3 or record[1] != " ":
            raise MeasurementError("could not parse git ls-files -v output")
        tag = record[0]
        path = _normalize_git_path(record[2:])
        if path in tags:
            raise MeasurementError(f"duplicate index tag path: {path}")
        tags[path] = tag
    return tags


def _index_fingerprint(
    entries: dict[str, dict[str, Any]],
    tags: dict[str, str],
) -> str:
    if set(entries) != set(tags):
        raise MeasurementError("index entry/tag path sets differ")
    records = [
        (
            f"{path}\0{entry['mode']}\0{entry['oid']}\0"
            f"{entry['stage']}\0{tags[path]}"
        )
        for path, entry in sorted(entries.items())
    ]
    return _sha256_bytes("\0".join(records).encode("utf-8"))


def _parse_head_tree(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in _split_nul(output):
        try:
            prefix, raw_path = record.split("\t", 1)
            _mode, object_type, oid = prefix.split(" ", 2)
        except ValueError as exc:
            raise MeasurementError("could not parse git ls-tree output") from exc
        if object_type != "blob":
            continue
        path = _normalize_git_path(raw_path)
        result[path] = oid
    return result


def _parse_untracked(output: str) -> list[str]:
    result: list[str] = []
    records = _split_nul(output)
    index = 0
    while index < len(records):
        record = records[index]
        if record.startswith("?? "):
            result.append(_normalize_git_path(record[3:]))
        if len(record) >= 2 and ("R" in record[:2] or "C" in record[:2]):
            index += 1
        index += 1
    return sorted(set(result))


def _worktree_blob(
    recorder: CommandRecorder,
    repo: Path,
    path: str,
) -> str | None:
    full_path = repo.joinpath(*PurePosixPath(path).parts)
    if not os.path.lexists(full_path):
        return None
    if full_path.is_dir() and not full_path.is_symlink():
        return None
    proc = _git(recorder, "hash-object", "--", path)
    oid = proc.stdout.strip()
    if not HEX_RE.fullmatch(oid):
        raise MeasurementError(f"invalid hash-object output for {path}")
    return oid


def _worktree_blob_map(
    recorder: CommandRecorder,
    repo: Path,
    paths: Iterable[str],
) -> dict[str, str | None]:
    ordered = sorted(set(paths))
    result: dict[str, str | None] = {}
    existing: list[str] = []
    for path in ordered:
        if "\n" in path or "\r" in path:
            raise MeasurementError("tracked paths containing newlines are unsupported")
        full_path = repo.joinpath(*PurePosixPath(path).parts)
        if not os.path.lexists(full_path) or (
            full_path.is_dir() and not full_path.is_symlink()
        ):
            result[path] = None
        else:
            existing.append(path)
    if existing:
        proc = recorder.run(
            ["git", "hash-object", "--stdin-paths"],
            input_text="".join(path + "\n" for path in existing),
        )
        if proc.returncode != 0:
            raise MeasurementError("git hash-object --stdin-paths failed")
        object_ids = [line.strip() for line in proc.stdout.splitlines()]
        if len(object_ids) != len(existing):
            raise MeasurementError("hash-object result count mismatch")
        for path, oid in zip(existing, object_ids):
            if not HEX_RE.fullmatch(oid):
                raise MeasurementError(f"invalid hash-object output for {path}")
            result[path] = oid
    return dict(sorted(result.items()))


def _verifier_oid(recorder: CommandRecorder) -> str:
    path = str(Path(__file__).resolve())
    proc = _git(recorder, "hash-object", "--", path)
    oid = proc.stdout.strip()
    if not HEX_RE.fullmatch(oid):
        raise MeasurementError("invalid verifier hash-object output")
    return oid


def _snapshot(recorder: CommandRecorder, repo: Path) -> dict[str, Any]:
    head_sha = _git(recorder, "rev-parse", "HEAD").stdout.strip()
    upstream_sha = _git(recorder, "rev-parse", "@{upstream}").stdout.strip()
    counts_text = _git(
        recorder,
        "rev-list",
        "--left-right",
        "--count",
        "@{upstream}...HEAD",
    ).stdout.strip()
    try:
        behind_text, ahead_text = counts_text.split()
        behind = int(behind_text)
        ahead = int(ahead_text)
    except (ValueError, TypeError) as exc:
        raise MeasurementError("could not parse ahead/behind counts") from exc

    index_entries = _parse_index_entries(
        _git(recorder, "ls-files", "-s", "-z").stdout
    )
    index_tags = _parse_index_tags(
        _git(recorder, "ls-files", "-v", "-z").stdout
    )
    dirty_paths = sorted(
        {
            _normalize_git_path(item)
            for item in _split_nul(
                _git(recorder, "diff", "--name-only", "-z", "--").stdout
            )
        }
    )
    staged_paths = sorted(
        {
            _normalize_git_path(item)
            for item in _split_nul(
                _git(
                    recorder,
                    "diff",
                    "--cached",
                    "--name-only",
                    "-z",
                    "--",
                ).stdout
            )
        }
    )
    untracked = _parse_untracked(
        _git(
            recorder,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ).stdout
    )
    head_tree = _parse_head_tree(
        _git(recorder, "ls-tree", "-r", "-z", "HEAD").stdout
    )
    tracked_blobs = _worktree_blob_map(
        recorder,
        repo,
        set(index_entries) | set(head_tree),
    )
    return {
        "head_sha": head_sha,
        "upstream_sha": upstream_sha,
        "ahead": ahead,
        "behind": behind,
        "index_entries": index_entries,
        "index_tags": index_tags,
        "index_fingerprint": _index_fingerprint(index_entries, index_tags),
        "dirty_paths": dirty_paths,
        "staged_paths": staged_paths,
        "untracked": untracked,
        "head_tree": head_tree,
        "tracked_blobs": tracked_blobs,
    }


def _parse_collect_output(output: str) -> list[str]:
    nodeids: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if "::" not in line:
            continue
        module = line.split("::", 1)[0]
        if not module.endswith(".py") or any(char.isspace() for char in module):
            continue
        rest = line[len(module):]
        nodeids.append(_normalize_git_path(module) + rest)
    if not nodeids:
        raise MeasurementError("pytest collection returned no nodeids")
    if len(nodeids) != len(set(nodeids)):
        raise MeasurementError("pytest collection returned duplicate nodeids")
    return sorted(nodeids)


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _collect_nodeids(recorder: CommandRecorder) -> list[str]:
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        "--color=no",
    ]
    proc = recorder.run(argv, env=_pytest_env())
    if proc.returncode != 0:
        raise MeasurementError(
            f"pytest collection failed with exit {proc.returncode}"
        )
    return _parse_collect_output(proc.stdout)


def _nodeid_key(nodeid: str) -> tuple[str, str]:
    parts = nodeid.split("::")
    module = parts[0]
    dotted_module = module[:-3].replace("/", ".")
    classname = ".".join([dotted_module, *parts[1:-1]])
    return classname, parts[-1]


def _parse_junit(path: Path, collected: list[str]) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise MeasurementError("could not parse pytest JUnit output") from exc

    by_key: dict[tuple[str, str], str] = {}
    for nodeid in collected:
        key = _nodeid_key(nodeid)
        if key in by_key:
            raise MeasurementError(f"ambiguous JUnit nodeid key: {key}")
        by_key[key] = nodeid

    outcomes: dict[str, list[str]] = {
        "passed": [],
        "skipped": [],
        "xfailed": [],
    }
    failed = 0
    errors = 0
    mapped: set[str] = set()
    for case in root.iter("testcase"):
        key = (case.attrib.get("classname", ""), case.attrib.get("name", ""))
        nodeid = by_key.get(key)
        if nodeid is None:
            if case.find("error") is not None:
                errors += 1
                continue
            raise MeasurementError(f"JUnit testcase does not map to collect: {key}")
        if nodeid in mapped:
            raise MeasurementError(f"duplicate JUnit testcase for {nodeid}")
        mapped.add(nodeid)

        if case.find("failure") is not None:
            failed += 1
        elif case.find("error") is not None:
            errors += 1
        else:
            skipped = case.find("skipped")
            if skipped is None:
                outcomes["passed"].append(nodeid)
            elif "xfail" in skipped.attrib.get("type", "").lower():
                outcomes["xfailed"].append(nodeid)
            else:
                outcomes["skipped"].append(nodeid)

    if mapped != set(collected):
        missing = sorted(set(collected) - mapped)
        raise MeasurementError(f"JUnit is missing collected nodeids: {missing}")

    for values in outcomes.values():
        values.sort()
    counts = {
        "passed": len(outcomes["passed"]),
        "skipped": len(outcomes["skipped"]),
        "xfailed": len(outcomes["xfailed"]),
        "failed": failed,
        "errors": errors,
    }
    return {**outcomes, "counts": counts}


def _run_pytest(
    recorder: CommandRecorder,
    collected: list[str],
) -> tuple[int, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="evidence-verifier-") as temp_dir:
        junit_path = Path(temp_dir) / "pytest.xml"
        argv = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-q",
            "-p",
            "no:cacheprovider",
            "--color=no",
            "-o",
            "xfail_strict=true",
            f"--junitxml={junit_path}",
        ]
        shown = list(argv)
        shown[-1] = "--junitxml=<temporary>"
        proc = recorder.run(
            argv,
            display_argv=shown,
            env=_pytest_env(),
        )
        if proc.returncode not in {0, 1}:
            raise MeasurementError(
                f"pytest execution failed with exit {proc.returncode}"
            )
        if not junit_path.is_file():
            raise MeasurementError("pytest did not create JUnit output")
        outcomes = _parse_junit(junit_path, collected)
    return proc.returncode, outcomes


def _snapshot_stable(before: dict[str, Any], after: dict[str, Any]) -> bool:
    keys = (
        "head_sha",
        "upstream_sha",
        "ahead",
        "behind",
        "index_fingerprint",
        "dirty_paths",
        "staged_paths",
        "untracked",
        "tracked_blobs",
    )
    return all(before[key] == after[key] for key in keys)


def _snapshot_stable_ignoring_evidence(
    before: dict[str, Any],
    after: dict[str, Any],
    evidence_paths: Iterable[str],
) -> bool:
    keys = (
        "head_sha",
        "upstream_sha",
        "ahead",
        "behind",
        "index_fingerprint",
        "dirty_paths",
        "staged_paths",
        "tracked_blobs",
    )
    if not all(before[key] == after[key] for key in keys):
        return False
    ignored = set(evidence_paths)
    before_untracked = set(before["untracked"]) - ignored
    after_untracked = set(after["untracked"]) - ignored
    return before_untracked == after_untracked


def _capture_baseline(out_path: Path) -> int:
    recorder = CommandRecorder(Path.cwd().resolve())
    try:
        repo = _repo_root(recorder)
        git_metadata_roots = _git_metadata_roots(recorder, repo)
        before = _snapshot(recorder, repo)
        _validate_output_path(
            out_path,
            repo=repo,
            snapshot=before,
            evidence_paths=None,
            forbidden_paths=(Path(__file__).resolve(),),
            forbidden_roots=git_metadata_roots,
        )
        collected = _collect_nodeids(recorder)
        pytest_exit, outcomes = _run_pytest(recorder, collected)
        after = _snapshot(recorder, repo)
        if not _snapshot_stable(before, after):
            raise MeasurementError("repository changed during baseline capture")
        if (
            pytest_exit != 0
            or outcomes["counts"]["failed"]
            or outcomes["counts"]["errors"]
        ):
            raise MeasurementError("baseline pytest is not GREEN")

        dirty_or_staged = sorted(
            set(before["dirty_paths"]) | set(before["staged_paths"])
        )
        worktree: dict[str, dict[str, str | None]] = {}
        for path in dirty_or_staged:
            index_entry = before["index_entries"].get(path)
            worktree[path] = {
                "worktree_blob": _worktree_blob(recorder, repo, path),
                "index_blob": index_entry["oid"]
                if path in before["staged_paths"] and index_entry
                else None,
                "head_blob": before["head_tree"].get(path),
            }

        baseline = {
            "schema_version": SCHEMA_VERSION,
            "tool": {"verifier_sha256": _verifier_oid(recorder)},
            "git": {
                "head_sha": before["head_sha"],
                "upstream_sha": before["upstream_sha"],
                "ahead": before["ahead"],
                "behind": before["behind"],
            },
            "worktree": worktree,
            "index_fingerprint": before["index_fingerprint"],
            "untracked": before["untracked"],
            "pytest": outcomes,
            "collect_nodeids": collected,
        }
        _atomic_write_json(out_path, baseline)
        print(_sha256_bytes(out_path.read_bytes()))
        return 0
    except InputInvalid as exc:
        print(f"capture-baseline failed: {exc}", file=sys.stderr)
        return 2
    except MeasurementError as exc:
        print(f"capture-baseline failed: {exc}", file=sys.stderr)
        return 3


def _validate_baseline(baseline: dict[str, Any]) -> None:
    _require_exact_keys(
        baseline,
        (
            "schema_version",
            "tool",
            "git",
            "worktree",
            "index_fingerprint",
            "untracked",
            "pytest",
            "collect_nodeids",
        ),
        where="baseline",
    )
    if (
        type(baseline["schema_version"]) is not int
        or baseline["schema_version"] != SCHEMA_VERSION
    ):
        raise InputInvalid("baseline schema_version is unsupported")

    tool = baseline["tool"]
    if not isinstance(tool, dict):
        raise InputInvalid("baseline.tool must be an object")
    _require_exact_keys(tool, ("verifier_sha256",), where="baseline.tool")
    _require_oid(tool["verifier_sha256"], where="baseline.tool.verifier_sha256")

    git = baseline["git"]
    if not isinstance(git, dict):
        raise InputInvalid("baseline.git must be an object")
    _require_exact_keys(
        git,
        ("head_sha", "upstream_sha", "ahead", "behind"),
        where="baseline.git",
    )
    _require_oid(git["head_sha"], where="baseline.git.head_sha")
    _require_oid(git["upstream_sha"], where="baseline.git.upstream_sha")
    _require_int(git["ahead"], where="baseline.git.ahead")
    _require_int(git["behind"], where="baseline.git.behind")

    if not isinstance(baseline["worktree"], dict):
        raise InputInvalid("baseline.worktree must be an object")
    for path, state in baseline["worktree"].items():
        _validate_rel_path(path, where=f"baseline.worktree[{path!r}]")
        if not isinstance(state, dict):
            raise InputInvalid(f"baseline.worktree[{path!r}] must be an object")
        _require_exact_keys(
            state,
            ("worktree_blob", "index_blob", "head_blob"),
            where=f"baseline.worktree[{path!r}]",
        )
        for key in ("worktree_blob", "index_blob", "head_blob"):
            value = state[key]
            if value is not None:
                _require_oid(
                    value,
                    where=f"baseline.worktree[{path!r}].{key}",
                )

    fingerprint = _require_string(
        baseline["index_fingerprint"],
        where="baseline.index_fingerprint",
    )
    if not SHA256_RE.fullmatch(fingerprint):
        raise InputInvalid("baseline.index_fingerprint must be SHA-256")
    _require_sorted_unique_strings(baseline["untracked"], where="baseline.untracked")
    collected = _require_sorted_unique_strings(
        baseline["collect_nodeids"],
        where="baseline.collect_nodeids",
    )
    if not collected:
        raise InputInvalid("baseline.collect_nodeids must not be empty")

    pytest_data = baseline["pytest"]
    if not isinstance(pytest_data, dict):
        raise InputInvalid("baseline.pytest must be an object")
    _require_exact_keys(
        pytest_data,
        ("passed", "skipped", "xfailed", "counts"),
        where="baseline.pytest",
    )
    outcome_sets: dict[str, set[str]] = {}
    for key in ("passed", "skipped", "xfailed"):
        values = _require_sorted_unique_strings(
            pytest_data[key],
            where=f"baseline.pytest.{key}",
        )
        if not set(values).issubset(collected):
            raise InputInvalid(f"baseline.pytest.{key} contains unknown nodeids")
        outcome_sets[key] = set(values)
    if any(
        outcome_sets[left] & outcome_sets[right]
        for left, right in (("passed", "skipped"), ("passed", "xfailed"), ("skipped", "xfailed"))
    ):
        raise InputInvalid("baseline pytest outcomes overlap")
    counts = pytest_data["counts"]
    if not isinstance(counts, dict):
        raise InputInvalid("baseline.pytest.counts must be an object")
    _require_exact_keys(
        counts,
        ("passed", "skipped", "xfailed", "failed", "errors"),
        where="baseline.pytest.counts",
    )
    for key in counts:
        _require_int(counts[key], where=f"baseline.pytest.counts.{key}")
    for key in ("passed", "skipped", "xfailed"):
        if counts[key] != len(outcome_sets[key]):
            raise InputInvalid(f"baseline.pytest.counts.{key} is inconsistent")
    if counts["failed"] != 0 or counts["errors"] != 0:
        raise InputInvalid("baseline pytest must have zero failed/errors")
    if set().union(*outcome_sets.values()) != set(collected):
        raise InputInvalid("baseline pytest outcomes do not cover collected nodeids")


def _validate_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(
        capsule,
        (
            "schema_version",
            "capsule_id",
            "baseline_sha256",
            "head_sha",
            "verifier_sha256",
            "allowed_write_paths",
            "expected_new_nodeids",
            "removed_nodeids_allowed",
            "production_invariant",
            "pytest_min_passed",
            "evidence_paths",
        ),
        where="capsule",
    )
    if (
        type(capsule["schema_version"]) is not int
        or capsule["schema_version"] != SCHEMA_VERSION
    ):
        raise InputInvalid("capsule schema_version is unsupported")
    _require_string(capsule["capsule_id"], where="capsule.capsule_id")
    baseline_sha = _require_string(
        capsule["baseline_sha256"],
        where="capsule.baseline_sha256",
    )
    if not SHA256_RE.fullmatch(baseline_sha):
        raise InputInvalid("capsule.baseline_sha256 must be SHA-256")
    _require_oid(capsule["head_sha"], where="capsule.head_sha")
    _require_oid(capsule["verifier_sha256"], where="capsule.verifier_sha256")
    allowed = _validate_path_list(
        capsule["allowed_write_paths"],
        where="capsule.allowed_write_paths",
    )
    expected = _require_sorted_unique_strings(
        capsule["expected_new_nodeids"],
        where="capsule.expected_new_nodeids",
    )
    if capsule["removed_nodeids_allowed"] is not False:
        raise InputInvalid("capsule.removed_nodeids_allowed must be false")
    production = capsule["production_invariant"]
    if not isinstance(production, dict) or not production:
        raise InputInvalid("capsule.production_invariant must be non-empty")
    normalized_production: dict[str, str] = {}
    for path, oid in production.items():
        normalized_path = _validate_rel_path(
            path,
            where=f"capsule.production_invariant[{path!r}]",
        )
        normalized_production[normalized_path] = _require_oid(
            oid,
            where=f"capsule.production_invariant[{path!r}]",
        )
    evidence = _validate_path_list(
        capsule["evidence_paths"],
        where="capsule.evidence_paths",
        forbid_glob=True,
    )
    minimum = _require_int(
        capsule["pytest_min_passed"],
        where="capsule.pytest_min_passed",
    )
    overlaps = set(allowed) & set(evidence)
    if overlaps:
        raise InputInvalid(
            f"allowed_write_paths overlap evidence_paths: {sorted(overlaps)}"
        )
    return {
        **capsule,
        "allowed_write_paths": allowed,
        "expected_new_nodeids": expected,
        "production_invariant": dict(sorted(normalized_production.items())),
        "evidence_paths": evidence,
        "pytest_min_passed": minimum,
    }


def _empty_dod() -> list[dict[str, Any]]:
    return [
        {"id": check_id, "verdict": "NOT_RUN", "detail": {}}
        for check_id in CHECK_IDS
    ]


def _bundle_template() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "capsule_id": None,
        "verifier_exit": 3,
        "exit_reason": "INFRA_FAILURE",
        "steps": [],
        "files": {},
        "pytest": {
            "exit_code": None,
            "counts": {
                "passed": 0,
                "skipped": 0,
                "xfailed": 0,
                "failed": 0,
                "errors": 0,
            },
        },
        "nodeids": {"added": [], "removed": []},
        "workspace_delta": {
            "worktree_delta": [],
            "index_changed": False,
            "untracked_added": [],
            "untracked_removed": [],
        },
        "dod": _empty_dod(),
    }


def _set_dod(
    bundle: dict[str, Any],
    check_id: str,
    verdict: str,
    detail: dict[str, Any],
) -> None:
    for item in bundle["dod"]:
        if item["id"] == check_id:
            item["verdict"] = verdict
            item["detail"] = detail
            return
    raise AssertionError(f"unknown check id: {check_id}")


def _aggregate_dod_exit(dod: list[dict[str, Any]]) -> int:
    if len(dod) != len(CHECK_IDS):
        return 3
    if [item.get("id") for item in dod] != list(CHECK_IDS):
        return 3
    verdicts = [item.get("verdict") for item in dod]
    if all(verdict == "GREEN" for verdict in verdicts):
        return 0
    if all(verdict in {"GREEN", "RED"} for verdict in verdicts):
        return 1
    return 3


def _baseline_blob(
    baseline: dict[str, Any],
    head_tree: dict[str, str],
    path: str,
) -> str | None:
    state = baseline["worktree"].get(path)
    if state is not None:
        return state["worktree_blob"]
    return head_tree.get(path)


def _verify(
    baseline_path: Path,
    capsule_path: Path,
    out_path: Path,
) -> int:
    bundle = _bundle_template()
    recorder = CommandRecorder(Path.cwd().resolve())
    output_write_safe = False
    try:
        lexical_out = os.path.normcase(os.path.abspath(out_path))
        lexical_protected = {
            os.path.normcase(os.path.abspath(path))
            for path in (
                baseline_path,
                capsule_path,
                Path(__file__),
            )
        }
        if lexical_out in lexical_protected:
            raise InputInvalid("output path overlaps a protected input/tool path")

        repo = _repo_root(recorder)
        git_metadata_roots = _git_metadata_roots(recorder, repo)
        initial = _snapshot(recorder, repo)
        _validate_output_path(
            out_path,
            repo=repo,
            snapshot=initial,
            evidence_paths=None,
            forbidden_paths=(
                baseline_path,
                capsule_path,
                Path(__file__),
            ),
            forbidden_roots=git_metadata_roots,
        )
        output_write_safe = True
        actual_evidence_paths = {
            _require_repo_relative_path(
                baseline_path,
                repo=repo,
                where="baseline path",
            ),
            _require_repo_relative_path(
                capsule_path,
                repo=repo,
                where="capsule path",
            ),
            _require_repo_relative_path(
                out_path,
                repo=repo,
                where="output path",
            ),
        }
        if len(actual_evidence_paths) != 3:
            raise InputInvalid(
                "baseline, capsule, and output paths must be distinct"
            )

        capsule, capsule_raw = _load_json(capsule_path)
        if isinstance(capsule.get("capsule_id"), str):
            bundle["capsule_id"] = capsule["capsule_id"]
        capsule = _validate_capsule(capsule)
        if set(capsule["evidence_paths"]) != actual_evidence_paths:
            raise InputInvalid(
                "capsule.evidence_paths must exactly match "
                "baseline/capsule/output paths"
            )
        baseline, baseline_raw = _load_json(baseline_path)
        _validate_baseline(baseline)

        actual_baseline_sha = _sha256_bytes(baseline_raw)
        if actual_baseline_sha != capsule["baseline_sha256"]:
            raise InputInvalid("baseline_sha256 does not match baseline bytes")

        if (
            initial["head_sha"] != capsule["head_sha"]
            or initial["head_sha"] != baseline["git"]["head_sha"]
        ):
            raise InputInvalid("current HEAD does not match capsule/baseline")
        if (
            initial["upstream_sha"] != baseline["git"]["upstream_sha"]
            or initial["ahead"] != baseline["git"]["ahead"]
            or initial["behind"] != baseline["git"]["behind"]
        ):
            raise InputInvalid(
                "current upstream/ahead/behind do not match baseline"
            )
        current_verifier_oid = _verifier_oid(recorder)
        if (
            current_verifier_oid != capsule["verifier_sha256"]
            or current_verifier_oid != baseline["tool"]["verifier_sha256"]
        ):
            raise InputInvalid("verifier hash-object does not match capsule/baseline")
        _set_dod(
            bundle,
            "C0",
            "GREEN",
            {
                "baseline_sha256": actual_baseline_sha,
                "head_sha": initial["head_sha"],
                "verifier_sha256": current_verifier_oid,
            },
        )
        _atomic_write_json(out_path, bundle)

        collected = _collect_nodeids(recorder)
        pytest_exit, outcomes = _run_pytest(recorder, collected)
        final = _snapshot(recorder, repo)
        if not _snapshot_stable_ignoring_evidence(
            initial,
            final,
            capsule["evidence_paths"],
        ):
            raise MeasurementError(
                "repository changed while pytest verification was running"
            )
        if (
            final["head_sha"] != initial["head_sha"]
            or final["upstream_sha"] != initial["upstream_sha"]
            or final["ahead"] != initial["ahead"]
            or final["behind"] != initial["behind"]
        ):
            raise InputInvalid("Git identity changed during verification")
        try:
            if _sha256_bytes(baseline_path.read_bytes()) != actual_baseline_sha:
                raise InputInvalid("baseline bytes changed during verification")
            if _sha256_bytes(capsule_path.read_bytes()) != _sha256_bytes(capsule_raw):
                raise InputInvalid("capsule bytes changed during verification")
        except OSError as exc:
            raise InputInvalid("baseline/capsule became unreadable") from exc
        if _verifier_oid(recorder) != current_verifier_oid:
            raise InputInvalid("verifier bytes changed during verification")

        allowed = set(capsule["allowed_write_paths"])
        candidates = (
            set(baseline["worktree"])
            | set(initial["head_tree"])
            | set(initial["index_entries"])
            | set(final["index_entries"])
            | allowed
        )
        worktree_delta: list[str] = []
        blob_pairs: dict[str, tuple[str | None, str | None]] = {}
        for path in sorted(candidates):
            before_blob = _baseline_blob(baseline, initial["head_tree"], path)
            after_blob = final["tracked_blobs"].get(path)
            if path not in final["tracked_blobs"]:
                after_blob = _worktree_blob(recorder, repo, path)
            blob_pairs[path] = (before_blob, after_blob)
            if before_blob != after_blob:
                worktree_delta.append(path)
        files: dict[str, dict[str, str | None]] = {}
        reported_paths = (
            set(worktree_delta)
            | allowed
            | set(capsule["production_invariant"])
            | set(baseline["worktree"])
        )
        for path in sorted(reported_paths):
            before_blob, after_blob = blob_pairs.get(
                path,
                (
                    _baseline_blob(baseline, initial["head_tree"], path),
                    final["tracked_blobs"].get(path),
                ),
            )
            files[path] = {
                "blob_before": before_blob,
                "blob_after": after_blob,
            }
        index_changed = (
            final["index_fingerprint"] != baseline["index_fingerprint"]
        )
        bundle["files"] = files
        bundle["workspace_delta"]["worktree_delta"] = worktree_delta
        bundle["workspace_delta"]["index_changed"] = index_changed
        c1_green = set(worktree_delta) == allowed and not index_changed
        _set_dod(
            bundle,
            "C1",
            "GREEN" if c1_green else "RED",
            {
                "expected": sorted(allowed),
                "observed": worktree_delta,
                "missing": sorted(allowed - set(worktree_delta)),
                "unexpected": sorted(set(worktree_delta) - allowed),
                "index_changed": index_changed,
            },
        )

        baseline_untracked = set(baseline["untracked"])
        current_untracked = set(final["untracked"])
        evidence = set(capsule["evidence_paths"])
        untracked_added = sorted(
            current_untracked - baseline_untracked - evidence
        )
        untracked_removed = sorted(baseline_untracked - current_untracked)
        bundle["workspace_delta"]["untracked_added"] = untracked_added
        bundle["workspace_delta"]["untracked_removed"] = untracked_removed
        c2_green = not untracked_added and not untracked_removed
        _set_dod(
            bundle,
            "C2",
            "GREEN" if c2_green else "RED",
            {
                "added": untracked_added,
                "removed": untracked_removed,
                "evidence_paths": sorted(evidence),
            },
        )

        baseline_nodeids = set(baseline["collect_nodeids"])
        current_nodeids = set(collected)
        added_nodeids = sorted(current_nodeids - baseline_nodeids)
        removed_nodeids = sorted(baseline_nodeids - current_nodeids)
        bundle["nodeids"]["added"] = added_nodeids
        bundle["nodeids"]["removed"] = removed_nodeids
        expected_new = set(capsule["expected_new_nodeids"])
        c3_green = set(added_nodeids) == expected_new and not removed_nodeids
        _set_dod(
            bundle,
            "C3",
            "GREEN" if c3_green else "RED",
            {
                "expected_added": sorted(expected_new),
                "added": added_nodeids,
                "removed": removed_nodeids,
            },
        )

        bundle["pytest"] = {
            "exit_code": pytest_exit,
            "counts": outcomes["counts"],
        }
        passed_now = set(outcomes["passed"])
        baseline_passed = set(baseline["pytest"]["passed"])
        new_skips = sorted(
            set(outcomes["skipped"]) - set(baseline["pytest"]["skipped"])
        )
        new_xfails = sorted(
            set(outcomes["xfailed"]) - set(baseline["pytest"]["xfailed"])
        )
        missing_baseline_passes = sorted(baseline_passed - passed_now)
        expected_not_passed = sorted(expected_new - passed_now)
        c4_green = (
            pytest_exit == 0
            and outcomes["counts"]["failed"] == 0
            and outcomes["counts"]["errors"] == 0
            and not missing_baseline_passes
            and not new_skips
            and not new_xfails
            and not expected_not_passed
            and outcomes["counts"]["passed"] >= capsule["pytest_min_passed"]
        )
        _set_dod(
            bundle,
            "C4",
            "GREEN" if c4_green else "RED",
            {
                "pytest_exit": pytest_exit,
                "missing_baseline_passes": missing_baseline_passes,
                "new_skipped": new_skips,
                "new_xfailed": new_xfails,
                "expected_not_passed": expected_not_passed,
                "passed": outcomes["counts"]["passed"],
                "minimum_passed": capsule["pytest_min_passed"],
            },
        )

        mismatches: list[dict[str, Any]] = []
        for path, expected_oid in capsule["production_invariant"].items():
            observed_oid = final["tracked_blobs"].get(path)
            if path not in final["tracked_blobs"]:
                observed_oid = _worktree_blob(recorder, repo, path)
            if observed_oid != expected_oid:
                mismatches.append(
                    {
                        "path": path,
                        "expected": expected_oid,
                        "observed": observed_oid,
                    }
                )
        _set_dod(
            bundle,
            "C5",
            "GREEN" if not mismatches else "RED",
            {"mismatches": mismatches},
        )

        terminal = _snapshot(recorder, repo)
        if not _snapshot_stable(final, terminal):
            raise MeasurementError("repository changed while checks were evaluated")

        exit_code = _aggregate_dod_exit(bundle["dod"])
        bundle["verifier_exit"] = exit_code
        if exit_code == 0:
            bundle["exit_reason"] = "GREEN"
        elif exit_code == 1:
            bundle["exit_reason"] = "DOD_RED"
        else:
            bundle["exit_reason"] = "INFRA_FAILURE: incomplete DoD evaluation"
    except InputInvalid as exc:
        bundle["verifier_exit"] = 2
        bundle["exit_reason"] = f"INPUT_INVALID: {exc}"
        _set_dod(bundle, "C0", "RED", {"reason": str(exc)})
        exit_code = 2
    except MeasurementError as exc:
        bundle["verifier_exit"] = 3
        bundle["exit_reason"] = f"INFRA_FAILURE: {exc}"
        if next(item for item in bundle["dod"] if item["id"] == "C0")[
            "verdict"
        ] == "NOT_RUN":
            _set_dod(bundle, "C0", "ERROR", {"reason": str(exc)})
        exit_code = 3
    except Exception as exc:  # fail closed on unexpected implementation errors
        bundle["verifier_exit"] = 3
        bundle["exit_reason"] = (
            f"INFRA_FAILURE: unexpected {type(exc).__name__}"
        )
        if next(item for item in bundle["dod"] if item["id"] == "C0")[
            "verdict"
        ] == "NOT_RUN":
            _set_dod(
                bundle,
                "C0",
                "ERROR",
                {"reason": f"unexpected {type(exc).__name__}"},
            )
        exit_code = 3

    bundle["steps"] = recorder.steps
    if not output_write_safe:
        print(
            f"verify refused unsafe output path: {out_path}",
            file=sys.stderr,
        )
        return exit_code
    try:
        _atomic_write_json(out_path, bundle)
    except MeasurementError as exc:
        print(f"verify failed: {exc}", file=sys.stderr)
        return 3
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="baseline-bound evidence verifier")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    capture = subparsers.add_parser("capture-baseline")
    capture.add_argument("--out", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--baseline", required=True)
    verify.add_argument("--capsule", required=True)
    verify.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.mode == "capture-baseline":
        return _capture_baseline(Path(args.out))
    return _verify(
        Path(args.baseline),
        Path(args.capsule),
        Path(args.out),
    )


if __name__ == "__main__":
    raise SystemExit(main())
