"""Task 3 — corpus anchor-extraction audit (read-only, no device).

Replays extract/join over the committed TC corpus and locks the 2026-06-05
audit facts as regression guards:
  - exported_tc1 44 = 25 top-level + 19 _autoconverted; exported_ss_call 16; golden 3
  - Settings baseline direct mapping is LOW
  - APN is a settings-domain baseline gap
  - SeniorShield is app:<pkg> reference-only domain
  - shell carries the main physical-risk signal
See docs/superpowers/plans/2026-06-05-menu-tree-v1_2-tdd-plan.md (Task 3).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "anchor_corpus_audit.py"
_spec = importlib.util.spec_from_file_location("anchor_corpus_audit", _PATH)
aca = importlib.util.module_from_spec(_spec)
sys.modules["anchor_corpus_audit"] = aca
_spec.loader.exec_module(aca)

_BASELINE = _ROOT / "THOR2_K - Settings" / "catalog" / "menu_tree_baseline_20260604T102316Z.json"


def _audit():
    return aca.audit_corpus(_ROOT, baseline_path=_BASELINE)


def test_corpus_file_counts_decomposed():
    corpus = _audit()["corpus"]
    assert corpus["exported_tc1"] == {"files": 44, "top_level": 25, "autoconverted": 19}
    assert corpus["exported_ss_call"]["files"] == 16
    assert corpus["golden_tc_set"]["files"] == 3
    assert corpus["total_files"] == 63


def test_summary_top_level_structure():
    s = _audit()
    assert set(s) == {"corpus", "candidates", "settings_deeplinks", "baseline", "action_safety"}


def test_seniorshield_is_app_domain_reference_only():
    cands = _audit()["candidates"]
    assert cands["app_packages"].get("com.example.seniorshield", 0) > 0
    # all three domain kinds appear in the corpus
    assert cands["by_domain"]["settings"] > 0
    assert cands["by_domain"]["app"] > 0
    assert cands["by_domain"]["external"] > 0


def test_apn_is_settings_deeplink_and_baseline_gap():
    s = _audit()
    assert "android.settings.APN_SETTINGS" in s["settings_deeplinks"]
    # baseline has no APN screen -> APN is a settings-domain gap
    assert "android.settings.APN_SETTINGS" not in s["baseline"]["mapped_actions"]


def test_settings_baseline_direct_mapping_is_low():
    baseline = _audit()["baseline"]
    assert baseline["screens"] == 17
    assert baseline["mapped_candidates"] <= 3


def test_shell_carries_main_risk_signal():
    safety = _audit()["action_safety"]
    assert safety.get("PRIVILEGED_SHELL", 0) > 0
    assert safety.get("DESTRUCTIVE", 0) > 0


def test_write_audit_json_roundtrip_to_tmp(tmp_path):
    s = _audit()
    out = tmp_path / "corpus_audit.json"
    aca.write_audit_json(s, out)
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == s


def test_audit_matches_golden_snapshot():
    # Regression snapshot: corpus + baseline are committed, so the audit is
    # deterministic. Any meaningful change to the corpus or extract/join logic
    # must update this golden intentionally.
    golden_path = _ROOT / "tests" / "fixtures" / "anchor" / "corpus_audit_baseline.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert _audit() == golden
