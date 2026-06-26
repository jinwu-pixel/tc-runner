# ALT Basic entry_detail Normalization Ledger — Design

> Status: DRAFT (brainstorming output, awaiting user spec review). Commit deferred to end-of-day batch per global §7 / project §7.1 (draft = no immediate commit).
> Date: 2026-06-26
> Track: THOR2 ALT Basic TC Audit — throughput pivot, device-free measurement slice.

---

## 1. Goal

Produce a **measurement ledger** that classifies the `entry_detail` of all **236 rows** of the batch10
device-validation manifest (`THOR2 - ALT Basic TC Audit/handoff_device_validation/VALIDATION_MANIFEST_BATCH10_2026-06-25.csv`)
into normalization dispositions, and quantifies — **defensibly** — how many rows each candidate normalization
rule would make eligible for the device-pilot flow.

This is a **measure-first** track. It answers "which normalization rule unlocks how much device-pilot
eligibility?" so we can decide which rules to build next, *before* committing any resolver/yaml change.

### Why this track exists

The C01 narrow driver (`thor2j runner/altbasic_narrow.py` + `altbasic_c01_driver.py`, committed 2026-06-26)
covers only the cleanly-keyed subset of one manifest chunk (sheet `1.Basic principle`, 13 rows → 4 RUNNABLE).
A pre-scan over the full 236 found `entry_detail` is ~70% free-text prose: **148/236 rows have at least one
"bare" continuation step** (no `action:` prefix, 245 bare tokens / 97 distinct), and of **273 `press_key`
bodies (134 distinct) only 5 resolve** via the driver's 5-key dictionary. The free-text/body-resolution gap —
not the driver mechanics — is the real throughput bottleneck. This ledger measures that gap precisely.

## 2. Non-goals (explicit boundaries)

- **No code/yaml mutation** to the runner, `validate_tc.py`, the canonical STAGE1 yaml, or the thor2j device
  driver. The only new code is the read-only ledger generator (§7).
- **No device contact.** Host-only, fully reproducible, no wall-clock dependence.
- **No commit to a keycode at device-run time.** The ledger *proposes* mappings; the device run1 still
  confirms literals (same as the C01 `PILOT_LITERAL` flow). A NOW_RESOLVABLE verdict means
  "device-pilot eligible", **not** "RUNNABLE without device" (§2.2 PASS vocabulary — static analysis ≠ runtime PASS).
- **No reclassification of the canonical yaml or manifest.** NOT_A_KEY / FREE_TEXT rows are *flagged* as
  candidates for a future reclassification or device-discovery track, not edited here.
- Not building the directional-key resolver into the device driver. That is a **future thor2j track** gated on
  this ledger's findings + user approval (§9).

## 3. Disposition taxonomy (5 tiers)

Conservative boundary (option A): the **headline** count includes only NOW_RESOLVABLE. Every other tier is
counted separately so the unlock potential stays visible without inflating the defensible number.

| Tier | Definition | Examples | Headline? |
|---|---|---|---|
| **NOW_RESOLVABLE** | A single, explicitly-named key or single direction that maps to one deterministic Android keycode. KO and EN variants both allowed, **provided the single direction/key is unambiguous in the phrase**. | `Press Down`, `UP 방향키`, `하방향키`, `press ok`, `Right 방향키`, plus existing keys `Recent App 버튼`(187)/`Home 버튼`(3)/`Camera 버튼`(27)/`Contact 버튼`(207)/`하드키 돌아가기 버튼`(4) | ✅ counted |
| **ADJUDICATE** | A plausible single candidate exists but selecting it requires an **intent decision** — disjunctions and qualified Navi/OK phrases. | `네비키 또는 OK키`, `Navi 키(OK)` | ❌ → `potential_with_adjudication` |
| **AMBIGUOUS_NOGUESS** | **Test-intent** ambiguity the device cannot resolve by probing — "any" keys and multi-key enumerations. fail-closed. | `아무 방향키`, `Press Any Direction`, `Navi U/D/L/R/OK 키 입력` | ❌ counted |
| **NOT_A_KEY** | Step is tagged `press_key` (or a bare step after one) but the body is a **screen / focus / state description**, not a key. Candidate for verifier or navigate **reclassification** (not a key-mapping rule). | `시계`, `wifi focus`, `앱서랍 진입`, `간편 설정 페이지`, `새 연락처 만들기 focus` | ❌ counted |
| **FREE_TEXT_DISCOVERY** | `tap`/`navigate` bodies needing a **selector**, named hardware keys with **no standard keycode** (device keycode-discovery), or bare prose that is none of the above. Resolved by device discovery or a manifest-rewrite track. | `더보기`, `퀵 패널`, `설정` (tap); `Message 버튼`, `지우기/취소 버튼` (keycode-discovery) | ❌ counted |

