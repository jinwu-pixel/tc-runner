# Device Menu Tree Baseline (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe, reproducible real-device auto-exploration tool that emits a canonical device-sourced Settings menu-tree baseline artifact (JSON + MD) for THOR2_K (ko-KR).

**Architecture:** A thin orchestration driver (`scripts/settings_tree_explorer.py`) reads a curated seed of Settings deep-links, opens each via `am start` (read-only — no semantic taps), captures `uiautomator dump` + scroll-revealed nodes, and serializes everything through a pure schema/emitter module (`src/menu_tree.py`). Node parsing/fingerprint/denylist are reused from `scripts/menu_mapper.py` (refactored to module-level functions). `src/menu_tree.py` MUST NOT import `scripts/menu_mapper.py` (src→scripts dependency forbidden); only the driver imports both.

**Tech Stack:** Python 3.11+, stdlib (`dataclasses`, `xml.etree`, `json`, `argparse`, `re`, `hashlib`), PyYAML (seed), pytest. ADB via `src/adb.py`. Interpreter: `venv/Scripts/python.exe`.

**Spec:** `docs/superpowers/specs/2026-06-02-device-menu-tree-baseline-design.md`

---

## ⚠️ Commit policy (overrides default "frequent commits")

Global commit policy (`~/.claude/CLAUDE.md`) forbids in-progress commits. **Every task below ends with a "Checkpoint — DO NOT COMMIT" step**, not a commit. A single batch commit happens only in the final task, **gated on explicit user "commit now"**. Never `git add .` / `-A` / broad add — explicit paths only.

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `scripts/menu_mapper.py` | Modify | Extract 4 pure parsers + `DENYLIST`/`ALLOWLIST_PACKAGES` to module-level; keep `MenuMapper` methods as wrappers (behavior unchanged). |
| `src/menu_tree.py` | Create | Pure schema (dataclasses) + classifiers (`classify_kind`, `text_role_hint`, `detect_script`, `build_element`, `bucket_texts`) + JSON/MD emitters. No device, no `scripts` import. |
| `scripts/settings_tree_explorer.py` | Create | Driver: `GuardedADB` (read-only command allowlist) + seed loader + per-screen reach/dump/parse/scroll + emit + CLI. |
| `THOR2_K - Settings/menu_tree_seed.yaml` | Create | Curated seed (~20 screens) from existing `MENU_TREE.md`. |
| `THOR2_K - Settings/catalog_schema.md` | Modify | Add Tier D paragraph. |
| `tests/fixtures/menu_tree/*.xml` | Create | 3 real uiautomator dumps copied from `THOR2_K - Settings/catalog/` as stable fixtures. |
| `tests/test_menu_mapper_refactor.py` | Create | Regression: module-level fns == old method outputs. |
| `tests/test_menu_tree.py` | Create | Schema/classifier/emitter/determinism tests on fixtures. |
| `tests/test_settings_tree_explorer.py` | Create | Stub-ADB driver tests: reach classification, scroll termination, recovery, summary, target-mismatch abort, `--dry-run`, allowlist-violation==0. |

---

## Task 1: Refactor menu_mapper.py parsers to module-level (behavior-preserving)

**Files:**
- Modify: `scripts/menu_mapper.py`
- Test: `tests/test_menu_mapper_refactor.py`

- [ ] **Step 1: Write the failing regression test**

Create `tests/test_menu_mapper_refactor.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_mapper_refactor.py -v`
Expected: FAIL — `AttributeError: module 'menu_mapper' has no attribute 'extract_nodes'` (functions are currently methods).

- [ ] **Step 3: Refactor — extract methods to module-level functions, keep methods as wrappers**

In `scripts/menu_mapper.py`, move the bodies of `extract_nodes`, `generate_fingerprint`, `parse_bounds`, `is_node_safe` to module-level functions (after the `ALLOWLIST_PACKAGES` constant, before `class MenuMapper`). Keep `DENYLIST`/`ALLOWLIST_PACKAGES` where they are (already module-level). Module-level functions:

```python
def parse_bounds(bounds_str: str):
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
    if not match:
        return None
    x1, y1, x2, y2 = map(int, match.groups())
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def extract_nodes(xml_str: str):
    try:
        start_idx = xml_str.find("<?xml")
        if start_idx != -1:
            xml_str = xml_str[start_idx:]
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"Failed to parse XML: {e}")
        return []
    nodes = []
    parent_map = {c: p for p in root.iter() for c in p}
    for elem in root.iter("node"):
        attrib = dict(elem.attrib)
        curr = elem
        is_clickable = False
        is_focusable = False
        while curr is not None:
            if curr.attrib.get("clickable") == "true":
                is_clickable = True
            if curr.attrib.get("focusable") == "true":
                is_focusable = True
            if is_clickable and is_focusable:
                break
            curr = parent_map.get(curr)
        attrib["inherited_clickable"] = "true" if is_clickable else "false"
        attrib["inherited_focusable"] = "true" if is_focusable else "false"
        nodes.append(attrib)
    return nodes


def generate_fingerprint(current_focus: str, nodes: list) -> str:
    texts = [n.get("text", "") for n in nodes if n.get("text")]
    rids = [n.get("resource-id", "") for n in nodes if n.get("resource-id")]
    raw_str = current_focus + "|" + "|".join(sorted(texts)) + "|" + "|".join(sorted(rids))
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:8]


def is_node_safe(node: dict) -> tuple[bool, str]:
    if node.get("checkable") == "true":
        return False, "checkable=true"
    if node.get("class") in ["android.widget.Switch", "android.widget.CheckBox", "android.widget.RadioButton"]:
        return False, "switch/checkbox/radio"
    text = node.get("text", "")
    content_desc = node.get("content-desc", "")
    label = text if text else content_desc
    if not label:
        return False, "no_label"
    for deny in DENYLIST:
        if deny.lower() in label.lower():
            return False, f"denylist_match_{deny}"
    if node.get("clickable") == "true" or node.get("focusable") == "true" or \
       node.get("inherited_clickable") == "true" or node.get("inherited_focusable") == "true":
        return True, "ok"
    return False, "not_clickable_or_focusable"
```

Then replace the four `MenuMapper` methods with thin wrappers (delegating to module functions) so all existing call sites and behavior are unchanged:

```python
    def parse_bounds(self, bounds_str: str):
        return parse_bounds(bounds_str)

    def extract_nodes(self, xml_str: str):
        return extract_nodes(xml_str)

    def generate_fingerprint(self, current_focus: str, nodes: list) -> str:
        return generate_fingerprint(current_focus, nodes)

    def is_node_safe(self, node: dict) -> tuple[bool, str]:
        return is_node_safe(node)
```

- [ ] **Step 4: Run the refactor regression + existing menu_mapper behavior**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_mapper_refactor.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 1 done — menu_mapper parsers module-level, methods wrap, regression GREEN." Do not stage or commit (global policy §7). Continue.

---

## Task 2: src/menu_tree.py — classifiers (TDD)

**Files:**
- Create: `src/menu_tree.py`
- Test: `tests/test_menu_tree.py`

- [ ] **Step 1: Write the failing classifier tests**

Create `tests/test_menu_tree.py`:

```python
"""Tests for src/menu_tree.py (canonical menu-tree baseline schema + classifiers)."""
from __future__ import annotations

from src import menu_tree as mt


def _node(**kw):
    base = {"text": "", "content-desc": "", "class": "", "resource-id": "",
            "clickable": "false", "focusable": "false", "checkable": "false",
            "inherited_clickable": "false", "inherited_focusable": "false", "bounds": ""}
    base.update(kw)
    return base


def test_detect_script_buckets():
    assert mt.detect_script("개인 정보 보호") == "ko"
    assert mt.detect_script("Wi-Fi") == "en"
    assert mt.detect_script("バッテリー") == "other"
    assert mt.detect_script("T 로밍") == "ko"  # any Hangul -> ko


def test_classify_kind():
    assert mt.classify_kind(_node(text="위치 사용", **{"class": "android.widget.Switch", "checkable": "true"})) == "toggle"
    assert mt.classify_kind(_node(text="검색", **{"class": "android.widget.EditText"})) == "input"
    assert mt.classify_kind(_node(text="확인", **{"class": "android.widget.Button", "clickable": "true"})) == "button"
    assert mt.classify_kind(_node(text="개인 정보 보호", clickable="true", focusable="true")) == "menu_row"
    assert mt.classify_kind(_node(text="설정", **{"resource-id": "android:id/title"})) == "title"
    assert mt.classify_kind(_node()) == "unknown"


def test_text_role_hint():
    assert mt.text_role_hint(_node(**{"resource-id": "android:id/title"})) == "primary"
    assert mt.text_role_hint(_node(**{"resource-id": "android:id/summary"})) == "summary"
    assert mt.text_role_hint(_node(**{"resource-id": "x/icon"})) == "unknown"


def test_build_element_risk_precedence():
    sw = mt.build_element(_node(text="위치 사용", **{"class": "android.widget.Switch", "checkable": "true"}), denylisted=False)
    assert sw.kind == "toggle" and sw.risk == "toggle"
    deny = mt.build_element(_node(text="삭제", clickable="true"), denylisted=True)
    assert deny.risk == "denylist"  # denylist > structural
    plain = mt.build_element(_node(text="개인 정보 보호", clickable="true", focusable="true"), denylisted=False)
    assert plain.kind == "menu_row" and plain.risk == "none"
    chk = mt.build_element(_node(text="동의", **{"class": "android.widget.CheckedTextView", "checkable": "true"}), denylisted=False)
    assert chk.risk == "checkable"


def test_bucket_texts_sorted_and_deduped():
    els = [
        mt.build_element(_node(text="Wi-Fi", clickable="true"), denylisted=False),
        mt.build_element(_node(text="개인 정보 보호", clickable="true"), denylisted=False),
        mt.build_element(_node(text="Wi-Fi", clickable="true"), denylisted=False),
        mt.build_element(_node(text="", clickable="true"), denylisted=False),
    ]
    buckets = mt.bucket_texts(els)
    assert buckets["en"] == ["Wi-Fi"]
    assert buckets["ko"] == ["개인 정보 보호"]
    assert buckets["other"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.menu_tree'`.

