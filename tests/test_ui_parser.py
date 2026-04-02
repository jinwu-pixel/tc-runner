from src.ui_parser import find_element_by_text, find_element_by_id

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="설정" resource-id="com.android.settings:id/title"
        class="android.widget.TextView" package="com.android.settings"
        bounds="[168,336][912,432]" />
  <node index="1" text="연결" resource-id="com.android.settings:id/title2"
        class="android.widget.TextView" package="com.android.settings"
        bounds="[168,432][912,528]" />
  <node index="2" text="" resource-id="com.android.settings:id/icon"
        class="android.widget.ImageView" package="com.android.settings"
        bounds="[48,336][144,432]" />
</hierarchy>"""


def test_find_element_by_text_found():
    result = find_element_by_text(SAMPLE_XML, "설정")
    assert result is not None
    assert result["x"] == 540  # (168 + 912) // 2
    assert result["y"] == 384  # (336 + 432) // 2
    assert result["text"] == "설정"


def test_find_element_by_text_not_found():
    result = find_element_by_text(SAMPLE_XML, "블루투스")
    assert result is None


def test_find_element_by_id_found():
    result = find_element_by_id(SAMPLE_XML, "com.android.settings:id/title2")
    assert result is not None
    assert result["x"] == 540
    assert result["y"] == 480  # (432 + 528) // 2


def test_find_element_by_id_not_found():
    result = find_element_by_id(SAMPLE_XML, "nonexistent:id/foo")
    assert result is None
