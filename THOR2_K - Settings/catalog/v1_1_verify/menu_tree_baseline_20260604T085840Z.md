# Settings Menu Tree Baseline

- run_id: `20260604T085840Z` · generated_at_utc: `2026-06-04T08:59:10Z`
- device: AT-M140 `B06201249E0002F0` · build `UP1A.231005.007` · ko-KR · 480x800@220 · SIM LG U+
- package: `com.android.settings` · schema v1 (menu-tree-baseline-v1)

## Summary
```yaml
screen_count: 3
reached: 2
reached_external: 0
unreachable: 0
launch_failed: 0
focus_mismatch: 1
dump_rejected: 0
denylist_recorded: 6
observed_texts_total: 44
scroll_passes_total: 5
```

## Google  (`settings_d1_google`)
- nav_path: 설정 → Google
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$AccountDashboardActivity` · fp `39c93c15`
- observed_texts: ko=9, en=1, other=1 · scroll 1 pass (no_new)
- risk_flags (record-only): 비밀번호, 비밀번호 및 계정, 앱에서 데이터를 자동으로 새로고침하도록 허용

| label | kind | role | risk |
|---|---|---|---|
| 비밀번호 및 계정 | title | unknown | denylist |
| 위로 탐색 | menu_row | unknown | none |
| 비밀번호 | menu_row | primary | denylist |
| Google | menu_row | primary | none |
| — | menu_row | summary | none |
| 자동완성 서비스 | menu_row | primary | none |
| Google | menu_row | primary | none |
| 설정 | menu_row | unknown | none |
| 소유자님의 계정 | menu_row | unknown | none |
| 소유자님의 계정 | menu_row | primary | none |
| 계정 추가 | menu_row | primary | none |
| 자동으로 앱 데이터 동기화 | menu_row | primary | none |
| 앱에서 데이터를 자동으로 새로고침하도록 허용 | menu_row | summary | denylist |

## 휴대전화 정보  (`settings_d1_device_info`)
- nav_path: 설정 → 휴대전화 정보
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$MyDeviceInfoActivity` · fp `623a4576`
- observed_texts: ko=24, en=7, other=2 · scroll 4 pass (no_new)
- risk_flags (record-only): 소프트웨어 업데이트, 전화번호, 휴대전화 정보

| label | kind | role | risk |
|---|---|---|---|
| 휴대전화 정보 | title | unknown | denylist |
| 위로 탐색 | menu_row | unknown | none |
| 기본 정보 | menu_row | primary | none |
| 기기 이름 | menu_row | primary | none |
| AT-M140L | menu_row | summary | none |
| 전화번호 | menu_row | primary | denylist |
| 탭하여 정보 표시 | menu_row | summary | none |
| 소프트웨어 업데이트 | menu_row | primary | denylist |
| 소프트웨어 업데이트 | menu_row | summary | denylist |
| 소유자 | menu_row | unknown | none |
| 법률 및 규제 | menu_row | primary | none |
| 법률 정보 | menu_row | primary | none |
| 규제 정보 | menu_row | primary | none |
| 기기 세부정보 | menu_row | primary | none |
| SIM 상태 | menu_row | primary | none |
| LG U+ | menu_row | summary | none |
| 모델 | menu_row | primary | none |
| AT-M140 | menu_row | summary | none |
| IMEI | menu_row | primary | none |
| Android 버전 | menu_row | primary | none |
| 14 | menu_row | summary | none |
| 기기 식별자 | menu_row | primary | none |
| IP 주소 | menu_row | primary | none |
| 2001:4430:41c7:b900::29e:4be2
192.0.0.4 | menu_row | summary | none |
| Wi-Fi MAC 주소 | menu_row | primary | none |
| 확인하려면 저장된 네트워크를 선택하세요. | menu_row | summary | none |
| 기기 Wi‑Fi MAC 주소 | menu_row | primary | none |
| 9c:1e:ce:0c:36:e0 | menu_row | summary | none |
| 블루투스 주소 | menu_row | primary | none |
| 사용할 수 없음 | menu_row | summary | none |
| 첫 통화 개시일 | menu_row | primary | none |
| 2024-10-10 | menu_row | summary | none |
| 빌드 번호 | menu_row | primary | none |
| AT-M140LZ0604U | menu_row | summary | none |

## 디지털 웰빙 및 자녀 보호 기능  (`settings_d1_wellbeing`)
- nav_path: 설정 → 디지털 웰빙
- reach: `FOCUS_MISMATCH` (kind=None) · focus `com.hnlens.simplemode/com.hnlens.simplemode.ui.home.MainActivity` · fp `None`
- observed_texts: ko=0, en=0, other=0 · scroll 0 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
