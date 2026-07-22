"""Canonical execution-contract normalization and schema helpers.

This module is the single ingress adapter for Slice 1a.  It converts declared
legacy aliases on deep copies, records stable findings, and leaves runtime
objects untouched when a conversion would require guessing.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


CANONICAL_TC_CLASSES = frozenset({"FULL_AUTO", "SEMI_AUTO", "AMBIGUOUS_NL"})

# normalize_step has no schema parameter by design.  This registry therefore
# describes the v1 contract boundary owned by this module.  Fields consumed by
# the current compiler/validator but intentionally left open in JSON Schema are
# included so they are preserved without a false undeclared-field observation.
_DECLARED_STEP_FIELDS = frozenset(
    {
        "action",
        "execution_mode",
        "step_role",
        "compile_status",
        "target",
        "command",
        "expected",
        "text",
        "key",
        "keys",
        "delay",
        "trigger_action",
        "trigger_step",
        "focus_model",
        "x",
        "y",
        "x2",
        "y2",
        "duration",
        "name",
        "description",
        "manual_timeout",
        "on_timeout",
        "timeout",
        "retry",
        "post_wait",
        "lint_allow",
        "wait_intent",
        "selector_fallback_reason",
        "source_trace",
        "warnings",
        "_unresolved_params",
    }
)

_ACTION_ALIASES = {
    "tap_text": frozenset({"text"}),
    "verify_text": frozenset({"text"}),
    "verify_gone": frozenset({"text"}),
    "tap_id": frozenset({"id"}),
    "wait": frozenset({"seconds"}),
    "key": frozenset({"keycode"}),
    "swipe": frozenset({"x1", "y1"}),
}


@dataclass(frozen=True)
class ContractFinding:
    code: str
    path: str
    severity: str
    canonical_field: str | None
    observed_field: str | None
    detail: str


@dataclass(frozen=True)
class NormalizationResult:
    value: dict
    findings: tuple[ContractFinding, ...]

    @property
    def blocking(self) -> bool:
        return any(finding.severity == "ERROR" for finding in self.findings)


def _strict_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON-like values without Python's bool/int equivalence."""
    return type(left) is type(right) and left == right


def _finding(
    code: str,
    path: str,
    severity: str,
    canonical_field: str | None,
    observed_field: str | None,
    detail: str,
) -> ContractFinding:
    return ContractFinding(
        code=code,
        path=path,
        severity=severity,
        canonical_field=canonical_field,
        observed_field=observed_field,
        detail=detail,
    )


