from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import yaml

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
    ).hexdigest()[:4]
    return f"{safe}_{content_hash}.yaml"


class YAMLExporter:
    def __init__(self, output_dir: Path, overwrite: bool = False):
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
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

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return path
