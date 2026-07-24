from dataclasses import FrozenInstanceError
from unittest.mock import call, patch, MagicMock
import subprocess

import pytest

from src.adb import ADB, ShellResult


def _completed(returncode=0, stdout="", stderr=""):
    return MagicMock(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _invoke_remote_helper(adb, helper, tmp_path):
    if helper == "screenshot":
        return adb.screenshot(tmp_path / "shot.png")
    return adb.dump_ui()


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
    mock_run.assert_called_once_with(
        ["adb", "devices"],
        capture_output=True,
        text=True,
        timeout=5,
        encoding="utf-8",
        errors="replace",
    )


@patch("src.adb.subprocess.run")
def test_is_connected_false_no_device(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="List of devices attached\n",
        stderr="",
    )
    adb = ADB()
    assert adb.is_connected() is False


@patch("src.adb.subprocess.run")
def test_positional_serial_default_preserves_exact_legacy_probe(mock_run):
    mock_run.return_value = _completed(
        returncode=1,
        stdout="legacy probe stdout",
        stderr="discarded stderr",
    )

    result = ADB("PROBE_SERIAL").shell("bogus-cmd", timeout=5)

    assert result == "legacy probe stdout"
    mock_run.assert_called_once_with(
        ["adb", "-s", "PROBE_SERIAL", "shell", "bogus-cmd"],
        capture_output=True,
        text=True,
        timeout=5,
        encoding="utf-8",
        errors="replace",
    )
    assert type(mock_run.call_args.kwargs["timeout"]) is int


@pytest.mark.parametrize("serial", ["", " ", "\t", "SER IAL"])
def test_adb_rejects_non_none_serial_containing_whitespace(serial):
    with pytest.raises(ValueError):
        ADB(serial, strict_shell=False)


@patch("src.adb.subprocess.run")
def test_explicit_none_serial_remains_unpinned(mock_run):
    mock_run.return_value = _completed(stdout="ok")

    result = ADB(device_serial=None, strict_shell=False).shell("id")

    assert result == "ok"
    assert mock_run.call_args.args[0] == ["adb", "shell", "id"]


@patch("src.adb.subprocess.run")
def test_pinned_device_serial_method_remains_callable(mock_run):
    mock_run.return_value = _completed(stdout="SERIAL-OBSERVED\n")
    adb = ADB("SERIAL-PINNED", strict_shell=False)

    assert adb._device_serial == "SERIAL-PINNED"
    assert callable(adb.device_serial)
    assert adb.device_serial() == "SERIAL-OBSERVED"
    assert mock_run.call_args.args[0] == [
        "adb", "-s", "SERIAL-PINNED", "get-serialno"
    ]


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (0, " device \n", True),
        (1, "device\n", False),
        (0, "offline\n", False),
        (0, "\n", False),
    ],
)
@patch("src.adb.subprocess.run")
def test_pinned_is_connected_uses_get_state_without_fallback(
    mock_run, returncode, stdout, expected
):
    mock_run.return_value = _completed(returncode=returncode, stdout=stdout)

    assert ADB("SERIAL", strict_shell=False).is_connected() is expected
    mock_run.assert_called_once_with(
        ["adb", "-s", "SERIAL", "get-state"],
        capture_output=True,
        text=True,
        timeout=5,
        encoding="utf-8",
        errors="replace",
    )


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired(cmd="adb", timeout=5),
        FileNotFoundError("adb missing"),
    ],
)
@patch("src.adb.subprocess.run")
def test_pinned_is_connected_failure_never_retries_unpinned(mock_run, failure):
    mock_run.side_effect = failure

    assert ADB("SERIAL", strict_shell=False).is_connected() is False
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["adb", "-s", "SERIAL", "get-state"]


@patch("src.adb.subprocess.run")
def test_strict_shell_nonzero_raises_bounded_typed_error_without_timeout_coercion(
    mock_run,
):
    mock_run.return_value = _completed(
        returncode=7,
        stdout="O" * 201 + "OUT_TAIL",
        stderr="E" * 201 + "ERR_TAIL",
    )

    with pytest.raises(RuntimeError) as exc_info:
        ADB(strict_shell=True).shell("restricted", timeout=5)

    message = str(exc_info.value)
    assert type(exc_info.value).__name__ == "ADBCommandError"
    assert "7" in message
    assert 0 < message.count("O") <= 200
    assert 0 < message.count("E") <= 200
    assert "OUT_TAIL" not in message
    assert "ERR_TAIL" not in message
    assert mock_run.call_args.kwargs["timeout"] == 5
    assert type(mock_run.call_args.kwargs["timeout"]) is int


@patch("src.adb.subprocess.run")
def test_strict_shell_zero_returncode_returns_stdout(mock_run):
    mock_run.return_value = _completed(returncode=0, stdout="strict stdout\n")

    result = ADB("SERIAL", strict_shell=True).shell("id", timeout=5)

    assert result == "strict stdout\n"
    assert mock_run.call_args.args[0] == ["adb", "-s", "SERIAL", "shell", "id"]
    assert mock_run.call_args.kwargs["timeout"] == 5


@patch("src.adb.subprocess.run")
def test_strict_shell_does_not_change_shell_result_contract(mock_run):
    mock_run.return_value = _completed(
        returncode=9,
        stdout="partial",
        stderr="denied",
    )

    result = ADB("SERIAL", strict_shell=True).shell_result(
        "restricted", timeout_s=2.5
    )

    assert result == ShellResult("restricted", "partial", "denied", 9)


