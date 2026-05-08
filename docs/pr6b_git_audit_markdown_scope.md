# PR 6B — Git Safe Push Audit Markdown Output (Scope)

**Status:** SCOPE PROPOSAL; repo-fixed pending; no code change; implementation not started.
**Parent plan:** `docs/pr6_git_audit_implementation_plan.md` (repo-fixed at `6f6aceb`)
**PR 6A baseline:** `5e6a2b8` — `tools/git_safe_push_audit.py` JSON-only audit + `tests/test_git_safe_push_audit.py` 10 tests
**Adoption Order context:** v2 Adoption Order 3.5단계 (PR 6A 머지 다음, PR 6C retrospective fixture 이전)

본 문서는 *PR 6B scope*만 정의한다. implementation plan 및 도구 코드 변경은 별도 결정·별도 PR로 진행한다.

---

## 1. Goal

PR 6A의 JSON audit 결과를 사람이 읽기 쉬운 Markdown report로 출력하는 범위를 정의한다.

### 1-1. 포함 목표

- Markdown human-readable report 추가 (`--format md` 분기)
- JSON output 기본값 유지 (PR 6A 호환성 보존)
- `recommended.push_command` 출력
- `force` / `force-with-lease` 사용 금지 문구 출력
- `human review required` 문구 출력
- PR 6A의 read-only guarantee 유지 (HEAD/index/working tree 변동 0)
- PR 6A의 JSON schema 변경 최소화 (`schema_version=1`, `tool_version` 그대로 유지)

### 1-2. 비포함 (Non-goals)

§7 Non-goals 참조.

---

## 2. CLI Option Decision

### 2-1. 채택

- `--format json|markdown`
- 기본값: `json`
- alias: `md` 도 허용 (`--format md`)

### 2-2. 거부된 대안

- `--markdown` 단독 boolean flag — 거부
  - 이유: 향후 출력 포맷 확장 (예: `text`, `sarif`, `junit`) 시 옵션 폭증
  - `--format` enum 형식이 확장성 우위
- JSON + Markdown 동시 출력 (예: `--format both`) — 거부
  - 이유: stdout 1개 채널에 두 포맷 혼재 시 파이프 친화성 훼손
  - 별도 파일 출력 옵션은 PR 6B 범위 밖 (별도 결정)

### 2-3. 채택 사유

- 기본값 `json` → PR 6A의 모든 호출자 (test, smoke run, future hook)는 변경 없이 동작
- `--format markdown` → 사람 검토용 보고서로만 사용
- exit code는 두 포맷 동일: PASS=0 / WARN=0 / FAIL=1

---

## 3. Markdown Report Structure

### 3-1. 헤더 (1 line)

| Verdict | Header 형식 |
|---|---|
| PASS | `# Git Safe Push Audit — PASS` |
| WARN | `# Git Safe Push Audit — WARN` |
| FAIL | `# Git Safe Push Audit — FAIL` |

헤더 다음 줄에 1-line summary (branch / ahead / behind / staged count). 예:

```
# Git Safe Push Audit — PASS

branch: master · ahead: 1 · behind: 0 · staged: 3 · untracked: 1119
generated_at: 2026-05-08T00:38:32Z · tool_version: pr6-git-audit-v1
```

### 3-2. 섹션 순서

1. **Branch state** — current branch, ahead/behind count, base ref, fetch result (skipped/PASS/FAIL)
2. **Staged scope** — staged 파일 목록 (count + bullet list), expected_paths 매칭 결과 (PASS/FAIL + missing/unexpected 분리)
3. **Forbidden path check** — staged forbidden FAIL 분리, untracked forbidden WARN 분리, tracked dirty forbidden FAIL 분리
4. **Dirty/untracked summary** — tracked dirty count + 목록 (forbidden 매칭 별도 표시), untracked count (개별 목록은 출력 X — 노이즈 회피)
5. **Recommended push command** — `git push origin HEAD:<target-branch>` 1줄 (target-branch는 `--base origin/<name>`에서 `<name>` 추출), force 금지 문구, human review reminder
6. **Checks table** — 13개 check를 ID / status / detail 표 형식으로 1줄씩

### 3-3. Verdict별 강조

- **PASS**: 평이한 요약, 모든 섹션 PASS 표시
- **WARN**: 헤더에 WARN, untracked_forbidden_report 등 WARN 항목을 `> WARN:` blockquote로 강조
- **FAIL**: 헤더에 FAIL, FAIL 항목을 `> FAIL:` blockquote로 강조 + `Decision required: do not push` 1줄 추가

---

## 4. Recommended Push Command Block

### 4-1. 형식

```
## Recommended push command

git push origin HEAD:master

- `--force` / `--force-with-lease` 사용 금지
- Decision required: human review before push
```

### 4-2. Target branch 결정 정책

- `--base origin/<name>` → target-branch = `<name>`
  - 예: `--base origin/master` → `git push origin HEAD:master`
  - 예: `--base origin/main` → `git push origin HEAD:main`
