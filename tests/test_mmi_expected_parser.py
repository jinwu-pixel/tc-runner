"""expected_parser 단위 테스트."""
import pytest
from src.mmi_converter.expected_parser import ExpectedResultParser


@pytest.fixture
def parser():
    return ExpectedResultParser()


class TestDisplayPattern:
    def test_shows_pattern(self, parser):
        intents = parser.parse("Wi-Fi가 표시된다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"
        assert intents[0].target == "Wi-Fi"

    def test_exposed_pattern(self, parser):
        intents = parser.parse("상단 인디케이터가 노출된다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"
        assert "인디케이터" in intents[0].target

    def test_visible_pattern(self, parser):
        intents = parser.parse("아이콘이 보인다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"


class TestEntryPattern:
    def test_menu_entry(self, parser):
        intents = parser.parse("잠금 화면 설정 메뉴로 진입된다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"
        assert "잠금 화면 설정" in intents[0].target

    def test_execute_pattern(self, parser):
        intents = parser.parse("카메라 앱이 실행된다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"

    def test_open_pattern(self, parser):
        intents = parser.parse("설정 화면이 열린다")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"


class TestOnOffState:
    def test_on_state(self, parser):
        intents = parser.parse("Wi-Fi ON 상태로 표시된다")
        assert any(i.target == "켬" for i in intents)

    def test_off_state(self, parser):
        intents = parser.parse("비활성화 상태")
        assert any(i.target == "끔" for i in intents)


class TestEdgeCases:
    def test_empty_expected(self, parser):
        assert parser.parse("") == []

    def test_whitespace_only(self, parser):
        assert parser.parse("   ") == []

    def test_ambiguous_expected(self, parser):
        """모호한 기대결과는 무리하게 변환하지 않는다."""
        intents = parser.parse("정상적으로 동작함")
        # 어떤 패턴에도 안 걸리면 빈 리스트
        assert isinstance(intents, list)
