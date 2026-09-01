# BUG27084 Quantitative Loop Evidence Implementation Plan

> **For Codex:** Use `superpowers:test-driven-development` and execute each task in order. Device mutations are outside this plan until a separate exact execution capsule is approved.

**Goal:** Correct the current n=1/crash-only conclusion boundary and extend the host harness so each future cycle records a 30-second BUG27084 signature, Launcher crash-exit PID, restart-loop, and exact old-widget loader-log delta.

**Architecture:** Keep device orchestration in `appwidget_stale_provider_orchestrator.py` and add only a pure `ApplicationExitInfo` parser/value object to the existing parser/model layer. Observation remains one trigger transaction, but the authoritative crash/log/exit-info snapshots move to the end of a 30-second window so events occurring during that window are included. Classification remains `OBSERVED`; loop evidence is an additional measured field, not a new PASS state.

**Tech Stack:** Python 3, dataclasses, pytest, existing evidence manifest and exact-serial transport.

---

### Task 1: Correct the documented conclusion boundary

**Files:**
- Modify: `AT-M140 - Launcher BUG27084/RESULT_2026-09-01.md`
- Modify: `docs/superpowers/specs/2026-08-29-appwidget-stale-provider-knowledge-pipeline-design.md`

- [x] State that each formal A/B cell is n=1.
- [x] Separate one recovered crash from the field crash-loop symptom.
- [x] Record `INFERRED_ONLY` as the current stale-record evidence limitation.
- [x] Require known-bad independent-fixture n=5 first, expand to n=10 if unstable, before matched fixed-build comparison.

### Task 2: Add pure Launcher crash-exit parsing

**Files:**
- Modify: `scripts/appwidget_stale_provider_models.py`
- Modify: `scripts/appwidget_stale_provider_parsers.py`
- Test: `tests/test_appwidget_stale_provider_repro.py`

- [x] Write RED tests using real-format `dumpsys activity exit-info` records.
- [x] Parse only exact package `reason=4 (APP CRASH...)` entries into immutable identities.
- [x] Prove record renumbering does not defeat baseline subtraction.

### Task 3: Extend the observation schema and 30-second window

**Files:**
- Modify: `scripts/appwidget_stale_provider_orchestrator.py`
- Test: `tests/test_appwidget_stale_provider_repro.py`

- [x] Write RED tests for phase-new crash exits, exact loader-log delta count, and loop threshold.
- [x] Move authoritative crash/main-log/exit-info capture after the stability wait.
- [x] Change the default window from 10 to 30 seconds.
- [x] Persist `launcher_crash_exit_count`, `launcher_crash_exit_pids`, `launcher_loop_observed`, `launcher_loop_basis`, and `launcher_loader_record_count` in result and verification records.
- [x] Define loop evidence as at least two BUG27084 signatures or at least two phase-new exact-package APP CRASH exits within the active-boot window.

### Task 4: Verify host-only behavior

**Files:**
- Test: `tests/test_appwidget_stale_provider_repro.py`

- [x] Run focused parser and observation tests.
- [x] Run the full AppWidget harness test file.
- [x] Run Python compilation and `git diff --check`.
- [x] Run the repository `tests/` suite if focused checks pass.

### Task 5: Prepare the independent-cycle device capsule

**Files:**
- Modify: `AT-M140 - Launcher BUG27084/RESULT_2026-09-01.md`

- [x] Define SimpleClock and AccuWeather A/B cells with independent fixture reset per cycle.
- [x] Start with n=5 per cell and preserve numerator/denominator, crash count, loop count, loader-log count, and recovery outcome.
- [x] Receive explicit aggregate approval for the bounded known-bad campaign; do not infer firmware, commit, or push authorization.

### Task 6: Execute the known-bad independent-fixture matrix

**Evidence root:** `AT-M140 - Launcher BUG27084/evidence/`

- [ ] Run SimpleClock clean-control A with a 30-second observation window for n=5 independent cycles.
- [ ] Run SimpleClock stale-control B with a 30-second observation window for n=5 independent cycles.
- [ ] Run AccuWeather clean-control A with a 30-second observation window for n=5 independent cycles.
- [ ] Run AccuWeather stale-control B with a 30-second observation window for n=5 independent cycles.
- [ ] Use `trigger` as the sole authoritative 30-second observation. Do not run `verify` as a second sample; clean-control phases do not support it and it would not be an independent fixture.
- [ ] Between cycles, prove safe Simple HOME recovery, persist exact-serial Launcher-reset evidence, perform clean Launcher first initialization, prove all prior widget IDs/host bindings absent, return to Simple HOME 3-way, and link that reset to the next run before capture.
- [ ] Stop only on exact-identity, immutable-input, evidence-integrity, selector, package-recovery, or safe-HOME recovery gate failure.

### Task 7: Reconcile and report the quantitative campaign

**Files:**
- Modify: `AT-M140 - Launcher BUG27084/RESULT_2026-09-01.md`

- [ ] Verify every completed bundle manifest and exact target serial.
- [ ] Record per-cell numerator/denominator for BUG27084 crash, loop, loader-log, and successful safe recovery.
- [ ] Keep diagnosis at `OBSERVED` unless the repository's `CONFIRMED` matrix and quantitative requirements are actually satisfied.
- [ ] Exclude fixture/capture/precondition failures from the observation denominator with an explicit reason. If `trigger` evidence is valid but later recovery fails, retain that observation in the crash/loop/loader denominator and report recovery against its own attempted-recovery denominator.

### Campaign execution rulings

- Ruling: command-by-command orchestration may continue without phase approvals under the bounded campaign approval, but no raw outer loop may bypass evidence or fail-stop gates.
- Ruling: `trigger` is the only observation counted as one cycle; `verify` is omitted from campaign cycles.
- Ruling: `restore → pm clear launcher → immediate capture` is insufficient for independence. Reset mutation, first-launch cleanup, prior-ID absence, final Simple HOME 3-way, and predecessor linkage must all be evidenced before the next capture.

Commit and push are deliberately omitted because neither is authorized in this task.
