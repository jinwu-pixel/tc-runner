# PR 6C — Git Safe Push Audit Retrospective Fixture & Scope Drift (Scope)

**Status:** SCOPE PROPOSAL; repo-fixed at `80c0d04`; no code change; implementation not started.
**Parent plan:** `docs/pr6_git_audit_implementation_plan.md` (repo-fixed at `6f6aceb`)
**Parent scope:** `docs/pr6_git_audit_scope.md` (repo-fixed at `c68e045`)
**PR 6A baseline:** `5e6a2b8` — `tools/git_safe_push_audit.py` JSON-only audit + `tests/test_git_safe_push_audit.py` 10 tests
**PR 6B baseline:** `3dd761a` — Markdown output + `derive_push_command` + 8 추가 tests (총 18 tests)
**Adoption Order context:** v2 Adoption Order 3.5d 단계 (PR 6A/6B 머지 후, PR 7 synthetic delta 진입 *전*)

본 문서는 *PR 6C scope*만 정의한다. implementation plan 및 도구 코드/테스트 변경은 별도 결정·별도 PR로 진행한다.

---

## 1. Purpose

PR 6 git audit 트랙의 마지막 누적 단계로, 다음 두 축을 정의한다.

- **PR 6A/6B 도구의 장기 안정성 확보** — 도구가 미래 commit 유형에서 의도한 verdict(PASS/WARN/FAIL)을 안정적으로 산출하는지 retrospective fixture로 회귀 검증
- **forbidden path policy drift 방지** — `docs/pr6_git_audit_scope.md` §4 forbidden path 정책과 `tools/git_safe_push_audit.py` 내 forbidden pattern 상수 사이의 drift를 정책적·기계적으로 차단
- **retrospective audit 신뢰성 확인** — Music Phase 1 commit history(SMOKE_01~06) 또는 대표 commit 유형에 대해 PR 6A/6B 도구가 사용자가 수동으로 수행했던 audit 결과를 재현
- **PR 7 synthetic delta 진입 전 git audit 트랙 closure** — PR 7/8 진입 전에 PR 6 트랙을 정식으로 완료해 누적 보장

---

## 2. Non-goals

다음은 본 PR 6C가 **하지 않는** 일이다:

- **PR 7 synthetic delta 구현 아님** — delta 신뢰성 측정은 별도 PR
- **PR 8 anchor recommender 구현 아님** — 별도 PR
- **policy v2 운영 적용 아님** — proposal `b4552c4` repo-fixed 그대로 보류
- **pre-commit hook 통합 아님** — 별도 결정
- **CI 통합 아님** — 별도 결정
- **Markdown output 추가 변경 아님** — PR 6B 출력 형식 그대로
- **JSON schema 변경 아님** — schema_version=1, tool_version=`pr6-git-audit-v1` 유지
- **runner runtime 변경 아님** — `cli run`/`load_tc`/runtime catalog 영향 없음
- **TC YAML 변경 아님** — golden_tc_set/exported_tc1/ODIN2 testdata 영향 없음
- **generated/probe/catalog/reports commit 아님** — 영구 비커밋 정책 그대로 유지
- **forbidden path 패턴 *내용* 변경 아님** — 본 PR 6C는 drift 검출 메커니즘만 정의. 패턴 자체 보강은 별도 결정

---

## 3. Retrospective Fixture Options

### 3-1. Option A — Full Music Phase 1 retrospective

- SMOKE_01~06 관련 commit 6개 모두를 fixture로 재현해 audit 도구로 retrospective PASS/WARN/FAIL 검증
- 각 fixture commit의 staged scope, ahead/behind, forbidden 산출물 상태를 실제 commit에서 추출해 재구성
- 장점:
  - PR 6 scope §6 acceptance criteria "Music Phase 1 history 6 commit 모두 retrospective PASS" 직접 충족
  - 실증 근거 강함, 사용자 수동 audit 결과와 1:1 비교 가능
- 단점:
  - fixture 비용 큼 (6 commit 각각의 git history/state 재구성 부담)
  - 기존 commit history를 의존하므로 history rewrite 시 brittle
  - 유지보수 면적 큼

