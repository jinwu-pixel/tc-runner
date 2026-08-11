# shell-rc producer reconcile amendment — 확정 설계

> **STATUS: IMPLEMENTED + TESTED — COMMIT APPROVAL PENDING (2026-08-11)**
>
> 사용자 승인 범위 = Run-A의 P0 mismatch 원인을 producer reconcile 방식으로
> 교정하는 TDD 구현과 검증. staging, commit, push, capsule capture, campaign
> 재실행은 아직 승인하지 않는다. 각 행위는 기존 승인 게이트를 유지한다.

대상 directive = `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md`
(`RB-20260728-shellrc-p0p1`). 목표는 curated tracked YAML identity와 workbook
producer identity를 서로 같은 이름이라고 가정하지 않고, source row provenance와
target blocker semantics를 각각 fail-closed로 결박하는 것이다.

---

## 1. Run-A에서 확정된 사실

### 1.1 evidence anchor

| 항목 | 값 |
|---|---|
| evidence | `reports/canonical_shell_rc_provenance/RB-20260728-shellrc-p0p1/PROVENANCE_EVIDENCE.json` |
| evidence raw SHA-256 | `e23deb0a5832106ba5cca8571fddff9d96e3d7e0915974d72258652748335f7f` |
| verdict | `PROVENANCE_MISMATCH`, code `1` |
| last phase | `P0_ARTIFACT_CAPTURE` |
| P0 result | tracked YAML 12개 모두 `candidate_count=0` |
| workbook identity | P0 전후 raw SHA와 mtime 불변 |
| producer rehearsal inventory | `SS-TC 0`: 3 documents, `SS-TC 1`: 19 documents |

Run-A는 artifact-tool import와 real workbook capture까지 성공했다. 따라서 관측된
mismatch는 import, ACL, workbook mutation, producer crash가 아니라 P0 join
계약의 구조적 불일치다.

### 1.2 root cause

현행 Appendix A는 tracked YAML의 curated `tc_name`, 예를 들어
`SS_TC01_permission_denied`, 를 workbook-derived `MMIRow.tc_name`, 예를 들어
`TC-01_필수`, 와 exact 비교한다. 그러나 producer의 이름 규칙은
`<source no>_<feature_name>`이고 tracked YAML 이름은 사람이 관리하는 semantic
identity다. 두 namespace 사이에 동등성 계약은 없다.

또한 `SS_TC05_boundary_values.yaml`은 workbook의 `TC-05A`, `TC-05B`, `TC-05C`
세 source row를 한 tracked YAML로 합친 curated aggregate다. 그러므로 파일 rename
한 번이나 one-YAML-to-one-row 가정으로는 provenance를 정직하게 표현할 수 없다.

---

## 2. 선택한 방향과 기각한 대안

| 방향 | 판정 | 이유 |
|---|---|---|
| **producer reconcile** | **채택** | workbook source row, producer output, tracked target semantics를 각자의 identity로 검증할 수 있다 |
| compiled-artifact exception | 기각 | source-first chain을 우회하고 현재 측정 가능한 producer provenance를 버린다 |
| tracked YAML 일괄 rename | 기각 | curated identity와 참조를 불필요하게 파괴하고 aggregate 문제도 해결하지 못한다 |
| `SS_TC05`를 세 YAML로 분할 | 기각 | 현재 tracked artifact의 의미와 범위를 바꾸는 별도 source change이며 reconnaissance 교정 범위를 넘는다 |
| filename 또는 physical-row heuristic | 기각 | row 삽입·정렬·이름 변경에 취약하고 기존 fail-closed 요구를 약화한다 |

본 amendment는 workbook, tracked YAML, `src/mmi_converter/` producer source의
내용을 바꾸지 않는다. 측정 모델과 verifier만 정렬한다.

---

## 3. Frozen source binding manifest

### 3.1 selector 규칙

각 source selector는 다음 세 필드의 exact conjunction이다.

1. `sheet`
2. `source_no`
3. carry-forward 적용 후 `source_functionality_effective`

대소문자 변환, 공백 정규화, prefix match, physical-row fallback은 금지한다.
physical row는 selector 입력이 아니라 관측 결과다. 각 selector의 workbook
candidate count는 정확히 1이어야 한다. `0` 또는 `2+`는 measured mismatch다.

