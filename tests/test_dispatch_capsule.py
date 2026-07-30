"""Adversarial tests for the host-only dispatch capsule generator."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = ROOT / "scripts" / "dispatch_capsule.py"
PROVENANCE_DIRECTIVE_PATH = (
    ROOT / "HANDOFF_2026-07-28_SHELL_RC_PROVENANCE_DIRECTIVE.md"
)
REMEDIATION_SPEC_PATH = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-27-shell-rc-remediation-design.md"
)
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


def _provenance_directive_text() -> str:
    return PROVENANCE_DIRECTIVE_PATH.read_text(encoding="utf-8")


def _appendix_source(label: str) -> str:
    text = _provenance_directive_text()
    section_start = text.index(f"## Appendix {label} ")
    fence_start = text.index("```", section_start)
    body_start = text.index("\n", fence_start) + 1
    fence_end = text.index("\n```", body_start)
    return text[body_start : fence_end + 1]


def _module_route_binding_source() -> str:
    text = _provenance_directive_text()
    start = text.index("function Assert-ModuleRouteBinding")
    end = text.index("$CapsuleVerifyArgs", start)
    return text[start:end].rstrip() + "\n"


def _module_binding_payload(root: Path) -> dict[str, object]:
    entry = root / "@oai" / "artifact-tool" / "dist" / "artifact_tool.mjs"
    entry_bytes = entry.read_bytes()
    return {
        "module_roots": [
            {
                "entry_bytes": len(entry_bytes),
                "entry_relpath": "dist/artifact_tool.mjs",
                "entry_sha256": hashlib.sha256(entry_bytes).hexdigest(),
                "package_name": MODULE_PACKAGE,
                "package_version": "2.8.33",
                "root_path": Path(os.path.abspath(root)).as_posix(),
            }
        ]
    }


def _run_module_route_binding(
    tmp_path: Path,
    *,
    capsule: dict[str, object],
    repo: Path,
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "module-route-binding.ps1"
    source = (
        "$ErrorActionPreference = 'Stop'\n"
        "$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)\n"
        "$Repo = [System.IO.Path]::GetFullPath($env:TC_REPO_ROOT)\n"
        "function Throw-InputMismatch([string]$Message) {\n"
        "    throw \"INPUT_MISMATCH: $Message\"\n"
        "}\n"
        f"{_module_route_binding_source()}"
        "$Capsule = $env:TC_CAPSULE_JSON | ConvertFrom-Json\n"
        "try {\n"
        "    Assert-ModuleRouteBinding $Capsule\n"
        "    [Console]::Out.WriteLine('ACCEPTED')\n"
        "    exit 0\n"
        "} catch {\n"
        "    [Console]::Error.WriteLine($_.Exception.Message)\n"
        "    exit 9\n"
        "}\n"
    )
    _write(script, source.encode("utf-8"))
    env = os.environ.copy()
    env["TC_CAPSULE_JSON"] = json.dumps(capsule, separators=(",", ":"))
    env["TC_REPO_ROOT"] = str(repo)
    return _run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=ROOT,
        check=False,
        env=env,
    )


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


MODULE_PACKAGE = "@oai/artifact-tool"
MODULE_ENTRY_BYTES = b"export const SpreadsheetFile = 1;\n"


def _make_module_tree(
    tmp_path: Path,
    *,
    package_name: str = MODULE_PACKAGE,
    manifest: bytes | None = None,
    entry: bytes | None = MODULE_ENTRY_BYTES,
) -> Path:
    root = tmp_path / "modules" / "node_modules"
    package_dir = root
    for part in package_name.split("/"):
        package_dir = package_dir / part
    if manifest is None:
        manifest = json.dumps(
            {
                "name": package_name,
                "version": "2.8.33",
                "type": "module",
                "exports": {".": "./dist/artifact_tool.mjs"},
            }
        ).encode("utf-8")
    _write(package_dir / "package.json", manifest)
    if entry is not None:
        _write(package_dir / "dist" / "artifact_tool.mjs", entry)
    return root


def _capture_with_module(
    tool: ModuleType,
    fixture: RepoFixture,
    capsule_root: Path,
    module_root: Path,
    *,
    package_name: str = MODULE_PACKAGE,
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
        module_specs=((module_root, package_name),),
        now_fn=lambda: now,
    )


def test_capture_schema_version_2_with_empty_module_roots(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)

    path, _digest = _capture(tool, fixture, tmp_path / "capsules")

    payload = json.loads(path.read_bytes())
    assert payload["schema_version"] == 2
    assert payload["module_roots"] == []


def test_capture_measures_module_root_exactly(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)

    path, _digest = _capture_with_module(
        tool, fixture, tmp_path / "capsules", module_root
    )

    payload = json.loads(path.read_bytes())
    assert payload["module_roots"] == [
        {
            "entry_bytes": len(MODULE_ENTRY_BYTES),
            "entry_relpath": "dist/artifact_tool.mjs",
            "entry_sha256": hashlib.sha256(MODULE_ENTRY_BYTES).hexdigest(),
            "package_name": MODULE_PACKAGE,
            "package_version": "2.8.33",
            "root_path": module_root.resolve().as_posix(),
        }
    ]


def test_capture_with_module_root_is_byte_deterministic(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)

    first, first_digest = _capture_with_module(
        tool, fixture, tmp_path / "capsules-a", module_root
    )
    second, second_digest = _capture_with_module(
        tool, fixture, tmp_path / "capsules-b", module_root
    )

    assert first_digest == second_digest
    assert first.read_bytes() == second.read_bytes()


def test_capture_rejects_module_root_inside_repo(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    inside = fixture.repo / "node_modules"
    package_dir = inside / "@oai" / "artifact-tool"
    _write(
        package_dir / "package.json",
        json.dumps(
            {
                "name": MODULE_PACKAGE,
                "version": "2.8.33",
                "exports": {".": "./dist/artifact_tool.mjs"},
            }
        ).encode("utf-8"),
    )
    _write(package_dir / "dist" / "artifact_tool.mjs", MODULE_ENTRY_BYTES)

    with pytest.raises(tool.InputInvalid, match="outside repository"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules", inside
        )


def test_capture_rejects_missing_module_root(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)

    with pytest.raises(tool.InputInvalid, match="module root"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules",
            tmp_path / "modules" / "absent",
        )


def test_capture_rejects_module_package_name_mismatch(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    manifest = json.dumps(
        {
            "name": "@oai/other-tool",
            "version": "2.8.33",
            "exports": {".": "./dist/artifact_tool.mjs"},
        }
    ).encode("utf-8")
    module_root = _make_module_tree(tmp_path, manifest=manifest)

    with pytest.raises(tool.InputInvalid, match="package name mismatch"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules", module_root
        )


def test_capture_rejects_non_string_exports_entry(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    manifest = json.dumps(
        {
            "name": MODULE_PACKAGE,
            "version": "2.8.33",
            "exports": {".": {"import": "./dist/artifact_tool.mjs"}},
        }
    ).encode("utf-8")
    module_root = _make_module_tree(tmp_path, manifest=manifest)

    with pytest.raises(tool.InputInvalid, match="exports entry"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules", module_root
        )


def test_capture_rejects_missing_module_entry_file(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path, entry=None)

    with pytest.raises(tool.InputInvalid, match="module entry"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules", module_root
        )


def test_capture_rejects_module_drift_between_measurements(
    tmp_path,
    monkeypatch,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)
    entry_path = (
        module_root / "@oai" / "artifact-tool" / "dist"
        / "artifact_tool.mjs"
    )
    original = tool._measure_module_specs
    call_count = 0

    def measure_then_mutate(*args, **kwargs):
        nonlocal call_count
        measured = original(*args, **kwargs)
        call_count += 1
        if call_count == 1:
            entry_path.write_bytes(MODULE_ENTRY_BYTES + b"late\n")
        return measured

    monkeypatch.setattr(tool, "_measure_module_specs", measure_then_mutate)

    with pytest.raises(tool.InputInvalid, match="module state changed"):
        _capture_with_module(
            tool, fixture, tmp_path / "capsules", module_root
        )

    assert call_count == 2


def test_verify_accepts_capsule_with_module_roots(tmp_path):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)
    root = tmp_path / "capsules"
    _path, digest = _capture_with_module(tool, fixture, root, module_root)

    payload = _verify(
        tool,
        fixture,
        root,
        digest,
        now_fn=lambda: NOW + 1,
    )

    assert payload["module_roots"][0]["package_name"] == MODULE_PACKAGE


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda c: c.__setitem__("module_roots", {}), "module_roots"),
        (lambda c: c.__setitem__("schema_version", 1), "fixed fields"),
        (
            lambda c: c["module_roots"][0].__setitem__("extra", 1),
            "module_roots",
        ),
        (
            lambda c: c["module_roots"][0].__setitem__(
                "entry_sha256",
                "ABCDEF0123456789ABCDEF0123456789"
                "ABCDEF0123456789ABCDEF0123456789",
            ),
            "module_roots",
        ),
        (
            lambda c: c["module_roots"][0].__setitem__("entry_bytes", True),
            "module_roots",
        ),
        (
            lambda c: c["module_roots"][0].__setitem__(
                "entry_relpath", "C:/abs/entry.mjs"
            ),
            "module",
        ),
        (
            lambda c: c["module_roots"][0].__setitem__(
                "root_path", "C:\\backslash\\node_modules"
            ),
            "module_roots",
        ),
    ],
)
def test_verify_rejects_invalid_module_roots(tmp_path, mutate, match):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)
    root = tmp_path / "capsules"
    path, _digest = _capture_with_module(tool, fixture, root, module_root)
    payload = json.loads(path.read_bytes())
    mutate(payload)
    _path, candidate_digest = _canonical_variant(root, payload)

    with pytest.raises(tool.InputInvalid, match=match):
        _verify(
            tool,
            fixture,
            root,
            candidate_digest,
            now_fn=lambda: NOW + 1,
        )


def test_cli_capture_module_argument_pairing_mismatch_is_exit_2(
    tmp_path,
    capsys,
):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    root = tmp_path / "capsules"

    exit_code = tool.main(
        [
            "capture",
            "--repo", str(fixture.repo),
            "--directive-id", DIRECTIVE_ID,
            "--directive", "HANDOFF.md",
            "--spec", "docs/design.md",
            "--module-root", str(tmp_path / "modules" / "node_modules"),
        ],
        capsule_root=root,
        now_fn=lambda: NOW,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "INPUT_INVALID" in captured.err
    assert not root.exists()


def test_cli_capture_with_module_pair_writes_module_roots(tmp_path, capsys):
    tool = _load_tool()
    fixture = _make_repo(tmp_path)
    module_root = _make_module_tree(tmp_path)
    root = tmp_path / "capsules"

    exit_code = tool.main(
        [
            "capture",
            "--repo", str(fixture.repo),
            "--directive-id", DIRECTIVE_ID,
            "--directive", "HANDOFF.md",
            "--spec", "docs/design.md",
            "--module-root", str(module_root),
            "--module-package", MODULE_PACKAGE,
        ],
        capsule_root=root,
        now_fn=lambda: NOW,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    digest = json.loads(captured.out)["capsule_sha256"]
    payload = json.loads((root / f"{digest}.json").read_bytes())
    assert payload["module_roots"][0]["root_path"] == (
        module_root.resolve().as_posix()
    )


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


def test_provenance_module_binding_rejects_live_exports_retarget(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    module_root = _make_module_tree(tmp_path)
    capsule = _module_binding_payload(module_root)
    package_dir = module_root / "@oai" / "artifact-tool"
    _write(
        package_dir / "package.json",
        json.dumps(
            {
                "name": MODULE_PACKAGE,
                "version": "2.8.33",
                "type": "module",
                "exports": {".": "./dist/other.mjs"},
            }
        ).encode("utf-8"),
    )
    _write(package_dir / "dist" / "other.mjs", b"export const other = 1;\n")

    result = _run_module_route_binding(
        tmp_path,
        capsule=capsule,
        repo=repo,
    )

    assert result.returncode == 9
    assert "module capsule-vs-live mismatch" in result.stderr


def test_provenance_module_binding_accepts_pinned_external_module(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    module_root = _make_module_tree(tmp_path)

    result = _run_module_route_binding(
        tmp_path,
        capsule=_module_binding_payload(module_root),
        repo=repo,
    )

    assert result.returncode == 0
    assert result.stdout == "ACCEPTED\n"
    assert result.stderr == ""


def test_provenance_module_binding_rejects_root_inside_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    module_root = _make_module_tree(repo)

    result = _run_module_route_binding(
        tmp_path,
        capsule=_module_binding_payload(module_root),
        repo=repo,
    )

    assert result.returncode == 9
    assert "module root must be outside repository" in result.stderr


def test_provenance_module_binding_rejects_non_absolute_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    module_root = _make_module_tree(tmp_path)
    capsule = _module_binding_payload(module_root)
    capsule["module_roots"][0]["root_path"] = "relative/node_modules"

    result = _run_module_route_binding(
        tmp_path,
        capsule=capsule,
        repo=repo,
    )

    assert result.returncode == 9
    assert "module path is not absolute" in result.stderr


@pytest.mark.parametrize("component", ["root", "package", "entry_parent"])
def test_provenance_module_binding_rejects_reparse_path_component(
    tmp_path,
    component,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    target_root = _make_module_tree(tmp_path / "target")
    live_root = tmp_path / "live-node-modules"
    target_package = target_root / "@oai" / "artifact-tool"
    if component == "root":
        junction = live_root
        junction_target = target_root
    elif component == "package":
        (live_root / "@oai").mkdir(parents=True)
        junction = live_root / "@oai" / "artifact-tool"
        junction_target = target_package
    else:
        live_package = live_root / "@oai" / "artifact-tool"
        live_package.mkdir(parents=True)
        _write(
            live_package / "package.json",
            (target_package / "package.json").read_bytes(),
        )
        junction = live_package / "dist"
        junction_target = target_package / "dist"
    created = _run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            str(junction),
            str(junction_target),
        ],
        cwd=tmp_path,
        check=False,
    )
    if created.returncode != 0:
        pytest.skip(f"junction creation unavailable: {created.stderr}")
    try:
        result = _run_module_route_binding(
            tmp_path,
            capsule=_module_binding_payload(live_root),
            repo=repo,
        )
    finally:
        os.rmdir(junction)

    assert result.returncode == 9
    assert "module path is link/reparse point" in result.stderr


def test_provenance_appendix_c_accepts_schema_v2_p0_early_stop():
    tree = ast.parse(_appendix_source("C"))
    mismatch_assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "mismatch_schema"
            for target in node.targets
        )
    )
    expression = compile(
        ast.Expression(mismatch_assignment.value),
        "<appendix-c-mismatch-schema>",
        "eval",
    )
    p0 = {
        "schema_version": 2,
        "directive_id": "RB-20260728-shellrc-p0p1",
        "mappings": [{} for _ in range(12)],
        "reconciled": False,
        "p0_blocking_reasons": ["workbook mapping mismatch"],
    }

    accepted = eval(
        expression,
        {
            "DIRECTIVE_ID": "RB-20260728-shellrc-p0p1",
            "p0": p0,
            "valid_reason_list": (
                lambda value, *, allow_empty: (
                    isinstance(value, list)
                    and (allow_empty or bool(value))
                    and all(isinstance(item, str) and item for item in value)
                )
            ),
        },
    )

    assert accepted is True


def test_provenance_identity_literals_match_live_spec_and_generator():
    directive = _provenance_directive_text()
    appendix_c = ast.parse(_appendix_source("C"))
    constants = {
        target.id: node.value.value
        for node in appendix_c.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance((target := node.targets[0]), ast.Name)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    identities = {
        "SPEC": REMEDIATION_SPEC_PATH,
        "GENERATOR": TOOL_PATH,
    }

    for label, path in identities.items():
        raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(ROOT).as_posix()
        blob = _git(ROOT, "hash-object", "--no-filters", "--", relative).stdout.strip()
        table_label = (
            "spec" if label == "SPEC" else "capsule generator"
        )
        capsule_label = "spec" if label == "SPEC" else "generator"

        assert (
            f"| {table_label} raw SHA-256 | `{raw_sha}` |"
            in directive
        )
        assert (
            f"| {table_label} `git hash-object --no-filters` blob | "
            f"`{blob}` |"
            in directive
        )
        assert re.search(
            rf"\$Capsule\.identities\.{capsule_label}\.raw_sha256"
            rf"\s+-ne\s+'{raw_sha}'",
            directive,
        )
        assert re.search(
            rf"\$Capsule\.identities\.{capsule_label}"
            rf"\.git_blob_no_filters\s+-ne\s+'{blob}'",
            directive,
        )
        assert constants[f"{label}_SHA"] == raw_sha
        assert constants[f"{label}_BLOB"] == blob

    spec_sha = hashlib.sha256(REMEDIATION_SPEC_PATH.read_bytes()).hexdigest()
    assert f"SPEC_REVIEW_APPROVED: {spec_sha}" in directive
