# Canonical Shell-RC Curated Remediation Implementation Plan

> **Execution workflow:** Use `superpowers:executing-plans` in this workspace.
> Tasks 0-7 are already implemented through the first full-regression diagnosis.
> Resume only through the approved nine-path schema-v5 recovery correction and
> six-hash report, then hard STOP. Capture/verify and
> Tasks 6-9 require a later exact user authorization. The repository instruction
> forbidding unrequested subagents remains authoritative.

**Goal:** Replace the 18 fail-open or masked canonical shell-RC blocker assertions
with deterministic `verify_shell` assertions while preserving curated YAML as the
authority, the current P2 workbook relationship, all non-target semantics, and the
frozen v1 evidence.

**Architecture:** A tracked JSON manifest records the frozen projection and bounded
renderer inputs for all 18 coordinates. A host-only verifier renders the sole
accepted shell command, compares the candidate worktree or commit to frozen Git
objects, checks the coordinated P2 projections, protects the index and the declared
untracked/ignored invariant scope, and publishes deterministic ignored evidence. Existing runner,
ADB, schema, loader, validator, workbook, provenance seed/gate, and v1 inventory/risk
implementations remain unchanged.

**Tech stack:** Python 3 from `venv/Scripts/python.exe`, pytest, PyYAML, Git object
reads, JSON/CSV, PowerShell orchestration on Windows.

**Normative spec:**
`docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`, raw
SHA-256 `4484f3528a126fe1210b10a73960df11a7ab4331fb4dc86296a1d4fd2c521ba9`.

**Publication boundary:** This plan contains no commit step. Stage, commit, push,
device contact, campaign rerun, campaign-root cleanup, dependency installation and
network access remain outside the authorized implementation slice.

**Continuation-capsule prerequisite:** Before resumed Task 6, the separately
approved bounded repair modifies exactly the directive, this plan, the successor
spec, `scripts/dispatch_capsule.py`, `tests/test_dispatch_capsule.py`,
`scripts/canonical_shell_rc_remediation_check.py` and
`tests/test_canonical_shell_rc_remediation.py`. The first five are outside the
original 21-path implementation boundary; the last two are already inside it, so
the union remains exactly 26 continuation candidates. Only these seven may receive
writes in this phase; the other 19 are frozen. Focused tests must prove
repo-relative exact-hash untracked governance inputs, exact tracked-dirty path/byte
sealing, externally supplied `--tracked-worktree-sha256` and
`--invariant-scope-sha256` anchors, exact/prefix selector normalization,
missing/malformed/mismatched anchor rejection, path rejection, scoped verify-time
drift rejection, clean schema-v2 and full continuation schema-v3 compatibility, and
the remediation consumer's schema-v4 capsule-bound bytes. After GREEN, align the
spec/plan/directive, report six fresh hashes and hard STOP.
Capture/verify, Tasks 6-9, stage, commit and push remain unauthorized pending a
later exact user message.

P2 large-file identity records, P3 quiescence prechecks and `.gitignore` changes are
not part of this correction.

---

## Fixed Inputs and Target Data

The dispatch preflight must prove these identities before the first implementation
write:

