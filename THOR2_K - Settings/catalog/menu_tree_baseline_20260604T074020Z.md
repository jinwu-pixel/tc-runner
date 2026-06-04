# Settings Menu Tree Baseline

- run_id: `20260604T074020Z` · generated_at_utc: `2026-06-04T07:44:24Z`
- device: AT-M140 `B06201249E0002F0` · build `UP1A.231005.007` · ko-KR · 480x800@220 · SIM LG U+
- package: `com.android.settings` · schema v1 (menu-tree-baseline-v1)

## Summary
```yaml
screen_count: 17
reached: 13
reached_external: 1
unreachable: 0
launch_failed: 0
focus_mismatch: 3
dump_rejected: 0
denylist_recorded: 29
observed_texts_total: 353
scroll_passes_total: 49
```

## 설정 home  (`settings_home`)
- nav_path: 설정
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.homepage.SettingsHomepageActivity` · fp `30c23865`
- observed_texts: ko=44, en=3, other=1 · scroll 6 pass (no_new)
- risk_flags (record-only): 긴급 SOS, 의료 정보, 알림, 보호자 등록, 안심 메시지, SOS 버튼, 비밀번호 및 계정, 안전 및 긴급 상황, 저장된 비밀번호, 자동 완성, 동기화된 계정, 전화 및 문자 발신자 읽어주기, 홈, 잠금 화면, 화면 잠금, 내 기기 찾기, 앱 보안, 휴대전화 정보

| label | kind | role | risk |
|---|---|---|---|
| 설정 | title | unknown | none |
| 설정 검색 | menu_row | unknown | none |
| 네트워크 및 인터넷 | menu_row | primary | none |
| 모바일, Wi-Fi, 핫스팟 | menu_row | summary | none |
| 연결된 기기 | menu_row | primary | none |
| 블루투스, 페어링 | menu_row | summary | none |
| 해외 로밍 | menu_row | primary | none |
| 앱 | menu_row | primary | none |
| 어시스턴트, 최근 앱, 기본 앱 | menu_row | summary | none |
| 안심 기능 | menu_row | primary | none |
| 보호자 등록, 안심 메시지, SOS 버튼 | menu_row | summary | denylist |
| 알림 | menu_row | primary | none |
| 알림 기록, 대화 | menu_row | summary | none |
| 알림 읽어주기 | menu_row | primary | none |
| 전화 및 문자 발신자 읽어주기 | menu_row | summary | denylist |
| 배터리 | menu_row | primary | none |
| 100% | menu_row | summary | none |
| 저장용량 | menu_row | primary | none |
| 27% 사용 - 23.37GB 사용 가능 | menu_row | summary | none |
| 소리 및 진동 | menu_row | primary | none |
| 볼륨, 진동, 방해 금지 모드 | menu_row | summary | none |
| 디스플레이 | menu_row | primary | none |
| 글꼴 크기, 밝기 | menu_row | summary | none |
| 배경화면 및 스타일 | menu_row | primary | none |
| 홈, 잠금 화면 | menu_row | summary | denylist |
| 모드 설정 | menu_row | primary | none |
| 간편 및 일반 모드 | menu_row | summary | none |
| 접근성 | menu_row | primary | none |
| 디스플레이, 상호작용, 오디오 | menu_row | summary | none |
| 보안 | menu_row | primary | none |
| 화면 잠금, 내 기기 찾기, 앱 보안 | menu_row | summary | denylist |
| 개인 정보 보호 | menu_row | primary | none |
| 권한, 계정 활동, 개인 정보 | menu_row | summary | none |
| 위치 | menu_row | primary | none |
| 사용 - 앱 7개가 위치에 액세스할 수 있음 | menu_row | summary | none |
| 안전 및 긴급 상황 | menu_row | primary | denylist |
| 긴급 SOS, 의료 정보, 알림 | menu_row | summary | denylist |
| 비밀번호 및 계정 | menu_row | primary | denylist |
| 저장된 비밀번호, 자동 완성, 동기화된 계정 | menu_row | summary | denylist |
| 디지털 웰빙 및 자녀 보호 기능 | menu_row | primary | none |
| 기기 사용 시간, 앱 타이머, 취침 시간 일정 | menu_row | summary | none |
| Google | menu_row | primary | none |
| 서비스 및 환경설정 | menu_row | summary | none |
| DuraSpeed | menu_row | primary | none |
| 시스템 | menu_row | primary | none |
| 언어, 동작, 시간, 백업 | menu_row | summary | none |
| 휴대전화 정보 | menu_row | primary | denylist |
| AT-M140L | menu_row | summary | none |

## 개인 정보 보호  (`settings_d1_privacy`)
- nav_path: 설정 → 개인 정보 보호
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$PrivacyDashboardActivity` · fp `f87f7ee7`
- observed_texts: ko=28, en=0, other=0 · scroll 4 pass (no_new)
- risk_flags (record-only): 비밀번호 표시, 앱 및 서비스에 적용. 설정이 꺼져 있어도 긴급 전화번호로 전화를 걸 때 마이크 데이터가 공유될 수 있습니다., 앱이 복사된 텍스트, 이미지 또는 기타 콘텐츠에 액세스할 때 메시지 표시, 위치 데이터 공유 방법 업데이트, 잠금 화면에 미디어 표시, 잠금 화면에 표시할 알림, 재생을 빠르게 재개할 수 있도록 잠금 화면에서 미디어 플레이어를 계속 열어 둡니다., 저장된 비밀번호, 신용카드, 주소

