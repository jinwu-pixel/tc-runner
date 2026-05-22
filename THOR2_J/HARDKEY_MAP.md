# THOR2_J Hardkey Map (v0.6)

**대상 단말**: THOR2_J (AT-M140 thor2 / ALT brand)
**serial**: `B2700125BW000083`
**Android**: 14 (UP1A.231005.007), build `SELJY072603MZ0511`
**디스플레이**: 480x800 @ 220dpi, ja-JP locale
**작성 기준**: Figma `0_0_[THOR2-J] FocusRule v1.0.5` **전체 (45페이지)** — 0_1.x ~ 0_9.x 통합 + adb 실측 (2026-05-11). PDF 원본: `doc/0_0_[THOR2-J] FocusRule _v1.0.5.pdf` (16.8MB, working tree 보관)

---

## 1. 단말 입력 디바이스 인벤토리

`getevent -lp` 실측 결과:

| event | name | 역할 | 주요 KEY/SW |
|-------|------|------|------------|
| event0 | `gpio-keys` | 측면 GPIO | `KEY_F4` (SOS btn), `KEY_VOLUMEDOWN` |
| event1 | `mtk-pmic-keys` | 전원/볼륨 | `KEY_VOLUMEUP`, `KEY_POWER` |
| event2 | `chsc_cap_touch` | 정전식 터치스크린 | `BTN_TOUCH`, `ABS_X/Y` (480x800, multi-touch 5) |
| event3 | **`mtk-kpd`** | **전면 키패드 (메인)** | 0~9, *, #, F1~F3, UP/DOWN/LEFT/RIGHT, BACK, PHONE, HOMEPAGE, CAMERA, BACKSPACE, ENTER, APPSELECT, SLEEP, WAKEUP |
| event4 | `mt-snd-card Headset Jack` | 헤드셋 미디어 키 | KEY_PLAYPAUSE, KEY_VOLUMEUP/DOWN, KEY_VOICECOMMAND + SW_HEADPHONE_INSERT |

**중요**: `mtk-kpd` 단일 디바이스에 전면 키패드 모든 키가 매핑되어 있어 Figma 정의와 1:1 대응됩니다.

---

## 2. 폴더 상태 (Hall sensor) detection

`getprop` 실측 — hall sensor가 단말 property로 노출됨:

```bash
adb -s B2700125BW000083 shell "getprop sys.hls.hall.state"
# 현재 측정값: 0
# 0 또는 1 (실제 폴더 OPEN/CLOSED 매핑은 실측 시 확인 필요)
```

관련 feature flag:
- `sys.hls.f.LS_HALL_STATE` = `1` (hall sensor 기능 활성)
- `sys.hls.f.LS_HALL_AUTO_ANSWER_PHONE` = `1` (폴더 열기로 통화 받기)
- `sys.hls.f.LS_HALL_AUTO_END_PHONE` = `1` (폴더 닫기로 통화 종료)
- `sys.hls.f.LS_CHECK_RINGTONE_VALIDITY` = `1`

**실측 확인 필요**: 현재 0의 의미가 OPEN인지 CLOSED인지 (폴더를 열고/닫으며 값 변화 관찰)

---

## 3. Linux KEY ↔ Android KEYCODE ↔ Figma 정의 매핑

### 3-A. 전면 키패드 (mtk-kpd, 폴더 OPEN 시) — **물리 키 실측 확정 (2026-05-11)**

| 물리 키 (Figma) | Linux KEY | Android KEYCODE | 정수 | 확정 방법 |
|----------------|-----------|----------------|------|---------|
| Recent apps btn | `KEY_APPSELECT` | `KEYCODE_APP_SWITCH` | 187 | input keyevent → RecentsActivity 진입 |
| Home btn | `KEY_HOMEPAGE` | `KEYCODE_HOME` | 3 | 표준 |
| Back btn | `KEY_BACK` | `KEYCODE_BACK` | 4 | 표준 |
| **Contact shortcut btn** | **`KEY_F1`** ✅ | `KEYCODE_F1` | 131 | **getevent 실측 + `input keyevent CONTACTS`(207)로도 진입 가능** |
| **Message shortcut btn** | **`KEY_F2`** ✅ | `KEYCODE_F2` | 132 | getevent 실측 + input keyevent F2 → MMS 진입 |
| **Favorite shortcut btn** | **`KEY_F3`** ✅ | `KEYCODE_F3` | 133 | getevent 실측 + input keyevent F3 → ShortcutEditActivity |
| Camera shortcut btn | `KEY_CAMERA` | `KEYCODE_CAMERA` | 27 | input keyevent → 벤더 camera 진입 |
| Call btn | `KEY_PHONE` | `KEYCODE_CALL` | 5 | input keyevent → AOSP dialer 진입 |
| Num. 0 | `KEY_0` | `KEYCODE_0` | 7 | 표준 |
| Num. 1~9 | `KEY_1` ~ `KEY_9` | `KEYCODE_1` ~ `KEYCODE_9` | 8 ~ 16 | 표준 |
| `*` btn | `KEY_NUMERIC_STAR` | `KEYCODE_STAR` | 17 | 표준 |
| `#` btn | `KEY_NUMERIC_POUND` | `KEYCODE_POUND` | 18 | 표준 |
| Clear btn (クリア) | `KEY_BACKSPACE` | `KEYCODE_DEL` | 67 | 표준 |
| **OK/Select (DPAD center)** | **`KEY_ENTER`** ✅ | `KEYCODE_ENTER` | 66 | getevent 실측. UI focus context에선 `KEYCODE_DPAD_CENTER` (23) 사용도 권고 |
| 방향 UP | `KEY_UP` | `KEYCODE_DPAD_UP` | 19 | 표준 |
| 방향 DOWN | `KEY_DOWN` | `KEYCODE_DPAD_DOWN` | 20 | 표준 |
| 방향 LEFT | `KEY_LEFT` | `KEYCODE_DPAD_LEFT` | 21 | 표준 |
| 방향 RIGHT | `KEY_RIGHT` | `KEYCODE_DPAD_RIGHT` | 22 | 표준 |
| (wake/sleep) | `KEY_WAKEUP` / `KEY_SLEEP` | `KEYCODE_WAKEUP` / `KEYCODE_SLEEP` | 224 / 223 | mtk-kpd 등록되어 있으나 물리 매핑 키 없음. 보조 |

### 3-B. 측면 키 — **물리 키 실측 확정 (2026-05-11)**

| 물리 키 (Figma) | event | Linux KEY | Android KEYCODE | 정수 | 확정 방법 |
|----------------|-------|-----------|----------------|------|---------|
| SOS btn | event0 (gpio-keys) | `KEY_F4` ✅ | `KEYCODE_F4` | 134 | getevent 실측 |
| Side Volume Up | event1 (mtk-pmic-keys) | `KEY_VOLUMEUP` | `KEYCODE_VOLUME_UP` | 24 | 표준 |
| Side Volume Down | event0 (gpio-keys) | `KEY_VOLUMEDOWN` | `KEYCODE_VOLUME_DOWN` | 25 | 표준 |
| **End btn = 측면 Power** | event1 (mtk-pmic-keys) | `KEY_POWER` ✅ | `KEYCODE_POWER` | 26 | **getevent 실측. 단말은 전면에 별도 End 키 없음. 측면 Power 키가 Figma End btn 역할** |

