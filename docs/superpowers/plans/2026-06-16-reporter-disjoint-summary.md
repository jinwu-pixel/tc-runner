# Reporter disjoint summary fix + qa-suite 이주 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Reporter.get_summary()` 의 비배타 집계 버그(한 TC 의 fail 이 skipped 에 먹혀 `failed=0`)를 TC 레벨 disjoint 분류로 고치고, 정정된 reporter 를 qa-suite `automation/tc_step` 로 이주한다.

**Architecture:** `TCResult.status`(passed|failed|skipped, 우선순위 fail>skip>pass) 프로퍼티를 단일 진실원천으로 추가하고 `get_summary()` 를 status 카운트로 재작성(파생 `total-passed-skipped` 제거). tc-runner 소스를 먼저 TDD 로 고쳐 commit 한 뒤, 정정본을 qa-suite 로 import-transform 이주.

**Tech Stack:** Python 3.12, pytest, jinja2(reporter HTML). 실행기 = `C:/Users/momen/Projects/tc-runner/venv/Scripts/python.exe`.

**설계문서:** `docs/superpowers/specs/2026-06-16-reporter-disjoint-summary-design.md`

**운영 제약(사용자 lock):** 양 repo **push 금지**. **commit 은 단계별 보고 후 별도 승인** — 본 플랜의 commit 스텝은 "승인 대기"이며 무단 실행 금지. spec+plan 문서는 Part 1 tc-runner commit 에 번들. jinja2 dependency manifest 는 후속 티켓(이번 slice requirements 생성 X).

---

## File Structure

**Part 1 — tc-runner (정합성 fix)**
- Modify: `src/reporter.py` — `TCResult.status` 프로퍼티 추가 + `get_summary()` 재작성
- Modify: `tests/test_reporter.py` — 신규 status/invariant/fail+skip RED 테스트 + bundle fixture 정렬
- Bundle(문서): `docs/superpowers/specs/2026-06-16-reporter-disjoint-summary-design.md` + `docs/superpowers/plans/2026-06-16-reporter-disjoint-summary.md`

**Part 2 — qa-suite (이주)**
- Create: `automation/tc_step/reporter.py` (정정본 + import/template transform)
- Create: `automation/tc_step/templates/report.html` (verbatim from tc-runner `templates/report.html`)
- Create: `automation/tc_step/tests/test_reporter.py` (정정본 + import transform)
- Modify: `campaigns/manifests/provenance.csv` (+3행)
- Modify: `MIGRATION.md` (§4.2-11)

---

## Part 1 — tc-runner reporter fix (TDD)

### Task 1: 실패 테스트 작성 (RED)

**Files:**
- Modify: `tests/test_reporter.py`

- [ ] **Step 1: 신규 status / invariant / fail+skip 테스트를 `tests/test_reporter.py` 끝에 추가**

