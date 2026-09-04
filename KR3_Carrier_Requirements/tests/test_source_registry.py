import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_source_registry import build_registry, load_scope
from g0a_common import G0AError, canonical_json_bytes, sha256_bytes


AS_OF = date(2026, 8, 14)
OLE_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")


def active(
    path: str,
    document_id: str,
    *,
    media: str = "application/pdf",
    carrier: str = "KT",
    role: str = "REQUIREMENT",
) -> dict:
    return {
        "path": path,
        "state": "ACTIVE",
        "document_id": document_id,
        "carrier": carrier,
        "role": role,
        "media": media,
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def pending(path: str) -> dict:
    return {
        "path": path,
        "state": "PENDING_REVIEW",
        "blocked_on": "INTERNAL_DECISION",
        "recorded_date": "2026-08-14",
        "currentness": "CURRENTNESS_UNVERIFIED",
    }


def scope_value(documents: list[dict]) -> dict:
    return {
        "schema_version": 2,
        "corpus_parent": {
            "path": "corpus",
            "expected_entries": 1,
            "non_corpus_entries": [],
        },
        "corpus_roots": [{"root": "corpus/KT", "expected_total": len(documents)}],
        "documents": documents,
        "relations": [],
        "external_gaps": [],
    }


def install(tmp_path: Path, documents: list[dict], contents: dict[str, bytes]) -> Path:
    (tmp_path / "corpus" / "KT").mkdir(parents=True)
    for raw_path, content in contents.items():
        path = tmp_path.joinpath(*Path(raw_path).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    scope_path = (
        tmp_path
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "source_scope_v2.yaml"
    )
    scope_path.parent.mkdir(parents=True)
    scope_path.write_text(
        yaml.safe_dump(scope_value(documents), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    return scope_path


def test_registry_projects_only_active_documents_with_explicit_stable_ids(tmp_path):
    active_path = "corpus/KT/[KT-REQ-001] requirement.pdf"
    pending_path = "corpus/KT/pending.pdf"
    scope_path = install(
        tmp_path,
        [active(active_path, "KT_REQ_001"), pending(pending_path)],
        {active_path: b"active", pending_path: b"pending"},
    )

    registry = build_registry(tmp_path, scope_path)

    assert registry == {
        "schema_version": 1,
        "documents": [
            {
                "document_id": "KT_REQ_001",
                "carrier": "KT",
                "role": "REQUIREMENT",
                "media_type": "application/pdf",
                "path": active_path,
                "size_bytes": 6,
                "sha256": sha256_bytes(b"active"),
                "intake": {
                    "container_status": "READABLE",
                    "semantic_parse_status": "NOT_APPLICABLE",
                    "semantic_parser": None,
                },
            }
        ],
    }


@pytest.mark.parametrize(
    ("content", "expected_status"),
    [
        (OLE_SIGNATURE + b"xls", "READABLE"),
        (b"not-an-ole", "UNREADABLE"),
    ],
)
def test_registry_preserves_xls_container_probe_without_semantic_parse(
    tmp_path,
    content,
    expected_status,
):
    raw_path = "corpus/KT/workbook.xls"
    document = active(
        raw_path,
        "SKT_PROC_0001",
        media="application/vnd.ms-excel",
        carrier="SKT",
        role="PROCEDURE",
    )
    scope_path = install(tmp_path, [document], {raw_path: content})

    registry = build_registry(tmp_path, scope_path)

    assert registry["documents"][0]["intake"] == {
        "container_status": expected_status,
        "semantic_parse_status": "NOT_ATTEMPTED",
        "semantic_parser": None,
    }


def test_registry_fails_when_pending_source_is_missing_or_new_file_is_unclassified(tmp_path):
    active_path = "corpus/KT/active.pdf"
    pending_path = "corpus/KT/pending.pdf"
    documents = [active(active_path, "KT_REQ_001"), pending(pending_path)]
    scope_path = install(
        tmp_path,
        documents,
        {active_path: b"active", pending_path: b"pending"},
    )
    (tmp_path / pending_path).unlink()
    with pytest.raises(G0AError) as caught:
        build_registry(tmp_path, scope_path)
    assert caught.value.code == "SCOPE_PATH_MISSING"

    (tmp_path / pending_path).write_bytes(b"pending")
    (tmp_path / "corpus" / "KT" / "new.pdf").write_bytes(b"new")
    with pytest.raises(G0AError) as caught:
        build_registry(tmp_path, scope_path)
    assert caught.value.code == "SCOPE_UNCLASSIFIED"


def test_registry_is_byte_deterministic_and_does_not_accept_previous_id_input(tmp_path):
    raw_path = "corpus/KT/active.pdf"
    scope_path = install(tmp_path, [active(raw_path, "KT_REQ_001")], {raw_path: b"active"})

    first = build_registry(tmp_path, scope_path)
    second = build_registry(tmp_path, scope_path)

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    with pytest.raises(TypeError):
        build_registry(tmp_path, scope_path, previous=first)


def test_build_source_registry_reexports_v2_scope_loader(tmp_path):
    raw_path = "corpus/KT/active.pdf"
    scope_path = install(tmp_path, [active(raw_path, "KT_REQ_001")], {raw_path: b"active"})
    assert load_scope(scope_path, as_of=AS_OF)["schema_version"] == 2


def test_cli_writes_registry_and_returns_controlled_error_without_traceback(tmp_path):
    raw_path = "corpus/KT/active.pdf"
    scope_path = install(tmp_path, [active(raw_path, "KT_REQ_001")], {raw_path: b"active"})
    out = tmp_path / "registry.json"
    script = Path(__file__).resolve().parents[1] / "tools" / "build_source_registry.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(tmp_path),
            "--scope",
            str(scope_path),
            "--out",
            str(out),
        ],
        cwd=Path(tmp_path).anchor,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(out.read_text(encoding="utf-8"))["documents"][0]["document_id"] == "KT_REQ_001"

    (tmp_path / raw_path).unlink()
    failed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(tmp_path),
            "--scope",
            str(scope_path),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2
    assert failed.stderr.startswith("SCOPE_PATH_MISSING:")
    assert "Traceback" not in failed.stderr


def test_registry_schema_remains_v1_closed_and_full_hash_bound():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "source_registry_schema_v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    document = schema["properties"]["documents"]["items"]
    assert document["additionalProperties"] is False
    assert document["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}$"
