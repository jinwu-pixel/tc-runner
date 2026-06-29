# ALT Basic NOT_A_KEY Subtype Ledger + Eligibility Cascade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the 189 `NOT_A_KEY` steps of the predecessor entry_detail ledger into 6 actionability subtypes and re-derive, defensibly, how many batch10 TCs each subtype would unlock for device-pilot eligibility — computed over the full 620-step cascade, host-only.

**Architecture:** A new read-only analyzer `scripts/altbasic_not_a_key_subtype_ledger.py` that **imports** (does not fork) the predecessor `scripts/altbasic_entry_detail_ledger.py`, adds pure functions (`subclassify_not_a_key`, `resolution_requirement`, `scenario_eligible`, `build`, `summarize`) and a thin IO/CLI layer. Outputs a subtype-ledger CSV, a per-TC cascade CSV, and a summary MD. No device, no wall-clock, no network, no catalog, no yaml/manifest mutation.

**Tech Stack:** Python 3 (stdlib only: `csv`, `importlib`, `re`, `collections`, `argparse`), pytest. venv at `venv/Scripts/python.exe`. Spec: [docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md](../specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md).

> **Commit policy (global §7 / project §7.1):** NO per-task commits. After each task run the suite GREEN as the checkpoint. A single end-of-day batch commit (named paths only) is the LAST task and requires explicit user approval. No `git add .`/`-A`/dir-broad.

---

### Task 1: Module scaffold + predecessor import + constants

**Files:**
- Create: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/altbasic_not_a_key_subtype_ledger.py (read-only subtype ledger).
Pure classifier tested with synthetic strings only. NO device, NO network, NO wall-clock.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_not_a_key_subtype_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_not_a_key_subtype_ledger", _PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_not_a_key_subtype_ledger"] = M
_spec.loader.exec_module(M)


def test_module_reuses_predecessor_primitives():
    # imported, not reimplemented
    assert callable(M.parse_entry_detail)
    assert callable(M.classify_step)
    assert callable(M.normalize_body)
    assert M.NOT_A_KEY == "NOT_A_KEY"


def test_subtype_constants_present():
    assert M.VERIFIER_FOCUS_STATE == "VERIFIER_FOCUS_STATE"
    assert M.VERIFIER_FOCUS_CANDIDATE == "VERIFIER_FOCUS_CANDIDATE"
    assert M.VERIFIER_SCREEN_PRESENT == "VERIFIER_SCREEN_PRESENT"
    assert M.MANUAL_RETAIN == "MANUAL_RETAIN"
    assert M.KEYCODE_DISCOVERY == "KEYCODE_DISCOVERY"
    assert M.SELECTOR_DISCOVERY == "SELECTOR_DISCOVERY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -v`
Expected: FAIL — file `scripts/altbasic_not_a_key_subtype_ledger.py` does not exist (import error).

- [ ] **Step 3: Write minimal implementation**

```python
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
import re
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

# ---- NOT_A_KEY subtypes (§3) ------------------------------------------------
VERIFIER_FOCUS_STATE = "VERIFIER_FOCUS_STATE"
VERIFIER_FOCUS_CANDIDATE = "VERIFIER_FOCUS_CANDIDATE"
VERIFIER_SCREEN_PRESENT = "VERIFIER_SCREEN_PRESENT"
MANUAL_RETAIN = "MANUAL_RETAIN"
KEYCODE_DISCOVERY = "KEYCODE_DISCOVERY"
SELECTOR_DISCOVERY = "SELECTOR_DISCOVERY"

# ---- resolution_requirement enum (§4) ---------------------------------------
R_RESOLVED = "RESOLVED"
R_VFOCUS = "VERIFIER_FOCUS"
R_VFOCUS_CAND = "VERIFIER_FOCUS_CANDIDATE"
R_VSCREEN = "VERIFIER_SCREEN"
R_SELECTOR = "SELECTOR"
R_KEYCODE = "KEYCODE"
R_ADJUDICATE = "ADJUDICATE"
R_BLOCKER = "BLOCKER"
R_NONEXEC = "NONEXEC"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint (no commit)**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q`
Expected: 2 passed. (Commit deferred — see header.)

