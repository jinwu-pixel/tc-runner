# Canonical Execution Contract — Design and TDD Implementation Plan

> 상태: **DESIGN ONLY / host-only**. 사용자 승인일은 2026-07-14이고, live source 재감사는 2026-07-20에 수행했다. 이 문서는 구현 승인, 단말 접촉 승인, 커밋 승인을 뜻하지 않는다.
>
> 실행 담당자는 별도 사용자 승인 후 이 문서의 gate와 RED→GREEN 순서를 그대로 따른다. 현재 회차에서는 이 문서 1개 외 코드·TC·governance 문서를 편집하지 않는다.

**Goal:** schema, validator, loader, runner와 Excel/MMI producer 사이의 실행 계약을 하나의 canonical dialect로 수렴시키고, 기존 runtime 의미 변경은 측정 후 opt-in flag로만 도입한다.

**Architecture:** 먼저 결정적 host-only ledger로 현재 수용 행렬과 corpus 영향을 고정한다. 그 다음 입력 경계에서 legacy alias를 canonical form으로 정규화하는 단일 계층을 만들고, 마지막으로 `cli run`에 기본 OFF인 fail-closed 모드를 연결한다. 종단 검증은 이미 git-tracked이고 과거 `runtime PASS` 근거가 있는 THOR2_J Settings SMOKE 01/02를 canonical mode로 차등 재실행해 `tc-runner` vertical loop를 닫는다. THOR2_K ko-KR authoring/runtime은 필요할 때 여는 별도 후속 캠페인이다.

**Tech stack:** Python 3, PyYAML, pytest, JSON Schema draft-07, CSV/Markdown evidence, existing `src.cli`/`ActionRunner`/`ADB` runtime.

## Global Constraints

- **Throughput guard:** ALT Part B 236은 `thor2j-tc-appium` side driver 경유다. 본 kernel 작업과 병렬·비차단이며, G1·Part B·SMOKE 같은 단말 캠페인이 항상 우선권을 가진다.
- 같은 Codex 세션에서 G1과 kernel 작업은 병렬 실행하지 않는다. single-writer로 순차 실행하고, 단말 창이 열리면 host-only kernel 작업은 즉시 양보한다.
- 현재 설계 회차는 host-only다. `adb`, 단말, 설정, 패키지, TC runtime을 접촉하지 않는다.
- kernel 코드 편집 시작 전 eng-mode core 5경로, 독립 USB composition 1경로, gap-8 문서 2경로, 이 설계서 1경로의 **정확-path 분리 커밋 완료**, commit `1affffc` 리뷰, Stage 0 governance 결정이 모두 필요하다.
- runtime 의미를 바꾸는 Slice 1b는 `legacy` 기본값을 유지한 opt-in flag로 시작한다. default flip은 별도 사용자 승인이다.
- 기존 1120 test node를 회귀 기준으로 고정한다. 신규 테스트 추가 후에는 전체 collected 수가 1120보다 커져야 하며 기존 node 실패·누락이 0이어야 한다.
- 구현 slice마다 source definition, code, tests를 같은 승인 batch에서 정렬한다. 일부 표면만 바꾸는 drift는 허용하지 않는다.
- 각 커밋·스테이징은 별도 사용자 승인 대상이다. 아래의 commit boundary는 후보일 뿐 자동 실행 지시가 아니다.

---

## 1. Decision and Scope

### 1.1 선택한 접근

세 접근을 비교했다.

| 접근 | 장점 | 위험 | 결정 |
|---|---|---|---|
| 표면별 patch | 국소 수정이 빠름 | alias·단위·metadata 규칙이 다시 복제됨 | 기각 |
| schema strict flip | 계약이 단순해 보임 | producer와 legacy corpus를 측정 없이 즉시 깨뜨림 | 기각 |
| **measure-first adapter + staged cutover** | drift를 수치화하고 기존 의미를 보존한 채 수렴 가능 | 단계와 gate가 필요 | **채택** |

채택안의 핵심은 다음과 같다.

1. Slice 0.5가 현재 행위를 재현 가능한 ledger로 고정한다.
2. Slice 1a가 alias→canonical 변환을 한 함수군으로 단일화한다.
3. Slice 1b가 canonical validation, runnable/UNRESOLVED gate, shell 결과, abort 정책을 opt-in runtime에 연결한다.
4. Slice 2가 기존 THOR2_J Settings SMOKE 01/02를 legacy mode와 canonical mode로 차등 검증하고, 가용 ja-JP 단말 창에서 실제 `tc_loader → cli → ActionRunner → reporter` 종단 경로를 검증한다.

### 1.2 포함 범위

- `tc_step_schema.json`, `validate_tc.py`, `src/tc_loader.py`, `src/action_runner.py`의 계약 수용 행위
- `src/excel_converter.py`와 `src/mmi_converter/{compiler.py,exporter.py}`의 producer 출력
- top-level name/metadata, step field alias, duration/timeout unit, fail-closed runtime gate
- deterministic drift ledger, corpus impact, TDD, staged cutover
- 기존 THOR2_J Settings SMOKE의 host canonical 차등검증과 가용 단말 조건부 runtime gate 설계
- 필요 시 별도 후속으로 여는 THOR2_K ko-KR authoring/runtime 캠페인 경계

### 1.3 제외 범위

- G1 `pm clear`, ALT Part B 실행, PFW seed/선택, 다른 단말 캠페인
- qa-suite로의 실제 소유권 cutover
- schema 전면 재작성, TypedDict/Pydantic 도입, 모든 unknown step field의 즉시 금지
- legacy mode 제거
- TC oracle authoring 또는 `RUNNABLE_NOW` 승격
- 현재 회차의 code/TC/governance edit, commit, push, staging

---

## 2. Live Evidence Baseline

아래는 2026-07-20 host static inspection으로 재확인한 사실이다. 단말 관찰이나 `runtime PASS` 주장이 아니다.

| 표면 | 검증 확정 사실 | 상태 |
|---|---|---|
| schema | top-level `tc_name`, `metadata`, `steps` 필수; top-level extra field 금지; metadata에 `runnable/tc_class/execution_type/manual_detail` 필수 | observed |
| schema step | text 계열은 `target`, wait는 `duration`(ms), key는 `key`, swipe는 `x/y/x2/y2`; timeout 설명은 ms | observed |
| validator | schema-derived action required rules를 사용하지만 lint helper는 `seconds`와 `duration`을 모두 수용 | observed contradiction |
| loader | `tc_name → name`만 정규화하고 metadata, runnable, unresolved, action parameter를 검사하지 않음 | observed |
| runner | `text/target`, `seconds/duration`, `keycode/key`, `x1/y1` 또는 `x/y`를 action별로 개별 수용 | observed plurality |
| `tap_id` | schema는 `target`을 요구하지만 runner는 `id`를 직접 인덱싱 | observed runtime seam |
| screenshot | runner는 `name`을 사용하지만 schema property definition에 없음; step extra field가 닫혀 있지 않아 ungoverned 상태 | observed |
| `input_text` | `src/action_runner.py:371-373`의 `_input_text`는 입력값으로 `text`를 직접 소비; selector action의 `text → target` alias와 action scope가 다름 | observed action-scoped exception |
| `key_sequence` | runner의 `delay`는 `time.sleep(delay)`에 직접 전달되어 seconds 단위로 잔존 | observed deferred unit mismatch |
| timeout | `verify_shell.timeout`은 schema상 ms지만 `ADB.shell(timeout=...)`에는 seconds로 그대로 전달 | observed unit drift |
| shell | `ADB.shell`은 return code/stderr를 버리고 stdout만 반환; `ActionRunner._shell`은 무조건 성공 반환 | confirmed defect |
| Excel producer | `name`; `text/id/seconds/keycode/x1/y1/name`을 출력하고 metadata 없음 | observed legacy producer |
| Excel swipe | `x2/y2`를 출력할 입력 계약이 없어 runner에서 `KeyError` 가능 | confirmed defect |
| MMI producer | compiler가 `text/keycode/seconds`; exporter가 `name`과 `automation_class/runnable`을 출력하나 canonical metadata 필수 필드가 불완전 | observed legacy producer |
| `cli run` | `metadata.runnable:false`와 unresolved를 gate하지 않고, verifier 실패만 현재 TC를 중단; non-verifier 실패 후 다음 step을 계속함 | observed runtime looseness |
| ALT Part B | handoff는 236 = verify_text 229 + focus_state 7, runner 소유를 `thor2j-tc-appium` side로 명시 | observed throughput independence |

