# ALT Basic focus_candidate Adjudication Ledger — Design

> Status: DRAFT (continuous-execution track; user gave standing approval to proceed through to the measurement STOP). Commit deferred to EOD batch per global §7.
> Date: 2026-06-29
> Track: THOR2 ALT Basic TC Audit — throughput pivot, device-free measurement slice #3.
> Predecessors: [NOT_A_KEY subtype ledger](2026-06-29-altbasic-not-a-key-subtype-ledger-design.md) (committed `39bb45e`), [entry_detail ledger](2026-06-26-altbasic-entry-detail-ledger-design.md) (`b9e1bd2`).
> Handoff: `THOR2 - ALT Basic TC Audit/HANDOFF_FOCUS_CANDIDATE_2026-06-29.md`.

---

## 1. Goal

The NOT_A_KEY subtype ledger found **61 `VERIFIER_FOCUS_CANDIDATE` steps** and a **+39** TC-level
`focus_candidate_delta` — but that delta optimistically assumed *all 61* bare-`X focus` steps are
device-free verifier reclassifications. This ledger adjudicates the 61 against real manifest context
(`verifier_candidates` + step position) into 3 classes and reports the **defensible high-confidence
adjudicated delta**, separating it from the inflated +39.

**The headline is the adjudicated high-confidence delta, NOT +39.** +39 is reported only as the
prior optimistic upper bound for this subtype.

## 2. Data-grounded finding (the reason for this track)

The bulk of the 61 are Quick-Panel (QPN) directional-navigation steps:

```
entry_detail        : press_key:wifi focus > Press down
verifier_candidates : literal: 모바일 데이터
title               : 확장 퀵패널 Wi-Fi 하 방향키 — 모바일 데이터 Focus 확인
```

Here `wifi focus` is the **starting position**; a directional key then moves focus, and the *verified
outcome* is a different element (`모바일 데이터`). So the focus_candidate step is **navigation/positioning**,
not a verify-point. Reclassifying it to a no-device verifier would be wrong — it is a device-positioned
precondition. This is exactly the "+39 must not be claimed as automatic unlock" caution.

## 3. Non-goals

- **No yaml / manifest / runner mutation.** New read-only analyzer only.
- **No edit to predecessor modules** (`altbasic_not_a_key_subtype_ledger.py`, `altbasic_entry_detail_ledger.py`); imported, not forked. Their tests stay green.
- **No device, no catalog, no wall-clock, no network.**
- **No reclassification committed.** Adjudication only; STOP at the measurement report; await user decision on the high-confidence subset.
- **No `PASS` / `RUNNABLE_NOW` / `validated`** in the generated summary (denylist + test). Eligibility = fail-closed blocker removal, not a runtime verdict.

## 4. Adjudication taxonomy (3 classes, fail-closed)

For each `VERIFIER_FOCUS_CANDIDATE` step at index *i* within its TC's parsed entry steps:

| # | Class | Rule | Cascade role |
|---|---|---|---|
| 1 | **NAVIGATE_TO_FOCUS** | there is **any later executable step** after *i* (any key/navigation/tap/input/focus action) — the focus at *i* is a position the TC then acts *from* | device positioning → stays an executable blocker (NOT reclassified no-device) |
| 2 | **VERIFY_POINT_HIGH** | *i* is **terminal** (no later executable step; only observe/literal or nothing follows) **AND** the focus target literal is contained in the TC's `verifier_candidates` (normalized contains-match) | high-confidence verifier → reclassify to non-exec (the only no-device unlock) |
| 3 | **AMBIGUOUS_RETAIN** | terminal but target ∉ `verifier_candidates`, or structure undeterminable | fail-closed blocker; await user/device evidence |

Precedence: rule 1 (navigate) is checked first — if **any executable step** follows, the focus is a
position acted upon, regardless of any verifier match. Only a terminal focus step can be VERIFY_POINT_HIGH.
This is deliberately strict: a focus that is the verified *end state* has nothing acting after it.

### 4.1 "later executable step" definition

A later step (index > *i*) counts if the predecessor `classify_step(step)["executable"]` is `True` — i.e.
any key/navigation/tap/input/focus action (directional, OK, back/cancel, long-press, tap, another focus).
Non-executable observe tokens and literals (`executable == False`) do **not** count. This catches the QPN
`X focus > Press back 또는 cancel` case (back/cancel is executable even though it classifies ADJUDICATE),
preventing a false VERIFY_POINT promotion. Pinned by golden fixtures.

