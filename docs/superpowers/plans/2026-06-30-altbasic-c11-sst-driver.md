# ALT Basic batch10 — C11 SST v1a driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** F0 간편모드 9.Simple settings 5건(SST_008/012/013/014/015)을 launch(홈 설정 tap)→tap-nav/press_key→literal 검증하는 첫 dispatch 러너 increment를 host-TDD로 빌드한다.

**Architecture:** 순수 결정 모듈 `altbasic_c11.py`(no-appium, host-test 전부) + device executor `altbasic_c11_driver.py`(appium lazy, import-safe). `altbasic_narrow`(parse/literal/result codes)·`altbasic_c01_driver`(device helper) **import-only 재사용**(fork 0). spec = `docs/superpowers/specs/2026-06-30-altbasic-c11-sst-driver-design.md`.

**Tech Stack:** Python 3, pytest(host, appium 불요), Appium/uiautomator2(device 2-run phase만). 코드 위치 = `thor2j-tc-appium/runner` + `tests` (§2.5 — tc-runner는 spec/plan/manifest/RESULT만).

---

## ⚠️ 실행 전제 (모든 task 공통)

- **commit 금지**: 글로벌 정책 — per-task commit 0. 전 task 산출물은 EOD batch에서 **명시 path만** stage(broad add 금지). 본 plan의 어떤 step도 `git commit` 하지 않는다.
- **thor2j dirty 격리**: 작업트리에 FocusRule 트랙 dirty 4파일(`docs/lessons_learned.md`·`docs/recovery_honesty.md`·`testcases/focusrule/focusrule_tc_catalog.yaml`·`tests/test_recovery_feasibility_audit.py`) 존재 — **무수정**. 신규 3파일만 생성. 테스트는 신규 test 파일만 스코프 실행.
- **device 0**: Task 1~4 전부 host-only. **F0 2-run은 본 plan 밖**(build green + F0 단독연결 확인 + 사용자 승인 후 별도 phase).
- 작업 디렉토리 = `C:\Users\momen\Projects\thor2j-tc-appium`. pytest 실행도 이 repo root.

## File Structure

| 파일 | 책임 |
|---|---|
| Create `runner/altbasic_c11.py` | 순수 결정 — C11 키사전, `parse_sst_entry`, `normalize_action_step`, `classify_sst`. appium 0. |
| Create `runner/altbasic_c11_driver.py` | device executor — manifest 로드, dry-run, `_ensure_awake`, `_run_sst`, `run_pilot`. b1은 run 경로 lazy import(import-safe). |
| Create `tests/test_altbasic_c11.py` | host-test — pure 모듈 전수 + driver import-safety/dry-run. SST 5행 verbatim golden. |

---

## Task 1: 순수 모듈 `altbasic_c11.py` — parse/normalize/classify

**Files:**
- Create: `runner/altbasic_c11.py`
- Test: `tests/test_altbasic_c11.py`

- [ ] **Step 1: Write the failing test (5행 verbatim golden + classify)**

`tests/test_altbasic_c11.py`:
```python
# -*- coding: utf-8 -*-
"""host-TDD for altbasic_c11 (C11 SST v1a). appium 불요."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runner import altbasic_c11 as C   # noqa: E402

# 실제 manifest VALIDATION_MANIFEST_BATCH10_2026-06-25.csv 행 verbatim (entry_detail, verifier_candidates)
SST_ROWS = {
    "ALTBASIC_SST_008": ("press_key:쉬운 설정 > Press 방향키 or OK", "literal: 소리 및 진동"),
    "ALTBASIC_SST_012": ("tap:방향키로 Simple setting > WiFi tap", "literal: 네트워크 및 인터넷 / WiFi"),
    "ALTBASIC_SST_013": ("tap:방향키로 Simple setting > 배경화면 및 스타일 tap", "literal: 테마 및 배경화면"),
    "ALTBASIC_SST_014": ("tap:방향키로 Simple setting > 디스플레이 tap", "literal: 디스플레이"),
    "ALTBASIC_SST_015": ("tap:방향키로 Simple setting > 안심기능 tap", "literal: 안심기능"),
}


def test_parse_launch_recognized_both_prefixes():
    # SST_008 launch step = press_key prefix, SST_012 = tap prefix — 둘 다 launch 인정
    launch8, act8 = C.parse_sst_entry(SST_ROWS["ALTBASIC_SST_008"][0])
    launch12, act12 = C.parse_sst_entry(SST_ROWS["ALTBASIC_SST_012"][0])
    assert launch8 is not None and len(act8) == 1
    assert launch12 is not None and len(act12) == 1


def test_normalize_tapnav_strips_trailing_tap():
    _, act = C.parse_sst_entry(SST_ROWS["ALTBASIC_SST_014"][0])
    kind, payload = C.normalize_action_step(act[0])
    assert kind == C.ACT_TAP and payload == "디스플레이"


def test_normalize_key_ok_candidate():
    _, act = C.parse_sst_entry(SST_ROWS["ALTBASIC_SST_008"][0])
    kind, payload = C.normalize_action_step(act[0])
    assert kind == C.ACT_KEY and payload == C.OK_KEYCODE


def test_classify_sst_dispositions():
    got = {tc: C.classify_sst(tc, ed, vc)[0] for tc, (ed, vc) in SST_ROWS.items()}
    assert got == {
        "ALTBASIC_SST_008": C.SST_KEY,
        "ALTBASIC_SST_012": C.SST_TAPNAV,
        "ALTBASIC_SST_013": C.SST_TAPNAV,
        "ALTBASIC_SST_014": C.SST_TAPNAV,
        "ALTBASIC_SST_015": C.SST_TAPNAV,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: FAIL — `ModuleNotFoundError: runner.altbasic_c11` (모듈 미존재).

- [ ] **Step 3: Write `runner/altbasic_c11.py`**

```python
# -*- coding: utf-8 -*-
"""ALT Basic batch10 — C11 SST (9.Simple settings) v1a 순수 결정 (no Appium / no device).

spec: tc-runner/docs/superpowers/specs/2026-06-30-altbasic-c11-sst-driver-design.md

원칙: no-guess / fail-closed. launch = 홈 '설정' tap(쉬운설정), action = tap-nav(label) 또는
press_key OK candidate(run1 device-verify). altbasic_narrow **import-only**(fork 0). host-TDD 대상.
"""
from __future__ import annotations

import re

from runner import altbasic_narrow as N

# ── key candidates (run1 device-verify; no-guess for unmapped) ──
OK_KEYCODE = 23           # KEYCODE_DPAD_CENTER (OK candidate)
DPAD_CANDIDATES = {"up": 19, "down": 20, "left": 21, "right": 22, "ok": 23, "center": 23}
C11_KEY_DICT = dict(N.KEY_DICT)   # 하드웨어키 사전 재사용 (DPAD/OK는 normalize 경유)

# ── dispositions ──
SST_TAPNAV = "SST_TAPNAV"
SST_KEY = "SST_KEY"
FAIL_CLOSED = N.DISP_FAIL_CLOSED   # "FAIL_CLOSED"

# ── action kinds ──
ACT_TAP = "tap"
ACT_KEY = "press_key"

_LAUNCH_MARKERS = ("쉬운 설정", "simple setting")
_OK_RE = re.compile(r"\bOK\b", re.I)


def is_launch_step(step) -> bool:
    body = (step.body or "")
    low = body.lower()
    return ("쉬운 설정" in body) or ("simple setting" in low)


def normalize_action_step(step):
    """bare/action step → (kind, payload). 미해석 → (None, raw_body).

    '<label> tap' → (ACT_TAP, label). '방향키'/'OK' 포함 → (ACT_KEY, OK_KEYCODE).
    """
    body = (step.body or "").strip()
    if ("방향키" in body) or _OK_RE.search(body):
        return ACT_KEY, OK_KEYCODE
    if body.endswith("tap"):
        label = body[:-3].strip()
        if label:
            return ACT_TAP, label
    if step.action == "tap" and body:
        return ACT_TAP, body
    return None, body


def parse_sst_entry(entry_detail):
    """(launch_step or None, [action_step, ...]). launch = 첫 step body가 쉬운설정/Simple setting."""
    steps = N.parse_entry_detail(entry_detail)
    if not steps:
        return None, []
    if is_launch_step(steps[0]):
        return steps[0], steps[1:]
    return None, steps


def classify_sst(tc_id, entry_detail, verifier_candidates):
    """(disposition, detail). no-guess — launch 미인식·verifier 비-verify_text·action 미정규화 → FAIL_CLOSED."""
    launch, actions = parse_sst_entry(entry_detail)
    if launch is None:
        return FAIL_CLOSED, "launch 미인식 (쉬운 설정/Simple setting 부재)"
    if N._verifier_kind(verifier_candidates) != "verify_text":
        return FAIL_CLOSED, "verifier 비 verify_text"
    if len(actions) != 1:
        return FAIL_CLOSED, f"action step != 1 ({len(actions)})"
    kind, payload = normalize_action_step(actions[0])
    if kind == ACT_TAP:
        return SST_TAPNAV, f"tap label={payload!r}"
    if kind == ACT_KEY:
        return SST_KEY, f"press_key OK(candidate {payload}, run1-verify)"
    return FAIL_CLOSED, f"action 미정규화: {actions[0].raw!r}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit** — **SKIP (글로벌 정책: per-task commit 금지, EOD batch defer).**