| input | required identity |
|---|---|
| entry HEAD and `origin/master` | `db20ea487f1f2fb906c543e2262bc7066a593b93`, ahead/behind `0/0` |
| approved successor spec | `4484f3528a126fe1210b10a73960df11a7ab4331fb4dc86296a1d4fd2c521ba9` |
| base design | `af800c57d81f25b3419e51d522247f83956858b57f2d14157e546bd5a6e48ef6` |
| P2 design | `3e8fe99da9cb6541ce3b17bdad12ed5be417401666d99d209c92b13dbc67f7b0` |
| P2 manifest before remediation | `b4544cf636bf7be22fc9ba0a05c0b217c35710eceb92db9994e28ce0b3d88e3c` |
| workbook | `160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa` |
| frozen inventory HEAD | `78b3ac34e9f8bacabe926172dd199342b7eb58c5` |
| frozen inventory CSV | `b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f` |
| frozen risk matrix | `81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4` |
| risk policy v1 | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` |
| archived P2 evidence | `f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a` |

The renderer input table is exact. `source_no` is JSON `null` for local/manual rows.

| # | row key | class | renderer | source command | grep pattern | predicate | provenance/source_no |
|---:|---|---|---|---|---|---|---|
| 1 | `ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml#24` | `COUNT_EQ_0` | `uiautomator_dump_count` | `uiautomator dump` | `viewSelectionOverlay` | `EQ_0` | `local` / `null` |
| 2 | `ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml#11` | `MASKED_ASSERTION` | `uiautomator_dump_count` | `uiautomator dump` | `rv_files` | `EQ_1` | `local` / `null` |
| 3 | `exported_ss_call/SS_TC01_permission_denied.yaml#10` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s SeniorShield-Coordinator:D` | `callSignals=\\[\\]` | `EQ_0` | `p2_manifest` / `TC-01` |
| 4 | `exported_ss_call/SS_TC01_permission_denied.yaml#11` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `TC-01` |
| 5 | `exported_ss_call/SS_TC02_permission_allow_idle.yaml#11` | `COUNT_EQ_1` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D` | `registered` | `EQ_1` | `p2_manifest` / `TC-02` |
| 6 | `exported_ss_call/SS_TC03_ringing_permission.yaml#15` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `TC-03` |
| 7 | `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml#18` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `TC-04` |
| 8 | `exported_ss_call/SS_TC05_boundary_values.yaml#9` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D SeniorShield-Coordinator:D` | `LONG_CALL_DURATION` | `EQ_0` | `p2_manifest` / `TC-05A` |
| 9 | `exported_ss_call/SS_TC06_missed_rejected.yaml#10` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D SeniorShield-Coordinator:D` | `LONG_CALL_DURATION` | `EQ_0` | `p2_manifest` / `TC-06` |
| 10 | `exported_ss_call/SS_TC06_missed_rejected.yaml#11` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s SeniorShield-Coordinator:D` | `event` | `EQ_0` | `p2_manifest` / `TC-06` |
| 11 | `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml#9` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D SeniorShield-Coordinator:D` | `LONG_CALL_DURATION` | `EQ_0` | `p2_manifest` / `TC-07` |
| 12 | `exported_ss_call/SS_TC09_offhook_permission_banking.yaml#20` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `TC-09` |
| 13 | `exported_ss_call/SS_TC0_P0_endcall_crash.yaml#15` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `T/C-01` |
| 14 | `exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml#24` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `manual` / `null` |
| 15 | `exported_ss_call/SS_TC10_permission_toggle.yaml#24` | `COUNT_EQ_1` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D` | `registered` | `EQ_1` | `p2_manifest` / `TC-10` |
| 16 | `exported_ss_call/SS_TC11_multi_subscription.yaml#20` | `COUNT_EQ_1` | `stream_count` | `logcat -d -s SeniorShield-CallMonitor:D` | `LONG_CALL_DURATION` | `EQ_1` | `p2_manifest` / `TC-11` |
| 17 | `exported_ss_call/SS_TC11_multi_subscription.yaml#21` | `COUNT_LE_1` | `stream_count` | `logcat -d -s SeniorShield-Coordinator:D` | `notification escalation` | `LE_1` | `p2_manifest` / `TC-11` |
| 18 | `exported_ss_call/SS_TC12_legacy_path.yaml#19` | `COUNT_EQ_0` | `stream_count` | `logcat -d -s AndroidRuntime:E` | `FATAL` | `EQ_0` | `p2_manifest` / `TC-12` |

---

### Task 0: Verify the dispatched entry capsule

> Historical entry task, already completed before Tasks 1-5. Do not rerun it during
> the 2026-08-14 continuation; use the scoped schema-v4 checkpoint before Task 6 instead.

**Read-only paths:**

- Read: `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`
- Read: `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`
- Read: `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`
- Read: external capsule below `C:\tmp\tc-runner-dispatch-capsules\`

- [ ] **Step 1: Confirm the user authorization binds the live directive, plan, spec and capsule**

The authorization must name directive ID
`RB-20260813-shellrc-curated-remediation-t1`, the directive raw SHA-256, this
plan raw SHA-256, the approved spec raw SHA-256, generator raw SHA-256,
tracked-worktree canonical JSON SHA-256, invariant-scope canonical JSON SHA-256 and
a lowercase 64-hex fresh capsule SHA-256. Do not infer any of them from an older
conversation.

- [ ] **Step 2: Verify the capsule before any implementation write**

Run the directive's exact `dispatch_capsule.py verify` command. Expected result:
exit 0, same HEAD/upstream, clean index, complete tracked-worktree identity and an
unchanged scoped untracked/ignored map plus excluded counts.
If verification is exit 2/3 or the 1800-second TTL expires, STOP without editing.
The expected directive and spec arguments are repo-relative. Verify obtains their
exact hashes from the capsule and rechecks both identities twice.

- [ ] **Step 3: Record a baseline pytest nodeid count without writing repo artifacts**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final' --collect-only -q tests\
```

Record the final collected count in the execution log. Do not redirect it into the
repository. The final collect-only gate must use these same environment and cache
settings. A collection error is a STOP condition.

- [ ] **Step 4: Re-prove immutable hashes and ignored evidence root**

Run read-only `Get-FileHash`, `git hash-object --no-filters`, `git check-ignore -v`,
and `git diff --quiet` checks listed by the directive. The exact two completed
campaign roots must be absent and the final archive must be present. Any mismatch is
a STOP condition.

