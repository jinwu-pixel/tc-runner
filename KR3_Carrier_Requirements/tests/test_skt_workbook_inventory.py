import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from build_skt_workbook_inventory import (
    build_inventory,
    load_registry,
    skt_sources,
    validate_acquisition,
)
from g0a_common import G0AError, write_json


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
BUILD_SCRIPT = TOOLS_DIR / "build_skt_workbook_inventory.py"
POWERSHELL_SCRIPT = TOOLS_DIR / "acquire_skt_workbook_inventory.ps1"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "skt_workbook_inventory_schema_v1.json"
)


def source_document(index: int) -> dict:
    return {
        "document_id": f"SKT_PROC_{index:04d}",
        "carrier": "SKT",
        "role": "PROCEDURE",
        "media_type": "application/vnd.ms-excel",
        "path": f"sources/skt/source_{index:04d}.xls",
        "size_bytes": index,
        "sha256": f"{index:064x}",
        "intake": {
            "container_status": "READABLE",
            "semantic_parse_status": "NOT_ATTEMPTED",
            "semantic_parser": None,
        },
    }


def registry(document_count: int = 66) -> dict:
    return {
        "schema_version": 1,
        "documents": [source_document(index) for index in range(1, document_count + 1)],
    }


def sheet(index: int = 1) -> dict:
    return {
        "sheet_index": index,
        "sheet_name": f"Sheet {index}",
        "visibility": "VISIBLE",
        "used_range": {
            "first_row": 1,
            "last_row": 10,
            "first_column": 1,
            "last_column": 4,
        },
    }


def disposition(document: dict) -> dict:
    return {
        "document_id": document["document_id"],
        "path": document["path"],
        "source_sha256": document["sha256"],
        "acquisition_status": "READABLE",
        "error_code": None,
        "sheet_count": 1,
        "sheets": [sheet()],
    }


def acquisition(registry_value: dict) -> dict:
    return {
        "workbooks": [
            disposition(document) for document in reversed(registry_value["documents"])
        ]
    }


def write_json_fixture(path: Path, value: object) -> Path:
    write_json(path, value)
    return path


def error_code(callable_) -> str:
    with pytest.raises(G0AError) as caught:
        callable_()
    return caught.value.code


def test_valid_acquisition_returns_sorted_canonical_inventory_and_registry_identity(tmp_path):
    registry_value = registry()
    acquisition_value = acquisition(registry_value)
    registry_path = write_json_fixture(tmp_path / "registry.json", registry_value)
    acquisition_path = write_json_fixture(tmp_path / "acquisition.json", acquisition_value)

    result = build_inventory(
        tmp_path,
        registry_path,
        acquisition_path,
        POWERSHELL_SCRIPT,
    )

    assert set(result) == {"schema_version", "tool", "workbooks"}
    assert result["schema_version"] == 1
    assert result["tool"] == "skt-workbook-inventory-v1"
    assert [item["document_id"] for item in result["workbooks"]] == [
        f"SKT_PROC_{index:04d}" for index in range(1, 67)
    ]
    assert result["workbooks"][0] == disposition(registry_value["documents"][0])
    assert result["workbooks"][-1]["path"] == registry_value["documents"][-1]["path"]
    assert result["workbooks"][-1]["source_sha256"] == registry_value["documents"][-1]["sha256"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_acquisition_rejects_missing_extra_and_duplicate_disposition_ids(mutation):
    registry_value = registry()
    raw = acquisition(registry_value)
    if mutation == "missing":
        raw["workbooks"].pop()
    elif mutation == "extra":
        extra = copy.deepcopy(raw["workbooks"][0])
        extra.update(
            {
                "document_id": "SKT_PROC_9999",
                "path": "sources/skt/extra.xls",
                "source_sha256": "f" * 64,
            }
        )
        raw["workbooks"].append(extra)
    else:
        raw["workbooks"][-1] = copy.deepcopy(raw["workbooks"][0])

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_SOURCE_SET_MISMATCH"
    )


