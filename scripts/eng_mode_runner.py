#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Profile-driven Engineer-Mode device runner.

The pure helpers and ``plan`` command are host-only. Device commands preserve
the ODIN2 V1 call-site behavior of the frozen run_complex_0617.py runner.
Runtime validation on a device is deliberately a separate gate.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_PROFILE_PATH = _HERE / "eng_mode_profiles.py"
_profile_spec = importlib.util.spec_from_file_location("eng_mode_profiles", _PROFILE_PATH)
_profiles = importlib.util.module_from_spec(_profile_spec)
sys.modules[_profile_spec.name] = _profiles
_profile_spec.loader.exec_module(_profiles)

PROFILES = _profiles.PROFILES
CASESETS = _profiles.CASESETS

PROFILE_NAME = "ODIN2_ENG_V1"
PROFILE = PROFILES[PROFILE_NAME]
CASES = CASESETS[PROFILE_NAME]
DEV: str | None = None
RUN: Path | None = None

_PROFILE_KEYS = {
    "package",
    "activity",
    "gate_label",
    "expect_model",
    "tabs",
    "default_serial",
    "rid",
    "btn_labels",
    "popup_dismiss_exact",
    "reboot_popup_labels",
    "pull_specs",
    "hook_keywords",
    "swipe_reset",
    "swipe_list_scroll",
    "swipe_detail_scroll",
    "evidence_dir",
}
_RID_KEYS = {
    "item_title",
    "tv_detail_value",
    "tv_detail_status",
    "tv_top_title",
    "et_detail_input",
    "btn_read",
    "btn_write",
    "btn_reset",
    "btn_back",
    "radio_prefix",
    "current_value",
    "text_key",
    "edit_value",
    "mfield_write",
    "mfield_read",
    "text_value",
}


# ---- PURE ------------------------------------------------------------------

def nodes(xml_text: str) -> list[dict[str, str]]:
    """Parse uiautomator XML, tolerating its occasional stdout prefix."""
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        index = xml_text.find("<hierarchy")
        root = ET.fromstring(xml_text[index:]) if index >= 0 else None
    return [node.attrib for node in root.iter("node")] if root is not None else []


def center(bounds: str) -> tuple[int, int]:
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    return (
        (int(match.group(1)) + int(match.group(3))) // 2,
        (int(match.group(2)) + int(match.group(4))) // 2,
    )


def _rid_tail(node: dict[str, str]) -> str:
    return node.get("resource-id", "").split("/")[-1]


def find_text_node(
    xml_text: str, needle: str, *, exact: bool = False
) -> dict[str, str] | None:
    for node in nodes(xml_text):
        text = node.get("text", "")
        if text == needle if exact else needle in text:
            return node
    return None


def _btn_by_text(xml_text: str, label: str) -> dict[str, str] | None:
    for node in nodes(xml_text):
        if node.get("text", "") == label and node.get("resource-id", ""):
            return node
    return None


def locate_item(
    xml_text: str, item_substr: str, item_title_rid: str
) -> dict[str, str] | None:
    return next(
        (
            node
            for node in nodes(xml_text)
            if node.get("resource-id", "").endswith(item_title_rid)
            and item_substr in node.get("text", "")
        ),
        None,
    )


def list_bottom_signature(xml_text: str, item_title_rid: str) -> str:
    return "|".join(
        node.get("text", "")
        for node in nodes(xml_text)
        if node.get("resource-id", "").endswith(item_title_rid)
    )


