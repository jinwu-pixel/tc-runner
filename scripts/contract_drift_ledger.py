#!/usr/bin/env python3
"""Slice 0.5 — measure-first contract drift ledger.

설계 source: docs/superpowers/specs/2026-07-14-canonical-execution-contract-design.md §6.
실제 함수 경계를 host-only fake 의존성으로 probe 하여 producer/consumer 간
execution contract drift 를 결정론적 CSV/SUMMARY 로 기록한다.

- 소스/코퍼스 파일은 절대 수정하지 않는다 (read-only).
- 산출물에 wall-clock 이 들어가지 않는다 (byte-deterministic).
- exit: 0=scan 완료 / 1=--fail-on-blocking & blocking 존재 / 2=입력 read·parse 실패
  / 3=결정론·self-check invariant 실패.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402
from src.execution_contract import (  # noqa: E402
    derive_action_required,
    normalize_tc,
    validate_canonical_tc,
)

SCHEMA_VERSION = 1
TOOL_VERSION = "contract-drift-ledger-v4"
FIXTURE_VERSION = 4

CONSUMERS = ["schema", "validate_tc", "tc_loader", "action_runner"]
PRODUCERS = ["excel", "mmi"]
PRODUCER_MODES = ["legacy", "canonical"]

CSV_COLUMNS = [
    "schema_version", "fixture_id", "actor_kind", "actor", "producer",
    "consumer", "corpus", "source_path", "tc_name", "step_index", "action",
    "variant", "canonical_field", "observed_fields", "unit", "verdict",
    "finding_code", "normalized_json", "source_sha256",
]

CONFIRMED_DEFECT_BASELINE = {
    "EXCEL_SWIPE_ENDPOINT_MISSING": 2,
    "SHELL_RC_DISCARDED": 2,
}
EXPECTED_BLOCKING_COUNTS = {
    "ALIAS_CONFLICT": 6,
    "EXCEL_SWIPE_ENDPOINT_MISSING": 2,
    "PRODUCER_DOC_NONCANONICAL": 2,
    "SHELL_RC_DISCARDED": 2,
}

# 6 actor (4 consumer + 2 producer) — digest 입력 소스
ACTOR_SOURCE_FILES = {
    "schema": ["tc_step_schema.json"],
    "validate_tc": ["validate_tc.py", "src/execution_contract.py"],
    "tc_loader": ["src/tc_loader.py"],
    "action_runner": ["src/action_runner.py", "src/adb.py"],
    "excel": ["src/excel_converter.py"],
    "mmi": ["src/mmi_converter/compiler.py", "src/mmi_converter/exporter.py"],
}

# (name, kind, pattern-or-paths, primary)
CORPUS_GROUPS = [
    ("golden_tc_set", "glob", "golden_tc_set/*.yaml", True),
    ("exported_tc1", "glob", "exported_tc1/*.yaml", True),
    ("thor2j_settings_smoke", "paths", [
        "THOR2_J - Settings/SETTINGS_SMOKE_01_app_launch.yaml",
        "THOR2_J - Settings/SETTINGS_SMOKE_02_scroll_more_menu.yaml",
    ], True),
    ("tc_samples_legacy", "paths", ["tc_samples/simple_smoke_test.yaml"], True),
    ("thor2k_settings_smoke", "glob", "THOR2_K - Settings/SETTINGS_SMOKE_*.yaml", False),
]
PRIMARY_COUNTS = (3, 25, 2, 1)  # §6.4 locked regression expectation

SELECTOR_ACTIONS = {"tap_text", "verify_text", "verify_gone",
                    "tap_content_desc", "verify_content_desc"}

CANONICAL_METADATA = {
    "runnable": True, "tc_class": "FULL_AUTO",
    "execution_type": "AUTO", "manual_detail": "NONE",
}


class LedgerInputError(Exception):
    pass


# ─── 공용 헬퍼 ───

def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contract_findings(result) -> list[dict]:
    return [
        {
            "code": finding.code,
            "path": finding.path,
            "severity": finding.severity,
            "canonical_field": finding.canonical_field,
            "observed_field": finding.observed_field,
            "detail": finding.detail,
        }
        for finding in result.findings
    ]


def _contract_errors(result) -> list[str]:
    return [
        f"{finding.code} [{finding.path}]: {finding.detail}"
        for finding in result.findings
        if finding.severity == "ERROR"
    ]


def _validator_boundary(doc: dict, schema: dict):
    """Return shared-core evidence plus the actual validate_tc wrapper result."""
    import validate_tc as validator_module

    source = str(doc.get("tc_name") or doc.get("name") or "<memory>")
    normalized = normalize_tc(doc, source=source)
    core_errors = _contract_errors(normalized) + validate_canonical_tc(
        normalized.value, schema
    )
    wrapper_errors = validator_module.validate_tc(doc, schema)
    return normalized, core_errors, wrapper_errors


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _corpus_files(group) -> list[Path]:
    name, kind, spec, _primary = group
    if kind == "glob":
        files = sorted(REPO_ROOT.glob(spec), key=lambda p: p.as_posix())
    else:
        files = [REPO_ROOT / p for p in spec]
        for f in files:
            if not f.exists():
                raise LedgerInputError(f"corpus 파일 없음: {f}")
        files = sorted(files, key=lambda p: p.as_posix())
    return files


def iter_input_files() -> list[Path]:
    files = []
    for actor_files in ACTOR_SOURCE_FILES.values():
        files.extend(REPO_ROOT / f for f in actor_files)
    for group in CORPUS_GROUPS:
        files.extend(_corpus_files(group))
    return sorted(set(files), key=lambda p: p.as_posix())


def snapshot_inputs() -> dict[str, dict[str, int | str]]:
    """Capture content and timestamp state for every declared ledger input."""
    snapshot: dict[str, dict[str, int | str]] = {}
    for path in iter_input_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        snapshot[rel] = {
            "sha256": sha256_file(path),
            "mtime_ns": path.stat().st_mtime_ns,
        }
    return snapshot


def compute_input_digest(
    snapshot: dict[str, dict[str, int | str]] | None = None,
) -> str:
    state = snapshot if snapshot is not None else snapshot_inputs()
    h = hashlib.sha256()
    h.update(f"fixture_version:{FIXTURE_VERSION}\n".encode("utf-8"))
    for rel in sorted(state):
        h.update(f"{rel}:{state[rel]['sha256']}\n".encode("utf-8"))
    return h.hexdigest()


def _row(**kw) -> dict:
    row = {c: "-" for c in CSV_COLUMNS}
    row["schema_version"] = str(SCHEMA_VERSION)
    row.update(kw)
    return row


def _load_schema() -> dict:
    import validate_tc as vt
    return vt.load_schema()


def _schema_rules(schema: dict) -> dict:
    return derive_action_required(schema)


def _schema_type_matches(value, expected) -> bool:
    if isinstance(expected, list):
        return any(_schema_type_matches(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_schema_instance(instance, schema: dict) -> list[dict[str, str]]:
    """Evaluate the deterministic Draft-07 subset used by tc_step_schema.json."""

    def resolve_ref(ref: str) -> dict:
        if not ref.startswith("#/"):
            raise LedgerInputError(f"unsupported schema ref: {ref}")
        node = schema
        for token in ref[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            node = node[token]
        return node

    def child_path(path: str, key) -> str:
        token = str(key).replace("~", "~0").replace("/", "~1")
        return f"{path}/{token}" if path else f"/{token}"

    def violation(path: str, keyword: str, message: str) -> dict[str, str]:
        return {"path": path or "/", "keyword": keyword, "message": message}

    def walk(value, node: dict, path: str) -> list[dict[str, str]]:
        if "$ref" in node:
            node = resolve_ref(node["$ref"])

        findings: list[dict[str, str]] = []
        expected_type = node.get("type")
        if expected_type is not None and not _schema_type_matches(value, expected_type):
            actual = type(value).__name__
            findings.append(violation(path, "type", f"expected {expected_type}, got {actual}"))
            return findings

        if "const" in node and value != node["const"]:
            findings.append(violation(path, "const", f"expected {node['const']!r}"))
        if "enum" in node and value not in node["enum"]:
            findings.append(violation(path, "enum", f"value {value!r} not in enum"))
        if isinstance(value, str):
            if "pattern" in node and re.search(node["pattern"], value) is None:
                findings.append(violation(path, "pattern", "string does not match pattern"))
            if "minLength" in node and len(value) < node["minLength"]:
                findings.append(violation(path, "minLength", "string is too short"))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in node and value < node["minimum"]:
                findings.append(violation(path, "minimum", "number is below minimum"))

        if isinstance(value, dict):
            properties = node.get("properties", {})
            for key in node.get("required", []):
                if key not in value:
                    findings.append(violation(
                        child_path(path, key), "required", f"missing required property {key!r}",
                    ))
            for key, child_schema in properties.items():
                if key in value:
                    findings.extend(walk(value[key], child_schema, child_path(path, key)))
            extras = sorted(set(value) - set(properties))
            additional = node.get("additionalProperties", True)
            if additional is False:
                for key in extras:
                    findings.append(violation(
                        child_path(path, key), "additionalProperties",
                        f"unexpected property {key!r}",
                    ))
            elif isinstance(additional, dict):
                for key in extras:
                    findings.extend(walk(value[key], additional, child_path(path, key)))

        if isinstance(value, list):
            if "minItems" in node and len(value) < node["minItems"]:
                findings.append(violation(path, "minItems", "array has too few items"))
            if isinstance(node.get("items"), dict):
                for index, item in enumerate(value):
                    findings.extend(walk(item, node["items"], child_path(path, index)))

        for branch in node.get("allOf", []):
            findings.extend(walk(value, branch, path))
        if "if" in node and not walk(value, node["if"], path):
            if "then" in node:
                findings.extend(walk(value, node["then"], path))
        return findings

    return sorted(
        walk(instance, schema, ""),
        key=lambda item: (item["path"], item["keyword"], item["message"]),
    )


def _schema_document_observation(doc: dict, schema: dict) -> dict:
    top_properties = set(schema.get("properties", {}))
    top_missing = sorted(key for key in schema.get("required", []) if key not in doc)
    top_extra = sorted(set(doc) - top_properties)

    metadata = doc.get("metadata")
    metadata_schema = schema.get("properties", {}).get("metadata", {})
    metadata_missing = sorted(
        key for key in metadata_schema.get("required", [])
        if not isinstance(metadata, dict) or key not in metadata
    )

    rules = _schema_rules(schema)
    step_rule_violations = []
    steps = doc.get("steps") if isinstance(doc.get("steps"), list) else []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        action = step.get("action")
        missing = sorted(key for key in rules.get(action, []) if key not in step)
        if missing:
            step_rule_violations.append({
                "step_index": index,
                "action": action,
                "missing": missing,
            })

    return {
        "violations": validate_schema_instance(doc, schema),
        "top_level_missing": top_missing,
        "top_level_extra": top_extra,
        "metadata_missing": metadata_missing,
        "step_rule_violations": step_rule_violations,
    }


# ─── fixture matrix (§6.2) ───

def build_fixture_matrix() -> list[dict]:
    fx: list[dict] = []

    def add(fid, family, variant, action, step, canonical_field="-", unit="-", **kw):
        entry = {
            "fixture_id": fid, "family": family, "variant": variant,
            "action": action, "step": step,
            "canonical_field": canonical_field, "unit": unit,
        }
        entry.update(kw)
        fx.append(entry)

    # 1. target/text (selector alias)
    add("tap_text_canonical_only", "target/text", "canonical_only", "tap_text",
        {"action": "tap_text", "target": "OK"}, "target")
    add("tap_text_alias_only", "target/text", "alias_only", "tap_text",
        {"action": "tap_text", "text": "OK"}, "target")
    add("tap_text_equal_duplicate", "target/text", "equal_duplicate", "tap_text",
        {"action": "tap_text", "target": "OK", "text": "OK"}, "target")
    add("tap_text_conflicting_duplicate", "target/text", "conflicting_duplicate", "tap_text",
        {"action": "tap_text", "target": "B", "text": "A"}, "target")

    # 2. duration/seconds (wait)
    add("wait_canonical_only", "duration/seconds", "canonical_only", "wait",
        {"action": "wait", "duration": 1500}, "duration", "ms")
    add("wait_alias_only", "duration/seconds", "alias_only", "wait",
        {"action": "wait", "seconds": 2}, "duration", "s")
    add("wait_equal_duplicate", "duration/seconds", "equal_duplicate", "wait",
        {"action": "wait", "duration": 2000, "seconds": 2}, "duration", "ms/s")
    add("wait_conflicting_duplicate", "duration/seconds", "conflicting_duplicate", "wait",
        {"action": "wait", "duration": 2000, "seconds": 5}, "duration", "ms/s")

    # 3. key/keycode
    add("key_canonical_only", "key/keycode", "canonical_only", "key",
        {"action": "key", "key": "KEYCODE_HOME"}, "key")
    add("key_alias_only", "key/keycode", "alias_only", "key",
        {"action": "key", "keycode": "KEYCODE_HOME"}, "key")
    add("key_equal_duplicate", "key/keycode", "equal_duplicate", "key",
        {"action": "key", "key": "KEYCODE_HOME", "keycode": "KEYCODE_HOME"}, "key")
    add("key_conflicting_duplicate", "key/keycode", "conflicting_duplicate", "key",
        {"action": "key", "key": "KEYCODE_A", "keycode": "KEYCODE_B"}, "key")

    # 4. x/y vs x1/y1 (swipe 시작점)
    add("swipe_canonical_only", "x/y vs x1/y1", "canonical_only", "swipe",
        {"action": "swipe", "x": 100, "y": 200, "x2": 300, "y2": 400}, "x/y")
    add("swipe_alias_only", "x/y vs x1/y1", "alias_only", "swipe",
        {"action": "swipe", "x1": 100, "y1": 200, "x2": 300, "y2": 400}, "x/y")
    add("swipe_equal_duplicate", "x/y vs x1/y1", "equal_duplicate", "swipe",
        {"action": "swipe", "x": 100, "y": 200, "x1": 100, "y1": 200,
         "x2": 300, "y2": 400}, "x/y")
    add("swipe_conflicting_duplicate", "x/y vs x1/y1", "conflicting_duplicate", "swipe",
        {"action": "swipe", "x": 900, "y": 900, "x1": 100, "y1": 200,
         "x2": 300, "y2": 400}, "x/y")

    # 5. target/id (tap_id)
    add("tap_id_canonical_only", "target/id", "canonical_only", "tap_id",
        {"action": "tap_id", "target": "com.x:id/btn"}, "target")
    add("tap_id_alias_only", "target/id", "alias_only", "tap_id",
        {"action": "tap_id", "id": "com.x:id/btn"}, "target")
    add("tap_id_equal_duplicate", "target/id", "equal_duplicate", "tap_id",
        {"action": "tap_id", "target": "com.x:id/btn", "id": "com.x:id/btn"}, "target")
    add("tap_id_conflicting_duplicate", "target/id", "conflicting_duplicate", "tap_id",
        {"action": "tap_id", "target": "com.x:id/a", "id": "com.x:id/b"}, "target")

    # 특수 fixture (§6.2)
    add("input_text_text_canonical", "input_text", "special", "input_text",
        {"action": "input_text", "text": "hello"}, "text")
    add("input_text_target_rejected", "input_text", "special", "input_text",
        {"action": "input_text", "target": "hello"}, "text")
    add("key_sequence_delay_seconds_observed", "key_sequence/delay", "special",
        "key_sequence", {"action": "key_sequence", "keys": [3, 4], "delay": 7},
        "delay", "s")
    add("screenshot_name", "screenshot/name", "special", "screenshot",
        {"action": "screenshot", "name": "shot1"}, "name")
    add("verify_shell_timeout_5000_ms", "timeout", "special", "verify_shell",
        {"action": "verify_shell", "command": "getprop ro.build.type",
         "expected": "user", "timeout": 5000}, "timeout", "ms")
    add("verify_gone_timeout_1000_ms", "timeout", "special", "verify_gone",
        {"action": "verify_gone", "target": "팝업", "timeout": 1000}, "timeout", "ms")
    add("metadata_runnable_false", "metadata", "special", "wait",
        {"action": "wait", "duration": 500}, "runnable",
        metadata_override={**CANONICAL_METADATA, "runnable": False,
                           "runnable_reason": ["FIXTURE_REQUIRED"]})
    add("metadata_runnable_reason_unresolved", "metadata", "special", "wait",
        {"action": "wait", "duration": 500}, "runnable_reason",
        metadata_override={**CANONICAL_METADATA,
                           "runnable_reason": ["UNRESOLVED_PARAMS"]})
    add("step_compile_status_unresolved", "compile_status", "special", "shell",
        {"action": "shell", "command": "am start -n com.probe/.Main",
         "compile_status": "UNRESOLVED_PARAMS"}, "compile_status")
    add("shell_placeholder_brace", "compile_status", "special", "shell",
        {"action": "shell", "command": "am start {PKG}"}, "command")
    add("shell_rc1_with_stdout", "shell_result", "special", "shell",
        {"action": "shell", "command": "bogus-cmd"}, "returncode",
        scope="shell_rc")
    add("excel_swipe_endpoint_missing", "producer/excel", "special", "swipe",
        {"action": "swipe", "x1": 100, "y1": 200}, "x2/y2",
        scope="producer", producer="excel",
        producer_input={
            "tc_name": "EXCEL_TC1", "step": 4, "action": "swipe",
            "parameter1": 100, "parameter2": 200, "expected": None,
        })
    add("excel_canonical_swipe_complete", "producer/excel", "canonical", "swipe",
        {"action": "swipe", "x": 100, "y": 200, "x2": 300, "y2": 400},
        "x/y/x2/y2", scope="producer", producer="excel",
        producer_mode="canonical",
        producer_input={
            "tc_name": "EXCEL_TC1", "step": 4, "action": "swipe",
            "parameter1": "100,200", "parameter2": "300,400",
            "expected": None,
        })
    add("mmi_unresolved_shell_compiler", "producer/mmi", "special", "shell",
        {"action": "shell", "command": "am start {package}"}, "command",
        scope="producer", producer="mmi",
        producer_input={
            "target": "__ledger_unresolved_package__",
            "execution_mode": "SHELL_AUTO", "step_role": "ACTION",
        })
    add("mmi_canonical_document", "producer/mmi", "canonical", "-", {},
        "document", scope="producer", producer="mmi",
        producer_mode="canonical", producer_input={})

    # 6. tc_name/name (top-level, loader/validator/schema 전용)
    def doc(**top):
        d = dict(top)
        d["metadata"] = dict(CANONICAL_METADATA)
        d["steps"] = [{"action": "wait", "duration": 500}]
        return d

    add("tcname_canonical_only", "tc_name/name", "canonical_only", "-",
        {}, "tc_name", scope="toplevel", doc=doc(tc_name="TOPLEVEL_CANON"))
    add("tcname_alias_only", "tc_name/name", "alias_only", "-",
        {}, "tc_name", scope="toplevel", doc=doc(name="TOPLEVEL_ALIAS"))
    add("tcname_equal_duplicate", "tc_name/name", "equal_duplicate", "-",
        {}, "tc_name", scope="toplevel",
        doc=doc(tc_name="TOPLEVEL_EQ", name="TOPLEVEL_EQ"))
    add("tcname_conflicting_duplicate", "tc_name/name", "conflicting_duplicate", "-",
        {}, "tc_name", scope="toplevel",
        doc=doc(tc_name="B_TCNAME", name="A_NAME"))

    return fx


# ─── runner probe 하네스 (fake ADB + fake time, no device/subprocess) ───

class _FakeTime:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def time(self):
        self.now += 0.26
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += float(s)


class _FakeADB:
    def __init__(
        self,
        shell_output="ro.build.type=user PROBE_OK state=2",
        shell_returncode=0,
        shell_stderr="",
    ):
        self.calls = []
        self.shell_output = shell_output
        self.shell_returncode = shell_returncode
        self.shell_stderr = shell_stderr

    def dump_ui(self):
        self.calls.append(["dump_ui"])
        return "<hierarchy/>"

    def tap(self, x, y):
        self.calls.append(["tap", x, y])

    def swipe(self, x1, y1, x2, y2, duration=300):
        self.calls.append(["swipe", x1, y1, x2, y2, duration])

    def key(self, keycode):
        self.calls.append(["key", keycode])

    def shell(self, command, timeout=10):
        self.calls.append(["shell", command, timeout])
        return self.shell_output

    def shell_result(self, command, *, timeout_s=10.0):
        from src.adb import ShellResult

        self.calls.append(["shell_result", command, timeout_s])
        return ShellResult(
            command=command,
            stdout=self.shell_output,
            stderr=self.shell_stderr,
            returncode=self.shell_returncode,
        )

    def input_text(self, text):
        self.calls.append(["input_text", text])

    def screenshot(self, path):
        self.calls.append(["screenshot", str(path)])


def _run_runner_step(
    step: dict,
    shell_output=None,
    element_found=True,
    *,
    contract_mode="legacy",
    shell_returncode=0,
    shell_stderr="",
) -> dict:
    import src.action_runner as ar

    fake_time = _FakeTime()
    fake_kwargs = {
        "shell_returncode": shell_returncode,
        "shell_stderr": shell_stderr,
    }
    if shell_output is not None:
        fake_kwargs["shell_output"] = shell_output
    fake = _FakeADB(**fake_kwargs)
    lookups: list[list] = []

    def _find_text(xml, t):
        lookups.append(["text", t])
        return {"x": 10, "y": 20} if element_found else None

    def _find_id(xml, i):
        lookups.append(["id", i])
        return {"x": 11, "y": 21}

    def _find_desc(xml, t):
        lookups.append(["desc", t])
        return ("ok", {"x": 12, "y": 22})

    patches = {
        "time": fake_time,
        "find_element_by_text": _find_text,
        "find_element_by_id": _find_id,
        "find_clickable_target_by_content_desc": _find_desc,
        "find_focused_node": lambda xml: {"bounds": "[0,0][10,10]"},
        "find_selected_node": lambda xml: {"bounds": "[0,0][10,10]"},
    }
    orig = {name: getattr(ar, name) for name in patches}
    with tempfile.TemporaryDirectory() as td:
        scr_dir = Path(td) / "shots"
        runner = ar.ActionRunner(adb=fake, screenshot_dir=scr_dir,
                                 max_retries=1, retry_interval=0.0,
                                 contract_mode=contract_mode)
        for name, val in patches.items():
            setattr(ar, name, val)
        try:
            result = runner.run_step(dict(step))
        finally:
            for name, val in orig.items():
                setattr(ar, name, val)
        scrub = str(scr_dir)

    def _scrub(v):
        return v.replace(scrub, "<SCRDIR>") if isinstance(v, str) else v

    return {
        "passed": result.passed,
        "message": _scrub(result.message),
        "calls": [[_scrub(x) for x in c] for c in fake.calls],
        "sleeps": fake_time.sleeps,
        "lookups": lookups,
    }


# ─── consumer probes ───

def _family_values(f: dict):
    step = f["step"]
    family = f["family"]
    if family == "target/text":
        return step.get("target"), step.get("text")
    if family == "duration/seconds":
        canon = step["duration"] / 1000.0 if "duration" in step else None
        return canon, step.get("seconds")
    if family == "key/keycode":
        return step.get("key"), step.get("keycode")
    if family == "x/y vs x1/y1":
        canon = (step.get("x"), step.get("y"))
        alias = (step.get("x1"), step.get("y1"))
        return canon, alias
    if family == "target/id":
        return step.get("target"), step.get("id")
    return None, None


def _consumed_value(f: dict, res: dict):
    family = f["family"]
    if family in ("target/text", "target/id"):
        return res["lookups"][0][1] if res["lookups"] else None
    if family == "duration/seconds":
        return res["sleeps"][0] if res["sleeps"] else None
    if family == "key/keycode":
        for c in res["calls"]:
            if c[0] == "key":
                return c[1]
        return None
    if family == "x/y vs x1/y1":
        for c in res["calls"]:
            if c[0] == "swipe":
                return (c[1], c[2])
        return None
    return None


def _runner_verdict(
    f: dict,
    res: dict,
    *,
    contract_mode="legacy",
) -> tuple[str, str]:
    fid = f["fixture_id"]
    variant = f["variant"]
    verdict = "accept" if res["passed"] else "reject"
    finding = "-"

    if fid == "input_text_text_canonical" and res["passed"]:
        finding = "INPUT_TEXT_VALUE_NOT_ALIAS"
    elif fid == "key_sequence_delay_seconds_observed":
        verdict, finding = "observed", "KEY_SEQUENCE_DELAY_SECONDS_OBSERVED"
    elif fid == "verify_shell_timeout_5000_ms":
        if contract_mode == "canonical":
            shell_calls = [
                c for c in res["calls"] if c[0] == "shell_result"
            ]
            if (
                shell_calls
                and shell_calls[0][2] == f["step"]["timeout"] / 1000.0
            ):
                verdict, finding = (
                    "observed",
                    "TIMEOUT_MS_CONVERTED_AT_ADB_BOUNDARY",
                )
        else:
            shell_calls = [c for c in res["calls"] if c[0] == "shell"]
            if shell_calls and shell_calls[0][2] == f["step"]["timeout"]:
                verdict, finding = "observed", "TIMEOUT_MS_AS_SECONDS"
    elif fid == "verify_gone_timeout_1000_ms":
        verdict, finding = "observed", "TIMEOUT_MS_CONVERTED_BY_VERIFY_GONE"
    elif fid == "screenshot_name":
        verdict, finding = "observed", "SCREENSHOT_NAME_UNGOVERNED"
    elif fid == "step_compile_status_unresolved" and res["passed"]:
        verdict, finding = "observed", "UNRESOLVED_STEP_EXECUTED"
    elif fid == "shell_placeholder_brace" and res["passed"]:
        verdict, finding = "observed", "UNRESOLVED_PLACEHOLDER_EXECUTED"
    elif variant in ("equal_duplicate", "conflicting_duplicate"):
        canon, alias = _family_values(f)
        consumed = _consumed_value(f, res)
        verdict = "observed"
        # canon 은 family 별로 이미 정규화된 비교값 (duration 은 초 환산; 2.0 == 2)
        if variant == "equal_duplicate":
            consistent = (consumed is not None and canon == alias
                          and consumed == alias)
            finding = ("EQUAL_DUPLICATE_CONSISTENT" if consistent
                       else "EQUAL_DUPLICATE_INCONSISTENT")
        else:
            finding = ("CONFLICT_ALIAS_SHADOWS_CANONICAL"
                       if consumed == alias else "CONFLICT_CANONICAL_WINS")
    elif (
        contract_mode == "canonical"
        and fid == "tap_id_canonical_only"
        and res["passed"]
    ):
        verdict, finding = "observed", "CANONICAL_ACCEPTED_BY_RUNNER"
    elif variant == "canonical_only" and not res["passed"]:
        finding = "CANONICAL_REJECTED_BY_RUNNER"
    elif variant == "alias_only" and res["passed"]:
        verdict, finding = "observed", "ALIAS_ACCEPTED_BY_RUNNER"
    return verdict, finding


def _probe_runner_consumer(f: dict, *, contract_mode="legacy") -> dict:
    res = _run_runner_step(f["step"], contract_mode=contract_mode)
    verdict, finding = _runner_verdict(
        f,
        res,
        contract_mode=contract_mode,
    )
    return _row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="action_runner",
        consumer="action_runner", action=f["step"].get("action", "-"),
        variant=(
            f["variant"] if contract_mode == "legacy" else "canonical_runner"
        ), canonical_field=f["canonical_field"],
        observed_fields=_json(sorted(k for k in f["step"] if k != "action")),
        unit=f["unit"], verdict=verdict, finding_code=finding,
        normalized_json=_json(res),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    )


def _probe_schema_consumer(f: dict, schema: dict, rules: dict) -> dict:
    step = f["step"]
    action = step.get("action", "-")
    req = rules.get(action)
    missing = [k for k in (req or []) if k not in step]
    violations = validate_schema_instance(step, schema["$defs"]["step"])
    verdict = "accept" if not violations else "reject"
    finding = "SCHEMA_RULE_ABSENT" if req is None else "-"
    nj = {"required": req, "missing": missing, "violations": violations}
    return _row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="schema",
        consumer="schema", action=action, variant=f["variant"],
        canonical_field=f["canonical_field"],
        observed_fields=_json(sorted(k for k in step if k != "action")),
        unit=f["unit"], verdict=verdict, finding_code=finding,
        normalized_json=_json(nj),
        source_sha256=sha256_bytes(_json(step).encode("utf-8")),
    )


def _probe_validator_consumer(f: dict, schema: dict) -> dict:
    meta = f.get("metadata_override") or dict(CANONICAL_METADATA)
    tc = {"tc_name": f["fixture_id"], "metadata": meta, "steps": [dict(f["step"])]}
    normalized, core_errors, wrapper_errors = _validator_boundary(tc, schema)
    wrapper_core_match = wrapper_errors == core_errors
    verdict = "blocking" if (normalized.blocking or not wrapper_core_match) else (
        "accept" if not wrapper_errors else "reject"
    )
    finding = "-"
    contract_findings = _contract_findings(normalized)
    if not wrapper_core_match:
        finding = "VALIDATOR_CORE_DIVERGENCE"
    elif contract_findings:
        finding = contract_findings[0]["code"]
    elif "compile_status" in f["step"] and not wrapper_errors:
        finding = "COMPILE_STATUS_IGNORED_BY_VALIDATOR"
    elif any("placeholder" in e for e in wrapper_errors):
        finding = "PLACEHOLDER_BRACE_DETECTED"
    elif any("runnable=false" in e for e in wrapper_errors):
        finding = "RUNNABLE_REASON_CONSISTENCY_ENFORCED"
    return _row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="validate_tc",
        consumer="validate_tc", action=f["step"].get("action", "-"),
        variant=f["variant"], canonical_field=f["canonical_field"],
        observed_fields=_json(sorted(k for k in f["step"] if k != "action")),
        unit=f["unit"], verdict=verdict, finding_code=finding,
        normalized_json=_json({
            "canonical": normalized.value,
            "contract_findings": contract_findings,
            "core_errors": core_errors,
            "wrapper_errors": wrapper_errors,
            "wrapper_core_match": wrapper_core_match,
            "errors": wrapper_errors,
        }),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    )


def _load_tc_via_tempfile(
    doc: dict,
    contract_mode: str = "legacy",
) -> tuple[dict | None, str | None, str]:
    """load_tc 를 임시 YAML 로 호출. (loaded, error_type, scrubbed_error)"""
    from src.tc_loader import load_tc, TCValidationError
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "probe_tc.yaml"
        p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                     encoding="utf-8")
        try:
            return load_tc(p, contract_mode=contract_mode), None, ""
        except TCValidationError as e:
            return None, "TCValidationError", str(e).replace(str(p), "<TC>")
        except Exception as e:  # yaml 오류 등
            return None, type(e).__name__, str(e).replace(str(p), "<TC>")


def _probe_loader_consumer(f: dict, rules: dict) -> dict:
    doc = {"name": f["fixture_id"], "steps": [dict(f["step"])]}
    loaded, err_type, err = _load_tc_via_tempfile(doc)
    verdict = "accept" if loaded is not None else "reject"
    req = rules.get(f["step"].get("action"))
    missing = [k for k in (req or []) if k not in f["step"]]
    finding = "PARAMS_UNVALIDATED_BY_LOADER" if (loaded is not None and missing) else "-"
    nj = {"error": err or None, "error_type": err_type,
          "loaded_keys": sorted(loaded.keys()) if loaded else None}
    return _row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="tc_loader",
        consumer="tc_loader", action=f["step"].get("action", "-"),
        variant=f["variant"], canonical_field=f["canonical_field"],
        observed_fields=_json(sorted(k for k in f["step"] if k != "action")),
        unit=f["unit"], verdict=verdict, finding_code=finding,
        normalized_json=_json(nj),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    )


def _probe_toplevel_fixture(f: dict, schema: dict) -> list[dict]:
    doc = f["doc"]
    rows = []
    schema_observation = _schema_document_observation(doc, schema)
    extra = schema_observation["top_level_extra"]
    verdict = "accept" if not schema_observation["violations"] else "reject"
    rows.append(_row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="schema",
        consumer="schema", variant=f["variant"], canonical_field="tc_name",
        observed_fields=_json(sorted(doc.keys())),
        verdict=verdict,
        finding_code="TOPLEVEL_EXTRA_KEY_PRESENT" if extra else "-",
        normalized_json=_json(schema_observation),
        source_sha256=sha256_bytes(_json(doc).encode("utf-8")),
    ))

    # validate_tc 경계가 사용하는 shared normalizer 결과를 별도 기록한다.
    normalized, core_errors, wrapper_errors = _validator_boundary(doc, schema)
    wrapper_core_match = wrapper_errors == core_errors
    verdict = "blocking" if (normalized.blocking or not wrapper_core_match) else (
        "accept" if not wrapper_errors else "reject"
    )
    finding = "-"
    contract_findings = _contract_findings(normalized)
    if not wrapper_core_match:
        finding = "VALIDATOR_CORE_DIVERGENCE"
    elif contract_findings:
        finding = contract_findings[0]["code"]
    elif extra and not any(k in e for e in wrapper_errors for k in extra):
        finding = "TOPLEVEL_EXTRA_KEY_UNENFORCED"
    rows.append(_row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="validate_tc",
        consumer="validate_tc", variant=f["variant"], canonical_field="tc_name",
        observed_fields=_json(sorted(doc.keys())),
        verdict=verdict, finding_code=finding,
        normalized_json=_json({
            "canonical": normalized.value,
            "contract_findings": contract_findings,
            "core_errors": core_errors,
            "wrapper_errors": wrapper_errors,
            "wrapper_core_match": wrapper_core_match,
            "errors": wrapper_errors,
        }),
        source_sha256=sha256_bytes(_json(doc).encode("utf-8")),
    ))

    # tc_loader (tc_name → name shim 방향 관찰)
    loaded, err_type, err = _load_tc_via_tempfile(doc)
    verdict = "accept" if loaded is not None else "reject"
    finding = "-"
    nj = {"error": err or None, "error_type": err_type}
    if loaded is not None:
        nj["name"] = loaded.get("name")
        nj["tc_name"] = loaded.get("tc_name")
        if "name" not in doc and "tc_name" in doc:
            finding = "TC_NAME_SHIM_APPLIED"
        elif "name" in doc and "tc_name" in doc and doc["name"] != doc["tc_name"]:
            finding = "NAME_WINS_OVER_TC_NAME"
    rows.append(_row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="tc_loader",
        consumer="tc_loader", variant=f["variant"], canonical_field="tc_name",
        observed_fields=_json(sorted(doc.keys())),
        verdict=verdict, finding_code=finding,
        normalized_json=_json(nj),
        source_sha256=sha256_bytes(_json(doc).encode("utf-8")),
    ))
    return rows


def _probe_shell_rc(f: dict) -> list[dict]:
    """Legacy defect and canonical runner handling for a nonzero shell rc."""
    import src.adb as adb_mod

    captured = {}

    class _FakeCompleted:
        returncode = 1
        stdout = "sh: bogus-cmd: inaccessible or not found"
        stderr = "boom"

    def fake_run(cmd, **kw):
        captured["cmd"] = list(cmd)
        captured["timeout"] = kw.get("timeout")
        return _FakeCompleted()

    orig_run = adb_mod.subprocess.run
    adb_mod.subprocess.run = fake_run
    try:
        returned = adb_mod.ADB("PROBE_SERIAL").shell("bogus-cmd", timeout=5)
    finally:
        adb_mod.subprocess.run = orig_run

    returned_rc = (
        returned.get("returncode") if isinstance(returned, dict)
        else getattr(returned, "returncode", None)
    )
    returned_stderr = (
        returned.get("stderr") if isinstance(returned, dict)
        else getattr(returned, "stderr", None)
    )
    shell_returned_stdout_only = returned == _FakeCompleted.stdout
    shell_failure_preserved = (
        returned_rc == _FakeCompleted.returncode
        and returned_stderr == _FakeCompleted.stderr
    )
    shell_defect_observed = shell_returned_stdout_only or not shell_failure_preserved
    shell_verdict = "blocking" if shell_defect_observed else "observed"
    shell_finding = (
        "SHELL_RC_DISCARDED" if shell_defect_observed else "SHELL_RC_PRESERVED"
    )
    if isinstance(returned, (str, int, float, bool, list, dict, type(None))):
        returned_observation = returned
    else:
        returned_observation = {
            "type": type(returned).__name__,
            "returncode": returned_rc,
            "stdout": getattr(returned, "stdout", None),
            "stderr": returned_stderr,
        }

    rows = [_row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="adb",
        action="shell", variant=f["variant"], canonical_field="returncode",
        observed_fields=_json(["command", "timeout"]),
        verdict=shell_verdict, finding_code=shell_finding,
        normalized_json=_json({
            "returncode": 1,
            "stdout": _FakeCompleted.stdout,
            "stderr_discarded": _FakeCompleted.stderr,
            "returned": returned_observation,
            "shell_returned_stdout_only": shell_returned_stdout_only,
            "shell_failure_preserved": shell_failure_preserved,
            "subprocess_timeout": captured["timeout"],
        }),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    )]

    res = _run_runner_step(f["step"],
                           shell_output="sh: bogus-cmd: inaccessible or not found")
    runner_defect_observed = res["passed"]
    rows.append(_row(
        fixture_id=f["fixture_id"], actor_kind="consumer", actor="action_runner",
        consumer="action_runner", action="shell", variant=f["variant"],
        canonical_field="returncode", observed_fields=_json(["command"]),
        verdict="blocking" if runner_defect_observed else "observed",
        finding_code=(
            "SHELL_RC_DISCARDED" if runner_defect_observed
            else "SHELL_NONZERO_REJECTED"
        ),
        normalized_json=_json(res),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    ))

    canonical_res = _run_runner_step(
        f["step"],
        shell_output=_FakeCompleted.stdout,
        contract_mode="canonical",
        shell_returncode=_FakeCompleted.returncode,
        shell_stderr=_FakeCompleted.stderr,
    )
    canonical_rejected = not canonical_res["passed"]
    rows.append(_row(
        fixture_id=f["fixture_id"], actor_kind="consumer",
        actor="action_runner", consumer="action_runner", action="shell",
        variant="canonical_runner", canonical_field="returncode",
        observed_fields=_json(["command", "returncode", "stderr"]),
        verdict="observed" if canonical_rejected else "blocking",
        finding_code=(
            "SHELL_NONZERO_REJECTED"
            if canonical_rejected else "SHELL_RC_DISCARDED"
        ),
        normalized_json=_json(canonical_res),
        source_sha256=sha256_bytes(_json(f["step"]).encode("utf-8")),
    ))
    return rows


def probe_consumers(fixtures: list[dict]) -> list[dict]:
    schema = _load_schema()
    rules = _schema_rules(schema)
    rows: list[dict] = []
    for f in fixtures:
        scope = f.get("scope", "consumers")
        if scope == "producer":
            continue
        if scope == "shell_rc":
            rows.extend(_probe_shell_rc(f))
            continue
        if scope == "toplevel":
            rows.extend(_probe_toplevel_fixture(f, schema))
            continue
        rows.append(_probe_schema_consumer(f, schema, rules))
        rows.append(_probe_validator_consumer(f, schema))
        rows.append(_probe_loader_consumer(f, rules))
        rows.append(_probe_runner_consumer(f))
        if f["fixture_id"] in {
            "tap_id_canonical_only",
            "verify_shell_timeout_5000_ms",
        }:
            rows.append(
                _probe_runner_consumer(f, contract_mode="canonical")
            )
    return rows


# ─── producer probes + pair rows ───

_EXCEL_ROWS = [
    ("EXCEL_TC1", 1, "tap_text", "확인", None, None),
    ("EXCEL_TC1", 2, "tap_id", "com.x:id/btn", None, None),
    ("EXCEL_TC1", 3, "tap_xy", 100, 200, None),
    ("EXCEL_TC1", 5, "key", "KEYCODE_HOME", None, None),
    ("EXCEL_TC1", 6, "shell", "getprop ro.build.type", None, None),
    ("EXCEL_TC1", 7, "wait", "2", None, None),
    ("EXCEL_TC1", 8, "screenshot", "shot1", None, None),
    ("EXCEL_TC1", 9, "verify_text", "완료", None, None),
    ("EXCEL_TC1", 10, "verify_shell", "getprop ro.build.type", None, "user"),
    ("EXCEL_TC1", 11, "input_text", "hello", None, None),
]

_LEGACY_STEP_FIELDS = {"seconds", "keycode", "x1", "y1", "id"}


def _emitted_step_finding(step: dict) -> tuple[str, str]:
    action = step.get("action")
    keys = set(step) - {"action"}
    if action == "swipe" and not {"x2", "y2"} <= keys:
        return "blocking", "EXCEL_SWIPE_ENDPOINT_MISSING"
    legacy = keys & _LEGACY_STEP_FIELDS
    if action in SELECTOR_ACTIONS and "text" in keys:
        legacy = legacy | {"text"}
    if "{" in str(step.get("command", "")):
        return "observed", "UNRESOLVED_PLACEHOLDER_EMITTED"
    if legacy:
        return "observed", "LEGACY_ALIAS_EMITTED"
    return "observed", "-"


def _producer_fixtures(
    fixtures: list[dict],
    producer: str,
    mode: str = "legacy",
) -> list[dict]:
    return [
        fixture for fixture in fixtures
        if fixture.get("scope") == "producer"
        and fixture.get("producer") == producer
        and fixture.get("producer_mode", "legacy") == mode
    ]


def _produce_excel_doc(
    fixtures: list[dict],
    contract_mode: str = "legacy",
) -> tuple[dict, dict[int, str]]:
    from openpyxl import Workbook
    from src.excel_converter import convert_excel_to_yaml

    producer_fixtures = _producer_fixtures(fixtures, "excel", contract_mode)
    rows = list(_EXCEL_ROWS)
    for fixture in producer_fixtures:
        item = fixture["producer_input"]
        rows.append((
            item["tc_name"], item["step"], item["action"],
            item.get("parameter1"), item.get("parameter2"), item.get("expected"),
        ))
    rows.sort(key=lambda row: (str(row[0]), int(row[1])))

    wb = Workbook()
    ws = wb.active
    ws.append(["TC Name", "Step", "Action", "Parameter1", "Parameter2", "Expected"])
    for r in rows:
        ws.append(list(r))
    with tempfile.TemporaryDirectory() as td:
        xlsx = Path(td) / "probe.xlsx"
        wb.save(xlsx)
        kwargs = {"contract_mode": contract_mode}
        if contract_mode == "canonical":
            kwargs["metadata_by_tc"] = {"EXCEL_TC1": dict(CANONICAL_METADATA)}
        files = convert_excel_to_yaml(xlsx, Path(td) / "out", **kwargs)
        doc = yaml.safe_load(files[0].read_text(encoding="utf-8"))

    fixture_ids: dict[int, str] = {}
    for fixture in producer_fixtures:
        action = fixture["producer_input"]["action"]
        index = next(
            idx for idx, step in enumerate(doc.get("steps", []))
            if step.get("action") == action and idx not in fixture_ids
        )
        fixture_ids[index] = fixture["fixture_id"]
    return doc, fixture_ids


def _produce_mmi_doc(
    fixtures: list[dict],
    contract_mode: str = "legacy",
) -> tuple[dict, dict[int, str]]:
    from src.mmi_converter.models import (
        ClassifiedIntent, ConversionPreview, Intent, TCIR,
    )
    from src.mmi_converter.compiler import TCRunnerCompiler
    from src.mmi_converter import exporter as exporter_mod
    from src.mmi_converter.shell_action_map import ShellAction, ShellActionMap

    ir = TCIR(
        tc_name="MMI_TC1", description="probe", preconditions=["precondition 1"],
        intents=[
            Intent(type="navigate", target="설정"),
            Intent(type="press_key", value="BACK"),
            Intent(type="wait", value="3"),
            Intent(type="input_text", extra={"text": "hello"}),
        ],
        expected_intents=[Intent(type="verify_text", target="연결됨")],
    )
    compiled = TCRunnerCompiler(contract_mode=contract_mode).compile(ir)
    producer_fixtures = _producer_fixtures(fixtures, "mmi", contract_mode)
    steps = list(compiled["steps"])
    warnings = ["probe_warning"]
    classified_intents = []
    fixture_ids: dict[int, str] = {}

    if contract_mode == "legacy":
        unresolved_fixture = next(
            fixture for fixture in producer_fixtures
            if fixture["fixture_id"] == "mmi_unresolved_shell_compiler"
        )
        producer_input = unresolved_fixture["producer_input"]

        class _ProbeShellActionMap(ShellActionMap):
            def resolve(self, intent):
                if intent.target == producer_input["target"]:
                    return ShellAction(
                        key="probe_unresolved_package",
                        command_template="am start {package}",
                        required_params=["package"],
                    )
                return super().resolve(intent)

        classified = ClassifiedIntent(
            intent=Intent(type="navigate", target=producer_input["target"]),
            execution_mode=producer_input["execution_mode"],
            step_role=producer_input["step_role"],
        )
        unresolved_steps, unresolved_warnings = TCRunnerCompiler(
            shell_action_map=_ProbeShellActionMap(),
            contract_mode=contract_mode,
        ).compile_classified(classified)
        unresolved_index = len(steps)
        steps.extend(unresolved_steps)
        warnings.extend(unresolved_warnings)
        classified_intents.append(classified)
        fixture_ids[unresolved_index] = unresolved_fixture["fixture_id"]

    preview = ConversionPreview(
        tc_name="MMI_TC1", automation_class="SEMI_AUTO",
        source_procedure="1. 설정 진입", source_expected="연결됨 표시",
        parsed_intents=[], compiled_steps=steps,
        warnings=warnings,
        classified_intents=classified_intents,
    )
    with tempfile.TemporaryDirectory() as td:
        path = exporter_mod.YAMLExporter(
            output_dir=Path(td),
            contract_mode=contract_mode,
        ).export_one(
            preview, source_file="PROBE.xlsx", source_sheet="S1", source_row=5)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc, fixture_ids


def _deterministic_document_view(doc: dict) -> dict:
    """Remove evidence-only wall-clock fields from deterministic comparisons."""
    view = copy.deepcopy(doc)
    metadata = view.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("exported_at", None)
    return view


def _producer_emission_rows(
    producer: str,
    doc: dict,
    fixture_ids: dict[int, str] | None = None,
    *,
    mode: str = "legacy",
) -> list[dict]:
    rows = []
    fixture_ids = fixture_ids or {}
    comparison_doc = _deterministic_document_view(doc)
    normalized = normalize_tc(
        comparison_doc,
        source=f"{producer}:{mode}:document",
    )
    canonical = normalized.value
    meta = canonical.get("metadata")
    canonical_errors = _contract_errors(normalized) + validate_canonical_tc(
        canonical, _load_schema()
    )
    doc_nj = {
        "top_level": sorted(doc.keys()),
        "top_key": "tc_name" if "tc_name" in doc else "name",
        "has_metadata": meta is not None,
        "metadata_keys": sorted(meta.keys()) if isinstance(meta, dict) else None,
        "metadata_warnings": list(meta.get("warnings", [])) if isinstance(meta, dict) else [],
        "exported_at_present": isinstance(doc.get("metadata"), dict)
        and "exported_at" in doc["metadata"],
        "canonical": canonical,
        "contract_findings": _contract_findings(normalized),
        "canonical_validation_errors": canonical_errors,
    }
    missing_meta = (sorted({"runnable", "tc_class", "execution_type", "manual_detail"}
                           - set(meta or {})))
    doc_finding = "PRODUCER_DOC_NONCANONICAL" if (
        normalized.findings or canonical_errors
    ) else "-"
    doc_nj["missing_canonical_metadata"] = missing_meta
    rows.append(_row(
        actor_kind="producer", actor=producer, producer=producer,
        tc_name=canonical.get("tc_name") or "-",
        variant=f"{mode}_document",
        observed_fields=_json(sorted(comparison_doc.keys())),
        verdict="blocking" if canonical_errors else "observed",
        finding_code=doc_finding,
        normalized_json=_json(doc_nj),
        source_sha256=sha256_bytes(_json(comparison_doc).encode("utf-8")),
    ))
    for idx, step in enumerate(comparison_doc.get("steps", [])):
        verdict, finding = _emitted_step_finding(step)
        if producer != "excel" and finding == "EXCEL_SWIPE_ENDPOINT_MISSING":
            finding = "SWIPE_ENDPOINT_MISSING"
        rows.append(_row(
            fixture_id=fixture_ids.get(idx, "-"),
            actor_kind="producer", actor=producer, producer=producer,
            tc_name=(comparison_doc.get("tc_name")
                     or comparison_doc.get("name") or "-"),
            step_index=str(idx), action=step.get("action", "-"),
            variant=f"{mode}_emission",
            observed_fields=_json(sorted(k for k in step if k != "action")),
            verdict=verdict, finding_code=finding,
            normalized_json=_json({k: v for k, v in step.items()}),
            source_sha256=sha256_bytes(_json(step).encode("utf-8")),
        ))
    return rows


def _pair_rows(
    producer: str,
    mode: str,
    doc: dict,
    schema: dict,
) -> list[dict]:
    import validate_tc as vt
    rows = []
    tc_name = doc.get("tc_name") or doc.get("name") or "-"
    doc_sha = sha256_bytes(
        _json(_deterministic_document_view(doc)).encode("utf-8")
    )

    def pair(consumer, verdict, finding, nj):
        rows.append(_row(
            actor_kind="pair", actor=consumer, producer=producer,
            consumer=consumer, tc_name=tc_name, variant=mode,
            verdict=verdict, finding_code=finding, normalized_json=_json(nj),
            source_sha256=doc_sha,
        ))

    schema_observation = _schema_document_observation(doc, schema)
    pair("schema", "accept" if not schema_observation["violations"] else "reject",
         "-", schema_observation)

    errors = vt.validate_tc(doc, schema)
    pair("validate_tc", "accept" if not errors else "reject", "-",
         {"error_count": len(errors), "errors": errors})

    loaded, err_type, err = _load_tc_via_tempfile(
        doc,
        contract_mode=mode,
    )
    pair("tc_loader", "accept" if loaded is not None else "reject", "-",
         {"error": err or None, "error_type": err_type,
          "loaded_name": (
              loaded.get("tc_name") or loaded.get("name")
              if loaded else None
          )})

    step_results = []
    any_fail = False
    endpoint_missing = False
    placeholder_executed = False
    for step in doc.get("steps", []):
        res = _run_runner_step(step)
        step_results.append({"action": step.get("action"),
                             "passed": res["passed"], "message": res["message"]})
        if not res["passed"]:
            any_fail = True
            if step.get("action") == "swipe" and "'x2'" in res["message"]:
                endpoint_missing = True
        elif "{" in str(step.get("command", "")):
            placeholder_executed = True
    if endpoint_missing:
        verdict, finding = "blocking", "EXCEL_SWIPE_ENDPOINT_MISSING"
    elif any_fail:
        verdict, finding = "reject", "-"
    elif placeholder_executed:
        verdict, finding = "accept", "UNRESOLVED_PLACEHOLDER_EXECUTED"
    else:
        verdict, finding = "accept", "-"
    pair("action_runner", verdict, finding, {"steps": step_results})
    return rows


def probe_producers(fixtures: list[dict]) -> list[dict]:
    schema = _load_schema()
    rows: list[dict] = []
    for mode in PRODUCER_MODES:
        excel_doc, excel_fixture_ids = _produce_excel_doc(fixtures, mode)
        mmi_doc, mmi_fixture_ids = _produce_mmi_doc(fixtures, mode)
        rows.extend(_producer_emission_rows(
            "excel", excel_doc, excel_fixture_ids, mode=mode,
        ))
        rows.extend(_pair_rows("excel", mode, excel_doc, schema))
        rows.extend(_producer_emission_rows(
            "mmi", mmi_doc, mmi_fixture_ids, mode=mode,
        ))
        rows.extend(_pair_rows("mmi", mode, mmi_doc, schema))
    return rows


# ─── corpus scan (read-only) ───

def _classify_step_fields(step: dict) -> tuple[dict, dict]:
    action = step.get("action")
    canonical: dict[str, int] = {}
    legacy: dict[str, int] = {}

    def c(k):
        canonical[k] = canonical.get(k, 0) + 1

    def l(k):
        legacy[k] = legacy.get(k, 0) + 1

    if "duration" in step:
        c("duration")
    if "seconds" in step:
        l("seconds")
    if "key" in step:
        c("key")
    if "keycode" in step:
        l("keycode")
    if action in SELECTOR_ACTIONS:
        if "target" in step:
            c("target")
        if "text" in step:
            l("text")
    if action == "input_text" and "text" in step:
        c("text")
    if action == "tap_id":
        if "target" in step:
            c("target")
        if "id" in step:
            l("id")
    if action in ("swipe", "tap_xy"):
        for k in ("x", "y", "x2", "y2"):
            if k in step:
                c(k)
        for k in ("x1", "y1"):
            if k in step:
                l(k)
    return canonical, legacy


def scan_corpora(groups=None) -> list[dict]:
    rows: list[dict] = []
    for group in (groups or CORPUS_GROUPS):
        name, _kind, _spec, primary = group
        files = _corpus_files(group)
        rows.append(_row(
            actor_kind="corpus", actor="corpus_scan", corpus=name,
            variant="group_count", verdict="observed",
            normalized_json=_json({"file_count": len(files), "primary": primary}),
        ))
        for fpath in files:
            rel = fpath.relative_to(REPO_ROOT).as_posix()
            try:
                doc = yaml.safe_load(fpath.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as e:
                raise LedgerInputError(f"corpus parse 실패 {rel}: {e}") from e
            if not isinstance(doc, dict):
                raise LedgerInputError(f"corpus 최상위가 dict 아님: {rel}")
            canonical: dict[str, int] = {}
            legacy: dict[str, int] = {}
            screenshot_name = 0
            steps = doc.get("steps") or []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                cc, ll = _classify_step_fields(step)
                for k, v in cc.items():
                    canonical[k] = canonical.get(k, 0) + v
                for k, v in ll.items():
                    legacy[k] = legacy.get(k, 0) + v
                if step.get("action") == "screenshot" and "name" in step:
                    screenshot_name += 1
            top = ("both" if "tc_name" in doc and "name" in doc
                   else "tc_name" if "tc_name" in doc
                   else "name" if "name" in doc else "-")
            verdict = ("canonical" if not legacy and top == "tc_name"
                       else "legacy")
            rows.append(_row(
                actor_kind="corpus", actor="corpus_scan", corpus=name,
                source_path=rel,
                tc_name=str(doc.get("tc_name") or doc.get("name") or "-"),
                variant="file",
                observed_fields=_json({"canonical": canonical, "legacy": legacy}),
                verdict=verdict,
                finding_code="LEGACY_DIALECT_FILE" if verdict == "legacy" else "-",
                normalized_json=_json({
                    "top_level": top,
                    "has_metadata": isinstance(doc.get("metadata"), dict),
                    "screenshot_name": screenshot_name,
                    "step_count": len(steps),
                }),
                source_sha256=sha256_file(fpath),
            ))
    return rows


# ─── 출력 (byte-deterministic) ───

def _sort_key(row: dict):
    idx = row.get("step_index", "-")
    idx_key = f"{int(idx):06d}" if idx not in ("-", "") else "-"
    return (row["producer"], row["variant"], row["consumer"], row["corpus"],
            row["source_path"], row["tc_name"], idx_key, row["fixture_id"])


def render_csv_bytes(rows: list[dict]) -> bytes:
    sio = io.StringIO()
    writer = csv.writer(sio, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in sorted(rows, key=_sort_key):
        writer.writerow([row[c] for c in CSV_COLUMNS])
    return sio.getvalue().encode("utf-8")


def _pair_matrix(rows: list[dict]) -> dict:
    matrix = {}
    for r in rows:
        if r["actor_kind"] == "pair":
            matrix[(r["producer"], r["variant"], r["consumer"])] = (
                r["verdict"], r["finding_code"]
            )
    return matrix


def render_summary_bytes(
    rows: list[dict],
    input_digest: str,
    csv_bytes: bytes,
    input_snapshot: dict[str, dict[str, int | str]],
) -> bytes:
    source_state = input_snapshot
    lines: list[str] = []
    add = lines.append
    add("# Contract Drift Ledger — SUMMARY")
    add("")
    add("## 1. Input digest / versions")
    add(f"- input_digest: `{input_digest}`")
    add(f"- out_dir prefix: `{input_digest[:16]}`")
    add(f"- tool_version: `{TOOL_VERSION}` / schema_version: {SCHEMA_VERSION}"
        f" / fixture_version: {FIXTURE_VERSION}")
    add("- actor sources:")
    for actor, files in ACTOR_SOURCE_FILES.items():
        for f in files:
            add(f"  - {actor}: `{f}` sha256 `{source_state[f]['sha256'][:16]}`")
    add("")
    add("## 2. Producer × consumer acceptance matrix (16 pairs)")
    matrix = _pair_matrix(rows)
    add("| producer | " + " | ".join(CONSUMERS) + " |")
    add("|---|" + "---|" * len(CONSUMERS))
    for p in PRODUCERS:
        for mode in PRODUCER_MODES:
            cells = []
            for c in CONSUMERS:
                verdict, finding = matrix.get((p, mode, c), ("-", "-"))
                cells.append(
                    verdict if finding == "-" else f"{verdict} ({finding})"
                )
            add(f"| {p}/{mode} | " + " | ".join(cells) + " |")
    add("")
    add("## 3. Alias / unit findings by action (consumer probes)")
    counts: dict[tuple, int] = {}
    for r in rows:
        if r["actor_kind"] == "consumer" and r["finding_code"] != "-":
            k = (r["action"], r["consumer"] if r["consumer"] != "-" else r["actor"],
                 r["finding_code"])
            counts[k] = counts.get(k, 0) + 1
    add("| action | consumer | finding | rows |")
    add("|---|---|---|---|")
    for (action, consumer, finding), n in sorted(counts.items()):
        add(f"| {action} | {consumer} | {finding} | {n} |")
    add("")
    add("## 4. Corpus impact")
    add("| group | files | legacy hits | primary |")
    add("|---|---|---|---|")
    group_counts = {}
    for r in rows:
        if r["actor_kind"] == "corpus" and r["variant"] == "group_count":
            nj = json.loads(r["normalized_json"])
            group_counts[r["corpus"]] = nj
    legacy_hits: dict[str, int] = {}
    for r in rows:
        if r["actor_kind"] == "corpus" and r["variant"] == "file":
            of = json.loads(r["observed_fields"])
            legacy_hits[r["corpus"]] = (legacy_hits.get(r["corpus"], 0)
                                        + sum(of["legacy"].values()))
    for gname, nj in group_counts.items():
        add(f"| {gname} | {nj['file_count']} | {legacy_hits.get(gname, 0)} |"
            f" {'yes' if nj['primary'] else 'no (informational)'} |")
    primary = tuple(group_counts[g[0]]["file_count"]
                    for g in CORPUS_GROUPS if g[3])
    add("")
    add(f"- primary counts (locked): {primary} — expected {PRIMARY_COUNTS}")
    add(f"- THOR2_K target count (informational only): "
        f"{group_counts.get('thor2k_settings_smoke', {}).get('file_count', '-')}")
    add("")
    add("## 5. Blocking findings / confirmed defects")
    blocking: dict[str, int] = {}
    for r in rows:
        if r["verdict"] == "blocking":
            blocking[r["finding_code"]] = blocking.get(r["finding_code"], 0) + 1
    for code in sorted(blocking):
        add(f"- `{code}`: {blocking[code]} rows")
    add(f"- blocking codes observed: `{_json(blocking)}`")
    add(f"- blocking baseline expected: `{_json(EXPECTED_BLOCKING_COUNTS)}`")
    canonical_runner_observations: dict[str, int] = {}
    for row in rows:
        if row["variant"] != "canonical_runner":
            continue
        code = row["finding_code"]
        canonical_runner_observations[code] = (
            canonical_runner_observations.get(code, 0) + 1
        )
    add(
        "- canonical runner observations: "
        f"`{_json(canonical_runner_observations)}`"
    )
    add(
        "- confirmed-defect baseline expected: "
        f"`{_json(CONFIRMED_DEFECT_BASELINE)}`"
    )
    add("- confirmed defect 1: `SHELL_RC_DISCARDED` — `ADB.shell` 이 returncode/stderr"
        " 를 폐기하고 stdout 만 반환, `ActionRunner._shell` 은 무조건 PASS"
        " (legacy `ADB.shell` / legacy `ActionRunner._shell` 경로)")
    add("- confirmed defect 2: `EXCEL_SWIPE_ENDPOINT_MISSING` — Excel producer 의"
        " swipe 입력 계약에 x2/y2 부재, runner 에서 KeyError"
        " (legacy Excel producer / runner swipe 경로)")
    add("")
    add("## 6. Adapter acceptance checklist (Slice 1a targets)")
    add("- [ ] `text`→`target` 은 selector action 에만 적용 —"
        " `input_text.text` 는 입력값 payload, 절대 변환 금지")
    add("- [x] `id`→`target` (tap_id) + runner canonical 수용 정렬")
    add("- [ ] `seconds`→`duration`(ms), equal-duplicate 일관성 확인,"
        " conflicting-duplicate 는 오류")
    add("- [ ] `keycode`→`key`")
    add("- [ ] `x1/y1`→`x/y`; Excel swipe endpoint 입력 계약 수정이 선행")
    add("- [ ] top-level `name`→`tc_name`")
    add("- [ ] screenshot `name` schema 정식 편입")
    add("- [x] `verify_shell.timeout` ms→s 변환을 ADB 경계에서 수행")
    add("- [ ] `key_sequence.delay` 는 v1 정규화 대상 아님 (seconds 유지, 관찰만)")
    add("- [x] shell returncode/stderr 구조화 반환")
    add("")
    add("## 7. Output hash / self-check")
    kinds: dict[str, int] = {}
    for r in rows:
        kinds[r["actor_kind"]] = kinds.get(r["actor_kind"], 0) + 1
    add(f"- rows: {len(rows)} ({_json(kinds)})")
    add(f"- contract_drift_matrix.csv sha256: `{sha256_bytes(csv_bytes)}`")
    add("- self-check: PASS (structural invariants only; input snapshot verified before write)")
    add("")
    reported_lines: list[str] = []
    for line in lines:
        if line.startswith("- primary counts (locked):"):
            reported_lines.append(f"- primary counts observed: {primary}")
            reported_lines.append(f"- baseline expected: {PRIMARY_COUNTS}")
        elif line.startswith("- THOR2_K target count (informational only):"):
            observed = group_counts.get("thor2k_settings_smoke", {}).get(
                "file_count", "-"
            )
            reported_lines.append(
                "- THOR2_K target count observed (informational only): "
                f"{observed}"
            )
        elif line.startswith("## 5. Blocking findings / confirmed defects"):
            section_status = (
                "observed defects" if blocking else "baseline defect status"
            )
            reported_lines.append(f"## 5. Blocking findings / {section_status}")
        elif line.startswith("- confirmed defect 1:"):
            if blocking.get("SHELL_RC_DISCARDED"):
                reported_lines.append(
                    line.replace("- confirmed defect 1:", "- observed defect 1:", 1)
                )
            else:
                reported_lines.append(
                    "- baseline defect 1 not observed (fixed candidate): "
                    "`SHELL_RC_DISCARDED`"
                )
        elif line.startswith("- confirmed defect 2:"):
            if blocking.get("EXCEL_SWIPE_ENDPOINT_MISSING"):
                reported_lines.append(
                    line.replace("- confirmed defect 2:", "- observed defect 2:", 1)
                )
            else:
                reported_lines.append(
                    "- baseline defect 2 not observed (fixed candidate): "
                    "`EXCEL_SWIPE_ENDPOINT_MISSING`"
                )
        else:
            reported_lines.append(line)
    return "\n".join(reported_lines).encode("utf-8")


def write_outputs(
    rows: list[dict],
    out_dir: Path,
    input_digest: str,
    input_snapshot: dict[str, dict[str, int | str]],
) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    source_state = input_snapshot
    digest = input_digest
    csv_bytes = render_csv_bytes(rows)
    summary_bytes = render_summary_bytes(rows, digest, csv_bytes, source_state)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "contract_drift_matrix.csv"
    summary_path = out_dir / "SUMMARY.md"
    csv_path.write_bytes(csv_bytes)
    summary_path.write_bytes(summary_bytes)
    return csv_path, summary_path


# ─── self-check + main ───

def _build_all_rows() -> list[dict]:
    fixtures = build_fixture_matrix()
    rows = probe_consumers(fixtures)
    rows.extend(probe_producers(fixtures))
    rows.extend(scan_corpora())
    return rows


def _self_check(rows: list[dict]) -> list[str]:
    problems = []
    expected_pairs = {
        (producer, mode, consumer)
        for producer in PRODUCERS
        for mode in PRODUCER_MODES
        for consumer in CONSUMERS
    }
    pair_counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        if row["actor_kind"] == "pair":
            pair = (row["producer"], row["variant"], row["consumer"])
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    pairs = set(pair_counts)
    if pairs != expected_pairs:
        problems.append(f"pair groups != 16: {sorted(pairs)}")
    duplicates = sorted(pair for pair, count in pair_counts.items() if count != 1)
    if duplicates:
        problems.append(f"duplicate pair groups: {duplicates}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="contract drift ledger (Slice 0.5)")
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "reports" / "contract_drift"))
    ap.add_argument("--verify-determinism", action="store_true",
                    help="전체 파이프라인 2회 실행 후 byte 동일성 검증")
    ap.add_argument("--fail-on-blocking", action="store_true",
                    help="blocking finding 존재 시 exit 1")
    args = ap.parse_args(argv)

    try:
        input_before = snapshot_inputs()
        digest_before = compute_input_digest(input_before)
        rows = _build_all_rows()
    except LedgerInputError as e:
        print(f"ERROR: input read/parse 실패: {e}", file=sys.stderr)
        return 2
    except (OSError, yaml.YAMLError) as e:
        print(f"ERROR: input read/parse 실패: {e}", file=sys.stderr)
        return 2

    problems = _self_check(rows)

    if args.verify_determinism:
        rows2 = _build_all_rows()
        csv1, csv2 = render_csv_bytes(rows), render_csv_bytes(rows2)
        if csv1 != csv2:
            problems.append("determinism: CSV bytes 2회 실행 불일치")
        else:
            s1 = render_summary_bytes(rows, digest_before, csv1, input_before)
            s2 = render_summary_bytes(rows2, digest_before, csv2, input_before)
            if s1 != s2:
                problems.append("determinism: SUMMARY bytes 2회 실행 불일치")

    if problems:
        for p in problems:
            print(f"SELF-CHECK FAIL: {p}", file=sys.stderr)
        return 3

    out_dir = Path(args.out_dir) / digest_before[:16]
    try:
        input_after = snapshot_inputs()
    except (LedgerInputError, OSError) as exc:
        print(f"SELF-CHECK FAIL: final input snapshot failed: {exc}", file=sys.stderr)
        return 3
    if input_after != input_before:
        print("SELF-CHECK FAIL: 입력 소스 hash 가 scan 중 변경됨", file=sys.stderr)
        return 3

    csv_path, summary_path = write_outputs(
        rows, out_dir, digest_before, input_before,
    )

    blocking = [r for r in rows if r["verdict"] == "blocking"]
    print(f"rows={len(rows)} blocking={len(blocking)}")
    print(f"csv={csv_path}")
    print(f"summary={summary_path}")
    if args.fail_on_blocking and blocking:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
