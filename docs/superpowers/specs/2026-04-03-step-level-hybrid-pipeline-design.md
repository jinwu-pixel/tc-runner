# Step-level Hybrid Pipeline 설계 문서

> tc-runner의 MMI 변환 파이프라인을 step-level classification, hybrid runner, shell action map, multi-format segmenter, YAML export로 확장하는 설계.

---

## 1. 실행 순서 및 의존 관계

```
Phase 1: Issue 1 (Step-level classification) → Issue 2 (Hybrid runner)
Phase 2: Issue 3 (Shell action map) → Issue 4 (Multi-format segmenter)
Phase 3: Issue 5 (YAML export)
```

의존 관계:
- Issue 2는 Issue 1에 의존 (step classification 결과를 runner가 소비)
- Issue 3는 Issue 1에 의존 (SHELL_AUTO 승격은 shell_action_map 존재 여부에 따름)
- Issue 4는 Issue 1 일부 완료 후 진행 가능
- Issue 5는 Issue 1~4 모두 안정화된 후 진행

---

## 2. 데이터 모델 변경 (전체 공통)

### 2.1 두 축 분리: ExecutionMode + StepRole

`StepClass`를 단일 enum으로 두지 않고 두 축으로 분리한다. 실행 방식과 단계 역할은 독립적인 관심사이다.

```python
ExecutionMode = Literal[
    "UI_AUTO",            # UI 탭/스와이프/키 조작
    "SHELL_AUTO",         # adb shell 명령 실행
    "MANUAL_REQUIRED",    # 물리적 수동 조작
    "EXTERNAL_EVENT",     # 외부 단말/네트워크 이벤트
    "UNSUPPORTED",        # 해석 불가
]

StepRole = Literal[
    "ACTION",             # 실행 동작
    "ASSERT",             # 검증
    "SETUP",              # 사전 조건 준비
    "TEARDOWN",           # 정리/복원
]
```

**설계 근거:** 동일한 `Intent(type="input_text")`라도 문맥에 따라 `UI_AUTO`일 수도 있고 `EXTERNAL_EVENT`일 수도 있으므로, Intent 자체에 step_class를 optional 필드로 넣으면 책임이 섞인다.

### 2.2 ClassifiedIntent

```python
@dataclass(slots=True)
class ClassifiedIntent:
    intent: Intent
    execution_mode: ExecutionMode
    step_role: StepRole
    confidence: float = 1.0
    reasons: list[str] = field(default_factory=list)
```

`reasons`는 `list[str]`이며, 각 항목은 `규칙명: 설명` 형식으로 남긴다:
- `"external_keyword_match: '수신 전화' → EXTERNAL_EVENT"`
- `"shell_mapping_missing: '권한 허용' shell 매핑 미구현"`
- `"parser_fallback_low_confidence: navigate fallback, confidence 0.5"`

### 2.3 파이프라인 변경

```
현재:  parser → list[Intent] → compiler → steps
변경:  parser → list[Intent] → step_classifier → list[ClassifiedIntent] → compiler → steps
```

`service.py`의 `convert_row()`가 이 흐름을 조율한다.

### 2.4 Intent.extra 메타데이터 규약

parser가 classifier에 전달하는 힌트:

```python
Intent(
    type="navigate",
    target="수신 전화",
    extra={
        "raw_segment": "3) 수신 전화 1회",
        "matched_rule": "navigate_fallback",
        "parser_confidence": 0.5,
        "position": 2,           # 0-indexed segment 위치
        "total_segments": 5,
        "source_phase": "procedure",
        "detected_format": "numbered_paren",
        "split_strategy": "hierarchical_numbered_then_menu",
    }
)
```

---

## 3. StepClassifier 모듈 (Issue 1)

새 파일: `src/mmi_converter/step_classifier.py`

### 3.1 인터페이스

```python
class StepClassifier:
    def __init__(self, shell_action_map: ShellActionMap | None = None):
        """shell_action_map이 없으면 SHELL_AUTO 승격을 하지 않는다."""

    def classify(
        self, intents: list[Intent], context: dict | None = None
    ) -> list[ClassifiedIntent]:
        """Intent 리스트를 분류한다.
        context에는 source_row, precondition 등 TC-level 정보 포함 가능.
        """

    def summarize_tc_class(
        self, classified: list[ClassifiedIntent]
    ) -> str:
        """step 분류 결과를 집계하여 TC-level automation class 반환."""
```

