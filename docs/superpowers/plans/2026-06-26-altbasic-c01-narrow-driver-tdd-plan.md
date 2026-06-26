# ALT Basic C01 Narrow Fail-Closed Pilot Driver — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a host-TDD'd narrow, fail-closed driver that runs only the cleanly-keyed C01 subset (5 of 13) of the ALT Basic batch10 manifest, routing everything else to explicit fail-closed/observe-only/unsupported states — then STOP before any device contact.

**Architecture:** Two thor2j-tc-appium modules: `runner/altbasic_narrow.py` (pure decision logic — no Appium, fully host-testable) and `runner/altbasic_c01_driver.py` (thin device executor + CLI + dry-run, reusing `runner/altbasic_validation_batch1.py` `b1` infra and `runner/focus_snapshot.py` `fsnap`). All logic is unit-tested host-side with fake Dev / synthetic fsnap fixtures; the device 2-run is a SEPARATE later phase gated on user approval.

**Tech Stack:** Python 3, pytest 9.0.2 — **system python (`python -m pytest`)**. thor2j repo `C:/Users/momen/Projects/thor2j-tc-appium`. Run tests from repo root (`from runner import ...`; `runner/__init__.py` + `tests/conftest.py` present). NOTE: the appium venv `C:/Users/momen/venvs/thor2j_appium` has **no pytest** — it is for the **device phase only** (appium import); host-TDD tests run on system python.

**Spec:** `tc-runner/docs/superpowers/specs/2026-06-26-altbasic-c01-narrow-driver-design.md`

---

> ### ⚠ COMMIT POLICY (overrides skill's per-task commit)
> Global policy §7 + §2.5: **do NOT auto-commit per task.** Each task ends at "tests GREEN" (checkpoint only). thor2j module commits are **deferred to an end-of-day batch with explicit user approval**, staged with explicit paths only. No commit appears as a task step below.

> ### ⚠ DEVICE BOUNDARY
> This plan is **host-only (no device, no Appium, no helper APK).** It ends at a hard STOP (Task 9). The device 2-run (helper install + F0 run1/run2 + keycode/dropdown device-verify) is a separate phase requiring user device-go.

---

## File Structure

| File | Responsibility |
|---|---|
| `runner/altbasic_narrow.py` (create) | Pure: result-code/disposition constants, `Step`, `parse_entry_detail`, `KEY_DICT`+`resolve_keycode`, `literal_decision`, `focus_retained_decision`, `classify_c01_disposition`. No Appium import. |
| `runner/altbasic_c01_driver.py` (create) | Device executor + CLI: manifest loader, disposition dispatch, `check_literal(dev,…)` glue, observe-only/unsupported guards, `--dry-run` report. Imports `b1`+`fsnap`+`altbasic_narrow`. |
| `tests/test_altbasic_narrow.py` (create) | Pure unit tests for `altbasic_narrow` (parser/dict/literal/focus/classify). |
| `tests/test_altbasic_c01_driver.py` (create) | FakeDev glue tests + observe/unsupported guards + classify-over-13 + dry-run counts. |

Disposition routing (spec §3, no-guess): **PILOT_LITERAL 4** (BSC_014/015/017/019), **PILOT_FOCUS 1** (BSC_120), **FAIL_CLOSED 7** (018/121 key-discovery + 031/071/072/073 needs-decision + 124 unparseable), **OBSERVE_ONLY 1** (025). Total 13.

---

## Task 1: Pure module skeleton + `parse_entry_detail`