---

### Task 2: `subclassify_not_a_key` (the 6-way classifier)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
def _subtype(body):
    step = M.parse_entry_detail(f"press_key:{body}")[0]
    return M.subclassify_not_a_key(step)["not_a_key_subtype"]


def test_focus_with_state_marker_is_focus_state():
    assert _subtype("앱 서랍 포커스 되지 않은 상태") == M.VERIFIER_FOCUS_STATE
    assert _subtype("스크롤 마지막 앱에 포커스 위치") == M.VERIFIER_FOCUS_STATE


def test_bare_focus_is_candidate_not_state():
    assert _subtype("wifi focus") == M.VERIFIER_FOCUS_CANDIDATE
    assert _subtype("새 연락처 만들기 focus") == M.VERIFIER_FOCUS_CANDIDATE
    # focus wins over the 버튼 keycode signal; no state marker -> candidate
    assert _subtype("전원 버튼 focus") == M.VERIFIER_FOCUS_CANDIDATE


def test_screen_marker_without_focus_is_screen_present():
    assert _subtype("간편 설정 페이지") == M.VERIFIER_SCREEN_PRESENT
    assert _subtype("홈화면") == M.VERIFIER_SCREEN_PRESENT
    assert _subtype("앱서랍 진입") == M.VERIFIER_SCREEN_PRESENT


def test_truncated_or_sensitive_is_manual_retain():
    assert _subtype("언어 및") == M.MANUAL_RETAIN       # spaced dangling 및
    assert _subtype("언어및") == M.MANUAL_RETAIN          # no-space dangling 및 (robust)
    assert _subtype("긴급 전화") == M.MANUAL_RETAIN


def test_truncated_does_not_false_match_noun_ending():
    # 와/과 are common noun endings; only a *spaced* dangling conjunction is truncation.
    # a plain label ending in 과 (e.g. 결과) must NOT be MANUAL_RETAIN.
    assert _subtype("결과") == M.SELECTOR_DISCOVERY


def test_keycode_discovery_modifier_or_navword():
    assert _subtype("해당 버튼을 짧게 누른다") == M.KEYCODE_DISCOVERY
    assert _subtype("하드키 즐겨 찾기 버튼 롱") == M.KEYCODE_DISCOVERY
    assert _subtype("뒤로가기") == M.KEYCODE_DISCOVERY


def test_selector_discovery_is_default():
    assert _subtype("펼치기 Tap") == M.SELECTOR_DISCOVERY
    assert _subtype("사진") == M.SELECTOR_DISCOVERY
    assert _subtype("시계") == M.SELECTOR_DISCOVERY
    assert _subtype("언어 및 입력") == M.SELECTOR_DISCOVERY  # full label, not truncated


def test_subclassify_row_shape():
    step = M.parse_entry_detail("press_key:wifi focus")[0]
    row = M.subclassify_not_a_key(step)
    assert set(row) == {"not_a_key_subtype", "confidence", "proposed_action",
                        "resolution_requirement", "rationale", "required_decision"}
    assert row["resolution_requirement"] == M.R_VFOCUS_CAND
    assert row["confidence"] == "medium"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k subclassify -v`
Expected: FAIL — `M.subclassify_not_a_key` not defined.

- [ ] **Step 3: Write the implementation** (append to module)

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "subclassify or focus or screen or truncated or keycode or selector" -v`
Expected: PASS (all subtype tests).

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 3: `resolution_requirement` + `blocker_reason` (map any step → enum)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
def _base_and_req(entry):
    """parse one step, run predecessor classify_step, then map to requirement."""
    step = M.parse_entry_detail(entry)[0]
    base = M.classify_step(step)
    subtype_req = None
    if base["disposition"] == M.NOT_A_KEY:
        subtype_req = M.subclassify_not_a_key(step)["resolution_requirement"]
    return base, M.resolution_requirement(base, subtype_req)


