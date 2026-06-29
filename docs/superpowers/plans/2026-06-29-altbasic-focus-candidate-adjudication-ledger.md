# ALT Basic focus_candidate Adjudication Ledger — Implementation Plan (condensed)

> REQUIRED SUB-SKILL: executing-plans (inline, continuous). Refinement track reusing the predecessor
> `altbasic_not_a_key_subtype_ledger` architecture — condensed plan (not full bite-sized), host-TDD.

**Goal:** Adjudicate the 61 `VERIFIER_FOCUS_CANDIDATE` steps into 3 classes
(`VERIFY_POINT_HIGH` / `NAVIGATE_TO_FOCUS` / `AMBIGUOUS_RETAIN`) grounded in manifest
`verifier_candidates` + step position, and report the defensible `adjudicated_delta` vs the prior +39.

**Spec:** [docs/superpowers/specs/2026-06-29-altbasic-focus-candidate-adjudication-ledger-design.md](../specs/2026-06-29-altbasic-focus-candidate-adjudication-ledger-design.md)

**Commit policy:** no per-task commit; suite GREEN checkpoints; EOD batch on explicit approval only.

---

## Files
- Create: `scripts/altbasic_focus_candidate_adjudication_ledger.py` (imports predecessor subtype ledger via importlib + sys.modules registration)
- Create: `tests/test_altbasic_focus_candidate_adjudication_ledger.py`
- Create: `tests/fixtures/altbasic/focus_candidate_adjudication_golden.json`
- Artifacts: `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_{LEDGER,CASCADE}_2026-06-29.csv` + `_SUMMARY_2026-06-29.md`

## Tasks (host-TDD; RED → GREEN each)

### T1 — scaffold + import predecessor subtype ledger
- importlib load `altbasic_not_a_key_subtype_ledger` (register in `sys.modules` BEFORE exec — dataclass).
- re-export needed primitives: `parse_entry_detail`, `classify_step`, `subclassify_not_a_key`, `resolution_requirement`, `blocker_reason`, `load_manifest`, `normalize_body`, `_compact`, `VERIFIER_FOCUS_CANDIDATE`, `scenario_eligible`, `R_*`, `SCENARIOS`, `NOT_A_KEY`.
- new constants: `R_VERIFY_HIGH="VERIFY_POINT_HIGH"`, `R_NAV_FOCUS="NAVIGATE_TO_FOCUS"`, `R_AMBIG_FOCUS="AMBIGUOUS_RETAIN"`.
- Test: import works, constants present.

### T2 — `_later_executable(steps, i)` + `_vc_match(target, verifier_candidates)`
- `_later_executable`: any step at index > i with `classify_step(step)["executable"] is True`.
- `_vc_match`: strip `literal:` from vc, compact+casefold both; strip focus words (`focus`/`포커싱`/`포커스`/`에`/`아이콘`) from target core; return `core and core in vc_compact`.
- Tests: `wifi focus` vs `literal: 모바일 데이터` → False; `wifi focus` vs `퀵패널 / 알림창 / wifi` → True; later-exec True when a directional/back follows, False when only observe/terminal.

### T3 — `adjudicate_focus_candidate(steps, i, verifier_candidates) -> dict`
- precedence: later-executable → NAVIGATE_TO_FOCUS; else vc-match → VERIFY_POINT_HIGH; else AMBIGUOUS_RETAIN.
- returns: `adjudication_class`, `resolution_requirement` (R_NAV_FOCUS / R_VERIFY_HIGH / R_AMBIG_FOCUS), `rationale`, `position_info` (e.g. `terminal` / `exec_after`), `required_decision`.
- Tests: QPN `wifi focus > Press down` → NAVIGATE; terminal `X focus` with vc-match → VERIFY_POINT_HIGH; terminal no vc-match → AMBIGUOUS; QPN_142 `wifi focus > Press back 또는 cancel` → NAVIGATE (exec-after wins).

### T4 — `build(manifest_rows)` → (adj_rows[61], tc_steps)
- per TC: parse steps; for each step, predecessor `classify_step`; if NOT_A_KEY → `subclassify_not_a_key`.
- if subtype == VERIFIER_FOCUS_CANDIDATE → `adjudicate_focus_candidate(steps, i, verifier_candidates)`; emit adj_row; requirement = the adjudicated R_*.
- else requirement = predecessor `resolution_requirement`.
- empty entry → single NONEXEC (mirror predecessor).
- Tests: adj_rows length == focus_candidate count; per-class requirement mapping.

### T5 — cascade + `summarize` (adjudicated_delta headline + prior +39 reference)
- Extend scenario set: `tier0_verify_high` = tier0 `to_nonexec` ∪ {R_VERIFY_HIGH}; `tier0_all_candidate` = tier0 ∪ {R_VERIFY_HIGH, R_NAV_FOCUS, R_AMBIG_FOCUS}.
- reuse predecessor `scenario_eligible`. baseline/tier0 reuse predecessor SCENARIOS.
- metrics: `baseline_eligible`(==5), `tier0_eligible`(==6), `verify_high_eligible`, **`adjudicated_delta`=verify_high−tier0 (HEADLINE)**, `all_candidate_eligible`, `prior_focus_candidate_delta`=all_candidate−tier0 (==+39), `inflation`=prior−adjudicated, 3-class counts, remaining (NAV/AMBIG retained).
- Tests over a mini manifest: class counts, adjudicated_delta, prior delta.

### T6 — IO writers + forbidden guard (reuse predecessor `assert_no_forbidden`)
- adjudication ledger CSV (61), cascade CSV (per TC scenario booleans), summary MD (labels, headline=adjudicated_delta, +39 as reference, STOP banner, no PASS/RUNNABLE_NOW/validated).
- Tests: roundtrip + forbidden-word.

### T7 — golden fixture + golden test
- curated manifest fixture: QPN navigate (`wifi focus > Press down`, vc=모바일 데이터), QPN_142-style (`wifi focus > Press back 또는 cancel`, vc=…wifi → still NAVIGATE), a terminal verify-point (`X focus`, vc=X), a terminal non-match (AMBIGUOUS). Assert class counts + cascade deltas.

### T8 — main/CLI + real-manifest self-checks
- defaults: predecessor `DEFAULT_MANIFEST`, artifact paths in audit folder.
- Tests on real manifest: focus_candidate rows == **61**, baseline==5, tier0==6, prior_focus_candidate_delta==**+39** (or STOP+reconcile), 3-class sum == 61, summary forbidden==0.

### T9 — generate artifacts + measurement STOP report
- run script; eyeball summary (adjudicated_delta vs +39, inflation, 3-class); report; STOP (no yaml mutation).

## Self-checks
focus_candidate==61 · baseline==5 · tier0==6 · prior delta==+39 reproduced · 3-class sum==61 · predecessor+subtype tests green · forbidden==0 · no device/yaml/manifest mutation.
