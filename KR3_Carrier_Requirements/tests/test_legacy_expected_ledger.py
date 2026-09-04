import copy
import datetime
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from g0a_common import G0AError, canonical_json_bytes
from build_legacy_expected_ledger import (
    check_ledger,
    extract_expected,
    initialize_ledger,
    validate_ledger,
)


def write_case(directory: Path, filename: str, tc_id: str, steps: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(
        yaml.safe_dump({"tc_id": tc_id, "procedure_steps": steps}, allow_unicode=True),
        encoding="utf-8",
    )


def step(number: object, expected: object, trace: object = None) -> dict:
    return {"step_no": number, "source_trace": trace, "expected": expected}


def expected(value: str) -> dict:
    return {"type": "verify_text", "value": value}


def assert_error_code(call, code: str) -> None:
    with pytest.raises(G0AError) as caught:
        call()
    assert caught.value.code == code


def assert_json_domain_error(call, code: str) -> None:
    with pytest.raises(G0AError) as caught:
        call()
    assert caught.value.code == code
    assert "canonical JSON" in caught.value.detail


def schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "contracts" / "legacy_expected_ledger_schema_v1.json"


def script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tools" / "build_legacy_expected_ledger.py"


class SchemaConformanceError(AssertionError):
    pass


_SUPPORTED_SCHEMA_KEYWORDS = {
    "$schema",
    "additionalProperties",
    "const",
    "enum",
    "items",
    "minimum",
    "minLength",
    "pattern",
    "properties",
    "required",
    "title",
    "type",
}
_SUPPORTED_SCHEMA_TYPES = {"array", "integer", "null", "object", "string"}
_SUPPORTED_ANCHORED_PATTERN = re.compile(
    r"\^([A-Za-z0-9-]*)(\[(?:0-9|0-9a-f)\])\{([1-9][0-9]*)\}\$\Z"
)


def _schema_error(path: str, detail: str) -> None:
    raise SchemaConformanceError(f"{path}: {detail}")


def _compile_supported_anchored_pattern(pattern: str, path: str) -> re.Pattern[str]:
    """Translate only the anchored ASCII subset used by the published schema."""
    matched = _SUPPORTED_ANCHORED_PATTERN.fullmatch(pattern)
    if matched is None:
        _schema_error(path, "unsupported anchored pattern")
    literal_prefix, character_class, repeat_count = matched.groups()
    return re.compile(
        rf"{re.escape(literal_prefix)}{character_class}{{{repeat_count}}}",
        flags=re.ASCII,
    )


def _assert_supported_schema(schema: object, path: str) -> None:
    if not isinstance(schema, dict):
        _schema_error(path, "schema must be an object")
    unsupported = sorted(set(schema) - _SUPPORTED_SCHEMA_KEYWORDS)
    if unsupported:
        _schema_error(path, f"unsupported schema keyword: {unsupported[0]}")

    declared_type = schema.get("type")
    if declared_type is not None:
        declared_types = declared_type if isinstance(declared_type, list) else [declared_type]
        if not declared_types or any(
            not isinstance(item, str) or item not in _SUPPORTED_SCHEMA_TYPES
            for item in declared_types
        ):
            _schema_error(path, "unsupported schema type")
    if "$schema" in schema and not isinstance(schema["$schema"], str):
        _schema_error(path, "$schema must be a string")
    if "title" in schema and not isinstance(schema["title"], str):
        _schema_error(path, "title must be a string")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        _schema_error(path, "additionalProperties must be boolean")
    if "required" in schema and (
        not isinstance(schema["required"], list)
        or any(not isinstance(item, str) for item in schema["required"])
    ):
        _schema_error(path, "required must be a string array")
    if "properties" in schema:
        properties = schema["properties"]
        if not isinstance(properties, dict) or any(not isinstance(key, str) for key in properties):
            _schema_error(path, "properties must be an object with string keys")
        for key, subschema in properties.items():
            _assert_supported_schema(subschema, f"{path}.properties.{key}")
    if "items" in schema:
        _assert_supported_schema(schema["items"], f"{path}.items")
    if "enum" in schema and not isinstance(schema["enum"], list):
        _schema_error(path, "enum must be an array")
    if "minimum" in schema and (
        isinstance(schema["minimum"], bool)
        or not isinstance(schema["minimum"], (int, float))
    ):
        _schema_error(path, "minimum must be a number")
    if "minLength" in schema and (
        isinstance(schema["minLength"], bool)
        or not isinstance(schema["minLength"], int)
        or schema["minLength"] < 0
    ):
        _schema_error(path, "minLength must be a nonnegative integer")
    if "pattern" in schema:
        if not isinstance(schema["pattern"], str):
            _schema_error(path, "pattern must be a string")
        _compile_supported_anchored_pattern(schema["pattern"], path)


def _matches_schema_type(instance: object, declared_type: str) -> bool:
    if declared_type == "null":
        return instance is None
    if declared_type == "object":
        return isinstance(instance, dict)
    if declared_type == "array":
        return isinstance(instance, list)
    if declared_type == "string":
        return isinstance(instance, str)
    if declared_type == "integer":
        if isinstance(instance, int) and not isinstance(instance, bool):
            return True
        return (
            isinstance(instance, float)
            and math.isfinite(instance)
            and instance.is_integer()
        )
    raise AssertionError(f"unsupported checked type: {declared_type}")


def _same_json_value(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def _validate_schema_instance(schema: dict, instance: object, path: str) -> None:
    declared_type = schema.get("type")
    if declared_type is not None:
        declared_types = declared_type if isinstance(declared_type, list) else [declared_type]
        if not any(_matches_schema_type(instance, item) for item in declared_types):
            _schema_error(path, f"type mismatch: expected {declared_types}")
    if "const" in schema and not _same_json_value(instance, schema["const"]):
        _schema_error(path, "const mismatch")
    if "enum" in schema and not any(_same_json_value(instance, item) for item in schema["enum"]):
        _schema_error(path, "enum mismatch")
    if "minimum" in schema and instance < schema["minimum"]:
        _schema_error(path, "minimum violation")
    if "minLength" in schema and len(instance) < schema["minLength"]:
        _schema_error(path, "minLength violation")
    if "pattern" in schema:
        compiled_pattern = _compile_supported_anchored_pattern(schema["pattern"], path)
        if compiled_pattern.fullmatch(instance) is None:
            _schema_error(path, "pattern mismatch")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for required_key in schema.get("required", []):
            if required_key not in instance:
                _schema_error(path, f"missing required property: {required_key}")
        if schema.get("additionalProperties", True) is False:
            extras = sorted(set(instance) - set(properties))
            if extras:
                _schema_error(path, f"additional property: {extras[0]}")
        for key, subschema in properties.items():
            if key in instance:
                _validate_schema_instance(subschema, instance[key], f"{path}.{key}")
    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            _validate_schema_instance(schema["items"], item, f"{path}[{index}]")


def validate_schema_contract(schema: object, instance: object) -> None:
    """Validate against every keyword used by the checked-in ledger schema."""
    _assert_supported_schema(schema, "$")
    _validate_schema_instance(schema, instance, "$")


def test_initialize_assigns_global_ids_from_sorted_tc_step_and_expected_indexes(tmp_path):
    write_case(
        tmp_path,
        "z_canonical.yaml",
        "TC_B",
        [step(2, [expected("b2")]), step(1, [expected("b1"), expected("b1-second")])],
    )
    write_case(tmp_path, "a_canonical.yaml", "TC_A", [step(4, [expected("a4")])])

    ledger = initialize_ledger(tmp_path)

    assert [(item["legacy_expected_id"], item["tc_id"], item["step_no"], item["expected_index"])
            for item in ledger["items"]] == [
        ("LGU-EXP-000001", "TC_A", 4, 1),
        ("LGU-EXP-000002", "TC_B", 1, 1),
        ("LGU-EXP-000003", "TC_B", 1, 2),
        ("LGU-EXP-000004", "TC_B", 2, 1),
    ]
    assert ledger["case_count"] == 2
    assert ledger["expected_count"] == 4


def test_logically_identical_yaml_key_orders_produce_identical_ledger_bytes(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "one_canonical.yaml").write_text(
        "tc_id: TC_A\nprocedure_steps:\n  - step_no: 1\n    source_trace: {position: 1}\n    expected: [{value: alpha, type: verify_text}]\n",
        encoding="utf-8",
    )
    (second / "one_canonical.yaml").write_text(
        "procedure_steps:\n  - expected: [{type: verify_text, value: alpha}]\n    source_trace: {position: 1}\n    step_no: 1\ntc_id: TC_A\n",
        encoding="utf-8",
    )

    assert canonical_json_bytes(initialize_ledger(first)) == canonical_json_bytes(initialize_ledger(second))


def test_generated_ledger_validates_against_real_draft_2020_12_schema(tmp_path):
    write_case(
        tmp_path / "stage1",
        "one_canonical.yaml",
        "TC_A",
        [
            step(
                1,
                [{"type": "verify_text", "value": "alpha", "source_specific": ["preserved"]}],
                {"position": 1, "source_specific": {"preserved": True}},
            )
        ],
    )
    ledger = initialize_ledger(tmp_path / "stage1")
    schema = json.loads(schema_path().read_text(encoding="utf-8"))

    validate_schema_contract(schema, ledger)


def test_schema_contract_rejects_invalid_generated_instance(tmp_path):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    ledger["items"][0]["unexpected"] = True
    schema = json.loads(schema_path().read_text(encoding="utf-8"))

    with pytest.raises(SchemaConformanceError, match="additional property"):
        validate_schema_contract(schema, ledger)


def test_schema_contract_fails_closed_for_unsupported_schema_keyword(tmp_path):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    schema["properties"]["case_count"]["maximum"] = 28

    with pytest.raises(SchemaConformanceError, match="unsupported schema keyword: maximum"):
        validate_schema_contract(schema, ledger)


@pytest.mark.parametrize("location", ["schema_version", "case_count", "step_no"])
def test_schema_integer_accepts_finite_integral_json_numbers(tmp_path, location):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    if location == "schema_version":
        ledger["schema_version"] = 1.0
    elif location == "case_count":
        ledger["case_count"] = 0.0
    else:
        ledger["items"][0]["step_no"] = 1.0
    schema = json.loads(schema_path().read_text(encoding="utf-8"))

    validate_schema_contract(schema, ledger)


@pytest.mark.parametrize(
    "invalid_integer",
    [True, False, math.nan, math.inf, -math.inf, 0.5, 1.5],
)
def test_schema_integer_rejects_bool_nonfinite_and_nonintegral_numbers(tmp_path, invalid_integer):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    ledger["case_count"] = invalid_integer
    schema = json.loads(schema_path().read_text(encoding="utf-8"))

    with pytest.raises(SchemaConformanceError, match="type mismatch"):
        validate_schema_contract(schema, ledger)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("legacy_expected_id", "LGU-EXP-000001\n"),
        ("fingerprint_sha256", "0" * 64 + "\n"),
    ],
)
def test_schema_anchored_patterns_reject_final_newline_bypass(tmp_path, field, value):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    ledger["items"][0][field] = value
    schema = json.loads(schema_path().read_text(encoding="utf-8"))

    with pytest.raises(SchemaConformanceError, match="pattern mismatch"):
        validate_schema_contract(schema, ledger)