### 3-2. Option B — Representative fixture set (권고)

대표 fixture 5종(또는 그 이하)으로 각 verdict 분기 1개씩 커버:

- **docs-only commit** → PASS
- **generated staged FAIL commit** (`reports/foo.json` 또는 `*/catalog/` staged) → FAIL
- **untracked generated WARN state** (working tree에 untracked forbidden 존재, staged 0) → WARN
- **behind/diverged state** (HEAD..origin non-empty) → FAIL
- **expected path mismatch** (whitelist 불일치) → FAIL

- 장점:
  - fixture 작고 유지보수 쉬움
  - verdict 분기별 회귀 명시
  - history rewrite에 무관 (실제 commit 의존 0)
- 단점:
  - Music Phase 1 전체 재현은 아님 (acceptance §6의 "6 commit 전부" 항목은 별도 처리 필요)

### 3-3. Option C — Hybrid (defer)

- 대표 fixture(B) + Music Phase 1 일부(예: SMOKE_06 1개) 혼합
- 본 PR 6C 범위에서는 **defer**, 추후 확장 후보로만 명시

### 3-4. Recommendation

- **Option B 우선 채택**
- Option A 전체 retrospective는 **별도 확장 후보**(PR 6C+) 로 보류
- §6 acceptance §6 "6 commit 전부" 항목은 PR 6C 범위에서 *대표 fixture로 충족 간주* 하거나, defer 명시 중 하나를 implementation plan 단계에서 결정

---

## 4. Scope Drift Test Options

### 4-1. Option A — scope 문서 §4 parse

- `docs/pr6_git_audit_scope.md` §4 본문에서 forbidden pattern을 직접 추출해 `tools/git_safe_push_audit.py`의 상수와 비교
- 장점:
  - 문서가 source-of-truth임을 기계적으로 강제
  - drift 발생 시 즉시 test FAIL
- 단점:
  - markdown 문구·들여쓰기·bullet 변경에 test brittle
  - 문서 parsing 자체가 별도 책임 영역으로 비대화될 위험

### 4-2. Option B — 코드 상수 vs explicit baseline test (권고)

- `tests/test_git_safe_push_audit.py`에 expected forbidden pattern baseline list를 명시
- `tools/git_safe_push_audit.py` 코드 상수와 baseline을 정확 일치 비교
- 장점:
  - 안정적이고 단순
  - 문서·코드 중 어느 한쪽 변경 시 baseline test가 강제로 의식 단계 도입
- 단점:
  - 문서와 완전 자동 동기화는 아님 (사람이 baseline·문서·코드 3곳을 수동으로 정렬)

### 4-3. Option C — 별도 config 추출 (defer)

- forbidden path policy를 `tools/git_audit_config.yaml` 같은 별도 config로 분리
- 장점:
  - 장기적으로 가장 깔끔, 문서·코드·test 모두 단일 source 참조
- 단점:
  - PR 6C 범위 초과 가능성 큼 (config loader, schema 정의, 기존 코드 reference 변경 동반)
  - Source-of-truth Policy 영향 면적 큼

### 4-4. Recommendation

- **Option B 우선 채택**
- Option C는 별도 PR 후보 (예: PR 6D 또는 PR 7 이후)
- Option A는 markdown parsing 취약성 때문에 **비추천**

---

## 5. Acceptance Criteria

본 PR 6C는 다음을 만족해야 한다:

- [ ] PR 6A/6B 기존 18 tests **그대로 PASS** (회귀 0)
- [ ] retrospective representative fixture tests 추가 (Option B 채택 시 verdict 분기별 1개 이상)
- [ ] forbidden pattern baseline test 추가 (Option B 채택 시 `_EXPECTED_FORBIDDEN_PATTERNS` 같은 상수 + 코드 상수 정확 일치 assertion)
- [ ] generated staged FAIL / untracked generated WARN 정책 *그대로 유지* (verdict 분류 변경 0)
- [ ] Markdown/JSON 출력 변경 없음 — schema_version=1, tool_version=`pr6-git-audit-v1`, 13 check IDs, recommended 4 keys 그대로
- [ ] policy v2 적용 없음 — proposal `b4552c4` repo-fixed 유지
- [ ] cross-platform 동작 (Windows + POSIX) — path separator forward-slash 정규화 그대로
- [ ] 본 도구 자체가 push/commit/reset/checkout 미수행 (READ-ONLY audit invariant 유지)