| label | kind | role | risk |
|---|---|---|---|
| 개인 정보 보호 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 개인 정보 대시보드 | menu_row | primary | none |
| 최근에 권한을 사용한 앱 표시 | menu_row | summary | none |
| 권한 관리자 | menu_row | primary | none |
| 내 데이터에 대한 앱 액세스 권한 제어 | menu_row | summary | none |
| 위치 데이터 공유 방법 업데이트 | menu_row | primary | denylist |
| 위치 데이터 공유 방법을 변경했을 수 있는 앱을 검토합니다. | menu_row | summary | none |
| 마이크 액세스 | menu_row | primary | none |
| 앱 및 서비스에 적용. 설정이 꺼져 있어도 긴급 전화번호로 전화를 걸 때 마이크 데이터가 공유될 수 있습니다. | menu_row | summary | denylist |
| 비밀번호 표시 | menu_row | primary | denylist |
| 입력할 때 잠깐 표시 | menu_row | summary | none |
| 잠금 화면에 표시할 알림 | menu_row | primary | denylist |
| 모든 알림 내용 표시 | menu_row | summary | none |
| 잠금 화면에 미디어 표시 | menu_row | primary | denylist |
| 재생을 빠르게 재개할 수 있도록 잠금 화면에서 미디어 플레이어를 계속 열어 둡니다. | menu_row | summary | denylist |
| 클립보드 액세스 표시 | menu_row | primary | none |
| 앱이 복사된 텍스트, 이미지 또는 기타 콘텐츠에 액세스할 때 메시지 표시 | menu_row | summary | denylist |
| 헬스 커넥트 | menu_row | primary | none |
| 건강 데이터에 대한 앱 액세스 제어 | menu_row | summary | none |
| Google 자동 완성 서비스 | menu_row | primary | none |
| 저장된 비밀번호, 신용카드, 주소 | menu_row | summary | denylist |
| 활동 제어 | menu_row | primary | none |
| Google에 저장할 활동 및 정보 선택 | menu_row | summary | none |
| 광고 | menu_row | primary | none |
| 이 기기에서 광고 개인 최적화 관리 | menu_row | summary | none |
| 사용 및 진단 | menu_row | primary | none |
| 데이터를 공유하여 Android 개선에 참여 | menu_row | summary | none |

