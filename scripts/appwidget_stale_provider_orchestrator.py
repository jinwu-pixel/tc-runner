"""Phase orchestration for the BUG27084 stale-provider harness."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from functools import wraps
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Callable, Mapping

from appwidget_stale_provider_evidence import (
    EvidenceBundle,
    EvidenceInputError,
    RunLockError,
    exclusive_run_lock,
    make_run_id,
    validate_run_id,
    verify_evidence_manifest,
    verify_inputs,
    write_evidence_artifact,
)
from appwidget_stale_provider_models import Event, LauncherCrashExit, Phase
from appwidget_stale_provider_parsers import (
    UiDumpParseError,
    parse_appwidget_state,
    parse_launcher_host_bindings,
    parse_crash_signature,
    parse_launcher_crash_exits,
    find_ui_node,
    find_ui_node_by_resource_id,
    normalize_ui_dump,
    parse_home_role,
    parse_package_state,
    ui_contains_exact_package,
)
from appwidget_stale_provider_preflight import preflight_identity
from appwidget_stale_provider_state import assert_transition


Clock = Callable[[], datetime]
_ANDROID_ALERT_TITLE_RESOURCE_ID = "android:id/alertTitle"
_ANDROID_AERR_CLOSE_RESOURCE_ID = "android:id/aerr_close"
_LAUNCHER_CRASH_TITLES = (
    "MIVE Home이(가) 중지됨",
    "MIVE Home이(가) 계속 중단됨",
)
KST = timezone(timedelta(hours=9))
_sleep = time.sleep
_monotonic = time.monotonic


class GateFailure(RuntimeError):
    """A fail-closed precondition was not established."""


class CaptureIncomplete(GateFailure):
    """A mandatory read-only capture artifact could not be collected."""


class EvidenceIntegrityFailure(GateFailure):
    """A resumed run no longer matches its recorded evidence manifest."""


def _instant(clock: Clock | None) -> datetime:
    value = clock() if clock is not None else datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceInputError("orchestrator clock must be timezone-aware")
    return value


def _pause(wait: Callable[[], None] | None, seconds: float) -> None:
    if wait is not None:
        wait()
    else:
        _sleep(seconds)


def _timestamp(value: datetime, zone: timezone) -> str:
    return value.astimezone(zone).isoformat(timespec="seconds").replace("+00:00", "Z")


def _bytes(value: str | bytes) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def _digest(value: str | bytes) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _write_raw(path: Path, value: str | bytes) -> None:
    if path.parent.name in {"snapshots", "screenshots"}:
        bundle_directory = path.parent.parent
    else:
        bundle_directory = path.parent
    relative = path.relative_to(bundle_directory).as_posix()
    write_evidence_artifact(bundle_directory, relative, _bytes(value))


def _initial_result(home_role: str | None = None) -> dict[str, Any]:
    return {
        "crash_signature_count": 0,
        "diagnosis_status": "SUSPECT",
        "evidence_term": "manual evidence observed",
        "final_home_role": home_role,
        "home_rendered": None,
        "launcher_crash_exit_count": 0,
        "launcher_crash_exit_pids": [],
        "launcher_loader_record_count": 0,
        "launcher_loop_basis": [],
        "launcher_loop_observed": False,
        "launcher_process_stable": None,
        "launcher_stale_record_evidence": "INFERRED_ONLY",
        "mutations_remaining": [],
        "precondition_status": "NOT_EVALUATED",
        "provider_registered": None,
        "widget_bound_after": None,
        "widget_bound_before": None,
    }


def _read_state(run_directory: Path) -> dict[str, Any]:
    try:
        value = json.loads((run_directory / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure("run.json is missing or invalid") from exc
    if not isinstance(value, dict):
        raise GateFailure("run.json must contain an object")
    return value


def require_run_phase(run_directory: Path | str, expected: str | Phase) -> dict[str, Any]:
    directory = Path(run_directory)
    state = _read_state(directory)
    expected_value = expected.value if isinstance(expected, Phase) else str(expected)
    if not state.get("capture_complete"):
        raise GateFailure("baseline capture is incomplete")
    if state.get("current_phase") != expected_value:
        raise GateFailure(
            f"run phase mismatch: expected {expected_value}, got {state.get('current_phase')}"
        )
    return state


def _assert_run_identity(
    run_directory: Path,
    state: Mapping[str, Any],
    *,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    profile: Mapping[str, Any],
) -> None:
    fixture_reset_state = state.get("fixture_reset")
    if (
        isinstance(fixture_reset_state, dict)
        and fixture_reset_state.get("status") == "CONSUMED"
    ):
        raise GateFailure("source run was handed off and is immutable")
    if state.get("run_id") != run_directory.name:
        raise GateFailure("run ID differs from the run directory/CLI identity")
    try:
        verify_evidence_manifest(run_directory)
    except EvidenceInputError as exc:
        raise EvidenceIntegrityFailure("run evidence integrity verification failed") from exc
    identity = state.get("profile_identity")
    expected_identity = {
        "fingerprint": expected_fingerprint,
        "incremental": profile["incremental"],
        "model": expected_model,
        "serial": serial,
        "viewport": list(profile["viewport"]),
    }
    if identity != expected_identity:
        raise GateFailure("run identity differs from CLI/profile identity")
    if expected_model != profile["model"] or expected_fingerprint != profile["fingerprint"]:
        raise GateFailure("run identity CLI values differ from profile")
    try:
        inputs = json.loads((run_directory / "inputs.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure("run input identity is missing or invalid") from exc
    app = profile["app"]
    apk_dir = str(app.get("apk_dir", "simpleclock_apk"))
    expected_splits = [
        {
            "logical_id": f"{apk_dir}/{name}",
            "name": name,
            "sha256": digest.upper(),
            "size": size,
        }
        for name, size, digest in app["splits"]
    ]
    expected_inputs = {
        "package": app["package"],
        "signature_token": app["signature_token"],
        "source_bundle": app["source_bundle"],
        "source_manifest_sha256": str(app["source_manifest_sha256"]).upper(),
        "splits": expected_splits,
        "version_code": app["version_code"],
        "version_name": app["version_name"],
    }
    if inputs != expected_inputs:
        raise GateFailure("run input identity differs from the selected profile")
    lineage_value = state.get("lineage")
    lineage_path = run_directory / "lineage.json"
    if lineage_value is None and not lineage_path.exists():
        return
    try:
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure("run predecessor lineage is missing or invalid") from exc
    if not isinstance(lineage, dict) or lineage != lineage_value:
        raise GateFailure("run predecessor lineage differs from run.json")
    source_run_id = lineage.get("source_run_id")
    if not isinstance(source_run_id, str):
        raise GateFailure("run predecessor lineage lacks a source run ID")
    source_directory = run_directory.parent / validate_run_id(source_run_id)
    try:
        source_directory = source_directory.resolve(strict=True)
        source_directory.relative_to(run_directory.parent)
        verify_evidence_manifest(source_directory)
    except (OSError, ValueError, EvidenceInputError) as exc:
        raise GateFailure("run predecessor evidence is missing or invalid") from exc
    pinned_files = {
        "source_manifest_sha256": source_directory / "evidence_sha256.txt",
        "reset_receipt_sha256": source_directory / "fixture_reset.json",
        "reset_consumption_sha256": (
            source_directory / "fixture_reset_consumption.json"
        ),
    }
    for field, path in pinned_files.items():
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        except OSError as exc:
            raise GateFailure(f"run predecessor {field} artifact is missing") from exc
        if lineage.get(field) != actual:
            raise GateFailure(f"run predecessor {field} mismatch")
    source_state = _read_state(source_directory)
    fixture_reset = source_state.get("fixture_reset")
    if not isinstance(fixture_reset, dict) or (
        fixture_reset.get("status") != "CONSUMED"
        or fixture_reset.get("consumed_by_run_id") != run_directory.name
        or fixture_reset.get("attempt_id") != lineage.get("reset_attempt_id")
    ):
        raise GateFailure("run predecessor reset consumption differs from lineage")
    try:
        receipt = json.loads(
            (source_directory / "fixture_reset.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure("run predecessor reset receipt is invalid") from exc
    if receipt.get("next_run_id") != run_directory.name:
        raise GateFailure("run predecessor receipt targets another run")
    if receipt.get("next_profile_identity", {}).get("inputs") != inputs:
        raise GateFailure("run predecessor receipt targets another input profile")


def _consume_fixture_reset(
    *,
    root: Path,
    profile: Mapping[str, Any],
    profile_name: str,
    checked_inputs: Mapping[str, Any],
    source_run_id: str,
    next_run_id: str,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
) -> dict[str, Any]:
    source_directory = _run_directory(root, profile, source_run_id)
    evidence_root = source_directory.parent
    target_directory = evidence_root / next_run_id
    with exclusive_run_lock(source_directory):
        try:
            verify_evidence_manifest(source_directory)
        except EvidenceInputError as exc:
            raise EvidenceIntegrityFailure(
                "reset predecessor evidence integrity verification failed"
            ) from exc
        state = _read_state(source_directory)
        expected_source_identity = {
            "fingerprint": expected_fingerprint,
            "incremental": profile["incremental"],
            "model": expected_model,
            "serial": serial,
            "viewport": list(profile["viewport"]),
        }
        if state.get("profile_identity") != expected_source_identity:
            raise GateFailure("reset predecessor device identity differs from capture")
        fixture_state = state.get("fixture_reset")
        if isinstance(fixture_state, dict) and fixture_state.get("status") == "CONSUMED":
            raise GateFailure("fixture reset receipt was already consumed")
        if (
            state.get("current_phase") != Phase.RESTORED_SAFE.value
            or state.get("run_complete") is not True
            or state.get("mutations_remaining")
            or state.get("active_attempts")
            or state.get("attempt_reconciliation_required")
        ):
            raise GateFailure("reset predecessor is not clean RESTORED_SAFE")
        if not isinstance(fixture_state, dict) or (
            fixture_state.get("status") != "READY_FOR_CAPTURE"
        ):
            raise GateFailure("reset predecessor has no READY_FOR_CAPTURE receipt")
        if target_directory.exists():
            raise GateFailure("next capture run directory already exists")
        try:
            receipt_bytes = (source_directory / "fixture_reset.json").read_bytes()
            receipt = json.loads(receipt_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GateFailure("fixture reset receipt is missing or invalid") from exc
        reset_attempt_id = fixture_state.get("attempt_id")
        expected_profile_identity = _reset_profile_identity(
            profile_name, profile, checked_inputs
        )
        if (
            receipt.get("schema_version") != 1
            or receipt.get("status") != "READY_FOR_CAPTURE"
            or receipt.get("source_run_id") != source_run_id
            or receipt.get("next_run_id") != next_run_id
            or receipt.get("reset_attempt_id") != reset_attempt_id
            or receipt.get("next_profile_identity") != expected_profile_identity
            or receipt.get("markers_remaining") != []
            or receipt.get("post_clear_launcher_host_bindings") != []
            or receipt.get("post_clear_launcher_widget_ids") != []
            or receipt.get("final_home_role") != profile["simple_home"]
        ):
            raise GateFailure("fixture reset receipt does not match the next capture")
        completed_attempt = next(
            (
                item
                for item in state.get("attempts", [])
                if item.get("attempt_id") == reset_attempt_id
                and item.get("kind") == "reset-fixture"
                and item.get("status") == "COMPLETED"
            ),
            None,
        )
        if completed_attempt is None:
            raise GateFailure("fixture reset attempt is not completed")
        ready_manifest_sha256 = hashlib.sha256(
            (source_directory / "evidence_sha256.txt").read_bytes()
        ).hexdigest().upper()
        receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest().upper()
        consumption = {
            "consumed_by_run_id": next_run_id,
            "ready_manifest_sha256": ready_manifest_sha256,
            "reset_attempt_id": reset_attempt_id,
            "reset_receipt_sha256": receipt_sha256,
            "schema_version": 1,
            "source_run_id": source_run_id,
            "status": "CONSUMED",
        }
        source_bundle = EvidenceBundle(source_directory)
        source_bundle.write_json("fixture_reset_consumption.json", consumption)
        state["fixture_reset"] = {
            "attempt_id": reset_attempt_id,
            "consumed_by_run_id": next_run_id,
            "next_run_id": next_run_id,
            "status": "CONSUMED",
        }
        source_bundle.write_json("run.json", state)
        verify_evidence_manifest(source_directory)
        return {
            "reset_attempt_id": reset_attempt_id,
            "reset_consumption_sha256": hashlib.sha256(
                (source_directory / "fixture_reset_consumption.json").read_bytes()
            ).hexdigest().upper(),
            "reset_receipt_sha256": receipt_sha256,
            "schema_version": 1,
            "source_manifest_sha256": hashlib.sha256(
                (source_directory / "evidence_sha256.txt").read_bytes()
            ).hexdigest().upper(),
            "source_run_id": source_run_id,
        }


class _CaptureWriter:
    def __init__(
        self,
        bundle: EvidenceBundle,
        transport,
        serial: str,
        clock: Clock | None,
    ) -> None:
        self.bundle = bundle
        self.transport = transport
        self.serial = serial
        self.clock = clock
        self.failures: list[str] = []

    def _record_transport_error(
        self,
        name: str,
        args: tuple[str, ...],
        artifact: str,
        error: Exception,
    ) -> None:
        self.bundle.write_json(
            "capture_error.json",
            {
                "artifact": artifact,
                "command_category": name,
                "error_type": type(error).__name__,
                "logical_command": list(_redact_logical_command(args)),
                "message": str(error),
                "phase": "capture",
                "schema_version": 1,
                "target_serial": self.serial,
            },
        )

    def _event(
        self,
        category: str,
        result,
        state: str,
        args: tuple[str, ...],
    ) -> None:
        instant = _instant(self.clock)
        boot_id = None
        if args == ("shell", "cat", "/proc/sys/kernel/random/boot_id"):
            boot_id = str(result.stdout).strip() if result.returncode == 0 else None
        elapsed_realtime = None
        if args == ("shell", "cat", "/proc/uptime") and result.returncode == 0:
            try:
                elapsed_realtime = float(str(result.stdout).split()[0])
            except (IndexError, ValueError):
                elapsed_realtime = None
        self.bundle.append_event(
            Event(
                timestamp_utc=_timestamp(instant, timezone.utc),
                timestamp_kst=_timestamp(instant, KST),
                phase="capture",
                command_category=category,
                target_serial=self.serial,
                returncode=result.returncode,
                stdout_sha256=_digest(result.stdout),
                stderr_sha256=_digest(result.stderr),
                resulting_state=state,
                logical_command=_redact_logical_command(args),
                boot_id=boot_id,
                device_elapsed_realtime_s=elapsed_realtime,
                previous_state=state,
            )
        )

    def text(self, name: str, args: tuple[str, ...]) -> str:
        try:
            result = self.transport.run_target(args)
        except Exception as exc:
            self._record_transport_error(
                name, args, f"snapshots/{name}", exc
            )
            raise
        self._event(name, result, "CAPTURING", args)
        if result.returncode != 0 or not isinstance(result.stdout, str):
            self.failures.append(name)
            value = result.stdout if isinstance(result.stdout, str) else ""
        else:
            value = result.stdout
        _write_raw(self.bundle.directory / "snapshots" / name, value)
        return value

    def binary(self, name: str, args: tuple[str, ...]) -> bytes:
        try:
            result = self.transport.run_target_binary(args)
        except Exception as exc:
            self._record_transport_error(
                name, args, f"screenshots/{name}", exc
            )
            raise
        self._event(name, result, "CAPTURING", args)
        if result.returncode != 0 or not isinstance(result.stdout, bytes):
            self.failures.append(name)
            value = result.stdout if isinstance(result.stdout, bytes) else b""
        else:
            value = result.stdout
        _write_raw(self.bundle.directory / "screenshots" / name, value)
        return value

    def ui_dump(self, stem: str, args: tuple[str, ...]) -> str:
        raw_name = f"{stem}.raw.txt"
        xml_name = f"{stem}.xml"
        raw = self.text(raw_name, args)
        try:
            xml = normalize_ui_dump(raw)
        except UiDumpParseError:
            self.failures.append(xml_name)
            return ""
        _write_raw(self.bundle.directory / "snapshots" / xml_name, xml)
        return xml


def capture(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str | None = None,
    profile_name: str | None = None,
    after_reset_run_id: str | None = None,
    now: Clock | None = None,
) -> dict[str, str]:
    """Collect the complete read-only baseline and create one durable run."""
    root = Path(repo_root).resolve(strict=True)
    checked_inputs = verify_inputs(root, profile)
    actual_run_id = run_id or make_run_id(_instant(now))
    if after_reset_run_id is not None:
        validate_run_id(after_reset_run_id)
        if not run_id:
            raise GateFailure("capture after reset requires an exact --run-id")
        if not profile_name:
            raise GateFailure("capture after reset requires an exact profile name")
    identity = preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )
    evidence_root = root.joinpath(*Path(str(profile["evidence_root"])).parts)
    lineage = None
    if after_reset_run_id is not None:
        lineage = _consume_fixture_reset(
            root=root,
            profile=profile,
            profile_name=str(profile_name),
            checked_inputs=checked_inputs,
            source_run_id=after_reset_run_id,
            next_run_id=actual_run_id,
            serial=serial,
            expected_model=expected_model,
            expected_fingerprint=expected_fingerprint,
        )
    bundle = EvidenceBundle.create(evidence_root, actual_run_id)
    bundle.write_json("inputs.json", checked_inputs)
    if lineage is not None:
        bundle.write_json("lineage.json", lineage)

    state: dict[str, Any] = {
        "capture_complete": False,
        "completed_phases": [],
        "connected_devices": [list(item) for item in identity.connected_devices],
        "current_phase": None,
        "active_attempts": {},
        "attempt_counters": {},
        "attempt_reconciliation_required": [],
        "attempts": [],
        "final_home_role": None,
        "mutations_remaining": [],
        "old_widget_id": None,
        "profile_identity": {
            "fingerprint": identity.fingerprint,
            "incremental": identity.incremental,
            "model": identity.model,
            "serial": identity.serial,
            "viewport": list(identity.viewport),
        },
        "run_id": actual_run_id,
    }
    if lineage is not None:
        state["lineage"] = lineage
        state["profile_name"] = profile_name
    bundle.write_json("run.json", state)

    writer = _CaptureWriter(bundle, transport, serial, now)
    writer.text("model_baseline.txt", ("shell", "getprop", "ro.product.model"))
    writer.text(
        "fingerprint_baseline.txt",
        ("shell", "getprop", "ro.build.fingerprint"),
    )
    writer.text(
        "incremental_baseline.txt",
        ("shell", "getprop", "ro.build.version.incremental"),
    )
    writer.text("viewport_baseline.txt", ("shell", "wm", "size"))
    role = writer.text(
        "role_baseline.txt",
        ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"),
    )
    activity = writer.text(
        "activity_baseline.txt", ("shell", "dumpsys", "activity", "activities")
    )
    package_text = writer.text(
        "package_baseline.txt",
        ("shell", "dumpsys", "package", str(profile["app"]["package"])),
    )
    appwidget_text = writer.text(
        "appwidget_baseline.txt", ("shell", "dumpsys", "appwidget")
    )
    crash_text = writer.text(
        "crash_baseline.txt",
        ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"),
    )
    writer.text(
        "main_log_baseline.txt",
        ("shell", "logcat", "-d", "-v", "threadtime"),
    )
    writer.text(
        "exit_info_baseline.txt",
        (
            "shell",
            "dumpsys",
            "activity",
            "exit-info",
            str(profile["launcher_package"]),
        ),
    )
    boot_id = writer.text(
        "boot_id_baseline.txt",
        ("shell", "cat", "/proc/sys/kernel/random/boot_id"),
    )
    writer.text("elapsed_baseline.txt", ("shell", "cat", "/proc/uptime"))
    ui_xml = writer.ui_dump(
        "ui_baseline", ("exec-out", "uiautomator", "dump", "/dev/tty")
    )
    screenshot = writer.binary(
        "baseline.png", ("exec-out", "screencap", "-p")
    )

    if "<hierarchy" not in ui_xml:
        writer.failures.append("ui_baseline.xml")
    if not screenshot.startswith(b"\x89PNG\r\n\x1a\n"):
        writer.failures.append("baseline.png")

    role_holder = parse_home_role(role, dict(profile))
    resumed_role = parse_home_role(activity, dict(profile))
    home_role = (
        role_holder
        if resumed_role in {"UNKNOWN", role_holder}
        else "UNKNOWN"
    )
    package_state = parse_package_state(package_text, str(profile["app"]["package"]))
    widget_state = parse_appwidget_state(
        appwidget_text,
        str(profile["app"]["provider"]),
        str(profile["launcher_package"]),
    )
    crash = parse_crash_signature(crash_text)
    result = _initial_result(home_role)
    result.update(
        {
            "crash_signature_count": crash.count,
            "provider_registered": widget_state.provider_registered,
            "widget_bound_before": bool(widget_state.bindings),
        }
    )
    state.update(
        {
            "baseline": {
                "binding_ids": [binding.widget_id for binding in widget_state.bindings],
                "home_role": home_role,
                "package_uid": package_state.uid,
                "provider_uid": widget_state.provider_uid,
            },
            "active_boot_id": boot_id.strip(),
            "final_home_role": home_role,
        }
    )

    unique_failures = sorted(set(writer.failures))
    if not unique_failures:
        phase = assert_transition(None, "capture")
        state.update(
            {
                "capture_complete": True,
                "completed_phases": [phase.value],
                "current_phase": phase.value,
            }
        )
    else:
        result["evidence_term"] = "runtime precondition FAIL"
        result["precondition_status"] = "FAIL"

    bundle.write_json("run.json", state)
    bundle.write_json("result.json", result)
    verification = (
        "capture_complete=" + ("true" if not unique_failures else "false") + "\n"
        + "missing_or_invalid="
        + (",".join(unique_failures) if unique_failures else "—")
        + "\n"
    )
    _write_raw(bundle.directory / "verification.txt", verification)
    verify_evidence_manifest(bundle.directory)

    if unique_failures:
        raise CaptureIncomplete(
            "mandatory capture artifacts failed: " + ", ".join(unique_failures)
        )
    relative_bundle = bundle.directory.relative_to(root).as_posix()
    return {
        "bundle": relative_bundle,
        "current_phase": Phase.BASELINE_CAPTURED.value,
        "run_id": actual_run_id,
    }


def _run_directory(root: Path, profile: Mapping[str, Any], run_id: str) -> Path:
    validate_run_id(run_id)
    evidence_root = root.joinpath(*Path(str(profile["evidence_root"])).parts)
    directory = evidence_root / run_id
    try:
        resolved = directory.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise GateFailure("run directory is missing or outside the repository") from exc
    return resolved


def _read_result(run_directory: Path) -> dict[str, Any]:
    try:
        value = json.loads((run_directory / "result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure("result.json is missing or invalid") from exc
    if not isinstance(value, dict):
        raise GateFailure("result.json must contain an object")
    return value


def _record_command(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    category: str,
    args: tuple[str, ...],
    *,
    now: Clock | None = None,
    binary: bool = False,
    allow_nonzero: bool = False,
):
    result = (
        transport.run_target_binary(args)
        if binary
        else transport.run_target(args)
    )
    instant = _instant(now)
    try:
        event_state = json.loads(
            (bundle.directory / "run.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        event_state = {}
    recorded_phase = event_state.get("current_phase") or "CAPTURING"
    boot_id = event_state.get("active_boot_id")
    if args == ("shell", "cat", "/proc/sys/kernel/random/boot_id"):
        boot_id = str(result.stdout).strip() if result.returncode == 0 else boot_id
    elapsed_realtime = None
    if args == ("shell", "cat", "/proc/uptime") and result.returncode == 0:
        try:
            elapsed_realtime = float(str(result.stdout).split()[0])
        except (IndexError, ValueError):
            elapsed_realtime = None
    bundle.append_event(
        Event(
            timestamp_utc=_timestamp(instant, timezone.utc),
            timestamp_kst=_timestamp(instant, KST),
            phase=phase,
            command_category=category,
            target_serial=serial,
            returncode=result.returncode,
            stdout_sha256=_digest(result.stdout),
            stderr_sha256=_digest(result.stderr),
            resulting_state=str(recorded_phase),
            logical_command=_redact_logical_command(args),
            boot_id=str(boot_id) if boot_id else None,
            device_elapsed_realtime_s=elapsed_realtime,
            previous_state=str(recorded_phase),
        )
    )
    if result.returncode != 0 and not allow_nonzero:
        raise GateFailure(f"device command failed: {category}")
    if binary and not isinstance(result.stdout, bytes):
        raise GateFailure(f"binary command returned text: {category}")
    if not binary and not isinstance(result.stdout, str):
        raise GateFailure(f"text command returned bytes: {category}")
    return result.stdout


def _redact_logical_command(args: tuple[str, ...]) -> tuple[str, ...]:
    if args and args[0] == "install-multiple":
        return (
            args[0],
            *(f"<split:{PureWindowsPath(value).name}>" for value in args[1:]),
        )
    return tuple(
        "<path:redacted>"
        if PureWindowsPath(value).drive or PurePosixPath(value).is_absolute()
        else value
        for value in args
    )


def _wait_for_boot_complete(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    *,
    poll_attempts: int,
    poll_timeout_s: float,
    poll_interval_s: float,
    wait: Callable[[], None] | None,
    now: Clock | None = None,
) -> None:
    """Poll boot completion through transient offline responses with a deadline."""
    deadline = _monotonic() + poll_timeout_s
    for attempt in range(max(1, poll_attempts)):
        boot = _record_command(
            bundle,
            transport,
            serial,
            phase,
            f"boot_complete_poll_{attempt + 1}",
            ("shell", "getprop", "sys.boot_completed"),
            now=now,
            allow_nonzero=True,
        )
        if isinstance(boot, str) and boot.strip() == "1":
            return
        if attempt + 1 >= max(1, poll_attempts) or _monotonic() >= deadline:
            break
        _pause(wait, poll_interval_s)
    raise GateFailure("device did not report boot completion")


def _ui_dump(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    name: str,
    *,
    now: Clock | None = None,
) -> str:
    raw = _record_command(
        bundle,
        transport,
        serial,
        phase,
        name,
        ("exec-out", "uiautomator", "dump", "/dev/tty"),
        now=now,
    )
    assert isinstance(raw, str)
    _write_raw(bundle.directory / "snapshots" / f"{name}.raw.txt", raw)
    try:
        xml = normalize_ui_dump(raw)
    except UiDumpParseError as exc:
        raise GateFailure(f"UI dump is incomplete: {exc}") from exc
    _write_raw(bundle.directory / "snapshots" / f"{name}.xml", xml)
    return xml


def _ui_dump_with_retry(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    name: str,
    *,
    poll_attempts: int,
    poll_interval_s: float,
    now: Clock | None = None,
) -> str:
    """Retry only incomplete UI hierarchies while preserving every raw attempt."""
    last_error: GateFailure | None = None
    for attempt in range(max(1, poll_attempts)):
        try:
            return _ui_dump(
                bundle,
                transport,
                serial,
                phase,
                f"{name}_attempt_{attempt + 1}",
                now=now,
            )
        except GateFailure as exc:
            if not str(exc).startswith("UI dump is incomplete:"):
                raise
            last_error = exc
            if attempt + 1 < max(1, poll_attempts):
                _pause(None, poll_interval_s)
    raise GateFailure(
        f"UI dump remained incomplete after {max(1, poll_attempts)} attempts"
    ) from last_error


def _tap_node(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    xml: str,
    exact_text: str,
    category: str,
    *,
    fallback: tuple[int, int] | None = None,
    now: Clock | None = None,
) -> None:
    node = find_ui_node(xml, exact_text)
    if node is None:
        raise GateFailure(f"required exact UI selector is absent: {exact_text}")
    center = node.center or fallback
    if center is None:
        raise GateFailure(f"required UI selector has no usable bounds: {exact_text}")
    _record_command(
        bundle,
        transport,
        serial,
        phase,
        category,
        ("shell", "input", "tap", str(center[0]), str(center[1])),
        now=now,
    )


def _require_resource_node(
    xml: str,
    resource_id: str,
    *,
    checked: bool | None = None,
):
    if not resource_id:
        raise GateFailure("required UI resource ID is not configured")
    node = find_ui_node_by_resource_id(xml, resource_id)
    if node is None:
        raise GateFailure(f"required UI resource ID is absent: {resource_id}")
    if checked is not None and node.checked is not checked:
        expected = str(checked).lower()
        actual = "unknown" if node.checked is None else str(node.checked).lower()
        raise GateFailure(
            f"UI resource checked state mismatch for {resource_id}: "
            f"expected {expected}, got {actual}"
        )
    return node


def _tap_resource_node(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    phase: str,
    node,
    resource_id: str,
    category: str,
    *,
    now: Clock | None = None,
) -> None:
    center = node.center
    if center is None:
        raise GateFailure(f"required UI resource has no usable bounds: {resource_id}")
    _record_command(
        bundle,
        transport,
        serial,
        phase,
        category,
        ("shell", "input", "tap", str(center[0]), str(center[1])),
        now=now,
    )


def _select_new_binding(widget_state, baseline_ids: set[int]):
    return next(
        (
            binding
            for binding in widget_state.bindings
            if binding.remote_views_present and binding.widget_id not in baseline_ids
        ),
        None,
    )


def _update_mutation_ledger(
    bundle: EvidenceBundle,
    state: dict[str, Any],
    *,
    add: tuple[str, ...] = (),
    remove: tuple[str, ...] = (),
    updates: Mapping[str, Any] | None = None,
) -> list[str]:
    """Durably record mutation intent/result before the next device action."""
    removed = set(remove)
    mutations = [
        item for item in state.get("mutations_remaining", []) if item not in removed
    ]
    for item in add:
        if item not in mutations:
            mutations.append(item)
    state["mutations_remaining"] = mutations
    if updates:
        state.update(updates)
    bundle.write_json("run.json", state)
    return mutations


def _reserve_attempt(
    bundle: EvidenceBundle,
    state: dict[str, Any],
    kind: str,
) -> str:
    """Durably reserve a monotonic ID before any work for a retriable action."""
    counters = dict(state.get("attempt_counters", {}))
    previous = counters.get(kind, 0)
    if not isinstance(previous, int) or isinstance(previous, bool) or previous < 0:
        raise GateFailure(f"invalid {kind} attempt counter")
    current = previous + 1
    attempt_id = f"{kind}-{current:04d}"
    active_attempts = dict(state.get("active_attempts", {}))
    attempts = [dict(item) for item in state.get("attempts", [])]
    reconciliation_required = list(
        state.get("attempt_reconciliation_required", [])
    )
    if reconciliation_required and kind != "restore":
        raise GateFailure(
            "interrupted attempt still requires restore reconciliation"
        )
    if active_attempts:
        active_records: list[dict[str, Any]] = []
        for active_kind, active_id in active_attempts.items():
            record = next(
                (
                    item
                    for item in reversed(attempts)
                    if item.get("attempt_id") == active_id
                    and item.get("kind") == active_kind
                    and item.get("status") == "RESERVED"
                ),
                None,
            )
            if record is None:
                raise GateFailure(
                    f"active attempt ledger is invalid: {active_kind}={active_id}"
                )
            active_records.append(record)
        if kind != "restore":
            interrupted_ids = []
            for record in active_records:
                record["status"] = "INTERRUPTED"
                record["interruption_reason"] = (
                    f"stale active attempt found before {kind}"
                )
                interrupted_ids.append(str(record["attempt_id"]))
            state["attempts"] = attempts
            state["active_attempts"] = {}
            state["attempt_reconciliation_required"] = interrupted_ids
            bundle.write_json("run.json", state)
            raise GateFailure(
                "stale active attempt was recorded as INTERRUPTED; "
                "restore reconciliation is required before another attempt"
            )
        for record in active_records:
            record["status"] = "INTERRUPTED"
            record["interruption_reason"] = (
                f"stale active attempt found before {kind}"
            )
            reconciliation_required.append(str(record["attempt_id"]))
        active_attempts = {}

    if kind == "restore" and reconciliation_required:
        pending_ids = set(reconciliation_required)
        found_ids = set()
        for record in attempts:
            record_id = record.get("attempt_id")
            if record_id in pending_ids and record.get("status") == "INTERRUPTED":
                record["reconciliation_attempt"] = attempt_id
                found_ids.add(str(record_id))
        if found_ids != pending_ids:
            raise GateFailure("attempt reconciliation ledger is invalid")
        state["attempt_reconciliation_required"] = sorted(pending_ids)

    counters[kind] = current
    state["attempt_counters"] = counters
    active_attempts[kind] = attempt_id
    state["active_attempts"] = active_attempts
    attempts.append({"attempt_id": attempt_id, "kind": kind, "status": "RESERVED"})
    state["attempts"] = attempts
    bundle.write_json("run.json", state)
    return attempt_id


def _complete_attempt_reconciliation(
    state: dict[str, Any], restore_attempt_id: str
) -> None:
    """Commit reconciliation only after live restore reached RESTORED_SAFE."""
    pending_ids = set(state.get("attempt_reconciliation_required", []))
    if not pending_ids:
        return
    attempts = [dict(item) for item in state.get("attempts", [])]
    found_ids = set()
    for record in attempts:
        record_id = record.get("attempt_id")
        if record_id not in pending_ids:
            continue
        if (
            record.get("status") != "INTERRUPTED"
            or record.get("reconciliation_attempt") != restore_attempt_id
        ):
            raise GateFailure("attempt reconciliation ledger is invalid")
        record["reconciled_by"] = restore_attempt_id
        found_ids.add(str(record_id))
    if found_ids != pending_ids:
        raise GateFailure("attempt reconciliation ledger is invalid")
    state["attempts"] = attempts
    state["attempt_reconciliation_required"] = []


def _set_attempt_status(
    bundle: EvidenceBundle,
    state: dict[str, Any],
    attempt_id: str,
    status: str,
) -> None:
    _apply_attempt_status(state, attempt_id, status)
    bundle.write_json("run.json", state)


def _apply_attempt_status(
    state: dict[str, Any],
    attempt_id: str,
    status: str,
) -> None:
    attempts = [dict(item) for item in state.get("attempts", [])]
    for item in reversed(attempts):
        if item.get("attempt_id") == attempt_id:
            item["status"] = status
            active_attempts = dict(state.get("active_attempts", {}))
            if active_attempts.get(item.get("kind")) == attempt_id:
                active_attempts.pop(str(item.get("kind")), None)
            state["active_attempts"] = active_attempts
            state["attempts"] = attempts
            return
    raise GateFailure(f"attempt reservation is missing: {attempt_id}")


def _record_active_attempt_failure(
    run_directory: Path,
    kind: str,
    error: BaseException,
) -> None:
    state = _read_state(run_directory)
    active_attempts = dict(state.get("active_attempts", {}))
    attempt_id = active_attempts.get(kind)
    if not isinstance(attempt_id, str):
        return
    attempts = [dict(item) for item in state.get("attempts", [])]
    for item in reversed(attempts):
        if item.get("attempt_id") != attempt_id:
            continue
        item["status"] = "ERROR"
        item["primary_error"] = f"{type(error).__name__}: {error}"
        cleanup_error = getattr(error, "cleanup_error", None)
        if cleanup_error is not None:
            item["cleanup_error"] = (
                f"{type(cleanup_error).__name__}: {cleanup_error}"
            )
        state["attempts"] = attempts
        active_attempts.pop(kind, None)
        state["active_attempts"] = active_attempts
        if kind == "reset-fixture" and (
            state.get("fixture_reset_status") != "FAILED_SAFE"
        ):
            state["fixture_reset_status"] = "FAILED"
            state["run_complete"] = False
        bundle = EvidenceBundle(run_directory)
        bundle.write_json("run.json", state)
        result = _read_result(run_directory)
        result.update(
            {
                "final_home_role": state.get("final_home_role"),
                "mutations_remaining": list(
                    state.get("mutations_remaining", [])
                ),
                "run_complete": state.get("run_complete"),
            }
        )
        if kind == "reset-fixture":
            result["fixture_reset_status"] = state.get("fixture_reset_status")
        bundle.write_json("result.json", result)
        return
    raise GateFailure(f"active attempt record is missing: {attempt_id}")


def bind(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    execute: bool,
    adopt_existing: bool = False,
    now: Clock | None = None,
    poll_attempts: int = 10,
    poll_timeout_s: float = 30.0,
    poll_interval_s: float = 1.0,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Place the exact provider through selector-gated UI and prove binding."""
    if not execute:
        raise GateFailure("bind requires explicit --execute approval")
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = require_run_phase(run_directory, Phase.BASELINE_CAPTURED)
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "bind")
    previous_home_role = state.get("final_home_role")
    preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )
    def mark_home_switch_intent() -> None:
        _update_mutation_ledger(
            bundle,
            state,
            add=("home_role:unverified",),
        )

    role = _ensure_home_role(
        bundle,
        transport,
        serial,
        profile,
        str(profile["general_home"]),
        "bind",
        now=now,
        poll_attempts=poll_attempts,
        poll_timeout_s=poll_timeout_s,
        poll_interval_s=poll_interval_s,
        wait=wait,
        before_switch=mark_home_switch_intent,
        artifact_prefix=attempt_id,
    )
    if role != profile["general_home"]:
        raise GateFailure("bind requires verified General HOME")
    if previous_home_role != profile["general_home"]:
        deadline = _monotonic() + poll_timeout_s
        last_readiness_error: GateFailure | None = None
        for readiness_attempt in range(1, max(1, poll_attempts) + 1):
            try:
                _verify_home_role_three_way(
                    bundle,
                    transport,
                    serial,
                    profile,
                    str(profile["general_home"]),
                    "bind",
                    f"{attempt_id}_general_ready_{readiness_attempt}",
                    now=now,
                )
                last_readiness_error = None
                break
            except GateFailure as error:
                last_readiness_error = error
            if (
                readiness_attempt >= max(1, poll_attempts)
                or _monotonic() >= deadline
            ):
                break
            _pause(wait, poll_interval_s)
        if last_readiness_error is not None:
            raise GateFailure("General HOME did not become ready for widget binding") from last_readiness_error
    mutations = _update_mutation_ledger(
        bundle,
        state,
        add=("home_role:general",),
        remove=("home_role:unverified",),
        updates={
            "final_home_role": str(profile["general_home"]),
        },
    )

    if adopt_existing:
        appwidget_text = _record_command(
            bundle,
            transport,
            serial,
            "bind",
            f"{attempt_id}_adopt_appwidget",
            ("shell", "dumpsys", "appwidget"),
            now=now,
        )
        assert isinstance(appwidget_text, str)
        _write_raw(
            bundle.directory / "snapshots" / f"{attempt_id}_adopt_appwidget.txt",
            appwidget_text,
        )
        widget_state = parse_appwidget_state(
            appwidget_text,
            str(profile["app"]["provider"]),
            str(profile["launcher_package"]),
        )
        if (
            not widget_state.provider_registered
            or len(widget_state.bindings) != 1
            or not widget_state.bindings[0].remote_views_present
        ):
            raise GateFailure(
                "adopt-existing requires exactly one registered exact binding with RemoteViews"
            )
        binding = widget_state.bindings[0]
        baseline_ids = {
            int(value) for value in state.get("baseline", {}).get("binding_ids", [])
        }
        if baseline_ids != {binding.widget_id}:
            raise GateFailure(
                "adopt-existing binding does not match the capture baseline"
            )
        phase = assert_transition(Phase.BASELINE_CAPTURED, "bind")
        completed = list(state.get("completed_phases", []))
        completed.append(phase.value)
        mutations = _update_mutation_ledger(
            bundle,
            state,
            add=("home_role:general", f"widget_binding:{binding.widget_id}"),
        )
        state.update(
            {
                "binding_origin": "ADOPTED_EXISTING",
                "completed_phases": completed,
                "current_phase": phase.value,
                "final_home_role": str(profile["general_home"]),
                "last_bind_attempt_id": attempt_id,
                "mutations_remaining": mutations,
                "old_widget_id": binding.widget_id,
            }
        )
        result = _read_result(run_directory)
        result.update(
            {
                "binding_origin": "ADOPTED_EXISTING",
                "final_home_role": str(profile["general_home"]),
                "mutations_remaining": mutations,
                "provider_registered": True,
                "widget_bound_before": True,
            }
        )
        bundle.write_json("run.json", state)
        bundle.write_json("result.json", result)
        _set_attempt_status(bundle, state, attempt_id, "COMPLETED")
        verify_evidence_manifest(run_directory)
        return {
            "binding_origin": "ADOPTED_EXISTING",
            "current_phase": phase.value,
            "old_widget_id": binding.widget_id,
            "run_id": run_id,
        }

    ui = profile["ui"]
    x, y, duration = ui["home_long_press"]
    _record_command(
        bundle,
        transport,
        serial,
        "bind",
        "home_long_press",
        (
            "shell", "input", "touchscreen", "swipe",
            str(x), str(y), str(x), str(y), str(duration),
        ),
        now=now,
    )
    menu_xml = _ui_dump(
        bundle, transport, serial, "bind", f"{attempt_id}_widget_menu", now=now
    )
    widget_menu_text = str(ui["widget_menu_text"])
    if find_ui_node(menu_xml, widget_menu_text) is None:
        education_resource_id = str(
            ui.get("widget_education_close_resource_id", "")
        )
        education_node = find_ui_node_by_resource_id(
            menu_xml,
            education_resource_id,
        )
        overlay_dismissed = False
        if education_node is not None:
            _tap_resource_node(
                bundle,
                transport,
                serial,
                "bind",
                education_node,
                education_resource_id,
                "dismiss_existing_widget_education",
                now=now,
            )
            overlay_dismissed = True
        else:
            drag_tip_text = str(ui.get("widget_drag_tip_text", ""))
            drag_tip_node = find_ui_node(menu_xml, drag_tip_text)
            if drag_tip_node is not None:
                _tap_node(
                    bundle,
                    transport,
                    serial,
                    "bind",
                    menu_xml,
                    drag_tip_text,
                    "dismiss_existing_widget_drag_tip",
                    now=now,
                )
                overlay_dismissed = True
        if overlay_dismissed:
            _record_command(
                bundle,
                transport,
                serial,
                "bind",
                "home_long_press_after_education",
                (
                    "shell", "input", "touchscreen", "swipe",
                    str(x), str(y), str(x), str(y), str(duration),
                ),
                now=now,
            )
            menu_xml = _ui_dump(
                bundle,
                transport,
                serial,
                "bind",
                f"{attempt_id}_widget_menu_after_education",
                now=now,
            )
    _tap_node(
        bundle, transport, serial, "bind", menu_xml,
        widget_menu_text, "open_widget_menu", now=now,
    )
    search_xml = _ui_dump(
        bundle, transport, serial, "bind", f"{attempt_id}_widget_search", now=now
    )
    search_text = str(ui["widget_search_text"])
    if find_ui_node(search_xml, search_text) is None:
        education_resource_id = str(
            ui.get("widget_education_close_resource_id", "")
        )
        education_node = _require_resource_node(
            search_xml,
            education_resource_id,
        )
        _tap_resource_node(
            bundle,
            transport,
            serial,
            "bind",
            education_node,
            education_resource_id,
            "dismiss_widget_education",
            now=now,
        )
        search_xml = _ui_dump(
            bundle,
            transport,
            serial,
            "bind",
            f"{attempt_id}_widget_search_after_education",
            now=now,
        )
    _tap_node(
        bundle, transport, serial, "bind", search_xml,
        search_text, "focus_widget_search", now=now,
    )
    label = str(ui["provider_label"])
    _record_command(
        bundle,
        transport,
        serial,
        "bind",
        "enter_provider_search",
        ("shell", "input", "text", label),
        now=now,
    )
    provider_xml = _ui_dump(
        bundle, transport, serial, "bind", f"{attempt_id}_provider_row", now=now
    )
    _tap_node(
        bundle, transport, serial, "bind", provider_xml,
        label, "expand_provider", now=now,
    )
    preview_xml = _ui_dump(
        bundle, transport, serial, "bind", f"{attempt_id}_provider_preview", now=now
    )
    if find_ui_node(preview_xml, label) is None:
        drag_tip_text = str(ui.get("widget_drag_tip_text", ""))
        if find_ui_node(preview_xml, drag_tip_text) is not None:
            _tap_node(
                bundle,
                transport,
                serial,
                "bind",
                preview_xml,
                drag_tip_text,
                "dismiss_widget_drag_tip",
                now=now,
            )
            preview_xml = _ui_dump(
                bundle,
                transport,
                serial,
                "bind",
                f"{attempt_id}_provider_preview_after_tip",
                now=now,
            )
    if find_ui_node(preview_xml, label) is None:
        raise GateFailure("provider preview selector is absent")
    provider_variant_text = ui.get("provider_variant_text")
    if provider_variant_text is not None:
        if (
            not isinstance(provider_variant_text, str)
            or not provider_variant_text.strip()
        ):
            raise GateFailure("provider variant selector is invalid")
        if find_ui_node(preview_xml, provider_variant_text) is None:
            raise GateFailure(
                f"required exact provider variant is absent: {provider_variant_text}"
            )
    preview_png = _record_command(
        bundle,
        transport,
        serial,
        "bind",
        "provider_preview_screenshot",
        ("exec-out", "screencap", "-p"),
        now=now,
        binary=True,
    )
    assert isinstance(preview_png, bytes)
    _write_raw(
        bundle.directory / "screenshots" / f"{attempt_id}_provider_preview.png",
        preview_png,
    )
    if not preview_png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise GateFailure("provider preview screenshot is invalid")
    before_attempt_text = _record_command(
        bundle,
        transport,
        serial,
        "bind",
        f"appwidget_before_{attempt_id}",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(before_attempt_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"{attempt_id}_appwidget_before.txt",
        before_attempt_text,
    )
    before_attempt_state = parse_appwidget_state(
        before_attempt_text,
        str(profile["app"]["provider"]),
        str(profile["launcher_package"]),
    )
    baseline_ids = {binding.widget_id for binding in before_attempt_state.bindings}
    _update_mutation_ledger(
        bundle,
        state,
        add=("widget_binding:unknown",),
        updates={
            "widget_binding_attempt_baseline_ids": sorted(baseline_ids),
            "widget_binding_attempt_id": attempt_id,
        },
    )
    sx, sy, ex, ey, drag_ms = ui["widget_drag"]
    _record_command(
        bundle,
        transport,
        serial,
        "bind",
        "drag_widget",
        (
            "shell", "input", "touchscreen", "draganddrop",
            str(sx), str(sy), str(ex), str(ey), str(drag_ms),
        ),
        now=now,
    )
    if bool(ui.get("provider_confirm_required", True)):
        confirm_xml = _ui_dump_with_retry(
            bundle,
            transport,
            serial,
            "bind",
            f"{attempt_id}_provider_confirm",
            poll_attempts=poll_attempts,
            poll_interval_s=poll_interval_s,
            now=now,
        )
        confirm_resource_id = ui.get("provider_confirm_resource_id")
        if confirm_resource_id is not None:
            resource_id = str(confirm_resource_id)
            confirm_node = _require_resource_node(confirm_xml, resource_id)
            _tap_resource_node(
                bundle,
                transport,
                serial,
                "bind",
                confirm_node,
                resource_id,
                "confirm_provider",
                now=now,
            )
        else:
            _tap_node(
                bundle,
                transport,
                serial,
                "bind",
                confirm_xml,
                str(ui["provider_confirm_text"]),
                "confirm_provider",
                fallback=tuple(ui["provider_confirm_fallback"]),
                now=now,
            )

    widget_state = None
    appwidget_text = ""
    deadline = _monotonic() + poll_timeout_s
    for attempt in range(max(1, poll_attempts)):
        appwidget_text = _record_command(
            bundle,
            transport,
            serial,
            "bind",
            f"appwidget_binding_poll_{attempt + 1}",
            ("shell", "dumpsys", "appwidget"),
            now=now,
        )
        assert isinstance(appwidget_text, str)
        _write_raw(
            bundle.directory
            / "snapshots"
            / f"{attempt_id}_appwidget_poll_{attempt + 1}.txt",
            appwidget_text,
        )
        widget_state = parse_appwidget_state(
            appwidget_text,
            str(profile["app"]["provider"]),
            str(profile["launcher_package"]),
        )
        binding = _select_new_binding(widget_state, baseline_ids)
        if binding is not None:
            break
        if attempt + 1 >= max(1, poll_attempts) or _monotonic() >= deadline:
            break
        _pause(wait, poll_interval_s)
    else:
        raise GateFailure("exact provider/host/RemoteViews binding was not observed")
    if binding is None:
        raise GateFailure("new exact provider/host/RemoteViews binding was not observed")

    _write_raw(
        bundle.directory / "snapshots" / f"{attempt_id}_appwidget_bound.txt",
        appwidget_text,
    )
    phase = assert_transition(Phase.BASELINE_CAPTURED, "bind")
    completed = list(state.get("completed_phases", []))
    completed.append(phase.value)
    mutations = _update_mutation_ledger(
        bundle,
        state,
        add=("home_role:general", f"widget_binding:{binding.widget_id}"),
        remove=("widget_binding:unknown",),
        updates={"widget_binding_attempt_baseline_ids": sorted(baseline_ids)},
    )
    state.update(
        {
            "completed_phases": completed,
            "current_phase": phase.value,
            "final_home_role": str(profile["general_home"]),
            "last_bind_attempt_id": attempt_id,
            "mutations_remaining": mutations,
            "old_widget_id": binding.widget_id,
        }
    )
    result = _read_result(run_directory)
    result.update(
        {
            "final_home_role": str(profile["general_home"]),
            "mutations_remaining": mutations,
            "provider_registered": widget_state.provider_registered,
            "widget_bound_before": True,
        }
    )
    bundle.write_json("run.json", state)
    bundle.write_json("result.json", result)
    _set_attempt_status(bundle, state, attempt_id, "COMPLETED")
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": phase.value,
        "old_widget_id": binding.widget_id,
        "run_id": run_id,
    }


