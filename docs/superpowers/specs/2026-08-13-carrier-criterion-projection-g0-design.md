# Carrier Criterion Contract & Projection G0 설계

> 상태: 사용자 승인 설계를 문서화한 정본. 이 문서는 계약·전환 경계를 확정하며 코드, CTF, 원본 corpus, runner 동작은 변경하지 않는다.
>
> 작성일: 2026-08-13

## 0. 결정 요약

이통3사 규격서·시험절차서를 tc-runner에 내재화할 때 `expected.type`,
`feasibility`, `metadata.runnable` 한 축으로 규격 의미와 현재 러너 준비도를 함께
표현하지 않는다.

G0는 다음 네 경계를 도입한다.

1. **source criterion contract** — 사업자 원문에서 읽히는 판정 의미와 출처만 보존한다.
2. **oracle provider catalog** — 러너·도구·단말에 종속된 관찰 구현과 qualification을 누적한다.
3. **projection context** — 대상 단말, 시험 환경, 정책, provider capability를 시점별로 결박한다.
4. **readiness vector** — source/procedure/execution/verdict 준비도를 서로 독립 계산한다.

최종 상태는 기존 `expected.type × feasibility` 계약 제거다. 전환은 즉시 strict flip이
아니라 `측정 원장 → shadow v2 → differential → consistency-set cutover` 순서로 한다.
이는 canonical execution contract에서 검증된 measure-first staged cutover를 재사용한다.

## 1. 검토 범위와 권위

### 1.1 교차 검토 범위

설계는 다음 세 저장소의 현재 정책, tracked 코드·테스트, 주요 설계·실패 기록과 현재
dirty state를 대조해 확정했다.

| 저장소 | 확인한 역할 | 설계에 반영한 실패 교훈 |
|---|---|---|
| `tc-runner` | STAGE1/2, tc-step runner, catalog, QCAT/SIP 도구, ALT Basic 실패 원장, provenance | cue 과승격, expected 계약 drift, 미실측 literal 승격, source join 누락, hard cutover 위험 |
| `thor2j-tc-appium` | FocusRule 151 TC, recovery gate, device-fit, verifier factory, 2-run promotion | pure-ADB와 session runner 결과 불일치, false-promote 방지, rollback·sole-device·2-run 필요, input-token clustering 실패 |
| `qa-suite` | 최종 통합 목표, 계약·결과 경계, migration authority ledger | verified snapshot과 writer 권위 혼동, consistency-set 부분 refresh 실패, 공통 orchestrator 조기 도입 금지 |

대용량 raw screenshot·원본 modem log를 모두 재판독한 것은 아니다. 계약 결정을 바꿀 수
있는 tracked 설계, 코드, 테스트, 결과 원장, provenance, 현재 diff를 검토 범위로 삼았다.

### 1.2 현재 writer

G0의 최초 writer는 `tc-runner`다.

- `qa-suite`는 통합 목표지만 코드·데이터 cutover가 완료되지 않았다.
- `qa-suite`의 tc-step schema와 runner는 verified snapshot이며 현재 `tc-runner`와 hash가 다르다.
- `thor2j-tc-appium`은 campaign·Appium 실행의 현재 writer다.
- cross-repo Python import와 cross-commit은 금지한다.
- qa-suite 반영은 tc-runner에서 검증된 consistency set을 provenance와 함께 refresh한 뒤,
  별도 cutover 조건을 충족할 때 수행한다.

## 2. 측정 baseline

### 2.1 LG U+ 현재 CTF

| 측정값 | 값 |
|---|---:|
| TC | 28 |
| procedure step | 196 |
| expected atom | 232 |
| `verify_shell × element_presence` | 124 |
| `verify_text × element_presence` | 45 |
| `verify_shell × infeasible` | 13 |
| `manual_required × infeasible` | 33 |
| `verify_text × text_literal` | 17 |
| 현재 계약 정합 | 50/232 |
| 현재 계약 위반 | 182/232 |

현재 `0/28 runnable 후보`는 schema 합법 blocker 기준으로 재현되지만, readiness의 모든
의미를 대표하지 않는다. `FIXTURE_REQUIRED 28`, `MUTATION_UNMANAGED 26`,
`INFEASIBLE_VERIFIER 23`은 source 사실, campaign 환경, runner capability를 한 결과에
혼합한다.

### 2.2 SKT 신규 시험절차서

`새 폴더 (2)/SKT_시험절차서_최신/`에는 legacy `.xls` 66건이 있다. G0 표현력 검증에
사용할 고정 표본은 다음 8건이다.

- `5G DSDS 1.0.xls`
- `USIM 3.01 (2).xls`
- `DATA 3.01.xls`
- `5G NR 1.20.xls`
- `SD QI_HD Voice CAF 3.13.xls`
- `SD QI_HD Voice_RTCP 1.02.xls`
- `Field Test 1.21(5G).xls`
- `메시지 3.01.xls`

