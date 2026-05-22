"""Tests for tools/git_safe_push_audit.py (PR 6A required suite).

Each test creates a fresh git repo + bare origin under tmp_path so the audit
runs against real git output (no mocks of git itself). Tests verify that the
audit is read-only and that verdict aggregation responds to staging, branch
divergence, path policy, and Windows-style path inputs.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_TOOL_PATH = _ROOT / "tools" / "git_safe_push_audit.py"
_spec = importlib.util.spec_from_file_location("git_safe_push_audit", _TOOL_PATH)
audit = importlib.util.module_from_spec(_spec)
sys.modules["git_safe_push_audit"] = audit
_spec.loader.exec_module(audit)


def _git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, check=True
    )


def _git_init_workdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["-c", "init.defaultBranch=master", "init"], cwd=path)
    _git(["config", "user.email", "test@test.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)
    _git(["config", "commit.gpgsign", "false"], cwd=path)


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create work repo + bare origin with one shared initial commit on master."""
    bare = tmp_path / "origin.git"
    bare.mkdir()
    _git(["-c", "init.defaultBranch=master", "init", "--bare"], cwd=bare)
    _git(["symbolic-ref", "HEAD", "refs/heads/master"], cwd=bare)

    repo = tmp_path / "repo"
    _git_init_workdir(repo)
    _git(["remote", "add", "origin", str(bare)], cwd=repo)

    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(["add", "README.md"], cwd=repo)
    _git(["commit", "-m", "init"], cwd=repo)
    _git(["push", "origin", "master"], cwd=repo)
    return repo, bare


def _stage_file(repo: Path, rel_path: str, content: str = "x\n") -> None:
    full = repo / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    _git(["add", "--", rel_path], cwd=repo)


def _check(result: dict, check_id: str) -> dict:
    for c in result["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"check {check_id!r} not in result")


def test_docs_only_pass(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "hello\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["docs/foo.md"],
        allowed_prefixes=["docs/"],
        do_fetch=False,
    )

    assert result["verdict"] == "PASS", result
    assert _check(result, "forbidden_path_guard")["status"] == "PASS"
    assert _check(result, "candidate_whitelist_match")["status"] == "PASS"
    assert _check(result, "allowed_whitelist_match")["status"] == "PASS"
    assert _check(result, "head_minus_origin_empty")["status"] == "PASS"


def test_generated_artifact_staged_fails(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "reports/run.html", "<html/>\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["reports/run.html"],
        do_fetch=False,
    )

    assert result["verdict"] == "FAIL"
    fpg = _check(result, "forbidden_path_guard")
    assert fpg["status"] == "FAIL"
    assert any(
        f["path"] == "reports/run.html" for f in fpg["data"]["forbidden"]
    )


def test_unexpected_staged_path_fails(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")
    _stage_file(repo, "docs/bar.md", "b\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["docs/foo.md"],
        do_fetch=False,
    )

    assert result["verdict"] == "FAIL"
    cwm = _check(result, "candidate_whitelist_match")
    assert cwm["status"] == "FAIL"
    assert "docs/bar.md" in cwm["data"]["unexpected"]
    assert cwm["data"]["missing"] == []


def test_behind_origin_fails(tmp_path):
    repo, bare = _make_repo(tmp_path)

    pusher = tmp_path / "pusher"
    _git(["clone", str(bare), str(pusher)], cwd=tmp_path)
    _git(["config", "user.email", "p@t.com"], cwd=pusher)
    _git(["config", "user.name", "Pusher"], cwd=pusher)
    _git(["config", "commit.gpgsign", "false"], cwd=pusher)
    (pusher / "remote.txt").write_text("from remote\n", encoding="utf-8")
    _git(["add", "remote.txt"], cwd=pusher)
    _git(["commit", "-m", "remote ahead"], cwd=pusher)
    _git(["push", "origin", "master"], cwd=pusher)

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=True,
    )

    assert result["verdict"] == "FAIL"
    hme = _check(result, "head_minus_origin_empty")
    assert hme["status"] == "FAIL"
    assert hme["data"]["behind"] >= 1


def test_diverged_branch_fails(tmp_path):
    repo, bare = _make_repo(tmp_path)

    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(["add", "local.txt"], cwd=repo)
    _git(["commit", "-m", "local commit"], cwd=repo)

    pusher = tmp_path / "pusher"
    _git(["clone", str(bare), str(pusher)], cwd=tmp_path)
    _git(["config", "user.email", "p@t.com"], cwd=pusher)
    _git(["config", "user.name", "Pusher"], cwd=pusher)
    _git(["config", "commit.gpgsign", "false"], cwd=pusher)
    (pusher / "remote.txt").write_text("from remote\n", encoding="utf-8")
    _git(["add", "remote.txt"], cwd=pusher)
    _git(["commit", "-m", "remote ahead"], cwd=pusher)
    _git(["push", "origin", "master"], cwd=pusher)

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=1,
        do_fetch=True,
    )

    assert result["verdict"] == "FAIL"
    hme = _check(result, "head_minus_origin_empty")
    assert hme["status"] == "FAIL"
    ab = _check(result, "ahead_behind_count")["data"]
    assert ab["ahead"] == 1
    assert ab["behind"] >= 1


