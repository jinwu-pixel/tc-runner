import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from build_resolver_proposal import (
    build_proposal,
    build_proposal_from_paths,
    validate_stored_proposal,
)
from g0a_common import G0AError, sha256_bytes, write_json


def _document(
    path: str,
    digest: str,
    *,
    state: str = "PENDING_REVIEW",
) -> dict:
    item = {
        "currentness": "CURRENTNESS_UNVERIFIED",
        "path": path,
        "root": "corpus/KT",
        "sha256": digest,
        "size_bytes": 1,
        "state": state,
    }
    if state == "ACTIVE":
        item["document_id"] = "KT_ACTIVE_001"
    else:
        item["blocked_on"] = "INTERNAL_DECISION"
        item["recorded_date"] = "2026-08-14"
    return item


def _closure(documents: list[dict]) -> dict:
    ordered = sorted(documents, key=lambda item: item["path"].encode("utf-8"))
    active = sum(item["state"] == "ACTIVE" for item in ordered)
    pending = sum(item["state"] == "PENDING_REVIEW" for item in ordered)
    return {
        "corpus_parent": "corpus",
        "documents": ordered,
        "generator": {"name": "build_corpus_closure", "version": "1"},
        "schema_version": 1,
        "source_scope_path": (
            "KR3_Carrier_Requirements/contracts/source_scope_v2.yaml"
        ),
        "source_scope_sha256": "f" * 64,
        "summary": {
            "active": active,
            "currentness": {
                "CURRENT": 0,
                "CURRENTNESS_UNVERIFIED": len(ordered),
            },
            "excluded": 0,
            "oldest_pending_recorded_date": "2026-08-14" if pending else None,
            "pending_by_resolver": {
                "CARRIER_INQUIRY": 0,
                "INTERNAL_DECISION": pending,
                "INTAKE_CAPABILITY": 0,
            },
            "pending_review": pending,
            "roots": {
                "corpus/KT": {
                    "active": active,
                    "excluded": 0,
                    "pending_review": pending,
                    "total": len(ordered),
                }
            },
            "total": len(ordered),
            "unclassified": 0,
        },
    }


def test_build_proposal_applies_first_match_rules_and_complete_duplicate_evidence():
    closure = _closure(
        [
            _document("corpus/KT/active.pdf", "a" * 64, state="ACTIVE"),
            _document("corpus/KT/duplicate.zip", "a" * 64),
            _document("corpus/KT/group-3.pdf", "b" * 64),
            _document("corpus/KT/group-1.pdf", "b" * 64),
            _document("corpus/KT/group-2.pdf", "b" * 64),
            _document("corpus/KT/artwork.AI", "c" * 64),
            _document("corpus/KT/manual.DoCx", "d" * 64),
            _document("corpus/KT/spec.PDF", "e" * 64),
        ]
    )

    proposal = build_proposal(
        closure,
        closure_sha256="1" * 64,
        source_scope_sha256="2" * 64,
    )

    by_path = {item["path"]: item for item in proposal["proposals"]}
    assert by_path["corpus/KT/duplicate.zip"]["basis"] == (
        "SHA256_DUPLICATE_IN_CORPUS"
    )
    assert by_path["corpus/KT/artwork.AI"]["basis"] == "NON_DOCUMENT_ASSET"
    assert by_path["corpus/KT/manual.DoCx"]["basis"] == "UNSUPPORTED_MEDIA"
    assert by_path["corpus/KT/spec.PDF"]["basis"] == "NORMATIVITY_UNKNOWN"
    assert by_path["corpus/KT/duplicate.zip"]["evidence"] == {
        "duplicate_group_paths": [
            "corpus/KT/active.pdf",
            "corpus/KT/duplicate.zip",
        ],
        "duplicate_group_sha256": "a" * 64,
    }
    assert by_path["corpus/KT/group-1.pdf"]["evidence"] == {
        "duplicate_group_paths": [
            "corpus/KT/group-1.pdf",
            "corpus/KT/group-2.pdf",
            "corpus/KT/group-3.pdf",
        ],
        "duplicate_group_sha256": "b" * 64,
    }
    assert [item["path"] for item in proposal["proposals"]] == sorted(
        by_path,
        key=lambda path: path.encode("utf-8"),
    )
    assert proposal["summary"] == {
        "by_basis": {
            "NON_DOCUMENT_ASSET": 1,
            "NORMATIVITY_UNKNOWN": 1,
            "SHA256_DUPLICATE_IN_CORPUS": 4,
            "UNSUPPORTED_MEDIA": 1,
        },
        "by_resolver": {
            "CARRIER_INQUIRY": 1,
            "INTERNAL_DECISION": 5,
            "INTAKE_CAPABILITY": 1,
        },
        "duplicate_group_count": 2,
        "duplicate_member_count": 4,
        "roots": {
            "corpus/KT": {
                "by_resolver": {
                    "CARRIER_INQUIRY": 1,
                    "INTERNAL_DECISION": 5,
                    "INTAKE_CAPABILITY": 1,
                }
            }
        },
        "total": 7,
    }


