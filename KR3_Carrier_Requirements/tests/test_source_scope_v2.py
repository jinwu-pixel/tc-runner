import copy
import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from g0a_common import G0AError
from source_scope_v2 import active_documents, currentness_evidence_paths, load_scope


AS_OF = date(2026, 8, 14)


def active_document(path: str = "corpus/KT/requirement.pdf") -> dict:
    return {
        "path": path,
        "state": "ACTIVE",
        "document_id": "KT_REQ_001",
        "carrier": "KT",
        "role": "REQUIREMENT",
        "media": "application/pdf",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def pending_document(path: str = "corpus/KT/pending.pdf") -> dict:
    return {
        "path": path,
        "state": "PENDING_REVIEW",
        "blocked_on": "INTERNAL_DECISION",
        "recorded_date": "2026-08-14",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def minimal_scope(documents: list[dict] | None = None) -> dict:
    return {
        "schema_version": 2,
        "corpus_parent": {
            "path": "corpus",
            "expected_entries": 2,
            "non_corpus_entries": [
                {"name": "debug", "kind": "DIRECTORY", "rationale": "test fixture"}
            ],
        },
        "corpus_roots": [{"root": "corpus/KT", "expected_total": 1}],
        "documents": documents if documents is not None else [active_document()],
        "relations": [],
        "external_gaps": [],
    }


def write_scope(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "source_scope_v2.yaml"
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    return path


def write_raw(tmp_path: Path, raw: str | bytes) -> Path:
    path = tmp_path / "source_scope_v2.yaml"
    if isinstance(raw, bytes):
        path.write_bytes(raw)
    else:
        path.write_text(raw, encoding="utf-8", newline="\n")
    return path


def test_scope_v2_accepts_literal_brackets_in_exact_repo_relative_path(tmp_path):
    bracket_path = "corpus/KT/[SKT-5G-001] requirement.pdf"
    scope = minimal_scope([active_document(bracket_path)])

    loaded = load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert loaded["documents"][0]["path"] == bracket_path
    assert active_documents(loaded)[0]["document_id"] == "KT_REQ_001"


@pytest.mark.parametrize(
    "raw",
    [
        "schema_version: 2\nschema_version: 2\n",
        "schema_version: &version 2\nother: *version\n",
        "schema_version: !custom 2\n",
        b"\xff",
    ],
)
def test_scope_v2_rejects_duplicate_alias_tag_and_invalid_utf8(tmp_path, raw):
    with pytest.raises(G0AError) as caught:
        load_scope(write_raw(tmp_path, raw), as_of=AS_OF)

    assert caught.value.code == "SCOPE_INVALID"


def test_scope_v2_rejects_non_string_path_as_controlled_scope_invalid(tmp_path):
    scope = minimal_scope()
    scope["documents"][0]["path"] = ["corpus", "KT", "requirement.pdf"]

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert caught.value.code == "SCOPE_INVALID"
    assert "documents[0].path" in caught.value.detail


@pytest.mark.parametrize(
    "raw_path",
    [
        r"corpus\KT\requirement.pdf",
        "/absolute/requirement.pdf",
        "//server/share/requirement.pdf",
        "C:/absolute/requirement.pdf",
        "corpus/../requirement.pdf",
        "corpus/./KT/requirement.pdf",
        "corpus//KT/requirement.pdf",
        "corpus/KT/",
    ],
)
def test_scope_v2_rejects_non_posix_or_noncanonical_paths(tmp_path, raw_path):
    scope = minimal_scope([active_document(raw_path)])

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert caught.value.code == "SCOPE_INVALID"


def test_scope_v2_rejects_duplicate_document_path_as_state_conflict(tmp_path):
    scope = minimal_scope([active_document(), pending_document("corpus/KT/requirement.pdf")])

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert caught.value.code == "SCOPE_STATE_CONFLICT"


def test_scope_v2_requires_pending_blocker_and_nonfuture_recorded_date(tmp_path):
    missing = minimal_scope([pending_document()])
    del missing["documents"][0]["blocked_on"]
    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, missing), as_of=AS_OF)
    assert caught.value.code == "PENDING_BLOCKER_MISSING"

    future = minimal_scope([pending_document()])
    future["documents"][0]["recorded_date"] = "2026-08-15"
    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, future), as_of=AS_OF)
    assert caught.value.code == "SCOPE_INVALID"


@pytest.mark.parametrize(
    "document",
    [
        {
            "path": "corpus/KT/duplicate.pdf",
            "state": "EXCLUDED",
            "exclusion_reason": "DUPLICATE",
            "currentness": "CURRENTNESS_UNVERIFIED",
        },
        {
            "path": "corpus/KT/superseded.pdf",
            "state": "EXCLUDED",
            "exclusion_reason": "SUPERSEDED",
            "currentness": "CURRENTNESS_UNVERIFIED",
        },
        {
            "path": "corpus/KT/reference.pdf",
            "state": "EXCLUDED",
            "exclusion_reason": "REFERENCE_ONLY",
            "currentness": "CURRENTNESS_UNVERIFIED",
        },
    ],
)
def test_scope_v2_requires_reason_specific_exclusion_evidence(tmp_path, document):
    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, minimal_scope([document])), as_of=AS_OF)

    assert caught.value.code == "EXCLUSION_EVIDENCE_MISSING"


def test_scope_v2_requires_hash_bound_currentness_evidence(tmp_path):
    document = active_document()
    document["currentness"] = "CURRENT"

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, minimal_scope([document])), as_of=AS_OF)

    assert caught.value.code == "CURRENTNESS_EVIDENCE_MISSING"

    document["verified_by"] = {
        "evidence_type": "OFFICIAL_NOTICE",
        "evidence_path": "KR3_Carrier_Requirements/evidence/currentness/notice.pdf",
        "evidence_sha256": "a" * 64,
        "verified_date": "2026-08-14",
    }
    loaded = load_scope(write_scope(tmp_path, minimal_scope([document])), as_of=AS_OF)
    assert currentness_evidence_paths(loaded) == [document["verified_by"]["evidence_path"]]


def test_scope_v2_rejects_duplicate_active_document_id(tmp_path):
    second = active_document("corpus/KT/second.pdf")
    scope = minimal_scope([active_document(), second])

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert caught.value.code == "SCOPE_INVALID"
    assert "duplicate document_id" in caught.value.detail


def test_scope_v2_validates_external_gap_shape_and_unique_id(tmp_path):
    scope = minimal_scope()
    gap = {
        "gap_id": "LGU_MISSING_DOC",
        "carrier": "LGU+",
        "description": "missing source",
        "blocked_on": "CARRIER_INQUIRY",
        "recorded_date": "2026-08-14",
    }
    scope["external_gaps"] = [gap, copy.deepcopy(gap)]

    with pytest.raises(G0AError) as caught:
        load_scope(write_scope(tmp_path, scope), as_of=AS_OF)

    assert caught.value.code == "SCOPE_INVALID"
    assert "duplicate gap_id" in caught.value.detail


def test_scope_v2_schema_is_closed_and_contains_all_state_contracts():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "source_scope_schema_v2.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "schema_version",
        "corpus_parent",
        "corpus_roots",
        "documents",
        "relations",
        "external_gaps",
    ]
    document = schema["$defs"]["document"]
    assert document["oneOf"]
    assert {branch["properties"]["state"]["const"] for branch in document["oneOf"]} == {
        "ACTIVE",
        "EXCLUDED",
        "PENDING_REVIEW",
    }
    exclusion_branches = schema["$defs"]["excludedDocument"]["allOf"][1]["oneOf"]
    assert all("not" in branch for branch in exclusion_branches)
