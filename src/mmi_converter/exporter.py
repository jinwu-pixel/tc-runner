from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml

from src.execution_contract import (
    CANONICAL_TC_CLASSES,
    derive_execution_metadata,
    normalize_step,
    validate_canonical_tc,
)

from .models import ConversionPreview


def check_runnable(preview: ConversionPreview) -> tuple[bool, list[str]]:
    issues = []
    if not preview.compiled_steps:
        issues.append("compiled steps가 비어 있음")
    for i, step in enumerate(preview.compiled_steps):
        if step.get("compile_status") == "UNRESOLVED_PARAMS":
            issues.append(f"Step {i+1}: unresolved params {step.get('_unresolved_params')}")
        if step.get("action") == "shell" and "{" in step.get("command", ""):
            issues.append(f"Step {i+1}: placeholder in command")
        if step.get("action") == "manual_pause" and not step.get("description"):
            issues.append(f"Step {i+1}: manual_pause missing description")
    for w in preview.warnings:
        if "shell_mapping_missing" in w:
            issues.append(f"치명 warning: {w}")
    return len(issues) == 0, issues


def _make_filename(tc_name: str, procedure: str, expected: str) -> str:
    safe = re.sub(r"[^\w가-힣\s-]", "", tc_name)
    safe = re.sub(r"\s+", "_", safe.strip())[:80]
    content_hash = hashlib.sha256(
        f"{tc_name}{procedure}{expected}".encode()
    ).hexdigest()[:8]
    return f"{safe}_{content_hash}.yaml"


class YAMLExporter:
    def __init__(
        self,
        output_dir: Path,
        overwrite: bool = False,
        *,
        contract_mode: Literal["legacy", "canonical"] = "legacy",
    ):
        if contract_mode not in ("legacy", "canonical"):
            raise ValueError(f"unsupported contract_mode: {contract_mode!r}")
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.contract_mode = contract_mode
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_one(
        self,
        preview: ConversionPreview,
        source_file: str,
        source_sheet: str,
        source_row: int,
    ) -> Path | None:
        filename = _make_filename(
            preview.tc_name, preview.source_procedure, preview.source_expected,
        )
        path = self.output_dir / filename

        if path.exists() and not self.overwrite:
            return None

        if self.contract_mode == "legacy":
            runnable, _ = check_runnable(preview)
            doc = {
                "name": preview.tc_name,
                "description": preview.source_procedure[:200],
                "metadata": {
                    "source_file": source_file,
                    "source_sheet": source_sheet,
                    "source_row": source_row,
                    "automation_class": preview.automation_class,
                    "runnable": runnable,
                    "has_manual_steps": any(
                        s.get("action") == "manual_pause" for s in preview.compiled_steps
                    ),
                    "has_shell_actions": any(
                        s.get("action") == "shell" for s in preview.compiled_steps
                    ),
                    "has_unresolved_params": any(
                        s.get("compile_status") == "UNRESOLVED_PARAMS"
                        for s in preview.compiled_steps
                    ),
                    "warnings": preview.warnings[:20],
                    "exported_at": datetime.now().isoformat(timespec="seconds"),
                },
                "steps": preview.compiled_steps,
            }
        else:
            doc = self._canonical_document(
                preview,
                source_file=source_file,
                source_sheet=source_sheet,
                source_row=source_row,
            )

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return path

    @staticmethod
    def _canonical_steps(steps: list[dict]) -> list[dict]:
        canonical: list[dict] = []
        for index, step in enumerate(steps):
            result = normalize_step(step, path=f"mmi_export.steps[{index}]")
            if result.blocking:
                codes = ", ".join(
                    finding.code
                    for finding in result.findings
                    if finding.severity == "ERROR"
                )
                raise ValueError(f"canonical MMI export blocked: {codes}")
            canonical.append(result.value)
        return canonical

    def _canonical_document(
        self,
        preview: ConversionPreview,
        *,
        source_file: str,
        source_sheet: str,
        source_row: int,
    ) -> dict:
        if preview.automation_class not in CANONICAL_TC_CLASSES:
            raise ValueError(
                "canonical MMI export requires tc_class in "
                f"{sorted(CANONICAL_TC_CLASSES)}; got {preview.automation_class!r}"
            )

        steps = self._canonical_steps(preview.compiled_steps)
        runnable, _ = check_runnable(preview)
        derived = derive_execution_metadata(steps)
        warnings = list(preview.warnings[:20])
        if derived["manual_detail"] == "UNKNOWN":
            warnings.append("manual_detail_unknown: Step 4 token 추정 불가")

        has_unresolved = any(
            step.get("compile_status") == "UNRESOLVED_PARAMS"
            or (
                step.get("action") == "shell"
                and "{" in str(step.get("command", ""))
            )
            for step in steps
        ) or any("shell_mapping_missing" in warning for warning in preview.warnings)
        runnable_reason: list[str] = []
        if has_unresolved:
            runnable_reason.append("UNRESOLVED_PARAMS")
        if not steps:
            runnable_reason.append("MANUAL_FALLBACK")
        if any(
            step.get("action") == "manual_pause" and not step.get("description")
            for step in steps
        ):
            runnable_reason.append("MANUAL_FALLBACK")

        metadata = {
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row": source_row,
            "tc_class": preview.automation_class,
            "runnable": runnable,
            "has_shell_actions": any(
                step.get("action") == "shell" for step in steps
            ),
            "has_unresolved_params": has_unresolved,
            "warnings": warnings,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            **derived,
        }
        if runnable_reason:
            metadata["runnable_reason"] = runnable_reason

        document = {
            "tc_name": preview.tc_name,
            "description": preview.source_procedure[:200],
            "metadata": metadata,
            "steps": steps,
        }
        schema_path = Path(__file__).parents[2] / "tc_step_schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validation_errors = validate_canonical_tc(document, schema)
        if runnable and validation_errors:
            raise ValueError(
                "canonical MMI validation failed: "
                + "; ".join(validation_errors)
            )
        if not runnable:
            warnings.extend(
                f"canonical_validation_error: {error}"
                for error in validation_errors
            )
        return document
