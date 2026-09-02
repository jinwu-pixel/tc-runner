from __future__ import annotations

import importlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent


def _load_script(module_name: str):
    path = ROOT / "scripts" / f"{module_name}.py"
    assert path.is_file(), f"missing production module: {path}"
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    importlib.invalidate_caches()
    return importlib.import_module(module_name)


def _fresh_script(module_name: str):
    sys.modules.pop(module_name, None)
    return _load_script(module_name)


def test_profile_has_exact_known_bad_identity_and_apk_pins():
    profiles = _load_script("appwidget_stale_provider_profiles")

    profile = profiles.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]

    assert profile["model"] == "AT-M140"
    assert profile["fingerprint"] == (
        "ALT/alt_thor2/thor2:14/UP1A.231005.007/"
        "RY07260901S:user/release-keys"
    )
    assert profile["incremental"] == "RY07260901S"
    assert profile["viewport"] == (480, 800)
    assert profile["simple_home"] == "com.hnlens.simplemode"
    assert profile["general_home"] == "com.hnlens.launcher3"
    assert profile["general_home_activity"] == (
        "com.hnlens.launcher3/com.android.launcher3.uioverrides.QuickstepLauncher"
    )
    assert profile["switch_activity"] == (
        "com.hnlens.simplemode/.ui.home.SwitchModeActivity"
    )
    assert profile["launcher_package"] == "com.hnlens.launcher3"
    assert profile["app"]["package"] == "com.winson.simpleclock"
    assert profile["app"]["version_name"] == "2.1.6"
    assert profile["app"]["version_code"] == 216
    assert profile["app"]["signature_token"] == "498de32a"
    assert profile["app"]["provider"] == (
        "com.winson.simpleclock/"
        "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
    )
    assert profile["app"]["source_bundle"] == (
        "AT-M140 - Launcher BUG27084/evidence/"
        "20260828T221502KST_widget_generality"
    )
    assert profile["app"]["source_manifest_sha256"] == (
        "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8"
    )
    assert profile["app"]["splits"] == (
        (
            "base.apk",
            23871293,
            "BC7CFFF4E2A441864B35B9064EA6B4E0B3D907FCAA788C4F83EAA7F0152F0B29",
        ),
        (
            "split_config.ko.apk",
            33177,
            "5711AF8D4E523EC7768C6DBCE0D2E480AFA36B0AFB638B0D1A85BB5E32C94003",
        ),
        (
            "split_config.tvdpi.apk",
            167375,
            "3C03AF1D7B647A389FEA8F96EAF181B34B0F0DED077A0C0B49B8ED951061C92E",
        ),
    )
    assert profile["ui"] == {
        "home_long_press": (240, 350, 1200),
        "widget_menu_text": "위젯",
        "widget_search_text": "검색",
        "provider_label": "SimpleClock",
        "widget_drag": (240, 560, 240, 240, 1200),
        "widget_remove_drag": (240, 240, 150, 70, 1200),
        "widget_education_close_resource_id": "com.hnlens.launcher3:id/edu_close_button",
        "widget_drag_tip_text": "길게 터치하여 위젯을 이동하세요.",
        "provider_confirm_text": "OK",
        "provider_confirm_fallback": (346, 741),
    }
    assert profile["mode_ui"] == {
        "switch_to_general_resource_id": "com.hnlens.simplemode:id/rb_normal",
        "switch_to_simple_resource_id": "com.hnlens.simplemode:id/rb_simple",
        "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
        "always_allow_text": "항상 허용",
    }
    assert profile["recovery_ui"] == {
        "launcher_crash_titles": (
            "MIVE Home이(가) 중지됨",
            "MIVE Home이(가) 계속 중단됨",
        ),
        "title_resource_id": "android:id/alertTitle",
        "close_resource_id": "android:id/aerr_close",
    }
    assert profile["evidence_root"] == "AT-M140 - Launcher BUG27084/evidence"


def test_accuweather_profile_has_exact_calibrated_identity_apk_pins_and_ui():
    profiles = _load_script("appwidget_stale_provider_profiles")

    profile = profiles.PROFILES["AT_M140_BUG27084_ACCUWEATHER_V1"]

    assert profile["model"] == "AT-M140"
    assert profile["fingerprint"] == (
        "ALT/alt_thor2/thor2:14/UP1A.231005.007/"
        "RY07260901S:user/release-keys"
    )
    assert profile["incremental"] == "RY07260901S"
    assert profile["viewport"] == (480, 800)
    assert profile["app"] == {
        "package": "com.accuweather.android",
        "provider": (
            "com.accuweather.android/"
            "com.accuweather.android.widgets.todaytonighttomorrow.ui."
            "TodayTonightTomorrowWidgetProvider"
        ),
        "version_name": "21.1.15-3-rc",
        "version_code": 210115003,
        "signature_token": "d4f22e39",
        "source_bundle": (
            "AT-M140 - Launcher BUG27084/evidence/"
            "20260828T221502KST_widget_generality"
        ),
        "source_manifest_sha256": (
            "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8"
        ),
        "apk_dir": "accuweather_apk",
        "splits": (
            (
                "base.apk",
                29421672,
                "D1E0FE5245F94D9538823F7BFA79864EE6D802CFFABE11D813A5D07834A55C41",
            ),
            (
                "split_config.armeabi_v7a.apk",
                53779,
                "8B5E10EF5404C646D72E097AE0882FA3756C31192C546307F45F98ED7C9E1125",
            ),
            (
                "split_config.ko.apk",
                74137,
                "03D0D7B0DDCA87F4A34D47D389AAAC1ABB0EA4761C866A979618B0B76FEC2E63",
            ),
            (
                "split_config.tvdpi.apk",
                612677,
                "7D3D6A8D987CD3FCB53F99C1D69A863C2F340B6B4B64A02B2FD1EBF8255E2B2A",
            ),
        ),
    }
    assert profile["ui"] == {
        "home_long_press": (240, 250, 1200),
        "widget_menu_text": "위젯",
        "widget_search_text": "검색",
        "provider_label": "AccuWeather",
        "provider_variant_text": "36시간 예보",
        "widget_drag": (240, 485, 240, 240, 1500),
        "widget_remove_drag": (297, 187, 150, 70, 1200),
        "widget_remove_selector": "36시간 예보",
        "widget_remove_resource_id": (
            "com.hnlens.launcher3:id/widget_resize_frame"
        ),
        "widget_education_close_resource_id": (
            "com.hnlens.launcher3:id/edu_close_button"
        ),
        "widget_drag_tip_text": "길게 터치하여 위젯을 이동하세요.",
        "provider_confirm_required": True,
        "provider_confirm_resource_id": (
            "com.accuweather.android:id/widget_confirm_submit_button"
        ),
        "provider_confirm_text": "저장",
        "provider_confirm_fallback": (240, 736),
    }
    assert profile["evidence_root"] == "AT-M140 - Launcher BUG27084/evidence"


def test_parse_adb_devices_preserves_target_state_without_metadata():
    parsers = _load_script("appwidget_stale_provider_parsers")
    stdout = """List of devices attached
B06201249E00030C device product:thor2 model:AT-M140 transport_id:4
ODIN2 offline transport_id:7
BROKEN unauthorized usb:1-1

"""

    assert parsers.parse_adb_devices(stdout) == {
        "B06201249E00030C": "device",
        "ODIN2": "offline",
        "BROKEN": "unauthorized",
    }


def test_package_parser_extracts_version_signature_uid_and_flags():
    parsers = _load_script("appwidget_stale_provider_parsers")
    stdout = """
Packages:
  Package [com.winson.simpleclock] (123abc):
    userId=10234
    versionCode=216 minSdk=23 targetSdk=35
    versionName=2.1.6
    signatures=PackageSignatures{abc version:3, signatures:[498de32a]}
    User 0: ceDataInode=1 installed=true hidden=false suspended=false
      stopped=true notLaunched=true enabled=0
"""

    state = parsers.parse_package_state(stdout, "com.winson.simpleclock")

    assert state.package == "com.winson.simpleclock"
    assert state.version_name == "2.1.6"
    assert state.version_code == 216
    assert state.signature_token == "498de32a"
    assert state.uid == 10234
    assert state.stopped is True
    assert state.not_launched is True


def test_package_parser_accepts_production_app_id_as_package_uid():
    """Catch rejection of Android 14 package dumps that expose appId, not userId."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    stdout = """
Packages:
  Package [com.winson.simpleclock] (123abc):
    appId=10194
    versionCode=216 minSdk=23 targetSdk=35
    versionName=2.1.6
    signatures=PackageSignatures{abc version:3, signatures:[498de32a]}
    User 0: ceDataInode=1 installed=true hidden=false suspended=false
      stopped=true notLaunched=true enabled=0
"""

    state = parsers.parse_package_state(stdout, "com.winson.simpleclock")

    assert state.uid == 10194


def test_appwidget_parser_separates_registered_provider_from_bound_widget():
    parsers = _load_script("appwidget_stale_provider_parsers")
    component = (
        "com.winson.simpleclock/"
        "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
    )
    stdout = f"""
Providers:
  Provider{{id=42 uid=10234 cmp={component}}}
Widgets:
  AppWidgetId{{user:0, appWidgetId:17, hostId=HostId{{user:0, app:10123,
    hostId:1024, pkg:com.hnlens.launcher3}}, provider={component},
    views=android.widget.RemoteViews}}
"""

    state = parsers.parse_appwidget_state(
        stdout, component, "com.hnlens.launcher3"
    )

    assert state.provider_registered is True
    assert state.provider_uid == 10234
    assert len(state.bindings) == 1
    assert state.bindings[0].widget_id == 17
    assert state.bindings[0].provider_component == component
    assert state.bindings[0].host_package == "com.hnlens.launcher3"
    assert state.bindings[0].remote_views_present is True


def test_appwidget_parser_registry_only_is_not_a_binding():
    parsers = _load_script("appwidget_stale_provider_parsers")
    component = (
        "com.winson.simpleclock/"
        "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
    )
    stdout = f"Providers:\n  Provider{{uid=10299 cmp={component}}}\nWidgets:\n"

    state = parsers.parse_appwidget_state(
        stdout, component, "com.hnlens.launcher3"
    )

    assert state.provider_registered is True
    assert state.provider_uid == 10299
    assert state.bindings == ()


def test_home_role_parser_uses_exact_holder_or_resumed_field_not_package_order():
    """Catch Simple HOME winning merely because both package names occur in a dump."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    profile = {
        "simple_home": "com.hnlens.simplemode",
        "general_home": "com.hnlens.launcher3",
    }
    activity = (
        "Recent #0: com.hnlens.simplemode/.Home\n"
        "mResumedActivity: ActivityRecord{abc u0 com.hnlens.launcher3/.Home t12}\n"
    )

    assert parsers.parse_home_role(activity, profile) == "com.hnlens.launcher3"
    assert parsers.parse_home_role("com.hnlens.launcher3\n", profile) == (
        "com.hnlens.launcher3"
    )
    assert parsers.parse_home_role(
        "history com.hnlens.simplemode and com.hnlens.launcher3", profile
    ) == "UNKNOWN"


def test_home_role_parser_distinguishes_simple_general_and_unknown():
    parsers = _load_script("appwidget_stale_provider_parsers")
    profile = {
        "simple_home": "com.hnlens.simplemode",
        "general_home": "com.hnlens.launcher3",
    }

    assert parsers.parse_home_role(
        "com.hnlens.simplemode\n", profile
    ) == "com.hnlens.simplemode"
    assert parsers.parse_home_role(
        "mResumedActivity: com.hnlens.launcher3/.QuickstepLauncher", profile
    ) == "com.hnlens.launcher3"
    assert parsers.parse_home_role(
        "mResumedActivity: com.example.other/.Home", profile
    ) == "UNKNOWN"


@pytest.mark.parametrize(
    "activity",
    [
        (
            "ResumedActivity: ActivityRecord{5b7f1 u0 "
            "com.hnlens.launcher3/com.android.launcher3.uioverrides."
            "QuickstepLauncher t42}"
        ),
        (
            "topResumedActivity=ActivityRecord{5b7f1 u0 "
            "com.hnlens.launcher3/com.android.launcher3.uioverrides."
            "QuickstepLauncher t42}"
        ),
    ],
)
def test_home_role_parser_accepts_production_resumed_activity_fields(activity):
    """Minimal field forms copied from the preserved AT-M140 activity dump."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    profile = {
        "simple_home": "com.hnlens.simplemode",
        "general_home": "com.hnlens.launcher3",
    }

    assert parsers.parse_home_role(activity, profile) == "com.hnlens.launcher3"


def test_crash_parser_requires_both_lines_in_the_same_record():
    parsers = _load_script("appwidget_stale_provider_parsers")
    same_record = """FATAL EXCEPTION: main
java.lang.NullPointerException
  at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185
  at com.android.launcher3.widget.PendingAppWidgetHostView.java:88
"""
    split_records = """FATAL EXCEPTION: main
  at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185

FATAL EXCEPTION: main
  at com.android.launcher3.widget.PendingAppWidgetHostView.java:88
"""

    assert parsers.parse_crash_signature(same_record).count == 1
    assert parsers.parse_crash_signature(split_records).count == 0


def test_launcher_crash_exit_parser_uses_stable_identity_and_exact_package():
    parsers = _load_script("appwidget_stale_provider_parsers")
    transcript = """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:19:23.986 pid=23363 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
ApplicationExitInfo #1:
  timestamp=2026-09-01 15:18:52.665 pid=22527 realUid=10151
  process=com.hnlens.launcher3 reason=13 (OTHER KILLS BY SYSTEM) subreason=11
ApplicationExitInfo #2:
  timestamp=2026-09-01 15:18:10.000 pid=22000 realUid=10152
  process=com.example.other reason=4 (APP CRASH(EXCEPTION)) subreason=0
