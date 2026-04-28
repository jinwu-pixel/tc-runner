import json
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent / "tc_step_schema.json"


def _load_step_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    return schema["$defs"]["step"]


def test_step_has_lint_allow_field():
    step = _load_step_schema()
    assert "lint_allow" in step["properties"]
    assert step["properties"]["lint_allow"]["type"] == "array"


def test_lint_allow_enum_matches_pr1_rules():
    # PR 1 lint rule_id set: TAP_XY_USED (INFO) / LONG_FIXED_WAIT (WARN) / WEAK_VERIFY_TEXT (WARN)
    step = _load_step_schema()
    enum = set(step["properties"]["lint_allow"]["items"]["enum"])
    assert enum == {"TAP_XY_USED", "LONG_FIXED_WAIT", "WEAK_VERIFY_TEXT"}


def test_wait_intent_enum_is_timer_modeling_only():
    # PR 1: polling은 enum에 포함되지 않음. timer_modeling 단독.
    # jsonschema validation 미도입이므로 실제 거절 동작은 강제하지 않으며,
    # 본 테스트는 enum 정의(enumeration)만 보장한다.
    step = _load_step_schema()
    assert step["properties"]["wait_intent"]["enum"] == ["timer_modeling"]


def test_selector_fallback_reason_is_non_empty_string():
    step = _load_step_schema()
    field = step["properties"]["selector_fallback_reason"]
    assert field["type"] == "string"
    assert field["minLength"] == 1


def test_lint_fields_not_in_step_required():
    # 등록은 했으나 강제 아님. step.required 는 ["action"] 단독 유지.
    step = _load_step_schema()
    assert step["required"] == ["action"]
    for field in ("lint_allow", "wait_intent", "selector_fallback_reason"):
        assert field in step["properties"]


def test_lint_fields_have_non_empty_descriptions():
    # suppression/evidence 근거 문서화: 3 필드 모두 non-empty description 필수.
    step = _load_step_schema()
    for field in ("lint_allow", "wait_intent", "selector_fallback_reason"):
        desc = step["properties"][field].get("description", "")
        assert desc.strip(), f"{field} description 누락"