- [ ] **Step 3: Implement classifiers in src/menu_tree.py**

Create `src/menu_tree.py`:

```python
"""Canonical device-sourced Settings menu-tree baseline (v1).

Pure & device-independent: dataclasses + classifiers + JSON/MD emitters.
MUST NOT import scripts.menu_mapper (layering: src must not depend on scripts).
The driver parses nodes via scripts.menu_mapper and passes node dicts +
denylist booleans into build_element().
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1
TOOL_VERSION = "menu-tree-baseline-v1"

_TOGGLE_CLASSES = {
    "android.widget.Switch", "android.widget.CheckBox", "android.widget.RadioButton",
}
_INPUT_CLASSES = {"android.widget.EditText", "android.widget.AutoCompleteTextView"}


def detect_script(text: str) -> str:
    """Bucket a label by dominant script: 'ko' (Hangul) > 'en' (Latin) > 'other'."""
    for c in text:
        if "가" <= c <= "힣" or "ᄀ" <= c <= "ᇿ":
            return "ko"
    has_latin = any("a" <= c.lower() <= "z" for c in text)
    has_cjk_or_kana = any(ord(c) >= 0x3000 for c in text)
    if has_latin and not has_cjk_or_kana:
        return "en"
    return "other"


def classify_kind(node: dict) -> str:
    cls = node.get("class", "")
    if node.get("checkable") == "true" or cls in _TOGGLE_CLASSES:
        return "toggle"
    if cls in _INPUT_CLASSES:
        return "input"
    if cls == "android.widget.Button":
        return "button"
    clickable = node.get("clickable") == "true" or node.get("inherited_clickable") == "true"
    focusable = node.get("focusable") == "true" or node.get("inherited_focusable") == "true"
    label = node.get("text") or node.get("content-desc") or ""
    if clickable or focusable:
        return "menu_row"
    if label:
        return "title"
    return "unknown"


def text_role_hint(node: dict) -> str:
    rid = node.get("resource-id", "") or ""
    if rid.endswith("/title") or rid.endswith(":id/title"):
        return "primary"
    if "summary" in rid:
        return "summary"
    return "unknown"


@dataclass
class MenuElement:
    label: str
    resource_id: str | None
    kind: str
    source_class: str
    text_role_hint: str
    clickable: bool
    focusable: bool
    checkable: bool
    risk: str
    bounds: str | None = None


def build_element(node: dict, denylisted: bool) -> MenuElement:
    label = node.get("text") or node.get("content-desc") or ""
    kind = classify_kind(node)
    cls = node.get("class", "")
    checkable = node.get("checkable") == "true"
    if denylisted:
        risk = "denylist"
    elif cls in _TOGGLE_CLASSES:
        risk = "toggle"
    elif checkable:
        risk = "checkable"
    else:
        risk = "none"
    return MenuElement(
        label=label,
        resource_id=(node.get("resource-id") or None),
        kind=kind,
        source_class=cls,
        text_role_hint=text_role_hint(node),
        clickable=node.get("clickable") == "true",
        focusable=node.get("focusable") == "true",
        checkable=checkable,
        risk=risk,
        bounds=(node.get("bounds") or None),
    )


def bucket_texts(elements: list[MenuElement]) -> dict:
    buckets: dict[str, set] = {"ko": set(), "en": set(), "other": set()}
    for e in elements:
        if not e.label:
            continue
        buckets[detect_script(e.label)].add(e.label)
    return {k: sorted(v) for k, v in buckets.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 2 done — menu_tree classifiers GREEN." No commit.

---

## Task 3: src/menu_tree.py — dataclasses + JSON/MD emitters (TDD)

**Files:**
- Modify: `src/menu_tree.py`
- Test: `tests/test_menu_tree.py` (append)

- [ ] **Step 1: Write the failing emitter tests (append to tests/test_menu_tree.py)**

```python
def _screen(screen_id="settings_d1_privacy"):
    els = [mt.build_element(_node(text="개인 정보 보호", clickable="true", focusable="true"), denylisted=False)]
    return mt.MenuScreen(
        screen_id=screen_id, label_ko="개인 정보 보호", nav_path=["설정", "개인 정보 보호"],
        entry={"method": "deeplink", "action": "android.settings.PRIVACY_SETTINGS",
               "component": None, "launched_cmd": "am start -a android.settings.PRIVACY_SETTINGS"},
        reach_status="REACHED", reach_kind="internal",
        observed_focus="com.android.settings/.Settings$PrivacyDashboardActivity",
        expect_activity_regex="PrivacyDashboardActivity", activity_match=True,
        fingerprint="abcd1234", observed_texts=mt.bucket_texts(els), elements=els,
        scroll=mt.ScrollInfo(passes=1, swipes=[{"dir": "up", "x1": 240, "y1": 600, "x2": 240, "y2": 200}],
                             new_texts_per_pass=[0], terminated="no_new"),
        dump_info=mt.DumpInfo(dump_error=None, dump_size=2048, raw_present=True),
        risk_flags=[], raw_dump_ref="catalog/raw/20260602T000000Z/settings_d1_privacy.xml",
    )


def _baseline(screens=None):
    dev = mt.DeviceBaseline(
        serial="B06201249E0002B8", model="AT-M140", product="alt_thor2", device="thor2",
        build_fingerprint="ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys",
        build_id="RY07260302M", android="14", locale_persist="ko-KR", locale_product="en-US",
        viewport="480x800", dpi="220", sim="SKT")
    return mt.MenuTreeBaseline(
        schema_version=mt.SCHEMA_VERSION, tool_version=mt.TOOL_VERSION,
        generated_at_utc="2026-06-02T00:00:00Z", run_id="20260602T000000Z",
        device=dev, package="com.android.settings",
        seed_ref={"source_menu_tree": "THOR2_K - Settings/MENU_TREE.md", "seed_version": 1,
                  "seed_path": "THOR2_K - Settings/menu_tree_seed.yaml"},
        target_mismatch_ack=False, summary=mt.compute_summary(screens or [_screen()]),
        screens=screens or [_screen()])


def test_compute_summary_counts_reach_kind_external_independent_of_status():
    s_int = _screen("a"); s_int.reach_kind = "internal"; s_int.reach_status = "REACHED"
    s_ext = _screen("b"); s_ext.reach_kind = "external"; s_ext.reach_status = "DUMP_REJECTED"
    summ = mt.compute_summary([s_int, s_ext])
    assert summ["screen_count"] == 2
    assert summ["reached_external"] == 1   # counted by reach_kind, not status
    assert summ["dump_rejected"] == 1


def test_to_json_is_deterministic_with_fixed_clock():
    b1 = _baseline(); b2 = _baseline()
    assert b1.to_json() == b2.to_json()   # byte-identical with fixed run_id/clock


def test_to_json_roundtrip_schema_fields():
    import json
    d = json.loads(_baseline().to_json())
    assert d["schema_version"] == 1
    assert d["screens"][0]["reach_kind"] == "internal"
    assert d["screens"][0]["elements"][0]["kind"] == "menu_row"
    assert d["device"]["serial"] == "B06201249E0002B8"


def test_dump_rejected_screen_nullable_fields():
    s = _screen("dr")
    s.reach_status = "DUMP_REJECTED"; s.fingerprint = None; s.elements = []
    s.observed_texts = mt.bucket_texts([]); s.raw_dump_ref = None
    s.dump_info = mt.DumpInfo(dump_error="null root", dump_size=0, raw_present=False)
    import json
    d = json.loads(mt.MenuTreeBaseline.__dict__  # sanity: dataclass usable
                   and _baseline([s]).to_json())
    sc = d["screens"][0]
    assert sc["fingerprint"] is None and sc["raw_dump_ref"] is None and sc["elements"] == []


