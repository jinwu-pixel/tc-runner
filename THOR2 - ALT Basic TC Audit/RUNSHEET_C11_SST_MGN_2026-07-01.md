# RUNSHEET — C11 SST/MGN device 2-run (다음 F0-sole 창 즉시 실행용)

**작성 2026-07-01 (무단말 스테이징).** host-TDD 전부 GREEN, device 2-run만 HELD (F0 sole 불가 = 타 단말 blank-screen 스크립트 점유). F0 단독 확보되는 즉시 아래대로 실행 → TWO_RUN_GREEN이면 **잠재 +4 RUNNABLE** (SST_008/013/014 + MGN_001).

- 단말: **F0 `B06201249E0002F0`** (AT-M140, RY07260601S, ko-KR 480×800). B27/ODIN2 미접촉.
- driver: thor2j `runner/altbasic_c11_driver.py` (host-TDD 23/23 GREEN, uncommitted — SST+MGN v2).
- venv: driver=`C:\Users\momen\venvs\thor2j_appium\Scripts\python.exe` / pytest=`tc-runner\venv\Scripts\python.exe`.

## 대상 (device-touch 4, 전부 host-TDD staged)

| tc_id | v2 동작 | verify | caveat |
|---|---|---|---|
| SST_008 | 홈 설정 tap → scroll+tap `소리 및 진동`(OK-key 폐기) | literal `소리 및 진동` | 목적지 title 미확인 → PENDING 시 backfill |
| SST_013 | 홈 설정 tap → scroll+tap `배경화면 및 스타일` | literal `테마 및 배경화면` | 〃 |
| SST_014 | 홈 설정 tap → scroll+tap `디스플레이` | literal `디스플레이` | 〃 |
| MGN_001 | launch 돋보기(OK 폐기) → element present | element `com.hnlens.magnifying:id/scale_bar` | grounded (mgn.xml 실측) |

**★SST literal caveat**: 목적지 화면 title(`테마 및 배경화면`/`디스플레이`/`소리 및 진동`)은 nav 카탈로그가 **root 메뉴 존재만** 확인했고 **목적지 title은 device 미확인**. run에서 `LITERAL_PENDING` 나오면 = 실 title 상이 → run1 dump에서 실측 title 채록 → PDM_044 방식 backfill(canonical `expected[].target` + manifest 재생성, `expected_result_raw` 소스 보존) 후 fresh 2-run 재실행. **no-guess: 임의 title 금지.**

## 실행 절차

### 0. pre-flight (read-only)
```bash
adb devices                 # F0 단독? (B27/타단말 있으면 STOP — sole-device bus-guard abort)
adb -s B06201249E0002F0 shell pm list packages | grep -i io.appium   # 잔존 0 기대
adb -s B06201249E0002F0 shell pm list packages | sort > c:/tmp/F0_pkgs_pre.txt   # pre-snapshot (219 기대)
```

### 1. host-TDD 재확인 (device 전제)
```bash
cd thor2j-tc-appium
tc-runner\venv\Scripts\python.exe -m pytest tests/test_altbasic_c11.py -q     # 23 passed
thor2j_appium\Scripts\python.exe runner/altbasic_c11_driver.py --dry-run | grep -E "SST_008|SST_013|SST_014|MGN_001"
# 기대: SST_008 SST_KEY / SST_013·014 SST_TAPNAV / MGN_001 APP_LAUNCH_KEY(element)
```

### 2. Appium 기동 (★MSYS_NO_PATHCONV=1 필수)
```bash
# Git Bash가 '--base-path /' 를 'C:/Program Files/Git/' 로 mangle → 반드시 MSYS_NO_PATHCONV=1
MSYS_NO_PATHCONV=1 "C:/Users/momen/AppData/Roaming/npm/appium.cmd" --port 4723 --base-path / --log-timestamp &
curl -s http://127.0.0.1:4723/status    # {"ready":true} 확인
```

### 3. fresh 2-run (v2 EV_REL=altbasic_batch10_c11_v2_20260701 — PDM run과 같은 dir, tc_id 분리라 무충돌)
```bash
ONLY=ALTBASIC_SST_008,ALTBASIC_SST_013,ALTBASIC_SST_014,ALTBASIC_MGN_001
thor2j_appium\Scripts\python.exe runner/altbasic_c11_driver.py --run 1 --only $ONLY
thor2j_appium\Scripts\python.exe runner/altbasic_c11_driver.py --run 2 --only $ONLY
# 판정: run1 SINGLE_RUN_PASS + run2 RUN2_PASS → TWO_RUN_GREEN
```

### 4. helper cleanup + mutation 검증
```bash
for p in io.appium.uiautomator2.server io.appium.uiautomator2.server.test io.appium.settings; do adb -s B06201249E0002F0 uninstall $p; done
adb -s B06201249E0002F0 shell pm list packages | grep -i io.appium   # 잔존 0
adb -s B06201249E0002F0 shell pm list packages | sort > c:/tmp/F0_pkgs_post.txt
diff c:/tmp/F0_pkgs_pre.txt c:/tmp/F0_pkgs_post.txt                   # empty = mutation 0
# appium 정지: netstat -ano | grep :4723 → taskkill //PID <pid> //F
```

### 5. 회수 + commit (별도 승인)
- TWO_RUN_GREEN만 RUNNABLE_NOW 후보로 RESULT_RECOVERY_BATCH10_C11 갱신.
- commit 시 **명시 path만** (§7): thor2j `runner/altbasic_c11.py`·`runner/altbasic_c11_driver.py`·`tests/test_altbasic_c11.py` (★동시 writer의 `docs/lessons_learned.md`·`docs/recovery_honesty.md` 절대 미포함) + tc-runner `ALTBASIC_MGN_001_canonical.yaml`·`VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`.
- **§2.3 note**: `scratch/gen_batch10_manifest.py` element 분기 추가는 local-only 관례 — MGN manifest artifact가 이 편집에 의존하므로 커밋 시 generator 동봉 여부 판단(미동봉 시 재생성으로 MGN 행 revert 위험을 커밋 메시지에 명시).

## defer (device discovery 선행 필요, 이번 run 제외)
- **PDM_040**: 만보기 메인 back 요소 0·focused=gear → "최초 focus 뒤로가기 버튼" spec-device 불일치. re-scope(gear focus?) 또는 spec-gap 결정 필요.
- **SST_015**: top-level `안심기능` 부재 → `안전 및 긴급 상황` 후보 매핑 + verify literal 미확정. run1 discovery로 목적지 화면 채록 후 backfill.
- **SST_012**: WiFi = 설정 타일 경로 밖(Quick Panel 추정) re-scope.
- **gap-9**: PFW×6·MGN_005/006·SST_016 = 별도 authoring 큐(source paraphrase → device discovery 선행).

## 현재 미커밋 (staged, device 전)
- thor2j 3 M: altbasic_c11.py·altbasic_c11_driver.py·test_altbasic_c11.py (SST+MGN host-TDD).
- tc-runner 2 M: ALTBASIC_MGN_001_canonical.yaml·VALIDATION_MANIFEST_BATCH10 (MGN element backfill).
- (PDM_041~044 v2는 이미 커밋: tc-runner `f124db2` / thor2j `7415d5f`, device 4/4 TWO_RUN_GREEN.)