```python
# ─── disjoint status 분류 (fail > skip > pass) ───

def test_tc_status_skip_only():
    tc = TCResult(name="skip", description="", steps=[
        StepResult(action="manual_step", passed=False, duration=0.0,
                   manual_action="skip", skip_reason="no device"),
    ])
    assert tc.status == "skipped"


def test_tc_status_fail_only():
    tc = TCResult(name="fail", description="", steps=[
        StepResult(action="verify_text", passed=False, duration=0.1),
    ])
    assert tc.status == "failed"


def test_tc_status_pass_only():
    tc = TCResult(name="pass", description="", steps=[
        StepResult(action="wait", passed=True, duration=0.1),
    ])
    assert tc.status == "passed"


def test_tc_status_fail_and_skip_is_failed():
    """fail step + skip step 동시 → failed (skip 이 fail 을 가리지 않음)."""
    tc = TCResult(name="failskip", description="", steps=[
        StepResult(action="verify_text", passed=False, duration=0.1),
        StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip"),
    ])
    assert tc.status == "failed"


def test_get_summary_fail_plus_skip_in_one_tc():
    """핵심 RED: 한 TC 의 fail 이 skipped 에 먹혀 failed=0 이 되면 안 된다."""
    reporter = Reporter(report_dir=Path("/tmp"))
    reporter.results = [
        TCResult(name="TC_C", description="", steps=[
            StepResult(action="verify_text", passed=False, duration=0.1),
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip"),
        ]),
    ]
    assert reporter.get_summary() == {"total": 1, "passed": 0, "skipped": 0, "failed": 1}


def test_get_summary_disjoint_invariant():
    """passed + failed + skipped == total, 각 TC 정확히 한 버킷."""
    reporter = Reporter(report_dir=Path("/tmp"))
    reporter.results = [
        TCResult(name="p", description="", steps=[
            StepResult(action="wait", passed=True, duration=0.1)]),
        TCResult(name="f", description="", steps=[
            StepResult(action="verify", passed=False, duration=0.1)]),
        TCResult(name="s", description="", steps=[
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip")]),
        TCResult(name="fs", description="", steps=[
            StepResult(action="verify", passed=False, duration=0.1),
            StepResult(action="manual_step", passed=False, duration=0.0, manual_action="skip")]),
    ]
    s = reporter.get_summary()
    assert s["passed"] + s["failed"] + s["skipped"] == s["total"]
    assert s == {"total": 4, "passed": 1, "skipped": 1, "failed": 2}
```

- [ ] **Step 2: bundle 테스트 fixture 를 실 계약(skip `passed=False`)으로 정렬 + 기대 summary 정정**

`tests/test_reporter.py::test_reporter_bundle_mode_summary_json_shape` 안에서:

TC_B 의 skip step `passed=True` → `passed=False`:
```python
        TCResult(name="TC_B", description="beta", steps=[
            StepResult(
                action="manual_step",
                passed=False,
                duration=0.0,
                manual_action="skip",
                skip_reason="user requested",
            ),
        ]),
```

기대 summary (현 `{"total": 2, "passed": 1, "skipped": 1, "failed": 0}`):
```python
    assert data["summary"] == {"total": 2, "passed": 0, "skipped": 1, "failed": 1}
```
(이 단언은 실 계약 하 현 코드도 통과 = 회귀 잠금이지 RED 아님. RED 는 위 `test_get_summary_fail_plus_skip_in_one_tc` 와 status 테스트가 담당.)

- [ ] **Step 3: 테스트 실행 → RED 확인**

Run: `venv/Scripts/python.exe -m pytest tests/test_reporter.py -v`
Expected: FAIL —
- `test_tc_status_*` 4건 → `AttributeError: 'TCResult' object has no attribute 'status'`
- `test_get_summary_fail_plus_skip_in_one_tc` → AssertionError (현=`{...skipped:1, failed:0}`)
- `test_get_summary_disjoint_invariant` → AssertionError (현=`{...skipped:2, failed:1}`)
- bundle 테스트 → PASS (회귀 잠금)

### Task 2: 구현 (GREEN)

**Files:**
- Modify: `src/reporter.py`

- [ ] **Step 4: `TCResult` 에 `status` 프로퍼티 추가**

`src/reporter.py` 의 `TCResult` 데이터클래스에 `is_pass` 프로퍼티 다음에 추가:
```python
    @property
    def status(self) -> str:
        has_failed = any(
            (not s.passed) and getattr(s, "manual_action", "") != "skip"
            for s in self.steps
        )
        if has_failed:
            return "failed"
        if any(getattr(s, "manual_action", "") == "skip" for s in self.steps):
            return "skipped"
        return "passed"
```

- [ ] **Step 5: `get_summary()` 를 status 카운트로 재작성**

`src/reporter.py` `Reporter.get_summary()` (현 line 88-96) 전체 교체:
```python
    def get_summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        return {"total": total, "passed": passed, "skipped": skipped, "failed": failed}
```

- [ ] **Step 6: 타겟 테스트 실행 → GREEN 확인**

Run: `venv/Scripts/python.exe -m pytest tests/test_reporter.py -v`
Expected: PASS (전건)

