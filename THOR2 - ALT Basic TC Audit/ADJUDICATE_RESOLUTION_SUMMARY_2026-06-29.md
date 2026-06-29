# ALT Basic ADJUDICATE Resolution Ledger — Summary
- ADJUDICATE steps adjudicated: 53  |  total TCs: 236

## Adjudication class counts (step-level)
- RESOLVABLE_HIGH: 24  (step-level)
- DISJUNCTION_CHOICE: 25  (step-level)
- AMBIGUOUS_RETAIN: 4  (step-level)

## Eligibility (TC-level) — device-pilot eligibility unlock
*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*
- baseline_eligible: 5  (TC-level)
- tier0_eligible: 6  (TC-level)
- tier0_adj_high_eligible: 17  (TC-level)
- tier0_adj_high_disj_eligible: 20  (TC-level)
- tier0_all_adjudicate_eligible: 24  (TC-level)

## Deltas (TC-level)
- **headline adjudicated_delta: 11** (no-device; RESOLVABLE_HIGH single-determinable-key only)
- disjunction_delta: 3  (medium; either/or intent-choice steps, not headline)
- prior_adjudicate_delta: 18  (reference upper bound = all ADJUDICATE resolved; the subtype ledger's +18)
- ambiguous_retained (step-level, never unlocks): 4

*** STOP: host-only adjudication. No device, no reclassification committed. Await user decision on the RESOLVABLE_HIGH / DISJUNCTION_CHOICE subsets. ***
