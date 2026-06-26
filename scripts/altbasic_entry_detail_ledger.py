# -*- coding: utf-8 -*-
"""ALT Basic batch10 entry_detail normalization measurement ledger (read-only).

Classifies each entry_detail step into one of 5 dispositions and quantifies
device-pilot unlock potential. NO device, NO mutation of runner/yaml/manifest.
See docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md
"""
from __future__ import annotations

import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

# ---- dispositions -----------------------------------------------------------
NOW_RESOLVABLE = "NOW_RESOLVABLE"
ADJUDICATE = "ADJUDICATE"
AMBIGUOUS_NOGUESS = "AMBIGUOUS_NOGUESS"
NOT_A_KEY = "NOT_A_KEY"
FREE_TEXT_DISCOVERY = "FREE_TEXT_DISCOVERY"

# ---- required_decision ------------------------------------------------------
RD_NONE = ""
RD_INTENT = "intent_choice"
RD_SPEC = "spec_clarification"
RD_RECLASSIFY = "reclassify_verifier_or_navigate"
RD_SEL_DISCOVERY = "device_selector_discovery"
RD_KEY_DISCOVERY = "device_keycode_discovery"
RD_MANIFEST = "manifest_rewrite"

STEP_SEP = ">"
EXECUTABLE_ACTIONS = frozenset({
    "press_key", "tap", "swipe", "long_press", "navigate",
    "launch", "launch_app", "input", "wait",
})

_STEP_NUM_RE = re.compile(r"^\s*\d+\.\s*")
_PREFIX_RE = re.compile(r"^[a-zA-Z_]{2,20}$")


@dataclass(frozen=True)
class Step:
    action: str   # executable action / "(bare)" / "?<prefix>"
    body: str
    raw: str


def parse_entry_detail(s: str) -> list[Step]:
    s = (s or "").strip()
    if not s or s == "—":
        return []
    out: list[Step] = []
    for raw in [x.strip() for x in s.split(STEP_SEP) if x.strip()]:
        head = raw.split(":", 1)[0].strip() if ":" in raw else ""
        if head and _PREFIX_RE.match(head):
            body = _STEP_NUM_RE.sub("", raw.split(":", 1)[1].strip())
            action = head if head in EXECUTABLE_ACTIONS else f"?{head}"
            out.append(Step(action=action, body=body, raw=raw))
        else:
            out.append(Step(action="(bare)", body=_STEP_NUM_RE.sub("", raw), raw=raw))
    return out


_TRAIL_VERBS = (
    "누른다", "누름", "입력한다", "입력", "누르기", "눌러", "한다",
    "Tap", "tap", "탭", "을", "를",
)


def normalize_body(body: str) -> str:
    """Strip leading 'N.', trailing verbs/punctuation, collapse whitespace.
    Markers ((), /, 또는, 아무) are preserved for downstream classification."""
    b = _STEP_NUM_RE.sub("", (body or "").strip())
    b = re.sub(r"\s+", " ", b).strip()
    changed = True
    while changed:
        changed = False
        b = b.rstrip(" .。")
        for v in _TRAIL_VERBS:
            if b.endswith(v):
                b = b[: -len(v)].strip()
                changed = True
    return b.strip()


def _compact(nb: str) -> str:
    return re.sub(r"\s+", "", nb).casefold()


# Named hardware keys WITH a standard keycode (compact form -> keycode).
NAMED_KEYS = {
    "recentapp버튼": 187,   # KEYCODE_APP_SWITCH
    "home버튼": 3,          # KEYCODE_HOME
    "camera버튼": 27,       # KEYCODE_CAMERA
    "contact버튼": 207,     # KEYCODE_CONTACTS
    "하드키돌아가기버튼": 4,  # KEYCODE_BACK
}

# D-pad keycode -> human name (for proposed_normalized_step).
KEYCODE_NAME = {
    3: "KEYCODE_HOME", 4: "KEYCODE_BACK", 19: "KEYCODE_DPAD_UP",
    20: "KEYCODE_DPAD_DOWN", 21: "KEYCODE_DPAD_LEFT", 22: "KEYCODE_DPAD_RIGHT",
    23: "KEYCODE_DPAD_CENTER", 27: "KEYCODE_CAMERA", 187: "KEYCODE_APP_SWITCH",
    207: "KEYCODE_CONTACTS",
}

