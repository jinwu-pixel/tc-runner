"""PR 4 Catalog Delta Detector tests.

verdict priority: insufficient → non_target_context → known_screen → changed_texts → new_screen
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.catalog import compute_screen_id
from src.catalog_delta import (
    DEFAULT_JACCARD_THRESHOLD,
    INVALID_RUN_ID_CHARS,
    SCHEMA_VERSION,
    TOOL_VERSION,
    VERDICT_CHANGED_TEXTS,
    VERDICT_INSUFFICIENT,
    VERDICT_KNOWN_SCREEN,
    VERDICT_NEW_SCREEN,
    VERDICT_NON_TARGET_CONTEXT,
    cmd_delta,
    diff_texts,
    evaluate_delta,
    jaccard_texts,
    validate_run_id_for_filename,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, overrides: dict) -> dict:
    out = dict(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
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
            "screenshot_sha256": "ss_aaa",
            "window_dump_path": "window_dump.xml",
            "xml_status": "ok",
            "xml_sha256": "xml_aaa",
        },
        "text_model": {
            "expected_texts_from_tc": [],
            "visible_texts_from_dump": ["Alpha", "Beta", "Gamma", "Delta"],
            "missing_expected_texts": [],
            "diff_status": "ok",
            "coverage": 1.0,
        },
        "preflight_status": {"level": "OK", "reasons": []},
    }
    return _deep_merge(base, overrides)


def _make_catalog(target_package: str | None, screens: dict) -> dict:
    return {
        "schema_version": 1,
        "tool_version": "pr3-catalog-v1",
        "app_dir": "test_app",
        "target_package": target_package,
        "generated_at": "2026-04-29T00:00:00Z",
        "screens": screens,
    }


def _make_screen_entry(
    *,
    current_activity: str | None,
    xml_sha256: str,
    visible_texts: list[str],
    screen_kind: str = "target_app",
) -> dict:
    sid = compute_screen_id(current_activity, xml_sha256)
    return sid, {
        "screen_id": sid,
        "screen_kind": screen_kind,
        "current_activity": current_activity,
        "xml_sha256": xml_sha256,
        "observed_count": 1,
        "first_seen": "2026-04-29T00:00:00Z",
        "last_seen": "2026-04-29T00:00:00Z",
        "visible_texts": visible_texts,
    }


def _write_catalog(catalog_dir: Path, target_package: str | None, screens: dict) -> Path:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    doc = _make_catalog(target_package, screens)
    path = catalog_dir / "screens.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    # visits.jsonl 도 함께 (read-only invariant 검증용)
    visits_path = catalog_dir / "visits.jsonl"
    if not visits_path.exists():
        visits_path.write_text("", encoding="utf-8")
    return path


def _write_manifest(path: Path, manifest: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def _setup_basic(tmp_path: Path, *, manifest_overrides=None, catalog_screens=None, target_package="com.example.test"):
    """공통 setup: catalog_dir, manifest_path, output_dir, manifest dict 반환."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    if catalog_screens is None:
        catalog_screens = {}
    _write_catalog(catalog_dir, target_package, catalog_screens)

    m = _make_manifest(**(manifest_overrides or {}))
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, m)

    output_dir = tmp_path / "out"
    return catalog_dir, manifest_path, output_dir, m


# ---------------------------------------------------------------------------
# Pure helpers (validate_run_id_for_filename, jaccard_texts, diff_texts)
# ---------------------------------------------------------------------------


def test_validate_run_id_accepts_normal():
    assert validate_run_id_for_filename("manual_pr3_target_gallery_odin2") == (
        "manual_pr3_target_gallery_odin2"
    )


def test_validate_run_id_rejects_empty():
    with pytest.raises(ValueError):
        validate_run_id_for_filename("")
    with pytest.raises(ValueError):
        validate_run_id_for_filename("   ")
    with pytest.raises(ValueError):
        validate_run_id_for_filename(None)


def test_validate_run_id_rejects_path_separators_and_dangerous_chars():
    for ch in INVALID_RUN_ID_CHARS:
        with pytest.raises(ValueError):
            validate_run_id_for_filename(f"bad{ch}id")


def test_jaccard_both_empty_returns_none():
    assert jaccard_texts([], []) is None


def test_jaccard_one_empty_returns_zero():
    assert jaccard_texts([], ["a"]) == 0.0
    assert jaccard_texts(["a"], []) == 0.0