def _seconds_to_exact_ms(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a duration")
    try:
        seconds = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("seconds must be numeric") from None
    if not seconds.is_finite() or seconds < 0:
        raise ValueError("seconds must be finite and nonnegative")
    _sign, digits, exponent = seconds.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if coefficient == 0:
        return 0

    # Multiplying Decimal values uses the ambient precision context and can
    # round long, otherwise valid decimal text.  Shift the tuple exponent
    # directly so the seconds -> milliseconds conversion is lossless.
    millisecond_exponent = exponent + 3
    if millisecond_exponent >= 0:
        return coefficient * (10**millisecond_exponent)

    fractional_digits = -millisecond_exponent
    if fractional_digits >= len(digits):
        raise ValueError("seconds loses precision below one millisecond")
    divisor = 10**fractional_digits
    milliseconds, remainder = divmod(coefficient, divisor)
    if remainder:
        raise ValueError("seconds loses precision below one millisecond")
    return milliseconds


def _apply_alias(
    value: dict[str, Any],
    findings: list[ContractFinding],
    *,
    alias: str,
    canonical: str,
    path: str,
    transform=None,
) -> None:
    if alias not in value:
        return

    observed = value[alias]
    if transform is not None:
        try:
            normalized = transform(observed)
        except ValueError as exc:
            findings.append(
                _finding(
                    "INVALID_UNIT",
                    f"{path}.{alias}",
                    "ERROR",
                    canonical,
                    alias,
                    str(exc),
                )
            )
            return
    else:
        normalized = observed

    if canonical not in value:
        value[canonical] = normalized
        del value[alias]
        findings.append(
            _finding(
                "ALIAS_NORMALIZED",
                f"{path}.{alias}",
                "INFO",
                canonical,
                alias,
                f"legacy field '{alias}' normalized to '{canonical}'",
            )
        )
        return

    if _strict_json_equal(value[canonical], normalized):
        del value[alias]
        findings.append(
            _finding(
                "ALIAS_DUPLICATE",
                f"{path}.{alias}",
                "INFO",
                canonical,
                alias,
                f"legacy field '{alias}' duplicates '{canonical}'",
            )
        )
        return

    # Fail sticky: retain both values so a second normalization cannot launder
    # a conflict into a finding-free canonical document.
    findings.append(
        _finding(
            "ALIAS_CONFLICT",
            f"{path}.{alias}",
            "ERROR",
            canonical,
            alias,
            f"legacy field '{alias}' conflicts with '{canonical}'",
        )
    )


def normalize_step(
    step: Mapping[str, Any], *, path: str
) -> NormalizationResult:
    """Normalize one step on a deep copy and return deterministic findings."""
    if not isinstance(step, Mapping):
        raise TypeError("step must be a mapping")

    value: dict[str, Any] = copy.deepcopy(dict(step))
    findings: list[ContractFinding] = []
    action = value.get("action")

    if action in {"tap_text", "verify_text", "verify_gone"}:
        _apply_alias(
            value,
            findings,
            alias="text",
            canonical="target",
            path=path,
        )
    elif action == "tap_id":
        _apply_alias(
            value,
            findings,
            alias="id",
            canonical="target",
            path=path,
        )
    elif action == "wait":
        _apply_alias(
            value,
            findings,
            alias="seconds",
            canonical="duration",
            path=path,
            transform=_seconds_to_exact_ms,
        )
    elif action == "key":
        _apply_alias(
            value,
            findings,
            alias="keycode",
            canonical="key",
            path=path,
        )
    elif action == "swipe":
        _apply_alias(value, findings, alias="x1", canonical="x", path=path)
        _apply_alias(value, findings, alias="y1", canonical="y", path=path)

    aliases_for_action = _ACTION_ALIASES.get(action, frozenset())
    for field in sorted(value):
        if field in _DECLARED_STEP_FIELDS or field in aliases_for_action:
            continue
        findings.append(
            _finding(
                "UNDECLARED_STEP_FIELD",
                f"{path}.{field}",
                "INFO",
                None,
                field,
                f"undeclared step field '{field}' preserved",
            )
        )

    return NormalizationResult(value=value, findings=tuple(findings))


def normalize_tc(tc: Mapping[str, Any], *, source: str) -> NormalizationResult:
    """Normalize a complete TC document without mutating caller-owned data."""
    if not isinstance(tc, Mapping):
        raise TypeError("tc must be a mapping")

    value: dict[str, Any] = copy.deepcopy(dict(tc))
    findings: list[ContractFinding] = []

    _apply_alias(
        value,
        findings,
        alias="name",
        canonical="tc_name",
        path=source,
    )

    metadata = value.get("metadata")
    if isinstance(metadata, Mapping):
        metadata_value = copy.deepcopy(dict(metadata))
        value["metadata"] = metadata_value
        automation_class = metadata_value.get("automation_class")
        if automation_class in CANONICAL_TC_CLASSES:
            _apply_alias(
                metadata_value,
                findings,
                alias="automation_class",
                canonical="tc_class",
                path=f"{source}.metadata",
            )

    steps = value.get("steps")
    if isinstance(steps, list):
        normalized_steps: list[Any] = []
        for index, step in enumerate(steps):
            if isinstance(step, Mapping):
                result = normalize_step(step, path=f"{source}.steps[{index}]")
                normalized_steps.append(result.value)
                findings.extend(result.findings)
            else:
                normalized_steps.append(copy.deepcopy(step))
        value["steps"] = normalized_steps

    return NormalizationResult(value=value, findings=tuple(findings))


def derive_action_required(
    schema: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Derive per-action required fields from JSON Schema allOf rules."""
    step_schema: Mapping[str, Any]
    defs = schema.get("$defs") if isinstance(schema, Mapping) else None
    if isinstance(defs, Mapping) and isinstance(defs.get("step"), Mapping):
        step_schema = defs["step"]
    else:
        step_schema = schema

    accumulated: dict[str, list[str]] = {}
    for rule in step_schema.get("allOf", []):
        if not isinstance(rule, Mapping):
            continue
        action = (
            rule.get("if", {})
            .get("properties", {})
            .get("action", {})
            .get("const")
        )
        required = rule.get("then", {}).get("required", [])
        if not isinstance(action, str) or not isinstance(required, list):
            continue
        fields = accumulated.setdefault(action, [])
        for field in required:
            if isinstance(field, str) and field not in fields:
                fields.append(field)
    return {action: tuple(fields) for action, fields in accumulated.items()}


def derive_execution_metadata(
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, str | bool]:
    """Derive the STAGE2 Step 4 execution metadata from structured steps."""
    manual_routed_steps = [
        step
        for step in steps
        if step.get("action") == "manual_pause"
        or step.get("execution_mode")
        in ("MANUAL_REQUIRED", "EXTERNAL_EVENT")
    ]
    descriptions = "\n".join(
        str(step.get("description", "")).lower()
        for step in manual_routed_steps
    )
    external_description_patterns = (
        r"보조폰",
        r"수신(?!함)",
        r"발신(?!함)",
        r"상대 단말",
        r"외부 이벤트",
        r"secondary phone",
        r"incoming call",
        r"receive call",
        r"outgoing call",
        r"place call",
        r"other device",
        r"external event",
    )
    has_external = any(
        step.get("execution_mode") == "EXTERNAL_EVENT" for step in steps
    ) or any(
        re.search(pattern, descriptions) is not None
        for pattern in external_description_patterns
    )
    has_manual_local = any(
        step.get("action") == "manual_pause"
        or step.get("execution_mode") == "MANUAL_REQUIRED"
        for step in steps
    )

    if has_external:
        execution_type = "EXTERNAL_EVENT"
    elif has_manual_local:
        execution_type = "MANUAL_LOCAL"
    else:
        return {
            "execution_type": "AUTO",
            "manual_detail": "NONE",
            "has_manual_steps": False,
        }

    detail_rules = (
        ("CALL_RECEIVE", ("수신", "incoming call", "receive call")),
        ("CALL_PLACE", ("발신", "텔레뱅킹", "outgoing call", "place call")),
        ("APP_INSTALL", ("설치", "사이드로딩", "sideload")),
        ("BUTTON_TOUCH", ("버튼", "터치", "button", "touch")),
        ("PHYSICAL_ACTION", ("usb", "sim", "물리", "케이블", "cable")),
        ("PAIRING", ("블루투스", "nfc", "페어링", "pairing")),
        ("MULTI_DEVICE", ("다중 디바이스", "다중 단말", "multi-device")),
        ("SERVER_CALLBACK", ("콜백", "callback")),
    )

    def marker_observed(marker: str) -> bool:
        if marker == "sim":
            return (
                re.search(
                    r"(?<![a-z0-9_])sim(?![a-z0-9_])",
                    descriptions,
                )
                is not None
            )
        if marker == "수신":
            return re.search(r"수신(?!함)", descriptions) is not None
        if marker == "발신":
            return re.search(r"발신(?!함)", descriptions) is not None
        return marker in descriptions

    details = [
        token
        for token, markers in detail_rules
        if any(marker_observed(marker) for marker in markers)
    ]
    if not details:
        details.append("UNKNOWN")
    return {
        "execution_type": execution_type,
        "manual_detail": "|".join(details),
        "has_manual_steps": True,
    }


def _required_value_missing(step: Mapping[str, Any], field: str) -> bool:
    if field not in step or step[field] is None:
        return True
    value = step[field]
    if isinstance(value, bool):
        return not value
    if isinstance(value, (str, bytes, list, tuple, dict, set)):
        return len(value) == 0
    return False


def validate_canonical_tc(
    tc: Mapping[str, Any], schema: Mapping[str, Any]
) -> list[str]:
    """Perform schema-derived structural checks on an already canonical TC."""
    errors: list[str] = []
    if not isinstance(tc, Mapping):
        return ["최상위가 dict가 아님"]

    for field in schema.get("required", []):
        if field not in tc:
            errors.append(f"필수 필드 누락: '{field}'")

    tc_name = tc.get("tc_name", "")
    if tc_name:
        pattern = schema.get("properties", {}).get("tc_name", {}).get("pattern", "")
        if pattern and (not isinstance(tc_name, str) or not re.match(pattern, tc_name)):
            errors.append(
                f"tc_name 형식 불일치: '{tc_name}' (허용: 영문/숫자/_/-)"
            )

    metadata = tc.get("metadata", {})
    metadata_schema = schema.get("properties", {}).get("metadata", {})
    if not isinstance(metadata, Mapping):
        errors.append("metadata 형식 오류: object여야 함")
        metadata = {}
    for field in metadata_schema.get("required", []):
        if field not in metadata:
            errors.append(f"metadata 필수 필드 누락: '{field}'")

    tc_class = metadata.get("tc_class", "")
    valid_classes = (
        metadata_schema.get("properties", {}).get("tc_class", {}).get("enum", [])
    )
    if tc_class and tc_class not in valid_classes:
        errors.append(f"tc_class 값 불일치: '{tc_class}' (허용: {valid_classes})")

    valid_exec_types = {"AUTO", "MANUAL_LOCAL", "EXTERNAL_EVENT"}
    valid_detail_tokens = {
        "NONE",
        "CALL_RECEIVE",
        "CALL_PLACE",
        "APP_INSTALL",
        "BUTTON_TOUCH",
        "PHYSICAL_ACTION",
        "PAIRING",
        "MULTI_DEVICE",
        "SERVER_CALLBACK",
        "UNKNOWN",
    }

    exec_type = metadata.get("execution_type")
    manual_detail = metadata.get("manual_detail")
    if exec_type is None:
        errors.append("metadata 필수 필드 누락: 'execution_type'")
    elif exec_type not in valid_exec_types:
        errors.append(
            f"execution_type 값 불일치: '{exec_type}' "
            f"(허용: {sorted(valid_exec_types)})"
        )

    if manual_detail is None:
        errors.append("metadata 필수 필드 누락: 'manual_detail'")
    else:
        detail_str = str(manual_detail)
        for token in detail_str.split("|"):
            if token not in valid_detail_tokens:
                errors.append(
                    f"manual_detail 토큰 불일치: '{token}' "
                    f"(허용: {sorted(valid_detail_tokens)})"
                )

    if exec_type and manual_detail is not None:
        detail_str = str(manual_detail)
        if exec_type == "AUTO" and detail_str != "NONE":
            errors.append(
                "일관성 오류: execution_type=AUTO 이면 manual_detail='NONE' "
                f"이어야 함 (현재: '{detail_str}')"
            )
        if exec_type != "AUTO" and detail_str == "NONE":
            errors.append(
                f"일관성 오류: execution_type={exec_type} 이면 "
                "manual_detail='NONE' 이 아니어야 함"
            )

    has_manual = metadata.get("has_manual_steps")
    if exec_type and has_manual is not None:
        if exec_type == "AUTO" and has_manual is True:
            errors.append(
                "일관성 오류: execution_type=AUTO 이면 "
                "has_manual_steps=false 이어야 함"
            )
        if exec_type in ("MANUAL_LOCAL", "EXTERNAL_EVENT") and has_manual is False:
            errors.append(
                f"일관성 오류: execution_type={exec_type} 이면 "
                "has_manual_steps=true 이어야 함"
            )

    steps = tc.get("steps", [])
    step_mappings = (
        [step for step in steps if isinstance(step, Mapping)]
        if isinstance(steps, list)
        else []
    )
    if exec_type:
        expected_exec_type = str(
            derive_execution_metadata(step_mappings)["execution_type"]
        )
        if exec_type != expected_exec_type:
            errors.append(
                f"일관성 오류: step 분석 결과 execution_type='{expected_exec_type}' "
                f"이어야 하나, metadata에 '{exec_type}' 으로 설정됨"
            )

    valid_runnable_reasons = {
        "FIXTURE_REQUIRED",
        "MUTATION_UNMANAGED",
        "INFEASIBLE_VERIFIER",
        "UNRESOLVED_PARAMS",
        "MANUAL_FALLBACK",
    }
    runnable_reason = metadata.get("runnable_reason")
    if runnable_reason is not None:
        if not isinstance(runnable_reason, list):
            errors.append(
                "runnable_reason 형식 오류: 배열이어야 함 "
                f"(현재: {type(runnable_reason).__name__})"
            )
        else:
            for reason in runnable_reason:
                # Keep the type guard before set membership.  list/dict values
                # are unhashable and must become validation errors, not crashes.
                if not isinstance(reason, str):
                    errors.append(
                        "runnable_reason 원소 형식 오류: 문자열이어야 함 "
                        f"(현재: {type(reason).__name__})"
                    )
                    continue
                if reason not in valid_runnable_reasons:
                    errors.append(
                        f"runnable_reason 토큰 불일치: '{reason}' "
                        f"(허용: {sorted(valid_runnable_reasons)})"
                    )
            if runnable_reason and metadata.get("runnable") is True:
                errors.append(
                    "일관성 오류: runnable_reason이 비어있지 않으면 "
                    "runnable=false 이어야 함 (현재 runnable=True)"
                )

    if not isinstance(steps, list):
        return errors + ["steps 형식 오류: 배열이어야 함"]
    if not steps:
        errors.append("steps가 비어 있음")

    step_schema = schema.get("$defs", {}).get("step", {})
    step_properties = step_schema.get("properties", {})
    valid_actions = step_properties.get("action", {}).get("enum", [])
    valid_modes = step_properties.get("execution_mode", {}).get("enum", [])
    valid_roles = step_properties.get("step_role", {}).get("enum", [])
    action_required = derive_action_required(schema)

    for index, step in enumerate(steps):
        prefix = f"steps[{index}]"
        if not isinstance(step, Mapping):
            errors.append(f"{prefix}: step 형식 오류: object여야 함")
            continue
        action = step.get("action")
        if not action:
            errors.append(f"{prefix}: 'action' 누락")
            continue
        if action not in valid_actions:
            errors.append(f"{prefix}: 미지원 action '{action}' (허용: {valid_actions})")
            continue

        mode = step.get("execution_mode")
        if mode and mode not in valid_modes:
            errors.append(f"{prefix}: 미지원 execution_mode '{mode}'")
        role = step.get("step_role")
        if role and role not in valid_roles:
            errors.append(f"{prefix}: 미지원 step_role '{role}'")

        for field in action_required.get(action, ()):
            if field == "action":
                continue
            if _required_value_missing(step, field):
                errors.append(
                    f"{prefix}: action='{action}'에 필수 필드 '{field}' 누락"
                )

        if action == "manual_pause":
            if not step.get("description"):
                errors.append(
                    f"{prefix}: manual_pause에 description 누락 (작업자 지시 필수)"
                )
            on_timeout = step.get("on_timeout")
            if on_timeout and on_timeout not in ["fail", "skip", "warn"]:
                errors.append(
                    f"{prefix}: on_timeout '{on_timeout}' 불일치 "
                    "(허용: fail/skip/warn)"
                )

        if action in ("shell", "verify_shell"):
            command = step.get("command", "")
            if isinstance(command, str) and "{" in command and "}" in command:
                errors.append(
                    f"{prefix}: command에 미해결 placeholder 잔존: '{command}'"
                )

    return errors


__all__ = [
    "ContractFinding",
    "NormalizationResult",
    "derive_action_required",
    "derive_execution_metadata",
    "normalize_step",
    "normalize_tc",
    "validate_canonical_tc",
]