### 3-C. vendor key handler 패턴 (자동화 영향) — v0.4 자동 시험 결과 확장

다음 항목은 **`input keyevent` 시뮬로 동작 안 됨** (vendor hook 전용). 자동화 시 우회 또는 사용자 협력 필요:

| 항목 | input keyevent 결과 | 우회 방법 |
|------|-------------------|---------|
| **물리 F1 (Contact)** | focus null, 진입 안 됨 | `KEYCODE_CONTACTS` (207) 발사 → `com.hnlens.contacts` 진입 ✅ |
| **물리 POWER short press** | mWakefulness 변화 없음 (Awake 유지) | `KEYCODE_SLEEP` (223) 발사 → 단말 sleep ✅ |
| **물리 Vol Down Long press** | ringer mode 변화 없음, audio dump 영향 없음 | 우회 없음 — 사용자 협력 필요 |
| **물리 F2 IME 모드 cycle** | mCurSubtypeId 변화 없음 | 우회 없음 — 사용자 협력 또는 IME 직접 API |
| **물리 0~9 Long press (Quick dial)** | 정상 dialer 진입만, 미등록 안내 안 뜸 | 우회 없음 — 사용자 협력 |
| **물리 * Long press (진동 모드)** | 미검증 (자동 시뮬 안 됨 추정) | 사용자 협력 |
| **물리 # Long press (터치 잠금)** | 미검증 | 사용자 협력 |

**vendor hook 안 거치고 input keyevent로 동작하는 키**:
- F2 short / F3 short (default app 진입은 OK, IME 컨텍스트 동작은 hook)
- CAMERA / CALL / APP_SWITCH / CONTACTS (207) / SYSRQ (120, 스크린샷)
- DPAD (UP/DOWN/LEFT/RIGHT/CENTER)
- 숫자 0~9 short / * / # short / BACK / HOME / BACKSPACE / ENTER
- SLEEP (223) / WAKEUP (224)

**자동화 운영 표준 — 우회 명령 표 (v0.5 확장)**:

| Figma 트리거 | 자동화 우회 명령 | 검증 방법 |
|------------|--------------|---------|
| End btn = 측면 Power | `input keyevent SLEEP` (223) | mWakefulness=Asleep |
| Contact 진입 | `input keyevent CONTACTS` (207) | mCurrentFocus = com.hnlens.contacts |
| 스크린샷 (End + Vol Down) | `input keyevent 120` (SYSRQ) | /sdcard/Pictures/Screenshots/ 새 파일 |
| **Home short press from home → Quick Panel** | **`cmd statusbar expand-notifications`** | mCurrentFocus = NotificationShade |
| Quick Panel 닫기 | `cmd statusbar collapse` | — |
| **End Long press → Power Pop-up** | **`input keyevent --longpress KEYCODE_POWER`** ✅ (system 처리, vendor hook 안 거침) | mCurrentFocus = ActionsDialog, 라벨 緊急通報/電源を切る/再起動 |

**자동화 영역 X (TC `manual_detail`로 분리)**:
- IME 모드 cycle (F2 Long/Short — vendor hook 또는 IME app 내부)
- Vol Down Long → 진동 모드 진입
- 0~9 Long → Quick dial 발신 (등록/미등록 분기)
- * Long → 진동 토글 / # Long → 터치 잠금
- DPAD Long → Fast Scroll (vendor hook 추정)
- Lock screen 잠금 해제 분기 (PIN 등록 후만 의미 있음)

---

## 4. Figma 룰 ↔ KEYCODE 결합 (Frame별)

### 4-A. Frame 0_1.1.1 — Default App Mapping

**원칙**: Hardware key (Call / Message / Contacts / Camera) 입력 → **default app 라우팅**
- 기본: System preloaded app = default
- 사용자가 Downloaded app으로 변경 가능

**THOR2_J 단말의 default 확정 (`cmd role get-role-holders` 2026-05-11 실측)**:

| Role | Default app | 진입 시 Activity |
|------|------------|----------------|
| `DIALER` | `com.android.dialer` (AOSP) | `.main.impl.MainActivity` |
| `SMS` | `com.android.mms` (AOSP) | `.ui.ConversationList` |
| **`HOME` (launcher)** | **`com.hnlens.simplemode`** (벤더) | `.ui.home.MainActivity` |
| `BROWSER` | `com.android.chrome` | — |
| `ASSISTANT` | `com.google.android.apps.searchlite` | `.SelectAccountActivity` (KEYCODE_ASSIST=219 발사 시) |
| `SYSTEM_GALLERY` | `com.google.android.apps.photosgo` | — |
| `EMERGENCY` | `com.google.android.apps.safetyhub` | — |
| Contacts (role 미정의, KEYCODE_CONTACTS 매핑) | **`com.hnlens.contacts`** (벤더) | `com.android.contacts.activities.PeopleActivity` |
| Camera (KEYCODE_CAMERA 매핑) | **`com.hnlens.camera`** (벤더) | `com.mediatek.camera.CameraLauncher` |
| Recent apps (KEYCODE_APP_SWITCH 매핑) | **`com.hnlens.launcher3`** (벤더) | `com.android.quickstep.RecentsActivity` |

### 4-B. Frame 0_1.1 — 폴더 닫힌 상태 / 측면 키

| 키 | 컨텍스트 | 동작 | KEYCODE |
|----|---------|------|--------|
| SOS btn (CLOSED, 외부) | 1회 short | Wake up → Sub LCD 화면 전환 | F4 |
| SOS btn (CLOSED, 외부) | Long ≥5s | Style folder SOS (보호자 위치 알림) | F4 (long) |
| Side Volume Up | idle | Volume up | VOLUME_UP |
| Side Volume Up | sound playing | Playing 중 볼륨 up | VOLUME_UP |
| Side Volume Down | idle | Volume down | VOLUME_DOWN |
| Side Volume Down | sound playing | Playing 중 볼륨 down | VOLUME_DOWN |

**폴더 상태 분기 검증**:
```bash
adb shell getprop sys.hls.hall.state
# CLOSED 시 단말 메인 LCD off, Sub LCD 상태 — adb dump 불가능 영역
```

### 4-C. Frame 0_1.2 — 폴더 열린 상태 / 전면 키패드

(Figma 원본 그대로 + KEYCODE 추가, ja-JP IME 컨텍스트 분기 포함)

