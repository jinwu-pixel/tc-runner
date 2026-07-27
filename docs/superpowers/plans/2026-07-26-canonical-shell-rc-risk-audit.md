# Canonical Shell RC Risk Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, host-only companion audit that joins all 692 frozen canonical RC-sensitive inventory rows to an exact reviewed RC policy while preserving the Slice ⑤A CSV bytes.

**Architecture:** `canonical_shell_rc_risk_audit.py` consumes the frozen V3 inventory CSV and a versioned JSON policy keyed by exact `row_key`, `action`, and `command_sha256`. The 24 reviewed command exceptions are semantic-manifest- and file-SHA-locked. Closed static detectors additionally classify 74 high-confidence `verify_shell` oracle advisories (37 numeric-count + 37 fallback/collision/empty-equality). Remaining `shell` rows receive `REQUIRE_ZERO`; remaining `verify_shell` rows receive `VERIFY_ZERO_AND_EXPECTED`. The tool reports the 18 reviewed canonical-default rc blockers separately from the 74 pre-existing stdout-oracle advisories, emits a one-row-per-input CSV and deterministic SUMMARY, and fails closed on frozen input/policy identity, join, final-state drift, or partial evidence writes.

**Tech Stack:** Python standard library, pytest, CSV/JSON, SHA-256. No ADB, device, network, or new dependency.

## Global Constraints

- Permitted ⑤A changes are the optional exact
  `canonical_shell_rc_inventory.py --head <full-sha>` replay path, atomic
  publication of its CSV+SUMMARY evidence pair, and their tests. Default
  current-HEAD measurement behavior and frozen CSV bytes remain unchanged.
- Frozen input identity: HEAD `78b3ac34e9f8bacabe926172dd199342b7eb58c5`, inventory CSV SHA-256 `b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f`, 692 rows (`shell` 470 + `verify_shell` 222).
- Frozen policy identity: file SHA-256
  `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed`,
  24 overrides, semantic manifest
  `d42e891471bedb10a9a35a879670051d0a2ffc62ff514f9a718b7ef811e61cc3`.
- Preserve every input `row_key`, `action`, and `command_sha256` exactly once.
- Tests replay the explicit `78b3ac3` Git object; they must not regenerate the
  frozen CSV from the post-landing current HEAD.
- Do not infer runtime rc observations. Static classifications describe contract risk only.
- Do not attribute the 74 stdout-oracle advisories to the canonical-default
  cutover. They are a separate, non-corpus-mutating review queue.
- Do not add `allowed_exit_codes` or change runner/schema/TC files.
- No staging, commit, push, device call, or ignored runtime bundle mutation.

---

### Task 1: Exact Reviewed Policy

**Files:**
- Create: `scripts/canonical_shell_rc_risk_policy_v1.json`
- Test: `tests/test_canonical_shell_rc_risk_audit.py`

**Interfaces:**
- Consumes: frozen inventory rows with `row_key`, `command_sha256`, `source_path`, `step_index`, and `command`.
- Produces: JSON object with `schema_version`, `inventory_sha256`,
  `inventory_row_count`, `override_count`, `override_identity_sha256`,
  and `overrides`.

- [x] **Step 1: Write the failing policy tests**

Test that policy entries have unique `(row_key, command_sha256)` keys and the exact classification distribution:

```python
{
    "REQUIRE_ZERO": 449,
    "VERIFY_ZERO_AND_EXPECTED": 145,
    "COUNT_EQ_0": 13,
    "COUNT_EQ_1": 3,
    "COUNT_LE_1": 1,
    "COUNT_NUMERIC_SUBSTRING": 37,
    "EXPECTED_ERROR_FALLBACK_MASKING": 30,
    "GREP_WC_UPSTREAM_MASKING": 1,
    "NEGATED_TOKEN_SUBSTRING_COLLISION": 2,
    "PRE_POST_EMPTY_EQUALITY": 4,
    "MASKED_ASSERTION": 1,
    "OBSERVE_ONLY": 1,
    "TRANSPORT_TERMINATING": 2,
    "REVIEW_REQUIRED": 3,
}
```

The 24 overrides consist only of:

- 14 `exported_ss_call` terminal `grep -c` assertion rows, classified from their reviewed step descriptions.
- One minifile `uiautomator ... && grep -c ... || echo 0` masked assertion.
- One gallery `dumpsys | grep | head` observe-only row.
- Two exact reboot rows.
- Two gallery empty-glob `sh -c` cleanup loops.
- One minifile `for i in $(seq ...)` loop.
- Three `verify_shell` direct `grep -c`, `expected: "0"` rows whose
  desired zero-match result returns rc=1 before the expected-output check.