### 3.2 12 YAML / 14 source selectors / 15 blocker bindings

| tracked YAML | sheet | exact source selector(s) | Run-A row(s) | blocker binding |
|---|---|---|---:|---|
| `exported_ss_call/SS_TC01_permission_denied.yaml` | `SS-TC 1` | `TC-01` / `권한 미부여 기본 동작 확인` | `2` | steps `10,11` → `TC-01` |
| `exported_ss_call/SS_TC02_permission_allow_idle.yaml` | `SS-TC 1` | `TC-02` / `권한 허용 후 Idle 진입 확인` | `3` | step `11` → `TC-02` |
| `exported_ss_call/SS_TC03_ringing_permission.yaml` | `SS-TC 1` | `TC-03` / `RINGING 중 권한 허용 시 현재 통화 감지` | `4` | step `15` → `TC-03` |
| `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml` | `SS-TC 1` | `TC-04` / `OFFHOOK 도중 권한 허용 시 seed 복구 확인` | `5` | step `18` → `TC-04` |
| `exported_ss_call/SS_TC05_boundary_values.yaml` | `SS-TC 1` | `TC-05A` / `9초 경계값 검증`; `TC-05B` / `10초 경계값 검증`; `TC-05C` / `11초 경계값 검증` | `6,7,8` | step `9` → `TC-05A` |
| `exported_ss_call/SS_TC06_missed_rejected.yaml` | `SS-TC 1` | `TC-06` / `부재중/거절 통화 처리 확인` | `9` | steps `10,11` → `TC-06` |
| `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml` | `SS-TC 1` | `TC-07` / `짧은 정상 통화 오탐 방지` | `10` | step `9` → `TC-07` |
| `exported_ss_call/SS_TC09_offhook_permission_banking.yaml` | `SS-TC 1` | `TC-09` / `OFFHOOK 중 권한 허용 후 금융 앱 개입 확인` | `12` | step `20` → `TC-09` |
| `exported_ss_call/SS_TC0_P0_endcall_crash.yaml` | `SS-TC 0` | `T/C-01` / `경고 팝업의 "지금 전화 끊기" 버튼 경로에서 다이얼러 크래시 재발 여부와 dismiss→suppression→delayed endCall→IDLE→suppression release 순서 검증` | `2` | step `15` → `T/C-01` |
| `exported_ss_call/SS_TC10_permission_toggle.yaml` | `SS-TC 1` | `TC-10` / `true→false→true 권한 흔들기` | `13` | step `24` → `TC-10` |
| `exported_ss_call/SS_TC11_multi_subscription.yaml` | `SS-TC 1` | `TC-11` / `다중 구독 안전성 확인` | `14` | steps `20,21` → `TC-11` |
| `exported_ss_call/SS_TC12_legacy_path.yaml` | `SS-TC 1` | `TC-12` / `Legacy 경로 현재 상태 반영 확인` | `15` | step `19` → `TC-12` |

`Run-A row(s)`는 evidence에 기록된 관측값이며 selector가 아니다. 구현 후 새
workbook에서 행 번호가 바뀌어도 exact selector가 유일하면 그 새 physical row를
증거로 기록한다.

Acceptance cardinality는 다음으로 교체한다.

- tracked YAML identities = `12`
- unique source selectors / mapped workbook rows = `14`
- source row distribution = `SS-TC 0: 1`, `SS-TC 1: 13`
- target blocker bindings = `15`
- target step distribution = `SS-TC 0: 1`, `SS-TC 1: 14`
- aggregate fan-in = `SS_TC05_boundary_values.yaml`만 `3 source rows → 1 YAML`
- same-row blocker fan-out = `SS_TC01`, `SS_TC06`, `SS_TC11`만 각 2개
- 모든 `(yaml_path, blocker_step_index)`는 unique, step index는 1-based
- 모든 `(sheet, source_no, source_functionality_effective)`는 unique

`SS_TC05`의 세 source row는 모두 provenance 대상이다. 다만 blocker step 9는
9초 통화에서 `LONG_CALL_DURATION`이 없어야 한다는 semantic이므로 `TC-05A`에만
결박한다. `TC-05B/C`는 aggregate의 positive-boundary source provenance로
남으며 blocker step 9의 대체 candidate가 아니다.

