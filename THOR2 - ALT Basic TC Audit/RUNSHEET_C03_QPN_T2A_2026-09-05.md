# RUNSHEET — C03/C04 Quick panel T2-A F0 2-run

**작성일**: 2026-09-05
**상태**: host-only 실행 문서. 이 파일은 device 실행 승인이 아니다.
**실행 repo**: `C:\Users\momen\Projects\thor2j-tc-appium`
**driver 기준 OID**: `30beec0f15403ce325534137d9f054403df145d4`

## 1. 범위와 권위

- 권위 설계: `docs/superpowers/specs/2026-08-20-altbasic-c03-qpn-driver-design.md` §7.1~§7.2.
- 대상: drivable 34건을 run1/run2에서 각각 한 번 실행한다.
- 각 run은 `d1` 3건을 먼저 실행하고, GREEN일 때만 `rest41`로 진행한다.
- `rest41`은 drivable 31건과 registry 10건이다. registry 행은 `results.csv`를 44행으로 닫기 위한 분류이며 device 입력은 0회다.
- **QPN_145는 registry다.** 현 driver는 QPN_145 목적지로 이동하지 않는다. 따라서 이 T2-A에서 `altbasic_c03_idle_probe.py`를 실행하거나 145 판정을 주장하지 않는다. 145 관찰은 별도 T2-B 설계·승인 대상이다.
- run1 결과를 근거로 run2 절차·selector·budget을 변경하지 않는다.

## 2. 승인 경계

아래는 각각 별도 사용자 승인이 필요하다.

1. F0 identity를 읽는 ADB read-only 확인
2. T2-A device 2-run
3. 예상 밖 상태의 복구 mutation
4. commit과 push

승인 전에는 `--run 1`, `--run 2`, 직접 ADB 입력을 실행하지 않는다. D2 타일 추가, D2-a short-OK, 102 비-scalar guard, 145 Appium 채널은 이 runsheet의 비목표다.

## 3. T0 — host와 sole-writer 게이트

`C:\Users\momen\Projects\thor2j-tc-appium`에서 실행한다.

```powershell
git rev-parse HEAD
git branch --show-current
git status --short
```

수용 조건:

- HEAD가 `30beec0f15403ce325534137d9f054403df145d4`와 일치한다.
- branch는 `master`다.
- 다음 선존 tracked M 6개는 실행 전후 byte-identical이어야 하며 읽기 외 접촉하지 않는다.
  - `docs/annotation_candidate_dossier_2026-07-06.md`
  - `docs/recovery_honesty.md`
  - `testcases/focusrule/focusrule_tc_catalog.yaml`
  - `testcases/focusrule/tc_profiles_index.yaml`
  - `tests/test_recovery_feasibility_audit.py`
  - `tests/test_tc_quality_audit.py`
- thor2j device writer가 해제됐음을 사용자가 명시한다.
- evidence 대상 `evidence/altbasic_batch10_c03_v1_20260820/run1`과 `run2`가 없거나 비어 있다. 기존 파일이 있으면 삭제·덮어쓰기하지 않고 STOP한다.

host 재자격:

```powershell
python -m pytest tests/test_altbasic_c01_driver.py tests/test_altbasic_c02.py tests/test_altbasic_c03.py tests/test_altbasic_c03_idle_probe.py tests/test_altbasic_c11.py tests/test_altbasic_narrow.py
python runner/altbasic_c03_driver.py --dry-run
```

수용 조건은 `238 passed`, exit 0과 `drivable=34 registry=10`이다. 불일치하면 device gate로 넘어가지 않는다.

## 4. T1 — device identity read-only 게이트

이 절은 사용자가 ADB read-only 확인을 승인한 뒤에만 실행한다. C03 대상은 F0 `B06201249E0002F0` 단독이다. ODIN2와 B27/THOR2_J를 포함한 다른 단말이 한 대라도 함께 보이면 STOP한다.

```powershell
adb devices -l
adb -s B06201249E0002F0 shell getprop ro.product.model
adb -s B06201249E0002F0 shell getprop ro.build.version.incremental
adb -s B06201249E0002F0 shell getprop persist.sys.locale
adb -s B06201249E0002F0 shell pm list packages io.appium
```

기준값:

- serial: `B06201249E0002F0`
- model: `AT-M140`
- incremental: `RY07260601S`
- locale: `ko-KR`
- `io.appium` package: 출력 없음

incremental을 포함해 하나라도 다르면 입력 0회로 STOP하고 실측값만 보고한다. 사용자가 재베이스라인 또는 보류를 결정하기 전에는 기존 기준을 자동 완화하지 않는다. USB 재연결 시 이 절 전체를 다시 실행한다.

## 5. T2 — pre-snapshot

device 2-run 승인을 받은 뒤, 첫 입력 전에 아래를 읽어 별도 evidence에 보존한다. 기존 파일을 덮어쓰지 않는다.

