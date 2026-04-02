import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.adb import ADB
from src.ui_parser import find_element_by_text, find_element_by_id


@dataclass
class StepResult:
    action: str
    passed: bool
    message: str = ""
    duration: float = 0.0
    screenshot_path: Optional[Path] = None


class ActionRunner:
    def __init__(self, adb: ADB, screenshot_dir: Path, max_retries: int = 3, retry_interval: float = 1.0):
        self.adb = adb
        self.screenshot_dir = screenshot_dir
        self.max_retries = max_retries
        self.retry_interval = retry_interval

    def run_step(self, step: dict) -> StepResult:
        action = step["action"]
        start = time.time()
        try:
            passed, message = self._dispatch(action, step)
            duration = time.time() - start
            result = StepResult(action=action, passed=passed, message=message, duration=duration)
            if not passed:
                result.screenshot_path = self._capture_failure_screenshot(action)
            return result
        except Exception as e:
            duration = time.time() - start
            result = StepResult(action=action, passed=False, message=str(e), duration=duration)
            result.screenshot_path = self._capture_failure_screenshot(action)
            return result

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
        output = self.adb.shell(command)
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