"""

    exits = parsers.parse_launcher_crash_exits(
        transcript, "com.hnlens.launcher3"
    )

    assert len(exits) == 1
    assert exits[0].timestamp == "2026-09-01 15:19:23.986"
    assert exits[0].pid == 23363
    assert exits[0].process == "com.hnlens.launcher3"
    assert exits[0].reason_code == 4


def test_import_has_no_subprocess_side_effect(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("module import invoked subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)

    _fresh_script("appwidget_stale_provider_cli")


def test_plan_is_default_and_adb_free(monkeypatch, capsys):
    cli = _fresh_script("appwidget_stale_provider_cli")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("plan invoked subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)

    assert cli.main(["--profile", "AT_M140_BUG27084_KNOWN_BAD_V1"]) == 0
    default_bytes = capsys.readouterr().out.encode("utf-8")
    assert cli.main(
        ["plan", "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1"]
    ) == 0
    explicit_bytes = capsys.readouterr().out.encode("utf-8")

    assert default_bytes == explicit_bytes
    payload = json.loads(default_bytes)
    assert payload["adb"] == "OFF"
    assert payload["profile"] == "AT_M140_BUG27084_KNOWN_BAD_V1"
    assert payload["identity"] == {
        "model": "AT-M140",
        "fingerprint": (
            "ALT/alt_thor2/thor2:14/UP1A.231005.007/"
            "RY07260901S:user/release-keys"
        ),
        "viewport": [480, 800],
    }
    assert [phase["command"] for phase in payload["phases"]] == [
        "capture",
        "bind",
        "arm",
        "trigger",
        "verify",
        "restore",
        "reset-fixture",
        "cleanup-widget",
    ]
    assert payload["phases"][0]["mutating"] is False
    assert payload["phases"][1]["requires_execute"] is True
    restore_phase = next(
        phase for phase in payload["phases"] if phase["command"] == "restore"
    )
    assert restore_phase["conditional_actions"] == [
        {
            "action": "install-multiple",
            "condition": "interrupted lifecycle left the exact package absent",
            "requires_flag": "--recover-package",
        },
        {
            "action": "cmd role add-role-holder",
            "condition": "verified General HOME crash loop blocks UI restore",
            "requires_flag": "--direct-home-role-recovery",
        },
    ]
    assert payload["source_manifest_sha256"] == (
        "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8"
    )


def test_unknown_profile_returns_exit_2(capsys):
    cli = _fresh_script("appwidget_stale_provider_cli")

    assert cli.main(["plan", "--profile", "MISSING"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown profile: MISSING" in captured.err


def test_transport_prefixes_exact_serial_and_rejects_selector_injection():
    models = _load_script("appwidget_stale_provider_models")
    transport_module = _load_script("appwidget_stale_provider_transport")
    calls: list[tuple[str, ...]] = []

    def runner(argv, timeout_s, binary):
        calls.append(tuple(argv))
        return models.CommandResult(tuple(argv), 0, "ok\n", "")

    transport = transport_module.AdbTransport("B06201249E00030C", runner=runner)

    result = transport.run_target(("shell", "getprop", "ro.product.model"))

    assert result.argv == (
        "adb",
        "-s",
        "B06201249E00030C",
        "shell",
        "getprop",
        "ro.product.model",
    )
    assert calls == [result.argv]
    for unsafe in (
        ("-s", "ODIN2", "shell", "id"),
        ("-d", "shell", "id"),
        ("-e", "shell", "id"),
        ("-t", "7", "shell", "id"),
        ("--transport-id", "7", "shell", "id"),
    ):
        with pytest.raises(transport_module.TransportInputError):
            transport.run_target(unsafe)
    assert calls == [result.argv]


@pytest.mark.parametrize(
    "args",
    [
        ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"),
        ("shell", "logcat", "-t", "10", "-v", "threadtime"),
    ],
)
def test_transport_allows_subcommand_options_after_exact_target_boundary(args):
    """Catch validation that mistakes logcat options for ADB selectors."""
    models = _load_script("appwidget_stale_provider_models")
    transport_module = _load_script("appwidget_stale_provider_transport")
    calls: list[tuple[str, ...]] = []

    def runner(argv, timeout_s, binary):
        calls.append(tuple(argv))
        return models.CommandResult(tuple(argv), 0, "ok\n", "")

    transport = transport_module.AdbTransport("SER", runner=runner)

    result = transport.run_target(args)

    assert result.argv == ("adb", "-s", "SER", *args)
    assert calls == [("adb", "-s", "SER", *args)]


def test_transport_rejects_unlisted_global_option_before_subcommand():
    """Catch future ADB global options bypassing the exact-target boundary."""
    models = _load_script("appwidget_stale_provider_models")
    transport_module = _load_script("appwidget_stale_provider_transport")
    calls: list[tuple[str, ...]] = []

    def runner(argv, timeout_s, binary):
        calls.append(tuple(argv))
        return models.CommandResult(tuple(argv), 0, "ok\n", "")

    transport = transport_module.AdbTransport("SER", runner=runner)

    with pytest.raises(transport_module.TransportInputError):
        transport.run_target(("-H", "other-host", "shell", "id"))

    assert calls == []


def test_only_device_listing_may_omit_serial_and_binary_is_separate():
    models = _load_script("appwidget_stale_provider_models")
    transport_module = _load_script("appwidget_stale_provider_transport")
    calls: list[tuple[tuple[str, ...], bool]] = []

    def runner(argv, timeout_s, binary):
        calls.append((tuple(argv), binary))
        stdout = b"PNG" if binary else "List of devices attached\nSER device\n"
        return models.CommandResult(tuple(argv), 0, stdout, b"" if binary else "")

    transport = transport_module.AdbTransport("SER", runner=runner)

    assert transport.list_devices() == {"SER": "device"}
    assert transport.run_target_binary(("exec-out", "screencap", "-p")).stdout == b"PNG"
    assert calls == [
        (("adb", "devices", "-l"), False),
        (("adb", "-s", "SER", "exec-out", "screencap", "-p"), True),
    ]


@pytest.mark.parametrize("encoding", ["utf-8", "cp949"])
def test_subprocess_transport_decodes_korean_ui_bytes_explicitly(
    monkeypatch, encoding
):
    """Catch Windows locale-dependent corruption of Korean selector text."""
    transport_module = _load_script("appwidget_stale_provider_transport")
    calls = []

    class Completed:
        returncode = 0
        stdout = "간편모드 항상 허용".encode(encoding)
        stderr = "오류 없음".encode(encoding)

    def fake_run(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return Completed()

    monkeypatch.setattr(transport_module.subprocess, "run", fake_run)

    result = transport_module._subprocess_runner(("adb", "shell", "echo"), 3, False)

    assert result.stdout == "간편모드 항상 허용"
    assert result.stderr == "오류 없음"
    assert calls[0][1]["text"] is False


def test_transport_normalizes_subprocess_timeout():
    transport_module = _load_script("appwidget_stale_provider_transport")

    def runner(argv, timeout_s, binary):
        raise transport_module.subprocess.TimeoutExpired(argv, timeout_s)

    transport = transport_module.AdbTransport("SER", runner=runner)

    with pytest.raises(transport_module.TransportTimeout, match="timed out"):
        transport.run_target(("shell", "getprop", "sys.boot_completed"))


@pytest.mark.parametrize("state", [None, "offline", "unauthorized"])
def test_preflight_rejects_missing_offline_and_unauthorized(state):
    models = _load_script("appwidget_stale_provider_models")
    preflight = _load_script("appwidget_stale_provider_preflight")

    class FakeTransport:
        serial = "B06201249E00030C"

        def list_devices(self):
            return {} if state is None else {self.serial: state}

        def run_target(self, _args, timeout_s=60):
            raise AssertionError("identity command issued after connection gate failed")

    with pytest.raises(preflight.IdentityMismatch):
        preflight.preflight_identity(
            FakeTransport(),
            "B06201249E00030C",
            "AT-M140",
            (
                "ALT/alt_thor2/thor2:14/UP1A.231005.007/"
                "RY07260901S:user/release-keys"
            ),
            _load_script("appwidget_stale_provider_profiles").PROFILES[
                "AT_M140_BUG27084_KNOWN_BAD_V1"
            ],
        )


def test_preflight_binds_cli_profile_and_live_identity():
    models = _load_script("appwidget_stale_provider_models")
    transport_module = _load_script("appwidget_stale_provider_transport")
    preflight = _load_script("appwidget_stale_provider_preflight")
    profile = _load_script("appwidget_stale_provider_profiles").PROFILES[
        "AT_M140_BUG27084_KNOWN_BAD_V1"
    ]
    serial = "B06201249E00030C"
    fingerprint = profile["fingerprint"]
    responses = {
        ("adb", "devices", "-l"): (
            "List of devices attached\n"
            f"{serial} device model:AT-M140\n"
            "ODIN2 device model:ODIN2\n"
        ),
        ("adb", "-s", serial, "shell", "getprop", "ro.product.model"): "AT-M140\n",
        (
            "adb",
            "-s",
            serial,
            "shell",
            "getprop",
            "ro.build.fingerprint",
        ): f"{fingerprint}\n",
        (
            "adb",
            "-s",
            serial,
            "shell",
            "getprop",
            "ro.build.version.incremental",
        ): "RY07260901S\n",
        ("adb", "-s", serial, "shell", "wm", "size"): "Physical size: 480x800\n",
    }
    calls: list[tuple[str, ...]] = []

    def runner(argv, timeout_s, binary):
        key = tuple(argv)
        calls.append(key)
        return models.CommandResult(key, 0, responses[key], "")

    identity = preflight.preflight_identity(
        transport_module.AdbTransport(serial, runner=runner),
        serial,
        "AT-M140",
        fingerprint,
        profile,
    )

    assert identity == models.DeviceIdentity(
        serial=serial,
        model="AT-M140",
        fingerprint=fingerprint,
        incremental="RY07260901S",
        viewport=(480, 800),
        connected_devices=((serial, "device"), ("ODIN2", "device")),
    )
    assert all("ODIN2" not in call for call in calls[1:])


@pytest.mark.parametrize(
    ("cli_model", "cli_fingerprint", "live_key", "live_value"),
    [
        ("WRONG", "PROFILE", None, None),
        ("PROFILE", "WRONG", None, None),
        ("PROFILE", "PROFILE", "model", "WRONG"),
        ("PROFILE", "PROFILE", "fingerprint", "WRONG"),
        ("PROFILE", "PROFILE", "viewport", "720x1280"),
    ],
)
def test_preflight_wrong_identity_fails_closed(
    cli_model, cli_fingerprint, live_key, live_value
):
    models = _load_script("appwidget_stale_provider_models")
    preflight = _load_script("appwidget_stale_provider_preflight")
    profile = {
        "model": "PROFILE",
        "fingerprint": "PROFILE",
        "incremental": "INC",
        "viewport": (480, 800),
    }

    class FakeTransport:
        serial = "SER"

        def list_devices(self):
            return {"SER": "device"}

        def run_target(self, args, timeout_s=60):
            command = tuple(args)
            value = {
                ("shell", "getprop", "ro.product.model"): "PROFILE",
                ("shell", "getprop", "ro.build.fingerprint"): "PROFILE",
                ("shell", "getprop", "ro.build.version.incremental"): "INC",
                ("shell", "wm", "size"): "Physical size: 480x800",
            }[command]
            if live_key == "model" and command[-1] == "ro.product.model":
                value = live_value
            if live_key == "fingerprint" and command[-1] == "ro.build.fingerprint":
                value = live_value
            if live_key == "viewport" and command[-2:] == ("wm", "size"):
                value = f"Physical size: {live_value}"
            return models.CommandResult(("adb", "-s", "SER", *command), 0, value, "")

    with pytest.raises(preflight.IdentityMismatch):
        preflight.preflight_identity(
            FakeTransport(), "SER", cli_model, cli_fingerprint, profile
        )


def test_phase_machine_rejects_illegal_order_and_models_negative_control():
    state = _load_script("appwidget_stale_provider_state")
    models = _load_script("appwidget_stale_provider_models")

    assert state.assert_transition(None, "capture") is models.Phase.BASELINE_CAPTURED
    assert state.assert_transition(
        models.Phase.BASELINE_CAPTURED, "bind"
    ) is models.Phase.BOUND_GENERAL
    assert state.assert_transition(
        models.Phase.BOUND_GENERAL, "arm-switch"
    ) is models.Phase.SAFE_SIMPLE
    assert state.assert_transition(
        models.Phase.SAFE_SIMPLE, "arm-lifecycle"
    ) is models.Phase.STALE_ARMED
    assert state.assert_transition(
        models.Phase.SAFE_SIMPLE, "arm-clean-control"
    ) is models.Phase.CLEAN_CONTROL_ARMED
    assert state.assert_transition(
        models.Phase.STALE_ARMED, "trigger", outcome="bug"
    ) is models.Phase.TRIGGERED_BUG
    assert state.assert_transition(
        models.Phase.STALE_ARMED, "trigger", outcome="fixed"
    ) is models.Phase.TRIGGERED_FIXED
    assert state.assert_transition(
        models.Phase.STALE_ARMED, "trigger", outcome="no-bug"
    ) is models.Phase.TRIGGERED_STALE_NO_BUG
    assert state.assert_transition(
        models.Phase.CLEAN_CONTROL_ARMED, "trigger-control", outcome="no-bug"
    ) is models.Phase.TRIGGERED_CONTROL_NO_BUG
    assert state.assert_transition(
        models.Phase.CLEAN_CONTROL_ARMED, "trigger-control", outcome="bug"
    ) is models.Phase.TRIGGERED_CONTROL_BUG
    assert state.assert_transition(
        models.Phase.BOUND_GENERAL, "negative-control-failed"
    ) is models.Phase.BOUND_GENERAL
    assert state.assert_transition(
        models.Phase.TRIGGERED_BUG, "restore"
    ) is models.Phase.RESTORED_SAFE
    with pytest.raises(state.PhaseViolation):
        state.assert_transition(models.Phase.BASELINE_CAPTURED, "trigger")
    with pytest.raises(state.PhaseViolation):
        state.assert_transition(models.Phase.STALE_ARMED, "trigger", outcome="unknown")


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        "20260829T000000",
        "20260829T000000KST",
        "../20260829T000000Z",
        "/tmp/20260829T000000Z",
        "C:/tmp/20260829T000000Z",
        "C:20260829T000000Z",
        "20260829T000000Z\\child",
        "20260829T000000Z\nother",
    ],
)
def test_run_id_rejects_non_exact_or_path_qualified_values(run_id):
    evidence = _load_script("appwidget_stale_provider_evidence")

    with pytest.raises(evidence.EvidenceInputError):
        evidence.validate_run_id(run_id)


def test_run_id_uses_exact_utc_format():
    evidence = _load_script("appwidget_stale_provider_evidence")
    now = datetime(2026, 8, 29, 5, 6, 18, tzinfo=timezone.utc)

    assert evidence.make_run_id(now) == "20260829T050618Z"
    assert evidence.validate_run_id("20260829T050618Z") == "20260829T050618Z"


def test_bundle_writes_deterministic_atomic_json_and_refuses_overwrite(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    models = _load_script("appwidget_stale_provider_models")
    root = tmp_path / "evidence"
    bundle = evidence.EvidenceBundle.create(root, "20260829T050618Z")

    bundle.write_json("run.json", {"z": 2, "a": "한글"})
    evidence.verify_evidence_manifest(bundle.directory)
    bundle.append_event(
        models.Event(
            timestamp_utc="2026-08-29T05:06:18Z",
            timestamp_kst="2026-08-29T14:06:18+09:00",
            phase="BASELINE_CAPTURED",
            command_category="capture",
            target_serial="SER",
            returncode=0,
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            resulting_state="BASELINE_CAPTURED",
        )
    )
    evidence.verify_evidence_manifest(bundle.directory)

    assert (bundle.directory / "run.json").read_bytes() == (
        b'{"a":"\xed\x95\x9c\xea\xb8\x80","z":2}\n'
    )
    event_line = (bundle.directory / "events.jsonl").read_text(
        encoding="utf-8"
    )
    assert event_line.endswith("\n")
    assert json.loads(event_line)["target_serial"] == "SER"
    assert (bundle.directory / "snapshots").is_dir()
    assert (bundle.directory / "screenshots").is_dir()
    assert not list(bundle.directory.glob("*.tmp"))
    with pytest.raises(evidence.EvidenceInputError):
        evidence.EvidenceBundle.create(root, "20260829T050618Z")


@pytest.mark.parametrize("interrupted_target", ["run.json", "evidence_sha256.txt"])
def test_pending_evidence_transaction_recovers_exact_old_or_new_state(
    tmp_path, monkeypatch, interrupted_target
):
    """A hard stop at either replace boundary must remain attestable."""
    evidence = _load_script("appwidget_stale_provider_evidence")
    bundle = evidence.EvidenceBundle.create(tmp_path, "20260829T050618Z")
    bundle.write_json("run.json", {"generation": 1})
    original_atomic_write = evidence._atomic_write

    def interrupt_at_target(path, data):
        if path.name == interrupted_target and (
            bundle.directory / ".evidence_pending.json"
        ).is_file():
            raise OSError(f"simulated hard stop before {interrupted_target}")
        original_atomic_write(path, data)

    monkeypatch.setattr(evidence, "_atomic_write", interrupt_at_target)
    with pytest.raises(OSError, match="simulated hard stop"):
        bundle.write_json("run.json", {"generation": 2})

    assert (bundle.directory / ".evidence_pending.json").is_file()
    monkeypatch.setattr(evidence, "_atomic_write", original_atomic_write)
    evidence.verify_evidence_manifest(bundle.directory)

    expected_generation = 1 if interrupted_target == "run.json" else 2
    assert json.loads((bundle.directory / "run.json").read_text(encoding="utf-8")) == {
        "generation": expected_generation
    }
    assert not (bundle.directory / ".evidence_pending.json").exists()


def test_event_append_is_atomic_and_never_seals_partial_jsonl(tmp_path, monkeypatch):
    evidence = _load_script("appwidget_stale_provider_evidence")
    models = _load_script("appwidget_stale_provider_models")
    bundle = evidence.EvidenceBundle.create(tmp_path, "20260829T050618Z")
    event = models.Event(
        timestamp_utc="2026-08-29T05:06:18Z",
        timestamp_kst="2026-08-29T14:06:18+09:00",
        phase="capture",
        command_category="probe",
        target_serial="SER",
        returncode=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        resulting_state="CAPTURING",
    )
    original_atomic_write = evidence._atomic_write

    def interrupt_manifest(path, data):
        if path.name == "evidence_sha256.txt" and (
            bundle.directory / ".evidence_pending.json"
        ).is_file():
            raise OSError("simulated stop after event replace")
        original_atomic_write(path, data)

    monkeypatch.setattr(evidence, "_atomic_write", interrupt_manifest)
    with pytest.raises(OSError, match="after event replace"):
        bundle.append_event(event)
    monkeypatch.setattr(evidence, "_atomic_write", original_atomic_write)

    evidence.verify_evidence_manifest(bundle.directory)
    event_bytes = (bundle.directory / "events.jsonl").read_bytes()
    assert event_bytes.endswith(b"\n")
    assert len(event_bytes.splitlines()) == 1
    assert json.loads(event_bytes) ["target_serial"] == "SER"

    evidence.write_evidence_artifact(
        bundle.directory, "events.jsonl", event_bytes + b'{"partial":'
    )
    with pytest.raises(evidence.EvidenceInputError, match="complete JSON lines"):
        bundle.append_event(event)


def test_second_process_is_blocked_by_run_level_writer_lock(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(tmp_path, profile)
    transport = _ScriptedTransport(models, {})

    with evidence.exclusive_run_lock(bundle.directory):
        evidence.verify_evidence_manifest(bundle.directory)
        with pytest.raises(orchestrator.GateFailure, match="already active"):
            orchestrator.bind(
                repo_root=tmp_path,
                profile=profile,
                transport=transport,
                serial="SER",
                expected_model="AT-M140",
                expected_fingerprint="FINGERPRINT",
                run_id="20260829T050618Z",
                execute=True,
            )

    state = json.loads((bundle.directory / "run.json").read_text(encoding="utf-8"))
    assert state.get("attempts", []) == []
    assert transport.calls == []
    evidence.verify_evidence_manifest(bundle.directory)


def test_command_event_records_state_boot_and_redacted_logical_splits(tmp_path):
    """Catch events that cannot reconstruct install intent or leak host paths."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(tmp_path, profile)
    command = (
        "install-multiple",
        r"C:\secret\base.apk",
        r"C:\secret\split_config.ko.apk",
    )
    transport = _ScriptedTransport(models, {command: "Success\n"})

    orchestrator._record_command(
        bundle,
        transport,
        "SER",
        "arm",
        "install_verified_splits",
        command,
    )
    _load_script("appwidget_stale_provider_evidence").verify_evidence_manifest(
        bundle.directory
    )

    event = json.loads(
        (bundle.directory / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    assert event["boot_id"] == "boot-1"
    assert event["previous_state"] == "BASELINE_CAPTURED"
    assert event["resulting_state"] == "BASELINE_CAPTURED"
    assert event["logical_command"] == [
        "install-multiple",
        "<split:base.apk>",
        "<split:split_config.ko.apk>",
    ]
    assert "C:\\secret" not in json.dumps(event)


def test_manifest_is_sorted_and_excludes_its_own_digest(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    bundle = evidence.EvidenceBundle.create(tmp_path, "20260829T050618Z")
    (bundle.directory / "z.txt").write_bytes(b"z")
    (bundle.directory / "snapshots" / "a.txt").write_bytes(b"a")

    manifest = evidence.write_evidence_manifest(bundle.directory)
    lines = manifest.read_text(encoding="utf-8").splitlines()

    assert lines == sorted(lines, key=lambda line: line.split("  ", 1)[1])
    assert any(line.endswith("  snapshots/a.txt") for line in lines)
    assert any(line.endswith("  z.txt") for line in lines)
    assert all("evidence_sha256.txt" not in line for line in lines)


def _profile_for_input_fixture(
    source_bundle: str,
    source_manifest: Path,
    apk_dir_name: str = "simpleclock_apk",
):
    apk_dir = source_manifest.parent / apk_dir_name
    splits = []
    for name in ("base.apk", "split_config.ko.apk", "split_config.tvdpi.apk"):
        data = (apk_dir / name).read_bytes()
        splits.append((name, len(data), hashlib.sha256(data).hexdigest().upper()))
    return {
        "app": {
            "apk_dir": apk_dir_name,
            "source_bundle": source_bundle,
            "source_manifest_sha256": hashlib.sha256(
                source_manifest.read_bytes()
            ).hexdigest().upper(),
            "splits": tuple(splits),
            "package": "com.winson.simpleclock",
            "version_name": "2.1.6",
            "version_code": 216,
            "signature_token": "498de32a",
        }
    }


def test_verify_inputs_accepts_exact_manifest_size_and_hash(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    source = tmp_path / "evidence" / "source"
    apk_dir = source / "simpleclock_apk"
    apk_dir.mkdir(parents=True)
    (apk_dir / "base.apk").write_bytes(b"base")
    (apk_dir / "split_config.ko.apk").write_bytes(b"ko")
    (apk_dir / "split_config.tvdpi.apk").write_bytes(b"tvdpi")
    manifest = source / "evidence_sha256.txt"
    manifest.write_bytes(b"immutable source manifest\n")
    profile = _profile_for_input_fixture("evidence/source", manifest)

    verified = evidence.verify_inputs(tmp_path, profile)

    assert verified["source_bundle"] == "evidence/source"
    assert verified["source_manifest_sha256"] == profile["app"][
        "source_manifest_sha256"
    ]
    assert [item["logical_id"] for item in verified["splits"]] == [
        "simpleclock_apk/base.apk",
        "simpleclock_apk/split_config.ko.apk",
        "simpleclock_apk/split_config.tvdpi.apk",
    ]
    assert all("absolute_path" not in item for item in verified["splits"])


@pytest.mark.parametrize("fault", ["manifest", "size", "hash"])
def test_verify_inputs_rejects_each_identity_mismatch(tmp_path, fault):
    evidence = _load_script("appwidget_stale_provider_evidence")
    source = tmp_path / "evidence" / "source"
    apk_dir = source / "simpleclock_apk"
    apk_dir.mkdir(parents=True)
    for name, data in (
        ("base.apk", b"base"),
        ("split_config.ko.apk", b"ko"),
        ("split_config.tvdpi.apk", b"tvdpi"),
    ):
        (apk_dir / name).write_bytes(data)
    manifest = source / "evidence_sha256.txt"
    manifest.write_bytes(b"manifest\n")
    profile = _profile_for_input_fixture("evidence/source", manifest)
    if fault == "manifest":
        profile["app"]["source_manifest_sha256"] = "0" * 64
    elif fault == "size":
        name, size, digest = profile["app"]["splits"][0]
        profile["app"]["splits"] = ((name, size + 1, digest), *profile["app"]["splits"][1:])
    else:
        name, size, _digest = profile["app"]["splits"][0]
        profile["app"]["splits"] = ((name, size, "0" * 64), *profile["app"]["splits"][1:])

    with pytest.raises(evidence.EvidenceInputError):
        evidence.verify_inputs(tmp_path, profile)


@pytest.mark.parametrize(
    "source_bundle",
    ["../outside", "/abs/path", "C:/abs/path", "C:drive-relative", "bad\\path"],
)
def test_verify_inputs_rejects_non_relative_source_bundle(tmp_path, source_bundle):
    evidence = _load_script("appwidget_stale_provider_evidence")
    profile = {"app": {"source_bundle": source_bundle}}

    with pytest.raises(evidence.EvidenceInputError):
        evidence.verify_inputs(tmp_path, profile)


def _capture_profile_and_repo(tmp_path):
    source = tmp_path / "source"
    apk_dir = source / "simpleclock_apk"
    apk_dir.mkdir(parents=True)
    for name, data in (
        ("base.apk", b"base"),
        ("split_config.ko.apk", b"ko"),
        ("split_config.tvdpi.apk", b"tvdpi"),
    ):
        (apk_dir / name).write_bytes(data)
    manifest = source / "evidence_sha256.txt"
    manifest.write_bytes(b"source manifest\n")
    profile = _profile_for_input_fixture("source", manifest)
    profile.update(
        {
            "model": "AT-M140",
            "fingerprint": "FINGERPRINT",
            "incremental": "INC",
            "viewport": (480, 800),
            "simple_home": "com.hnlens.simplemode",
            "general_home": "com.hnlens.launcher3",
            "general_home_activity": "com.hnlens.launcher3/.Home",
            "switch_activity": "com.hnlens.simplemode/.SwitchModeActivity",
            "launcher_package": "com.hnlens.launcher3",
            "evidence_root": "out",
            "ui": {
                "home_long_press": (240, 350, 1200),
                "widget_menu_text": "위젯",
                "widget_search_text": "검색",
                "provider_label": "SimpleClock",
                "widget_drag": (240, 560, 240, 240, 1200),
                "widget_remove_drag": (240, 240, 150, 70, 1200),
                "widget_education_close_resource_id": (
                    "com.hnlens.launcher3:id/edu_close_button"
                ),
                "widget_drag_tip_text": "길게 터치하여 위젯을 이동하세요.",
                "provider_confirm_text": "OK",
                "provider_confirm_fallback": (346, 741),
            },
            "mode_ui": {
                "switch_to_general_resource_id": (
                    "com.hnlens.simplemode:id/rb_normal"
                ),
                "switch_to_simple_resource_id": (
                    "com.hnlens.simplemode:id/rb_simple"
                ),
                "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
                "always_allow_text": "항상 허용",
            },
        }
    )
    profile["app"].update(
        {
            "provider": "com.winson.simpleclock/.SimpleClockWidgetProvider",
        }
    )
    return profile


class _ScriptedTransport:
    def __init__(self, models, responses, *, serial="SER"):
        self.serial = serial
        self._models = models
        transport_module = _load_script("appwidget_stale_provider_transport")
        self._responses = {
            tuple(key): list(value) if isinstance(value, list) else [value]
            for key, value in responses.items()
        }
        self.calls = []
        self._transport = transport_module.AdbTransport(serial, runner=self._runner)

    def list_devices(self):
        return self._transport.list_devices()

    def _runner(self, argv, timeout_s, binary):
        full_argv = tuple(argv)
        if full_argv == ("adb", "devices", "-l"):
            self.calls.append(("devices",))
            stdout = (
                "List of devices attached\n"
                f"{self.serial} device model:TEST\n"
                "ODIN2 device model:ODIN2\n"
            )
            return self._models.CommandResult(full_argv, 0, stdout, "")
        prefix = ("adb", "-s", self.serial)
        if full_argv[:3] != prefix:
            raise AssertionError(f"unexpected ADB target prefix: {full_argv}")
        key = full_argv[3:]
        self.calls.append(key)
        if key not in self._responses or not self._responses[key]:
            raise AssertionError(f"unexpected transport call: {key}")
        value = self._responses[key].pop(0)
        if isinstance(value, Exception):
            raise value
        if callable(value):
            value = value(full_argv, binary)
        if isinstance(value, self._models.CommandResult):
            return value
        stdout = value
        stderr = b"" if binary else ""
        return self._models.CommandResult(full_argv, 0, stdout, stderr)

    def run_target(self, args, timeout_s=60):
        return self._transport.run_target(args, timeout_s)

    def run_target_binary(self, args, timeout_s=60):
        return self._transport.run_target_binary(args, timeout_s)


def _capture_responses(profile, *, screenshot=b"\x89PNG\r\n\x1a\nPNG"):
    component = profile["app"]["provider"]
    package = profile["app"]["package"]
    return {
        ("shell", "getprop", "ro.product.model"): ["AT-M140\n", "AT-M140\n"],
        ("shell", "getprop", "ro.build.fingerprint"): [
            "FINGERPRINT\n",
            "FINGERPRINT\n",
        ],
        ("shell", "getprop", "ro.build.version.incremental"): ["INC\n", "INC\n"],
        ("shell", "wm", "size"): ["Physical size: 480x800\n", "Physical size: 480x800\n"],
        ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
            "com.hnlens.simplemode\n"
        ),
        ("shell", "dumpsys", "activity", "activities"): (
            "mResumedActivity: com.hnlens.simplemode/.Home\n"
        ),
        ("shell", "dumpsys", "package", package): (
            "userId=10234\nversionCode=216\nversionName=2.1.6\n"
            "signatures=PackageSignatures{signatures:[498de32a]}\n"
            "stopped=false notLaunched=false\n"
        ),
        ("shell", "dumpsys", "appwidget"): (
            f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
        ),
        ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
        ("shell", "logcat", "-d", "-v", "threadtime"): "",
        ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): (
            "ACTIVITY MANAGER LRU PROCESSES\n"
        ),
        ("shell", "cat", "/proc/sys/kernel/random/boot_id"): "boot-1\n",
        ("shell", "cat", "/proc/uptime"): "123.45 67.89\n",
        ("exec-out", "uiautomator", "dump", "/dev/tty"): (
            '<?xml version="1.0"?><hierarchy><node text="간편모드" '
            'bounds="[0,0][480,800]" /></hierarchy>'
            "UI hierchary dumped to: /dev/tty\n"
        ),
        ("exec-out", "screencap", "-p"): screenshot,
    }


def test_verify_inputs_and_install_paths_support_profile_apk_directory(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    source = tmp_path / "evidence" / "source"
    apk_dir = source / "accuweather_apk"
    apk_dir.mkdir(parents=True)
    for name, data in (
        ("base.apk", b"accu-base"),
        ("split_config.ko.apk", b"accu-ko"),
        ("split_config.tvdpi.apk", b"accu-tvdpi"),
    ):
        (apk_dir / name).write_bytes(data)
    manifest = source / "evidence_sha256.txt"
    manifest.write_bytes(b"accuweather source manifest\n")
    profile = _profile_for_input_fixture(
        "evidence/source",
        manifest,
        apk_dir_name="accuweather_apk",
    )

    verified = evidence.verify_inputs(tmp_path, profile)
    install_paths = orchestrator._verified_apk_paths(tmp_path, profile, verified)

    assert [item["logical_id"] for item in verified["splits"]] == [
        "accuweather_apk/base.apk",
        "accuweather_apk/split_config.ko.apk",
        "accuweather_apk/split_config.tvdpi.apk",
    ]
    assert install_paths == tuple(
        str((apk_dir / name).resolve())
        for name in (
            "base.apk",
            "split_config.ko.apk",
            "split_config.tvdpi.apk",
        )
    )


def _mode_switch_raw(*, normal_checked: bool, simple_checked: bool) -> str:
    return (
        '<hierarchy rotation="0">'
        f'<node text="일반 모드" resource-id="com.hnlens.simplemode:id/rb_normal" '
        f'checkable="true" checked="{str(normal_checked).lower()}" '
        'bounds="[35,320][445,408]" />'
        f'<node text="간편 모드" resource-id="com.hnlens.simplemode:id/rb_simple" '
        f'checkable="true" checked="{str(simple_checked).lower()}" '
        'bounds="[35,409][445,497]" />'
        '<node text="취소" resource-id="com.hnlens.simplemode:id/tv_cancel" '
        'checkable="false" checked="false" bounds="[202,510][284,575]" />'
        '<node text="확인" resource-id="com.hnlens.simplemode:id/tv_confirm" '
        'checkable="false" checked="false" bounds="[318,510][401,575]" />'
        "</hierarchy>UI hierchary dumped to: /dev/tty\n"
    )


def _permission_raw() -> str:
    return (
        '<hierarchy><node text="항상 허용" bounds="[100,600][380,760]" />'
        "</hierarchy>UI hierchary dumped to: /dev/tty\n"
    )


def _launcher_crash_dialog_raw(
    *,
    title: str = "MIVE Home이(가) 중지됨",
    decoy_text: str | None = None,
    title_resource_id: str = "android:id/alertTitle",
    close_resource_id: str = "android:id/aerr_close",
) -> str:
    decoy = (
        f'<node text="{decoy_text}" resource-id="android:id/message" '
        'package="android" bounds="[64,310][416,350]" />'
        if decoy_text is not None
        else ""
    )
    return (
        '<hierarchy rotation="0">'
        f'<node text="{title}" resource-id="{title_resource_id}" '
        'package="android" bounds="[64,246][416,310]" />'
        f"{decoy}"
        f'<node text="앱 닫기" resource-id="{close_resource_id}" '
        'package="android" bounds="[156,454][322,520]" />'
        "</hierarchy>UI hierchary dumped to: /dev/tty\n"
    )


def _simple_home_raw() -> str:
    return (
        '<hierarchy rotation="0"><node text="간편 홈" '
        'package="com.hnlens.simplemode" bounds="[0,0][480,800]" />'
        "</hierarchy>UI hierchary dumped to: /dev/tty\n"
    )


def test_ui_dump_preserves_raw_output_and_returns_normalized_xml(tmp_path):
    """Catch evidence writers overwriting raw framing or parsing it directly."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    bundle = evidence.EvidenceBundle.create(tmp_path / "out", "20260829T050618Z")
    command = ("exec-out", "uiautomator", "dump", "/dev/tty")
    hierarchy = '<hierarchy><node text="일반 모드" /></hierarchy>'
    raw = hierarchy + "UI hierchary dumped to: /dev/tty\n"
    transport = _ScriptedTransport(models, {command: raw})

    normalized = orchestrator._ui_dump(
        bundle, transport, "SER", "bind", "mode_switch"
    )

    assert normalized == hierarchy
    assert (bundle.directory / "snapshots" / "mode_switch.raw.txt").read_text(
        encoding="utf-8"
    ) == raw
    assert (bundle.directory / "snapshots" / "mode_switch.xml").read_text(
        encoding="utf-8"
    ) == hierarchy
    evidence.verify_evidence_manifest(bundle.directory)


def test_capture_collects_complete_read_only_snapshot_and_durable_state(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    transport = _ScriptedTransport(models, _capture_responses(profile))

    result = orchestrator.capture(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        now=lambda: datetime(2026, 8, 29, 5, 6, 18, tzinfo=timezone.utc),
    )

    bundle = tmp_path / "out" / "20260829T050618Z"
    state = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    assert result == {
        "bundle": "out/20260829T050618Z",
        "current_phase": "BASELINE_CAPTURED",
        "run_id": "20260829T050618Z",
    }
    assert state["capture_complete"] is True
    assert state["current_phase"] == "BASELINE_CAPTURED"
    assert state["completed_phases"] == ["BASELINE_CAPTURED"]
    assert state["final_home_role"] == "com.hnlens.simplemode"
    assert state["old_widget_id"] is None
    assert state["mutations_remaining"] == []
    assert (bundle / "inputs.json").is_file()
    assert (bundle / "verification.txt").is_file()
    assert (bundle / "result.json").is_file()
    assert (bundle / "snapshots" / "package_baseline.txt").is_file()
    assert (bundle / "snapshots" / "appwidget_baseline.txt").is_file()
    assert (bundle / "snapshots" / "ui_baseline.raw.txt").read_text(
        encoding="utf-8"
    ).endswith("UI hierchary dumped to: /dev/tty\n")
    assert (bundle / "snapshots" / "ui_baseline.xml").is_file()
    assert "UI hierchary dumped" not in (
        bundle / "snapshots" / "ui_baseline.xml"
    ).read_text(encoding="utf-8")
    assert (bundle / "screenshots" / "baseline.png").read_bytes().startswith(b"\x89PNG")
    assert (bundle / "evidence_sha256.txt").is_file()
    events = [
        json.loads(line)
        for line in (bundle / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(event["boot_id"] == "boot-1" for event in events)
    assert any(event["device_elapsed_realtime_s"] == 123.45 for event in events)
    assert all(event["logical_command"] for event in events)
    assert all(event["resulting_state"] == "CAPTURING" for event in events)
    forbidden = {"uninstall", "install-multiple", "reboot", "force-stop", "clear", "tap", "swipe"}
    assert not any(forbidden.intersection(call) for call in transport.calls)
    assert all("ODIN2" not in call for call in transport.calls)


def test_capture_transport_exception_records_durable_failure_context(tmp_path):
    """Catch transport exceptions leaving an unexplained partial bundle."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    failing_command = (
        "shell",
        "logcat",
        "-d",
        "-b",
        "crash",
        "-v",
        "threadtime",
    )
    responses = _capture_responses(profile)
    responses[failing_command] = RuntimeError("simulated capture transport failure")
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(RuntimeError, match="simulated capture transport failure"):
        orchestrator.capture(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
        )

    bundle = tmp_path / "out" / "20260829T050618Z"
    state = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    error = json.loads(
        (bundle / "capture_error.json").read_text(encoding="utf-8")
    )
    assert state["capture_complete"] is False
    assert error == {
        "artifact": "snapshots/crash_baseline.txt",
        "command_category": "crash_baseline.txt",
        "error_type": "RuntimeError",
        "logical_command": list(failing_command),
        "message": "simulated capture transport failure",
        "phase": "capture",
        "schema_version": 1,
        "target_serial": "SER",
    }
    evidence.verify_evidence_manifest(bundle)


def test_capture_binary_transport_exception_records_durable_failure_context(
    tmp_path,
):
    """Catch screenshot transport exceptions leaving an unexplained bundle."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    failing_command = ("exec-out", "screencap", "-p")
    responses = _capture_responses(profile)
    responses[failing_command] = RuntimeError("simulated screenshot failure")
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(RuntimeError, match="simulated screenshot failure"):
        orchestrator.capture(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
        )

    bundle = tmp_path / "out" / "20260829T050618Z"
    error = json.loads(
        (bundle / "capture_error.json").read_text(encoding="utf-8")
    )
    assert error["artifact"] == "screenshots/baseline.png"
    assert error["command_category"] == "baseline.png"
    assert error["logical_command"] == list(failing_command)
    assert error["error_type"] == "RuntimeError"
    assert error["message"] == "simulated screenshot failure"
    evidence.verify_evidence_manifest(bundle)


@pytest.mark.parametrize("broken", ["screenshot", "ui"])
def test_incomplete_capture_is_persisted_and_blocks_mutation(tmp_path, broken):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    responses = _capture_responses(profile, screenshot=b"not-png" if broken == "screenshot" else b"\x89PNG\r\n\x1a\n")
    if broken == "ui":
        responses[("exec-out", "uiautomator", "dump", "/dev/tty")] = "ERROR"
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.CaptureIncomplete):
        orchestrator.capture(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["capture_complete"] is False
    assert state["current_phase"] is None
    with pytest.raises(orchestrator.GateFailure):
        orchestrator.require_run_phase(
            tmp_path / "out" / "20260829T050618Z", "BASELINE_CAPTURED"
        )


def test_ui_parser_requires_exact_selector_and_returns_node_center():
    parsers = _load_script("appwidget_stale_provider_parsers")
    xml = (
        '<hierarchy><node text="SimpleClock extra" bounds="[0,0][10,10]" />'
        '<node text="SimpleClock" bounds="[100,200][300,400]" /></hierarchy>'
    )

    assert parsers.find_ui_node(xml, "SimpleClock").center == (200, 300)
    assert parsers.find_ui_node(xml, "simpleclock") is None
    assert parsers.find_ui_node(xml, "Simple") is None


def test_normalize_ui_dump_strips_uiautomator_status_suffix():
    """Catch raw /dev/tty framing being passed to the XML parser."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    hierarchy = (
        '<hierarchy rotation="0"><node text="일반 모드" '
        'resource-id="com.hnlens.simplemode:id/rb_normal" '
        'checked="false" bounds="[35,320][445,408]" /></hierarchy>'
    )
    raw = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
        + hierarchy
        + "UI hierchary dumped to: /dev/tty\n"
    )

    assert parsers.normalize_ui_dump(raw) == hierarchy


