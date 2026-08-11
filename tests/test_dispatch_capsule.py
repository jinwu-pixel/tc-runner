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


def _appendix_namespace(label: str) -> dict[str, object]:
    namespace: dict[str, object] = {
        "__name__": f"appendix_{label.lower()}_contract_test",
    }
    exec(
        compile(
            _appendix_source(label),
            f"<appendix-{label.lower()}-contract>",
            "exec",
        ),
        namespace,
    )
    return namespace


def _appendix_a_targets() -> list[dict[str, object]]:
    source = _appendix_source("A")
    start = source.index("const TARGETS = ") + len("const TARGETS = ")
    end = source.index(";\n  const HEADER_PATTERNS", start)
    expression = source[start:end]
    result = _run(
        [
            "node",
            "-e",
            "const targets = (" + expression + ");" +
            "process.stdout.write(JSON.stringify(targets));",
        ],
        cwd=ROOT,
    )
    value = json.loads(result.stdout)
    assert isinstance(value, list)
    return value


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


RECONCILE_MANIFEST_ROWS = (
    ("exported_ss_call/SS_TC01_permission_denied.yaml",
     "SS_TC01_permission_denied", "SS-TC 1",
     (("TC-01", "\uad8c\ud55c \ubbf8\ubd80\uc5ec \uae30\ubcf8 \ub3d9\uc791 \ud655\uc778"),),
     ((10, "TC-01"), (11, "TC-01"))),
    ("exported_ss_call/SS_TC02_permission_allow_idle.yaml",
     "SS_TC02_permission_allow_idle", "SS-TC 1",
     (("TC-02", "\uad8c\ud55c \ud5c8\uc6a9 \ud6c4 Idle \uc9c4\uc785 \ud655\uc778"),), ((11, "TC-02"),)),
    ("exported_ss_call/SS_TC03_ringing_permission.yaml",
     "SS_TC03_ringing_permission", "SS-TC 1",
     (("TC-03", "RINGING \uc911 \uad8c\ud55c \ud5c8\uc6a9 \uc2dc \ud604\uc7ac \ud1b5\ud654 \uac10\uc9c0"),),
     ((15, "TC-03"),)),
    ("exported_ss_call/SS_TC04_offhook_seed_recovery.yaml",
     "SS_TC04_offhook_seed_recovery", "SS-TC 1",
     (("TC-04", "OFFHOOK \ub3c4\uc911 \uad8c\ud55c \ud5c8\uc6a9 \uc2dc seed \ubcf5\uad6c \ud655\uc778"),),
     ((18, "TC-04"),)),
    ("exported_ss_call/SS_TC05_boundary_values.yaml",
     "SS_TC05_boundary_values", "SS-TC 1",
     (("TC-05A", "9\ucd08 \uacbd\uacc4\uac12 \uac80\uc99d"),
      ("TC-05B", "10\ucd08 \uacbd\uacc4\uac12 \uac80\uc99d"),
      ("TC-05C", "11\ucd08 \uacbd\uacc4\uac12 \uac80\uc99d")), ((9, "TC-05A"),)),
    ("exported_ss_call/SS_TC06_missed_rejected.yaml",
     "SS_TC06_missed_rejected", "SS-TC 1",
     (("TC-06", "\ubd80\uc7ac\uc911/\uac70\uc808 \ud1b5\ud654 \ucc98\ub9ac \ud655\uc778"),),
     ((10, "TC-06"), (11, "TC-06"))),
    ("exported_ss_call/SS_TC07_short_call_no_false_positive.yaml",
     "SS_TC07_short_call_no_false_positive", "SS-TC 1",
     (("TC-07", "\uc9e7\uc740 \uc815\uc0c1 \ud1b5\ud654 \uc624\ud0d0 \ubc29\uc9c0"),), ((9, "TC-07"),)),
    ("exported_ss_call/SS_TC09_offhook_permission_banking.yaml",
     "SS_TC09_offhook_permission_banking", "SS-TC 1",
     (("TC-09", "OFFHOOK \uc911 \uad8c\ud55c \ud5c8\uc6a9 \ud6c4 \uae08\uc735 \uc571 \uac1c\uc785 \ud655\uc778"),),
     ((20, "TC-09"),)),
    ("exported_ss_call/SS_TC0_P0_endcall_crash.yaml",
     "SS_TC0_P0_endcall_crash", "SS-TC 0",
     (("T/C-01", "\uacbd\uace0 \ud31d\uc5c5\uc758 \"\uc9c0\uae08 \uc804\ud654 \ub04a\uae30\" \ubc84\ud2bc \uacbd\ub85c\uc5d0\uc11c \ub2e4\uc774\uc5bc\ub7ec \ud06c\ub798\uc2dc \uc7ac\ubc1c \uc5ec\ubd80\uc640 dismiss\u2192suppression\u2192delayed endCall\u2192IDLE\u2192suppression release \uc21c\uc11c \uac80\uc99d"),),
     ((15, "T/C-01"),)),
    ("exported_ss_call/SS_TC10_permission_toggle.yaml",
     "SS_TC10_permission_toggle", "SS-TC 1",
     (("TC-10", "true\u2192false\u2192true \uad8c\ud55c \ud754\ub4e4\uae30"),), ((24, "TC-10"),)),
    ("exported_ss_call/SS_TC11_multi_subscription.yaml",
     "SS_TC11_multi_subscription", "SS-TC 1",
     (("TC-11", "\ub2e4\uc911 \uad6c\ub3c5 \uc548\uc804\uc131 \ud655\uc778"),),
     ((20, "TC-11"), (21, "TC-11"))),
    ("exported_ss_call/SS_TC12_legacy_path.yaml",
     "SS_TC12_legacy_path", "SS-TC 1",
     (("TC-12", "Legacy \uacbd\ub85c \ud604\uc7ac \uc0c1\ud0dc \ubc18\uc601 \ud655\uc778"),), ((19, "TC-12"),)),
)