### 2.1 Corpus impact baseline

read-only YAML scan 결과다.

| corpus | 파일 | canonical field 관찰 | legacy alias 관찰 | required metadata |
|---|---:|---|---|---:|
| `golden_tc_set/` | 3 | `duration=13`, `key=5`, `target=4`, `name=11` | 0 | 3/3 |
| `exported_tc1/` | 25 | `duration=283`, `key=61`, `target=127`, `x/y=55`, `x2/y2=54`, `name=87` | 0 | 25/25 |
| `THOR2_J - Settings/SETTINGS_SMOKE_01/02.yaml` | 2 | top-level `tc_name=2`, `duration=3`, `target=11`, screenshot `name=3` | 0 | 2/2 |
| tracked legacy `tc_samples/simple_smoke_test.yaml` | 1 | screenshot `name=1` | top-level `name=1`, `seconds=1`, `keycode=2` | 0/1 |
| `THOR2_K - Settings/SETTINGS_SMOKE_*.yaml` | **0** | — | — | — |

따라서 golden 3, exported 25, THOR2_J SMOKE 2는 step dialect 관점에서 이미 canonical이다. J 실파일의 top-level도 `name`이 아니라 `tc_name`이다. J는 semantic-delta-0 실코퍼스로 사용하고, `name → tc_name` adapter는 tracked legacy sample과 합성 fixture로 별도 고정한다. `THOR2_J - Settings/RESUME.md`와 `BUG_LOG.md`에는 SMOKE 01 `runtime PASS 11/11`, SMOKE 02 `runtime PASS 13/13`의 과거 근거가 있다. 이는 Slice 2 재실행 결과가 아니라 단일변수 차등검증의 baseline이다. THOR2_K target SMOKE는 0건이며 kernel 종결 선행조건이 아니다.

### 2.2 Test baseline

- commit `1affffc` 메시지는 `tests/ 1120 passed (회귀 0)`을 기록한다.
- 2026-07-20 collect-only 재확인 결과는 tracked tests 1073개 + untracked eng-mode backlog의 `tests/test_eng_mode_runner.py` 47개 = **1120개**다.
- 이 회차에서는 full pytest를 실행하지 않았다. 따라서 현재 상태를 새 `validate PASS`나 test pass로 주장하지 않는다.
- backlog flush 후 kernel 첫 RED 전에 `pytest tests/ -q`로 1120개 전부 green을 다시 고정해야 한다. repo root 전체 실행은 `doc/THOR2_VoiceRec_AutoTest_20260429`의 선존 collection 오류로 중단되므로, 정식 regression baseline 표면은 `tests/`다 (`tests/ regression baseline: 1120 passed`).

---

## 3. Current Contract Drift Matrix

### 3.1 Canonical and legacy forms

| 의미 | canonical | accepted/emitted legacy | 현재 문제 |
|---|---|---|---|
| TC id | `tc_name` | `name` | schema와 loader 방향이 반대 |
| text selector | `target` | `text` | validator와 runner 수용 규칙 분리 |
| resource id selector | `target` | `id` | canonical validated input이 runner에서 실패 가능 |
| wait | `duration` ms | `seconds` s | validator schema와 lint/runner 모순 |
| key | `key` | `keycode` | producer와 schema 불일치 |
| swipe start | `x`,`y` | `x1`,`y1` | producer legacy; endpoint 누락 별도 결함 |
| swipe end | `x2`,`y2` | 없음 | Excel producer가 미출력 |
| screenshot label | `name` | — | runner 소비 필드가 schema에 미정의 |
| input value | `input_text.text` | — | selector alias 정규화가 이 필드를 건드리면 입력값이 유실됨 |
| key sequence pacing | `key_sequence.delay` seconds | — | ms 통일에서 의도적으로 이연; ledger 관찰만, v1 정규화 대상 아님 |
| verifier timeout | `timeout` ms | runner가 seconds로 해석 | 1000배 단위 drift 가능 |
| TC class | `metadata.tc_class` | `metadata.automation_class` | MMI exporter metadata 불완전 |

### 3.2 Producer × consumer current pairs

Slice 0.5는 아래 8개 pair를 executable probe로 다시 계산한다. 이 표는 현재 static inspection에서 확정한 seed다.

| producer → consumer | schema | `validate_tc.py` | `tc_loader.py` | `ActionRunner` |
|---|---|---|---|---|
| Excel | `name`/metadata/legacy fields로 비정합 | top-level·required field 실패 | `name`을 수용, parameter 검사는 생략 | 대부분 alias로 실행; swipe endpoint 누락 시 실패 |
| MMI | `name`/metadata/legacy fields로 비정합 | top-level·required field 실패 | `name`을 수용, metadata는 무시 | `text/keycode/seconds` alias로 실행 |

### 3.3 Existing embryos to reuse

- `tc_loader`: `tc_name → name` compatibility shim
- `validate_tc`: schema의 per-action `required` rule derivation
- `validate_tc._normalize_wait_seconds`: `seconds`/`duration` 단위 변환
- runner: 이미 존재하는 alias 수용 분기와 action dispatch sentinel tests

이 배아는 복사하지 않는다. Slice 1a에서 `src/execution_contract.py`로 이동 또는 위임해 한 구현만 남긴다.

---

## 4. Canonical Execution Contract v1

### 4.1 Top-level shape

Canonical document는 다음을 만족한다.

```yaml
tc_name: SETTINGS_SMOKE_01_app_launch_K
description: Settings cold-launch smoke
metadata:
  runnable: true
  tc_class: FULL_AUTO
  execution_type: AUTO
  manual_detail: NONE
steps:
  - action: wait
    duration: 1500
```

- `tc_name`만 canonical이다. `name`은 input-boundary legacy alias다.
- metadata 4필드는 생략하거나 추정 기본값으로 채우지 않는다.
- `runnable:false`, non-empty `runnable_reason`, unresolved marker는 canonical runtime에서 blocking이다.
- display/report layer가 `name`을 필요로 하면 `tc_name`을 읽는다. canonical dict에 duplicate `name`을 다시 만들지 않는다.

### 4.2 Per-action fields and units

