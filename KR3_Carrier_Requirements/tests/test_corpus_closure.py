import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_corpus_closure import (
    build_closure,
    closure_source_state,
    validate_stored_closure,
)
from g0a_common import G0AError, canonical_json_bytes, sha256_bytes


AS_OF = date(2026, 8, 14)


def active(path: str = "corpus/KT/[KT-REQ-001] requirement.pdf") -> dict:
    return {
        "path": path,
        "state": "ACTIVE",
        "document_id": "KT_REQ_001",
        "carrier": "KT",
        "role": "REQUIREMENT",
        "media": "application/pdf",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def pending(path: str = "corpus/KT/pending.pdf") -> dict:
    return {
        "path": path,
        "state": "PENDING_REVIEW",
        "blocked_on": "INTERNAL_DECISION",
        "recorded_date": "2026-08-14",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def scope_value(documents: list[dict] | None = None, *, expected_total: int = 2) -> dict:
    return {
        "schema_version": 2,
        "corpus_parent": {
            "path": "corpus",
            "expected_entries": 2,
            "non_corpus_entries": [
                {"name": "debug", "kind": "DIRECTORY", "rationale": "fixture output"}
            ],
        },
        "corpus_roots": [{"root": "corpus/KT", "expected_total": expected_total}],
        "documents": documents if documents is not None else [active(), pending()],
        "relations": [],
        "external_gaps": [],
    }


def install_fixture(tmp_path: Path, scope: dict | None = None) -> tuple[Path, Path]:
    (tmp_path / "corpus" / "KT").mkdir(parents=True)
    (tmp_path / "corpus" / "debug").mkdir()
    (tmp_path / "corpus" / "KT" / "[KT-REQ-001] requirement.pdf").write_bytes(b"active")
    (tmp_path / "corpus" / "KT" / "pending.pdf").write_bytes(b"pending")
    scope_path = (
        tmp_path
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "source_scope_v2.yaml"
    )
    scope_path.parent.mkdir(parents=True)
    scope_path.write_text(
        yaml.safe_dump(scope or scope_value(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    return tmp_path, scope_path


def test_build_closure_hashes_active_and_pending_and_emits_stable_summary(tmp_path):
    repo, scope_path = install_fixture(tmp_path)

    closure = build_closure(repo, scope_path, as_of=AS_OF)

    assert closure["schema_version"] == 1
    assert closure["source_scope_path"] == (
        "KR3_Carrier_Requirements/contracts/source_scope_v2.yaml"
    )
    assert closure["source_scope_sha256"] == sha256_bytes(scope_path.read_bytes())
    assert [item["path"] for item in closure["documents"]] == [
        "corpus/KT/[KT-REQ-001] requirement.pdf",
        "corpus/KT/pending.pdf",
    ]
    assert closure["documents"][1]["sha256"] == sha256_bytes(b"pending")
    assert closure["summary"] == {
        "active": 1,
        "currentness": {"CURRENT": 0, "CURRENTNESS_UNVERIFIED": 2},
        "excluded": 0,
        "oldest_pending_recorded_date": "2026-08-14",
        "pending_by_resolver": {
            "CARRIER_INQUIRY": 0,
            "INTERNAL_DECISION": 1,
            "INTAKE_CAPABILITY": 0,
        },
        "pending_review": 1,
        "roots": {
            "corpus/KT": {
                "active": 1,
                "excluded": 0,
                "pending_review": 1,
                "total": 2,
            }
        },
        "total": 2,
        "unclassified": 0,
    }


def test_new_file_is_unclassified_not_automatically_pending(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    (repo / "corpus" / "KT" / "extra.pdf").write_bytes(b"new")

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)

    assert caught.value.code == "SCOPE_UNCLASSIFIED"
    assert "corpus/KT/extra.pdf" in caught.value.detail


def test_declared_missing_path_fails_closed(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    (repo / "corpus" / "KT" / "pending.pdf").unlink()

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)

    assert caught.value.code == "SCOPE_PATH_MISSING"
    assert "corpus/KT/pending.pdf" in caught.value.detail


def test_parent_entry_set_and_kind_are_exact(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    (repo / "corpus" / "unexpected").mkdir()
    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)
    assert caught.value.code == "SCOPE_PARENT_DRIFT"

    (repo / "corpus" / "unexpected").rmdir()
    (repo / "corpus" / "debug").rmdir()
    (repo / "corpus" / "debug").write_bytes(b"wrong kind")
    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)
    assert caught.value.code == "SCOPE_PARENT_KIND_MISMATCH"


def test_root_total_is_independent_regression_guard(tmp_path):
    repo, scope_path = install_fixture(tmp_path, scope_value(expected_total=3))

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)

    assert caught.value.code == "SCOPE_TOTAL_MISMATCH"


def duplicate(path: str, duplicate_of: str) -> dict:
    return {
        "path": path,
        "state": "EXCLUDED",
        "exclusion_reason": "DUPLICATE",
        "duplicate_of": duplicate_of,
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def test_duplicate_exclusion_requires_active_target_and_equal_hash(tmp_path):
    canonical = "corpus/KT/[KT-REQ-001] requirement.pdf"
    duplicate_path = "corpus/KT/pending.pdf"
    scope = scope_value([active(canonical), duplicate(duplicate_path, canonical)])
    repo, scope_path = install_fixture(tmp_path, scope)

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)
    assert caught.value.code == "DUPLICATE_HASH_MISMATCH"

    (repo / duplicate_path).write_bytes(b"active")
    closure = build_closure(repo, scope_path, as_of=AS_OF)
    assert closure["summary"]["excluded"] == 1


def test_duplicate_exclusion_rejects_nonactive_or_self_target(tmp_path):
    duplicate_path = "corpus/KT/pending.pdf"
    scope = scope_value([active(), duplicate(duplicate_path, duplicate_path)])
    repo, scope_path = install_fixture(tmp_path, scope)

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)

    assert caught.value.code == "DUPLICATE_HASH_MISMATCH"


def test_superseded_exclusion_requires_existing_active_document_id(tmp_path):
    superseded = {
        "path": "corpus/KT/pending.pdf",
        "state": "EXCLUDED",
        "exclusion_reason": "SUPERSEDED",
        "superseded_by": "MISSING",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }
    repo, scope_path = install_fixture(tmp_path, scope_value([active(), superseded]))

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)

    assert caught.value.code == "SUPERSEDED_TARGET_UNKNOWN"


def test_currentness_evidence_is_path_and_hash_verified(tmp_path):
    current = active()
    current["currentness"] = "CURRENT"
    current["verified_by"] = {
        "evidence_type": "OFFICIAL_NOTICE",
        "evidence_path": "evidence/currentness/notice.pdf",
        "evidence_sha256": "a" * 64,
        "verified_date": "2026-08-14",
    }
    repo, scope_path = install_fixture(tmp_path, scope_value([current, pending()]))

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)
    assert caught.value.code == "CURRENTNESS_EVIDENCE_MISSING"

    evidence = repo / "evidence" / "currentness" / "notice.pdf"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"notice")
    current["verified_by"]["evidence_sha256"] = sha256_bytes(b"notice")
    scope_path.write_text(
        yaml.safe_dump(scope_value([current, pending()]), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    closure = build_closure(repo, scope_path, as_of=AS_OF)
    assert closure["summary"]["currentness"]["CURRENT"] == 1


def test_closure_is_deterministic_and_source_state_covers_pending(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    first = build_closure(repo, scope_path, as_of=AS_OF)
    second = build_closure(repo, scope_path, as_of=AS_OF)

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    state = closure_source_state(first, repo)
    assert set(state) == {
        "corpus/KT/[KT-REQ-001] requirement.pdf",
        "corpus/KT/pending.pdf",
    }
    assert state["corpus/KT/pending.pdf"][0] == sha256_bytes(b"pending")


def test_stored_closure_validation_is_closed_and_hash_strict(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    closure = build_closure(repo, scope_path, as_of=AS_OF)
    assert validate_stored_closure(closure) == closure

    closure["documents"][0]["sha256"] = "A" * 64
    with pytest.raises(G0AError) as caught:
        validate_stored_closure(closure)
    assert caught.value.code == "CORPUS_CLOSURE_INVALID"


def test_stored_closure_rejects_state_specific_semantic_drift(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    closure = build_closure(repo, scope_path, as_of=AS_OF)

    empty_active_id = json.loads(json.dumps(closure))
    empty_active_id["documents"][0]["document_id"] = ""
    with pytest.raises(G0AError) as caught:
        validate_stored_closure(empty_active_id)
    assert caught.value.code == "CORPUS_CLOSURE_INVALID"

    invalid_pending_date = json.loads(json.dumps(closure))
    invalid_pending_date["documents"][1]["recorded_date"] = "not-a-date"
    invalid_pending_date["summary"]["oldest_pending_recorded_date"] = "not-a-date"
    with pytest.raises(G0AError) as caught:
        validate_stored_closure(invalid_pending_date)
    assert caught.value.code == "CORPUS_CLOSURE_INVALID"

    canonical = "corpus/KT/[KT-REQ-001] requirement.pdf"
    duplicate_path = "corpus/KT/pending.pdf"
    duplicate_scope = scope_value([active(canonical), duplicate(duplicate_path, canonical)])
    duplicate_scope_path = install_fixture(tmp_path / "excluded", duplicate_scope)[1]
    (tmp_path / "excluded" / duplicate_path).write_bytes(b"active")
    excluded = build_closure(tmp_path / "excluded", duplicate_scope_path, as_of=AS_OF)
    excluded["documents"][1]["exclusion_reason"] = "UNKNOWN"
    with pytest.raises(G0AError) as caught:
        validate_stored_closure(excluded)
    assert caught.value.code == "CORPUS_CLOSURE_INVALID"


def test_linked_document_is_rejected_when_platform_allows_symlink(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    source = repo / "outside.pdf"
    source.write_bytes(b"pending")
    linked = repo / "corpus" / "KT" / "pending.pdf"
    linked.unlink()
    try:
        os.symlink(source, linked)
    except OSError as error:
        pytest.skip(f"symlink unavailable: {error}")

    with pytest.raises(G0AError) as caught:
        build_closure(repo, scope_path, as_of=AS_OF)
    assert caught.value.code == "SCOPE_INVALID"


def test_cli_writes_canonical_artifact_and_errors_without_traceback(tmp_path):
    repo, scope_path = install_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "tools" / "build_corpus_closure.py"
    out = tmp_path / "closure.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo),
            "--scope",
            str(scope_path),
            "--out",
            str(out),
            "--as-of",
            "2026-08-14",
        ],
        cwd=Path(tmp_path).anchor,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["summary"]["total"] == 2
    assert out.read_bytes().endswith(b"\n")

    (repo / "corpus" / "KT" / "extra.pdf").write_bytes(b"new")
    failed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo),
            "--scope",
            str(scope_path),
            "--out",
            str(out),
            "--as-of",
            "2026-08-14",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2
    assert failed.stderr.startswith("SCOPE_UNCLASSIFIED:")
    assert "Traceback" not in failed.stderr


def test_closure_schema_is_closed_and_requires_full_hashes():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "corpus_closure_schema_v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    item = schema["properties"]["documents"]["items"]
    assert item["additionalProperties"] is False
    assert len(item["allOf"]) == 3
    assert item["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}(?![\\s\\S])"

    summary = schema["properties"]["summary"]["properties"]
    roots = summary["roots"]
    assert roots["additionalProperties"]["additionalProperties"] is False
    assert set(roots["additionalProperties"]["required"]) == {
        "active",
        "excluded",
        "pending_review",
        "total",
    }

    pending = summary["pending_by_resolver"]
    assert pending["additionalProperties"] is False
    assert set(pending["required"]) == {
        "CARRIER_INQUIRY",
        "INTERNAL_DECISION",
        "INTAKE_CAPABILITY",
    }

    currentness = summary["currentness"]
    assert currentness["additionalProperties"] is False
    assert set(currentness["required"]) == {
        "CURRENT",
        "CURRENTNESS_UNVERIFIED",
    }
