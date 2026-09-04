import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from g0a_common import G0AError, canonical_json_bytes

from build_source_relations import build_relations, load_registry
from build_source_registry import load_scope


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def relation(relation_id: str, kind: str, source_id: str, target_id: str) -> dict:
    return {
        "relation_id": relation_id,
        "kind": kind,
        "source_document_id": source_id,
        "target_document_id": target_id,
    }


def document(document_id: str, role: str, sha256: str) -> dict:
    return {
        "document_id": document_id,
        "carrier": "KT",
        "role": role,
        "media_type": "application/pdf",
        "path": f"sources/{document_id}.pdf",
        "size_bytes": 1,
        "sha256": sha256,
        "intake": {
            "container_status": "READABLE",
            "semantic_parse_status": "NOT_APPLICABLE",
            "semantic_parser": None,
        },
    }


def registry_value() -> dict:
    return {
        "schema_version": 1,
        "documents": [
            document("REQ_A", "REQUIREMENT", HASH_A),
            document("PROC_A", "PROCEDURE", HASH_B),
            document("SAT_A", "SAT", HASH_C),
        ],
    }


def scope_value(relations: list[dict]) -> dict:
    return {
        "schema_version": 2,
        "corpus_parent": {
            "path": "sources",
            "expected_entries": 1,
            "non_corpus_entries": [],
        },
        "corpus_roots": [{"root": "sources/KT", "expected_total": 3}],
        "documents": [
            {
                "path": "sources/KT/REQ_A.pdf",
                "state": "ACTIVE",
                "document_id": "REQ_A",
                "carrier": "KT",
                "role": "REQUIREMENT",
                "media": "application/pdf",
                "currentness": "CURRENTNESS_UNVERIFIED",
            },
            {
                "path": "sources/KT/PROC_A.pdf",
                "state": "ACTIVE",
                "document_id": "PROC_A",
                "carrier": "KT",
                "role": "PROCEDURE",
                "media": "application/pdf",
                "currentness": "CURRENTNESS_UNVERIFIED",
            },
            {
                "path": "sources/KT/SAT_A.pdf",
                "state": "ACTIVE",
                "document_id": "SAT_A",
                "carrier": "KT",
                "role": "SAT",
                "media": "application/pdf",
                "currentness": "CURRENTNESS_UNVERIFIED",
            },
        ],
        "relations": relations,
        "external_gaps": [],
    }


def test_build_relations_rejects_endpoint_not_declared_active():
    scope = scope_value(
        [relation("REQ_TO_PENDING", "REQUIREMENT_TO_SAT", "REQ_A", "PENDING_DOC")]
    )
    scope["documents"].append(
        {
            "path": "sources/KT/pending.pdf",
            "state": "PENDING_REVIEW",
            "blocked_on": "INTERNAL_DECISION",
            "recorded_date": "2026-08-14",
            "currentness": "CURRENTNESS_UNVERIFIED",
        }
    )

    with pytest.raises(G0AError) as caught:
        build_relations(scope, registry_value())

    assert caught.value.code == "RELATION_ENDPOINT_NOT_ACTIVE"


