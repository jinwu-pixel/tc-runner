from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
CHECK_PATH = REPO / "scripts" / "canonical_shell_rc_remediation_check.py"
MANIFEST_PATH = (
    REPO / "scripts" / "canonical_shell_rc_remediation_manifest_v1.json"
)
BASELINE_HEAD = "78b3ac34e9f8bacabe926172dd199342b7eb58c5"
TARGET_ROW_KEYS = [
    "ODIN2 - My gallary/functional/photo/GAL_FUNC_03_photo_multi_select.yaml#24",
    "ODIN2 - minifile/functional/trash/MNF_FUNC_27_trash_enter.yaml#11",
    "exported_ss_call/SS_TC01_permission_denied.yaml#10",
    "exported_ss_call/SS_TC01_permission_denied.yaml#11",
    "exported_ss_call/SS_TC02_permission_allow_idle.yaml#11",
    "exported_ss_call/SS_TC03_ringing_permission.yaml#15",
    "exported_ss_call/SS_TC04_offhook_seed_recovery.yaml#18",
    "exported_ss_call/SS_TC05_boundary_values.yaml#9",
    "exported_ss_call/SS_TC06_missed_rejected.yaml#10",
    "exported_ss_call/SS_TC06_missed_rejected.yaml#11",
    "exported_ss_call/SS_TC07_short_call_no_false_positive.yaml#9",
    "exported_ss_call/SS_TC09_offhook_permission_banking.yaml#20",
    "exported_ss_call/SS_TC0_P0_endcall_crash.yaml#15",
    "exported_ss_call/SS_TC0_P0_telebanking_offhook.yaml#24",
    "exported_ss_call/SS_TC10_permission_toggle.yaml#24",
    "exported_ss_call/SS_TC11_multi_subscription.yaml#20",
    "exported_ss_call/SS_TC11_multi_subscription.yaml#21",
    "exported_ss_call/SS_TC12_legacy_path.yaml#19",
]
RUNTIME_DISPOSITIONS = [
    (
        "ODIN2 - My gallary/functional/photo/"
        "GAL_FUNC_05_photo_multi_delete_trash_flow.yaml#23",
        "STATIC_ADJUDICATED_REQUIRE_ZERO",
    ),
    (
        "ODIN2 - My gallary/functional/photo/"
        "GAL_FUNC_12_photo_edit_save_copy.yaml#18",
        "STATIC_ADJUDICATED_REQUIRE_ZERO",
    ),
    (
        "ODIN2 - My gallary/functional/video/"
        "GAL_FUNC_16_video_orientation.yaml#8",
        "STATIC_ADJUDICATED_OBSERVE_ONLY",
    ),
    (
        "ODIN2 - minifile/functional/ops/MNF_FUNC_12_ops_rename.yaml#22",
        "CORPUS_DESIGN_REQUIRED",
    ),
    (
        "exported_tc1/BUG_25175_LGU_APN_menu.yaml#75",
        "DEVICE_EVIDENCE_REQUIRED",
    ),
    (
        "exported_tc1/BUG_5426_airplane_reboot_apn.yaml#15",
        "DEVICE_EVIDENCE_REQUIRED",
    ),
]


