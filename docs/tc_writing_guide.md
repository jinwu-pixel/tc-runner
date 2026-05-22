# TC 작성 가이드

TC Runner에서 실행 가능한 YAML 테스트케이스 작성 규칙.

---

## 1. 파일 구조

```yaml
name: "TC-XX_테스트명"
description: "한 줄 설명: 어떤 조건에서 어떤 결과를 확인하는지"
metadata:
  source: "출처 (엑셀, Jira 등)"
  priority: "필수 | 중요 | 권장"
  repeat: 1          # 반복 횟수 (선택)
steps:
  - action: ...
  - action: ...
```

### 필수 필드
- `name`: TC 고유 이름
- `steps`: 액션 리스트 (최소 1개)

### 선택 필드
- `description`, `metadata`: 리포트에 표시됨

---

## 2. 액션 레퍼런스

### 앱 제어

| 액션 | 필수 파라미터 | 선택 파라미터 | 설명 |
|------|-------------|-------------|------|
| `shell` | `command` | - | ADB shell 명령 실행 |
| `key` | `keycode` | - | 키 입력 (HOME, BACK, ENTER 등) |
| `wait` | `seconds` | - | 지정 시간 대기 |
| `input_text` | `text` | - | 텍스트 입력 (현재 포커스된 필드) |

```yaml
# 앱 강제종료 + 재시작
- action: shell
  command: "am force-stop com.example.app"
- action: wait
  seconds: 1
- action: shell
  command: "am start -n com.example.app/.MainActivity"
- action: wait
  seconds: 3

# 키 입력
- action: key
  keycode: BACK

# 텍스트 입력
- action: input_text
  text: "검색어"
```

### 탭/스와이프

| 액션 | 필수 파라미터 | 선택 파라미터 | 설명 |
|------|-------------|-------------|------|
| `tap_text` | `text` | - | 화면에서 텍스트를 찾아 탭 |
| `tap_id` | `id` | - | resource-id로 요소를 찾아 탭 |
| `tap_xy` | `x`, `y` | - | 좌표 직접 탭 |
| `swipe` | `x1`, `y1`, `x2`, `y2` | `duration` (기본 300ms) | 스와이프 |

```yaml
# 텍스트로 탭 (권장 - 해상도 독립적)
- action: tap_text
  text: "전체 감지 기록 보기"

# resource-id로 탭
- action: tap_id
  id: "com.example.app:id/btn_start"

# 좌표로 탭 (비추천 - 해상도 의존적)
- action: tap_xy
  x: 240
  y: 500

# 아래로 스크롤
- action: swipe
  x1: 240
  y1: 600
  x2: 240
  y2: 200
  duration: 300
```

### 검증 (실패 시 TC 중단)

| 액션 | 필수 파라미터 | 선택 파라미터 | 설명 |
|------|-------------|-------------|------|
| `verify_text` | `text` | - | 화면에 텍스트 존재 확인 |
| `verify_shell` | `command`, `expected` | `timeout` (기본 30s) | shell 출력에 문자열 포함 확인 |

```yaml
# UI 텍스트 확인
- action: verify_text
  text: "시니어쉴드"

# shell 출력 확인
- action: verify_shell
  command: "logcat -d | grep 'FATAL' || echo NO_CRASH"
  expected: "NO_CRASH"
  timeout: 30
```

> **중요**: `verify_text`는 **정확히 일치(exact match)** 합니다.
> - `"시니어쉴드"` -> 해당 text 속성이 정확히 "시니어쉴드"인 요소만 매칭
> - 여러 줄 텍스트, 부분 문자열은 매칭 안 됨
> - UI에 실제로 표시되는 텍스트를 `uiautomator dump`로 먼저 확인할 것

### 스크린샷

```yaml
- action: screenshot
  name: "TC01_02_결과화면"   # .png 자동 추가
```

### 수동 개입 (전화, 물리 조작 등)

```yaml
- action: manual_pause
  execution_mode: EXTERNAL_EVENT    # 또는 MANUAL_REQUIRED
  description: "보조폰으로 전화를 걸어주세요. 수신 후 10초 이상 통화한 뒤 종료하세요."
  manual_timeout: 120               # 초 단위 (기본 300)
```

> **수행 순서**: 안내 메시지 표시 -> **수동 작업 수행** -> `c` 입력 -> 다음 스텝 진행
>
> | 입력 | 동작 |
> |------|------|
> | `c` | 계속 (PASS) |
> | `s` | 건너뛰기 (사유 입력) |
> | `f` | 실패 처리 |