### 3.2 3단계 판정 (refinement 방식)

**1단계: Intent.type → 기본값**

| Intent.type | 기본 ExecutionMode | 기본 StepRole |
|---|---|---|
| `navigate` | `UI_AUTO` | `ACTION` |
| `press_key` | `UI_AUTO` | `ACTION` |
| `wait` | `UI_AUTO` | `ACTION` |
| `toggle` | `UI_AUTO` | `ACTION` |
| `input_text` | `UI_AUTO` | `ACTION` |
| `verify_text` | `UI_AUTO` | `ASSERT` |
| `verify_shell` | `SHELL_AUTO` | `ASSERT` |
| `manual_required` | `MANUAL_REQUIRED` | `ACTION` |

**2단계: 키워드 refinement (허용 전이 규칙 적용)**

전이는 override가 아니라 refinement이다. Intent.type별 허용 전이 테이블:

```python
ALLOWED_TRANSITIONS = {
    "UI_AUTO":          {"SHELL_AUTO", "MANUAL_REQUIRED", "EXTERNAL_EVENT"},
    "SHELL_AUTO":       {"MANUAL_REQUIRED", "EXTERNAL_EVENT"},
    "MANUAL_REQUIRED":  set(),
    "EXTERNAL_EVENT":   {"MANUAL_REQUIRED"},
    "UNSUPPORTED":      set(),
}
```

ASSERT role 전이 규칙:
- ASSERT role에서는 lexical match만으로 `SHELL_AUTO`로 뒤집지 않음
- `EXTERNAL_EVENT` / `MANUAL_REQUIRED` 전이는 제한적으로 허용
  (예: "수신 전화 수신 확인" → ASSERT이면서 EXTERNAL_EVENT 의존)

키워드 목록 (좁힌 버전):

```python
EXTERNAL_KEYWORDS = [
    "수신 전화", "발신 전화", "전화 수신", "전화 발신",
    "보조폰", "보조 단말", "상대 단말", "외부 단말",
]

MANUAL_KEYWORDS = [
    "이어폰 연결", "이어폰 해제", "헤드셋 연결",
    "USB 케이블 연결", "USIM 삽입", "USIM 교체", "SIM 교체",
    "충전기 연결", "충전기 분리",
]

# SHELL_AUTO 승격은 shell_action_map에 대응 키가 있을 때만
SHELL_CANDIDATES = [
    "앱 실행", "앱 열기", "앱 종료", "강제 종료",
    "권한 부여", "권한 허용", "권한 거부", "권한 철회",
    "로그 초기화", "logcat",
]
```

SHELL_CANDIDATES 매칭 시:
```python
if keyword in SHELL_CANDIDATES:
    if self._shell_map and self._shell_map.has_mapping(keyword):
        execution_mode = "SHELL_AUTO"
        reasons.append(f"shell_mapping_confirmed: '{keyword}' → shell action 존재")
    else:
        reasons.append(f"shell_mapping_missing: '{keyword}' shell 매핑 미구현")
        # execution_mode 유지 (UI_AUTO 또는 원래 값)
```

SHELL_AUTO 승격은 "후보"일 뿐이고, 실제 shell step 생성 확정은 compiler에서 `resolve + params resolution` 성공 시점이다.

**ExecutionMode refinement priority**는 아래와 같다.

- `MANUAL_REQUIRED > EXTERNAL_EVENT > SHELL_AUTO`

이는 **ExecutionMode 축에만 적용되는 우선순위**이다.

`StepRole` (`ACTION`, `ASSERT`, `SETUP`, `TEARDOWN`)은 별도 규칙으로 판정하며,
ExecutionMode 우선순위와 직접 경쟁하지 않는다.

즉:
- ExecutionMode는 "이 step을 어떤 방식으로 수행/대기할 것인가"를 나타낸다.
- StepRole은 "이 step이 실행/검증/준비/정리 중 어떤 역할인가"를 나타낸다.

두 축은 독립적으로 판정되며, 하나의 우선순위 체계로 섞어 다루지 않는다.

**3단계: 메타데이터 보정**

parser_confidence가 낮고 fallback 규칙이면 confidence 하향. ExecutionMode 자체는 변경하지 않음.

### 3.3 SETUP / TEARDOWN 판정

