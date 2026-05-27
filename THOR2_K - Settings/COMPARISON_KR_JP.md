# THOR2 KR/JP 비교 summary (2026-05-27)

차기 모델 비교 자산 — 같은 alt_thor2 / AT-M140 base, locale/lineup 변종.

> schema: [`catalog_schema.md`](catalog_schema.md) v0.2 §11 (multi-device 비교 Tier C). 표준 섹션: baseline / depth 0 노출 / depth 1 1:1 / 차기 모델 비교 자산 / 미진.

## 단말 baseline 차이
| 필드 | KR (`<kr-serial>`) | JP (`<jp-serial>`) |
|---|---|---|
| 모델명 | **AT-M140S** | **AT-M140J** |
| build | `RY07260302M` | `SELJY072603MZ0527` |
| locale | ko-KR | ja-JP |
| SIM | SKT | KT (한국 SIM이 JP 단말에 삽입) |
| product / device / Android | `alt_thor2` / `thor2` / 14 | (동일) |

## simplemode 런처
| 항목 | KR | JP |
|---|---|---|
| 위젯 | 시간 + 날짜 + **날씨** (`<weather-location>` 흐림 13° 좋음) | 시간 + 날짜만 |
| 앱 아이콘 | 갤러리 / 라디오 / 메시지 / 설정 / 전화 / 카메라 | ギャラリー / FMラジオ / メッセージ / 設定 / 電話 / カメラ |
| 매핑 | 6개 동일 | 6개 동일 (라벨 번역만) |

🔑 **KR-only 위젯**: 날씨 (현지 정보 통합). 차기 모델에서 변동 가능 핵심 포인트.

## Settings home depth 0 노출 entries
같은 `.SettingsHomepageActivity` (clear-task 진입). 한 화면 노출 entries 다름.

| 비교 | KR (이전 dump) | JP (이번 dump) |
|---|---|---|
| 첫 노출 entries | 사용 promo / 안전 및 긴급 / 비밀번호 및 계정 / 디지털 웰빙 / Google | ネットワークとインターネット / 接続設定 / アプリ / **海外ローミング** |
| KR-only | 사용 promo (사용 - 앱 10개가 위치에 액세스) / 안전 및 긴급 상황 | — |
| JP-only | — | **海外ローミング** (해외 로밍, JP 라인업 특화 추정) |

> ⚠ 한 화면 노출 entries 차이는 (1) locale rearrangement (2) 라인업별 entry 추가/제거 (3) Android 14 Settings A/B 실험 노출 차이 중 하나. depth 0 완전 스크롤 매핑이 필요 (별 회차).

## depth 1 SubSettings (deep link 검증)

| home entry | activity | KR | JP |
|---|---|---|---|
| 개인 정보 보호 / プライバシー | `PrivacyDashboardActivity` | ✅ 5 라벨 | ✅ 7 라벨 (KR 5 + 추가 summary) |
| 위치 / 位置情報 | `LocationSettingsActivity` | ✅ SKT 앱 노출 (간편 모드 / 에이닷 전화) | ✅ **Appium Settings** + 표준 앱 |
| Google / Google | `AccountDashboardActivity` | ✅ 1:1 라벨 | ✅ 1:1 |
| 휴대전화 정보 / デバイス情報 | `MyDeviceInfoActivity` | ✅ AT-M140S / **소프트웨어 업데이트** | ✅ AT-M140J / **法的情報·認証情報** |
| 디지털 웰빙 / Digital Wellbeing | `com.google.android.apps.wellbeing.SettingsActivity` (외부 앱) | ✅ 3 라벨 / lazy load 아님 | ✅ 3 라벨 (영문+ツール 혼용) |
| 시스템 | (deep link `SYSTEM_SETTINGS` 양 단말 미존재) | ❌ fallback | ❌ fallback |
| DuraSpeed | (deep link 미존재) | ❌ KR only entry | (JP home에 노출 미확인) |
| Boost (보너스) | `LensUsbSettingsActivity` (KR 보너스) | ✅ 영문 OEM | (JP 미시도) |

