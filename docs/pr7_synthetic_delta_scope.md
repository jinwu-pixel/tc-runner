# PR 7 — Synthetic Delta Measurement (Scope)

**Status:** SCOPE PROPOSAL; repo-fixed at `e35bf65`; no code change; implementation not started.
**Adoption Order context:** v2 Adoption Order 4단계 (PR 6 git audit 트랙 종료 후, Tier 정의·자동화 *전*)
**PR 6 track closure:**
- PR 6A `5e6a2b8` — `tools/git_safe_push_audit.py` JSON audit + 10 tests
- PR 6B `3dd761a` — Markdown formatter + `derive_push_command` + 8 tests (총 18 tests)
- PR 6C scope `80c0d04` / plan `af43c48` / impl `eca3104` — retrospective + drift baseline 3 tests (총 21 tests)

본 문서는 *PR 7 scope*만 정의한다. fixture/측정 코드 구현 및 plan 단계 진입은 본 commit과 분리된다.

---

## 1. Purpose

catalog/delta verdict의 신뢰성을 작은 synthetic fixture로 정량 검증한다.

목표:

- Music Phase 1에서 반복적으로 사용된 delta 분류(`delta insufficient` / `non_target_context` / `expected screen change` 등)가 실제로 noise와 의미 변경을 분리하는지 측정
- cold launch / 동일 화면 재진입에서 XML hash·visible_texts 변화량 baseline 확립
- v2 Adoption Order 4단계 진입 전 delta 계층의 실증 baseline 확보
- PR 8 anchor recommender 설계 입력 데이터 마련

PR 7은 **측정 scope**다. Tier 자동화 적용도, 운영 변경도 아니다.

---

## 2. Non-goals

본 PR 7이 **하지 않는** 일:

- **policy v2 운영 적용 아님** — proposal `b4552c4` repo-fixed 그대로 보류
- **Tier 0 자동 진행 적용 아님** — synthetic 측정만, 자동 promote 없음
- **PR 8 anchor recommender 구현 아님** — recommender 설계는 별도 PR
- **Git audit 도구 변경 아님** — `tools/git_safe_push_audit.py` 변경 0
- **TC YAML 대량 변경 아님** — golden_tc_set / exported_tc1 / ODIN2 testdata 변경 0
- **runner runtime 구조 변경 아님** — `cli run` / `load_tc` / runtime catalog 영향 없음
- **generated/probe/catalog/reports commit 허용 아님** — 영구 비커밋 정책 그대로 유지
- **실기 device run 강제 아님** — synthetic fixture는 XML/text 입력만으로 평가
- **full Music app corpus 재측정 아님** — synthetic 3~5개 제한
- **flakey UI 자동 안정화 프레임워크 구축 아님** — measurement scope 한정
- **JSON schema 변경 아님** — 본 PR 7은 별도 schema 정의 (delta 측정 schema는 별도)

---

## 3. Problem statement

Music Phase 1(SMOKE_01~06) 진행 중 delta는 다음과 같은 분류로 반복 사용되었다:

- `delta insufficient` — 화면 텍스트가 부족해 anchor 변화 확인 불가
- `non_target_context` — 변화는 있으나 target 외 영역(노이즈, 광고 배너, 무관 팝업)
- `expected screen change` — 의도한 transition (탭 전환, 화면 진입)
- `stable` — 의미 있는 변화 없음

문제:

- 위 분류가 실제 변경과 noise를 얼마나 분리하는지 **정량 baseline이 없다**
- cold launch 시 XML hash가 동일/상이한 빈도, visible_texts Jaccard 분포 baseline 없음
- `delta insufficient`와 `non_target_context` 의 재현성 검증 없음
- Tier 정책에서 delta verdict를 자동화 입력으로 사용하기 전 신뢰도 baseline 필요

---

## 4. Synthetic fixture scope

### 4-1. Fixture set (3~5개 제한)

각 fixture는 *XML pair (before/after)* + *expected verdict* 형태로 구성한다.

후보 분기:

1. **identical snapshot pair**
   - before == after (XML 동일)
   - expected: `stable`, no meaningful delta

2. **text-only change (target anchor 변화)**
   - 동일 layout, target text 1개 추가/변경
   - expected: `expected screen change` 또는 meaningful delta with `changed_texts` 감지

3. **non-target context change (noise)**
   - target 외 영역(banner/popup/unrelated tab badge) 변경
   - target anchor presence 그대로
   - expected: `non_target_context` 또는 WARN

4. **insufficient evidence**
   - visible_texts 매우 적음 (예: blank loading 화면), target anchor 부재
   - expected: `delta insufficient`

