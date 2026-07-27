"""Host-only tests for the canonical shell RC companion audit."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
INVENTORY_SCRIPT = REPO / "scripts" / "canonical_shell_rc_inventory.py"
AUDIT_SCRIPT = REPO / "scripts" / "canonical_shell_rc_risk_audit.py"
POLICY_PATH = REPO / "scripts" / "canonical_shell_rc_risk_policy_v1.json"
FROZEN_CSV_SHA256 = (
    "b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f"
)
FROZEN_HEAD_SHA = "78b3ac34e9f8bacabe926172dd199342b7eb58c5"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INVENTORY = _load_module(
    "canonical_shell_rc_inventory_for_risk_tests",
    INVENTORY_SCRIPT,
)
AUDIT = _load_module("canonical_shell_rc_risk_audit", AUDIT_SCRIPT)


@pytest.fixture(scope="module")
def frozen_inventory(tmp_path_factory):
    report = INVENTORY.collect_inventory(
        REPO,
        head_sha=FROZEN_HEAD_SHA,
    )
    csv_bytes = INVENTORY._csv_bytes(report.rows)
    path = tmp_path_factory.mktemp("shell-risk") / "inventory.csv"
    path.write_bytes(csv_bytes)
    return path, csv_bytes


def _synthetic_inventory_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=INVENTORY.CSV_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _synthetic_row(
    *,
    row_key: str = "a" * 40 + ":case.yaml#1",
    command: str = "echo ok",
    action: str = "shell",
    expected: str = "",
    timeout_ms: str = "",
) -> dict[str, str]:
    return {
        "schema_version": INVENTORY.SCHEMA_VERSION,
        "head_sha": "a" * 40,
        "row_key": row_key,
        "source_path": "case.yaml",
        "source_blob": "b" * 40,
        "tc_name": "case",
        "step_index": "1",
        "action": action,
        "command": command,
        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        "expected": expected,
        "timeout_ms": timeout_ms,
        "execution_mode": "SHELL_AUTO",
        "dispatch_route": "RUNNER_SHELL",
    }


def _write_policy(
    path: Path,
    inventory_sha256: str,
    overrides: list[dict[str, str]],
    *,
    inventory_row_count: int = 1,
) -> None:
    identity_rows = [
        {
            "row_key": override["row_key"],
            "action": override["action"],
            "command_sha256": override["command_sha256"],
            "classification": override["classification"],
            "reason_code": override["reason_code"],
            "evidence": override["evidence"],
        }
        for override in overrides
    ]
    identity_rows.sort(
        key=lambda item: (
            item["row_key"],
            item["action"],
            item["command_sha256"],
            item["classification"],
            item["reason_code"],
            item["evidence"],
        )
    )
    identity_bytes = json.dumps(
        identity_rows,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    path.write_text(
        json.dumps(
            {
                "schema_version": AUDIT.POLICY_SCHEMA_VERSION,
                "inventory_sha256": inventory_sha256,
                "inventory_row_count": inventory_row_count,
                "override_count": len(overrides),
                "override_identity_sha256": hashlib.sha256(
                    identity_bytes
                ).hexdigest(),
                "overrides": overrides,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _bind_main_contract(
    monkeypatch,
    inventory_bytes: bytes,
    policy_path: Path,
    *,
    head_sha: str = "a" * 40,
    row_count: int = 1,
) -> None:
    monkeypatch.setattr(
        AUDIT,
        "FROZEN_INVENTORY_SHA256",
        hashlib.sha256(inventory_bytes).hexdigest(),
    )
    monkeypatch.setattr(AUDIT, "FROZEN_HEAD_SHA", head_sha)
    monkeypatch.setattr(AUDIT, "FROZEN_ROW_COUNT", row_count)
    monkeypatch.setattr(
        AUDIT,
        "FROZEN_POLICY_SHA256",
        hashlib.sha256(policy_path.read_bytes()).hexdigest(),
    )


def test_current_policy_joins_all_692_rows_and_locks_reviewed_distribution(
    frozen_inventory,
) -> None:
    inventory_path, csv_bytes = frozen_inventory
    assert hashlib.sha256(csv_bytes).hexdigest() == FROZEN_CSV_SHA256

    identity, rows = AUDIT.load_inventory(inventory_path)
    policy = AUDIT.load_policy(POLICY_PATH)
    report = AUDIT.build_audit(identity, rows, policy)

    assert len(report.rows) == 692
    assert {row["row_key"] for row in report.rows} == {
        row["row_key"] for row in rows
    }
    assert report.classification_counts == {
        "REQUIRE_ZERO": 449,
        "VERIFY_ZERO_AND_EXPECTED": 145,
        "COUNT_EQ_0": 13,
        "COUNT_EQ_1": 3,
        "COUNT_LE_1": 1,
        "COUNT_NUMERIC_SUBSTRING": 37,
        "EXPECTED_ERROR_FALLBACK_MASKING": 30,
        "GREP_WC_UPSTREAM_MASKING": 1,
        "NEGATED_TOKEN_SUBSTRING_COLLISION": 2,
        "PRE_POST_EMPTY_EQUALITY": 4,
        "MASKED_ASSERTION": 1,
        "OBSERVE_ONLY": 1,
        "TRANSPORT_TERMINATING": 2,
        "REVIEW_REQUIRED": 3,
    }
    assert report.blocking_rows == 18
    assert report.advisory_oracle_rows == 74
    assert report.runtime_review_rows == 6


def test_sha_bound_policy_and_result_are_pinned_to_lf() -> None:
    attributes = (REPO / ".gitattributes").read_text(encoding="utf-8")

    assert (
        "scripts/canonical_shell_rc_risk_policy_v1.json text eol=lf"
        in attributes
    )
    assert (
        '"THOR2_J - Settings/RESULT_2026-07-24.md" text eol=lf'
        in attributes
    )


def test_policy_semantics_distinguish_inverted_count_masking_and_transport(
    frozen_inventory,
) -> None:
    inventory_path, _csv_bytes = frozen_inventory
    identity, rows = AUDIT.load_inventory(inventory_path)
    report = AUDIT.build_audit(
        identity,
        rows,
        AUDIT.load_policy(POLICY_PATH),
    )
    by_source_step = {
        (row["source_path"], row["step_index"]): row
        for row in report.rows
    }

    zero_count = by_source_step[
        ("exported_ss_call/SS_TC01_permission_denied.yaml", "11")
    ]
    assert zero_count["classification"] == "COUNT_EQ_0"
    assert zero_count["reason_code"] == "GREP_ZERO_RC_POLARITY_INVERTED"
    assert zero_count["remediation_requirement"] == "STDOUT_PREDICATE_REQUIRED"

    count_one = by_source_step[
        ("exported_ss_call/SS_TC02_permission_allow_idle.yaml", "11")
    ]
    assert count_one["classification"] == "COUNT_EQ_1"
    assert count_one["remediation_requirement"] == "STDOUT_PREDICATE_REQUIRED"

    masked = by_source_step[
        ("ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml", "11")
    ]
    assert masked["classification"] == "MASKED_ASSERTION"
    assert masked["reason_code"] == "OR_FALLBACK_MASKS_ASSERTION"

    reboot = by_source_step[
        ("exported_tc1/BUG_25175_LGU_APN_menu.yaml", "75")
    ]
    assert reboot["classification"] == "TRANSPORT_TERMINATING"
    assert reboot["remediation_requirement"] == "RUNTIME_REVIEW_REQUIRED"

    verify_zero = by_source_step[
        (
            "ODIN2 - My gallary/functional/photo/"
            "GAL_FUNC_03_photo_multi_select.yaml",
            "24",
        )
    ]
    assert verify_zero["action"] == "verify_shell"
    assert verify_zero["expected"] == "0"
    assert verify_zero["classification"] == "COUNT_EQ_0"
    assert (
        verify_zero["reason_code"]
        == "VERIFY_GREP_ZERO_RC_POLARITY_INVERTED"
    )

    numeric_substring = by_source_step[
        ("ODIN2 - My gallary/GAL_SMOKE_ODIN2.yaml", "3")
    ]
    assert numeric_substring["classification"] == (
        "COUNT_NUMERIC_SUBSTRING"
    )
    assert numeric_substring["expected"] == "27"

    error_fallback = by_source_step[
        (
            "ODIN2 - minifile/functional/browse/"
            "MNF_FUNC_07_folder_enter_title.yaml",
            "10",
        )
    ]
    assert error_fallback["classification"] == (
        "EXPECTED_ERROR_FALLBACK_MASKING"
    )

    upstream_masking = by_source_step[
        (
            "ODIN2 - minifile/functional/selection/"
            "MNF_FUNC_34_selection_all_toggle.yaml",
            "20",
        )
    ]
    assert upstream_masking["classification"] == (
        "GREP_WC_UPSTREAM_MASKING"
    )

    explicit_special_cases = {
        (
            "ODIN2 - My gallary/functional/photo/"
            "GAL_FUNC_05_photo_multi_delete_trash_flow.yaml",
            "23",
        ): "REVIEW_REQUIRED",
        (
            "ODIN2 - My gallary/functional/photo/"
            "GAL_FUNC_12_photo_edit_save_copy.yaml",
            "18",
        ): "REVIEW_REQUIRED",
        (
            "ODIN2 - My gallary/functional/video/"
            "GAL_FUNC_16_video_orientation.yaml",
            "8",
        ): "OBSERVE_ONLY",
        (
            "ODIN2 - minifile/functional/ops/"
            "MNF_FUNC_12_ops_rename.yaml",
            "22",
        ): "REVIEW_REQUIRED",
    }
    for source_step, classification in explicit_special_cases.items():
        assert by_source_step[source_step]["classification"] == classification


@pytest.mark.parametrize(
    ("classification", "returncode", "stdout", "expected"),
    [
        ("COUNT_EQ_0", 1, "0\n", True),
        ("COUNT_EQ_0", 0, "1\n", False),
        ("COUNT_EQ_0", 2, "0\n", False),
        ("COUNT_EQ_1", 0, "1\n", True),
        ("COUNT_EQ_1", 0, "10\n", False),
        ("COUNT_EQ_1", 1, "1\n", False),
        ("COUNT_LE_1", 0, "1\n", True),
        ("COUNT_LE_1", 1, "0\n", True),
        ("COUNT_LE_1", 0, "2\n", False),
    ],
)
def test_reviewed_count_contract_truth_table(
    classification: str,
    returncode: int,
    stdout: str,
    expected: bool,
) -> None:
    assert (
        AUDIT.observation_satisfies_reviewed_count_contract(
            classification,
            returncode=returncode,
            stdout=stdout,
        )
        is expected
    )


def test_verify_shell_defaults_to_zero_rc_plus_expected_predicate(
    tmp_path: Path,
) -> None:
    row = _synthetic_row(
        action="verify_shell",
        command="getprop ro.product.model",
        expected="AT-M140",
        timeout_ms="30000",
    )
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )

    identity, rows = AUDIT.load_inventory(inventory_path)
    report = AUDIT.build_audit(
        identity,
        rows,
        AUDIT.load_policy(policy_path),
    )

    assert report.classification_counts[
        "VERIFY_ZERO_AND_EXPECTED"
    ] == 1
    assert report.rows[0]["canonical_rc_contract"] == (
        "rc == 0 and expected substring in stdout"
    )
    assert report.rows[0]["expected"] == "AT-M140"
    assert report.rows[0]["timeout_ms"] == "30000"


@pytest.mark.parametrize(
    ("command", "expected", "classification"),
    [
        (
            "logcat -d | grep -c EVENT || echo 0",
            "0",
            "EXPECTED_ERROR_FALLBACK_MASKING",
        ),
        (
            "grep -o EVENT /data/local/tmp/log | wc -l",
            "0",
            "GREP_WC_UPSTREAM_MASKING",
        ),
        (
            "logcat -d | grep -c EVENT || echo 0",
            "1",
            "COUNT_NUMERIC_SUBSTRING",
        ),
        (
            "ls /data/local/tmp/*.txt | wc -l",
            "27",
            "COUNT_NUMERIC_SUBSTRING",
        ),
        (
            "check && echo GRANTED || echo NOT_GRANTED",
            "GRANTED",
            "NEGATED_TOKEN_SUBSTRING_COLLISION",
        ),
        (
            "ls /missing && echo STILL || echo MOVED",
            "MOVED",
            "EXPECTED_ERROR_FALLBACK_MASKING",
        ),
        (
            "PRE=$(cat /missing/a); POST=$(stat -c %s /missing/b); "
            '[ "$PRE" = "$POST" ] && echo UNCHANGED || echo CHANGED',
            "UNCHANGED",
            "PRE_POST_EMPTY_EQUALITY",
        ),
    ],
)
def test_verify_oracles_are_never_default_safe(
    tmp_path: Path,
    command: str,
    expected: str,
    classification: str,
) -> None:
    row = _synthetic_row(
        action="verify_shell",
        command=command,
        expected=expected,
        timeout_ms="30000",
    )
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )

    identity, rows = AUDIT.load_inventory(inventory_path)
    report = AUDIT.build_audit(
        identity,
        rows,
        AUDIT.load_policy(policy_path),
    )

    assert report.rows[0]["classification"] == classification
    assert (
        report.rows[0]["remediation_requirement"]
        == "STDOUT_PREDICATE_REQUIRED"
    )


def test_load_inventory_rejects_duplicate_row_key(tmp_path: Path) -> None:
    row = _synthetic_row()
    path = tmp_path / "duplicate.csv"
    path.write_bytes(_synthetic_inventory_bytes([row, row]))

    with pytest.raises(AUDIT.AuditInputError, match="duplicate row_key"):
        AUDIT.load_inventory(path)


def test_build_audit_rejects_policy_command_hash_drift(tmp_path: Path) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [
                {
                    "row_key": row["row_key"],
                    "action": "shell",
                    "command_sha256": "0" * 64,
                "classification": "COUNT_EQ_0",
                "reason_code": "GREP_ZERO_RC_POLARITY_INVERTED",
                "evidence": "0이어야 정상",
            }
        ],
    )

    identity, rows = AUDIT.load_inventory(inventory_path)
    with pytest.raises(AUDIT.AuditInputError, match="command hash"):
        AUDIT.build_audit(identity, rows, AUDIT.load_policy(policy_path))


def test_build_audit_rejects_policy_entry_missing_from_inventory(
    tmp_path: Path,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [
                {
                    "row_key": "a" * 40 + ":missing.yaml#1",
                    "action": "shell",
                    "command_sha256": "1" * 64,
                "classification": "REVIEW_REQUIRED",
                "reason_code": "MISSING",
                "evidence": "missing",
            }
        ],
    )

    identity, rows = AUDIT.load_inventory(inventory_path)
    with pytest.raises(AUDIT.AuditInputError, match="not present"):
        AUDIT.build_audit(identity, rows, AUDIT.load_policy(policy_path))


def test_build_audit_rejects_policy_action_drift(tmp_path: Path) -> None:
    row = _synthetic_row(action="shell")
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [
            {
                "row_key": row["row_key"],
                "action": "verify_shell",
                "command_sha256": row["command_sha256"],
                "classification": "COUNT_EQ_0",
                "reason_code": "VERIFY_GREP_ZERO_RC_POLARITY_INVERTED",
                "evidence": "expected zero",
            }
        ],
    )

    identity, rows = AUDIT.load_inventory(inventory_path)
    with pytest.raises(AUDIT.AuditInputError, match="action mismatch"):
        AUDIT.build_audit(identity, rows, AUDIT.load_policy(policy_path))


def test_load_policy_rejects_deleted_override_against_manifest(
    tmp_path: Path,
) -> None:
    row = _synthetic_row()
    overrides = [
        {
            "row_key": row["row_key"],
            "action": "shell",
            "command_sha256": row["command_sha256"],
            "classification": "COUNT_EQ_0",
            "reason_code": "GREP_ZERO_RC_POLARITY_INVERTED",
            "evidence": "expected zero",
        }
    ]
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, "f" * 64, overrides)
    document = json.loads(policy_path.read_text(encoding="utf-8"))
    document["overrides"] = []
    policy_path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(AUDIT.AuditInputError, match="override count"):
        AUDIT.load_policy(policy_path)


def test_load_policy_rejects_semantic_override_drift_against_manifest(
    tmp_path: Path,
) -> None:
    row = _synthetic_row()
    override = {
        "row_key": row["row_key"],
        "action": "shell",
        "command_sha256": row["command_sha256"],
        "classification": "COUNT_EQ_0",
        "reason_code": "GREP_ZERO_RC_POLARITY_INVERTED",
        "evidence": "reviewed evidence",
    }
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, "f" * 64, [override])
    document = json.loads(policy_path.read_text(encoding="utf-8"))
    document["overrides"][0]["classification"] = "REVIEW_REQUIRED"
    document["overrides"][0]["reason_code"] = "SEMANTIC_REWRITE"
    policy_path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(AUDIT.AuditInputError, match="override identity"):
        AUDIT.load_policy(policy_path)


def test_load_policy_rejects_duplicate_override(tmp_path: Path) -> None:
    row = _synthetic_row()
    override = {
        "row_key": row["row_key"],
        "action": "shell",
        "command_sha256": row["command_sha256"],
        "classification": "COUNT_EQ_0",
        "reason_code": "GREP_ZERO_RC_POLARITY_INVERTED",
        "evidence": "expected zero",
    }
    policy_path = tmp_path / "policy.json"
    _write_policy(policy_path, "f" * 64, [override, override])

    with pytest.raises(AUDIT.AuditInputError, match="duplicate policy"):
        AUDIT.load_policy(policy_path)


def test_main_policy_mutation_before_write_returns_three_without_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    output = tmp_path / "out"
    original_render = AUDIT.render_artifacts

    def mutate_policy(report):
        artifacts = original_render(report)
        policy_path.write_bytes(policy_path.read_bytes() + b"\n")
        return artifacts

    monkeypatch.setattr(AUDIT, "render_artifacts", mutate_policy)

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
            ]
        )
        == 3
    )
    assert not output.exists()


def test_main_inventory_mutation_before_write_returns_three_without_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    output = tmp_path / "out"
    original_render = AUDIT.render_artifacts

    def mutate_inventory(report):
        artifacts = original_render(report)
        inventory_path.write_bytes(inventory_path.read_bytes() + b"\n")
        return artifacts

    monkeypatch.setattr(AUDIT, "render_artifacts", mutate_inventory)

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
            ]
        )
        == 3
    )
    assert not output.exists()


def test_main_verify_determinism_is_host_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    output = tmp_path / "out"

    def unexpected_subprocess(*_args, **_kwargs):
        raise AssertionError("audit must not invoke subprocess or ADB")

    import src.cli as cli

    def unexpected_adb(*_args, **_kwargs):
        raise AssertionError("audit must not construct ADB")

    monkeypatch.setattr(cli, "ADB", unexpected_adb)
    monkeypatch.setattr("subprocess.run", unexpected_subprocess)

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
                "--verify-determinism",
            ]
        )
        == 0
    )
    assert len(list(output.glob("*/shell_rc_risk_matrix.csv"))) == 1
    assert len(list(output.glob("*/SUMMARY.md"))) == 1


def test_main_rejects_csv_sha_mismatch_without_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    inventory_path.write_bytes(inventory_bytes + b"\n")
    output = tmp_path / "out"

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()


def test_main_rejects_added_override_even_with_recomputed_self_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [
            {
                "row_key": row["row_key"],
                "action": row["action"],
                "command_sha256": row["command_sha256"],
                "classification": "COUNT_EQ_0",
                "reason_code": "UNAPPROVED_OVERRIDE",
                "evidence": "self-consistent but not externally approved",
            }
        ],
    )
    output = tmp_path / "out"

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()


def test_main_policy_mutation_during_publish_returns_three_without_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _synthetic_row()
    inventory_path = tmp_path / "inventory.csv"
    inventory_bytes = _synthetic_inventory_bytes([row])
    inventory_path.write_bytes(inventory_bytes)
    policy_path = tmp_path / "policy.json"
    _write_policy(
        policy_path,
        hashlib.sha256(inventory_bytes).hexdigest(),
        [],
    )
    _bind_main_contract(monkeypatch, inventory_bytes, policy_path)
    output = tmp_path / "out"
    original_replace = AUDIT.os.replace

    def mutate_after_publish(source, destination):
        original_replace(source, destination)
        policy_path.write_bytes(policy_path.read_bytes() + b"\n")

    monkeypatch.setattr(AUDIT.os, "replace", mutate_after_publish)

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(inventory_path),
                "--policy",
                str(policy_path),
                "--out-dir",
                str(output),
            ]
        )
        == 3
    )
    assert not list(output.glob("*"))


def test_write_artifacts_is_atomic_when_summary_write_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "out"
    input_digest = "d" * 64
    original_write_bytes = Path.write_bytes

    def fail_summary(path: Path, data: bytes) -> int:
        if path.name == "SUMMARY.md":
            raise OSError("synthetic summary write failure")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_summary)

    with pytest.raises(OSError, match="synthetic summary"):
        AUDIT._write_artifacts(
            output,
            input_digest,
            b"csv",
            b"summary",
        )
    assert not (output / input_digest[:16]).exists()


def test_write_artifacts_rejects_extra_existing_entry(tmp_path: Path) -> None:
    output = tmp_path / "out"
    input_digest = "e" * 64
    destination = AUDIT._write_artifacts(
        output,
        input_digest,
        b"csv",
        b"summary",
    )
    (destination / "unexpected.txt").write_text(
        "not part of the artifact pair",
        encoding="utf-8",
    )

    with pytest.raises(AUDIT.AuditInfraError, match="entry set"):
        AUDIT._write_artifacts(
            output,
            input_digest,
            b"csv",
            b"summary",
        )


def test_render_artifacts_are_byte_deterministic_and_csv_safe(
    frozen_inventory,
) -> None:
    inventory_path, _csv_bytes = frozen_inventory
    identity, rows = AUDIT.load_inventory(inventory_path)
    report = AUDIT.build_audit(
        identity,
        rows,
        AUDIT.load_policy(POLICY_PATH),
    )

    first = AUDIT.render_artifacts(report)
    second = AUDIT.render_artifacts(report)

    assert first == second
    rendered_rows = list(
        csv.DictReader(io.StringIO(first[0].decode("utf-8")))
    )
    assert len(rendered_rows) == 692
    assert rendered_rows[0]["input_csv_sha256"] == FROZEN_CSV_SHA256


def test_render_artifacts_uses_supplied_tool_hash_without_reread(
    frozen_inventory,
    monkeypatch,
) -> None:
    inventory_path, _csv_bytes = frozen_inventory
    identity, rows = AUDIT.load_inventory(inventory_path)
    report = AUDIT.build_audit(
        identity,
        rows,
        AUDIT.load_policy(POLICY_PATH),
    )
    frozen_tool_sha256 = "a" * 64

    monkeypatch.setattr(AUDIT, "_tool_sha256", lambda: "b" * 64)
    _csv_bytes, summary_bytes = AUDIT.render_artifacts(
        report,
        tool_sha256=frozen_tool_sha256,
    )
    summary = summary_bytes.decode("utf-8")

    assert f"- Tool SHA-256: `{frozen_tool_sha256}`" in summary
    assert (
        f"- Input digest: "
        f"`{AUDIT._input_digest(report, frozen_tool_sha256)}`"
    ) in summary
    assert "b" * 64 not in summary


def test_two_independent_main_runs_publish_identical_artifacts(
    frozen_inventory,
    tmp_path: Path,
) -> None:
    inventory_path, _csv_bytes = frozen_inventory
    output_a = tmp_path / "run-a"
    output_b = tmp_path / "run-b"
    argv = [
        "--inventory",
        str(inventory_path),
        "--policy",
        str(POLICY_PATH),
        "--verify-determinism",
    ]

    assert AUDIT.main([*argv, "--out-dir", str(output_a)]) == 0
    assert AUDIT.main([*argv, "--out-dir", str(output_b)]) == 0

    artifacts_a = {
        path.name: path.read_bytes()
        for path in next(output_a.iterdir()).iterdir()
    }
    artifacts_b = {
        path.name: path.read_bytes()
        for path in next(output_b.iterdir()).iterdir()
    }
    assert artifacts_a == artifacts_b
    assert set(artifacts_a) == {
        "shell_rc_risk_matrix.csv",
        "SUMMARY.md",
    }


def test_main_invalid_inventory_writes_nothing(tmp_path: Path) -> None:
    bad_inventory = tmp_path / "bad.csv"
    bad_inventory.write_text("not,the,inventory\n", encoding="utf-8")
    output = tmp_path / "out"

    assert (
        AUDIT.main(
            [
                "--inventory",
                str(bad_inventory),
                "--policy",
                str(POLICY_PATH),
                "--out-dir",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()
