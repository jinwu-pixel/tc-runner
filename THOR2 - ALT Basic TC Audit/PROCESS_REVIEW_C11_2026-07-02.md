# PROCESS_REVIEW — C11 사례 기반 TC 생산 파이프라인 정합성 리뷰 (2026-07-02)

**목적**: 실행 결과 요약이 아니라, C11(chunk 21)을 사례로 "요구/기획서 → TC oracle → 실측 UI ground truth → 자동화 → 실행 결과 → 개선 지표" end-to-end 정합성을 검토하고 **다음 batch(Part B 236) 작성·자동화 설계 품질을 높이는 규칙**을 산출한다.

**데이터 원천**: 본 문서의 모든 수치는 `C11_TRACEABILITY_LEDGER_2026-07-02.csv`(21행) 집계에서 기계 파생 (검증 스크립트로 count 대조 — 불일치 시 본 문서가 아니라 ledger가 우선). 분모 = chunk 21 전행(시도 12 + 미착수 9) — 성공 8건만으로 회고를 미화하지 않는다.

---

## 1. 입력 계층 — 검증 의도 추출

- 소스 = Excel `[THOR 2] ALT Basic Test Case_FULL.xlsx` (sheet 5.Magnifying/6.Pedometer/8.Picture Frame/9.Simple settings) → STAGE1 canonical yaml. 원 기획서/규격/버그리포트는 **가용하지 않음** → ledger `source_intent_source`는 전행 `tc_yaml` (의도 발명 0).
- 검증 의도 유형 분포(21행): 메뉴 진입+title 확인(SST 6) · focus 이동 확인(PDM 5 + PFW 6 + MGN 4) — **focus-이동형이 15/21로 지배적**이며, 이 유형이 divergence의 주 발원지(§2).
- 입력 계층의 구조적 한계: 소스 TC의 entry 서술("방향키로", "Hardkey로", "OK")과 expected 서술("~에 포커싱 됨")은 **단말 위젯/포커스 모델을 전제하지 않은 서술형** — F0 실물(RecyclerView/ListView·simple-mode launch 표면)과의 대조 없이는 oracle로 승격 불가.

## 2. 정합 판단 계층 — divergence 분류와 판단 원칙

### 2.1 v1 "0 RUNNABLE"의 원인 재분류 (divergence 4유형 axis)

기존 cluster ①②③(RESULT_RECOVERY)을 사용자 지정 4유형으로 재매핑:

| divergence 유형 | 해당 TC | 기존 cluster |
|---|---|---|
| ① 요구 해석 오류 | 해당 없음 확정 0 — 단, SST_012(설정 내 WiFi 가정)는 ①/② 경계(소스가 가정한 UI 위치 자체가 오류) | ② 일부 |
| ② UI 실제 차이 | SST_012(WiFi=Quick Panel), SST_015(안심 기능 표기·위치), PDM_040(back 요소 0·초기 focus 0), PDM_041~044(down-chain 모델 부재), SST_013(title 상이) | ② |
| ③ TC literal 패러프레이즈 | SST_013(테마 및 배경화면→배경화면 및 스타일), PDM_044(목표 걸음수→목표 걸음 수), SST_015(안심기능→안심 기능), SST_016(Emergency→한글 유력, 미실측) | ①(부분) |
| ④ automation selector 오류 | MGN_001·PDM_040(요소 묘사를 verify_text로 오기), SST_008(OK-key nav 가설 오류), v1 무스크롤 직접 tap | ①③ |
| (신규) ⑤ 실행 환경 상태 | **2026-07-02 발견**: 간편모드 설정 타일 = 기존 task **상태 그대로 resume** → 이전 세션 잔존 스택(GoogleSettingsActivity/SubSettings/스크롤 위치) 위에서 ENTRY_FAILED 3건. oracle·TC·selector 전부 정상인데 실패하는 제5유형 | 미분류 (신규) |

**핵심 통찰**: 한 TC가 복수 유형을 동시 보유(예: SST_013 = ②+③, MGN_001 = ②+④) — ledger가 `primary+secondary` 복합 decision을 갖는 이유.

### 2.2 정합 판단 유형별 허용 원칙 (ledger `decision_type` 판례화)

