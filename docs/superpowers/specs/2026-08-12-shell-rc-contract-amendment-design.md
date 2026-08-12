# Shell-RC provenance contract amendment design

> **STATUS: IMPLEMENTED + TESTED — COMMIT APPROVAL PENDING (2026-08-12)**
>
> 사용자 승인 범위는 Appendix B의 loader-equivalent shared-column 검증,
> deterministic analyzer stdout, 회귀 테스트, SHA/spec identity 재결박이다.
> staging, commit, push, capsule capture, campaign 실행, campaign root cleanup은
> 포함하지 않는다.

## 1. Evidence anchor

- directive: `RB-20260728-shellrc-p0p1`
- entry commit: `5b1dd8879733da9269650f552e547733c40d0b6e`
- isolated diagnostic SHA-256:
  `08799f816845291c8ea0d4782712bcf08dca13d488def3e3241d7f07d9b5b770`
- diagnostic reproducibility: two executions byte-identical
- observed valid reconciliation after in-memory alias correction:
  14 mapped documents, 13 reconciled documents, 15 target bindings,
  17 blocking reasons
- blocking reason distribution:
  `TARGET_STEP_JOIN=15`, `PRODUCER_RUNNABILITY_GAP=2`

The campaign reached `ANALYZE`; the final `INPUT_INVALID` was not an ACL or
producer-process failure. Two verifier contracts converted a valid measured
`PROVENANCE_MISMATCH` into invalid input.

## 2. Root causes

### 2.1 Loader-equivalent semantic alias

`src/mmi_converter/row_loader.py` maps an absent `feature_name` header to
`functionality - 1`. In `SS-TC 1`, that physical column is also the explicit
`priority` column. Appendix A correctly records both semantic fields against the
same cell. The old Appendix B incorrectly required seven distinct column values
and seven distinct region coordinates.

### 2.2 Silent analyzer versus non-empty evidence

Appendix B atomically published `reconciliation.json` and returned `0` without
stdout. The controller therefore wrote a zero-byte `analyze.combined.txt`, while
Appendix C correctly kept every completed ANALYZE required file non-empty. The
two contracts were mutually unsatisfiable.

## 3. Chosen design

### 3.1 Narrow shared-column allowance

The semantic column map remains injective except for exactly one duplicate
group: `{feature_name, priority}`. It is allowed only when
`feature_name == functionality - 1`, reproducing the loader fallback. Any other
duplicate group, triple collision, or position fails closed.

For an allowed shared coordinate:

- duplicate header cell evidence is identical after excluding only the semantic
  `field` label;
- duplicate row cell evidence is fully identical field by field;
- duplicate row region records are fully identical field by field;
- the unique-coordinate region set still equals the expected semantic
  coordinate set.

Appendix A remains byte-unchanged because its capture already matches the
loader.

### 3.2 Deterministic analyzer line

After atomic reconciliation publish, every successful analyzer invocation emits
exactly one line:

```text
ANALYZE_RESULT verdict=<verdict> mapped_documents=<int> targets=<int> blocking_reasons=<int>
```

The field order and LF are fixed. Timestamp, nonce, absolute path, mtime, and
environment-dependent text are forbidden. Appendix C's non-empty invariant is
unchanged.

## 4. Test contract

TDD requires the old Appendix B to demonstrate these failures before the
implementation change:

1. a real-shape `SS-TC 1` shared `feature_name`/`priority` fixture is rejected;
2. differing duplicate evidence lacks the new fail-closed reason;
3. a successful analyzer invocation captures empty stdout.

The new Appendix B must make the valid shared fixture and deterministic stdout
GREEN while continuing to reject the corrupted duplicate evidence. Static
self-checks freeze the narrow alias predicate, both evidence checks, and the
summary fields.

## 5. Identity cascade

- Appendix A: unchanged
- Appendix B: refreeze after final fence bytes
- Appendix C: unchanged
- Appendix R: unchanged
- base spec: edited; raw SHA-256 and no-filter Git blob must be refrozen in all
  directive consumers
- a new `SPEC_REVIEW_APPROVED` token is required after commit because the base
  spec identity changed

## 6. Allowed files and stop boundary

Only the seven user-approved paths may change. In particular,
`scripts/provenance_controller.ps1`, Appendix A, workbook, tracked YAML,
`src/mmi_converter`, capsule generator, campaign roots, and existing unrelated
untracked files are immutable. A need to change controller or Appendix A is an
immediate STOP for independent review.

## 7. Qualification

Final qualification records the RED/GREEN evidence, Appendix hashes, base-spec
identity, selfcheck/selftest/dispatch counts, exact changed paths, immutable
hash/diff checks, and unstaged Git state. No campaign execution is part of this
amendment.

Measured qualification:

- RED behavior: `3 failed, 76 deselected`; RED selfcheck: only C9h/C9i failed
- GREEN behavior: `3 passed, 76 deselected`
- static selfcheck: `40/40 GREEN`
- controller runtime selftest: `S1-S17 GREEN`
- dispatch regression: `79 passed` under Windows PowerShell 5.1 outer process
- Appendix A/B/C/R SHA-256:
  `f6e046c74f1b002bfe05d15788ccef4693015df7bd2e774ae20db60fdcb7b2aa`,
  `516feffaa4522ba67d1864c5467ce7ff45505d9c8efb9b126d9d988dfbc0a267`,
  `6182cbaa8962d43965e3b34eebfd600a19d1bd7410b7e4e70b2630fb75f0cc54`,
  `d57734b2131cfaf548c28c68d1febbbada6236e49ed8aa21474351f3067f7e64`
- base-spec raw SHA-256/no-filter blob:
  `af800c57d81f25b3419e51d522247f83956858b57f2d14157e546bd5a6e48ef6` /
  `bc63b8f69f1fc79757adb41f7f43600491b67f00`

The base-spec change invalidates the prior review token. A new
`SPEC_REVIEW_APPROVED` token is required after commit; prior capsules are not
reusable.
