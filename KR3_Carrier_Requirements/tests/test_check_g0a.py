import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

import check_g0a
import build_skt_workbook_inventory
from build_corpus_closure import build_closure
from build_legacy_expected_ledger import initialize_ledger
from build_resolver_proposal import build_proposal_from_paths
from build_skt_workbook_inventory import skt_sources, validate_acquisition
from build_source_registry import build_registry
from build_source_relations import build_relations
from g0a_common import G0AError, sha256_bytes, write_json

from check_g0a import (
    ARTIFACT_NAMES,
    REBUILT_ARTIFACT_NAMES,
    check_all,
    compare_expected_artifact_bytes,
    load_json,
    main as check_main,
    summarize,
    validate_stored_inventory,
)


KR3_DIR = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = KR3_DIR / "tools" / "check_g0a.py"
SOURCE_SCOPE_SCHEMA = KR3_DIR / "contracts" / "source_scope_schema_v2.json"
CLOSURE_SCHEMA = KR3_DIR / "contracts" / "corpus_closure_schema_v1.json"
INVENTORY_SCHEMA = KR3_DIR / "contracts" / "skt_workbook_inventory_schema_v1.json"
MSISDN_ALLOWLIST_SCHEMA = (
    KR3_DIR / "contracts" / "corpus_msisdn_fixture_allowlist_schema_v1.json"
)
MSISDN_ALLOWLIST = (
    KR3_DIR / "contracts" / "corpus_msisdn_fixture_allowlist_v1.json"
)
OLE_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")
AS_OF = date(2026, 8, 14)


def _sheet(index: int = 1, *, rows: int = 10) -> dict:
    return {
        "sheet_index": index,
        "sheet_name": f"Sheet {index}",
        "visibility": "VISIBLE",
        "used_range": {
            "first_row": 1,
            "last_row": rows,
            "first_column": 1,
            "last_column": 4,
        },
    }


def _disposition(source: dict, *, status: str = "READABLE") -> dict:
    if status == "FAILED":
        return {
            "document_id": source["document_id"],
            "path": source["path"],
            "source_sha256": source["sha256"],
            "acquisition_status": "FAILED",
            "error_code": "EXCEL_COM_80004005",
            "sheet_count": 0,
            "sheets": [],
        }
    return {
        "document_id": source["document_id"],
        "path": source["path"],
        "source_sha256": source["sha256"],
        "acquisition_status": "READABLE",
        "error_code": None,
        "sheet_count": 1,
        "sheets": [_sheet()],
    }


def _inventory(registry: dict) -> dict:
    return {
        "schema_version": 1,
        "tool": "skt-workbook-inventory-v1",
        "workbooks": [_disposition(source) for source in skt_sources(registry)],
    }