def load_check_module():
    spec = importlib.util.spec_from_file_location(
        "canonical_shell_rc_remediation_check_for_tests", CHECK_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_module_exists() -> None:
    assert CHECK_PATH.is_file()


def _manifest() -> dict:
    assert MANIFEST_PATH.is_file(), "remediation manifest is absent"
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_from_git(head: str, path: str) -> dict:
    completed = subprocess.run(
        ["git", "show", f"{head}:{path}"],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    value = yaml.safe_load(completed.stdout.decode("utf-8"))
    assert isinstance(value, dict)
    return value


def _baseline_documents(manifest: dict) -> dict[str, dict]:
    return {
        path: _load_from_git(BASELINE_HEAD, path)
        for path in dict.fromkeys(target["source_path"] for target in manifest["targets"])
    }


def _remediated_documents(check, manifest: dict) -> dict[str, dict]:
    documents = _baseline_documents(manifest)
    for target in manifest["targets"]:
        step = documents[target["source_path"]]["steps"][target["step_index"] - 1]
        step["action"] = "verify_shell"
        step["command"] = check.render_command(target)
        step["expected"] = target["sentinel"]
    return documents


def _load_provenance_tests():
    path = REPO / "tests" / "test_provenance_manifest.py"
    spec = importlib.util.spec_from_file_location(
        "provenance_gate_for_remediation_tests", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_contract_and_semantic_identities_are_exact() -> None:
    check = load_check_module()
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    assert list(manifest) == [
        "baseline",
        "runtime_review_dispositions",
        "schema_version",
        "semantic_identity",
        "subject",
        "targets",
    ]
    assert manifest["schema_version"] == 1
    assert manifest["subject"] == "canonical shell-rc blocker remediation"
    assert [target["row_key"] for target in manifest["targets"]] == TARGET_ROW_KEYS
    assert [
        (row["row_key"], row["disposition"])
        for row in manifest["runtime_review_dispositions"]
    ] == RUNTIME_DISPOSITIONS
    assert manifest["semantic_identity"] == {
        "runtime_review_dispositions_sha256": check.canonical_json_sha256(
            manifest["runtime_review_dispositions"]
        ),
        "targets_sha256": check.canonical_json_sha256(manifest["targets"]),
    }
    assert MANIFEST_PATH.read_bytes().endswith(b"\n")
    assert b"\r\n" not in MANIFEST_PATH.read_bytes()


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_root",
        "missing_root",
        "duplicate_target",
        "path_traversal",
        "baseline_hash",
        "semantic_hash",
        "pattern_quote",
        "pattern_newline",
        "pattern_nul",
        "renderer_kind",
        "predicate_kind",
        "predicate_value",
    ],
)
def test_manifest_loader_rejects_contract_mutations(
    tmp_path: Path, mutation: str
) -> None:
    check = load_check_module()
    value = _manifest()
    if mutation == "unknown_root":
        value["extra"] = True
    elif mutation == "missing_root":
        del value["subject"]
    elif mutation == "duplicate_target":
        value["targets"][1] = copy.deepcopy(value["targets"][0])
    elif mutation == "path_traversal":
        value["targets"][0]["source_path"] = "../escape.yaml"
    elif mutation == "baseline_hash":
        value["targets"][0]["baseline_command_sha256"] = "0" * 64
    elif mutation == "semantic_hash":
        value["semantic_identity"]["targets_sha256"] = "0" * 64
    elif mutation == "pattern_quote":
        value["targets"][0]["grep_pattern"] = "bad'quote"
    elif mutation == "pattern_newline":
        value["targets"][0]["grep_pattern"] = "bad\npattern"
    elif mutation == "pattern_nul":
        value["targets"][0]["grep_pattern"] = "bad\0pattern"
    elif mutation == "renderer_kind":
        value["targets"][0]["renderer_kind"] = "free_form"
    elif mutation == "predicate_kind":
        value["targets"][0]["predicate_kind"] = "NE_0"
    elif mutation == "predicate_value":
        value["targets"][0]["predicate_value"] = 1
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(check.InputInvalid):
        check.load_and_validate_manifest(path)


def test_sentinel_algorithm_is_stable_and_unique() -> None:
    check = load_check_module()
    assert check.sentinel_for(TARGET_ROW_KEYS[0].rsplit("#", 1)[0], 24) == (
        "__TC_ASSERT_OK_a22abbba8627__"
    )
    assert check.sentinel_for(TARGET_ROW_KEYS[1].rsplit("#", 1)[0], 11) == (
        "__TC_ASSERT_OK_dba44bf7c584__"
    )
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    sentinels = [target["sentinel"] for target in manifest["targets"]]
    assert len(sentinels) == len(set(sentinels)) == 18


@pytest.mark.parametrize(
    ("source_rc", "grep_rc", "count_text", "kind", "value", "ok"),
    [
        (1, 0, "0", "EQ_0", 0, False),
        (0, 2, "0", "EQ_0", 0, False),
        (0, 1, "", "EQ_0", 0, False),
        (0, 1, "x", "EQ_0", 0, False),
        (0, 1, "0", "EQ_0", 0, True),
        (0, 0, "1", "EQ_0", 0, False),
        (0, 0, "1", "EQ_1", 1, True),
        (0, 1, "0", "EQ_1", 1, False),
        (0, 0, "1", "LE_1", 1, True),
        (0, 0, "2", "LE_1", 1, False),
    ],
)
def test_evaluate_count_truth_table(
    source_rc: int,
    grep_rc: int,
    count_text: str,
    kind: str,
    value: int,
    ok: bool,
) -> None:
    check = load_check_module()
    actual, _ = check.evaluate_count(
        source_rc=source_rc,
        grep_rc=grep_rc,
        count_text=count_text,
        predicate_kind=kind,
        predicate_value=value,
    )
    assert actual is ok


@pytest.mark.parametrize(
    ("args", "diagnostic"),
    [
        ((7, 0, "0", "EQ_0", 0), "TC_ASSERT_SOURCE_RC=7"),
        ((0, 2, "0", "EQ_0", 0), "TC_ASSERT_GREP_RC=2"),
        ((0, 1, "x", "EQ_0", 0), "TC_ASSERT_COUNT_INVALID=x"),
        ((0, 0, "1", "EQ_0", 0), "TC_ASSERT_COUNT=1 EXPECTED=count==0"),
        ((0, 0, "0", "EQ_1", 1), "TC_ASSERT_COUNT=0 EXPECTED=count==1"),
        ((0, 0, "2", "LE_1", 1), "TC_ASSERT_COUNT=2 EXPECTED=count<=1"),
    ],
)
def test_evaluate_count_diagnostics(
    args: tuple[int, int, str, str, int], diagnostic: str
) -> None:
    check = load_check_module()
    assert check.evaluate_count(*args) == (False, diagnostic)


def test_evaluate_count_success_has_no_diagnostic() -> None:
    check = load_check_module()
    assert check.evaluate_count(0, 1, "0", "EQ_0", 0) == (True, "")


def test_renderer_is_fail_closed_and_preserves_operation_order() -> None:
    check = load_check_module()
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    for target in manifest["targets"]:
        command = check.render_command(target)
        assert target["sentinel"] in command
        assert command.count(target["sentinel"]) == 1
        assert "/data/local/tmp/tc_runner_rc_" in command
        assert "_$$." in command
        assert "/sdcard" not in command
        assert "|| echo 0" not in command
        assert f"{target['source_command']} | grep" not in command
        markers = [
            "tmp=",
            "pre_cleanup_rc=$?",
            "source_rc=$?",
            "grep_rc=$?",
            "TC_ASSERT_COUNT_INVALID=",
            "TC_ASSERT_COUNT=",
            target["sentinel"],
        ]
        positions = [command.index(marker) for marker in markers]
        assert positions == sorted(positions)
        assert "TC_ASSERT_SOURCE_RC=$source_rc" in command
        assert "TC_ASSERT_GREP_RC=$grep_rc" in command
        assert "exit \"$source_rc\"" in command
        assert "exit \"$grep_rc\"" in command
        assert "TC_ASSERT_CLEANUP_RC=$cleanup_rc" in command
        assert command.count("cleanup_rc=$?") >= 4
        if target["renderer_kind"] == "uiautomator_dump_count":
            assert 'uiautomator dump "$tmp" >/dev/null 2>&1' in command
        else:
            assert f'{target["source_command"]} >"$tmp"' in command


def test_renderer_uses_bounded_unique_scratch_and_cleans_every_exit_path() -> None:
    check = load_check_module()
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    for target in manifest["targets"]:
        command = check.render_command(target)
        suffix = target["sentinel"].removeprefix(
            "__TC_ASSERT_OK_"
        ).removesuffix("__")
        extension = (
            "xml"
            if target["renderer_kind"] == "uiautomator_dump_count"
            else "txt"
        )
        assert command.startswith(
            f'tmp="/data/local/tmp/tc_runner_rc_{suffix}_$$.{extension}"; '
            'rm -f "$tmp"; pre_cleanup_rc=$?'
        )
        assert command.count('rm -f "$tmp"') == 6
        assert command.count("cleanup_rc=$?") == 6
        for primary in ("source_rc", "grep_rc"):
            assert (
                'rm -f "$tmp"; cleanup_rc=$?; '
                'if [ "$cleanup_rc" -ne 0 ]; then '
                'echo "TC_ASSERT_CLEANUP_RC=$cleanup_rc" >&2; fi; '
                f'exit "${primary}"'
            ) in command
        assert command.count('exit "$primary_rc"') == 2
        assert command.rfind('rm -f "$tmp"') < command.rfind(target["sentinel"])


def test_live_safety_transition_is_explicit_and_execution_metadata_is_unchanged() -> None:
    from src import execution_contract, menu_anchor

    manifest = _manifest()
    baseline = _baseline_documents(manifest)
    current = {
        path: yaml.safe_load((REPO / path).read_text(encoding="utf-8"))
        for path in baseline
    }
    transitions = []
    for target in manifest["targets"]:
        path = target["source_path"]
        index = target["step_index"] - 1
        before = menu_anchor.classify_step(baseline[path]["steps"][index])
        after = menu_anchor.classify_step(current[path]["steps"][index])
        if (
            path.startswith("exported_ss_call/")
            and before.safety != after.safety
        ):
            transitions.append((before.safety, after.safety))

    assert transitions == [
        (
            menu_anchor.ActionSafety.READ_ONLY_SHELL,
            menu_anchor.ActionSafety.UNKNOWN_UNSAFE,
        )
    ] * 16
    assert {
        menu_anchor.safety_to_automation_class(before):
        menu_anchor.safety_to_automation_class(after)
        for before, after in transitions
    } == {"FULL_AUTO": "MANUAL_REQUIRED"}

    for path in baseline:
        before_metadata = execution_contract.derive_execution_metadata(
            baseline[path]["steps"]
        )
        after_metadata = execution_contract.derive_execution_metadata(
            current[path]["steps"]
        )
        assert after_metadata == before_metadata
        for key in ("execution_type", "manual_detail"):
            assert current[path]["metadata"][key] == baseline[path]["metadata"][key]

    execution_source = (REPO / "src" / "execution_contract.py").read_text(
        encoding="utf-8"
    )
    assert "menu_anchor" not in execution_source
    assert "ActionSafety" not in execution_source


def test_live_anchor_audit_records_the_accepted_safety_totals() -> None:
    path = REPO / "scripts" / "anchor_corpus_audit.py"
    spec = importlib.util.spec_from_file_location("anchor_audit_v5_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.audit_corpus(
        REPO,
        baseline_path=(
            REPO
            / "THOR2_K - Settings"
            / "catalog"
            / "menu_tree_baseline_20260604T102316Z.json"
        ),
    )
    assert result["action_safety"]["READ_ONLY_SHELL"] == 112
    assert result["action_safety"]["UNKNOWN_UNSAFE"] == 107


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("grep_pattern", "bad'quote"),
        ("grep_pattern", "bad\npattern"),
        ("grep_pattern", "bad\0pattern"),
        ("source_command", "logcat -d | grep bad"),
        ("renderer_kind", "shell_template"),
        ("predicate_kind", "NE_0"),
    ],
)
def test_renderer_rejects_unsafe_or_unsupported_inputs(
    field: str, value: str
) -> None:
    check = load_check_module()
    target = copy.deepcopy(_manifest()["targets"][0])
    target[field] = value
    with pytest.raises(check.InputInvalid):
        check.render_command(target)