**Files:**
- Create: `runner/altbasic_narrow.py`
- Test: `tests/test_altbasic_narrow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_altbasic_narrow.py
from __future__ import annotations
from runner import altbasic_narrow as N


def test_parse_single_press_key_strips_step_number():
    steps = N.parse_entry_detail("press_key:1. Recent App 버튼 누른다")
    assert len(steps) == 1
    assert steps[0].action == "press_key"
    assert steps[0].body == "Recent App 버튼 누른다"


def test_parse_multistep_split_on_gt():
    steps = N.parse_entry_detail("tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다")
    assert [s.action for s in steps] == ["tap", "press_key"]
    assert steps[1].body == "하드키 돌아가기 버튼 누른다"


def test_parse_bare_continuation_step_is_marked_bare():
    # 콜론-prefix 없는 연속 step → (bare), 추측 0
    steps = N.parse_entry_detail("press_key:Select box Dropdown 활성화 > 돌아가기 버튼 하드키 입력")
    assert steps[0].action == "press_key"
    assert steps[1].action == "(bare)"


def test_parse_unknown_prefix_is_marked_question():
    steps = N.parse_entry_detail("foobar:do something")
    assert steps[0].action == "?foobar"


def test_parse_empty_or_dash_returns_empty():
    assert N.parse_entry_detail("") == []
    assert N.parse_entry_detail("—") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_narrow.py -v`
