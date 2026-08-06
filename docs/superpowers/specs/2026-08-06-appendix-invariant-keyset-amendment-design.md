# Appendix Invariant Key-set Amendment — Design + Implementation Record

- Date: 2026-08-06
- Target: `HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md`
- Prior identity: raw `109c2131be4df64c44f8b9e9fac3d0afb3afac27ed53d3b66d193db8b10bac92`
  / blob `49a0cec213e4663ea8a1f7e84c892afcfd134ee2`
- New identity: raw `b029b8905cf8fb4ccba4fe44370c7bb680e0ce7efcb9b73b9649881785aff069`
  / blob `56a6ced1d6519ba6bf53c5414c4c522e93fdaed8`
- Status: implemented; commit pending user approval

## 1. Defect (measured 2026-08-06)

`derive_appendix_hashes()` returns 4 keys (A/B/C/R) since the 62e68d5
module-route amendment added Appendix R to its loop. The ASSEMBLE
invariant compared it whole-dict against `appendix_actual` and
`appendix_arguments`, both 3-key dicts (A/B/C). Dict comparison with
differing key sets is unconditionally unequal, so
`invariant_problems.append("appendix source hashes")` fired on every run
regardless of values.

Reproduction: derive-repro against the pre-amendment directive yielded
A=`784fdeb7…`, B=`6ab74d52…`, C=`9af40ad1…`, R=`d57734b2…` — each equal
to its frozen pin individually; only the key set differed. Confirmed
live in the first ASSEMBLE-reaching run (RB-20260728-shellrc-p0p1,
evidence raw `c1b3e2ed92d2d38d7eb3588a0c5e404342eba1dc3b1622f4741382e61a57fcbf`,
verdict INPUT_INVALID with blocking reason `appendix source hashes` at
`post_state` despite byte-exact appendix materialization). Consequence:
any run reaching ASSEMBLE — including a fully successful P0/P1 — was
structurally forced to INPUT_INVALID (2).

## 2. Fix (Option 1 — 3-key restriction)

Inside the Appendix C fence, insert `appendix_expected` (A/B/C keys
projected from `appendix_derived`) and compare `appendix_arguments` /
`appendix_actual` against it. `derive_appendix_hashes()` unchanged — its
Appendix R heading/fence cardinality validation remains active.

Option 2 (bind R via a 4th `--appendix-r-sha` argv) was rejected: R is
already bound at §3 preflight (`module_route.probe_source_sha256`,
ledgered and present in evidence; measured working in the same run), so
ASSEMBLE re-binding adds diff surface with zero added integrity.

## 3. Edit sites (3, single file)

1. Appendix C fence: `appendix_expected` block inserted after
   `appendix_derived = derive_appendix_hashes()`; the two comparison
   operands swapped from `appendix_derived` to `appendix_expected`.
2. `--appendix-c-sha` argv pin → new C source SHA.
3. Appendix C `**Expected source SHA-256:**` → same new SHA.

New Appendix C source SHA-256:
`258c1c96739d782ef56040fb95fa390384752a75f9623d4a79ab07c99c72013e`

Diff: 12 insertions, 4 deletions, 1 file.

## 4. DoD results (all measured 2026-08-06)

- V1 fence edit only — derive-repro post-edit: A/B/R hashes unchanged.
- V2 new C SHA appears exactly at the 2 pins; pins byte-equal to
  recomputed value.
- V3 old C SHA `9af40ad1…` occurrences in directive: 0.
- V4 all other `appendix_derived` consumers are single-key lookups
  (`["appendix_a/b/c_source_sha256"]`); no whole-dict comparison remains.
- V5 invariant simulation: positive (byte-exact materialization +
  matching argv) does NOT fire; tampered-B fires; old logic demonstrably
  fired on the positive case (bug reproduced).
- V6 byte hygiene: UTF-8 no BOM, CRLF 0, trailing LF; `.gitattributes`
  `eol=lf` + `text` pins confirmed active for the directive.
- V7 pytest tests/: 1526 passed; 3 failures all explained and unrelated:
  - `test_current_head_inventory_matches_reviewed_target_set`:
    pre-existing drift — batch commit `3cafbf8` added 4 tracked YAMLs
    (docs/tc_templates_folder.yaml, docs/tc_templates_kids.yaml,
    tc_samples/folder_basic_nav.yaml, tc_samples/kids_basic_nav.yaml)
    without updating the literal 615 → live 619. Queued as its own
    slice; not part of this amendment.
  - 2× `test_provenance_module_binding_*`: environment chain — pwsh 7
    session PSModulePath (PS7 module dirs first) inherited through
    python `subprocess(env=os.environ.copy())` breaks Windows PowerShell
    5.1 module autoload (`Get-FileHash` unresolved). Positive control:
    with 5.1-default PSModulePath both tests pass unchanged against the
    amended directive (2 passed, 2.88s). Codex 5.1-native runs are
    unaffected.
- V8 new directive identity recorded above; dispatch blocks must use the
  new raw SHA from the next capsule onward (capsule measures it live).

## 5. Non-goals

No Appendix A/B/R fence changes; no EEXIST-related directive change (the
`fs.mkdir(WORK_ROOT, { recursive: false })` contract stands — controller
must not pre-create `artifact-tool-work`); no run-ID path restructure;
no probe-directive rev3; no CLAUDE.md edits; inventory-test literal fix
deferred to its own slice.
