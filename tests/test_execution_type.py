"""execution_type / manual_detail 파생 계산 회귀 테스트 (pytest 정식).

13 케이스:
  01 AUTO 대표 — execution_type=AUTO, manual_detail=NONE
  02 MANUAL_LOCAL 대표 — manual_pause(MANUAL_REQUIRED)만 있음
  03 EXTERNAL_EVENT 대표 — execution_mode=EXTERNAL_EVENT step 존재
  04 복합 manual_detail — CALL_RECEIVE|BUTTON_TOUCH
  05 잘못된 enum — execution_type='INVALID'
  06 필드 누락 — execution_type 없음
  07 필드 누락 — manual_detail 없음
  08 일관성 — AUTO + manual_detail != NONE
  09 일관성 — AUTO + has_manual_steps=true
  10 일관성 — EXTERNAL_EVENT + manual_detail=NONE
  11 잘못된 manual_detail 토큰 — 'BLUETOOTH'
  12 step=EXTERNAL_EVENT vs metadata=MANUAL_LOCAL 불일치
  13 step에 manual_pause 없음 + metadata=MANUAL_LOCAL
"""

import sys
from pathlib import Path

import pytest

# repo root 를 path 에 추가 (tests/ 이관 후 정합)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from validate_tc import validate_tc, load_schema  # noqa: E402


@pytest.fixture(scope="module")
def schema():
    return load_schema()


def _base_tc(**overrides):
    tc = {
        "tc_name": "TEST-01",
        "metadata": {
            "runnable": True,
            "tc_class": "FULL_AUTO",
            "has_manual_steps": False,
            "has_shell_actions": True,
            "has_unresolved_params": False,
            "execution_type": "AUTO",
            "manual_detail": "NONE",
        },
        "steps": [
            {
                "action": "shell",
                "command": "am start -n com.example.app/.MainActivity",
                "execution_mode": "SHELL_AUTO",
                "step_role": "SETUP",
                "compile_status": "OK",
                "source_trace": {
                    "raw_segment": "test",
                    "source_phase": "procedure",
                    "position": 1,
                    "total_segments": 1,
                },
            }
        ],
    }
    if "metadata" in overrides:
        tc["metadata"].update(overrides.pop("metadata"))
    if "steps" in overrides:
        tc["steps"] = overrides.pop("steps")
    tc.update(overrides)
    return tc


def _manual_pause_step(description, execution_mode):
    return {
        "action": "manual_pause",
        "description": description,
        "execution_mode": execution_mode,
        "step_role": "ACTION",
        "compile_status": "OK",
        "source_trace": {
            "raw_segment": "test",
            "source_phase": "procedure",
            "position": 1,
            "total_segments": 1,
        },
    }


def _tc_no_execution_type():
    tc = _base_tc()
    del tc["metadata"]["execution_type"]
    return tc


def _tc_no_manual_detail():
    tc = _base_tc()
    del tc["metadata"]["manual_detail"]
    return tc


CASES = [
    # (case_id, builder, expect_pass, expect_error_substr)
    (
        "01_AUTO_normal",
        lambda: _base_tc(),
        True,
        None,
    ),
    (
        "02_MANUAL_LOCAL_normal",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "MANUAL_LOCAL",
                "manual_detail": "BUTTON_TOUCH",
            },
            steps=[_manual_pause_step("앱을 설치해주세요.", "MANUAL_REQUIRED")],
        ),
        True,
        None,
    ),
    (
        "03_EXTERNAL_EVENT_normal",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "EXTERNAL_EVENT",
                "manual_detail": "CALL_RECEIVE",
            },
            steps=[_manual_pause_step("보조폰에서 전화를 걸어주세요.", "EXTERNAL_EVENT")],
        ),
        True,
        None,
    ),
    (
        "04_compound_manual_detail",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "EXTERNAL_EVENT",
                "manual_detail": "CALL_RECEIVE|BUTTON_TOUCH",
            },
            steps=[_manual_pause_step("보조폰에서 전화 + 버튼", "EXTERNAL_EVENT")],
        ),
        True,
        None,
    ),
    (
        "05_invalid_execution_type_enum",
        lambda: _base_tc(metadata={"execution_type": "INVALID"}),
        False,
        "execution_type 값 불일치",
    ),
    (
        "06_missing_execution_type",
        _tc_no_execution_type,
        False,
        "execution_type",
    ),
    (
        "07_missing_manual_detail",
        _tc_no_manual_detail,
        False,
        "manual_detail",
    ),
    (
        "08_AUTO_with_nonzero_manual_detail",
        lambda: _base_tc(metadata={"manual_detail": "CALL_RECEIVE"}),
        False,
        "일관성 오류",
    ),
    (
        "09_AUTO_with_has_manual_steps_true",
        lambda: _base_tc(metadata={"has_manual_steps": True}),
        False,
        "일관성 오류",
    ),
    (
        "10_EXTERNAL_EVENT_with_NONE_detail",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "EXTERNAL_EVENT",
                "manual_detail": "NONE",
            },
            steps=[_manual_pause_step("외부 이벤트 대기", "EXTERNAL_EVENT")],
        ),
        False,
        "일관성 오류",
    ),
    (
        "11_invalid_manual_detail_token",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "MANUAL_LOCAL",
                "manual_detail": "BLUETOOTH",
            },
            steps=[_manual_pause_step("블루투스 연결", "MANUAL_REQUIRED")],
        ),
        False,
        "manual_detail 토큰 불일치",
    ),
    (
        "12_step_external_vs_metadata_manual_local",
        lambda: _base_tc(
            metadata={
                "tc_class": "SEMI_AUTO",
                "has_manual_steps": True,
                "execution_type": "MANUAL_LOCAL",
                "manual_detail": "BUTTON_TOUCH",
            },
            steps=[_manual_pause_step("보조폰 수신", "EXTERNAL_EVENT")],
        ),
        False,
        "step 분석 결과",
    ),
    (
        "13_no_manual_step_but_manual_local",
        lambda: _base_tc(
            metadata={
                "execution_type": "MANUAL_LOCAL",
                "manual_detail": "BUTTON_TOUCH",
                "has_manual_steps": True,
            }
        ),
        False,
        "step 분석 결과",
    ),
]


@pytest.mark.parametrize(
    "case_id,builder,expect_pass,expect_error_substr",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_execution_type_validation(
    case_id, builder, expect_pass, expect_error_substr, schema
):
    tc = builder()
    errors = validate_tc(tc, schema)
    is_pass = len(errors) == 0
    if expect_pass:
        assert is_pass, f"{case_id}: validate FAIL — {errors}"
    else:
        assert not is_pass, f"{case_id}: 실패 예상했으나 통과"
        if expect_error_substr:
            assert any(expect_error_substr in e for e in errors), (
                f"{case_id}: 예상 에러 미검출 '{expect_error_substr}'; 실제 = {errors}"
            )
