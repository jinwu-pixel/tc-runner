"""Task 6 — failure_reason classification (menu-tree v1.2, design only).

Pure mapping from (reach_status / ActionSafety / expected-vs-observed texts /
document mismatch) to a failure_reason. NO runner/reporter integration, NO
schema bump. closest_menu_node (I3) stays a stub. See
docs/superpowers/plans/2026-06-05-menu-tree-v1_2-tdd-plan.md (Task 6).
"""
from __future__ import annotations

import ast
import inspect

import pytest

from src import menu_anchor as ma


def _r(**kw):
    return ma.classify_failure_reason(**kw)


def test_failure_reason_vocab_locked():
    assert set(ma.FAILURE_REASONS) == {
        "unreachable", "focus_mismatch", "text_missing", "no_device_observation",
        "risky_action", "input_required", "document_drift",
    }


@pytest.mark.parametrize("status", ["UNREACHABLE_NO_ACTION", "LAUNCH_FAILED"])
def test_unreachable(status):
    assert _r(reach_status=status) == "unreachable"


def test_focus_mismatch():
    assert _r(reach_status="FOCUS_MISMATCH") == "focus_mismatch"


def test_input_required():
    assert _r(action_safety=ma.ActionSafety.INPUT_REQUIRED) == "input_required"


@pytest.mark.parametrize("safety", [
    ma.ActionSafety.SELECTION_GATED,
    ma.ActionSafety.PRIVILEGED_SHELL,
    ma.ActionSafety.DESTRUCTIVE,
    ma.ActionSafety.UNKNOWN_UNSAFE,
])
def test_risky_action(safety):
    assert _r(action_safety=safety) == "risky_action"


@pytest.mark.parametrize("safety", [
    ma.ActionSafety.READ_ONLY, ma.ActionSafety.READ_ONLY_SHELL,
    ma.ActionSafety.NAVIGATION_ONLY,
])
def test_safe_actions_do_not_trigger_risky(safety):
    assert _r(action_safety=safety) is None


# --- no_device_observation vs text_missing (the key split) -----------------

def test_no_device_observation_when_observed_absent():
    assert _r(expected_texts=["개인 정보 보호"], observed_texts=None) == "no_device_observation"
    assert _r(expected_texts=["개인 정보 보호"], observed_texts=[]) == "no_device_observation"


def test_text_missing_only_when_observed_present_but_lacks_expected():
    assert _r(expected_texts=["A", "B"], observed_texts=["A"]) == "text_missing"


def test_no_text_failure_when_all_expected_observed():
    assert _r(expected_texts=["A"], observed_texts=["A", "B"]) is None


def test_empty_expected_texts_is_not_a_failure():
    assert _r(expected_texts=[], observed_texts=[]) is None


def test_document_drift_when_flagged():
    assert _r(document_mismatch=True) == "document_drift"


def test_no_failure_when_all_clear():
    assert _r(reach_status="REACHED", action_safety=ma.ActionSafety.READ_ONLY,
              expected_texts=["A"], observed_texts=["A"]) is None


# --- priority ---------------------------------------------------------------

def test_reach_status_outranks_risky_action():
    assert _r(reach_status="FOCUS_MISMATCH",
              action_safety=ma.ActionSafety.PRIVILEGED_SHELL) == "focus_mismatch"


def test_unreachable_outranks_text_branch():
    assert _r(reach_status="UNREACHABLE_NO_ACTION",
              expected_texts=["A"], observed_texts=["B"]) == "unreachable"


def test_input_required_outranks_text_branch():
    assert _r(action_safety=ma.ActionSafety.INPUT_REQUIRED,
              expected_texts=["A"], observed_texts=None) == "input_required"


def test_text_branch_outranks_document_drift():
    assert _r(expected_texts=["A"], observed_texts=["B"], document_mismatch=True) == "text_missing"


# --- closest_menu_node stub (I3 deferred) ----------------------------------

def test_closest_menu_node_is_stub():
    # Algorithm (fingerprint/text distance) is deferred (I3); stub returns None.
    assert ma.closest_menu_node() is None


# --- layering: no runner/reporter/cli coupling -----------------------------

def test_menu_anchor_does_not_import_runner_or_reporter():
    tree = ast.parse(inspect.getsource(ma))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [n.name for n in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    banned = ("reporter", "action_runner", "cli")
    assert not any(any(b in m for b in banned) for m in modules), modules
