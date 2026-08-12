"""G1-G5 gates for the curated shell-RC provenance manifest."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import yaml

from src.mmi_converter.row_loader import load_mmi_rows


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "provenance" / "ss_call_shell_rc_manifest.yaml"
EXPECTED_DIRECTIVE_ID = "RB-20260728-shellrc-p0p1"
EXPECTED_EVIDENCE_SHA256 = (
    "f3e62fe3dee4c8b1213aff7827eadcf2ccdf046348229bbf810cccab30ce487a"
)
EXPECTED_EVIDENCE_HEAD = "99ee58b176718805b38e3e9ed916a19beaf4a00e"
EXPECTED_VERDICT = "PROVENANCE_MISMATCH"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OID_RE = re.compile(r"^[0-9a-f]{40}$")


def _load_manifest(path: Path = MANIFEST_PATH) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _assert_exact_keys(value: object, expected: set[str], label: str) -> dict:
    assert isinstance(value, dict), f"{label} must be a mapping"
    assert set(value) == expected, f"{label} keys differ"
    return value


def _validate_g1(manifest: dict) -> None:
    _assert_exact_keys(
        manifest,
        {"schema_version", "subject", "origin", "workbook", "mappings"},
        "manifest",
    )
    assert manifest["schema_version"] == 1
    assert manifest["subject"] == "ss_call shell-rc blocker provenance"
    mappings = manifest["mappings"]
    assert isinstance(mappings, list)
    assert len(mappings) == 12

    yaml_paths: list[str] = []
    selector_keys: list[tuple[str, str, str]] = []
    binding_keys: list[tuple[str, int, str]] = []
    for mapping_index, mapping_value in enumerate(mappings):
        mapping = _assert_exact_keys(
            mapping_value,
            {
                "yaml_path",
                "yaml_tc_name",
                "source_sheet",
                "source_selectors",
                "blocker_bindings",
            },
            f"mappings[{mapping_index}]",
        )
        assert isinstance(mapping["yaml_path"], str) and mapping["yaml_path"]
        assert isinstance(mapping["yaml_tc_name"], str) and mapping["yaml_tc_name"]
        assert mapping["source_sheet"] in {"SS-TC 0", "SS-TC 1"}
        yaml_paths.append(mapping["yaml_path"])

        source_nos: set[str] = set()
        selectors = mapping["source_selectors"]
        assert isinstance(selectors, list) and selectors
        for selector_index, selector_value in enumerate(selectors):
            selector = _assert_exact_keys(
                selector_value,
                {
                    "source_no",
                    "functionality_effective",
                    "workbook_physical_row",
                    "source_content_hash",
                },
                f"mappings[{mapping_index}].source_selectors[{selector_index}]",
            )
            assert isinstance(selector["source_no"], str) and selector["source_no"]
            assert (
                isinstance(selector["functionality_effective"], str)
                and selector["functionality_effective"]
            )
            assert (
                isinstance(selector["workbook_physical_row"], int)
                and not isinstance(selector["workbook_physical_row"], bool)
                and selector["workbook_physical_row"] > 0
            )
            assert SHA256_RE.fullmatch(selector["source_content_hash"])
            source_nos.add(selector["source_no"])
            selector_keys.append(
                (
                    mapping["source_sheet"],
                    selector["source_no"],
                    selector["functionality_effective"],
                )
            )

        bindings = mapping["blocker_bindings"]
        assert isinstance(bindings, list) and bindings
        for binding_index, binding_value in enumerate(bindings):
            binding = _assert_exact_keys(
                binding_value,
                {"blocker_step_index", "source_no", "step_projection"},
                f"mappings[{mapping_index}].blocker_bindings[{binding_index}]",
            )
            assert (
                isinstance(binding["blocker_step_index"], int)
                and not isinstance(binding["blocker_step_index"], bool)
                and binding["blocker_step_index"] > 0
            )
            assert binding["source_no"] in source_nos
            projection = _assert_exact_keys(
                binding["step_projection"],
                {"action", "command", "expected"},
                (
                    f"mappings[{mapping_index}].blocker_bindings"
                    f"[{binding_index}].step_projection"
                ),
            )
            assert isinstance(projection["action"], str) and projection["action"]
            assert isinstance(projection["command"], str) and projection["command"]
            assert projection["expected"] is None or isinstance(
                projection["expected"], str
            )
            binding_keys.append(
                (
                    mapping["yaml_path"],
                    binding["blocker_step_index"],
                    binding["source_no"],
                )
            )

    assert len(yaml_paths) == len(set(yaml_paths))
    assert len(selector_keys) == 14
    assert len(selector_keys) == len(set(selector_keys))
    assert len(binding_keys) == 15
    assert len(binding_keys) == len(set(binding_keys))


def _validate_g2(manifest: dict, workbook_path: Path | None = None) -> None:
    workbook = _assert_exact_keys(
        manifest["workbook"], {"path", "raw_sha256"}, "workbook"
    )
    assert workbook["path"] == "tc_samples/TC_1.xlsx"
    assert SHA256_RE.fullmatch(workbook["raw_sha256"])
    actual_path = workbook_path or ROOT / workbook["path"]
    assert actual_path.is_file()
    assert hashlib.sha256(actual_path.read_bytes()).hexdigest() == workbook["raw_sha256"]


def _source_content_hash(row: object) -> str:
    from scripts.gen_provenance_manifest import source_content_hash

    return source_content_hash(row)


def _validate_g3(manifest: dict, workbook_path: Path | None = None) -> None:
    workbook = manifest["workbook"]
    actual_path = workbook_path or ROOT / workbook["path"]
    rows_by_sheet: dict[str, list] = {}
    for mapping in manifest["mappings"]:
        sheet = mapping["source_sheet"]
        if sheet not in rows_by_sheet:
            rows_by_sheet[sheet] = load_mmi_rows(actual_path, sheet_name=sheet)
        for selector in mapping["source_selectors"]:
            matches = [
                row
                for row in rows_by_sheet[sheet]
                if row.no == selector["source_no"]
                and row.functionality == selector["functionality_effective"]
            ]
            assert len(matches) == 1
            row = matches[0]
            assert row.row_index == selector["workbook_physical_row"]
            assert _source_content_hash(row) == selector["source_content_hash"]


def _tracked(relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative_path],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _validate_g4(
    manifest: dict,
    curated_overrides: dict[str, Path] | None = None,
) -> None:
    overrides = curated_overrides or {}
    for mapping in manifest["mappings"]:
        relative_path = mapping["yaml_path"]
        assert _tracked(relative_path)
        yaml_path = overrides.get(relative_path, ROOT / relative_path)
        assert yaml_path.is_file()
        document = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert isinstance(document, dict)
        assert document["tc_name"] == mapping["yaml_tc_name"]
        steps = document["steps"]
        assert isinstance(steps, list)
        for binding in mapping["blocker_bindings"]:
            index = binding["blocker_step_index"]
            assert 1 <= index <= len(steps)
            step = steps[index - 1]
            assert isinstance(step, dict)
            actual_projection = {
                "action": step.get("action"),
                "command": step.get("command"),
                "expected": step.get("expected"),
            }
            assert actual_projection == binding["step_projection"]


def _validate_g5(manifest: dict) -> None:
    origin = _assert_exact_keys(
        manifest["origin"],
        {"directive_id", "evidence_raw_sha256", "evidence_head", "verdict"},
        "origin",
    )
    assert origin["directive_id"] == EXPECTED_DIRECTIVE_ID
    assert SHA256_RE.fullmatch(origin["evidence_raw_sha256"])
    assert origin["evidence_raw_sha256"] == EXPECTED_EVIDENCE_SHA256
    assert OID_RE.fullmatch(origin["evidence_head"])
    assert origin["evidence_head"] == EXPECTED_EVIDENCE_HEAD
    assert origin["verdict"] == EXPECTED_VERDICT


def test_g1_schema_cardinalities_and_unique_selectors_are_frozen():
    """Catches missing/duplicate 12/14/15 relationships or schema drift."""
    _validate_g1(_load_manifest())


def test_g2_workbook_bytes_match_manifest_pin():
    """Catches workbook replacement without provenance review."""
    _validate_g2(_load_manifest())


def test_g3_loader_rows_match_selector_hashes():
    """Catches loader-visible source-row changes, including carry semantics."""
    _validate_g3(_load_manifest())


def test_g4_curated_yaml_identity_and_blocker_steps_match():
    """Catches curated tc_name or blocker action/command/expected changes."""
    _validate_g4(_load_manifest())


def test_g5_campaign_baseline_is_pinned():
    """Catches silent replacement or reclassification of campaign evidence."""
    _validate_g5(_load_manifest())