def _expected_reconcile_manifest() -> list[dict[str, object]]:
    return [
        {
            "yaml_path": path,
            "yaml_tc_name": name,
            "sheet": sheet,
            "source_selectors": [
                {
                    "source_no": source_no,
                    "source_functionality_effective": functionality,
                }
                for source_no, functionality in selectors
            ],
            "blocker_bindings": [
                {"blocker_step_index": index, "source_no": source_no}
                for index, source_no in blockers
            ],
        }
        for path, name, sheet, selectors, blockers in RECONCILE_MANIFEST_ROWS
    ]


def _green_reconciliation_fixture(
    source_keys: list[tuple[str, str]], *, schema_version: int = 2,
) -> dict[str, object]:
    targets = [
        {
            "yaml_path": path,
            "blocker_step_index": index,
            "source_no": source_no,
            "tracked_tc_name_match": True,
            "emitted_name_match": True,
            "procedure_prefix_match": True,
            "source_content_hash_match": True,
            "candidate_count": 1,
            "step_join_verdict": "RECONCILED",
            "verdict": "RECONCILED",
            "emitted_step_index": index,
        }
        for path, _name, _sheet, _selectors, blockers
        in RECONCILE_MANIFEST_ROWS
        for index, source_no in blockers
    ]
    documents = [
        {
            "yaml_path": path,
            "source_no": source_no,
            "tracked_tc_name_match": True,
            "emitted_name_match": True,
            "procedure_prefix_match": True,
            "source_content_hash_match": True,
            "runnable": True,
            "has_unresolved_params": False,
            "verdict": "RECONCILED",
        }
        for path, source_no in source_keys
    ]
    return {
        "schema_version": schema_version,
        "directive_id": "RB-20260728-shellrc-p0p1",
        "reconciled": True,
        "blocking_reasons": [],
        "verdict": "PROVENANCE_RECONCILED",
        "targets": targets,
        "mapped_document_status": documents,
        "producer_counts": [
            {"sheet_label": "SS-TC-0", "dry_total": 1, "created": 1,
             "inventory_count": 1, "skipped": 0},
            {"sheet_label": "SS-TC-1", "dry_total": 1, "created": 1,
             "inventory_count": 1, "skipped": 0},
        ],
        "inventories": [
            {"relative_path": "SS-TC-0/a.yaml", "raw_sha256": "0" * 64,
             "semantic_sha256": "1" * 64},
            {"relative_path": "SS-TC-1/b.yaml", "raw_sha256": "2" * 64,
             "semantic_sha256": "3" * 64},
        ],
        "document_step_projection_report": [
            {"yaml_path": path, "source_no": source_no, "gating": False}
            for path, source_no in source_keys
        ],
    }