---

## 3. TC 유형별 작성 패턴

### 패턴 A: 자동 검증 (체크리스트형)

**적용 대상**: Wi-Fi TC, MMI 확인, 기본기능 OK/NG 체크리스트

엑셀에서 한 줄짜리 확인 항목을 자동화할 때 사용합니다.

```yaml
name: "CHK_WiFi_기본연결"
description: "Wi-Fi 연결/해제 기본 동작 확인"
metadata:
  source: "ODIN Wi-Fi TC / 항목 1~5"
  priority: 중요
steps:
  # --- Setup ---
  - action: shell
    command: "svc wifi enable"
  - action: wait
    seconds: 5

  # --- 체크 1: Wi-Fi ON 상태 확인 ---
  - action: verify_shell
    command: "dumpsys wifi | grep 'Wi-Fi is' || echo UNKNOWN"
    expected: "enabled"
  - action: screenshot
    name: "CHK_WIFI_01_enabled"

  # --- 체크 2: 연결된 SSID 확인 ---
  - action: verify_shell
    command: "dumpsys wifi | grep 'mWifiInfo' | head -1 || echo NONE"
    expected: "SSID"

  # --- 체크 3: Wi-Fi OFF ---
  - action: shell
    command: "svc wifi disable"
  - action: wait
    seconds: 3
  - action: verify_shell
    command: "dumpsys wifi | grep 'Wi-Fi is' || echo UNKNOWN"
    expected: "disabled"
  - action: screenshot
    name: "CHK_WIFI_02_disabled"

  # --- Cleanup ---
  - action: shell
    command: "svc wifi enable"
```

### 패턴 B: 절차형 (사전조건 → 절차 → 기대결과)

**적용 대상**: 스팸 차단 TC, 기능별 상세 테스트

엑셀의 "Pre-condition / Test procedure / Expected result" 구조를 그대로 매핑합니다.

```yaml
name: "SPAM_01_차단번호_SMS"
description: "수신차단 번호로부터 SMS 수신 시 차단 메시지함에 보관되는지 확인"
metadata:
  source: "ODIN 스팸 메시지번호 차단 TC / 항목 3"
  priority: 필수
steps:
  # --- Pre-condition: 수신차단 번호 등록 ---
  - action: shell
    command: "am start -a android.intent.action.MAIN -n com.android.messaging/.ui.ConversationListActivity"
  - action: wait
    seconds: 3
  - action: screenshot
    name: "SPAM01_01_precondition"

  # --- Test procedure ---
  - action: manual_pause
    execution_mode: MANUAL_REQUIRED
    description: "메시지 > 더보기 > 차단 및 스팸관리 > 차단된 번호에서 수신차단 번호를 추가하세요. 추가 후 해당 번호로 SMS를 발송하세요."
    manual_timeout: 180

  # --- Expected result: 차단 메시지함에 수신됨 ---
  - action: wait
    seconds: 5
  - action: screenshot
    name: "SPAM01_02_after"
  - action: manual_pause
    execution_mode: MANUAL_REQUIRED
    description: "차단된 메시지함에 SMS가 수신되었는지 확인하세요. 확인되면 [c], 미확인이면 [f]"
    manual_timeout: 60
```

### 패턴 C: 수동 작업 포함 (전화, 외부 이벤트)

**적용 대상**: 통화 감지, 전화 착/발신 확인

```yaml
name: "TC-XX_통화감지확인"
description: "10초 이상 통화 후 감지 이벤트 생성 확인"
steps:
  # --- Setup ---
  - action: shell
    command: "am force-stop com.example.app"
  - action: wait
    seconds: 1
  - action: shell
    command: "pm grant com.example.app android.permission.READ_PHONE_STATE"
  - action: shell
    command: "logcat -c"
  - action: shell
    command: "am start -n com.example.app/.MainActivity"
  - action: wait
    seconds: 3
  - action: verify_text
    text: "메인 화면 제목"
  - action: screenshot
    name: "TCXX_01_before"

  # --- 수동 작업 ---
  - action: manual_pause
    execution_mode: EXTERNAL_EVENT
    description: "보조폰으로 전화를 걸어주세요. 수신 후 10초 이상 통화한 뒤 종료하세요."
    manual_timeout: 120

  # --- 대기 (앱이 이벤트를 처리할 시간) ---
  - action: wait
    seconds: 5

  # --- 검증 ---
  - action: shell
    command: "am start -n com.example.app/.MainActivity"
  - action: wait
    seconds: 3
  - action: screenshot
    name: "TCXX_02_after"
  - action: verify_text
    text: "감지 결과 텍스트"
  - action: screenshot
    name: "TCXX_03_verified"
```