---

### Task 1: Write focused tests and demonstrate RED

**Files:**

- Create: `tests/test_canonical_shell_rc_remediation.py`
- Test: `tests/test_canonical_shell_rc_remediation.py`
- Test: `tests/test_provenance_manifest.py`

- [ ] **Step 1: Add a loader that does not import production code at collection time**

Start the test file with this shape so the first RED is a focused test failure rather
than a collection failure:

```python
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
CHECK_PATH = REPO / "scripts" / "canonical_shell_rc_remediation_check.py"
MANIFEST_PATH = REPO / "scripts" / "canonical_shell_rc_remediation_manifest_v1.json"


def load_check_module():
    spec = importlib.util.spec_from_file_location(
        "canonical_shell_rc_remediation_check_for_tests", CHECK_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_module_exists() -> None:
    assert CHECK_PATH.is_file()
```

- [ ] **Step 2: Run the first focused RED**

Run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py::test_verifier_module_exists -q
```

Expected: exactly one failed test because the verifier file is absent. A pass or a
different failure reason is a STOP condition.

- [ ] **Step 3: Add complete manifest, predicate and renderer tests before implementation**

Cover exact-root-key validation; exact 18 target order; duplicate/missing/path
traversal rejection; raw baseline command SHA validation; canonical JSON semantic
hashes; row-unique sentinel and temp coordinates; quote/newline/NUL rejection;
unsupported renderer/predicate rejection; source rc, grep rc, count parse and
predicate truth tables; diagnostics; source/grep separation; cleanup ordering;
failure-rc preservation; no sentinel on failure; sentinel-only success stdout; no
`/sdcard`; no pipeline; no `|| echo 0`; and no target `timeout`.

Use the pure API exactly:

```python
ok, diagnostic = check.evaluate_count(
    source_rc=0,
    grep_rc=1,
    count_text="0",
    predicate_kind="EQ_0",
    predicate_value=0,
)
assert ok is True
assert diagnostic == ""
```

Parameterize at least these rows:

```python
@pytest.mark.parametrize(
    ("source_rc", "grep_rc", "count_text", "kind", "value", "ok"),
    [
        (1, 0, "0", "EQ_0", 0, False),
        (0, 2, "0", "EQ_0", 0, False),
        (0, 1, "", "EQ_0", 0, False),
        (0, 1, "x", "EQ_0", 0, False),
        (0, 1, "0", "EQ_0", 0, True),
        (0, 0, "1", "EQ_0", 0, False),
        (0, 0, "1", "EQ_1", 1, True),
        (0, 1, "0", "EQ_1", 1, False),
        (0, 0, "1", "LE_1", 1, True),
        (0, 0, "2", "LE_1", 1, False),
    ],
)
```

- [ ] **Step 4: Add candidate-comparison and evidence tests before implementation**

Use temporary Git repositories and temporary candidate YAML copies. Cover:

- all 18 rendered target triples accepted;
- one old target command rejected;
- action/command/expected mutation rejected independently;
- target description or any non-target field mutation rejected;
- 674 non-target row mutation rejected;
- manual/local target appearing in P2 rejected;
- a P2 target projection mismatch rejected;
- P2 cardinality and identity drift rejected;
- frozen v1 input drift rejected;
- index fingerprint drift rejected;
- in-scope untracked add/delete/type/content drift rejected;
- out-of-scope membership drift rejected while out-of-scope content-only drift is
  accepted;
- two independently rendered output bundles byte-identical;
- existing identical final output accepted and mismatched output rejected;
- invalid input exits 2 without final evidence;
- infrastructure/publish failure exits 3 without partial final evidence.

- [ ] **Step 5: Prove P2 transition behavior in temporary copies**

Call the existing G4 helpers or invoke the exact P2 validation logic on temporary
copies. The sequence must demonstrate:

1. old YAML + old projection = GREEN;
2. remediated YAML + old projection = RED;
3. remediated YAML + matching updated projection = GREEN;
4. changed origin/workbook/selector/non-target projection = RED.

- [ ] **Step 6: Run the full focused RED**

Run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py -q
```

Expected: nonzero with failures caused only by the missing verifier and remediation
manifest/API. Save the measured nodeids and failure summary in chat, not a repo file.

---

### Task 2: Create the remediation manifest v1

**Files:**

- Create: `scripts/canonical_shell_rc_remediation_manifest_v1.json`
- Modify: `.gitattributes`
- Test: `tests/test_canonical_shell_rc_remediation.py`

- [ ] **Step 1: Add only the approved LF rules**

Append exact `text eol=lf` rules for the successor spec, this plan, the directive,
the remediation JSON manifest, verifier, and verifier test. Preserve all existing
`.gitattributes` lines and order.

- [ ] **Step 2: Build the exact manifest from frozen Git and policy inputs**

