import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional

from src.adb import ADB
from src.ui_parser import find_element_by_text, find_element_by_id


@dataclass
class StepResult:
    action: str
    passed: bool
    message: str = ""
    duration: float = 0.0
    screenshot_path: Optional[Path] = None
    execution_mode: str = ""
    manual_action: str = ""
    skip_reason: str = ""
    paused: bool = False
    pause_screenshot_path: Optional[Path] = None


@dataclass(slots=True)
class ManualStepAction:
    decision: Literal["continue", "skip", "fail"]
    reason: str = ""
    evidence_path: Optional[Path] = None


@dataclass(slots=True)
class ManualStepContext:
    tc_name: str
    step_index: int
    step: dict
    execution_mode: str
    screenshot_path: Optional[Path]
    timeout_seconds: Optional[int] = None


class ActionRunner:
    def __init__(self, adb: ADB, screenshot_dir: Path, max_retries: int = 3,
                 retry_interval: float = 1.0, on_manual_step=None):
        self.adb = adb
        self.screenshot_dir = screenshot_dir
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.on_manual_step = on_manual_step

    def run_step(self, step: dict, tc_name: str = "", step_index: int = 0) -> StepResult:
        action = step["action"]
        exec_mode = step.get("execution_mode", "")
        start = time.time()

        # Manual/External pause point
        if exec_mode in ("MANUAL_REQUIRED", "EXTERNAL_EVENT") or action == "manual_pause":
            return self._handle_manual_step(step, tc_name, step_index, start)

        try:
            passed, message = self._dispatch(action, step)
            duration = time.time() - start
            result = StepResult(action=action, passed=passed, message=message,
                              duration=duration, execution_mode=exec_mode)
            if not passed:
                result.screenshot_path = self._capture_failure_screenshot(action)
            return result
        except Exception as e:
            duration = time.time() - start
            result = StepResult(action=action, passed=False, message=str(e),
                              duration=duration, execution_mode=exec_mode)
            result.screenshot_path = self._capture_failure_screenshot(action)
            return result

    def _handle_manual_step(self, step, tc_name, step_index, start):
        exec_mode = step.get("execution_mode", "MANUAL_REQUIRED")
        action = step.get("action", "manual_pause")

        pause_screenshot = self._capture_failure_screenshot("pre_manual")

        if not self.on_manual_step:
            duration = time.time() - start
            return StepResult(
                action=action, passed=False,
                message="manual handler not configured",
                duration=duration, execution_mode=exec_mode,
                manual_action="fail", paused=True,
                pause_screenshot_path=pause_screenshot,
            )

        ctx = ManualStepContext(
            tc_name=tc_name,
            step_index=step_index,
            step=step,
            execution_mode=exec_mode,
            screenshot_path=pause_screenshot,
            timeout_seconds=step.get("manual_timeout", 300),
        )

        try:
            result_action = self._invoke_handler_with_timeout(ctx)
        except Exception as e:
            duration = time.time() - start
            return StepResult(
                action=action, passed=False,
                message=f"Manual handler error: {e}",
                duration=duration, execution_mode=exec_mode,
                manual_action="fail", paused=True,
                pause_screenshot_path=pause_screenshot,
            )
        duration = time.time() - start

        if result_action.decision == "continue":
            return StepResult(
                action=action, passed=True,
                message=f"Manual step completed: {step.get('description', '')}",
                duration=duration, execution_mode=exec_mode,
                manual_action="continue", paused=True,
                pause_screenshot_path=pause_screenshot,
            )
        elif result_action.decision == "skip":
            return StepResult(
                action=action, passed=False,
                message=f"Skipped: {result_action.reason}",
                duration=duration, execution_mode=exec_mode,
                manual_action="skip", skip_reason=result_action.reason,
                paused=True, pause_screenshot_path=pause_screenshot,
            )
        else:  # fail
            fail_msg = f"Manual step failed: {result_action.reason}" if result_action.reason else "Manual step failed"
            return StepResult(
                action=action, passed=False,
                message=fail_msg,
                duration=duration, execution_mode=exec_mode,
                manual_action="fail", paused=True,
                pause_screenshot_path=pause_screenshot,
            )

    def _invoke_handler_with_timeout(self, ctx: ManualStepContext) -> ManualStepAction:
        """Handler를 timeout 제한 내에서 호출한다."""
        timeout = ctx.timeout_seconds or 300
        result_holder: list[ManualStepAction] = []
        error_holder: list[Exception] = []

        def _run():
            try:
                result_holder.append(self.on_manual_step(ctx))
            except Exception as e:
                error_holder.append(e)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Timeout — thread은 daemon이므로 프로세스 종료 시 자동 정리
            return ManualStepAction(decision="fail", reason=f"timeout ({timeout}s)")

        if error_holder:
            raise error_holder[0]

        if result_holder:
            return result_holder[0]

        return ManualStepAction(decision="fail", reason="handler returned no result")

    def _dispatch(self, action: str, step: dict) -> tuple[bool, str]:
        handlers = {
            "tap_text": self._tap_text,
            "tap_id": self._tap_id,
            "tap_xy": self._tap_xy,
            "swipe": self._swipe,
            "key": self._key,
            "shell": self._shell,
            "wait": self._wait,
            "screenshot": self._screenshot,
            "verify_text": self._verify_text,
            "verify_shell": self._verify_shell,
            "input_text": self._input_text,
            "manual_pause": lambda step: (False, "manual_pause requires handler"),
        }
        handler = handlers.get(action)
        if handler is None:
            return False, f"Unknown action: {action}"
        return handler(step)

    def _tap_text(self, step: dict) -> tuple[bool, str]:
        text = step["text"]
        for attempt in range(self.max_retries):
            xml = self.adb.dump_ui()
            element = find_element_by_text(xml, text)
            if element:
                self.adb.tap(element["x"], element["y"])
                return True, f"Tapped '{text}' at ({element['x']}, {element['y']})"
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
        return False, f"Text '{text}' not found on screen"

    def _tap_id(self, step: dict) -> tuple[bool, str]:
        resource_id = step["id"]
        for attempt in range(self.max_retries):
            xml = self.adb.dump_ui()
            element = find_element_by_id(xml, resource_id)
            if element:
                self.adb.tap(element["x"], element["y"])
                return True, f"Tapped id '{resource_id}' at ({element['x']}, {element['y']})"
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
        return False, f"Element with id '{resource_id}' not found"

    def _tap_xy(self, step: dict) -> tuple[bool, str]:
        x, y = step["x"], step["y"]
        self.adb.tap(x, y)
        return True, f"Tapped ({x}, {y})"

    def _swipe(self, step: dict) -> tuple[bool, str]:
        x1, y1, x2, y2 = step["x1"], step["y1"], step["x2"], step["y2"]
        duration = step.get("duration", 300)
        self.adb.swipe(x1, y1, x2, y2, duration)
        return True, f"Swiped ({x1},{y1}) -> ({x2},{y2})"

    def _key(self, step: dict) -> tuple[bool, str]:
        keycode = step["keycode"]
        self.adb.key(keycode)
        return True, f"Key: {keycode}"

    def _shell(self, step: dict) -> tuple[bool, str]:
        command = step["command"]
        output = self.adb.shell(command)
        return True, f"Shell: {command} -> {output.strip()[:100]}"

    def _wait(self, step: dict) -> tuple[bool, str]:
        seconds = step["seconds"]
        time.sleep(seconds)
        return True, f"Waited {seconds}s"

    def _screenshot(self, step: dict) -> tuple[bool, str]:
        name = step.get("name", f"screenshot_{int(time.time())}")
        path = self.screenshot_dir / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.adb.screenshot(path)
        return True, f"Screenshot saved: {path}"

    def _verify_text(self, step: dict) -> tuple[bool, str]:
        text = step["text"]
        for attempt in range(self.max_retries):
            xml = self.adb.dump_ui()
            element = find_element_by_text(xml, text)
            if element:
                return True, f"Text '{text}' found on screen"
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
        return False, f"Text '{text}' not found on screen"

    def _verify_shell(self, step: dict) -> tuple[bool, str]:
        command = step["command"]
        expected = step["expected"]
        timeout = step.get("timeout", 30)
        output = self.adb.shell(command, timeout=timeout)
        if expected in output:
            return True, f"'{expected}' found in output"
        return False, f"Expected '{expected}' not found in: {output.strip()[:200]}"

    def _input_text(self, step: dict) -> tuple[bool, str]:
        text = step["text"]
        self.adb.input_text(text)
        return True, f"Input: {text}"

    def _capture_failure_screenshot(self, action: str) -> Optional[Path]:
        try:
            path = self.screenshot_dir / f"fail_{action}_{int(time.time())}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self.adb.screenshot(path)
            return path
        except Exception:
            return None
