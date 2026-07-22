import json
from pathlib import Path

import pytest

from src.reporter import (
    Reporter,
    SUMMARY_SCHEMA_VERSION,
    SUMMARY_TOOL_VERSION,
    TCResult,
)
from src.action_runner import StepResult


def test_tc_result_is_pass_all_steps_pass():
    tc = TCResult(name="Test1", description="desc", steps=[
        StepResult(action="wait", passed=True, duration=0.1),
        StepResult(action="shell", passed=True, duration=0.2),
    ])
    assert tc.is_pass is True


def test_tc_result_is_fail_one_step_fails():
    tc = TCResult(name="Test2", description="desc", steps=[
        StepResult(action="wait", passed=True, duration=0.1),
        StepResult(action="verify_text", passed=False, message="not found", duration=1.0),
    ])
    assert tc.is_pass is False


def test_reporter_summary():
    reporter = Reporter(report_dir=Path("/tmp"))
    reporter.results = [
        TCResult(name="TC1", description="", steps=[
            StepResult(action="wait", passed=True, duration=0.1),
        ]),
        TCResult(name="TC2", description="", steps=[
            StepResult(action="verify_text", passed=False, duration=1.0),
        ]),
    ]
    summary = reporter.get_summary()
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1


def test_reporter_generate_html(tmp_path):
    reporter = Reporter(report_dir=tmp_path)
    reporter.device_info = {"model": "Galaxy S24", "android_version": "14"}
    reporter.results = [
        TCResult(name="TC1", description="test", steps=[
            StepResult(action="wait", passed=True, duration=0.1),
        ]),
    ]
    html_path = reporter.generate_html()
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "TC1" in content
    assert "Galaxy S24" in content


# ─── Bundle 모드 (run_id) ───


def test_reporter_legacy_mode_writes_timestamp_html_in_report_dir(tmp_path):
    """run_id 없음 = legacy. <ts>_report.html 가 report_dir 직속에 생성."""
    reporter = Reporter(report_dir=tmp_path)
    reporter.results = [
        TCResult(name="TC1", description="", steps=[
            StepResult(action="wait", passed=True, duration=0.1),
        ]),
    ]
    html_path = reporter.generate_html()
    assert html_path.parent == tmp_path
    assert html_path.name.endswith("_report.html")
    assert reporter.bundle_dir == tmp_path
    assert reporter.screenshot_dir == tmp_path / "screenshots"


def test_reporter_bundle_mode_paths(tmp_path):
    """run_id 있음 = bundle. report.html / screenshots/ / bundle_dir 위치 검증."""
    run_id = "20260526T120000Z"
    reporter = Reporter(report_dir=tmp_path, run_id=run_id)

    assert reporter.bundle_dir == tmp_path / run_id
    assert reporter.screenshot_dir == tmp_path / run_id / "screenshots"

    reporter.device_info = {"model": "AT-M140", "android_version": "14"}
    reporter.results = [
        TCResult(name="TC_BUNDLE", description="bundle test", steps=[
            StepResult(action="wait", passed=True, duration=0.5),
        ]),
    ]
    html_path = reporter.generate_html()
    assert html_path == tmp_path / run_id / "report.html"
    assert html_path.exists()
    assert "TC_BUNDLE" in html_path.read_text(encoding="utf-8")