def _appendix_b_cell(coordinate: str, value: object) -> dict[str, object]:
    return {
        "coordinate": coordinate,
        "artifact_value": value,
        "formula": None,
        "display_formula_view": None,
        "cached_or_displayed_value": None,
        "loader_value": value,
        "region_request": {"coordinate": coordinate},
        "region_ndjson": json.dumps({"coordinate": coordinate}) + "\n",
        "region_sha256": "0" * 64,
    }


def _run_real_appendix_b_reconcile(
    tmp_path: Path,
    *,
    mutate_p0: Callable[[dict[str, object]], None] | None = None,
    mutate_emitted: Callable[
        [dict[tuple[str, str], dict[str, object]]], None
    ] | None = None,
) -> tuple[dict[str, object], int, str]:
    appendix = _appendix_namespace("B")
    appendix["EXPECTED_TEMP"] = tmp_path
    # These three checks validate artifact-tool-specific evidence envelopes.
    # The fixture deliberately retains the real sheet/selector consistency
    # checks and every producer/tracked/source/step reconciliation operation.
    appendix["valid_cell_evidence"] = lambda _cell, _sheet: True
    appendix["valid_region_record"] = lambda _record, _sheet: True
    appendix["valid_render_evidence"] = lambda _sheet: True

    p0_fields = tuple(appendix["P0_FIELDS"])
    column_map = {field: index for index, field in enumerate(p0_fields)}
    row_inventories = {"SS-TC 0": [], "SS-TC 1": []}
    mappings: list[dict[str, object]] = []
    emitted: dict[tuple[str, str], dict[str, object]] = {}
    repo = tmp_path / "repo"
    out0 = tmp_path / "SS-TC-0"
    out1 = tmp_path / "SS-TC-1"
    repo.mkdir()
    out0.mkdir()
    out1.mkdir()
    next_row = {"SS-TC 0": 2, "SS-TC 1": 2}

    for path, yaml_name, sheet, selectors, blockers in RECONCILE_MANIFEST_ROWS:
        max_step = max(index for index, _source_no in blockers)
        tracked_steps = [
            {
                "action": f"action-{index}",
                "command": f"command-{index}",
                "expected": f"expected-{index}",
            }
            for index in range(1, max_step + 1)
        ]
        tracked = {
            "tc_name": yaml_name,
            "metadata": {"source": f"TC_1.xlsx / {sheet}"},
            "steps": tracked_steps,
        }
        tracked_path = repo / Path(path)
        tracked_path.parent.mkdir(parents=True, exist_ok=True)
        tracked_path.write_text(
            appendix["yaml"].safe_dump(
                tracked, allow_unicode=True, sort_keys=False,
            ),
            encoding="utf-8",
        )

        selector_results = []
        for source_no, functionality in selectors:
            physical_row = next_row[sheet]
            next_row[sheet] += 1
            feature = "Feature"
            procedure = f"procedure:{source_no}"
            expected = f"expected:{source_no}"
            priority = "P1"
            values = (
                source_no, feature, functionality, "precondition",
                procedure, expected, priority,
            )
            cells = [
                _appendix_b_cell(
                    f"{appendix['column_name'](index)}{physical_row}", value,
                )
                for index, value in enumerate(values)
            ]
            region_records = [
                {
                    "coordinate": cell["coordinate"],
                    "region_request": cell["region_request"],
                    "region_ndjson": cell["region_ndjson"],
                    "region_sha256": cell["region_sha256"],
                }
                for cell in cells
            ]
            workbook_tc_name = f"{source_no}_{feature}"
            selector = {
                "source_no": source_no,
                "source_functionality_effective": functionality,
                "candidate_count": 1,
                "workbook_sheet": sheet,
                "workbook_physical_row": physical_row,
                "workbook_tc_name": workbook_tc_name,
                "source_feature_name_raw": feature,
                "source_feature_name_effective": feature,
                "source_feature_anchor_row": physical_row,
                "source_functionality_raw": functionality,
                "source_functionality_anchor_row": physical_row,
                "source_precondition": "precondition",
                "source_procedure": procedure,
                "source_expected": expected,
                "source_priority": priority,
                "cells": cells,
                "carry_forward_cells": [cells[1], cells[2]],
                "cell_region_records": region_records,
            }
            selector_results.append(selector)
            row_inventories[sheet].append(
                {
                    "physical_row": physical_row,
                    "tc_name": workbook_tc_name,
                    "source_no": source_no,
                    "source_feature_name_raw": feature,
                    "source_feature_name_effective": feature,
                    "source_feature_anchor_row": physical_row,
                    "source_functionality_raw": functionality,
                    "source_functionality_effective": functionality,
                    "source_functionality_anchor_row": physical_row,
                    "source_precondition": "precondition",
                    "source_procedure": procedure,
                    "source_expected": expected,
                    "source_priority": priority,
                }
            )
            document = {
                "name": workbook_tc_name,
                "description": procedure[:200],
                "metadata": {
                    "source_file": "TC_1.xlsx",
                    "source_sheet": sheet,
                    "source_row": physical_row,
                    "runnable": True,
                    "has_unresolved_params": False,
                },
                "steps": [dict(step) for step in tracked_steps],
            }
            emitted[(path, source_no)] = {
                "document": document,
                "directory": out0 if sheet == "SS-TC 0" else out1,
                "filename": appendix["make_filename"](
                    workbook_tc_name, procedure, expected,
                ),
            }

        mappings.append(
            {
                "yaml_path": path,
                "yaml_tc_name": yaml_name,
                "declared_source_file": "TC_1.xlsx",
                "declared_source_sheet": sheet,
                "source_selectors": selector_results,
                "blocker_bindings": [
                    {"blocker_step_index": index, "source_no": source_no}
                    for index, source_no in blockers
                ],
                "verdict": "RECONCILED",
            }
        )

    sheets = []
    for sheet in ("SS-TC 0", "SS-TC 1"):
        end_row = max(row["physical_row"] for row in row_inventories[sheet])
        sheets.append(
            {
                "sheet_name": sheet,
                "column_map": column_map,
                "header_physical_row": 1,
                "used_range": f"A1:G{end_row}",
                "used_start_row": 1,
                "used_start_column": 1,
                "used_matrix_height": end_row,
                "used_matrix_width": 7,
                "expanded_physical_height": end_row,
                "expanded_physical_width": 7,
                "header_cells": [
                    {
                        "field": field,
                        **_appendix_b_cell(
                            f"{appendix['column_name'](index)}1", field,
                        ),
                    }
                    for index, field in enumerate(p0_fields)
                ],
                "row_inventory": row_inventories[sheet],
            }
        )
    sheet_overview = json.dumps(
        {"sheets": ["SS-TC 0", "SS-TC 1"]},
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"
    p0: dict[str, object] = {
        "schema_version": 3,
        "directive_id": "RB-20260728-shellrc-p0p1",
        "sheet_overview_ndjson": sheet_overview,
        "sheet_overview_sha256": hashlib.sha256(
            sheet_overview.encode("utf-8")
        ).hexdigest(),
        "sheets": sheets,
        "mappings": mappings,
        "p0_blocking_reasons": [],
        "reconciled": True,
    }
    if mutate_p0 is not None:
        mutate_p0(p0)
    if mutate_emitted is not None:
        mutate_emitted(emitted)

    p0_path = tmp_path / "p0.json"
    p0_path.write_text(json.dumps(p0, ensure_ascii=False), encoding="utf-8")
    for item in emitted.values():
        output_path = item["directory"] / item["filename"]
        output_path.write_text(
            appendix["yaml"].safe_dump(
                item["document"], allow_unicode=True, sort_keys=False,
            ),
            encoding="utf-8",
        )
    for label, count in (("SS-TC-0", 1), ("SS-TC-1", 13)):
        (tmp_path / f"dry-run-{label}.combined.txt").write_text(
            f"Total: {count} TCs\n", encoding="utf-8",
        )
        (tmp_path / f"export-{label}.combined.txt").write_text(
            f"  생성      : {count}개\n  건너뜀    : 0개\n",
            encoding="utf-8",
        )

    output = tmp_path / "reconciliation.json"
    temporary = tmp_path / "reconciliation.json.tmp"
    args = appendix["argparse"].Namespace(
        repo=repo, p0=p0_path, out0=out0, out1=out1, output=output,
    )
    reconcile_v2 = appendix["reconcile_v2"]
    invocations = 0

    def invoke() -> int:
        nonlocal invocations
        invocations += 1
        return reconcile_v2(args, temporary)

    assert invoke() == 0
    return (
        json.loads(output.read_text(encoding="utf-8")),
        invocations,
        reconcile_v2.__code__.co_filename,
    )


def test_provenance_appendix_b_real_reconcile_accepts_aggregate(tmp_path):
    result, invocations, source = _run_real_appendix_b_reconcile(tmp_path)

    assert (invocations, source) == (1, "<appendix-b-contract>")
    assert result["schema_version"] == 2
    assert result["reconciled"] is True
    assert result["verdict"] == "PROVENANCE_RECONCILED"
    assert result["blocking_reasons"] == []
    assert len(result["mapped_document_status"]) == 14
    assert len(result["targets"]) == 15
    boundary_documents = [
        item for item in result["mapped_document_status"]
        if item["yaml_path"].endswith("SS_TC05_boundary_values.yaml")
    ]
    assert [item["source_no"] for item in boundary_documents] == [
        "TC-05A", "TC-05B", "TC-05C",
    ]
    assert all(item["verdict"] == "RECONCILED"
               for item in boundary_documents)
    boundary = [
        target for target in result["targets"]
        if target["yaml_path"].endswith("SS_TC05_boundary_values.yaml")
    ]
    assert [(item["blocker_step_index"], item["source_no"])
            for item in boundary] == [(9, "TC-05A")]
    assert boundary[0]["candidate_count"] == 1


def test_provenance_appendix_b_real_reconcile_rejects_wrong_source_binding(
    tmp_path,
):
    def mutate(p0: dict[str, object]) -> None:
        mapping = next(
            item for item in p0["mappings"]
            if item["yaml_path"].endswith("SS_TC05_boundary_values.yaml")
        )
        mapping["blocker_bindings"][0]["source_no"] = "TC-05B"

    result, invocations, source = _run_real_appendix_b_reconcile(
        tmp_path, mutate_p0=mutate,
    )

    assert (invocations, source) == (1, "<appendix-b-contract>")
    assert result["reconciled"] is False
    assert result["verdict"] == "PROVENANCE_MISMATCH"
    assert any(
        reason["code"] == "P0_BLOCKER_MANIFEST"
        and reason["path"].endswith("SS_TC05_boundary_values.yaml")
        for reason in result["blocking_reasons"]
    )


def test_provenance_appendix_b_real_reconcile_rejects_ambiguous_candidate(
    tmp_path,
):
    def mutate(
        emitted: dict[tuple[str, str], dict[str, object]],
    ) -> None:
        item = next(
            value for (path, source_no), value in emitted.items()
            if path.endswith("SS_TC05_boundary_values.yaml")
            and source_no == "TC-05A"
        )
        item["document"]["steps"].append(
            dict(item["document"]["steps"][8])
        )

    result, invocations, source = _run_real_appendix_b_reconcile(
        tmp_path, mutate_emitted=mutate,
    )

    assert (invocations, source) == (1, "<appendix-b-contract>")
    assert result["reconciled"] is False
    assert result["verdict"] == "PROVENANCE_MISMATCH"
    reason = next(
        item for item in result["blocking_reasons"]
        if item["code"] == "TARGET_STEP_JOIN"
        and item["path"].endswith(":9:TC-05A")
    )
    assert reason["message"] == "candidate_count=2"
    target = next(
        item for item in result["targets"]
        if item["yaml_path"].endswith("SS_TC05_boundary_values.yaml")
    )
    assert target["candidate_count"] == 2
    assert target["step_join_verdict"] == "MISMATCH"


def test_provenance_appendix_c_accepts_schema_v3_p0_early_stop():
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
        "schema_version": 3,
        "directive_id": "RB-20260728-shellrc-p0p1",
        "mappings": _expected_reconcile_manifest(),
        "reconciled": False,
        "p0_blocking_reasons": [
            {
                "code": "P0_UNIQUE_JOIN",
                "path": "exported_ss_call/SS_TC01_permission_denied.yaml",
                "message": "candidate_count=0",
            }
        ],
    }

    accepted = eval(
        expression,
        {
            "DIRECTIVE_ID": "RB-20260728-shellrc-p0p1",
            "p0": p0,
            "valid_reason_list": lambda value, *, allow_empty: (
                isinstance(value, list) and (allow_empty or bool(value))
            ),
        },
    )

    assert accepted is True


