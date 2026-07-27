#!/usr/bin/env python3
"""Join a frozen canonical shell inventory to a reviewed static RC policy."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_SCHEMA_VERSION = "canonical-shell-rc-risk-policy-v1"
SCHEMA_VERSION = "canonical-shell-rc-risk-audit-v1"
INVENTORY_SCHEMA_VERSION = "canonical-shell-rc-inventory-v3"
FROZEN_HEAD_SHA = "78b3ac34e9f8bacabe926172dd199342b7eb58c5"
FROZEN_INVENTORY_SHA256 = (
    "b0c5552c4a3d20590c85ce701c46061a7c6cd5e2cf589bc1cfa5395382880b7f"
)
FROZEN_ROW_COUNT = 692
FROZEN_POLICY_SHA256 = (
    "f41adf36600b027b1bcb4d4f2cb27ba852af0e9121ae4f276c5e670c299e90ed"
)
DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().with_name("canonical_shell_rc_risk_policy_v1.json")
)
CLASSIFICATION_ORDER = (
    "REQUIRE_ZERO",
    "VERIFY_ZERO_AND_EXPECTED",
    "COUNT_EQ_0",
    "COUNT_EQ_1",
    "COUNT_LE_1",
    "COUNT_NUMERIC_SUBSTRING",
    "EXPECTED_ERROR_FALLBACK_MASKING",
    "GREP_WC_UPSTREAM_MASKING",
    "NEGATED_TOKEN_SUBSTRING_COLLISION",
    "PRE_POST_EMPTY_EQUALITY",
    "MASKED_ASSERTION",
    "OBSERVE_ONLY",
    "TRANSPORT_TERMINATING",
    "REVIEW_REQUIRED",
)
CLASSIFICATIONS = frozenset(CLASSIFICATION_ORDER)
DEFAULT_CLASSIFICATIONS = frozenset(
    {"REQUIRE_ZERO", "VERIFY_ZERO_AND_EXPECTED"}
)
CUTOVER_BLOCKING_CLASSIFICATIONS = frozenset(
    {
        "COUNT_EQ_0",
        "COUNT_EQ_1",
        "COUNT_LE_1",
        "MASKED_ASSERTION",
    }
)
ADVISORY_ORACLE_CLASSIFICATIONS = frozenset(
    {
        "COUNT_NUMERIC_SUBSTRING",
        "EXPECTED_ERROR_FALLBACK_MASKING",
        "GREP_WC_UPSTREAM_MASKING",
        "NEGATED_TOKEN_SUBSTRING_COLLISION",
        "PRE_POST_EMPTY_EQUALITY",
    }
)
RUNTIME_REVIEW_CLASSIFICATIONS = frozenset(
    {"OBSERVE_ONLY", "TRANSPORT_TERMINATING", "REVIEW_REQUIRED"}
)
INVENTORY_FIELDS = (
    "schema_version",
    "head_sha",
    "row_key",
    "source_path",
    "source_blob",
    "tc_name",
    "step_index",
    "action",
    "command",
    "command_sha256",
    "expected",
    "timeout_ms",
    "execution_mode",
    "dispatch_route",
)
OUTPUT_FIELDS = (
    "schema_version",
    "input_csv_sha256",
    "row_key",
    "source_path",
    "step_index",
    "action",
    "command_sha256",
    "command",
    "expected",
    "timeout_ms",
    "classification",
    "reason_code",
    "evidence",
    "canonical_rc_contract",
    "remediation_requirement",
)
CONTRACT_BY_CLASSIFICATION = {
    "REQUIRE_ZERO": "rc == 0",
    "VERIFY_ZERO_AND_EXPECTED": (
        "rc == 0 and expected substring in stdout"
    ),
    "COUNT_EQ_0": "stdout integer == 0; grep rc is inverted at zero",
    "COUNT_EQ_1": "stdout integer == 1; rc == 0 is insufficient",
    "COUNT_LE_1": "stdout integer <= 1; rc is insufficient",
    "COUNT_NUMERIC_SUBSTRING": (
        "stdout integer must equal expected exactly"
    ),
    "EXPECTED_ERROR_FALLBACK_MASKING": (
        "upstream success must be distinguished from expected fallback"
    ),
    "GREP_WC_UPSTREAM_MASKING": (
        "upstream grep success must be distinguished from zero count"
    ),
    "NEGATED_TOKEN_SUBSTRING_COLLISION": (
        "expected token must not match a negated failure token"
    ),
    "PRE_POST_EMPTY_EQUALITY": (
        "both reads must succeed before comparing values"
    ),
    "MASKED_ASSERTION": "fallback may force rc == 0",
    "OBSERVE_ONLY": "last pipeline command may mask upstream failure",
    "TRANSPORT_TERMINATING": "success may close the ADB transport",
    "REVIEW_REQUIRED": "compound-command rc meaning is ambiguous",
}
REMEDIATION_BY_CLASSIFICATION = {
    "REQUIRE_ZERO": "NONE_FROM_STATIC_AUDIT",
    "VERIFY_ZERO_AND_EXPECTED": "NONE_FROM_STATIC_AUDIT",
    "COUNT_EQ_0": "STDOUT_PREDICATE_REQUIRED",
    "COUNT_EQ_1": "STDOUT_PREDICATE_REQUIRED",
    "COUNT_LE_1": "STDOUT_PREDICATE_REQUIRED",
    "COUNT_NUMERIC_SUBSTRING": "STDOUT_PREDICATE_REQUIRED",
    "EXPECTED_ERROR_FALLBACK_MASKING": "STDOUT_PREDICATE_REQUIRED",
    "GREP_WC_UPSTREAM_MASKING": "STDOUT_PREDICATE_REQUIRED",
    "NEGATED_TOKEN_SUBSTRING_COLLISION": "STDOUT_PREDICATE_REQUIRED",
    "PRE_POST_EMPTY_EQUALITY": "STDOUT_PREDICATE_REQUIRED",
    "MASKED_ASSERTION": "STDOUT_PREDICATE_REQUIRED",
    "OBSERVE_ONLY": "RUNTIME_REVIEW_REQUIRED",
    "TRANSPORT_TERMINATING": "RUNTIME_REVIEW_REQUIRED",
    "REVIEW_REQUIRED": "RUNTIME_REVIEW_REQUIRED",
}


class AuditInputError(ValueError):
    """Inventory or policy bytes do not satisfy the frozen contract."""


class AuditInfraError(RuntimeError):
    """Filesystem, self-check, or determinism prevented measurement."""


@dataclass(frozen=True)
class InventoryIdentity:
    csv_sha256: str
    head_sha: str
    row_count: int


@dataclass(frozen=True)
class PolicyEntry:
    row_key: str
    action: str
    command_sha256: str
    classification: str
    reason_code: str
    evidence: str


@dataclass(frozen=True)
class Policy:
    schema_version: str
    inventory_sha256: str
    inventory_row_count: int
    override_count: int
    override_identity_sha256: str
    overrides: tuple[PolicyEntry, ...]
    file_sha256: str


@dataclass(frozen=True)
class AuditReport:
    input_csv_sha256: str
    input_head_sha: str
    policy_sha256: str
    rows: tuple[dict[str, str], ...]
    classification_counts: dict[str, int]
    blocking_rows: int
    advisory_oracle_rows: int
    runtime_review_rows: int


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_input_bytes(path: Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise AuditInputError(f"unable to read {label}: {path}: {exc}") from exc


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )


def _override_identity_sha256(
    overrides: Sequence[PolicyEntry],
) -> str:
    identities = [
        {
            "row_key": entry.row_key,
            "action": entry.action,
            "command_sha256": entry.command_sha256,
            "classification": entry.classification,
            "reason_code": entry.reason_code,
            "evidence": entry.evidence,
        }
        for entry in overrides
    ]
    identities.sort(
        key=lambda item: (
            item["row_key"],
            item["action"],
            item["command_sha256"],
            item["classification"],
            item["reason_code"],
            item["evidence"],
        )
    )
    material = json.dumps(
        identities,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(material)


def load_inventory(
    path: Path,
) -> tuple[InventoryIdentity, tuple[dict[str, str], ...]]:
    data = _read_input_bytes(path, "inventory")
    csv_sha256 = _sha256_bytes(data)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditInputError("inventory is not UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != INVENTORY_FIELDS:
        raise AuditInputError(
            "inventory header mismatch: "
            f"observed={tuple(reader.fieldnames or ())!r}"
        )

    rows: list[dict[str, str]] = []
    row_keys: set[str] = set()
    head_sha: str | None = None
    for line_number, raw in enumerate(reader, start=2):
        if any(value is None for value in raw.values()):
            raise AuditInputError(
                f"inventory row {line_number} has missing columns"
            )
        row = {key: str(value) for key, value in raw.items()}
        if row["schema_version"] != INVENTORY_SCHEMA_VERSION:
            raise AuditInputError(
                f"inventory row {line_number} schema mismatch"
            )
        if not _is_lower_hex(row["head_sha"], 40):
            raise AuditInputError(
                f"inventory row {line_number} has invalid HEAD"
            )
        if head_sha is None:
            head_sha = row["head_sha"]
        elif row["head_sha"] != head_sha:
            raise AuditInputError("inventory contains multiple HEAD values")

        row_key = row["row_key"]
        if row_key in row_keys:
            raise AuditInputError(f"duplicate row_key: {row_key}")
        row_keys.add(row_key)
        command_sha256 = _sha256_bytes(row["command"].encode("utf-8"))
        if command_sha256 != row["command_sha256"]:
            raise AuditInputError(
                f"inventory command hash mismatch: {row_key}"
            )
        if row["dispatch_route"] != "RUNNER_SHELL":
            raise AuditInputError(
                f"inventory contains non-runner shell row: {row_key}"
            )
        if row["action"] not in {"shell", "verify_shell"}:
            raise AuditInputError(
                f"inventory contains unsupported action: {row_key}"
            )
        rows.append(row)

    if not rows or head_sha is None:
        raise AuditInputError("inventory contains no rows")
    return (
        InventoryIdentity(
            csv_sha256=csv_sha256,
            head_sha=head_sha,
            row_count=len(rows),
        ),
        tuple(rows),
    )


def load_policy(path: Path) -> Policy:
    data = _read_input_bytes(path, "policy")
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditInputError(f"invalid policy JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise AuditInputError("policy root must be an object")
    if document.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise AuditInputError("policy schema_version mismatch")
    inventory_sha256 = document.get("inventory_sha256")
    if not isinstance(inventory_sha256, str) or not _is_lower_hex(
        inventory_sha256,
        64,
    ):
        raise AuditInputError("policy inventory_sha256 is invalid")
    inventory_row_count = document.get("inventory_row_count")
    if (
        not isinstance(inventory_row_count, int)
        or isinstance(inventory_row_count, bool)
        or inventory_row_count < 1
    ):
        raise AuditInputError("policy inventory_row_count is invalid")
    override_count = document.get("override_count")
    if (
        not isinstance(override_count, int)
        or isinstance(override_count, bool)
        or override_count < 0
    ):
        raise AuditInputError("policy override_count is invalid")
    override_identity_sha256 = document.get(
        "override_identity_sha256"
    )
    if not isinstance(
        override_identity_sha256,
        str,
    ) or not _is_lower_hex(override_identity_sha256, 64):
        raise AuditInputError(
            "policy override_identity_sha256 is invalid"
        )
    raw_overrides = document.get("overrides")
    if not isinstance(raw_overrides, list):
        raise AuditInputError("policy overrides must be a list")

    overrides: list[PolicyEntry] = []
    seen_row_keys: set[str] = set()
    for index, raw in enumerate(raw_overrides, start=1):
        if not isinstance(raw, dict):
            raise AuditInputError(f"policy override {index} is not an object")
        values: dict[str, str] = {}
        for field in (
            "row_key",
            "action",
            "command_sha256",
            "classification",
            "reason_code",
            "evidence",
        ):
            value = raw.get(field)
            if not isinstance(value, str) or not value.strip():
                raise AuditInputError(
                    f"policy override {index} has invalid {field}"
                )
            values[field] = value
        if values["row_key"] in seen_row_keys:
            raise AuditInputError(
                f"duplicate policy row_key: {values['row_key']}"
            )
        seen_row_keys.add(values["row_key"])
        if not _is_lower_hex(values["command_sha256"], 64):
            raise AuditInputError(
                f"policy override {index} command_sha256 is invalid"
            )
        if values["action"] not in {"shell", "verify_shell"}:
            raise AuditInputError(
                f"policy override {index} action is invalid"
            )
        if (
            values["classification"] not in CLASSIFICATIONS
            or values["classification"] in DEFAULT_CLASSIFICATIONS
        ):
            raise AuditInputError(
                f"policy override {index} classification is invalid"
            )
        overrides.append(PolicyEntry(**values))

    if len(overrides) != override_count:
        raise AuditInputError(
            "policy override count does not match manifest"
        )
    observed_override_identity = _override_identity_sha256(overrides)
    if observed_override_identity != override_identity_sha256:
        raise AuditInputError(
            "policy override identity does not match manifest"
        )

    return Policy(
        schema_version=POLICY_SCHEMA_VERSION,
        inventory_sha256=inventory_sha256,
        inventory_row_count=inventory_row_count,
        override_count=override_count,
        override_identity_sha256=override_identity_sha256,
        overrides=tuple(overrides),
        file_sha256=_sha256_bytes(data),
    )


def build_audit(
    identity: InventoryIdentity,
    rows: Sequence[Mapping[str, str]],
    policy: Policy,
) -> AuditReport:
    if policy.inventory_sha256 != identity.csv_sha256:
        raise AuditInputError(
            "policy inventory SHA-256 does not match input inventory"
        )
    if policy.inventory_row_count != identity.row_count:
        raise AuditInputError(
            "policy inventory row count does not match input inventory"
        )
    by_row_key = {str(row["row_key"]): row for row in rows}
    if len(by_row_key) != len(rows):
        raise AuditInputError("inventory row_key set is not unique")

    overrides: dict[str, PolicyEntry] = {}
    for entry in policy.overrides:
        inventory_row = by_row_key.get(entry.row_key)
        if inventory_row is None:
            raise AuditInputError(
                f"policy row_key not present in inventory: {entry.row_key}"
            )
        if str(inventory_row["command_sha256"]) != entry.command_sha256:
            raise AuditInputError(
                f"policy command hash mismatch: {entry.row_key}"
            )
        if str(inventory_row["action"]) != entry.action:
            raise AuditInputError(
                f"policy action mismatch: {entry.row_key}"
            )
        overrides[entry.row_key] = entry

    output_rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    applied_overrides = 0
    for inventory_row in rows:
        row_key = str(inventory_row["row_key"])
        override = overrides.get(row_key)
        if override is None:
            classification, reason_code, evidence = (
                _default_classification(inventory_row)
            )
        else:
            applied_overrides += 1
            classification = override.classification
            reason_code = override.reason_code
            evidence = override.evidence
        counts[classification] += 1
        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "input_csv_sha256": identity.csv_sha256,
                "row_key": row_key,
                "source_path": str(inventory_row["source_path"]),
                "step_index": str(inventory_row["step_index"]),
                "action": str(inventory_row["action"]),
                "command_sha256": str(inventory_row["command_sha256"]),
                "command": str(inventory_row["command"]),
                "expected": str(inventory_row["expected"]),
                "timeout_ms": str(inventory_row["timeout_ms"]),
                "classification": classification,
                "reason_code": reason_code,
                "evidence": evidence,
                "canonical_rc_contract": CONTRACT_BY_CLASSIFICATION[
                    classification
                ],
                "remediation_requirement": REMEDIATION_BY_CLASSIFICATION[
                    classification
                ],
            }
        )

    classification_counts = {
        classification: counts[classification]
        for classification in CLASSIFICATION_ORDER
    }
    report = AuditReport(
        input_csv_sha256=identity.csv_sha256,
        input_head_sha=identity.head_sha,
        policy_sha256=policy.file_sha256,
        rows=tuple(output_rows),
        classification_counts=classification_counts,
        blocking_rows=sum(
            count
            for classification, count in classification_counts.items()
            if classification in CUTOVER_BLOCKING_CLASSIFICATIONS
        ),
        advisory_oracle_rows=sum(
            count
            for classification, count in classification_counts.items()
            if classification in ADVISORY_ORACLE_CLASSIFICATIONS
        ),
        runtime_review_rows=sum(
            count
            for classification, count in classification_counts.items()
            if classification in RUNTIME_REVIEW_CLASSIFICATIONS
        ),
    )
    _self_check(
        report,
        identity.row_count,
        len(policy.overrides),
        applied_overrides,
    )
    return report


def observation_satisfies_reviewed_count_contract(
    classification: str,
    *,
    returncode: int,
    stdout: str,
) -> bool:
    """Evaluate the three reviewed count contracts without device access."""
    if classification not in {
        "COUNT_EQ_0",
        "COUNT_EQ_1",
        "COUNT_LE_1",
    }:
        raise ValueError(f"unsupported reviewed count contract: {classification}")
    try:
        count = int(stdout.strip())
    except ValueError:
        return False
    if count < 0 or returncode not in {0, 1}:
        return False
    if classification == "COUNT_EQ_0":
        return count == 0
    if classification == "COUNT_EQ_1":
        return returncode == 0 and count == 1
    return count <= 1


def _default_classification(
    inventory_row: Mapping[str, str],
) -> tuple[str, str, str]:
    action = str(inventory_row["action"])
    if action == "shell":
        return (
            "REQUIRE_ZERO",
            "NO_REVIEWED_NONZERO_SIGNAL",
            "",
        )

    command = str(inventory_row["command"])
    expected = str(inventory_row["expected"])
    if expected and f"NOT_{expected}" in command:
        return (
            "NEGATED_TOKEN_SUBSTRING_COLLISION",
            "EXPECTED_SUBSTRING_MATCHES_FAILURE_TOKEN",
            "static detector: expected token occurs inside NOT_<expected>",
        )
    if (
        expected == "UNCHANGED"
        and "PRE=$(" in command
        and "POST=$(" in command
    ):
        return (
            "PRE_POST_EMPTY_EQUALITY",
            "BOTH_READ_FAILURES_CAN_COMPARE_EQUAL_AS_EMPTY",
            "static detector: PRE and POST command substitutions",
        )

    is_count_command = "grep -c" in command or "wc -l" in command
    if expected.isdecimal() and is_count_command:
        if expected == "0" and "|| echo 0" in command:
            return (
                "EXPECTED_ERROR_FALLBACK_MASKING",
                "UPSTREAM_ERROR_COLLAPSES_TO_EXPECTED_ZERO",
                "static detector: count failure falls back to expected zero",
            )
        if (
            expected == "0"
            and "grep" in command
            and "wc -l" in command
        ):
            return (
                "GREP_WC_UPSTREAM_MASKING",
                "PIPELINE_UPSTREAM_ERROR_COLLAPSES_TO_ZERO",
                "static detector: wc reports zero after upstream failure",
            )
        if expected == "0" and "grep -c" in command:
            return (
                "COUNT_EQ_0",
                "VERIFY_GREP_ZERO_RC_POLARITY_INVERTED",
                "static detector: grep -c returns rc=1 at zero matches",
            )
        return (
            "COUNT_NUMERIC_SUBSTRING",
            "EXPECTED_SUBSTRING_DOES_NOT_ENFORCE_EXACT_CARDINALITY",
            "static detector: numeric count checked as a substring",
        )

    if "||" in command and expected in command.rsplit("||", 1)[1]:
        return (
            "EXPECTED_ERROR_FALLBACK_MASKING",
            "UPSTREAM_ERROR_COLLAPSES_TO_EXPECTED_TOKEN",
            "static detector: expected token is emitted by fallback branch",
        )

    return (
        "VERIFY_ZERO_AND_EXPECTED",
        "CANONICAL_VERIFY_CONJUNCTION",
        "",
    )


def _self_check(
    report: AuditReport,
    expected_rows: int,
    expected_overrides: int,
    applied_overrides: int,
) -> None:
    if len(report.rows) != expected_rows:
        raise AuditInfraError("audit row count mismatch")
    row_keys = [row["row_key"] for row in report.rows]
    if len(row_keys) != len(set(row_keys)):
        raise AuditInfraError("audit contains duplicate row_key")
    if sum(report.classification_counts.values()) != expected_rows:
        raise AuditInfraError("classification count mismatch")
    if applied_overrides != expected_overrides:
        raise AuditInfraError("policy override count mismatch")
    if any(
        row["classification"] not in CLASSIFICATIONS for row in report.rows
    ):
        raise AuditInfraError("audit contains unknown classification")


def _csv_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=OUTPUT_FIELDS,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _tool_sha256() -> str:
    return _sha256_bytes(Path(__file__).read_bytes())


def _input_digest(report: AuditReport, tool_sha256: str) -> str:
    material = "\n".join(
        (
            SCHEMA_VERSION,
            report.input_csv_sha256,
            report.policy_sha256,
            tool_sha256,
            "",
        )
    ).encode("utf-8")
    return _sha256_bytes(material)


def render_artifacts(
    report: AuditReport,
    *,
    tool_sha256: str | None = None,
) -> tuple[bytes, bytes]:
    csv_bytes = _csv_bytes(report.rows)
    csv_sha256 = _sha256_bytes(csv_bytes)
    if tool_sha256 is None:
        tool_sha256 = _tool_sha256()
    input_digest = _input_digest(report, tool_sha256)
    lines = [
        "# Canonical Shell RC Risk Audit",
        "",
        f"- Schema version: `{SCHEMA_VERSION}`",
        f"- Input HEAD: `{report.input_head_sha}`",
        f"- Input CSV SHA-256: `{report.input_csv_sha256}`",
        f"- Policy SHA-256: `{report.policy_sha256}`",
        f"- Tool SHA-256: `{tool_sha256}`",
        f"- Input digest: `{input_digest}`",
        f"- CSV SHA-256: `{csv_sha256}`",
        f"- Rows: {len(report.rows)}",
        f"- Cutover-blocking rows: {report.blocking_rows}",
        f"- Advisory oracle rows: {report.advisory_oracle_rows}",
        f"- Runtime-review rows: {report.runtime_review_rows}",
        "",
        "## Classification counts",
        "",
    ]
    for classification in CLASSIFICATION_ORDER:
        lines.append(
            f"- {classification}: "
            f"{report.classification_counts[classification]}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Cutover-blocking rows are the reviewed rc-sensitive "
            "canonical-default delta, not device results.",
            "- Advisory oracle rows are pre-existing stdout-predicate "
            "risks and are not attributed to the cutover.",
            "- Runtime-review rows remain unresolved pending runtime evidence.",
            "- REQUIRE_ZERO means no reviewed non-zero signal was found.",
            "- VERIFY_ZERO_AND_EXPECTED means canonical execution requires "
            "both rc=0 and the expected stdout substring; no current "
            "high-confidence static risk detector matched.",
            "",
        ]
    )
    return csv_bytes, "\n".join(lines).encode("utf-8")


def _write_artifacts(
    output_root: Path,
    input_digest: str,
    csv_bytes: bytes,
    summary_bytes: bytes,
    *,
    state_check: Callable[[], None] | None = None,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / input_digest[:16]
    expected = {
        "shell_rc_risk_matrix.csv": csv_bytes,
        "SUMMARY.md": summary_bytes,
    }
    if destination.exists():
        try:
            entries = {
                entry.name
                for entry in destination.iterdir()
            }
            if entries != set(expected):
                raise AuditInfraError(
                    f"existing destination entry set differs: {destination}"
                )
            observed = {
                name: (destination / name).read_bytes()
                for name in expected
            }
        except OSError as exc:
            raise AuditInfraError(
                f"existing destination is incomplete: {destination}"
            ) from exc
        if observed != expected:
            raise AuditInfraError(
                f"existing destination bytes differ: {destination}"
            )
        if state_check is not None:
            state_check()
        return destination

    published = False
    with tempfile.TemporaryDirectory(
        prefix=".canonical-shell-risk-",
        dir=output_root,
    ) as temporary:
        temporary_root = Path(temporary)
        staged = temporary_root / destination.name
        staged.mkdir()
        for name, data in expected.items():
            (staged / name).write_bytes(data)
        observed_staged = {
            name: (staged / name).read_bytes()
            for name in expected
        }
        if observed_staged != expected:
            raise AuditInfraError("staged artifact readback mismatch")
        if state_check is not None:
            state_check()
        os.replace(staged, destination)
        published = True
        try:
            if state_check is not None:
                state_check()
        except Exception:
            if published and destination.exists():
                shutil.rmtree(destination)
            raise
    return destination


def _verify_frozen_contract(
    identity: InventoryIdentity,
    policy: Policy,
) -> None:
    if identity.head_sha != FROZEN_HEAD_SHA:
        raise AuditInputError("inventory HEAD does not match frozen contract")
    if identity.csv_sha256 != FROZEN_INVENTORY_SHA256:
        raise AuditInputError(
            "inventory SHA-256 does not match frozen contract"
        )
    if identity.row_count != FROZEN_ROW_COUNT:
        raise AuditInputError(
            "inventory row count does not match frozen contract"
        )
    if policy.file_sha256 != FROZEN_POLICY_SHA256:
        raise AuditInputError("policy SHA-256 does not match frozen contract")


def _verify_unchanged_inputs(
    inventory_path: Path,
    policy_path: Path,
    *,
    inventory_sha256: str,
    policy_sha256: str,
    tool_sha256: str,
) -> None:
    try:
        observed_inventory = _sha256_bytes(inventory_path.read_bytes())
        observed_policy = _sha256_bytes(policy_path.read_bytes())
        observed_tool = _tool_sha256()
    except OSError as exc:
        raise AuditInfraError(
            f"unable to re-read frozen inputs: {exc}"
        ) from exc
    if observed_inventory != inventory_sha256:
        raise AuditInfraError("inventory changed during audit")
    if observed_policy != policy_sha256:
        raise AuditInfraError("policy changed during audit")
    if observed_tool != tool_sha256:
        raise AuditInfraError("tool changed during audit")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "canonical_shell_rc_risk_audit",
    )
    parser.add_argument("--verify-determinism", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    inventory_path = args.inventory.resolve()
    policy_path = args.policy.resolve()
    try:
        start_tool_sha256 = _tool_sha256()
        identity, rows = load_inventory(inventory_path)
        policy = load_policy(policy_path)
        _verify_frozen_contract(identity, policy)
        report = build_audit(identity, rows, policy)
        artifacts = render_artifacts(
            report,
            tool_sha256=start_tool_sha256,
        )

        if args.verify_determinism:
            second_identity, second_rows = load_inventory(inventory_path)
            second_policy = load_policy(policy_path)
            second_report = build_audit(
                second_identity,
                second_rows,
                second_policy,
            )
            second_artifacts = render_artifacts(
                second_report,
                tool_sha256=start_tool_sha256,
            )
            if second_report != report or second_artifacts != artifacts:
                raise AuditInfraError("determinism verification mismatch")

        def state_check() -> None:
            _verify_unchanged_inputs(
                inventory_path,
                policy_path,
                inventory_sha256=identity.csv_sha256,
                policy_sha256=policy.file_sha256,
                tool_sha256=start_tool_sha256,
            )

        state_check()

        destination = _write_artifacts(
            args.out_dir.resolve(),
            _input_digest(report, start_tool_sha256),
            *artifacts,
            state_check=state_check,
        )
    except AuditInputError as exc:
        print(f"INPUT INVALID: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"INFRA FAILURE: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 3

    print(f"audit: {destination}")
    print(f"rows: {len(report.rows)}")
    print(f"blocking: {report.blocking_rows}")
    print(f"advisory_oracle: {report.advisory_oracle_rows}")
    print(f"runtime_review: {report.runtime_review_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
