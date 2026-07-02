# RESULT_RECOVERY — ALT Basic batch10 C11 v1 subset F0 run1 discovery (2026-07-01)

- 단말: **F0 `B06201249E0002F0`** (AT-M140 THOR2, RY07260601S, ko-KR). B27 `B2700125BW000083`/ODIN2 **미접촉**(UDID 고정 가드).
- 실행: thor2j-tc-appium `runner/altbasic_c11_driver.py` (Appium 3.4.0 + uiautomator2 7.2.1, system python). driver 코드 수정 0.
- scope: **C11 v1 subset 12** (SST 5 + PDM 5 + MGN 2). manifest chunk C11=21 중 driver 미구현 9(PFW×6·MGN_005/006·SST_016) 제외 — reconcile 결과 명시 하향(§handoff C11=21 ≠ 구현 12).
- mutation: 전건 NAVIGATION_ONLY/READ_ONLY. 위험 컨트롤 0 접촉. **helper cleanup 완료(2026-07-01 checkpoint)**: run1 후 io.appium 헬퍼 3종(uiautomator2.server·.server.test·settings) 잔존 발견 → uninstall 3× Success → `pm list packages | grep io.appium` = **잔존 0 (CLEAN)** 확인 + Appium host 서버(4723) 정지. §7 "잔존 0" 불변식 회복.

## ★ v2 재설계 회수 (2026-07-01 후속) — PDM_041~044 RUNNABLE_NOW +4

아래 v1 discovery(run1 = 0 RUNNABLE)의 nav 카탈로그를 근거로 PDM_041~044 **gear-nav 재설계 + literal backfill** 후 fresh 2-run 수행. **4/4 TWO_RUN_GREEN**.

| tc_id | literal | run1 | run2 | 판정 |
|---|---|---|---|---|
| PDM_041 | 키 | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| PDM_042 | 몸무게 | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| PDM_043 | 성별 | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| PDM_044 | 목표 걸음 수 | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |

**재설계 (thor2j §2.5 승인)**: `runner/altbasic_c11.py` — v1 down-chain(`PDM_CHAIN`/`pdm_down_count`) 폐기 → `APP_GEAR_NAV`(만보기 + personal-info literal 일 때만, 그 외 no-guess FAIL_CLOSED) + `PDM_PERSONAL_INFO`·`normalize_pdm_literal`·`_literals`. `runner/altbasic_c11_driver.py` `_run_app` — 만보기 메인 우상단 gear(`id/imageView`, clickable, center 441,77) tap → **PersonalInformationActivity 도달 게이트**(activity명 / 내정보·신체정보 marker, 미도달=ENTRY_FAILED) → literal 대조. host-TDD **19/19 GREEN**.

**literal backfill (tc-runner §2.1 승인)**: `stage1_review_mapping_batch10/ALTBASIC_PDM_044_canonical.yaml` verify_text target `목표 걸음수 → 목표 걸음 수`(run1 실측), `expected_result_raw`·title 은 소스 verbatim 보존. manifest 재생성 → diff = PDM_044 `verifier_candidates` 셀만(faithfulness 사전검증: 무편집 재생성 == committed byte-identical).

