# PR 6C — Git Safe Push Audit Retrospective Fixture & Scope Drift (Implementation Plan)

**Status:** PLAN; repo-fixed at `af43c48`; PR 6C implemented at `eca3104`; PR 6 track closed.
**Scope source-of-truth:** `docs/pr6c_git_audit_retrospective_scope.md` (repo-fixed at `80c0d04`)
**PR 6A baseline:** `5e6a2b8` — `tools/git_safe_push_audit.py` JSON-only audit + `tests/test_git_safe_push_audit.py` 10 tests
**PR 6B baseline:** `3dd761a` — Markdown output + `derive_push_command` + 8 추가 tests (총 18 tests)
**Adoption Order context:** v2 Adoption Order 3.5d 단계 (PR 6A/6B 머지 후, PR 7 synthetic delta 진입 *전*)

본 문서는 *implementation plan*만 정의한다. 도구 코드/테스트 변경은 별도 결정·별도 PR로 진행한다.

---

## 1. Implementation Target

### 1-1. 변경 대상

- `tests/test_git_safe_push_audit.py` — retrospective representative fixture tests + forbidden pattern baseline test 추가

### 1-2. 변경 면적 제약

- `tools/git_safe_push_audit.py` 변경 **0** (코드 상수/함수 signature/JSON schema/Markdown 출력 형식 모두 그대로)
- src/* 변경 0
- schema 변경 0
- runner_capability 변경 0
- TC YAML 변경 0
- prompts 변경 0
- generated/probe/catalog/reports staged 0
- `tools/git_safe_push_audit.py` 상수는 이미 module-level public tuple (`FORBIDDEN_BASENAME_PATTERNS` / `FORBIDDEN_DIRECTORY_PREFIXES` / `FORBIDDEN_DIRECTORY_NAMES`) → 추가 export 정리 불필요
- 단, 테스트 작성 중 import 편의를 위해 `tools/git_safe_push_audit.py`에 `__all__` 명시 같은 사소한 변경이 *필요해질 경우*에만 본 plan을 갱신해 명시 후 수행 (default는 변경 0)

### 1-3. PR 6A/6B 호환성

- `run_audit()` 함수 시그니처 유지
- `run_audit()` return dict 구조 유지 (schema_version=1, tool_version=`pr6-git-audit-v1`, 5 블록 + 13 checks)
- JSON output schema/keys/13 check IDs 유지
- Markdown output 섹션/헤더 형식/push command 형식 유지
- exit code 매핑 유지: PASS=0 / WARN=0 / FAIL=1
- 기존 18 tests 회귀 0 (PR 6A 10 + PR 6B 8)

### 1-4. 실제 구현은 별도 승인

본 plan은 *어떻게* 구현할지의 설계만 정의한다. 실제 테스트 작성은 별도 단계 + 별도 사용자 승인.

---

## 2. Retrospective Representative Fixture Plan

### 2-1. 채택

- scope §3-2 — Option B representative fixture set
- 5 verdict-branch fixtures (각 verdict 분기 1개씩)

### 2-2. 거부된 대안

- **Option A (full Music Phase 1 retrospective)** — 거부. 6 commit 재현 비용 + history rewrite brittle. defer 후보로만 유지
- **Option C (hybrid)** — defer. 본 PR 6C 범위 초과

### 2-3. 5 fixture 정의

| Fixture | Verdict | 재현 상태 | 핵심 검증 |
|---|---|---|---|
| `test_retro_docs_only_pass` | PASS | docs-only commit staged, ahead=1, behind=0, untracked 0 forbidden | base case PASS 회귀 |
| `test_retro_generated_staged_fail` | FAIL | `reports/foo.json` staged | `forbidden_path_guard` FAIL 트리거 |
| `test_retro_untracked_generated_warn` | WARN | working tree에 `reports/stray.html` untracked, staged 0 | `untracked_forbidden_report` WARN 트리거 |
| `test_retro_behind_origin_fail` | FAIL | HEAD..origin/master non-empty (behind 상태) | `head_minus_origin_empty` FAIL 트리거 |
| `test_retro_expected_path_mismatch_fail` | FAIL | staged 경로가 `--expected-path` whitelist 불일치 | `candidate_whitelist_match` FAIL 트리거 |

### 2-4. Fixture 구현 패턴

- PR 6A/6B의 `_make_repo`/`_stage_file`/`_check` 헬퍼 그대로 재사용
- `tmp_path` + 실제 `git init` (mock 없음)
- bare origin은 file path
- 각 fixture는 self-contained — 다른 fixture 의존 0
- `run_audit(...)` 호출 후 result dict의 `verdict` 및 해당 `checks[*]` level 검증 (substring assertion)

### 2-5. 거부된 fixture 후보

- Music Phase 1 SMOKE_01~06 실제 commit history 의존 fixture — 거부 (Option A로 defer)
- `git filter-repo` / `git rebase` 사용 fixture — 거부 (history rewrite는 fixture 안정성 저하)
- `--no-fetch` 분기 fixture — 거부 (PR 6B `test_no_fetch_skips_fetch_check`로 이미 커버)
- detached HEAD fixture — 거부 (PR 6B 선택 후보로만 등장. 본 PR 6C 범위에서는 미포함)

---

## 3. Forbidden Pattern Baseline Test Plan

### 3-1. 채택

- scope §4-2 — Option B code constants vs explicit baseline
- test 파일 안에 explicit expected baseline tuple/set을 정의
- `tools/git_safe_push_audit.py`의 3 module-level 상수와 정확 일치 검증

### 3-2. 거부된 대안

- **Option A (scope §4 markdown parse)** — 거부. markdown 문구 변경에 brittle, parser 자체가 별도 책임 영역
- **Option C (별도 config 파일 분리)** — defer. PR 6C 범위 초과 (config loader/schema/refactor 동반)

### 3-3. 검증 대상 상수

| 상수 | 현재 값 (참고용 — drift 검출이 목적) |
|---|---|
| `FORBIDDEN_BASENAME_PATTERNS` | `("probe_*.xml", "_probe_*.py", "probe_dump_*.xml", "ui_*.xml", "popup_*.xml", "screenshot_*.png")` |
| `FORBIDDEN_DIRECTORY_PREFIXES` | `("generated/", "reports/")` |
| `FORBIDDEN_DIRECTORY_NAMES` | `("catalog",)` |

> 위 표는 PR 6C plan 작성 시점의 코드 snapshot. test 안에 baseline을 *동일하게* 명시하고 import 한 상수와 비교한다. drift 발생 시 양쪽이 의식적으로 갱신되도록 강제하는 것이 목적.

### 3-4. 비교 방식

- **tuple exact 비교 (권고)** — 순서까지 고정. drift 감지 민감도 최대.
  ```python
  assert audit.FORBIDDEN_BASENAME_PATTERNS == EXPECTED_FORBIDDEN_BASENAME_PATTERNS
  ```
- set 비교는 거부 — 순서가 잠재적으로 의미를 가질 가능성 (fnmatch 매칭 우선순위 등)이 있어 보수적으로 tuple exact

### 3-5. 추가 tests

- [ ] `test_baseline_forbidden_basename_patterns` — `FORBIDDEN_BASENAME_PATTERNS` tuple exact match
- [ ] `test_baseline_forbidden_directory_prefixes` — `FORBIDDEN_DIRECTORY_PREFIXES` tuple exact match
- [ ] `test_baseline_forbidden_directory_names` — `FORBIDDEN_DIRECTORY_NAMES` tuple exact match

### 3-6. 거부된 추가 baseline

- `SCHEMA_VERSION` / `TOOL_VERSION` baseline — 거부 (PR 6A/6B 기존 test에서 이미 검증)
- 13 check ID 집합 baseline — 거부 (PR 6B `test_markdown_output_checks_table_completeness` + JSON schema 회귀로 이미 커버)
- `NOTE_READ_ONLY` 문자열 baseline — 거부 (PR 6A/6B substring assertion으로 이미 커버)

---

## 4. Test File Structure Plan

### 4-1. 추가 위치

- `tests/test_git_safe_push_audit.py` 하단에 **PR 6C** 섹션 추가 (`# --- PR 6C: retrospective fixtures + forbidden pattern baseline ---` 주석 헤더)

### 4-2. 새 import / 새 헬퍼

- 추가 import 0 (PR 6A/6B 헬퍼 그대로 사용)
- 새 헬퍼 0 (`_make_repo`/`_stage_file`/`_check` 재사용)
- 단, baseline test 작성 시 `from tools.git_safe_push_audit import FORBIDDEN_BASENAME_PATTERNS, FORBIDDEN_DIRECTORY_PREFIXES, FORBIDDEN_DIRECTORY_NAMES` import 추가는 인정 (이미 상수가 module-level public이므로 추가 export 작업 불필요)

### 4-3. 테스트 추가 수

- retrospective fixtures: **5**
- forbidden baseline: **3**
- **총 PR 6C 추가: 8**
- 기존 PR 6A 10 + PR 6B 8 + PR 6C 8 = **최종 26 tests** (회귀 0 가정 시)

### 4-4. 중복 검토

- `test_retro_generated_staged_fail` vs PR 6A `test_forbidden_path_guard_blocks_generated_staged` — 검증 본질 유사. PR 6C는 retrospective 컨텍스트 (대표 시나리오 회귀)로 위치시키되, 중복도 높으면 implementation 단계에서 통합/명확 분리 결정
- `test_retro_untracked_generated_warn` vs PR 6A `test_untracked_forbidden_report` — 동일 분기 검증. retrospective 컨텍스트 차별화 명시 또는 통합
- 결정 기준: 추가 test가 **기존 test 위에 어떤 retrospective 보장**을 더하는지 implementation 단계에서 명시하지 못하면 해당 fixture는 추가하지 않는다 (테스트 수 부풀리기 금지)

---

## 5. Acceptance Criteria

본 PR 6C는 다음을 만족해야 한다:

- [ ] PR 6A/6B 기존 18 tests **그대로 PASS** (회귀 0)
- [ ] retrospective representative fixture tests 5건 추가, 각 verdict 분기 1개 이상 커버
- [ ] forbidden pattern baseline test 3건 추가 (basename/prefix/name 각 1)
- [ ] `tools/git_safe_push_audit.py` 변경 0
- [ ] generated staged FAIL / untracked generated WARN 정책 그대로 유지 (verdict 분류 변경 0)
- [ ] Markdown/JSON 출력 변경 없음 — schema_version=1, tool_version=`pr6-git-audit-v1`, 13 check IDs, recommended 4 keys 그대로
- [ ] policy v2 적용 없음 — proposal `b4552c4` repo-fixed 유지
- [ ] cross-platform 동작 (Windows + POSIX) — path separator forward-slash 정규화 그대로
- [ ] 본 도구 자체가 push/commit/reset/checkout 미수행 (READ-ONLY audit invariant 유지)
- [ ] 최종 test 수 **26 tests** (PR 6A 10 + PR 6B 8 + PR 6C 8) — 단 §4-4 중복 검토 결과로 축소될 경우 본 plan 갱신 후 진행

---

## 6. Test Plan Summary

### 6-1. 필수 테스트 (8건)

- [ ] `test_retro_docs_only_pass` — docs-only staged 시 PASS
- [ ] `test_retro_generated_staged_fail` — `reports/foo.json` staged 시 FAIL
- [ ] `test_retro_untracked_generated_warn` — `reports/stray.html` untracked 시 WARN
- [ ] `test_retro_behind_origin_fail` — HEAD..origin non-empty 시 FAIL
- [ ] `test_retro_expected_path_mismatch_fail` — `--expected-path` 불일치 시 FAIL
- [ ] `test_baseline_forbidden_basename_patterns` — tuple exact match
- [ ] `test_baseline_forbidden_directory_prefixes` — tuple exact match
- [ ] `test_baseline_forbidden_directory_names` — tuple exact match

### 6-2. 선택 / PR 6C+ 후보

- [ ] `test_retro_diverged_branch_fail` — 양방향 non-empty (PR 6C 범위 내, 단 implementation 단계 결정)
- [ ] `test_retro_full_music_phase1` — Option A 일부 SMOKE_06 commit retrospective (defer 후보, 본 PR 6C 미포함)

### 6-3. Read-only invariant 회귀

- 기존 `test_read_only_audit` (JSON) + PR 6B `test_read_only_audit_markdown` (있을 경우)는 그대로 유지
- PR 6C 새 fixture 호출 후 working tree/HEAD 미변경 substring assertion은 implementation 단계에서 추가 여부 결정

### 6-4. Test infrastructure 정책 (PR 6A/6B 그대로)

- pytest + `tmp_path` + 실제 `git init` (mock 없음)
- bare origin은 file path
- assertion은 substring 우선, regex는 형식 한정
- `_make_repo`/`_stage_file`/`_check` 헬퍼 재사용

---

## 7. PR 분리

### 7-1. 추천: 단일 PR 6C

- `tests/test_git_safe_push_audit.py`에 8 test 일괄 추가
- 변경 파일 1개, 변경 면적 작음
- code change 0

### 7-2. 거부: 분리

- retrospective fixture PR 6C-retro + baseline PR 6C-baseline 분리는 비용 대비 이득 X
- 두 영역 모두 동일 테스트 파일 변경, drift 방지라는 공통 목적

### 7-3. PR 분리 옵션 (사용자 결정 시)

| 옵션 | 범위 |
|---|---|
| **단일 PR 6C** | retrospective 5 + baseline 3 일괄 |
| **PR 6C-retro + PR 6C-baseline** | retrospective 5 → baseline 3 (2단) |
| **PR 6C-retro + PR 6C-baseline + PR 6D-config** | + Option C config 분리 (과분리, 정책 위반) |

추천: **단일 PR 6C**

---

## 8. Non-goals

본 PR 6C implementation은 다음을 **하지 않는다**:

- `tools/git_safe_push_audit.py` 코드 변경 (상수/함수/CLI/JSON/Markdown 모두)
- forbidden path 패턴 *내용* 변경 (추가/삭제/수정)
- 13 check ID 추가/삭제
- JSON schema 확장 (`schema_version` 그대로 1)
- Markdown 섹션 변경
- `recommended.push_command` 형식 변경
- exit code 매핑 변경
- scope 문서 markdown parse 기반 drift test (Option A 거부)
- forbidden path config 파일 분리 (Option C defer)
- full Music Phase 1 retrospective (Option A defer)
- pre-commit hook 통합 (별도 PR)
- CI 통합 (별도 결정)
- file output 옵션
- color output
- GitHub annotation 형식
- policy v2 운영 적용
- PR 7 synthetic delta 선진입
- PR 8 anchor recommender 선진입
- TC YAML 변경
- runner_capability.yaml 변경
- src/cli.py 변경
- runner runtime 변경
- generated/probe/catalog/reports commit
- Music Phase 1 실제 commit history 의존 fixture

---

## 9. Risks

### 9-1. Fixture overbuild

- **Risk:** 5 retrospective fixture가 필수 18 test 위에 중복으로 쌓이며 PR 6C 면적이 PR 6A/6B 합계보다 커질 위험
- **완화:** §4-4 중복 검토 — implementation 단계에서 기존 test와 본질 중복인 fixture는 제외. 추가 fixture는 *retrospective 보장*이라는 별도 책임을 명시할 수 있을 때만 채택. 통합 결정 시 본 plan 갱신

### 9-2. Baseline false confidence

- **Risk:** baseline test가 통과한다고 해서 `docs/pr6_git_audit_scope.md` §4 forbidden path 정책 문서와 코드가 *정확히 동기화*된다는 보장은 아님 (사람이 baseline·코드·문서 3곳을 의식적으로 갱신해야 함)
- **완화:** baseline test의 목적은 **drift 발생 시 의식 단계 강제**. test가 깨지면 사람이 양쪽 (코드/baseline/문서)을 모두 갱신할 동기가 생긴다. PR 6C scope §6 "scope drift false confidence" risk를 본 plan에서 동일하게 인정하고, implementation 단계에서 PR 설명에 "baseline 갱신 시 §4 문서도 함께 검토" 가이드를 PR 본문에 명시

### 9-3. Config split temptation

- **Risk:** "이왕 baseline 만드는 김에 config 파일로 분리" 욕심이 PR 6C 면적을 폭증시킬 위험
- **완화:** §8 Non-goals + scope §3-3 Option C defer 명시. 본 PR 6C 범위에서 config 분리는 **금지**. 별도 PR 후보 (예: PR 6D)

### 9-4. PR 7 진입 지연

- **Risk:** 본 PR 6C가 비대화되어 PR 7 synthetic delta 진입이 지연
- **완화:** 단일 PR 6C 추천 + Option B/B로 작게 시작 + Option A 전체 retrospective defer

### 9-5. Brittle markdown parsing

- **Risk:** Option A 채택 시 scope 문서 §4 문구 변경에 baseline test가 brittle. 문서 작성에 부정적 압력
- **완화:** Option A 거부, Option B 채택 (§3-2)

### 9-6. Test 중복

- **Risk:** retrospective fixture 일부가 PR 6A/6B 기존 test와 본질 중복 → 테스트 수 부풀리기
- **완화:** §4-4 — implementation 단계에서 retrospective 차별점을 명시하지 못하면 해당 fixture는 추가하지 않는다. 결과적으로 §4-3의 "8 추가" 수치가 5~8로 축소될 수 있음. 축소 시 본 plan 갱신

### 9-7. Cross-platform 회귀

- **Risk:** retrospective fixture가 Windows path separator / line ending 가정에 의존
- **완화:** PR 6A/6B의 path forward-slash 정규화 + utf-8 binary write 패턴 그대로 사용. fixture는 OS에 의존하지 않는 git plumbing 호출만 사용 (`git init`/`git add`/`git commit`/`git fetch`)

### 9-8. Read-only invariant 위반

- **Risk:** retrospective fixture가 git 호출 중 working tree나 HEAD를 우연히 변경
- **완화:** §6-3 — PR 6A `test_read_only_audit` + PR 6B `test_read_only_audit_markdown`이 이미 invariant 회귀를 보장. 추가 PR 6C 호출도 동일 codepath이므로 회귀 risk 0. implementation 단계에서 fixture 호출 후 HEAD/working tree 미변경을 보강 검증할지 결정

---

## 10. Decision boundary

### 10-1. 본 plan 문서 commit 시점의 단독 범위

#### Commit candidate

- `docs/pr6c_git_audit_retrospective_implementation_plan.md` (NEW)

#### Excluded

- `tools/git_safe_push_audit.py` (PR 6C implementation에서도 변경 0이 default)
- `tests/test_git_safe_push_audit.py` (PR 6C implementation에서 변경)
- `docs/pr6c_git_audit_retrospective_scope.md` (이미 `80c0d04`에 commit됨)
- `docs/pr6b_git_audit_markdown_implementation_plan.md` (status line 정정은 `80c0d04`에 포함됨)
- generated / probe / catalog / reports artifacts
- `docs/tc_template.yaml`
- `docs/tc_writing_guide.md`
- TC YAML / golden_tc_set / exported_tc1 / ODIN2 testdata
- src/ schema/ runner_capability tc_prompts/ 변경 0
- PR 7 / PR 8 시작 0

#### Pre-commit verification

- staged 파일 명시적으로 plan 문서 1건만 허용
- src/schema/runner/tools/tests 변경 0
- generated 산출물 staged 0
- ahead/behind audit 통과 (fast-forward only)
- force / force-with-lease 사용 0

### 10-2. Implementation 진입 조건

본 commit은 *plan 문서를 repo에 고정하는 행위*에 한정한다. **PR 6C implementation 진입은 별도 결정**이며 본 commit과 분리된다.

진입 시 사용자 명시 승인 필수:
- 단일 PR 6C / 분리 옵션 선택
- 변경 파일 명시 (`tests/test_git_safe_push_audit.py` only — `tools/` 변경 default 0)
- retrospective fixture 5 + baseline 3 = **8** 적용 / §4-4 중복 검토 결과 축소 여부
- Option B/B 결정 재확인 (Option A retrospective full / Option C config 분리는 본 PR 6C에서 거부/defer 그대로)

### 10-3. Adoption Order 위치

- v2 Adoption Order 3.5d 단계 = PR 6C retrospective fixture + scope drift
- 본 PR 6C는 **PR 6A/6B 머지 후, PR 7 synthetic delta 진입 *전***
- PR 7 synthetic delta는 4단계 진입, 별도 결정