For each target, read the baseline action/command from Git object
`78b3ac34e9f8bacabe926172dd199342b7eb58c5`; compute:

```python
baseline_command_sha256 = hashlib.sha256(
    baseline_command.encode("utf-8")
).hexdigest()
row_key = f"{source_path}#{step_index}"
sentinel = "__TC_ASSERT_OK_" + hashlib.sha256(
    row_key.encode("utf-8")
).hexdigest()[:12] + "__"
```

Populate the exact table above and the exact six base-spec §7 runtime-review
dispositions. The baseline object uses the full hashes in this plan. Use no absolute
path, timestamp, random value, mtime, candidate HEAD or free-form shell template.

- [ ] **Step 3: Compute semantic identities and serialize deterministically**

Use this exact identity algorithm:

```python
def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

The raw file uses sorted keys, two-space indentation, UTF-8/LF and one terminal LF.
Generate it twice in two external temporary locations and require byte identity
before placing the reviewed bytes at the tracked path.

- [ ] **Step 4: Run manifest-only tests**

Run only the manifest validation, semantic hash, cardinality, and sentinel test
nodeids. Expected: GREEN for the manifest; verifier-dependent tests remain RED.

---

### Task 3: Implement the pure verifier core

**Files:**

- Create: `scripts/canonical_shell_rc_remediation_check.py`
- Modify: `tests/test_canonical_shell_rc_remediation.py`

- [ ] **Step 1: Implement strict manifest loading**

Expose these exact public callable signatures:

- `canonical_json_sha256(value: object) -> str`
- `sentinel_for(source_path: str, step_index: int) -> str`
- `evaluate_count(source_rc: int, grep_rc: int, count_text: str,
  predicate_kind: str, predicate_value: int) -> tuple[bool, str]`
- `render_command(target: dict) -> str`
- `load_and_validate_manifest(path: Path) -> dict`

Reject unknown/missing keys and wrong JSON types. Reject NUL/CR/LF, single quote in
patterns, path traversal, duplicate row keys/sentinels/temp paths, unsupported
renderer/predicate, predicate-value mismatch, baseline hash mismatch, semantic hash
mismatch, wrong counts, and wrong target order.

- [ ] **Step 2: Implement the predicate oracle**

Return distinct diagnostics for source failure, grep infrastructure failure, invalid
count and predicate mismatch. `grep_rc` 0 and 1 are valid; greater than 1 is failure.
Require ASCII decimal count text. Implement only `EQ_0`, `EQ_1`, and `LE_1`.

- [ ] **Step 3: Implement the exact shell renderer**

Generate the twelve-state operation order from successor spec §6. Use single-quoted
validated grep patterns, double-quoted temp variables, literal Android `$$`, stderr
diagnostics, primary-rc preservation, final cleanup gate, and one success sentinel.
Do not invoke a shell on the host.

- [ ] **Step 4: Run pure-core GREEN**

Run the manifest/predicate/renderer subset. All of those nodeids must be GREEN while
end-to-end candidate tests may remain RED until Task 5.

---

### Task 4: Implement Git/YAML comparison and deterministic evidence

**Files:**

- Modify: `scripts/canonical_shell_rc_remediation_check.py`
- Modify: `tests/test_canonical_shell_rc_remediation.py`

- [ ] **Step 1: Implement Git-object readers and semantic inventory comparison**

Read the baseline exclusively with Git commands against
`78b3ac34e9f8bacabe926172dd199342b7eb58c5`. Do not checkout or reset. Parse candidate
YAML from the worktree in `verify-worktree` and entirely from Git objects in
`verify-commit`. Enforce 692/692 total rows, 18 remediated targets, 674 unchanged
non-target rows, 74 unchanged advisory rows, six unchanged runtime-review rows and
zero unresolved cutover blockers.

- [ ] **Step 2: Implement exact P2 relationship checks**

Require `12 mappings / 14 selectors / 15 bindings`; preserve schema, subject,
origin, workbook, YAML identities, selectors, coordinates and source numbers. Permit
only the 15 existing `step_projection` objects to move to the corresponding rendered
target triples. Require local/manual rows to have no P2 entry.

- [ ] **Step 3: Implement worktree identity guards**

Measure `{worktree_blob,index_blob,head_blob}` for every approved tracked path and
exact raw `git ls-files --stage -z` bytes. For schema-v4 continuation, measure
untracked/ignored content only under the capsule's exact/prefix selectors and record
the excluded count for each bucket. Re-measure before publish and after publish. The
index must never change. In-scope content and out-of-scope membership must remain
stable; out-of-scope content-only drift is outside this shell-RC invariant. Only the
directive's exact implementation write set may differ.

- [ ] **Step 4: Implement deterministic evidence and exit codes**

Render exactly `shell_rc_remediation_matrix.csv` and `SUMMARY.md` twice under
`reports/canonical_shell_rc_remediation/.staging/`. Compare bytes and publish
atomically to the 16-hex input-digest directory. Exit 0 publishes GREEN, exit 1
publishes measured violation evidence, exit 2 writes no final output for invalid
input, and exit 3 writes no final output for infrastructure failure. Cleanup is
limited to the verifier's own staging directory.

- [ ] **Step 5: Add the exact CLI**

Support only:

```text
verify-worktree
verify-commit --candidate-head full-lowercase-40-hex-sha
```

Both modes require explicit manifest, spec, directive and archived evidence paths;
the tool hashes those inputs itself and compares the approved spec/evidence values
from the manifest/directive contract. `verify-commit` must refuse a worktree-only
identity and is not executed in this uncommitted slice.

- [ ] **Step 6: Run verifier unit/adversarial GREEN**

Run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py -q
```

