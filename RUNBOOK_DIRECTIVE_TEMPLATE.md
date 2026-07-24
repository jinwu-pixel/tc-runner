# RUNBOOK DIRECTIVE — 템플릿 v2

> 목적: 태스크마다 발생하던 **이중 게이트(Codex 검토 + 사용자 승인)** 를 blast radius에 비례해 재배치한다.
> 승인 판단을 앞으로 당기되(사전등록 DoD), **실행 권한은 exact-bytes 캡슐에 결박**한다.
> 선례 = CLAUDE.md §3.5 SMOKE 무중단(현재 same device·app·SMOKE 한정 — §8 승격 경로 참조).

**역할 고정**: Claude = 지시문 작성·tier 결정·검토·freeze / Codex = 실행 / 사용자 = 캡슐 승인·하드게이트 승인.
**불변**: tier·게이트·재분류 판단은 **Codex 금지**. Codex는 literal equality만 검사하고, 애매하면 STOP + 보고.

### v1 → v2 REVISE 사유 (실측 근거)
1. 승인이 exact bytes에 결박되지 않아 문서 drift 미탐지 — **실증**: v1 부록이 `ahead 2`라 했으나 실제 `HEAD==origin/master==b114c01`, `0/0`.
2. contamination 검사가 공검사 — **실증**: `tools/untracked_contamination_scan.py` `--protected` default `[]` → 인자 없는 호출은 대상 0건이라 무조건 exit 0.
3. Tier 0 범위가 production behavior까지 포함 가능 + 자동연속이 Codex에게 tier 판단을 요구(§4 충돌).
4. evidence bundle이 사람이 옮겨 적는 Markdown → self-attesting 아님.

---

## 0. 실행 캡슐 (EXECUTION CAPSULE) — 승인 단위

**Tier는 위험 설명일 뿐이고, 실행 권한은 캡슐이 결정한다.** Claude가 작성 시 아래를 고정하고, 사용자가 승인 시 서명한다. 실행 시점에 하나라도 불일치하면 **승인 자동 무효 + STOP**.

```
capsule_id:            RB-YYYYMMDD-<slug>
runbook_sha256:        <승인 시점 이 파일 전체의 SHA-256 — 승인 레코드에 기록, 파일 내부 자기참조 금지>
approval_ref:          <사용자가 채움>
approval_time:         <사용자가 채움 (KST)>

baseline_fingerprint:                       # 실행 시작 시 재측정해 일치 확인
  head_sha:            <sha>
  upstream_sha:        <origin/master sha>
  ahead_behind:        <N/M>                # 실측값. 하드코딩 금지
  index_fingerprint:   <staged blob SHA 정렬 해시>
  untracked_fingerprint: <git status --porcelain -uall 전체 untracked 집합 정렬 SHA>
  per_file_pre_run_sha:                     # dirty 파일 포함 — HEAD 아닌 실제 worktree
    <path>:            <sha256>

ordered_task_ids:      [T1, T2, ...]        # 순서 고정, capsule과 §2 Task 1:1

grant:
  allowed_write_paths: [<정확 path 집합>]   # 이 밖 write = 위반
  allowed_commands:    [<정확 argv 접두 집합>]
  forbidden_capabilities: [device, commit, push, network, schema, deps, production_src]

invalidation:          runbook_sha256 · baseline_fingerprint 중 하나라도 실행 시점과 불일치 → 승인 무효 + STOP
```

---

## 1. TIER (위험 설명 — 권한 아님)

| Tier | 정의 | 게이트 |
|---|---|---|
| **0** | **ALL of**: ① production·schema·config·deps **무변경** ② test-only characterization **OR** 비권위 문서 초안 **OR** 입력불변이 증명된 결정론 파생 ③ 단말·외부·네트워크 부작용 0 | 캡슐 승인 후 **자동연속.** Claude=verifier exit + spot-check 1개 |
| **1** | contract/schema/state 변경 | **이중 게이트 유지** |
| **2** | 비가역 (device·commit·push·migration) | **풀 게이트 + 태스크별 명시 승인**, batching 금지 |

각 Task의 tier·allowed path·forbidden capability는 **Claude가 캡슐에 사전 고정**한다. Codex는 literal equality만 검사(판단 금지).
> 근거: 이번 세션에서 게이트가 실제 잡은 결함(over-promotion·ledger 커플링·strict-shell 오염)은 전부 Tier 1/2. tiering은 그 catch를 보존하고 mechanical(Tier 0)만 batch.

---

## 2. 태스크 (capsule `ordered_task_ids`와 1:1)

