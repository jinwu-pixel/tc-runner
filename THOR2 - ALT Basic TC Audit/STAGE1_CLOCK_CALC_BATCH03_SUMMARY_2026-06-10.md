# STAGE1 Clock+Calculator batch03 — 재판정 + 합성 summary (2026-06-10)

첫 throughput batch. 모집단 = `29.Clock`(71) + `32.Calculator`(25) EXPORT_TO_APPIUM 후보 96 (overlap_join 2026-06-08 기준, 실측 일치).

## 재판정 결과 (전수 96)

| 분류 | 건수 | 비고 |
|---|---|---|
| **KEEP** | **12** | Clock 4 (35/65/68/96) + Calculator 8 (1/3/5/7/9/11/40/51) |
| REVIEW_QUEUE | 39 | 재설계/fixture/검증수단 별도 트랙 |
| EXCLUDE | 45 | mutation·실행·외부효과·외부기준 |

KEEP 12/96 = **12.5% yield** — Clock corpus는 알람·타이머 조작(변이)이 지배적. 40건 미충족이나 **모호 건 승격 0** (운영 원칙 준수). 전체 기록 = `CLOCK_CALC_REJUDGE_2026-06-10.csv` (96행, 건별 사유).

### 분리 규칙 적용
- 알람 생성·수정·삭제·토글·라벨 저장, 타이머 Play/추가/삭제, 스톱워치 실행 → EXCLUDE (observe-only와 분리)
- Calculator 계산 입력 → **safety_class=INPUT_REQUIRED 분리** (단순 진입 NAVIGATION_ONLY와 등급 비혼용). '=' 미사용 입력 = transient(기록 미생성·AC 복구)
- CALC_051만 '=' 시행 포함 — 계산 기록 1건 생성 잔존을 risk_note에 명시 (결과 246 = 결정적 assert)
- verifier 수단 부재는 KEEP 불가: 색상 assert(76/77/78)·미명시 토스트(C49)·진동(C50)·외부 비교(C13/15/17, C53) → REVIEW 또는 EXCLUDE

### REVIEW_QUEUE 주요 묶음 (재설계 트랙 입력)
| 묶음 | 건수 | 재설계 방향 |
|---|---|---|
| fixture 전제(알람/타이머/세계시간/기록 존재) | 13 | safe-fixture(생성→관찰→정리) 사이클 설계 |
| transient input 검증(라벨 공백/최대문자/특수문자 등) | 12 | fixture + no-save 보장 후 승격 |
| observe 분리 재설계(Clock 설정 106/112/113, C13/15/17/48) | 7 | mutation step 제거·결정적 기대값 재작성 |
| 검증 수단 재설계(색상/토스트) | 5 | screenshot 비교 등 |
| 모호(C19/C45/82) | 3 | 원문 재확인 |

## batch03 산출 (KEEP 12)

`stage1_clock_calc_batch03/ALTBASIC_{CLK,CALC}_<id>_canonical.yaml` — batch02 스키마 정합. 공통: `SEMI_AUTO_CANDIDATE` / `STAGE1_DRAFT` / `STATIC_ONLY` / `device_2run_green` / `focusrule_evidence_transfer: false`.

**app-domain 좌표계 주의**: Settings menu-tree baseline 비적용 → `anchor_state: MISSING`, 앱 패키지/activity **미확정(발명 0)** → `entry_type: app_launch_unresolved` (launcher 경유 진입 후보).

## 검증 + 표본 리뷰

- 자동 검증: parse 12/12 · 필수필드 FAIL 0 · ID↔KEEP 정합 일치 · 금지토큰(RUNNABLE_NOW/runnable:true/FULL_AUTO/am start) **0**
- 표본 리뷰 = max(20, 20%) → **20건** (batch03 전수 12 + handoff 계층 8): **false-promote 0/20** (anchor 발명 0 / safety 과소 0 / source 밖 verifier 0 / 토큰 0)
- 공통 결함 2건 일괄 수정 (재생성·재검증 GREEN): 빈 expected_texts_candidate None 파싱 → `[]` 명시 / "스크린으로 입력" 사전조건 라벨 `state_precondition` → `input_method_constraint`
- NOTE (수정 안 함, 개별 미세조정 금지 룰): CALC_051 step2 verify "123"은 비판별(판별은 step3 "246"이 담당 — 콤마 보정 실패 시 123.123≠246으로 검출)

## 다음

1. 잔여 시트 재판정 폭 확대 — yield 12.5% 기준 draft 120/주 달성에는 ~1,000건 재판정 필요 (Launcher 107·Status bar 27·Voice Recorder 50·Camera 127·Message 88·Contacts 60 우선)
2. batch03 12건 handoff package 전환 (launcher 진입 = 정의된 경로, 내일 DVR 후보)
3. REVIEW_QUEUE 39 재설계 별도 트랙 (fixture 사이클·observe 분리)
