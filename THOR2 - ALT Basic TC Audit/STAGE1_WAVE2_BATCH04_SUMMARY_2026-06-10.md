# STAGE1 batch04 — wave2 KEEP 49 합성 + DVR handoff (2026-06-10)

입력 = wave2 재판정 KEEP 49 (전건 human_confirmed). 산출 = `stage1_wave2_batch04/ALTBASIC_{LCH,STB,VRC,CAM,MSG,CNT}_<id>_canonical.yaml` 49건 + `handoff_device_validation/HANDOFF_PACKAGE_BATCH04_2026-06-10.csv`.

## 계약

batch01~03 CTF + audit_meta 계약 재사용 (SEMI_AUTO_CANDIDATE / STAGE1_DRAFT / STATIC_ONLY / device_2run_green / focusrule_evidence_transfer=false) + 신규 키 2종:

| 키 | 값 | 근거 |
|---|---|---|
| `cleanup_candidate` | per-TC 원상복귀 절차 (예: Camera 모드 전환 → 사진 모드 복귀 필수) | transient 행위 원상복귀 요구 기록 |
| `carrier_fit` | `UNCONFIRMED_ON_TARGET_DEVICE` 11건 (STB 20~28, LCH 184/185) / 나머지 `not_applicable` | carrier pre TC = 단말 SIM 적합성 미확인, 불일치 시 skip(NOT FAIL) |

- entry = `app_launch_unresolved` 48건(launcher 경유, 패키지/component 발명 0) + `tap_navigation_required` 1건(MSG_361 Settings 경유)
- Camera/Message/Contacts의 촬영·발송·편집·저장 = **합성 0** (gate에서 동사 스캔으로 검증)
- safety_class 전건 NAVIGATION_ONLY, input_text intent 0

## 자동 검증 (전부 PASS)

parse 49/49 · source 중복 0 · 생성 ID ↔ KEEP 49 정확 일치 · REVIEW/EXCLUDE 혼입 0 · intent ⊆ {navigate, tap} · mutation/input/외부효과 동사 0 · am start/component/금지토큰 0 · verifier 후보 또는 verifier note 49/49 · cleanup_candidate 49/49 · pre 단일화 49/49

## 표본 리뷰 (계층 21건: L5/S4/V3/C3/M4/T2)

- **false-promote 0/21** — 2회 연속 ≤5% 충족 → **다음 batch부터 10% 리뷰로 축소 발동**
- 변환 오류 공통 결함 2건 발견 → **일괄 수정 + 재생성 + gate 재검증 GREEN**:
  1. source pre 실존 시 합성 pre와 병기 중복/충돌 (VRC_063/065, CNT_122, LCH_184/185) → source 원문 채택 + 판정 메타 적용으로 병합
  2. 행위형 pre('Home 키 입력')가 `state_precondition blocking:true` 오분류 → `nav_precondition blocking:false` 일괄
- 개별 문구 미세조정 0 (NOTE: MSG_101 '대화 이력 있음' fixture pre는 정직 기재 — 미충족 시 skip)

## handoff

49/49 → `DEVICE_VALIDATION_READY_CANDIDATE` (정적 완결성 5필드 충족: source trace / entry / verifier / cleanup / risk). **단말 검증 전 DEVICE_VALIDATION_READY 확정·RUNNABLE_NOW 주장 없음.**

- carrier_fit UNCONFIRMED 11 — F0 SIM 확인 후 해당 carrier subset만 시도
- redaction CHECK 2 (CNT_122 연락처 dump, MSG_101 대화 dump) — 캡처 산출물 redaction 검사 경유
- precondition 의존은 per-row 기재 — 미충족 시 skip (FAIL 아님)

## 누적 (2026-06-10 종료 시점)

| 지표 | 누적 | 구성 |
|---|---|---|
| STAGE1_DRAFT | **61** | batch03 12 + batch04 49 |
| DVR_CANDIDATE | **63** | Settings 기존분 14 + batch04 49 (batch03 12는 전환 대기) |
| 재판정 처리 | 524 | Clock+Calc 96 + wave2 428 |
| 수정 집계 | KEEP 61 / REVIEW 178 / 확정 EXCLUDE 74 / **미검토 후보 211 (통계 비합산)** | wave1+2 합산 |
