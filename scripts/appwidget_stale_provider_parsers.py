"""Pure parsers for Android state used by the AppWidget harness."""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from appwidget_stale_provider_models import (
    AppWidgetState,
    CrashSignature,
    PackageState,
    UiNode,
    WidgetBinding,
)


def parse_adb_devices(stdout: str) -> dict[str, str]:
    """Return serial -> connection state without transport metadata."""
    devices: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        if line.startswith("*") or line.startswith("adb server"):
            continue
        fields = line.split()
        if len(fields) >= 2:
            devices[fields[0]] = fields[1]
    return devices


def _matched_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _matched_text(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def _matched_bool(name: str, text: str) -> bool | None:
    value = _matched_text(rf"\b{re.escape(name)}=(true|false)\b", text)
    return None if value is None else value == "true"


def parse_package_state(stdout: str, package: str) -> PackageState:
    """Parse package identity and user-state flags from dumpsys package."""
    return PackageState(
        package=package,
        version_name=_matched_text(r"^\s*versionName=([^\s]+)", stdout),
        version_code=_matched_int(r"^\s*versionCode=(\d+)", stdout),
        signature_token=_matched_text(
            r"signatures:\[([0-9A-Fa-f]+)\]", stdout
        ),
        uid=_matched_int(r"^\s*(?:userId|appId)=(\d+)", stdout),
        stopped=_matched_bool("stopped", stdout),
        not_launched=_matched_bool("notLaunched", stdout),
    )


def _widget_blocks(widget_region: str) -> list[str]:
    starts = list(
        re.finditer(
            r"(?m)^\s*(?:AppWidgetId\{|\[\d+\]\s+id=\d+)",
            widget_region,
        )
    )
    return [
        widget_region[match.start() : starts[index + 1].start()]
        if index + 1 < len(starts)
        else widget_region[match.start() :]
        for index, match in enumerate(starts)
    ]


def parse_appwidget_state(
    stdout: str,
    component: str,
    launcher_package: str,
) -> AppWidgetState:
    """Parse provider registration independently from concrete bindings."""
    provider_region, separator, widget_region = stdout.partition("Widgets:")
    if not separator:
        widget_region = ""

    provider_registered = component in provider_region
    provider_uid: int | None = None
    for line in provider_region.splitlines():
        if component not in line:
            continue
        provider_uid = _matched_int(r"\b(?:uid=|app:)(\d+)", line)
        break

    bindings: list[WidgetBinding] = []
    for block in _widget_blocks(widget_region):
        if component not in block:
            continue
        widget_id = _matched_int(r"\b(?:appWidgetId[:=]|id=)(\d+)", block)
        host_package = _matched_text(r"\bpkg[:=]([A-Za-z0-9_.]+)", block)
        if widget_id is None or host_package != launcher_package:
            continue
        views_value = _matched_text(
            r"\b(?:views|RemoteViews)\s*[:=]\s*([^\s,}\]]+)", block
        )
        bindings.append(
            WidgetBinding(
                widget_id=widget_id,
                provider_component=component,
                host_package=host_package,
                remote_views_present=(
                    views_value is not None and views_value.lower() != "null"
                ),
            )
        )

    return AppWidgetState(
        provider_registered=provider_registered,
        provider_uid=provider_uid,
        bindings=tuple(bindings),
    )


def parse_home_role(stdout: str, profile: dict[str, Any]) -> str:
    """Parse only an exact role-holder line or the resumed-activity field."""
    packages = {str(profile["simple_home"]), str(profile["general_home"])}
    holders = {
        line.strip() for line in stdout.splitlines() if line.strip() in packages
    }
    if len(holders) == 1:
        return next(iter(holders))
    resumed_field = re.compile(
        r"^\s*(?:(?:mResumedActivity|ResumedActivity)\s*:|"
        r"topResumedActivity\s*=)"
    )
    for line in stdout.splitlines():
        if resumed_field.match(line) is None:
            continue
        for package in packages:
            if re.search(
                rf"\b{re.escape(package)}/[A-Za-z0-9_.$]+",
                line,
            ):
                return package
    return "UNKNOWN"


def parse_crash_signature(stdout: str) -> CrashSignature:
    """Count only crash records containing both BUG27084 stack locations."""
    starts = list(re.finditer(r"(?m)^[^\r\n]*FATAL EXCEPTION:", stdout))
    if starts:
        records = [
            stdout[match.start() : starts[index + 1].start()].strip()
            if index + 1 < len(starts)
            else stdout[match.start() :].strip()
            for index, match in enumerate(starts)
        ]
    else:
        records = [part.strip() for part in re.split(r"\r?\n\s*\r?\n", stdout)]
    matched = tuple(
        record
        for record in records
        if "LauncherAppWidgetHostView.java:185" in record
        and "PendingAppWidgetHostView.java:88" in record
    )
    return CrashSignature(count=len(matched), matched_records=matched)


def find_ui_node(xml: str, exact_value: str) -> UiNode | None:
    """Find one exact text/content-description node in a UIAutomator dump."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return None
    for element in root.iter("node"):
        text = element.attrib.get("text", "")
        description = element.attrib.get("content-desc", "")
        if text != exact_value and description != exact_value:
            continue
        raw_bounds = element.attrib.get("bounds", "")
        match = re.fullmatch(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", raw_bounds)
        bounds = tuple(int(value) for value in match.groups()) if match else None
        return UiNode(
            text=text,
            content_description=description,
            bounds=bounds,
        )
    return None