| decision | 허용 원칙 | C11 판례 |
|---|---|---|
| `verbatim` | 실측이 oracle과 일치하면 무변경 | SST_008·SST_014 |
| `literal_backfill` | 목적지 도달+화면 로드 상태에서 title/text 상이 → run1 dump 실측값으로만 백필(no-guess), `expected_result_raw` verbatim 보존, manifest 재생성 diff=해당 셀만(faithfulness 사전검증) | PDM_044·SST_013 (실행) / SST_015 (staged) |
| `re_scope` | oracle의 검증 모델 자체가 실 UI와 불일치 → 의도 보존 하에 검증 모델 재정의(focus-assert→도달+literal 등). 재정의 근거는 반드시 discovery dump | PDM_041~043(down-chain→gear-nav), SST_012(설정 내→Quick Panel) |
| `element_verifier` | oracle이 화면 text가 아닌 **요소 묘사**("줌 슬라이더 핸들") → verify_text가 아닌 element_presence(resource-id)로 전환 | MGN_001 (확정) / PDM_040 (후보) |
| `fail_closed` | entry/keymap 미상 → 추측 실행 금지, 단말 미접촉 유지 | MGN_002 |
| `selector_discovery` | nav 경로·위젯 모델을 device discovery로 확정한 후에만 driver 작성 | 시도 12 중 10 |

## 3. 자동화 판단 계층 — "왜 이 driver가 생성됐는가" 지식화

- **gear-nav driver(PDM)가 필요했던 이유**: 소스의 down-chain focus 모델이 실 UI에 부재 — 실물은 "메인 우상단 gear(id/imageView) → PersonalInformationActivity에 키/몸무게/성별/목표 걸음 수 집약". **재사용 가능 factory 조건**: (a) 진입 요소가 resource-id로 안정 식별 (b) 목적지에 **도달 게이트**(activity명/marker) 존재 (c) 검증 대상이 목적지 화면의 literal/element. 이 3조건 충족 시 앱 불문 재사용 가능.
- **scroll+tap(SST)이 OK-key를 대체한 이유**: OK-key는 F0에서 기본 정보(About)로 이탈(가설 오류) — scroll_find_tap은 below-fold·스크롤 위치 무관 도달. 단, **launch 후 root 도달 게이트 부재**가 ⑤유형에 노출(§5 규칙 R1).
- **element-presence 분기(MGN)**: verify_text 단일 모델의 한계 — 요소 묘사형 oracle 대응. generator(`scratch/gen_batch10_manifest.py`) element 분기와 driver 분기의 **동기 유지 필요**(§2.3 source-of-truth: generator가 local-only인 동안 manifest MGN 행 revert 위험).
- **host-TDD의 역할 실증**: 23/23 GREEN(순수 분류 모듈)이 device 창 소모 전에 disposition 오류를 차단 — dry-run disposition 4건 일치 확인이 pre-flight의 일부로 정착.

## 4. 실행 결과 계층 — 2026-07-02 회수 + 잔여 gap

- **TWO_RUN_GREEN 8** (PDM_041~044 + SST_008/013/014 + MGN_001) — C11 RUNNABLE_NOW 누적 8. 상세: `RESULT_RECOVERY_BATCH10_C11_2026-07-01.md` v2 회수 1·2차 섹션.
- **NOTE 4** (deferred): SST_012(**2026-07-02 Quick Panel re-scope 백필+fresh 2-run TWO_RUN_GREEN 회수**), SST_015(백필 staged — **2026-07-02 driver slice에서 백필+fresh 2-run TWO_RUN_GREEN 회수**) → **C11 누적 10**, PDM_040(**2026-07-02 spec-gap 확정** — oracle 술어 양쪽 단말 부재·의도보존 재정의 불가, ledger 갱신), MGN_002(fail-closed 유지 — false-progress 방지 실사례 1).
- **NOT_STARTED 9** (gap-9): PFW 6(위젯 진입 표면 자체 미채록) + MGN_005/006(요소 묘사형 위험 동형) + SST_016(영문 literal 위험). **2026-07-02 gap-9 discovery(21 dump, non-mutating)**: SST_016 divergence 확정→백필+2-run **TWO_RUN_GREEN 회수(NOT_STARTED 9→8)** / MGN_005/006 요소 실존·썸네일 미발견·dpad는 scale_bar 고착(판정 보류) / PFW 표면=홈 p3 위젯 페이지 확정·빈 앨범 — **MGN_006·PFW 6은 사진 세팅 precondition(mutating·승인 필요)이 공통 게이트**.
- **⑤유형 실사례**: 초회 run1 SST 3건 ENTRY_FAILED — driver·oracle 무결 상태에서 stale task로 실패. BACK-루프 수동 복구 후 전건 PASS. LIT_ABSENT/LIT_PENDING 경계 오분류 1건(SST_013 — 도달+로드 상태의 title 상이를 VERIFIER_FAILED로 보고)도 driver 분류 gap으로 확인.

## 5. 개선 지표 계층 (ledger 기계 집계)

**분모 표기 규약**: `chunk-21` = C11 전행(ledger 21행) / **`non-gap 12`** = gap-9(NOT_STARTED) 제외, 실측·판단이 이뤄진 시도분. 비율 지표의 분모는 **non-gap 12** — gap-9는 판단 자체가 없어 divergence 여부를 셀 수 없으므로 분모에 넣으면 지표가 희석·왜곡된다. 결과 분포만 chunk-21 기준.