- [ ] **Step 7: tc-runner 전체 suite 회귀 확인**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: PASS (회귀 0). 특히 `test_failure_reason`·`test_action_runner` 무영향.

- [ ] **Step 8: commit (★사용자 승인 대기 — 무단 실행 금지)**

보고 후 승인 시 명시 path 만 stage:
```bash
git add src/reporter.py tests/test_reporter.py \
  docs/superpowers/specs/2026-06-16-reporter-disjoint-summary-design.md \
  docs/superpowers/plans/2026-06-16-reporter-disjoint-summary.md
git commit -m "fix(reporter): disjoint TC summary 집계 (fail>skip>pass) + 설계/플랜"
```
(tc-runner ahead 5 → +1. push 안 함.)

---

## Part 2 — qa-suite reporter 슬라이스 이주

작업 repo = `C:/Users/momen/Projects/qa-suite`. 실행기는 tc-runner venv 사용.

### Task 3: reporter 모듈 + 템플릿 이주

**Files:**
- Create: `automation/tc_step/reporter.py`
- Create: `automation/tc_step/templates/report.html`

- [ ] **Step 1: 정정된 reporter.py 를 verbatim 복사 (이후 import/template transform)**

```bash
cp "C:/Users/momen/Projects/tc-runner/src/reporter.py" \
   "C:/Users/momen/Projects/qa-suite/automation/tc_step/reporter.py"
```

- [ ] **Step 2: import 2줄 + template 경로 transform (qa-suite `automation/tc_step/reporter.py`)**

- `from src.action_runner import StepResult` → `from .action_runner import StepResult`
- `from src.catalog_delta import validate_run_id_for_filename` → `from learning.engine.catalog_delta import validate_run_id_for_filename`
- `template_dir = Path(__file__).parent.parent / "templates"` → `template_dir = Path(__file__).parent / "templates"`

(나머지 — `DEFAULT_TEMPLATE` 내장 fallback 포함 — 무변경.)

- [ ] **Step 3: report.html 템플릿 verbatim 복사**

```bash
mkdir -p "C:/Users/momen/Projects/qa-suite/automation/tc_step/templates"
cp "C:/Users/momen/Projects/tc-runner/templates/report.html" \
   "C:/Users/momen/Projects/qa-suite/automation/tc_step/templates/report.html"
```

### Task 4: 테스트 이주

**Files:**
- Create: `automation/tc_step/tests/test_reporter.py`

- [ ] **Step 4: 정정된 test_reporter.py 복사 후 import transform**

```bash
cp "C:/Users/momen/Projects/tc-runner/tests/test_reporter.py" \
   "C:/Users/momen/Projects/qa-suite/automation/tc_step/tests/test_reporter.py"
```
qa-suite `automation/tc_step/tests/test_reporter.py` 에서:
- `from src.reporter import (` → `from automation.tc_step.reporter import (`
- `from src.action_runner import StepResult` → `from automation.tc_step.action_runner import StepResult`

### Task 5: 검증

- [ ] **Step 5: 타겟 reporter 테스트**

Run: `cd "C:/Users/momen/Projects/qa-suite" && "C:/Users/momen/Projects/tc-runner/venv/Scripts/python.exe" -m pytest automation/tc_step/tests/test_reporter.py -v`
Expected: PASS (전건 — status·invariant·bundle 포함)

- [ ] **Step 6: qa-suite 전체 suite + 교차 import 런타임 스모크**

Run:
```bash
cd "C:/Users/momen/Projects/qa-suite"
PY="C:/Users/momen/Projects/tc-runner/venv/Scripts/python.exe"
"$PY" -m pytest -q
"$PY" -c "from automation.tc_step.reporter import Reporter, TCResult; from learning.engine.catalog_delta import validate_run_id_for_filename; print('cross-track import OK')"
```
Expected: 전체 PASS (530 + reporter 테스트, 회귀 0) · `cross-track import OK`

### Task 6: provenance + MIGRATION 기록

**Files:**
- Modify: `campaigns/manifests/provenance.csv`
- Modify: `MIGRATION.md`