def test_jaccard_full_overlap():
    assert jaccard_texts(["a", "b"], ["b", "a"]) == 1.0


def test_jaccard_partial():
    # {a,b,c} vs {b,c,d}: |∩|=2, |∪|=4 → 0.5
    assert jaccard_texts(["a", "b", "c"], ["b", "c", "d"]) == 0.5


def test_diff_texts_added_removed():
    added, removed = diff_texts(["a", "b", "c"], ["b", "c", "d"])
    assert added == ["d"]
    assert removed == ["a"]


# ---------------------------------------------------------------------------
# Test 1: known_screen exact match
# ---------------------------------------------------------------------------


def test_known_screen_exact_match(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha", "Beta"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_KNOWN_SCREEN
    assert report["delta"]["baseline_screen_id"] == sid
    assert report["manifest_kind"] == "target_app"
    assert report["package_match"] is True


# ---------------------------------------------------------------------------
# Test 2: changed_texts at boundary J = θ (inclusive)
# ---------------------------------------------------------------------------


def test_changed_texts_boundary_inclusive(tmp_path):
    """manifest visible {A,B,C,D}, catalog same activity 다른 xml_sha visible {C,D,E,F}.
    |∩|=2, |∪|=6 → J=0.333... 으로는 부족하니 별도로 J=0.5 케이스 구성.
    {A,B,C} vs {B,C,D} → J=2/4=0.5. boundary inclusive.
    """
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["B", "C", "D"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"xml_sha256": "xml_NEW"},
            "text_model": {"visible_texts_from_dump": ["A", "B", "C"]},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_CHANGED_TEXTS
    assert report["delta"]["baseline_screen_id"] == sid
    assert report["delta"]["jaccard"] == 0.5
    assert report["delta"]["added_texts"] == ["A"]
    assert report["delta"]["removed_texts"] == ["D"]


# ---------------------------------------------------------------------------
# Test 3: new_screen — same activity but J < θ
# ---------------------------------------------------------------------------


def test_new_screen_when_j_below_threshold(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["P", "Q", "R"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"xml_sha256": "xml_NEW"},
            "text_model": {"visible_texts_from_dump": ["A", "B", "C"]},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_NEW_SCREEN
    assert report["delta"]["baseline_screen_id"] is None
    assert report["delta"]["jaccard"] is None


# ---------------------------------------------------------------------------
# Test 4: new_screen — no same-activity candidate
# ---------------------------------------------------------------------------


def test_new_screen_when_no_same_activity(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.OtherActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A", "B"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_NEW_SCREEN
    assert report["delta"]["baseline_screen_id"] is None


# ---------------------------------------------------------------------------
# Test 5/6: non_target_context (lockscreen / other_app)
# ---------------------------------------------------------------------------


def test_non_target_context_lockscreen(tmp_path):
    # 빈 catalog 가 아닌 catalog (insufficient 회피용)
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {
                "current_activity": None,
                "activity_parse_status": "failed",
            },
            "preflight_status": {"level": "WARN", "reasons": ["activity_parse_failed"]},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_NON_TARGET_CONTEXT
    assert report["manifest_kind"] == "lockscreen_or_non_target"
    assert "lockscreen_context" in report["interpretation_flags"]


def test_non_target_context_other_app(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"current_activity": "com.android.settings/.MainActivity"},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_NON_TARGET_CONTEXT
    assert report["manifest_kind"] == "other_app_or_system"
    assert "non_target_app_context" in report["interpretation_flags"]


# ---------------------------------------------------------------------------
# Test 7-10: insufficient subtypes
# ---------------------------------------------------------------------------


def test_insufficient_missing_xml_sha(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={"screen": {"xml_sha256": None}},
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_INSUFFICIENT
    assert "xml_sha256_missing" in report["insufficient_reasons"]


def test_insufficient_package_mismatch_with_cross_app_flag(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={"app": {"package_name": "com.example.OTHER"}},
        catalog_screens={sid: entry},
        target_package="com.example.test",
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_INSUFFICIENT
    assert "package_mismatch" in report["insufficient_reasons"]
    assert "cross_app_context" in report["interpretation_flags"]


def test_insufficient_catalog_screens_empty(tmp_path):
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={}
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_INSUFFICIENT
    assert "catalog_screens_empty" in report["insufficient_reasons"]


def test_insufficient_current_activity_and_visible_texts_both_missing(tmp_path):
    # current_activity null + visible_texts empty + activity_parse_failed
    # screens 가 비어있지 않도록 mock 추가
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_OTHER",
        visible_texts=["A"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"current_activity": None, "activity_parse_status": "failed"},
            "text_model": {"visible_texts_from_dump": []},
            "preflight_status": {"level": "WARN", "reasons": ["activity_parse_failed"]},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_INSUFFICIENT
    assert "current_activity_and_visible_texts_missing" in report["insufficient_reasons"]


# ---------------------------------------------------------------------------
# Test 11: preset_unknown flag — verdict not overridden (still known_screen)
# ---------------------------------------------------------------------------


def test_preset_unknown_flag_does_not_override_verdict(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha", "Beta", "Gamma", "Delta"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "preflight_status": {"level": "WARN", "reasons": ["expected_texts_missing"]},
        },
        catalog_screens={sid: entry},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_KNOWN_SCREEN
    assert "preset_unknown" in report["interpretation_flags"]


# ---------------------------------------------------------------------------
# Test 12: read-only invariant — catalog 파일 byte-equal & mtime 보존
# ---------------------------------------------------------------------------


def test_catalog_files_read_only_invariant(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    screens_path = catalog_dir / "screens.json"
    visits_path = catalog_dir / "visits.jsonl"

    screens_bytes = screens_path.read_bytes()
    visits_bytes = visits_path.read_bytes()
    screens_mtime = screens_path.stat().st_mtime_ns
    visits_mtime = visits_path.stat().st_mtime_ns

    cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)

    assert screens_path.read_bytes() == screens_bytes
    assert visits_path.read_bytes() == visits_bytes
    assert screens_path.stat().st_mtime_ns == screens_mtime
    assert visits_path.stat().st_mtime_ns == visits_mtime


# ---------------------------------------------------------------------------
# Test 13: manifest_path verbatim — 입력 문자열 그대로 보존
# ---------------------------------------------------------------------------


def test_manifest_path_verbatim_in_report(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    # str(Path) 변환 후 그대로 들어가야 함
    assert report["manifest_path"] == str(manifest_path)


# ---------------------------------------------------------------------------
# Test 14: threshold validation — out of range raises
# ---------------------------------------------------------------------------


def test_cmd_delta_threshold_out_of_range_raises(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    with pytest.raises(ValueError):
        cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=-0.1)
    with pytest.raises(ValueError):
        cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=1.5)


# ---------------------------------------------------------------------------
# Test 15: report 작성 + schema_version + tool_version
# ---------------------------------------------------------------------------


def test_cmd_delta_writes_report_with_schema(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    out_path = output_dir / "test_run_001.json"
    assert out_path.exists()

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["schema_version"] == SCHEMA_VERSION
    assert written["tool_version"] == TOOL_VERSION
    assert written["jaccard_threshold"] == 0.5
    assert written["delta"]["verdict"] == VERDICT_KNOWN_SCREEN


# ---------------------------------------------------------------------------
# Test 16: invalid run_id (slash / backslash / colon) — no report written
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_run_id", ["bad/id", "bad\\id", "bad:id", "bad*id", "bad?id"])
def test_invalid_run_id_rejects_and_writes_no_report(tmp_path, bad_run_id):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={"run_id": bad_run_id},
        catalog_screens={sid: entry},
    )

    with pytest.raises(ValueError):
        cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)

    # output_dir 가 만들어졌더라도 report 파일은 없어야 한다
    if output_dir.exists():
        assert list(output_dir.glob("*.json")) == []


# ---------------------------------------------------------------------------
# Test 17: same current_activity 후보 여러 개 → highest J 선택
# ---------------------------------------------------------------------------


def test_multiple_same_activity_candidates_highest_jaccard(tmp_path):
    # candidate1: J=2/4=0.5 with manifest, candidate2: J=3/3=1.0 (more overlap)
    activity = "com.example.test/com.example.test.MainActivity"
    sid1, entry1 = _make_screen_entry(
        current_activity=activity,
        xml_sha256="xml_LOW",
        visible_texts=["B", "C", "Z"],  # vs manifest [A,B,C,D]: ∩={B,C}, ∪={A,B,C,D,Z} → 2/5=0.4
    )
    sid2, entry2 = _make_screen_entry(
        current_activity=activity,
        xml_sha256="xml_HIGH",
        visible_texts=["A", "B", "C"],  # vs [A,B,C,D]: ∩={A,B,C}, ∪={A,B,C,D} → 3/4=0.75
    )

    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"xml_sha256": "xml_NEW"},
            "text_model": {"visible_texts_from_dump": ["A", "B", "C", "D"]},
        },
        catalog_screens={sid1: entry1, sid2: entry2},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_CHANGED_TEXTS
    assert report["delta"]["baseline_screen_id"] == sid2
    assert report["delta"]["jaccard"] == 0.75


# ---------------------------------------------------------------------------
# Test 18: Jaccard 동률 → lex-smallest screen_id 선택
# ---------------------------------------------------------------------------


def test_jaccard_tie_break_lex_smallest_screen_id(tmp_path):
    """동일 visible_texts(=동일 J) 두 후보 — xml_sha 만 다름 → screen_id lex 비교."""
    activity = "com.example.test/com.example.test.MainActivity"
    # 두 candidate 의 visible_texts 가 동일 → manifest 와의 J 가 동일
    # xml_sha 만 다르게 하여 screen_id 가 달라지도록
    sid_a, entry_a = _make_screen_entry(
        current_activity=activity,
        xml_sha256="xml_OTHER_111",
        visible_texts=["A", "B"],
    )
    sid_b, entry_b = _make_screen_entry(
        current_activity=activity,
        xml_sha256="xml_OTHER_222",
        visible_texts=["A", "B"],
    )

    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"xml_sha256": "xml_NEW"},
            "text_model": {"visible_texts_from_dump": ["A", "B"]},
        },
        catalog_screens={sid_a: entry_a, sid_b: entry_b},
    )

    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_CHANGED_TEXTS
    expected = min(sid_a, sid_b)
    assert report["delta"]["baseline_screen_id"] == expected