표본은 UI literal 외에 DUT·대향 단말·서버·망·기준 단말 endpoint, Pcap+DM+call 복합
판정, duration, ratio, formula, relative comparison, 대안 경로, `TBD`를 포함한다.

### 2.3 KT paired source 표본

requirement와 SAT의 역할을 분리 검증하기 위해 다음 두 쌍을 고정 표본으로 사용한다.

- `KT 5G NSA 단말 기능 규격 V1.3.0(배포용)_20260508.pdf`
  ↔ `KT 5G NSA 단말 기능 SAT 규격 V1.3.0(배포용)_20260508.pdf`
- `KT 5G SA 단말 기능 규격 V1.6.0(배포용)_20260429.pdf`
  ↔ `KT 5G SA 단말 기능 SAT 규격 V1.6.0(배포용)_20260429.pdf`

requirement는 normativity·요구 의미, SAT는 procedure·판정 관찰 위치의 출처로 보존한다.
둘 중 하나를 다른 하나로 덮어쓰지 않는다.

## 3. 목표와 비목표

### 3.1 목표

- 사업자 판정문을 runner action과 분리해 무손실 정규화한다.
- 한 TC 안의 UI, OS, modem, APDU, network, instrument, physical 근거를 criterion 단위로 표현한다.
- 현재 runner·단말·시험대 상태가 바뀌어도 CTF를 다시 쓰지 않고 projection만 재계산한다.
- source pending, action compile, environment availability, verdict capability를 독립적으로 보고한다.
- raw evidence에서 최종 claim까지 hash와 변환 관계를 추적한다.
- 기존 232 expected의 drop·중복·임의 강등을 기계적으로 차단한다.

### 3.2 비목표

G0는 다음 기능을 구현하지 않는다.

- QXDM capture, QCAT COM 자동 실행, modem message decoder
- multi-device orchestration, campaign scheduler, 장비 예약
- SIM port·airplane action, reboot crossing
- fixture seed와 teardown/finally runtime
- 범용 formula 언어 또는 임의 expression evaluator
- qa-suite 공통 orchestrator
- source criterion의 PASS/FAIL을 직접 판정하는 runtime

위 항목은 G0 contract를 소비하는 후속 티켓이다.

## 4. 핵심 용어

| 용어 | 정의 |
|---|---|
| source document | 규격서·시험절차서·외부 참조 문서 한 파일 |
| source case | 사업자 문서가 정의한 한 시험 항목 |
| procedure step | 시험 수행 동작 또는 관찰 시점 |
| criterion | 독립적으로 PASS/FAIL/INCONCLUSIVE 판정 가능한 최소 규범 단위 |
| criterion group | 여러 criterion의 ALL/ANY/AT_LEAST/UNORDERED_ALL 관계 |
| evidence requirement | criterion 판정에 요구되는 관찰 영역과 허용 취득 경로 |
| oracle provider | raw/derived artifact를 criterion verdict fragment로 변환하는 구현 |
| oracle binding | 특정 criterion과 provider의 호환·qualification 관계 |
| projection context | runner·target·environment·policy snapshot의 hash 결박 |
| readiness vector | source/procedure/execution/verdict 네 독립 상태 |
| diagnostic criterion | campaign이 보강 관찰을 위해 추가한 비사업자 criterion |

## 5. Source Criterion Contract v2

### 5.1 top-level shape

```yaml
schema_version: 2
case_id: LGU5G_04_6_DATA_LINE_SWITCH
title: 모바일 데이터 설정 회선 변경 시험
source_case:
  carrier: LGU+
  document_id: LGU_CD20_5G_TEST_V02_00_00
  document_path: 새 폴더 (2)/LGU+/LGU+_5G_20260728/CD_20_LGU_디바이스_5G_시험절차서_V02_00_00.html
  document_sha256: fc909067efe913479660161a97de4def46a7ba806fa3f41c9498724d37e3259b
  location:
    sheet: null
    section: "4.6"
    physical_row: null
preconditions: []
procedure_steps: []
criteria: []
criterion_groups: []
source_warnings: []
```

`document_path`는 repo root 상대경로다. 절대경로는 저장하지 않는다. SHA-256은 축약하지
않고 `^[0-9a-f]{64}$`로 저장한다. Excel은 `sheet`와 `physical_row`, PDF/HTML은
`section`과 page/span을 사용한다.

`source_case_sha256`은 top-level 문서에서 volatile projection/runtime 필드를 제외한 v2
source case 전체를 canonical JSON(UTF-8, key lexical sort, 배열 순서 보존, 공백 없음)으로
직렬화한 bytes의 SHA-256이다. canonicalization version은 schema version에 결박한다.
이 문서의 `sha256(...)` 표기는 계산 규칙을 나타내는 설계 표기다. 실제 YAML/JSON 산출물은
표현식을 저장하지 않고 계산된 64자리 lowercase hex만 저장한다.

