"""Redaction module — Task 1 (module skeleton + layering guard).

Pure, device-independent PII redaction for menu-tree v1.2 phone/network
issue-probe artifacts. See
docs/superpowers/plans/2026-06-08-redaction-residual-scan.md (Task 1).
"""
from __future__ import annotations

import ast
import inspect
import json
import pathlib

import pytest

from src import redaction as rd


def test_module_surface_exists():
    for name in ("Span", "Finding", "KeyMap", "detect", "redact", "redact_text",
                 "residual_scan", "path_policy_findings"):
        assert hasattr(rd, name), name


def test_redaction_does_not_import_scripts_runner_cli():
    tree = ast.parse(inspect.getsource(rd))
    mods = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mods.append(n.module or "")
    forbidden = {"scripts", "cli", "action_runner", "reporter", "adb",
                 "mmi_converter", "preflight", "app_explorer"}
    for m in mods:
        segs = set(m.split("."))
        assert not (segs & forbidden), (m, mods)


# --- Task 2: network identifier detection + tokenization -------------------

@pytest.mark.parametrize("text,kind,val", [
    ("IP 주소 192.0.0.4", "IPV4", "192.0.0.4"),
    ("9c:1e:ce:0c:36:e0", "MAC", "9c:1e:ce:0c:36:e0"),
])
def test_detect_ipv4_and_mac(text, kind, val):
    spans = rd.detect(text)
    assert any(s.kind == kind and s.value == val and s.klass == "T" for s in spans), spans


def test_detect_ipv6_full_form():
    v = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    spans = rd.detect(v)
    assert any(s.kind == "IPV6" and s.value == v and s.klass == "T" for s in spans), spans


def test_detect_ipv6_compressed_form():
    v = "2001:4430:41c7:b900::29e:4be2"
    spans = rd.detect(v)
    assert any(s.kind == "IPV6" and s.value == v and s.klass == "T" for s in spans), spans


def test_mac_not_misdetected_as_ipv6():
    spans = rd.detect("9c:1e:ce:0c:36:e0")
    assert {s.kind for s in spans} == {"MAC"}, spans


def test_redact_text_tokenizes_network_ids():
    km = rd.KeyMap()
    out = rd.redact_text("v4 192.0.0.4 mac 9c:1e:ce:0c:36:e0", km)
    assert "192.0.0.4" not in out and "9c:1e:ce:0c:36:e0" not in out
    assert "<IPV4_1>" in out and "<MAC_1>" in out


def test_keymap_same_value_same_token():
    km = rd.KeyMap()
    a = rd.redact_text("ip 192.0.0.4", km)
    b = rd.redact_text("again 192.0.0.4", km)
    assert "<IPV4_1>" in a and "<IPV4_1>" in b


def test_keymap_distinct_values_increment_in_document_order():
    km = rd.KeyMap()
    out = rd.redact_text("a 192.0.0.4 b 10.0.0.9", km)
    assert "<IPV4_1>" in out and "<IPV4_2>" in out
    assert out.index("<IPV4_1>") < out.index("<IPV4_2>")


# --- Task 3: identity ids (label-anchored, precedence) ---------------------

def test_imei_label_anchored_tokenized():
    out = rd.redact_text("IMEI 350000000000001", rd.KeyMap())
    assert "<IMEI_1>" in out and "350000000000001" not in out


def test_imsi_label_anchored_tokenized_not_imei():
    out = rd.redact_text("IMSI 450060000000001", rd.KeyMap())
    assert "<IMSI_1>" in out and "IMEI" not in out and "450060000000001" not in out


def test_iccid_label_anchored_tokenized():
    out = rd.redact_text("ICCID 8982000000000000001", rd.KeyMap())
    assert "<ICCID_1>" in out and "8982000000000000001" not in out


def test_msisdn_format_tokenized():
    out = rd.redact_text("전화번호 +821012345678", rd.KeyMap())
    assert "<MSISDN_1>" in out and "821012345678" not in out


def test_iccid_not_sliced_into_imsi_or_imei():
    spans = rd.detect("ICCID 8982000000000000001")
    assert {s.kind for s in spans} == {"ICCID"}, spans


