# TalkBack × 하드키(D-PAD) 접근성 검증 플레이북

> 정립 사례: THOR2_J(AT-M140) × LINE 26.10.0 이슈 2건 규명 (2026-07-02, `THOR2_J - LINE Talkback/RESULT_2026-07-02.md`).
> 적용 범위: 하드키 단말 × TalkBack × 임의 앱(3rd-party 포함)의 접근성 이슈 재현·판정·수정 가능성 검토. 앱 특이 내용은 최소화하고 방법론만 담는다.

---

## 1. 개념 모델 (판정의 전제)

### 1.1 포커스 2축 — 혼동하면 판정 전체가 틀어진다

| 축 | 이동 주체 | 관찰 수단 |
|---|---|---|
| **입력 포커스** (input focus) | D-PAD 방향키 → 프레임워크 FocusFinder | `uiautomator dump`의 `focused="true"` |
| **a11y 포커스** (accessibility focus) | TalkBack (터치 탐색·선형 제스처·입력 포커스 추종) | TalkBack 초록 박스 (오버레이 — screencap에 찍힘) |

- 하드키 단말에서 D-PAD는 **입력 포커스**를 움직이고, TalkBack이 이를 추종해 a11y 포커스 + 발화를 만든다.
- **TalkBack 추종 규칙**: "자식이 있는 non-speaking actionable 컨테이너"(자체 desc/text 없음 + 발화 가능 자손이 전부 별도 focusable 자식 내부)에는 a11y 포커스를 동기화하지 않는다 → **입력 포커스만 이동하고 사용자 피드백 0인 구간**이 생긴다. 반면 자식 없는 leaf actionable 노드는 무라벨이어도 포커스를 받고 "레이블 없음"을 발화한다.
- 발화 라벨 집계: focusable 노드의 발화 = 자신 desc/text + **비-focusable 자손**만 집계. focusable 자식의 라벨은 부모 발화에서 제외된다.

### 1.2 FocusFinder / 키 소비 기하 (D-PAD 도달성의 프레임워크 규칙)

- `FocusFinder.isCandidate()`: 이동 방향으로 후보 rect가 소스 rect보다 **더 나아가 있어야** 후보가 된다 (RIGHT면 candidate.right > src.right). → **전폭 focusable 컨테이너에 완전 포함된 자식은 4방향 모두 도달 불가** (컨테이너가 자식을 가림 = shadowing).
- UP 후보 경쟁: 소스가 전폭이면 전폭 컨테이너가 부분폭 개별 버튼을 항상 이긴다 (minor-axis 거리 0).
- `ScrollView`: 최상단에서 UP은 소비 못 하고 버블 → 전역 포커스 탐색 진행. `ViewPager`: LEFT/RIGHT를 소비해 **페이지(탭) 전환** — 페이지 내 우측 후보가 없으면 사용자는 "옆 탭으로 튕김"을 겪는다.
- 앱이 `nextFocusUp/Right` 등 힌트를 지정하면 기하를 우회 가능 — 힌트 부재는 실측 궤적으로 확인.

## 2. 표준 검증 프로토콜

### 2.0 환경 고정 (기록 필수)

```
adb devices                                              # 시리얼 확인, 이후 전 명령 -s 핀
adb shell getprop ro.product.model; getprop ro.build.display.id
adb shell settings get secure enabled_accessibility_services   # TalkBack 활성 여부
adb shell settings get secure touch_exploration_enabled
adb shell "dumpsys package <앱pkg> | grep versionName"
adb shell "dumpsys package com.google.android.marvin.talkback | grep versionName"
```

### 2.1 구조 캡처 (a11y 트리 = TalkBack이 보는 것과 동일)

```
adb shell uiautomator dump /sdcard/x.xml && adb pull /sdcard/x.xml <증거경로>
```

노드별 체크 4속성: `focusable` / `clickable` / `content-desc` / `bounds` (+`NAF`). 스크리닝 항목은 §4.

### 2.2 D-PAD 궤적 추적

- 키 주입: `input keyevent 19/20/21/22` (UP/DOWN/LEFT/RIGHT), 활성화 `23`(CENTER).
- **스텝 사이에는 `screencap`만** — 초록 박스 위치가 a11y 포커스 지표. dump는 시퀀스 종료 후 1회 (함정 §3-①).
- 궤적 기록 형식: 스텝별 (키, 초록 박스 노드, 화면 전환 여부) 표.