### 5.2 source trace

모든 precondition, step, criterion은 다음 구조를 가진다.

```yaml
source_trace:
  document_id: LGU_CD20_5G_TEST_V02_00_00
  document_sha256: fc909067efe913479660161a97de4def46a7ba806fa3f41c9498724d37e3259b
  location:
    sheet: null
    section: "4.6 판정2"
    page: null
    physical_row: null
    span: "판정1 SIM A 회선이 RRC Connected State로 천이하여 모바일 데이터 PDN에 대한 ESM 'PDN disconnect' 절차를 완료하는지 확인한다."
  extraction:
    method: HTML_TEXT
    extractor_version: carrier-source-v1
```

`span`은 원문을 보존하되 저작권·보안 정책상 전체 문서 복제물이 되지 않는 판정 단위로
한정한다. 원본 파일 hash가 변하면 이전 source trace는 자동 갱신하지 않고 drift로 차단한다.

### 5.3 precondition

```yaml
- precondition_id: P001
  raw_text: "SIM 포트1, 포트2 각각 개통 회선"
  kind: INVENTORY
  establishment: PREEXISTING
  subject: "DUT.SIM_PORT[1..2].SUBSCRIPTION"
  source_trace: {}
```

enum:

- `kind`: `CAPABILITY | INVENTORY | STATE | PRIOR_CASE | EXTERNAL_SERVICE | POLICY`
- `establishment`: `PREEXISTING | PROCEDURE_ESTABLISHED | SOURCE_UNSPECIFIED`

CTF에는 `blocking`, 현재 시험대의 충족 여부, 담당자, auto-seed 가능 여부를 저장하지
않는다. 모든 source precondition은 요구사항이며, 충족·provision 가능성은 projection이
평가한다.

### 5.4 procedure step

```yaml
- step_id: S003
  raw_text: "SIM B 회선을 모바일 데이터 설정 회선으로 변경한다."
  semantic_role: ACTION
  resolution: RESOLVED
  intent:
    kind: CHANGE_DEFAULT_DATA_SUBSCRIPTION
    target: DUT.SUBSCRIPTION.B
    value: DEFAULT_DATA
  effects:
    - effect_kind: STATE_MUTATION
      target: DUT.DEFAULT_DATA_SUBSCRIPTION
      reversibility: REVERSIBLE
      basis: ANALYST_INFERRED
  criterion_refs: [C001, C002]
  source_trace: {}
```

enum:

- `semantic_role`: `SETUP | ACTION | OBSERVE | RESTORE`
- `resolution`: `RESOLVED | SOURCE_PENDING | AMBIGUOUS`
- `effect_kind`: `STATE_MUTATION | EXTERNAL_SIDE_EFFECT | DESTRUCTIVE_ACTION | NONE`
- `reversibility`: `REVERSIBLE | IRREVERSIBLE | UNKNOWN`
- `basis`: `SOURCE_EXPLICIT | ANALYST_INFERRED`

`intent.kind`는 source semantic registry의 값이다. `tap_text`, `verify_shell`, selector,
ADB command 같은 runner action은 v2 CTF에 넣지 않는다. 확정되지 않은 intent parameter를
추측하지 않고 `resolution: AMBIGUOUS`와 source warning으로 남긴다.

### 5.5 criterion

```yaml
- criterion_id: C001
  raw_text: "SIM A의 모바일 데이터 PDN disconnect 절차가 완료된다."
  normativity: REQUIRED
  resolution: RESOLVED
  endpoint: DUT_MODEM
  subject_kind: PROTOCOL_MESSAGE
  assertion:
    operator: SEQUENCE_CONTAINS
    expected:
      registry_ref: 3GPP_ESM_PDN_DISCONNECT_SEQUENCE
  evidence_requirements:
    mode: ANY
    items:
      - domain: MODEM
        acquisition_hint: QXDM
        basis: ANALYST_INFERRED
      - domain: NETWORK
        acquisition_hint: NETWORK_TRACE
        basis: ANALYST_INFERRED
  source_trace: {}
```

enum:

- `normativity`: `REQUIRED | INFORMATIVE`
- `resolution`: `RESOLVED | SOURCE_PENDING | AMBIGUOUS`
- `endpoint`: `DUT_UI | DUT_OS | DUT_MODEM | DUT_UICC | PEER_DEVICE | NETWORK_CORE | SERVER | INSTRUMENT | OPERATOR_OBSERVATION`
- `subject_kind`: `TEXT | ELEMENT_STATE | OS_STATE | PROTOCOL_MESSAGE | PROTOCOL_IE | NETWORK_FLOW | METRIC | DURATION | RATIO | FORMULA_RESULT | STATE_TRANSITION | USER_OBSERVABLE`
- `evidence_requirements.mode`: `ALL | ANY`
- `domain`: `UI | OS_STATE | MODEM | APDU | NETWORK | INSTRUMENT | PHYSICAL`
- `basis`: `SOURCE_EXPLICIT | ANALYST_INFERRED | UNSPECIFIED`

