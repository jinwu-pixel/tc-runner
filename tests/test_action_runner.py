import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.action_runner import ActionRunner, StepResult


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