@pytest.mark.parametrize("benign", [
    "순번 350000000000001",            # bare 15-digit, no identity label
    "2024-10-10",                       # date
    "27% 사용 - 23.37GB 사용 가능",     # capacity
    "16개 중 7개의 앱",                 # count
    "Android 버전 14",                 # version
])
def test_identity_no_false_positive(benign):
    assert rd.detect(benign) == [], rd.detect(benign)


def test_same_identity_value_same_token():
    km = rd.KeyMap()
    a = rd.redact_text("IMEI 350000000000001", km)
    b = rd.redact_text("again IMEI 350000000000001", km)
    assert "<IMEI_1>" in a and "<IMEI_1>" in b


# --- Task 4: operator numeric / MCCMNC (known KR PLMN set + label only) ----

def test_operator_numeric_label_tokenized():
    out = rd.redact_text("operator numeric 45006", rd.KeyMap())
    assert "<OPERATOR_NUMERIC_1>" in out and "45006" not in out


def test_operator_numeric_plmn_label():
    out = rd.redact_text("PLMN=45005", rd.KeyMap())
    assert "<OPERATOR_NUMERIC_1>" in out and "45005" not in out


def test_operator_numeric_same_value_same_token():
    km = rd.KeyMap()
    out = rd.redact_text("operator numeric 45006 / numeric 45006", km)
    assert out.count("<OPERATOR_NUMERIC_1>") == 2 and "<OPERATOR_NUMERIC_2>" not in out


def test_operator_numeric_distinct_values_document_order():
    out = rd.redact_text("operator numeric 45006, PLMN=45005", rd.KeyMap())
    assert "<OPERATOR_NUMERIC_1>" in out and "<OPERATOR_NUMERIC_2>" in out
    assert out.index("<OPERATOR_NUMERIC_1>") < out.index("<OPERATOR_NUMERIC_2>")


def test_operator_numeric_no_label_not_detected():
    assert not any(s.kind == "OPERATOR_NUMERIC" for s in rd.detect("45006"))


def test_operator_numeric_unknown_plmn_not_detected():
    assert not any(s.kind == "OPERATOR_NUMERIC" for s in rd.detect("operator numeric 45099"))


def test_operator_numeric_mccmnc_inside_imsi_not_sliced():
    spans = rd.detect("IMSI 450060000000001")
    assert {s.kind for s in spans} == {"IMSI"}, spans


@pytest.mark.parametrize("benign", [
    "27% 사용 - 23.37GB 사용 가능",
    "2024-10-10",
    "빌드 번호 AT-M140LZ0604U",
    "Android 버전 14",
    "16개 중 7개의 앱",
])
def test_operator_numeric_no_false_positive(benign):
    assert not any(s.kind == "OPERATOR_NUMERIC" for s in rd.detect(benign))


# --- Task 5: build fingerprint (full token) vs short build id (keep) -------

FP = "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260600S:user/release-keys"


def test_full_fingerprint_tokenized():
    out = rd.redact_text(f"fingerprint {FP}", rd.KeyMap())
    assert "<BUILD_FP_1>" in out and FP not in out


def test_build_fingerprint_label_line_tokenized():
    out = rd.redact_text(f"build fingerprint: {FP}", rd.KeyMap())
    assert "<BUILD_FP_1>" in out


def test_same_fingerprint_same_token():
    km = rd.KeyMap()
    out = rd.redact_text(f"a {FP} b {FP}", km)
    assert out.count("<BUILD_FP_1>") == 2 and "<BUILD_FP_2>" not in out


@pytest.mark.parametrize("keep", ["build_id Z0604U", "RY07260600S", "AT-M140LZ0604U"])
def test_short_build_id_kept(keep):
    assert not any(s.kind == "BUILD_FP" for s in rd.detect(keep))
    assert keep.split()[-1] in rd.redact_text(keep, rd.KeyMap())


@pytest.mark.parametrize("benign", [
    "Android 버전 14",
    "2024-10-10",
    "16개 중 7개의 앱",
    "27% 사용 - 23.37GB",
])
def test_build_fp_no_false_positive(benign):
    assert not any(s.kind == "BUILD_FP" for s in rd.detect(benign))


