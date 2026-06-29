# ALT Basic NOT_A_KEY Subtype Ledger — Summary
- total TCs: 236  |  NOT_A_KEY steps: 189
- self_check=ok (baseline_eligible vs predecessor headline)

## NOT_A_KEY subtype counts (step-level)
- VERIFIER_FOCUS_STATE: 8  (step-level)
- VERIFIER_FOCUS_CANDIDATE: 61  (step-level)
- VERIFIER_SCREEN_PRESENT: 20  (step-level)
- MANUAL_RETAIN: 2  (step-level)
- KEYCODE_DISCOVERY: 6  (step-level)
- SELECTOR_DISCOVERY: 92  (step-level)

## Eligibility cascade (TC-level) — device-pilot eligibility unlock
*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*
- baseline_eligible: 5  (TC-level)
- tier0_eligible: 6  (TC-level)
- tier1_eligible: 52  (TC-level)
- tier2_eligible: 80  (TC-level)
- tier0_screen_eligible: 6  (TC-level)
- tier0_focus_candidate_eligible: 45  (TC-level)
- tier0_adjudicate_eligible: 24  (TC-level)
- optimistic_upper_bound_eligible: 173  (TC-level)

## Deltas (TC-level)
- **headline_now_unlock = tier0_delta: 1** (no-device; high-confidence focus-state verifier reclassification only)
- selector_delta: 46  (potential, not headline)
- keycode_delta: 28  (potential, not headline)
- screen_present_delta: 0  (potential, not headline)
- focus_candidate_delta: 39  (potential, not headline)
- adjudication_delta: 18  (potential, not headline)

## Remaining blocked (at optimistic upper bound, by dominant reason)
- AMBIGUOUS: 42
- FREE_TEXT_MANIFEST: 18
- MANUAL_RETAIN: 2
- OTHER: 1

*** STOP: host-only measurement. No device, no reclassification committed. Await user decision on which subtypes to action. ***
