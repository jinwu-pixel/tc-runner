# tests/test_exporter.py
"""YAML exporter 단위 테스트."""
import hashlib
import pytest
from pathlib import Path
from src.mmi_converter.exporter import YAMLExporter, check_runnable
from src.mmi_converter.models import ConversionPreview, Intent


@pytest.fixture
def exporter(tmp_path):
    return YAMLExporter(output_dir=tmp_path)


def _preview(name="TC-01_테스트", auto_class="FULL_AUTO", steps=None, warnings=None):
    _SENTINEL = object()
    compiled = steps if steps is not None else [{"action": "tap_text", "text": "설정"}]
    return ConversionPreview(
        tc_name=name,
        automation_class=auto_class,
        source_procedure="설정 > 네트워크",
        source_expected="표시된다",
        parsed_intents=[],
        compiled_steps=compiled,
        warnings=warnings or [],
    )


class TestCheckRunnable:
    def test_normal_steps_are_runnable(self):
        preview = _preview(steps=[{"action": "tap_text", "text": "설정"}])
        runnable, issues = check_runnable(preview)
        assert runnable

    def test_unresolved_params_not_runnable(self):
        preview = _preview(steps=[{
            "action": "shell", "command": "am start -n {package}",
            "compile_status": "UNRESOLVED_PARAMS",
        }])
        runnable, issues = check_runnable(preview)
        assert not runnable

    def test_empty_steps_not_runnable(self):
        preview = _preview(steps=[])
        runnable, issues = check_runnable(preview)
        assert not runnable


class TestYAMLExporter:
    def test_export_creates_file(self, exporter, tmp_path):
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=2)
        assert path.exists()
        assert path.suffix == ".yaml"

    def test_filename_has_hash(self, exporter):
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=2)
        assert "_" in path.stem  # tc_name + hash

    def test_skip_existing_without_overwrite(self, exporter, tmp_path):
        preview = _preview()
        path1 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        path2 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        assert path2 is None  # skipped

    def test_overwrite_flag(self, exporter):
        exporter.overwrite = True
        preview = _preview()
        path1 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        path2 = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        assert path2 is not None
