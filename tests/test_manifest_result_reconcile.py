"""Tests for scripts/manifest_result_reconcile.py (P-4 — manifest result/join 컬럼).

tc_id를 안정 조인 키로, (manifest 선언 vs 구현 yaml vs RESULT 판정) 3원을 자동
reconcile — chunk-N/구현/결과 ±1~3 불일치·annex manifest 밖 실행(C12) 드리프트 방지.
순수 함수 테스트.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "manifest_result_reconcile.py"
_spec = importlib.util.spec_from_file_location("manifest_result_reconcile", _PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["manifest_result_reconcile"] = M
_spec.loader.exec_module(M)


def test_reconcile_all_match():
    r = M.reconcile_by_tcid(["A", "B"], ["A", "B"], {"A": "GREEN", "B": "GREEN"})
    assert r["summary"]["reconciled"] == ["A", "B"]
    assert r["summary"]["manifest_not_implemented"] == []
    assert r["summary"]["implemented_no_result"] == []
    assert r["summary"]["orphan_result"] == []


def test_reconcile_manifest_not_implemented():
    r = M.reconcile_by_tcid(["A", "B"], ["A"], {"A": "GREEN"})
    assert r["summary"]["manifest_not_implemented"] == ["B"]


def test_reconcile_implemented_no_result():
    r = M.reconcile_by_tcid(["A"], ["A"], {})
    assert r["summary"]["implemented_no_result"] == ["A"]


def test_reconcile_orphan_result():
    # annex가 manifest 밖에서 실행됨 (C12)
    r = M.reconcile_by_tcid(["A"], ["A"], {"A": "GREEN", "ANNEX": "GREEN"})
    assert r["summary"]["orphan_result"] == ["ANNEX"]


def test_reconcile_rows_join_status():
    r = M.reconcile_by_tcid(["A"], [], {})
    assert r["rows"] == [
        {"tc_id": "A", "in_manifest": True, "implemented": False, "result": ""}
    ]


def test_reconcile_rows_sorted_union_of_all_ids():
    r = M.reconcile_by_tcid(["B"], ["A"], {"C": "GREEN"})
    assert [row["tc_id"] for row in r["rows"]] == ["A", "B", "C"]
