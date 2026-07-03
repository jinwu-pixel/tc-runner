# ALT Basic 파이프라인 실패 분류 (FAILURE TAXONOMY)

- 작성일: 2026-07-03
- 목적: 규격서/MMI Excel → STAGE1 정규화·판정 → STAGE2 컴파일 → F0 단말 검증 파이프라인 **개선 설계의 입력**
- 근거: 트랙 누적 증거(batch01~11 요약·재판정 CSV, 검수 원장 4종, F0 결과 C01/C11 + batch1~5·11·R2_LIST, 프로세스·도구 사건, 조인 커버리지)
- 방법: 증거 5그룹 병렬 추출 → 실패 분류 합성(12 category) → category별 증거 적대 검증 (workflow `wf_8c990ba1-181`, agent 18, 오류 0)
- 검증 판정: ADJUSTED 4, CONFIRMED 8. ADJUSTED 항목은 각 category '검증' 절의 정정을 본문 수치보다 우선한다.
- 성격: 분석 산출물 (§2.4 누적). TC/코드/프롬프트 수정 없음 — 개선 반영은 별도 승인 게이트(§2.1).

## 검증 요약

| id | 단계 | 제목 | 판정 |
|---|---|---|---|
| C1-stage1-classifier | STAGE1_판정 | 자동 분류기(cue·휴리스틱) 신뢰성 실패 — 양방향 오류·과승격·집계 드리프트 | CONFIRMED |
| C2-stage1-infeasible-corpus | STAGE1_판정 | corpus 자동화 부적격 — 암묵 fixture·verifier 수단 부재·비결정 상태 (관찰-전용 계약 충돌) | CONFIRMED |
| C3-entry-detail-freetext | STAGE1_정규화·판정 | entry_detail 자유문 정규화·키/포커스 의미 판정 실패 (검수 원장 체인) | CONFIRMED |
| C4-stage1-verifier-synthesis | STAGE1_정규화 | verifier 계약·위젯 포커스 모델 합성 결함 (렌더러/합성 시점 오류) | CONFIRMED |
| C5-stage2-oracle | STAGE2_컴파일 | oracle 미실측 승격·navigation 가설 오류 (컴파일 시점 단말 대조 부재) | ADJUSTED |
| C6-prep-entry-anchor | PREP_조립 | entry 확정·anchor 커버리지 갭 (카탈로그 도달 미달이 합성까지 전파) | CONFIRMED |
| C7-prep-manifest-integrity | PREP_조립 | manifest·식별자 조립 무결성 결함 (tc_id 충돌·generator 결손·포맷 드리프트) | ADJUSTED |
| C8-f0-device-fit | F0_런타임 | 단말-corpus 적합성 불일치 (device-fit — 기능 부재·fixture·mutation 게이트·모드 불일치) | CONFIRMED |
| C9-f0-divergence-env | F0_런타임 | oracle divergence 실증·실행 환경 상태·카탈로그 오판 (시도분 실패와 회수) | CONFIRMED |
| C10-f0-blocked-holds | F0_런타임 | fail-closed·미착수·보류 군 (탈락과 구분되는 정직 분류) | CONFIRMED |
| C11-process-tooling | 프로세스_도구 | 워크플로 에이전트·러너·게이트 도구 자체 결함 | ADJUSTED |
| C12-coverage-join | 커버리지_조인 | 원본 Excel-외부 corpus-manifest-결과 간 조인·커버리지 갭 | ADJUSTED |

---

## C1-stage1-classifier — 자동 분류기(cue·휴리스틱) 신뢰성 실패 — 양방향 오류·과승격·집계 드리프트

**단계**: STAGE1_판정

### 실패 모드

- **mutation-cue 분류기 false-pass (결과동사가 선언적 cue-set 밖: '유지된다/처리된다'·무동사 선택-적용)**
  - 정량: 20/36 (batch02 자동 clean-observe 휴리스틱 통과 후보)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_SETTINGS_BATCH02_SUMMARY_2026-06-09.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`
  - 메모: 선언적 mutation 동사 매칭만으로는 mutation 검출 불충분 — expected 결과문 의미 판독 필요
- **cue 자동 과배제 (위양성 EXCLUDE — 메뉴 라벨·화면 이동·취소 경로·빈 상태 문구 맥락 오발)**
  - 정량: 8/20 (wave2 cue_auto EXCLUDE 직독 표본)
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_2026-06-10.csv`
  - 메모: 재검 표본에서도 7/31=22.6% > 5% 기준 → 'cue=후보 분류 전용, KEEP/확정 EXCLUDE는 사람 판정만' 원칙 확립. 구제 필터로 KEEP 17 회수
- **cue 자동 KEEP 후보의 직독 강등 (cue가 놓친 mutation 8 + 모호/fixture 13)**
  - 정량: 21/114 (wave2 cue 자동 KEEP 후보)
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_2026-06-10.csv`
  - 메모: 최종 KEEP 49 전건 human_confirmed — cue 단독 KEEP 0
- **1차 KEEP의 false-KEEP (관대 판정 — 암묵 fixture·비결정 verifier·암묵 pre-state)**
  - 정량: 28/60 (1차 KEEP 층화 QA 표본)
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_SUMMARY_2026-06-15.md`
  - 메모: 46.7% — 이 결과가 strict 2-pass 전수 재판정을 촉발
- **strict 2-pass 강등 — disqualifier 분포 D1_fixture 128·D5_mutation 86·D2_verifier 46·D3_prestate 40·D4_carrier 10**
  - 정량: 310/581 (1차 KEEP = strict 2-pass 입력)
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_SUMMARY_2026-06-15.md`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_2026-06-15.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv`
  - 메모: D1+D5가 강등의 69% — fresh 1,130 최종 KEEP 271(24.0%)
- **자동분류 과승격 → 직독 확정 yield 급락 반복 (yield 4.6~15.8%)**
  - 정량: 29/183 (S2 자동분류 device-free 구제권; 유사: Clock+Calc 12/96, wave2 49/428, wave3 13/280)
  - 증거: `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_SUMMARY_2026-06-10.md`
  - 메모: S2 29는 보수적 floor(적대 strict의 borderline 과강등 포함) — spot-check 트랙으로 일부 회수 가능
- **미직독 cue 배제의 확정 EXCLUDE 오집계 (KPI 합산 직전 표기 보정)**
  - 정량: 211/428 (wave2 unique 재판정 모집단)
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_2026-06-10.csv`
  - 메모: EXCLUDE_CANDIDATE_UNREVIEWED 분리 집계로 정정 — 확정 EXCLUDE는 직독 29건만
- **판정 집계 정합성 드리프트 (직독 수 과대 보고·ledger 추정치 불일치·stale judge_method·summary-CSV 분포 불일치 — 4건)**
  - 정량: 정량 미기록
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_UNREAD_REJUDGE_2026-06-11.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_REVIEW_REDESIGN_BATCH06_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_BATCH06_SELECTION_2026-06-10.csv`
  - 메모: 199 vs 194, 97 vs 102, stale 24행, 분포 25/17/12 vs 23/18/13

### 개선 후보

- STAGE1 프롬프트(tc_prompts/STAGE1_NORMALIZE.md): disqualifier D1~D5와 결과동사 cue('유지된다/처리된다'·무동사 선택-적용)를 1차 판정 프롬프트에 선주입 — 2-pass 재판정 비용 절감
- prep 사전검사 도구: cue 분류기의 권한을 '후보 슬리밍 전용'으로 제한하는 규칙을 classifier 트랙(scripts/settings_anchor_gap.py + golden)에 고정 — KEEP/확정 EXCLUDE는 human 게이트 필수
- prep 사전검사 도구: 판정 CSV를 단일 원장으로 하고 summary 수치는 CSV 재집계 스크립트로 자동 생성 (수기 집계·추정치 병기 금지, judge_method 컬럼으로 자동/사람 분리)
- 프로세스: 용량 계획은 자동분류 수가 아닌 직독 확정 yield(10~25%) 기준으로 산정 + 1차 판정 직후 적대 QA 표본 → 초과 시 전수 strict re-pass를 표준 사이클로

### 검증

- 판정: **CONFIRMED**
- 검증 메모: 전 8개 failure_mode의 분자/분모가 인용 문서와 일치, CSV 기반 수치는 CSV-aware 재집계로 독립 재현. 재집계 결과: WAVE2 428행(KEEP 50·EXCLUDE 29·REVIEW_QUEUE 145·UNREVIEWED 204 — KEEP 전건 human_confirmed, cue 단독 KEEP 0), WAVE3 280행(KEEP 13), REVIEW_MAPPING 1,130행(KEEP 271/REVIEW 812/EXCLUDE 47, pass=strict2 581, defect D1 128·D5 86·D2 46·D3 40·D4 10 합 310), KEEP_CONFIRMED 271행, S2 183행(SALVAGE_CONFIRMED 29), UNREAD_REJUDGE 102행(stale 24=ALREADY_LEDGERED 16+ALREADY_SYNTHESIZED 8), batch06 selection 57행(popup_cancel 23/observe_split 18/transient_input 13 — summary 25/17/12와 불일치 사실 재현). 뉘앙스 3건: (1) mode1의 20/36 중 REVIEW 10은 cue-동사 누락 외 사유(verifier 모호·민감·외부 전환) 포함 — 단 원문 summary 자체가 20 전체를 휴리스틱 통과 후 인간 강등으로 귀속. (2) mode3의 '모호/fixture 13'은 summary 명시가 아닌 산술 도출(21−8, EXCLUDE 8만 명시). (3) mode7의 211은 표기 보정 시점 수치이며 현재 CSV는 wave3 표본 재검(211→204, 문서화됨) 반영 후 204. mode8 quantity '정량 미기록'은 보수적 표기 — 실제로는 4건 모두 정량 존재(199→194, 97→102, stale 24행, 분포 3필드 25/17/12→23/18/13). wave2 직독 194(ledger 기재)는 wave1+2+3 REVIEW_QUEUE 모집단 296 기준 수치로 ledger 기록으로만 확인(원장 자체가 정정 기록).
- 확인 파일 16건: `THOR2 - ALT Basic TC Audit/STAGE1_SETTINGS_BATCH02_SUMMARY_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/WAVE2_REJUDGE_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_SUMMARY_2026-06-15.md`, `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_2026-06-15.csv`, `THOR2 - ALT Basic TC Audit/KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv`, `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_2026-06-16.csv`, `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/REVIEW_UNREAD_REJUDGE_2026-06-11.csv`, `THOR2 - ALT Basic TC Audit/STAGE1_REVIEW_REDESIGN_BATCH06_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_BATCH06_SELECTION_2026-06-10.csv`

---

## C2-stage1-infeasible-corpus — corpus 자동화 부적격 — 암묵 fixture·verifier 수단 부재·비결정 상태 (관찰-전용 계약 충돌)

**단계**: STAGE1_판정

### 실패 모드

- **암묵 fixture 전제 (precondition 공란 + 사전 데이터 존재 암묵 가정) — 전 wave 횡단 최다 반복 사유**
  - 정량: 300/1130 (REVIEW_MAPPING fresh 재판정 모집단 defer_category A_fixture)
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_2026-06-15.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`
  - 메모: 동형 계수: 강등 D1_fixture 128/581, S2 DEMOTE_FIXTURE 57/183, wave1 fixture 13, DEFER ledger A 다수
- **verifier 수단 부재/비결정 — 색상·미명시 toast·진동·오디오·SubLCD·물리 LED·screenshot 시각 판정·무동작 negative assert**
  - 정량: 103/1130 (REVIEW_MAPPING fresh 모집단 defer_category C_verifier)
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_2026-06-15.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/CLOCK_CALC_REJUDGE_2026-06-10.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_2026-06-16.csv`
  - 메모: 동형 계수: 강등 D2_verifier 46/581 + S2 EXCLUDE 26/183 (시각 전용)
- **비결정 상태·unbound selector — 홈 레이아웃 의존 focus target, negative-only assert, hold-timing 의존, 음량 mutation 내재**
  - 정량: 71/183 (S2 device-free 구제 자동분류 후보 DEMOTE_DEVICE)
  - 증거: `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`
  - 증거: `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_2026-06-16.csv`
  - 메모: 'redesign_pattern 존재'만으로 device-free 구제 가능 판단 금지 — selector 바인딩·상태 결정성은 별도 축
- **구조적 자동화 불가 — 폴더 물리 개폐(SubLCD)·외부 SMS 발송·정각 대기·factory 초기 상태·환경 제어 불가(날씨)**
  - 정량: 87/280 (wave3 일반 15시트 EXPORT 후보 unique 확정 EXCLUDE)
  - 증거: `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/CLOCK_CALC_REJUDGE_2026-06-10.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_SETTINGS_BATCH01_SUMMARY_2026-06-08.md`
  - 메모: Sub LCD 13 전건·Safety 15 전건·TTS 18/22·Setup Wizard 11 — 시트(도메인) 단위 군집