def test_to_md_renders_screen_and_summary():
    md = _baseline().to_md()
    assert "# Settings Menu Tree Baseline" in md
    assert "개인 정보 보호" in md
    assert "settings_d1_privacy" in md
    assert "B06201249E0002B8" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py -k "summary or json or md or nullable" -v`
Expected: FAIL — `AttributeError: module 'src.menu_tree' has no attribute 'MenuScreen'`.

- [ ] **Step 3: Implement dataclasses + summary + emitters (append to src/menu_tree.py)**

```python
import json


@dataclass
class ScrollInfo:
    passes: int = 0
    swipes: list[dict] = field(default_factory=list)
    new_texts_per_pass: list[int] = field(default_factory=list)
    terminated: str = "no_new"


@dataclass
class DumpInfo:
    dump_error: str | None = None
    dump_size: int = 0
    raw_present: bool = False


@dataclass
class MenuScreen:
    screen_id: str
    label_ko: str
    nav_path: list[str]
    entry: dict
    reach_status: str
    reach_kind: str | None
    observed_focus: str
    expect_activity_regex: str
    activity_match: bool
    fingerprint: str | None
    observed_texts: dict
    elements: list[MenuElement]
    scroll: ScrollInfo
    dump_info: DumpInfo
    risk_flags: list[str]
    raw_dump_ref: str | None


@dataclass
class DeviceBaseline:
    serial: str
    model: str
    product: str
    device: str
    build_fingerprint: str
    build_id: str
    android: str
    locale_persist: str
    locale_product: str
    viewport: str
    dpi: str
    sim: str


_REACH_STATUSES = (
    "REACHED", "REACHED_EXTERNAL_PACKAGE", "UNREACHABLE_NO_ACTION",
    "LAUNCH_FAILED", "FOCUS_MISMATCH", "DUMP_REJECTED",
)


def compute_summary(screens: list[MenuScreen]) -> dict:
    status_count = {s: 0 for s in _REACH_STATUSES}
    for sc in screens:
        status_count[sc.reach_status] = status_count.get(sc.reach_status, 0) + 1
    return {
        "screen_count": len(screens),
        "reached": status_count["REACHED"],
        "reached_external": sum(1 for sc in screens if sc.reach_kind == "external"),
        "unreachable": status_count["UNREACHABLE_NO_ACTION"],
        "launch_failed": status_count["LAUNCH_FAILED"],
        "focus_mismatch": status_count["FOCUS_MISMATCH"],
        "dump_rejected": status_count["DUMP_REJECTED"],
        "denylist_recorded": sum(len(sc.risk_flags) for sc in screens),
        "observed_texts_total": sum(
            len(v) for sc in screens for v in sc.observed_texts.values()),
        "scroll_passes_total": sum(sc.scroll.passes for sc in screens),
    }


def _element_dict(e: MenuElement) -> dict:
    return {
        "label": e.label, "resource_id": e.resource_id, "kind": e.kind,
        "source_class": e.source_class, "text_role_hint": e.text_role_hint,
        "clickable": e.clickable, "focusable": e.focusable, "checkable": e.checkable,
        "risk": e.risk, "bounds": e.bounds,
    }


def _screen_dict(sc: MenuScreen) -> dict:
    return {
        "screen_id": sc.screen_id, "label_ko": sc.label_ko, "nav_path": sc.nav_path,
        "entry": sc.entry, "reach_status": sc.reach_status, "reach_kind": sc.reach_kind,
        "observed_focus": sc.observed_focus, "expect_activity_regex": sc.expect_activity_regex,
        "activity_match": sc.activity_match, "fingerprint": sc.fingerprint,
        "observed_texts": sc.observed_texts,
        "elements": [_element_dict(e) for e in sc.elements],
        "scroll": {"passes": sc.scroll.passes, "swipes": sc.scroll.swipes,
                   "new_texts_per_pass": sc.scroll.new_texts_per_pass,
                   "terminated": sc.scroll.terminated},
        "dump_info": {"dump_error": sc.dump_info.dump_error, "dump_size": sc.dump_info.dump_size,
                      "raw_present": sc.dump_info.raw_present},
        "risk_flags": sc.risk_flags, "raw_dump_ref": sc.raw_dump_ref,
    }


@dataclass
class MenuTreeBaseline:
    schema_version: int
    tool_version: str
    generated_at_utc: str
    run_id: str
    device: DeviceBaseline
    package: str
    seed_ref: dict
    target_mismatch_ack: bool
    summary: dict
    screens: list[MenuScreen]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "tool_version": self.tool_version,
            "generated_at_utc": self.generated_at_utc, "run_id": self.run_id,
            "device": self.device.__dict__, "package": self.package,
            "seed_ref": self.seed_ref, "target_mismatch_ack": self.target_mismatch_ack,
            "summary": self.summary, "screens": [_screen_dict(s) for s in self.screens],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    def to_md(self) -> str:
        d = self.device
        lines = [
            "# Settings Menu Tree Baseline",
            "",
            f"- run_id: `{self.run_id}` · generated_at_utc: `{self.generated_at_utc}`",
            f"- device: {d.model} `{d.serial}` · build `{d.build_id}` · {d.locale_persist}"
            f" · {d.viewport}@{d.dpi} · SIM {d.sim}",
            f"- package: `{self.package}` · schema v{self.schema_version} ({self.tool_version})",
            "",
            "## Summary",
            "```yaml",
        ]
        for k, v in self.summary.items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("")
        for sc in self.screens:
            lines.append(f"## {sc.label_ko}  (`{sc.screen_id}`)")
            lines.append(f"- nav_path: {' → '.join(sc.nav_path)}")
            lines.append(f"- reach: `{sc.reach_status}` (kind={sc.reach_kind}) · "
                         f"focus `{sc.observed_focus}` · fp `{sc.fingerprint}`")
            counts = ", ".join(f"{k}={len(v)}" for k, v in sc.observed_texts.items())
            lines.append(f"- observed_texts: {counts} · scroll {sc.scroll.passes} pass "
                         f"({sc.scroll.terminated})")
            if sc.risk_flags:
                lines.append(f"- risk_flags (record-only): {', '.join(sc.risk_flags)}")
            lines.append("")
            lines.append("| label | kind | role | risk |")
            lines.append("|---|---|---|---|")
            for e in sc.elements:
                lines.append(f"| {e.label} | {e.kind} | {e.text_role_hint} | {e.risk} |")
            lines.append("")
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py -v`
Expected: PASS (all menu_tree tests).

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 3 done — schema + JSON/MD emitters + determinism GREEN." No commit.

---

## Task 4: Test fixtures — copy 3 real uiautomator dumps

**Files:**
- Create: `tests/fixtures/menu_tree/settings_root.xml`, `settings_d1_privacy.xml`, `settings_d1_location.xml`

- [ ] **Step 1: Copy real dumps from THOR2_K catalog into fixtures (stable copies)**

Run (bash):

```bash
cd "c:/Users/momen/Projects/tc-runner"
mkdir -p tests/fixtures/menu_tree
cp "THOR2_K - Settings/catalog/_raw_settings_root.xml"  tests/fixtures/menu_tree/settings_root.xml
cp "THOR2_K - Settings/catalog/_raw_d1_privacy.xml"     tests/fixtures/menu_tree/settings_d1_privacy.xml
cp "THOR2_K - Settings/catalog/_raw_d1_location.xml"    tests/fixtures/menu_tree/settings_d1_location.xml
```

- [ ] **Step 2: Write a fixture-driven parse test (append to tests/test_menu_tree.py)**

```python
import importlib.util as _ilu
from pathlib import Path as _P

_ROOT = _P(__file__).resolve().parent.parent
_FX = _ROOT / "tests" / "fixtures" / "menu_tree"
_mm_spec = _ilu.spec_from_file_location("menu_mapper", _ROOT / "scripts" / "menu_mapper.py")
_mm = _ilu.module_from_spec(_mm_spec); _mm_spec.loader.exec_module(_mm)


def test_real_dump_parses_into_elements_and_buckets():
    xml = (_FX / "settings_d1_privacy.xml").read_text(encoding="utf-8")
    nodes = _mm.extract_nodes(xml)
    els = [mt.build_element(n, denylisted=_mm.is_node_safe(n)[1].startswith("denylist"))
           for n in nodes if (n.get("text") or n.get("content-desc"))]
    buckets = mt.bucket_texts(els)
    assert els, "expected non-empty elements from real privacy dump"
    assert any(buckets.values()), "expected at least one bucketed text"
    assert all(e.kind in {"title", "menu_row", "button", "toggle", "input", "unknown"} for e in els)
```

- [ ] **Step 3: Run the fixture test**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py::test_real_dump_parses_into_elements_and_buckets -v`
Expected: PASS.