- 실행: Appium 3.4.0(base-path /, MSYS_NO_PATHCONV=1 로 Git Bash `/` mangle 회피) + thor2j_appium venv. **helper 3종 설치→uninstall Success · 잔존 0 · pre 219 == post 219 (mutation 0)**. F0 sole-device(B27 미접촉).
- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_c11_v2_20260701/{run1,run2}/{tc_id}/` + `results_run{1,2}.csv`.
- **RUNNABLE_NOW +4** (PDM_041~044). 잔여 C11: SST_008/013/014/015 · MGN_001/PDM_040(verifier-model) · SST_012(re-scope) · MGN_002(fail-closed) · gap-9 = 후속 slice.
- **2026-07-01 무단말 스테이징 (device HELD, F0 sole 불가)**: SST_008/013/014(scroll+tap·OK-retire) + MGN_001(element-verifier `id/scale_bar`) host-TDD **23/23 GREEN** + MGN tc-runner backfill(canonical element_presence/generator/manifest, diff=MGN_001 행만). PDM_040(back 요소 0)·SST_015(안심기능 부재)·SST_012(WiFi) = spec-device 불일치 **defer**. device 2-run 즉시실행 절차 = **`RUNSHEET_C11_SST_MGN_2026-07-01.md`** (잠재 +4 RUNNABLE). ★SST verify literal은 목적지 title device 미확인 → PENDING 시 backfill.

## ★ v2 회수 2차 (2026-07-02) — SST_008/013/014 + MGN_001 RUNNABLE_NOW +4 (C11 누적 8)

F0 sole 창 확보 → `RUNSHEET_C11_SST_MGN_2026-07-01.md` 절차대로 실행. pre-flight(F0 단독·helper 0·pre 스냅샷 219) + host-TDD 23/23 재확인 + dry-run disposition 4건 일치 후 fresh 2-run.

| tc_id | verifier | run1 | run2 | 판정 |
|---|---|---|---|---|
| SST_008 | literal `소리 및 진동` | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| SST_013 | literal `배경화면 및 스타일`(backfill) | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| SST_014 | literal `디스플레이` | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |
| MGN_001 | element `com.hnlens.magnifying:id/scale_bar` | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |

**초회 run1 ENTRY_FAILED 3건(SST) 원인 = 단말 stale task 상태 (driver 결함 아님·환경 오염)**: 간편모드 홈 `설정` 타일은 기존 `com.android.settings` task(t156)를 **상태 그대로 resume** — 이전 세션 잔존 스택(`GoogleSettingsActivity`→`.Settings`(하단 스크롤)→`SubSettings` 다층) 위에 도달해 scroll+tap 미발견. manual evidence observed: `dumpsys activity` topResumed + run1 dump(`02_settings.xml`=`com.google.android.gms`). BACK-루프로 task 완전 종료 후 재launch = fresh task root 정상 도달 → 재run 전건 PASS. **개선 규칙: driver launch 후 "설정 root 도달 게이트"(activity=.Settings ∧ `설정 검색` 존재, 미충족 시 BACK-루프 self-heal) 필요 — 차기 driver slice.**

**SST_013 literal backfill (본 세션 1사이클, 사전 승인 범위 내)**: 소스 oracle `테마 및 배경화면`(paraphrase) vs 실측 목적지 title `배경화면 및 스타일`(하위: 배경화면 변경/잠금 화면/홈 화면). canonical `expected[].target`+`expected_texts_candidate`만 변경, `expected_result_raw`·title verbatim 보존. manifest 재생성(faithfulness 사전검증: 무편집 재생성 byte-identical → 편집 후 diff=SST_013 `verifier_candidates` 셀만). 백필 후 fresh run1+run2. **분류 note**: driver는 이를 `VERIFIER_FAILED`(LIT_ABSENT)로 보고 — 목적지 도달+화면 로드 상태의 title 상이는 `LITERAL_PENDING` 취급이 의도(runsheet caveat)와 정합. LIT_ABSENT/LIT_PENDING 경계 재정의 = 차기 driver slice.

- 실행: Appium 3.4.0(MSYS_NO_PATHCONV=1) + thor2j_appium venv. **helper 3종 설치→uninstall Success·잔존 0·pre 219 == post 219 (mutation 0)**. Appium 정지(4723 free). F0 sole 유지(B27 미접촉).
- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_c11_v2_20260701/{run1,run2}/{tc_id}/` + `results_run{1,2}.csv` (2026-07-02 행 append).

## ★ v3 driver slice (2026-07-02 후속) — R1/R2 구현 + SST_015 회수 (C11 누적 9)

PROCESS_REVIEW R1·R2를 host-TDD(RED→GREEN)로 driver에 반영 + SST_015 백필·fresh 2-run + PDM_040 결정.

**R1 (launch root 게이트+self-heal, ⑤유형 차단)**: `altbasic_c11.sst_root_gate`(activity `.Settings` suffix ∧ `설정 검색` marker — sst_root_top.xml 실측) + driver `_sst_launch_root`(미충족 시 `_sst_back_heal` BACK-루프 max 8 → HOME → 재launch 1회 재시도, 재실패 = ENTRY_FAILED 사유 명시 + `root_gate_stale` 증거 dump). HOME 단독은 task 미종료(resume 동일 stale)라 BACK 종료 필수.

