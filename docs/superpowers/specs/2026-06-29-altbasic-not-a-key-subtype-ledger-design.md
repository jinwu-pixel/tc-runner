# ALT Basic NOT_A_KEY Subtype Ledger + Eligibility Cascade — Design

> Status: DRAFT (brainstorming output, awaiting user spec review). Commit deferred to end-of-day batch per global §7 / project §7.1 (draft = no immediate commit).
> Date: 2026-06-29
> Track: THOR2 ALT Basic TC Audit — throughput pivot, device-free measurement slice #2.
> Predecessor: [2026-06-26 entry_detail Normalization Ledger](2026-06-26-altbasic-entry-detail-ledger-design.md) (committed `b9e1bd2`).

---

## 1. Goal

The predecessor ledger measured that, of 620 `entry_detail` steps across 236 batch10 TCs, the **NOT_A_KEY tier
holds 189 steps** (the single largest tier) and that directional key normalization alone unlocks only **5 TCs**
at the TC level — because most TCs are blocked by *other* non-resolvable steps (fail-closed eligibility). The
predecessor's own conclusion: the real mass is **NOT_A_KEY 189 reclassification + FREE_TEXT 158 discovery**, not
the directional resolver.

This spec refines the **189 NOT_A_KEY steps** into **actionability subtypes** and re-derives, *defensibly*, how
many TCs each subtype would unlock for device-pilot eligibility — computed over the **full 620-step cascade** so
the numbers account for every co-occurring blocker in a TC.

This is a **measure-first, device-free** track. It answers "if we reclassify the NOT_A_KEY steps, how much
device-pilot eligibility do we actually unlock — and how much of that needs no device at all?" before any
canonical-yaml / manifest / runner change is made.

### Why this track exists

`NOT_A_KEY` (189) is a single coarse bucket: steps tagged `press_key`/bare whose body is *not a key* — a
screen/focus/state reference (80) or a bare noun mis-tagged as a key (109). "Reclassify them" is not one action:
some become **verifiers** (drop out of the executable eligibility denominator with **no device**), some become
**tap/navigate targets** needing device **selector discovery**, some need device **keycode discovery**, and some
are genuinely **manual**. Only the first kind moves the throughput needle without a device window. This ledger
separates the four so the next track is chosen on evidence, not on the 189 headline.

## 2. Non-goals (explicit boundaries)

- **No existing pipeline/yaml/manifest mutation; new read-only analyzer only.** The canonical STAGE1 yaml, `validate_tc.py`, the batch10 manifest, and the
  thor2j device driver are untouched. The only new code is the read-only ledger generator (§8).
- **No edit to the predecessor ledger** (`scripts/altbasic_entry_detail_ledger.py`, its test, its golden). It is
  **imported** and reused, so its 39 tests stay green and there is zero classifier drift.
- **No device contact.** Host-only, fully reproducible, no wall-clock / network dependence.
- **No actual reclassification.** Steps are *flagged* with a proposed subtype + `required_decision`; nothing is
  rewritten. The output is a ledger + summary; the track then **STOPs** and awaits user decision on which
  subtypes to action.
- **No catalog lookup.** The classifier is deterministic and self-contained (no `menu_tree`/golden coupling), so a
  frozen golden fixture pins its output. Catalog cross-checks (e.g. confirming a screen-present label exists) are a
  separate manual follow-up, not baked into the classifier.
- **A Tier0 eligibility unlock is NOT a `PASS`, NOT `RUNNABLE_NOW`, NOT `validated`.** It means a fail-closed
  *blocker has been removed* so the TC *could* enter the device-pilot flow. Those three words are a forbidden
  denylist enforced by a test over the generated summary (§7.1).

## 3. NOT_A_KEY subtype taxonomy (6 subtypes, fail-closed)

Applied **only to the 189 NOT_A_KEY rows** (rows the predecessor classified as `NOT_A_KEY`). The user's original
4-way framing (verifier / selector / keycode / manual) is refined here: **"verifier" splits into three** by
confidence (focus-state high / focus-candidate medium / screen-present medium) per the spec-review lock-ins, so
the headline stays defensible. Deterministic precedence, top-to-bottom — the first matching rule wins (5 ordered
rules + a conservative default):