def _assert_package_identity(package_state, app: Mapping[str, Any]) -> None:
    expected = (
        str(app["version_name"]),
        int(app["version_code"]),
        str(app["signature_token"]).lower(),
    )
    actual = (
        package_state.version_name,
        package_state.version_code,
        package_state.signature_token.lower()
        if package_state.signature_token is not None
        else None,
    )
    if actual != expected:
        raise GateFailure(
            "installed package version/name/signature differs from immutable input pin"
        )
    if package_state.uid is None:
        raise GateFailure("installed package UID is unavailable")


def _verified_apk_paths(
    root: Path,
    profile: Mapping[str, Any],
    checked_inputs: Mapping[str, Any],
) -> tuple[str, ...]:
    source = root.joinpath(*PurePosixPath(str(checked_inputs["source_bundle"])).parts)
    paths: list[str] = []
    for split in checked_inputs["splits"]:
        logical_id = PurePosixPath(str(split["logical_id"]))
        path = source.joinpath(*logical_id.parts).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise GateFailure("verified APK path escaped the repository") from exc
        paths.append(str(path))
    return tuple(paths)


def _current_role(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    phase: str,
    category: str,
    *,
    now: Clock | None = None,
) -> str:
    text = _record_command(
        bundle,
        transport,
        serial,
        phase,
        category,
        ("shell", "cmd", "role", "get-role-holders", "android.app.role.HOME"),
        now=now,
    )
    assert isinstance(text, str)
    return parse_home_role(text, dict(profile))