def extract_detail(
    xml_text: str, detail_keys: set[str] | tuple[str, ...]
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for node in nodes(xml_text):
        key = _rid_tail(node)
        if key in detail_keys:
            result[key] = {
                "text": node.get("text", ""),
                "bounds": node.get("bounds", ""),
            }
    return result


def locate_radio_command(
    xml_text: str, option_text: str, radio_prefix: str
) -> dict[str, str] | None:
    radios = [node for node in nodes(xml_text) if _rid_tail(node).startswith(radio_prefix)]
    return next((node for node in radios if node.get("text", "") == option_text), None) or next(
        (node for node in radios if option_text in node.get("text", "")), None
    )


def locate_radio_session(
    xml_text: str, option: str, radio_prefix: str
) -> dict[str, str] | None:
    radios = [node for node in nodes(xml_text) if _rid_tail(node).startswith(radio_prefix)]
    if option.startswith(radio_prefix):
        return next((node for node in radios if _rid_tail(node) == option), None)
    return next((node for node in radios if node.get("text", "") == option), None) or next(
        (node for node in radios if option in node.get("text", "")), None
    )


def locate_mfield_command(
    node_list: list[dict[str, str]], fieldkey: str, rid: dict[str, str]
) -> tuple[int | None, dict[str, str] | None, dict[str, str] | None, dict[str, str] | None]:
    """Preserve cmd_mfield's endswith matching and early-break scan."""
    index = next(
        (
            i
            for i, node in enumerate(node_list)
            if node.get("resource-id", "").endswith(rid["text_key"])
            and fieldkey in node.get("text", "")
        ),
        None,
    )
    if index is None:
        return None, None, None, None
    edit = write = read = None
    for node in node_list[index + 1 :]:
        tail = _rid_tail(node)
        if tail == rid["edit_value"] and edit is None:
            edit = node
        if tail == rid["mfield_write"] and write is None:
            write = node
        if tail == rid["mfield_read"] and read is None:
            read = node
        if edit and write and read:
            break
    return index, edit, write, read


def locate_mfield_session(
    node_list: list[dict[str, str]], fieldkey: str, rid: dict[str, str]
) -> tuple[int | None, dict[str, str] | None, dict[str, str] | None, dict[str, str] | None]:
    """Preserve _sess_mfield's endswith matching and independent next scans."""
    index = next(
        (
            i
            for i, node in enumerate(node_list)
            if node.get("resource-id", "").endswith(rid["text_key"])
            and fieldkey in node.get("text", "")
        ),
        None,
    )
    if index is None:
        return None, None, None, None
    tail = node_list[index + 1 :]
    edit = next(
        (node for node in tail if node.get("resource-id", "").endswith(rid["edit_value"])),
        None,
    )
    write = next(
        (node for node in tail if node.get("resource-id", "").endswith(rid["mfield_write"])),
        None,
    )
    read = next(
        (node for node in tail if node.get("resource-id", "").endswith(rid["mfield_read"])),
        None,
    )
    return index, edit, write, read


def parse_adb_devices(stdout: str) -> list[str]:
    serials = []
    for line in stdout.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 2 and columns[1] == "device":
            serials.append(columns[0])
    return serials


def resolve_device(serials: list[str], default: str) -> tuple[str, str | None]:
    if default in serials:
        return default, None
    if len(serials) == 1:
        chosen = serials[0]
        return chosen, f"default {default} not connected; using sole device {chosen}"
    return default, f"default {default} not connected; connected={serials or 'none'}"


def device_identity_ok(model: str, app_present: bool, profile: dict) -> bool:
    return model == profile["expect_model"] and app_present


def capture_gate_reached(registry_text: str, want: str) -> bool:
    if want == "any":
        return True
    if want == "reg":
        return "availableServices=[VOICE" in registry_text
    if want == "call":
        return "mCallState=2" in registry_text
    raise ValueError(f"unknown capture gate: {want}")


def filter_hook_lines(lines: list[str], keywords: tuple[str, ...]) -> list[str]:
    return [line for line in lines if any(keyword in line for keyword in keywords)]


def write_mismatch_abort(value: object, observed: str) -> bool:
    text = str(value)
    return text.split("/")[0] not in observed and text[:6] not in observed


def encode_input_text(value: object) -> str:
    return str(value).replace(" ", "%s")


def toggle_write_needed(before: str | None, want: str | None) -> bool:
    return want is None or want.upper() not in (before or "").upper()


def pick_latest(ls_stdout: str, extension: str) -> str | None:
    return next((name for name in ls_stdout.split() if name.endswith(extension)), None)


def pull_spec_for_extension(profile: dict, extension: str):
    return next((spec for spec in profile["pull_specs"] if spec[1] == extension), None)


def validate_profile(profile: dict) -> list[str]:
    errors = [f"missing profile key: {key}" for key in sorted(_PROFILE_KEYS - set(profile))]
    rid = profile.get("rid", {})
    errors.extend(f"missing rid key: {key}" for key in sorted(_RID_KEYS - set(rid)))
    labels = profile.get("btn_labels", {})
    for key in ("write", "read"):
        if key not in labels:
            errors.append(f"missing btn_labels key: {key}")
    return errors


def validate_caseset(profile: dict, casesets: dict, tcid: str) -> list[str]:
    if tcid not in casesets:
        return [f"unknown case: {tcid}"]
    case = casesets[tcid]
    if not isinstance(case, (tuple, list)) or len(case) != 2:
        return ["case must be (tab, items)"]
    tab, items = case
    errors = []
    if tab not in profile["tabs"]:
        errors.append(f"unsupported tab: {tab}")
    if not isinstance(items, list):
        errors.append("case items must be a list")
        return errors
    for index, row in enumerate(items, 1):
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            errors.append(f"item {index}: expected (item, kind, value)")
            continue
        kind = row[1]
        if kind not in {"text", "radio", "toggle"} and not str(kind).startswith("mfield:"):
            errors.append(f"item {index}: unsupported kind {kind}")
        if str(kind).startswith("mfield:") and not str(kind).split(":", 1)[1]:
            errors.append(f"item {index}: empty mfield key")
    return errors


def _plan_target(profile: dict, kind: str, value: object) -> str:
    rid = profile["rid"]
    if kind == "text":
        return f"{rid['et_detail_input']}->{rid['btn_write']}"
    if kind == "radio":
        option = str(value)
        target = option if option.startswith(rid["radio_prefix"]) else rid["radio_prefix"] + "*"
        return f"{target}->{profile['btn_labels']['write']}"
    if kind == "toggle":
        return f"{rid['btn_read']}->{rid['btn_write']}"
    fieldkey = kind.split(":", 1)[1]
    return f"{rid['text_key']}={fieldkey}->{rid['edit_value']}->{rid['mfield_write']}"


def render_plan(profile: dict, casesets: dict, tcid: str) -> list[dict[str, object]]:
    errors = validate_profile(profile)
    if not errors:
        errors.extend(validate_caseset(profile, casesets, tcid))
    if errors:
        raise ValueError("; ".join(errors))
    tab, items = casesets[tcid]
    return [
        {
            "index": index,
            "tab": tab,
            "item": item,
            "kind": kind,
            "value": value,
            "target": _plan_target(profile, kind, value),
        }
        for index, (item, kind, value) in enumerate(items, 1)
    ]


def resolve_output_root(repo_root: Path, profile: dict, override: str | None) -> Path:
    candidate = Path(override) if override else Path(profile["evidence_dir"])
    return candidate if candidate.is_absolute() else repo_root / candidate


def validate_run_label(label: str) -> str:
    if not label or label in {".", ".."} or Path(label).name != label:
        raise ValueError("run label must be one path component")
    return label


# ---- DEVICE ---------------------------------------------------------------

def _connected() -> list[str]:
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return parse_adb_devices(result.stdout)


def _configure(profile_name: str, out_root: str | None, run_label: str) -> None:
    global PROFILE_NAME, PROFILE, CASES, DEV, RUN
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name}; known={sorted(PROFILES)}")
    if profile_name not in CASESETS:
        raise ValueError(f"profile has no casesets: {profile_name}")
    profile = PROFILES[profile_name]
    errors = validate_profile(profile)
    if errors:
        raise ValueError("; ".join(errors))
    label = validate_run_label(run_label)
    PROFILE_NAME = profile_name
    PROFILE = profile
    CASES = CASESETS[profile_name]
    default = os.environ.get("ENG_DEV", profile["default_serial"])
    DEV, warning = resolve_device(_connected(), default)
    if warning:
        print(f"WARN: {warning}", file=sys.stderr)
    RUN = resolve_output_root(_REPO_ROOT, profile, out_root) / label


