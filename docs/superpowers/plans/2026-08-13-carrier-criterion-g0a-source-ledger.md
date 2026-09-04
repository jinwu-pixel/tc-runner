# Carrier Criterion G0-A Source Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, read-only source intake and immutable ledger for LGU+, SKT, and KT carrier artifacts without changing the existing STAGE1 or runner behavior.

**Architecture:** A tracked scope contract declares explicit LGU+/KT documents and the SKT legacy-XLS discovery set. Focused standard-library tools build a full-SHA source registry, validate requirement↔procedure/SAT relations, and freeze all 232 LGU legacy expected items behind immutable IDs; a final checker rebuilds every artifact in a temporary directory and compares bytes. G0-A does not parse business meaning, compile procedures, call a device, or claim that an `.xls` workbook was semantically parsed when only its OLE container was probed.

**Tech Stack:** Python 3, PyYAML already present in `venv`, Python standard library (`argparse`, `hashlib`, `json`, `pathlib`, `tempfile`), pytest, JSON/YAML contracts.

**Spec:** `docs/superpowers/specs/2026-08-13-carrier-criterion-projection-g0-design.md`

## Global Constraints

- G0-A is one independently reviewable slice; G0-B criterion migration, G0-C projection, and G0-D cutover each require a separate implementation plan.
- Source documents under `새 폴더 (2)/` are read-only. Any source SHA-256 or mtime change is a hard failure.
- Stored paths are repo-root-relative POSIX paths. Absolute paths, drive letters, `..`, and paths outside the repo are rejected.
- Stored SHA-256 values are full 64-character lowercase hexadecimal strings.
- All JSON outputs use UTF-8, lexically sorted keys, two-space indentation, and one terminal newline.
- Existing `spec_corpus_index.py`, STAGE1 files, prompts, schema, runner, and `project_runnable.py` behavior remain unchanged.
- No new dependency is added in G0-A. `.xls` semantic parsing is not claimed; OLE/CFB readability is recorded separately from parser availability.
- SKT intake must account for exactly 66 `.xls` files in `새 폴더 (2)/SKT_시험절차서_최신/`.
- LGU legacy expected intake must account for exactly 28 cases and 232 expected entries.
- KT relation fixtures are the exact NSA V1.3.0 and SA V1.6.0 requirement↔SAT pairs named in the spec.
- Do not commit or push during execution without a new explicit user instruction. Exact-path staging and commit commands below are conditional handoff boundaries only.
- Preserve all pre-existing tracked and untracked workspace changes; never use broad `git add`.

## Status alignment (2026-09-03)

- checked 항목 근거: `KR3_Carrier_Requirements/G0A1_SCOPE_CLOSURE_REPORT_2026-08-14.md` §1·§3·§4, `G0A2_RESOLVER_ASSIGNMENT_REPORT_2026-08-14.md`의 Cutover 증거·자동 검증 경계, 그리고 2026-09-03 fresh KR3/checker/구조 gate 결과.
- 과거 v1 RED transcript를 직접 가리키는 파일·커밋·보고서 절이 없는 RED 단계와 conditional commit-boundary 단계는 소급 추정하지 않고 열어 둔다.
- AGENTS 정책 편집은 수행하지 않았고, 최종 사용자 review/commit gate도 열려 있다.

## File Structure

Create these focused files:

- `KR3_Carrier_Requirements/contracts/source_scope_v1.yaml` — declared document sets, roles, expected counts, and source relations.
- `KR3_Carrier_Requirements/contracts/source_registry_schema_v1.json` — registry output contract.
- `KR3_Carrier_Requirements/contracts/source_relations_schema_v1.json` — relation output contract.
- `KR3_Carrier_Requirements/contracts/legacy_expected_ledger_schema_v1.json` — legacy expected identity contract.
- `KR3_Carrier_Requirements/tools/g0a_common.py` — canonical serialization, SHA-256, path containment, and fail-closed exceptions.
- `KR3_Carrier_Requirements/tools/build_source_registry.py` — scope loading, source discovery, media probing, and source registry build.
- `KR3_Carrier_Requirements/tools/build_source_relations.py` — relation materialization and role/reference checks.
- `KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py` — 232-entry freeze and drift detection.
- `KR3_Carrier_Requirements/tools/check_g0a.py` — temporary rebuild, byte comparison, count invariants, and source immutability audit.
- `KR3_Carrier_Requirements/tests/conftest.py` — exposes only the KR3 tools directory to focused tests.
- `KR3_Carrier_Requirements/tests/test_g0a_common.py` — common primitive tests.
- `KR3_Carrier_Requirements/tests/test_source_registry.py` — registry and `.xls` probe tests.
- `KR3_Carrier_Requirements/tests/test_source_relations.py` — source-pair relation tests.
- `KR3_Carrier_Requirements/tests/test_legacy_expected_ledger.py` — immutable expected-ID tests.
- `KR3_Carrier_Requirements/tests/test_check_g0a.py` — end-to-end fail-closed checker tests.

Generate and track these deterministic artifacts:

- `KR3_Carrier_Requirements/catalog/source_registry_v1.json`
- `KR3_Carrier_Requirements/catalog/source_relations_v1.json`
- `KR3_Carrier_Requirements/catalog/lgu_legacy_expected_ledger_v1.json`

