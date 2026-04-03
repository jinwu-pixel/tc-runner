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

    def test_filename_has_8char_hash(self, exporter):
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=2)
        # filename format: {tc_name}_{sha256[:8]}.yaml
        parts = path.stem.rsplit("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 8  # 8-char hex hash

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


class TestCheckRunnableEdgeCases:
    def test_shell_placeholder_not_runnable(self):
        preview = _preview(steps=[{
            "action": "shell", "command": "am start -n {package}/.Main",
        }])
        runnable, issues = check_runnable(preview)
        assert not runnable
        assert any("placeholder" in i for i in issues)

    def test_manual_pause_missing_description_not_runnable(self):
        preview = _preview(steps=[{
            "action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
        }])
        runnable, issues = check_runnable(preview)
        assert not runnable
        assert any("manual_pause" in i for i in issues)

    def test_manual_pause_with_description_is_runnable(self):
        preview = _preview(steps=[{
            "action": "manual_pause", "execution_mode": "MANUAL_REQUIRED",
            "description": "이어폰 연결",
        }])
        runnable, issues = check_runnable(preview)
        assert runnable

    def test_shell_mapping_missing_warning_not_runnable(self):
        preview = _preview(
            steps=[{"action": "tap_text", "text": "설정"}],
            warnings=["shell_mapping_missing: '앱 실행' shell 매핑 미구현"],
        )
        runnable, issues = check_runnable(preview)
        assert not runnable
        assert any("치명 warning" in i for i in issues)

    def test_mixed_runnable_and_unrunnable_steps(self):
        preview = _preview(steps=[
            {"action": "tap_text", "text": "설정"},
            {"action": "shell", "command": "logcat -c"},
            {"action": "shell", "command": "am start -n {package}", "compile_status": "UNRESOLVED_PARAMS"},
        ])
        runnable, issues = check_runnable(preview)
        assert not runnable  # one unresolved is enough


class TestExportMetadata:
    def test_exported_yaml_contains_metadata(self, exporter, tmp_path):
        import yaml
        preview = _preview()
        path = exporter.export_one(preview, source_file="TC_1.xlsx",
                                   source_sheet="SS-TC 1", source_row=5)
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        assert doc["name"] == "TC-01_테스트"
        assert doc["metadata"]["source_file"] == "TC_1.xlsx"
        assert doc["metadata"]["source_sheet"] == "SS-TC 1"
        assert doc["metadata"]["source_row"] == 5
        assert doc["metadata"]["automation_class"] == "FULL_AUTO"
        assert doc["metadata"]["runnable"] is True
        assert "exported_at" in doc["metadata"]
        assert len(doc["steps"]) == 1

    def test_exported_yaml_flags_manual_steps(self, exporter, tmp_path):
        import yaml
        preview = _preview(steps=[
            {"action": "tap_text", "text": "설정"},
            {"action": "manual_pause", "description": "이어폰 연결", "execution_mode": "MANUAL_REQUIRED"},
        ])
        path = exporter.export_one(preview, source_file="f", source_sheet="s", source_row=1)
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        assert doc["metadata"]["has_manual_steps"] is True

    def test_different_content_different_hash(self, exporter):
        p1 = _preview(name="TC-01_테스트")
        p2 = ConversionPreview(
            tc_name="TC-01_테스트",
            automation_class="FULL_AUTO",
            source_procedure="다른 절차",
            source_expected="다른 기대",
            parsed_intents=[],
            compiled_steps=[{"action": "tap_text", "text": "설정"}],
        )
        path1 = exporter.export_one(p1, source_file="f", source_sheet="s", source_row=1)
        path2 = exporter.export_one(p2, source_file="f", source_sheet="s", source_row=2)
        assert path1 is not None
        assert path2 is not None
        assert path1.name != path2.name  # different content → different hash
