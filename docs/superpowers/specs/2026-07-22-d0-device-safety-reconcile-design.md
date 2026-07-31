# D0 Device Safety Reconcile Design

Status: conditionally approved — A-1 through A-14 binding amendments applied

Date: 2026-07-22

Parent design: `2026-07-14-canonical-execution-contract-design.md` §9.3/§9.5

Code baseline: `093789584746aef38bf1c138ce195cb110369aa7`

## 1. Decision

Implement a bounded, standalone D0 host slice before any possible THOR2_J
legacy↔canonical device differential:

1. expose an explicit `cli run --serial <serial>` transport pin;
2. expose a separate `cli run --strict-shell` opt-in for checked shell results
   and strict invocation abort policy;
3. record both pinned and observed serials in every run bundle;
4. move screenshot and UI-dump temporary artifacts from `/sdcard` to
   `/data/local/tmp`;
5. replace the stale-property locale gate with active Android configuration
   evidence while retaining both locale properties as diagnostics.

`device_serial` and `strict_shell` are independent. A serial alone changes only
transport selection and never changes legacy execution semantics. The planned
four-run differential uses `--serial` only and must not use `--strict-shell`.

D0 is justified as standalone host safety and evidence work. The four-run
campaign is not currently executable because the observed active locale is
`en-US`; it remains blocked on the user decision in §7. The already committed
26-file slice is not amended.

## 2. Observed blockers

The first 2026-07-22 device preflight observed:

- expected/observed serial: `B2700125BW000083` / `B2700125BW000083`;
- observed model: `AT-M140`;
- `persist.sys.locale=en-US`;
- `ro.product.locale=ja-JP`.

The current code also conflicts with the approved device directive:

- `src.cli.cmd_run()` constructs bare `ADB()` and has no `--serial` option;
- `ADB.is_connected()` uses `adb devices`, even when an `ADB` instance has a
  serial-prefixed base command;
- `ADB.screenshot()` writes `/sdcard/screenshot_tmp.png`;
- `ADB.dump_ui()` writes `/sdcard/ui_dump.xml`.

No SMOKE run occurred after these blockers were observed. Locale/settings were
not changed, and `RESULT_2026-07-22.md` was not created.

## 3. Goals and non-goals

### Goals

- Make device identity pinning explicit in CLI argv and subprocess argv.
- Record `serial_pinned` and `serial_observed` in `summary.json` without
  changing `src/reporter.py`.
- Preserve the current no-serial CLI behavior for existing users.
- Preserve serial-pinned legacy behavior unless `--strict-shell` is explicitly
  supplied.
- Provide an independent strict-shell diagnostic mode that surfaces nonzero
  ADB results and applies strict invocation abort behavior.
- Keep all approved temporary device artifacts under `/data/local/tmp` and
  attempt their removal on every success or failure path.
- Define a locale gate that measures active runtime configuration rather than
  treating either property as authoritative by itself.
- Preserve canonical fail-closed behavior and all non-strict legacy execution
  behavior, whether pinned or unpinned.
- Produce a new deterministic ledger generation because `src/adb.py` is a
  ledger actor source.

### Non-goals

- No persistent configuration mutation. The approved TC process/navigation
  deltas (`am force-stop`, `am start`, and `input swipe`) are the only state
  changes allowed in a later campaign, and Settings remains force-stopped at
  campaign end. That delta must be recorded in the RESULT.
- No default flip or cutover decision.
- No THOR2_K work, producer promotion, schema change, action change, reporter
  schema change, or TC edit. ActionRunner dispatch semantics remain unchanged;
  bounded runtime changes are the explicit strict-shell transport and strict
  invocation policy defined in §5.3 and §6.
- No retry/compensation behavior for device failures.
- No push and no amendment of commit `0937895`.
- No device command during D0 implementation or review.

## 4. File scope

D0 implementation may modify exactly four tracked files:

- `src/cli.py`
- `src/adb.py`
- `tests/test_cli.py`
- `tests/test_adb.py`

The later device directive is a separate untracked review artifact. Ledger
CSV/SUMMARY outputs remain gitignored. All other tracked and untracked paths
are out of scope.