- [ ] **Step 4: Checkpoint — DO NOT COMMIT**

Record: "Task 4 done — 3 real fixtures wired, real-dump parse GREEN." No commit.

---

## Task 5: Seed YAML + catalog_schema Tier D

**Files:**
- Create: `THOR2_K - Settings/menu_tree_seed.yaml`
- Modify: `THOR2_K - Settings/catalog_schema.md`

- [ ] **Step 1: Author the curated seed from MENU_TREE.md**

Create `THOR2_K - Settings/menu_tree_seed.yaml` (screens = depth0 home + depth1 + deep-link batch #2; entries copied from `MENU_TREE.md` activities/actions). Authoritative subset (extend as MENU_TREE.md grows):

```yaml
seed_version: 1
locale: ko-KR
target_serial: "B06201249E0002B8"
target_serial_label: "THOR2_K (AT-M140)"
source_menu_tree: "THOR2_K - Settings/MENU_TREE.md"
package: com.android.settings
screens:
  - id: settings_home
    label_ko: "설정 home"
    nav_path: ["설정"]
    entry: { action: "android.settings.SETTINGS" }
    expect_activity_regex: "(Settings|SettingsHomepageActivity)$"
  - id: settings_d1_privacy
    label_ko: "개인 정보 보호"
    nav_path: ["설정", "개인 정보 보호"]
    entry: { action: "android.settings.PRIVACY_SETTINGS" }
    expect_activity_regex: "PrivacyDashboardActivity"
  - id: settings_d1_location
    label_ko: "위치"
    nav_path: ["설정", "위치"]
    entry: { action: "android.settings.LOCATION_SOURCE_SETTINGS" }
    expect_activity_regex: "LocationSettingsActivity"
  - id: settings_d1_google
    label_ko: "Google"
    nav_path: ["설정", "Google"]
    entry: { component: "com.android.settings/.Settings$AccountDashboardActivity" }
    expect_activity_regex: "AccountDashboardActivity"
  - id: settings_d1_device_info
    label_ko: "휴대전화 정보"
    nav_path: ["설정", "휴대전화 정보"]
    entry: { component: "com.android.settings/.Settings$MyDeviceInfoActivity" }
    expect_activity_regex: "MyDeviceInfoActivity"
  - id: settings_d1_wifi
    label_ko: "Wi-Fi / 네트워크"
    nav_path: ["설정", "Wi-Fi"]
    entry: { action: "android.settings.WIFI_SETTINGS" }
    expect_activity_regex: "WifiSettingsActivity"
  - id: settings_d1_bluetooth
    label_ko: "연결된 기기"
    nav_path: ["설정", "연결된 기기"]
    entry: { action: "android.settings.BLUETOOTH_SETTINGS" }
    expect_activity_regex: "ConnectedDeviceDashboardActivity"
  - id: settings_d1_data_usage
    label_ko: "데이터 사용"
    nav_path: ["설정", "데이터 사용"]
    entry: { action: "android.settings.DATA_USAGE_SETTINGS" }
    expect_activity_regex: "DataUsageSummaryActivity"
  - id: settings_d1_sound
    label_ko: "소리·진동"
    nav_path: ["설정", "소리 및 진동"]
    entry: { action: "android.settings.SOUND_SETTINGS" }
    expect_activity_regex: "SoundSettingsActivity"
  - id: settings_d1_display
    label_ko: "디스플레이"
    nav_path: ["설정", "디스플레이"]
    entry: { action: "android.settings.DISPLAY_SETTINGS" }
    expect_activity_regex: "DisplaySettingsActivity"
  - id: settings_d1_accessibility
    label_ko: "접근성"
    nav_path: ["설정", "접근성"]
    entry: { action: "android.settings.ACCESSIBILITY_SETTINGS" }
    expect_activity_regex: "AccessibilitySettings"
  - id: settings_d1_date
    label_ko: "날짜·시간"
    nav_path: ["설정", "날짜 및 시간"]
    entry: { action: "android.settings.DATE_SETTINGS" }
    expect_activity_regex: "DateTimeSettingsActivity"
  - id: settings_d1_apps
    label_ko: "앱"
    nav_path: ["설정", "앱"]
    entry: { action: "android.settings.APPLICATION_SETTINGS" }
    expect_activity_regex: "ManageApplicationsActivity"
  - id: settings_d1_usage_access
    label_ko: "사용 정보 접근"
    nav_path: ["설정", "사용 정보 접근"]
    entry: { action: "android.settings.USAGE_ACCESS_SETTINGS" }
    expect_activity_regex: "UsageAccessSettingsActivity"
  - id: settings_d1_dream
    label_ko: "화면 보호기"
    nav_path: ["설정", "화면 보호기"]
    entry: { action: "android.settings.DREAM_SETTINGS" }
    expect_activity_regex: "DreamSettingsActivity"
  - id: settings_d1_home_launcher
    label_ko: "기본 앱 / 런처"
    nav_path: ["설정", "기본 앱"]
    entry: { action: "android.settings.HOME_SETTINGS" }
    expect_activity_regex: "DefaultAppActivity"
  - id: settings_d1_wellbeing
    label_ko: "디지털 웰빙 및 자녀 보호 기능"
    nav_path: ["설정", "디지털 웰빙"]
    entry: { component: "com.google.android.apps.wellbeing/.settings.SettingsActivity" }
    expect_activity_regex: "wellbeing"
```

> Note: `STORAGE_SETTINGS` / `NOTIFICATION_LISTENER_SETTINGS` / `NETWORK_OPERATOR_SETTINGS` / `DuraSpeed` are intentionally omitted (MENU_TREE.md marks them action-missing / dump-rejected). They become coverage-gap candidates for v1.1.

- [ ] **Step 2: Add Tier D to catalog_schema.md**

In `THOR2_K - Settings/catalog_schema.md`, append (or insert near the Tier A/B/C definitions) the exact paragraph:

```markdown
### Tier D — device-sourced machine baseline

Tier A/B/C는 hand-written catalog 정본이다. Tier D는 device-sourced machine
baseline으로, tool-generated append-only artifact이며 hand-written catalog와
구분한다. Tier D는 TC 합성·drift 분석의 입력 source로 사용할 수 있지만, 사람이
해석한 catalog 정본을 대체하지 않는다.

- 생성: `scripts/settings_tree_explorer.py` (read-only deep-link enumeration)
- 산출: `catalog/menu_tree_baseline_<run_id>.json` + `.md`, raw = `catalog/raw/<run_id>/<screen_id>.xml`
- schema: `src/menu_tree.py` (schema_version=1, tool_version="menu-tree-baseline-v1")
```

- [ ] **Step 3: Validate seed parses**

Run: `venv/Scripts/python.exe -c "import yaml,io; d=yaml.safe_load(open('THOR2_K - Settings/menu_tree_seed.yaml',encoding='utf-8')); print(len(d['screens']),'screens', d['seed_version'], d['target_serial'])"`
Expected: prints `17 screens 1 B06201249E0002B8` (no exception).

- [ ] **Step 4: Checkpoint — DO NOT COMMIT**

Record: "Task 5 done — seed (17 screens) + Tier D added; seed parses." No commit.

---

## Task 6: Driver — GuardedADB (read-only command allowlist) (TDD)

**Files:**
- Create: `scripts/settings_tree_explorer.py`
- Test: `tests/test_settings_tree_explorer.py`

- [ ] **Step 1: Write the failing GuardedADB tests**

Create `tests/test_settings_tree_explorer.py`:

```python
"""Tests for scripts/settings_tree_explorer.py (stub-ADB, offline)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "scripts" / "settings_tree_explorer.py"
_spec = importlib.util.spec_from_file_location("settings_tree_explorer", _PATH)
ste = importlib.util.module_from_spec(_spec)
sys.modules["settings_tree_explorer"] = ste
_spec.loader.exec_module(ste)


class StubADB:
    """Records every shell/op; returns scripted focus + dump per call."""
    def __init__(self, focus_seq=None, dump_seq=None, props=None):
        self.calls: list[str] = []
        self._focus_seq = list(focus_seq or [])
        self._dump_seq = list(dump_seq or [])
        self._props = props or {}
    def shell(self, command: str, timeout: int = 10) -> str:
        self.calls.append(command)
        if command.startswith("dumpsys window"):
            return self._focus_seq.pop(0) if self._focus_seq else ""
        if command.startswith("cat "):                       # GuardedADB.dump reads via cat
            return self._dump_seq.pop(0) if self._dump_seq else ""
        if command.startswith("getprop"):
            key = command.split(" ", 1)[1].strip()
            return self._props.get(key, "")
        return ""
    def swipe(self, x1, y1, x2, y2, duration=300):
        self.calls.append(f"input swipe {x1} {y1} {x2} {y2} {duration}")
    def key(self, keycode: str):
        self.calls.append(f"input keyevent {keycode}")
    def device_serial(self):
        return self._props.get("__serial__")


def test_guarded_adb_blocks_tap_and_forbidden_keys():
    g = ste.GuardedADB(StubADB())
    with pytest.raises(ste.CommandNotAllowed):
        g.raw_shell("input tap 100 200")
    with pytest.raises(ste.CommandNotAllowed):
        g.key("KEYCODE_POWER")
    with pytest.raises(ste.CommandNotAllowed):
        g.key("KEYCODE_ENTER")


def test_guarded_adb_allows_readonly_ops_and_logs_them():
    stub = StubADB(focus_seq=["mCurrentFocus=Window{x u0 com.android.settings/com.android.settings.Settings}"])
    g = ste.GuardedADB(stub)
    g.launch_action("android.settings.WIFI_SETTINGS")
    g.scroll_up(240, 600, 240, 200)
    g.home()
    g.current_focus()
    # Every recorded command must match the read-only allowlist.
    assert all(ste.is_allowed_command(c) for c in g.command_log)
    assert g.violations == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k guarded -v`
Expected: FAIL — `AttributeError: module 'settings_tree_explorer' has no attribute 'GuardedADB'`.

- [ ] **Step 3: Implement module skeleton + GuardedADB**

Create `scripts/settings_tree_explorer.py`:

```python
"""Device Settings menu-tree baseline explorer (v1, read-only deep-link enum).

Driver/orchestration only. Imports src.menu_tree (pure schema) and
scripts.menu_mapper (parsers). All ADB access routes through GuardedADB,
which enforces a read-only command allowlist (no semantic taps / no
POWER/ENTER/DPAD_CENTER).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, ".."))   # repo root -> enables `from src...`
sys.path.append(_HERE)                        # scripts/ -> enables `import menu_mapper`
from src import menu_tree as mt          # noqa: E402
import menu_mapper as mm                 # same dir (scripts/)  # noqa: E402
from src.adb import ADB                  # noqa: E402

# --- read-only command allowlist ------------------------------------------
_ALLOWED_PATTERNS = [
    re.compile(r"^am start (-a [\w\.]+|-n [\w\./\$]+)$"),
    re.compile(r"^input swipe \d+ \d+ \d+ \d+( \d+)?$"),
    re.compile(r"^input keyevent KEYCODE_HOME$"),
    re.compile(r"^uiautomator dump /sdcard/[\w\.]+$"),
    re.compile(r"^cat /sdcard/[\w\.]+$"),
    re.compile(r"^rm -f /sdcard/[\w\.]+$"),
    re.compile(r"^dumpsys window$"),
    re.compile(r"^getprop [\w\.]+$"),
    re.compile(r"^wm (size|density)$"),
]
# NOTE: `am force-stop` is intentionally NOT in the generic allowlist — it is an
# opt-in stuck-recovery op gated solely inside force_stop_settings() (no bypass
# via raw_shell).


def is_allowed_command(command: str) -> bool:
    return any(p.match(command.strip()) for p in _ALLOWED_PATTERNS)


class CommandNotAllowed(RuntimeError):
    pass


class GuardedADB:
    """Narrow read-only facade over src.adb.ADB. Logs + validates every op."""

    def __init__(self, adb, allow_force_stop: bool = False):
        self._adb = adb
        self._allow_force_stop = allow_force_stop
        self.command_log: list[str] = []
        self.violations = 0

    def _guard(self, command: str) -> None:
        self.command_log.append(command)
        if not is_allowed_command(command):
            self.violations += 1
            raise CommandNotAllowed(command)

    def raw_shell(self, command: str) -> str:
        self._guard(command)
        return self._adb.shell(command)

    def launch_action(self, action: str) -> str:
        return self.raw_shell(f"am start -a {action}")

    def launch_component(self, comp: str) -> str:
        return self.raw_shell(f"am start -n {comp}")

    def scroll_up(self, x1, y1, x2, y2, duration=300):
        self._guard(f"input swipe {x1} {y1} {x2} {y2} {duration}")
        self._adb.swipe(x1, y1, x2, y2, duration)

    def home(self):
        self.key("KEYCODE_HOME")

    def key(self, keycode: str):
        self._guard(f"input keyevent {keycode}")
        self._adb.key(keycode)

    def force_stop_settings(self):
        # Opt-in only; bypasses the generic allowlist by design (flag-gated + logged).
        if not self._allow_force_stop:
            raise CommandNotAllowed("am force-stop com.android.settings (not enabled)")
        cmd = "am force-stop com.android.settings"
        self.command_log.append(cmd)
        self._adb.shell(cmd)

    def dump(self) -> str:
        # Implement the full temp-path flow HERE so every adb shell call is guarded.
        # (ADB.dump_ui would issue uiautomator/cat/rm outside the gate.)
        remote = "/sdcard/ui_dump.xml"
        self.raw_shell(f"uiautomator dump {remote}")
        xml = self.raw_shell(f"cat {remote}")
        self.raw_shell(f"rm -f {remote}")
        return xml

    def getprop(self, name: str) -> str:
        return self.raw_shell(f"getprop {name}").strip()

    def current_focus(self) -> str:
        out = self.raw_shell("dumpsys window")
        m = re.search(r"mCurrentFocus=\S+ u0 ([\w\.]+)/([\w\.\$]+)", out)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
        m = re.search(r" ([\w\.]+)/([\w\.\$]+)\}", out)
        return f"{m.group(1)}/{m.group(2)}" if m else "unknown/unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k guarded -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 6 done — GuardedADB read-only allowlist GREEN." No commit.

---

## Task 7: Driver — per-screen reach classification + dump/parse (TDD)

**Files:**
- Modify: `scripts/settings_tree_explorer.py`
- Test: `tests/test_settings_tree_explorer.py` (append)

- [ ] **Step 1: Write the failing reach/explore-screen tests**

```python
_WIFI_FOCUS = "mCurrentFocus=Window{a u0 com.android.settings/com.android.settings.Settings$WifiSettingsActivity}"
_EXT_FOCUS = "mCurrentFocus=Window{a u0 com.google.android.apps.wellbeing/.settings.SettingsActivity}"
_HOME_FOCUS = "mCurrentFocus=Window{a u0 com.hnlens.simplemode/.ui.home.MainActivity}"
_DUMP = """<?xml version='1.0'?><hierarchy><node class="android.widget.TextView" text="Wi-Fi"
 resource-id="android:id/title" clickable="true" focusable="true" checkable="false" bounds="[0,0][480,80]"/></hierarchy>"""


def _seed_screen(**over):
    base = {"id": "settings_d1_wifi", "label_ko": "Wi-Fi", "nav_path": ["설정", "Wi-Fi"],
            "entry": {"action": "android.settings.WIFI_SETTINGS"},
            "expect_activity_regex": "WifiSettingsActivity"}
    base.update(over)
    return base


def test_explore_screen_reached_internal():
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "REACHED" and sc.reach_kind == "internal"
    assert sc.activity_match is True and sc.fingerprint
    assert "Wi-Fi" in sc.observed_texts["en"]


def test_explore_screen_external_package_is_not_failure():
    g = ste.GuardedADB(StubADB(focus_seq=[_EXT_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(id="settings_d1_wellbeing",
        entry={"component": "com.google.android.apps.wellbeing/.settings.SettingsActivity"},
        expect_activity_regex="wellbeing"), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "REACHED_EXTERNAL_PACKAGE" and sc.reach_kind == "external"


def test_explore_screen_focus_mismatch():
    g = ste.GuardedADB(StubADB(focus_seq=[_HOME_FOCUS], dump_seq=[_DUMP]))
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "FOCUS_MISMATCH" and sc.reach_kind is None


def test_explore_screen_unreachable_no_action():
    g = ste.GuardedADB(StubADB())
    sc = ste.explore_screen(g, _seed_screen(entry={}), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "UNREACHABLE_NO_ACTION"


def test_explore_screen_dump_rejected_nullable():
    g = ste.GuardedADB(StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[""]))  # empty dump
    sc = ste.explore_screen(g, _seed_screen(), run_id="R", max_passes=1, settle=0)
    assert sc.reach_status == "DUMP_REJECTED" and sc.reach_kind == "internal"
    assert sc.fingerprint is None and sc.elements == [] and sc.raw_dump_ref is None
    assert sc.dump_info.raw_present is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k explore_screen -v`
Expected: FAIL — `AttributeError: ... has no attribute 'explore_screen'`.

- [ ] **Step 3: Implement reach + explore_screen (append to settings_tree_explorer.py)**

```python
_SETTINGS_PKG = "com.android.settings"
_VIEWPORT = (480, 800)  # THOR2_K; swipe geometry source


def _launch(g: GuardedADB, entry: dict) -> tuple[str | None, str | None]:
    """Returns (launched_cmd, None) or (None, 'NO_ACTION')."""
    if entry.get("action"):
        cmd = f"am start -a {entry['action']}"
        g.launch_action(entry["action"])
        return cmd, None
    if entry.get("component"):
        cmd = f"am start -n {entry['component']}"
        g.launch_component(entry["component"])
        return cmd, None
    return None, "NO_ACTION"


def _classify_reach(focus: str, expect_regex: str) -> tuple[str, str | None, bool]:
    """Returns (reach_status, reach_kind, activity_match)."""
    pkg = focus.split("/")[0] if "/" in focus else focus
    activity_match = bool(re.search(expect_regex, focus))
    if pkg == _SETTINGS_PKG:
        if activity_match:
            return "REACHED", "internal", True
        return "FOCUS_MISMATCH", None, False
    if pkg in mm.ALLOWLIST_PACKAGES and pkg != _SETTINGS_PKG:
        return ("REACHED_EXTERNAL_PACKAGE", "external", activity_match) if activity_match \
            else ("REACHED_EXTERNAL_PACKAGE", "external", False)
    return "FOCUS_MISMATCH", None, activity_match


def _elements_from_xml(xml: str) -> list[mt.MenuElement]:
    nodes = mm.extract_nodes(xml)
    els = []
    for n in nodes:
        if not (n.get("text") or n.get("content-desc")):
            continue
        denylisted = is_denylisted(n)
        els.append(mt.build_element(n, denylisted))
    return els


def is_denylisted(node: dict) -> bool:
    label = (node.get("text") or node.get("content-desc") or "").lower()
    return any(d.lower() in label for d in mm.DENYLIST)


def explore_screen(g: GuardedADB, seed: dict, run_id: str,
                   max_passes: int = 8, settle: float = 1.2, raw_writer=None) -> mt.MenuScreen:
    entry = dict(seed.get("entry") or {})
    nav_path = seed.get("nav_path", [])
    label_ko = seed.get("label_ko", "")
    screen_id = seed["id"]
    expect_regex = seed.get("expect_activity_regex", "")

    launched_cmd, no_action = _launch(g, entry)
    entry_rec = {"method": "deeplink", "action": entry.get("action"),
                 "component": entry.get("component"), "launched_cmd": launched_cmd}
    empty_scroll = mt.ScrollInfo()
    if no_action == "NO_ACTION":
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "UNREACHABLE_NO_ACTION", None, "unknown/unknown", expect_regex, False,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="no_launch", dump_size=0, raw_present=False), [], None)

    if settle:
        time.sleep(settle)
    focus = g.current_focus()
    if focus in ("unknown/unknown", ""):
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "LAUNCH_FAILED", None, focus or "unknown/unknown", expect_regex, False,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="no_focus", dump_size=0, raw_present=False), [], None)

    reach_status, reach_kind, activity_match = _classify_reach(focus, expect_regex)
    if reach_status == "FOCUS_MISMATCH":
        g.home()  # HOME-only recovery
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            reach_status, reach_kind, focus, expect_regex, activity_match,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error=None, dump_size=0, raw_present=False), [], None)

    xml = g.dump()
    dump_size = len(xml)
    if not xml or "<node" not in xml:
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "DUMP_REJECTED", reach_kind, focus, expect_regex, activity_match,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="empty_or_no_nodes", dump_size=dump_size, raw_present=False),
            [], None)

    els = _elements_from_xml(xml)
    scroll, els = _scroll_sweep(g, els, max_passes)  # Task 8
    fingerprint = mm.generate_fingerprint(focus, mm.extract_nodes(xml))
    risk_flags = sorted({e.label for e in els if e.risk == "denylist"})
    raw_ref = f"catalog/raw/{run_id}/{screen_id}.xml"
    if raw_writer:
        raw_writer(screen_id, xml)
    g.home()  # HOME-only recovery before next screen
    return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
        reach_status, reach_kind, focus, expect_regex, activity_match,
        fingerprint, mt.bucket_texts(els), els, scroll,
        mt.DumpInfo(dump_error=None, dump_size=dump_size, raw_present=True),
        risk_flags, raw_ref)