| action | canonical required fields | optional unit/field |
|---|---|---|
| `tap_text`, `verify_text`, `verify_gone` | `target` | `timeout` ms for supported verifier |
| `tap_content_desc`, `verify_content_desc` | `target` | `timeout` ms when supported |
| `tap_id` | `target` | — |
| `tap_xy` | `x`, `y` | — |
| `swipe` | `x`, `y`, `x2`, `y2` | `duration` ms, default 300 |
| `key` | `key` | — |
| `key_sequence` | `keys` | `delay` seconds remains action-specific v1 field |
| `shell` | `command` | `timeout` ms if added to the action |
| `verify_shell` | `command`, `expected` | `timeout` ms, default 30000 |
| `wait` | `duration` ms | — |
| `screenshot` | `name` | deterministic fallback remains allowed only in legacy mode |
| `input_text` | `text` | `text` is canonical here, not a selector alias |
| `manual_pause` | `description` | existing manual fields preserved |

`key_sequence.delay`는 현재 runner의 `time.sleep()` 경계와 호환성을 유지하기 위해 seconds로 남기는 **알려진 이연 불일치**다. v1 adapter는 이를 ms로 변환하거나 이름을 바꾸지 않고 ledger에 관찰 행만 남긴다.

### 4.3 Alias normalization

`normalize_tc` and `normalize_step` operate on copies and never mutate caller data.

| action scope | alias → canonical |
|---|---|
| top-level | `name → tc_name` |
| `tap_text`, `verify_text`, `verify_gone` | `text → target` |
| `tap_id` | `id → target` |
| `wait` | `seconds → duration` with seconds×1000 |
| `key` | `keycode → key` |
| `swipe` | `x1 → x`, `y1 → y` |
| metadata compatibility | `automation_class → tc_class` only when value belongs to canonical enum |

Rules:

1. canonical-only input is unchanged and produces no alias finding.
2. alias-only input is converted and emits `ALIAS_NORMALIZED`.
3. canonical+alias with semantically equal values keeps canonical, drops alias, emits non-blocking `ALIAS_DUPLICATE`.
4. canonical+alias with different values emits blocking `ALIAS_CONFLICT`; neither value is guessed.
5. seconds conversion uses decimal text semantics at 1 ms resolution. Negative, non-numeric, or sub-millisecond precision-loss values emit blocking `INVALID_UNIT`.
6. normalization is idempotent: `normalize(normalize(x).value)` has byte-equivalent canonical JSON and no new alias finding.
7. recognized auxiliary fields (`execution_mode`, `step_role`, `compile_status`, lint fields, descriptions) are preserved.
8. unknown step fields are not silently deleted. v1 records `UNDECLARED_STEP_FIELD`; tightening them to blocking is a later schema gate.
9. `text → target`은 표에 열거한 selector action에만 적용한다. `input_text.text`는 입력 payload이므로 그대로 보존하며 `target`을 만들지 않는다.

### 4.4 Shared interface

`src/execution_contract.py` owns these interfaces.

```python
@dataclass(frozen=True)
class ContractFinding:
    code: str
    path: str
    severity: str          # "INFO" | "ERROR"
    canonical_field: str | None
    observed_field: str | None
    detail: str


@dataclass(frozen=True)
class NormalizationResult:
    value: dict
    findings: tuple[ContractFinding, ...]

    @property
    def blocking(self) -> bool:
        return any(f.severity == "ERROR" for f in self.findings)


# Public API signatures
normalize_step(step: Mapping[str, Any], *, path: str) -> NormalizationResult
normalize_tc(tc: Mapping[str, Any], *, source: str) -> NormalizationResult
derive_action_required(schema: Mapping[str, Any]) -> dict[str, tuple[str, ...]]
validate_canonical_tc(tc: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]
```

`validate_tc.py`, canonical loader, ledger가 이 interface를 재사용한다. runner 내부에서 alias를 다시 정규화하지 않는다.

### 4.5 Metadata policy

- `execution_type`, `manual_detail`, `has_manual_steps` 파생의 normative source는 `tc_prompts/STAGE2_COMPILE.md` Step 4다.
- normalizer는 누락 metadata를 발명하지 않는다.
- MMI canonical producer는 이미 보유한 classified steps에서 Step 4 규칙으로 metadata를 파생한다.
- Excel canonical producer는 explicit metadata input 없이는 `METADATA_REQUIRED`로 닫는다. 단순 action 목록만 보고 TC class나 외부 개입을 추측하지 않는다.
- `automation_class` alias는 enum이 정확히 맞는 경우만 `tc_class`로 변환한다. `execution_type/manual_detail`은 별도로 파생·제공되어야 한다.

### 4.6 Timeout boundary

- TC contract의 모든 `timeout`은 ms다.
- `ActionRunner`가 ADB process boundary에서만 `timeout_ms / 1000.0`으로 변환한다.
- ADB API parameter는 `timeout_s`로 이름을 고정해 unit을 드러낸다.
- `verify_shell` default는 30000 ms이며, `verify_gone`의 기존 ms 해석과 정렬한다.
- 예외: `key_sequence.delay`는 seconds인 알려진 이연 불일치다. v1 timeout/ms 통일 범위 밖이며 ledger 관찰만 수행한다.

---

## 5. Governance and Throughput Gates

### 5.1 Stage 0 — repository policy SSOT decision

live Git 기준 `CLAUDE.md`는 tracked·modified이고 `AGENTS.md`는 untracked다. 이는 세션 지시의 효력을 바꾸는 사실이 아니라, **repository documentation SSOT**가 미결정이라는 뜻이다.

별도 사용자 gate에서 다음 중 하나를 정한다.

- **A — `CLAUDE.md` canonical 유지 (현재 live Git 근거상 권고):** `AGENTS.md`는 mirror/local instruction으로 남기고 §8.2 proposed row는 `CLAUDE.md`에만 반영한다.
- **B — `AGENTS.md` canonical 전환:** tracking, reference, archive policy를 별도 migration으로 정렬한 뒤 governance row의 목적지를 바꾼다.

결정 전에는 두 파일을 자동 동기화하거나 어느 쪽도 편집하지 않는다.

### 5.2 Kernel code edit prerequisites

Stage 0은 실행 계획만 고정하며, 아래 각 stage/commit은 **매번 사용자 명시 승인 후** exact-path로만 수행한다. 현재 live Git 근거상 repository policy SSOT는 **A안(`CLAUDE.md` canonical 유지)**을 권고한다. `CLAUDE.md`는 tracked이고 `AGENTS.md`는 untracked이기 때문이다. 이 사실은 자동 결정을 뜻하지 않으며 최종 SSOT 선택은 별도 사용자 gate다.

원래 제시된 eng-mode 6-path 묶음을 소스 연관성으로 감사한 결과, `scripts/usb_composition_verify.py`는 eng-mode runner/profile을 참조하지 않고 BTS25462 USB composition retention evidence를 기본 경로로 사용하는 독립 도구다. 따라서 3개 논리 batch를 다음 **4개 물리 commit**으로 분리하는 안을 권고한다. 사용자가 물리 commit 3개만 유지하려면 USB path를 eng-mode에 혼입하지 말고 이번 backlog flush 밖에 남긴다.

**Commit 1a — eng-mode core, 5 paths**

1. `ODIN2 - Engineer IMS/RUNTIME_PLAYBOOK.md`
2. `docs/superpowers/specs/2026-07-13-eng-mode-runner-generalization-design.md`
3. `scripts/eng_mode_profiles.py`
4. `scripts/eng_mode_runner.py`
5. `tests/test_eng_mode_runner.py`

`RUNTIME_PLAYBOOK.md`는 commit 1a에만 포함한다. 현재 diff가 eng-mode migration 범위라는 사전 감사 결과를 staging 직전 다시 확인하고, user-owned 또는 다른 캠페인 hunk가 새로 섞였으면 STOP한다.