---

## 6. Risks

| Risk | 설명 | 완화 |
|------|------|------|
| **fixture overbuild** | Option A 채택 시 6 commit 재현 부담으로 PR 6C 면적이 PR 6A/6B 합계보다 커질 가능성 | Option B 채택 + Option A는 defer 후보로 명시 |
| **brittle markdown parsing** | Option A 채택 시 문서 문구 변경마다 test FAIL → 문서 작성에 부정적 압력 | Option A 비추천, Option B로 baseline 명시 |
| **scope drift false confidence** | baseline test가 통과한다고 해서 *문서가 정확히 동기화*된다는 보장은 아님 | implementation plan 단계에서 "문서·baseline·코드 3 갱신 의무" 명시 |
| **scope creep** | Option C(config 분리) 욕심으로 PR 6C 면적 폭증 | Option C는 명시적으로 defer, 별도 PR 후보 |
| **PR 7 진입 지연** | PR 6C 비대화로 PR 7 synthetic delta 진입이 지연될 가능성 | Option B로 작게 시작, full retrospective는 defer |

---

## 7. Recommendation

권고안 요약:

- **PR 6C는 작게 간다.**
- retrospective는 **representative fixture set (Option B)** 으로 제한한다.
- scope drift는 **코드 상수 vs explicit baseline test (Option B)** 로 시작한다.
- full Music Phase 1 retrospective(Option A) 와 config 분리(Option C) 는 **defer**한다.
- 본 scope 확정 후 PR 6C implementation plan을 별도 작성한다 (코드 변경은 implementation plan 승인 이후).

---

## 8. Out-of-scope deferred

다음은 본 PR 6C의 **out-of-scope** — 별도 PR/scope:

- full Music Phase 1 retrospective (Option A) — defer 후보
- forbidden path config 파일 분리 (Option C) — 별도 PR 후보
- pre-commit hook 통합 — PR 6+1 후보
- CI 통합 — 별도 결정
- batch commit candidate manifest 자동 생성 — v2 §8-4 영역
- PR 7 synthetic delta measurement — 별도
- PR 8 anchor recommender — 별도

---

## 9. Decision boundary

본 scope 문서를 commit하는 시점에 적용되는 단독 범위:

### Commit candidate

- `docs/pr6c_git_audit_retrospective_scope.md` (only)
- (option) `docs/pr6b_git_audit_markdown_implementation_plan.md` — Status 라인 정정만 포함된 동일 commit (`PLAN; repo-fixed at \`ab42343\`; PR 6B implemented at \`3dd761a\`; PR 6C pending.`)

### Excluded

- `tools/git_safe_push_audit.py` (구현은 별도 PR)
- `tests/test_git_safe_push_audit.py` (테스트는 별도 PR)
- `docs/tc_template.yaml`
- `docs/tc_writing_guide.md`
- generated / probe / catalog / reports / `_probe_*.py` / `*.png` / `popup_*.xml` / `ui_*.xml` / `probe_dump_*.xml`
- TC YAML / golden_tc_set / exported_tc1 / ODIN2 testdata
- src/ schema/ runner_capability tc_prompts/ 변경 0
- PR 7 / PR 8 시작 0

### Pre-commit verification

- staged file은 **명시적으로 지정된 docs 파일만** 허용 (1 + optional 1 = 최대 2)
- src/schema/runner/tests/tools 변경 0
- generated 산출물 staged 0
- ahead/behind audit 통과 (fast-forward only)
- force / force-with-lease 사용 0

### Adoption note

본 commit은 *scope 문서를 repo에 고정하는 행위*에 한정한다. **PR 6C 구현 진입은 별도 결정**이며 본 commit과 분리된다. PR 6C implementation plan 작성 → implementation 승인 → 코드/테스트 변경 순서를 따른다.