Modify only for documentation alignment:

- `KR3_Carrier_Requirements/README.md`
- `AGENTS.md` §5.4/§5.6/§8.2, only after the execution turn confirms approval for the policy-file edit.

---

### Task 1: Canonical and Path-Safety Primitives

**Files:**

- Create: `KR3_Carrier_Requirements/tools/g0a_common.py`
- Create: `KR3_Carrier_Requirements/tests/conftest.py`
- Create: `KR3_Carrier_Requirements/tests/test_g0a_common.py`

**Interfaces:**

- Produces: `G0AError(code: str, detail: str)`.
- Produces: `canonical_json_bytes(value: object) -> bytes`.
- Produces: `sha256_bytes(data: bytes) -> str` and `sha256_file(path: Path) -> str`.
- Produces: `resolve_repo_relative(repo_root: Path, raw_path: str) -> Path`.
- Produces: `write_json(path: Path, value: object) -> None`.

- [ ] **Step 1: Write failing canonicalization and path-containment tests**

First create the focused import boundary:

```python
from __future__ import annotations

import sys
from pathlib import Path

import pytest


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
```

```python
from pathlib import Path

import pytest

from g0a_common import G0AError, canonical_json_bytes, resolve_repo_relative, sha256_bytes


def test_canonical_json_is_stable_and_hashes_full_lowercase() -> None:
    payload = {"b": 2, "a": 1}
    assert canonical_json_bytes(payload) == b'{"a":1,"b":2}'
    assert sha256_bytes(canonical_json_bytes(payload)) == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


@pytest.mark.parametrize("raw", [r"C:\\outside\\a.xls", "../a.xls", "/tmp/a.xls"])
def test_repo_relative_path_rejects_escape(tmp_path: Path, raw: str) -> None:
    with pytest.raises(G0AError, match="PATH_OUTSIDE_REPO"):
        resolve_repo_relative(tmp_path, raw)
```