| 키 | KEYCODE | Short press | Long press |
|----|--------|-------------|-----------|
| Recent apps | APP_SWITCH | 최근 앱 활성화 | - |
| Home | HOME | 홈 화면 | - |
| Back | BACK | 이전 화면 | - |
| Contact shortcut | F1 | default Contact app 진입 | - |
| Message shortcut | F2 | **텍스트 입력 중**: IME 모드 전환 (漢字→English→Number) / **그 외**: default Message app | - |
| Camera shortcut | CAMERA | default Camera app | - |
| Favorite shortcut | F3 | **텍스트 입력 중**: 기호 입력 모드 (記号) / **그 외**: Favorite app | - |
| Call btn | CALL | default Call app / 발신 | - |
| End btn | SLEEP (추정) | 통화 중: 통화 종료 / 앱 실행 중: Home 복귀 | **Power on/off pop-up** ⚠️ |
| Num. 0~9 | 0~9 | Dialer 진입 + Hiragana/Symbol/Number 입력 | Quick dialer 단축번호 발신 |
| `*` btn | STAR | **텍스트 입력 중**: ゛/゜ 추가 (か/さ/た/は행) · 문장 끝 줄바꿈 · 대/소문자 토글 / **Dialer**: `*` | 진동 모드 ON/OFF |
| `#` btn | POUND | **텍스트 입력 중**: 、 。 ?! 입력 / **Dialer**: `#` | 터치스크린 잠금/해제 |

**⚠️ TC 작성 시 주의 — End 키 long press**: Power off popup 등장. cleanup 누락 시 단말 종료 위험. End long press 사용 TC는 반드시 `KEYCODE_BACK` 또는 popup dismiss step 포함.

### 4-D. Frame 0_1.1.2 — Downloaded app default 시 Toast 정책

| 케이스 | 트리거 | 동작 |
|--------|--------|------|
| Case 1 — default 설정 직후 | `Settings > App > Default app` 에서 Downloaded app(예: Downloaded Call app)을 default로 지정 | Toast `"Some hardware key functions may not be supported by downloaded apps."` 설정 완료 직후 **1회** |
| Case 2 — Downloaded Call app 사용 중 Number 키 입력 | Downloaded app이 default 상태 + Number 하드키 입력 | 동일 Toast. **반복 입력 시 2초당 1회** throttle |

**TC 검증 포인트**:
- Toast 위치: Lockscreen 영역 기준 (AOSP popup 아닌 custom toast)
- detection 자동화: `dumpsys notification` 으로는 안 됨 (Toast는 SystemUI overlay). `uiautomator dump` 시 화면 잡기 어려움 — `logcat | grep -i toast` 또는 `dumpsys window | grep Toast` 시도

### 4-E. Frame 0_1.4 — 4-way Navigation + OK 키 컨텍스트 매트릭스

| 상황 \ 키 | Up | Down | Left | Right | OK |
|----------|----|------|------|-------|-----|
| **focus 없음** (focus starting point 없을 때) | Wake up focus | Wake up focus | Wake up focus | Wake up focus | Wake up focus |
| **Short press (normal)** | focus 위 | focus 아래 | focus 왼쪽 | focus 오른쪽 | 선택 확정 (앱/시스템 진입) |
| **Long press (normal)** | focus 위로 빠른 이동 | 아래 빠름 | 왼쪽 빠름 | 오른쪽 빠름 | long tap 동일 |
| **텍스트 입력 중** | cursor 위 | • 예측 변환 단어 선택 / • cursor 아래 | cursor 왼쪽 | cursor 오른쪽 | • 입력 중 확정 / • 예측 변환 단어 list에서 선택 |

**추가 룰**:
- focus 활성화 트리거: 4-way + OK 중 어느 키든 누르면 focus starting point 노출 (5개 모두 wake-focus 역할)
- 텍스트 입력 컨텍스트는 IME shown 여부로 detection (`dumpsys input_method | grep mInputShown=true`)
- **DPAD_DOWN 동작 분기**: 일반 = focus 아래 / 텍스트 입력 + 예측 단어 list 표시 중 = 단어 선택 (1차 동작) → 이후 cursor 아래

### 4-F. Frame 0_1.5 — Lock screen 에서 Volume 흐름

| Step | 트리거 | 결과 |
|------|--------|------|
| 1 | Lock screen에서 Volume Up Press | Volume control bar **appears** + Vol up 1단계 |
| 2 | 이어 Vol Up Press | 단계 증가 |
| 3 | Vol Down Press | Bar appears + Vol down 1단계 |
| 4 | 이어 Vol Down Press | 단계 감소 |
| 5 (Dismiss) | **Back / Cancel(クリア) Press** 또는 **3초 무입력** | Bar **disappears**, Lock screen 화면 **유지** (잠금 해제 안 됨) |

### 4-G. Frame 0_1.6 — Normal 화면 Volume Up 흐름

| Step | 트리거 | 결과 |
|------|--------|------|
| 1 | Normal 화면에서 Volume Up Press | Bar appears + Vol up |
| 2 | DPAD Up Press | Bar 내부 indicator 위로 이동 (단계 ↑) |
| 3 | OK Press | 현재 값 **확정** |
| 4 | 이어 DPAD Up Press | 추가 단계 증가 |
| 5 (Dismiss) | Back/Cancel 또는 3초 무입력 | Bar disappears |
| 추가 | DPAD Down Press | Vol down 단계 |

**앱 실행 중 규칙**: Bar dismiss 시 **bar만 사라지고 앱 화면(하단 shortcut icon 포함)은 유지**

### 4-H. Frame 0_1.7 — Normal 화면 Volume Down 흐름

0_1.6 미러 (Vol Down 시작):
- Vol Down Press → Bar appears + 감소
- DPAD Down → bar indicator 아래 / DPAD Up → 증가 / OK → 확정
- Dismiss = Back/Cancel/3초 무입력 (앱 실행 중에는 bar만)

### 4-I. Frame 0_1.8 — Volume Long Press

| 트리거 | 결과 |
|--------|------|
| **Volume Up Long Press** | Volume Up to **최대** (즉시 max) |
| **Volume Down Long Press** | Volume Down to 최소 후 **진동 모드 진입** |

두 동작 모두 Bar 표시 중. Bar는 일반 dismiss 룰 (Back/Cancel/3초).

**detection**:
- 최대 볼륨: `dumpsys audio | grep -E "STREAM_RING|STREAM_MUSIC" | grep -i max`
- 진동 모드: `settings get global zen_mode` 또는 `cmd notification get_zen_mode` 또는 `media_volume_zen_mode`

### 4-J. 특수 조합 — 스크린샷

**End btn + Volume Down btn 동시 누름 → 스크린샷 캡처**

- End = KEYCODE_POWER (측면)
- Volume Down = event0 gpio-keys
- 자동화: `input keyevent --longpress 26 25` (multiple keycode 동시 발사) — 단 동시성 보장 어려움. `adb shell screencap` 으로 대체 가능 (테스트 시)

### 4-L. Frame 0_2.1 — Lock screen 해제