def test_candidate_comparison_accepts_only_rendered_target_triples() -> None:
    check = load_check_module()
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    baseline = _baseline_documents(manifest)
    candidate = _remediated_documents(check, manifest)
    result = check.compare_candidate_documents(baseline, candidate, manifest)
    assert result == {
        "non_target_mutations": 0,
        "remediated_targets": 18,
        "target_violations": [],
    }


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("action", "TARGET_ACTION"),
        ("command", "TARGET_COMMAND"),
        ("expected", "TARGET_EXPECTED"),
        ("description", "TARGET_NON_PROJECTION"),
        ("non_target", "NON_TARGET_MUTATION"),
    ],
)
def test_candidate_comparison_rejects_target_and_non_target_mutations(
    mutation: str, expected_code: str
) -> None:
    check = load_check_module()
    manifest = check.load_and_validate_manifest(MANIFEST_PATH)
    baseline = _baseline_documents(manifest)
    candidate = _remediated_documents(check, manifest)
    target = manifest["targets"][0]
    step = candidate[target["source_path"]]["steps"][target["step_index"] - 1]
    if mutation in {"action", "command", "expected"}:
        step[mutation] = "mutated"
    elif mutation == "description":
        step["description"] = "mutated"
    else:
        candidate[target["source_path"]]["steps"][0]["description"] = "mutated"
    result = check.compare_candidate_documents(baseline, candidate, manifest)
    assert expected_code in {row["code"] for row in result["target_violations"]}


