"""Freeze and verify the immutable LGU legacy expected ledger."""

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

import yaml

from g0a_common import G0AError, canonical_json_bytes, sha256_bytes, write_json


_LEDGER_KEYS = {"schema_version", "case_count", "expected_count", "items"}
_ITEM_KEYS = {
    "legacy_expected_id",
    "fingerprint_sha256",
    "status",
    "tc_id",
    "step_no",
    "expected_index",
    "step_source_trace",
    "expected",
}
_ID_PATTERN = re.compile(r"LGU-EXP-[0-9]{6}\Z")
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _input_error(detail: str) -> None:
    raise G0AError("LEGACY_EXPECTED_INPUT_INVALID", detail)


def _ledger_error(detail: str) -> None:
    raise G0AError("LEGACY_EXPECTED_LEDGER_INVALID", detail)


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _require_canonical_json(
    value: object,
    reject,
    path: str,
    ancestors: set[int] | None = None,
) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            reject(f"{path}: canonical JSON UTF-8 string")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        reject(f"{path}: canonical JSON non-finite number")
    if ancestors is None:
        ancestors = set()
    if isinstance(value, list):
        identity = id(value)
        if identity in ancestors:
            reject(f"{path}: canonical JSON cycle")
        ancestors.add(identity)
        try:
            for index, item in enumerate(value):
                _require_canonical_json(item, reject, f"{path}[{index}]", ancestors)
        finally:
            ancestors.remove(identity)
        return
    if isinstance(value, dict):
        identity = id(value)
        if identity in ancestors:
            reject(f"{path}: canonical JSON cycle")
        ancestors.add(identity)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    reject(f"{path}: canonical JSON mapping key")
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError:
                    reject(f"{path}: canonical JSON UTF-8 mapping key")
                _require_canonical_json(item, reject, f"{path}.{key}", ancestors)
        finally:
            ancestors.remove(identity)
        return
    reject(f"{path}: canonical JSON value type")


def _snapshot(
    tc_id: str,
    step_no: int,
    expected_index: int,
    step_source_trace: object,
    expected: object,
) -> dict[str, object]:
    return {
        "tc_id": tc_id,
        "step_no": step_no,
        "expected_index": expected_index,
        "step_source_trace": copy.deepcopy(step_source_trace),
        "expected": copy.deepcopy(expected),
    }


