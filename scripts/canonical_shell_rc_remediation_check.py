from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

import yaml


class InputInvalid(ValueError):
    """The caller supplied data outside the closed remediation contract."""


class InfrastructureFailure(RuntimeError):
    """A host or publication operation failed."""


ROOT_KEYS = {
    "schema_version",
    "subject",
    "baseline",
    "targets",
    "runtime_review_dispositions",
    "semantic_identity",
}
BASELINE_KEYS = {
    "inventory_head",
    "inventory_csv_sha256",
    "risk_matrix_sha256",
    "risk_policy_sha256",
    "p2_manifest_pre_remediation_head",
    "p2_manifest_pre_remediation_sha256",
    "p2_evidence_sha256",
}
TARGET_KEYS = {
    "row_key",
    "source_path",
    "step_index",
    "baseline_action",
    "baseline_command",
    "baseline_command_sha256",
    "classification",
    "renderer_kind",
    "source_command",
    "grep_pattern",
    "predicate_kind",
    "predicate_value",
    "sentinel",
    "timeout_policy",
    "provenance",
}
PROVENANCE_KEYS = {"mode", "yaml_path", "source_no"}
RUNTIME_KEYS = {"row_key", "disposition"}
SEMANTIC_KEYS = {
    "targets_sha256",
    "runtime_review_dispositions_sha256",
}
LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LOWER_OID_RE = re.compile(r"^[0-9a-f]{40}$")
INVARIANT_SCOPE_VERSION = 1
VERIFIER_OWNED_INVARIANT_SCOPE_VERSION = 2
VERIFIER_OWNED_IGNORED_PREFIXES = (
    "reports/canonical_shell_rc_remediation/",
)
TARGET_ROW_KEYS = [
    "ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml#24",
    "ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml#11",
    "exported_ss_call/SS_TC01_permission_denied.yaml#10",
    "exported_ss_call/SS_TC01_permission_denied.yaml#11",
    "exported_ss_call/SS_TC02_permission_allow_idle.yaml#11",
    "exported_ss_call/SS_TC03_ringing_permission.yaml#15",
    "exported_ss_call/SS_TC04_offhook_seed_recovery.yaml#18",
    "exported_ss_call/SS_TC05_boundary_values.yaml#9",
    "exported_ss_call/SS_TC06_missed_rejected.yaml#10",
    "exported_ss_call/SS_TC06_missed_rejected.yaml#11",
    "exported_ss_call/SS_TC07_short_call_no_false_positive.yaml#9",
    "exported_ss_call/SS_TC09_offhook_permission_banking.yaml#20",
    "exported_ss_call/SS_TC0_P0_endcall_crash.yaml#15",
    "exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml#24",
    "exported_ss_call/SS_TC10_permission_toggle.yaml#24",
    "exported_ss_call/SS_TC11_multi_subscription.yaml#20",
    "exported_ss_call/SS_TC11_multi_subscription.yaml#21",
    "exported_ss_call/SS_TC12_legacy_path.yaml#19",
]
EXPECTED_BASELINE = {
    "inventory_head": "78b3ac34e9f8bacabe926172dd199342b7eb58c5",
    "inventory_csv_sha256": (
        "b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f"
    ),
    "risk_matrix_sha256": (
        "81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4"
    ),
    "risk_policy_sha256": (
        "f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed"
    ),
    "p2_manifest_pre_remediation_head": (
        "4c484d53e4227933b43fffad3f1846435a70c995"
    ),
    "p2_manifest_pre_remediation_sha256": (
        "b4544cf636bf7be22fc9ba0a05c0b217c35710eceb92db9994e28ce0b3d88e3c"
    ),
    "p2_evidence_sha256": (
        "f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a"
    ),
}
EXPECTED_RUNTIME = [
    {
        "row_key": (
            "ODIN2 - My gallary/functional/photo/"
            "GAL_FUNC_05_photo_multi_delete_trash_flow.yaml#23"
        ),
        "disposition": "STATIC_ADJUDICATED_REQUIRE_ZERO",
    },
    {
        "row_key": (
            "ODIN2 - My gallary/functional/photo/"
            "GAL_FUNC_12_photo_edit_save_copy.yaml#18"
        ),
        "disposition": "STATIC_ADJUDICATED_REQUIRE_ZERO",
    },
    {
        "row_key": (
            "ODIN2 - My gallary/functional/video/"
            "GAL_FUNC_16_video_orientation.yaml#8"
        ),
        "disposition": "STATIC_ADJUDICATED_OBSERVE_ONLY",
    },
    {
        "row_key": (
            "ODIN2 - minifile/functional/ops/"
            "MNF_FUNC_12_ops_rename.yaml#22"
        ),
        "disposition": "CORPUS_DESIGN_REQUIRED",
    },
    {
        "row_key": "exported_tc1/BUG_25175_LGU_APN_menu.yaml#75",
        "disposition": "DEVICE_EVIDENCE_REQUIRED",
    },
    {
        "row_key": "exported_tc1/BUG_5426_airplane_reboot_apn.yaml#15",
        "disposition": "DEVICE_EVIDENCE_REQUIRED",
    },
]
PREDICATES = {
    "EQ_0": (0, "-eq", "count==0"),
    "EQ_1": (1, "-eq", "count==1"),
    "LE_1": (1, "-le", "count<=1"),
}
REPO_ROOT = Path(__file__).resolve().parents[1]
CAPSULE_ROOT = Path(r"C:\tmp\tc-runner-dispatch-capsules")
P2_PATH = "provenance/ss_call_shell_rc_manifest.yaml"
FROZEN_INVENTORY_PATH = (
    "reports/_codex_shell_inventory_v3_277e_a/66951de779d78dc6/"
    "shell_rc_inventory.csv"
)
FROZEN_RISK_PATH = (
    "reports/_codex_shell_rc_risk_3d99_a/c60be6036584ce8f/"
    "shell_rc_risk_matrix.csv"
)
ALLOWED_TRACKED_PATHS = {
    ".gitattributes",
    P2_PATH,
    "ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml",
    "ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml",
    "exported_ss_call/SS_TC01_permission_denied.yaml",
    "exported_ss_call/SS_TC02_permission_allow_idle.yaml",
    "exported_ss_call/SS_TC03_ringing_permission.yaml",
    "exported_ss_call/SS_TC04_offhook_seed_recovery.yaml",
    "exported_ss_call/SS_TC05_boundary_values.yaml",
    "exported_ss_call/SS_TC06_missed_rejected.yaml",
    "exported_ss_call/SS_TC07_short_call_no_false_positive.yaml",
    "exported_ss_call/SS_TC09_offhook_permission_banking.yaml",
    "exported_ss_call/SS_TC0_P0_endcall_crash.yaml",
    "exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml",
    "exported_ss_call/SS_TC10_permission_toggle.yaml",
    "exported_ss_call/SS_TC11_multi_subscription.yaml",
    "exported_ss_call/SS_TC12_legacy_path.yaml",
    "scripts/dispatch_capsule.py",
    "tests/test_dispatch_capsule.py",
    "tests/fixtures/anchor/corpus_audit_baseline.json",
    "CLAUDE.md",
}
ALLOWED_NEW_PATHS = {
    "scripts/canonical_shell_rc_remediation_manifest_v1.json",
    "scripts/canonical_shell_rc_remediation_check.py",
    "tests/test_canonical_shell_rc_remediation.py",
}
PROTECTED_GOVERNANCE_PATHS = {
    "docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md",
    "docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md",
    "HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md",
}