def adb(*args: object, timeout: int = 180):
    if DEV is None:
        raise RuntimeError("device is not configured")
    return subprocess.run(
        ["adb", "-s", DEV, *[str(value) for value in args]],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def dump() -> str:
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    return adb("exec-out", "cat", "/sdcard/ui.xml").stdout


def tap(x: int, y: int, pause: float = 0.8) -> None:
    adb("shell", "input", "tap", x, y)
    time.sleep(pause)


def tap_text(xml_text: str, needle: str, exact: bool = False) -> bool:
    node = find_text_node(xml_text, needle, exact=exact)
    if node is None:
        return False
    x, y = center(node["bounds"])
    tap(x, y)
    return True


def reset_top() -> None:
    for _ in range(6):
        adb("shell", "input", "swipe", *PROFILE["swipe_reset"])
    time.sleep(0.5)


def goto(tab: str) -> None:
    adb("shell", "am", "force-stop", PROFILE["package"])
    time.sleep(1.0)
    adb("shell", "am", "start", "-n", PROFILE["package"] + "/" + PROFILE["activity"])
    time.sleep(2.0)
    tap_text(dump(), PROFILE["gate_label"])
    time.sleep(1.6)
    tap_text(dump(), tab, exact=True)
    time.sleep(1.6)


def find_item(item_substr: str, max_scroll: int = 12) -> bool:
    reset_top()
    last = None
    for _ in range(max_scroll):
        xml_text = dump()
        node = locate_item(xml_text, item_substr, PROFILE["rid"]["item_title"])
        if node:
            x, y = center(node["bounds"])
            tap(x, y, 1.2)
            return True
        signature = list_bottom_signature(xml_text, PROFILE["rid"]["item_title"])
        if signature == last:
            break
        last = signature
        adb("shell", "input", "swipe", *PROFILE["swipe_list_scroll"])
        time.sleep(0.9)
    return False


def detail() -> tuple[dict[str, dict[str, str]], str]:
    xml_text = dump()
    rid = PROFILE["rid"]
    keys = (
        rid["tv_detail_value"],
        rid["tv_detail_status"],
        rid["tv_top_title"],
        rid["et_detail_input"],
        rid["btn_read"],
        rid["btn_write"],
        rid["btn_reset"],
        rid["btn_back"],
    )
    return extract_detail(xml_text, keys), xml_text


def outdir(tcid: str) -> Path:
    if RUN is None:
        raise RuntimeError("output root is not configured")
    directory = RUN / tcid
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def hook(path: Path) -> list[str]:
    lines = filter_hook_lines(adb("logcat", "-d").stdout.splitlines(), PROFILE["hook_keywords"])
    path.write_text("\n".join(lines), encoding="utf-8")
    return lines


def save(path: Path, xml_text: str) -> None:
    path.write_text(xml_text, encoding="utf-8")


def show(detail_map: dict[str, dict[str, str]]) -> None:
    rid = PROFILE["rid"]
    for key in (
        rid["tv_top_title"],
        rid["tv_detail_value"],
        rid["tv_detail_status"],
        rid["et_detail_input"],
    ):
        if key in detail_map:
            print(f"   {key:18s}= {detail_map[key]['text']!r}")


def cmd_read(tcid: str, tab: str, item_substr: str, step: str = "r") -> None:
    output = outdir(tcid)
    goto(tab)
    if not find_item(item_substr):
        print(f"!! not found: {item_substr}")
        return
    detail_map, xml_text = detail()
    save(output / f"{step}_{item_substr[:10]}_pre.xml", xml_text)
    adb("logcat", "-c")
    key = PROFILE["rid"]["btn_read"]
    if key in detail_map:
        x, y = center(detail_map[key]["bounds"])
        tap(x, y, 1.2)
    detail_map, xml_text = detail()
    save(output / f"{step}_{item_substr[:10]}_read.xml", xml_text)
    lines = hook(output / f"{step}_{item_substr[:10]}_read_hook.log")
    print(f"== READ {tcid} :: {item_substr}")
    show(detail_map)
    print(f"   Way2 hook lines = {len(lines)}")
    for line in lines[-6:]:
        print("   | " + line[-150:])


def cmd_write(tcid: str, tab: str, item_substr: str, value: str, step: str = "w") -> None:
    output = outdir(tcid)
    goto(tab)
    if not find_item(item_substr):
        print(f"!! not found: {item_substr}")
        return
    rid = PROFILE["rid"]
    detail_map, xml_text = detail()
    if rid["et_detail_input"] not in detail_map:
        print("!! no et_detail_input — radio/action item. dump saved.")
        save(output / f"{step}_{item_substr[:10]}_noinput.xml", xml_text)
        print("   detail keys:", list(detail_map.keys()))
        for node in nodes(xml_text):
            text = node.get("text", "").strip()
            tail = _rid_tail(node)
            if text and tail:
                print(f"     [{tail}] {text!r} {node.get('bounds', '')}")
        return
    x, y = center(detail_map[rid["et_detail_input"]]["bounds"])
    tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 16))
    time.sleep(0.3)
    adb("shell", "input", "text", encode_input_text(value))
    time.sleep(0.5)
    detail_map, xml_text = detail()
    save(output / f"{step}_{item_substr[:10]}_input.xml", xml_text)
    observed = detail_map.get(rid["et_detail_input"], {}).get("text", "")
    print(f"== WRITE {tcid} :: {item_substr} <- {value}")
    print(f"   input field now = {observed!r}")
    if write_mismatch_abort(value, observed):
        print("   !! input mismatch — ABORT")
        return
    adb("logcat", "-c")
    if rid["btn_write"] in detail_map:
        x, y = center(detail_map[rid["btn_write"]]["bounds"])
        tap(x, y, 1.4)
    detail_map, xml_text = detail()
    save(output / f"{step}_{item_substr[:10]}_post.xml", xml_text)
    lines = hook(output / f"{step}_{item_substr[:10]}_hook.log")
    show(detail_map)
    print(f"   Way2 hook lines = {len(lines)}")
    for line in lines[-8:]:
        print("   | " + line[-150:])


