# RESULT RECOVERY — ALT Basic batch11 F0 검증 사이클 1 (2026-06-17)

단말 F0 `B06201249E0002F0` (AT-M140 THOR2, build **RY07260601S**, ko-KR). ODIN2 `c4324122` 미접촉.
러너 = `thor2j-tc-appium/runner/altbasic_validation_batch11.py` (b1.Dev/run_one + focus_snapshot R1 재사용).
evidence = `thor2j-tc-appium/evidence/altbasic_batch11_20260617/` (local-only).

## 결과 — RUNNABLE_NOW = 12 / 64

| 클러스터 | tc | 결과 |
|---|---|---|
| BSC_038~045 (8) | Navi Up/Down/Left/Right × short/long, 홈 focus_move | ✅ TWO_RUN_GREEN |
| HDK_043/044/045/047 (4) | 홈/2nd-홈 focus_move (R1 NAVIGATION_ONLY) | ✅ TWO_RUN_GREEN |

- 게이트: run1 SINGLE_RUN_PASS ∧ run2 RUN2_PASS. 조인 12/12 GREEN.
- 검증 모델: R1 `has_focus_moved_from_baseline` — focused 노드(any axis) 변경. selector 사전확정 불필요.
- 런처 = `com.hnlens.simplemode`. 캡처 selector(`rl_home_app`·`rv_main_apps`·`weather_view`·`dial_view`·`tv_edit`·`rl_first`·`t_all_apps`) → STAGE1 yaml `device_value` 환류 완료(12건, PENDING_F0 해소).
- HDK_044 = 2nd-home swipe 직후 focus 부재 → seat 키 1회 보정 후 GREEN.

## NOT_GREEN / deferred

| tc | 사유 |
|---|---|
| MSG_069~077 (5) | **list-focus 한계** — 차단·스팸/설정 화면은 `android:id/list` 컨테이너 자체가 focused, DPAD가 focused *노드* 미변경(선택은 `selected` 속성). **R1 focus_move로 판정 불가** → `selected="true"`/스크롤 델타 기반 verifier 재설계 필요. + nav flaky(더보기→차단·스팸 tap) |

**§8.2 후보(발견)**: list/설정 화면 focus 검증은 R1 focus-moved(노드 변경) 모델로 위양성/위음성 → **list-aware verifier**(selected 속성 또는 scroll delta) 별도 필요. 잔여 focus_state 중 list 화면류 다수에 영향.

## 안전 / mutation-0

- 전건 NAVIGATION_ONLY (DPAD 이동 + HOME). 선택/ENTER/실행/설정변경 0.
- helper `io.appium.uiautomator2.server(.test)`·`io.appium.settings` **uninstall 완료** — F0 io.appium 패키지 잔존 0.
- (사전 pkg 베이스라인 미채록 — 다음 사이클부터 pre/post snapshot 권장. 본 사이클은 코드상 install/save/send/call 동작 0 + helper 제거로 mutation 0.)

## 잔여 batch11 = 52 (다음 사이클)

| 묶음 | n | 선결 |
|---|---|---|
| MSG list-focus | 5 | **list-aware verifier 설계** |
| QPN 169/170 · HDK_069 | 3 | 퀵패널 편집 진입 / 연락처 더보기 탐색 |
| WARN35 focus_state 기타 | 14 | invariant/boundary_stop/retained/created/position/absent — 일부 list 화면이면 위 설계 의존 |
| batch11 29 | 29 | element_presence / popup_cancel(취소·back denylist) / transient_input(가역·발신·저장 금지) |

## 다음 진입 순서 (권장)

1. **list-aware focus verifier** 설계 (`selected="true"` 노드 + scroll position) → MSG 5 + list형 focus_state 재시도.
2. QPN 2 + HDK_069 (퀵패널 편집/연락처 더보기 — run1 dump로 진입 경로 채록).
3. WARN35 focus_state 기타 14 (assert별 R1 변형: invariant=`is_baseline_equivalent`, boundary_stop, retained 등).
4. batch11 29 — 안전 denylist enforce 핸들러 (popup_cancel/transient_input 마지막).

commit/push = 별도 명시 승인 (백필된 12 yaml + 본 RESULT + 러너).