def _remove_bound_widget_before_lifecycle(
    *,
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    state: dict[str, Any],
    old_widget_id: int,
    attempt_id: str,
    now: Clock | None = None,
    poll_attempts: int = 30,
    poll_interval_s: float = 2.0,
    wait: Callable[[], None] | None = None,
) -> None:
    """Remove the exact clean-control widget and prove binding loss."""
    role = _current_role(
        bundle,
        transport,
        serial,
        profile,
        "arm",
        f"role_before_{attempt_id}_widget_removal",
        now=now,
    )
    if role != profile["general_home"]:
        raise GateFailure("clean-control widget removal requires verified General HOME")
    stale_marker = f"stale_launcher_record:{old_widget_id}"
    if stale_marker in state.get("mutations_remaining", []):
        raise GateFailure("clean-control fixture already carries a stale-record mutation")

    before_text = _record_command(
        bundle,
        transport,
        serial,
        "arm",
        f"appwidget_before_{attempt_id}_widget_removal",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(before_text, str)
    _write_raw(
        bundle.directory
        / "snapshots"
        / f"appwidget_before_{attempt_id}_widget_removal.txt",
        before_text,
    )
    before_state = parse_appwidget_state(
        before_text,
        str(profile["app"]["provider"]),
        str(profile["launcher_package"]),
    )
    if (
        len(before_state.bindings) != 1
        or before_state.bindings[0].widget_id != old_widget_id
        or not before_state.bindings[0].remote_views_present
    ):
        raise GateFailure(
            "clean-control removal requires one exact bound widget with RemoteViews"
        )

    raw_drag = profile.get("ui", {}).get("widget_remove_drag")
    if (
        not isinstance(raw_drag, (tuple, list))
        or len(raw_drag) != 5
        or any(not isinstance(value, int) for value in raw_drag)
    ):
        raise GateFailure("clean-control widget removal gesture is not configured")
    start_x, start_y, end_x, end_y, duration_ms = raw_drag
    viewport = profile.get("viewport")
    if (
        not isinstance(viewport, (tuple, list))
        or len(viewport) != 2
        or duration_ms <= 0
        or not all(
            0 <= value < limit
            for value, limit in (
                (start_x, int(viewport[0])),
                (end_x, int(viewport[0])),
                (start_y, int(viewport[1])),
                (end_y, int(viewport[1])),
            )
        )
    ):
        raise GateFailure("clean-control widget removal gesture is outside viewport")
    ui = profile.get("ui", {})
    remove_selector = ui.get("widget_remove_selector")
    if remove_selector is not None:
        if not isinstance(remove_selector, str) or not remove_selector.strip():
            raise GateFailure("clean-control widget removal selector is invalid")
        removal_xml = _ui_dump_with_retry(
            bundle,
            transport,
            serial,
            "arm",
            f"{attempt_id}_widget_removal_target",
            poll_attempts=poll_attempts,
            poll_interval_s=poll_interval_s,
            now=now,
        )
        removal_node = find_ui_node(removal_xml, remove_selector)
        if removal_node is None or removal_node.bounds is None:
            raise GateFailure(
                "clean-control exact widget removal selector is absent or unbounded"
            )
        left, top, right, bottom = removal_node.bounds
        if not (left <= start_x < right and top <= start_y < bottom):
            raise GateFailure(
                "widget removal start is outside the exact selected widget bounds"
            )
    else:
        bind_drag = ui.get("widget_drag")
        if (
            not isinstance(bind_drag, (tuple, list))
            or len(bind_drag) != 5
            or (start_x, start_y) != (bind_drag[2], bind_drag[3])
        ):
            raise GateFailure("widget removal start is not pinned to bind destination")

    _record_command(
        bundle,
        transport,
        serial,
        "arm",
        "remove_bound_widget",
        (
            "shell",
            "input",
            "touchscreen",
            "draganddrop",
            str(start_x),
            str(start_y),
            str(end_x),
            str(end_y),
            str(duration_ms),
        ),
        now=now,
    )
    for attempt in range(1, max(1, poll_attempts) + 1):
        after_text = _record_command(
            bundle,
            transport,
            serial,
            "arm",
            f"appwidget_after_{attempt_id}_widget_removal_{attempt}",
            ("shell", "dumpsys", "appwidget"),
            now=now,
        )
        assert isinstance(after_text, str)
        _write_raw(
            bundle.directory
            / "snapshots"
            / f"appwidget_after_{attempt_id}_widget_removal_{attempt}.txt",
            after_text,
        )
        after_state = parse_appwidget_state(
            after_text,
            str(profile["app"]["provider"]),
            str(profile["launcher_package"]),
        )
        if not any(
            binding.widget_id == old_widget_id for binding in after_state.bindings
        ):
            _update_mutation_ledger(
                bundle,
                state,
                remove=(f"widget_binding:{old_widget_id}",),
                updates={
                    "control_kind": "WIDGET_REMOVED_BEFORE_LIFECYCLE",
                    "widget_removed_before_lifecycle": True,
                },
            )
            return
        if attempt < max(1, poll_attempts):
            _pause(wait, poll_interval_s)
    raise GateFailure("widget removal did not remove the exact AppWidget binding")


def arm(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    lifecycle: str,
    execute: bool,
    now: Clock | None = None,
    poll_attempts: int = 30,
    poll_timeout_s: float = 120.0,
    poll_interval_s: float = 2.0,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Establish or disprove the stale-binding precondition."""
    if not execute:
        raise GateFailure("arm requires explicit --execute approval")
    if lifecycle not in {
        "uninstall-reinstall",
        "remove-widget-uninstall-reinstall",
        "clear-force-stop-reboot",
    }:
        raise GateFailure(f"unsupported lifecycle: {lifecycle}")
    clean_control = lifecycle == "remove-widget-uninstall-reinstall"
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = require_run_phase(run_directory, Phase.BOUND_GENERAL)
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    old_widget_id = state.get("old_widget_id")
    if not isinstance(old_widget_id, int):
        raise GateFailure("arm requires the exact old widget ID from bind")

    # The immutable host inputs are checked before even the HOME-role mutation.
    checked_inputs = verify_inputs(root, profile)
    apk_paths = _verified_apk_paths(root, profile, checked_inputs)
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "arm")
    preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )
    bundle.write_json("inputs.json", checked_inputs)

    if clean_control:
        _remove_bound_widget_before_lifecycle(
            bundle=bundle,
            transport=transport,
            serial=serial,
            profile=profile,
            state=state,
            old_widget_id=old_widget_id,
            attempt_id=attempt_id,
            now=now,
            poll_attempts=poll_attempts,
            poll_interval_s=poll_interval_s,
            wait=wait,
        )

    def mark_home_switch_intent() -> None:
        _update_mutation_ledger(
            bundle,
            state,
            add=("home_role:unverified",),
        )

    role = _ensure_home_role(
        bundle,
        transport,
        serial,
        profile,
        str(profile["simple_home"]),
        "arm",
        now=now,
        poll_attempts=poll_attempts,
        wait=wait,
        before_switch=mark_home_switch_intent,
        artifact_prefix=attempt_id,
    )
    if role != profile["simple_home"]:
        raise GateFailure("lifecycle mutation requires verified Simple HOME")
    safe_phase = assert_transition(Phase.BOUND_GENERAL, "arm-switch")
    mutations = [
        item
        for item in state.get("mutations_remaining", [])
        if item not in {"home_role:general", "home_role:unverified"}
    ]
    completed = list(state.get("completed_phases", []))
    if safe_phase.value not in completed:
        completed.append(safe_phase.value)
    state.update(
        {
            "completed_phases": completed,
            "current_phase": safe_phase.value,
            "final_home_role": str(profile["simple_home"]),
            "mutations_remaining": mutations,
        }
    )
    bundle.write_json("run.json", state)

    app = profile["app"]
    package = str(app["package"])
    if lifecycle in {"uninstall-reinstall", "remove-widget-uninstall-reinstall"}:
        _update_mutation_ledger(
            bundle,
            state,
            add=("package:state-unverified",),
        )
        uninstall_stdout = _record_command(
            bundle,
            transport,
            serial,
            "arm",
            "uninstall_package",
            ("uninstall", package),
            now=now,
        )
        if not isinstance(uninstall_stdout, str) or "Success" not in uninstall_stdout:
            raise GateFailure("package uninstall did not report Success")
        mutations = [
            item for item in state.get("mutations_remaining", [])
            if item not in {
                f"widget_binding:{old_widget_id}",
                "package:state-unverified",
            }
        ]
        post_uninstall_markers = ["package:missing"]
        if not clean_control:
            post_uninstall_markers.insert(0, f"stale_launcher_record:{old_widget_id}")
        for item in post_uninstall_markers:
            if item not in mutations:
                mutations.append(item)
        state["mutations_remaining"] = mutations
        bundle.write_json("run.json", state)
        install_stdout = _record_command(
            bundle,
            transport,
            serial,
            "arm",
            "install_verified_splits",
            ("install-multiple", *apk_paths),
            now=now,
        )
        if not isinstance(install_stdout, str) or "Success" not in install_stdout:
            raise GateFailure("install-multiple did not report Success")
        mutations = [
            item
            for item in mutations
            if item not in {"package:missing", "package:state-unverified"}
        ]
        mutations.append("package_identity:unverified")
        state["mutations_remaining"] = mutations
        bundle.write_json("run.json", state)
    else:
        clear_stdout = _record_command(
            bundle,
            transport,
            serial,
            "arm",
            "clear_package",
            ("shell", "pm", "clear", package),
            now=now,
        )
        if not isinstance(clear_stdout, str) or "Success" not in clear_stdout:
            raise GateFailure("package clear did not report Success")
        _record_command(
            bundle,
            transport,
            serial,
            "arm",
            "force_stop_package",
            ("shell", "am", "force-stop", package),
            now=now,
        )
        _record_command(
            bundle,
            transport,
            serial,
            "arm",
            "reboot_target",
            ("reboot",),
            now=now,
        )
        _wait_for_boot_complete(
            bundle,
            transport,
            serial,
            "arm",
            poll_attempts=poll_attempts,
            poll_timeout_s=poll_timeout_s,
            poll_interval_s=poll_interval_s,
            wait=wait,
            now=now,
        )
        recovered_role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            "arm",
            "role_after_reboot",
            now=now,
        )
        if recovered_role != profile["simple_home"]:
            raise GateFailure("Simple HOME role was not recovered after reboot")

    package_text = _record_command(
        bundle,
        transport,
        serial,
        "arm",
        "package_after_lifecycle",
        ("shell", "dumpsys", "package", package),
        now=now,
    )
    assert isinstance(package_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"package_after_{attempt_id}.txt",
        package_text,
    )
    appwidget_text = _record_command(
        bundle,
        transport,
        serial,
        "arm",
        "appwidget_after_lifecycle",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(appwidget_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"appwidget_after_{attempt_id}.txt",
        appwidget_text,
    )
    package_state = parse_package_state(package_text, package)
    _assert_package_identity(package_state, app)
    widget_state = parse_appwidget_state(
        appwidget_text,
        str(app["provider"]),
        str(profile["launcher_package"]),
    )
    old_binding_retained = any(
        binding.widget_id == old_widget_id for binding in widget_state.bindings
    )
    result = _read_result(run_directory)
    mutations = [
        mutation
        for mutation in state.get("mutations_remaining", [])
        if mutation
        not in {
            "home_role:general",
            "package_identity:unverified",
        }
    ]

    if clean_control and old_binding_retained:
        raise GateFailure("clean-control widget binding reappeared after lifecycle")
    if old_binding_retained:
        phase = assert_transition(Phase.BOUND_GENERAL, "negative-control-failed")
        result.update(
            {
                "evidence_term": "runtime precondition FAIL",
                "final_home_role": str(profile["simple_home"]),
                "mutations_remaining": mutations,
                "precondition_status": "FAIL",
                "provider_registered": widget_state.provider_registered,
                "widget_bound_before": True,
                "widget_bound_after": True,
            }
        )
        state.update(
            {
                "current_phase": phase.value,
                "final_home_role": str(profile["simple_home"]),
                "last_arm_attempt_id": attempt_id,
                "mutations_remaining": mutations,
                "precondition_status": "FAIL",
            }
        )
    else:
        mutations = [
            mutation
            for mutation in mutations
            if mutation != f"widget_binding:{old_widget_id}"
        ]
        if not widget_state.provider_registered or widget_state.provider_uid is None:
            raise GateFailure("provider registry/UID was not restored")
        if widget_state.provider_uid != package_state.uid:
            raise GateFailure("provider UID and installed package UID differ")
        phase = assert_transition(
            safe_phase,
            "arm-clean-control" if clean_control else "arm-lifecycle",
        )
        if not clean_control:
            mutation = f"stale_launcher_record:{old_widget_id}"
            if mutation not in mutations:
                mutations.append(mutation)
        completed = list(state.get("completed_phases", []))
        if phase.value not in completed:
            completed.append(phase.value)
        state.update(
            {
                "completed_phases": completed,
                "current_phase": phase.value,
                "final_home_role": str(profile["simple_home"]),
                "last_arm_attempt_id": attempt_id,
                "mutations_remaining": mutations,
                "new_provider_uid": widget_state.provider_uid,
                "precondition_status": (
                    "CLEAN_CONTROL_READY" if clean_control else "PASS"
                ),
            }
        )
        result.update(
            {
                "evidence_term": "manual evidence observed",
                "final_home_role": str(profile["simple_home"]),
                "mutations_remaining": mutations,
                "precondition_kind": (
                    "CLEAN_REMOVAL_CONTROL" if clean_control else "STALE_BINDING"
                ),
                "precondition_status": (
                    "CLEAN_CONTROL_READY" if clean_control else "PASS"
                ),
                "control_precondition_status": "PASS" if clean_control else None,
                "binding_absence_cause": (
                    "UI_REMOVAL_VERIFIED" if clean_control else "PACKAGE_LIFECYCLE"
                ),
                "widget_removed_before_lifecycle": clean_control,
                "provider_registered": True,
                "widget_bound_before": True,
                "widget_bound_after": False,
            }
        )

    bundle.write_json("run.json", state)
    bundle.write_json("result.json", result)
    _set_attempt_status(bundle, state, attempt_id, "COMPLETED")
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": phase.value,
        "precondition_status": result["precondition_status"],
        "run_id": run_id,
    }


def classify_trigger(
    *,
    precondition_status: str,
    home_rendered: bool,
    launcher_process_stable: bool,
    crash_signature_count: int,
    launcher_stale_record_evidence: str,
    safe_placeholder_or_cleanup: bool,
    normal_widget_update: bool,
) -> dict[str, str]:
    """Apply the known-bad/fixed verdict boundary without device access."""
    if precondition_status != "PASS":
        raise GateFailure("stale state-equivalence precondition is not PASS")
    if crash_signature_count > 0:
        return {
            "diagnosis_status": "OBSERVED",
            "evidence_term": "BUG-GAP observed",
            "phase": Phase.TRIGGERED_BUG.value,
        }
    fixed_evidence = launcher_stale_record_evidence in {
        "DIRECT_DB",
        "LOADER_LOG",
        "PRESERVED_PREUPGRADE",
    }
    if all(
        (
            home_rendered,
            launcher_process_stable,
            fixed_evidence,
            safe_placeholder_or_cleanup,
            normal_widget_update,
        )
    ):
        return {
            "diagnosis_status": "OBSERVED",
            "evidence_term": "runtime PASS",
            "phase": Phase.TRIGGERED_FIXED.value,
        }
    raise GateFailure("zero crash is inconclusive: fixed verdict gates are incomplete")


def classify_clean_control(
    *,
    home_rendered: bool,
    launcher_process_stable: bool,
    crash_signature_count: int,
) -> dict[str, str]:
    """Classify the widget-removed control without implying a stale/fixed PASS."""
    if crash_signature_count > 0:
        return {
            "control_outcome": "BUG_OBSERVED",
            "diagnosis_status": "OBSERVED",
            "evidence_term": "BUG-GAP observed",
            "phase": Phase.TRIGGERED_CONTROL_BUG.value,
        }
    if home_rendered and launcher_process_stable:
        return {
            "control_outcome": "NO_TRIGGER_OBSERVED",
            "diagnosis_status": "OBSERVED",
            "evidence_term": "manual evidence observed",
            "phase": Phase.TRIGGERED_CONTROL_NO_BUG.value,
        }
    raise GateFailure("clean-control observation is inconclusive")


def _signature_delta_count(current: str, baseline: str) -> int:
    current_records = Counter(parse_crash_signature(current).matched_records)
    baseline_records = Counter(parse_crash_signature(baseline).matched_records)
    return sum((current_records - baseline_records).values())


def _phase_crash_signature_count(
    *,
    current_crash: str,
    baseline_crash: str,
    current_exit_info: str,
    baseline_exit_info: str,
    same_boot: bool,
) -> int:
    """Count only BUG27084 signatures added after the active-boot baseline."""
    crash_baseline = baseline_crash if same_boot else ""
    exit_baseline = baseline_exit_info if same_boot else ""
    return max(
        _signature_delta_count(current_crash, crash_baseline),
        _signature_delta_count(current_exit_info, exit_baseline),
    )


def _phase_launcher_crash_exits(
    *,
    current_exit_info: str,
    baseline_exit_info: str,
    launcher_package: str,
    same_boot: bool,
) -> tuple[LauncherCrashExit, ...]:
    """Return active-window exact-package APP CRASH exits by stable identity."""
    current = Counter(
        parse_launcher_crash_exits(current_exit_info, launcher_package)
    )
    baseline = (
        Counter(parse_launcher_crash_exits(baseline_exit_info, launcher_package))
        if same_boot
        else Counter()
    )
    return tuple((current - baseline).elements())


def _classify_loop_evidence(
    *,
    crash_signature_count: int,
    launcher_crash_exit_count: int,
) -> tuple[bool, list[str]]:
    """Keep one recovered crash distinct from repeated crash-loop evidence."""
    basis: list[str] = []
    if crash_signature_count >= 2:
        basis.append("BUG27084_SIGNATURES")
    if launcher_crash_exit_count >= 2:
        basis.append("LAUNCHER_APP_CRASH_EXITS")
    return bool(basis), basis


def _loader_records(text: str, old_widget_id: int) -> Counter[str]:
    pattern = re.compile(
        rf"Widget provider not found for id={old_widget_id}(?!\d)"
    )
    return Counter(
        line.strip() for line in text.splitlines() if pattern.search(line)
    )


def _has_new_loader_record(
    current: str,
    baseline: str,
    *,
    old_widget_id: int,
    same_boot: bool,
) -> bool:
    """Require a phase-new loader record for the exact armed widget ID."""
    return _new_loader_record_count(
        current,
        baseline,
        old_widget_id=old_widget_id,
        same_boot=same_boot,
    ) > 0


def _new_loader_record_count(
    current: str,
    baseline: str,
    *,
    old_widget_id: int,
    same_boot: bool,
) -> int:
    """Count phase-new loader records for the exact armed widget ID."""
    baseline_records = (
        _loader_records(baseline, old_widget_id) if same_boot else Counter()
    )
    return sum((_loader_records(current, old_widget_id) - baseline_records).values())


def run_with_safety_cleanup(operation: Callable[[], Any], cleanup: Callable[[], Any]):
    """Run safety cleanup on primary failure without obscuring that failure."""
    try:
        return operation()
    except Exception as primary:
        try:
            cleanup()
        except Exception as cleanup_error:
            setattr(primary, "cleanup_error", cleanup_error)
            if hasattr(primary, "add_note"):
                primary.add_note(f"safety cleanup also failed: {cleanup_error}")
        raise


def _run_reset_with_safety_cleanup(
    operation: Callable[[], Any], cleanup: Callable[[], Any]
):
    """Attempt reset cleanup for ordinary failures and operator interruption."""
    try:
        return operation()
    except BaseException as primary:
        try:
            cleanup()
        except BaseException as cleanup_error:
            setattr(primary, "cleanup_error", cleanup_error)
            if hasattr(primary, "add_note"):
                primary.add_note(f"safety cleanup also failed: {cleanup_error}")
        raise


def _ensure_home_role(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    target_role: str,
    phase: str,
    *,
    now: Clock | None = None,
    poll_attempts: int = 15,
    poll_timeout_s: float = 30.0,
    poll_interval_s: float = 1.0,
    wait: Callable[[], None] | None = None,
    before_switch: Callable[[], None] | None = None,
    artifact_prefix: str | None = None,
    required_source_role: str | None = None,
) -> str:
    artifact_stem = artifact_prefix or phase
    current = _current_role(
        bundle,
        transport,
        serial,
        profile,
        phase,
        f"role_before_{artifact_stem}",
        now=now,
    )
    if required_source_role is not None and current != required_source_role:
        raise GateFailure(
            f"HOME role drifted before switch: expected {required_source_role}, "
            f"got {current}"
        )
    if current == target_role:
        return current
    if current not in {profile["simple_home"], profile["general_home"]}:
        raise GateFailure("current HOME role is neither configured Simple nor General HOME")
    _record_command(
        bundle,
        transport,
        serial,
        phase,
        "open_mode_switch",
        ("shell", "am", "start", "-n", str(profile["switch_activity"])),
        now=now,
    )
    mode_xml = _ui_dump(
        bundle,
        transport,
        serial,
        phase,
        f"{artifact_stem}_mode_switch",
        now=now,
    )
    mode_ui = profile.get("mode_ui", {})
    target_selector_key = (
        "switch_to_simple_resource_id"
        if target_role == profile["simple_home"]
        else "switch_to_general_resource_id"
    )
    source_selector_key = (
        "switch_to_general_resource_id"
        if target_role == profile["simple_home"]
        else "switch_to_simple_resource_id"
    )
    target_resource_id = str(mode_ui.get(target_selector_key, ""))
    source_resource_id = str(mode_ui.get(source_selector_key, ""))
    confirm_resource_id = str(mode_ui.get("confirm_resource_id", ""))
    target_node = _require_resource_node(
        mode_xml,
        target_resource_id,
        checked=False,
    )
    _require_resource_node(mode_xml, source_resource_id, checked=True)
    confirm_node = _require_resource_node(mode_xml, confirm_resource_id)
    if target_node.center is None:
        raise GateFailure(
            f"required UI resource has no usable bounds: {target_resource_id}"
        )
    if confirm_node.center is None:
        raise GateFailure(
            f"required UI resource has no usable bounds: {confirm_resource_id}"
        )
    if before_switch is not None:
        before_switch()
    _tap_resource_node(
        bundle,
        transport,
        serial,
        phase,
        target_node,
        target_resource_id,
        "select_mode",
        now=now,
    )
    selected_xml = _ui_dump(
        bundle,
        transport,
        serial,
        phase,
        f"{artifact_stem}_mode_selected",
        now=now,
    )
    _require_resource_node(selected_xml, target_resource_id, checked=True)
    _require_resource_node(selected_xml, source_resource_id, checked=False)
    selected_confirm_node = _require_resource_node(
        selected_xml,
        confirm_resource_id,
    )
    _tap_resource_node(
        bundle,
        transport,
        serial,
        phase,
        selected_confirm_node,
        confirm_resource_id,
        "confirm_mode_switch",
        now=now,
    )
    permission_handled = False
    deadline = _monotonic() + poll_timeout_s
    for _attempt in range(max(1, poll_attempts)):
        current = _current_role(
            bundle,
            transport,
            serial,
            profile,
            phase,
            f"role_poll_{artifact_stem}",
            now=now,
        )
        if current == target_role:
            return current
        allow_text = str(mode_ui.get("always_allow_text", ""))
        if allow_text and not permission_handled:
            permission_xml = _ui_dump(
                bundle,
                transport,
                serial,
                phase,
                f"{artifact_stem}_mode_permission",
                now=now,
            )
            if find_ui_node(permission_xml, allow_text) is not None:
                _tap_node(
                    bundle,
                    transport,
                    serial,
                    phase,
                    permission_xml,
                    allow_text,
                    "confirm_mode_permission",
                    now=now,
                )
                permission_handled = True
        if _attempt + 1 >= max(1, poll_attempts) or _monotonic() >= deadline:
            break
        _pause(wait, poll_interval_s)
    raise GateFailure(f"target HOME role was not reached: {target_role}")


def _recover_simple_home_role_direct(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    state: Mapping[str, Any],
    phase: str,
    *,
    now: Clock | None = None,
    poll_attempts: int = 15,
    poll_timeout_s: float = 30.0,
    poll_interval_s: float = 1.0,
    wait: Callable[[], None] | None = None,
    before_switch: Callable[[], None] | None = None,
    artifact_prefix: str | None = None,
) -> str:
    """Recover Simple HOME without racing Launcher crash-dialog restarts."""
    if not {
        "home_role:general",
        "home_role:unverified",
    }.intersection(state.get("mutations_remaining", [])):
        raise GateFailure(
            "direct recovery requires a recorded General HOME mutation"
        )
    artifact_stem = artifact_prefix or phase
    current = _current_role(
        bundle,
        transport,
        serial,
        profile,
        phase,
        f"role_before_{artifact_stem}_direct",
        now=now,
    )
    if current != profile["general_home"]:
        raise GateFailure(
            "direct recovery requires verified General HOME as the current role"
        )
    crash_xml = _ui_dump(
        bundle,
        transport,
        serial,
        phase,
        f"{artifact_stem}_launcher_crash_dialog",
        now=now,
    )
    recovery_ui = profile.get("recovery_ui", {})
    raw_titles = recovery_ui.get("launcher_crash_titles", ())
    titles = (
        tuple(str(value) for value in raw_titles if str(value))
        if isinstance(raw_titles, (tuple, list))
        else ()
    )
    title_resource_id = str(recovery_ui.get("title_resource_id", ""))
    close_resource_id = str(recovery_ui.get("close_resource_id", ""))
    title_node = find_ui_node_by_resource_id(crash_xml, title_resource_id)
    close_node = find_ui_node_by_resource_id(crash_xml, close_resource_id)
    if (
        titles != _LAUNCHER_CRASH_TITLES
        or title_resource_id != _ANDROID_ALERT_TITLE_RESOURCE_ID
        or close_resource_id != _ANDROID_AERR_CLOSE_RESOURCE_ID
        or title_node is None
        or title_node.text not in titles
        or close_node is None
    ):
        raise GateFailure("exact Launcher crash dialog is not present")
    if before_switch is not None:
        before_switch()
    _record_command(
        bundle,
        transport,
        serial,
        phase,
        "set_simple_home_role_direct",
        (
            "shell",
            "cmd",
            "role",
            "add-role-holder",
            "--user",
            "0",
            "android.app.role.HOME",
            str(profile["simple_home"]),
        ),
        now=now,
    )
    _record_command(
        bundle,
        transport,
        serial,
        phase,
        "render_simple_home_direct",
        ("shell", "input", "keyevent", "KEYCODE_HOME"),
        now=now,
    )
    deadline = _monotonic() + poll_timeout_s
    for attempt in range(1, max(1, poll_attempts) + 1):
        role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            phase,
            f"role_poll_{artifact_stem}_direct_{attempt}",
            now=now,
        )
        if role == profile["simple_home"]:
            activity = _record_command(
                bundle,
                transport,
                serial,
                phase,
                "activity_after_direct_recovery",
                ("shell", "dumpsys", "activity", "activities"),
                now=now,
            )
            assert isinstance(activity, str)
            _write_raw(
                bundle.directory
                / "snapshots"
                / f"activity_after_{artifact_stem}_direct_{attempt}.txt",
                activity,
            )
            ui_xml = _ui_dump(
                bundle,
                transport,
                serial,
                phase,
                f"{artifact_stem}_simple_home_direct_{attempt}",
                now=now,
            )
            if (
                parse_home_role(activity, dict(profile))
                == profile["simple_home"]
                and ui_contains_exact_package(
                    ui_xml, str(profile["simple_home"])
                )
            ):
                return str(profile["simple_home"])
        if attempt >= max(1, poll_attempts) or _monotonic() >= deadline:
            break
        _pause(wait, poll_interval_s)
    raise GateFailure("direct HOME role recovery failed 3-way verification")


def _verify_home_role_three_way(
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    target_role: str,
    phase: str,
    artifact_stem: str,
    *,
    now: Clock | None = None,
) -> str:
    """Require fresh role, resumed activity, and UI package agreement."""
    role = _current_role(
        bundle,
        transport,
        serial,
        profile,
        phase,
        f"role_verify_{artifact_stem}",
        now=now,
    )
    activity = _record_command(
        bundle,
        transport,
        serial,
        phase,
        f"activity_verify_{artifact_stem}",
        ("shell", "dumpsys", "activity", "activities"),
        now=now,
    )
    assert isinstance(activity, str)
    _write_raw(
        bundle.directory / "snapshots" / f"activity_verify_{artifact_stem}.txt",
        activity,
    )
    ui_xml = _ui_dump(
        bundle,
        transport,
        serial,
        phase,
        f"ui_verify_{artifact_stem}",
        now=now,
    )
    if (
        role != target_role
        or parse_home_role(activity, dict(profile)) != target_role
        or not ui_contains_exact_package(ui_xml, target_role)
    ):
        raise GateFailure("target HOME role failed 3-way verification")
    return target_role


def _capture_attempt_baseline(
    *,
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    event_phase: str,
    artifact_suffix: str,
    now: Clock | None = None,
) -> dict[str, str]:
    """Capture the log/boot boundary immediately before one observation attempt."""
    commands = {
        "crash": ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"),
        "main_log": ("shell", "logcat", "-d", "-v", "threadtime"),
        "exit_info": (
            "shell",
            "dumpsys",
            "activity",
            "exit-info",
            str(profile["launcher_package"]),
        ),
        "boot_id": ("shell", "cat", "/proc/sys/kernel/random/boot_id"),
    }
    captured: dict[str, str] = {}
    for name, command in commands.items():
        value = _record_command(
            bundle,
            transport,
            serial,
            event_phase,
            f"{name}_before_{artifact_suffix}",
            command,
            now=now,
        )
        assert isinstance(value, str)
        captured[name] = value
        _write_raw(
            bundle.directory
            / "snapshots"
            / f"{name}_before_{artifact_suffix}.txt",
            value,
        )
    if not captured["boot_id"].strip():
        raise GateFailure("boot ID is missing from attempt baseline")
    return captured


def _observe_trigger(
    *,
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    home_role: str,
    old_widget_id: int,
    attempt_baseline: Mapping[str, str],
    event_phase: str = "trigger",
    artifact_suffix: str = "trigger",
    now: Clock | None = None,
    wait: Callable[[], None] | None = None,
    stability_window_s: float = 30.0,
) -> dict[str, Any]:
    activity = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"activity_after_{artifact_suffix}",
        ("shell", "dumpsys", "activity", "activities"),
        now=now,
    )
    assert isinstance(activity, str)
    _write_raw(
        bundle.directory / "snapshots" / f"activity_after_{artifact_suffix}.txt",
        activity,
    )
    ui_xml = _ui_dump(
        bundle,
        transport,
        serial,
        event_phase,
        f"ui_after_{artifact_suffix}",
        now=now,
    )
    screenshot = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"screenshot_after_{artifact_suffix}",
        ("exec-out", "screencap", "-p"),
        now=now,
        binary=True,
    )
    assert isinstance(screenshot, bytes)
    _write_raw(
        bundle.directory / "screenshots" / f"{artifact_suffix}.png", screenshot
    )
    pid_before = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"launcher_pid_before_{artifact_suffix}_window",
        ("shell", "pidof", str(profile["launcher_package"])),
        now=now,
    )
    assert isinstance(pid_before, str)
    _write_raw(
        bundle.directory / "snapshots" / f"pid_before_{artifact_suffix}.txt",
        pid_before,
    )
    _pause(wait, stability_window_s)
    pid_after = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"launcher_pid_after_{artifact_suffix}_window",
        ("shell", "pidof", str(profile["launcher_package"])),
        now=now,
    )
    assert isinstance(pid_after, str)
    _write_raw(
        bundle.directory / "snapshots" / f"pid_after_{artifact_suffix}.txt",
        pid_after,
    )
    crash_text = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"crash_after_{artifact_suffix}",
        ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"),
        now=now,
    )
    assert isinstance(crash_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"crash_after_{artifact_suffix}.txt",
        crash_text,
    )
    main_log = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"main_log_after_{artifact_suffix}",
        ("shell", "logcat", "-d", "-v", "threadtime"),
        now=now,
    )
    assert isinstance(main_log, str)
    _write_raw(
        bundle.directory / "snapshots" / f"main_log_after_{artifact_suffix}.txt",
        main_log,
    )
    exit_info = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"exit_info_after_{artifact_suffix}",
        (
            "shell", "dumpsys", "activity", "exit-info",
            str(profile["launcher_package"]),
        ),
        now=now,
    )
    assert isinstance(exit_info, str)
    _write_raw(
        bundle.directory / "snapshots" / f"exit_info_after_{artifact_suffix}.txt",
        exit_info,
    )
    current_boot_id = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"boot_id_after_{artifact_suffix}",
        ("shell", "cat", "/proc/sys/kernel/random/boot_id"),
        now=now,
    )
    assert isinstance(current_boot_id, str)
    _write_raw(
        bundle.directory / "snapshots" / f"boot_id_after_{artifact_suffix}.txt",
        current_boot_id,
    )
    appwidget_text = _record_command(
        bundle,
        transport,
        serial,
        event_phase,
        f"appwidget_after_{artifact_suffix}",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(appwidget_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"appwidget_after_{artifact_suffix}.txt",
        appwidget_text,
    )
    assert all(
        isinstance(value, str)
        for value in (
            activity,
            ui_xml,
            crash_text,
            main_log,
            exit_info,
            current_boot_id,
            pid_before,
            pid_after,
            appwidget_text,
        )
    )
    current_boot = current_boot_id.strip()
    attempt_boot = str(attempt_baseline.get("boot_id", "")).strip()
    if not current_boot or not attempt_boot:
        raise GateFailure("boot ID is missing from phase evidence")
    same_boot = current_boot == attempt_boot
    crash_signature_count = _phase_crash_signature_count(
        current_crash=crash_text,
        baseline_crash=str(attempt_baseline.get("crash", "")),
        current_exit_info=exit_info,
        baseline_exit_info=str(attempt_baseline.get("exit_info", "")),
        same_boot=same_boot,
    )
    launcher_crash_exits = _phase_launcher_crash_exits(
        current_exit_info=exit_info,
        baseline_exit_info=str(attempt_baseline.get("exit_info", "")),
        launcher_package=str(profile["launcher_package"]),
        same_boot=same_boot,
    )
    loop_observed, loop_basis = _classify_loop_evidence(
        crash_signature_count=crash_signature_count,
        launcher_crash_exit_count=len(launcher_crash_exits),
    )
    resumed_role = parse_home_role(activity, dict(profile))
    parsed_role = home_role if resumed_role == home_role else "UNKNOWN"
    home_rendered = (
        parsed_role == profile["general_home"]
        and "<hierarchy" in ui_xml
        and screenshot.startswith(b"\x89PNG\r\n\x1a\n")
    )
    before = pid_before.strip()
    after = pid_after.strip()
    stable = bool(before) and before == after
    loader_record_count = _new_loader_record_count(
        main_log,
        str(attempt_baseline.get("main_log", "")),
        old_widget_id=old_widget_id,
        same_boot=same_boot,
    )
    stale_evidence = "LOADER_LOG" if loader_record_count else "INFERRED_ONLY"
    fixed = profile.get("fixed_evidence", {})
    safe_marker = str(fixed.get("safe_placeholder_marker", ""))
    update_marker = str(fixed.get("normal_widget_update_marker", ""))
    combined = f"{ui_xml}\n{main_log}\n{appwidget_text}"
    return {
        "appwidget_text": appwidget_text,
        "crash_signature_count": crash_signature_count,
        "evidence_boot_id": current_boot,
        "evidence_same_boot_as_baseline": same_boot,
        "evidence_same_boot_as_attempt": same_boot,
        "home_rendered": home_rendered,
        "launcher_crash_exit_count": len(launcher_crash_exits),
        "launcher_crash_exit_pids": [item.pid for item in launcher_crash_exits],
        "launcher_loader_record_count": loader_record_count,
        "launcher_loop_basis": loop_basis,
        "launcher_loop_observed": loop_observed,
        "launcher_process_stable": stable,
        "launcher_stability_window_s": stability_window_s,
        "launcher_stale_record_evidence": stale_evidence,
        "normal_widget_update": bool(update_marker) and update_marker in combined,
        "safe_placeholder_or_cleanup": bool(safe_marker) and safe_marker in combined,
    }


def trigger(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    execute: bool,
    now: Clock | None = None,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Enter General HOME, observe the stale record, and classify the outcome."""
    if not execute:
        raise GateFailure("trigger requires explicit --execute approval")
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = _read_state(run_directory)
    if not state.get("capture_complete"):
        raise GateFailure("baseline capture is incomplete")
    try:
        armed_phase = Phase(state.get("current_phase"))
    except ValueError as exc:
        raise GateFailure("run has an unknown phase") from exc
    if armed_phase not in {Phase.STALE_ARMED, Phase.CLEAN_CONTROL_ARMED}:
        raise GateFailure("trigger requires a stale or clean-control armed run")
    clean_control = armed_phase is Phase.CLEAN_CONTROL_ARMED
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    result = _read_result(run_directory)
    precondition = result.get("precondition_status", state.get("precondition_status"))
    expected_precondition = "CLEAN_CONTROL_READY" if clean_control else "PASS"
    if precondition != expected_precondition:
        raise GateFailure("trigger is blocked because its precondition is not ready")
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "trigger")
    preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )

    def observe_and_classify():
        initial_role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            "trigger",
            f"role_before_{attempt_id}",
            now=now,
        )
        if initial_role != profile["simple_home"]:
            raise GateFailure("trigger requires verified Simple HOME before baseline")
        attempt_baseline = _capture_attempt_baseline(
            bundle=bundle,
            transport=transport,
            serial=serial,
            profile=profile,
            event_phase="trigger",
            artifact_suffix=attempt_id,
            now=now,
        )

        def mark_home_switch_intent() -> None:
            _update_mutation_ledger(
                bundle,
                state,
                add=("home_role:unverified",),
            )

        home_role = _ensure_home_role(
            bundle,
            transport,
            serial,
            profile,
            str(profile["general_home"]),
            "trigger",
            now=now,
            wait=wait,
            before_switch=mark_home_switch_intent,
            artifact_prefix=attempt_id,
            required_source_role=str(profile["simple_home"]),
        )
        _update_mutation_ledger(
            bundle,
            state,
            add=("home_role:general",),
            remove=("home_role:unverified",),
            updates={
                "final_home_role": str(profile["general_home"]),
            },
        )
        observation = _observe_trigger(
            bundle=bundle,
            transport=transport,
            serial=serial,
            profile=profile,
            home_role=home_role,
            old_widget_id=int(state["old_widget_id"]),
            attempt_baseline=attempt_baseline,
            event_phase="trigger",
            artifact_suffix=attempt_id,
            now=now,
            wait=wait,
        )
        if clean_control:
            classification = classify_clean_control(
                home_rendered=bool(observation["home_rendered"]),
                launcher_process_stable=bool(observation["launcher_process_stable"]),
                crash_signature_count=int(observation["crash_signature_count"]),
            )
        else:
            classification = classify_trigger(
                precondition_status=str(precondition),
                home_rendered=bool(observation["home_rendered"]),
                launcher_process_stable=bool(observation["launcher_process_stable"]),
                crash_signature_count=int(observation["crash_signature_count"]),
                launcher_stale_record_evidence=str(
                    observation["launcher_stale_record_evidence"]
                ),
                safe_placeholder_or_cleanup=bool(
                    observation["safe_placeholder_or_cleanup"]
                ),
                normal_widget_update=bool(observation["normal_widget_update"]),
            )
        return home_role, observation, classification

    def cleanup_primary_failure() -> None:
        def mark_home_switch_intent() -> None:
            _update_mutation_ledger(
                bundle,
                state,
                add=("home_role:unverified",),
            )

        final_role = _ensure_home_role(
            bundle,
            transport,
            serial,
            profile,
            str(profile["simple_home"]),
            "trigger-cleanup",
            now=now,
            wait=wait,
            before_switch=mark_home_switch_intent,
            artifact_prefix=f"{attempt_id}_cleanup",
        )
        remaining = [
            item
            for item in state.get("mutations_remaining", [])
            if item not in {"home_role:general", "home_role:unverified"}
        ]
        state.update(
            {
                "final_home_role": final_role,
                "mutations_remaining": remaining,
            }
        )
        bundle.write_json("run.json", state)

    home_role, observation, classification = run_with_safety_cleanup(
        observe_and_classify, cleanup_primary_failure
    )
    if clean_control:
        outcome = (
            "bug"
            if classification["phase"] == Phase.TRIGGERED_CONTROL_BUG.value
            else "no-bug"
        )
        phase = assert_transition(
            Phase.CLEAN_CONTROL_ARMED,
            "trigger-control",
            outcome=outcome,
        )
    else:
        outcome = (
            "bug" if classification["phase"] == Phase.TRIGGERED_BUG.value else "fixed"
        )
        phase = assert_transition(Phase.STALE_ARMED, "trigger", outcome=outcome)
    completed = list(state.get("completed_phases", []))
    completed.append(phase.value)
    mutations = list(state.get("mutations_remaining", []))
    if "home_role:general" not in mutations:
        mutations.append("home_role:general")
    state.update(
        {
            "completed_phases": completed,
            "current_phase": phase.value,
            "final_home_role": str(profile["general_home"]),
            "last_trigger_attempt_id": attempt_id,
            "mutations_remaining": mutations,
        }
    )
    result.update(
        {
            "crash_signature_count": observation["crash_signature_count"],
            "diagnosis_status": classification["diagnosis_status"],
            "evidence_term": classification["evidence_term"],
            "evidence_boot_id": observation["evidence_boot_id"],
            "evidence_same_boot_as_baseline": observation[
                "evidence_same_boot_as_baseline"
            ],
            "final_home_role": str(profile["general_home"]),
            "home_rendered": observation["home_rendered"],
            "launcher_crash_exit_count": observation[
                "launcher_crash_exit_count"
            ],
            "launcher_crash_exit_pids": observation[
                "launcher_crash_exit_pids"
            ],
            "launcher_loader_record_count": observation[
                "launcher_loader_record_count"
            ],
            "launcher_loop_basis": observation["launcher_loop_basis"],
            "launcher_loop_observed": observation["launcher_loop_observed"],
            "launcher_process_stable": observation["launcher_process_stable"],
            "launcher_stability_window_s": observation[
                "launcher_stability_window_s"
            ],
            "launcher_stale_record_evidence": (
                "NOT_APPLICABLE"
                if clean_control
                else observation["launcher_stale_record_evidence"]
            ),
            "mutations_remaining": mutations,
            "normal_widget_update": observation["normal_widget_update"],
            "safe_placeholder_or_cleanup": observation[
                "safe_placeholder_or_cleanup"
            ],
            "trigger_attempt_id": attempt_id,
        }
    )
    if clean_control:
        result["control_outcome"] = classification["control_outcome"]
    bundle.write_json("run.json", state)
    bundle.write_json("result.json", result)
    _set_attempt_status(bundle, state, attempt_id, "COMPLETED")
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": phase.value,
        "evidence_term": classification["evidence_term"],
        "run_id": run_id,
    }


