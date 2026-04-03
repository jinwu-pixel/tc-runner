from pathlib import Path

import yaml


VALID_ACTIONS = {
    "tap_text", "tap_id", "tap_xy", "swipe", "key",
    "shell", "wait", "screenshot", "verify_text",
    "verify_shell", "input_text", "manual_pause",
}


class TCValidationError(Exception):
    pass


def load_tc(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        tc = yaml.safe_load(f)
    validate_tc(tc, filepath)
    return tc


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
