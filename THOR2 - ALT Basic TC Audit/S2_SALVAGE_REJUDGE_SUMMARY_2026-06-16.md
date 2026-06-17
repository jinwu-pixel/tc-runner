# Stream 2 — REVIEW device-free 구제 직독 재판정 (2026-06-16)

REVIEW 812 중 자동분류상 device-free 구제권 183(redesign_pattern 有 × defer∈{C_verifier·E_binding·F_misc·B_compose})을 **직독 적대 재판정** → 실제 합성 가능 yield 확정.

## 방법

- 입력 183 = `_s2_salvage_input.json` (Excel 원문 procedure/expected/precondition join, missing 0).
- Workflow `altbasic-s2-salvage-rejudge` (24 에이전트, 9.4분): 12청크 judge → SALVAGE_CONFIRMED 적대 strict refute 패스(숨은 fixture·암묵 prestate·비결정 verifier·mutation·carrier). 불확실시 강등 원칙.

## yield — 29 / 183 (15.8%)

| verdict | n | % |
|---|---|---|
| **SALVAGE_CONFIRMED** | **29** | 15.8% |
| DEMOTE_DEVICE | 71 | 38.8% |
| DEMOTE_FIXTURE | 57 | 31.1% |
| EXCLUDE | 26 | 14.2% |

자동분류 상한 183 → 직독에서 **84% 탈락**. 이전 wave yield(Clock+Calc 12.5%·wave2 11.4%)와 정합 — cue 단독 과승격 패턴 재확인.

## 강등/제외 근거 (top)

- **DEMOTE_DEVICE 71**: 비결정 상태·unbound selector·폴더 닫힘 하드웨어 상태·연속 zoom 범위·선행 모드선택 영속 mutation 전제.
- **DEMOTE_FIXTURE 57**: 사전 데이터 필요 — 즐겨찾기 4+ 연락처·기존 대화함·메시지 fixture·연락처 검색 결과.
- **EXCLUDE 26**: 카메라 센서/라이브 프리뷰·SubLCD 물리 디스플레이·물리 LED 색상 시각 전용 verifier.

## SALVAGE_CONFIRMED 29 분포

- by sheet: Calculator 7 · Call 6 · Quick panel 4 · Hard Key 3 · Launcher 3 · Clock 3 · Simple settings 2 · Settings 1
- by pattern: transient_input 12 · popup_cancel 8 · observe_split 6 · selection_gated 3
- 전건 `verifier_sketch` 부여 (element-presence / 고정 literal / focus_state 계약, 구체 selector PENDING_F0).

## caveat

29는 **보수적 floor** — strict 패스가 적대적이라 일부 transient_input(예: Basic principle dialer 숫자표시 29/32/35.0)은 salvage-leaning reason에도 DEMOTE_DEVICE 처리됨. 최대 회수 원하면 해당 borderline DEMOTE_DEVICE 일부 spot-check 가능(별도).

## 산출 / 상태

- `S2_SALVAGE_REJUDGE_2026-06-16.csv` (183 전건 verdict·blocker·reason)
- `S2_CONFIRMED_29_2026-06-16.csv` (29 합성 후보 + verifier_sketch)
- **합성 미실행** — 29 STAGE1 합성은 별도 승인 대기. commit 미실행.
