from __future__ import annotations

from .models import Intent, TCIR, ClassifiedIntent
from .shell_action_map import ShellActionMap, APP_ALIAS_REGISTRY, PERMISSION_ALIAS_REGISTRY


class TCRunnerCompiler:
    def __init__(self, shell_action_map=None):
        self._shell_map = shell_action_map or ShellActionMap()

    def compile(self, ir: TCIR, automation_class: str = "FULL_AUTO") -> dict:
        steps: list[dict] = []
        warnings = list(ir.warnings)

        for intent in ir.intents:
            compiled = self._compile_intent(intent, warnings)
            if compiled:
                steps.extend(compiled)

        for intent in ir.expected_intents:
            compiled = self._compile_intent(intent, warnings, expected_phase=True)
            if compiled:
                steps.extend(compiled)

        return {
            "name": ir.tc_name,
            "description": ir.description,
            "preconditions": ir.preconditions,
            "metadata": {
                "automation_class": automation_class,
                "source_sheet": ir.source_row.sheet_name if ir.source_row else "",
                "source_row": ir.source_row.row_index if ir.source_row else -1,
                "warnings": warnings,
            },
            "steps": steps,
        }

    def _compile_intent(
        self,
        intent: Intent,
        warnings: list[str],
        expected_phase: bool = False,
    ) -> list[dict]:
        if intent.type == "navigate":
            if not intent.target:
                warnings.append("navigate intent에 target이 없음")
                return []
            return [{"action": "tap_text", "text": intent.target}]

        if intent.type == "press_key":
            if not intent.value:
                warnings.append("press_key intent에 value가 없음")
                return []
            return [{"action": "key", "keycode": intent.value}]

        if intent.type == "wait":
            seconds = intent.value or "2"
            return [{"action": "wait", "seconds": int(seconds)}]

        if intent.type == "verify_text":
            if not intent.target:
                warnings.append("verify_text intent에 target이 없음")
                return []
            return [{"action": "verify_text", "text": intent.target}]

        if intent.type == "input_text":
            text_value = intent.extra.get("text") if intent.extra else None
            if text_value:
                return [{"action": "input_text", "text": text_value}]
            warnings.append(f"입력 대상 '{intent.target or ''}' 에 실제 입력값이 없어 수동 보완 필요")
            return []

        if intent.type == "toggle":
            if intent.target:
                warnings.append(
                    f"토글 intent('{intent.target}', value={intent.value})는 현재 직접 실행 rule 미구현. "
                    "메뉴 진입 및 후속 검증 위주로 처리 필요"
                )
            else:
                warnings.append("toggle intent target 추정 실패")
            return []

        if intent.type == "verify_shell":
            command = intent.extra.get("command")
            expected = intent.extra.get("expected")
            if command and expected:
                return [{"action": "verify_shell", "command": command, "expected": expected}]
            warnings.append("verify_shell intent에 command/expected 누락")
            return []

        if intent.type == "manual_required":
            warnings.append(intent.target or "수동 개입 필요")
            return []

        warnings.append(f"미지원 intent type: {intent.type}")
        return []

    def compile_classified(self, ci: ClassifiedIntent) -> tuple[list[dict], list[str]]:
        """ClassifiedIntent → (steps, warnings)."""
        warnings: list[str] = []
        intent = ci.intent

        if ci.execution_mode in ("MANUAL_REQUIRED", "EXTERNAL_EVENT"):
            step = {
                "action": "manual_pause",
                "execution_mode": ci.execution_mode,
                "step_role": ci.step_role,
                "description": intent.target or "",
            }
            return [step], warnings

        if ci.execution_mode == "SHELL_AUTO":
            action = self._shell_map.resolve(intent)
            if action:
                params = self._extract_shell_params(intent, action)
                unresolved = [p for p in action.required_params if p not in params]
                if unresolved:
                    step = {
                        "action": "shell",
                        "command": action.command_template,
                        "execution_mode": "SHELL_AUTO",
                        "compile_status": "UNRESOLVED_PARAMS",
                        "runnable": False,
                        "_unresolved_params": unresolved,
                    }
                    warnings.append(f"unresolved_params: {unresolved} for {action.key}")
                    return [step], warnings
                cmd = self._shell_map.render_command(action, params)
                return [{"action": "shell", "command": cmd, "execution_mode": "SHELL_AUTO"}], warnings
            warnings.append(f"shell_resolve_failed: {intent.target}")

        # Default: use existing intent compilation
        compiled = self._compile_intent(intent, warnings)
        return compiled, warnings

    def _extract_shell_params(self, intent: Intent, action) -> dict:
        params = {}
        text = intent.target or ""
        if "package" in action.required_params:
            for name, pkg in APP_ALIAS_REGISTRY.items():
                if name in text:
                    params["package"] = pkg
                    break
        if "permission" in action.required_params:
            for name, perm in PERMISSION_ALIAS_REGISTRY.items():
                if name in text:
                    params["permission"] = perm
                    break
        if "settings_action" in action.required_params:
            params["settings_action"] = self._shell_map.resolve_settings_alias(text)
        return params
