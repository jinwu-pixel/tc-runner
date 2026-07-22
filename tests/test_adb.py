from dataclasses import FrozenInstanceError
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from src.adb import ADB, ShellResult


@patch("src.adb.subprocess.run")
def test_shell_result_preserves_returncode_and_stderr(mock_run):
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="partial output\n",
        stderr="permission denied\n",
    )
    adb = ADB(device_serial="SERIAL")

    result = adb.shell_result("restricted command", timeout_s=2.5)

    assert result == ShellResult(
        command="restricted command",
        stdout="partial output\n",
        stderr="permission denied\n",
        returncode=1,
    )
    assert result.ok is False
    mock_run.assert_called_once_with(
        ["adb", "-s", "SERIAL", "shell", "restricted command"],
        capture_output=True,
        text=True,
        timeout=2.5,
        encoding="utf-8",
        errors="replace",
    )


@patch("src.adb.subprocess.run")
def test_legacy_shell_still_returns_stdout(mock_run):
    mock_run.return_value = MagicMock(
        returncode=7,
        stdout="legacy stdout\n",
        stderr="legacy stderr\n",
    )

    result = ADB().shell("legacy command")

    assert result == "legacy stdout\n"


def test_shell_result_is_frozen_and_ok_for_zero():
    result = ShellResult(
        command="command",
        stdout="ok",
        stderr="",
        returncode=0,
    )

    assert result.ok is True
    with pytest.raises(FrozenInstanceError):
        result.returncode = 1


@patch("src.adb.subprocess.run")
def test_shell_returns_output(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Wi-Fi is enabled\n",
        stderr="",
    )
    adb = ADB()
    result = adb.shell("dumpsys wifi")
    assert result == "Wi-Fi is enabled\n"
    mock_run.assert_called_once_with(
        ["adb", "shell", "dumpsys wifi"],
        capture_output=True, text=True, timeout=10,
        encoding="utf-8", errors="replace",
    )


@patch("src.adb.subprocess.run")
def test_shell_raises_on_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
    adb = ADB()
    try:
        adb.shell("hang_command")
        assert False, "Should have raised"
    except TimeoutError as e:
        assert "timeout" in str(e).lower()


@patch("src.adb.subprocess.run")
def test_tap_calls_input_tap(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    adb = ADB()
    adb.tap(500, 1000)
    mock_run.assert_called_once_with(
        ["adb", "shell", "input tap 500 1000"],
        capture_output=True, text=True, timeout=10,
        encoding="utf-8", errors="replace",
    )


@patch("src.adb.subprocess.run")
def test_key_calls_keyevent(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    adb = ADB()
    adb.key("HOME")
    mock_run.assert_called_once_with(
        ["adb", "shell", "input keyevent HOME"],
        capture_output=True, text=True, timeout=10,
        encoding="utf-8", errors="replace",
    )


@patch("src.adb.subprocess.run")
def test_is_connected_true(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="List of devices attached\nR5CT1234567\tdevice\n",
        stderr="",
    )
    adb = ADB()
    assert adb.is_connected() is True


@patch("src.adb.subprocess.run")
def test_is_connected_false_no_device(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="List of devices attached\n",
        stderr="",
    )
    adb = ADB()
    assert adb.is_connected() is False
