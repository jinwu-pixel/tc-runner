"""IR → tc-runner YAML compiler 단위 테스트."""
import pytest
from src.mmi_converter.compiler import TCRunnerCompiler
from src.mmi_converter.models import Intent, TCIR, MMIRow, ClassifiedIntent


@pytest.fixture
def compiler():
    return TCRunnerCompiler()


def _make_ir(intents, expected_intents=None, tc_name="test_tc"):
    return TCIR(
        tc_name=tc_name,
        description="test",
        preconditions=[],
        intents=intents,
        expected_intents=expected_intents or [],
    )


class TestNavigateCompile:
    def test_navigate_to_tap_text(self, compiler):
        ir = _make_ir([Intent(type="navigate", target="설정")])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "tap_text", "text": "설정"}]

    def test_navigate_no_target_warns(self, compiler):
        ir = _make_ir([Intent(type="navigate", target=None)])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert any("target" in w for w in result["metadata"]["warnings"])


class TestKeyCompile:
    def test_press_key(self, compiler):
        ir = _make_ir([Intent(type="press_key", value="HOME")])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "key", "keycode": "HOME"}]

    def test_press_key_no_value_warns(self, compiler):
        ir = _make_ir([Intent(type="press_key", value=None)])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert len(result["metadata"]["warnings"]) > 0


class TestWaitCompile:
    def test_wait(self, compiler):
        ir = _make_ir([Intent(type="wait", value="3")])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "wait", "seconds": 3}]

    def test_wait_default(self, compiler):
        ir = _make_ir([Intent(type="wait", value=None)])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "wait", "seconds": 2}]


class TestVerifyTextCompile:
    def test_verify_text(self, compiler):
        ir = _make_ir([], [Intent(type="verify_text", target="Wi-Fi")])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "verify_text", "text": "Wi-Fi"}]

    def test_verify_text_no_target_warns(self, compiler):
        ir = _make_ir([], [Intent(type="verify_text", target=None)])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert len(result["metadata"]["warnings"]) > 0


class TestInputTextCompile:
    def test_input_with_value(self, compiler):
        ir = _make_ir([Intent(type="input_text", target="번호", extra={"text": "01012345678"})])
        result = compiler.compile(ir)
        assert result["steps"] == [{"action": "input_text", "text": "01012345678"}]

    def test_input_no_value_warns(self, compiler):
        ir = _make_ir([Intent(type="input_text", target="번호")])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert any("입력 대상" in w for w in result["metadata"]["warnings"])


class TestToggleCompile:
    def test_toggle_warns_not_implemented(self, compiler):
        ir = _make_ir([Intent(type="toggle", target="Wi-Fi", value="on")])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert any("토글 intent" in w for w in result["metadata"]["warnings"])

    def test_toggle_no_target_warns(self, compiler):
        ir = _make_ir([Intent(type="toggle", target=None, value="on")])
        result = compiler.compile(ir)
        assert any("target 추정 실패" in w for w in result["metadata"]["warnings"])


class TestVerifyShellCompile:
    def test_verify_shell(self, compiler):
        ir = _make_ir([Intent(
            type="verify_shell",
            extra={"command": "dumpsys wifi", "expected": "enabled"},
        )])
        result = compiler.compile(ir)
        assert result["steps"] == [
            {"action": "verify_shell", "command": "dumpsys wifi", "expected": "enabled"}
        ]

    def test_verify_shell_missing_fields(self, compiler):
        ir = _make_ir([Intent(type="verify_shell")])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert len(result["metadata"]["warnings"]) > 0


class TestManualRequired:
    def test_manual_required_warns(self, compiler):
        ir = _make_ir([Intent(type="manual_required", target="이어폰 연결 필요")])
        result = compiler.compile(ir)
        assert result["steps"] == []
        assert "이어폰 연결 필요" in result["metadata"]["warnings"]


class TestMetadata:
    def test_metadata_fields(self, compiler):
        row = MMIRow(
            row_index=42, no="7", feature_name="test",
            functionality="f", precondition="p", procedure="proc",
            expected_result="exp", priority="S", sheet_name="sheet1",
        )
        ir = _make_ir([Intent(type="navigate", target="설정")], tc_name="tc_42")
        ir.source_row = row
        result = compiler.compile(ir, automation_class="FULL_AUTO")
        assert result["metadata"]["automation_class"] == "FULL_AUTO"
        assert result["metadata"]["source_sheet"] == "sheet1"
        assert result["metadata"]["source_row"] == 42


class TestClassifiedIntentCompilation:
    def test_shell_auto_with_resolved_params(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="로그 초기화"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "shell"
        assert steps[0]["command"] == "logcat -c"

    def test_manual_required_emits_manual_pause(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="이어폰 연결"),
            execution_mode="MANUAL_REQUIRED",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "manual_pause"
        assert steps[0]["execution_mode"] == "MANUAL_REQUIRED"

    def test_external_event_emits_manual_pause(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="수신 전화"),
            execution_mode="EXTERNAL_EVENT",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert steps[0]["action"] == "manual_pause"
        assert steps[0]["execution_mode"] == "EXTERNAL_EVENT"

    def test_ui_auto_compiles_normally(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate", target="설정"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert steps[0] == {"action": "tap_text", "text": "설정"}
