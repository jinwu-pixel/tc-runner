# PR 7 — Synthetic Delta Measurement (Implementation Plan)

**Status:** PLAN; not committed; no code change; implementation not started.
**Scope source-of-truth:** `docs/pr7_synthetic_delta_scope.md` (repo-fixed at `e35bf65`)
**PR 6 track closure:**
- PR 6A `5e6a2b8` — `tools/git_safe_push_audit.py` JSON audit + 10 tests
- PR 6B `3dd761a` — Markdown formatter + `derive_push_command` + 8 tests (총 18 tests)
- PR 6C scope `80c0d04` / plan `af43c48` / impl `eca3104` — drift baseline 3 tests (총 21 tests)
**Adoption Order context:** v2 Adoption Order 4단계 진입 (PR 6 종료 후, Tier 자동화 *전*)

본 문서는 *implementation plan*만 정의한다. fixture/측정 코드/테스트 변경은 별도 결정·별도 PR로 진행한다.

---

## 1. Implementation target

scope §1 목적을 충족하는 최소 측정 도구 1개 + fixture set 3~5개 + 단위 테스트.

본 plan은 implementation을 **3 단계로 분리**하여 진행한다 — full 5 fixture · Markdown report · threshold tuning을 한 번에 밀지 않는다.

### 1-1. PR 7A — small implementation (필수)

**범위:**

- XML visible text extraction (stdlib `xml.etree.ElementTree`)
- xml_sha256 / Jaccard / added·removed / target presence metric 계산
- JSON 출력 (stdout 한정, file write 금지)
- fixture **3개만** 우선 지원 (`identical_snapshot`, `text_only_change`, `insufficient_evidence`)
- 단위 테스트 (대표 verdict 분기 + read-only invariant)

**금지:**

- Markdown 출력
- file write (reports/ catalog/ 등 모두 금지)
- threshold 자동 튜닝
- 실기 dump fixture
- PR 8 / runner runtime / TC YAML / policy v2 / Tier 0 / git audit 변경

### 1-2. PR 7B — optional extension (defer)

**범위:**

- 나머지 fixture 2종 (`non_target_context`, `target_transition`) 추가 — 총 5개로 확장
- Markdown report 옵션 (`--format markdown`)
- threshold / verdict 알고리즘 보강
- expected verdict 매트릭스 5/5 정합 검증

**진입 조건:**

- PR 7A merged + 회귀 0
- fixture 3개 측정 결과로부터 threshold 재결정 근거 확보

### 1-3. PR 7C 또는 defer

**범위 후보:**

- full Music corpus 측정
- 실기 device dump 입력 통합
- PR 8 anchor recommender input 통합
- catalog auto-update 통합

**진입 조건:**

- PR 7B merged 후 별도 결정
- v2 policy 적용 결정 별도

대상 산출물 (구현 단계 진입 시 만들어질 것):

- **측정 도구**: `tools/synthetic_delta_measure.py` (제안 — Source-of-truth Policy 적용 시 schema/test 동시 변경)
  - 입력: fixture directory or fixture pair list
  - 출력: JSON (stdout 또는 `reports/pr7_delta_measurement/<run_id>/result.json`) + 옵션 Markdown
- **fixture set**: `tests/fixtures/synthetic_delta/<name>/before.xml` + `after.xml` + `expected.json`
- **단위 테스트**: `tests/test_synthetic_delta_measure.py`
  - fixture별 verdict 일치 검증 + metric 계산 정확성 검증

PR 6과 동일하게 도구는 **읽기 전용** (push/commit/reset/checkout 금지). 출력 reports는 `reports/` 하위로 commit 금지.

---

## 2. Fixture design

scope §4-1의 5개 분기를 구체화.

### 2-1. Fixture 명명·경로

```
tests/fixtures/synthetic_delta/
├── identical_snapshot/
│   ├── before.xml
│   ├── after.xml
│   └── expected.json
├── text_only_change/
│   ├── before.xml
│   ├── after.xml
│   └── expected.json
├── non_target_context/
│   ├── before.xml
│   ├── after.xml
│   └── expected.json
├── insufficient_evidence/
│   ├── before.xml
│   ├── after.xml
│   └── expected.json
└── target_transition/
    ├── before.xml
    ├── after.xml
    └── expected.json
```

`expected.json` 구조:

```json
{
  "name": "identical_snapshot",
  "expected_verdict": "stable",
  "target_text": null,
  "noise_text_hints": [],
  "notes": "before == after, anchor 동일"
}
```

