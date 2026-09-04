"""Check the complete G0-A source ledger without invoking Excel or COM."""

import argparse
import json
import math
import re
import shutil
import stat
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.redaction import detect

from build_corpus_closure import (
    build_closure,
    closure_source_state,
    pending_max_age_days,
    validate_stored_closure,
)
from build_legacy_expected_ledger import initialize_ledger, validate_ledger
from build_resolver_proposal import build_proposal, validate_stored_proposal
from build_skt_workbook_inventory import skt_sources, validate_acquisition
from build_source_registry import build_registry
from build_source_relations import build_relations
from g0a_common import (
    G0AError,
    resolve_repo_relative,
    sha256_bytes,
    sha256_file,
    write_json,
)
from source_scope_v2 import currentness_evidence_paths, load_scope


ARTIFACT_NAMES = (
    "corpus_closure_v1.json",
    "resolver_proposal_v1.json",
    "source_registry_v1.json",
    "skt_workbook_inventory_v1.json",
    "source_relations_v1.json",
    "lgu_legacy_expected_ledger_v1.json",
)
REBUILT_ARTIFACT_NAMES = (
    "corpus_closure_v1.json",
    "resolver_proposal_v1.json",
    "source_registry_v1.json",
    "source_relations_v1.json",
    "lgu_legacy_expected_ledger_v1.json",
)
_INVENTORY_KEYS = {"schema_version", "tool", "workbooks"}
_EXPECTED_COUNTS = {
    "documents": 72,
    "lgu": 2,
    "kt": 4,
    "skt_xls": 66,
    "relations": 3,
    "lgu_cases": 28,
    "lgu_expected": 232,
    "skt_workbooks": 66,
    "corpus_parent_entries": 9,
    "corpus_total": 214,
    "corpus_active": 72,
    "corpus_excluded": 0,
    "corpus_pending_review": 142,
    "corpus_unclassified": 0,
}
_EXPECTED_ROOT_COUNTS = {
    "새 폴더 (2)/KT": {"active": 4, "excluded": 0, "pending_review": 112, "total": 116},
    "새 폴더 (2)/LGU+": {"active": 2, "excluded": 0, "pending_review": 0, "total": 2},
    "새 폴더 (2)/SKT_시험절차서_최신": {
        "active": 66,
        "excluded": 0,
        "pending_review": 0,
        "total": 66,
    },
    "새 폴더 (2)/THOR3_SKT_Requirements": {
        "active": 0,
        "excluded": 0,
        "pending_review": 30,
        "total": 30,
    },
}
_EXPECTED_PENDING_BY_RESOLVER = {
    "CARRIER_INQUIRY": 112,
    "INTERNAL_DECISION": 22,
    "INTAKE_CAPABILITY": 8,
}
_EXPECTED_PROPOSAL_BASIS = {
    "NORMATIVITY_UNKNOWN": 112,
    "SHA256_DUPLICATE_IN_CORPUS": 17,
    "UNSUPPORTED_MEDIA": 8,
    "NON_DOCUMENT_ASSET": 5,
}
_EXPECTED_MSISDN_COUNTS = {
    "corpus_msisdn_fixtures": 9,
    "corpus_msisdn_occurrences": 11,
    "corpus_msisdn_documents": 3,
}
_MSISDN_ALLOWLIST_KEYS = {
    "schema_version",
    "tool",
    "source_artifact",
    "expected_unique",
    "expected_occurrences",
    "fixtures",
}
_MSISDN_FIXTURE_KEYS = {"value_sha256", "rationale", "occurrences"}
_MSISDN_OCCURRENCE_KEYS = {
    "source_path",
    "source_sha256",
    "section_index",
    "section_id",
    "title_sha256",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _require_strict_json_domain(value: object, path: str = "root") -> None:
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _StrictJsonError(f"{path}: non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_strict_json_domain(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8", errors="strict")
            _require_strict_json_domain(item, f"{path}.{key}")
        return
    raise _StrictJsonError(f"{path}: unsupported JSON type")


def _serialized_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _load_json_with_bytes(
    path: Path,
    *,
    require_serialized_canonical: bool = False,
) -> tuple[dict, bytes]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        loaded = json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_object,
        )
        _require_strict_json_domain(loaded)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        _StrictJsonError,
    ) as error:
        raise G0AError("ARTIFACT_INVALID", path.name) from error
    if not isinstance(loaded, dict):
        raise G0AError("ARTIFACT_INVALID", f"{path.name}: non-object root")
    if require_serialized_canonical and raw != _serialized_json_bytes(loaded):
        raise G0AError("ARTIFACT_BYTE_NONCANONICAL", path.name)
    return loaded, raw


def load_json(path: Path, *, require_serialized_canonical: bool = False) -> dict:
    """Load a strict tracked JSON object with one controlled error contract."""
    loaded, _ = _load_json_with_bytes(
        path,
        require_serialized_canonical=require_serialized_canonical,
    )
    return loaded


def _validate_msisdn_allowlist_structure(allowlist: dict) -> None:
    def invalid(detail: str) -> None:
        raise G0AError("MSISDN_FIXTURE_ALLOWLIST_INVALID", detail)

    if not isinstance(allowlist, dict) or set(allowlist) != _MSISDN_ALLOWLIST_KEYS:
        invalid("root fields")
    if (
        allowlist.get("schema_version") != 1
        or allowlist.get("tool") != "corpus-msisdn-fixture-allowlist-v1"
        or allowlist.get("source_artifact")
        != "KR3_Carrier_Requirements/catalog/corpus_index.json"
    ):
        invalid("identity")
    for name in ("expected_unique", "expected_occurrences"):
        value = allowlist.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            invalid(name)
    fixtures = allowlist.get("fixtures")
    if not isinstance(fixtures, list):
        invalid("fixtures")
    seen_values: set[str] = set()
    seen_occurrences: set[tuple[object, ...]] = set()
    for fixture in fixtures:
        if not isinstance(fixture, dict) or set(fixture) != _MSISDN_FIXTURE_KEYS:
            invalid("fixture fields")
        value_sha256 = fixture.get("value_sha256")
        if not isinstance(value_sha256, str) or not _SHA256_RE.fullmatch(value_sha256):
            invalid("value_sha256")
        if value_sha256 in seen_values:
            invalid("duplicate value_sha256")
        seen_values.add(value_sha256)
        rationale = fixture.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            invalid("rationale")
        occurrences = fixture.get("occurrences")
        if not isinstance(occurrences, list) or not occurrences:
            invalid("occurrences")
        for occurrence in occurrences:
            if (
                not isinstance(occurrence, dict)
                or set(occurrence) != _MSISDN_OCCURRENCE_KEYS
            ):
                invalid("occurrence fields")
            if not isinstance(occurrence.get("source_path"), str):
                invalid("source_path")
            if not isinstance(occurrence.get("section_id"), str):
                invalid("section_id")
            section_index = occurrence.get("section_index")
            if (
                isinstance(section_index, bool)
                or not isinstance(section_index, int)
                or section_index < 0
            ):
                invalid("section_index")
            for name in ("source_sha256", "title_sha256"):
                digest = occurrence.get(name)
                if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                    invalid(name)
            identity = (
                value_sha256,
                occurrence["source_path"],
                occurrence["source_sha256"],
                section_index,
                occurrence["section_id"],
                occurrence["title_sha256"],
            )
            if identity in seen_occurrences:
                invalid("duplicate occurrence")
            seen_occurrences.add(identity)
    if len(fixtures) != allowlist["expected_unique"]:
        invalid("expected_unique")
    if len(seen_occurrences) != allowlist["expected_occurrences"]:
        invalid("expected_occurrences")


def validate_corpus_msisdn_fixtures(
    corpus_index: dict,
    allowlist: dict,
    closure: dict,
) -> dict[str, int]:
    """Match title-only MSISDN detections to source-bound exact fixtures."""
    _validate_msisdn_allowlist_structure(allowlist)
    try:
        closure_by_path = {
            document["path"]: document["sha256"]
            for document in closure["documents"]
        }
        actual: dict[str, list[dict[str, object]]] = {}
        documents_with_matches: set[str] = set()
        root = corpus_index["root"].rstrip("/")
        for document in corpus_index["docs"]:
            source_path = f"{root}/{document['rel']}"
            source_sha256 = closure_by_path[source_path]
            for section_index, section in enumerate(document["sections"]):
                title = section["title"]
                for span in detect(title):
                    if span.kind != "MSISDN":
                        continue
                    value_sha256 = sha256_bytes(span.value.encode("utf-8"))
                    actual.setdefault(value_sha256, []).append(
                        {
                            "source_path": source_path,
                            "source_sha256": source_sha256,
                            "section_index": section_index,
                            "section_id": section["id"],
                            "title_sha256": sha256_bytes(title.encode("utf-8")),
                        }
                    )
                    documents_with_matches.add(source_path)
        expected = {
            fixture["value_sha256"]: fixture["occurrences"]
            for fixture in allowlist["fixtures"]
        }
    except (KeyError, TypeError, ValueError) as error:
        raise G0AError("MSISDN_FIXTURE_ALLOWLIST_INVALID", "structure") from error

    if actual != expected:
        raise G0AError("MSISDN_FIXTURE_MISMATCH", "title occurrences")
    counts = {
        "corpus_msisdn_fixtures": len(actual),
        "corpus_msisdn_occurrences": sum(len(items) for items in actual.values()),
        "corpus_msisdn_documents": len(documents_with_matches),
    }
    if allowlist.get("expected_unique") != counts["corpus_msisdn_fixtures"]:
        raise G0AError("MSISDN_FIXTURE_ALLOWLIST_INVALID", "expected_unique")
    if allowlist.get("expected_occurrences") != counts["corpus_msisdn_occurrences"]:
        raise G0AError("MSISDN_FIXTURE_ALLOWLIST_INVALID", "expected_occurrences")
    return counts