def _append_verification(
    result: Mapping[str, Any],
    *,
    attempt_id: str | None = None,
    current_phase: str,
    classification: Mapping[str, str] | None,
    observation: Mapping[str, Any],
    error: Exception | None = None,
) -> dict[str, Any]:
    updated = dict(result)
    verifications = list(updated.get("verifications", []))
    record: dict[str, Any] = {
        "attempt_id": attempt_id,
        "status": (
            "ERROR"
            if classification is not None and error is not None
            else "CLASSIFIED" if classification is not None else "INCONCLUSIVE"
        ),
        "classification_phase": (
            classification["phase"] if classification is not None else None
        ),
        "crash_signature_count": observation["crash_signature_count"],
        "diagnosis_status": (
            classification["diagnosis_status"] if classification is not None else None
        ),
        "evidence_term": (
            classification["evidence_term"] if classification is not None else None
        ),
        "home_rendered": observation["home_rendered"],
        "launcher_crash_exit_count": observation["launcher_crash_exit_count"],
        "launcher_crash_exit_pids": observation["launcher_crash_exit_pids"],
        "launcher_loader_record_count": observation[
            "launcher_loader_record_count"
        ],
        "launcher_loop_basis": observation["launcher_loop_basis"],
        "launcher_loop_observed": observation["launcher_loop_observed"],
        "launcher_process_stable": observation["launcher_process_stable"],
        "launcher_stale_record_evidence": observation[
            "launcher_stale_record_evidence"
        ],
        "phase_consistent": (
            classification["phase"] == current_phase
            if classification is not None
            else None
        ),
    }
    if error is not None:
        record["error"] = f"{type(error).__name__}: {error}"
    verifications.append(record)
    updated["verifications"] = verifications
    return updated


