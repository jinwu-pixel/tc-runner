# Carrier G0-A.2 Resolver Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** G0-A.1의 PENDING_REVIEW 142건에 대해 관측 가능한 속성만으로 resolver proposal을 생성하고, 사람이 반영한 scope와 proposal을 하나의 fail-closed consistency set으로 검증한다.

**Architecture:** `resolver_proposal_v1.json`은 closure 전체의 hash/extension에서 계산한 기계 제안이며 scope를 수정하지 않는다. 새 builder는 proposal 생성·저장형 검증을 담당하고, `check_g0a.py`는 proposal을 필수 artifact로 snapshot/rebuild하여 stale·set·basis·canonical byte drift를 검사한다. 실제 cutover는 baseline proposal 생성, scope 수기 반영, closure 재생성, 최종 proposal 재생성 순서로 수행한다.

**Tech Stack:** Python 3, stdlib `collections/hashlib/json/pathlib`, pytest, Draft 2020-12 JSON Schema 문서 계약

**Spec:** `docs/superpowers/specs/2026-08-14-carrier-g0a2-resolver-assignment-design.md`

## Global Constraints

- 배정 우선순위는 SHA256 duplicate → non-document `.ai/.png` → unsupported `.doc/.docx/.zip` → normativity unknown 순서다.
- proposal builder는 `source_scope_v2.yaml`을 쓰거나 resolver를 자동 반영하지 않는다.
- proposal/scope의 `blocked_on` 불일치는 허용한다. proposal 자체의 basis/resolver/evidence drift만 실패한다.
- `recorded_date=2026-08-14`, corpus 상태 72/0/142, corpus 214건 bytes/mtime, 기존 G0-A artifact 4건 bytes를 보존한다.
- 자동 테스트는 synthetic fixture만 사용한다.
- dependency, AGENTS, corpus, 다른 repo, shell-RC 트랙을 변경하지 않는다.
- staging, commit, push를 수행하지 않는다.

## Status alignment (2026-09-03)

- 2026-08-14 구현·RED/GREEN·cutover 근거: `KR3_Carrier_Requirements/G0A2_RESOLVER_ASSIGNMENT_REPORT_2026-08-14.md`의 계약과 반영 경계·Cutover 증거·자동 검증 경계.
- fresh acceptance: KR3 selector `251 passed, 4 skipped`; checker 3회 모두 exit 0이며 resolver `112/22/8`, proposal basis `112/17/8/5`, duplicate `8 groups/17 members`가 일치했다.
- 2026-09-03 parent hardening은 proposal 의미·214-document closure를 바꾸지 않았고 closure/scope hash pin만 재생성했다.

---

### Task 1: Resolver Proposal Builder and Stored Contract

**Files:**
- Create: `KR3_Carrier_Requirements/tools/build_resolver_proposal.py`
- Create: `KR3_Carrier_Requirements/contracts/resolver_proposal_schema_v1.json`
- Create: `KR3_Carrier_Requirements/tests/test_resolver_proposal.py`

**Interfaces:**
- Consumes: validated closure v1 dictionaries and exact closure/scope SHA-256 values
- Produces: `build_proposal(closure: dict, *, closure_sha256: str, source_scope_sha256: str) -> dict`
- Produces: `build_proposal_from_paths(closure_path: Path, scope_path: Path) -> dict`
- Produces: `validate_stored_proposal(value: object, closure: dict, *, closure_sha256: str, source_scope_sha256: str) -> dict`
- Produces: controlled CLI `main(argv: list[str] | None = None) -> int`

- [x] **Step 1: Write rule and priority RED tests**

Create literal synthetic closure entries for each basis and assert:

```python
assert by_path["corpus/duplicate.zip"]["basis"] == "SHA256_DUPLICATE_IN_CORPUS"
assert by_path["corpus/artwork.AI"]["basis"] == "NON_DOCUMENT_ASSET"
assert by_path["corpus/manual.DoCx"]["basis"] == "UNSUPPORTED_MEDIA"
assert by_path["corpus/spec.PDF"]["basis"] == "NORMATIVITY_UNKNOWN"
```