```

> All `explore_screen` paths return a single `mt.MenuScreen`; raw XML is persisted via the `raw_writer(screen_id, xml)` callback (driver supplies it in Task 9). Early-return paths (no-action / launch-failed / focus-mismatch / dump-rejected) set `fingerprint=None`, `elements=[]`, `raw_dump_ref=None`.

- [ ] **Step 4: Run reach tests to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k explore_screen -v`
Expected: PASS (5 passed). (`_scroll_sweep` is implemented in Task 8; add a temporary stub `def _scroll_sweep(g, els, max_passes): return mt.ScrollInfo(passes=0, terminated="no_new"), els` to make Task 7 green, replaced in Task 8.)

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 7 done — reach classification + dump/parse GREEN (scroll stubbed)." No commit.

---

## Task 8: Driver — read-only scroll sweep (TDD)

**Files:**
- Modify: `scripts/settings_tree_explorer.py` (replace `_scroll_sweep` stub)
- Test: `tests/test_settings_tree_explorer.py` (append)

- [ ] **Step 1: Write the failing scroll tests**

```python
def _dump_with(texts):
    nodes = "".join(
        f'<node class="android.widget.TextView" text="{t}" resource-id="android:id/title"'
        f' clickable="true" focusable="true" checkable="false" bounds="[0,0][480,80]"/>' for t in texts)
    return f"<?xml version='1.0'?><hierarchy>{nodes}</hierarchy>"


def test_scroll_terminates_on_no_new():
    # pass1 reveals A,B; pass2 reveals nothing new -> terminate no_new at 1 sweep
    stub = StubADB(dump_seq=[_dump_with(["A", "B"])])  # subsequent dumps identical
    stub._dump_seq = [_dump_with(["A", "B"])]
    g = ste.GuardedADB(stub)
    seed_els = ste._elements_from_xml(_dump_with(["A", "B"]))
    scroll, merged = ste._scroll_sweep(g, list(seed_els), max_passes=8)
    assert scroll.terminated == "no_new"
    assert scroll.passes >= 1
    assert {e.label for e in merged} == {"A", "B"}


def test_scroll_merges_new_then_stops():
    stub = StubADB(dump_seq=[_dump_with(["A", "B", "C"]), _dump_with(["A", "B", "C"])])
    g = ste.GuardedADB(stub)
    seed_els = ste._elements_from_xml(_dump_with(["A", "B"]))
    scroll, merged = ste._scroll_sweep(g, list(seed_els), max_passes=8)
    assert "C" in {e.label for e in merged}
    assert scroll.new_texts_per_pass[0] == 1  # added C on first sweep
    assert any(s["dir"] == "up" for s in scroll.swipes)


def test_scroll_respects_max_passes():
    # every sweep yields a brand-new label -> never converges -> stop at max_passes
    seq = [_dump_with([f"L{i}"]) for i in range(20)]
    g = ste.GuardedADB(StubADB(dump_seq=seq))
    scroll, merged = ste._scroll_sweep(g, [], max_passes=3)
    assert scroll.terminated == "max_passes" and scroll.passes == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k scroll -v`