def _create_real_shape_repo(tmp_path: Path) -> tuple[Path, Path, dict]:
    repo = tmp_path / "repo"
    contracts = repo / "KR3_Carrier_Requirements" / "contracts"
    stage1 = repo / "KR3_Carrier_Requirements" / "stage1"
    artifacts = repo / "KR3_Carrier_Requirements" / "catalog"
    contracts.mkdir(parents=True)
    stage1.mkdir()
    artifacts.mkdir()
    scope_path = contracts / "source_scope_v2.yaml"
    (contracts / "source_scope_schema_v2.json").write_bytes(
        SOURCE_SCOPE_SCHEMA.read_bytes()
    )
    (contracts / "corpus_closure_schema_v1.json").write_bytes(
        CLOSURE_SCHEMA.read_bytes()
    )
    (contracts / "skt_workbook_inventory_schema_v1.json").write_bytes(
        INVENTORY_SCHEMA.read_bytes()
    )
    (contracts / "corpus_msisdn_fixture_allowlist_schema_v1.json").write_bytes(
        MSISDN_ALLOWLIST_SCHEMA.read_bytes()
    )

    corpus_parent = repo / "새 폴더 (2)"
    roots = {
        "KT": corpus_parent / "KT",
        "LGU+": corpus_parent / "LGU+",
        "SKT_시험절차서_최신": corpus_parent / "SKT_시험절차서_최신",
        "THOR3_SKT_Requirements": corpus_parent / "THOR3_SKT_Requirements",
    }
    for root in roots.values():
        root.mkdir(parents=True)
    (corpus_parent / "files").mkdir()
    (corpus_parent / "ls_log").mkdir()
    (corpus_parent / "BTS27107").mkdir()
    (corpus_parent / "THOR2_J TC-10").mkdir()
    (corpus_parent / "Batchuserdata_1.1_2024121914_debug.apk").write_bytes(b"tool")

    documents = []
    kt_active = [
        ("KT_REQ_NSA_V1_3_0", "REQUIREMENT"),
        ("KT_SAT_NSA_V1_3_0", "SAT"),
        ("KT_REQ_SA_V1_6_0", "REQUIREMENT"),
        ("KT_SAT_SA_V1_6_0", "SAT"),
    ]
    for index, (document_id, role) in enumerate(kt_active, start=1):
        raw_path = f"새 폴더 (2)/KT/active_{index:03d}.pdf"
        repo.joinpath(*Path(raw_path).parts).write_bytes(f"kt-{index}".encode("ascii"))
        documents.append(
            {
                "path": raw_path,
                "state": "ACTIVE",
                "document_id": document_id,
                "carrier": "KT",
                "role": role,
                "media": "application/pdf",
                "currentness": "CURRENTNESS_UNVERIFIED",
            }
        )
    for index in range(1, 113):
        if index <= 3:
            extension = ".pdf"
            content = b"duplicate-group-1"
        elif index <= 15:
            extension = ".pdf"
            group = 2 + ((index - 4) // 2)
            content = f"duplicate-group-{group}".encode("ascii")
        elif index == 16:
            extension = ".pdf"
            content = b"cross-root-duplicate"
        elif index <= 21:
            extension = ".ai" if index % 2 else ".png"
            content = f"asset-{index}".encode("ascii")
        elif index <= 29:
            extension = (".doc", ".docx", ".zip")[(index - 22) % 3]
            content = f"unsupported-{index}".encode("ascii")
        else:
            extension = ".pdf"
            content = f"kt-pending-{index}".encode("ascii")
        raw_path = f"새 폴더 (2)/KT/pending_{index:03d}{extension}"
        repo.joinpath(*Path(raw_path).parts).write_bytes(content)
        documents.append(
            {
                "path": raw_path,
                "state": "PENDING_REVIEW",
                "blocked_on": (
                    "INTERNAL_DECISION"
                    if index <= 21
                    else "INTAKE_CAPABILITY"
                    if index <= 29
                    else "CARRIER_INQUIRY"
                ),
                "recorded_date": "2026-08-14",
                "currentness": "CURRENTNESS_UNVERIFIED",
            }
        )

    for document_id, role, filename in (
        ("LGU_REQ_5G_V02_00_00", "REQUIREMENT", "requirement.html"),
        ("LGU_PROC_5G_V02_00_00", "PROCEDURE", "procedure.html"),
    ):
        raw_path = f"새 폴더 (2)/LGU+/{filename}"
        repo.joinpath(*Path(raw_path).parts).write_bytes(document_id.encode("ascii"))
        documents.append(
            {
                "path": raw_path,
                "state": "ACTIVE",
                "document_id": document_id,
                "carrier": "LGU+",
                "role": role,
                "media": "text/html",
                "currentness": "CURRENTNESS_UNVERIFIED",
            }
        )

    for index in range(1, 67):
        raw_path = f"새 폴더 (2)/SKT_시험절차서_최신/source_{index:04d}.xls"
        repo.joinpath(*Path(raw_path).parts).write_bytes(
            OLE_SIGNATURE + f"workbook-{index}".encode("ascii")
        )
        documents.append(
            {
                "path": raw_path,
                "state": "ACTIVE",
                "document_id": f"SKT_PROC_{index:04d}",
                "carrier": "SKT",
                "role": "PROCEDURE",
                "media": "application/vnd.ms-excel",
                "currentness": "CURRENTNESS_UNVERIFIED",
            }
        )
    for index in range(1, 31):
        raw_path = f"새 폴더 (2)/THOR3_SKT_Requirements/[SKT-{index:03d}] pending.pdf"
        content = (
            b"cross-root-duplicate"
            if index == 1
            else f"skt-pending-{index}".encode("ascii")
        )
        repo.joinpath(*Path(raw_path).parts).write_bytes(content)
        documents.append(
            {
                "path": raw_path,
                "state": "PENDING_REVIEW",
                "blocked_on": (
                    "INTERNAL_DECISION" if index == 1 else "CARRIER_INQUIRY"
                ),
                "recorded_date": "2026-08-14",
                "currentness": "CURRENTNESS_UNVERIFIED",
            }
        )

    scope = {
        "schema_version": 2,
        "corpus_parent": {
            "path": "새 폴더 (2)",
            "expected_entries": 9,
            "non_corpus_entries": [
                {"name": "files", "kind": "DIRECTORY", "rationale": "fixture"},
                {"name": "ls_log", "kind": "DIRECTORY", "rationale": "fixture"},
                {
                    "name": "Batchuserdata_1.1_2024121914_debug.apk",
                    "kind": "FILE",
                    "rationale": "fixture",
                },
                {"name": "BTS27107", "kind": "DIRECTORY", "rationale": "fixture"},
                {
                    "name": "THOR2_J TC-10",
                    "kind": "DIRECTORY",
                    "rationale": "fixture",
                },
            ],
        },
        "corpus_roots": [
            {"root": "새 폴더 (2)/KT", "expected_total": 116},
            {"root": "새 폴더 (2)/LGU+", "expected_total": 2},
            {"root": "새 폴더 (2)/SKT_시험절차서_최신", "expected_total": 66},
            {"root": "새 폴더 (2)/THOR3_SKT_Requirements", "expected_total": 30},
        ],
        "documents": documents,
        "relations": [
            {
                "relation_id": "LGU_5G_V02_REQ_TO_PROC",
                "kind": "REQUIREMENT_TO_PROCEDURE",
                "source_document_id": "LGU_REQ_5G_V02_00_00",
                "target_document_id": "LGU_PROC_5G_V02_00_00",
            },
            {
                "relation_id": "KT_NSA_V1_3_0_REQ_TO_SAT",
                "kind": "REQUIREMENT_TO_SAT",
                "source_document_id": "KT_REQ_NSA_V1_3_0",
                "target_document_id": "KT_SAT_NSA_V1_3_0",
            },
            {
                "relation_id": "KT_SA_V1_6_0_REQ_TO_SAT",
                "kind": "REQUIREMENT_TO_SAT",
                "source_document_id": "KT_REQ_SA_V1_6_0",
                "target_document_id": "KT_SAT_SA_V1_6_0",
            },
        ],
        "external_gaps": [],
    }
    scope_path.write_text(
        yaml.safe_dump(scope, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    for case_index in range(1, 29):
        expected_count = 9 if case_index <= 8 else 8
        case = {
            "tc_id": f"LGU_CASE_{case_index:03d}",
            "procedure_steps": [
                {
                    "step_no": 1,
                    "source_trace": {"case": case_index},
                    "expected": [
                        {"type": "verify_text", "value": f"{case_index}-{item_index}"}
                        for item_index in range(1, expected_count + 1)
                    ],
                }
            ],
        }
        (stage1 / f"case_{case_index:03d}_canonical.yaml").write_text(
            yaml.safe_dump(case, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    closure = build_closure(repo, scope_path, as_of=AS_OF)
    registry = build_registry(repo, scope_path)
    relations = build_relations(scope, registry)
    ledger = initialize_ledger(stage1)
    inventory = _inventory(registry)
    write_json(artifacts / "corpus_closure_v1.json", closure)
    proposal = build_proposal_from_paths(
        artifacts / "corpus_closure_v1.json",
        scope_path,
    )
    write_json(artifacts / "resolver_proposal_v1.json", proposal)
    write_json(artifacts / "source_registry_v1.json", registry)
    write_json(artifacts / "skt_workbook_inventory_v1.json", inventory)
    write_json(artifacts / "source_relations_v1.json", relations)
    write_json(artifacts / "lgu_legacy_expected_ledger_v1.json", ledger)
    closure_by_path = {
        document["path"]: document["sha256"] for document in closure["documents"]
    }
    fixture_values = [f"010{10_000_000 + index:08d}" for index in range(1, 10)]
    occurrence_values = fixture_values + fixture_values[:2]
    source_paths = [
        "새 폴더 (2)/KT/active_001.pdf",
        "새 폴더 (2)/KT/active_002.pdf",
        "새 폴더 (2)/KT/active_003.pdf",
    ]
    index_documents = []
    allowlist_by_value = {value: [] for value in fixture_values}
    occurrence_index = 0
    for document_index, source_path in enumerate(source_paths):
        section_count = (4, 4, 3)[document_index]
        sections = []
        for section_index in range(section_count):
            value = occurrence_values[occurrence_index]
            title = f"carrier fixture {value}"
            section = {"id": f"2.1.1.{section_index + 1}", "title": title}
            sections.append(section)
            allowlist_by_value[value].append(
                {
                    "source_path": source_path,
                    "source_sha256": closure_by_path[source_path],
                    "section_index": section_index,
                    "section_id": section["id"],
                    "title_sha256": _fixture_digest(title),
                }
            )
            occurrence_index += 1
        index_documents.append(
            {
                "rel": source_path.removeprefix("새 폴더 (2)/"),
                "sections": sections,
            }
        )
    write_json(
        artifacts / "corpus_index.json",
        {
            "root": "새 폴더 (2)",
            "docs": index_documents,
        },
    )
    write_json(
        contracts / "corpus_msisdn_fixture_allowlist_v1.json",
        {
            "schema_version": 1,
            "tool": "corpus-msisdn-fixture-allowlist-v1",
            "source_artifact": "KR3_Carrier_Requirements/catalog/corpus_index.json",
            "expected_unique": 9,
            "expected_occurrences": 11,
            "fixtures": [
                {
                    "value_sha256": _fixture_digest(value),
                    "rationale": "synthetic carrier specification fixture",
                    "occurrences": allowlist_by_value[value],
                }
                for value in fixture_values
            ],
        },
    )
    return repo, artifacts, registry


class InventorySchemaError(AssertionError):
    pass


_SUPPORTED_INVENTORY_SCHEMA_KEYWORDS = {
    "$schema",
    "additionalProperties",
    "allOf",
    "const",
    "enum",
    "if",
    "items",
    "maxItems",
    "minItems",
    "minimum",
    "minLength",
    "oneOf",
    "pattern",
    "properties",
    "required",
    "then",
    "title",
    "type",
}
_SUPPORTED_INVENTORY_PATTERNS = {
    r"^[0-9a-f]{64}(?![\s\S])",
    r"^(?:SOURCE_HASH_DRIFT|EXCEL_COM_[0-9A-F]{8})(?![\s\S])",
}


def _assert_supported_inventory_schema(schema: object, path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise InventorySchemaError(f"{path}: schema object")
    unsupported = sorted(set(schema) - _SUPPORTED_INVENTORY_SCHEMA_KEYWORDS)
    if unsupported:
        raise InventorySchemaError(f"{path}: unsupported {unsupported[0]}")
    if "pattern" in schema and schema["pattern"] not in _SUPPORTED_INVENTORY_PATTERNS:
        raise InventorySchemaError(f"{path}: unsupported pattern")
    for key in ("properties",):
        if key in schema:
            if not isinstance(schema[key], dict):
                raise InventorySchemaError(f"{path}: {key}")
            for name, subschema in schema[key].items():
                _assert_supported_inventory_schema(subschema, f"{path}.{key}.{name}")
    if "items" in schema:
        _assert_supported_inventory_schema(schema["items"], f"{path}.items")
    for key in ("allOf", "oneOf"):
        if key in schema:
            if not isinstance(schema[key], list):
                raise InventorySchemaError(f"{path}: {key}")
            for index, subschema in enumerate(schema[key]):
                _assert_supported_inventory_schema(subschema, f"{path}.{key}[{index}]")
    for key in ("if", "then"):
        if key in schema:
            _assert_supported_inventory_schema(schema[key], f"{path}.{key}")


def _matches_schema_type(value: object, declared: str) -> bool:
    if declared == "null":
        return value is None
    if declared == "object":
        return isinstance(value, dict)
    if declared == "array":
        return isinstance(value, list)
    if declared == "string":
        return isinstance(value, str)
    if declared == "integer":
        return (
            isinstance(value, int) and not isinstance(value, bool)
        ) or (
            isinstance(value, float) and math.isfinite(value) and value.is_integer()
        )
    raise InventorySchemaError(f"unsupported schema type: {declared}")


def _same_json_value(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def _validate_inventory_schema(schema: dict, value: object, path: str = "$") -> None:
    if path == "$":
        _assert_supported_inventory_schema(schema)
    declared = schema.get("type")
    if declared is not None:
        declared_types = declared if isinstance(declared, list) else [declared]
        if not any(_matches_schema_type(value, item) for item in declared_types):
            raise InventorySchemaError(f"{path}: type")
    if "const" in schema and not _same_json_value(value, schema["const"]):
        raise InventorySchemaError(f"{path}: const")
    if "enum" in schema and not any(
        _same_json_value(value, item) for item in schema["enum"]
    ):
        raise InventorySchemaError(f"{path}: enum")
    if "minimum" in schema and value < schema["minimum"]:
        raise InventorySchemaError(f"{path}: minimum")
    if "minLength" in schema and len(value) < schema["minLength"]:
        raise InventorySchemaError(f"{path}: minLength")
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        raise InventorySchemaError(f"{path}: maxItems")
    if "minItems" in schema and len(value) < schema["minItems"]:
        raise InventorySchemaError(f"{path}: minItems")
    if "pattern" in schema and re.search(schema["pattern"], value, flags=re.ASCII) is None:
        raise InventorySchemaError(f"{path}: pattern")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                raise InventorySchemaError(f"{path}: missing {required}")
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                raise InventorySchemaError(f"{path}: extra {sorted(extras)[0]}")
        for key, subschema in properties.items():
            if key in value:
                _validate_inventory_schema(subschema, value[key], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_inventory_schema(schema["items"], item, f"{path}[{index}]")

    for subschema in schema.get("allOf", []):
        condition = subschema.get("if")
        if condition is None:
            _validate_inventory_schema(subschema, value, path)
            continue
        try:
            _validate_inventory_schema(condition, value, path)
        except InventorySchemaError:
            pass
        else:
            _validate_inventory_schema(subschema["then"], value, path)
    if "oneOf" in schema:
        matches = 0
        for subschema in schema["oneOf"]:
            try:
                _validate_inventory_schema(subschema, value, path)
            except InventorySchemaError:
                continue
            matches += 1
        if matches != 1:
            raise InventorySchemaError(f"{path}: oneOf")


@pytest.mark.parametrize(
    ("contents", "binary"),
    [
        (None, False),
        (b"\xff", True),
        ("{", False),
        ("[]", False),
    ],
    ids=["missing", "invalid-utf8", "invalid-json", "non-object"],
)
def test_load_json_fails_closed_for_every_artifact_load_error(tmp_path, contents, binary):
    path = tmp_path / "artifact.json"
    if contents is not None:
        if binary:
            path.write_bytes(contents)
        else:
            path.write_text(contents, encoding="utf-8")

    with pytest.raises(G0AError) as caught:
        load_json(path)

    assert caught.value.code == "ARTIFACT_INVALID"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b'{"value":1e400}',
        b'{"value":1,"value":2}',
        b'{"nested":{"value":1,"value":2}}',
        b'{"value":"\\ud800"}',
        b'{"\\ud800":"value"}',
    ],
    ids=[
        "nan",
        "positive-infinity",
        "negative-infinity",
        "overflow-infinity",
        "duplicate-root",
        "duplicate-nested",
        "surrogate-value",
        "surrogate-key",
    ],
)
def test_load_json_rejects_noncanonical_json_domain_and_duplicate_keys(tmp_path, raw):
    path = tmp_path / "artifact.json"
    path.write_bytes(raw)

    with pytest.raises(G0AError) as caught:
        load_json(path)

    assert caught.value.code == "ARTIFACT_INVALID"


def test_inventory_loader_rejects_noncanonical_serialized_bytes(tmp_path):
    path = tmp_path / "skt_workbook_inventory_v1.json"
    path.write_text('{"tool":"x","schema_version":1,"workbooks":[]}', encoding="utf-8")

    with pytest.raises(G0AError) as caught:
        load_json(path, require_serialized_canonical=True)

    assert caught.value.code == "ARTIFACT_BYTE_NONCANONICAL"

    write_json(path, {"tool": "x", "schema_version": 1, "workbooks": []})
    assert load_json(path, require_serialized_canonical=True)["schema_version"] == 1


def test_artifact_comparison_fails_closed_on_stale_or_missing_rebuilt_bytes(tmp_path):
    tracked = tmp_path / "tracked"
    rebuilt = tmp_path / "rebuilt"
    tracked.mkdir()
    rebuilt.mkdir()
    for name in REBUILT_ARTIFACT_NAMES:
        (tracked / name).write_text('{"state":"old"}\n', encoding="utf-8")
        (rebuilt / name).write_text('{"state":"old"}\n', encoding="utf-8")
    (rebuilt / "source_registry_v1.json").write_text(
        '{"state":"new"}\n', encoding="utf-8"
    )

    with pytest.raises(G0AError) as stale:
        compare_expected_artifact_bytes(tracked, rebuilt)
    assert stale.value.code == "ARTIFACT_BYTE_DRIFT"
    assert "source_registry_v1.json" in stale.value.detail

    (rebuilt / "source_registry_v1.json").unlink()
    with pytest.raises(G0AError) as missing:
        compare_expected_artifact_bytes(tracked, rebuilt)
    assert missing.value.code == "ARTIFACT_INVALID"


def test_stored_inventory_requires_exact_contract_canonical_order_and_registry_hashes(tmp_path):
    repo, _, registry = _create_real_shape_repo(tmp_path)
    inventory = _inventory(registry)

    validated = validate_stored_inventory(inventory, registry, INVENTORY_SCHEMA)
    assert validated == inventory

    extra = {**inventory, "unexpected": True}
    with pytest.raises(G0AError) as extra_error:
        validate_stored_inventory(extra, registry, INVENTORY_SCHEMA)
    assert extra_error.value.code == "SKT_INVENTORY_INVALID"

    reversed_inventory = copy.deepcopy(inventory)
    reversed_inventory["workbooks"].reverse()
    with pytest.raises(G0AError) as order_error:
        validate_stored_inventory(reversed_inventory, registry, INVENTORY_SCHEMA)
    assert order_error.value.code == "SKT_INVENTORY_CANONICALIZATION_DRIFT"

    hash_drift = copy.deepcopy(inventory)
    hash_drift["workbooks"][0]["source_sha256"] = "f" * 64
    with pytest.raises(G0AError) as hash_error:
        validate_stored_inventory(hash_drift, registry, INVENTORY_SCHEMA)
    assert hash_error.value.code == "XLS_ACQUISITION_IDENTITY_MISMATCH"

    assert repo.is_dir()


def test_published_inventory_schema_accepts_canonical_artifact_and_rejects_extra_root(tmp_path):
    _, _, registry = _create_real_shape_repo(tmp_path)
    inventory = _inventory(registry)
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))

    _validate_inventory_schema(schema, inventory)

    invalid = {**inventory, "extra": True}
    with pytest.raises(InventorySchemaError, match="extra"):
        _validate_inventory_schema(schema, invalid)

    malformed_failed = copy.deepcopy(inventory)
    malformed_failed["workbooks"][0].update(
        acquisition_status="FAILED",
        error_code="EXCEL_COM_80004005",
        sheet_count=1,
    )
    with pytest.raises(InventorySchemaError, match="const|maxItems"):
        _validate_inventory_schema(schema, malformed_failed)


def test_published_inventory_schema_rejects_unknown_failed_error_code_and_empty_readable():
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))
    registry = {
        "schema_version": 1,
        "documents": [
            {
                "document_id": f"SKT_PROC_{index:04d}",
                "carrier": "SKT",
                "role": "PROCEDURE",
                "media_type": "application/vnd.ms-excel",
                "path": f"sources/{index:04d}.xls",
                "size_bytes": 1,
                "sha256": f"{index:064x}",
                "intake": {
                    "container_status": "READABLE",
                    "semantic_parse_status": "NOT_ATTEMPTED",
                    "semantic_parser": None,
                },
            }
            for index in range(1, 67)
        ],
    }
    inventory = _inventory(registry)

    unknown_error = copy.deepcopy(inventory)
    unknown_error["workbooks"][0] = _disposition(
        registry["documents"][0], status="FAILED"
    )
    unknown_error["workbooks"][0]["error_code"] = "ARBITRARY_FAILURE"
    with pytest.raises(InventorySchemaError, match="oneOf"):
        _validate_inventory_schema(schema, unknown_error)

    empty_readable = copy.deepcopy(inventory)
    empty_readable["workbooks"][0]["sheet_count"] = 0
    empty_readable["workbooks"][0]["sheets"] = []
    with pytest.raises(InventorySchemaError, match="minimum|minItems"):
        _validate_inventory_schema(schema, empty_readable)


def test_inventory_schema_walker_fails_closed_on_unknown_keyword():
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))
    schema["properties"]["workbooks"]["maximum"] = 66

    with pytest.raises(InventorySchemaError, match="unsupported maximum"):
        _validate_inventory_schema(
            schema,
            {"schema_version": 1, "tool": "skt-workbook-inventory-v1", "workbooks": []},
        )