### 2.3 TalkBack OFF 대조 (레이어 분리의 핵심)

1. 설정 3종 백업: `enabled_accessibility_services` / `accessibility_enabled` / `touch_exploration_enabled` → 파일 저장.
2. `settings put secure enabled_accessibility_services ''` → 같은 키 궤적을 이번엔 **dump 병행**으로 추적 (`focused="true"` = 입력 포커스 실측 — OFF에선 dump가 아무것도 억제하지 않음).
3. 복원 후 백업값 대조 확인.
- 판정: ON/OFF 입력 포커스 궤적이 같으면 → 차이는 TalkBack 피드백 계층. OFF에서도 도달 불가면 → 순수 포커스 그래프 문제.

### 2.4 발화 정량 (utterance 텍스트는 원격으로 못 본다 — 타임라인으로 판정)

```
adb logcat -c → (조작) → adb logcat -d -v time > 파일
```

| 신호 | 의미 |
|---|---|
| `GoogleTTSServiceImpl: Synthesis request` | 발화(utterance) 시작 단위 |
| `MediaFocusControl: requestAudioFocus ... USAGE_ASSISTANCE_ACCESSIBILITY` / `abandonAudioFocus` | 발화 세션 경계 (지속시간 측정) |
| `TTS.BlockingAudioTrack ... write` | 실제 오디오 기록 (utterance 내부 진행) |
| `ActivityTaskManager: Displayed` | 창 전환 시점 — 합성과의 선후로 announce 주체 판별 |

- **대조군 2종 필수**: ① 같은 단말의 정상 앱(OEM 런처 등) = 단말 baseline 분리 ② 유휴 20s+ 관찰 = 자발적 발화 소스(광고 등) 유무. 근접 이중 합성(수십 ms 쌍)은 baseline에서도 발생하므로 단독으론 끊김 증거가 아니다.
- 창 전환 announce는 진행 중 발화를 flush하는 것이 TalkBack 표준 의미론 — "끊김" 판정 시 이 정상 동작과 앱 유발 이벤트를 구분할 것.

## 3. 함정 (실측 확립 — 위반 시 데이터 오염)

1. **`uiautomator dump`는 실행 중 TalkBack을 일시 억제한다** (UiAutomation 연결의 타 서비스 suppress). 키 시퀀스 사이에 dump 금지.
2. **`adb shell input tap/swipe`는 a11y 입력 필터 이전에 주입돼 TalkBack 터치 탐색을 우회한다** — 탭=탐색이 아니라 **즉시 클릭**. 터치 탐색 발화는 원격 재현 불가 → D-PAD 키 주입(`input keyevent`는 필터 통과)으로 같은 스피치 파이프라인을 유발해 대체. 역으로: TalkBack ON이어도 좌표 탭 자동화는 그대로 동작한다. TalkBack 더블탭 활성화가 필요하면 한 셸 세션에서 `input tap X Y && input tap X Y`.
3. **Git Bash에서 `/sdcard/...` 인자는 MSYS 경로 변환으로 깨진다** → adb 조작 루프는 PowerShell로. PowerShell 5.1의 `>` 리다이렉트는 바이너리를 UTF-16으로 깨뜨림 → screencap은 단말 내 파일로 찍고 pull.
4. 발화 텍스트 로깅: `setprop log.tag.talkback VERBOSE`로는 안 열림(TalkBack LogUtils는 자체 prefs 게이트). 실기에서는 TalkBack 설정→고급→개발자 설정→**"음성 출력 표시"** 사용.

## 4. 앱 접근성 정적 스크리닝 체크리스트 (dump 1장으로 앱 무관 적용)