키워드뿐 아니라 위치와 context도 함께 본다:
- 첫 step이면 SETUP 가중치 증가
- 마지막 step이면 TEARDOWN 가중치 증가
- `context.precondition`, `position`, `source_phase` 참고
- 중간 step의 "초기화", "설치"는 무조건 role 변경하지 않고 reason만 추가

### 3.4 TC-level summary 도출

StepClassifier를 항상 실행한다. TC-level 분류는 step 결과 집계로 도출:

```python
def summarize_tc_class(self, classified: list[ClassifiedIntent]) -> str:
    if not classified:
        return "AMBIGUOUS_NL"

    modes = [c.execution_mode for c in classified]
    total = len(modes)
    unsupported_count = sum(1 for m in modes if m == "UNSUPPORTED")

    if "MANUAL_REQUIRED" in modes or "EXTERNAL_EVENT" in modes:
        return "SEMI_AUTO"

    if unsupported_count == total:
        return "AMBIGUOUS_NL"

    # 일부 step만 unsupported인 경우는 기본적으로 SEMI_AUTO로 완화
    if unsupported_count > 0:
        return "SEMI_AUTO"

    if all(m in {"UI_AUTO", "SHELL_AUTO"} for m in modes):
        return "FULL_AUTO"

    return "AMBIGUOUS_NL"
```

설계 원칙:
- `UNSUPPORTED`가 일부 포함되더라도 전체 TC를 즉시 `AMBIGUOUS_NL`로 강등하지 않는다.
- 소수의 unsupported step이 포함된 경우 기본적으로 `SEMI_AUTO`로 분류한다.
- 전체 step이 unsupported이거나, 핵심 step 다수가 unsupported인 경우에만 `AMBIGUOUS_NL`로 본다.

향후 필요하면 unsupported 비율 또는 핵심 step 여부를 반영하는 방식으로 정교화할 수 있다.

기존 `MMITCClassifier`는 coarse pre-check으로 유지하되, 최종 TC 분류는 이 집계 결과를 사용. 이후 안정화되면 `MMITCClassifier`는 backward compatibility 용도로 축소 가능.

### 3.5 기존 classifier.py와의 관계

- 기존 `MMITCClassifier`: TC 전체를 분류 (유지, coarse pre-check)
- 새 `StepClassifier`: 개별 step을 분류 (최종 TC 분류의 근거)
- StepClassifier는 항상 실행. TC-level classifier가 MANUAL_REQUIRED여도 step 분류를 건너뛰지 않음.

---

## 4. Hybrid Runner (Issue 2)

### 4.1 핵심 방향

- `action_runner`는 직접 `input()`을 호출하지 않는다
- 수동 개입은 `on_manual_step` 콜백으로 위임
- manual/external step은 "즉시 실행 action"이 아니라 **pause point**
- no-handler 기본 동작은 **fail-fast** (auto skip 아님)

### 4.2 콜백 인터페이스

```python
@dataclass(slots=True)
class ManualStepAction:
    decision: Literal["continue", "skip", "fail"]
    reason: str = ""
    evidence_path: Path | None = None

@dataclass(slots=True)
class ManualStepContext:
    tc_name: str
    step_index: int
    step: dict
    execution_mode: str
    screenshot_path: Path | None
    timeout_seconds: int | None = None

ManualStepHandler = Callable[[ManualStepContext], ManualStepAction]
```

### 4.3 ActionRunner 확장

```python
class ActionRunner:
    def __init__(self, adb, screenshot_dir, on_manual_step: ManualStepHandler | None = None):
        self.on_manual_step = on_manual_step
```

### 4.4 run_step 동작 원칙

1. `execution_mode in ("MANUAL_REQUIRED", "EXTERNAL_EVENT")`이면 pause point
2. pause 진입 시점 스크린샷 캡처
3. manual handler 호출
4. handler 결과에 따라 현재 step 결과 반환
5. 다음 step 실행은 **상위 실행 루프**가 담당

### 4.5 decision별 처리

**continue:**
- 현재 step을 성공 처리
- 다음 step 실행 전 sanity check / recovery hook 수행 가능:
  - DUT 화면 잠김 확인
  - 앱 foreground 확인
  - 예상치 못한 팝업 존재 여부 확인
- "무조건 다음 액션 실행"이 아니라, 가벼운 상태 점검 후 상위 루프가 다음 step 진행

