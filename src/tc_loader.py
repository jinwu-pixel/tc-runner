import json
from pathlib import Path
from typing import Literal

import yaml

from src.execution_contract import normalize_tc, validate_canonical_tc


VALID_ACTIONS = {
    "tap_text", "tap_id", "tap_xy", "tap_content_desc",
    "swipe", "key", "key_sequence",
    "shell", "wait", "screenshot", "verify_text",
    "verify_shell", "verify_gone", "verify_content_desc", "verify_focus_moved",
    "input_text", "manual_pause",
}


class TCValidationError(Exception):
    pass


def load_tc(
    filepath: Path,
    contract_mode: Literal["legacy", "canonical"] = "legacy",
) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        tc = yaml.safe_load(f)

    if contract_mode == "legacy":
        # tc_name → name 정규화 (MiniFile TC 포맷 호환)
        if isinstance(tc, dict) and "name" not in tc and "tc_name" in tc:
            tc["name"] = tc["tc_name"]
        validate_tc(tc, filepath)
        return tc

    if contract_mode != "canonical":
        raise ValueError(f"unsupported contract_mode: {contract_mode!r}")
    if not isinstance(tc, dict):
        raise TCValidationError(f"{filepath}: T/C must be a YAML mapping")

    normalized = normalize_tc(tc, source=str(filepath))
    blocking = tuple(
        finding
        for finding in normalized.findings
        if finding.severity == "ERROR"
    )
    if blocking:
        detail = "; ".join(
            f"{finding.code} {finding.path}: {finding.detail}"
            for finding in blocking
        )
        raise TCValidationError(
            f"{filepath}: canonical normalization blocked: {detail}"
        )

    schema_path = Path(__file__).parent.parent / "tc_step_schema.json"
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    errors = validate_canonical_tc(normalized.value, schema)
    if errors:
        raise TCValidationError(
            f"{filepath}: canonical validation failed: {'; '.join(errors)}"
        )
    return normalized.value


def validate_tc(tc: dict, filepath: Path | None = None) -> None:
    source = str(filepath) if filepath else "unknown"

    if not isinstance(tc, dict):
        raise TCValidationError(f"{source}: T/C must be a YAML mapping")

    if "name" not in tc:
        raise TCValidationError(f"{source}: 'name' 필드가 필요합니다")

    if "steps" not in tc or not isinstance(tc.get("steps"), list):
        raise TCValidationError(f"{source}: 'steps' 필드(리스트)가 필요합니다")

    if len(tc["steps"]) == 0:
        raise TCValidationError(f"{source}: 'steps'가 비어있습니다")

    for i, step in enumerate(tc["steps"]):
        if "action" not in step:
            raise TCValidationError(f"{source}: step {i+1}에 'action' 필드가 필요합니다")
        if step["action"] not in VALID_ACTIONS:
            raise TCValidationError(
                f"{source}: step {i+1}의 action '{step['action']}'은(는) 지원하지 않습니다. "
                f"지원: {', '.join(sorted(VALID_ACTIONS))}"
            )
        if step["action"] == "manual_pause" and "description" not in step:
            raise TCValidationError(
                f"{source}: step {i+1}의 manual_pause에는 'description' 필드가 필요합니다"
            )
