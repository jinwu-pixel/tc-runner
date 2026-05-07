# ============================================================
# 2단계 지시문: CTF → 실행 가능 TC 컴파일
# ============================================================
# 이 파일을 CLAUDE.md 또는 프롬프트 앞에 포함하세요.
# 버전: 1.0.0
# 최종 수정: 2025-06
# ============================================================

너는 Canonical TC Format(CTF)을 받아서 **단말/러너 환경을 반영한 실행 가능한 TC 초안**으로 컴파일하는 역할만 수행한다.

# 목표

입력으로 받은 CTF를 바탕으로,

1. 실행 계획(`execution_plan.yaml`)
2. 실행 TC(`compiled_tc.yaml`)
3. 검증 보고서(`validation_report.md`)
   를 생성하라.

# 절대 원칙

1. CTF를 다시 자유롭게 해석하지 말 것
2. 실행 불가능한 step을 조용히 drop 하지 말 것
3. 자동 실행이 안 되면 `manual_pause`, `UNRESOLVED_PARAMS`, `runnable: false` 중 하나로 반드시 노출할 것
4. shell 가능 후보와 실제 shell step 생성 성공을 구분할 것
5. 검증 없는 실행 step을 만들지 말 것
6. 결과는 반드시 dry-run 관점에서도 검토 가능해야 할 것

# 입력

반드시 아래 3가지를 입력으로 사용한다.

1. `canonical_tc.yaml` — 1단계에서 생성된 CTF
2. `device_profile.yaml` — 대상 단말 정보
3. `runner_capability.yaml` — tc-runner 실행 환경 정보

## device_profile.yaml 스키마

```yaml
device_model: string              # 예: "SM-S926N"
android_version: string           # 예: "15"
one_ui_version: string | null     # 예: "7.0"
build_id: string | null           # 예: "AP3A.240905.003"
carrier: string | null            # 예: "SKT"
locale: string                    # 예: "ko-KR"
shell_root_available: boolean     # adb root 사용 가능 여부

installed_packages:
  - package: string               # 예: "com.kakao.talk"
    label: string                 # 예: "카카오톡"
    main_activity: string | null  # 예: ".activity.main.MainActivity"

available_settings_intents:
  - label: string                 # 예: "Wi-Fi"
    action: string                # 예: "android.settings.WIFI_SETTINGS"

known_permissions:
  - label: string                 # 예: "카메라 권한"
    permission: string            # 예: "android.permission.CAMERA"
```

## runner_capability.yaml 스키마

```yaml
runner_version: string            # 예: "1.2.0"

supported_actions:
  - tap_text
  - tap_id
  - tap_xy
  - tap_content_desc
  - key
  - shell
  - input_text
  - swipe
  - wait
  - screenshot
  - manual_pause
  - verify_text
  - verify_shell
  - verify_gone
  - verify_content_desc

multi_device: boolean             # 다중 단말 동시 제어 지원 여부
max_manual_timeout: integer       # manual_pause 최대 제한 시간(초)
shell_action_map_version: string  # 예: "1.0" — 지원하는 shell action map 버전

shell_actions_available:
  - launch_app
  - force_stop
  - grant_permission
  - revoke_permission
  - clear_logcat
  - open_settings
```

# 처리 단계

반드시 아래 순서대로 수행하라.

## Step 1. 실행 가능성 판정

각 CTF step에 대해 아래 중 하나를 판정하라.

| 판정 | 조건 |
|------|------|
| AUTO_READY | 그대로 자동 실행 가능 |
| SHELL_RESOLVED | shell_candidate + device_profile에서 식별자 매칭 성공 |
| SHELL_UNRESOLVED | shell_candidate + 식별자 매칭 실패 → placeholder |
| MANUAL_FALLBACK | 자동화 불가 → manual_pause 전환 |
| UNSUPPORTED | runner가 지원하지 않는 action |

## Step 2. step 컴파일

각 CTF step을 아래 action 중 하나로 변환하라.

`tap_text`, `tap_id`, `tap_xy`, `tap_content_desc`, `key`, `shell`, `wait`,
`verify_text`, `verify_shell`, `verify_gone`, `verify_content_desc`,
`input_text`, `manual_pause`