def _stored_fixture() -> tuple[dict, dict]:
    closure = _closure(
        [
            _document("corpus/KT/active.pdf", "a" * 64, state="ACTIVE"),
            _document("corpus/KT/duplicate.zip", "a" * 64),
            _document("corpus/KT/artwork.AI", "b" * 64),
            _document("corpus/KT/manual.docx", "c" * 64),
            _document("corpus/KT/spec.pdf", "d" * 64),
        ]
    )
    return closure, build_proposal(
        closure,
        closure_sha256="1" * 64,
        source_scope_sha256="2" * 64,
    )


def _assert_error_code(code: str, value: object, closure: dict) -> None:
    with pytest.raises(G0AError) as caught:
        validate_stored_proposal(
            value,
            closure,
            closure_sha256="1" * 64,
            source_scope_sha256="2" * 64,
        )
    assert caught.value.code == code


def test_validate_stored_proposal_rejects_malformed_keys_and_evidence():
    closure, proposal = _stored_fixture()

    extra_key = copy.deepcopy(proposal)
    extra_key["unexpected"] = True
    _assert_error_code("PROPOSAL_INVALID", extra_key, closure)

    missing_evidence = copy.deepcopy(proposal)
    missing_evidence["proposals"][1]["evidence"].pop("duplicate_group_paths")
    _assert_error_code("PROPOSAL_INVALID", missing_evidence, closure)


@pytest.mark.parametrize("pin", ["closure_sha256", "source_scope_sha256"])
def test_validate_stored_proposal_rejects_either_stale_input_hash(pin):
    closure, proposal = _stored_fixture()
    proposal[pin] = "9" * 64

    _assert_error_code("PROPOSAL_STALE", proposal, closure)


@pytest.mark.parametrize("change", ["remove", "add"])
def test_validate_stored_proposal_rejects_pending_path_set_drift(change):
    closure, proposal = _stored_fixture()
    if change == "remove":
        proposal["proposals"].pop()
    else:
        proposal["proposals"].append(copy.deepcopy(proposal["proposals"][-1]))
        proposal["proposals"][-1]["path"] = "corpus/KT/unexpected.pdf"

    _assert_error_code("PROPOSAL_SET_MISMATCH", proposal, closure)


@pytest.mark.parametrize("field", ["basis", "blocked_on", "evidence"])
def test_validate_stored_proposal_rejects_recomputed_rule_drift(field):
    closure, proposal = _stored_fixture()
    item = proposal["proposals"][-1]
    if field == "basis":
        item["basis"] = "UNSUPPORTED_MEDIA"
        item["blocked_on"] = "INTAKE_CAPABILITY"
        item["evidence"] = {"extension": ".pdf"}
    elif field == "blocked_on":
        item["blocked_on"] = "INTERNAL_DECISION"
    else:
        duplicate_item = next(
            candidate
            for candidate in proposal["proposals"]
            if candidate["basis"] == "SHA256_DUPLICATE_IN_CORPUS"
        )
        duplicate_item["evidence"]["duplicate_group_sha256"] = "e" * 64

    _assert_error_code("PROPOSAL_BASIS_DRIFT", proposal, closure)


