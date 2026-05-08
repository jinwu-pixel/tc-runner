"""Tests for tools/synthetic_delta_measure.py (PR 7A required suite).

Covers metric extraction, verdict classification on the 3 fixtures, JSON
output schema, and the read-only invariant (no file write, no fixture
mutation).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_TOOL_PATH = _ROOT / "tools" / "synthetic_delta_measure.py"
_spec = importlib.util.spec_from_file_location("synthetic_delta_measure", _TOOL_PATH)
sdm = importlib.util.module_from_spec(_spec)
sys.modules["synthetic_delta_measure"] = sdm
_spec.loader.exec_module(sdm)

_FIXTURE_ROOT = _ROOT / "tests" / "fixtures" / "synthetic_delta"


def test_tool_version_constants():
    assert sdm.SCHEMA_VERSION == 1
    assert sdm.TOOL_VERSION == "pr7-delta-measurement-v1"
    assert sdm.MIN_TEXT_COUNT == 3


def test_extract_visible_texts_from_minimal_xml():
    root = ET.fromstring(
        '<hierarchy>'
        '<node text="홈" />'
        '<node content-desc="재생 버튼" />'
        '<node text="" />'
        '<node text="  " />'
        '<node />'
        '</hierarchy>'
    )
    texts = sdm.extract_visible_texts(root)
    assert texts == {"홈", "재생 버튼"}


def test_jaccard_identical_returns_one():
    assert sdm.jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint_returns_zero():
    assert sdm.jaccard({"a", "b"}, {"c", "d"}) == 0.0


def test_jaccard_both_empty_returns_one():
    assert sdm.jaccard(set(), set()) == 1.0


def test_added_removed_texts_correct():
    before = b'<hierarchy><node text="A"/><node text="B"/><node text="C"/></hierarchy>'
    after = b'<hierarchy><node text="A"/><node text="C"/><node text="D"/></hierarchy>'
    result = sdm.measure_pair(before, after, target_text="A")
    assert result["visible_texts"]["added"] == ["D"]
    assert result["visible_texts"]["removed"] == ["B"]


def test_identical_snapshot_verdict_stable():
    result = sdm.measure_fixture(_FIXTURE_ROOT / "identical_snapshot")
    assert result["verdict"] == "stable"
    assert result["match"] is True
    assert result["xml_sha256"]["equal"] is True
    assert result["visible_texts"]["added"] == []
    assert result["visible_texts"]["removed"] == []


def test_text_only_change_verdict_meaningful_delta():
    result = sdm.measure_fixture(_FIXTURE_ROOT / "text_only_change")
    assert result["verdict"] == "meaningful_delta"
    assert result["match"] is True
    assert result["xml_sha256"]["equal"] is False
    assert result["visible_texts"]["added"]
    assert result["visible_texts"]["removed"]
    assert result["target"]["before"] is True
    assert result["target"]["after"] is True


def test_insufficient_evidence_verdict_insufficient():
    result = sdm.measure_fixture(_FIXTURE_ROOT / "insufficient_evidence")
    assert result["verdict"] == "insufficient"
    assert result["match"] is True
    assert result["visible_texts"]["before_count"] < sdm.MIN_TEXT_COUNT
    assert result["visible_texts"]["after_count"] < sdm.MIN_TEXT_COUNT


def test_json_output_schema_via_cli():
    proc = subprocess.run(
        [
            sys.executable,
            str(_TOOL_PATH),
            "--fixture-dir",
            str(_FIXTURE_ROOT / "identical_snapshot"),
        ],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    data = json.loads(proc.stdout.decode("utf-8"))
    assert data["schema_version"] == 1
    assert data["tool_version"] == "pr7-delta-measurement-v1"
    assert data["verdict"] == "stable"
    assert "xml_sha256" in data
    assert "visible_texts" in data
    assert "target" in data
    assert data["fixture"]["name"] == "identical_snapshot"
    assert data["match"] is True


def test_no_generated_artifact_written_by_cli(tmp_path):
    before = set(p.name for p in tmp_path.iterdir())
    proc = subprocess.run(
        [
            sys.executable,
            str(_TOOL_PATH),
            "--fixture-dir",
            str(_FIXTURE_ROOT / "text_only_change"),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0
    after = set(p.name for p in tmp_path.iterdir())
    assert after == before


def test_read_only_invariant_no_fixture_mutation():
    fixture = _FIXTURE_ROOT / "identical_snapshot"
    before_bytes = (fixture / "before.xml").read_bytes()
    after_bytes = (fixture / "after.xml").read_bytes()
    expected_bytes = (fixture / "expected.json").read_bytes()
    sdm.measure_fixture(fixture)
    assert (fixture / "before.xml").read_bytes() == before_bytes
    assert (fixture / "after.xml").read_bytes() == after_bytes
    assert (fixture / "expected.json").read_bytes() == expected_bytes


def test_measure_pair_with_no_target():
    before = b'<hierarchy><node text="A"/><node text="B"/><node text="C"/></hierarchy>'
    after = b'<hierarchy><node text="A"/><node text="B"/><node text="C"/></hierarchy>'
    result = sdm.measure_pair(before, after, target_text=None)
    assert result["verdict"] == "stable"
    assert result["target"]["text"] is None
    assert result["target"]["before"] is False
    assert result["target"]["after"] is False