## 위치  (`settings_d1_location`)
- nav_path: 설정 → 위치
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$LocationSettingsActivity` · fp `0782e82f`
- observed_texts: ko=14, en=0, other=0 · scroll 3 pass (no_new)
- risk_flags (record-only): 전화

| label | kind | role | risk |
|---|---|---|---|
| 위치 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 위치 사용 | menu_row | unknown | none |
| 최근에 위치 정보에 액세스한 앱 | menu_row | primary | none |
| 간편 모드 | menu_row | primary | none |
| 0분 전 | menu_row | summary | none |
| 전화 | menu_row | primary | denylist |
| 45분 전 | menu_row | summary | none |
| 모두 보기 | menu_row | primary | none |
| 앱 위치 정보 액세스 권한 | menu_row | primary | none |
| 16개 중 7개의 앱이 위치에 액세스할 수 있음 | menu_row | summary | none |
| 위치 서비스 | menu_row | primary | none |
| 위치 정확도가 켜져 있으면 앱과 서비스에서 더 정확한 위치를 얻습니다. 이를 위해 Google은 기기 센서 및 기기의 무선 신호에 대한 정보를 주기적으로 처리하여 무선 신호 위치 정보를 크라우드소싱합니다. 이러한 정보는 사용자의 신원을 밝히지 않고 사용되며, 위치 정확도와 위치 기반 서비스를 개선하고, 사용자의 요구사항 충족을 목적으로 Google 및 서드 파티의 적법한 이익에 따라 Google 서비스를 개선, 제공, 유지하는 데 사용됩니다.

근처 기기 액세스 권한이 있는 앱은 연결된 기기 간의 상대적인 위치를 파악할 수 있습니다. | menu_row | primary | none |
| 위치 설정 자세히 알아보기 | menu_row | unknown | none |

## Google  (`settings_d1_google`)
- nav_path: 설정 → Google
- reach: `FOCUS_MISMATCH` (kind=None) · focus `com.android.settings/com.android.settings.Settings` · fp `None`
- observed_texts: ko=0, en=0, other=0 · scroll 0 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|

## 휴대전화 정보  (`settings_d1_device_info`)
- nav_path: 설정 → 휴대전화 정보
- reach: `FOCUS_MISMATCH` (kind=None) · focus `com.android.settings/com.android.settings.Settings` · fp `None`
- observed_texts: ko=0, en=0, other=0 · scroll 0 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|

## Wi-Fi / 네트워크  (`settings_d1_wifi`)
- nav_path: 설정 → Wi-Fi
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$WifiSettingsActivity` · fp `500f6324`
- observed_texts: ko=21, en=15, other=0 · scroll 5 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
| Wi-Fi | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 연결 문제 해결 | button | unknown | none |
| Wi-Fi | menu_row | primary | none |
| ALT,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| ALT | menu_row | primary | none |
| ALT2,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| ALT2 | menu_row | primary | none |
| KT_GiGA_2G_12F,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| KT_GiGA_2G_12F | menu_row | primary | none |
| KT_GiGA_5G_ALT,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| KT_GiGA_5G_ALT | menu_row | primary | none |
| [LG_StickVacuum]ccd4,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| [LG_StickVacuum]ccd4 | menu_row | primary | none |
| kianchoi 2.4G,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| kianchoi 2.4G | menu_row | primary | none |
| kianchoi 5G,Wi-Fi 신호가 강합니다.,보안 네트워크 | menu_row | unknown | none |
| kianchoi 5G | menu_row | primary | none |
| DIRECT-C4 C56x Series,Wi-Fi 신호 막대가 세 개입니다.,보안 네트워크 | menu_row | unknown | none |
| DIRECT-C4 C56x Series | menu_row | primary | none |
| [LG_AirPurifier]89ff,Wi-Fi 신호 막대가 세 개입니다.,보안 네트워크 | menu_row | unknown | none |
| [LG_AirPurifier]89ff | menu_row | primary | none |
| snri12,Wi-Fi 신호 막대가 세 개입니다.,보안 네트워크 | menu_row | unknown | none |
| snri12 | menu_row | primary | none |
| snri125ghz,Wi-Fi 신호 막대가 세 개입니다.,보안 네트워크 | menu_row | unknown | none |
| snri125ghz | menu_row | primary | none |
| DIRECT-D0 C51x Series,Wi-Fi 신호 막대가 두 개입니다.,보안 네트워크 | menu_row | unknown | none |
| DIRECT-D0 C51x Series | menu_row | primary | none |
| nearsolution_NEW_5G,Wi-Fi 연결이 끊어졌습니다.,보안 네트워크 | menu_row | unknown | none |
| nearsolution_NEW_5G | menu_row | primary | none |
| 네트워크 추가 | menu_row | primary | none |
| 네트워크 환경설정 | menu_row | primary | none |
| Wi‑Fi가 자동으로 다시 사용 설정됨 | menu_row | summary | none |
| 이동통신사 외의 데이터 사용량 | menu_row | primary | none |
| 5월 7일 ~ 6월 4일에 0B 사용함 | menu_row | summary | none |
| nearsolution_guest_2.4G,Wi-Fi 신호 막대가 한 개입니다.,보안 네트워크 | menu_row | unknown | none |
| nearsolution_guest_2.4G | menu_row | primary | none |

