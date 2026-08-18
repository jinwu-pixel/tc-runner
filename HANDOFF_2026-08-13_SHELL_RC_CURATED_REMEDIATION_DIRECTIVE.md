# Gate 0.75 Directive — Canonical Shell-RC Curated Remediation

> **DIRECTIVE ID:** `RB-20260813-shellrc-curated-remediation-t1`
>
> **STATUS:** `PRE-CAPTURE SCHEMA V5 RECOVERY CORRECTION AUTHORIZED; SIX-HASH REPORT THEN HARD
> STOP; CAPTURE/VERIFY/STAGE/COMMIT/PUSH NOT AUTHORIZED`
>
> The user approved the 2026-08-18 schema-v5 recovery amendment described below:
> focused TDD, spec/plan/directive alignment and a six-hash report followed by a
> hard STOP.
> Existing changes must be preserved. This does not authorize capsule capture or
> verify, stage, commit, push, device contact, campaign rerun or cleanup.

## 0. Purpose and Authority

This is the successor design's Gate 0.75 host-only Tier 1 execution directive. It
converts exactly 18 known shell-RC blockers in 15 authoritative curated YAML files to
deterministic fail-closed `verify_shell` assertions, updates exactly the 15 existing
P2 current projections, adds a separate baseline/transformation manifest and host
verifier, produces deterministic ignored v2 evidence, and preserves all non-target
semantics and frozen v1 evidence.

Normative authority, in descending order:

1. the user's 2026-08-14 continuation authorization and any later exact gate;
2. this directive;
3. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
4. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
5. the retained contracts of the 2026-07-27 base design and 2026-08-12 P2 design;
6. live `AGENTS.md` and `CLAUDE.md` repository instructions.

If any instruction conflicts, any identity differs, or the exact behavior cannot be
implemented without expanding this boundary, STOP and report. Do not improvise.

### 0.0 2026-08-14 scoped-v4 pre-capture continuation amendment

The user's latest 2026-08-14 approval supersedes the completed five-path v3
correction gate and makes this amendment the first repository edit of the scoped-v4
phase. For this pre-capture phase only, this amendment supersedes the conflicting
read-only/immutability/restart rules in §3.3, §4.1, §4.2 and §6.13 solely for these
seven paths:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
3. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
4. `scripts/dispatch_capsule.py`;
5. `tests/test_dispatch_capsule.py`;
6. `scripts/canonical_shell_rc_remediation_check.py`;
7. `tests/test_canonical_shell_rc_remediation.py`.

The exact continuation candidate write boundary remains the original 21 paths in
§3.1 and §3.2 plus the five additional governance/infrastructure paths: 26 unique
paths total. The consumer and its test are already members 20 and 21 of the original
set. During this pre-capture correction, only the seven paths above may receive new
writes. The other 19 candidate paths are frozen, including `CLAUDE.md`; their
already-present working-tree state must not be reset, restored or cleaned.

This amendment authorizes only: adding a scoped continuation schema v4 by focused
TDD; keeping full-scope clean/continuation captures byte-compatible as schema v2/v3;
adding directive-bound exact/prefix selectors plus an externally authenticated
`--invariant-scope-sha256`; updating the remediation consumer for the same contract;
aligning this directive/spec/plan; running focused tests with Python `-B`, disabled
pytest plugin autoload and an external pytest cache; and measuring the resulting six
authorization hashes. P2 large-file metadata identity, P3 quiescence precheck and
`.gitignore` changes are excluded. The six hashes are
`DIRECTIVE_SHA256`, `PLAN_SHA256`, `SPEC_SHA256`, `GENERATOR_SHA256` and
`TRACKED_WORKTREE_SHA256`, plus `INVARIANT_SCOPE_SHA256`.

After reporting those exact six lowercase SHA-256 values, the executor must hard
STOP. Capsule capture and verify require a later fresh user message containing the
exact six values. No stage, commit or push is authorized. After a later successful
capture/verify, these seven pre-capture paths become read-only again; Tasks 6-9 may
write only their original §3.1/§3.2 task paths, and `CLAUDE.md` remains gated until
all technical gates are GREEN.

### 0.0A 2026-08-18 post-validation recovery amendment