def test_fingerprint_build_id_part_not_separately_tokenized():
    spans = rd.detect(FP)
    assert {s.kind for s in spans} == {"BUILD_FP"}, spans
    assert spans[0].value == FP


# --- Task 6: D-class drop (APN credential, first call date) ----------------

def test_apn_user_in_context_dropped():
    out = rd.redact_text("apn user foo", rd.KeyMap())
    assert "<REDACTED:apn_user>" in out and "foo" not in out


def test_password_dropped_strong():
    out = rd.redact_text("password=secret", rd.KeyMap())
    assert "<REDACTED:apn_password>" in out and "secret" not in out


def test_apn_password_spaced_dropped():
    out = rd.redact_text("apn password secret", rd.KeyMap())
    assert "<REDACTED:apn_password>" in out and "secret" not in out


def test_authtype_dropped():
    out = rd.redact_text("authtype=pap", rd.KeyMap())
    assert "<REDACTED:apn_auth>" in out and "pap" not in out


def test_first_call_date_dash_dropped():
    out = rd.redact_text("첫 통화 개시일 2024-10-10", rd.KeyMap())
    assert "<REDACTED:first_call_date>" in out and "2024-10-10" not in out


def test_first_call_date_dot_dropped():
    out = rd.redact_text("개통일: 2024.10.10", rd.KeyMap())
    assert "<REDACTED:first_call_date>" in out and "2024.10.10" not in out


def test_bare_user_without_apn_context_not_credential():
    assert not any(s.kind == "APN_CRED" for s in rd.detect("user=admin"))


def test_general_date_not_first_call_date():
    assert not any(s.kind == "FIRST_CALL_DATE" for s in rd.detect("2026-06-08"))


def test_author_word_not_credential():
    assert not any(s.kind == "APN_CRED" for s in rd.detect("author John"))


@pytest.mark.parametrize("benign", [
    "build_id Z0604U",
    "Android 버전 14",
    "16개 중 7개의 앱",
    "27% 사용 - 23.37GB",
])
def test_dclass_no_false_positive(benign):
    assert not any(s.klass == "D" for s in rd.detect(benign)), rd.detect(benign)


def test_dclass_has_no_numbering_and_no_token_map():
    km = rd.KeyMap()
    out = rd.redact_text("password=secret and password=secret", km)
    assert out.count("<REDACTED:apn_password>") == 2
    assert "_1>" not in out
    assert "APN_CRED" not in km._by_kind


# --- Task 7: false-positive negative sweep ---------------------------------

_FP_NEGATIVE_CORPUS = [
    "27% 사용 - 23.37GB",
    "2024-10-10",
    "count 365 elements, 49 scroll passes",
    "version 1.2.3",
    "Z0604U / RY07260600S / AT-M140LZ0604U",
    "operator 45099",                                  # known set 밖
    "45006",                                           # label 없음
    "user=admin",                                      # APN 맥락 없음
    "author=someone",
    "content://telephony/carriers",                    # URI 자체는 credential 아님
    "com.android.settings/.Settings$MyDeviceInfoActivity",
    "Settings$PrivacyDashboardActivity",
    "menu_tree_baseline_20260604T102316Z.json",
    "run_id 20260604T102316Z",
    "screen_count=17 reached=15 focus_mismatch=2",
]


@pytest.mark.parametrize("text", _FP_NEGATIVE_CORPUS)
def test_false_positive_corpus_detect_empty(text):
    assert rd.detect(text) == [], rd.detect(text)


@pytest.mark.parametrize("text", _FP_NEGATIVE_CORPUS)
def test_false_positive_corpus_redact_unchanged(text):
    assert rd.redact_text(text, rd.KeyMap()) == text


def test_combined_report_text_no_detection():
    report = "\n".join(_FP_NEGATIVE_CORPUS)
    assert rd.detect(report) == [], rd.detect(report)