### 2-2. Fixture XML 작성 원칙

- **최소 layout**: `<hierarchy>` → `<node>` 1~3 depth, 5~20 visible texts
- **target text는 명시적**: 예 `홈`, `즐겨찾기`, `최근 재생` (Music 도메인 익숙 텍스트)
- **noise text도 명시적**: 광고/배너/스낵바 형태 (예 `데이터 절약 모드 알림`)
- **resource-id / class는 일반화**: `android.widget.TextView`, `android.widget.Button` 정도만
- **timestamps / dynamic ids 미포함**: hash 안정성 확보
- **PII 0**: 전화번호, 이름, 주소 등 절대 미포함

### 2-3. Fixture 분기 디테일

| name | before / after 차이 | expected_verdict | target_text |
|------|-------------------|------------------|-------------|
| `identical_snapshot` | 완전 동일 | `stable` | `홈` |
| `text_only_change` | "재생 0곡" → "재생 12곡" 한 줄만 변경 | `meaningful_delta` | `재생 0곡` |
| `non_target_context` | 광고 배너 텍스트만 변경, 본 화면 anchor 동일 | `non_target_context` | `홈` |
| `insufficient_evidence` | 양쪽 모두 visible_texts < 3 (loading 화면) | `insufficient` | null |
| `target_transition` | 화면 전환 (홈 → 즐겨찾기 화면) | `meaningful_delta` | `즐겨찾기` |

### 2-4. Fixture commit policy

- fixture XML / expected.json은 **commit 가능** (`tests/fixtures/synthetic_delta/`)
- 측정 결과 `reports/pr7_delta_measurement/` 는 **commit 금지** (PR 6 §4 forbidden 정책 그대로)
- fixture 추가는 별도 PR로 분리 가능 — implementation PR에서는 minimum 3개부터 시작 가능

---

## 3. Metric calculation

scope §5 metric 표를 구현 알고리즘으로 매핑.

### 3-1. 핵심 metric 알고리즘

| metric | 알고리즘 |
|--------|---------|
| `xml_sha256_equal` | `hashlib.sha256(xml_bytes).hexdigest()` 비교 (UTF-8 정규화 후) |
| `visible_texts_*` | XML parse → `text` 속성 non-empty + `content-desc` non-empty 합집합, trim, dedupe |
| `visible_texts_jaccard` | `|A ∩ B| / |A ∪ B|`, 양쪽 빈 집합이면 1.0 |
| `added_texts` | `after_set - before_set` |
| `removed_texts` | `before_set - after_set` |
| `target_anchor_presence_*` | `target_text in before_set` / `in after_set` (exact match, case-sensitive) |
| `expected_text_present` | scope 사용자가 expected_text 지정 시 동일 |
| `forbidden_noise_text_present` | `expected.noise_text_hints` 와 `added_texts` 교집합 non-empty |

### 3-2. Verdict 분류 알고리즘 (초안)

```
if xml_sha256_equal:
    verdict = "stable"
elif before_visible_texts_count < 3 and after_visible_texts_count < 3:
    verdict = "insufficient"
elif target_anchor presence_after == False and target was specified:
    verdict = "meaningful_delta"  # transition
elif jaccard >= 0.9 and forbidden_noise_text_present:
    verdict = "non_target_context"
else:
    verdict = "meaningful_delta"
```

threshold 값(`< 3`, `>= 0.9`)은 초안. fixture 결과 측정 후 plan 보강에서 재결정.

### 3-3. parser

- `xml.etree.ElementTree` (stdlib) 우선
- 외부 의존성 추가 금지 (실 구현 PR에서 결정)
- 잘못된 XML 입력은 명확한 error로 실패 (fixture 작성 강제)

---

## 4. Expected verdict matrix

implementation 후 fixture별 expected vs actual 매트릭스. plan 단계에서는 expected만 명시.

| fixture | expected_verdict | matched 기준 |
|---------|------------------|--------------|
| `identical_snapshot` | `stable` | actual == `stable` |
| `text_only_change` | `meaningful_delta` | actual == `meaningful_delta` AND `added_texts` non-empty |
| `non_target_context` | `non_target_context` | actual == `non_target_context` AND target_anchor_after == True |
| `insufficient_evidence` | `insufficient` | actual == `insufficient` |
| `target_transition` | `meaningful_delta` | actual == `meaningful_delta` AND target_anchor_after == False AND target_anchor_before == True |