---

## 4. P0 contract 변경

### 4.1 p0_workbook schema version

`p0_workbook.json` schema는 `2 → 3`으로 올린다. 기존 top-level workbook identity,
sheet inspection, header/cell/carry-forward/render evidence는 그대로 유지한다.

각 `p0.mappings[]`는 tracked YAML 단위 record이며 최소 다음 구조를 가진다.

```text
yaml_path
yaml_tc_name
declared_source_file
declared_source_sheet
source_selectors[]
  source_no
  source_functionality_effective
  candidate_count
  workbook_physical_row
  workbook_tc_name
  source_* semantic fields
  cells[] / cell_region_records[] / carry_forward_cells[]
blocker_bindings[]
  blocker_step_index
  source_no
verdict
```

`yaml_tc_name`은 P0 frozen manifest의 tracked identity field로 기록하되 Appendix
A에서 tracked YAML을 읽어 검증하지 않으며 workbook row 이름과도 비교하지 않는다.
tracked file과의 exact 비교는 P1 Appendix B가 수행한다. 각 selector로 찾은 row에서
기존 `MMIRow.tc_name` 파생을 재계산해
`workbook_tc_name`으로 기록한다. 이 이름은 P1 producer output binding에만 쓴다.

P0 GREEN 조건은 다음 conjunction이다.

- 12 tracked YAML identity / 14 selector / 15 blocker binding frozen manifest의
  구조, cardinality, uniqueness가 exact 일치
- 14 selector 각각 candidate count = 1
- selector의 exact functionality와 artifact-tool carry-forward 결과 일치
- 14 selected physical row가 서로 unique
- 15 blocker binding이 manifest cardinality와 uniqueness를 만족
- blocker binding의 `source_no`가 같은 mapping의 selector 중 정확히 하나를 참조
- 기존 workbook identity, seven-column, cell, render, no-mutation gate 전부 GREEN

candidate mismatch는 예외로 승격하지 않는다. P0 phase를 `COMPLETED`로 기록한 뒤
`--status measured --last-phase P0_ARTIFACT_CAPTURE`로 evidence를 publish하고
campaign code 1로 STOP하는 현재 흐름을 유지한다.

---

## 5. P1 producer reconcile 변경

### 5.1 identity namespace 분리

P1은 다음 두 identity를 별도로 검증한다.

- tracked identity: `tracked.tc_name == manifest.yaml_tc_name`
- producer identity: `emitted.name == p0.source_selector.workbook_tc_name`

Appendix B는 12개 tracked YAML을 직접 읽고 metadata source가 anchored grammar와
manifest declared sheet에 exact 일치하는지도 검증한다. 즉 alias/source 검증은
P0-only 조건이 아니라 P1의 tracked-input gate이며, producer identity 검증과
독립적으로 판정한다.

따라서 `emitted.name == tracked.tc_name` 비교는 제거한다. producer document의
source binding은 각 selected source row별로 다음 exact conjunction을 유지한다.

1. `emitted.metadata.source_sheet == selected sheet`
2. `emitted.metadata.source_row == selected physical row`
3. `emitted.name == workbook_tc_name`
4. `emitted.description == source_procedure[:200]`
5. emitted filename == `_make_filename(workbook_tc_name, procedure, expected)`
6. `runnable is true` 및 `has_unresolved_params is false`

producer가 export한 전체 inventory는 계속 보존한다. 그중 frozen selector에 결박된
14 documents만 target provenance acceptance에 참여하며, 나머지 workbook rows의
documents는 누락·collision 감사 대상이되 target cardinality에 더하지 않는다.

### 5.2 tracked blocker semantic reconcile

각 `blocker_binding`은 해당 source selector의 emitted document 안에서 tracked
blocker step의 `(action, command, expected)` projection과 exact 일치하는 step을
찾는다. candidate count가 정확히 1일 때만 reconciled다.

- 일반 mapping: one selected source document에서 blocker step을 찾는다.
- `SS_TC05`: 세 producer documents를 모두 source-bound로 검증하되 blocker step 9
  semantic join은 `TC-05A` document 안에서만 수행한다.