- `--base` 형식이 `<remote>/<branch>` 가 아니면: command line 미생성 + 명시 오류 메시지 (`base argument must be in 'remote/branch' form`). silent fallback 금지
- current branch가 master가 아니면: `branch_current` WARN은 유지하되 push command는 target-branch 기준 그대로 출력 (push command는 *권장*이며 사용자가 검토 후 실행)
- detached HEAD 상태: branch 비어있음 → `Decision required: detached HEAD detected — resolve branch first` 표기, push command line 미생성
- Markdown report는 target branch와 base 둘 다 명시 (`base: origin/master · target: master`)

---

## 5. WARN/FAIL 표현 정책

### 5-1. WARN — 비차단성 이슈

- 별도 `## Warnings` 섹션에 모든 WARN 항목 모음
- 각 항목 1줄: `- WARN [<check_id>] <detail>`
- WARN 발생 시에도 push 자체는 가능하나, 사람이 검토 결정

### 5-2. FAIL — 차단성 이슈

- 별도 `## Failures` 섹션에 모든 FAIL 항목 모음
- 각 항목 1줄: `- FAIL [<check_id>] <detail>`
- FAIL 발생 시 `> Decision required: do not push` blockquote 의무 출력

### 5-3. 매핑 표

| Source | Verdict | Markdown 위치 |
|---|---|---|
| `staged forbidden path` | FAIL | Failures + Forbidden path check |
| `untracked forbidden path` | WARN | Warnings + Forbidden path check |
| `tracked dirty forbidden` | FAIL | Failures + Forbidden path check |
| `head_minus_origin not empty (behind)` | FAIL | Failures + Branch state |
| `ahead expected mismatch` | FAIL | Failures + Branch state |
| `staged whitelist mismatch` | FAIL | Failures + Staged scope |
| `branch != master` | WARN | Warnings + Branch state |

---

## 6. JSON Compatibility 보장

### 6-1. JSON output 변동 없음

- `--format json`(기본값) 호출 시 PR 6A 출력과 byte-level 동일
  - 단, `generated_at`, `run_id`는 매 호출마다 변동되므로 byte-level 동일 보장 X (그 외 필드는 동일)
- JSON schema는 `schema_version=1` 그대로
- 새 필드 추가 0 (Markdown은 `--format markdown` 분기에서만 derive)

### 6-2. 새 필드 추가 금지

- Markdown rendering을 위해 `markdown_report` 같은 필드를 JSON에 추가하지 않는다
- Markdown은 JSON의 derived view (별도 codepath, 같은 input)
- 결과: PR 6A schema와 100% 호환, 외부 consumer (예: 향후 hook/CI)는 변경 없이 동작

---

## 7. Non-goals (PR 6B에서 하지 않음)

- retrospective Music Phase 1 fixture 구현 (PR 6C)
- scope drift test 구현 (PR 6C)
- pre-commit hook 통합 (별도 PR)
- CI 통합 (별도 결정)
- policy v2 운영 적용 (Adoption Order 별도 단계)
- PR 7 synthetic delta 선진입
- PR 8 anchor recommender 선진입
- TC YAML 변경
- `runner_capability.yaml` 변경
- schema 확장
- `src/cli.py` 변경 (서브커맨드 추가 금지)
- runner runtime 변경
- PR 6A의 13 check ID 추가/삭제 (Markdown은 13 check를 그대로 표 출력)
- PR 6A의 JSON 출력 byte 동일성 위반 (단 `generated_at`/`run_id` 제외)

---

## 8. Test Plan Candidates

### 8-1. 필수 케이스

- [ ] **`test_markdown_output_pass_contains_verdict_header`** — staged docs only PASS 시 헤더 `# Git Safe Push Audit — PASS` 포함
- [ ] **`test_markdown_output_fail_contains_blocking_reason`** — `reports/run.html` staged FAIL 시 `## Failures` 섹션 + `Decision required: do not push` 포함
- [ ] **`test_markdown_output_warn_lists_untracked_forbidden`** — `reports/stray.html` untracked WARN 시 `## Warnings` 섹션 + `untracked_forbidden_report` detail 포함
- [ ] **`test_markdown_output_contains_recommended_push_command`** — 모든 verdict에서 `git push origin HEAD:<target-branch>` line 출력 (target-branch는 `--base origin/<name>`에서 derive)
- [ ] **`test_markdown_output_contains_force_prohibition`** — 모든 verdict에서 `--force` / `--force-with-lease` 사용 금지 문구 포함
- [ ] **`test_json_default_output_unchanged`** — `--format` 미지정 시 JSON 출력이 PR 6A 결과 schema와 동일 (verdict, branch, staging, path_policy, checks, recommended 5 블록 + schema_version + tool_version)

### 8-2. 선택 케이스 (PR 6B 진입 시 결정)

- [ ] **`test_markdown_output_human_review_reminder`** — Recommended push command 섹션에 "Decision required: human review before push" 포함
- [ ] **`test_markdown_output_checks_table_completeness`** — 13개 check ID 모두 표에 출현
- [ ] **`test_markdown_output_detached_head`** — detached HEAD 상태에서 `Decision required: detached HEAD detected — resolve branch first` 출력
- [ ] **`test_markdown_output_branch_warn`** — non-master branch 시 헤더 `WARN`, `## Warnings`에 `branch_current` 포함