def test_provenance_appendix_c_rejects_12_source_documents():
    validate = _appendix_namespace("C")["validate_reconciliation"]
    source_keys = [
        (path, selectors[0][0])
        for path, _name, _sheet, selectors, _blockers
        in RECONCILE_MANIFEST_ROWS
    ]

    assert "reconciliation green documents" in validate(
        _green_reconciliation_fixture(source_keys)
    )


def test_provenance_appendix_c_accepts_14_source_documents():
    validate = _appendix_namespace("C")["validate_reconciliation"]
    source_keys = [
        (path, source_no)
        for path, _name, _sheet, selectors, _blockers
        in RECONCILE_MANIFEST_ROWS
        for source_no, _functionality in selectors
    ]

    assert "reconciliation green documents" not in validate(
        _green_reconciliation_fixture(source_keys)
    )


def test_provenance_reconcile_manifest_requires_schema_v2():
    validate = _appendix_namespace("C")["validate_reconciliation"]
    source_keys = [
        (path, source_no)
        for path, _name, _sheet, selectors, _blockers
        in RECONCILE_MANIFEST_ROWS
        for source_no, _functionality in selectors
    ]

    assert "reconciliation schema_version" in validate(
        _green_reconciliation_fixture(source_keys, schema_version=1)
    )
    assert validate(_green_reconciliation_fixture(source_keys)) == []