def test_schema_pattern_checker_fails_closed_for_unsupported_construct(tmp_path):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    schema["properties"]["items"]["items"]["properties"]["legacy_expected_id"]["pattern"] = "^LGU-EXP-.*$"

    with pytest.raises(SchemaConformanceError, match="unsupported anchored pattern"):
        validate_schema_contract(schema, ledger)


def test_check_rejects_changed_expected_as_drift(tmp_path):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("before")])])
    ledger = initialize_ledger(tmp_path)
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("after")])])

    assert_error_code(lambda: check_ledger(tmp_path, ledger), "LEGACY_EXPECTED_DRIFT")


@pytest.mark.parametrize(
    ("original_steps", "changed_steps"),
    [
        ([step(1, [expected("one")])], [step(1, [expected("one"), expected("two")])]),
        ([step(1, [expected("one"), expected("two")])], [step(1, [expected("one")])]),
    ],
)
def test_check_rejects_added_or_removed_expected_as_set_drift(tmp_path, original_steps, changed_steps):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", original_steps)
    ledger = initialize_ledger(tmp_path)
    write_case(tmp_path, "one_canonical.yaml", "TC_A", changed_steps)

    assert_error_code(lambda: check_ledger(tmp_path, ledger), "LEGACY_EXPECTED_SET_DRIFT")


