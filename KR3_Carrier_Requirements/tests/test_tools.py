from __future__ import annotations

import json
import os
import subprocess
import sys
import importlib.util
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "KR3_Carrier_Requirements" / "tools"
COVERAGE_TOOL = TOOLS_DIR / "verify_step_coverage.py"
RUNNABLE_TOOL = TOOLS_DIR / "project_runnable.py"
CORPUS_INDEX_TOOL = TOOLS_DIR / "spec_corpus_index.py"


def _run(
    script: Path,
    *args: object,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *(str(arg) for arg in args)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def _load_tool(name: str, path: Path):
    sys.path.insert(0, str(TOOLS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TOOLS_DIR))


def _write_ctf(stage1_dir: Path, *, blockers: bool) -> None:
    stage1_dir.mkdir()
    if blockers:
        preconditions = [
            {
                "text": "사람이 준비하는 fixture",
                "blocking": True,
                "implicit_fixture_suspected": True,
            }
        ]
        mutation_risk = True
        expected = [
            {
                "type": "manual_required",
                "target": "외부 판정",
                "value": None,
                "feasibility": "infeasible",
            }
        ]
    else:
        preconditions = []
        mutation_risk = False
        expected = [
            {
                "type": "verify_text",
                "target": "상태",
                "value": "정상",
                "feasibility": "text_literal",
            }
        ]

    document = {
        "tc_id": "SAMPLE_01",
        "source_trace": {"row": "1.1"},
        "preconditions": preconditions,
        "procedure_steps": [
            {
                "step_no": 1,
                "normalized_intent": {"mutation_risk": mutation_risk},
                "expected": expected,
                "execution_candidate": {
                    "mode": "EXTERNAL_EVENT",
                    "role": "ACTION",
                },
            },
            {
                "step_no": 2,
                "normalized_intent": {"mutation_risk": False},
                "expected": [],
                "execution_candidate": {
                    "mode": "UNSUPPORTED",
                    "role": "ASSERT",
                },
            },
        ],
        "automation_summary": {"tc_class": "SEMI_AUTO"},
        "risk_flags": [{"flag": "MULTI_DEVICE", "step_no": 1}],
    }
    (stage1_dir / "SAMPLE_01_canonical.yaml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _write_capability(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "runner_version": "test",
                "supported_actions": ["manual_pause"],
                "multi_device": False,
                "shell_actions_available": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_coverage_reads_html_directly_from_arbitrary_cwd(tmp_path: Path) -> None:
    source = tmp_path / "source.html"
    source.write_text(
        """
        <html><body>
        <h2>1.1 Sample</h2>
        <h3>1.1.1 시험방법</h3>
        <p>1) 첫 번째 절차</p>
        <p>2) 두 번째 절차</p>
        <h3>1.1.2 판정기준</h3>
        <p>1) 판정 문장은 세지 않는다</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    stage1_dir = tmp_path / "stage1"
    stage1_dir.mkdir()
    (stage1_dir / "SAMPLE_01_canonical.yaml").write_text(
        yaml.safe_dump(
            {
                "source_trace": {"row": "1.1"},
                "procedure_steps": [{"step_no": 1}, {"step_no": 2}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = _run(
        COVERAGE_TOOL,
        "--source",
        source,
        "--stage1",
        stage1_dir,
        "--target",
        "1.1",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "합계  원문 2 / CTF 2  — 불일치 0건" in result.stdout


def test_coverage_missing_source_fails_closed_without_traceback(tmp_path: Path) -> None:
    stage1_dir = tmp_path / "stage1"
    stage1_dir.mkdir()

    result = _run(
        COVERAGE_TOOL,
        "--source",
        tmp_path / "missing.html",
        "--stage1",
        stage1_dir,
        "--target",
        "1.1",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "원본 HTML 없음" in result.stderr
    assert "Traceback" not in result.stderr


def test_default_source_discovery_is_scoped_to_lgu_corpus(tmp_path: Path) -> None:
    source = (
        tmp_path
        / "새 폴더 (2)"
        / "LGU+"
        / "snapshot"
        / "CD_20_LGU_디바이스_5G_시험절차서_V02_00_00.html"
    )
    source.parent.mkdir(parents=True)
    source.write_text("<html></html>", encoding="utf-8")
    module = _load_tool("verify_step_coverage_test", COVERAGE_TOOL)

    assert module.discover_source(tmp_path) == source


def test_projection_keeps_capability_gaps_as_diagnostics(tmp_path: Path) -> None:
    stage1_dir = tmp_path / "stage1"
    _write_ctf(stage1_dir, blockers=False)
    capability = tmp_path / "runner_capability.yaml"
    _write_capability(capability)

    result = _run(
        RUNNABLE_TOOL,
        "--stage1",
        stage1_dir,
        "--capability",
        capability,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "투영 결과: runnable:true 후보 1 / 1" in result.stdout
    assert "runnable 차단 사유별 건수:\n  —" in result.stdout
    assert "EXTERNAL_EVENT" in result.stdout
    assert "MULTI_DEVICE_UNSUPPORTED" in result.stdout
    assert "UNSUPPORTED_STEP" in result.stdout


def test_projection_uses_only_stage2_schema_blockers(tmp_path: Path) -> None:
    stage1_dir = tmp_path / "stage1"
    _write_ctf(stage1_dir, blockers=True)
    capability = tmp_path / "runner_capability.yaml"
    _write_capability(capability)

    result = _run(
        RUNNABLE_TOOL,
        "--stage1",
        stage1_dir,
        "--capability",
        capability,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "투영 결과: runnable:true 후보 0 / 1" in result.stdout
    assert "FIXTURE_REQUIRED" in result.stdout
    assert "INFEASIBLE_VERIFIER" in result.stdout
    assert "MUTATION_UNMANAGED" in result.stdout


def test_projection_rejects_empty_stage1_directory(tmp_path: Path) -> None:
    stage1_dir = tmp_path / "stage1"
    stage1_dir.mkdir()
    capability = tmp_path / "runner_capability.yaml"
    _write_capability(capability)

    result = _run(
        RUNNABLE_TOOL,
        "--stage1",
        stage1_dir,
        "--capability",
        capability,
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "CTF 입력 0건" in result.stderr
    assert "Traceback" not in result.stderr


def test_corpus_index_relative_root_is_repo_anchored_from_arbitrary_cwd(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_tool("spec_corpus_index_root_test", CORPUS_INDEX_TOOL)
    monkeypatch.chdir(tmp_path)

    resolved, recorded = module.resolve_corpus_root("새 폴더 (2)")

    assert resolved == REPO_ROOT / "새 폴더 (2)"
    assert recorded == "새 폴더 (2)"


def test_corpus_index_build_requires_explicit_poppler(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    out = tmp_path / "out"
    env = os.environ.copy()
    env.pop("TC_RUNNER_POPPLER_BIN", None)

    result = _run(
        CORPUS_INDEX_TOOL,
        "build",
        "--root",
        corpus,
        "--out",
        out,
        cwd=tmp_path,
        env=env,
    )

    assert result.returncode == 2
    assert "--poppler" in result.stderr
    assert "TC_RUNNER_POPPLER_BIN" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (out / "corpus_index.json").exists()


def test_corpus_index_resolves_poppler_from_cli_or_environment(tmp_path: Path) -> None:
    poppler = tmp_path / "poppler-bin"
    poppler.mkdir()
    expected = (poppler / "pdftotext.exe", poppler / "pdfinfo.exe")
    for executable in expected:
        executable.write_bytes(b"")
    module = _load_tool("spec_corpus_index_poppler_test", CORPUS_INDEX_TOOL)

    assert module.resolve_poppler_tools(str(poppler), {}) == expected
    assert module.resolve_poppler_tools(
        None,
        {"TC_RUNNER_POPPLER_BIN": str(poppler)},
    ) == expected


def test_corpus_index_read_commands_do_not_require_poppler(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "corpus_index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tool": "spec_corpus_index-v1",
                "root": "새 폴더 (2)",
                "doc_count": 0,
                "section_count": 0,
                "docs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("TC_RUNNER_POPPLER_BIN", None)

    commands = (("search", "needle"), ("doc", "needle"), ("stats",))
    for command in commands:
        result = _run(
            CORPUS_INDEX_TOOL,
            *command,
            "--out",
            out,
            cwd=tmp_path,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr
