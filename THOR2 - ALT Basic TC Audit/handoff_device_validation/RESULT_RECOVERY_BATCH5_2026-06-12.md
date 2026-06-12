# thor2j 실행 결과 회수 — ALT Basic validation batch5 (2026-06-12, 보정 반영 최종)

**원본**: `C:\Users\momen\Projects\thor2j-tc-appium\reports\ALTBASIC_BATCH5_RESULT_2026-06-12.md` + `evidence/altbasic_batch5_20260612{,_msgfix_rerun,_msg210probe}/`
**단말**: F0 (build **RY07260600S** 채록) · B27 미접촉 · helper pre 218 == post 218 (추가분만 uninstall) → **persistent mutation 0 / post-state diff 0** (영속변경·대화·draft·파일 0)
**실행**: orchestrator `_orchestrate_batch5_20260612.py` — date override 20260612 · Appium `/status` 게이트 · 모든 종료 경로 finally(helper 복원+서버 taskkill) · subset/probe 모드 · F0 build 채록

## 최종 집계 (11) — TWO_RUN_GREEN 7 / DEVICE_FIT_SKIP 3 / ENTRY_FAILED 1 → RUNNABLE_NOW 66 → **73**

| 판정 | tc_id |
|---|---|
| **TWO_RUN_GREEN 7** | MSG_191 · MSG_202 · **MSG_203** · **MSG_205** · MSG_296 · PDM_028 · PDM_035 |
| DEVICE_FIT_SKIP 3 | LCH_121(사진 fixture) · LCH_123 · LCH_223 (간편모드 런처 기능 부재) |
| ENTRY_FAILED 1 | MSG_210 (첨부 '오디오' 항목 부재 — spec-device 갭) |

## verifier 보정 — MSG_203/205 (원 CLEANUP_FAILED = 결함, 단말 잔존 0 확정)

- 원 증상 `draft=False list_match=False`는 `_compose_exit_verify`의 **무조건 BACK 2회**가 picker 케이스에서 홈까지 과이탈 → 전체 text 홈-vs-메시지 거짓 불일치. 단말 잔존 아님(draft 부재 + run2 before==run1 before 동일).
- **보정**(무조건 2 BACK 제거 → 상태 인지 재anchor: 이탈→저장팝업→메인확인→HOME이면 런처-경유 재진입→대화목록·draft 비교, HOME 안착 불인정) 후 **MSG_203/205 재실행 → 양 run `on_main=True list_match=True draft=False` = TWO_RUN_GREEN**. persistent mutation 0 재확인. **재실행 중 금지 선택·첨부·권한 허용·임의 복구 0, 영속 잔존 0**.

## MSG_210 — 스크롤 재관찰 완료 → 오디오 첨부 부재 확정 (ENTRY_FAILED 유지)

첨부 메뉴 아래쪽 스크롤(끝 도달, tap 0): 앨범·카메라·동영상·동영상 촬영·연락처·제목만, `오디오`/`벨소리` 부재 = below-fold 배제. **spec-device 갭**(타 빌드 비교 전 BUG 단정 보류 NOTE).

## 간편모드 런처 (LCH 3 = DEVICE_FIT_SKIP)

홈 아이콘 라벨 부재(9 null) + 앱서랍 검색 부재 + 플랫 12앱 → 표준 런처 전제 TC 미적용. resource-id/bounds + 슬라이드쇼 fixture 재설계.

## 카탈로그 — +5 rows, 누적 62 (LIT-035 picker external·오디오 부재 / LIT-036 만보기 / STR-009 간편모드 / FIT-011 슬라이드쇼 / FIT-012 오디오 부재 확정)

## 후속

1. MSG_210 spec-device 갭 — 타 빌드 비교 시 BUG-GAP 승격 검토 (현 NOTE)
2. LCH 간편모드 재설계 (selector + 슬라이드쇼 fixture)
3. **commit/push 미실행** — 본 세션 승인 = 단말 실행까지. `907b4bb`·batch5 결과 그 사이 push 안 함. untracked: RESULT 2종 + 카탈로그 +5 + orchestrator + batch5.py 보정(thor2j) + evidence(local-only). 보정 사이클 종료 → batch commit 승인 대기

## 세션 결과

- 실행일 2026-06-12 / 단말 F0 RY07260600S / 앱 ALT Basic (Message·Pedometer·Launcher)
- 범위 batch5 11건 2-run + verifier 보정 재실행(MSG_203/205) + MSG_210 스크롤 probe
- PASS = TWO_RUN_GREEN 7 → RUNNABLE 66→73
- 신규 발견 = 간편모드 런처(STR-009) · 오디오 첨부 부재(FIT-012, 스크롤 확정) · picker external · runner verifier 결함(보정 완료)
- 변경·정정 = MSG_203/205 CLEANUP_FAILED→TWO_RUN_GREEN(verifier 보정) · 카탈로그 57→62
- 다음 확인 = batch commit 승인 · LCH 간편모드 재설계 · MSG_210 타빌드 비교
