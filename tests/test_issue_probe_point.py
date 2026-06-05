"""Task 5 — IssueProbePoint sidecar (menu-tree v1.2 issue-probe coordinate).

Represents an issue-reproduction coordinate (screen_id + condition + trials +
verdict) as an append-only sidecar. 1호 = 2026-06-05 privacy settle-probe.
Depends only on ledger-summary values, never on the raw probe bundles (local
carry). See docs/superpowers/plans/2026-06-05-menu-tree-v1_2-tdd-plan.md (Task 5).
"""
from __future__ import annotations

import json
from pathlib import Path

from src import menu_anchor as ma

_ROOT = Path(__file__).resolve().parent.parent
_LEDGER = "THOR2_K - Settings/catalog/MENU_TREE_RUNS.md"


def _privacy_probe():
    return ma.IssueProbePoint(
        issue_id="menu_tree_privacy_anomaly",
        probe_id="privacy_settle_probe_20260604",
        source_runs=["20260604T102316Z"],
        screen_id="settings_d1_privacy",
        domain="settings",
        entry_action="android.settings.PRIVACY_SETTINGS",
        entry_component=None,
        observed_condition="102316Z full run: privacy REACHED->FOCUS_MISMATCH (focus=device_info)",
        hypothesis="settle race / residual device_info window after warm-up",
        trials_summary=ma.make_trials_summary(total=20, valid=20, mismatch_count=0),
        verdict="not_regression",
        evidence_refs={"ledger_path": _LEDGER, "artifact_paths": []},
        notes="A(HOME-clean) 0/5, B(device_info warm) 0/5; post total 0/20 mismatch. "
              "B pre_focus device_info 5/5 confirmed. Phase 2 not needed.",
    )


def test_make_trials_summary_computes_rate():
    assert ma.make_trials_summary(20, 20, 0) == {
        "total": 20, "valid": 20, "mismatch_count": 0, "mismatch_rate": 0.0}
    assert ma.make_trials_summary(20, 20, 3)["mismatch_rate"] == 0.15
    # no division by zero when nothing valid
    assert ma.make_trials_summary(0, 0, 0)["mismatch_rate"] == 0.0


def test_suggest_verdict_thresholds():
    assert ma.suggest_verdict(0.0) == "not_regression"
    assert ma.suggest_verdict(0.2) == "inconclusive"
    assert ma.suggest_verdict(0.6) == "regression_candidate"


def test_verdict_vocab_locked():
    assert set(ma.ISSUE_PROBE_VERDICTS) == {
        "observed_one_off", "not_regression", "regression_candidate", "inconclusive"}
    assert _privacy_probe().verdict in ma.ISSUE_PROBE_VERDICTS


def test_issue_probe_point_roundtrip():
    p = _privacy_probe()
    assert ma.IssueProbePoint.from_dict(json.loads(json.dumps(p.to_dict()))) == p


def test_issue_probe_has_no_anchor_text_fields():
    p = _privacy_probe()
    # issue-probe is a reproduction coordinate, NOT an anchor text mapping
    assert not hasattr(p, "source_expected_texts")
    assert not hasattr(p, "device_observed_texts")


def test_ledger_reference_preserved():
    p = _privacy_probe()
    assert p.evidence_refs["ledger_path"] == _LEDGER
    assert p.source_runs == ["20260604T102316Z"]


def test_write_probe_json_roundtrip_to_tmp(tmp_path):
    p = _privacy_probe()
    out = tmp_path / "menu_tree_privacy_anomaly_20260604.json"
    ma.write_probe_json(p, out)
    assert out.exists()
    assert ma.load_probe_json(out) == p


def test_privacy_fixture_is_first_case():
    fx = _ROOT / "tests" / "fixtures" / "anchor" / "issue_probe_privacy.json"
    p = ma.load_probe_json(fx)
    assert p.issue_id == "menu_tree_privacy_anomaly"
    assert p.screen_id == "settings_d1_privacy"
    assert p.domain == "settings"
    assert p.entry_action == "android.settings.PRIVACY_SETTINGS"
    assert p.trials_summary["mismatch_rate"] == 0.0
    assert p.verdict == "not_regression"
    assert "20260604T102316Z" in p.source_runs
    assert p.evidence_refs["ledger_path"] == _LEDGER
