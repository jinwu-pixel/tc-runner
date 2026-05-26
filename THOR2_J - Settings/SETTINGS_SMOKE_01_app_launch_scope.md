# SETTINGS_SMOKE_01 — app launch scope (THOR2_J ja-JP)

**Status:** SCOPE; not committed; YAML 작성 예정 / runtime 예정.
**단말:** THOR2_J (AT-M140 thor2 alt_thor2) · serial `<thor2_device_serial>` · 480x800 @ 220dpi · ja-JP
**앱:** `com.android.settings` v14 (Android 14)
**probe 근거:** `THOR2_J - Settings/probe_settings_home.xml` (Phase 0, 2026-05-08)
**횡 비교:** ODIN2 ko-KR `SETTINGS_SMOKE_01_app_launch.yaml` (commit `5e4dc44`)

---

## 1. 목표
- Settings 앱 cold launch 후 ROOT 화면 진입 검증 (ja-JP)
- 일본어 anchor 6개로 home 화면 정합성 확인
- read-only — toggle / permission / system write 없음
- ODIN2 ko-KR SMOKE_01 동일 패턴, anchor만 일본어로 교체

## 2. 예상 steps
1. SETUP — `am force-stop com.android.settings`
2. SETUP — `am start -n com.android.settings/.Settings`
3. SETUP — `wait 1500ms` (foreground stabilize)
4. ASSERT — `screenshot SETTINGS_SMOKE_01_J_home`
5. ASSERT — `verify_text "設定"` (헤더 anchor, length=2 lint suppress)
6. ASSERT — `verify_text "設定を検索"` (검색바)
7. ASSERT — `verify_text "ネットワークとインターネット"`
8. ASSERT — `verify_text "接続設定"`
9. ASSERT — `verify_text "アプリ"` (length=3, lint OK)
10. ASSERT — `verify_text "海外ローミング"`
11. TEARDOWN — `am force-stop com.android.settings`

총 11 step. 좌표 tap 0, 입력 0, mutation 0.

## 3. anchor 후보 (probe 실측 기반)
정적 visible text 9건 중 6건 채택:

1. `設定` — 헤더 (가장 안정, lint suppress)
2. `設定を検索` — 검색 placeholder
3. `ネットワークとインターネット`
4. `接続設定` (ko-KR `연결된 기기` 대응)
5. `アプリ`
6. `海外ローミング` (ko-KR `T 로밍` 대응)

배제:
- sub-label (`モバイル、Wi-Fi、アクセス ポイント` / `Bluetooth、ペア設定` / `最近使ったアプリ、デフォルトのアプリ`) — main label로 충분
- 첫 화면 미노출 (`通知`/`バッテリー`/`ストレージ` 등) — Phase 1+ 후보

## 4. cleanup
- `force-stop com.android.settings` 1회. persistent 변경 없음.

## 5. mutation risk
- read-only verify 한정 → 0
- ja-JP locale 유지 (테스트 중 언어 변경 금지)

## 6. risk
- 화면 480x800에 9 visible texts만 노출 — 첫 화면 anchor 6개로 제한
- ja-JP 텍스트 길이로 인해 일부 main label이 sub-label과 함께 한 줄에 들어가지 않을 가능성 → 실제 runtime에서 확인
- `海外ローミング`은 통신사·SIM 의존 라벨 (현재 KT SIM에서 노출 확인됨, 다른 SIM 시 변동 가능)
- `am start -n` 권한 — 시스템 settings 일반적으로 starting 가능

## 7. capability
- 신규 capability: **0**
- 기존 capability 충분: force-stop / launch / wait / screenshot / verify_text
- gap: 없음

## 8. generated artifact policy
- probe XML: `THOR2_J - Settings/probe_*.xml` — **commit 금지**
- catalog: `THOR2_J - Settings/catalog/` — 미생성, **commit 금지**
- reports: `reports/` — **commit 금지**
- commit candidate (사용자 승인 후, batch 단위):
  - `THOR2_J - Settings/RESUME.md`
  - `THOR2_J - Settings/MENU_TREE.md`
  - `THOR2_J - Settings/BUG_LOG.md`
  - `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch_scope.md`
  - `THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml`

## 9. non-goals
- 하위 화면 진입 (Phase 1+)
- scroll 후 추가 anchor 발굴 (SMOKE_02 후보)
- locale 변경 검증
- 단말 횡 비교 자동 검증 (PR 7A delta tool 적용은 별 트랙)
- catalog delta 자동 분류 적용
- policy v2 / Tier 0 자동화 적용

## 10. decision boundary
- 본 scope는 working tree만 — **commit 미수행**
- batch commit은 (docs 4 + YAML 1 + runtime PASS evidence) 의미 단위 종결 시 1회