# Direction keyword sets (compact, casefolded). Only counted when a key-context
# token is present (avoids false matches inside screen names like 상단/상태).
_DIR_KW = {
    19: ("up", "위방향", "상방향"),
    20: ("down", "하방향", "아래방향"),
    21: ("left", "좌방향", "왼방향"),
    22: ("right", "우방향", "오른방향"),
    23: ("ok", "확인", "center", "가운데", "enter", "엔터"),
}
_KEY_CTX = ("방향", "press", "키", "key")
_ANY_RE = re.compile(r"아무|any")
# direction enumeration: word/letter direction tokens joined by '/'
_ENUM_RE = re.compile(
    r"(?:up|down|left|right|ok|u|d|l|r)(?:/(?:up|down|left|right|ok|u|d|l|r))+", re.I
)


def _detect_dirs(c: str) -> set:
    if not any(k in c for k in _KEY_CTX):
        return set()
    found = set()
    for code, kws in _DIR_KW.items():
        if any(kw in c for kw in kws):
            found.add(code)
    return found


def resolve_single_key(body: str):
    """(keycode|None, verdict). verdict in RESOLVED/ADJUDICATE/AMBIGUOUS/NONE.
    Conservative: only a single explicit key/direction with no ambiguity marker
    is RESOLVED."""
    nb = normalize_body(body)
    c = _compact(nb)
    if c in NAMED_KEYS:
        return NAMED_KEYS[c], "RESOLVED"
    if _ANY_RE.search(c):
        return None, "AMBIGUOUS"
    if _ENUM_RE.search(c):
        return None, "AMBIGUOUS"
    dirs = _detect_dirs(c)
    navi_present = ("navi" in c) or ("네비" in c)
    has_or = "또는" in c
    if navi_present or has_or:
        cand = next(iter(dirs)) if len(dirs) == 1 else None
        return cand, "ADJUDICATE"
    if len(dirs) == 1:
        return next(iter(dirs)), "RESOLVED"
    if len(dirs) >= 2:
        return None, "AMBIGUOUS"
    return None, "NONE"


# ---- Task 4: classify_step --------------------------------------------------

_SCREEN_MARKERS = ("focus", "화면", "페이지", "진입", "스크린", "screen")
_OBSERVE_RE = re.compile(r"(확인한다|확인됨|표시된다|노출된다|확인\s*한다)\s*[.。]?\s*$")
_LONG_PRESS_RE = re.compile(r"길게")


def _is_observe(raw_body: str) -> bool:
    # run on the ORIGINAL body — normalize_body strips trailing 한다.
    return bool(_OBSERVE_RE.search((raw_body or "").strip()))


def _is_named_key_no_keycode(c: str) -> bool:
    # ends with 버튼/키 but did not resolve and is not a screen ref
    return c.endswith("버튼") or c.endswith("키")


def _is_screen_ref(c: str) -> bool:
    return any(m in c for m in _SCREEN_MARKERS)


def _has_latin_or_digit(c: str) -> bool:
    return bool(re.search(r"[a-z0-9]", c))


def _row(disp, token, prop, kc, conf, rat, rd, executable):
    return {
        "extracted_token": token,
        "disposition": disp,
        "proposed_normalized_step": prop,
        "proposed_keycode": kc,
        "confidence": conf,
        "rationale": rat,
        "required_decision": rd,
        "executable": executable,
    }