def test_find_ui_node_raises_for_malformed_xml_instead_of_returning_none():
    """Catch infrastructure parse failures masquerading as selector misses."""
    parsers = _load_script("appwidget_stale_provider_parsers")

    with pytest.raises(ValueError, match="UI dump XML is malformed"):
        parsers.find_ui_node("<hierarchy><node></hierarchy>", "일반 모드")


def test_ui_parser_finds_exact_resource_id_and_checked_state():
    """Catch mode switching falling back to localized text or adjacent bounds."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    xml = (
        '<hierarchy rotation="0">'
        '<node text="일반 모드" resource-id="com.hnlens.simplemode:id/rb_normal" '
        'checkable="true" checked="false" bounds="[35,320][445,408]" />'
        '<node text="간편 모드" resource-id="com.hnlens.simplemode:id/rb_simple" '
        'checkable="true" checked="true" bounds="[35,409][445,497]" />'
        '<node text="취소" resource-id="com.hnlens.simplemode:id/tv_cancel" '
        'checkable="false" checked="false" bounds="[202,510][284,575]" />'
        '<node text="확인" resource-id="com.hnlens.simplemode:id/tv_confirm" '
        'checkable="false" checked="false" bounds="[318,510][401,575]" />'
        "</hierarchy>"
    )

    normal = parsers.find_ui_node_by_resource_id(
        xml, "com.hnlens.simplemode:id/rb_normal"
    )
    simple = parsers.find_ui_node_by_resource_id(
        xml, "com.hnlens.simplemode:id/rb_simple"
    )
    confirm = parsers.find_ui_node_by_resource_id(
        xml, "com.hnlens.simplemode:id/tv_confirm"
    )

    assert normal.resource_id == "com.hnlens.simplemode:id/rb_normal"
    assert normal.checked is False
    assert normal.center == (240, 364)
    assert simple.checked is True
    assert confirm.center == (359, 542)
    assert parsers.find_ui_node_by_resource_id(
        xml, "com.hnlens.simplemode:id/missing"
    ) is None


def _seed_run(tmp_path, profile, phase="BASELINE_CAPTURED", **updates):
    evidence = _load_script("appwidget_stale_provider_evidence")
    bundle = evidence.EvidenceBundle.create(
        tmp_path / profile["evidence_root"], "20260829T050618Z"
    )
    state = {
        "capture_complete": True,
        "completed_phases": [phase],
        "current_phase": phase,
        "final_home_role": profile["general_home"],
        "mutations_remaining": [],
        "old_widget_id": None,
        "active_boot_id": "boot-1",
        "profile_identity": {
            "fingerprint": profile["fingerprint"],
            "incremental": profile["incremental"],
            "model": profile["model"],
            "serial": "SER",
            "viewport": list(profile["viewport"]),
        },
        "run_id": "20260829T050618Z",
    }
    state.update(updates)
    bundle.write_json("run.json", state)
    bundle.write_json("inputs.json", evidence.verify_inputs(tmp_path, profile))
    bundle.write_json("result.json", {
        "crash_signature_count": 0,
        "diagnosis_status": "SUSPECT",
        "evidence_term": "manual evidence observed",
        "final_home_role": state["final_home_role"],
        "home_rendered": None,
        "launcher_crash_exit_count": 0,
        "launcher_crash_exit_pids": [],
        "launcher_loader_record_count": 0,
        "launcher_loop_basis": [],
        "launcher_loop_observed": False,
        "launcher_process_stable": None,
        "launcher_stale_record_evidence": "INFERRED_ONLY",
        "mutations_remaining": state["mutations_remaining"],
        "precondition_status": "NOT_EVALUATED",
        "provider_registered": True,
        "widget_bound_after": None,
        "widget_bound_before": False,
    })
    snapshots = bundle.directory / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    for name in (
        "crash_baseline.txt",
        "exit_info_baseline.txt",
        "main_log_baseline.txt",
    ):
        (snapshots / name).write_text("", encoding="utf-8")
    evidence.write_evidence_manifest(bundle.directory)
    return bundle


def _identity_responses():
    return {
        ("shell", "getprop", "ro.product.model"): "AT-M140\n",
        ("shell", "getprop", "ro.build.fingerprint"): "FINGERPRINT\n",
        ("shell", "getprop", "ro.build.version.incremental"): "INC\n",
        ("shell", "wm", "size"): "Physical size: 480x800\n",
    }


def _bind_responses(
    profile,
    before_appwidget: str,
    after_appwidget: str,
    *,
    education=False,
    education_before_menu=False,
    drag_tip_after_row=False,
    provider_confirm_transient_null=False,
    preview_variant_text=None,
    include_provider_confirm=True,
    provider_confirm_resource_id=None,
):
    responses = _identity_responses()
    responses = {key: [value, value] for key, value in responses.items()}
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                "com.hnlens.launcher3\n"
            ),
            ("shell", "input", "touchscreen", "swipe", "240", "350", "240", "350", "1200"): (
                ["", ""] if education_before_menu else ""
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                *(
                    [
                        '<hierarchy><node text="확인" '
                        'resource-id="com.hnlens.launcher3:id/edu_close_button" '
                        'bounds="[33,646][447,723]" /></hierarchy>',
                    ]
                    if education_before_menu
                    else []
                ),
                '<hierarchy><node text="위젯" bounds="[10,20][110,120]" /></hierarchy>',
                *(
                    [
                        '<hierarchy><node text="확인" '
                        'resource-id="com.hnlens.launcher3:id/edu_close_button" '
                        'bounds="[33,646][447,723]" /></hierarchy>',
                    ]
                    if education
                    else []
                ),
                '<hierarchy><node text="검색" bounds="[20,30][120,130]" /></hierarchy>',
                '<hierarchy><node text="SimpleClock" bounds="[30,40][130,140]" /></hierarchy>',
                *(
                    [
                        '<hierarchy><node text="길게 터치하여 위젯을 이동하세요." '
                        'resource-id="com.hnlens.launcher3:id/text" '
                        'bounds="[98,332][383,403]" /></hierarchy>',
                    ]
                    if drag_tip_after_row
                    else []
                ),
                (
                    '<hierarchy><node text="SimpleClock" bounds="[40,50][140,150]" />'
                    + (
                        f'<node text="{preview_variant_text}" bounds="[150,50][250,150]" />'
                        if preview_variant_text
                        else ""
                    )
                    + '</hierarchy>'
                ),
                *(
                    ["ERROR: null root node returned by UiTestAutomationBridge."]
                    if provider_confirm_transient_null
                    else []
                ),
                *(
                    [
                        '<hierarchy><node text="OK" '
                        + (
                            f'resource-id="{provider_confirm_resource_id}" '
                            if provider_confirm_resource_id
                            else ""
                        )
                        + 'bounds="[300,700][390,780]" /></hierarchy>'
                    ]
                    if include_provider_confirm
                    else []
                ),
            ],
            ("shell", "input", "tap", "60", "70"): "",
            ("shell", "input", "tap", "240", "684"): "",
            ("shell", "input", "tap", "70", "80"): "",
            ("shell", "input", "text", "SimpleClock"): "",
            ("shell", "input", "tap", "80", "90"): "",
            ("shell", "input", "tap", "240", "367"): "",
            (
                "shell", "input", "touchscreen", "draganddrop",
                "240", "560", "240", "240", "1200",
            ): "",
            ("shell", "input", "tap", "345", "740"): "",
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\npreview",
            ("shell", "dumpsys", "appwidget"): [before_appwidget, after_appwidget],
        }
    )
    return responses


def test_bind_requires_exact_provider_variant_before_drag(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["ui"]["provider_variant_text"] = "3×2"
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(models, _bind_responses(profile, before, after))

    with pytest.raises(orchestrator.GateFailure, match="provider variant"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    assert not any("draganddrop" in call for call in transport.calls)


def test_bind_can_poll_binding_without_provider_confirmation_activity(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["ui"]["provider_confirm_required"] = False
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(
            profile,
            before,
            after,
            include_provider_confirm=False,
        ),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    assert ("shell", "input", "tap", "345", "740") not in transport.calls


def test_bind_can_confirm_provider_by_exact_resource_id(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    confirm_rid = "com.accuweather.android:id/widget_confirm_submit_button"
    profile["ui"]["provider_confirm_resource_id"] = confirm_rid
    profile["ui"]["provider_confirm_text"] = "저장"
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(
            profile,
            before,
            after,
            provider_confirm_resource_id=confirm_rid,
        ),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    assert ("shell", "input", "tap", "345", "740") in transport.calls


def test_bind_retries_transient_incomplete_provider_confirmation_ui(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(
            profile,
            before,
            after,
            provider_confirm_transient_null=True,
        ),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        poll_attempts=2,
        poll_interval_s=0,
    )

    snapshots = tmp_path / "out" / "20260829T050618Z" / "snapshots"
    assert result["current_phase"] == "BOUND_GENERAL"
    assert "null root node" in (
        snapshots / "bind-0001_provider_confirm_attempt_1.raw.txt"
    ).read_text(encoding="utf-8")
    assert "text=\"OK\"" in (
        snapshots / "bind-0001_provider_confirm_attempt_2.xml"
    ).read_text(encoding="utf-8")


def test_bind_can_adopt_one_exact_existing_binding_without_placing_another(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": [39]})
    component = profile["app"]["provider"]
    existing = (
        f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
        f" AppWidgetId{{appWidgetId=39, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "dumpsys", "appwidget"): existing,
        }
    )
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        adopt_existing=True,
    )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert result == {
        "binding_origin": "ADOPTED_EXISTING",
        "current_phase": "BOUND_GENERAL",
        "old_widget_id": 39,
        "run_id": "20260829T050618Z",
    }
    assert state["old_widget_id"] == 39
    assert "widget_binding:39" in state["mutations_remaining"]
    assert not any("draganddrop" in call for call in transport.calls)


def test_bind_uses_selector_gated_drag_and_persists_exact_binding(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    responses = _bind_responses(profile, before, after)
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["current_phase"] == "BOUND_GENERAL"
    assert state["old_widget_id"] == 17
    assert state["current_phase"] == "BOUND_GENERAL"
    assert "widget_binding:17" in state["mutations_remaining"]
    assert "widget_binding:unknown" not in state["mutations_remaining"]
    assert (
        tmp_path / "out" / "20260829T050618Z" / "snapshots"
        / "bind-0001_appwidget_before.txt"
    ).read_text(encoding="utf-8") == before
    assert (
        "shell", "input", "touchscreen", "draganddrop",
        "240", "560", "240", "240", "1200",
    ) in transport.calls
    assert all("ODIN2" not in call for call in transport.calls)


def test_bind_waits_for_general_home_three_way_after_mode_switch(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        baseline={"binding_ids": []},
        final_home_role=profile["simple_home"],
    )
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    responses = _bind_responses(profile, before, after)
    normal_ui = responses[("exec-out", "uiautomator", "dump", "/dev/tty")]
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "359", "542"): "",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                '<hierarchy><node package="com.hnlens.launcher3" text="Launcher" '
                'bounds="[0,0][480,800]" /></hierarchy>',
                *normal_ui,
            ],
        }
    )
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    activity_call = ("shell", "dumpsys", "activity", "activities")
    long_press = (
        "shell", "input", "touchscreen", "swipe", "240", "350", "240", "350", "1200"
    )
    assert transport.calls.index(activity_call) < transport.calls.index(long_press)


def test_bind_dismisses_exact_first_run_widget_education_before_search(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(profile, before, after, education=True),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    education_tap = ("shell", "input", "tap", "240", "684")
    search_tap = ("shell", "input", "tap", "70", "80")
    assert transport.calls.index(education_tap) < transport.calls.index(search_tap)


def test_bind_retry_dismisses_existing_widget_education_before_home_menu(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(
            profile,
            before,
            after,
            education_before_menu=True,
        ),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    long_press = (
        "shell", "input", "touchscreen", "swipe", "240", "350", "240", "350", "1200"
    )
    assert transport.calls.count(long_press) == 2
    education_tap = ("shell", "input", "tap", "240", "684")
    widget_menu_tap = ("shell", "input", "tap", "60", "70")
    assert transport.calls.index(education_tap) < transport.calls.index(widget_menu_tap)


def test_bind_dismisses_exact_widget_drag_tip_before_preview(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    before = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    after = (
        before
        + f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models,
        _bind_responses(
            profile,
            before,
            after,
            drag_tip_after_row=True,
        ),
    )

    result = orchestrator.bind(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert result["current_phase"] == "BOUND_GENERAL"
    tip_tap = ("shell", "input", "tap", "240", "367")
    drag = (
        "shell", "input", "touchscreen", "draganddrop",
        "240", "560", "240", "240", "1200",
    )
    assert transport.calls.index(tip_tap) < transport.calls.index(drag)


def test_bind_retry_rejects_binding_that_existed_before_this_attempt(tmp_path):
    """A partial placement from a prior attempt is not new evidence on retry."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile, baseline={"binding_ids": []})
    component = profile["app"]["provider"]
    existing = (
        f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
        f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    transport = _ScriptedTransport(
        models, _bind_responses(profile, existing, existing)
    )

    with pytest.raises(orchestrator.GateFailure, match="new exact provider"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
            poll_attempts=1,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert "widget_binding:unknown" in state["mutations_remaining"]
    assert state["widget_binding_attempt_baseline_ids"] == [17]

    with pytest.raises(orchestrator.GateFailure, match="new exact provider"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(
                models, _bind_responses(profile, existing, existing)
            ),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
            poll_attempts=1,
        )
    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["attempt_counters"]["bind"] == 2
    bind_attempts = [item for item in state["attempts"] if item["kind"] == "bind"]
    assert [item["status"] for item in bind_attempts] == ["ERROR", "ERROR"]
    assert all("new exact provider" in item["primary_error"] for item in bind_attempts)
    snapshots = tmp_path / "out" / "20260829T050618Z" / "snapshots"
    assert (snapshots / "bind-0001_appwidget_before.txt").is_file()
    assert (snapshots / "bind-0002_appwidget_before.txt").is_file()
    assert (snapshots / "bind-0001_appwidget_poll_1.txt").is_file()
    assert (snapshots / "bind-0002_appwidget_poll_1.txt").is_file()

    package = profile["app"]["package"]
    restore_responses = _identity_responses()
    restore_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                '<hierarchy><node text="간편모드" bounds="[100,200][300,300]" /></hierarchy>',
                '<hierarchy><node text="간편모드" bounds="[0,0][480,800]" /></hierarchy>',
            ],
            ("shell", "input", "tap", "200", "250"): "",
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nrestore",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): "",
            ("shell", "dumpsys", "appwidget"): existing,
            ("shell", "dumpsys", "package", package): (
                "appId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=_ScriptedTransport(models, restore_responses),
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )
    recovered_state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert restored["mutations_remaining"] == ["widget_binding:17"]
    assert recovered_state["run_complete"] is False


def test_bind_selection_rejects_a_preexisting_valid_widget_id():
    """Catch a failed drag being accepted because an older binding already exists."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    existing = models.WidgetBinding(
        widget_id=17,
        provider_component="com.winson.simpleclock/.SimpleClockWidgetProvider",
        host_package="com.hnlens.launcher3",
        remote_views_present=True,
    )
    state = models.AppWidgetState(
        provider_registered=True,
        provider_uid=10234,
        bindings=(existing,),
    )

    assert orchestrator._select_new_binding(state, {17}) is None
    assert orchestrator._select_new_binding(state, set()) == existing


def test_bind_fails_before_transport_without_execute_or_from_unknown_home(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile)
    transport = _ScriptedTransport(models, {})

    with pytest.raises(orchestrator.GateFailure):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=False,
        )
    assert transport.calls == []


def test_existing_run_is_rebound_to_original_serial_and_profile_before_transport(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile)
    transport = _ScriptedTransport(models, {}, serial="OTHER")

    with pytest.raises(orchestrator.GateFailure, match="run identity"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="OTHER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )
    assert transport.calls == []


def test_resume_rejects_copied_run_id_before_transport(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(tmp_path, profile)
    state = json.loads((bundle.directory / "run.json").read_text(encoding="utf-8"))
    state["run_id"] = "20260829T050619Z"
    bundle.write_json("run.json", state)
    evidence.write_evidence_manifest(bundle.directory)
    transport = _ScriptedTransport(models, {})

    with pytest.raises(orchestrator.GateFailure, match="run ID"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )
    assert transport.calls == []


def test_resume_rejects_tampered_bundle_manifest_without_reblessing(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(tmp_path, profile)
    manifest_before = (bundle.directory / "evidence_sha256.txt").read_bytes()
    (bundle.directory / "result.json").write_text("{}\n", encoding="utf-8")
    transport = _ScriptedTransport(models, {})

    with pytest.raises(orchestrator.GateFailure, match="integrity"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )
    assert transport.calls == []
    assert (bundle.directory / "evidence_sha256.txt").read_bytes() == manifest_before


def test_phase_failure_does_not_rebless_tampering_after_precheck(
    tmp_path, monkeypatch
):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(tmp_path, profile)
    manifest_at_tamper = []

    def tamper_after_precheck(*_args, **_kwargs):
        manifest_at_tamper.append(
            (bundle.directory / "evidence_sha256.txt").read_bytes()
        )
        (bundle.directory / "result.json").write_text("{}\n", encoding="utf-8")
        raise orchestrator.GateFailure("simulated post-precheck failure")

    monkeypatch.setattr(orchestrator, "_ensure_home_role", tamper_after_precheck)
    with pytest.raises(orchestrator.GateFailure, match="post-precheck failure") as raised:
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, _identity_responses()),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    assert manifest_at_tamper
    assert (bundle.directory / "evidence_sha256.txt").read_bytes() == manifest_at_tamper[0]
    assert isinstance(raised.value.attempt_record_error, evidence.EvidenceInputError)
    assert isinstance(raised.value.manifest_error, evidence.EvidenceInputError)


def test_bind_failure_persists_general_home_mutation_before_widget_actions(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "input", "touchscreen", "swipe", "240", "350", "240", "350", "1200"): "",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="다른 메뉴" bounds="[0,0][100,100]" /></hierarchy>'
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="selector"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["current_phase"] == "BASELINE_CAPTURED"
    assert state["final_home_role"] == profile["general_home"]
    assert "home_role:general" in state["mutations_remaining"]

    package = profile["app"]["package"]
    restore_responses = _identity_responses()
    restore_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                '<hierarchy><node text="간편모드" bounds="[100,200][300,300]" /></hierarchy>',
                '<hierarchy><node text="간편모드" bounds="[0,0][480,800]" /></hierarchy>',
            ],
            ("shell", "input", "tap", "200", "250"): "",
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nrestore",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): "",
            ("shell", "dumpsys", "appwidget"): "Providers:\nWidgets:\n",
            ("shell", "dumpsys", "package", package): (
                "appId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=_ScriptedTransport(models, restore_responses),
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )
    assert restored["current_phase"] == "RESTORED_SAFE"
    assert restored["mutations_remaining"] == []


def test_keyboard_interrupt_checkpoints_attempt_error_and_manifest(
    tmp_path, monkeypatch
):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(tmp_path, profile)

    def interrupted(*_args, **_kwargs):
        raise KeyboardInterrupt("operator interrupt")

    monkeypatch.setattr(orchestrator, "_ensure_home_role", interrupted)
    with pytest.raises(KeyboardInterrupt, match="operator interrupt"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, _identity_responses()),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    run_dir = tmp_path / "out" / "20260829T050618Z"
    evidence.verify_evidence_manifest(run_dir)
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert state["attempts"][-1]["attempt_id"] == "bind-0001"
    assert state["attempts"][-1]["status"] == "ERROR"
    assert state["attempts"][-1]["primary_error"] == (
        "KeyboardInterrupt: operator interrupt"
    )
    assert "bind" not in state["active_attempts"]


def test_new_attempt_blocks_after_reconciling_stale_active_attempt(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        active_attempts={"bind": "bind-0001"},
        attempt_counters={"bind": 1},
        attempts=[
            {"attempt_id": "bind-0001", "kind": "bind", "status": "RESERVED"}
        ],
    )
    state = json.loads((bundle.directory / "run.json").read_text(encoding="utf-8"))

    with pytest.raises(orchestrator.GateFailure, match="restore reconciliation"):
        orchestrator._reserve_attempt(bundle, state, "bind")

    recovered = json.loads(
        (bundle.directory / "run.json").read_text(encoding="utf-8")
    )
    assert recovered["attempt_counters"]["bind"] == 1
    assert recovered["attempts"][-1]["status"] == "INTERRUPTED"
    assert recovered["attempts"][-1]["interruption_reason"] == (
        "stale active attempt found before bind"
    )
    assert recovered["active_attempts"] == {}
    assert recovered["attempt_reconciliation_required"] == ["bind-0001"]
    with pytest.raises(orchestrator.GateFailure, match="restore reconciliation"):
        orchestrator._reserve_attempt(bundle, recovered, "bind")
    blocked_again = json.loads(
        (bundle.directory / "run.json").read_text(encoding="utf-8")
    )
    assert blocked_again["attempt_counters"]["bind"] == 1
    assert len(blocked_again["attempts"]) == 1
    restore_id = orchestrator._reserve_attempt(bundle, blocked_again, "restore")
    reconciled = json.loads(
        (bundle.directory / "run.json").read_text(encoding="utf-8")
    )
    assert restore_id == "restore-0001"
    assert reconciled["attempts"][0]["reconciliation_attempt"] == "restore-0001"
    assert "reconciled_by" not in reconciled["attempts"][0]
    assert reconciled["attempt_reconciliation_required"] == ["bind-0001"]
    assert reconciled["active_attempts"] == {"restore": "restore-0001"}
    orchestrator._complete_attempt_reconciliation(reconciled, "restore-0001")
    assert reconciled["attempts"][0]["reconciled_by"] == "restore-0001"
    assert reconciled["attempt_reconciliation_required"] == []
    evidence.verify_evidence_manifest(bundle.directory)


def test_restore_reservation_reconciles_all_stale_attempts(tmp_path):
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        active_attempts={"arm": "arm-0001"},
        attempt_counters={"arm": 1},
        attempts=[
            {"attempt_id": "arm-0001", "kind": "arm", "status": "RESERVED"}
        ],
    )
    state = json.loads((bundle.directory / "run.json").read_text(encoding="utf-8"))

    attempt_id = orchestrator._reserve_attempt(bundle, state, "restore")

    recovered = json.loads(
        (bundle.directory / "run.json").read_text(encoding="utf-8")
    )
    assert attempt_id == "restore-0001"
    assert recovered["attempts"][0] == {
        "attempt_id": "arm-0001",
        "kind": "arm",
        "status": "INTERRUPTED",
        "interruption_reason": "stale active attempt found before restore",
        "reconciliation_attempt": "restore-0001",
    }
    assert recovered["attempts"][1] == {
        "attempt_id": "restore-0001",
        "kind": "restore",
        "status": "RESERVED",
    }
    assert recovered["attempt_reconciliation_required"] == ["arm-0001"]
    assert recovered["active_attempts"] == {"restore": "restore-0001"}
    evidence.verify_evidence_manifest(bundle.directory)


def test_bind_mode_switch_poll_failure_persists_unverified_home_intent(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["mode_ui"] = {
        "switch_to_general_resource_id": "com.hnlens.simplemode:id/rb_normal",
        "switch_to_simple_resource_id": "com.hnlens.simplemode:id/rb_simple",
        "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
        "always_allow_text": "",
    }
    _seed_run(tmp_path, profile)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
            ],
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "359", "542"): "",
        }
    )

    with pytest.raises(orchestrator.GateFailure, match="target HOME role"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, responses),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
            poll_attempts=1,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert "home_role:unverified" in state["mutations_remaining"]
    result = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["mutations_remaining"] == state["mutations_remaining"]
    assert result["final_home_role"] == state["final_home_role"]


def test_bind_missing_mode_resource_id_does_not_record_mutation_intent(tmp_path):
    """Catch non-mutating selector failures contaminating the mutation ledger."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["mode_ui"] = {
        "switch_to_general_resource_id": "com.hnlens.simplemode:id/rb_normal",
        "switch_to_simple_resource_id": "com.hnlens.simplemode:id/rb_simple",
        "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
        "always_allow_text": "항상 허용",
    }
    _seed_run(tmp_path, profile)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="확인" '
                'resource-id="com.hnlens.simplemode:id/tv_confirm" '
                'checked="false" bounds="[318,510][401,575]" />'
                "</hierarchy>UI hierchary dumped to: /dev/tty\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="resource ID"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["mutations_remaining"] == []
    assert not any("tap" in call for call in transport.calls)


