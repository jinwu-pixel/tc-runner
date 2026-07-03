# ============================================================
# 1단계 지시문: TC → Canonical TC Format (CTF) 정규화
# ============================================================
# 이 파일을 CLAUDE.md 또는 프롬프트 앞에 포함하세요.
# 버전: 1.1.0
# 최종 수정: 2026-07
# 변경: 1.1.0 — "ALT Basic F0 taxonomy 환류" 6건 (mutation 의미 판독 · 암묵 fixture 역산 게이트 ·
#         verifier 실행가능성 등급 · press_key subtype 판별 · focus_state CTF 스키마 · 자동분류 확정권한 금지)
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
8. 자동 cue·휴리스틱만으로 **자동화 적합/부적합을 확정 판정하지 말 것**. 자동 cue의 오류율은 양방향 모두 높다(false-pass·과배제) — cue는 후보 신호일 뿐 확정 근거가 아니다. 단, 무단말로 확정 가능한 판정(명시 하드웨어 키의 keycode 확정[규칙13], 진짜 비자동화 신호의 infeasible 분기[규칙12], tc_class 부여)은 허용된다. mutation·자동화 여부가 애매하면 `ambiguous`로 남겨라.

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
    implicit_fixture_suspected: true | false
        # 절차 step이 스스로 확립하지 않는(진짜 선존재) 데이터/상태 — 전제 데이터(사진·연락처·녹음·알람)나
        # 사전 화면 상태를 요구하면 precondition 공란이라도 true. (통상 앱 진입·홈 위치 등 절차가 스스로
        # 만드는 상태는 제외 — 이것까지 true로 몰지 말 것.)
        # blocking: harness가 safe-fixture 사이클(생성→관찰→정리, 잔존 0)로 자동 seed 가능하면
        #   blocking: false + SETUP 요건 표기 / 사람 개입 필요 시에만 blocking: true (무조건 강제 아님).

