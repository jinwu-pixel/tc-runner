"""AppExplorer 단위 테스트 (ADB mock)."""
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import json

from src.app_explorer import (
    AppExplorer, AppMap, ScreenInfo,
    collect_screen_elements, collect_clickable_texts, _sanitize_key,
)


# 테스트용 UI dump XML
MAIN_SCREEN_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
<node text="앱 타이틀" resource-id="title" class="android.widget.TextView"
      clickable="false" bounds="[0,0][1080,100]" />
<node text="메뉴A" resource-id="btn_a" class="android.widget.Button"
      clickable="true" bounds="[100,200][500,300]" />
<node text="메뉴B" resource-id="btn_b" class="android.widget.Button"
      clickable="true" bounds="[100,400][500,500]" />
<node text="" resource-id="empty" class="android.view.View"
      clickable="true" bounds="[0,0][10,10]" />
</hierarchy>'''

SUB_SCREEN_A_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
<node text="메뉴A 상세" resource-id="detail" class="android.widget.TextView"
      clickable="false" bounds="[0,0][1080,100]" />
<node text="항목1" resource-id="item1" class="android.widget.TextView"
      clickable="false" bounds="[100,200][500,300]" />
<node text="항목2" resource-id="item2" class="android.widget.Button"
      clickable="true" bounds="[100,400][500,500]" />
</hierarchy>'''

SUB_SCREEN_B_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
<node text="앱 타이틀" resource-id="title" class="android.widget.TextView"
      clickable="false" bounds="[0,0][1080,100]" />
<node text="메뉴A" resource-id="btn_a" class="android.widget.Button"
      clickable="true" bounds="[100,200][500,300]" />
<node text="메뉴B" resource-id="btn_b" class="android.widget.Button"
      clickable="true" bounds="[100,400][500,500]" />
