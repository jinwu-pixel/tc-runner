"""Build the deterministic G0-A.1 full-corpus closure artifact."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from g0a_common import G0AError, resolve_repo_relative, sha256_file, write_json
from source_scope_v2 import load_scope


_BLOCKERS = ("CARRIER_INQUIRY", "INTERNAL_DECISION", "INTAKE_CAPABILITY")
_CURRENTNESS = ("CURRENT", "CURRENTNESS_UNVERIFIED")
_STATES = ("ACTIVE", "EXCLUDED", "PENDING_REVIEW")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TOP_KEYS = {
    "schema_version",
    "generator",
    "source_scope_path",
    "source_scope_sha256",
    "corpus_parent",
    "documents",
    "summary",
}
_SUMMARY_KEYS = {
    "total",
    "active",
    "excluded",
    "pending_review",
    "unclassified",
    "roots",
    "pending_by_resolver",
    "oldest_pending_recorded_date",
    "currentness",
}


def _error(code: str, detail: str) -> None:
    raise G0AError(code, detail)


def _is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or (
            hasattr(path, "is_junction") and path.is_junction()
        )
    except OSError as error:
        raise G0AError("SCOPE_INVALID", str(path)) from error


def _resolve_existing(repo_root: Path, raw_path: str, detail: str) -> Path:
    root = repo_root.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(raw_path).parts)
    current = root
    try:
        for component in PurePosixPath(raw_path).parts:
            current /= component
            if _is_link_or_junction(current):
                _error("SCOPE_INVALID", f"{detail}: linked ancestry")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            _error("SCOPE_INVALID", f"{detail}: repo escape")
    except G0AError:
        raise
    except (OSError, RuntimeError) as error:
        raise G0AError("SCOPE_PATH_MISSING", detail) from error
    return resolved


def _kind(path: Path) -> str:
    if _is_link_or_junction(path):
        return "LINK"
    if path.is_dir():
        return "DIRECTORY"
    if path.is_file():
        return "FILE"
    return "OTHER"


def _validate_parent(scope: dict, repo_root: Path) -> Path:
    parent_decl = scope["corpus_parent"]
    parent_path = _resolve_existing(repo_root, parent_decl["path"], "corpus_parent")
    if not parent_path.is_dir():
        _error("SCOPE_PARENT_KIND_MISMATCH", str(parent_decl["path"]))

    expected_kinds = {
        PurePosixPath(root["root"]).name: "DIRECTORY"
        for root in scope["corpus_roots"]
    }
    expected_kinds.update(
        {entry["name"]: entry["kind"] for entry in parent_decl["non_corpus_entries"]}
    )
    try:
        actual_entries = {entry.name: entry for entry in parent_path.iterdir()}
    except OSError as error:
        raise G0AError("SCOPE_PARENT_DRIFT", str(parent_decl["path"])) from error
    if set(actual_entries) != set(expected_kinds):
        missing = sorted(set(expected_kinds) - set(actual_entries))
        unexpected = sorted(set(actual_entries) - set(expected_kinds))
        _error("SCOPE_PARENT_DRIFT", f"missing={missing}; unexpected={unexpected}")
    if len(actual_entries) != parent_decl["expected_entries"]:
        _error(
            "SCOPE_PARENT_DRIFT",
            f"expected={parent_decl['expected_entries']}; found={len(actual_entries)}",
        )
    for name, expected_kind in expected_kinds.items():
        actual_kind = _kind(actual_entries[name])
        if actual_kind != expected_kind:
            _error(
                "SCOPE_PARENT_KIND_MISMATCH",
                f"{name}: expected={expected_kind}; found={actual_kind}",
            )
    return parent_path


def _walk_regular_files(root: Path, repo_root: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise G0AError("SCOPE_INVALID", str(directory)) from error
        for entry in entries:
            if _is_link_or_junction(entry):
                _error("SCOPE_INVALID", f"linked corpus entry: {entry}")
            if entry.is_dir():
                visit(entry)
            elif entry.is_file():
                found.append((entry.relative_to(repo_root).as_posix(), entry))
            else:
                _error("SCOPE_INVALID", f"non-regular corpus entry: {entry}")

    visit(root)
    return found


def _enumerate_roots(scope: dict, repo_root: Path) -> dict[str, list[tuple[str, Path]]]:
    enumerated: dict[str, list[tuple[str, Path]]] = {}
    resolved_identities: set[str] = set()
    for root_decl in scope["corpus_roots"]:
        raw_root = root_decl["root"]
        root = _resolve_existing(repo_root, raw_root, raw_root)
        if not root.is_dir():
            _error("SCOPE_PARENT_KIND_MISMATCH", raw_root)
        identity = str(root).casefold()
        if identity in resolved_identities:
            _error("SCOPE_STATE_CONFLICT", f"resolver-equivalent root: {raw_root}")
        resolved_identities.add(identity)
        enumerated[raw_root] = _walk_regular_files(root, repo_root)
    return enumerated


def _root_for_path(raw_path: str, roots: list[str]) -> str:
    candidate = PurePosixPath(raw_path)
    matches: list[str] = []
    for raw_root in roots:
        try:
            candidate.relative_to(PurePosixPath(raw_root))
        except ValueError:
            continue
        matches.append(raw_root)
    if len(matches) != 1:
        _error("SCOPE_INVALID", f"document outside or across roots: {raw_path}")
    return matches[0]


def _closure_document(document: dict, root: str, source: Path) -> dict:
    item = {
        "path": document["path"],
        "root": root,
        "state": document["state"],
        "currentness": document["currentness"],
        "size_bytes": source.stat().st_size,
        "sha256": sha256_file(source),
    }
    if document["state"] == "ACTIVE":
        item["document_id"] = document["document_id"]
    elif document["state"] == "EXCLUDED":
        item["exclusion_reason"] = document["exclusion_reason"]
    else:
        item["blocked_on"] = document["blocked_on"]
        item["recorded_date"] = document["recorded_date"]
    return item


def _validate_evidence(scope: dict, entries: list[dict], repo_root: Path) -> None:
    by_path = {document["path"]: document for document in scope["documents"]}
    closure_by_path = {entry["path"]: entry for entry in entries}
    active_ids = {
        document["document_id"]
        for document in scope["documents"]
        if document["state"] == "ACTIVE"
    }
    for document in scope["documents"]:
        raw_path = document["path"]
        if document["state"] == "EXCLUDED":
            reason = document["exclusion_reason"]
            if reason == "DUPLICATE":
                target_path = document["duplicate_of"]
                target = by_path.get(target_path)
                if (
                    target_path == raw_path
                    or target is None
                    or target.get("state") != "ACTIVE"
                ):
                    _error("DUPLICATE_HASH_MISMATCH", raw_path)
                if closure_by_path[raw_path]["sha256"] != closure_by_path[target_path]["sha256"]:
                    _error("DUPLICATE_HASH_MISMATCH", f"{raw_path} != {target_path}")
            elif reason == "SUPERSEDED" and document["superseded_by"] not in active_ids:
                _error("SUPERSEDED_TARGET_UNKNOWN", document["superseded_by"])

        if document["currentness"] == "CURRENT":
            verified = document["verified_by"]
            try:
                evidence_path = _resolve_existing(
                    repo_root,
                    verified["evidence_path"],
                    verified["evidence_path"],
                )
                if not evidence_path.is_file():
                    raise OSError("not a file")
                actual_hash = sha256_file(evidence_path)
            except (G0AError, OSError) as error:
                raise G0AError("CURRENTNESS_EVIDENCE_MISSING", raw_path) from error
            if actual_hash != verified["evidence_sha256"]:
                _error("CURRENTNESS_EVIDENCE_MISSING", raw_path)


def _summary(entries: list[dict], roots: list[str]) -> dict:
    root_counts = {}
    for root in roots:
        items = [entry for entry in entries if entry["root"] == root]
        root_counts[root] = {
            "active": sum(entry["state"] == "ACTIVE" for entry in items),
            "excluded": sum(entry["state"] == "EXCLUDED" for entry in items),
            "pending_review": sum(entry["state"] == "PENDING_REVIEW" for entry in items),
            "total": len(items),
        }
    pending_dates = [
        entry["recorded_date"]
        for entry in entries
        if entry["state"] == "PENDING_REVIEW"
    ]
    return {
        "total": len(entries),
        "active": sum(entry["state"] == "ACTIVE" for entry in entries),
        "excluded": sum(entry["state"] == "EXCLUDED" for entry in entries),
        "pending_review": sum(entry["state"] == "PENDING_REVIEW" for entry in entries),
        "unclassified": 0,
        "roots": root_counts,
        "pending_by_resolver": {
            blocker: sum(
                entry["state"] == "PENDING_REVIEW" and entry["blocked_on"] == blocker
                for entry in entries
            )
            for blocker in _BLOCKERS
        },
        "oldest_pending_recorded_date": min(pending_dates) if pending_dates else None,
        "currentness": {
            currentness: sum(entry["currentness"] == currentness for entry in entries)
            for currentness in _CURRENTNESS
        },
    }


def build_closure(
    repo_root: Path,
    scope_path: Path,
    *,
    as_of: date | None = None,
) -> dict:
    """Build and validate one exact full-corpus closure artifact."""
    root = repo_root.resolve(strict=True)
    scope = load_scope(scope_path, as_of=as_of)
    _validate_parent(scope, root)
    enumerated = _enumerate_roots(scope, root)
    actual = {
        raw_path: path
        for root_items in enumerated.values()
        for raw_path, path in root_items
    }
    declared = {document["path"] for document in scope["documents"]}
    unclassified = sorted(set(actual) - declared)
    if unclassified:
        _error("SCOPE_UNCLASSIFIED", ", ".join(unclassified))
    missing = sorted(declared - set(actual))
    if missing:
        _error("SCOPE_PATH_MISSING", ", ".join(missing))

    roots = [root_decl["root"] for root_decl in scope["corpus_roots"]]
    for root_decl in scope["corpus_roots"]:
        raw_root = root_decl["root"]
        actual_count = len(enumerated[raw_root])
        declared_count = sum(
            _root_for_path(document["path"], roots) == raw_root
            for document in scope["documents"]
        )
        expected = root_decl["expected_total"]
        if actual_count != expected or declared_count != expected:
            _error(
                "SCOPE_TOTAL_MISMATCH",
                f"{raw_root}: expected={expected}; actual={actual_count}; declared={declared_count}",
            )

    resolved_documents: dict[str, str] = {}
    entries: list[dict] = []
    for document in scope["documents"]:
        raw_path = document["path"]
        source = _resolve_existing(root, raw_path, raw_path)
        identity = str(source).casefold()
        if identity in resolved_documents:
            _error(
                "SCOPE_STATE_CONFLICT",
                f"{resolved_documents[identity]} == {raw_path}",
            )
        resolved_documents[identity] = raw_path
        entries.append(_closure_document(document, _root_for_path(raw_path, roots), source))
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    _validate_evidence(scope, entries, root)

    try:
        scope_resolved = scope_path.resolve(strict=True)
        source_scope_path = scope_resolved.relative_to(root).as_posix()
    except (OSError, ValueError) as error:
        raise G0AError("SCOPE_INVALID", "scope path outside repo") from error
    return {
        "schema_version": 1,
        "generator": {"name": "build_corpus_closure", "version": "1"},
        "source_scope_path": source_scope_path,
        "source_scope_sha256": sha256_file(scope_resolved),
        "corpus_parent": scope["corpus_parent"]["path"],
        "documents": entries,
        "summary": _summary(entries, roots),
    }


def _expected_document_keys(state: str) -> set[str]:
    common = {"path", "root", "state", "currentness", "size_bytes", "sha256"}
    if state == "ACTIVE":
        return common | {"document_id"}
    if state == "EXCLUDED":
        return common | {"exclusion_reason"}
    return common | {"blocked_on", "recorded_date"}


def validate_stored_closure(value: object) -> dict:
    """Validate the closed stored JSON shape independently of the filesystem."""
    if not isinstance(value, dict) or set(value) != _TOP_KEYS:
        _error("CORPUS_CLOSURE_INVALID", "top-level keys")
    if value.get("schema_version") != 1 or value.get("generator") != {
        "name": "build_corpus_closure",
        "version": "1",
    }:
        _error("CORPUS_CLOSURE_INVALID", "schema_version or generator")
    for field in {"source_scope_path", "source_scope_sha256", "corpus_parent"}:
        if not isinstance(value.get(field), str) or not value[field]:
            _error("CORPUS_CLOSURE_INVALID", field)
    if _SHA256.fullmatch(value["source_scope_sha256"]) is None:
        _error("CORPUS_CLOSURE_INVALID", "source_scope_sha256")
    documents = value.get("documents")
    if not isinstance(documents, list):
        _error("CORPUS_CLOSURE_INVALID", "documents")
    paths: list[str] = []
    roots: set[str] = set()
    for index, item in enumerate(documents):
        detail = f"documents[{index}]"
        if not isinstance(item, dict) or item.get("state") not in _STATES:
            _error("CORPUS_CLOSURE_INVALID", detail)
        if set(item) != _expected_document_keys(item["state"]):
            _error("CORPUS_CLOSURE_INVALID", f"{detail} keys")
        for field in {"path", "root", "state", "currentness", "sha256"}:
            if not isinstance(item[field], str) or not item[field]:
                _error("CORPUS_CLOSURE_INVALID", f"{detail}.{field}")
        if item["currentness"] not in _CURRENTNESS or _SHA256.fullmatch(item["sha256"]) is None:
            _error("CORPUS_CLOSURE_INVALID", detail)
        if isinstance(item["size_bytes"], bool) or not isinstance(item["size_bytes"], int) or item["size_bytes"] < 0:
            _error("CORPUS_CLOSURE_INVALID", f"{detail}.size_bytes")
        if item["state"] == "ACTIVE" and (
            not isinstance(item["document_id"], str) or not item["document_id"]
        ):
            _error("CORPUS_CLOSURE_INVALID", f"{detail}.document_id")
        if item["state"] == "EXCLUDED" and item["exclusion_reason"] not in {
            "DUPLICATE",
            "SUPERSEDED",
            "REFERENCE_ONLY",
            "OUT_OF_SCOPE",
        }:
            _error("CORPUS_CLOSURE_INVALID", f"{detail}.exclusion_reason")
        if item["state"] == "PENDING_REVIEW":
            if item["blocked_on"] not in _BLOCKERS:
                _error("CORPUS_CLOSURE_INVALID", f"{detail}.blocked_on")
            if not isinstance(item["recorded_date"], str):
                _error("CORPUS_CLOSURE_INVALID", f"{detail}.recorded_date")
            try:
                parsed_date = date.fromisoformat(item["recorded_date"])
            except ValueError as error:
                raise G0AError(
                    "CORPUS_CLOSURE_INVALID",
                    f"{detail}.recorded_date",
                ) from error
            if parsed_date.isoformat() != item["recorded_date"]:
                _error("CORPUS_CLOSURE_INVALID", f"{detail}.recorded_date")
        paths.append(item["path"])
        roots.add(item["root"])
    if paths != sorted(paths, key=lambda item: item.encode("utf-8")) or len(paths) != len(set(paths)):
        _error("CORPUS_CLOSURE_INVALID", "document order or duplicate path")
    summary = value.get("summary")
    if not isinstance(summary, dict) or set(summary) != _SUMMARY_KEYS:
        _error("CORPUS_CLOSURE_INVALID", "summary")
    expected_summary = _summary(documents, sorted(roots))
    if summary != expected_summary:
        _error("CORPUS_CLOSURE_INVALID", "summary drift")
    return value


def closure_source_state(
    closure: dict,
    repo_root: Path,
) -> dict[str, tuple[str, int]]:
    """Return all 214 source hashes/mtimes and enforce stored full hashes."""
    validated = validate_stored_closure(closure)
    state: dict[str, tuple[str, int]] = {}
    for item in validated["documents"]:
        raw_path = item["path"]
        source = _resolve_existing(repo_root, raw_path, raw_path)
        if not source.is_file():
            _error("SOURCE_STATE_INVALID", raw_path)
        actual_hash = sha256_file(source)
        if actual_hash != item["sha256"]:
            _error("SOURCE_HASH_DRIFT", raw_path)
        state[raw_path] = (actual_hash, source.stat().st_mtime_ns)
    return state


def pending_max_age_days(closure: dict, as_of: date) -> int | None:
    validated = validate_stored_closure(closure)
    oldest = validated["summary"]["oldest_pending_recorded_date"]
    if oldest is None:
        return None
    return (as_of - date.fromisoformat(oldest)).days


def _parse_as_of(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise G0AError("SCOPE_INVALID", f"as_of: {raw}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
    )
    arguments = parser.parse_args(argv)
    try:
        closure = build_closure(
            arguments.repo_root,
            arguments.scope,
            as_of=_parse_as_of(arguments.as_of),
        )
        write_json(arguments.out, closure)
    except G0AError as error:
        print(error, file=sys.stderr)
        return 2
    except Exception as error:
        print(G0AError("CHECK_FAILED", type(error).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