def test_arm_uninstall_reinstall_verifies_inputs_then_establishes_stale_state(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["widget_binding:17", "home_role:general"],
    )
    component = profile["app"]["provider"]
    package = profile["app"]["package"]
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            ("uninstall", package): "Success\n",
            (
                "install-multiple",
                str((tmp_path / "source" / "simpleclock_apk" / "base.apk").resolve()),
                str((tmp_path / "source" / "simpleclock_apk" / "split_config.ko.apk").resolve()),
                str((tmp_path / "source" / "simpleclock_apk" / "split_config.tvdpi.apk").resolve()),
            ): "Success\n",
            ("shell", "dumpsys", "package", package): (
                "userId=20234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.arm(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        lifecycle="uninstall-reinstall",
        execute=True,
    )

    run_dir = tmp_path / "out" / "20260829T050618Z"
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["current_phase"] == "STALE_ARMED"
    assert state["current_phase"] == "STALE_ARMED"
    assert state["new_provider_uid"] == 20234
    assert state["old_widget_id"] == 17
    assert verdict["precondition_status"] == "PASS"
    assert verdict["widget_bound_before"] is True
    assert verdict["widget_bound_after"] is False
    assert verdict["provider_registered"] is True
    assert "stale_launcher_record:17" in state["mutations_remaining"]
    assert state["attempts"][-1]["attempt_id"] == "arm-0001"
    assert state["attempts"][-1]["status"] == "COMPLETED"
    assert (run_dir / "snapshots" / "package_after_arm-0001.txt").is_file()
    assert (run_dir / "snapshots" / "appwidget_after_arm-0001.txt").is_file()
    assert not any("ODIN2" in call for call in transport.calls)


def test_arm_clean_control_removes_binding_before_package_lifecycle(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["ui"]["widget_remove_drag"] = (297, 187, 150, 70, 1200)
    profile["ui"]["widget_remove_selector"] = "36시간 예보"
    profile["ui"]["widget_remove_resource_id"] = (
        "com.hnlens.launcher3:id/widget_resize_frame"
    )
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["general_home"],
        mutations_remaining=["widget_binding:17", "home_role:general"],
    )
    component = profile["app"]["provider"]
    package = profile["app"]["package"]
    with_binding = (
        f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
        f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    without_binding = f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
    reinstalled_without_binding = (
        f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
    )
    install_key = (
        "install-multiple",
        str((tmp_path / "source" / "simpleclock_apk" / "base.apk").resolve()),
        str((tmp_path / "source" / "simpleclock_apk" / "split_config.ko.apk").resolve()),
        str((tmp_path / "source" / "simpleclock_apk" / "split_config.tvdpi.apk").resolve()),
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "dumpsys", "appwidget"): [
                with_binding,
                without_binding,
                reinstalled_without_binding,
            ],
            ("shell", "input", "keyevent", "KEYCODE_HOME"): "",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            (
                "shell", "input", "touchscreen", "draganddrop",
                "297", "187", "150", "70", "1200",
            ): "",
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                (
                    '<hierarchy><node resource-id="com.hnlens.launcher3:id/widget_resize_frame" '
                    'bounds="[126,48][468,326]" /></hierarchy>'
                ),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                _mode_switch_raw(normal_checked=False, simple_checked=True),
            ],
            ("shell", "input", "tap", "240", "453"): "",
            ("shell", "input", "tap", "359", "542"): "",
            ("uninstall", package): "Success\n",
            install_key: "Success\n",
            ("shell", "dumpsys", "package", package): (
                "userId=20234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.arm(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        lifecycle="remove-widget-uninstall-reinstall",
        execute=True,
    )

    run_dir = tmp_path / "out" / "20260829T050618Z"
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result == {
        "current_phase": "CLEAN_CONTROL_ARMED",
        "precondition_status": "CLEAN_CONTROL_READY",
        "run_id": "20260829T050618Z",
    }
    assert state["current_phase"] == "CLEAN_CONTROL_ARMED"
    assert state["control_kind"] == "WIDGET_REMOVED_BEFORE_LIFECYCLE"
    assert "widget_binding:17" not in state["mutations_remaining"]
    assert "stale_launcher_record:17" not in state["mutations_remaining"]
    assert verdict["precondition_status"] == "CLEAN_CONTROL_READY"
    assert verdict["widget_removed_before_lifecycle"] is True
    assert verdict["widget_bound_before"] is True
    assert verdict["widget_bound_after"] is False
    remove_index = transport.calls.index(
        ("shell", "input", "touchscreen", "draganddrop", "297", "187", "150", "70", "1200")
    )
    normalize_index = transport.calls.index(
        ("shell", "input", "keyevent", "KEYCODE_HOME")
    )
    uninstall_index = transport.calls.index(("uninstall", package))
    assert normalize_index < remove_index
    assert remove_index < uninstall_index


def test_widget_removal_selector_accepts_resize_frame_or_exact_description():
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    rid = "com.hnlens.launcher3:id/widget_resize_frame"
    selector = "36시간 예보"
    resize = (
        f'<hierarchy><node resource-id="{rid}" bounds="[134,56][460,318]" />'
        "</hierarchy>"
    )
    normal = (
        '<hierarchy><node content-desc="36시간 예보" '
        'bounds="[126,48][468,326]" /></hierarchy>'
    )

    assert orchestrator.find_widget_removal_node(
        resize, resource_id=rid, selector=selector
    ).bounds == (134, 56, 460, 318)
    assert orchestrator.find_widget_removal_node(
        normal, resource_id=rid, selector=selector
    ).bounds == (126, 48, 468, 326)


def test_arm_clean_control_blocks_uninstall_when_widget_binding_remains(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["general_home"],
        mutations_remaining=["widget_binding:17", "home_role:general"],
    )
    component = profile["app"]["provider"]
    package = profile["app"]["package"]
    with_binding = (
        f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
        f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
        f"provider={component}, views=android.widget.RemoteViews}}\n"
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "input", "keyevent", "KEYCODE_HOME"): "",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("shell", "dumpsys", "appwidget"): [with_binding, with_binding],
            (
                "shell", "input", "touchscreen", "draganddrop",
                "240", "240", "150", "70", "1200",
            ): "",
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="widget removal did not remove"):
        orchestrator.arm(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            lifecycle="remove-widget-uninstall-reinstall",
            execute=True,
            poll_attempts=1,
        )

    assert ("uninstall", package) not in transport.calls


def test_arm_rejects_input_mismatch_before_any_device_call(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
    )
    (tmp_path / "source" / "simpleclock_apk" / "base.apk").write_bytes(b"tampered")
    transport = _ScriptedTransport(models, {})

    with pytest.raises(evidence.EvidenceInputError):
        orchestrator.arm(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            lifecycle="uninstall-reinstall",
            execute=True,
        )
    assert transport.calls == []


def test_arm_install_failure_persists_package_missing_ledger(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["widget_binding:17", "home_role:general"],
    )
    package = profile["app"]["package"]
    install_key = (
        "install-multiple",
        str((tmp_path / "source" / "simpleclock_apk" / "base.apk").resolve()),
        str((tmp_path / "source" / "simpleclock_apk" / "split_config.ko.apk").resolve()),
        str((tmp_path / "source" / "simpleclock_apk" / "split_config.tvdpi.apk").resolve()),
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            ("uninstall", package): "Success\n",
            install_key: models.CommandResult(
                ("adb", "-s", "SER", *install_key), 1, "Failure\n", "install failed"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="install_verified_splits"):
        orchestrator.arm(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            lifecycle="uninstall-reinstall",
            execute=True,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["current_phase"] == "SAFE_SIMPLE"
    assert "package:missing" in state["mutations_remaining"]
    manifest = tmp_path / "out" / "20260829T050618Z" / "evidence_sha256.txt"
    expected = hashlib.sha256(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_bytes()
    ).hexdigest()
    assert f"{expected}  run.json" in manifest.read_text(encoding="utf-8")

    blocked_responses = _identity_responses()
    blocked_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            ("shell", "dumpsys", "package", package): "",
        }
    )
    blocked_transport = _ScriptedTransport(models, blocked_responses)
    with pytest.raises(orchestrator.GateFailure, match="--recover-package"):
        orchestrator.restore(
            repo_root=tmp_path,
            profile=profile,
            transport=blocked_transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )
    assert install_key not in blocked_transport.calls

    restore_responses = _identity_responses()
    restore_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            install_key: "Success\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="간편모드" bounds="[0,0][480,800]" /></hierarchy>'
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nrestore",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): "",
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={profile['app']['provider']}}}\nWidgets:\n"
            ),
            ("shell", "dumpsys", "package", package): [
                "",
                (
                    "appId=20234\nversionCode=216\nversionName=2.1.6\n"
                    "signatures=PackageSignatures{signatures:[498de32a]}\n"
                    "stopped=false notLaunched=false\n"
                ),
            ],
        }
    )
    restored_transport = _ScriptedTransport(models, restore_responses)
    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=restored_transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        recover_package=True,
    )
    recovered_state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert install_key in restored_transport.calls
    assert restored["current_phase"] == "RESTORED_SAFE"
    assert "package:missing" not in recovered_state["mutations_remaining"]
    assert "package_identity:unverified" not in recovered_state["mutations_remaining"]
    assert recovered_state["attempt_counters"]["restore"] == 2
    restore_attempts = [
        item for item in recovered_state["attempts"] if item["kind"] == "restore"
    ]
    assert [item["status"] for item in restore_attempts] == ["ERROR", "COMPLETED"]
    snapshots = tmp_path / "out" / "20260829T050618Z" / "snapshots"
    assert (snapshots / "package_recovery_probe_restore-0001.txt").is_file()
    assert (snapshots / "package_recovery_probe_restore-0002.txt").is_file()
    assert (
        tmp_path / "out" / "20260829T050618Z" / "screenshots"
        / "restore-0002.png"
    ).is_file()


