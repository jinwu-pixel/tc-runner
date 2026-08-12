"""Seed the curated shell-RC provenance manifest from campaign evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mmi_converter.models import MMIRow  # noqa: E402
from src.mmi_converter.row_loader import load_mmi_rows  # noqa: E402


EVIDENCE_RAW_SHA256 = (
    "f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a"
)
DIRECTIVE_ID = "RB-20260728-shellrc-p0p1"
EVIDENCE_HEAD = "99ee58b176718805b38e3e9ed916a19beaf4a00e"
EVIDENCE_VERDICT = "PROVENANCE_MISMATCH"
WORKBOOK_RELATIVE_PATH = Path("tc_samples/TC_1.xlsx")
EXPECTED_MAPPING_COUNT = 12
EXPECTED_SELECTOR_COUNT = 14
EXPECTED_BINDING_COUNT = 15


class SeedError(ValueError):
    """Raised when the frozen evidence cannot seed the v1 manifest."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_content_hash(row: MMIRow) -> str:
    """Hash the seven loader-produced MMIRow provenance fields."""
    canonical = "\x1f".join(
        (
            row.no,
            row.feature_name,
            row.functionality,
            row.precondition,
            row.procedure,
            row.expected_result,
            row.priority,
        )
    )
    return _sha256_bytes(canonical.encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SeedError(message)


def _load_evidence(evidence_path: Path) -> dict[str, Any]:
    raw = evidence_path.read_bytes()
    _require(
        _sha256_bytes(raw) == EVIDENCE_RAW_SHA256,
        "evidence raw SHA-256 mismatch",
    )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedError("evidence is not valid UTF-8 JSON") from exc
    _require(isinstance(value, dict), "evidence root must be an object")
    return value


def _target_projection(target: dict[str, Any]) -> dict[str, Any]:
    tracked = target.get("tracked_step_projection")
    _require(isinstance(tracked, dict), "target projection is missing")
    result: dict[str, Any] = {}
    for field in ("action", "command", "expected"):
        wrapped = tracked.get(field)
        _require(isinstance(wrapped, dict), f"target {field} projection is invalid")
        _require(set(wrapped) == {"present", "value"}, f"target {field} shape differs")
        _require(isinstance(wrapped["present"], bool), f"target {field} presence is invalid")
        if wrapped["present"]:
            _require(
                isinstance(wrapped["value"], str),
                f"target {field} value must be text",
            )
            result[field] = wrapped["value"]
        else:
            _require(wrapped["value"] is None, f"absent target {field} must be null")
            result[field] = None
    _require(isinstance(result["action"], str), "target action must be present")
    _require(isinstance(result["command"], str), "target command must be present")
    return result


def _selector_row(
    rows: list[MMIRow],
    *,
    source_no: str,
    functionality_effective: str,
) -> MMIRow:
    matches = [
        row
        for row in rows
        if row.no == source_no and row.functionality == functionality_effective
    ]
    _require(
        len(matches) == 1,
        (
            "selector did not resolve uniquely: "
            f"source_no={source_no!r}, functionality={functionality_effective!r}"
        ),
    )
    return matches[0]


def build_manifest(evidence_path: Path, repo_root: Path = ROOT) -> dict[str, Any]:
    """Build an in-memory manifest from one exact campaign evidence file."""
    evidence = _load_evidence(evidence_path)
    capsule = evidence.get("entry", {}).get("dispatch_capsule", {})
    _require(capsule.get("directive_id") == DIRECTIVE_ID, "directive ID mismatch")
    repo_state = capsule.get("repo", {})
    _require(repo_state.get("head_sha") == EVIDENCE_HEAD, "evidence HEAD mismatch")
    _require(
        evidence.get("verdict", {}).get("label") == EVIDENCE_VERDICT,
        "evidence verdict mismatch",
    )

    p0 = evidence.get("p0", {})
    mappings = p0.get("mappings")
    _require(isinstance(mappings, list), "P0 mappings are missing")
    _require(len(mappings) == EXPECTED_MAPPING_COUNT, "P0 mapping count mismatch")
    _require(p0.get("reconciled") is True, "P0 is not reconciled")

    reconciliation = evidence.get("p1", {}).get("reconciliation", {})
    targets = reconciliation.get("targets")
    _require(isinstance(targets, list), "P1 targets are missing")
    _require(len(targets) == EXPECTED_BINDING_COUNT, "P1 target count mismatch")
    target_by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    for target in targets:
        _require(isinstance(target, dict), "P1 target must be an object")
        key = (
            target.get("yaml_path"),
            target.get("blocker_step_index"),
            target.get("source_no"),
        )
        _require(
            isinstance(key[0], str)
            and isinstance(key[1], int)
            and not isinstance(key[1], bool)
            and isinstance(key[2], str),
            "P1 target key is invalid",
        )
        _require(key not in target_by_key, "duplicate P1 target key")
        target_by_key[key] = target

    workbook_path = (repo_root / WORKBOOK_RELATIVE_PATH).resolve(strict=True)
    workbook_raw_sha256 = _sha256_bytes(workbook_path.read_bytes())
    _require(
        workbook_raw_sha256 == evidence.get("workbook", {}).get("raw_sha256"),
        "live workbook differs from campaign evidence",
    )

    rows_by_sheet: dict[str, list[MMIRow]] = {}
    manifest_mappings: list[dict[str, Any]] = []
    selector_count = 0
    binding_count = 0
    consumed_targets: set[tuple[str, int, str]] = set()
    for mapping in mappings:
        _require(isinstance(mapping, dict), "P0 mapping must be an object")
        yaml_path = mapping.get("yaml_path")
        yaml_tc_name = mapping.get("yaml_tc_name")
        source_sheet = mapping.get("declared_source_sheet")
        _require(isinstance(yaml_path, str) and yaml_path, "yaml_path is invalid")
        _require(
            isinstance(yaml_tc_name, str) and yaml_tc_name,
            "yaml_tc_name is invalid",
        )
        _require(source_sheet in {"SS-TC 0", "SS-TC 1"}, "source sheet is invalid")
        if source_sheet not in rows_by_sheet:
            rows_by_sheet[source_sheet] = load_mmi_rows(
                workbook_path, sheet_name=source_sheet
            )

        selectors = mapping.get("source_selectors")
        bindings = mapping.get("blocker_bindings")
        _require(isinstance(selectors, list) and selectors, "selectors are missing")
        _require(isinstance(bindings, list) and bindings, "bindings are missing")
        manifest_selectors: list[dict[str, Any]] = []
        selector_source_nos: set[str] = set()
        for selector in selectors:
            _require(isinstance(selector, dict), "selector must be an object")
            source_no = selector.get("source_no")
            functionality = selector.get("source_functionality_effective")
            physical_row = selector.get("workbook_physical_row")
            _require(
                isinstance(source_no, str) and source_no,
                "selector source_no is invalid",
            )
            _require(
                isinstance(functionality, str) and functionality,
                "selector functionality is invalid",
            )
            _require(
                isinstance(physical_row, int)
                and not isinstance(physical_row, bool)
                and physical_row > 0,
                "selector physical row is invalid",
            )
            _require(
                selector.get("workbook_sheet") == source_sheet,
                "selector sheet differs from mapping",
            )
            row = _selector_row(
                rows_by_sheet[source_sheet],
                source_no=source_no,
                functionality_effective=functionality,
            )
            _require(row.row_index == physical_row, "selector physical row drifted")
            _require(source_no not in selector_source_nos, "duplicate mapping source_no")
            selector_source_nos.add(source_no)
            manifest_selectors.append(
                {
                    "source_no": source_no,
                    "functionality_effective": functionality,
                    "workbook_physical_row": physical_row,
                    "source_content_hash": source_content_hash(row),
                }
            )
            selector_count += 1

        manifest_bindings: list[dict[str, Any]] = []
        for binding in bindings:
            _require(isinstance(binding, dict), "binding must be an object")
            blocker_step_index = binding.get("blocker_step_index")
            source_no = binding.get("source_no")
            _require(
                isinstance(blocker_step_index, int)
                and not isinstance(blocker_step_index, bool)
                and blocker_step_index > 0,
                "binding step index is invalid",
            )
            _require(source_no in selector_source_nos, "binding source_no is unknown")
            key = (yaml_path, blocker_step_index, source_no)
            _require(key in target_by_key, "binding has no P1 target")
            _require(key not in consumed_targets, "binding target was reused")
            consumed_targets.add(key)
            manifest_bindings.append(
                {
                    "blocker_step_index": blocker_step_index,
                    "source_no": source_no,
                    "step_projection": _target_projection(target_by_key[key]),
                }
            )
            binding_count += 1

        manifest_mappings.append(
            {
                "yaml_path": yaml_path,
                "yaml_tc_name": yaml_tc_name,
                "source_sheet": source_sheet,
                "source_selectors": manifest_selectors,
                "blocker_bindings": manifest_bindings,
            }
        )

    _require(selector_count == EXPECTED_SELECTOR_COUNT, "selector count mismatch")
    _require(binding_count == EXPECTED_BINDING_COUNT, "binding count mismatch")
    _require(
        consumed_targets == set(target_by_key),
        "P1 target set differs from P0 bindings",
    )
    return {
        "schema_version": 1,
        "subject": "ss_call shell-rc blocker provenance",
        "origin": {
            "directive_id": DIRECTIVE_ID,
            "evidence_raw_sha256": EVIDENCE_RAW_SHA256,
            "evidence_head": EVIDENCE_HEAD,
            "verdict": EVIDENCE_VERDICT,
        },
        "workbook": {
            "path": WORKBOOK_RELATIVE_PATH.as_posix(),
            "raw_sha256": workbook_raw_sha256,
        },
        "mappings": manifest_mappings,
    }


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Serialize the manifest deterministically as UTF-8 YAML."""
    text = yaml.safe_dump(
        manifest,
        allow_unicode=True,
        default_flow_style=False,
        line_break="\n",
        sort_keys=True,
        width=4096,
    )
    return text.encode("utf-8")


def _write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="seed the shell-RC provenance manifest from frozen evidence"
    )
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw = manifest_bytes(build_manifest(args.evidence, ROOT))
        if args.output is None:
            sys.stdout.buffer.write(raw)
        else:
            _write_new(args.output, raw)
        return 0
    except (OSError, SeedError) as exc:
        print(f"SEED_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
