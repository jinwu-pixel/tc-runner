"""Tests for scripts/ledger_recompute.py (P-3 — 단일 원장 재집계).

판정 CSV(단일 원장)에서 summary 수치를 결정적으로 재집계 — 수기 집계·추정치 병기
드리프트(FAILURE_TAXONOMY C1) 방지. judge_method(auto/human) 분리. 순수 함수 테스트.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "ledger_recompute.py"
_spec = importlib.util.spec_from_file_location("ledger_recompute", _PATH)
L = importlib.util.module_from_spec(_spec)
sys.modules["ledger_recompute"] = L
_spec.loader.exec_module(L)


_ROWS = [
    {"disposition": "KEEP", "judge_method": "human"},
    {"disposition": "KEEP", "judge_method": "human"},
    {"disposition": "EXCLUDE", "judge_method": "auto"},
    {"disposition": "UNREVIEWED", "judge_method": ""},
]


# ─── tally ───

def test_tally_counts():
    assert L.tally(_ROWS, "disposition") == {"KEEP": 2, "EXCLUDE": 1, "UNREVIEWED": 1}


def test_tally_missing_key_is_empty_bucket():
    rows = [{"disposition": "KEEP"}, {}]
    assert L.tally(rows, "disposition") == {"KEEP": 1, "": 1}


# ─── cross_tally (nested, JSON-safe) ───

def test_cross_tally_nested():
    assert L.cross_tally(_ROWS, "disposition", "judge_method") == {
        "KEEP": {"human": 2},
        "EXCLUDE": {"auto": 1},
        "UNREVIEWED": {"": 1},
    }


# ─── recompute_ledger_summary ───

def test_recompute_total_and_judged_denominators():
    s = L.recompute_ledger_summary(
        _ROWS, "disposition", "judge_method", undecided_values=("UNREVIEWED",)
    )
    assert s["total"] == 4
    assert s["judged"] == 3  # UNREVIEWED 제외 (미판단분은 비율 분모 제외)


def test_recompute_by_method_separates_auto_human():
    s = L.recompute_ledger_summary(
        _ROWS, "disposition", "judge_method", undecided_values=("UNREVIEWED",)
    )
    assert s["by_method"] == {"human": 2, "auto": 1, "": 1}


def test_recompute_by_verdict_and_cross():
    s = L.recompute_ledger_summary(
        _ROWS, "disposition", "judge_method", undecided_values=("UNREVIEWED",)
    )
    assert s["by_verdict"] == {"KEEP": 2, "EXCLUDE": 1, "UNREVIEWED": 1}
    assert s["by_verdict_method"]["KEEP"] == {"human": 2}


def test_recompute_empty_undecided_means_all_judged():
    s = L.recompute_ledger_summary(_ROWS, "disposition", "judge_method")
    assert s["total"] == 4
    assert s["judged"] == 4
