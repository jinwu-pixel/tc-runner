# PR 6 — Git Safe Push Audit Script (Implementation Plan)

**Status:** PLAN; repo-fixed at `6f6aceb`; PR 6A implemented at `5e6a2b8`; PR 6B/6C deferred.
**Scope source-of-truth:** `docs/pr6_git_audit_scope.md` (repo-fixed at `c68e045`)
**Adoption Order context:** v2 Adoption Order 2단계 (운영 노트 anchor 다음, Tier 정의 이전)
**Empirical basis:** Music Phase 1 (SMOKE_01~06)에서 매 commit·push마다 사용자가 수동 수행한 audit 7항목

본 문서는 *implementation plan*만 정의한다. 도구 코드는 별도 결정·별도 PR로 진행한다.

---

## 1. Implementation Decision

### 1-1. 채택 위치

- **`tools/git_safe_push_audit.py`** (standalone script)
- 진입 방식: `python tools/git_safe_push_audit.py [options...]`
- 결과 출력: stdout JSON + (옵션) Markdown report

### 1-2. 거부된 대안

- **`src/cli.py` 서브커맨드 (`cli git-audit`) 추가** — 거부
  - 이유: Source-of-truth Policy 적용 시 schema/test/docs 동시 변경 동반 → 변경 면적 큼
  - PR 6 1차 도입에서는 standalone이 회귀 위험 최소

- **pre-commit hook 직접 통합** — 거부 (PR 6 out-of-scope)
  - 이유: PR 6은 *audit* 도구. hook 통합은 별도 결정 (PR 6+1 후보)

- **CI 통합** — 거부 (PR 6 out-of-scope)
  - 이유: 별도 인프라 결정 필요

### 1-3. 채택 사유 요약

