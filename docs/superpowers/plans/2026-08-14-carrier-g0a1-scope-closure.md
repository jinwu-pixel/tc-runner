# Carrier G0-A.1 Scope Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 214개 이통3사 corpus 파일을 ACTIVE/EXCLUDED/PENDING_REVIEW로 전수 분류하고, 전건 SHA-256 closure와 기존 ACTIVE 72개 G0-A artifact를 하나의 fail-closed consistency set으로 검증한다.

**Architecture:** `source_scope_v2.yaml`은 사람이 관리하는 분류 계약이고 `corpus_closure_v1.json`은 그 계약과 214개 파일 bytes를 결박하는 기계 생성 원장이다. 새 strict scope loader가 구조를 검증하고, closure builder가 filesystem set·근거·hash를 검증하며, 기존 registry/relations/checker는 v2 ACTIVE subset과 closure snapshot을 소비한다.

**Tech Stack:** Python 3, PyYAML, stdlib `hashlib/json/pathlib/tempfile/shutil`, pytest, Draft 2020-12 JSON Schema 문서 계약

**Spec:** `docs/superpowers/specs/2026-08-14-carrier-g0a1-scope-closure-design.md`

## Global Constraints

- corpus 원본 214개를 이동·rename·삭제·수정하지 않는다.
- dependency를 추가하지 않는다. `jsonschema` 없는 project venv에서 동작해야 한다.
- 모든 stored path는 exact repo-relative POSIX literal이며 glob expansion을 사용하지 않는다.
- 신규 215번째 파일은 자동 PENDING 처리하지 않고 `SCOPE_UNCLASSIFIED`로 실패한다.
- 기존 `source_registry_v1.json`, `source_relations_v1.json`, `skt_workbook_inventory_v1.json`, `lgu_legacy_expected_ledger_v1.json` bytes를 최초 cutover에서 보존한다.
- checker는 Excel COM, QCAT, ADB, network를 호출하지 않는다.
- 자동 테스트는 synthetic fixture corpus만 사용한다.
- 편집은 승인된 KR3와 본 plan/spec 경로로 한정하며 staging·commit·push하지 않는다.

## Status alignment (2026-09-03)

- 2026-08-14 구현·RED/GREEN·cutover 근거: `KR3_Carrier_Requirements/G0A1_SCOPE_CLOSURE_REPORT_2026-08-14.md` §1·§3·§4.
- fresh acceptance: KR3 selector `251 passed, 4 skipped`; checker repo root 2회와 arbitrary CWD 1회 모두 exit 0, `corpus_parent_entries=9/9`, `byte_drift=0 source_mutation=0`.
- 2026-08-14의 parent 7-entry seed는 당시 완료된 단계이며, 2026-09-03 hardening에서 contract·checker·test 이중 pin을 9로 함께 승격했다.

---

### Task 1: Strict Source Scope v2 Contract

**Files:**
- Create: `KR3_Carrier_Requirements/tools/source_scope_v2.py`
- Create: `KR3_Carrier_Requirements/contracts/source_scope_schema_v2.json`
- Create: `KR3_Carrier_Requirements/tests/test_source_scope_v2.py`

**Interfaces:**
- Produces: `load_scope(path: Path, *, as_of: date | None = None) -> dict[str, object]`
- Produces: `active_documents(scope: dict) -> list[dict]`
- Produces: `currentness_evidence_paths(scope: dict) -> list[str]`
- Consumes: `G0AError` and repo-relative POSIX path rules from `g0a_common.py`

- [x] **Step 1: Write strict-loader RED tests**

```python
def test_scope_v2_accepts_literal_brackets_and_rejects_new_document_automation(tmp_path):
    scope = minimal_scope("corpus/[SKT-5G-001] requirement.pdf")
    loaded = load_scope(write_scope(tmp_path, scope), as_of=date(2026, 8, 14))
    assert loaded["documents"][0]["path"].endswith("[SKT-5G-001] requirement.pdf")

@pytest.mark.parametrize("raw", [DUPLICATE_KEY, YAML_ALIAS, CUSTOM_TAG, NON_STRING_PATH])
def test_scope_v2_rejects_unsafe_yaml_as_controlled_scope_invalid(tmp_path, raw):
    with pytest.raises(G0AError) as caught:
        load_scope(write_raw(tmp_path, raw), as_of=date(2026, 8, 14))
    assert caught.value.code == "SCOPE_INVALID"
```