Expected: FAIL (stub `_scroll_sweep` returns immediately; assertions on passes/terminated fail).

- [ ] **Step 3: Implement `_scroll_sweep` (replace the Task-7 stub)**

```python
def _scroll_sweep(g: GuardedADB, els: list, max_passes: int):
    """One pass = single swipe-up then dump; merge new labels; stop on no_new/max."""
    w, h = _VIEWPORT
    x = w // 2
    y1, y2 = int(h * 0.75), int(h * 0.25)   # swipe up within list area
    seen = {e.label for e in els if e.label}
    merged = list(els)
    swipes: list[dict] = []
    new_per_pass: list[int] = []
    terminated = "no_new"
    passes = 0
    for _ in range(max_passes):
        g.scroll_up(x, y1, x, y2)
        swipes.append({"dir": "up", "x1": x, "y1": y1, "x2": x, "y2": y2})
        passes += 1
        xml = g.dump()
        if not xml or "<node" not in xml:
            new_per_pass.append(0)
            terminated = "no_new"
            break
        new_els = _elements_from_xml(xml)
        added = 0
        for e in new_els:
            if e.label and e.label not in seen:
                seen.add(e.label)
                merged.append(e)
                added += 1
        new_per_pass.append(added)
        if added == 0:
            terminated = "no_new"
            break
    else:
        terminated = "max_passes"
    return mt.ScrollInfo(passes=passes, swipes=swipes,
                         new_texts_per_pass=new_per_pass, terminated=terminated), merged
```

- [ ] **Step 4: Run scroll + reach tests to verify pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k "scroll or explore_screen" -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint — DO NOT COMMIT**

Record: "Task 8 done — scroll sweep (single-swipe-per-pass) GREEN." No commit.

---

## Task 9: Driver — orchestration, device baseline, emit, CLI (TDD)

**Files:**
- Modify: `scripts/settings_tree_explorer.py`
- Test: `tests/test_settings_tree_explorer.py` (append)