### 3.1 Boundary rules (the defensible core)

The classifier normalizes a step body (strip leading `N.`, strip trailing verbs `누른다/누름/입력한다/입력/누르기/Tap/탭`,
collapse whitespace, case-fold the ASCII portion) and then applies, **in this precedence**:

1. **Known named key** (exact match to the 5-key dictionary) → NOW_RESOLVABLE.
2. **Single-direction / single-key vocabulary** (controlled list, §4) with **no ambiguity marker** → NOW_RESOLVABLE.
3. **Ambiguity marker present**:
   - disjunction (`또는`, `/` between key tokens) or qualified-Navi (`Navi …(OK)`) with one plausible candidate → **ADJUDICATE**.
   - "any" (`아무`, `any`) or a multi-direction enumeration (`U/D/L/R/OK`, ≥2 distinct direction tokens) → **AMBIGUOUS_NOGUESS**.
4. **Screen/focus/state reference** on a `press_key`/bare body (contains `focus`/`화면`/`페이지`/`진입` markers, or is a
   bare noun-phrase matching no key vocabulary) → **NOT_A_KEY**.
5. **Otherwise** (`tap`/`navigate` body, named-key-without-keycode, residual bare prose) → **FREE_TEXT_DISCOVERY**,
   with `required_decision` distinguishing `device_selector_discovery` / `device_keycode_discovery` / `manifest_rewrite`.

The exact vocabulary lists and marker tokens are pinned by the golden fixture and refined test-first in the plan;
this section fixes the *rules*, not every token.

### 3.2 Named-hardware-key-without-keycode (boundary refinement — flag for review)

`Message 버튼` / `지우기/취소 버튼` are real hardware keys but have **no standard Android keycode** (C01 routed
them to FAIL_CLOSED). They are neither NOT_A_KEY (they *are* keys) nor AMBIGUOUS_NOGUESS (intent is clear). To
avoid adding a 6th tier against the agreed 5, they land in **FREE_TEXT_DISCOVERY** with
`required_decision = device_keycode_discovery`, keeping them distinct from selector-discovery in the data.
**This placement is called out explicitly for user sign-off at the spec-review gate.**

## 4. Resolver vocabulary (NOW_RESOLVABLE mapping)

Single-direction / single-key controlled vocabulary, each mapping to exactly one keycode. KO/EN variants of the
*same single* direction are folded together; nothing with an ambiguity marker (§3.1) enters here.

| Keycode | Constant | Accepted single-key/direction variants (normalized, illustrative) |
|---|---|---|
| 19 | DPAD_UP | `up 방향키`, `up방향키`, `press up`, `상방향키`, `위 방향키`, `위방향키` |
| 20 | DPAD_DOWN | `press down`, `down 방향키`, `하방향키`, `아래 방향키`, `press down(하드키)` |
| 21 | DPAD_LEFT | `left 방향키`, `press left`, `좌방향키`, `왼쪽 방향키` |
| 22 | DPAD_RIGHT | `right 방향키`, `press right`, `우방향키`, `오른쪽 방향키` |
| 23 | DPAD_CENTER | `press ok`, `ok키`, `ok 버튼`, `확인키` (single OK token, no `또는`, no `Navi(…)` qualifier) |
| 187 | APP_SWITCH | `Recent App 버튼` (existing) |
| 3 | HOME | `Home 버튼` (existing) |
| 27 | CAMERA | `Camera 버튼` (existing) |
| 207 | CONTACTS | `Contact 버튼` (existing) |
| 4 | BACK | `하드키 돌아가기 버튼` (existing) |

The mapping is a **proposal**: device run1 still confirms the resulting screen literal before the row counts as
RUNNABLE. The ledger records the proposed keycode and the rationale; it does not assert runtime success.

## 5. Ledger schema

One row **per extracted step (token)**. A multi-step `entry_detail` produces multiple ledger rows.