def test_p2_transition_is_red_then_green_without_identity_drift(
    tmp_path: Path,
) -> None:
    check = load_check_module()
    gates = _load_provenance_tests()
    remediation = check.load_and_validate_manifest(MANIFEST_PATH)
    old_p2 = _load_from_git(
        "HEAD", "provenance/ss_call_shell_rc_manifest.yaml"
    )
    candidate_p2 = copy.deepcopy(old_p2)
    baseline = _baseline_documents(remediation)
    overrides: dict[str, Path] = {}
    for mapping in old_p2["mappings"]:
        path = tmp_path / f"{len(overrides)}.yaml"
        path.write_text(
            yaml.safe_dump(
                baseline[mapping["yaml_path"]],
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        overrides[mapping["yaml_path"]] = path
    gates._validate_g4(old_p2, overrides)

    target = next(
        row for row in remediation["targets"] if row["provenance"]["mode"] == "p2_manifest"
    )
    changed = copy.deepcopy(baseline[target["source_path"]])
    changed_step = changed["steps"][target["step_index"] - 1]
    changed_step.update(
        action="verify_shell",
        command=check.render_command(target),
        expected=target["sentinel"],
    )
    overrides[target["source_path"]].write_text(
        yaml.safe_dump(changed, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        gates._validate_g4(old_p2, overrides)

    mapping = next(
        row for row in candidate_p2["mappings"] if row["yaml_path"] == target["source_path"]
    )
    binding = next(
        row for row in mapping["blocker_bindings"]
        if row["blocker_step_index"] == target["step_index"]
    )
    binding["step_projection"] = {
        "action": "verify_shell",
        "command": check.render_command(target),
        "expected": target["sentinel"],
    }
    gates._validate_g1(candidate_p2)
    gates._validate_g4(candidate_p2, overrides)

    bad_origin = copy.deepcopy(candidate_p2)
    bad_origin["origin"]["verdict"] = "GREEN"
    with pytest.raises(AssertionError):
        gates._validate_g5(bad_origin)
    bad_selector = copy.deepcopy(candidate_p2)
    bad_selector["mappings"][0]["source_selectors"].pop()
    with pytest.raises(AssertionError):
        gates._validate_g1(bad_selector)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


def test_repository_identity_detects_index_and_untracked_drift(
    tmp_path: Path,
) -> None:
    check = load_check_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    tracked = repo / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "--", "tracked.txt")
    _git(repo, "commit", "-m", "baseline")
    untracked = repo / "asset.txt"
    untracked.write_text("one\n", encoding="utf-8")
    before = check.snapshot_repository_identity(repo)
    untracked.write_text("two\n", encoding="utf-8")
    after_content = check.snapshot_repository_identity(repo)
    assert before["untracked"] != after_content["untracked"]
    untracked.unlink()
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    after_replace = check.snapshot_repository_identity(repo)
    assert before["untracked"] != after_replace["untracked"]
    tracked.write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "--", "tracked.txt")
    after_index = check.snapshot_repository_identity(repo)
    assert before["index"] != after_index["index"]


def test_repository_scope_accepts_only_capsule_bound_continuation_bytes(
    tmp_path: Path,
) -> None:
    """Catches a v3 capsule check that trusts only a dirty pathname."""

    check = load_check_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    target = repo / ".gitattributes"
    target.write_bytes(b"baseline\n")
    _git(repo, "add", "--", ".gitattributes")
    _git(repo, "commit", "-m", "baseline")
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/master", head)
    changed = b"continuation\n"
    target.write_bytes(changed)
    rows = [
        {
            "git_blob_no_filters": hashlib.sha1(
                f"blob {len(changed)}\0".encode("ascii") + changed
            ).hexdigest(),
            "path": ".gitattributes",
            "raw_sha256": hashlib.sha256(changed).hexdigest(),
        }
    ]
    tracked_worktree = {
        "count": 1,
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "rows": rows,
    }
    identity = check.snapshot_repository_identity(repo)
    capsule = {
        "schema_version": 3,
        "repo": {"head_sha": head, "upstream_sha": head},
        "index": identity["index"],
        "untracked": {
            key: identity["untracked"][key]
            for key in ("count", "canonical_json_sha256")
        },
        "ignored": {
            key: identity["ignored"][key]
            for key in ("count", "canonical_json_sha256")
        },
        "tracked_worktree": tracked_worktree,
    }

    assert identity["tracked_worktree"] == tracked_worktree
    check._require_repo_scope(repo, capsule, identity)

    target.write_bytes(b"drift\n")
    drifted = check.snapshot_repository_identity(repo)
    with pytest.raises(check.InputInvalid, match="tracked worktree"):
        check._require_repo_scope(repo, capsule, drifted)


def test_repository_scope_v4_ignores_outside_and_rejects_inside_scope_drift(
    tmp_path: Path,
) -> None:
    """Catches the Task 6 consumer re-expanding a scoped capsule to full state."""

    check = load_check_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    tracked = repo / ".gitattributes"
    tracked.write_bytes(b"baseline\n")
    _git(repo, "add", "--", ".gitattributes")
    _git(repo, "commit", "-m", "baseline")
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/master", head)
    tracked.write_bytes(b"continuation\n")
    scoped = repo / "scoped.txt"
    scoped.write_bytes(b"scoped\n")
    outside = repo / "outside.txt"
    outside.write_bytes(b"outside\n")
    selector_payload = {
        "exact_paths": ["scoped.txt"],
        "prefixes": [],
        "scope_version": 1,
    }
    scope = {
        **selector_payload,
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(
                selector_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }
    identity = check.snapshot_repository_identity(
        repo,
        invariant_scope=scope,
    )
    capsule = {
        "schema_version": 4,
        "repo": {"head_sha": head, "upstream_sha": head},
        "index": identity["index"],
        "untracked": identity["untracked"],
        "ignored": identity["ignored"],
        "tracked_worktree": identity["tracked_worktree"],
        "invariant_scope": scope,
    }

    check._require_repo_scope(repo, capsule, identity)

    outside.write_bytes(b"outside drift\n")
    outside_drift = check.snapshot_repository_identity(
        repo,
        invariant_scope=scope,
    )
    check._require_repo_scope(repo, capsule, outside_drift)

    scoped.write_bytes(b"scoped drift\n")
    inside_drift = check.snapshot_repository_identity(
        repo,
        invariant_scope=scope,
    )
    with pytest.raises(check.InputInvalid, match="untracked invariant"):
        check._require_repo_scope(repo, capsule, inside_drift)


def _v5_scope(owned_prefixes: list[str]) -> dict:
    payload = {
        "exact_paths": ["scoped.txt"],
        "prefixes": [],
        "scope_version": 2,
        "verifier_owned_ignored_prefixes": owned_prefixes,
    }
    return {
        **payload,
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


@pytest.mark.parametrize(
    "owned_prefixes",
    [
        [],
        [
            "reports/canonical_shell_rc_remediation/",
            "reports/other/",
        ],
        ["reports/canonical_shell_rc_remediaton/"],
    ],
)
def test_consumer_rejects_v5_missing_extra_or_misspelled_owned_prefix(
    owned_prefixes: list[str],
) -> None:
    check = load_check_module()
    with pytest.raises(check.InputInvalid, match="verifier-owned ignored prefix"):
        check._validate_invariant_scope(_v5_scope(owned_prefixes))


def test_v5_generator_and_consumer_use_identical_excluded_count_formula(
    tmp_path: Path,
) -> None:
    check = load_check_module()
    dispatch_path = REPO / "scripts" / "dispatch_capsule.py"
    spec = importlib.util.spec_from_file_location("dispatch_v5_parity", dispatch_path)
    assert spec is not None and spec.loader is not None
    dispatch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatch)

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / ".gitignore").write_text("reports/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "--", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "baseline")
    (repo / "scoped.txt").write_text("scope\n", encoding="utf-8")
    owned = repo / "reports" / "canonical_shell_rc_remediation" / "old" / "SUMMARY.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("owned\n", encoding="utf-8")
    other = repo / "reports" / "lint" / "sidecar.json"
    other.parent.mkdir(parents=True)
    other.write_text("{}\n", encoding="utf-8")

    generated_scope = dispatch._normalize_invariant_scope(
        (Path("scoped.txt"),),
        (),
        (Path("reports/canonical_shell_rc_remediation"),),
    )
    consumed_scope = check._validate_invariant_scope(generated_scope)
    assert consumed_scope == generated_scope

    generated_untracked = dispatch.measure_path_map(
        repo,
        ignored=False,
        invariant_scope=generated_scope,
    )
    consumed_untracked = check._path_map(
        repo,
        ignored=False,
        excluded_exact=set(),
        excluded_prefixes=(),
        invariant_scope=consumed_scope,
    )
    generated_ignored = dispatch.measure_path_map(
        repo,
        ignored=True,
        invariant_scope=generated_scope,
    )
    consumed_ignored = check._path_map(
        repo,
        ignored=True,
        excluded_exact=set(),
        excluded_prefixes=(),
        invariant_scope=consumed_scope,
    )

    assert consumed_untracked == generated_untracked
    assert consumed_ignored == generated_ignored
    assert generated_ignored["count"] == 0
    assert generated_ignored["excluded_count"] == 1


def test_v5_write_boundary_is_exactly_21_tracked_paths() -> None:
    check = load_check_module()
    assert len(check.ALLOWED_TRACKED_PATHS) == 21
    assert "tests/fixtures/anchor/corpus_audit_baseline.json" in (
        check.ALLOWED_TRACKED_PATHS
    )


def test_load_capsule_rejects_schema_v4_without_invariant_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Catches a scoped schema accepted without the selector contract it needs."""

    check = load_check_module()
    monkeypatch.setattr(check, "CAPSULE_ROOT", tmp_path)
    capsule = {
        "directive_id": "RB-20260813-shellrc-curated-remediation-t1",
        "schema_version": 4,
        "tracked_worktree": {},
    }
    raw = json.dumps(
        capsule,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    (tmp_path / f"{digest}.json").write_bytes(raw)

    with pytest.raises(check.InputInvalid, match="invariant scope"):
        check._load_capsule(digest)


def test_evidence_render_and_publish_are_deterministic_and_no_overwrite(
    tmp_path: Path,
) -> None:
    check = load_check_module()
    report = {
        "status": "GREEN",
        "baseline_rows": 692,
        "candidate_rows": 692,
        "remediated_targets": 18,
        "non_target_rows": 674,
        "advisory_rows": 74,
        "runtime_review_rows": 6,
        "unresolved": 0,
        "p2_mappings": 12,
        "p2_selectors": 14,
        "p2_bindings": 15,
        "matrix_rows": [],
    }
    identities = {"manifest": "1" * 64, "candidate": "2" * 64}
    first = check.render_evidence(report, identities)
    second = check.render_evidence(copy.deepcopy(report), copy.deepcopy(identities))
    assert first == second
    assert set(first) == {"SUMMARY.md", "shell_rc_remediation_matrix.csv"}
    destination = check.publish_evidence(tmp_path, "a" * 16, first)
    assert check.publish_evidence(tmp_path, "a" * 16, second) == destination
    (destination / "SUMMARY.md").write_text("mismatch", encoding="utf-8")
    with pytest.raises(check.InfrastructureFailure):
        check.publish_evidence(tmp_path, "a" * 16, first)


def test_invalid_cli_input_returns_two_without_final_evidence(
    tmp_path: Path,
) -> None:
    check = load_check_module()
    output = tmp_path / "output"
    code = check.main(
        [
            "verify-worktree",
            "--manifest",
            str(tmp_path / "missing.json"),
            "--spec",
            str(tmp_path / "missing-spec.md"),
            "--directive",
            str(tmp_path / "missing-directive.md"),
            "--evidence",
            str(tmp_path / "missing-evidence.json"),
            "--capsule-sha256",
            "0" * 64,
            "--approved-spec-sha256",
            "1" * 64,
            "--approved-directive-sha256",
            "2" * 64,
            "--approved-evidence-sha256",
            "3" * 64,
            "--output-root",
            str(output),
        ]
    )
    assert code == 2
    assert not output.exists()


def test_live_worktree_is_fully_remediated() -> None:
    check = load_check_module()
    report = check.verify_repository_candidate(
        REPO,
        check.load_and_validate_manifest(MANIFEST_PATH),
        mode="worktree",
    )
    assert report["status"] == "GREEN", report
    assert {
        key: report[key]
        for key in (
            "baseline_rows",
            "candidate_rows",
            "remediated_targets",
            "non_target_rows",
            "advisory_rows",
            "runtime_review_rows",
            "unresolved",
            "p2_mappings",
            "p2_selectors",
            "p2_bindings",
        )
    } == {
        "baseline_rows": 692,
        "candidate_rows": 692,
        "remediated_targets": 18,
        "non_target_rows": 674,
        "advisory_rows": 74,
        "runtime_review_rows": 6,
        "unresolved": 0,
        "p2_mappings": 12,
        "p2_selectors": 14,
        "p2_bindings": 15,
    }
