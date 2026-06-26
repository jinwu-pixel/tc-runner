# RESULT_RECOVERY — ALT Basic batch10 C01 narrow driver F0 검증 (2026-06-26)

- 단말: **F0 `B06201249E0002F0`** (AT-M140 THOR2, build RY07260601S, ko-KR). 다중 단말 환경 — `B2700125BW000115`/B27/ODIN2 **미접촉**(UDID 고정 가드 + bare adb 금지).
- 실행: thor2j-tc-appium `runner/altbasic_c01_driver.py` (+ `altbasic_narrow.py`), b1/fsnap 재사용. Appium 3.4.0 + uiautomator2 7.2.1.
- mutation-0: helper(io.appium.* 3종) 매 phase 후 uninstall, 잔존 0 검증. 위험 컨트롤 0 접촉.
- evidence: thor2j `evidence/altbasic_batch10_c01_{20260626(discovery), postbackfill_20260626}/` (local-only, gitignored).

## 실행 구조 (run1 ≠ TWO_RUN_GREEN 회차)

```
run1 (discovery / keycode-verification)  → candidate keycode 실증 + 실측 literal 채록 (TWO_RUN 미카운트)
   → literal backfill 4건 (run1 실측값, yaml expected target 갱신 + manifest 재생성)
fresh run A (run1) + run B (run2)        → TWO_RUN_GREEN 판정 (oracle 수정 후 fresh 2-run)
```

## RUNNABLE_NOW 후보 (TWO_RUN_GREEN) — 4

| tc_id | keycode (device-verified) | literal (backfill, run1 실측) | runA / runB |
|---|---|---|---|
| ALTBASIC_BSC_014 | 187 APP_SWITCH → recents | `모두 닫기` | SINGLE_RUN_PASS / RUN2_PASS |
| ALTBASIC_BSC_015 | 3 HOME → home | `전화` + `설정` (all-of) | SINGLE_RUN_PASS / RUN2_PASS |
| ALTBASIC_BSC_017 | 207 CONTACTS → 연락처 앱 | `연락처` | SINGLE_RUN_PASS / RUN2_PASS |
| ALTBASIC_BSC_019 | 27 CAMERA → 카메라 앱 | `사진` | SINGLE_RUN_PASS / RUN2_PASS |

### literal backfill 표 (paraphrase → 실측, expected_result_raw 의미 보존)
| tc_id | 기존(패러프레이즈) | 실측 backfill |
|---|---|---|
| BSC_014 | 최근앱 리스트 화면 | 모두 닫기 |
| BSC_015 | 홈스크린 | 전화 / 설정 (all-of) |
| BSC_017 | 연락처 앱 실행 초기 화면 | 연락처 |
| BSC_019 | 카메라 앱 실행 초기 화면 | 사진 |

## DEFERRED — 1

| tc_id | 상태 | 후속 |
|---|---|---|
| ALTBASIC_BSC_120 | ENTRY_FAILED (양 run) | precond '더보기 포커스 상태' 수동 진입 + dropdown 시그니처 device-verify → 2축(`focus_retained` ∧ `dropdown_absent`) 판정. 추측 금지. |

## FAIL-CLOSED (실행 0) — 7 + OBSERVE_ONLY — 1

| tc_id | result | 사유 |
|---|---|---|
| BSC_018, BSC_121 | UNSUPPORTED_ENTRY_DETAIL | `Message`/`지우기·취소` 표준 keycode 부재 → device key-discovery (추측 0) |
| BSC_031, BSC_071, BSC_072, BSC_073 | UNSUPPORTED_ENTRY_DETAIL | `숫자버튼`/`Navi U/D/L/R/OK` 미지정·vague-nav |
| BSC_124 | UNSUPPORTED_ENTRY_DETAIL | bare 연속 step + focus_absent 미검증 |
| BSC_025 | OBSERVE_ONLY | elevated §6 전원 모달 — 전원키 미입력(자동 실행 0) |

→ run1·runA·runB 3회 모두 8건 **단말 미접촉(Dev 세션 0)** — `_record` 직접 기록. 위험 키 0.

## discovery run1 (keycode 실증, TWO_RUN 미카운트)
candidate keycode 187/3/207/27 전부 정확 화면 도달 실증(recents `모두 닫기`·home 앱아이콘·`연락처`·camera `사진/동영상`). literal 패러프레이즈라 LITERAL_PENDING + 실측 채록 → backfill 입력.

## 산출물 / non-goals
- tc-runner(M, 무커밋): C01 4 yaml backfill(`stage1_review_mapping_batch10/`) · manifest 재생성(verifier 4행만 변경, drift 0) · 본 리포트. spec/plan(`docs/superpowers/`).
- thor2j(untracked, 무커밋): `runner/altbasic_narrow.py` · `runner/altbasic_c01_driver.py` · `tests/test_altbasic_*` (host 30 GREEN) · evidence(local-only).
- **commit/push 0 · staged 0 · B27/ODIN2 미접촉 · 위험 컨트롤 0 · helper 잔존 0.**