def test_reporter_bundle_mode_summary_json_shape(tmp_path):
    """summary.json 스키마 검증 — 필드·duration_s·screenshot_path 상대경로."""
    run_id = "20260526T130000Z"
    reporter = Reporter(report_dir=tmp_path, run_id=run_id)
    reporter.device_info = {"serial": "ABCD", "model": "AT-M140", "android_version": "14"}

    bundle = tmp_path / run_id
    bundle.mkdir(parents=True, exist_ok=True)
    shot_dir = bundle / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    shot = shot_dir / "fail_tap_text_1.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")

    reporter.results = [
        TCResult(name="TC_A", description="alpha", steps=[
            StepResult(action="wait", passed=True, duration=0.123456),
            StepResult(
                action="tap_text",
                passed=False,
                message="not found",
                duration=2.5,
                screenshot_path=shot,
                execution_mode="AUTO",
            ),
        ]),
        TCResult(name="TC_B", description="beta", steps=[
            StepResult(
                action="manual_step",
                passed=False,
                duration=0.0,
                manual_action="skip",
                skip_reason="user requested",
            ),
        ]),
    ]

    out = reporter.write_summary_json()
    assert out == bundle / "summary.json"
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data["schema_version"] == SUMMARY_SCHEMA_VERSION == 2
    assert data["tool_version"] == SUMMARY_TOOL_VERSION
    assert data["contract_mode"] == "legacy"
    assert data["run_status"] == "COMPLETED"
    assert data["run_id"] == run_id
    assert data["generated_at"].endswith("Z")
    assert data["device"]["model"] == "AT-M140"
    assert data["summary"] == {"total": 2, "passed": 0, "skipped": 1, "failed": 1}

    assert len(data["results"]) == 2
    tc_a = data["results"][0]
    assert tc_a["name"] == "TC_A"
    assert tc_a["passed"] is False
    assert tc_a["duration_s"] == pytest.approx(2.623456, rel=1e-3)

    step1 = tc_a["steps"][0]
    assert step1 == {
        "index": 1, "action": "wait", "passed": True, "duration_s": 0.1235,
        "message": "", "execution_mode": "", "manual_action": "",
        "skip_reason": "", "paused": False, "screenshot_path": None,
    }
    step2 = tc_a["steps"][1]
    assert step2["index"] == 2
    assert step2["action"] == "tap_text"
    assert step2["passed"] is False
    assert step2["execution_mode"] == "AUTO"
    assert step2["screenshot_path"] == "screenshots/fail_tap_text_1.png"

    tc_b = data["results"][1]
    assert tc_b["steps"][0]["manual_action"] == "skip"
    assert tc_b["steps"][0]["skip_reason"] == "user requested"


def test_summary_schema_version_two_records_contract_mode(tmp_path):
    reporter = Reporter(
        report_dir=tmp_path,
        run_id="20260721T020000Z",
        contract_mode="canonical",
    )

    data = json.loads(reporter.write_summary_json().read_text(encoding="utf-8"))

    assert data["schema_version"] == 2
    assert data["contract_mode"] == "canonical"
    assert data["run_status"] == "COMPLETED"


def test_aborted_fail_closed_is_serialized_in_partial_summary(tmp_path):
    reporter = Reporter(
        report_dir=tmp_path,
        run_id="20260721T020001Z",
        contract_mode="canonical",
        run_status="ABORTED_FAIL_CLOSED",
    )
    reporter.results = [
        TCResult(
            name="PARTIAL",
            description="",
            steps=[
                StepResult(action="wait", passed=True, duration=0.1),
                StepResult(
                    action="tap_xy",
                    passed=False,
                    message="forced failure",
                    duration=0.2,
                ),
            ],
        )
    ]

    data = json.loads(reporter.write_summary_json().read_text(encoding="utf-8"))

    assert data["contract_mode"] == "canonical"
    assert data["run_status"] == "ABORTED_FAIL_CLOSED"
    assert [step["action"] for step in data["results"][0]["steps"]] == [
        "wait",
        "tap_xy",
    ]


@pytest.mark.parametrize(
    ("contract_mode", "run_status"),
    [
        ("legacy", "COMPLETED"),
        ("canonical", "ABORTED_FAIL_CLOSED"),
    ],
)
def test_report_records_contract_mode_and_abort_context(
    tmp_path, contract_mode, run_status
):
    reporter = Reporter(
        report_dir=tmp_path,
        run_id=f"20260721T02000{int(contract_mode == 'canonical') + 2}Z",
        contract_mode=contract_mode,
        run_status=run_status,
    )

    data = json.loads(reporter.write_summary_json().read_text(encoding="utf-8"))

    assert data["contract_mode"] == contract_mode
    assert data["run_status"] == run_status