@pytest.mark.parametrize(
    ("cases", "code"),
    [
        ([("a_canonical.yaml", "TC_A", [step(1, [expected("a")])]), ("b_canonical.yaml", "TC_A", [step(2, [expected("b")])])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [step(1, [expected("a")]), step(1, [expected("b")])])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [step(0, [expected("a")])])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [step(True, [expected("a")])])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [{"step_no": 1, "source_trace": None}])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [step(1, [])])], "LEGACY_EXPECTED_INPUT_INVALID"),
        ([("a_canonical.yaml", "TC_A", [step(1, ["not-a-mapping"])])], "LEGACY_EXPECTED_INPUT_INVALID"),
    ],
)
def test_extract_fails_closed_for_invalid_cases(tmp_path, cases, code):
    for filename, tc_id, steps in cases:
        write_case(tmp_path, filename, tc_id, steps)

    assert_error_code(lambda: extract_expected(tmp_path), code)


def test_extract_fails_closed_for_empty_input(tmp_path):
    assert_error_code(lambda: extract_expected(tmp_path), "LEGACY_EXPECTED_INPUT_INVALID")


@pytest.mark.parametrize(
    "yaml_value",
    [
        "{1: alpha}",
        "2026-08-14",
        "2026-08-14T12:34:56Z",
        "!!set {alpha: null}",
        '!!binary "AAE="',
        ".nan",
        ".inf",
    ],
)
def test_extract_rejects_values_outside_canonical_json_domain(tmp_path, yaml_value):
    (tmp_path / "bad_canonical.yaml").write_text(
        "tc_id: TC_A\n"
        "procedure_steps:\n"
        "  - step_no: 1\n"
        "    source_trace: null\n"
        "    expected:\n"
        "      - type: verify_text\n"
        f"        value: {yaml_value}\n",
        encoding="utf-8",
    )

    assert_json_domain_error(
        lambda: extract_expected(tmp_path),
        "LEGACY_EXPECTED_INPUT_INVALID",
    )