| # | Subtype | Signal (on normalized body / original body) | Examples | Cascade role |
|---|---|---|---|---|
| 1 | **VERIFIER_FOCUS_STATE** | focus token (`focus`/`포커싱`/`포커스`) **AND** an explicit state/observe marker (`상태`/`위치`/`된`/`되어`/`되지`/`확인`/observe-regex) | `앱 서랍 포커스 되지 않은 상태`, `스크롤 마지막 앱에 포커스 위치` | **Tier0** (high) → non-exec verifier |
| 2 | **VERIFIER_FOCUS_CANDIDATE** | focus token **without** a state/observe marker (move-to-focus vs verify-focus ambiguous) | `wifi focus`, `새 연락처 만들기 focus`, `모바일 데이터 focus`, `전원 버튼 focus` | medium (separate `focus_candidate` potential, **not** Tier0) |
| 3 | **VERIFIER_SCREEN_PRESENT** | no focus token, but a screen/state marker (`화면`/`페이지`/`진입`/`스크린`/`screen`/`상태`) | `간편 설정 페이지`, `홈화면`, `앱서랍 진입` | medium (separate `screen_present` potential, **not** Tier0) |
| 4 | **MANUAL_RETAIN** | truncated (ends with a dangling conjunction `및`/`와`/`과`/`및 ` with no object) OR sensitive (`긴급`/`emergency`) OR un-actionable vague phrase | `언어 및`, `긴급 전화` | blocker (never unlocks) |
| 5 | **KEYCODE_DISCOVERY** | hardware-key reference: `버튼`/`키` with a press modifier (`롱`/`길게`/`짧게`) OR a navigation/hardware-key word the predecessor's key dictionary did not map (`뒤로가기` etc. — conservative: device-confirm the keycode rather than guess) | `해당 버튼을 짧게`, `하드키 즐겨 찾기 버튼 롱`, `뒤로가기` | **Tier2** → device keycode discovery |
| 6 | **SELECTOR_DISCOVERY** (default) | none of the above: explicit `Tap`/`탭` in the original body, OR a bare UI-label noun | `사진`, `시계`, `더보기`, `펼치기 Tap`, `실시간 자막 Tap` | **Tier1** → device selector discovery |

The exact marker/vocabulary tokens (state markers, press modifiers, conjunctions) are pinned by the golden fixture
and refined test-first in the plan; this section fixes the **rules and precedence**, not every token.

### 3.1 Precedence rationale (the defensible core)

- **focus + state marker > bare focus** (rules 1 vs 2): `전원 버튼 focus` → FOCUS_CANDIDATE (focus wins over the
  `버튼` keycode signal — it is describing a focus position, not a key press), but it lacks a state marker so it is
  **candidate, not Tier0**. Only an explicit state/observe phrase earns Tier0.
- **focus/screen verifier > manual/keycode/selector** (rules 1–3 before 4–5): a state description is a verifier
  regardless of nouns it contains.
- **manual before keycode/selector** (rule 4 before 5): a truncated or sensitive phrase must not be optimistically
  promoted to a discoverable target.
- **selector is the conservative default** (last): a bare noun with no other signal is treated as a tap target
  needing device selector discovery — executable, never silently dropped.

### 3.2 Fail-closed for ambiguous focus (user lock-in)

Rule 2 (`VERIFIER_FOCUS_CANDIDATE`) is the fail-closed catch for the move-to-focus vs verify-focus-state
ambiguity. A bare `X focus` is **not** assumed to be a verifier. It is recorded with
`required_decision = focus_intent_decision` and counted only in the separate `focus_candidate` potential — never
in the Tier0 headline. (NOTE for the summary: batch10 T1 already reclassified several focus-toggle steps to
`focus_state` verifiers in `48f6529`; this ledger is deliberately *more* conservative, so `focus_candidate` may
under-count true verifiers. That is the intended direction of the error — defensible headline over inflated one.)

## 4. Resolution-requirement mapping (all 620 steps)