At this checkpoint, pure/adversarial fixtures must be GREEN. A live-worktree
characterization test must still report exactly the 18 legacy target violations.

---

### Task 5: Apply the coordinated YAML and P2 projection transition

**Files:**

- Modify: `provenance/ss_call_shell_rc_manifest.yaml`
- Modify: `ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml`
- Modify: `ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml`
- Modify: `exported_ss_call/SS_TC01_permission_denied.yaml`
- Modify: `exported_ss_call/SS_TC02_permission_allow_idle.yaml`
- Modify: `exported_ss_call/SS_TC03_ringing_permission.yaml`
- Modify: `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml`
- Modify: `exported_ss_call/SS_TC05_boundary_values.yaml`
- Modify: `exported_ss_call/SS_TC06_missed_rejected.yaml`
- Modify: `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml`
- Modify: `exported_ss_call/SS_TC09_offhook_permission_banking.yaml`
- Modify: `exported_ss_call/SS_TC0_P0_endcall_crash.yaml`
- Modify: `exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml`
- Modify: `exported_ss_call/SS_TC10_permission_toggle.yaml`
- Modify: `exported_ss_call/SS_TC11_multi_subscription.yaml`
- Modify: `exported_ss_call/SS_TC12_legacy_path.yaml`

- [ ] **Step 1: Render all 18 target triples from the validated manifest**

For every target set only:

```yaml
action: verify_shell
command: the exact render_command(target) result
expected: the exact target sentinel
```

Preserve descriptions, metadata, key topology, step order, non-target steps and all
other fields. Add no `timeout`.

- [ ] **Step 2: Update the 15 P2 step projections in the same bounded batch**

For each `p2_manifest` target, copy the exact three-field rendered projection into
the already-existing binding. Do not reorder mappings/selectors/bindings or change
any other P2 manifest value. Do not add the two local targets or the manual target.

- [ ] **Step 3: Run existing P2 G1-G5 immediately**

Run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_provenance_manifest.py -q
```

Expected: 5 passed with measured `12/14/15`. Any failure is a STOP; do not weaken
G4 and do not regenerate the old evidence seed over the reviewed projection.

- [ ] **Step 4: Run live-worktree verifier tests**

The characterization RED must become GREEN with exactly 18 remediated targets and no
other semantic delta.

---

### Schema-v5 recovery checkpoint: nine-path TDD and six-hash hard STOP

This checkpoint supersedes the conflicting v4 continuation and fixed-count recovery
steps below while preserving them as execution history. The authorized write set is
exactly:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
3. this plan;
4. `scripts/dispatch_capsule.py`;
5. `tests/test_dispatch_capsule.py`;
6. `scripts/canonical_shell_rc_remediation_check.py`;
7. `tests/test_canonical_shell_rc_remediation.py`;
8. `tests/fixtures/anchor/corpus_audit_baseline.json`;
9. `CLAUDE.md`.

Preserve the 15 YAML files, P2 manifest, remediation manifest, `.gitattributes`,
eight lint sidecars, 32 existing capsules and existing evidence bundle. The recorded
15/15 validation result is final and validation must not be rerun. Do not reset,
restore, clean, stage, commit or push.

- [x] **V5 Step 1: Amend directive, spec and plan**

Record schema v5, scope version 2 and the exact
`verifier_owned_ignored_prefixes=["reports/canonical_shell_rc_remediation/"]`
contract. Record that this field participates in canonical scope JSON, that v5
omits its subtree from ignored rows and excluded count, and that v2/v3/v4 remain
unchanged. Retire fixed `2143/6842` pins in favor of fresh stable snapshots with
generator/consumer arithmetic parity.

Also record the accepted safety result: exactly 16 steps in the audited
`exported_ss_call` corpus move
`READ_ONLY_SHELL -> UNKNOWN_UNSAFE`, totals become `112/107`, and the audit adapter
moves them `FULL_AUTO -> MANUAL_REQUIRED`. Production execution metadata remains
unchanged because the adapter is not connected to the production derivation; any
future connection requires separate policy approval. The bounded
`/data/local/tmp/tc_runner_rc_<hash>_$$.*` scratch plus cleanup on every outcome is
accepted for deterministic fail-closed verification.

- [x] **V5 Step 2: Add tests and demonstrate RED**

Before production edits, add fixed tests for scratch naming and every cleanup path,
the 16 safety transitions and `112/107` audit, unchanged production execution
metadata, v5 missing/extra/typo prefix rejection, v2/v3/v4 compatibility,
generator/consumer excluded-count parity, exact 21-row tracked dirty sealing and
scope-version 2 digest. Run only the focused dispatch, remediation and anchor audit
tests with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python `-B` and a pytest cache outside
the repository. Require at least one expected v5/fixture failure before production
implementation.

- [x] **V5 Step 3: Implement minimal GREEN**

Add generator schema v5 and CLI
`--verifier-owned-ignored-prefix reports/canonical_shell_rc_remediation/`.
Normalize the new prefixes with trailing slash, sorting, duplicate/nesting checks
and reject overlap with exact/ordinary selectors. For v5 only, remove owned ignored
paths before selected rows and excluded count are calculated.

Add consumer schema-v5 support using the same arithmetic. Require exactly the one
approved prefix, otherwise exit 2. Add the audit fixture to
`ALLOWED_TRACKED_PATHS`, making the capture dirty boundary 21. Change only fixture
values `READ_ONLY_SHELL: 128 -> 112` and `UNKNOWN_UNSAFE: 91 -> 107`. Re-run the
same focused bundle and require GREEN.

Observed GREEN: `177 passed in 567.83s` with
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python `-B` and the pytest cache under the
user's external Temp directory. The schema-v5 measurement guard was stable before
and after: selected untracked/ignored `6/0`, excluded untracked/ignored
`2143/6842`.

- [x] **V5 Step 4: Complete governance and report six hashes**

Update directive §0.1 with fresh generator, generator-test, consumer and
consumer-test hashes and add the fixture hash; retain the historical
`CLAUDE.md before remediation` pin. Preserve the existing Task 7 `CLAUDE.md` row
and add two separate §8.2 rows: safety reclassification/connection approval, and
schema-v5 symmetric generator/consumer exclusion. Run `git diff --check`, compute
fresh `DIRECTIVE_SHA256`, `PLAN_SHA256`, `SPEC_SHA256`, `GENERATOR_SHA256`,
`TRACKED_WORKTREE_SHA256` and `INVARIANT_SCOPE_SHA256`, report them, then hard STOP.
This amendment does not authorize capture or verify.

- [ ] **V5 Step 5: Later authorized recovery execution**

Only after a fresh six-hash §0.2 message plus `AUTHORIZE_TASKS_6_9`, capture once
with all 21 repeatable dirty paths, the six exact invariant paths, no ordinary
prefix and the one verifier-owned ignored prefix. Require schema 5, 21 tracked rows
and scope version 2, then immediately verify with no intervening command.

Task 6 resumes at focused pytest only. Measure selected/excluded counts immediately
before and after pytest and STOP on drift; never rerun the 15 validations. Publish
consumer evidence twice in the approved escalated boundary, require GREEN and
byte-identical output, then run contamination scan. Run Task 8 full pytest once and
collect-only with expected nodeid growth limited to the new v5 tests.

Task 9 must compensate for the capsule-unbound evidence subtree by enumerating it.
Require exactly the existing `f6dfecc48ea8fa09` bundle plus one new content-addressed
bundle, each containing only `SUMMARY.md` and
`shell_rc_remediation_matrix.csv`; require `.staging` residue 0 and no other paths.
Then perform the final audit and STOP immediately before Git publication.

### Continuation checkpoint: six-hash hard STOP before scoped schema-v4 capture

**Files:**

- Edit/test: `scripts/dispatch_capsule.py`, `tests/test_dispatch_capsule.py`
- Edit/test: `scripts/canonical_shell_rc_remediation_check.py`,
  `tests/test_canonical_shell_rc_remediation.py`
- Align/hash: successor spec, this plan, directive
- Generated external output: `C:\tmp\tc-runner-dispatch-capsules\<sha256>.json`

- [ ] **Step 1: Re-run the focused v4 generator/consumer tests**

Use `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-B`, and a pytest cache below the user's
external Temp directory. Require zero failures and zero warnings for the exact
continuation, governance-input and remediation-consumer nodeids.

- [ ] **Step 2: Align and hash the three governance documents**

Replace the superseded full-invariant prerequisite with the scoped schema-v4
contract: clean captures remain v2 and full dirty continuation remains v3; scoped
dirty continuation requires the exact repeatable dirty path set, seals each tracked
path's raw SHA-256 and no-filter Git blob, normalizes repeatable exact/prefix
untracked selectors, and rejects unless both external canonical digests match.
Compute fresh raw SHA-256 and Git blobs after alignment.

- [ ] **Step 3: Prove the live continuation preconditions**

Require `HEAD == origin/master == db20ea487f1f2fb906c543e2262bc7066a593b93`,
ahead/behind `0/0`, an empty staged set, and the exact 19 tracked-dirty paths listed
in the directive. Require no prefixes and these exact invariant paths:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
3. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
4. `scripts/canonical_shell_rc_remediation_manifest_v1.json`;
5. `scripts/canonical_shell_rc_remediation_check.py`;
6. `tests/test_canonical_shell_rc_remediation.py`.

Their selector digest is
`5f4d42550ed2a8aa70db3d75bcc02191b4d17ae0a2bef4483001d36457bb983f`.
Capture rechecks selected content and both excluded counts; do not reset, restore,
clean, stage or delete anything.

- [ ] **Step 4: Report six hashes and hard STOP**

Report exact lowercase `DIRECTIVE_SHA256`, `PLAN_SHA256`, `SPEC_SHA256`,
`GENERATOR_SHA256`, `TRACKED_WORKTREE_SHA256` and `INVARIANT_SCOPE_SHA256`, then hard
STOP. Do not capture, verify, stage, commit or push under the pre-capture correction
authorization.

- [ ] **Step 5: After a fresh exact authorization, capture and verify**

Run the directive's exact capture command once with all 19 repeatable
`--allow-dirty-path` values, the fresh directive/spec hashes and the exact authorized
`--tracked-worktree-sha256`, all six repeatable `--invariant-path` values and the
exact authorized `--invariant-scope-sha256`. Require exit 0 and `schema_version=4`,
then run the exact verify command against that digest. Between capture and verify, do not run
pytest, collect-only, validation, or any other command that can mutate repository
state. Require verify exit 0 within the 1800-second TTL. Continue to Task 6 only if
the fresh user message explicitly authorizes Tasks 6-9; it does not imply stage,
commit or push authorization.

### 2026-08-18 recovery checkpoint after accumulated validation evidence

**Files:**

- Edit/hash: `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`
- Edit/hash: this implementation plan
- Preserve: `reports/lint/20260818T022205Z.json` through
  `reports/lint/20260818T022212Z.json`

The first authorized continuation produced schema-v4 capsule
`146582a7e40fbb76d965e3813395b1de8affb937a56bbd515174f777aa0d926e`
and immediate verify status `GREEN`. Its scoped baseline was selected
untracked/ignored `6/0` and excluded untracked/ignored `2143/6834`.

Task 6 validation then completed 15/15 `validate PASS` and created exactly eight
ignored lint sidecars. The post-validation scope was selected `6/0` and excluded
`2143/6842`, so the run correctly stopped before focused pytest. Preserve the
sidecars; do not delete, rewrite or regenerate them.

The user-authorized recovery amendment changes only the directive and this plan.
After alignment, compute fresh `DIRECTIVE_SHA256`, `PLAN_SHA256`, `SPEC_SHA256`,
`GENERATOR_SHA256`, `TRACKED_WORKTREE_SHA256` and `INVARIANT_SCOPE_SHA256`, report
them, and hard STOP without capture, verify or tests.

A later fresh §0.2 authorization may perform one recovery capture plus immediate
verify despite the normal no-recapture rule. Recovery preflight and both capture
snapshots require the exact dirty 19, selected `6/0`, excluded `2143/6842`, and all
other §1.1 identities. After recovery verify `GREEN`, resume at Task 6 Step 2; Task 6
Step 1 is already complete and must not run again.

### Task 6: Run focused validation, determinism and contamination gates

**Files:**

- Test: all 15 target YAML files
- Test: focused provenance/inventory/risk/dispatch suites
- Generated ignored output: `reports/canonical_shell_rc_remediation/`

- [x] **Step 1: Validate each exact YAML path**

Invoke `validate_tc.py` once with each of the 15 exact file paths. Expected:
15/15 `validate PASS`; no directory-broad mutation or output staging.

Recorded result: 15/15 `validate PASS`. The eight exact lint sidecars named in the
recovery checkpoint are accumulated evidence. This step must not be rerun during
recovery.

- [ ] **Step 2: Run focused regression tests**

Immediately before pytest, run the generator's schema-v4 scoped path measurement as
a read-only guard and require selected untracked/ignored `6/0` and excluded
untracked/ignored `2143/6842`, equal to the recovery capsule. Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-task6-recovery' tests\test_canonical_shell_rc_remediation.py tests\test_provenance_manifest.py tests\test_canonical_shell_rc_inventory.py tests\test_canonical_shell_rc_risk_audit.py tests\test_dispatch_capsule.py -q
```