### 패턴 D: 메뉴트리 탐색

**적용 대상**: MENU TREE (TC3), Settings 전수 검증

계층적 화면을 DEPTH별로 순회하며 스크린샷을 남깁니다.

```yaml
name: "MENU_Settings_Display"
description: "설정 > 디스플레이 메뉴트리 전수 확인"
metadata:
  source: "ODIN MENU TREE (TC3) / Settings"
  priority: 중요
steps:
  # --- DEPTH 1: 설정 진입 ---
  - action: shell
    command: "am start -a android.settings.SETTINGS"
  - action: wait
    seconds: 3
  - action: verify_text
    text: "설정"
  - action: screenshot
    name: "MENU_SET_01_main"

  # --- DEPTH 2: 디스플레이 ---
  - action: tap_text
    text: "디스플레이"
  - action: wait
    seconds: 2
  - action: screenshot
    name: "MENU_SET_02_display"

  # --- DEPTH 3: 밝기 ---
  - action: tap_text
    text: "밝기 수준"
  - action: wait
    seconds: 2
  - action: screenshot
    name: "MENU_SET_03_brightness"
  - action: key
    keycode: BACK
  - action: wait
    seconds: 1

  # --- DEPTH 3: 글꼴 크기 ---
  - action: tap_text
    text: "글꼴 크기"
  - action: wait
    seconds: 2
  - action: screenshot
    name: "MENU_SET_04_fontsize"
  - action: key
    keycode: BACK
  - action: wait
    seconds: 1

  # --- 스크롤 후 추가 항목 ---
  - action: swipe
    x1: 240
    y1: 600
    x2: 240
    y2: 200
  - action: wait
    seconds: 1
  - action: screenshot
    name: "MENU_SET_05_scrolled"

  # --- 최종 복귀 ---
  - action: key
    keycode: HOME
```

### 패턴 E: 매트릭스/조합 테스트

**적용 대상**: 사업자간 Call Test, 재난문자 수신, Data ON/OFF 조합

동일한 절차를 조건만 바꿔 반복하는 경우, **조건별로 별도 YAML**을 만듭니다.

```yaml
# --- 파일: CALL_SKT_to_KT.yaml ---
name: "CALL_SKT_to_KT_음성통화"
description: "SKT → KT 음성 착/발신 5회 + long call 1회(1분 이상)"
metadata:
  source: "이동통신 사업자간 CallMessage Test / 행 5"
  priority: 필수
steps:
  - action: screenshot
    name: "CALL_SKT_KT_01_before"

  - action: manual_pause
    execution_mode: EXTERNAL_EVENT
    description: |
      SKT 단말에서 KT 단말로 음성 통화 테스트:
      1) 5회 착/발신 (각 10초 이상)
      2) 1회 long call (1분 이상)
      통화 품질, 끊김, 3G 천이 여부 확인
    manual_timeout: 600

  - action: screenshot
    name: "CALL_SKT_KT_02_after"

  # --- 통화 기록 확인 ---
  - action: shell
    command: "content query --uri content://call_log/calls --projection number:duration:type --where \"duration>0\" --sort-order \"date DESC\" | head -6"
  - action: screenshot
    name: "CALL_SKT_KT_03_calllog"
```

```yaml
# --- 파일: CALL_KT_to_SKT.yaml ---
name: "CALL_KT_to_SKT_음성통화"
description: "KT → SKT 음성 착/발신 5회 + long call 1회(1분 이상)"
# ... 동일 구조, description만 변경
```

### 패턴 F: 권한/상태 변경 테스트

**적용 대상**: 권한 부여/철회, Data ON/OFF, 비행기 모드 등

상태를 변경하고 복구해야 하는 TC에서는 **cleanup을 verify 앞에** 배치합니다.

