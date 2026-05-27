# THOR2_K - Settings 메뉴트리

## Scope
- 단말: THOR2 KR `B06201249E0002B8` (AT-M140 / build `RY07260302M` / ko-KR)
- 대상 앱: `com.android.settings`
- 탐색 방식: 사용자 수동 조작 + 세션 dump 해석 (DFS / 자동 탭 금지)
- 단말 viewport: 480x800

## 표기 규칙 (catalog schema v0.2)
참조: [`catalog_schema.md`](catalog_schema.md) v0.2 — Tier A/B/C 화면 단위, fingerprint 정책, sanitize, DENYLIST, deep link 결과 표준.

- Tier A (단일 화면): `catalog/<screen_id>.md` — depth 0 / depth 1 핵심
- Tier B (통합 MD): `catalog/<batch_name>_inventory.md` — track / batch 단위
- Tier C (비교 MD): `COMPARISON_*.md` — multi-device
- depth 0 fp 의무 (`<pkg>_<name>_<fp8>`), depth 1+ fp 선택 (`<pkg>_<screen_short>`)
- DPAD focus_path = depth 2 / hidden menu만 의무, deep link 진입 가능 시 생략
- 위험 화면 = 기록만, 진입 안 함 (DENYLIST 매치)

## 트리 (진행 중)

| depth | label | screen_id | activity | risk | catalog |
|---|---|---|---|---|---|
| 0 | Settings home | `settings_home_d15a7f0e` | `com.android.settings/.Settings` | 1건: 안전·긴급 (SOS) | [catalog/settings_home_d15a7f0e.md](catalog/settings_home_d15a7f0e.md) |

### depth 0 노출 entries (스크롤 전, 1면)
| 순번 | label | 진입 가능 | 비고 |
|---|---|---|---|
| 1 | (location promo, no title) | ✅ | Android 14 보안 banner |
| 2 | 안전 및 긴급 상황 | 🚫 (DENYLIST) | SOS·비상 — 기록만 |
| 3 | 비밀번호 및 계정 | ✅ | depth 1 후보 |
| 4 | 디지털 웰빙 및 자녀 보호 기능 | ✅ | depth 1 후보 |
| 5 | Google | ✅ | depth 1 후보 |

### depth 0 off-screen (스크롤 확장 결과, 2026-05-27 사용자 UP/DOWN sweep)
| 추가 entries (스크롤 노출) | 비고 |
|---|---|
| 개인 정보 보호 | 권한, 계정 활동, 개인 정보 |
| 위치 | (location promo와 별개 entry) |
| (보안 카테고리, title 미확정) | 화면 잠금, 내 기기 찾기, 앱 보안 — 🚫 DENYLIST "잠금" |

> depth 0 home 전체 entries 확정 미완 (스크롤 끝까지 안 가봄). 본 세션 끝 보고에 정리.

## depth 1 (자동 deep link 진입, 2026-05-27)

| label (home entry) | screen_id | activity | risk | catalog |
|---|---|---|---|---|
| 개인 정보 보호 | `settings_d1_privacy` | `com.android.settings/.Settings$PrivacyDashboardActivity` | summary 내 DENYLIST 매치 (긴급·전화), 진입 OK | [catalog/settings_d1_privacy.md](catalog/settings_d1_privacy.md) |
| 위치 | `settings_d1_location` | `com.android.settings/.Settings$LocationSettingsActivity` | toggle "위치 사용" 진입 X | [catalog/settings_d1_location.md](catalog/settings_d1_location.md) |
| Google | `settings_d1_google` | `com.android.settings/.Settings$AccountDashboardActivity` | 다수 DENYLIST (비밀번호/허용), 화면 OK | [catalog/settings_d1_google.md](catalog/settings_d1_google.md) |
| 디지털 웰빙 및 자녀 보호 기능 | `settings_d1_wellbeing` | `com.google.android.apps.wellbeing/.settings.SettingsActivity` (외부 앱) | dashboard stat, lazy-load 아님 (2.5s 재dump 검증) | [catalog/settings_d1_wellbeing.md](catalog/settings_d1_wellbeing.md) |
| 휴대전화 정보 | `settings_d1_device_info` | `com.android.settings/.Settings$MyDeviceInfoActivity` | KR=AT-M140S + "소프트웨어 업데이트" entry — OTA 트리거 가드 | [catalog/settings_d1_device_info.md](catalog/settings_d1_device_info.md) |
| (home entry 매핑 미확정) | `settings_d1_lensusb` (보너스) | `com.android.settings/.Settings$LensUsbSettingsActivity` | OEM USB, ADB toggle 진입 X | [catalog/settings_d1_lensusb.md](catalog/settings_d1_lensusb.md) |

### KR/JP 비교 자산 (별 문서)
- [`COMPARISON_KR_JP.md`](COMPARISON_KR_JP.md) — 모델명 차이 (AT-M140S/J) / 위젯 차이 (날씨 KR-only) / Settings home 노출 entries 차이 / Device Info entries 차이 / Deep Link batch #2 결과
- JP catalog: [`../THOR2_J - Settings/catalog/jp_baseline_inventory.md`](../THOR2_J%20-%20Settings/catalog/jp_baseline_inventory.md)

## Deep Link batch #2 (2026-05-27, KR 13 추가)
세부: [catalog/d1_batch2_inventory.md](catalog/d1_batch2_inventory.md)

