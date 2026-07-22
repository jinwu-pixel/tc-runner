# tests/test_exporter.py
"""YAML exporter 단위 테스트."""
import hashlib
import json
from datetime import datetime as RealDatetime
import pytest
from pathlib import Path
import yaml

import src.mmi_converter.exporter as exporter_module
from src.mmi_converter.exporter import YAMLExporter, check_runnable
from src.mmi_converter.models import ConversionPreview, Intent
from src.execution_contract import validate_canonical_tc


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


def test_canonical_exporter_emits_required_metadata(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI_CANONICAL",
        steps=[{"action": "tap_text", "text": "Settings"}],
    )

    path = exporter.export_one(
        preview,
        source_file="mmi.xlsx",
        source_sheet="Sheet1",
        source_row=7,
    )

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["tc_name"] == "MMI_CANONICAL"
    assert "name" not in doc
    assert doc["steps"] == [{"action": "tap_text", "target": "Settings"}]
    assert doc["metadata"]["runnable"] is True
    assert doc["metadata"]["tc_class"] == "FULL_AUTO"
    assert doc["metadata"]["execution_type"] == "AUTO"
    assert doc["metadata"]["manual_detail"] == "NONE"
    assert doc["metadata"]["has_manual_steps"] is False
    assert "automation_class" not in doc["metadata"]
    assert "exported_at" in doc["metadata"]
    schema = json.loads(
        (Path(__file__).parent.parent / "tc_step_schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_canonical_tc(doc, schema) == []


def test_unresolved_mmi_export_is_not_runnable(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI_UNRESOLVED",
        steps=[
            {
                "action": "shell",
                "command": "am start -n {package}/.MainActivity",
                "compile_status": "UNRESOLVED_PARAMS",
                "_unresolved_params": ["package"],
            }
        ],
    )

    path = exporter.export_one(
        preview,
        source_file="mmi.xlsx",
        source_sheet="Sheet1",
        source_row=8,
    )

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["metadata"]["runnable"] is False
    assert doc["metadata"]["runnable_reason"] == ["UNRESOLVED_PARAMS"]


def test_canonical_mmi_export_rejects_invalid_document_before_write(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI INVALID NAME",
        steps=[{"action": "tap_text", "text": "Settings"}],
    )

    with pytest.raises(ValueError, match="canonical MMI validation failed"):
        exporter.export_one(
            preview,
            source_file="mmi.xlsx",
            source_sheet="Sheet1",
            source_row=10,
        )

    assert not list(tmp_path.glob("*.yaml"))


def test_canonical_exporter_composes_external_marker_derivation_and_validation(
    tmp_path,
):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI_CALL_RECEIVE",
        auto_class="SEMI_AUTO",
        steps=[
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "보조폰에서 전화를 수신하세요",
            }
        ],
    )

    path = exporter.export_one(preview, "mmi.xlsx", "Sheet1", 11)

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["metadata"]["execution_type"] == "EXTERNAL_EVENT"
    schema = json.loads(
        (Path(__file__).parent.parent / "tc_step_schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_canonical_tc(doc, schema) == []


def test_canonical_exporter_keeps_inbox_manual_local(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI_INBOX_CHECK",
        auto_class="SEMI_AUTO",
        steps=[
            {
                "action": "manual_pause",
                "execution_mode": "MANUAL_REQUIRED",
                "description": "문자 수신함을 확인하세요",
            }
        ],
    )

    path = exporter.export_one(preview, "mmi.xlsx", "Sheet1", 12)

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["metadata"]["execution_type"] == "MANUAL_LOCAL"
    assert doc["metadata"]["manual_detail"] == "UNKNOWN"
    schema = json.loads(
        (Path(__file__).parent.parent / "tc_step_schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_canonical_tc(doc, schema) == []


def test_nonrunnable_canonical_export_records_validation_errors(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")
    preview = _preview(
        name="MMI INVALID NAME",
        steps=[
            {
                "action": "shell",
                "command": "am start -n {package}/.MainActivity",
                "compile_status": "UNRESOLVED_PARAMS",
                "_unresolved_params": ["package"],
            }
        ],
    )

    path = exporter.export_one(preview, "mmi.xlsx", "Sheet1", 13)

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert any(
        warning.startswith("canonical_validation_error: tc_name 형식 불일치")
        for warning in doc["metadata"]["warnings"]
    )


def test_empty_canonical_export_has_manual_fallback_reason(tmp_path):
    exporter = YAMLExporter(output_dir=tmp_path, contract_mode="canonical")

    path = exporter.export_one(
        _preview(name="MMI_EMPTY", steps=[]),
        "mmi.xlsx",
        "Sheet1",
        14,
    )

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["metadata"]["runnable"] is False
    assert doc["metadata"]["runnable_reason"] == ["MANUAL_FALLBACK"]
    assert any(
        warning == "canonical_validation_error: steps가 비어 있음"
        for warning in doc["metadata"]["warnings"]
    )


def test_legacy_mmi_output_is_unchanged(tmp_path, monkeypatch):
    class FixedDatetime:
        @classmethod
        def now(cls):
            return RealDatetime(2026, 7, 21, 12, 0, 0)

    monkeypatch.setattr(exporter_module, "datetime", FixedDatetime)
    preview = _preview(
        name="MMI_LEGACY",
        steps=[{"action": "wait", "seconds": 2}],
    )
    default_exporter = YAMLExporter(output_dir=tmp_path / "default")
    explicit_exporter = YAMLExporter(
        output_dir=tmp_path / "explicit",
        contract_mode="legacy",
    )

    default_path = default_exporter.export_one(preview, "mmi.xlsx", "Sheet1", 9)
    explicit_path = explicit_exporter.export_one(preview, "mmi.xlsx", "Sheet1", 9)

    assert default_path.read_bytes() == explicit_path.read_bytes()
    doc = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    assert doc["name"] == "MMI_LEGACY"
    assert "tc_name" not in doc
    assert doc["metadata"]["automation_class"] == "FULL_AUTO"
    assert "tc_class" not in doc["metadata"]
    assert doc["steps"] == [{"action": "wait", "seconds": 2}]