Expected: zero failures. Record the measured passed count. Immediately repeat the
same read-only scoped path measurement and require all four values unchanged. Any
drift is a STOP before `verify-worktree`.

- [ ] **Step 3: Run `verify-worktree` twice independently**

Use the exact directive command and the archived evidence path. Require exit 0 for
both runs and byte identity for both files. Record their SHA-256 values and final
ignored evidence directory. The second run may accept the pre-existing identical
content-addressed directory; it may not overwrite a mismatch.

- [ ] **Step 4: Recheck contamination and exact path scope**

Run this exact read-only contamination scan and independently compare the capsule
baseline map:

```powershell
venv\Scripts\python.exe -B tools\untracked_contamination_scan.py --cwd C:\Users\momen\Projects\tc-runner --protected exported_ss_call --protected "ODIN2 - My gallary/functional/photo" --protected "ODIN2 - minifile/functional/trash" --protected scripts --protected tests --protected provenance --allow scripts/canonical_shell_rc_remediation_manifest_v1.json --allow scripts/canonical_shell_rc_remediation_check.py --allow tests/test_canonical_shell_rc_remediation.py
```

The only new untracked implementation files may be the three exact `--allow` paths
plus the already-approved spec/plan/directive outside these protected prefixes;
ignored verifier evidence must remain below its approved root. No unrelated asset may
change.

