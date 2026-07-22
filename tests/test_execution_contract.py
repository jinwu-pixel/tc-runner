"""Slice 1a Task 2 canonical execution-contract tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import src.execution_contract as execution_contract
from src.execution_contract import (
    derive_action_required,
    normalize_step,
    normalize_tc,
    validate_canonical_tc,
)


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "tc_step_schema.json"
STAGE2_PROMPT_PATH = ROOT / "tc_prompts" / "STAGE2_COMPILE.md"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _codes(result) -> list[str]:
    return [finding.code for finding in result.findings]


def test_corpus_normalization_is_identity():
    paths = sorted((ROOT / "golden_tc_set").glob("*.yaml"))
    paths += sorted((ROOT / "exported_tc1").glob("*.yaml"))
    paths += [
        ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_01_app_launch.yaml",
        ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_02_scroll_more_menu.yaml",
    ]

    assert len(paths) == 30
    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        result = normalize_tc(document, source=path.as_posix())
        assert result.value == document, path
        assert result.blocking is False, path


def test_primary_corpus_execution_type_matches_shared_derivation():
    paths = sorted((ROOT / "golden_tc_set").glob("*.yaml"))
    paths += sorted((ROOT / "exported_tc1").glob("*.yaml"))
    paths += [
        ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_01_app_launch.yaml",
        ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_02_scroll_more_menu.yaml",
    ]

    assert len(paths) == 30
    mismatches = []
    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        observed = document["metadata"]["execution_type"]
        derived = execution_contract.derive_execution_metadata(
            document["steps"]
        )["execution_type"]
        if observed != derived:
            mismatches.append((path.relative_to(ROOT).as_posix(), observed, derived))

    assert mismatches == []


@pytest.mark.parametrize(
    ("raw", "expected", "canonical_field", "observed_field"),
    [
        (
            {"action": "verify_text", "text": "Wi-Fi"},
            {"action": "verify_text", "target": "Wi-Fi"},
            "target",
            "text",
        ),
        (
            {"action": "tap_id", "id": "com.example:id/ok"},
            {"action": "tap_id", "target": "com.example:id/ok"},
            "target",
            "id",
        ),
        (
            {"action": "key", "keycode": "KEYCODE_HOME"},
            {"action": "key", "key": "KEYCODE_HOME"},
            "key",
            "keycode",
        ),
    ],
)
def test_single_alias_normalizes_without_mutating_source(
    raw, expected, canonical_field, observed_field
):
    before = deepcopy(raw)

    result = normalize_step(raw, path="steps[0]")

    assert result.value == expected
    assert raw == before
    assert _codes(result) == ["ALIAS_NORMALIZED"]
    finding = result.findings[0]
    assert finding.path == f"steps[0].{observed_field}"
    assert finding.severity == "INFO"
    assert finding.canonical_field == canonical_field
    assert finding.observed_field == observed_field


def test_swipe_start_aliases_preserve_endpoint_and_finding_order():
    raw = {
        "action": "swipe",
        "x1": 10,
        "y1": 20,
        "x2": 30,
        "y2": 40,
        "duration": 300,
    }

    result = normalize_step(raw, path="steps[2]")

    assert result.value == {
        "action": "swipe",
        "x": 10,
        "y": 20,
        "x2": 30,
        "y2": 40,
        "duration": 300,
    }
    assert [finding.path for finding in result.findings] == [
        "steps[2].x1",
        "steps[2].y1",
    ]
    assert _codes(result) == ["ALIAS_NORMALIZED", "ALIAS_NORMALIZED"]


def test_seconds_conversion_is_exact_ms():
    result = normalize_step(
        {"action": "wait", "seconds": "1.001"}, path="steps[0]"
    )

    assert result.value == {"action": "wait", "duration": 1001}
    assert _codes(result) == ["ALIAS_NORMALIZED"]


def test_seconds_decimal_exponent_is_exact_ms():
    result = normalize_step(
        {"action": "wait", "seconds": "1e-3"}, path="steps[0]"
    )

    assert result.value["duration"] == 1
    assert not result.blocking


def test_seconds_conversion_preserves_milliseconds_beyond_decimal_context_precision():
    result = normalize_step(
        {
            "action": "wait",
            "seconds": "1234567890123456789012345678.001",
        },
        path="steps[0]",
    )

    assert result.value["duration"] == 1234567890123456789012345678001
    assert not result.blocking


@pytest.mark.parametrize("seconds", [-1, True, "not-a-number", "0.0005", float("inf")])
def test_invalid_or_sub_millisecond_seconds_blocks_and_is_fail_sticky(seconds):
    raw = {"action": "wait", "seconds": seconds}

    first = normalize_step(raw, path="steps[0]")
    second = normalize_step(first.value, path="steps[0]")

    assert first.value == raw
    assert second.value == raw
    assert first.blocking and second.blocking
    assert _codes(first) == ["INVALID_UNIT"]
    assert _codes(second) == ["INVALID_UNIT"]


def test_equal_duplicate_keeps_canonical_and_drops_alias():
    result = normalize_step(
        {"action": "wait", "duration": 1500, "seconds": "1.5"},
        path="steps[0]",
    )

    assert result.value == {"action": "wait", "duration": 1500}
    assert _codes(result) == ["ALIAS_DUPLICATE"]
    assert not result.blocking


def test_conflicting_alias_is_blocking_and_preserves_both_values():
    raw = {"action": "verify_text", "target": "A", "text": "B"}

    first = normalize_step(raw, path="steps[0]")
    second = normalize_step(first.value, path="steps[0]")

    assert first.value == raw
    assert second.value == raw
    assert first.blocking and second.blocking
    assert _codes(first) == ["ALIAS_CONFLICT"]
    assert _codes(second) == ["ALIAS_CONFLICT"]


def test_semantic_duplicate_requires_same_json_type():
    result = normalize_step(
        {"action": "key", "key": 1, "keycode": True}, path="steps[0]"
    )

    assert result.blocking
    assert _codes(result) == ["ALIAS_CONFLICT"]


def test_input_text_text_is_not_selector_alias():
    raw = {"action": "input_text", "text": "fixture-input"}

    result = normalize_step(raw, path="steps[0]")

    assert result.value == raw
    assert "target" not in result.value
    assert result.findings == ()


def test_key_sequence_delay_seconds_is_observed_not_normalized():
    raw = {"action": "key_sequence", "keys": [19, 20], "delay": 0.25}

    result = normalize_step(raw, path="steps[0]")

    assert result.value == raw
    assert result.findings == ()


def test_unknown_step_field_is_preserved_and_nonblocking():
    raw = {"action": "wait", "duration": 1, "future_hint": {"mode": "x"}}

    result = normalize_step(raw, path="steps[0]")

    assert result.value == raw
    assert not result.blocking
    assert _codes(result) == ["UNDECLARED_STEP_FIELD"]
    assert result.findings[0].path == "steps[0].future_hint"


def test_alias_name_outside_declared_action_scope_is_undeclared():
    raw = {"action": "wait", "duration": 1, "id": "wrong-scope"}

    result = normalize_step(raw, path="steps[0]")

    assert result.value == raw
    assert not result.blocking
    assert _codes(result) == ["UNDECLARED_STEP_FIELD"]
    assert result.findings[0].path == "steps[0].id"


def test_normalizer_returns_a_deep_copy():
    raw = {
        "action": "verify_focus_moved",
        "trigger_action": "key",
        "trigger_step": {"action": "key", "key": "KEYCODE_DPAD_DOWN"},
    }

    result = normalize_step(raw, path="steps[0]")
    result.value["trigger_step"]["key"] = "KEYCODE_DPAD_UP"

    assert raw["trigger_step"]["key"] == "KEYCODE_DPAD_DOWN"


def test_successful_normalization_is_idempotent():
    first = normalize_step(
        {"action": "swipe", "x1": 1, "y1": 2, "x2": 3, "y2": 4},
        path="steps[0]",
    )
    second = normalize_step(first.value, path="steps[0]")

    first_json = json.dumps(first.value, sort_keys=True, separators=(",", ":"))
    second_json = json.dumps(second.value, sort_keys=True, separators=(",", ":"))
    assert second_json == first_json
    assert second.findings == ()


def test_tc_normalization_handles_top_level_metadata_and_steps_in_order():
    raw = {
        "name": "LEGACY_01",
        "metadata": {
            "automation_class": "SEMI_AUTO",
            "runnable": True,
            "execution_type": "AUTO",
            "manual_detail": "NONE",
        },
        "steps": [{"action": "wait", "seconds": 0.25}],
    }

    result = normalize_tc(raw, source="fixture.yaml")

    assert result.value["tc_name"] == "LEGACY_01"
    assert "name" not in result.value
    assert result.value["metadata"]["tc_class"] == "SEMI_AUTO"
    assert "automation_class" not in result.value["metadata"]
    assert result.value["steps"] == [{"action": "wait", "duration": 250}]
    assert [finding.path for finding in result.findings] == [
        "fixture.yaml.name",
        "fixture.yaml.metadata.automation_class",
        "fixture.yaml.steps[0].seconds",
    ]
    assert raw["name"] == "LEGACY_01"
    assert raw["steps"][0]["seconds"] == 0.25


def test_invalid_automation_class_is_not_promoted_to_canonical_metadata():
    raw = {
        "tc_name": "T1",
        "metadata": {"automation_class": "MANUAL_REQUIRED"},
        "steps": [{"action": "wait", "duration": 1}],
    }

    result = normalize_tc(raw, source="fixture.yaml")

    assert result.value["metadata"] == {"automation_class": "MANUAL_REQUIRED"}
    assert result.findings == ()


def test_top_level_alias_conflict_is_blocking_and_not_laundered():
    raw = {"tc_name": "CANONICAL", "name": "LEGACY", "steps": []}

    result = normalize_tc(raw, source="fixture.yaml")

    assert result.value == raw
    assert result.blocking
    assert _codes(result) == ["ALIAS_CONFLICT"]


def test_schema_required_fields_come_from_shared_derivation():
    required = derive_action_required(_schema())

    assert required["tap_id"] == ("action", "target")
    assert required["tap_xy"] == ("action", "x", "y")
    assert required["wait"] == ("action", "duration")
    assert required["screenshot"] == ("action", "name")


def test_canonical_validation_accepts_zero_numeric_operands():
    tc = {
        "tc_name": "ZERO_VALUES",
        "metadata": {
            "runnable": True,
            "tc_class": "FULL_AUTO",
            "execution_type": "AUTO",
            "manual_detail": "NONE",
        },
        "steps": [
            {"action": "tap_xy", "x": 0, "y": 0},
            {"action": "wait", "duration": 0},
            {"action": "key", "key": 0},
        ],
    }

    assert validate_canonical_tc(tc, _schema()) == []


def test_screenshot_name_is_schema_defined_and_step_remains_open():
    step_schema = _schema()["$defs"]["step"]

    assert step_schema["properties"]["name"]["type"] == "string"
    assert "additionalProperties" not in step_schema
    assert derive_action_required(_schema())["screenshot"] == ("action", "name")


def test_verify_shell_timeout_is_documented_as_ms():
    timeout_schema = _schema()["$defs"]["step"]["properties"]["timeout"]

    assert "ms" in timeout_schema["description"].lower()
    assert "30000" in timeout_schema["description"]


def test_key_sequence_delay_is_documented_as_seconds():
    delay_schema = _schema()["$defs"]["step"]["properties"]["delay"]

    assert "초" in delay_schema["description"] or "second" in delay_schema[
        "description"
    ].lower()


def test_stage2_emitted_field_table_uses_canonical_contract_names():
    prompt = STAGE2_PROMPT_PATH.read_text(encoding="utf-8")

    assert "target: string | null          # tap_text, tap_id" in prompt
    assert "keys:" in prompt and "key_sequence" in prompt
    assert "delay:" in prompt and "seconds" in prompt
    assert "name:" in prompt and "screenshot" in prompt
    assert "derive_action_required" in prompt


def test_derive_execution_metadata_follows_step4_precedence():
    assert hasattr(execution_contract, "derive_execution_metadata")
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "버튼을 터치하세요",
            },
            {
                "action": "manual_pause",
                "execution_mode": "EXTERNAL_EVENT",
                "description": "보조폰에서 전화를 수신하세요",
            },
        ]
    )

    assert result["execution_type"] == "EXTERNAL_EVENT"
    assert result["has_manual_steps"] is True


def test_derive_execution_metadata_uses_description_external_event_trigger():
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "보조폰에서 전화를 수신하세요",
            }
        ]
    )

    assert result == {
        "execution_type": "EXTERNAL_EVENT",
        "manual_detail": "CALL_RECEIVE",
        "has_manual_steps": True,
    }


def test_derive_execution_metadata_ignores_automatic_step_description_markers():
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "shell",
                "execution_mode": "SHELL_AUTO",
                "description": "비행기 모드 중 긴급호 118 자동 발신",
                "command": "am start -a android.intent.action.CALL",
            }
        ]
    )

    assert result == {
        "execution_type": "AUTO",
        "manual_detail": "NONE",
        "has_manual_steps": False,
    }


def test_derive_execution_metadata_does_not_treat_inbox_as_external_dependency():
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "문자 수신함을 확인하세요",
            }
        ]
    )

    assert result == {
        "execution_type": "MANUAL_LOCAL",
        "manual_detail": "UNKNOWN",
        "has_manual_steps": True,
    }


def test_derive_execution_metadata_honors_explicit_external_event_mode():
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "EXTERNAL_EVENT",
                "description": "담당자가 사전 조건을 처리하세요",
            }
        ]
    )

    assert result["execution_type"] == "EXTERNAL_EVENT"


def test_canonical_validation_uses_shared_description_dependency_rule():
    tc = {
        "tc_name": "MANUAL_CALL_RECEIVE",
        "metadata": {
            "runnable": True,
            "tc_class": "SEMI_AUTO",
            "execution_type": "EXTERNAL_EVENT",
            "manual_detail": "CALL_RECEIVE",
            "has_manual_steps": True,
        },
        "steps": [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "보조폰에서 전화를 수신하세요",
            }
        ],
    }

    assert validate_canonical_tc(tc, _schema()) == []


def test_derive_execution_metadata_does_not_match_sim_inside_word():
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "Run the simulation and touch the button",
            }
        ]
    )

    assert result["manual_detail"] == "BUTTON_TOUCH"


def test_derive_execution_metadata_orders_multiple_detail_tokens():
    assert hasattr(execution_contract, "derive_execution_metadata")
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "EXTERNAL_EVENT",
                "description": "보조폰에서 전화 수신 후 안전함 버튼을 터치하세요",
            }
        ]
    )

    assert result["manual_detail"] == "CALL_RECEIVE|BUTTON_TOUCH"


def test_derive_execution_metadata_uses_unknown_for_unclassified_manual():
    assert hasattr(execution_contract, "derive_execution_metadata")
    result = execution_contract.derive_execution_metadata(
        [
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "담당자가 사전 조건을 처리하세요",
            }
        ]
    )

    assert result == {
        "execution_type": "MANUAL_LOCAL",
        "manual_detail": "UNKNOWN",
        "has_manual_steps": True,
    }


def test_derive_execution_metadata_does_not_mutate_steps():
    assert hasattr(execution_contract, "derive_execution_metadata")
    steps = [
        {
            "action": "manual_pause",
            "execution_mode": "MANUAL_REQUIRED",
            "description": "앱 설치 후 버튼을 터치하세요",
        }
    ]
    before = deepcopy(steps)

    execution_contract.derive_execution_metadata(steps)

    assert steps == before