- [x] **Step 2: Run RED**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_scope_v2.py -q`

Expected: collection/import failure because `source_scope_v2` does not exist.

- [x] **Step 3: Implement the strict loader and schema**

Implement a PyYAML SafeLoader subclass that rejects duplicate keys, aliases, merge keys and custom tags; remove implicit timestamp conversion so `recorded_date` remains a validated string. Validate exact top-level keys, parent/root shape, state-specific exact keys, currentness evidence, relations, external gaps, ID uniqueness and path canonicality.

- [x] **Step 4: Run GREEN and schema contract tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_scope_v2.py -q`

Expected: all Task 1 tests pass.

### Task 2: Corpus Closure Builder

**Files:**
- Create: `KR3_Carrier_Requirements/tools/build_corpus_closure.py`
- Create: `KR3_Carrier_Requirements/contracts/corpus_closure_schema_v1.json`
- Create: `KR3_Carrier_Requirements/tests/test_corpus_closure.py`

**Interfaces:**
- Consumes: `load_scope()` from Task 1
- Produces: `build_closure(repo_root: Path, scope_path: Path, *, as_of: date | None = None) -> dict`
- Produces: `validate_stored_closure(value: object) -> dict`
- Produces: `closure_source_state(closure: dict, repo_root: Path) -> dict[str, tuple[str, int]]`

- [x] **Step 1: Write filesystem closure RED tests**

```python
def test_new_215th_file_is_unclassified_not_auto_pending(fixture_repo):
    fixture_repo.write("corpus/extra.pdf", b"new")
    with pytest.raises(G0AError) as caught:
        build_closure(fixture_repo.root, fixture_repo.scope, as_of=DATE)
    assert caught.value.code == "SCOPE_UNCLASSIFIED"

def test_pending_content_is_full_hash_bound(fixture_repo):
    first = build_closure(fixture_repo.root, fixture_repo.scope, as_of=DATE)
    fixture_repo.write("corpus/pending.pdf", b"changed")
    second = build_closure(fixture_repo.root, fixture_repo.scope, as_of=DATE)
    assert first["documents"] != second["documents"]
```

- [x] **Step 2: Run RED**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_corpus_closure.py -q`

Expected: import failure because `build_corpus_closure` does not exist.

- [x] **Step 3: Implement secure enumeration and closure generation**

Validate parent entry names/kinds, four non-overlapping roots, recursive regular-file sets, symlink/junction ancestry, root totals, state evidence, DUPLICATE hash equality, SUPERSEDED ACTIVE target and CURRENT evidence hashes. Emit sorted canonical closure entries and stable summary; compute max pending age only for CLI output.

- [x] **Step 4: Run GREEN**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_corpus_closure.py -q`

Expected: all Task 2 tests pass, including arbitrary CWD and controlled exit 2.

### Task 3: ACTIVE Registry and Relation Adapter

**Files:**
- Modify: `KR3_Carrier_Requirements/tools/build_source_registry.py`
- Modify: `KR3_Carrier_Requirements/tools/build_source_relations.py`
- Rewrite: `KR3_Carrier_Requirements/tests/test_source_registry.py`
- Modify: `KR3_Carrier_Requirements/tests/test_source_relations.py`

**Interfaces:**
- Consumes: `build_closure()` and `active_documents()`
- Produces: unchanged `build_registry(repo_root: Path, scope_path: Path) -> dict` artifact shape
- Produces: unchanged `build_relations(scope: dict, registry: dict) -> dict` artifact shape

- [x] **Step 1: Write RED tests for v2 ACTIVE-only behavior**

```python
def test_registry_contains_only_active_documents_and_never_uses_previous_ids(fixture_repo):
    registry = build_registry(fixture_repo.root, fixture_repo.scope)
    assert [item["document_id"] for item in registry["documents"]] == ["ACTIVE_REQ"]

def test_relation_endpoint_must_be_active(scope, registry):
    scope["relations"][0]["target_document_id"] = "PENDING_DOC"
    with pytest.raises(G0AError) as caught:
        build_relations(scope, registry)
    assert caught.value.code == "RELATION_ENDPOINT_NOT_ACTIVE"
```