| home entry (추정) | action | activity | 비고 |
|---|---|---|---|
| Wi-Fi / 네트워크 | `WIFI_SETTINGS` | `Settings$WifiSettingsActivity` | ✅ |
| 블루투스 / 연결 | `BLUETOOTH_SETTINGS` | `Settings$ConnectedDeviceDashboardActivity` | 통합 hub |
| 모바일 네트워크 | `NETWORK_OPERATOR_SETTINGS` | OEM MTK | ⚠ dump 거부 |
| 데이터 사용 | `DATA_USAGE_SETTINGS` | `Settings$DataUsageSummaryActivity` | ✅ |
| 소리·진동 | `SOUND_SETTINGS` | `Settings$SoundSettingsActivity` | ✅ slider 5개 |
| 디스플레이 | `DISPLAY_SETTINGS` | `Settings$DisplaySettingsActivity` | ✅ |
| 저장공간 | `STORAGE_SETTINGS` | (action 미존재) | ❌ |
| 접근성 | `ACCESSIBILITY_SETTINGS` | `Settings$AccessibilitySettings` | ✅ |
| 날짜·시간 | `DATE_SETTINGS` | `Settings$DateTimeSettingsActivity` | ✅ |
| 앱 | `APPLICATION_SETTINGS` = `MANAGE_APPLICATIONS_SETTINGS` | `Settings$ManageApplicationsActivity` | ✅ 두 action 동일 activity |
| 사용 정보 접근 | `USAGE_ACCESS_SETTINGS` | `Settings$UsageAccessSettingsActivity` | ✅ |
| 알림 접근 | `NOTIFICATION_LISTENER_SETTINGS` | (action 미존재) | ❌ |
| 화면 보호기 | `DREAM_SETTINGS` | `Settings$DreamSettingsActivity` | ✅ |
| 기본 앱 / 런처 | `HOME_SETTINGS` | `com.google.android.permissioncontroller/.DefaultAppActivity` | ✅ 외부 (MIVE Home / 간편 모드 2개) |
| DuraSpeed (OEM) | `am start -n com.mediatek.duraspeed/.DuraSpeedMainActivity` | Exception | ❌ |

### 진입 금지 (DENYLIST, 기록만)
- 안전 및 긴급 상황 (SOS·비상)
- 비밀번호 및 계정 (비밀번호)
- (보안 카테고리, "잠금")
- (location promo, "허용" 가능성)

## depth 0 home — 스크롤 끝쪽 추가 entries (2026-05-27 batch, 30회 DOWN)

| 추가 entries (끝쪽 노출) | 비고 |
|---|---|
| 시스템 / 언어, 동작, 시간, 백업 | depth 1 후보 (안전) |
| 휴대전화 정보 | depth 1 후보 (`AT-M140S` 모델명 노출) |
| DuraSpeed | MTK 성능 부스터 toggle 추정 |

> Settings home 진입 시 fresh activity 두 가지: `.Settings` (사용자 자연 진입) / `.homepage.SettingsHomepageActivity` (deep link + clear-task). 같은 화면 — 별 activity 명. 차기 모델 비교 자산.

## 폴더 hall sensor 검증 (2026-05-27)

| 상태 | 메인 디스플레이 | sub-display | 잠금 |
|---|---|---|---|
| 닫힘 | OFF (Asleep) | 비활성 (mFocusedApp=null) | — |
| 열림 | ON 즉시 (Awake) | 비활성 그대로 | 잠금 없음, 런처 직진입 |

핵심: `com.hnlens.app.subdisplay` 패키지 존재하지만 **실제 비활성** (dead code). 차기 모델에서 sub-display 활용 가능성 = 핵심 비교 포인트.

## Track #3 — hnlens 기본앱 inventory

세부: [catalog/track3_hnlens_apps_inventory.md](catalog/track3_hnlens_apps_inventory.md)

| 앱 | activity | 핵심 |
|---|---|---|
| simplemode 런처 | `com.hnlens.simplemode/.ui.home.MainActivity` | 앱 아이콘 6 + 위젯 (시간/날짜/날씨). [catalog/simplemode_home.md](catalog/simplemode_home.md) |
| Calculator | `com.hnlens.calculator/com.android.calculator.Calculator` | 0~9 + AC |
| Clock | `com.hnlens.clock/com.android.deskclock.DeskClock` | 세계시각·스톱워치·알람·타이머 |
| Magnifying | `com.hnlens.magnifying/.CameraLauncher` | 손전등 toggle, OEM custom |
| Pedometer | `com.hnlens.pedometer/.MainActivity` | 만보기 dashboard, 목표 10000 |
| FM Radio | `com.hnlens.fmradio/.MainActivity` | 이어폰 안테나 안내 |
| Sound Recorder | `com.hnlens.soundrecorder/com.android.soundrecorder.SoundRecorder` | 음성 녹음, 00:00 |
| Camera | `com.hnlens.camera/com.mediatek.camera.CameraLauncher` | 1x/2x, 사진·동영상 |

진입 보류 (가드): contacts / dialer / messaging / removeapp / update

## depth 2 미달성

| 시도 deep link | 결과 |
|---|---|
| `MANAGE_APP_PERMISSIONS` | result=-91 (action 미존재) → home으로 fallback |

depth 2는 별 회차에서 fragment direct + DPAD navigation 조합 필요.