The user's exact `AUTHORIZE_RECOVERY_AMENDMENT` message temporarily supersedes the
post-verify read-only and no-recapture rules in §0.0, §2, §3.3, §4.2 and §6 solely
to edit these two governance paths:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`.

No source, test, manifest, YAML, `CLAUDE.md`, report or capsule may be edited,
deleted, cleaned, staged or otherwise changed under this amendment. In particular,
the eight lint sidecars listed below are accumulated validation evidence and must be
preserved byte-for-byte.

The first authorized schema-v4 operation completed as follows:

- capsule SHA-256
  `146582a7e40fbb76d965e3813395b1de8affb937a56bbd515174f777aa0d926e`;
- capture exit 0 with `schema_version=4`, 19 tracked rows, six exact invariant
  paths, no prefixes, selected untracked/ignored `6/0`, and excluded
  untracked/ignored `2143/6834`;
- immediate verify exit 0 with status `GREEN`;
- all 15 exact curated YAML invocations completed with 15/15 `validate PASS`;
- validation created exactly these ignored evidence files:
  `reports/lint/20260818T022205Z.json`,
  `reports/lint/20260818T022206Z.json`,
  `reports/lint/20260818T022207Z.json`,
  `reports/lint/20260818T022208Z.json`,
  `reports/lint/20260818T022209Z.json`,
  `reports/lint/20260818T022210Z.json`,
  `reports/lint/20260818T022211Z.json`, and
  `reports/lint/20260818T022212Z.json`;
- post-validation selected untracked/ignored remained `6/0`, excluded untracked
  remained `2143`, and excluded ignored changed from `6834` to `6842`.

That expected evidence accumulation activated §6 STOP before focused pytest. No
focused regression, remediation verifier, contamination gate, `CLAUDE.md` edit,
full pytest, stage, commit or push ran after the STOP.

The recovery contract is exact:

1. the two governance edits above record this history, mark Task 6 validation
   complete and forbid rerunning it, and add capsule-count guards immediately before
   and after focused pytest;
2. after those two edits, measure and report fresh lowercase
   `DIRECTIVE_SHA256`, `PLAN_SHA256`, `SPEC_SHA256`, `GENERATOR_SHA256`,
   `TRACKED_WORKTREE_SHA256` and `INVARIANT_SCOPE_SHA256`, then hard STOP;
3. no capture, verify, pytest, validation, verifier, contamination scan or other
   repository write is authorized by this amendment;
4. one later fresh user message using the exact §0.2 binding shape, the new six
   values and `AUTHORIZE_TASKS_6_9` authorizes one recovery capture plus its
   immediate verify despite the otherwise-applicable no-recapture rule;
5. recovery preflight and both capsule snapshots require selected untracked/ignored
   `6/0`, excluded untracked/ignored `2143/6842`, the same exact dirty 19 and all
   other §1.1 identities;
6. after recovery verify `GREEN`, resume at Task 6 focused regression. Task 6 YAML
   validation is already complete and must not run again.

The earlier capsule remains immutable evidence of the first authorized attempt. It
is not deleted, rewritten or used as the recovery continuation token.

### 0.0B 2026-08-18 schema-v5 safety-acceptance recovery amendment

The user's `RECOVERY AMENDMENT (schema v5)` package supersedes conflicting v4
capture/count/write-boundary and remaining-task clauses in §0.0, §0.0A, §0.2,
§0.3, §1, §2, §3.3, §4.2, §5 Steps 6-9 and §6 only as stated here. It authorizes
pre-capture edits to exactly these nine paths:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
3. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
4. `scripts/dispatch_capsule.py`;
5. `tests/test_dispatch_capsule.py`;
6. `scripts/canonical_shell_rc_remediation_check.py`;
7. `tests/test_canonical_shell_rc_remediation.py`;
8. `tests/fixtures/anchor/corpus_audit_baseline.json`;
9. `CLAUDE.md`.

Every other path is frozen. In particular, preserve the 15 curated YAML files,
P2 manifest, remediation manifest, `.gitattributes`, eight lint sidecars, all 32
existing capsules and the two-file evidence bundle under
`reports/canonical_shell_rc_remediation/f6dfecc48ea8fa09/`. The completed 15/15
`validate PASS` result is final for this recovery and those validation commands
must not be rerun. Reset, restore, cleanup, stage, commit and push are forbidden.

The schema-v5 contract is exact:

- capsule `schema_version` is `5` and `invariant_scope.scope_version` is `2`;
- `exact_paths` remains the six paths in §1.2, `prefixes` remains empty, and
  `verifier_owned_ignored_prefixes` is exactly
  `["reports/canonical_shell_rc_remediation/"]`;
- `verifier_owned_ignored_prefixes` participates in the canonical scope JSON and
  therefore in `INVARIANT_SCOPE_SHA256`;
- for schema v5 only, generator and consumer both omit every ignored path under
  that verifier-owned prefix from the selected ignored rows and from the excluded
  ignored count. The capsule deliberately binds neither count nor contents of that
  subtree;
- scope-version 2 normalization retains trailing-slash, sorting, deduplication,
  nesting and redundancy checks, applies the same prefix rules to the new field,
  and rejects overlap between the new field and either exact or ordinary prefix
  selectors;
- schema v2, v3 and v4 behavior remains unchanged;
- the remediation consumer accepts schema v5 only when the capsule lists exactly
  the one approved verifier-owned ignored prefix. Missing, extra or misspelled
  values are exit 2;
- the tracked dirty boundary at capture is exactly 21 paths: the previous 19 plus
  `CLAUDE.md` and `tests/fixtures/anchor/corpus_audit_baseline.json`.

The fixed excluded counts in §0.0A item 5 are retired. Recovery capture instead
requires a fresh capture-time measurement, two stable snapshots and identical
generator/consumer excluded-count arithmetic. Focused pytest has the same
read-only count guard immediately before and after it; any drift is a STOP.

The renderer's bounded device-side scratch mutation is accepted as an explicit
safety tradeoff:

1. exactly 16 steps in the audited `exported_ss_call` corpus move from
   `READ_ONLY_SHELL` to `UNKNOWN_UNSAFE`, changing the audit totals from `128/91`
   to `112/107`;
2. the audit adapter consequently maps those steps from `FULL_AUTO` to
   `MANUAL_REQUIRED`;
3. current production `execution_contract` and persisted `execution_type` do not
   change because no production import/call path connects this audit adapter to
   that metadata derivation;
4. connecting those layers later requires separate policy approval;
5. the bounded ephemeral scratch path
   `/data/local/tmp/tc_runner_rc_<hash>_$$.*` and cleanup on every outcome path are
   accepted because they provide deterministic fail-closed rc verification.

Focused TDD must cover scratch naming and every cleanup path, the 16 transitions
and `112/107` audit totals, unchanged execution metadata, v5 prefix
missing/extra/typo rejection, v2/v3/v4 compatibility, symmetric excluded-count
arithmetic, 21 tracked dirty rows and scope-version 2 digest binding. After GREEN,
§0.1 must contain freshly measured generator, generator-test, consumer and
consumer-test identities plus a new fixture identity row; the historical
`CLAUDE.md before remediation` identity remains unchanged.

After focused GREEN, add exactly two new `CLAUDE.md` §8.2 rows while retaining the
existing Task 7 row: one records the safety reclassification and connection-approval
requirement; the other records symmetric schema-v5 generator/consumer exclusion.
Then run `git diff --check`, measure all six fresh authorization hashes and hard
STOP. This amendment does not authorize capture or verify. A later fresh §0.2
message with all six exact values and `AUTHORIZE_TASKS_6_9` is required.

Focused schema-v5 verification completed GREEN with `177 passed in 567.83s` under
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python `-B` and a repository-external pytest
cache. The generator's immediately adjacent measurement guards were identical:
selected untracked/ignored `6/0`, excluded untracked/ignored `2143/6842`.

After that later authorization, capture and immediate verify are one uninterrupted
pair with no intervening command. Task 6 resumes at focused pytest only, guarded by
pre/post counts; the 15 validations remain forbidden. Verifier evidence publication
runs twice, followed by contamination scan, Task 8 full pytest and collect-only,
then Task 9. Task 9 compensates for the unbound verifier-owned subtree by requiring
exactly the existing `f6dfecc48ea8fa09` bundle and one newly published bundle, each
containing only `SUMMARY.md` and `shell_rc_remediation_matrix.csv`; `.staging`
residue and every other subtree path must both be zero. STOP again immediately
before Git publication.

### 0.1 Bound entry identities

| artifact/state | raw SHA-256 or exact value | Git blob (`--no-filters`) |
|---|---|---|
| entry HEAD | `db20ea487f1f2fb906c543e2262bc7066a593b93` | — |
| entry `origin/master` | `db20ea487f1f2fb906c543e2262bc7066a593b93` | — |
| entry ahead/behind | `0/0` | — |
| approved successor spec | `f5b4e53693929839997e5edcfbbecdca9ca1fac7f47d23c6ae91ab556898f6a4` | `ee957f021089f9b99a6f20878a7b943218cc8a49` |
| implementation plan | `309903e77d91ef3e39d4dc9da8a513678b28b497e597f2f4e9dbca72e98f8c69` | `1136f8ec37ce2c5b7dd94dd4fa9df386be2dd94a` |
| base design | `af800c57d81f25b3419e51d522247f83956858b57f2d14157e546bd5a6e48ef6` | `bc63b8f69f1fc79757adb41f7f43600491b67f00` |
| P2 design | `3e8fe99da9cb6541ce3b17bdad12ed5be417401666d99d209c92b13dbc67f7b0` | `fafc06e7da4f98d44a796903e4e70b36cab89321` |
| dispatch capsule generator | `4e0779c6b85c03e1bc033ee0c283c9060d1358e150b8b86481d4fa8d53d73641` | `c36a5a765dba6c20ac90184784995aee459272c9` |
| dispatch capsule tests | `4269a7c8d827a22f7c91524461d0624628fc6702a61496d97869c4fbb89b900e` | `9c5a146505acb5e105906e78aa6cc160aa4a5e0b` |
| remediation manifest current | `32e335a29a8ab45b74b2135ecaf9b85bb01e84996357af5e3f8537bdb63b32e7` | `10976a5a309b0fc547d047bd3e606f566678b3a3` |
| remediation consumer current | `999ca3f29c1aab03085a873697cc8705c6190063fc2d9a12a60c5a2987a4a7e0` | `73004e4882caf9b7a25305d7974656b3be99f2ad` |
| remediation consumer tests current | `3f511b3967bdcde02e767c411a9ed062e80480fd9fa18751db0a6325c01f2ad6` | `a39f84ba3ef690ec765b66af5db5b4cc606794c3` |
| anchor corpus audit fixture current | `bd66371401acea5f296a92a995812ae7aeb7e9ad70e3c8f71c5c3a5aebf938a5` | `d69118f02f10d5e3c693b7e8dacaaa86c10984cf` |
| P2 manifest before remediation | `b4544cf636bf7be22fc9ba0a05c0b217c35710eceb92db9994e28ce0b3d88e3c` | `d595574f7a85b2f467b5eaeaaac601276236e581` |
| P2 seed tool | `e9d8710929b55161897ff3a092bc6cf6a9a5ac226f34dd4262b5877f8f68472f` | `3a5c509b67fef2496744a0bd3d0ecb9d8f0381fb` |
| P2 G1-G5 gate | `919eff565abcb726049a0523d9fa0269edab266462ff62d2411997051c28af71` | `9936deae1abfd9825e39037285b970e65f5bca89` |
| workbook | `160cdf4ad3e4fd25c470ad9e3ae1681e8cc7b350e59fdc5acb5b196b480304fa` | `24593d11dd80a2b3711655bd0c5216ee9157dedc` |
| inventory implementation | `7731650815aa87bf7f801a911347c64c6fd4bfaaa6844b08eaf7dc78d1a4f73f` | `5247c9a0428229931704c0136c8006714a55c9df` |
| risk audit implementation | `3d9903854a8c4d4cbb64edec4b412563a3ac4626f0ad25cf2934d06d44e61d34` | `3e5680bc6b8733162d8691189cdccd0ab564d1d9` |
| risk policy v1 | `f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed` | `3a1373bf32a4a074a3e57863bb7702d34fe573ed` |
| `.gitattributes` before remediation | `095cbdb1314dcd3be5a6cae2342a8ba4cd7a3805d4eebb422cb8a8a43a70f6fa` | `23bd4f2895e629c9fc95a35eac2682db3bde65b7` |
| `CLAUDE.md` before remediation | `1606178c28e252fe3c2e18802035c7387f8953c586d1bc8f466c3107332fdd20` | `1c13c15f08278992634afdb9a5e289d1bc0b6677` |

The frozen inventory identity is HEAD
`78b3ac34e9f8bacabe926172dd199342b7eb58c5`, CSV SHA-256
`b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f`,
and risk-matrix SHA-256
`81b44a584f2b1cf83955545c7b2898c93f1a8f2a000872d1fb8576d768ffd8e4`.

The protected evidence input is exactly:

```text
C:\tmp\tc-runner-provenance-archive\20260812-final\evidence-root\PROVENANCE_EVIDENCE.json
```

It must be a regular file of 319,583 bytes with raw SHA-256
`f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a`.
The archive root is read-only.

### 0.2 Directive self-binding rule

This file cannot contain its own raw SHA without changing it. The active 2026-08-18
schema-v5 recovery authorizes measuring and reporting the six final hashes,
then requires a hard STOP. It does not authorize capture or verify. One future
capture plus its immediate verify requires a fresh user message with this exact
binding shape and the final measured directive value:

```text
AUTHORIZE_CAPSULE_CAPTURE_AND_IMMEDIATE_VERIFY: RB-20260813-shellrc-curated-remediation-t1
DIRECTIVE_SHA256: measured final directive raw SHA-256
PLAN_SHA256: measured final plan raw SHA-256
SPEC_SHA256: measured final spec raw SHA-256
GENERATOR_SHA256: measured final generator raw SHA-256
TRACKED_WORKTREE_SHA256: measured final 21-row canonical JSON SHA-256
INVARIANT_SCOPE_SHA256: measured final scope-version-2 canonical JSON SHA-256
```

That future message authorizes only §1 capture and its immediate §2 verify unless it
also explicitly names Tasks 6-9. It never implies any Git publication operation.

### 0.3 Scoped continuation capsule v4 gate

The pre-capture correction set is exactly:

1. `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`;
2. `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
3. `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
4. `scripts/dispatch_capsule.py`;
5. `tests/test_dispatch_capsule.py`;
6. `scripts/canonical_shell_rc_remediation_check.py`;
7. `tests/test_canonical_shell_rc_remediation.py`.

Its accepted behavior is repo-relative directive/spec paths, exact lowercase
SHA-256 support for ordinary unignored untracked governance inputs, exact repeatable
tracked-dirty path and byte sealing, wrong/missing/extra/duplicate/absolute-path
rejection, an exact external `--tracked-worktree-sha256` anchor with
missing/malformed/mismatch rejection, exact/prefix invariant selectors with an
external `--invariant-scope-sha256` anchor, scoped verify-time drift rejection, and
preserved full-scope schema-v2/v3 behavior.
The completed 2026-07-28 directive remains immutable; its identity test validates
the historical pinned Git objects rather than forcing the generator's current bytes
to equal a historical version.

The generator and consumer tests must pass focused v4 tests before governance
alignment. The original 21-path implementation set plus five additional paths is the
exact 26-path continuation candidate boundary; only the seven §0.0 paths may receive
writes before the six-hash hard STOP. Scoped continuation capture emits schema v4
with a canonical `tracked_worktree` payload only when the allow-list equals all 19
live dirty tracked paths and its canonical JSON digest equals the authorized
`ee425f983f723095c255a3fb5e9760aeb00d31933c47e3dde0ea27dc4f30aced`.
It also requires the exact six-path selector set in §1.2, no prefix selectors, and
the authorized invariant-scope digest
`5f4d42550ed2a8aa70db3d75bcc02191b4d17ae0a2bef4483001d36457bb983f`.
The index must be clean and `HEAD == origin/master` at `0/0`. Stage, commit and push
are deferred until after Task 9 and require a separate user Git authorization.

---

## 1. Fresh Capsule Capture Gate

### 1.1 Preconditions

After exact capture authorization and before capture, perform only read-only checks:

- actual working directory resolves to `C:\Users\momen\Projects\tc-runner`;
- HEAD and local `origin/master` both equal
  `db20ea487f1f2fb906c543e2262bc7066a593b93`, and ahead/behind is `0/0`;
- staged deltas are zero and the tracked-dirty set is exactly the 21 paths supplied
  by §1.2;
- this directive, approved spec, implementation plan and generator hashes equal the
  authorized/pinned values;
- the measured tracked-worktree canonical JSON SHA-256 equals the exact value in the
  fresh six-hash authorization;
- the normalized invariant selector canonical JSON SHA-256 equals the exact value in
  that same authorization;
- `scripts/dispatch_capsule.py`, `tests/test_dispatch_capsule.py`,
  `scripts/canonical_shell_rc_remediation_check.py` and
  `tests/test_canonical_shell_rc_remediation.py` equal the live hashes in §0.1 and
  the focused v5 test bundle is GREEN;
- the three implementation-created files in §3.2 are present and unchanged during
  capture/verify;
- the selected untracked/ignored content and both excluded counts remain stable;
- the executor leaves all unrelated untracked/ignored assets untouched;
- completed campaign roots in §6.3 remain absent and final archive remains present.

Do not fetch, clean, stage, reset, checkout, restore, delete or modify anything.

### 1.2 Exact capture operation

Run exactly once after the fresh §0.2 authorization, replacing the four
`AUTHORIZED_*` placeholders only with its exact lowercase digests:

```powershell
venv\Scripts\python.exe -B scripts\dispatch_capsule.py capture `
  --repo C:\Users\momen\Projects\tc-runner `
  --directive-id RB-20260813-shellrc-curated-remediation-t1 `
  --directive HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md `
  --directive-sha256 AUTHORIZED_DIRECTIVE_SHA256 `
  --spec docs\superpowers\specs\2026-08-13-shell-rc-curated-remediation-design.md `
  --spec-sha256 AUTHORIZED_SPEC_SHA256 `
  --allow-dirty-path .gitattributes `
  --allow-dirty-path CLAUDE.md `
  --allow-dirty-path "ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml" `
  --allow-dirty-path "ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml" `
  --allow-dirty-path exported_ss_call/SS_TC01_permission_denied.yaml `
  --allow-dirty-path exported_ss_call/SS_TC02_permission_allow_idle.yaml `
  --allow-dirty-path exported_ss_call/SS_TC03_ringing_permission.yaml `
  --allow-dirty-path exported_ss_call/SS_TC04_offhook_seed_recovery.yaml `
  --allow-dirty-path exported_ss_call/SS_TC05_boundary_values.yaml `
  --allow-dirty-path exported_ss_call/SS_TC06_missed_rejected.yaml `
  --allow-dirty-path exported_ss_call/SS_TC07_short_call_no_false_positive.yaml `
  --allow-dirty-path exported_ss_call/SS_TC09_offhook_permission_banking.yaml `
  --allow-dirty-path exported_ss_call/SS_TC0_P0_endcall_crash.yaml `
  --allow-dirty-path exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml `
  --allow-dirty-path exported_ss_call/SS_TC10_permission_toggle.yaml `
  --allow-dirty-path exported_ss_call/SS_TC11_multi_subscription.yaml `
  --allow-dirty-path exported_ss_call/SS_TC12_legacy_path.yaml `
  --allow-dirty-path provenance/ss_call_shell_rc_manifest.yaml `
  --allow-dirty-path scripts/dispatch_capsule.py `
  --allow-dirty-path tests/fixtures/anchor/corpus_audit_baseline.json `
  --allow-dirty-path tests/test_dispatch_capsule.py `
  --tracked-worktree-sha256 AUTHORIZED_TRACKED_WORKTREE_SHA256 `
  --invariant-path HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md `
  --invariant-path docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md `
  --invariant-path docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md `
  --invariant-path scripts/canonical_shell_rc_remediation_manifest_v1.json `
  --invariant-path scripts/canonical_shell_rc_remediation_check.py `
  --invariant-path tests/test_canonical_shell_rc_remediation.py `
  --verifier-owned-ignored-prefix reports/canonical_shell_rc_remediation/ `
  --invariant-scope-sha256 AUTHORIZED_INVARIANT_SCOPE_SHA256
