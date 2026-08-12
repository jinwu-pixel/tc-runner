#!/usr/bin/env python3
"""Freeze canonical rc-sensitive targets from current HEAD or an exact commit.

This host-only census includes both ``shell`` and ``verify_shell`` actions.  It
deliberately does not classify whether a command is expected to return a
non-zero exit code; that semantic review is a separate follow-up gate.  The
optional ``--head`` path replays a full immutable commit SHA after HEAD moves.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.cli import host_preflight  # noqa: E402


SCHEMA_VERSION = "canonical-shell-rc-inventory-v3"
TOOL_VERSION = "3"
CSV_FIELDS = (
    "schema_version",
    "head_sha",
    "row_key",
    "source_path",
    "source_blob",
    "tc_name",
    "step_index",
    "action",
    "command",
    "command_sha256",
    "expected",
    "timeout_ms",
    "execution_mode",
    "dispatch_route",
)
MANUAL_EXECUTION_MODES = frozenset({"MANUAL_REQUIRED", "EXTERNAL_EVENT"})
RUNTIME_INPUT_PATHS = (
    "src/adb.py",
    "src/action_runner.py",
    "src/cli.py",
    "src/tc_loader.py",
    "src/execution_contract.py",
    "tc_step_schema.json",
)


class AuditInputError(ValueError):
    """The requested repository snapshot cannot form a valid inventory."""


class AuditInfraError(RuntimeError):
    """Git, filesystem, or an internal invariant prevented measurement."""


@dataclass(frozen=True)
class HeadYamlBlob:
    path: str
    blob_oid: str
    data: bytes


@dataclass(frozen=True)
class PreflightObservation:
    passed: bool
    tc_data: Mapping[str, object] | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class InventoryReport:
    head_sha: str
    rows: tuple[dict[str, object], ...]
    summary: dict[str, int]
    rejection_reason_counts: dict[str, int]


def _run_git_bytes(repo: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"")
        if isinstance(stderr, bytes):
            detail = stderr.decode("utf-8", errors="replace").strip()
        else:
            detail = str(stderr).strip()
        suffix = f": {detail}" if detail else ""
        raise AuditInfraError(f"git {' '.join(args)} failed{suffix}") from exc
    return result.stdout


def resolve_head(repo: Path) -> str:
    raw = _run_git_bytes(repo, "rev-parse", "--verify", "HEAD").strip()
    try:
        head = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditInfraError("git returned a non-ASCII HEAD") from exc
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise AuditInfraError(f"git returned an invalid full HEAD: {head!r}")
    return head


def resolve_commit(repo: Path, revision: str) -> str:
    """Resolve an exact full lowercase commit SHA without following HEAD."""
    if (
        len(revision) != 40
        or any(char not in "0123456789abcdef" for char in revision)
    ):
        raise AuditInputError(
            "explicit --head must be a full lowercase 40-character SHA"
        )
    raw = _run_git_bytes(
        repo,
        "rev-parse",
        "--verify",
        f"{revision}^{{commit}}",
    ).strip()
    try:
        resolved = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditInfraError(
            "git returned a non-ASCII explicit commit"
        ) from exc
    if resolved != revision:
        raise AuditInputError(
            "explicit --head did not resolve to the exact requested commit"
        )
    return resolved


def snapshot_runtime_inputs(repo: Path) -> dict[str, str]:
    """Hash worktree actors that define canonical host-preflight behavior."""
    hashes: dict[str, str] = {}
    for relative in RUNTIME_INPUT_PATHS:
        path = repo.joinpath(*PurePosixPath(relative).parts)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise AuditInfraError(
                f"unable to read runtime input {relative}: {exc}"
            ) from exc
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return hashes


def _head_yaml_tree(repo: Path, head_sha: str) -> dict[str, str]:
    raw = _run_git_bytes(
        repo,
        "ls-tree",
        "-rz",
        "--full-tree",
        head_sha,
    )
    paths: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, path_bytes = record.split(b"\t", 1)
            _mode, object_type, oid = header.split(b" ", 2)
            path = path_bytes.decode("utf-8")
            oid_text = oid.decode("ascii")
        except (ValueError, UnicodeDecodeError) as exc:
            raise AuditInfraError("unable to decode git ls-tree output") from exc
        if object_type != b"blob":
            continue
        if PurePosixPath(path).suffix.lower() not in {".yaml", ".yml"}:
            continue
        if PurePosixPath(path).parts[0] == "provenance":
            continue
        if path in paths:
            raise AuditInfraError(f"duplicate YAML path in HEAD tree: {path}")
        paths[path] = oid_text
    if not paths:
        raise AuditInputError("HEAD contains no tracked YAML files")
    return paths


def read_head_yaml_blobs(
    repo: Path,
    head_sha: str,
) -> tuple[HeadYamlBlob, ...]:
    """Read tracked YAML bytes from HEAD, never from the current worktree."""
    tree = _head_yaml_tree(repo, head_sha)
    ordered = tuple(sorted(tree.items()))
    request = b"".join(
        oid.encode("ascii") + b"\n" for _path, oid in ordered
    )
    try:
        result = subprocess.run(
            ["git", "cat-file", "--batch"],
            cwd=repo,
            input=request,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"")
        detail = (
            stderr.decode("utf-8", errors="replace").strip()
            if isinstance(stderr, bytes)
            else str(stderr).strip()
        )
        suffix = f": {detail}" if detail else ""
        raise AuditInfraError(f"git cat-file --batch failed{suffix}") from exc

    output = result.stdout
    offset = 0
    blobs: list[HeadYamlBlob] = []
    for path, expected_oid in ordered:
        header_end = output.find(b"\n", offset)
        if header_end < 0:
            raise AuditInfraError(
                f"git cat-file omitted header for {path}"
            )
        header = output[offset:header_end]
        try:
            actual_oid_raw, object_type, size_raw = header.split(b" ", 2)
            actual_oid = actual_oid_raw.decode("ascii")
            size = int(size_raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise AuditInfraError(
                f"invalid git cat-file header for {path}: {header!r}"
            ) from exc
        if actual_oid != expected_oid or object_type != b"blob":
            raise AuditInfraError(
                f"git cat-file identity mismatch for {path}"
            )
        data_start = header_end + 1
        data_end = data_start + size
        if data_end >= len(output) or output[data_end : data_end + 1] != b"\n":
            raise AuditInfraError(
                f"git cat-file truncated blob for {path}"
            )
        blobs.append(
            HeadYamlBlob(
                path=path,
                blob_oid=expected_oid,
                data=output[data_start:data_end],
            )
        )
        offset = data_end + 1
    if offset != len(output):
        raise AuditInfraError("git cat-file returned trailing output")
    return tuple(blobs)


def _parse_yaml_document(blob: HeadYamlBlob) -> object:
    try:
        text = blob.data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AuditInputError(f"{blob.path}: YAML is not UTF-8") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AuditInputError(f"{blob.path}: invalid YAML: {exc}") from exc


def parse_yaml_mapping(blob: HeadYamlBlob) -> dict[str, object]:
    document = _parse_yaml_document(blob)
    if not isinstance(document, dict):
        raise AuditInputError(
            f"{blob.path}: YAML root must be a mapping, "
            f"got {type(document).__name__}"
        )
    return document


def _raw_runnable_rc_candidate(document: Mapping[str, object]) -> bool:
    metadata = document.get("metadata")
    if not isinstance(metadata, Mapping):
        return False
    if metadata.get("runnable") is not True:
        return False
    steps = document.get("steps")
    return isinstance(steps, list) and any(
        isinstance(step, Mapping)
        and step.get("action") in {"shell", "verify_shell"}
        for step in steps
    )


def _rejection_reason_code(reason: str) -> str:
    if reason.startswith("CANONICAL_LOAD_OR_VALIDATION_ERROR:"):
        return ":".join(reason.split(":", 2)[:2])
    return reason


def _command_text(command: object, source_path: str, step_index: int) -> str:
    if not isinstance(command, str):
        raise AuditInputError(
            f"{source_path}: canonical shell step {step_index} "
            "has a non-string command"
        )
    return command


def _verify_shell_contract_fields(
    step: Mapping[str, object],
    source_path: str,
    step_index: int,
) -> tuple[str, int | float]:
    expected = step.get("expected")
    if not isinstance(expected, str):
        raise AuditInputError(
            f"{source_path}: canonical verify_shell step {step_index} "
            "has a non-string expected value"
        )
    timeout_ms = step.get("timeout", 30000)
    if (
        isinstance(timeout_ms, bool)
        or not isinstance(timeout_ms, (int, float))
        or not math.isfinite(timeout_ms)
        or timeout_ms < 0
    ):
        raise AuditInputError(
            f"{source_path}: canonical verify_shell step {step_index} "
            "has an invalid timeout"
        )
    return expected, timeout_ms


def build_inventory_from_blobs(
    head_sha: str,
    blobs: Sequence[HeadYamlBlob],
    preflight: Callable[[HeadYamlBlob], PreflightObservation],
) -> InventoryReport:
    parsed = tuple(
        (blob, document)
        for blob in blobs
        if isinstance((document := _parse_yaml_document(blob)), dict)
    )
    candidates = tuple(
        blob
        for blob, document in parsed
        if _raw_runnable_rc_candidate(document)
    )

    rows: list[dict[str, object]] = []
    rejection_reasons: Counter[str] = Counter()
    passed_files = 0
    action_shell_files = 0
    action_shell_steps = 0
    verify_shell_files = 0
    verify_shell_steps = 0

    for blob in candidates:
        observation = preflight(blob)
        if not observation.passed:
            if not observation.reasons:
                raise AuditInfraError(
                    f"{blob.path}: rejected preflight has no reason"
                )
            rejection_reasons.update(
                _rejection_reason_code(reason)
                for reason in observation.reasons
            )
            continue
        if not isinstance(observation.tc_data, Mapping):
            raise AuditInfraError(
                f"{blob.path}: passing preflight returned no TC mapping"
            )

        passed_files += 1
        tc_data = observation.tc_data
        tc_name_value = tc_data.get("name", tc_data.get("tc_name", ""))
        tc_name = (
            tc_name_value
            if isinstance(tc_name_value, str)
            else json.dumps(
                tc_name_value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        steps = tc_data.get("steps")
        if not isinstance(steps, list):
            raise AuditInfraError(
                f"{blob.path}: passing canonical TC has no step list"
            )

        file_action_shell_steps = 0
        file_verify_shell_steps = 0
        for step_index, step in enumerate(steps, start=1):
            if not isinstance(step, Mapping):
                raise AuditInfraError(
                    f"{blob.path}: canonical step {step_index} is not a mapping"
                )
            action = step.get("action")
            if action not in {"shell", "verify_shell"}:
                continue

            command = _command_text(
                step.get("command"),
                blob.path,
                step_index,
            )
            if action == "verify_shell":
                expected, timeout_ms = _verify_shell_contract_fields(
                    step,
                    blob.path,
                    step_index,
                )
                file_verify_shell_steps += 1
            else:
                expected = ""
                timeout_ms = ""
                file_action_shell_steps += 1
            execution_mode_value = step.get("execution_mode", "")
            execution_mode = (
                execution_mode_value
                if isinstance(execution_mode_value, str)
                else str(execution_mode_value)
            )
            dispatch_route = (
                "MANUAL_PAUSE"
                if execution_mode in MANUAL_EXECUTION_MODES
                else "RUNNER_SHELL"
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "head_sha": head_sha,
                    "row_key": f"{head_sha}:{blob.path}#{step_index}",
                    "source_path": blob.path,
                    "source_blob": blob.blob_oid,
                    "tc_name": tc_name,
                    "step_index": step_index,
                    "action": action,
                    "command": command,
                    "command_sha256": hashlib.sha256(
                        command.encode("utf-8")
                    ).hexdigest(),
                    "expected": expected,
                    "timeout_ms": timeout_ms,
                    "execution_mode": execution_mode,
                    "dispatch_route": dispatch_route,
                }
            )
        if file_action_shell_steps:
            action_shell_files += 1
            action_shell_steps += file_action_shell_steps
        if file_verify_shell_steps:
            verify_shell_files += 1
            verify_shell_steps += file_verify_shell_steps

    rows.sort(key=lambda row: (str(row["source_path"]), int(row["step_index"])))
    runner_rows = sum(
        row["dispatch_route"] == "RUNNER_SHELL" for row in rows
    )
    manual_rows = sum(
        row["dispatch_route"] == "MANUAL_PAUSE" for row in rows
    )
    summary = {
        "tracked_yaml_files": len(blobs),
        "raw_runnable_rc_files": len(candidates),
        "canonical_preflight_pass_files": passed_files,
        "canonical_preflight_reject_files": len(candidates) - passed_files,
        "inventory_rc_steps": len(rows),
        "runner_dispatched_rc_steps": runner_rows,
        "manual_routed_rc_steps": manual_rows,
        "action_shell_files": action_shell_files,
        "action_shell_steps": action_shell_steps,
        "verify_shell_files": verify_shell_files,
        "verify_shell_steps": verify_shell_steps,
    }
    report = InventoryReport(
        head_sha=head_sha,
        rows=tuple(rows),
        summary=summary,
        rejection_reason_counts=dict(sorted(rejection_reasons.items())),
    )
    _self_check(report)
    return report


def _self_check(report: InventoryReport) -> None:
    summary = report.summary
    if (
        summary["canonical_preflight_pass_files"]
        + summary["canonical_preflight_reject_files"]
        != summary["raw_runnable_rc_files"]
    ):
        raise AuditInfraError("preflight file counts are inconsistent")
    if (
        summary["runner_dispatched_rc_steps"]
        + summary["manual_routed_rc_steps"]
        != summary["inventory_rc_steps"]
    ):
        raise AuditInfraError("rc-sensitive dispatch counts are inconsistent")
    if len(report.rows) != summary["inventory_rc_steps"]:
        raise AuditInfraError("CSV row count is inconsistent")
    if (
        summary["action_shell_steps"] + summary["verify_shell_steps"]
        != summary["inventory_rc_steps"]
    ):
        raise AuditInfraError("action counts are inconsistent")
    row_keys = [str(row["row_key"]) for row in report.rows]
    if len(row_keys) != len(set(row_keys)):
        raise AuditInfraError("duplicate inventory row_key")
    if any(
        row["dispatch_route"] not in {"RUNNER_SHELL", "MANUAL_PAUSE"}
        for row in report.rows
    ):
        raise AuditInfraError("unknown rc-sensitive dispatch route")
    if any(
        row["action"] not in {"shell", "verify_shell"}
        for row in report.rows
    ):
        raise AuditInfraError("unknown rc-sensitive action")
    if (
        sum(report.rejection_reason_counts.values())
        < summary["canonical_preflight_reject_files"]
    ):
        raise AuditInfraError("rejection reason counts are incomplete")


def _sanitize_reason(
    reason: str,
    temporary_path: Path,
    source_path: str,
    temporary_root: Path,
) -> str:
    return (
        reason.replace(str(temporary_path), source_path)
        .replace(temporary_path.as_posix(), source_path)
        .replace(str(temporary_root), "<TEMP>")
        .replace(temporary_root.as_posix(), "<TEMP>")
    )


def collect_inventory(
    repo: Path,
    *,
    head_sha: str | None = None,
) -> InventoryReport:
    repo = Path(repo).resolve()
    if head_sha is None:
        head_sha = resolve_head(repo)
    else:
        head_sha = resolve_commit(repo, head_sha)
    blobs = read_head_yaml_blobs(repo, head_sha)

    with tempfile.TemporaryDirectory(
        prefix="tc-runner-shell-audit-"
    ) as temporary:
        temporary_root = Path(temporary)
        path_by_source: dict[str, Path] = {}

        def run_preflight(blob: HeadYamlBlob) -> PreflightObservation:
            temporary_path = path_by_source.get(blob.path)
            if temporary_path is None:
                suffix = PurePosixPath(blob.path).suffix or ".yaml"
                temporary_path = (
                    temporary_root / f"{len(path_by_source):06d}{suffix}"
                )
                temporary_path.write_bytes(blob.data)
                path_by_source[blob.path] = temporary_path

            preflight_report = host_preflight(
                (temporary_path,),
                "canonical",
            )
            if len(preflight_report.verdicts) != 1:
                raise AuditInfraError(
                    f"{blob.path}: host_preflight returned "
                    f"{len(preflight_report.verdicts)} verdicts"
                )
            verdict = preflight_report.verdicts[0]
            reasons = tuple(
                _sanitize_reason(
                    reason,
                    temporary_path,
                    blob.path,
                    temporary_root,
                )
                for reason in verdict.reasons
            )
            return PreflightObservation(
                passed=verdict.passed,
                tc_data=verdict.tc_data,
                reasons=reasons,
            )

        return build_inventory_from_blobs(
            head_sha,
            blobs,
            run_preflight,
        )


def _csv_bytes(rows: Sequence[Mapping[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def render_artifacts(
    report: InventoryReport,
    *,
    input_digest: str,
    tool_sha256: str,
    runtime_input_sha256: Mapping[str, str],
) -> tuple[bytes, bytes]:
    _self_check(report)
    csv_bytes = _csv_bytes(report.rows)
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()

    lines = [
        "# Canonical Shell RC Inventory",
        "",
        f"- Schema version: `{SCHEMA_VERSION}`",
        f"- Tool version: `{TOOL_VERSION}`",
        f"- HEAD: `{report.head_sha}`",
        f"- Input digest: `{input_digest}`",
        f"- Tool SHA-256: `{tool_sha256}`",
        f"- CSV SHA-256: `{csv_sha256}`",
        "- Target scope: tracked HEAD YAML with `metadata.runnable: true`, "
        "at least one raw rc-sensitive action, and passing canonical "
        "preflight.",
        "- CSV actions: `action: shell` and `action: verify_shell`; "
        "`verify_shell` rows freeze `expected` and effective `timeout_ms`.",
        "",
        "## Runtime input SHA-256",
        "",
    ]
    for path, digest in sorted(runtime_input_sha256.items()):
        lines.append(f"- `{path}`: `{digest}`")
    lines.extend(
        [
        "",
        "## Counts",
        "",
        ]
    )
    for key, value in report.summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Canonical preflight rejection reasons",
            "",
        ]
    )
    if report.rejection_reason_counts:
        for reason, count in report.rejection_reason_counts.items():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- none")
    lines.append("")
    return csv_bytes, "\n".join(lines).encode("utf-8")


def _tool_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _input_digest(
    head_sha: str,
    tool_sha256: str,
    runtime_input_sha256: Mapping[str, str],
) -> str:
    parts = [SCHEMA_VERSION, TOOL_VERSION, head_sha, tool_sha256]
    parts.extend(
        f"{path}\0{digest}"
        for path, digest in sorted(runtime_input_sha256.items())
    )
    parts.append("")
    material = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _write_artifacts(
    output_root: Path,
    input_digest: str,
    csv_bytes: bytes,
    summary_bytes: bytes,
    *,
    state_check: Callable[[], None] | None = None,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / input_digest[:16]
    expected = {
        "shell_rc_inventory.csv": csv_bytes,
        "SUMMARY.md": summary_bytes,
    }
    if destination.exists():
        try:
            entries = {
                entry.name
                for entry in destination.iterdir()
            }
            if entries != set(expected):
                raise AuditInfraError(
                    f"existing destination entry set differs: {destination}"
                )
            observed = {
                name: (destination / name).read_bytes()
                for name in expected
            }
        except OSError as exc:
            raise AuditInfraError(
                f"existing destination is incomplete: {destination}"
            ) from exc
        if observed != expected:
            raise AuditInfraError(
                f"existing destination bytes differ: {destination}"
            )
        if state_check is not None:
            state_check()
        return destination

    published = False
    with tempfile.TemporaryDirectory(
        prefix=".canonical-shell-rc-",
        dir=output_root,
    ) as temporary:
        temporary_root = Path(temporary)
        staged = temporary_root / destination.name
        staged.mkdir()
        for name, data in expected.items():
            (staged / name).write_bytes(data)
        observed_staged = {
            name: (staged / name).read_bytes()
            for name in expected
        }
        if observed_staged != expected:
            raise AuditInfraError("staged artifact readback mismatch")
        if state_check is not None:
            state_check()
        os.replace(staged, destination)
        published = True
        try:
            if state_check is not None:
                state_check()
        except Exception:
            if published and destination.exists():
                shutil.rmtree(destination)
            raise
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--head",
        help=(
            "replay an exact full 40-character commit SHA instead of "
            "the current HEAD"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "canonical_shell_rc_audit",
        help="artifact root",
    )
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="repeat the complete measurement and require byte identity",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo = REPO_ROOT.resolve()
    try:
        start_worktree_head = resolve_head(repo)
        measurement_head = (
            resolve_commit(repo, args.head)
            if args.head is not None
            else start_worktree_head
        )
        start_tool_sha = _tool_sha256()
        start_runtime_inputs = snapshot_runtime_inputs(repo)
        input_digest = _input_digest(
            measurement_head,
            start_tool_sha,
            start_runtime_inputs,
        )

        first_report = collect_inventory(repo, head_sha=measurement_head)
        if first_report.head_sha != measurement_head:
            raise AuditInfraError(
                "measurement commit changed before measurement"
            )
        first_artifacts = render_artifacts(
            first_report,
            input_digest=input_digest,
            tool_sha256=start_tool_sha,
            runtime_input_sha256=start_runtime_inputs,
        )

        if args.verify_determinism:
            second_report = collect_inventory(
                repo,
                head_sha=measurement_head,
            )
            second_artifacts = render_artifacts(
                second_report,
                input_digest=input_digest,
                tool_sha256=start_tool_sha,
                runtime_input_sha256=start_runtime_inputs,
            )
            if second_report != first_report:
                raise AuditInfraError(
                    "determinism verification report mismatch"
                )
            if second_artifacts != first_artifacts:
                raise AuditInfraError(
                    "determinism verification byte mismatch"
                )

        def state_check() -> None:
            if resolve_head(repo) != start_worktree_head:
                raise AuditInfraError("HEAD changed during measurement")
            if _tool_sha256() != start_tool_sha:
                raise AuditInfraError("tool changed during measurement")
            if snapshot_runtime_inputs(repo) != start_runtime_inputs:
                raise AuditInfraError(
                    "runtime inputs changed during measurement"
                )

        state_check()

        destination = _write_artifacts(
            args.out_dir.resolve(),
            input_digest,
            *first_artifacts,
            state_check=state_check,
        )
    except AuditInputError as exc:
        print(f"INPUT INVALID: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"INFRA FAILURE: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 3

    print(f"inventory: {destination}")
    print(f"rows: {first_report.summary['inventory_rc_steps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
