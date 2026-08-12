# Shell-RC Producer Reconcile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the impossible tracked-YAML-name-to-workbook-name join with a fail-closed 12 tracked YAML / 14 workbook source selector / 15 blocker binding producer reconciliation, while preserving workbook, producer source, and tracked YAML bytes.

**Architecture:** Appendix A captures source rows by exact `(sheet, source_no, source_functionality_effective)` selectors and emits P0 schema v3. Appendix B reads and validates the 12 tracked YAML aliases/sources, binds the resulting 14 workbook identities to 14 producer documents, and then binds 15 tracked blocker steps through an explicit source selector; Appendix C validates and publishes those namespaces separately. PowerShell self-checks and Python tests freeze the cross-language manifest, aggregate semantics, schema, cardinalities, and SHA identities.

**Tech Stack:** Windows PowerShell 5.1, embedded JavaScript for `node_repl`, Python 3.12, pytest, JSON/YAML, Git object identities.

## Global Constraints

- Canonical repo is exactly `C:\Users\momen\Projects\tc-runner`; work in this checkout because controller preflight rejects a linked-worktree path.
- User explicitly approved implementation on `master`; staging, commit, push, capsule capture, and campaign execution remain separate unapproved gates.
- Do not edit `tc_samples/TC_1.xlsx`, `exported_ss_call/*.yaml`, `src/mmi_converter/**`, or `scripts/dispatch_capsule.py`.
- Intended implementation paths are exactly the directive, base spec, controller, controller self-check, `tests/test_dispatch_capsule.py`, the approved amendment design, and this plan.
- Existing unrelated tracked/untracked files are user-owned and must remain untouched.
- Apply TDD: add observable RED gates first, run them and record the expected failure, then change directive/controller sources.
- Appendix roles are exact: A = artifact-tool P0 capture, B = analysis-only producer verifier, C = evidence/failure assembler, R = module-route negative control.
- Tracked YAML identities = `12`; unique source selectors = `14`; target blocker bindings = `15`.
- Source distribution = `SS-TC 0: 1`, `SS-TC 1: 13`; blocker distribution = `SS-TC 0: 1`, `SS-TC 1: 14`.
- The only aggregate is `exported_ss_call/SS_TC05_boundary_values.yaml`: selectors `TC-05A/B/C`; blocker step 9 binds only to `TC-05A`.
- The only same-source blocker fan-outs are `SS_TC01`, `SS_TC06`, and `SS_TC11`, each with two blocker steps.
- P0 selector is exact `(sheet, source_no, source_functionality_effective)`; physical row is evidence, never selector input.
- P0 selector candidate `0` or `2+`, missing/colliding producer documents, or ambiguous target step are measured `PROVENANCE_MISMATCH` code 1.
- P0 schema version changes `2 → 3`; reconciliation schema version changes `1 → 2` because document/projection identity changes from 12 YAML paths to 14 `(yaml_path, source_no)` keys.
- Producer identity is `emitted.name == workbook_tc_name`; tracked identity is `tracked.tc_name == yaml_tc_name`; these comparisons must never be collapsed.
- Appendix A/B/C source bytes, heading SHA pins, assembler argv pins, ledger pins, and controller self-check derivations must agree exactly.
- Base spec raw SHA/blob changes must be re-frozen in every directive consumer before tests can be GREEN.
- PowerShell files remain ASCII-only and Windows PowerShell 5.1 parseable. Directive and base spec remain UTF-8 LF with final LF.
- No task may stage or commit. The plan intentionally replaces the skill's per-task commit step with an uncommitted working-tree checkpoint because repo policy requires a separate explicit commit approval.

## Frozen Manifest Interface

Every executable appendix that consumes expected identities uses an equivalent manifest with these literal records. `source_selectors` are ordered; `blocker_bindings` are ordered by blocker step.

