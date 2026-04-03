"""procedure_parser 단위 테스트."""
import pytest
from src.mmi_converter.procedure_parser import ProcedureParser, ProcedureSegmenter


@pytest.fixture
def parser():
    return ProcedureParser()


@pytest.fixture
def segmenter():
    return ProcedureSegmenter()


class TestSegmenter:
    def test_split_by_arrow(self, segmenter):
        result = segmenter.split("설정 > 네트워크 > Wi-Fi")
        assert result == ["설정", "네트워크", "Wi-Fi"]

    def test_split_by_unicode_arrow(self, segmenter):
        result = segmenter.split("설정 → 네트워크 → Wi-Fi")
        assert result == ["설정", "네트워크", "Wi-Fi"]

    def test_split_by_newline(self, segmenter):
        result = segmenter.split("1. 설정 열기\n2. Wi-Fi 선택")
        assert "설정 열기" in result
        assert "Wi-Fi 선택" in result

    def test_empty_input(self, segmenter):
        assert segmenter.split("") == []
        assert segmenter.split(None) == []

    def test_normalize_whitespace(self, segmenter):
        result = segmenter.split("설정  >   네트워크")
        assert result == ["설정", "네트워크"]


class TestMenuChain:
    def test_simple_menu_chain(self, parser):
        intents = parser.parse("설정 > 안심 기능 > 수신 차단")
        assert len(intents) == 3
        assert all(i.type == "navigate" for i in intents)
        assert intents[0].target == "설정"
        assert intents[1].target == "안심 기능"
        assert intents[2].target == "수신 차단"

    def test_deep_menu_chain(self, parser):
        intents = parser.parse("설정 > 네트워크 및 인터넷 > 인터넷 > 통신사 설정 > 기본 네트워크 유형")
        assert len(intents) == 5
        assert intents[4].target == "기본 네트워크 유형"


class TestToggle:
    def test_toggle_on(self, parser):
        intents = parser.parse("Wi-Fi 토글 On")
        assert len(intents) == 1
        assert intents[0].type == "toggle"
        assert intents[0].value == "on"

    def test_toggle_off(self, parser):
        intents = parser.parse("Wi-Fi 토글 버튼 OFF")
        assert len(intents) == 1
        assert intents[0].type == "toggle"
        assert intents[0].value == "off"

    def test_toggle_in_chain(self, parser):
        intents = parser.parse("설정 > 네트워크 > 모바일 데이터 On")
        assert intents[-1].type == "toggle"
        assert intents[-1].value == "on"

    def test_activate_as_toggle(self, parser):
        intents = parser.parse("활성화")
        assert len(intents) == 1
        assert intents[0].type == "toggle"
        assert intents[0].value == "on"


class TestKeyEvent:
    def test_home_key(self, parser):
        intents = parser.parse("Home 키 입력")
        assert any(i.type == "press_key" and i.value == "HOME" for i in intents)

    def test_back_key(self, parser):
        intents = parser.parse("Back 키 입력")
        assert any(i.type == "press_key" and i.value == "BACK" for i in intents)

    def test_recent_key(self, parser):
        intents = parser.parse("최근앱 키 입력")
        assert any(i.type == "press_key" and i.value == "APP_SWITCH" for i in intents)


class TestWait:
    def test_seconds(self, parser):
        intents = parser.parse("3초 대기")
        assert len(intents) == 1
        assert intents[0].type == "wait"
        assert intents[0].value == "3"

    def test_momentary(self, parser):
        intents = parser.parse("잠시 대기")
        assert len(intents) == 1
        assert intents[0].type == "wait"
        assert intents[0].value == "2"


class TestInput:
    def test_input_detected(self, parser):
        intents = parser.parse("번호 입력")
        assert len(intents) == 1
        assert intents[0].type == "input_text"

    def test_input_in_chain(self, parser):
        intents = parser.parse("검색 아이콘 탭 > 임의 문자열 입력")
        assert intents[-1].type == "input_text"


class TestVerify:
    def test_verify_text(self, parser):
        intents = parser.parse("인디게이터 확인")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"

    def test_verify_display(self, parser):
        intents = parser.parse("Wi-Fi 아이콘 표시")
        assert len(intents) == 1
        assert intents[0].type == "verify_text"


class TestAmbiguousProtection:
    def test_empty_procedure(self, parser):
        assert parser.parse("") == []

    def test_no_forced_auto(self, parser):
        """모호한 문장을 억지로 FULL_AUTO intent로 변환하지 않는다."""
        intents = parser.parse("정상 동작")
        # navigate로 나오는 건 괜찮지만, verify_text나 toggle로 과잉해석하면 안 됨
        for i in intents:
            assert i.type not in ("toggle", "verify_shell")


class TestParserMetadata:
    def test_navigate_includes_raw_segment(self, parser):
        intents = parser.parse("설정 > 네트워크")
        assert intents[0].extra.get("raw_segment") == "설정"
        assert intents[0].extra.get("matched_rule") == "navigate_fallback"
        assert intents[0].extra.get("position") == 0
        assert intents[0].extra.get("total_segments") == 2
        assert intents[0].extra.get("source_phase") == "procedure"

    def test_key_includes_matched_rule(self, parser):
        intents = parser.parse("Home 키 입력")
        assert intents[0].extra.get("matched_rule") == "key"
        assert intents[0].extra.get("parser_confidence") == 1.0