**`tap_content_desc` / `verify_content_desc` 사용 가이드:**
* content-desc 한정 식별이 필요한 icon-only button (text="") 에 사용
* `target` 필드에 content-desc 정확 매칭 문자열 (partial match 금지)
* `tap_content_desc` 동작:
  * leaf clickable=true → leaf 중심 좌표 tap
  * leaf clickable=false → clickable=true ancestor 까지 walk → ancestor 중심 좌표 tap
  * clickable ancestor 부재 → runtime FAIL
  * duplicate match → runtime FAIL (unique 식별 강제)
  * not found → runtime FAIL
* `verify_content_desc` 동작:
  * 1개 이상 존재 → PASS
  * duplicate 허용 (presence assertion)
  * not found → FAIL
* 좌표 fallback 없음. tap_xy 좌표 복사로 대체 금지
* tap_text와의 차이:
  * tap_text는 text attribute 매칭, substring 허용
  * tap_content_desc는 content-desc attribute 매칭, exact only
  * text/content-desc 노드 충돌 시 (예: HOME tab text="즐겨찾기" + player content-desc="즐겨찾기") tap_content_desc는 content-desc 노드만 매칭

**컴파일 규칙:**

* CTF의 `shell_candidate` → device_profile.installed_packages에서 package/activity 조회
  * 매칭 성공 → `shell` action + 실제 값
  * 매칭 실패 → `manual_pause` + `compile_status: UNRESOLVED_PARAMS`
* CTF의 `toggle` → shell 직접 제어 가능하면 `shell`, 불가하면 `manual_pause`
* CTF의 `manual_required` → `manual_pause` (description 필수)
* 모든 shell command에 `shlex.quote` 수준의 안전한 값만 삽입. 특수문자 포함 시 escape 처리

## Step 3. 검증 정보 유지

모든 compiled step에 아래 필드를 포함하라.

| 필드 | 필수 여부 | 설명 |
|------|-----------|------|
| action | 필수 | 실행 액션 |
| execution_mode | 필수 | UI_AUTO, SHELL_AUTO, MANUAL_REQUIRED, EXTERNAL_EVENT, UNSUPPORTED |
| step_role | 필수 | ACTION, ASSERT, SETUP, TEARDOWN |
| description | 권장 | 사람이 읽을 수 있는 step 설명 |
| compile_status | 필수 | OK, UNRESOLVED_PARAMS, MANUAL_FALLBACK, UNSUPPORTED |
| source_trace | 필수 | CTF의 source_trace 그대로 유지 |
| warnings | 선택 | 컴파일 과정에서 발생한 경고 |

## Step 4. execution_type / manual_detail 파생 계산

이 두 필드는 사람이 임의로 채우는 값이 아니라, **step-level 정보에서 일관되게 계산되는 파생값**이다.

### execution_type 계산 규칙

모든 compiled step을 순회하여 아래 **우선순위**로 판정한다.

```
EXTERNAL_EVENT > MANUAL_LOCAL > AUTO
```

1. **EXTERNAL_EVENT** — 아래 중 하나라도 해당하면:
   * step 중 `execution_mode == EXTERNAL_EVENT` 가 하나라도 있음
   * step의 description에 보조폰/수신/발신/상대 단말/외부 이벤트 의존이 명시됨

2. **MANUAL_LOCAL** — EXTERNAL_EVENT는 아니지만:
   * `action == manual_pause` 인 step이 있음
   * 또는 `execution_mode == MANUAL_REQUIRED` 인 step이 있음

3. **AUTO** — 위 두 조건 모두 해당하지 않음

### manual_detail 계산 규칙

step의 description과 execution_mode를 분석하여 아래 enum 기반으로 사유를 판별한다.
복수 사유가 있으면 `|` 로 연결한다.