**skip:**
- `passed=False`, `manual_action="skip"`으로 기록 (success와 구분)
- 결과에 명시적으로 skip 상태와 사유 기록
- 리포트에서 success / skipped / failed를 3가지로 분리 표시

**fail:**
- 현재 step 즉시 실패 처리
- 상위 루프에서 TC 중단 여부 결정

### 4.6 no-handler 기본 동작

manual/external step인데 handler가 없으면 **fail-fast**:
- 메시지: `"manual handler not configured"`
- 예외적으로 `--auto-skip-manual` 옵션이 있을 때만 skip 허용

### 4.7 timeout 정책

무한 대기는 허용하지 않는다.

- step별 `manual_timeout` optional 지원
- 기본값: 300초
- `on_timeout: fail | skip` 지원, 기본값은 `fail`

YAML 예시:
```yaml
- action: manual_pause
  execution_mode: EXTERNAL_EVENT
  step_role: ACTION
  description: "보조폰에서 DUT로 전화를 걸어주세요"
  manual_timeout: 300
  on_timeout: fail
  allow_skip: true
```

### 4.8 StepResult 확장

```python
@dataclass
class StepResult:
    action: str
    passed: bool
    message: str = ""
    duration: float = 0.0
    screenshot_path: Optional[Path] = None
    execution_mode: str = ""
    manual_action: str = ""           # continue / skip / fail / ""
    skip_reason: str = ""
    paused: bool = False
    pause_screenshot_path: Optional[Path] = None
    manual_evidence_path: Optional[Path] = None
```

`skip`은 success와 동일하게 보이면 안 된다. report summary에서 success / skipped / failed를 분리 표시.

### 4.9 Reporter 반영

HTML/터미널 리포트에 표시:
- `[MANUAL]` / `[EXTERNAL]` 라벨
- decision 결과: continue / skip / fail
- skip reason
- pause 시점 스크린샷
- timeout 발생 여부
- sanity check / recovery 수행 여부

### 4.10 설계 원칙

manual/external step은 가능하면 실제 검증 step과 분리:
- Step A: `manual_pause` / `EXTERNAL_EVENT` (pause point)
- Step B: `verify_text` (검증)

"수신 전화" 자체는 pause point로 두고, 검증은 다음 step으로 명시적으로 분리.

---

## 5. Shell Action Map (Issue 3)

새 파일: `src/mmi_converter/shell_action_map.py`

### 5.1 3단계 매핑 원칙

자연어에서 직접 shell 문자열을 생성하지 않는다:
```
한국어 키워드 → shell action key → adb shell command template
```

### 5.2 ShellAction 모델

```python
@dataclass(slots=True)
class ShellAction:
    key: str                    # "launch_app", "grant_permission" 등
    command_template: str       # "am start -n {package}/{activity}"
    required_params: list[str]  # ["package"]
    optional_params: dict[str, str]  # {"activity": ".MainActivity"}
    description: str

class ShellActionMap:
    def has_mapping(self, keyword: str) -> bool:
        """StepClassifier가 SHELL_AUTO 승격 여부 판단 시 사용"""

    def resolve(self, intent: Intent) -> ShellAction | None:
        """Intent에서 매칭되는 ShellAction 반환"""

    def render_command(self, action: ShellAction, params: dict) -> str:
        """template에 params를 채워 최종 command 생성"""
```

### 5.3 초기 지원 액션 (6개)

| key | 키워드 패턴 | command template | required_params |
|-----|-----------|------------------|-----------------|
| `launch_app` | 앱 실행, 앱 열기, 실행 | `am start -n {package}/{activity}` | `package` |
| `force_stop` | 앱 종료, 강제 종료 | `am force-stop {package}` | `package` |
| `grant_permission` | 권한 부여, 권한 허용 | `pm grant {package} {permission}` | `package`, `permission` |
| `revoke_permission` | 권한 거부, 권한 철회 | `pm revoke {package} {permission}` | `package`, `permission` |
| `clear_logcat` | 로그 초기화, logcat 초기화 | `logcat -c` | 없음 |
| `open_settings` | 설정 화면 진입 | `am start -a {settings_action}` | `settings_action` |

후속 후보: `open_app_details_settings`, `start_activity` 계열.

`grant_permission` / `revoke_permission`은 Android 버전/권한 종류에 따라 제약이 있을 수 있다. 문서에 warning 명시.

### 5.4 파라미터 해결 전략