**R2 (PENDING/ABSENT 경계 재정의)**: `altbasic_c11.literal_outcome` — 도달+로드 ∧ 전 literal = PASS / 도달+로드 ∧ 부재·일부 = `LITERAL_PENDING`(백필 트리거) / 미도달·미로드 = `VERIFIER_FAILED`. SST 도달판정 = `sst_dest_loaded`(dump 존재 ∧ root marker 이탈), APP gear 경로 = 기존 PersonalInfo 도달 게이트. **부수 수정: root 잔존 상태에서 literal 우연 일치 시 PASS 승격되던 잠재 false-PASS 차단**(host-TDD로 기존 결함 재현 후 수정). SST_013 유형(도달+로드 title 상이)은 이제 `LITERAL_PENDING`으로 정분류.

**SST_015 백필+회수**: canonical `expected[].target`+`expected_texts_candidate` `안심기능→안심 기능`(discovery sst015_ansim_dest.xml 실측, `expected_result_raw` 소스 보존) + manifest 재생성(faithfulness 사전검증: 무편집 재생성 byte-identical → 편집 후 diff = SST_015 `verifier_candidates` 셀만) + nav label은 driver 정규화(`SST_NAV_BACKFILL` 안심기능→안심 기능, sst_root_p1.xml 실측). fresh 2-run:

| tc_id | verifier | run1 | run2 | 판정 |
|---|---|---|---|---|
| SST_015 | literal `안심 기능`(backfill) | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |

두 run 모두 R1 게이트 1차 통과(`root_gate_stale` 미발생 = fresh task 상태) — self-heal 경로는 host-TDD fake로 검증.

**PDM_040 결정 = spec-gap 확정**: cold-launch 전체 dump(pdm040_main.xml) 실측 — `뒤로/back` 요소 0건 ∧ `focused="true"` 0건. oracle "최초 focus가 뒤로가기 버튼"의 두 술어(요소 존재·초기 focus) 모두 단말 대응물 부재 → PDM_041~044과 달리 보존할 의도 잔여 없음(타 요소로의 element_verifier 전환 = 발명) → **re-scope 기각, spec-gap**. driver `C11_SPEC_GAP` registry로 분류 시 `SPEC_GAP` 기록·단말 미접촉. ledger primary `re_scope→spec_gap` 갱신.