def test_arm_uninstall_response_failure_keeps_package_state_unverified(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["widget_binding:17"],
    )
    package = profile["app"]["package"]
    uninstall_key = ("uninstall", package)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            uninstall_key: models.CommandResult(
                ("adb", "-s", "SER", *uninstall_key),
                1,
                "",
                "transport interrupted",
            ),
        }
    )

    with pytest.raises(orchestrator.GateFailure, match="uninstall_package"):
        orchestrator.arm(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, responses),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            lifecycle="uninstall-reinstall",
            execute=True,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["current_phase"] == "SAFE_SIMPLE"
    assert "package:state-unverified" in state["mutations_remaining"]
    assert state["attempts"][-1]["attempt_id"] == "arm-0001"
    assert state["attempts"][-1]["status"] == "ERROR"


def test_restore_reconciles_ambiguous_install_success_without_reinstall(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="SAFE_SIMPLE",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL", "SAFE_SIMPLE"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["stale_launcher_record:17", "package:missing"],
        attempt_counters={"arm": 1},
        attempts=[
            {
                "attempt_id": "arm-0001",
                "kind": "arm",
                "status": "INTERRUPTED",
                "interruption_reason": "stale active attempt found before restore",
            }
        ],
        active_attempts={},
        attempt_reconciliation_required=["arm-0001"],
    )
    package = profile["app"]["package"]
    exact_package = (
        "appId=20234\nversionCode=216\nversionName=2.1.6\n"
        "signatures=PackageSignatures{signatures:[498de32a]}\n"
        "stopped=false notLaunched=false\n"
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['simple_home']}\n"
            ),
            ("shell", "dumpsys", "package", package): [exact_package, exact_package],
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="간편모드" bounds="[0,0][480,800]" /></hierarchy>'
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nrestore",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): "",
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={profile['app']['provider']}}}\nWidgets:\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert restored["current_phase"] == "RESTORED_SAFE"
    assert "package:missing" not in restored["mutations_remaining"]
    assert not any(call and call[0] == "install-multiple" for call in transport.calls)
    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["attempt_reconciliation_required"] == []
    assert state["attempts"][0]["reconciliation_attempt"] == "restore-0001"
    assert state["attempts"][0]["reconciled_by"] == "restore-0001"


@pytest.mark.parametrize(
    "views_value",
    ["android.widget.RemoteViews", "null"],
    ids=["remote-views-present", "remote-views-null"],
)
def test_developer_lifecycle_retained_widget_id_is_precondition_fail(
    tmp_path, views_value
):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["widget_binding:17"],
    )
    package = profile["app"]["package"]
    component = profile["app"]["provider"]
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "pm", "clear", package): "Success\n",
            ("shell", "am", "force-stop", package): "",
            ("reboot",): "",
            ("shell", "getprop", "sys.boot_completed"): "1\n",
            ("shell", "dumpsys", "package", package): (
                "userId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=true notLaunched=true\n"
            ),
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=10234 cmp={component}}}\nWidgets:\n"
                f" AppWidgetId{{appWidgetId=17, hostId=HostId{{pkg={profile['launcher_package']}}}, "
                f"provider={component}, views={views_value}}}\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    result = orchestrator.arm(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        lifecycle="clear-force-stop-reboot",
        execute=True,
    )

    run_dir = tmp_path / "out" / "20260829T050618Z"
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["current_phase"] == "BOUND_GENERAL"
    assert result["precondition_status"] == "FAIL"
    assert state["current_phase"] == "BOUND_GENERAL"
    assert verdict["evidence_term"] == "runtime precondition FAIL"
    assert verdict["widget_bound_after"] is True
    assert "widget_binding:17" in state["mutations_remaining"]
    with pytest.raises(orchestrator.GateFailure):
        orchestrator.require_run_phase(run_dir, "STALE_ARMED")


def test_trigger_classifier_requires_all_six_fixed_conditions():
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")

    fixed = orchestrator.classify_trigger(
        precondition_status="PASS",
        home_rendered=True,
        launcher_process_stable=True,
        crash_signature_count=0,
        launcher_stale_record_evidence="LOADER_LOG",
        safe_placeholder_or_cleanup=True,
        normal_widget_update=True,
    )
    assert fixed["phase"] == "TRIGGERED_FIXED"
    assert fixed["evidence_term"] == "runtime PASS"

    for missing in ("home_rendered", "launcher_process_stable"):
        values = {
            "precondition_status": "PASS",
            "home_rendered": True,
            "launcher_process_stable": True,
            "crash_signature_count": 0,
            "launcher_stale_record_evidence": "LOADER_LOG",
            "safe_placeholder_or_cleanup": True,
            "normal_widget_update": True,
        }
        values[missing] = False
        with pytest.raises(orchestrator.GateFailure):
            orchestrator.classify_trigger(**values)

    for missing in ("safe_placeholder_or_cleanup", "normal_widget_update"):
        values = {
            "precondition_status": "PASS",
            "home_rendered": True,
            "launcher_process_stable": True,
            "crash_signature_count": 0,
            "launcher_stale_record_evidence": "LOADER_LOG",
            "safe_placeholder_or_cleanup": True,
            "normal_widget_update": True,
        }
        values[missing] = False
        observed = orchestrator.classify_trigger(**values)
        assert observed == {
            "diagnosis_status": "OBSERVED",
            "evidence_term": "manual evidence observed",
            "phase": "TRIGGERED_STALE_NO_BUG",
            "stale_outcome": "NO_TRIGGER_OBSERVED",
        }

    inferred_only = orchestrator.classify_trigger(
        precondition_status="PASS",
        home_rendered=True,
        launcher_process_stable=True,
        crash_signature_count=0,
        launcher_stale_record_evidence="INFERRED_ONLY",
        safe_placeholder_or_cleanup=False,
        normal_widget_update=False,
    )
    assert inferred_only["phase"] == "TRIGGERED_STALE_NO_BUG"
    assert inferred_only["stale_outcome"] == "NO_TRIGGER_OBSERVED"

    with pytest.raises(orchestrator.GateFailure):
        orchestrator.classify_trigger(
            precondition_status="FAIL",
            home_rendered=True,
            launcher_process_stable=True,
            crash_signature_count=0,
            launcher_stale_record_evidence="LOADER_LOG",
            safe_placeholder_or_cleanup=True,
            normal_widget_update=True,
        )


def test_phase_crash_delta_ignores_baseline_and_includes_exit_info():
    """Catch whole-buffer crash reuse and omission of exit-info-only crashes."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    old = (
        "FATAL EXCEPTION: main\n"
        " at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185\n"
        " at com.android.launcher3.widget.PendingAppWidgetHostView.java:88\n"
    )
    new = old.replace("main", "main-new", 1)

    assert orchestrator._phase_crash_signature_count(
        current_crash=old,
        baseline_crash=old,
        current_exit_info="",
        baseline_exit_info="",
        same_boot=True,
    ) == 0
    assert orchestrator._phase_crash_signature_count(
        current_crash=old,
        baseline_crash=old,
        current_exit_info=new,
        baseline_exit_info="",
        same_boot=True,
    ) == 1


def test_launcher_crash_exit_delta_ignores_record_renumbering():
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    old = """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:18:52.665 pid=22527 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
"""
    current = """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:19:23.986 pid=23363 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
ApplicationExitInfo #1:
  timestamp=2026-09-01 15:18:52.665 pid=22527 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
"""

    exits = orchestrator._phase_launcher_crash_exits(
        current_exit_info=current,
        baseline_exit_info=old,
        launcher_package="com.hnlens.launcher3",
        same_boot=True,
    )

    assert [item.pid for item in exits] == [23363]


@pytest.mark.parametrize(
    ("signature_count", "crash_exit_count", "observed", "basis"),
    [
        (1, 1, False, []),
        (2, 1, True, ["BUG27084_SIGNATURES"]),
        (1, 2, True, ["LAUNCHER_APP_CRASH_EXITS"]),
        (
            2,
            2,
            True,
            ["BUG27084_SIGNATURES", "LAUNCHER_APP_CRASH_EXITS"],
        ),
    ],
)
def test_loop_evidence_requires_repeated_events(
    signature_count, crash_exit_count, observed, basis
):
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")

    assert orchestrator._classify_loop_evidence(
        crash_signature_count=signature_count,
        launcher_crash_exit_count=crash_exit_count,
    ) == (observed, basis)


def test_loader_delta_is_scoped_to_old_widget_id_and_baseline():
    """Catch stale evidence borrowed from another widget or an earlier phase."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    old_line = "Widget provider not found for id=17, delaying widget query\n"

    assert not orchestrator._has_new_loader_record(
        "Widget provider not found for id=18, delaying widget query\n",
        "",
        old_widget_id=17,
        same_boot=True,
    )
    assert not orchestrator._has_new_loader_record(
        old_line,
        old_line,
        old_widget_id=17,
        same_boot=True,
    )
    assert orchestrator._has_new_loader_record(
        old_line,
        "",
        old_widget_id=17,
        same_boot=True,
    )
    assert orchestrator._new_loader_record_count(
        old_line + old_line,
        old_line,
        old_widget_id=17,
        same_boot=True,
    ) == 1


@pytest.mark.parametrize(
    ("crash_count", "phase", "evidence_term", "control_outcome"),
    [
        (0, "TRIGGERED_CONTROL_NO_BUG", "manual evidence observed", "NO_TRIGGER_OBSERVED"),
        (1, "TRIGGERED_CONTROL_BUG", "BUG-GAP observed", "BUG_OBSERVED"),
    ],
)
def test_clean_control_classifier_never_reports_runtime_pass(
    crash_count, phase, evidence_term, control_outcome
):
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")

    result = orchestrator.classify_clean_control(
        home_rendered=True,
        launcher_process_stable=True,
        crash_signature_count=crash_count,
    )

    assert result == {
        "control_outcome": control_outcome,
        "diagnosis_status": "OBSERVED",
        "evidence_term": evidence_term,
        "phase": phase,
    }
    assert result["evidence_term"] != "runtime PASS"


def test_trigger_clean_control_observes_no_bug_without_stale_pass(tmp_path, monkeypatch):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    evidence = _load_script("appwidget_stale_provider_evidence")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="CLEAN_CONTROL_ARMED",
        old_widget_id=17,
        completed_phases=[
            "BASELINE_CAPTURED",
            "BOUND_GENERAL",
            "SAFE_SIMPLE",
            "CLEAN_CONTROL_ARMED",
        ],
        final_home_role=profile["simple_home"],
        mutations_remaining=[],
        precondition_status="CLEAN_CONTROL_READY",
        control_kind="WIDGET_REMOVED_BEFORE_LIFECYCLE",
    )
    run_dir = tmp_path / "out" / "20260829T050618Z"
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    verdict.update(
        {
            "precondition_status": "CLEAN_CONTROL_READY",
            "control_precondition_status": "PASS",
        }
    )
    (run_dir / "result.json").write_text(json.dumps(verdict), encoding="utf-8")
    evidence.write_evidence_manifest(run_dir)
    component = profile["app"]["provider"]
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                '<hierarchy><node package="com.hnlens.launcher3" text="Launcher" '
                'bounds="[0,0][480,800]" /></hierarchy>',
            ],
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "359", "542"): "",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\ncontrol",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): ["", ""],
            ("shell", "logcat", "-d", "-v", "threadtime"): ["", ""],
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): ["", ""],
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): ["boot-1\n", "boot-1\n"],
            ("shell", "pidof", profile["launcher_package"]): ["123\n", "123\n"],
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)
    slept = []
    monkeypatch.setattr(
        orchestrator, "_sleep", lambda seconds: slept.append(seconds), raising=False
    )

    triggered = orchestrator.trigger(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    assert triggered == {
        "current_phase": "TRIGGERED_CONTROL_NO_BUG",
        "evidence_term": "manual evidence observed",
        "run_id": "20260829T050618Z",
    }
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert verdict["control_outcome"] == "NO_TRIGGER_OBSERVED"
    assert verdict["precondition_status"] == "CLEAN_CONTROL_READY"
    assert verdict["launcher_stale_record_evidence"] == "NOT_APPLICABLE"
    assert verdict["evidence_term"] == "manual evidence observed"
    assert verdict["launcher_stability_window_s"] == 30.0
    assert verdict["launcher_crash_exit_count"] == 0
    assert verdict["launcher_crash_exit_pids"] == []
    assert verdict["launcher_loop_observed"] is False
    assert verdict["launcher_loop_basis"] == []
    assert verdict["launcher_loader_record_count"] == 0
    assert slept == [30.0]


def test_trigger_bug_observation_and_restore_preserve_remaining_stale_ledger(
    tmp_path, monkeypatch
):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="STALE_ARMED",
        old_widget_id=17,
        completed_phases=[
            "BASELINE_CAPTURED",
            "BOUND_GENERAL",
            "SAFE_SIMPLE",
            "STALE_ARMED",
        ],
        final_home_role=profile["simple_home"],
        mutations_remaining=["stale_launcher_record:17"],
        precondition_status="PASS",
    )
    run_dir = tmp_path / "out" / "20260829T050618Z"
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    verdict["precondition_status"] = "PASS"
    (run_dir / "result.json").write_text(json.dumps(verdict), encoding="utf-8")
    _load_script("appwidget_stale_provider_evidence").write_evidence_manifest(run_dir)
    component = profile["app"]["provider"]
    package = profile["app"]["package"]
    crash = (
        "FATAL EXCEPTION: main\n"
        " at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185\n"
        " at com.android.launcher3.widget.PendingAppWidgetHostView.java:88\n"
    )
    responses = _identity_responses()
    responses = {key: [value, value] for key, value in responses.items()}
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                '<hierarchy><node text="Launcher" bounds="[0,0][480,800]" /></hierarchy>',
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                '<hierarchy><node text="간편모드" bounds="[0,0][480,800]" /></hierarchy>',
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): [
                "Starting\n",
                "Starting\n",
            ],
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "240", "453"): "",
            ("shell", "input", "tap", "359", "542"): ["", ""],
            ("exec-out", "screencap", "-p"): [
                b"\x89PNG\r\n\x1a\ntrigger",
                b"\x89PNG\r\n\x1a\nrestore",
            ],
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): [
                "",
                crash,
                crash,
            ],
            ("shell", "logcat", "-d", "-v", "threadtime"): [
                "",
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
            ],
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): [
                """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:18:52.665 pid=22527 realUid=10151
  process=com.hnlens.launcher3 reason=13 (OTHER KILLS BY SYSTEM) subreason=11
""",
                """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:19:23.986 pid=23363 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
ApplicationExitInfo #1:
  timestamp=2026-09-01 15:18:52.665 pid=22527 realUid=10151
  process=com.hnlens.launcher3 reason=13 (OTHER KILLS BY SYSTEM) subreason=11
""",
                """ApplicationExitInfo #0:
  timestamp=2026-09-01 15:19:23.986 pid=23363 realUid=10151
  process=com.hnlens.launcher3 reason=4 (APP CRASH(EXCEPTION)) subreason=0
""",
            ],
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): [
                "boot-1\n",
                "boot-1\n",
            ],
            ("shell", "pidof", profile["launcher_package"]): ["123\n", "\n"],
            ("shell", "dumpsys", "appwidget"): [
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n",
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n",
            ],
            ("shell", "dumpsys", "package", package): (
                "userId=20234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)
    slept = []
    monkeypatch.setattr(
        orchestrator, "_sleep", lambda seconds: slept.append(seconds), raising=False
    )

    triggered = orchestrator.trigger(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )
    assert triggered["current_phase"] == "TRIGGERED_BUG"
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert verdict["diagnosis_status"] == "OBSERVED"
    assert verdict["evidence_term"] == "BUG-GAP observed"
    assert verdict["stale_outcome"] == "BUG_OBSERVED"
    assert verdict["launcher_stale_record_evidence"] == "LOADER_LOG"
    assert verdict["crash_signature_count"] == 1
    assert verdict["evidence_boot_id"] == "boot-1"
    assert verdict["evidence_same_boot_as_baseline"] is True
    assert verdict["launcher_stability_window_s"] == 30.0
    assert verdict["launcher_crash_exit_count"] == 1
    assert verdict["launcher_crash_exit_pids"] == [23363]
    assert verdict["launcher_loop_observed"] is False
    assert verdict["launcher_loop_basis"] == []
    assert verdict["launcher_loader_record_count"] == 1
    assert verdict["safe_placeholder_or_cleanup"] is False
    assert verdict["normal_widget_update"] is False
    assert slept == [30.0]
    baseline_call = ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime")
    switch_call = ("shell", "am", "start", "-n", profile["switch_activity"])
    assert transport.calls.index(baseline_call) < transport.calls.index(switch_call)
    event_categories = [
        json.loads(line)["command_category"]
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert event_categories.index("launcher_pid_after_trigger-0001_window") < (
        event_categories.index("crash_after_trigger-0001")
    )
    assert (run_dir / "snapshots" / "crash_before_trigger-0001.txt").is_file()
    assert (run_dir / "snapshots" / "crash_after_trigger-0001.txt").is_file()
    assert (run_dir / "screenshots" / "trigger-0001.png").is_file()

    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert restored["current_phase"] == "RESTORED_SAFE"
    assert state["final_home_role"] == profile["simple_home"]
    assert state["mutations_remaining"] == ["stale_launcher_record:17"]


def test_trigger_requires_live_simple_home_before_attempt_baseline(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="STALE_ARMED",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL", "SAFE_SIMPLE", "STALE_ARMED"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["stale_launcher_record:17"],
        precondition_status="PASS",
    )
    run_dir = tmp_path / "out" / "20260829T050618Z"
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    result["precondition_status"] = "PASS"
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    _load_script("appwidget_stale_provider_evidence").write_evidence_manifest(run_dir)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="간편모드" bounds="[100,200][300,300]" /></hierarchy>'
            ),
            ("shell", "input", "tap", "200", "250"): "",
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="Simple HOME"):
        orchestrator.trigger(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    assert not any(call[:3] == ("shell", "logcat", "-d") for call in transport.calls)
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert state["attempt_counters"]["trigger"] == 1


def test_primary_error_is_not_replaced_by_cleanup_error():
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    primary = orchestrator.GateFailure("primary")
    cleanup = RuntimeError("cleanup")

    def fail_primary():
        raise primary

    def fail_cleanup():
        raise cleanup

    with pytest.raises(orchestrator.GateFailure, match="primary") as raised:
        orchestrator.run_with_safety_cleanup(fail_primary, fail_cleanup)
    assert raised.value is primary
    assert raised.value.cleanup_error is cleanup


def test_cli_error_format_surfaces_secondary_failures_and_remaining_state():
    cli = _fresh_script("appwidget_stale_provider_cli")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    primary = orchestrator.GateFailure("primary")
    primary.cleanup_error = RuntimeError("cleanup")
    primary.manifest_error = RuntimeError("manifest")

    rendered = cli._format_exception(
        primary,
        {
            "final_home_role": "com.hnlens.launcher3",
            "mutations_remaining": ["home_role:general"],
        },
    )

    assert "GateFailure: primary" in rendered
    assert "cleanup_error=RuntimeError: cleanup" in rendered
    assert "manifest_error=RuntimeError: manifest" in rendered
    assert "current_role=com.hnlens.launcher3" in rendered
    assert "mutations_remaining=home_role:general" in rendered


def test_trigger_zero_crash_records_stale_no_bug_without_claiming_fixed(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="STALE_ARMED",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL", "SAFE_SIMPLE", "STALE_ARMED"],
        final_home_role=profile["simple_home"],
        mutations_remaining=["stale_launcher_record:17"],
        precondition_status="PASS",
    )
    run_dir = tmp_path / "out" / "20260829T050618Z"
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    verdict["precondition_status"] = "PASS"
    (run_dir / "result.json").write_text(json.dumps(verdict), encoding="utf-8")
    component = profile["app"]["provider"]
    old_crash = (
        "FATAL EXCEPTION: main\n"
        " at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185\n"
        " at com.android.launcher3.widget.PendingAppWidgetHostView.java:88\n"
    )
    (run_dir / "snapshots" / "crash_baseline.txt").write_text(
        old_crash, encoding="utf-8"
    )
    _load_script("appwidget_stale_provider_evidence").write_evidence_manifest(run_dir)
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                '<hierarchy><node text="Launcher" bounds="[0,0][480,800]" /></hierarchy>',
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                _mode_switch_raw(normal_checked=False, simple_checked=True),
            ],
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\ninconclusive",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): [
                old_crash,
                old_crash,
            ],
            ("shell", "logcat", "-d", "-v", "threadtime"): [
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
            ],
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): [
                "",
                "",
            ],
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): [
                "boot-1\n",
                "boot-1\n",
            ],
            ("shell", "pidof", profile["launcher_package"]): ["123\n", "123\n"],
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
            ),
            ("shell", "am", "start", "-n", profile["switch_activity"]): [
                "Starting\n",
                "Starting\n",
            ],
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "240", "453"): "",
            ("shell", "input", "tap", "359", "542"): ["", ""],
        }
    )
    transport = _ScriptedTransport(models, responses)

    observed = orchestrator.trigger(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        wait=lambda: None,
    )

    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert observed["current_phase"] == "TRIGGERED_STALE_NO_BUG"
    assert observed["evidence_term"] == "manual evidence observed"
    assert state["current_phase"] == "TRIGGERED_STALE_NO_BUG"
    assert state["final_home_role"] == profile["general_home"]
    assert "home_role:general" in state["mutations_remaining"]
    assert state["attempts"][-1]["attempt_id"] == "trigger-0001"
    assert state["attempts"][-1]["status"] == "COMPLETED"
    assert verdict["diagnosis_status"] == "OBSERVED"
    assert verdict["evidence_term"] == "manual evidence observed"
    assert verdict["stale_outcome"] == "NO_TRIGGER_OBSERVED"
    assert verdict["crash_signature_count"] == 0
    assert ("shell", "am", "start", "-n", profile["switch_activity"]) in transport.calls