def test_inventory_schema_walker_fails_closed_on_unknown_pattern():
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))
    error_code = schema["properties"]["workbooks"]["items"]["properties"]["error_code"]
    error_code["oneOf"][1]["pattern"] = ".*"

    with pytest.raises(InventorySchemaError, match="unsupported pattern"):
        _validate_inventory_schema(
            schema,
            {"schema_version": 1, "tool": "skt-workbook-inventory-v1", "workbooks": []},
        )


@pytest.mark.parametrize(
    ("pattern", "positives", "negatives"),
    [
        (
            r"^[0-9a-f]{64}(?![\s\S])",
            ["0" * 64, "0123456789abcdef" * 4],
            ["0" * 63, "0" * 65, "F" * 64, "0" * 64 + "\n", "x" + "0" * 64],
        ),
        (
            r"^(?:SOURCE_HASH_DRIFT|EXCEL_COM_[0-9A-F]{8})(?![\s\S])",
            ["SOURCE_HASH_DRIFT", "EXCEL_COM_0123ABCD"],
            [
                "SOURCE_HASH_DRIFT\n",
                "SOURCE_HASH_DRIFT_EXTRA",
                "xSOURCE_HASH_DRIFT",
                "EXCEL_COM_0123abcD",
                "EXCEL_COM_0123ABCDE",
            ],
        ),
    ],
)
def test_published_inventory_patterns_have_exact_ecma_search_boundaries(
    pattern, positives, negatives
):
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))
    published_patterns = {
        schema["properties"]["workbooks"]["items"]["properties"][
            "source_sha256"
        ]["pattern"],
        schema["properties"]["workbooks"]["items"]["properties"]["error_code"]
        ["oneOf"][1]["pattern"],
    }
    assert pattern in published_patterns

    pattern_schema = {"type": "string", "pattern": pattern}
    for value in positives:
        _validate_inventory_schema(pattern_schema, value)
    for value in negatives:
        with pytest.raises(InventorySchemaError, match="pattern"):
            _validate_inventory_schema(pattern_schema, value)


