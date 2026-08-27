# Canonical Shell-RC Curated Remediation Successor Design

> **2026-08-27 post-commit baseline resolver amendment:** The verifier resolves
> pre-remediation P2 from immutable Git object `4c484d53…`, then checks the frozen
> raw SHA-256. It never treats moving `HEAD` as the P2 baseline.
> This amendment supersedes the conflicting P2-baseline construction language in
> `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md` lines 68 and
> 324–326. That plan remains historical execution provenance; its hash-only baseline
> description must not be used to reconstruct P2 without the immutable object OID.
>
> **2026-08-18 schema-v5 recovery amendment:** The schema-v5 contract in §1.2A
> supersedes conflicting schema-v4 recovery/count/write-boundary clauses. The
> historical v4 design remains as execution provenance.

> **STATUS: APPROACH 1 + EXACT BOUNDARY APPROVED; PRE-CAPTURE SCHEMA V5
> RECOVERY APPROVED; SIX-HASH REPORT THEN HARD STOP (2026-08-18)**
>
> 사용자는 2026-08-13 대화에서 “접근안 1과 제시한 exact boundary”를 승인하고
> successor spec 작성을 지시했다. 이후 bounded remediation Tasks 0-5와
> continuation capsule v3 설계가 승인되었다. 2026-08-14 추가 교정은
> scoped continuation schema v4 producer/consumer focused TDD, P1 invariant-scope
> allowlist와 첫 recovery capsule을 도입했다. 2026-08-18 recovery amendment는
> schema v5 verifier-owned evidence 제외, 안전성 재분류 수용, 본
> spec/plan/directive 정렬 및 새 6개 해시 보고까지만 연다. P2 large-file
> identity, P3 quiescence precheck 및
> `.gitignore` 변경은 이 범위에 포함되지 않는다. 그 보고 후 hard STOP이며 fresh
> capture/verify, Tasks 6-9, stage, commit, push, device 접촉, campaign 재실행 및
> cleanup은 새 exact authorization 전까지 승인되지 않았다.

**Goal:** curated YAML을 authoritative artifact로 유지하면서 canonical shell-RC
blocker 18행을 기존 `verify_shell` 계약만으로 fail-closed 교정하고, 기존 P2
provenance 관계와 frozen v1 evidence를 잃지 않는 결정론적 host verifier 및 v2
evidence를 제공한다.

**Decision:** P2 manifest의 schema, 12 mapping, 14 selector, 15 binding, workbook
pin, campaign origin은 유지한다. 교정 대상인 15 binding의 `step_projection`만
승인된 remediation 결과와 함께 갱신한다. 별도 remediation manifest가 18행의
baseline projection, source/pattern/predicate, renderer, sentinel과 provenance
lineage를 고정한다. P2 G4는 계속 live curated YAML과 P2 projection의 exact
일치를 검사한다.

---

## 1. Authority and Supersession

### 1.1 Normative inputs