Columns (minimum, per user directive):

| Column | Meaning |
|---|---|
| `tc_id` | e.g. `ALTBASIC_BSC_014` |
| `source_file` | manifest `source_file` (xlsx) for provenance |
| `original_entry_detail` | the full unmodified `entry_detail` string |
| `extracted_token` | the single step/body this row classifies (after split on `>`, step-number strip) |
| `disposition` | one of the 5 tiers |
| `proposed_normalized_step` | the structured step we would emit, e.g. `press_key:DPAD_DOWN` / `tap:<target>` / `(reclassify→navigate)` |
| `proposed_keycode` | integer keycode for NOW_RESOLVABLE/ADJUDICATE-candidate, else blank |
| `confidence` | `high` (NOW_RESOLVABLE) / `medium` (ADJUDICATE) / `low` (others) |
| `rationale` | why this disposition — names the matched vocabulary/marker |
| `required_decision` | blank, or `intent_choice` / `spec_clarification` / `reclassify_verifier_or_navigate` / `device_selector_discovery` / `device_keycode_discovery` / `manifest_rewrite` |
| `device_pilot_eligible` | TC-level boolean (see §5.1), repeated across that TC's rows |

### 5.1 TC-level eligibility rollup (fail-closed)

`device_pilot_eligible` is a **TC-level** verdict, repeated on every row of that TC: **true only if *every*
parsed executable entry step of the TC is NOW_RESOLVABLE.** A single non-NOW_RESOLVABLE executable step (bare
prose, tap-without-selector, ambiguous key, etc.) blocks the whole TC — consistent with the C01 driver's
no-guess routing (any unresolved step → not a pilot).

**Rollup scope = parsed executable entry steps only.** An executable step is one whose intended action is an
interaction (`press_key`/`tap`/`swipe`/`long_press`/`navigate`/`launch`/`launch_app`/`input`/`wait`). Tokens that
are observation/literal/assert in nature (non-executable — e.g. a `확인한다`-style observe token or a literal that
slipped into `entry_detail`) are **excluded from the eligibility denominator** (recorded with a
`disposition`/`required_decision` flag, but never counted *against* eligibility). This avoids undercounting
pilot-eligible TCs whose `entry_detail` mixes in a non-executable token.

`headline_resolvable_count` = number of **TCs** with `device_pilot_eligible = true`.

## 6. Summary metrics & STOP report

The generator emits a sibling `…_SUMMARY_…md` with, at minimum:

- Per-tier counts: NOW_RESOLVABLE / ADJUDICATE / AMBIGUOUS_NOGUESS / NOT_A_KEY / FREE_TEXT_DISCOVERY
  — **explicitly labelled `(step-level)`**.
- `headline_resolvable_count` **`(TC-level)`** (§5.1) and `potential_with_adjudication_count` **`(TC-level)`**
  (TCs that become eligible if every ADJUDICATE step is decided favorably — i.e. eligible-or-adjudicate-only).
  The summary **must carry the `(step-level)` vs `(TC-level)` label on each metric**: tier counts are step-level,
  the two headline metrics are TC-level, and conflating them would misrepresent the unlock size to a reader.
- **Top 10 unlock rules**: which normalization rule (e.g. "DPAD_DOWN variants", "DPAD_CENTER/ok", "fold `press down(하드키)`")
  unlocks the most TCs, ranked.
- **Representative misclassification / boundary examples**: rows near each boundary (e.g. `press ok` NOW_RESOLVABLE
  vs `네비키 또는 OK키` ADJUDICATE vs `아무 방향키` AMBIGUOUS) so the boundary is auditable by eye.
- **Calibration against C01**: the 13 sheet-`1.Basic principle` rows already dispositioned by the narrow driver are
  cross-checked; any disagreement is reported (the ledger classifier must agree with the committed C01 routing on
  those 13 — a self-consistency check).

Then a **STOP banner**: host-only, no device, no further normalization committed; await user decision on which
rules to build.

## 7. Architecture (settings_anchor_gap.py pattern)

Read-only static analysis: a pure parser/classifier plus a thin IO/CLI layer, reproducible with no wall-clock.

