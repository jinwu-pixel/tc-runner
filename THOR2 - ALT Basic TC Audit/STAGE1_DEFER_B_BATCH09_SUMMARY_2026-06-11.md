# STAGE1 batch09 — DEFER B 재판정 + compose-entry redesign 합성 (2026-06-11)

입력 = DEFER ledger **B. compose-entry 연쇄 17건** (MSG 13 + rejudge 신규 4). B-gate 해제 근거 = MSG_201 TWO_RUN_GREEN + draft 무생성 (`handoff_device_validation/RESULT_RECOVERY_BATCH4_2026-06-11.md`).
산출 = `stage1_compose_defer_b_batch09/ALTBASIC_MSG_{191,202,203,205,210,296}_canonical.yaml` **6건** + `DEFER_B_REJUDGE_2026-06-11.csv` (17 판정) + `handoff_device_validation/VALIDATION_MANIFEST_BATCH5_2026-06-11.csv` (11건).

## 재판정 (17 = KEEP 6 / REVIEW 5 / EXCLUDE 6)

| verdict | 건수 | tc |
|---|---|---|
| KEEP (합성) | 6 | MSG 191 · 202 · 203 · 205 · 210 · 296 |
| REVIEW (보류) | 5 | MSG 218(MMS toast 미실증) · 266(클립보드 외부효과) · 326(218 동축) · 393(202 중복+carrier) · SPM_076(MSG_325 dedup) |
| EXCLUDE | 6 | MSG 207·208(연락처 fixture) · 297·298·372·455(사진 fixture) — 전부 이중 게이트 |

사용자 제외 필터 적용: fixture 이중 게이트 / 연락처 기본계정 / 알람 / 사진 데이터 종속 → EXCLUDE 6 전건 해당. 알람 종속 항목은 B 카테고리 내 없음(A-1 풀).

## redesign 패턴 (6건)

| pattern | 건수 | tc |
|---|---|---|
| popup_cancel | 1 | MSG_191 (빠른 답장 팝업/목록 컨테이너 노출 observe — 문구 내용/삽입 비단정) |
| observe_split | 5 | MSG 202(제목 입력창 노출) · 203(앨범 picker 전환·LCH_121 동형) · 205(동영상 picker 전환) · 210(벨소리/오디오 메뉴 노출) · 296(더보기 메뉴 중복 없음) |

공통 가드: compose-entry 전건 BACK 이탈 시 **draft('임시') 무생성 검증** step 내장 (B-gate 계약). 선택/삽입/첨부/실행 tap 0. 203/205 = picker 사진/동영상 노출 비단정(데이터 비종속) + 캡처 정책 LOCK.

## 검토 보정 (2026-06-11, F0 실행 전 3건 — 사용자 검토 반영)

1. **LCH_121/123 verifier 명시** (P1): manifest `verifier_candidates` 공란('—') → 구조 판독 기준 기재. LCH_121 = picker 컨테이너/그리드 presence(사진 콘텐츠 비의존), LCH_123 = 앱 아이콘 집합 presence(LIT-007, 헤더 의존 금지). → 11건 전건 verifier 비공란.
2. **picker 캡처 정책 LOCK** (P1): MSG_203·MSG_205·LCH_121 risk에 명시 — 현 redaction gate PNG 마스킹 불가 → **스크린샷 local-only(커밋 금지) · 커밋 후보 = redacted XML/JSON/요약만 · 사진/미디어 접근 권한 팝업 시 '허용' 금지 = DEVICE_FIT_SKIP**.
3. **MSG_191 가정 축소** (P2): '시스템 기본 문구 fixture 무관' 미실증 가정 제거 → **팝업·목록 컨테이너 노출만 판정**(문구 내용/개수 비단정). expected_texts '—', title/verifier 갱신.

## 자동 gate (전부 GREEN)

parse 6/6 · tc_id 중복 0 (기존 드래프트 충돌 0) · intent ⊆ {navigate, tap} · HARD 토큰(am start/component/shell/발송 실행) 0 · soft mutation 토큰 전건 cleanup_candidate + risk_note 가드 동반 · expected 누락 step 0 · 5필드(source·entry·verifier·cleanup·risk) 결측 0 · 계약 키 완비 · redaction residual_scan PASS (PII/cred/phone/IMEI 0).

## 검증 manifest (batch5 = 11건)

`VALIDATION_MANIFEST_BATCH5_2026-06-11.csv` (18필드, batch08 handoff 스키마 동일):
- 신규 batch09 = MSG 191·202·203·205·210·296 (6)
- 기존 batch08 = LCH 121·123·223 + PDM 028·035 (5) — **CNT editor-entry 7건은 ⓔ 게이트(기본 계정 다이얼로그)로 제외**
- 전건 `DEVICE_VALIDATION_READY_CANDIDATE` / `STATIC_ONLY` — **단말 검증 전 RUNNABLE 주장 없음**

## 단말 미접촉 / 다음 게이트

- 본 작업 단말 호출 0 (정적 합성 + python gate만). F0 미연결 유지, B27 미접촉.
- **F0 연결 + 2-run 실행 = 별도 승인 대기** (manifest 준비 완료 — 승인 시 thor2j 배정).
- commit/push = 별도 승인 대기 (uncommitted).
- REVIEW 5건 = verifier 실증(218/326 MMS) / dedup 결정(393/SPM_076) / 클립보드 외부효과 정책(266) 후 후속 사이클.
