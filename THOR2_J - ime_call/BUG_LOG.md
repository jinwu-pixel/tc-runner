# BUG_LOG — THOR2_J ime_call (AT-M140 다이얼러 하드키)

## 요약표
| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |
|---|---|---|---|---|---|---|
| IME-CALL-001 | 다이얼러 하드키 입력 | CONFIRMED | OPEN | a11y 연결 후 하드 `*` 삼킴 (sticky, 재부팅 리셋) | `IME_CALL_001_A11Y_STAR_REGRESSION` | RESULT_2026-07-07 §ISSUE-1 |
| IME-CALL-002 | 다이얼러 하드키 입력 | OBSERVED | OPEN | 하드 숫자키 1프레스 → 2회 입력 (희귀 transient) | — | RESULT_2026-07-07 §ISSUE-2, bugreport |

---

## IME-CALL-001 — 하드키 `*` 삼킴
- **기능 영역**: 다이얼러 하드 키패드 입력
- **진단 상태**: CONFIRMED
- **이슈 상태**: OPEN (개발 제보 대기)
- **단말**: AT-M140 (083·043·115 교차)
- **앱**: com.android.dialer 1.0.0 (build 1638, ls_dialer) / IME iWnn 2.23.1 (build 10)
- **요약**: 접근성/자동화(a11y) 연결이 1회 발생하면, 이후 다이얼러 재실행 시 iWnn이 하드 `*`를 소비. 재부팅 전까지 sticky.
- **기대 결과**: 하드 `*` → 번호 필드에 `*` 입력
- **실제 결과**: `*` 미입력 (숫자·`#` 정상)
- **재현 절차**: (정) a11y 도구 실행 이력 상태 → 다이얼러 실행 → 하드 `*` 미입력 / (역) 재부팅 or iWnn 비활성 → 정상. 최소쌍 = REF R4(클린 통과)/R5(dump 1회→삼킴)/R6(sticky)
- **증거**: RESULT_2026-07-07 §ISSUE-1 (IME A/B 2/2, 물리키 전용 확정, kernel getevent clean, 단말 무관)
- **관련 TC**: `TC_IME_CALL_001_A11Y_STAR_REGRESSION.yaml` (`MANUAL_LOCAL`, 표준 tc-runner/Appium 실행 금지)
- **개발 문의**: `DEV_INQUIRY_IME_CALL_001_2026-07-13.md`
- **정정 이력**: 초기 "다이얼러 2회차 재실행" 가설 → REF 재부팅 최소쌍으로 **a11y 연결 트리거**로 정정 (2026-07-07)

## IME-CALL-002 — 하드키 숫자 이중 입력
- **기능 영역**: 다이얼러 하드 키패드 입력
- **진단 상태**: OBSERVED
- **이슈 상태**: OPEN
- **단말**: AT-M140 (083, 최초 관찰)
- **앱**: com.android.dialer 1.0.0 (build 1638, ls_dialer) / IME iWnn 2.23.1 (build 10)
- **요약**: 하드 숫자키 1프레스 → 번호 필드에 숫자 2회. `*`/`#`는 1회.
- **기대 결과**: 숫자 1프레스 → 1회 입력
- **실제 결과**: 2회 입력 (2026-07-07 11:18 사용자 관찰). 다이얼패드 첫 터치로 치유 후 소실
- **재현 절차**: 미확보. 오늘 모드 잔존(数字·かな)·a11y 조합 매트릭스 전부 미재현. phone 필드 numeric passthrough + one-shot transient + 관측자 효과로 강제 불가
- **증거**: bugreport-alt_thor2-*.txt (입력 전 계층 1회 대칭 전달 입증 → 이중은 미로깅 텍스트 계층), RESULT_2026-07-07 §ISSUE-2
- **관련 TC**: —
- **정정 이력**: —

---

## 세션 결과 (2026-07-07)
- IME-CALL-001 CONFIRMED (a11y 트리거, 3 유닛 검증)
- IME-CALL-002 OBSERVED 유지 (강제 재현 불가 → 야생 포획 하니스 `capture_harness.sh`로 추적)
- 단말 정리: 083·115 재부팅 권장 (sticky `*`삼킴·TalkBack 리셋)
