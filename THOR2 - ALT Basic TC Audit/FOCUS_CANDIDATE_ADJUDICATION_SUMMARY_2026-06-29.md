# ALT Basic focus_candidate Adjudication Ledger — Summary
- focus_candidate steps adjudicated: 61  |  total TCs: 236

## Adjudication class counts (step-level)
- VERIFY_POINT_HIGH: 0  (step-level)
- NAVIGATE_TO_FOCUS: 61  (step-level)
- AMBIGUOUS_RETAIN: 0  (step-level)

## Eligibility (TC-level) — device-pilot eligibility unlock
*Eligibility = fail-closed blocker removal, NOT a runtime verdict.*
- baseline_eligible: 5  (TC-level)
- tier0_eligible: 6  (TC-level)
- verify_high_eligible: 6  (TC-level)
- all_candidate_eligible: 45  (TC-level, reference)

## Deltas (TC-level)
- **headline adjudicated_delta: 0** (no-device; high-confidence VERIFY_POINT_HIGH reclassification only)
- prior_focus_candidate_delta: 39  (reference upper bound = all 61 reclassified; the NOT_A_KEY ledger's +39)
- inflation avoided (prior − adjudicated): 39

## Retained as blockers (not reclassified no-device)
- NAVIGATE_TO_FOCUS: 61
- AMBIGUOUS_RETAIN: 0

*** STOP: host-only adjudication. No device, no reclassification committed. Await user decision on the high-confidence VERIFY_POINT_HIGH subset. ***