## Location 앱 리스트 (carrier 차이)
| 단말 | 노출 앱 |
|---|---|
| KR | 간편 모드 / 에이닷 전화 / 전화 (다이얼러) |
| JP | カメラ / Appium Settings / 電話 |

🔑 KR에는 SKT 고유 앱 (간편 모드 = SKT 시니어 모드, 에이닷 = SKT AI 비서). JP에는 자동화 테스트 도구 (Appium Settings) 설치. **carrier-specific app 설치 차이가 위치 권한 사용 앱 리스트에 노출됨**.

## Device Info 차이 (라인업 / 단말명 / OS 변종)
| 필드 | KR | JP |
|---|---|---|
| 모델명 | AT-M140S | AT-M140J |
| 추가 entry | **소프트웨어 업데이트** | **法的情報** / **認証情報** |
| 공통 | 기기 이름 / 기본 정보 / 법률 및 규제 / 소유자 / 전화번호 / 탭하여 정보 표시 (1:1 번역) | デバイス名 / 基本情報 / 法律と規制 / 所有者 / 電話番号 / 情報を表示するにはタップ |

🔑 핵심 발견:
- KR-only "소프트웨어 업데이트" entry → FotaApp 진입 — KR에서만 OTA 트리거 가능 (JP는 다른 경로일 가능성)
- JP-only "法的情報" / "認証情報" → JP 시장 규제 요구 (법적 정보 표시 의무)

## Privacy / Sync 라벨 매핑 (1:1 직역, 화면 구성 동일)
거의 완벽 매핑. 별 차이 없음.

## 차기 모델 비교 자산 — 핵심 포인트
1. **모델명 suffix 규칙** (`S=SKT`, `J=Japan`) — 차기 라인업 명명 패턴
2. **carrier-specific 위젯 / 앱**: KR=날씨/간편모드/에이닷 / JP=Appium (테스트), 海外ローミング
3. **OS entry 차이**: 소프트웨어 업데이트 (KR) ↔ 法的情報·認証情報 (JP) — 시장 규제 reflect
4. **공통 vs 차이**: deep link로 진입 가능한 SubSettings는 거의 1:1. home 노출 entries는 locale-driven 정렬·필터링 차이.

## 미진 / 별 회차 후보
- depth 0 home **전체 entries 스크롤 끝까지** 매핑 (KR + JP) — 노출 entries 차이가 실제 entry 차이인지 정렬 차이인지 확정
- depth 2 진입 (KR/JP 둘 다)
- 시스템 / DuraSpeed deep link 대체 진입 경로
- dialer / messaging / gallery 패키지 식별 + KR/JP 비교
- JP 단말의 LensUsbSettings / OEM custom 화면 추적

## Deep Link batch #2 (2026-05-27) — KR 단독 진행 (JP disconnected)

KR Tier A 15 actions + OEM DuraSpeed 시도. 세부는 [`catalog/d1_batch2_inventory.md`](catalog/d1_batch2_inventory.md).

### KR 진입 성공 (13)
WIFI / BLUETOOTH (`ConnectedDeviceDashboardActivity` 통합) / DATA_USAGE / SOUND / DISPLAY / ACCESSIBILITY / DATE / APPLICATION (= MANAGE_APPLICATIONS 동일 activity) / USAGE_ACCESS / DREAM / HOME_SETTINGS (`DefaultAppActivity` 외부 permissioncontroller)

### KR 실패 (3 + 1)
- `STORAGE_SETTINGS` / `NOTIFICATION_LISTENER_SETTINGS` action 미존재 (result -91)
- `NETWORK_OPERATOR_SETTINGS` uiautomator dump 실패 (OEM `mediatek.settings.network.MobileNetworkSettings` 가 view hierarchy extraction 거부)
- DuraSpeed `am start -n` exception

