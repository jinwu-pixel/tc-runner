# THOR2_J - Settings · RESUME

## 단말 / 앱
- 단말: THOR2_J (AT-M140 thor2 alt_thor2, ALT brand) · serial `<thor2_device_serial>` · 480x800 @ 220dpi · **ja-JP** locale (persist.sys.locale=`ja`)
- Android: 14 (UP1A.231005.007), build `SELJY072603MZ0507`
- 대상 앱: `com.android.settings` v`14` (versionCode 34, minSdk 34, targetSdk 34)
- launcher activity: `com.android.settings/.Settings`
- SIM (현재 테스트): KT (한국 SIM, 일본 단말 + 한국 SIM 조합)

## 진행 상태
- Phase 0 (2026-05-08) — **preflight 완료**
  - device 연결 확인 (`adb devices` → `<thor2_device_serial> device`)
  - locale 확인: ja-JP / ja
  - package 확인: com.android.settings v14
  - launch 확인 (`am start -n com.android.settings/.Settings` → foreground)
  - home XML dump (`THOR2_J - Settings/probe_settings_home.xml`, 17909 bytes)
  - visible texts 9건 추출 (text 9 + content-desc 0)
- SMOKE_01 — **validate PASS + runtime PASS 11/11** (working tree, batch commit 후보)
- SMOKE_02 (scroll + post-scroll anchor) — **validate PASS + runtime PASS 13/13** (working tree, batch commit 후보)
- B 단말 횡 비교 측정 (PR 7A delta tool) — ODIN2 ko vs THOR2_J ja, verdict=`meaningful_delta`, jaccard=0.0 (locale 전환 정확 분류)

## 단말 횡 비교 시드 (ODIN2 ko-KR ↔ THOR2_J ja-JP)
| ko-KR (ODIN2 AT-M150) | ja-JP (THOR2_J AT-M140) |
|---|---|
| 설정 | 設定 |
| 설정 검색 | 設定を検索 |
| 네트워크 및 인터넷 | ネットワークとインターネット |
| 연결된 기기 | 接続設定 |
| 앱 | アプリ |
| T 로밍 | 海外ローミング |

- ODIN2 ko-KR home: 17 visible texts (720x1560 화면)
- THOR2_J ja-JP home: 9 visible texts (480x800 화면 → 첫 화면에 들어가는 항목 수가 적음)
- 한국 단말 첫 화면 anchor 6개 중 `알림`/`배터리`는 ja-JP 첫 화면에 미노출 — scroll 필요 가능
- PR 7A delta tool 입력 후보: ko/ja XML 동일 화면 jaccard 측정 가능

## Artifact policy
- probe XML / catalog / reports — **commit 금지** (PR 6 §4 forbidden)
- commit candidate (working tree, 미커밋):
  - `THOR2_J - Settings/RESUME.md`
  - `THOR2_J - Settings/MENU_TREE.md`
  - `THOR2_J - Settings/BUG_LOG.md`
  - `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch_scope.md`
  - `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml`

## 사용 규칙
- multi-device 환경 시 `-s <thor2_device_serial>` prefix 필수 (ODIN2 <odin2_device_serial>와 혼선 주의)
- Git Bash에서 `/sdcard/...` 경로 사용 시 `MSYS_NO_PATHCONV=1` 필요
- ja-JP locale 유지 (테스트 중 언어 변경 금지)
- policy v2 / Tier 0 / PR 8 미적용 (모두 deferred)