def _append_verification_error(
    result: Mapping[str, Any],
    *,
    attempt_id: str,
    current_phase: str,
    error: Exception,
) -> dict[str, Any]:
    updated = dict(result)
    verifications = list(updated.get("verifications", []))
    verifications.append(
        {
            "attempt_id": attempt_id,
            "status": "ERROR",
            "classification_phase": None,
            "current_phase": current_phase,
            "error": f"{type(error).__name__}: {error}",
            "phase_consistent": None,
        }
    )
    updated["verifications"] = verifications
    return updated


def verify(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    now: Clock | None = None,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Repeat the verdict observation without changing HOME or package state."""
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = _read_state(run_directory)
    if not state.get("capture_complete"):
        raise GateFailure("baseline capture is incomplete")
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    try:
        current_phase = Phase(state.get("current_phase"))
    except ValueError as exc:
        raise GateFailure("run has an unknown phase") from exc
    if current_phase not in {
        Phase.STALE_ARMED,
        Phase.TRIGGERED_BUG,
        Phase.TRIGGERED_FIXED,
    }:
        raise GateFailure("verify requires an armed or triggered run")
    result = _read_result(run_directory)
    precondition = result.get("precondition_status", state.get("precondition_status"))
    if precondition != "PASS":
        raise GateFailure("verify is blocked because stale precondition is not PASS")
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "verify")
    def collect_observation() -> dict[str, Any]:
        preflight_identity(
            transport,
            serial,
            expected_model,
            expected_fingerprint,
            dict(profile),
        )
        role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            "verify",
            f"role_during_{attempt_id}",
            now=now,
        )
        attempt_baseline = _capture_attempt_baseline(
            bundle=bundle,
            transport=transport,
            serial=serial,
            profile=profile,
            event_phase="verify",
            artifact_suffix=attempt_id,
            now=now,
        )
        return _observe_trigger(
            bundle=bundle,
            transport=transport,
            serial=serial,
            profile=profile,
            home_role=role,
            old_widget_id=int(state["old_widget_id"]),
            attempt_baseline=attempt_baseline,
            event_phase="verify",
            artifact_suffix=attempt_id,
            now=now,
            wait=wait,
        )

    try:
        observation = collect_observation()
    except Exception as error:
        result = _append_verification_error(
            result,
            attempt_id=attempt_id,
            current_phase=current_phase.value,
            error=error,
        )
        bundle.write_json("result.json", result)
        _set_attempt_status(bundle, state, attempt_id, "ERROR")
        raise
    try:
        classification = classify_trigger(
            precondition_status=str(precondition),
            home_rendered=bool(observation["home_rendered"]),
            launcher_process_stable=bool(observation["launcher_process_stable"]),
            crash_signature_count=int(observation["crash_signature_count"]),
            launcher_stale_record_evidence=str(
                observation["launcher_stale_record_evidence"]
            ),
            safe_placeholder_or_cleanup=bool(
                observation["safe_placeholder_or_cleanup"]
            ),
            normal_widget_update=bool(observation["normal_widget_update"]),
        )
    except GateFailure as error:
        result = _append_verification(
            result,
            attempt_id=attempt_id,
            current_phase=current_phase.value,
            classification=None,
            observation=observation,
            error=error,
        )
        bundle.write_json("result.json", result)
        _set_attempt_status(bundle, state, attempt_id, "INCONCLUSIVE")
        raise
    conflict_error = None
    if classification["phase"] != current_phase.value:
        conflict_error = GateFailure(
            "verification verdict conflicts with canonical trigger phase"
        )
    result = _append_verification(
        result,
        attempt_id=attempt_id,
        current_phase=current_phase.value,
        classification=classification,
        observation=observation,
        error=conflict_error,
    )
    bundle.write_json("result.json", result)
    if conflict_error is not None:
        _record_active_attempt_failure(run_directory, "verify", conflict_error)
        raise conflict_error
    _set_attempt_status(bundle, state, attempt_id, "COMPLETED")
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": current_phase.value,
        "evidence_term": classification["evidence_term"],
        "run_id": run_id,
    }


def restore(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    execute: bool,
    preserve_armed_state: bool = False,
    recover_package: bool = False,
    direct_home_role_recovery: bool = False,
    now: Clock | None = None,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Return to verified Simple HOME or explicitly preserve an incomplete run."""
    if not execute:
        raise GateFailure("restore/preserve requires explicit --execute approval")
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = _read_state(run_directory)
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    current_value = state.get("current_phase")
    try:
        current_phase = Phase(current_value)
    except ValueError as exc:
        raise GateFailure(f"run has unknown phase: {current_value}") from exc
    if (
        current_phase is Phase.BASELINE_CAPTURED
        and not state.get("mutations_remaining")
        and not state.get("active_attempts")
    ):
        raise GateFailure("baseline restore requires a recorded partial mutation")
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "restore")
    if preserve_armed_state:
        if current_phase not in {
            Phase.STALE_ARMED,
            Phase.TRIGGERED_BUG,
            Phase.TRIGGERED_FIXED,
        }:
            raise GateFailure("only an armed/triggered run can be preserved")
        warning = (
            "Armed state preserved; update RESUME.md before leaving this run. "
            "General HOME may trigger the Launcher crash loop."
        )
        state.update({"preserve_warning": warning, "run_complete": False})
        bundle.write_json("run.json", state)
        _set_attempt_status(bundle, state, attempt_id, "PRESERVED")
        verify_evidence_manifest(run_directory)
        return {
            "current_phase": current_phase.value,
            "preserved": True,
            "run_id": run_id,
            "warning": warning,
        }

    require_run_phase(run_directory, current_phase)
    reset_debt = any(
        isinstance(item, str) and item.startswith("launcher_data:")
        for item in state.get("mutations_remaining", [])
    )
    if (
        current_phase is Phase.RESTORED_SAFE
        and state.get("fixture_reset_status") == "FAILED"
        and reset_debt
    ):
        preflight_identity(
            transport,
            serial,
            expected_model,
            expected_fingerprint,
            dict(profile),
        )
        final_role = _verify_home_role_three_way(
            bundle,
            transport,
            serial,
            profile,
            str(profile["simple_home"]),
            "restore-reset-reconcile",
            f"{attempt_id}_failed_reset_simple",
            now=now,
        )
        _update_mutation_ledger(
            bundle,
            state,
            remove=("home_role:general", "home_role:unverified"),
            updates={
                "final_home_role": final_role,
                "fixture_reset_status": "FAILED_SAFE",
                "run_complete": False,
            },
        )
        _apply_attempt_status(state, attempt_id, "COMPLETED")
        bundle.write_json("run.json", state)
        _sync_fixture_reset_result(bundle, state)
        verify_evidence_manifest(run_directory)
        return {
            "current_phase": Phase.RESTORED_SAFE.value,
            "final_home_role": final_role,
            "fixture_reset_status": "FAILED_SAFE",
            "mutations_remaining": list(state.get("mutations_remaining", [])),
            "run_id": run_id,
        }
    package_recovery_needed = any(
        item in {"package:missing", "package:state-unverified"}
        for item in state.get("mutations_remaining", [])
    )
    apk_paths: tuple[str, ...] = ()
    if package_recovery_needed and recover_package:
        checked_inputs = verify_inputs(root, profile)
        apk_paths = _verified_apk_paths(root, profile, checked_inputs)
        bundle.write_json("inputs.json", checked_inputs)
    preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )
    retry_requires_three_way = (
        "home_role:unverified" in state.get("mutations_remaining", [])
    )

    def mark_home_switch_intent() -> None:
        _update_mutation_ledger(
            bundle,
            state,
            add=("home_role:unverified",),
        )

    if direct_home_role_recovery:
        final_role = _recover_simple_home_role_direct(
            bundle,
            transport,
            serial,
            profile,
            state,
            "restore",
            now=now,
            wait=wait,
            before_switch=mark_home_switch_intent,
            artifact_prefix=attempt_id,
        )
    else:
        final_role = _ensure_home_role(
            bundle,
            transport,
            serial,
            profile,
            str(profile["simple_home"]),
            "restore",
            now=now,
            wait=wait,
            before_switch=mark_home_switch_intent,
            artifact_prefix=attempt_id,
        )
        if retry_requires_three_way:
            final_role = _verify_home_role_three_way(
                bundle,
                transport,
                serial,
                profile,
                str(profile["simple_home"]),
                "restore",
                f"{attempt_id}_retry",
                now=now,
            )
    _update_mutation_ledger(
        bundle,
        state,
        remove=("home_role:general", "home_role:unverified"),
        updates={"final_home_role": final_role},
    )
    if package_recovery_needed:
        package = str(profile["app"]["package"])
        probe_text = _record_command(
            bundle,
            transport,
            serial,
            "restore",
            "package_recovery_probe",
            ("shell", "dumpsys", "package", package),
            now=now,
        )
        assert isinstance(probe_text, str)
        _write_raw(
            bundle.directory
            / "snapshots"
            / f"package_recovery_probe_{attempt_id}.txt",
            probe_text,
        )
        probe_state = parse_package_state(probe_text, package)
        exact_package_present = False
        try:
            _assert_package_identity(probe_state, profile["app"])
            exact_package_present = True
        except GateFailure as probe_error:
            observed_identity = any(
                value is not None
                for value in (
                    probe_state.version_name,
                    probe_state.version_code,
                    probe_state.signature_token,
                    probe_state.uid,
                )
            )
            if observed_identity:
                raise GateFailure(
                    "live package recovery probe found an unexpected identity"
                ) from probe_error
        if exact_package_present:
            _update_mutation_ledger(
                bundle,
                state,
                remove=("package:missing", "package:state-unverified"),
            )
        else:
            if not recover_package:
                raise GateFailure(
                    "package is absent; recovery install requires explicit "
                    "--recover-package approval"
                )
            install_stdout = _record_command(
                bundle,
                transport,
                serial,
                "restore",
                "install_verified_splits_recovery",
                ("install-multiple", *apk_paths),
                now=now,
            )
            if not isinstance(install_stdout, str) or "Success" not in install_stdout:
                raise GateFailure("recovery install-multiple did not report Success")
            _update_mutation_ledger(
                bundle,
                state,
                add=("package_identity:unverified",),
                remove=("package:missing", "package:state-unverified"),
            )
    ui_xml = _ui_dump(
        bundle,
        transport,
        serial,
        "restore",
        f"ui_after_{attempt_id}",
        now=now,
    )
    screenshot = _record_command(
        bundle,
        transport,
        serial,
        "restore",
        "screenshot_after_restore",
        ("exec-out", "screencap", "-p"),
        now=now,
        binary=True,
    )
    assert isinstance(screenshot, bytes)
    _write_raw(
        bundle.directory / "screenshots" / f"{attempt_id}.png", screenshot
    )
    crash_text = _record_command(
        bundle,
        transport,
        serial,
        "restore",
        "crash_after_restore",
        ("shell", "logcat", "-d", "-b", "crash", "-v", "threadtime"),
        now=now,
    )
    assert isinstance(crash_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"crash_after_{attempt_id}.txt",
        crash_text,
    )
    exit_info = _record_command(
        bundle,
        transport,
        serial,
        "restore",
        "exit_info_after_restore",
        (
            "shell", "dumpsys", "activity", "exit-info",
            str(profile["launcher_package"]),
        ),
        now=now,
    )
    assert isinstance(exit_info, str)
    _write_raw(
        bundle.directory / "snapshots" / f"exit_info_after_{attempt_id}.txt",
        exit_info,
    )
    appwidget_text = _record_command(
        bundle,
        transport,
        serial,
        "restore",
        "appwidget_after_restore",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(appwidget_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"appwidget_after_{attempt_id}.txt",
        appwidget_text,
    )
    package_text = _record_command(
        bundle,
        transport,
        serial,
        "restore",
        "package_after_restore",
        ("shell", "dumpsys", "package", str(profile["app"]["package"])),
        now=now,
    )
    assert isinstance(package_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"package_after_{attempt_id}.txt",
        package_text,
    )
    assert isinstance(ui_xml, str)
    assert isinstance(screenshot, bytes)
    assert isinstance(crash_text, str)
    assert isinstance(exit_info, str)
    assert isinstance(appwidget_text, str)
    assert isinstance(package_text, str)
    if not screenshot.startswith(b"\x89PNG\r\n\x1a\n"):
        raise GateFailure("restore screenshot is invalid")
    package_state = parse_package_state(package_text, str(profile["app"]["package"]))
    _assert_package_identity(package_state, profile["app"])
    widget_state = parse_appwidget_state(
        appwidget_text,
        str(profile["app"]["provider"]),
        str(profile["launcher_package"]),
    )
    phase = assert_transition(current_phase, "restore")
    completed = list(state.get("completed_phases", []))
    completed.append(phase.value)
    baseline_ids = {
        int(value)
        for value in state.get("baseline", {}).get("binding_ids", [])
        if isinstance(value, int) and not isinstance(value, bool)
    }
    live_added_ids = sorted(
        binding.widget_id
        for binding in widget_state.bindings
        if binding.widget_id not in baseline_ids
    )
    mutations = [
        item
        for item in state.get("mutations_remaining", [])
        if item not in {
            "home_role:general",
            "home_role:unverified",
            "package_identity:unverified",
            "widget_binding:unknown",
        }
        and not item.startswith("widget_binding:")
    ]
    for widget_id in live_added_ids:
        mutations.append(f"widget_binding:{widget_id}")
    unresolved_prefixes = (
        "home_role:",
        "package:",
        "package_identity:",
        "widget_binding:",
    )
    run_complete = not any(
        item.startswith(unresolved_prefixes) for item in mutations
    )
    state.update(
        {
            "completed_phases": completed,
            "current_phase": phase.value,
            "final_home_role": final_role,
            "last_restore_attempt_id": attempt_id,
            "mutations_remaining": mutations,
            "run_complete": run_complete,
        }
    )
    result = _read_result(run_directory)
    result.update(
        {
            "final_home_role": final_role,
            "mutations_remaining": mutations,
        }
    )
    bundle.write_json("result.json", result)
    _write_raw(
        bundle.directory / f"verification_{attempt_id}.txt",
        f"current_phase={phase.value}\nfinal_home_role={final_role}\n"
        f"mutations_remaining={','.join(mutations) if mutations else '—'}\n",
    )
    _complete_attempt_reconciliation(state, attempt_id)
    _apply_attempt_status(state, attempt_id, "COMPLETED")
    bundle.write_json("run.json", state)
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": phase.value,
        "final_home_role": final_role,
        "mutations_remaining": mutations,
        "run_id": run_id,
    }