| 입력 | raw SHA-256 | Git blob (`--no-filters`) |
|---|---|---|
| base design `docs/superpowers/specs/2026-07-27-shell-rc-remediation-design.md` | `af800c57d81f25b3419e51d522247f83956858b57f2d14157e546bd5a6e48ef6` | `bc63b8f69f1fc79757adb41f7f43600491b67f00` |
| P2 design `docs/superpowers/specs/2026-08-12-shell-rc-p2-provenance-manifest-design.md` | `3e8fe99da9cb6541ce3b17bdad12ed5be417401666d99d209c92b13dbc67f7b0` | `fafc06e7da4f98d44a796903e4e70b36cab89321` |
| P2 manifest `provenance/ss_call_shell_rc_manifest.yaml` | `b4544cf636bf7be22fc9ba0a05c0b217c35710eceb92db9994e28ce0b3d88e3c` | `d595574f7a85b2f467b5eaeaaac601276236e581` |
| P2 seed tool `scripts/gen_provenance_manifest.py` | `e9d8710929b55161897ff3a092bc6cf6a9a5ac226f34dd4262b5877f8f68472f` | `3a5c509b67fef2496744a0bd3d0ecb9d8f0381fb` |
| P2 gate `tests/test_provenance_manifest.py` | `919eff565abcb726049a0523d9fa0269edab266462ff62d2411997051c28af71` | `9936deae1abfd9825e39037285b970e65f5bca89` |
| workbook `tc_samples/TC_1.xlsx` | `160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa` | `24593d11dd80a2b3711655bd0c5216ee9157dedc` |
| risk policy v1 | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` | `3a1373bf32a4a074a3e57863bb7702d34fe573ed` |
| risk audit v1 | `3d9903854a8c4d4cbb64edec4b412563a3ac4626f0ad25cf2934d06d44e61d34` | `3e5680bc6b8733162d8691189cdccd0ab564d1d9` |

Official campaign evidence is archived at
`C:\tmp\tc-runner-provenance-archive\20260812-final\evidence-root\PROVENANCE_EVIDENCE.json`.
It is 319,583 bytes with raw SHA-256
`f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a`.
The archive is a protected read-only input and is never an allowed-write path.

Dispatch-time Git HEAD, upstream, index fingerprint, tracked/staged state and the
selected untracked/ignored invariant map are not pinned in this design. The Gate
0.75 directive and its fresh external dispatch envelope bind those values
immediately before execution.

### 1.2 Continuation capsule v4 alignment

The approved spec, plan and directive are intentionally review artifacts before
publication. `dispatch_capsule.py` accepts directive and spec identities under this
fail-closed split:

- every identity path is exact repo-relative; absolute paths remain invalid;
- a tracked directive/spec keeps the historical rule: worktree blob must equal
  `HEAD`, with an optional supplied SHA required to match the same bytes;
- an untracked directive/spec is accepted only when it is an ordinary, unignored
  `git ls-files --others --exclude-standard` file and the capture command supplies
  its exact lowercase raw SHA-256;
- an absent, ignored, link-like, wrong-hash or changed governance input is rejected;
- verify reuses the raw SHA-256 stored in the capsule and applies the same identity
  branch twice before accepting live state.

Full-scope compatibility is unchanged: clean capture preserves schema v2 and has no
`tracked_worktree` field; dirty continuation without invariant selectors preserves
schema v3 and the complete untracked/ignored content maps. Continuation is accepted
only when every repeatable
`--allow-dirty-path` is an exact repo-relative tracked path and the supplied set
equals the live tracked-dirty set. Schema v3 records the sorted rows as
`{path, raw_sha256, git_blob_no_filters}` plus their canonical JSON hash; verify
remeasures the same bytes twice and rejects missing, extra, duplicate, absolute or
drifted paths. Staged state must remain clean, `HEAD == origin/master`, and
ahead/behind must remain `0/0`. There is no `SkipVerify` path.

Continuation capture also requires
`--tracked-worktree-sha256 <lowercase-64-hex>` whenever any
`--allow-dirty-path` values are supplied. The value must equal the measured
`tracked_worktree.canonical_json_sha256` before publication. Missing, malformed or
mismatched values are input-invalid; supplying it without dirty paths is also
input-invalid so clean schema-v2 behavior cannot silently ignore a continuation
authorization.

Scoped dirty continuation emits schema v4. It requires at least one exact
`--invariant-path` or repo-relative directory `--invariant-prefix`, plus
`--invariant-scope-sha256 <lowercase-64-hex>`. Selectors are normalized and sorted;
duplicates, absolute paths, overlapping prefixes and exact paths redundant beneath
a prefix are input-invalid. The external digest must equal the SHA-256 of canonical
JSON `{"exact_paths":[...],"prefixes":[...],"scope_version":1}`. Supplying a scope
without dirty paths is invalid, so schema v2 cannot silently become scoped.

The scope applies only to untracked/ignored content hashing. `HEAD`, upstream,
ahead/behind, index, staged state and the complete tracked-dirty byte set remain
globally bound. Each scoped untracked/ignored map records the selected path count and
canonical content digest plus the excluded path count. In-scope content drift and
out-of-scope membership drift are rejected; out-of-scope content-only drift is not a
shell-RC invariant and is intentionally ignored. Capture and verify both reject any
exact or prefix selector that matches no current untracked/ignored file.

The approved current selector set has no prefixes and exactly these six paths:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
3. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
4. `scripts/canonical_shell_rc_remediation_manifest_v1.json`;
5. `scripts/canonical_shell_rc_remediation_check.py`;
6. `tests/test_canonical_shell_rc_remediation.py`.

Its selector digest is
`5f4d42550ed2a8aa70db3d75bcc02191b4d17ae0a2bef4483001d36457bb983f`.
P2 large-file identity records, P3 quiescence prechecks and `.gitignore` edits are
not part of this correction.

The generator/consumer focused tests must be GREEN before the governance documents
are aligned and hashed. The executor then reports exact
`DIRECTIVE_SHA256/PLAN_SHA256/SPEC_SHA256/GENERATOR_SHA256/
TRACKED_WORKTREE_SHA256/INVARIANT_SCOPE_SHA256` values and hard STOPs. A fresh user
message containing all six exact values is required before a schema-v4 capture;
capture and its immediate
verify must have no intervening pytest, collect-only, validation, or other
repository-mutating command. Publication of the generator/tests is deferred to the
final Git gate and is not a capture prerequisite; stage, commit and push remain
separately prohibited.

### 1.2A Schema-v5 verifier-owned evidence recovery

The 2026-08-18 recovery keeps the six exact invariant paths and no ordinary prefix
selectors, but adds one deliberately unbound ignored-output ownership boundary:

```json
{
  "exact_paths": [
    "HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md",
    "docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md",
    "docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md",
    "scripts/canonical_shell_rc_remediation_manifest_v1.json",
    "scripts/canonical_shell_rc_remediation_check.py",
    "tests/test_canonical_shell_rc_remediation.py"
  ],
  "prefixes": [],
  "scope_version": 2,
  "verifier_owned_ignored_prefixes": [
    "reports/canonical_shell_rc_remediation/"
  ]
}
```

The canonical JSON is compact, ASCII, key-sorted JSON, and its SHA-256 is the new
`INVARIANT_SCOPE_SHA256`. Schema v5 is selected only for a dirty scoped capture
that supplies `--verifier-owned-ignored-prefix`; it records `schema_version=5` and
the scope object above. Clean schema v2, full dirty schema v3 and scoped schema v4
retain their existing bytes and behavior.

All directory prefixes are normalized to repo-relative forward-slash form ending
in `/`. Values are sorted and deduplicated; duplicates are rejected rather than
silently discarded. Empty, absolute, link-like and escaping selectors are invalid.
Nested or overlapping ordinary prefixes are invalid, exact paths below an ordinary
prefix are redundant and invalid, verifier-owned prefixes may not nest or overlap
one another, and any overlap between a verifier-owned prefix and an exact or
ordinary prefix selector is invalid.

For schema v5 only, the complete ignored map is partitioned before scope counts are
formed. Every path below `reports/canonical_shell_rc_remediation/` is removed from
both selected ignored rows and excluded ignored count. Its count and contents are
therefore intentionally not capsule invariants. Untracked selection is unchanged.
The generator and remediation consumer must use the same partition function and
tests must compare their selected/excluded results. The consumer accepts v5 only
when the capsule's verifier-owned list is exactly the single approved prefix;
missing, extra and misspelled lists fail with exit 2.

This narrow omission is compensated at Task 9, after the consumer has published
evidence twice. A full enumeration must contain only the preserved bundle
`f6dfecc48ea8fa09/{SUMMARY.md,shell_rc_remediation_matrix.csv}` and one new
content-addressed run bundle with the same two filenames. The `.staging` tree must
be empty or absent and every other path under the prefix is forbidden.

The schema-v5 recovery dirty boundary is exactly 21 tracked paths: the 19 paths
sealed by v4 plus `CLAUDE.md` and
`tests/fixtures/anchor/corpus_audit_baseline.json`. Fixed excluded-count pins are
retired because accumulated verifier evidence is an approved write. Capture uses a
fresh measurement and requires two stable snapshots; focused pytest is guarded by
the same read-only measurement immediately before and after it.

The deterministic renderer's device scratch behavior is an accepted semantic and
safety change, not a stale fixture correction. Within the audited
`exported_ss_call` corpus, sixteen steps move from
`READ_ONLY_SHELL` to `UNKNOWN_UNSAFE`, so audit totals change from `128/91` to
`112/107` and the audit adapter maps them from `FULL_AUTO` to `MANUAL_REQUIRED`.
Production `execution_contract` and persisted `execution_type` remain unchanged
because the adapter has no production import/call path into that derivation.
Connecting those two layers later requires separate policy approval. The accepted
scratch is bounded to `/data/local/tmp/tc_runner_rc_<hash>_$$.*` and every result
path performs cleanup; that mutation is the cost of deterministic fail-closed rc
verification.

TDD must prove the scratch name and all cleanup outcomes, the 16 transitions and
`112/107` totals, unchanged execution metadata, exact v5 prefix rejection, v2-v4
compatibility, symmetric excluded-count arithmetic, 21-row dirty sealing and the
scope-version 2 digest. The bounded recovery may edit exactly the directive, this
spec, plan, generator/test, consumer/test, audit fixture and `CLAUDE.md`. All other
artifacts and accumulated evidence remain frozen. After GREEN and two new
`CLAUDE.md` §8.2 rows, report six fresh hashes and hard STOP; capture/verify and all
Git publication still require later explicit authorization.

The focused schema-v5 bundle completed GREEN with `177 passed` under
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python `-B` and a repository-external pytest
cache. The generator measurement immediately before and after that run was stable:
selected untracked/ignored `6/0`, excluded untracked/ignored `2143/6842`.

### 1.3 Retained base-design contracts

The following base-design contracts remain normative without reinterpretation:

- §3 exact target set: 15 YAML files, 18 one-based `steps[]` coordinates;
- §5 assertion contract: all targets end as `verify_shell`, row-unique sentinel,
  source/grep/count separation and cleanup preservation;
- §5.2 timeout contract: target steps use `verify_shell` default 30 seconds and do
  not add a `timeout` field;
- §5.4 UI dump semantics and §5.5 forbidden command shapes;
- §6.2 verifier modes, §6.3 worktree identity, §6.4 deterministic v2 evidence and
  §6.5 frozen v1 preservation;
- §7 runtime-review six-row dispositions;
- §9 Tier 2 device follow-up remains a separate approval and is not host GREEN.

### 1.4 Superseded base-design contracts

P2 measured that all 15 workbook-bound blocker source joins have candidate count 0.
Curated YAML is authoritative, the workbook is a human specification, and
`export-mmi` is a non-authoritative skeleton producer. Therefore this successor
supersedes only these source-first assumptions:

- workbook cell edits are removed from the remediation write set;
- post-change `export-mmi` output is not required to reproduce curated shell oracles;
- P0/P1 rerun is not required; the archived evidence and tracked P2 manifest are the
  provenance baseline;
- the P2 manifest update is a reviewed current-projection transition, not a new
  campaign or a claim that the producer generated the remediated command;
- base §6.1 planned files and Gate 0.75 allowed paths are replaced by §3 below.

The base design file, P2 design file and P2 seed tool remain unchanged historical
inputs. This successor document records the approved evolution rather than rewriting
their implementation-time state.

---

## 2. Exact Target Contract

The set remains 18 coordinates across 15 YAML files. Predicate distribution is
`EQ_0=13`, `EQ_1=4`, `LE_1=1`.

| # | source path | step | baseline action | predicate | provenance mode |
|---:|---|---:|---|---|---|
| 1 | `ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml` | 24 | `verify_shell` | `EQ_0` | `local` |
| 2 | `ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml` | 11 | `shell` | `EQ_1` | `local` |
| 3 | `exported_ss_call/SS_TC01_permission_denied.yaml` | 10 | `verify_shell` | `EQ_0` | `p2_manifest` |
| 4 | `exported_ss_call/SS_TC01_permission_denied.yaml` | 11 | `shell` | `EQ_0` | `p2_manifest` |
| 5 | `exported_ss_call/SS_TC02_permission_allow_idle.yaml` | 11 | `shell` | `EQ_1` | `p2_manifest` |
| 6 | `exported_ss_call/SS_TC03_ringing_permission.yaml` | 15 | `shell` | `EQ_0` | `p2_manifest` |
| 7 | `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml` | 18 | `shell` | `EQ_0` | `p2_manifest` |
| 8 | `exported_ss_call/SS_TC05_boundary_values.yaml` | 9 | `shell` | `EQ_0` | `p2_manifest` |
| 9 | `exported_ss_call/SS_TC06_missed_rejected.yaml` | 10 | `shell` | `EQ_0` | `p2_manifest` |
| 10 | `exported_ss_call/SS_TC06_missed_rejected.yaml` | 11 | `shell` | `EQ_0` | `p2_manifest` |
| 11 | `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml` | 9 | `shell` | `EQ_0` | `p2_manifest` |
| 12 | `exported_ss_call/SS_TC09_offhook_permission_banking.yaml` | 20 | `shell` | `EQ_0` | `p2_manifest` |
| 13 | `exported_ss_call/SS_TC0_P0_endcall_crash.yaml` | 15 | `shell` | `EQ_0` | `p2_manifest` |
| 14 | `exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml` | 24 | `verify_shell` | `EQ_0` | `manual` |
| 15 | `exported_ss_call/SS_TC10_permission_toggle.yaml` | 24 | `shell` | `EQ_1` | `p2_manifest` |
| 16 | `exported_ss_call/SS_TC11_multi_subscription.yaml` | 20 | `shell` | `EQ_1` | `p2_manifest` |
| 17 | `exported_ss_call/SS_TC11_multi_subscription.yaml` | 21 | `shell` | `LE_1` | `p2_manifest` |
| 18 | `exported_ss_call/SS_TC12_legacy_path.yaml` | 19 | `shell` | `EQ_0` | `p2_manifest` |

The 15 `p2_manifest` rows are exactly the existing P2 blocker bindings. The manual
row and two local rows never acquire workbook selectors or invented workbook debt.

Only `action`, `command`, and `expected` may change at these coordinates. The
following are semantic invariants for all 15 files:

- step count and order;
- every non-target step;
- target description and any existing execution/compile/role metadata;
- TC metadata, source fields, `tc_name`, preconditions and top-level keys;
- no new `timeout`, alias, action type or unknown schema field.

---

## 3. Exact File Boundary

### 3.1 Design and dispatch artifacts

The successor workflow creates exactly these governance files in order:

1. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`
2. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`
3. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`

