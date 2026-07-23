import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class ShellResult:
    command: str
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class ADBCommandError(RuntimeError):
    """ADB command completed with a nonzero return code in strict mode."""


def validate_device_serial(device_serial: str | None) -> None:
    if device_serial is None:
        return
    if (
        not isinstance(device_serial, str)
        or not device_serial
        or any(char.isspace() for char in device_serial)
    ):
        raise ValueError(
            "device_serial must be a non-empty value without whitespace"
        )


class ADB:
    """ADB 명령을 실행하는 래퍼 클래스."""

    def __init__(
        self,
        device_serial: str | None = None,
        *,
        strict_shell: bool = False,
    ):
        validate_device_serial(device_serial)
        self._device_serial = device_serial
        self._strict_shell = bool(strict_shell)
        self._base_cmd = ["adb"]
        if device_serial is not None:
            self._base_cmd += ["-s", device_serial]

    @staticmethod
    def _command_error(operation: str, result) -> ADBCommandError:
        stdout = (result.stdout or "")[:200]
        stderr = (result.stderr or "")[:200]
        return ADBCommandError(
            f"ADB {operation} failed (rc={result.returncode}); "
            f"stdout={stdout!r}; stderr={stderr!r}"
        )

    def _run_direct(
        self,
        command: list[str],
        *,
        operation: str,
        timeout: int,
        timeout_message: str,
    ):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(timeout_message)
        if self._strict_shell and result.returncode != 0:
            raise self._command_error(operation, result)
        return result

    def shell(self, command: str, timeout: int = 10) -> str:
        """ADB shell 명령을 실행하고 stdout을 반환한다."""
        try:
            result = subprocess.run(
                self._base_cmd + ["shell", command],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
            if self._strict_shell and result.returncode != 0:
                raise self._command_error(f"shell {command!r}", result)
            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB shell timeout ({timeout}s): {command}")

    def shell_result(
        self,
        command: str,
        *,
        timeout_s: float = 10.0,
    ) -> ShellResult:
        """ADB shell 명령의 stdout, stderr, 종료 코드를 함께 반환한다."""
        try:
            result = subprocess.run(
                self._base_cmd + ["shell", command],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                encoding="utf-8",
                errors="replace",
            )
            return ShellResult(
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"ADB shell timeout ({timeout_s}s): {command}"
            )

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
        remote = "/data/local/tmp/tc_runner_screenshot_tmp.png"
        primary_error = None
        try:
            self.shell(f"screencap -p {remote}")
            self._run_direct(
                self._base_cmd + ["pull", remote, str(local_path)],
                operation="pull screenshot",
                timeout=10,
                timeout_message="ADB pull screenshot timeout",
            )
        except Exception as exc:
            primary_error = exc
            raise
        finally:
            try:
                self.shell(f"rm -f {remote}")
            except Exception:
                if primary_error is None:
                    raise

    def dump_ui(self) -> str:
        remote = "/data/local/tmp/tc_runner_ui_dump.xml"
        primary_error = None
        try:
            self.shell(f"uiautomator dump {remote}")
            result = self._run_direct(
                self._base_cmd + ["shell", "cat", remote],
                operation="cat UI dump",
                timeout=10,
                timeout_message="ADB dump_ui timeout",
            )
            return result.stdout
        except Exception as exc:
            primary_error = exc
            raise
        finally:
            try:
                self.shell(f"rm -f {remote}")
            except Exception:
                if primary_error is None:
                    raise

    def get_device_info(self) -> dict:
        model = self.shell("getprop ro.product.model").strip()
        version = self.shell("getprop ro.build.version.release").strip()
        return {"model": model, "android_version": version}

    def device_serial(self) -> str | None:
        try:
            result = subprocess.run(
                self._base_cmd + ["get-serialno"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            serial = result.stdout.strip()
            if serial and serial != "unknown":
                return serial
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def is_connected(self) -> bool:
        try:
            if self._device_serial is not None:
                result = subprocess.run(
                    self._base_cmd + ["get-state"],
                    capture_output=True, text=True, timeout=5,
                    encoding="utf-8", errors="replace",
                )
                return result.returncode == 0 and result.stdout.strip() == "device"
            result = subprocess.run(
                self._base_cmd + ["devices"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            lines = result.stdout.strip().split("\n")
            return len(lines) > 1 and "device" in lines[1]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