def test_extract_rejects_invalid_utf8_as_controlled_error(tmp_path):
    (tmp_path / "bad_canonical.yaml").write_bytes(b"\xff")

    assert_error_code(lambda: extract_expected(tmp_path), "LEGACY_EXPECTED_INPUT_INVALID")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda ledger: ledger["items"][0].__setitem__("fingerprint_sha256", "0" * 64),
        lambda ledger: ledger["items"][0].__setitem__("legacy_expected_id", "LGU-EXP-000002"),
        lambda ledger: ledger.__setitem__("case_count", 99),
        lambda ledger: ledger["items"].reverse(),
        lambda ledger: ledger["items"][0].__setitem__("status", "RETIRED"),
    ],
)
def test_validate_rejects_tampering_without_repair(tmp_path, mutate):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")]), step(2, [expected("two")])])
    ledger = initialize_ledger(tmp_path)
    mutate(ledger)

    assert_error_code(lambda: validate_ledger(ledger), "LEGACY_EXPECTED_LEDGER_INVALID")


def test_validate_rejects_duplicate_ids(tmp_path):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one"), expected("two")])])
    ledger = initialize_ledger(tmp_path)
    ledger["items"][1]["legacy_expected_id"] = ledger["items"][0]["legacy_expected_id"]

    assert_error_code(lambda: validate_ledger(ledger), "LEGACY_EXPECTED_LEDGER_INVALID")