def test_preserve_armed_state_is_explicit_and_does_not_fake_completion(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="STALE_ARMED",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL", "SAFE_SIMPLE", "STALE_ARMED"],
        mutations_remaining=["stale_launcher_record:17"],
        attempt_counters={"arm": 1},
        attempts=[
            {
                "attempt_id": "arm-0001",
                "kind": "arm",
                "status": "INTERRUPTED",
                "interruption_reason": "stale active attempt found before restore",
            }
        ],
        active_attempts={},
        attempt_reconciliation_required=["arm-0001"],
    )
    transport = _ScriptedTransport(models, {})

    preserved = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        preserve_armed_state=True,
    )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert preserved["current_phase"] == "STALE_ARMED"
    assert preserved["preserved"] is True
    assert state["run_complete"] is False
    assert "RESUME.md" in state["preserve_warning"]
    assert state["attempt_reconciliation_required"] == ["arm-0001"]
    assert state["attempts"][0]["reconciliation_attempt"] == "restore-0001"
    assert "reconciled_by" not in state["attempts"][0]
    assert transport.calls == []


def test_verify_repeats_observation_without_mutating_device_or_phase(tmp_path):
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="TRIGGERED_BUG",
        old_widget_id=17,
        completed_phases=["BASELINE_CAPTURED", "BOUND_GENERAL", "SAFE_SIMPLE", "STALE_ARMED", "TRIGGERED_BUG"],
        final_home_role=profile["general_home"],
        mutations_remaining=["stale_launcher_record:17", "home_role:general"],
        precondition_status="PASS",
    )
    run_dir = tmp_path / "out" / "20260829T050618Z"
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    verdict.update(
        {
            "crash_signature_count": 1,
            "diagnosis_status": "OBSERVED",
            "evidence_term": "BUG-GAP observed",
            "precondition_status": "PASS",
        }
    )
    (run_dir / "result.json").write_text(json.dumps(verdict), encoding="utf-8")
    _load_script("appwidget_stale_provider_evidence").write_evidence_manifest(run_dir)
    component = profile["app"]["provider"]
    crash = (
        "FATAL EXCEPTION: main\n"
        " at com.android.launcher3.widget.LauncherAppWidgetHostView.java:185\n"
        " at com.android.launcher3.widget.PendingAppWidgetHostView.java:88\n"
    )
    responses = _identity_responses()
    responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="Launcher" bounds="[0,0][480,800]" /></hierarchy>'
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nverify",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): [
                "",
                crash,
            ],
            ("shell", "logcat", "-d", "-v", "threadtime"): [
                "",
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
            ],
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): [
                "",
                "REASON_CRASH\n",
            ],
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): [
                "boot-1\n",
                "boot-1\n",
            ],
            ("shell", "pidof", profile["launcher_package"]): ["321\n", "\n"],
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    observed = orchestrator.verify(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        wait=lambda: None,
    )

    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert observed["current_phase"] == "TRIGGERED_BUG"
    assert observed["evidence_term"] == "BUG-GAP observed"
    assert state["current_phase"] == "TRIGGERED_BUG"
    assert verdict["evidence_term"] == "BUG-GAP observed"
    assert verdict["verifications"][-1]["phase_consistent"] is True
    mutating_tokens = {"tap", "swipe", "draganddrop", "uninstall", "install-multiple", "reboot", "clear", "force-stop", "start"}
    assert not any(mutating_tokens.intersection(call) for call in transport.calls)

    repeated_responses = _identity_responses()
    repeated_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                '<hierarchy><node text="Launcher" bounds="[0,0][480,800]" /></hierarchy>'
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nverify-repeat",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): [
                crash,
                crash,
            ],
            ("shell", "logcat", "-d", "-v", "threadtime"): [
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
                "Widget provider not found for id=17 PendingAppWidgetHostView\n",
            ],
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): [
                "REASON_CRASH\n",
                "REASON_CRASH\n",
            ],
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): [
                "boot-1\n",
                "boot-1\n",
            ],
            ("shell", "pidof", profile["launcher_package"]): ["321\n", "321\n"],
            ("shell", "dumpsys", "appwidget"): (
                f"Providers:\n Provider{{uid=20234 cmp={component}}}\nWidgets:\n"
            ),
        }
    )
    with pytest.raises(orchestrator.GateFailure, match="conflicts"):
        orchestrator.verify(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, repeated_responses),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            wait=lambda: None,
        )
    repeated_verdict = json.loads(
        (run_dir / "result.json").read_text(encoding="utf-8")
    )
    assert len(repeated_verdict["verifications"]) == 2
    assert repeated_verdict["verifications"][-1]["attempt_id"] == "verify-0002"
    assert repeated_verdict["verifications"][-1]["status"] == "ERROR"
    assert repeated_verdict["verifications"][-1]["classification_phase"] == (
        "TRIGGERED_STALE_NO_BUG"
    )
    assert repeated_verdict["verifications"][-1]["phase_consistent"] is False
    assert (run_dir / "snapshots" / "crash_before_verify-0001.txt").is_file()
    assert (run_dir / "snapshots" / "crash_before_verify-0002.txt").is_file()
    assert (run_dir / "screenshots" / "verify-0001.png").is_file()
    assert (run_dir / "screenshots" / "verify-0002.png").is_file()

    error_responses = _identity_responses()
    error_responses.update(
        {
            ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): (
                f"{profile['general_home']}\n"
            ),
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            ("shell", "logcat", "-d", "-v", "threadtime"): "",
            ("shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]): "",
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): "boot-1\n",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): "ERROR",
        }
    )
    with pytest.raises(orchestrator.GateFailure, match="UI dump is incomplete"):
        orchestrator.verify(
            repo_root=tmp_path,
            profile=profile,
            transport=_ScriptedTransport(models, error_responses),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            wait=lambda: None,
        )
    error_verdict = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert error_verdict["verifications"][-1]["attempt_id"] == "verify-0003"
    assert error_verdict["verifications"][-1]["status"] == "ERROR"
    assert (
        run_dir / "snapshots" / "ui_after_verify-0003.raw.txt"
    ).read_text(encoding="utf-8") == "ERROR"
    assert not (
        run_dir / "snapshots" / "ui_after_verify-0003.xml"
    ).exists()


def test_verification_append_does_not_overwrite_canonical_trigger_verdict():
    """Catch re-verification rewriting a historical TRIGGERED_BUG result as fixed."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    result = {
        "diagnosis_status": "OBSERVED",
        "evidence_term": "BUG-GAP observed",
        "crash_signature_count": 1,
    }
    classification = {
        "diagnosis_status": "OBSERVED",
        "evidence_term": "runtime PASS",
        "phase": "TRIGGERED_FIXED",
    }
    observation = {
        "crash_signature_count": 0,
        "home_rendered": True,
        "launcher_crash_exit_count": 0,
        "launcher_crash_exit_pids": [],
        "launcher_loader_record_count": 1,
        "launcher_loop_basis": [],
        "launcher_loop_observed": False,
        "launcher_process_stable": True,
        "launcher_stale_record_evidence": "LOADER_LOG",
    }

    updated = orchestrator._append_verification(
        result,
        attempt_id="verify-0001",
        current_phase="TRIGGERED_BUG",
        classification=classification,
        observation=observation,
    )

    assert updated["evidence_term"] == "BUG-GAP observed"
    assert updated["crash_signature_count"] == 1
    assert updated["verifications"] == [
        {
            "attempt_id": "verify-0001",
            "status": "CLASSIFIED",
            "classification_phase": "TRIGGERED_FIXED",
            "crash_signature_count": 0,
            "diagnosis_status": "OBSERVED",
            "evidence_term": "runtime PASS",
            "home_rendered": True,
            "launcher_crash_exit_count": 0,
            "launcher_crash_exit_pids": [],
            "launcher_loader_record_count": 1,
            "launcher_loop_basis": [],
            "launcher_loop_observed": False,
            "launcher_process_stable": True,
            "launcher_stale_record_evidence": "LOADER_LOG",
            "phase_consistent": False,
        }
    ]


def test_verify_phase_conflict_records_error_before_closing_attempt(
    tmp_path, monkeypatch
):
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="TRIGGERED_BUG",
        old_widget_id=17,
        attempt_counters={},
        attempts=[],
        active_attempts={},
    )
    result = json.loads(
        (bundle.directory / "result.json").read_text(encoding="utf-8")
    )
    result["precondition_status"] = "PASS"
    bundle.write_json("result.json", result)

    monkeypatch.setattr(orchestrator, "preflight_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(
        orchestrator,
        "_current_role",
        lambda *_a, **_k: profile["general_home"],
    )
    monkeypatch.setattr(
        orchestrator,
        "_capture_attempt_baseline",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        orchestrator,
        "_observe_trigger",
        lambda **_kwargs: {
            "crash_signature_count": 0,
            "home_rendered": True,
            "launcher_crash_exit_count": 0,
            "launcher_crash_exit_pids": [],
            "launcher_loader_record_count": 1,
            "launcher_loop_basis": [],
            "launcher_loop_observed": False,
            "launcher_process_stable": True,
            "launcher_stale_record_evidence": "LOADER_LOG",
            "normal_widget_update": True,
            "safe_placeholder_or_cleanup": True,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "classify_trigger",
        lambda **_kwargs: {
            "diagnosis_status": "OBSERVED",
            "evidence_term": "runtime PASS",
            "phase": "TRIGGERED_FIXED",
        },
    )

    with pytest.raises(
        orchestrator.GateFailure,
        match="conflicts with canonical trigger phase",
    ):
        orchestrator.verify(
            repo_root=tmp_path,
            profile=profile,
            transport=object(),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
        )

    state = json.loads((bundle.directory / "run.json").read_text(encoding="utf-8"))
    verdict = json.loads(
        (bundle.directory / "result.json").read_text(encoding="utf-8")
    )
    assert state["attempts"][-1]["attempt_id"] == "verify-0001"
    assert state["attempts"][-1]["status"] == "ERROR"
    assert "conflicts with canonical trigger phase" in state["attempts"][-1][
        "primary_error"
    ]
    assert "verify" not in state["active_attempts"]
    assert verdict["verifications"][-1]["status"] == "ERROR"
    assert verdict["verifications"][-1]["phase_consistent"] is False
    assert "conflicts with canonical trigger phase" in verdict["verifications"][-1][
        "error"
    ]
    evidence.verify_evidence_manifest(bundle.directory)


@pytest.mark.parametrize(
    ("command", "extra"),
    [
        ("bind", []),
        ("arm", ["--lifecycle", "uninstall-reinstall"]),
        ("arm", ["--lifecycle", "remove-widget-uninstall-reinstall"]),
        ("trigger", []),
        ("restore", []),
        (
            "reset-fixture",
            [
                "--next-profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
                "--next-run-id", "20260829T050619Z",
            ],
        ),
    ],
)
def test_mutating_cli_requires_execute_before_transport(monkeypatch, capsys, command, extra):
    cli = _fresh_script("appwidget_stale_provider_cli")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("transport constructed before approval gate")

    monkeypatch.setattr(cli, "AdbTransport", forbidden, raising=False)
    argv = [
        command,
        "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
        "--serial", "SER",
        "--expected-model", "AT-M140",
        "--expected-fingerprint",
        "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260901S:user/release-keys",
        "--run-id", "20260829T050618Z",
        *extra,
    ]

    assert cli.main(argv) == 2
    assert "--execute" in capsys.readouterr().err


def test_restore_cli_requires_and_forwards_explicit_package_recovery_approval(
    monkeypatch, capsys
):
    cli = _fresh_script("appwidget_stale_provider_cli")
    captured = {}
    monkeypatch.setattr(cli, "AdbTransport", lambda _serial: object())

    def fake_restore(**kwargs):
        captured.update(kwargs)
        return {"run_id": kwargs["run_id"]}

    monkeypatch.setattr(cli, "restore", fake_restore)
    common = [
        "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
        "--serial", "SER",
        "--expected-model", "AT-M140",
        "--expected-fingerprint",
        cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]["fingerprint"],
        "--run-id", "20260829T050618Z",
        "--execute",
    ]

    assert cli.main(["restore", *common, "--recover-package"]) == 0
    assert captured["recover_package"] is True
    assert "install-multiple" in json.dumps(
        cli.render_plan(
            "AT_M140_BUG27084_KNOWN_BAD_V1",
            cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"],
        )
    )
    assert "--recover-package" in cli._parser().format_help()

    assert cli.main(["bind", *common, "--recover-package"]) == 2
    assert "valid only with restore" in capsys.readouterr().err


def test_entrypoint_reexports_cli_and_remains_plan_default(capsys):
    entrypoint = _fresh_script("appwidget_stale_provider_repro")

    assert entrypoint.main(
        ["--profile", "AT_M140_BUG27084_KNOWN_BAD_V1"]
    ) == 0
    assert json.loads(capsys.readouterr().out)["adb"] == "OFF"


def test_cli_resolves_repo_root_from_entrypoint_not_process_cwd(
    tmp_path, monkeypatch, capsys
):
    cli = _fresh_script("appwidget_stale_provider_cli")
    captured = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "AdbTransport", lambda _serial: object())

    def fake_capture(**kwargs):
        captured.update(kwargs)
        return {"run_id": "20260829T050618Z"}

    monkeypatch.setattr(cli, "capture", fake_capture)

    assert cli.main(
        [
            "capture",
            "--profile",
            "AT_M140_BUG27084_KNOWN_BAD_V1",
            "--serial",
            "SER",
            "--expected-model",
            "AT-M140",
            "--expected-fingerprint",
            cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]["fingerprint"],
        ]
    ) == 0
    assert captured["repo_root"] == Path(cli.__file__).resolve().parents[1]
    assert json.loads(capsys.readouterr().out)["run_id"] == "20260829T050618Z"


def test_production_appwidget_transcript_format_parses_bound_and_registry_only():
    """Minimal lines copied from the preserved 20260829 AT-M140 evidence."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    component = (
        "com.winson.simpleclock/"
        "com.winson.simpleclock.widget.SimpleClockWidgetProvider"
    )
    bound = f"""Providers:
  [51] provider ProviderId{{user:0, app:10195, cmp:ComponentInfo{{{component}}}}}
Widgets:
  [7] id=24
    host=HostId{{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}}
    provider=ProviderId{{user:0, app:10195, cmp:ComponentInfo{{{component}}}}}
    host.callbacks=com.android.internal.appwidget.IAppWidgetHost$Stub$Proxy@5a9b4
    views=android.widget.RemoteViews@1743a84
"""
    registry_only = f"""Providers:
  [51] provider ProviderId{{user:0, app:10197, cmp:ComponentInfo{{{component}}}}}
Widgets:
  [0] id=19
    host=HostId{{user:0, app:10151, hostId:1026, pkg:com.hnlens.launcher3}}
    provider=ProviderId{{user:0, app:10098, cmp:ComponentInfo{{com.google/.Other}}}}
    views=android.widget.RemoteViews@696db9c
"""

    before = parsers.parse_appwidget_state(bound, component, "com.hnlens.launcher3")
    after = parsers.parse_appwidget_state(
        registry_only, component, "com.hnlens.launcher3"
    )

    assert before.provider_uid == 10195
    assert [(item.widget_id, item.remote_views_present) for item in before.bindings] == [
        (24, True)
    ]
    assert after.provider_registered is True
    assert after.provider_uid == 10197
    assert after.bindings == ()


def test_production_crash_records_are_counted_per_fatal_exception_without_blank_lines():
    parsers = _load_script("appwidget_stale_provider_parsers")
    record = (
        "FATAL EXCEPTION: main\n"
        " at com.android.launcher3.widget.LauncherAppWidgetHostView.updateAppWidget"
        "(LauncherAppWidgetHostView.java:185)\n"
        " at com.android.launcher3.widget.PendingAppWidgetHostView.<init>"
        "(PendingAppWidgetHostView.java:88)\n"
    )
    transcript = "--------- beginning of crash\n" + record + record

    assert parsers.parse_crash_signature(transcript).count == 2


def test_mode_switch_handles_user_observed_always_allow_gate(tmp_path, monkeypatch):
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["mode_ui"] = {
        "switch_to_general_resource_id": "com.hnlens.simplemode:id/rb_normal",
        "switch_to_simple_resource_id": "com.hnlens.simplemode:id/rb_simple",
        "confirm_resource_id": "com.hnlens.simplemode:id/tv_confirm",
        "always_allow_text": "항상 허용",
    }
    bundle = evidence.EvidenceBundle.create(tmp_path / "out", "20260829T050618Z")
    responses = {
        ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"): [
            f"{profile['simple_home']}\n",
            f"{profile['simple_home']}\n",
            f"{profile['general_home']}\n",
        ],
        ("shell", "am", "start", "-n", profile["switch_activity"]): "Starting\n",
        ("exec-out", "uiautomator", "dump", "/dev/tty"): [
            _mode_switch_raw(normal_checked=False, simple_checked=True),
            _mode_switch_raw(normal_checked=True, simple_checked=False),
            _permission_raw(),
        ],
        ("shell", "input", "tap", "240", "364"): "",
        ("shell", "input", "tap", "359", "542"): "",
        ("shell", "input", "tap", "240", "680"): "",
    }
    transport = _ScriptedTransport(models, responses)
    slept = []
    mutation_intents = []
    monkeypatch.setattr(orchestrator, "_sleep", lambda seconds: slept.append(seconds))

    role = orchestrator._ensure_home_role(
        bundle,
        transport,
        "SER",
        profile,
        profile["general_home"],
        "test-switch",
        poll_attempts=3,
        before_switch=lambda: mutation_intents.append(list(transport.calls)),
    )

    assert role == profile["general_home"]
    assert mutation_intents[-1][-1] == (
        "exec-out",
        "uiautomator",
        "dump",
        "/dev/tty",
    )
    assert ("shell", "input", "tap", "240", "364") in transport.calls
    assert ("shell", "input", "tap", "359", "542") in transport.calls
    assert ("shell", "input", "tap", "240", "680") in transport.calls
    assert ("shell", "input", "tap", "243", "542") not in transport.calls
    assert slept == [1.0]


def test_ui_package_match_is_exact_and_fail_closed():
    """Catch recovery accepting Android's crash dialog or a package prefix as HOME."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    xml = (
        '<hierarchy><node package="android" />'
        '<node package="com.hnlens.simplemode.helper" />'
        '<node package="com.hnlens.simplemode" /></hierarchy>'
    )

    assert parsers.ui_contains_exact_package(xml, "com.hnlens.simplemode") is True
    assert parsers.ui_contains_exact_package(xml, "com.hnlens.launcher3") is False

    with pytest.raises(parsers.UiDumpParseError):
        parsers.ui_contains_exact_package("not xml", "com.hnlens.simplemode")


@pytest.mark.parametrize(
    ("mutations_remaining", "dialog_title"),
    [
        pytest.param(
            ["home_role:general"],
            "MIVE Home이(가) 중지됨",
            id="general-ledger-stopped",
        ),
        pytest.param(
            ["home_role:general"],
            "MIVE Home이(가) 계속 중단됨",
            id="general-ledger-keeps-stopping",
        ),
        pytest.param(
            ["home_role:unverified"],
            "MIVE Home이(가) 중지됨",
            id="unverified-only-ledger",
        ),
    ],
)
def test_restore_direct_home_role_recovery_bypasses_crash_loop_and_verifies_three_way(
    tmp_path, mutations_remaining, dialog_title
):
    """Catch emergency restore falling back to slow dialog-dismiss/UI mode switching."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["recovery_ui"] = {
        "launcher_crash_titles": (
            "MIVE Home이(가) 중지됨",
            "MIVE Home이(가) 계속 중단됨",
        ),
        "title_resource_id": "android:id/alertTitle",
        "close_resource_id": "android:id/aerr_close",
    }
    _seed_run(
        tmp_path,
        profile,
        final_home_role=profile["general_home"],
        mutations_remaining=mutations_remaining,
    )
    package = profile["app"]["package"]
    responses = _identity_responses()
    responses.update(
        {
            (
                "shell", "cmd", "role", "get-role-holders",
                "android.app.role.HOME",
            ): [
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _launcher_crash_dialog_raw(title=dialog_title),
                _simple_home_raw(),
                _simple_home_raw(),
            ],
            (
                "shell", "cmd", "role", "add-role-holder", "--user", "0",
                "android.app.role.HOME", profile["simple_home"],
            ): "",
            ("shell", "input", "keyevent", "KEYCODE_HOME"): "",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['simple_home']}/.Home\n"
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\ndirect-restore",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            (
                "shell", "dumpsys", "activity", "exit-info",
                profile["launcher_package"],
            ): "",
            ("shell", "dumpsys", "appwidget"): "Providers:\nWidgets:\n",
            ("shell", "dumpsys", "package", package): (
                "appId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
        direct_home_role_recovery=True,
        wait=lambda: None,
    )

    assert restored["current_phase"] == "RESTORED_SAFE"
    assert restored["final_home_role"] == profile["simple_home"]
    assert restored["mutations_remaining"] == []
    assert (
        "shell", "cmd", "role", "add-role-holder", "--user", "0",
        "android.app.role.HOME", profile["simple_home"],
    ) in transport.calls
    assert ("shell", "input", "keyevent", "KEYCODE_HOME") in transport.calls
    assert not any(call[:3] == ("shell", "input", "tap") for call in transport.calls)
    assert ("shell", "am", "start", "-n", profile["switch_activity"]) not in transport.calls


