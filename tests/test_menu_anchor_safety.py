"""Task 1 — ActionSafety derive (menu-tree v1.2 sidecar).

Locks the physical-safety classification policy for TC steps and baseline
MenuElements. Pure, device-independent. See
docs/superpowers/plans/2026-06-05-menu-tree-v1_2-tdd-plan.md (Task 1).
"""
from __future__ import annotations

import ast
import inspect

import pytest

from src import menu_anchor as ma
from src import menu_tree as mt


def _node(**kw):
    base = {"text": "", "content-desc": "", "class": "", "resource-id": "",
            "clickable": "false", "focusable": "false", "checkable": "false",
            "inherited_clickable": "false", "inherited_focusable": "false", "bounds": ""}
    base.update(kw)
    return base


def _safety(step):
    return ma.classify_step(step).safety


# --- enum surface ----------------------------------------------------------

def test_action_safety_has_eight_separated_members():
    names = {m.name for m in ma.ActionSafety}
    assert names == {
        "READ_ONLY", "READ_ONLY_SHELL", "NAVIGATION_ONLY", "SELECTION_GATED",
        "INPUT_REQUIRED", "DESTRUCTIVE", "PRIVILEGED_SHELL", "UNKNOWN_UNSAFE",
    }


# --- step: read-only (non-shell observation) -------------------------------

@pytest.mark.parametrize("action", ["verify_text", "wait", "screenshot",
                                    "verify_gone", "verify_content_desc",
                                    "verify_focus_moved"])
def test_nonshell_observation_is_read_only(action):
    assert _safety({"action": action}) is ma.ActionSafety.READ_ONLY


# --- step: read-only shell vs privileged/destructive shell -----------------

@pytest.mark.parametrize("command", [
    "getprop ro.build.id",
    "dumpsys window",
    "logcat -d",
    "cmd package resolve-activity --brief com.android.settings",
    "settings get global airplane_mode_on",
    "settings list system",
    "pm list packages",
    "content query --uri content://telephony/carriers",
    "cat /sdcard/window_dump.xml",
    "uiautomator dump",
    "wm size",
])
def test_read_only_shell(command):
    assert _safety({"action": "shell", "command": command}) is ma.ActionSafety.READ_ONLY_SHELL


def test_verify_shell_with_read_command_is_read_only_shell():
    v = ma.classify_step({"action": "verify_shell", "command": "getprop ro.build.id"})
    assert v.safety is ma.ActionSafety.READ_ONLY_SHELL


@pytest.mark.parametrize("command", [
    "settings put global airplane_mode_on 1",
    "settings delete global airplane_mode_on",
    "svc wifi disable",
    "svc data enable",
    "pm grant com.x android.permission.CAMERA",
    "pm revoke com.x android.permission.CAMERA",
    "pm clear com.x",
    "pm install /data/local/tmp/a.apk",
    "pm uninstall com.x",
])
def test_privileged_shell(command):
    assert _safety({"action": "shell", "command": command}) is ma.ActionSafety.PRIVILEGED_SHELL


@pytest.mark.parametrize("command", [
    "reboot",
    "content delete --uri content://telephony/carriers --where _id=5",
    "content insert --uri content://telephony/carriers --bind name:s:x",
    "content update --uri content://telephony/carriers --bind apn:s:y",
])
def test_destructive_shell(command):
    assert _safety({"action": "shell", "command": command}) is ma.ActionSafety.DESTRUCTIVE


def test_am_start_shell_is_navigation_only():
    assert _safety({"action": "shell", "command": "am start -n com.android.settings/.Settings"}) \
        is ma.ActionSafety.NAVIGATION_ONLY


@pytest.mark.parametrize("command", [
    "frobnicate --foo",
    "magisk --install",
    "",
])
def test_unknown_shell_is_unknown_unsafe(command):
    assert _safety({"action": "shell", "command": command}) is ma.ActionSafety.UNKNOWN_UNSAFE


# --- step: key / key_sequence navigation vs selection vs unsafe ------------

@pytest.mark.parametrize("keycode", ["DPAD_DOWN", "KEYCODE_DPAD_UP", "BACK",
                                     "KEYCODE_BACK", "HOME"])
def test_navigation_key(keycode):
    assert _safety({"action": "key", "keycode": keycode}) is ma.ActionSafety.NAVIGATION_ONLY


