from src.ui_parser import (
    count_content_desc_matches,
    find_clickable_target_by_content_desc,
    find_element_by_id,
    find_element_by_text,
    find_focused_node,
)

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


# 실제 Music player favorite 구조 재현:
#   - leaf: text="" / content-desc="즐겨찾기" / clickable=false
#   - parent: clickable=true (ancestor bubbling target)
# HOME tab 은 별개 노드로 text="즐겨찾기" / clickable=true (text vs content-desc 분리 검증)
HIERARCHY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node bounds="[0,0][720,1560]" clickable="false">
    <node clickable="true" bounds="[520,96][616,192]">
      <node text="" content-desc="즐겨찾기" clickable="false" bounds="[544,120][592,168]" />
      <node text="" content-desc="" clickable="false" bounds="[528,104][608,184]" />
    </node>
    <node text="홈탭문구" content-desc="홈탭" clickable="true" bounds="[100,1500][200,1560]" />
    <node text="" content-desc="비클릭아이콘" clickable="false" bounds="[300,300][400,400]" />
  </node>
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


# ─── content-desc query ───

def test_content_desc_clickable_leaf_returns_leaf_center():
    status, info = find_clickable_target_by_content_desc(HIERARCHY_XML, "홈탭")
    assert status == "ok"
    assert info["x"] == 150  # (100+200)/2
    assert info["y"] == 1530  # (1500+1560)/2


def test_content_desc_non_clickable_leaf_bubbles_to_clickable_parent():
    # 즐겨찾기 leaf clickable=false → parent clickable=true bounds [520,96][616,192]
    status, info = find_clickable_target_by_content_desc(HIERARCHY_XML, "즐겨찾기")
    assert status == "ok"
    assert info["x"] == 568  # (520+616)/2
    assert info["y"] == 144  # (96+192)/2


def test_content_desc_not_found():
    status, info = find_clickable_target_by_content_desc(HIERARCHY_XML, "없는항목")
    assert status == "not_found"
    assert info is None


def test_content_desc_no_clickable_ancestor_returns_not_clickable():
    status, info = find_clickable_target_by_content_desc(HIERARCHY_XML, "비클릭아이콘")
    assert status == "not_clickable"


def test_content_desc_duplicate_match_returns_duplicate():
    dup_xml = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node clickable="true" bounds="[0,0][100,100]">
    <node content-desc="중복" clickable="false" bounds="[10,10][50,50]" />
  </node>
  <node clickable="true" bounds="[200,200][300,300]">
    <node content-desc="중복" clickable="false" bounds="[210,210][250,250]" />
  </node>
</hierarchy>"""
    status, info = find_clickable_target_by_content_desc(dup_xml, "중복")
    assert status == "duplicate"
    assert info == 2


def test_content_desc_exact_match_only_no_substring():
    # tap_content_desc는 substring 금지 — "즐겨찾"는 "즐겨찾기"와 매칭하지 않음
    status, _ = find_clickable_target_by_content_desc(HIERARCHY_XML, "즐겨찾")
    assert status == "not_found"


def test_count_content_desc_matches_zero():
    assert count_content_desc_matches(HIERARCHY_XML, "없는항목") == 0


def test_count_content_desc_matches_one():
    assert count_content_desc_matches(HIERARCHY_XML, "즐겨찾기") == 1


def test_count_content_desc_matches_duplicate_returns_count():
    dup_xml = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node content-desc="중복" bounds="[0,0][50,50]" />
  <node content-desc="중복" bounds="[100,100][150,150]" />
</hierarchy>"""
    assert count_content_desc_matches(dup_xml, "중복") == 2


def test_text_and_content_desc_are_separate_attributes():
    # HOME tab text="즐겨찾기" 가 있어도 tap_content_desc 는 content-desc 노드만 찾는다
    text_only_xml = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="즐겨찾기" content-desc="" clickable="true" bounds="[100,1500][200,1560]" />
</hierarchy>"""
    status, info = find_clickable_target_by_content_desc(text_only_xml, "즐겨찾기")
    assert status == "not_found"
    # 반대: text=비어있어도 content-desc 매칭은 그 자체 attribute만 본다
    assert count_content_desc_matches(text_only_xml, "즐겨찾기") == 0


# ─── find_focused_node ───

FOCUSED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="A" focused="false" bounds="[0,0][100,100]" />
  <node text="B" focused="true" bounds="[100,0][200,100]" />
  <node text="C" focused="false" bounds="[200,0][300,100]" />
</hierarchy>"""

NO_FOCUS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="A" focused="false" bounds="[0,0][100,100]" />
  <node text="B" focused="false" bounds="[100,0][200,100]" />
</hierarchy>"""


def test_find_focused_node_returns_focused_attrib():
    node = find_focused_node(FOCUSED_XML)
    assert node is not None
    assert node.get("focused") == "true"
    assert node.get("text") == "B"
    assert node.get("bounds") == "[100,0][200,100]"


def test_find_focused_node_returns_none_when_no_focus():
    assert find_focused_node(NO_FOCUS_XML) is None


def test_find_focused_node_returns_none_on_parse_error():
    # invalid XML — not a parse error from ET's perspective if completely malformed
    # use clearly broken structure
    assert find_focused_node("<hierarchy><node unclosed") is None
    assert find_focused_node("") is None
