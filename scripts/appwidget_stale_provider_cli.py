"""Command-line interface for the AppWidget stale-provider harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from appwidget_stale_provider_orchestrator import (
    GateFailure,
    arm,
    bind,
    capture,
    reset_fixture,
    restore,
    trigger,
    verify,
)
from appwidget_stale_provider_profiles import PROFILES
from appwidget_stale_provider_transport import AdbTransport


COMMANDS = (
    "plan", "capture", "bind", "arm", "trigger", "verify", "restore",
    "reset-fixture",
)
MUTATING_COMMANDS = frozenset(
    {"bind", "arm", "trigger", "restore", "reset-fixture"}
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def render_plan(profile_name: str, profile: dict[str, Any]) -> dict[str, Any]:
    phases = []
    for command in COMMANDS:
        if command == "plan":
            continue
        phase = {
            "command": command,
            "mutating": command in MUTATING_COMMANDS,
            "requires_approval": command in MUTATING_COMMANDS,
            "requires_execute": command in MUTATING_COMMANDS,
        }
        if command == "restore":
            phase["conditional_actions"] = [
                {
                    "action": "install-multiple",
                    "condition": "interrupted lifecycle left the exact package absent",
                    "requires_flag": "--recover-package",
                },
                {
                    "action": "cmd role add-role-holder",
                    "condition": "verified General HOME crash loop blocks UI restore",
                    "requires_flag": "--direct-home-role-recovery",
                },
            ]
        phases.append(phase)
    return {
        "adb": "OFF",
        "profile": profile_name,
        "identity": {
            "model": profile["model"],
            "fingerprint": profile["fingerprint"],
            "viewport": list(profile["viewport"]),
        },
        "source_manifest_sha256": profile["app"]["source_manifest_sha256"],
        "phases": phases,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appwidget_stale_provider_repro.py",
        description="Fail-closed BUG27084 AppWidget stale-provider harness",
    )
    parser.add_argument("command", nargs="?", default="plan", choices=COMMANDS)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--serial")
    parser.add_argument("--expected-model")
    parser.add_argument("--expected-fingerprint")
    parser.add_argument("--run-id")
    parser.add_argument("--next-profile")
    parser.add_argument("--next-run-id")
    parser.add_argument("--after-reset-run-id")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help=(
            "with bind --execute, adopt one exact binding already pinned by the "
            "capture baseline instead of placing another widget"
        ),
    )
    parser.add_argument(
        "--lifecycle",
        choices=(
            "uninstall-reinstall",
            "remove-widget-uninstall-reinstall",
            "clear-force-stop-reboot",
        ),
    )
    parser.add_argument("--preserve-armed-state", action="store_true")
    parser.add_argument(
        "--recover-package",
        action="store_true",
        help=(
            "with restore --execute, explicitly approve install-multiple only when "
            "a live exact-package probe proves the interrupted lifecycle left it absent"
        ),
    )
    parser.add_argument(
        "--direct-home-role-recovery",
        action="store_true",
        help=(
            "with restore --execute, explicitly approve exact HOME role recovery "
            "when the verified Launcher crash dialog blocks UI mode switching"
        ),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _format_exception(exc: Exception, state: dict[str, Any] | None = None) -> str:
    parts = [f"{type(exc).__name__}: {exc}"]
    for attribute in ("cleanup_error", "attempt_record_error", "manifest_error"):
        secondary = getattr(exc, attribute, None)
        if secondary is not None:
            parts.append(
                f"{attribute}={type(secondary).__name__}: {secondary}"
            )
    if state is not None:
        parts.append(f"current_role={state.get('final_home_role', '—')}")
        mutations = state.get("mutations_remaining", [])
        parts.append(
            "mutations_remaining="
            + (",".join(str(item) for item in mutations) if mutations else "—")
        )
    return "; ".join(parts)


def _emit(payload: dict[str, Any]) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    profile = PROFILES.get(args.profile)
    if profile is None:
        return _error(f"unknown profile: {args.profile}")
    if args.command == "plan":
        _emit(render_plan(args.profile, profile))
        return 0

    required = {
        "--serial": args.serial,
        "--expected-model": args.expected_model,
        "--expected-fingerprint": args.expected_fingerprint,
    }
    if args.command != "capture":
        required["--run-id"] = args.run_id
    if args.command == "reset-fixture":
        required["--next-profile"] = args.next_profile
        required["--next-run-id"] = args.next_run_id
    if args.command == "capture" and args.after_reset_run_id:
        required["--run-id"] = args.run_id
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        return _error("missing required arguments: " + ", ".join(missing))
    if args.command in MUTATING_COMMANDS and not args.execute:
        return _error(f"{args.command} requires explicit --execute approval")
    if args.command == "arm" and args.lifecycle is None:
        return _error("arm requires --lifecycle")
    if args.preserve_armed_state and args.command != "restore":
        return _error("--preserve-armed-state is valid only with restore")
    if args.recover_package and args.command != "restore":
        return _error("--recover-package is valid only with restore")
    if args.direct_home_role_recovery and args.command != "restore":
        return _error("--direct-home-role-recovery is valid only with restore")
    if args.adopt_existing and args.command != "bind":
        return _error("--adopt-existing is valid only with bind")
    if (args.next_profile or args.next_run_id) and args.command != "reset-fixture":
        return _error("--next-profile/--next-run-id are valid only with reset-fixture")
    if args.after_reset_run_id and args.command != "capture":
        return _error("--after-reset-run-id is valid only with capture")
    next_profile = None
    if args.command == "reset-fixture":
        next_profile = PROFILES.get(str(args.next_profile))
        if next_profile is None:
            return _error(f"unknown next profile: {args.next_profile}")

    transport = AdbTransport(str(args.serial))
    common = {
        "repo_root": REPO_ROOT,
        "profile": profile,
        "transport": transport,
        "serial": str(args.serial),
        "expected_model": str(args.expected_model),
        "expected_fingerprint": str(args.expected_fingerprint),
    }
    try:
        if args.command == "capture":
            payload = capture(
                **common,
                run_id=args.run_id,
                profile_name=args.profile,
                after_reset_run_id=args.after_reset_run_id,
            )
        elif args.command == "bind":
            payload = bind(
                **common,
                run_id=args.run_id,
                execute=args.execute,
                adopt_existing=args.adopt_existing,
            )
        elif args.command == "arm":
            payload = arm(
                **common,
                run_id=args.run_id,
                lifecycle=args.lifecycle,
                execute=args.execute,
            )
        elif args.command == "trigger":
            payload = trigger(**common, run_id=args.run_id, execute=args.execute)
        elif args.command == "verify":
            payload = verify(**common, run_id=args.run_id)
        elif args.command == "restore":
            payload = restore(
                **common,
                run_id=args.run_id,
                execute=args.execute,
                preserve_armed_state=args.preserve_armed_state,
                recover_package=args.recover_package,
                direct_home_role_recovery=args.direct_home_role_recovery,
            )
        else:
            assert next_profile is not None
            payload = reset_fixture(
                **common,
                run_id=args.run_id,
                next_profile=next_profile,
                next_profile_name=str(args.next_profile),
                next_run_id=str(args.next_run_id),
                execute=args.execute,
            )
    except (GateFailure, ValueError, OSError, RuntimeError) as exc:
        state = None
        if args.run_id:
            state_path = (
                Path(common["repo_root"])
                / str(profile["evidence_root"])
                / str(args.run_id)
                / "run.json"
            )
            try:
                candidate = json.loads(state_path.read_text(encoding="utf-8"))
                state = candidate if isinstance(candidate, dict) else None
            except (OSError, json.JSONDecodeError):
                pass
        return _error(_format_exception(exc, state))
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
