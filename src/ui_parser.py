import re
from typing import Optional


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