```

No `--module-root` is allowed. The generator writes only to its fixed external
capsule root `C:\tmp\tc-runner-dispatch-capsules`. TTL is exactly 1800 seconds.
There is no `SkipVerify` path. The approved scope content-hashes six untracked files
and zero ignored files. Out-of-scope content is not read; live excluded counts
outside the verifier-owned ignored subtree are bound by capture and immediate
verify, while that subtree is deliberately unbound and compensated at Task 9.
Capsule issue time and TTL are assigned only after both snapshots finish.

`AUTHORIZED_DIRECTIVE_SHA256`, `AUTHORIZED_SPEC_SHA256`,
`AUTHORIZED_TRACKED_WORKTREE_SHA256` and `AUTHORIZED_INVARIANT_SCOPE_SHA256` are
replaced only with the exact values from the fresh §0.2 user message. Governance
and scope selectors are exact repo-relative
paths. The supplied hashes are mandatory because review/implementation artifacts may
still be untracked; ignored, missing, wrong-hash, absolute or changed inputs are
rejected. Tracked-worktree and invariant-scope hashes are mandatory for this scoped
dirty continuation; missing, malformed, mismatched or schema-v2/v3-only use is
rejected before publication.

Expected result: exit 0, a single external content-addressed schema-v5 capsule, and
a lowercase 64-hex capsule SHA-256. The first 2026-08-14 wrapper used an insufficient
1,800,000 ms orchestration timeout and ended with exit 124 before a generator result;
read-only audit proved no child process, no new capsule and no repository drift. The
historical attempt grants no reusable authorization. On any timeout or exit 2/3,
STOP without another capture.

### 1.3 Immediate post-capture verify

After exit 0, inspect the capsule as read-only and require `schema_version=5`, the
exact 21-row `tracked_worktree` set, exact six-path/no-ordinary-prefix invariant
scope, scope version 2, the one exact verifier-owned ignored prefix, selected map
identities, scoped excluded counts and expected identities. Do not mutate the
repository. Between capture and the immediate §2 verify, do not run pytest,
collect-only, validation, or any other command that can mutate repository state.

---

## 2. Exact Execution Authorization and Capsule Verify

No current message authorizes this verify. The future exact §0.2 message may batch
one capture with its immediate verify. Continuation through Tasks 6-9 additionally
requires an explicit authorization naming this directive ID.

```text
AUTHORIZE_TASKS_6_9: RB-20260813-shellrc-curated-remediation-t1
```

Without any repository mutation after capture, substitute its digest and run exactly
this command once:

```powershell
venv\Scripts\python.exe -B scripts\dispatch_capsule.py verify --repo C:\Users\momen\Projects\tc-runner --capsule-sha256 AUTHORIZED_CAPSULE_SHA256 --expected-directive-id RB-20260813-shellrc-curated-remediation-t1 --expected-directive HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md --expected-spec docs\superpowers\specs\2026-08-13-shell-rc-curated-remediation-design.md
```

`AUTHORIZED_CAPSULE_SHA256` denotes only the exact lowercase digest emitted by the
single immediately preceding capture authorized by the same fresh §0.2 message; it
is not read from memory or another file. Expected result is exit 0 within the
1800-second TTL. On exit 2/3, expiry, state drift or identity mismatch, STOP before
writing. Do not bypass verify.

After successful verify, continue to §5 Step 6 only when the user also supplied the
exact `AUTHORIZE_TASKS_6_9` line; otherwise STOP and report the verify result. Do not
recapture or re-verify after the continuation verify. Capsule expiry after successful
verify does not invalidate an authorized Tasks 6-9 sequence. If the executor session
ends or an unapproved process changes repository state after verify, STOP and report.

---

## 3. Exact Write Boundary

### 3.1 Existing tracked files allowed to change — exactly 18

1. `.gitattributes`
2. `provenance/ss_call_shell_rc_manifest.yaml`
3. `ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml`
4. `ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml`
5. `exported_ss_call/SS_TC01_permission_denied.yaml`
6. `exported_ss_call/SS_TC02_permission_allow_idle.yaml`
7. `exported_ss_call/SS_TC03_ringing_permission.yaml`
8. `exported_ss_call/SS_TC04_offhook_seed_recovery.yaml`
9. `exported_ss_call/SS_TC05_boundary_values.yaml`
10. `exported_ss_call/SS_TC06_missed_rejected.yaml`
11. `exported_ss_call/SS_TC07_short_call_no_false_positive.yaml`
12. `exported_ss_call/SS_TC09_offhook_permission_banking.yaml`
13. `exported_ss_call/SS_TC0_P0_endcall_crash.yaml`
14. `exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml`
15. `exported_ss_call/SS_TC10_permission_toggle.yaml`
16. `exported_ss_call/SS_TC11_multi_subscription.yaml`
17. `exported_ss_call/SS_TC12_legacy_path.yaml`
18. `CLAUDE.md`

### 3.2 New tracked-source candidates allowed to be created — exactly 3

19. `scripts/canonical_shell_rc_remediation_manifest_v1.json`
20. `scripts/canonical_shell_rc_remediation_check.py`
21. `tests/test_canonical_shell_rc_remediation.py`

No other repository path may be created, modified, renamed, deleted, staged or have
its file type changed. This is an exact 21-path implementation write set, not a
directory allowance.

For the pre-capture amendment only, §0.0 adds five new paths to this set and reopens
the consumer/test at members 20-21: seven currently writable paths within an exact
26-path continuation candidate boundary. The other 19 paths above are frozen until
a later successful capsule verify and explicit Tasks 6-9 authorization.

### 3.3 Protected governance paths

The following newly written governance documents are capsule-bound read-only inputs
during execution and may not change after the six-hash pre-capture STOP:

- `docs/superpowers/specs/2026-08-13-shell-rc-curated-remediation-design.md`;
- `docs/superpowers/plans/2026-08-13-shell-rc-curated-remediation.md`;
- `HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md`.

### 3.4 Generated ignored write root

The verifier alone may create and remove its own staging entries below:

```text
reports/canonical_shell_rc_remediation/
```

Before the first verifier write, `git check-ignore -v` must prove this path is
ignored by the existing `reports/` rule. Final evidence is content-addressed and may
not be staged. Cleanup is limited to a verifier-created `.staging/<nonce>` directory
after invalid-input/infrastructure failure. Existing final output is never
overwritten or removed.

Framework-managed temporary directories outside the repository are allowed for
pytest fixtures and deterministic double-generation. No other repository scratch,
report or temporary output is allowed.

---

## 4. Immutable and Forbidden Boundary

### 4.1 Immutable technical inputs

- `tc_samples/TC_1.xlsx`;
- `scripts/gen_provenance_manifest.py` and
  `tests/test_provenance_manifest.py`;
- `scripts/canonical_shell_rc_inventory.py`,
  `scripts/canonical_shell_rc_risk_audit.py`, and
  `scripts/canonical_shell_rc_risk_policy_v1.json`;
- `src/action_runner.py`, `src/adb.py`, `src/execution_contract.py`;
- all schemas, loaders, normalizers, compilers and `validate_tc.py`;
- `scripts/dispatch_capsule.py`, provenance controller and controller selfcheck
  (the §0.0 amendment supersedes this only during the seven-path pre-capture phase);
- base design, P2 design, completed provenance directives and archived v1 evidence;
- advisory 74 rows and runtime-review six source rows;
- every non-target step and every target field other than
  `action`, `command`, `expected`.

The P2 manifest may change only the 15 existing
`mappings[].blocker_bindings[].step_projection` objects. Its schema, subject, origin,
workbook, mapping order/cardinality, YAML identity, selectors, binding coordinates
and source numbers are immutable.

### 4.2 Absolutely forbidden operations

- broad or exact stage, commit, push, fetch, pull, merge, rebase, reset, restore,
  checkout, revert, tag, branch or worktree mutation;
- file deletion, rename, cleanup or permission/type change outside verifier-owned
  staging cleanup;
- device/ADB/fastboot contact, Android command execution, runtime TC execution;
- workbook, exporter, runner, schema, validator or provenance-campaign edit/rerun;
- capsule recapture/reverify after continuation verify or any `SkipVerify` equivalent;
- dependency installation/update, network access or external-system write;
- campaign root cleanup, archive mutation, capsule deletion or old report cleanup;
- weakening existing P2 G1-G5, changing test meaning to obtain GREEN, or treating
  host GREEN as `runtime PASS`.

If any forbidden operation becomes necessary, STOP and request a new design/approval.

---

## 5. Exact Execution Sequence

The implementation follows the approved plan and may not reorder a downstream GREEN
ahead of its prerequisite RED. Use `apply_patch` for repository edits.

### Step 0 — verified entry and nodeid baseline

Every pytest invocation in Steps 0-8 uses
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, Python `-B`, and the external cache directory
`C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final`.
No pytest command may write `.pytest_cache` inside the repository.

1. Complete §2 capsule verify.
2. Rehash directive, plan, spec and all §0.1 immutable inputs.
3. Prove generated output is ignored, archive present, old roots absent.
4. Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final' --collect-only -q tests\
```

