import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.action_runner import ActionRunner, StepResult, ManualStepAction, ManualStepContext


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="설정" resource-id="com.test:id/title"
        class="android.widget.TextView" package="com.test"
        bounds="[100,200][300,400]" />
</hierarchy>"""


def make_runner(adb_mock=None):
    adb = adb_mock or MagicMock()
    return ActionRunner(adb=adb, screenshot_dir=Path("/tmp/screenshots"))


def test_wait_action():
    runner = make_runner()
    result = runner.run_step({"action": "wait", "seconds": 0.01})
    assert result.passed is True
    assert result.action == "wait"


def test_shell_action():
    adb = MagicMock()
    adb.shell.return_value = "some output"
    runner = make_runner(adb)
    result = runner.run_step({"action": "shell", "command": "echo hello"})
    assert result.passed is True
    adb.shell.assert_called_once_with("echo hello")


def test_tap_xy_action():
    adb = MagicMock()
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_xy", "x": 500, "y": 1000})
    assert result.passed is True
    adb.tap.assert_called_once_with(500, 1000)


def test_key_action():
    adb = MagicMock()
    runner = make_runner(adb)
    result = runner.run_step({"action": "key", "keycode": "HOME"})
    assert result.passed is True
    adb.key.assert_called_once_with("HOME")


def test_verify_shell_pass():
    adb = MagicMock()
    adb.shell.return_value = "Wi-Fi is enabled\n"
    runner = make_runner(adb)
    result = runner.run_step({
        "action": "verify_shell",
        "command": "dumpsys wifi",
        "expected": "enabled",
    })
    assert result.passed is True


def test_verify_shell_fail():
    adb = MagicMock()
    adb.shell.return_value = "Wi-Fi is disabled\n"
    runner = make_runner(adb)
    result = runner.run_step({
        "action": "verify_shell",
        "command": "dumpsys wifi",
        "expected": "enabled",
    })
    assert result.passed is False


def test_tap_text_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "tap_text", "text": "설정"})
    assert result.passed is True
    adb.tap.assert_called_once_with(200, 300)


def test_tap_text_not_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "tap_text", "text": "없는텍스트"})
    assert result.passed is False


def test_verify_text_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = make_runner(adb)
    result = runner.run_step({"action": "verify_text", "text": "설정"})
    assert result.passed is True


def test_verify_text_not_found():
    adb = MagicMock()
    adb.dump_ui.return_value = SAMPLE_XML
    runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"), max_retries=1, retry_interval=0)
    result = runner.run_step({"action": "verify_text", "text": "없는텍스트"})
    assert result.passed is False


class TestHybridPause:
    def test_manual_step_without_handler_fails(self):
        """no-handler → fail-fast."""
        runner = make_runner()
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "이어폰 연결"}
        result = runner.run_step(step)
        assert not result.passed
        assert "manual handler not configured" in result.message

    def test_manual_step_continue(self):
        """continue → passed=True."""
        def handler(ctx):
            return ManualStepAction(decision="continue")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "EXTERNAL_EVENT",
                "description": "보조폰에서 전화"}
        result = runner.run_step(step)
        assert result.passed
        assert result.manual_action == "continue"

    def test_manual_step_skip(self):
        """skip → passed=False, manual_action='skip'."""
        def handler(ctx):
            return ManualStepAction(decision="skip", reason="장비 없음")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "이어폰 연결"}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "skip"
        assert result.skip_reason == "장비 없음"

    def test_manual_step_fail(self):
        """fail → passed=False, manual_action='fail'."""
        def handler(ctx):
            return ManualStepAction(decision="fail")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test"}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "fail"

    def test_manual_step_timeout(self):
        """timeout → fail with timeout reason."""
        import time as _time
        def slow_handler(ctx):
            _time.sleep(10)  # will be interrupted by timeout
            return ManualStepAction(decision="continue")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=slow_handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test", "manual_timeout": 1}
        result = runner.run_step(step)
        assert not result.passed
        assert result.manual_action == "fail"
        assert "timeout" in result.message.lower() or "timeout" in (result.skip_reason or "")

    def test_manual_step_handler_exception(self):
        """handler exception → fail gracefully."""
        def error_handler(ctx):
            raise RuntimeError("device disconnected")
        adb = MagicMock()
        runner = ActionRunner(adb=adb, screenshot_dir=Path("/tmp"),
                            on_manual_step=error_handler)
        step = {"action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
                "description": "test"}
        result = runner.run_step(step)
        assert not result.passed
        assert "error" in result.message.lower() or "disconnect" in result.message.lower()