def test_provenance_reconcile_manifest_is_consistent_across_appendices():
    expected = _expected_reconcile_manifest()
    appendix_b = _appendix_namespace("B")
    appendix_c = _appendix_namespace("C")
    source_keys = tuple(
        (item["yaml_path"], selector["source_no"])
        for item in expected
        for selector in item["source_selectors"]
    )
    target_keys = tuple(
        (
            item["yaml_path"],
            binding["blocker_step_index"],
            binding["source_no"],
        )
        for item in expected
        for binding in item["blocker_bindings"]
    )

    assert _appendix_a_targets() == expected
    assert list(appendix_b["TARGETS"]) == expected
    assert appendix_c["EXPECTED_TARGETS"] == target_keys
    assert any(
        value == source_keys
        for name, value in appendix_c.items()
        if name.startswith("EXPECTED_") and isinstance(value, tuple)
    )
    assert (len(expected), len(source_keys), len(target_keys)) == (12, 14, 15)
    assert [key[1] for key in source_keys].count("TC-05A") == 1
    assert [key[1] for key in source_keys].count("TC-05B") == 1
    assert [key[1] for key in source_keys].count("TC-05C") == 1
    assert [key[2] for key in target_keys if "SS_TC05" in key[0]] == [
        "TC-05A"
    ]
    assert {
        sheet: sum(len(selectors) for _path, _name, current, selectors,
                   _blockers in RECONCILE_MANIFEST_ROWS if current == sheet)
        for sheet in ("SS-TC 0", "SS-TC 1")
    } == {"SS-TC 0": 1, "SS-TC 1": 13}
    assert {
        sheet: sum(len(blockers) for _path, _name, current, _selectors,
                   blockers in RECONCILE_MANIFEST_ROWS if current == sheet)
        for sheet in ("SS-TC 0", "SS-TC 1")
    } == {"SS-TC 0": 1, "SS-TC 1": 14}


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
