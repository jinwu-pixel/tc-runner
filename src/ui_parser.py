import re
from typing import Optional
from xml.etree import ElementTree as ET


def _parse_bounds(bounds_str: str) -> dict:
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
    if not match:
        return {"x": 0, "y": 0}
    x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
    return {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2}


def _find_nodes(xml_str: str) -> list[dict]:
    nodes = []
    for match in re.finditer(r'<node\s+([^>]+)/>', xml_str):
        attrs_str = match.group(1)
        attrs = {}
        for attr_match in re.finditer(r'(\w[\w-]*)="([^"]*)"', attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)
        nodes.append(attrs)
    return nodes


def find_element_by_text(xml_str: str, text: str) -> Optional[dict]:
    for node in _find_nodes(xml_str):
        if text in node.get("text", ""):
            coords = _parse_bounds(node.get("bounds", ""))
            return {"x": coords["x"], "y": coords["y"], "text": text}
    return None


def find_element_by_id(xml_str: str, resource_id: str) -> Optional[dict]:
    for node in _find_nodes(xml_str):
        if node.get("resource-id") == resource_id:
            coords = _parse_bounds(node.get("bounds", ""))
            return {"x": coords["x"], "y": coords["y"], "id": resource_id}
    return None


def find_focused_node(xml_str: str) -> Optional[dict]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None
    for node in root.iter("node"):
        if node.get("focused") == "true":
            return node.attrib
    return None


def _bounds_center(bounds_str: str) -> Optional[tuple[int, int]]:
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
    if not match:
        return None
    x1, y1, x2, y2 = (int(match.group(i)) for i in range(1, 5))
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def find_clickable_target_by_content_desc(xml_str: str, target: str) -> tuple[str, object]:
    # exact content-desc match → clickable target resolution.
    # leaf clickable=false → walk ancestors until clickable=true.
    # status: "ok" / "not_found" / "duplicate" / "not_clickable".
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return ("not_found", None)

    matches = [n for n in root.iter("node") if n.get("content-desc") == target]
    if not matches:
        return ("not_found", None)
    if len(matches) > 1:
        return ("duplicate", len(matches))

    parent_map = {child: parent for parent in root.iter() for child in parent}
    current = matches[0]
    while current is not None:
        if current.get("clickable") == "true":
            center = _bounds_center(current.get("bounds", ""))
            if center is not None:
                return ("ok", {"x": center[0], "y": center[1]})
            return ("not_clickable", None)
        current = parent_map.get(current)
    return ("not_clickable", None)


def count_content_desc_matches(xml_str: str, target: str) -> int:
    # exact content-desc presence count for verify_content_desc.
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return 0
    return sum(1 for n in root.iter("node") if n.get("content-desc") == target)