```yaml
name: "TC-XX_권한테스트"
description: "권한 철회 상태에서 크래시 없음 확인"
steps:
  # --- Setup: 권한 철회 ---
  - action: shell
    command: "am force-stop com.example.app"
  - action: wait
    seconds: 1
  - action: shell
    command: "pm revoke com.example.app android.permission.READ_PHONE_STATE"
  - action: shell
    command: "logcat -c"
  - action: shell
    command: "am start -n com.example.app/.MainActivity"
  - action: wait
    seconds: 3

  # --- 수동 작업 ---
  - action: manual_pause
    execution_mode: EXTERNAL_EVENT
    description: "전화를 걸어주세요."
    manual_timeout: 120
  - action: wait
    seconds: 5

  # --- Cleanup 먼저! (verify 실패해도 권한 복구 보장) ---
  - action: shell
    command: "pm grant com.example.app android.permission.READ_PHONE_STATE"

  # --- 검증 ---
  - action: shell
    command: "am start -n com.example.app/.MainActivity"
  - action: wait
    seconds: 3
  - action: verify_text
    text: "메인 화면 제목"
  - action: verify_shell
    command: "logcat -d | grep 'AndroidRuntime.*FATAL' || echo NO_CRASH"
    expected: "NO_CRASH"
```

### 패턴 G: 증거 수집용 (수동 판정)

**적용 대상**: 자동 판정이 어려운 항목 (음질, UI 깨짐, 진동 등)

화면 캡처와 수동 판정을 조합합니다.

```yaml
name: "MAN_VoLTE_음질확인"
description: "VoLTE 통화 음질 및 스피커/뮤트/보류 기능 수동 확인"
metadata:
  source: "ODIN 기본기능TC / 항목 6 - VoLTE 착/발신"
  priority: 필수
steps:
  # --- Setup ---
  - action: screenshot
    name: "MAN_VOLTE_01_idle"

  # --- 통화 시작 ---
  - action: manual_pause
    execution_mode: EXTERNAL_EVENT
    description: |
      VoLTE 음성 통화 테스트:
      1) 보조폰으로 전화 걸기 → 수신 → 1분 이상 통화
      2) 통화 중 음소거 ON/OFF 확인
      3) 스피커 ON/OFF 확인
      4) 보류 → 보류해제 확인
      5) 3G 천이 없이 VoLTE 유지되는지 확인
      모든 확인 후 통화 종료
    manual_timeout: 300

  - action: wait
    seconds: 3
  - action: screenshot
    name: "MAN_VOLTE_02_after"

  # --- 통화 기록에서 VoLTE 확인 ---
  - action: shell
    command: "dumpsys telecom | grep -i 'volte\\|vowifi' | tail -5 || echo NO_INFO"
  - action: screenshot
    name: "MAN_VOLTE_03_telecom"

  # --- 수동 판정 ---
  - action: manual_pause
    execution_mode: MANUAL_REQUIRED
    description: "위 항목들이 모두 정상이었으면 [c], 이슈가 있었으면 [f]를 눌러주세요."
    manual_timeout: 60
```

---

## 4. 엑셀 → YAML 변환 가이드

### 체크리스트형 (Wi-Fi TC, MMI 확인)

| 엑셀 | YAML |
|------|------|
| `번호: 1` | `name: "CHK_WIFI_01"` |
| `검증 항목: T WiFi zone 연결` | `description: "..."` + `verify_shell` 또는 `manual_pause` |
| `OK / FAIL` | 자동: `verify_*` / 수동: `manual_pause`로 판정 |

**자동화 가능**: shell 명령으로 확인 가능한 항목 (Wi-Fi 상태, 연결 SSID 등)
**수동 판정 필요**: 화면 표시 품질, 물리 동작 (패턴 G 사용)

### 절차형 (스팸 차단 TC)

| 엑셀 컬럼 | YAML 매핑 |
|----------|----------|
| `Pre-condition` | Setup 블록 (`shell`, `tap_text` 등) |
| `Test procedure` | 액션 스텝 + `manual_pause` |
| `Expected result` | `verify_text` / `verify_shell` / `manual_pause`(수동 판정) |
| `비고 (BTS-XXXX)` | `metadata.source`에 기록 |

### 매트릭스형 (사업자간 Call Test)

행 × 열 조합마다 **별도 YAML 파일**로 분리합니다.

| 엑셀 | 파일 |
|------|------|
| SKT → KT, 5회 | `CALL_SKT_to_KT.yaml` |
| KT → SKT, 5회 | `CALL_KT_to_SKT.yaml` |
| SKT → LGU+, 5회 | `CALL_SKT_to_LGU.yaml` |

### 메뉴트리형 (MENU TREE TC3)

