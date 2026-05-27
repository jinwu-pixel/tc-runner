# Catalog Schema v0.2 (2026-05-27 pilot 결과 반영)

목적: THOR2 KR/JP pilot 결과를 catalog 형식으로 표준화. catalog MD는 hand-written 정본 — `scripts/menu_mapper.py`는 raw inventory 보조.

## 0. 변경 이력
- v0.1: 초안 (1 화면 1 entry 정의)
- **v0.2 (2026-05-27)**: pilot 결과 반영
  - Tier A/B/C 화면 단위 도입
  - fingerprint 의무 완화 (depth 0만)
  - labels 단순화 (전체 노드 → 표 형식)
  - entry_method / entry_result / dump_size / external_package / activity_aliases 신규 필드
  - DENYLIST 사용자 가드 통합 (`menu_mapper.py` 동기)
  - sanitize placeholder 표준화
  - Deep link 결과 / ANR-crash / dump refused / 외부 앱 / activity 동일 매핑 표준 정의
  - KR/JP multi-device 비교 schema (Tier C) 추가
  - DPAD focus_path 선택화 (depth 2 / hidden menu만 의무)

---

## 1. 화면 단위 (Tier 3종)

### Tier A — 단일 화면 entry
`catalog/<screen_id>.md`. 1 화면 1 entry. depth 0 / depth 1 핵심 / 단일 진입 자산.

**사용 예**: `settings_home_d15a7f0e.md`, `settings_d1_privacy.md`, `simplemode_home.md`

### Tier B — 통합 MD (batch / track 단위)
`catalog/<batch_name>_inventory.md`. 다수 화면 1 파일 묶음. 각 entry는 메타 표 + 라벨 표.

**사용 예**: `track3_hnlens_apps_inventory.md`, `d1_batch2_inventory.md`, `jp_baseline_inventory.md`

### Tier C — 비교 MD (multi-device / multi-version)
`<폴더 root>/COMPARISON_<X>_<Y>.md`. hand-written (자동 diff 미지원 — KR/JP 차이는 사람 해석).

**사용 예**: `THOR2_K - Settings/COMPARISON_KR_JP.md`

---

## 2. screen_id 명명

| depth | 형식 | fingerprint | 예시 |
|---|---|---|---|
| 0 (의무 fp) | `<pkg_alias>_<screen_name>_<fp8>` | 의무 | `settings_home_d15a7f0e` |
| 1+ (fp 선택) | `<pkg_alias>_<screen_short>` | 선택 | `settings_d1_privacy`, `settings_d1_device_info` |
| Tier B entry | `<pkg_alias>_<screen_short>` | 생략 | (메타 표만) |

> fingerprint = md5(`focus + sorted(text) + sorted(resource_id)`) 앞 8자.
> depth 0은 자산 식별성 위해 의무. depth 1+ 는 deep link action + activity name이 식별자 역할이라 선택.

---

## 3. 필드 (Tier A 기준)

### 필수
| 필드 | 값 | 비고 |
|---|---|---|
| `screen_id` | string | unique |
| `package` | string | `com.android.settings` 등 |
| `activity` | string | `dumpsys window | grep mCurrentFocus` 기반 |
| `entry_method` | enum | `deep_link` / `dpad+enter` / `monkey_launcher` / `am_start_n` / `manual` |
| `entry_result` | enum | `ok` / `action_missing` / `dump_refused` / `entry_exception` / `anr_crash` |
| `nav_from_parent` | string | 진입 동작 (action 명, DPAD 시퀀스 등) |
| `depth` | int | settings_home=0, SubSettings=1, ... |
| `raw_xml` | string | `catalog/_raw_*.xml` 상대경로 |
| `dump_size` | int | bytes (정상 vs ANR 4145B 구분 시그널) |
| `labels` | table | 화면 노출 라벨 표 (전체 노드 X) |

### 선택 / 상황별
| 필드 | 값 | 비고 |
|---|---|---|
| `capture_ts` | ISO8601 | 기록 시 |
| `parent_screen_id` | string \| null | 직전 화면 (root=null) |
| `fingerprint` | md5_8 | depth 0 의무 / depth 1+ 선택 |
| `viewport` | string | "480x800" |
| `risk_flags` | array | "DENYLIST 매치 항목" 명시 |
| `screenshot_path` | string | 검증용만 |
| `external_package` | bool | Settings 외부 앱 (Wellbeing 등) |
| `activity_aliases` | list | 동일 activity 매핑 시 (`APPLICATION_SETTINGS = MANAGE_APPLICATIONS_SETTINGS`) |
| `focus_path` | list (DPAD 시퀀스) | depth 2 / hidden menu 만 의무 |
| `notes` | string | 기타 발견 |

