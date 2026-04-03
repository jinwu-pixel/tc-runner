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