## 5. CLI and ADB interface

### 5.1 CLI

`cli run` gains two independent optional arguments:

```text
--serial DEVICE_SERIAL
--strict-shell
```

The value is passed as one argv token; it is never interpolated into a shell
string. `cmd_run()` reads it compatibly for both argparse and direct unit-test
callers, then constructs:

```python
device_serial = getattr(args, "serial", None)
strict_shell = bool(getattr(args, "strict_shell", False))
if device_serial is not None:
    try:
        validate_device_serial(device_serial)
    except ValueError as exc:
        print(f"ERROR: --serial 부적합: {exc}", file=sys.stderr)
        sys.exit(1)
if device_serial is None and not strict_shell:
    adb = ADB()
elif device_serial is None:
    adb = ADB(strict_shell=True)
elif not strict_shell:
    adb = ADB(device_serial=device_serial)
else:
    adb = ADB(device_serial=device_serial, strict_shell=True)
```

Validation happens before ADB construction. With neither option, direct
callers that lack both attributes retain the same unpinned, non-strict
behavior used before D0. Both options are available to legacy and canonical
modes, but the four-run differential supplies `--serial` only.

`--serial` accepts a non-empty, non-whitespace serial only. Absent/`None`
preserves unpinned compatibility. An explicitly supplied blank value or any
value containing whitespace is rejected before ADB construction.
`ADB(device_serial=...)` applies the same validation so an explicit pin cannot
degrade to unpinned operation when called outside the CLI. Explicit
`device_serial=None` is unpinned and valid; sentinel-based "argument supplied"
logic is forbidden because existing scripts pass `None` explicitly.

`--serial` is transport pinning only. It does not imply checked shell results,
strict abort, fatal legacy load rejection, or a different `run_status`.
`--strict-shell` independently enables the behavior in §5.3 and remains off by
default. `ADB` therefore has this signature:

```python
ADB(device_serial: str | None = None, *, strict_shell: bool = False)
```

The first positional parameter remains the serial for compatibility with the
ledger probe and existing scripts. The constructor stores it only as
`self._device_serial`; `self.device_serial` is forbidden because it would mask
the existing public `device_serial()` method.

This change is limited to the `run` subcommand. `devices`, `explore`, and
`preflight` intentionally remain unpinned and retain their current interfaces.
They are forbidden during a later four-run campaign (§11).

### 5.2 ADB connectivity

`ADB(device_serial=...)` continues to build:

```text
adb -s <serial>
```

as its base argv. When a serial is present, `is_connected()` must execute the
equivalent of:

```text
adb -s <serial> get-state
```

and return true only for return code 0 plus stdout `device` after trimming.
This prevents another attached device from satisfying the connectivity gate.
The constructor stores the explicit pin separately (for example,
`_device_serial`) and `is_connected()` branches on that state, not on inferred
`_base_cmd` shape.

When no serial is present, `is_connected()` preserves the existing
`adb devices` compatibility path. D0 does not redefine unpinned legacy device
selection.

Pinned `is_connected()` returns `False` on subprocess timeout or a missing ADB
executable and never retries through the unpinned `adb devices` path.

All other ADB subprocesses continue to derive argv from the same `_base_cmd`,
so `shell`, `shell_result`, the screenshot `pull` subprocess, the UI-dump
`shell cat` subprocess, `get-serialno`, and cleanup inherit the explicit serial
prefix. The exact pinned `ADB` object is also the object passed to
`ActionRunner`.

`cmd_run()` records device identity through the existing free-form reporter
device dictionary:

```python
reporter.device_info = {
    **adb.get_device_info(),
    "serial_pinned": device_serial,
    "serial_observed": adb.device_serial(),
}
```

`serial_pinned` remains `None` for an unpinned run. `serial_observed` comes from
the same ADB instance, so a pinned call executes `adb -s <serial>
get-serialno`. `src/reporter.py` is unchanged because it already serializes the
complete dictionary.

### 5.3 Strict-shell and strict invocation policy

