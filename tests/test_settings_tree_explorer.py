"""Tests for scripts/settings_tree_explorer.py (stub-ADB, OFFLINE).

Task 6: GuardedADB read-only / navigation-safe command allowlist.
The real `adb` is NEVER invoked — only the in-memory StubADB below.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "settings_tree_explorer.py"
_spec = importlib.util.spec_from_file_location("settings_tree_explorer", _PATH)
ste = importlib.util.module_from_spec(_spec)
sys.modules["settings_tree_explorer"] = ste
_spec.loader.exec_module(ste)

from src import menu_anchor as ma  # noqa: E402  (repo root on sys.path after ste load)

_GATE_PATH = _ROOT / "tools" / "redaction_gate.py"
_gspec = importlib.util.spec_from_file_location("redaction_gate", _GATE_PATH)
rg = importlib.util.module_from_spec(_gspec)
sys.modules["redaction_gate"] = rg
_gspec.loader.exec_module(rg)


class StubADB:
    """Records every shell/op; returns scripted focus + dump per call. NEVER real adb."""

    def __init__(self, focus_seq=None, dump_seq=None, props=None):
        self.calls: list[str] = []
        self._focus_seq = list(focus_seq or [])
        self._dump_seq = list(dump_seq or [])
        self._props = props or {}

    def shell(self, command: str, timeout: int = 10) -> str:
        self.calls.append(command)
        if command.startswith("dumpsys window"):
            return self._focus_seq.pop(0) if self._focus_seq else ""
        if command.startswith("cat "):
            return self._dump_seq.pop(0) if self._dump_seq else ""
        if command.startswith("getprop"):
            key = command.split(" ", 1)[1].strip()
            return self._props.get(key, "")
        return ""

    def swipe(self, x1, y1, x2, y2, duration=300):
        self.calls.append(f"input swipe {x1} {y1} {x2} {y2} {duration}")

    def key(self, keycode: str):
        self.calls.append(f"input keyevent {keycode}")

    def device_serial(self):
        return self._props.get("__serial__")


def test_guarded_adb_blocks_tap_and_forbidden_keys():
    g = ste.GuardedADB(StubADB())
    with pytest.raises(ste.CommandNotAllowed):
        g.raw_shell("input tap 100 200")
    # Only HOME/BACK navigation keys allowed; everything else (incl. numeric) denied.
    for badkey in ["KEYCODE_POWER", "KEYCODE_ENTER", "KEYCODE_DPAD_CENTER", "66", "23", "26"]:
        with pytest.raises(ste.CommandNotAllowed):
            g.key(badkey)


def test_guarded_adb_blocks_device_mutations_and_passthrough():
    g = ste.GuardedADB(StubADB())
    forbidden = [
        "input text hello",
        "settings put system x 1",
        "pm clear com.android.settings",
        "pm uninstall com.foo",
        "pm install /sdcard/x.apk",
        "am force-stop com.android.settings",
        "rm -f /sdcard/ui_dump.xml",
        "mv /sdcard/a /sdcard/b",
        "cp /sdcard/a /sdcard/b",
        "monkey -p com.android.settings 1",
        "reboot",
    ]
    for cmd in forbidden:
        with pytest.raises(ste.CommandNotAllowed):
            g.raw_shell(cmd)
    assert g.violations == len(forbidden)


def test_guarded_adb_allows_readonly_ops_and_logs_them():
    stub = StubADB(focus_seq=["mCurrentFocus=Window{x u0 com.android.settings/com.android.settings.Settings}"])
    g = ste.GuardedADB(stub)
    g.launch_action("android.settings.WIFI_SETTINGS")
    g.launch_component("com.android.settings/.Settings$MyDeviceInfoActivity")
    g.scroll_up(240, 600, 240, 200)
    g.home()
    g.back()
    g.getprop("ro.serialno")
    g.current_focus()
    # Every recorded command must match the read-only allowlist.
    assert all(ste.is_allowed_command(c) for c in g.command_log)
    assert g.violations == 0


def test_force_stop_blocked_by_default_but_gated_when_enabled():
    g = ste.GuardedADB(StubADB())
    with pytest.raises(ste.CommandNotAllowed):
        g.force_stop_settings()                 # default off
    # raw_shell can never reach force-stop either:
    with pytest.raises(ste.CommandNotAllowed):
        g.raw_shell("am force-stop com.android.settings")
    g2 = ste.GuardedADB(StubADB(), allow_force_stop=True)
    g2.force_stop_settings()                    # opt-in gate, no raise
    assert "am force-stop com.android.settings" in g2.command_log


def test_blocked_exception_message_has_command_and_reason():
    g = ste.GuardedADB(StubADB())
    with pytest.raises(ste.CommandNotAllowed) as ei:
        g.raw_shell("input tap 5 5")
    msg = str(ei.value)
    assert "input tap 5 5" in msg and "reason" in msg.lower()


def test_home_and_back_are_the_only_allowed_keys():
    assert ste.is_allowed_command("input keyevent KEYCODE_HOME")
    assert ste.is_allowed_command("input keyevent KEYCODE_BACK")
    assert not ste.is_allowed_command("input keyevent KEYCODE_ENTER")
    assert not ste.is_allowed_command("input keyevent 66")
    assert not ste.is_allowed_command("input keyevent KEYCODE_DPAD_CENTER")


# --- Task 7: per-screen reach classification + dump/parse -----------------
_WIFI_FOCUS = "mCurrentFocus=Window{a u0 com.android.settings/com.android.settings.Settings$WifiSettingsActivity}"
_EXT_FOCUS = "mCurrentFocus=Window{a u0 com.google.android.apps.wellbeing/.settings.SettingsActivity}"
_HOME_FOCUS = "mCurrentFocus=Window{a u0 com.hnlens.simplemode/.ui.home.MainActivity}"
_DUMP = """<?xml version='1.0'?><hierarchy><node class="android.widget.TextView" text="Wi-Fi"
 resource-id="android:id/title" clickable="true" focusable="true" checkable="false" bounds="[0,0][480,80]"/></hierarchy>"""


def _seed_screen(**over):
    base = {"id": "settings_d1_wifi", "label_ko": "Wi-Fi", "nav_path": ["설정", "Wi-Fi"],
            "entry": {"action": "android.settings.WIFI_SETTINGS"},
            "expect_activity_regex": "WifiSettingsActivity"}
    base.update(over)
    return base


def test_explore_screen_reached_internal():
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "REACHED" and sc.reach_kind == "internal"
    assert sc.activity_match is True and sc.fingerprint
    assert "Wi-Fi" in sc.observed_texts["en"]
    assert g.violations == 0


def test_explore_screen_external_package_is_not_failure():
    g = ste.GuardedADB(StubADB(focus_seq=[_EXT_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(id="settings_d1_wellbeing",
        entry={"component": "com.google.android.apps.wellbeing/.settings.SettingsActivity"},
        expect_activity_regex="wellbeing"), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "REACHED_EXTERNAL_PACKAGE" and sc.reach_kind == "external"


def test_explore_screen_focus_mismatch():
    # simplemode IS in ALLOWLIST_PACKAGES, but we expected WifiSettingsActivity ->
    # unexpected landing must be FOCUS_MISMATCH, NOT external routing.
    g = ste.GuardedADB(StubADB(focus_seq=[_HOME_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "FOCUS_MISMATCH" and sc.reach_kind is None


def test_explore_screen_unreachable_no_action():
    g = ste.GuardedADB(StubADB())
    sc = ste.explore_screen(g, _seed_screen(entry={}), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "UNREACHABLE_NO_ACTION"


def test_explore_screen_dump_rejected_nullable():
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[""]))  # empty dump
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "DUMP_REJECTED" and sc.reach_kind == "internal"
    assert sc.fingerprint is None and sc.elements == [] and sc.raw_dump_ref is None
    assert sc.dump_info.raw_present is False


# --- Task 8: read-only scroll sweep ---------------------------------------
def _dump_with(texts):
    nodes = "".join(
        f'<node class="android.widget.TextView" text="{t}" resource-id="android:id/title"'
        f' clickable="true" focusable="true" checkable="false" bounds="[0,0][480,80]"/>' for t in texts)
    return f"<?xml version='1.0'?><hierarchy>{nodes}</hierarchy>"


def test_scroll_terminates_on_no_new():
    # pass1 reveals A,B; nothing new -> terminate no_new at 1 sweep
    stub = StubADB(dump_seq=[_dump_with(["A", "B"])])
    g = ste.GuardedADB(stub)
    seed_els = ste._elements_from_xml(_dump_with(["A", "B"]))
    scroll, merged = ste._scroll_sweep(g, list(seed_els), max_passes=8)
    assert scroll.terminated == "no_new"
    assert scroll.passes >= 1
    assert {e.label for e in merged} == {"A", "B"}


def test_scroll_merges_new_then_stops():
    stub = StubADB(dump_seq=[_dump_with(["A", "B", "C"]), _dump_with(["A", "B", "C"])])
    g = ste.GuardedADB(stub)
    seed_els = ste._elements_from_xml(_dump_with(["A", "B"]))
    scroll, merged = ste._scroll_sweep(g, list(seed_els), max_passes=8)
    assert "C" in {e.label for e in merged}
    assert scroll.new_texts_per_pass[0] == 1  # added C on first sweep
    assert any(s["dir"] == "up" for s in scroll.swipes)
    # merged keeps full MenuElement (kind/risk/source_class preserved, not just text)
    c = next(e for e in merged if e.label == "C")
    assert c.kind == "menu_row" and c.risk == "none" and c.source_class == "android.widget.TextView"


def test_scroll_respects_max_passes():
    # every sweep yields a brand-new label -> never converges -> stop at max_passes
    seq = [_dump_with([f"L{i}"]) for i in range(20)]
    g = ste.GuardedADB(StubADB(dump_seq=seq))
    scroll, merged = ste._scroll_sweep(g, [], max_passes=3)
    assert scroll.terminated == "max_passes" and scroll.passes == 3


def test_scroll_uses_only_readonly_commands():
    stub = StubADB(dump_seq=[_dump_with(["A", "B", "C"]), _dump_with(["A", "B", "C"])])
    g = ste.GuardedADB(stub)
    seed_els = ste._elements_from_xml(_dump_with(["A", "B"]))
    ste._scroll_sweep(g, list(seed_els), max_passes=8)
    assert g.violations == 0
    assert all(ste.is_allowed_command(c) for c in g.command_log)
    assert not any(c.startswith("input tap") for c in g.command_log)
    assert not any("keyevent" in c for c in g.command_log)   # scroll never uses keys


# --- Task 9: orchestration + device baseline + emit + CLI ------------------
_PROPS = {
    "ro.product.model": "AT-M140", "ro.product.name": "alt_thor2", "ro.product.device": "thor2",
    "ro.build.fingerprint": "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys",
    "ro.build.id": "RY07260302M", "ro.build.version.release": "14",
    "persist.sys.locale": "ko-KR", "ro.product.locale": "en-US",
    "__serial__": "B06201249E0002B8",
}


def _full_seed(screens=None):
    return {"seed_version": 1, "locale": "ko-KR", "target_serial": "B06201249E0002B8",
            "source_menu_tree": "x", "package": "com.android.settings",
            "screens": screens if screens is not None else [_seed_screen()]}


def test_capture_device_baseline():
    g = ste.GuardedADB(StubADB(props=_PROPS))
    dev = ste.capture_device_baseline(g, serial="B06201249E0002B8")
    assert dev.model == "AT-M140" and dev.build_id == "RY07260302M"
    assert dev.locale_persist == "ko-KR" and dev.serial == "B06201249E0002B8"


def test_target_mismatch_aborts_without_flag():
    stub = StubADB(props={"__serial__": "WRONGSERIAL"})
    with pytest.raises(ste.TargetMismatch):
        ste.preflight_serial(stub, target="B06201249E0002B8", allow_mismatch=False)


def test_target_mismatch_acknowledged_with_flag():
    stub = StubADB(props={"__serial__": "WRONGSERIAL"})
    ack = ste.preflight_serial(stub, target="B06201249E0002B8", allow_mismatch=True)
    assert ack is True


def test_run_explore_builds_baseline_and_allowlist_clean(tmp_path):
    stub = StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS)
    g = ste.GuardedADB(stub)
    baseline = ste.run_explore(g, _full_seed(), run_id="20260602T000000Z",
                               out_dir=str(tmp_path), settle=0, max_passes=1,
                               target_mismatch_ack=False)
    assert baseline.summary["screen_count"] == 1
    assert baseline.summary["reached"] == 1
    assert g.violations == 0                        # read-only invariant
    assert all(ste.is_allowed_command(c) for c in g.command_log)
    out_json = tmp_path / "menu_tree_baseline_20260602T000000Z.json"
    out_md = tmp_path / "menu_tree_baseline_20260602T000000Z.md"
    assert out_json.exists() and out_md.exists()
    import json
    d = json.loads(out_json.read_text(encoding="utf-8"))
    assert d["device"]["serial"] == "B06201249E0002B8"
    assert d["schema_version"] == 1


def test_run_explore_refuses_overwrite(tmp_path):
    seed = _full_seed()
    g1 = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g1, seed, run_id="20260602T000000Z", out_dir=str(tmp_path),
                    settle=0, max_passes=1, target_mismatch_ack=False)
    g2 = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    with pytest.raises(FileExistsError):
        ste.run_explore(g2, seed, run_id="20260602T000000Z", out_dir=str(tmp_path),
                        settle=0, max_passes=1, target_mismatch_ack=False)
    assert g2.command_log == []   # fail-fast: no device interaction before overwrite check


def test_target_mismatch_ack_recorded_in_json(tmp_path):
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g, _full_seed(), run_id="20260602T000009Z", out_dir=str(tmp_path),
                    settle=0, max_passes=1, target_mismatch_ack=True)
    import json
    d = json.loads((tmp_path / "menu_tree_baseline_20260602T000009Z.json").read_text(encoding="utf-8"))
    assert d["target_mismatch_ack"] is True


def test_one_screen_failure_does_not_abort_run(tmp_path):
    bad = _seed_screen(id="settings_bad", entry={})       # -> UNREACHABLE_NO_ACTION
    good = _seed_screen(id="settings_d1_wifi")            # -> REACHED
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    baseline = ste.run_explore(g, _full_seed([bad, good]), run_id="20260602T000010Z",
                               out_dir=str(tmp_path), settle=0, max_passes=1,
                               target_mismatch_ack=False)
    statuses = {s.screen_id: s.reach_status for s in baseline.screens}
    assert statuses["settings_bad"] == "UNREACHABLE_NO_ACTION"
    assert statuses["settings_d1_wifi"] == "REACHED"
    assert baseline.summary["screen_count"] == 2


def test_dry_run_makes_no_device_calls():
    seed = {"screens": [_seed_screen()], "target_serial": "B06201249E0002B8"}
    plan = ste.dry_run_plan(seed)
    assert "settings_d1_wifi" in plan and "am start -a android.settings.WIFI_SETTINGS" in plan


def test_run_id_format_matches_pattern():
    import re as _re
    rid = ste._now_run_id()
    assert _re.match(r"^\d{8}T\d{6}Z$", rid), rid


# --- v1.1: component `$` preservation (launch fidelity) -------------------
# Class A FOCUS_MISMATCH root cause: `am start -n .../Settings$MyDeviceInfoActivity`
# had `$MyDeviceInfoActivity` expanded to empty by the *device* shell, so the
# launch collapsed to base `.../Settings` (google + device_info landed on the
# identical base focus). Fix = single-quote the component so the device sh
# treats `$` literally; the component is pattern-validated first so the quoting
# cannot be broken out of (quote / `;` / space / substitution injection).

def test_build_component_command_quotes_dollar_alias():
    cmd = ste.build_component_command("com.android.settings/.Settings$MyDeviceInfoActivity")
    assert cmd == "am start -n 'com.android.settings/.Settings$MyDeviceInfoActivity'"
    assert ste.is_allowed_command(cmd)


def test_build_component_command_rejects_injection():
    for bad in [
        "com.x/.Y'; reboot #",     # break out of single quotes
        "com.x/.Y;reboot",         # command separator
        "com.x/.Y rm -rf /",       # whitespace -> extra args
        "com.x/.Y$(reboot)",       # command substitution
        "com.x/.Y`id`",            # backtick substitution
        "com.x",                   # missing '/activity' form
    ]:
        with pytest.raises(ste.CommandNotAllowed):
            ste.build_component_command(bad)


def test_launch_component_preserves_dollar_and_stays_allowlisted():
    g = ste.GuardedADB(StubADB())
    g.launch_component("com.android.settings/.Settings$AccountDashboardActivity")
    sent = g.command_log[-1]
    assert sent == "am start -n 'com.android.settings/.Settings$AccountDashboardActivity'"
    assert "$AccountDashboardActivity" in sent          # alias NOT stripped by device sh
    assert ste.is_allowed_command(sent)
    assert g.violations == 0


def test_launch_component_injection_never_reaches_device():
    g = ste.GuardedADB(StubADB())
    with pytest.raises(ste.CommandNotAllowed):
        g.launch_component("com.android.settings/.X'; reboot #")
    # the dangerous string must never appear in the command log (rejected pre-shell)
    assert not any("reboot" in c for c in g.command_log)


def test_allowlist_rejects_unquoted_dollar_component():
    # the buggy unquoted form (device-shell expands `$Xxx`) is no longer accepted
    assert not ste.is_allowed_command(
        "am start -n com.android.settings/.Settings$MyDeviceInfoActivity")
    # the safe single-quoted form is accepted
    assert ste.is_allowed_command(
        "am start -n 'com.android.settings/.Settings$MyDeviceInfoActivity'")


# --- Task 4.2 wiring: orchestration-seam redaction (JSON + MD) -------------
# menu_tree.to_md() bypasses to_dict() and reads dataclass fields directly
# (element labels), so redacting only the JSON dict would leave PII plaintext in
# the MD. The seam must redact BOTH outputs with one shared per-run KeyMap.
# menu_tree stays pure (no redaction import); redaction is orchestration-owned.

_FULL_FP = "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys"


def _pii_baseline(run_id="20260608T000000Z"):
    mt = ste.mt  # menu_tree, bound by the explorer (`from src import menu_tree as mt`)
    el = mt.MenuElement(
        label="IP 주소 192.0.0.4", resource_id=None, kind="title",
        source_class="android.widget.TextView", text_role_hint="unknown",
        clickable=False, focusable=False, checkable=False, risk="none", bounds=None)
    screen = mt.MenuScreen(
        screen_id="settings_d1_device_info", label_ko="휴대전화 정보",
        nav_path=["설정", "휴대전화 정보"],
        entry={"action": "android.settings.DEVICE_INFO_SETTINGS"},
        reach_status="REACHED", reach_kind="internal",
        observed_focus="com.android.settings/.Settings$MyDeviceInfoActivity",
        expect_activity_regex=".*", activity_match=True, fingerprint="fp",
        observed_texts={"ko": ["IP 주소 192.0.0.4"], "en": [], "other": []},
        elements=[el], scroll=mt.ScrollInfo(),
        dump_info=mt.DumpInfo(raw_present=True), risk_flags=[], raw_dump_ref=None)
    device = mt.DeviceBaseline(
        serial="B06201249E0002F0", model="AT-M140", product="alt_thor2", device="thor2",
        build_fingerprint=_FULL_FP, build_id="Z0604U", android="14",
        locale_persist="ko-KR", locale_product="en-US",
        viewport="480x800", dpi="220", sim="45005")
    return mt.MenuTreeBaseline(
        schema_version=mt.SCHEMA_VERSION, tool_version=mt.TOOL_VERSION,
        generated_at_utc="2026-06-08T00:00:00Z", run_id=run_id, device=device,
        package="com.android.settings", seed_ref={}, target_mismatch_ack=False,
        summary=mt.compute_summary([screen]), screens=[screen])


def test_emit_redacted_baseline_redacts_json_and_md_with_shared_tokens(tmp_path):
    base = str(tmp_path / "menu_tree_baseline_20260608T000000Z")
    json_str, md_str, km = ste.emit_redacted_baseline(_pii_baseline(), base)
    # JSON: no plaintext PII; full build fingerprint tokenized; short build id kept.
    assert "192.0.0.4" not in json_str
    assert "RY07260302M:user/release-keys" not in json_str
    assert "Z0604U" in json_str
    # MD: the to_md() bypass must ALSO be redacted (the critical leak guard).
    assert "192.0.0.4" not in md_str
    # token consistency: the same IP value -> the same token in BOTH artifacts.
    assert "<IPV4_1>" in json_str and "<IPV4_1>" in md_str
    # both files written
    assert (tmp_path / "menu_tree_baseline_20260608T000000Z.json").exists()
    assert (tmp_path / "menu_tree_baseline_20260608T000000Z.md").exists()


def test_run_explore_emits_redacted_fingerprint(tmp_path):
    # run_explore must route its emit through the redaction seam: the full build
    # fingerprint (from _PROPS) is tokenized, the short build id kept.
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g, _full_seed(), run_id="20260608T010101Z",
                    out_dir=str(tmp_path), settle=0, max_passes=1,
                    target_mismatch_ack=False)
    out_json = (tmp_path / "menu_tree_baseline_20260608T010101Z.json").read_text(encoding="utf-8")
    assert "RY07260302M:user/release-keys" not in out_json   # full fingerprint tokenized
    assert "<BUILD_FP_1>" in out_json
    assert '"serial": "B06201249E0002B8"' in out_json         # serial kept (not in policy)


# --- Task 4.2 T2: per-run KeyMap dump = local carry only, commit-forbidden ---
# The run's KeyMap (original -> token map) is dumped beside the raw XML at
# raw/<run_id>/_redaction_keymap.json. It holds plaintext PII so it is local
# carry only: path_policy_findings flags it as commit-forbidden. The redacted
# baseline JSON/MD (commit candidates) must carry no residual PII.

def test_run_explore_dumps_keymap_as_local_carry(tmp_path):
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g, _full_seed(), run_id="20260608T020202Z",
                    out_dir=str(tmp_path), settle=0, max_passes=1)
    km_path = tmp_path / "raw" / "20260608T020202Z" / "_redaction_keymap.json"
    assert km_path.exists()                                   # dumped beside raw XML
    data = json.loads(km_path.read_text(encoding="utf-8"))
    fp = _PROPS["ro.build.fingerprint"]
    # original -> token mapping present (the full fingerprint was tokenized)
    assert data["by_kind"]["BUILD_FP"][fp] == "<BUILD_FP_1>"
    # roundtrip: same original -> same token after from_dict
    km2 = ste.rd.KeyMap.from_dict(data)
    assert km2.token_for("BUILD_FP", fp) == "<BUILD_FP_1>"


def test_dumped_keymap_path_is_commit_forbidden(tmp_path):
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g, _full_seed(), run_id="20260608T030303Z",
                    out_dir=str(tmp_path), settle=0, max_passes=1)
    km_path = tmp_path / "raw" / "20260608T030303Z" / "_redaction_keymap.json"
    findings = ste.rd.path_policy_findings([str(km_path)])
    assert findings and any(f.kind == "PATH_POLICY" for f in findings)


def test_run_explore_output_passes_residual_scan(tmp_path):
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS))
    ste.run_explore(g, _full_seed(), run_id="20260608T040404Z",
                    out_dir=str(tmp_path), settle=0, max_passes=1)
    out_json = tmp_path / "menu_tree_baseline_20260608T040404Z.json"
    out_md = tmp_path / "menu_tree_baseline_20260608T040404Z.md"
    assert ste.rd.residual_scan(json.loads(out_json.read_text(encoding="utf-8"))) == []
    assert ste.rd.residual_scan(out_md.read_text(encoding="utf-8")) == []


# --- Task 4.2 T3: probe sidecar redaction (scan-before-write) --------------
# emit_redacted_probe is a thin orchestration wrapper over an issue-probe sidecar:
# redact(probe.to_dict(), run_keymap) -> residual_scan -> write JSON only if clean.
# Scan-before-write: a residual finding raises BEFORE any file is written, so no
# plaintext PII ever lands on disk. write_probe_json's contract is left intact.

def _pii_probe(observed="IP 주소 192.0.0.4 / MAC 9c:1e:ce:0c:36:e0"):
    return ma.IssueProbePoint(
        issue_id="BTS-X", probe_id="p1", source_runs=["20260608T020202Z"],
        screen_id="settings_d1_device_info", domain="settings",
        entry_action="android.settings.DEVICE_INFO_SETTINGS", entry_component=None,
        observed_condition=observed,
        hypothesis="IMEI: 350000000000001 leaks into the sidecar",
        trials_summary=ma.make_trials_summary(20, 20, 0),
        verdict="not_regression",
        evidence_refs={"ledger_path": "x", "artifact_paths": []},
        notes="APN password=secret123 개통일 2024-10-10")


def test_emit_redacted_probe_tokenizes_network_and_identity(tmp_path):
    path = str(tmp_path / "probes" / "bts_x.json")
    redacted = ste.emit_redacted_probe(_pii_probe(), path, ste.rd.KeyMap())
    text = Path(path).read_text(encoding="utf-8")
    for plain in ("192.0.0.4", "9c:1e:ce:0c:36:e0", "350000000000001"):
        assert plain not in text, plain
    assert "<IPV4_1>" in text and "<MAC_1>" in text and "<IMEI_1>" in text
    assert ste.rd.residual_scan(redacted) == []


def test_emit_redacted_probe_drops_dclass_and_keeps_it_out_of_keymap(tmp_path):
    path = str(tmp_path / "probes" / "bts_d.json")
    km = ste.rd.KeyMap()
    ste.emit_redacted_probe(_pii_probe(), path, km)
    text = Path(path).read_text(encoding="utf-8")
    assert "secret123" not in text and "2024-10-10" not in text
    assert "<REDACTED:apn_password>" in text and "<REDACTED:first_call_date>" in text
    # D-class never enters the KeyMap (drop = no correlation token)
    assert "APN_CRED" not in km.to_dict()["by_kind"]
    assert "secret123" not in json.dumps(km.to_dict())


def test_emit_redacted_probe_scans_before_write(tmp_path, monkeypatch):
    # If residual_scan reports a finding, the writer must raise BEFORE writing —
    # no plaintext file may be left on disk.
    path = str(tmp_path / "probes" / "bts_block.json")
    fake = [ste.rd.Finding("IPV4", "residual", "$", "leak")]
    monkeypatch.setattr(ste.rd, "residual_scan", lambda obj: fake)
    with pytest.raises(ste.ResidualPIIError):
        ste.emit_redacted_probe(_pii_probe(), path, ste.rd.KeyMap())
    assert not Path(path).exists()


def test_probe_and_baseline_share_tokens_via_one_keymap(tmp_path):
    km = ste.rd.KeyMap()
    ste.emit_redacted_baseline(_pii_baseline(), str(tmp_path / "b"), keymap=km)  # IP -> <IPV4_1>
    path = str(tmp_path / "probes" / "p.json")
    ste.emit_redacted_probe(_pii_probe(), path, km)        # same IP reuses the token
    text = Path(path).read_text(encoding="utf-8")
    assert "192.0.0.4" not in text and "<IPV4_1>" in text


def test_emit_redacted_probe_fresh_keymap_restarts_numbering(tmp_path):
    path = str(tmp_path / "probes" / "p2.json")
    ste.emit_redacted_probe(_pii_probe(), path, ste.rd.KeyMap())   # fresh namespace
    text = Path(path).read_text(encoding="utf-8")
    assert "<IPV4_1>" in text


def test_probe_paths_are_commit_candidates_not_forbidden():
    for p in ["THOR2_K - Settings/catalog/probes/bts_x.json",
              "THOR2_K - Settings/catalog/anchors/debugscreen.json"]:
        assert ste.rd.path_policy_findings([p]) == []


def test_emit_redacted_probe_does_not_write_raw_or_keymap(tmp_path):
    path = str(tmp_path / "probes" / "p3.json")
    ste.emit_redacted_probe(_pii_probe(), path, ste.rd.KeyMap())
    assert Path(path).exists()
    assert not (tmp_path / "raw").exists()                      # probe writer touches no raw dir
    assert not list(tmp_path.rglob("_redaction_keymap.json"))   # and dumps no keymap


def test_emit_redacted_probe_rejects_raw_dir_output(tmp_path):
    # A forbidden output path (a raw/ capture dir) is refused BEFORE any write —
    # not merely "the writer doesn't choose it", but it rejects the argument.
    bad = str(tmp_path / "catalog" / "raw" / "20260608T020202Z" / "x.json")
    with pytest.raises(ste.ForbiddenProbePathError):
        ste.emit_redacted_probe(_pii_probe(), bad, ste.rd.KeyMap())
    assert not Path(bad).exists()


def test_emit_redacted_probe_rejects_keymap_output(tmp_path):
    bad = str(tmp_path / "anchors" / "_redaction_keymap.json")
    with pytest.raises(ste.ForbiddenProbePathError):
        ste.emit_redacted_probe(_pii_probe(), bad, ste.rd.KeyMap())
    assert not Path(bad).exists()


@pytest.mark.parametrize("good", ["anchors/debugscreen.json", "probes/bts_x.json"])
def test_emit_redacted_probe_allows_anchors_and_probes_output(tmp_path, good):
    p = str(tmp_path / good)
    ste.emit_redacted_probe(_pii_probe(), p, ste.rd.KeyMap())
    assert Path(p).exists()


# --- Task 4.2 T4: RunRedactionContext (shared KeyMap lifecycle + finalize) --
# One context per run_id holds the shared KeyMap, commit_candidates, and
# local_only_paths. baseline + probes share context.keymap. A probe that fails
# the residual gate must NOT pollute the shared keymap (trial isolation). The
# keymap is written ONCE at finalize (after all outputs), never mid-run.

def _ctx(tmp_path):
    return ste.RunRedactionContext(run_id="20260608T090000Z",
                                   raw_dir=str(tmp_path / "raw" / "20260608T090000Z"))


def test_context_baseline_and_probe_share_ip_token(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))       # IP -> <IPV4_1>
    ppath = str(tmp_path / "probes" / "p.json")
    ctx.emit_probe(_pii_probe(), ppath)                          # same IP reuses token
    text = Path(ppath).read_text(encoding="utf-8")
    assert "192.0.0.4" not in text and "<IPV4_1>" in text


def test_context_new_probe_token_lands_in_final_keymap(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    ctx.emit_probe(_pii_probe(), str(tmp_path / "probes" / "p.json"))   # adds a MAC
    kpath = ctx.finalize()
    data = json.loads(Path(kpath).read_text(encoding="utf-8"))
    assert "9c:1e:ce:0c:36:e0" in data["by_kind"]["MAC"]


def test_context_keymap_written_only_at_finalize(tmp_path):
    raw = tmp_path / "raw" / "20260608T090000Z"
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    ctx.emit_probe(_pii_probe(), str(tmp_path / "probes" / "p.json"))
    assert not (raw / "_redaction_keymap.json").exists()         # not written mid-run
    ctx.finalize()
    assert (raw / "_redaction_keymap.json").exists()             # written at finalize


def test_context_final_keymap_roundtrip_restores_all_tokens(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    ctx.emit_probe(_pii_probe(), str(tmp_path / "probes" / "p.json"))
    kpath = ctx.finalize()
    km = ste.rd.KeyMap.from_dict(json.loads(Path(kpath).read_text(encoding="utf-8")))
    assert km.token_for("BUILD_FP", _FULL_FP) == "<BUILD_FP_1>"       # baseline token
    assert km.token_for("IPV4", "192.0.0.4") == "<IPV4_1>"           # shared token
    assert km.token_for("MAC", "9c:1e:ce:0c:36:e0") == "<MAC_1>"     # probe token


def test_context_commit_candidates_pass_gate(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    ctx.emit_probe(_pii_probe(), str(tmp_path / "probes" / "p.json"))
    ctx.finalize()
    result = rg.run_gate(ctx.commit_candidates)
    assert result["verdict"] == "PASS", result


def test_context_mixing_local_only_into_candidates_fails_gate(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    kpath = ctx.finalize()
    assert kpath in ctx.local_only_paths and kpath not in ctx.commit_candidates
    result = rg.run_gate(ctx.commit_candidates + [kpath])        # keymap wrongly mixed in
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "PATH_POLICY" for f in result["findings"])


def test_context_probe_residual_failure_no_file_and_no_pollution(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    before = ctx.keymap.to_dict()
    ppath = str(tmp_path / "probes" / "fail.json")
    monkeypatch.setattr(ste.rd, "residual_scan",
                        lambda obj: [ste.rd.Finding("IPV4", "residual", "$", "leak")])
    with pytest.raises(ste.ResidualPIIError):
        ctx.emit_probe(_pii_probe(), ppath)
    assert not Path(ppath).exists()                  # scan-before-write: no file
    assert ctx.keymap.to_dict() == before            # failed probe did not pollute keymap
    assert ppath not in ctx.commit_candidates


def test_context_finalize_twice_is_rejected(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    ctx.finalize()
    with pytest.raises(RuntimeError):
        ctx.finalize()


# --- T4 guards: baseline transaction + finalize atomic keymap write ---------

def test_context_baseline_residual_failure_is_transactional(tmp_path, monkeypatch):
    # If either the JSON or MD redaction leaves residual PII, emit_baseline must
    # write no file, register no candidate, and leave the shared keymap untouched.
    ctx = _ctx(tmp_path)
    before = ctx.keymap.to_dict()
    base = str(tmp_path / "b")
    monkeypatch.setattr(ste.rd, "residual_scan",
                        lambda obj: [ste.rd.Finding("IPV4", "residual", "$", "leak")])
    with pytest.raises(ste.ResidualPIIError):
        ctx.emit_baseline(_pii_baseline(), base)
    assert not Path(base + ".json").exists()
    assert not Path(base + ".md").exists()
    assert ctx.commit_candidates == []
    assert ctx.keymap.to_dict() == before


def test_finalize_atomic_preserves_prior_keymap_on_write_failure(tmp_path, monkeypatch):
    # A failed keymap write must not corrupt/truncate an existing keymap (atomic
    # temp + replace, never an in-place truncating "w" on the final path).
    ctx = _ctx(tmp_path)
    prior = Path(ctx.raw_dir) / "_redaction_keymap.json"
    prior.parent.mkdir(parents=True, exist_ok=True)
    original = '{"by_kind": {"IPV4": {"1.2.3.4": "<IPV4_1>"}}}'
    prior.write_text(original, encoding="utf-8")
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))

    def boom(*a, **k):
        raise OSError("disk full mid-write")
    monkeypatch.setattr(ste.json, "dump", boom)
    with pytest.raises(OSError):
        ctx.finalize()
    assert prior.read_text(encoding="utf-8") == original   # prior keymap intact
    assert ctx.finalized is False
    assert not (Path(ctx.raw_dir) / "_redaction_keymap.json.tmp").exists()


def test_finalize_write_failure_leaves_context_unfinalized(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))

    def boom(keymap, raw_dir):
        raise OSError("disk full")
    monkeypatch.setattr(ste, "dump_keymap", boom)
    with pytest.raises(OSError):
        ctx.finalize()
    assert ctx.finalized is False
    assert ctx.local_only_paths == []                      # keymap not registered


def test_finalize_can_retry_after_transient_failure(tmp_path, monkeypatch):
    # retry policy: a failed finalize leaves the context retryable; a later
    # finalize succeeds (a *successful* finalize then locks against re-finalize).
    ctx = _ctx(tmp_path)
    ctx.emit_baseline(_pii_baseline(), str(tmp_path / "b"))
    real = ste.dump_keymap
    calls = {"n": 0}

    def flaky(keymap, raw_dir):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("transient")
        return real(keymap, raw_dir)
    monkeypatch.setattr(ste, "dump_keymap", flaky)
    with pytest.raises(OSError):
        ctx.finalize()
    assert ctx.finalized is False
    kpath = ctx.finalize()                                  # retry succeeds
    assert ctx.finalized is True and Path(kpath).exists()