def test_mixed_text_redacts_positives_keeps_analysis():
    km = rd.KeyMap()
    text = ("device_info IP 주소 192.0.0.4 build fingerprint " + FP
            + " screen_count=17 reached=15 focus_mismatch=2")
    out = rd.redact_text(text, km)
    assert "192.0.0.4" not in out and FP not in out          # positives gone
    assert "<IPV4_1>" in out and "<BUILD_FP_1>" in out
    assert "screen_count=17 reached=15 focus_mismatch=2" in out   # analysis preserved
    assert "device_info" in out and "IP 주소" in out


# --- Task 8: KeyMap serialization + redact(obj) walker --------------------

def test_keymap_roundtrip_same_value_same_token():
    km = rd.KeyMap()
    rd.redact({"ip": "192.0.0.4"}, km)
    km2 = rd.KeyMap.from_dict(km.to_dict())
    out, _ = rd.redact({"ip2": "192.0.0.4"}, km2)
    assert out["ip2"] == "<IPV4_1>"


def test_keymap_roundtrip_counter_continues():
    km = rd.KeyMap()
    rd.redact({"a": "192.0.0.4"}, km)
    km2 = rd.KeyMap.from_dict(km.to_dict())
    out, _ = rd.redact({"b": "10.0.0.9"}, km2)
    assert out["b"] == "<IPV4_2>"


def test_redact_nested_dict_list_values_only():
    obj = {"ko": ["IP 주소", "192.0.0.4"], "mac": "9c:1e:ce:0c:36:e0",
           "n": 17, "ok": True, "x": None}
    out, _ = rd.redact(obj, rd.KeyMap())
    assert out["ko"][0] == "IP 주소"          # label kept
    assert out["ko"][1] == "<IPV4_1>"
    assert out["mac"] == "<MAC_1>"
    assert out["n"] == 17 and out["ok"] is True and out["x"] is None


def test_redact_does_not_change_dict_keys():
    obj = {"192.0.0.4": "value"}               # an IP as a KEY must stay verbatim
    out, _ = rd.redact(obj, rd.KeyMap())
    assert "192.0.0.4" in out


def test_dclass_value_not_stored_in_keymap():
    km = rd.KeyMap()
    rd.redact({"pw": "password=secret"}, km)
    assert "APN_CRED" not in km.to_dict().get("by_kind", {})


def test_two_objects_share_tokens_with_same_keymap():
    km = rd.KeyMap()
    a, _ = rd.redact({"ip": "192.0.0.4", "imei": "IMEI 350000000000001"}, km)
    b, _ = rd.redact({"ip": "192.0.0.4", "imei": "IMEI 350000000000001"}, km)
    assert a["ip"] == b["ip"] == "<IPV4_1>"
    assert a["imei"] == b["imei"]


def test_different_keymaps_restart_numbering():
    a, _ = rd.redact({"ip": "192.0.0.4"}, rd.KeyMap())
    b, _ = rd.redact({"ip": "192.0.0.4"}, rd.KeyMap())
    assert a["ip"] == b["ip"] == "<IPV4_1>"


def test_redact_device_info_fixture():
    p = pathlib.Path(__file__).parent / "fixtures" / "redaction" / "device_info_sample.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    out, _ = rd.redact(obj, rd.KeyMap())
    flat = json.dumps(out, ensure_ascii=False)
    assert "192.0.0.4" not in flat and "<IPV4_1>" in flat
    assert "9c:1e:ce:0c:36:e0" not in flat and "<MAC_1>" in flat
    assert FP not in flat and "<BUILD_FP_1>" in flat
    assert "Z0604U" in flat                     # short build id kept as analysis context


# --- Task 9: residual_scan content gate ------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("fallback IP 주소 192.0.0.4 leaked", "IPV4"),
    ("mac 9c:1e:ce:0c:36:e0", "MAC"),
    ("IMEI 350000000000001", "IMEI"),
    ("IMSI 450060000000001", "IMSI"),
    ("ICCID 8982000000000000001", "ICCID"),
    ("전화번호 +821012345678", "MSISDN"),
    ("operator numeric 45006", "OPERATOR_NUMERIC"),
    ("fingerprint " + FP, "BUILD_FP"),
    ("password=secret", "APN_CRED"),
    ("첫 통화 개시일 2024-10-10", "FIRST_CALL_DATE"),
])
def test_residual_scan_flags_plaintext_pii(text, kind):
    findings = rd.residual_scan(text)
    assert findings and all(f.severity == "high" for f in findings)
    assert any(f.kind == kind for f in findings)