```json
[
  {"yaml_path":"exported_ss_call/SS_TC01_permission_denied.yaml","yaml_tc_name":"SS_TC01_permission_denied","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-01","source_functionality_effective":"권한 미부여 기본 동작 확인"}],"blocker_bindings":[{"blocker_step_index":10,"source_no":"TC-01"},{"blocker_step_index":11,"source_no":"TC-01"}]},
  {"yaml_path":"exported_ss_call/SS_TC02_permission_allow_idle.yaml","yaml_tc_name":"SS_TC02_permission_allow_idle","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-02","source_functionality_effective":"권한 허용 후 Idle 진입 확인"}],"blocker_bindings":[{"blocker_step_index":11,"source_no":"TC-02"}]},
  {"yaml_path":"exported_ss_call/SS_TC03_ringing_permission.yaml","yaml_tc_name":"SS_TC03_ringing_permission","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-03","source_functionality_effective":"RINGING 중 권한 허용 시 현재 통화 감지"}],"blocker_bindings":[{"blocker_step_index":15,"source_no":"TC-03"}]},
  {"yaml_path":"exported_ss_call/SS_TC04_offhook_seed_recovery.yaml","yaml_tc_name":"SS_TC04_offhook_seed_recovery","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-04","source_functionality_effective":"OFFHOOK 도중 권한 허용 시 seed 복구 확인"}],"blocker_bindings":[{"blocker_step_index":18,"source_no":"TC-04"}]},
  {"yaml_path":"exported_ss_call/SS_TC05_boundary_values.yaml","yaml_tc_name":"SS_TC05_boundary_values","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-05A","source_functionality_effective":"9초 경계값 검증"},{"source_no":"TC-05B","source_functionality_effective":"10초 경계값 검증"},{"source_no":"TC-05C","source_functionality_effective":"11초 경계값 검증"}],"blocker_bindings":[{"blocker_step_index":9,"source_no":"TC-05A"}]},
  {"yaml_path":"exported_ss_call/SS_TC06_missed_rejected.yaml","yaml_tc_name":"SS_TC06_missed_rejected","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-06","source_functionality_effective":"부재중/거절 통화 처리 확인"}],"blocker_bindings":[{"blocker_step_index":10,"source_no":"TC-06"},{"blocker_step_index":11,"source_no":"TC-06"}]},
  {"yaml_path":"exported_ss_call/SS_TC07_short_call_no_false_positive.yaml","yaml_tc_name":"SS_TC07_short_call_no_false_positive","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-07","source_functionality_effective":"짧은 정상 통화 오탐 방지"}],"blocker_bindings":[{"blocker_step_index":9,"source_no":"TC-07"}]},
  {"yaml_path":"exported_ss_call/SS_TC09_offhook_permission_banking.yaml","yaml_tc_name":"SS_TC09_offhook_permission_banking","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-09","source_functionality_effective":"OFFHOOK 중 권한 허용 후 금융 앱 개입 확인"}],"blocker_bindings":[{"blocker_step_index":20,"source_no":"TC-09"}]},
  {"yaml_path":"exported_ss_call/SS_TC0_P0_endcall_crash.yaml","yaml_tc_name":"SS_TC0_P0_endcall_crash","sheet":"SS-TC 0","source_selectors":[{"source_no":"T/C-01","source_functionality_effective":"경고 팝업의 \"지금 전화 끊기\" 버튼 경로에서 다이얼러 크래시 재발 여부와 dismiss→suppression→delayed endCall→IDLE→suppression release 순서 검증"}],"blocker_bindings":[{"blocker_step_index":15,"source_no":"T/C-01"}]},
  {"yaml_path":"exported_ss_call/SS_TC10_permission_toggle.yaml","yaml_tc_name":"SS_TC10_permission_toggle","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-10","source_functionality_effective":"true→false→true 권한 흔들기"}],"blocker_bindings":[{"blocker_step_index":24,"source_no":"TC-10"}]},
  {"yaml_path":"exported_ss_call/SS_TC11_multi_subscription.yaml","yaml_tc_name":"SS_TC11_multi_subscription","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-11","source_functionality_effective":"다중 구독 안전성 확인"}],"blocker_bindings":[{"blocker_step_index":20,"source_no":"TC-11"},{"blocker_step_index":21,"source_no":"TC-11"}]},
  {"yaml_path":"exported_ss_call/SS_TC12_legacy_path.yaml","yaml_tc_name":"SS_TC12_legacy_path","sheet":"SS-TC 1","source_selectors":[{"source_no":"TC-12","source_functionality_effective":"Legacy 경로 현재 상태 반영 확인"}],"blocker_bindings":[{"blocker_step_index":19,"source_no":"TC-12"}]}
]
```