def test_published_inventory_schema_uses_draft_integer_semantics(tmp_path):
    schema = json.loads(INVENTORY_SCHEMA.read_text(encoding="utf-8"))
    _, artifacts, registry = _create_real_shape_repo(tmp_path)
    inventory = _inventory(registry)
    workbook = inventory["workbooks"][0]
    workbook["sheet_count"] = 1.0
    workbook["sheets"][0]["sheet_index"] = 1.0
    workbook["sheets"][0]["used_range"]["last_row"] = 10.0

    _validate_inventory_schema(schema, inventory)

    for invalid in (True, math.nan, math.inf, -math.inf, 1.5):
        malformed = copy.deepcopy(inventory)
        malformed["workbooks"][0]["sheet_count"] = invalid
        with pytest.raises(InventorySchemaError, match="type"):
            _validate_inventory_schema(schema, malformed)

    assert artifacts.is_dir()


def test_summary_reports_structural_totals_and_blocks_failed_workbooks(tmp_path):
    _, artifacts, registry = _create_real_shape_repo(tmp_path)
    relations = load_json(artifacts / "source_relations_v1.json")
    ledger = load_json(artifacts / "lgu_legacy_expected_ledger_v1.json")
    closure = load_json(artifacts / "corpus_closure_v1.json")
    proposal = load_json(artifacts / "resolver_proposal_v1.json")
    inventory = _inventory(registry)

    counts = summarize(
        registry,
        relations,
        ledger,
        inventory,
        closure,
        proposal,
        corpus_parent_entries=9,
        as_of=AS_OF,
    )

    assert {key: counts[key] for key in (
        "documents",
        "lgu",
        "kt",
        "skt_xls",
        "relations",
        "lgu_cases",
        "lgu_expected",
        "skt_workbooks",
        "readable_workbooks",
        "failed_workbooks",
        "sheets",
        "used_rows",
    )} == {
        "documents": 72,
        "lgu": 2,
        "kt": 4,
        "skt_xls": 66,
        "relations": 3,
        "lgu_cases": 28,
        "lgu_expected": 232,
        "skt_workbooks": 66,
        "readable_workbooks": 66,
        "failed_workbooks": 0,
        "sheets": 66,
        "used_rows": 660,
    }
    assert counts["corpus_total"] == 214
    assert counts["corpus_active"] == 72
    assert counts["corpus_excluded"] == 0
    assert counts["corpus_pending_review"] == 142
    assert counts["corpus_unclassified"] == 0
    assert counts["pending_by_resolver"] == {
        "CARRIER_INQUIRY": 112,
        "INTERNAL_DECISION": 22,
        "INTAKE_CAPABILITY": 8,
    }
    assert counts["proposal_basis"] == {
        "NORMATIVITY_UNKNOWN": 112,
        "SHA256_DUPLICATE_IN_CORPUS": 17,
        "UNSUPPORTED_MEDIA": 8,
        "NON_DOCUMENT_ASSET": 5,
    }
    assert counts["duplicate_groups"] == 8
    assert counts["duplicate_members"] == 17
    assert counts["oldest_pending_recorded_date"] == "2026-08-14"
    assert counts["pending_max_age_days"] == 0
    assert counts["currentness"] == {
        "CURRENT": 0,
        "CURRENTNESS_UNVERIFIED": 214,
    }

    failed = copy.deepcopy(inventory)
    failed["workbooks"][0] = _disposition(registry["documents"][6], status="FAILED")
    with pytest.raises(G0AError) as caught:
        summarize(
            registry,
            relations,
            ledger,
            failed,
            closure,
            proposal,
            corpus_parent_entries=9,
            as_of=AS_OF,
        )
    assert caught.value.code == "SKT_WORKBOOK_FAILED"
    assert "EXCEL_COM_80004005=1" in caught.value.detail

    with pytest.raises(G0AError) as caught:
        summarize(
            registry,
            relations,
            ledger,
            inventory,
            closure,
            proposal,
            corpus_parent_entries=8,
            as_of=AS_OF,
        )
    assert caught.value.code == "ACCEPTANCE_COUNT_MISMATCH"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "ARTIFACT_INVALID"),
        ("malformed", "PROPOSAL_INVALID"),
        ("stale-closure", "PROPOSAL_STALE"),
        ("stale-scope", "PROPOSAL_STALE"),
        ("set", "PROPOSAL_SET_MISMATCH"),
        ("basis", "PROPOSAL_BASIS_DRIFT"),
    ],
)
def test_checker_requires_and_validates_resolver_proposal(
    tmp_path,
    mutation,
    expected_code,
):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    proposal_path = artifacts / "resolver_proposal_v1.json"
    if mutation == "missing":
        proposal_path.unlink()
    else:
        proposal = load_json(proposal_path)
        if mutation == "malformed":
            proposal["unexpected"] = True
        elif mutation == "stale-closure":
            proposal["closure_sha256"] = "1" * 64
        elif mutation == "stale-scope":
            proposal["source_scope_sha256"] = "2" * 64
        elif mutation == "set":
            proposal["proposals"].pop()
        else:
            normativity = next(
                item
                for item in proposal["proposals"]
                if item["basis"] == "NORMATIVITY_UNKNOWN"
            )
            normativity["blocked_on"] = "INTERNAL_DECISION"
        write_json(proposal_path, proposal)

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == expected_code


