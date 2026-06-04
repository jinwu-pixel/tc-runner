"""Validation of the curated THOR2_K Settings menu-tree seed (Task 5).

Structure-only checks on the hand-curated seed YAML — NOT a device test.
Source of truth for the seed = `THOR2_K - Settings/MENU_TREE.md` (curated subset).
"""
from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_SEED = _ROOT / "THOR2_K - Settings" / "menu_tree_seed.yaml"


def _load():
    return yaml.safe_load(_SEED.read_text(encoding="utf-8"))


def test_seed_file_exists():
    assert _SEED.is_file(), f"seed missing: {_SEED}"


def test_seed_top_level_structure():
    d = _load()
    assert d["seed_version"] == 1
    assert d["target_serial"] == "B06201249E0002F0"
    assert d["locale"] == "ko-KR"
    assert d["package"] == "com.android.settings"
    assert isinstance(d["screens"], list) and len(d["screens"]) >= 17


def test_seed_screen_ids_unique():
    d = _load()
    ids = [s["id"] for s in d["screens"]]
    assert len(ids) == len(set(ids)), "duplicate screen id(s)"


def test_seed_entry_action_xor_component():
    d = _load()
    for s in d["screens"]:
        entry = s["entry"]
        has_action = bool(entry.get("action"))
        has_component = bool(entry.get("component"))
        assert has_action != has_component, \
            f"{s['id']}: entry must have exactly one of action/component"


def test_seed_required_fields_present():
    d = _load()
    for s in d["screens"]:
        assert s.get("id"), "a screen is missing id"
        assert s.get("label_ko"), f"{s['id']}: missing label_ko"
        nav = s.get("nav_path")
        assert isinstance(nav, list) and nav, f"{s['id']}: missing/empty nav_path"
        assert s.get("expect_activity_regex"), f"{s['id']}: missing expect_activity_regex"