---

## 4. labels 단순화

v0.1의 `nodes` (전체 노드 attrib array) → **`labels` 표 (소수 라벨만)**:

```markdown
| label | 비고 |
|---|---|
| Wi-Fi | 제목 |
| 네트워크 환경설정 | depth 2 후보 |
| 마이크 액세스 | 🚫 toggle, 진입 X |
```

전체 노드 정보는 `raw_xml` (비커밋)에 보존. catalog MD는 사람 검토용 요약.

---

## 5. Deep link 결과 표준 표 (Tier B 통합 MD)

| # | action | 진입 | activity | size | result |
|---|---|---|---|---|---|
| 1 | WIFI_SETTINGS | ✅ | `Settings$WifiSettingsActivity` | 12.7KB | `ok` |
| 7 | STORAGE_SETTINGS | ❌ | (action 미존재) | — | `action_missing` |
| 3 | NETWORK_OPERATOR_SETTINGS | ⚠ | mediatek OEM | — | `dump_refused` |
| OEM | DuraSpeed `am start -n` | ❌ | exception | — | `entry_exception` |
| 8 | ACCESSIBILITY_SETTINGS (post-ANR) | ❌ | crash dialog | 4145B | `anr_crash` |

---

## 6. ANR / crash dialog 패턴

`dump_size`가 정확히 같은 값 (예: 4145B) = single ANR dialog signature.

| 필드 | 값 |
|---|---|
| `entry_result` | `anr_crash` |
| `dump_size` | 정확한 bytes (단말·locale 의존 signature) |
| 라벨 | locale 의존 — "設定 が停止しました" / "アプリを閉じる" / "アプリ情報" 또는 한국어 "설정이 중지되었습니다" 등 |
| 트리거 | 예: STORAGE_SETTINGS action 미존재 직후 Settings 영구 crash (JP-specific) |
| 복구 | `am force-stop com.android.settings` → 효과 없음 시 단말 cold reboot |

---

## 7. dump extraction 거부

uiautomator dump가 root node null 반환 → 파일 미생성 또는 작은 size:

| 필드 | 값 |
|---|---|
| `entry_result` | `dump_refused` |
| 추정 원인 | OEM activity view server 거부 (예: `mediatek.settings.network.MobileNetworkSettings` KR-side) |
| fallback (수동, 별 회차) | `adb shell screencap -p /sdcard/x.png` / `dumpsys window` / `cmd window dump-visible-window-views` |
| 비교 시그널 | 같은 OEM activity가 단말 A 거부 / 단말 B 성공 가능 (KR=거부 / JP=성공 사례) |

---

## 8. 외부 앱 entry

Settings home에서 진입했지만 다른 패키지일 때 (예: 디지털 웰빙 = `com.google.android.apps.wellbeing`):

| 필드 | 값 |
|---|---|
| `package` | `com.google.android.apps.wellbeing` |
| `external_package` | `true` |
| `nav_from_parent` | home "디지털 웰빙 및 자녀 보호 기능" → ENTER (deep link 미존재 시 `am start -n .../.settings.TopLevelSettingsActivity` fallback) |
| `entry_method` | `am_start_n` (deep link fallback) |

---

## 9. activity 동일 매핑 (`activity_aliases`)

서로 다른 deep link action이 같은 activity 진입할 때:

```markdown
- screen_id: settings_d1_application
- activity: com.android.settings.Settings$ManageApplicationsActivity
- activity_aliases:
  - "android.settings.APPLICATION_SETTINGS"
  - "android.settings.MANAGE_APPLICATIONS_SETTINGS"
```

별 entry 만들지 말고 동일 entry 안에 aliases 누적.

---

## 10. sanitize placeholder 표준

raw xml = 비커밋 (개인정보 노출 가능). **catalog MD에는 sanitize 의무**:

| placeholder | 의미 | 예시 raw → MD |
|---|---|---|
| `<device-serial>` / `<kr-serial>` / `<jp-serial>` | 단말 시리얼 | B06201249E0002B8 → `<kr-serial>` |
| `<phone-number>` | SIM 번호 / 전화번호 | 010-xxxx-xxxx → `<phone-number>` |
| `<weather-location>` | 날씨 위젯 위치명 | 정자동 → `<weather-location>` |
| `<wifi-network-N>` | WiFi SSID | KT_GiGA_2G_12F → `<wifi-network-1>` |
| `<user-installed-app-*>` | 사용자 설치 앱 | 니어메디 → `<user-installed-app-A>` |
| `<account-name>` | 사용자 계정명 | xxx@gmail.com → `<account-name>` |