| # | 스크리닝 항목 | 결함 신호 |
|---|---|---|
| S1 | focusable+clickable인데 자체 desc/text 없고 발화 가능 자손이 전부 focusable 자식 내부인 **컨테이너** | 무피드백 포커스 구간·무발화 터치 영역 (LINE 익명 헤더 행 패턴) |
| S2 | 라벨이 클릭 가능한 노드가 아닌 **포커스 불가 자식**에만 존재 | 라벨-타겟 분리 (베스트 프랙티스 위반) |
| S3 | 아이콘 ImageView의 무의미/오라벨 desc | 발화 오염 (LINE '閉じる' ×4 패턴) |
| S4 | 인터랙티브 요소별 **방향키 도달성**: 전폭 컨테이너 내부 자식 / 스크롤 컨테이너 밖 형제 오버레이 | D-PAD 도달 불가 (S1과 결합 시 확정적) |
| S5 | ViewPager 등 수평 키 소비 위젯 + 페이지 내 우측 후보 부재 | 방향키 → 의도치 않은 탭 전환 |
| S6 | `NAF="true"` 노드 | uiautomator 자체 판정 결함 노드 |
| S7 | 발화 세션 완주 여부 (§2.4 타임라인) | 끊김/무발화 |
| S8 | TalkBack 초기 포커스 위치 (창 전환 직후) | 진입점 안내 적절성 |

> 도구화 후보(승인 대기): dump XML → S1~S6 자동 플래깅 스크립트 (`scripts/` 신설은 §2.1 승인 게이트 대상).

## 5. 판정 프레임

### 5.1 레이어 분리 절차

```
① 구조 덤프에서 S1~S6 결함 → 앱 구현 결함 (트리는 앱 프로세스 산출물)
② TalkBack ON/OFF 입력 포커스 궤적 동일 여부 → TalkBack 계층 분리
③ 같은 단말 정상 앱 대조 → 단말/TalkBack baseline 분리
④ (권장) REF 단말 × 같은 앱 버전 → 단말 일반성 확보 (제보 첨부용)
```

- ①~③ 성립 시 단말 리포트는 **SPEC_GAP(단말 결함 아님)** 판정 가능. ④는 외부 제보 설득력 보강.

### 5.2 수정 가능성 판정표 (Android 14 기준, 리서치 확정 — 재사용 가능 결론)

| 경로 | 판정 | 근거 |
|---|---|---|
| 단말(OEM)에서 3rd-party 앱 a11y 트리/포커스 패치 | **불가** | AccessibilityNodeInfo 트리는 앱 프로세스 소유. 외부 서비스는 read+performAction만 (노드 생성·라벨 주입·focusable 수정 API 없음). developer.android.com a11y service 문서 |
| RRO(Runtime Resource Overlay) | 불가 | 리소스 값 전용 + overlayable/서명 게이트. 포커스 로직은 코드. source.android.com/docs/core/runtime/rros |
| TalkBack 동작 수정 | 불가 | Google 유지보수·Play 배포. OEM 개입 = 오픈소스(github.com/google/talkback) 포크 프리로드뿐 (Samsung 선례, 전면 포크 수준 부담) |
| TalkBack에 bare D-PAD 선형탐색 매핑 | 현행 없음 | keymap 2종 모두 수식키(TalkBack key) 조합 필수 — 하드키 전용 단말에서는 입력 포커스 이동만 가능 |
| 커스텀 AccessibilityService 프리로드 | 기술적 가능·비권장 | 트리에 없는 정보 복원 불가 + a11y 포커스 경합 + 앱 업데이트마다 유지보수 부채 |
| **앱 벤더 수정** | **유일한 근본 해결** | §5.3 제보 항목 패턴 |

### 5.3 앱 벤더 제보 항목 패턴 (수정 요구 4종)

1. 무라벨 focusable 컨테이너의 `focusable/clickable` 제거 또는 `importantForAccessibility=no`.
2. `contentDescription`을 **클릭 가능한 노드에 직접** 부여.
3. 장식/상태 아이콘의 오라벨 제거.
4. 하드키 대응 `nextFocusUp/Down/Left/Right` 지정 (스크롤 컨테이너 밖 오버레이 요소 필수).

---

## 6. 사례 인덱스

| 날짜 | 단말×앱 | 결과 | 증거 |
|---|---|---|---|
| 2026-07-02 | THOR2_J × LINE 26.10.0 | 이슈 2건 SPEC_GAP (익명 헤더 컨테이너 shadowing + 무라벨/오라벨). 적대적 검증 통과 | `THOR2_J - LINE Talkback/` |
