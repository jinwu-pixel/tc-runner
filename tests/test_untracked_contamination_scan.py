"""Tests for tools/untracked_contamination_scan.py (P-2 — workflow agent 오염 스캔).

phantom side-effect(batch11 4건이 batch10 dir에 untracked 오기록) 재발 방지.
순수 매칭 함수를 synthetic 경로로 테스트 (git IO wrapper는 별도).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--protected", ""],
        ["--protected", "   "],
        ["--protected", " safe "],
        ["--protected", "safe", "--protected", "\t"],
    ],
    ids=[
        "omitted",
        "empty",
        "whitespace",
        "surrounding-whitespace",
        "mixed-valid-and-blank",
    ],
)
def test_main_rejects_vacuous_protected_before_git(
    argv,
    monkeypatch,
    capsys,
):
    def unexpected_git_call(_cwd):
        raise AssertionError("git_untracked must not run for invalid input")

    monkeypatch.setattr(S, "git_untracked", unexpected_git_call)

    assert S.main(argv) == 2
    assert "--protected" in capsys.readouterr().err


def test_main_valid_prefix_clean_returns_zero(monkeypatch):
    observed = []

    def fake_git(cwd):
        observed.append(cwd)
        return []

    monkeypatch.setattr(S, "git_untracked", fake_git)

    assert S.main(["--protected", "safe", "--cwd", "repo"]) == 0
    assert observed == ["repo"]


def test_main_valid_prefix_phantom_returns_one(monkeypatch):
    monkeypatch.setattr(
        S,
        "git_untracked",
        lambda _cwd: ["safe/PHANTOM.yaml"],
    )

    assert S.main(["--protected", "safe"]) == 1


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "status"],
            stderr="not a git repository",
        ),
        OSError("git unavailable"),
    ],
    ids=["called-process-error", "os-error"],
)
def test_main_git_failure_returns_infra_exit_three(
    failure,
    monkeypatch,
    capsys,
):
    def failed_git(_cwd):
        raise failure

    monkeypatch.setattr(S, "git_untracked", failed_git)

    assert S.main(["--protected", "safe"]) == 3
    assert "infra failure" in capsys.readouterr().err.lower()