### JP — 부분 수행 (사용자 USB 재연결 후 2nd attempt)
- ✅ valid 6: wifi / bluetooth / **network_op** / data_usage / sound / display (KR과 동일 deep link)
- ❌ retry 7: `STORAGE_SETTINGS` (action 미존재 result -91) 직후 Settings 앱 전체 ANR 트리거 → 이후 accessibility/date/application/manage_apps/usage_access/dream/home_launcher 모두 crash dialog ("設定 が停止しました" 4145B 동일)
- ❌ DuraSpeed `am start -n` exception (KR과 동일)
- 별 회차: JP 단말 cold reboot 후 STORAGE 직전까지 보수적 진행

### KR 신규 차기 모델 비교 자산 (batch #2)
1. **런처 옵션 2개** (`HOME_SETTINGS` → `DefaultAppActivity`) — `MIVE Home` / `간편 모드` (현재 default). 차기 모델에서 런처 선택지 변동 가능.
2. **BLUETOOTH_SETTINGS 통합** — `ConnectedDeviceDashboardActivity` (블루투스 + USB + 페어링 + 기기 충전). 단순 BluetoothSettings 아닌 hub 화면.
3. **OEM MobileNetworkSettings** — `mediatek.settings.network.MobileNetworkSettings` (MTK base). dump 거부 = view extraction 제한 (privacy/보안 시그널).
4. **carrier-specific app 노출** — usage_access list에 `모바일가드` / `원스토어` (SKT 사전 설치) — 차기 라인업/carrier 비교 포인트.

### KR 미진 (JP와 별개)
- NETWORK_OPERATOR dump 재시도 — screencap fallback 또는 dumpsys window 활용
- STORAGE / NOTIFICATION_LISTENER 대체 진입 경로
- DuraSpeed activity entry 검증

## Deep Link batch #2 — KR/JP 1:1 비교 (valid pair 6)

| activity | KR | JP | 비교 시그널 |
|---|---|---|---|
| WifiSettingsActivity | "4월 29일~5월 27일에 203MB 사용함" / 네트워크 1개 | KT_GiGA WiFi 다수 / 24.9KB (KR 12.7KB 대비 더 큼) | 같은 화면 — 노출 네트워크 환경 다름 |
| ConnectedDeviceDashboardActivity | 블루투스 + USB + 페어링 통합 | 동일 통합 hub | 1:1 매핑 |
| **mediatek.settings.network.MobileNetworkSettings** | **dump 거부 (view extraction X)** | **dump 성공** | 🔑 동일 OEM activity 단말별 동작 차이 |
| DataUsageSummaryActivity | 34.85MB (5/1~31) | **159MB** (같은 기간) | 데이터 사용 패턴 차이 (JP=자동화 테스트 사용) |
| SoundSettingsActivity | 5 slider (미디어/벨소리/알람/알림/통화) | 5 slider 1:1 | 완전 일치 |
| DisplaySettingsActivity | screen off **5초** / 83% | screen off **10秒** / 82% | 사용자 설정 차이 |

## Deep Link batch #2 핵심 발견 (추가)
1. **OEM `MobileNetworkSettings` view extraction 단말별 차이** — 동일 OEM activity인데 KR=거부 / JP=성공. uiautomator dump의 view server 응답이 build / locale / runtime 상태에 의존하는 시그널.
2. **JP 단말 Settings 영구 ANR 패턴** — STORAGE_SETTINGS action 미존재 시 Settings 앱 자체 crash. JP locale-specific 또는 build-specific 버그 가능성 (KR은 같은 action 미존재해도 다음 진입 정상).
3. **screen off timeout default 차이 추정** — KR=5초 / JP=10초 (사용자 설정 또는 OEM default).
4. **OEM DuraSpeed `am start -n` exception 양 단말 공통** — manifest export 제한.

## 산출물 위치
- KR: `THOR2_K - Settings/catalog/*.md` + `MENU_TREE.md`
- KR batch #2: `THOR2_K - Settings/catalog/d1_batch2_inventory.md` (Tier A 13 entries 통합)
- JP: `THOR2_J - Settings/catalog/jp_baseline_inventory.md` (batch #1만, batch #2 미달성)
- 비교: 본 문서
- raw xml: 양 폴더 `catalog/_raw_*.xml` (비커밋)
