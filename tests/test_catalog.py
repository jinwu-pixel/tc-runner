"""PR 3 Screen Identity Catalog tests.

총 23건:
- pure helper 4 (compute_screen_id)
- screen_kind 분류 3
- discovery + CLI 입력 모드 5
- run_id source-of-truth 2
- build 시나리오 8
- show 1
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from src import catalog as catalog_mod
from src.catalog import (
    SCREEN_KIND_LOCKSCREEN,
    SCREEN_KIND_OTHER,
    SCREEN_KIND_TARGET,
    classify_screen_kind,
    cmd_build,
    cmd_show,
    compute_screen_id,
    discover_manifests,
    union_visible_texts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, overrides: dict) -> dict:
    out = dict(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = _deep_merge(out[k], v)
            out[k] = merged
        else:
            out[k] = v
    return out


def _make_manifest(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "tool_version": "pr2-preflight-v1",
        "run_id": "test_run_001",
        "tc_path": "fake.yaml",
        "tc_id": "FAKE",
        "device": {"serial": "DEV1", "model": "AT-M150", "android_version": "14"},
        "app": {
            "package_name": "com.example.test",
            "installed": True,
            "version_name": "1.0",
            "version_code": 1,
        },
        "permissions": {"required": [], "grants": {}, "parse_status": "ok"},
        "screen": {
            "resolution": "720x1560",
            "current_activity": "com.example.test/com.example.test.MainActivity",
            "activity_parse_status": "ok",
            "screenshot_path": "screenshot.png",
            "screenshot_status": "ok",
            "screenshot_sha256": "screenshot_hash_aaaa",
            "window_dump_path": "window_dump.xml",
            "xml_status": "ok",
            "xml_sha256": "xml_hash_aaaa",
        },
        "text_model": {
            "expected_texts_from_tc": [],
            "visible_texts_from_dump": ["Hello", "World"],
            "missing_expected_texts": [],
            "diff_status": "ok",
            "coverage": 1.0,
        },
        "preflight_status": {"level": "OK", "reasons": []},
    }
    return _deep_merge(base, overrides)


def _write_manifest(path: Path, manifest: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Pure helpers (4)
# ---------------------------------------------------------------------------


def test_compute_screen_id_stable():
    a = compute_screen_id("com.example/.MainActivity", "abc")
    b = compute_screen_id("com.example/.MainActivity", "abc")
    assert a == b
    assert isinstance(a, str) and len(a) == 64


def test_compute_screen_id_changes_with_xml_sha():
    a = compute_screen_id("com.example/.MainActivity", "abc")
    b = compute_screen_id("com.example/.MainActivity", "def")
    assert a != b


def test_compute_screen_id_unknown_activity_when_null():
    a = compute_screen_id(None, "abc")
    b = compute_screen_id("UNKNOWN_ACTIVITY", "abc")
    assert a == b


def test_compute_screen_id_returns_none_when_no_xml_sha():
    assert compute_screen_id("com.example/.MainActivity", None) is None
    assert compute_screen_id("com.example/.MainActivity", "") is None


# ---------------------------------------------------------------------------
# classify_screen_kind (3)
# ---------------------------------------------------------------------------


def test_classify_target_app():
    m = _make_manifest(
        screen={"current_activity": "com.example.test/.MainActivity"}
    )
    assert classify_screen_kind(m, "com.example.test") == SCREEN_KIND_TARGET


def test_classify_lockscreen_or_non_target():
    m = _make_manifest(
        screen={"current_activity": None, "activity_parse_status": "failed"},
        preflight_status={"level": "WARN", "reasons": ["activity_parse_failed"]},
    )
    assert classify_screen_kind(m, "com.example.test") == SCREEN_KIND_LOCKSCREEN


def test_classify_other_app_or_system():
    m = _make_manifest(
        screen={"current_activity": "com.android.settings/.MainActivity"}
    )
    assert classify_screen_kind(m, "com.example.test") == SCREEN_KIND_OTHER


# ---------------------------------------------------------------------------
# Discovery + CLI input modes (5)
# ---------------------------------------------------------------------------


def test_discover_from_reports_flat(tmp_path):
    base = tmp_path / "reports" / "preflight"
    p1 = base / "run_a" / "manifest.json"
    p2 = base / "run_b" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_a"))
    _write_manifest(p2, _make_manifest(run_id="run_b"))

    found = discover_manifests(base)
    assert sorted(found) == sorted([p1, p2])


def test_discover_from_reports_nested(tmp_path):
    base = tmp_path / "reports" / "preflight"
    p1 = base / "run_a" / "tc_alpha" / "manifest.json"
    p2 = base / "run_a" / "tc_beta" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_a"))
    _write_manifest(p2, _make_manifest(run_id="run_a"))

    found = discover_manifests(base)
    assert sorted(found) == sorted([p1, p2])


def test_build_rejects_both_from_reports_and_manifest(tmp_path):
    app_dir = tmp_path / "app"
    with pytest.raises(ValueError):
        cmd_build(
            app_dir,
            from_reports=tmp_path / "reports" / "preflight",
            manifest=tmp_path / "manifest.json",
        )


def test_build_defaults_to_reports_preflight_when_neither_given(tmp_path, monkeypatch):
    base = tmp_path / "reports" / "preflight"
    p1 = base / "run_a" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_a"))

    app_dir = tmp_path / "ODIN2 - test"
    app_dir.mkdir(parents=True)

    monkeypatch.chdir(tmp_path)
    summary = cmd_build(app_dir)
    assert summary["discovered"] == 1
    assert summary["added"] == 1


def test_build_manifest_single_input(tmp_path):
    p1 = tmp_path / "reports" / "preflight" / "run_x" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_x"))

    app_dir = tmp_path / "app"
    summary = cmd_build(app_dir, manifest=p1)
    assert summary["discovered"] == 1
    assert summary["added"] == 1


# ---------------------------------------------------------------------------
# run_id source-of-truth (2)
# ---------------------------------------------------------------------------


def test_run_id_comes_only_from_manifest(tmp_path):
    """visit.jsonl 기록 시 run_id는 manifest['run_id'] 값과 정확히 일치해야 한다."""
    p1 = tmp_path / "m" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="from_manifest_xyz"))

    app_dir = tmp_path / "app"
    cmd_build(app_dir, manifest=p1)

    visits = (app_dir / "catalog" / "visits.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 1
    visit = json.loads(visits[0])
    assert visit["run_id"] == "from_manifest_xyz"


def test_missing_run_id_skipped(tmp_path):
    base = tmp_path / "reports" / "preflight"
    p_no_id = base / "missing" / "manifest.json"
    p_ok = base / "ok" / "manifest.json"

    no_id_doc = _make_manifest()
    no_id_doc["run_id"] = ""
    _write_manifest(p_no_id, no_id_doc)
    _write_manifest(p_ok, _make_manifest(run_id="ok_run"))

    app_dir = tmp_path / "app"
    summary = cmd_build(app_dir, from_reports=base)

    assert summary["skipped_missing_run_id"] == 1
    assert summary["added"] == 1
    visits_path = app_dir / "catalog" / "visits.jsonl"
    visits = visits_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 1
    assert json.loads(visits[0])["run_id"] == "ok_run"


# ---------------------------------------------------------------------------
# Build scenarios (8)
# ---------------------------------------------------------------------------


def test_build_first_manifest_creates_screens_and_visits(tmp_path):
    p1 = tmp_path / "m" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_001"))

    app_dir = tmp_path / "app"
    summary = cmd_build(app_dir, manifest=p1)

    screens_path = app_dir / "catalog" / "screens.json"
    visits_path = app_dir / "catalog" / "visits.jsonl"

    assert screens_path.exists()
    assert visits_path.exists()

    doc = json.loads(screens_path.read_text(encoding="utf-8"))
    assert len(doc["screens"]) == 1
    only_entry = next(iter(doc["screens"].values()))
    assert only_entry["observed_count"] == 1

    visits = visits_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 1
    assert summary["added"] == 1
    assert summary["updated"] == 0


def test_build_idempotent_on_same_key(tmp_path):
    """동일 (manifest_path, run_id) 재실행은 full skip — 변동 0."""
    p1 = tmp_path / "m" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_dup"))

    app_dir = tmp_path / "app"
    summary1 = cmd_build(app_dir, manifest=p1)
    assert summary1["added"] == 1

    summary2 = cmd_build(app_dir, manifest=p1)
    assert summary2["skipped_duplicate"] == 1
    assert summary2["added"] == 0
    assert summary2["updated"] == 0

    visits = (app_dir / "catalog" / "visits.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 1

    doc = json.loads((app_dir / "catalog" / "screens.json").read_text(encoding="utf-8"))
    only_entry = next(iter(doc["screens"].values()))
    assert only_entry["observed_count"] == 1


def test_build_same_screen_different_run_id_increments(tmp_path):
    """같은 screen_id, 다른 (manifest_path, run_id) 는 visit append + observed_count++."""
    base = tmp_path / "reports"
    p1 = base / "run_a" / "manifest.json"
    p2 = base / "run_b" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="run_a"))
    _write_manifest(p2, _make_manifest(run_id="run_b"))

    app_dir = tmp_path / "app"
    cmd_build(app_dir, from_reports=base)

    doc = json.loads((app_dir / "catalog" / "screens.json").read_text(encoding="utf-8"))
    assert len(doc["screens"]) == 1
    only_entry = next(iter(doc["screens"].values()))
    assert only_entry["observed_count"] == 2

    visits = (app_dir / "catalog" / "visits.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 2


def test_build_same_file_different_path_string_is_separate_visit(tmp_path):
    """같은 파일이라도 다른 경로 문자열로 입력하면 별도 visit. (정책 명시)"""
    real = tmp_path / "m" / "manifest.json"
    _write_manifest(real, _make_manifest(run_id="run_path_test"))

    app_dir = tmp_path / "app"

    # 1차: 절대경로
    cmd_build(app_dir, manifest=Path(str(real.resolve())))

    # 2차: 상대경로 (cwd 기준)
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        rel = Path("m") / "manifest.json"
        cmd_build(app_dir, manifest=rel)
    finally:
        os.chdir(cwd)

    visits = (app_dir / "catalog" / "visits.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(visits) == 2
    paths = [json.loads(v)["manifest_path"] for v in visits]
    assert paths[0] != paths[1]

    doc = json.loads((app_dir / "catalog" / "screens.json").read_text(encoding="utf-8"))
    only_entry = next(iter(doc["screens"].values()))
    assert only_entry["observed_count"] == 2


def test_build_visible_texts_union_preserves_order_and_dedupes(tmp_path):
    """같은 screen_id 다회 관찰 시 visible_texts 합집합이 순서 보존 + 중복 제거."""
    base = tmp_path / "reports"
    p1 = base / "a" / "manifest.json"
    p2 = base / "b" / "manifest.json"
    _write_manifest(
        p1,
        _make_manifest(run_id="r1", text_model={"visible_texts_from_dump": ["A", "B", "C"]}),
    )
    _write_manifest(
        p2,
        _make_manifest(run_id="r2", text_model={"visible_texts_from_dump": ["B", "D", "E"]}),
    )

    app_dir = tmp_path / "app"
    cmd_build(app_dir, from_reports=base)

    doc = json.loads((app_dir / "catalog" / "screens.json").read_text(encoding="utf-8"))
    only_entry = next(iter(doc["screens"].values()))
    assert only_entry["visible_texts"] == ["A", "B", "C", "D", "E"]


def test_build_xml_sha_null_skipped(tmp_path):
    """xml_sha256 null manifest 는 skipped_no_xml_hash 로 집계, screens/visits 변동 0."""
    p1 = tmp_path / "m" / "manifest.json"
    bad = _make_manifest(run_id="bad")
    bad["screen"]["xml_sha256"] = None
    _write_manifest(p1, bad)

    app_dir = tmp_path / "app"
    summary = cmd_build(app_dir, manifest=p1)

    assert summary["skipped_no_xml_hash"] == 1
    assert summary["added"] == 0
    assert not (app_dir / "catalog" / "visits.jsonl").exists()
    assert not (app_dir / "catalog" / "screens.json").exists()


def test_build_generated_at_idempotent_when_no_change(tmp_path):
    """변경 0건 재실행 시 screens.json 의 mtime 과 generated_at 이 모두 보존된다."""
    p1 = tmp_path / "m" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="r_idempotent"))

    app_dir = tmp_path / "app"
    cmd_build(app_dir, manifest=p1)

    screens_path = app_dir / "catalog" / "screens.json"
    first_mtime = screens_path.stat().st_mtime_ns
    first_doc = json.loads(screens_path.read_text(encoding="utf-8"))
    first_generated_at = first_doc["generated_at"]

    time.sleep(1.1)  # ensure mtime resolution

    summary = cmd_build(app_dir, manifest=p1)
    assert summary["skipped_duplicate"] == 1

    second_mtime = screens_path.stat().st_mtime_ns
    second_doc = json.loads(screens_path.read_text(encoding="utf-8"))

    assert second_mtime == first_mtime
    assert second_doc["generated_at"] == first_generated_at


def test_build_default_target_package_from_first_valid(tmp_path):
    """target_package 미지정 시 첫 valid manifest.app.package_name 을 채택."""
    base = tmp_path / "reports"
    # discover sorted: 'a' comes before 'b'
    p_no_pkg = base / "a" / "manifest.json"
    p_with_pkg = base / "b" / "manifest.json"

    no_pkg = _make_manifest(run_id="ra", screen={"xml_sha256": "xa"})
    no_pkg["app"]["package_name"] = None
    _write_manifest(p_no_pkg, no_pkg)

    with_pkg = _make_manifest(run_id="rb", screen={"xml_sha256": "xb"})
    with_pkg["app"]["package_name"] = "com.example.target"
    _write_manifest(p_with_pkg, with_pkg)

    app_dir = tmp_path / "app"
    summary = cmd_build(app_dir, from_reports=base)

    assert summary["target_package"] == "com.example.target"

    doc = json.loads((app_dir / "catalog" / "screens.json").read_text(encoding="utf-8"))
    assert doc["target_package"] == "com.example.target"


# ---------------------------------------------------------------------------
# Show (1)
# ---------------------------------------------------------------------------


def test_show_summary_output(tmp_path, capsys):
    p1 = tmp_path / "m" / "manifest.json"
    _write_manifest(p1, _make_manifest(run_id="r_show"))

    app_dir = tmp_path / "app"
    cmd_build(app_dir, manifest=p1)

    text = cmd_show(app_dir)
    assert "app_dir:" in text
    assert "target_package: com.example.test" in text
    assert "total: 1" in text
    assert "target_app: 1" in text


def test_union_visible_texts_dedupe_and_order():
    out = union_visible_texts(["a", "b"], ["b", "c", "a", "d"])
    assert out == ["a", "b", "c", "d"]