@pytest.mark.parametrize(
    ("helper", "remote"),
    [
        ("screenshot", "/data/local/tmp/tc_runner_screenshot_tmp.png"),
        ("dump_ui", "/data/local/tmp/tc_runner_ui_dump.xml"),
    ],
)
@patch("src.adb.subprocess.run")
def test_remote_helper_success_uses_namespaced_tmp_and_pinned_argv(
    mock_run, helper, remote, tmp_path
):
    mock_run.side_effect = [
        _completed(),
        _completed(stdout="<hierarchy/>"),
        _completed(),
    ]

    result = _invoke_remote_helper(
        ADB("SERIAL", strict_shell=False), helper, tmp_path
    )

    calls = [call.args[0] for call in mock_run.call_args_list]
    assert len(calls) == 3
    assert all(call[:3] == ["adb", "-s", "SERIAL"] for call in calls)
    assert all(remote in " ".join(call) for call in calls)
    assert all("/sdcard" not in " ".join(call) for call in calls)
    if helper == "dump_ui":
        assert result == "<hierarchy/>"


@patch("src.adb.subprocess.run")
def test_screenshot_exact_argv_with_pinned_serial(mock_run, tmp_path):
    mock_run.side_effect = [_completed(), _completed(), _completed()]
    local_path = tmp_path / "shot.png"

    result = ADB("SERIAL", strict_shell=False).screenshot(local_path)

    assert result is None
    assert mock_run.call_args_list == [
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "shell",
                "screencap -p "
                "/data/local/tmp/tc_runner_screenshot_tmp.png",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "pull",
                "/data/local/tmp/tc_runner_screenshot_tmp.png",
                str(local_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "shell",
                "rm -f /data/local/tmp/tc_runner_screenshot_tmp.png",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
    ]


@patch("src.adb.subprocess.run")
def test_dump_ui_exact_argv_with_pinned_serial(mock_run):
    mock_run.side_effect = [
        _completed(),
        _completed(stdout="<hierarchy/>"),
        _completed(),
    ]

    result = ADB("SERIAL", strict_shell=False).dump_ui()

    assert result == "<hierarchy/>"
    assert mock_run.call_args_list == [
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "shell",
                "uiautomator dump "
                "/data/local/tmp/tc_runner_ui_dump.xml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "shell",
                "cat",
                "/data/local/tmp/tc_runner_ui_dump.xml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
        call(
            [
                "adb",
                "-s",
                "SERIAL",
                "shell",
                "rm -f /data/local/tmp/tc_runner_ui_dump.xml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        ),
    ]


@pytest.mark.parametrize("helper", ["screenshot", "dump_ui"])
@pytest.mark.parametrize(
    "phase",
    ["creation", "transfer", "cleanup", "primary_and_cleanup"],
)
@patch("src.adb.subprocess.run")
def test_remote_helper_strict_failure_cleanup_matrix(
    mock_run, phase, helper, tmp_path
):
    if phase == "creation":
        mock_run.side_effect = [
            _completed(returncode=1, stderr="creation failure"),
            _completed(),
        ]
    elif phase == "transfer":
        mock_run.side_effect = [
            _completed(),
            _completed(returncode=2, stderr="transfer failure"),
            _completed(),
        ]
    elif phase == "cleanup":
        mock_run.side_effect = [
            _completed(),
            _completed(stdout="<hierarchy/>"),
            _completed(returncode=3, stderr="cleanup failure"),
        ]
    else:
        mock_run.side_effect = [
            _completed(returncode=1, stderr="primary failure"),
            _completed(returncode=4, stderr="cleanup failure"),
        ]

    with pytest.raises(RuntimeError) as exc_info:
        _invoke_remote_helper(ADB(strict_shell=True), helper, tmp_path)

    assert type(exc_info.value).__name__ == "ADBCommandError"
    if phase == "primary_and_cleanup":
        assert "primary failure" in str(exc_info.value)
        assert "cleanup failure" not in str(exc_info.value)
    assert "rm -f" in " ".join(mock_run.call_args_list[-1].args[0])


@pytest.mark.parametrize("helper", ["screenshot", "dump_ui"])
@patch("src.adb.subprocess.run")
def test_remote_helper_non_strict_cleanup_nonzero_is_ignored(
    mock_run, helper, tmp_path
):
    mock_run.side_effect = [
        _completed(),
        _completed(stdout="<hierarchy/>"),
        _completed(returncode=5, stderr="ignored cleanup rc"),
    ]

    _invoke_remote_helper(ADB(strict_shell=False), helper, tmp_path)


@pytest.mark.parametrize("helper", ["screenshot", "dump_ui"])
@pytest.mark.parametrize(
    ("cleanup_failure", "expected_error"),
    [
        (subprocess.TimeoutExpired(cmd="rm", timeout=10), TimeoutError),
        (FileNotFoundError("adb missing"), FileNotFoundError),
    ],
)
@patch("src.adb.subprocess.run")
def test_remote_helper_non_strict_sole_cleanup_failure_propagates(
    mock_run, cleanup_failure, expected_error, helper, tmp_path
):
    mock_run.side_effect = [
        _completed(),
        _completed(stdout="<hierarchy/>"),
        cleanup_failure,
    ]

    with pytest.raises(expected_error):
        _invoke_remote_helper(ADB(strict_shell=False), helper, tmp_path)


@pytest.mark.parametrize("helper", ["screenshot", "dump_ui"])
@patch("src.adb.subprocess.run")
def test_remote_helper_cleanup_timeout_does_not_mask_primary_timeout(
    mock_run, helper, tmp_path
):
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd="create", timeout=10),
        subprocess.TimeoutExpired(cmd="cleanup", timeout=10),
    ]

    with pytest.raises(TimeoutError) as exc_info:
        _invoke_remote_helper(ADB(strict_shell=False), helper, tmp_path)

    expected = "screencap" if helper == "screenshot" else "uiautomator dump"
    assert expected in str(exc_info.value)
    assert mock_run.call_count == 2