def test_untracked_generated_warn(tmp_path):
    repo, _ = _make_repo(tmp_path)
    rep_dir = repo / "reports"
    rep_dir.mkdir()
    (rep_dir / "stray.html").write_text("<html/>\n", encoding="utf-8")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )

    assert result["verdict"] == "WARN"
    ufr = _check(result, "untracked_forbidden_report")
    assert ufr["status"] == "WARN"
    assert any(
        f["path"] == "reports/stray.html" for f in ufr["data"]["forbidden"]
    )
    assert _check(result, "forbidden_path_guard")["status"] == "PASS"


def test_candidate_whitelist_mismatch_fails(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["docs/foo.md", "docs/bar.md"],
        do_fetch=False,
    )

    assert result["verdict"] == "FAIL"
    cwm = _check(result, "candidate_whitelist_match")
    assert cwm["status"] == "FAIL"
    assert "docs/bar.md" in cwm["data"]["missing"]
    assert cwm["data"]["unexpected"] == []


def test_force_prohibition_notice_present(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )

    assert result["recommended"]["force_prohibited"] is True
    assert result["recommended"]["human_review_required"] is True
    assert "READ-ONLY" in result["recommended"]["note"]
    fpn = _check(result, "force_prohibition_notice")
    assert fpn["status"] == "INFO"
    assert fpn["data"]["force_prohibited"] is True


def test_windows_path_normalization(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=[r"docs\foo.md"],
        allowed_prefixes=[r"docs\\"],
        do_fetch=False,
    )

    assert result["verdict"] == "PASS"
    cwm = _check(result, "candidate_whitelist_match")
    assert cwm["status"] == "PASS"
    assert cwm["data"]["expected"] == ["docs/foo.md"]
    awl = _check(result, "allowed_whitelist_match")
    assert awl["status"] == "PASS"
    assert "docs/" in [p.rstrip("/") + "/" for p in awl["data"]["prefixes"]]


_EXPECTED_CHECK_IDS = [
    "branch_current",
    "remote_fetch",
    "ahead_behind_count",
    "head_minus_origin_empty",
    "origin_minus_head_count",
    "staged_files_list",
    "tracked_dirty",
    "untracked_count",
    "untracked_forbidden_report",
    "allowed_whitelist_match",
    "forbidden_path_guard",
    "candidate_whitelist_match",
    "force_prohibition_notice",
]