- **이중 게이트 fixture 종속 + verifier 미실증 잔류 — 단일 게이트 해제 후에도 잔존**
  - 정량: 11/17 (DEFER B compose-entry 재판정 모집단, REVIEW 5+EXCLUDE 6)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_DEFER_B_BATCH09_SUMMARY_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/DEFER_B_REJUDGE_2026-06-11.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`
  - 메모: 단일 게이트 해소 ≠ 전체 해소 — TC별 게이트 의존 그래프 명시 필요

### 개선 후보

- STAGE1 프롬프트: fixture 추론 단계(절차/expected에서 전제 데이터 역산)를 1차 게이트로 내장 — precondition 공란=암묵 fixture 의심 기본값 + expected 상태변화 서술 스캔 (강등 원인 69% 커버)
- STAGE1 프롬프트: expected 문을 verifier 실행가능성 등급(text literal/element presence/focus state/screenshot/불가)으로 정규화 앞에서 선분류 — 불가 등급은 판정 비용 없이 조기 분기
- prep 사전검사 도구: 시트(앱 도메인)별 feasibility 프로파일(dump 가능 여부·외부효과·시간 의존)을 재판정 전에 부착 — 저yield 시트의 전수 직독 비용 절감
- prep 사전검사 도구: safe-fixture 사이클(생성→관찰→정리, 잔존 0) 템플릿을 1급 패턴으로 + TC별 게이트 의존 그래프(이중/삼중) ledger 도구화 — DEFER A VRC 10건 중 9건 즉시 합성 선례

### 검증

- 판정: **CONFIRMED**
- 검증 메모: All 5 primary quantities reproduced exactly from evidence files by direct count. FM1: defer_category A_fixture 300/1130 data rows (CSV counted; A_fixture is the largest category, narrowly over D_system_state 298 — supports '최다 반복 사유'). Note figures verified: D1_fixture 128/581 (581 = rows with defect_class assigned = 1차 KEEP strict 2-pass 모집단 per summary; CSV empty defect_class 549, 1130-549=581), S2 DEMOTE_FIXTURE 57/183, wave1 fixture 13 (batch03 REVIEW_QUEUE 'fixture 전제' 묶음 13 = DEFER ledger A-1 CLK 13건), DEFER ledger A = 6 sub-rows. FM2: C_verifier 103/1130 exact; D2_verifier 46/581 exact; S2 EXCLUDE 26/183 with visual-only reasons (카메라 센서/SubLCD/물리 LED) per summary. FM3: DEMOTE_DEVICE 71/183 exact. FM4: wave3 EXCLUDE(확정, human_confirmed) 87/280 exact; sheet clusters within the 87: TTS 18·Safety 15·SubLCD 13·SetupWizard 11·Weather 8. FM5: DEFER B 17 rows = KEEP 6/REVIEW 5/EXCLUDE 6 exact; EXCLUDE 6 전부 이중 게이트(연락처 2+사진 4) per batch09 summary. Coverage caveats (not claim errors, kept for downstream precision): (1) FM4 note 'TTS 18/22' — numerator 18 confirmed in CSV, but denominator 22 comes only from the wave3 summary text; CSV shows TTS sheet total 30 (18 EXCLUDE + 6 REVIEW_QUEUE + 6 EXCLUDE_CANDIDATE_UNREVIEWED), so '22' is not reproducible from the CSV. (2) 'Safety 15 전건'/'Sub LCD 13 전건' refers to reason-homogeneity of the confirmed-EXCLUDE set, not the whole sheet (Safety sheet has 21 wave3 rows incl. 4 REVIEW_QUEUE; Sub LCD 20 rows incl. 7 UNREVIEWED candidates). (3) FM5 REVIEW 5 breakdown: verifier 미실증 is 2/5 (MSG 218/326); remainder = 클립보드 외부효과 1 (MSG 266) + dedup/중복 2 (MSG 393, SPM_076) — mode title 'verifier 미실증 잔류' describes a subset of REVIEW. (4) FM3 descriptive cues are attested but non-dominant in DEMOTE_DEVICE reasons: hold/long-press timing 15/71, volume mutation 7/71, home-layout focus 3/71, negative-only assert 3/71; dominant framing per S2 summary = 비결정 상태·unbound selector·폴더 닫힘 하드웨어·연속 zoom·모드선택 영속 mutation. (5) Source-internal arithmetic: REVIEW_MAPPING summary states 1,196 − 기재판정 63 = fresh 1,130 (arithmetically 1,133), but the CSV row count is exactly 1,130, which is what the claim denominators use.
- 확인 파일 11건: `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_2026-06-15.csv`, `THOR2 - ALT Basic TC Audit/REVIEW_MAPPING_REJUDGE_SUMMARY_2026-06-15.md`, `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_2026-06-16.csv`, `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/CLOCK_CALC_REJUDGE_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/WAVE3_REJUDGE_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/STAGE1_DEFER_B_BATCH09_SUMMARY_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/DEFER_B_REJUDGE_2026-06-11.csv`

---

## C3-entry-detail-freetext — entry_detail 자유문 정규화·키/포커스 의미 판정 실패 (검수 원장 체인)

**단계**: STAGE1_정규화·판정

### 실패 모드

- **press_key 오부착 (NOT_A_KEY — bare 명사 오태깅 109 + 화면/포커스/상태 참조 오태깅 80)**
  - 정량: 189/620 (entry-detail 원장 press_key 계열 step, 236 TC)
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`
  - 증거: `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md`
  - 메모: subtype 재판정: SELECTOR_DISCOVERY 92 / FOCUS_CANDIDATE 61 / SCREEN_PRESENT 20 / FOCUS_STATE 8 / KEYCODE 6 / MANUAL 2. 30.5%는 키 신호 자체 부재
- **무단말 확정 가능분 미정규화 — single explicit key(DPAD 170/175)인데 STAGE1이 keycode 확정 안 함**
  - 정량: 175/620 (entry-detail 원장 step)
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`
  - 메모: 단 TC-level headline unlock은 5/236에 그침 (동일 TC 내 다른 blocker 공존)
- **free-text discovery 잔존 — navigate/tap selector 필요 98 + 표준 keycode 없는 named key 28 + manifest_rewrite 18 등**
  - 정량: 158/620 (entry-detail 원장 step)
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`
  - 메모: 무단말 정규화로 못 푸는 부류 — required_decision 분포가 F0 discovery 작업 큐로 직결
- **disjunction·multi-key 열거 판정 보류 (ADJUDICATE 53 + AMBIGUOUS_NOGUESS 45) — 한 step에 키 열거, no-guess fail-closed**
  - 정량: 98/620 (entry-detail 원장 step)
  - 증거: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
  - 메모: 원문이 'Navi Up/Down/Left/Right/OK 키 입력한다'식 열거 — 시험 의도 키 불명
- **ADJUDICATE 과보류 — qualified 문맥 단일 키 24건은 무단말 확정 가능했음 (STAGE1이 일괄 보류)**
  - 정량: 24/53 (ADJUDICATE step, 46 distinct TC)
  - 증거: `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_LEDGER_2026-06-29.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_CASCADE_2026-06-29.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_SUMMARY_2026-06-29.md`
  - 메모: headline delta는 방어적 11 TC만 인정 — DISJUNCTION_CHOICE 25는 intent_choice, AMBIGUOUS 4는 spec_clarification 잔류
- **focus 후보 오판 — 'X focus'를 verify-point로 본 잠재량(+39 TC)이 전액 inflation: 실제 전건 navigate 실행 위치**
  - 정량: 61/61 (VERIFIER_FOCUS_CANDIDATE step, VERIFY_POINT_HIGH 0)
  - 증거: `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_LEDGER_2026-06-29.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_CASCADE_2026-06-29.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_SUMMARY_2026-06-29.md`
  - 증거: `THOR2 - ALT Basic TC Audit/HANDOFF_FOCUS_CANDIDATE_2026-06-29.md`
  - 메모: 'Do not claim +39 as automatic unlock' handoff 규칙이 실측으로 정당화 — headline delta 0
- **entry_detail 표현 손실 병목 — bare continuation step 보유 행 다수, press_key body 273개 중 driver 5-key 사전 해석분 5개뿐**
  - 정량: 148/236 (batch10 manifest 행 중 bare continuation step ≥1 보유)
  - 증거: `docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md`
  - 증거: `docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md`
  - 증거: `docs/superpowers/plans/2026-06-26-altbasic-entry-detail-ledger.md`
  - 증거: `scratch/batch10_entry_scan.py`
  - 메모: 러너 역학이 아닌 조립·정규화 단계의 표현 갭이 throughput 병목 — measure-first 원장 2종이 정량화

### 개선 후보

- STAGE1 프롬프트(tc_prompts/STAGE1_NORMALIZE.md): press_key 태깅 전 '키 신호'(키 명사+누른다 패턴) 게이트 → 없으면 tap/verifier 후보 분기 + Navi Up/Down/Left/Right/OK→DPAD keycode 매핑 룰 테이블 내장 (step-level 28.2% 자동 해소)
- STAGE1 프롬프트: '수식어+단일 키'(qualified) 패턴은 disjunction과 분리해 즉시 keycode 확정, 열거형만 intent-choice 필드로 명시 분리하는 스키마 요구
- STAGE1 프롬프트: bare 'X focus' 토큰의 기본 해석 = verify가 아닌 navigate(selector discovery blocker) — verify-point 승격은 후속 실행 step 부재 시에만
- prep 사전검사 도구: measure-first 원장 체인(headline=무단말 고신뢰 / potential=별도 표기, fail-closed·self_check·STOP 조건)을 상시 게이트로 — inflation 39+7 회피 실적

### 검증

- 판정: **CONFIRMED**
- 검증 메모: All 7 failure-mode quantities independently recomputed from raw CSVs with proper CSV parsing (ledger contains quoted multi-line fields; naive line-splitting misparses 4 rows and undercounts NOT_A_KEY as 187 — a trap for future audits). Denominators verified: 620 entry-detail steps / 236 distinct TC. Mode 1: NOT_A_KEY 189/620 with exact rationale split 109 bare-noun + 80 screen/focus/state; subtype recount 92/61/20/8/6/2=189; 30.48%≈30.5%. Mode 2: 175/620, DPAD 170/175 (49+47+30+29+15), TC-level headline 5/236 per summary. Mode 3: 158/620; selector 98, manifest_rewrite 18, keycode_discovery 42 of which 'named hardware key, no standard keycode'=28 exactly (the claim's 28 is a rationale-level subset, not the full 42; remaining 14 long-press steps fall under the claim's '등'). Mode 4: 53+45=98/620. Mode 5: RESOLVABLE_HIGH 24/53 across 46 distinct TC; DISJUNCTION_CHOICE 25 all required_decision=intent_choice; AMBIGUOUS_RETAIN 4 all spec_clarification; headline delta 11 TC per summary. Mode 6: 61/61 NAVIGATE_TO_FOCUS, VERIFY_POINT_HIGH 0, inflation avoided 39; HANDOFF line 3 verbatim 'Do not claim +39 as automatic unlock.'. Mode 7: design spec states verbatim 148/236 rows with ≥1 bare continuation step (245 bare tokens/97 distinct) and 273 press_key bodies (134 distinct) with only 5 resolving via the driver 5-key dictionary; scratch/batch10_entry_scan.py implements the bare-step scan. Improvement-candidate figures consistent: 28.2%=175/620; '39+7' inflation avoidance = focus-candidate 39 + ADJUDICATE (prior 18 − headline 11)=7. Coverage limits: cascade CSVs, the 06-29 subtype design spec, and the plan file were verified for existence only — TC-level cascade tier numbers (e.g. tier1_eligible 52, tier2_eligible 80, optimistic 173) were taken from summary text, not re-derived from the cascade CSVs, as no category claim depends on them.
- 확인 파일 15건: `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`, `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`, `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv`, `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md`, `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_LEDGER_2026-06-29.csv`, `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_SUMMARY_2026-06-29.md`, `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_CASCADE_2026-06-29.csv`, `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_LEDGER_2026-06-29.csv`, `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_SUMMARY_2026-06-29.md`, `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_CASCADE_2026-06-29.csv`, `THOR2 - ALT Basic TC Audit/HANDOFF_FOCUS_CANDIDATE_2026-06-29.md`, `docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md`, `docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md`, `docs/superpowers/plans/2026-06-26-altbasic-entry-detail-ledger.md`, `scratch/batch10_entry_scan.py`

---

## C4-stage1-verifier-synthesis — verifier 계약·위젯 포커스 모델 합성 결함 (렌더러/합성 시점 오류)

**단계**: STAGE1_정규화

### 실패 모드

- **verify_text 기본값 오적용 — 텍스트 literal이 본질적으로 없는 focus-state TC에 verify_text+빈 expected 합성 (WARN35)**
  - 정량: 35/271 (batch10 합성 draft)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_REVIEW_MAPPING_BATCH10_SUMMARY_2026-06-15.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`
  - 증거: `THOR2 - ALT Basic TC Audit/WARN35_FOCUS_STATE_VERIFIER_2026-06-16.md`
  - 증거: `scratch/warn35_focus_state_transform.py`
  - 증거: `scratch/t1_focus_state_transform.py`
  - 메모: focus_state 7종 assert로 surgical 정정. 2026-06-25 QA에서 동일 오분류 7건 추가 발견(t1) — 1차 sweep 불완전, 사후 정정 합계 42건. batch11은 동일 유형을 contract 선인코딩해 WARN 0
- **verify_text가 outcome(focus/state 변화) 미포착 — literal이 동작 전후 모두 노출되어 outcome 비관측**
  - 정량: 7/56 (verify_text→focus 변화 outcome 스윕 후보, 모집단 batch10 queued 236)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/QA_NOTES_BATCH10_2026-06-25.md`
  - 메모: BSC_120/121은 2축(닫힘+focused 유지) 동시 확인 없이 승격 금지 — 단일 assert의 false-PASS 구멍 봉합
- **focus 모델 오적용 — node focus 모델 일률 가정 → list 화면(컨테이너 focused 고정, 자식 selected 이동) 위음성 (R1)**
  - 정량: 5/64 (batch11 manifest queued 사이클1 NOT_GREEN; host 분류도 5/13 오류)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_CYCLE2_LIST_FOCUS_SUMMARY_2026-06-22.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`
  - 증거: `scratch/cycle2_list_focus_model_transform.py`
  - 증거: `scratch/r2_list_focus_correct.py`
  - 증거: `scratch/gen_r2_list_manifest.py`
  - 메모: R2 실기 확정: focus 모델은 화면 의미가 아닌 위젯 클래스가 결정(ListView=list / RecyclerView·ScrollView=node). host 분류는 단말 확인 없이 38%(5/13) 오류 — cycle2 13건 list 적용 중 5건 node 환원. 13건 재작업(focus_model 직교 필드, 멱등 transform)
- **합성 공통 결함 — 빈 후보 None 파싱, precondition 타입 오분류(state↔input_method/nav), source-pre 병기 중복·충돌**
  - 정량: 4/공통 결함 유형 수 (batch03 2 + batch04 2; false-promote 0/20·0/21)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_WAVE2_BATCH04_SUMMARY_2026-06-10.md`
  - 메모: 개별 미세조정 아닌 일괄 수정+재생성+게이트 재검증으로 처리 — 반복 결함=렌더러 코드 결함