def write_yaml(path: Path, value: dict) -> Path:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    return path


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_build_relations_emits_relations_in_lexical_id_order_with_registry_hashes():
    relations = [
        relation("Z_REQ_TO_SAT", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"),
        relation("A_REQ_TO_PROC", "REQUIREMENT_TO_PROCEDURE", "REQ_A", "PROC_A"),
        relation("M_REQ_TO_SAT", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A_2"),
    ]
    registry = registry_value()
    registry["documents"].append(document("SAT_A_2", "SAT", "d" * 64))
    scope = scope_value(relations)
    scope["documents"].append(
        {
            "path": "sources/KT/SAT_A_2.pdf",
            "state": "ACTIVE",
            "document_id": "SAT_A_2",
            "carrier": "KT",
            "role": "SAT",
            "media": "application/pdf",
            "currentness": "CURRENTNESS_UNVERIFIED",
        }
    )

    built = build_relations(scope, registry)

    assert built == {
        "schema_version": 1,
        "relations": [
            {
                "relation_id": "A_REQ_TO_PROC",
                "kind": "REQUIREMENT_TO_PROCEDURE",
                "source_document_id": "REQ_A",
                "source_sha256": HASH_A,
                "target_document_id": "PROC_A",
                "target_sha256": HASH_B,
            },
            {
                "relation_id": "M_REQ_TO_SAT",
                "kind": "REQUIREMENT_TO_SAT",
                "source_document_id": "REQ_A",
                "source_sha256": HASH_A,
                "target_document_id": "SAT_A_2",
                "target_sha256": "d" * 64,
            },
            {
                "relation_id": "Z_REQ_TO_SAT",
                "kind": "REQUIREMENT_TO_SAT",
                "source_document_id": "REQ_A",
                "source_sha256": HASH_A,
                "target_document_id": "SAT_A",
                "target_sha256": HASH_C,
            },
        ],
    }


@pytest.mark.parametrize("field", ["source_document_id", "target_document_id"])
def test_build_relations_rejects_dangling_source_or_target_document(field):
    item = relation("REQ_TO_SAT", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A")
    item[field] = "MISSING"

    with pytest.raises(G0AError) as caught:
        build_relations(scope_value([item]), registry_value())

    assert caught.value.code == "RELATION_ENDPOINT_NOT_ACTIVE"


def test_build_relations_rejects_wrong_required_role_pair():
    item = relation("REQ_TO_PROC", "REQUIREMENT_TO_PROCEDURE", "REQ_A", "SAT_A")

    with pytest.raises(G0AError) as caught:
        build_relations(scope_value([item]), registry_value())

    assert caught.value.code == "RELATION_ROLE_MISMATCH"


def test_build_relations_rejects_duplicate_relation_id():
    relations = [
        relation("DUP", "REQUIREMENT_TO_PROCEDURE", "REQ_A", "PROC_A"),
        relation("DUP", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"),
    ]

    with pytest.raises(G0AError) as caught:
        build_relations(scope_value(relations), registry_value())

    assert caught.value.code == "RELATION_DUPLICATE_ID"


def test_build_relations_rejects_duplicate_source_target_pair_under_different_id():
    relations = [
        relation("ONE", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"),
        relation("TWO", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"),
    ]

    with pytest.raises(G0AError) as caught:
        build_relations(scope_value(relations), registry_value())

    assert caught.value.code == "RELATION_DUPLICATE_PAIR"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda registry: registry["documents"].append(document("REQ_A", "REQUIREMENT", HASH_A)),
        lambda registry: registry["documents"].__setitem__(0, {**registry["documents"][0], "document_id": ""}),
        lambda registry: registry["documents"].__setitem__(0, {**registry["documents"][0], "sha256": "A" * 64}),
        lambda registry: registry["documents"].__setitem__(0, {**registry["documents"][0], "sha256": "a" * 63}),
        lambda registry: registry["documents"][0]["intake"].__setitem__("container_status", []),
        lambda registry: registry["documents"][0]["intake"].__setitem__("semantic_parse_status", []),
        lambda registry: registry["documents"][0]["intake"].__setitem__("semantic_parser", ""),
    ],
)
def test_load_registry_rejects_duplicate_or_malformed_ids_and_hashes(tmp_path, mutate):
    registry = registry_value()
    mutate(registry)
    path = write_json(tmp_path / "registry.json", registry)

    with pytest.raises(G0AError) as caught:
        load_registry(path)

    assert caught.value.code == "SOURCE_REGISTRY_INVALID"


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"schema_version": 1},
        {"schema_version": 1, "documents": [], "extra": True},
        {"schema_version": True, "documents": []},
    ],
)
def test_load_registry_fails_closed_for_nonobject_or_wrong_root_shape(tmp_path, value):
    path = write_json(tmp_path / "registry.json", value)

    with pytest.raises(G0AError) as caught:
        load_registry(path)

    assert caught.value.code == "SOURCE_REGISTRY_INVALID"


def test_load_registry_wraps_invalid_utf8_as_controlled_registry_error(tmp_path):
    path = tmp_path / "registry.json"
    path.write_bytes(b"\xff")

    with pytest.raises(G0AError) as caught:
        load_registry(path)

    assert caught.value.code == "SOURCE_REGISTRY_INVALID"


@pytest.mark.parametrize(
    "item",
    [
        relation("UNKNOWN", "UNKNOWN", "REQ_A", "SAT_A"),
        {**relation("EXTRA", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"), "extra": "no"},
        {key: value for key, value in relation("MISSING", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A").items() if key != "kind"},
        relation("SELF", "REQUIREMENT_TO_SAT", "REQ_A", "REQ_A"),
    ],
)
def test_build_relations_rejects_invalid_declaration_shapes_and_values(item):
    with pytest.raises(G0AError) as caught:
        build_relations(scope_value([item]), registry_value())

    assert caught.value.code == "RELATION_INVALID"


def test_build_relations_is_canonical_byte_identical_across_two_builds():
    relations = [
        relation("B", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A"),
        relation("A", "REQUIREMENT_TO_PROCEDURE", "REQ_A", "PROC_A"),
    ]
    scope = scope_value(relations)
    registry = registry_value()

    assert canonical_json_bytes(build_relations(scope, registry)) == canonical_json_bytes(
        build_relations(scope, registry)
    )


def test_cli_writes_valid_relations_and_returns_controlled_error_without_traceback(tmp_path):
    script = Path(__file__).resolve().parents[1] / "tools" / "build_source_relations.py"
    scope_path = write_yaml(
        tmp_path / "scope.yaml",
        scope_value([relation("REQ_TO_SAT", "REQUIREMENT_TO_SAT", "REQ_A", "SAT_A")]),
    )
    registry_path = write_json(tmp_path / "registry.json", registry_value())
    out_path = tmp_path / "relations.json"

    valid = subprocess.run(
        [
            sys.executable,
            str(script),
            "--scope",
            str(scope_path),
            "--registry",
            str(registry_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert valid.returncode == 0
    assert json.loads(out_path.read_text(encoding="utf-8"))["relations"][0]["source_sha256"] == HASH_A

    malformed_scope = write_yaml(tmp_path / "malformed.yaml", scope_value([relation("BAD", "UNKNOWN", "REQ_A", "SAT_A")]))
    malformed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--scope",
            str(malformed_scope),
            "--registry",
            str(registry_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert malformed.returncode == 2
    assert malformed.stderr.startswith("SCOPE_INVALID:")
    assert "Traceback" not in malformed.stderr

    registry_path.write_bytes(b"\xff")
    invalid_utf8 = subprocess.run(
        [
            sys.executable,
            str(script),
            "--scope",
            str(scope_path),
            "--registry",
            str(registry_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert invalid_utf8.returncode == 2
    assert invalid_utf8.stderr.startswith("SOURCE_REGISTRY_INVALID:")
    assert "Traceback" not in invalid_utf8.stderr


def test_relation_schema_is_closed_and_requires_full_hashes():
    schema_path = Path(__file__).resolve().parents[1] / "contracts" / "source_relations_schema_v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["schema_version", "relations"]
    item = schema["properties"]["relations"]["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == [
        "relation_id",
        "kind",
        "source_document_id",
        "source_sha256",
        "target_document_id",
        "target_sha256",
    ]
    assert item["properties"]["source_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert item["properties"]["target_sha256"]["pattern"] == "^[0-9a-f]{64}$"