`acquisition_hint`는 open registry다. 최초 registry는 다음 값을 정의한다.

`UIAUTOMATOR | SCREENSHOT | ADB_SHELL | DUMPSYS | LOGCAT | QXDM | QCAT | APDU_TRACE | PCAP | NETWORK_TRACE | LAB_INSTRUMENT | OPERATOR`

`domain`은 관찰 영역이고 `acquisition_hint`는 취득 경로다. `UI`와 `ADB`를 동일 enum에
넣지 않는다.

### 5.6 assertion registry

G0는 임의 expression을 실행하지 않는다. 다음 operator와 typed payload만 허용한다.

| operator | payload 의미 |
|---|---|
| `PRESENT` / `ABSENT` | 대상의 존재·부재 |
| `EQUALS` / `CONTAINS` / `MATCHES_PATTERN` / `IN_SET` | text·enum 비교 |
| `GTE` / `LTE` / `BETWEEN` | 수치 경계 |
| `COUNT_EQUALS` / `COUNT_GTE` | event 개수 |
| `DURATION_GTE` | 지속시간 |
| `RATIO_GTE` | 분자/분모와 임계값 |
| `SEQUENCE_CONTAINS` | 순서가 의미 있는 event sequence |
| `UNORDERED_ALL` | 순서 무관 event 집합 |
| `STATE_TRANSITION` | before→after 상태 변화 |
| `RELATIVE_COMPARE` | 기준 단말·이전 측정값과의 비교 |
| `FORMULA_COMPARE` | 등록된 formula 결과와 threshold 비교 |

`MATCHES_PATTERN`은 source literal을 정규식으로 임의 승격하지 않는다. source가 pattern을
명시했거나 사람이 승인한 registry entry만 참조한다. `FORMULA_COMPARE`는
`formula_ref`, 입력 단위, rounding mode, comparator를 요구한다. YAML 문자열을 코드로
평가하지 않는다.

criterion assertion의 `UNORDERED_ALL`은 한 criterion 내부 event set의 정합을 뜻한다.
criterion group의 `UNORDERED_ALL`은 여러 criterion verdict의 순서 무관 conjunction이다.
checker는 두 위치의 payload schema를 별도로 검증한다.

### 5.7 criterion group

```yaml
- group_id: G001
  operator: UNORDERED_ALL
  members: [C002, C003]
  min_pass: null
  normativity: REQUIRED
  source_trace: {}
```

enum:

- `operator`: `ALL | ANY | AT_LEAST | UNORDERED_ALL`
- `AT_LEAST`만 `min_pass` 양의 정수를 요구한다.
- group member는 criterion 또는 하위 group ID다.
- cycle, dangling reference, 중복 member는 checker가 fail-closed한다.

원문의 복합 판정은 독립적으로 judge 가능한 경우에만 atomize한다. atomization 전후 관계는
migration ledger에 `legacy_expected_id → criterion_ids/group_id`로 기록한다.

### 5.8 immutable ID allocation

`document_id`, `case_id`, `precondition_id`, `step_id`, `criterion_id`, `group_id`는 한 번
발급하면 rename·삽입·재정렬 때 바꾸거나 재사용하지 않는다.

- case 내부 ID는 각 prefix별 다음 미사용 단조 증가 번호(`P001`, `S001`, `C001`, `G001`)
  를 발급한다.
- 원문 중간 삽입도 기존 ID를 renumber하지 않고 새 max+1을 쓴다.
- 원문 순서는 별도 `source_order` 정수로 저장하며 identity로 사용하지 않는다.
- 삭제된 source item은 ledger에서 tombstone 처리하고 해당 ID를 재사용하지 않는다.
- atomize한 criterion은 새 ID를 받고 parent legacy expected ID와 source span을 migration
  ledger에 모두 유지한다.

### 5.9 source pending 처리

`TBD`, “확인 필요”, 미수령 참조, 상충 판정은 삭제하거나 informative로 강등하지 않는다.

- required 판정이면 `normativity: REQUIRED`
- `resolution: SOURCE_PENDING` 또는 `AMBIGUOUS`
- 미수령 문서 ID와 질문을 `source_warnings`에 기록
- projection 결과 `source_ready=false`
- 사업자 회신 또는 문서 수령 후 source hash와 adjudication provenance를 남겨 해소

## 6. normativity와 verdict role 분리

`core/supplemental`은 CTF 필드가 아니다.

projection의 `verdict_role` 파생 규칙은 다음과 같다.