Record the collection count only in the execution report. Any mismatch/error stops
the run before implementation writes.

### Step 1 — RED tests first

Create only `tests/test_canonical_shell_rc_remediation.py` and run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py::test_verifier_module_exists -q
```

Required RED: exactly one failed test because
`scripts/canonical_shell_rc_remediation_check.py` is absent. Then add the complete
manifest/predicate/renderer/candidate/P2/evidence adversarial tests from plan Task 1
and run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py -q
```

Required RED: failures are caused only by absent remediation manifest/verifier/API.
Unexpected pass, collection error or unrelated failure is a STOP condition.

### Step 2 — manifest and pure verifier GREEN

1. Add only the six approved LF rules to `.gitattributes`.
2. Create the exact 18-target manifest plus six runtime-review dispositions.
3. Prove two external generations byte-identical.
4. Create the verifier's strict manifest loader, semantic hasher, sentinel function,
   predicate oracle and renderer.
5. Run only the manifest/predicate/renderer test subset until GREEN.

Do not edit production YAML or P2 during this step.

### Step 3 — verifier comparison/evidence GREEN and characterization RED

Implement worktree/commit Git-object readers, exact target/non-target comparison,
P2 relation checks, capsule/index/untracked identity guards, deterministic two-pass
evidence, atomic publish and exit 0/1/2/3. Run:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_canonical_shell_rc_remediation.py -q
```

All pure/adversarial fixtures must be GREEN, while the live pre-remediation candidate
must be classified with exactly 18 legacy target violations and zero non-target
delta. This is the end-to-end characterization RED.

### Step 4 — coordinated 18-row YAML / 15-projection transition

Edit only the 18 target coordinates named in the approved plan. Set each to its
manifest-rendered `action=verify_shell`, exact command and row-unique expected
sentinel. Add no `timeout`. In the same bounded batch, update only the matching 15
P2 `step_projection` objects. Then run immediately:

```powershell
venv\Scripts\python.exe -B -m pytest tests\test_provenance_manifest.py -q
```

Required: 5 passed and exact `12 mappings / 14 selectors / 15 bindings`. Do not
regenerate the old evidence seed over the reviewed current projection. Any P2
failure is a STOP; do not weaken G4.

### Step 5 — validate all 15 curated YAML paths

Run `validate_tc.py` separately for exactly these files:

```powershell
venv\Scripts\python.exe -B validate_tc.py "ODIN2 - My gallary\functional\photo\GAL_FUNC_03_photo_multi_select.yaml"
venv\Scripts\python.exe -B validate_tc.py "ODIN2 - minifile\functional\trash\MNF_FUNC_27_trash_enter.yaml"
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC01_permission_denied.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC02_permission_allow_idle.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC03_ringing_permission.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC04_offhook_seed_recovery.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC05_boundary_values.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC06_missed_rejected.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC07_short_call_no_false_positive.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC09_offhook_permission_banking.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC0_P0_endcall_crash.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC0_P0_telebanking_offhook.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC10_permission_toggle.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC11_multi_subscription.yaml
venv\Scripts\python.exe -B validate_tc.py exported_ss_call\SS_TC12_legacy_path.yaml
```

Required: 15/15 `validate PASS`. This is not `runtime PASS`.

Recovery record: this step completed under capsule
`146582a7e40fbb76d965e3813395b1de8affb937a56bbd515174f777aa0d926e`.
The eight accumulated `reports/lint/20260818T0222*.json` sidecars in §0.0A are the
complete output of those 15 invocations. Do not run any of the validations again.

### Step 6 — focused regression and verifier determinism

Immediately before pytest, use the generator's schema-v5 scoped path measurement as
a read-only guard. Require selected untracked/ignored `6/0` and record the fresh
excluded untracked/ignored values from the recovery capsule; do not require the
historical fixed `2143/6842`. Then run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-task6-recovery' tests\test_canonical_shell_rc_remediation.py tests\test_provenance_manifest.py tests\test_canonical_shell_rc_inventory.py tests\test_canonical_shell_rc_risk_audit.py tests\test_dispatch_capsule.py -q
```