sanitize 범위: catalog/*.md (Tier A/B), COMPARISON_*.md (Tier C). raw xml은 비커밋이라 sanitize 안 함.

---

## 11. multi-device 비교 schema (Tier C)

`COMPARISON_<X>_<Y>.md` 표준 섹션 5종:

1. **단말 baseline 차이** — serial / model / build / locale / SIM / product (placeholder 사용)
2. **depth 0 / 런처 노출 차이** — 위젯 / 앱 아이콘 / 노출 entries
3. **depth 1 1:1 비교 표** — activity / 라벨 / size / 시그널
4. **차기 모델 비교 자산 핵심 포인트** — 라인업·locale·OS·OEM 차이
5. (선택) **미진 / 별 회차 후보**

> 자동 diff 생성 X (hand-written). multi-device 차이는 사람 해석 영역.

---

## 12. DPAD focus_path 정책 (v0.2 — 선택)

- **생략 가능**: deep link / `am_start_n` / `monkey_launcher`로 안정 진입 가능 시
- **의무**: depth 2 / hidden menu 진입 (deep link 미존재) — DPAD 시퀀스 필수 기록

focus_path 표기 (필요 시):
```markdown
- focus_path:
  - HOME → DPAD DOWN×3 → DPAD RIGHT → ENTER
  - 진입 활동: <activity_name>
```

---

## 13. menu_mapper.py 관계

`scripts/menu_mapper.py`는 **raw inventory 보조 도구**:
- `inventory` 모드: 현재 화면 단발 dump (catalog 작성 전 빠른 라벨 확인)
- `dfs` 모드 + `--allow-tap`: 운영 가드 금지. `--i-understand-risk` opt-in 명시 필요 (v0.2 deprecation 경고)
- 출력 (`menu_tree_<ts>.{json,md}`): 도구 자체 형식 — catalog MD와 별개

catalog MD는 **hand-written 정본**. menu_mapper.py 출력을 그대로 catalog로 쓰지 않음.

---

## 14. DENYLIST (menu_mapper.py 정합, §2.3 source-of-truth)

v0.2 통합 DENYLIST — `scripts/menu_mapper.py` `DENYLIST` 와 양쪽 동기:

### 한국어
긴급 / 전화 / 메시지 / 초기화 / 삭제 / 허용 / 거부 / 결제 / 비밀번호 / 잠금 / 공장초기화 / 발신 / 발송 / 녹음 / 촬영 / 업데이트 / PIN

### 영어
reset / delete / emergency / call / message / permission / allow / deny / developer / factory / payment / uninstall / remove / clear data / update / OTA / record / capture / shutter / fota / force stop

### 일본어
緊急 / SOS / 発信 / 電話 / メッセージ送信 / 初期化 / リセット / 削除 / 消去 / 許可 / 拒否 / 保存 / 変更 / アカウント / パスワード / PIN / ロック / 開発者向け / 通話 / 通信 / 緊急通報 / アップデート / 録音

변경 시 양쪽 갱신 의무.

---

## 15. ALLOWLIST_PACKAGES (menu_mapper.py 정합)

v0.2 확장 list — `scripts/menu_mapper.py` `ALLOWLIST_PACKAGES` 와 동기:

- `com.android.settings`
- `com.hnlens.simplemode` (런처)
- `com.hnlens.calculator` / `com.hnlens.clock` / `com.hnlens.magnifying` / `com.hnlens.pedometer` / `com.hnlens.fmradio` / `com.hnlens.soundrecorder` / `com.hnlens.camera`
- `com.hnlens.lssys` / `com.hnlens.wallpaper` / `com.hnlens.lsoqc`
- `com.hnlens.contacts` (진입 가드는 별도 — DENYLIST)
- `com.google.android.apps.wellbeing` (외부, Settings 통합 entry)
- `com.google.android.permissioncontroller` (HOME_SETTINGS 라우팅)
- `com.mediatek.duraspeed` (OEM)

---

## 16. 미결정 (다음 회차)
- screencap fallback 자동화 (dump refused 시)
- ANR crash dialog 단말·locale별 signature 등록 (현재 hand-written 표기)
- 사용자 설치 앱 자동 분류 (carrier vs personal vs preinstalled — 현재 hand-written)
- depth 2 entry 진입 패턴 정형화 (DPAD fragment direct / shell `cmd` 활용)
- raw xml extraction 거부 시 alternative dump 방법 표준 명시