| 시작 상태 | 트리거 | 결과 |
|----------|--------|------|
| Folder open + Lock screen | Any hard key Press **(end / back / erase·cancel / camera / num 제외)** | "Enter your PIN" 입력 화면 표시 |
| Folder open + Lock screen | **Num hard key Press** | PIN 입력 화면 진입 + **첫 자리에 해당 숫자 자동 입력** |
| PIN 입력 화면 | Num hard key 계속 누름 | 입력 숫자 누적 (`・ ・ ・ 1`) |
| PIN 입력 화면 | **OK Press** | PIN 검증 → 일치 시 Home, 불일치 시 "올바르지 않은 PIN입니다." |

**0_2.2 (Deleted definition)**: 키패드 입력만으로 잠금 해제. 별도 룰 없음 (0_2.1 적용)

### 4-M. Frame 0_2.3 / 0_2.6 — Home Focus 기본 + Normal mode Navigation

| 트리거 | Simple mode Home | Normal mode Home |
|--------|----------------|----------------|
| 무 focus + Any Direction/OK | Focus 활성화 (starting point) | Focus 활성화 (좌상단 App부터) |
| Up at top edge | **Stop, No looping** | Stop, No looping |
| Down | 다음 행 | 인접 App |
| Left/Right at edge | Stop | Stop |
| 비고 | Weather widget deleted | search bar ↔ first app 간 looping 미지원 (Android system 이슈) |

**Navigation 기본 원칙** (0_2.4): Focus 항상 **좌상단 시작** (앱별 예외 가능). 상하 = Android adjacent-object 원칙.

### 4-N. Frame 0_2.7 — Home short press → Quick Panel **(Thor 2 변경 사항)**

⚠️ **중요**: 기존 KEYCODE_HOME 매핑이 **컨텍스트 분기 추가**

| 트리거 | 동작 |
|--------|------|
| Home 화면에서 Any Direction/OK | Focus 활성화 (Call/Message/Camera 아이콘부터) |
| Home 화면에서 **Home btn Press** *(Thor 1 = Long press, Thor 2 = **Short Press**로 변경)* | **Quick Panel opens** |
| Quick Panel 노출 상태 + Home btn Press | Quick Panel closes (Home 복귀) |
| Quick Panel 노출 상태 + Back/Cancel(クリア) | Quick Panel closes |
| Up Press | 위쪽 항목 focus 이동 |

**Thor 1 → Thor 2 차이**: Thor 1은 Long press home = Google Assistant. **Thor 2는 Short press home (Home 화면 안에서) = Quick Panel. Google Assistant 미사용**.

### 4-O. Frame 0_2.8 — Quick Panel 1 depth

표시 항목: Wi-Fi / Bluetooth / Mobile data / Sound mode + "Open∨" + 알림 영역 + Manage / Clear all

| 트리거 | 동작 |
|--------|------|
| Right | 같은 행 우측 (Wi-Fi → Bluetooth, Mobile data → Sound mode) |
| Down | 다음 행 (Wi-Fi → Mobile data, Bluetooth → Sound mode → Open∨ → 알림 → Manage/Clear all) |
| Right → Down 조합 | 모든 토글·"Open∨"·알림·Manage·Clear all 순회 |

### 4-P. Frame 0_2.9 — Quick Panel 2 depth

1 depth "Open∨" focus → OK → 2 depth 진입. 표시: Wi-Fi / Bluetooth / Mobile data / Sound mode / Airplane mode / Flashlight 6 토글 + 페이지 인디케이터(•○) + Edit / Power off / Settings (두 번째 페이지)

| 트리거 | 동작 |
|--------|------|
| 1 depth "Open∨" focus + OK | 2 depth 열림 |
| 2 depth + Back/Cancel(クリア) | 1 depth 복귀 |
| 1 depth + Back/Cancel(クリア) | Quick Panel closed |
| 2 depth + 페이지 인디케이터 따라 좌우 | 두 번째 페이지 (Edit/Power off/Settings) |

### 4-Q. Frame 0_3.1 — Power Pop-up (End Long Press)

| 트리거 | 결과 |
|--------|------|
| Anyscreen + **End btn Long Press** | Power pop-up: emergency call / power off / Restart 3 버튼 |
| Pop-up 진입 시 focus | **emergency call** (좌상단) |
| Right | emergency call → power off |
| Down | power off → Restart |
| Up | Restart → power off |
| Left | **No change** (좌측 이동 무동작) |

### 4-R. Frame 0_3.2 ~ 0_3.5 — List Navigation 4 케이스

| Case | 화면 예 | Top bar 좌우 이동 | Up/Down |
|------|--------|----------------|---------|
| **Case 1** (0_3.2) | Messages (검색 / More⋮) | Right 끝에서 추가 Right = **이동 없음**, Left 끝에서도 동일 | 리스트 항목 간 이동 |
| **Case 2** (0_3.3) | Contacts (≡ / + / 🔍) | ≡ → + → 🔍 순서, 끝에서 stop | 자모 인덱스 + 연락처 항목 |
| **Case 3** (0_3.4) | 앱 최초 진입 | Profile(사진) 영역 **focus 미지원** | 다음 리스트 항목 전체 영역 |
| **Case 4** (0_3.5) | Messages + "+メッセージ作成" 버튼 + 검색 | Right로 검색 → More⋮ 이동 | Up = "+ 메시지 작성" → 검색 / Down = 첫 메시지 |

**공통 룰** (Case 3): 앱 최초 진입 시 focus는 **첫 리스트 항목 전체 영역**. Left/Right로는 항목 내 서브로 안 가고 하단 탭바(즐겨찾기/최근/연락처/다이얼)로 이동.

### 4-S. Frame 0_3.6 — Fast Scroll (Up/Down Long Press, 전 화면 공통)

| 트리거 | 결과 |
|--------|------|
| **Up btn Long Press** | 현재 zone 위쪽 빠른 스크롤 → 최상단 도달 후 **stop** |
| **Down btn Long Press** | 현재 zone 아래쪽 빠른 스크롤 → 마지막 도달 후 **stop** |
| 리스트 최상단 + Up Short Press | 위쪽 인접 항목/툴바로 move upward |
| Home 마지막 행 + Down Short Press | **App drawer 진입** |
| Simple home에서도 동일 | — |

→ **전 화면 공통** (Home / List / 앱 내부 모두)

### 4-T. Frame 0_4.1 / 4.2 — Search

| 화면 | 동작 |
|------|------|
| 검색 진입 시 (focus 없음) | Any Direction / OK → focus 활성화 (검색 input 또는 결과 list 첫 항목) |
| 검색 입력 후 | Right/Left = cursor 이동, Down = 결과 list, OK = 검색 실행 |
| 결과 list | Up/Down = 항목 이동, OK = 항목 진입, Back/Cancel = 검색 화면 종료 |

### 4-U. Frame 0_4.3 — More menu (메시지/연락처 ⋮)

