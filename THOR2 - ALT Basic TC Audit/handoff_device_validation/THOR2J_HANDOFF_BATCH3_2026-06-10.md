# thor2j-tc-appium 실기 검증 handoff — ALT Basic validation batch 3 (2026-06-10)

**기본 계약 = batch1/2 handoff 전체 승계** (F0 전용 / B27 미접촉 / 2-run / taxonomy / helper 생명주기 diff 0). 차분만 기술.

## 입력

- manifest 20건: `VALIDATION_MANIFEST_BATCH3_2026-06-10.csv` — 본선 = 신규 20 (batch1/2 중복 0)
- 구성: LCH 6 (long-press·팝업류 포함) + SET 3 + CALC 4 + MSG 3 + CAM_006 + VRC_065 + MGN_040 + PDM_020
- 목표 컨텍스트: **stretch 40 승격됨** (사용자 2026-06-10) — 누적 34 + 본 batch에서 +6 이상

## batch3 특수 계약

1. **fixture annex 1건 — VRC_061 재시도** (사용자 부분 승인 2026-06-10): 녹음 파일 1건 생성(수 초) → 목록 노출 검증(core) → **파일 삭제 + '저장된 녹음이 없습니다' 재확인 = 원상복귀 증명**. 삭제 실패 = CLEANUP_FAILED 즉시 보고. batch1 manifest 기실행분이므로 본선 20 밖 annex로 기록
2. **미승인 mutation 유지**: CLK_035 알람 삭제 / MSG_084 대화 삭제 = 불허 — 미접촉
3. **SELECTION_GATED류 3건** (LCH_133/134, MSG_116): 팝업 노출·취소만 — 등록 '확인'/입력 절대 금지, 종료 후 등록 0 재확인
4. **신규 primitive**: long-press (`mobile: longClickGesture`) — LCH_133/134/201
5. CAM_006: batch1 관찰상 슬로모션 모드 부재 가능 — 사진↔동영상 전환 성공 관찰 병기 후 DEVICE_FIT_SKIP 허용 (전환 = transient, 사진 복귀 필수)
6. SET_149 방해금지: 토글 접촉 절대 금지 (상태 변이)
7. batch1/2 literal 선반영: '추가'(+) · 계산기 desc 한글 연산자 · 간편설정=좌 스와이프 · parent-marker 게이트

## 회수 계약

batch1/2와 동일. 종료 시 3-batch 누적 성공률 집계 (stretch 40 달성 여부 보고).