@pytest.mark.parametrize(
    "invalid_value",
    [
        {1: "alpha"},
        datetime.date(2026, 8, 14),
        datetime.datetime(2026, 8, 14, 12, 34, 56),
        {"alpha"},
        b"\x00\x01",
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_validate_rejects_values_outside_canonical_json_domain(tmp_path, invalid_value):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    ledger["items"][0]["expected"]["value"] = invalid_value

    assert_json_domain_error(
        lambda: validate_ledger(ledger),
        "LEGACY_EXPECTED_LEDGER_INVALID",
    )


@pytest.mark.parametrize("location", ["value", "mapping_key"])
def test_validate_rejects_non_utf8_encodable_strings_and_mapping_keys(tmp_path, location):
    write_case(tmp_path, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(tmp_path)
    surrogate = chr(0xD800)
    if location == "value":
        ledger["items"][0]["expected"]["value"] = surrogate
    else:
        ledger["items"][0]["expected"][surrogate] = "alpha"

    assert_json_domain_error(
        lambda: validate_ledger(ledger),
        "LEGACY_EXPECTED_LEDGER_INVALID",
    )


@pytest.mark.parametrize("contents", ["[not, a, mapping]", "tc_id: TC_A\nprocedure_steps: ["])
def test_extract_reports_yaml_decode_or_nonmapping_root_as_controlled_error(tmp_path, contents):
    (tmp_path / "bad_canonical.yaml").write_text(contents, encoding="utf-8")

    assert_error_code(lambda: extract_expected(tmp_path), "LEGACY_EXPECTED_INPUT_INVALID")


def test_cli_init_and_check_succeed_and_bad_ledger_has_no_traceback(tmp_path):
    write_case(tmp_path / "stage1", "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    script = script_path()
    ledger_path = tmp_path / "ledger.json"

    initialized = subprocess.run(
        [sys.executable, str(script), "init", "--stage1", str(tmp_path / "stage1"), "--out", str(ledger_path)],
        capture_output=True, text=True, check=False,
    )
    checked = subprocess.run(
        [sys.executable, str(script), "check", "--stage1", str(tmp_path / "stage1"), "--ledger", str(ledger_path)],
        capture_output=True, text=True, check=False,
    )
    ledger_path.write_text("{", encoding="utf-8")
    malformed = subprocess.run(
        [sys.executable, str(script), "check", "--stage1", str(tmp_path / "stage1"), "--ledger", str(ledger_path)],
        capture_output=True, text=True, check=False,
    )

    assert initialized.returncode == checked.returncode == 0
    assert initialized.stdout.strip() == checked.stdout.strip() == "cases=1 expected=1 drift=0"
    assert malformed.returncode == 2
    assert "Traceback" not in malformed.stderr


def test_cli_invalid_utf8_yaml_and_ledger_exit_2_without_traceback(tmp_path):
    stage1 = tmp_path / "stage1"
    stage1.mkdir()
    (stage1 / "bad_canonical.yaml").write_bytes(b"\xff")
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_bytes(b"\xff")

    bad_yaml = subprocess.run(
        [sys.executable, str(script_path()), "init", "--stage1", str(stage1), "--out", str(tmp_path / "out.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    bad_ledger = subprocess.run(
        [sys.executable, str(script_path()), "check", "--stage1", str(stage1), "--ledger", str(ledger_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert bad_yaml.returncode == bad_ledger.returncode == 2
    assert "LEGACY_EXPECTED_INPUT_INVALID" in bad_yaml.stderr
    assert "LEGACY_EXPECTED_LEDGER_INVALID" in bad_ledger.stderr
    assert "Traceback" not in bad_yaml.stderr
    assert "Traceback" not in bad_ledger.stderr


@pytest.mark.parametrize(
    "expected_lines",
    [
        '        value: "\\uD800"\n',
        '        value: one\n        "\\uD800": alpha\n',
    ],
)
def test_cli_yaml_surrogate_value_or_key_exits_2_without_traceback(tmp_path, expected_lines):
    stage1 = tmp_path / "stage1"
    stage1.mkdir()
    (stage1 / "bad_canonical.yaml").write_text(
        "tc_id: TC_A\n"
        "procedure_steps:\n"
        "  - step_no: 1\n"
        "    source_trace: null\n"
        "    expected:\n"
        "      - type: verify_text\n"
        + expected_lines,
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(script_path()), "init", "--stage1", str(stage1), "--out", str(tmp_path / "out.json")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "LEGACY_EXPECTED_INPUT_INVALID" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("location", ["value", "mapping_key"])
def test_cli_ledger_json_surrogate_value_or_key_exits_2_without_traceback(tmp_path, location):
    stage1 = tmp_path / "stage1"
    write_case(stage1, "one_canonical.yaml", "TC_A", [step(1, [expected("one")])])
    ledger = initialize_ledger(stage1)
    surrogate = chr(0xD800)
    if location == "value":
        ledger["items"][0]["expected"]["value"] = surrogate
    else:
        ledger["items"][0]["expected"][surrogate] = "alpha"
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=True), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script_path()), "check", "--stage1", str(stage1), "--ledger", str(ledger_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "LEGACY_EXPECTED_LEDGER_INVALID" in result.stderr
    assert "Traceback" not in result.stderr


def test_schema_is_closed_and_constrains_ids_hashes_and_positive_numbers():
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    item = schema["properties"]["items"]["items"]

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "case_count", "expected_count", "items"}
    assert item["additionalProperties"] is False
    assert item["properties"]["legacy_expected_id"]["pattern"] == "^LGU-EXP-[0-9]{6}$"
    assert item["properties"]["fingerprint_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert item["properties"]["step_no"]["minimum"] == 1
    assert item["properties"]["expected_index"]["minimum"] == 1
    assert item["properties"]["status"]["enum"] == ["ACTIVE"]
    assert item["properties"]["step_source_trace"] == {"type": ["object", "null"]}
    assert item["properties"]["expected"] == {"type": "object"}


def test_real_stage1_initializes_and_checks_all_legacy_expected_entries_read_only():
    stage1 = Path(__file__).resolve().parents[1] / "stage1"
    if not stage1.exists():
        pytest.skip("local-carry artifact absent: KR3_Carrier_Requirements/stage1")

    ledger = initialize_ledger(stage1)
    check_ledger(stage1, ledger)
    validate_schema_contract(
        json.loads(schema_path().read_text(encoding="utf-8")),
        ledger,
    )

    assert ledger["case_count"] == 28
    assert ledger["expected_count"] == 232