- **automation_class over-claim + audit_meta 스키마 batch 간 drift**
  - 정량: 16/32 (batch01+02 STAGE1 draft 전수 감사, D1 정렬 수정 16건)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`
  - 메모: entry 미확정·verify paraphrase 상태의 FULL_AUTO_CANDIDATE는 over-claim — 어휘 lock 이전 산출의 소급 정렬
- **verifier 공란·미실증 가정 잔존 — F0 실행 전 사용자 검토에서 보정 (공란 '—', redaction 정책 미명시, 미실증 단정)**
  - 정량: 3/11 (batch09 검증 manifest 등재 건)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_DEFER_B_BATCH09_SUMMARY_2026-06-11.md`
  - 메모: 3건 모두 기계 검사 가능 패턴

### 개선 후보

- STAGE1 프롬프트/렌더러: verifier_type 선택을 expected_result_raw의 텍스트 literal 유무로 게이트 — 부재 시 focus_state/element_presence 계약으로 분기 + device_value=PENDING_F0 (발명 0, batch11 선례 WARN 0)
- STAGE1 프롬프트: focus_model은 위젯 클래스로 판별하고 모호(tab vs list) 시 model_confidence=device_confirm 기본값 — host 확정은 단말 채록 후에만
- validate 게이트: manifest 발행 게이트에 verifier 비공란 검사 + '미실증 가정' 스캔 추가; STAGE1 산출 메타 스키마는 첫 배치 전 lock, lock 변경 시 소급 정렬을 게이트에 포함
- 런너 코드/도구: STAGE1 yaml에 안전한 프로그램적 갱신 경로(주석·포맷 보존 surgical 치환) 정식화 — 사후 sweep 2회 분할 정정의 재발 방지

### 검증

- 판정: **CONFIRMED**
- 검증 메모: 모든 quantity가 인용 문서와 일치: FM1 35/271(batch10 WARN 35, 271/271 parse) + T1 추가 7 = 사후 정정 42, batch11 WARN 0(focus_state 13·element_presence 10·verify_text 6). FM2 56 후보/모집단 queued 236, T1 7 재분류·T2 ~49 note-only, BSC_120/121 2축 승격금지 가드 문서화 확인. FM3 cycle1 NOT_GREEN 5/64(MSG_069/070/071/072/077; manifest 64=29+35), R2에서 13건 중 node 환원 5(5/13=38%)·list 유지 5·defer 3, 위젯 클래스 판별(ListView=list/RecyclerView·ScrollView=node) 실기 확정, 13건 focus_model 직교 필드 멱등 transform 확인. FM4 batch03 공통 결함 2(None 파싱, state→input_method) + batch04 2(source-pre 병기, state→nav) = 4 유형, false-promote 0/20·0/21, 일괄 수정+재생성+gate 재검증 GREEN 양쪽 문서 명시. FM5 16/32(batch01 16 FULL_AUTO_CANDIDATE over-claim → SEMI 정렬 applied, SEMI 16/FULL 0 검증) + D2 audit_meta 필드셋 drift. FM6 3/11(batch09 검토 보정 3건 vs manifest 11행). 미세 뉘앙스 2건(수치 아님): (1) FM1 notes의 '1차 sweep 불완전' 표현 — QA_NOTES 원문은 T1 7건을 WARN35의 '의도적 제외분(literal 보유)'으로 규정하므로, sweep 누락이라기보다 scope 설계상 제외였던 케이스가 후속 기준(literal이 outcome 미포착)으로 재분류된 것. 오분류 합계 42는 정확. (2) FM6 notes의 '3건 모두 기계 검사 가능 패턴'은 인용 문서(batch09 summary)에 명시 근거 없음 — 공란 '—' 스캔은 자명하나 '미실증 단정' 검출의 기계화 가능성은 문서상 미실증 주장. 보조: FM3 R2 문서 NOTE상 SST_009/HDK_095의 node 판정은 com.android.settings 동형 추정(직접 화면 미캡처)이며 5/13 분모 13에는 미검증 defer 3 포함(검증 완료 10 기준이면 5/10=50%). scratch 스크립트 3종(warn35/t1/r2) 헤더가 문서 서술(surgical·멱등·발명 0·대상 건수)과 일치, cycle2 transform·gen_r2_list_manifest는 존재만 확인.
- 확인 파일 16건: `THOR2 - ALT Basic TC Audit/STAGE1_REVIEW_MAPPING_BATCH10_SUMMARY_2026-06-15.md`, `THOR2 - ALT Basic TC Audit/WARN35_FOCUS_STATE_VERIFIER_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/QA_NOTES_BATCH10_2026-06-25.md`, `THOR2 - ALT Basic TC Audit/STAGE1_CYCLE2_LIST_FOCUS_SUMMARY_2026-06-22.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`, `THOR2 - ALT Basic TC Audit/STAGE1_CLOCK_CALC_BATCH03_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/STAGE1_WAVE2_BATCH04_SUMMARY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/STAGE1_DEFER_B_BATCH09_SUMMARY_2026-06-11.md`, `scratch/warn35_focus_state_transform.py`, `scratch/t1_focus_state_transform.py`, `scratch/r2_list_focus_correct.py`, `scratch/cycle2_list_focus_model_transform.py`, `scratch/gen_r2_list_manifest.py`

---

## C5-stage2-oracle — oracle 미실측 승격·navigation 가설 오류 (컴파일 시점 단말 대조 부재)

**단계**: STAGE2_컴파일

### 실패 모드

- **oracle divergence — verifier literal(=source paraphrase)+nav 후보의 미실측 승격이 F0 실 UI와 괴리**
  - 정량: 10/12 (C11 non-gap 시도분; v1 run1 탈락 11/12)
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 메모: divergence 5유형(요구 해석/UI 실제 차/paraphrase/selector/실행 환경 상태). 한 TC가 복수 유형 동시 보유 — Part B 유사 chunk에서 83% 재현 예상. 파이프라인 인프라 자체는 정상
- **literal 패러프레이즈 미실측 승격 → run1 후 backfill (공백 변형·명칭 개정·영문 literal)**
  - 정량: 5/12 (C11 non-gap, primary 4+secondary 1; 동형 C01 4건, batch4 first-pass GREEN 3/14뿐)
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst015_ansim_dest.xml`
  - 메모: backfill 규율 = run1/discovery dump 실측값만(no-guess), source verbatim 보존, manifest faithfulness 사전검증. batch4에서는 GREEN 14 중 11이 관찰-보정 경유 — 첫 시도 literal/selector 부정확이 최빈 1차 실패
- **navigation 가설 오류 — OK-key nav 이탈(About 직행)·무스크롤 직접 tap의 below-fold 미발견**
  - 정량: 5/12 (C11 non-gap: SST_008 1 + SST_012~015 4)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst012_quickpanel_1.xml`
  - 메모: 대체 = scroll_find_tap + OK-key 폐기. SST_012는 검증 모델 자체 오류 → Quick Panel re-scope
- **focus down-chain 모델 부재 — 소스 TC의 down-chain 이동 모델이 F0 실물(gear tap→집약 화면)에 부재**
  - 정량: 4/12 (C11 non-gap re_scope primary; PDM_041~044 재설계 후 4/4 TWO_RUN_GREEN)
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/pdm/pdm_main.xml`
  - 메모: focus-이동형 검증 의도가 15/21로 지배적이며 divergence 주 발원지 — 실물 대조 없이 oracle 승격 불가
- **verifier 유형 오기 — 요소 묘사('줌 슬라이더 핸들'·'뒤로가기 버튼')를 verify_text로 컴파일**
  - 정량: 2/12 (C11 non-gap: element_presence 전환 1 + spec-gap 확정 1)
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/mgn/mgn.xml`
  - 메모: generator element 분기와 driver 분기 동기 유지 필요(§2.3 source-of-truth) — generator local-only 동안 manifest revert 위험

### 개선 후보

- STAGE2 프롬프트(tc_prompts/STAGE2_COMPILE.md): R3(discovery-first — focus-이동형·요소 묘사형·영문 literal·공백 변형은 discovery 선행 없이 oracle 승격 금지) + R6(expected에 '~핸들/버튼/그래프/아이콘' 어휘 시 element_presence 후보 사전 분류) 규칙 추가; 실증 반영된 v1.1.0 R1~R5 유지
- 카탈로그 활용: f0_literal_catalog(62 rows, literal/device_fit/structure/verify_pattern)·nav 카탈로그를 STAGE2 컴파일 입력으로 선반영 — run1-discovery→literal backfill→fresh 2-run을 표준 사이클로(C01→C11 계승 패턴)
- 런너 코드: gear-nav factory 재사용 조건 3(진입 resource-id 안정·목적지 도달 게이트·목적지 literal/element 검증) 일반화 + generator/driver 분기 동기(같은 PR)
- STAGE2 프롬프트: nav label=목적지 title 동일군(R5)만 저위험 선행 실행 허용 — 그 외는 selector discovery 선행

### 검증

- 판정: **ADJUSTED**
- 정정: 2건 정정, 나머지 전부 원문 부합.

[FM2 — literal backfill "5/12"] 분자 5는 ledger 기계 재집계로 확정(primary 4 = SST_013/SST_015/SST_016/PDM_044 + secondary 1 = SST_012). 그러나 분모 표기 불일치: SST_016은 리뷰 스냅샷의 "non-gap 12"에 포함되지 않는 gap-9 항목(이후 2026-07-02 회수). 정합 표기는 (a) 스냅샷 기준 3/non-gap 12(실행 2 SST_013·PDM_044 + staged 1 SST_015 — PROCESS_REVIEW §5 표 그대로) 또는 (b) gap-9 SST_016 회수 반영 시 5/non-gap 13(ledger 현행 attempted=13). "5/12"는 갱신 분자에 스냅샷 분모를 섞은 표기. 부속 수치는 전부 확인됨: C01 동형 backfill 4건(BSC_014/015/017/019 패러프레이즈→실측, RESULT_RECOVERY_BATCH10_C01 표), batch4 first-pass GREEN 3/14(CALC_013/CLK_038/VRC_075)·나머지 11=관찰-보정 사이클(RESULT_RECOVERY_BATCH4 원문 그대로), backfill 규율(no-guess·expected_result_raw verbatim 보존·manifest faithfulness 사전검증)도 원문 일치.

[FM4 — "4/12 re_scope primary"] down-chain 모델 부재 4건(PDM_041~044)과 재설계 후 4/4 TWO_RUN_GREEN은 정확(RESULT v2 표·PROCESS_REVIEW §2.1 ②). 단 괄호 서술 "re_scope primary"는 부정확 — ledger상 primary=re_scope는 PDM_041/042/043의 3건이며, PDM_044는 primary=literal_backfill·secondary=re_scope. 정정: "4/12 (down-chain 부재군 PDM_041~044 = re_scope primary 3 + secondary 1)".
- 검증 메모: CONFIRMED 항목 근거: [FM1] 10/non-gap 12(83%)는 PROCESS_REVIEW §5 표와 ledger 재집계(스냅샷 기준, SST_016 gap 제외 시 attempted 12 중 primary≠verbatim 10) 모두 일치. "v1 run1 탈락 11/12"는 RESULT run1 섹션 "device-touch 11 전건 VERIFIER_FAILED/ENTRY_FAILED + fail-closed 1"과 일치. divergence 5유형(①~⑤, ⑤=실행 환경 상태 신규)·복수 유형 동시 보유(SST_013=②+③, MGN_001=②+④)·Part B 83% 재현 예상(R3)·"파이프라인 인프라 정상" 전부 원문 존재. 단 주석: 10/12 산식(attempted ∧ primary≠verbatim)은 MGN_002(fail_closed, 설계상 단말 미접촉)를 divergence에 포함 — "미실측 승격이 실 UI와 괴리"로 좁게 읽으면 9/12이나, 문서 자체 정의 산식과는 일치하므로 정정 아닌 주석. 현행 ledger(gap-9 회수 후) 재집계는 11/13(85%)로 결론 동일. [FM3] 5/12 = SST_008(OK키→기본 정보 About 이탈, VERIFIER_FAILED) 1 + SST_012~015(무스크롤 직접 tap ENTRY_FAILED) 4 — run1 표와 정확 일치. scroll_find_tap 대체·OK-key 폐기·SST_012 Quick Panel re-scope(검증 모델 자체 오류) 전부 ledger/RESULT 일치. [FM5] 2/12 = MGN_001('줌 슬라이더 핸들' verify_text→element_presence id/scale_bar 전환 확정) + PDM_040('뒤로가기 버튼' verify_text→2026-07-02 spec-gap 확정, ledger primary re_scope→spec_gap 갱신 반영됨). generator/driver 분기 동기·manifest revert 위험 서술도 §3 원문 일치. improvement_candidates 부속 확인: f0_literal_catalog.csv = 62 rows·kind 4종(literal 36/device_fit 12/structure 9/verify_pattern 5) 실측 일치, R3/R5/R6·gear-nav factory 3조건 모두 PROCESS_REVIEW 원문 존재. 판별 불가분: batch4 "관찰-보정 11건"의 원 † 표는 thor2j repo `reports/ALTBASIC_BATCH4_RESULT_2026-06-11.md`(본 repo 밖)라 회수 문서 진술로만 확인. ledger 현행 결과 분포 = TWO_RUN_GREEN 11 / NOTE 2 / NOT_STARTED 8 (PROCESS_REVIEW §5 갱신 주석과 일치). 결과 분포·수치는 리뷰 스냅샷 vs 2026-07-02 후속 갱신의 이중 시점이 존재하며 문서 스스로 "불일치 시 ledger 우선" 규약 명시 — FM2/FM4 정정도 이 규약 적용 결과.
- 확인 파일 11건: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`, `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst015_ansim_dest.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst012_quickpanel_1.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/pdm040_main.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/pdm/pdm_main.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/mgn/mgn.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_literal_catalog.csv`

---

## C6-prep-entry-anchor — entry 확정·anchor 커버리지 갭 (카탈로그 도달 미달이 합성까지 전파)

**단계**: PREP_조립

### 실패 모드

- **Settings anchor 부재 — 정적 anchor-gap 61% (MISSING 202 + PARTIAL 121), 합성 단계에 selector PENDING_F0로 전파**
  - 정량: 323/528 (23.Settings EXPORT_TO_APPIUM 모집단; MISSING 단독 202/528)
  - 증거: `THOR2 - ALT Basic TC Audit/SETTINGS_ANCHOR_GAP_SUMMARY_2026-06-09.md`
  - 증거: `THOR2 - ALT Basic TC Audit/settings_anchor_gap_enriched_2026-06-09.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_2026-06-10.md`
  - 증거: `scratch/s2_render_batch11.py`
  - 메모: PARTIAL='leaf 미관찰'이지 'leaf 부재' 아님. TARGET_REACHED 29/528(5.5%)뿐. Day1 handoff NOT_READY 18/32 동형(웰빙 coverage-gap 8·depth-3 chain 5·entry UNRESOLVED 4·기타 1)
- **deeplink resolver 부재·WRONG_TARGET — 공개 action 부재(NO_RESOLVER 8) + 빌드별 action 해석 상이(WRONG_TARGET 3)**
  - 정량: 11/16 (batch01 STAGE1 drafts 단말 entry probe 미해결)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_BATCH01_DEVICE_PROBE_2026-06-09.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_SETTINGS_BATCH01_SUMMARY_2026-06-08.md`
  - 메모: '발명 0' 원칙 덕에 오류는 후보 표기 3건에 국한 — draft가 action 미발명한 것이 옳았음이 실기로 정당화. F0 USB dropout 1회(INTERRUPTED)로 085/086 UNVERIFIED 잔여
