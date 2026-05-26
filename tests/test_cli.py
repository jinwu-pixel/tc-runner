from pathlib import Path

import pytest
from openpyxl import Workbook

from src.cli import _resolve_tc_files, main


def create_test_excel(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["TC Name", "Step", "Action", "Parameter1", "Parameter2", "Expected"])
    ws.append(["테스트", 1, "key", "HOME", "", ""])
    ws.append(["테스트", 2, "wait", "1", "", ""])
    wb.save(path)


def test_resolve_xlsx_converts_to_yaml(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    create_test_excel(xlsx)

    tc_files, temp_dirs = _resolve_tc_files([str(xlsx)])

    assert len(tc_files) == 1
    assert tc_files[0].suffix == ".yaml"
    assert tc_files[0].exists()
    assert len(temp_dirs) == 1

    # cleanup
    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_yaml_passes_through(tmp_path):
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\nsteps:\n  - action: wait\n    seconds: 1\n")

    tc_files, temp_dirs = _resolve_tc_files([str(yaml_file)])

    assert len(tc_files) == 1
    assert tc_files[0] == yaml_file
    assert len(temp_dirs) == 0


def test_resolve_mixed_xlsx_and_yaml(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    create_test_excel(xlsx)
    yaml_file = tmp_path / "extra.yaml"
    yaml_file.write_text("name: extra\nsteps:\n  - action: wait\n    seconds: 1\n")

    tc_files, temp_dirs = _resolve_tc_files([str(xlsx), str(yaml_file)])

    assert len(tc_files) == 2
    assert len(temp_dirs) == 1

    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_invalid_xlsx_skips(tmp_path):
    bad_xlsx = tmp_path / "bad.xlsx"
    bad_xlsx.write_bytes(b"not an excel file")

    tc_files, temp_dirs = _resolve_tc_files([str(bad_xlsx)])

    assert len(tc_files) == 0
    assert len(temp_dirs) == 1

    import shutil
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


def test_run_subparser_accepts_run_id(monkeypatch):
    """`cli run` 이 --run-id override 를 파싱하여 cmd_run 에 전달한다."""
    captured = {}

    def fake_run(args):
        captured["run_id"] = args.run_id
        captured["tc_files"] = list(args.tc_files)

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "run", "dummy.yaml", "--run-id", "20260526T120000Z"],
    )
    main()
    assert captured == {"run_id": "20260526T120000Z", "tc_files": ["dummy.yaml"]}


def test_run_subparser_run_id_default_none(monkeypatch):
    """--run-id 미지정 시 args.run_id == None (cmd_run 안에서 _now_run_id() 적용)."""
    captured = {}

    def fake_run(args):
        captured["run_id"] = args.run_id

    monkeypatch.setattr("src.cli.cmd_run", fake_run)
    monkeypatch.setattr("sys.argv", ["cli", "run", "dummy.yaml"])
    main()
    assert captured["run_id"] is None