def compare_expected_artifact_bytes(expected_dir: Path, rebuilt_dir: Path) -> None:
    """Require every reproducible artifact to match byte for byte."""
    for name in REBUILT_ARTIFACT_NAMES:
        try:
            expected = (expected_dir / name).read_bytes()
            rebuilt = (rebuilt_dir / name).read_bytes()
        except OSError as error:
            raise G0AError("ARTIFACT_INVALID", name) from error
        if expected != rebuilt:
            raise G0AError("ARTIFACT_BYTE_DRIFT", name)


def _validate_inventory_schema_if_available(inventory: dict, schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        return

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        validator.check_schema(schema)
        first_error = next(iter(validator.iter_errors(inventory)), None)
    except (OSError, UnicodeError, json.JSONDecodeError, jsonschema.SchemaError) as error:
        raise G0AError("SKT_INVENTORY_SCHEMA_INVALID", schema_path.name) from error
    if first_error is not None:
        location = ".".join(str(part) for part in first_error.absolute_path) or "root"
        raise G0AError("SKT_INVENTORY_SCHEMA_MISMATCH", location)


def validate_stored_inventory(
    inventory: dict,
    registry: dict,
    schema_path: Path,
) -> dict:
    """Validate the stored structural acquisition without running its COM backend."""
    if (
        not isinstance(inventory, dict)
        or set(inventory) != _INVENTORY_KEYS
        or isinstance(inventory.get("schema_version"), bool)
        or inventory.get("schema_version") != 1
        or inventory.get("tool") != "skt-workbook-inventory-v1"
        or not isinstance(inventory.get("workbooks"), list)
    ):
        raise G0AError("SKT_INVENTORY_INVALID", "top-level contract")

    sources = skt_sources(registry)
    canonical_workbooks = validate_acquisition(
        {"workbooks": inventory["workbooks"]},
        sources,
    )
    if canonical_workbooks != inventory["workbooks"]:
        raise G0AError(
            "SKT_INVENTORY_CANONICALIZATION_DRIFT",
            "stored workbooks differ from canonical acquisition",
        )
    _validate_inventory_schema_if_available(inventory, schema_path)
    return inventory


def source_state(registry: dict, repo_root: Path) -> dict[str, tuple[str, int]]:
    """Snapshot every registered source's content hash and nanosecond mtime."""
    documents = registry.get("documents") if isinstance(registry, dict) else None
    if not isinstance(documents, list):
        raise G0AError("SOURCE_REGISTRY_INVALID", "documents")
    state: dict[str, tuple[str, int]] = {}
    for index, document in enumerate(documents):
        if not isinstance(document, dict) or not isinstance(document.get("path"), str):
            raise G0AError("SOURCE_REGISTRY_INVALID", f"documents[{index}].path")
        raw_path = document["path"]
        if raw_path in state:
            raise G0AError("SOURCE_REGISTRY_INVALID", f"duplicate path: {raw_path}")
        try:
            source_path = resolve_repo_relative(repo_root, raw_path)
            if not source_path.is_file():
                raise OSError("source is not a file")
            state[raw_path] = (sha256_file(source_path), source_path.stat().st_mtime_ns)
        except G0AError:
            raise
        except OSError as error:
            raise G0AError("SOURCE_STATE_INVALID", raw_path) from error
    return state


def _file_state(path: Path, detail: str) -> tuple[str, int]:
    try:
        if path.is_symlink() or not path.is_file():
            raise OSError("input is not a regular file")
        return sha256_file(path), path.stat().st_mtime_ns
    except OSError as error:
        raise G0AError("SOURCE_STATE_INVALID", detail) from error


def _is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or (
            hasattr(path, "is_junction") and path.is_junction()
        )
    except OSError as error:
        raise G0AError("SOURCE_STATE_INVALID", str(path)) from error


def _reject_link_ancestry(path: Path, boundary: Path, detail: str) -> None:
    try:
        relative = path.relative_to(boundary)
    except ValueError as error:
        raise G0AError("SOURCE_STATE_INVALID", f"{detail}: parent escape") from error
    current = boundary
    for component in relative.parts:
        current /= component
        if _is_link_or_junction(current):
            raise G0AError("SOURCE_STATE_INVALID", f"{detail}: linked ancestry")


def _stage1_input_paths(
    repo_root: Path,
    stage1_dir: Path,
) -> tuple[Path, list[Path]]:
    try:
        resolved_repo = repo_root.resolve(strict=True)
        _reject_link_ancestry(stage1_dir, resolved_repo, "stage1")
        resolved_stage1 = stage1_dir.resolve(strict=True)
        if not resolved_stage1.is_relative_to(resolved_repo):
            raise G0AError("SOURCE_STATE_INVALID", "stage1: parent escape")
        if not resolved_stage1.is_dir():
            raise OSError("stage1 is not a directory")
        stage1_files = sorted(
            resolved_stage1.glob("*_canonical.yaml"),
            key=lambda item: item.name,
        )
    except G0AError:
        raise
    except (OSError, RuntimeError) as error:
        raise G0AError("SOURCE_STATE_INVALID", "stage1") from error
    if not stage1_files:
        raise G0AError("SOURCE_STATE_INVALID", "stage1: no canonical YAML")
    for path in stage1_files:
        detail = f"stage1/{path.name}"
        _reject_link_ancestry(path, resolved_stage1, detail)
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise G0AError("SOURCE_STATE_INVALID", detail) from error
        if not resolved_path.is_relative_to(resolved_stage1) or not resolved_path.is_relative_to(
            resolved_repo
        ):
            raise G0AError("SOURCE_STATE_INVALID", f"{detail}: parent escape")
    return resolved_stage1, stage1_files


def _auxiliary_input_state(
    repo_root: Path,
    scope_path: Path,
    scope_schema_path: Path,
    closure_schema_path: Path,
    inventory_schema_path: Path,
    msisdn_allowlist_path: Path,
    msisdn_allowlist_schema_path: Path,
    corpus_index_path: Path,
    stage1_dir: Path,
    scope: dict,
) -> dict[str, tuple[str, int]]:
    state = {
        "scope": _file_state(scope_path, "scope"),
        "scope_schema": _file_state(scope_schema_path, "scope_schema"),
        "closure_schema": _file_state(closure_schema_path, "closure_schema"),
        "inventory_schema": _file_state(inventory_schema_path, "inventory_schema"),
        "msisdn_allowlist": _file_state(
            msisdn_allowlist_path,
            "msisdn_allowlist",
        ),
        "msisdn_allowlist_schema": _file_state(
            msisdn_allowlist_schema_path,
            "msisdn_allowlist_schema",
        ),
        "corpus_index": _file_state(corpus_index_path, "corpus_index"),
    }
    for raw_path in currentness_evidence_paths(scope):
        evidence = resolve_repo_relative(repo_root, raw_path)
        state[f"evidence/{raw_path}"] = _file_state(evidence, f"evidence/{raw_path}")
    _, stage1_files = _stage1_input_paths(repo_root, stage1_dir)
    for path in stage1_files:
        state[f"stage1/{path.name}"] = _file_state(path, f"stage1/{path.name}")
    return state


def _copy_verified_snapshot(
    source: Path,
    destination: Path,
    expected_sha256: str,
    detail: str,
    copied: list[Path],
) -> None:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if sha256_file(destination) != expected_sha256:
            raise G0AError("SNAPSHOT_HASH_MISMATCH", detail)
        destination.chmod(stat.S_IREAD)
        copied.append(destination)
    except G0AError:
        raise
    except OSError as error:
        raise G0AError("SNAPSHOT_COPY_FAILED", detail) from error


def _snapshot_consumed_inputs(
    closure: dict,
    scope: dict,
    repo_root: Path,
    snapshot_root: Path,
    source_before: dict[str, tuple[str, int]],
    auxiliary_before: dict[str, tuple[str, int]],
    copied: list[Path],
) -> tuple[Path, Path, Path]:
    for document in closure["documents"]:
        raw_path = document["path"]
        expected_sha256 = document["sha256"]
        if source_before[raw_path][0] != expected_sha256:
            raise G0AError("SOURCE_HASH_DRIFT", raw_path)
        _copy_verified_snapshot(
            resolve_repo_relative(repo_root, raw_path),
            resolve_repo_relative(snapshot_root, raw_path),
            expected_sha256,
            raw_path,
            copied,
        )

    scope_relative = "KR3_Carrier_Requirements/contracts/source_scope_v2.yaml"
    scope_source = resolve_repo_relative(repo_root, scope_relative)
    scope_snapshot = resolve_repo_relative(snapshot_root, scope_relative)
    _copy_verified_snapshot(
        scope_source,
        scope_snapshot,
        auxiliary_before["scope"][0],
        "scope",
        copied,
    )

    scope_schema_relative = (
        "KR3_Carrier_Requirements/contracts/source_scope_schema_v2.json"
    )
    _copy_verified_snapshot(
        resolve_repo_relative(repo_root, scope_schema_relative),
        resolve_repo_relative(snapshot_root, scope_schema_relative),
        auxiliary_before["scope_schema"][0],
        "scope_schema",
        copied,
    )

    closure_schema_relative = (
        "KR3_Carrier_Requirements/contracts/corpus_closure_schema_v1.json"
    )
    _copy_verified_snapshot(
        resolve_repo_relative(repo_root, closure_schema_relative),
        resolve_repo_relative(snapshot_root, closure_schema_relative),
        auxiliary_before["closure_schema"][0],
        "closure_schema",
        copied,
    )

    schema_relative = (
        "KR3_Carrier_Requirements/contracts/skt_workbook_inventory_schema_v1.json"
    )
    schema_source = resolve_repo_relative(repo_root, schema_relative)
    schema_snapshot = resolve_repo_relative(snapshot_root, schema_relative)
    _copy_verified_snapshot(
        schema_source,
        schema_snapshot,
        auxiliary_before["inventory_schema"][0],
        "inventory_schema",
        copied,
    )

    for raw_path in currentness_evidence_paths(scope):
        key = f"evidence/{raw_path}"
        _copy_verified_snapshot(
            resolve_repo_relative(repo_root, raw_path),
            resolve_repo_relative(snapshot_root, raw_path),
            auxiliary_before[key][0],
            key,
            copied,
        )

    snapshot_parent = resolve_repo_relative(
        snapshot_root,
        str(scope["corpus_parent"]["path"]),
    )
    for root in scope["corpus_roots"]:
        resolve_repo_relative(snapshot_root, str(root["root"])).mkdir(
            parents=True,
            exist_ok=True,
        )
    for entry in scope["corpus_parent"]["non_corpus_entries"]:
        target = snapshot_parent / str(entry["name"])
        if entry["kind"] == "DIRECTORY":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")

    stage1_source, stage1_files = _stage1_input_paths(
        repo_root,
        repo_root / "KR3_Carrier_Requirements" / "stage1",
    )
    stage1_snapshot = snapshot_root / "KR3_Carrier_Requirements" / "stage1"
    stage1_by_name = {path.name: path for path in stage1_files}
    for key, (expected_sha256, _) in auxiliary_before.items():
        if not key.startswith("stage1/"):
            continue
        filename = key.removeprefix("stage1/")
        source_path = stage1_by_name.get(filename)
        if source_path is None or source_path.parent != stage1_source:
            raise G0AError("SOURCE_STATE_INVALID", key)
        _copy_verified_snapshot(
            source_path,
            stage1_snapshot / filename,
            expected_sha256,
            key,
            copied,
        )
    return scope_snapshot, schema_snapshot, stage1_snapshot


def _make_snapshots_writable(copied: list[Path]) -> None:
    for path in copied:
        try:
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
        except OSError:
            pass


def _count_used_rows(inventory: dict) -> int:
    return sum(
        sheet["used_range"]["last_row"] - sheet["used_range"]["first_row"] + 1
        for workbook in inventory["workbooks"]
        for sheet in workbook["sheets"]
    )


def summarize(
    registry: dict,
    relations: dict,
    expected_ledger: dict,
    inventory: dict,
    closure: dict,
    proposal: dict,
    *,
    corpus_parent_entries: int,
    as_of: date,
) -> dict[str, object]:
    """Return measured G0-A totals and reject every acceptance-count drift."""
    try:
        documents = registry["documents"]
        relation_items = relations["relations"]
        workbooks = inventory["workbooks"]
        closure_summary = closure["summary"]
        counts = {
            "documents": len(documents),
            "lgu": sum(document["carrier"] == "LGU+" for document in documents),
            "kt": sum(document["carrier"] == "KT" for document in documents),
            "skt_xls": sum(
                document["carrier"] == "SKT"
                and document["media_type"] == "application/vnd.ms-excel"
                for document in documents
            ),
            "relations": len(relation_items),
            "lgu_cases": expected_ledger["case_count"],
            "lgu_expected": expected_ledger["expected_count"],
            "skt_workbooks": len(workbooks),
            "readable_workbooks": sum(
                workbook["acquisition_status"] == "READABLE" for workbook in workbooks
            ),
            "failed_workbooks": sum(
                workbook["acquisition_status"] == "FAILED" for workbook in workbooks
            ),
            "sheets": sum(workbook["sheet_count"] for workbook in workbooks),
            "used_rows": _count_used_rows(inventory),
            "corpus_parent_entries": corpus_parent_entries,
            "corpus_total": closure_summary["total"],
            "corpus_active": closure_summary["active"],
            "corpus_excluded": closure_summary["excluded"],
            "corpus_pending_review": closure_summary["pending_review"],
            "corpus_unclassified": closure_summary["unclassified"],
            "root_counts": closure_summary["roots"],
            "pending_by_resolver": closure_summary["pending_by_resolver"],
            "oldest_pending_recorded_date": closure_summary[
                "oldest_pending_recorded_date"
            ],
            "pending_max_age_days": pending_max_age_days(closure, as_of),
            "currentness": closure_summary["currentness"],
            "proposal_basis": proposal["summary"]["by_basis"],
            "duplicate_groups": proposal["summary"]["duplicate_group_count"],
            "duplicate_members": proposal["summary"]["duplicate_member_count"],
        }
    except (KeyError, TypeError, ValueError) as error:
        raise G0AError("ARTIFACT_INVALID", "summary structure") from error

    mismatches = [
        f"{name}: expected={expected}; found={counts.get(name)}"
        for name, expected in _EXPECTED_COUNTS.items()
        if counts.get(name) != expected
    ]
    if mismatches:
        raise G0AError("ACCEPTANCE_COUNT_MISMATCH", "; ".join(mismatches))
    if counts["root_counts"] != _EXPECTED_ROOT_COUNTS:
        raise G0AError(
            "ACCEPTANCE_COUNT_MISMATCH",
            "root state counts",
        )
    if counts["pending_by_resolver"] != _EXPECTED_PENDING_BY_RESOLVER:
        raise G0AError(
            "ACCEPTANCE_COUNT_MISMATCH",
            "pending resolver counts",
        )
    if counts["proposal_basis"] != _EXPECTED_PROPOSAL_BASIS:
        raise G0AError(
            "ACCEPTANCE_COUNT_MISMATCH",
            "proposal basis counts",
        )
    if counts["duplicate_groups"] != 8 or counts["duplicate_members"] != 17:
        raise G0AError(
            "ACCEPTANCE_COUNT_MISMATCH",
            "proposal duplicate counts",
        )
    if counts["failed_workbooks"]:
        distribution = Counter(
            workbook["error_code"]
            for workbook in workbooks
            if workbook["acquisition_status"] == "FAILED"
        )
        formatted = ",".join(
            f"{code}={distribution[code]}" for code in sorted(distribution)
        )
        raise G0AError(
            "SKT_WORKBOOK_FAILED",
            f"failed={counts['failed_workbooks']}; error_codes={formatted}",
        )
    return counts


def check_all(
    repo_root: Path,
    artifact_dir: Path,
    *,
    as_of: date | None = None,
) -> dict[str, object]:
    """Rebuild portable artifacts, validate closure, and audit all source state."""
    effective_date = as_of or datetime.now(timezone(timedelta(hours=9))).date()
    root = repo_root.resolve()
    scope_path = root / "KR3_Carrier_Requirements" / "contracts" / "source_scope_v2.yaml"
    scope_schema_path = (
        root
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "source_scope_schema_v2.json"
    )
    closure_schema_path = (
        root
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "corpus_closure_schema_v1.json"
    )
    inventory_schema_path = (
        root
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "skt_workbook_inventory_schema_v1.json"
    )
    msisdn_allowlist_path = (
        root
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "corpus_msisdn_fixture_allowlist_v1.json"
    )
    msisdn_allowlist_schema_path = (
        root
        / "KR3_Carrier_Requirements"
        / "contracts"
        / "corpus_msisdn_fixture_allowlist_schema_v1.json"
    )
    corpus_index_path = artifact_dir / "corpus_index.json"
    stage1_dir = root / "KR3_Carrier_Requirements" / "stage1"
    artifacts: dict[str, dict] = {}
    artifact_bytes: dict[str, bytes] = {}
    for name in ARTIFACT_NAMES:
        loaded, raw = _load_json_with_bytes(
            artifact_dir / name,
            require_serialized_canonical=(
                name
                in {
                    "corpus_closure_v1.json",
                    "resolver_proposal_v1.json",
                    "skt_workbook_inventory_v1.json",
                }
            ),
        )
        artifacts[name] = loaded
        artifact_bytes[name] = raw
    closure = validate_stored_closure(artifacts["corpus_closure_v1.json"])
    _load_json_with_bytes(msisdn_allowlist_schema_path)
    msisdn_allowlist = load_json(
        msisdn_allowlist_path,
        require_serialized_canonical=True,
    )
    corpus_index = load_json(corpus_index_path)
    msisdn_counts = validate_corpus_msisdn_fixtures(
        corpus_index,
        msisdn_allowlist,
        closure,
    )
    msisdn_mismatches = [
        f"{name}: expected={expected}; found={msisdn_counts.get(name)}"
        for name, expected in _EXPECTED_MSISDN_COUNTS.items()
        if msisdn_counts.get(name) != expected
    ]
    if msisdn_mismatches:
        raise G0AError(
            "ACCEPTANCE_COUNT_MISMATCH",
            "; ".join(msisdn_mismatches),
        )
    tracked_proposal = artifacts["resolver_proposal_v1.json"]
    registry = artifacts["source_registry_v1.json"]
    inventory = artifacts["skt_workbook_inventory_v1.json"]
    tracked_relations = artifacts["source_relations_v1.json"]
    tracked_ledger = artifacts["lgu_legacy_expected_ledger_v1.json"]
    validate_ledger(tracked_ledger)
    scope = load_scope(scope_path, as_of=effective_date)
    source_before = closure_source_state(closure, root)
    auxiliary_before = _auxiliary_input_state(
        root,
        scope_path,
        scope_schema_path,
        closure_schema_path,
        inventory_schema_path,
        msisdn_allowlist_path,
        msisdn_allowlist_schema_path,
        corpus_index_path,
        stage1_dir,
        scope,
    )
    proposal = validate_stored_proposal(
        tracked_proposal,
        closure,
        closure_sha256=sha256_bytes(artifact_bytes["corpus_closure_v1.json"]),
        source_scope_sha256=auxiliary_before["scope"][0],
    )
    pending_error: G0AError | None = None
    counts: dict[str, object] | None = None
    try:
        live_closure = build_closure(root, scope_path, as_of=effective_date)
        if live_closure != closure:
            raise G0AError("ARTIFACT_BYTE_DRIFT", "corpus_closure_v1.json")
        with tempfile.TemporaryDirectory(prefix="kr3-g0a-") as temporary:
            temporary_root = Path(temporary)
            snapshot_root = temporary_root / "repo-snapshot"
            tracked_snapshot_dir = temporary_root / "tracked-artifacts"
            rebuilt_dir = temporary_root / "rebuilt"
            tracked_snapshot_dir.mkdir()
            rebuilt_dir.mkdir()
            for name, raw in artifact_bytes.items():
                (tracked_snapshot_dir / name).write_bytes(raw)

            copied: list[Path] = []
            try:
                snapshot_scope, snapshot_schema, snapshot_stage1 = _snapshot_consumed_inputs(
                    closure,
                    scope,
                    root,
                    snapshot_root,
                    source_before,
                    auxiliary_before,
                    copied,
                )
                snapshot_scope_value = load_scope(
                    snapshot_scope,
                    as_of=effective_date,
                )
                # Full registry validation happens against the snapshotted scope.
                build_relations(snapshot_scope_value, registry)
                validate_stored_inventory(inventory, registry, snapshot_schema)
                rebuilt_closure = build_closure(
                    snapshot_root,
                    snapshot_scope,
                    as_of=effective_date,
                )
                rebuilt_registry = build_registry(snapshot_root, snapshot_scope)
                rebuilt_relations = build_relations(
                    snapshot_scope_value,
                    rebuilt_registry,
                )
                rebuilt_ledger = initialize_ledger(snapshot_stage1)
                rebuilt_closure_path = rebuilt_dir / "corpus_closure_v1.json"
                write_json(rebuilt_closure_path, rebuilt_closure)
                rebuilt_proposal = build_proposal(
                    rebuilt_closure,
                    closure_sha256=sha256_file(rebuilt_closure_path),
                    source_scope_sha256=sha256_file(snapshot_scope),
                )
                write_json(
                    rebuilt_dir / "resolver_proposal_v1.json",
                    rebuilt_proposal,
                )
                write_json(rebuilt_dir / "source_registry_v1.json", rebuilt_registry)
                write_json(rebuilt_dir / "source_relations_v1.json", rebuilt_relations)
                write_json(
                    rebuilt_dir / "lgu_legacy_expected_ledger_v1.json",
                    rebuilt_ledger,
                )
                compare_expected_artifact_bytes(tracked_snapshot_dir, rebuilt_dir)
            finally:
                _make_snapshots_writable(copied)
        counts = summarize(
            registry,
            tracked_relations,
            tracked_ledger,
            inventory,
            closure,
            proposal,
            corpus_parent_entries=scope["corpus_parent"]["expected_entries"],
            as_of=effective_date,
        )
        counts.update(msisdn_counts)
    except G0AError as error:
        pending_error = error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        pending_error = G0AError("BUILDER_FAILED", type(error).__name__)
    finally:
        try:
            source_after = closure_source_state(closure, root)
            auxiliary_after = _auxiliary_input_state(
                root,
                scope_path,
                scope_schema_path,
                closure_schema_path,
                inventory_schema_path,
                msisdn_allowlist_path,
                msisdn_allowlist_schema_path,
                corpus_index_path,
                stage1_dir,
                scope,
            )
        except G0AError as error:
            raise G0AError("SOURCE_MUTATION", error.detail) from error
        if source_before != source_after or auxiliary_before != auxiliary_after:
            raise G0AError("SOURCE_MUTATION", "source hash or mtime changed")
    if pending_error is not None:
        raise pending_error
    if counts is None:
        raise G0AError("CHECK_FAILED", "missing summary")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
    )
    arguments = parser.parse_args(argv)
    try:
        try:
            as_of = date.fromisoformat(arguments.as_of)
        except ValueError as error:
            raise G0AError("SCOPE_INVALID", f"as_of: {arguments.as_of}") from error
        repo_root = arguments.repo_root.resolve()
        artifact_dir = (
            arguments.artifact_dir.resolve()
            if arguments.artifact_dir is not None
            else repo_root / "KR3_Carrier_Requirements" / "catalog"
        )
        counts = check_all(repo_root, artifact_dir, as_of=as_of)
    except G0AError as error:
        print(error, file=sys.stderr)
        return 2
    except Exception as error:
        print(G0AError("CHECK_FAILED", type(error).__name__), file=sys.stderr)
        return 2

    print(
        f"documents={counts['documents']} lgu={counts['lgu']} "
        f"kt={counts['kt']} skt_xls={counts['skt_xls']}"
    )
    print(f"relations={counts['relations']}")
    print(
        f"lgu_cases={counts['lgu_cases']} "
        f"lgu_expected={counts['lgu_expected']}"
    )
    print(
        f"skt_workbooks={counts['skt_workbooks']} "
        f"readable={counts['readable_workbooks']} "
        f"failed={counts['failed_workbooks']} sheets={counts['sheets']} "
        f"used_rows={counts['used_rows']}"
    )
    print(
        f"corpus_parent_entries={counts['corpus_parent_entries']}/"
        f"{counts['corpus_parent_entries']}"
    )
    print(
        f"corpus_msisdn_fixtures={counts['corpus_msisdn_fixtures']}/9 "
        f"occurrences={counts['corpus_msisdn_occurrences']}/11 "
        f"documents={counts['corpus_msisdn_documents']}/3"
    )
    print(
        f"corpus_total={counts['corpus_total']} active={counts['corpus_active']} "
        f"excluded={counts['corpus_excluded']} "
        f"pending_review={counts['corpus_pending_review']} "
        f"unclassified={counts['corpus_unclassified']}"
    )
    pending = counts["pending_by_resolver"]
    print(
        "pending_by_resolver="
        f"CARRIER_INQUIRY:{pending['CARRIER_INQUIRY']},"
        f"INTERNAL_DECISION:{pending['INTERNAL_DECISION']},"
        f"INTAKE_CAPABILITY:{pending['INTAKE_CAPABILITY']}"
    )
    proposal_basis = counts["proposal_basis"]
    print(
        "proposal_basis="
        f"NORMATIVITY_UNKNOWN:{proposal_basis['NORMATIVITY_UNKNOWN']},"
        "SHA256_DUPLICATE_IN_CORPUS:"
        f"{proposal_basis['SHA256_DUPLICATE_IN_CORPUS']},"
        f"UNSUPPORTED_MEDIA:{proposal_basis['UNSUPPORTED_MEDIA']},"
        f"NON_DOCUMENT_ASSET:{proposal_basis['NON_DOCUMENT_ASSET']}"
    )
    print(
        f"duplicate_groups={counts['duplicate_groups']} "
        f"duplicate_members={counts['duplicate_members']}"
    )
    print(
        f"oldest_pending_recorded_date={counts['oldest_pending_recorded_date']} "
        f"pending_max_age_days={counts['pending_max_age_days']}"
    )
    currentness = counts["currentness"]
    print(
        f"currentness=CURRENT:{currentness['CURRENT']},"
        f"CURRENTNESS_UNVERIFIED:{currentness['CURRENTNESS_UNVERIFIED']}"
    )
    print("semantic_parse_status=NOT_ATTEMPTED")
    print("byte_drift=0 source_mutation=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