각 Task를 복제해 채운다. DoD는 사람이 읽는 체크박스가 아니라 **verifier가 판정**한다.

### Task `<id>` — `<title>`

- **tier**: `<0/1/2>` (캡슐 고정값)
- **allowed_write_paths**: `[<capsule grant의 부분집합>]`
- **근거**: (승인된 설계? / 미승인이면 하드STOP §4)
- **RED / expected-initial-state**: (characterization은 `initial GREEN expected`, 실패 시 production 수정 없이 STOP — "RED가 곧 GREEN" 아님)
- **DoD (machine-checkable — verifier exit 0으로만 GREEN)**:
  - [ ] **file delta** = `allowed_write_paths`와 정확히 일치 (그 외 tracked-M / staged / untracked_added = 0). 기준 = `per_file_pre_run_sha` (HEAD 아님)
  - [ ] **new nodeid manifest** = 선언된 집합, **removed nodeid = 0** (`pytest --collect-only` 전/후 델타 — 함수명 비교 아님; parametrization 변화 포착)
  - [ ] **full pytest exit 0** (passed 감소·신규 skip/xfail 0)
  - [ ] **untracked delta = 0** (pre/post 전체 untracked 집합 동일 — 도구 기본 호출 아닌 full-set delta)
  - [ ] ledger digest `<hex>` / CSV byte-identical to `<frozen>` *(해당 트랙만)*
  - [ ] **task-specific 불변식** (예: production 무변경 증명 → `src/adb.py sha256 == <full sha>` 불변)

---

## 3. 자동연속 (Tier 0 전용 — Codex 판단 제거)

다음 **literal 조건 AND** 성립 시에만 STOP 없이 다음 Task 진입. 전부 판단이 아닌 비교/exit 확인:

1. 직전 Task **evidence verifier exit 0**
2. 다음 Task의 **pre-declared tier == 0** (캡슐에 이미 박힘 — Codex가 정하지 않음)
3. 다음 Task의 `allowed_write_paths` ⊆ 캡슐 grant (집합 포함 비교)
4. `runbook_sha256` · `untracked_fingerprint` · `index_fingerprint` 실행 시점 재확인 = 승인값과 동일

하나라도 불성립 → **STOP + 보고**. Tier 1/2 runbook은 자동연속 없음.

---

## 4. 하드 STOP 게이트 (Codex 판단 금지 — 무조건 STOP)

- commit / push (항상 별도 명시 승인 — CLAUDE.md §7)
- device 명령 (`adb push/install/uninstall`, 설정 변경, reboot, **locale 등 device write**)
- network 호출 / schema / state / migration / deps 변경
- **임의 DoD RED** (재도전은 원인 보고 후)
- **capsule drift** (baseline/runbook_sha256 불일치)
- **tier 재분류가 필요해 보이는 관찰** (재분류 금지 — STOP)
- 사전 미승인 설계 변경 필요 / 예상 외 untracked·broad staging 신호

---

## 5. evidence bundle (versioned JSON — 기계 생성)

Task별로 아래를 **verifier가 생성**한다. Tier 0 GREEN = `evidence verifier exit 0` (Markdown 체크박스 아님).

```json
{
  "schema_version": 1,
  "capsule_id": "...", "task_id": "...", "tier": 0,
  "steps": [{"command": "...", "cwd": "...", "exit_code": 0}],
  "files": {"<path>": {"sha_before": "...", "sha_after": "..."}},
  "pytest": {"exit_code": 0, "passed": 0, "junit_sha256": "..."},
  "nodeids": {"added": ["..."], "removed": []},
  "workspace_delta": {
    "tracked_modified": ["..."], "staged": [],
    "untracked_added": [], "untracked_removed": []
  },
  "ledger": {"digest": "...", "determinism_exit": 0, "csv_byte_identical": true},
  "dod": [{"name": "...", "verdict": "GREEN", "verifier_exit": 0}],
  "verdict": "validate PASS | runtime PASS | manual evidence observed | BUG-GAP observed | NOTE"
}
```

어휘 = CLAUDE.md §2.2 4종 한정사. 단독 `PASS` 금지.

---

## 6. Claude 검토 계약

- **Tier 0**: evidence bundle `verifier_exit == 0` 확인 + 불변식 **1개 spot-check**(전량 재도출 아님).
- **Tier 1/2**: 풀 독립 재검증 유지.

> Tier 0 검토가 값싸지려면 §5 bundle이 self-attesting(file delta·nodeid manifest·untracked delta·pytest exit)이어야 한다. `contract_drift_ledger`의 byte-deterministic 패턴이 그 전제.

