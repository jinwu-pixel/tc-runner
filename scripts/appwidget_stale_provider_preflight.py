"""Fail-closed device identity preflight for BUG27084."""

from __future__ import annotations

import re
from typing import Any

from appwidget_stale_provider_models import CommandResult, DeviceIdentity


class IdentityMismatch(RuntimeError):
    """The requested, configured, or live device identity did not match."""


def _text_result(result: CommandResult, label: str) -> str:
    if result.returncode != 0 or not isinstance(result.stdout, str):
        raise IdentityMismatch(f"{label} could not be read")
    return result.stdout.strip()


def _read(transport, args: tuple[str, ...], label: str) -> str:
    return _text_result(transport.run_target(args), label)


def _parse_viewport(stdout: str) -> tuple[int, int]:
    matches = re.findall(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", stdout)
    if not matches:
        raise IdentityMismatch("viewport could not be parsed")
    width, height = matches[-1]
    return int(width), int(height)


def preflight_identity(
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    profile: dict[str, Any],
) -> DeviceIdentity:
    if serial != transport.serial:
        raise IdentityMismatch("CLI serial and transport serial differ")
    devices = transport.list_devices()
    if devices.get(serial) != "device":
        raise IdentityMismatch(
            f"target serial is not connected as device: {devices.get(serial, 'missing')}"
        )
    if expected_model != profile["model"]:
        raise IdentityMismatch("CLI model and profile model differ")
    if expected_fingerprint != profile["fingerprint"]:
        raise IdentityMismatch("CLI fingerprint and profile fingerprint differ")

    model = _read(
        transport, ("shell", "getprop", "ro.product.model"), "device model"
    )
    fingerprint = _read(
        transport,
        ("shell", "getprop", "ro.build.fingerprint"),
        "device fingerprint",
    )
    incremental = _read(
        transport,
        ("shell", "getprop", "ro.build.version.incremental"),
        "device incremental",
    )
    viewport = _parse_viewport(
        _read(transport, ("shell", "wm", "size"), "device viewport")
    )

    if model != expected_model:
        raise IdentityMismatch("live model differs from expected model")
    if fingerprint != expected_fingerprint:
        raise IdentityMismatch("live fingerprint differs from expected fingerprint")
    if incremental != profile["incremental"]:
        raise IdentityMismatch("live incremental differs from profile")
    if viewport != tuple(profile["viewport"]):
        raise IdentityMismatch("live viewport differs from profile")

    return DeviceIdentity(
        serial=serial,
        model=model,
        fingerprint=fingerprint,
        incremental=incremental,
        viewport=viewport,
        connected_devices=tuple(sorted(devices.items())),
    )
