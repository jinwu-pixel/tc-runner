# ODIN2 - Settings · RESUME

## 단말 / 앱
- 단말: ODIN2 (AT-M150) · serial `c4324122` · 720x1560 @ 320dpi · ko_KR portrait
- 대상 앱: `com.android.settings` v`1.0.0.1101` (versionCode 10000, minSdk 26, targetSdk 34)
- launcher activity: `com.android.settings/.Settings`

## 진행 상태
- Phase 0 (2026-05-08) — **preflight 완료**
  - Step 1 device 연결 확인 (`adb devices` → `c4324122 device`)
  - Step 2 package/activity 확정 (`pm list packages` + `cmd package resolve-activity --brief`)
  - Step 3 force-stop + `am start -n com.android.settings/.Settings` foreground 확인 (`dumpsys window mCurrentFocus` 일치)
  - Step 4 home XML dump 1회 (`uiautomator dump /sdcard/probe_settings_home.xml` → pull `ODIN2 - Settings/probe_settings_home.xml`, 29478 bytes)
  - Step 5 visible texts 17건 추출 (정적 15 + 동적 2)
  - Step 6 anchor 후보 6건 도출 + dynamic noise 분류
- SMOKE_01 — **scope working tree 작성, runtime/commit 미수행**

## 다음 작업 (사용자 결정 대기)
- A: scope 승인 후 YAML 작성 단계 진입
- B: anchor 보강 probe 1회 추가
- C: Candidate 2 Clock으로 변경
- D: 중단

## Artifact policy
- probe XML / catalog / reports — **commit 금지** (PR 6 §4 forbidden)
- commit candidate (현재 working tree, 미커밋):
  - `ODIN2 - Settings/RESUME.md`
  - `ODIN2 - Settings/MENU_TREE.md`
  - `ODIN2 - Settings/BUG_LOG.md`
  - `ODIN2 - Settings/SETTINGS_SMOKE_01_app_launch_scope.md`

## 사용 규칙
- multi-device 환경 시 모든 adb 호출에 `-s c4324122` prefix 필수
- Git Bash에서 `/sdcard/...` 경로 사용 시 `MSYS_NO_PATHCONV=1` 필요
- policy v2 / Tier 0 자동화 / PR 8 anchor recommender 미적용 (모두 deferred)
