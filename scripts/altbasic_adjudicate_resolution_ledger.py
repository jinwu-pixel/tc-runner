# -*- coding: utf-8 -*-
"""ADJUDICATE resolution ledger + eligibility re-derivation (read-only).

Adjudicates the 53 ADJUDICATE-disposition steps (disjunction/qualified keys) into 3
classes (RESOLVABLE_HIGH / DISJUNCTION_CHOICE / AMBIGUOUS_RETAIN) and reports the
defensible high-confidence delta vs the prior +18. The last device-free lever.
NO device, NO mutation. See docs/superpowers/specs/2026-06-29-altbasic-adjudicate-resolution-ledger-design.md
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

# ---- reused predecessor primitives -------------------------------------------
parse_entry_detail = _S.parse_entry_detail
classify_step = _S.classify_step
subclassify_not_a_key = _S.subclassify_not_a_key
resolution_requirement = _S.resolution_requirement
blocker_reason = _S.blocker_reason
load_manifest = _S.load_manifest
_compact = _S._compact
scenario_eligible = _S.scenario_eligible
assert_no_forbidden = _S.assert_no_forbidden
DEFAULT_MANIFEST = _S.DEFAULT_MANIFEST

ADJUDICATE = _S.ADJUDICATE
NOT_A_KEY = _S.NOT_A_KEY
R_VFOCUS = _S.R_VFOCUS
R_RESOLVED = _S.R_RESOLVED
R_NONEXEC = _S.R_NONEXEC

# ---- new adjudicated requirement / class constants --------------------------
R_ADJ_HIGH = "ADJUDICATE_RESOLVABLE_HIGH"
R_ADJ_DISJ = "ADJUDICATE_DISJUNCTION_CHOICE"
R_ADJ_AMBIG = "ADJUDICATE_AMBIGUOUS"

CLASS_TO_REQ = {
    "RESOLVABLE_HIGH": R_ADJ_HIGH,
    "DISJUNCTION_CHOICE": R_ADJ_DISJ,
    "AMBIGUOUS_RETAIN": R_ADJ_AMBIG,
}
_CLASSES = ("RESOLVABLE_HIGH", "DISJUNCTION_CHOICE", "AMBIGUOUS_RETAIN")

_AMBIG_MARK = ("전체", "모든", "all", "아무", "any")
_KEYCODE_NAME = {19: "DPAD_UP", 20: "DPAD_DOWN", 21: "DPAD_LEFT", 22: "DPAD_RIGHT", 23: "DPAD_CENTER"}


def _detect_adj_dirs(body: str) -> set:
    """Determinable single keys. Glyph + English + ok only (no bare Korean single
    chars like 상/위/우 — they false-match 상태/위치/etc)."""
    r = body or ""
    c = _compact(r)
    d = set()
    if ("↑" in r) or ("up" in c):
        d.add(19)
    if ("↓" in r) or ("down" in c):
        d.add(20)
    if ("←" in r) or ("left" in c):
        d.add(21)
    if ("→" in r) or ("right" in c):
        d.add(22)
    if ("ok" in c) or ("확인" in c) or ("center" in c):
        d.add(23)
    return d


def _has_disjunction(body: str) -> bool:
    c = _compact(body)
    return ("또는" in c) or ("키나" in c) or ("/" in (body or ""))


def adjudicate_adjudicate(body: str) -> dict:
    """Adjudicate one ADJUDICATE-disposition step into 3 classes (spec §3).
    Precedence: ambiguity marker / multi-direction -> AMBIGUOUS_RETAIN; else
    disjunction marker -> DISJUNCTION_CHOICE; else single determinable key ->
    RESOLVABLE_HIGH; else (disjunction w/o resolvable key) -> DISJUNCTION_CHOICE."""
    c = _compact(body)
    kc = ""
    if any(m in c for m in _AMBIG_MARK):
        cls, rat, dec = "AMBIGUOUS_RETAIN", "all/any/every marker", "spec_clarification"
    else:
        dirs = _detect_adj_dirs(body)
        disj = _has_disjunction(body)
        if len(dirs) >= 2:
            cls, rat, dec = "AMBIGUOUS_RETAIN", "multiple distinct directions", "spec_clarification"
        elif disj:
            cls, rat, dec = "DISJUNCTION_CHOICE", "disjunction (either/or) — intent choice", "intent_choice"
        elif len(dirs) == 1:
            kc = next(iter(dirs))
            cls, rat, dec = "RESOLVABLE_HIGH", f"single determinable key -> {_KEYCODE_NAME[kc]}", "none"
        else:
            cls, rat, dec = "DISJUNCTION_CHOICE", "no determinable single key", "intent_choice"
    return {
        "adjudication_class": cls,
        "resolution_requirement": CLASS_TO_REQ[cls],
        "proposed_keycode": (str(kc) if kc != "" else ""),
        "rationale": rat,
        "required_decision": dec,
    }


# ---- build ------------------------------------------------------------------
def build(manifest_rows):
    """Return (adj_rows, tc_steps). adj_rows: one per ADJUDICATE step (53).
    tc_steps reqs: ADJUDICATE split into R_ADJ_HIGH/DISJ/AMBIG; others via predecessor."""
    adj_rows = []
    tc_steps = defaultdict(list)
    for m in manifest_rows:
        tc_id = m.get("tc_id", "")
        src = m.get("source_file", "")
        ed = m.get("entry_detail", "")
        steps = parse_entry_detail(ed)
        if not steps:
            tc_steps[tc_id].append({"req": R_NONEXEC, "reason": ""})
            continue
        for step in steps:
            base = classify_step(step)
            if base["disposition"] == ADJUDICATE:
                a = adjudicate_adjudicate(step.body)
                adj_rows.append({
                    "tc_id": tc_id,
                    "source_file": src,
                    "original_entry_detail": ed,
                    "extracted_token": step.body,
                    "adjudication_class": a["adjudication_class"],
                    "resolution_requirement": a["resolution_requirement"],
                    "proposed_keycode": a["proposed_keycode"],
                    "rationale": a["rationale"],
                    "required_decision": a["required_decision"],
                })
                tc_steps[tc_id].append({"req": a["resolution_requirement"], "reason": ""})
            else:
                subtype = None
                subtype_req = None
                if base["disposition"] == NOT_A_KEY:
                    sub = subclassify_not_a_key(step)
                    subtype = sub["not_a_key_subtype"]
                    subtype_req = sub["resolution_requirement"]
                req = resolution_requirement(base, subtype_req)
                tc_steps[tc_id].append({"req": req, "reason": blocker_reason(base, subtype)})
    return adj_rows, dict(tc_steps)


# ---- cascade + summarize ----------------------------------------------------
SCENARIOS = {
    "baseline": (set(), set()),
    "tier0": ({R_VFOCUS}, set()),
    "tier0_adj_high": ({R_VFOCUS}, {R_ADJ_HIGH}),
    "tier0_adj_high_disj": ({R_VFOCUS}, {R_ADJ_HIGH, R_ADJ_DISJ}),
    "tier0_all_adjudicate": ({R_VFOCUS}, {R_ADJ_HIGH, R_ADJ_DISJ, R_ADJ_AMBIG}),
}


def summarize(adj_rows, tc_steps):
    class_counts = Counter(r["adjudication_class"] for r in adj_rows)
    for c in _CLASSES:
        class_counts.setdefault(c, 0)

    elig = {}
    for name, (non, res) in SCENARIOS.items():
        elig[name] = sum(
            1 for s in tc_steps.values()
            if scenario_eligible([d["req"] for d in s], non, res))

    adjudicated_delta = elig["tier0_adj_high"] - elig["tier0"]
    disjunction_delta = elig["tier0_adj_high_disj"] - elig["tier0_adj_high"]
    prior_delta = elig["tier0_all_adjudicate"] - elig["tier0"]
    return {
        "adjudicate_total": len(adj_rows),
        "total_tcs": len(tc_steps),
        "class_counts": dict(class_counts),          # step-level
        "eligible": elig,                            # TC-level
        "baseline_eligible": elig["baseline"],
        "tier0_eligible": elig["tier0"],
        "adjudicated_delta": adjudicated_delta,                # HEADLINE (high only)
        "disjunction_delta": disjunction_delta,               # medium potential
        "prior_adjudicate_delta": prior_delta,                # reference (== +18)
        "ambiguous_retained": class_counts["AMBIGUOUS_RETAIN"],
    }


# ---- IO ---------------------------------------------------------------------
LEDGER_COLUMNS = [
    "tc_id", "source_file", "original_entry_detail", "extracted_token",
    "adjudication_class", "resolution_requirement", "proposed_keycode",
    "rationale", "required_decision",
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
    L.append("# ALT Basic ADJUDICATE Resolution Ledger — Summary\n")
    L.append(f"- ADJUDICATE steps adjudicated: {s['adjudicate_total']}  |  total TCs: {s['total_tcs']}\n")
    L.append("\n## Adjudication class counts (step-level)\n")
    for c in _CLASSES:
        L.append(f"- {c}: {s['class_counts'][c]}  (step-level)\n")
    L.append("\n## Eligibility (TC-level) — device-pilot eligibility unlock\n")
    L.append("*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*\n")
    for name in ("baseline", "tier0", "tier0_adj_high", "tier0_adj_high_disj", "tier0_all_adjudicate"):
        L.append(f"- {name}_eligible: {s['eligible'][name]}  (TC-level)\n")
    L.append("\n## Deltas (TC-level)\n")
    L.append(f"- **headline adjudicated_delta: {s['adjudicated_delta']}** "
             f"(no-device; RESOLVABLE_HIGH single-determinable-key only)\n")
    L.append(f"- disjunction_delta: {s['disjunction_delta']}  "
             f"(medium; either/or intent-choice steps, not headline)\n")
    L.append(f"- prior_adjudicate_delta: {s['prior_adjudicate_delta']}  "
             f"(reference upper bound = all ADJUDICATE resolved; the subtype ledger's +18)\n")
    L.append(f"- ambiguous_retained (step-level, never unlocks): {s['ambiguous_retained']}\n")
    L.append("\n*** STOP: host-only adjudication. No device, no reclassification committed. "
             "Await user decision on the RESOLVABLE_HIGH / DISJUNCTION_CHOICE subsets. ***\n")
    return "".join(L)


def write_summary_md(s: dict, path: str) -> None:
    md = render_summary_md(s)
    assert_no_forbidden(md)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


# ---- CLI --------------------------------------------------------------------
_AUDIT = os.path.join(_ROOT, "THOR2 - ALT Basic TC Audit")
DEFAULT_LEDGER_CSV = os.path.join(_AUDIT, "ADJUDICATE_RESOLUTION_LEDGER_2026-06-29.csv")
DEFAULT_CASCADE_CSV = os.path.join(_AUDIT, "ADJUDICATE_RESOLUTION_CASCADE_2026-06-29.csv")
DEFAULT_SUMMARY_MD = os.path.join(_AUDIT, "ADJUDICATE_RESOLUTION_SUMMARY_2026-06-29.md")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="ALT Basic ADJUDICATE resolution ledger")
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
    print(f"[adjudicate-resolution] adjudicate={s['adjudicate_total']} tcs={s['total_tcs']}")
    print(f"[adjudicate-resolution] class_counts(step-level)={s['class_counts']}")
    print(f"[adjudicate-resolution] baseline={s['baseline_eligible']} tier0={s['tier0_eligible']}")
    print(f"[adjudicate-resolution] adjudicated_delta(HEADLINE)={s['adjudicated_delta']} "
          f"disjunction_delta={s['disjunction_delta']} prior_adjudicate_delta={s['prior_adjudicate_delta']}")
    print("*** STOP: host-only. ***")


if __name__ == "__main__":
    main()