</hierarchy>'''


class TestCollectScreenElements:
    def test_collects_all_text_elements(self):
        elements = collect_screen_elements(MAIN_SCREEN_XML)
        texts = [e["text"] for e in elements]
        assert "앱 타이틀" in texts
        assert "메뉴A" in texts
        assert "메뉴B" in texts

    def test_skips_empty_text(self):
        elements = collect_screen_elements(MAIN_SCREEN_XML)
        texts = [e["text"] for e in elements]
        assert "" not in texts

    def test_parses_coordinates(self):
        elements = collect_screen_elements(MAIN_SCREEN_XML)
        menu_a = next(e for e in elements if e["text"] == "메뉴A")
        assert menu_a["x"] == 300  # (100+500)//2
        assert menu_a["y"] == 250  # (200+300)//2

    def test_clickable_flag(self):
        elements = collect_screen_elements(MAIN_SCREEN_XML)
        title = next(e for e in elements if e["text"] == "앱 타이틀")
        menu_a = next(e for e in elements if e["text"] == "메뉴A")
        assert title["clickable"] is False
        assert menu_a["clickable"] is True

    def test_deduplicates_text(self):
        xml = '''<hierarchy>
        <node text="같은텍스트" bounds="[0,0][100,100]" clickable="true" />
        <node text="같은텍스트" bounds="[200,200][300,300]" clickable="true" />
        </hierarchy>'''
        elements = collect_screen_elements(xml)
        assert len(elements) == 1


class TestCollectClickableTexts:
    def test_only_clickable(self):
        clickable = collect_clickable_texts(MAIN_SCREEN_XML)
        texts = [e["text"] for e in clickable]
        assert "메뉴A" in texts
        assert "메뉴B" in texts
        assert "앱 타이틀" not in texts

    def test_empty_text_excluded(self):
        clickable = collect_clickable_texts(MAIN_SCREEN_XML)
        assert all(e["text"] for e in clickable)


class TestSanitizeKey:
    def test_korean(self):
        assert _sanitize_key("메뉴A") == "메뉴A"

    def test_special_chars(self):
        result = _sanitize_key("a/b c!d")
        assert "/" not in result
        assert "!" not in result

    def test_truncation(self):
        long = "가" * 50
        assert len(_sanitize_key(long)) <= 30


class TestAppExplorer:
    def _make_adb(self, dump_sequence):
        """dump_ui()가 호출될 때마다 순서대로 XML을 반환하는 mock ADB."""
        adb = MagicMock()
        adb.dump_ui = MagicMock(side_effect=dump_sequence)
        adb.shell = MagicMock(return_value="")
        adb.tap = MagicMock()
        adb.key = MagicMock()
        return adb

    def test_explore_collects_main_and_subs(self):
        adb = self._make_adb([MAIN_SCREEN_XML, SUB_SCREEN_A_XML, SUB_SCREEN_B_XML])
        explorer = AppExplorer(adb, wait_after_tap=0, wait_after_back=0)
        app_map = explorer.explore("com.test.app")

        assert app_map.package == "com.test.app"
        assert "main" in app_map.screens
        assert len(app_map.screens) == 3  # main + 2 subs
        assert len(app_map.transitions) == 2

    def test_main_screen_has_clickable_texts(self):
        adb = self._make_adb([MAIN_SCREEN_XML, SUB_SCREEN_A_XML, SUB_SCREEN_B_XML])
        explorer = AppExplorer(adb, wait_after_tap=0, wait_after_back=0)
        app_map = explorer.explore("com.test.app")

        main = app_map.screens["main"]
        assert "메뉴A" in main.clickable_texts
        assert "메뉴B" in main.clickable_texts

    def test_taps_each_clickable_element(self):
        adb = self._make_adb([MAIN_SCREEN_XML, SUB_SCREEN_A_XML, SUB_SCREEN_B_XML])
        explorer = AppExplorer(adb, wait_after_tap=0, wait_after_back=0)
        explorer.explore("com.test.app")

        assert adb.tap.call_count == 2
        assert adb.key.call_count == 2  # 2x BACK

    def test_same_screen_detection(self):
        # 메뉴B를 탭하면 같은 화면(팝업 등 없이 그대로) → same_screen=True
        adb = self._make_adb([MAIN_SCREEN_XML, SUB_SCREEN_A_XML, SUB_SCREEN_B_XML])
        explorer = AppExplorer(adb, wait_after_tap=0, wait_after_back=0)
        app_map = explorer.explore("com.test.app")

        t_a = app_map.transitions[0]
        t_b = app_map.transitions[1]
        assert t_a["same_screen"] is False  # sub A는 다른 화면
        # sub B는 main과 텍스트 동일 (빈 텍스트 노드 제외하면)
        # SUB_SCREEN_B_XML has same texts as MAIN minus empty node → not exact same set
        # Actually let's check: main has {앱 타이틀, 메뉴A, 메뉴B}, sub_b has {앱 타이틀, 메뉴A, 메뉴B}
        assert t_b["same_screen"] is True

    def test_max_elements_limit(self):
        adb = self._make_adb([MAIN_SCREEN_XML, SUB_SCREEN_A_XML])
        explorer = AppExplorer(adb, wait_after_tap=0, wait_after_back=0, max_elements=1)
        app_map = explorer.explore("com.test.app")

        assert len(app_map.transitions) == 1  # max_elements=1 → 1개만 탐색

    def test_save_creates_json(self, tmp_path):
        app_map = AppMap(package="com.test", explore_time=5.0)
        app_map.screens["main"] = ScreenInfo(
            name="main", elements=[{"text": "테스트"}], clickable_texts=["테스트"])

        explorer = AppExplorer(MagicMock())
        out = explorer.save(app_map, tmp_path / "map.json")

        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["package"] == "com.test"
        assert data["screen_count"] == 1
        assert data["screens"]["main"]["clickable_texts"] == ["테스트"]

    def test_to_dict_structure(self):
        app_map = AppMap(package="com.test", explore_time=3.5)
        app_map.screens["main"] = ScreenInfo(name="main", elements=[], clickable_texts=["A"])
        app_map.transitions.append({"from": "main", "action": "tap 'A'", "to": "sub_00_A"})

        d = app_map.to_dict()
        assert d["package"] == "com.test"
        assert d["explore_time_seconds"] == 3.5
        assert d["screen_count"] == 1
        assert d["transition_count"] == 1
        assert "main" in d["screens"]
