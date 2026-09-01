"""Pure phase transition rules for the AppWidget harness."""

from __future__ import annotations

from appwidget_stale_provider_models import Phase


class PhaseViolation(RuntimeError):
    """A command was attempted from an illegal phase."""


def assert_transition(
    current: Phase | None,
    command: str,
    *,
    outcome: str | None = None,
) -> Phase:
    if current is None and command == "capture":
        return Phase.BASELINE_CAPTURED
    if current is Phase.BASELINE_CAPTURED and command == "bind":
        return Phase.BOUND_GENERAL
    if current is Phase.BOUND_GENERAL and command == "arm-switch":
        return Phase.SAFE_SIMPLE
    if current is Phase.BOUND_GENERAL and command == "negative-control-failed":
        return Phase.BOUND_GENERAL
    if current is Phase.SAFE_SIMPLE and command == "arm-lifecycle":
        return Phase.STALE_ARMED
    if current is Phase.SAFE_SIMPLE and command == "arm-clean-control":
        return Phase.CLEAN_CONTROL_ARMED
    if current is Phase.STALE_ARMED and command == "trigger":
        if outcome == "bug":
            return Phase.TRIGGERED_BUG
        if outcome == "fixed":
            return Phase.TRIGGERED_FIXED
        raise PhaseViolation(f"unknown trigger outcome: {outcome}")
    if current is Phase.CLEAN_CONTROL_ARMED and command == "trigger-control":
        if outcome == "no-bug":
            return Phase.TRIGGERED_CONTROL_NO_BUG
        if outcome == "bug":
            return Phase.TRIGGERED_CONTROL_BUG
        raise PhaseViolation(f"unknown control trigger outcome: {outcome}")
    if command == "restore" and current in {
        Phase.BASELINE_CAPTURED,
        Phase.BOUND_GENERAL,
        Phase.SAFE_SIMPLE,
        Phase.STALE_ARMED,
        Phase.CLEAN_CONTROL_ARMED,
        Phase.TRIGGERED_BUG,
        Phase.TRIGGERED_FIXED,
        Phase.TRIGGERED_CONTROL_NO_BUG,
        Phase.TRIGGERED_CONTROL_BUG,
    }:
        return Phase.RESTORED_SAFE
    raise PhaseViolation(f"illegal transition: {current!r} -> {command}")
