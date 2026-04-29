"""Runtime preflight: TC 실행 전 단말 상태 스냅샷을 수집한다.

PR 2 범위. 산출물은 reports/preflight/<run_id>/[<tc_stem>/]에 누적되며
manifest.json + screenshot.png + window_dump.xml 3종으로 구성된다.

CLI는 cmd_preflight()가 주도하며 본 모듈은 순수 조립 로직을 제공한다.
warn-only 정책: ADB 도구 자체 오류 외에는 manifest에 reason을 남기고 exit 0.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.adb import ADB

SCHEMA_VERSION = 1
TOOL_VERSION = "pr2-preflight-v1"

EXPECTED_TEXT_ACTIONS = ("verify_text", "verify_gone", "tap_text")

PM_GRANT_RE = re.compile(
    r"\bpm\s+grant\s+(\S+)\s+(android\.permission\.[A-Z0-9_\.]+)"
)


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_visible_texts_from_xml(xml: str) -> list[str]:
    """uiautomator dump XML에서 visible text를 추출한다.

    중복 제거 + 순서 보존. ParseError 시 빈 배열 반환.
    """
    if not xml:
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    seen: set[str] = set()
    result: list[str] = []
    for node in root.iter():
        value = (node.attrib.get("text") or "").strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_expected_texts(tc: dict) -> list[str]:
    """TC steps에서 expected text를 추출한다.

    scope: verify_text / verify_gone / tap_text의 target 또는 text.
    input_text 제외. 중복 제거 + 순서 보존.
    """
    seen: set[str] = set()
    result: list[str] = []
    steps = tc.get("steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = step.get("action")
        if action not in EXPECTED_TEXT_ACTIONS:
            continue
        value = step.get("target") or step.get("text") or ""
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_package_name(tc: dict) -> str | None:
    """TC top-level 또는 metadata에서 package_name을 추출한다.

    Lookup 우선순위 (PR 2.1):
        1. tc.package_name
        2. metadata.package_name
        3. metadata.target_app.package (target_app이 dict인 경우에만)

    값이 문자열이고 strip 후 non-empty일 때만 채택한다.
    shell command parsing은 본 PR 범위 밖.
    """
    if isinstance(tc.get("package_name"), str) and tc["package_name"].strip():
        return tc["package_name"].strip()
    metadata = tc.get("metadata") or {}
    if isinstance(metadata, dict):
        value = metadata.get("package_name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        target_app = metadata.get("target_app")
        if isinstance(target_app, dict):
            nested = target_app.get("package")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def extract_required_permissions(tc: dict, package_name: str | None) -> list[str]:
    """TC shell steps의 `pm grant <pkg> <permission>`에서 권한을 추출한다.

    package_name이 주어지면 그것에 매칭되는 항목만 채택. 미주어지면 모든 매칭.
    중복 제거 + 순서 보존.
    """
    seen: set[str] = set()
    result: list[str] = []
    steps = tc.get("steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("action") != "shell":
            continue
        command = step.get("command") or ""
        if not isinstance(command, str):
            continue
        for match in PM_GRANT_RE.finditer(command):
            pkg, perm = match.group(1), match.group(2)
            if package_name and pkg != package_name:
                continue
            if perm not in seen:
                seen.add(perm)
                result.append(perm)
    return result


def parse_dumpsys_permissions(dumpsys_output: str, required: list[str]) -> dict[str, str]:
    """dumpsys package 결과에서 required 권한별 granted 상태를 추출한다.

    매칭되지 않으면 'unknown'.
    """
    state: dict[str, str] = {}
    for perm in required:
        pattern = re.compile(
            re.escape(perm) + r":\s*granted=(true|false)", re.IGNORECASE
        )
        match = pattern.search(dumpsys_output or "")
        if match:
            state[perm] = "granted" if match.group(1).lower() == "true" else "denied"
        else:
            state[perm] = "unknown"
    return state


def is_package_installed(adb: ADB, package_name: str) -> bool:
    try:
        out = adb.shell(f"pm list packages {package_name}")
    except TimeoutError:
        return False
    return f"package:{package_name}" in (out or "")


def get_screen_resolution(adb: ADB) -> str | None:
    try:
        out = adb.shell("wm size")
    except TimeoutError:
        return None
    match = re.search(r"(\d+)x(\d+)", out or "")
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    return None


_VERSION_NAME_RE = re.compile(r"versionName=([^\s]+)")
_VERSION_CODE_RE = re.compile(r"versionCode=(\d+)")


def parse_app_version(dumpsys_output: str) -> tuple[str | None, int | None]:
    """dumpsys package 출력에서 versionName / versionCode 추출."""
    if not dumpsys_output:
        return None, None
    name_match = _VERSION_NAME_RE.search(dumpsys_output)
    code_match = _VERSION_CODE_RE.search(dumpsys_output)
    version_name = name_match.group(1) if name_match else None
    version_code = int(code_match.group(1)) if code_match else None
    return version_name, version_code


_FOCUS_RE = re.compile(r"mCurrentFocus=Window\{[^}]*?\s+([\w\.]+/[\w\.\$]+)\}")
_RESUMED_RE = re.compile(r"mResumedActivity:\s*ActivityRecord\{[^}]*?\s+([\w\.]+/[\w\.\$]+)")


def parse_current_activity(dumpsys_window: str, dumpsys_activity: str = "") -> str | None:
    """dumpsys window/activity 출력에서 현재 activity (pkg/Activity) 추출."""
    for source in (dumpsys_window, dumpsys_activity):
        if not source:
            continue
        match = _FOCUS_RE.search(source)
        if match:
            return match.group(1)
        match = _RESUMED_RE.search(source)
        if match:
            return match.group(1)
    return None


def get_current_activity(adb: ADB) -> str | None:
    try:
        win_out = adb.shell("dumpsys window", timeout=15)
    except TimeoutError:
        win_out = ""
    activity = parse_current_activity(win_out)
    if activity:
        return activity
    try:
        act_out = adb.shell("dumpsys activity activities", timeout=15)
    except TimeoutError:
        return None
    return parse_current_activity("", act_out)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _load_tc_raw(tc_path: Path) -> dict:
    with open(tc_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{tc_path}: TC YAML must be a mapping")
    if "name" not in data and "tc_name" in data:
        data["name"] = data["tc_name"]
    return data


def run_preflight(
    tc_path: Path,
    output_dir: Path,
    adb: ADB,
    run_id: str,
    take_screenshot: bool = True,
) -> dict[str, Any]:
    """단일 TC에 대해 preflight를 수행하고 manifest dict를 반환한다.

    output_dir = reports/preflight/<run_id>[/<tc_stem>]
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    tc = _load_tc_raw(tc_path)
    tc_id = tc.get("name") or tc.get("tc_name") or tc_path.stem

    reasons: list[str] = []

    package_name = extract_package_name(tc)
    if package_name is None:
        reasons.append("package_name_missing")

    expected_texts = extract_expected_texts(tc)
    required_permissions = extract_required_permissions(tc, package_name)

    device_serial = adb.device_serial()
    info = adb.get_device_info()
    device = {
        "serial": device_serial,
        "model": info.get("model") or None,
        "android_version": info.get("android_version") or None,
        "status": "connected",
    }

    dumpsys_pkg_out: str = ""
    if package_name is not None:
        try:
            installed = is_package_installed(adb, package_name)
        except Exception:
            installed = None
            reasons.append("package_check_failed")
        if installed:
            try:
                dumpsys_pkg_out = adb.shell(f"dumpsys package {package_name}", timeout=15)
            except TimeoutError:
                dumpsys_pkg_out = ""
    else:
        installed = None

    version_name, version_code = parse_app_version(dumpsys_pkg_out)
    app = {
        "package_name": package_name,
        "installed": installed,
        "version_name": version_name,
        "version_code": version_code,
    }

    if not required_permissions:
        # 권한 요구가 없으면 package_name 유무와 무관하게 parse 자체가 N/A.
        # package_name_missing reason은 permissions 분기 밖(line 257)에서 별도 유지.
        permissions = {
            "required": [],
            "grants": {},
            "parse_status": "ok",
        }
    elif package_name is None:
        permissions = {
            "required": required_permissions,
            "grants": {},
            "parse_status": "failed",
        }
    elif dumpsys_pkg_out:
        grants = parse_dumpsys_permissions(dumpsys_pkg_out, required_permissions)
        unknowns = [p for p, s in grants.items() if s == "unknown"]
        permissions = {
            "required": required_permissions,
            "grants": grants,
            "parse_status": "partial" if unknowns else "ok",
        }
        if unknowns:
            reasons.append("permissions_partial")
    else:
        permissions = {
            "required": required_permissions,
            "grants": {},
            "parse_status": "failed",
        }
        reasons.append("permissions_dump_failed")

    current_activity = get_current_activity(adb)
    if current_activity is None:
        activity_parse_status = "failed"
        reasons.append("activity_parse_failed")
    else:
        activity_parse_status = "ok"

    resolution = get_screen_resolution(adb)
    xml_file = output_dir / "window_dump.xml"
    screenshot_file = output_dir / "screenshot.png"

    try:
        xml = adb.dump_ui()
        xml_file.write_text(xml or "", encoding="utf-8")
        visible_texts = parse_visible_texts_from_xml(xml or "")
        xml_status = "ok"
    except Exception:
        visible_texts = []
        xml_status = "failed"
        reasons.append("xml_dump_failed")

    if xml_status == "ok":
        window_dump_path: str | None = xml_file.name
        xml_sha256 = _sha256_file(xml_file)
    else:
        window_dump_path = None
        xml_sha256 = None

    screenshot_recorded: str | None = None
    screenshot_sha256: str | None = None
    if not take_screenshot:
        screenshot_status = "skipped"
    else:
        try:
            adb.screenshot(screenshot_file)
            if screenshot_file.exists() and screenshot_file.stat().st_size > 0:
                screenshot_recorded = screenshot_file.name
                screenshot_sha256 = _sha256_file(screenshot_file)
                screenshot_status = "ok"
            else:
                screenshot_status = "failed"
                reasons.append("screenshot_failed")
        except Exception:
            screenshot_status = "failed"
            reasons.append("screenshot_failed")

    screen = {
        "resolution": resolution,
        "current_activity": current_activity,
        "activity_parse_status": activity_parse_status,
        "screenshot_path": screenshot_recorded,
        "screenshot_status": screenshot_status,
        "screenshot_sha256": screenshot_sha256,
        "window_dump_path": window_dump_path,
        "xml_status": xml_status,
        "xml_sha256": xml_sha256,
    }

    if xml_status == "ok":
        diff_status = "ok"
        visible_set = set(visible_texts)
        missing = [t for t in expected_texts if t not in visible_set]
    else:
        diff_status = "skipped"
        missing = []

    expected_set = set(expected_texts)
    coverage = (
        round((len(expected_set) - len(missing)) / len(expected_set), 4)
        if expected_set and diff_status == "ok"
        else (1.0 if diff_status == "ok" else None)
    )
    text_model = {
        "expected_texts_from_tc": expected_texts,
        "visible_texts_from_dump": visible_texts,
        "missing_expected_texts": missing,
        "diff_status": diff_status,
        "coverage": coverage,
    }
    if missing and diff_status == "ok":
        reasons.append("expected_texts_missing")

    level = "OK" if not reasons else "WARN"
    preflight_status = {"level": level, "reasons": reasons}

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "generated_at": _now_iso(),
        "tc_path": str(tc_path),
        "tc_id": tc_id,
        "device": device,
        "app": app,
        "permissions": permissions,
        "screen": screen,
        "text_model": text_model,
        "preflight_status": preflight_status,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest


def _resolve_dir_tc_files(dir_path: Path) -> list[Path]:
    return sorted(p for p in dir_path.glob("*.yaml") if p.is_file())