def test_residual_scan_finding_contract():
    f = rd.residual_scan("IP 주소 192.0.0.4")[0]
    assert f.kind == "IPV4"
    assert isinstance(f.message, str) and f.message
    assert isinstance(f.location, str)
    assert "192.0.0.4" in f.excerpt
    assert f.severity == "high"


@pytest.mark.parametrize("placeholder", [
    "<IPV4_1>", "<MAC_1>", "<IMEI_1>", "<BUILD_FP_1>",
    "<REDACTED:apn_password>", "<REDACTED:first_call_date>",
])
def test_residual_scan_ignores_placeholders(placeholder):
    assert rd.residual_scan(placeholder) == []


@pytest.mark.parametrize("text", _FP_NEGATIVE_CORPUS)
def test_residual_scan_no_finding_on_fp_corpus(text):
    assert rd.residual_scan(text) == []


def test_residual_scan_recurses_dict_list():
    leaked = {"a": ["ok", "IP 주소 192.0.0.4"], "b": {"c": "mac 9c:1e:ce:0c:36:e0"}}
    kinds = {f.kind for f in rd.residual_scan(leaked)}
    assert kinds == {"IPV4", "MAC"}


def test_residual_scan_clean_redacted_object_no_findings():
    p = pathlib.Path(__file__).parent / "fixtures" / "redaction" / "device_info_sample.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    out, _ = rd.redact(obj, rd.KeyMap())
    assert rd.residual_scan(out) == []


def test_residual_scan_location_points_into_structure():
    f = rd.residual_scan({"device": {"ip": "192.0.0.4"}})[0]
    assert "device" in f.location and "ip" in f.location


# --- Task 10: path policy gate ---------------------------------------------

@pytest.mark.parametrize("path", [
    "catalog/raw/20260608T000000Z/settings_d1_apn.xml",
    "catalog/raw/20260608T000000Z/_redaction_keymap.json",
    "catalog/raw/20260608T000000Z/anything.txt",
    "THOR2_K - Settings/catalog/_raw_calculator.xml",
    "some/dir/_redaction_keymap.json",
])
def test_path_policy_flags_forbidden(path):
    findings = rd.path_policy_findings([path])
    assert findings, path
    assert findings[0].kind == "PATH_POLICY" and findings[0].severity == "high"
    assert findings[0].location == path


@pytest.mark.parametrize("path", [
    "catalog/anchors/apn_lgu.json",
    "catalog/probes/debugscreen.json",
    "catalog/MENU_TREE_RUNS.md",
    "RESULT_2026-06-08.md",
    "catalog/digest_2026-06-08.md",
    "tests/fixtures/redaction/device_info_sample.json",
])
def test_path_policy_allows_redacted_sidecars(path):
    assert rd.path_policy_findings([path]) == [], path


def test_path_policy_finding_message_mentions_reason():
    f = rd.path_policy_findings(["catalog/raw/20260608/x.xml"])[0]
    msg = f.message.lower()
    assert ("raw" in msg or "keymap" in msg) and "forbidden" in msg
    assert f.excerpt


def test_path_policy_mixed_only_forbidden_flagged():
    paths = [
        "catalog/anchors/x.json",
        "catalog/raw/20260608/leak.xml",
        "catalog/probes/y.json",
        "catalog/raw/20260608/_redaction_keymap.json",
        "RESULT_2026-06-08.md",
    ]
    flagged = {f.location for f in rd.path_policy_findings(paths)}
    assert flagged == {
        "catalog/raw/20260608/leak.xml",
        "catalog/raw/20260608/_redaction_keymap.json",
    }


def test_path_policy_windows_backslash():
    findings = rd.path_policy_findings(["catalog\\raw\\20260608\\settings.xml"])
    assert findings and findings[0].kind == "PATH_POLICY"


def test_path_policy_separate_from_content_scan():
    # residual_scan never judges paths; path_policy never judges content.
    assert rd.residual_scan("catalog/raw/x.xml") == []
    assert rd.path_policy_findings(["clean text 192.0.0.4"]) == []