---

### Task 1: Add RED producer-reconcile contract tests

**Files:**
- Modify: `scripts/provenance_controller_selfcheck.ps1:109-411`
- Modify: `tests/test_dispatch_capsule.py:78-95,1359-1451`

**Interfaces:**
- Consumes: directive fence extraction helpers already present in both test files.
- Produces: C9 static checks and pytest assertions that fail on schema v2, the direct name join, 12-document green reconciliation, or an inconsistent 12/14/15 manifest.

- [ ] **Step 1: Add C9 static contract checks**

Add self-checks that parse Appendix A/B/C bodies and assert these independent literal outcomes:

```powershell
# Expected RED against current directive.
$ExpectedYamlCount = 12
$ExpectedSelectorCount = 14
$ExpectedBlockerCount = 15
$ExpectedSourceDistribution = @{ 'SS-TC 0' = 1; 'SS-TC 1' = 13 }
$ExpectedBlockerDistribution = @{ 'SS-TC 0' = 1; 'SS-TC 1' = 14 }
```

The checks must also reject the current strings `row.tc_name === target.yaml_tc_name`, `mapping.get("yaml_tc_name") != expected_tc_name`, and `emitted.get("name") == tc_name`; require schema v3; and pin `SS_TC05` selectors A/B/C with blocker step 9 → A only. The check names start `C9` so their RED result is unambiguous.

- [ ] **Step 2: Add behavior-facing pytest gates**

Rename the early-stop test to `test_provenance_appendix_c_accepts_schema_v3_p0_early_stop` and make its literal P0 fixture schema v3 with 12 mappings, where every mapping has `source_selectors` and `blocker_bindings`. Add tests that execute Appendix C's real `validate_reconciliation` function from an isolated namespace and assert:

```python
assert "reconciliation green documents" in validate_reconciliation(
    green_fixture_with_12_source_documents
)
assert "reconciliation green documents" not in validate_reconciliation(
    green_fixture_with_14_source_documents
)
```

The 14-document fixture is keyed by `(yaml_path, source_no)` and the 15 target fixture includes `source_no`. Add a manifest-consistency test that derives 12/14/15, `1+13`, `1+14`, and the aggregate-only invariant from Appendix A/B/C executable constants rather than grepping prose.

- [ ] **Step 3: Run RED and verify the reason**

Run separately with `timeout_ms >= 300000`:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\provenance_controller_selfcheck.ps1 -RepoRoot C:\Users\momen\Projects\tc-runner
venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_dispatch_capsule.py -k "schema_v3_p0_early_stop or reconcile_manifest or 12_source_documents or 14_source_documents"
```

Expected: self-check exit 1 only in new C9 checks; pytest fails because current Appendix A/B/C still encode schema v2 and 12 one-row documents. Syntax/import errors are not an acceptable RED.

- [ ] **Step 4: Self-review the tests**

For each test, name the mutation it catches: restoring the direct alias join, changing one selector/functionality, moving step 9 from A, accepting 12 documents, or omitting source_no. Expected values must be literal and not built by the directive helper under test.

- [ ] **Step 5: Record uncommitted checkpoint**

Record exact RED commands/output in the SDD task report and ledger. Do not stage or commit.

### Task 2: Implement P0 schema v3 and Appendix B producer reconcile

**Files:**
- Modify: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md:637-790,2065-2236,2371-4085`

