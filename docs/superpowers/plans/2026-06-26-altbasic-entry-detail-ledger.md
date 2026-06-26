# ALT Basic entry_detail Normalization Ledger — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a host-TDD'd, read-only generator that classifies every `entry_detail` step of the 236-row batch10 device-validation manifest into 5 normalization dispositions and emits a defensible measurement ledger (CSV + summary) of device-pilot unlock potential — then STOP, no code/yaml mutation, no device.

**Architecture:** One tc-runner module `scripts/altbasic_entry_detail_ledger.py` in the `settings_anchor_gap.py` shape — pure parser/classifier functions at the top (no IO, no wall-clock, no device, no network), thin manifest-read + CSV/MD-write + `main()` at the bottom. Conservative-by-construction: any uncertainty falls *below* NOW_RESOLVABLE, so classification error biases toward under-counting the headline, never inflating it.

**Tech Stack:** Python 3.12, pytest 9.0.2. Run tests with **`venv/Scripts/python.exe -m pytest`** from repo root (root `conftest.py` adds repo root to `sys.path`). Tests load the script via `importlib.util.spec_from_file_location` (the established `tests/test_settings_anchor_gap.py` pattern). No new dependencies — stdlib `csv`/`re`/`dataclasses`/`collections`/`argparse` only.

**Spec:** `docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md`

---

> ### ⚠ COMMIT POLICY (overrides skill's per-task `git commit` step)
> Global policy §7 + project §7.1: **do NOT auto-commit per task.** Each task ends at "tests GREEN" (a checkpoint only). The module + tests + golden fixture + ledger artifacts are committed in **one end-of-day batch with explicit user approval**, staged with explicit paths only (no `git add .`/`-A`/dir). No `git commit` step appears in any task below.

> ### ⚠ BOUNDARY (spec §2)
> Read-only. No edit to the runner, `validate_tc.py`, canonical STAGE1 yaml, the manifest, or the thor2j driver. No device, no Appium, no network. The directional resolver port into the device driver is a **future thor2j track**, out of scope here.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/altbasic_entry_detail_ledger.py` (create) | **Pure:** `Step`, `parse_entry_detail`, `normalize_body`/`_compact`, key vocab + marker regexes, `resolve_single_key`, `classify_step`, `rollup_eligibility`. **IO:** `load_manifest`, `build_ledger`, `summarize`, `write_ledger_csv`, `write_summary_md`, `main`. |
| `tests/test_altbasic_entry_detail_ledger.py` (create) | Unit tests for every pure function + each disposition boundary + rollup + a full golden-snapshot test. |
| `tests/fixtures/altbasic/entry_detail_ledger_golden.json` (create) | Golden expected ledger rows for a curated fixture subset (all 5 tiers, every boundary pair, the required `device_keycode_discovery` case, the §5.1 mixed-token case, and the C01 calibration rows). |

**Output artifacts** (durable evidence, written by `main()`, local until EOD batch):
- `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
- `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`

**Module-level constants (defined once in Task 1, referenced everywhere):**

```python
# dispositions
NOW_RESOLVABLE = "NOW_RESOLVABLE"
ADJUDICATE = "ADJUDICATE"
AMBIGUOUS_NOGUESS = "AMBIGUOUS_NOGUESS"
NOT_A_KEY = "NOT_A_KEY"
FREE_TEXT_DISCOVERY = "FREE_TEXT_DISCOVERY"

# required_decision values
RD_NONE = ""
RD_INTENT = "intent_choice"
RD_SPEC = "spec_clarification"
RD_RECLASSIFY = "reclassify_verifier_or_navigate"
RD_SEL_DISCOVERY = "device_selector_discovery"
RD_KEY_DISCOVERY = "device_keycode_discovery"
RD_MANIFEST = "manifest_rewrite"
```

---

## Task 1: Module skeleton + `parse_entry_detail`