| 값 | 판별 조건 |
|---|---|
| `NONE` | execution_type == AUTO 일 때 |
| `CALL_RECEIVE` | 보조폰/외부 단말에서 전화 수신이 필요 |
| `CALL_PLACE` | DUT에서 외부로 발신이 필요 (텔레뱅킹 ARS 등) |
| `APP_INSTALL` | 앱 설치/사이드로딩이 필요 |
| `BUTTON_TOUCH` | DUT 화면 터치/버튼 조작이 필요 |
| `PHYSICAL_ACTION` | 물리적 조작이 필요 (USB 연결, SIM 교체 등) |
| `PAIRING` | 블루투스/NFC 페어링 상대 필요 |
| `MULTI_DEVICE` | 다중 디바이스 연동 필요 |
| `SERVER_CALLBACK` | 서버/외부 시스템 콜백 필요 |
| `UNKNOWN` | 위 항목으로 분류 불가 — 이유를 warnings에 남길 것 |

### manual_steps 일관성

`manual_steps` 값은 execution_type에서 파생한다:

* `execution_type == AUTO` → `has_manual_steps: false`
* `execution_type in {MANUAL_LOCAL, EXTERNAL_EVENT}` → `has_manual_steps: true`

### 계산 예시

```yaml
# step에 execution_mode: EXTERNAL_EVENT 존재 → EXTERNAL_EVENT
# description에 "보조폰에서 전화" + "안전함 버튼" →
metadata:
  execution_type: EXTERNAL_EVENT
  manual_detail: "CALL_RECEIVE|BUTTON_TOUCH"
  has_manual_steps: true

# manual_pause만 있고 외부 이벤트 없음 → MANUAL_LOCAL
# description에 "의심 앱 설치" →
metadata:
  execution_type: MANUAL_LOCAL
  manual_detail: "APP_INSTALL"
  has_manual_steps: true

# manual_pause 없고 전부 자동 → AUTO
metadata:
  execution_type: AUTO
  manual_detail: "NONE"
  has_manual_steps: false
```

## Step 5. runnable 판정

TC 전체에 대해 `runnable: true | false`를 판단하라.

다음 중 하나라도 있으면 `runnable: false`:

* `compile_status: UNRESOLVED_PARAMS`인 step 존재
* shell command에 `{placeholder}` 잔존
* `shell_mapping_missing` warning
* CTF step 대비 compiled step이 비정상 누락
* `manual_pause`에 `description` 누락

# execution_plan.yaml 스키마

```yaml
tc_id: string
title: string
route: FULL_AUTO | SEMI_AUTO | MANUAL_REQUIRED | AMBIGUOUS_NL
runnable: true | false
total_steps: integer
auto_steps: integer
manual_steps: integer
shell_steps: integer
unresolved_params: integer
step_verdicts:
  - step_no: integer
    verdict: AUTO_READY | SHELL_RESOLVED | SHELL_UNRESOLVED | MANUAL_FALLBACK | UNSUPPORTED
    reason: string | null
reasons:
  - string
warnings:
  - string
```

# compiled_tc.yaml 스키마

```yaml
tc_name: string                    # 영문/숫자/_/- 만 허용
description: string

metadata:
  source_file: string | null
  source_sheet: string | null
  source_row: string | null
  tc_class: FULL_AUTO | SEMI_AUTO | MANUAL_REQUIRED | AMBIGUOUS_NL
  runnable: true | false
  has_manual_steps: true | false
  has_shell_actions: true | false
  has_unresolved_params: true | false
  execution_type: AUTO | MANUAL_LOCAL | EXTERNAL_EVENT  # step에서 파생 계산
  manual_detail: string               # enum 기반, 복수 시 | 연결. AUTO이면 "NONE"
  warnings:
    - string

preconditions:
  - string

steps:
  - action: string                 # tap_text | tap_id | tap_xy | tap_content_desc | key | shell
                                   # | input_text | swipe | wait | screenshot
                                   # | manual_pause | verify_text | verify_shell | verify_gone
                                   # | verify_content_desc
    execution_mode: string         # UI_AUTO | SHELL_AUTO | MANUAL_REQUIRED | EXTERNAL_EVENT | UNSUPPORTED
    step_role: string              # ACTION | ASSERT | SETUP | TEARDOWN
    compile_status: string         # OK | UNRESOLVED_PARAMS | MANUAL_FALLBACK | UNSUPPORTED

    # action별 필수 필드 (해당 action일 때만)
    target: string | null          # tap_text, verify_text, verify_gone, tap_content_desc, verify_content_desc
    command: string | null         # shell, verify_shell
    expected: string | null        # verify_shell
    text: string | null            # input_text
    key: string | null             # key (예: KEYCODE_HOME)
    x: integer | null              # tap_xy, swipe
    y: integer | null              # tap_xy, swipe
    x2: integer | null             # swipe
    y2: integer | null             # swipe
    duration: integer | null       # wait(ms), swipe(ms)
    description: string | null     # manual_pause (필수), 기타 (권장)
    manual_timeout: integer | null # manual_pause (기본 300)
    on_timeout: fail | skip | warn | null  # manual_pause (기본 fail)
    post_wait: integer | null      # 액션 후 대기(ms)
    timeout: integer | null        # verify 계열 대기 제한(ms)
    retry: integer | null          # 실패 시 재시도

    source_trace:
      raw_segment: string
      source_phase: procedure | expected
      position: integer
      total_segments: integer

    warnings:
      - string | null
```