@pytest.mark.parametrize(
    ("mutations", "dialog_title", "decoy_text", "expected_error"),
    [
        (
            ["widget_binding:17"],
            "MIVE Home이(가) 중지됨",
            None,
            "recorded General HOME mutation",
        ),
        (
            ["home_role:general"],
            "다른 앱이 중지됨",
            "MIVE Home이(가) 중지됨",
            "exact Launcher crash dialog",
        ),
    ],
)
def test_restore_direct_home_role_recovery_rejects_unsafe_preconditions_before_role_write(
    tmp_path, mutations, dialog_title, decoy_text, expected_error
):
    """Catch the emergency role write becoming an unconditional restore path."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["recovery_ui"] = {
        "launcher_crash_titles": (
            "MIVE Home이(가) 중지됨",
            "MIVE Home이(가) 계속 중단됨",
        ),
        "title_resource_id": "android:id/alertTitle",
        "close_resource_id": "android:id/aerr_close",
    }
    _seed_run(
        tmp_path,
        profile,
        final_home_role=profile["general_home"],
        mutations_remaining=mutations,
    )
    responses = _identity_responses()
    responses.update(
        {
            (
                "shell", "cmd", "role", "get-role-holders",
                "android.app.role.HOME",
            ): f"{profile['general_home']}\n",
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                _launcher_crash_dialog_raw(
                    title=dialog_title,
                    decoy_text=decoy_text,
                )
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match=expected_error):
        orchestrator.restore(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
            direct_home_role_recovery=True,
        )

    assert not any(
        call[:5] == ("shell", "cmd", "role", "add-role-holder", "--user")
        for call in transport.calls
    )


def test_direct_home_role_recovery_rejects_profile_that_redefines_system_dialog_ids(
    tmp_path,
):
    """Catch a profile broadening the emergency recovery gate to arbitrary nodes."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["recovery_ui"] = {
        "launcher_crash_titles": ("MIVE Home이(가) 계속 중단됨",),
        "title_resource_id": "example:id/title",
        "close_resource_id": "example:id/close",
    }
    bundle = evidence.EvidenceBundle.create(tmp_path / "direct", "20260901T000000Z")
    state = {"mutations_remaining": ["home_role:general"]}
    responses = {
        (
            "shell", "cmd", "role", "get-role-holders",
            "android.app.role.HOME",
        ): f"{profile['general_home']}\n",
        ("exec-out", "uiautomator", "dump", "/dev/tty"): (
            _launcher_crash_dialog_raw(
                title="MIVE Home이(가) 계속 중단됨",
                title_resource_id="example:id/title",
                close_resource_id="example:id/close",
            )
        ),
    }
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="exact Launcher crash dialog"):
        orchestrator._recover_simple_home_role_direct(
            bundle,
            transport,
            "SER",
            profile,
            state,
            "restore",
        )

    assert not any(
        call[:5] == ("shell", "cmd", "role", "add-role-holder", "--user")
        for call in transport.calls
    )


def test_direct_home_role_recovery_rejects_profile_that_expands_title_allowlist(
    tmp_path,
):
    """Catch a profile authorizing crash dialogs beyond the two observed titles."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    profile["recovery_ui"] = {
        "launcher_crash_titles": (
            "MIVE Home이(가) 중지됨",
            "MIVE Home이(가) 계속 중단됨",
            "다른 앱이 중지됨",
        ),
        "title_resource_id": "android:id/alertTitle",
        "close_resource_id": "android:id/aerr_close",
    }
    bundle = evidence.EvidenceBundle.create(tmp_path / "direct", "20260901T000000Z")
    state = {"mutations_remaining": ["home_role:general"]}
    responses = {
        (
            "shell", "cmd", "role", "get-role-holders",
            "android.app.role.HOME",
        ): f"{profile['general_home']}\n",
        ("exec-out", "uiautomator", "dump", "/dev/tty"): (
            _launcher_crash_dialog_raw(title="다른 앱이 중지됨")
        ),
    }
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="exact Launcher crash dialog"):
        orchestrator._recover_simple_home_role_direct(
            bundle,
            transport,
            "SER",
            profile,
            state,
            "restore",
        )

    assert not any(
        call[:5] == ("shell", "cmd", "role", "add-role-holder", "--user")
        for call in transport.calls
    )


def test_default_restore_keeps_unverified_ledger_when_role_only_is_simple(
    tmp_path,
):
    """Catch a retry declaring RESTORED_SAFE after a partial direct-role recovery."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        final_home_role=profile["general_home"],
        mutations_remaining=["home_role:general", "home_role:unverified"],
    )
    package = profile["app"]["package"]
    responses = _identity_responses()
    responses.update(
        {
            (
                "shell", "cmd", "role", "get-role-holders",
                "android.app.role.HOME",
            ): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['general_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                _launcher_crash_dialog_raw()
            ),
            ("exec-out", "screencap", "-p"): b"\x89PNG\r\n\x1a\nunsafe",
            ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"): "",
            (
                "shell", "dumpsys", "activity", "exit-info",
                profile["launcher_package"],
            ): "",
            ("shell", "dumpsys", "appwidget"): "Providers:\nWidgets:\n",
            ("shell", "dumpsys", "package", package): (
                "appId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(orchestrator.GateFailure, match="3-way verification"):
        orchestrator.restore(
            repo_root=tmp_path,
            profile=profile,
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    state = json.loads(
        (tmp_path / "out" / "20260829T050618Z" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["current_phase"] == "BASELINE_CAPTURED"
    assert "home_role:general" in state["mutations_remaining"]
    assert "home_role:unverified" in state["mutations_remaining"]
    assert ("exec-out", "screencap", "-p") not in transport.calls


def test_restore_cli_scopes_and_forwards_direct_home_role_recovery(monkeypatch, capsys):
    """Catch the emergency recovery flag leaking to non-restore commands or being ignored."""
    cli = _fresh_script("appwidget_stale_provider_cli")
    captured = {}
    monkeypatch.setattr(cli, "AdbTransport", lambda _serial: object())

    def fake_restore(**kwargs):
        captured.update(kwargs)
        return {"run_id": kwargs["run_id"]}

    monkeypatch.setattr(cli, "restore", fake_restore)
    common = [
        "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
        "--serial", "SER",
        "--expected-model", "AT-M140",
        "--expected-fingerprint",
        cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]["fingerprint"],
        "--run-id", "20260829T050618Z",
        "--execute",
        "--direct-home-role-recovery",
    ]

    assert cli.main(["restore", *common]) == 0
    assert captured["direct_home_role_recovery"] is True
    assert "--direct-home-role-recovery" in cli._parser().format_help()
    assert "add-role-holder" in json.dumps(
        cli.render_plan(
            "AT_M140_BUG27084_KNOWN_BAD_V1",
            cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"],
        )
    )

    assert cli.main(["bind", *common]) == 2
    assert "valid only with restore" in capsys.readouterr().err


def test_parse_launcher_host_bindings_includes_every_provider_and_widget_id():
    """Catch fixture resets proving absence for only the selected provider."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    transcript = """Providers:
  Provider{uid=101 cmp=com.vendor.one/.Widget}
  Provider{uid=102 cmp=com.vendor.two/.Widget}
Widgets:
  [0] id=17
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:101, cmp:ComponentInfo{com.vendor.one/.Widget}}
    views=RemoteViews{one}
  [1] id=29
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:102, cmp:ComponentInfo{com.vendor.two/.Widget}}
    views=null
  [2] id=31
    host=HostId{user:0, app:999, hostId:12, pkg:com.other.launcher}
    provider=ProviderId{user:0, app:102, cmp:ComponentInfo{com.vendor.two/.Widget}}
"""

    bindings = parsers.parse_launcher_host_bindings(
        transcript, "com.hnlens.launcher3"
    )

    assert [(item.widget_id, item.provider_component) for item in bindings] == [
        (17, "com.vendor.one/.Widget"),
        (29, "com.vendor.two/.Widget"),
    ]
    assert [item.remote_views_present for item in bindings] == [True, False]


def test_parse_launcher_host_bindings_rejects_incomplete_appwidget_transcript(
):
    """Catch a truncated dump being misclassified as an empty Launcher host."""
    parsers = _load_script("appwidget_stale_provider_parsers")

    with pytest.raises(ValueError, match="appwidget dump is incomplete"):
        parsers.parse_launcher_host_bindings(
            "Providers:\n", "com.hnlens.launcher3"
        )


def test_parse_launcher_host_bindings_counts_orphan_provider_as_a_binding():
    """Catch stale provider=null host records disappearing from reset evidence."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    transcript = (
        "Providers:\nWidgets:\n  [0] id=17\n"
        "    host=HostId{pkg:com.hnlens.launcher3}\n"
        "    provider=null\n"
    )

    bindings = parsers.parse_launcher_host_bindings(
        transcript, "com.hnlens.launcher3"
    )

    assert len(bindings) == 1
    assert bindings[0].widget_id == 17
    assert bindings[0].provider_component is None


def _general_home_raw(profile):
    return (
        '<hierarchy rotation="0"><node text="General home" '
        f'package="{profile["general_home"]}" bounds="[0,0][480,800]" />'
        "</hierarchy>UI hierchary dumped to: /dev/tty\n"
    )


def _reset_fixture_responses(profile, *, clear_callback="Success\n"):
    before = """Providers:
  Provider{uid=101 cmp=com.vendor.one/.Widget}
  Provider{uid=102 cmp=com.vendor.two/.Widget}
Widgets:
  [0] id=17
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:101, cmp:ComponentInfo{com.vendor.one/.Widget}}
    views=RemoteViews{one}
  [1] id=29
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:102, cmp:ComponentInfo{com.vendor.two/.Widget}}
    views=null
"""
    responses = _identity_responses()
    responses.update(
        {
            (
                "shell", "cmd", "role", "get-role-holders",
                "android.app.role.HOME",
            ): [
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['general_home']}\n",
                f"{profile['simple_home']}\n",
                f"{profile['simple_home']}\n",
            ],
            ("shell", "dumpsys", "activity", "activities"): [
                f"mResumedActivity: {profile['simple_home']}/.Home\n",
                f"mResumedActivity: {profile['general_home']}/.Home\n",
                f"mResumedActivity: {profile['simple_home']}/.Home\n",
            ],
            ("exec-out", "uiautomator", "dump", "/dev/tty"): [
                _simple_home_raw(),
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                _general_home_raw(profile),
                _mode_switch_raw(normal_checked=True, simple_checked=False),
                _mode_switch_raw(normal_checked=False, simple_checked=True),
                _simple_home_raw(),
            ],
            ("shell", "dumpsys", "appwidget"): [
                before,
                "Providers:\nWidgets:\n",
            ],
            ("shell", "dumpsys", "package", profile["app"]["package"]): (
                "appId=10234\nversionCode=216\nversionName=2.1.6\n"
                "signatures=PackageSignatures{signatures:[498de32a]}\n"
                "stopped=false notLaunched=false\n"
            ),
            ("shell", "pm", "clear", profile["launcher_package"]): (
                clear_callback
            ),
            ("shell", "am", "start", "-n", profile["switch_activity"]): [
                "Starting\n",
                "Starting\n",
            ],
            ("shell", "input", "tap", "240", "364"): "",
            ("shell", "input", "tap", "240", "453"): "",
            ("shell", "input", "tap", "359", "542"): ["", ""],
        }
    )
    return responses


def test_reset_fixture_clears_only_after_durable_intent_and_records_ready_lineage(
    tmp_path,
):
    """Catch an independent-cycle reset clearing Launcher before a durable ledger."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        completed_phases=["BASELINE_CAPTURED", "RESTORED_SAFE"],
        mutations_remaining=["stale_launcher_record:37"],
        old_widget_id=41,
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=True,
    )

    def clear_after_ledger(_argv, _binary):
        state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
        result = json.loads((bundle.directory / "result.json").read_text("utf-8"))
        assert "launcher_data:clear-unverified" in state["mutations_remaining"]
        assert state["run_complete"] is False
        assert state["fixture_reset_status"] == "IN_PROGRESS"
        assert result["run_complete"] is False
        assert result["fixture_reset_status"] == "IN_PROGRESS"
        assert result["mutations_remaining"] == state["mutations_remaining"]
        return "Success\n"

    transport = _ScriptedTransport(
        models,
        _reset_fixture_responses(profile, clear_callback=clear_after_ledger),
    )

    reset = orchestrator.reset_fixture(
        repo_root=tmp_path,
        profile=profile,
        next_profile=profile,
        next_profile_name="NEXT_PROFILE",
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        next_run_id="20260829T050619Z",
        execute=True,
        wait=lambda: None,
    )

    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    record = json.loads(
        (bundle.directory / "fixture_reset.json").read_text("utf-8")
    )
    assert reset["status"] == "READY_FOR_CAPTURE"
    assert state["current_phase"] == "RESTORED_SAFE"
    assert state["mutations_remaining"] == []
    assert state["fixture_reset"]["status"] == "READY_FOR_CAPTURE"
    assert record["status"] == "READY_FOR_CAPTURE"
    assert record["source_run_id"] == "20260829T050618Z"
    assert record["next_run_id"] == "20260829T050619Z"
    assert record["next_profile_name"] == "NEXT_PROFILE"
    assert record["prior_launcher_widget_ids"] == [17, 29, 37, 41]
    assert record["post_clear_launcher_widget_ids"] == []
    assert record["post_clear_launcher_host_bindings"] == []
    assert record["markers_remaining"] == []
    assert record["final_home_role"] == profile["simple_home"]
    pre_manifest = (
        bundle.directory / record["pre_reset_manifest_snapshot"]
    ).read_bytes()
    assert hashlib.sha256(pre_manifest).hexdigest().upper() == record[
        "pre_reset_manifest_sha256"
    ]
    assert (
        "shell", "pm", "clear", profile["launcher_package"]
    ) in transport.calls
    result_state = json.loads(
        (bundle.directory / "result.json").read_text("utf-8")
    )
    assert result_state["run_complete"] is True
    assert result_state["fixture_reset_status"] == "READY_FOR_CAPTURE"
    assert result_state["mutations_remaining"] == []
    evidence.verify_evidence_manifest(bundle.directory)


def test_reset_fixture_retries_transient_final_simple_activity_race(tmp_path):
    """Catch a single transition snapshot wasting an otherwise valid reset."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        completed_phases=["BASELINE_CAPTURED", "RESTORED_SAFE"],
        mutations_remaining=["stale_launcher_record:37"],
        old_widget_id=41,
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=True,
    )
    responses = _reset_fixture_responses(profile)
    role_key = (
        "shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"
    )
    responses[role_key].append(f"{profile['simple_home']}\n")
    activity_key = ("shell", "dumpsys", "activity", "activities")
    responses[activity_key][-1:] = [
        "mResumedActivity: unknown/.Transition\n",
        f"mResumedActivity: {profile['simple_home']}/.Home\n",
    ]
    ui_key = ("exec-out", "uiautomator", "dump", "/dev/tty")
    responses[ui_key].append(_simple_home_raw())
    transport = _ScriptedTransport(models, responses)

    reset = orchestrator.reset_fixture(
        repo_root=tmp_path,
        profile=profile,
        next_profile=profile,
        next_profile_name="NEXT_PROFILE",
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        next_run_id="20260829T050619Z",
        execute=True,
        wait=lambda: None,
    )

    assert reset["status"] == "READY_FOR_CAPTURE"
    snapshots = tmp_path / "out" / "20260829T050618Z" / "snapshots"
    assert (
        snapshots
        / "activity_verify_reset-fixture-0001_final_simple_retry_2.txt"
    ).exists()


def _seed_ready_fixture_reset(tmp_path, profile):
    evidence = _load_script("appwidget_stale_provider_evidence")
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        completed_phases=["BASELINE_CAPTURED", "RESTORED_SAFE"],
        mutations_remaining=[],
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=True,
    )
    inputs = evidence.verify_inputs(tmp_path, profile)
    receipt = {
        "final_home_role": profile["simple_home"],
        "markers_remaining": [],
        "next_profile_identity": {
            "inputs": inputs,
            "profile_identity": {
                "fingerprint": profile["fingerprint"],
                "incremental": profile["incremental"],
                "model": profile["model"],
                "viewport": list(profile["viewport"]),
            },
            "profile_name": "NEXT_PROFILE",
        },
        "next_profile_name": "NEXT_PROFILE",
        "next_run_id": "20260829T050619Z",
        "post_clear_launcher_host_bindings": [],
        "post_clear_launcher_widget_ids": [],
        "pre_reset_manifest_sha256": "A" * 64,
        "prior_launcher_host_bindings": [],
        "prior_launcher_widget_ids": [],
        "reset_attempt_id": "reset-fixture-0001",
        "schema_version": 1,
        "source_run_id": "20260829T050618Z",
        "status": "READY_FOR_CAPTURE",
    }
    bundle.write_json("fixture_reset.json", receipt)
    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    state.update(
        {
            "attempts": [
                {
                    "attempt_id": "reset-fixture-0001",
                    "kind": "reset-fixture",
                    "status": "COMPLETED",
                }
            ],
            "fixture_reset": {
                "attempt_id": "reset-fixture-0001",
                "next_run_id": "20260829T050619Z",
                "status": "READY_FOR_CAPTURE",
            },
            "last_fixture_reset_attempt_id": "reset-fixture-0001",
        }
    )
    bundle.write_json("run.json", state)
    return bundle


def test_capture_consumes_exact_reset_once_and_pins_external_lineage(tmp_path):
    """Catch a reset receipt being replayed or a child omitting predecessor hashes."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    source = _seed_ready_fixture_reset(tmp_path, profile)
    transport = _ScriptedTransport(models, _capture_responses(profile))

    result = orchestrator.capture(
        repo_root=tmp_path,
        profile=profile,
        profile_name="NEXT_PROFILE",
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050619Z",
        after_reset_run_id="20260829T050618Z",
    )

    child = tmp_path / "out" / "20260829T050619Z"
    source_state = json.loads((source.directory / "run.json").read_text("utf-8"))
    lineage = json.loads((child / "lineage.json").read_text("utf-8"))
    assert result["run_id"] == "20260829T050619Z"
    assert source_state["fixture_reset"]["status"] == "CONSUMED"
    assert source_state["fixture_reset"]["consumed_by_run_id"] == (
        "20260829T050619Z"
    )
    assert lineage["source_run_id"] == "20260829T050618Z"
    assert lineage["reset_attempt_id"] == "reset-fixture-0001"
    assert lineage["source_manifest_sha256"] == hashlib.sha256(
        (source.directory / "evidence_sha256.txt").read_bytes()
    ).hexdigest().upper()
    assert lineage["reset_receipt_sha256"] == hashlib.sha256(
        (source.directory / "fixture_reset.json").read_bytes()
    ).hexdigest().upper()
    assert lineage["reset_consumption_sha256"] == hashlib.sha256(
        (source.directory / "fixture_reset_consumption.json").read_bytes()
    ).hexdigest().upper()
    evidence.verify_evidence_manifest(source.directory)
    evidence.verify_evidence_manifest(child)
    child_state = json.loads((child / "run.json").read_text("utf-8"))
    orchestrator._assert_run_identity(
        child,
        child_state,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        profile=profile,
    )

    with pytest.raises(orchestrator.GateFailure, match="handed off"):
        orchestrator.bind(
            repo_root=tmp_path,
            profile=profile,
            transport=object(),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            execute=True,
        )

    replay_transport = _ScriptedTransport(models, _identity_responses())
    with pytest.raises(orchestrator.GateFailure, match="already consumed"):
        orchestrator.capture(
            repo_root=tmp_path,
            profile=profile,
            profile_name="NEXT_PROFILE",
            transport=replay_transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050619Z",
            after_reset_run_id="20260829T050618Z",
        )


def test_reset_fixture_host_binding_timeout_recovers_simple_and_keeps_reset_marker(
    tmp_path,
):
    """Catch a failed host-zero poll leaving General HOME or erasing reset debt."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        completed_phases=["BASELINE_CAPTURED", "RESTORED_SAFE"],
        mutations_remaining=["stale_launcher_record:17"],
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=True,
    )
    responses = _reset_fixture_responses(profile)
    stale_dump = responses[("shell", "dumpsys", "appwidget")][0]
    responses[("shell", "dumpsys", "appwidget")] = [
        stale_dump,
        *([stale_dump] * 15),
    ]
    role_key = (
        "shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"
    )
    responses[role_key].insert(5, f"{profile['general_home']}\n")
    transport = _ScriptedTransport(models, responses)

    with pytest.raises(
        orchestrator.GateFailure,
        match="Launcher host bindings remain",
    ):
        orchestrator.reset_fixture(
            repo_root=tmp_path,
            profile=profile,
            next_profile=profile,
            next_profile_name="NEXT_PROFILE",
            transport=transport,
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            next_run_id="20260829T050619Z",
            execute=True,
            wait=lambda: None,
        )

    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    assert state["final_home_role"] == profile["simple_home"]
    assert "launcher_data:cleared-uninitialized" in state["mutations_remaining"]
    assert "stale_launcher_record:17" in state["mutations_remaining"]
    assert "home_role:general" not in state["mutations_remaining"]
    assert "home_role:unverified" not in state["mutations_remaining"]
    assert state["attempts"][-1]["attempt_id"] == "reset-fixture-0001"
    assert state["attempts"][-1]["status"] == "ERROR"
    assert state["run_complete"] is False
    assert state["fixture_reset_status"] == "FAILED_SAFE"
    result = json.loads((bundle.directory / "result.json").read_text("utf-8"))
    assert result["run_complete"] is False
    assert result["fixture_reset_status"] == "FAILED_SAFE"
    assert result["mutations_remaining"] == state["mutations_remaining"]
    assert not (bundle.directory / "fixture_reset.json").exists()


def test_reset_safety_cleanup_runs_for_keyboard_interrupt_and_preserves_primary():
    """Catch operator interruption bypassing the reset-specific Simple cleanup."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    primary = KeyboardInterrupt("operator interrupt")
    calls = []

    def interrupt():
        raise primary

    with pytest.raises(KeyboardInterrupt, match="operator interrupt") as raised:
        orchestrator._run_reset_with_safety_cleanup(
            interrupt, lambda: calls.append("cleanup")
        )

    assert raised.value is primary
    assert calls == ["cleanup"]


def test_reset_safety_cleanup_attaches_secondary_failure_to_interrupt():
    """Catch reset cleanup errors replacing the operator interruption."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    primary = KeyboardInterrupt("operator interrupt")
    cleanup = RuntimeError("cleanup failed")

    def interrupt():
        raise primary

    def fail_cleanup():
        raise cleanup

    with pytest.raises(KeyboardInterrupt, match="operator interrupt") as raised:
        orchestrator._run_reset_with_safety_cleanup(interrupt, fail_cleanup)

    assert raised.value is primary
    assert raised.value.cleanup_error is cleanup