| 트리거 | 동작 |
|--------|------|
| 리스트 화면 + OK (More⋮ focus) | More menu 펼침 (예: 삭제 / 모두 읽음으로 표시 / 차단 및 스팸 / 휴지통 / 설정) |
| More menu + Down | 다음 항목 focus |
| More menu + Back / Cancel(クリア) | More menu 닫음 |

### 4-V. Frame 0_5.1 / 5.2 / 5.3 — Multi-selection (리스트 다중 선택)

| 트리거 | 동작 |
|--------|------|
| 리스트 항목 focus + **Long press OK** | **다중 선택 모드 진입**, "1 Selected" 표시 |
| 다중 선택 모드 + 항목 focus + OK | 항목 추가/해제 ("N Selected" 갱신) |
| 다중 선택 모드 + "Select all" focus + OK | 전체 선택 (5 Selected) |
| 5 Selected + "Deselect all" focus + OK | 전체 해제 (0 Selected) |
| 다중 선택 모드 + Back/Cancel | 다중 선택 모드 종료 |

**자동화 한계**: A-2 자동 검증 시 MMS list 비어있어 미검증. 데이터 있는 list (연락처 / 통화 기록) 또는 메시지 추가 후 재검증 필요.

### 4-W. Frame 0_5.4 — Toggle (depth 없음 / 있음)

- depth 없는 토글: OK 누르면 토글 ON/OFF (예: 알림 활성/비활성)
- depth 있는 토글: OK 누르면 sub-menu 진입 → 항목 선택 후 OK 확정 → Back으로 복귀

### 4-X. Frame 0_5.5 — Filter (예: 통화 목록 필터)

| 트리거 | 동작 |
|--------|------|
| 필터 화면 진입 + Any Direction/OK | focus 활성화 |
| 필터 항목 (모든 통화 / 수신 / 발신 / 부재중) + OK | 선택 + 필터 적용 |
| Back/Cancel | 필터 닫음 |

### 4-Y. Frame 0_5.6 — Tab (Tab 1~4 화면)

| 트리거 | 동작 |
|--------|------|
| Right edge에서 Right | 다음 tab으로 focus 이동 (Tab 1 → Tab 2 → Tab 3 → Tab 4) |
| Left edge에서 Left | 이전 tab으로 |
| Tab 4(마지막)에서 Right | **Stop, No loop** |

### 4-Z. Frame 0_6.x — Popup focus 룰

| Popup 유형 | 기본 focus | 비고 |
|----------|----------|------|
| Basic popup (확인 메시지) | **OK** | |
| **Delete popup** | **Cancel** | ⚠️ 실수 방지 — 삭제 popup은 기본 focus가 Cancel |
| Input popup (단순) | Down → Label, Right/Up = 취소/확인 (좌상단·우상단) |  |
| Input popup 2 (입력 영역 중심) | Down → Hi(입력), Right = 취소/확인 |  |
| Item list popup | Down → Item, 취소 |  |
| Radio button popup | Down → Item / Right = 취소/확인 / OK = 선택 |  |

### 4-AA. Frame 0_7.x — **Favorite button** (F3 Long Press 1초)

**Figma 정의 (v1.0.4 modified, Long press duration)**:

| Case | 조건 | 동작 |
|------|------|------|
| **Case 1** | 등록된 app 있음 | **Short Press = 등록앱 바로 실행 (어디서든)** / Long Press 1초 = popup |
| Case 1 popup | 등록 있음 | Title=**お気に入り (즐겨찾기)** / content=등록앱 아이콘+이름 / button=**変更 (변경)** / toast=**`즐겨찾기 버튼에 App6을(를) 등록하였습니다`** |
| **Case 2** | 등록 없음 | **Short OR Long Press = 동일 — popup 표시** |
| Case 2 popup | 등록 없음 | Title=**お気に入り** / content=**`お気に入りにアプリが登録されていません`** (등록 없음 안내) / button=**`キャンセル` / `登録`** |

**자동 검증 (A-3 PASS) 2026-05-11**:
- 현재 단말은 Case 2 (등록 없음) 상태
- `input keyevent F3` (short) OR `--longpress F3` 둘 다 → `com.hnlens.simplemode/.ui.shortcutbutton.ShortcutEditActivity` 진입
- 캡처 라벨: **お気に入り** / **お気に入りにアプリが登録されていません。** / **キャンセル** / **登録** (Figma 정의 정확히 일치 ✅)
- popup이 별도 Activity로 구현됨 (Dialog 아니라 Activity)

### 4-AB. Frame 0_8.1 / 8.2 — Touch screen lock (`#` Long Press)

| 트리거 | 동작 |
|--------|------|
| **`#` Long Press** (정상 상태) | 확인 popup: **`화면 터치 잠금 시, 물리 키패드로만 입력 및 선택 가능하며, 일부 앱에서는 기능이 제한 될 수 있습니다. 잠금 설정하시겠습니까?`** / Cancel/OK |
| 확인 popup + OK | 터치 잠금 ON, indicator에 lock icon, toast: **`화면 터치 잠금 상태입니다. 잠금을 해제하려면 [#]을 길게 누르세요.`** |
| 잠금 ON 상태 + 화면 터치 시 | popup: **`화면 터치 잠금 상태입니다. 잠금을 해제하려면 [#]을 길게 누르세요.`** 반복 |
| **`#` Long Press** (잠금 ON) | 해제 popup: **`화면 터치 잠금을 해제하시겠습니까?`** + Cancel/OK |
| 해제 popup + OK | 터치 잠금 OFF, toast: **`화면 터치 잠금이 해제되었습니다. 잠금을 다시 설정하려면 [#]을 길게 누르세요.`** |
| **재부팅** | 터치 잠금 ON 상태 **유지** (0_8.2) |

**자동 검증 결과 (A-1 FAIL)**: `input keyevent --longpress KEYCODE_POUND` → vendor hook 안 거치고 dialer로 단순 `#` 입력. **자동화 불가 — 물리 # 키 long press 사용자 협력 필요** (U-8 LOW → MEDIUM 승격)

### 4-AC. Frame 0_9.x — Input box

| 화면 | 동작 |
|------|------|
| Input box focus | Right/Left = **cursor 이동** (다른 화면의 navigation과 다름) |
| Input box + Down | 다음 항목 focus (예: 검색 결과 첫 항목) |
| Input box + Up | 이전 focus 또는 머무름 |
| 한글 키패드 | **Deleted = 미지원** (v1.0.2 수정: Hangul keypad is not supported) |

### 4-AD. Frame 0_1.3 — Dialer / 입력 컨텍스트 보충