def test_checker_compares_rebuilt_proposal_bytes(tmp_path, monkeypatch):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    import check_g0a

    original_builder = check_g0a.build_proposal

    def drifting_builder(*args, **kwargs):
        proposal = original_builder(*args, **kwargs)
        proposal["summary"]["total"] += 1
        return proposal

    monkeypatch.setattr(check_g0a, "build_proposal", drifting_builder)

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "ARTIFACT_BYTE_DRIFT"


def test_checker_allows_reviewed_scope_to_differ_without_proposal_writing_scope(
    tmp_path,
):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    scope_path = (
        repo
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "source_scope_v2.yaml"
    )
    scope = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
    carrier_item = next(
        item
        for item in scope["documents"]
        if item.get("blocked_on") == "CARRIER_INQUIRY"
    )
    internal_item = next(
        item
        for item in scope["documents"]
        if item.get("blocked_on") == "INTERNAL_DECISION"
    )
    carrier_item["blocked_on"], internal_item["blocked_on"] = (
        internal_item["blocked_on"],
        carrier_item["blocked_on"],
    )
    scope_path.write_text(
        yaml.safe_dump(scope, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    closure_path = artifacts / "corpus_closure_v1.json"
    write_json(closure_path, build_closure(repo, scope_path, as_of=AS_OF))
    scope_before = (scope_path.read_bytes(), scope_path.stat().st_mtime_ns)
    proposal = build_proposal_from_paths(closure_path, scope_path)
    assert scope_before == (scope_path.read_bytes(), scope_path.stat().st_mtime_ns)
    write_json(artifacts / "resolver_proposal_v1.json", proposal)

    counts = check_all(repo, artifacts, as_of=AS_OF)

    assert counts["pending_by_resolver"] == {
        "CARRIER_INQUIRY": 112,
        "INTERNAL_DECISION": 22,
        "INTAKE_CAPABILITY": 8,
    }


def test_undeclared_corpus_file_fails_before_proposal_can_absorb_it(tmp_path):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    unexpected = repo / "새 폴더 (2)" / "KT" / "unexpected.pdf"
    unexpected.write_bytes(b"undeclared")

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SCOPE_UNCLASSIFIED"


def test_checker_rebuilds_byte_identically_from_arbitrary_cwd_without_com(tmp_path, monkeypatch):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    cwd = tmp_path / "unrelated-cwd"
    cwd.mkdir()

    def forbidden_com(*args, **kwargs):
        raise AssertionError("static checker invoked the Excel/COM acquisition seam")

    monkeypatch.setattr(
        build_skt_workbook_inventory,
        "_run_powershell_acquisition",
        forbidden_com,
    )
    assert check_all(repo, artifacts, as_of=AS_OF)["skt_workbooks"] == 66
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(CHECK_SCRIPT),
            "--repo-root",
            str(repo),
            "--artifact-dir",
            str(artifacts),
            "--as-of",
            "2026-08-14",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "documents=72 lgu=2 kt=4 skt_xls=66" in result.stdout
    assert "relations=3" in result.stdout
    assert "lgu_cases=28 lgu_expected=232" in result.stdout
    assert "skt_workbooks=66 readable=66 failed=0 sheets=66 used_rows=660" in result.stdout
    assert "corpus_parent_entries=9/9" in result.stdout
    assert "corpus_msisdn_fixtures=9/9 occurrences=11/11 documents=3/3" in result.stdout
    assert "corpus_total=214 active=72 excluded=0 pending_review=142 unclassified=0" in result.stdout
    assert "pending_by_resolver=CARRIER_INQUIRY:112,INTERNAL_DECISION:22,INTAKE_CAPABILITY:8" in result.stdout
    assert "proposal_basis=NORMATIVITY_UNKNOWN:112,SHA256_DUPLICATE_IN_CORPUS:17,UNSUPPORTED_MEDIA:8,NON_DOCUMENT_ASSET:5" in result.stdout
    assert "duplicate_groups=8 duplicate_members=17" in result.stdout
    assert "oldest_pending_recorded_date=2026-08-14 pending_max_age_days=0" in result.stdout
    assert "currentness=CURRENT:0,CURRENTNESS_UNVERIFIED:214" in result.stdout
    assert "semantic_parse_status=NOT_ATTEMPTED" in result.stdout
    assert "byte_drift=0 source_mutation=0" in result.stdout


def test_checker_integrates_exact_msisdn_fixture_counts(tmp_path):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)

    counts = check_all(repo, artifacts, as_of=AS_OF)

    assert counts["corpus_msisdn_fixtures"] == 9
    assert counts["corpus_msisdn_occurrences"] == 11
    assert counts["corpus_msisdn_documents"] == 3


def test_checker_detects_source_mtime_mutation_even_when_rebuild_bytes_match(tmp_path, monkeypatch):
    repo, artifacts, registry = _create_real_shape_repo(tmp_path)
    source_path = repo.joinpath(*Path(registry["documents"][0]["path"]).parts)

    import check_g0a

    original_builder = check_g0a.build_registry

    def mutating_builder(*args, **kwargs):
        result = original_builder(*args, **kwargs)
        current = source_path.stat().st_mtime_ns
        os.utime(source_path, ns=(current + 1_000_000, current + 1_000_000))
        return result

    monkeypatch.setattr(check_g0a, "build_registry", mutating_builder)

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SOURCE_MUTATION"


def test_checker_detects_pending_source_mutation_outside_active_registry(tmp_path, monkeypatch):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    closure = load_json(artifacts / "corpus_closure_v1.json")
    pending_item = next(
        item for item in closure["documents"] if item["state"] == "PENDING_REVIEW"
    )
    source_path = repo.joinpath(*Path(pending_item["path"]).parts)

    import check_g0a

    original_builder = check_g0a.build_registry

    def mutating_builder(*args, **kwargs):
        result = original_builder(*args, **kwargs)
        current = source_path.stat().st_mtime_ns
        os.utime(source_path, ns=(current + 1_000_000, current + 1_000_000))
        return result

    monkeypatch.setattr(check_g0a, "build_registry", mutating_builder)

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SOURCE_MUTATION"


def test_checker_verdict_uses_registered_source_snapshot_during_mutation_and_restoration(
    tmp_path, monkeypatch
):
    repo, artifacts, registry = _create_real_shape_repo(tmp_path)
    source_path = repo.joinpath(*Path(registry["documents"][0]["path"]).parts)
    original_bytes = source_path.read_bytes()
    original_stat = source_path.stat()

    import check_g0a

    original_builder = check_g0a.build_registry

    def mutating_builder(builder_root, scope_path):
        source_path.write_bytes(b"temporary-mutated-original")
        try:
            return original_builder(builder_root, scope_path)
        finally:
            source_path.write_bytes(original_bytes)
            os.utime(
                source_path,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )

    monkeypatch.setattr(check_g0a, "build_registry", mutating_builder)

    assert check_all(repo, artifacts, as_of=AS_OF)["documents"] == 72


def test_checker_passes_snapshot_scope_and_stage1_to_builders(tmp_path, monkeypatch):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    import check_g0a

    original_registry_builder = check_g0a.build_registry
    original_ledger_builder = check_g0a.initialize_ledger
    observed = {}

    def observing_registry_builder(builder_root, scope_path):
        observed["root"] = builder_root.resolve()
        observed["scope"] = scope_path.resolve()
        return original_registry_builder(builder_root, scope_path)

    def observing_ledger_builder(stage1_dir):
        observed["stage1"] = stage1_dir.resolve()
        return original_ledger_builder(stage1_dir)

    monkeypatch.setattr(check_g0a, "build_registry", observing_registry_builder)
    monkeypatch.setattr(check_g0a, "initialize_ledger", observing_ledger_builder)

    check_all(repo, artifacts, as_of=AS_OF)

    assert observed["root"] != repo.resolve()
    assert observed["scope"].is_relative_to(observed["root"])
    assert observed["stage1"].is_relative_to(observed["root"])


def test_checker_uses_snapshot_inventory_schema_during_mutation_and_restoration(
    tmp_path, monkeypatch
):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    schema_path = (
        repo
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "skt_workbook_inventory_schema_v1.json"
    )
    original_bytes = schema_path.read_bytes()
    original_stat = schema_path.stat()

    import check_g0a

    original_validator = check_g0a.validate_stored_inventory
    observed = {}

    def mutating_validator(inventory, registry, consumed_schema_path):
        observed["schema"] = consumed_schema_path.resolve()
        schema_path.write_bytes(b"temporary-mutated-original")
        try:
            return original_validator(inventory, registry, consumed_schema_path)
        finally:
            schema_path.write_bytes(original_bytes)
            os.utime(
                schema_path,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )

    monkeypatch.setattr(check_g0a, "validate_stored_inventory", mutating_validator)

    assert check_all(repo, artifacts, as_of=AS_OF)["documents"] == 72
    assert observed["schema"] != schema_path.resolve()
    assert observed["schema"].name == "skt_workbook_inventory_schema_v1.json"
    assert schema_path.read_bytes() == original_bytes
    assert schema_path.stat().st_mtime_ns == original_stat.st_mtime_ns


def test_checker_audits_inventory_schema_mtime_mutation(tmp_path, monkeypatch):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    schema_path = (
        repo
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "skt_workbook_inventory_schema_v1.json"
    )

    import check_g0a

    original_validator = check_g0a.validate_stored_inventory

    def mutating_validator(inventory, registry, consumed_schema_path):
        result = original_validator(inventory, registry, consumed_schema_path)
        current = schema_path.stat().st_mtime_ns
        os.utime(schema_path, ns=(current + 1_000_000, current + 1_000_000))
        return result

    monkeypatch.setattr(check_g0a, "validate_stored_inventory", mutating_validator)

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SOURCE_MUTATION"


def test_checker_rejects_stage1_directory_symlink_escape(tmp_path):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    stage1 = repo / "KR3_Carrier_Requirements" / "stage1"
    outside = tmp_path / "outside-stage1"
    stage1.rename(outside)
    try:
        stage1.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink unavailable: {error}")

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SOURCE_STATE_INVALID"


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction regression")
def test_checker_rejects_stage1_directory_junction_escape(tmp_path):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    stage1 = repo / "KR3_Carrier_Requirements" / "stage1"
    outside = tmp_path / "outside-stage1-junction"
    stage1.rename(outside)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(stage1), str(outside)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"directory junction unavailable: {result.stderr or result.stdout}")

    with pytest.raises(G0AError) as caught:
        check_all(repo, artifacts, as_of=AS_OF)

    assert caught.value.code == "SOURCE_STATE_INVALID"