`strict_shell` is independent from `device_serial`. `ADB("PROBE_SERIAL")` and
`ADB(device_serial="PROBE_SERIAL")` both remain non-strict unless the keyword
is explicitly true. This preserves the ledger's positional-serial defect probe
and the existing menu/tree scripts.

With `strict_shell=False`, `ADB.shell()` remains frozen: it passes the caller's
`timeout` value to `subprocess.run` without numeric coercion, returns stdout,
and discards a nonzero return code and stderr. In particular, the ledger probe
must continue to observe integer `timeout=5`, not `5.0`.

With `strict_shell=True`, a zero return code still returns stdout. A nonzero
return code raises `ADBCommandError(RuntimeError)` containing the operation,
return code, and at most 200 characters each of stdout and stderr in its
message. Timeout and missing-executable errors remain explicit. Serial
prefixing, if any, is orthogonal.
`shell_result()` keeps its structured non-raising-on-nonzero contract for
canonical callers.

Tap, swipe, key, input text, `dump_ui`, screenshot, and legacy `shell` paths
are all affected by strict mode. A strict `dump_ui` error escapes the handler
and is caught by the outer `ActionRunner.run_step()` boundary, so an inner
verifier retry loop can collapse from three attempts to one. A strict
screenshot action fails immediately; failure-screenshot capture retains its
existing best-effort exception suppression. These are explicit strict-mode
diagnostic contracts and are why the four-run differential must not enable
`--strict-shell`.

Only `--strict-shell` activates strict invocation handling:

- any failed step aborts the current TC and all later TCs, including legacy;
- a legacy `load_tc` `TCValidationError` is fatal instead of `SKIP + continue`;
- the failed StepResult is appended before
  `run_status=ABORTED_FAIL_CLOSED` is set;
- `summary.json` is attempted before the nonzero exit, and summary-write
  failure is fatal.

A strict legacy load rejection has no StepResult and never synthesizes one. If
it occurs before any TC result exists, it is a pre-step fatal error with no
summary requirement. If earlier TCs already produced results, those results
are preserved in a partial summary with
`run_status=ABORTED_FAIL_CLOSED`; summary-write failure is fatal, then the
process exits nonzero. No later TC is loaded or executed.

Without `--strict-shell`, a serial-pinned legacy run retains verifier-only
break/continue and load-SKIP behavior. Canonical mode remains independently
fail-closed through its existing contract-mode branch. This preserves
`run_status` as a legacy↔canonical comparison signal in the differential.

## 6. Temporary artifact confinement

Use these exact remote paths:

```text
/data/local/tmp/tc_runner_screenshot_tmp.png
/data/local/tmp/tc_runner_ui_dump.xml
```

Artifact creation and transfer/read execute inside one `try`, and cleanup is
always attempted in `finally`.

With `strict_shell=True`, the screenshot `screencap` call, UI-dump
`uiautomator dump` call, screenshot `pull` subprocess, UI-dump `shell cat`
subprocess, and cleanup `rm -f` each fail their helper on timeout or nonzero
return code. Cleanup failure must not mask an earlier operation failure; if
cleanup is the only failure, the helper fails. Error messages include the
failed operation, return code, and at most 200 characters each of stdout and
stderr.

With `strict_shell=False`, including a serial-pinned differential run, D0
changes only the two remote paths and guarantees a best-effort cleanup attempt.
Existing nonzero-result handling remains unchanged, and cleanup failure is
handled compatibly: cleanup rc nonzero is ignored, while a sole cleanup
`TimeoutError` or `FileNotFoundError` propagates as before. If a primary
creation/transfer/read error already exists, cleanup failure must not mask that
primary error. Tests characterize strict and non-strict paths separately.

D0 guarantees a cleanup attempt, not verified post-deletion absence on a
disconnected or failing device. The differential does not retroactively apply
strict helper semantics to the historical legacy baseline; a later strict
diagnostic run requires a separate label and approval.

The device directive may allow only these two remote files. `/sdcard` remains
forbidden for the differential.

## 7. Locale evidence contract