def test_req_now_resolvable_is_resolved():
    _, req = _base_and_req("press_key:Home 버튼 누른다")
    assert req == M.R_RESOLVED


def test_req_not_a_key_focus_state():
    _, req = _base_and_req("press_key:앱 서랍 포커스 되지 않은 상태")
    assert req == M.R_VFOCUS


def test_req_not_a_key_selector_default():
    _, req = _base_and_req("press_key:사진")
    assert req == M.R_SELECTOR


def test_req_free_text_tap_is_selector():
    _, req = _base_and_req("tap:더보기 Tap")
    assert req == M.R_SELECTOR


def test_req_ambiguous_is_blocker():
    _, req = _base_and_req("press_key:아무 방향키")
    assert req == M.R_BLOCKER


def test_req_nonexec_observe_token():
    # bare observe token is non-executable in predecessor -> NONEXEC
    step = M.parse_entry_detail("설정 화면이 표시된다")[0]
    base = M.classify_step(step)
    assert base["executable"] is False
    assert M.resolution_requirement(base, None) == M.R_NONEXEC


def test_blocker_reason_distinguishes_sources():
    s1 = M.parse_entry_detail("press_key:아무 방향키")[0]
    assert M.blocker_reason(M.classify_step(s1), None) == "AMBIGUOUS"
    s2 = M.parse_entry_detail("press_key:언어 및")[0]
    assert M.blocker_reason(M.classify_step(s2), M.MANUAL_RETAIN) == "MANUAL_RETAIN"
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "req_ or blocker_reason" -v`
Expected: FAIL — `M.resolution_requirement` / `M.blocker_reason` not defined.

- [ ] **Step 3: Write the implementation** (append)

```python
def resolution_requirement(base_row: dict, subtype_req) -> str:
    """Map a predecessor classify_step row (+ NOT_A_KEY subtype requirement) to the
    unified resolution_requirement enum used by the eligibility cascade (§4)."""
    if not base_row.get("executable"):
        return R_NONEXEC
    disp = base_row["disposition"]
    if disp == NOW_RESOLVABLE:
        return R_RESOLVED
    if disp == NOT_A_KEY:
        return subtype_req  # one of R_VFOCUS/R_VFOCUS_CAND/R_VSCREEN/R_SELECTOR/R_KEYCODE/R_BLOCKER
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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "req_ or blocker_reason" -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — full file: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 4: `scenario_eligible` + `SCENARIOS` (the cascade predicate)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_baseline_eligible_iff_all_executable_resolved():
    non, res = M.SCENARIOS["baseline"]
    assert M.scenario_eligible([M.R_RESOLVED, M.R_RESOLVED], non, res) is True
    assert M.scenario_eligible([M.R_RESOLVED, M.R_SELECTOR], non, res) is False
    assert M.scenario_eligible([M.R_NONEXEC], non, res) is False  # no executable step


def test_tier0_drops_focus_verifier_from_denominator():
    non, res = M.SCENARIOS["tier0"]
    # a TC whose only blocker was a focus-state step becomes eligible
    assert M.scenario_eligible([M.R_RESOLVED, M.R_VFOCUS], non, res) is True
    # but a co-occurring selector step still blocks at tier0
    assert M.scenario_eligible([M.R_VFOCUS, M.R_SELECTOR], non, res) is False


def test_mixed_focus_and_selector_unlocks_only_at_tier1():
    reqs = [M.R_VFOCUS, M.R_SELECTOR]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier1"]) is True


def test_screen_present_only_in_screen_scenario():
    reqs = [M.R_RESOLVED, M.R_VSCREEN]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0_screen"]) is True


def test_all_focus_steps_reclassified_leaves_no_executable():
    # a TC that is ONLY a focus-state step -> after tier0 it has 0 executable -> not eligible
    assert M.scenario_eligible([M.R_VFOCUS], *M.SCENARIOS["tier0"]) is False