1. source `REQUIRED` criterion → `REQUIRED`
2. source `INFORMATIVE` criterion → `NOTE`
3. campaign overlay가 추가한 diagnostic criterion → `SUPPLEMENTAL` 또는 `NOTE`
4. source `REQUIRED` → `SUPPLEMENTAL/NOTE` 자동 강등 금지
5. 강등은 사업자 waiver 식별자, 승인자, 적용 버전, source hash를 가진 명시적 waiver overlay만 허용

3-way ground truth처럼 DUT UI 판정을 보강하는 ADB·interface 관찰은 source criterion을
바꾸지 않고 diagnostic overlay로 추가한다.

```yaml
overlay_schema_version: 1
overlay_id: LGU5G_04_6_DIAGNOSTICS_V1
case_id: LGU5G_04_6_DATA_LINE_SWITCH
source_case_sha256: sha256(canonical_source_case_json)
diagnostic_criteria:
  - criterion_id: D-ADB-PDN-001
    verdict_role: SUPPLEMENTAL
    subject_kind: OS_STATE
    assertion: {operator: STATE_TRANSITION, expected: "interface_up"}
```

## 7. Oracle Provider Catalog

### 7.1 provider와 binding

provider는 독립 도구 또는 runner adapter다. criterion은 provider 이름을 알지 못한다.

```yaml
provider_schema_version: 1
provider_id: QCAT_SIP_DIGEST
provider_version: "1"
runner_family: OFFLINE_TOOL
consumes:
  domains: [MODEM]
  media_types: [application/vnd.qualcomm.qcat-text]
produces: criterion-verdict-fragment-v1
operational_constraints:
  - ONLINE_QXDM_CAPTURE_REQUIRED_FOR_0X156E
```

```yaml
binding_schema_version: 1
binding_id: LGU_4_7_C001_QCAT_SIP_V1
case_id: LGU5G_04_7_DATA_SWITCH_DURING_CALL
criterion_id: C001
provider_id: QCAT_SIP_DIGEST
binding_state: DESIGNED
target_fit: UNKNOWN
qualification_refs: []
limitations:
  - OFFLINE_USER_QMDL_HAS_NO_0X156E
```

enum:

- `runner_family`: `TC_STEP | APPIUM | OFFLINE_TOOL | MANUAL`
- `binding_state`: `UNBOUND | DESIGNED | HOST_VALIDATED | DEVICE_QUALIFIED`
- `target_fit`: `UNKNOWN | FIT | LIMITED | ABSENT | SPEC_PENDING`

`HOST_VALIDATED`는 parser unit test·dry-run을 뜻하며 verdict 준비 근거가 아니다.
`DEVICE_QUALIFIED`는 실제 target context에서 provider가 required observation을 얻고
false-positive negative control을 통과한 상태다. 아래 ODIN2 qualification은 provider
자체의 선행 자산을 보여줄 뿐 LGU 4.7 target binding을 승격시키지 않는다.

### 7.2 qualification record

qualification은 provider 선언에 내장하지 않고 append-only record로 저장한다.

```yaml
qualification_id: QUAL-20260616-ODIN2-IMS
provider_id: QCAT_SIP_DIGEST
target_profile_id: ODIN2_USER_BUILD
context_digest: sha256(canonical_projection_context_json)
runs: 2
positive_controls: 2
negative_controls: 1
rollback_verified: true
evidence_manifest_sha256: sha256(evidence_manifest_bytes)
result: QUALIFIED
```

한 단말·capture mode에서 qualified된 provider를 다른 target·capture mode로 자동 전이하지
않는다. thor2j의 pure-ADB와 session-backed 결과 불일치처럼 실행 context가 의미를 바꿀
수 있으므로 `context_digest`가 다르면 별도 qualification이다.

## 8. Projection Context

G0는 qa-suite에서 미확정인 전역 device-profile schema를 선점하지 않는다. 다음 최소
reference 계약만 정의한다.

```yaml
projection_context_version: 1
context_id: THOR3_LGU_LAB_A_20260813
runner:
  family: TC_STEP
  version: "1.4.0"
  capability_sha256: sha256(runner_capability_bytes)
target:
  profile_id: THOR3_LGU_SANITIZED
  profile_sha256: sha256(target_profile_bytes)
environment:
  inventory_snapshot_id: LAB_A_20260813
  inventory_snapshot_sha256: sha256(inventory_snapshot_bytes)
  policy_profile_sha256: sha256(policy_profile_bytes)
qualification_policy:
  required_runs: 2
  rollback_required: true
```

- tracked target profile에는 serial·전화번호·credential을 저장하지 않는다.
- 실제 device identity와 lab inventory raw 값은 local-only다.
- projection에는 stable alias와 sanitized hash만 기록한다.
- fixture 상시 비치 여부는 environment inventory에 기록하며 CTF를 바꾸지 않는다.
- multi-device, SIM, network core, CBCF, QXDM, QCAT, instrument availability도 inventory item이다.

