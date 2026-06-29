"""Tests for scripts/altbasic_adjudicate_resolution_ledger.py (read-only).
Pure adjudicator + real-manifest self-checks. NO device, NO network, NO wall-clock.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_adjudicate_resolution_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_adjudicate_resolution_ledger", _PATH)
A = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_adjudicate_resolution_ledger"] = A
_spec.loader.exec_module(A)


def _cls(body):
    return A.adjudicate_adjudicate(body)["adjudication_class"]


# ---- constants / import -----------------------------------------------------
def test_imports_and_constants():
    assert callable(A.parse_entry_detail)
    assert A.ADJUDICATE == "ADJUDICATE"
    assert A.R_ADJ_HIGH == "ADJUDICATE_RESOLVABLE_HIGH"
    assert A.R_ADJ_DISJ == "ADJUDICATE_DISJUNCTION_CHOICE"
    assert A.R_ADJ_AMBIG == "ADJUDICATE_AMBIGUOUS"


# ---- adjudicate rule --------------------------------------------------------
def test_arrow_glyph_is_resolvable_high():
    assert _cls("Navi 키( ↓) 버튼을 누른다.") == "RESOLVABLE_HIGH"
    assert _cls("Navi 키( →) 버튼을 누른다.") == "RESOLVABLE_HIGH"
    assert _cls("Navi 키( ←) 버튼을 누른다.") == "RESOLVABLE_HIGH"


def test_text_direction_is_resolvable_high():
    assert _cls("포커스 활성화된 상태에서 Navi Up키 입력한다") == "RESOLVABLE_HIGH"
    assert _cls("포커스 활성화된 상태에서 Navi Down키 입력한다") == "RESOLVABLE_HIGH"


def test_state_word_does_not_false_match_direction():
    # '상태' must NOT inject UP; the only direction is Down -> single -> HIGH
    out = A.adjudicate_adjudicate("포커스 활성화된 상태에서 Navi Down키 입력한다")
    assert out["adjudication_class"] == "RESOLVABLE_HIGH"
    assert out["proposed_keycode"] == "20"


def test_parenthetical_ok_is_resolvable_high():
    assert _cls("Navi 키(OK) 버튼을 누른다.") == "RESOLVABLE_HIGH"


def test_disjunction_is_choice():
    assert _cls("네비키 또는 OK키 입력") == "DISJUNCTION_CHOICE"
    assert _cls("네비키나 OK키 입력") == "DISJUNCTION_CHOICE"
    assert _cls("Press back 또는 cancel") == "DISJUNCTION_CHOICE"


def test_all_marker_is_ambiguous():
    assert _cls("Navi 키(전체) 버튼을 누른다.") == "AMBIGUOUS_RETAIN"
    assert _cls("Navi 키(모든) 버튼을 누른다.") == "AMBIGUOUS_RETAIN"


# ---- golden -----------------------------------------------------------------
def _golden():
    return json.loads(
        (_ROOT / "tests" / "fixtures" / "altbasic" / "adjudicate_resolution_golden.json")
        .read_text(encoding="utf-8"))


def test_golden_summary():
    g = _golden()
    adj_rows, tc_steps = A.build(g["manifest_rows"])
    s = A.summarize(adj_rows, tc_steps)
    assert s["adjudicate_total"] == g["expected_adjudicate_total"]
    assert s["class_counts"] == g["expected_class_counts"]
    assert s["eligible"] == g["expected_eligible"]
    assert s["adjudicated_delta"] == g["expected_adjudicated_delta"]
    assert s["disjunction_delta"] == g["expected_disjunction_delta"]
    assert s["prior_adjudicate_delta"] == g["expected_prior_adjudicate_delta"]


# ---- IO ---------------------------------------------------------------------
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


# ---- real manifest self-consistency ----------------------------------------
def test_real_manifest_self_consistency():
    rows = A.load_manifest(A.DEFAULT_MANIFEST)
    adj_rows, tc_steps = A.build(rows)
    s = A.summarize(adj_rows, tc_steps)
    assert s["adjudicate_total"] == 53
    assert sum(s["class_counts"].values()) == 53
    assert s["baseline_eligible"] == 5
    assert s["tier0_eligible"] == 6
    # all-ADJUDICATE-resolved must reproduce the subtype ledger's +18
    assert s["prior_adjudicate_delta"] == 18
    assert 0 <= s["adjudicated_delta"] <= 18