def test_reset_fixture_rejects_existing_next_run_before_transport_or_clear(tmp_path):
    """Catch a reset mutating Launcher when its exact child bundle is unavailable."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        mutations_remaining=[],
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=True,
    )
    (tmp_path / "out" / "20260829T050619Z").mkdir()

    with pytest.raises(orchestrator.GateFailure, match="already exists"):
        orchestrator.reset_fixture(
            repo_root=tmp_path,
            profile=profile,
            next_profile=profile,
            next_profile_name="NEXT_PROFILE",
            transport=object(),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            next_run_id="20260829T050619Z",
            execute=True,
        )


def test_cli_scopes_reset_fixture_and_capture_lineage_arguments(monkeypatch, capsys):
    """Catch reset/capture lineage flags being ignored or accepted by other phases."""
    cli = _fresh_script("appwidget_stale_provider_cli")
    reset_call = {}
    capture_call = {}
    monkeypatch.setattr(cli, "AdbTransport", lambda _serial: object())

    def fake_reset(**kwargs):
        reset_call.update(kwargs)
        return {"status": "READY_FOR_CAPTURE"}

    def fake_capture(**kwargs):
        capture_call.update(kwargs)
        return {"run_id": kwargs["run_id"]}

    monkeypatch.setattr(cli, "reset_fixture", fake_reset)
    monkeypatch.setattr(cli, "capture", fake_capture)
    common = [
        "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
        "--serial", "SER",
        "--expected-model", "AT-M140",
        "--expected-fingerprint",
        cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]["fingerprint"],
    ]

    assert cli.main(
        [
            "reset-fixture",
            *common,
            "--run-id", "20260829T050618Z",
            "--next-profile", "AT_M140_BUG27084_ACCUWEATHER_V1",
            "--next-run-id", "20260829T050619Z",
            "--execute",
        ]
    ) == 0
    assert reset_call["next_profile_name"] == (
        "AT_M140_BUG27084_ACCUWEATHER_V1"
    )
    assert reset_call["next_profile"] is cli.PROFILES[
        "AT_M140_BUG27084_ACCUWEATHER_V1"
    ]
    assert reset_call["next_run_id"] == "20260829T050619Z"

    assert cli.main(
        [
            "capture",
            *common,
            "--run-id", "20260829T050619Z",
            "--after-reset-run-id", "20260829T050618Z",
        ]
    ) == 0
    assert capture_call["profile_name"] == "AT_M140_BUG27084_KNOWN_BAD_V1"
    assert capture_call["after_reset_run_id"] == "20260829T050618Z"

    assert cli.main(
        [
            "bind",
            *common,
            "--run-id", "20260829T050619Z",
            "--after-reset-run-id", "20260829T050618Z",
            "--execute",
        ]
    ) == 2
    assert "valid only with capture" in capsys.readouterr().err


def test_cli_scopes_measured_drift_campaign_arguments(monkeypatch, capsys):
    cli = _fresh_script("appwidget_stale_provider_cli")
    captured = {}
    monkeypatch.setattr(cli, "AdbTransport", lambda _serial: object())
    monkeypatch.setattr(
        cli,
        "reset_fixture",
        lambda **kwargs: captured.update(kwargs) or {"status": "READY_FOR_CAPTURE"},
    )
    common = [
        "--profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
        "--serial", "SER",
        "--expected-model", "AT-M140",
        "--expected-fingerprint",
        cli.PROFILES["AT_M140_BUG27084_KNOWN_BAD_V1"]["fingerprint"],
        "--run-id", "20260829T050618Z",
    ]

    assert cli.main(
        [
            "reset-fixture",
            *common,
            "--next-profile", "AT_M140_BUG27084_KNOWN_BAD_V1",
            "--next-run-id", "20260829T050619Z",
            "--reset-policy", "measured-drift",
            "--campaign-seed", "bug27084-known-bad-v1",
            "--campaign-blocks", "5",
            "--campaign-ordinal", "1",
            "--wake-device",
            "--execute",
        ]
    ) == 0
    assert captured["reset_policy"] == "measured-drift"
    assert captured["campaign_seed"] == "bug27084-known-bad-v1"
    assert captured["campaign_blocks"] == 5
    assert captured["campaign_ordinal"] == 1
    assert captured["wake_device"] is True

    assert cli.main(
        [
            "capture",
            *common,
            "--reset-policy", "measured-drift",
        ]
    ) == 2
    assert "valid only with reset-fixture" in capsys.readouterr().err


def test_arm_rejects_lifecycle_that_differs_from_campaign_before_device_call(
    tmp_path,
):
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    schedule = orchestrator.build_campaign_schedule("sealed-order", blocks=1)
    clean_entry = next(
        item
        for item in schedule["entries"]
        if item["lifecycle"] == "remove-widget-uninstall-reinstall"
    )
    _seed_run(
        tmp_path,
        profile,
        phase="BOUND_GENERAL",
        old_widget_id=17,
        campaign={
            "entry": clean_entry,
            "schedule": schedule,
            "schedule_sha256": schedule["schedule_sha256"],
        },
    )

    with pytest.raises(orchestrator.GateFailure, match="campaign lifecycle"):
        orchestrator.arm(
            repo_root=tmp_path,
            profile=profile,
            transport=object(),
            serial="SER",
            expected_model="AT-M140",
            expected_fingerprint="FINGERPRINT",
            run_id="20260829T050618Z",
            lifecycle="uninstall-reinstall",
            execute=True,
        )


def test_cleanup_bound_widget_reconciles_failed_clean_cell_for_retry(
    tmp_path, monkeypatch
):
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        old_widget_id=56,
        final_home_role=profile["simple_home"],
        mutations_remaining=["widget_binding:56"],
        run_complete=False,
    )
    monkeypatch.setattr(orchestrator, "preflight_identity", lambda *_a, **_k: None)

    def switch(_bundle, _transport, _serial, _profile, target, _phase, **kwargs):
        callback = kwargs.get("before_switch")
        if callback is not None:
            callback()
        return target

    def remove(*, bundle, state, old_widget_id, **_kwargs):
        orchestrator._update_mutation_ledger(
            bundle,
            state,
            remove=(f"widget_binding:{old_widget_id}",),
        )

    monkeypatch.setattr(orchestrator, "_ensure_home_role", switch)
    monkeypatch.setattr(orchestrator, "_remove_bound_widget_before_lifecycle", remove)
    monkeypatch.setattr(
        orchestrator,
        "_verify_home_role_three_way",
        lambda *_a, **_k: profile["simple_home"],
    )
    monkeypatch.setattr(
        orchestrator,
        "_record_command",
        lambda *_a, **_k: "Providers:\nWidgets:\n",
    )

    result = orchestrator.cleanup_bound_widget(
        repo_root=tmp_path,
        profile=profile,
        transport=object(),
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    assert result["current_phase"] == "RESTORED_SAFE"
    assert result["mutations_remaining"] == []
    assert state["run_complete"] is True
    assert state["final_home_role"] == profile["simple_home"]
    assert state["attempts"][-1]["kind"] == "cleanup-widget"
    assert state["attempts"][-1]["status"] == "COMPLETED"


def test_reset_cleanup_reprobes_live_simple_before_direct_fallback(
    tmp_path, monkeypatch
):
    """Catch a transient normal-path failure invoking direct recovery after Simple won."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["general_home"],
        mutations_remaining=[
            "launcher_data:cleared-uninitialized",
            "home_role:general",
            "home_role:unverified",
        ],
        run_complete=False,
        fixture_reset_status="IN_PROGRESS",
    )
    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    roles = iter([profile["general_home"], profile["simple_home"]])
    monkeypatch.setattr(
        orchestrator, "_current_role", lambda *_a, **_k: next(roles)
    )
    monkeypatch.setattr(
        orchestrator,
        "_ensure_home_role",
        lambda *_a, **_k: (_ for _ in ()).throw(
            orchestrator.GateFailure("transient post-switch check")
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "_verify_home_role_three_way",
        lambda *_a, **_k: profile["simple_home"],
    )
    monkeypatch.setattr(
        orchestrator,
        "_recover_simple_home_role_direct",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("direct recovery must not run for live Simple")
        ),
    )

    orchestrator._recover_reset_failure_to_simple(
        bundle=bundle,
        state=state,
        transport=object(),
        serial="SER",
        profile=profile,
        attempt_id="reset-fixture-0001",
        now=None,
        wait=lambda: None,
    )

    persisted = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    result = json.loads((bundle.directory / "result.json").read_text("utf-8"))
    assert persisted["final_home_role"] == profile["simple_home"]
    assert persisted["fixture_reset_status"] == "FAILED_SAFE"
    assert persisted["run_complete"] is False
    assert persisted["mutations_remaining"] == [
        "launcher_data:cleared-uninitialized"
    ]
    assert result["fixture_reset_status"] == "FAILED_SAFE"
    assert result["mutations_remaining"] == persisted["mutations_remaining"]


def test_restore_reconciles_failed_reset_by_read_only_simple_three_way(tmp_path):
    """Catch FAILED reset reconciliation re-clearing Launcher or switching HOME."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["general_home"],
        mutations_remaining=[
            "stale_launcher_record:17",
            "launcher_data:cleared-uninitialized",
            "home_role:general",
            "home_role:unverified",
        ],
        run_complete=False,
        fixture_reset_status="FAILED",
        active_attempts={},
        attempt_reconciliation_required=[],
    )
    responses = _identity_responses()
    responses.update(
        {
            (
                "shell", "cmd", "role", "get-role-holders",
                "android.app.role.HOME",
            ): f"{profile['simple_home']}\n",
            ("shell", "dumpsys", "activity", "activities"): (
                f"mResumedActivity: {profile['simple_home']}/.Home\n"
            ),
            ("exec-out", "uiautomator", "dump", "/dev/tty"): (
                _simple_home_raw()
            ),
        }
    )
    transport = _ScriptedTransport(models, responses)

    restored = orchestrator.restore(
        repo_root=tmp_path,
        profile=profile,
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        execute=True,
    )

    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    result = json.loads((bundle.directory / "result.json").read_text("utf-8"))
    assert restored["current_phase"] == "RESTORED_SAFE"
    assert restored["fixture_reset_status"] == "FAILED_SAFE"
    assert state["final_home_role"] == profile["simple_home"]
    assert state["fixture_reset_status"] == "FAILED_SAFE"
    assert state["run_complete"] is False
    assert state["mutations_remaining"] == [
        "stale_launcher_record:17",
        "launcher_data:cleared-uninitialized",
    ]
    assert state["attempts"][-1]["kind"] == "restore"
    assert state["attempts"][-1]["status"] == "COMPLETED"
    assert result["fixture_reset_status"] == "FAILED_SAFE"
    assert result["mutations_remaining"] == state["mutations_remaining"]
    assert not any(call[:3] == ("shell", "pm", "clear") for call in transport.calls)
    assert ("shell", "am", "start", "-n", profile["switch_activity"]) not in (
        transport.calls
    )
    evidence.verify_evidence_manifest(bundle.directory)


def test_launcher_binding_parser_preserves_host_id_for_drift_accounting():
    """Catch host recreation being hidden behind an unchanged host package."""
    parsers = _load_script("appwidget_stale_provider_parsers")
    transcript = """Providers:
Widgets:
  [0] id=52
    host=HostId{user:0, app:10151, hostId:1026, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:10098, cmp:ComponentInfo{com.google.android.apps.searchlite/.Widget}}
    views=RemoteViews{one}
  [1] id=53
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=null
    views=null
"""

    bindings = parsers.parse_launcher_host_bindings(
        transcript, "com.hnlens.launcher3"
    )

    assert [(item.widget_id, item.host_id) for item in bindings] == [
        (52, 1026),
        (53, 1024),
    ]


def test_campaign_schedule_is_deterministic_complete_and_content_hashed():
    """Catch hand-written order drift or cells aligning with binding accumulation."""
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")

    first = orchestrator.build_campaign_schedule("bug27084-known-bad-v1", blocks=5)
    repeated = orchestrator.build_campaign_schedule(
        "bug27084-known-bad-v1", blocks=5
    )
    different = orchestrator.build_campaign_schedule(
        "bug27084-known-bad-v2", blocks=5
    )

    assert first == repeated
    assert first["schedule_sha256"] != different["schedule_sha256"]
    assert first["algorithm"] == "sha256-cell-order-v1"
    assert len(first["entries"]) == 20
    assert [item["ordinal"] for item in first["entries"]] == list(range(1, 21))
    for block in range(1, 6):
        cells = {
            item["cell"] for item in first["entries"] if item["block"] == block
        }
        assert cells == {
            "SIMPLECLOCK_CLEAN_A",
            "SIMPLECLOCK_STALE_B",
            "ACCUWEATHER_CLEAN_A",
            "ACCUWEATHER_STALE_B",
        }
    canonical = dict(first)
    digest = canonical.pop("schedule_sha256")
    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest().upper() == digest


def test_campaign_retry_requires_same_sealed_cell_and_explicit_flag():
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    schedule = orchestrator.build_campaign_schedule("retry-seed", blocks=1)
    current = {
        "entry": schedule["entries"][0],
        "schedule": schedule,
        "schedule_sha256": schedule["schedule_sha256"],
    }

    with pytest.raises(orchestrator.GateFailure, match="retry approval"):
        orchestrator.validate_campaign_predecessor(
            current,
            current,
            campaign_retry=False,
        )

    retry = orchestrator.validate_campaign_predecessor(
        current,
        current,
        campaign_retry=True,
    )
    assert retry["retry"] is True
    assert retry["retry_of_ordinal"] == 1

    different = {
        "entry": schedule["entries"][1],
        "schedule": schedule,
        "schedule_sha256": schedule["schedule_sha256"],
    }
    with pytest.raises(orchestrator.GateFailure, match="does not precede"):
        orchestrator.validate_campaign_predecessor(
            current,
            different,
            campaign_retry=True,
        )


def test_binding_drift_summary_discloses_host_and_provider_delta():
    """Catch a non-empty reset being accepted without measurable confounders."""
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    before = (
        models.LauncherHostBinding(
            widget_id=25,
            provider_component="com.google.android.apps.searchlite/.Widget",
            host_package="com.hnlens.launcher3",
            remote_views_present=True,
            host_id=1026,
        ),
        models.LauncherHostBinding(
            widget_id=51,
            provider_component="com.accuweather.android/.Weather",
            host_package="com.hnlens.launcher3",
            remote_views_present=True,
            host_id=1024,
        ),
    )
    after = (
        models.LauncherHostBinding(
            widget_id=25,
            provider_component="com.google.android.apps.searchlite/.Widget",
            host_package="com.hnlens.launcher3",
            remote_views_present=True,
            host_id=1026,
        ),
        models.LauncherHostBinding(
            widget_id=53,
            provider_component="com.google.android.apps.searchlite/.Widget",
            host_package="com.hnlens.launcher3",
            remote_views_present=True,
            host_id=1024,
        ),
    )

    drift = orchestrator.summarize_launcher_binding_drift(
        before,
        after,
        target_provider="com.accuweather.android/.Weather",
    )

    assert drift["before_widget_ids"] == [25, 51]
    assert drift["after_widget_ids"] == [25, 53]
    assert drift["retained_widget_ids"] == [25]
    assert drift["added_widget_ids"] == [53]
    assert drift["removed_widget_ids"] == [51]
    assert drift["before_host_sizes"] == [
        {"host_id": 1024, "widgets_size": 1},
        {"host_id": 1026, "widgets_size": 1},
    ]
    assert drift["after_host_sizes"] == [
        {"host_id": 1024, "widgets_size": 1},
        {"host_id": 1026, "widgets_size": 1},
    ]
    assert drift["target_provider_before_widget_ids"] == [51]
    assert drift["target_provider_after_widget_ids"] == []


def test_measured_drift_policy_rejects_target_or_unbounded_provider_growth():
    models = _load_script("appwidget_stale_provider_models")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")

    def binding(widget_id, provider, host_id=1026):
        return models.LauncherHostBinding(
            widget_id=widget_id,
            provider_component=provider,
            host_package="com.hnlens.launcher3",
            remote_views_present=True,
            host_id=host_id,
        )

    search = "com.google.android.apps.searchlite/.Widget"
    target = "com.accuweather.android/.Weather"
    before = (binding(25, search), binding(51, target, 1024))

    with pytest.raises(orchestrator.GateFailure, match="target provider"):
        orchestrator.validate_measured_launcher_binding_drift(
            before,
            (binding(25, search), binding(53, target, 1024)),
            target_provider=target,
        )

    with pytest.raises(orchestrator.GateFailure, match="new provider"):
        orchestrator.validate_measured_launcher_binding_drift(
            before,
            (binding(25, search), binding(53, "com.unknown/.Widget", 1024)),
            target_provider=target,
        )

    with pytest.raises(orchestrator.GateFailure, match=r"\+1 reset envelope"):
        orchestrator.validate_measured_launcher_binding_drift(
            before,
            (
                binding(25, search),
                binding(52, search),
                binding(53, search, 1024),
                binding(54, search, 1024),
            ),
            target_provider=target,
        )


def test_measured_drift_reset_reconciles_failed_strict_pilot_and_pins_campaign(
    tmp_path,
):
    """Catch the executable fallback losing drift, crash, or schedule evidence."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    profile = _capture_profile_and_repo(tmp_path)
    bundle = _seed_run(
        tmp_path,
        profile,
        phase="RESTORED_SAFE",
        final_home_role=profile["simple_home"],
        completed_phases=["BASELINE_CAPTURED", "RESTORED_SAFE"],
        mutations_remaining=["launcher_data:cleared-uninitialized"],
        active_attempts={},
        attempt_reconciliation_required=[],
        run_complete=False,
        fixture_reset_status="FAILED_SAFE",
    )
    responses = _reset_fixture_responses(profile)
    before = f"""Providers:
Widgets:
  [0] id=25
    host=HostId{{user:0, app:10151, hostId:1026, pkg:com.hnlens.launcher3}}
    provider=ProviderId{{user:0, app:10098, cmp:ComponentInfo{{com.google.android.apps.searchlite/.Widget}}}}
    views=RemoteViews{{one}}
  [1] id=51
    host=HostId{{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}}
    provider=ProviderId{{user:0, app:10205, cmp:ComponentInfo{{{profile['app']['provider']}}}}}
    views=RemoteViews{{weather}}
"""
    evidence.write_evidence_artifact(
        bundle.directory,
        "snapshots/appwidget_baseline.txt",
        before.encode("utf-8"),
    )
    residual = """Providers:
Widgets:
  [0] id=25
    host=HostId{user:0, app:10151, hostId:1026, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:10098, cmp:ComponentInfo{com.google.android.apps.searchlite/.Widget}}
    views=RemoteViews{one}
  [1] id=53
    host=HostId{user:0, app:10151, hostId:1024, pkg:com.hnlens.launcher3}
    provider=ProviderId{user:0, app:10098, cmp:ComponentInfo{com.google.android.apps.searchlite/.Widget}}
    views=RemoteViews{two}
"""
    responses[("shell", "dumpsys", "appwidget")] = [
        before,
        residual,
        residual,
    ]
    crash_key = ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime")
    exit_key = (
        "shell", "dumpsys", "activity", "exit-info", profile["launcher_package"]
    )
    boot_key = ("shell", "cat", "/proc/sys/kernel/random/boot_id")
    responses[crash_key] = ["old crash baseline\n", "old crash baseline\n"]
    responses[exit_key] = ["old exit baseline\n", "old exit baseline\n"]
    responses[boot_key] = ["BOOT-A\n", "BOOT-A\n"]
    responses[("shell", "input", "keyevent", "KEYCODE_WAKEUP")] = ""
    responses[("shell", "input", "keyevent", "KEYCODE_HOME")] = ""
    transport = _ScriptedTransport(models, responses)
    schedule = orchestrator.build_campaign_schedule(
        "bug27084-known-bad-v1", blocks=5
    )
    first = schedule["entries"][0]

    reset = orchestrator.reset_fixture(
        repo_root=tmp_path,
        profile=profile,
        next_profile=profile,
        next_profile_name=first["profile_name"],
        transport=transport,
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050618Z",
        next_run_id="20260829T050619Z",
        execute=True,
        reset_policy="measured-drift",
        campaign_seed="bug27084-known-bad-v1",
        campaign_blocks=5,
        campaign_ordinal=1,
        wake_device=True,
        wait=lambda: None,
    )

    receipt = json.loads(
        (bundle.directory / "fixture_reset.json").read_text("utf-8")
    )
    state = json.loads((bundle.directory / "run.json").read_text("utf-8"))
    assert reset["status"] == "READY_FOR_CAPTURE"
    assert receipt["reset_policy"] == "measured-drift"
    assert receipt["campaign"]["schedule_sha256"] == schedule["schedule_sha256"]
    assert receipt["campaign"]["entry"] == first
    assert receipt["binding_drift"]["after_widget_ids"] == [25, 53]
    assert receipt["binding_drift"]["target_provider_after_widget_ids"] == []
    assert receipt["clean_init_crash_signature_count"] == 0
    assert receipt["clean_init_launcher_crash_exit_count"] == 0
    assert state["run_complete"] is True
    assert state["mutations_remaining"] == []
    assert state["fixture_reset_status"] == "READY_FOR_CAPTURE"
    assert transport.calls.index(
        ("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    ) < transport.calls.index(
        ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME")
    )
    evidence.verify_evidence_manifest(bundle.directory)

    child = orchestrator.capture(
        repo_root=tmp_path,
        profile=profile,
        profile_name=first["profile_name"],
        transport=_ScriptedTransport(models, _capture_responses(profile)),
        serial="SER",
        expected_model="AT-M140",
        expected_fingerprint="FINGERPRINT",
        run_id="20260829T050619Z",
        after_reset_run_id="20260829T050618Z",
    )
    child_state = json.loads(
        (tmp_path / "out" / child["run_id"] / "run.json").read_text("utf-8")
    )
    assert child_state["campaign"]["schedule_sha256"] == schedule[
        "schedule_sha256"
    ]
    assert child_state["campaign"]["entry"] == first


def test_boot_poll_retries_transient_offline_with_condition_wait(tmp_path):
    """Catch reboot polling that aborts on the first transient nonzero result."""
    models = _load_script("appwidget_stale_provider_models")
    evidence = _load_script("appwidget_stale_provider_evidence")
    orchestrator = _load_script("appwidget_stale_provider_orchestrator")
    bundle = evidence.EvidenceBundle.create(tmp_path / "out", "20260829T050618Z")
    key = ("shell", "getprop", "sys.boot_completed")
    responses = {
        key: [
            models.CommandResult(
                ("adb", "-s", "SER", *key),
                1,
                "",
                "error: device offline",
            ),
            "1\n",
        ]
    }
    transport = _ScriptedTransport(models, responses)
    waits = []

    orchestrator._wait_for_boot_complete(
        bundle,
        transport,
        "SER",
        "arm",
        poll_attempts=3,
        poll_timeout_s=30.0,
        poll_interval_s=1.0,
        wait=lambda: waits.append("tick"),
    )

    assert transport.calls.count(key) == 2
    assert waits == ["tick"]