def test_validate_stored_proposal_does_not_compare_scope_resolver_assignment():
    closure, proposal = _stored_fixture()

    assert {item["blocked_on"] for item in closure["documents"] if item["state"] == "PENDING_REVIEW"} == {
        "INTERNAL_DECISION"
    }
    assert validate_stored_proposal(
        proposal,
        closure,
        closure_sha256="1" * 64,
        source_scope_sha256="2" * 64,
    ) == proposal


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, dict]:
    scope_path = tmp_path / "source_scope_v2.yaml"
    scope_path.write_bytes(b"schema_version: 2\n")
    closure, _ = _stored_fixture()
    closure["source_scope_sha256"] = sha256_bytes(scope_path.read_bytes())
    closure_path = tmp_path / "corpus_closure_v1.json"
    write_json(closure_path, closure)
    return closure_path, scope_path, closure


def test_build_proposal_from_paths_hash_binds_exact_canonical_inputs(tmp_path):
    closure_path, scope_path, _ = _write_inputs(tmp_path)

    proposal = build_proposal_from_paths(closure_path, scope_path)

    assert proposal["closure_sha256"] == sha256_bytes(closure_path.read_bytes())
    assert proposal["source_scope_sha256"] == sha256_bytes(scope_path.read_bytes())


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'{"value":NaN}',
    ],
)
def test_build_proposal_from_paths_rejects_duplicate_key_and_nonfinite_json(
    tmp_path,
    raw,
):
    closure_path, scope_path, _ = _write_inputs(tmp_path)
    closure_path.write_bytes(raw)

    with pytest.raises(G0AError) as caught:
        build_proposal_from_paths(closure_path, scope_path)

    assert caught.value.code == "PROPOSAL_INVALID"


def test_build_proposal_from_paths_rejects_noncanonical_json_and_stale_scope_pin(
    tmp_path,
):
    closure_path, scope_path, closure = _write_inputs(tmp_path)
    closure_path.write_text(
        json.dumps(closure, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(G0AError) as caught:
        build_proposal_from_paths(closure_path, scope_path)
    assert caught.value.code == "PROPOSAL_INVALID"

    write_json(closure_path, closure)
    scope_path.write_bytes(b"schema_version: 2\nchanged: true\n")
    with pytest.raises(G0AError) as caught:
        build_proposal_from_paths(closure_path, scope_path)
    assert caught.value.code == "PROPOSAL_STALE"


def test_cli_is_canonical_deterministic_arbitrary_cwd_and_scope_read_only(tmp_path):
    closure_path, scope_path, _ = _write_inputs(tmp_path)
    script = Path(__file__).resolve().parents[1] / "tools" / "build_resolver_proposal.py"
    first_out = tmp_path / "first.json"
    second_out = tmp_path / "second.json"
    scope_before = (scope_path.read_bytes(), scope_path.stat().st_mtime_ns)
    base_args = [
        sys.executable,
        str(script),
        "--closure",
        str(closure_path),
        "--scope",
        str(scope_path),
    ]

    first = subprocess.run(
        [*base_args, "--out", str(first_out)],
        cwd=Path(tmp_path).anchor,
        capture_output=True,
        text=True,
        check=False,
    )
    second = subprocess.run(
        [*base_args, "--out", str(second_out)],
        cwd=Path(tmp_path).anchor,
        capture_output=True,
        text=True,
        check=False,
    )

    assert first.returncode == second.returncode == 0
    assert first_out.read_bytes() == second_out.read_bytes()
    assert first_out.read_bytes().endswith(b"\n")
    assert scope_before == (scope_path.read_bytes(), scope_path.stat().st_mtime_ns)

    closure_path.write_bytes(b'{"value":Infinity}')
    failed = subprocess.run(
        [*base_args, "--out", str(first_out)],
        cwd=Path(tmp_path).anchor,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2
    assert failed.stderr.startswith("PROPOSAL_INVALID:")
    assert "Traceback" not in failed.stderr


def test_published_schema_is_closed_draft_2020_12_and_validates_proposal():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "resolver_proposal_schema_v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    closure, proposal = _stored_fixture()
    validator = jsonschema.Draft202012Validator(schema)

    assert list(validator.iter_errors(proposal)) == []
    proposal["unexpected"] = True
    assert list(validator.iter_errors(proposal))