def _reset_profile_identity(
    profile_name: str,
    profile: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "inputs": dict(inputs),
        "profile_identity": {
            "fingerprint": profile["fingerprint"],
            "incremental": profile["incremental"],
            "model": profile["model"],
            "viewport": list(profile["viewport"]),
        },
        "profile_name": profile_name,
    }


def _assert_reset_profile_compatibility(
    source_profile: Mapping[str, Any],
    next_profile: Mapping[str, Any],
) -> None:
    keys = (
        "model",
        "fingerprint",
        "incremental",
        "viewport",
        "simple_home",
        "general_home",
        "launcher_package",
        "evidence_root",
    )
    if any(source_profile.get(key) != next_profile.get(key) for key in keys):
        raise GateFailure("next profile is incompatible with the reset device/Launcher")


def _launcher_binding_records(bindings) -> list[dict[str, Any]]:
    return [
        {
            "host_package": binding.host_package,
            "provider_component": binding.provider_component,
            "remote_views_present": binding.remote_views_present,
            "widget_id": binding.widget_id,
        }
        for binding in bindings
    ]


def _sync_fixture_reset_result(
    bundle: EvidenceBundle,
    state: Mapping[str, Any],
) -> None:
    result = _read_result(bundle.directory)
    result.update(
        {
            "final_home_role": state.get("final_home_role"),
            "fixture_reset_status": state.get("fixture_reset_status"),
            "mutations_remaining": list(state.get("mutations_remaining", [])),
            "run_complete": state.get("run_complete"),
        }
    )
    bundle.write_json("result.json", result)