For the eligibility cascade to be honest, **every** step in a TC — not just its NOT_A_KEY steps — is mapped to a
single `resolution_requirement`, drawing the NOT_A_KEY subtypes (§3) together with the predecessor's existing
dispositions/`required_decision`:

| `resolution_requirement` | Source steps |
|---|---|
| `RESOLVED` | predecessor `NOW_RESOLVABLE` |
| `VERIFIER_FOCUS` | NOT_A_KEY subtype `VERIFIER_FOCUS_STATE` |
| `VERIFIER_FOCUS_CANDIDATE` | NOT_A_KEY subtype `VERIFIER_FOCUS_CANDIDATE` |
| `VERIFIER_SCREEN` | NOT_A_KEY subtype `VERIFIER_SCREEN_PRESENT` |
| `SELECTOR` | NOT_A_KEY subtype `SELECTOR_DISCOVERY` **+** predecessor FREE_TEXT with `required_decision=device_selector_discovery` |
| `KEYCODE` | NOT_A_KEY subtype `KEYCODE_DISCOVERY` **+** predecessor FREE_TEXT with `required_decision=device_keycode_discovery` |
| `ADJUDICATE` | predecessor `ADJUDICATE` |
| `BLOCKER` | predecessor `AMBIGUOUS_NOGUESS` **+** NOT_A_KEY subtype `MANUAL_RETAIN` **+** predecessor FREE_TEXT `manifest_rewrite`/empty |
| `NONEXEC` | predecessor non-executable observe tokens (already excluded from denominator) |

This is the crux: a TC with a NOT_A_KEY focus step **and** a FREE_TEXT selector step is `VERIFIER_FOCUS` +
`SELECTOR`. It does **not** unlock at Tier0 (the selector step still blocks) — it unlocks only at Tier1. Pulling
in the FREE_TEXT selector/keycode steps keeps the cascade from over-crediting Tier0.

## 5. Eligibility cascade (scenarios + metric naming)

### 5.1 Eligibility predicate (unchanged from predecessor §5.1, fail-closed)

A TC is `eligible` under a scenario iff: it has **≥1 executable step** AND **every executable step is
scenario-resolved**. `NONEXEC` steps are excluded from the denominator. A scenario "resolves" a set of
`resolution_requirement` values (treats those steps as satisfied: verifier requirements become NONEXEC;
selector/keycode requirements become RESOLVED-equivalent).

### 5.2 Primary cascade (ordered, cumulative)

| Scenario | Resolves (in addition to baseline RESOLVED) | Metric key |
|---|---|---|
| `baseline` | nothing | `baseline_eligible` |
| `tier0` | `VERIFIER_FOCUS` → NONEXEC | `tier0_eligible`, `tier0_delta` = tier0−baseline |
| `tier1` | tier0 + `SELECTOR` → RESOLVED | `tier1_eligible`, `selector_delta` = tier1−tier0 |
| `tier2` | tier1 + `KEYCODE` → RESOLVED | `tier2_eligible`, `keycode_delta` = tier2−tier1 |

`baseline_eligible` **must reproduce the predecessor's `headline_resolvable_count` = 5** (self-consistency check).

### 5.3 Separate one-off potentials (each measured off `tier0`, NOT cumulative)

| Scenario | Resolves | Metric key |
|---|---|---|
| `tier0 + screen` | tier0 + `VERIFIER_SCREEN` → NONEXEC | `screen_present_delta` |
| `tier0 + focus_candidate` | tier0 + `VERIFIER_FOCUS_CANDIDATE` → NONEXEC | `focus_candidate_delta` |
| `tier0 + adjudicate` | tier0 + `ADJUDICATE` → RESOLVED | `adjudication_delta` |
| `optimistic_upper_bound` | resolve everything except `BLOCKER` | `upper_bound_eligible` |

`BLOCKER` (AMBIGUOUS + MANUAL_RETAIN + manifest-rewrite) never resolves in any scenario.

### 5.4 Headline (the one defensible no-device number)

**`headline_now_unlock = tier0_delta`** — TCs that become device-pilot *eligible* with **only** high-confidence
focus-state verifier reclassification, **no device required**. Everything else (`selector_delta`,
`keycode_delta`, `screen_present_delta`, `focus_candidate_delta`, `adjudication_delta`) is reported as labelled
*potential*, not headline.

