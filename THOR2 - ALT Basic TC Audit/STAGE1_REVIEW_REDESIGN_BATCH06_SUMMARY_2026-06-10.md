# STAGE1 batch06 — REVIEW_QUEUE 재설계 57건 합성 (2026-06-10, Day 2)

입력 = REVIEW_QUEUE 누적 **296** (wave1 39 + wave2 145 + wave3 112 — summary 종전 290은 wave2 표본 재분류 +6 반영 전 수치, 본 문서로 정정).
산출 = `stage1_review_redesign_batch06/ALTBASIC_{BSC,WTH,NMD,TTS,MGN,MSW,PDM,CLK,CALC,LCH,CAM,MSG,CNT}_<id>_canonical.yaml` **57건** + 선정 manifest + DEFER ledger.

**KPI: 목표 DRAFT +46 → 57 합성 (124%)**

## 모집단 처리

| 구분 | 건수 |
|---|---|
| 직독 판정 | 199 (wave3 cue무해 36 + wave1 39 + wave3 input/삭제/시스템 31 + wave2 직독·표본검사 93) |
| 합성 (batch06) | **57** |
| DEFER (ledger 6분류) | 142 — `REVIEW_REDESIGN_DEFER_LEDGER_2026-06-10.md` |
| 미직독 (cue 분류 유지) | 97 (wave2 input 30 / fixture 22 + wave3 토글 20 / fixture 25) — 후속 직독 대상 |

## 재설계 패턴 분포 (전건 batch3 단말 실증 패턴 기반)

| redesign_pattern | 건수 | 실증 근거 (batch3) |
|---|---|---|
| popup_cancel | 25 | SELECTION_GATED류 GREEN 4 (MSG_117, LCH_133/134, MSG_116) — 선택/팝업 → observe → 취소 |
| observe_split | 17 | assert 분리 — mutation 항 제거 후 노출 observe (DSP_001 dump-checked 방식 포함) |
| transient_input | 12 | INPUT_REQUIRED GREEN 5 (CALC) — 입력 → 검증 → clear, 확인-비활성 = 구조적 저장 불가 |
| selection_gated | 1 | LCH_212 — long-press 메뉴 observe (batch3 카탈로그 literal 재사용) |
| roundtrip_restore | 2 | CAM 전환 (CAM_006 전환 성공 관찰) — 왕복/복귀 cleanup 내장 |

## 계약 (batch04/05 + 신규 키 3종)

batch04 계약 전체 재사용 (cleanup_candidate / carrier_fit 포함) + 추가:

| 키 | 값 | 근거 |
|---|---|---|
| `redesign_source` | REVIEW_QUEUE_wave{1,2,3} | KEEP 합성과 구분 — REVIEW 재설계 출신 추적 |
| `redesign_pattern` | 5종 (위 표) | 단말 실증 패턴 매핑 |
| `redesign_removed` | 제거/변경한 mutation 요소 서술 | source 대비 변경의 정직 기재 (원문 무변경 시 "없음 — 가드 명시") |

- intent 허용 집합 = {navigate, tap, **input_text**} — batch04(navigate/tap만)와 다름: transient_input 패턴 도입 (기존 batch03 CALC input_text 선례)
- 신규 prefix 4종: BSC(1.Basic principle) / WTH(10.Weather widget) / TTS(4.Voice notification) / MSW(7.Mode Switch app)
- carrier_fit UNCONFIRMED 1건 (LCH_188 — SKT ZEM/KT 시나모롤)

## 자동 gate (전부 PASS)

parse 57/57 · manifest 정확 일치 57=57 · tc_id 중복 0 · 기존 드래프트 106건과 ID 충돌 0 · intent ⊆ {navigate, tap, input_text} · HARD 토큰(발송/전송/공유 실행/am start/component/shell) 0 · soft mutation 토큰 21 step **전건 cleanup_candidate + risk_note 가드 동반** · expected 누락 step 0 · 계약 키 17종 완비 · redesign_pattern manifest 일치

## 표본 리뷰 (계층 6건 = 10.5%, batch04에서 10% 축소 발동분)

NMD_020 / CLK_092 / LCH_085 / LCH_212 / CAM_098 / MSG_201 — source 원문 대조 재검: **false-promote 0/6**

## 안전 설계 공통 가드

1. mutation 인접 버튼(취소/확인)은 정확 literal 매칭 — partial 매칭 금지 (batch3 패턴 ②)
2. 필드 판독 = resource-id/필드 한정 — 전역 substring 금지 (batch3 패턴 ①)
3. 전후 비교 필수형 (값 유지/개수 무변경) = 사전 기록 step 명시
4. pre 미충족 = skip (FAIL 아님); 환경 의존 항 = NOTE; cross-screen 비교·재활성 검증 = 보강 axis 강등
5. CALC '=' 시행 기록 잔존 = NOTE 정직 기재 (기록 삭제 미실행)

## 단말 배정 전 사용자 확인 권고 (3건)

editor/compose-entry: **MSG_201**(새 메시지 '+' 첨부 리스트 — compose 진입), **CNT_132/CNT_137**(새 연락처 편집 화면 진입). 무입력·무저장 설계이나 '미승인 mutation(대화) 미접촉' 원칙의 경계 — 이탈 시 draft/저장 팝업 거동이 단말 미관찰 상태. 1차 run에서 draft 발생 시 중단 보고 설계.

## handoff 상태

57건 전부 `STAGE1_DRAFT` / `STATIC_ONLY` — **DVR handoff 패키지 미발행** (단말 미가용 Day 2). 단말 확보 시 정적 완결성 5필드 재점검 후 DEVICE_VALIDATION_READY_CANDIDATE 선별 발행 예정. **단말 검증 전 RUNNABLE 주장 없음.**

## 누적 (2026-06-10 Day 2 종료 시점)

| 지표 | 누적 | 구성 |
|---|---|---|
| STAGE1_DRAFT | **163** | Settings 32 + b03 12 + b04 49 + b05 13 + **b06 57** |
| REVIEW_QUEUE 잔여 | 239 | 296 − 57 (DEFER 142 + 미직독 97) |
| RUNNABLE_NOW | 52 (Day 1 동결) | 단말 미가용 — 변동 없음 |
