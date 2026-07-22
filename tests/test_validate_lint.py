import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_tc import (
    LINT_RULE_IDS,
    LINT_SCHEMA_VERSION,
    LINT_TOOL_VERSION,
    LONG_WAIT_THRESHOLD_SECONDS,
    WEAK_VERIFY_MAX_LENGTH,
    _normalize_wait_seconds,
    build_sidecar,
    lint_tc,
    main,
    validate_lint_dsl_fields,
    write_sidecar,
)


# ─── lint rule 동작: TAP_XY_USED ───

def test_tap_xy_emits_info_finding():
    tc = {"tc_name": "T1", "steps": [{"action": "tap_xy", "x": 100, "y": 200}]}
    findings, dsl_errors = lint_tc(tc, Path("a.yaml"), "T1")
    assert dsl_errors == []
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "TAP_XY_USED"
    assert findings[0]["level"] == "INFO"
    assert findings[0]["suppressed"] is False


def test_tap_xy_with_selector_fallback_reason_keeps_evidence_does_not_suppress():
    # selector_fallback_reason은 evidence이지 suppression 근거가 아님 (사용자 결정 §7)
    tc = {"tc_name": "T1", "steps": [{
        "action": "tap_xy", "x": 100, "y": 200,
        "selector_fallback_reason": "icon-only button (텍스트 selector 부재)",
    }]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings[0]["evidence"]["selector_fallback_reason"] == "icon-only button (텍스트 selector 부재)"
    assert findings[0]["suppressed"] is False


# ─── lint rule 동작: LONG_FIXED_WAIT ───

def test_long_fixed_wait_warns_at_threshold_seconds_unit():
    tc = {"tc_name": "T1", "steps": [{"action": "wait", "seconds": 10}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "LONG_FIXED_WAIT"
    assert findings[0]["level"] == "WARN"
    assert findings[0]["evidence"]["normalized_seconds"] == 10.0


def test_long_fixed_wait_normalizes_ms_duration():
    # action_runner._wait()와 동일하게 duration(ms)도 인식
    tc = {"tc_name": "T1", "steps": [{"action": "wait", "duration": 15000}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings[0]["rule_id"] == "LONG_FIXED_WAIT"
    assert findings[0]["evidence"]["normalized_seconds"] == 15.0


def test_validator_and_lint_share_normalized_wait():
    from validate_tc import load_schema, validate_tc

    tc = {
        "name": "LEGACY_WAIT",
        "metadata": {
            "runnable": True,
            "tc_class": "FULL_AUTO",
            "execution_type": "AUTO",
            "manual_detail": "NONE",
        },
        "steps": [{"action": "wait", "seconds": 10}],
    }

    errors = validate_tc(tc, load_schema())
    findings, dsl_errors = lint_tc(tc, Path("legacy_wait.yaml"), "LEGACY_WAIT")

    assert errors == []
    assert dsl_errors == []
    assert findings[0]["rule_id"] == "LONG_FIXED_WAIT"
    assert findings[0]["evidence"]["normalized_seconds"] == 10.0


def test_lint_normalizes_document_once_without_renormalizing_wait(monkeypatch):
    import validate_tc as validator_module

    calls = {"tc": 0, "step": 0}
    original_normalize_tc = validator_module.normalize_tc
    original_normalize_step = validator_module.normalize_step

    def count_tc(*args, **kwargs):
        calls["tc"] += 1
        return original_normalize_tc(*args, **kwargs)

    def count_step(*args, **kwargs):
        calls["step"] += 1
        return original_normalize_step(*args, **kwargs)

    monkeypatch.setattr(validator_module, "normalize_tc", count_tc)
    monkeypatch.setattr(validator_module, "normalize_step", count_step)

    findings, errors = validator_module.lint_tc(
        {"tc_name": "T1", "steps": [{"action": "wait", "seconds": 10}]},
        Path("once.yaml"),
        "T1",
    )

    assert errors == []
    assert findings[0]["rule_id"] == "LONG_FIXED_WAIT"
    assert calls == {"tc": 1, "step": 0}


def test_long_fixed_wait_below_threshold_no_finding():
    tc = {"tc_name": "T1", "steps": [{"action": "wait", "seconds": 5}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings == []


def test_long_fixed_wait_with_timer_modeling_intent_is_suppressed():
    # wait_intent='timer_modeling'은 LONG_FIXED_WAIT suppression 근거 (사용자 결정 §7)
    tc = {"tc_name": "T1", "steps": [{
        "action": "wait", "seconds": 60, "wait_intent": "timer_modeling",
    }]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings[0]["suppressed"] is True
    assert findings[0]["evidence"]["wait_intent"] == "timer_modeling"


# ─── lint rule 동작: WEAK_VERIFY_TEXT ───

def test_weak_verify_text_warns_at_length_2():
    tc = {"tc_name": "T1", "steps": [{"action": "verify_text", "target": "OK"}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings[0]["rule_id"] == "WEAK_VERIFY_TEXT"
    assert findings[0]["level"] == "WARN"
    assert findings[0]["evidence"]["length"] == 2


def test_weak_verify_text_above_threshold_no_finding():
    tc = {"tc_name": "T1", "steps": [{"action": "verify_text", "target": "Wi-Fi 켜짐"}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings == []


def test_weak_verify_text_supports_text_field_fallback():
    # legacy TC가 text 필드를 사용하는 경우도 lint가 인식 (verify_text text/target duality는 별 PR에서 정리)
    tc = {"tc_name": "T1", "steps": [{"action": "verify_text", "text": "x"}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings[0]["rule_id"] == "WEAK_VERIFY_TEXT"


def test_weak_verify_text_does_not_apply_to_verify_gone():
    # verify_gone은 negative assertion이라 짧은 target도 정상 케이스 → PR 1 범위에서 제외 (사용자 결정 수정 1).
    tc = {"tc_name": "T1", "steps": [{"action": "verify_gone", "target": "OK"}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert findings == []


# ─── suppression / DSL 오류 ───

def test_lint_allow_suppresses_finding_but_keeps_in_findings():
    # suppression은 finding 삭제가 아니라 suppressed=True 마킹 (사용자 결정 §7)
    tc = {"tc_name": "T1", "steps": [{
        "action": "tap_xy", "x": 100, "y": 200,
        "lint_allow": ["TAP_XY_USED"],
    }]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    assert len(findings) == 1
    assert findings[0]["suppressed"] is True


def test_invalid_lint_allow_rule_id_is_dsl_error():
    # lint_allow에 미허용 rule_id가 있으면 validate FAIL로 처리 (사용자 결정 §3)
    tc = {"tc_name": "T1", "steps": [{
        "action": "tap_xy", "x": 100, "y": 200,
        "lint_allow": ["UNKNOWN_RULE"],
    }]}
    _, dsl_errors = lint_tc(tc, Path("a.yaml"), "T1")
    assert len(dsl_errors) == 1
    assert "UNKNOWN_RULE" in dsl_errors[0]


def test_validate_lint_dsl_fields_runs_independent_of_lint_engine():
    # validate_lint_dsl_fields는 lint finding 생성과 분리된 단일 source-of-truth.
    # --no-lint 옵션과 무관하게 항상 호출되어야 invalid lint_allow를 잡을 수 있다 (사용자 필수 수정 1).
    tc = {"tc_name": "T1", "steps": [{
        "action": "tap_xy", "x": 100, "y": 200,
        "lint_allow": ["UNKNOWN_RULE"],
    }]}
    errors = validate_lint_dsl_fields(tc)
    assert len(errors) == 1
    assert "UNKNOWN_RULE" in errors[0]


def test_validate_lint_dsl_fields_passes_when_lint_allow_is_valid():
    tc = {"tc_name": "T1", "steps": [{
        "action": "tap_xy", "x": 100, "y": 200,
        "lint_allow": ["TAP_XY_USED"],
    }]}
    assert validate_lint_dsl_fields(tc) == []


def test_no_lint_flag_still_catches_invalid_lint_allow_via_main(tmp_path, monkeypatch, capsys):
    # --no-lint 상태에서도 invalid lint_allow는 validate FAIL이며 exit 1 (사용자 필수 수정 1).
    # Source-of-truth Policy: lint_allow DSL 검사는 lint finding 생성과 분리되어 항상 수행.
    yaml_content = """tc_name: T1
description: dsl error check
metadata:
  runnable: true
  tc_class: FULL_AUTO
  execution_type: AUTO
  manual_detail: NONE
steps:
  - action: tap_xy
    x: 100
    y: 200
    lint_allow:
      - UNKNOWN_RULE
"""
    tc_file = tmp_path / "test.yaml"
    tc_file.write_text(yaml_content, encoding="utf-8")

    monkeypatch.chdir(tmp_path)  # 워킹트리 reports/lint 격리
    monkeypatch.setattr(sys, "argv", ["validate_tc.py", str(tc_file), "--no-lint"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "UNKNOWN_RULE" in out
    # --no-lint이므로 lint sidecar는 생성되지 않아야 함
    assert not (tmp_path / "reports" / "lint").exists()


# ─── helper: _normalize_wait_seconds ───

def test_normalize_wait_seconds_handles_both_units():
    assert _normalize_wait_seconds({"seconds": 3}) == 3.0
    assert _normalize_wait_seconds({"duration": 2500}) == 2.5
    # canonical/alias 충돌은 어느 쪽도 추측하지 않는다.
    assert _normalize_wait_seconds({"seconds": 1, "duration": 9999}) is None
    # 둘 다 없으면 None
    assert _normalize_wait_seconds({"action": "wait"}) is None


# ─── sidecar shape ───

def _empty_scope():
    return {"target_paths": [], "tc_count": 0, "step_count": 0}


def test_sidecar_has_required_top_level_fields():
    scope = {"target_paths": ["a.yaml"], "tc_count": 1, "step_count": 5}
    sidecar = build_sidecar([], scope, "run-test-1")
    assert sidecar["schema_version"] == 1
    assert sidecar["tool_version"] == "pr1-lint-v1"
    assert sidecar["run_id"] == "run-test-1"
    assert "generated_at" in sidecar
    assert sidecar["scan_scope"] == scope
    assert "summary" in sidecar
    assert "findings" in sidecar


def test_sidecar_scan_scope_is_object_with_required_fields():
    # scan_scope는 object 형태 (사용자 결정 수정 2).
    # PR 3 catalog 입력 고려 + 데이터 누적 원칙.
    scope = {"target_paths": ["a.yaml", "b.yaml"], "tc_count": 2, "step_count": 42}
    sidecar = build_sidecar([], scope, "r1")
    s = sidecar["scan_scope"]
    assert isinstance(s, dict)
    assert s["target_paths"] == ["a.yaml", "b.yaml"]
    assert s["tc_count"] == 2
    assert s["step_count"] == 42


def test_sidecar_summary_excludes_suppressed_findings():
    findings = [
        {"rule_id": "TAP_XY_USED", "level": "INFO", "suppressed": False,
         "tc_path": "a.yaml", "tc_id": "T", "step_index": 0, "action": "tap_xy",
         "message": "", "suggested_fix": "", "evidence": {}},
        {"rule_id": "TAP_XY_USED", "level": "INFO", "suppressed": True,
         "tc_path": "a.yaml", "tc_id": "T", "step_index": 1, "action": "tap_xy",
         "message": "", "suggested_fix": "", "evidence": {}},
        {"rule_id": "LONG_FIXED_WAIT", "level": "WARN", "suppressed": False,
         "tc_path": "a.yaml", "tc_id": "T", "step_index": 2, "action": "wait",
         "message": "", "suggested_fix": "", "evidence": {}},
    ]
    sidecar = build_sidecar(findings, _empty_scope(), "r1")
    assert sidecar["summary"]["total_infos"] == 1
    assert sidecar["summary"]["total_warnings"] == 1
    assert sidecar["summary"]["by_rule"] == {"TAP_XY_USED": 1, "LONG_FIXED_WAIT": 1}
    # findings[]에는 suppressed 보존
    assert len(sidecar["findings"]) == 3


def test_sidecar_findings_array_is_single_not_split():
    # warnings[] / infos[] 분리 금지 (사용자 결정 §7)
    sidecar = build_sidecar([], _empty_scope(), "r1")
    assert "findings" in sidecar
    assert "warnings" not in sidecar
    assert "infos" not in sidecar


def test_finding_has_all_required_fields():
    tc = {"tc_name": "T1", "steps": [{"action": "tap_xy", "x": 100, "y": 200}]}
    findings, _ = lint_tc(tc, Path("a.yaml"), "T1")
    finding = findings[0]
    required = {"rule_id", "level", "tc_path", "tc_id", "step_index", "action",
                "message", "suggested_fix", "evidence", "suppressed"}
    assert required <= set(finding.keys())


# ─── 상수 ───

def test_lint_constants():
    assert LINT_TOOL_VERSION == "pr1-lint-v1"
    assert LINT_SCHEMA_VERSION == 1
    assert LINT_RULE_IDS == {"TAP_XY_USED", "LONG_FIXED_WAIT", "WEAK_VERIFY_TEXT"}
    assert LONG_WAIT_THRESHOLD_SECONDS == 10
    assert WEAK_VERIFY_MAX_LENGTH == 2


# ─── write_sidecar (tmp_path 격리, 워킹트리 reports/lint 미생성) ───

def test_write_sidecar_creates_json_at_custom_out_dir(tmp_path):
    sidecar = build_sidecar([], _empty_scope(), "test-run")
    out = write_sidecar(sidecar, "test-run", out_dir=tmp_path)
    assert out.exists()
    assert out.name == "test-run.json"
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "test-run"
    assert loaded["schema_version"] == 1
    assert loaded["tool_version"] == "pr1-lint-v1"
    assert loaded["scan_scope"] == {"target_paths": [], "tc_count": 0, "step_count": 0}