def _exact_mapping(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise InputInvalid(f"{label} keys differ")
    return value


def _json_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputInvalid(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _plain_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputInvalid(f"{label} must be a non-empty string")
    if any(character in value for character in ("\0", "\r", "\n")):
        raise InputInvalid(f"{label} contains a forbidden control character")
    return value


def _relative_posix(value: object, label: str) -> str:
    text = _plain_string(value, label)
    path = PurePosixPath(text)
    if (
        "\\" in text
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != text
    ):
        raise InputInvalid(f"{label} is not an exact repo-relative path")
    return text


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_invariant_scope(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputInvalid("capsule invariant scope is invalid")
    scope_version = value.get("scope_version")
    expected_keys = {
        "canonical_json_sha256",
        "exact_paths",
        "prefixes",
        "scope_version",
    }
    if scope_version == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION:
        expected_keys.add("verifier_owned_ignored_prefixes")
    if scope_version not in {
        INVARIANT_SCOPE_VERSION,
        VERIFIER_OWNED_INVARIANT_SCOPE_VERSION,
    } or set(value) != expected_keys:
        raise InputInvalid("capsule invariant scope is invalid")
    exact_paths = value["exact_paths"]
    prefixes = value["prefixes"]
    if (
        not isinstance(exact_paths, list)
        or not isinstance(prefixes, list)
        or not exact_paths and not prefixes
        or LOWER_SHA256_RE.fullmatch(
            str(value["canonical_json_sha256"])
        ) is None
    ):
        raise InputInvalid("capsule invariant scope is invalid")
    normalized_exact = [
        _relative_posix(path, "capsule invariant path")
        for path in exact_paths
    ]
    normalized_prefixes = []
    for prefix in prefixes:
        if not isinstance(prefix, str) or not prefix.endswith("/"):
            raise InputInvalid("capsule invariant prefix is invalid")
        normalized_prefixes.append(
            f"{_relative_posix(prefix[:-1], 'capsule invariant prefix')}/"
        )
    normalized_owned_prefixes = []
    if scope_version == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION:
        owned_prefixes = value["verifier_owned_ignored_prefixes"]
        if not isinstance(owned_prefixes, list):
            raise InputInvalid("capsule verifier-owned ignored prefix is invalid")
        for prefix in owned_prefixes:
            if not isinstance(prefix, str) or not prefix.endswith("/"):
                raise InputInvalid(
                    "capsule verifier-owned ignored prefix is invalid"
                )
            normalized_owned_prefixes.append(
                f"{_relative_posix(prefix[:-1], 'capsule verifier-owned ignored prefix')}/"
            )
    if (
        normalized_exact
        != sorted(set(normalized_exact), key=lambda item: item.encode("utf-8"))
        or normalized_prefixes
        != sorted(
            set(normalized_prefixes),
            key=lambda item: item.encode("utf-8"),
        )
        or normalized_owned_prefixes
        != sorted(
            set(normalized_owned_prefixes),
            key=lambda item: item.encode("utf-8"),
        )
    ):
        raise InputInvalid("capsule invariant scope is not canonical")
    for index, prefix in enumerate(normalized_prefixes):
        if any(prefix.startswith(other) for other in normalized_prefixes[:index]):
            raise InputInvalid("capsule invariant scope overlaps")
    if any(
        exact.startswith(prefix)
        for exact in normalized_exact
        for prefix in normalized_prefixes
    ):
        raise InputInvalid("capsule invariant scope overlaps")
    for index, prefix in enumerate(normalized_owned_prefixes):
        if any(prefix.startswith(other) for other in normalized_owned_prefixes[:index]):
            raise InputInvalid("capsule invariant scope overlaps")
    if any(
        owned.startswith(prefix) or prefix.startswith(owned)
        for owned in normalized_owned_prefixes
        for prefix in normalized_prefixes
    ) or any(
        exact.startswith(owned) or owned.startswith(f"{exact}/")
        for exact in normalized_exact
        for owned in normalized_owned_prefixes
    ):
        raise InputInvalid("capsule invariant scope overlaps")
    if (
        scope_version == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION
        and tuple(normalized_owned_prefixes)
        != VERIFIER_OWNED_IGNORED_PREFIXES
    ):
        raise InputInvalid(
            "capsule verifier-owned ignored prefix contract differs"
        )
    selector_payload = {
        "exact_paths": normalized_exact,
        "prefixes": normalized_prefixes,
        "scope_version": scope_version,
    }
    if scope_version == VERIFIER_OWNED_INVARIANT_SCOPE_VERSION:
        selector_payload["verifier_owned_ignored_prefixes"] = (
            normalized_owned_prefixes
        )
    if value["canonical_json_sha256"] != canonical_json_sha256(
        selector_payload
    ):
        raise InputInvalid("capsule invariant scope hash mismatch")
    return value


def _path_is_in_invariant_scope(
    relative: str,
    scope: dict[str, Any],
) -> bool:
    return relative in scope["exact_paths"] or any(
        relative.startswith(prefix) for prefix in scope["prefixes"]
    )


def sentinel_for(source_path: str, step_index: int) -> str:
    path = _relative_posix(source_path, "source_path")
    if not _is_int(step_index) or step_index <= 0:
        raise InputInvalid("step_index must be a positive integer")
    suffix = hashlib.sha256(f"{path}#{step_index}".encode("utf-8")).hexdigest()[:12]
    return f"__TC_ASSERT_OK_{suffix}__"


def _predicate(predicate_kind: object, predicate_value: object) -> tuple[int, str, str]:
    if predicate_kind not in PREDICATES:
        raise InputInvalid("unsupported predicate")
    expected, operator, diagnostic = PREDICATES[str(predicate_kind)]
    if not _is_int(predicate_value) or predicate_value != expected:
        raise InputInvalid("predicate value mismatch")
    return expected, operator, diagnostic


def evaluate_count(
    source_rc: int,
    grep_rc: int,
    count_text: str,
    predicate_kind: str,
    predicate_value: int,
) -> tuple[bool, str]:
    if not _is_int(source_rc) or source_rc < 0:
        raise InputInvalid("source rc is invalid")
    if not _is_int(grep_rc) or grep_rc < 0:
        raise InputInvalid("grep rc is invalid")
    expected, _, diagnostic = _predicate(predicate_kind, predicate_value)
    if source_rc != 0:
        return False, f"TC_ASSERT_SOURCE_RC={source_rc}"
    if grep_rc not in (0, 1):
        return False, f"TC_ASSERT_GREP_RC={grep_rc}"
    if not isinstance(count_text, str) or re.fullmatch(r"[0-9]+", count_text) is None:
        return False, f"TC_ASSERT_COUNT_INVALID={count_text}"
    count = int(count_text)
    if predicate_kind == "LE_1":
        matches = count <= expected
    else:
        matches = count == expected
    if not matches:
        return False, f"TC_ASSERT_COUNT={count} EXPECTED={diagnostic}"
    return True, ""


def _validate_target(target: object, expected_row_key: str | None = None) -> dict[str, Any]:
    row = _exact_mapping(target, TARGET_KEYS, "target")
    path = _relative_posix(row["source_path"], "target.source_path")
    index = row["step_index"]
    if not _is_int(index) or index <= 0:
        raise InputInvalid("target.step_index is invalid")
    row_key = _plain_string(row["row_key"], "target.row_key")
    if row_key != f"{path}#{index}":
        raise InputInvalid("target.row_key mismatch")
    if expected_row_key is not None and row_key != expected_row_key:
        raise InputInvalid("target order differs")
    if row["baseline_action"] not in {"shell", "verify_shell"}:
        raise InputInvalid("target.baseline_action is invalid")
    baseline_command = _plain_string(
        row["baseline_command"], "target.baseline_command"
    )
    baseline_hash = row["baseline_command_sha256"]
    if (
        not isinstance(baseline_hash, str)
        or LOWER_SHA256_RE.fullmatch(baseline_hash) is None
        or hashlib.sha256(baseline_command.encode("utf-8")).hexdigest()
        != baseline_hash
    ):
        raise InputInvalid("target baseline command hash mismatch")
    _plain_string(row["classification"], "target.classification")
    renderer = row["renderer_kind"]
    if renderer not in {"stream_count", "uiautomator_dump_count"}:
        raise InputInvalid("unsupported renderer")
    source = _plain_string(row["source_command"], "target.source_command")
    if "|" in source:
        raise InputInvalid("source command contains a pipeline")
    if renderer == "uiautomator_dump_count" and source != "uiautomator dump":
        raise InputInvalid("UI renderer source command mismatch")
    pattern = _plain_string(row["grep_pattern"], "target.grep_pattern")
    if "'" in pattern:
        raise InputInvalid("grep pattern contains a single quote")
    _predicate(row["predicate_kind"], row["predicate_value"])
    if row["sentinel"] != sentinel_for(path, index):
        raise InputInvalid("target sentinel mismatch")
    if row["timeout_policy"] != "verify_shell_default_30s":
        raise InputInvalid("target timeout policy mismatch")
    provenance = _exact_mapping(row["provenance"], PROVENANCE_KEYS, "provenance")
    mode = provenance["mode"]
    if mode == "p2_manifest":
        if provenance["yaml_path"] != path:
            raise InputInvalid("P2 provenance path mismatch")
        _plain_string(provenance["source_no"], "provenance.source_no")
    elif mode in {"local", "manual"}:
        if provenance["yaml_path"] is not None or provenance["source_no"] is not None:
            raise InputInvalid("local/manual provenance must use null joins")
    else:
        raise InputInvalid("unsupported provenance mode")
    return row


def load_and_validate_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputInvalid("remediation manifest could not be read") from exc
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_json_without_duplicates,
        )
    except InputInvalid:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputInvalid("remediation manifest is invalid JSON") from exc
    manifest = _exact_mapping(value, ROOT_KEYS, "manifest")
    if manifest["schema_version"] != 1:
        raise InputInvalid("manifest schema version mismatch")
    if manifest["subject"] != "canonical shell-rc blocker remediation":
        raise InputInvalid("manifest subject mismatch")
    baseline = _exact_mapping(manifest["baseline"], BASELINE_KEYS, "baseline")
    if baseline != EXPECTED_BASELINE:
        raise InputInvalid("manifest baseline mismatch")
    targets = manifest["targets"]
    if not isinstance(targets, list) or len(targets) != len(TARGET_ROW_KEYS):
        raise InputInvalid("manifest target cardinality mismatch")
    validated = [
        _validate_target(target, expected)
        for target, expected in zip(targets, TARGET_ROW_KEYS, strict=True)
    ]
    row_keys = [target["row_key"] for target in validated]
    sentinels = [target["sentinel"] for target in validated]
    temps = [
        _temp_path(target)
        for target in validated
    ]
    if len(set(row_keys)) != 18 or len(set(sentinels)) != 18 or len(set(temps)) != 18:
        raise InputInvalid("manifest target identities are not unique")
    distribution = {kind: 0 for kind in PREDICATES}
    for target in validated:
        distribution[target["predicate_kind"]] += 1
    if distribution != {"EQ_0": 13, "EQ_1": 4, "LE_1": 1}:
        raise InputInvalid("manifest predicate distribution mismatch")
    runtime = manifest["runtime_review_dispositions"]
    if not isinstance(runtime, list) or runtime != EXPECTED_RUNTIME:
        raise InputInvalid("runtime-review dispositions differ")
    for row in runtime:
        _exact_mapping(row, RUNTIME_KEYS, "runtime disposition")
    semantic = _exact_mapping(
        manifest["semantic_identity"], SEMANTIC_KEYS, "semantic identity"
    )
    if semantic != {
        "targets_sha256": canonical_json_sha256(targets),
        "runtime_review_dispositions_sha256": canonical_json_sha256(runtime),
    }:
        raise InputInvalid("manifest semantic identity mismatch")
    return manifest


def _temp_path(target: dict[str, Any]) -> str:
    suffix = target["sentinel"].removeprefix("__TC_ASSERT_OK_").removesuffix("__")
    extension = "xml" if target["renderer_kind"] == "uiautomator_dump_count" else "txt"
    return f"/data/local/tmp/tc_runner_rc_{suffix}_$$.{extension}"


def _cleanup_and_exit(primary: str) -> str:
    return (
        'rm -f "$tmp"; cleanup_rc=$?; '
        'if [ "$cleanup_rc" -ne 0 ]; then '
        'echo "TC_ASSERT_CLEANUP_RC=$cleanup_rc" >&2; fi; '
        f'exit "${primary}"'
    )


def render_command(target: dict[str, Any]) -> str:
    row_key = target.get("row_key") if isinstance(target, dict) else None
    expected = row_key if row_key in TARGET_ROW_KEYS else None
    row = _validate_target(target, expected)
    temp = _temp_path(row)
    _, operator, diagnostic = _predicate(
        row["predicate_kind"], row["predicate_value"]
    )
    if row["renderer_kind"] == "stream_count":
        source = f'{row["source_command"]} >"$tmp"'
    else:
        source = 'uiautomator dump "$tmp" >/dev/null 2>&1'
    source_failure = _cleanup_and_exit("source_rc")
    grep_failure = _cleanup_and_exit("grep_rc")
    invalid_failure = _cleanup_and_exit("primary_rc")
    mismatch_failure = _cleanup_and_exit("primary_rc")
    return "; ".join(
        [
            f'tmp="{temp}"',
            'rm -f "$tmp"',
            "pre_cleanup_rc=$?",
            (
                'if [ "$pre_cleanup_rc" -ne 0 ]; then '
                'echo "TC_ASSERT_PRE_CLEANUP_RC=$pre_cleanup_rc" >&2; '
                'exit "$pre_cleanup_rc"; fi'
            ),
            source,
            "source_rc=$?",
            (
                'if [ "$source_rc" -ne 0 ]; then '
                'echo "TC_ASSERT_SOURCE_RC=$source_rc" >&2; '
                f"{source_failure}; fi"
            ),
            f'count=$(grep -c \'{row["grep_pattern"]}\' "$tmp")',
            "grep_rc=$?",
            (
                'if [ "$grep_rc" -gt 1 ]; then '
                'echo "TC_ASSERT_GREP_RC=$grep_rc" >&2; '
                f"{grep_failure}; fi"
            ),
            (
                'case "$count" in \'\'|*[!0-9]*) '
                'echo "TC_ASSERT_COUNT_INVALID=$count" >&2; primary_rc=1; '
                f"{invalid_failure};; esac"
            ),
            (
                f'if ! [ "$count" {operator} {row["predicate_value"]} ]; then '
                f'echo "TC_ASSERT_COUNT=$count EXPECTED={diagnostic}" >&2; '
                f"primary_rc=1; {mismatch_failure}; fi"
            ),
            'rm -f "$tmp"',
            "cleanup_rc=$?",
            (
                'if [ "$cleanup_rc" -ne 0 ]; then '
                'echo "TC_ASSERT_CLEANUP_RC=$cleanup_rc" >&2; '
                'exit "$cleanup_rc"; fi'
            ),
            f"printf '%s\\n' '{row['sentinel']}'",
        ]
    )


def _git_bytes(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", *args],
            cwd=repo,
            input=input_bytes,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise InfrastructureFailure("Git could not be started") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(
            f"git {' '.join(args)} exit {completed.returncode}: {message}"
        )
    if completed.stderr:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise InfrastructureFailure(f"git {' '.join(args)} emitted stderr: {message}")
    return completed.stdout


def _git_text(repo: Path, *args: str) -> str:
    try:
        return _git_bytes(repo, *args).decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise InfrastructureFailure("Git emitted non-UTF-8 output") from exc


def _sha256_file(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise InputInvalid(f"{label} could not be read") from exc


def _load_yaml_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InputInvalid(f"{label} is invalid YAML") from exc
    if not isinstance(value, dict):
        raise InputInvalid(f"{label} root is not a mapping")
    return value


def _read_candidate_yaml(
    repo: Path,
    relative: str,
    *,
    mode: str,
    candidate_head: str | None,
) -> dict[str, Any]:
    if mode == "worktree":
        try:
            raw = (repo / PurePosixPath(relative)).read_bytes()
        except OSError as exc:
            raise InputInvalid(f"candidate YAML missing: {relative}") from exc
    elif mode == "commit":
        if candidate_head is None or re.fullmatch(r"[0-9a-f]{40}", candidate_head) is None:
            raise InputInvalid("commit mode requires a full lowercase candidate HEAD")
        raw = _git_bytes(repo, "show", f"{candidate_head}:{relative}")
    else:
        raise InputInvalid("unsupported verification mode")
    return _load_yaml_bytes(raw, f"candidate {relative}")


def _baseline_documents(repo: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    head = manifest["baseline"]["inventory_head"]
    result: dict[str, dict[str, Any]] = {}
    for target in manifest["targets"]:
        relative = target["source_path"]
        if relative not in result:
            result[relative] = _load_yaml_bytes(
                _git_bytes(repo, "show", f"{head}:{relative}"),
                f"baseline {relative}",
            )
    return result


def compare_candidate_documents(
    baseline_documents: dict[str, dict[str, Any]],
    candidate_documents: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    targets_by_path: dict[str, list[dict[str, Any]]] = {}
    for target in manifest["targets"]:
        targets_by_path.setdefault(target["source_path"], []).append(target)
    violations: list[dict[str, Any]] = []
    remediated = 0
    non_target_mutations = 0
    for source_path, path_targets in targets_by_path.items():
        baseline = baseline_documents.get(source_path)
        candidate = candidate_documents.get(source_path)
        if not isinstance(baseline, dict) or not isinstance(candidate, dict):
            violations.append({"code": "DOCUMENT_MISSING", "row_key": source_path})
            continue
        baseline_steps = baseline.get("steps")
        candidate_steps = candidate.get("steps")
        if not isinstance(baseline_steps, list) or not isinstance(candidate_steps, list):
            violations.append({"code": "STEPS_INVALID", "row_key": source_path})
            continue
        if len(baseline_steps) != len(candidate_steps):
            violations.append({"code": "NON_TARGET_MUTATION", "row_key": source_path})
            non_target_mutations += 1
            continue
        if {key: value for key, value in baseline.items() if key != "steps"} != {
            key: value for key, value in candidate.items() if key != "steps"
        }:
            violations.append({"code": "NON_TARGET_MUTATION", "row_key": source_path})
            non_target_mutations += 1
        target_by_index = {target["step_index"]: target for target in path_targets}
        for index, (baseline_step, candidate_step) in enumerate(
            zip(baseline_steps, candidate_steps, strict=True), start=1
        ):
            if not isinstance(baseline_step, dict) or not isinstance(candidate_step, dict):
                violations.append(
                    {"code": "NON_TARGET_MUTATION", "row_key": f"{source_path}#{index}"}
                )
                non_target_mutations += 1
                continue
            target = target_by_index.get(index)
            if target is None:
                if baseline_step != candidate_step:
                    violations.append(
                        {"code": "NON_TARGET_MUTATION", "row_key": f"{source_path}#{index}"}
                    )
                    non_target_mutations += 1
                continue
            expected = {
                "action": "verify_shell",
                "command": render_command(target),
                "expected": target["sentinel"],
            }
            exact = True
            for field, code in (
                ("action", "TARGET_ACTION"),
                ("command", "TARGET_COMMAND"),
                ("expected", "TARGET_EXPECTED"),
            ):
                if candidate_step.get(field) != expected[field]:
                    exact = False
                    violations.append({"code": code, "row_key": target["row_key"]})
            if exact:
                remediated += 1
            normalized = copy.deepcopy(candidate_step)
            for field in ("action", "command", "expected"):
                if field in baseline_step:
                    normalized[field] = baseline_step[field]
                else:
                    normalized.pop(field, None)
            if normalized != baseline_step:
                violations.append(
                    {"code": "TARGET_NON_PROJECTION", "row_key": target["row_key"]}
                )
    return {
        "non_target_mutations": non_target_mutations,
        "remediated_targets": remediated,
        "target_violations": violations,
    }


def _p2_cardinalities(value: dict[str, Any]) -> tuple[int, int, int]:
    mappings = value.get("mappings")
    if not isinstance(mappings, list):
        return 0, 0, 0
    selectors = 0
    bindings = 0
    for mapping in mappings:
        if isinstance(mapping, dict):
            source_selectors = mapping.get("source_selectors")
            blocker_bindings = mapping.get("blocker_bindings")
            if isinstance(source_selectors, list):
                selectors += len(source_selectors)
            if isinstance(blocker_bindings, list):
                bindings += len(blocker_bindings)
    return len(mappings), selectors, bindings


def _compare_p2(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], tuple[int, int, int]]:
    violations: list[dict[str, Any]] = []
    cardinalities = _p2_cardinalities(candidate)
    if cardinalities != (12, 14, 15):
        violations.append({"code": "P2_CARDINALITY", "row_key": P2_PATH})
        return violations, cardinalities
    target_by_key = {
        (
            target["source_path"],
            target["step_index"],
            target["provenance"]["source_no"],
        ): target
        for target in manifest["targets"]
        if target["provenance"]["mode"] == "p2_manifest"
    }
    normalized = copy.deepcopy(candidate)
    baseline_projection: dict[tuple[str, int, str], dict[str, Any]] = {}
    for mapping in baseline["mappings"]:
        for binding in mapping["blocker_bindings"]:
            baseline_projection[(
                mapping["yaml_path"],
                binding["blocker_step_index"],
                binding["source_no"],
            )] = binding["step_projection"]
    observed: set[tuple[str, int, str]] = set()
    for mapping in normalized["mappings"]:
        for binding in mapping["blocker_bindings"]:
            key = (
                mapping["yaml_path"],
                binding["blocker_step_index"],
                binding["source_no"],
            )
            observed.add(key)
            target = target_by_key.get(key)
            if target is None:
                violations.append({"code": "P2_UNEXPECTED_BINDING", "row_key": str(key)})
                continue
            expected = {
                "action": "verify_shell",
                "command": render_command(target),
                "expected": target["sentinel"],
            }
            if binding["step_projection"] != expected:
                violations.append({"code": "P2_PROJECTION", "row_key": target["row_key"]})
            binding["step_projection"] = copy.deepcopy(baseline_projection.get(key))
    if observed != set(target_by_key):
        violations.append({"code": "P2_BINDING_SET", "row_key": P2_PATH})
    if normalized != baseline:
        violations.append({"code": "P2_IDENTITY", "row_key": P2_PATH})
    return violations, cardinalities


def verify_repository_candidate(
    repo: Path,
    manifest: dict[str, Any],
    *,
    mode: str,
    candidate_head: str | None = None,
) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    baseline_documents = _baseline_documents(repo, manifest)
    candidate_documents = {
        source_path: _read_candidate_yaml(
            repo, source_path, mode=mode, candidate_head=candidate_head
        )
        for source_path in baseline_documents
    }
    comparison = compare_candidate_documents(
        baseline_documents, candidate_documents, manifest
    )
    baseline_p2_head = manifest["baseline"]["p2_manifest_pre_remediation_head"]
    baseline_p2_raw = _git_bytes(
        repo, "show", f"{baseline_p2_head}:{P2_PATH}"
    )
    if hashlib.sha256(baseline_p2_raw).hexdigest() != manifest["baseline"][
        "p2_manifest_pre_remediation_sha256"
    ]:
        raise InputInvalid("P2 baseline identity mismatch")
    baseline_p2 = _load_yaml_bytes(baseline_p2_raw, "baseline P2 manifest")
    candidate_p2 = _read_candidate_yaml(
        repo, P2_PATH, mode=mode, candidate_head=candidate_head
    )
    p2_violations, cardinalities = _compare_p2(
        baseline_p2, candidate_p2, manifest
    )
    frozen_inventory = repo / PurePosixPath(FROZEN_INVENTORY_PATH)
    frozen_risk = repo / PurePosixPath(FROZEN_RISK_PATH)
    if _sha256_file(frozen_inventory, "frozen inventory") != manifest["baseline"][
        "inventory_csv_sha256"
    ]:
        raise InputInvalid("frozen inventory identity mismatch")
    if _sha256_file(frozen_risk, "frozen risk matrix") != manifest["baseline"][
        "risk_matrix_sha256"
    ]:
        raise InputInvalid("frozen risk matrix identity mismatch")
    if _sha256_file(
        repo / "scripts" / "canonical_shell_rc_risk_policy_v1.json",
        "risk policy",
    ) != manifest["baseline"]["risk_policy_sha256"]:
        raise InputInvalid("risk policy identity mismatch")
    all_violations = comparison["target_violations"] + p2_violations
    unresolved = len(
        {
            row["row_key"]
            for row in comparison["target_violations"]
            if row["code"].startswith("TARGET_")
        }
    )
    matrix_rows = []
    for target in manifest["targets"]:
        candidate_step = candidate_documents[target["source_path"]]["steps"][
            target["step_index"] - 1
        ]
        matrix_rows.append(
            {
                "row_key": target["row_key"],
                "source_path": target["source_path"],
                "step_index": target["step_index"],
                "predicate_kind": target["predicate_kind"],
                "baseline_action": target["baseline_action"],
                "candidate_action": candidate_step.get("action"),
                "status": (
                    "REMEDIATED"
                    if candidate_step.get("action") == "verify_shell"
                    and candidate_step.get("command") == render_command(target)
                    and candidate_step.get("expected") == target["sentinel"]
                    else "VIOLATION"
                ),
            }
        )
    return {
        "status": "GREEN" if not all_violations else "VIOLATION",
        "baseline_rows": 692,
        "candidate_rows": 692,
        "remediated_targets": comparison["remediated_targets"],
        "non_target_rows": 674,
        "non_target_mutations": comparison["non_target_mutations"],
        "advisory_rows": 74,
        "runtime_review_rows": 6,
        "unresolved": unresolved,
        "p2_mappings": cardinalities[0],
        "p2_selectors": cardinalities[1],
        "p2_bindings": cardinalities[2],
        "violations": all_violations,
        "matrix_rows": matrix_rows,
    }


def _path_map(
    repo: Path,
    *,
    ignored: bool,
    excluded_exact: set[str],
    excluded_prefixes: tuple[str, ...],
    invariant_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    args = ["ls-files", "--others"]
    if ignored:
        args.append("--ignored")
    args.extend(["--exclude-standard", "-z"])
    raw = _git_bytes(repo, *args)
    paths: list[str] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            relative = item.decode("utf-8", "strict").replace("\\", "/")
        except UnicodeDecodeError as exc:
            raise InfrastructureFailure("Git path is not UTF-8") from exc
        if relative in excluded_exact or any(
            relative.startswith(prefix) for prefix in excluded_prefixes
        ):
            continue
        paths.append(relative)
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
    paths.sort(key=lambda value: value.encode("utf-8"))
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
        path = repo / PurePosixPath(relative)
        if not path.is_file() or path.is_symlink():
            raise InputInvalid(f"non-ordinary untracked path: {relative}")
    request = "".join(
        f"{path}\n" for path in selected_paths
    ).encode("utf-8")
    hashes = (
        _git_bytes(repo, "hash-object", "--no-filters", "--stdin-paths", input_bytes=request)
        .decode("ascii", "strict")
        .splitlines()
    )
    if len(selected_paths) != len(hashes):
        raise InfrastructureFailure("path/hash cardinality mismatch")
    rows = [
        {
            "file_type": "file",
            "git_hash_object_no_filters": digest,
            "path": path,
        }
        for path, digest in zip(selected_paths, hashes, strict=True)
    ]
    result = {
        "count": len(rows),
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "rows": rows,
    }
    if invariant_scope is not None:
        result["excluded_count"] = len(paths) - len(selected_paths)
    return result


def _tracked_worktree_map(repo: Path) -> dict[str, Any]:
    raw = _git_bytes(
        repo,
        "-c",
        "core.quotepath=false",
        "diff-index",
        "--name-only",
        "-z",
        "HEAD",
        "--",
    )
    paths: list[str] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            relative = item.decode("utf-8", "strict").replace("\\", "/")
        except UnicodeDecodeError as exc:
            raise InfrastructureFailure("tracked worktree path is not UTF-8") from exc
        _relative_posix(relative, "tracked worktree path")
        path = repo / PurePosixPath(relative)
        if not path.is_file() or path.is_symlink():
            raise InputInvalid(f"non-ordinary tracked worktree path: {relative}")
        paths.append(relative)
    paths.sort(key=lambda value: value.encode("utf-8"))
    request = "".join(f"{path}\n" for path in paths).encode("utf-8")
    hashes = (
        _git_bytes(repo, "hash-object", "--no-filters", "--stdin-paths", input_bytes=request)
        .decode("ascii", "strict")
        .splitlines()
    )
    if len(paths) != len(hashes):
        raise InfrastructureFailure("tracked worktree path/hash cardinality mismatch")
    rows = []
    for path, digest in zip(paths, hashes, strict=True):
        if LOWER_OID_RE.fullmatch(digest) is None:
            raise InfrastructureFailure("tracked worktree Git blob is invalid")
        rows.append(
            {
                "git_blob_no_filters": digest,
                "path": path,
                "raw_sha256": hashlib.sha256(
                    (repo / PurePosixPath(path)).read_bytes()
                ).hexdigest(),
            }
        )
    return {
        "count": len(rows),
        "canonical_json_sha256": canonical_json_sha256(rows),
        "rows": rows,
    }


def snapshot_repository_identity(
    repo: Path,
    *,
    excluded_untracked: set[str] | None = None,
    excluded_ignored_prefixes: tuple[str, ...] = (),
    invariant_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    if invariant_scope is not None:
        invariant_scope = _validate_invariant_scope(invariant_scope)
    index_raw = _git_bytes(repo, "ls-files", "--stage", "-z")
    identity = {
        "head": _git_text(repo, "rev-parse", "HEAD"),
        "tracked_worktree": _tracked_worktree_map(repo),
        "index": {
            "entry_count": len([item for item in index_raw.split(b"\0") if item]),
            "raw_stage_z_sha256": hashlib.sha256(index_raw).hexdigest(),
        },
        "untracked": _path_map(
            repo,
            ignored=False,
            excluded_exact=excluded_untracked or set(),
            excluded_prefixes=(),
            invariant_scope=invariant_scope,
        ),
        "ignored": _path_map(
            repo,
            ignored=True,
            excluded_exact=set(),
            excluded_prefixes=excluded_ignored_prefixes,
            invariant_scope=invariant_scope,
        ),
    }
    if invariant_scope is not None:
        selected = {
            row["path"]
            for row in identity["untracked"]["rows"]
            + identity["ignored"]["rows"]
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
        identity["invariant_scope"] = invariant_scope
    return identity


def render_evidence(
    report: dict[str, Any], identities: dict[str, str]
) -> dict[str, bytes]:
    output = io.StringIO(newline="")
    fields = (
        "row_key",
        "source_path",
        "step_index",
        "predicate_kind",
        "baseline_action",
        "candidate_action",
        "status",
    )
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in report.get("matrix_rows", []):
        writer.writerow({field: row.get(field, "") for field in fields})
    summary_lines = [
        "# Canonical Shell-RC Remediation Summary",
        "",
        f"- status: {report['status']}",
        f"- baseline_rows: {report['baseline_rows']}",
        f"- candidate_rows: {report['candidate_rows']}",
        f"- remediated_targets: {report['remediated_targets']}",
        f"- non_target_rows: {report['non_target_rows']}",
        f"- advisory_rows: {report['advisory_rows']}",
        f"- runtime_review_rows: {report['runtime_review_rows']}",
        f"- unresolved: {report['unresolved']}",
        f"- p2: {report['p2_mappings']}/{report['p2_selectors']}/{report['p2_bindings']}",
        "",
        "## Identities",
        "",
    ]
    summary_lines.extend(f"- {key}: {identities[key]}" for key in sorted(identities))
    summary_lines.extend(["", "## Violations", ""])
    violations = report.get("violations", [])
    if violations:
        summary_lines.extend(
            f"- {row['code']}: {row['row_key']}" for row in violations
        )
    else:
        summary_lines.append("- none")
    return {
        "shell_rc_remediation_matrix.csv": output.getvalue().encode("utf-8"),
        "SUMMARY.md": ("\n".join(summary_lines) + "\n").encode("utf-8"),
    }


def _validate_existing_bundle(path: Path, artifacts: dict[str, bytes]) -> None:
    if not path.is_dir() or path.is_symlink():
        raise InfrastructureFailure("existing evidence destination is not ordinary")
    entries = {item.name for item in path.iterdir()}
    if entries != set(artifacts):
        raise InfrastructureFailure("existing evidence entries differ")
    for name, raw in artifacts.items():
        actual = path / name
        if not actual.is_file() or actual.is_symlink() or actual.read_bytes() != raw:
            raise InfrastructureFailure("existing evidence bytes differ")


def publish_evidence(
    output_root: Path, input_digest: str, artifacts: dict[str, bytes]
) -> Path:
    if re.fullmatch(r"[0-9a-f]{16}", input_digest) is None:
        raise InputInvalid("evidence input digest is invalid")
    if set(artifacts) != {"SUMMARY.md", "shell_rc_remediation_matrix.csv"}:
        raise InputInvalid("evidence artifact set differs")
    output_root.mkdir(parents=True, exist_ok=True)
    final = output_root / input_digest
    if final.exists():
        _validate_existing_bundle(final, artifacts)
        return final
    staging_root = output_root / ".staging"
    staging_root.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="bundle-", dir=staging_root))
    try:
        for name, raw in artifacts.items():
            (temporary / name).write_bytes(raw)
        for name, raw in artifacts.items():
            if (temporary / name).read_bytes() != raw:
                raise InfrastructureFailure("staged evidence verification failed")
        try:
            temporary.rename(final)
        except FileExistsError:
            _validate_existing_bundle(final, artifacts)
            shutil.rmtree(temporary)
        return final
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def _load_capsule(digest: str) -> dict[str, Any]:
    if LOWER_SHA256_RE.fullmatch(digest) is None:
        raise InputInvalid("capsule SHA-256 is invalid")
    path = CAPSULE_ROOT / f"{digest}.json"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputInvalid("capsule could not be read") from exc
    if hashlib.sha256(raw).hexdigest() != digest:
        raise InputInvalid("capsule content hash mismatch")
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputInvalid("capsule JSON is invalid") from exc
    if not isinstance(value, dict) or value.get("schema_version") not in {
        2, 3, 4, 5
    }:
        raise InputInvalid("capsule schema mismatch")
    if value.get("directive_id") != "RB-20260813-shellrc-curated-remediation-t1":
        raise InputInvalid("capsule directive mismatch")
    if value["schema_version"] in {3, 4, 5} and not isinstance(
        value.get("tracked_worktree"), dict
    ):
        raise InputInvalid("continuation capsule lacks tracked worktree")
    if value["schema_version"] in {4, 5}:
        _validate_invariant_scope(value.get("invariant_scope"))
    return value


def _require_repo_scope(repo: Path, capsule: dict[str, Any], identity: dict[str, Any]) -> None:
    head = _git_text(repo, "rev-parse", "HEAD")
    upstream = _git_text(repo, "rev-parse", "origin/master")
    if head != capsule["repo"]["head_sha"] or upstream != capsule["repo"]["upstream_sha"]:
        raise InputInvalid("repository HEAD/upstream drift")
    ahead_behind = _git_text(repo, "rev-list", "--left-right", "--count", "HEAD...origin/master")
    if ahead_behind.split() != ["0", "0"]:
        raise InputInvalid("repository ahead/behind drift")
    if identity["index"] != capsule["index"]:
        raise InputInvalid("repository index drift")
    if capsule.get("schema_version") in {3, 4, 5}:
        if identity["tracked_worktree"] != capsule["tracked_worktree"]:
            raise InputInvalid("repository tracked worktree drift")
    elif identity["tracked_worktree"]["count"]:
        dirty_paths = {
            row["path"] for row in identity["tracked_worktree"]["rows"]
        }
        if not dirty_paths <= ALLOWED_TRACKED_PATHS:
            raise InputInvalid("tracked dirty path is outside write boundary")
    if capsule.get("schema_version") in {4, 5} and (
        identity.get("invariant_scope") != capsule["invariant_scope"]
    ):
        raise InputInvalid("repository invariant scope drift")
    for name in ("untracked", "ignored"):
        keys = (
            ("count", "canonical_json_sha256", "excluded_count")
            if capsule.get("schema_version") in {4, 5}
            else ("count", "canonical_json_sha256")
        )
        observed = {key: identity[name][key] for key in keys}
        expected = {key: capsule[name][key] for key in keys}
        if observed != expected:
            raise InputInvalid(f"repository {name} invariant drift")
    staged = _git_bytes(repo, "diff", "--cached", "--name-only", "-z")
    if staged:
        raise InputInvalid("index is not clean")
    dirty = {
        row["path"] for row in identity["tracked_worktree"]["rows"]
    }
    if not dirty <= ALLOWED_TRACKED_PATHS:
        raise InputInvalid("tracked dirty path is outside write boundary")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("verify-worktree", "verify-commit"):
        command = subparsers.add_parser(mode)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--spec", type=Path, required=True)
        command.add_argument("--directive", type=Path, required=True)
        command.add_argument("--evidence", type=Path, required=True)
        command.add_argument("--capsule-sha256", required=True)
        command.add_argument("--approved-spec-sha256", required=True)
        command.add_argument("--approved-directive-sha256", required=True)
        command.add_argument("--approved-evidence-sha256", required=True)
        command.add_argument("--output-root", type=Path, required=True)
        if mode == "verify-commit":
            command.add_argument("--candidate-head", required=True)
    return parser


def _run_cli(args: argparse.Namespace) -> int:
    repo = REPO_ROOT.resolve(strict=True)
    manifest_path = (repo / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    spec_path = (repo / args.spec).resolve() if not args.spec.is_absolute() else args.spec
    directive_path = (repo / args.directive).resolve() if not args.directive.is_absolute() else args.directive
    output_root = (repo / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root
    manifest = load_and_validate_manifest(manifest_path)
    for value, label in (
        (args.approved_spec_sha256, "approved spec SHA-256"),
        (args.approved_directive_sha256, "approved directive SHA-256"),
        (args.approved_evidence_sha256, "approved evidence SHA-256"),
    ):
        if LOWER_SHA256_RE.fullmatch(value) is None:
            raise InputInvalid(f"{label} is invalid")
    if _sha256_file(spec_path, "spec") != args.approved_spec_sha256:
        raise InputInvalid("spec identity mismatch")
    if _sha256_file(directive_path, "directive") != args.approved_directive_sha256:
        raise InputInvalid("directive identity mismatch")
    if _sha256_file(args.evidence, "evidence") != args.approved_evidence_sha256:
        raise InputInvalid("evidence identity mismatch")
    if args.approved_evidence_sha256 != manifest["baseline"]["p2_evidence_sha256"]:
        raise InputInvalid("manifest evidence identity mismatch")
    capsule = _load_capsule(args.capsule_sha256)
    if capsule["identities"]["spec"]["raw_sha256"] != args.approved_spec_sha256:
        raise InputInvalid("capsule spec identity mismatch")
    if capsule["identities"]["directive"]["raw_sha256"] != args.approved_directive_sha256:
        raise InputInvalid("capsule directive identity mismatch")
    excluded_untracked = (
        ALLOWED_NEW_PATHS if capsule["schema_version"] == 2 else set()
    )
    invariant_scope = (
        capsule["invariant_scope"]
        if capsule["schema_version"] in {4, 5}
        else None
    )
    ignored_exclusions = (
        ()
        if capsule["schema_version"] == 5
        else VERIFIER_OWNED_IGNORED_PREFIXES
    )
    identity_before = snapshot_repository_identity(
        repo,
        excluded_untracked=excluded_untracked,
        excluded_ignored_prefixes=ignored_exclusions,
        invariant_scope=invariant_scope,
    )
    _require_repo_scope(repo, capsule, identity_before)
    mode = "worktree" if args.mode == "verify-worktree" else "commit"
    report = verify_repository_candidate(
        repo,
        manifest,
        mode=mode,
        candidate_head=getattr(args, "candidate_head", None),
    )
    identities = {
        "candidate": canonical_json_sha256(report),
        "capsule": args.capsule_sha256,
        "directive": args.approved_directive_sha256,
        "evidence": args.approved_evidence_sha256,
        "manifest": _sha256_file(manifest_path, "manifest"),
        "spec": args.approved_spec_sha256,
        "verifier": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "index": identity_before["index"]["raw_stage_z_sha256"],
        "untracked": identity_before["untracked"]["canonical_json_sha256"],
        "ignored": identity_before["ignored"]["canonical_json_sha256"],
        "tracked_worktree": identity_before["tracked_worktree"][
            "canonical_json_sha256"
        ],
    }
    first = render_evidence(report, identities)
    second = render_evidence(copy.deepcopy(report), copy.deepcopy(identities))
    if first != second:
        raise InfrastructureFailure("independent evidence rendering differs")
    input_digest = canonical_json_sha256(identities)[:16]
    destination = publish_evidence(output_root, input_digest, first)
    identity_after = snapshot_repository_identity(
        repo,
        excluded_untracked=excluded_untracked,
        excluded_ignored_prefixes=ignored_exclusions,
        invariant_scope=invariant_scope,
    )
    if identity_after != identity_before:
        raise InputInvalid("repository identity changed during verification")
    print(
        json.dumps(
            {
                "evidence_path": destination.as_posix(),
                "input_digest": input_digest,
                "matrix_sha256": hashlib.sha256(
                    first["shell_rc_remediation_matrix.csv"]
                ).hexdigest(),
                "status": report["status"],
                "summary_sha256": hashlib.sha256(first["SUMMARY.md"]).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0 if report["status"] == "GREEN" else 1


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return _run_cli(args)
    except InputInvalid as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except InfrastructureFailure as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