| File | Responsibility |
|---|---|
| `scripts/altbasic_entry_detail_ledger.py` (create) | **Pure**: `parse_entry_detail`, body-normalizer, `KEY_VOCAB` + `resolve_single_key`, `classify_disposition`, TC-level `rollup_eligibility`. **Plus** IO/`main`: read manifest CSV, emit ledger CSV + summary MD. No device, no wall-clock, no network. |
| `tests/test_altbasic_entry_detail_ledger.py` (create) | Unit tests for the pure functions (parser, vocab, each disposition boundary, rollup) + a **golden** test asserting the full ledger output for a fixed input subset. |
| `tests/fixtures/altbasic/entry_detail_ledger_golden.json` (create) | Golden expected ledger rows for a curated fixture subset (covers all 5 tiers + boundary cases + the C01 calibration rows). |

**Output artifacts** (durable evidence, §2.4, into the audit folder — local until EOD batch):
- `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_LEDGER_2026-06-26.csv`
- `THOR2 - ALT Basic TC Audit/ENTRY_DETAIL_NORMALIZATION_SUMMARY_2026-06-26.md`

**Cross-repo note (§2.5):** the parser/key-resolver here conceptually mirrors thor2j `altbasic_narrow`, but is
**independently implemented in tc-runner** (no cross-repo import). They serve different purposes — this is a
learning-loop *measurement* (tc-runner); `altbasic_narrow` is *device execution* (thor2j). Any later port of the
expanded vocabulary into the device driver is a separate thor2j track.

## 8. Testing strategy

- **Host TDD**: every classifier rule written test-first (RED → GREEN), one failing test per boundary before its code.
- **Golden test**: full-pipeline assertion over a fixture subset so the headline number is reproducible and a rule
  change that shifts a disposition fails loudly.
- **Calibration test**: the 13 C01 rows must classify consistently with the committed narrow-driver routing.
- **Required fixture cases** — the golden fixture and parser tests **must** include, at minimum:
  - the named-hardware-key-without-keycode case (`Message 버튼`, `지우기/취소 버튼`) → asserts
    `disposition=FREE_TEXT_DISCOVERY` **and** `required_decision=device_keycode_discovery` (§3.2);
  - one example of every other tier and every boundary pair in §6 (e.g. `press ok` NOW_RESOLVABLE vs
    `네비키 또는 OK키` ADJUDICATE vs `아무 방향키` AMBIGUOUS_NOGUESS);
  - a multi-step TC where one executable step is non-NOW_RESOLVABLE → asserts `device_pilot_eligible=false`;
  - a TC mixing a non-executable token with NOW_RESOLVABLE executable steps → asserts the non-executable token is
    excluded from the denominator and the TC stays eligible (§5.1).
- **No wall-clock / no device / no network** in tests — pure functions over fixed strings.
- Reproducibility: re-running the generator on the same manifest yields byte-identical ledger output.

## 9. Future tracks (out of scope here, gated on this ledger)

- **Directional resolver → thor2j device driver**: extend `altbasic_narrow.KEY_DICT` with the NOW_RESOLVABLE
  vocabulary, then device run1/run2 the newly-eligible rows (separate thor2j track + device-go).
- **ADJUDICATE decisions**: user decides per-case which branch `또는`/`Navi(OK)` rows take; decided rows graduate
  to NOW_RESOLVABLE in a later ledger pass.
- **NOT_A_KEY reclassification**: convert mis-tagged screen/focus bodies to verifier-targets or navigate steps
  (canonical yaml edit track, separate approval).
- **FREE_TEXT_DISCOVERY**: device selector/keycode discovery or manifest rewrite.

## 10. Resolved decisions (spec review, 2026-06-26)

- **§3.2 confirmed** — named-hardware-keys-without-standard-keycode (`Message 버튼`, `지우기/취소 버튼`) stay in
  FREE_TEXT_DISCOVERY with `required_decision=device_keycode_discovery`; **no 6th tier**. Rationale: they are keys
  but have no standard keycode, so placing them in NOW_RESOLVABLE would break the C01 no-guess boundary; they are
  not NOT_A_KEY either, so `required_decision` carries the distinction. (User-approved.)
- **§5.1 revised** — rollup scope restricted to *parsed executable entry steps*; non-executable observe/literal
  tokens are excluded from the eligibility denominator (avoids undercounting pilot-eligible TCs).
- **§6 revised** — summary must label tier counts `(step-level)` and the two headline metrics `(TC-level)`.
- **§8** — golden fixture must include the `device_keycode_discovery` case and the §5.1 mixed-token case.