def test_blocker_never_resolves():
    assert M.scenario_eligible([M.R_BLOCKER], *M.SCENARIOS["optimistic_upper_bound"]) is False
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "scenario or tier or baseline_eligible or blocker_never" -v`
Expected: FAIL — `M.SCENARIOS` / `M.scenario_eligible` not defined.

- [ ] **Step 3: Write the implementation** (append)

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "scenario or tier or baseline_eligible or blocker_never" -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 5: `build` (manifest rows → subtype_rows + per-TC step reqs)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
_MINI = [
    {"tc_id": "T_FOCUS", "source_file": "x.xlsx",
     "entry_detail": "press_key:1. Home 버튼 누른다 > press_key:wifi focus"},
    {"tc_id": "T_STATE_OK", "source_file": "x.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:앱 서랍 포커스 되지 않은 상태"},
    {"tc_id": "T_SELECTOR", "source_file": "x.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:사진"},
    {"tc_id": "T_EMPTY", "source_file": "x.xlsx", "entry_detail": "—"},
]


def test_build_emits_one_row_per_not_a_key_step():
    subtype_rows, tc_steps = M.build(_MINI)
    # NOT_A_KEY steps across the mini set: wifi focus, 포커스 상태, 사진 = 3
    assert len(subtype_rows) == 3
    by_tc = {r["tc_id"]: r["not_a_key_subtype"] for r in subtype_rows}
    assert by_tc["T_FOCUS"] == M.VERIFIER_FOCUS_CANDIDATE
    assert by_tc["T_STATE_OK"] == M.VERIFIER_FOCUS_STATE
    assert by_tc["T_SELECTOR"] == M.SELECTOR_DISCOVERY


def test_build_tc_steps_carry_requirements():
    _, tc_steps = M.build(_MINI)
    reqs = [d["req"] for d in tc_steps["T_STATE_OK"]]
    assert reqs == [M.R_RESOLVED, M.R_VFOCUS]


def test_build_empty_entry_is_single_nonexec():
    _, tc_steps = M.build(_MINI)
    assert [d["req"] for d in tc_steps["T_EMPTY"]] == [M.R_NONEXEC]
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k build -v`
Expected: FAIL — `M.build` not defined.

- [ ] **Step 3: Write the implementation** (append)

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k build -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 6: `summarize` (counts, eligibility, deltas, remaining-blocked, self_check)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_summarize_headline_and_deltas():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    # baseline: T_EMPTY no exec; T_FOCUS has VFOCUS_CAND blocker; T_STATE_OK has VFOCUS
    # blocker; T_SELECTOR has SELECTOR blocker -> baseline eligible = 0
    assert s["eligible"]["baseline"] == 0
    # tier0 drops VFOCUS -> T_STATE_OK becomes eligible (Home resolved + focus dropped)
    assert s["eligible"]["tier0"] == 1
    assert s["headline_now_unlock"] == 1            # tier0 - baseline
    # tier1 adds SELECTOR -> T_SELECTOR also eligible
    assert s["deltas"]["selector_delta"] == 1
    # focus_candidate scenario unlocks T_FOCUS
    assert s["deltas"]["focus_candidate_delta"] == 1


def test_summarize_subtype_counts():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["subtype_counts"][M.VERIFIER_FOCUS_STATE] == 1
    assert s["subtype_counts"][M.SELECTOR_DISCOVERY] == 1


def test_summarize_self_check_flags_mismatch():
    subtype_rows, tc_steps = M.build(_MINI)
    assert M.summarize(subtype_rows, tc_steps, predecessor_headline=0)["self_check"] == "ok"
    assert M.summarize(subtype_rows, tc_steps, predecessor_headline=99)["self_check"] == "mismatch"
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k summarize -v`
Expected: FAIL — `M.summarize` not defined.

- [ ] **Step 3: Write the implementation** (append)

```python
_SUBTYPES = (VERIFIER_FOCUS_STATE, VERIFIER_FOCUS_CANDIDATE, VERIFIER_SCREEN_PRESENT,
             MANUAL_RETAIN, KEYCODE_DISCOVERY, SELECTOR_DISCOVERY)


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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k summarize -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 7: IO writers + forbidden-word guard

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_forbidden_word_guard_raises():
    import pytest
    with pytest.raises(AssertionError):
        M.assert_no_forbidden("this text contains RUNNABLE_NOW which is banned")
    M.assert_no_forbidden("clean device-pilot eligibility text")  # no raise


def test_summary_md_has_no_forbidden_tokens_and_labels():
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    md = M.render_summary_md(s)
    for w in ("PASS", "RUNNABLE_NOW", "validated"):
        assert w not in md
    assert "headline_now_unlock" in md
    assert "(step-level)" in md and "(TC-level)" in md
    assert "self_check=ok" in md


def test_write_outputs_roundtrip(tmp_path):
    subtype_rows, tc_steps = M.build(_MINI)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    ledger_csv = tmp_path / "ledger.csv"
    cascade_csv = tmp_path / "cascade.csv"
    summary_md = tmp_path / "summary.md"
    M.write_subtype_csv(subtype_rows, str(ledger_csv))
    M.write_cascade_csv(tc_steps, str(cascade_csv))
    M.write_summary_md(s, str(summary_md))
    import csv as _csv
    with open(ledger_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) == 3
    assert set(M.SUBTYPE_COLUMNS).issubset(rows[0].keys())
    with open(cascade_csv, encoding="utf-8-sig", newline="") as f:
        crows = list(_csv.DictReader(f))
    assert {"tc_id", "baseline", "tier0", "tier2"}.issubset(crows[0].keys())
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "forbidden or summary_md or write_outputs" -v`
Expected: FAIL — writers/guard not defined.

- [ ] **Step 3: Write the implementation** (append)

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k "forbidden or summary_md or write_outputs" -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 8: Golden fixture + full-pipeline golden test

**Files:**
- Create: `tests/fixtures/altbasic/not_a_key_subtype_golden.json`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the golden fixture** (`tests/fixtures/altbasic/not_a_key_subtype_golden.json`)

```json
{
  "manifest_rows": [
    {"tc_id": "G_FOCUS_STATE", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:앱 서랍 포커스 되지 않은 상태"},
    {"tc_id": "G_FOCUS_CAND", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:전원 버튼 focus"},
    {"tc_id": "G_SCREEN", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:간편 설정 페이지"},
    {"tc_id": "G_MANUAL", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:긴급 전화"},
    {"tc_id": "G_KEYCODE", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:뒤로가기"},
    {"tc_id": "G_SELECTOR", "source_file": "g.xlsx",
     "entry_detail": "press_key:Home 버튼 누른다 > press_key:사진"},
    {"tc_id": "G_MIXED", "source_file": "g.xlsx",
     "entry_detail": "press_key:wifi focus > tap:더보기 Tap"}
  ],
  "expected_subtype_counts": {
    "VERIFIER_FOCUS_STATE": 1,
    "VERIFIER_FOCUS_CANDIDATE": 2,
    "VERIFIER_SCREEN_PRESENT": 1,
    "MANUAL_RETAIN": 1,
    "KEYCODE_DISCOVERY": 1,
    "SELECTOR_DISCOVERY": 1
  },
  "expected_eligible": {
    "baseline": 0,
    "tier0": 1,
    "tier1": 2,
    "tier2": 3,
    "tier0_screen": 2,
    "tier0_focus_candidate": 2,
    "tier0_adjudicate": 1,
    "optimistic_upper_bound": 6
  },
  "expected_headline_now_unlock": 1,
  "screen_present_only_tc": "G_SCREEN"
}
```

> Counts rationale (engineer: verify against the classifier, do not blindly trust):
> 7 TCs. NOT_A_KEY steps = the 2nd step of G_FOCUS_STATE/CAND/SCREEN/MANUAL/KEYCODE/SELECTOR
> (6) + the `wifi focus` step of G_MIXED (1) = **7 subtype rows**, distributed as above
> (G_MIXED's `wifi focus` → VERIFIER_FOCUS_CANDIDATE, so FOCUS_CANDIDATE = G_FOCUS_CAND +
> G_MIXED = 2). baseline eligible = 0 (every TC has one non-RESOLVED executable step).
> tier0 (+VFOCUS→nonexec): only G_FOCUS_STATE (Home RESOLVED, focus-state dropped) = 1.
> tier1 (+SELECTOR): G_SELECTOR joins → 2. tier2 (+KEYCODE): G_KEYCODE joins → 3.
> tier0_screen: G_FOCUS_STATE + G_SCREEN = 2. tier0_focus_candidate: G_FOCUS_STATE +
> G_FOCUS_CAND = 2 (G_MIXED still blocked by its tap-selector) . tier0_adjudicate: 1
> (no ADJUDICATE steps). optimistic_upper_bound: all except G_MANUAL (BLOCKER) = 6.

- [ ] **Step 2: Write the failing golden test** (append to test file)

```python
import json


def test_golden_full_pipeline():
    golden = json.loads(
        (_ROOT / "tests" / "fixtures" / "altbasic" / "not_a_key_subtype_golden.json")
        .read_text(encoding="utf-8"))
    subtype_rows, tc_steps = M.build(golden["manifest_rows"])
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["subtype_counts"] == golden["expected_subtype_counts"]
    assert s["eligible"] == golden["expected_eligible"]
    assert s["headline_now_unlock"] == golden["expected_headline_now_unlock"]


def test_golden_screen_present_excluded_from_headline():
    """간편 설정 페이지 contributes to screen_present_delta but NOT headline_now_unlock."""
    golden = json.loads(
        (_ROOT / "tests" / "fixtures" / "altbasic" / "not_a_key_subtype_golden.json")
        .read_text(encoding="utf-8"))
    subtype_rows, tc_steps = M.build(golden["manifest_rows"])
    # the screen-present TC is eligible at tier0_screen but not at tier0
    reqs = [d["req"] for d in tc_steps[golden["screen_present_only_tc"]]]
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0"]) is False
    assert M.scenario_eligible(reqs, *M.SCENARIOS["tier0_screen"]) is True
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=0)
    assert s["deltas"]["screen_present_delta"] >= 1
```

- [ ] **Step 3: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k golden -v`
Expected: FAIL first run if any count is off → **engineer recomputes against the actual classifier output and corrects the golden JSON (the JSON is the assertion, the classifier is the source of truth — fix the JSON to the real output only after eyeballing each value is defensible).**

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k golden -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -q` → all passed.

---

### Task 9: `main` / CLI + run on the real manifest (self-consistency baseline==5)

**Files:**
- Modify: `scripts/altbasic_not_a_key_subtype_ledger.py`
- Test: `tests/test_altbasic_not_a_key_subtype_ledger.py`

- [ ] **Step 1: Write the failing test** (append)

```python
def test_real_manifest_baseline_matches_predecessor():
    """Self-consistency: baseline_eligible over the real batch10 manifest == predecessor
    headline (5). Also assert the 189 NOT_A_KEY step count is reproduced."""
    rows = M.load_manifest(M.DEFAULT_MANIFEST)
    subtype_rows, tc_steps = M.build(rows)
    s = M.summarize(subtype_rows, tc_steps, predecessor_headline=5)
    assert s["self_check"] == "ok"            # baseline_eligible == 5
    assert s["not_a_key_steps"] == 189        # predecessor NOT_A_KEY tier
    assert s["total_tcs"] == 236
```

- [ ] **Step 2: Run to verify fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k real_manifest -v`
Expected: FAIL — `M.DEFAULT_MANIFEST` / `M.main` not defined. (If `not_a_key_steps`/`baseline` assertions surface a real discrepancy, STOP and reconcile with the predecessor — do not paper over it.)

- [ ] **Step 3: Write the implementation** (append)

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py -k real_manifest -v`
Expected: PASS. If `self_check == mismatch` or `not_a_key_steps != 189`, STOP — the predecessor classifier changed or the manifest drifted; reconcile before continuing.

- [ ] **Step 5: Full-suite checkpoint**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_not_a_key_subtype_ledger.py tests/test_altbasic_entry_detail_ledger.py -q`
Expected: new tests + predecessor **39 passed** (zero predecessor regression). Then `venv/Scripts/python.exe -m pytest -q` for the full repo suite → all passed.

---

### Task 10: Generate artifacts + EOD batch commit (EXPLICIT APPROVAL REQUIRED)

**Files (artifacts, untracked until commit):**
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv`
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_CASCADE_2026-06-29.csv`
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md`

- [ ] **Step 1: Generate the artifacts**

Run: `venv/Scripts/python.exe scripts/altbasic_not_a_key_subtype_ledger.py`
Expected: prints `self_check=ok`, writes the 3 files into the audit folder.

- [ ] **Step 2: Eyeball the summary**

Read `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md`. Confirm:
- `self_check=ok`; subtype counts sum to 189;
- `headline_now_unlock` is reported as the only no-device number; every other delta is labelled potential;
- no `PASS`/`RUNNABLE_NOW`/`validated` tokens;
- remaining-blocked breakdown present.

Report the headline number and the subtype distribution to the user. **This is the deliverable that answers "how many TCs unlock without a device".**

- [ ] **Step 3: STOP — await user decision**

The track ends here (spec §11: which subtypes to action next is a separate, user-gated track). Do NOT reclassify any yaml.

- [ ] **Step 4: EOD batch commit — ONLY on explicit user "commit now"**

Per global §7: no commit without explicit approval. When approved, run the push-audit-style staging discipline (named paths only):

```bash
git status --short
git add scripts/altbasic_not_a_key_subtype_ledger.py \
        tests/test_altbasic_not_a_key_subtype_ledger.py \
        tests/fixtures/altbasic/not_a_key_subtype_golden.json \
        docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md \
        docs/superpowers/plans/2026-06-29-altbasic-not-a-key-subtype-ledger.md \
        "THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv" \
        "THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_CASCADE_2026-06-29.csv" \
        "THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md"
git diff --cached --name-only   # confirm ONLY the named paths are staged
git status --short              # confirm nothing unexpected
git commit -m "feat(altbasic): NOT_A_KEY subtype ledger + eligibility cascade (host-TDD, 189 sub-classified)"
```

Expected: exactly the named paths staged (no broad add, no surprise files). Report changed/staged files + test results + final `git status` per §7 report format. Push remains a separate explicit decision.

---

## Self-Review (plan vs spec)

- **§3 6 subtypes** → Task 2 (all 6 + precedence + boundary cases). ✓
- **§3.2 fail-closed focus candidate** → Task 2 `test_bare_focus_is_candidate_not_state`. ✓
- **§4 resolution_requirement over all 620 steps (incl FREE_TEXT selector/keycode)** → Task 3. ✓
- **§5 cascade scenarios + deltas + naming (baseline/tier0/tier0_delta)** → Task 4 + Task 6. ✓
- **§5.4 headline = tier0_delta** → Task 6 `test_summarize_headline_and_deltas`, Task 10 step 2. ✓
- **§5.5 forbidden denylist PASS/RUNNABLE_NOW/validated** → Task 7 guard + Task 8/10 assertions. ✓
- **§6 two outputs (subtype ledger + cascade CSV)** → Task 7 writers. ✓
- **§7 summary labels (step-level)/(TC-level) + self_check + remaining-blocked + STOP** → Task 7 `render_summary_md`. ✓
- **§8 reuse predecessor (no fork), 39 tests green** → Task 1 import + Task 9 step 5 regression. ✓
- **§9 golden incl 간편 설정 페이지 screen-only + mixed focus+selector tier1** → Task 8 golden + Task 4 mixed test. ✓
- **§10 invariant baseline_eligible==5** → Task 9 `test_real_manifest_baseline_matches_predecessor`. ✓
- **Non-goals: no device/mutation/catalog/commit-without-approval** → header + Task 10 STOP/approval gate. ✓

No placeholders; method/constant names consistent across tasks (`R_VFOCUS`, `SCENARIOS`, `subclassify_not_a_key`, `build`, `summarize`, `render_summary_md`).