def classify_step(step: Step) -> dict:
    nb = normalize_body(step.body)
    c = _compact(nb)
    token = step.body

    # non-executable observe token (bare only) — excluded from rollup denominator
    if step.action == "(bare)" and _is_observe(step.body):
        return _row(FREE_TEXT_DISCOVERY, token, "(observe)", "", "low",
                    "non-executable observe token (excluded from rollup)", RD_NONE, False)

    # tap / navigate → selector discovery
    if step.action in ("tap", "navigate"):
        return _row(FREE_TEXT_DISCOVERY, token, f"{step.action}:<{nb}>", "", "low",
                    f"{step.action} target needs a selector", RD_SEL_DISCOVERY, True)

    # long-press modifier cannot map to a standard keycode → device pilot must confirm
    if _LONG_PRESS_RE.search(step.body):
        return _row(FREE_TEXT_DISCOVERY, token, f"press_key:<{nb}>(long-press)", "", "low",
                    "long-press modifier — keycode insufficient, device pilot needed",
                    RD_KEY_DISCOVERY, True)

    # press_key / bare / unknown-prefix → key resolution path
    kc, verdict = resolve_single_key(step.body)
    if verdict == "RESOLVED":
        return _row(NOW_RESOLVABLE, token, f"press_key:{KEYCODE_NAME[kc]}", kc, "high",
                    f"single explicit key -> keycode {kc}", RD_NONE, True)
    if verdict == "ADJUDICATE":
        prop = f"press_key:{KEYCODE_NAME[kc]}?" if kc else "press_key:?"
        return _row(ADJUDICATE, token, prop, (kc if kc else ""), "medium",
                    "disjunction/qualified key — intent choice", RD_INTENT, True)
    if verdict == "AMBIGUOUS":
        return _row(AMBIGUOUS_NOGUESS, token, "press_key:?", "", "low",
                    "any/multi-key enumeration — test intent", RD_SPEC, True)
    # verdict == NONE
    if _is_screen_ref(c):
        return _row(NOT_A_KEY, token, f"(reclassify) {nb}", "", "low",
                    "screen/focus/state ref mis-tagged as key", RD_RECLASSIFY, True)
    if _is_named_key_no_keycode(c):
        return _row(FREE_TEXT_DISCOVERY, token, f"press_key:<{nb}>", "", "low",
                    "named hardware key, no standard keycode", RD_KEY_DISCOVERY, True)
    # residual bare noun (e.g. 시계, 타이머) mis-tagged as a key step
    if step.action in ("press_key", "(bare)") and not _has_latin_or_digit(c):
        return _row(NOT_A_KEY, token, f"(reclassify) {nb}", "", "low",
                    "bare noun mis-tagged as key (no key signal)", RD_RECLASSIFY, True)
    return _row(FREE_TEXT_DISCOVERY, token, f"{step.action}:<{nb}>", "", "low",
                "unresolved free-text body", RD_MANIFEST, True)


# ---- Task 5: rollup_eligibility ---------------------------------------------

def rollup_eligibility(step_rows: list[dict]) -> bool:
    """TC-level fail-closed: eligible iff there is >=1 executable step AND every
    executable step is NOW_RESOLVABLE. Non-executable tokens are excluded."""
    execs = [r for r in step_rows if r.get("executable")]
    if not execs:
        return False
    return all(r["disposition"] == NOW_RESOLVABLE for r in execs)


# ---- Task 6: manifest IO ----------------------------------------------------

LEDGER_COLUMNS = [
    "tc_id", "source_file", "original_entry_detail", "extracted_token",
    "disposition", "proposed_normalized_step", "proposed_keycode",
    "confidence", "rationale", "required_decision", "device_pilot_eligible",
    "executable",
]