`context_digest`는 위 projection context에서 `context_id` 같은 표시용 alias를 제외하고
runner capability hash, target profile hash, inventory snapshot hash, policy profile hash,
qualification policy를 canonical JSON(UTF-8, key lexical sort, 배열 순서 보존, 공백 없음)으로
직렬화한 bytes의 SHA-256이다. qualification 의미에 영향을 주는 필드를 추가하면
`projection_context_version`을 올린다.

## 9. Readiness Vector

### 9.1 결과 구조

```yaml
projection_schema_version: 1
case_id: LGU5G_04_6_DATA_LINE_SWITCH
source_case_sha256: sha256(canonical_source_case_json)
context_digest: sha256(canonical_projection_context_json)
readiness:
  source_ready: false
  procedure_compile_ready: false
  execution_ready: false
  verdict_ready: false
blockers: []
diagnostics: []
```

### 9.2 계산 규칙

`source_ready=true` iff:

- 모든 required criterion이 `RESOLVED`
- required group의 모든 member 정의가 `RESOLVED`; `ANY`도 미확정 대안이 허용 의미를
  바꿀 수 있으므로 source 단계에서 생략하지 않음
- 모든 required source/reference document가 존재하고 hash가 일치
- criterion/group reference가 완전하고 cycle이 없음

`procedure_compile_ready=true` iff:

- 모든 procedure step이 runner action, explicit manual route 또는 external route로 추측 없이 binding됨
- selector·command·parameter unresolved가 0
- procedure step drop이 0

`execution_ready=true` iff:

- `procedure_compile_ready=true`
- 모든 required precondition이 현재 충족됐거나, 현재 context에서 qualified된 provision
  action이 compiled SETUP에 포함됨
- 필요한 endpoint·resource가 available
- policy block이 없음
- mutation이 있으면 rollback/teardown path가 해당 target context에서 qualified

`verdict_ready=true` iff:

- `source_ready=true`
- 모든 required criterion/group에 현재 context와 호환되는 `DEVICE_QUALIFIED` binding이 있음
- required evidence domain을 실제로 획득할 resource가 available
- group이 현재 binding 조합으로 만족 가능

네 값은 서로 대체하지 않는다. 예를 들어 procedure execution은 가능하지만 modem oracle이
없으면 `execution_ready=true`, `verdict_ready=false`가 가능하다. source가 unresolved면
다른 세 축이 준비돼도 인증 verdict를 만들 수 없다.

campaign 실행 후보는 별도 파생값
`source_ready && procedure_compile_ready && execution_ready && verdict_ready`로만 계산한다.
이 값을 CTF의 `runnable` 필드로 역기록하지 않으며, 네 축 중 어느 실패도 다른 축의 상태로
덮지 않는다.

### 9.3 blocker vocabulary

blocker는 축별 namespace를 가진다.

| 축 | code |
|---|---|
| source | `SRC_REFERENCE_MISSING`, `SRC_HASH_DRIFT`, `SRC_CRITERION_PENDING`, `SRC_CRITERION_AMBIGUOUS`, `SRC_GROUP_INVALID` |
| procedure | `PROC_ACTION_UNBOUND`, `PROC_SELECTOR_UNRESOLVED`, `PROC_PARAMETER_UNRESOLVED`, `PROC_STEP_DROPPED` |
| execution | `EXEC_PRECONDITION_UNSATISFIED`, `EXEC_RESOURCE_UNAVAILABLE`, `EXEC_POLICY_BLOCKED`, `EXEC_ROLLBACK_UNQUALIFIED`, `EXEC_ENDPOINT_UNAVAILABLE` |
| verdict | `VERDICT_ORACLE_UNBOUND`, `VERDICT_ORACLE_NOT_DEVICE_QUALIFIED`, `VERDICT_EVIDENCE_UNAVAILABLE`, `VERDICT_GROUP_UNSATISFIABLE` |

`MULTI_DEVICE`, `EXTERNAL_EVENT`, `UNSUPPORTED_STEP` 같은 관찰은 대응 blocker의 detail 또는
비차단 diagnostic으로 표현한다. 새로운 code는 schema·checker·projection·테스트를 같은
consistency set으로 바꿀 때만 추가한다.

### 9.4 4.6 판정

`LGU5G_04_6_DATA_LINE_SWITCH`는 G0 기준에서 다음처럼 해석한다.

- procedure vertical slice 후보: 맞음
- ADB OS-state supplemental observation 후보: 맞음
- ESM PDN disconnect/connect와 TAU를 ADB만으로 required verdict: 불가
- MODEM 또는 NETWORK의 device-qualified binding 없이는 `verdict_ready=false`

따라서 “G1 없이 부분 인증 PASS”를 허용하지 않는다. ADB 관찰은 source required criterion을
대체하지 않는 supplemental diagnostic이다.