**Commit 1b — USB Composition BTS25462, 1 path**

1. `scripts/usb_composition_verify.py`

**Commit 2 — gap-8 docs, 2 paths**

1. `THOR2 - ALT Basic TC Audit/MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md`
2. `THOR2 - ALT Basic TC Audit/RESULT_MEDIA_SEED_C11_GAP8_2026-07-13.md`

**Commit 3 — canonical contract design, 1 path**

1. `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md`

각 commit 직전 `git diff --cached --name-only`가 비어 있는지 확인하고, 위 명시 path만 stage한다. `git add .`, `git add -A`, 디렉터리 broad add는 금지다. `CLAUDE.md`의 현재 user-owned 변경은 어느 backlog commit에도 넣지 않는다. `RUNTIME_PLAYBOOK.md`도 commit 1a 밖으로 혼입하지 않는다.

Commit `1affffc`의 3-path 리뷰 결과는 다음과 같이 Stage 0 ledger에 고정한다.

| path | 검토 결과 | Task 2 보존 조건 |
|---|---|---|
| `validate_tc.py` | §3-e가 `runnable_reason`의 list/dict/int 비문자열 원소를 set membership 전에 형식 오류로 fail-closed 처리 | normalizer/validator 재편집 후에도 TypeError 없이 같은 형식 오류 유지 |
| `tests/test_execution_type.py` | cases 20/21/22가 list/dict/int 반례를 고정 | 세 nodeid를 원본 회귀 집합으로 보존 |
| `tc_prompts/STAGE2_COMPILE.md` | R7 focus model 체크리스트를 node/list 규범에 정렬 | Task 2의 emitted-field 표 정렬이 R7 문구를 되돌리지 않음 |

위 backlog commit과 SSOT 사용자 결정이 끝난 뒤, kernel 첫 RED 전에 repo root에서 `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider`를 실행해 기존 **1120 tests green**을 재고정한다. 실패·node 누락이면 Slice 0.5 code edit 전에 STOP한다. 이 절은 commit/staging/test의 자동 실행 지시가 아니다.

### 5.3 §2.5 qa-suite proposed row와의 관계

본 작업은 qa-suite cutover를 선언하거나 §2.5 proposed row를 supersede하지 않는다. 현재 writer인 tc-runner의 execution contract를 안정화하는 **pre-cutover prerequisite**다. qa-suite owner matrix가 바뀌면 이 contract와 ledger를 migration input으로 넘긴다.

### 5.4 Time-box and preemption

| stage/slice | maximum elapsed | deliverable | preemption rule |
|---|---:|---|---|
| Stage 0 | 45 min | SSOT decision, backlog audit, 1120 baseline | 단말 창 즉시 양보 |
| Slice 0.5 | 4 h | deterministic CSV + SUMMARY | G1/Part B 우선 |
| Slice 0.5 review | 30 min | adapter acceptance freeze | review 미완료 시 code STOP |
| Slice 1a | 1 workday | canonical normalizer + consumer/producer alignment | campaign 우선, time-box 초과 시 partial report |
| Slice 1b | 1 workday | opt-in fail-closed CLI/runner | default flip 금지 |
| Slice 2 host differential | 1 h | existing J SMOKE legacy/canonical semantic diff | device 0; mismatch 시 runtime 금지 |
| Slice 2 device window | 45 min | existing J SMOKE actual tc-runner runtime evidence | ja-JP 단말 가용 시만; sole/pin 규율 우선 |
| Optional K follow-up | 2 h host + separate device window | ko-KR coverage가 실제 필요할 때 authoring/validate/runtime | kernel 종결 선행조건 아님 |
| Cutover review | 30 min | default flip 여부 | 별도 사용자 결정 |

Time-box는 품질을 낮추는 마감이 아니다. 초과 시 현재 RED/GREEN 상태와 blocker를 기록하고 멈춘다.

---

## 6. Slice 0.5 — Measure-first Contract Drift Ledger

### 6.1 Deliverable

Create:

- `scripts/contract_drift_ledger.py`
- `tests/test_contract_drift_ledger.py`
- runtime evidence: `reports/contract_drift/<input_digest>/contract_drift_matrix.csv`
- runtime evidence: `reports/contract_drift/<input_digest>/SUMMARY.md`

`<input_digest>`는 문서 표기의 변수명이다. 실제 실행에서는 fixture version, 6 actor source files, corpus bytes의 sorted SHA-256으로 자동 계산하며 사람이 입력하지 않는다.

### 6.2 Probe model

Host-only fake dependencies를 사용해 실제 함수 경계를 probe한다.

- schema: current schema-derived required fields
- validator: `validate_tc.validate_tc`
- loader: temporary YAML input, no device
- runner: fake ADB + patched sleep/screenshot, no subprocess
- Excel producer: temporary workbook → emitted YAML
- MMI producer: synthetic IR → compiler → exporter document

Fixture set은 최소 다음 양방향 반례를 포함한다.

- canonical-only, alias-only, equal duplicate, conflicting duplicate
- `target/text`, `duration/seconds`, `key/keycode`, `x/y` vs `x1/y1`, `target/id`
- `fixture_id=input_text_text_canonical`: `input_text.text` canonical payload에 `target/text` selector alias 규칙을 적용하지 않는 독립 fixture 1행
- `fixture_id=key_sequence_delay_seconds_observed`: `key_sequence.delay` seconds 알려진 이연 불일치 관찰 fixture 1행; 정규화 대상 아님
- screenshot `name`
- timeout 5000 ms interpretation
- `runnable:false`, `runnable_reason`, `compile_status: UNRESOLVED_PARAMS`
- Excel swipe endpoint missing
- shell returncode 1 with non-empty stdout

### 6.3 CSV schema

Stable column order:

```text
schema_version,fixture_id,actor_kind,actor,producer,consumer,corpus,
source_path,tc_name,step_index,action,variant,canonical_field,
observed_fields,unit,verdict,finding_code,normalized_json,source_sha256
```

- rows sort by `(producer, consumer, corpus, source_path, tc_name, step_index, fixture_id)`.
- JSON cells use sorted keys and compact UTF-8 serialization.
- no wall-clock timestamp is included in deterministic content.
- source file is never modified.

### 6.4 SUMMARY contract

`SUMMARY.md` contains:

1. input digest and tool/schema version
2. 4 consumers × 2 producers acceptance matrix
3. alias and unit counts by action
4. golden 3 / exported 25 / existing THOR2_J SMOKE 2 / tracked legacy `name` sample 1 impact; optional THOR2_K count is reported separately
5. blocking findings and confirmed defects
6. adapter acceptance checklist
7. output SHA-256 and self-check result

Current primary corpus counts `3/25/2/1` are locked regression expectations in the order above. THOR2_K target count 0 remains an informational field only; optional K authoring is not a Slice 2 or kernel completion gate.

### 6.5 Exit behavior

- `0`: scan completed and outputs passed internal consistency; drift findings may exist.
- `1`: `--fail-on-blocking` requested and blocking findings exist.
- `2`: input parse/read failure.
- `3`: deterministic/self-check invariant failure.

Measure mode does not confuse discovered drift with tool failure. Cutover gate uses `--fail-on-blocking`.

### 6.6 Slice 0.5 acceptance