@pytest.mark.parametrize("field", ["path", "source_sha256"])
def test_acquisition_rejects_registry_path_or_hash_mismatch(field):
    registry_value = registry()
    raw = acquisition(registry_value)
    raw["workbooks"][0][field] = "wrong.xls" if field == "path" else "f" * 64

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_IDENTITY_MISMATCH"
    )


def test_readable_disposition_rejects_sheet_count_mismatch():
    registry_value = registry()
    raw = acquisition(registry_value)
    raw["workbooks"][0]["sheet_count"] = 2

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_INVALID"
    )


def test_readable_disposition_requires_at_least_one_sheet():
    registry_value = registry()
    raw = acquisition(registry_value)
    raw["workbooks"][0]["sheet_count"] = 0
    raw["workbooks"][0]["sheets"] = []

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_INVALID"
    )


def test_runtime_accepts_finite_integral_json_numbers_for_integer_fields():
    registry_value = registry()
    raw = acquisition(registry_value)
    workbook = raw["workbooks"][0]
    workbook["sheet_count"] = 1.0
    workbook["sheets"][0]["sheet_index"] = 1.0
    workbook["sheets"][0]["used_range"] = {
        "first_row": 1.0,
        "last_row": 10.0,
        "first_column": 1.0,
        "last_column": 4.0,
    }

    canonical = validate_acquisition(raw, skt_sources(registry_value))

    assert canonical[0]["sheet_count"] == 1.0
    assert canonical[0]["sheets"][0]["used_range"]["last_row"] == 10.0


@pytest.mark.parametrize("invalid", [True, False, float("nan"), float("inf"), -float("inf"), 1.5])
def test_runtime_rejects_bool_nonfinite_and_nonintegral_integer_fields(invalid):
    registry_value = registry()
    raw = acquisition(registry_value)
    raw["workbooks"][0]["sheet_count"] = invalid

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_INVALID"
    )


@pytest.mark.parametrize("with_sheets,null_error", [(True, False), (False, True)])
def test_failed_disposition_rejects_sheets_or_null_error(with_sheets, null_error):
    registry_value = registry()
    raw = acquisition(registry_value)
    failed = raw["workbooks"][0]
    failed["acquisition_status"] = "FAILED"
    failed["error_code"] = None if null_error else "EXCEL_COM_80004005"
    failed["sheet_count"] = 1 if with_sheets else 0
    failed["sheets"] = [sheet()] if with_sheets else []

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_INVALID"
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda sheets: sheets[0].update(sheet_index=0),
        lambda sheets: sheets.__setitem__(slice(None), [sheet(2), sheet(1)]),
        lambda sheets: sheets[0].update(visibility="COLLAPSED"),
        lambda sheets: sheets[0]["used_range"].update(first_row=0),
        lambda sheets: sheets[0]["used_range"].update(first_row=11, last_row=10),
    ],
    ids=["zero-index", "out-of-order", "visibility", "zero-range", "reversed-range"],
)
def test_acquisition_rejects_invalid_sheet_index_order_visibility_or_range(mutate):
    registry_value = registry()
    raw = acquisition(registry_value)
    workbook = raw["workbooks"][0]
    mutate(workbook["sheets"])
    workbook["sheet_count"] = len(workbook["sheets"])

    assert error_code(lambda: validate_acquisition(raw, skt_sources(registry_value))) == (
        "XLS_ACQUISITION_INVALID"
    )


def test_skt_sources_requires_exactly_66_registry_documents():
    assert error_code(lambda: skt_sources(registry(65))) == "SKT_SOURCE_COUNT_MISMATCH"


def test_registry_loader_rejects_missing_non_object_and_malformed_roots(tmp_path):
    missing = tmp_path / "missing.json"
    scalar = tmp_path / "scalar.json"
    malformed = tmp_path / "malformed.json"
    scalar.write_text("[]", encoding="utf-8")
    malformed.write_text("{", encoding="utf-8")

    assert error_code(lambda: load_registry(missing)) == "SOURCE_REGISTRY_INVALID"
    assert error_code(lambda: load_registry(scalar)) == "SOURCE_REGISTRY_INVALID"
    assert error_code(lambda: load_registry(malformed)) == "SOURCE_REGISTRY_INVALID"


