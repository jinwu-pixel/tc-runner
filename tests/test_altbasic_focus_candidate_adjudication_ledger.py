"""Tests for scripts/altbasic_focus_candidate_adjudication_ledger.py (read-only).
Pure adjudicator tested with synthetic strings + real manifest self-checks.
NO device, NO network, NO wall-clock.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_focus_candidate_adjudication_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_focus_candidate_adjudication_ledger", _PATH)
A = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_focus_candidate_adjudication_ledger"] = A
_spec.loader.exec_module(A)


# ---- T1: scaffold + import --------------------------------------------------
def test_imports_predecessor_primitives():
    assert callable(A.parse_entry_detail)
    assert callable(A.classify_step)
    assert callable(A.subclassify_not_a_key)
    assert A.VERIFIER_FOCUS_CANDIDATE == "VERIFIER_FOCUS_CANDIDATE"


def test_adjudicated_constants():
    assert A.R_VERIFY_HIGH == "VERIFY_POINT_HIGH"
    assert A.R_NAV_FOCUS == "NAVIGATE_TO_FOCUS"
    assert A.R_AMBIG_FOCUS == "AMBIGUOUS_RETAIN"


# ---- T2: helpers ------------------------------------------------------------
def test_later_executable():
    steps = A.parse_entry_detail("press_key:wifi focus > Press down")
    assert A._later_executable(steps, 0) is True   # Press down follows
    assert A._later_executable(steps, 1) is False  # terminal
    steps2 = A.parse_entry_detail("press_key:Home 버튼 누른다 > press_key:블루투스 focus")
    assert A._later_executable(steps2, 1) is False  # focus is terminal


def test_vc_match():
    assert A._vc_match("wifi focus", "literal: 모바일 데이터") is False
    assert A._vc_match("wifi focus", "퀵패널 / 알림창 / wifi") is True
    assert A._vc_match("블루투스 focus", "literal: 블루투스") is True
    assert A._vc_match("집중 모드 focus", "literal: 전혀다른값") is False


# ---- T3: adjudicate ---------------------------------------------------------
def test_adjudicate_navigate_when_exec_after():
    steps = A.parse_entry_detail("press_key:wifi focus > Press down")
    assert A.adjudicate_focus_candidate(steps, 0, "literal: 모바일 데이터")["adjudication_class"] \
        == "NAVIGATE_TO_FOCUS"


def test_adjudicate_back_cancel_is_navigate_not_verify():
    # exec-after (back/cancel) wins over a verifier match -> NAVIGATE, not VERIFY
    steps = A.parse_entry_detail("press_key:wifi focus > Press back 또는 cancel")
    assert A.adjudicate_focus_candidate(steps, 0, "퀵패널 / 알림창 / wifi")["adjudication_class"] \
        == "NAVIGATE_TO_FOCUS"


def test_adjudicate_verify_point_high_terminal_vc_match():
    steps = A.parse_entry_detail("press_key:Home 버튼 누른다 > press_key:블루투스 focus")
    out = A.adjudicate_focus_candidate(steps, 1, "literal: 블루투스")
    assert out["adjudication_class"] == "VERIFY_POINT_HIGH"
    assert out["resolution_requirement"] == A.R_VERIFY_HIGH
    assert out["position_info"] == "terminal"


def test_adjudicate_ambiguous_terminal_no_vc_match():
    steps = A.parse_entry_detail("press_key:Home 버튼 누른다 > press_key:집중 모드 focus")
    assert A.adjudicate_focus_candidate(steps, 1, "literal: 전혀다른값")["adjudication_class"] \
        == "AMBIGUOUS_RETAIN"


# ---- T4: build --------------------------------------------------------------
def _golden():
    return json.loads(
        (_ROOT / "tests" / "fixtures" / "altbasic" / "focus_candidate_adjudication_golden.json")
        .read_text(encoding="utf-8"))


def test_build_emits_one_row_per_focus_candidate():
    adj_rows, tc_steps = A.build(_golden()["manifest_rows"])
    assert len(adj_rows) == 4
    by_tc = {r["tc_id"]: r["adjudication_class"] for r in adj_rows}
    assert by_tc["G_NAV_QPN"] == "NAVIGATE_TO_FOCUS"
    assert by_tc["G_VERIFY"] == "VERIFY_POINT_HIGH"
    assert by_tc["G_AMBIG"] == "AMBIGUOUS_RETAIN"


def test_build_tc_steps_split_requirement():
    _, tc_steps = A.build(_golden()["manifest_rows"])
    assert [d["req"] for d in tc_steps["G_VERIFY"]] == [A.R_RESOLVED, A.R_VERIFY_HIGH]


# ---- T5/T7: summarize + golden ---------------------------------------------
def test_golden_summary():
    g = _golden()
    adj_rows, tc_steps = A.build(g["manifest_rows"])
    s = A.summarize(adj_rows, tc_steps)
    assert s["focus_candidate_total"] == g["expected_focus_candidate_total"]
    assert s["class_counts"] == g["expected_class_counts"]
    assert s["eligible"] == g["expected_eligible"]
    assert s["adjudicated_delta"] == g["expected_adjudicated_delta"]
    assert s["prior_focus_candidate_delta"] == g["expected_prior_focus_candidate_delta"]


# ---- T6: IO + forbidden -----------------------------------------------------
def test_summary_md_no_forbidden_and_labels():
    g = _golden()
    adj_rows, tc_steps = A.build(g["manifest_rows"])
    md = A.render_summary_md(A.summarize(adj_rows, tc_steps))
    for w in ("PASS", "RUNNABLE_NOW", "validated"):
        assert w not in md
    assert "adjudicated_delta" in md
    assert "(step-level)" in md and "(TC-level)" in md


def test_write_outputs_roundtrip(tmp_path):
    import csv as _csv
    g = _golden()
    adj_rows, tc_steps = A.build(g["manifest_rows"])
    s = A.summarize(adj_rows, tc_steps)
    led = tmp_path / "l.csv"
    cas = tmp_path / "c.csv"
    summ = tmp_path / "s.md"
    A.write_ledger_csv(adj_rows, str(led))
    A.write_cascade_csv(tc_steps, str(cas))
    A.write_summary_md(s, str(summ))
    with open(led, encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) == 4
    assert set(A.LEDGER_COLUMNS).issubset(rows[0].keys())
    with open(cas, encoding="utf-8-sig", newline="") as f:
        crows = list(_csv.DictReader(f))
    assert {"tc_id", "baseline", "tier0_verify_high", "tier0_all_candidate"}.issubset(crows[0].keys())


# ---- T8: real manifest self-consistency ------------------------------------
def test_real_manifest_self_consistency():
    rows = A.load_manifest(A.DEFAULT_MANIFEST)
    adj_rows, tc_steps = A.build(rows)
    s = A.summarize(adj_rows, tc_steps)
    assert s["focus_candidate_total"] == 61
    assert sum(s["class_counts"].values()) == 61
    assert s["baseline_eligible"] == 5
    assert s["tier0_eligible"] == 6
    # prior optimistic (all 61 reclassified) must reproduce the NOT_A_KEY ledger's +39
    assert s["prior_focus_candidate_delta"] == 39
    # headline must be <= prior (high-confidence subset), and non-negative
    assert 0 <= s["adjudicated_delta"] <= 39