Required: zero failures. Repeat the same read-only scoped path measurement
immediately after pytest and require the same four freshly recorded values. Any
count or selected-map
drift is a STOP before verifier execution. Then run the following verifier operation
twice, replacing both authorization tokens only with their exact user-authorized
lowercase hashes:

```powershell
venv\Scripts\python.exe -B scripts\canonical_shell_rc_remediation_check.py verify-worktree --manifest scripts\canonical_shell_rc_remediation_manifest_v1.json --spec docs\superpowers\specs\2026-08-13-shell-rc-curated-remediation-design.md --directive HANDOFF_2026-08-13_SHELL_RC_CURATED_REMEDIATION_DIRECTIVE.md --evidence C:\tmp\tc-runner-provenance-archive\20260812-final\evidence-root\PROVENANCE_EVIDENCE.json --capsule-sha256 AUTHORIZED_CAPSULE_SHA256 --approved-spec-sha256 4484f3528a126fe1210b10a73960df11a7ab4331fb4dc86296a1d4fd2c521ba9 --approved-directive-sha256 AUTHORIZED_DIRECTIVE_SHA256 --approved-evidence-sha256 f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a --output-root reports\canonical_shell_rc_remediation
```

Both runs must exit 0 and produce/accept byte-identical CSV and SUMMARY. Required
measures: 18 targets/15 YAML, predicates `13/4/1`, P2 `12/14/15`, inventory
`692 baseline / 692 candidate / 18 remediated / 674 non-target / 74 advisory / 6
runtime-review / 0 unresolved`.