## 연결된 기기  (`settings_d1_bluetooth`)
- nav_path: 설정 → 연결된 기기
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$ConnectedDeviceDashboardActivity` · fp `e1974853`
- observed_texts: ko=12, en=1, other=0 · scroll 2 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
| 연결된 기기 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 다른 기기 | menu_row | primary | none |
| USB | menu_row | primary | none |
| 기기 충전 | menu_row | summary | none |
| 새 기기와 페어링 | menu_row | primary | none |
| 페어링을 위해 블루투스가 켜집니다 | menu_row | summary | none |
| 저장된 기기 | menu_row | primary | none |
| 전체 보기 | menu_row | primary | none |
| 블루투스를 사용 설정함 | menu_row | summary | none |
| 연결 환경설정 | menu_row | primary | none |
| 블루투스 | menu_row | summary | none |
| 다른 기기에 연결하려면 블루투스를 사용 설정하세요. | menu_row | primary | none |

## 데이터 사용  (`settings_d1_data_usage`)
- nav_path: 설정 → 데이터 사용
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$DataUsageSummaryActivity` · fp `4205c738`
- observed_texts: ko=14, en=3, other=0 · scroll 2 pass (no_new)
- risk_flags (record-only): 앱을 사용하지 않을 때 동기화, 앱 업데이트 등 백그라운드 데이터 사용을 제한합니다.

| label | kind | role | risk |
|---|---|---|---|
| 데이터 사용량 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 124MB 사용됨 | menu_row | unknown | none |
| 0B | menu_row | unknown | none |
| 2.00GB | menu_row | unknown | none |
| 데이터 사용량 경고 한도: 2.00GB | menu_row | unknown | none |
| 26일 남음 | menu_row | unknown | none |
| 데이터 절약 모드 | menu_row | primary | none |
| 앱을 사용하지 않을 때 동기화, 앱 업데이트 등 백그라운드 데이터 사용을 제한합니다. | menu_row | summary | denylist |
| 모바일 | menu_row | primary | none |
| 모바일 데이터 | menu_row | primary | none |
| 모바일 데이터 사용량 | menu_row | primary | none |
| 6월 1일~30일에 124MB 사용함 | menu_row | summary | none |
| 데이터 경고 및 한도 | menu_row | primary | none |
| Wi-Fi | menu_row | primary | none |
| Wi-Fi 데이터 사용량 | menu_row | primary | none |
| 5월 7일 ~ 6월 4일에 0B 사용함 | menu_row | summary | none |

## 소리·진동  (`settings_d1_sound`)
- nav_path: 설정 → 소리 및 진동
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$SoundSettingsActivity` · fp `dce31011`
- observed_texts: ko=20, en=3, other=0 · scroll 3 pass (no_new)
- risk_flags (record-only): 전화 벨소리, 화면 잠금 소리

| label | kind | role | risk |
|---|---|---|---|
| 소리 및 진동 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 미디어 볼륨 | menu_row | primary | none |
| 미디어 볼륨 | menu_row | unknown | none |
| 통화 볼륨 | menu_row | primary | none |
| 통화 볼륨 | menu_row | unknown | none |
| 벨소리 볼륨 | menu_row | primary | none |
| 벨소리 볼륨 | menu_row | unknown | none |
| 알림 볼륨 | menu_row | primary | none |
| 알림 볼륨 | menu_row | unknown | none |
| 알람 볼륨 | menu_row | primary | none |
| 알람 볼륨 | menu_row | unknown | none |
| 방해 금지 모드 | menu_row | primary | none |
| 꺼짐 | menu_row | summary | none |
| 전화 벨소리 | menu_row | primary | denylist |
| Themos | menu_row | summary | none |
| 미디어 | menu_row | primary | none |
| 플레이어 표시 | menu_row | summary | none |
| 진동 및 햅틱 | menu_row | primary | none |
| 사용 | menu_row | summary | none |
| 기본 알림 소리 | menu_row | primary | none |
| Alya | menu_row | summary | none |
| 기본 알람 소리 | menu_row | primary | none |
| Platinum | menu_row | summary | none |
| 다이얼패드 효과음 | menu_row | primary | none |
| 화면 잠금 소리 | menu_row | primary | denylist |
| 충전 소리 및 진동 | menu_row | primary | none |
| 터치음 | menu_row | primary | none |

## 디스플레이  (`settings_d1_display`)
- nav_path: 설정 → 디스플레이
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$DisplaySettingsActivity` · fp `7f6766b0`
- observed_texts: ko=25, en=0, other=1 · scroll 3 pass (no_new)
- risk_flags (record-only): 잠금 디스플레이, 잠금 화면, 화면 자동 잠금 시간

