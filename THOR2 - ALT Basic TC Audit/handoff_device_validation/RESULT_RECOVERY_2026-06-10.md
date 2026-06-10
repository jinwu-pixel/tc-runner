# thor2j 실행 결과 회수 — ALT Basic validation batch1 (2026-06-10)

**실행 주체**: thor2j-tc-appium (계약대로 — tc-runner는 본 문서로 결과 회수만)
**원본 결과**: `C:\Users\momen\Projects\thor2j-tc-appium\reports\ALTBASIC_BATCH1_RESULT_2026-06-10.md` + `evidence/altbasic_batch1_20260610/`
**단말**: F0 `B06201249E0002F0` (AT_M140 / Android 14) · B27 미접촉 · helper 3종 설치→uninstall→**package diff 0**

## RUNNABLE_NOW 승격 — TWO_RUN_GREEN 15건 (이것만 evidence)

| run_order | tc_id | source | 비고 |
|---|---|---|---|
| 1 | ALTBASIC_STB_001 | 13.Status bar#1.0 | UI 시간 ↔ `date` 분 단위 일치 (12h 표기 확정) |
| 2 | ALTBASIC_LCH_053 | 24.Launcher#53.0 | 단축 다이얼 = 홈 좌측 page |
| 3 | ALTBASIC_LCH_057 | 24.Launcher#57.0 | 퀵 패널(알림) 노출, 토글 접촉 0 |
| 4 | ALTBASIC_LCH_076 | 24.Launcher#76.0 | 앱 목록 도달 (헤더 비표시 — 앱 6종 집합 판정) |
| 5 | ALTBASIC_LCH_088 | 24.Launcher#88.0 | 간편설정 9항목 (만보기 below-fold) |
| 6 | ALTBASIC_LCH_112 | 24.Launcher#112.0 | 포토 슬라이드 쇼 '사진 추가하기' |
| 7 | ALTBASIC_SET_082 | 23.Settings#82.0 | deeplink 진입 |
| 8 | ALTBASIC_SET_081 | 23.Settings#81.0 | 설정홈→앱 tap 경로 |
| 9 | ALTBASIC_SET_143 | 23.Settings#143.0 | 위양성 1회 차단 후 정당 PASS (parent-marker 게이트) |
| 10 | ALTBASIC_SET_145 | 23.Settings#145.0 | leaf 전환 확인 (앱 목록 노출) |
| 12 | ALTBASIC_VRC_025 | 30.Voice Recorder#25.0 | 00:00 대기 화면, 녹음 버튼 접촉 0 |
| 14 | ALTBASIC_VRC_063 | 30.Voice Recorder#63.0 | '저장된 녹음이 없습니다' |
| 17 | ALTBASIC_MSG_100 | 26.Message#100.0 | 더보기 3항목 ('차단 및 스팸관리' literal) |
| 19 | ALTBASIC_MSG_128 | 26.Message#128.0 | '차단된 메시지가 없습니다' |
| 20 | ALTBASIC_CNT_223 | 27.Contacts#223.0 | 4종 라벨 ('빌드 버전' 1.0.0.1145) — 외부 tap 0 |

## DEVICE_FIT_SKIP 5건 (FAIL 아님 — 정적 등급 유지)

| tc_id | 축 | 사유 |
|---|---|---|
| ALTBASIC_CLK_035 | fixture | 알람 2건 실존 (삭제 = mutation 금지) — 알람 없는 상태 확보 시 재시도 가능 |
| ALTBASIC_VRC_061 | fixture | 녹음 파일 0 (VRC_063과 상호 배타 — 파일 생성은 mutation, 별도 fixture 결정 필요) |
| ALTBASIC_CAM_002 | 단말 기능 | '인물 사진' 모드 부재 (사진/동영상만) — corpus-단말 불일치 관찰 |
| ALTBASIC_MSG_084 | fixture | 대화 이력 실존 (114, 실종 경보 문자) |
| ALTBASIC_SET_144 | 단말 기능 | '대화창'(Bubbles) 항목 부재 — 알림 설정 전수 스캔 증거 |

실패 4축 분리 보고: entry 0 / verifier 0 / cleanup 0 / device-fit 5. INFRA_FAILURE 0.

## 카탈로그 수확 (학습 루프 입력 — 차기 STAGE2/anchor 반영 후보)

- **literal 확정 9건**: 12h status bar · 세계시각 · 빌드 버전(공백) · 차단 및 스팸관리(붙여쓰기) · 탐색 창 열기(drawer) · 단축 다이얼=좌측 page · 모든 앱 헤더 비표시 · 녹음 목록(content-desc) · 만보기 below-fold
- **검증 패턴 2건**: parent-marker 소멸 = leaf 전환 증명 (위양성 차단) · task 잔존 → 메인 marker BACK 복구
- **단말 기능 부재 2건**: 카메라 인물 사진 모드 / 알림 대화창(Bubbles) — THOR2 corpus와 단말 스펙 차이, EXCLUDE 아님(타 단말 재사용 가능)

## KPI 반영 (주간)

| 지표 | 목표 | 현재 |
|---|---|---|
| RUNNABLE_NOW | 20/주 (40 stretch) | **15** (batch1 1회로 75% 도달) |

F0 배치 성공률 = 시도 15 중 15 TWO_RUN_GREEN (100%, skip 제외) → **stretch 40 승격 판단 입력값 확보** (계약상 2회 실측 후 판단 — batch2 1회 추가 필요).
