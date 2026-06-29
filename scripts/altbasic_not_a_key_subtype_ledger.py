# -*- coding: utf-8 -*-
"""NOT_A_KEY subtype ledger + device-pilot eligibility cascade (read-only).

Refines the 189 NOT_A_KEY steps of the predecessor entry_detail ledger into 6
actionability subtypes and re-derives TC-level eligibility over the full 620-step
cascade. NO device, NO mutation, NO catalog, NO wall-clock.
See docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md
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
_PRED_PATH = os.path.join(_HERE, "altbasic_entry_detail_ledger.py")
_spec = importlib.util.spec_from_file_location("altbasic_entry_detail_ledger", _PRED_PATH)
_P = importlib.util.module_from_spec(_spec)
# MUST register in sys.modules BEFORE exec_module: the predecessor defines a @dataclass
# (Step), and dataclass resolution needs the module discoverable in sys.modules, else
# exec raises AttributeError: 'NoneType' object has no attribute '__dict__' (Py 3.12).
sys.modules[_spec.name] = _P
_spec.loader.exec_module(_P)

# ---- reused predecessor primitives (imported, not forked) --------------------
parse_entry_detail = _P.parse_entry_detail
classify_step = _P.classify_step
normalize_body = _P.normalize_body
load_manifest = _P.load_manifest
_compact = _P._compact
_is_observe = _P._is_observe

NOW_RESOLVABLE = _P.NOW_RESOLVABLE
ADJUDICATE = _P.ADJUDICATE
AMBIGUOUS_NOGUESS = _P.AMBIGUOUS_NOGUESS
NOT_A_KEY = _P.NOT_A_KEY
FREE_TEXT_DISCOVERY = _P.FREE_TEXT_DISCOVERY
RD_SEL_DISCOVERY = _P.RD_SEL_DISCOVERY
RD_KEY_DISCOVERY = _P.RD_KEY_DISCOVERY

# ---- NOT_A_KEY subtypes (spec §3) -------------------------------------------
VERIFIER_FOCUS_STATE = "VERIFIER_FOCUS_STATE"
VERIFIER_FOCUS_CANDIDATE = "VERIFIER_FOCUS_CANDIDATE"
VERIFIER_SCREEN_PRESENT = "VERIFIER_SCREEN_PRESENT"
MANUAL_RETAIN = "MANUAL_RETAIN"
KEYCODE_DISCOVERY = "KEYCODE_DISCOVERY"
SELECTOR_DISCOVERY = "SELECTOR_DISCOVERY"

# ---- resolution_requirement enum (spec §4) ----------------------------------
R_RESOLVED = "RESOLVED"
R_VFOCUS = "VERIFIER_FOCUS"
R_VFOCUS_CAND = "VERIFIER_FOCUS_CANDIDATE"
R_VSCREEN = "VERIFIER_SCREEN"
R_SELECTOR = "SELECTOR"
R_KEYCODE = "KEYCODE"
R_ADJUDICATE = "ADJUDICATE"
R_BLOCKER = "BLOCKER"
R_NONEXEC = "NONEXEC"

# ---- subtype classifier -----------------------------------------------------
_FOCUS_TOKENS = ("focus", "포커싱", "포커스")
_STATE_TOKENS = ("상태", "위치", "되어", "되지", "된")
_SCREEN_TOKENS = ("화면", "페이지", "진입", "스크린", "screen")
_PRESS_MOD = ("롱", "길게", "짧게")
_NAV_HW = ("뒤로가기", "돌아가기")
_SENSITIVE = ("긴급", "emergency")


def _has_state_marker(c: str, body: str) -> bool:
    return ("확인" in c) or _is_observe(body) or any(t in c for t in _STATE_TOKENS)


def _is_truncated(body: str) -> bool:
    # Check the ORIGINAL body, not normalize_body output: the predecessor's trailing-verb
    # strip eats legit nouns (e.g. '입력' in '언어 및 입력'), which would falsely look
    # truncated. 및 is always a standalone conjunction (never a noun suffix) -> safe even
    # with no leading space. 와/과 ARE common noun endings (결과/사과), so only treat them
    # as truncation when space-separated (a dangling trailing conjunction).
    s = (body or "").strip().rstrip(" .。")
    if s.endswith("및"):
        return True
    return any(s.endswith(" " + t) for t in ("와", "과"))


def _sub(subtype, conf, action, req, rationale, decision) -> dict:
    return {
        "not_a_key_subtype": subtype,
        "confidence": conf,
        "proposed_action": action,
        "resolution_requirement": req,
        "rationale": rationale,
        "required_decision": decision,
    }


def subclassify_not_a_key(step) -> dict:
    """Sub-classify ONE predecessor NOT_A_KEY step into 6 actionability subtypes.
    Deterministic precedence (§3): focus_state > focus_candidate > screen_present
    > manual_retain > keycode_discovery > selector_discovery (default)."""
    body = step.body
    nb = normalize_body(body)
    c = _compact(nb)

    if any(t in c for t in _FOCUS_TOKENS):
        if _has_state_marker(c, body):
            return _sub(VERIFIER_FOCUS_STATE, "high", "verifier:focus_state", R_VFOCUS,
                        "focus token + state/observe marker", "screen_verifier_decision")
        return _sub(VERIFIER_FOCUS_CANDIDATE, "medium", "verifier:focus_state?", R_VFOCUS_CAND,
                    "bare focus token, move-vs-verify ambiguous", "focus_intent_decision")
    if any(t in c for t in _SCREEN_TOKENS):
        return _sub(VERIFIER_SCREEN_PRESENT, "medium", "verifier:screen_present", R_VSCREEN,
                    "screen/state reference, no focus", "screen_verifier_decision")
    if _is_truncated(body) or any(s in c for s in _SENSITIVE):
        return _sub(MANUAL_RETAIN, "low", "(manual)", R_BLOCKER,
                    "truncated or sensitive phrase", "manual_review")
    if any(m in c for m in _PRESS_MOD) or c in _NAV_HW:
        return _sub(KEYCODE_DISCOVERY, "low", "press_key:<keycode-discovery>", R_KEYCODE,
                    "hardware/nav key or press modifier", "device_keycode_discovery")
    return _sub(SELECTOR_DISCOVERY, "low", "tap:<selector-discovery>", R_SELECTOR,
                "bare UI-label / explicit tap target", "device_selector_discovery")


# ---- resolution_requirement mapping (all 620 steps) -------------------------
def resolution_requirement(base_row: dict, subtype_req) -> str:
    """Map a predecessor classify_step row (+ NOT_A_KEY subtype requirement) to the
    unified resolution_requirement enum used by the eligibility cascade (§4)."""
    if not base_row.get("executable"):
        return R_NONEXEC
    disp = base_row["disposition"]
    if disp == NOW_RESOLVABLE:
        return R_RESOLVED
    if disp == NOT_A_KEY:
        return subtype_req
    if disp == ADJUDICATE:
        return R_ADJUDICATE
    if disp == AMBIGUOUS_NOGUESS:
        return R_BLOCKER
    if disp == FREE_TEXT_DISCOVERY:
        rd = base_row.get("required_decision")
        if rd == RD_SEL_DISCOVERY:
            return R_SELECTOR
        if rd == RD_KEY_DISCOVERY:
            return R_KEYCODE
        return R_BLOCKER  # manifest_rewrite / residual free-text / empty
    return R_BLOCKER


def blocker_reason(base_row: dict, subtype) -> str:
    """For BLOCKER steps, the finer reason used in the remaining-blocked breakdown."""
    disp = base_row["disposition"]
    if disp == AMBIGUOUS_NOGUESS:
        return "AMBIGUOUS"
    if disp == NOT_A_KEY and subtype == MANUAL_RETAIN:
        return "MANUAL_RETAIN"
    if disp == FREE_TEXT_DISCOVERY and base_row.get("required_decision") not in (
            RD_SEL_DISCOVERY, RD_KEY_DISCOVERY):
        return "FREE_TEXT_MANIFEST"
    return ""


# ---- eligibility cascade (spec §5) ------------------------------------------
# (to_nonexec, to_resolved) per scenario.
#  to_nonexec : requirements that, when the scenario applies, become NONEXEC
#               (verifier reclassification — drop out of the executable denominator)
#  to_resolved: requirements that become satisfied-executable (device discovery / decision)
SCENARIOS = {
    "baseline": (set(), set()),
    "tier0": ({R_VFOCUS}, set()),
    "tier1": ({R_VFOCUS}, {R_SELECTOR}),
    "tier2": ({R_VFOCUS}, {R_SELECTOR, R_KEYCODE}),
    "tier0_screen": ({R_VFOCUS, R_VSCREEN}, set()),
    "tier0_focus_candidate": ({R_VFOCUS, R_VFOCUS_CAND}, set()),
    "tier0_adjudicate": ({R_VFOCUS}, {R_ADJUDICATE}),
    "optimistic_upper_bound": ({R_VFOCUS, R_VFOCUS_CAND, R_VSCREEN},
                               {R_SELECTOR, R_KEYCODE, R_ADJUDICATE}),
}


def scenario_eligible(reqs, to_nonexec, to_resolved) -> bool:
    """Fail-closed eligibility (§5.1): a TC is eligible under a scenario iff, after
    removing NONEXEC + to_nonexec steps, it has >=1 executable step AND every such
    step is RESOLVED or in to_resolved."""
    post = [r for r in reqs if r != R_NONEXEC and r not in to_nonexec]
    if not post:
        return False
    return all(r == R_RESOLVED or r in to_resolved for r in post)


# ---- build + summarize ------------------------------------------------------
_SUBTYPES = (VERIFIER_FOCUS_STATE, VERIFIER_FOCUS_CANDIDATE, VERIFIER_SCREEN_PRESENT,
             MANUAL_RETAIN, KEYCODE_DISCOVERY, SELECTOR_DISCOVERY)


def build(manifest_rows):
    """Return (subtype_rows, tc_steps).
    subtype_rows: one dict per NOT_A_KEY step (the 189), for the subtype ledger CSV.
    tc_steps: {tc_id: [{"req": <enum>, "reason": <blocker reason or "">}, ...]}.
    """
    subtype_rows = []
    tc_steps = defaultdict(list)
    for m in manifest_rows:
        tc_id = m.get("tc_id", "")
        src = m.get("source_file", "")
        ed = m.get("entry_detail", "")
        steps = parse_entry_detail(ed)
        if not steps:
            # mirror predecessor empty handling: a single non-executable row
            tc_steps[tc_id].append({"req": R_NONEXEC, "reason": ""})
            continue
        for step in steps:
            base = classify_step(step)
            subtype = None
            subtype_req = None
            if base["disposition"] == NOT_A_KEY:
                sub = subclassify_not_a_key(step)
                subtype = sub["not_a_key_subtype"]
                subtype_req = sub["resolution_requirement"]
                subtype_rows.append({
                    "tc_id": tc_id,
                    "source_file": src,
                    "original_entry_detail": ed,
                    "extracted_token": step.body,
                    **sub,
                })
            req = resolution_requirement(base, subtype_req)
            tc_steps[tc_id].append({"req": req, "reason": blocker_reason(base, subtype)})
    return subtype_rows, dict(tc_steps)


def summarize(subtype_rows, tc_steps, predecessor_headline=5):
    subtype_counts = Counter(r["not_a_key_subtype"] for r in subtype_rows)
    for st in _SUBTYPES:
        subtype_counts.setdefault(st, 0)

    elig = {}
    for name, (non, res) in SCENARIOS.items():
        elig[name] = sum(
            1 for steps in tc_steps.values()
            if scenario_eligible([d["req"] for d in steps], non, res))

    deltas = {
        "tier0_delta": elig["tier0"] - elig["baseline"],
        "selector_delta": elig["tier1"] - elig["tier0"],
        "keycode_delta": elig["tier2"] - elig["tier1"],
        "screen_present_delta": elig["tier0_screen"] - elig["tier0"],
        "focus_candidate_delta": elig["tier0_focus_candidate"] - elig["tier0"],
        "adjudication_delta": elig["tier0_adjudicate"] - elig["tier0"],
    }

    non, res = SCENARIOS["optimistic_upper_bound"]
    remaining = Counter()
    for steps in tc_steps.values():
        if scenario_eligible([d["req"] for d in steps], non, res):
            continue
        reasons = [d["reason"] for d in steps if d["req"] == R_BLOCKER and d["reason"]]
        remaining[Counter(reasons).most_common(1)[0][0] if reasons else "OTHER"] += 1

    return {
        "total_tcs": len(tc_steps),
        "not_a_key_steps": len(subtype_rows),
        "subtype_counts": dict(subtype_counts),     # step-level
        "eligible": elig,                            # TC-level
        "deltas": deltas,                            # TC-level
        "headline_now_unlock": deltas["tier0_delta"],
        "remaining_blocked": dict(remaining),
        "self_check": "ok" if elig["baseline"] == predecessor_headline else "mismatch",
    }


# ---- IO writers + forbidden-word guard --------------------------------------
FORBIDDEN = ("PASS", "RUNNABLE_NOW", "validated")

SUBTYPE_COLUMNS = [
    "tc_id", "source_file", "original_entry_detail", "extracted_token",
    "not_a_key_subtype", "confidence", "proposed_action", "resolution_requirement",
    "rationale", "required_decision",
]


def assert_no_forbidden(text: str) -> None:
    hits = [w for w in FORBIDDEN if w in text]
    if hits:
        raise AssertionError(f"forbidden token(s) in output: {hits}")


def write_subtype_csv(subtype_rows, path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUBTYPE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in subtype_rows:
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
    L.append("# ALT Basic NOT_A_KEY Subtype Ledger — Summary\n")
    L.append(f"- total TCs: {s['total_tcs']}  |  NOT_A_KEY steps: {s['not_a_key_steps']}\n")
    L.append(f"- self_check={s['self_check']} (baseline_eligible vs predecessor headline)\n")
    L.append("\n## NOT_A_KEY subtype counts (step-level)\n")
    for st in _SUBTYPES:
        L.append(f"- {st}: {s['subtype_counts'][st]}  (step-level)\n")
    L.append("\n## Eligibility cascade (TC-level) — device-pilot eligibility unlock\n")
    L.append("*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*\n")
    for name in ("baseline", "tier0", "tier1", "tier2",
                 "tier0_screen", "tier0_focus_candidate", "tier0_adjudicate",
                 "optimistic_upper_bound"):
        L.append(f"- {name}_eligible: {s['eligible'][name]}  (TC-level)\n")
    L.append("\n## Deltas (TC-level)\n")
    L.append(f"- **headline_now_unlock = tier0_delta: {s['headline_now_unlock']}** "
             f"(no-device; high-confidence focus-state verifier reclassification only)\n")
    for k in ("selector_delta", "keycode_delta", "screen_present_delta",
              "focus_candidate_delta", "adjudication_delta"):
        L.append(f"- {k}: {s['deltas'][k]}  (potential, not headline)\n")
    L.append("\n## Remaining blocked (at optimistic upper bound, by dominant reason)\n")
    for reason, n in sorted(s["remaining_blocked"].items()):
        L.append(f"- {reason}: {n}\n")
    L.append("\n*** STOP: host-only measurement. No device, no reclassification committed. "
             "Await user decision on which subtypes to action. ***\n")
    return "".join(L)


def write_summary_md(s: dict, path: str) -> None:
    md = render_summary_md(s)
    assert_no_forbidden(md)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


# ---- CLI --------------------------------------------------------------------
_AUDIT = os.path.join(_ROOT, "THOR2 - ALT Basic TC Audit")
DEFAULT_MANIFEST = _P.DEFAULT_MANIFEST
DEFAULT_SUBTYPE_CSV = os.path.join(_AUDIT, "NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv")
DEFAULT_CASCADE_CSV = os.path.join(_AUDIT, "NOT_A_KEY_SUBTYPE_CASCADE_2026-06-29.csv")
DEFAULT_SUMMARY_MD = os.path.join(_AUDIT, "NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md")
PREDECESSOR_HEADLINE = 5


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="ALT Basic NOT_A_KEY subtype ledger + cascade")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--subtype-out", default=DEFAULT_SUBTYPE_CSV)
    ap.add_argument("--cascade-out", default=DEFAULT_CASCADE_CSV)
    ap.add_argument("--summary-out", default=DEFAULT_SUMMARY_MD)
    a = ap.parse_args(argv)
    rows = load_manifest(a.manifest)
    subtype_rows, tc_steps = build(rows)
    s = summarize(subtype_rows, tc_steps, predecessor_headline=PREDECESSOR_HEADLINE)
    write_subtype_csv(subtype_rows, a.subtype_out)
    write_cascade_csv(tc_steps, a.cascade_out)
    write_summary_md(s, a.summary_out)
    print(f"[subtype-ledger] tcs={s['total_tcs']} not_a_key_steps={s['not_a_key_steps']}")
    print(f"[subtype-ledger] subtype_counts(step-level)={s['subtype_counts']}")
    print(f"[subtype-ledger] eligible(TC-level)={s['eligible']}")
    print(f"[subtype-ledger] headline_now_unlock={s['headline_now_unlock']} "
          f"self_check={s['self_check']}")
    print("*** STOP: host-only. ***")


if __name__ == "__main__":
    main()
