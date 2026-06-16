# Reporter run-bundle summary 비중복(disjoint) 집계 계약 — 설계

- 날짜: 2026-06-16
- 영역: tc-runner `src/reporter.py` (정합성 fix) → qa-suite `automation/tc_step` (이주)
- 선결 근거: qa-suite `ARCHITECTURE.md §6` "reporter run-bundle summary 비중복 집계 의미 계약" (reporter 이주 선결)
- 상태: 승인됨 (Q1~Q3 + status 우선순위 보정 확정)

## 1. 문제

`Reporter.get_summary()` 가 `summary.json` 의 status별 카운트를 **중복 집계**한다.

```python
total   = len(self.results)                                  # TC 수
passed  = sum(1 for r in self.results if r.is_pass)          # is_pass = all(step.passed)
skipped = sum(1 for r in self.results
              if any(step.manual_action == "skip" for step in r.steps))
failed  = total - passed - skipped                           # 파생 — 중복분만큼 침식
```

근본 원인: 멤버십이 비배타(non-disjoint)인데 `failed` 를 `total - passed - skipped` 로 **파생**한다.
한 TC 가 둘 이상 버킷 성격을 가지면 차감이 실패를 침식한다.

### 1.1 근본 원인과 RED 케이스

**실 계약(skip=`passed=False`, §1.2) 하 잔존 버그 = 한 TC 안에 fail step + skip step 동시 존재** (genuine RED):

```python
TC_C = [
    StepResult(action="verify_text", passed=False),                       # 실패
    StepResult(action="manual_step", passed=False, manual_action="skip"), # skip
]
```
- 현 코드: `is_pass=False`(→passed 0) · `any skip`(→skipped 1) · `failed = 1 - 0 - 1 = 0`
  → `{total:1, passed:0, skipped:1, failed:0}` — **실패가 skipped 에 먹혀 사라짐.**
- 정정 후: `TC_C.status == "failed"` → `{total:1, passed:0, skipped:0, failed:1}`.

이 케이스가 이번 fix 의 **핵심 RED** 다. (TC_A=fail-only + TC_B=skip-only **분리** 시나리오는 skip 이
`passed=False` 인 실 계약에선 현 코드도 우연히 `{passed:0, skipped:1, failed:1}` 를 내므로 RED 가
약하다 — 회귀 잠금용으로만 유지.)

**레거시 관찰(참고)**: 현 `test_reporter.py::test_reporter_bundle_mode_summary_json_shape` 의 bundle
fixture 는 skip step 을 `passed=True` 로 구성 → 그 경우 skip TC 가 `is_pass=True` 라 passed·skipped
양쪽 계상(`{passed:1, skipped:1, failed:0}`). 이는 fixture 가 실 계약(§1.2)과 어긋난 탓이며, 본 fix 에서
fixture 를 `passed=False` 로 정렬한다.

### 1.2 action_runner skip 계약 (검증됨) — 함정

`src/action_runner.py:127-132` + `tests/test_action_runner.py::test_manual_step_skip` 계약:
**skip step = `passed=False` + `manual_action="skip"`**.

따라서 "`any step passed is False → failed`" 식의 순진한 분류는 **skip-only TC 를 failed 로 오분류**한다.
현 `test_reporter.py` 의 bundle fixture 는 skip step 을 `passed=True` 로 구성해 이 함정을 **테스트에서 가려왔다**
(실 runtime 은 `passed=False`). status 분류는 반드시 skip step 을 failed 판정에서 제외해야 한다.

## 2. 결정

| # | 결정 | 근거 |
|---|---|---|
| Q1 | **TC 레벨 disjoint**, 우선순위 `failed > skipped > passed` | 현 데이터 구조(`total=len(results)`)와 일치하는 최소 변경. "실패 우선" = QA 안전 기본값(실패 비은폐). HTML 카드 의미 유지 |
| Q2 | **tc-runner 소스 먼저 fix → 정정본 이주** (옵션 1) | 활성 도구 정합성 즉시 해소 · §2.3 source-of-truth(의미·코드·테스트 동시) · 이주본=정확 → divergence 0 · validate_tc 병존 패턴과 정합 |
| Q3 | **schema_version=1 / tool_version 유지**, disjoint 불변식을 본 spec 에 명문화 | 필드 구조 무변경 · v1 의 의도였고 구현만 버그 · 구 summary 는 애초 신뢰 대상 아님. contracts/ run-bundle 정식 명세는 별도 §6 티켓 |

### 2.1 status 분류 (보정 확정)

`TCResult.status` 프로퍼티 — `"passed" | "failed" | "skipped"` (직렬화 필드 아님, 내부 분류 단일 진실원천):

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

- `failed`: `manual_action != "skip"` 인 step 중 `passed=False` 가 하나라도 있으면
- `skipped`: failed 없고 `manual_action=="skip"` step 이 하나라도 있으면
- `passed`: 그 외
- 분류표: skip-only → `skipped` / fail-only → `failed` / pass-only → `passed` / **fail+skip 동시 → `failed`**

## 3. 설계

### Part 1 — tc-runner 소스 fix (정합성)