| 키 | 컨텍스트 | Short press | Long press |
|----|---------|-------------|-----------|
| Num. 0~9 (Dialer) | dialer 화면 | 번호 입력 (없으면 dialer 진입 후 입력) | `+` 입력 |
| Num. 0~9 (Quick dial 등록 시) | dialer + 등록 | 위와 동일 | Quick dial 단축번호 발신 |
| Num. 0~9 (Quick dial 미등록) | dialer + 미등록 | 위와 동일 | "이 번호에 저장된 단축번호 연락처가 없습니다" 안내 |
| Clear btn (텍스트 입력창 + cursor) | text editing | 1글자 삭제 + 커서 이동 | 모든 문자 빠르게 삭제 |
| Clear btn (텍스트 입력창 외) | non-edit | 이전 화면 (BACK과 동일) | - |
| Clear btn (변환 단어 list) | conversion list | 변환 중지 | - |

---

## 5. 컨텍스트 분기 detection 방법 (TC step 작성용)

### 5-A. 컨텍스트 매트릭스 — 자동화 분기축

전체 분기축: `(폴더 OPEN/CLOSED) × (Lockscreen/Normal/App실행중/텍스트입력중/Dialer/통화중/Volume bar 표시중) × (Short/Long Press)`

### 5-B. detection 명령

| 컨텍스트 | detection 명령 | 기대 출력 |
|---------|-------------|---------|
| **텍스트 입력 중 (IME shown)** | `dumpsys input_method | grep mInputShown` | `mInputShown=true` (SMOKE_04 검증 패턴) |
| **폴더 OPEN/CLOSED** | `getprop sys.hls.hall.state` | `0` 또는 `1` (의미 매핑 실측 필요) |
| **현재 dialer 화면** | `dumpsys window | grep mCurrentFocus` | `com.android.dialer/...` |
| **현재 IME 모드 (漢字/EN/Number)** | `dumpsys input_method | grep -E 'mCurMethodId|mSubtypeId'` | iWnn subtype id 변화 — 실측 필요 |
| **default app** | `cmd role get-role-holders android.app.role.DIALER` | 현재 default 패키지 |
| **Lock screen 여부** | `dumpsys window | grep -E 'mShowingLockscreen|mDreamingLockscreen'` 또는 `dumpsys keyguard \| grep mShowing` | `mShowing=true` = Lock 상태 |
| **통화 중 여부** | `dumpsys telephony.registry | grep -i callState` 또는 `dumpsys telecom \| grep -i 'CALL_STATE'` | `mCallState=2` (OFFHOOK) |
| **Volume bar 표시 중** | `dumpsys window | grep -E 'volume_dialog|VolumeDialog'` | window 노출 여부 |
| **진동 모드** | `cmd notification get_zen_mode` 또는 `settings get global zen_mode` 또는 `getprop sys.audio.ringer` | mode 정수 |
| **현재 볼륨 단계** | `dumpsys audio | grep -E "STREAM_RING|STREAM_MUSIC" -A 5` | volume 단계 |

---

## 6. 실측 진행 현황 (v0.2 완료 / v0.3 후속)

### v0.2 완료 (2026-05-11 실측)

| # | 항목 | 결과 |
|---|------|------|
| 1 | F1/F2/F3 ↔ Contact/Message/Favorite 매핑 | ✅ 물리 키 getevent 실측 — F1=Contact / F2=Message / F3=Favorite 확정 |
| 2 | End btn KEYCODE | ✅ **KEY_POWER (측면 Power 키)** — 전면 키패드에 별도 End 없음 |
| 5 | Default app 현재 설정 | ✅ DIALER=AOSP, SMS=AOSP, HOME=hnlens.simplemode, Contacts/Camera=hnlens.* 확정 |
| 추가 | OK/Select KEYCODE | ✅ KEY_ENTER (KEYCODE_ENTER 66) |
| 추가 | SOS KEYCODE | ✅ KEY_F4 (event0 gpio-keys, KEYCODE_F4 134) |
| 추가 | F1 vendor hook 패턴 | ✅ 물리 키만 vendor hook → input keyevent F1 동작 없음 (자동화 시 KEYCODE_CONTACTS 207 사용) |
| 추가 | Simple Mode 홈 DPAD 네비게이션 | ✅ DPAD_DOWN x2 → DirectActivity2 → DPAD_CENTER → AOSP dialer 단축 발신 |
| 추가 | 홈에서 숫자 키 동작 | ✅ Simple Mode home 유지하면서 Quick Dialer 백그라운드 입력 수신, BACK 누르면 풀스크린 dialer 전환 |
| 추가 | Simple Mode 홈 메뉴 라벨 (ja-JP) | ✅ ギャラリー / FMラジオ / 設定 / 電話 / メッセージ / カメラ |

### v0.5 실측 진행 결과 (2026-05-11 Round 1~3 완료)

| # | 항목 | 결과 |
|---|------|------|
| **U-1** | hall.state 0/1 OPEN/CLOSED 매핑 | ✅ **확정**: `sys.hls.hall.state=1` → CLOSED (단말 Asleep 동반), `=0` → OPEN (Awake) |
| **U-2** | 물리 Vol Down Long → 진동 모드 | ✅ **확정**: `dumpsys audio` `mode (internal) = VIBRATE` / `mode (external) = VIBRATE` / `ringer mode muted streams = 0x126` (SYSTEM·RING·NOTIFICATION·DTMF muted). detection 명령: `dumpsys audio | grep "mode (internal)"` |
| **U-3** | F2 IME 모드 cycle | ❌ **자동 detection 한계** — iWnn IME가 framework `mCurSubtypeId` 미갱신 (mSubtypeId=0 고정). IME window는 uiautomator dump 영역 외. logcat에도 모드 변경 로그 없음 → **manual_detail 분리** |
| **U-4** | 0~9 Long press 미등록 안내 ja-JP | ❌ **vendor hook 한계** — 사용자 long press 시도해도 "5" 입력만 처리 (text count 13→14), 안내 메시지 미등장. Figma 0_1.3 정의 동작은 vendor handler 영역 → manual_detail 분리 또는 Phone 트랙에서 단축번호 등록 + 재시도 |

### v0.5 후속 사용자 협력 영역 (남은 항목)

| # | 항목 | 우선순위 |
|---|------|--------|
| U-5 | 물리 F1 vs `input keyevent CONTACTS` (207) 동등성 검증 | MEDIUM |
| U-6 | End(Power) short → 통화 중 종료 시나리오 | MEDIUM (다른 단말 발신 필요) |
| U-7 | `*` Long press → 진동 모드 토글 | LOW |
| U-8 | `#` Long press → 터치스크린 잠금 | LOW |
| U-9 | Default app 변경 시 Toast 정책 (Downloaded app 필요) | MEDIUM |
| U-10 | SOS Long press 동작 (보호자 알림 발송 위험) | LOW (수동) |
| U-11 | 폴더 closed 상태 ADB 응답성 | MEDIUM |
| **U-12** | PIN 잠금 등록 + Lock screen 키 분기 검증 | HIGH (Lock 트랙 진입 시 필수) |
| U-13 | 물리 HOME short (home에서) → Quick Panel | MEDIUM |
| U-14 | DPAD Long → Fast Scroll | MEDIUM |

