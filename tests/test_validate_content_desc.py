import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_tc import load_schema, validate_tc


SCHEMA = load_schema()


def _wrap_steps(steps):
    return {
        "tc_name": "T1",
        "metadata": {
            "runnable": True,
            "tc_class": "FULL_AUTO",
            "execution_type": "AUTO",
            "manual_detail": "NONE",
            "has_manual_steps": False,
        },
        "steps": steps,
    }


def test_schema_accepts_tap_content_desc_action():
    tc = _wrap_steps([{"action": "tap_content_desc", "target": "즐겨찾기"}])
    errors = validate_tc(tc, SCHEMA)
    assert errors == []


def test_schema_accepts_verify_content_desc_action():
    tc = _wrap_steps([{"action": "verify_content_desc", "target": "즐겨찾기"}])
    errors = validate_tc(tc, SCHEMA)
    assert errors == []


def test_validate_fail_tap_content_desc_missing_target():
    tc = _wrap_steps([{"action": "tap_content_desc"}])
    errors = validate_tc(tc, SCHEMA)
    assert any("tap_content_desc" in e and "target" in e for e in errors)


def test_validate_fail_verify_content_desc_missing_target():
    tc = _wrap_steps([{"action": "verify_content_desc"}])
    errors = validate_tc(tc, SCHEMA)
    assert any("verify_content_desc" in e and "target" in e for e in errors)


def test_validate_fail_tap_content_desc_empty_target():
    tc = _wrap_steps([{"action": "tap_content_desc", "target": ""}])
    errors = validate_tc(tc, SCHEMA)
    assert any("target" in e for e in errors)


def test_validate_fail_verify_content_desc_empty_target():
    tc = _wrap_steps([{"action": "verify_content_desc", "target": ""}])
    errors = validate_tc(tc, SCHEMA)
    assert any("target" in e for e in errors)


def test_existing_actions_still_validate_after_enum_extension():
    # 기존 action 회귀 — tap_text / verify_text / shell 등 변동 없음
    tc = _wrap_steps([
        {"action": "tap_text", "target": "설정"},
        {"action": "verify_text", "target": "메뉴"},
        {"action": "shell", "command": "echo hello"},
    ])
    errors = validate_tc(tc, SCHEMA)
    assert errors == []


def test_validate_fail_unknown_action_still_rejected():
    tc = _wrap_steps([{"action": "tap_xpath", "target": "//foo"}])
    errors = validate_tc(tc, SCHEMA)
    assert any("미지원 action" in e for e in errors)