---

## Task 2: 순수 모듈 edge/fail-closed + literal 재사용 테스트

**Files:**
- Modify: `tests/test_altbasic_c11.py` (append)

- [ ] **Step 1: Write failing tests (fail-closed + literal all-of)**

`tests/test_altbasic_c11.py` 끝에 추가:
```python
from runner import altbasic_narrow as N   # noqa: E402


def test_classify_fail_closed_no_launch():
    # launch 마커 없음 → FAIL_CLOSED
    disp, _ = C.classify_sst("X", "tap:어딘가 > 디스플레이 tap", "literal: 디스플레이")
    assert disp == C.FAIL_CLOSED


def test_classify_fail_closed_non_verify_text():
    # verifier가 focus_state([assert]) → FAIL_CLOSED (C11 SST v1a는 verify_text만)
    disp, _ = C.classify_sst("X", "tap:쉬운 설정 > 디스플레이 tap", "[focus_move] 디스플레이")
    assert disp == C.FAIL_CLOSED


def test_classify_fail_closed_empty():
    disp, _ = C.classify_sst("X", "—", "literal: x")
    assert disp == C.FAIL_CLOSED


def test_literal_all_of_multi_present():
    # SST_012 = 2 literal all-of. N.literal_decision 재사용.
    exp = ["네트워크 및 인터넷", "WiFi"]
    assert N.literal_decision(exp, "<x text='네트워크 및 인터넷'/><y text='WiFi'/>") == N.LIT_PASS
    assert N.literal_decision(exp, "<x text='네트워크 및 인터넷'/>") == N.LIT_PENDING
    assert N.literal_decision(exp, "<x text='없음'/>") == N.LIT_ABSENT
```

- [ ] **Step 2: Run test to verify it fails (or passes if logic already correct)**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: 신규 4 테스트 PASS (Task 1 구현이 이미 커버 — fail-closed 분기·literal 재사용 검증). 만약 `test_classify_fail_closed_non_verify_text`가 FAIL이면 `N._verifier_kind` 분기 점검 후 수정.

- [ ] **Step 3: (구현 변경 필요 시) `altbasic_c11.py` 보정** — Task 1 분기로 충분하면 변경 0.

- [ ] **Step 4: Run test to verify all pass**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: 전체 PASS (8 tests).

- [ ] **Step 5: Commit** — **SKIP (EOD defer).**

---

## Task 3: device executor `altbasic_c11_driver.py` + import-safety

**Files:**
- Create: `runner/altbasic_c11_driver.py`
- Modify: `tests/test_altbasic_c11.py` (append import-safety + dry-run test)

- [ ] **Step 1: Write failing test (import-safety + dry-run classify)**

`tests/test_altbasic_c11.py` 끝에 추가:
```python
def test_driver_import_safe_no_appium():
    # b1(appium)은 run 경로 lazy import — driver import 시 altbasic_validation_batch1 미로드
    sys.modules.pop("altbasic_validation_batch1", None)
    from runner import altbasic_c11_driver as D   # noqa: F401
    assert "altbasic_validation_batch1" not in sys.modules
    assert hasattr(D, "run_pilot") and hasattr(D, "main")


def test_driver_dry_run_table():
    from runner import altbasic_c11_driver as D
    rows = [{"tc_id": tc, "entry_detail": ed, "verifier_candidates": vc}
            for tc, (ed, vc) in SST_ROWS.items()]
    table = {r["tc_id"]: r["disposition"] for r in D.dry_run_table(rows)}
    assert table["ALTBASIC_SST_008"] == C.SST_KEY
    assert all(table[t] == C.SST_TAPNAV for t in
               ("ALTBASIC_SST_012", "ALTBASIC_SST_013", "ALTBASIC_SST_014", "ALTBASIC_SST_015"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_altbasic_c11.py::test_driver_import_safe_no_appium -v`
Expected: FAIL — `ModuleNotFoundError: runner.altbasic_c11_driver`.

- [ ] **Step 3: Write `runner/altbasic_c11_driver.py`**

