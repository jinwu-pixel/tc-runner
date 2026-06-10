# thor2j-tc-appium 실기 검증 handoff — ALT Basic validation batch 2 (2026-06-10)

**기본 계약 = batch1 handoff 전체 승계**: `THOR2J_HANDOFF_BATCH1_2026-06-10.md` (F0 `B06201249E0002F0` 전용 / B27 미접촉 / 2-run / taxonomy 8종 / INFRA 분모 제외 / Appium helper 생명주기 6항 — pre/post snapshot·허용 3종·uninstall·중단 시 cleanup·diff 0 / 단말 호출 = 명시 승인 후). 본 문서는 batch2 차분만 기술.

## 입력

- 실행 manifest (20건): `VALIDATION_MANIFEST_BATCH2_2026-06-10.csv` (동일 폴더, `yaml_path` = tc-runner repo-root 상대)
- batch1 결과 회수: `RESULT_RECOVERY_2026-06-10.md` — TWO_RUN_GREEN 15 / DEVICE_FIT_SKIP 5 / 실패 0
- 실행 도구 재사용: thor2j `runner/altbasic_validation_batch1.py`의 primitive(클릭형 ancestor tap·parent-marker 게이트·task 잔존 BACK 복구) — batch2용 per-TC 함수 추가

## batch2 구성 (선정 근거)

| 축 | 내용 |
|---|---|
| 구성 | batch03 6 (CLK 065/068/096, CALC 001/003/011) + batch04 9 (LCH 054/063/093/097, VRC_058, CAM_097, MSG 102/117/143) + batch05 5 (SPM_062, DSP 001/005, MGN_024, PDM_019) |
| 신규 시트 커버 | Dura Speed / 돋보기 / 만보기 / 스팸 — batch05 첫 실측 |
| **안전 계층 통제 확장** | NAVIGATION_ONLY 17 + **INPUT_REQUIRED 2** (CALC_003/011 — '=' 미사용·AC 복구 transient) + **SELECTION_GATED 1** (MSG_117 — batch1 제외분, 생성 데이터 0 계약 부착 후 재진입) |
| batch1 literal 반영 | 세계시각(CLK_065) · 차단 및 스팸관리(MSG_102/143/117, SPM_062) · 간편설정=좌 스와이프(LCH_054) · 모든 앱 헤더 비표시→앱 이름 집합 판정(LCH_097) |

## batch2 특수 계약

1. **세션 시작 시 SIM read-only probe**: `getprop gsm.sim.operator.alpha` + `dumpsys telephony.registry`(읽기만) → carrier 확인 기록
2. **carrier annex 11건** (manifest 밖): STB_020~028 + LCH_184/185 — probe 결과와 일치하는 carrier subset만 annex로 실행 가능 (불일치 = 시도 없이 보류, DEVICE_FIT_SKIP 기록도 하지 않음 — 시도 자체를 안 함)
3. **fixture annex 3건** (사용자 mutation 승인 대기): CLK_035(알람 2건 삭제) / MSG_084(대화 삭제) / VRC_061(녹음 파일 생성) — **승인 전 실행 금지**, 승인 시 batch2 세션 말미에 fixture 조성 → 재시도 → 원상 보고
4. **MSG_117 (SELECTION_GATED)**: '+' 후 취소만, 저장/확인 tap 절대 금지. 취소 후 '차단된 문구가 없습니다' 재확인 = 생성 데이터 0 검증. 미노출 시 CLEANUP_FAILED + 즉시 보고
5. **CALC INPUT 2건**: '=' 키 절대 미사용(계산 기록 생성 차단). 입력 수열 제안값(-5 / 123)은 1차 관찰에서 키패드 형태 확인 후 고정. AC 복구 실패 = CLEANUP_FAILED
6. **MGN_024 / 카메라 권한 팝업**: 출현 시 RISK_BLOCKED 기록 후 정지 — 수동 동의는 별도 절차 (CAM_002 계약과 동일)
7. **stretch 40 판단 입력**: batch2 종료 시 2회 실측 성공률 집계 (batch1 15/15 + batch2 시도분) — 판단 자체는 사용자 결정

## 회수 계약

batch1과 동일 — TWO_RUN_GREEN만 RUNNABLE_NOW evidence, 실패 4축 분리, literal 수확은 RESULT_RECOVERY 시리즈에 누적.