def _poll_launcher_host_empty(
    *,
    bundle: EvidenceBundle,
    transport,
    serial: str,
    profile: Mapping[str, Any],
    attempt_id: str,
    now: Clock | None,
    wait: Callable[[], None] | None,
    poll_attempts: int = 15,
    poll_interval_s: float = 1.0,
):
    last_bindings = ()
    for attempt in range(1, max(1, poll_attempts) + 1):
        text = _record_command(
            bundle,
            transport,
            serial,
            "reset-fixture",
            f"appwidget_after_fixture_reset_poll_{attempt}",
            ("shell", "dumpsys", "appwidget"),
            now=now,
        )
        assert isinstance(text, str)
        _write_raw(
            bundle.directory
            / "snapshots"
            / f"appwidget_after_{attempt_id}_poll_{attempt}.txt",
            text,
        )
        try:
            last_bindings = parse_launcher_host_bindings(
                text, str(profile["launcher_package"])
            )
        except ValueError as exc:
            raise GateFailure("post-reset AppWidget snapshot is incomplete") from exc
        if not last_bindings:
            return last_bindings
        if attempt < max(1, poll_attempts):
            _pause(wait, poll_interval_s)
    raise GateFailure("Launcher host bindings remain after fixture reset")


def _recover_reset_failure_to_simple(
    *,
    bundle: EvidenceBundle,
    state: dict[str, Any],
    transport,
    serial: str,
    profile: Mapping[str, Any],
    attempt_id: str,
    now: Clock | None,
    wait: Callable[[], None] | None,
) -> None:
    try:
        role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            "reset-fixture-cleanup",
            f"role_before_{attempt_id}_cleanup",
            now=now,
        )
        if role != profile["simple_home"]:
            _ensure_home_role(
                bundle,
                transport,
                serial,
                profile,
                str(profile["simple_home"]),
                "reset-fixture-cleanup",
                now=now,
                wait=wait,
                before_switch=lambda: _update_mutation_ledger(
                    bundle, state, add=("home_role:unverified",)
                ),
                artifact_prefix=f"{attempt_id}_cleanup_simple",
            )
        final_role = _verify_home_role_three_way(
            bundle,
            transport,
            serial,
            profile,
            str(profile["simple_home"]),
            "reset-fixture-cleanup",
            f"{attempt_id}_cleanup_final_simple",
            now=now,
        )
    except GateFailure as normal_error:
        live_role = _current_role(
            bundle,
            transport,
            serial,
            profile,
            "reset-fixture-cleanup",
            f"role_reprobe_{attempt_id}_cleanup",
            now=now,
        )
        if live_role == profile["simple_home"]:
            final_role = _verify_home_role_three_way(
                bundle,
                transport,
                serial,
                profile,
                str(profile["simple_home"]),
                "reset-fixture-cleanup",
                f"{attempt_id}_cleanup_reprobe_simple",
                now=now,
            )
        elif live_role == profile["general_home"]:
            final_role = _recover_simple_home_role_direct(
                bundle,
                transport,
                serial,
                profile,
                state,
                "reset-fixture-cleanup",
                now=now,
                wait=wait,
                before_switch=lambda: _update_mutation_ledger(
                    bundle, state, add=("home_role:unverified",)
                ),
                artifact_prefix=f"{attempt_id}_cleanup_direct",
            )
        else:
            raise normal_error
    _update_mutation_ledger(
        bundle,
        state,
        remove=("home_role:general", "home_role:unverified"),
        updates={
            "final_home_role": final_role,
            "fixture_reset_status": "FAILED_SAFE",
            "run_complete": False,
        },
    )
    _sync_fixture_reset_result(bundle, state)