## 10. Criterion Verdict Fragment

runner를 합치지 않고 결과 artifact만 공통 계약으로 결속한다.

```yaml
fragment_schema_version: 1
run_id: 20260813T120000Z
case_id: LGU5G_04_6_DATA_LINE_SWITCH
criterion_id: C001
binding_id: LGU_4_6_C001_MODEM_V1
provider_id: MODEM_ESM_SEQUENCE
context_digest: sha256(canonical_projection_context_json)
status: PASS
observed_at: "2026-08-13T12:00:00+09:00"
observation:
  registry_ref: 3GPP_ESM_PDN_DISCONNECT_SEQUENCE
  matched_event_count: 3
evidence:
  - artifact_id: A001
    relative_path: derived/modem/c001_digest.json
    sha256: sha256(artifact_bytes)
    media_type: application/json
    redaction_status: REDACTED
    derived_from: [RAW-QXDM-001, QCAT-TEXT-001]
```

enum `status`:

`PASS | FAIL | INCONCLUSIVE | NOT_OBSERVED | INFRA_FAILURE`

- `INFRA_FAILURE`는 criterion FAIL이 아니다.
- required criterion이 `INCONCLUSIVE`, `NOT_OBSERVED`, `INFRA_FAILURE`면 campaign verdict는 PASS가 아니다.
- source case `runtime PASS`는 procedure 성공, required criterion group 전부 PASS,
  rollback 성공이 모두 성립할 때만 가능하다.
- supplemental criterion 미수집은 NOTE로 남고 required PASS를 차단하지 않는다.

## 11. Evidence provenance

### 11.1 source provenance

- source file full SHA-256
- PDF page/section 또는 Excel sheet/physical row
- loader가 해석한 canonical row content hash
- extraction method와 version
- adjudication·waiver의 승인 provenance

파일명, section number, 배열 위치만으로 identity를 만들지 않는다. 절 삽입·row 이동으로
identity가 바뀌지 않도록 immutable `document_id`, `case_id`, `criterion_id`를 사용한다.

### 11.2 runtime artifact chain

raw artifact는 local-only 원칙을 유지한다. tracked 가능한 것은 redacted digest와 manifest다.

QCAT 예시:

```text
online QXDM hdf
  -> filtered ISF (QCAT version + code set + SHA)
  -> QCAT text (0x156E + SHA)
  -> ims_sip_digest JSON (tool version + SHA)
  -> criterion verdict fragment
```

각 변환은 producer/version, input artifact IDs, output SHA-256, exit status를 남긴다.
offline USER `.qmdl`에 0x156E가 없다는 limitation을 success로 세탁하지 않고
`NOT_OBSERVED` 또는 provider incompatibility로 처리한다.

## 12. 저장소 경계

| 책임 | 현재 writer | G0 산출 위치 원칙 |
|---|---|---|
| corpus intake·source hash·CTF v2·migration ledger | tc-runner | `KR3_Carrier_Requirements/` |
| criterion schema·checker·static projection | tc-runner | KR3 도구/계약 모듈, 기존 runtime schema와 분리 |
| oracle analyzer·binding·qualification catalog | tc-runner | 학습·핀포인트 자산으로 누적 |
| campaign 실행·multi-device·2-run promotion | thor2j-tc-appium | campaign manifest와 runner 소유 |
| 공통 result contract·최종 통합 | qa-suite | cutover 후, provenance refresh |

G0 projection은 read-only static synthesis다. device를 점유하거나 runner를 dispatch하는
orchestrator가 아니다.

## 13. 전환 설계

G0는 네 개의 독립 검증 슬라이스로 구현한다. 각 슬라이스는 별도 reviewer gate와
host-only acceptance를 가진다.

### G0-A — Source intake & immutable ledger

산출:

- 절대경로가 없는 corpus source registry
- PDF/HTML/XLS full SHA-256
- SKT `.xls` 66건 intake와 sheet/row inventory
- LGU legacy expected 232개 immutable ID ledger
- requirement↔procedure/SAT relation

acceptance:

- LGU 232/232 ledgered, 중복·drop 0
- SKT 66/66 parse/read disposition 존재
- KT 고정 2쌍 relation 존재
- 두 번 실행 결과 byte-identical
- source hash·mtime 변화 0

### G0-B — Criterion Contract v2 shadow

산출:

- v2 schema와 fail-closed checker
- assertion/evidence registry
- legacy 232 → v2 criterion/group migration ledger
- LGU 28 shadow v2 문서
- SKT 8표본·KT 2쌍 표현력 fixtures

acceptance:

- legacy 232/232가 하나 이상의 criterion 또는 group에 조인
- silent drop·untraced atomization·dangling group 0
- `verify_shell`, `verify_text`, `feasibility`, `runnable`, `oracle_status`, `core/supplemental`이 v2 CTF에 0
- required source pending이 `source_ready=true`가 되는 반례 0
- 기존 STAGE1/runner 행위 변화 0