- [ ] **Step 2: Run the focused tests and confirm the missing-module failure**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_g0a_common.py -q
```

Expected: collection fails because `g0a_common` does not exist.

- [x] **Step 3: Implement the minimal deterministic primitives**

```python
class G0AError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_repo_relative(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or candidate.drive or ".." in candidate.parts:
        raise G0AError("PATH_OUTSIDE_REPO", raw_path)
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise G0AError("PATH_OUTSIDE_REPO", raw_path)
    return resolved
```

`write_json` must implement the following exact formatting; `sha256_file` must stream fixed-size
binary chunks and never open a source file for writing.

```python
def write_json(path: Path, value: object) -> None:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(rendered, encoding="utf-8", newline="\n")
```

- [x] **Step 4: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_g0a_common.py -q`

Expected: all tests pass.

- [ ] **Step 5: Review the conditional commit boundary**

Exact paths only:

```powershell
git add KR3_Carrier_Requirements/tools/g0a_common.py KR3_Carrier_Requirements/tests/test_g0a_common.py
git diff --cached --name-only
```

Expected staged list: exactly the three files above. Do not run `git commit` without explicit approval; the eventual message is `feat(kr3): add deterministic G0-A primitives`.

### Task 2: Scope Contract and Source Registry Builder

**Files:**

- Create: `KR3_Carrier_Requirements/contracts/source_scope_v1.yaml`
- Create: `KR3_Carrier_Requirements/contracts/source_registry_schema_v1.json`
- Create: `KR3_Carrier_Requirements/tools/build_source_registry.py`
- Create: `KR3_Carrier_Requirements/tests/test_source_registry.py`

**Interfaces:**

- Consumes: `G0AError`, `resolve_repo_relative`, `sha256_file`, and `write_json` from Task 1.
- Produces: `load_scope(path: Path) -> dict[str, object]`.
- Produces: `probe_media(path: Path, media_type: str) -> dict[str, object]`.
- Produces: `build_registry(repo_root: Path, scope_path: Path, previous: dict | None) -> dict`.
- CLI: `build_source_registry.py --repo-root PATH --scope PATH --out PATH [--previous PATH]`.

- [ ] **Step 1: Write failing discovery, full-hash, OLE-probe, and deterministic-ID tests**

```python
OLE_CFB = bytes.fromhex("d0cf11e0a1b11ae1")


def write_scope(tmp_path: Path, expected_count: int) -> Path:
    scope = tmp_path / "scope.yaml"
    scope.write_text(
        yaml.safe_dump({
            "schema_version": 1,
            "explicit_documents": [],
            "discoveries": [{
                "discovery_id": "SKT_TEST",
                "carrier": "SKT",
                "role": "PROCEDURE",
                "media_type": "application/vnd.ms-excel",
                "base_path": "corpus/SKT",
                "glob": "*.xls",
                "expected_count": expected_count,
                "id_prefix": "SKT_PROC_",
                "id_width": 4,
            }],
            "relations": [],
        }, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return scope


def test_registry_discovers_expected_xls_and_records_honest_probe(tmp_path: Path) -> None:
    source = tmp_path / "corpus" / "SKT"
    source.mkdir(parents=True)
    (source / "b.xls").write_bytes(OLE_CFB + bytes(504))
    (source / "a.xls").write_bytes(OLE_CFB + bytes(504))
    scope = write_scope(tmp_path, expected_count=2)

    registry = build_registry(tmp_path, scope, previous=None)

    assert [d["document_id"] for d in registry["documents"]] == [
        "SKT_PROC_0001",
        "SKT_PROC_0002",
    ]
    assert registry["documents"][0]["intake"]["container_status"] == "READABLE"
    assert registry["documents"][0]["intake"]["semantic_parse_status"] == "NOT_ATTEMPTED"
    assert len(registry["documents"][0]["sha256"]) == 64


def test_registry_fails_closed_on_expected_count_mismatch(tmp_path: Path) -> None:
    scope = write_scope(tmp_path, expected_count=66)
    with pytest.raises(G0AError, match="DISCOVERY_COUNT_MISMATCH"):
        build_registry(tmp_path, scope, previous=None)
```

Add these exact regression cases in the same file:

```python
def test_previous_registry_preserves_ids_and_rename_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "corpus/SKT"
    source.mkdir(parents=True)
    original = source / "a.xls"
    original.write_bytes(OLE_CFB + bytes(504))
    scope = write_scope(tmp_path, expected_count=1)
    previous = build_registry(tmp_path, scope, previous=None)
    assert previous["documents"][0]["document_id"] == "SKT_PROC_0001"
    original.rename(source / "renamed.xls")
    with pytest.raises(G0AError, match="SOURCE_SET_DRIFT"):
        build_registry(tmp_path, scope, previous=previous)


def test_invalid_xls_is_unreadable_and_two_builds_are_identical(tmp_path: Path) -> None:
    source = tmp_path / "corpus/SKT"
    source.mkdir(parents=True)
    (source / "a.xls").write_bytes(b"not-an-ole-workbook")
    scope = write_scope(tmp_path, expected_count=1)
    first = build_registry(tmp_path, scope, previous=None)
    second = build_registry(tmp_path, scope, previous=first)
    assert first["documents"][0]["intake"]["container_status"] == "UNREADABLE"
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_registry.py -q`

Expected: collection fails because `build_source_registry` does not exist.

- [x] **Step 3: Define the exact source scope**

```yaml
schema_version: 1
explicit_documents:
  - document_id: LGU_REQ_5G_V02_00_00
    carrier: LGU+
    role: REQUIREMENT
    media_type: text/html
    path: 새 폴더 (2)/LGU+/LGU+_5G_20260728/CD_20_LGU_디바이스_5G_기술요구서_V02_00_00.html
  - document_id: LGU_PROC_5G_V02_00_00
    carrier: LGU+
    role: PROCEDURE
    media_type: text/html
    path: 새 폴더 (2)/LGU+/LGU+_5G_20260728/CD_20_LGU_디바이스_5G_시험절차서_V02_00_00.html
  - document_id: KT_REQ_NSA_V1_3_0
    carrier: KT
    role: REQUIREMENT
    media_type: application/pdf
    path: 새 폴더 (2)/KT/20260702-KR/KT 5G NSA 단말 기능 규격 V1.3.0(배포용)_20260508.pdf
  - document_id: KT_SAT_NSA_V1_3_0
    carrier: KT
    role: SAT
    media_type: application/pdf
    path: 새 폴더 (2)/KT/20260702-KR/KT 5G NSA 단말 기능 SAT 규격 V1.3.0(배포용)_20260508.pdf
  - document_id: KT_REQ_SA_V1_6_0
    carrier: KT
    role: REQUIREMENT
    media_type: application/pdf
    path: 새 폴더 (2)/KT/20260702-KR/KT 5G SA 단말 기능 규격 V1.6.0(배포용)_20260429.pdf
  - document_id: KT_SAT_SA_V1_6_0
    carrier: KT
    role: SAT
    media_type: application/pdf
    path: 새 폴더 (2)/KT/20260702-KR/KT 5G SA 단말 기능 SAT 규격 V1.6.0(배포용)_20260429.pdf
discoveries:
  - discovery_id: SKT_LEGACY_XLS_V1
    carrier: SKT
    role: PROCEDURE
    media_type: application/vnd.ms-excel
    base_path: 새 폴더 (2)/SKT_시험절차서_최신
    glob: "*.xls"
    expected_count: 66
    id_prefix: SKT_PROC_
    id_width: 4
```

The contract must not contain hashes; hashes belong to the generated registry. It must reject duplicate explicit IDs, overlapping explicit/discovered paths, unsupported roles/media types, recursive globs, and symlink escapes.

`source_registry_schema_v1.json` uses JSON Schema draft 2020-12, sets
`additionalProperties: false`, and requires top-level `schema_version` and `documents`. Each document
requires exactly `document_id`, `carrier`, `role`, `media_type`, `path`, `size_bytes`, `sha256`, and
`intake`; the hash pattern is `^[0-9a-f]{64}$`, size minimum is zero, and intake requires
`container_status`, `semantic_parse_status`, and nullable `semantic_parser`.

- [x] **Step 4: Implement registry construction and the schema contract**

```python
OLE_CFB_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")


def probe_media(path: Path, media_type: str) -> dict[str, object]:
    if media_type == "application/vnd.ms-excel":
        with path.open("rb") as stream:
            readable = stream.read(8) == OLE_CFB_SIGNATURE
        return {
            "container_status": "READABLE" if readable else "UNREADABLE",
            "semantic_parse_status": "NOT_ATTEMPTED",
            "semantic_parser": None,
        }
    return {
        "container_status": "READABLE",
        "semantic_parse_status": "NOT_APPLICABLE",
        "semantic_parser": None,
    }
```

Registry entries must contain exactly `document_id`, `carrier`, `role`, `media_type`, `path`, `size_bytes`, `sha256`, and `intake`. Sort output documents by `document_id`; initial discovered IDs are assigned from repo-relative POSIX path lexical order. With `--previous`, match by stored path and fail closed on missing/unexpected paths rather than auto-renaming.

- [x] **Step 5: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_registry.py -q`

Expected: all tests pass.

- [x] **Step 6: Verify CLI failure behavior from an arbitrary CWD**

Run:

```powershell
Push-Location C:\
& 'C:\Users\momen\Projects\tc-runner\venv\Scripts\python.exe' 'C:\Users\momen\Projects\tc-runner\KR3_Carrier_Requirements\tools\build_source_registry.py' --repo-root 'C:\Users\momen\Projects\tc-runner' --scope 'C:\Users\momen\Projects\tc-runner\KR3_Carrier_Requirements\contracts\source_scope_v1.yaml' --out "$env:TEMP\source_registry_v1.json"
Pop-Location
```

Expected: exit 0; the output contains 72 documents: LGU+ 2, KT 4, SKT 66. No traceback is printed on a controlled error; controlled errors exit 2.

- [ ] **Step 7: Review the conditional commit boundary**

Stage only the four Task 2 files after explicit commit approval. Expected eventual message: `feat(kr3): register carrier source scope`.

### Task 3: Requirement-to-Procedure/SAT Relation Ledger

**Files:**

- Modify: `KR3_Carrier_Requirements/contracts/source_scope_v1.yaml`
- Create: `KR3_Carrier_Requirements/contracts/source_relations_schema_v1.json`
- Create: `KR3_Carrier_Requirements/tools/build_source_relations.py`
- Create: `KR3_Carrier_Requirements/tests/test_source_relations.py`

**Interfaces:**

- Consumes: `source_registry_v1.json` from Task 2.
- Produces: `build_relations(scope: dict, registry: dict) -> dict`.
- CLI: `build_source_relations.py --scope PATH --registry PATH --out PATH`.

- [ ] **Step 1: Write failing relation-integrity tests**

```python
def valid_registry() -> dict:
    return {
        "schema_version": 1,
        "documents": [
            {"document_id": "LGU_REQ", "role": "REQUIREMENT", "sha256": "0" * 64},
            {"document_id": "LGU_PROC", "role": "PROCEDURE", "sha256": "1" * 64},
            {"document_id": "KT_NSA_REQ", "role": "REQUIREMENT", "sha256": "2" * 64},
            {"document_id": "KT_NSA_SAT", "role": "SAT", "sha256": "3" * 64},
            {"document_id": "KT_SA_REQ", "role": "REQUIREMENT", "sha256": "4" * 64},
            {"document_id": "KT_SA_SAT", "role": "SAT", "sha256": "5" * 64},
        ],
    }


def valid_scope() -> dict:
    return {"relations": [
        {"relation_id": "LGU_5G_V02_REQ_TO_PROC", "kind": "REQUIREMENT_TO_PROCEDURE", "source_document_id": "LGU_REQ", "target_document_id": "LGU_PROC"},
        {"relation_id": "KT_NSA_V1_3_0_REQ_TO_SAT", "kind": "REQUIREMENT_TO_SAT", "source_document_id": "KT_NSA_REQ", "target_document_id": "KT_NSA_SAT"},
        {"relation_id": "KT_SA_V1_6_0_REQ_TO_SAT", "kind": "REQUIREMENT_TO_SAT", "source_document_id": "KT_SA_REQ", "target_document_id": "KT_SA_SAT"},
    ]}


def test_relations_require_existing_ids_and_correct_roles() -> None:
    result = build_relations(valid_scope(), valid_registry())
    assert [r["relation_id"] for r in result["relations"]] == [
        "KT_NSA_V1_3_0_REQ_TO_SAT",
        "KT_SA_V1_6_0_REQ_TO_SAT",
        "LGU_5G_V02_REQ_TO_PROC",
    ]


def test_relation_rejects_requirement_pointing_to_requirement() -> None:
    scope = valid_scope()
    scope["relations"][0]["target_document_id"] = "KT_SA_REQ"
    with pytest.raises(G0AError, match="RELATION_ROLE_MISMATCH"):
        build_relations(scope, valid_registry())
```

Add explicit dangling and duplicate checks:

```python
def test_relations_reject_dangling_and_duplicate_pairs() -> None:
    dangling = valid_scope()
    dangling["relations"][0]["target_document_id"] = "MISSING"
    with pytest.raises(G0AError, match="RELATION_DANGLING_DOCUMENT"):
        build_relations(dangling, valid_registry())

    duplicate = valid_scope()
    duplicate["relations"].append(dict(duplicate["relations"][0], relation_id="DUP"))
    with pytest.raises(G0AError, match="RELATION_DUPLICATE_PAIR"):
        build_relations(duplicate, valid_registry())
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_relations.py -q`

Expected: collection fails because `build_source_relations` does not exist.

- [x] **Step 3: Add the exact three source relations to the scope contract**

```yaml
relations:
  - relation_id: LGU_5G_V02_REQ_TO_PROC
    kind: REQUIREMENT_TO_PROCEDURE
    source_document_id: LGU_REQ_5G_V02_00_00
    target_document_id: LGU_PROC_5G_V02_00_00
  - relation_id: KT_NSA_V1_3_0_REQ_TO_SAT
    kind: REQUIREMENT_TO_SAT
    source_document_id: KT_REQ_NSA_V1_3_0
    target_document_id: KT_SAT_NSA_V1_3_0
  - relation_id: KT_SA_V1_6_0_REQ_TO_SAT
    kind: REQUIREMENT_TO_SAT
    source_document_id: KT_REQ_SA_V1_6_0
    target_document_id: KT_SAT_SA_V1_6_0
```

- [x] **Step 4: Implement relation materialization**

`source_relations_schema_v1.json` uses JSON Schema draft 2020-12, rejects additional properties,
requires top-level `schema_version` and `relations`, and requires every relation to contain exactly
`relation_id`, `kind`, `source_document_id`, and `target_document_id`.

```python
ROLE_MATRIX = {
    "REQUIREMENT_TO_PROCEDURE": ("REQUIREMENT", "PROCEDURE"),
    "REQUIREMENT_TO_SAT": ("REQUIREMENT", "SAT"),
}


def build_relations(scope: dict, registry: dict) -> dict:
    documents = {item["document_id"]: item for item in registry["documents"]}
    relations = []
    for declared in scope["relations"]:
        expected_roles = ROLE_MATRIX[declared["kind"]]
        source = documents.get(declared["source_document_id"])
        target = documents.get(declared["target_document_id"])
        if source is None or target is None:
            raise G0AError("RELATION_DANGLING_DOCUMENT", declared["relation_id"])
        if (source["role"], target["role"]) != expected_roles:
            raise G0AError("RELATION_ROLE_MISMATCH", declared["relation_id"])
        relations.append({**declared})
    return {"schema_version": 1, "relations": sorted(relations, key=lambda x: x["relation_id"])}
```

- [x] **Step 5: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_source_relations.py -q`

Expected: all tests pass.

- [ ] **Step 6: Review the conditional commit boundary**

Stage only the four Task 3 paths after explicit commit approval. Expected eventual message: `feat(kr3): add source relation ledger`.

### Task 4: Immutable LGU Legacy Expected Ledger

**Files:**

- Create: `KR3_Carrier_Requirements/contracts/legacy_expected_ledger_schema_v1.json`
- Create: `KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py`
- Create: `KR3_Carrier_Requirements/tests/test_legacy_expected_ledger.py`

**Interfaces:**

- Consumes: `*_canonical.yaml` files from a supplied STAGE1 directory.
- Produces: `extract_expected(stage1_dir: Path) -> list[dict[str, object]]`.
- Produces: `initialize_ledger(stage1_dir: Path) -> dict`.
- Produces: `check_ledger(stage1_dir: Path, ledger: dict) -> None`.
- CLI modes: `init --stage1 PATH --out PATH` and `check --stage1 PATH --ledger PATH`.

- [ ] **Step 1: Write failing initialization and drift tests**

```python
def write_case(stage1_dir: Path, tc_id: str, entries: list[tuple[int, str]]) -> None:
    steps = []
    for step_no, target in entries:
        steps.append({
            "step_no": step_no,
            "source_trace": {"raw_segment": f"source-{target}"},
            "expected": [{"type": "verify_text", "target": target, "value": None}],
        })
    (stage1_dir / f"{tc_id}_canonical.yaml").write_text(
        yaml.safe_dump({"tc_id": tc_id, "procedure_steps": steps}, sort_keys=False),
        encoding="utf-8",
    )


def test_initialization_assigns_global_immutable_ids_in_canonical_order(tmp_path: Path) -> None:
    write_case(tmp_path, "CASE_B", [(1, "b")])
    write_case(tmp_path, "CASE_A", [(2, "a2"), (1, "a1")])
    ledger = initialize_ledger(tmp_path)
    assert [(x["legacy_expected_id"], x["tc_id"], x["step_no"]) for x in ledger["items"]] == [
        ("LGU-EXP-000001", "CASE_A", 1),
        ("LGU-EXP-000002", "CASE_A", 2),
        ("LGU-EXP-000003", "CASE_B", 1),
    ]


def test_check_rejects_changed_expected_without_reissuing_id(tmp_path: Path) -> None:
    write_case(tmp_path, "CASE_A", [(1, "before")])
    ledger = initialize_ledger(tmp_path)
    write_case(tmp_path, "CASE_A", [(1, "after")])
    with pytest.raises(G0AError, match="LEGACY_EXPECTED_DRIFT"):
        check_ledger(tmp_path, ledger)
```

Add explicit locator-set drift and empty-input checks:

```python
def test_check_rejects_removed_or_inserted_expected(tmp_path: Path) -> None:
    write_case(tmp_path, "CASE_A", [(1, "one")])
    ledger = initialize_ledger(tmp_path)
    write_case(tmp_path, "CASE_A", [(1, "one"), (2, "two")])
    with pytest.raises(G0AError, match="LEGACY_EXPECTED_SET_DRIFT"):
        check_ledger(tmp_path, ledger)


def test_initialization_rejects_empty_stage1(tmp_path: Path) -> None:
    with pytest.raises(G0AError, match="CTF_INPUT_EMPTY"):
        initialize_ledger(tmp_path)
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_legacy_expected_ledger.py -q`

Expected: collection fails because `build_legacy_expected_ledger` does not exist.

- [x] **Step 3: Implement exact legacy snapshots and fingerprints**

`legacy_expected_ledger_schema_v1.json` uses JSON Schema draft 2020-12, rejects additional
properties, and requires `schema_version` plus `items`. Each item requires
`legacy_expected_id`, `fingerprint_sha256`, `status`, `tc_id`, `step_no`, `expected_index`,
`step_source_trace`, and `expected`. The ID pattern is `^LGU-EXP-[0-9]{6}$`, fingerprint pattern is
`^[0-9a-f]{64}$`, status is the single v1 value `ACTIVE`, and both numeric indexes have minimum 1.

```python
def expected_snapshot(tc_id: str, step: dict, expected_index: int, expected: dict) -> dict:
    return {
        "tc_id": tc_id,
        "step_no": step["step_no"],
        "expected_index": expected_index,
        "step_source_trace": step.get("source_trace"),
        "expected": expected,
    }


def initialize_ledger(stage1_dir: Path) -> dict:
    snapshots = extract_expected(stage1_dir)
    items = []
    for sequence, snapshot in enumerate(snapshots, start=1):
        items.append({
            "legacy_expected_id": f"LGU-EXP-{sequence:06d}",
            "fingerprint_sha256": sha256_bytes(canonical_json_bytes(snapshot)),
            "status": "ACTIVE",
            **snapshot,
        })
    return {"schema_version": 1, "items": items}
```

Sort snapshots by `(tc_id, step_no, expected_index)`. `check` compares the complete ordered locator set and every fingerprint; it never edits or reallocates IDs. Any accepted future source correction requires a separately reviewed ledger migration, not an automatic repair.

- [x] **Step 4: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_legacy_expected_ledger.py -q`

Expected: all tests pass.

- [x] **Step 5: Initialize in a temporary location and verify the real count**

Run:

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py init --stage1 KR3_Carrier_Requirements/stage1 --out "$env:TEMP\lgu_legacy_expected_ledger_v1.json"
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py check --stage1 KR3_Carrier_Requirements/stage1 --ledger "$env:TEMP\lgu_legacy_expected_ledger_v1.json"
```

Expected: exit 0; `cases=28 expected=232 drift=0`.

- [ ] **Step 6: Review the conditional commit boundary**

Stage only the three Task 4 files after explicit commit approval. Expected eventual message: `feat(kr3): freeze LGU legacy expected identities`.

### Task 5: G0-A End-to-End Checker and Tracked Artifacts

**Files:**

- Create: `KR3_Carrier_Requirements/tools/check_g0a.py`
- Create: `KR3_Carrier_Requirements/tests/test_check_g0a.py`
- Create: `KR3_Carrier_Requirements/catalog/source_registry_v1.json`
- Create: `KR3_Carrier_Requirements/catalog/source_relations_v1.json`
- Create: `KR3_Carrier_Requirements/catalog/lgu_legacy_expected_ledger_v1.json`

**Interfaces:**

- Consumes: builders and contracts from Tasks 1–4.
- Produces: `ARTIFACT_NAMES: tuple[str, str, str]` containing the three tracked JSON filenames.
- Produces: `load_json(path: Path) -> dict`.
- Produces: `compare_expected_artifact_bytes(expected_dir: Path, rebuilt_dir: Path) -> None`.
- Produces: `summarize(registry: dict, relations: dict, expected_ledger: dict) -> dict[str, int]`.
- CLI: `check_g0a.py --repo-root PATH [--artifact-dir PATH]`.
- Exit 0 only when artifacts rebuild byte-identically and all acceptance counts match; controlled failure exits 2 without traceback.

- [ ] **Step 1: Write failing end-to-end checker tests**

```python
def test_checker_rebuilds_byte_identically_from_arbitrary_cwd(
    repo_root: Path, tmp_path: Path
) -> None:
    script = repo_root / "KR3_Carrier_Requirements/tools/check_g0a.py"
    result = subprocess.run(
        [sys.executable, "-B", str(script), "--repo-root", str(repo_root)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "documents=72 lgu=2 kt=4 skt_xls=66" in result.stdout
    assert "relations=3" in result.stdout
    assert "lgu_cases=28 lgu_expected=232" in result.stdout
    assert "byte_drift=0 source_mutation=0" in result.stdout


def test_artifact_comparison_fails_closed_on_stale_bytes(tmp_path: Path) -> None:
    tracked = tmp_path / "tracked"
    rebuilt = tmp_path / "rebuilt"
    tracked.mkdir()
    rebuilt.mkdir()
    for name in ARTIFACT_NAMES:
        (tracked / name).write_text('{"state":"old"}\n', encoding="utf-8")
        (rebuilt / name).write_text('{"state":"old"}\n', encoding="utf-8")
    (rebuilt / "source_registry_v1.json").write_text(
        '{"state":"new"}\n', encoding="utf-8"
    )
    with pytest.raises(G0AError, match="ARTIFACT_BYTE_DRIFT"):
        compare_expected_artifact_bytes(tracked, rebuilt)
```

The source-set mismatch cases are exercised in Task 2, empty STAGE1 in Task 4, stale/missing
artifacts in this task, and the final real-corpus gate below rechecks source hashes and mtimes.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_check_g0a.py -q`

Expected: collection fails because `check_g0a` does not exist.

- [x] **Step 3: Implement a read-only temporary rebuild**

```python
def source_state(registry: dict, repo_root: Path) -> dict[str, tuple[str, int]]:
    return {
        item["path"]: (
            sha256_file(resolve_repo_relative(repo_root, item["path"])),
            resolve_repo_relative(repo_root, item["path"]).stat().st_mtime_ns,
        )
        for item in registry["documents"]
    }


def check_all(repo_root: Path, artifact_dir: Path) -> dict[str, int]:
    scope_path = repo_root / "KR3_Carrier_Requirements/contracts/source_scope_v1.yaml"
    stage1_dir = repo_root / "KR3_Carrier_Requirements/stage1"
    scope_data = load_scope(scope_path)
    tracked_registry = load_json(artifact_dir / "source_registry_v1.json")
    tracked_relations = load_json(artifact_dir / "source_relations_v1.json")
    tracked_expected = load_json(artifact_dir / "lgu_legacy_expected_ledger_v1.json")
    before = source_state(tracked_registry, repo_root)
    with tempfile.TemporaryDirectory(prefix="kr3-g0a-") as raw_tmp:
        tmp = Path(raw_tmp)
        rebuilt_registry = build_registry(repo_root, scope_path, previous=tracked_registry)
        write_json(tmp / "source_registry_v1.json", rebuilt_registry)
        rebuilt_relations = build_relations(scope_data, rebuilt_registry)
        rebuilt_expected = initialize_ledger(stage1_dir)
        write_json(tmp / "source_relations_v1.json", rebuilt_relations)
        write_json(tmp / "lgu_legacy_expected_ledger_v1.json", rebuilt_expected)
        compare_expected_artifact_bytes(artifact_dir, tmp)
    after = source_state(tracked_registry, repo_root)
    if before != after:
        raise G0AError("SOURCE_MUTATION", "source hash or mtime changed")
    return summarize(tracked_registry, tracked_relations, tracked_expected)
```

`load_json` rejects missing files and non-object roots. `compare_expected_artifact_bytes` iterates
only `ARTIFACT_NAMES` and raises `ARTIFACT_BYTE_DRIFT` with the filename on the first unequal byte
sequence. `summarize` counts carrier/role/media fields and ledger items, then raises a dedicated
count error unless the totals are documents 72, LGU+ 2, KT 4, SKT XLS 66, relations 3, LGU cases
28, and LGU expected 232.

Resolve `scope_path` and `stage1_dir` from `repo_root`, not current working directory. Do not call
`spec_corpus_index.py`, Poppler, Excel, ADB, QCAT, or COM.

- [x] **Step 4: Run focused tests**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_check_g0a.py -q`

Expected: all tests pass.

- [x] **Step 5: Generate candidate artifacts into a temporary directory**

Run:

```powershell
$g0aCandidate = Join-Path $env:TEMP 'kr3-g0a-candidate'
New-Item -ItemType Directory -Force -Path $g0aCandidate | Out-Null
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/build_source_registry.py --repo-root . --scope KR3_Carrier_Requirements/contracts/source_scope_v1.yaml --out "$g0aCandidate\source_registry_v1.json"
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/build_source_relations.py --scope KR3_Carrier_Requirements/contracts/source_scope_v1.yaml --registry "$g0aCandidate\source_registry_v1.json" --out "$g0aCandidate\source_relations_v1.json"
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/build_legacy_expected_ledger.py init --stage1 KR3_Carrier_Requirements/stage1 --out "$g0aCandidate\lgu_legacy_expected_ledger_v1.json"
```

Expected: three files, registry count 72, relation count 3, expected count 232. Before copying them into `catalog/`, review the complete SKT document-ID assignment and all three relation records. Copying into tracked catalog is an implementation action covered by the execution approval, not by this planning turn.

- [x] **Step 6: Install the reviewed artifacts with `apply_patch` and run the real checker twice**

Run twice:

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/check_g0a.py --repo-root .
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/check_g0a.py --repo-root .
```

Expected both times: exit 0 with `documents=72`, `skt_xls=66`, `relations=3`, `lgu_cases=28`, `lgu_expected=232`, `byte_drift=0`, and `source_mutation=0`.

- [ ] **Step 7: Review the conditional commit boundary**

Stage only the five Task 5 paths after explicit commit approval. Expected eventual message: `feat(kr3): add fail-closed G0-A audit`.

### Task 6: Documentation and Source-of-Truth Alignment

**Files:**

- Modify: `KR3_Carrier_Requirements/README.md`
- Modify: `AGENTS.md` §5.4, §5.6, and §8.2 only with explicit approval in the execution turn.

**Interfaces:**

- Consumes: exact G0-A measured output from Task 5.
- Produces: user-facing commands and honest status vocabulary.

- [ ] **Step 1: Add a documentation assertion test**

Add to `KR3_Carrier_Requirements/tests/test_check_g0a.py`:

```python
def test_readme_reports_skt_procedure_intake_without_claiming_semantic_parse(repo_root: Path) -> None:
    readme = (repo_root / "KR3_Carrier_Requirements/README.md").read_text(encoding="utf-8")
    assert "SKT legacy .xls 66건" in readme
    assert "semantic_parse_status: NOT_ATTEMPTED" in readme
    assert "check_g0a.py" in readme
    assert "SKT 시험절차서 | 존재 여부 자체가 미확인" not in readme
```

- [ ] **Step 2: Run the assertion and verify it fails against the stale README**

Run: `venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_check_g0a.py::test_readme_reports_skt_procedure_intake_without_claiming_semantic_parse -q`

Expected: FAIL because the README still says the SKT procedure is missing.

- [x] **Step 3: Update README status and commands**

The updated text must state:

```markdown
- SKT legacy .xls 66건은 full SHA-256과 OLE container readability까지 intake했다.
- G0-A에는 .xls semantic parser 의존성이 없으므로 `semantic_parse_status: NOT_ATTEMPTED`다.
- 이는 sheet/row 의미 분석이나 CTF 정규화 완료를 뜻하지 않는다.
```

Add the command:

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/check_g0a.py --repo-root .
```

Remove only the stale claim that SKT test-procedure existence is unknown; retain the separate fact that the original THOR3 requirement corpus contains 30 PDFs.

- [ ] **Step 4: Update AGENTS source-of-truth entries after explicit policy-file approval**

Add `check_g0a.py`, the three focused builders, and the three catalog artifacts to §5.4/§5.6. Add one §8.2 row with status `applied` only after the user approves that policy edit and the final checker passes; otherwise leave AGENTS untouched and report the pending alignment blocker.

- [x] **Step 5: Run documentation and focused G0-A tests**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_g0a_common.py KR3_Carrier_Requirements/tests/test_source_registry.py KR3_Carrier_Requirements/tests/test_source_relations.py KR3_Carrier_Requirements/tests/test_legacy_expected_ledger.py KR3_Carrier_Requirements/tests/test_check_g0a.py -q
```

Expected: all G0-A tests pass.

- [x] **Step 6: Run the pre-existing KR3 regression tests**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests/test_tools.py -q
```

Expected: the existing six tests pass; `verify_step_coverage.py` and `project_runnable.py` behavior is unchanged.

- [ ] **Step 7: Review the conditional commit boundary**

Stage README, the modified G0-A test, and—only if separately approved—AGENTS.md by exact path. Expected eventual message: `docs(kr3): document G0-A source intake`.

### Task 7: Final G0-A Acceptance Gate

**Files:**

- Verify only; no new files.

**Interfaces:**

- Produces the reviewer evidence needed before writing or executing the G0-B plan.

- [x] **Step 1: Run all G0-A and pre-existing KR3 tests together**

Run:

```powershell
venv\Scripts\python.exe -m pytest KR3_Carrier_Requirements/tests -q
```

Expected: all tests pass with no collection errors.

- [x] **Step 2: Run the real source ledger gate from repo root and an arbitrary CWD**

Run:

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/check_g0a.py --repo-root .
Push-Location C:\
& 'C:\Users\momen\Projects\tc-runner\venv\Scripts\python.exe' 'C:\Users\momen\Projects\tc-runner\KR3_Carrier_Requirements\tools\check_g0a.py' --repo-root 'C:\Users\momen\Projects\tc-runner'
Pop-Location
```

Expected: both invocations exit 0 with identical counts and `byte_drift=0 source_mutation=0`.

- [x] **Step 3: Run the original LGU structural gates**

Run:

```powershell
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/check_stage1.py
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/verify_step_coverage.py
venv\Scripts\python.exe KR3_Carrier_Requirements/tools/project_runnable.py
```

Expected: `check_stage1.py` exit 0 for 28 cases/196 steps, coverage reports source 196 ↔ CTF 196 with mismatch 0, and projection remains 0/28 with the previously measured blocker counts. These are static checks, not `validate PASS` or `runtime PASS`.

- [x] **Step 4: Audit exact worktree scope**

Run:

```powershell
git status --short
git diff -- KR3_Carrier_Requirements AGENTS.md docs/superpowers/plans/2026-08-13-carrier-criterion-g0a-source-ledger.md
```

Expected: only approved G0-A paths differ within this task scope; unrelated pre-existing changes remain unstaged and untouched.

- [ ] **Step 5: Stop at the user review gate**

Report measured counts, test selectors, source immutability result, remaining `.xls` semantic-parser limitation, and any unapproved AGENTS alignment. Do not begin G0-B, commit, or push until the user gives the corresponding instruction.
