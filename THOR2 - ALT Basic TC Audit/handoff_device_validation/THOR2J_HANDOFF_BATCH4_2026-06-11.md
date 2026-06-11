# thor2j-tc-appium 실기 검증 handoff — ALT Basic validation batch 4 (2026-06-11)

**기본 계약 = batch1~3 handoff 전체 승계** (F0 `B06201249E0002F0` 전용 / B27 미접촉 / 2-run / taxonomy 8종 / DEVICE_FIT_SKIP≠FAIL / INFRA 분모 제외 / helper 생명주기 pre·post snapshot + 허용 3종 + uninstall + diff 0). 차분만 기술.

## 입력

- manifest 22건: `VALIDATION_MANIFEST_BATCH4_2026-06-11.csv` — batch1~3 중복 0 (기실행 누적 60)
- 구성: batch06 대표 10 (CALC 2·CLK 3·TTS 1·PDM 1·NMD 1·MSG 1·LCH 1) + **batch07 VRC fixture 9** + **editor/compose-entry 3** (MSG_201·CNT_132·CNT_137, 사용자 배정 승인 2026-06-11)
- run_order = 저위험→고위험 (1~10 일반 / 11~19 VRC 블록 / 20~22 editor·compose)
- 목표 컨텍스트: batch06 재설계 5패턴 첫 단말 실증 + DEFER ledger C/B 게이트 해제 근거 수집

## batch4 특수 계약

1. **VRC fixture 블록 (run 11~19, 사용자 승인 2026-06-11 = DEFER A-2)**: fixture **1회 생성으로 9건 연속 실행 후 삭제** (사이클 비용 절감). 생성 = 녹음→'**정지**'(정확 literal — '일시중지' 부분문자열 오매칭 금지)→'녹음 저장'→'확인'. 종료 = 파일 삭제 + '저장된 녹음이 없습니다' 재확인 (batch3 VRC_061 계약 승계). **중단/실패 시에도 삭제 시도** — 실패 = CLEANUP_FAILED 즉시 보고. 각 TC 종료 시 목록/메인 복귀 확인 후 다음 진행
2. **MSG_201 = compose 연쇄 게이트 1호**: 2-run GREEN 판정과 **별도로 draft 무생성 관찰 필드 보고** (대화방 list 전후 비교). draft 발생 = 중단 보고 + 임의 삭제 금지. 결과가 GREEN+무생성이면 DEFER ledger B 연쇄 13건 승격 판단 (tc-runner 측)
3. **CNT_132/137**: 연락처 개수 전후 일치 — 증가 시 중단 보고 (임의 삭제 금지). 저장 0
4. **redaction CHECK 5건** (NMD_005·MSG_201·CNT_132·CNT_137·VRC_064): 캡처/dump 산출물 redaction 검사 전 commit 금지, raw = local carry ([[project_redaction_policy_task41]] 계약)
5. **primitive**: drag-down 1건 (VRC_046 — 좌표 = 재생창 헤더 한정, 목록 영역 금지) / long-press 2건 (VRC_066·LCH_212 — batch3 기실증 `mobile: longClickGesture`)
6. **미승인 mutation 유지**: 알람 생성/삭제 · 대화 삭제 불허 — CLK_038은 알람 editor 진입+취소만 (저장 0, list 개수 전후 일치). MSW 모드전환·CAM 왕복은 본 batch 미포함 (2차)
7. **F0 빌드 문자열 기록** (현재 미기록 — 연결 시 `getprop ro.build.display.id` 채록)

## annex — CALC_009 BUG-GAP 매트릭스 (본선 후 별도)

OBSERVED(백스페이스 1탭 전체 삭제, Appium+adb 2경로 교차 재현) → CONFIRMED 전환 매트릭스: ① 연속 n≥5회 재현율 ② 재부팅 후 재현 ③ 타 빌드 가용 시 대조. 발생률 분자/분모 기록 (§4.3).

## 회수 계약

batch1~3 동일 (thor2j 실행 / tc-runner RESULT_RECOVERY 회수). 종료 시 RUNNABLE 누적 (52 + 본 batch 성공분) + 패턴별 GREEN 집계 (popup_cancel/observe_split/transient_input/selection_gated/roundtrip 실증 여부 = DEFER C 게이트 판단 입력).