def cmd_reboot() -> None:
    print("== REBOOT ...")
    adb("reboot")
    time.sleep(3)
    adb("wait-for-device", timeout=180)
    time.sleep(28)
    adb("shell", "svc", "power", "stayon", "true")
    adb("shell", "input", "keyevent", "224")
    adb("shell", "wm", "dismiss-keyguard")
    time.sleep(1)
    xml_text = dump()
    if any(tap_text(xml_text, label) for label in PROFILE["reboot_popup_labels"]):
        print("   DataPopup handled")
        time.sleep(1)
    print("   boot done. radio settle wait ...")
    time.sleep(20)


def cmd_pull(tcid: str, tag: str = "") -> None:
    output = outdir(tcid)
    for remote_dir, extension, label in PROFILE["pull_specs"]:
        latest = pick_latest(adb("shell", "ls", "-t", remote_dir).stdout, extension)
        if not latest:
            continue
        destination = output / f"{label}_{tag}_{latest}"
        adb("pull", remote_dir + latest, destination)
        if label == "modem":
            print(f"   pulled modem: {latest} -> {destination.stat().st_size} bytes")
        else:
            print(f"   pulled {label}: {latest}")


def _dismiss_popup() -> bool:
    if tap_text(dump(), PROFILE["popup_dismiss_exact"], exact=True):
        time.sleep(0.8)
        return True
    return False