The plan and directive are created only after written spec review. Their creation is
not remediation dispatch. The directive requires a fresh explicit authorization that
pins its raw SHA-256 and the approved spec raw SHA-256.

The 2026-08-14 pre-capture correction may modify exactly seven paths: this spec, its
plan, the Gate 0.75 directive, `scripts/dispatch_capsule.py`,
`tests/test_dispatch_capsule.py`, `scripts/canonical_shell_rc_remediation_check.py`
and `tests/test_canonical_shell_rc_remediation.py`. The first five are outside the
original 21-path remediation implementation set; the last two are already in it, so
the exact continuation candidate boundary remains 26 unique paths. Only these seven
may receive pre-capture writes; the other 19 candidate paths are frozen. All seven
must be reviewed and GREEN before the six-hash hard STOP. Their stage, commit and
push remain deferred to the final publication gate.

### 3.2 Implementation-created tracked files

- `scripts/canonical_shell_rc_remediation_manifest_v1.json`
- `scripts/canonical_shell_rc_remediation_check.py`
- `tests/test_canonical_shell_rc_remediation.py`

### 3.3 Implementation-modified tracked files

- `.gitattributes`
- `provenance/ss_call_shell_rc_manifest.yaml`
- the 15 YAML paths enumerated in §2
- `CLAUDE.md`, limited after all verification is GREEN to:
  - §5.3 registration of the remediation verifier/manifest gate;
  - one §8.2 `applied` row recording the curated-authoritative remediation lesson.