procedure_steps:
  - step_no: integer
    raw_text: string             # 원문 그대로 보존
    normalized_intent:
      type: navigate | tap | toggle | press_key | input_text | wait
            | verify_text | verify_shell | shell_candidate
            | manual_required | unsupported
        # shell_candidate: 원문에 shell 실행 의도가 보이나 식별자 미확인
      key_subtype: keycode | selector_discovery | focus_candidate
                 | screen_present | focus_state | null
        # type이 press_key 후보일 때만 세분류. keycode(명시 하드웨어 키 — 방향키/확인/BACK/전원 등
        #   keycode 확정 가능)만 확정 press_key. bare 명사·화면 이동 표현·포커스/상태 참조는
        #   press_key 아님 → selector_discovery / focus_candidate / screen_present / focus_state.
        #   단일 명시 키(DPAD 등)는 STAGE1에서 keycode 확정 허용(무단말 확정 가능분).
        #   (주의: 'focus_state' 토큰은 3곳에서 층위별로 쓰인다 — 여기 key_subtype[step 의도],
        #    expected.type[verifier 타입], expected.feasibility[실행가능성 등급].
        #    key_subtype: focus_state로 재분류된 step은 expected에 type: focus_state 계약을 생성한다.)
      target: string | null
      value: string | null
      shell_hint: string | null  # shell_candidate일 때 추정 action key
                                 # (예: "force_stop", "launch_app", "clear_logcat")
                                 # 식별자가 없으면 이 필드만 남기고 추측하지 말 것
      mutation_risk: true | false | ambiguous
        # 이 step이 상태 변경(mutation)을 일으키는가. 결과문의 상태 변화 "의미"로 판독하라.
        #   대칭 주의 — 상태-유지(상태 변경을 가로질러 값이 지속됨=mutation) vs 표시-유지(값이 단지
        #   표시·판독됨=관찰)를 구분. 선언 동사 매칭만으로 판정 금지('유지된다/처리된다'·무동사 선택→적용).
        #   true는 입증 가능한 상태 변경에 한정 · 경계가 모호하면 ambiguous(true 아님).
        #   true면 자동화 시 fixture 생성→관찰→정리(잔존 0) 사이클이 필요할 수 있음을 advisory로
        #   표시한다(실제 runnable gate 소비는 트랙 B — 아래 "신호 소비 범위").
    expected:
      - type: verify_text | verify_shell | focus_state
            | manual_required | unsupported
        target: string | null
        value: string | null
        feasibility: text_literal | element_presence | focus_state
                   | screenshot | infeasible
            # verifier 실행가능성 등급 — 정규화 앞단에서 선분류. type 매핑:
            #   text_literal→verify_text · element_presence→verify_content_desc(또는 verify_gone) ·
            #   focus_state→focus_state · screenshot→screenshot axis(STAGE2 R5) · infeasible→manual_required/unsupported.
            #   ★element_presence·screenshot 등급을 verify_text로 정규화 금지(WARN35류 재발 방지).
            #   infeasible(색상·미명시 toast·진동·오디오·물리 LED·시각 판정·무동작 negative·
            #   외부효과·시간 의존)은 판정 비용 없이 manual_required/unsupported로 조기 분기.
        focus_model: node | list | device_confirm | null
            # type == focus_state 일 때만. 위젯 클래스 미상이면 device_confirm hedge.
        focus_assert: focus_move | invariant | boundary_stop | retained
                    | created | position | absent | null
            # type == focus_state 일 때만. STAGE1은 assert 계약만 남긴다 —
            #   실측 device_value(PENDING_F0)·literal_outcome은 STAGE2 컴파일이 backfill(STAGE1 필드 아님).
            #   ★list 모델 focus는 현 런너 미지원 → runnable 승격 금지(STAGE2 R7, 트랙 B).
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
10. **mutation 의미 판독**: expected 결과문의 상태 변화를 의미로 판독하라. 선언적 mutation 동사 목록 매칭만으로 "mutation 없음(관찰 전용)"을 판정하지 말 것 — 값 유지·묵시적 상태 전이·선택→적용 패턴도 mutation. `mutation_risk`에 반영하라.
11. **암묵 fixture 역산**: procedure/expected가 사전 데이터나 화면 상태를 전제하면 precondition 공란이라도 `implicit_fixture_suspected: true`로 표시하라. 전제 없이 자동 통과시키지 말 것.
12. **verifier 실행가능성 선분류**: 각 expected를 `feasibility` 등급으로 먼저 분류하라. `infeasible`(색상·진동·오디오·물리·외부효과·시간 의존)은 정규화 후반까지 끌지 말고 조기에 `manual_required`/`unsupported`로 분기하라.
13. **press_key 태깅 제한**: bare 명사·화면 이동 표현·포커스/상태 참조를 `press_key`로 태깅 금지. 명시적 하드웨어 키만 `press_key` + `key_subtype: keycode`. 그 외는 `key_subtype`으로 세분류하라.

> **신호 소비 범위**: `mutation_risk`·`implicit_fixture_suspected`·`feasibility`는 정규화 판정을 돕는 신호다. 현 파이프라인에서 STAGE2 runnable 판정이 이들을 소비하는 규칙은 **트랙 B(별도 설계)**다 — 본 트랙에서는 advisory이며 report/warnings에 보존한다. `focus_state`의 list 모델도 런너 미지원(트랙 B)이므로 runnable로 승격하지 말 것.

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
* [ ] press_key로 태깅한 step이 실제 명시 하드웨어 키인가? (bare 명사·화면·포커스 참조 아님)
* [ ] mutation을 일으키는 step에 mutation_risk가 표시되었는가? (선언 동사 매칭에만 의존하지 않았는가)
* [ ] 전제 데이터/상태를 요구하는 TC에 implicit_fixture_suspected가 표시되었는가?
* [ ] 각 expected에 feasibility 등급이 부여되고 infeasible이 조기 분기되었는가?
* [ ] focus 상태를 확인하는 expected가 verify_text가 아닌 focus_state로 정규화되었는가?

하나라도 실패하면 수정 후 재출력하라.

# 금지

* 최종 tc-runner YAML 바로 생성 금지
* package/activity/permission 추측 금지
* step 생략 금지
* "대충 동작할 것" 같은 표현 금지
* bare 명사·화면 이동·포커스 참조를 press_key로 태깅 금지
* 자동 cue/휴리스틱만으로 KEEP·확정 EXCLUDE 판정 금지 (후보 슬리밍 전용)
* 선언 동사 매칭만으로 "mutation 없음" 단정 금지

이 지시문은 항상 우선 적용한다.
