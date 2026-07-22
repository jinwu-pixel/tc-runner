import hashlib
import json
from pathlib import Path

import yaml

import src.cli as cli
from scripts import contract_drift_ledger as ledger
from src.tc_loader import load_tc


ROOT = Path(__file__).resolve().parents[1]
THOR2J_SMOKE_PATHS = (
    ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_01_app_launch.yaml",
    ROOT / "THOR2_J - Settings" / "SETTINGS_SMOKE_02_scroll_more_menu.yaml",
)


def _source_snapshot(path: Path) -> tuple[str, int]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns


def _semantic_projection(tc: dict) -> dict:
    steps = tc.get("steps", [])
    return {
        "tc_name": tc.get("tc_name", tc.get("name")),
        "step_count": len(steps),
        "steps": [
            {
                "action": step.get("action"),
                "command": step.get("command"),
                "target": step.get("target"),
                "duration": step.get("duration"),
                "timeout": step.get("timeout"),
            }
            for step in steps
        ],
        "metadata": tc.get("metadata"),
    }


def test_contract_ledger_counts_existing_thor2j_smoke_two():
    group_rows = [
        row
        for row in ledger.scan_corpora()
        if row["actor_kind"] == "corpus"
        and row["corpus"] == "thor2j_settings_smoke"
        and row["variant"] == "group_count"
    ]

    assert len(group_rows) == 1
    observed = json.loads(group_rows[0]["normalized_json"])
    assert observed == {"file_count": 2, "primary": True}


def test_thor2j_smoke_top_level_is_already_tc_name():
    for path in THOR2J_SMOKE_PATHS:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        assert "tc_name" in raw, path
        assert "name" not in raw, path


def test_thor2j_smoke_legacy_and_canonical_semantics_match():
    for path in THOR2J_SMOKE_PATHS:
        legacy = load_tc(path, contract_mode="legacy")
        canonical = load_tc(path, contract_mode="canonical")

        assert _semantic_projection(legacy) == _semantic_projection(canonical), path


def test_thor2j_smoke_source_hashes_unchanged():
    before = {path: _source_snapshot(path) for path in THOR2J_SMOKE_PATHS}

    for path in THOR2J_SMOKE_PATHS:
        _semantic_projection(load_tc(path, contract_mode="legacy"))
        _semantic_projection(load_tc(path, contract_mode="canonical"))

    after = {path: _source_snapshot(path) for path in THOR2J_SMOKE_PATHS}
    assert after == before


def test_thor2j_smoke_canonical_host_preflight_passes_without_adb(monkeypatch):
    adb_calls = []

    def forbidden_adb():
        adb_calls.append("constructed")
        raise AssertionError("host preflight must not construct ADB")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    report = cli.host_preflight(list(THOR2J_SMOKE_PATHS), "canonical")

    assert report.passed is True
    assert [verdict.path for verdict in report.verdicts] == list(
        THOR2J_SMOKE_PATHS
    )
    assert all(verdict.passed for verdict in report.verdicts)
    assert all(verdict.reasons == () for verdict in report.verdicts)
    assert [path for path, _tc in report.loaded_tcs] == list(
        THOR2J_SMOKE_PATHS
    )
    assert adb_calls == []


def test_thor2j_smoke_canonical_host_preflight_rejects_injected_copy_without_adb(
    tmp_path, monkeypatch
):
    source = THOR2J_SMOKE_PATHS[0]
    source_before = _source_snapshot(source)
    injected = yaml.safe_load(source.read_text(encoding="utf-8"))
    injected["metadata"]["runnable"] = False
    injected["metadata"]["runnable_reason"] = ["FIXTURE_REQUIRED"]
    candidate = tmp_path / source.name
    candidate.write_text(
        yaml.safe_dump(injected, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    adb_calls = []

    def forbidden_adb():
        adb_calls.append("constructed")
        raise AssertionError("host preflight must not construct ADB")

    monkeypatch.setattr(cli, "ADB", forbidden_adb)

    report = cli.host_preflight([candidate], "canonical")

    assert report.passed is False
    assert report.verdicts[0].passed is False
    assert report.verdicts[0].reasons == (
        "NOT_RUNNABLE",
        "RUNNABLE_REASON_PRESENT",
    )
    assert report.loaded_tcs == ()
    assert adb_calls == []
    assert _source_snapshot(source) == source_before