def test_navigation_key_sequence_all_nav():
    step = {"action": "key_sequence", "keys": ["DPAD_DOWN", "DPAD_DOWN", "BACK"]}
    assert _safety(step) is ma.ActionSafety.NAVIGATION_ONLY


@pytest.mark.parametrize("keycode", ["DPAD_CENTER", "KEYCODE_ENTER", "ENTER"])
def test_selection_gated_key(keycode):
    assert _safety({"action": "key", "keycode": keycode}) is ma.ActionSafety.SELECTION_GATED


def test_key_sequence_with_center_is_selection_gated():
    step = {"action": "key_sequence", "keys": ["DPAD_DOWN", "DPAD_CENTER"]}
    assert _safety(step) is ma.ActionSafety.SELECTION_GATED


@pytest.mark.parametrize("keycode", ["KEYCODE_POWER", "CALL", "KEYCODE_ENDCALL",
                                     "KEYCODE_SOMETHING_NEW"])
def test_unsafe_or_unknown_key_is_unknown_unsafe(keycode):
    assert _safety({"action": "key", "keycode": keycode}) is ma.ActionSafety.UNKNOWN_UNSAFE


def test_key_field_fallback_used_when_keycode_absent():
    assert _safety({"action": "key", "key": "DPAD_LEFT"}) is ma.ActionSafety.NAVIGATION_ONLY


# --- step: taps / swipe / input / unknown ---------------------------------

@pytest.mark.parametrize("action", ["tap_text", "tap_id", "tap_xy", "tap_content_desc"])
def test_taps_are_selection_gated(action):
    assert _safety({"action": action}) is ma.ActionSafety.SELECTION_GATED


def test_swipe_is_navigation_only():
    assert _safety({"action": "swipe"}) is ma.ActionSafety.NAVIGATION_ONLY


def test_input_text_is_input_required():
    assert _safety({"action": "input_text", "text": "hello"}) is ma.ActionSafety.INPUT_REQUIRED


def test_unknown_action_is_unknown_unsafe():
    assert _safety({"action": "frobnicate"}) is ma.ActionSafety.UNKNOWN_UNSAFE


def test_manual_pause_is_selection_gated_distinct_from_unknown():
    # manual_pause mutates nothing itself, but gates on a human action ->
    # not READ_ONLY, and not UNKNOWN_UNSAFE (must stay distinct from a truly
    # unclassified action).
    verdict = ma.classify_step({"action": "manual_pause", "description": "remove SIM"})
    assert verdict.safety is ma.ActionSafety.SELECTION_GATED
    assert "manual" in verdict.reason.lower()


# --- element-based ---------------------------------------------------------

def test_element_input_is_input_required():
    el = mt.build_element(_node(**{"class": "android.widget.EditText", "focusable": "true"}), False)
    assert ma.classify_element(el).safety is ma.ActionSafety.INPUT_REQUIRED


@pytest.mark.parametrize("node", [
    {"class": "android.widget.Switch"},
    {"checkable": "true"},
])
def test_element_toggle_checkable_is_selection_gated(node):
    el = mt.build_element(_node(**node), False)
    assert ma.classify_element(el).safety is ma.ActionSafety.SELECTION_GATED


def test_element_denylist_is_unknown_unsafe_and_keeps_reason():
    el = mt.build_element(_node(**{"class": "android.widget.Switch"}), True)
    verdict = ma.classify_element(el)
    assert verdict.safety is ma.ActionSafety.UNKNOWN_UNSAFE
    assert "denylist" in verdict.reason


@pytest.mark.parametrize("node", [
    {"class": "android.widget.Button", "text": "OK", "clickable": "true"},
    {"text": "Wi-Fi"},
    {"text": "Network", "clickable": "true"},
])
def test_element_plain_read_is_read_only(node):
    el = mt.build_element(_node(**node), False)
    assert ma.classify_element(el).safety is ma.ActionSafety.READ_ONLY


# --- layering guard (production must not import mmi_converter / scripts) ----

def test_menu_anchor_does_not_import_mmi_converter_or_scripts():
    tree = ast.parse(inspect.getsource(ma))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [n.name for n in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    assert not any("mmi_converter" in m for m in modules), modules
    assert not any(m.split(".")[0] == "scripts" for m in modules), modules