| label | kind | role | risk |
|---|---|---|---|
| 디스플레이 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 밝기 | menu_row | primary | none |
| 밝기 수준 | menu_row | primary | none |
| 83% | menu_row | summary | none |
| 키패드 조명 동작 시간 | menu_row | primary | none |
| 5초 | menu_row | summary | none |
| 밝기 자동 조절 | menu_row | primary | none |
| 밝기 자동 조절 | toggle | unknown | toggle |
| 잠금 디스플레이 | menu_row | primary | denylist |
| 잠금 화면 | menu_row | primary | denylist |
| 모든 알림 내용 표시 | menu_row | summary | none |
| 화면 자동 잠금 시간 | menu_row | primary | denylist |
| 30분 이상 동작이 없을 때 | menu_row | summary | none |
| 디자인 | menu_row | primary | none |
| 디스플레이 크기 및 텍스트 | menu_row | primary | none |
| 색상 | menu_row | primary | none |
| 야간 조명 | menu_row | primary | none |
| 자동으로 켜지지 않음 | menu_row | summary | none |
| 기타 디스플레이 제어 | menu_row | primary | none |
| 화면 자동 회전 | menu_row | primary | none |
| 네트워크 이름 | menu_row | primary | none |
| 상태 표시줄에 네트워크 이름 표시 | menu_row | summary | none |
| 터치 민감도 | menu_row | primary | none |
| 화면 보호용 필름을 사용할 때도 터치가 입력되도록 터치 민감도를 높일 수 있습니다. | menu_row | summary | none |
| 화면 보호기 | menu_row | primary | none |
| 사용 안함 | menu_row | summary | none |

## 접근성  (`settings_d1_accessibility`)
- nav_path: 설정 → 접근성
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$AccessibilitySettingsActivity` · fp `3c57ace7`
- observed_texts: ko=32, en=1, other=0 · scroll 5 pass (no_new)
- risk_flags (record-only): 휴대전화의 최소 밝기보다 화면 어둡게 하기

| label | kind | role | risk |
|---|---|---|---|
| 접근성 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 다운로드한 앱 | menu_row | primary | none |
| TalkBack | menu_row | primary | none |
| 사용 안함/화면의 항목 읽어주기 | menu_row | summary | none |
| 스위치 제어 | menu_row | primary | none |
| 사용 안함/스위치 또는 전면 카메라로 기기를 제어합니다 | menu_row | summary | none |
| 텍스트 읽어주기 | menu_row | primary | none |
| 사용 안함/선택한 텍스트 듣기 | menu_row | summary | none |
| 디스플레이 | menu_row | primary | none |
| 디스플레이 크기 및 텍스트 | menu_row | primary | none |
| 색상 및 모션 | menu_row | primary | none |
| 더 어둡게 | menu_row | primary | none |
| 휴대전화의 최소 밝기보다 화면 어둡게 하기 | menu_row | summary | denylist |
| 확대 | menu_row | primary | none |
| 사용 안함 | menu_row | summary | none |
| 상호작용 관리 | menu_row | primary | none |
| 접근성 메뉴 | menu_row | primary | none |
| 사용 안함/큰 메뉴로 기기 제어 | menu_row | summary | none |
| 타이밍 제어 | menu_row | primary | none |
| 시스템 제어 | menu_row | primary | none |
| 진동 및 햅틱 | menu_row | primary | none |
| 사용 | menu_row | summary | none |
| 자막 | menu_row | primary | none |
| 자막 환경설정 | menu_row | primary | none |
| 오디오 | menu_row | primary | none |
| 오디오 설명 | menu_row | primary | none |
| 오디오 설명 기능이 지원되는 영화 및 프로그램의 상황을 음성 설명으로 듣기 | menu_row | summary | none |
| 플래시 알림 | menu_row | primary | none |
| 오디오 조정 | menu_row | primary | none |
| 일반 | menu_row | primary | none |
| 접근성 단축키 | menu_row | primary | none |
| 텍스트 음성 변환 출력 | menu_row | primary | none |

## 날짜·시간  (`settings_d1_date`)
- nav_path: 설정 → 날짜 및 시간
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$DateTimeSettingsActivity` · fp `d6a3c742`
- observed_texts: ko=17, en=0, other=0 · scroll 2 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
| 날짜 및 시간 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 자동으로 시간 설정 | menu_row | primary | none |
| 네트워크 제공 시간 사용 | menu_row | summary | none |
| 날짜 설정 | menu_row | primary | none |
| 2026년 6월 4일 | menu_row | summary | none |
| 시간 설정 | menu_row | primary | none |
| 오후 4:43 | menu_row | summary | none |
| 시간대 자동 설정 | menu_row | primary | none |
| 네트워크 제공 시간대 사용 | menu_row | summary | none |
| 표준시간대 선택 | menu_row | primary | none |
| GMT+09:00 한국 표준시 | menu_row | summary | none |
| 위치 사용 | menu_row | primary | none |
| 시간대 설정을 위해 위치가 사용될 수 있음 | menu_row | summary | none |
| 언어 기본값 사용 | menu_row | primary | none |
| 24시간 형식 사용 | menu_row | primary | none |
| 오후 1:00 | menu_row | summary | none |

