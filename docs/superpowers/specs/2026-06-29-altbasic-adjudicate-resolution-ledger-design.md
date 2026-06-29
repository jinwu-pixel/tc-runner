# ALT Basic ADJUDICATE Resolution Ledger — Design (lean)

> Status: DRAFT (continuous-execution track; user-directed). Commit deferred to EOD batch per global §7.
> Date: 2026-06-29 · Track: THOR2 ALT Basic — throughput pivot, device-free measurement slice #4 (last no-device lever).
> Predecessors: [NOT_A_KEY subtype](2026-06-29-altbasic-not-a-key-subtype-ledger-design.md) (`39bb45e`), [focus_candidate adjudication](2026-06-29-altbasic-focus-candidate-adjudication-ledger-design.md), [entry_detail](2026-06-26-altbasic-entry-detail-ledger-design.md) (`b9e1bd2`).

## 1. Goal & context

The subtype cascade found `adjudication_delta` = **+18** (TCs that become device-pilot eligible if every
`ADJUDICATE` step is resolved). `ADJUDICATE` (53 steps / 46 TCs) is disjunction/qualified-key intent choice
("네비키 또는 OK키", "Navi 키(↓)", "Navi 키(전체)"). Unlike `focus_candidate` (which proved 100% navigation,
adjudicated_delta 0), many ADJUDICATE steps name a determinable key. This ledger adjudicates them into 3 classes
and reports the **defensible high-confidence delta** separately from the disjunction (intent-choice) potential
and the prior +18.

This is the **last no-device lever** (the subtype ledger proved no-device NOT_A_KEY throughput ≈ 0:
focus_state +1, focus_candidate +0, screen_present 0). Host-only, measurement only.

## 2. Non-goals
No yaml/manifest/runner mutation; predecessors imported not forked; no device/catalog/wall-clock/network; no
reclassification committed (STOP at report); no `PASS`/`RUNNABLE_NOW`/`validated` in summary (denylist + test).

## 3. Taxonomy (3 classes, fail-closed)

For each step whose predecessor disposition is `ADJUDICATE`:

| Class | Rule | Cascade role |
|---|---|---|
| **RESOLVABLE_HIGH** | exactly one determinable key — a single explicit direction (arrow glyph `↑↓←→` or text up/down/left/right / 상하좌우 / 위·아래) **or** an OK/center reference — **and no disjunction marker** (`또는`/`나`(키나)/`/`) and no ambiguity marker | resolved (no-device decision) → **headline** |
| **DISJUNCTION_CHOICE** | a disjunction marker offers alternatives (`네비키 또는 OK키`, `Press back 또는 cancel`, `네비키나 OK키`) — resolvable only by an intent decision (which branch) | medium potential, **not headline** |
| **AMBIGUOUS_RETAIN** | `전체`/`모든`/`all`/`아무`/`any`, or ≥2 distinct explicit directions | fail-closed blocker |

Precedence: ambiguity marker → AMBIGUOUS_RETAIN first; else disjunction marker → DISJUNCTION_CHOICE; else
single determinable key → RESOLVABLE_HIGH; else (no key, has disjunction) → DISJUNCTION_CHOICE.

### 3.1 direction/OK detection
`↑`/up/상/위→UP(19), `↓`/down/하/아래→DOWN(20), `←`/left/좌/왼→LEFT(21), `→`/right/우/오른→RIGHT(22),
ok/확인/center/가운데→OK(23). Arrow glyphs matched on the raw body; text on the compact casefold. ≥2 distinct
direction codes ⇒ AMBIGUOUS. Pinned by golden.

## 4. Cascade

Reuse predecessor `build` chain; for `ADJUDICATE`-disposition steps emit one of
`R_ADJ_HIGH` / `R_ADJ_DISJ` / `R_ADJ_AMBIG` (replacing `R_ADJUDICATE`). Scenarios on top of `tier0` (focus_state
reclassified; resolved steps go to `to_resolved`, they are key presses not verifiers):

| Scenario | to_resolved adds | Metric |
|---|---|---|
| `tier0` | — | `tier0_eligible` (==6) |
| `tier0_adj_high` | `R_ADJ_HIGH` | `adj_high_eligible`; **`adjudicated_delta` = adj_high − tier0 (HEADLINE)** |
| `tier0_adj_high_disj` | `R_ADJ_HIGH, R_ADJ_DISJ` | `disjunction_delta` = high_disj − adj_high (medium) |
| `tier0_all_adjudicate` | all 3 | `prior_adjudicate_delta` = all − tier0 (== **+18** reference) |

Headline = `adjudicated_delta` (RESOLVABLE_HIGH only). DISJUNCTION = separate medium potential. AMBIGUOUS never resolves.

## 5. Outputs
`scripts/altbasic_adjudicate_resolution_ledger.py` (imports focus_candidate ledger module → predecessor chain) +
test + golden + artifacts `THOR2 - ALT Basic TC Audit/ADJUDICATE_RESOLUTION_{LEDGER,CASCADE}_2026-06-29.csv` + `_SUMMARY_2026-06-29.md`.

## 6. Self-checks
ADJUDICATE input steps == **53**; baseline==5; tier0==6; `prior_adjudicate_delta` == **+18** (reproduce subtype
ledger or STOP+reconcile); class counts sum == 53; summary forbidden==0; predecessor tests green.

## 7. Invariants
1. Headline = RESOLVABLE_HIGH delta only; +18 is reference; DISJUNCTION separate medium.
2. AMBIGUOUS never unlocks (fail-closed).
3. Predecessors imported not forked; baseline 5 / tier0 6 / prior +18 reproduced.
4. Eligibility = device-pilot eligibility, not PASS/RUNNABLE_NOW/validated.
