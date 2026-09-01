"""Exact-serial ADB transport boundary for the AppWidget harness."""

from __future__ import annotations

import subprocess
from typing import Callable, Sequence

from appwidget_stale_provider_models import CommandResult
from appwidget_stale_provider_parsers import parse_adb_devices


class TransportInputError(ValueError):
    """A caller attempted to bypass the exact-target transport contract."""


class TransportTimeout(RuntimeError):
    """An exact-target ADB command exceeded its bounded timeout."""


Runner = Callable[[Sequence[str], int, bool], CommandResult]


def _decode_adb_text(value: bytes) -> str:
    for encoding in ("utf-8", "cp949"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def _subprocess_runner(
    argv: Sequence[str], timeout_s: int, binary: bool
) -> CommandResult:
    completed = subprocess.run(
        tuple(argv),
        capture_output=True,
        check=False,
        text=False,
        timeout=timeout_s,
    )
    stdout = completed.stdout if binary else _decode_adb_text(completed.stdout)
    stderr = completed.stderr if binary else _decode_adb_text(completed.stderr)
    return CommandResult(
        argv=tuple(argv),
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )


class AdbTransport:
    def __init__(self, serial: str, *, runner: Runner | None = None) -> None:
        if not serial or any(character in serial for character in "\r\n\0"):
            raise TransportInputError("target serial is missing or malformed")
        self.serial = serial
        self._runner = runner or _subprocess_runner

    def _invoke(
        self, argv: Sequence[str], timeout_s: int, binary: bool
    ) -> CommandResult:
        try:
            return self._runner(argv, timeout_s, binary)
        except subprocess.TimeoutExpired as exc:
            raise TransportTimeout(
                f"ADB command timed out after {timeout_s}s"
            ) from exc

    def list_devices(self) -> dict[str, str]:
        result = self._invoke(("adb", "devices", "-l"), 30, False)
        if result.returncode != 0 or not isinstance(result.stdout, str):
            raise RuntimeError("adb device listing failed")
        return parse_adb_devices(result.stdout)

    @staticmethod
    def _validate_target_args(args: Sequence[str]) -> tuple[str, ...]:
        normalized = tuple(args)
        if not normalized:
            raise TransportInputError("target command is empty")
        if normalized[0].startswith("-"):
            raise TransportInputError("target command must begin with an ADB subcommand")
        if any("\0" in token or "\r" in token or "\n" in token for token in normalized):
            raise TransportInputError("target command contains a control character")
        return normalized

    def run_target(
        self, args: Sequence[str], timeout_s: int = 60
    ) -> CommandResult:
        normalized = self._validate_target_args(args)
        argv = ("adb", "-s", self.serial, *normalized)
        return self._invoke(argv, timeout_s, False)

    def run_target_binary(
        self, args: Sequence[str], timeout_s: int = 60
    ) -> CommandResult:
        normalized = self._validate_target_args(args)
        argv = ("adb", "-s", self.serial, *normalized)
        return self._invoke(argv, timeout_s, True)