- two independent runs produce byte-identical CSV/SUMMARY and identical hashes.
- exactly 8 producer-consumer pair groups are present.
- seed facts in §2/§3 are reproduced, including the two confirmed defects.
- corpus paths are sorted and primary counts equal `3/25/2/1`; optional THOR2_K count remains separately visible as 0.
- no source/corpus file mtime or hash changes.
- only after Claude review freezes the matrix may Slice 1a begin.

---

## 7. Slice 1a — Canonical Normalization Layer

### 7.1 Data flow

```text
raw YAML / producer output
        |
        v
normalize_tc() ---- findings ----> ledger/report
        |
        v
canonical validation
        |
        +---- blocking -> no runtime
        |
        v
tc_loader canonical result -> cli/runner
```

Only the ingress boundary understands aliases. `ActionRunner` canonical mode receives canonical fields only.

### 7.2 Consumer integration

- `validate_tc.py`: normalizes once, reuses `derive_action_required`, then validates canonical data. Lint consumes the same normalized view; `_normalize_wait_seconds` becomes a thin compatibility wrapper or is removed after callers migrate.
- `src/tc_loader.py`: add `contract_mode: Literal["legacy", "canonical"] = "legacy"`. Canonical mode returns `tc_name` and performs normalization + canonical validation. Legacy mode stays byte/behavior compatible.
- `tc_step_schema.json`: define screenshot `name`; lock ms units in descriptions; keep v1 step extra-field openness unchanged; retain canonical action requirements.
- runner: alias branches remain only for legacy mode during Slice 1a. Removal is not part of this cutover.

### 7.3 Producer alignment

**Excel**

- add canonical conversion mode; legacy remains default until cutover.
- emit `tc_name`, canonical step fields, and explicit supplied metadata.
- for `swipe`, canonical input encoding is `Parameter1="x,y"`, `Parameter2="x2,y2"`; both pairs must be two integers. Scalar legacy start coordinates without endpoint emit `SWIPE_ENDPOINT_MISSING` and write no runnable TC.
- canonical producer 승격 전, user-approved **실 워크북**의 converter 6-column row에서 위 두 coordinate pair를 read-only로 대조하고 workbook path/sheet/row와 redacted cell values를 evidence에 남긴다. 2026-07-20 사전 감사에서 `tc_samples/TC_1.xlsx`에는 swipe row가 없고 `tc_samples/ODIN T_C 메뉴트리.xlsx`의 `swipe` 문자열은 자연어 TC 본문뿐이어서 해당 실표본이 아니다. 적합한 실표본이 없으면 합성 workbook fixture로 대체했다고 주장하지 않고 producer promotion을 STOP해 표본을 요청한다.
- do not repurpose `Expected` as endpoint storage.

**MMI**

- compiler canonical mode emits `target`, `key`, `duration`.
- exporter emits `tc_name` and canonical metadata.
- `execution_type/manual_detail/has_manual_steps` derive from STAGE2 Step 4; unresolved input remains `runnable:false` with a canonical reason.
- `exported_at` stays evidence metadata but is excluded from deterministic ledger comparisons.

### 7.4 Slice 1a acceptance

- all alias fixtures normalize to canonical form once and idempotently.
- conflicts fail with stable finding codes.
- validator, loader, and ledger call the same normalizer.
- golden 3 and exported 25 have zero blocking findings and zero semantic delta.
- Excel/MMI canonical-mode outputs validate against the schema when complete explicit input is supplied.
- legacy-mode producer tests remain unchanged.

---

## 8. Slice 1b — Opt-in Fail-closed Runtime Gate

### 8.1 CLI flag

Add:

```text
cli run ... --contract-mode {legacy,canonical}
```

- default: `legacy`
- canonical mode is opt-in until cutover review.
- unknown mode is argparse rejection.
- report bundle records the selected mode. This is a required reporter contract change, not a conditional fallback.

### 8.2 Pre-device host gate

Canonical mode resolves, loads, normalizes, and validates **all** TC files before constructing `ADB` or issuing any device call.

Invocation aborts with non-zero exit if any TC has:

- canonical/schema error
- `metadata.runnable is not True`
- non-empty `runnable_reason`
- `metadata.has_unresolved_params is true`
- `compile_status == UNRESOLVED_PARAMS`
- non-empty `_unresolved_params`
- unresolved shell placeholder
- alias conflict or invalid unit

No valid subset is run when the invocation contains a blocking TC. This prevents partial device mutation before a later file fails validation.

### 8.3 Shell result contract

`src/adb.py` adds a non-breaking structured API.

```python
@dataclass(frozen=True)
class ShellResult:
    command: str
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


# ADB public API signature
shell_result(command: str, *, timeout_s: float = 10.0) -> ShellResult
```

- existing `shell() -> str` remains for legacy callers in this slice.
- canonical `_shell` and `_verify_shell` use `shell_result`.
- returncode non-zero fails even if stdout contains expected text.
- message/report includes bounded stdout/stderr and returncode, with existing redaction policy applied at artifact boundary.

### 8.4 Abort policy

Canonical mode applies one rule to all actions:

1. first failed step stops the current TC immediately;
2. remaining TCs are not started;
3. no speculative automatic cleanup action is injected;
4. reporter writes the partial result with `ABORTED_FAIL_CLOSED` context;
5. process exits non-zero.

Legacy mode preserves the current verifier-only break behavior until default cutover.

`src/reporter.py` bumps `SUMMARY_SCHEMA_VERSION` from 1 to 2. Every `summary.json` gains top-level `contract_mode` (`legacy` or `canonical`) and `run_status` (`COMPLETED` or `ABORTED_FAIL_CLOSED`). A canonical fail-closed abort must persist `run_status: ABORTED_FAIL_CLOSED` even when only a partial TC/step result exists. Readers/tests that assert schema version 1 are updated in the same slice; silently adding fields without a version bump is prohibited.

### 8.5 Promotion stages

| stage | default | evidence required | next decision |
|---|---|---|---|
| 1b-A | legacy | ledger + unit tests | opt-in host corpus check |
| 1b-B | legacy | golden 3/exported 25 canonical check, blocking 0 | Slice 2 device gate |
| 1b-C | legacy | existing THOR2_J Settings SMOKE legacy↔canonical differential; device evidence when ja-JP device is available | default flip review only after device evidence |
| 1b-D | user decision | tests/ regression baseline + campaign impact | default canonical or remain opt-in |

Legacy removal is not implied by a default flip.

---

## 9. Slice 2 — Existing THOR2_J Settings Canonical Differential

### 9.1 Why existing THOR2_J Settings

Primary corpus:

- `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml`
- `THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml`

두 파일은 git-tracked이고 현재 canonical step dialect와 top-level `tc_name`을 사용한다. `THOR2_J - Settings/RESUME.md`와 `BUG_LOG.md`에는 각각 과거 `runtime PASS 11/11`, `runtime PASS 13/13`가 기록돼 있다. 기존 legacy-mode PASS를 같은 TC로 재현한 뒤 contract mode만 canonical로 바꾸면 신규 TC authoring과 새 oracle이라는 두 미지수를 동시에 도입하지 않는다. TC authoring gate도 제거되며, J의 top-level이 `name`이라는 가정은 사용하지 않는다. `name → tc_name`은 §2.1의 tracked legacy sample과 contract fixture가 담당한다.

Required vertical path:

```text
existing THOR2_J Settings YAML
  -> src.tc_loader canonical mode
  -> src.cli run pre-device gate
  -> ActionRunner
  -> Reporter schema v2 bundle
```