def cmd_radio(tcid: str, tab: str, item_substr: str, option_text: str, step: str = "w") -> None:
    output = outdir(tcid)
    goto(tab)
    _dismiss_popup()
    goto(tab)
    if not find_item(item_substr):
        print(f"!! not found: {item_substr}")
        return
    time.sleep(0.4)
    radio = locate_radio_command(dump(), option_text, PROFILE["rid"]["radio_prefix"])
    if not radio:
        print(f"!! radio option not found: {option_text}")
        return
    x, y = center(radio["bounds"])
    tap(x, y, 0.5)
    adb("logcat", "-c")
    write = _btn_by_text(dump(), PROFILE["btn_labels"]["write"])
    x, y = center(write["bounds"])
    tap(x, y, 1.3)
    save(output / f"{step}_{item_substr[:10]}_post.xml", dump())
    lines = hook(output / f"{step}_{item_substr[:10]}_hook.log")
    read = _btn_by_text(dump(), PROFILE["btn_labels"]["read"])
    if read:
        x, y = center(read["bounds"])
        tap(x, y, 1.1)
    current = next(
        (
            node.get("text", "")
            for node in nodes(dump())
            if node.get("resource-id", "").endswith(PROFILE["rid"]["current_value"])
        ),
        None,
    )
    print(f"== RADIO {tcid} :: {item_substr} <- {option_text}")
    print(f"   readback current_value = {current!r}   Way2 hook lines = {len(lines)}")
    for line in lines[-6:]:
        print("   | " + line[-150:])


def cmd_mfield(
    tcid: str, tab: str, item_substr: str, fieldkey: str, value: str, step: str = "w"
) -> None:
    output = outdir(tcid)
    goto(tab)
    _dismiss_popup()
    goto(tab)
    if not find_item(item_substr):
        print(f"!! not found: {item_substr}")
        return
    time.sleep(0.4)
    rid = PROFILE["rid"]
    node_list: list[dict[str, str]] = []
    index = None
    edit = write = read = None
    for _ in range(8):
        node_list = nodes(dump())
        index, edit, write, read = locate_mfield_command(node_list, fieldkey, rid)
        if index is not None:
            break
        adb("shell", "input", "swipe", *PROFILE["swipe_detail_scroll"])
        time.sleep(0.7)
    if index is None:
        print(f"!! field not found: {fieldkey}")
        return
    x, y = center(edit["bounds"])
    tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 10))
    time.sleep(0.2)
    adb("shell", "input", "text", str(value))
    time.sleep(0.3)
    adb("shell", "input", "keyevent", "111")
    time.sleep(0.6)
    node_list = nodes(dump())
    index, _, write, read = locate_mfield_command(node_list, fieldkey, rid)
    adb("logcat", "-c")
    x, y = center(write["bounds"])
    tap(x, y, 1.3)
    save(output / f"{step}_{item_substr[:8]}_{fieldkey[:8]}_post.xml", dump())
    lines = hook(output / f"{step}_{item_substr[:8]}_{fieldkey[:8]}_hook.log")
    x, y = center(read["bounds"])
    tap(x, y, 1.1)
    node_list = nodes(dump())
    index, _, _, _ = locate_mfield_command(node_list, fieldkey, rid)
    text_value = next(
        (
            node.get("text", "")
            for node in node_list[index + 1 :]
            if node.get("resource-id", "").endswith(rid["text_value"])
        ),
        None,
    )
    print(f"== MFIELD {tcid} :: {item_substr}/{fieldkey} <- {value}")
    print(f"   readback textValue = {text_value!r}   Way2 hook lines = {len(lines)}")
    for line in lines[-6:]:
        print("   | " + line[-150:])


def _on_list() -> bool:
    return any(
        node.get("resource-id", "").endswith(PROFILE["rid"]["item_title"])
        for node in nodes(dump())
    )


def _back_to_list(tries: int = 4) -> bool:
    for _ in range(tries):
        xml_text = dump()
        if any(
            node.get("resource-id", "").endswith(PROFILE["rid"]["item_title"])
            for node in nodes(xml_text)
        ):
            return True
        back = next(
            (
                node
                for node in nodes(xml_text)
                if node.get("resource-id", "").endswith(PROFILE["rid"]["btn_back"])
            ),
            None,
        )
        if back:
            x, y = center(back["bounds"])
            tap(x, y, 0.8)
        else:
            adb("shell", "input", "keyevent", "4")
            time.sleep(0.8)
    return _on_list()