def test_reporter_summary_json_rejects_legacy_mode(tmp_path):
    """legacy 모드 (run_id 없음) 에서 write_summary_json 호출 = RuntimeError."""
    reporter = Reporter(report_dir=tmp_path)
    with pytest.raises(RuntimeError):
        reporter.write_summary_json()


def test_reporter_rejects_invalid_run_id(tmp_path):
    """파일명 위험 문자 (/) 가 포함된 run_id 는 즉시 거부."""
    with pytest.raises(ValueError):
        Reporter(report_dir=tmp_path, run_id="bad/run/id")


def test_reporter_bundle_screenshot_outside_bundle_keeps_path(tmp_path):
    """screenshot_path 가 bundle 외부면 그대로 문자열로 직렬화 (relative_to 실패 fallback)."""
    run_id = "20260526T140000Z"
    reporter = Reporter(report_dir=tmp_path, run_id=run_id)

    outside = tmp_path / "elsewhere" / "shot.png"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_bytes(b"")

    reporter.results = [
        TCResult(name="TC_X", description="", steps=[
            StepResult(action="wait", passed=False, duration=0.1, screenshot_path=outside),
        ]),
    ]
    out = reporter.write_summary_json()
    data = json.loads(out.read_text(encoding="utf-8"))
    sp = data["results"][0]["steps"][0]["screenshot_path"]
    assert sp is not None
    assert sp.endswith("shot.png")


# ─── disjoint status 분류 (fail > skip > pass) ───


def test_tc_status_skip_only():
    tc = TCResult(name="skip", description="", steps=[
        StepResult(action="manual_step", passed=False, duration=0.0,
                   manual_action="skip", skip_reason="no device"),
    ])
    assert tc.status == "skipped"


def test_tc_status_fail_only():
    tc = TCResult(name="fail", description="", steps=[
        StepResult(action="verify_text", passed=False, duration=0.1),
    ])
    assert tc.status == "failed"


def test_tc_status_pass_only():
    tc = TCResult(name="pass", description="", steps=[
        StepResult(action="wait", passed=True, duration=0.1),
    ])
    assert tc.status == "passed"


def test_tc_status_fail_and_skip_is_failed():
    """fail step + skip step 동시 → failed (skip 이 fail 을 가리지 않음)."""
    tc = TCResult(name="failskip", description="", steps=[
        StepResult(action="verify_text", passed=False, duration=0.1),
        StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip"),
    ])
    assert tc.status == "failed"


def test_get_summary_fail_plus_skip_in_one_tc():
    """핵심 RED: 한 TC 의 fail 이 skipped 에 먹혀 failed=0 이 되면 안 된다."""
    reporter = Reporter(report_dir=Path("/tmp"))
    reporter.results = [
        TCResult(name="TC_C", description="", steps=[
            StepResult(action="verify_text", passed=False, duration=0.1),
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip"),
        ]),
    ]
    assert reporter.get_summary() == {"total": 1, "passed": 0, "skipped": 0, "failed": 1}


def test_get_summary_disjoint_invariant():
    """passed + failed + skipped == total, 각 TC 정확히 한 버킷."""
    reporter = Reporter(report_dir=Path("/tmp"))
    reporter.results = [
        TCResult(name="p", description="", steps=[
            StepResult(action="wait", passed=True, duration=0.1)]),
        TCResult(name="f", description="", steps=[
            StepResult(action="verify", passed=False, duration=0.1)]),
        TCResult(name="s", description="", steps=[
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip")]),
        TCResult(name="fs", description="", steps=[
            StepResult(action="verify", passed=False, duration=0.1),
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip")]),
    ]
    s = reporter.get_summary()
    assert s["passed"] + s["failed"] + s["skipped"] == s["total"]
    assert s == {"total": 4, "passed": 1, "skipped": 1, "failed": 2}