**`src/reporter.py`**
- `TCResult.status` 프로퍼티 추가 (위 §2.1). 기존 `is_pass`(=`all(step.passed)`) 는 **유지**(per-TC 직렬화·HTML ✓/✗ 가 계속 사용).
- `get_summary()`: `status` 로 직접 카운트. `total - passed - skipped` 파생 제거.
  ```python
  def get_summary(self) -> dict:
      total = len(self.results)
      passed = sum(1 for r in self.results if r.status == "passed")
      failed = sum(1 for r in self.results if r.status == "failed")
      skipped = sum(1 for r in self.results if r.status == "skipped")
      return {"total": total, "passed": passed, "skipped": skipped, "failed": failed}
  ```
- **무변경**: 필드 구조 · per-TC `passed`(=is_pass) 직렬화 · HTML 템플릿 · `schema_version` · `tool_version`.

**`tests/test_reporter.py`**
- **신규 핵심 RED — fail+skip 동시 TC (§1.1 TC_C)**: `results=[TC_C]` → `get_summary() == {total:1, passed:0, skipped:0, failed:1}` + `TC_C.status == "failed"`. 현 코드 = `{...skipped:1, failed:0}` 로 **RED**.
- 신규 `TCResult.status` 4분류: skip-only→skipped / fail-only→failed / pass-only→passed / fail+skip→failed.
- 신규 불변식 테스트: 혼합 결과 집합에서 `passed+failed+skipped == total`.
- `test_reporter_bundle_mode_summary_json_shape`: skip step `passed=True` → **`passed=False`**(실 계약 정렬, §1.2) + 기대 summary `{passed:1,skipped:1,failed:0}` → **`{total:2, passed:0, skipped:1, failed:1}`**. **회귀 잠금**(실 계약 하 현 코드도 통과 = RED 아님) · 단언 무영향.
- `test_reporter_summary`(passed=1/failed=1, skip 0) 는 영향 없음.

**검증·commit**: tc-runner 전체 suite GREEN → **tc-runner commit** (ahead 5 → +1). push 금지.

### Part 2 — qa-suite 이주 (reporter 슬라이스)

**`src/reporter.py`(정정본) → `automation/tc_step/reporter.py`**
- `from src.action_runner import StepResult` → `from .action_runner import StepResult` (동일 트랙 relative)
- `from src.catalog_delta import validate_run_id_for_filename` → `from learning.engine.catalog_delta import validate_run_id_for_filename` (교차 트랙 절대 — 결정7 패턴)
- template 경로: `Path(__file__).parent.parent / "templates"` → `Path(__file__).parent / "templates"` (reporter 가 `automation/tc_step/` 로 이동 → 템플릿은 `automation/tc_step/templates/`)
- `DEFAULT_TEMPLATE` 내장 fallback 유지

**`templates/report.html` → `automation/tc_step/templates/report.html`** (verbatim)

**`tests/test_reporter.py`(정정본) → `automation/tc_step/tests/test_reporter.py`**
- `from src.reporter import ...` → `from automation.tc_step.reporter import ...`
- `from src.action_runner import StepResult` → `from automation.tc_step.action_runner import StepResult`

**기록**: provenance 3행(reporter·test = transform / report.html = verbatim) + MIGRATION §4.2-11.

**의존성(P2)**: reporter 이주는 `jinja2` 를 qa-suite 런타임 의존으로 들인다. 현 실행환경에 설치돼 있어(`jinja2 3.1.6`) 검증은 그 전제로 진행. **qa-suite 독립 실행용 dependency manifest(requirements/pyproject) 정착은 본 slice 범위 밖 — MIGRATION 후속 티켓으로 기록**(이번 slice 에서 requirements 생성 안 함).

**검증·commit**: 타겟 test_reporter + qa-suite 전체 suite GREEN + 교차 import 런타임 스모크(`automation.tc_step.reporter` → `learning.engine.catalog_delta`) → **qa-suite commit**. push 금지.

## 4. 테스트 요건 (TDD)

1. **RED 먼저**: 핵심 RED = fail+skip 동시 TC(§1.1 TC_C) 의 `get_summary() == {total:1, passed:0, skipped:0, failed:1}` — 현 코드는 `{...skipped:1, failed:0}` 로 **실패**해야 한다. `TCResult.status` 4분류·불변식 테스트도 함께(status 미구현이라 동시 RED).
2. **GREEN**: `TCResult.status` 추가 + `get_summary()` 를 status 카운트로 수정 → RED 통과.
3. 불변식 `passed+failed+skipped==total` 은 모든 시나리오에서 고정. bundle 회귀 테스트는 실 계약(skip `passed=False`) 정렬 — RED 아닌 잠금.

## 5. 비목표 (YAGNI)

- per-TC `passed` 직렬화 의미 변경 X (= `is_pass` 유지)
- HTML presentation 변경(skipped 카드 추가 등) X
- `schema_version` / `tool_version` bump X
- contracts/ run-bundle 정식 명세 작성 X (별도 §6 티켓)
- cli / mmi_converter 이주 X (reporter 단독 이주 가능 — 의존 action_runner·catalog_delta 이주 완료)
- step 레벨 집계(B안) / TC+step 양립(C안) X
- qa-suite dependency manifest(requirements.txt/pyproject) 생성 X — jinja2 등 런타임 의존 정착은 MIGRATION 후속 티켓(현 실행환경 jinja2 존재 전제로 검증)

## 6. 롤아웃

- Part 1(tc-runner) → 검증 → 보고 → **사용자 승인 후 commit**
- Part 2(qa-suite) → 검증 → 보고 → **사용자 승인 후 commit**
- 양 repo 모두 **push 금지** (commit 은 단계별 보고 후 별도 승인)
