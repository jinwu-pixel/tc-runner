from pathlib import Path
from src.reporter import Reporter, TCResult
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