```python
# -*- coding: utf-8 -*-
"""ALT Basic batch10 — C11 SST v1a device executor (F0 전용).

spec:  tc-runner/docs/superpowers/specs/2026-06-30-altbasic-c11-sst-driver-design.md
plan:  tc-runner/docs/superpowers/plans/2026-06-30-altbasic-c11-sst-driver.md

import-safe until --run: appium(b1)은 run_pilot 내부에서만 lazy import.
순수결정 = altbasic_c11, device helper(check_literal/_literals) = altbasic_c01_driver 재사용(fork 0).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runner import altbasic_narrow as N            # pure
from runner import altbasic_c11 as C               # pure
from runner import altbasic_c01_driver as C01      # device helper (import-safe: appium도 C01 lazy)

DEFAULT_MANIFEST = os.path.join(
    _ROOT, "..", "tc-runner", "THOR2 - ALT Basic TC Audit",
    "handoff_device_validation", "VALIDATION_MANIFEST_BATCH10_2026-06-25.csv")

PINNED_UDID = "B06201249E0002F0"     # F0 only — wrong-device 가드
LAUNCH_TILE = "설정"                  # 간편모드 홈 설정 타일 → 쉬운설정 (run1 진입경로 확정)
EV_REL = ("evidence", "altbasic_batch10_c11sst_20260630")
SST_V1A = {"ALTBASIC_SST_008", "ALTBASIC_SST_012", "ALTBASIC_SST_013",
           "ALTBASIC_SST_014", "ALTBASIC_SST_015"}


def load_sst_rows(manifest_path):
    rows = []
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("tc_id", "") in SST_V1A:
                rows.append(r)
    return rows


def dry_run_table(rows):
    out = []
    for row in rows:
        disp, reason = C.classify_sst(
            row.get("tc_id", ""), row.get("entry_detail", ""), row.get("verifier_candidates", ""))
        out.append({"tc_id": row.get("tc_id", ""), "disposition": disp, "reason": reason})
    return out


def _print_dry_run(manifest_path):
    rows = load_sst_rows(manifest_path)
    print(f"[C11 SST dry-run] manifest={manifest_path} rows={len(rows)}")
    for r in dry_run_table(rows):
        print(f"  {r['tc_id']:20s} {r['disposition']:12s} {r['reason']}")
    print("\n*** STOP: host-only. device 2-run 은 F0 단독연결 + 사용자 승인 후 별도 phase. ***")


# ── device path (b1/appium은 run_pilot 안에서만) ──
def _ensure_awake(v):
    """b1 무수정·v.wake() 없음 → WAKEUP + sanity dump (실측: screen-off면 dump null)."""
    v.d.press_keycode(224)   # KEYCODE_WAKEUP
    time.sleep(1.0)
    return v.src()


def _run_sst(v, row):
    """launch(홈 설정 tap) → action(tap label | press_key OK) → literal 대조 → Back/HOME. NAVIGATION_ONLY."""
    tc = row.get("tc_id", "")
    disp, reason = C.classify_sst(tc, row.get("entry_detail", ""), row.get("verifier_candidates", ""))
    if disp == C.FAIL_CLOSED:
        v.home()
        return N.UNSUPPORTED_ENTRY_DETAIL, reason
    _, actions = C.parse_sst_entry(row.get("entry_detail", ""))
    kind, payload = C.normalize_action_step(actions[0])
    expected = C01._literals(row.get("verifier_candidates", ""))

    _ensure_awake(v)
    v.home()
    v.evidence("home")
    if not v.tap_text(LAUNCH_TILE, partial=True):
        v.home()
        return N.ENTRY_FAILED, f"launch tap {LAUNCH_TILE!r} 실패 (홈 설정 타일 미발견)"
    time.sleep(1.2)
    v.evidence("settings")

    if kind == C.ACT_TAP:
        if not v.tap_text(payload, partial=True):
            v.home()
            return N.ENTRY_FAILED, f"menu tap {payload!r} 실패 (미발견/스크롤 필요?)"
    elif kind == C.ACT_KEY:
        v.d.press_keycode(payload)   # OK candidate (run1 device-verify)
    else:
        v.home()
        return N.UNSUPPORTED_ENTRY_DETAIL, f"action 미정규화 {actions[0].raw!r}"
    time.sleep(1.2)
    v.evidence("after")

    code, note = C01.check_literal(v, expected)
    v.d.press_keycode(4)   # BACK — 설정 root 복귀
    time.sleep(0.8)
    v.home()
    if code == N.LIT_PASS:
        return "PASS", f"literal present {expected}"
    if code == N.LIT_PENDING:
        return N.LITERAL_PENDING, note
    return N.VERIFIER_FAILED, note   # LIT_ABSENT


def run_pilot(run_no: int, manifest_path: str, only=None):
    import altbasic_validation_batch1 as b1   # appium (lazy)
    if b1.UDID != PINNED_UDID:
        print(f"!! WRONG UDID {b1.UDID} != {PINNED_UDID} — ABORT (wrong-device 가드)")
        return
    b1.EV_BASE = os.path.join(b1.REPO, *EV_REL)
    rows = load_sst_rows(manifest_path)
    if only:
        sel = {x.replace("ALTBASIC_", "") for x in only}
        rows = [r for r in rows if r.get("tc_id", "").replace("ALTBASIC_", "") in sel]
    print(f"[c11sst run{run_no}] EV_BASE={b1.EV_BASE} UDID={b1.UDID} rows={len(rows)}")
    for row in rows:
        b1.run_one(row.get("tc_id", ""), (lambda r: lambda v: _run_sst(v, r))(row), run_no)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", type=int)            # 1 또는 2
    ap.add_argument("--only")                      # comma tc list
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    a = ap.parse_args()
    if a.dry_run:
        _print_dry_run(a.manifest)
        return
    if a.run in (1, 2):
        only = [x.strip() for x in a.only.split(",")] if a.only else None
        run_pilot(a.run, a.manifest, only)
        return
    print("usage: --dry-run | --run {1,2} [--only SST_012,...]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: 전체 PASS (10 tests). import-safety 통과(appium 미로드).

- [ ] **Step 5: Commit** — **SKIP (EOD defer).**

---

## Task 4: 실 manifest dry-run 검증 (host, device 0)

**Files:** (코드 변경 없음 — CLI 실측)

- [ ] **Step 1: Run dry-run against real manifest**

Run: `python -m runner.altbasic_c11_driver --dry-run`
Expected 출력:
```
[C11 SST dry-run] manifest=...VALIDATION_MANIFEST_BATCH10_2026-06-25.csv rows=5
  ALTBASIC_SST_008     SST_KEY      press_key OK(candidate 23, run1-verify)
  ALTBASIC_SST_012     SST_TAPNAV   tap label='WiFi'
  ALTBASIC_SST_013     SST_TAPNAV   tap label='배경화면 및 스타일'
  ALTBASIC_SST_014     SST_TAPNAV   tap label='디스플레이'
  ALTBASIC_SST_015     SST_TAPNAV   tap label='안심기능'