The P2 manifest modification is limited to the 15 existing
`mappings[].blocker_bindings[].step_projection` objects. Its schema version,
subject, origin, workbook block, mapping count, YAML identities, selectors,
binding coordinates and `source_no` values are byte-semantically unchanged.

`.gitattributes` adds explicit `text eol=lf` rules only for the new design, plan,
directive, remediation JSON manifest, verifier and verifier test. Existing rules are
unchanged.

### 3.4 Immutable tracked and external paths

- `tc_samples/TC_1.xlsx`;
- `scripts/gen_provenance_manifest.py`;
- `tests/test_provenance_manifest.py` (existing G1-G5 meaning remains unchanged);
- `src/action_runner.py`, `src/adb.py`, `src/execution_contract.py`;
- schema, loader, normalizer, compiler and `validate_tc.py`;
- canonical inventory, risk-audit and risk-policy v1 implementation/baseline;
- base design, P2 design and completed provenance directive;
- provenance controller and controller selfcheck;
- `C:\tmp\tc-runner-provenance-archive\20260812-final`;
- all unrelated tracked changes and existing untracked/ignored backlog.

### 3.5 Generated ignored output

Verifier evidence is written only below
`reports/canonical_shell_rc_remediation/`. A directive preflight must prove this root
is ignored before the verifier writes. No generated evidence is staged or committed.