- 전체 package 목록
- `settings get global airplane_mode_on` — 반드시 `0`
- `dumpsys wifi`의 단일 `Wi-Fi is ...` 상태행
- `settings get secure sysui_qs_tiles`
- 외부 images media row 수
- D1 축: `mobile_data`, `accelerometer_rotation`, `low_power`

값이 비거나 명령이 실패하거나 `sysui_qs_tiles`가 모호하면 `runtime precondition FAIL`로 STOP한다. `sysui_qs_tiles`가 `null`이면 split/full dump에서 상태·SSID suffix를 제거한 타일 identity 순서를 별도 기준으로 남긴다.

## 6. rest41 결정론 파생

목록은 손으로 작성하지 않고 manifest 순서에서 D1 3건을 제외해 파생한다.

```powershell
$rest41 = & python -c "from runner.altbasic_c03_driver import DEFAULT_MANIFEST,load_c03_rows; d={'ALTBASIC_QPN_026','ALTBASIC_QPN_053','ALTBASIC_QPN_056'}; ids=[r['tc_id'] for r in load_c03_rows(DEFAULT_MANIFEST) if r['tc_id'] not in d]; assert len(ids)==41 and len(set(ids))==41; print(','.join(ids))"
if ($LASTEXITCODE -ne 0) { throw 'rest41 derivation failed' }
if (($rest41 -split ',').Count -ne 41) { throw 'rest41 cardinality mismatch' }
```

파생 실패, 중복, 기수 41 불일치는 device 입력 전 STOP이다.

## 7. run1

```powershell
python runner/altbasic_c03_driver.py --run 1 --segment d1 --only ALTBASIC_QPN_026,ALTBASIC_QPN_053,ALTBASIC_QPN_056
```

exit 0이고 `results.csv`에 `runtime mutation FAIL`·`evidence collision STOP`이 없을 때만 다음 호출로 진행한다. D1 `state_unchanged`가 하나라도 실패하면 rest41 입력은 0회다.

```powershell
python runner/altbasic_c03_driver.py --run 1 --segment rest41 --only $rest41
```

run1 수용 조건:

- 결과 행 44개, tc_id unique 44개
- drivable 34개는 각 1회, registry 10개는 분류만 기록
- diagnostics는 `_diagnostics/d1/`과 `_diagnostics/rest41/`로 분리
- `runtime mutation FAIL`·`evidence collision STOP` 없음
- HOME 복귀와 pre-snapshot 상태 불변 확인

하나라도 불충족이면 run2를 시작하지 않는다.

## 8. run2

run1과 같은 identity/precondition을 다시 확인하되 run1 결과로 절차를 바꾸지 않는다.

```powershell
python runner/altbasic_c03_driver.py --run 2 --segment d1 --only ALTBASIC_QPN_026,ALTBASIC_QPN_053,ALTBASIC_QPN_056
```

D1 gate가 GREEN일 때만 실행한다.

```powershell
python runner/altbasic_c03_driver.py --run 2 --segment rest41 --only $rest41
```

run2도 결과 행 44개, unique tc_id 44개와 run1과 같은 안전 조건을 요구한다.

## 9. 공통 중단·복구 규칙

- 동일 tc의 run 내 두 번째 입력은 금지한다. 가드가 충돌을 잡으면 우회하지 않는다.
- 동일 tc의 세 번째 입력 시도는 금지한다.
- 예상 밖 화면은 BACK 1회 후 STOP하고 상태만 채록한다.
- `FORBIDDEN_KEYCODES = {134}`를 유지한다. SOS·발신·긴급전화·전원·재시작·삭제 입력은 금지한다.
- hotspot/Tether state 형식이 기존 기대와 다르면 추측 정규화하지 않는다.
- 실패 뒤 자동 재실행, evidence 삭제, 경로 재사용을 금지한다.
- 복구가 device mutation을 요구하면 사용자 승인 전 실행하지 않는다.

## 10. 종료와 보고

세션 종료 시 다음을 확인한다.

- F0가 Simple HOME에 있고 resumed activity/UI package가 명확하다.
- package, airplane mode, Wi-Fi, QS tile, media, D1 상태 축이 pre-snapshot과 일치한다.
- driver 소유 `/data/local/tmp/altbasic_c03_ui.xml`이 정리됐다.
- mutation debt가 0이다. 불명확하면 안전 상태를 주장하지 않는다.
- thor2j 선존 tracked M 6개가 pre-run bytes와 일치한다.

보고 항목:

- serial/model/incremental/locale 실측
- run1/run2별 44행 기수와 per-tc 결과
- `TWO_RUN_GREEN` 목록
- D1 3건의 state pre/post
- evidence 경로와 충돌 여부
- 최종 HOME·mutation debt
- QPN_145는 `T2-B PENDING`, 관찰 digest 없음

`validate PASS`, `runtime PASS`, `manual evidence observed`, `BUG-GAP observed` 중 실제 근거가 있는 어휘만 사용한다. 단독 `PASS`는 사용하지 않는다.