- [x] **Step 2: Run RED**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_registry.py KR3_Carrier_Requirements/tests/test_source_relations.py -q`

Expected: failures from v1 discovery assumptions and missing ACTIVE endpoint gate.

- [x] **Step 3: Replace discovery logic with explicit ACTIVE projection**

Keep registry schema/output byte format unchanged. Use explicit v2 document IDs, closure size/hash values, and existing media probe behavior. Remove previous-registry ID allocation and discovery expansion from the active build path.

- [x] **Step 4: Run GREEN**

Run: same focused selector. Expected: all Task 3 tests pass.

### Task 4: Checker Consistency-Set Integration

**Files:**
- Modify: `KR3_Carrier_Requirements/tools/check_g0a.py`
- Modify: `KR3_Carrier_Requirements/tests/test_check_g0a.py`

**Interfaces:**
- Adds tracked artifact `corpus_closure_v1.json` to `ARTIFACT_NAMES` and `REBUILT_ARTIFACT_NAMES`
- Changes `check_all(repo_root, artifact_dir, *, as_of: date | None = None) -> dict`
- Adds CLI `--as-of YYYY-MM-DD`

- [x] **Step 1: Write RED tests for all-source snapshot and reporting**

```python
def test_checker_snapshots_pending_sources_and_rejects_their_mutation(repo):
    pending = repo.path("corpus/pending.pdf")
    install_valid_artifacts(repo)
    mutate_during_rebuild(pending)
    with pytest.raises(G0AError) as caught:
        check_all(repo.root, repo.artifacts, as_of=DATE)
    assert caught.value.code == "SOURCE_MUTATION"

def test_summary_reports_scope_closure_counts(repo):
    counts = check_all(repo.root, repo.artifacts, as_of=DATE)
    assert counts["corpus_total"] == 214
    assert counts["corpus_unclassified"] == 0
```

- [x] **Step 2: Run RED**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_check_g0a.py -q`

Expected: failures for missing closure artifact, v1 scope path and missing counts.

- [x] **Step 3: Implement snapshot/rebuild/count integration**

Load closure canonically; obtain before/after source state from all closure entries; snapshot all 214 corpus files plus scope/schema/evidence; recreate non-corpus parent names/kinds without copying their contents; rebuild closure/registry/relations/ledger only from read-only snapshots; compare canonical artifact bytes; retain stored SKT inventory validation without COM.

- [x] **Step 4: Run GREEN**

Run: focused checker selector. Expected: all Task 4 tests pass.

### Task 5: Real Scope, Closure Artifact and Documentation Cutover

**Files:**
- Create: `KR3_Carrier_Requirements/contracts/source_scope_v2.yaml`
- Create: `KR3_Carrier_Requirements/catalog/corpus_closure_v1.json`
- Modify: `KR3_Carrier_Requirements/README.md`
- Preserve: `KR3_Carrier_Requirements/contracts/source_scope_v1.yaml`
- Preserve bytes: the four existing G0-A catalog artifacts

**Interfaces:**
- Consumes existing registry document IDs for the 72 ACTIVE entries exactly once during initial seed
- Produces exact 214-entry source scope and canonical closure artifact

- [x] **Step 1: Record existing artifact hashes and 214-source before state**

Run read-only SHA-256/mtime snapshot commands and save the measured values in the execution report, not in corpus files.

- [x] **Step 2: Seed the explicit v2 scope**

Emit the existing registry 72 as ACTIVE and the remaining 142 as PENDING_REVIEW with `INTERNAL_DECISION`, `2026-08-14`, and `CURRENTNESS_UNVERIFIED`; include exact 7 parent entries, root totals, three relations and external gaps.

- [x] **Step 3: Build closure and prove existing artifact byte identity**

Run the closure builder, registry builder and relation builder to temporary candidate paths. Compare registry and relations to tracked bytes before installing only the new closure artifact.

- [x] **Step 4: Update README commands and honest status vocabulary**

Document 214 corpus/72 ACTIVE distinction, 142 pending, closure builder, `--as-of`, synthetic-test boundary and G0-A.1 internal consistency wording.

### Task 6: Acceptance and Blast-Radius Audit

**Files:**
- Verify all files above; no new production changes before evidence is read.

- [x] **Step 1: Run focused suites**

Run scope, closure, registry, relations and checker test modules separately. Expected: zero failures.

- [x] **Step 2: Run full KR3 selector**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q`

Expected: zero failures; platform-only symlink skips explicitly reported.

- [x] **Step 3: Run real checker twice and from arbitrary CWD**

Run with `--as-of 2026-08-14` from repo root twice and `C:\` once. Expected identical counts, byte drift 0 and source mutation 0.

- [x] **Step 4: Recheck source and legacy artifact hashes**

Compare all 214 `(sha256, mtime_ns)` and four pre-cutover artifact SHA-256 values with Step 1. Expected exact equality.

- [x] **Step 5: Audit exact changed paths**

Use `git status --short`, `git diff -- <exact paths>` and explicit untracked enumeration. Confirm no corpus, dependency, AGENTS, staging, commit or other-repo changes.