# ---------------------------------------------------------------------------
# Test 19: 반복 cmd_delta — generated_at 제외 semantic equality
# ---------------------------------------------------------------------------


def test_repeated_cmd_delta_semantic_equal_except_generated_at(tmp_path):
    sid, entry = _make_screen_entry(
        current_activity="com.example.test/com.example.test.MainActivity",
        xml_sha256="xml_aaa",
        visible_texts=["Alpha"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path, catalog_screens={sid: entry}
    )

    r1 = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    r2 = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)

    a = {k: v for k, v in r1.items() if k != "generated_at"}
    b = {k: v for k, v in r2.items() if k != "generated_at"}
    assert a == b


# ---------------------------------------------------------------------------
# Test 20: CLI required flags — argparse error
# ---------------------------------------------------------------------------


def test_cli_requires_catalog_dir_and_manifest():
    """python -m src.cli catalog delta 실행 시 필수 플래그 누락 → exit 2."""
    repo_root = Path(__file__).parent.parent
    venv_python = repo_root / "venv" / "Scripts" / "python.exe"
    py = str(venv_python) if venv_python.exists() else sys.executable

    result = subprocess.run(
        [py, "-m", "src.cli", "catalog", "delta"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "catalog-dir" in combined or "manifest" in combined


# ---------------------------------------------------------------------------
# Test 21: empty manifest visible_texts vs non-empty candidate → J=0 → new_screen
# ---------------------------------------------------------------------------


def test_empty_manifest_texts_vs_non_empty_candidate_is_new_screen(tmp_path):
    activity = "com.example.test/com.example.test.MainActivity"
    sid, entry = _make_screen_entry(
        current_activity=activity,
        xml_sha256="xml_OTHER",
        visible_texts=["A", "B", "C"],
    )
    catalog_dir, manifest_path, output_dir, _ = _setup_basic(
        tmp_path,
        manifest_overrides={
            "screen": {"xml_sha256": "xml_NEW"},
            "text_model": {"visible_texts_from_dump": ["just_one"]},
        },
        catalog_screens={sid: entry},
    )
    # ∩=∅, ∪={A,B,C,just_one}=4 → J=0.0 < 0.5 → new_screen
    report = cmd_delta(catalog_dir, manifest_path, output_dir=output_dir, threshold=0.5)
    assert report["delta"]["verdict"] == VERDICT_NEW_SCREEN
