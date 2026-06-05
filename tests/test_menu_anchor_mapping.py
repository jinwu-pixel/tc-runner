"""Task 2 — TCAnchorMapping extract stage (menu-tree v1.2 sidecar).

`extract_anchor_candidates` parses `am start` launches from a TC and produces
candidates carrying ONLY source-side fields (entry_action, domain, match_method,
source_expected_texts). Baseline-side fields (screen_id, device_observed_texts,
match_confidence) are added later by `join_anchor_to_baseline` — expected and
observed are never mixed at this stage.
See docs/superpowers/plans/2026-06-05-menu-tree-v1_2-tdd-plan.md (Task 2).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import menu_anchor as ma


def _baseline(screens):
    return {"schema_version": 1, "screens": screens}


def _screen(screen_id, entry, observed_texts=None):
    return {"screen_id": screen_id, "entry": entry,
            "observed_texts": observed_texts or {"ko": [], "en": [], "other": []}}


def _one(tc, tc_file="x.yaml"):
    return ma.extract_anchor_candidates(tc, tc_file)[0]


def _tc(steps, name="T"):
    return {"name": name, "steps": steps}


def test_component_launch_candidate():
    tc = _tc([
        {"action": "key", "key": "KEYCODE_HOME"},
        {"action": "shell", "command": "am force-stop com.example.seniorshield"},
        {"action": "shell", "command": "am start -n com.example.seniorshield/.MainActivity"},
        {"action": "verify_text", "target": "시니어쉴드"},
        {"action": "verify_text", "target": "현재 보호 상태"},
    ])
    cands = ma.extract_anchor_candidates(tc, "exported_tc1/SS_01_main_screen.yaml")
    assert len(cands) == 1
    c = cands[0]
    assert c.tc_file == "exported_tc1/SS_01_main_screen.yaml"
    assert c.match_method == "component"
    assert c.domain == "app:com.example.seniorshield"
    assert "am start -n com.example.seniorshield/.MainActivity" in c.entry_action
    assert c.source_expected_texts == {
        "source": "tc_yaml", "texts": ["시니어쉴드", "현재 보호 상태"]}


def test_deeplink_settings_candidate_dedups_repeated_launches():
    tc = _tc([
        {"action": "shell", "command": "am start -a android.settings.APN_SETTINGS"},
        {"action": "wait", "duration": 2000},
        {"action": "shell", "command": "am start -a android.settings.APN_SETTINGS"},
    ])
    cands = ma.extract_anchor_candidates(tc, "exported_tc1/BUG_25175_LGU_APN_menu.yaml")
    assert len(cands) == 1
    assert cands[0].match_method == "deeplink"
    assert cands[0].domain == "settings"
    assert "android.settings.APN_SETTINGS" in cands[0].entry_action
    assert cands[0].source_expected_texts == {"source": "tc_yaml", "texts": []}


def test_component_in_settings_package_is_settings_domain():
    tc = _tc([{"action": "shell", "command": "am start -n com.android.settings/.Settings"}])
    c = ma.extract_anchor_candidates(tc, "x.yaml")[0]
    assert c.match_method == "component"
    assert c.domain == "settings"


def test_non_settings_deeplink_is_external():
    tc = _tc([{"action": "shell", "command": "am start -a android.intent.action.DIAL"}])
    c = ma.extract_anchor_candidates(tc, "x.yaml")[0]
    assert c.match_method == "deeplink"
    assert c.domain == "external"


def test_broadcast_and_forcestop_are_not_launches():
    tc = _tc([
        {"action": "shell", "command": "am force-stop com.x"},
        {"action": "shell",
         "command": "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"},
        {"action": "tap_text", "target": "설정"},
    ])
    assert ma.extract_anchor_candidates(tc, "x.yaml") == []


def test_expected_texts_dedup_and_text_field_fallback_preserves_order():
    tc = _tc([
        {"action": "shell", "command": "am start -n com.x/.A"},
        {"action": "verify_text", "text": "A"},
        {"action": "verify_text", "target": "A"},   # duplicate
        {"action": "verify_text", "target": "B"},
    ])
    c = ma.extract_anchor_candidates(tc, "x.yaml")[0]
    assert c.source_expected_texts["texts"] == ["A", "B"]


def test_candidate_has_no_baseline_side_fields():
    tc = _tc([{"action": "shell", "command": "am start -n com.x/.A"}])
    c = ma.extract_anchor_candidates(tc, "x.yaml")[0]
    # screen_id / device_observed_texts / match_confidence are join-stage only.
    assert not hasattr(c, "screen_id")
    assert not hasattr(c, "device_observed_texts")
    assert not hasattr(c, "match_confidence")


def test_real_ss01_file_integration():
    from src import tc_loader
    tc = tc_loader.load_tc(Path("exported_tc1/SS_01_main_screen.yaml"))
    cands = ma.extract_anchor_candidates(tc, "exported_tc1/SS_01_main_screen.yaml")
    assert len(cands) == 1
    assert cands[0].match_method == "component"
    assert cands[0].domain == "app:com.example.seniorshield"
    assert "시니어쉴드" in cands[0].source_expected_texts["texts"]


# --- join stage (baseline-side fields) -------------------------------------

def test_join_deeplink_exact_match():
    cand = _one(_tc([
        {"action": "shell", "command": "am start -a android.settings.PRIVACY_SETTINGS"},
        {"action": "verify_text", "target": "개인정보"},
    ]), "p.yaml")
    baseline = _baseline([_screen(
        "settings_d1_privacy", {"action": "android.settings.PRIVACY_SETTINGS"},
        {"ko": ["개인 정보 보호", "권한"], "en": ["Privacy"], "other": []})])
    m = ma.join_anchor_to_baseline(cand, baseline)
    assert m.screen_id == "settings_d1_privacy"
    assert m.match_confidence == 0.9
    assert m.device_observed_texts == ["개인 정보 보호", "권한", "Privacy"]
    # expected (source) stays separate from observed (device)
    assert m.source_expected_texts == {"source": "tc_yaml", "texts": ["개인정보"]}


def test_join_deeplink_no_match_is_null_and_low_confidence():
    cand = _one(_tc([{"action": "shell", "command": "am start -a android.settings.WIFI_SETTINGS"}]))
    baseline = _baseline([_screen("settings_d1_privacy",
                                  {"action": "android.settings.PRIVACY_SETTINGS"})])
    m = ma.join_anchor_to_baseline(cand, baseline)
    assert m.screen_id is None
    assert m.match_confidence == 0.3
    assert m.device_observed_texts == []


def test_join_settings_component_exact_match():
    cand = _one(_tc([{"action": "shell",
                      "command": "am start -n com.android.settings/.Settings$WifiSettingsActivity"}]))
    baseline = _baseline([_screen(
        "settings_d1_wifi", {"component": "com.android.settings/.Settings$WifiSettingsActivity"},
        {"ko": ["Wi-Fi"], "en": [], "other": []})])
    m = ma.join_anchor_to_baseline(cand, baseline)
    assert m.domain == "settings"
    assert m.match_method == "component"
    assert m.screen_id == "settings_d1_wifi"
    assert m.match_confidence == 0.8
    assert m.device_observed_texts == ["Wi-Fi"]


def test_join_app_component_stays_out_of_settings_scope():
    cand = _one(_tc([
        {"action": "shell", "command": "am start -n com.example.seniorshield/.MainActivity"},
        {"action": "verify_text", "target": "시니어쉴드"},
    ]), "s.yaml")
    # even if a same-component screen existed, app:<pkg> is out of Settings scope
    baseline = _baseline([_screen("x", {"component": "com.example.seniorshield/.MainActivity"})])
    m = ma.join_anchor_to_baseline(cand, baseline)
    assert m.domain == "app:com.example.seniorshield"
    assert m.screen_id is None
    assert m.match_confidence == 0.3
    assert m.device_observed_texts == []
    assert m.source_expected_texts["texts"] == ["시니어쉴드"]


def test_observed_texts_bucket_order_preserved_no_global_sort():
    cand = _one(_tc([{"action": "shell", "command": "am start -a android.settings.X"}]))
    baseline = _baseline([_screen("s", {"action": "android.settings.X"},
                                  {"ko": ["하", "가"], "en": ["zeta", "alpha"], "other": ["9", "1"]})])
    m = ma.join_anchor_to_baseline(cand, baseline)
    # ko -> en -> other, original within-bucket order kept (global sort would reorder)
    assert m.device_observed_texts == ["하", "가", "zeta", "alpha", "9", "1"]


# --- TCAnchorMapping JSON sidecar contract ---------------------------------

def test_tc_anchor_mapping_json_roundtrip_allows_null_screen_id():
    cand = _one(_tc([{"action": "shell", "command": "am start -a android.settings.WIFI_SETTINGS"}]))
    m = ma.join_anchor_to_baseline(cand, _baseline([]))
    assert m.screen_id is None
    d = m.to_dict()
    assert set(d) == {
        "tc_file", "entry_action", "domain", "match_method",
        "source_expected_texts", "screen_id", "device_observed_texts", "match_confidence",
    }
    restored = ma.TCAnchorMapping.from_dict(json.loads(json.dumps(d)))
    assert restored == m


# --- ActionSafety -> AutomationClass adapter (string-based) -----------------

@pytest.mark.parametrize("safety,expected", [
    (ma.ActionSafety.READ_ONLY, "FULL_AUTO"),
    (ma.ActionSafety.READ_ONLY_SHELL, "FULL_AUTO"),
    (ma.ActionSafety.NAVIGATION_ONLY, "SEMI_AUTO"),
    (ma.ActionSafety.SELECTION_GATED, "MANUAL_REQUIRED"),
    (ma.ActionSafety.INPUT_REQUIRED, "MANUAL_REQUIRED"),
    (ma.ActionSafety.PRIVILEGED_SHELL, "MANUAL_REQUIRED"),
    (ma.ActionSafety.DESTRUCTIVE, "MANUAL_REQUIRED"),
    (ma.ActionSafety.UNKNOWN_UNSAFE, "MANUAL_REQUIRED"),
])
def test_safety_to_automation_class_table(safety, expected):
    assert ma.safety_to_automation_class(safety) == expected


def test_adapter_outputs_are_valid_automation_class_values():
    # non-skip consistency: AutomationClass imported in TEST ONLY.
    from typing import get_args
    from src.mmi_converter.models import AutomationClass
    valid = set(get_args(AutomationClass))
    for s in ma.ActionSafety:
        assert ma.safety_to_automation_class(s) in valid


def test_confidence_constants_locked():
    assert (ma.CONFIDENCE_DEEPLINK, ma.CONFIDENCE_SETTINGS_COMPONENT,
            ma.CONFIDENCE_UNMATCHED, ma.CONFIDENCE_TEXT_FALLBACK) == (0.9, 0.8, 0.3, 0.2)