*** STOP: host-only. ...
```
검증: rows=5, SST_KEY×1 + SST_TAPNAV×4, FAIL_CLOSED 0. 불일치 시 manifest 행/정규화 재점검.

- [ ] **Step 2: 전체 신규 test 스위트 green 확인**

Run: `python -m pytest tests/test_altbasic_c11.py -v`
Expected: 10 passed. (FocusRule dirty test와 격리 — 신규 파일만 스코프.)

- [ ] **Step 3: STOP — device handoff gate**

host build green. 다음(본 plan 밖):
1. thor2j dirty 4파일 known 확인(사용자).
2. `adb -s B06201249E0002F0 get-state` = F0 단독연결 재확인(wrong-device 가드).
3. **사용자 승인 후** `python -m runner.altbasic_c11_driver --run 1` → `--run 2` 2-run.
4. 회수 = tc-runner `RESULT_RECOVERY_BATCH10_C11SST_2026-06-30.md`(RUNNABLE/LITERAL_PENDING/ENTRY_FAILED 분리).

---

## Self-Review

- **Spec coverage**: §3 pure 모듈(C11_KEY_DICT/parse_sst_entry/normalize/classify) → Task 1·2. §3 device executor(b1 lazy·_ensure_awake·check_literal 재사용·PINNED_UDID) → Task 3. §4 per-TC flow → `_run_sst`. §7 host-TDD(parse/classify/literal/import-safe) → Task 1~3. §6 dry-run/2-run → Task 4 + handoff. §5 안전(NAVIGATION_ONLY·Back/HOME) → `_run_sst`. ✓ gap 0.
- **Placeholder scan**: 코드 완전(TBD/TODO 0). evidence runtag = `20260630` 고정(placeholder 아님).
- **Type consistency**: `C.SST_KEY`/`C.SST_TAPNAV`/`C.FAIL_CLOSED`/`C.ACT_TAP`/`C.ACT_KEY`/`C.OK_KEYCODE` — Task 1 정의 ↔ Task 2/3 사용 일치. `C01._literals`/`C01.check_literal` = 기존 시그니처(driver Read 확인). `N.literal_decision`/`N.LIT_*`/`N.DISP_FAIL_CLOSED`/`N._verifier_kind`/`N.parse_entry_detail` = altbasic_narrow 실존. ✓
- **commit**: 전 task Step 5 = SKIP(EOD). per-task commit 0 확인. ✓