### 4.2 verifier_candidates contains-match

Normalize both the focus target and the `verifier_candidates` text (strip `literal:` prefix, lowercase
ASCII, compact whitespace) and test substring containment in either direction on the core token (e.g.
`wifi`/`wi-fi` ↔ `wifi`). Korean tokens compared on the compact form. Pinned by golden.

## 5. Eligibility cascade (re-derivation)

Reuse the predecessor's `build` (620-step `tc_steps`) and subtype rows. Split the
`VERIFIER_FOCUS_CANDIDATE` requirement (`R_VFOCUS_CAND`) per step into one of three adjudicated
requirements: `R_VERIFY_HIGH` / `R_NAV_FOCUS` / `R_AMBIG_FOCUS`.

Scenarios (each on top of `tier0` = focus_state already reclassified, the prior committed baseline):

| Scenario | Resolves (→ nonexec) | Metric |
|---|---|---|
| `tier0` | focus_state | `tier0_eligible` (== prior 6) |
| `tier0_verify_high` | tier0 + `R_VERIFY_HIGH` → nonexec | `verify_high_eligible`, **`adjudicated_delta` = verify_high − tier0** ← HEADLINE |
| `tier0_all_candidate` (reference) | tier0 + all 3 focus_candidate classes → nonexec | `all_candidate_eligible`; `prior_focus_candidate_delta` = all_candidate − tier0 (should reproduce **+39**) |

`adjudicated_delta` is the defensible no-device number. `prior_focus_candidate_delta` (≈ +39) is the
optimistic upper bound, reported beside it so the inflation `(39 − adjudicated_delta)` is explicit.
`NAVIGATE_TO_FOCUS` / `AMBIGUOUS_RETAIN` never resolve no-device.

## 6. Outputs

| File | Content |
|---|---|
| `scripts/altbasic_focus_candidate_adjudication_ledger.py` (create) | imports predecessor; pure `adjudicate_focus_candidate(steps, i, verifier_candidates)`, cascade re-derive, summarize; IO/CLI |
| `tests/test_altbasic_focus_candidate_adjudication_ledger.py` (create) | per-rule + cascade + golden + forbidden-word + real-manifest self-checks |
| `tests/fixtures/altbasic/focus_candidate_adjudication_golden.json` (create) | curated fixture covering all 3 classes + the QPN navigate pattern + a terminal verify-point |
| `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_LEDGER_2026-06-29.csv` | 61 rows: tc_id, token, adjudication_class, rationale, verifier_candidates, position_info, required_decision |
| `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_CASCADE_2026-06-29.csv` | per-TC scenario booleans |
| `THOR2 - ALT Basic TC Audit/FOCUS_CANDIDATE_ADJUDICATION_SUMMARY_2026-06-29.md` | 3-class counts + adjudicated_delta (headline) + prior +39 reference + inflation + remaining + STOP |

## 7. Verification / self-consistency

- focus_candidate input rows == **61**.
- predecessor `baseline_eligible` == **5**, `tier0_eligible` == **6** (reproduced).
- `prior_focus_candidate_delta` == **+39** (reproduces the NOT_A_KEY ledger's `focus_candidate_delta`, or STOP + reconcile).
- 3-class counts sum to 61.
- summary contains no `PASS`/`RUNNABLE_NOW`/`validated`.
- predecessor + subtype ledger tests stay green; `tests/` full run.

## 8. STOP

Host-only. No reclassification committed. Report 3-class distribution + adjudicated_delta vs +39, then STOP
for user decision: (A) high-confidence subset reclassification spec/plan, (B) ambiguous review, (C) move to
selector/keycode device discovery.

## 9. Core invariants

1. Headline = `adjudicated_delta` (high-confidence VERIFY_POINT only); **+39 is reference upper bound, never the headline**.
2. NAVIGATE_TO_FOCUS / AMBIGUOUS_RETAIN never unlock no-device (fail-closed).
3. Grounded in real `verifier_candidates` + step position — not token-only promotion.
4. Predecessors imported, not forked; baseline 5 / tier0 6 / prior +39 reproduced.
5. Eligibility = device-pilot eligibility (blocker removal), not PASS/RUNNABLE_NOW/validated.
