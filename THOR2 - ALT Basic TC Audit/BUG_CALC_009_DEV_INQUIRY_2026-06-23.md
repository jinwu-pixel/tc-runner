# 개발 문의 — CALC_009 계산기 백스페이스 1탭 전체 삭제 (2026-06-23)

> ALT Basic TC 감사 트랙 산출. 로컬 초안(개발 문의/티켓 제출 = 담당자 행위). redaction-clean(PII 0 — 패키지/resource-id/build id만, build id는 keep 정책).

## 1줄 요약
계산기에서 백스페이스(←) **1회 탭** 시 입력값 **전체**가 삭제됨 — source 기대는 **한 자리** 삭제.

## 분류 (§6.4)
| 필드 | 값 |
|---|---|
| 기능 영역 | 계산기 키패드 입력/편집 (백스페이스) |
| 진단 상태 | **CONFIRMED** (F0 / build RY07260600S 관측 한정 — 제품 공통 단정은 타 빌드 비교 전 보류, NOTE) |
| 이슈 상태 | OPEN (개발 문의) |
| 단말 / 빌드 | AT-M140 ("스타일폴더 2", THOR2) · build `RY07260600S` · ko-KR · 480x800 |
| 앱 | `com.hnlens.calculator` |
| 관련 TC | `ALTBASIC_CALC_009` (ALT Basic Excel "32.Calculator" row 9) |

## 기대 vs 실제
- **source 기대결과**: "숫자 한개씩 삭제가 되어야 한다"
- **실제 동작**: 백스페이스 1탭 → display 전체 비워짐 (`"123"` → `""`, 기대 `"12"`)

## 재현 절차 (결정적)
1. `com.hnlens.calculator` 실행 (display/result 빈 상태)
2. `1` → `2` → `3` 순차 입력 → `com.hnlens.calculator:id/display` = `"123"` (precondition 통과 확인)
3. 백스페이스(←) 키 **1회 short tap** — adb `input tap <x> <y>` 사용 (Appium click의 long-press 오인 가능성 배제)
4. **기대**: display = `"12"` (한 자리 삭제)
5. **실제**: display = `""` (전체 삭제)

## CONFIRMED 근거 (매트릭스)
- **15/15 전체삭제** = 연속 5회 + **재부팅 후** 5회 + 재현 run2 5회 (전부 전체삭제, 한 자리 삭제 **0회**)
- **입력 경로 2종 교차** = Appium click + adb `input tap`(short) — 양쪽 동일 결과 ⇒ **테스트 도구 아티팩트 아님** (long-press 오인 배제)
- **ground truth** = `com.hnlens.calculator:id/display` resource-id 직접 판독 (전역 substring 위양성 배제)

## 증거
| 항목 | 경로 (thor2j-tc-appium repo) |
|---|---|
| CONFIRMED 매트릭스 (run1/run2 각 main + trial1~5, .png/.xml) | `evidence/altbasic_batch4_20260611/run{1,2}/ALTBASIC_CALC_009_MATRIX5/` |
| 최초 관찰 | `evidence/altbasic_batch3_20260610/run1/ALTBASIC_CALC_009/` |
| 분석 기록 (OBSERVED→CONFIRMED) | `THOR2 - ALT Basic TC Audit/handoff_device_validation/RESULT_RECOVERY_BATCH3_2026-06-10.md` · `RESULT_RECOVERY_BATCH4_2026-06-11.md` (annex) |

trial 스냅샷의 `id/display` text=`""`가 백스페이스 후 전체삭제 상태를 직접 보여줌.

## Scope / NOTE
- 본 결과는 **F0 단말 + build RY07260600S 관측 한정**. 타 빌드/타 단말 비교 미수행 → "제품 공통 결함" 단정 보류.
- 백스페이스 핸들러가 short tap에서 전체 삭제로 동작하는 것이 **사양인지 결함인지** 개발 측 코드 확인 요청 (1자리 삭제가 source 기대).

## 문의 요청 사항
1. `com.hnlens.calculator` 백스페이스(←) 핸들러가 single short tap → 전체 삭제로 동작하는 것이 **사양 / 결함** 중 무엇인지.
2. (결함이라면) 수정 대상 빌드 + 타 빌드 영향 범위(회귀 필요 여부).