def _sess_text(output: Path, item_substr: str, value: object) -> str:
    if not find_item(item_substr):
        return f"!nf {item_substr}"
    rid = PROFILE["rid"]
    detail_map, _ = detail()
    if rid["et_detail_input"] not in detail_map:
        _back_to_list()
        return f"!not-text {item_substr}"
    x, y = center(detail_map[rid["et_detail_input"]]["bounds"])
    tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 16))
    time.sleep(0.3)
    adb("shell", "input", "text", encode_input_text(value))
    time.sleep(0.4)
    adb("shell", "input", "keyevent", "111")
    time.sleep(0.3)
    detail_map, _ = detail()
    write = detail_map.get(rid["btn_write"])
    adb("logcat", "-c")
    if write:
        x, y = center(write["bounds"])
        tap(x, y, 1.2)
    detail_map, _ = detail()
    readback = detail_map.get(rid["tv_detail_value"], {}).get("text", "")
    count = len(hook(output / f"cs_{item_substr[:12]}_hook.log"))
    _back_to_list()
    return f"{item_substr}={readback!r} (Way2 {count})"


def _sess_radio(output: Path, item_substr: str, option: str) -> str:
    if not find_item(item_substr):
        return f"!nf {item_substr}"
    radio = locate_radio_session(dump(), option, PROFILE["rid"]["radio_prefix"])
    if not radio:
        _back_to_list()
        return f"!no-opt {item_substr}/{option}"
    x, y = center(radio["bounds"])
    tap(x, y, 0.5)
    adb("logcat", "-c")
    write = _btn_by_text(dump(), PROFILE["btn_labels"]["write"])
    if write:
        x, y = center(write["bounds"])
        tap(x, y, 1.2)
    count = len(hook(output / f"cs_{item_substr[:12]}_hook.log"))
    read = _btn_by_text(dump(), PROFILE["btn_labels"]["read"])
    if read:
        x, y = center(read["bounds"])
        tap(x, y, 1.0)
    current = next(
        (
            node.get("text", "")
            for node in nodes(dump())
            if node.get("resource-id", "").endswith(PROFILE["rid"]["current_value"])
        ),
        None,
    )
    _back_to_list()
    return f"{item_substr}={current!r} (Way2 {count})"


def _sess_toggle(output: Path, item_substr: str, want: str | None = None) -> str:
    if not find_item(item_substr):
        return f"!nf {item_substr}"
    rid = PROFILE["rid"]

    def current() -> str:
        return next(
            (
                node.get("text", "")
                for node in nodes(dump())
                if node.get("resource-id", "").endswith(rid["tv_detail_value"])
            ),
            "",
        )

    read = _btn_by_text(dump(), PROFILE["btn_labels"]["read"])
    if read:
        x, y = center(read["bounds"])
        tap(x, y, 1.0)
    before = current()
    count = 0
    if toggle_write_needed(before, want):
        adb("logcat", "-c")
        write = next(
            (
                node
                for node in nodes(dump())
                if node.get("resource-id", "").endswith(rid["btn_write"])
            ),
            None,
        )
        if write:
            x, y = center(write["bounds"])
            tap(x, y, 1.2)
        count = len(hook(output / f"cs_{item_substr[:12]}_hook.log"))
        read = _btn_by_text(dump(), PROFILE["btn_labels"]["read"])
        if read:
            x, y = center(read["bounds"])
            tap(x, y, 1.0)
    after = current()
    _back_to_list()
    return f"{item_substr}={after!r}(was {before!r}) (Way2 {count})"


def _sess_mfield(output: Path, item_substr: str, fieldkey: str, value: object) -> str:
    if not find_item(item_substr):
        return f"!nf {item_substr}"
    rid = PROFILE["rid"]
    index = None
    node_list: list[dict[str, str]] = []
    edit = None
    for _ in range(8):
        node_list = nodes(dump())
        index, edit, _, _ = locate_mfield_session(node_list, fieldkey, rid)
        if index is not None:
            break
        adb("shell", "input", "swipe", *PROFILE["swipe_detail_scroll"])
        time.sleep(0.6)
    if index is None:
        _back_to_list()
        return f"!no-field {fieldkey}"
    x, y = center(edit["bounds"])
    tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 10))
    time.sleep(0.2)
    adb("shell", "input", "text", str(value))
    time.sleep(0.3)
    adb("shell", "input", "keyevent", "111")
    time.sleep(0.5)
    node_list = nodes(dump())
    index, _, write, _ = locate_mfield_session(node_list, fieldkey, rid)
    adb("logcat", "-c")
    x, y = center(write["bounds"])
    tap(x, y, 1.2)
    count = len(hook(output / f"cs_{item_substr[:8]}_{fieldkey[:10]}_hook.log"))
    node_list = nodes(dump())
    index, _, _, _ = locate_mfield_session(node_list, fieldkey, rid)
    text_value = (
        next(
            (
                node.get("text", "")
                for node in node_list[index + 1 :]
                if node.get("resource-id", "").endswith(rid["text_value"])
            ),
            None,
        )
        if index is not None
        else None
    )
    _back_to_list()
    return f"{item_substr}/{fieldkey}={text_value!r} (Way2 {count})"