- **entry 패키지/activity 미확정 (launcher 경유) — 단 런타임 탈락으로 이어지지 않음 (entry FAIL 0)**
  - 정량: 73/82 (batch1~4 구식 11-col manifest 행 합계)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH1_2026-06-10.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH2_2026-06-10.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH3_2026-06-10.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH4_2026-06-11.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`
  - 메모: launcher 경유 실행으로 흡수 — batch5 이후 18-col(entry_method/entry_detail) 전환

### 개선 후보

- 카탈로그 활용: anchor MISSING 202를 device probe 우선순위 큐(recommended_probe 컬럼)로 사용해 카탈로그 anchor 선보강 후 합성 — PENDING_F0 잔량 축소
- STAGE1 프롬프트: deeplink action은 candidate로만 정규화(발명 0 유지) + menu-tree anchor와 action 매핑 분리 기록 — WRONG_TARGET은 진입 좌표계 불일치에서 발생
- prep 사전검사 도구: deeplink는 빌드별 resolve-activity 실측 후 채택하는 probe 환류 게이트 유지

### 검증

- 판정: **CONFIRMED**
- 검증 메모: FM1 CONFIRMED — recomputed from enriched CSV (utf-8-sig, 528 data rows, all source_sheet=23.Settings): anchor_state Counter = MISSING 202 / LEAF_LABEL_OBSERVED 176 / PARTIAL 121 / TARGET_REACHED 29. MISSING+PARTIAL = 323/528 = 61.2%; TARGET_REACHED 29/528 = 5.5%. Matches summary MD ALL row exactly. PENDING_F0 propagation: scratch/s2_render_batch11.py line 43 ("anchor MISSING ... verifier 구체 selector PENDING_F0") and line 109 ("device_value: PENDING_F0"). PARTIAL='leaf not observed yet, never leaf absent' at summary lines 95-96. Day1 handoff: 14 DVR_CANDIDATE + 18 NOT_READY = 32; NOT_READY breakdown 웰빙 coverage-gap 8 / depth-3 chain 5 / entry UNRESOLVED 2 + entry UNRESOLVED+PII 2 (=4) / leaf 위치 모호 1 — matches claim's '기타 1'.

FM2 CONFIRMED — probe doc per-draft verdict over 16 batch01 STAGE1 drafts: CONFIRMED 4 / WRONG_TARGET 3 (081·085·086, APPLICATION_SETTINGS→ManageApplicationsActivity 해석) / 부모CONFIRMED-leaf UNVERIFIED 1 (149) / NO_RESOLVER 8 (848·871·922·923·955·956·957·962; WELLBEING/EMERGENCY/GOOGLE actions 'No activity found'). 8+3=11/16 exact for the mode as framed. Nuance (not a correction): doc's own 'batch01 미해결' count is 12 because it also includes 149 (leaf UNVERIFIED — not a resolver failure); the claim's 11 correctly counts only NO_RESOLVER+WRONG_TARGET. '발명 0' justification explicit in probe line 63-64 and DRAFT_AUDIT line 79 ('draft가 action 미발명한 게 옳았음'). F0 USB dropout INTERRUPTED with 085/086 UNVERIFIED explicit at probe lines 99-100, 107-108. batch01=KEEP 16 confirmed in BATCH01_SUMMARY line 3.

FM3 CONFIRMED — batch1~4 VALIDATION_MANIFESTs all 11-col (run_order,tc_id,yaml_path,source,entry,steps,verifier,precondition,cleanup,unresolved,risk); data rows 20+20+20+22 = 82. unresolved column = 'entry 패키지/activity 미확정(launcher 경유)' on 72 rows + 1 variant row ('...; risk_note 내 단말 확정 항목') = 73/82. Cross-check via entry column: 82 − 9 resolved-entry rows (deeplink_confirmed 1, home_tap_path 1, parent_deeplink_plus_tap 3, tap_navigation_required 2, settings_deeplink_confirmed 1, baseline_reached_parent_then_tap 1) = 73, consistent. entry FAIL 0 within batch1~4: batch1 recovery explicit 'entry 0 / verifier 0 / cleanup 0 / device-fit 5, INFRA_FAILURE 0'; only FAILs through batch4 cumulative (66 GREEN + 19 SKIP + 2 FAIL) are SPM_062 VERIFIER_FAILED (fixture 의존) and CALC_009 VERIFIER_FAILED→BUG-GAP(CONFIRMED, BUG 트랙 이관) — neither entry-axis. Boundary note: first ENTRY_FAILED appears in batch5 (MSG_210, RESULT_RECOVERY_BATCH5_2026-06-12.md — 첨부 '오디오' 항목 부재 spec-device 갭, launcher 패키지 미확정과 무관), outside the claimed batch1~4 scope, so 'entry FAIL 0' holds as scoped. 18-col 전환 confirmed: VALIDATION_MANIFEST_BATCH5_2026-06-11.csv header = 18 cols incl. entry_method/entry_detail vs batch1 = 11 cols. Unreconciled minor point (no bearing on claim): batch4 recovery cumulative denominator 87 (본선 누적) vs manifest row sum 82 — recovery docs count 본선 시도 단위 (e.g. batch3 '52/54 시도'), and I did not fully reconcile the 5-row difference from the cited files alone.
- 확인 파일 17건: `THOR2 - ALT Basic TC Audit/SETTINGS_ANCHOR_GAP_SUMMARY_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/settings_anchor_gap_enriched_2026-06-09.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_2026-06-10.md`, `scratch/s2_render_batch11.py`, `THOR2 - ALT Basic TC Audit/STAGE1_BATCH01_DEVICE_PROBE_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/STAGE1_DRAFT_AUDIT_2026-06-09.md`, `THOR2 - ALT Basic TC Audit/STAGE1_SETTINGS_BATCH01_SUMMARY_2026-06-08.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH1_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH2_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH3_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH4_2026-06-11.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH5_2026-06-11.csv`

---

## C7-prep-manifest-integrity — manifest·식별자 조립 무결성 결함 (tc_id 충돌·generator 결손·포맷 드리프트)

**단계**: PREP_조립

### 실패 모드

- **tc_id 스킴 비단사(ALTBASIC_<PREFIX>_<excel_row3>) → cross-batch 충돌 — 원본 Excel 4 sheet 83건 중복 TC ID가 구조 원인**
  - 정량: 4/29 (batch11 SALVAGE_CONFIRMED 합성 대상; Excel dup는 83/미기록 — 4 sheet 감사 건수)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`
  - 증거: `CLAUDE.md`
  - 증거: `scratch/altbasic_tcid_collision_check.py`
  - 증거: `scratch/s2_collision_diag.py`
  - 증거: `scratch/s2_synth_prep.py`
  - 증거: `scratch/s2_finalize_batch11.py`
  - 증거: `THOR2 - ALT Basic TC Audit/KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv`
  - 메모: prep 사전검사 누락 → gate에서 포착. finalize의 'KEEP supersede drop'은 phantom 사건과 얽혀 오판이었음(후속 정정). 스킴 자체 수정 없이는 재발
- **manifest generator entry_detail 결손 — 첫 2 step 한정+40자 truncation으로 후속 네비 step·gesture qualifier 누락 (운영자 under-execute·false FAIL 위험)**
  - 정량: 5/236 (batch10 manifest queued, adversarial QA MED 3+LOW 중 5건)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/QA_NOTES_BATCH10_2026-06-25.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`
  - 메모: generator 교체 후 236행 전체 재생성 RESOLVED(provenance 236/236 grounded·0 invented) — 런타임 도달 전 차단
- **조립 추정 카운트·비근거 행·18-col 포맷 복붙 드리프트 — 카운트는 set-diff 재파생 필요, verifier 신호 0/비안전 행은 REVIEW_BUCKET 분리, 헤더 계약이 스크립트 간 복붙으로만 유지**
  - 정량: 정량 미기록
  - 증거: `scratch/gen_batch10_manifest.py`
  - 증거: `scratch/gen_batch11_manifest.py`
  - 메모: gen_batch11은 대상 35 tc_id 하드코딩 — 공유 상수 부재의 드리프트 위험

### 개선 후보

- prep 사전검사 도구: altbasic_tcid_collision_check.py(cross-batch tc_id + Excel dup 감사)를 scratch에서 정식 파이프라인 선행 게이트로 승격 + (sheet,row,TC ID) 유일성 감사를 진입 첫 게이트로, 충돌 시 결정적 suffix 규칙
- prep 사전검사 도구: manifest 컬럼 스키마를 공유 모듈 상수로 단일화(§2.3 source-of-truth) + 대상 카운트는 항상 set-diff 파생 규칙화
- prep 사전검사 도구: entry_detail은 전 step·raw_text 기반 생성 + truncation cap 상향(120) — 적용된 패턴의 게이트 고정

### 검증

- 판정: **ADJUSTED**
- 정정: [FM1 — 인과 정정] '4/29 cross-batch 충돌'의 gate 포착 사실·분모(29 SALVAGE_CONFIRMED)·충돌 4건(CALC_027/028·SST_010/011)은 CONFIRMED. 그러나 "Excel 4 sheet 83건 중복 TC ID가 구조 원인"은 이 4건에 한해 오귀속 — 실제 원인은 워크플로 에이전트 phantom side-effect(동일 batch11 4건을 batch10 dir에 오기록)이며 Excel dup 발현이 아님. 근거 3중: (a) 충돌 4건의 row_key('32.Calculator#27/28.0'·'9.Simple settings#10/11.0')는 KEEP_CONFIRMED 271행에 부재(grep 0건, s2_collision_diag.py의 진단 대상과 일치); (b) 충돌 sheet(Calculator·Simple settings)는 Excel dup 4 sheet(17.Safety Feature/24.Launcher/25.Call/28.Camera)에 미포함 — dup 스킴으로는 CALC/SST 충돌 발생 불가; (c) s2_correct_phantom.py("drop했던 4건 = 정당한 REVIEW salvage") + batch11 summary gate "tc_id 충돌 0 (phantom 삭제 후)". 즉 최종 실충돌 = 0/29, Excel dup 비단사는 실측 83건의 **잠재(latent) 구조 위험**(기록상 실발현 0). CLAUDE.md §8.2 2026-06-16 row와 collision_check 도구 docstring 자체가 두 사건을 압축 서술로 혼착한 상태 — category notes의 '오판(후속 정정)' 인지는 맞으나 failure_mode 헤드라인의 구조 원인 서술은 phantom 원인으로 교체 필요. [FM1 — 정량 보강] Excel dup '83/미기록'의 분모 정밀화: 83 = 4 sheet 내 중복 보유 고유 TC ID 수(독립 재실행 재현: Safety 23·Launcher 4·Call 4·Camera 52), 영향 행수 = 168행. [FM2 — CONFIRMED] 5/236 정확(MED 3+LOW 3 = 6 중 entry_detail 5건: HDK_019·SET_610 med / LCH_146·CAL_354·PFW_015 low, 나머지 1건 BSC_124=verifier 오분류로 별건). manifest 236행·18-col 실측 일치(237줄-헤더). 첫 2 step([:2])+40자([:40]) truncation은 gen_batch11_manifest.py entry_detail()에 원형 잔존, gen_batch10은 전 step·raw_text·cap 120으로 교체 완료 + 재생성 후 provenance 236/236 grounded·0 invented 유지 — 무단말 QA 단계 포착(런타임 전 차단) 서술 정확. [FM3 — CONFIRMED] 18-col COLS 리스트가 gen_batch10/gen_batch11 두 스크립트에 복붙 중복(공유 모듈 없음, grep 2곳), gen_batch10 docstring "271−35 추정은 방향성일 뿐, 실제 입력은 set-diff" + REVIEW_BUCKET 분리 로직(review_reasons: no_grounded_verifier/safety_class_review 등) 실재, WARN35 = 35 tc_id 하드코딩 실재(수기 카운트 35 = manifest batch10_warn35 35행 일치). 추가 증거: gen_batch11 docstring의 stale 카운트 "25+35=60" vs 실제 manifest 64행(29+35) — 추정 카운트 드리프트의 실사례.
- 검증 메모: coverage: (1) '35 tc_id 하드코딩'은 WARN35(batch10 focus 재분류분) 집합을 지칭 — batch11 29건 자체는 glob 동적 수집이므로 서술 시 구분 권장. (2) s2_synth_prep.py는 현재 collision 검사 코드를 포함 — 사건 당시 부재 후 retrofit인지 파일만으로 판별 불가(CLAUDE.md·도구 docstring은 'prep 사전검사 누락'으로 기록; prep은 합성 전 실행이라 합성 중 생성된 phantom은 어차피 prep 시점 검출 불가). (3) REVIEW_BUCKET_BATCH10 CSV는 handoff 디렉토리에 부재 — 실제 batch10 run에서 review 0건(QA notes set-diff: 271 = already 35 + queued 236 + review 0)이라 '있을 때만' 생성 설계와 정합, 분리 기제는 설계·코드로만 확인됨. (4) Excel dup 감사의 전체 TC ID 분모(sheet 전체 ID 수)는 repo 기록에 없음 — 83은 중복 보유 고유 ID 수 기준. (5) FM1 개선안(충돌 시 결정적 suffix 규칙)은 어느 파일에도 기록 없음 — improvement_candidates 고유 제안으로 판단.
- 확인 파일 16건: `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/S2_SALVAGE_REJUDGE_SUMMARY_2026-06-16.md`, `THOR2 - ALT Basic TC Audit/KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/QA_NOTES_BATCH10_2026-06-25.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH11_2026-06-16.csv`, `THOR2 - ALT Basic TC Audit/stage1_s2_salvage_batch11/`, `scratch/altbasic_tcid_collision_check.py`, `scratch/s2_collision_diag.py`, `scratch/s2_synth_prep.py`, `scratch/s2_finalize_batch11.py`, `scratch/s2_correct_phantom.py`, `scratch/gen_batch10_manifest.py`, `scratch/gen_batch11_manifest.py`, `CLAUDE.md`, `doc/[THOR 2] ALT Basic Test Case_FULL.xlsx`

---

## C8-f0-device-fit — 단말-corpus 적합성 불일치 (device-fit — 기능 부재·fixture·mutation 게이트·모드 불일치)

**단계**: F0_런타임

### 실패 모드

- **본선 비승격 총괄 — DEVICE_FIT_SKIP 22 + VERIFIER_FAILED 2 + ENTRY_FAILED 1 (INFRA_FAILURE 0)**
  - 정량: 25/98 (batch1~5 본선 투입 누적; 조건부 성공률 66/68=97.1%)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`
- **단말 기능·메뉴 항목 부재 (THOR2 corpus와 F0 빌드 스펙 차) — 배치 횡단 최대·지속 사유**
  - 정량: 9/25 (batch1~5 본선 비승격)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`
  - 메모: EXCLUDE 아닌 타 단말 재사용 가능 분류, FIT-nnn 카탈로그(build_id 스코프) 누적 — 배치를 거치며 해소되지 않는 구조적 사유
- **fixture·precondition 미충족 (알람/녹음/대화/차단목록/사진 부재)**
  - 정량: 6/25 (batch1~5 본선 비승격)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH07_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`
  - 메모: VRC_061 fixture 승인 사이클(생성→검증→삭제·잔존0)로 GREEN 전환 + 1 fixture→9건 재사용 실증. CNT 기본계정(영속·rollback 부재)·사진·차단 메시지 fixture 미해소 잔존
- **mutation 미승인 게이트 — 관찰 전용 계약과 충돌 (동의 팝업·폴더 생성·기본 계정 영속 선택)**
  - 정량: 4/25 (batch1~5 본선 비승격, batch4 집중)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH08_2026-06-11.md`
  - 메모: FAIL 아닌 skip 처리 — batch08 CNT editor-entry 7건 연쇄 의존
- **단말 설정·모드 불일치 — 간편모드 런처(라벨 부재·앱서랍 없음)·잠금화면 미사용이 표준 모드 전제 TC와 충돌 (b2→b5 반복)**
  - 정량: 4/25 (batch1~5 본선 비승격, LCH_121 중복 성격 포함)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`
  - 메모: batch11은 간편모드 런처 자체를 대상화해 selector 채록으로 12건 GREEN — 전제를 바꾼 우회 해소
- **검증 수단 한계 — uiautomator dump에 systemui 미포함 (status bar 검증 불가)**
  - 정량: 1/25 (batch1~5 본선 비승격)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`
  - 메모: screenshot axis 설계 필요 — 이후 동류 TC 미배정으로 재발 여부 판별 불가
- **제품 결함 BUG-GAP (탈락 아닌 발견) — CALC_009 백스페이스 전체 삭제 15/15 CONFIRMED**
  - 정량: 1/25 (batch1~5 본선 비승격 중 버그 트랙 이관)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`
  - 메모: 러너/TC 결함 아님 — F0 빌드 한정, 제품 공통 단정은 타 빌드 비교 전 NOTE

### 개선 후보

- 카탈로그 활용: FIT-nnn(기능 부재)·STR-nnn(구조 발견) 카탈로그를 STAGE1 판정·prep 조립 시 사전 조회해 동일 build_id 재배정 차단
- prep 사전검사 도구: 모드 전제(간편/표준 런처)·잠금화면·carrier_fit을 manifest 필수 필드로 명시 + 표준 런처 전제 TC는 간편모드 selector(채록 완료)로 재컴파일 경로 제공
- prep 사전검사 도구: 영속 설정류는 rollback 가능성 사전 조사 후 mutation 승인 게이트를 manifest 조립 전에 처리 (batch5의 CNT 사전 제외 방식) + fixture 승인 사이클 재사용 확대
- 런너 코드: status bar 계열 verifier에 screenshot 판정 axis 계약 추가

### 검증

- 판정: **CONFIRMED**
- 정정: null 수치 정정 없음. 정밀화 2건: (1) '조건부 성공률 66/68=97.1%'는 batch1~4 시점 KPI (RESULT_RECOVERY_BATCH4 표에 분모 정의 verbatim — 분모 68 = device-fit-skip 제외 실행 적합 = GREEN 66 + FAIL 2). batch5 RESULT는 이 지표를 갱신하지 않음 — batch1~5 기준 재계산치는 문서에 부재 (GREEN 73·FAIL 2·ENTRY_FAILED 1에서 MSG_210 분모 포함 여부 미정의 → 73/75 또는 73/76, 어느 쪽도 기록 없음). batch1~5 헤더 아래 66/68을 배치한 표현은 시점 라벨(4-batch 시점)을 붙여야 정확. (2) 분모 98은 문서 자체 계상(b4 '본선 누적 87' + b5 11)을 따르며, 이 87의 GREEN 66에는 annex GREEN 2건(b2 STB_025, b3 VRC_061 fixture annex)이 포함됨 — 문서 계상과 category가 동일하므로 오류 아님.
- 검증 메모: 전 failure_mode 수치가 증거 파일과 정합: DFS 22 = b1 5 + b2 4 + b3 2 + b4 8 + b5 3 / VERIFIER_FAILED 2 = SPM_062(b2)+CALC_009(b3) / ENTRY_FAILED 1 = MSG_210(b5) / 25 = 98−73. 하위 분류 합 9+6+4+4+1+1 = 25 정합 — 단, 이 partition은 LCH_121을 mode3(사진 fixture)에 단일 계상할 때만 성립 (b5 문서가 LCH_121을 '사진 fixture'로 표기하면서 간편모드 섹션 'LCH 3'에도 묶는 이중 성격 — category의 'LCH_121 중복 성격 포함' 문구가 이를 반영, 이중 계상 아님). INFRA_FAILURE 0은 b1만 4축 분리 보고로 명시(entry 0/verifier 0/cleanup 0/device-fit 5); b2~b5는 INFRA_FAILURE 어휘 미사용이나 인프라 실패 보고 0건으로 무모순. mode6 note '이후 동류 TC 미배정으로 재발 여부 판별 불가'는 기록 부재로 문서상 판별 불가가 맞음(b2 carrier 보류 STB 6건 시도 0, 이후 배치 STB 재배정 기록 없음). mode5 note의 batch11 '12건 GREEN'은 간편모드 런처 selector 채록 기반 BSC/HDK focus_move 12건(TWO_RUN_GREEN, com.hnlens.simplemode selector→device_value 환류 12건)이며 b2/b5에서 skip된 LCH TC 자체의 회수는 아님 — '전제를 바꾼 우회 해소'라는 서술 취지와는 부합. mode3 note의 미해소 잔존(CNT 기본계정 ⓔ 게이트·사진·차단 메시지 fixture)은 06-22 R2_LIST까지 해소 기록 없음('070/071/072 fixture-gated' 잔존 확인). mode7의 15/15 = 연속 5+재부팅 후 5+run2 5 (b4 annex verbatim), F0 RY07260600S 한정 CONFIRMED + 타 빌드 비교 전 제품 공통 단정 보류 NOTE도 verbatim 부합.
- 확인 파일 9건: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH07_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH08_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`

---

## C9-f0-divergence-env — oracle divergence 실증·실행 환경 상태·카탈로그 오판 (시도분 실패와 회수)

**단계**: F0_런타임

### 실패 모드

- **v1 run1 oracle divergence 전건 탈락 (RUNNABLE 0) — 인프라 정상, oracle이 실 UI와 divergent**
  - 정량: 11/12 (C11 v1 subset, device-touch 11 전건 + fail-closed 1 별도)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 메모: run1은 설계 목적(literal/keycode run1-verify)대로 divergence를 노출한 discovery 회차 — TWO_RUN 미카운트, 최종 RUNNABLE 11/21로 회수
- **실행 환경 상태(신규 ⑤유형) — 간편모드 홈 타일이 stale task를 상태 그대로 resume → 잔존 스택 위 도달로 ENTRY_FAILED**
  - 정량: 3/4 (v2 2차 회수 device run 대상: SST_008/013/014)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/sst016_stale_resume_display.xml`
  - 메모: oracle·TC·selector 전부 무결인데 실패하는 제5 유형. HOME 단독은 task 미종료 — BACK-루프 종료 후 재launch 필수. R1(root 도달 게이트+BACK-heal) driver v3 구현으로 해소, gap-9에서 1회 재관찰
- **카탈로그 부정 판단 오판 — 부분 캡처 기반 '항목 부재' 단정이 오매핑 연쇄(SST_015→SST_016 후보 오염) 유발**
  - 정량: 1/12 (C11 non-gap 실사례)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst015_ansim_dest.xml`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst_root_p1.xml`
  - 메모: 전체 리스트 채록(p1~p4)으로 정정 → backfill 근거 확보·TWO_RUN_GREEN 회수. R4: '부재' 판단은 전체 스크롤 채록으로만 확정. MGN dpad focus 고착(keyevent 3회 한정 관찰) 판정 보류 2/21도 동형 원칙 적용
- **spec-gap 확정 — oracle 술어(back 요소 존재·초기 focus) 양쪽 모두 F0 대응물 부재, 의도 보존 잔여 없음**
  - 정량: 1/12 (C11 non-gap, PDM_040)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/pdm040_main.xml`
  - 메모: 타 요소로의 verifier 전환=발명 → re-scope 기각. 의도 보존 가능 여부가 re_scope vs spec_gap 분기 기준
- **최종 도달 분포 — RUNNABLE 11 / NOTE 2(spec_gap·fail_closed) / NOT_STARTED 8, secondary selector_discovery 11행**
  - 정량: 11/21 (C11 chunk-21 ledger 전행)
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 메모: 회수 경로 다단(run1 0 → gear-nav+backfill → 2차 → v3 R1/R2 → re-scope → gap-9). 성공분만으로 회고 미화 금지 — 분모는 chunk 전행 또는 명명된 non-gap

### 개선 후보

- 런너 코드: launch 후 root 도달 게이트(activity suffix ∧ marker) + BACK-heal 재시도 패턴(driver v3 R1)을 앱 진입 공통 로직으로 일반화 — stale 상태를 정상 입력으로 간주하고 설계
- 카탈로그 활용: '항목 부재' 류 부정 판단은 전체 스크롤 채록으로만 등재 가능하도록 카탈로그 등재 규칙(R4)에 내장 — 부분 캡처·제한 keyevent 관찰 단정 금지
- STAGE2 프롬프트: 의도 보존 가능 여부를 re_scope vs spec_gap 분기 기준으로 명문화 — 대응물 부재 시 verifier 발명 금지
- 런너 코드: run1을 RUNNABLE promotion이 아닌 grounded redesign input으로 취급하는 2-run 구조(discovery→backfill→fresh 2-run) 표준 유지

### 검증

- 판정: **CONFIRMED**
- 검증 메모: All 5 quantities verified against sources. (1) 11/12: RESULT scope=v1 subset 12(SST5+PDM5+MGN2), device-touch 11 전건 VERIFIER_FAILED/ENTRY_FAILED + fail-closed 1(MGN_002), 진단='v1 oracle divergence (파이프라인 정상)' verbatim. (2) 3/4: v2 2차 device run 대상 4건(SST_008/013/014+MGN_001) 중 초회 ENTRY_FAILED 3건(SST) = stale task resume; ⑤유형 명명은 PROCESS_REVIEW §2.1 신규 행; R1 구현은 RESULT v3 섹션+PROCESS_REVIEW R1 [구현 2026-07-02]; gap-9 1회 재관찰은 RESULT gap-9 섹션+ledger SST_016 행+sst016_stale_resume_display.xml(com.android.settings 디스플레이 하위 화면=stale 실물) 정합. (3) 1/12: SST_015 오판 1건, RESULT 'SST_015 정정'+PROCESS_REVIEW R4('오매핑 SST_016 후보까지 오염' verbatim), sst015_ansim_dest.xml/sst_root_p1.xml에 '안심 기능' 실존 grep 확인, non-gap 12 분모는 §5 규약 정의와 일치. (4) 1/12: PDM_040 ledger primary=spec_gap/result=NOTE, pdm040_main.xml grep: focused="true" 0건·뒤로/back 0건(술어 양쪽 부재 실증), 'verifier 전환=발명→re-scope 기각' 문서 부합. (5) 11/21: ledger 21행 직접 집계 TWO_RUN_GREEN 11/NOTE 2(PDM_040·MGN_002)/NOT_STARTED 8, secondary에 selector_discovery 포함 행 정확히 11. Nuances(비정정): claim3 note의 'MGN dpad focus 고착 판정 보류 2/21'은 ledger상 MGN_005(dpad 고착·keyevent 3회 한정)와 MGN_006(썸네일 미발견·빈 갤러리 추정)의 보류 기전이 상이 — 2건 보류 자체는 문서 부합. claim5의 PROCESS_REVIEW §5 표는 스냅샷(8/4/9)이며 line 70 재집계 note가 11/2/8로 갱신, 'ledger 우선' 규약과 정합. run1 evidence CSV 원본(thor2j-tc-appium evidence/)은 본 repo 밖이라 미열람 — 검증은 tc-runner 내 RESULT/ledger/catalog 기준.
- 확인 파일 7건: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`, `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`, `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst015_ansim_dest.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/sst_root_p1.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/pdm040_main.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/sst016_stale_resume_display.xml`