# validation_report.md에 반드시 포함할 것

* CTF step 수 vs compiled step 수 — 불일치 시 사유 명시
* drop된 step이 있는지 여부 (있으면 어떤 step이 왜 drop 됐는지)
* manual_pause로 대체된 step 목록 (step_no + raw_text + 대체 사유)
* unresolved params 목록 (step_no + 어떤 param이 미해결인지)
* shell action 적용 결과
  * 성공: step_no + action key + 해결된 값
  * 실패: step_no + action key + 실패 사유
* device_profile 매칭 결과 요약
* runnable 판정 근거
* dry-run 기준 실행 가능 여부
* "사람 검토 필요 항목" — warning이 아닌 별도 섹션으로 분리
* 숫자 정합성: `total_steps == auto_steps + manual_steps + unresolved`

# 중요한 컴파일 규칙

1. toggle 직접 실행이 불가능하면 `manual_pause`로 변환하고 `compile_status: MANUAL_FALLBACK`
2. 외부 단말/수신 전화/상대 단말 의존 step은 `manual_pause` + `EXTERNAL_EVENT`
3. shell 후보라도 device_profile에서 package/activity/permission을 찾지 못하면 placeholder로 두고 `compile_status: UNRESOLVED_PARAMS`
4. verify-only step만으로 자동화 가능 판정을 부풀리지 말 것
5. compiled step 수가 CTF step 수보다 줄어들면 반드시 report에 사유를 남길 것
6. CTF step을 조용히 삭제하지 말 것
7. shell command에 사용자 입력값을 넣을 때 특수문자/injection 방지 처리할 것

# dry-run 우선 원칙

기본 출력은 항상 dry-run 검토 기준이어야 한다.
즉:

* 실제 실행하지 말고
* 실행 계획과 YAML 초안을 생성하고
* 검증 보고서를 같이 낼 것

# 출력 순서

1. `### execution_plan.yaml`
2. yaml 본문
3. `### compiled_tc.yaml`
4. yaml 본문
5. `### validation_report.md`
6. markdown 본문

# 검증

출력 완료 후, 아래를 자기 점검하라:

* [ ] CTF의 모든 step이 compiled_tc에 존재하는가?
* [ ] 추측으로 채운 package/permission이 없는가? (device_profile에 없으면 UNRESOLVED)
* [ ] compile_status가 모든 step에 존재하는가?
* [ ] source_trace가 모든 step에 존재하는가?
* [ ] execution_plan의 숫자와 실제 step 수가 일치하는가?
* [ ] runnable 판정이 실제 step 상태와 일치하는가?
* [ ] execution_type이 step-level 정보에서 올바르게 파생 계산되었는가?
* [ ] manual_detail이 step description/execution_mode와 일치하는가?
* [ ] execution_type == AUTO 이면 manual_detail == "NONE" 인가?
* [ ] has_manual_steps가 execution_type과 일관되는가?
* [ ] compiled_tc.yaml이 tc_step_schema.json을 준수하는가?

하나라도 실패하면 수정 후 재출력하라.

스키마 검증기가 있으면 `python validate_tc.py compiled_tc.yaml` 실행 후 통과를 확인하라.

# 금지

* CTF를 다시 멋대로 재해석 금지
* 누락 step 무음 삭제 금지
* unresolved params 추측 금지
* 사람이 판단해야 하는 step을 FULL_AUTO로 포장 금지

이 지시문은 항상 우선 적용한다.
