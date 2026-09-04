"""Build a hash-bound ledger of declared source document relations."""

import argparse
import json
import re
import sys
from pathlib import Path

from g0a_common import G0AError, write_json
from build_source_registry import load_scope


_REGISTRY_TOP_LEVEL_KEYS = {"schema_version", "documents"}
_DOCUMENT_KEYS = {
    "document_id",
    "carrier",
    "role",
    "media_type",
    "path",
    "size_bytes",
    "sha256",
    "intake",
}
_INTAKE_KEYS = {"container_status", "semantic_parse_status", "semantic_parser"}
_RELATION_KEYS = {
    "relation_id",
    "kind",
    "source_document_id",
    "target_document_id",
}
_CARRIERS = {"LGU+", "KT", "SKT"}
_ROLES = {"REQUIREMENT", "PROCEDURE", "SAT"}
_MEDIA_TYPES = {"text/html", "application/pdf", "application/vnd.ms-excel"}
_CONTAINER_STATUSES = {"READABLE", "UNREADABLE"}
_SEMANTIC_PARSE_STATUSES = {"NOT_ATTEMPTED", "NOT_APPLICABLE"}
_ROLE_PAIRS = {
    "REQUIREMENT_TO_PROCEDURE": ("REQUIREMENT", "PROCEDURE"),
    "REQUIREMENT_TO_SAT": ("REQUIREMENT", "SAT"),
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _registry_error(detail: str) -> None:
    raise G0AError("SOURCE_REGISTRY_INVALID", detail)


def _relation_error(detail: str) -> None:
    raise G0AError("RELATION_INVALID", detail)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _validate_intake(value: object, index: int) -> None:
    if not isinstance(value, dict) or set(value) != _INTAKE_KEYS:
        _registry_error(f"documents[{index}].intake")
    container_status = value["container_status"]
    semantic_parse_status = value["semantic_parse_status"]
    semantic_parser = value["semantic_parser"]
    if not isinstance(container_status, str) or container_status not in _CONTAINER_STATUSES:
        _registry_error(f"documents[{index}].intake.container_status")
    if (
        not isinstance(semantic_parse_status, str)
        or semantic_parse_status not in _SEMANTIC_PARSE_STATUSES
    ):
        _registry_error(f"documents[{index}].intake.semantic_parse_status")
    if semantic_parser is not None and not _is_nonempty_string(semantic_parser):
        _registry_error(f"documents[{index}].intake.semantic_parser")


def _validate_registry(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != _REGISTRY_TOP_LEVEL_KEYS:
        _registry_error("top-level keys")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != 1
        or not isinstance(value["documents"], list)
    ):
        _registry_error("schema_version or documents")

    document_ids: set[str] = set()
    for index, document in enumerate(value["documents"]):
        if not isinstance(document, dict) or set(document) != _DOCUMENT_KEYS:
            _registry_error(f"documents[{index}] keys")
        for field in {"document_id", "carrier", "role", "media_type", "path", "sha256"}:
            if not _is_nonempty_string(document[field]):
                _registry_error(f"documents[{index}].{field}")
        if document["carrier"] not in _CARRIERS:
            _registry_error(f"documents[{index}].carrier")
        if document["role"] not in _ROLES:
            _registry_error(f"documents[{index}].role")
        if document["media_type"] not in _MEDIA_TYPES:
            _registry_error(f"documents[{index}].media_type")
        if (
            isinstance(document["size_bytes"], bool)
            or not isinstance(document["size_bytes"], int)
            or document["size_bytes"] < 0
        ):
            _registry_error(f"documents[{index}].size_bytes")
        if not _SHA256_PATTERN.fullmatch(document["sha256"]):
            _registry_error(f"documents[{index}].sha256")
        _validate_intake(document["intake"], index)
        document_id = document["document_id"]
        if document_id in document_ids:
            _registry_error(f"duplicate document_id: {document_id}")
        document_ids.add(document_id)
    return value


def load_registry(path: Path) -> dict:
    """Load a complete, validated source registry document."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise G0AError("SOURCE_REGISTRY_INVALID", str(path)) from error
    return _validate_registry(loaded)


def _validate_relation(value: object, index: int) -> dict:
    if not isinstance(value, dict) or set(value) != _RELATION_KEYS:
        _relation_error(f"relations[{index}] keys")
    for field in _RELATION_KEYS:
        if not _is_nonempty_string(value[field]):
            _relation_error(f"relations[{index}].{field}")
    if value["kind"] not in _ROLE_PAIRS:
        _relation_error(f"relations[{index}].kind")
    if value["source_document_id"] == value["target_document_id"]:
        _relation_error(f"relations[{index}] self relation")
    return value


def build_relations(scope: dict, registry: dict) -> dict:
    """Resolve declared source relations to a sorted, hash-bound ledger."""
    validated_registry = _validate_registry(registry)
    if (
        not isinstance(scope, dict)
        or not isinstance(scope.get("relations"), list)
        or not isinstance(scope.get("documents"), list)
    ):
        _relation_error("scope.relations")

    active_ids = {
        document.get("document_id")
        for document in scope["documents"]
        if isinstance(document, dict) and document.get("state") == "ACTIVE"
    }

    documents = {
        document["document_id"]: document for document in validated_registry["documents"]
    }
    relation_ids: set[str] = set()
    source_target_pairs: set[tuple[str, str]] = set()
    resolved: list[dict[str, str]] = []
    for index, raw_relation in enumerate(scope["relations"]):
        relation = _validate_relation(raw_relation, index)
        relation_id = relation["relation_id"]
        pair = (relation["source_document_id"], relation["target_document_id"])
        if relation_id in relation_ids:
            raise G0AError("RELATION_DUPLICATE_ID", relation_id)
        if pair in source_target_pairs:
            raise G0AError("RELATION_DUPLICATE_PAIR", f"{pair[0]} -> {pair[1]}")
        relation_ids.add(relation_id)
        source_target_pairs.add(pair)

        if pair[0] not in active_ids or pair[1] not in active_ids:
            inactive = pair[0] if pair[0] not in active_ids else pair[1]
            raise G0AError("RELATION_ENDPOINT_NOT_ACTIVE", str(inactive))

        source = documents.get(relation["source_document_id"])
        target = documents.get(relation["target_document_id"])
        if source is None or target is None:
            missing = relation["source_document_id"] if source is None else relation["target_document_id"]
            raise G0AError("RELATION_DANGLING_DOCUMENT", missing)
        required_source_role, required_target_role = _ROLE_PAIRS[relation["kind"]]
        if source["role"] != required_source_role or target["role"] != required_target_role:
            raise G0AError("RELATION_ROLE_MISMATCH", relation_id)
        resolved.append(
            {
                "relation_id": relation_id,
                "kind": relation["kind"],
                "source_document_id": source["document_id"],
                "source_sha256": source["sha256"],
                "target_document_id": target["document_id"],
                "target_sha256": target["sha256"],
            }
        )
    return {"schema_version": 1, "relations": sorted(resolved, key=lambda item: item["relation_id"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        relations = build_relations(load_scope(arguments.scope), load_registry(arguments.registry))
        write_json(arguments.out, relations)
    except G0AError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
