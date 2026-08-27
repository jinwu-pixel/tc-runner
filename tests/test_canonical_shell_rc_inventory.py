"""Host-only characterization for the canonical shell exposure inventory."""

from __future__ import annotations

import csv
import importlib.util
import io
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "canonical_shell_rc_inventory.py"
SPEC = importlib.util.spec_from_file_location(
    "canonical_shell_rc_inventory",
    SCRIPT,
)
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _blob(path: str, text: str, oid: str) -> object:
    return AUDIT.HeadYamlBlob(
        path=path,
        blob_oid=oid,
        data=text.encode("utf-8"),
    )


def test_head_snapshot_preserves_non_ascii_paths_and_ignores_worktree(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")

    tracked = repo / "한글" / "테스트.yaml"
    tracked.parent.mkdir()
    committed = "name: committed\nmetadata:\n  runnable: true\nsteps: []\n"
    tracked.write_bytes(committed.encode("utf-8"))
    _git(repo, "add", "--", "한글/테스트.yaml")
    _git(
        repo,
        "-c",
        "user.name=Inventory Test",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    head = _git(repo, "rev-parse", "HEAD")

    tracked.write_bytes(b"name: dirty\n")
    (repo / "untracked.yaml").write_bytes(b"name: untracked\n")

    blobs = AUDIT.read_head_yaml_blobs(repo, head)
    committed_blob = subprocess.run(
        ["git", "show", f"{head}:한글/테스트.yaml"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout

    assert [blob.path for blob in blobs] == ["한글/테스트.yaml"]
    assert blobs[0].data == committed_blob
    assert b"dirty" not in blobs[0].data
    assert blobs[0].blob_oid == _git(
        repo,
        "rev-parse",
        "HEAD:한글/테스트.yaml",
    )


def test_head_snapshot_excludes_provenance_manifests(tmp_path: Path) -> None:
    """Catches provenance metadata leaking into the executable TC inventory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")

    case = repo / "case.yaml"
    case.write_text("tc_name: case\nsteps: []\n", encoding="utf-8")
    manifest = repo / "provenance" / "manifest.yaml"
    manifest.parent.mkdir()
    manifest.write_text("schema_version: 1\n", encoding="utf-8")
    _git(repo, "add", "--", "case.yaml", "provenance/manifest.yaml")
    _git(
        repo,
        "-c",
        "user.name=Inventory Test",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    head = _git(repo, "rev-parse", "HEAD")

    blobs = AUDIT.read_head_yaml_blobs(repo, head)

    assert [blob.path for blob in blobs] == ["case.yaml"]


def test_collect_inventory_replays_explicit_head_after_head_advances(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    tracked = repo / "case.yaml"
    tracked.write_text(
        "tc_name: replay_case\n"
        "description: explicit revision replay fixture\n"
        "metadata:\n"
        "  source: test\n"
        "  runnable: true\n"
        "  tc_class: FULL_AUTO\n"
        "  execution_type: AUTO\n"
        "  manual_detail: NONE\n"
        "  has_manual_steps: false\n"
        "  has_shell_actions: true\n"
        "  has_unresolved_params: false\n"
        "  target_app:\n"
        "    package: com.example.fixture\n"
        "    version: test\n"
        "  target_device: fixture\n"
        "preconditions: []\n"
        "steps:\n"
        "  - action: shell\n"
        "    command: echo first\n"
        "    execution_mode: SHELL_AUTO\n"
        "    step_role: SETUP\n"
        "    compile_status: OK\n",
        encoding="utf-8",
    )
    _git(repo, "add", "--", "case.yaml")
    _git(
        repo,
        "-c",
        "user.name=Inventory Test",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-q",
        "-m",
        "first",
    )
    first_head = _git(repo, "rev-parse", "HEAD")

    tracked.write_text(
        "tc_name: replay_case\n"
        "description: explicit revision replay fixture\n"
        "metadata:\n"
        "  source: test\n"
        "  runnable: true\n"
        "  tc_class: FULL_AUTO\n"
        "  execution_type: AUTO\n"
        "  manual_detail: NONE\n"
        "  has_manual_steps: false\n"
        "  has_shell_actions: true\n"
        "  has_unresolved_params: false\n"
        "  target_app:\n"
        "    package: com.example.fixture\n"
        "    version: test\n"
        "  target_device: fixture\n"
        "preconditions: []\n"
        "steps:\n"
        "  - action: shell\n"
        "    command: echo second\n"
        "    execution_mode: SHELL_AUTO\n"
        "    step_role: SETUP\n"
        "    compile_status: OK\n",
        encoding="utf-8",
    )
    _git(repo, "add", "--", "case.yaml")
    _git(
        repo,
        "-c",
        "user.name=Inventory Test",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-q",
        "-m",
        "second",
    )
    second_head = _git(repo, "rev-parse", "HEAD")

    report = AUDIT.collect_inventory(repo, head_sha=first_head)

    assert first_head != second_head
    assert AUDIT.resolve_head(repo) == second_head
    assert report.head_sha == first_head
    assert [row["command"] for row in report.rows] == ["echo first"]
    assert report.rows[0]["row_key"] == f"{first_head}:case.yaml#1"


def test_parser_accepts_exact_head_replay() -> None:
    head = "1" * 40

    args = AUDIT._parser().parse_args(["--head", head])

    assert args.head == head


@pytest.mark.parametrize("revision", ["HEAD", "abc123", "A" * 40])
def test_explicit_head_replay_requires_full_lowercase_sha(
    tmp_path: Path,
    revision: str,
) -> None:
    with pytest.raises(AUDIT.AuditInputError, match="full lowercase"):
        AUDIT.resolve_commit(tmp_path, revision)


def test_inventory_filters_raw_boolean_runnable_and_keeps_rejected_sibling(
) -> None:
    head = "1" * 40
    accepted = _blob(
        "corpus/accepted.yaml",
        """
name: accepted
metadata:
  runnable: true
steps:
  - action: wait
    seconds: 1
  - action: shell
    command: echo runner
    execution_mode: SHELL_AUTO
  - action: verify_shell
    command: getprop ro.product.model
    expected: Pixel
    timeout: 1234
  - action: shell
    command: echo manual
    execution_mode: MANUAL_REQUIRED
""".lstrip(),
        "a" * 40,
    )
    rejected = _blob(
        "corpus/rejected.yaml",
        """
name: rejected
metadata:
  runnable: true
steps:
  - action: shell
    command: exit 1
""".lstrip(),
        "b" * 40,
    )
    string_true = _blob(
        "corpus/string_true.yaml",
        """
name: string true
metadata:
  runnable: "true"
steps:
  - action: shell
    command: echo excluded
""".lstrip(),
        "c" * 40,
    )
    verify_only = _blob(
        "corpus/verify_only.yaml",
        """
name: verify only
metadata:
  runnable: true
steps:
  - action: verify_shell
    command: echo excluded
    expected: excluded
""".lstrip(),
        "d" * 40,
    )
    comment_only = _blob(
        "docs/comment_only.yaml",
        "# documentation template with no YAML document\n",
        "f" * 40,
    )

    def preflight(blob: object) -> object:
        if blob.path == rejected.path:
            return AUDIT.PreflightObservation(
                passed=False,
                tc_data=None,
                reasons=("CANONICAL_LOAD_OR_VALIDATION_ERROR:Fixture:bad",),
            )
        return AUDIT.PreflightObservation(
            passed=True,
            tc_data=AUDIT.parse_yaml_mapping(blob),
            reasons=(),
        )

    report = AUDIT.build_inventory_from_blobs(
        head,
        (accepted, rejected, string_true, verify_only, comment_only),
        preflight,
    )

    assert report.summary == {
        "tracked_yaml_files": 5,
        "raw_runnable_rc_files": 3,
        "canonical_preflight_pass_files": 2,
        "canonical_preflight_reject_files": 1,
        "inventory_rc_steps": 4,
        "runner_dispatched_rc_steps": 3,
        "manual_routed_rc_steps": 1,
        "action_shell_files": 1,
        "action_shell_steps": 2,
        "verify_shell_files": 2,
        "verify_shell_steps": 2,
    }
    assert report.rejection_reason_counts == {
        "CANONICAL_LOAD_OR_VALIDATION_ERROR:Fixture": 1
    }
    assert [row["row_key"] for row in report.rows] == [
        f"{head}:corpus/accepted.yaml#2",
        f"{head}:corpus/accepted.yaml#3",
        f"{head}:corpus/accepted.yaml#4",
        f"{head}:corpus/verify_only.yaml#1",
    ]
    assert [row["dispatch_route"] for row in report.rows] == [
        "RUNNER_SHELL",
        "RUNNER_SHELL",
        "MANUAL_PAUSE",
        "RUNNER_SHELL",
    ]
    assert {row["action"] for row in report.rows} == {
        "shell",
        "verify_shell",
    }
    verify_row = report.rows[1]
    assert verify_row["expected"] == "Pixel"
    assert verify_row["timeout_ms"] == 1234
    assert report.rows[3]["timeout_ms"] == 30000
    assert report.rows[0]["expected"] == ""
    assert report.rows[0]["timeout_ms"] == ""


@pytest.mark.parametrize("timeout", [".nan", ".inf"], ids=["nan", "infinity"])
def test_verify_shell_timeout_must_be_finite(timeout: str) -> None:
    source = _blob(
        "corpus/nonfinite.yaml",
        f"""
name: nonfinite
metadata:
  runnable: true
steps:
  - action: verify_shell
    command: echo ready
    expected: ready
    timeout: {timeout}
""".lstrip(),
        "9" * 40,
    )

    def preflight(blob: object) -> object:
        return AUDIT.PreflightObservation(
            passed=True,
            tc_data=AUDIT.parse_yaml_mapping(blob),
            reasons=(),
        )

    with pytest.raises(AUDIT.AuditInputError, match="invalid timeout"):
        AUDIT.build_inventory_from_blobs(
            "8" * 40,
            (source,),
            preflight,
        )


def test_rendered_artifacts_are_byte_deterministic_and_csv_safe() -> None:
    head = "2" * 40
    source = _blob(
        "한글/quoted.yaml",
        """
name: 'quoted, "case"'
metadata:
  runnable: true
steps:
  - action: shell
    command: |-
      printf "a,b"
      echo second
    execution_mode: SHELL_AUTO
""".lstrip(),
        "e" * 40,
    )

    def preflight(blob: object) -> object:
        return AUDIT.PreflightObservation(
            passed=True,
            tc_data=AUDIT.parse_yaml_mapping(blob),
            reasons=(),
        )

    report = AUDIT.build_inventory_from_blobs(head, (source,), preflight)
    first = AUDIT.render_artifacts(
        report,
        input_digest="f" * 64,
        tool_sha256="0" * 64,
        runtime_input_sha256={"src/cli.py": "1" * 64},
    )
    second = AUDIT.render_artifacts(
        report,
        input_digest="f" * 64,
        tool_sha256="0" * 64,
        runtime_input_sha256={"src/cli.py": "1" * 64},
    )

    assert first == second
    csv_bytes, summary_bytes = first
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))
    assert rows[0]["source_path"] == "한글/quoted.yaml"
    assert rows[0]["tc_name"] == 'quoted, "case"'
    assert rows[0]["action"] == "shell"
    assert rows[0]["command"] == 'printf "a,b"\necho second'
    assert rows[0]["expected"] == ""
    assert rows[0]["timeout_ms"] == ""
    assert b"CSV SHA-256" in summary_bytes
    assert b"Target scope" in summary_bytes
    assert b"action: shell" in summary_bytes
    assert b"verify_shell" in summary_bytes


def test_runtime_actor_set_covers_shell_rc_semantics() -> None:
    assert AUDIT.SCHEMA_VERSION == "canonical-shell-rc-inventory-v3"
    assert AUDIT.TOOL_VERSION == "3"
    assert set(AUDIT.RUNTIME_INPUT_PATHS) == {
        "src/adb.py",
        "src/action_runner.py",
        "src/cli.py",
        "src/tc_loader.py",
        "src/execution_contract.py",
        "tc_step_schema.json",
    }


def test_current_head_inventory_matches_reviewed_target_set() -> None:
    report = AUDIT.collect_inventory(REPO)

    assert report.summary == {
        "tracked_yaml_files": 619,
        "raw_runnable_rc_files": 112,
        "canonical_preflight_pass_files": 112,
        "canonical_preflight_reject_files": 0,
        "inventory_rc_steps": 692,
        "runner_dispatched_rc_steps": 692,
        "manual_routed_rc_steps": 0,
        "action_shell_files": 112,
        "action_shell_steps": 455,
        "verify_shell_files": 74,
        "verify_shell_steps": 237,
    }
    assert report.rejection_reason_counts == {}
    assert len(report.rows) == 692


def test_current_head_inventory_never_constructs_adb(monkeypatch) -> None:
    import src.cli as cli

    def forbidden_adb(*_args, **_kwargs):
        raise AssertionError("host-only inventory must not construct ADB")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    assert AUDIT.collect_inventory(REPO).summary[
        "canonical_preflight_pass_files"
    ] == 112


def test_cli_does_not_allow_cross_repo_override(tmp_path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        AUDIT._parser().parse_args(["--repo", str(tmp_path)])

    assert exc_info.value.code == 2


def test_runtime_actor_hash_changes_input_digest() -> None:
    head = "3" * 40
    tool_sha = "4" * 64
    first = {"src/cli.py": "a" * 64}
    second = {"src/cli.py": "b" * 64}

    assert AUDIT._input_digest(head, tool_sha, first) != AUDIT._input_digest(
        head,
        tool_sha,
        second,
    )


def test_main_runtime_actor_change_fails_before_output(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    head = "5" * 40
    summary = {
        "tracked_yaml_files": 0,
        "raw_runnable_rc_files": 0,
        "canonical_preflight_pass_files": 0,
        "canonical_preflight_reject_files": 0,
        "inventory_rc_steps": 0,
        "runner_dispatched_rc_steps": 0,
        "manual_routed_rc_steps": 0,
        "action_shell_files": 0,
        "action_shell_steps": 0,
        "verify_shell_files": 0,
        "verify_shell_steps": 0,
    }
    report = AUDIT.InventoryReport(
        head_sha=head,
        rows=(),
        summary=summary,
        rejection_reason_counts={},
    )
    actor_snapshots = iter(
        [
            {"src/cli.py": "a" * 64},
            {"src/cli.py": "b" * 64},
        ]
    )
    monkeypatch.setattr(AUDIT, "resolve_head", lambda _repo: head)
    monkeypatch.setattr(AUDIT, "_tool_sha256", lambda: "6" * 64)
    monkeypatch.setattr(
        AUDIT,
        "snapshot_runtime_inputs",
        lambda _repo: next(actor_snapshots),
    )
    monkeypatch.setattr(
        AUDIT,
        "collect_inventory",
        lambda _repo, *, head_sha=None: report,
    )

    def unexpected_write(*_args, **_kwargs):
        raise AssertionError("runtime input drift must prevent output")

    monkeypatch.setattr(AUDIT, "_write_artifacts", unexpected_write)

    assert AUDIT.main(["--out-dir", str(tmp_path)]) == 3
    assert "runtime inputs changed" in capsys.readouterr().err


def test_write_artifacts_second_file_failure_leaves_no_destination(
    tmp_path,
    monkeypatch,
) -> None:
    digest = "7" * 64
    destination = tmp_path / digest[:16]
    original_write_bytes = Path.write_bytes

    def fail_on_summary(path: Path, data: bytes) -> int:
        if path.name == "SUMMARY.md":
            raise OSError("summary write failed")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_on_summary)

    with pytest.raises(OSError, match="summary write failed"):
        AUDIT._write_artifacts(
            tmp_path,
            digest,
            b"csv-bytes",
            b"summary-bytes",
        )

    assert not destination.exists()


def test_write_artifacts_publish_replace_failure_leaves_no_destination(
    tmp_path,
    monkeypatch,
) -> None:
    digest = "b" * 64
    destination = tmp_path / digest[:16]

    def fail_replace(_source, _destination) -> None:
        raise OSError("publish replace failed")

    monkeypatch.setattr(AUDIT.os, "replace", fail_replace)

    with pytest.raises(OSError, match="publish replace failed"):
        AUDIT._write_artifacts(
            tmp_path,
            digest,
            b"csv-bytes",
            b"summary-bytes",
        )

    assert not destination.exists()


def test_write_artifacts_rejects_existing_extra_entry(tmp_path) -> None:
    digest = "8" * 64
    destination = tmp_path / digest[:16]
    destination.mkdir()
    (destination / "shell_rc_inventory.csv").write_bytes(b"csv-bytes")
    (destination / "SUMMARY.md").write_bytes(b"summary-bytes")
    (destination / "EXTRA.txt").write_bytes(b"unexpected")

    with pytest.raises(
        AUDIT.AuditInfraError,
        match="existing destination entry set differs",
    ):
        AUDIT._write_artifacts(
            tmp_path,
            digest,
            b"csv-bytes",
            b"summary-bytes",
        )


def test_write_artifacts_rejects_existing_byte_mismatch(tmp_path) -> None:
    digest = "9" * 64
    destination = tmp_path / digest[:16]
    destination.mkdir()
    (destination / "shell_rc_inventory.csv").write_bytes(b"csv-bytes")
    (destination / "SUMMARY.md").write_bytes(b"stale-summary")

    with pytest.raises(
        AUDIT.AuditInfraError,
        match="existing destination bytes differ",
    ):
        AUDIT._write_artifacts(
            tmp_path,
            digest,
            b"csv-bytes",
            b"summary-bytes",
        )


def test_write_artifacts_post_publish_state_failure_rolls_back(
    tmp_path,
) -> None:
    digest = "a" * 64
    destination = tmp_path / digest[:16]
    checks = 0

    def state_check() -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise AUDIT.AuditInfraError("state changed after publish")

    with pytest.raises(
        AUDIT.AuditInfraError,
        match="state changed after publish",
    ):
        AUDIT._write_artifacts(
            tmp_path,
            digest,
            b"csv-bytes",
            b"summary-bytes",
            state_check=state_check,
        )

    assert checks == 2
    assert not destination.exists()