- 동일 source document로 fan-out하는 `SS_TC01`, `SS_TC06`, `SS_TC11`의 두
  blocker step은 각자 독립 candidate count = 1을 만족해야 한다.
- tracked 전체 ordered projection과 producer projection의 차이는 기존처럼
  non-target semantic delta로 기록하며, target blocker acceptance와 혼합하지 않는다.

P1 acceptance cardinality는 `14 source-bound producer documents`,
`15 blocker semantic bindings`, `12 tracked YAML identities`다. 이 변경은
reconciliation document/projection key를 YAML path 단독에서
`(yaml_path, source_no)`로 바꾸므로 `reconciliation.json` schema도 `1 → 2`로
올린다. Appendix C는 schema 1 green payload를 거부한다.

---

## 6. Failure classification

| 조건 | 분류 |
|---|---|
| selector candidate `0` 또는 `2+` | measured `PROVENANCE_MISMATCH`, code 1 |
| selected source document 누락 또는 collision | measured `PROVENANCE_MISMATCH`, code 1 |
| producer identity/filename/source metadata 불일치 | measured `PROVENANCE_MISMATCH`, code 1 |
| target blocker step candidate `0` 또는 `2+` | measured `PROVENANCE_MISMATCH`, code 1 |
| tracked alias, manifest cardinality, aggregate binding 불일치 | measured `PROVENANCE_MISMATCH`, code 1 |
| artifact-tool/API/JSON schema/IO/process 불능 | `INFRA`, code 3 |
| capsule/directive/spec/input identity 거부 | `INPUT_MISMATCH`, code 2 |

외곽 process의 exit 관측이 왜곡될 수 있으므로 campaign 판정은 기존 계약대로
stderr 접두사, evidence verdict, disk state를 함께 사용한다.

---

## 7. Source-of-truth와 구현 slice

승인된 구현은 다음 path를 하나의 정렬 slice로 수정한다.

1. `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md`
   - §4 P0 manifest/cardinality/schema
   - Appendix A capture source와 source SHA 소비 지점
   - Appendix B analyzer, Appendix C assembler acceptance, selftest fixture
2. `docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md`
   - P0/P1 one-row 가정을 12/14/15 producer reconcile 계약으로 교체
3. `scripts/provenance_controller_selfcheck.ps1`
   - frozen manifest, Appendix SHA, analyzer fixture의 static/runtime gates
4. `scripts/provenance_controller.ps1`
   - materialization 또는 embedded selftest contract가 변경되는 부분만 최소 수정
5. `tests/test_dispatch_capsule.py`
   - schema v3 early-stop, schema v2 reconciliation, 12/14/15 aggregate fixture
6. 본 amendment design
   - 구현 중 확정된 refinement, 측정 결과, 최종 상태 반영

`tc_samples/TC_1.xlsx`, `exported_ss_call/*.yaml`, `src/mmi_converter/**`,
`scripts/dispatch_capsule.py`는 본 reconcile 구현의 변경 대상이 아니다. live 구현
중 이들 source를 수정해야만 해결 가능한 결함이 발견되면 즉시 STOP하고 별도
승인을 받는다.

Directive Appendix A/B/C bytes가 바뀌므로 각 source SHA와 모든 소비 지점을 다시
freeze한다. Directive raw SHA/git blob도 변경된다. base spec 변경 뒤 raw SHA/blob을
directive에 다시 결박하며, commit+push+0/0 clean 이후에만 새 capsule을 capture한다.
기존 capsule과 기존 execution token은 재사용하지 않는다.

### 7.1 구현 refinement

구현 중 executable 역할과 schema 경계를 다음과 같이 확정했다.

- Appendix A = artifact-tool P0 capture, schema `2 -> 3`
- Appendix B = analysis-only producer verifier
- Appendix C = evidence/failure assembler, reconciliation schema `1 -> 2`
- 12 alias / 14 source selector / 15 blocker binding 계약을 소비하므로 Appendix
  A/B/C 세 fence 모두 변경한다. Appendix R은 변경하지 않는다.
- reconciliation document/projection key는 `(yaml_path, source_no)`, target key는
  `(yaml_path, blocker_step_index, source_no)`다.
