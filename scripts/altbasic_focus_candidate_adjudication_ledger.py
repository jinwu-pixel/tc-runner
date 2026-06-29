# -*- coding: utf-8 -*-
"""focus_candidate adjudication ledger + eligibility re-derivation (read-only).

Adjudicates the 61 VERIFIER_FOCUS_CANDIDATE steps (from the NOT_A_KEY subtype ledger)
into 3 classes grounded in manifest `verifier_candidates` + step position, and reports
the defensible adjudicated_delta vs the prior optimistic +39. NO device, NO mutation.
See docs/superpowers/specs/2026-06-29-altbasic-focus-candidate-adjudication-ledger-design.md
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SUB_PATH = os.path.join(_HERE, "altbasic_not_a_key_subtype_ledger.py")
_spec = importlib.util.spec_from_file_location("altbasic_not_a_key_subtype_ledger", _SUB_PATH)
_S = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _S  # register before exec (predecessor chain defines a dataclass)
_spec.loader.exec_module(_S)

# ---- reused predecessor primitives (imported, not forked) --------------------
parse_entry_detail = _S.parse_entry_detail
classify_step = _S.classify_step
subclassify_not_a_key = _S.subclassify_not_a_key
resolution_requirement = _S.resolution_requirement
blocker_reason = _S.blocker_reason
load_manifest = _S.load_manifest
normalize_body = _S.normalize_body
_compact = _S._compact
scenario_eligible = _S.scenario_eligible
assert_no_forbidden = _S.assert_no_forbidden
DEFAULT_MANIFEST = _S.DEFAULT_MANIFEST

NOT_A_KEY = _S.NOT_A_KEY
VERIFIER_FOCUS_CANDIDATE = _S.VERIFIER_FOCUS_CANDIDATE
R_RESOLVED = _S.R_RESOLVED
R_NONEXEC = _S.R_NONEXEC
R_VFOCUS = _S.R_VFOCUS

# ---- new adjudicated requirement / class constants --------------------------
R_VERIFY_HIGH = "VERIFY_POINT_HIGH"
R_NAV_FOCUS = "NAVIGATE_TO_FOCUS"
R_AMBIG_FOCUS = "AMBIGUOUS_RETAIN"

ADJ_CLASS_TO_REQ = {
    "VERIFY_POINT_HIGH": R_VERIFY_HIGH,
    "NAVIGATE_TO_FOCUS": R_NAV_FOCUS,
    "AMBIGUOUS_RETAIN": R_AMBIG_FOCUS,
}

_FOCUS_WORDS = ("focus", "포커싱", "포커스")


# ---- adjudication helpers ---------------------------------------------------
def _later_executable(steps, i) -> bool:
    """True if any step after index i is executable (a key/nav/tap/input/focus action)."""
    for j in range(i + 1, len(steps)):
        if classify_step(steps[j]).get("executable"):
            return True
    return False


def _focus_core(target: str) -> str:
    core = _compact(normalize_body(target))
    for w in _FOCUS_WORDS:
        core = core.replace(w, "")
    return core.replace("-", "")


def _vc_match(target: str, verifier_candidates: str) -> bool:
    core = _focus_core(target)
    if not core:
        return False
    vc = _compact((verifier_candidates or "").replace("literal:", "").replace("literal", ""))
    vc = vc.replace("-", "")
    return core in vc


def adjudicate_focus_candidate(steps, i, verifier_candidates) -> dict:
    """Adjudicate one VERIFIER_FOCUS_CANDIDATE step into 3 classes (spec §4).
    Precedence: any later executable step -> NAVIGATE_TO_FOCUS; else vc-match ->
    VERIFY_POINT_HIGH; else AMBIGUOUS_RETAIN (fail-closed)."""
    target = steps[i].body
    if _later_executable(steps, i):
        cls, pos = "NAVIGATE_TO_FOCUS", "exec_after"
        rat = "later executable step -> focus is a position acted upon"
        dec = "device_navigation"
    elif _vc_match(target, verifier_candidates):
        cls, pos = "VERIFY_POINT_HIGH", "terminal"
        rat = "terminal focus + target in verifier_candidates"
        dec = "verify_point_reclassify_candidate"
    else:
        cls, pos = "AMBIGUOUS_RETAIN", "terminal"
        rat = "terminal focus but target not in verifier_candidates"
        dec = "needs_user_or_device_decision"
    return {
        "adjudication_class": cls,
        "resolution_requirement": ADJ_CLASS_TO_REQ[cls],
        "rationale": rat,
        "position_info": pos,
        "required_decision": dec,
    }


# ---- build ------------------------------------------------------------------
def build(manifest_rows):
    """Return (adj_rows, tc_steps).
    adj_rows: one dict per VERIFIER_FOCUS_CANDIDATE step (the 61).
    tc_steps: {tc_id: [{"req": <enum>, "reason": ...}]} with focus_candidate reqs split
    into R_VERIFY_HIGH / R_NAV_FOCUS / R_AMBIG_FOCUS."""
    adj_rows = []
    tc_steps = defaultdict(list)
    for m in manifest_rows:
        tc_id = m.get("tc_id", "")
        src = m.get("source_file", "")
        ed = m.get("entry_detail", "")
        vc = m.get("verifier_candidates", "")
        steps = parse_entry_detail(ed)
        if not steps:
            tc_steps[tc_id].append({"req": R_NONEXEC, "reason": ""})
            continue
        for i, step in enumerate(steps):
            base = classify_step(step)
            subtype = None
            subtype_req = None
            if base["disposition"] == NOT_A_KEY:
                sub = subclassify_not_a_key(step)
                subtype = sub["not_a_key_subtype"]
                subtype_req = sub["resolution_requirement"]
            if subtype == VERIFIER_FOCUS_CANDIDATE:
                adj = adjudicate_focus_candidate(steps, i, vc)
                adj_rows.append({
                    "tc_id": tc_id,
                    "source_file": src,
                    "original_entry_detail": ed,
                    "extracted_token": step.body,
                    "adjudication_class": adj["adjudication_class"],
                    "resolution_requirement": adj["resolution_requirement"],
                    "position_info": adj["position_info"],
                    "verifier_candidates": vc,
                    "rationale": adj["rationale"],
                    "required_decision": adj["required_decision"],
                })
                tc_steps[tc_id].append({"req": adj["resolution_requirement"], "reason": ""})
            else:
                req = resolution_requirement(base, subtype_req)
                tc_steps[tc_id].append({"req": req, "reason": blocker_reason(base, subtype)})
    return adj_rows, dict(tc_steps)


# ---- cascade + summarize ----------------------------------------------------
# (to_nonexec, to_resolved). tier0 = focus_state already reclassified (committed baseline).
SCENARIOS = {
    "baseline": (set(), set()),
    "tier0": ({R_VFOCUS}, set()),
    "tier0_verify_high": ({R_VFOCUS, R_VERIFY_HIGH}, set()),
    "tier0_all_candidate": ({R_VFOCUS, R_VERIFY_HIGH, R_NAV_FOCUS, R_AMBIG_FOCUS}, set()),
}
_CLASSES = ("VERIFY_POINT_HIGH", "NAVIGATE_TO_FOCUS", "AMBIGUOUS_RETAIN")


def summarize(adj_rows, tc_steps):
    class_counts = Counter(r["adjudication_class"] for r in adj_rows)
    for c in _CLASSES:
        class_counts.setdefault(c, 0)

    elig = {}
    for name, (non, res) in SCENARIOS.items():
        elig[name] = sum(
            1 for s in tc_steps.values()
            if scenario_eligible([d["req"] for d in s], non, res))

    adjudicated_delta = elig["tier0_verify_high"] - elig["tier0"]
    prior_delta = elig["tier0_all_candidate"] - elig["tier0"]
    return {
        "focus_candidate_total": len(adj_rows),
        "total_tcs": len(tc_steps),
        "class_counts": dict(class_counts),          # step-level
        "eligible": elig,                            # TC-level
        "baseline_eligible": elig["baseline"],
        "tier0_eligible": elig["tier0"],
        "verify_high_eligible": elig["tier0_verify_high"],
        "all_candidate_eligible": elig["tier0_all_candidate"],
        "adjudicated_delta": adjudicated_delta,                # HEADLINE
        "prior_focus_candidate_delta": prior_delta,           # reference (== +39)
        "inflation": prior_delta - adjudicated_delta,
        "retained": {c: class_counts[c] for c in ("NAVIGATE_TO_FOCUS", "AMBIGUOUS_RETAIN")},
    }


# ---- IO ---------------------------------------------------------------------
LEDGER_COLUMNS = [
    "tc_id", "source_file", "original_entry_detail", "extracted_token",
    "adjudication_class", "resolution_requirement", "position_info",
    "verifier_candidates", "rationale", "required_decision",
]


def write_ledger_csv(adj_rows, path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in adj_rows:
            w.writerow(r)


def write_cascade_csv(tc_steps, path: str) -> None:
    cols = ["tc_id"] + list(SCENARIOS.keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for tc_id, steps in tc_steps.items():
            reqs = [d["req"] for d in steps]
            row = {"tc_id": tc_id}
            for name, (non, res) in SCENARIOS.items():
                row[name] = scenario_eligible(reqs, non, res)
            w.writerow(row)


def render_summary_md(s: dict) -> str:
    L = []
    L.append("# ALT Basic focus_candidate Adjudication Ledger — Summary\n")
    L.append(f"- focus_candidate steps adjudicated: {s['focus_candidate_total']}  |  "
             f"total TCs: {s['total_tcs']}\n")
    L.append("\n## Adjudication class counts (step-level)\n")
    for c in _CLASSES:
        L.append(f"- {c}: {s['class_counts'][c]}  (step-level)\n")
    L.append("\n## Eligibility (TC-level) — device-pilot eligibility unlock\n")
    L.append("*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*\n")
    L.append(f"- baseline_eligible: {s['baseline_eligible']}  (TC-level)\n")
    L.append(f"- tier0_eligible: {s['tier0_eligible']}  (TC-level)\n")
    L.append(f"- verify_high_eligible: {s['verify_high_eligible']}  (TC-level)\n")
    L.append(f"- all_candidate_eligible: {s['all_candidate_eligible']}  (TC-level, reference)\n")
    L.append("\n## Deltas (TC-level)\n")
    L.append(f"- **headline adjudicated_delta: {s['adjudicated_delta']}** "
             f"(no-device; high-confidence VERIFY_POINT_HIGH reclassification only)\n")
    L.append(f"- prior_focus_candidate_delta: {s['prior_focus_candidate_delta']}  "
             f"(reference upper bound = all 61 reclassified; the NOT_A_KEY ledger's +39)\n")
    L.append(f"- inflation avoided (prior − adjudicated): {s['inflation']}\n")
    L.append("\n## Retained as blockers (not reclassified no-device)\n")
    for c, n in s["retained"].items():
        L.append(f"- {c}: {n}\n")
    L.append("\n*** STOP: host-only adjudication. No device, no reclassification committed. "
             "Await user decision on the high-confidence VERIFY_POINT_HIGH subset. ***\n")
    return "".join(L)


def write_summary_md(s: dict, path: str) -> None:
    md = render_summary_md(s)
    assert_no_forbidden(md)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


# ---- CLI --------------------------------------------------------------------
_AUDIT = os.path.join(_ROOT, "THOR2 - ALT Basic TC Audit")
DEFAULT_LEDGER_CSV = os.path.join(_AUDIT, "FOCUS_CANDIDATE_ADJUDICATION_LEDGER_2026-06-29.csv")
DEFAULT_CASCADE_CSV = os.path.join(_AUDIT, "FOCUS_CANDIDATE_ADJUDICATION_CASCADE_2026-06-29.csv")
DEFAULT_SUMMARY_MD = os.path.join(_AUDIT, "FOCUS_CANDIDATE_ADJUDICATION_SUMMARY_2026-06-29.md")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="ALT Basic focus_candidate adjudication ledger")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--ledger-out", default=DEFAULT_LEDGER_CSV)
    ap.add_argument("--cascade-out", default=DEFAULT_CASCADE_CSV)
    ap.add_argument("--summary-out", default=DEFAULT_SUMMARY_MD)
    a = ap.parse_args(argv)
    rows = load_manifest(a.manifest)
    adj_rows, tc_steps = build(rows)
    s = summarize(adj_rows, tc_steps)
    write_ledger_csv(adj_rows, a.ledger_out)
    write_cascade_csv(tc_steps, a.cascade_out)
    write_summary_md(s, a.summary_out)
    print(f"[fc-adjudication] focus_candidate={s['focus_candidate_total']} tcs={s['total_tcs']}")
    print(f"[fc-adjudication] class_counts(step-level)={s['class_counts']}")
    print(f"[fc-adjudication] baseline={s['baseline_eligible']} tier0={s['tier0_eligible']} "
          f"verify_high={s['verify_high_eligible']} all_candidate={s['all_candidate_eligible']}")
    print(f"[fc-adjudication] adjudicated_delta(HEADLINE)={s['adjudicated_delta']} "
          f"prior_focus_candidate_delta={s['prior_focus_candidate_delta']} "
          f"inflation={s['inflation']}")
    print("*** STOP: host-only. ***")


if __name__ == "__main__":
    main()