5. **expected target transition**
   - 화면 자체가 다른 컨텍스트로 이동 (예: Home → Favorite tab)
   - target anchor가 명백히 변경
   - expected: meaningful delta, target screen identified

scope에서 fixture 수는 **최대 5개로 제한**한다. implementation에서 fixture가 비대해지면 plan 단계에서 중단·재계획.

### 4-2. Fixture input format

후보:

- 작은 raw `uiautomator dump` XML (실 단말 capture가 아닌 *손으로 작성한 최소 reproducer*)
- 또는 합성된 minimal Android UI XML (복잡도 최소, target text/resource-id만 포함)

원칙:

- fixture는 가능한 작게 유지
- repo에 둘지 여부는 plan 단계에서 별도 판단 (기본 안: `tests/fixtures/delta/<name>/before.xml` `after.xml`)
- 실제 device dump는 fixture로 사용하지 않는다 (PII / app-version drift 위험)

### 4-3. Fixture exclusions

다음은 PR 7 fixture로 **포함하지 않는다**:

- 실제 단말 dump (probe_*.xml, catalog/*.xml)
- ODIN2 Music/MyGallery/MiniFile capture
- 광고/지역화 텍스트 의존 fixture
- 대용량 XML (>500 라인)
- 외부 SDK overlay 의존 fixture

---

## 5. Measurement metrics

PR 7 scope는 metric **정의만** 한다. 구현은 별도 plan.

후보 metric:

| metric | 정의 | 용도 |
|--------|------|------|
| `xml_sha256_equal` | before/after XML SHA256 hash 동일 여부 | 무변화 빠른 감지 |
| `visible_texts_count_before` | before 단계 visible texts 개수 | insufficient evidence 분류 입력 |
| `visible_texts_count_after` | after 단계 visible texts 개수 | 동일 |
| `visible_texts_jaccard` | Jaccard similarity (before texts ∩ after texts) | 의미 변경 정도 |
| `added_texts` | after-only texts 목록 | 신규 anchor 후보 |
| `removed_texts` | before-only texts 목록 | 사라진 anchor |
| `target_anchor_presence_before` | 사용자가 expected target text 지정 시 before 존재 여부 | target 식별 |
| `target_anchor_presence_after` | 동일, after | target transition 검증 |
| `expected_text_present` | scope 사용자가 지정한 expected_text 위치 |  positive/negative |
| `forbidden_noise_text_present` | banner/popup/광고 등 noise text 존재 | non_target_context 분류 입력 |
| `verdict` | `stable` / `meaningful_delta` / `non_target_context` / `insufficient` 중 하나 | 종합 분류 |
| `false_positive_examples` | 측정 verdict가 expected와 다른 경우 sample | implementation feedback |
| `false_negative_examples` | 동일, 누락 케이스 | implementation feedback |

metric 정의 자체는 PR 7 scope에 명시. 알고리즘·구현 디테일은 plan에서 결정.

---

## 6. Output

### 6-1. JSON (machine-readable)

후보 형식 (구현 단계에서 확정):

```json
{
  "schema_version": 1,
  "tool_version": "pr7-delta-measurement-v1",
  "run_id": "<timestamp>",
  "fixtures": [
    {
      "name": "identical_snapshot",
      "expected_verdict": "stable",
      "actual_verdict": "stable",
      "metrics": {
        "xml_sha256_equal": true,
        "visible_texts_jaccard": 1.0,
        "added_texts": [],
        "removed_texts": []
      },
      "match": true
    }
  ],
  "summary": {
    "total": 5,
    "matched": 5,
    "false_positive": 0,
    "false_negative": 0
  }
}
```

### 6-2. Markdown (human-readable)

후보 섹션:

- 헤더: 1 line PASS/FAIL summary
- Fixture table: name / expected / actual / match
- False positive / negative samples
- Recommendation (e.g., threshold 후보값)

### 6-3. Generated artifact policy

- JSON / Markdown 출력은 **commit 금지** (영구 비커밋 정책)
- `reports/pr7_delta_measurement/<run_id>/` 같은 경로는 generated. forbidden path 정책에 포함 (PR 6 §4 그대로)
- fixture input(`tests/fixtures/delta/<name>/*.xml`)은 commit 가능 후보 — plan에서 결정

---

## 7. Acceptance criteria

본 PR 7 scope acceptance:

- [ ] synthetic fixture 3~5개 제한 명시
- [ ] verdict 분기별 expected 1개 이상 정의
- [ ] metric 후보 표 제공
- [ ] generated artifact commit 금지 유지
- [ ] PR 6 git audit과 역할 분리 (scope drift baseline은 PR 6C, delta verdict 측정은 PR 7)
- [ ] PR 8 anchor recommender와 역할 분리 (recommender 설계는 PR 8)
- [ ] policy v2 적용 없음
- [ ] implementation 진입 전 plan 단계 필수
- [ ] cross-platform 동작 (Windows + POSIX) — fixture XML, hash 계산 모두 path-agnostic
- [ ] **실기 device run 강제 없음** — synthetic 입력만으로 평가 가능

---

## 8. Risks

| Risk | 설명 | 완화 |
|------|------|------|
| **synthetic fixture overbuild** | fixture가 실 화면을 흉내 내려다 비대화 | 3~5개 제한, layout 복잡도 최소 |
| **real device behavior와 fixture 간 괴리** | synthetic에서 PASS여도 실기에선 noise로 false positive | scope에 "synthetic은 baseline일 뿐 실기 대체 아님" 명시 |
| **XML hash 과의존** | hash 동일 = stable 단정은 위험 (timestamp/dynamic id 차이) | `visible_texts_jaccard` 보조 metric 도입, scope에서 hash-only 단정 금지 |
| **Jaccard threshold 임의성** | 0.8/0.9 등 threshold는 근거 없는 임의값 위험 | scope에서는 metric만 정의, threshold는 plan 단계에서 fixture 결과 보고 결정 |
| **delta verdict false confidence** | "5/5 match"라 해도 fixture 5개로 일반화 위험 | "small synthetic baseline" 명시, full corpus는 별도 |
| **PR 8 scope creep** | recommender 설계까지 끌고 가려 함 | anchor recommendation은 PR 8 scope, PR 7은 측정만 |
| **generated artifact 오염** | 측정 reports를 commit 시도 | PR 6 §4 forbidden path 정책 그대로 적용, `reports/pr7_*` 경로 차단 |
| **fixture 입력으로 실기 dump 사용** | PII / app-version drift / 비대화 | fixture는 손으로 작성한 minimal reproducer만 |

---

## 9. Recommendation

권고:

- **PR 7은 작게 간다** — scope → implementation plan → small implementation 순서.
- 첫 implementation은 **fixture 3~5개 + metric 계산 + JSON/Markdown 출력**만.
- full Music corpus / 실기 device 반복 측정은 **defer**.
- PR 7 완료 전 **policy v2 Tier 자동화 적용 금지**.
- threshold 결정은 fixture 측정 결과를 본 뒤 plan 보강에서 수행.

---

## 10. Out-of-scope deferred

다음은 PR 7 **out-of-scope** — 별도 PR/scope:

- PR 8 anchor recommender 구현 — 별도
- full Music corpus retrospective delta 측정 — defer 후보 (PR 7+1)
- 실기 device 반복 측정 — defer
- catalog 자동 갱신 — v2 §9 영역, 별도
- delta verdict가 cli runtime을 차단/경고하는 통합 — 별도 결정
- pre-commit hook delta 검증 — 별도
- CI 통합 — 별도
- threshold 자동 튜닝 — defer

---

## 11. Decision boundary

본 scope 문서를 commit하는 시점에 적용되는 단독 범위:

### Commit candidate

- `docs/pr7_synthetic_delta_scope.md` (only)
- (option) `docs/pr6c_git_audit_retrospective_scope.md` — Status 라인 정정만
- (option) `docs/pr6c_git_audit_retrospective_implementation_plan.md` — Status 라인 정정만

### Excluded

- `tools/` 전체 (구현은 별도 PR)
- `tests/` 전체 (테스트 fixture는 별도 PR)
- `src/` / schema / runner_capability / tc_prompts / TC YAML / golden_tc_set / exported_tc1 / ODIN2 testdata
- `docs/tc_template.yaml` / `docs/tc_writing_guide.md`
- generated / probe / catalog / reports / `_probe_*.py` / `*.png` / `popup_*.xml` / `ui_*.xml` / `probe_dump_*.xml`
- PR 8 anchor recommender 시작 0
- policy v2 운영 적용 0

### Pre-commit verification

- staged file은 **명시적으로 지정된 docs 파일만** 허용 (1 + optional 2 = 최대 3)
- src/schema/runner/tests/tools 변경 0
- generated 산출물 staged 0
- ahead/behind audit 통과 (fast-forward only)
- force / force-with-lease 사용 0

### Adoption note

본 commit은 *scope 문서를 repo에 고정하는 행위*에 한정한다. **PR 7 구현 진입은 별도 결정**이며 본 commit과 분리된다. PR 7 implementation plan 작성 → implementation 승인 → 코드/테스트 변경 순서를 따른다.