def _fingerprint(snapshot: dict[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(snapshot))


def _load_case(path: Path) -> dict:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise G0AError("LEGACY_EXPECTED_INPUT_INVALID", str(path)) from error
    _require_canonical_json(loaded, _input_error, path.name)
    if not isinstance(loaded, dict):
        _input_error(f"{path.name}: root")
    return loaded


def extract_expected(stage1_dir: Path) -> list[dict[str, object]]:
    """Extract sorted immutable expected snapshots from canonical STAGE1 YAML."""
    try:
        files = sorted(
            (candidate for candidate in stage1_dir.glob("*_canonical.yaml") if candidate.is_file()),
            key=lambda candidate: candidate.name,
        )
    except OSError as error:
        raise G0AError("LEGACY_EXPECTED_INPUT_INVALID", str(stage1_dir)) from error
    if not files:
        _input_error(f"{stage1_dir}: no canonical YAML")

    snapshots: list[dict[str, object]] = []
    tc_ids: set[str] = set()
    for path in files:
        case = _load_case(path)
        tc_id = case.get("tc_id")
        if not isinstance(tc_id, str) or not tc_id.strip() or tc_id in tc_ids:
            _input_error(f"{path.name}: tc_id")
        tc_ids.add(tc_id)
        steps = case.get("procedure_steps")
        if not isinstance(steps, list) or not steps:
            _input_error(f"{path.name}: procedure_steps")

        step_numbers: set[int] = set()
        for position, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                _input_error(f"{path.name}: procedure_steps[{position}]")
            step_no = step.get("step_no")
            if not _is_positive_integer(step_no) or step_no in step_numbers:
                _input_error(f"{path.name}: step_no")
            step_numbers.add(step_no)
            trace = step.get("source_trace")
            if trace is not None and not isinstance(trace, dict):
                _input_error(f"{path.name}: source_trace")
            expected_items = step.get("expected")
            if not isinstance(expected_items, list) or not expected_items:
                _input_error(f"{path.name}: expected")
            for expected_index, expected in enumerate(expected_items, start=1):
                if not isinstance(expected, dict):
                    _input_error(f"{path.name}: expected[{expected_index}]")
                snapshots.append(_snapshot(tc_id, step_no, expected_index, trace, expected))

    return sorted(
        snapshots,
        key=lambda item: (str(item["tc_id"]), int(item["step_no"]), int(item["expected_index"])),
    )


def initialize_ledger(stage1_dir: Path) -> dict:
    """Assign immutable IDs to the current sorted expected snapshots."""
    snapshots = extract_expected(stage1_dir)
    items: list[dict[str, object]] = []
    for index, snapshot in enumerate(snapshots, start=1):
        items.append(
            {
                "legacy_expected_id": f"LGU-EXP-{index:06d}",
                "fingerprint_sha256": _fingerprint(snapshot),
                "status": "ACTIVE",
                **snapshot,
            }
        )
    return {
        "schema_version": 1,
        "case_count": len({str(snapshot["tc_id"]) for snapshot in snapshots}),
        "expected_count": len(items),
        "items": items,
    }


def validate_ledger(ledger: object) -> dict:
    """Validate a ledger exactly as stored; this function never repairs it."""
    _require_canonical_json(ledger, _ledger_error, "ledger")
    if not isinstance(ledger, dict) or set(ledger) != _LEDGER_KEYS:
        _ledger_error("top-level keys")
    if ledger.get("schema_version") != 1 or isinstance(ledger["schema_version"], bool):
        _ledger_error("schema_version")
    for count_key in ("case_count", "expected_count"):
        value = ledger[count_key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _ledger_error(count_key)
    items = ledger["items"]
    if not isinstance(items, list):
        _ledger_error("items")

    locators: list[tuple[str, int, int]] = []
    seen_ids: set[str] = set()
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict) or set(item) != _ITEM_KEYS:
            _ledger_error(f"items[{position}] keys")
        identifier = item["legacy_expected_id"]
        if not isinstance(identifier, str) or not _ID_PATTERN.fullmatch(identifier):
            _ledger_error(f"items[{position}].legacy_expected_id")
        if identifier != f"LGU-EXP-{position:06d}" or identifier in seen_ids:
            _ledger_error("legacy_expected_id sequence")
        seen_ids.add(identifier)
        if item["status"] != "ACTIVE":
            _ledger_error(f"items[{position}].status")
        fingerprint = item["fingerprint_sha256"]
        if not isinstance(fingerprint, str) or not _HASH_PATTERN.fullmatch(fingerprint):
            _ledger_error(f"items[{position}].fingerprint_sha256")
        tc_id = item["tc_id"]
        if not isinstance(tc_id, str) or not tc_id.strip():
            _ledger_error(f"items[{position}].tc_id")
        step_no = item["step_no"]
        expected_index = item["expected_index"]
        if not _is_positive_integer(step_no) or not _is_positive_integer(expected_index):
            _ledger_error(f"items[{position}] locator")
        trace = item["step_source_trace"]
        if trace is not None and not isinstance(trace, dict):
            _ledger_error(f"items[{position}].step_source_trace")
        expected = item["expected"]
        if not isinstance(expected, dict):
            _ledger_error(f"items[{position}].expected")
        snapshot = _snapshot(tc_id, step_no, expected_index, trace, expected)
        if _fingerprint(snapshot) != fingerprint:
            _ledger_error(f"items[{position}].fingerprint_sha256")
        locator = (tc_id, step_no, expected_index)
        if locator in locators:
            _ledger_error("duplicate locator")
        locators.append(locator)

    if locators != sorted(locators):
        _ledger_error("locator order")
    if ledger["case_count"] != len({locator[0] for locator in locators}):
        _ledger_error("case_count")
    if ledger["expected_count"] != len(items):
        _ledger_error("expected_count")
    return ledger


def check_ledger(stage1_dir: Path, ledger: dict) -> None:
    """Reject every set or content drift against a validated stored ledger."""
    validated = validate_ledger(ledger)
    current = extract_expected(stage1_dir)
    stored_locators = [
        (item["tc_id"], item["step_no"], item["expected_index"])
        for item in validated["items"]
    ]
    current_locators = [
        (item["tc_id"], item["step_no"], item["expected_index"])
        for item in current
    ]
    if stored_locators != current_locators:
        raise G0AError("LEGACY_EXPECTED_SET_DRIFT", "locator set differs")
    for stored, snapshot in zip(validated["items"], current, strict=True):
        if stored["fingerprint_sha256"] != _fingerprint(snapshot):
            locator = (snapshot["tc_id"], snapshot["step_no"], snapshot["expected_index"])
            raise G0AError("LEGACY_EXPECTED_DRIFT", str(locator))


def _load_ledger(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise G0AError("LEGACY_EXPECTED_LEDGER_INVALID", str(path)) from error
    return validate_ledger(loaded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    init_parser = subcommands.add_parser("init")
    init_parser.add_argument("--stage1", type=Path, required=True)
    init_parser.add_argument("--out", type=Path, required=True)
    check_parser = subcommands.add_parser("check")
    check_parser.add_argument("--stage1", type=Path, required=True)
    check_parser.add_argument("--ledger", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "init":
            ledger = initialize_ledger(arguments.stage1)
            write_json(arguments.out, ledger)
        else:
            ledger = _load_ledger(arguments.ledger)
            check_ledger(arguments.stage1, ledger)
        print(f"cases={ledger['case_count']} expected={ledger['expected_count']} drift=0")
    except (G0AError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