- Appendix A는 artifact-tool-only P0이므로 workbook identity, frozen manifest,
  exact selector join을 검증한다. tracked YAML의 alias/source는 Appendix B P1이
  직접 읽어 producer identity와 독립 검증한다. full-chain GREEN은 양 phase 모두를
  요구하고 P0/P1 mismatch는 P2 전에 STOP한다. 이는 검증 완화가 아니라 reader
  책임을 구현과 일치시킨 phase-boundary refinement다.

---

## 8. TDD와 qualification gates

구현은 다음 순서를 지킨다.

### 8.1 RED

먼저 self-check/selftest에 아래 실패를 추가하고 현행 코드에서 RED를 확인한다.

1. direct `yaml_tc_name == MMIRow.tc_name` join 금지
2. manifest cardinality `12 YAML / 14 selectors / 15 blockers` exact pin
3. source distribution `1 + 13`, blocker distribution `1 + 14` exact pin
4. `SS_TC05`만 selector 3개이고 step 9가 `TC-05A`에만 결박됨
5. selector candidate `0` 및 `2+`가 code 1 measured path로 감
6. tracked alias와 producer `workbook_tc_name` namespace가 분리됨
7. synthetic aggregate fixture에서 3 producer docs → 1 tracked YAML reconcile
8. aggregate의 잘못된 source_no 또는 ambiguous blocker step이 fail-closed
9. reconciliation schema 1 green payload 거부 및 schema 2 exact payload 수용

### 8.2 GREEN

Directive Appendix A/B/C와 controller contract를 최소 수정해 신규 RED를 GREEN으로
만든다. 그 후 다음을 모두 실행한다.

- controller static self-check 전체 GREEN
- controller runtime selftest 전체 GREEN
- `git diff --check`
- directive Appendix source 4종의 materialized bytes와 frozen SHA exact 일치
- 기존 dispatch capsule tests 전체 GREEN
- repo 전체 관련 Python/PowerShell regression GREEN

테스트 수는 구현 시 실제 출력으로 기록하며 사전에 임의 고정하지 않는다.

### 8.3 Run-A qualification

구현 commit과 push, fresh capsule, clean/temp-absent preflight를 각각 승인받은 뒤
비공식 Run-A를 재실행한다. 성공 조건은 다음과 같다.

- P0: 12 mappings / 14 unique selected rows / 15 blocker bindings GREEN
- P1: 14 selected producer documents source-bound
- ANALYZE: 15 target blocker bindings 모두 unique reconcile
- ASSEMBLE: evidence publish 완료, 8-phase ledger 계약 충족
- workbook와 tracked producer inputs 무변경
- evidence raw SHA와 독립 재검증 결과 보고

Run-A 완주 전에는 P2 source-first 교정으로 넘어가지 않는다.

---

## 9. 승인 게이트

| 단계 | 내용 | 상태 |
|---|---|---|
| A | producer reconcile conceptual design 선택 | **사용자 승인 완료** |
| B | 본 written amendment spec 작성 + self-review | **완료** |
| C | written spec 사용자 review/승인 | **완료** |
| D | TDD 구현 + regression | **IMPLEMENTED + TESTED — COMMIT APPROVAL PENDING (2026-08-11)** |
| E | 명시 path stage + commit | 별도 승인 대기 |
| F | push audit + fast-forward push | 별도 승인 대기 |
| G | fresh capsule + Run-A campaign | 별도 실행 승인 대기 |

### 9.1 Qualification 측정 결과

> **SUPERSEDED (Task 6):** 아래 Task 5 수치는 당시 실행 기록으로만 보존한다.
> real Appendix B characterization/mutation tests와 base-spec phase-boundary 변경이
> 추가되어 identity drift가 의도적으로 발생했다. Task 7 identity refreeze와 전체
> requalification 전에는 현 구현의 최종 qualification으로 사용하지 않는다.