- [ ] **Step 7: provenance 3행 추가 (sha 는 실제 계산값으로 — git blob 기준)**

기존 마지막 행 뒤에 append. source_commit = 작성 시점 tc-runner HEAD(예: `fc56cf8…`, Part 1 commit 후 새 HEAD). 각 행:
- `src/reporter.py` → `automation/tc_step/reporter.py` · transform_note=`from src.action_runner→from .action_runner + from src.catalog_delta→from learning.engine.catalog_delta + template parent.parent→parent` · status=`verified`
- `tests/test_reporter.py` → `automation/tc_step/tests/test_reporter.py` · transform_note=`from src.reporter→automation.tc_step.reporter + from src.action_runner→automation.tc_step.action_runner` · status=`verified`
- `templates/report.html` → `automation/tc_step/templates/report.html` · transform_note=`verbatim (HTML 템플릿)` · status=`verified`

(sha 계산: `git -C <tc-runner> show HEAD:<src path> | sha256sum` = source; target 은 `tr -d '\r' < <file> | sha256sum`. transform_note 에 콤마 금지.)

- [ ] **Step 8: MIGRATION §4.2-11 추가**

§4.2-10 뒤에:
```
11. **reporter 슬라이스(2026-06-16)** — `src/reporter.py`→`automation/tc_step/reporter.py`(import 2: `from .action_runner` + 교차 `from learning.engine.catalog_delta`; template 경로 parent.parent→parent) + `templates/report.html`→`automation/tc_step/templates/`(verbatim) + `tests/test_reporter.py`→`automation/tc_step/tests/`(import 2 전환). disjoint 집계 fix 는 tc-runner 소스 선반영(별도 commit) 후 이주 — 이주본=정정본. 검증 = file <N> passed / 전체 <M> passed / <K> skipped(회귀 0). 교차 import 런타임 스모크 OK. provenance 3행. jinja2 런타임 의존 = dependency manifest 후속 티켓.
```
(`<N>/<M>/<K>` 는 실제 실행값으로 채움.)

### Task 7: qa-suite commit (★사용자 승인 대기)

- [ ] **Step 9: commit (보고 후 승인 시 명시 path 만)**

```bash
cd "C:/Users/momen/Projects/qa-suite"
git add automation/tc_step/reporter.py automation/tc_step/templates/report.html \
  automation/tc_step/tests/test_reporter.py \
  campaigns/manifests/provenance.csv MIGRATION.md
git commit -m "automation/tc_step: reporter 슬라이스 이주 (disjoint summary 정정본 + template)"
```
(push 안 함.)

---

## Self-Review

**Spec coverage:**
- §2.1 status 우선순위 → Task 2 Step 4 ✓ / Task 1 status 테스트 4종 ✓
- §1.1 genuine RED(fail+skip TC) → Task 1 `test_get_summary_fail_plus_skip_in_one_tc` ✓
- §3 Part 1 get_summary 재작성 → Task 2 Step 5 ✓ / bundle fixture 정렬 → Task 1 Step 2 ✓
- §3 Part 2 import/template transform → Task 3-4 ✓ / provenance+MIGRATION → Task 6 ✓
- §4 TDD RED-first → Task 1(RED) → Task 2(GREEN) ✓
- §5 비목표(per-TC passed·HTML·schema bump·cli/mmi·requirements) → 플랜에 해당 작업 없음 ✓
- §6 롤아웃(단계별 commit 승인·push 금지) → Task 2 Step 8 / Task 7 Step 9 "승인 대기" ✓

**Placeholder scan:** sha/`<N>` 등은 "실제 계산값으로" 명시된 런타임 산출값(placeholder 아님 — 계산 방법 제공). 그 외 TBD/TODO 없음.

**Type consistency:** `TCResult.status` 반환 `"passed"|"failed"|"skipped"` — Task 1 테스트·Task 2 구현·get_summary 카운트 키 일치. `StepResult` kwargs(action/passed/duration/manual_action/skip_reason) = 기존 테스트와 동일 시그니처.