`persist.sys.locale` and `ro.product.locale` are recorded as diagnostics, not
used alone as the active-locale verdict.

Before the first legacy run, the revised device directive executes the pinned,
read-only command:

```text
adb -s B2700125BW000083 shell cmd activity get-config
```

The gate passes only when the command returns zero and the active
configuration yields exactly one usable configuration record whose primary
locale, after normalizing `ja-rJP` or `ja_JP` to `ja-JP`, equals `ja-JP`.
Japanese appearing only as a fallback/non-primary locale does not pass.
Matches elsewhere in raw output are diagnostic only. Zero usable records,
multiple/conflicting records, or unparsable active-locale evidence records raw
stdout, stderr, and return code, then records `NOTE` + `미실행` and STOPs
without changing locale.

The legacy SMOKE steps then provide UI-level ground truth through their
Japanese anchors. A property/configuration discrepancy is retained in the
result evidence; it is not silently normalized or repaired.

The currently observed `persist.sys.locale=en-US` does not satisfy the two
approved TCs' `persist.sys.locale=ja` precondition. `ro.product.locale=ja-JP`
is a factory default and cannot substitute for the active locale. Therefore no
four-run campaign can start until the user chooses one of these options:

1. manually set the device language to Japanese through Settings before the
   window; automation still performs no locale write; or
2. record `NOTE` + `미실행`, defer the differential, and keep canonical opt-in.

D0 implementation and ledger verification do not depend on that decision and
must not claim that the campaign can complete.

The later device directive must also run a step-0 capability probe before run
1 because `/data/local/tmp` has not been verified on AT-M140:

```text
adb -s <S> shell 'uiautomator dump /data/local/tmp/tc_runner_ui_dump.xml && cat /data/local/tmp/tc_runner_ui_dump.xml | head -c 200 && rm -f /data/local/tmp/tc_runner_ui_dump.xml'
adb -s <S> shell 'screencap -p /data/local/tmp/tc_runner_screenshot_tmp.png && rm -f /data/local/tmp/tc_runner_screenshot_tmp.png'
```

Failure is a D0 transport/design STOP, not a campaign result and not an
app/device defect verdict. `/sdcard` fallback remains forbidden.

## 8. Error and compatibility behavior

- A non-`None` blank or whitespace-containing serial prints a bounded
  `ERROR: --serial 부적합: ...` message to stderr and exits 1 before ADB
  construction. No traceback is emitted.
- Unsupported/offline pinned serial: stop before TC execution.
- Canonical host-preflight rejection: ADB construction remains zero.
- Serial pinning alone never changes legacy load, continuation, abort, or
  reporting behavior.
- Strict legacy load rejection or device failure stops the invocation under
  §5.3; no later step or TC executes.
- Canonical device failure: preserve `ABORTED_FAIL_CLOSED` and stop at the
  exact step.
- Strict temporary-artifact cleanup failure fails the helper but does not
  authorize a retry or `/sdcard` fallback. An earlier operation exception
  remains primary when cleanup also fails. Non-strict cleanup is best-effort
  and introduces no new failure surface.
- No environment-global `setx`, locale write, device setting write, install,
  reboot, or push is introduced.

## 9. TDD acceptance

Tests are added before implementation and must demonstrate RED at the missing
serial/strict plumbing and old `/sdcard` paths. Required behavior coverage:

1. `cli run --serial SERIAL` and `--strict-shell` parse independently.
2. `ADB(device_serial=None, *, strict_shell=False)` keeps serial as the first
   positional parameter and stores it in `self._device_serial` without masking
   the public `device_serial()` method.
3. `ADB("PROBE_SERIAL").shell()` returns stdout on rc nonzero and forwards the
   original integer timeout unchanged; serial alone never implies strict.
4. Explicit `ADB(device_serial=None)` is unpinned; non-`None` blank or
   whitespace-containing values are rejected.
5. Invalid CLI serial prints to stderr, exits 1 without traceback, and
   constructs zero ADB instances.
6. A canonical host-preflight failure still constructs no ADB even when either
   new option was supplied.