def test_cli_returns_exit_2_without_traceback_for_invalid_artifact(tmp_path):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    (artifacts / "source_relations_v1.json").write_bytes(b"\xff")

    result = subprocess.run(
        [
            sys.executable,
            str(CHECK_SCRIPT),
            "--repo-root",
            str(repo),
            "--artifact-dir",
            str(artifacts),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr.startswith("ARTIFACT_INVALID:")
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("local_carry", "expected_code"),
    [
        ("catalog/corpus_index.json", "ARTIFACT_INVALID"),
        ("catalog/lgu_legacy_expected_ledger_v1.json", "ARTIFACT_INVALID"),
        ("stage1", "SOURCE_STATE_INVALID"),
    ],
)
def test_cli_fails_closed_without_each_local_carry_artifact(
    tmp_path,
    local_carry,
    expected_code,
):
    repo, artifacts, _ = _create_real_shape_repo(tmp_path)
    missing = repo / "KR3_Carrier_Requirements" / local_carry
    if missing.is_dir():
        shutil.rmtree(missing)
    else:
        missing.unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(CHECK_SCRIPT),
            "--repo-root",
            str(repo),
            "--artifact-dir",
            str(artifacts),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr.startswith(f"{expected_code}:")
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("artifact_name", ARTIFACT_NAMES)
def test_cli_strict_json_error_is_controlled_for_each_artifact(tmp_path, artifact_name):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    for name in ARTIFACT_NAMES:
        write_json(artifacts / name, {})
    (artifacts / artifact_name).write_text('{"value":NaN}', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(CHECK_SCRIPT),
            "--repo-root",
            str(tmp_path / "repo"),
            "--artifact-dir",
            str(artifacts),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr.startswith("ARTIFACT_INVALID:")
    assert "Traceback" not in result.stderr


def test_cli_path_resolution_error_is_inside_controlled_boundary(tmp_path, monkeypatch, capsys):
    original_resolve = Path.resolve

    def failing_resolve(self, *args, **kwargs):
        if self == tmp_path / "unresolvable-repo":
            raise OSError("resolution failed")
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", failing_resolve)

    exit_code = check_main(["--repo-root", str(tmp_path / "unresolvable-repo")])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("CHECK_FAILED:")
    assert "Traceback" not in captured.err


def test_artifact_name_contract_contains_closure_and_existing_tracked_outputs():
    assert ARTIFACT_NAMES == (
        "corpus_closure_v1.json",
        "resolver_proposal_v1.json",
        "source_registry_v1.json",
        "skt_workbook_inventory_v1.json",
        "source_relations_v1.json",
        "lgu_legacy_expected_ledger_v1.json",
    )
    assert REBUILT_ARTIFACT_NAMES == (
        "corpus_closure_v1.json",
        "resolver_proposal_v1.json",
        "source_registry_v1.json",
        "source_relations_v1.json",
        "lgu_legacy_expected_ledger_v1.json",
    )


def test_readme_distinguishes_historic_index_from_g0a_structural_ledger():
    readme = (KR3_DIR / "README.md").read_text(encoding="utf-8")

    required_facts = (
        "148 파일 / PDF 133 / **7,475 페이지**",
        "G0-A 권위 source ledger",
        "LGU+ 2 / KT 4 / SKT legacy XLS 66",
        "`새 폴더 (2)/SKT_시험절차서_최신/`",
        "66 `READABLE` / 0 `FAILED` / 66 sheets / 8,101 inclusive used rows",
        "`semantic_parse_status: NOT_ATTEMPTED`",
        "source_registry_v1.json",
        "corpus_closure_v1.json",
        "skt_workbook_inventory_v1.json",
        "source_relations_v1.json",
        "lgu_legacy_expected_ledger_v1.json",
        "check_g0a.py --repo-root .",
        "build_corpus_closure.py --repo-root .",
        "build_source_registry.py --repo-root .",
        "build_source_relations.py",
        "build_legacy_expected_ledger.py init",
        "build_skt_workbook_inventory.py --repo-root .",
        "acquire_skt_workbook_inventory.ps1",
        "Excel/COM을 호출하지 않는다",
        "72 documents / 3 relations / LGU 28 cases / 232 expected identities",
        "214 documents: ACTIVE 72 / EXCLUDED 0 / PENDING_REVIEW 142",
        "source_scope_v2.yaml",
        "`--as-of 2026-08-14`",
        "synthetic fixture corpus",
        "`byte_drift=0` / `source_mutation=0`",
        "| 기존 LGU runnable projection | 0/28 (SKT 문서 intake로 변경되지 않음) |",
        "`project_runnable.py` 종료코드 0(schema 합법 blocker 기준 runnable 후보 0/28:",
        "static source-ledger check",
        "`validate PASS`·`runtime PASS`·`manual evidence observed`가 아니다",
    )
    for fact in required_facts:
        assert fact in readme

    assert "시험절차서 부재" not in readme
    assert "존재 여부 자체가 미확인" not in readme

    missing_section = readme.partition("## 6. 미수령 문서")[2].partition(
        "## 7. 트랙 규칙"
    )[0]
    missing_rows = tuple(
        line
        for line in missing_section.splitlines()
        if line.startswith("| ") and line != "| 문서 | 필요 이유 |"
    )
    assert missing_rows == (
        "| `[66] LGU_디바이스_Network_UI_Mandatory` | Indicator·안테나바 표시 규격 (2.1·2.2 판정) |",
        "| `CD_01 LGU 디바이스 LTE 기술요구서` | 발신 번호별 ESCV 매핑 (11.3·11.5 판정) |",
        "| `CD_02 LGU_디바이스_VoLTE_기술요구서` | VoLTE 패킷 송수신 판정 (11.2·11.4 판정) |",
        "| LGU+ 5G 영문판 | `LGU+/2026-EN/` 폴더 0건 |",
    )
    assert "| SKT 시험절차서 |" not in missing_section


def _fixture_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _synthetic_msisdn(last_four: str) -> str:
    return "".join(("010", "1234", last_four))


def _msisdn_fixture_inputs() -> tuple[dict, dict, dict]:
    fixture_value = _synthetic_msisdn("5678")
    title = f"fixture {fixture_value}"
    source_sha256 = "a" * 64
    source_path = "새 폴더 (2)/KT/example.pdf"
    corpus_index = {
        "root": "새 폴더 (2)",
        "docs": [
            {
                "rel": "KT/example.pdf",
                "sections": [
                    {"id": "2.1.1.1", "title": title},
                    {"id": "2.1.1.2", "title": "Default EPS bearer"},
                ],
            }
        ],
        "sha256": "016017561253" * 5,
    }
    allowlist = {
        "schema_version": 1,
        "tool": "corpus-msisdn-fixture-allowlist-v1",
        "source_artifact": "KR3_Carrier_Requirements/catalog/corpus_index.json",
        "expected_unique": 1,
        "expected_occurrences": 1,
        "fixtures": [
            {
                "value_sha256": _fixture_digest(fixture_value),
                "rationale": "synthetic carrier specification fixture",
                "occurrences": [
                    {
                        "source_path": source_path,
                        "source_sha256": source_sha256,
                        "section_index": 0,
                        "section_id": "2.1.1.1",
                        "title_sha256": _fixture_digest(title),
                    }
                ],
            }
        ],
    }
    closure = {
        "documents": [
            {
                "path": source_path,
                "sha256": source_sha256,
            }
        ]
    }
    return corpus_index, allowlist, closure


def test_msisdn_fixture_allowlist_scans_only_title_msisdn_with_public_detector():
    validator = getattr(check_g0a, "validate_corpus_msisdn_fixtures", None)
    assert validator is not None, "production MSISDN fixture validator is missing"
    corpus_index, allowlist, closure = _msisdn_fixture_inputs()

    counts = validator(corpus_index, allowlist, closure)

    assert counts == {
        "corpus_msisdn_fixtures": 1,
        "corpus_msisdn_occurrences": 1,
        "corpus_msisdn_documents": 1,
    }


def test_msisdn_fixture_allowlist_rejects_plain_values_and_unknown_fields():
    corpus_index, allowlist, closure = _msisdn_fixture_inputs()
    allowlist["fixtures"][0]["value"] = _synthetic_msisdn("5678")

    with pytest.raises(G0AError, match="MSISDN_FIXTURE_ALLOWLIST_INVALID"):
        check_g0a.validate_corpus_msisdn_fixtures(corpus_index, allowlist, closure)


@pytest.mark.parametrize("mutation", ("unlisted", "relocated", "source-digest"))
def test_msisdn_fixture_allowlist_fails_closed_on_occurrence_drift(mutation):
    corpus_index, allowlist, closure = _msisdn_fixture_inputs()
    if mutation == "unlisted":
        corpus_index["docs"][0]["sections"].append(
            {"id": "3", "title": f"unexpected {_synthetic_msisdn('4321')}"}
        )
    elif mutation == "relocated":
        allowlist["fixtures"][0]["occurrences"][0]["section_index"] = 1
    else:
        allowlist["fixtures"][0]["occurrences"][0]["source_sha256"] = "b" * 64

    with pytest.raises(G0AError) as caught:
        check_g0a.validate_corpus_msisdn_fixtures(corpus_index, allowlist, closure)

    assert caught.value.code == "MSISDN_FIXTURE_MISMATCH"


def test_real_msisdn_fixture_contract_pins_nine_values_and_eleven_occurrences():
    corpus_index_path = KR3_DIR / "catalog" / "corpus_index.json"
    if not corpus_index_path.exists():
        pytest.skip(
            "local-carry artifact absent: "
            "KR3_Carrier_Requirements/catalog/corpus_index.json"
        )
    schema = json.loads(MSISDN_ALLOWLIST_SCHEMA.read_text(encoding="utf-8"))
    allowlist = load_json(MSISDN_ALLOWLIST, require_serialized_canonical=True)
    corpus_index = load_json(corpus_index_path)
    closure = load_json(
        KR3_DIR / "catalog" / "corpus_closure_v1.json",
        require_serialized_canonical=True,
    )

    _validate_inventory_schema(schema, allowlist)
    counts = check_g0a.validate_corpus_msisdn_fixtures(
        corpus_index,
        allowlist,
        closure,
    )

    assert counts == {
        "corpus_msisdn_fixtures": 9,
        "corpus_msisdn_occurrences": 11,
        "corpus_msisdn_documents": 3,
    }
