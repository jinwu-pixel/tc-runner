"""Build deterministic G0-A.2 resolver proposals from a validated closure."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from build_corpus_closure import validate_stored_closure
from g0a_common import G0AError, sha256_bytes, write_json


NON_DOCUMENT_EXTENSIONS = frozenset({".ai", ".png"})
UNSUPPORTED_MEDIA_EXTENSIONS = frozenset({".doc", ".docx", ".zip"})

_BASES = (
    "NORMATIVITY_UNKNOWN",
    "SHA256_DUPLICATE_IN_CORPUS",
    "UNSUPPORTED_MEDIA",
    "NON_DOCUMENT_ASSET",
)
_RESOLVERS = (
    "CARRIER_INQUIRY",
    "INTERNAL_DECISION",
    "INTAKE_CAPABILITY",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TOP_KEYS = {
    "closure_sha256",
    "generator",
    "proposals",
    "schema_version",
    "source_scope_sha256",
    "summary",
}
_PROPOSAL_KEYS = {"basis", "blocked_on", "evidence", "path"}
_SUMMARY_KEYS = {
    "by_basis",
    "by_resolver",
    "duplicate_group_count",
    "duplicate_member_count",
    "roots",
    "total",
}


class _StrictJsonError(ValueError):
    pass


def _reject_json_constant(value: str) -> None:
    raise _StrictJsonError(f"non-finite constant: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJsonError(f"duplicate key: {key}")
        result[key] = value
    return result


def _require_strict_json_domain(value: object, detail: str = "root") -> None:
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _StrictJsonError(f"{detail}: non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_strict_json_domain(item, f"{detail}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8", errors="strict")
            _require_strict_json_domain(item, f"{detail}.{key}")
        return
    raise _StrictJsonError(f"{detail}: unsupported JSON type")


def _serialized_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _error(detail: str) -> None:
    raise G0AError("PROPOSAL_INVALID", detail)


def _require_sha256(value: str, detail: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _error(detail)
    return value


def _require_count(value: object, detail: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _error(detail)
    return value


def _require_string(value: object, detail: str) -> str:
    if not isinstance(value, str) or not value:
        _error(detail)
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise G0AError("PROPOSAL_INVALID", detail) from error
    return value


def _validate_evidence(basis: str, value: object, detail: str) -> None:
    if not isinstance(value, dict):
        _error(detail)
    if basis == "SHA256_DUPLICATE_IN_CORPUS":
        if set(value) != {"duplicate_group_sha256", "duplicate_group_paths"}:
            _error(detail)
        _require_sha256(value["duplicate_group_sha256"], detail)
        paths = value["duplicate_group_paths"]
        if not isinstance(paths, list) or len(paths) < 2:
            _error(detail)
        validated_paths = [
            _require_string(path, f"{detail}.duplicate_group_paths") for path in paths
        ]
        if validated_paths != sorted(
            validated_paths,
            key=lambda path: path.encode("utf-8"),
        ) or len(validated_paths) != len(set(validated_paths)):
            _error(detail)
        return
    if basis in {"NON_DOCUMENT_ASSET", "UNSUPPORTED_MEDIA"}:
        if set(value) != {"extension"}:
            _error(detail)
        extension = _require_string(value["extension"], f"{detail}.extension")
        if not extension.startswith(".") or extension != extension.lower():
            _error(detail)
        return
    if value:
        _error(detail)


def _validate_count_map(value: object, keys: tuple[str, ...], detail: str) -> None:
    if not isinstance(value, dict) or set(value) != set(keys):
        _error(detail)
    for key in keys:
        _require_count(value[key], f"{detail}.{key}")


def _validate_summary_shape(value: object) -> None:
    if not isinstance(value, dict) or set(value) != _SUMMARY_KEYS:
        _error("summary")
    _validate_count_map(value["by_basis"], _BASES, "summary.by_basis")
    _validate_count_map(value["by_resolver"], _RESOLVERS, "summary.by_resolver")
    for field in {"duplicate_group_count", "duplicate_member_count", "total"}:
        _require_count(value[field], f"summary.{field}")
    roots = value["roots"]
    if not isinstance(roots, dict):
        _error("summary.roots")
    root_names = list(roots)
    if root_names != sorted(root_names, key=lambda root: root.encode("utf-8")):
        _error("summary.roots")
    for root, root_summary in roots.items():
        _require_string(root, "summary.roots key")
        if not isinstance(root_summary, dict) or set(root_summary) != {"by_resolver"}:
            _error(f"summary.roots.{root}")
        _validate_count_map(
            root_summary["by_resolver"],
            _RESOLVERS,
            f"summary.roots.{root}.by_resolver",
        )


def _classify(document: dict, duplicate_paths: list[str]) -> tuple[str, str, dict]:
    if len(duplicate_paths) > 1:
        return (
            "SHA256_DUPLICATE_IN_CORPUS",
            "INTERNAL_DECISION",
            {
                "duplicate_group_sha256": document["sha256"],
                "duplicate_group_paths": duplicate_paths,
            },
        )

    extension = PurePosixPath(document["path"]).suffix.lower()
    if extension in NON_DOCUMENT_EXTENSIONS:
        return "NON_DOCUMENT_ASSET", "INTERNAL_DECISION", {"extension": extension}
    if extension in UNSUPPORTED_MEDIA_EXTENSIONS:
        return "UNSUPPORTED_MEDIA", "INTAKE_CAPABILITY", {"extension": extension}
    return "NORMATIVITY_UNKNOWN", "CARRIER_INQUIRY", {}


def build_proposal(
    closure: dict,
    *,
    closure_sha256: str,
    source_scope_sha256: str,
) -> dict:
    """Return the canonical resolver proposal value for one closure/scope pair."""
    validated = validate_stored_closure(closure)
    _require_sha256(closure_sha256, "closure_sha256")
    _require_sha256(source_scope_sha256, "source_scope_sha256")

    paths_by_hash: dict[str, list[str]] = defaultdict(list)
    for document in validated["documents"]:
        paths_by_hash[document["sha256"]].append(document["path"])
    for paths in paths_by_hash.values():
        paths.sort(key=lambda path: path.encode("utf-8"))

    proposals = []
    for document in validated["documents"]:
        if document["state"] != "PENDING_REVIEW":
            continue
        basis, resolver, evidence = _classify(
            document,
            paths_by_hash[document["sha256"]],
        )
        proposals.append(
            {
                "basis": basis,
                "blocked_on": resolver,
                "evidence": evidence,
                "path": document["path"],
            }
        )
    proposals.sort(key=lambda item: item["path"].encode("utf-8"))

    by_basis = Counter(item["basis"] for item in proposals)
    by_resolver = Counter(item["blocked_on"] for item in proposals)
    root_by_path = {
        document["path"]: document["root"] for document in validated["documents"]
    }
    roots: dict[str, dict] = {}
    for root in sorted(
        {root_by_path[item["path"]] for item in proposals},
        key=lambda value: value.encode("utf-8"),
    ):
        root_counts = Counter(
            item["blocked_on"]
            for item in proposals
            if root_by_path[item["path"]] == root
        )
        roots[root] = {
            "by_resolver": {
                resolver: root_counts[resolver] for resolver in _RESOLVERS
            }
        }

    duplicate_items = [
        item for item in proposals if item["basis"] == "SHA256_DUPLICATE_IN_CORPUS"
    ]
    return {
        "closure_sha256": closure_sha256,
        "generator": {"name": "build_resolver_proposal", "version": "1"},
        "proposals": proposals,
        "schema_version": 1,
        "source_scope_sha256": source_scope_sha256,
        "summary": {
            "by_basis": {basis: by_basis[basis] for basis in _BASES},
            "by_resolver": {
                resolver: by_resolver[resolver] for resolver in _RESOLVERS
            },
            "duplicate_group_count": len(
                {
                    item["evidence"]["duplicate_group_sha256"]
                    for item in duplicate_items
                }
            ),
            "duplicate_member_count": len(duplicate_items),
            "roots": roots,
            "total": len(proposals),
        },
    }


def validate_stored_proposal(
    value: object,
    closure: dict,
    *,
    closure_sha256: str,
    source_scope_sha256: str,
) -> dict:
    """Validate stored shape, input pins, pending set, and regenerated rules."""
    validated_closure = validate_stored_closure(closure)
    expected_closure_sha256 = _require_sha256(closure_sha256, "closure_sha256")
    expected_scope_sha256 = _require_sha256(
        source_scope_sha256,
        "source_scope_sha256",
    )
    if not isinstance(value, dict) or set(value) != _TOP_KEYS:
        _error("top-level keys")
    if value.get("schema_version") != 1 or value.get("generator") != {
        "name": "build_resolver_proposal",
        "version": "1",
    }:
        _error("schema_version or generator")
    _require_sha256(value.get("closure_sha256"), "closure_sha256")
    _require_sha256(value.get("source_scope_sha256"), "source_scope_sha256")

    proposals = value.get("proposals")
    if not isinstance(proposals, list):
        _error("proposals")
    paths: list[str] = []
    for index, item in enumerate(proposals):
        detail = f"proposals[{index}]"
        if not isinstance(item, dict) or set(item) != _PROPOSAL_KEYS:
            _error(f"{detail} keys")
        basis = item.get("basis")
        resolver = item.get("blocked_on")
        if basis not in _BASES or resolver not in _RESOLVERS:
            _error(detail)
        path = _require_string(item.get("path"), f"{detail}.path")
        _validate_evidence(basis, item.get("evidence"), f"{detail}.evidence")
        paths.append(path)
    if paths != sorted(paths, key=lambda path: path.encode("utf-8")) or len(paths) != len(
        set(paths)
    ):
        _error("proposal order or duplicate path")
    _validate_summary_shape(value.get("summary"))

    if (
        value["closure_sha256"] != expected_closure_sha256
        or value["source_scope_sha256"] != expected_scope_sha256
    ):
        raise G0AError("PROPOSAL_STALE", "closure or source scope hash")

    pending_paths = {
        document["path"]
        for document in validated_closure["documents"]
        if document["state"] == "PENDING_REVIEW"
    }
    if set(paths) != pending_paths:
        raise G0AError("PROPOSAL_SET_MISMATCH", "pending paths")

    regenerated = build_proposal(
        validated_closure,
        closure_sha256=expected_closure_sha256,
        source_scope_sha256=expected_scope_sha256,
    )
    if proposals != regenerated["proposals"] or value["summary"] != regenerated["summary"]:
        raise G0AError("PROPOSAL_BASIS_DRIFT", "proposal rules or summary")
    return value


def build_proposal_from_paths(closure_path: Path, scope_path: Path) -> dict:
    """Load exact tracked bytes and return their hash-bound resolver proposal."""
    try:
        closure_bytes = closure_path.read_bytes()
        closure_text = closure_bytes.decode("utf-8", errors="strict")
        closure = json.loads(
            closure_text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_object,
        )
        _require_strict_json_domain(closure)
        if closure_bytes != _serialized_json_bytes(closure):
            raise _StrictJsonError("closure JSON is not canonical")
        scope_bytes = scope_path.read_bytes()
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        _StrictJsonError,
    ) as error:
        raise G0AError("PROPOSAL_INVALID", closure_path.name) from error
    if not isinstance(closure, dict):
        _error("closure root")
    validated = validate_stored_closure(closure)
    scope_sha256 = sha256_bytes(scope_bytes)
    if validated["source_scope_sha256"] != scope_sha256:
        raise G0AError("PROPOSAL_STALE", "closure source scope hash")
    return build_proposal(
        validated,
        closure_sha256=sha256_bytes(closure_bytes),
        source_scope_sha256=scope_sha256,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        proposal = build_proposal_from_paths(arguments.closure, arguments.scope)
        write_json(arguments.out, proposal)
    except G0AError as error:
        print(error, file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(G0AError("PROPOSAL_INVALID", type(error).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
