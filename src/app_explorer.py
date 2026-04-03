"""앱 자동 탐색기: 1-depth BFS로 화면 구조를 수집하여 앱 맵을 생성한다.

사용법:
    explorer = AppExplorer(adb)
    app_map = explorer.explore("com.example.seniorshield")
    explorer.save(app_map, Path("app_map.json"))

# TODO [3단계]: TC 매칭기
# 탐색 결과(app_map)와 TC 요구사항(엑셀/YAML)을 대조하여
# 실행 가능한 TC YAML을 자동 생성하는 기능.
# AppMap의 screen→element→sub_screen 그래프를 순회하며
# TC 절차 텍스트의 각 단계가 어떤 화면의 어떤 요소에 매핑되는지 찾고,
# 매핑 결과를 바탕으로 YAML steps를 자동 조립한다.
# 구현 시 고려사항:
#   - TC 절차 텍스트 ↔ 화면 요소 텍스트 유사도 매칭 (exact + fuzzy)
#   - 다중 경로 존재 시 최단 경로 선택
#   - 매칭 실패 시 manual_pause fallback
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.adb import ADB


def _find_nodes(xml_str: str) -> list[dict]:
    """UI dump XML에서 모든 node의 속성을 파싱한다."""
    nodes = []
    for match in re.finditer(r'<node\s+([^>]+)/?>', xml_str):
        attrs_str = match.group(1)
        attrs = {}
        for attr_match in re.finditer(r'(\w[\w-]*)="([^"]*)"', attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)
        nodes.append(attrs)
    return nodes


def _parse_bounds(bounds_str: str) -> tuple[int, int]:
    """bounds 문자열 → 중심 좌표 (x, y)."""
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
    if not match:
        return 0, 0
    x1, y1, x2, y2 = (int(match.group(i)) for i in range(1, 5))
    return (x1 + x2) // 2, (y1 + y2) // 2


def collect_screen_elements(xml_str: str) -> list[dict]:
    """화면의 모든 텍스트 요소를 수집한다."""
    elements = []
    seen_texts = set()
    for node in _find_nodes(xml_str):
        text = node.get("text", "").strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        x, y = _parse_bounds(node.get("bounds", ""))
        elements.append({
            "text": text,
            "x": x,
            "y": y,
            "clickable": node.get("clickable") == "true",
            "class": node.get("class", ""),
            "resource_id": node.get("resource-id", ""),
        })
    return elements


def collect_clickable_texts(xml_str: str) -> list[dict]:
    """화면에서 클릭 가능한 텍스트 요소만 수집한다."""
    return [e for e in collect_screen_elements(xml_str) if e["clickable"] and e["text"]]


@dataclass
class ScreenInfo:
    """화면 하나의 정보."""
    name: str
    elements: list[dict] = field(default_factory=list)
    clickable_texts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "elements": self.elements,
            "clickable_texts": self.clickable_texts,
        }


@dataclass
class AppMap:
    """앱의 화면 구조 맵."""
    package: str
    screens: dict[str, ScreenInfo] = field(default_factory=dict)
    transitions: list[dict] = field(default_factory=list)
    explore_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "explore_time_seconds": round(self.explore_time, 1),
            "screen_count": len(self.screens),
            "transition_count": len(self.transitions),
            "screens": {k: v.to_dict() for k, v in self.screens.items()},
            "transitions": self.transitions,
        }


class AppExplorer:
    """1-depth BFS 앱 탐색기.

    메인 화면에서 클릭 가능한 요소를 하나씩 탭하고,
    진입한 서브 화면의 요소를 수집한 후 BACK으로 돌아온다.
    """

    def __init__(self, adb: ADB, wait_after_tap: float = 2.0,
                 wait_after_back: float = 1.0, max_elements: int = 20):
        self.adb = adb
        self.wait_after_tap = wait_after_tap
        self.wait_after_back = wait_after_back
        self.max_elements = max_elements

    def explore(self, package: str, activity: str = ".MainActivity") -> AppMap:
        """앱을 실행하고 1-depth 탐색을 수행한다."""
        start = time.time()
        app_map = AppMap(package=package)

        # 1. 앱 실행
        self.adb.shell(f"am force-stop {package}")
        time.sleep(0.5)
        self.adb.shell(f"am start -n {package}/{activity}")
        time.sleep(self.wait_after_tap)

        # 2. 메인 화면 수집
        main_xml = self.adb.dump_ui()
        main_elements = collect_screen_elements(main_xml)
        clickable = collect_clickable_texts(main_xml)

        main_screen = ScreenInfo(
            name="main",
            elements=main_elements,
            clickable_texts=[e["text"] for e in clickable],
        )
        app_map.screens["main"] = main_screen

        # 3. 클릭 가능한 요소를 하나씩 탭 → 서브 화면 수집 → BACK
        for i, elem in enumerate(clickable[:self.max_elements]):
            text = elem["text"]
            screen_key = f"sub_{i:02d}_{_sanitize_key(text)}"

            self.adb.tap(elem["x"], elem["y"])
            time.sleep(self.wait_after_tap)

            sub_xml = self.adb.dump_ui()
            sub_elements = collect_screen_elements(sub_xml)
            sub_clickable = collect_clickable_texts(sub_xml)

            # 같은 화면인지 간단 판별 (텍스트 집합 비교)
            main_texts = {e["text"] for e in main_elements}
            sub_texts = {e["text"] for e in sub_elements}
            is_same = (sub_texts == main_texts)

            sub_screen = ScreenInfo(
                name=screen_key,
                elements=sub_elements,
                clickable_texts=[e["text"] for e in sub_clickable],
            )
            app_map.screens[screen_key] = sub_screen

            app_map.transitions.append({
                "from": "main",
                "action": f"tap '{text}'",
                "to": screen_key,
                "same_screen": is_same,
            })

            # BACK으로 복귀
            self.adb.key("BACK")
            time.sleep(self.wait_after_back)

        app_map.explore_time = time.time() - start
        return app_map

    def save(self, app_map: AppMap, path: Path) -> Path:
        """AppMap을 JSON 파일로 저장한다."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(app_map.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def print_summary(self, app_map: AppMap) -> None:
        """탐색 결과 요약을 출력한다."""
        print(f"\n{'='*50}")
        print(f"  앱 탐색 완료: {app_map.package}")
        print(f"{'='*50}")
        print(f"  화면 수     : {len(app_map.screens)}")
        print(f"  전이 수     : {len(app_map.transitions)}")
        print(f"  소요 시간   : {app_map.explore_time:.1f}초")

        main = app_map.screens.get("main")
        if main:
            print(f"\n  [메인 화면] 요소 {len(main.elements)}개, "
                  f"클릭 가능 {len(main.clickable_texts)}개")
            for text in main.clickable_texts:
                print(f"    • {text}")

        for t in app_map.transitions:
            marker = " (동일 화면)" if t.get("same_screen") else ""
            to_screen = app_map.screens.get(t["to"])
            elem_count = len(to_screen.elements) if to_screen else 0
            print(f"\n  {t['action']} → [{t['to']}] ({elem_count}개 요소){marker}")
            if to_screen and not t.get("same_screen"):
                for e in to_screen.elements[:8]:
                    print(f"    - {e['text']}")
                if len(to_screen.elements) > 8:
                    print(f"    ... +{len(to_screen.elements) - 8}개")


def _sanitize_key(text: str) -> str:
    """화면 키로 사용할 수 있도록 텍스트를 정리한다."""
    clean = re.sub(r'[^\w가-힣]', '_', text)
    return clean[:30].strip('_') or "unknown"
