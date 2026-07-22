from pathlib import Path
import pytest

from src.tc_loader import load_tc, validate_tc, TCValidationError


def test_load_tc_valid(tmp_path):
    tc_file = tmp_path / "test.yaml"
    tc_file.write_text("""
name: Wi-Fi 테스트
description: Wi-Fi 연결 확인
steps:
  - action: tap_text
    text: "설정"
  - action: wait
    seconds: 2
  - action: verify_text
    text: "연결됨"
""", encoding="utf-8")

    tc = load_tc(tc_file)
    assert tc["name"] == "Wi-Fi 테스트"
    assert tc["description"] == "Wi-Fi 연결 확인"
    assert len(tc["steps"]) == 3
    assert tc["steps"][0]["action"] == "tap_text"


def test_load_tc_missing_name(tmp_path):
    tc_file = tmp_path / "bad.yaml"
    tc_file.write_text("""
steps:
  - action: wait
    seconds: 1
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="name"):
        load_tc(tc_file)


def test_load_tc_missing_steps(tmp_path):
    tc_file = tmp_path / "bad2.yaml"
    tc_file.write_text("""
name: 빈 테스트
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="steps"):
        load_tc(tc_file)


def test_load_tc_invalid_action(tmp_path):
    tc_file = tmp_path / "bad3.yaml"
    tc_file.write_text("""
name: 잘못된 액션
steps:
  - action: fly_to_moon
""", encoding="utf-8")

    with pytest.raises(TCValidationError, match="fly_to_moon"):
        load_tc(tc_file)


def test_load_tc_with_verify_gone_is_accepted(tmp_path):
    # PR 0: verify_gone drift fix — loader must no longer reject this action
    tc_file = tmp_path / "verify_gone.yaml"
    tc_file.write_text("""
name: verify_gone load test
steps:
  - action: tap_text
    text: "다음"
  - action: verify_gone
    target: "이전 화면 타이틀"
""", encoding="utf-8")

    tc = load_tc(tc_file)
    assert tc["steps"][1]["action"] == "verify_gone"


def test_schema_action_enum_matches_loader_valid_actions():
    # Drift sentinel: tc_step_schema.json action enum must equal tc_loader.VALID_ACTIONS.
    # If they diverge, a TC can pass validate_tc.py but be rejected at runtime (or vice versa).
    import json
    from src.tc_loader import VALID_ACTIONS

    schema_path = Path(__file__).parent.parent / "tc_step_schema.json"
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    schema_actions = set(schema["$defs"]["step"]["properties"]["action"]["enum"])

    only_in_schema = schema_actions - VALID_ACTIONS
    only_in_loader = VALID_ACTIONS - schema_actions
    assert schema_actions == VALID_ACTIONS, (
        f"schema/loader drift — only_in_schema={only_in_schema}, only_in_loader={only_in_loader}"
    )


def test_action_runner_dispatch_supports_all_valid_actions(tmp_path):
    # Drift sentinel: every action in VALID_ACTIONS must be dispatched by ActionRunner.
    # Probe via _dispatch with a minimal step; handlers raise on missing required fields,
    # which still proves the action is dispatched (only "Unknown action: X" indicates drift).
    from unittest.mock import MagicMock
    from src.action_runner import ActionRunner
    from src.tc_loader import VALID_ACTIONS

    runner = ActionRunner(adb=MagicMock(), screenshot_dir=tmp_path)
    for action in VALID_ACTIONS:
        try:
            _, message = runner._dispatch(action, {"action": action})
        except Exception:
            continue
        assert not message.startswith("Unknown action"), (
            f"VALID_ACTIONS contains '{action}' but ActionRunner._dispatch does not handle it"
        )


def test_canonical_loader_returns_tc_name_without_name_duplicate(tmp_path):
    tc_file = tmp_path / "canonical.yaml"
    tc_file.write_text(
        """
name: CANONICAL_LOADER
metadata:
  runnable: true
  tc_class: FULL_AUTO
  execution_type: AUTO
  manual_detail: NONE
steps:
  - action: wait
    seconds: 0.25
""",
        encoding="utf-8",
    )

    tc = load_tc(tc_file, contract_mode="canonical")

    assert tc["tc_name"] == "CANONICAL_LOADER"
    assert "name" not in tc
    assert tc["steps"] == [{"action": "wait", "duration": 250}]


def test_canonical_loader_rejects_alias_conflict(tmp_path):
    tc_file = tmp_path / "conflict.yaml"
    tc_file.write_text(
        """
tc_name: CANONICAL
name: LEGACY
metadata:
  runnable: true
  tc_class: FULL_AUTO
  execution_type: AUTO
  manual_detail: NONE
steps:
  - action: wait
    duration: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(TCValidationError, match="ALIAS_CONFLICT"):
        load_tc(tc_file, contract_mode="canonical")


def test_canonical_loader_rejects_canonical_validation_error(tmp_path):
    tc_file = tmp_path / "invalid-canonical.yaml"
    tc_file.write_text(
        """
tc_name: INVALID_CANONICAL
metadata:
  runnable: true
  tc_class: FULL_AUTO
  execution_type: AUTO
  manual_detail: NONE
steps:
  - action: tap_id
""",
        encoding="utf-8",
    )

    with pytest.raises(TCValidationError, match="target"):
        load_tc(tc_file, contract_mode="canonical")


def test_legacy_loader_behavior_is_unchanged(tmp_path):
    tc_file = tmp_path / "legacy.yaml"
    tc_file.write_text(
        """
tc_name: LEGACY_LOADER
steps:
  - action: tap_text
    text: 설정
  - action: wait
    seconds: 2
""",
        encoding="utf-8",
    )

    default_result = load_tc(tc_file)
    explicit_legacy_result = load_tc(tc_file, contract_mode="legacy")

    assert explicit_legacy_result == default_result
    assert explicit_legacy_result == {
        "tc_name": "LEGACY_LOADER",
        "name": "LEGACY_LOADER",
        "steps": [
            {"action": "tap_text", "text": "설정"},
            {"action": "wait", "seconds": 2},
        ],
    }