def _complete_fixture_reset_device_sequence(
    *,
    bundle: EvidenceBundle,
    state: dict[str, Any],
    transport,
    serial: str,
    profile: Mapping[str, Any],
    attempt_id: str,
    prior_ids: list[int],
    stale_markers: tuple[str, ...],
    now: Clock | None,
    wait: Callable[[], None] | None,
):
    _ensure_home_role(
        bundle,
        transport,
        serial,
        profile,
        str(profile["general_home"]),
        "reset-fixture",
        now=now,
        wait=wait,
        before_switch=lambda: _update_mutation_ledger(
            bundle, state, add=("home_role:unverified",)
        ),
        artifact_prefix=f"{attempt_id}_general_init",
        required_source_role=str(profile["simple_home"]),
    )
    _verify_home_role_three_way(
        bundle,
        transport,
        serial,
        profile,
        str(profile["general_home"]),
        "reset-fixture",
        f"{attempt_id}_general_initialized",
        now=now,
    )
    _update_mutation_ledger(
        bundle,
        state,
        add=("home_role:general",),
        remove=("home_role:unverified",),
        updates={"final_home_role": str(profile["general_home"])},
    )
    after_bindings = _poll_launcher_host_empty(
        bundle=bundle,
        transport=transport,
        serial=serial,
        profile=profile,
        attempt_id=attempt_id,
        now=now,
        wait=wait,
    )
    after_ids = sorted({binding.widget_id for binding in after_bindings})
    if set(prior_ids).intersection(after_ids):
        raise GateFailure("prior Launcher widget IDs remain after fixture reset")
    _ensure_home_role(
        bundle,
        transport,
        serial,
        profile,
        str(profile["simple_home"]),
        "reset-fixture",
        now=now,
        wait=wait,
        before_switch=lambda: _update_mutation_ledger(
            bundle, state, add=("home_role:unverified",)
        ),
        artifact_prefix=f"{attempt_id}_return_simple",
        required_source_role=str(profile["general_home"]),
    )
    final_role = _verify_home_role_three_way(
        bundle,
        transport,
        serial,
        profile,
        str(profile["simple_home"]),
        "reset-fixture",
        f"{attempt_id}_final_simple",
        now=now,
    )
    _update_mutation_ledger(
        bundle,
        state,
        remove=(
            "home_role:general",
            "home_role:unverified",
            "launcher_data:clear-unverified",
            "launcher_data:cleared-uninitialized",
            *stale_markers,
        ),
        updates={"final_home_role": final_role},
    )
    if state.get("mutations_remaining"):
        raise GateFailure("fixture reset left unresolved mutation markers")
    return after_bindings, after_ids, final_role


def reset_fixture(
    *,
    repo_root: Path | str,
    profile: Mapping[str, Any],
    next_profile: Mapping[str, Any],
    next_profile_name: str,
    transport,
    serial: str,
    expected_model: str,
    expected_fingerprint: str,
    run_id: str,
    next_run_id: str,
    execute: bool,
    now: Clock | None = None,
    wait: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Reset Launcher storage and issue one receipt for an exact next capture."""
    if not execute:
        raise GateFailure("reset-fixture requires explicit --execute approval")
    validate_run_id(next_run_id)
    if next_run_id == run_id:
        raise GateFailure("next run ID must differ from the source run ID")
    root = Path(repo_root).resolve(strict=True)
    run_directory = _run_directory(root, profile, run_id)
    state = _read_state(run_directory)
    _assert_run_identity(
        run_directory,
        state,
        serial=serial,
        expected_model=expected_model,
        expected_fingerprint=expected_fingerprint,
        profile=profile,
    )
    if state.get("current_phase") != Phase.RESTORED_SAFE.value:
        raise GateFailure("fixture reset requires a RESTORED_SAFE source run")
    if state.get("run_complete") is not True:
        raise GateFailure("fixture reset requires a completed source run")
    if state.get("active_attempts"):
        raise GateFailure("fixture reset source has active attempts")
    if state.get("attempt_reconciliation_required"):
        raise GateFailure("fixture reset source requires attempt reconciliation")
    mutations = list(state.get("mutations_remaining", []))
    if any(
        not isinstance(item, str)
        or re.fullmatch(r"stale_launcher_record:[0-9]+", item) is None
        for item in mutations
    ):
        raise GateFailure(
            "fixture reset source has mutations other than a stale Launcher record"
        )
    if (run_directory / "fixture_reset.json").exists() or state.get("fixture_reset"):
        raise GateFailure("source run already owns a fixture-reset receipt")

    _assert_reset_profile_compatibility(profile, next_profile)
    next_inputs = verify_inputs(root, next_profile)
    next_directory = (
        root.joinpath(*Path(str(profile["evidence_root"])).parts) / next_run_id
    )
    if next_directory.exists():
        raise GateFailure("next capture run directory already exists")
    pre_reset_manifest_bytes = (
        run_directory / "evidence_sha256.txt"
    ).read_bytes()
    pre_reset_manifest_sha256 = hashlib.sha256(
        pre_reset_manifest_bytes
    ).hexdigest().upper()
    preflight_identity(
        transport,
        serial,
        expected_model,
        expected_fingerprint,
        dict(profile),
    )
    bundle = EvidenceBundle(run_directory)
    attempt_id = _reserve_attempt(bundle, state, "reset-fixture")
    _write_raw(
        bundle.directory / f"fixture_reset_pre_manifest_{attempt_id}.txt",
        pre_reset_manifest_bytes,
    )
    next_package_text = _record_command(
        bundle,
        transport,
        serial,
        "reset-fixture",
        "next_package_identity_before_fixture_reset",
        ("shell", "dumpsys", "package", str(next_profile["app"]["package"])),
        now=now,
    )
    assert isinstance(next_package_text, str)
    _write_raw(
        bundle.directory
        / "snapshots"
        / f"next_package_before_{attempt_id}.txt",
        next_package_text,
    )
    _assert_package_identity(
        parse_package_state(next_package_text, str(next_profile["app"]["package"])),
        next_profile["app"],
    )
    _verify_home_role_three_way(
        bundle,
        transport,
        serial,
        profile,
        str(profile["simple_home"]),
        "reset-fixture",
        f"{attempt_id}_source_simple",
        now=now,
    )

    before_text = _record_command(
        bundle,
        transport,
        serial,
        "reset-fixture",
        "appwidget_before_fixture_reset",
        ("shell", "dumpsys", "appwidget"),
        now=now,
    )
    assert isinstance(before_text, str)
    _write_raw(
        bundle.directory / "snapshots" / f"appwidget_before_{attempt_id}.txt",
        before_text,
    )
    try:
        before_bindings = parse_launcher_host_bindings(
            before_text, str(profile["launcher_package"])
        )
    except ValueError as exc:
        raise GateFailure("pre-reset AppWidget snapshot is incomplete") from exc
    recorded_stale_ids = {
        int(item.rsplit(":", 1)[1])
        for item in mutations
        if re.fullmatch(r"stale_launcher_record:[0-9]+", item)
    }
    old_widget_id = state.get("old_widget_id")
    if isinstance(old_widget_id, int) and not isinstance(old_widget_id, bool):
        recorded_stale_ids.add(old_widget_id)
    prior_ids = sorted(
        {binding.widget_id for binding in before_bindings} | recorded_stale_ids
    )

    _update_mutation_ledger(
        bundle,
        state,
        add=("launcher_data:clear-unverified",),
        updates={
            "fixture_reset_status": "IN_PROGRESS",
            "run_complete": False,
        },
    )
    _sync_fixture_reset_result(bundle, state)
    clear_stdout = _record_command(
        bundle,
        transport,
        serial,
        "reset-fixture",
        "clear_launcher_data",
        ("shell", "pm", "clear", str(profile["launcher_package"])),
        now=now,
    )
    if not isinstance(clear_stdout, str) or clear_stdout.strip() != "Success":
        raise GateFailure("Launcher package clear did not report exact Success")
    _update_mutation_ledger(
        bundle,
        state,
        add=("launcher_data:cleared-uninitialized",),
        remove=("launcher_data:clear-unverified",),
    )
    stale_markers = tuple(
        item for item in mutations if item.startswith("stale_launcher_record:")
    )
    after_bindings, after_ids, final_role = _run_reset_with_safety_cleanup(
        lambda: _complete_fixture_reset_device_sequence(
            bundle=bundle,
            state=state,
            transport=transport,
            serial=serial,
            profile=profile,
            attempt_id=attempt_id,
            prior_ids=prior_ids,
            stale_markers=stale_markers,
            now=now,
            wait=wait,
        ),
        lambda: _recover_reset_failure_to_simple(
            bundle=bundle,
            state=state,
            transport=transport,
            serial=serial,
            profile=profile,
            attempt_id=attempt_id,
            now=now,
            wait=wait,
        ),
    )

    receipt = {
        "final_home_role": final_role,
        "markers_remaining": [],
        "next_profile_identity": _reset_profile_identity(
            next_profile_name, next_profile, next_inputs
        ),
        "next_profile_name": next_profile_name,
        "next_run_id": next_run_id,
        "post_clear_launcher_host_bindings": _launcher_binding_records(
            after_bindings
        ),
        "post_clear_launcher_widget_ids": after_ids,
        "pre_reset_manifest_sha256": pre_reset_manifest_sha256,
        "pre_reset_manifest_snapshot": (
            f"fixture_reset_pre_manifest_{attempt_id}.txt"
        ),
        "prior_launcher_host_bindings": _launcher_binding_records(before_bindings),
        "prior_launcher_widget_ids": prior_ids,
        "reset_attempt_id": attempt_id,
        "schema_version": 1,
        "source_run_id": run_id,
        "status": "READY_FOR_CAPTURE",
    }
    bundle.write_json("fixture_reset.json", receipt)
    state.update(
        {
            "fixture_reset": {
                "attempt_id": attempt_id,
                "next_run_id": next_run_id,
                "status": "READY_FOR_CAPTURE",
            },
            "last_fixture_reset_attempt_id": attempt_id,
            "fixture_reset_status": "READY_FOR_CAPTURE",
            "run_complete": True,
        }
    )
    _apply_attempt_status(state, attempt_id, "COMPLETED")
    bundle.write_json("run.json", state)
    _sync_fixture_reset_result(bundle, state)
    verify_evidence_manifest(run_directory)
    return {
        "current_phase": Phase.RESTORED_SAFE.value,
        "next_run_id": next_run_id,
        "reset_attempt_id": attempt_id,
        "run_id": run_id,
        "status": "READY_FOR_CAPTURE",
    }


def _finalize_phase_manifest(function, *, attempt_kind: str | None = None):
    """Hold the run writer lock and verify evidence at every phase boundary."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        root = Path(kwargs["repo_root"]).resolve(strict=True)
        directory = _run_directory(root, kwargs["profile"], kwargs["run_id"])
        try:
            with exclusive_run_lock(directory):
                try:
                    verify_evidence_manifest(directory)
                except EvidenceInputError as exc:
                    raise EvidenceIntegrityFailure(
                        "run evidence integrity verification failed"
                    ) from exc
                handed_off = _read_state(directory).get("fixture_reset")
                if (
                    isinstance(handed_off, dict)
                    and handed_off.get("status") == "CONSUMED"
                ):
                    raise GateFailure("source run was handed off and is immutable")

                def finalize() -> None:
                    verify_evidence_manifest(directory)

                try:
                    result = function(*args, **kwargs)
                except BaseException as primary:
                    if isinstance(primary, EvidenceIntegrityFailure):
                        raise
                    try:
                        _record_active_attempt_failure(
                            directory, attempt_kind or function.__name__, primary
                        )
                    except Exception as attempt_record_error:
                        setattr(primary, "attempt_record_error", attempt_record_error)
                        if hasattr(primary, "add_note"):
                            primary.add_note(
                                "attempt failure recording also failed: "
                                f"{attempt_record_error}"
                            )
                    try:
                        finalize()
                    except Exception as manifest_error:
                        setattr(primary, "manifest_error", manifest_error)
                        if hasattr(primary, "add_note"):
                            primary.add_note(
                                "evidence manifest finalization also failed: "
                                f"{manifest_error}"
                            )
                    raise
                finalize()
                return result
        except RunLockError as exc:
            raise GateFailure(
                "run is already active in another process"
            ) from exc

    return wrapped


bind = _finalize_phase_manifest(bind)
arm = _finalize_phase_manifest(arm)
trigger = _finalize_phase_manifest(trigger)
verify = _finalize_phase_manifest(verify)
restore = _finalize_phase_manifest(restore)
reset_fixture = _finalize_phase_manifest(
    reset_fixture, attempt_kind="reset-fixture"
)
