"""Tests for scripts/altbasic_entry_detail_ledger.py (read-only normalization ledger).

Pure parser/classifier tested with synthetic strings only. NO device, NO network,
NO wall-clock. Manifest IO + golden snapshot covered in later tasks.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_entry_detail_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_entry_detail_ledger", _PATH)
L = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_entry_detail_ledger"] = L
_spec.loader.exec_module(L)


def test_parse_single_press_key_strips_step_number():
    steps = L.parse_entry_detail("press_key:1. Recent App 버튼 누른다")
    assert len(steps) == 1
    assert steps[0].action == "press_key"
    assert steps[0].body == "Recent App 버튼 누른다"


def test_parse_multistep_split_on_gt():
    steps = L.parse_entry_detail("tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다")
    assert [s.action for s in steps] == ["tap", "press_key"]
    assert steps[1].body == "하드키 돌아가기 버튼 누른다"


def test_parse_bare_continuation_is_marked_bare():
    steps = L.parse_entry_detail("press_key:1. Home 버튼 누른다 > Press Down")
    assert steps[0].action == "press_key"
    assert steps[1].action == "(bare)"
    assert steps[1].body == "Press Down"


def test_parse_unknown_prefix_is_marked_question():
    steps = L.parse_entry_detail("foobar:do something")
    assert steps[0].action == "?foobar"


def test_parse_empty_or_dash_returns_empty():
    assert L.parse_entry_detail("") == []
    assert L.parse_entry_detail("—") == []


def test_normalize_strips_step_num_and_trailing_verb():
    assert L.normalize_body("1. Home 버튼 누른다") == "Home 버튼"
    assert L.normalize_body("Recent App 버튼 누른다.") == "Recent App 버튼"


def test_normalize_keeps_markers():
    # parentheses, slash, 또는 must survive for marker detection
    assert "(" in L.normalize_body("Navi 키(OK) 버튼을 누른다.")
    assert "또는" in L.normalize_body("네비키 또는 OK키 입력")


def test_compact_casefolds_and_removes_space():
    assert L._compact("Press Down") == "pressdown"
    assert L._compact("UP 방향키") == "up방향키"


def test_resolve_named_keys():
    assert L.resolve_single_key("Recent App 버튼") == (187, "RESOLVED")
    assert L.resolve_single_key("Home 버튼 누른다") == (3, "RESOLVED")
    assert L.resolve_single_key("Camera 버튼") == (27, "RESOLVED")
    assert L.resolve_single_key("Contact 버튼") == (207, "RESOLVED")
    assert L.resolve_single_key("하드키 돌아가기 버튼") == (4, "RESOLVED")


def test_resolve_single_direction_now_resolvable():
    assert L.resolve_single_key("Press Down") == (20, "RESOLVED")
    assert L.resolve_single_key("UP 방향키") == (19, "RESOLVED")
    assert L.resolve_single_key("하방향키") == (20, "RESOLVED")
    assert L.resolve_single_key("Right 방향키") == (22, "RESOLVED")
    assert L.resolve_single_key("press ok") == (23, "RESOLVED")
    assert L.resolve_single_key("Press down(하드키)") == (20, "RESOLVED")


def test_resolve_disjunction_is_adjudicate():
    kc, v = L.resolve_single_key("네비키 또는 OK키")
    assert v == "ADJUDICATE" and kc == 23
    kc, v = L.resolve_single_key("Navi 키(OK) 버튼을 누른다.")
    assert v == "ADJUDICATE"


def test_resolve_any_and_enumeration_is_ambiguous():
    assert L.resolve_single_key("아무 방향키")[1] == "AMBIGUOUS"
    assert L.resolve_single_key("Press Any Direction")[1] == "AMBIGUOUS"
    assert L.resolve_single_key("홈화면에서 Navi U/D/L/R/OK 키 입력한다")[1] == "AMBIGUOUS"


def test_resolve_slash_keyname_is_not_direction_enumeration():
    # 지우기/취소 has a slash but is NOT a direction enumeration -> NONE (not AMBIGUOUS)
    assert L.resolve_single_key("지우기/취소 버튼")[1] == "NONE"


def test_resolve_screen_name_is_none():
    assert L.resolve_single_key("시계")[1] == "NONE"
    assert L.resolve_single_key("wifi focus")[1] == "NONE"
    assert L.resolve_single_key("앱서랍 진입")[1] == "NONE"


def test_resolve_no_false_resolved_from_noun_ending_in_key():
    # nouns ending in 키 with embedded direction syllables must NOT resolve
    assert L.resolve_single_key("위치 정보 키")[1] == "NONE"
    assert L.resolve_single_key("좌측 메뉴 키")[1] == "NONE"
    assert L.resolve_single_key("상태 표시줄 키")[1] == "NONE"


def test_resolve_navi_without_parens_is_adjudicate():
    assert L.resolve_single_key("Navi 키 OK")[1] == "ADJUDICATE"


# ---- Task 4: classify_step --------------------------------------------------

def _disp(action, body):
    return L.classify_step(L.Step(action=action, body=body, raw=body))["disposition"]


def test_classify_now_resolvable():
    r = L.classify_step(L.Step("press_key", "Recent App 버튼 누른다", "x"))
    assert r["disposition"] == L.NOW_RESOLVABLE
    assert r["proposed_keycode"] == 187
    assert r["confidence"] == "high"
    assert r["executable"] is True


def test_classify_bare_direction_now_resolvable():
    assert _disp("(bare)", "Press Down") == L.NOW_RESOLVABLE


def test_classify_adjudicate_sets_intent_decision():
    r = L.classify_step(L.Step("press_key", "네비키 또는 OK키 입력", "x"))
    assert r["disposition"] == L.ADJUDICATE
    assert r["required_decision"] == L.RD_INTENT
    assert r["confidence"] == "medium"


def test_classify_ambiguous_sets_spec_decision():
    r = L.classify_step(L.Step("press_key", "아무 방향키", "x"))
    assert r["disposition"] == L.AMBIGUOUS_NOGUESS
    assert r["required_decision"] == L.RD_SPEC


def test_classify_named_key_without_keycode_is_device_keycode_discovery():
    # REQUIRED fixture case (spec 3.2)
    r = L.classify_step(L.Step("press_key", "Message 버튼 누른다", "x"))
    assert r["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r["required_decision"] == L.RD_KEY_DISCOVERY
    r2 = L.classify_step(L.Step("press_key", "지우기/취소 버튼", "x"))
    assert r2["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r2["required_decision"] == L.RD_KEY_DISCOVERY


def test_classify_screen_ref_is_not_a_key():
    r = L.classify_step(L.Step("press_key", "wifi focus", "x"))
    assert r["disposition"] == L.NOT_A_KEY
    assert r["required_decision"] == L.RD_RECLASSIFY


def test_classify_tap_is_selector_discovery():
    r = L.classify_step(L.Step("tap", "퀵 패널", "x"))
    assert r["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r["required_decision"] == L.RD_SEL_DISCOVERY


def test_classify_observe_token_is_non_executable():
    r = L.classify_step(L.Step("(bare)", "기본 항목 확인한다", "x"))
    assert r["executable"] is False


def test_classify_long_press_modifier_is_device_keycode_discovery():
    # 길게 = long-press gesture, NOT a standard keyevent → must NOT be NOW_RESOLVABLE
    r = L.classify_step(L.Step("(bare)", "Press Ok 길게 입력", "x"))
    assert r["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r["required_decision"] == L.RD_KEY_DISCOVERY
    r2 = L.classify_step(L.Step("press_key", "종료 버튼 길게 누른다", "x"))
    assert r2["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r2["required_decision"] == L.RD_KEY_DISCOVERY


# ---- Task 5: rollup_eligibility ---------------------------------------------

def test_rollup_all_resolvable_is_eligible():
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
    ]
    assert L.rollup_eligibility(rows) is True


def test_rollup_one_blocking_step_is_not_eligible():
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.AMBIGUOUS_NOGUESS, "executable": True},
    ]
    assert L.rollup_eligibility(rows) is False


def test_rollup_excludes_non_executable_token():
    # mixed-token case (spec 5.1): observe token excluded, TC stays eligible
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.FREE_TEXT_DISCOVERY, "executable": False},
    ]
    assert L.rollup_eligibility(rows) is True


def test_rollup_no_executable_steps_is_not_eligible():
    rows = [{"disposition": L.FREE_TEXT_DISCOVERY, "executable": False}]
    assert L.rollup_eligibility(rows) is False


# ---- Task 6: manifest IO ----------------------------------------------------

import csv as _csv

LEDGER_COLUMNS = L.LEDGER_COLUMNS


def _write_manifest(tmp_path):
    p = tmp_path / "m.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["tc_id", "source_file", "entry_detail"])
        w.writerow(["ALTBASIC_BSC_014", "x.xlsx", "press_key:1. Recent App 버튼 누른다"])
        w.writerow(["ALTBASIC_BSC_120",
                    "x.xlsx", "tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다"])
    return str(p)


def test_load_manifest_reads_rows(tmp_path):
    rows = L.load_manifest(_write_manifest(tmp_path))
    assert [r["tc_id"] for r in rows] == ["ALTBASIC_BSC_014", "ALTBASIC_BSC_120"]


def test_build_ledger_one_row_per_step_with_all_columns(tmp_path):
    rows = L.load_manifest(_write_manifest(tmp_path))
    ledger = L.build_ledger(rows)
    # BSC_014 = 1 step, BSC_120 = 2 steps => 3 ledger rows
    assert len(ledger) == 3
    for r in ledger:
        assert set(LEDGER_COLUMNS).issubset(r.keys())
    bsc014 = [r for r in ledger if r["tc_id"] == "ALTBASIC_BSC_014"]
    assert bsc014[0]["device_pilot_eligible"] is True   # single resolvable key
    # BSC_120 has a tap step (selector discovery) => not eligible
    bsc120 = [r for r in ledger if r["tc_id"] == "ALTBASIC_BSC_120"]
    assert all(r["device_pilot_eligible"] is False for r in bsc120)


# ---- Task 7: summarize ------------------------------------------------------

def _ledger_from(entries):
    # entries: list of (tc_id, entry_detail)
    rows = [{"tc_id": t, "source_file": "x.xlsx", "entry_detail": e} for t, e in entries]
    return L.build_ledger(rows)


def test_summarize_tier_counts_are_step_level():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # 1 NOW_RESOLVABLE
        ("T2", "press_key:1. 아무 방향키"),                      # 1 AMBIGUOUS
        ("T3", "tap:1. 퀵 패널"),                                # 1 FREE_TEXT
    ])
    s = L.summarize(ledger)
    assert s["tier_counts"][L.NOW_RESOLVABLE] == 1
    assert s["tier_counts"][L.AMBIGUOUS_NOGUESS] == 1
    assert s["tier_counts"][L.FREE_TEXT_DISCOVERY] == 1


def test_summarize_headline_is_tc_level():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # eligible
        ("T2", "press_key:1. Home 버튼 누른다 > Press Down"),    # eligible (both resolvable)
        ("T3", "press_key:1. 아무 방향키"),                      # not eligible
    ])
    s = L.summarize(ledger)
    assert s["headline_resolvable_count"] == 2          # TC-level
    assert s["potential_with_adjudication_count"] >= 2  # at least the eligible ones


def test_summarize_potential_counts_adjudicate_only_tcs():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # eligible
        ("T2", "press_key:1. 네비키 또는 OK키 입력"),            # adjudicate-only
    ])
    s = L.summarize(ledger)
    assert s["headline_resolvable_count"] == 1
    assert s["potential_with_adjudication_count"] == 2


def test_summarize_top_unlock_counts_tcs_not_steps():
    # a TC with two identical NOW_RESOLVABLE steps must contribute 1, not 2
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다 > press_key:2. Home 버튼 누른다"),
        ("T2", "press_key:1. Home 버튼 누른다"),
    ])
    s = L.summarize(ledger)
    top = dict(s["top_unlock"])
    assert top.get("press_key:KEYCODE_HOME") == 2   # 2 TCs, not 3 step-rows


# ---- Task 8: writers + CLI --------------------------------------------------

def test_write_ledger_csv_roundtrip(tmp_path):
    ledger = _ledger_from([("T1", "press_key:1. Home 버튼 누른다")])
    out = tmp_path / "ledger.csv"
    L.write_ledger_csv(ledger, str(out))
    with open(out, encoding="utf-8-sig", newline="") as f:
        got = list(_csv.DictReader(f))
    assert got[0]["tc_id"] == "T1"
    assert got[0]["disposition"] == L.NOW_RESOLVABLE
    assert list(got[0].keys()) == LEDGER_COLUMNS   # exact column order


def test_write_summary_md_labels_levels(tmp_path):
    ledger = _ledger_from([("T1", "press_key:1. Home 버튼 누른다")])
    s = L.summarize(ledger)
    out = tmp_path / "summary.md"
    L.write_summary_md(s, str(out))
    text = out.read_text(encoding="utf-8")
    assert "(step-level)" in text
    assert "(TC-level)" in text
    assert "headline_resolvable_count" in text


def test_main_writes_both_artifacts(tmp_path):
    man = _write_manifest(tmp_path)
    csv_out = tmp_path / "L.csv"
    md_out = tmp_path / "S.md"
    L.main(["--manifest", man, "--ledger-out", str(csv_out), "--summary-out", str(md_out)])
    assert csv_out.exists() and md_out.exists()


# ---- Task 9: golden snapshot ------------------------------------------------

import json


def test_golden_snapshot():
    fix = _ROOT / "tests" / "fixtures" / "altbasic" / "entry_detail_ledger_golden.json"
    data = json.loads(fix.read_text(encoding="utf-8"))
    ledger = L.build_ledger(data["manifest"])
    keys = ["tc_id", "extracted_token", "disposition", "proposed_keycode",
            "required_decision", "device_pilot_eligible", "executable"]
    got = [{k: r[k] for k in keys} for r in ledger]
    assert got == data["expected_ledger"]