False positive / false negative 분류:

- FP: actual == `meaningful_delta` but expected ∈ {`stable`, `non_target_context`, `insufficient`}
- FN: expected == `meaningful_delta` but actual ∈ {`stable`, `non_target_context`, `insufficient`}

implementation acceptance: 5개 fixture 모두 `matched = true`.

---

## 5. Files allowed (implementation PR 진입 시)

implementation PR 1단계 (도구 + fixture + 테스트):

- `tools/synthetic_delta_measure.py` — 신규
- `tests/fixtures/synthetic_delta/identical_snapshot/before.xml` — 신규
- `tests/fixtures/synthetic_delta/identical_snapshot/after.xml` — 신규
- `tests/fixtures/synthetic_delta/identical_snapshot/expected.json` — 신규
- `tests/fixtures/synthetic_delta/text_only_change/before.xml` — 신규
- `tests/fixtures/synthetic_delta/text_only_change/after.xml` — 신규
- `tests/fixtures/synthetic_delta/text_only_change/expected.json` — 신규
- `tests/fixtures/synthetic_delta/non_target_context/before.xml` — 신규
- `tests/fixtures/synthetic_delta/non_target_context/after.xml` — 신규
- `tests/fixtures/synthetic_delta/non_target_context/expected.json` — 신규
- `tests/fixtures/synthetic_delta/insufficient_evidence/before.xml` — 신규
- `tests/fixtures/synthetic_delta/insufficient_evidence/after.xml` — 신규
- `tests/fixtures/synthetic_delta/insufficient_evidence/expected.json` — 신규
- `tests/fixtures/synthetic_delta/target_transition/before.xml` — 신규
- `tests/fixtures/synthetic_delta/target_transition/after.xml` — 신규
- `tests/fixtures/synthetic_delta/target_transition/expected.json` — 신규
- `tests/test_synthetic_delta_measure.py` — 신규
- (option) `docs/pr7_synthetic_delta_scope.md` — Status 라인 정정만
- (option) `docs/pr7_synthetic_delta_implementation_plan.md` — Status 라인 정정만

implementation 1단계는 **하나의 PR**로 묶거나 fixture 별로 분리 가능. plan 단계에서 결정 보류.

---

## 6. Files forbidden

implementation PR에서 **수정 금지**:

- `tools/git_safe_push_audit.py` (PR 6 트랙, 본 PR과 무관)
- `tests/test_git_safe_push_audit.py` (동)
- `src/` 전체 (runner runtime 영향 없음)
- `schema/` (TC schema 영향 없음)
- `runner_capability.yaml`
- `tc_prompts/` 전체
- `golden_tc_set/` / `exported_tc1/` / ODIN2 testdata
- `validate_tc.py` / `gen_excel.py`
- `docs/tc_template.yaml` / `docs/tc_writing_guide.md`
- generated/probe/catalog/reports artifacts

---

## 7. Generated artifact policy

- 측정 도구가 만드는 reports는 `reports/pr7_delta_measurement/<run_id>/result.json` (또는 stdout)
- `reports/` prefix는 PR 6 §4 forbidden path 정책 대상 — **commit 금지**
- fixture XML / expected.json은 input — **commit 가능**
- run_id는 timestamp 기반, 디렉토리 자동 생성, `.gitignore` 필요 시 별도 처리
- 도구는 push/commit/reset 미수행 (READ-ONLY measurement invariant)

---

## 8. Test plan

### 8-1. 단위 테스트 후보 (`tests/test_synthetic_delta_measure.py`)

- `test_xml_sha256_equal_identical`
- `test_xml_sha256_differs_when_text_changes`
- `test_visible_texts_extraction_basic`
- `test_jaccard_identical_returns_one`
- `test_jaccard_disjoint_returns_zero`
- `test_added_removed_texts_correct`
- `test_verdict_identical_snapshot`
- `test_verdict_text_only_change`
- `test_verdict_non_target_context`
- `test_verdict_insufficient_evidence`
- `test_verdict_target_transition`
- `test_fixture_directory_runner_all_match` (fixture 5개 정합)
- `test_read_only_invariant` (도구가 git/filesystem mutation 안 함)

총 13개 후보. fixture 측정 결과 보고 추가/축소 결정.

### 8-2. 실행 명령

```
venv/Scripts/python.exe -m pytest tests/test_synthetic_delta_measure.py -v
```