### 8-3. Test infrastructure 정책

- pytest 기존 패턴 그대로 (`tmp_path` + `git init` + 인위적 commit/index)
- mock 사용 최소화 (PR 6A와 동일)
- Markdown 검증은 substring assertion 우선, regex는 지정된 형식 한정
- byte-identical assertion은 사용 X (`generated_at`/`run_id` 변동 인정)

---

## 9. Risks

### 9-1. JSON compatibility

- **Risk:** Markdown 렌더링을 위해 JSON에 새 필드 추가하면 외부 consumer 회귀
- **완화:** §6 — JSON output에 새 필드 추가 금지. Markdown은 derived view로만 구현. test `test_json_default_output_unchanged`로 보호

### 9-2. Output duplication

- **Risk:** Markdown과 JSON이 동일 정보를 별도 경로로 derive하면서 drift 발생
- **완화:** Markdown formatter는 `run_audit()` return dict를 입력으로 받음 (단일 source). JSON 분기와 Markdown 분기가 같은 dict를 참조

### 9-3. Markdown ambiguity

- **Risk:** Markdown 형식 지정 모호 → 향후 변경 시 사용자 혼란
- **완화:** §3 섹션 순서 + §4-1 push command 형식 + §5-3 매핑 표를 source-of-truth로 고정. test에 substring assertion으로 형식 강제

### 9-4. Scope creep

- **Risk:** "이왕 만드는 김에" file output, color, GitHub annotation 형식 등 추가 위험
- **완화:** §7 Non-goals 강제. 추가는 별도 PR/별도 결정

### 9-5. Unicode rendering

- **Risk:** Windows cp949 환경에서 em-dash (—) / arrow (→) 출력 시 PR 6A와 동일 인코딩 이슈
- **완화:** PR 6A의 utf-8 binary write 패턴 (`sys.stdout.buffer.write(payload.encode("utf-8"))`) 그대로 적용. Markdown 분기도 동일 codepath

### 9-6. Verdict 표시 일관성

- **Risk:** JSON `verdict` 필드와 Markdown 헤더 verdict 불일치 → 사람이 잘못 해석
- **완화:** 두 분기 모두 `result["verdict"]`를 단일 source로 사용. test로 보호

---

## 10. Decision boundary

### 10-1. 본 문서 commit 시점의 단독 범위

#### Commit candidate

- `docs/pr6b_git_audit_markdown_scope.md` (NEW)
- `docs/pr6_git_audit_implementation_plan.md` (status line 정정 — PR 6A merged 반영)

#### Excluded

- `tools/git_safe_push_audit.py` (PR 6B implementation에서 변경)
- `tests/test_git_safe_push_audit.py` (PR 6B implementation에서 변경)
- `docs/pr6b_git_audit_markdown_implementation_plan.md` (별도 문서, 별도 결정)
- generated / probe / catalog / reports artifacts

#### Pre-commit verification

- staged 파일 명시적으로 지정된 docs 파일만 허용
- src/schema/runner/tests/tools 변경 0
- generated 산출물 staged 0
- ahead/behind audit (fast-forward only)
- force/force-with-lease 미사용

### 10-2. PR 6B implementation 진입은 별도 결정

본 commit은 *PR 6B scope를 repo에 고정하는 행위*에 한정한다. **PR 6B implementation plan 작성 및 implementation 진입은 별도 결정**이며 본 commit과 분리된다.

### 10-3. PR 6B 분리 옵션

향후 implementation 시 PR 분리 방향:

| 옵션 | 범위 | 비용 |
|---|---|---|
| **단일 PR 6B** | scope/plan/code/test 전부 | 중간 (review 면적 큼) |
| **PR 6B-plan + PR 6B-impl 분리** | scope → plan → impl 3단계 | 작음 (각 단계 독립 review) |

추천: **PR 6B-plan + PR 6B-impl 분리** (PR 6 패턴 재사용)

---

## 11. Empirical basis

- PR 6A 의 smoke run 결과 (1119 untracked + ODIN2 - Music/catalog/ + probe_*.xml 다수 검출) 에서 JSON 출력은 정확하나 사람 검토 시 길이 부담
- Music Phase 1 6 commit + PR 6 docs commit 5건의 경우 사용자가 `git status --short` + `git diff --cached --name-only` + `git rev-list --left-right --count` 수동 audit 7항목 매번 수행
- Markdown report 1장이면 위 7항목 + 13 check 결과를 한 화면에 압축 가능
- 4단 운영 패턴(사전 보고/검토/의견/직시)의 *사전 보고* 단계에 직접 첨부 가능한 형식이 부재

---

## 12. Adoption note

본 PR 6B scope는 v2 operating policy의 *4단 운영 패턴* 자동화가 아니다. **Markdown report는 검토 자료의 표준화일 뿐, 의사결정 자체는 사람이 한다.** Tier 정의(v2 Adoption Order 5단계) 이후의 자동화 진입은 별도 결정.
