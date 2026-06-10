# thor2j 실행 결과 회수 — ALT Basic validation batch3 (2026-06-10)

**원본**: `C:\Users\momen\Projects\thor2j-tc-appium\reports\ALTBASIC_BATCH3_RESULT_2026-06-10.md` + `evidence/altbasic_batch3_20260610/`
**단말**: F0 · B27 미접촉 · helper diff 0 · 미승인 mutation(알람/대화) 미접촉

## RUNNABLE_NOW 승격 — TWO_RUN_GREEN 18건

본선 17: LCH 055/059/077/201/133/134 · SET 086/827 · CALC 005/007/040 · MSG 116/183/186 · VRC_065 · MGN_040 · PDM_020
fixture annex 1: **VRC_061** (사용자 부분 승인 — 생성→검증→삭제 원상복귀 완료, 잔존 0; batch1 DEVICE_FIT_SKIP → GREEN 전환)

계층 누적: SELECTION_GATED류 GREEN 4 (MSG_117 + LCH_133/134 + MSG_116) · INPUT_REQUIRED GREEN 5 (CALC 003/011/005/007/009除外) · fixture-cycle GREEN 1 (VRC_061) — **REVIEW 풀 290 재설계 트랙의 실증 기반 확보** (assert 분리·팝업 취소·fixture 사이클 패턴 전부 단말 검증됨)

## 비승격 3건

| tc_id | 분류 | 사유 |
|---|---|---|
| SET_149 | DEVICE_FIT_SKIP | '방해금지' 항목 단말 미탑재 — 알림 전수+설정홈+소리 3중 탐색 증거 |
| CAM_006 | DEVICE_FIT_SKIP | '슬로모션' 모드 부재 (사진↔동영상 전환 자체는 성공 관찰 — 부분 기능 확인) |
| **CALC_009** | VERIFIER_FAILED → **BUG-GAP 후보 (진단: OBSERVED)** | **백스페이스 1탭 = 전체 삭제 동작.** source 기대 = 한 자리 삭제. Appium click + adb `input tap`(short) 2개 입력 경로 교차 재현, formula id 판독 + 스크린샷 증거. CONFIRMED 전환에는 추가 매트릭스(타 빌드/재부팅 후/연속 n회) 필요 — 개발 문의 후보 |

## 카탈로그 수확 (batch3)

- literal 8건: 계산기 formula/result id · 기록=display 드래그('기록이 없습니다.') · '녹음 중지'/'녹음 저장'+'확인' · 메시지 설정 알림=below-fold · 만보기 imageView 단일 clickable · long-press 메뉴('즐겨찾기 버튼에 등록'/'홈 화면에서 삭제') · 통화 녹음=필터 경유 · 방해금지 미탑재
- **자동화 패턴 2건**: ① display/필드 검증은 resource-id 한정 판독 (전역 substring = 키패드 라벨 위양성) ② partial 매칭 금지 사례 — '정지'⊂'일시중지' (mutation 인접 버튼은 정확 literal 필수)

## KPI 최종 (2026-06-10, 3-batch)

| 지표 | 목표 | 달성 |
|---|---|---|
| RUNNABLE_NOW | 20 (stretch **40** 승격분) | **52** — stretch 130% |
| 2-run 성공률 | — | 52/54 시도 = 96.3% (FAIL 2 = SPM_062 fixture 의존 · CALC_009 BUG-GAP 후보) |
| DVR 잔여 풀 | — | 24 (carrier 7 보류 + redaction/NMD 8 + 미승인 fixture 2 + 기타 7) |
