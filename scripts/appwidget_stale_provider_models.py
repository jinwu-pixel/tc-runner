"""Immutable value objects shared by the AppWidget stale-provider harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union


TextOrBytes = Union[str, bytes]


@dataclass(frozen=True)
class PackageState:
    package: str
    version_name: str | None
    version_code: int | None
    signature_token: str | None
    uid: int | None
    stopped: bool | None
    not_launched: bool | None


@dataclass(frozen=True)
class WidgetBinding:
    widget_id: int
    provider_component: str
    host_package: str
    remote_views_present: bool


@dataclass(frozen=True)
class LauncherHostBinding:
    widget_id: int
    provider_component: str | None
    host_package: str
    remote_views_present: bool
    host_id: int | None = None


@dataclass(frozen=True)
class AppWidgetState:
    provider_registered: bool
    provider_uid: int | None
    bindings: tuple[WidgetBinding, ...]


@dataclass(frozen=True)
class CrashSignature:
    count: int
    matched_records: tuple[str, ...]


@dataclass(frozen=True)
class LauncherCrashExit:
    timestamp: str
    pid: int
    process: str
    reason_code: int


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: TextOrBytes
    stderr: TextOrBytes


@dataclass(frozen=True)
class DeviceIdentity:
    serial: str
    model: str
    fingerprint: str
    incremental: str
    viewport: tuple[int, int]
    connected_devices: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Event:
    timestamp_utc: str
    timestamp_kst: str
    phase: str
    command_category: str
    target_serial: str
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    resulting_state: str
    logical_command: tuple[str, ...] = ()
    boot_id: str | None = None
    device_elapsed_realtime_s: float | None = None
    previous_state: str | None = None


@dataclass(frozen=True)
class UiNode:
    text: str
    content_description: str
    resource_id: str
    checked: bool | None
    bounds: tuple[int, int, int, int] | None

    @property
    def center(self) -> tuple[int, int] | None:
        if self.bounds is None:
            return None
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)


class Phase(str, Enum):
    BASELINE_CAPTURED = "BASELINE_CAPTURED"
    BOUND_GENERAL = "BOUND_GENERAL"
    SAFE_SIMPLE = "SAFE_SIMPLE"
    STALE_ARMED = "STALE_ARMED"
    CLEAN_CONTROL_ARMED = "CLEAN_CONTROL_ARMED"
    TRIGGERED_BUG = "TRIGGERED_BUG"
    TRIGGERED_FIXED = "TRIGGERED_FIXED"
    TRIGGERED_STALE_NO_BUG = "TRIGGERED_STALE_NO_BUG"
    TRIGGERED_CONTROL_NO_BUG = "TRIGGERED_CONTROL_NO_BUG"
    TRIGGERED_CONTROL_BUG = "TRIGGERED_CONTROL_BUG"
    RESTORED_SAFE = "RESTORED_SAFE"
