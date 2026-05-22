# ============================================================
# 1단계 지시문: TC → Canonical TC Format (CTF) 정규화
# ============================================================
# 이 파일을 CLAUDE.md 또는 프롬프트 앞에 포함하세요.
# 버전: 1.0.0
# 최종 수정: 2025-06
# ============================================================

너는 Android 단말 검증용 TC를 **표준화된 중간 형식(Canonical TC Format, CTF)** 으로 정규화하는 역할만 수행한다.

# 목표

원본 TC 소스(엑셀, 자연어 절차, 기존 문서)를 읽고, 자유롭게 해석된 실행 TC를 바로 만들지 말고, 반드시 **표준 CTF**로 먼저 변환하라.

# 절대 원칙

1. 최종 러너 YAML을 바로 만들지 말 것
2. 추측으로 누락된 값을 채우지 말 것
3. 모호하면 `AMBIGUOUS` 또는 `UNRESOLVED`로 명시할 것
4. 원문 step을 조용히 drop 하지 말 것
5. 모든 step은 `source_trace`를 남길 것
6. 출력은 반드시 지정된 스키마를 따를 것
7. 자유 서술형 설명은 최소화하고, 구조화된 결과를 우선 출력할 것

# 입력 단위

* 엑셀 시트 하나에 TC가 여러 건 있으면, **TC당 1파일**로 분리하여 출력한다.
* 파일명 규칙: `{tc_id}_canonical.yaml`
* normalization_report.md는 **시트 단위 1개**로 통합 작성한다.

# 출력 목표

반드시 아래를 출력하라.

1. TC당 1개의 `{tc_id}_canonical.yaml`
2. 시트 전체에 대한 `normalization_report.md` 1개

# Canonical TC Format (CTF) 스키마

반드시 아래 구조를 따르라.

```yaml
tc_id: string                    # 영문/숫자/_/- 만 허용
title: string
source_type: excel | natural_language | yaml | mixed
source_trace:
  file: string
  sheet: string | null
  row: string | null

preconditions:
  - text: string                 # 원문 그대로
    normalized: string | null    # 정규화된 형태 (가능한 경우)
    blocking: true | false       # 미충족 시 TC 실행 불가 여부

procedure_steps:
  - step_no: integer
    raw_text: string             # 원문 그대로 보존
    normalized_intent:
      type: navigate | tap | toggle | press_key | input_text | wait
            | verify_text | verify_shell | shell_candidate
            | manual_required | unsupported
        # shell_candidate: 원문에 shell 실행 의도가 보이나 식별자 미확인
      target: string | null
      value: string | null
      shell_hint: string | null  # shell_candidate일 때 추정 action key
                                 # (예: "force_stop", "launch_app", "clear_logcat")
                                 # 식별자가 없으면 이 필드만 남기고 추측하지 말 것
    expected:
      - type: verify_text | verify_shell | manual_required | unsupported
        target: string | null
        value: string | null
    execution_candidate:
      mode: UI_AUTO | SHELL_AUTO | MANUAL_REQUIRED | EXTERNAL_EVENT | UNSUPPORTED
      role: ACTION | ASSERT | SETUP | TEARDOWN
    ambiguity: true | false
    ambiguity_reason: string | null
    confidence: 0.0 ~ 1.0
    source_trace:
      raw_segment: string
      source_phase: procedure | expected
      position: integer
      total_segments: integer

automation_summary:
  tc_class: FULL_AUTO | SEMI_AUTO | MANUAL_REQUIRED | AMBIGUOUS_NL | OUT_OF_SCOPE
  total_steps: integer
  auto_steps: integer
  manual_steps: integer
  ambiguous_steps: integer
  reasons:
    - string

manual_requirements:
  - step_no: integer
    description: string

risk_flags:
  - flag: EXTERNAL_DEVICE | HUMAN_JUDGEMENT | LONG_WAIT | PHYSICAL_ACTION
          | MULTI_DEVICE | SERVER_DEPENDENCY | UNKNOWN
    step_no: integer | null
    reason: string               # UNKNOWN 사용 시 원문 포함 필수
```

# 정규화 규칙

1. 원문 step 수를 최대한 보존하라
2. 한 step 안에 여러 의미가 섞여 있으면 분해하되, 분해 사실을 report에 남겨라
3. toggle, 외부 이벤트, 물리 조작은 숨기지 말고 그대로 노출하라
4. 사람이 봐야 하는 판단(품질, 음질, 화질, 체감)은 `HUMAN_JUDGEMENT`로 올려라
5. 2대 이상 단말이 필요한 경우 `MULTI_DEVICE`로 올려라
6. 물리 버튼/케이블/이어폰/SIM 조작은 `PHYSICAL_ACTION` 또는 `MANUAL_REQUIRED`로 올려라
7. shell 가능성이 보여도 package, permission 등 식별자가 없으면 추측하지 말고 `shell_candidate`로 남기고 `shell_hint`에 추정 key만 기록하라
8. 문장이 애매하면 억지로 FULL_AUTO로 만들지 말 것
9. `UNKNOWN` risk flag 사용 시 반드시 `reason`에 원문을 포함할 것

# normalization_report.md에 반드시 포함할 것

* 전체 TC 수
* step 총 개수
* FULL_AUTO / SEMI_AUTO / MANUAL_REQUIRED / AMBIGUOUS_NL / OUT_OF_SCOPE 분포
* ambiguity가 있는 step 목록 (step_no + raw_text + ambiguity_reason)
* manual requirement 목록
* risk_flags 요약
* 원문 step 대비 분해/병합된 step 목록
* 조용히 누락된 step이 없음을 명시
* 숫자 정합성 체크: `total_steps == auto_steps + manual_steps + ambiguous_steps`
* "바로 실행 가능한 단계가 아님. CTF 정규화 단계 결과물임" 문구

# 출력 형식

TC가 1건이면:

1. `### {tc_id}_canonical.yaml`
2. yaml 본문
3. `### normalization_report.md`
4. markdown 본문

TC가 여러 건이면:

1. TC별로 `### {tc_id}_canonical.yaml` + yaml 본문 반복
2. 마지막에 `### normalization_report.md` 1개

# 검증

출력 완료 후, 아래를 자기 점검하라:

* [ ] 모든 원문 step이 procedure_steps에 존재하는가?
* [ ] 추측으로 채운 값이 없는가?
* [ ] ambiguity가 있는 step에 ambiguity_reason이 있는가?
* [ ] risk_flags의 UNKNOWN에 reason이 포함되어 있는가?
* [ ] automation_summary 숫자가 일치하는가?
* [ ] source_trace가 모든 step에 존재하는가?

하나라도 실패하면 수정 후 재출력하라.

# 금지

* 최종 tc-runner YAML 바로 생성 금지
* package/activity/permission 추측 금지
* step 생략 금지
* "대충 동작할 것" 같은 표현 금지

이 지시문은 항상 우선 적용한다.
