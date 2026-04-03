import subprocess
from pathlib import Path
from typing import List


class ADB:
    """ADB 명령을 실행하는 래퍼 클래스."""

    def __init__(self, device_serial: str | None = None):
        self._base_cmd = ["adb"]
        if device_serial:
            self._base_cmd += ["-s", device_serial]

    def shell(self, command: str, timeout: int = 10) -> str:
        """ADB shell 명령을 실행하고 stdout을 반환한다."""
        try:
            result = subprocess.run(
                self._base_cmd + ["shell", command],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB shell timeout ({timeout}s): {command}")

    def tap(self, x: int, y: int) -> None:
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")

    def key(self, keycode: str) -> None:
        self.shell(f"input keyevent {keycode}")

    def input_text(self, text: str) -> None:
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        self.shell(f"input text '{escaped}'")

    def screenshot(self, local_path: Path) -> None:
        remote = "/sdcard/screenshot_tmp.png"
        self.shell(f"screencap -p {remote}")
        try:
            subprocess.run(
                self._base_cmd + ["pull", remote, str(local_path)],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError("ADB pull screenshot timeout")
        finally:
            self.shell(f"rm -f {remote}")

    def dump_ui(self) -> str:
        remote = "/sdcard/ui_dump.xml"
        self.shell(f"uiautomator dump {remote}")
        try:
            result = subprocess.run(
                self._base_cmd + ["shell", "cat", remote],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError("ADB dump_ui timeout")
        finally:
            self.shell(f"rm -f {remote}")

    def get_device_info(self) -> dict:
        model = self.shell("getprop ro.product.model").strip()
        version = self.shell("getprop ro.build.version.release").strip()
        return {"model": model, "android_version": version}

    def is_connected(self) -> bool:
        try:
            result = subprocess.run(
                self._base_cmd + ["devices"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            lines = result.stdout.strip().split("\n")
            return len(lines) > 1 and "device" in lines[1]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
