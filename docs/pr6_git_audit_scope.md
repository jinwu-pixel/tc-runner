# PR 6 — Git Safe Push Audit Script (Scope Proposal)

**Status:** SCOPE PROPOSAL (no code change, no commit until approved)
**Adoption Order context:** v2 Adoption Order 2단계 (운영 노트 anchor 다음 단계, Tier 정의 이전)
**Empirical basis:** Music Phase 1 (SMOKE_01~06)에서 매 commit·push마다 사용자가 수동 수행한 audit 7항목

본 문서는 *scope*만 정의한다. 도구 구현은 별도 결정·별도 PR로 진행한다.

---

## 1. 목적

- commit/push 전 반복 **수동 audit 비용 절감** (Music Phase 1에서 매 SMOKE마다 수행한 ahead/behind/staged/forbidden-path 7항목 점검을 자동화)
- generated/probe/catalog/reports **실수 commit 방지** (영구 비커밋 정책 기계 검증)
- **fast-forward only / force 금지 원칙 기계 검증**
- v2 Tier 자동화 적용 전 **git safety baseline 확보** (Tier 0/1/2 정의 *전에* 도입해야 batch commit risk를 줄일 수 있음)

---

## 2. Non-goals

다음은 본 도구가 **하지 않는** 일이다:

- **의미적 testdata 오류 검출 아님** — TC YAML의 anchor 선택 오류, validate_tc.py가 잡는 schema 위반, runtime FAIL 등은 별도
- **anchor drift 검출 아님** — preflight/catalog/delta로 분리됨
- **runtime 검증 대체 아님** — `cli run` 결과 평가는 별도 영역
- **policy v2 즉시 적용 아님** — 본 도구 도입은 audit 자동화 한정. Tier/sentinel/batch commit 운영 적용은 별도 결정
- **PR 7 synthetic delta 선진입 아님** — delta 신뢰성 측정은 PR 7 scope

---

## 3. 검사 항목

### 3-1. Branch / remote state

- **current branch 확인** — `master` 이외에서 실행 시 INFO (master 강제 아님, 다만 push target 명시 필요)
- **origin/master fetch 후 ahead/behind 확인** — `git fetch origin master` 후 `git rev-list --left-right --count HEAD...origin/master`
- **`HEAD..origin/master` empty 확인** — non-empty 시 FAIL (behind 상태 = fast-forward 불가)
- **`origin/master..HEAD` expected commit count 확인** — 사용자가 기대 commit 수 지정 시 mismatch면 FAIL

### 3-2. Working tree state

- **staged files 확인** — `git diff --cached --name-only`
- **tracked dirty 확인** — `git status --short` 중 `^[MTARDC][MTARDC]` 또는 ` [MTARDC]` 라인
- **untracked report 출력** — INFO 레벨, FAIL 아님 (사전 untracked는 정상)

### 3-3. Path policy

- **allowed path whitelist** — staged 경로가 whitelist에 모두 포함되는지 확인
- **forbidden/generated path guard** — staged 경로가 forbidden 패턴(§4)에 매칭되면 FAIL
- **candidate commit path whitelist** — 사용자가 expected commit path 목록을 인자로 전달하면 정확 일치 검증

### 3-4. Force push 정책

- **force push 금지 안내** — 본 도구는 push를 직접 수행하지 않으나, 출력 리포트에 `git push` 명령 권장형(`git push origin HEAD:master` 등)을 명시. `--force`/`--force-with-lease` 사용 금지를 출력에 포함

---

## 4. Forbidden paths

다음 경로/패턴이 staged에 포함되면 FAIL:

- `generated/`
- `reports/`
- `**/catalog/` (모든 앱 단말 폴더의 `catalog/` 디렉토리)
- `probe_*.xml`
- `**/probe_*.xml`
- `_probe_*.py` (root)
- `**/probe_dump_*.xml`
- ODIN2 app catalog/probe/report outputs:
  - `ODIN2 - Music/catalog/`
  - `ODIN2 - Music/probe_*.xml`
  - `ODIN2 - My gallary/catalog/`
  - `ODIN2 - minifile/catalog/`
- root probe dumps: `probe_dump_*.xml`, `ui_*.xml`, `popup_*.xml`
- 기타 generated artifact: `*.html` (reports), `screenshot_*.png` (root), `manifest.json` (preflight 산출물 경로 한정)

명시:

- forbidden 패턴 목록은 본 scope의 **§4 본문이 source-of-truth**. 구현 시 별도 config 파일로 분리 가능하나 본 문서가 baseline.
- **untracked 상태로 존재하는 forbidden 파일은 FAIL이 아님** (영구 비커밋 정책 자체 — 그저 untracked로 남는 것은 정상). FAIL 트리거는 *staged*에 포함될 때.

---

## 5. Output format

### 5-1. JSON (machine-readable)

```json
{
  "schema_version": 1,
  "tool_version": "pr6-git-audit-v1",
  "run_id": "<timestamp>",
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
    "untracked_count": 42
  },
  "path_policy": {
    "allowed_whitelist_match": true,
    "forbidden_violations": [],
    "candidate_whitelist_match": true
  },
  "checks": [
    {"id": "behind_zero", "level": "PASS", "detail": "..."},
    {"id": "forbidden_path_guard", "level": "PASS", "detail": "..."},
    ...
  ]
}
```

### 5-2. Markdown (human-readable)

- 헤더: 1 line PASS/WARN/FAIL verdict + branch summary
- 섹션:
  - Branch state (ahead/behind/HEAD..origin/origin..HEAD)
  - Staged scope (file 목록 + path policy 결과)
  - Forbidden path check
  - Recommended push command (force 금지 명시)
- 본 문서 형식과 호환되는 형태로 출력

### 5-3. Verdict 분류

- **PASS** — 모든 check 통과, commit/push 진행 권장
- **WARN** — 비차단성 이슈 (예: untracked forbidden 산출물 존재, current branch가 master 아님). commit/push 가능하나 사용자 확인 권장
- **FAIL** — 차단성 이슈 (behind/diverged/forbidden staged/whitelist mismatch). **commit/push 중단 권고**

---

## 6. Acceptance criteria

본 도구는 다음을 만족해야 한다:

- [ ] proposal 문서 commit 같은 단독 docs commit에서 **PASS** 가능
- [ ] **generated artifact staged** 시 **FAIL** (예: `reports/foo.json`이 staged면 차단)
- [ ] **unexpected staged path** 시 **FAIL** (whitelist 불일치)
- [ ] **behind origin/master** 시 **FAIL** (HEAD..origin non-empty)
- [ ] **diverged branch** 시 **FAIL** (양방향 non-empty)
- [ ] **untracked generated artifacts**는 **WARN 또는 INFO**로 보고 (staged가 아니면 FAIL 아님)
- [ ] **force push는 사용하지 않도록** 보고 본문에 명시
- [ ] Music Phase 1 history 6 commit 모두 본 도구로 retrospective audit 시 **PASS** 출력 (회귀 검증)
- [ ] cross-platform 동작 (Windows + POSIX) — path separator는 forward-slash로 정규화
- [ ] **본 도구 자체가 push를 수행하지 않음** (READ-ONLY audit)

---

## 7. Implementation notes (deferred)

본 §7은 구현 단계 진입 시 별도 채움. scope proposal 단계에서는 placeholder.

후보 구현 위치:

- `tools/git_safe_push_audit.py` (제안)
- `src/cli.py` 서브커맨드 추가 (`cli git-audit`) — Source-of-truth Policy 적용 시 schema/test 동시 변경 동반

---

## 8. Out-of-scope deferred

다음은 본 PR 6의 **out-of-scope** — 별도 PR/scope:

- pre-commit hook 통합 (PR 6+1 후보)
- CI 통합 (별도 결정)
- batch commit candidate manifest 자동 생성 (v2 §8-4 영역, 별도)
- PR 7 synthetic delta measurement (별도)
- PR 8 anchor recommender (별도)

---

## 9. Decision boundary

본 scope 문서를 commit하는 시점에 적용되는 단독 범위:

### Commit candidate

- `docs/pr6_git_audit_scope.md` (only)
- (option) `docs/tc_runner_operating_policy_v2_proposal.md` — Status 라인 정정만 포함된 후속 commit

### Excluded

- `docs/tc_template.yaml`
- `docs/tc_writing_guide.md`
- generated / probe / catalog / reports artifacts
- `tools/` 코드 (구현 PR에서 별도 도입)

### Pre-commit verification

- staged file은 **명시적으로 지정된 docs 파일만** 허용
- src/schema/runner/tests 변경 0
- generated 산출물 staged 0
- ahead/behind audit 통과 (fast-forward only)

### Adoption note

본 commit은 *scope 문서를 repo에 고정하는 행위*에 한정한다. **PR 6 구현 진입은 별도 결정**이며 본 commit과 분리된다.
