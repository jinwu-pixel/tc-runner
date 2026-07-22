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

    def test_toggle_emits_manual_pause_not_drop(self):
        """toggle intent가 drop되지 않고 manual_pause 1건으로 살아남는다."""
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="toggle", target="Wi-Fi", value="ON"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "manual_pause"
        assert steps[0]["execution_mode"] == "MANUAL_REQUIRED"
        assert "Wi-Fi" in steps[0]["description"]
        assert "ON" in steps[0]["description"]
        assert steps[0]["manual_timeout"] == 300
        assert steps[0]["on_timeout"] == "fail"
        assert any("toggle_compile_not_implemented" in w for w in warnings)
        assert any("manual_pause_inserted_for_toggle" in w for w in warnings)


class TestSemanticIntentCompilation:
    """시맨틱 intent 타입(app_launch, app_close, navigate_back) 컴파일 테스트."""

    def test_app_launch_known_package(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="app_launch", target="카카오톡 앱 실행"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "shell"
        assert "com.kakao.talk" in steps[0]["command"]
        assert "am start" in steps[0]["command"]

    def test_app_launch_unknown_package_fallback(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="app_launch", target="알수없는앱"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "manual_pause"
        assert any("app_launch_no_package_match" in w for w in warnings)

    def test_app_close_known_package(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="app_close", target="유튜브 앱 종료"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0]["action"] == "shell"
        assert "am force-stop" in steps[0]["command"]
        assert "com.google.android.youtube" in steps[0]["command"]

    def test_app_close_unknown_package_fallback(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="app_close", target="미등록앱"),
            execution_mode="SHELL_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert steps[0]["action"] == "manual_pause"
        assert any("app_close_no_package_match" in w for w in warnings)

    def test_navigate_back(self):
        compiler = TCRunnerCompiler()
        ci = ClassifiedIntent(
            intent=Intent(type="navigate_back", target="이전 화면"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        steps, warnings = compiler.compile_classified(ci)
        assert len(steps) == 1
        assert steps[0] == {"action": "key", "keycode": "BACK"}


def test_canonical_compiler_emits_target_key_duration():
    compiler = TCRunnerCompiler(contract_mode="canonical")
    classified = [
        ClassifiedIntent(
            intent=Intent(type="navigate", target="Settings"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        ),
        ClassifiedIntent(
            intent=Intent(type="press_key", value="HOME"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        ),
        ClassifiedIntent(
            intent=Intent(type="wait", value="3"),
            execution_mode="UI_AUTO",
            step_role="ACTION",
        ),
    ]

    steps = []
    for intent in classified:
        compiled, warnings = compiler.compile_classified(intent)
        assert warnings == []
        steps.extend(compiled)

    assert steps == [
        {"action": "tap_text", "target": "Settings"},
        {"action": "key", "key": "HOME"},
        {"action": "wait", "duration": 3000},
    ]


def test_canonical_compiler_preserves_input_text_payload():
    compiler = TCRunnerCompiler(contract_mode="canonical")
    classified = ClassifiedIntent(
        intent=Intent(
            type="input_text",
            target="phone number",
            extra={"text": "01012345678"},
        ),
        execution_mode="UI_AUTO",
        step_role="ACTION",
    )

    steps, warnings = compiler.compile_classified(classified)

    assert warnings == []
    assert steps == [{"action": "input_text", "text": "01012345678"}]


def test_canonical_compiler_compile_normalizes_full_document_steps():
    ir = _make_ir(
        [
            Intent(type="navigate", target="Settings"),
            Intent(type="press_key", value="HOME"),
            Intent(type="wait", value="3"),
        ],
        tc_name="MMI_CANONICAL_DOCUMENT",
    )

    document = TCRunnerCompiler(contract_mode="canonical").compile(ir)

    assert document["steps"] == [
        {"action": "tap_text", "target": "Settings"},
        {"action": "key", "key": "HOME"},
        {"action": "wait", "duration": 3000},
    ]


def test_canonical_compiler_canonicalize_steps_raises_on_blocking_conflict():
    with pytest.raises(ValueError, match="ALIAS_CONFLICT"):
        TCRunnerCompiler._canonicalize_steps(
            [{"action": "wait", "duration": 2000, "seconds": 3}]
        )


def test_explicit_legacy_compiler_behavior_is_unchanged():
    ir = _make_ir(
        [
            Intent(type="navigate", target="Settings"),
            Intent(type="press_key", value="HOME"),
            Intent(type="wait", value="3"),
        ],
        tc_name="MMI_LEGACY",
    )

    assert TCRunnerCompiler(contract_mode="legacy").compile(ir) == (
        TCRunnerCompiler().compile(ir)
    )