**Case 1: 파라미터 불필요** — `clear_logcat`. 바로 command 생성.

**Case 2: TC 컨텍스트에서 추출** — precondition/extra에서 패키지명 추출 시도.

**Case 3: 추출 불가** — warning + placeholder + `compile_status: "UNRESOLVED_PARAMS"` + `runnable: false` 표시.

placeholder 포함 step은 실행 가능한 step처럼 보이면 안 된다:
```yaml
- action: shell
  command: "am start -n {package}/{activity}"
  execution_mode: SHELL_AUTO
  compile_status: UNRESOLVED_PARAMS
  runnable: false
  _unresolved_params: ["package", "activity"]
```

### 5.4.1 Alias Registry (앱/권한 번역 계층)

TC 자연어에는 보통 Android 시스템 식별자 대신 사람이 읽는 이름이 등장한다.
예:
- "카카오톡 실행"
- "유튜브 강제 종료"
- "카메라 권한 허용"
- "위치 권한 거부"

따라서 Shell Action Map이 실제 command를 생성하려면
자연어 이름을 Android 식별자로 변환하는 별도 번역 계층이 필요하다.

초기 설계:
- `APP_ALIAS_REGISTRY`
- `PERMISSION_ALIAS_REGISTRY`

예시:

```python
APP_ALIAS_REGISTRY = {
    "카카오톡": "com.kakao.talk",
    "유튜브": "com.google.android.youtube",
    "설정": "com.android.settings",
}

PERMISSION_ALIAS_REGISTRY = {
    "카메라 권한": "android.permission.CAMERA",
    "위치 권한": "android.permission.ACCESS_FINE_LOCATION",
    "전화 권한": "android.permission.READ_PHONE_STATE",
}
```

파라미터 해결 순서:

1. 자연어에서 직접 시스템 식별자가 명시된 경우 우선 사용
2. alias registry로 변환 시도
3. context(precondition / extra / prior resolved app)에서 보완 추론
4. 그래도 실패하면 placeholder + `UNRESOLVED_PARAMS`

이 계층이 없으면 `package`, `permission` 추출 실패로 인해 placeholder 비율이 과도하게 높아질 수 있다.

### 5.5 Compiler 연동

compiler가 `ClassifiedIntent`를 받을 때, `execution_mode == "SHELL_AUTO"`이면 shell_action_map을 조회:
- `resolve()` 성공 + params 해결 → shell step 생성
- `resolve()` 성공 + params 미해결 → placeholder step + warning
- `resolve()` 실패 → warning, step 미생성

classifier의 SHELL_AUTO 승격은 "후보"이고, compiler에서 실제 step 생성이 확정된다.

### 5.6 open_settings 서브 매핑

```python
SETTINGS_INTENTS = {
    "Wi-Fi": "android.settings.WIFI_SETTINGS",
    "블루투스": "android.settings.BLUETOOTH_SETTINGS",
    "디스플레이": "android.settings.DISPLAY_SETTINGS",
    "소리": "android.settings.SOUND_SETTINGS",
    "배터리": "android.intent.action.POWER_USAGE_SUMMARY",
    "앱": "android.settings.APPLICATION_SETTINGS",
}
```

alias normalize 필요: `와이파이`, `wifi`, `WiFi` → `Wi-Fi`
exact mapping 실패 시 일반 설정 화면(`android.settings.SETTINGS`)으로 fallback.

`open_settings`의 alias normalize는 settings 메뉴명 전용이며,
앱 패키지명/권한명 변환은 `APP_ALIAS_REGISTRY` / `PERMISSION_ALIAS_REGISTRY`가 담당한다.

### 5.7 제한사항

현재 `adb.shell()`은 `returncode/stderr`를 보존하지 않는 구조이다. shell action 확장 시 실행 성공/실패 판정이 취약할 수 있다. 향후 `adb.shell()` 반환값 확장이 필요할 수 있음.

---

## 6. Multi-format Segmenter (Issue 4)

### 6.1 설계 전략: 포맷 감지 → 포맷별 분리

단일 정규식 확장 대신 텍스트 포맷을 먼저 감지하고 포맷에 맞는 분리 전략을 적용한다.

```python
class ProcedureSegmenter:
    def split(self, text: str) -> list[str]:
        if not text:
            return []
        fmt = self._detect_format(text)
        raw = self._split_by_format(text, fmt)
        return [self._normalize(s) for s in raw if self._normalize(s)]
```