- host-TDD: `tests/test_altbasic_c11.py` **36/36 GREEN** (신규 14: R1 게이트 5·R2 경계 4·SST_015 2·PDM_040 1·driver wiring fake 5 — RED 확인 후 구현). thor2j 전체 host suite에서 C11 외 실패는 본 변경 무관(altbasic_c11 참조 테스트 = test_altbasic_c11.py 유일).
- 실행: Appium 3.4.0(MSYS_NO_PATHCONV=1) + thor2j_appium venv. **helper 3종 uninstall Success·잔존 0·pre 219 == post 219 (mutation 0)**. Appium 정지(4723 free). F0 sole(단독 연결 확인).
- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_c11_v2_20260701/{run1,run2}/ALTBASIC_SST_015/` + `results_run{1,2}.csv` append.

### v3 후속 — SST_012 Quick Panel re-scope 회수 (2026-07-02, C11 누적 10)

**위임 실행 모드**: 구현·단말 실행을 sonnet 서브에이전트 runbook 위임으로 수행(설계 잠금·grounded 값 사전 확정·결과 직접 재검증은 오케스트레이터). host-TDD RED 7(전건 의도 사유)→GREEN **41/41**.

**re-scope (ledger decision=re_scope·literal_backfill)**: 소스 oracle(설정 내 WiFi tap→네트워크 및 인터넷/WiFi)의 F0 대응물 부재 확정 → 검증모델 = **Quick Panel(com.android.systemui) 열기 → Wi-Fi 타일 literal 노출 확인**(읽기 전용·토글 tap 0회). verifier literal 백필 `네트워크 및 인터넷 / WiFi → Wi-Fi`(실측 sst012_quickpanel_1.xml; 상태의존 `Wi-Fi, 켜짐` 제외 — 비단정 규칙). canonical `expected_result_raw` 보존, manifest faithfulness(무편집 byte-identical → diff=SST_012 verifier 셀만). driver = `SST_QUICKPANEL` disposition(`C11_QUICKPANEL_RESCOPE` registry) + `_run_sst_quickpanel`(`open_notifications()` 우선·좌표 swipe fallback·R2 `quickpanel_loaded` 게이트).

| tc_id | verifier | run1 | run2 | 판정 |
|---|---|---|---|---|
| SST_012 | literal `Wi-Fi`(backfill·Quick Panel) | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |

- pre-flight F0 sole·helper 0·pre 219 → run1/run2 → **helper 3종 uninstall Success·잔존 0·pre==post 219(mutation 0)**·4723 free. run dump 검증: `02_quickpanel.xml` systemui 133 노드·`text="Wi-Fi"` 존재.
- evidence: `thor2j-tc-appium/evidence/altbasic_batch10_c11_v2_20260701/{run1,run2}/ALTBASIC_SST_012/` + `results_run{1,2}.csv` append.
- **C11 잔여**: MGN_002(fail-closed 유지) · gap-9(authoring 큐). PDM_040 = spec-gap 종결. SST 5/5 전건 회수 완료.

### v3 후속 2 — gap-9 discovery + SST_016 회수 (2026-07-02, C11 누적 11)

**gap-9 discovery (non-mutating adb-only, sonnet 위임·21 dump → `catalog/f0_c11_nav_2026-07-01/discovery_gap9_2026-07-02/`)**: ①SST_016 — 목적지 title `안전 및 긴급 상황`(collapsing_toolbar desc)·영문 `Emergency` 0건 = divergence 확정, ⑤유형 stale resume 1회 재관찰(BACK 복구, R1 근거 3호) ②MGN_005/006 — `id/flash_light`·`id/scale_bar`(SeekBar)·`id/shutter_button` 실존·썸네일 노드 미발견(빈 갤러리 추정)·dpad DOWN 후 scale_bar focus 고착(keyevent 3회 한정 — 판정 보류) ③PFW — 진입 표면 = 홈 4페이지 중 p3 사진 액자 위젯 페이지(`simplemode:id/frame_bg`·`cl_vp2`) 확정·모든 앱 35 전면 채록 관련 앱 부재·현재 빈 앨범(`사진 추가하기`). **MGN_006·PFW 6 공통 게이트 = 사진 세팅 precondition(mutating·별도 승인)**. 금지 행위 위반 0·단말 HOME 복귀.

**SST_016 백필+회수 (ledger decision=literal_backfill)**: canonical `Emergency→안전 및 긴급 상황`(`expected_result_raw` 소스 보존)+manifest faithfulness(diff=SST_016 verifier 셀만)+driver `C11_V1` 편입(기존 SST_TAPNAV 경로 재사용·신규 로직 0). host-TDD **43/43 GREEN**(RED=C11_V1 포함 검사 1건 — 분류·nav는 기존 로직이 즉시 커버).

| tc_id | verifier | run1 | run2 | 판정 |
|---|---|---|---|---|
| SST_016 | literal `안전 및 긴급 상황`(backfill) | SINGLE_RUN_PASS | RUN2_PASS | **TWO_RUN_GREEN** |

- 양 run R1 게이트 1차 통과(`root_gate_stale` 미발동). helper 3종 uninstall Success·잔존 0·pre 219==post 219(mutation 0)·4723 free. after dump: title 1건·`설정 검색` 0건(R2 정합).
- evidence: `{run1,run2}/ALTBASIC_SST_016/` + `results_run{1,2}.csv` append.
- **C11 최종 잔여**: MGN_005/006·PFW 6(사진 세팅 게이트 공통) · MGN_002(fail-closed) · PDM_040(spec-gap). 결과 분포 = TWO_RUN_GREEN **11** / NOTE 2 / NOT_STARTED 8.

**동일 창 A-확장 discovery (non-mutating: dump/back/home + navigation tap만, toggle 0)** → `catalog/f0_c11_nav_2026-07-01/discovery_2026-07-02/` 10 dump:
- **SST_015 정정**: 설정 root top-level에 **`안심 기능` 존재** (nav 카탈로그 "안심기능 부재"는 오판 — stale 스크롤/부분 캡처 추정). `안전 및 긴급 상황`은 **별개 항목**(긴급 SOS/의료 정보)으로 공존 = 기존 후보 매핑은 오매핑. `안심 기능` 진입 = `com.hnlens.safetyfeature/.ui.MainActivity`, title literal `안심 기능`, 항목 SOS 버튼/보호자 등록/안심 메시지/수신 차단 → **backfill 근거 확보, 무단말 재설계 가능**.
- **SST_012**: Quick Panel(swipe, com.android.systemui)에 Wi-Fi 타일 실존(text `Wi-Fi`/`Wi-Fi, 켜짐`) — re-scope 경로 grounded. tap 0회(토글 변이 방지).
- **PDM_040**: 만보기 cold launch 실측 = **focused 요소 0·back 요소 0**, gear(`id/imageView`) clickable/focusable·focused=false·bounds[408,44][474,110]. "최초 focus 뒤로가기 버튼" spec은 단말 실물과 불일치 확정 → ①gear/element verifier re-scope ②spec-gap 판정 중 결정 필요.
- **설정 root 전체 리스트 채록**(p1~p4): 네트워크및인터넷/연결된기기/앱/안심 기능/해외 로밍 → 소리및진동/디스플레이/배경화면및스타일/배터리/저장용량 → 안전및긴급상황/위치/개인정보보호/비밀번호및계정/디지털웰빙 → Google/시스템/휴대전화 정보/DuraSpeed.

---

## run1 결과 — TWO_RUN_GREEN 0 / RUNNABLE_NOW 0 (v1 discovery, 아래는 재설계 근거 기록)

run1 = discovery 회차(TWO_RUN 미카운트). 결과: **device-touch 11 전건 VERIFIER_FAILED/ENTRY_FAILED**, fail-closed 1.

| tc_id | result | 실측 |
|---|---|---|
| MGN_001 | VERIFIER_FAILED | expected `줌 슬라이더 핸들`(요소) / actual `0.0`·`손전등` |
| MGN_002 | UNSUPPORTED_ENTRY_DETAIL | hardkey 미상 → 단말 미접촉(설계대로) |
| PDM_040 | VERIFIER_FAILED | expected `뒤로가기 버튼`(요소) / 만보기 메인 |
| PDM_041~044 | VERIFIER_FAILED | expected `키/몸무게/성별/목표 걸음수` = 설정 하위(메인 아님) |
| SST_008 | VERIFIER_FAILED | OK키→`기본 정보`(About) 이탈 |
| SST_012~015 | ENTRY_FAILED | `WiFi/배경화면 및 스타일/디스플레이/안심기능` 직접 tap 미발견 |

## 진단 = v1 oracle divergence (파이프라인 정상)

세션·앱 진입·dump·evidence·결과 CSV 전부 동작(smoke SST_012 E2E 검증). 0 RUNNABLE 원인 = **v1 oracle(verifier literal=source paraphrase + navigation candidate)가 F0 실 UI와 divergent**. run1이 설계 목적(literal run1-verify·keycode run1-verify)대로 divergence를 노출.

3-cluster: ① verifier=요소 묘사(텍스트 아님, MGN_001·PDM_040) ② navigation 모델 오류(PDM down-chain·SST OK-key·SST 무스크롤 직접 tap) ③ fail-closed(MGN_002, 설계).

## grounded 재설계 근거 = nav 카탈로그

device-assisted discovery로 실 navigation·verifier 채록 → **`catalog/f0_c11_nav_2026-07-01/F0_C11_NAV_CATALOG.md`**.
핵심: SST=표준 scrollable 설정(소리및진동/디스플레이/배경화면 top-level 존재, WiFi 부재) · PDM=**gear(id/imageView)→PersonalInformationActivity** · MGN=verifier by `id/scale_bar`.

**재설계 후 잠재**: RUNNABLE ~8(SST_008/013/014/015 + PDM_041~044) + verifier-model 변경 2(PDM_040·MGN_001) + re-scope 1(SST_012 WiFi) + fail-closed 1(MGN_002).

## evidence

- run1: `thor2j-tc-appium/evidence/altbasic_batch10_c11_20260630/run1/{tc_id}/` (xml+png) + `results_run1.csv`.
- discovery: `catalog/f0_c11_nav_2026-07-01/{sst,pdm,mgn}/*.xml` + nav 카탈로그.

## Path A discovery 종결 상태

**Path A discovery complete.** 본 결과 = **grounded redesign input, RUNNABLE promotion 아님**. RUNNABLE_NOW 전환은 literal backfill + driver 재설계 + fresh 2-run **이후에만**. helper 잔존 0 확인(위 mutation 라인). checkpoint 종료 — oracle 재설계는 무단말 세션에서 안정화 후 다음 F0 창에서 회수.

## 다음 세션 지시문 (무단말 우선 → 단말 재run)

```text
C11 Path A discovery는 완료. 이 결과는 RUNNABLE promotion이 아니라 grounded redesign input이다.

STEP0:
- ★ Path A 산출물 존재 확인 먼저 (전부 untracked local — git 복구 불가, 부재 시 STOP = 재설계 근거 유실·device re-discovery 필요):
    - THOR2 - ALT Basic TC Audit/catalog/f0_c11_nav_2026-07-01/  (F0_C11_NAV_CATALOG.md + sst/pdm/mgn/*.xml dump)
    - THOR2 - ALT Basic TC Audit/RESULT_RECOVERY_BATCH10_C11_2026-07-01.md
    - thor2j evidence/altbasic_batch10_c11_20260630/run1/  (gitignored local, run1 xml+png)
- 존재 확인 후 위 산출물 읽기 (nav catalog + 본 리포트)
- F0/helper clean 여부 확인 (본 세션 잔존 0 확인 완료)
- tc-runner/thor2j git status 확인

우선순위:
1. PDM_041~044 재설계부터
   - gear(id/imageView center 441,77) -> PersonalInformationActivity 진입
   - PDM_044 literal spacing backfill (목표 걸음수 -> 목표 걸음 수)
   - host-TDD 먼저
   - device run은 별도 승인 후 fresh 2-run
2. SST 다음
   - SST_008/013/014/015 = catalog 기반 tap / scroll+tap / backfill
   - SST_012 WiFi = Quick Panel 추정이라 re-scope 별도
3. MGN/PDM verifier-model
   - PDM_040 element verifier / MGN_001 resource-id verifier(id/scale_bar) / MGN_002 hardkey fail-closed 유지

금지:
- Path A 결과를 RUNNABLE_NOW로 주장하지 말 것
- host-TDD 없이 device rerun 금지
- helper 잔존 상태로 세션 종료 금지
- commit/push는 별도 승인
```

- gap-9(PFW×6·MGN_005/006·SST_016) = 별도 authoring 큐(불변).

## commit/push
- (2026-07-02 현행화) v2 1차 회수분은 커밋 완료: tc-runner `f124db2`(PDM_044+manifest+본 리포트)·`f682bcf`(MGN_001+runsheet) — **origin push 완료(`0008555..f682bcf` ff)**. thor2j `7415d5f`·`cd9e057`(driver+tests, remote 없음 → bundle 백업 `C:\Users\momen\Backups\thor2j-tc-appium\thor2j_2026-07-02.bundle`).
- 2차 회수(2026-07-02)분 미커밋: `ALTBASIC_SST_013_canonical.yaml`(M) · `VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`(M) · 본 리포트 v2-2차 섹션(M) · `catalog/f0_c11_nav_2026-07-01/`+`discovery_2026-07-02/`(untracked) · PROCESS_REVIEW·LEDGER(untracked 신규). 명시 승인 전 commit 금지(§7) — 당일 말 배치커밋 스코핑에 합류.