- [ ] **Step 1: Write the failing orchestration tests**

```python
import json as _json


_PROPS = {
    "ro.product.model": "AT-M140", "ro.product.name": "alt_thor2", "ro.product.device": "thor2",
    "ro.build.fingerprint": "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260302M:user/release-keys",
    "ro.build.id": "RY07260302M", "ro.build.version.release": "14",
    "persist.sys.locale": "ko-KR", "ro.product.locale": "en-US",
    "__serial__": "B06201249E0002B8",
}


def test_capture_device_baseline():
    stub = StubADB(props=_PROPS)
    g = ste.GuardedADB(stub)
    dev = ste.capture_device_baseline(g, serial="B06201249E0002B8")
    assert dev.model == "AT-M140" and dev.build_id == "RY07260302M"
    assert dev.locale_persist == "ko-KR" and dev.serial == "B06201249E0002B8"


def test_target_mismatch_aborts_without_flag():
    stub = StubADB(props={"__serial__": "WRONGSERIAL"})
    with pytest.raises(ste.TargetMismatch):
        ste.preflight_serial(stub, target="B06201249E0002B8", allow_mismatch=False)


def test_target_mismatch_acknowledged_with_flag():
    stub = StubADB(props={"__serial__": "WRONGSERIAL"})
    ack = ste.preflight_serial(stub, target="B06201249E0002B8", allow_mismatch=True)
    assert ack is True   # target_mismatch_ack


def test_run_explore_builds_baseline_and_allowlist_clean(tmp_path):
    seed = {"seed_version": 1, "locale": "ko-KR", "target_serial": "B06201249E0002B8",
            "source_menu_tree": "x", "package": "com.android.settings",
            "screens": [_seed_screen()]}
    stub = StubADB(focus_seq=[_WIFI_FOCUS], dump_seq=[_DUMP, _DUMP], props=_PROPS)
    g = ste.GuardedADB(stub)
    baseline = ste.run_explore(g, seed, run_id="20260602T000000Z",
                               out_dir=str(tmp_path), settle=0, max_passes=1,
                               target_mismatch_ack=False)
    assert baseline.summary["screen_count"] == 1
    assert baseline.summary["reached"] == 1
    assert g.violations == 0                       # read-only invariant
    assert all(ste.is_allowed_command(c) for c in g.command_log)
    # JSON + MD written to out_dir
    out_json = tmp_path / "menu_tree_baseline_20260602T000000Z.json"
    assert out_json.exists()
    d = _json.loads(out_json.read_text(encoding="utf-8"))
    assert d["device"]["serial"] == "B06201249E0002B8"


def test_dry_run_makes_no_device_calls():
    seed = {"screens": [_seed_screen()], "target_serial": "B06201249E0002B8"}
    plan = ste.dry_run_plan(seed)
    assert "settings_d1_wifi" in plan and "am start -a android.settings.WIFI_SETTINGS" in plan
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -k "baseline or mismatch or run_explore or dry_run" -v`
Expected: FAIL — missing `capture_device_baseline` / `preflight_serial` / `run_explore` / `dry_run_plan`.

- [ ] **Step 3: Implement orchestration + emit + CLI (append)**

