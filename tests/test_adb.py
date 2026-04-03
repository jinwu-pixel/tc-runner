from unittest.mock import patch, MagicMock
import subprocess

from src.adb import ADB


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