### 6.2 포맷 분류

```python
class ProcedureFormat(Enum):
    MENU_CHAIN = "menu_chain"
    NUMBERED_PAREN = "numbered_paren"
    NUMBERED_DOT = "numbered_dot"
    CIRCLED = "circled"
    NEWLINE = "newline"
    MIXED = "mixed"
```

감지 로직:
- 복수 신호 감지 시 → `MIXED`
- `>` / `→` / `->` → `MENU_CHAIN`
- `N)` → `NUMBERED_PAREN`
- `N. ` → `NUMBERED_DOT`
- `①②③` → `CIRCLED`
- 비어 있지 않은 줄이 2개 이상 → `NEWLINE`
- 기본 → `MIXED`

### 6.3 MIXED 계층적 분리

MIXED는 flat split 대신 계층적 split:

1. 먼저 번호형/원문자/줄바꿈 등 바깥 구조로 분리
2. 각 조각 안에 `>`가 있으면 메뉴 체인으로 다시 분리
3. 연결어(`후`, `그리고`, `이후`)는 마지막에 보조 분리

이렇게 해야 바깥 포맷 정보가 덜 손실된다.

### 6.4 연결어 처리

`후`, `그리고`, `이후`는 모든 포맷에서 보조 분리자로 작동하되, **괄호 depth 0에서만 적용**:
- 괄호 내부 텍스트를 임시 보호한 뒤 분리
- 예: `"(예: 원격제어 앱 실행 후 확인)"` → 괄호 내부이므로 "후"로 분리하지 않음

### 6.5 normalize 보강

```python
def _normalize(self, text: str) -> str:
    text = " ".join(text.strip().split())
    text = re.sub(r"^\d+\.\s*", "", text).strip()
    text = re.sub(r"^\d+\)\s*", "", text).strip()
    text = re.sub(r"^[①-⑳]\s*", "", text).strip()
    text = re.sub(r"\(\s*\)", "", text).strip()  # 빈 괄호 제거
    return text
```

### 6.5.1 구현 메모

- numbered split 정규식은 줄 시작 또는 공백 경계를 고려해야 한다.
- 예: `\d+\)` / `\d+\.` 패턴을 문장 중간 숫자와 혼동하지 않도록 주의
- 괄호 내부 텍스트는 연결어 후처리 전에 임시 보호한 뒤 복원하는 방식이 바람직하다

### 6.6 기존 `/` 구분자 유지

기존 패턴에 있던 `/` 구분자를 low-priority delimiter로 유지한다. 제거 시 회귀 테스트로 영향 확인.

### 6.7 호환성

- `ProcedureParser.segmenter.split()` 인터페이스 변경 없음
- 기존 `>` 기반 테스트 전부 통과 필수

---

## 7. YAML Export (Issue 5)

### 7.1 CLI 구조

공식 CLI는 `export-mmi`, preview는 `--dry-run`:

```bash
# preview (파일 생성 없음)
python -m src.cli export-mmi TC_1.xlsx --sheet "SS-TC 1" --dry-run

# 실제 export
python -m src.cli export-mmi TC_1.xlsx --sheet "SS-TC 1" \
    --output-dir exported/ --only-class FULL_AUTO
```

기존 `preview-mmi`는 alias로 유지 가능하나 공식 기준 명령은 `export-mmi`.

### 7.2 기본 export 정책: fail-fast

- unrunnable TC가 하나라도 발견되면 export 전체를 중단하고 Exit Code 1 반환
- 사용자 명시 옵션:
  - `--skip-unrunnable`: unrunnable TC 제외하고 나머지만 export
  - `--export-unrunnable`: placeholder/warning 포함 상태로 export

Fail-fast 판정 순서:

1. 먼저 export 대상 필터를 적용한다.
   - `--only-class`
   - `--include-semi`
   - 기타 class 관련 필터
2. 필터 적용 후 실제 export 대상 집합을 확정한다.
3. 그 대상 집합에 대해 runnable 여부를 검사한다.
4. 기본 정책에서는 unrunnable TC가 하나라도 있으면 export 전체를 중단하고 Exit Code 1을 반환한다.

즉, export 대상이 아닌 TC의 unrunnable 상태 때문에 전체 export가 중단되지는 않는다.
Abort 판정은 항상 **필터 적용 후 최종 export 대상 집합**을 기준으로 한다.

