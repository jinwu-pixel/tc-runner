"""Tests for tools/redaction_gate.py (independent content + path gate, OFFLINE).

No device, no git: the gate only reads the given paths and reports findings.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATH = _ROOT / "tools" / "redaction_gate.py"
_spec = importlib.util.spec_from_file_location("redaction_gate", _PATH)
rg = importlib.util.module_from_spec(_spec)
sys.modules["redaction_gate"] = rg
_spec.loader.exec_module(rg)


def _write(p: Path, text: str) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_clean_redacted_json_passes(tmp_path):
    p = _write(tmp_path / "probes" / "clean.json",
               json.dumps({"device": {"build": "Z0604U", "ip": "<IPV4_1>", "mac": "<MAC_1>"}}))
    result = rg.run_gate([p])
    assert result["verdict"] == "PASS"
    assert result["findings"] == []


def test_clean_redacted_md_passes(tmp_path):
    p = _write(tmp_path / "b.md", "# baseline\n- ip: <IPV4_1> mac <MAC_1> build Z0604U\n")
    assert rg.run_gate([p])["verdict"] == "PASS"


def test_plaintext_pii_json_fails(tmp_path):
    p = _write(tmp_path / "leak.json", json.dumps({"device": {"ip": "192.0.0.4"}}))
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "IPV4" for f in result["findings"])


def test_plaintext_pii_md_fails(tmp_path):
    p = _write(tmp_path / "leak.md", "IP 주소 192.0.0.4 남음\n")
    assert rg.run_gate([p])["verdict"] == "FAIL"


def test_raw_xml_blocked_regardless_of_content(tmp_path):
    # clean content, but under a raw/ dir -> path policy blocks it
    p = _write(tmp_path / "catalog" / "raw" / "20260608T0Z" / "x.xml", "<node text='ok'/>")
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "PATH_POLICY" for f in result["findings"])


def test_keymap_blocked_regardless_of_content(tmp_path):
    p = _write(tmp_path / "anchors" / "_redaction_keymap.json", json.dumps({"by_kind": {}}))
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "PATH_POLICY" for f in result["findings"])


def test_mixed_paths_reports_only_offenders(tmp_path):
    clean = _write(tmp_path / "probes" / "ok.json", json.dumps({"ip": "<IPV4_1>"}))
    leaked = _write(tmp_path / "probes" / "bad.json", json.dumps({"ip": "192.0.0.4"}))
    keymap = _write(tmp_path / "raw" / "r" / "_redaction_keymap.json", "{}")
    result = rg.run_gate([clean, leaked, keymap])
    assert result["verdict"] == "FAIL"
    offenders = {f["path"] for f in result["findings"]}
    assert all("ok.json" not in op for op in offenders)        # clean file not reported
    assert any("bad.json" in op for op in offenders)
    assert any("_redaction_keymap.json" in op for op in offenders)


def test_missing_path_fails_safely(tmp_path):
    result = rg.run_gate([str(tmp_path / "nope.json")])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "MISSING_PATH" for f in result["findings"])


def test_unsupported_extension_not_silently_skipped(tmp_path):
    # a genuinely unsupported, non-image binary type stays UNSUPPORTED_EXT
    # (image binaries get their own BINARY_IMAGE kind — see below)
    p = _write(tmp_path / "blob.bin", "not scannable")
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "UNSUPPORTED_EXT" for f in result["findings"])


def test_windows_backslash_raw_path_blocked():
    # path gate is string-based; backslashes normalize -> a raw/ segment still blocks
    findings = rg.scan_path("work\\catalog\\raw\\run\\f.json")
    assert any(f["kind"] == "PATH_POLICY" for f in findings)


def test_exit_codes_pass_and_fail(tmp_path):
    clean = _write(tmp_path / "ok.json", json.dumps({"ip": "<IPV4_1>"}))
    leaked = _write(tmp_path / "bad.json", json.dumps({"ip": "192.0.0.4"}))
    assert rg.main([clean]) == 0
    assert rg.main([leaked]) == 1


def test_finding_dict_has_required_fields(tmp_path):
    p = _write(tmp_path / "leak.json", json.dumps({"ip": "192.0.0.4"}))
    f = rg.run_gate([p])["findings"][0]
    for key in ("path", "kind", "severity", "location", "message"):
        assert key in f, key


# --- T5 hardening: malformed JSON / read error / directory input ------------
# A commit-candidate JSON must be valid JSON (no raw-text fallback); an
# unreadable/undecodable file and a directory must FAIL rather than slip through.

def test_malformed_clean_json_is_invalid_json(tmp_path):
    p = _write(tmp_path / "broken.json", "{ not valid json")   # no PII, but malformed
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "INVALID_JSON" for f in result["findings"])


def test_malformed_json_with_pii_still_invalid_json(tmp_path):
    p = _write(tmp_path / "broken2.json", '{"ip": 192.0.0.4')   # malformed + PII-looking
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "INVALID_JSON" for f in result["findings"])


def test_read_or_decode_error_fails(tmp_path):
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xff\xfe\x00\x01 not utf-8")               # invalid UTF-8
    result = rg.run_gate([str(p)])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "READ_ERROR" for f in result["findings"])


def test_plain_directory_input_fails(tmp_path):
    d = tmp_path / "somedir"
    d.mkdir()
    result = rg.run_gate([str(d)])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "INVALID_PATH" for f in result["findings"])


def test_raw_directory_input_is_path_policy(tmp_path):
    d = tmp_path / "catalog" / "raw" / "run"
    d.mkdir(parents=True)
    result = rg.run_gate([str(d)])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "PATH_POLICY" for f in result["findings"])


# --- .csv content support + binary-image policy (gate extension) ------------
# .csv is text → content-scannable (same residual_scan as MD/TXT). Image
# binaries (.png/.jpg/...) cannot be content-scanned for residual PII, so a
# commit-candidate image FAILs with a dedicated BINARY_IMAGE kind (screenshots
# are local-carry only per the redaction policy — committed text artifacts only).

def test_clean_redacted_csv_passes(tmp_path):
    p = _write(tmp_path / "probes" / "clean.csv",
               "id,ip,mac\n1,<IPV4_1>,<MAC_1>\n2,<IPV4_2>,<MAC_2>\n")
    result = rg.run_gate([p])
    assert result["verdict"] == "PASS"
    assert result["findings"] == []


def test_plaintext_pii_csv_fails(tmp_path):
    p = _write(tmp_path / "leak.csv", "id,ip\n1,192.0.0.4\n")
    result = rg.run_gate([p])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "IPV4" for f in result["findings"])


def test_png_image_fails_as_binary_local_only(tmp_path):
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n fake png bytes")
    result = rg.run_gate([str(p)])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "BINARY_IMAGE" for f in result["findings"])


def test_jpg_image_fails_as_binary_local_only(tmp_path):
    p = tmp_path / "shot.jpg"
    p.write_bytes(b"\xff\xd8\xff fake jpg")
    result = rg.run_gate([str(p)])
    assert result["verdict"] == "FAIL"
    assert any(f["kind"] == "BINARY_IMAGE" for f in result["findings"])