### 5.5 Vocabulary rule (forbidden denylist)

Report titles/tables use **"device-pilot eligibility unlock (fail-closed blocker removal)"**. Internal metric keys
use `*_eligible` / `*_delta`. The tokens **`PASS`, `RUNNABLE_NOW`, `validated`** must not appear in the
**generated summary** — enforced by a test (§9). (The subtype/cascade CSVs are *not* scanned: they preserve
`original_entry_detail` raw text for provenance, so a forced scan there would conflict with audit fidelity.)

## 6. Ledger schema

Two related outputs.

### 6.1 Subtype ledger CSV — one row per NOT_A_KEY step (189 rows)

| Column | Meaning |
|---|---|
| `tc_id` | e.g. `ALTBASIC_BSC_014` |
| `source_file` | provenance (xlsx) |
| `original_entry_detail` | full unmodified string |
| `extracted_token` | the NOT_A_KEY step body this row classifies |
| `not_a_key_subtype` | one of the 6 subtypes (§3) |
| `confidence` | `high` (FOCUS_STATE) / `medium` (FOCUS_CANDIDATE, SCREEN_PRESENT) / `low` (SELECTOR, KEYCODE, MANUAL_RETAIN) |
| `proposed_action` | e.g. `verifier:focus_state`, `verifier:screen_present`, `tap:<selector>`, `press_key:<keycode-discovery>`, `(manual)` |
| `resolution_requirement` | the §4 enum value for this step |
| `rationale` | which signal matched (names the marker) |
| `required_decision` | `focus_intent_decision` / `screen_verifier_decision` / `device_selector_discovery` / `device_keycode_discovery` / `manual_review` |

### 6.2 Full-cascade rows (optional, for audit) — one row per TC

`tc_id`, the multiset of its `resolution_requirement` values, and a boolean per scenario
(`baseline`/`tier0`/`tier1`/`tier2`/`tier0+screen`/`tier0+focus_candidate`/`tier0+adjudicate`). Lets a reviewer
see *why* a TC does/does not unlock at each tier.

## 7. Summary metrics & STOP report

`…_SUMMARY_2026-06-29.md` contains, at minimum:

- **NOT_A_KEY subtype counts** (step-level): the 6 subtypes over the 189 — explicitly labelled `(step-level)`.
- **Eligibility cascade** (TC-level): `baseline_eligible` … `tier2_eligible` plus every `*_delta` from §5,
  explicitly labelled `(TC-level)`, with `headline_now_unlock = tier0_delta` called out as **the** no-device number.
- **Remaining-blocked breakdown**: of the TCs still not eligible at `upper_bound`, the count by dominant
  `BLOCKER` reason (AMBIGUOUS vs MANUAL_RETAIN vs manifest-rewrite).
- **Self-consistency line**: `baseline_eligible == predecessor headline (5)` — `self_check=ok|mismatch`.
- **Boundary examples**: a representative row for each subtype + the `간편 설정 페이지` screen-present case shown
  landing in `screen_present_delta` only, never in `headline_now_unlock`.
- A **STOP banner**: host-only, no device, no reclassification committed; await user decision on which subtypes to
  build.

### 7.1 Forbidden-word guard

The generator (and a test) assert the summary text contains none of `PASS`, `RUNNABLE_NOW`, `validated` (§5.5).

## 8. Architecture (predecessor-reuse pattern)

| File | Responsibility |
|---|---|
| `scripts/altbasic_not_a_key_subtype_ledger.py` (create) | **Imports** `parse_entry_detail`, `classify_step`, `build_ledger`, `normalize_body` from `altbasic_entry_detail_ledger`. Adds **pure**: `subclassify_not_a_key(step) -> subtype`, `resolution_requirement(row) -> enum`, `scenario_eligible(tc_rows, resolves) -> bool`, `summarize_cascade(ledger) -> dict`. Plus IO/`main`: emit subtype ledger CSV + cascade CSV + summary MD. No device, no wall-clock, no network, no catalog. |
| `tests/test_altbasic_not_a_key_subtype_ledger.py` (create) | Unit tests per subtype rule + each cascade scenario + a **golden** full-output test over a curated fixture subset + the forbidden-word test. |
| `tests/fixtures/altbasic/not_a_key_subtype_golden.json` (create) | Golden expected rows for a fixture covering all 6 subtypes, the §3.1 precedence pairs, the §5 scenario tiers, and the boundary cases. |