- controller static self-check: `38/38 GREEN`, exit `0`
- controller runtime selftest: `S1-S17 GREEN`, exit `0`, selftest temp residue `0`
- dispatch capsule regression: `73 passed`, exit `0`
- producer regression: `52 passed`, exit `0`
- materialized Appendix A/B/C/R SHA-256:
  - A `f6e046c74f1b002bfe05d15788ccef4693015df7bd2e774ae20db60fdcb7b2aa`
  - B `63f48a6c88a19bcf5f57679ce0facf18231513590ad2722dc53ebc6a4448981b`
  - C `eda7da101e254ce7dde5eebbdc53861390891761748f75ff6d7af83aa9b692fa`
  - R `d57734b2131cfaf548c28c68d1febbbada6236e49ed8aa21474351f3067f7e64`
- base spec raw SHA-256 / no-filter blob:
  `23c8bfb2ef593dedfff9756f176c7275a89d9d33f7fb84a74481e69f444c95be` /
  `9927ee34c3247047db666edc5beaa6dc41bea3bc`
- `git diff --check` exit `0`; HEAD와 `origin/master`는
  `4376853704a0e6f9a6b3a2d8708892b159d81ff9`로 동일하고 ahead/behind는 `0/0`,
  staged는 비어 있다.

위 결과는 superseded된 Task 5의 historical uncommitted qualification이며
campaign/runtime provenance 완주를 의미하지 않는다. 당시 다음 게이트는 Task 7의
identity refreeze와 전체 fresh requalification이었다. Task 7은 현재 완료됐으며,
현재 게이트는 명시 path stage + commit의 별도 승인이다.

### 9.2 Task 7 fresh qualification 결과

Task 7은 base-spec identity를 fresh rederive한 뒤 directive의 모든 consumer와
Appendix C 외부 pin을 순서대로 refreeze하고, 제품·테스트 파일을 추가 변경하지 않은
상태에서 다음 gate를 순차 실행했다.

- focused identity/manifest/schema: `9 passed, 67 deselected`, exit `0`
- controller static self-check: `38/38 GREEN`, exit `0`
- controller runtime selftest (sandbox 밖): `S1-S17 GREEN`, exit `0`,
  `C:\tmp` selftest residue `0`
- dispatch capsule regression: 단일 Windows PowerShell 5.1 outer process,
  `76 passed`, exit `0`, kill/restart 없음
- producer regression: `52 passed`, exit `0`
- real Appendix B 3-scenario selection: `3 passed, 73 deselected`, exit `0`
- materialized Appendix A/B/C/R SHA-256:
  - A `f6e046c74f1b002bfe05d15788ccef4693015df7bd2e774ae20db60fdcb7b2aa`
  - B `63f48a6c88a19bcf5f57679ce0facf18231513590ad2722dc53ebc6a4448981b`
  - C `62261c533481982b707903ecd00bdb149de670b4aadb133aa7180adb0eff1728`
  - R `d57734b2131cfaf548c28c68d1febbbada6236e49ed8aa21474351f3067f7e64`
- base spec raw SHA-256 / no-filter blob:
  `881008154f34b954379e8745998432744ab911fdcd2a692dbba1c3c4634d8fce` /
  `c6448f0d390ac07e9d5aa8ae7b7a50017795ace9`
- immutable workbook, `exported_ss_call`, `src/mmi_converter`, generator에
  working-tree diff 없음; workbook index identity와 generator raw/blob 일치
- tracked changed-path allowlist 정확히 5개, staged 비어 있음, HEAD와
  `origin/master`는 `4376853704a0e6f9a6b3a2d8708892b159d81ff9`로 동일,
  ahead/behind `0/0`, `git diff --check` exit `0`
- 기존 campaign 두 root는 old directive raw SHA
  `ff74a51c56346daaeb0accd05e5d64f75470689d93b74c16c5634dd207d431b1`에
  결박된 2026-08-11 11시대 KST residue이며, 현 Task 7 directive raw SHA는
  포함하지 않는다. Task 7 생성물이 아니다.

Task 7 중 두 번의 read-only audit-command construction 오류는 제품/contract
불일치가 아니며, proven heading/fence extractor와 단순 immutable Git checks로
교정한 Gate 7 최종 실행은 GREEN이다. 상세 command·duration·실패 이력은
`task-7-report.md`에 보존한다.

이 qualification은 uncommitted 구현 검증이다. campaign/runtime provenance는 아직
완주하지 않았고, staging, commit, push, capsule capture, campaign 실행은 모두
승인되지 않았다.