---

## C10-f0-blocked-holds — fail-closed·미착수·보류 군 (탈락과 구분되는 정직 분류)

**단계**: F0_런타임

### 실패 모드

- **fail-closed — entry hardkey/keymap 미상 시 추측 실행 금지(UNSUPPORTED_ENTRY_DETAIL), 단말 미접촉 유지**
  - 정량: 1/21 (C11 chunk-21, MGN_002; 동형 C01 7/13 군집)
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md`
  - 메모: false-progress 방지 설계 동작(결함 아님) — device key-discovery 선행 후에만 해제
- **gap-9 미착수 — driver 미구현·진입 표면 미채록으로 v1 scope 명시 제외 (PFW 6 + MGN 2 + SST_016)**
  - 정량: 9/21 (C11 chunk-21 v1 시점 NOT_STARTED; SST_016 discovery 회수 후 8)
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 증거: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/pfw_home_p3.xml`
  - 메모: 미착수는 divergence를 셀 수 없어 비율 분모에서 제외(non-gap 분모 규약) — 미착수와 탈락 혼동 금지
- **gap-8 — 사진 세팅 precondition 공통 게이트 (단말 사진 부재: PFW 빈 앨범·MGN 빈 갤러리 추정)**
  - 정량: 8/21 (C11 chunk-21 최종 NOT_STARTED = PFW 6 + MGN_005/006)
  - 증거: `THOR2 - ALT Basic TC Audit/MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/pfw_home_p3.xml`
  - 증거: `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/mgn_main_full.xml`
  - 메모: MEDIA_SEED 설계 확정(전용 경로 한정 세팅/원복 대칭·기존 미디어 무접촉·PII 0, S0 완료·S1 HELD 승인 대기) — 기존 Gallery 자산 재사용, 발명 0
- **batch11 잔여 미시도 — list-aware verifier·진입 경로 채록·R1 변형·안전 denylist 핸들러 등 선결 조건 보류**
  - 정량: 52/64 (batch11 manifest queued 사이클1 이후)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`
  - 메모: MSG list-focus 5는 R2로 해소됨 — 탈락 아닌 미착수 보류
- **carrier SIM 불일치 보류 — F0=LGU+ 확인 후 SKT 4+KT 3 시도 0으로 잔존, 이후 회수 문서에 시도 기록 없음**
  - 정량: 7/7 (carrier 보류 지정 전건 미시도 잔존)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH06_2026-06-11.md`
  - 메모: annex STB_025(LGU+ 'U+')는 carrier_fit CONFIRMED GREEN — carrier_fit 필드는 manifest에 기존재

### 개선 후보

- prep 사전검사 도구: precondition-gated 군(사진·fixture·carrier)은 케이스별이 아닌 공통 게이트로 묶어 1회 세팅/스왑 사이클로 일괄 해제 — SIM 스왑 세션 1회로 SKT/KT 묶음 소진, 원복 검증 PASS 전 세션 종료 금지
- 런너 코드: fail-closed(UNSUPPORTED_ENTRY_DETAIL) 어휘와 registry 분류를 표준 유지 — 해제는 device key-discovery 선행 후에만
- 보고 규칙/validate 게이트: 미착수·보류·fail-closed를 탈락과 분리 집계(non-gap 분모 규약, headline/potential 분리)를 결과 문서 템플릿에 강제

### 검증

- 판정: **CONFIRMED**
- 정정: null — 5개 failure_mode의 quantity 전부 원문서와 일치. (1) fail-closed 1/21: ledger 21행 중 MGN_002 유일 fail_closed·UNSUPPORTED_ENTRY_DETAIL·단말 미접촉(v1·v2), PROCESS_REVIEW §5 'fail-closed 사례 1'; C01 7/13: FAIL-CLOSED 7건(BSC_018/121/031/071/072/073/124) / scope 13(GREEN 4+DEFERRED 1+fail-closed 7+OBSERVE_ONLY 1). (2) gap-9 9/21→8: C11 RESULT 'driver 미구현 9(PFW×6·MGN_005/006·SST_016) 제외' + PROCESS_REVIEW 'NOT_STARTED 9→8'(SST_016 TWO_RUN_GREEN 회수) + non-gap 분모 규약 §5 명문. (3) gap-8 8/21: ledger NOT_STARTED 8행 = PFW_010/011/013/014/015/022+MGN_005/006, 최종 분포 TWO_RUN_GREEN 11/NOTE 2/NOT_STARTED 8, MEDIA_SEED '잔여 8건 공통 게이트'·S0 스크립트 3종 실재·S1 HELD는 commit 7b65813 메시지 정합. (4) batch11 52/64: RESULT headline 'RUNNABLE_NOW = 12/64'+'잔여 batch11 = 52' 일치. (5) carrier 7/7: BATCH2 'carrier 보류(시도 0): SKT 4(STB_020/021/022·LCH_184)+KT 3(STB_026/027/028)'·F0 SIM=LG U+ 명기, BATCH3 'carrier 7 보류' 유지, 7개 ID 전체 grep 결과 이후 회수 문서 시도 기록 0건, STB_025 annex TWO_RUN_GREEN(carrier_fit CONFIRMED_LGU+)·carrier_fit 필드 manifest 기존재 확인.
- 검증 메모: 뉘앙스 3건(수치 오류 아님): ① batch11 잔여 52의 문서 내부 breakdown 표는 5+3+14+29=51로 headline 52와 1건 불일치 — 원문서(RESULT_RECOVERY_BATCH11) 자체 결함, 잔여 1건의 소속 묶음은 판별 불가. ② gap-8의 '사진 세팅 공통 게이트' 범위: C11 RESULT 본문 한 곳(line 84)은 'MGN_006·PFW 6'(7건)으로, 최종 잔여 요약(line 94)과 MEDIA_SEED는 MGN_005 포함 8건으로 기술 — MGN_005는 사진 부재 차단이 아닌 '전체 UI 상태에서 dpad focus 재관찰'(현 관찰 keyevent 3회 한정) 목적의 동반 대상. category 서술('MGN 빈 갤러리 추정')은 MGN_006에 정확, MGN_005는 재관찰 사유. ③ 'MSG list-focus 5는 R2로 해소됨': R2 LIST 결과(2026-06-22)는 verifier 모델 한계 해소(MSG_069/077 직접 정·역재현, MSG_070/071/072는 동일 ListView 분류이나 fixture-gated 미검증)이며 yaml 백필은 §2.1 승인 대기 — '모델 차단 해소'로는 정확하나 TC 5건 회수 완료는 아님. 추가: HANDOFF_SUMMARY_BATCH06에 별도 carrier UNCONFIRMED 1건(LCH_188, 'SIM 불일치 시 skip' 계약)이 존재하나 이는 batch2의 '보류 지정 7건'과 다른 축(정적 플래그)이라 7/7 분모에 불포함이 타당. C01 fail-closed 7과 C11 MGN_002의 '동형' 서술은 양쪽 모두 UNSUPPORTED_ENTRY_DETAIL·단말 미접촉·key-discovery 선행 해제 조건으로 문서상 정합.
- 확인 파일 16건: `THOR2 - ALT Basic TC Audit/C11_TRACEABILITY_LEDGER_2026-07-02.csv`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`, `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md`, `THOR2 - ALT Basic TC Audit/MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_SUMMARY_BATCH06_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/THOR2J_HANDOFF_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/pfw_home_p3.xml`, `THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/mgn_main_full.xml`, `scripts/gen_pfwseed_photos.py`, `scripts/setup_pfwseed_f0.py`, `scripts/reset_pfwseed_f0.py`

---

## C11-process-tooling — 워크플로 에이전트·러너·게이트 도구 자체 결함

**단계**: 프로세스_도구

### 실패 모드

- **합성 워크플로 에이전트 side-effect — 구조화 반환 계약 위반 file 직접 기록(phantom 4건) + 슬라이스 over-read(53 반환/29 기대)**
  - 정량: 53/29 (batch11 기대 draft 수 대비 반환; phantom 4/29)
  - 증거: `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`
  - 증거: `CLAUDE.md`
  - 증거: `scratch/s2_correct_phantom.py`
  - 증거: `scratch/s2_synth_prep.py`
  - 증거: `scratch/s2_finalize_batch11.py`
  - 증거: `scratch/s2_render_batch11.py`
  - 메모: phantom을 batch10 정당 산출물로 오인한 2차 오류(4건 drop·25 오보고)까지 유발 — git 추적 검증(untracked·fc56cf8 미포함)으로 확정·정정. 부수 취약점: agent 출력을 세션별 Temp 경로 하드코딩으로 읽음(휘발 입력 의존)
- **STAGE1 정적 게이트 부재 — validate_tc.py는 compiled 전용이라 STAGE1 canonical draft에 적용 가능한 게이트가 파이프라인에 없었음**
  - 정량: 정량 미기록
  - 증거: `scratch/stage1_canonical_check.py`
  - 증거: `scratch/s2_finalize_batch11.py`
  - 증거: `scratch/s2_correct_phantom.py`
  - 메모: stage1_canonical_check.py 별도 신설 자체가 공백의 증언. ad-hoc 재게이트(intent 화이트리스트·adb denylist)도 합성 산출물의 금지 명령 포함 위험을 전제
- **runner verifier 결함 — _compose_exit_verify 무조건 BACK 2회가 picker 케이스에서 과이탈 → CLEANUP_FAILED 위양성**
  - 정량: 2/11 (batch5 본선)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`
  - 메모: 상태 인지 재anchor 로직으로 동일 배치 내 해소 → TWO_RUN_GREEN 전환 — 러너 자체 결함이 탈락으로 보고된 유일 사례
- **driver 판정 경계 오분류 — LITERAL_PENDING을 VERIFIER_FAILED(LIT_ABSENT)로 보고 + root 잔존 상태 literal 우연 일치 시 잠재 false-PASS**
  - 정량: 1/12 (C11 non-gap 경계 오분류 실사례 SST_013)
  - 증거: `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`
  - 증거: `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`
  - 메모: R2 literal_outcome 3분지 재정의 + host-TDD 36/36 GREEN(RED 확인 후 구현)으로 봉합 — device 창 소모 전 차단
- **러너 커버리지 갭 — batch10 236 큐를 실행할 러너 부재 (현 커버: C01 narrow 4 + batch11 12)**
  - 정량: 16/236 (batch10 device-validation 큐 중 러너 커버 TC)
  - 증거: `docs/superpowers/specs/2026-06-30-altbasic-c11-sst-driver-design.md`
  - 증거: `docs/superpowers/plans/2026-06-30-altbasic-c11-sst-driver.md`
  - 증거: `docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md`
  - 메모: Part B의 진짜 병목 — 대응 전략은 범용 dispatch 선구축 대신 청크별 점진 빌드(TWO_RUN_GREEN만 승격, 2~3 청크 후 공통형 추출)

### 개선 후보

- prep 사전검사 도구/워크플로: 합성 에이전트 read-only·return-only 계약 + 실행 직후 git status 기반 untracked 오염 스캔 + 출력 개수 계약(입력 N=출력 N, 초과 시 fail) + agent 출력 영속 경로 보존을 게이트로 명문화
- validate 게이트: STAGE1 canonical 스키마 정적 검증기(stage1_canonical_check.py)를 §5.1 정식 도구로 승격하고 GATE 체인에 STAGE1 게이트 단계 명시 (현행 §3.2는 compiled 전제)
- 런너 코드: 이탈 verifier는 고정 BACK 횟수 대신 상태 인지 재anchor 패턴 표준화 + host-TDD dry-run disposition 일치 확인을 pre-flight에 정착 + 미도달 시 PASS 승격 금지 규칙
- 런너 코드: 청크별 점진 dispatch(import-only 재사용·no-fork·wrong-device 가드) 반복 후 공통 dispatch 추출 — YAGNI 순서 유지