def _device_ok() -> bool:
    connected = _connected()
    if not connected:
        print("ABORT: no adb device connected.")
        return False
    model = adb("shell", "getprop", "ro.product.model").stdout.strip()
    app_present = PROFILE["package"] in adb(
        "shell", "pm", "list", "packages", PROFILE["package"]
    ).stdout
    if not device_identity_ok(model, app_present, PROFILE):
        print(
            f"ABORT (wrong/absent target): active={DEV} model={model!r} "
            f"engineer_app={app_present} (expected {PROFILE['expect_model']} + "
            f"{PROFILE['package']}). Target 연결 확인 후 재시도 (preflight 권장)."
        )
        return False
    return True


def cmd_caseset(tcid: str) -> None:
    if tcid not in CASES:
        print("unknown case. known:", list(CASES))
        return
    if not _device_ok():
        return
    tab, items = CASES[tcid]
    output = outdir(tcid)
    goto(tab)
    _dismiss_popup()
    if not _on_list():
        goto(tab)
    print(f"== CASESET {tcid} ({tab}) — {len(items)} settings in ONE app session (Way2 hook per item)")
    for item_substr, kind, value in items:
        if kind == "text":
            result = _sess_text(output, item_substr, value)
        elif kind == "radio":
            result = _sess_radio(output, item_substr, value)
        elif kind == "toggle":
            result = _sess_toggle(output, item_substr, value)
        elif kind.startswith("mfield:"):
            result = _sess_mfield(output, item_substr, kind.split(":", 1)[1], value)
        else:
            result = f"!badkind {kind}"
        print("   -", result)
        if not _on_list():
            _back_to_list()
    print(f"   (per-item Way2 hooks -> {output}/cs_*_hook.log)")


def cmd_preflight() -> str | None:
    output = outdir("_session")
    connected = _connected()
    if not connected:
        print("PREFLIGHT ABORT: no adb device connected.")
        return None
    default = os.environ.get("ENG_DEV", PROFILE["default_serial"])
    if DEV not in connected:
        print(f"PREFLIGHT: default target {default} not connected — using {DEV} (connected: {connected})")

    def getprop(name: str) -> str:
        return adb("shell", "getprop", name).stdout.strip()

    model = getprop("ro.product.model")
    app_present = PROFILE["package"] in adb(
        "shell", "pm", "list", "packages", PROFILE["package"]
    ).stdout
    if not device_identity_ok(model, app_present, PROFILE):
        print(
            f"WRONG DEVICE: active={DEV} model={model!r} engineer_app={app_present} "
            f"(expected {PROFILE['expect_model']} + {PROFILE['package']}). "
            "caseset/call 실행 전 단말 확인 필요."
        )
    registry = adb("shell", "dumpsys", "telephony.registry").stdout

    def grep1(pattern: str) -> str:
        matches = [re.search(pattern, line) for line in registry.splitlines()]
        return next((match.group(0) for match in matches if match), "?")

    boot = adb("shell", "cat", "/proc/sys/kernel/random/boot_id").stdout.strip()
    modem_spec = pull_spec_for_extension(PROFILE, ".qmdl")
    qmdl = (
        pick_latest(adb("shell", "ls", "-t", modem_spec[0]).stdout, modem_spec[1])
        if modem_spec
        else None
    )
    info = (
        f"PREFLIGHT model={getprop('ro.product.model')} build={getprop('ro.build.version.incremental')} "
        f"carrier_sim={getprop('gsm.sim.operator.alpha')} carrier_net={getprop('gsm.operator.alpha')} "
        f"rat={grep1(r'getRilVoiceRadioTechnology=[0-9]+\([A-Z]+\)')} "
        f"ims={grep1(r'availableServices=\[[A-Z,]*\]')} boot_id={boot} qmdl={qmdl}"
    )
    print(info)
    with (output / "preflight.txt").open("a", encoding="utf-8") as stream:
        stream.write(info + "\n")
    return getprop("gsm.operator.alpha")