## 앱  (`settings_d1_apps`)
- nav_path: 설정 → 앱
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$ManageApplicationsActivity` · fp `317803e8`
- observed_texts: ko=32, en=41, other=0 · scroll 8 pass (max_passes)
- risk_flags (record-only): 메시지, 음성 녹음, 전화

| label | kind | role | risk |
|---|---|---|---|
| 모든 앱 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 검색 | button | unknown | none |
| 옵션 더보기 | menu_row | unknown | none |
| 간편 모드 | menu_row | primary | none |
| 119kB | menu_row | summary | none |
| 계산기 | menu_row | primary | none |
| 0B | menu_row | summary | none |
| 내 기기 찾기 | menu_row | primary | none |
| 11.59MB | menu_row | summary | none |
| 니어메디2 | menu_row | primary | none |
| 0B | menu_row | summary | none |
| 당신의 U+
(고객센터) | menu_row | primary | none |
| 돋보기 | menu_row | primary | none |
| 디지털 웰빙 | menu_row | primary | none |
| 647kB | menu_row | summary | none |
| 라디오 | menu_row | primary | none |
| 만보기 | menu_row | primary | none |
| 36.86kB | menu_row | summary | none |
| 메시지 | menu_row | primary | denylist |
| 32.77kB | menu_row | summary | none |
| 배경화면 및 스타일 | menu_row | primary | none |
| 8.19kB | menu_row | summary | none |
| 설정 | menu_row | primary | none |
| 42.76MB | menu_row | summary | none |
| 시계 | menu_row | primary | none |
| 28.67kB | menu_row | summary | none |
| 안심 기능 | menu_row | primary | none |
| 4.10kB | menu_row | summary | none |
| 연락처 | menu_row | primary | none |
| 원스토어 | menu_row | primary | none |
| 451kB | menu_row | summary | none |
| 위급 상황 정보 | menu_row | primary | none |
| 389kB | menu_row | summary | none |
| 음성 녹음 | menu_row | primary | denylist |
| 재난 문자 | menu_row | primary | none |
| 40.96kB | menu_row | summary | none |
| 전화 | menu_row | primary | denylist |
| 86.02kB | menu_row | summary | none |
| 지도 | menu_row | primary | none |
| 606kB | menu_row | summary | none |
| 카메라 | menu_row | primary | none |
| 캘린더 | menu_row | primary | none |
| 700kB | menu_row | summary | none |
| 파일 | menu_row | primary | none |
| 16.38kB | menu_row | summary | none |
| Chrome | menu_row | primary | none |
| Drive | menu_row | primary | none |
| 725kB | menu_row | summary | none |
| Files by Google | menu_row | primary | none |
| 422kB | menu_row | summary | none |
| Gallery | menu_row | primary | none |
| 160kB | menu_row | summary | none |
| Gmail | menu_row | primary | none |
| 799kB | menu_row | summary | none |
| Google 어시스턴트 | menu_row | primary | none |
| Google Go | menu_row | primary | none |
| 184kB | menu_row | summary | none |
| Google Play 서비스 | menu_row | primary | none |
| 344MB | menu_row | summary | none |
| Google Play 스토어 | menu_row | primary | none |
| 131MB | menu_row | summary | none |
| Google TV | menu_row | primary | none |
| 623kB | menu_row | summary | none |
| Keep 메모 | menu_row | primary | none |
| 32.02MB | menu_row | summary | none |
| LGU_GPSnWPS | menu_row | primary | none |
| 28.92MB | menu_row | summary | none |
| Meet | menu_row | primary | none |
| 766kB | menu_row | summary | none |
| MIVE Home | menu_row | primary | none |
| OQC | menu_row | primary | none |
| 45.69MB | menu_row | summary | none |
| YouTube | menu_row | primary | none |

## 사용 정보 접근  (`settings_d1_usage_access`)
- nav_path: 설정 → 사용 정보 접근
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$UsageAccessSettingsActivity` · fp `11bc6ed7`
- observed_texts: ko=10, en=2, other=0 · scroll 2 pass (no_new)
- risk_flags (record-only): 허용됨

