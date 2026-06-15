# REVIEW_MAPPING 재판정 — fresh 1,130 전수 + 강화 2-pass (2026-06-15)

throughput lever #1("재판정 ~1,000건 폭 확보가 STAGE1 합성의 선결"). 분류 마스터 `overlap_join_2026-06-08.csv`의 `recommended_next_action=REVIEW_MAPPING` 1,196 중 기재판정 63 제외 **fresh 1,130 전수** 재판정.

## 방법 (3단계 + 교차검증)

1. **1차 재판정** — Excel에서 1,130건 procedure/expected 원문 추출 → 워크플로 `altbasic-review-rejudge`(24청크 × 2단계 judge→rescue-verify, 48 에이전트). 잠금 규칙(WAVE2/ledger) + 과배제 40% 구제 필터. 커버리지 누락 48건(Camera/Contacts) gap 재판정 머지. → KEEP 581 / REVIEW 509 / EXCLUDE 40.
2. **false-KEEP QA** — KEEP 합성후보 60 층화 표본에 적대적 스켑틱 1패스 → **false-KEEP 46.7%(28/60)**. 결함: 암묵 fixture·비결정 verifier·암묵 pre-state 다수.
3. **강화 2-pass** — KEEP 581 전수를 D1~D5 disqualifier(암묵fixture/비결정verifier/암묵prestate/carrier분기/잠재mutation) 주입 재판정(워크플로 `altbasic-keep-strict-repass`, 13청크 × 2단계, 26 에이전트). → **KEEP_CONFIRMED 271 / 강등 310**. QA 추정(53% 확정)과 일치(교차검증 일관).

## 최종 분류 (fresh 1,130)

| verdict | 건수 | 비율 |
|---|---|---|
| **KEEP** (confirmed automatable) | **271** | 24.0% |
| REVIEW (재설계·fixture) | 812 | 71.9% |
| EXCLUDE | 47 | 4.2% |

### 강등 결함 분류 (581 KEEP → 310 강등)
D1_fixture 128 · D5_mutation 86 · D2_verifier 46 · D3_prestate 40 · D4_carrier 10. (1차 KEEP이 precondition 공란의 암묵 fixture와 LED/SubLCD/애니메이션/IME/배터리% 비결정 verifier를 놓쳤음.)

### KEEP_CONFIRMED 271 (합성 후보)
- 67 distinct (sheet, functionality) 그룹 — 합성 단위. confidence median 0.82.
- by sheet: Quick panel 48 · Launcher 40 · Hard Key 36 · Basic 21 · Call 21 · Contacts 20 · Camera 18 · Message 13 · Settings 12 · Clock 12 …
- 최대 클러스터 = 하드키 focus 네비게이션(Quick panel 33 · Hard Key 27 · Call 21 · Camera 16 · Basic 15 · Message 12 · Launcher Focus 군). → **클러스터별 템플릿/파라미터화 합성 가능**.

## 산출

- `REVIEW_MAPPING_REJUDGE_2026-06-15.csv` (1,130행, 보정 — verdict·defect_class·redesign_pattern·defer_category·pass[pass1|strict2])
- `KEEP_CONFIRMED_CANDIDATES_2026-06-15.csv` (271행 — 합성 후보 리스트)
- 작업 중간물: `_rejudge_chunks/`·`_strict_chunks/` (untracked 분석 intermediate)

## 다음 게이트 (승인 대기)

1. 271 KEEP_CONFIRMED → 67 클러스터 템플릿 STAGE1 합성 배치 (TC 파일 = 명시 승인 필요).
2. REVIEW 812는 DEFER 트랙(D_system_state/fixture/verifier) — 단말·fixture 결정 후.
3. STAGE1 합성 / F0 단말 / commit = 명시 승인.