- [x] **Step 2: Run the policy tests and observe RED**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\test_canonical_shell_rc_risk_audit.py -q -p no:cacheprovider
```

Expected: collection failure because the policy and audit module do not exist.

- [x] **Step 3: Add the minimal exact policy**

Each override must contain:

```json
{
  "row_key": "<full HEAD:path#step>",
  "action": "shell",
  "command_sha256": "<64 lowercase hex>",
  "classification": "COUNT_EQ_0",
  "reason_code": "GREP_COUNT_ZERO_EXPECTED",
  "evidence": "<source step description>"
}
```

Static detectors are restricted to the frozen inventory fields and the exact
current-corpus count invariants. Never classify from command hash alone.

- [x] **Step 4: Re-run the policy tests**

Expected: policy shape and distribution tests pass; audit-module tests remain RED.

---

### Task 2: Fail-Closed Companion Audit

**Files:**
- Create: `scripts/canonical_shell_rc_risk_audit.py`
- Test: `tests/test_canonical_shell_rc_risk_audit.py`

**Interfaces:**
- Consumes: `load_inventory(path: Path) -> tuple[InventoryIdentity, tuple[dict[str, str], ...]]`
- Consumes: `load_policy(path: Path) -> Policy`
- Produces: `build_audit(identity, rows, policy) -> AuditReport`
- Produces: `render_artifacts(report) -> tuple[bytes, bytes]`
- CLI: `main(argv=None) -> int`, with required `--inventory`, optional `--policy`, `--out-dir`, and `--verify-determinism`.

- [x] **Step 1: Add adversarial RED tests**

Cover:

- CSV SHA mismatch -> exit 2 and no output.
- Missing, duplicate, extra, or command-hash-drift policy entry -> exit 2 and no output.
- Duplicate inventory `row_key` -> exit 2.
- Input or policy bytes changing before write -> exit 3 and no output.
- `grep -c` truth table: stdout 0/rc1 is valid for `COUNT_EQ_0`, while stdout 1+/rc0 violates it.
- `COUNT_EQ_1` cannot be proven by rc alone.
- `|| echo 0`, pipeline-to-`head`, empty-glob loop, missing `seq`, and reboot rows retain their explicit non-`REQUIRE_ZERO` classifications.
- A patched `src.cli.ADB` constructor that raises is never called.

- [x] **Step 2: Run tests and observe RED**

Expected: missing functions/classes and incorrect exit behavior.

- [x] **Step 3: Implement the minimal audit**

Required constants:

```python
SCHEMA_VERSION = "canonical-shell-rc-risk-audit-v1"
CLASSIFICATIONS = {
    "REQUIRE_ZERO",
    "VERIFY_ZERO_AND_EXPECTED",
    "COUNT_EQ_0",
    "COUNT_EQ_1",
    "COUNT_LE_1",
    "COUNT_NUMERIC_SUBSTRING",
    "EXPECTED_ERROR_FALLBACK_MASKING",
    "GREP_WC_UPSTREAM_MASKING",
    "NEGATED_TOKEN_SUBSTRING_COLLISION",
    "PRE_POST_EMPTY_EQUALITY",
    "MASKED_ASSERTION",
    "OBSERVE_ONLY",
    "TRANSPORT_TERMINATING",
    "REVIEW_REQUIRED",
}
```

Output columns:

```text
schema_version,input_csv_sha256,row_key,source_path,step_index,action,
command_sha256,command,expected,timeout_ms,classification,reason_code,evidence,
canonical_rc_contract,remediation_requirement
```

For default rows:

```text
classification=REQUIRE_ZERO
reason_code=NO_REVIEWED_NONZERO_SIGNAL
canonical_rc_contract=rc == 0
remediation_requirement=NONE_FROM_STATIC_AUDIT
```

For default `verify_shell` rows:

```text
classification=VERIFY_ZERO_AND_EXPECTED
reason_code=CANONICAL_VERIFY_CONJUNCTION
canonical_rc_contract=rc == 0 and expected substring in stdout
remediation_requirement=NONE_FROM_STATIC_AUDIT
```

For the 18 cutover-blocking rows:

```text
remediation_requirement=STDOUT_PREDICATE_REQUIRED
```

The five detector-only classifications total 74 advisory oracle rows. They
retain `STDOUT_PREDICATE_REQUIRED` at row level but are reported separately
from `blocking_rows`.

For `OBSERVE_ONLY`, `TRANSPORT_TERMINATING`, and `REVIEW_REQUIRED`:

```text
remediation_requirement=RUNTIME_REVIEW_REQUIRED
```

Exit contract:

- `0`: artifact generation and all structural checks succeeded.
- `2`: invalid input/policy identity or join.
- `3`: Git/IO/self-check/determinism/final-state failure.

- [x] **Step 4: Run focused tests until GREEN**

Expected: all companion audit tests pass without touching the frozen ⑤A files.

---

### Task 3: Corpus Characterization and Determinism

**Files:**
- Modify: `scripts/canonical_shell_rc_inventory.py`
- Modify: `tests/test_canonical_shell_rc_inventory.py`
- Modify: `tests/test_canonical_shell_rc_risk_audit.py`
- Local ignored output only: `reports/canonical_shell_rc_risk_audit/<digest>/`

- [x] **Step 1: Add the current-corpus characterization**

Assert:

```python
assert len(report.rows) == 692
assert report.counts == {
    "REQUIRE_ZERO": 449,
    "VERIFY_ZERO_AND_EXPECTED": 145,
    "COUNT_EQ_0": 13,
    "COUNT_EQ_1": 3,
    "COUNT_LE_1": 1,
    "COUNT_NUMERIC_SUBSTRING": 37,
    "EXPECTED_ERROR_FALLBACK_MASKING": 30,
    "GREP_WC_UPSTREAM_MASKING": 1,
    "NEGATED_TOKEN_SUBSTRING_COLLISION": 2,
    "PRE_POST_EMPTY_EQUALITY": 4,
    "MASKED_ASSERTION": 1,
    "OBSERVE_ONLY": 1,
    "TRANSPORT_TERMINATING": 2,
    "REVIEW_REQUIRED": 3,
}
assert report.blocking_rows == 18
assert report.advisory_oracle_rows == 74
assert report.runtime_review_rows == 6
```

- [x] **Step 2: Run the focused suite**

Expected: current-corpus characterization passes.

- [x] **Step 3: Run two independent CLI executions**

First regenerate the durable input from the committed Git object:

```powershell
python scripts\canonical_shell_rc_inventory.py `
  --head 78b3ac34e9f8bacabe926172dd199342b7eb58c5 `
  --verify-determinism `
  --out-dir <ignored-output-root>
```