def test_markdown_output_pass_contains_verdict_header(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "hello\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["docs/foo.md"],
        allowed_prefixes=["docs/"],
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert md.startswith("# Git Safe Push Audit — PASS")


def test_markdown_output_fail_contains_blocking_reason(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "reports/run.html", "<html/>\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["reports/run.html"],
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "# Git Safe Push Audit — FAIL" in md
    assert "## Failures" in md
    assert "forbidden_path_guard" in md
    assert "Decision required: do not push" in md


def test_markdown_output_warn_lists_untracked_forbidden(tmp_path):
    repo, _ = _make_repo(tmp_path)
    rep_dir = repo / "reports"
    rep_dir.mkdir()
    (rep_dir / "stray.html").write_text("<html/>\n", encoding="utf-8")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "# Git Safe Push Audit — WARN" in md
    assert "## Warnings" in md
    assert "reports/stray.html" in md


def test_markdown_output_contains_recommended_push_command(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "## Recommended push command" in md
    assert "git push origin HEAD:master" in md


def test_markdown_output_contains_force_prohibition(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "--force" in md
    assert "--force-with-lease" in md
    assert "prohibited" in md.lower()


def test_json_default_output_unchanged(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "hello\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        expected_paths=["docs/foo.md"],
        allowed_prefixes=["docs/"],
        do_fetch=False,
    )

    assert result["schema_version"] == 1
    assert result["tool_version"] == "pr6-git-audit-v1"
    assert set(result.keys()) >= {
        "schema_version", "tool_version", "run_id", "generated_at",
        "verdict", "branch", "staging", "path_policy", "checks", "recommended",
    }
    check_ids = [c["id"] for c in result["checks"]]
    assert check_ids == _EXPECTED_CHECK_IDS
    assert set(result["recommended"].keys()) == {
        "push_command", "force_prohibited", "human_review_required", "note",
    }
    assert result["recommended"]["push_command"] == "git push origin HEAD:master"


def test_markdown_output_human_review_reminder(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "human review" in md.lower()


def test_markdown_output_checks_table_completeness(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "a\n")

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=0,
        do_fetch=False,
    )
    md = audit.render_markdown_report(result)

    assert "| ID | Status | Detail |" in md
    for cid in _EXPECTED_CHECK_IDS:
        assert f"`{cid}`" in md, f"check ID {cid!r} missing in markdown"


def test_read_only_audit(tmp_path):
    repo, _ = _make_repo(tmp_path)
    _stage_file(repo, "docs/foo.md", "hello\n")
    (repo / "tracked.txt").write_text("untouched\n", encoding="utf-8")
    _git(["add", "tracked.txt"], cwd=repo)
    _git(["commit", "-m", "second"], cwd=repo)
    (repo / "tracked.txt").write_text("dirty edit\n", encoding="utf-8")

    head_before = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo
    ).strip()
    index_before = (repo / ".git" / "index").read_bytes()
    status_before = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=repo
    )
    worktree_before = {
        p.name: p.read_bytes()
        for p in repo.iterdir()
        if p.is_file()
    }

    result = audit.run_audit(
        cwd=str(repo),
        base="origin/master",
        expected_ahead=1,
        expected_paths=["docs/foo.md"],
        allowed_prefixes=["docs/"],
        do_fetch=False,
    )

    head_after = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo
    ).strip()
    index_after = (repo / ".git" / "index").read_bytes()
    status_after = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=repo
    )
    worktree_after = {
        p.name: p.read_bytes()
        for p in repo.iterdir()
        if p.is_file()
    }

    assert head_before == head_after
    assert index_before == index_after
    assert status_before == status_after
    assert worktree_before == worktree_after
    assert result["verdict"] in {"PASS", "WARN", "FAIL"}


# PR 6C — forbidden path policy drift baseline.
#
# Each baseline test pins the exact ordered tuple of forbidden patterns/prefixes/
# names declared in tools/git_safe_push_audit.py. Tuple-exact comparison (not set
# comparison) is intentional: the goal is to surface ANY drift — including
# reorderings — as a conscious-step trigger so docs/code/test stay aligned per
# the Source-of-truth Policy.
_BASELINE_FORBIDDEN_BASENAME_PATTERNS = (
    "probe_*.xml",
    "_probe_*.py",
    "probe_dump_*.xml",
    "ui_*.xml",
    "popup_*.xml",
    "screenshot_*.png",
)

_BASELINE_FORBIDDEN_DIRECTORY_PREFIXES = (
    "generated/",
    "reports/",
)

# 2026-05-22: "catalog" removed — catalog/ is append-only accumulation state
# (src/catalog.py), tracked as learning data per CLAUDE.md §2.4/§5.6, not a
# regenerable artifact. Baseline updated as the conscious-step drift trigger.
_BASELINE_FORBIDDEN_DIRECTORY_NAMES: tuple[str, ...] = ()


def test_baseline_forbidden_basename_patterns():
    assert audit.FORBIDDEN_BASENAME_PATTERNS == _BASELINE_FORBIDDEN_BASENAME_PATTERNS


def test_baseline_forbidden_directory_prefixes():
    assert audit.FORBIDDEN_DIRECTORY_PREFIXES == _BASELINE_FORBIDDEN_DIRECTORY_PREFIXES


def test_baseline_forbidden_directory_names():
    assert audit.FORBIDDEN_DIRECTORY_NAMES == _BASELINE_FORBIDDEN_DIRECTORY_NAMES
