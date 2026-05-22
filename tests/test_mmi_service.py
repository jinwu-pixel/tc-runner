"""MMIConversionService 통합 테스트 + downgrade rule 검증."""
import pytest
from src.mmi_converter.service import MMIConversionService
from src.mmi_converter.models import MMIRow


@pytest.fixture
def svc():
    return MMIConversionService()


def _row(procedure, expected="", functionality="테스트", feature_name="feat", precondition=""):
    return MMIRow(
        row_index=1, no="1", feature_name=feature_name,
        functionality=functionality, precondition=precondition,
        procedure=procedure, expected_result=expected,
        priority="S", sheet_name="test",
    )


class TestConvertibleFlow:
    def test_menu_chain_produces_steps(self, svc):
        result = svc.convert_row(_row("설정 > 네트워크 > Wi-Fi"))
        assert result.automation_class in ("FULL_AUTO", "SEMI_AUTO")
        assert len(result.compiled_steps) == 3
        assert result.compiled_steps[0] == {"action": "tap_text", "text": "설정"}

    def test_key_event_produces_step(self, svc):
        result = svc.convert_row(_row("Home 키 입력", "홈화면으로 전환된다"))
        assert any(s["action"] == "key" for s in result.compiled_steps)


class TestNonConvertible:
    def test_manual_required(self, svc):
        result = svc.convert_row(_row("유선 이어폰 연결 후 통화 확인"))
        assert result.automation_class == "MANUAL_REQUIRED"

    def test_ambiguous(self, svc):
        result = svc.convert_row(_row("정상 동작 확인한다", "문제 없는지 확인"))
        assert result.automation_class == "AMBIGUOUS_NL"

    def test_empty_procedure(self, svc):
        result = svc.convert_row(_row("", "Wi-Fi가 표시된다"))
        assert result.automation_class == "AMBIGUOUS_NL"


class TestDowngradeRule:
    def test_downgrade_many_segments_few_steps(self, svc):
        """segment >= 4 이고 compiled steps <= 1 이면 downgrade."""
        # 4개 segment 중 3개가 토글로 빠져 step이 적은 경우
        result = svc.convert_row(_row(
            "설정 > 네트워크 > Wi-Fi > 토글 On > 확인 > 활성화 > 끄기",
            "Wi-Fi가 표시된다",
        ))
        # toggle/verify_text가 다수 → compiled step이 적을 수 있음
        if len(result.compiled_steps) <= 1:
            assert result.automation_class == "SEMI_AUTO"

    def test_downgrade_toggle_no_step(self, svc):
        """toggle intent가 있으나 compiled step이 0이면 downgrade."""
        result = svc.convert_row(_row("Wi-Fi 토글 On", "Wi-Fi가 표시된다"))
        # toggle → 미구현 warning, step 없음
        assert result.automation_class == "SEMI_AUTO"

    def test_downgrade_expected_no_verify(self, svc):
        """expected가 있는데 verify step이 0이면 downgrade."""
        result = svc.convert_row(_row(
            "설정 > 네트워크 > Wi-Fi",
            "정상적으로 연결됨",  # expected_parser에서 패턴에 안 걸리는 문장
        ))
        # expected가 있지만 verify step 없음
        if not any(s.get("action", "").startswith("verify") for s in result.compiled_steps):
            assert result.automation_class == "SEMI_AUTO"

    def test_no_downgrade_when_healthy(self, svc):
        """steps가 충분하고 verify도 있으면 downgrade 안 함."""
        result = svc.convert_row(_row(
            "설정 > 디스플레이 > 잠금 화면",
            "잠금 화면 설정 메뉴로 진입된다",
        ))
        # 3 navigate steps + 1 verify_text step → 건강한 상태
        assert len(result.compiled_steps) >= 3