---

## 4. P2 Manifest Transition

P2 design §6 explicitly defines the seed tool as provenance bootstrap and permits
subsequent human-reviewed updates after a gate RED. This remediation is that reviewed
transition.

Before coordinated edit:

- current YAML and P2 projection are equal;
- the P2 manifest raw SHA is `b4544cf6…`;
- G1-G5 are GREEN.

During TDD:

1. a temporary candidate YAML with one rendered target must make existing G4 RED
   against the old projection;
2. the corresponding temporary P2 projection update must restore G4 GREEN;
3. deleting a selector/binding, changing origin/workbook, or changing a non-target
   projection remains RED;
4. after the exact 15 coordinated live edits, all existing G1-G5 tests are GREEN.

After coordinated edit:

- mapping/selector/binding cardinality remains `12/14/15`;
- G4 continues to mean “live authoritative YAML projection equals reviewed tracked
  projection”;
- campaign origin still states where the relationship was measured;
- the remediation manifest supplies pre-change projection and transformation lineage;
- regenerating the original seed from evidence remains a historical/bootstrap check,
  not a command for overwriting the reviewed post-remediation manifest.

No P2 schema v2, duplicate provenance manifest or G4 historical-mode branch is added.

---

## 5. Remediation Manifest v1

The JSON root has exactly these keys:

```text
schema_version
subject
baseline
targets
runtime_review_dispositions
semantic_identity
```

`schema_version` is integer `1`; `subject` is
`canonical shell-rc blocker remediation`.

### 5.1 Baseline object

The `baseline` object has exactly:

```text
inventory_head
inventory_csv_sha256
risk_matrix_sha256
risk_policy_sha256
p2_manifest_pre_remediation_head
p2_manifest_pre_remediation_sha256
p2_evidence_sha256
```

Values are the full lowercase hashes from the base design and §1. The manifest does
not pin a candidate commit, current HEAD, timestamp, absolute repo path, mtime or
dispatch nonce. `p2_manifest_pre_remediation_head` is the immutable full Git commit
OID `4c484d53e4227933b43fffad3f1846435a70c995`, whose P2 blob must match
`p2_manifest_pre_remediation_sha256`; it is a baseline identity, not a candidate.
For P2 baseline construction, this pinned-object rule supersedes the historical
implementation plan's hash-only baseline-object instructions. A verifier must fail
closed when that object or path is unavailable or its raw bytes do not match; it
must not fall back to `HEAD`, `HEAD^`, another ancestor or worktree bytes.

### 5.2 Target objects

`targets` has exactly 18 entries in §2 order. Every entry has the same exact keys:

```text
row_key
source_path
step_index
baseline_action
baseline_command
baseline_command_sha256
classification
renderer_kind
source_command
grep_pattern
predicate_kind
predicate_value
sentinel
timeout_policy
provenance
```

Constraints:

- `row_key = source_path + "#" + decimal(step_index)`;
- baseline action/command are read from Git object `78b3ac34…` and the command hash is
  raw UTF-8 SHA-256 of `baseline_command`;
- `classification` is the frozen risk-policy class;
- `renderer_kind` is `stream_count` for 16 logcat rows or
  `uiautomator_dump_count` for the two local XML rows;
- `source_command` contains no pipeline; for stream rows it is the exact logcat
  producer and for UI rows it is exactly `uiautomator dump`;