| 지표 | 값 | 산식(ledger) |
|---|---|---|
| oracle divergence 발생률 | **10/non-gap 12 (83%)** | attempted ∧ primary≠verbatim |
| literal backfill 발생률 | **3/non-gap 12 (25%)** — 실행 2(SST_013·PDM_044)+staged 1(SST_015) | any(literal_backfill) |
| re-scope 필요 TC 수 | **6/non-gap 12** (PDM_040~043·SST_012 + PDM_044 secondary) | any(re_scope) |
| selector discovery 필요 TC 수 | **10/non-gap 12 (83%)** | any(selector_discovery) |
| element verifier 전환 TC 수 | **2/non-gap 12** — 확정 1(MGN_001)+후보 1(PDM_040) | any(element_verifier) |
| fail-closed false-progress 방지 사례 | **1** (MGN_002 — 미상 hardkey 추측 실행 차단, v1·v2 일관) | primary=fail_closed |
| 결과 분포 (chunk-21) | TWO_RUN_GREEN **8** / NOTE **4** / NOT_STARTED **9** (=21) | result count |

**2026-07-02 후속 결정 반영**: PDM_040 primary `re_scope→spec_gap`·secondary `element_verifier→—`(ledger 갱신) — 재집계 시 re-scope 필요 6→5·element verifier 전환 2→1. SST_015 백필+2-run·SST_012 Quick Panel re-scope 백필+2-run·SST_016 gap-9 백필+2-run 모두 TWO_RUN_GREEN — 결과 분포 재집계 시 TWO_RUN_GREEN 8→**11**·NOTE 4→**2**(PDM_040 spec-gap·MGN_002 fail-closed)·NOT_STARTED 9→**8**, literal backfill 3→5(SST_012 secondary·SST_016 추가). 위 표는 리뷰 시점 스냅샷 — 불일치 시 ledger 우선(문서 서두 규약).

### 다음 batch(Part B 236) 작성 시 사전 개선 규칙

- **R1 (launch 게이트, ⑤유형 차단)**: driver launch 후 "기대 화면 도달 게이트"(activity명 ∧ marker 요소) 필수 — 미충족 시 BACK-루프 self-heal 후 1회 재시도. 간편모드 타일은 task-resume 방식이므로 **stale 상태를 정상 입력으로 간주**하고 설계. **[구현 2026-07-02 — thor2j driver v3: `sst_root_gate`(activity `.Settings` ∧ `설정 검색`) + `_sst_back_heal`(max 8)+1회 재시도, host-TDD]**
- **R2 (PENDING/ABSENT 경계)**: 목적지 도달+화면 로드 상태에서 expected literal 부재 = `LITERAL_PENDING`(백필 트리거), 도달 실패/화면 미로드 = `VERIFIER_FAILED`. 현 driver는 전자를 후자로 보고 — 재정의. **[구현 2026-07-02 — driver v3: `literal_outcome` — 부수 효과로 root 잔존 시 literal 우연일치 false-PASS도 차단(미도달=PASS 승격 금지), host-TDD]**
- **R3 (oracle 작성 규율)**: focus-이동형·요소 묘사형·영문 literal·공백 변형은 **discovery 선행 없이 oracle 승격 금지** — 15/21이 focus-이동형인 Part B 유사 chunk에서 divergence 83%가 재현될 것. 작성 순서 = 진입 표면 채록 → 위젯/포커스 모델 판별([[reference_alt_focus_widget_model]]) → literal/element 실측 → oracle 고정.
- **R4 (부정 판단 금지)**: "항목 부재" 류 카탈로그 판단은 전체 스크롤 채록으로만 확정 (SST_015 '안심기능 부재' 오판 재발 방지 — 부분 캡처로 단정한 것이 오매핑 SST_016 후보까지 오염시켰음).
- **R5 (nav label=title 동일군 우선)**: nav label과 목적지 title이 동일한 TC(SST_014형)는 divergence 저위험 — Part B 착수 시 이 군을 선행 실행해 창 수확을 조기 확보.
- **R6 (요소 묘사 감지)**: "~핸들/버튼/그래프/아이콘" 어휘가 expected에 등장하면 element_presence 후보로 사전 분류(MGN_001 판례).

---

- 근거 evidence: thor2j `evidence/altbasic_batch10_c11_v2_20260701/` + tc-runner `catalog/f0_c11_nav_2026-07-01/`(+`discovery_2026-07-02/` 10 dump).
- 본 문서 수치 정합 검증: ledger 재집계 스크립트 결과와 §5 표 일치 확인 완료 (2026-07-02).
