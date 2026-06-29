"""Tests for scripts/altbasic_not_a_key_subtype_ledger.py (read-only subtype ledger).
Pure classifier tested with synthetic strings only. NO device, NO network, NO wall-clock.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_not_a_key_subtype_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_not_a_key_subtype_ledger", _PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_not_a_key_subtype_ledger"] = M
_spec.loader.exec_module(M)


# ---- Task 1: scaffold + import ----------------------------------------------
def test_module_reuses_predecessor_primitives():
    assert callable(M.parse_entry_detail)
    assert callable(M.classify_step)
    assert callable(M.normalize_body)
    assert M.NOT_A_KEY == "NOT_A_KEY"


def test_subtype_constants_present():
    assert M.VERIFIER_FOCUS_STATE == "VERIFIER_FOCUS_STATE"
    assert M.VERIFIER_FOCUS_CANDIDATE == "VERIFIER_FOCUS_CANDIDATE"
    assert M.VERIFIER_SCREEN_PRESENT == "VERIFIER_SCREEN_PRESENT"
    assert M.MANUAL_RETAIN == "MANUAL_RETAIN"
    assert M.KEYCODE_DISCOVERY == "KEYCODE_DISCOVERY"
    assert M.SELECTOR_DISCOVERY == "SELECTOR_DISCOVERY"


# ---- Task 2: subclassify_not_a_key ------------------------------------------
def _subtype(body):
    step = M.parse_entry_detail(f"press_key:{body}")[0]
    return M.subclassify_not_a_key(step)["not_a_key_subtype"]


def test_focus_with_state_marker_is_focus_state():
    assert _subtype("앱 서랍 포커스 되지 않은 상태") == M.VERIFIER_FOCUS_STATE
    assert _subtype("스크롤 마지막 앱에 포커스 위치") == M.VERIFIER_FOCUS_STATE


def test_bare_focus_is_candidate_not_state():
    assert _subtype("wifi focus") == M.VERIFIER_FOCUS_CANDIDATE
    assert _subtype("새 연락처 만들기 focus") == M.VERIFIER_FOCUS_CANDIDATE
    # focus wins over the 버튼 keycode signal; no state marker -> candidate
    assert _subtype("전원 버튼 focus") == M.VERIFIER_FOCUS_CANDIDATE


def test_screen_marker_without_focus_is_screen_present():
    assert _subtype("간편 설정 페이지") == M.VERIFIER_SCREEN_PRESENT
    assert _subtype("홈화면") == M.VERIFIER_SCREEN_PRESENT
    assert _subtype("앱서랍 진입") == M.VERIFIER_SCREEN_PRESENT


def test_truncated_or_sensitive_is_manual_retain():
    assert _subtype("언어 및") == M.MANUAL_RETAIN       # spaced dangling 및
    assert _subtype("언어및") == M.MANUAL_RETAIN          # no-space dangling 및 (robust)
    assert _subtype("긴급 전화") == M.MANUAL_RETAIN


def test_truncated_does_not_false_match_noun_ending():
    # 와/과 are common noun endings; only a *spaced* dangling conjunction is truncation.
    # a plain label ending in 과 (e.g. 결과) must NOT be MANUAL_RETAIN.
    assert _subtype("결과") == M.SELECTOR_DISCOVERY


def test_keycode_discovery_modifier_or_navword():
    assert _subtype("해당 버튼을 짧게 누른다") == M.KEYCODE_DISCOVERY
    assert _subtype("하드키 즐겨 찾기 버튼 롱") == M.KEYCODE_DISCOVERY
    assert _subtype("뒤로가기") == M.KEYCODE_DISCOVERY


def test_selector_discovery_is_default():
    assert _subtype("펼치기 Tap") == M.SELECTOR_DISCOVERY
    assert _subtype("사진") == M.SELECTOR_DISCOVERY
    assert _subtype("시계") == M.SELECTOR_DISCOVERY
    assert _subtype("언어 및 입력") == M.SELECTOR_DISCOVERY  # full label, not truncated


def test_subclassify_row_shape():
    step = M.parse_entry_detail("press_key:wifi focus")[0]
    row = M.subclassify_not_a_key(step)
    assert set(row) == {"not_a_key_subtype", "confidence", "proposed_action",
                        "resolution_requirement", "rationale", "required_decision"}
    assert row["resolution_requirement"] == M.R_VFOCUS_CAND
    assert row["confidence"] == "medium"


# ---- Task 3: resolution_requirement + blocker_reason ------------------------
def _base_and_req(entry):
    step = M.parse_entry_detail(entry)[0]
    base = M.classify_step(step)
    subtype_req = None
    if base["disposition"] == M.NOT_A_KEY:
        subtype_req = M.subclassify_not_a_key(step)["resolution_requirement"]
    return base, M.resolution_requirement(base, subtype_req)


def test_req_now_resolvable_is_resolved():
    _, req = _base_and_req("press_key:Home 버튼 누른다")
    assert req == M.R_RESOLVED


def test_req_not_a_key_focus_state():
    _, req = _base_and_req("press_key:앱 서랍 포커스 되지 않은 상태")
    assert req == M.R_VFOCUS


def test_req_not_a_key_selector_default():
    _, req = _base_and_req("press_key:사진")
    assert req == M.R_SELECTOR


def test_req_free_text_tap_is_selector():
    _, req = _base_and_req("tap:더보기 Tap")
    assert req == M.R_SELECTOR


def test_req_ambiguous_is_blocker():
    _, req = _base_and_req("press_key:아무 방향키")
    assert req == M.R_BLOCKER


def test_req_nonexec_observe_token():
    step = M.parse_entry_detail("설정 화면이 표시된다")[0]
    base = M.classify_step(step)
    assert base["executable"] is False
    assert M.resolution_requirement(base, None) == M.R_NONEXEC


def test_blocker_reason_distinguishes_sources():
    s1 = M.parse_entry_detail("press_key:아무 방향키")[0]
    assert M.blocker_reason(M.classify_step(s1), None) == "AMBIGUOUS"
    s2 = M.parse_entry_detail("press_key:언어 및")[0]
    assert M.blocker_reason(M.classify_step(s2), M.MANUAL_RETAIN) == "MANUAL_RETAIN"


# ---- Task 4: scenario_eligible + SCENARIOS ----------------------------------
def test_baseline_eligible_iff_all_executable_resolved():
    non, res = M.SCENARIOS["baseline"]
    assert M.scenario_eligible([M.R_RESOLVED, M.R_RESOLVED], non, res) is True
    assert M.scenario_eligible([M.R_RESOLVED, M.R_SELECTOR], non, res) is False
    assert M.scenario_eligible([M.R_NONEXEC], non, res) is False  # no executable step


def test_tier0_drops_focus_verifier_from_denominator():
    non, res = M.SCENARIOS["tier0"]
    assert M.scenario_eligible([M.R_RESOLVED, M.R_VFOCUS], non, res) is True
    assert M.scenario_eligible([M.R_VFOCUS, M.R_SELECTOR], non, res) is False


def test_mixed_focus_and_selector_unlocks_only_at_tier1():
    reqs = [M.R_VFOCUS, M.R_SELECTOR]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier1"]) is True


def test_screen_present_only_in_screen_scenario():
    reqs = [M.R_RESOLVED, M.R_VSCREEN]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0_screen"]) is True


def test_all_focus_steps_reclassified_leaves_no_executable():
    assert M.scenario_eligible([M.R_VFOCUS], *M.SCENARIOS["tier0"]) is False


def test_blocker_never_resolves():
    assert M.scenario_eligible([M.R_BLOCKER], *M.SCENARIOS["optimistic_upper_bound"]) is False


# ---- Task 5: build ----------------------------------------------------------
_MINI = [
    {"tc_id": "T_FOCUS", "source_file": "x.xlsx",
     "entry_detail": "press_key:1. Home 버튼 누른다 > press_key:wifi focus"},
    {"tc_id": "T_STATE_OK", "source_file": "x.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:앱 서랍 포커스 되지 않은 상태"},
    {"tc_id": "T_SELECTOR", "source_file": "x.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:사진"},
    {"tc_id": "T_EMPTY", "source_file": "x.xlsx", "entry_detail": "—"},
]


def test_build_emits_one_row_per_not_a_key_step():
    subtype_rows, tc_steps = M.build(_MINI)
    assert len(subtype_rows) == 3
    by_tc = {r["tc_id"]: r["not_a_key_subtype"] for r in subtype_rows}
    assert by_tc["T_FOCUS"] == M.VERIFIER_FOCUS_CANDIDATE
    assert by_tc["T_STATE_OK"] == M.VERIFIER_FOCUS_STATE
    assert by_tc["T_SELECTOR"] == M.SELECTOR_DISCOVERY


def test_build_tc_steps_carry_requirements():
    _, tc_steps = M.build(_MINI)
    reqs = [d["req"] for d in tc_steps["T_STATE_OK"]]
    assert reqs == [M.R_RESOLVED, M.R_VFOCUS]


def test_build_empty_entry_is_single_nonexec():
    _, tc_steps = M.build(_MINI)
    assert [d["req"] for d in tc_steps["T_EMPTY"]] == [M.R_NONEXEC]


# ---- Task 6: summarize ------------------------------------------------------
def test_summarize_headline_and_deltas():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["eligible"]["baseline"] == 0
    assert s["eligible"]["tier0"] == 1
    assert s["headline_now_unlock"] == 1
    assert s["deltas"]["selector_delta"] == 1
    assert s["deltas"]["focus_candidate_delta"] == 1


def test_summarize_subtype_counts():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["subtype_counts"][M.VERIFIER_FOCUS_STATE] == 1
    assert s["subtype_counts"][M.SELECTOR_DISCOVERY] == 1


def test_summarize_self_check_flags_mismatch():
    subtype_rows, tc_steps = M.build(_MINI)
    assert M.summarize(subtype_rows, tc_steps, predecessor_headline=0)["self_check"] == "ok"
    assert M.summarize(subtype_rows, tc_steps, predecessor_headline=99)["self_check"] == "mismatch"


# ---- Task 7: IO writers + forbidden guard -----------------------------------
def test_forbidden_word_guard_raises():
    with pytest.raises(AssertionError):
        M.assert_no_forbidden("this text contains RUNNABLE_NOW which is banned")
    M.assert_no_forbidden("clean device-pilot eligibility text")  # no raise


def test_summary_md_has_no_forbidden_tokens_and_labels():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    md = M.render_summary_md(s)
    for w in ("PASS", "RUNNABLE_NOW", "validated"):
        assert w not in md
    assert "headline_now_unlock" in md
    assert "(step-level)" in md and "(TC-level)" in md
    assert "self_check=ok" in md


def test_write_outputs_roundtrip(tmp_path):
    import csv as _csv
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    ledger_csv = tmp_path / "ledger.csv"
    cascade_csv = tmp_path / "cascade.csv"
    summary_md = tmp_path / "summary.md"
    M.write_subtype_csv(subtype_rows, str(ledger_csv))
    M.write_cascade_csv(tc_steps, str(cascade_csv))
    M.write_summary_md(s, str(summary_md))
    with open(ledger_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) == 3
    assert set(M.SUBTYPE_COLUMNS).issubset(rows[0].keys())
    with open(cascade_csv, encoding="utf-8-sig", newline="") as f:
        crows = list(_csv.DictReader(f))
    assert {"tc_id", "baseline", "tier0", "tier2"}.issubset(crows[0].keys())


# ---- Task 8: golden full pipeline -------------------------------------------
def _golden():
    return json.loads(
        (_ROOT / "tests" / "fixtures" / "altbasic" / "not_a_key_subtype_golden.json")
        .read_text(encoding="utf-8"))


def test_golden_full_pipeline():
    golden = _golden()
    subtype_rows, tc_steps = M.build(golden["manifest_rows"])
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["subtype_counts"] == golden["expected_subtype_counts"]
    assert s["eligible"] == golden["expected_eligible"]
    assert s["headline_now_unlock"] == golden["expected_headline_now_unlock"]


def test_golden_screen_present_excluded_from_headline():
    golden = _golden()
    subtype_rows, tc_steps = M.build(golden["manifest_rows"])
    reqs = [d["req"] for d in tc_steps[golden["screen_present_only_tc"]]]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0_screen"]) is True
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["deltas"]["screen_present_delta"] >= 1


# ---- Task 9: real manifest self-consistency ---------------------------------
def test_real_manifest_baseline_matches_predecessor():
    rows = M.load_manifest(M.DEFAULT_MANIFEST)
    subtype_rows, tc_steps = M.build(rows)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=5)
    assert s["self_check"] == "ok"            # baseline_eligible == 5
    assert s["not_a_key_steps"] == 189        # predecessor NOT_A_KEY tier
    assert s["total_tcs"] == 236
