# PR 6B — Git Safe Push Audit Markdown Output (Implementation Plan)

**Status:** PLAN; repo-fixed pending; implementation not started.
**Scope source-of-truth:** `docs/pr6b_git_audit_markdown_scope.md` (repo-fixed at `85d5920`)
**PR 6A baseline:** `5e6a2b8` — `tools/git_safe_push_audit.py` JSON-only audit + `tests/test_git_safe_push_audit.py` 10 tests
**Adoption Order context:** v2 Adoption Order 3.5단계 (PR 6A 머지 후, PR 6C retrospective fixture 이전)

본 문서는 *implementation plan*만 정의한다. 도구 코드 변경은 별도 결정·별도 PR로 진행한다.

---

## 1. Implementation Target

### 1-1. 변경 대상

- `tools/git_safe_push_audit.py` — Markdown formatter + `--format` CLI 옵션 추가
- `tests/test_git_safe_push_audit.py` — Markdown output test 추가 + JSON 호환성 회귀 test 추가

### 1-2. 변경 면적 제약

- src/* 변경 0
- schema 변경 0
- runner_capability 변경 0
- TC YAML 변경 0
- prompts 변경 0
- generated/probe/catalog/reports staged 0

### 1-3. PR 6A 호환성

- `run_audit()` 함수 시그니처 유지 (`run_audit(*, cwd, base, expected_ahead, expected_paths, allowed_prefixes, do_fetch)`)
- `run_audit()` return dict 구조 유지 (schema_version=1, tool_version 그대로, 5 블록 + 13 checks)
- JSON output (`--format json`, default) byte-equivalent (단 `generated_at`/`run_id` 변동 인정)
- exit code 매핑 유지: PASS=0 / WARN=0 / FAIL=1

### 1-4. 실제 구현은 별도 승인

본 plan은 *어떻게* 구현할지의 설계만 정의한다. 실제 코드/테스트 작성은 별도 단계 + 별도 사용자 승인.

---

## 2. CLI Plan

### 2-1. 채택

- `--format` enum option, choices: `["json", "markdown", "md"]`
- 기본값: `"json"`
- `"md"`는 `"markdown"`의 alias (argparse `choices` 매개변수에 둘 다 등록, 내부에서 동일 분기)
- 잘못된 값은 argparse가 자동 차단 (`error: argument --format: invalid choice`)

### 2-2. argparse 등록 방식

```python
parser.add_argument(
    "--format",
    dest="output_format",
    choices=["json", "markdown", "md"],
    default="json",
)
```

- `dest`를 `output_format`으로 명시 (Python keyword `format` 회피)
- `args.output_format in ("markdown", "md")` 분기

### 2-3. 거부된 대안

- `--markdown` boolean flag 추가 — 거부 (PR 6B scope §2-2 참조, 옵션 폭증 risk)
- `--json` boolean flag 추가 — 거부 (PR 6A의 default 동작이 이미 JSON, 별도 옵션 불필요)
- JSON + Markdown 동시 출력 — 거부 (stdout 채널 1개 보장)

### 2-4. 기존 옵션 변경 0

- `--base`, `--expected-ahead`, `--expected-path`, `--allowed-prefix`, `--no-fetch`, `--cwd` 모두 PR 6A와 동일

---

## 3. Markdown Renderer Plan

### 3-1. 함수 시그니처

```python
def render_markdown_report(result: dict) -> str:
    """Render run_audit() result dict as a Markdown report.

    Pure function: no I/O, no git calls, no clock reads.
    Input: result dict from run_audit().
    Output: Markdown string (utf-8 safe, ends with newline).
    """
```

- 입력: `run_audit()`가 반환한 result dict 그대로
- 출력: 문자열 (호출자가 stdout에 쓰는 책임)
- 부수효과 0 (pure function)
- `result` dict 구조에 의존하지만 *변경하지 않음*

### 3-2. 단일 source 보장

- Markdown 분기는 `run_audit()`를 그대로 호출 → return dict를 `render_markdown_report(result)`에 전달
- JSON 분기와 동일한 dict 사용 → drift 차단
- result dict의 verdict/branch/staging/path_policy/checks/recommended를 모두 인용 (재계산 0)

### 3-3. 출력 인코딩

- PR 6A의 stdout binary write 패턴 그대로:
  ```python
  if args.output_format in ("markdown", "md"):
      payload = render_markdown_report(result)
      sys.stdout.buffer.write(payload.encode("utf-8"))
  else:
      payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
      sys.stdout.buffer.write(payload.encode("utf-8"))
  ```
- cp949 환경의 em-dash 회피
- 항상 newline으로 끝남 (`\n`)

---

## 4. Markdown Sections

### 4-1. 섹션 순서 (scope §3-2 그대로)

1. **Verdict header** (1 line) — `# Git Safe Push Audit — <VERDICT>`
2. **Summary line** (1 line) — `branch · ahead · behind · staged · untracked · base · target · generated_at · tool_version`
3. **Branch state** — current branch, base, target branch, ahead/behind count, fetch result (skipped/PASS/FAIL)
4. **Staged scope** — staged 파일 목록 (count + bullet list), expected_paths 매칭 결과 (PASS/FAIL + missing/unexpected 분리)
5. **Forbidden path check** — staged forbidden FAIL / untracked forbidden WARN / tracked dirty forbidden FAIL 분리
6. **Dirty/untracked summary** — tracked dirty count + 목록 (forbidden 매칭 별도 표시), untracked count (개별 목록 출력 X — 노이즈 회피)
7. **Failures** (FAIL이 있을 때만) — `- FAIL [<check_id>] <detail>` bullet list + `> Decision required: do not push` blockquote
8. **Warnings** (WARN이 있을 때만) — `- WARN [<check_id>] <detail>` bullet list
9. **Checks table** — 13 check를 ID / status / detail 표 형식
10. **Recommended push command** — `git push origin HEAD:<target-branch>` + force 금지 + human review reminder

### 4-2. 헤더/요약 line 형식

```
# Git Safe Push Audit — PASS

branch: master · ahead: 1 · behind: 0 · staged: 3 · untracked: 1119
base: origin/master · target: master
generated_at: 2026-05-08T00:38:32Z · tool_version: pr6-git-audit-v1
```

- 비결정값은 fixed-width 정렬 X (test 단순화)
- 모든 섹션 헤더는 `## ` (h2) 시작

### 4-3. Verdict별 강조

| Verdict | Failures 섹션 | Warnings 섹션 | "do not push" blockquote |
|---|---|---|---|
| PASS | 미출력 | 미출력 | 미출력 |
| WARN | 미출력 | 출력 | 미출력 |
| FAIL | 출력 | 출력(있을 때) | 출력 |

---

## 5. Push Command Plan

### 5-1. 형식

```
## Recommended push command

git push origin HEAD:<target-branch>

- `--force` / `--force-with-lease` 사용 금지
- Decision required: human review before push
```

### 5-2. Target branch 결정 (scope §4-2)

- `--base` 형식: `<remote>/<branch>` (예: `origin/master`)
- target-branch = `<branch>` (slash 이후 부분)
- 구현:
  ```python
  if "/" in base:
      remote, _, target_branch = base.partition("/")
  else:
      remote, target_branch = "origin", None  # 명시 오류 출력
  ```

### 5-3. 예외 처리

| 상황 | Markdown 출력 |
|---|---|
| `--base` 형식 비정상 | command line 미생성, `> Decision required: --base must be in 'remote/branch' form` blockquote |
| current branch 비어있음 (detached HEAD) | command line 미생성, `> Decision required: detached HEAD detected — resolve branch first` |
| current branch != target branch (ex: 작업 branch에서 master로 push 의도) | command line은 출력 (`HEAD:<target>` 형식이라 동작), `branch_current` WARN은 유지 |
| `--no-fetch` 지정 | summary line에 `fetch: skipped` 표기, push command 자체에는 영향 없음 |

### 5-4. 항상 포함되는 안전 문구

- `--force` 금지
- `--force-with-lease` 금지
- `Decision required: human review before push`

FAIL verdict 시:
- 추가로 `> Decision required: do not push` blockquote (§4-3 표 참조)

### 5-5. JSON `recommended.push_command` 필드 갱신

- 현재 PR 6A: `f"git push {remote_name} {branch}"` (예: `git push origin master`)
- PR 6B: `f"git push {remote_name} HEAD:{target_branch}"` (예: `git push origin HEAD:master`)
- **이는 JSON schema 호환성 변경**:
  - `schema_version`은 `1` 그대로 유지 (필드 이름/구조 변동 0, 값만 변경)
  - 단, byte-equivalent assertion은 무효 (`recommended.push_command` 값 변동)
  - `test_force_prohibition_notice_present`는 `recommended.push_command` 형식을 직접 검증하지 않으므로 회귀 risk 0
- 호출자 영향: PR 6A의 호출자는 `recommended.push_command`를 *문자열*로만 사용 → 형식 변경은 의미상 동일 push 명령

---

## 6. Test Plan

### 6-1. 필수 테스트

- [ ] **`test_markdown_output_pass_contains_verdict_header`** — staged docs only PASS 시 첫 줄 `# Git Safe Push Audit — PASS` 포함
- [ ] **`test_markdown_output_fail_contains_blocking_reason`** — `reports/run.html` staged FAIL 시 `## Failures` 섹션 + `Decision required: do not push` blockquote 포함
- [ ] **`test_markdown_output_warn_lists_untracked_forbidden`** — `reports/stray.html` untracked WARN 시 `## Warnings` 섹션 + `untracked_forbidden_report` detail 포함
- [ ] **`test_markdown_output_contains_recommended_push_command`** — 모든 verdict에서 `git push origin HEAD:master` line 출력
- [ ] **`test_markdown_output_contains_force_prohibition`** — 모든 verdict에서 `--force` / `--force-with-lease` 사용 금지 문구 포함
- [ ] **`test_json_default_output_unchanged`** — `--format` 미지정 시 JSON 출력의 schema keys + 13 checks IDs + verdict + recommended 5 키 모두 PR 6A와 동일
- [ ] **`test_markdown_output_human_review_reminder`** — 모든 verdict에서 `Decision required: human review before push` 포함
- [ ] **`test_markdown_output_checks_table_completeness`** — Markdown checks table에 13 check ID 모두 출현 (branch_current, remote_fetch, ahead_behind_count, head_minus_origin_empty, origin_minus_head_count, staged_files_list, tracked_dirty, untracked_count, untracked_forbidden_report, allowed_whitelist_match, forbidden_path_guard, candidate_whitelist_match, force_prohibition_notice)

### 6-2. 선택 / PR 6C 후보

- [ ] **`test_markdown_output_detached_head`** — detached HEAD 상태에서 `Decision required: detached HEAD detected — resolve branch first` 출력
- [ ] **`test_markdown_output_branch_warn`** — non-master branch 시 헤더 `WARN`, `## Warnings`에 `branch_current` 포함

### 6-3. JSON 호환성 검증 기준

- byte-identical 비교 **금지** (`generated_at`/`run_id`/`recommended.push_command` 변동 허용)
- 다음 항목을 keys/values 비교로 검증:
  - top-level keys: `schema_version`, `tool_version`, `run_id`, `generated_at`, `verdict`, `branch`, `staging`, `path_policy`, `checks`, `recommended`
  - `schema_version == 1`
  - `tool_version == "pr6-git-audit-v1"`
  - `verdict in {"PASS", "WARN", "FAIL"}`
  - `len(checks) == 13` 및 `{c["id"] for c in checks}` 집합 일치
  - `set(recommended.keys()) == {"push_command", "force_prohibited", "human_review_required", "note"}`
  - `recommended.force_prohibited is True`
  - `recommended.human_review_required is True`
  - `"READ-ONLY" in recommended.note`

### 6-4. Test infrastructure 정책 (PR 6A 그대로)

- pytest + `tmp_path` + 실제 `git init` (mock 없음)
- bare origin은 file path
- Markdown 검증은 substring assertion 우선, regex는 형식 한정
- `_make_repo`/`_stage_file`/`_check` 헬퍼 재사용

### 6-5. Read-only invariant 회귀

- 기존 `test_read_only_audit`는 JSON 호출 기준 → PR 6B에서 Markdown 호출도 read-only인지 검증할 보조 test (`test_read_only_audit_markdown`) 추가 후보 (필수 vs 선택 PR 6B implementation 단계에서 결정)

---

## 7. PR 분리

### 7-1. 추천: 단일 PR 6B

- `tools/git_safe_push_audit.py` Markdown formatter 추가
- `tests/test_git_safe_push_audit.py` 8 필수 + 2 선택 test 추가
- `recommended.push_command` 형식 변경 (`<remote> <branch>` → `<remote> HEAD:<branch>`)
- 변경 면적 작음 (PR 6A에 비례)

### 7-2. 거부: 분리

- formatter 추가 PR 6B-impl 와 push_command 형식 변경 PR 6B-fmt 분리는 비용 대비 이득 X
- Markdown formatter가 어차피 `recommended.push_command`를 그대로 인용하므로 형식 동시 변경이 자연스러움

### 7-3. PR 분리 옵션 (사용자 결정 시)

| 옵션 | 범위 |
|---|---|
| **단일 PR 6B** | formatter + `--format` 옵션 + push_command 형식 + tests 일괄 |
| **PR 6B-fmt + PR 6B-impl** | push_command 형식 변경 → Markdown formatter 추가 (2단) |
| **PR 6B-cli + PR 6B-render + PR 6B-tests** | CLI 옵션 + renderer 함수 + tests 3단 (과분리) |

추천: **단일 PR 6B**

---

## 8. Non-goals

본 PR 6B implementation은 다음을 **하지 않는다**:

- retrospective Music Phase 1 fixture 구현 (PR 6C)
- scope drift test 구현 (PR 6C)
- pre-commit hook 통합 (별도 PR)
- CI 통합 (별도 결정)
- file output 옵션 (`--output <path>` 등)
- color output (ANSI escape, terminal 의존)
- GitHub annotation 형식 (sarif, junit 등)
- policy v2 운영 적용
- PR 7 synthetic delta 선진입
- PR 8 anchor recommender 선진입
- TC YAML 변경
- runner_capability.yaml 변경
- schema 확장
- src/cli.py 변경 (서브커맨드 추가 금지)
- runner runtime 변경
- PR 6A의 13 check ID 추가/삭제
- JSON output에 새 필드 추가 (`markdown_report` 등)
- 새 verdict 추가 (PASS/WARN/FAIL 그대로)
- exit code 매핑 변경 (PASS=0/WARN=0/FAIL=1 그대로)

---

## 9. Risks

### 9-1. JSON compatibility

- **Risk:** `recommended.push_command` 형식 변경(`<remote> <branch>` → `<remote> HEAD:<branch>`)이 PR 6A의 외부 consumer를 깰 위험
- **완화:** §1-3 — schema_version/tool_version/필드 이름/구조 모두 유지. 값만 변경. byte-identical assertion 미사용. consumer는 push_command를 문자열로만 사용 → 의미상 동일 push 명령. test `test_json_default_output_unchanged`로 keys/13 check IDs/recommended 키 집합 회귀 검증

### 9-2. Push command ambiguity

- **Risk:** `--base` 형식 비정상 / detached HEAD 등 예외 상황에서 잘못된 push command 출력
- **완화:** §5-3 표 — base 비정상 시 command line 미생성 + 명시 오류 blockquote. detached HEAD 시 명시 오류. silent fallback 금지

### 9-3. Unicode/cp949 rendering

- **Risk:** Windows cp949 환경에서 em-dash (—) / arrow (→) 출력 시 PR 6A와 동일 인코딩 이슈
- **완화:** §3-3 — PR 6A의 utf-8 binary write 패턴 그대로. Markdown 분기도 동일 codepath. test에서 Markdown 출력의 utf-8 round-trip 가능 여부 substring assertion으로 보장

### 9-4. Output duplication / drift

- **Risk:** Markdown과 JSON이 동일 정보를 별도 경로로 derive하면서 drift 발생
- **완화:** §3-2 — `render_markdown_report(result)`는 result dict를 단일 source로 사용. 재계산 0. result dict 변경 0

### 9-5. Markdown ambiguity

- **Risk:** Markdown 형식 지정 모호 → 향후 변경 시 사용자 혼란
- **완화:** §4 섹션 순서 + §4-2 헤더 형식 + §5 push command 형식 + §6-1 substring assertion test로 형식 강제

### 9-6. Scope creep

- **Risk:** "이왕 만드는 김에" file output, color, GitHub annotation, --quiet 등 추가
- **완화:** §8 Non-goals 강제. 추가는 별도 PR

### 9-7. Checks table drift

- **Risk:** 13 check ID 중 일부가 코드에서 추가/삭제되면 Markdown table과 mismatch
- **완화:** `test_markdown_output_checks_table_completeness`로 13 check ID 출현 회귀. PR 6A의 check 추가/삭제는 PR 6B와 분리된 별도 결정

### 9-8. Push command 형식 변경 회귀

- **Risk:** PR 6A의 `recommended.push_command`가 `git push origin master` 형식이라고 외부 consumer가 가정하면 회귀
- **완화:** §1-3 — PR 6A 초기 도입이고 외부 consumer 0. test `test_force_prohibition_notice_present`도 push_command 형식 직접 검증 X. PR 6B 머지와 함께 필요 시 회귀 test 추가 후보

---

## 10. Decision boundary

### 10-1. 본 plan 문서 commit 시점의 단독 범위

#### Commit candidate

- `docs/pr6b_git_audit_markdown_implementation_plan.md` (NEW)

#### Excluded

- `tools/git_safe_push_audit.py` (PR 6B implementation에서 변경)
- `tests/test_git_safe_push_audit.py` (PR 6B implementation에서 변경)
- `docs/pr6b_git_audit_markdown_scope.md` (이미 `85d5920`에 commit됨)
- generated / probe / catalog / reports artifacts

#### Pre-commit verification

- staged 파일 명시적으로 plan 문서 1건만 허용
- src/schema/runner/tests/tools 변경 0
- generated 산출물 staged 0
- ahead/behind audit (fast-forward only)
- force/force-with-lease 미사용

### 10-2. Implementation 진입 조건

본 commit은 *plan 문서를 repo에 고정하는 행위*에 한정한다. **PR 6B implementation 진입은 별도 결정**이며 본 commit과 분리된다.

진입 시 사용자 명시 승인 필수:
- 단일 PR 6B / 분리 옵션 선택
- 변경 파일 명시 (`tools/git_safe_push_audit.py`, `tests/test_git_safe_push_audit.py`)
- 필수 8 + 선택 2 test 중 적용 범위 확정
- `recommended.push_command` 형식 변경 수용 여부

### 10-3. Adoption Order 위치

- v2 Adoption Order 3단계 = PR 6 implementation (PR 6A `5e6a2b8` 머지)
- 본 PR 6B는 **3.5단계 (PR 6A와 PR 7 사이)**
- PR 6C retrospective fixture는 4단계 진입 전 또는 후 별도 결정