ALT Part B 236은 이 kernel loop에 부적합하다. 실행 owner가 `thor2j-tc-appium` side driver라서 campaign oracle은 검증할 수 있어도 tc-runner loader/CLI/runner wiring을 입증하지 못한다. ALT Part B는 본 작업과 병렬·비차단으로 유지한다.

### 9.2 Host differential — device 0

1. ledger에서 J 두 파일이 blocking 0이고 semantic-delta-0인지 확인한다.
2. 두 파일을 legacy와 canonical loader로 각각 읽어 action order, command, selector, timeout, metadata projection을 비교한다. 표시용 top-level key 차이는 canonical projection 후 비교한다.
3. canonical preflight의 ADB construction 0 negative cases를 실행한다.
4. reporter schema v2 fixture에서 `contract_mode`와 `COMPLETED`/`ABORTED_FAIL_CLOSED`를 확인한다.
5. 원본 J YAML hash/mtime 변화 0을 확인한다. host Slice 2는 TC 편집이나 authoring을 포함하지 않는다.

Host differential이 green이어도 실제 `runtime PASS`를 주장하지 않는다. 반대로 ja-JP 단말이 없어도 host kernel implementation/test closeout은 가능하지만, device-backed promotion과 default flip은 계속 보류한다.

### 9.3 Device-window sequence — availability conditional

THOR2_J의 ja-JP 단말(B27)이 다른 세션에서 점유될 수 있으므로, device portion은 가용 창과 별도 serial-pinned 사용자 승인에 조건부다.

1. sole device/model/locale와 Settings precondition을 승인된 지시문으로 확인한다.
2. 같은 파일·같은 단말 상태에서 legacy mode SMOKE 01을 재실행하고, 전 step 성공 시에만 `runtime PASS 11/11`로 기록한다.
3. §3.5 조건이 맞으면 legacy mode SMOKE 02를 재실행하고, 전 step 성공 시에만 `runtime PASS 13/13`로 기록한다.
4. 같은 window에서 contract mode만 canonical로 바꾸어 SMOKE 01→02를 같은 순서로 실행한다.
5. legacy/canonical step result, duration, shell returncode, bundle `contract_mode`, `run_status`를 대조한다.
6. mismatch나 unexpected mutation이면 default는 legacy로 유지하고 exact step에서 STOP한다.

단말 미가용은 `NOTE`이며 host 테스트의 FAIL은 아니다. 다만 device portion은 `미실행`으로 남고, canonical default promotion의 근거로 사용할 수 없다.

### 9.4 Optional THOR2_K follow-up

ko-KR coverage가 실제로 필요할 때만 THOR2_K를 별도 캠페인으로 연다. 현재 target TC는 0개이므로 grounded K catalog evidence, TC authoring, validate, serial-pinned runtime 각각에 별도 사용자 승인이 필요하다. J literal/selector를 K로 복사하지 않는다. 이 후속 캠페인은 kernel 구현 종결 선행조건이 아니다.

### 9.5 Slice 2 acceptance

- host: existing J two-file canonical projection has blocking 0 and semantic delta 0; original files remain unchanged.
- host: schema-v2 report fixtures record contract mode and fail-closed abort context.
- device, when available: legacy reproduction and canonical replay both traverse actual tc-runner runtime with equivalent outcomes.
- report contains no silent failed shell; non-verifier negative control remains host-mocked and is not injected into the device campaign.
- device result uses §2.2 vocabulary: `runtime PASS` only when every approved step passes; unavailable means `미실행`, not PASS or FAIL.

---

## 10. File-by-file TDD Execution Plan

Every task is a separate review gate. Commands are run from repo root with `venv/Scripts/python.exe`. Commit is never automatic.

### Task 0: Stage 0 gates

**Files:** no edit.

**Steps:**

- [ ] Present SSOT recommendation A (`CLAUDE.md` canonical: tracked; `AGENTS.md`: untracked) and obtain the separate user decision; do not edit either file yet.
- [ ] Obtain explicit approval and commit exact eng-mode core 5 paths as commit 1a; recheck every `RUNTIME_PLAYBOOK.md` hunk before staging.
- [ ] Obtain explicit approval and commit `scripts/usb_composition_verify.py` separately as commit 1b, or leave it uncommitted if the user requires only three physical commits; never mix it into eng-mode.
- [ ] Obtain explicit approval and commit exact gap-8 2 paths as commit 2.
- [ ] Obtain explicit approval and commit only this design path as commit 3.
- [ ] Confirm `git show --stat --oneline 1affffc` is 3 files / 30 insertions / 1 deletion and review all three diffs.
- [ ] Preserve the `validate_tc.py` §3-e non-string `runnable_reason` guard and the list/dict/int cases 20/21/22 while Task 2 refactors validation.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider`.
- [ ] Expect all baseline 1120 tests to pass; otherwise STOP before kernel edits.
- [ ] Confirm `git diff --cached --name-only` is empty before a new slice.

### Task 1: Deterministic drift ledger

**Files:**

- Create: `scripts/contract_drift_ledger.py`
- Create: `tests/test_contract_drift_ledger.py`
- Read: the 4 consumer and 2 producer sources listed in §2

**Interfaces:**

- `build_fixture_matrix() -> list[dict]`
- `probe_consumers(fixtures) -> list[dict]`
- `probe_producers(fixtures) -> list[dict]`
- `scan_corpora(groups) -> list[dict]`
- `write_outputs(rows, out_dir) -> tuple[Path, Path]`
- `main(argv: list[str] | None = None) -> int`

**RED cases:**

- `test_matrix_has_four_consumers_by_two_producers`
- `test_seed_alias_pairs_are_all_enumerated`
- `test_input_text_text_is_not_selector_alias`
- `test_key_sequence_delay_seconds_is_observed_not_normalized`
- `test_equal_duplicate_and_conflict_are_distinct`
- `test_excel_swipe_missing_endpoint_is_blocking`
- `test_shell_nonzero_with_stdout_is_blocking`
- `test_corpus_counts_are_3_25_2_1`
- `test_outputs_are_byte_deterministic`
- `test_source_hashes_unchanged_after_scan`

**Cycle:**

- [ ] Write RED tests with fake ADB and temporary producer inputs.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_contract_drift_ledger.py -q`; expect import/file failures.
- [ ] Implement only enough ledger code to satisfy the fixed CSV/SUMMARY contract.
- [ ] Re-run the same command; expect all ledger tests to pass.
- [ ] Run `venv/Scripts/python.exe scripts/contract_drift_ledger.py --out-dir reports/contract_drift --verify-determinism`.
- [ ] Run with `--fail-on-blocking`; expect exit 1 on the pre-adapter baseline and exact seed findings.
- [ ] Submit CSV/SUMMARY for Claude review; STOP before Task 2.

### Task 2: Canonical contract core and schema reuse

**Files:**

- Create: `src/execution_contract.py`
- Create: `tests/test_execution_contract.py`
- Modify: `tc_step_schema.json`
- Modify: `tc_prompts/STAGE2_COMPILE.md` (canonical emitted-field table와 shared derivation reference만 정렬; Step 4 의미 변경 금지)
- Modify: `validate_tc.py`
- Modify: `tests/test_validate_lint.py`
- Modify: `tests/test_execution_type.py`

**Key RED examples:**