DEPTH 구조를 탭 → 스크린샷 → BACK 패턴으로 변환합니다.

| 엑셀 | YAML |
|------|------|
| `기능명: Settings` | 파일 단위 (`MENU_Settings.yaml`) |
| `DEPTH1: 디스플레이` | `tap_text` + `screenshot` |
| `DEPTH2: 밝기 수준` | `tap_text` + `screenshot` + `key: BACK` |
| `결과: PASS/FAIL` | `verify_text` 또는 수동 판정 |

---

## 5. 자동화 수준 판단 기준

| 수준 | 설명 | 사용 액션 | 예시 |
|------|------|----------|------|
| **완전 자동** | ADB만으로 실행+판정 | `shell`, `verify_text`, `verify_shell` | 앱 실행, 권한 변경, UI 텍스트 존재 |
| **반자동** | 실행은 자동, 외부 이벤트 필요 | `manual_pause` (EXTERNAL_EVENT) | 전화 착/발신, SIM 교체 |
| **수동 판정** | 스크린샷 수집 후 사람이 판단 | `manual_pause` (MANUAL_REQUIRED) + `screenshot` | 음질, UI 깨짐, 진동 강도 |
| **자동화 불가** | 물리적 조작만 가능 | TC 작성 불필요 | 하드웨어 외관 검사 |

**규칙**: 자동화할 수 없는 항목도 **스크린샷 수집 + 수동 판정** 형태로 TC를 만들면, 증거 기록과 리포트 통합이 가능합니다.

---

## 6. 주의사항

### verify 실패 = TC 즉시 중단

`verify_text` 또는 `verify_shell`이 실패하면 **해당 TC의 남은 스텝은 실행되지 않습니다.**

따라서:
- Cleanup(권한 복구 등)은 verify **앞에** 배치
- 가장 중요한 verify를 먼저, 보조 verify는 나중에

### 화면 전환 후 반드시 wait

앱 시작, 화면 이동 후에는 **`wait` 2~3초** 필요. UI 렌더링이 완료되어야 `verify_text`, `tap_text`가 동작합니다.

### tap_text vs verify_text 차이

| | `tap_text` | `verify_text` |
|---|---|---|
| 용도 | 텍스트 찾아서 탭 | 텍스트 존재 확인 |
| 실패 시 | TC 계속 진행 | **TC 즉시 중단** |
| 재시도 | 3회 자동 재시도 | 3회 자동 재시도 |

### 앱이 자동으로 화면 전환하는 경우

통화 감지 등으로 앱이 **경고 화면을 자동으로 띄우는 경우**, `am start`로 돌아와도 메인이 아닌 경고 화면이 표시됩니다.

```yaml
# 통화 후 경고 화면이 뜨는 앱의 검증 패턴
- action: wait
  seconds: 5
- action: shell
  command: "am start -n com.example.app/.MainActivity"
- action: wait
  seconds: 3
- action: verify_text
  text: "경고 화면 텍스트"       # 경고 화면에서 먼저 확인
- action: key
  keycode: BACK                  # 경고 닫기
- action: wait
  seconds: 2
- action: tap_text
  text: "기록 보기"              # 메인 화면 조작
```

### 각 TC는 자립적으로

이전 TC의 상태에 의존하지 마세요. 각 TC 시작 시:
- `am force-stop` 으로 앱 초기화
- 필요한 권한을 명시적으로 `pm grant` / `pm revoke`
- `logcat -c` 로 이전 로그 제거

### 스크린샷 네이밍

```
{TC번호}_{순번}_{설명}
```
예: `TC08_01_main_before`, `TC08_02_after_call`, `TC08_03_history`

---

## 7. UI 텍스트 확인 방법

TC 작성 전에 실제 앱의 UI 텍스트를 확인하세요:

```bash
adb shell uiautomator dump /sdcard/ui_dump.xml
adb shell cat /sdcard/ui_dump.xml
```

출력에서 `text="..."` 속성의 값이 `verify_text`에 사용할 정확한 문자열입니다.

---

## 8. 실행 방법

```bash
# 단일 TC
python -m src.cli run "exported_tc1/TC-01_권한미부여.yaml"

# 여러 TC
python -m src.cli run exported_tc1/TC-*.yaml

# 디렉토리 내 전체
python -m src.cli run "exported_tc1/*.yaml"

# 엑셀에서 직접 실행 (자동 변환)
python -m src.cli run tc_samples/TC_1.xlsx
```
