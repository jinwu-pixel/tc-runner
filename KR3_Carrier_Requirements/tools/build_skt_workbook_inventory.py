"""Build a structural-only inventory for the registered SKT legacy workbooks."""

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from g0a_common import G0AError, resolve_repo_relative, write_json


_REGISTRY_KEYS = {"schema_version", "documents"}
_SOURCE_KEYS = {
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
_WORKBOOK_KEYS = {
    "document_id",
    "path",
    "source_sha256",
    "acquisition_status",
    "error_code",
    "sheet_count",
    "sheets",
}
_SHEET_KEYS = {"sheet_index", "sheet_name", "visibility", "used_range"}
_RANGE_KEYS = {"first_row", "last_row", "first_column", "last_column"}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CODE_PATTERN = re.compile(r"^(?:SOURCE_HASH_DRIFT|EXCEL_COM_[0-9A-F]{8})$")


def _fail(code: str, detail: str) -> None:
    raise G0AError(code, detail)


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _integer_at_least(value: object, minimum: int) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= minimum
    return (
        isinstance(value, float)
        and math.isfinite(value)
        and value.is_integer()
        and value >= minimum
    )


def _safe_posix_path(value: object) -> bool:
    if not _nonempty_string(value) or "\\" in value:
        return False
    pure = PurePosixPath(value)
    return not (
        pure.is_absolute()
        or value.startswith("//")
        or re.match(r"^[A-Za-z]:", value)
        or ".." in pure.parts
        or any(part in {"", "."} for part in value.split("/"))
    )


def load_registry(path: Path) -> dict:
    """Load a source registry, rejecting malformed or non-object roots."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise G0AError("SOURCE_REGISTRY_INVALID", "unable to load registry") from error
    if (
        not isinstance(loaded, dict)
        or set(loaded) != _REGISTRY_KEYS
        or loaded.get("schema_version") != 1
        or not isinstance(loaded.get("documents"), list)
    ):
        _fail("SOURCE_REGISTRY_INVALID", "malformed root")
    return loaded


def _validate_source(document: object, index: int) -> dict:
    if not isinstance(document, dict) or set(document) != _SOURCE_KEYS:
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}] keys")
    intake = document["intake"]
    if not isinstance(intake, dict) or set(intake) != _INTAKE_KEYS:
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].intake")
    if not all(
        _nonempty_string(document[field])
        for field in ("document_id", "carrier", "role", "media_type", "path")
    ):
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}] strings")
    if document["carrier"] != "SKT" or document["media_type"] != "application/vnd.ms-excel":
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}] selection")
    if document["role"] not in {"REQUIREMENT", "PROCEDURE", "SAT"}:
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].role")
    if not _safe_posix_path(document["path"]):
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].path")
    if not _integer_at_least(document["size_bytes"], 0):
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].size_bytes")
    if not _nonempty_string(document["sha256"]) or not _SHA256_PATTERN.fullmatch(document["sha256"]):
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].sha256")
    if (
        intake["container_status"] not in {"READABLE", "UNREADABLE"}
        or intake["semantic_parse_status"] != "NOT_ATTEMPTED"
        or intake["semantic_parser"] is not None
    ):
        _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}].intake values")
    return document


def skt_sources(registry: dict) -> list[dict]:
    """Select and validate exactly the 66 registered SKT legacy XLS sources."""
    if (
        not isinstance(registry, dict)
        or set(registry) != _REGISTRY_KEYS
        or registry.get("schema_version") != 1
        or not isinstance(registry.get("documents"), list)
    ):
        _fail("SOURCE_REGISTRY_INVALID", "malformed root")

    selected: list[dict] = []
    for index, document in enumerate(registry["documents"]):
        if not isinstance(document, dict):
            _fail("SOURCE_REGISTRY_INVALID", f"documents[{index}]")
        if document.get("carrier") == "SKT" and document.get("media_type") == "application/vnd.ms-excel":
            selected.append(_validate_source(document, index))

    if len(selected) != 66:
        _fail("SKT_SOURCE_COUNT_MISMATCH", f"expected=66; found={len(selected)}")
    document_ids = [str(document["document_id"]) for document in selected]
    paths = [str(document["path"]) for document in selected]
    if len(document_ids) != len(set(document_ids)) or len(paths) != len(set(paths)):
        _fail("SOURCE_REGISTRY_INVALID", "duplicate SKT document ID or path")
    return sorted(selected, key=lambda item: str(item["document_id"]))


def _validate_sheet(value: object, expected_index: int, detail: str) -> dict:
    if not isinstance(value, dict) or set(value) != _SHEET_KEYS:
        _fail("XLS_ACQUISITION_INVALID", f"{detail} keys")
    if value["sheet_index"] != expected_index or not _integer_at_least(value["sheet_index"], 1):
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.sheet_index")
    if not _nonempty_string(value["sheet_name"]):
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.sheet_name")
    if value["visibility"] not in {"VISIBLE", "HIDDEN", "VERY_HIDDEN"}:
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.visibility")
    used_range = value["used_range"]
    if not isinstance(used_range, dict) or set(used_range) != _RANGE_KEYS:
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.used_range")
    if not all(_integer_at_least(used_range[field], 1) for field in _RANGE_KEYS):
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.used_range minima")
    if (
        used_range["last_row"] < used_range["first_row"]
        or used_range["last_column"] < used_range["first_column"]
    ):
        _fail("XLS_ACQUISITION_INVALID", f"{detail}.used_range order")
    return {
        "sheet_index": value["sheet_index"],
        "sheet_name": value["sheet_name"],
        "visibility": value["visibility"],
        "used_range": {field: used_range[field] for field in sorted(_RANGE_KEYS)},
    }


def validate_acquisition(raw: dict, sources: list[dict]) -> list[dict]:
    """Validate backend dispositions and return canonical workbook records."""
    if not isinstance(raw, dict) or set(raw) != {"workbooks"} or not isinstance(raw["workbooks"], list):
        _fail("XLS_ACQUISITION_INVALID", "malformed root")
    source_by_id = {str(source["document_id"]): source for source in sources}
    entries = raw["workbooks"]
    ids: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not _nonempty_string(entry.get("document_id")):
            _fail("XLS_ACQUISITION_INVALID", f"workbooks[{index}].document_id")
        ids.append(entry["document_id"])
    if len(ids) != len(set(ids)) or set(ids) != set(source_by_id):
        _fail("XLS_ACQUISITION_SOURCE_SET_MISMATCH", "missing, extra, or duplicate disposition")

    canonical: list[dict] = []
    for index, entry in enumerate(entries):
        detail = f"workbooks[{index}]"
        if set(entry) != _WORKBOOK_KEYS:
            _fail("XLS_ACQUISITION_INVALID", f"{detail} keys")
        source = source_by_id[entry["document_id"]]
        if entry["path"] != source["path"] or entry["source_sha256"] != source["sha256"]:
            _fail("XLS_ACQUISITION_IDENTITY_MISMATCH", str(entry["document_id"]))
        if entry["acquisition_status"] not in {"READABLE", "FAILED"}:
            _fail("XLS_ACQUISITION_INVALID", f"{detail}.acquisition_status")
        if not _integer_at_least(entry["sheet_count"], 0) or not isinstance(entry["sheets"], list):
            _fail("XLS_ACQUISITION_INVALID", f"{detail}.sheet collection")

        if entry["acquisition_status"] == "FAILED":
            if (
                entry["sheet_count"] != 0
                or entry["sheets"] != []
                or not _nonempty_string(entry["error_code"])
                or not _ERROR_CODE_PATTERN.fullmatch(entry["error_code"])
            ):
                _fail("XLS_ACQUISITION_INVALID", f"{detail} FAILED invariant")
            sheets: list[dict] = []
        else:
            if (
                entry["error_code"] is not None
                or not entry["sheets"]
                or entry["sheet_count"] != len(entry["sheets"])
            ):
                _fail("XLS_ACQUISITION_INVALID", f"{detail} READABLE invariant")
            sheets = [
                _validate_sheet(sheet, sheet_index, f"{detail}.sheets[{sheet_index - 1}]")
                for sheet_index, sheet in enumerate(entry["sheets"], start=1)
            ]

        canonical.append(
            {
                "document_id": entry["document_id"],
                "path": entry["path"],
                "source_sha256": entry["source_sha256"],
                "acquisition_status": entry["acquisition_status"],
                "error_code": entry["error_code"],
                "sheet_count": entry["sheet_count"],
                "sheets": sheets,
            }
        )
    return sorted(canonical, key=lambda item: str(item["document_id"]))


def _load_acquisition(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise G0AError("XLS_ACQUISITION_INVALID", "unable to load acquisition") from error
    if not isinstance(loaded, dict):
        _fail("XLS_ACQUISITION_INVALID", "non-object root")
    return loaded


def _run_powershell_acquisition(
    repo_root: Path,
    sources: list[dict],
    powershell_script: Path,
) -> dict:
    if not powershell_script.is_file():
        _fail("XLS_ACQUISITION_FAILED", "PowerShell backend unavailable")
    with tempfile.TemporaryDirectory(prefix="skt-workbook-inventory-") as temporary:
        temporary_path = Path(temporary)
        request_path = temporary_path / "request.json"
        output_path = temporary_path / "acquisition.json"
        requests = []
        for source in sources:
            source_path = resolve_repo_relative(repo_root, str(source["path"]))
            requests.append(
                {
                    "document_id": source["document_id"],
                    "source_path": str(source_path),
                    "expected_source_sha256": source["sha256"],
                }
            )
        write_json(request_path, requests)
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(powershell_script.resolve()),
            "-Request",
            str(request_path),
            "-Out",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                capture_output=True,
                check=False,
                timeout=1800,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise G0AError("XLS_ACQUISITION_FAILED", "PowerShell invocation failed") from error
        if completed.returncode != 0 or not output_path.is_file():
            _fail("XLS_ACQUISITION_FAILED", "PowerShell backend failed")
        return _load_acquisition(output_path)


def build_inventory(
    repo_root: Path,
    registry_path: Path,
    acquisition_json: Path | None,
    powershell_script: Path,
) -> dict:
    """Build the deterministic structural inventory through a testable acquisition seam."""
    root = repo_root.resolve()
    sources = skt_sources(load_registry(registry_path))
    raw = (
        _load_acquisition(acquisition_json)
        if acquisition_json is not None
        else _run_powershell_acquisition(root, sources, powershell_script)
    )
    return {
        "schema_version": 1,
        "tool": "skt-workbook-inventory-v1",
        "workbooks": validate_acquisition(raw, sources),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--acquisition-json", type=Path)
    parser.add_argument(
        "--powershell-script",
        type=Path,
        default=Path(__file__).with_name("acquire_skt_workbook_inventory.ps1"),
    )
    arguments = parser.parse_args(argv)
    try:
        inventory = build_inventory(
            arguments.repo_root,
            arguments.registry,
            arguments.acquisition_json,
            arguments.powershell_script,
        )
        write_json(arguments.out, inventory)
    except (G0AError, OSError) as error:
        controlled = error if isinstance(error, G0AError) else G0AError("XLS_INVENTORY_WRITE_FAILED", "output write failed")
        print(controlled, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