Include one three-member hash group and one ACTIVE↔PENDING identical-hash pair. Assert duplicate evidence contains every closure path in UTF-8 byte order while `duplicate_member_count` counts proposal members with duplicate basis.

- [x] **Step 2: Run RED**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_resolver_proposal.py -q
```

Expected: collection error because `build_resolver_proposal` does not exist.

- [x] **Step 3: Implement minimal pure builder**

Keep extension sets in module constants. Group every closure document by lowercase full SHA-256, classify only PENDING_REVIEW entries with first-match priority, and emit proposals sorted by `path.encode("utf-8")`. Build summary with exact keys:

```python
{
    "total": len(proposals),
    "by_resolver": {resolver: ...},
    "by_basis": {basis: ...},
    "duplicate_group_count": ...,
    "duplicate_member_count": ...,
    "roots": {root: {"by_resolver": {...}}},
}
```

- [x] **Step 4: Add stored validation RED tests**

Mutate one fixture at a time and assert exact codes: malformed keys/evidence → `PROPOSAL_INVALID`; either input hash → `PROPOSAL_STALE`; pending path add/remove → `PROPOSAL_SET_MISMATCH`; basis/resolver/evidence manipulation → `PROPOSAL_BASIS_DRIFT`. Assert proposal/scope resolver mismatch is not consulted by this validator.

- [x] **Step 5: Implement strict stored validator and canonical CLI**

Validate exact key sets, enums, lowercase SHA-256, sorted unique paths, conditional evidence, summary recomputation and proposal regeneration. `build_proposal_from_paths` must reject noncanonical/duplicate-key/nonfinite JSON, verify closure `source_scope_sha256`, and hash the exact canonical closure/scope bytes. CLI writes through `g0a_common.write_json` and returns controlled exit 2 without traceback for every G0AError/OSError/Unicode/JSON failure.

- [x] **Step 6: Run Task 1 GREEN**

Run the Task 1 selector from repo root and `C:\`; assert deterministic byte identity across two writes and source scope bytes/mtime unchanged.

### Task 2: Checker Consistency-Set Integration

**Files:**
- Modify: `KR3_Carrier_Requirements/tools/check_g0a.py`
- Modify: `KR3_Carrier_Requirements/tests/test_check_g0a.py`

**Interfaces:**
- Adds required `resolver_proposal_v1.json` to `ARTIFACT_NAMES` and `REBUILT_ARTIFACT_NAMES`
- Extends `summarize(..., proposal: dict, ...)` with proposal basis/duplicate counts
- Rebuilds proposal from snapshot closure and snapshot scope bytes

- [x] **Step 1: Write checker integration RED tests**

Extend the synthetic real-shape fixture to install a proposal. Assert missing/malformed proposal is controlled, stale closure/scope hash is `PROPOSAL_STALE`, path-set drift is `PROPOSAL_SET_MISMATCH`, basis drift is `PROPOSAL_BASIS_DRIFT`, and rebuilt bytes drift is `ARTIFACT_BYTE_DRIFT`.

- [x] **Step 2: Write automatic-assignment prohibition RED tests**

Set a scope PENDING document resolver different from its proposal resolver while keeping closure consistent; checker must exit 0. Hash scope before/after proposal generation and assert equality. Add an undeclared corpus file and assert `SCOPE_UNCLASSIFIED` occurs before proposal can absorb it.

- [x] **Step 3: Run RED**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_check_g0a.py -q
```

Expected: failures for missing proposal artifact/validator/output and old resolver counts.

- [x] **Step 4: Integrate proposal as a required snapshot artifact**

Load proposal as strict canonical JSON, validate its two hash pins against current tracked closure and scope, copy tracked bytes into the existing temporary consistency set, rebuild proposal from `rebuilt_closure` plus snapshot scope bytes, and compare all rebuilt artifact bytes. Do not add any scope write path.

- [x] **Step 5: Add resolver acceptance and CLI output**

Add exact expected resolver counts 112/22/8, proposal basis 112/17/8/5, duplicate groups 8 and members 17. Print the two specified lines in stable enum order.

- [x] **Step 6: Run Task 2 GREEN**

Run focused checker tests. Confirm all existing G0-A.1 mutation, junction, arbitrary-CWD and README tests remain green.