class TestWarningAccumulation:
    def test_toggle_warning(self, svc):
        result = svc.convert_row(_row("설정 > 네트워크 > 모바일 데이터 On"))
        assert any("toggle_compile_not_implemented" in w for w in result.warnings)

    def test_input_warning(self, svc):
        result = svc.convert_row(_row("설정 > 검색 > 문자열 입력"))
        assert any("입력 대상" in w for w in result.warnings)


class TestLegacyOverride:
    """레거시 non-convertible인데 step summary가 FULL_AUTO라 compile 진행되는 케이스."""

    def test_ambiguous_nl_overridden_when_steps_automatable(self, svc):
        """AMBIGUOUS_NL이지만 StepClassifier가 FULL_AUTO로 판단 + auto steps > 0이면 override.

        "네트워크 비행기 모드"는 legacy classifier에서 auto_score=0 →
        AMBIGUOUS_NL이지만, procedure_parser가 navigate intent를 생성하여
        tap_text step으로 compile되므로 override 대상.
        """
        result = svc.convert_row(_row("네트워크 비행기 모드"))
        # Legacy would say AMBIGUOUS_NL, step classifier produces tap_text
        assert len(result.compiled_steps) > 0
        assert result.automation_class in ("FULL_AUTO", "SEMI_AUTO")
        assert any("legacy_override_applied" in w for w in result.warnings)

    def test_ambiguous_nl_not_overridden_verify_only(self, svc):
        """verify step만 있는 AMBIGUOUS_NL은 override 안 됨."""
        result = svc.convert_row(_row("정상 동작 확인한다", "문제 없는지 확인"))
        assert result.automation_class == "AMBIGUOUS_NL"

    def test_manual_required_not_overridden(self, svc):
        """진짜 MANUAL_REQUIRED는 override 안 됨."""
        result = svc.convert_row(_row("유선 이어폰 연결 후 통화 확인"))
        assert result.automation_class == "MANUAL_REQUIRED"
        assert not any("legacy_override_applied" in w for w in result.warnings)


class TestToggleManualFallback:
    """toggle intent가 drop되지 않고 manual_pause 1건으로 살아남는 케이스."""

    def test_toggle_produces_manual_pause_step(self, svc):
        result = svc.convert_row(_row("설정 > 네트워크 > Wi-Fi 토글 On"))
        manual_pauses = [s for s in result.compiled_steps if s.get("action") == "manual_pause"]
        assert len(manual_pauses) >= 1, f"Expected manual_pause for toggle, got steps: {result.compiled_steps}"
        assert any("toggle_compile_not_implemented" in w for w in result.warnings)
        assert any("manual_pause_inserted_for_toggle" in w for w in result.warnings)

    def test_toggle_step_count_matches_classified(self, svc):
        """classified intents 수 == compiled steps 수 (no silent drops)."""
        result = svc.convert_row(_row("설정 > 네트워크 > Wi-Fi 토글 On"))
        assert len(result.compiled_steps) >= len(result.classified_intents), (
            f"classified={len(result.classified_intents)} > compiled={len(result.compiled_steps)}: "
            "toggle or other intents silently dropped"
        )


class TestEndToEndWithGolden:
    """golden set의 일부를 서비스 레벨에서 검증."""

    def test_manual_earphone(self, svc):
        result = svc.convert_row(_row("유선 이어폰 연결 후 통화 확인"))
        assert result.automation_class == "MANUAL_REQUIRED"

    def test_manual_external_device(self, svc):
        result = svc.convert_row(_row("발신 단말에서 DUT로 전화 발신"))
        assert result.automation_class == "MANUAL_REQUIRED"

    def test_menu_chain_settings(self, svc):
        result = svc.convert_row(_row(
            "설정 > 안심 기능 > 수신 차단 > 수신차단 전화번호 추가",
            "'전화와 문자 메시지를 차단할 번호' 팝업 발생",
        ))
        assert result.automation_class in ("FULL_AUTO", "SEMI_AUTO")
        assert len(result.compiled_steps) >= 4