---

## 7. TC 작성 시 적용 가이드 (Phase 1 spec 시드)

### 7-A. yaml `key` action 표준
```yaml
- action: key
  key: "KEYCODE_CALL"
  description: "default Dialer 진입"
  execution_mode: SHELL_AUTO
  step_role: ACTION
```

### 7-B. Long press 표현 (yaml 확장 검토 영역)
현재 yaml `key` action은 short press 가정. Long press는 다음 방식 중 택일:
- (a) `adb shell input keyevent --longpress <KEYCODE>` 형태로 `shell` action에 위임
- (b) yaml `key` action에 `long_press: true` 옵션 추가 (schema 확장)

**권고**: 초기에는 (a) 방식으로 진행. long-press 사용 빈도 높으면 (b)로 schema 확장.

### 7-C. 컨텍스트 보장 step
key action 전에 컨텍스트 보장 ASSERT 추가:
```yaml
# Message 키 short press 의미 분기 — 텍스트 입력 중인지 명확
- action: verify_shell
  command: "dumpsys input_method"
  expected: "mInputShown=false"  # 또는 true
  step_role: ASSERT
- action: key
  key: "KEYCODE_F2"
  step_role: ACTION
```

### 7-D. Risk gate (TC 작성 자동 검토 항목)
- End 키 long press 사용 시 → cleanup에 popup dismiss step 강제
- SOS 키 사용 시 → 외부 알림 발생 가능, 테스트 환경 확인 필수
- 폴더 CLOSED 상태 TC → adb UI dump 불가, 수동 검증 비중 ↑

---

## 8. 변경 이력

| 버전 | 일자 | 변경 |
|------|------|------|
| v0.1 (seed) | 2026-05-11 | Figma `0_0_[THOR2-J] FocusRule v1.0.5` (frame 0_1.1, 0_1.1.1, 0_1.2, 0_1.3) + adb 실측 입력 디바이스 5종 + hall sensor + 벤더 앱 식별. KEYCODE 매핑 표·실측 영역 9건 식별 |
| v0.2 | 2026-05-11 | **물리 키 getevent 실측 완료** — F1=Contact / F2=Message / F3=Favorite / KEY_POWER=End / KEY_F4=SOS / KEY_ENTER=OK 확정. `cmd role get-role-holders` 7종으로 default app 확정 (DIALER/SMS=AOSP, HOME/Contacts/Camera/RecentApps=hnlens.*). vendor key handler 패턴 식별 (물리 F1만 vendor hook). Simple Mode home DPAD 네비게이션 + Quick Dialer 백그라운드 입력 패턴. ja-JP 메뉴 라벨 6종. v0.3 후속 영역 11건 분류 |
| v0.3 | 2026-05-11 | **Figma 추가 frame 6종 통합** (0_1.1.2, 0_1.4, 0_1.5, 0_1.6, 0_1.7, 0_1.8). Default app Toast 정책 + 2초 throttle. 4-way + OK 키 컨텍스트 매트릭스 (focus 없을 시 wake-focus / short/long / 텍스트 입력 중 cursor·예측변환). Lock screen Volume 흐름 (bar appear, 3초 dismiss, lock 유지). Normal Volume 흐름 (DPAD로 단계 조절, 앱 실행 중 bar만 dismiss). Volume Long press (Up=최대, Down=진동 모드). 스크린샷 단축키 (End+Vol Down). 컨텍스트 분기 detection 명령 11종 확장 (Lock screen / 통화 중 / Volume bar / 진동 모드 / 볼륨 단계 추가) |
| v0.4 | 2026-05-11 | **자동 시험 결과 통합** — (1) **PASS**: Vol Up → VolumeDialogImpl 등장 + 3초 dismiss, KEYCODE_SYSRQ(120) → 스크린샷 생성, KEYCODE_SLEEP(223) → Asleep, WAKEUP → Awake, MMS ComposeActivity 진입 즉시 mInputShown=true. (2) **vendor hook 한계 식별**: POWER short / Vol Down Long / F1 input / F2 IME cycle / Number Long press(Quick dial) 모두 input keyevent 시뮬 미동작. (3) **자동화 운영 표준 확정**: SLEEP(223)·CONTACTS(207)·SYSRQ(120) 사용. IME·진동·Quick dial 동작은 manual_detail 분리. (4) Power+Vol Up = Global Actions menu / Power+Vol Down = 스크린샷 (시스템 매핑 확인). (5) 사용자 협력 필요 영역 11건 분류 |
| v0.5 (이전) | 2026-05-11 | **Figma 추가 frame (0_2.x Lock screen / Home Navigation / Quick Panel, 0_3.x Power Pop-up / List Navigation / Fast Scroll) 통합**. (1) **PASS**: `input keyevent --longpress KEYCODE_POWER` → ActionsDialog(Power Pop-up) 진입 + ja-JP 라벨 緊急通報/電源を切る/再起動 일치. `cmd statusbar expand-notifications` → NotificationShade(Quick Panel) 진입 + 라벨 Wi-Fi/Bluetooth/モバイルデータ/サウンドモード/オープン/管理 일치. (2) **vendor hook 추가**: HOME short(home에서) → Quick Panel 자동 시뮬 안 됨, DPAD Long press → Fast Scroll 안 됨. (3) **PIN 잠금 미설정** 확인 (deviceLocked=0) — Lock screen 시험은 PIN 등록 사용자 협력 필요. (4) Thor 1 → Thor 2 변경: Long press home → Quick Panel 미사용, **Short press home (Home 화면 안) = Quick Panel**, Google Assistant 미사용. (5) 자동화 우회 명령 표 6종 정리 |
| v0.5.1 | 2026-05-11 | **사용자 협력 Round 1~3 완료** — (1) **U-1 PASS**: `sys.hls.hall.state` **1=CLOSED / 0=OPEN** 확정. CLOSED 시 wake=Asleep 동반. (2) **U-2 PASS**: 측면 Vol Down Long → audio `mode (internal)=VIBRATE`, `ringer mode muted streams=0x126`. detection 명령 `dumpsys audio \| grep "mode (internal)"`. (3) **U-3 manual_detail**: iWnn IME가 framework `mCurSubtypeId` 미갱신 (mSubtypeId=0 고정) → IME 모드 cycle은 자동 detection 불가. (4) **U-4 manual_detail**: 미등록 0~9 Long press 시 안내 메시지 미등장 (단순 번호 입력만 처리) → vendor handler 또는 단말 정책 영향, Phone 트랙에서 단축번호 등록 후 재검증. (5) 사용자 협력 남은 영역 10건 분류 (U-12 PIN HIGH, 나머지 MEDIUM/LOW) |
| **v0.6** | **2026-05-11** | **PDF v1.0.5 전체 (45페이지) 통합** + 자동 시험 단계 A 3건 결과 통합. (1) **신규 섹션 추가** (4-T ~ 4-AC): 0_4.x Search / 0_4.3 More menu / 0_5.x Multi-select·Toggle·Filter·Tab / 0_6.x Popup focus 룰 (default=OK / **delete=Cancel** 안전) / 0_7.x **Favorite button** Short=등록앱 실행·Long 1초=popup·Case 1·2 / 0_8.x **Touch screen lock** (`#` Long press 다국어 popup + 재부팅 유지) / 0_9.x Input box cursor 이동 + 한글 키패드 미지원. (2) **자동 시험 A 결과**: A-1 `#` Long → ❌ vendor hook 한계 (dialer 진입). A-2 OK Long → ⚠️ MMS list 빈 데이터로 미검증. **A-3 PASS**: F3 short/long 둘 다 ShortcutEditActivity (お気に入り / お気に入りにアプリが登録されていません / キャンセル / 登録) ✅ Case 2 정확 일치. (3) **v0.5 정정**: Favorite 동작 — 단말은 Case 2(미등록)이라 short/long 동일, Figma 정의 일치. (4) 다국어 메시지 ja-JP 라벨 다수 캡처 |

## 다국어 메시지 매트릭스 (PDF v1.0.5 추출)

| 컨텍스트 | JPN | KOR | ENG |
|---------|-----|-----|-----|
| Default app Toast (downloaded app) | ダウンロードしたアプリでは、一部のハードウェアキー機能がサポートされない場合があります 。 | 다운로드한 앱에서는 일부 하드웨어 키 기능이 지원되지 않을 수 있습니다. | Some hardware key functions may not be supported by downloaded apps. |
| Quick dial 미등록 | (단말 ja-JP 라벨 미확인) | 이 번호에 저장된 단축번호 연락처가 없습니다. | There is no assigned contact to this quick dial number. |
| Favorite 등록 안 됨 popup | **お気に入りにアプリが登録されていません。** ✅ 캡처됨 | 즐겨찾기에 등록된 앱이 없습니다. | There are no app registered as favorite. |
| Favorite 등록 toast | (캡처 미수행) | 즐겨찾기 버튼에 App6을(를) 등록하였습니다. | App6 is registered in the favorite button. |
| Touch lock 설정 확인 popup | (캡처 미수행) | 화면 터치 잠금 시, 물리 키패드로만 입력 및 선택 가능하며, 일부 앱에서는 기능이 제한 될 수 있습니다. 잠금 설정하시겠습니까? | If you lock touch screen, only a physical keypad is available and functions may be limited in some apps. Do you want to lock? |
| Touch lock ON toast | (캡처 미수행) | 화면 터치 잠금 상태입니다. 잠금을 해제하려면 [#]을 길게 누르세요. | Touch Screen Lock is ON. Long press [#] to unlock touch screen. |
| Touch lock OFF toast | (캡처 미수행) | 화면 터치 잠금이 해제되었습니다. 잠금을 다시 설정하려면 [#]을 길게 누르세요. | Touch Screen Lock is OFF. Long press [#] to lock touch screen. |
| Lock screen 잘못된 PIN | (캡처 미수행) | 올바르지 않은 PIN입니다. | (incorrect PIN) |
| Favorite popup 버튼 — 등록 없음 | **キャンセル / 登録** ✅ | 취소 / 등록 | Cancel / Register |
| Favorite popup 버튼 — 등록 있음 | (캡처 미수행) | 변경 | Change |

**자동화 검증 라벨**: `お気に入り` / `お気に入りにアプリが登録されていません。` / `キャンセル` / `登録` (A-3 dump 결과 — TC anchor로 사용 가능)

---

## 9. 자동화 구현 수준 종합

### ✅ 자동화 가능 (확정)

| 영역 | 명령 | TC 적용 |
|------|-----|---------|
| 단말 sleep / wake | `KEYCODE_SLEEP (223) / WAKEUP (224)` | preflight / cleanup |
| 스크린샷 | `KEYCODE_SYSRQ (120)` | 증거 캡처 |
| Power Pop-up | `--longpress KEYCODE_POWER` | TEARDOWN 회피 + popup 검증 |
| Quick Panel 열기/닫기 | `cmd statusbar expand-notifications / collapse` | TC step (HOME 2회 누름 대신) |
| Contact app 진입 | `KEYCODE_CONTACTS (207)` | F1 대신 |
| Volume Up Long → Bar 등장 / 3초 dismiss | `--longpress 24` + `dumpsys window | grep VolumeDialog` | Bar 동작 검증 |
| 폴더 상태 detection | `getprop sys.hls.hall.state` | precondition + verify_shell |
| 진동 모드 detection | `dumpsys audio | grep "mode (internal)"` | 검증 anchor |
| IME 노출 detection | `dumpsys input_method | grep mInputShown` | 컨텍스트 보장 |
| Favorite popup 진입 검증 | `KEYCODE_F3` (Case 2) + uiautomator dump | popup 라벨 verify_text |
| Lock 진입 (PIN 미설정 환경) | `KEYCODE_SLEEP` → keyguard 자동 등장 X | PIN 등록 후 의미 있음 |

### ❌ vendor hook 한계 (자동화 미지원, TC `manual_detail` 분리)

| 영역 | 원인 | 우회 |
|------|------|------|
| Power short press → sleep | input keyevent 무시 | SLEEP(223) 사용 |
| F1 (Contact) input | vendor hook only | CONTACTS(207) 사용 |
| F2 IME 모드 cycle | IME app 내부 처리 | manual_detail |
| Vol Down Long → 진동 | vendor hook only | 사용자 협력 (U-2 PASS) |
| 0~9 Long → Quick dial | vendor hook only | 단축번호 등록 후 사용자 협력 |
| `#` Long → Touch lock | vendor hook (dialer 진입만) | 사용자 협력 (신규 U-15) |
| HOME short (home에서) → Quick Panel | vendor hook only | `cmd statusbar` 우회 |
| DPAD Long → Fast Scroll | vendor hook only | 사용자 협력 |

### ⚠️ 데이터 의존 (자동 + 데이터 준비)

| 영역 | 필요 |
|------|------|
| OK Long → 다중 선택 모드 | 리스트 항목 ≥ 1건 (메시지·연락처 추가) |
| Quick dial 발신 / 미등록 안내 | 단축번호 등록 또는 미등록 환경 분리 |
| Lock screen 키 분기 | PIN 등록 (U-12) |
| Default app Toast | Downloaded app default 설정 |

---

## 10. 참조

- **PDF 원본**: `doc/0_0_[THOR2-J] FocusRule _v1.0.5.pdf` (45페이지, 16.8MB, working tree 보관)
- Figma URL: `0_0_[THOR2-J] FocusRule _v1.0.5` (MMI 페이지)
- Android KeyEvent 상수: https://developer.android.com/reference/android/view/KeyEvent
- 단말 SMOKE 자산: `THOR2_J - Settings/RESUME.md` (Settings 트랙 SMOKE_01+02 PASS, commit `c7fc638`)
