"""Host-only tests for scripts/eng_mode_runner.py."""
from __future__ import annotations

import ast
import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys

import pytest


_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "eng_mode_runner.py"
_FROZEN_PATH = _ROOT / "ODIN2 - Engineer IMS" / "run_complex_0617.py"


def _load(name: str = "eng_mode_runner"):
    spec = importlib.util.spec_from_file_location(name, _PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load()
P = R.PROFILES["ODIN2_ENG_V1"]


def _xml(*nodes: str) -> str:
    return "<hierarchy>" + "".join(nodes) + "</hierarchy>"


def _node(text="", rid="", bounds="[0,0][10,10]") -> str:
    return f'<node text="{text}" resource-id="{rid}" bounds="{bounds}" />'


def test_import_has_no_adb_side_effect(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("subprocess.run called during import")

    monkeypatch.setattr(subprocess, "run", forbidden)
    module = _load("eng_mode_runner_import_guard")
    assert module.DEV is None


def test_nodes_parses_plain_and_prefixed_xml():
    plain = _xml(_node("A"))
    assert R.nodes(plain)[0]["text"] == "A"
    assert R.nodes("UI dump complete\n" + plain)[0]["text"] == "A"


def test_nodes_without_hierarchy_returns_empty():
    assert R.nodes("not xml") == []


def test_center():
    assert R.center("[10,20][30,60]") == (20, 40)


def test_text_finder_exact_prevents_substring_match():
    xml = _xml(_node("Write all", "pkg:id/a"), _node("Write", "pkg:id/b"))
    assert R.find_text_node(xml, "Write", exact=True)["resource-id"].endswith("/b")
    assert R.find_text_node(xml, "Write")["resource-id"].endswith("/a")


def test_btn_by_text_requires_nonempty_resource_id():
    xml = _xml(_node("Write"), _node("Write", "pkg:id/write"))
    assert R._btn_by_text(xml, "Write")["resource-id"] == "pkg:id/write"


def test_item_locator_is_limited_to_item_title_rid():
    xml = _xml(
        _node("Domain", "pkg:id/other"),
        _node("IMS Domain", "pkg:id/tv_item_title"),
    )
    assert R.locate_item(xml, "Domain", "tv_item_title")["text"] == "IMS Domain"


def test_list_bottom_signature_only_uses_item_titles():
    xml = _xml(
        _node("A", "pkg:id/tv_item_title"),
        _node("ignored", "pkg:id/other"),
        _node("B", "pkg:id/tv_item_title"),
    )
    assert R.list_bottom_signature(xml, "tv_item_title") == "A|B"


def test_extract_detail_uses_split_tail_equality_not_endswith():
    xml = _xml(
        _node("yes", "pkg:id/tv_detail_value", "[1,2][3,4]"),
        _node("no", "pkg:id/not_tv_detail_value"),
    )
    assert R.extract_detail(xml, {"tv_detail_value"}) == {
        "tv_detail_value": {"text": "yes", "bounds": "[1,2][3,4]"}
    }


def test_extract_detail_covers_profile_detail_keys():
    keys = {
        "tv_detail_value",
        "tv_detail_status",
        "tv_top_title",
        "et_detail_input",
        "btn_read",
        "btn_write",
        "btn_reset",
        "btn_back",
    }
    xml = _xml(*[_node(key, f"pkg:id/{key}") for key in keys])
    assert set(R.extract_detail(xml, keys)) == keys


def test_radio_command_prefers_exact_text_before_substring():
    xml = _xml(
        _node("Default (H.264,H.265)", "pkg:id/rb_default"),
        _node("H.265", "pkg:id/rb_h265"),
    )
    assert R.locate_radio_command(xml, "H.265", "rb_")["resource-id"].endswith("rb_h265")


def test_radio_session_rid_mode_has_no_text_fallback():
    xml = _xml(_node("rb_missing", "pkg:id/rb_present"))
    assert R.locate_radio_session(xml, "rb_missing", "rb_") is None
    assert R.locate_radio_session(xml, "rb_present", "rb_")["text"] == "rb_missing"


def test_mfield_command_preserves_endswith_and_first_following_controls():
    rid = P["rid"]
    ns = [
        {"text": "speechStartPort", "resource-id": "pkg:id/row_textKey"},
        {"resource-id": "pkg:id/editValue", "bounds": "e1"},
        {"resource-id": "pkg:id/btnWrite", "bounds": "w1"},
        {"resource-id": "pkg:id/btnRead", "bounds": "r1"},
        {"resource-id": "pkg:id/editValue", "bounds": "e2"},
    ]
    index, edit, write, read = R.locate_mfield_command(ns, "speechStartPort", rid)
    assert index == 0
    assert (edit["bounds"], write["bounds"], read["bounds"]) == ("e1", "w1", "r1")


def test_mfield_session_preserves_endswith_matching():
    rid = P["rid"]
    ns = [
        {"text": "Timer_T1", "resource-id": "pkg:id/prefix_textKey"},
        {"resource-id": "pkg:id/prefix_editValue", "bounds": "e"},
        {"resource-id": "pkg:id/prefix_btnWrite", "bounds": "w"},
        {"resource-id": "pkg:id/prefix_btnRead", "bounds": "r"},
    ]
    index, edit, write, read = R.locate_mfield_session(ns, "Timer_T1", rid)
    assert index == 0
    assert (edit["bounds"], write["bounds"], read["bounds"]) == ("e", "w", "r")


def test_mfield_locator_distinguishes_duplicate_traffic_port_fieldkeys():
    rid = P["rid"]
    ns = [
        {"text": "speechStartPort", "resource-id": "pkg:id/textKey"},
        {"resource-id": "pkg:id/editValue", "bounds": "start"},
        {"text": "speechStopPort", "resource-id": "pkg:id/textKey"},
        {"resource-id": "pkg:id/editValue", "bounds": "stop"},
    ]
    assert R.locate_mfield_command(ns, "speechStartPort", rid)[0] == 0
    assert R.locate_mfield_command(ns, "speechStopPort", rid)[0] == 2


def test_parse_adb_devices_excludes_offline_and_unauthorized():
    stdout = (
        "List of devices attached\n"
        "good\tdevice product:x\n"
        "bad1\toffline\n"
        "bad2\tunauthorized\n"
    )
    assert R.parse_adb_devices(stdout) == ["good"]


@pytest.mark.parametrize(
    ("serials", "default", "chosen", "warn"),
    [
        (["target", "other"], "target", "target", False),
        (["sole"], "target", "sole", True),
        (["one", "two"], "target", "target", True),
        ([], "target", "target", True),
    ],
)
def test_resolve_device_branches(serials, default, chosen, warn):
    actual, message = R.resolve_device(serials, default)
    assert actual == chosen
    assert bool(message) is warn


def test_device_identity_predicate():
    assert R.device_identity_ok("AT-M150", True, P)
    assert not R.device_identity_ok("OTHER", True, P)
    assert not R.device_identity_ok("AT-M150", False, P)


@pytest.mark.parametrize(
    ("want", "text", "expected"),
    [
        ("any", "", True),
        ("reg", "availableServices=[VOICE,SMS]", True),
        ("reg", "availableServices=[SMS]", False),
        ("call", "mCallState=2", True),
        ("call", "mCallState=0", False),
    ],
)
def test_capture_gate_predicate(want, text, expected):
    assert R.capture_gate_reached(text, want) is expected


def test_hook_filter():
    lines = ["x TeleEngineer y", "plain", "QCRIL_JAVA z"]
    assert R.filter_hook_lines(lines, ("TeleEngineer", "QCRIL_JAVA")) == [lines[0], lines[2]]


def test_write_mismatch_abort_preserves_loosened_rule():
    assert not R.write_mismatch_abort("abc/def", "abc")
    assert not R.write_mismatch_abort("123456789", "123456")
    assert R.write_mismatch_abort("expected", "other")


def test_space_encoding_only_changes_spaces():
    assert R.encode_input_text("ALT test/value") == "ALT%stest/value"


def test_toggle_write_decision():
    assert R.toggle_write_needed("OFF", None)
    assert not R.toggle_write_needed("AUTO ANSWER ON", "on")
    assert R.toggle_write_needed("OFF", "ON")


def test_pick_latest_uses_ls_order():
    assert R.pick_latest("new.qmdl old.qmdl note.txt", ".qmdl") == "new.qmdl"
    assert R.pick_latest("note.txt", ".qmdl") is None


def test_pull_spec_lookup_allows_non_qmdl_profile():
    assert R.pull_spec_for_extension(P, ".qmdl") == (
        "/sdcard/ls_log/modem/",
        ".qmdl",
        "modem",
    )
    profile = dict(P, pull_specs=(("/sdcard/log/", ".txt", "main"),))
    assert R.pull_spec_for_extension(profile, ".qmdl") is None


def test_all_shipped_casesets_validate():
    cases = R.CASESETS["ODIN2_ENG_V1"]
    assert all(R.validate_caseset(P, cases, tcid) == [] for tcid in cases)


def test_frozen_casesets_remain_an_identical_subset():
    tree = ast.parse(_FROZEN_PATH.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "CASES" for target in node.targets)
    )
    frozen_cases = ast.literal_eval(assignment.value)
    current_cases = R.CASESETS["ODIN2_ENG_V1"]
    assert set(frozen_cases) <= set(current_cases)
    assert all(current_cases[tcid] == case for tcid, case in frozen_cases.items())


def test_render_plan_preserves_duplicate_traffic_port_rows_and_order():
    rows = R.render_plan(P, R.CASESETS["ODIN2_ENG_V1"], "CMB_IMS_SESSION")
    traffic = [row for row in rows if row["item"] == "Traffic Port"]
    assert [row["kind"] for row in traffic] == [
        "mfield:speechStartPort",
        "mfield:speechStopPort",
    ]
    assert [row["index"] for row in traffic] == [4, 5]


def test_plan_main_is_adb_free(monkeypatch, capsys):
    monkeypatch.setattr(R, "_connected", lambda: (_ for _ in ()).throw(AssertionError("adb")))
    assert R.main(["plan", "CMB_IMS_SESSION"]) == 0
    output = capsys.readouterr().out
    assert "adb=OFF" in output
    assert output.count("Traffic Port") == 2


def test_plan_unknown_case_is_clear_error(capsys):
    assert R.main(["plan", "NO_SUCH_CASE"]) == 2
    assert "unknown case: NO_SUCH_CASE" in capsys.readouterr().err


def test_profile_validation_catches_missing_keys_before_runtime():
    broken = dict(P)
    broken.pop("package")
    assert "missing profile key: package" in R.validate_profile(broken)


def test_render_plan_reports_profile_error_without_follow_on_keyerror():
    broken = dict(P)
    broken.pop("tabs")
    with pytest.raises(ValueError, match="missing profile key: tabs"):
        R.render_plan(broken, R.CASESETS["ODIN2_ENG_V1"], "CMB_IMS_SESSION")


def test_caseset_validator_rejects_malformed_outer_shape():
    assert R.validate_caseset(P, {"BAD": ("IMS",)}, "BAD") == [
        "case must be (tab, items)"
    ]


def test_output_root_is_repo_relative_unless_absolute(tmp_path):
    assert R.resolve_output_root(_ROOT, P, None) == _ROOT / "ODIN2 - Engineer IMS/log"
    absolute = tmp_path / "evidence"
    assert R.resolve_output_root(_ROOT, P, str(absolute)) == absolute


def test_profile_v1_matches_frozen_ast_assignments():
    tree = ast.parse(_FROZEN_PATH.read_text(encoding="utf-8"))
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert ast.literal_eval(assignments["APP"]) == P["package"]
    assert ast.literal_eval(assignments["EXPECT_MODEL"]) == P["expect_model"]
    default_call = assignments["_DEFAULT_DEV"]
    assert isinstance(default_call, ast.Call)
    assert ast.literal_eval(default_call.args[1]) == P["default_serial"]


def test_profile_v1_selectors_and_labels_exist_in_frozen_source():
    source = _FROZEN_PATH.read_text(encoding="utf-8")
    values = [
        P["activity"],
        P["gate_label"],
        *P["tabs"],
        *P["rid"].values(),
        *P["btn_labels"].values(),
        P["popup_dismiss_exact"],
        *P["reboot_popup_labels"],
        *(part for spec in P["pull_specs"] for part in spec[:2]),
        *P["hook_keywords"],
    ]
    assert all(str(value) in source for value in values)


def test_profile_v1_swipe_coordinates_match_frozen_ast():
    tree = ast.parse(_FROZEN_PATH.read_text(encoding="utf-8"))
    swipe_calls = {
        tuple(ast.literal_eval(arg) for arg in call.args[3:])
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "adb"
        and len(call.args) >= 8
        and all(isinstance(arg, ast.Constant) for arg in call.args[:3])
        and [arg.value for arg in call.args[:3]] == ["shell", "input", "swipe"]
    }
    assert P["swipe_reset"] == (360, 420, 360, 1100, 200)
    assert P["swipe_list_scroll"] == (360, 1000, 360, 420, 300)
    assert P["swipe_detail_scroll"] == (360, 1000, 360, 500, 300)
    assert P["swipe_reset"] in swipe_calls
    assert P["swipe_list_scroll"] in swipe_calls
    assert P["swipe_detail_scroll"] in swipe_calls


def test_text_callsite_contract_keeps_intentional_differences():
    command = inspect.getsource(R.cmd_write)
    session = inspect.getsource(R._sess_text)
    assert '["67"] * 16' in command and '["67"] * 16' in session
    assert '"111"' not in command and '"111"' in session
    assert "tap(x, y, 1.4)" in command and "tap(x, y, 1.2)" in session
    assert "write_mismatch_abort" in command and "write_mismatch_abort" not in session


def test_mfield_callsite_contract_keeps_intentional_differences():
    command = inspect.getsource(R.cmd_mfield)
    session = inspect.getsource(R._sess_mfield)
    assert '["67"] * 10' in command and '["67"] * 10' in session
    assert '"111"' in command and '"111"' in session
    assert "tap(x, y, 1.3)" in command
    assert "tap(x, y, 1.1)" in command
    assert "tap(x, y, 1.2)" in session


def test_radio_callsite_contract_keeps_button_pause_matrix():
    command = inspect.getsource(R.cmd_radio)
    session = inspect.getsource(R._sess_radio)
    assert "tap(x, y, 1.3)" in command and "tap(x, y, 1.1)" in command
    assert "tap(x, y, 1.2)" in session and "tap(x, y, 1.0)" in session