**Interfaces:**
- Consumes: Frozen Manifest Interface and Task 1 RED gates.
- Produces: Appendix A P0 mappings with 14 nested selector records and 15 bindings; Appendix B reconciliation with 14 source-bound documents, 15 target records, and source-keyed non-gating projections.

- [ ] **Step 1: Replace Appendix A flat TARGETS**

Represent each of the 12 records with `yaml_path`, `yaml_tc_name`, `sheet`, ordered `source_selectors`, and ordered `blocker_bindings`. For each selector, match row inventory by exact sheet plus:

```javascript
row.source_no === selector.source_no &&
row.source_functionality_effective ===
  selector.source_functionality_effective
```

Emit `workbook_tc_name: candidate.tc_name`; never compare it with `yaml_tc_name`.

- [ ] **Step 2: Emit P0 schema v3**

Each mapping keeps tracked alias fields at mapping level and nests the existing row/cell/carry evidence under each `source_selectors[]` result. Emit ordered `blocker_bindings[]`. Gate exactly 12 mappings, 14 unique selector rows, 15 bindings, source distribution `1+13`, blocker distribution `1+14`, and aggregate/fan-out invariants. Keep candidate `0/2+` as `reconciled:false` measured output.

- [ ] **Step 3: Rework Appendix B source binding**

For each mapping, validate tracked alias once, then iterate selector results. The producer binding is exactly:

```python
bindings = {
    "emitted_name_match": emitted.get("name") == workbook_tc_name,
    "procedure_prefix_match": emitted.get("description") == procedure[:200],
    "source_content_hash_match": (
        Path(emitted_item["relative_path"]).name
        == make_filename(workbook_tc_name, procedure, expected)
    ),
}
```

Emit 14 `mapped_document_status` records and 14 `document_step_projection_report` records, each keyed by `yaml_path` and `source_no`. A blocker binding selects exactly one source document by `source_no`; target semantic candidate count is computed only inside that document.

- [ ] **Step 4: Preserve fail-closed classifications**

Selector `0/2+`, producer source join `0/2+`, wrong emitted identity, wrong source_no, and target step `0/2+` append sorted measured reasons and produce code 1 through the existing measured path. IO, parse, API, or process inability remains code 3.

- [ ] **Step 5: Run focused GREEN attempts**

Run Task 1's focused commands. At this point Appendix A/B tests may pass while Appendix C validation tests remain RED; record that expected dependency rather than weakening tests.

- [ ] **Step 6: Record uncommitted checkpoint**

Write changed paths, manifest counts, and test results to the task report. Do not stage or commit.

### Task 3: Implement Appendix C validation and controller runtime fixture

**Files:**
- Modify: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md:4093-6134`
- Modify: `scripts/provenance_controller.ps1:1022-1172`

**Interfaces:**
- Consumes: P0 schema v3 and Appendix B output from Task 2.
- Produces: assembler acceptance for 12 aliases / 14 source documents / 15 blocker targets and a runtime synthetic aggregate selftest.

- [ ] **Step 1: Update assembler expected identities**

Set reconciliation schema to v2. Keep `EXPECTED_TARGETS` at 15 `(yaml_path, blocker_step_index)` keys and add each target's expected `source_no`. Add 14 ordered `(yaml_path, source_no)` source-document keys. Validate documents and projections by those compound keys; validate targets by `(yaml_path, blocker_step_index, source_no)`.

- [ ] **Step 2: Update P0 measured gates**

Both early-stop and full-measured gates require schema v3. Early-stop accepts structurally valid 12 mappings with non-empty sorted blocking reasons. Full-measured requires 12 mappings, 14 selectors, 15 bindings, `reconciled:true`, and empty P0 reasons.

- [ ] **Step 3: Add runtime aggregate selftest**

Extend `Invoke-SelfTestMode` without changing prepare/resume orchestration. Materialize or execute the real Appendix C validator against literal synthetic reconciliation fixtures:

- 12 mapped documents → rejected
- 14 exact `(yaml_path, source_no)` documents → accepted
- `SS_TC05` step 9 bound to `TC-05B` → rejected
- duplicate source key or missing source document → rejected

Name new checks `S12` onward and keep controller ASCII-only.

- [ ] **Step 4: Run RED-to-GREEN verification**

Run individually:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\provenance_controller_selfcheck.ps1 -RepoRoot C:\Users\momen\Projects\tc-runner
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\provenance_controller.ps1 -Mode selftest -RepoRoot C:\Users\momen\Projects\tc-runner
venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_dispatch_capsule.py -k "provenance"
```