```python
def test_text_alias_normalizes_without_mutating_source():
    raw = {"action": "verify_text", "text": "Wi-Fi"}
    result = normalize_step(raw, path="steps[0]")
    assert result.value == {"action": "verify_text", "target": "Wi-Fi"}
    assert raw == {"action": "verify_text", "text": "Wi-Fi"}


def test_conflicting_alias_is_blocking():
    result = normalize_step(
        {"action": "verify_text", "target": "A", "text": "B"},
        path="steps[0]",
    )
    assert result.blocking
    assert [f.code for f in result.findings] == ["ALIAS_CONFLICT"]


def test_seconds_conversion_is_exact_ms():
    result = normalize_step({"action": "wait", "seconds": 1.5}, path="steps[0]")
    assert result.value["duration"] == 1500


def test_input_text_text_is_not_selector_alias():
    raw = {"action": "input_text", "text": "fixture-input"}
    result = normalize_step(raw, path="steps[0]")
    assert result.value == raw
    assert "target" not in result.value
    assert result.findings == ()
```

Additional RED names:

- `test_normalization_is_idempotent`
- `test_tap_id_id_becomes_target`
- `test_keycode_becomes_key`
- `test_swipe_start_aliases_preserve_endpoint`
- `test_sub_millisecond_precision_loss_blocks`
- `test_screenshot_name_is_schema_defined`
- `test_verify_shell_timeout_is_documented_as_ms`
- `test_key_sequence_delay_seconds_is_observed_not_normalized`
- `test_validator_and_lint_share_normalized_wait`
- `test_schema_required_fields_come_from_shared_derivation`
- `test_runnable_reason_element_list_no_crash`
- `test_runnable_reason_element_dict_no_crash`
- `test_runnable_reason_element_int`

**Cycle:**

- [ ] Add RED tests; run the two new/affected test modules and observe expected failures.
- [ ] Implement dataclasses and pure normalization functions.
- [ ] Delegate action-required derivation and normalized lint input to the shared module.
- [ ] Update schema definitions without closing unrelated extra step fields.
- [ ] Verify the `input_text.text` RED stays canonical and the 3-e `runnable_reason` type guard from `1affffc` remains before enum/set membership.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_execution_contract.py tests/test_validate_lint.py tests/test_execution_type.py -q`.
- [ ] Re-run ledger; alias fixture rows should normalize but producer metadata defects remain blocking.

### Task 3: Loader and producer canonical modes

**Files:**

- Modify: `src/tc_loader.py`
- Modify: `tests/test_tc_loader.py`
- Modify: `src/excel_converter.py`
- Modify: `tests/test_excel_converter.py`
- Modify: `src/mmi_converter/compiler.py`
- Modify: `src/mmi_converter/exporter.py`
- Modify: `tests/test_mmi_compiler.py`
- Modify: `tests/test_exporter.py`

**RED cases:**

- loader:
  - `test_canonical_loader_returns_tc_name_without_name_duplicate`
  - `test_canonical_loader_rejects_alias_conflict`
  - `test_legacy_loader_behavior_is_unchanged`
- Excel:
  - `test_canonical_excel_emits_target_duration_key_and_tc_name`
  - `test_canonical_excel_requires_explicit_metadata`
  - `test_canonical_excel_swipe_requires_two_coordinate_pairs`
  - `test_legacy_excel_output_is_unchanged`
- MMI:
  - `test_canonical_compiler_emits_target_key_duration`
  - `test_canonical_exporter_emits_required_metadata`
  - `test_unresolved_mmi_export_is_not_runnable`
  - `test_legacy_mmi_output_is_unchanged`

**Cycle:**

- [ ] Add loader RED tests and implement `contract_mode` without changing default.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_tc_loader.py -q`.
- [ ] Add Excel RED tests, including the current endpoint failure.
- [ ] Read-only compare a user-approved real workbook swipe row against canonical `Parameter1="x,y"` + `Parameter2="x2,y2"`; record path/sheet/row and redacted cells. If no compatible real row exists, STOP producer promotion and request a sample.
- [ ] Implement canonical producer mode and explicit metadata requirement.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_excel_converter.py -q`.
- [ ] Add MMI RED tests and implement canonical compiler/exporter mode using STAGE2 metadata rules.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_mmi_compiler.py tests/test_exporter.py -q`.
- [ ] Re-run ledger with `--fail-on-blocking`; canonical producer fixtures must be clean while legacy fixtures remain measured.

### Task 4: Structured shell result and runner policy

**Files:**

- Modify: `src/adb.py`
- Modify: `tests/test_adb.py`
- Modify: `src/action_runner.py`
- Modify: `tests/test_action_runner.py`

**RED cases:**

```python
def test_shell_result_preserves_returncode_and_stderr():
    # subprocess mock returns rc=1, stdout="partial", stderr="denied"
    result = ADB().shell_result("cmd", timeout_s=5.0)
    assert (result.returncode, result.stdout, result.stderr) == (1, "partial", "denied")


def test_canonical_shell_nonzero_is_failure():
    adb = MagicMock()
    adb.shell_result.return_value = ShellResult("cmd", "partial", "denied", 1)
    result = ActionRunner(adb, tmp_path, contract_mode="canonical").run_step(
        {"action": "shell", "command": "cmd"}
    )
    assert result.passed is False
```

Additional RED names:

- `test_legacy_shell_still_returns_stdout`
- `test_canonical_verify_shell_does_not_pass_on_nonzero_stdout_match`
- `test_verify_shell_converts_5000ms_to_5_seconds`
- `test_canonical_runner_consumes_target_for_tap_id`
- `test_legacy_runner_alias_tests_are_unchanged`

**Cycle:**

- [ ] Add ADB RED tests; implement `ShellResult` and `shell_result` without changing `shell` return type.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_adb.py -q`.
- [ ] Add ActionRunner RED tests; implement canonical branch and timeout conversion.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_action_runner.py -q`.
- [ ] Re-run ledger; the unconditional-shell-success confirmed defect must move from blocking to fixed.

### Task 5: CLI pre-device gate and fail-closed abort

**Files:**

- Modify: `src/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `src/reporter.py` (required: `SUMMARY_SCHEMA_VERSION = 2`, `contract_mode`, `run_status`)
- Modify: `tests/test_reporter.py` (required schema-v2 and abort serialization coverage)

**RED cases:**

- `test_run_contract_mode_defaults_to_legacy`
- `test_run_accepts_canonical_contract_mode`
- `test_canonical_preflight_rejects_runnable_false_before_adb_constructed`
- `test_canonical_preflight_rejects_unresolved_before_adb_constructed`
- `test_one_invalid_file_prevents_all_valid_files_from_running`
- `test_canonical_nonverifier_failure_stops_remaining_steps_and_tcs`
- `test_canonical_failed_run_returns_nonzero_and_writes_partial_summary`
- `test_legacy_verifier_only_break_policy_is_unchanged`
- `test_report_records_contract_mode_and_abort_context`
- `test_summary_schema_version_two_records_contract_mode`
- `test_aborted_fail_closed_is_serialized_in_partial_summary`

**Cycle:**

- [ ] Write argparse and no-ADB-on-invalid RED tests.
- [ ] Split `cmd_run` into host preflight and device execution phases.
- [ ] Wire canonical loader/validator and all-file gate.
- [ ] Add run-level abort state and non-zero exit.
- [ ] Bump `SUMMARY_SCHEMA_VERSION` to 2 and serialize `contract_mode` plus `COMPLETED`/`ABORTED_FAIL_CLOSED` run status for every bundle.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/test_cli.py tests/test_reporter.py -q`.
- [ ] Run golden/exported host canonical checks; no device command is allowed in this task.

### Task 6: Regression and cutover evidence

**Files:** no new implementation file unless a failing test demonstrates a scoped defect.

