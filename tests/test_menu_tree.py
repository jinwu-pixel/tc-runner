"""Tests for src/menu_tree.py (canonical menu-tree baseline schema + classifiers)."""
from __future__ import annotations

from src import menu_tree as mt


def _node(**kw):
    base = {"text": "", "content-desc": "", "class": "", "resource-id": "",
            "clickable": "false", "focusable": "false", "checkable": "false",
            "inherited_clickable": "false", "inherited_focusable": "false", "bounds": ""}
    base.update(kw)
    return base


def test_detect_script_buckets():
    assert mt.detect_script("개인 정보 보호") == "ko"
    assert mt.detect_script("Wi-Fi") == "en"
    assert mt.detect_script("バッテリー") == "other"
    assert mt.detect_script("T 로밍") == "ko"  # any Hangul -> ko


def test_classify_kind():
    assert mt.classify_kind(_node(text="위치 사용", **{"class": "android.widget.Switch", "checkable": "true"})) == "toggle"
    assert mt.classify_kind(_node(text="검색", **{"class": "android.widget.EditText"})) == "input"
    assert mt.classify_kind(_node(text="확인", **{"class": "android.widget.Button", "clickable": "true"})) == "button"
    assert mt.classify_kind(_node(text="개인 정보 보호", clickable="true", focusable="true")) == "menu_row"
    assert mt.classify_kind(_node(text="설정", **{"resource-id": "android:id/title"})) == "title"
    assert mt.classify_kind(_node()) == "unknown"


def test_text_role_hint():
    assert mt.text_role_hint(_node(**{"resource-id": "android:id/title"})) == "primary"
    assert mt.text_role_hint(_node(**{"resource-id": "android:id/summary"})) == "summary"
    assert mt.text_role_hint(_node(**{"resource-id": "x/icon"})) == "unknown"


def test_build_element_risk_precedence():
    sw = mt.build_element(_node(text="위치 사용", **{"class": "android.widget.Switch", "checkable": "true"}), denylisted=False)
    assert sw.kind == "toggle" and sw.risk == "toggle"
    deny = mt.build_element(_node(text="삭제", clickable="true"), denylisted=True)
    assert deny.risk == "denylist"  # denylist > structural
    plain = mt.build_element(_node(text="개인 정보 보호", clickable="true", focusable="true"), denylisted=False)
    assert plain.kind == "menu_row" and plain.risk == "none"
    chk = mt.build_element(_node(text="동의", **{"class": "android.widget.CheckedTextView", "checkable": "true"}), denylisted=False)
    assert chk.risk == "checkable"


def test_bucket_texts_sorted_and_deduped():
    els = [
        mt.build_element(_node(text="Wi-Fi", clickable="true"), denylisted=False),
        mt.build_element(_node(text="개인 정보 보호", clickable="true"), denylisted=False),
        mt.build_element(_node(text="Wi-Fi", clickable="true"), denylisted=False),
        mt.build_element(_node(text="", clickable="true"), denylisted=False),
    ]
    buckets = mt.bucket_texts(els)
    assert buckets["en"] == ["Wi-Fi"]
    assert buckets["ko"] == ["개인 정보 보호"]
    assert buckets["other"] == []


def _screen(screen_id="settings_d1_privacy"):
    els = [mt.build_element(_node(text="개인 정보 보호", clickable="true", focusable="true"), denylisted=False)]
    return mt.MenuScreen(
        screen_id=screen_id, label_ko="개인 정보 보호", nav_path=["설정", "개인 정보 보호"],
        entry={"method": "deeplink", "action": "android.settings.PRIVACY_SETTINGS",
               "component": None, "launched_cmd": "am start -a android.settings.PRIVACY_SETTINGS"},
        reach_status="REACHED", reach_kind="internal",
        observed_focus="com.android.settings/.Settings$PrivacyDashboardActivity",
        expect_activity_regex="PrivacyDashboardActivity", activity_match=True,
        fingerprint="abcd1234", observed_texts=mt.bucket_texts(els), elements=els,
        scroll=mt.ScrollInfo(passes=1, swipes=[{"dir": "up", "x1": 240, "y1": 600, "x2": 240, "y2": 200}],
                             new_texts_per_pass=[0], terminated="no_new"),
        dump_info=mt.DumpInfo(dump_error=None, dump_size=2048, raw_present=True),
        risk_flags=[], raw_dump_ref="catalog/raw/20260602T000000Z/settings_d1_privacy.xml",
    )


def _baseline(screens=None):
    dev = mt.DeviceBaseline(
        serial="B06201249E0002B8", model="AT-M140", product="alt_thor2", device="thor2",
        build_fingerprint="ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys",
        build_id="RY07260302M", android="14", locale_persist="ko-KR", locale_product="en-US",
        viewport="480x800", dpi="220", sim="SKT")
    return mt.MenuTreeBaseline(
        schema_version=mt.SCHEMA_VERSION, tool_version=mt.TOOL_VERSION,
        generated_at_utc="2026-06-02T00:00:00Z", run_id="20260602T000000Z",
        device=dev, package="com.android.settings",
        seed_ref={"source_menu_tree": "THOR2_K - Settings/MENU_TREE.md", "seed_version": 1,
                  "seed_path": "THOR2_K - Settings/menu_tree_seed.yaml"},
        target_mismatch_ack=False, summary=mt.compute_summary(screens or [_screen()]),
        screens=screens or [_screen()])