Require CSV SHA-256
`b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f`.
This path must work after landing when current HEAD has advanced. Both risk
audit executions then use that same frozen inventory and policy, with
`--verify-determinism`, and write to separate ignored output roots.

- [x] **Step 4: Compare artifacts**

CSV and SUMMARY SHA-256 values must be identical across both runs.

- [x] **Step 5: Fail closed on partial or stale inventory evidence**

Publish `shell_rc_inventory.csv` and `SUMMARY.md` by staging a complete
digest directory and replacing that directory once. Reject an existing
destination unless its exact child set and bytes match, and remove a newly
published destination if the post-publish HEAD/tool/runtime-input check fails.
Adversarial tests cover second-file write failure, directory replace failure,
extra entries, stale bytes, and post-publish rollback.

---

### Task 4: Governance Evidence Preparation and Final Gates

**Files:**
- Modify: `CLAUDE.md` (one §8.2 row only)
- Modify: `.gitattributes` (exact LF pins for SHA-bound policy and RESULT)
- Preserve byte-for-byte: `THOR2_J - Settings/RESULT_2026-07-24.md`

- [x] **Step 1: Verify the concurrently added approved cutover row**

Do not add a duplicate. Verify the existing 2026-07-25 row records:

```markdown
| 2026-07-25 | canonical execution contract cutover | G0~G2-device 및 Cutover 승인 충족: 2026-07-24 THOR2_J Settings legacy↔canonical 4-run 48/48·action/step/passed mismatch 0·canonical shell message rc=0·serial pin 일치. `cli run` argparse default만 canonical로 승격(`78b3ac3`); explicit `--contract-mode legacy`와 library default는 유지. legacy 제거·corpus rewrite·qa-suite cutover·신규 device campaign은 미승인 | `src/cli.py`·`THOR2_J - Settings/RESULT_2026-07-24.md`·canonical design §8.5/§11 | applied |
```

- [x] **Step 2: Verify RESULT preservation**

Require:

```text
SHA-256 6c57d95aece7892f3547e4f6cca54bdedfbffdde77e4a3e5f9e94fa4e8f1ac4b
Git blob a63e62e5a8b774908124f330a917e6235e90a90d
```

Require `text eol=lf` attributes for both the policy JSON and RESULT so their
raw SHA-256 values remain stable on Windows checkouts.

- [x] **Step 3: Run verification**

Run focused audit/scanner tests, then all `tests/`. Run explicit protected-prefix contamination scan and verify no unexpected path.

- [x] **Step 4: Audit exact paths and STOP**

Expected new scope beyond the existing four ⑤A/④ files:

```text
scripts/canonical_shell_rc_risk_audit.py
scripts/canonical_shell_rc_risk_policy_v1.json
tests/test_canonical_shell_rc_risk_audit.py
CLAUDE.md
.gitattributes
docs/superpowers/plans/2026-07-26-canonical-shell-rc-risk-audit.md
```

`THOR2_J - Settings/RESULT_2026-07-24.md` remains byte-identical and untracked as an exact-path future commit candidate.

Do not stage, commit, or push. Report the exact-path commit grouping decision as a separate user gate.