**Steps:**

- [ ] Run all focused modules from Tasks 1–5.
- [ ] Run `venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider`.
- [ ] Require all original 1120 test nodeids plus all new tests; failures 0.
- [ ] Run `venv/Scripts/python.exe scripts/contract_drift_ledger.py --out-dir reports/contract_drift --verify-determinism --fail-on-blocking`.
- [ ] Require golden 3 and exported 25 semantic delta 0.
- [ ] Run redaction gate on CSV/SUMMARY commit candidates; raw/local-only artifacts remain excluded.
- [ ] Submit Slice 1a/1b evidence for Claude review; do not flip the default.

### Task 7: Existing THOR2_J SMOKE canonical differential + optional K authoring

**Primary files, read-only corpus:**

- Read: `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml`
- Read: `THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml`
- Modify/Create: no TC file in the primary host differential

**Host RED/differential:**

- `test_contract_ledger_counts_existing_thor2j_smoke_two`
- `test_thor2j_smoke_top_level_is_already_tc_name`
- `test_thor2j_smoke_legacy_and_canonical_semantics_match`
- `test_thor2j_smoke_source_hashes_unchanged`
- both tracked files `validate PASS`; ledger blocking 0; semantic delta 0

**Host steps:**

- [ ] Verify the two tracked J paths and historical evidence entries (`11/11`, `13/13`) without treating them as a new run.
- [ ] Run legacy/canonical loader projection and compare action order, commands, selectors, units, and metadata.
- [ ] Exercise schema-v2 reporter fixtures and no-ADB-on-invalid preflight.
- [ ] Record source hash/mtime unchanged and submit host differential evidence.

**Conditional ja-JP device gate:**

- [ ] Check whether the B27 ja-JP device is available; another session may own it. If unavailable, record `NOTE` + `미실행` and do not touch another device.
- [ ] Obtain explicit serial-pinned campaign approval before any device call.
- [ ] Reproduce legacy SMOKE 01→02 under §3.5, then replay canonical SMOKE 01→02 with contract mode as the only intended variable.
- [ ] Record `runtime PASS` only for an all-step pass, otherwise the exact failing step and stop point.
- [ ] Compare schema-v2 bundles and return to cutover review; do not default-flip automatically.

**Optional THOR2_K follow-up, separate campaign only:**

- [ ] If ko-KR coverage is requested, obtain separate approval for grounded K discovery/authoring before creating any K YAML.
- [ ] Treat K authoring/runtime as follow-up coverage, not Task 7 primary acceptance or kernel completion prerequisite.

---

## 11. Cutover Acceptance Matrix

| gate | required evidence | failure action |
|---|---|---|
| G0 governance | SSOT user decision + approved exact-path backlog commits (recommended 1a/1b/2/3) + `1affffc` review | no kernel edit |
| G0 tests | original 1120 tests/ regression baseline green (`tests/ 1120 passed`) | fix/review before Slice 0.5 |
| G0.5 ledger | deterministic 8-pair matrix + primary 3/25/2/1 corpus | ledger correction only |
| G1a normalizer | alias/idempotence/conflict tests + corpus semantic delta 0 | no runtime wiring |
| G1a producer | canonical Excel/MMI fixture schema-valid | producer stays legacy |
| G1b host gate | invalid invocation makes ADB calls 0 | canonical mode blocked |
| G1b runtime semantics | shell returncode respected + any-step abort tests | no device run |
| G2 host differential | existing J SMOKE `validate PASS` + legacy/canonical semantic delta 0 | mismatch이면 device run 금지 |
| G2 device conditional | available ja-JP device에서 legacy 재현 후 canonical replay `runtime PASS` | unavailable/FAIL이면 default remains legacy |
| Cutover | Claude review + user approval | stay opt-in |

Default canonical promotion requires every prior gate. Default promotion does not authorize legacy removal, corpus rewrite, qa-suite cutover, or new device campaigns.

---

## 12. Failure Modes and Stop Conditions

- ledger is nondeterministic or its source hashes change
- current corpus count differs from the declared baseline without an explained input change
- alias conflict is silently resolved
- `input_text.text`가 selector alias로 오정규화되어 `target`으로 이동·복제·유실됨
- `key_sequence.delay` seconds가 승인 없이 ms로 정규화됨
- producer invents metadata or missing swipe coordinates
- canonical preflight constructs ADB before all files validate
- `runnable:false` or unresolved TC reaches ActionRunner
- returncode non-zero is reported as success
- canonical mode changes legacy default behavior before promotion gate
- original baseline test node disappears or fails
- existing THOR2_J SMOKE is edited during the primary differential, or its already-canonical top-level `tc_name` is misreported as a legacy `name` fixture
- optional THOR2_K follow-up is treated as a kernel completion prerequisite or authored from ungrounded J literals
- kernel work blocks an open G1/Part B/SMOKE device window
- unrelated dirty/untracked paths enter staging

Any condition above causes fail-closed STOP at the current slice and an evidence-backed report. It does not authorize broad cleanup or rollback.

---

## 13. Proposed Governance Row Draft

This is text for the later Stage 0-approved repository policy file. It is **not** applied by this design task.

```markdown
| 2026-07-14 | execution contract / kernel | schema·validator·loader·runner와 Excel/MMI producer의 dialect plurality를 measure-first ledger로 고정한 뒤, ingress canonical normalization(1a)과 default-off fail-closed runtime gate(1b), 기존 THOR2_J Settings SMOKE canonical 차등검증(2)으로 단계 cutover하는 설계 승인. THOR2_K ko-KR은 필요 시 별도 후속이며 kernel 종결 선행조건이 아님. 구현은 exact-path backlog 분리 커밋·1120 baseline·별도 사용자 gate 후. 기존 §2.5 qa-suite proposed row를 supersede하지 않으며 tc-runner-side pre-cutover 안정화로 관계 설정 | §2.3·§3·§5.3; §2.5 proposed와 병행 | proposed |
```

If `CLAUDE.md` remains canonical, this row belongs in its §8.2 after approval. If `AGENTS.md` becomes canonical, migration decision must specify the one authoritative destination; duplicate manual rows are prohibited.

---

## 14. Review Checklist for This Design

- [x] Throughput guard and slice time-boxes included.
- [x] Slice 0.5 precedes code changes and covers 4 consumers × 2 producers.
- [x] All user-supplied alias/unit seeds and the two confirmed defects are represented.
- [x] Slice 1 is split into 1a normalization and 1b flag-gated runtime semantics.
- [x] `legacy` remains default until separate cutover approval.
- [x] governance SSOT decision, §2.5 relation, backlog flush, and `1affffc` review are explicit.
- [x] Existing tracked THOR2_J Settings SMOKE is the Slice 2 primary differential; historical 11/11·13/13 evidence, conditional ja-JP device gate, optional K follow-up, and ALT Part B unsuitability are distinguished.
- [x] `input_text.text` and deferred `key_sequence.delay` are fixed as action-scoped ledger/RED regressions.
- [x] Reporter schema v2 with `contract_mode` and `ABORTED_FAIL_CLOSED` is mandatory.
- [x] file-by-file RED cases and exact focused/tests-regression (`pytest tests/`) commands are included.
- [x] 1120 baseline is distinguished as committed evidence/current collect-only, not newly claimed pass evidence.
- [x] no code, TC, device, commit, push, or staging is authorized by this document.

Next gate: Claude reviews this design. Implementation planning/execution begins only after the user accepts that review and separately opens Stage 0.
