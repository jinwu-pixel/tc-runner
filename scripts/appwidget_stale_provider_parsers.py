"""Pure parsers for Android state used by the AppWidget harness."""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from appwidget_stale_provider_models import (
    AppWidgetState,
    CrashSignature,
    LauncherCrashExit,
    PackageState,
    UiNode,
    WidgetBinding,
    LauncherHostBinding,
)


class UiDumpParseError(ValueError):
    """A UIAutomator dump could not be framed or parsed as one hierarchy."""


def _parse_ui_root(xml: str):
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise UiDumpParseError("UI dump XML is malformed") from exc
    if root.tag != "hierarchy":
        raise UiDumpParseError("UI dump root must be hierarchy")
    return root


def normalize_ui_dump(raw: str) -> str:
    """Extract and validate exactly one hierarchy from raw /dev/tty output."""
    start = raw.find("<hierarchy")
    closing = "</hierarchy>"
    end = raw.find(closing, start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise UiDumpParseError("UI dump hierarchy is missing")
    end += len(closing)
    if raw.find("<hierarchy", end) >= 0:
        raise UiDumpParseError("UI dump contains multiple hierarchies")
    xml = raw[start:end]
    _parse_ui_root(xml)
    return xml


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


def parse_launcher_host_bindings(
    stdout: str,
    launcher_package: str,
) -> tuple[LauncherHostBinding, ...]:
    """Return every widget owned by one exact Launcher host package."""
    _provider_region, separator, widget_region = stdout.partition("Widgets:")
    if not separator:
        raise ValueError("appwidget dump is incomplete: Widgets section is missing")
    bindings: list[LauncherHostBinding] = []
    for block in _widget_blocks(widget_region):
        widget_id = _matched_int(r"\b(?:appWidgetId[:=]|id=)(\d+)", block)
        host_package = _matched_text(r"\bpkg[:=]([A-Za-z0-9_.]+)", block)
        provider_component = _matched_text(
            r"\bcmp[:=](?:ComponentInfo\{)?([A-Za-z0-9_.$]+/[A-Za-z0-9_.$]+)",
            block,
        )
        if host_package != launcher_package:
            continue
        if widget_id is None:
            raise ValueError(
                "appwidget dump is incomplete: Launcher binding lacks identity"
            )
        views_value = _matched_text(
            r"\b(?:views|RemoteViews)\s*[:=]\s*([^\s,}\]]+)", block
        )
        bindings.append(
            LauncherHostBinding(
                widget_id=widget_id,
                provider_component=provider_component,
                host_package=host_package,
                remote_views_present=(
                    views_value is not None and views_value.lower() != "null"
                ),
            )
        )
    return tuple(bindings)


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


def parse_launcher_crash_exits(
    stdout: str,
    launcher_package: str,
) -> tuple[LauncherCrashExit, ...]:
    """Parse stable identities for exact-package APP CRASH exit records."""
    starts = list(re.finditer(r"(?m)^\s*ApplicationExitInfo #\d+:\s*$", stdout))
    parsed: list[LauncherCrashExit] = []
    for index, match in enumerate(starts):
        block = (
            stdout[match.end() : starts[index + 1].start()]
            if index + 1 < len(starts)
            else stdout[match.end() :]
        )
        identity = re.search(
            r"(?m)^\s*timestamp=(.+?)\s+pid=(\d+)\b",
            block,
        )
        reason = re.search(
            r"(?m)^\s*process=([^\s]+)\s+reason=(\d+)\s+"
            r"\(([^\r\n]*)\)\s+subreason=",
            block,
        )
        if identity is None or reason is None:
            continue
        process = reason.group(1)
        reason_code = int(reason.group(2))
        reason_label = reason.group(3)
        if (
            process != launcher_package
            or reason_code != 4
            or not reason_label.startswith("APP CRASH")
        ):
            continue
        parsed.append(
            LauncherCrashExit(
                timestamp=identity.group(1),
                pid=int(identity.group(2)),
                process=process,
                reason_code=reason_code,
            )
        )
    return tuple(parsed)


def find_ui_node(xml: str, exact_value: str) -> UiNode | None:
    """Find one exact text/content-description node in a UIAutomator dump."""
    root = _parse_ui_root(xml)
    for element in root.iter("node"):
        text = element.attrib.get("text", "")
        description = element.attrib.get("content-desc", "")
        if text != exact_value and description != exact_value:
            continue
        return _ui_node_from_element(element)
    return None


def find_ui_node_by_resource_id(xml: str, resource_id: str) -> UiNode | None:
    """Find one node by exact Android resource ID."""
    root = _parse_ui_root(xml)
    for element in root.iter("node"):
        if element.attrib.get("resource-id", "") == resource_id:
            return _ui_node_from_element(element)
    return None


def ui_contains_exact_package(xml: str, package: str) -> bool:
    """Return whether a parsed hierarchy contains the exact package name."""
    root = _parse_ui_root(xml)
    return any(
        element.attrib.get("package", "") == package
        for element in root.iter("node")
    )


def _ui_node_from_element(element) -> UiNode:
    raw_bounds = element.attrib.get("bounds", "")
    match = re.fullmatch(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", raw_bounds)
    bounds = tuple(int(value) for value in match.groups()) if match else None
    raw_checked = element.attrib.get("checked")
    checked = {"true": True, "false": False}.get(raw_checked)
    return UiNode(
        text=element.attrib.get("text", ""),
        content_description=element.attrib.get("content-desc", ""),
        resource_id=element.attrib.get("resource-id", ""),
        checked=checked,
        bounds=bounds,
    )