### 검증

- 판정: **ADJUSTED**
- 정정: FM5(러너 커버리지 갭) quantity 정정: "16/236 (batch10 device-validation 큐 중 러너 커버 TC)"는 분모-분자 관계가 부정확. 실측: batch10 manifest = 정확히 236 rows(237 lines - header)이나, batch11 러너 커버 12건(BSC_038~045 8 + HDK_043/044/045/047 4)은 batch10 236 manifest에 0건 존재(grep 0 match) — 이 12는 별도 batch11 handoff 큐 64(batch11 29 + WARN35 35) 소속으로 RUNNABLE_NOW 12/64 (RESULT_RECOVERY_BATCH11_2026-06-17.md). 정정값: "batch10 236 큐 내 러너 커버 = 4/236 (C01 narrow, manifest 내 BSC 13행 중 4 RUNNABLE); 전체 러너 커버 합계 = 16 (C01 4/236 + 별도 batch11 큐 12/64)". 원 설계문서(2026-06-30-altbasic-c11-sst-driver-design.md §1) 문장 자체("batch10 236 큐를 실행할 러너가 없음(현 커버: C01 narrow 4 + batch11 12)")는 verbatim 정확 — 카테고리의 분수 표기만 두 큐를 한 분모로 합산한 오기. 나머지 4개 failure_mode(FM1 53/29·phantom 4/29, FM2 정량 미기록, FM3 2/11, FM4 1/12)는 수치·서술 모두 증거 파일과 일치(CONFIRMED).
- 검증 메모: 추가 확인 사항: (1) FM1 부수 취약점 "세션별 Temp 경로 하드코딩" 실증 = scratch/s2_correct_phantom.py:13 및 scratch/s2_synth_prep.py:8의 TASKOUT 절대경로(C:\Users\momen\AppData\Local\Temp\claude\...\tasks\*.output). (2) FM4의 36/36 GREEN·신규 14(RED 확인 후 구현)·literal_outcome 3분지(PASS/LITERAL_PENDING/VERIFIER_FAILED)·root 잔존 false-PASS 차단은 RESULT_RECOVERY_BATCH10_C11 v3 섹션에서 전부 확인. (3) FM3 notes의 "러너 자체 결함이 탈락으로 보고된 유일 사례" 주장은 전수 검증 불가 — 인접 사례로 batch11 MSG_069~077 5건(R1 focus_move 모델 한계로 판정 불가·deferred)과 C11 SST_013 오분류가 존재하나, 둘 다 '위양성 FAIL로 탈락 보고' 유형은 아니어서(전자=판정불가 유보, 후자=백필 후 동회차 회수) 좁은 정의에서는 성립. 판별 불가로 남김. (4) FM1 관련 CLAUDE.md §8.2 2026-06-16 row는 status=proposed(본문 미승격) — 카테고리 서술과 모순 없음. (5) C01 4 RUNNABLE의 tc_id 목록 자체는 확인한 파일들에 미기재(ledger design doc의 "13 rows → 4 RUNNABLE" 서술로만 확인) — handoff_device_validation에 C01 RESULT 파일 부재. (6) improvement_candidates 중 wrong-device 가드(PINNED_UDID ABORT)·import-only no-fork 재사용은 driver design doc §3에서 실재 확인, stage1_canonical_check.py의 §5.1 미등재(승격 후보) 상태도 CLAUDE.md §5.1 표와 대조 확인.
- 확인 파일 15건: `THOR2 - ALT Basic TC Audit/STAGE1_S2_SALVAGE_BATCH11_SUMMARY_2026-06-16.md`, `CLAUDE.md`, `scratch/s2_correct_phantom.py`, `scratch/s2_finalize_batch11.py`, `scratch/s2_synth_prep.py`, `scratch/s2_render_batch11.py`, `scratch/stage1_canonical_check.py`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`, `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`, `docs/superpowers/specs/2026-06-30-altbasic-c11-sst-driver-design.md`, `docs/superpowers/plans/2026-06-30-altbasic-c11-sst-driver.md`, `docs/superpowers/specs/2026-06-26-altbasic-entry-detail-ledger-design.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`

---

## C12-coverage-join — 원본 Excel-외부 corpus-manifest-결과 간 조인·커버리지 갭

**단계**: 커버리지_조인

### 실패 모드

- **thor2j corpus 조인 증거 재사용 0 — exact_id join 0, fuzzy 최고 0.47~0.59, TWO_RUN_GREEN 전이 가능 0건**
  - 정량: 1286/5717 (ALT Basic unique TC 중 overlap-theme 후보; NOT_FOUND 4,431)
  - 증거: `THOR2 - ALT Basic TC Audit/JOIN_SUMMARY_2026-06-08.md`
  - 증거: `THOR2 - ALT Basic TC Audit/overlap_join_2026-06-08.csv`
  - 메모: false-evidence 방지 수치 고정 — 재사용 대상은 실행 패턴(runner 코드·2-run gate)만. SETTINGS_DEFAULT_APP 버킷 과포착은 UNKNOWN+REVIEW_MAPPING 격리로 false-promote 0
- **Excel 원본 이질성 — sheet별 헤더 행 위치·ID 컬럼 헤더 비일관, TC ID float 저장 → 스크립트별 방어 로직 중복 재구현(드리프트 위험)**
  - 정량: 정량 미기록
  - 증거: `scratch/s2_extract_183.py`
  - 증거: `scratch/s2_synth_prep.py`
  - 증거: `scratch/altbasic_tcid_collision_check.py`
  - 메모: tc_id 비단사 사건(Excel dup)과 결합해 조인 무결성이 스크립트별 재구현에 의존
- **manifest 상태 result-join 부재 — 조립 시점 탈락 status 0, 탈락·보류 분포는 RESULT/QA 문서 수작업 추적만 가능, manifest 행수-결과 건수 ±1~4 불일치**
  - 정량: 324/324 (18-col manifest 4종 행 합계 전행 DEVICE_VALIDATION_READY_CANDIDATE)
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH5_2026-06-11.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH11_2026-06-16.csv`
  - 증거: `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_R2_LIST_2026-06-22.csv`
  - 메모: annex·probe 항목이 manifest 밖 실행 — 조인 키(tc_id)는 안정적이므로 결과 역환류 스키마 후보

### 개선 후보

- prep 사전검사 도구: 헤더 탐지·ID 정규화·row_key 생성을 공용 모듈로 승격해 스크립트별 재구현 드리프트 방지
- prep 사전검사 도구/보고: manifest에 판정 결과 역기입(result-join) 열 추가 — 배치 횡단 탈락 추적의 수작업 제거
- 조인 정책: corpus 상이 시 증거 전이 금지 lock(reuse_allowed ⟺ TWO_RUN_GREEN ∧ manual_candidate) 유지 — 버킷 키워드 정밀화는 reuse 0이므로 저우선

### 검증