- `grep_pattern` is the frozen pattern without shell quote delimiters;
- `predicate_kind` is `EQ_0`, `EQ_1` or `LE_1`; `predicate_value` is integer `0` or
  `1` and must agree with the kind;
- `sentinel` follows §6.1 and is globally unique;
- `timeout_policy` is exactly `verify_shell_default_30s`;
- `provenance` has exact keys `mode`, `yaml_path`, `source_no`; P2 rows use
  `mode=p2_manifest` with their existing values, while local/manual rows use their
  mode and set non-applicable values to JSON `null`.

Manifest strings containing NUL, CR, LF, an unescaped single quote in a grep pattern,
or an unsupported predicate are input-invalid. There is no free-form shell template
field.

### 5.3 Runtime-review dispositions and semantic hashes

`runtime_review_dispositions` contains the exact six rows and dispositions retained
from base design §7. No source YAML in this list is modified.

`semantic_identity` has exactly `targets_sha256` and
`runtime_review_dispositions_sha256`. Each is SHA-256 over compact UTF-8 canonical
JSON of the corresponding array (`sort_keys=True`, separators `(',', ':')`,
`ensure_ascii=False`) followed by no newline. The raw manifest is serialized as
UTF-8/LF, sorted keys, two-space indentation and one terminal LF.

---

## 6. Deterministic Assertion Renderer

### 6.1 Stable identifiers

For each row:

```text
suffix = sha256(UTF-8(source_path + "#" + step_index))[:12]
sentinel = "__TC_ASSERT_OK_" + suffix + "__"
temp = "/data/local/tmp/tc_runner_rc_" + suffix + "_$$." + extension
```

The extension is `txt` for `stream_count` and `xml` for
`uiautomator_dump_count`. All 18 suffixes, sentinels and temp templates must be
unique. `$` is emitted literally for Android shell expansion at runtime.

### 6.2 Operation order

The renderer emits a single POSIX-shell command string with this fixed state machine:

1. assign `tmp`;
2. remove stale temp and capture `pre_cleanup_rc`;
3. on pre-cleanup failure, write `TC_ASSERT_PRE_CLEANUP_RC=<rc>` to stderr and exit
   that rc without running the source;
4. execute the source and capture `source_rc`;
5. on source failure, write `TC_ASSERT_SOURCE_RC=<rc>`, attempt cleanup, additionally
   report cleanup failure, and exit the original source rc;
6. execute `grep -c '<pattern>' "$tmp"` and capture `grep_rc`;
7. accept grep rc 0 or 1; on rc greater than 1, report `TC_ASSERT_GREP_RC=<rc>`,
   cleanup, and exit the original grep rc;
8. reject empty or non-decimal count with `TC_ASSERT_COUNT_INVALID=<value>`, cleanup,
   and exit 1;
9. evaluate the exact predicate; on mismatch report
   `TC_ASSERT_COUNT=<n> EXPECTED=<predicate>`, cleanup, and exit 1;
10. remove temp and capture `cleanup_rc`;
11. on cleanup failure, report `TC_ASSERT_CLEANUP_RC=<rc>` and exit that rc;
12. print the row sentinel with one newline and exit 0.

For `stream_count`, the source command redirects stdout to `"$tmp"`. For
`uiautomator_dump_count`, the source is rendered as
`uiautomator dump "$tmp" >/dev/null 2>&1`; grep reads that XML path. Source stderr is
not laundered into count input.

Every failure-path cleanup preserves the primary failure rc. If its cleanup also
fails, it emits `TC_ASSERT_CLEANUP_RC=<rc>` but still exits the primary rc. The only
success stdout is the sentinel. Diagnostics go to stderr.

### 6.3 Predicate renderer

- `EQ_0`: `[ "$count" -eq 0 ]`
- `EQ_1`: `[ "$count" -eq 1 ]`
- `LE_1`: `[ "$count" -le 1 ]`

The diagnostic predicate text is exactly `count==0`, `count==1` or `count<=1`.

### 6.4 Forbidden output shapes

The verifier rejects target commands containing any of the following semantic shapes:

- source-to-grep pipeline;
- terminal `grep -c` used directly as step verdict;
- `|| echo 0` or unconditional success fallback;
- generic expected value `"0"` or `"1"`;
- `/sdcard` temp path;
- shared temp coordinate;
- sentinel on any failure branch;
- target `timeout` field or any changed field outside `action/command/expected`.

---

## 7. Verifier Architecture

`scripts/canonical_shell_rc_remediation_check.py` exposes:

```text
verify-worktree
verify-commit --candidate-head <full-lowercase-40-hex-sha>
```

Both modes consume the remediation manifest and existing frozen inventory/risk
inputs. They do not import or execute the runner, ADB, device tools or exporter.

### 7.1 Pure functions

The module exposes testable pure functions:

- `canonical_json_sha256(value: object) -> str`;
- `sentinel_for(source_path: str, step_index: int) -> str`;
- `evaluate_count(source_rc: int, grep_rc: int, count_text: str,
  predicate_kind: str, predicate_value: int) -> tuple[bool, str]`;