def test_output_rejects_backend_source_path_and_arbitrary_fields():
    registry_value = registry()
    sources = skt_sources(registry_value)
    for field, value in [
        ("source_path", r"C:\private\source.xls"),
        ("backend_note", "not part of the contract"),
    ]:
        raw = acquisition(registry_value)
        raw["workbooks"][0][field] = value

        assert error_code(lambda raw=raw: validate_acquisition(raw, sources)) == (
            "XLS_ACQUISITION_INVALID"
        )


def test_cli_with_acquisition_json_writes_inventory_and_malformed_input_is_controlled(tmp_path):
    registry_path = write_json_fixture(tmp_path / "registry.json", registry())
    acquisition_path = write_json_fixture(
        tmp_path / "acquisition.json", acquisition(registry())
    )
    output_path = tmp_path / "inventory.json"
    valid = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--registry",
            str(registry_path),
            "--out",
            str(output_path),
            "--acquisition-json",
            str(acquisition_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert valid.returncode == 0
    assert json.loads(output_path.read_text(encoding="utf-8"))["tool"] == (
        "skt-workbook-inventory-v1"
    )

    acquisition_path.write_text("{", encoding="utf-8")
    invalid = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--registry",
            str(registry_path),
            "--out",
            str(output_path),
            "--acquisition-json",
            str(acquisition_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert invalid.returncode == 2
    assert invalid.stderr.startswith("XLS_ACQUISITION_INVALID:")
    assert "Traceback" not in invalid.stderr


def test_inventory_schema_is_closed_draft_2020_12_with_full_sha_and_minima():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    workbook = schema["properties"]["workbooks"]["items"]
    sheet_schema = workbook["properties"]["sheets"]["items"]
    used_range = sheet_schema["properties"]["used_range"]

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert workbook["additionalProperties"] is False
    assert sheet_schema["additionalProperties"] is False
    assert used_range["additionalProperties"] is False
    assert workbook["properties"]["source_sha256"]["pattern"] == (
        r"^[0-9a-f]{64}(?![\s\S])"
    )
    assert workbook["properties"]["sheet_count"]["minimum"] == 0
    assert sheet_schema["properties"]["sheet_index"]["minimum"] == 1
    assert all(
        used_range["properties"][field]["minimum"] == 1
        for field in ("first_row", "last_row", "first_column", "last_column")
    )


def test_powershell_backend_has_read_only_com_guards_and_no_cell_or_save_access():
    source = POWERSHELL_SCRIPT.read_text(encoding="utf-8")

    assert re.search(r"AutomationSecurity\s*=\s*3\b", source)
    assert re.search(
        r"Workbooks\.Open\([^\r\n]*,\s*0\s*,\s*\$true\b",
        source,
        re.IGNORECASE,
    )
    assert re.search(r"\.Close\(\s*\$false\s*\)", source)
    assert re.search(r"DisplayAlerts\s*=\s*\$false\b", source)
    assert re.search(r"AskToUpdateLinks\s*=\s*\$false\b", source)
    assert re.search(r"EnableEvents\s*=\s*\$false\b", source)
    assert not re.search(r"\.(?:Value2?|Formula|Save|SaveAs)\b", source, re.IGNORECASE)


def test_powershell_backend_hashes_and_opens_per_workbook_snapshot_only():
    source = POWERSHELL_SCRIPT.read_text(encoding="utf-8")

    assert re.search(r"\$snapshotRoot\s*=\s*Join-Path", source)
    assert re.search(
        r"Copy-Item -LiteralPath \$sourcePath -Destination \$snapshotPath",
        source,
    )
    assert re.search(
        r"Get-FileHash -LiteralPath \$snapshotPath -Algorithm SHA256",
        source,
    )
    assert re.search(r"\$workbooks\.Open\(\$snapshotPath,\s*0,\s*\$true", source)
    assert not re.search(r"\$workbooks\.Open\(\$sourcePath", source)
    assert re.search(r"Remove-Item -LiteralPath \$snapshotPath -Force", source)
    assert re.search(r"Remove-Item -LiteralPath \$snapshotRoot -Recurse -Force", source)

    copy_index = source.index("Copy-Item -LiteralPath $sourcePath -Destination $snapshotPath")
    snapshot_hash_index = source.index(
        "Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256"
    )
    open_index = source.index("$workbooks.Open($snapshotPath")
    assert copy_index < snapshot_hash_index < open_index


def test_powershell_backend_releases_used_range_child_collections_before_parents():
    source = POWERSHELL_SCRIPT.read_text(encoding="utf-8")

    assert "$usedRows = $usedRange.Rows" in source
    assert "$usedColumns = $usedRange.Columns" in source
    assert "$usedRange.Rows.Count" not in source
    assert "$usedRange.Columns.Count" not in source
    release_order = [
        source.index("Release-ComObject -Object $usedRows"),
        source.index("Release-ComObject -Object $usedColumns"),
        source.index("Release-ComObject -Object $usedRange"),
        source.index("Release-ComObject -Object $worksheet"),
    ]
    assert release_order == sorted(release_order)


def test_powershell_backend_cleanup_releases_parents_even_when_close_or_quit_throws():
    source = re.sub(
        r"\s+",
        " ",
        POWERSHELL_SCRIPT.read_text(encoding="utf-8"),
    )

    workbook_cleanup = re.compile(
        r"finally \{ try \{ if \(\$null -ne \$workbook\) \{ "
        r"\$workbook\.Close\(\$false\) \} \} catch \{ \} finally \{ "
        r"Release-ComObject -Object \$worksheets "
        r"Release-ComObject -Object \$workbook "
        r".*?"
        r"\[GC\]::Collect\(\) \[GC\]::WaitForPendingFinalizers\(\) \} \}"
    )
    excel_cleanup = re.compile(
        r"finally \{ try \{ if \(\$null -ne \$excel\) \{ "
        r"\$excel\.Quit\(\) \} \} catch \{ \} finally \{ "
        r"Release-ComObject -Object \$workbooks "
        r"Release-ComObject -Object \$excel "
        r".*?"
        r"\[GC\]::Collect\(\) \[GC\]::WaitForPendingFinalizers\(\) \} \}"
    )

    assert workbook_cleanup.search(source)
    assert excel_cleanup.search(source)


def test_powershell_backend_enumerates_root_json_array_before_excel_startup(tmp_path):
    source = POWERSHELL_SCRIPT.read_text(encoding="utf-8")
    decode_sequence = re.compile(
        r"\$decoded\s*=\s*Get-Content -LiteralPath \$Request -Raw -Encoding UTF8 "
        r"\| ConvertFrom-Json\s+\$requestItems\s*=\s*@\(\$decoded\)"
    )
    assert decode_sequence.search(source)
    assert "$requestItems = @(Get-Content" not in source

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            [
                {"document_id": "SKT_PROC_0001", "source_path": "first.xls"},
                {"document_id": "SKT_PROC_0002", "source_path": "second.xls"},
            ]
        ),
        encoding="utf-8",
    )
    probe_path = tmp_path / "decode_probe.ps1"
    probe_path.write_text(
        "param([string]$Request)\n"
        "$decoded = Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json\n"
        "$requestItems = @($decoded)\n"
        "[ordered]@{ count = $requestItems.Count; ids = @($requestItems.document_id); "
        "paths = @($requestItems.source_path) } | ConvertTo-Json -Compress\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(probe_path),
            "-Request",
            str(request_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == {
        "count": 2,
        "ids": ["SKT_PROC_0001", "SKT_PROC_0002"],
        "paths": ["first.xls", "second.xls"],
    }