### 7.3 Export 대상 필터

```
--only-class FULL_AUTO          # 기본: FULL_AUTO만
--include-semi                  # SEMI_AUTO도 포함
--skip-unrunnable               # unrunnable 제외 후 계속
--export-unrunnable             # unrunnable도 export
--overwrite                     # 기존 파일 덮어쓰기
```

### 7.4 YAML 출력 구조

```yaml
name: TC-01_권한_미부여_기본_동작_확인
description: 권한 미부여 기본 동작 확인

metadata:
  source_file: TC_1.xlsx
  source_sheet: SS-TC 1
  source_row: 2
  automation_class: SEMI_AUTO
  runnable: false
  has_manual_steps: true
  has_shell_actions: true
  has_unresolved_params: true
  warnings:
    - "Step 2: package 파라미터 미해결"
    - "Step 3: EXTERNAL_EVENT — 보조폰에서 전화 필요"
  exported_at: "2026-04-03T15:30:00"

steps:
  - action: shell
    command: "am start -n {package}/{activity}"
    execution_mode: SHELL_AUTO
    step_role: ACTION
    compile_status: UNRESOLVED_PARAMS
    _unresolved_params: ["package", "activity"]

  - action: manual_pause
    execution_mode: EXTERNAL_EVENT
    step_role: ACTION
    description: "보조폰에서 DUT로 전화를 걸어주세요"
    manual_timeout: 300
    on_timeout: fail

  - action: verify_text
    text: "수신"
    execution_mode: UI_AUTO
    step_role: ASSERT
```

### 7.5 tc_loader 호환성

- `manual_pause`를 `VALID_ACTIONS`에 추가
- `manual_pause`에 대한 action-specific validation 지원
  - required: `description`
  - optional: `execution_mode`, `step_role`, `manual_timeout`, `on_timeout`, `allow_skip`
- `metadata`, `execution_mode`, `step_role`, `compile_status`, `_unresolved_params` 필드를 optional로 허용
- 단, permissive validation이라도 완전 무제한 허용은 아니며, 알 수 없는 핵심 필드는 warning 또는 validation error 대상으로 남긴다

### 7.6 파일명 정책

`source_row`를 파일명에 넣지 않는다 (행 삽입/삭제 시 파일명 대량 변경 → Git history 오염).

파일명 = `tc_name slug` + 내용 기반 short hash:
```
TC-01_권한_미부여_기본_동작_확인_a8f2.yaml
```

hash는 `tc_name + source_procedure + source_expected` 조합 기반.

### 7.7 runnable 판정

unresolved params만이 아니라 넓은 기준:
- `compile_status == "UNRESOLVED_PARAMS"`
- placeholder command 존재 여부
- 치명 warning 존재 여부 (`shell_mapping_missing` 등)
- compiled steps 비정상적으로 비어 있는 경우
- `manual_pause` step에 필수 필드 누락

기준: "현재 tc-runner가 이 YAML을 의미 있게 실행할 수 있는가"

### 7.8 Overwrite 정책

- 기본: 기존 파일 존재 시 skip + warning
- `--overwrite` 옵션으로 덮어쓰기 허용

### 7.9 Export 요약 출력

```
Export aborted: unrunnable TC 2개 발견
  생성      : 8개
  unrunnable : 2개
  경고 포함 : 3개
  종료 코드 : 1

힌트:
  --skip-unrunnable         제외하고 계속 진행
  --export-unrunnable       placeholder 포함 export
```

---

## 8. 제한사항

1. **adb.shell() 반환값**: 현재 returncode/stderr를 보존하지 않음. shell action 확장 시 실행 성공/실패 판정이 취약할 수 있음.
2. **자연어 파라미터 추출**: package, permission 등 구체 값을 자연어에서 안정적으로 추출하기 어려움. placeholder + 수동 보완이 현실적 전략.
3. **grant/revoke permission**: Android 버전/권한 종류에 따라 제약 존재.
4. **기존 MMITCClassifier**: 당분간 유지하되 향후 StepClassifier 기반 집계로 대체 가능.
5. **Alias Registry 필요성**: package / permission / settings menu의 자연어 표현과 Android 시스템 식별자 간 번역 계층이 충분히 준비되지 않으면 placeholder 생성 비율이 높아질 수 있다. 초기 구현 단계에서 alias registry를 병행 구축하는 것이 권장된다.