**Output artifacts** (durable evidence §2.4, audit folder, local until EOD batch):
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_LEDGER_2026-06-29.csv`
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_CASCADE_2026-06-29.csv`
- `THOR2 - ALT Basic TC Audit/NOT_A_KEY_SUBTYPE_SUMMARY_2026-06-29.md`

**Source-of-truth (§2.3):** new function = definition + code + test in the same change. The predecessor script is a
read-only dependency; if a NOT_A_KEY boundary needs the predecessor's classifier to change, that is a separate
change to the predecessor (with its own golden update), not an in-place fork here.

## 9. Testing strategy (host TDD)

- **Host TDD**: every subtype rule and cascade scenario written test-first (RED → GREEN).
- **Golden test**: full-pipeline assertion over a fixture subset so the headline and every delta are reproducible;
  a rule change that shifts a subtype or a tier fails loudly.
- **Self-consistency test**: `baseline_eligible` over the real manifest equals the predecessor headline (5).
- **Required golden/boundary cases** (minimum):
  - `전원 버튼 focus` → `VERIFIER_FOCUS_CANDIDATE` (focus wins over 버튼; no state marker ⇒ not Tier0);
  - `앱 서랍 포커스 되지 않은 상태` → `VERIFIER_FOCUS_STATE` (state marker ⇒ Tier0);
  - `간편 설정 페이지` → `VERIFIER_SCREEN_PRESENT`, and asserts this TC contributes to `screen_present_delta`
    **but not** to `headline_now_unlock`;
  - `해당 버튼을 짧게` and `뒤로가기` → `KEYCODE_DISCOVERY`;
  - `언어 및` (truncated) and `긴급 전화` (sensitive) → `MANUAL_RETAIN` (BLOCKER, never unlocks);
  - `펼치기 Tap` and `사진` → `SELECTOR_DISCOVERY`;
  - a TC mixing `VERIFIER_FOCUS` + `SELECTOR` → eligible at `tier1`, **not** at `tier0`;
  - the forbidden-word guard over the generated summary (`PASS`/`RUNNABLE_NOW`/`validated` absent).
- **Adversarial cases** (the kind the predecessor's review caught): single-syllable Korean direction false-match,
  long-press modifier, dangling-conjunction truncation.
- **No wall-clock / device / network** in tests. Re-running the generator on the same manifest is byte-identical.

## 10. Core invariants (the locks)

1. **Tier0 headline = high-confidence focus-state verifier reclassification only** (`headline_now_unlock = tier0_delta`).
2. **screen-present and focus-candidate are separate medium potentials**, never folded into the headline.
3. **Eligibility is computed over the full 620-step cascade** — every co-occurring blocker (FREE_TEXT selector/
   keycode, ADJUDICATE, AMBIGUOUS, MANUAL) is counted per TC; fail-closed.
4. **A Tier0 unlock is device-pilot *eligibility*, not a PASS / RUNNABLE_NOW / validated** — denylist enforced.
5. **Predecessor classifier reused, not forked**; its 39 tests stay green; `baseline_eligible == 5` self-check.

## 11. Future tracks (out of scope here, gated on this ledger)

- **VERIFIER_FOCUS_STATE reclassification** → convert the Tier0 steps to `focus_state` verifiers in the canonical
  yaml (separate approval; this is the no-device throughput win).
- **VERIFIER_FOCUS_CANDIDATE / SCREEN_PRESENT adjudication** → per-case decide verify-vs-navigate (possibly a
  catalog cross-check), then promote.
- **SELECTOR_DISCOVERY / KEYCODE_DISCOVERY** → thor2j device-discovery tracks (device window + go).
- **MANUAL_RETAIN** → stays manual; out of the automation funnel.