| label | kind | role | risk |
|---|---|---|---|
| 사용 기록 액세스 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 검색 | button | unknown | none |
| 옵션 더보기 | menu_row | unknown | none |
| 간편 모드 | menu_row | primary | none |
| 허용됨 | menu_row | summary | denylist |
| 디지털 웰빙 | menu_row | primary | none |
| 허용됨 | menu_row | summary | denylist |
| 원스토어 | menu_row | primary | none |
| 허용됨 | menu_row | summary | denylist |
| Files by Google | menu_row | primary | none |
| 허용됨 | menu_row | summary | denylist |
| Google Play 서비스 | menu_row | primary | none |
| 허용됨 | menu_row | summary | denylist |
| Google Play 스토어 | menu_row | primary | none |
| MIVE Home | menu_row | primary | none |

## 화면 보호기  (`settings_d1_dream`)
- nav_path: 설정 → 화면 보호기
- reach: `REACHED` (kind=internal) · focus `com.android.settings/com.android.settings.Settings$DreamSettingsActivity` · fp `45a25645`
- observed_texts: ko=8, en=0, other=0 · scroll 3 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
| 화면 보호기 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 화면 보호기 사용 | menu_row | unknown | none |
| 표시 시간 | menu_row | primary | none |
| 도킹 및 충전 중 | menu_row | summary | none |
| 화면 보호기 선택 | title | primary | none |
| 시계 | menu_row | unknown | none |
| 색상 | menu_row | unknown | none |

## 기본 앱 / 런처  (`settings_d1_home_launcher`)
- nav_path: 설정 → 기본 앱
- reach: `REACHED_EXTERNAL_PACKAGE` (kind=external) · focus `com.google.android.permissioncontroller/com.android.permissioncontroller.role.ui.DefaultAppActivity` · fp `f1445293`
- observed_texts: ko=4, en=1, other=0 · scroll 1 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
| 기본 홈 앱 | title | unknown | none |
| 위로 탐색 | menu_row | unknown | none |
| 간편 모드 | menu_row | primary | none |
| MIVE Home | menu_row | primary | none |
| Android 기기의 홈 화면을 대체하고 기기의 콘텐츠 및 기능에 액세스할 수 있게 해주는 앱(런처라고도 함) | menu_row | primary | none |

## 디지털 웰빙 및 자녀 보호 기능  (`settings_d1_wellbeing`)
- nav_path: 설정 → 디지털 웰빙
- reach: `FOCUS_MISMATCH` (kind=None) · focus `com.hnlens.simplemode/com.hnlens.simplemode.ui.home.MainActivity` · fp `None`
- observed_texts: ko=0, en=0, other=0 · scroll 0 pass (no_new)

| label | kind | role | risk |
|---|---|---|---|