### 8-3. PR 6 트랙 회귀 검증

- implementation PR에서 `tests/test_git_safe_push_audit.py` 21 tests **그대로 PASS** 강제 (회귀 0)
- `venv/Scripts/python.exe -m pytest tests/ -v` 전체 통과 확인

### 8-4. JSON / Markdown 출력 smoke

- `tools/synthetic_delta_measure.py --fixture-dir tests/fixtures/delta --format json` → schema_version=1, tool_version=`pr7-delta-measurement-v1`
- `--format markdown` → 헤더 `# Synthetic Delta Measurement — PASS/FAIL` 형식

---

## 9. Non-goals

implementation PR에서 **하지 않는** 일:

- threshold 자동 튜닝 (5 fixture만으로 일반화 금지)
- 실기 device dump fixture 사용
- full Music corpus 측정
- catalog 자동 갱신
- delta verdict가 `cli run` 차단/경고하는 통합
- pre-commit hook 통합
- CI 통합
- PR 8 anchor recommender 시작
- policy v2 운영 적용
- generated artifact commit
- runner runtime 변경

---

## 10. Risks

| Risk | 설명 | 완화 |
|------|------|------|
| **fixture overbuild** | layout이 실 화면을 흉내 내려다 비대화 | 5개 제한 + minimum 5~20 visible texts |
| **threshold 임의성** | jaccard `>= 0.9`, count `< 3`은 근거 없는 초안 | fixture 측정 후 plan 보강에서 재결정 |
| **synthetic만으로 일반화** | "5/5 match"라 해도 실기 신뢰 보장 아님 | scope §8 위험 그대로 명시, plan §8-4 smoke로 baseline만 |
| **PR 6 회귀** | 신규 의존/import가 기존 21 tests 영향 | implementation 시 `tests/test_git_safe_push_audit.py` 회귀 강제 |
| **generated artifact 오염** | 측정 reports를 commit 시도 | `reports/pr7_*` 경로 forbidden, PR 6 audit 도구로 검증 |
| **scope creep (PR 8)** | recommender 욕심으로 추가 코드 | implementation PR §6 forbidden 명시 |
| **threshold drift** | implementation 후 fixture 추가 시 verdict 분류 흔들림 | shrinkage 또는 plan 보강 절차 명시 |
| **외부 의존성 추가** | parser 라이브러리 추가 욕심 | stdlib `xml.etree.ElementTree` 한정 |

---

## 11. Decision boundary

본 implementation plan 문서를 commit하는 시점에 적용되는 단독 범위:

### Commit candidate (plan commit 단계)

- `docs/pr7_synthetic_delta_implementation_plan.md` (only)
- (option) `docs/pr7_synthetic_delta_scope.md` — Status 라인 정정만 포함된 동일 commit (`SCOPE PROPOSAL; repo-fixed at \`e35bf65\`; PR 7 implementation not started; plan working tree.`)

### Excluded (plan commit 단계)

- `tools/synthetic_delta_measure.py` (구현은 별도 PR)
- `tests/fixtures/synthetic_delta/` (fixture는 별도 PR)
- `tests/test_synthetic_delta_measure.py` (테스트는 별도 PR)
- `tools/git_safe_push_audit.py` (PR 6 트랙)
- `tests/test_git_safe_push_audit.py` (동)
- `src/` / `schema/` / `runner_capability.yaml` / `tc_prompts/` 변경 0
- TC YAML / golden_tc_set / exported_tc1 / ODIN2 testdata 변경 0
- generated / probe / catalog / reports / `_probe_*.py` / `*.png` / `popup_*.xml` / `ui_*.xml` / `probe_dump_*.xml`
- `docs/tc_template.yaml` / `docs/tc_writing_guide.md`
- PR 8 시작 0

### Pre-commit verification (plan commit 단계)

- staged file은 **명시적으로 지정된 docs 파일만** 허용 (1 + optional 1 = 최대 2)
- src/schema/runner/tests/tools 변경 0
- generated 산출물 staged 0
- ahead/behind audit 통과 (fast-forward only)
- force / force-with-lease 사용 0

### Adoption note

본 plan commit은 *implementation plan을 repo에 고정하는 행위*에 한정한다. **PR 7 구현 진입은 별도 결정**이며 본 commit과 분리된다. PR 7 implementation 승인 → 코드/테스트/fixture 변경 순서를 따른다.
