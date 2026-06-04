"""Regression: menu_mapper module-level parsers == legacy MenuMapper methods.

Guards the behavior-preserving refactor (Task 1 of device-menu-tree-baseline).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "menu_mapper.py"
_spec = importlib.util.spec_from_file_location("menu_mapper", _PATH)
mm = importlib.util.module_from_spec(_spec)
sys.modules["menu_mapper"] = mm
_spec.loader.exec_module(mm)

_SAMPLE_XML = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node class="android.widget.TextView" text="설정" resource-id="android:id/title"
        clickable="false" focusable="false" checkable="false" bounds="[0,0][480,60]"/>
  <node class="android.widget.LinearLayout" text="" clickable="true" focusable="true"
        checkable="false" bounds="[0,60][480,160]">
    <node class="android.widget.TextView" text="개인 정보 보호" resource-id="android:id/title"
          clickable="false" focusable="false" checkable="false" bounds="[20,80][300,120]"/>
  </node>
  <node class="android.widget.Switch" text="위치 사용" resource-id="x/sw"
        clickable="true" focusable="true" checkable="true" bounds="[400,60][470,100]"/>
</hierarchy>"""


def test_module_level_extract_nodes_exists_and_parses():
    nodes = mm.extract_nodes(_SAMPLE_XML)
    labels = [n.get("text") for n in nodes if n.get("text")]
    assert "설정" in labels and "개인 정보 보호" in labels and "위치 사용" in labels


def test_method_delegates_to_module_function():
    # Legacy MenuMapper.extract_nodes must return identical output to module fn.
    class _Args:
        mode = "inventory"; package = "com.android.settings"; max_depth = 3
    mapper = mm.MenuMapper(adb=None, args=_Args())
    assert mapper.extract_nodes(_SAMPLE_XML) == mm.extract_nodes(_SAMPLE_XML)


def test_module_level_fingerprint_stable():
    nodes = mm.extract_nodes(_SAMPLE_XML)
    fp1 = mm.generate_fingerprint("com.android.settings/.Settings", nodes)
    fp2 = mm.generate_fingerprint("com.android.settings/.Settings", nodes)
    assert fp1 == fp2 and len(fp1) == 8


def test_constants_exposed():
    assert "긴급" in mm.DENYLIST
    assert "com.android.settings" in mm.ALLOWLIST_PACKAGES