### Task 3: Real Scope Cutover and Canonical Artifacts

**Files:**
- Modify: `KR3_Carrier_Requirements/contracts/source_scope_v2.yaml`
- Modify: `KR3_Carrier_Requirements/catalog/corpus_closure_v1.json`
- Create: `KR3_Carrier_Requirements/catalog/resolver_proposal_v1.json`
- Preserve bytes: `source_registry_v1.json`, `source_relations_v1.json`, `skt_workbook_inventory_v1.json`, `lgu_legacy_expected_ledger_v1.json`

**Interfaces:**
- Uses Task 1 builder to generate a review proposal and final hash-bound proposal
- Applies only `documents[].blocked_on` for PENDING_REVIEW records; `recorded_date` and every other field remain byte-semantic equivalents

- [x] **Step 1: Record pre-cutover state**

Record 214 source `(sha256, mtime_ns)`, total bytes, scope hash, closure hash and the four preserved artifact hashes/sizes.

- [x] **Step 2: Generate and inspect baseline proposal**

Build to a temporary path from current G0-A.1 closure/scope. Independently count 142 proposals, resolver 112/22/8, basis 112/17/8/5, duplicate groups 8/members 17 and root totals. Keep the scope hash/mtime unchanged.

- [x] **Step 3: Apply reviewed resolver assignments**

Use an exact `apply_patch` generated from the reviewed proposal to change only PENDING `blocked_on` scalars. Verify a structural before/after comparison permits only `blocked_on`, keeps 142 `recorded_date` values at `2026-08-14`, and preserves ACTIVE/EXCLUDED/PENDING counts.

- [x] **Step 4: Rebuild closure and final proposal**

Write the new canonical closure, then regenerate proposal so its `closure_sha256` and `source_scope_sha256` pin the final files. Build proposal twice to temporary outputs and require byte identity before installing the reviewed candidate.

- [x] **Step 5: Prove preserved artifacts and corpus state**

Rebuild registry/relations to temporary paths and compare bytes; rehash inventory/ledger; recompute all 214 source hashes/mtimes. Any difference stops the task.

### Task 4: Documentation and Contract Alignment

**Files:**
- Modify: `KR3_Carrier_Requirements/README.md`
- Create: `KR3_Carrier_Requirements/G0A2_RESOLVER_ASSIGNMENT_REPORT_2026-08-14.md`
- Modify: `docs/superpowers/specs/2026-08-14-carrier-g0a1-scope-closure-design.md`

**Interfaces:**
- Documents proposal build/check commands, resolver counts, proposal/scope mismatch semantics and non-claims

- [x] **Step 1: Update README and execution report**

Document the required proposal artifact, builder CLI, checker output, two-stage regeneration order, synthetic fixture boundary and completion vocabulary `G0-A.2 resolver 배정 내부 정합 + 회귀 고정`.

- [x] **Step 2: Remove the G0-A.1 path-contract prose drift**

Replace the stale “glob 거부” phrase with the actual contract: reject absolute/backslash/dot/dot-dot/noncanonical paths; perform no glob expansion; treat wildcard metacharacters, including brackets, as literal stored path characters.

### Task 5: Acceptance and Blast-Radius Audit

**Files:**
- Verify every file above; make no production edits after fresh evidence is collected.

- [x] **Step 1: Run focused suites**

Run proposal and checker test modules independently; require zero failures and record platform skips.

- [x] **Step 2: Run full explicit selector**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q -rs
```

- [x] **Step 3: Run real checker twice and from arbitrary CWD**

Use `--as-of 2026-08-14`; require identical output, `byte_drift=0`, `source_mutation=0`, resolver 112/22/8 and proposal basis 112/17/8/5.

- [x] **Step 4: Recheck deterministic and preservation evidence**

Rehash proposal outputs, final scope/closure bindings, corpus content/mtime manifests and the four G0-A artifacts. Compare with Task 3 baseline.

- [x] **Step 5: Audit exact changed paths**

Confirm G0-A.2 exact-path changes only, staged diff empty, tracked 19-file shell-RC/provenance state unchanged, no cache/temp contamination under protected directories, and no dependency/AGENTS/corpus/other-repo changes.