- `render_command(target: dict) -> str`;
- `load_and_validate_manifest(path: Path) -> dict`.

`evaluate_count` distinguishes source failure, grep infrastructure failure, invalid
count, predicate mismatch and success. Host tests do not claim Android execution.

### 7.2 Candidate comparison

For each target the verifier:

- loads baseline YAML from Git object `78b3ac34…`;
- proves baseline action/command/hash and `(source_path, step_index)` identity;
- renders the sole accepted command from manifest fields;
- requires candidate `action=verify_shell`, `command=rendered`, and
  `expected=sentinel`;
- compares parsed file semantics and permits only the three target fields;
- loads pre-remediation P2 from `p2_manifest_pre_remediation_head` and verifies its
  raw bytes against `p2_manifest_pre_remediation_sha256` before comparison;
- verifies P2 rows equal the updated P2 manifest projection;
- verifies manual/local rows are absent from P2 mappings;
- requires 692 baseline rows, 692 candidate rows, 18 remediated rows, 674 non-target
  rows, 74 unchanged advisory rows, six unchanged runtime-review rows and zero
  unresolved cutover blockers.

The verifier checks frozen v1 script/policy hashes and inventory/risk-matrix replay.
It never modifies v1 artifacts.

### 7.3 Worktree identity

`verify-worktree` records and rechecks:

- candidate HEAD;
- per allowed-write path `{worktree_blob,index_blob,head_blob}`;
- full index fingerprint from `git ls-files --stage -z`;
- full pre-existing non-allowed untracked leaf map with file type and
  `git hash-object --no-filters` blob;
- parsed candidate inventory semantic hash;
- remediation manifest semantic hashes;
- verifier normalized source hash;
- approved spec, directive and P2 evidence raw hashes supplied by directive-bound
  arguments.

The index fingerprint must be identical before and after. Existing unrelated
untracked assets may not be added, removed, type-changed or content-changed. The
fresh spec/plan/directive and approved implementation-created files are exact
allowed paths, not broad directory allowances.

### 7.4 Commit mode

`verify-commit` reads the candidate entirely from Git objects. It is unavailable
until a separate user-approved commit exists. It checks the same target/non-target
semantics and records candidate commit identity. It does not perform stage, commit
or push.

---

## 8. Evidence Output and Exit Contract

The verifier builds two independent staging bundles under:

```text
reports/canonical_shell_rc_remediation/.staging/<nonce>/
```

Each bundle contains exactly:

- `shell_rc_remediation_matrix.csv`
- `SUMMARY.md`

Timestamp, nonce, absolute path, mtime and staging path are absent from file content.
CSV row order is frozen inventory order; SUMMARY section order is fixed by tests.
The two independent runs must be byte-identical file by file.

Final output is atomically published under:

```text
reports/canonical_shell_rc_remediation/<input_digest_16>/
```

The digest binds baseline/candidate inventory, allowed-path blobs, untracked invariant
map, remediation manifest semantic hashes, verifier hash, approved spec hash,
directive hash and P2 evidence hash. Existing final output is accepted only if both
files are byte-identical; it is never overwritten.

Exit codes:

| code | meaning | final evidence |
|---:|---|---|
| 0 | every acceptance gate GREEN | publish |
| 1 | measurable remediation contract violation | publish violation evidence |
| 2 | invalid manifest/hash/path/mode/directive-bound input | no final publish |
| 3 | Git/YAML/filesystem/atomic-publish infrastructure failure | no final publish |

Exit 2/3 removes only the verifier-created staging directory. It never cleans any
campaign root, unrelated report, repository file or user backlog.

---

## 9. TDD and Verification Gates

### Gate A — written design review

- this spec exists as the sole new worktree path created by this slice; the
  pre-existing unrelated untracked backlog remains present and untouched;
- placeholder, ambiguity, scope and internal-consistency self-review is clean;
- user reviews the actual file and explicitly approves it;
- no implementation file is changed.

### Gate B — implementation plan and Gate 0.75 directive

After Gate A approval:

1. create the exact implementation plan using the writing-plans workflow;
2. create the Gate 0.75 directive;
3. pin approved spec raw SHA, current P2 manifest raw SHA, P2 evidence SHA, workbook
   SHA and frozen v1 identities;
4. enumerate every allowed-write path and command;
5. complete the approved seven-path pre-capture correction and compute exact
   directive/plan/spec/generator/tracked-worktree/invariant-scope hashes;
6. report those six hashes and hard STOP for explicit capsule authorization.

After a later exact six-hash authorization, capture uses only repo-relative
directive/spec paths plus their exact lowercase raw SHA-256 values, repeatable
`--allow-dirty-path` values equal to the complete live tracked-dirty set, and the
authorized `--tracked-worktree-sha256`, exact scoped selectors and the authorized
`--invariant-scope-sha256`. It requires `HEAD == origin/master`, ahead/behind `0/0`,
a clean index, complete tracked-worktree stability and scoped untracked/ignored
identity stability; it does not require the approved tracked continuation paths to
be committed.