```python
class TargetMismatch(RuntimeError):
    pass


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def preflight_serial(adb, target: str, allow_mismatch: bool) -> bool:
    """Returns target_mismatch_ack. Raises TargetMismatch if mismatch & not allowed."""
    actual = adb.device_serial()
    if actual and target and actual != target:
        if not allow_mismatch:
            raise TargetMismatch(f"connected {actual} != target {target}")
        return True
    return False


def capture_device_baseline(g: GuardedADB, serial: str) -> mt.DeviceBaseline:
    gp = g.getprop
    try:
        viewport = (g.raw_shell("wm size").split(":")[-1].strip() or "480x800")
    except Exception:
        viewport = "480x800"
    try:
        dpi = (g.raw_shell("wm density").split(":")[-1].strip() or "220")
    except Exception:
        dpi = "220"
    return mt.DeviceBaseline(
        serial=serial or (g._adb.device_serial() or "unknown"),
        model=gp("ro.product.model"), product=gp("ro.product.name"),
        device=gp("ro.product.device"), build_fingerprint=gp("ro.build.fingerprint"),
        build_id=gp("ro.build.id"), android=gp("ro.build.version.release"),
        locale_persist=gp("persist.sys.locale"), locale_product=gp("ro.product.locale"),
        viewport=viewport, dpi=dpi, sim=gp("gsm.sim.operator.alpha") or "unknown")


def dry_run_plan(seed: dict) -> str:
    lines = [f"target_serial: {seed.get('target_serial')}",
             f"screens: {len(seed.get('screens', []))}"]
    for s in seed.get("screens", []):
        e = s.get("entry") or {}
        cmd = (f"am start -a {e['action']}" if e.get("action")
               else f"am start -n {e['component']}" if e.get("component") else "(no action)")
        lines.append(f"  - {s['id']}: {cmd}")
    return "\n".join(lines)


def run_explore(g: GuardedADB, seed: dict, run_id: str, out_dir: str,
                settle: float = 1.2, max_passes: int = 8,
                target_mismatch_ack: bool = False) -> mt.MenuTreeBaseline:
    serial = seed.get("target_serial", "")
    device = capture_device_baseline(g, serial)
    raw_root = os.path.join(out_dir, "raw", run_id)

    def raw_writer(screen_id: str, xml: str):
        os.makedirs(raw_root, exist_ok=True)
        with open(os.path.join(raw_root, f"{screen_id}.xml"), "w", encoding="utf-8") as fh:
            fh.write(xml)

    screens = [explore_screen(g, s, run_id=run_id, max_passes=max_passes,
                              settle=settle, raw_writer=raw_writer)
               for s in seed.get("screens", [])]
    baseline = mt.MenuTreeBaseline(
        schema_version=mt.SCHEMA_VERSION, tool_version=mt.TOOL_VERSION,
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        run_id=run_id, device=device, package=seed.get("package", "com.android.settings"),
        seed_ref={"source_menu_tree": seed.get("source_menu_tree"),
                  "seed_version": seed.get("seed_version"),
                  "seed_path": seed.get("__seed_path__", "")},
        target_mismatch_ack=target_mismatch_ack,
        summary=mt.compute_summary(screens), screens=screens)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, f"menu_tree_baseline_{run_id}")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        fh.write(baseline.to_json())
    with open(base + ".md", "w", encoding="utf-8") as fh:
        fh.write(baseline.to_md())
    return baseline


def main():
    import yaml
    p = argparse.ArgumentParser(description="Device Settings menu-tree baseline explorer (read-only).")
    p.add_argument("--seed", required=True, help="seed YAML path")
    p.add_argument("--out-dir", required=True, help="output dir (e.g. 'THOR2_K - Settings/catalog')")
    p.add_argument("--serial", help="ADB target serial")
    p.add_argument("--run-id", default=None)
    p.add_argument("--allow-target-mismatch", action="store_true")
    p.add_argument("--force-stop-on-stuck", action="store_true")
    p.add_argument("--max-passes", type=int, default=8)
    p.add_argument("--settle", type=float, default=1.2)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    with open(args.seed, encoding="utf-8") as fh:
        seed = yaml.safe_load(fh)
    seed["__seed_path__"] = args.seed
    if args.dry_run:
        print(dry_run_plan(seed))
        return

    adb = ADB(device_serial=args.serial)
    ack = preflight_serial(adb, target=seed.get("target_serial", ""),
                           allow_mismatch=args.allow_target_mismatch)
    g = GuardedADB(adb, allow_force_stop=args.force_stop_on_stuck)
    run_id = args.run_id or _now_run_id()
    baseline = run_explore(g, seed, run_id=run_id, out_dir=args.out_dir,
                           settle=args.settle, max_passes=args.max_passes,
                           target_mismatch_ack=ack)
    s = baseline.summary
    print(f"device smoke: baseline bundle 생성 run_id={run_id}, "
          f"{s['reached'] + s['reached_external']}/{s['screen_count']} REACHED, "
          f"allowlist violations={g.violations}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full driver suite**

Run: `venv/Scripts/python.exe -m pytest tests/test_settings_tree_explorer.py -v`
Expected: PASS (all driver tests).

- [ ] **Step 5: Run the entire new suite together**

Run: `venv/Scripts/python.exe -m pytest tests/test_menu_tree.py tests/test_menu_mapper_refactor.py tests/test_settings_tree_explorer.py -v`
Expected: PASS (all). Also run full repo suite to confirm no regression: `venv/Scripts/python.exe -m pytest -q` → no new failures.

- [ ] **Step 6: Checkpoint — DO NOT COMMIT**

Record: "Task 9 done — orchestration + emit + CLI + dry-run GREEN; full suite GREEN." No commit.

---

## Task 10: Device smoke (THOR2_K) — manual, gated — ✅ EXECUTED 2026-06-04

**Files:** none (runtime evidence only)

> Executed on **`B06201249E0002F0`** (THOR2_K, AT-M140, android 14, ko-KR) after explicit user go.
> Seed `target_serial` corrected **B06201249E0002B8 → B06201249E0002F0** before the run
> (user decision; `--allow-target-mismatch` NOT used). Appium device `B2700125BW000083`
> confirmed distinct and untouched. All ADB calls pinned `-s B06201249E0002F0`.

- [x] **Step 1: Dry-run (no device mutation)** — printed target_serial + 17 launch commands; 0 device calls.

- [x] **Step 2: Real run on THOR2_K**

Run: `venv/Scripts/python.exe scripts/settings_tree_explorer.py --seed "THOR2_K - Settings/menu_tree_seed.yaml" --out-dir "THOR2_K - Settings/catalog" --serial B06201249E0002F0`
Result: `device smoke: baseline bundle 생성 run_id=20260604T074020Z, 14/17 REACHED, allowlist violations=0`.

- [x] **Step 3: Verify acceptance criteria** — `screen_count == 17`, `violations == 0`, `device.serial == B06201249E0002F0` (실단말 일치), `target_mismatch_ack == false`. Report term (§2.2): **device smoke observed**.

- [x] **Step 4: Checkpoint — DO NOT COMMIT** — recorded below; no commit.

### Task 10 evidence (run_id `20260604T074020Z`)

Artifacts (append-only, overwrite-refuse active):
- JSON: `THOR2_K - Settings/catalog/menu_tree_baseline_20260604T074020Z.json` (192,335 B)
- MD:   `THOR2_K - Settings/catalog/menu_tree_baseline_20260604T074020Z.md` (28,973 B)
- raw:  `THOR2_K - Settings/catalog/raw/20260604T074020Z/*.xml` (14 dumps)

Reach tally (14/17 REACHED):
- `REACHED` (internal) ×13: home, privacy, location, wifi, bluetooth, data_usage, sound, display, accessibility, date, apps, usage_access, dream
- `REACHED_EXTERNAL_PACKAGE` ×1: home_launcher (allowlist ext pkg, activity_match)
- `FOCUS_MISMATCH` ×3: google, device_info, wellbeing
- LAUNCH_FAILED / DUMP_REJECTED / UNREACHABLE_NO_ACTION: 0
- elements parsed total 365 · observed_texts 353 · scroll passes 49 · denylist recorded 29

Acceptance criteria met: GuardedADB violations **0** · forbidden command (tap / ENTER / DPAD_CENTER / POWER / text input / settings put / pm clear / install·uninstall / rm) **0** · all ADB `-s B06201249E0002F0` pinned · output append-only (no overwrite).

**NOTE — FOCUS_MISMATCH ×3 (도구 결함 아님 / v1.1 후속)**: component·external deep-link 화면(google `.Settings$AccountDashboardActivity`, device_info `.Settings$MyDeviceInfoActivity`, wellbeing 외부 pkg)에서 실제 focus가 seed `expect_activity_regex`와 불일치. reach ladder가 crash/abort 없이 `FOCUS_MISMATCH`로 격리 + HOME 복구 → 설계대로 동작. seed regex/deeplink 조정은 **v1.1 후속으로 분리**, 이번 트랙에서 임의 수정하지 않음.

---

## Task 11: Batch commit (EXPLICIT APPROVAL GATE)

**Files:** all of the above (explicit paths only)

> **DO NOT run this task without the user explicitly saying "commit now".** Global policy §7.

- [ ] **Step 1: Show status (read-only)**

```bash
git status --short
git diff --name-only
```

- [ ] **Step 2: Stage explicit paths only (NO broad add)**

```bash
git add scripts/menu_mapper.py src/menu_tree.py scripts/settings_tree_explorer.py \
  "THOR2_K - Settings/menu_tree_seed.yaml" "THOR2_K - Settings/catalog_schema.md" \
  tests/test_menu_mapper_refactor.py tests/test_menu_tree.py tests/test_settings_tree_explorer.py \
  tests/fixtures/menu_tree \
  docs/superpowers/specs/2026-06-02-device-menu-tree-baseline-design.md \
  docs/superpowers/plans/2026-06-02-device-menu-tree-baseline.md
```

(Decide separately whether to include the generated `THOR2_K - Settings/catalog/menu_tree_baseline_*` bundle — Tier D append-only artifact; per §5.6 catalog is tracked, but confirm with user.)

- [ ] **Step 3: Commit**

```bash
git commit -m @'
feat(menu-tree): device-sourced Settings menu-tree baseline explorer (v1)

- src/menu_tree.py: canonical schema + classifiers + JSON/MD emitters (pure)
- scripts/settings_tree_explorer.py: read-only deep-link enumeration driver
  (GuardedADB command allowlist, reach 6-status, scroll sweep, emit)
- scripts/menu_mapper.py: parsers to module-level (methods wrap; behavior 0-change)
- THOR2_K seed (17 screens) + catalog_schema Tier D
- offline tests on real dumps; allowlist-violation==0 invariant

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
'@
```

- [ ] **Step 4: Report per §7.2 commit format** (changed/staged files, message, tests, non-goals, final `git status`).

---

## Self-Review (completed by plan author)

- **Spec coverage:** §3 layout → Tasks 1,2,5,6,9; §4 schema → Tasks 2,3; §5 seed → Task 5; §6 flow/reach → Tasks 6,7,8,9; §7 read-only allowlist → Task 6 + asserted Tasks 6/9; §8 Tier D → Task 5; §9 testing → Tasks 1–9; §10 acceptance → Tasks 9,10; §11 SoT → DENYLIST single-source (Task 1) + same-PR alignment (Task 11). No uncovered requirement.
- **Type consistency:** `MenuElement/MenuScreen/ScrollInfo/DumpInfo/DeviceBaseline/MenuTreeBaseline`, `build_element`, `bucket_texts`, `compute_summary`, `to_json/to_md`, `GuardedADB`, `is_allowed_command`, `CommandNotAllowed`, `explore_screen`, `_scroll_sweep`, `_classify_reach`, `preflight_serial`, `capture_device_baseline`, `run_explore`, `dry_run_plan`, `TargetMismatch` — referenced consistently across tasks.
- **Reach precedence:** `UNREACHABLE_NO_ACTION` (no action) → `LAUNCH_FAILED` (no focus) → `FOCUS_MISMATCH`/`REACHED*` → `DUMP_REJECTED` (reached but empty dump), reach_kind preserved — matches spec §6.
- **Commit policy:** per-task checkpoints (no commit); single gated batch commit in Task 11.

---

## Execution Log (2026-06-04)

| Task | Scope | Status |
|---|---|---|
| 1 | menu_mapper parsers → module-level (behavior-preserving) | ✅ done |
| 2 | src/menu_tree.py classifiers | ✅ done |
| 3 | dataclasses + JSON/MD emitters + determinism | ✅ done |
| 4 | 3 real-dump fixtures + parse test | ✅ done |
| 5 | seed (17 screens) + catalog_schema Tier D | ✅ done |
| 6 | GuardedADB read-only / navigation-safe allowlist | ✅ done |
| 7 | per-screen reach classification + dump/parse | ✅ done |
| 8 | scroll sweep (element-level merge, single fingerprint) | ✅ done |
| 9 | orchestration + device baseline + emit + CLI | ✅ done |
| 10 | device smoke on `B06201249E0002F0` | ✅ done — 14/17 REACHED, violations 0 (evidence in Task 10) |
| 11 | batch commit | ⏸ PENDING — gated on explicit "commit now" |

Offline track suite: **46 passed** (`test_menu_mapper_refactor` + `test_menu_tree` + `test_menu_tree_seed` + `test_settings_tree_explorer`). Task 10 = `device smoke observed` (§2.2).

Plan deviations recorded during execution (all confirmed by user):
- `_classify_reach`: `activity_match` (expect_regex) used as the external-package discriminator (plan version mis-classified any allowlisted external pkg as REACHED_EXTERNAL_PACKAGE).
- allowlist trimmed: only HOME/BACK keyevents (no numeric/ENTER/DPAD/POWER); `rm` removed (temp dump overwritten in place); `wm size|density` kept read-only.
- CLI limited to 5 options (`--seed/--out-dir/--serial/--allow-target-mismatch/--dry-run`).
- `run_explore` overwrite-refuse (fail-fast pre-device) + target-mismatch gate.
- seed `target_serial` corrected B8 → F0 for the smoke device (Task 10).

NOTE (out-of-scope, **not** introduced by this track): `tests/test_tc_loader.py::test_schema_action_enum_matches_loader_valid_actions` fails on a pre-existing schema↔loader drift (`key_sequence` / `verify_focus_moved` added to `tc_step_schema.json` in commit `cd44024`, not mirrored in `src/tc_loader.py` `VALID_ACTIONS`). Separate alignment ticket; untouched here.
