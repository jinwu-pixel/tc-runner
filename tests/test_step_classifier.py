# tests/test_step_classifier.py
"""StepClassifier 단위 테스트."""
import pytest
from src.mmi_converter.models import (
    ExecutionMode, StepRole, ClassifiedIntent, Intent,
)


class TestClassifiedIntent:
    def test_basic_construction(self):
        intent = Intent(type="navigate", target="설정")
        ci = ClassifiedIntent(
            intent=intent,
            execution_mode="UI_AUTO",
            step_role="ACTION",
        )
        assert ci.execution_mode == "UI_AUTO"
        assert ci.step_role == "ACTION"
        assert ci.confidence == 1.0
        assert ci.reasons == []

    def test_with_reasons(self):
        intent = Intent(type="navigate", target="수신 전화")
        ci = ClassifiedIntent(
            intent=intent,
            execution_mode="EXTERNAL_EVENT",
            step_role="ACTION",
            confidence=0.9,
            reasons=["external_keyword_match: '수신 전화' → EXTERNAL_EVENT"],
        )
        assert ci.execution_mode == "EXTERNAL_EVENT"
        assert len(ci.reasons) == 1


from src.mmi_converter.step_classifier import StepClassifier


@pytest.fixture
def classifier():
    return StepClassifier()


class TestStage1Defaults:
    """Intent.type 기반 기본 매핑."""

    def test_navigate_is_ui_auto_action(self, classifier):
        intents = [Intent(type="navigate", target="설정")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ACTION"

    def test_press_key_is_ui_auto_action(self, classifier):
        intents = [Intent(type="press_key", value="HOME")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ACTION"

    def test_verify_text_is_ui_auto_assert(self, classifier):
        intents = [Intent(type="verify_text", target="Wi-Fi")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_verify_shell_is_shell_auto_assert(self, classifier):
        intents = [Intent(type="verify_shell", target="dumpsys")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "SHELL_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_manual_required_is_manual(self, classifier):
        intents = [Intent(type="manual_required", target="이어폰 연결")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"


class TestStage2KeywordRefinement:
    """키워드 기반 ExecutionMode 재분류."""

    def test_external_keyword_overrides_ui_auto(self, classifier):
        intents = [Intent(type="navigate", target="수신 전화")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "EXTERNAL_EVENT"

    def test_manual_keyword_overrides_ui_auto(self, classifier):
        intents = [Intent(type="navigate", target="이어폰 연결 후 확인")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"

    def test_assert_role_blocks_shell_transition(self, classifier):
        """ASSERT role에서 lexical match로 SHELL_AUTO 전이 차단."""
        intents = [Intent(type="verify_text", target="logcat 확인")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert result[0].step_role == "ASSERT"

    def test_assert_allows_external_transition(self, classifier):
        """ASSERT role에서 EXTERNAL_EVENT 전이는 허용."""
        intents = [Intent(type="verify_text", target="수신 전화 수신 확인")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "EXTERNAL_EVENT"

    def test_manual_priority_over_external(self, classifier):
        """MANUAL_REQUIRED > EXTERNAL_EVENT 우선순위."""
        intents = [Intent(type="navigate", target="이어폰 연결 후 수신 전화")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "MANUAL_REQUIRED"

    def test_shell_candidate_without_map_stays_ui(self, classifier):
        """shell_action_map 없으면 SHELL_AUTO 승격 안 함."""
        intents = [Intent(type="navigate", target="앱 실행")]
        result = classifier.classify(intents)
        assert result[0].execution_mode == "UI_AUTO"
        assert any("shell_mapping_missing" in r for r in result[0].reasons)


class TestStage3SetupTeardown:
    """위치/context 기반 StepRole 조정."""

    def test_first_step_setup_hint(self, classifier):
        intents = [
            Intent(type="navigate", target="초기화"),
            Intent(type="navigate", target="설정"),
        ]
        result = classifier.classify(intents)
        assert result[0].step_role == "SETUP"

    def test_last_step_teardown_hint(self, classifier):
        intents = [
            Intent(type="navigate", target="설정"),
            Intent(type="navigate", target="초기화"),
        ]
        result = classifier.classify(intents)
        assert result[1].step_role == "TEARDOWN"

    def test_middle_step_no_role_change(self, classifier):
        intents = [
            Intent(type="navigate", target="설정"),
            Intent(type="navigate", target="초기화"),
            Intent(type="navigate", target="확인"),
        ]
        result = classifier.classify(intents)
        assert result[1].step_role == "ACTION"


class TestSummarizeTcClass:
    """TC-level summary 도출."""

    def test_empty_returns_ambiguous(self, classifier):
        assert classifier.summarize_tc_class([]) == "AMBIGUOUS_NL"

    def test_all_ui_auto_is_full_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="네트워크"), "UI_AUTO", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "FULL_AUTO"

    def test_mixed_ui_shell_is_full_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="verify_shell", target="dumpsys"), "SHELL_AUTO", "ASSERT"),
        ]
        assert classifier.summarize_tc_class(classified) == "FULL_AUTO"

    def test_manual_makes_semi_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="이어폰 연결"), "MANUAL_REQUIRED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "SEMI_AUTO"

    def test_all_unsupported_is_ambiguous(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="???"), "UNSUPPORTED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "AMBIGUOUS_NL"

    def test_partial_unsupported_is_semi_auto(self, classifier):
        classified = [
            ClassifiedIntent(Intent(type="navigate", target="설정"), "UI_AUTO", "ACTION"),
            ClassifiedIntent(Intent(type="navigate", target="???"), "UNSUPPORTED", "ACTION"),
        ]
        assert classifier.summarize_tc_class(classified) == "SEMI_AUTO"