**Files:**
- Create: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_altbasic_entry_detail_ledger.py
"""Tests for scripts/altbasic_entry_detail_ledger.py (read-only normalization ledger).

Pure parser/classifier tested with synthetic strings only. NO device, NO network,
NO wall-clock. Manifest IO + golden snapshot covered in later tasks.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "altbasic_entry_detail_ledger.py"
_spec = importlib.util.spec_from_file_location("altbasic_entry_detail_ledger", _PATH)
L = importlib.util.module_from_spec(_spec)
sys.modules["altbasic_entry_detail_ledger"] = L
_spec.loader.exec_module(L)


def test_parse_single_press_key_strips_step_number():
    steps = L.parse_entry_detail("press_key:1. Recent App 버튼 누른다")
    assert len(steps) == 1
    assert steps[0].action == "press_key"
    assert steps[0].body == "Recent App 버튼 누른다"


def test_parse_multistep_split_on_gt():
    steps = L.parse_entry_detail("tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다")
    assert [s.action for s in steps] == ["tap", "press_key"]
    assert steps[1].body == "하드키 돌아가기 버튼 누른다"


def test_parse_bare_continuation_is_marked_bare():
    steps = L.parse_entry_detail("press_key:1. Home 버튼 누른다 > Press Down")
    assert steps[0].action == "press_key"
    assert steps[1].action == "(bare)"
    assert steps[1].body == "Press Down"


def test_parse_unknown_prefix_is_marked_question():
    steps = L.parse_entry_detail("foobar:do something")
    assert steps[0].action == "?foobar"


def test_parse_empty_or_dash_returns_empty():
    assert L.parse_entry_detail("") == []
    assert L.parse_entry_detail("—") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -v`
Expected: FAIL (`ModuleNotFoundError` / file not found on `exec_module`).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/altbasic_entry_detail_ledger.py
# -*- coding: utf-8 -*-
"""ALT Basic batch10 entry_detail normalization measurement ledger (read-only).