- runner runtime과 직접 결합하지 않음 (audit은 pre-push read-only)
- 변경 면적 최소: src/* 0, schema 0, runner_capability 0
- 회귀 위험 낮음: TC 실행 경로 0 영향
- 이후 필요 시 CLI wrapper 또는 hook 통합으로 승격 가능

---

## 2. Source-of-truth Boundary

### 2-1. 변경 후보 (PR 6 1차 구현)

- `tools/git_safe_push_audit.py` (NEW)
- `tests/test_git_safe_push_audit.py` (NEW)
- `docs/pr6_git_audit_implementation_plan.md` (이 문서)
- (필요 시) `docs/pr6_git_audit_scope.md` status line 정정
- (필요 시) `docs/tc_runner_operating_policy_v2_proposal.md` PR 번호 정합성 정정

### 2-2. 변경 금지

- TC YAML (`exported_tc1/`, `ODIN2 - */`, `golden_tc_set/`)
- runner runtime (`src/runner/`, `src/cli.py`, `src/parser/`, `src/schema/`)
- TC schema (`tc_step_schema.json`)
- runner capability (`tc_prompts/runner_capability.yaml`)
- prompts (`tc_prompts/`)
- generated artifacts (`generated/`, `reports/`, `**/catalog/`)
- probe outputs (`probe_*.xml`, `_probe_*.py`, `**/probe_dump_*.xml`)
- policy v2 운영 적용 문구 (`docs/tc_runner_operating_policy_v2_proposal.md` Status 라인 외)

### 2-3. Source-of-truth Policy 적용 범위

본 PR 1차 구현에서는 Source-of-truth Policy의 *schema/code/test/docs 정렬* 요건이 다음과 같이 한정됨:

- **schema**: 본 PR에서 신규 schema 추가 없음 → 정렬 대상 없음
- **code**: `tools/git_safe_push_audit.py` 단일 진입점
- **test**: `tests/test_git_safe_push_audit.py`
- **docs**: scope (`pr6_git_audit_scope.md`) + plan (이 문서)

drift 위험: scope의 §4 forbidden paths 목록과 도구의 forbidden 패턴 정의가 분리될 가능성. 완화책 → §5-3 참조.

---

## 3. Core Checks

scope §3을 그대로 구현한다. 추가/감면 없음.

### 3-1. Branch / remote state

| Check ID | 동작 | 결과 레벨 |
|---|---|---|
| `branch_current` | `git branch --show-current` | 비-master면 INFO |
| `remote_fetch` | `git fetch origin master --quiet` | 실패 시 FAIL |
| `ahead_behind_count` | `git rev-list --left-right --count HEAD...origin/master` | numeric만 PASS, parse 실패 시 FAIL |
| `head_minus_origin_empty` | `git rev-list HEAD..origin/master` empty 여부 | non-empty 시 FAIL (behind) |
| `origin_minus_head_count` | `git rev-list origin/master..HEAD` count | expected count 인자 mismatch 시 FAIL |

### 3-2. Working tree state

| Check ID | 동작 | 결과 레벨 |
|---|---|---|
| `staged_files_list` | `git diff --cached --name-only` | 항상 보고 (verdict 자체 판정 X) |
| `tracked_dirty` | `git status --porcelain` 중 `^[MTARDC ][MTARDC]` filter | 0 외 INFO (FAIL 아님 — staging은 별도 check) |
| `untracked_count` | `git status --porcelain` 중 `^\?\?` count | INFO 보고만 |

### 3-3. Path policy

| Check ID | 동작 | 결과 레벨 |
|---|---|---|
| `allowed_whitelist_match` | staged 경로가 whitelist에 모두 매칭 (인자 제공 시) | mismatch FAIL |
| `forbidden_path_guard` | staged 경로가 forbidden 패턴(§5-1)에 매칭 | match 시 FAIL |
| `candidate_whitelist_match` | expected commit path 정확 일치 (인자 제공 시) | mismatch FAIL |
| `untracked_forbidden_report` | untracked 중 forbidden 패턴 매칭 | match 시 WARN (FAIL 아님) |

### 3-4. Force push 정책

| Check ID | 동작 | 결과 레벨 |
|---|---|---|
| `recommended_push_command` | output에 `git push origin HEAD:master` 명시 | 항상 출력 |
| `force_prohibition_notice` | output에 `--force` / `--force-with-lease` 사용 금지 명시 | 항상 출력 |

본 도구는 **push를 직접 수행하지 않는다.** READ-ONLY audit.

---

## 4. Path Normalization

### 4-1. 정규화 규칙

- 모든 비교 경로는 **forward-slash로 정규화**
- 구현 시 `pathlib.PurePosixPath(p).as_posix()` 또는 동등한 변환 사용
- forbidden path matching 전에 반드시 정규화 적용
- glob 매칭은 `fnmatch.fnmatchcase` 또는 `pathlib.PurePath.match` 사용

### 4-2. Windows ↔ POSIX 흡수

- `git diff --cached --name-only`는 항상 forward-slash 출력 (git 자체 정책)
- 그러나 인자로 받는 candidate path는 사용자 입력일 수 있으므로 강제 정규화
- ODIN2 단말 폴더의 공백 포함 경로 (`"ODIN2 - Music"`)는 quoting 유지

### 4-3. Cross-platform test 매트릭스

- Windows test: 본 개발 환경 (PowerShell, 백슬래시 네이티브)
- POSIX test: 가능 시 CI 또는 WSL (단, PR 6 1차에서는 Windows-only PASS 인정 + POSIX 호환 코드 작성)

---

## 5. Forbidden Path Policy

### 5-1. Source-of-truth

- **scope `pr6_git_audit_scope.md` §4를 baseline source-of-truth로 사용**
- 도구 내부 패턴 목록은 §4와 정확 일치해야 함
- 향후 외부 config 파일로 분리 가능하나 PR 6 1차에서는 도구 코드 내 상수로 보유

### 5-2. Forbidden staged paths (요약)

scope §4 그대로:

- `generated/`
- `reports/`
- `**/catalog/`
- `probe_*.xml`
- `**/probe_*.xml`
- `_probe_*.py`
- `**/probe_dump_*.xml`
- `ODIN2 - Music/catalog/`
- `ODIN2 - Music/probe_*.xml`
- `ODIN2 - My gallary/catalog/`
- `ODIN2 - minifile/catalog/`
- root: `probe_dump_*.xml`, `ui_*.xml`, `popup_*.xml`
- `*.html` (reports), `screenshot_*.png` (root), `manifest.json` (preflight 산출물 경로 한정)

### 5-3. Drift 완화

- 도구 코드의 패턴 상수와 scope §4 사이의 drift 검증을 위해, **test에서 scope 문서를 직접 parse하여 패턴 일치 확인** (선택적, PR 6C 후보)
- 1차 구현에서는 코드 commit 시 scope 문서 §4를 docstring/comment로 재기재 금지 (drift source 증가)
- scope 변경 시 plan/도구/test 동시 갱신 의무화

### 5-4. Untracked vs staged 구분

- **staged forbidden path → FAIL** (commit 차단)
- **untracked forbidden path → WARN** (영구 비커밋 정책 자체이므로 untracked 자체는 정상)
- **tracked dirty forbidden path → FAIL** (이미 추적 중이지만 dirty라는 것은 비정상 상태)

---

## 6. Output Schema

### 6-1. JSON output

```json
{
  "schema_version": 1,
  "tool_version": "pr6-git-audit-v1",
  "run_id": "<UTC timestamp YYYYMMDDTHHMMSSZ>",
  "generated_at": "<ISO8601>",
  "verdict": "PASS|WARN|FAIL",
  "branch": {
    "current": "master",
    "ahead": 1,
    "behind": 0,
    "head": "<sha>",
    "origin_master": "<sha>",
    "head_minus_origin_empty": true,
    "origin_minus_head": ["<sha> <subject>"]
  },
  "staging": {
    "staged_files": ["docs/..."],
    "tracked_dirty": [],
    "untracked_count": 42,
    "untracked_forbidden": []
  },
  "path_policy": {
    "allowed_whitelist_match": true,
    "allowed_whitelist_violations": [],
    "forbidden_violations": [],
    "candidate_whitelist_match": true,
    "candidate_whitelist_violations": []
  },
  "checks": [
    {"id": "head_minus_origin_empty", "level": "PASS", "detail": "..."},
    {"id": "forbidden_path_guard", "level": "PASS", "detail": "..."}
  ],
  "recommended": {
    "push_command": "git push origin HEAD:master",
    "force_prohibited": true
  }
}
```

### 6-2. Markdown output

- 헤더 1 line: `verdict: PASS|WARN|FAIL — branch=master, ahead=N, behind=M`
- 섹션 순서:
  1. Branch state (ahead/behind/HEAD..origin/origin..HEAD)
  2. Staged scope (file 목록 + path policy 결과)
  3. Forbidden path check (staged FAIL + untracked WARN 분리)
  4. Recommended push command (force 금지 명시)
- 본 plan 문서 형식과 호환

### 6-3. Verdict 매핑

| Trigger | Verdict |
|---|---|
| 모든 check PASS | PASS |
| WARN 있고 FAIL 없음 | WARN |
| FAIL 1개 이상 | FAIL |

---

## 7. Test Plan

### 7-1. 필수 케이스

- [ ] **`test_docs_only_pass`** — docs/ 만 staged, expected path 일치, ahead=1, behind=0 → PASS
- [ ] **`test_generated_artifact_staged_fails`** — `reports/foo.json` staged → FAIL (`forbidden_path_guard`)
- [ ] **`test_unexpected_staged_path_fails`** — whitelist 인자 제공 시 mismatch → FAIL (`candidate_whitelist_match`)
- [ ] **`test_behind_origin_fails`** — `HEAD..origin/master` non-empty → FAIL (`head_minus_origin_empty`)
- [ ] **`test_diverged_branch_fails`** — 양방향 non-empty → FAIL
- [ ] **`test_untracked_generated_warn`** — untracked `reports/foo.json` 존재 → WARN (FAIL 아님)
- [ ] **`test_candidate_whitelist_mismatch_fails`** — expected = `[a.md, b.md]`, staged = `[a.md, c.md]` → FAIL
- [ ] **`test_force_prohibition_notice_present`** — output에 `--force` 금지 문구 포함
- [ ] **`test_windows_path_normalization`** — `docs\foo.md` 입력 → `docs/foo.md`로 정규화 후 매칭
- [ ] **`test_read_only_audit`** — 도구 실행 후 git index/working tree 변동 0 확인

### 7-2. 선택 케이스 (PR 6C 또는 별도)

- [ ] **`test_retrospective_phase1_passes`** — Music Phase 1 6 commit 모두 audit 시 PASS
  - 비용 큼: fixture 또는 actual git history 의존
  - PR 6A에서 분리, PR 6C 또는 별도 PR로 보류
- [ ] **`test_scope_doc_pattern_consistency`** — scope §4와 도구 코드 상수 정합 (drift 방지)

### 7-3. Test infrastructure

- pytest 사용 (기존 `tests/` 디렉토리 패턴 준수)
- git fixture: `tmp_path` + `git init` + 인위적 commit/index 상태 구성
- mock 사용 최소화 — actual `subprocess.run("git ...")` 우선 (기존 정책: integration tests must hit real DB와 같은 정신)

---

## 8. PR 분리 전략

### 8-1. 추천 분리 (단계적)

| PR | 범위 | 변경 면적 |
|---|---|---|
| **PR 6A** | standalone script skeleton + JSON output + 핵심 unit tests (§7-1 항목) | 작음 — `tools/`, `tests/` 신규 |
| **PR 6B** | Markdown output + recommended push command 출력 + Markdown 포맷 test | 작음 — 기존 도구 확장 |
| **PR 6C** | retrospective fixture (Music Phase 1 6 commit) + scope drift test | 중간 — fixture 구축 비용 |

### 8-2. 단일 PR 옵션

- 장점: 한 번의 review, 한 번의 commit chain
- 단점:
  - retrospective fixture 비용이 합쳐져 PR 크기 증가
  - 회귀 위험 분리 불가 (한 PR에서 회귀 시 전부 revert)
- 결론: **PR 6A/B/C 분리 추천**, 단 사용자 결정에 따라 단일 PR 가능

### 8-3. 적용 순서

1. PR 6A → review → commit → push (fast-forward)
2. (대기) — 사용자 결정으로 PR 6B 진입
3. PR 6B → review → commit → push
4. (대기) — 사용자 결정으로 PR 6C 진입
5. PR 6C → review → commit → push

각 PR 사이에 **사용자 명시 승인** 필수.

---

## 9. Non-goals

본 PR 6 1차 구현은 다음을 **하지 않는다**:

- PR 6 implementation 즉시 시작 (본 plan 문서는 plan만)
- 도구가 push를 직접 수행 (READ-ONLY 유지)
- pre-commit hook 통합 (PR 6+1 후보)
- CI 통합 (별도 결정)
- policy v2 운영 적용 (Adoption Order 별도 단계)
- PR 7 synthetic delta 선진입
- PR 8 anchor recommender 선진입
- anchor drift 검출 포함 (preflight/catalog/delta 영역)
- runtime 검증 대체 (`cli run` 영역)
- TC YAML 변경
- runner_capability.yaml 변경
- schema 확장

---

## 10. Risks

### 10-1. False confidence

- 도구가 PASS를 줘도 *의미적 testdata 오류*는 검출 X
- 사용자가 도구 PASS = TC 정답이라고 오해할 위험
- 완화: scope §2 Non-goals + plan §9 Non-goals 양쪽에 명시. 출력에도 `READ-ONLY git audit only — does not validate TC content` 한 줄 포함

### 10-2. Path pattern drift

- scope §4 forbidden 목록과 도구 코드 상수 사이 drift
- 완화: §5-3 — 향후 scope 문서 직접 parse test (PR 6C 후보). 1차에서는 docstring 재기재 금지로 drift source 최소화

### 10-3. Windows/POSIX mismatch

- `git diff --cached --name-only`는 forward-slash 출력이지만 사용자 입력 candidate path는 백슬래시 가능
- 완화: §4 강제 정규화. test에 `test_windows_path_normalization` 포함

### 10-4. Fixture overbuild

- retrospective audit fixture (Music Phase 1 6 commit)는 비용 큼
- 완화: §8 PR 6C로 분리. PR 6A/B에서는 기본 fixture만

### 10-5. Scope creep

- "이왕 만드는 김에" pre-commit hook / CI / batch commit manifest 자동 생성 등 추가 위험
- 완화: §9 Non-goals 강제. 추가는 별도 PR/별도 결정

### 10-6. 4단 운영 패턴 우회 위험

- 도구가 PASS를 주면 사용자가 *사전 보고/검토/의견* 단계를 생략할 위험
- 완화: 도구 출력에 `Decision required: human review before push` 한 줄 포함. 4단 운영 패턴은 v2 Adoption Order 후속 단계에서만 자동화 진입 (Tier 정의 이후)

---

## 11. Decision boundary

본 plan 문서를 commit하는 시점의 단독 범위:

### Commit candidate

- `docs/pr6_git_audit_implementation_plan.md` (NEW)
- `docs/pr6_git_audit_scope.md` (status line 정정)
- `docs/tc_runner_operating_policy_v2_proposal.md` (PR 6 anchor recommender → PR 8 정정)

### Excluded

- `tools/git_safe_push_audit.py` (구현 PR에서 도입)
- `tests/test_git_safe_push_audit.py` (구현 PR에서 도입)
- `docs/tc_template.yaml`, `docs/tc_writing_guide.md`
- generated / probe / catalog / reports artifacts

### Pre-commit verification

- staged file은 명시적으로 지정된 docs 파일만 허용
- src/schema/runner/tests 변경 0
- generated 산출물 staged 0
- ahead/behind audit (fast-forward only)
- force/force-with-lease 미사용

### Adoption note

본 commit은 *plan 문서를 repo에 고정하는 행위*에 한정한다. **PR 6A 구현 진입은 별도 결정**이며 본 commit과 분리된다.