Expected: FAIL (`ModuleNotFoundError: runner.altbasic_narrow` / `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# runner/altbasic_narrow.py
from __future__ import annotations
import re
from dataclasses import dataclass

STEP_SEP = ">"
_STEP_NUM_RE = re.compile(r"^\s*\d+\.\s*")
_PREFIX_RE = re.compile(r"^[a-zA-Z_]{2,20}$")
KNOWN_ACTIONS = frozenset({"press_key", "tap", "swipe", "launch_app", "launch",
                           "long_press", "input", "navigate", "wait"})


@dataclass(frozen=True)
class Step:
    action: str   # known action / "(bare)" / "?<prefix>"
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
            action = head if head in KNOWN_ACTIONS else f"?{head}"
            out.append(Step(action=action, body=body, raw=raw))
        else:
            out.append(Step(action="(bare)", body=_STEP_NUM_RE.sub("", raw), raw=raw))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_narrow.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Checkpoint** — tests GREEN. No commit (batch-deferred per policy header).

---

## Task 2: `KEY_DICT` + `resolve_keycode` (verified keys only, no guess)

**Files:**
- Modify: `runner/altbasic_narrow.py`
- Test: `tests/test_altbasic_narrow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_resolve_known_keys_to_candidate_keycodes():
    assert N.resolve_keycode("Recent App 버튼") == 187
    assert N.resolve_keycode("Home 버튼") == 3
    assert N.resolve_keycode("Camera 버튼") == 27
    assert N.resolve_keycode("Contact 버튼") == 207
    assert N.resolve_keycode("하드키 돌아가기 버튼") == 4


def test_resolve_unknown_or_no_standard_keycode_returns_none_no_guess():
    # Message / 지우기·취소 = 표준 keycode 부재 → None (추측 금지)
    assert N.resolve_keycode("Message 버튼") is None
    assert N.resolve_keycode("하드키 지우기/취소 버튼") is None
    # vague-nav / focus-prose → None
    assert N.resolve_keycode("홈화면에서 Navi Up/Down/Left/Right/OK 키 입력") is None
    assert N.resolve_keycode("wifi focus") is None
    assert N.resolve_keycode("숫자버튼 길게") is None


def test_resolve_trims_trailing_verbs():
    # body 가 동사 포함이어도 사전 키와 매칭
    assert N.resolve_keycode("Home 버튼 누른다") == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_narrow.py::test_resolve_known_keys_to_candidate_keycodes -v`
Expected: FAIL (`AttributeError: resolve_keycode`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_narrow.py
# 표준 Android keycode 후보가 존재하는 키만 (run1 device-verify 대상). 추측 0.
KEY_DICT = {
    "Recent App 버튼": 187,   # KEYCODE_APP_SWITCH
    "Home 버튼": 3,           # KEYCODE_HOME
    "Camera 버튼": 27,        # KEYCODE_CAMERA
    "Contact 버튼": 207,      # KEYCODE_CONTACTS
    "하드키 돌아가기 버튼": 4,  # KEYCODE_BACK
}
_TRAIL_VERBS = ("누른다", "누름", "입력한다", "입력", "누르기", "Tap", "탭")


def _norm_key(body: str) -> str:
    b = (body or "").strip()
    for tail in _TRAIL_VERBS:
        if b.endswith(tail):
            b = b[: -len(tail)].strip()
    return b


def resolve_keycode(key_name: str):
    """KEY_DICT 정확 매칭만. 미등록/표준 keycode 부재 = None (추측 금지)."""
    name = _norm_key(key_name)
    return KEY_DICT.get(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_narrow.py -v`
Expected: PASS (all Task 1+2 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 3: `literal_decision` (PASS / LITERAL_PENDING / ABSENT)

**Files:**
- Modify: `runner/altbasic_narrow.py`
- Test: `tests/test_altbasic_narrow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_literal_all_present_is_pass():
    assert N.literal_decision(["최근앱 리스트 화면"], "...최근앱 리스트 화면...") == N.LIT_PASS


def test_literal_partial_is_pending():
    # 다수 literal 중 일부만 노출 → PENDING (실측 채록 대상)
    assert N.literal_decision(["A", "B"], "...only A here...") == N.LIT_PENDING


def test_literal_none_present_is_absent():
    assert N.literal_decision(["홈스크린"], "completely different text") == N.LIT_ABSENT


def test_literal_empty_expected_is_absent_not_pass():
    # 기대 literal 부재는 PASS 로 위양성 만들지 않음
    assert N.literal_decision([], "anything") == N.LIT_ABSENT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_narrow.py -k literal -v`
Expected: FAIL (`AttributeError: literal_decision`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_narrow.py
LIT_PASS = "PASS"
LIT_PENDING = "LITERAL_PENDING"
LIT_ABSENT = "ABSENT"


def literal_decision(expected_literals, dump_text: str) -> str:
    exp = [e for e in (expected_literals or []) if e]
    if not exp:
        return LIT_ABSENT
    dump = dump_text or ""
    present = [e for e in exp if e in dump]
    if len(present) == len(exp):
        return LIT_PASS
    if present:
        return LIT_PENDING
    return LIT_ABSENT
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_narrow.py -k literal -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 4: `focus_retained_decision` (BSC_120/121 2-axis)

**Files:**
- Modify: `runner/altbasic_narrow.py`
- Test: `tests/test_altbasic_narrow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_focus_retained_both_axes_pass():
    assert N.focus_retained_decision(focus_retained=True, dropdown_absent=True) == N.SINGLE_RUN_PASS_TOKEN


def test_focus_retained_only_focus_axis_fails():
    # focus 유지하나 dropdown 잔존 = false-PASS 구멍 → VERIFIER_FAILED
    assert N.focus_retained_decision(focus_retained=True, dropdown_absent=False) == N.VERIFIER_FAILED


def test_focus_retained_only_dropdown_axis_fails():
    assert N.focus_retained_decision(focus_retained=False, dropdown_absent=True) == N.VERIFIER_FAILED


def test_focus_retained_neither_axis_fails():
    assert N.focus_retained_decision(focus_retained=False, dropdown_absent=False) == N.VERIFIER_FAILED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_narrow.py -k focus_retained -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_narrow.py (result-code constants)
SINGLE_RUN_PASS = "SINGLE_RUN_PASS"
RUN2_PASS = "RUN2_PASS"
TWO_RUN_GREEN = "TWO_RUN_GREEN"
LITERAL_PENDING = "LITERAL_PENDING"
VERIFIER_FAILED = "VERIFIER_FAILED"
ENTRY_FAILED = "ENTRY_FAILED"
UNSUPPORTED_ENTRY_DETAIL = "UNSUPPORTED_ENTRY_DETAIL"
OBSERVE_ONLY = "OBSERVE_ONLY"
DEVICE_FIT_SKIP = "DEVICE_FIT_SKIP"
CLEANUP_FAILED = "CLEANUP_FAILED"
INFRA_FAILURE = "INFRA_FAILURE"

# 내부 PASS 토큰 (run_no 미반영) — driver 가 run_no 로 SINGLE/RUN2 매핑
SINGLE_RUN_PASS_TOKEN = "PASS"


def focus_retained_decision(focus_retained: bool, dropdown_absent: bool) -> str:
    """2축: dropdown 닫힘 ∧ focus 유지 → PASS. 하나만 = VERIFIER_FAILED (단독 승격 금지)."""
    if focus_retained and dropdown_absent:
        return SINGLE_RUN_PASS_TOKEN
    return VERIFIER_FAILED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_narrow.py -k focus_retained -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 5: `classify_c01_disposition` (route 13 → 4 buckets)

**Files:**
- Modify: `runner/altbasic_narrow.py`
- Test: `tests/test_altbasic_narrow.py`

- [ ] **Step 1: Write the failing test**

```python
def _disp(tc, entry, verifier):
    return N.classify_c01_disposition(tc, entry, verifier)[0]


def test_classify_pilot_literal():
    assert _disp("ALTBASIC_BSC_014", "press_key:1. Recent App 버튼 누른다",
                 "literal: 최근앱 리스트 화면") == N.DISP_PILOT_LITERAL


def test_classify_pilot_focus():
    assert _disp("ALTBASIC_BSC_120", "tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다",
                 "[focus_retained] 포커스 유지 ; literal: 더보기") == N.DISP_PILOT_FOCUS


def test_classify_fail_closed_key_discovery():
    # Message / 지우기·취소 = 키 미상 → FAIL_CLOSED
    assert _disp("ALTBASIC_BSC_018", "press_key:1. Message 버튼 누른다",
                 "literal: 메시지 앱 실행 초기 화면") == N.DISP_FAIL_CLOSED


def test_classify_fail_closed_vague_nav():
    assert _disp("ALTBASIC_BSC_071", "press_key:1. 홈화면에서 Navi Up/Down/Left/Right/OK 키 입력한다",
                 "literal: 전화") == N.DISP_FAIL_CLOSED


def test_classify_fail_closed_bare_step():
    assert _disp("ALTBASIC_BSC_124", "press_key:Select box Dropdown 활성화 > 돌아가기 버튼 하드키 입력",
                 "[focus_absent] 포커스 사라짐") == N.DISP_FAIL_CLOSED


def test_classify_observe_only_elevated():
    assert _disp("ALTBASIC_BSC_025", "press_key:1. 종료 버튼 길게 누른다",
                 "literal: 전원 종료 팝업") == N.DISP_OBSERVE_ONLY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_narrow.py -k classify -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_narrow.py
DISP_PILOT_LITERAL = "PILOT_LITERAL"
DISP_PILOT_FOCUS = "PILOT_FOCUS"
DISP_FAIL_CLOSED = "FAIL_CLOSED"
DISP_OBSERVE_ONLY = "OBSERVE_ONLY"

# handoff §6 ELEVATED-CAUTION (C01 내 = BSC_025). 전 batch set 은 driver 에서 주입 가능.
ELEVATED_C01 = frozenset({"ALTBASIC_BSC_025"})


def _verifier_kind(vc: str) -> str:
    s = vc or ""
    if re.search(r"\[[^\]]+\]", s):
        return "focus_state"
    if re.search(r"literal\s*:", s, re.I):
        return "verify_text"
    return "UNKNOWN"


def classify_c01_disposition(tc_id: str, entry_detail: str, verifier_candidates: str):
    """(disposition, reason). no-guess: 미해석은 FAIL_CLOSED."""
    if tc_id in ELEVATED_C01:
        return DISP_OBSERVE_ONLY, "elevated-caution (§6 위험모달 observe-only)"
    steps = parse_entry_detail(entry_detail)
    vkind = _verifier_kind(verifier_candidates)
    if not steps:
        return DISP_FAIL_CLOSED, "entry_detail empty"
    # 미인식/연속 bare step 존재 → fail-closed
    if any(s.action == "(bare)" or s.action.startswith("?") for s in steps):
        return DISP_FAIL_CLOSED, "bare/unknown step (추측 금지)"
    # 전 press_key step 이 사전 키로 resolve 되는가
    press = [s for s in steps if s.action == "press_key"]
    taps = [s for s in steps if s.action == "tap"]
    others = [s for s in steps if s.action not in ("press_key", "tap")]
    if others:
        return DISP_FAIL_CLOSED, f"미지원 action {[s.action for s in others]}"
    unresolved = [s.body for s in press if resolve_keycode(s.body) is None]
    if unresolved:
        return DISP_FAIL_CLOSED, f"키 미상/미사전 (device key-discovery): {unresolved}"
    # 여기부터 전 press_key resolved
    if vkind == "focus_state":
        # tap(더보기)+key+focus 2축 → pilot-focus (BSC_120 류)
        return DISP_PILOT_FOCUS, "tap+key+focus 2축"
    if vkind == "verify_text" and not taps:
        return DISP_PILOT_LITERAL, "단일/순수 press_key + literal"
    if vkind == "verify_text" and taps:
        return DISP_FAIL_CLOSED, "tap-nav+literal (C01 pilot 범위 밖)"
    return DISP_FAIL_CLOSED, f"verifier kind={vkind}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_narrow.py -k classify -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 6: Device executor skeleton + `check_literal` glue (FakeDev)

**Files:**
- Create: `runner/altbasic_c01_driver.py`
- Test: `tests/test_altbasic_c01_driver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_altbasic_c01_driver.py
from __future__ import annotations
from runner import altbasic_c01_driver as D
from runner import altbasic_narrow as N


class FakeDev:
    def __init__(self, page_source: str):
        self._ps = page_source
        self.pressed = []          # keycodes sent (안전 가드 검증용)
        self.shots = []

    def src(self):
        return self._ps

    def evidence(self, tag):
        self.shots.append(tag)

    def home(self):
        pass


def test_check_literal_pass():
    dev = FakeDev("헤더 최근앱 리스트 화면 본문")
    code, note = D.check_literal(dev, ["최근앱 리스트 화면"])
    assert code == N.LIT_PASS


def test_check_literal_pending_records_actual_text():
    dev = FakeDev("실제 화면 텍스트 ABC")
    code, note = D.check_literal(dev, ["기대 literal 다름"])
    assert code == N.LIT_ABSENT
    assert "ABC" in note or "기대 literal 다름" in note  # 실측/기대 채록 (발명 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -v`
Expected: FAIL (`ModuleNotFoundError: runner.altbasic_c01_driver`).

- [ ] **Step 3: Write minimal implementation**

```python
# runner/altbasic_c01_driver.py
# -*- coding: utf-8 -*-
"""ALT Basic batch10 C01 narrow fail-closed pilot driver (F0 전용).

host-TDD: 순수 결정은 altbasic_narrow, 단말 I/O 는 b1.Dev. 본 파일은 device
2-run 전까지 import-safe 해야 한다 (appium import 는 실행 함수 내부에서만).
"""
from __future__ import annotations
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runner import altbasic_narrow as N   # noqa: E402


def check_literal(dev, expected_literals):
    """dev.src() dump 에 기대 literal 대조. (LIT_*, note). 발명 0 — 실측/기대 채록."""
    dump = dev.src() or ""
    code = N.literal_decision(expected_literals, dump)
    if code == N.LIT_PASS:
        return code, f"literal present: {expected_literals}"
    # PENDING/ABSENT: 실측 텍스트 일부 채록(발명 금지) — 짧게
    snippet = " ".join(dump.split())[:160]
    return code, f"expected={expected_literals} actual~={snippet!r}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 7: Observe-only (BSC_025) + Unsupported (BSC_124) guards — no execution

**Files:**
- Modify: `runner/altbasic_c01_driver.py`
- Test: `tests/test_altbasic_c01_driver.py`

- [ ] **Step 1: Write the failing test**

```python
def test_observe_only_does_not_press_power():
    dev = FakeDev("전원 종료 팝업 / 긴급전화 / 전원끄기")
    row = {"tc_id": "ALTBASIC_BSC_025",
           "entry_detail": "press_key:1. 종료 버튼 길게 누른다",
           "verifier_candidates": "literal: 전원 종료 팝업"}
    result, note = D.dispatch_dry(row)        # 순수 분기 — 단말 미접촉
    assert result == N.OBSERVE_ONLY
    assert dev.pressed == []                  # 위험 키 0


def test_unsupported_row_is_not_executed():
    row = {"tc_id": "ALTBASIC_BSC_124",
           "entry_detail": "press_key:Select box Dropdown 활성화 > 돌아가기 버튼 하드키 입력",
           "verifier_candidates": "[focus_absent] 포커스 사라짐"}
    result, note = D.dispatch_dry(row)
    assert result == N.UNSUPPORTED_ENTRY_DETAIL


def test_fail_closed_key_discovery_is_unsupported():
    row = {"tc_id": "ALTBASIC_BSC_018",
           "entry_detail": "press_key:1. Message 버튼 누른다",
           "verifier_candidates": "literal: 메시지 앱 실행 초기 화면"}
    result, note = D.dispatch_dry(row)
    assert result == N.UNSUPPORTED_ENTRY_DETAIL
    assert "device key-discovery" in note or "키 미상" in note
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -k "observe or unsupported or key_discovery" -v`
Expected: FAIL (`AttributeError: dispatch_dry`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_c01_driver.py
def dispatch_dry(row: dict):
    """단말 미접촉 분기 결정 — disposition → 예정 result code (실행 0).

    PILOT_* 는 'WOULD_RUN' 신호만 반환(실제 실행은 device 함수). 나머지는 최종 코드.
    """
    disp, reason = N.classify_c01_disposition(
        row.get("tc_id", ""), row.get("entry_detail", ""), row.get("verifier_candidates", ""))
    if disp == N.DISP_OBSERVE_ONLY:
        return N.OBSERVE_ONLY, reason
    if disp == N.DISP_FAIL_CLOSED:
        return N.UNSUPPORTED_ENTRY_DETAIL, reason
    return "WOULD_RUN", f"{disp}: {reason}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 8: classify-over-13 + dry-run selection counts

**Files:**
- Modify: `runner/altbasic_c01_driver.py`
- Test: `tests/test_altbasic_c01_driver.py`

- [ ] **Step 1: Write the failing test**

```python
# 13 C01 행 (tc_id, entry_detail, verifier_candidates) — manifest 실측 추출 (2026-06-26)
C01_ROWS = [
    ("ALTBASIC_BSC_014", "press_key:1. Recent App 버튼 누른다", "literal: 최근앱 리스트 화면"),
    ("ALTBASIC_BSC_015", "press_key:1. Home 버튼 누른다", "literal: 홈스크린"),
    ("ALTBASIC_BSC_017", "press_key:1. Contact 버튼 누른다", "literal: 연락처 앱 실행 초기 화면"),
    ("ALTBASIC_BSC_018", "press_key:1. Message 버튼 누른다", "literal: 메시지 앱 실행 초기 화면"),
    ("ALTBASIC_BSC_019", "press_key:1. Camera 버튼 누른다", "literal: 카메라 앱 실행 초기 화면"),
    ("ALTBASIC_BSC_025", "press_key:1. 종료 버튼 길게 누른다", "literal: 전원 종료 팝업"),
    ("ALTBASIC_BSC_031", "press_key:1. 숫자버튼 길게 입력한다", "literal: Quick Dialer 팝업"),
    ("ALTBASIC_BSC_071", "press_key:1. 홈화면에서 Navi Up/Down/Left/Right/OK 키 입력한다", "literal: 전화"),
    ("ALTBASIC_BSC_072", "press_key:1. 홈화면에서 Navi U/D/L/R/OK 키 입력한다 > press_key:2. Navi Up키 입력한다", "literal: 갤러리"),
    ("ALTBASIC_BSC_073", "press_key:1. 홈화면에서 Navi U/D/L/R/OK 키 입력한다 > press_key:2. Navi Down키 입력한다", "literal: 앱서랍"),
    ("ALTBASIC_BSC_120", "tap:1. 더보기 Tap > press_key:하드키 돌아가기 버튼 누른다", "[focus_retained] 유지 ; literal: 더보기"),
    ("ALTBASIC_BSC_121", "tap:1. 더보기 Tap > press_key:하드키 지우기/취소 버튼 누른다", "[focus_retained] 유지 ; literal: 더보기"),
    ("ALTBASIC_BSC_124", "press_key:Select box Dropdown 활성화 > 돌아가기 버튼 하드키 입력", "[focus_absent] 사라짐"),
]


def test_dry_run_selection_counts():
    rows = [{"tc_id": t, "entry_detail": e, "verifier_candidates": v} for (t, e, v) in C01_ROWS]
    counts = D.dry_run_counts(rows)
    assert counts[N.DISP_PILOT_LITERAL] == 4    # 014/015/017/019
    assert counts[N.DISP_PILOT_FOCUS] == 1      # 120
    assert counts[N.DISP_FAIL_CLOSED] == 7      # 018/121 키미상 + 031/071/072/073 + 124
    assert counts[N.DISP_OBSERVE_ONLY] == 1     # 025
    assert sum(counts.values()) == 13


def test_dry_run_specific_routing():
    rows = [{"tc_id": t, "entry_detail": e, "verifier_candidates": v} for (t, e, v) in C01_ROWS]
    table = D.dry_run_table(rows)
    routed = {r["tc_id"]: r["disposition"] for r in table}
    assert routed["ALTBASIC_BSC_014"] == N.DISP_PILOT_LITERAL
    assert routed["ALTBASIC_BSC_120"] == N.DISP_PILOT_FOCUS
    assert routed["ALTBASIC_BSC_018"] == N.DISP_FAIL_CLOSED
    assert routed["ALTBASIC_BSC_025"] == N.DISP_OBSERVE_ONLY
    assert routed["ALTBASIC_BSC_124"] == N.DISP_FAIL_CLOSED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -k dry_run -v`
Expected: FAIL (`AttributeError: dry_run_counts`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_c01_driver.py
from collections import Counter   # top of file


def dry_run_table(rows):
    out = []
    for row in rows:
        disp, reason = N.classify_c01_disposition(
            row.get("tc_id", ""), row.get("entry_detail", ""), row.get("verifier_candidates", ""))
        out.append({"tc_id": row.get("tc_id", ""), "disposition": disp, "reason": reason})
    return out


def dry_run_counts(rows):
    c = Counter(r["disposition"] for r in dry_run_table(rows))
    # 모든 disposition 키 보장
    for k in (N.DISP_PILOT_LITERAL, N.DISP_PILOT_FOCUS, N.DISP_FAIL_CLOSED, N.DISP_OBSERVE_ONLY):
        c.setdefault(k, 0)
    return dict(c)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -v`
Expected: PASS (all driver tests).

- [ ] **Step 5: Checkpoint** — GREEN. No commit.

---

## Task 9: Manifest loader + `--dry-run` CLI + STOP gate

**Files:**
- Modify: `runner/altbasic_c01_driver.py`
- Test: `tests/test_altbasic_c01_driver.py`

- [ ] **Step 1: Write the failing test** (loader over a tmp fixture CSV)

```python
import csv as _csv


def test_load_c01_rows_from_manifest(tmp_path):
    p = tmp_path / "m.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["tc_id", "source_sheet", "entry_detail", "verifier_candidates"])
        w.writerow(["ALTBASIC_BSC_014", "1.Basic principle", "press_key:1. Recent App 버튼 누른다", "literal: 최근앱 리스트 화면"])
        w.writerow(["ALTBASIC_MSG_999", "26.Message", "tap:1. 더보기", "literal: x"])
    rows = D.load_c01_rows(str(p))
    assert [r["tc_id"] for r in rows] == ["ALTBASIC_BSC_014"]   # C01 sheet 만
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c01_driver.py -k load_c01 -v`
Expected: FAIL (`AttributeError: load_c01_rows`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to runner/altbasic_c01_driver.py
import argparse   # top of file
import csv        # top of file

# tc-runner manifest (read-only, cross-repo). §2.5 — 실행코드만 thor2j.
DEFAULT_MANIFEST = os.path.join(
    _ROOT, "..", "tc-runner", "THOR2 - ALT Basic TC Audit",
    "handoff_device_validation", "VALIDATION_MANIFEST_BATCH10_2026-06-25.csv")


def load_c01_rows(manifest_path: str):
    rows = []
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if (r.get("source_sheet", "") or "").startswith("1.Basic principle"):
                rows.append(r)
    return rows


def _print_dry_run(manifest_path: str):
    rows = load_c01_rows(manifest_path)
    table = dry_run_table(rows)
    counts = dry_run_counts(rows)
    print(f"[C01 dry-run] manifest={manifest_path}  rows={len(rows)}")
    for r in table:
        print(f"  {r['tc_id']:20s} {r['disposition']:14s} {r['reason']}")
    print("counts:", counts)
    print("\n*** STOP: host-only. device 2-run 은 사용자 승인 후 별도 phase "
          "(helper 설치/F0 실행 0). ***")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    a = ap.parse_args()
    if a.dry_run:
        _print_dry_run(a.manifest)
        return
    print("device run 은 미구현 (STOP gate). --dry-run 만 지원.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes + full suite**

Run: `python -m pytest tests/test_altbasic_narrow.py tests/test_altbasic_c01_driver.py -v`
Expected: PASS (all narrow + driver tests GREEN).

- [ ] **Step 5: Produce the dry-run selection report (device-free)**

Run: `python runner/altbasic_c01_driver.py --dry-run`
Expected output: 13 C01 rows routed, `counts: {'PILOT_LITERAL': 4, 'PILOT_FOCUS': 1, 'FAIL_CLOSED': 7, 'OBSERVE_ONLY': 1}`, then the STOP banner.
Save the printed report into the tc-runner recovery doc draft (local-only) for the STOP report.

- [ ] **Step 6: ★ STOP — host complete.**
No device contact. Report to user: all host tests GREEN + dry-run counts. **Await user approval of spec/plan + explicit device-go** before the device phase (helper install, F0 run1/run2, keycode + dropdown device-verify). Do NOT proceed past this point autonomously.

---

## Self-Review (writing-plans)

**Spec coverage:** §1 pre-scan rationale → embodied in fail-closed design + dry-run counts (T8). §3 C01 routing → T5/T8. §5 BSC_120/121 2-axis → T4. §6 result codes + unsupported policy → T2/T3/T4/T7. §7 STOP → T9 Step 6. §4 architecture (pure + executor split, b1/fsnap reuse) → file structure + T1/T6. ✓ All covered.

**Placeholder scan:** No TBD/TODO. `<verify>` markers removed (Message/지우기·취소 now explicit FAIL_CLOSED, no candidate keycode). Every code step has full code. ✓

**Type consistency:** `Step(action,body,raw)`, `resolve_keycode`→int|None, `literal_decision`→LIT_*, `focus_retained_decision`→PASS-token/VERIFIER_FAILED, `classify_c01_disposition`→(DISP_*, reason), `dispatch_dry`/`dry_run_table`/`dry_run_counts`/`load_c01_rows` consistent across tasks. Counts 4+1+7+1=13. ✓

**Device boundary:** No task installs a helper or touches F0. `altbasic_c01_driver` import-safe (appium import deferred to unwritten device path). STOP at T9. ✓