### G0-C — Provider catalog & static projection

산출:

- provider/binding/qualification schemas
- projection context 최소 계약
- readiness vector와 blocker registry
- criterion verdict fragment schema
- 기존 runner capability를 adapter로 읽는 projection

acceptance:

- runner version 변경 시 CTF hash 변화 0, projection만 변화
- fixture standing precondition 변경 시 CTF hash 변화 0
- HOST_VALIDATED binding이 verdict-ready를 true로 만드는 반례 0
- source required criterion 자동 강등 0
- projection 두 번 실행 byte-identical
- device/ADB call 0

### G0-D — Consistency-set cutover

선행조건:

- G0-A/B/C acceptance 전부 통과
- LGU 28 differential에서 source 의미 delta 0
- SKT·KT 표본이 v2 checker를 통과
- 모든 consumer inventory가 작성됨

cutover consistency set:

- CTF schema/definition
- STAGE1 prompt
- STAGE1 checker
- STAGE2 prompt/adapter
- projection
- migration ledger
- tests와 문서

한 항목만 먼저 바꾸는 partial cutover를 금지한다. cutover 후 legacy expected 계약을
제거하며 무기한 dual-write는 유지하지 않는다. qa-suite refresh는 이 cutover 이후 별도
authority-ledger 절차로 수행한다.

## 14. 후속 기능 순서

G0 이후 runtime 기능은 독립 설계·승인을 받는다.

1. rollback/finally teardown executor
2. airplane·SIM port action adapter
3. reboot-crossing lifecycle
4. online QXDM capture와 modem oracle provider
5. multi-device/campaign orchestration

첫 실기 vertical slice는 4.6 procedure + ADB supplemental observation으로 사용할 수 있으나,
modem provider 전에는 인증 `runtime PASS` 대상으로 승격하지 않는다.

## 15. 실패 조건과 stop rule

다음 중 하나가 발생하면 현재 슬라이스에서 중단한다.

- source 원본 hash 또는 mtime이 도구 실행으로 변함
- legacy expected 232개 중 join되지 않은 항목 존재
- atomization 후 원문 span·parent mapping 유실
- source required criterion이 supplemental/note로 자동 강등
- current runner capability가 CTF에 기록됨
- host test만으로 binding이 DEVICE_QUALIFIED로 승격
- source pending인데 source_ready=true
- required modem criterion을 ADB diagnostic으로 대체
- projection이 device/ADB/QCAT COM을 호출
- qa-suite snapshot을 현재 writer로 취급
- partial consistency-set refresh
- raw modem/device artifact가 tracked candidate에 유입

## 16. G0 완료 판정

G0 완료는 `0/28` 숫자의 증가가 아니다. 다음 불변식이 모두 기계적으로 확인되는 상태다.

1. LGU legacy expected 232/232 traceability 보존
2. LGU 28 + SKT 8표본 + KT 2쌍이 v2 계약으로 표현 가능
3. source·procedure·execution·verdict readiness가 독립 계산
4. CTF가 runner·단말·시험대 버전 변화에 불변
5. required source criterion 강등·drop 0
6. provider qualification과 evidence derivation chain 추적 가능
7. projection 결정론·read-only·device call 0
8. consistency-set cutover 이후 checker 위반 0

이 기준을 통과해야 G1 이후 runtime 기능의 우선순위와 실제 runnable/verdict-ready 범위를
신뢰할 수 있다.

## 17. 검토 근거 anchor

설계를 그대로 복제하지 않고 다음 구현·실패 기록의 제약을 추출했다.

- tc-runner: `docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md`,
  `THOR2 - ALT Basic TC Audit/FAILURE_TAXONOMY_2026-07-03.md`,
  `tc_prompts/STAGE1_NORMALIZE.md`, `tc_prompts/STAGE2_COMPILE.md`,
  `docs/qcat_parsing.md`, `scripts/ims_sip_digest.py`, `scripts/qcat_fast_extract.ps1`
- thor2j-tc-appium: `README.md`, `docs/lessons_learned.md`,
  `docs/recovery_honesty.md`, `runner/recovery_gate.py`,
  `docs/superpowers/specs/2026-05-20-automation-recovery-multisession-campaign-design.md`
- qa-suite: `ARCHITECTURE.md`, `MIGRATION.md`, `contracts/vocabulary.md`,
  `contracts/tc-step/tc_step_schema.json`, `contracts/run-bundle/summary_schema_v1.json`,
  `campaigns/manifests/provenance.csv`

특히 적용한 교훈은 source와 capability의 분리, session/context가 바뀌면 qualification을
재사용하지 않는 원칙, 복구 가능성을 실행 성공으로 세탁하지 않는 원칙, snapshot을 writer로
취급하지 않는 provenance 원칙이다.
