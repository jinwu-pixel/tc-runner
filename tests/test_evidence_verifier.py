"""Adversarial integration tests for scripts/evidence_verifier.py.

Every test runs the verifier CLI against an isolated temporary Git repository.
Git and pytest are real child processes; no live tc-runner state is consulted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


_ROOT = Path(__file__).resolve().parent.parent
_TOOL = _ROOT / "scripts" / "evidence_verifier.py"
_SPEC = importlib.util.spec_from_file_location("evidence_verifier", _TOOL)
VERIFIER = importlib.util.module_from_spec(_SPEC)
sys.modules["evidence_verifier"] = VERIFIER
_SPEC.loader.exec_module(VERIFIER)


@dataclass(frozen=True)
class RepoFixture:
    repo: Path
    artifacts: Path


def _run(
    argv: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repo, check=check)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(
    tmp_path: Path,
    *,
    tests_source: str = "def test_existing():\n    assert True\n",
) -> RepoFixture:
    bare = tmp_path / "origin.git"
    bare.mkdir()
    _git(bare, "-c", "init.defaultBranch=master", "init", "--bare")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/master")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "-c", "init.defaultBranch=master", "init")
    _git(repo, "config", "user.email", "verifier@example.invalid")
    _git(repo, "config", "user.name", "Evidence Verifier Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "remote", "add", "origin", str(bare))

    _write(
        repo / ".gitignore",
        ".pytest_cache/\n__pycache__/\n*.pyc\n",
    )
    _write(repo / "src" / "prod.py", "VALUE = 1\n")
    _write(repo / "notes.txt", "committed\n")
    _write(repo / "tests" / "test_sample.py", tests_source)
    _git(repo, "add", "--", ".gitignore", "src/prod.py", "notes.txt", "tests/test_sample.py")
    _git(repo, "commit", "-m", "baseline")
    _git(repo, "push", "-u", "origin", "master")

    artifacts = repo / "scratch"
    artifacts.mkdir()
    return RepoFixture(repo=repo, artifacts=artifacts)


def _make_linked_worktree(fx: RepoFixture, path: Path) -> RepoFixture:
    _git(
        fx.repo,
        "worktree",
        "add",
        "-b",
        "verifier-linked",
        str(path),
        "HEAD",
    )
    _git(path, "branch", "--set-upstream-to=origin/master")
    artifacts = path / "scratch"
    artifacts.mkdir()
    assert (path / ".git").is_file()
    return RepoFixture(repo=path, artifacts=artifacts)


def _tool_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    return env


def _run_tool(
    fx: RepoFixture,
    *args: str,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _tool_env()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(_TOOL), *args],
        cwd=fx.repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _capture(fx: RepoFixture) -> tuple[Path, dict[str, Any]]:
    baseline_path = fx.artifacts / "baseline.json"
    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(baseline_path),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert baseline_path.is_file()
    return baseline_path, _load_json(baseline_path)


def _blob(repo: Path, rel_path: str) -> str:
    return _git(repo, "hash-object", "--", rel_path).stdout.strip()


def _write_capsule(
    fx: RepoFixture,
    baseline_path: Path,
    baseline: dict[str, Any],
    *,
    allowed_write_paths: list[str] | None = None,
    expected_new_nodeids: list[str] | None = None,
    production_invariant: dict[str, str] | None = None,
    pytest_min_passed: int | None = None,
    evidence_paths: list[str] | None = None,
    output_rel: str = "scratch/bundle.json",
    overrides: dict[str, Any] | None = None,
    filename: str = "capsule.json",
) -> Path:
    expected = expected_new_nodeids or []
    if pytest_min_passed is None:
        pytest_min_passed = baseline["pytest"]["counts"]["passed"] + len(expected)
    capsule_path = fx.artifacts / filename
    if evidence_paths is None:
        evidence_paths = sorted(
            {
                baseline_path.resolve().relative_to(fx.repo.resolve()).as_posix(),
                capsule_path.resolve().relative_to(fx.repo.resolve()).as_posix(),
                output_rel,
            }
        )
    capsule: dict[str, Any] = {
        "schema_version": 1,
        "capsule_id": "isolated-verifier-test",
        "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "head_sha": baseline["git"]["head_sha"],
        "verifier_sha256": baseline["tool"]["verifier_sha256"],
        "allowed_write_paths": allowed_write_paths or [],
        "expected_new_nodeids": expected,
        "removed_nodeids_allowed": False,
        "production_invariant": production_invariant
        if production_invariant is not None
        else {"src/prod.py": _blob(fx.repo, "src/prod.py")},
        "pytest_min_passed": pytest_min_passed,
        "evidence_paths": evidence_paths,
    }
    if overrides:
        capsule.update(overrides)
    capsule_path.write_text(
        json.dumps(capsule, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return capsule_path


def _verify(
    fx: RepoFixture,
    baseline_path: Path,
    capsule_path: Path,
    *,
    output_name: str = "bundle.json",
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], Path]:
    bundle_path = fx.artifacts / output_name
    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(bundle_path),
    )
    assert bundle_path.is_file(), proc.stdout + proc.stderr
    return proc, _load_json(bundle_path), bundle_path


def _dod(bundle: dict[str, Any], check_id: str) -> dict[str, Any]:
    matches = [item for item in bundle["dod"] if item["id"] == check_id]
    assert len(matches) == 1, bundle["dod"]
    return matches[0]


def _assert_exit(
    proc: subprocess.CompletedProcess[str],
    bundle: dict[str, Any],
    expected: int,
) -> None:
    assert proc.returncode == expected, proc.stdout + proc.stderr
    assert bundle["verifier_exit"] == expected


def _assert_bundle_schema(bundle: dict[str, Any]) -> None:
    assert set(bundle) == {
        "schema_version",
        "capsule_id",
        "verifier_exit",
        "exit_reason",
        "steps",
        "files",
        "pytest",
        "nodeids",
        "workspace_delta",
        "dod",
    }
    assert type(bundle["schema_version"]) is int
    assert isinstance(bundle["capsule_id"], str)
    assert type(bundle["verifier_exit"]) is int
    assert isinstance(bundle["exit_reason"], str)

    assert isinstance(bundle["steps"], list)
    for step in bundle["steps"]:
        assert set(step) == {"command", "cwd", "exit_code"}
        assert isinstance(step["command"], list)
        assert all(isinstance(item, str) for item in step["command"])
        assert isinstance(step["cwd"], str)
        assert step["exit_code"] is None or type(step["exit_code"]) is int

    assert isinstance(bundle["files"], dict)
    for path, state in bundle["files"].items():
        assert isinstance(path, str)
        assert set(state) == {"blob_before", "blob_after"}
        assert state["blob_before"] is None or isinstance(
            state["blob_before"], str
        )
        assert state["blob_after"] is None or isinstance(
            state["blob_after"], str
        )

    assert set(bundle["pytest"]) == {"exit_code", "counts"}
    assert type(bundle["pytest"]["exit_code"]) is int
    assert set(bundle["pytest"]["counts"]) == {
        "passed",
        "skipped",
        "xfailed",
        "failed",
        "errors",
    }
    assert all(
        type(value) is int for value in bundle["pytest"]["counts"].values()
    )

    assert set(bundle["nodeids"]) == {"added", "removed"}
    assert all(
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        for value in bundle["nodeids"].values()
    )
    assert set(bundle["workspace_delta"]) == {
        "worktree_delta",
        "index_changed",
        "untracked_added",
        "untracked_removed",
    }
    assert type(bundle["workspace_delta"]["index_changed"]) is bool
    assert all(
        isinstance(bundle["workspace_delta"][key], list)
        and all(
            isinstance(item, str)
            for item in bundle["workspace_delta"][key]
        )
        for key in (
            "worktree_delta",
            "untracked_added",
            "untracked_removed",
        )
    )

    assert isinstance(bundle["dod"], list)
    assert len(bundle["dod"]) == 6
    for item in bundle["dod"]:
        assert set(item) == {"id", "verdict", "detail"}
        assert isinstance(item["id"], str)
        assert isinstance(item["verdict"], str)
        assert isinstance(item["detail"], dict)


def test_parse_collect_output_normalizes_only_module_path():
    output = r"tests\test_x.py::test_p[\t]" + "\n"

    assert VERIFIER._parse_collect_output(output) == [
        r"tests/test_x.py::test_p[\t]"
    ]


def test_capture_baseline_accepts_backslash_parameter_ids(tmp_path):
    fx = _make_repo(
        tmp_path,
        tests_source=(
            "import pytest\n\n"
            "@pytest.mark.parametrize('value', ['\\t', r'a\\b'])\n"
            "def test_backslash_param(value):\n"
            "    assert value\n"
        ),
    )
    baseline_path = fx.artifacts / "backslash-baseline.json"

    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(baseline_path),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    baseline = _load_json(baseline_path)
    assert baseline["pytest"]["counts"]["passed"] == 2
    assert len(baseline["collect_nodeids"]) == 2


def test_c0_rejects_baseline_byte_tampering(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    baseline_path.write_bytes(baseline_path.read_bytes() + b" ")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_c0_rejects_head_movement(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _write(fx.repo / "head_move.txt", "new commit\n")
    _git(fx.repo, "add", "--", "head_move.txt")
    _git(fx.repo, "commit", "-m", "move head")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_c0_rejects_path_traversal(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["../escape.py"],
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_c0_rejects_verifier_hash_mismatch(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        overrides={"verifier_sha256": "0" * 40},
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_capture_rejects_output_outside_repo(tmp_path):
    fx = _make_repo(tmp_path)
    outside = tmp_path / "outside-baseline.json"

    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(outside),
    )

    assert proc.returncode == 2
    assert not outside.exists()


def test_capture_rejects_symlink_or_junction_escape(tmp_path):
    fx = _make_repo(tmp_path)
    outside = tmp_path / "outside-artifacts"
    outside.mkdir()
    link = fx.repo / "scratch-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        proc = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    escaped = link / "baseline.json"
    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(escaped),
    )

    assert proc.returncode == 2
    assert not (outside / "baseline.json").exists()


def test_capture_refuses_linked_worktree_gitfile_output(tmp_path):
    fx = _make_repo(tmp_path)
    linked = _make_linked_worktree(fx, tmp_path / "linked")
    gitfile = linked.repo / ".git"
    before = gitfile.read_bytes()

    proc = _run_tool(
        linked,
        "capture-baseline",
        "--out",
        str(gitfile),
    )

    assert proc.returncode == 2
    assert gitfile.read_bytes() == before


def test_verify_refuses_linked_worktree_gitfile_output(tmp_path):
    fx = _make_repo(tmp_path)
    linked = _make_linked_worktree(fx, tmp_path / "linked")
    baseline_path, baseline = _capture(linked)
    gitfile = linked.repo / ".git"
    before = gitfile.read_bytes()
    capsule_path = _write_capsule(
        linked,
        baseline_path,
        baseline,
        evidence_paths=[
            "scratch/baseline.json",
            "scratch/capsule.json",
            ".git",
        ],
    )

    proc = _run_tool(
        linked,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(gitfile),
    )

    assert proc.returncode == 2
    assert gitfile.read_bytes() == before


def test_c0_rejects_external_verify_evidence_paths(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    outside_baseline = outside / "baseline.json"
    outside_capsule = outside / "capsule.json"
    outside_bundle = outside / "bundle.json"
    outside_baseline.write_bytes(baseline_path.read_bytes())
    outside_capsule.write_bytes(capsule_path.read_bytes())

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(outside_baseline),
        "--capsule",
        str(outside_capsule),
        "--out",
        str(outside_bundle),
    )

    assert proc.returncode == 2
    assert not outside_bundle.exists()


def test_c0_requires_actual_evidence_paths_to_match_capsule(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        evidence_paths=[
            "scratch/baseline.json",
            "scratch/capsule.json",
            "scratch/bundle.json",
            "scratch/not-an-actual-input.json",
        ],
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_c0_rejects_baseline_path_not_declared_as_evidence(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    moved_baseline = fx.artifacts / "moved-baseline.json"
    moved_baseline.write_bytes(baseline_path.read_bytes())

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(moved_baseline),
        "--capsule",
        str(capsule_path),
        "--out",
        str(fx.artifacts / "bundle.json"),
    )
    bundle = _load_json(fx.artifacts / "bundle.json")

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_c1_detects_additional_change_to_preexisting_dirty_file(tmp_path):
    fx = _make_repo(tmp_path)
    _write(fx.repo / "notes.txt", "dirty before baseline\n")
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _write(fx.repo / "notes.txt", "dirty after baseline\n")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["worktree_delta"] == ["notes.txt"]
    assert bundle["workspace_delta"]["index_changed"] is False


def test_c1_detects_revert_of_preexisting_dirty_file(tmp_path):
    fx = _make_repo(tmp_path)
    _write(fx.repo / "notes.txt", "dirty before baseline\n")
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _write(fx.repo / "notes.txt", "committed\n")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["worktree_delta"] == ["notes.txt"]


def test_c1_detects_any_index_change(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["notes.txt"],
    )
    _write(fx.repo / "notes.txt", "staged after baseline\n")
    _git(fx.repo, "add", "--", "notes.txt")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["index_changed"] is True


@pytest.mark.parametrize(
    "index_flag",
    ["--assume-unchanged", "--skip-worktree"],
)
def test_c1_detects_hidden_index_flag_content_change(tmp_path, index_flag):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _git(fx.repo, "update-index", index_flag, "notes.txt")
    _write(fx.repo / "notes.txt", "hidden from ordinary git diff\n")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["worktree_delta"] == ["notes.txt"]
    assert bundle["workspace_delta"]["index_changed"] is True


def test_c1_detects_declared_but_missing_write(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["notes.txt"],
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["worktree_delta"] == []


def test_c2_allows_only_exact_evidence_path(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 0)
    assert _dod(bundle, "C2")["verdict"] == "GREEN"
    assert bundle["workspace_delta"]["untracked_added"] == []


def test_c2_rejects_sibling_of_exact_evidence_path(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    sibling_rel = "scratch/bundle.json.extra"
    _write(fx.repo / sibling_rel, "{}\n")
    capsule_path = _write_capsule(fx, baseline_path, baseline)

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C2")["verdict"] == "RED"
    assert bundle["workspace_delta"]["untracked_added"] == [sibling_rel]


def test_c2_rejects_removed_baseline_untracked_path(tmp_path):
    fx = _make_repo(tmp_path)
    seed = fx.repo / "baseline-untracked.txt"
    _write(seed, "keep me\n")
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    seed.unlink()

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C2")["verdict"] == "RED"
    assert bundle["workspace_delta"]["untracked_removed"] == [
        "baseline-untracked.txt"
    ]


def test_c3_rejects_undeclared_added_nodeid(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    _write(
        fx.repo / "tests" / "test_sample.py",
        "def test_existing():\n"
        "    assert True\n\n"
        "def test_undeclared():\n"
        "    assert True\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C3")["verdict"] == "RED"
    assert bundle["nodeids"]["added"] == [
        "tests/test_sample.py::test_undeclared"
    ]


def test_c3_rejects_removed_parametrized_nodeid(tmp_path):
    fx = _make_repo(
        tmp_path,
        tests_source=(
            "import pytest\n\n"
            "@pytest.mark.parametrize('value', [1, 2], ids=['one', 'two'])\n"
            "def test_param(value):\n"
            "    assert value\n"
        ),
    )
    baseline_path, baseline = _capture(fx)
    _write(
        fx.repo / "tests" / "test_sample.py",
        "import pytest\n\n"
        "@pytest.mark.parametrize('value', [1], ids=['one'])\n"
        "def test_param(value):\n"
        "    assert value\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
        pytest_min_passed=1,
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C3")["verdict"] == "RED"
    assert bundle["nodeids"]["removed"] == [
        "tests/test_sample.py::test_param[two]"
    ]


def test_c4_rejects_baseline_pass_that_becomes_skipped(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    _write(
        fx.repo / "tests" / "test_sample.py",
        "import pytest\n\n"
        "def test_existing():\n"
        "    pytest.skip('regressed')\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
        pytest_min_passed=0,
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C4")["verdict"] == "RED"
    assert bundle["pytest"]["counts"]["skipped"] == 1


def test_c4_rejects_new_nodeid_with_fixture_error(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    new_nodeid = "tests/test_sample.py::test_new_error"
    _write(
        fx.repo / "tests" / "test_sample.py",
        "import pytest\n\n"
        "def test_existing():\n"
        "    assert True\n\n"
        "@pytest.fixture\n"
        "def broken():\n"
        "    raise RuntimeError('boom')\n\n"
        "def test_new_error(broken):\n"
        "    assert broken\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
        expected_new_nodeids=[new_nodeid],
        pytest_min_passed=1,
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C4")["verdict"] == "RED"
    assert bundle["pytest"]["counts"]["errors"] == 1


def test_c4_rejects_new_xfailed_nodeid(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    new_nodeid = "tests/test_sample.py::test_new_xfail"
    _write(
        fx.repo / "tests" / "test_sample.py",
        "import pytest\n\n"
        "def test_existing():\n"
        "    assert True\n\n"
        "@pytest.mark.xfail(reason='known')\n"
        "def test_new_xfail():\n"
        "    assert False\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
        expected_new_nodeids=[new_nodeid],
        pytest_min_passed=1,
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C4")["verdict"] == "RED"
    assert bundle["pytest"]["counts"]["xfailed"] == 1


def test_c5_rejects_production_hash_change_even_when_path_is_allowed(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    original_blob = _blob(fx.repo, "src/prod.py")
    _write(fx.repo / "src" / "prod.py", "VALUE = 2\n")
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["src/prod.py"],
        production_invariant={"src/prod.py": original_blob},
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "GREEN"
    assert _dod(bundle, "C5")["verdict"] == "RED"


def test_git_measurement_failure_is_exit_3(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    git_dir = fx.repo / ".git"
    hidden_git_dir = fx.repo / ".git-disabled"
    git_dir.rename(hidden_git_dir)

    bundle_path = fx.artifacts / "bundle.json"
    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(bundle_path),
    )

    assert proc.returncode == 3
    assert not bundle_path.exists()


def test_early_git_failure_cannot_overwrite_tracked_output(tmp_path, monkeypatch):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    production_path = fx.repo / "src" / "prod.py"
    before = production_path.read_bytes()

    def fail_repo_root(_recorder):
        raise VERIFIER.MeasurementError("injected Git failure")

    monkeypatch.setattr(VERIFIER, "_repo_root", fail_repo_root)
    monkeypatch.chdir(fx.repo)

    exit_code = VERIFIER._verify(
        baseline_path,
        capsule_path,
        production_path,
    )

    assert exit_code == 3
    assert production_path.read_bytes() == before


def test_pytest_collection_failure_is_exit_3(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    _write(fx.repo / "tests" / "test_sample.py", "def broken(:\n")
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
    )

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 3)
    assert bundle["exit_reason"].startswith("INFRA_FAILURE:")


def test_pytest_spawn_failure_is_exit_3(tmp_path, monkeypatch):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    bundle_path = fx.artifacts / "bundle.json"
    real_run = VERIFIER.subprocess.run

    def fail_pytest(argv, *args, **kwargs):
        if len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]:
            raise FileNotFoundError("injected pytest spawn failure")
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(VERIFIER.subprocess, "run", fail_pytest)
    monkeypatch.chdir(fx.repo)

    exit_code = VERIFIER._verify(baseline_path, capsule_path, bundle_path)
    bundle = _load_json(bundle_path)

    assert exit_code == 3
    assert bundle["verifier_exit"] == 3
    assert bundle["exit_reason"].startswith("INFRA_FAILURE:")


def test_junit_parse_failure_is_exit_3(tmp_path, monkeypatch):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    bundle_path = fx.artifacts / "bundle.json"

    def fail_junit(_path, _collected):
        raise VERIFIER.MeasurementError("injected JUnit parse failure")

    monkeypatch.setattr(VERIFIER, "_parse_junit", fail_junit)
    monkeypatch.chdir(fx.repo)

    exit_code = VERIFIER._verify(
        baseline_path,
        capsule_path,
        bundle_path,
    )
    bundle = _load_json(bundle_path)

    assert exit_code == 3
    assert bundle["verifier_exit"] == 3
    assert bundle["exit_reason"].startswith("INFRA_FAILURE:")


def test_final_bundle_io_failure_preserves_initial_exit_3_bundle(
    tmp_path,
    monkeypatch,
):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    bundle_path = fx.artifacts / "bundle.json"
    real_write = VERIFIER._atomic_write_json
    writes = 0

    def fail_second_write(path, value):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise VERIFIER.MeasurementError("injected final bundle IO failure")
        real_write(path, value)

    monkeypatch.setattr(VERIFIER, "_atomic_write_json", fail_second_write)
    monkeypatch.chdir(fx.repo)

    exit_code = VERIFIER._verify(
        baseline_path,
        capsule_path,
        bundle_path,
    )
    preserved = _load_json(bundle_path)

    assert exit_code == 3
    assert writes == 2
    assert preserved["verifier_exit"] == 3
    assert preserved["exit_reason"] == "INFRA_FAILURE"


def test_first_bundle_io_failure_is_exit_3_without_bundle(
    tmp_path,
    monkeypatch,
):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    bundle_path = fx.artifacts / "bundle.json"

    def fail_every_write(_path, _value):
        raise VERIFIER.MeasurementError("injected bundle IO failure")

    monkeypatch.setattr(VERIFIER, "_atomic_write_json", fail_every_write)
    monkeypatch.chdir(fx.repo)

    exit_code = VERIFIER._verify(
        baseline_path,
        capsule_path,
        bundle_path,
    )

    assert exit_code == 3
    assert not bundle_path.exists()


def test_capture_ignores_parent_pytest_addopts(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path = fx.artifacts / "baseline.json"

    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(baseline_path),
        env_overrides={"PYTEST_ADDOPTS": "-k definitely_not_a_real_test"},
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    baseline = _load_json(baseline_path)
    assert baseline["collect_nodeids"] == [
        "tests/test_sample.py::test_existing"
    ]


def test_capture_rejects_dirty_content_changed_by_pytest(tmp_path):
    fx = _make_repo(
        tmp_path,
        tests_source=(
            "from pathlib import Path\n\n"
            "def test_mutates_dirty_file():\n"
            "    Path('notes.txt').write_text('changed during pytest\\n', encoding='utf-8')\n"
        ),
    )
    _write(fx.repo / "notes.txt", "dirty before capture\n")
    baseline_path = fx.artifacts / "unstable-baseline.json"

    proc = _run_tool(
        fx,
        "capture-baseline",
        "--out",
        str(baseline_path),
    )

    assert proc.returncode == 3
    assert not baseline_path.exists()


def test_verify_rejects_pytest_normalizing_preexisting_unauthorized_change(
    tmp_path,
):
    fx = _make_repo(
        tmp_path,
        tests_source=(
            "from pathlib import Path\n\n"
            "def test_existing():\n"
            "    Path('notes.txt').write_text('committed\\n', encoding='utf-8')\n"
        ),
    )
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _write(fx.repo / "notes.txt", "UNAUTHORIZED BEFORE VERIFY\n")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 3)
    assert bundle["exit_reason"].startswith("INFRA_FAILURE:")


def test_verify_refuses_tracked_output_path_before_overwrite(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    production_path = fx.repo / "src" / "prod.py"
    before = production_path.read_bytes()

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(production_path),
    )

    assert proc.returncode == 2
    assert production_path.read_bytes() == before


def test_verify_refuses_git_metadata_output_before_overwrite(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    metadata_path = fx.repo / ".git" / "description"
    before = metadata_path.read_bytes()
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        evidence_paths=[
            "scratch/baseline.json",
            "scratch/capsule.json",
            ".git/description",
        ],
    )

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(metadata_path),
    )

    assert proc.returncode == 2
    assert metadata_path.read_bytes() == before


def test_verify_refuses_head_only_tracked_output_before_overwrite(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    _git(fx.repo, "rm", "--cached", "--", "notes.txt")
    output_path = fx.repo / "notes.txt"
    before = output_path.read_bytes()
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        evidence_paths=[
            "scratch/baseline.json",
            "scratch/capsule.json",
            "notes.txt",
        ],
    )

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(output_path),
    )

    assert proc.returncode == 2
    assert output_path.read_bytes() == before


def test_malformed_baseline_cannot_be_overwritten_as_output(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    baseline_path.write_text("{malformed\n", encoding="utf-8")
    before = baseline_path.read_bytes()

    proc = _run_tool(
        fx,
        "verify",
        "--baseline",
        str(baseline_path),
        "--capsule",
        str(capsule_path),
        "--out",
        str(baseline_path),
    )

    assert proc.returncode == 2
    assert baseline_path.read_bytes() == before


def test_exit_zero_requires_every_check_to_be_green():
    dod = [
        {"id": check_id, "verdict": "GREEN", "detail": {}}
        for check_id in VERIFIER.CHECK_IDS
    ]
    dod[-1]["verdict"] = "NOT_RUN"

    assert VERIFIER._aggregate_dod_exit(dod) == 3


def test_happy_path_is_exit_0_and_deterministic(tmp_path):
    fx = _make_repo(tmp_path)
    fixed_sibling = fx.artifacts / "bundle.json.tmp"
    fixed_sibling.write_text("user-owned sibling\n", encoding="utf-8")
    baseline_path, baseline = _capture(fx)
    new_nodeid = "tests/test_sample.py::test_added"
    _write(
        fx.repo / "tests" / "test_sample.py",
        "def test_existing():\n"
        "    assert True\n\n"
        "def test_added():\n"
        "    assert True\n",
    )
    capsule_path = _write_capsule(
        fx,
        baseline_path,
        baseline,
        allowed_write_paths=["tests/test_sample.py"],
        expected_new_nodeids=[new_nodeid],
    )
    proc1, bundle1, bundle_path1 = _verify(fx, baseline_path, capsule_path)
    bundle_bytes1 = bundle_path1.read_bytes()
    proc2, bundle2, bundle_path2 = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc1, bundle1, 0)
    _assert_exit(proc2, bundle2, 0)
    assert [item["id"] for item in bundle1["dod"]] == [
        "C0",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
    ]
    assert {item["verdict"] for item in bundle1["dod"]} == {"GREEN"}
    deterministic_keys = [
        "verifier_exit",
        "exit_reason",
        "files",
        "pytest",
        "nodeids",
        "workspace_delta",
        "dod",
    ]
    assert {
        key: bundle1[key] for key in deterministic_keys
    } == {
        key: bundle2[key] for key in deterministic_keys
    }
    assert bundle_path1 == bundle_path2
    assert bundle_bytes1 == bundle_path2.read_bytes()
    assert fixed_sibling.read_text(encoding="utf-8") == "user-owned sibling\n"
    _assert_bundle_schema(bundle1)
    assert bundle1["schema_version"] == 1
    assert bundle1["capsule_id"] == "isolated-verifier-test"
    assert bundle1["exit_reason"] == "GREEN"


def test_empty_capsule_is_input_invalid_and_emits_bundle(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, _ = _capture(fx)
    capsule_path = fx.artifacts / "empty-capsule.json"
    capsule_path.write_text("{}\n", encoding="utf-8")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 2)
    assert _dod(bundle, "C0")["verdict"] == "RED"


def test_empty_declared_delta_cannot_hide_real_change(tmp_path):
    fx = _make_repo(tmp_path)
    baseline_path, baseline = _capture(fx)
    capsule_path = _write_capsule(fx, baseline_path, baseline)
    _write(fx.repo / "notes.txt", "undeclared change\n")

    proc, bundle, _ = _verify(fx, baseline_path, capsule_path)

    _assert_exit(proc, bundle, 1)
    assert _dod(bundle, "C1")["verdict"] == "RED"
    assert bundle["workspace_delta"]["worktree_delta"] == ["notes.txt"]
