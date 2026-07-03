"""Tests for tools/untracked_contamination_scan.py (P-2 — workflow agent 오염 스캔).

phantom side-effect(batch11 4건이 batch10 dir에 untracked 오기록) 재발 방지.
순수 매칭 함수를 synthetic 경로로 테스트 (git IO wrapper는 별도).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "tools" / "untracked_contamination_scan.py"
_spec = importlib.util.spec_from_file_location("untracked_contamination_scan", _PATH)
S = importlib.util.module_from_spec(_spec)
sys.modules["untracked_contamination_scan"] = S
_spec.loader.exec_module(S)

_PROTECTED = ["THOR2 - ALT Basic TC Audit"]


def test_scan_flags_untracked_under_protected():
    flagged = S.scan_contamination(
        ["THOR2 - ALT Basic TC Audit/stage1_x/PHANTOM.yaml"],
        protected_prefixes=_PROTECTED,
        allow_globs=[],
    )
    assert flagged == ["THOR2 - ALT Basic TC Audit/stage1_x/PHANTOM.yaml"]


def test_scan_allows_matching_glob():
    flagged = S.scan_contamination(
        ["THOR2 - ALT Basic TC Audit/scratch/tmp.json"],
        protected_prefixes=_PROTECTED,
        allow_globs=["*/scratch/*"],
    )
    assert flagged == []


def test_scan_ignores_outside_protected():
    flagged = S.scan_contamination(
        ["reports/run/x.json"],
        protected_prefixes=_PROTECTED,
        allow_globs=[],
    )
    assert flagged == []


def test_scan_normalizes_backslashes():
    flagged = S.scan_contamination(
        ["THOR2 - ALT Basic TC Audit\\dir\\P.yaml"],
        protected_prefixes=_PROTECTED,
        allow_globs=[],
    )
    assert flagged == ["THOR2 - ALT Basic TC Audit/dir/P.yaml"]


def test_scan_empty():
    assert S.scan_contamination([], ["X"], []) == []


def test_scan_prefix_boundary_not_partial():
    # "...Audit2/..." must NOT match prefix "...Audit" (경계 오탐 방지)
    flagged = S.scan_contamination(
        ["THOR2 - ALT Basic TC Audit2/x.yaml"],
        protected_prefixes=_PROTECTED,
        allow_globs=[],
    )
    assert flagged == []


def test_scan_multiple_mixed():
    flagged = S.scan_contamination(
        [
            "THOR2 - ALT Basic TC Audit/batch10/GOOD.yaml",   # flagged
            "THOR2 - ALT Basic TC Audit/scratch/x.json",       # allowed
            "src/foo.py",                                       # outside
        ],
        protected_prefixes=_PROTECTED,
        allow_globs=["*/scratch/*"],
    )
    assert flagged == ["THOR2 - ALT Basic TC Audit/batch10/GOOD.yaml"]