Classifies each entry_detail step into one of 5 dispositions and quantifies
device-pilot unlock potential. NO device, NO mutation of runner/yaml/manifest.
See docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md
"""
from __future__ import annotations

import re
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Checkpoint** — tests GREEN. No commit (batch-deferred per policy header).

---

## Task 2: `normalize_body` + `_compact`

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def test_normalize_strips_step_num_and_trailing_verb():
    assert L.normalize_body("1. Home 버튼 누른다") == "Home 버튼"
    assert L.normalize_body("Recent App 버튼 누른다.") == "Recent App 버튼"


def test_normalize_keeps_markers():
    # parentheses, slash, 또는 must survive for marker detection
    assert "(" in L.normalize_body("Navi 키(OK) 버튼을 누른다.")
    assert "또는" in L.normalize_body("네비키 또는 OK키 입력")


def test_compact_casefolds_and_removes_space():
    assert L._compact("Press Down") == "pressdown"
    assert L._compact("UP 방향키") == "up방향키"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "normalize or compact" -v`
Expected: FAIL (`AttributeError: normalize_body`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "normalize or compact" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 3: Key vocabulary + marker regexes + `resolve_single_key`

This is the defensible core. `resolve_single_key` returns `(keycode_or_None, verdict)` where `verdict ∈ {"RESOLVED", "ADJUDICATE", "AMBIGUOUS", "NONE"}`.

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def test_resolve_named_keys():
    assert L.resolve_single_key("Recent App 버튼") == (187, "RESOLVED")
    assert L.resolve_single_key("Home 버튼 누른다") == (3, "RESOLVED")
    assert L.resolve_single_key("Camera 버튼") == (27, "RESOLVED")
    assert L.resolve_single_key("Contact 버튼") == (207, "RESOLVED")
    assert L.resolve_single_key("하드키 돌아가기 버튼") == (4, "RESOLVED")


def test_resolve_single_direction_now_resolvable():
    assert L.resolve_single_key("Press Down") == (20, "RESOLVED")
    assert L.resolve_single_key("UP 방향키") == (19, "RESOLVED")
    assert L.resolve_single_key("하방향키") == (20, "RESOLVED")
    assert L.resolve_single_key("Right 방향키") == (22, "RESOLVED")
    assert L.resolve_single_key("press ok") == (23, "RESOLVED")
    assert L.resolve_single_key("Press down(하드키)") == (20, "RESOLVED")


def test_resolve_disjunction_is_adjudicate():
    kc, v = L.resolve_single_key("네비키 또는 OK키")
    assert v == "ADJUDICATE" and kc == 23
    kc, v = L.resolve_single_key("Navi 키(OK) 버튼을 누른다.")
    assert v == "ADJUDICATE"


def test_resolve_any_and_enumeration_is_ambiguous():
    assert L.resolve_single_key("아무 방향키")[1] == "AMBIGUOUS"
    assert L.resolve_single_key("Press Any Direction")[1] == "AMBIGUOUS"
    assert L.resolve_single_key("홈화면에서 Navi U/D/L/R/OK 키 입력한다")[1] == "AMBIGUOUS"


def test_resolve_slash_keyname_is_not_direction_enumeration():
    # 지우기/취소 has a slash but is NOT a direction enumeration → NONE (not AMBIGUOUS)
    assert L.resolve_single_key("지우기/취소 버튼")[1] == "NONE"


def test_resolve_screen_name_is_none():
    assert L.resolve_single_key("시계")[1] == "NONE"
    assert L.resolve_single_key("wifi focus")[1] == "NONE"
    assert L.resolve_single_key("앱서랍 진입")[1] == "NONE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k resolve -v`
Expected: FAIL (`AttributeError: resolve_single_key`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py

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
    19: ("up", "위", "상"),
    20: ("down", "아래", "하"),
    21: ("left", "왼", "좌"),
    22: ("right", "오른", "우"),
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
    navi_paren = ("navi" in c or "네비" in c) and ("(" in nb)
    has_or = "또는" in c
    if navi_paren or has_or:
        cand = next(iter(dirs)) if len(dirs) == 1 else None
        return cand, "ADJUDICATE"
    if len(dirs) == 1:
        return next(iter(dirs)), "RESOLVED"
    if len(dirs) >= 2:
        return None, "AMBIGUOUS"
    return None, "NONE"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k resolve -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 4: `classify_step` (5-tier routing + ledger fields)

`classify_step(step)` returns a dict with the per-step ledger fields (everything except `tc_id`/`source_file`/`original_entry_detail`, which `build_ledger` adds): `extracted_token, disposition, proposed_normalized_step, proposed_keycode, confidence, rationale, required_decision, executable`.

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def _disp(action, body):
    return L.classify_step(L.Step(action=action, body=body, raw=body))["disposition"]


def test_classify_now_resolvable():
    r = L.classify_step(L.Step("press_key", "Recent App 버튼 누른다", "x"))
    assert r["disposition"] == L.NOW_RESOLVABLE
    assert r["proposed_keycode"] == 187
    assert r["confidence"] == "high"
    assert r["executable"] is True


def test_classify_bare_direction_now_resolvable():
    assert _disp("(bare)", "Press Down") == L.NOW_RESOLVABLE


def test_classify_adjudicate_sets_intent_decision():
    r = L.classify_step(L.Step("press_key", "네비키 또는 OK키 입력", "x"))
    assert r["disposition"] == L.ADJUDICATE
    assert r["required_decision"] == L.RD_INTENT
    assert r["confidence"] == "medium"


def test_classify_ambiguous_sets_spec_decision():
    r = L.classify_step(L.Step("press_key", "아무 방향키", "x"))
    assert r["disposition"] == L.AMBIGUOUS_NOGUESS
    assert r["required_decision"] == L.RD_SPEC


def test_classify_named_key_without_keycode_is_device_keycode_discovery():
    # REQUIRED fixture case (spec §3.2)
    r = L.classify_step(L.Step("press_key", "Message 버튼 누른다", "x"))
    assert r["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r["required_decision"] == L.RD_KEY_DISCOVERY
    r2 = L.classify_step(L.Step("press_key", "지우기/취소 버튼", "x"))
    assert r2["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r2["required_decision"] == L.RD_KEY_DISCOVERY


def test_classify_screen_ref_is_not_a_key():
    r = L.classify_step(L.Step("press_key", "wifi focus", "x"))
    assert r["disposition"] == L.NOT_A_KEY
    assert r["required_decision"] == L.RD_RECLASSIFY


def test_classify_tap_is_selector_discovery():
    r = L.classify_step(L.Step("tap", "퀵 패널", "x"))
    assert r["disposition"] == L.FREE_TEXT_DISCOVERY
    assert r["required_decision"] == L.RD_SEL_DISCOVERY


def test_classify_observe_token_is_non_executable():
    r = L.classify_step(L.Step("(bare)", "기본 항목 확인한다", "x"))
    assert r["executable"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k classify -v`
Expected: FAIL (`AttributeError: classify_step`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
_SCREEN_MARKERS = ("focus", "화면", "페이지", "진입", "스크린", "screen")
_OBSERVE_RE = re.compile(r"(확인한다|확인됨|표시된다|노출된다|확인 한다)\s*$")


def _is_observe(nb: str) -> bool:
    return bool(_OBSERVE_RE.search(nb))


def _is_named_key_no_keycode(c: str) -> bool:
    # ends with 버튼/키 but did not resolve and is not a screen ref
    return c.endswith("버튼") or c.endswith("키")


def _is_screen_ref(c: str) -> bool:
    return any(m in c for m in _SCREEN_MARKERS)


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
    if step.action == "(bare)" and _is_observe(nb):
        return _row(FREE_TEXT_DISCOVERY, token, "(observe)", "", "low",
                    "non-executable observe token (excluded from rollup)", RD_NONE, False)

    # tap / navigate → selector discovery
    if step.action in ("tap", "navigate"):
        return _row(FREE_TEXT_DISCOVERY, token, f"{step.action}:<{nb}>", "", "low",
                    f"{step.action} target needs a selector", RD_SEL_DISCOVERY, True)

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


def _has_latin_or_digit(c: str) -> bool:
    return bool(re.search(r"[a-z0-9]", c))
```

> **Note on `_is_screen_ref` vs `_is_named_key_no_keycode` order:** screen-ref is checked first so `wifi focus` (which also has no 버튼/키 suffix) routes to NOT_A_KEY, while `Message 버튼` (no screen marker, 버튼 suffix) routes to device_keycode_discovery. The trailing bare-noun branch catches `시계`/`타이머` (no latin, no 버튼/키, no screen marker) as NOT_A_KEY.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k classify -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 5: `rollup_eligibility` (TC-level, executable steps only)

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def test_rollup_all_resolvable_is_eligible():
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
    ]
    assert L.rollup_eligibility(rows) is True


def test_rollup_one_blocking_step_is_not_eligible():
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.AMBIGUOUS_NOGUESS, "executable": True},
    ]
    assert L.rollup_eligibility(rows) is False


def test_rollup_excludes_non_executable_token():
    # mixed-token case (spec §5.1): observe token excluded, TC stays eligible
    rows = [
        {"disposition": L.NOW_RESOLVABLE, "executable": True},
        {"disposition": L.FREE_TEXT_DISCOVERY, "executable": False},
    ]
    assert L.rollup_eligibility(rows) is True


def test_rollup_no_executable_steps_is_not_eligible():
    rows = [{"disposition": L.FREE_TEXT_DISCOVERY, "executable": False}]
    assert L.rollup_eligibility(rows) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k rollup -v`
Expected: FAIL (`AttributeError: rollup_eligibility`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
def rollup_eligibility(step_rows: list[dict]) -> bool:
    """TC-level fail-closed: eligible iff there is >=1 executable step AND every
    executable step is NOW_RESOLVABLE. Non-executable tokens are excluded."""
    execs = [r for r in step_rows if r.get("executable")]
    if not execs:
        return False
    return all(r["disposition"] == NOW_RESOLVABLE for r in execs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k rollup -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 6: `load_manifest` + `build_ledger`

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
import csv as _csv

LEDGER_COLUMNS = [
    "tc_id", "source_file", "original_entry_detail", "extracted_token",
    "disposition", "proposed_normalized_step", "proposed_keycode",
    "confidence", "rationale", "required_decision", "device_pilot_eligible",
    "executable",
]


def _write_manifest(tmp_path):
    p = tmp_path / "m.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["tc_id", "source_file", "entry_detail"])
        w.writerow(["ALTBASIC_BSC_014", "x.xlsx", "press_key:1. Recent App 버튼 누른다"])
        w.writerow(["ALTBASIC_BSC_120",
                    "x.xlsx", "tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다"])
    return str(p)


def test_load_manifest_reads_rows(tmp_path):
    rows = L.load_manifest(_write_manifest(tmp_path))
    assert [r["tc_id"] for r in rows] == ["ALTBASIC_BSC_014", "ALTBASIC_BSC_120"]


def test_build_ledger_one_row_per_step_with_all_columns(tmp_path):
    rows = L.load_manifest(_write_manifest(tmp_path))
    ledger = L.build_ledger(rows)
    # BSC_014 = 1 step, BSC_120 = 2 steps => 3 ledger rows
    assert len(ledger) == 3
    for r in ledger:
        assert set(LEDGER_COLUMNS).issubset(r.keys())
    bsc014 = [r for r in ledger if r["tc_id"] == "ALTBASIC_BSC_014"]
    assert bsc014[0]["device_pilot_eligible"] is True   # single resolvable key
    # BSC_120 has a tap step (selector discovery) => not eligible
    bsc120 = [r for r in ledger if r["tc_id"] == "ALTBASIC_BSC_120"]
    assert all(r["device_pilot_eligible"] is False for r in bsc120)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "load_manifest or build_ledger" -v`
Expected: FAIL (`AttributeError: load_manifest`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
import csv  # top-of-file import block

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "load_manifest or build_ledger" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 7: `summarize` (tier counts + headline/potential TC metrics + top unlock + calibration)

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def _ledger_from(entries):
    # entries: list of (tc_id, entry_detail)
    rows = [{"tc_id": t, "source_file": "x.xlsx", "entry_detail": e} for t, e in entries]
    return L.build_ledger(rows)


def test_summarize_tier_counts_are_step_level():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # 1 NOW_RESOLVABLE
        ("T2", "press_key:1. 아무 방향키"),                      # 1 AMBIGUOUS
        ("T3", "tap:1. 퀵 패널"),                                # 1 FREE_TEXT
    ])
    s = L.summarize(ledger)
    assert s["tier_counts"][L.NOW_RESOLVABLE] == 1
    assert s["tier_counts"][L.AMBIGUOUS_NOGUESS] == 1
    assert s["tier_counts"][L.FREE_TEXT_DISCOVERY] == 1


def test_summarize_headline_is_tc_level():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # eligible
        ("T2", "press_key:1. Home 버튼 누른다 > Press Down"),    # eligible (both resolvable)
        ("T3", "press_key:1. 아무 방향키"),                      # not eligible
    ])
    s = L.summarize(ledger)
    assert s["headline_resolvable_count"] == 2          # TC-level
    assert s["potential_with_adjudication_count"] >= 2  # at least the eligible ones


def test_summarize_potential_counts_adjudicate_only_tcs():
    ledger = _ledger_from([
        ("T1", "press_key:1. Home 버튼 누른다"),                 # eligible
        ("T2", "press_key:1. 네비키 또는 OK키 입력"),            # adjudicate-only
    ])
    s = L.summarize(ledger)
    assert s["headline_resolvable_count"] == 1
    assert s["potential_with_adjudication_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k summarize -v`
Expected: FAIL (`AttributeError: summarize`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
from collections import Counter, defaultdict  # top-of-file import block

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

    # top unlock rules: which rationale produces the most NOW_RESOLVABLE *TCs*
    unlock = Counter()
    for tc, rows in by_tc.items():
        if rows[0]["device_pilot_eligible"]:
            for r in rows:
                if r["disposition"] == NOW_RESOLVABLE:
                    unlock[r["proposed_normalized_step"]] += 1

    return {
        "total_steps": len(ledger),
        "total_tcs": len(by_tc),
        "tier_counts": dict(tier_counts),          # step-level
        "headline_resolvable_count": headline,      # TC-level
        "potential_with_adjudication_count": potential,  # TC-level
        "top_unlock": unlock.most_common(10),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k summarize -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 8: Writers + `main` CLI

**Files:**
- Modify: `scripts/altbasic_entry_detail_ledger.py`
- Test: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
def test_write_ledger_csv_roundtrip(tmp_path):
    ledger = _ledger_from([("T1", "press_key:1. Home 버튼 누른다")])
    out = tmp_path / "ledger.csv"
    L.write_ledger_csv(ledger, str(out))
    with open(out, encoding="utf-8-sig", newline="") as f:
        got = list(_csv.DictReader(f))
    assert got[0]["tc_id"] == "T1"
    assert got[0]["disposition"] == L.NOW_RESOLVABLE
    assert list(got[0].keys()) == LEDGER_COLUMNS   # exact column order


def test_write_summary_md_labels_levels(tmp_path):
    ledger = _ledger_from([("T1", "press_key:1. Home 버튼 누른다")])
    s = L.summarize(ledger)
    out = tmp_path / "summary.md"
    L.write_summary_md(s, str(out))
    text = out.read_text(encoding="utf-8")
    assert "(step-level)" in text
    assert "(TC-level)" in text
    assert "headline_resolvable_count" in text


def test_main_writes_both_artifacts(tmp_path):
    man = _write_manifest(tmp_path)
    csv_out = tmp_path / "L.csv"
    md_out = tmp_path / "S.md"
    L.main(["--manifest", man, "--ledger-out", str(csv_out), "--summary-out", str(md_out)])
    assert csv_out.exists() and md_out.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "write_ledger or write_summary or main_writes" -v`
Expected: FAIL (`AttributeError: write_ledger_csv`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to scripts/altbasic_entry_detail_ledger.py
import argparse  # top-of-file import block
import os        # top-of-file import block

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
```

> Move the `import csv`, `import argparse`, `import os`, `from collections import ...` lines into the
> top-of-file import block (next to `import re`) when integrating — they are shown at point-of-use here for
> readability but Python requires them at module top (or they may stay local; keep the module import block tidy).

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k "write_ledger or write_summary or main_writes" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 9: Golden snapshot test (required fixture cases + C01 calibration)

**Files:**
- Create: `tests/fixtures/altbasic/entry_detail_ledger_golden.json`
- Modify: `tests/test_altbasic_entry_detail_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
import json


def test_golden_snapshot():
    fix = _ROOT / "tests" / "fixtures" / "altbasic" / "entry_detail_ledger_golden.json"
    data = json.loads(fix.read_text(encoding="utf-8"))
    ledger = L.build_ledger(data["manifest"])
    # compare only the classification-relevant fields (stable across runs)
    keys = ["tc_id", "extracted_token", "disposition", "proposed_keycode",
            "required_decision", "device_pilot_eligible", "executable"]
    got = [{k: r[k] for k in keys} for r in ledger]
    assert got == data["expected_ledger"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k golden -v`
Expected: FAIL (fixture file missing → `FileNotFoundError`).

- [ ] **Step 3: Write the fixture**

Create `tests/fixtures/altbasic/entry_detail_ledger_golden.json`. The `manifest` array drives `build_ledger`;
`expected_ledger` is the asserted output. It MUST cover all 5 tiers, every boundary pair, the
`device_keycode_discovery` case, the §5.1 mixed-token case, and the C01 calibration rows
(BSC_014/120/018/025/071). After writing the fixture's `manifest`, run the module once over it to *generate*
the `expected_ledger` (then eyeball every row against the spec before saving — the golden is only valid if a
human confirmed it):

```json
{
  "manifest": [
    {"tc_id": "ALTBASIC_BSC_014", "source_file": "x.xlsx", "entry_detail": "press_key:1. Recent App 버튼 누른다"},
    {"tc_id": "ALTBASIC_BSC_120", "source_file": "x.xlsx", "entry_detail": "tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다"},
    {"tc_id": "ALTBASIC_BSC_018", "source_file": "x.xlsx", "entry_detail": "press_key:1. Message 버튼 누른다"},
    {"tc_id": "ALTBASIC_BSC_025", "source_file": "x.xlsx", "entry_detail": "press_key:1. 종료 버튼 길게 누른다"},
    {"tc_id": "ALTBASIC_BSC_071", "source_file": "x.xlsx", "entry_detail": "press_key:1. 홈화면에서 Navi U/D/L/R/OK 키 입력한다"},
    {"tc_id": "ALTBASIC_DIR_DN", "source_file": "x.xlsx", "entry_detail": "press_key:1. Home 버튼 누른다 > Press Down"},
    {"tc_id": "ALTBASIC_ADJ_OK", "source_file": "x.xlsx", "entry_detail": "press_key:1. 네비키 또는 OK키 입력"},
    {"tc_id": "ALTBASIC_NAK_WIFI", "source_file": "x.xlsx", "entry_detail": "press_key:1. wifi focus"},
    {"tc_id": "ALTBASIC_CANCEL", "source_file": "x.xlsx", "entry_detail": "press_key:1. 지우기/취소 버튼"},
    {"tc_id": "ALTBASIC_MIX_OBS", "source_file": "x.xlsx", "entry_detail": "press_key:1. Press Down > 기본 항목 확인한다"}
  ],
  "expected_ledger": "<<GENERATED THEN HUMAN-CONFIRMED — see Step 3 procedure>>"
}
```

Generation procedure (device-free, in a Python REPL using the module):
1. Load the module, call `build_ledger(data["manifest"])`.
2. Project the 7 `keys` (from the test) for each row.
3. Verify by eye that each row matches the spec — in particular: BSC_014 → NOW_RESOLVABLE/187/eligible;
   BSC_120 → both rows eligible=False (tap = selector); BSC_018 → FREE_TEXT/device_keycode_discovery;
   BSC_025 → FREE_TEXT/device_keycode_discovery (종료 버튼); BSC_071 → AMBIGUOUS_NOGUESS;
   ALTBASIC_DIR_DN → both NOW_RESOLVABLE, eligible=True; ALTBASIC_ADJ_OK → ADJUDICATE/intent;
   ALTBASIC_NAK_WIFI → NOT_A_KEY/reclassify; ALTBASIC_CANCEL → FREE_TEXT/device_keycode_discovery;
   ALTBASIC_MIX_OBS → step1 NOW_RESOLVABLE executable, step2 executable=False (observe), eligible=True.
4. Paste the confirmed projection as `expected_ledger`.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -k golden -v`
Expected: PASS. If a row disagrees with the spec, the classifier (Task 3/4) has a bug — fix the classifier,
not the golden, then regenerate.

- [ ] **Step 5: Run the full test file**

Run: `venv/Scripts/python.exe -m pytest tests/test_altbasic_entry_detail_ledger.py -v`
Expected: PASS (all unit + golden tests).

- [ ] **Step 6: Checkpoint** — GREEN. No commit.

---

## Task 10: Full run over 236 + STOP report (device-free, terminal)

**Files:**
- None modified (read-only run).
- Produces: the two output artifacts in `THOR2 - ALT Basic TC Audit/` (local until EOD batch).

- [ ] **Step 1: Run the generator over the real manifest**

Run: `venv/Scripts/python.exe scripts/altbasic_entry_detail_ledger.py`
Expected: prints `steps=<n> tcs=236`, the step-level tier_counts, the two TC-level headline metrics, and `*** STOP ***`; writes the ledger CSV + summary MD into the audit folder.

- [ ] **Step 2: Sanity + calibration check**

- Confirm `tcs=236` (matches the manifest row count).
- Confirm the 13 sheet-`1.Basic principle` rows (BSC_014/015/017/019 NOW_RESOLVABLE; BSC_018/121 + 031/071/072/073 + 124 not NOW_RESOLVABLE; BSC_025 not NOW_RESOLVABLE; BSC_120 not eligible due to its tap step) agree with the committed C01 narrow-driver routing. Any disagreement = classifier bug → fix Task 3/4 and re-run.
- Confirm `headline_resolvable_count` is conservative (every counted TC has only NOW_RESOLVABLE executable steps).

- [ ] **Step 3: Produce the STOP report to the user**

Report, verbatim from the summary:
- 5 tier counts (step-level).
- `headline_resolvable_count` and `potential_with_adjudication_count` (TC-level).
- Top 10 unlock rules.
- 5–10 representative boundary / misclassification examples (read from the ledger CSV) so the boundary is auditable by eye.
- The C01 calibration result (agree / list disagreements).

- [ ] **Step 4: ★ STOP — measurement complete.**
No device, no code/yaml mutation beyond the new read-only generator + tests + fixture + the two ledger artifacts. Await the user's decision on which normalization rules to build next (the future thor2j resolver track, the ADJUDICATE decisions, the NOT_A_KEY reclassification track). Then propose the EOD batch commit (explicit paths) for approval. Do NOT proceed autonomously.

---

## Self-Review (writing-plans)

**Spec coverage:**
- §1 goal / §2 non-goals → Task 10 STOP gate + read-only boundary header. ✓
- §3 taxonomy (5 tiers) + §3.1 precedence → `resolve_single_key` (T3) + `classify_step` (T4). ✓
- §3.2 named-key-without-keycode → T4 test `...device_keycode_discovery` + golden BSC_018/CANCEL/025 (T9). ✓
- §4 vocabulary → `NAMED_KEYS` + `_DIR_KW` + `_ENUM_RE`/`_ANY_RE` (T3). ✓
- §5 ledger schema (11 cols + executable) → `LEDGER_COLUMNS` + `build_ledger` (T6). ✓
- §5.1 TC-level fail-closed rollup, executable-only → `rollup_eligibility` (T5) + mixed-token golden (T9). ✓
- §6 summary (step-level tiers, TC-level headline/potential, top-10, calibration) → `summarize` (T7) + `write_summary_md` labels (T8) + T10 calibration. ✓
- §7 architecture (pure + IO, settings_anchor_gap pattern) → file structure + T1–T8. ✓
- §8 testing (host TDD, golden, calibration, required cases, no wall-clock) → every task RED→GREEN + T9 golden. ✓
- §9 future tracks → T10 Step 4 (explicitly out of scope). ✓

**Placeholder scan:** No TBD/TODO. The one generated artifact (`expected_ledger`) has an explicit human-confirmed generation procedure in T9 Step 3 (not a placeholder — it's a deterministic generate-then-verify step, the correct way to author a golden). Every code step has complete code.

**Type consistency:** `Step(action,body,raw)` (T1) used uniformly. `resolve_single_key`→`(int|None, str)` (T3) consumed by `classify_step` (T4). `_row(...)`→dict with fixed keys (T4) consumed by `rollup_eligibility`/`build_ledger`/`summarize`. `LEDGER_COLUMNS` order identical in T6 test, T6 impl, T8 writer. `classify_step` field names (`disposition`/`executable`/`required_decision`/`proposed_keycode`) consistent T4→T5→T6→T7→T8. ✓