---

## 7. 금지 (불변)

- broad add (`git add .` / `-A` / 디렉토리) · force / non-fast-forward push
- sibling repo(thor2j-tc-appium 등) cross-commit · device write(locale 등) 자동화
- **Codex mid-run tier/gate/재분류 판단** · placeholder를 implemented인 척 보고

---

## 8. SSOT 코드화 경로 (별도 승인 게이트)

- §3.5는 현재 **same device·app·SMOKE 한정**. 재사용 정책으로 승격 시 §3.x 신규 규칙 + §8.2 `proposed` row → 사용자 승인(§8.3). 임의 본문 반영 금지.
- 승격 시 **CLAUDE.md AND `AGENTS.md`(Codex가 실제 따르는 SSOT) 동시 정렬** 필요.
- **NOTE(미수정)**: 현 `AGENTS.md`는 CLAUDE.md의 기계 치환본으로 보이며 §7.1 source가 `~/.Codex/AGENTS.md`로 적혀 있음(실제 글로벌 정책 = `~/.claude/CLAUDE.md`). SSOT 정렬 시 사용자 확인 필요.

---
---

# 부록 A — 파일럿 `RB-20260723-d0-char` (T0-CHAR): **Task 2 only**

> v1 부록의 결함(HEAD 기준 single-file 증명 불가·rc 계약 미결·A-6 오기·nodeid 근사)을 반영. 파일럿은 exact-argv characterization 1건으로 축소.

## 캡슐

```
capsule_id:   RB-20260723-d0-char
runbook_sha256: <승인 시 기록>
baseline_fingerprint:
  head_sha:     b114c01
  upstream_sha: b114c01
  ahead_behind: 0/0            # 실측 (v1의 "ahead 2"는 stale — 정정)
  per_file_pre_run_sha:        # worktree dirty: D0 4파일 미커밋
    src/adb.py:       c9f6a5dff5f30250ce20dc79f8867d304056a161d634033f59e55df827c7e562
    src/cli.py:       <M — pre-run 측정>
    tests/test_adb.py:<M — pre-run 측정>
    tests/test_cli.py:<M — pre-run 측정>
선결:  D0 커밋 경계 확정 필요. 미확정이면 baseline = per_file_pre_run_sha(HEAD 아님)로 delta 계산.
ordered_task_ids: [T0-CHAR-2]
grant:
  allowed_write_paths: [tests/test_adb.py]
  allowed_commands:    [venv pytest, git status/diff/collect-only (read-only)]
  forbidden_capabilities: [device, commit, push, schema, deps, production_src, network]
```

## Task `T0-CHAR-2` — screenshot/dump exact-argv characterization

- **tier**: 0
- **allowed_write_paths**: `[tests/test_adb.py]`
- **근거**: D0 **A-7 / 설계 §6** (원격 경로 `/data/local/tmp` confine) — shipped, 신규 설계 아님 (v1의 "A-6"은 오기 — 정정)
- **expected-initial-state**: **initial GREEN expected** (현 동작 고정). 실패 시 **production 수정 없이 STOP**.
- **DoD**:
  - [ ] file delta = `{tests/test_adb.py}` 정확히 (그 외 tracked-M/staged/untracked_added = 0; 기존 D0 dirty 3파일은 pre-run SHA 불변으로 확인)
  - [ ] new nodeid = 선언된 집합(authoring 시 `--collect-only`로 pin), removed = 0
  - [ ] full pytest exit 0
  - [ ] untracked delta = 0 (pre/post full-set)
  - [ ] `src/adb.py sha256 == c9f6a5dff5f3…c7e562` 불변 (production 무변경 증명)

## Task `T0-CHAR-1` — `device_serial()` rc/None — **BLOCKED**

- **선결 계약 결정 필요**: `rc≠0` 시 반환 계약이 미정. **stdout 반환 고정 = Tier 0** / **`None` 변경 = production 계약 변경 = Tier 1**.
- 계약 결정 전 파일럿 제외. (Tier 판정이 계약 결정에 종속되므로 Claude가 사전 고정 불가 → 캡슐 편입 금지.)

---

## D0 evidence 정정 (본 리뷰 반영)

이전 D0 freeze 보고의 `contamination scan: 0`은 **공검사**(도구 기본 `--protected=[]`)였으므로 증거로 무효. 재측정(pre/post full untracked delta) 전까지 **`unproven`** 으로 정정한다. D0 변경은 tracked 4파일 **수정(M)** 이라 untracked phantom 개연은 낮으나, pre-D0 baseline 부재로 **증명은 미완**.