def test_compute_summary_counts_reach_kind_external_independent_of_status():
    s_int = _screen("a"); s_int.reach_kind = "internal"; s_int.reach_status = "REACHED"
    s_ext = _screen("b"); s_ext.reach_kind = "external"; s_ext.reach_status = "DUMP_REJECTED"
    summ = mt.compute_summary([s_int, s_ext])
    assert summ["screen_count"] == 2
    assert summ["reached_external"] == 1   # counted by reach_kind, not status
    assert summ["dump_rejected"] == 1


def test_to_json_is_deterministic_with_fixed_clock():
    b1 = _baseline(); b2 = _baseline()
    assert b1.to_json() == b2.to_json()   # byte-identical with fixed run_id/clock


def test_to_json_roundtrip_schema_fields():
    import json
    d = json.loads(_baseline().to_json())
    assert d["schema_version"] == 1
    assert d["screens"][0]["reach_kind"] == "internal"
    assert d["screens"][0]["elements"][0]["kind"] == "menu_row"
    assert d["device"]["serial"] == "B06201249E0002B8"


def test_dump_rejected_screen_nullable_fields():
    s = _screen("dr")
    s.reach_status = "DUMP_REJECTED"; s.fingerprint = None; s.elements = []
    s.observed_texts = mt.bucket_texts([]); s.raw_dump_ref = None
    s.dump_info = mt.DumpInfo(dump_error="null root", dump_size=0, raw_present=False)
    import json
    d = json.loads(mt.MenuTreeBaseline.__dict__  # sanity: dataclass usable
                   and _baseline([s]).to_json())
    sc = d["screens"][0]
    assert sc["fingerprint"] is None and sc["raw_dump_ref"] is None and sc["elements"] == []


def test_to_md_renders_screen_and_summary():
    md = _baseline().to_md()
    assert "# Settings Menu Tree Baseline" in md
    assert "개인 정보 보호" in md
    assert "settings_d1_privacy" in md
    assert "B06201249E0002B8" in md


# --- Task 4: real uiautomator dump fixtures (structure-focused, no golden text) ---
import importlib.util as _ilu
from pathlib import Path as _P

_ROOT = _P(__file__).resolve().parent.parent
_FX = _ROOT / "tests" / "fixtures" / "menu_tree"
_mm_spec = _ilu.spec_from_file_location("menu_mapper", _ROOT / "scripts" / "menu_mapper.py")
_mm = _ilu.module_from_spec(_mm_spec)
_mm_spec.loader.exec_module(_mm)

_FIXTURES = ["settings_root.xml", "settings_d1_privacy.xml", "settings_d1_location.xml"]
_KIND_ENUM = {"title", "menu_row", "button", "toggle", "input", "unknown"}


def _elements_from(xml: str):
    """Parse via the menu_mapper parser (driver boundary) into MenuElements."""
    nodes = _mm.extract_nodes(xml)
    els = [
        mt.build_element(n, denylisted=_mm.is_node_safe(n)[1].startswith("denylist"))
        for n in nodes if (n.get("text") or n.get("content-desc"))
    ]
    return nodes, els


def test_real_dump_structure_holds_for_all_fixtures():
    for name in _FIXTURES:
        xml = (_FX / name).read_text(encoding="utf-8")
        nodes, els = _elements_from(xml)
        assert nodes, f"{name}: expected non-empty node list"
        assert els, f"{name}: expected at least one labeled element"
        buckets = mt.bucket_texts(els)
        assert set(buckets.keys()) == {"ko", "en", "other"}, f"{name}: bucket keys"
        assert any(buckets.values()), f"{name}: expected at least one bucketed text"
        kinds = {e.kind for e in els}
        assert len(kinds) >= 2, f"{name}: expected >=2 distinct kinds, got {sorted(kinds)}"
        assert kinds <= _KIND_ENUM, f"{name}: unexpected kind in {sorted(kinds)}"


def test_real_dump_fingerprint_stable_same_input():
    xml = (_FX / "settings_d1_privacy.xml").read_text(encoding="utf-8")
    nodes = _mm.extract_nodes(xml)
    focus = "com.android.settings/.Settings$PrivacyDashboardActivity"
    fp1 = _mm.generate_fingerprint(focus, nodes)
    fp2 = _mm.generate_fingerprint(focus, nodes)
    assert fp1 == fp2 and len(fp1) == 8


def test_real_dump_json_serialization_deterministic():
    xml = (_FX / "settings_root.xml").read_text(encoding="utf-8")
    nodes, els = _elements_from(xml)

    def _make():
        return mt.MenuScreen(
            screen_id="settings_home", label_ko="설정", nav_path=["설정"],
            entry={"method": "deeplink", "action": "android.settings.SETTINGS",
                   "component": None, "launched_cmd": "am start -a android.settings.SETTINGS"},
            reach_status="REACHED", reach_kind="internal",
            observed_focus="com.android.settings/com.android.settings.Settings",
            expect_activity_regex="Settings$", activity_match=True,
            fingerprint=_mm.generate_fingerprint("com.android.settings/.Settings", nodes),
            observed_texts=mt.bucket_texts(els), elements=els,
            scroll=mt.ScrollInfo(passes=0, swipes=[], new_texts_per_pass=[], terminated="no_new"),
            dump_info=mt.DumpInfo(dump_error=None, dump_size=len(xml), raw_present=True),
            risk_flags=[], raw_dump_ref="tests/fixtures/menu_tree/settings_root.xml",
        )

    assert _baseline([_make()]).to_json() == _baseline([_make()]).to_json()