Run the exact protected-prefix contamination scan from plan Task 6 and independently
compare the capsule's scoped untracked/ignored map and scoped excluded counts. The
verifier-owned ignored subtree is not compared to the capsule and is instead subject
to the Task 9 compensating enumeration. Any in-scope content drift, other
out-of-scope membership drift or protected-prefix contamination is a STOP condition.

### Step 7 — bounded `CLAUDE.md` reconciliation

Only after Steps 1-6 are GREEN:

- add the verifier/manifest registration to §5.3;
- add one §8.2 `applied` row for the curated-authoritative/P2-current-projection plus
  baseline-transformation-manifest lesson.

No other `CLAUDE.md` text may change. Run `git diff --check`, focused remediation
tests and P2 tests again.

### Step 8 — full regression

Run exactly once:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
venv\Scripts\python.exe -B -m pytest -o cache_dir='C:\Users\momen\AppData\Local\Temp\tc-runner-pytest-cache-rb-20260813-final' tests\
```

Set the orchestration timeout to 2,400,000 ms. While active, use recurring output
yields at intervals no longer than 50 seconds. Do not kill, restart, duplicate or
parallelize this process. Required: zero failed tests. Then repeat collect-only with
the exact same environment, `-B` and external `cache_dir`; require no unexplained
nodeid deletion, and require the delta to equal only the new remediation test
nodeids.

### Step 9 — final audit and STOP

Recheck exact path set, `git diff --check`, raw SHA-256/blob for every changed/new
path, immutable hashes, archive/root state, HEAD/upstream/ahead-behind, index/staged
state, scoped untracked/ignored invariant, excluded counts and protected-prefix
contamination result. Report all required measures
from plan Task 9 and STOP.

Do not stage, commit, push or run `verify-commit`. Those require later separate user
authorization.

---

## 6. Fail-Closed STOP Conditions

Stop immediately without scope expansion when any of the following occurs:

1. directive/plan/spec/capsule/generator/tracked-worktree/invariant-scope/immutable
   hash mismatch;
2. capsule missing, expired, exit 2/3, non-exact identity or live-state mismatch;
3. HEAD/upstream/ahead-behind/index/tracked-worktree, scoped untracked/ignored
   content, excluded-count or protected-prefix contamination drift;
4. a required continuation path is missing or changes after capsule verify;
5. exact target set differs from 18 coordinates in 15 files;
6. predicate distribution differs from `EQ_0=13/EQ_1=4/LE_1=1`;
7. P2 current mapping differs from `12/14/15`, or any value outside 15 projections
   would need to change;
8. target semantics require changing any field beyond `action/command/expected`;
9. workbook/exporter/runner/schema/validator/v1 evidence changes would be required;
10. RED has the wrong cause, or GREEN would require weakening an existing test;
11. any of 15 validations, focused tests, determinism, contamination or full pytest
    is not GREEN;
12. a device, network, dependency, stage/commit/push or cleanup operation is needed;
13. executor/session restart or external repo mutation occurs after continuation verify;
14. a long process appears stalled: continue recurring yields and diagnose from new
    output, but do not kill/restart under this authorization.

On STOP, preserve all user assets and implementation evidence as-is, report the
exact failing command/exit/evidence and current Git state, and request a new bounded
decision. Do not reset, revert, restore or clean.

### 6.1 Long-process rule

Every process has an explicit timeout. No single wait/yield interval exceeds 50
seconds. A yielded process is resumed by its existing cell/process ID only. It is
never replaced with a duplicate run to obtain quicker feedback.

### 6.2 Reporting vocabulary

Use `validate PASS` only for `validate_tc.py`; use measured pytest counts for host
tests; call verifier exit 0 `host remediation gate GREEN`. Do not call any result
`runtime PASS`, because no device command is authorized.

### 6.3 External archive/root invariants

The final archive must remain present and unchanged:

```text
C:\tmp\tc-runner-provenance-archive\20260812-final
```

These two completed campaign roots must remain absent; do not recreate or delete
anything to force the check:

```text
C:\tmp\tc-runner-shell-rc-provenance-RB-20260728-shellrc-p0p1
C:\Users\momen\Projects\tc-runner\reports\canonical_shell_rc_provenance\RB-20260728-shellrc-p0p1
```

---

## 7. Completion Report Contract

Before requesting any publication gate, report in one self-contained response:

- final directive/spec/plan/capsule/evidence identities;
- full created/modified path list, classified as governance, implementation,
  current provenance and curated YAML;
- lowercase raw SHA-256 and `git hash-object --no-filters` for every path;
- initial RED command/count/cause and every GREEN command/count;
- exact 18/15 target set, predicate `13/4/1`, P2 `12/14/15` and inventory
  `692/692/18/674/74/6/0` measures;
- 15/15 `validate PASS` with no `runtime PASS` claim;
- two-run evidence byte hashes and content-addressed ignored output path;
- baseline/final pytest collection counts, focused passed count and full-suite result;
- immutable/hash and forbidden-path checks;
- final archive present, two completed campaign roots absent, no cleanup performed;
- HEAD/upstream/ahead-behind, tracked/staged set, scoped untracked/ignored map,
  excluded-count and protected-prefix contamination invariance;
- explicit statement that no stage, commit, push, device contact, campaign rerun,
  network/dependency operation or extra cleanup occurred.

Then STOP. A later Git publication relay, if requested, must use exact individual
stage paths, staged `--expected-path` audit before commit, an exact-set committed-tree
audit, non-force fast-forward push and post-push 0/0 verification. This directive
does not authorize any of those operations.
