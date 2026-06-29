Status: handoff only, no implementation.
Base HEAD: 39bb45e
Do not claim +39 as automatic unlock.
Next STOP: focus_candidate adjudication measurement report only.

---

# Handoff — ALT Basic focus_candidate 61 adjudication measurement

> 새 세션/터미널에 아래 지시문을 그대로 붙여넣어 실행한다.
> 본 문서는 untracked carry (commit defer). 다음 세션에서 spec/plan/ledger 생성 시
> 중복 가능성 → 그때 "보존 가치 handoff" vs "임시 백업" 판단 후 stage 여부 결정.

```text
[세션 목표]
tc-runner ALT Basic batch10 — focus_candidate 61 adjudication ledger 작성.
목적은 NOT_A_KEY_SUBTYPE 레저에서 드러난 VERIFIER_FOCUS_CANDIDATE 61개를
무단말로 3분류하여, 실제로 +39 device-pilot eligibility 잠재량 중 어떤 TC가
high-confidence verify-point로 풀리는지 방어적으로 측정하는 것이다.

중요: 이 세션은 measurement/adjudication 단계다.
YAML/manifest 재분류는 하지 않는다. 코드/레저/요약 산출까지만 하고 STOP한다.

[현재 기준선]
repo: C:\Users\momen\Projects\tc-runner
HEAD: 39bb45e
commit 내용: NOT_A_KEY subtype ledger + eligibility cascade
상태: tracked dirty 0, origin 대비 ahead 1(39bb45e), push 보류
직전 검증: tests/ 965 passed, self_check=ok
push는 별도 승인 전 금지.

[STEP 0 — 상태 확인, read-only]
cd C:\Users\momen\Projects\tc-runner
git status -sb
git status --short
git log --oneline -5

확인:
- HEAD가 39bb45e 또는 그 위의 동일 트랙 commit인지 확인
- tracked dirty가 예상 밖이면 STOP
- untracked carry는 broad add 금지. 필요한 파일만 명시 path로 다룰 것
- push/commit은 하지 않음

[입력 SoT]
1. THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv
   - not_a_key_subtype == VERIFIER_FOCUS_CANDIDATE 인 61행
2. THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_CASCADE_2026-06-29.csv
   - focus_candidate_delta +39의 TC-level 근거 확인
3. scripts/altbasic_not_a_key_subtype_ledger.py
   - predecessor로 import 재사용 가능
4. docs/superpowers/specs/2026-06-29-altbasic-not-a-key-subtype-ledger-design.md
   - false-progress 금지, device-pilot eligibility 용어 유지

[핵심 설계 원칙]
- focus_candidate 61은 곧바로 verifier로 간주하지 않는다.
- 3분류:
  1. VERIFY_POINT_HIGH
     X focus가 expected/outcome 문맥상 "포커스 상태 확인/관측점"으로 읽힘.
     실행 step으로 보기 어렵고, verify-point로 denominator에서 제외 가능.
  2. NAVIGATE_TO_FOCUS
     X focus가 "그 위치로 이동/포커스 맞추기" 실행 의도로 읽힘.
     무단말 재분류 금지. selector/key/device-discovery 쪽 blocker로 유지.
  3. AMBIGUOUS_RETAIN
     문맥만으로 verify vs navigate를 결정할 수 없음.
     fail-closed 유지. 사용자 결정/단말 evidence 전까지 승격 금지.

- headline은 high-confidence VERIFY_POINT_HIGH만.
- 보고 용어는 device-pilot eligibility delta만 사용.
- PASS / RUNNABLE_NOW / validated 같은 runtime verdict로 쓰지 말 것.
- +39 전체를 자동 unlock으로 주장하지 말 것. "잠재량 중 high-confidence로 실제 인정 가능한 부분"만 산출.

[권장 진행]
1. brainstorming/spec 작성
   docs/superpowers/specs/2026-06-29-altbasic-focus-candidate-adjudication-ledger-design.md

   포함할 것:
   - 입력 61행 범위
   - 3분류 taxonomy와 precedence
   - high-confidence 조건
   - TC-level cascade 계산 방식
   - +39 잠재량과 실제 adjudicated_delta를 구분
   - non-goals: yaml/manifest mutation 0, device 0, reclassification 0
   - STOP 지점

2. plan 작성
   docs/superpowers/plans/2026-06-29-altbasic-focus-candidate-adjudication-ledger.md

   TDD task 예시:
   - load focus_candidate rows
   - classify_focus_candidate(row/context)
   - TC-level cascade 재계산
   - summary renderer + forbidden-word guard
   - golden fixture
   - real artifact generation
   - STOP report

3. 구현은 plan 승인 후
   신규 파일 권장:
   - scripts/altbasic_focus_candidate_adjudication_ledger.py
   - tests/test_altbasic_focus_candidate_adjudication_ledger.py
   - tests/fixtures/altbasic/focus_candidate_adjudication_golden.json

   출력 artifact 권장:
   - THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_LEDGER_2026-06-29.csv
   - THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_CASCADE_2026-06-29.csv
   - THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_SUMMARY_2026-06-29.md

[검증]
- 신규 테스트 GREEN
- 기존 NOT_A_KEY subtype 테스트 회귀 GREEN
- 가능하면 전체 tests/ 실행
- real manifest checks:
  - focus_candidate input rows == 61
  - predecessor baseline_eligible == 5 유지
  - prior focus_candidate_delta == +39 재현 또는 명시적으로 reconcile
  - summary 금지어 0
  - YAML/manifest/runner 변경 0

[STOP 조건]
아래 중 하나면 즉시 STOP하고 보고:
- focus_candidate rows != 61
- prior +39 potential을 재현 못 함
- high-confidence rule이 expected/outcome 문맥 없이 token만으로 과도하게 승격하려 함
- YAML/manifest 변경이 필요해짐
- tests 실패 원인이 classifier drift 또는 predecessor mismatch
- unexpected tracked dirty 발견

[완료 보고 형식]
- focus_candidate 61 분포:
  VERIFY_POINT_HIGH / NAVIGATE_TO_FOCUS / AMBIGUOUS_RETAIN
- TC-level:
  baseline eligible
  prior focus_candidate potential
  adjudicated high-confidence delta
  remaining blocked breakdown
- 생성 파일 목록
- 테스트 결과
- non-goals 준수:
  device 0, yaml/manifest/runner mutation 0, commit 0, push 0
- 다음 선택지:
  A. high-confidence subset 재분류 spec/plan
  B. ambiguous review
  C. selector/keycode discovery로 이동

[commit/push]
이번 세션도 기본은 commit defer.
commit은 사용자 "commit now" 명시 전 금지.
stage는 명시 path만. git add . / -A / 디렉토리 add 금지.
push는 별도 §7.2 audit + 명시 승인 전 금지.
```
