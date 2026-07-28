"""Adversarial tests for the host-only dispatch capsule generator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = ROOT / "scripts" / "dispatch_capsule.py"
DIRECTIVE_ID = "RB-test-dispatch"
NOW = 1_700_000_000


@dataclass(frozen=True)
class RepoFixture:
    repo: Path
    bare: Path
    directive: Path
    spec: Path
    generator: Path


def _run(
    argv: list[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
        env=env,
    )


def _git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repo, check=check)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _make_repo(
    tmp_path: Path,
    *,
    include_identities: bool = True,
) -> RepoFixture:
    bare = tmp_path / "origin.git"
    bare.mkdir()
    _git(bare, "-c", "init.defaultBranch=master", "init", "--bare")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/master")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "-c", "init.defaultBranch=master", "init")
    _git(repo, "config", "user.email", "capsule@example.invalid")
    _git(repo, "config", "user.name", "Capsule Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "remote", "add", "origin", str(bare))

    _write(repo / ".gitignore", b"ignored/\n")
    _write(repo / "tracked.txt", b"tracked\n")
    directive = repo / "HANDOFF.md"
    spec = repo / "docs" / "design.md"
    generator = repo / "scripts" / "dispatch_capsule.py"
    if include_identities:
        _write(directive, b"directive\n")
        _write(spec, b"design\n")
        _write(generator, b"generator\n")

    _git(repo, "add", ".gitignore", "tracked.txt")
    if include_identities:
        _git(
            repo,
            "add",
            "HANDOFF.md",
            "docs/design.md",
            "scripts/dispatch_capsule.py",
        )
    _git(repo, "commit", "-m", "fixture")
    _git(repo, "push", "-u", "origin", "master")

    _write(repo / "backlog" / "ascii.txt", b"alpha\n")
    _write(repo / "backlog" / "\ud55c\uae00.txt", b"beta\n")
    _write(repo / "ignored" / "cache.bin", b"\x00\xffA")
    _write(repo / "ignored" / "\u00e9.txt", "caf\u00e9\n".encode("utf-8"))

    return RepoFixture(
        repo=repo,
        bare=bare,
        directive=directive,
        spec=spec,
        generator=generator,
    )


def _load_tool() -> ModuleType:
    assert TOOL_PATH.is_file(), "scripts/dispatch_capsule.py is not implemented"
    spec = importlib.util.spec_from_file_location("dispatch_capsule", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["dispatch_capsule"] = module
    spec.loader.exec_module(module)
    return module


def _capture(
    tool: ModuleType,
    fixture: RepoFixture,
    capsule_root: Path,
    *,
    now: int = NOW,
) -> tuple[Path, str]:
    return tool.capture_capsule(
        repo=fixture.repo,
        capsule_root=capsule_root,
        directive_id=DIRECTIVE_ID,
        directive_path=Path("HANDOFF.md"),
        spec_path=Path("docs/design.md"),
        generator_path=Path("scripts/dispatch_capsule.py"),
        upstream_ref="origin/master",
        now_fn=lambda: now,
    )


def _verify(
    tool: ModuleType,
    fixture: RepoFixture,
    capsule_root: Path,
    digest: str,
    *,
    now_fn: Callable[[], int],
) -> dict[str, object]:
    return tool.verify_capsule(
        repo=fixture.repo,
        capsule_root=capsule_root,
        capsule_sha256=digest,
        expected_directive_id=DIRECTIVE_ID,
        expected_directive_path=Path("HANDOFF.md"),
        expected_spec_path=Path("docs/design.md"),
        now_fn=now_fn,
    )


def _status_bytes(repo: Path) -> bytes:
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout


def _canonical_variant(root: Path, value: object) -> tuple[Path, str]:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = root / f"{digest}.json"
    path.write_bytes(raw)
    return path, digest


def test_canonical_json_bytes_is_utf8_compact_sorted_without_trailing_lf():
    tool = _load_tool()

    assert tool.canonical_json_bytes({"z": 1, "a": "\ud55c"}) == (
        '{"a":"\ud55c","z":1}'.encode("utf-8")
    )


def test_measure_index_hashes_exact_raw_ls_files_stage_z_bytes(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path, include_identities=False)

    assert tool.measure_index(fixture.repo) == {
        "entry_count": 2,
        "raw_stage_z_sha256":
            "2074df46ace65ffd105532da969ef72c6dbe2abb264b261ea0d8f792246186dc",
    }


def test_git_success_with_stderr_is_infrastructure_failure(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    completed = subprocess.CompletedProcess(
        args=["git"],
        returncode=0,
        stdout=b"",
        stderr=b"warning: incomplete identity\n",
    )
    monkeypatch.setattr(tool, "_run_git", lambda *_args, **_kwargs: completed)

    with pytest.raises(tool.InfrastructureFailure, match="emitted stderr"):
        tool.measure_index(tmp_path)


def test_measure_untracked_map_matches_hand_derived_literal(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)

    measured = tool.measure_path_map(fixture.repo, ignored=False)

    assert measured["count"] == 2
    assert measured["canonical_json_sha256"] == (
        "d4cc7398b3568c89801a4adfd5f14cf38e034e1733a6ffe511a44ef1fbce550b"
    )
    assert measured["rows"] == [
        {
            "file_type": "file",
            "git_hash_object_no_filters":
                "4a58007052a65fbc2fc3f910f2855f45a4058e74",
            "path": "backlog/ascii.txt",
        },
        {
            "file_type": "file",
            "git_hash_object_no_filters":
                "65b2df87f7df3aeedef04be96703e55ac19c2cfb",
            "path": "backlog/\ud55c\uae00.txt",
        },
    ]


def test_measure_ignored_map_matches_hand_derived_literal(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)

    measured = tool.measure_path_map(fixture.repo, ignored=True)

    assert measured["count"] == 2
    assert measured["canonical_json_sha256"] == (
        "3e6a0aa62f698c69b058496c6b3ae54c473352b3859fe900aebc2443a6d193c4"
    )


def test_path_map_uses_hash_object_no_filters(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    _write(
        fixture.repo / ".gitattributes",
        b"backlog/*.txt text eol=crlf\n",
    )
    _git(fixture.repo, "add", ".gitattributes")
    _git(fixture.repo, "commit", "-m", "add filter rule")
    _git(fixture.repo, "push", "origin", "master")
    expected_raw = b"alpha\n"
    expected_blob = hashlib.sha1(
        f"blob {len(expected_raw)}\0".encode("ascii") + expected_raw
    ).hexdigest()

    measured = tool.measure_path_map(fixture.repo, ignored=False)

    assert measured["rows"][0] == {
        "file_type": "file",
        "git_hash_object_no_filters": expected_blob,
        "path": "backlog/ascii.txt",
    }


def test_capture_writes_one_external_content_addressed_capsule(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    status_before = _status_bytes(fixture.repo)

    path, digest = _capture(tool, fixture, root)

    raw = path.read_bytes()
    payload = json.loads(raw)
    assert path == root / f"{digest}.json"
    assert hashlib.sha256(raw).hexdigest() == digest
    assert set(root.iterdir()) == {path}
    assert _status_bytes(fixture.repo) == status_before
    assert payload["issued_at_epoch_s"] == NOW
    assert payload["expires_at_epoch_s"] == NOW + 1800
    assert payload["ttl_seconds"] == 1800
    assert "capsule_sha256" not in payload
    assert "capsule_path" not in payload


def test_capture_same_state_and_clock_is_byte_deterministic(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)

    first, first_digest = _capture(tool, fixture, tmp_path / "capsules-a")
    second, second_digest = _capture(tool, fixture, tmp_path / "capsules-b")

    assert first_digest == second_digest
    assert first.read_bytes() == second.read_bytes()


def test_capture_rejects_output_inside_repo_without_writing(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = fixture.repo / "capsules"

    with pytest.raises(tool.InputInvalid, match="outside repository"):
        _capture(tool, fixture, root)

    assert not root.exists()


def test_capture_rejects_nonexistent_root_below_linklike_ancestor(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    linklike_ancestor = tmp_path / "external"
    (linklike_ancestor / "ordinary").mkdir(parents=True)
    root = linklike_ancestor / "ordinary" / "capsules"
    original = tool._is_linklike

    def mark_ancestor(path):
        lexical = Path(os.path.abspath(path))
        if lexical == Path(os.path.abspath(linklike_ancestor)):
            return True
        return original(path)

    monkeypatch.setattr(tool, "_is_linklike", mark_ancestor)
    with pytest.raises(tool.InputInvalid, match="unsafe"):
        _capture(tool, fixture, root)

    assert not root.exists()


def test_capture_refuses_preexisting_digest_target_without_overwrite(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    source, digest = _capture(tool, fixture, tmp_path / "capsules-a")
    root = tmp_path / "capsules-b"
    root.mkdir()
    target = root / f"{digest}.json"
    target.write_bytes(b"sentinel")

    with pytest.raises(tool.InputInvalid, match="already exists"):
        _capture(tool, fixture, root)

    assert target.read_bytes() == b"sentinel"
    assert source.is_file()


@pytest.mark.parametrize("mode", ["tracked", "staged", "ahead"])
def test_capture_rejects_non_dispatchable_repo_state(tmp_path, mode):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    if mode == "tracked":
        _write(fixture.repo / "tracked.txt", b"changed\n")
    elif mode == "staged":
        _write(fixture.repo / "tracked.txt", b"changed\n")
        _git(fixture.repo, "add", "tracked.txt")
    else:
        _write(fixture.repo / "new.txt", b"new\n")
        _git(fixture.repo, "add", "new.txt")
        _git(fixture.repo, "commit", "-m", "ahead")

    with pytest.raises(tool.InputInvalid, match="dispatchable"):
        _capture(tool, fixture, tmp_path / "capsules")

    assert not (tmp_path / "capsules").exists()


def test_capture_rejects_state_change_between_measurements(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    original = tool.measure_repo_state
    call_count = 0

    def measure_then_mutate(*args, **kwargs):
        nonlocal call_count
        measured = original(*args, **kwargs)
        call_count += 1
        if call_count == 1:
            _write(fixture.repo / "backlog" / "late.txt", b"late\n")
        return measured

    monkeypatch.setattr(tool, "measure_repo_state", measure_then_mutate)

    with pytest.raises(tool.InputInvalid, match="changed during capture"):
        _capture(tool, fixture, tmp_path / "capsules")

    assert call_count == 2
    assert not (tmp_path / "capsules").exists()


def test_capture_publish_failure_leaves_no_final_or_temp_file(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"

    def fail_link(_source, _target):
        raise OSError("injected link failure")

    monkeypatch.setattr(tool.os, "link", fail_link)
    with pytest.raises(tool.InfrastructureFailure, match="publish"):
        _capture(tool, fixture, root)

    assert root.is_dir()
    assert list(root.iterdir()) == []


def test_verify_accepts_exact_live_state_before_expiry_without_writes(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    path, digest = _capture(tool, fixture, root)
    raw_before = path.read_bytes()
    mtime_before = path.stat().st_mtime_ns
    children_before = tuple(root.iterdir())
    status_before = _status_bytes(fixture.repo)

    payload = _verify(
        tool,
        fixture,
        root,
        digest,
        now_fn=lambda: NOW + 1,
    )

    assert payload["directive_id"] == DIRECTIVE_ID
    assert path.read_bytes() == raw_before
    assert path.stat().st_mtime_ns == mtime_before
    assert tuple(root.iterdir()) == children_before
    assert _status_bytes(fixture.repo) == status_before


def test_verify_rejects_later_synced_head_when_repo_is_dispatchable(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)
    _write(fixture.repo / "tracked.txt", b"later\n")
    _git(fixture.repo, "add", "tracked.txt")
    _git(fixture.repo, "commit", "-m", "later synced head")
    _git(fixture.repo, "push", "origin", "master")
    assert _git(
        fixture.repo,
        "rev-list",
        "--left-right",
        "--count",
        "origin/master...HEAD",
    ).stdout.strip() == "0\t0"

    with pytest.raises(tool.InputInvalid, match="live repository state"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: NOW + 1,
        )


def test_verify_rejects_wrong_expected_directive_id(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)

    with pytest.raises(tool.InputInvalid, match="fixed fields"):
        tool.verify_capsule(
            repo=fixture.repo,
            capsule_root=root,
            capsule_sha256=digest,
            expected_directive_id="RB-other-dispatch",
            expected_directive_path=Path("HANDOFF.md"),
            expected_spec_path=Path("docs/design.md"),
            now_fn=lambda: NOW + 1,
        )


@pytest.mark.parametrize(
    ("field_path", "bad_value"),
    [
        (("repo", "upstream_ref"), "HEAD"),
        (("identities", "directive", "path"), "tracked.txt"),
        (("identities", "spec", "path"), "tracked.txt"),
    ],
)
def test_verify_rejects_alternate_ref_or_identity_path(
    tmp_path,
    field_path,
    bad_value,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    path, _digest = _capture(tool, fixture, root)
    payload = json.loads(path.read_bytes())
    target = payload
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = bad_value
    _path, candidate_digest = _canonical_variant(root, payload)

    with pytest.raises(tool.InputInvalid):
        _verify(
            tool,
            fixture,
            root,
            candidate_digest,
            now_fn=lambda: NOW + 1,
        )


@pytest.mark.parametrize("variant", ["tamper", "trailing-lf", "extra-key"])
def test_verify_rejects_non_exact_capsule_contract(tmp_path, variant):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    path, digest = _capture(tool, fixture, root)
    payload = json.loads(path.read_bytes())
    if variant == "tamper":
        path.write_bytes(path.read_bytes()[:-1] + b" ")
        candidate_digest = digest
    elif variant == "trailing-lf":
        raw = path.read_bytes() + b"\n"
        candidate_digest = hashlib.sha256(raw).hexdigest()
        (root / f"{candidate_digest}.json").write_bytes(raw)
    else:
        payload["unexpected"] = True
        _, candidate_digest = _canonical_variant(root, payload)

    with pytest.raises(tool.InputInvalid):
        _verify(
            tool,
            fixture,
            root,
            candidate_digest,
            now_fn=lambda: NOW + 1,
        )


@pytest.mark.parametrize(
    ("field_path", "bad_value"),
    [
        (("schema_version",), True),
        (("repo", "head_sha"), None),
        (("index", "raw_stage_z_sha256"), 7),
        (("identities", "directive", "raw_sha256"), []),
    ],
)
def test_verify_rejects_wrong_json_types_as_input_invalid(
    tmp_path,
    field_path,
    bad_value,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    path, _digest = _capture(tool, fixture, root)
    payload = json.loads(path.read_bytes())
    target = payload
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = bad_value
    _path, candidate_digest = _canonical_variant(root, payload)

    with pytest.raises(tool.InputInvalid):
        _verify(
            tool,
            fixture,
            root,
            candidate_digest,
            now_fn=lambda: NOW + 1,
        )


def test_verify_rejects_lone_surrogate_as_input_invalid(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    root.mkdir()
    raw = b'{"unexpected":"\\ud800"}'
    digest = hashlib.sha256(raw).hexdigest()
    (root / f"{digest}.json").write_bytes(raw)

    with pytest.raises(tool.InputInvalid, match="canonical"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: NOW + 1,
        )


def test_verify_rejects_uppercase_capsule_token(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)

    with pytest.raises(tool.InputInvalid, match="lowercase SHA-256"):
        _verify(
            tool,
            fixture,
            root,
            digest.upper(),
            now_fn=lambda: NOW + 1,
        )


@pytest.mark.parametrize("now", [NOW - 1, NOW + 1800])
def test_verify_rejects_future_or_expired_capsule(tmp_path, now):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)

    with pytest.raises(tool.InputInvalid, match="TTL"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: now,
        )


def test_verify_rechecks_ttl_after_live_measurement(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)
    times = iter([NOW + 1, NOW + 1800])

    with pytest.raises(tool.InputInvalid, match="TTL"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: next(times),
        )


def test_verify_rejects_drift_after_first_live_snapshot(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)
    original = tool.measure_repo_state
    call_count = 0

    def measure_then_mutate(*args, **kwargs):
        nonlocal call_count
        measured = original(*args, **kwargs)
        call_count += 1
        if call_count == 1:
            _write(fixture.repo / "backlog" / "late.txt", b"late\n")
        return measured

    monkeypatch.setattr(tool, "measure_repo_state", measure_then_mutate)
    with pytest.raises(tool.InputInvalid, match="live repository state"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: NOW + 1,
        )

    assert call_count == 2


@pytest.mark.parametrize("kind", ["untracked", "ignored", "tracked"])
def test_verify_rejects_live_repo_drift(tmp_path, kind):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture(tool, fixture, root)
    if kind == "untracked":
        _write(fixture.repo / "backlog" / "ascii.txt", b"changed\n")
    elif kind == "ignored":
        _write(fixture.repo / "ignored" / "cache.bin", b"changed\n")
    else:
        _write(fixture.repo / "tracked.txt", b"changed\n")

    with pytest.raises(tool.InputInvalid, match="live repository state"):
        _verify(
            tool,
            fixture,
            root,
            digest,
            now_fn=lambda: NOW + 1,
        )


def test_missing_git_is_infrastructure_failure(tmp_path, monkeypatch):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    monkeypatch.setenv("PATH", "")

    with pytest.raises(tool.InfrastructureFailure, match="could not start"):
        tool.measure_index(fixture.repo)


def test_cli_malformed_hash_is_exit_2_without_capsule_write(tmp_path, capsys):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"

    exit_code = tool.main(
        [
            "verify",
            "--repo", str(fixture.repo),
            "--capsule-sha256", "BAD",
            "--expected-directive-id", DIRECTIVE_ID,
            "--expected-directive", "HANDOFF.md",
            "--expected-spec", "docs/design.md",
        ],
        capsule_root=root,
        now_fn=lambda: NOW,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "INPUT_INVALID" in captured.err
    assert not root.exists()


def test_main_git_spawn_failure_is_exit_3_without_capsule_write(
    tmp_path,
    monkeypatch,
    capsys,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"
    monkeypatch.setenv("PATH", "")

    exit_code = tool.main(
        [
            "capture",
            "--repo", str(fixture.repo),
            "--directive-id", DIRECTIVE_ID,
            "--directive", "HANDOFF.md",
            "--spec", "docs/design.md",
        ],
        capsule_root=root,
        now_fn=lambda: NOW,
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert captured.out == ""
    assert "INFRA_FAILURE" in captured.err
    assert not root.exists()