No prior capsule or campaign authorization is reusable.

### Gate C — RED

After exact directive dispatch approval:

- write verifier tests before implementation;
- missing remediation manifest/verifier makes focused test collection RED;
- pure truth table covers source rc `{0,1}`, grep rc `{0,1,2}`, count
  `{empty,non-decimal,0,1,2}`, and predicates `EQ_0/EQ_1/LE_1`;
- renderer mutation fixtures reject pipeline, fallback success, wrong sentinel,
  shared temp, `/sdcard`, changed non-target field and P2 projection mismatch;
- temporary YAML-only remediation makes existing P2 G4 RED; coordinated temporary
  projection makes it GREEN.

### Gate D — GREEN implementation

- create manifest and verifier minimally to satisfy Gate C;
- update exactly 18 target steps across 15 YAML files;
- update exactly 15 P2 step projections;
- existing P2 G1-G5 remain GREEN with `12/14/15`;
- focused verifier/provenance/inventory/risk/dispatch-sensitive tests are GREEN;
- each of the 15 YAML files has `validate PASS`;
- verifier `verify-worktree` exit 0 and reports all §7.2 cardinalities;
- two verifier runs are byte-identical;
- forbidden/unrelated path delta is 0.

### Gate D.1 — scoped schema-v4 continuation checkpoint before Task 6

- run the focused continuation generator/consumer nodeids with
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-B`, and a pytest cache outside the repo;
- align this spec, the plan and directive only after those nodeids are GREEN, then
  compute the fresh directive/plan/spec/generator hashes and the canonical
  tracked-worktree and invariant-scope hashes;
- report those exact six lowercase values and hard STOP;
- only after a fresh user message binds all six values, capture a schema-v4 capsule
  with the exact 19 tracked-dirty paths produced by the approved Tasks 0-5 plus
  capsule generator/test alignment, the exact six-path invariant selector set and
  the exact authorized tracked-worktree/scope hashes;
- require exact `tracked_worktree` bytes, clean index, `HEAD == origin/master`,
  ahead/behind `0/0`, and unchanged scoped untracked/ignored maps and excluded
  counts;
- between capture and its immediate verify, run no pytest, collect-only, validation,
  or other command that can mutate repository state;
- verify that same capsule, then STOP unless the fresh user authorization also
  explicitly opens Tasks 6-9.

No stage, commit, push, recapture-after-verify or cleanup is part of this checkpoint.

### Gate E — regression and governance reconciliation

- run full `venv/Scripts/python.exe -B -m pytest tests/` with zero failures;
- verify test nodeid count has no unexplained deletion;
- run `git diff --check`;
- verify exact path set, raw SHA-256 and Git blobs;
- add the bounded `CLAUDE.md` entries only after all technical gates are GREEN;
- rerun affected documentation/static checks after the governance edit;
- prove final archive present and two completed campaign roots remain absent;
- prove tracked/staged changes are only approved paths and unrelated untracked map is
  unchanged.

Tests may create only framework-managed temporary files and the directive-approved
ignored verifier output. No device, ADB, network, dependency installation, campaign
execution or campaign cleanup is permitted.

### Gate F — STOP before Git publication

Report:

- every created/modified path classified by design/governance/implementation/YAML;
- the two continuation infrastructure paths (`scripts/dispatch_capsule.py` and
  `tests/test_dispatch_capsule.py`) classified separately;
- raw SHA-256 and `git hash-object --no-filters` for every path;
- RED/GREEN commands and counts;
- 18/15 target cardinality, `12/14/15` P2 cardinality and 692/18/674 audit counts;
- determinism output hashes and generated evidence location;
- validate and full pytest results;
- immutable and forbidden-path checks;
- HEAD/upstream/ahead-behind/tracked/staged/untracked invariant state.

Then STOP. Stage, commit and push each require separate explicit authorization and the
§7.2 exact-path relay. Device follow-up remains a separate Tier 2 task.

---

## 10. Rejected Alternatives

### 10.1 Keep P2 manifest byte-immutable and move G4 to historical Git

Rejected because G4 is intentionally the live curated projection guard. Moving it to
history would weaken the current-authoritative relation and create two current gates.

### 10.2 Introduce P2 schema v2 with baseline/current projections

Rejected as unnecessary schema and generator migration. The remediation manifest
already preserves baseline/transformation lineage while P2 v1 guards current binding.

### 10.3 Regenerate the P2 manifest from old campaign evidence after remediation

Rejected because the evidence contains pre-remediation projections. The seed tool is
bootstrap/provenance proof, not an overwrite mechanism after reviewed evolution.

### 10.4 Edit workbook cells or make exporter authoritative

Rejected by measured P1 evidence and the approved curated-authoritative P2 decision.
No workbook provenance is invented for hand-authored shell oracles.

### 10.5 YAML-only quick fix

Rejected because it makes P2 G4 RED, loses deterministic transformation lineage and
reintroduces source-of-truth drift.