def cmd_capture(tcid: str, tag: str = "cap", want: str = "reg", timeout: str = "60") -> None:
    if not _device_ok():
        return
    output = outdir(tcid)
    polls = max(1, int(timeout) // 3)
    reached = want == "any"
    for _ in range(polls):
        registry = adb("shell", "dumpsys", "telephony.registry").stdout
        if capture_gate_reached(registry, want):
            reached = True
            break
        time.sleep(3)
    if not reached:
        print(
            f"   WARN: want={want} not reached (timeout {timeout}s); pull continues but may be early/partial."
        )
    cmd_pull(tcid, tag)
    carrier = adb("shell", "getprop", "gsm.operator.alpha").stdout.strip()
    utc = adb("shell", "date", "-u", "+%Y-%m-%d %H:%M:%S").stdout.strip()
    line = f"capture {tag}: carrier={carrier} utc={utc} want={want}"
    with (output / f"capture_{tag}.txt").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
    print("  " + line)


def cmd_state() -> None:
    registry = adb("shell", "dumpsys", "telephony.registry").stdout
    for keyword in ("getRilVoiceRadioTechnology", "mVoiceRegState", "VOICE,SMS"):
        for line in registry.splitlines():
            if keyword in line:
                print("  ", line.strip()[:160])
                break


# ---- CLI -------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="ODIN2_ENG_V1", choices=sorted(PROFILES))
    parser.add_argument("--out-root", help="evidence root; relative paths resolve from repo root")
    parser.add_argument("--run-label", default=time.strftime("RUN_%Y%m%d"))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="render a caseset without adb access")
    p.add_argument("tcid")
    p = sub.add_parser("caseset")
    p.add_argument("tcid")
    sub.add_parser("preflight")
    p = sub.add_parser("capture")
    p.add_argument("tcid")
    p.add_argument("tag", nargs="?", default="cap")
    p.add_argument("want", nargs="?", choices=("reg", "call", "any"), default="reg")
    p.add_argument("timeout", nargs="?", default="60")
    p = sub.add_parser("read")
    p.add_argument("tcid")
    p.add_argument("tab")
    p.add_argument("item")
    p.add_argument("step", nargs="?", default="r")
    p = sub.add_parser("write")
    p.add_argument("tcid")
    p.add_argument("tab")
    p.add_argument("item")
    p.add_argument("value")
    p.add_argument("step", nargs="?", default="w")
    p = sub.add_parser("radio")
    p.add_argument("tcid")
    p.add_argument("tab")
    p.add_argument("item")
    p.add_argument("option")
    p.add_argument("step", nargs="?", default="w")
    p = sub.add_parser("mfield")
    p.add_argument("tcid")
    p.add_argument("tab")
    p.add_argument("item")
    p.add_argument("fieldkey")
    p.add_argument("value")
    p.add_argument("step", nargs="?", default="w")
    sub.add_parser("reboot")
    p = sub.add_parser("pull")
    p.add_argument("tcid")
    p.add_argument("tag", nargs="?", default="")
    sub.add_parser("state")
    return parser


def _print_plan(profile: dict, casesets: dict, tcid: str) -> None:
    rows = render_plan(profile, casesets, tcid)
    print(f"PROFILE {PROFILE_NAME} | CASESET {tcid} | {len(rows)} actions | adb=OFF")
    for row in rows:
        print(
            f"{row['index']:02d}. tab={row['tab']} item={row['item']!r} "
            f"kind={row['kind']} value={row['value']!r} target={row['target']}"
        )


def main(argv: list[str] | None = None) -> int:
    global PROFILE_NAME, PROFILE, CASES
    args = _parser().parse_args(argv)
    PROFILE_NAME = args.profile
    PROFILE = PROFILES[args.profile]
    CASES = CASESETS[args.profile]
    errors = validate_profile(PROFILE)
    if errors:
        print("profile error: " + "; ".join(errors), file=sys.stderr)
        return 2

    # plan is intentionally dispatched before device resolution: adb access is forbidden.
    if args.command == "plan":
        try:
            _print_plan(PROFILE, CASES, args.tcid)
        except ValueError as exc:
            print(f"plan error: {exc}", file=sys.stderr)
            return 2
        return 0

    try:
        _configure(args.profile, args.out_root, args.run_label)
    except ValueError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    dispatch = {
        "caseset": lambda: cmd_caseset(args.tcid),
        "preflight": cmd_preflight,
        "capture": lambda: cmd_capture(args.tcid, args.tag, args.want, args.timeout),
        "read": lambda: cmd_read(args.tcid, args.tab, args.item, args.step),
        "write": lambda: cmd_write(args.tcid, args.tab, args.item, args.value, args.step),
        "radio": lambda: cmd_radio(args.tcid, args.tab, args.item, args.option, args.step),
        "mfield": lambda: cmd_mfield(
            args.tcid, args.tab, args.item, args.fieldkey, args.value, args.step
        ),
        "reboot": cmd_reboot,
        "pull": lambda: cmd_pull(args.tcid, args.tag),
        "state": cmd_state,
    }
    dispatch[args.command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