def load_manifest(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_ledger(manifest_rows: list[dict]) -> list[dict]:
    ledger: list[dict] = []
    for m in manifest_rows:
        tc_id = m.get("tc_id", "")
        src = m.get("source_file", "")
        ed = m.get("entry_detail", "")
        steps = parse_entry_detail(ed)
        step_rows = [classify_step(s) for s in steps]
        eligible = rollup_eligibility(step_rows)
        if not step_rows:  # empty entry_detail still gets a row for completeness
            step_rows = [_row(FREE_TEXT_DISCOVERY, "", "", "", "low",
                              "empty entry_detail", RD_MANIFEST, False)]
            eligible = False
        for sr in step_rows:
            ledger.append({
                "tc_id": tc_id,
                "source_file": src,
                "original_entry_detail": ed,
                "device_pilot_eligible": eligible,
                **sr,
            })
    return ledger


# ---- Task 7: summarize ------------------------------------------------------

_ALL_TIERS = (NOW_RESOLVABLE, ADJUDICATE, AMBIGUOUS_NOGUESS, NOT_A_KEY, FREE_TEXT_DISCOVERY)


def summarize(ledger: list[dict]) -> dict:
    tier_counts = Counter(r["disposition"] for r in ledger)
    for t in _ALL_TIERS:
        tier_counts.setdefault(t, 0)

    by_tc = defaultdict(list)
    for r in ledger:
        by_tc[r["tc_id"]].append(r)

    headline = 0
    potential = 0
    for tc, rows in by_tc.items():
        if rows[0]["device_pilot_eligible"]:
            headline += 1
            potential += 1
            continue
        # adjudicate-only: every executable step is NOW_RESOLVABLE or ADJUDICATE,
        # at least one ADJUDICATE, and nothing worse.
        execs = [r for r in rows if r.get("executable")]
        if execs and all(r["disposition"] in (NOW_RESOLVABLE, ADJUDICATE) for r in execs) \
                and any(r["disposition"] == ADJUDICATE for r in execs):
            potential += 1

    # top unlock rules: which normalized step produces the most NOW_RESOLVABLE *TCs*
    unlock = Counter()
    for tc, rows in by_tc.items():
        if rows[0]["device_pilot_eligible"]:
            seen_steps = set()
            for r in rows:
                if r["disposition"] == NOW_RESOLVABLE:
                    key = r["proposed_normalized_step"]
                    if key not in seen_steps:
                        unlock[key] += 1
                        seen_steps.add(key)

    return {
        "total_steps": len(ledger),
        "total_tcs": len(by_tc),
        "tier_counts": dict(tier_counts),          # step-level
        "headline_resolvable_count": headline,      # TC-level
        "potential_with_adjudication_count": potential,  # TC-level
        "top_unlock": unlock.most_common(10),
    }


# ---- Task 8: writers + CLI --------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_AUDIT = os.path.join(_ROOT, "THOR2 - ALT Basic TC Audit")
DEFAULT_MANIFEST = os.path.join(
    _AUDIT, "handoff_device_validation", "VALIDATION_MANIFEST_BATCH10_2026-06-25.csv")
DEFAULT_LEDGER = os.path.join(_AUDIT, "ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv")
DEFAULT_SUMMARY = os.path.join(_AUDIT, "ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md")


def write_ledger_csv(ledger: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in ledger:
            w.writerow(r)


def write_summary_md(s: dict, path: str) -> None:
    lines = []
    lines.append("# ALT Basic entry_detail Normalization Ledger — Summary\n")
    lines.append(f"- total steps: {s['total_steps']}  |  total TCs: {s['total_tcs']}\n")
    lines.append("\n## Tier counts (step-level)\n")
    for t in _ALL_TIERS:
        lines.append(f"- {t}: {s['tier_counts'][t]}  (step-level)\n")
    lines.append("\n## Headline metrics (TC-level)\n")
    lines.append(f"- headline_resolvable_count: {s['headline_resolvable_count']}  (TC-level)\n")
    lines.append(f"- potential_with_adjudication_count: "
                 f"{s['potential_with_adjudication_count']}  (TC-level)\n")
    lines.append("\n## Top 10 unlock rules (by NOW_RESOLVABLE TC contribution)\n")
    for step, n in s["top_unlock"]:
        lines.append(f"- `{step}`: {n}\n")
    lines.append("\n*** STOP: host-only measurement. No device, no normalization committed. "
                 "Await user decision on which rules to build. ***\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(lines))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="ALT Basic entry_detail normalization ledger")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--ledger-out", default=DEFAULT_LEDGER)
    ap.add_argument("--summary-out", default=DEFAULT_SUMMARY)
    a = ap.parse_args(argv)
    rows = load_manifest(a.manifest)
    ledger = build_ledger(rows)
    s = summarize(ledger)
    write_ledger_csv(ledger, a.ledger_out)
    write_summary_md(s, a.summary_out)
    print(f"[ledger] manifest={a.manifest} steps={s['total_steps']} tcs={s['total_tcs']}")
    print(f"[ledger] tier_counts(step-level)={s['tier_counts']}")
    print(f"[ledger] headline_resolvable_count(TC-level)={s['headline_resolvable_count']}")
    print(f"[ledger] potential_with_adjudication_count(TC-level)="
          f"{s['potential_with_adjudication_count']}")
    print("*** STOP: host-only. ***")


if __name__ == "__main__":
    main()