- 판정: **ADJUSTED**
- 정정: FM1·FM2 = 수치·서술 전부 부합 (정정 없음). FM1 CSV 독립 재집계: 5717행×17열, overlap 1286 (HARD_KEY 739 + FOCUS_NAV 251 + QUICK_PANEL 221 + SETTINGS_DEFAULT_APP 42 + BASIC_FOCUS 33), NOT_FOUND 4431/5717, reuse_allowed=NO 5717/5717, TWO_RUN_GREEN 0/5717, IMPLEMENTED_* 0/5717, join_method exact_id 0. FM3 정정 2건: (1) "18-col manifest 4종" → 4종 중 3종만 18-col (BATCH5=11행·BATCH10=236행·BATCH11=64행); R2_LIST는 20-col (18-col + focus_model·model_confidence, 13행). 행 합계 324 및 handoff_status=DEVICE_VALIDATION_READY_CANDIDATE 324/324, result/판정 컬럼 부재(4/4 manifest)는 정확. (2) "행수-결과 건수 ±1~4 불일치" → 확인된 불일치는 ±1~3: batch2 +1 (annex STB_025 manifest 밖 GREEN), batch3 +1 (fixture annex VRC_061), batch4 +3 (본선 22 + 비본선 3 비집계), batch11 ±1 (잔여 선언 52 vs 분해 합 5+3+14+29=51). 크기 4 사례는 검사 파일에서 미발견. 또한 이 사례 대부분은 cited 4종이 아닌 11-col BATCH1~4 manifest 쪽 — cited 4종 내에서는 BATCH5가 11/11 정확 일치, batch10 C11의 chunk 21 vs 구현 12 (−9)는 RESULT_RECOVERY_BATCH10_C11에 명시 reconcile된 하향(무설명 불일치 아님).
- 검증 메모: coverage.notes: (1) FM1 fuzzy 최고점 0.47~0.59는 JOIN_SUMMARY 본문 서술로만 존재 — CSV join_confidence는 LOW/MEDIUM 범주값이라 수치 재현 불가 (모순은 아님, 독립 검증 불가일 뿐). (2) FM2 quantity "정량 미기록"은 정확 — 스크립트에 이질성 자체의 정량 기록 없음. 인접 정량으로 altbasic_tcid_collision_check.py docstring의 batch11 교차 충돌 4건, CLAUDE.md §8.2의 Excel dup TC ID 4 sheet·83건 존재 (이질성 아닌 tc_id 중복 정량). (3) FM3 notes의 "annex·probe manifest 밖 실행" 확인: THOR2J_HANDOFF_BATCH2 "carrier annex 11건 (manifest 밖)", batch3/4 annex, batch5 MSG_210 probe. (4) 조인 키 tc_id 안정성: 4종 manifest 모두 tc_id 1열 보유 + RESULT 문서들이 tc_id로 판정 기록 — 역환류 스키마 후보라는 서술과 정합. (5) improvement_candidates 3건은 확인된 사실과 모순 없음 (공용 모듈 부재·result-join 열 부재·reuse 0 모두 실측과 일치).
- 확인 파일 25건: `THOR2 - ALT Basic TC Audit/JOIN_SUMMARY_2026-06-08.md`, `THOR2 - ALT Basic TC Audit/overlap_join_2026-06-08.csv`, `scratch/s2_extract_183.py`, `scratch/s2_synth_prep.py`, `scratch/altbasic_tcid_collision_check.py`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH5_2026-06-11.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH11_2026-06-16.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_R2_LIST_2026-06-22.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH1_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH2_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH3_2026-06-10.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH4_2026-06-11.csv`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH5_2026-06-12.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH11_2026-06-17.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_R2_LIST_2026-06-22.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/QA_NOTES_BATCH10_2026-06-25.md`, `THOR2 - ALT Basic TC Audit/handoff_device_validation/THOR2J_HANDOFF_BATCH2_2026-06-10.md`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md`, `THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md`, `THOR2 - ALT Basic TC Audit/PROCESS_REVIEW_C11_2026-07-02.md`

---

## 횡단 패턴 (cross-cutting)

- 미실측 승격 금지 위반이 전 단계 공통 뿌리: cue 자동 확정(STAGE1 과배제 40%·강등 18.4%) → paraphrase literal·nav 후보 승격(STAGE2, C11 divergence 83%) → host focus 모델 분류(단말 미확인 시 38% 오류) → 부분 캡처 '부재' 단정(F0 카탈로그 오판). 각 단계의 회수 메커니즘(human 게이트, run1-discovery→backfill, device_confirm hedge, 전체 채록 R4)이 전부 '단말/사람 실증 후 확정'으로 수렴
- 위젯·포커스 모델 가정이 STAGE1→STAGE2→F0를 관통하는 최대 반복 실패원: node 일률 가정(R1 위음성 5/64) → 위젯 클래스 판별 원칙(ListView=list/RecyclerView=node) → C11 down-chain 모델 부재(re_scope 4) → bare focus 토큰=navigate 판정(61/61 inflation) → MGN focus 고착 판정 보류. focus 의미론의 단일 reference(reference_alt_focus_widget_model)로 수렴 중이나 소스 TC 서술 자체가 단말 위젯 모델을 전제하지 않음
- 암묵 fixture/precondition 전제가 판정 최다 탈락 사유(A_fixture 300/1130·D1 128/581)이자 F0 비승격(6/25)·gap-8(8/21) 공통 차단 요인 — safe-fixture 사이클(VRC 1 fixture→9건 재사용)과 MEDIA_SEED 공통 게이트가 실증된 회수 경로이며, 원본 TC의 precondition 공란 관행이 상류 원인
- headline vs potential 분리(false-progress 차단)가 원장 체인·non-gap 분모 규약·fail-closed 어휘·TWO_RUN_GREEN 승격 기준으로 단계 횡단 방어 기제를 형성 — 잠재량 inflation(+39·+18)을 headline +12로 방어한 실적. 반대로 이 분리가 없던 초기(cue 확정 EXCLUDE 오집계 211/428, 직독 199 vs 194)는 집계 드리프트 발생
- 수치 정합이 도구가 아닌 사람 손에 의존하는 구조적 취약: 판정 CSV-summary 불일치 4건, manifest result-join 부재, 18-col 헤더 복붙 유지, 카운트 추정, Excel 헤더 탐지 중복 구현 — '단일 원장 + 재집계 스크립트 생성' 원칙이 반복 제안되나 도구화 미완
- fail-closed는 결함이 아닌 설계 동작으로 반복 정당화(MGN_002·C01 7건·no-guess 보류 98 step) — false-progress 방지와 throughput의 트레이드오프가 구조화되어 있고, 해제는 항상 discovery/승인 선행. 다만 과보류(ADJUDICATE 24/53)도 실재해 fail-closed 경계의 정밀화 여지 존재
- 자동 분류기(cue·휴리스틱·host 모델)의 오류율이 양방향 모두 높아(false-pass 55.6%, 과배제 40%, false-KEEP 46.7%) '후보 슬리밍' 이상의 확정 권한 부여 금지가 데이터로 확립 — 직독 확정 yield 10~25%를 용량 계획 기준으로

## 미해결 질문 (open questions — 핀포인트 확인 후보)

- batch6~9의 단말 결과 문서가 디렉토리에 부재 — batch06/07/08 TC들의 단말 결과가 batch4/5 회수에 어느 정도 흡수됐는지 판별 불가 (원본 thor2j-tc-appium reports 대조 필요)
- carrier 보류 7건(SKT 4+KT 3) 시도 0 잔존 — SIM 스왑 세션 1회로 소진 가능한지, F0 carrier_fit 매트릭스의 실기 확인 필요
- f0_literal_catalog(62 rows)에 C11 사이클(2026-07-01~02) 수확분이 append되었는지 — observed_at 미집계로 미확인, 카탈로그 환류 사이클 준수 여부 점검 필요
- entry-detail ledger의 'executable' 컬럼이 620행 전부 True인 의미 — 문서에 정의 부재, 컬럼 의미 확정 필요
- WARN35 분모 271(batch10 합성 draft)과 manifest 236 TC의 관계(271=236+35?) — 명시 산식 부재, gate 분모 정의 확인 필요
- dump에 systemui 미포함 한계(STB_023)의 재발 여부 — 동류 TC 미배정으로 판별 불가, screenshot axis verifier의 실기 실증 필요
- MGN_005 dpad focus 모델(keyevent 3회 한정 관찰로 고착 여부 미확정)·MGN_006 썸네일 re_scope vs spec_gap 판정 — gap-8 사진 세팅(mutating 승인) 후에만 재관찰 가능
- focus_model defer 잔여 3건(HDK_069·LCH_014/015)과 CLK_030/031 tab vs list(model_confidence=device_confirm) — 단말 채록으로만 확정 가능
- batch2·3 manifest 행수(20)와 결과 건수의 ±1~4 불일치 대응표 — annex/probe가 manifest 밖 실행, 정확한 매핑은 원본 repo 증거 대조 필요
- PDM_040 spec-gap이 F0 빌드 한정인지 제품 공통인지 — 타 빌드/타 단말에서 oracle 술어 대응물 존재 여부 확인 필요 (CALC_009 CONFIRMED의 제품 공통 단정도 동일하게 타 빌드 비교 잔여)
- batch01 probe의 085/086 leaf(대시보드 2 viewport 미노출·USB dropout으로 UNVERIFIED 중단) — Phase 2 재probe 필요

## 부록 — 추출 커버리지·한계

### STAGE1 정규화·재판정 실패 유형 (THOR2 ALT Basic TC Audit)

- 읽음 24건 / 생략 0건
- 한계·주석: (1) 과업의 '디렉토리: undefined'는 Glob으로 'THOR2 - ALT Basic TC Audit/'로 확정 — 대상 파일 24개 전부 이 디렉토리에 존재, 목록 외 파일(ENTRY_DETAIL/NOT_A_KEY/FOCUS_CANDIDATE/ADJUDICATE ledger 등 6-26~29 산출물, overlap_join, C11 트랙)은 scope 밖으로 미분석. (2) md 15개는 전문 읽음; CSV 9개는 전문 붙여넣기 없이 python csv 파서(read-only)로 헤더·행수·판정 카테고리 분포·사유 상위 패턴만 집계, 개별 행 전수 직독은 미수행 — 행 단위 사유의 완전 enumeration은 본 추출 범위 밖. (3) CSV-summary 교차검증: REVIEW_MAPPING(1130=KEEP271/REVIEW812/EXCLUDE47, D1~D5=128/86/46/40/10), S2(183=29/71/57/26), CLOCK_CALC(96=12/39/45), WAVE3(280=13/112/87/68), DEFER_B(17=6/5/6) 모두 summary와 일치. (4) WAVE2 CSV KEEP=50 vs summary 49는 wave3 진입 전 표본 재검사에서 Camera#38 KEEP 회수(UNREVIEWED 211→204)가 CSV에 반영된 문서화된 정정 — 실패 아님. (5) REVIEW_MAPPING defect_class 공란 549 = pass1 행(strict2 581에만 부여, pass 컬럼과 산술 정합 확인). (6) batch06 summary vs selection CSV의 redesign_pattern 분포 불일치(25/17/12 vs 23/18/13)는 record로 등재. (7) wave1 = CLOCK_CALC 96 재판정을 지칭(별도 wave1 CSV 없음). REVIEW_UNREAD_REJUDGE는 대상 목록에 없었으나 DEFER ledger 정정의 근거 파일이라 집계에 포함. (8) batch05/07/08 summary는 대상 목록·디렉토리에 없어 해당 배치의 자체 실패 기록은 다른 문서의 인용(wave3 summary 내 batch05 gate, ledger 내 batch07/08)으로만 확인됨.

### ALT Basic 검수 원장(2026-06-26/29) 오류 유형·시정 규칙 추출

- 읽음 13건 / 생략 0건
- 한계·주석: 과업의 디렉토리 값이 'undefined'로 전달됨 — Glob으로 실제 위치 'THOR2 - ALT Basic TC Audit/' 확인, 대상 13파일 전부 그 안에서 발견·판독(누락 0). MD 6종은 전문 판독, CSV 7종은 헤더+전 행 카테고리 집계(Python csv, read-only). 정합 확인: 원장 체인 baseline 5/236이 3개 cascade에서 동일 재현, NOT_A_KEY 189=entry-detail ledger 189, focus_candidate 61=subtype ledger 61, ADJUDICATE 53=entry-detail 53. 판별 불가 항목: (1) entry-detail ledger의 'executable' 컬럼이 620행 전부 True인 의미(문서에 정의 없음); (2) ADJUDICATE_RESOLUTION의 headline 11이 어느 TC인지 개별 목록은 cascade의 tier0_adj_high−tier0 차집합으로 도출 가능하나 요청 범위 밖이라 미산출; (3) WARN35 문서의 분모 271은 batch10 합성 draft 수로 기재돼 있으나 236 TC와의 관계(271=236+35)는 문서에 명시 산식 없음 — 파일 기재값 그대로 인용. 관련 스크립트(scripts/altbasic_*.py)·spec 문서는 과업 대상 외라 미판독.

### ALT Basic C11 F0 실기 사이클 — 런타임 탈락 원인·갭 유형 추출

- 읽음 9건 / 생략 3건
  - 생략: catalog/f0_c11_nav_2026-07-01/**/*.xml dump 내용 (목록만 — 문서 기재 '10 dump'·'21 dump' 건수와 파일 수 일치 확인)
  - 생략: thor2j-tc-appium evidence/ 및 runner/driver 소스 (repo 외부, 과업 대상 아님)
  - 생략: 디렉토리 내 C11 외 batch 문서(STAGE1_*, REJUDGE 등 — 과업 지정 파일 아님)
- 한계·주석: ① 과업의 '디렉토리: undefined'는 파라미터 누락 — Glob으로 'THOR2 - ALT Basic TC Audit/'로 해소(지정 파일 전부 해당 디렉토리에서 발견). ② gap 번호 용어: 문서상 gap-9=미착수 9건(PFW 6+MGN_005/006+SST_016)의 authoring 큐 명칭이며, SST_016 회수 후 잔여 8건의 사진 precondition 게이트가 gap-8(MEDIA_SEED 제목)로 명명됨 — ledger CSV에는 gap 명시 컬럼이 없고 NOT_STARTED 8행이 대응(MEDIA_SEED가 인용한 'ledger gap-8 행'은 별도 필드로는 미확인). ③ PROCESS_REVIEW §5 표 수치(TWO_RUN_GREEN 8/NOTE 4/NOT_STARTED 9)는 리뷰 시점 스냅샷이고 후속 결정 반영 시 11/2/8 — ledger CSV 직접 집계로 11/2/8 확인(문서의 'ledger 우선' 규약과 정합). ④ f0_literal_catalog에 C11 사이클(2026-07-01~02) 수확분이 append되었는지는 observed_at 컬럼 미집계로 판별하지 않음. ⑤ SST_016의 divergence 유형 표(PROCESS_REVIEW §2.1 ③행)에는 '미실측'으로 기재되어 있으나 이후 gap-9 discovery로 실측·회수됨 — 문서 간 시점 차이며 모순 아님. ⑥ 원 기획서/규격 문서는 가용하지 않아(source_intent_source 전행 tc_yaml) '요구 해석 오류(①유형)' 확정 0은 소스 Excel 기준의 판단임.

### ALTBASIC_이전배치_런타임탈락원인 (batch1~11 + R2_LIST, F0 단말검증)

- 읽음 22건 / 생략 5건
  - 생략: THOR2 - ALT Basic TC Audit/handoff_device_validation/THOR2J_HANDOFF_BATCH1~5·BATCH10·BATCH11·R2_LIST .md 8종 (지시 목록 외)
  - 생략: THOR2 - ALT Basic TC Audit/handoff_device_validation/HANDOFF_PACKAGE_*.csv 6종 (지시 목록 외)
  - 생략: THOR2 - ALT Basic TC Audit/handoff_device_validation/DAY1_PATH_MANIFEST_2026-06-10.txt
  - 생략: THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C01_2026-06-26.md
  - 생략: THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md
- 한계·주석: ① 과업의 'undefined' 디렉토리는 'THOR2 - ALT Basic TC Audit'로 해석(glob으로 유일 매치 확인). ② VALIDATION_MANIFEST_BATCH5 파일명 날짜는 2026-06-11(RESULT는 06-12) — 지시문 'BATCH1~5' 범위 내로 판단해 포함. ③ batch6~9의 단독 단말 RESULT_RECOVERY는 본 디렉토리에 없음 — batch06/07/08은 정적 DVR handoff만 존재하고 해당 TC들의 단말 결과가 batch4/5 회수에 어느 정도 흡수됐는지는 문서상 명시가 없어 판별 불가. batch9 관련 파일은 디렉토리에 부재. ④ batch10의 실단말 결과는 상위 디렉토리 RESULT_RECOVERY_BATCH10_C01/C11(스코프 외, 미읽음)에 있음 — 본 추출의 batch10 기록은 무단말 prep QA 한정. ⑤ batch2·3의 manifest 행수(20)와 결과 건수(본선+annex+비승격)가 ±1~4 불일치 — annex/probe 항목이 manifest 밖에서 실행된 것으로 보이나 정확한 대응표는 원본(thor2j-tc-appium reports, 본 repo 밖)에 있어 미확인. ⑥ batch11 GREEN 12/64의 잔여 52는 '탈락'이 아닌 선결조건 보류 — 이후 사이클 결과(C01/C11 등 스코프 외 문서)는 반영 안 됨. ⑦ 비승격 25건의 사유 분류는 회수 문서의 명시 표를 그대로 집계했으며, LCH_121(fixture vs 간편모드)·LCH_185(단말설정 vs mutation)는 복수 축 성격이라 1개 축으로만 계상.

### ALT Basic — 프로세스·도구 사건 (파이프라인 자체 실패) + 커버리지·조인 갭

- 읽음 27건 / 생략 5건
  - 생략: scratch 16개 스크립트의 코드 본문(도크스트링/상단 주석 이후 부분 — 지시대로 미정독)
  - 생략: 3개 CSV의 행 단위 전문
  - 생략: docs/superpowers/plans/2026-06-29-altbasic-not-a-key-subtype-ledger.md (과업 목록이 06-29는 1건만 지정 — design spec만 읽음)
  - 생략: docs/superpowers 2026-06-26 c01-narrow-driver 문서 2건·2026-06-29 focus-candidate/adjudicate ledger 문서들(과업 목록 외)
  - 생략: doc/[THOR 2] ALT Basic Test Case_FULL.xlsx 원본(Excel dup 83건은 CLAUDE.md §8.2 기록 인용 — 본 세션 재검산 미수행)
- 한계·주석: 과업의 'undefined\' 경로 prefix는 전부 repo 루트(c:/Users/momen/Projects/tc-runner)로 해석됨 — BUG/JOIN 문서와 CSV 3종은 'THOR2 - ALT Basic TC Audit/' 하위에서 발견. overlap_join CSV의 naive comma-split 집계는 embedded comma로 21행 오분류돼 python csv 파서로 재집계했고 결과가 JOIN_SUMMARY_2026-06-08.md 수치와 정확히 일치(5,717행: 1867/1406/1196/561/503/184). KEEP_CONFIRMED는 271행(redesign_pattern: '-' 246 / popup_cancel 24 / roundtrip_restore 1) — record 1의 KEEP 풀 맥락. BUG_CALC_009는 제품 버그(CONFIRMED 15/15, 입력경로 2종 교차) 문서로 파이프라인 실패가 아니어서 record 제외(F0 런타임 스코프). §8.2의 2026-06-12 qa-suite 통합 행은 계획이지 실패 사건이 아니어서 제외. phantom 4건과 tc_id 충돌 4건은 동일한 4개 tc_id(CALC_027/028·SST_010/011)에 얽힌 별개 두 사건(스킴 비단사 + agent side-effect)이며, s2_finalize의 'KEEP supersede drop'이 s2_correct_phantom에서 오판으로 정정된 순서는 두 파일 도크스트링과 §8.2 기록으로 교차 확인. Excel sheet 내 dup TC ID '83건/4 sheet' 수치는 CLAUDE.md §8.2 기록 인용이며 본 세션에서 Excel을 직접 재검산하지는 않음(검산 도구는 altbasic_tcid_collision_check.py의 excel_dup_tcids). warn35의 분모 '236'은 batch10 manifest TC 수 기준 — WARN 판정 당시의 정확한 gate 분모(batch10 canonical 총수)는 읽은 범위에 명시가 없어 manifest 236을 사용.

---

*생성: 2026-07-03, workflow `wf_8c990ba1-181` (Extract 5 → Synthesize 1 → Verify 12). 원 JSON: 세션 task output `w2dwquns0`.*