---

### Task 7: Reconcile bounded governance only after technical GREEN

**Files:**

- Modify: `CLAUDE.md`
- Test: documentation/static checks selected from current repository conventions

- [ ] **Step 1: Add the §5.3 tool registration**

Register only `canonical_shell_rc_remediation_check.py` and
`canonical_shell_rc_remediation_manifest_v1.json` as the implemented host gate and
its tracked source. Do not rewrite unrelated tool rows.

- [ ] **Step 2: Add one §8.2 applied lesson row**

Record that curated YAML remains authoritative; P2 current projection and a separate
baseline/transformation manifest preserve provenance; 18 shell-RC blockers are
fail-closed without runner/schema/validator changes. Mark it `applied` only because
the edit occurs after all technical gates are GREEN.

- [ ] **Step 3: Re-run focused tests and diff checks**

Run `git diff --check`, the remediation tests, P2 tests, and any repository static
self-check that parses `CLAUDE.md`. A failure is a STOP before full regression.

---

### Task 8: Run full regression with recurring progress yields

**Files:**

- Test: `tests/`

- [ ] **Step 1: Run the full suite once**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final' tests\
```

Use the directive's explicit long timeout. While the process is active, yield new
output or a progress status at intervals no longer than 50 seconds. Do not kill,
restart or duplicate the process. Expected: zero failed tests.

- [ ] **Step 2: Compare collection cardinality**

Run collect-only again and require no unexplained deletion relative to Task 0.
Expected growth is solely the new remediation test nodeids. Record baseline, final
and delta counts. Use the exact same `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python
`-B`, and external `cache_dir` settings as Task 0 Step 3.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final' --collect-only -q tests\
```

---

### Task 9: Final fail-closed audit and handoff

**Files:**

- Read: every allowed-write path
- Read: Git state and external archive/root state

- [ ] **Step 1: Prove exact implementation path set**

Classify the final changed/untracked set as:

- governance: successor spec, plan, directive, `.gitattributes`, `CLAUDE.md`;
- continuation infrastructure: capsule generator and its test;
- implementation: remediation manifest, verifier, verifier tests;
- current provenance: P2 manifest;
- curated source: exact 15 YAML files.

No other tracked path may differ. The scoped untracked/ignored map and excluded
counts must match the capsule, and the independent protected-prefix contamination
scan must find no unexpected path.

- [ ] **Step 2: Compute file identities**

For every created/modified file compute lowercase raw SHA-256 and
`git hash-object --no-filters`. Do not stage to obtain blobs.

- [ ] **Step 3: Re-prove immutable and external state**

Rehash workbook, P2 seed/gate, runner/ADB/schema/validator, frozen v1 tools/policy,
base/P2 designs, completed provenance directive and capsule generator. Require final
archive present and the two completed campaign roots absent. Do no cleanup.

- [ ] **Step 4: Report and STOP**

Report RED and GREEN commands/counts, 18 targets/15 YAML, predicate distribution,
P2 `12/14/15`, audit `692/18/674`, 15/15 `validate PASS`, focused/full pytest,
schema-v4 capsule/capture/verify identity and invariant scope, determinism hashes/output, exact path
hashes, immutable checks, HEAD/upstream,
ahead/behind, tracked/staged state and unrelated-untracked invariant result.

STOP before stage, commit, push, `verify-commit`, device contact or Tier 2 work.
Those remain separately authorized gates.
