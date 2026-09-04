"""Strict, runner-independent loader for the G0-A.1 source scope contract."""

from __future__ import annotations

import copy
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

from g0a_common import G0AError


_TOP_LEVEL_KEYS = {
    "schema_version",
    "corpus_parent",
    "corpus_roots",
    "documents",
    "relations",
    "external_gaps",
}
_CARRIERS = {"LGU+", "KT", "SKT"}
_ROLES = {"REQUIREMENT", "PROCEDURE", "SAT"}
_MEDIA_TYPES = {"text/html", "application/pdf", "application/vnd.ms-excel"}
_STATES = {"ACTIVE", "EXCLUDED", "PENDING_REVIEW"}
_CURRENTNESS = {"CURRENT", "CURRENTNESS_UNVERIFIED"}
_BLOCKERS = {"CARRIER_INQUIRY", "INTERNAL_DECISION", "INTAKE_CAPABILITY"}
_EXCLUSION_REASONS = {"DUPLICATE", "SUPERSEDED", "REFERENCE_ONLY", "OUT_OF_SCOPE"}
_RELATION_KINDS = {"REQUIREMENT_TO_PROCEDURE", "REQUIREMENT_TO_SAT"}
_EVIDENCE_TYPES = {"CARRIER_DISTRIBUTION_LIST", "OFFICIAL_NOTICE"}
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class _StrictScopeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects aliases and preserves ISO dates as strings."""

    yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)

    def compose_node(self, parent, index):  # noqa: ANN001 - PyYAML hook signature
        if self.check_event(AliasEvent):
            event = self.peek_event()
            raise yaml.constructor.ConstructorError(
                None,
                None,
                "YAML aliases are not allowed",
                event.start_mark,
            )
        return super().compose_node(parent, index)


for _resolver_key, _resolvers in list(_StrictScopeLoader.yaml_implicit_resolvers.items()):
    _StrictScopeLoader.yaml_implicit_resolvers[_resolver_key] = [
        resolver
        for resolver in _resolvers
        if resolver[0] != "tag:yaml.org,2002:timestamp"
    ]


def _construct_unique_mapping(
    loader: _StrictScopeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict:
    if not isinstance(node, MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "expected a mapping node", node.start_mark
        )
    result: dict = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise yaml.constructor.ConstructorError(
                None, None, "YAML merge keys are not allowed", key_node.start_mark
            )
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                None, None, "mapping keys must be scalar", key_node.start_mark
            ) from error
        if duplicate:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key: {key}", key_node.start_mark
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictScopeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _error(code: str, detail: str) -> None:
    raise G0AError(code, detail)


def _mapping(value: object, detail: str) -> dict:
    if not isinstance(value, dict):
        _error("SCOPE_INVALID", detail)
    return value


def _list(value: object, detail: str) -> list:
    if not isinstance(value, list):
        _error("SCOPE_INVALID", detail)
    return value


def _string(value: object, detail: str) -> str:
    if not isinstance(value, str) or not value:
        _error("SCOPE_INVALID", detail)
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise G0AError("SCOPE_INVALID", detail) from error
    return value


def _integer(value: object, detail: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _error("SCOPE_INVALID", detail)
    return value


def _exact_keys(value: dict, expected: set[str], detail: str) -> None:
    if set(value) != expected:
        _error("SCOPE_INVALID", f"{detail} keys")


def _validate_path(value: object, detail: str) -> str:
    raw_path = _string(value, detail)
    pure = PurePosixPath(raw_path)
    if (
        pure.is_absolute()
        or raw_path.startswith("//")
        or re.match(r"^[A-Za-z]:", raw_path)
        or ".." in pure.parts
    ):
        _error("SCOPE_INVALID", detail)
    if "\\" in raw_path or any(part in {"", "."} for part in raw_path.split("/")):
        _error("SCOPE_INVALID", detail)
    return raw_path


def _validate_date(value: object, detail: str, as_of: date) -> str:
    raw = _string(value, detail)
    if _DATE.fullmatch(raw) is None:
        _error("SCOPE_INVALID", detail)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as error:
        raise G0AError("SCOPE_INVALID", detail) from error
    if parsed > as_of:
        _error("SCOPE_INVALID", f"{detail}: future date")
    return raw


def _today_kst() -> date:
    return datetime.now(timezone(timedelta(hours=9))).date()


def _validate_verified_by(value: object, detail: str, as_of: date) -> dict:
    verified = _mapping(value, detail)
    required = {"evidence_type", "evidence_path", "evidence_sha256", "verified_date"}
    _exact_keys(verified, required, detail)
    if _string(verified["evidence_type"], f"{detail}.evidence_type") not in _EVIDENCE_TYPES:
        _error("CURRENTNESS_EVIDENCE_MISSING", f"{detail}.evidence_type")
    _validate_path(verified["evidence_path"], f"{detail}.evidence_path")
    digest = _string(verified["evidence_sha256"], f"{detail}.evidence_sha256")
    if _SHA256.fullmatch(digest) is None:
        _error("CURRENTNESS_EVIDENCE_MISSING", f"{detail}.evidence_sha256")
    _validate_date(verified["verified_date"], f"{detail}.verified_date", as_of)
    return verified


def _validate_currentness(document: dict, detail: str, as_of: date) -> set[str]:
    currentness = _string(document.get("currentness"), f"{detail}.currentness")
    if currentness not in _CURRENTNESS:
        _error("SCOPE_INVALID", f"{detail}.currentness")
    if currentness == "CURRENT":
        if "verified_by" not in document:
            _error("CURRENTNESS_EVIDENCE_MISSING", detail)
        _validate_verified_by(document["verified_by"], f"{detail}.verified_by", as_of)
        return {"verified_by"}
    if "verified_by" in document:
        _error("SCOPE_INVALID", f"{detail}.verified_by")
    return set()


def _validate_document(value: object, index: int, as_of: date) -> dict:
    detail = f"documents[{index}]"
    document = _mapping(value, detail)
    state = _string(document.get("state"), f"{detail}.state")
    if state not in _STATES:
        _error("SCOPE_INVALID", f"{detail}.state")
    _validate_path(document.get("path"), f"{detail}.path")
    verified_key = _validate_currentness(document, detail, as_of)
    common = {"path", "state", "currentness"} | verified_key

    if state == "ACTIVE":
        state_keys = {"document_id", "carrier", "role", "media"}
        _exact_keys(document, common | state_keys, detail)
        _string(document["document_id"], f"{detail}.document_id")
        if _string(document["carrier"], f"{detail}.carrier") not in _CARRIERS:
            _error("SCOPE_INVALID", f"{detail}.carrier")
        if _string(document["role"], f"{detail}.role") not in _ROLES:
            _error("SCOPE_INVALID", f"{detail}.role")
        if _string(document["media"], f"{detail}.media") not in _MEDIA_TYPES:
            _error("SCOPE_INVALID", f"{detail}.media")
        return document

    if state == "PENDING_REVIEW":
        state_keys = {"blocked_on", "recorded_date"}
        if not state_keys.issubset(document):
            _error("PENDING_BLOCKER_MISSING", detail)
        _exact_keys(document, common | state_keys, detail)
        if _string(document["blocked_on"], f"{detail}.blocked_on") not in _BLOCKERS:
            _error("PENDING_BLOCKER_MISSING", f"{detail}.blocked_on")
        _validate_date(document["recorded_date"], f"{detail}.recorded_date", as_of)
        return document

    reason = document.get("exclusion_reason")
    if not isinstance(reason, str) or reason not in _EXCLUSION_REASONS:
        _error("EXCLUSION_EVIDENCE_MISSING", detail)
    evidence_key = {
        "DUPLICATE": "duplicate_of",
        "SUPERSEDED": "superseded_by",
        "REFERENCE_ONLY": "rationale",
        "OUT_OF_SCOPE": "rationale",
    }[reason]
    if evidence_key not in document:
        _error("EXCLUSION_EVIDENCE_MISSING", detail)
    _exact_keys(document, common | {"exclusion_reason", evidence_key}, detail)
    if evidence_key == "duplicate_of":
        _validate_path(document[evidence_key], f"{detail}.{evidence_key}")
    else:
        _string(document[evidence_key], f"{detail}.{evidence_key}")
    return document


def _validate_parent(value: object) -> dict:
    parent = _mapping(value, "corpus_parent")
    required = {"path", "expected_entries", "non_corpus_entries"}
    _exact_keys(parent, required, "corpus_parent")
    _validate_path(parent["path"], "corpus_parent.path")
    _integer(parent["expected_entries"], "corpus_parent.expected_entries", minimum=1)
    entries = _list(parent["non_corpus_entries"], "corpus_parent.non_corpus_entries")
    names: list[str] = []
    for index, raw_entry in enumerate(entries):
        detail = f"corpus_parent.non_corpus_entries[{index}]"
        entry = _mapping(raw_entry, detail)
        _exact_keys(entry, {"name", "kind", "rationale"}, detail)
        name = _string(entry["name"], f"{detail}.name")
        if "/" in name or "\\" in name or name in {".", ".."}:
            _error("SCOPE_INVALID", f"{detail}.name")
        if _string(entry["kind"], f"{detail}.kind") not in {"FILE", "DIRECTORY"}:
            _error("SCOPE_INVALID", f"{detail}.kind")
        _string(entry["rationale"], f"{detail}.rationale")
        names.append(name)
    if len(names) != len(set(name.casefold() for name in names)):
        _error("SCOPE_INVALID", "duplicate non_corpus entry")
    return parent


def _validate_roots(value: object, parent: dict) -> list[dict]:
    roots = _list(value, "corpus_roots")
    parent_path = PurePosixPath(str(parent["path"]))
    root_paths: list[str] = []
    for index, raw_root in enumerate(roots):
        detail = f"corpus_roots[{index}]"
        root = _mapping(raw_root, detail)
        _exact_keys(root, {"root", "expected_total"}, detail)
        raw_path = _validate_path(root["root"], f"{detail}.root")
        if PurePosixPath(raw_path).parent != parent_path:
            _error("SCOPE_INVALID", f"{detail}.root")
        _integer(root["expected_total"], f"{detail}.expected_total")
        root_paths.append(raw_path)
    if len(root_paths) != len(set(path.casefold() for path in root_paths)):
        _error("SCOPE_INVALID", "duplicate corpus root")
    expected_entries = len(root_paths) + len(parent["non_corpus_entries"])
    if parent["expected_entries"] != expected_entries:
        _error("SCOPE_INVALID", "corpus_parent.expected_entries")
    root_names = {PurePosixPath(path).name.casefold() for path in root_paths}
    non_corpus_names = {
        str(item["name"]).casefold() for item in parent["non_corpus_entries"]
    }
    if root_names & non_corpus_names:
        _error("SCOPE_INVALID", "corpus root/non-corpus overlap")
    return roots


def _validate_relations(value: object) -> list[dict]:
    relations = _list(value, "relations")
    required = {"relation_id", "kind", "source_document_id", "target_document_id"}
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for index, raw_relation in enumerate(relations):
        detail = f"relations[{index}]"
        relation = _mapping(raw_relation, detail)
        _exact_keys(relation, required, detail)
        for field in required:
            _string(relation[field], f"{detail}.{field}")
        if relation["kind"] not in _RELATION_KINDS:
            _error("SCOPE_INVALID", f"{detail}.kind")
        if relation["source_document_id"] == relation["target_document_id"]:
            _error("SCOPE_INVALID", f"{detail}: self relation")
        relation_id = str(relation["relation_id"])
        pair = (str(relation["source_document_id"]), str(relation["target_document_id"]))
        if relation_id in ids or pair in pairs:
            _error("SCOPE_INVALID", f"{detail}: duplicate relation")
        ids.add(relation_id)
        pairs.add(pair)
    return relations


def _validate_external_gaps(value: object, as_of: date) -> list[dict]:
    gaps = _list(value, "external_gaps")
    required = {"gap_id", "carrier", "description", "blocked_on", "recorded_date"}
    ids: set[str] = set()
    for index, raw_gap in enumerate(gaps):
        detail = f"external_gaps[{index}]"
        gap = _mapping(raw_gap, detail)
        _exact_keys(gap, required, detail)
        gap_id = _string(gap["gap_id"], f"{detail}.gap_id")
        if gap_id in ids:
            _error("SCOPE_INVALID", f"duplicate gap_id: {gap_id}")
        ids.add(gap_id)
        if _string(gap["carrier"], f"{detail}.carrier") not in _CARRIERS:
            _error("SCOPE_INVALID", f"{detail}.carrier")
        _string(gap["description"], f"{detail}.description")
        if _string(gap["blocked_on"], f"{detail}.blocked_on") not in _BLOCKERS:
            _error("SCOPE_INVALID", f"{detail}.blocked_on")
        _validate_date(gap["recorded_date"], f"{detail}.recorded_date", as_of)
    return gaps


def load_scope(path: Path, *, as_of: date | None = None) -> dict[str, object]:
    """Load and validate one exact G0-A.1 source scope document."""
    effective_date = as_of or _today_kst()
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            raise ValueError("scope must be UTF-8 without BOM and LF-only")
        text = raw.decode("utf-8", errors="strict")
        loaded = yaml.load(text, Loader=_StrictScopeLoader)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
        raise G0AError("SCOPE_INVALID", str(path)) from error

    scope = _mapping(loaded, "root")
    _exact_keys(scope, _TOP_LEVEL_KEYS, "root")
    if isinstance(scope.get("schema_version"), bool) or scope.get("schema_version") != 2:
        _error("SCOPE_INVALID", "schema_version")
    parent = _validate_parent(scope["corpus_parent"])
    roots = _validate_roots(scope["corpus_roots"], parent)
    documents = [
        _validate_document(document, index, effective_date)
        for index, document in enumerate(_list(scope["documents"], "documents"))
    ]
    paths = [str(document["path"]) for document in documents]
    folded_paths = [path.casefold() for path in paths]
    if len(folded_paths) != len(set(folded_paths)):
        _error("SCOPE_STATE_CONFLICT", "duplicate document path")
    active_ids = [
        str(document["document_id"])
        for document in documents
        if document["state"] == "ACTIVE"
    ]
    if len(active_ids) != len(set(active_ids)):
        _error("SCOPE_INVALID", "duplicate document_id")
    relations = _validate_relations(scope["relations"])
    external_gaps = _validate_external_gaps(scope["external_gaps"], effective_date)
    return {
        "schema_version": 2,
        "corpus_parent": parent,
        "corpus_roots": roots,
        "documents": documents,
        "relations": relations,
        "external_gaps": external_gaps,
    }


def active_documents(scope: dict) -> list[dict]:
    """Return explicit ACTIVE declarations in document-id order."""
    documents = scope.get("documents") if isinstance(scope, dict) else None
    if not isinstance(documents, list):
        _error("SCOPE_INVALID", "documents")
    active = [document for document in documents if document.get("state") == "ACTIVE"]
    return sorted(active, key=lambda item: str(item["document_id"]))


def currentness_evidence_paths(scope: dict) -> list[str]:
    """Return unique immutable local evidence paths consumed by this scope."""
    documents = scope.get("documents") if isinstance(scope, dict) else None
    if not isinstance(documents, list):
        _error("SCOPE_INVALID", "documents")
    paths = {
        str(document["verified_by"]["evidence_path"])
        for document in documents
        if document.get("currentness") == "CURRENT"
    }
    return sorted(paths)