7. Pinned `is_connected()` uses `adb -s SERIAL get-state`; rc 0 plus trimmed
   stdout `device` succeeds. Nonzero/offline/empty/other output, timeout, and
   missing executable return false without unpinned retry.
8. Unpinned `is_connected()` retains the existing `adb devices` path.
9. The exact serial-configured ADB instance reaches ActionRunner. Device
   evidence records `serial_pinned` and `serial_observed` from that instance.
10. `--serial` alone preserves legacy load-SKIP, continuation, abort,
    `run_status`, and summary-write warning behavior.
11. `--strict-shell` alone controls checked-shell behavior, legacy any-step
    abort, fatal legacy load rejection, `ABORTED_FAIL_CLOSED`, and fatal summary
    persistence. Tests fix failed-result append → status → write → exit order.
    A first-file load rejection produces no synthetic result/summary; a later
    rejection preserves prior results in an aborted partial summary.
12. Strict command errors include rc and at most 200 characters each of stdout
    and stderr. Non-strict shell output and timeout argument type remain frozen.
13. Screenshot and UI dump use only the two `/data/local/tmp` paths and attempt
    cleanup after creation, transfer/read failure, or success.
14. Strict helper tests distinguish creation failure, transfer/read failure,
    cleanup-only failure, and combined primary+cleanup failure; combined
    failure preserves the primary exception.
15. Non-strict screenshot/UI-dump cleanup rc nonzero is ignored, a sole cleanup
    timeout/missing executable propagates, and combined cleanup failure never
    masks an earlier primary error.
16. Strict device-info failure is pre-execution: ActionRunner construction and
    TC execution are zero, exit is nonzero, and no synthetic StepResult or
    summary is required.
17. Focused `tests/test_adb.py tests/test_cli.py` and the complete `tests/`
    suite have zero failures, and no original collected nodeid disappears.

Tests use mocked subprocesses only. D0 host verification issues no ADB command.

## 10. Ledger and freeze evidence

Because `src/adb.py` belongs to the ledger `action_runner` actor source, its
change must produce a new input digest and output directory. The existing
generations, including `16ee5ae8ca8f55c4`, remain immutable historical
evidence.

No ledger fixture or probe contract changes in D0. The following are
reconciliation expectations, not fixture or self-check invariants; the ledger
must remain capable of observing them changing:

- `TOOL_VERSION=contract-drift-ledger-v4` remains unchanged;
- `FIXTURE_VERSION=4` remains unchanged;
- expected rows remain 226;
- expected legacy blocking remains 12;
- expected producer×consumer base groups remain 8;
- expected legacy/canonical mode-expanded pair observations remain 16;
- the three canonical runner observations remain present;
- corpus counts remain `(3, 25, 2, 1)` and THOR2_K remains informational 0.

Run the new generation twice and require byte-identical CSV/SUMMARY. Combined
`--verify-determinism --fail-on-blocking` expects exit 1 due to the observed
legacy blocking 12 only after determinism and all independent self-checks
pass.

The new generation's `contract_drift_matrix.csv` must also be byte-identical to
`reports/contract_drift/16ee5ae8ca8f55c4/contract_drift_matrix.csv`. Counts
alone are insufficient: the non-strict shell probe must preserve
`"subprocess_timeout":5`, including the integer type. Its subprocess timeout
argument must not be coerced to `5.0` through delegation.

The new SUMMARY may differ from the `16ee5ae8ca8f55c4` SUMMARY only in the
input digest, output-directory/digest prefix, and the `src/adb.py` source-hash
line. Because the CSV is byte-identical, the CSV SHA-256 value must also remain
identical; only a generation-specific path/prefix on that line may differ if
present. Every other line is frozen. Any unexpected CSV byte, SUMMARY line,
row, verdict, count, or fixture/probe change is a STOP condition, not an
automatic baseline update. Existing generations remain immutable.

## 11. Post-D0 device directive

The four-run campaign remains blocked until the user makes the locale decision
in §7 and issues a new serial-pinned directive. D0 completion by itself does
not authorize device entry.

That later directive must:

- complete the `/data/local/tmp` step-0 capability probe from §7 before run 1;
- invoke every run with `--serial B2700125BW000083` and never with
  `--strict-shell`;
- assign four distinct explicit run IDs and prove each bundle directory did
  not exist before its run;
- use the active-configuration locale gate from §7 and record both locale
  properties without treating either as sole authority;
- permit only the two namespaced `/data/local/tmp` artifacts;
- preserve order: legacy 01 → legacy 02 → canonical 01 → canonical 02;
- enter each next run only after the preceding run meets every result-evidence
  gate below;
- require exclusive automation ownership of the serial for the whole window;
- forbid every tc-runner CLI command except `run --serial <S>` during the
  window because `devices`, `explore`, and `preflight` remain unpinned;
- record the approved process/navigation delta and the final force-stopped
  Settings state;
- forbid default flip, push, RESULT commit, locale automation, retries, and
  `/sdcard` fallback.

If exclusivity or any pre-run gate cannot be established, record `NOTE` +
`미실행` and STOP before run 1. Before approval, the directive must freeze the
locale parser against a captured raw `cmd activity get-config` sample: exact
record prefix/field, primary-locale extraction, normalization, and rejection
cases. Arbitrary locale-token occurrence never determines the verdict.

### 11.1 Per-run result-evidence gate

For each exact run ID, all of the following are required before the next run:

0. `reports/<run-id>/` did not exist before invocation;
1. command exit code is zero;
2. `reports/<run-id>/summary.json` exists and belongs to that exact run ID;
3. the expected TC is present exactly once, with no missing or skipped TC/step;
4. every expected `results[].steps[].passed` value is true;
5. `device.serial_pinned == device.serial_observed ==
   B2700125BW000083`;
6. `contract_mode` equals the intended mode: runs 1-2 `legacy`, runs 3-4
   `canonical`;
7. `len(results) == 1` and the literal step cardinality matches: SMOKE_01 is
   11 and SMOKE_02 is 13;
8. the run has a recorded pre-run `ls /data/local/tmp/` baseline and post-run
   `ls /data/local/tmp/tc_runner_*` shows zero residual artifacts.

Legacy process exit code or top-level `run_status=COMPLETED` alone is never a
success oracle. A missing/reused bundle, summary/run-id mismatch, serial or
mode mismatch, unexpected/missing result, cardinality mismatch, skipped item,
failed step, or residual artifact STOPs the campaign. Only runs not invoked are
`미실행`; an invoked run that fails must be classified by §11.2.

### 11.2 Divergence classification

| Observation | Vocabulary | Diagnosis | Action |
|---|---|---|---|
| Declared TC `shell` step records rc nonzero and fails | `BUG-GAP observed` | `CONFIRMED` (corroborates the frozen defect) | Record, STOP, review |
| ADB helper (`screencap`/`pull`/`uiautomator dump`/`cat`/`rm`) fails | `NOTE` | `OBSERVED` | D0 transport artifact; STOP and return to design review, with no app/device blame |
| `verify_text` fails with `Text '<X>' not found on screen` and no rc | `BUG-GAP observed` | `OBSERVED` | Only case that may implicate app/device behavior |
| Command is not invoked, including gate STOP | `미실행` + `NOTE` | — | Every later run remains `미실행` |

An invoked failed run must never be labeled `미실행`, and a surfaced rc must
never be reduced to generic "environment failure." Historical `11/11` and
`13/13` evidence is labeled `runtime PASS (legacy, rc-unchecked)` when cited.
Legacy exception text and canonical structured `Shell rc=...` text differ by
construction and are not by themselves a semantic mismatch.

## 12. Commit and review boundaries

After implementation, verification, ledger regeneration, review, and separate
explicit user approval to commit, stage exactly the four scoped files and
create one local micro-commit. Without that approval, leave all changes
uncommitted. Do not amend `0937895`. Suggested subject:

```text
fix(device): pin adb serial and confine temporary artifacts
```

Staging must equal the exact four-file set. Push remains separately gated.
The design document and later directive are not included unless the user
explicitly approves their disposition.