Expected: all new C9/S12+/pytest producer-reconcile checks GREEN. Appendix SHA/identity checks can remain RED until Task 4 refreezes bytes.

- [ ] **Step 5: Record uncommitted checkpoint**

Write runtime fixture outcomes and any remaining identity-only RED to the task report. Do not stage or commit.

### Task 4: Align prose, SHA pins, and identity cascade

**Files:**
- Modify: `docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md:117-163,596-601,666-698`
- Modify: `docs/superpowers/specs/2026-08-11-shell-rc-producer-reconcile-amendment-design.md:1-270`
- Modify: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md:50-51,637-790,848,876,1047-1050,2065-2350,2376,2972,4098,4178-4179`
- Modify only if a check contract requires it: `scripts/provenance_controller_selfcheck.ps1`

**Interfaces:**
- Consumes: final Appendix A/B/C bytes and approved reconcile behavior.
- Produces: internally consistent human contract, frozen Appendix SHA pins, and current base-spec raw SHA/blob consumers.

- [ ] **Step 1: Correct appendix role wording**

Record implementation refinement in the amendment design: Appendix B is analyzer, Appendix C is assembler, and A/B/C all change. Set status to implemented/tested only after Task 5 verification; until then use `IMPLEMENTATION IN PROGRESS`.

- [ ] **Step 2: Update base spec**

Replace one-row-per-YAML language with 12 aliases / 14 selectors / 15 blockers and identity namespace separation. Preserve the existing rule that P0/P1 mismatch stops before P2.

- [ ] **Step 3: Freeze Appendix source hashes**

Derive UTF-8 LF trailing-LF SHA-256 for Appendix A, B, and C fence bodies. Replace heading pins, assembler invocation pins, ledger/tool-input pins, and any duplicate literals. Appendix R remains unchanged and must retain its current SHA.

- [ ] **Step 4: Freeze base spec identities**

Calculate base spec raw SHA-256 and Git blob with `git hash-object --no-filters`. Update every directive table/setup/Appendix C consumer. Do not update directive raw SHA/blob inside the directive unless the existing contract has an explicit non-self-referential consumer.

- [ ] **Step 5: Run identity checks**

Run controller self-check and:

```powershell
venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_dispatch_capsule.py -k "provenance_identity_literals or appendix_c_accepts_schema_v3 or reconcile_manifest"
git diff --check
```

Expected: Appendix pins, base spec raw/blob, manifest, and schema tests GREEN.

- [ ] **Step 6: Record uncommitted checkpoint**

Record final A/B/C SHA values and base-spec raw/blob in the task report. Do not stage or commit.

### Task 5: Full regression and review handoff

**Files:**
- Verify only all paths changed by Tasks 1-4.
- Update status/result sections only: `docs/superpowers/specs/2026-08-11-shell-rc-producer-reconcile-amendment-design.md`

**Interfaces:**
- Consumes: complete uncommitted implementation.
- Produces: fresh verification evidence and a commit-ready, still-uncommitted review package.

- [ ] **Step 1: Run PowerShell gates separately**

Use `timeout_ms >= 300000` for each process:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\provenance_controller_selfcheck.ps1 -RepoRoot C:\Users\momen\Projects\tc-runner
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\provenance_controller.ps1 -Mode selftest -RepoRoot C:\Users\momen\Projects\tc-runner
```

- [ ] **Step 2: Run Python regressions separately**

The complete `tests/test_dispatch_capsule.py` previously exceeded a 300-second parallel wrapper, so run it alone with `timeout_ms >= 1800000` and recurring status yields. Then run producer regressions:

```powershell
venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_dispatch_capsule.py
venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_exporter.py tests\test_mmi_row_loader.py tests\test_mmi_service.py
```

- [ ] **Step 3: Verify bytes and scope**

Check PowerShell ASCII/parse, directive/base-spec LF/final LF, Appendix materialized SHA equality, `git diff --check`, exact changed paths, and unchanged workbook/YAML/producer hashes. Confirm HEAD still equals origin/master and no staging/commit occurred.

- [ ] **Step 4: Update design status with measured results**

Only after all commands are fresh GREEN, record actual check/test counts, A/B/C SHA values, base-spec raw/blob, and `IMPLEMENTED + TESTED — commit approval pending` in the amendment design.

- [ ] **Step 5: Broad final review**

Dispatch a fresh reviewer with the approved spec, plan, SDD ledger, full uncommitted diff package, and test reports. Resolve Critical/Important findings through one fix/re-review loop; record any Minor findings explicitly.

- [ ] **Step 6: Stop at commit gate**

Report exact changed paths, tests, hashes, and Git state. Request explicit `commit now`; do not stage, commit, push, capture a capsule, or run a campaign.

### Task 6: Final-review remediation

**Files:**
- Modify: `tests/test_dispatch_capsule.py`
- Modify: `docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md`
- Modify: `docs/superpowers/specs/2026-08-11-shell-rc-producer-reconcile-amendment-design.md`
- Update plan/SDD status and reports only.

**Interfaces:**
- Executes the actual Appendix B `reconcile_v2` against a deterministic 12/14/15 fixture.
- Keeps artifact-tool-only evidence validation narrowly stubbed while retaining real tracked, source, producer, filename, projection, candidate, sorting, and output logic.
- Aligns the P0/P1 reader responsibility without weakening the full-chain gate.

- [x] Add real-analyzer GREEN, wrong-source, and ambiguous-candidate tests.
- [x] Move tracked alias/source validation responsibility from P0-only wording to P1 Appendix B.
- [x] Run focused tests and gates, report expected base-spec identity RED, and stop for review.

Task 5 qualification is superseded by this test/spec change. Do not restore final
qualification status or refreeze identities in Task 6.

### Task 7: Identity refreeze and full requalification

**Files:**
- Update identity consumers required by the changed base spec and final bytes.
- Update the amendment status/results only after all fresh gates are GREEN.

- [x] Refreeze the base-spec raw SHA/no-filter blob and every affected consumer.
- [x] Re-run static selfcheck, controller selftest, complete dispatch capsule tests,
  producer regressions, byte/scope checks, and independent final review.
- [x] Record current A/B/C/R and spec/directive identities, then stop at the separate
  stage/commit approval gate.

No staging, commit, push, capsule capture, or campaign is part of Task 7 unless a
later explicit approval opens that separate gate.

### Task 8: 2026-08-12 contract amendment

**Approved files:** directive, base spec, amendment design, this plan,
controller self-check, dispatch tests, and the new
`2026-08-12-shell-rc-contract-amendment-design.md` only.

**Immutable:** Appendix A, Appendix C non-empty policy, controller, workbook,
tracked YAML, producer source, capsule generator, campaign roots.

- [x] Add RED tests for the real `SS-TC 1` shared feature/priority column,
  corrupted duplicate evidence, and silent analyzer success.
- [x] Observe `3 failed` against the old Appendix B for the intended reasons.
- [x] Add C9h/C9i static RED checks and observe only those two checks fail.
- [x] Implement the narrow loader-equivalent alias and field-identical duplicate
  evidence checks in Appendix B.
- [x] Emit one deterministic `ANALYZE_RESULT` line after atomic output publish.
- [x] Turn the three focused behavior tests GREEN.
- [x] Refreeze Appendix B and the edited base-spec identity in every consumer.
- [x] Run static selfcheck, runtime selftest, and complete dispatch regression.
- [x] Audit exact seven-path scope, immutable paths, hashes, blobs, and unstaged
  Git state; stop at the separate commit gate.
