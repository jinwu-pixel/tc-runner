"""PR 2 Runtime Preflight 단위/통합 테스트.

총 21건:
- unit 8 (expected text/permissions/package_name 추출)
- adb·parser mocking 5 (XML parsing + dumpsys)
- run_preflight scenario 4
- CLI integration 4
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src import preflight as preflight_mod
from src.preflight import (
    extract_expected_texts,
    extract_package_name,
    extract_required_permissions,
    parse_app_version,
    parse_current_activity,
    parse_dumpsys_permissions,
    parse_visible_texts_from_xml,
    run_preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_tc(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / f"{name}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return path


def _make_adb_mock(
    *,
    serial: str | None = "TEST_SERIAL",
    model: str = "AT-M140",
    android_version: str = "14",
    package_installed: bool = True,
    dumpsys_output: str = "",
    xml_output: str = "",
    resolution: str = "480x800",
    raise_xml: bool = False,
    raise_screenshot: bool = False,
) -> MagicMock:
    adb = MagicMock()
    adb.device_serial.return_value = serial
    adb.get_device_info.return_value = {"model": model, "android_version": android_version}

    def shell_side_effect(cmd: str, timeout: int = 10) -> str:
        if cmd.startswith("pm list packages"):
            pkg = cmd.split(" ", 3)[-1]
            return f"package:{pkg}\n" if package_installed else ""
        if cmd.startswith("dumpsys package"):
            return dumpsys_output
        if cmd == "wm size":
            return f"Physical size: {resolution}\n"
        if cmd == "dumpsys window":
            pkg = "com.example.foo"
            return (
                f"  mCurrentFocus=Window{{abc123 u0 {pkg}/{pkg}.MainActivity}}\n"
            )
        if cmd == "dumpsys activity activities":
            return ""
        return ""

    adb.shell.side_effect = shell_side_effect

    if raise_xml:
        adb.dump_ui.side_effect = TimeoutError("xml dump timeout")
    else:
        adb.dump_ui.return_value = xml_output

    if raise_screenshot:
        adb.screenshot.side_effect = TimeoutError("screenshot timeout")
    else:
        def screenshot_side_effect(local_path: Path) -> None:
            Path(local_path).write_bytes(b"\x89PNG\r\n\x1a\nfake")
        adb.screenshot.side_effect = screenshot_side_effect

    adb.is_connected.return_value = True
    return adb


# ---------------------------------------------------------------------------
# Unit tests (8)
# ---------------------------------------------------------------------------


def test_extract_expected_texts_from_verify_text():
    tc = {
        "steps": [
            {"action": "verify_text", "target": "설정"},
            {"action": "verify_text", "text": "전화"},
        ]
    }
    assert extract_expected_texts(tc) == ["설정", "전화"]


def test_extract_expected_texts_from_verify_gone():
    tc = {
        "steps": [
            {"action": "verify_gone", "target": "팝업 표시"},
            {"action": "verify_gone", "text": "쿨다운"},
        ]
    }
    assert extract_expected_texts(tc) == ["팝업 표시", "쿨다운"]


def test_extract_expected_texts_from_tap_text():
    tc = {
        "steps": [
            {"action": "tap_text", "target": "확인"},
            {"action": "tap_text", "text": "다음"},
        ]
    }
    assert extract_expected_texts(tc) == ["확인", "다음"]


def test_extract_expected_texts_skips_input_text():
    tc = {
        "steps": [
            {"action": "input_text", "text": "민감한 입력값"},
            {"action": "verify_text", "target": "환영"},
        ]
    }
    assert extract_expected_texts(tc) == ["환영"]


def test_extract_expected_texts_dedups_and_orders():
    tc = {
        "steps": [
            {"action": "verify_text", "target": "확인"},
            {"action": "tap_text", "target": "확인"},
            {"action": "verify_gone", "target": "취소"},
            {"action": "verify_text", "target": "확인"},
        ]
    }
    assert extract_expected_texts(tc) == ["확인", "취소"]


def test_extract_required_permissions_from_pm_grant():
    tc = {
        "steps": [
            {
                "action": "shell",
                "command": "pm grant com.example.foo android.permission.READ_PHONE_STATE",
            },
            {
                "action": "shell",
                "command": "pm grant com.example.foo android.permission.READ_CONTACTS",
            },
            {
                "action": "shell",
                "command": "pm grant com.example.foo android.permission.READ_PHONE_STATE",
            },
        ]
    }
    perms = extract_required_permissions(tc, "com.example.foo")
    assert perms == [
        "android.permission.READ_PHONE_STATE",
        "android.permission.READ_CONTACTS",
    ]


def test_extract_package_name_present():
    assert extract_package_name({"package_name": "com.a.b"}) == "com.a.b"
    assert (
        extract_package_name({"metadata": {"package_name": "com.c.d"}}) == "com.c.d"
    )


def test_extract_package_name_missing():
    assert extract_package_name({}) is None
    assert extract_package_name({"metadata": {"runnable": True}}) is None


def test_extract_package_name_from_target_app_nested():
    tc = {"metadata": {"target_app": {"package": "com.example.gallery"}}}
    assert extract_package_name(tc) == "com.example.gallery"


def test_extract_package_name_priority_top_level_wins():
    tc = {
        "package_name": "com.top.level",
        "metadata": {
            "package_name": "com.metadata.flat",
            "target_app": {"package": "com.metadata.target"},
        },
    }
    assert extract_package_name(tc) == "com.top.level"


def test_extract_package_name_priority_metadata_over_target_app():
    tc = {
        "metadata": {
            "package_name": "com.metadata.flat",
            "target_app": {"package": "com.metadata.target"},
        }
    }
    assert extract_package_name(tc) == "com.metadata.flat"


def test_extract_package_name_target_app_invalid():
    # target_app이 dict가 아닐 때
    assert extract_package_name({"metadata": {"target_app": "not a dict"}}) is None
    assert extract_package_name({"metadata": {"target_app": ["x"]}}) is None
    # target_app은 dict지만 package 키 없음
    assert extract_package_name({"metadata": {"target_app": {"version": "1.0"}}}) is None
    # package가 빈 문자열
    assert extract_package_name({"metadata": {"target_app": {"package": "   "}}}) is None
    # package가 문자열이 아님
    assert extract_package_name({"metadata": {"target_app": {"package": 42}}}) is None


# ---------------------------------------------------------------------------
# ADB / parser mocking (5)
# ---------------------------------------------------------------------------


def test_parse_visible_texts_from_xml_basic():
    xml = (
        '<hierarchy>'
        '<node text="설정" />'
        '<node text="전화" />'
        '</hierarchy>'
    )
    assert parse_visible_texts_from_xml(xml) == ["설정", "전화"]


def test_parse_visible_texts_from_xml_dedup_and_order():
    xml = (
        '<hierarchy>'
        '<node text="A" />'
        '<node text="B" />'
        '<node text="A" />'
        '<node text="C" />'
        '</hierarchy>'
    )
    assert parse_visible_texts_from_xml(xml) == ["A", "B", "C"]


def test_parse_visible_texts_from_xml_excludes_empty():
    xml = (
        '<hierarchy>'
        '<node text="" />'
        '<node text="   " />'
        '<node />'
        '<node text="OK" />'
        '</hierarchy>'
    )
    assert parse_visible_texts_from_xml(xml) == ["OK"]


def test_parse_visible_texts_from_xml_invalid():
    assert parse_visible_texts_from_xml("not xml") == []
    assert parse_visible_texts_from_xml("") == []


def test_parse_dumpsys_permissions():
    output = (
        "    android.permission.READ_PHONE_STATE: granted=true\n"
        "    android.permission.READ_CONTACTS: granted=false\n"
    )
    state = parse_dumpsys_permissions(
        output,
        [
            "android.permission.READ_PHONE_STATE",
            "android.permission.READ_CONTACTS",
            "android.permission.NOT_LISTED",
        ],
    )
    assert state["android.permission.READ_PHONE_STATE"] == "granted"
    assert state["android.permission.READ_CONTACTS"] == "denied"
    assert state["android.permission.NOT_LISTED"] == "unknown"


def test_parse_app_version_basic():
    output = "    versionName=1.2.3\n    versionCode=42\n"
    name, code = parse_app_version(output)
    assert name == "1.2.3"
    assert code == 42
    assert parse_app_version("") == (None, None)
    assert parse_app_version("no version info") == (None, None)


def test_parse_current_activity_from_window_focus():
    win = "  mCurrentFocus=Window{abc u0 com.example.foo/com.example.foo.MainActivity}\n"
    assert (
        parse_current_activity(win)
        == "com.example.foo/com.example.foo.MainActivity"
    )


def test_parse_current_activity_from_resumed_activity():
    act = (
        "  mResumedActivity: ActivityRecord{xyz u0 "
        "com.example.bar/com.example.bar.SettingsActivity t10}\n"
    )
    assert (
        parse_current_activity("", act)
        == "com.example.bar/com.example.bar.SettingsActivity"
    )


def test_parse_current_activity_none():
    assert parse_current_activity("") is None
    assert parse_current_activity("no focus info") is None


# ---------------------------------------------------------------------------
# run_preflight scenarios (4)
# ---------------------------------------------------------------------------


def test_run_preflight_full_success(tmp_path):
    tc_path = _write_tc(
        tmp_path,
        "tc_ok",
        {
            "tc_name": "TC_OK",
            "package_name": "com.example.foo",
            "steps": [
                {
                    "action": "shell",
                    "command": "pm grant com.example.foo android.permission.READ_PHONE_STATE",
                },
                {"action": "verify_text", "target": "확인"},
            ],
        },
    )
    adb = _make_adb_mock(
        dumpsys_output=(
            "    versionName=1.2.3\n"
            "    versionCode=42\n"
            "    android.permission.READ_PHONE_STATE: granted=true\n"
        ),
        xml_output='<hierarchy><node text="확인" /></hierarchy>',
    )
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="20260428T000000Z",
    )
    assert manifest["schema_version"] == 1
    assert manifest["tool_version"] == "pr2-preflight-v1"
    assert manifest["run_id"] == "20260428T000000Z"
    assert manifest["tc_id"] == "TC_OK"

    # app — package + installed + version_name + version_code
    assert manifest["app"]["package_name"] == "com.example.foo"
    assert manifest["app"]["installed"] is True
    assert manifest["app"]["version_name"] == "1.2.3"
    assert manifest["app"]["version_code"] == 42

    # permissions — grants (NOT granted_state)
    assert manifest["permissions"]["parse_status"] == "ok"
    assert "grants" in manifest["permissions"]
    assert manifest["permissions"]["grants"][
        "android.permission.READ_PHONE_STATE"
    ] == "granted"
    assert "granted_state" not in manifest["permissions"]

    # screen — current_activity / activity_parse_status / window_dump_path /
    # xml_status / sha256
    assert manifest["screen"]["current_activity"] == "com.example.foo/com.example.foo.MainActivity"
    assert manifest["screen"]["activity_parse_status"] == "ok"
    assert manifest["screen"]["window_dump_path"] == "window_dump.xml"
    assert manifest["screen"]["xml_status"] == "ok"
    assert manifest["screen"]["screenshot_status"] == "ok"
    assert manifest["screen"]["xml_sha256"] is not None
    assert manifest["screen"]["screenshot_sha256"] is not None
    assert "dump_status" not in manifest["screen"]
    assert "xml_path" not in manifest["screen"]

    # text_model — expected_texts_from_tc / visible_texts_from_dump / missing_expected_texts / diff_status
    assert manifest["text_model"]["expected_texts_from_tc"] == ["확인"]
    assert manifest["text_model"]["visible_texts_from_dump"] == ["확인"]
    assert manifest["text_model"]["missing_expected_texts"] == []
    assert manifest["text_model"]["diff_status"] == "ok"
    assert "observed_texts" not in manifest["text_model"]
    assert "missing_texts" not in manifest["text_model"]

    # preflight_status — level (NOT status), uppercase OK
    assert manifest["preflight_status"]["level"] == "OK"
    assert manifest["preflight_status"]["reasons"] == []
    assert "status" not in manifest["preflight_status"]

    # 12 top-level keys
    expected_keys = {
        "schema_version", "tool_version", "run_id", "generated_at",
        "tc_path", "tc_id", "device", "app", "permissions",
        "screen", "text_model", "preflight_status",
    }
    assert set(manifest.keys()) == expected_keys
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "window_dump.xml").exists()
    assert (out_dir / "screenshot.png").exists()


def test_run_preflight_package_missing(tmp_path):
    """required=[] + package_name missing — PR 2.1 의미 정리: parse_status="ok"."""
    tc_path = _write_tc(
        tmp_path,
        "tc_no_pkg",
        {
            "tc_name": "TC_NO_PKG",
            "steps": [{"action": "verify_text", "target": "환영"}],
        },
    )
    adb = _make_adb_mock(xml_output='<hierarchy><node text="환영" /></hierarchy>')
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
    )
    assert manifest["app"]["package_name"] is None
    assert manifest["app"]["installed"] is None
    assert manifest["app"]["version_name"] is None
    assert manifest["app"]["version_code"] is None
    assert manifest["permissions"]["parse_status"] == "ok"
    assert manifest["permissions"]["required"] == []
    assert manifest["permissions"]["grants"] == {}
    assert "package_name_missing" in manifest["preflight_status"]["reasons"]
    assert manifest["preflight_status"]["level"] == "WARN"


def test_run_preflight_target_app_package_resolved(tmp_path):
    """metadata.target_app.package 형태 → package_name 추출 + installed/version 진입."""
    tc_path = _write_tc(
        tmp_path,
        "tc_target_app",
        {
            "tc_name": "TC_TARGET_APP",
            "metadata": {
                "target_app": {
                    "package": "com.example.foo",
                    "version": "1.2.3",
                }
            },
            "steps": [{"action": "verify_text", "target": "확인"}],
        },
    )
    adb = _make_adb_mock(
        dumpsys_output="    versionName=1.2.3\n    versionCode=42\n",
        xml_output='<hierarchy><node text="확인" /></hierarchy>',
    )
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
    )
    assert manifest["app"]["package_name"] == "com.example.foo"
    assert manifest["app"]["installed"] is True
    assert manifest["app"]["version_name"] == "1.2.3"
    assert manifest["app"]["version_code"] == 42
    # required=[] 이므로 parse_status는 "ok"
    assert manifest["permissions"]["parse_status"] == "ok"
    # package_name이 추출되었으므로 reason에 package_name_missing 없어야 함
    assert "package_name_missing" not in manifest["preflight_status"]["reasons"]


def test_run_preflight_no_required_no_package(tmp_path):
    """required=[] + package_name missing — permissions parse_status="ok", reasons에 package_name_missing 유지."""
    tc_path = _write_tc(
        tmp_path,
        "tc_no_req_no_pkg",
        {
            "tc_name": "TC_NO_REQ_NO_PKG",
            "steps": [{"action": "verify_text", "target": "확인"}],
        },
    )
    adb = _make_adb_mock(xml_output='<hierarchy><node text="확인" /></hierarchy>')
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
    )
    assert manifest["permissions"]["required"] == []
    assert manifest["permissions"]["grants"] == {}
    assert manifest["permissions"]["parse_status"] == "ok"
    assert "package_name_missing" in manifest["preflight_status"]["reasons"]
    assert "permissions_dump_failed" not in manifest["preflight_status"]["reasons"]


def test_run_preflight_required_but_no_package(tmp_path):
    """required exists + package_name missing — parse_status="failed", package_name_missing reason 유지."""
    tc_path = _write_tc(
        tmp_path,
        "tc_req_no_pkg",
        {
            "tc_name": "TC_REQ_NO_PKG",
            # package_name 의도적으로 누락; pm grant 라인은 다른 패키지명을 갖지만
            # extract_required_permissions에 package_name=None을 넘기면 모든 매칭이 채택됨.
            "steps": [
                {
                    "action": "shell",
                    "command": "pm grant com.someother.app android.permission.READ_PHONE_STATE",
                },
                {"action": "verify_text", "target": "확인"},
            ],
        },
    )
    adb = _make_adb_mock(xml_output='<hierarchy><node text="확인" /></hierarchy>')
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
    )
    assert manifest["permissions"]["required"] == ["android.permission.READ_PHONE_STATE"]
    assert manifest["permissions"]["grants"] == {}
    assert manifest["permissions"]["parse_status"] == "failed"
    assert "package_name_missing" in manifest["preflight_status"]["reasons"]
    # 새 분기에서는 dumpsys 단계까지 진입하지 않으므로 permissions_dump_failed 미발생
    assert "permissions_dump_failed" not in manifest["preflight_status"]["reasons"]


def test_run_preflight_screenshot_skipped(tmp_path):
    tc_path = _write_tc(
        tmp_path,
        "tc_skip_ss",
        {
            "tc_name": "TC_SKIP_SS",
            "package_name": "com.example.foo",
            "steps": [{"action": "verify_text", "target": "OK"}],
        },
    )
    adb = _make_adb_mock(xml_output='<hierarchy><node text="OK" /></hierarchy>')
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
        take_screenshot=False,
    )
    assert manifest["screen"]["screenshot_path"] is None
    assert manifest["screen"]["screenshot_status"] == "skipped"
    assert manifest["screen"]["screenshot_sha256"] is None
    assert manifest["screen"]["window_dump_path"] == "window_dump.xml"
    assert manifest["screen"]["xml_status"] == "ok"
    assert manifest["screen"]["xml_sha256"] is not None
    assert not (out_dir / "screenshot.png").exists()
    assert (out_dir / "window_dump.xml").exists()
    adb.screenshot.assert_not_called()


def test_run_preflight_xml_dump_failed(tmp_path):
    tc_path = _write_tc(
        tmp_path,
        "tc_xml_fail",
        {
            "tc_name": "TC_XML_FAIL",
            "package_name": "com.example.foo",
            "steps": [{"action": "verify_text", "target": "X"}],
        },
    )
    adb = _make_adb_mock(raise_xml=True)
    out_dir = tmp_path / "out"
    manifest = run_preflight(
        tc_path=tc_path,
        output_dir=out_dir,
        adb=adb,
        run_id="RID",
    )
    assert manifest["screen"]["xml_status"] == "failed"
    assert manifest["screen"]["window_dump_path"] is None
    assert manifest["screen"]["xml_sha256"] is None
    assert manifest["text_model"]["diff_status"] == "skipped"
    assert manifest["text_model"]["missing_expected_texts"] == []
    assert "xml_dump_failed" in manifest["preflight_status"]["reasons"]
    assert manifest["preflight_status"]["level"] == "WARN"
    # warn-only: file is still written
    assert (out_dir / "manifest.json").exists()


# ---------------------------------------------------------------------------
# CLI integration (4)
# ---------------------------------------------------------------------------


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    repo_root = Path(__file__).resolve().parent.parent
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo_root,
    )


def test_cli_preflight_neither_arg_exits_1(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = _run_cli(["preflight"])
    assert result.returncode == 1
    assert "정확히 하나만" in (result.stderr or "")


def test_cli_preflight_both_args_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tc = _write_tc(tmp_path, "tc_x", {"tc_name": "TC_X", "steps": [{"action": "wait", "duration": 1}]})
    target_dir = tmp_path / "tcs"
    target_dir.mkdir()
    result = _run_cli(["preflight", str(tc), "--dir", str(target_dir)])
    assert result.returncode == 1
    assert "정확히 하나만" in (result.stderr or "")


def test_cli_preflight_single_tc_creates_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tc = _write_tc(
        tmp_path,
        "tc_solo",
        {
            "tc_name": "TC_SOLO",
            "package_name": "com.example.foo",
            "steps": [{"action": "verify_text", "target": "OK"}],
        },
    )

    fake_adb = _make_adb_mock(xml_output='<hierarchy><node text="OK" /></hierarchy>')

    from src import cli as cli_mod

    with patch.object(cli_mod, "ADB", return_value=fake_adb):
        cli_mod.main_argv = ["preflight", str(tc), "--run-id", "RIDSOLO"]
        argv = ["src.cli", "preflight", str(tc), "--run-id", "RIDSOLO"]
        with patch.object(sys, "argv", argv):
            cli_mod.main()

    manifest_path = tmp_path / "reports" / "preflight" / "RIDSOLO" / "manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["tc_id"] == "TC_SOLO"
    assert data["run_id"] == "RIDSOLO"


def test_cli_preflight_dir_mode_subdirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tc_dir = tmp_path / "batch"
    tc_dir.mkdir()
    _write_tc(
        tc_dir,
        "alpha",
        {
            "tc_name": "ALPHA",
            "package_name": "com.example.foo",
            "steps": [{"action": "verify_text", "target": "A"}],
        },
    )
    _write_tc(
        tc_dir,
        "beta",
        {
            "tc_name": "BETA",
            "package_name": "com.example.foo",
            "steps": [{"action": "verify_text", "target": "B"}],
        },
    )

    fake_adb = _make_adb_mock(xml_output='<hierarchy><node text="A" /><node text="B" /></hierarchy>')

    from src import cli as cli_mod

    with patch.object(cli_mod, "ADB", return_value=fake_adb):
        argv = ["src.cli", "preflight", "--dir", str(tc_dir), "--run-id", "RIDDIR", "--no-screenshot"]
        with patch.object(sys, "argv", argv):
            cli_mod.main()

    base = tmp_path / "reports" / "preflight" / "RIDDIR"
    assert (base / "alpha" / "manifest.json").exists()
    assert (base / "beta" / "manifest.json").exists()
    assert not (base / "alpha" / "screenshot.png").exists()
