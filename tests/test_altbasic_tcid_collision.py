"""Tests for scripts/altbasic_tcid_collision_check.py (P-1 — synth prep 선행 게이트).

Pure collision/dedupe/audit functions tested with synthetic inputs only.
NO file/Excel IO, NO device, NO wall-clock. (IO wrappers exercise openpyxl/glob
and are not unit-tested here.)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_tcid_collision_check.py"
_spec = importlib.util.spec_from_file_location("altbasic_tcid_collision_check", _PATH)
C = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_tcid_collision_check"] = C
_spec.loader.exec_module(C)


# ─── find_collisions ───

def test_find_collisions_none():
    res = C.find_collisions(["A", "B", "C"], existing={"X", "Y"})
    assert res["cross_batch"] == []
    assert res["internal_dup"] == []


def test_find_collisions_cross_batch():
    res = C.find_collisions(["A", "B"], existing={"B", "Z"})
    assert res["cross_batch"] == ["B"]
    assert res["internal_dup"] == []


def test_find_collisions_internal_dup():
    res = C.find_collisions(["A", "B", "A"], existing=set())
    assert res["internal_dup"] == ["A"]
    assert res["cross_batch"] == []


# ─── resolve_collisions_with_suffix (deterministic) ───

def test_resolve_no_collision_unchanged():
    assert C.resolve_collisions_with_suffix(["A", "B"], existing={"X"}) == ["A", "B"]


def test_resolve_cross_batch_gets_suffix_2():
    assert C.resolve_collisions_with_suffix(["A"], existing={"A"}) == ["A_2"]


def test_resolve_internal_dup_second_gets_suffix():
    # 첫 A는 유지, 둘째 A는 결정적으로 A_2
    assert C.resolve_collisions_with_suffix(["A", "A"], existing=set()) == ["A", "A_2"]


def test_resolve_cascade_skips_taken_suffix():
    # existing에 A, A_2 있으면 첫 A→A_3, 둘째 A→A_4 (결정적 최소 미사용 suffix)
    assert C.resolve_collisions_with_suffix(["A", "A"], existing={"A", "A_2"}) == ["A_3", "A_4"]


def test_resolve_output_has_no_collisions():
    existing = {"A", "B"}
    assigned = ["A", "A", "B", "C"]
    out = C.resolve_collisions_with_suffix(assigned, existing)
    # 결과는 서로 유일하고 existing과도 충돌 없음
    assert len(set(out)) == len(out)
    assert set(out).isdisjoint(existing)


def test_resolve_is_deterministic():
    a = C.resolve_collisions_with_suffix(["A", "A", "A"], existing={"A"})
    b = C.resolve_collisions_with_suffix(["A", "A", "A"], existing={"A"})
    assert a == b == ["A_2", "A_3", "A_4"]


# ─── audit_sheet_tcid_dups (sheet 내 TC ID 유일성) ───

def test_audit_no_dups():
    records = [("S1", "10"), ("S1", "11"), ("S2", "10")]
    assert C.audit_sheet_tcid_dups(records) == {}


def test_audit_dup_within_sheet():
    records = [("S1", "10"), ("S1", "10"), ("S1", "11")]
    assert C.audit_sheet_tcid_dups(records) == {"S1": {"10": 2}}


def test_audit_same_tcid_across_sheets_is_not_dup():
    # 다른 sheet의 동일 TC ID는 dup 아님 (per-sheet 유일성)
    records = [("S1", "10"), ("S2", "10")]
    assert C.audit_sheet_tcid_dups(records) == {}
