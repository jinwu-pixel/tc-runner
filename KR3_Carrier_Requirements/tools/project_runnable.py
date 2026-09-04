# -*- coding: utf-8 -*-
"""STAGE2 B-6 blocker와 capability 진단을 분리해 사전 투영한다.

실제 STAGE2 컴파일은 아니다. ``runnable_reason``에는 현재 CTF만으로 확정 가능한
schema 합법 B-6 사유 3종만 넣는다. multi-device/external/unsupported 신호는
capability 진단으로 보존하되 runnable 판정을 바꾸지 않는다.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml


TOOLS_DIR = Path(__file__).resolve().parent
TRACK_DIR = TOOLS_DIR.parent
REPO_ROOT = TRACK_DIR.parent
DEFAULT_STAGE1 = TRACK_DIR / "stage1"
DEFAULT_CAPABILITY = REPO_ROOT / "tc_prompts" / "runner_capability.yaml"


class ProjectionInputError(ValueError):
    pass


def project_document(document: dict, *, multi_device: bool) -> dict:
    steps = document.get("procedure_steps") or []
    reasons: list[str] = []
    diagnostics: list[str] = []

    infeasible_count = sum(
        1
        for step in steps
        for expected in (step.get("expected") or [])
        if expected.get("feasibility") == "infeasible"
    )
    if infeasible_count:
        reasons.append("INFEASIBLE_VERIFIER")

    fixtures = [
        precondition
        for precondition in (document.get("preconditions") or [])
        if precondition.get("implicit_fixture_suspected")
        and precondition.get("blocking")
    ]
    if fixtures:
        reasons.append("FIXTURE_REQUIRED")

    has_mutation = any(
        (step.get("normalized_intent") or {}).get("mutation_risk") is True
        for step in steps
    )
    has_teardown = any(
        (step.get("execution_candidate") or {}).get("role") == "TEARDOWN"
        for step in steps
    )
    if has_mutation and not has_teardown:
        reasons.append("MUTATION_UNMANAGED")

    flags = {flag.get("flag") for flag in (document.get("risk_flags") or [])}
    if "MULTI_DEVICE" in flags and not multi_device:
        diagnostics.append("MULTI_DEVICE_UNSUPPORTED")
    modes = Counter(
        (step.get("execution_candidate") or {}).get("mode") for step in steps
    )
    if modes.get("EXTERNAL_EVENT"):
        diagnostics.append("EXTERNAL_EVENT")
    if modes.get("UNSUPPORTED"):
        diagnostics.append("UNSUPPORTED_STEP")

    return {
        "tc_id": document["tc_id"],
        "tc_class": (document.get("automation_summary") or {}).get("tc_class", "—"),
        "runnable_reasons": sorted(set(reasons)),
        "diagnostics": sorted(set(diagnostics)),
    }


def load_projection(stage1_dir: Path, capability_path: Path) -> tuple[list[dict], dict]:
    if not stage1_dir.is_dir():
        raise ProjectionInputError(f"STAGE1 디렉토리 없음: {stage1_dir}")
    files = sorted(stage1_dir.glob("*_canonical.yaml"))
    if not files:
        raise ProjectionInputError(f"CTF 입력 0건: {stage1_dir}")
    if not capability_path.is_file():
        raise ProjectionInputError(f"runner capability 없음: {capability_path}")

    capability = yaml.safe_load(capability_path.read_text(encoding="utf-8")) or {}
    rows = [
        project_document(
            yaml.safe_load(path.read_text(encoding="utf-8")) or {},
            multi_device=bool(capability.get("multi_device")),
        )
        for path in files
    ]
    return rows, capability


def render_projection(rows: list[dict], capability: dict) -> None:
    print(
        "%-42s %-16s %-52s %s"
        % ("tc_id", "tc_class", "runnable_reason (투영)", "diagnostics")
    )
    for row in rows:
        reasons = row["runnable_reasons"]
        diagnostics = row["diagnostics"]
        print(
            "%-42s %-16s %-52s %s"
            % (
                row["tc_id"],
                row["tc_class"],
                ", ".join(reasons) if reasons else "— (runnable 후보)",
                ", ".join(diagnostics) if diagnostics else "—",
            )
        )

    runnable = [row for row in rows if not row["runnable_reasons"]]
    print("\n투영 결과: runnable:true 후보 %d / %d" % (len(runnable), len(rows)))

    blocker_counts = Counter(
        reason for row in rows for reason in row["runnable_reasons"]
    )
    print("\nrunnable 차단 사유별 건수:")
    if blocker_counts:
        for key, value in blocker_counts.most_common():
            print("  %-26s %d" % (key, value))
    else:
        print("  —")

    diagnostic_counts = Counter(
        diagnostic for row in rows for diagnostic in row["diagnostics"]
    )
    print("\ncapability 진단별 건수 (runnable 비차단):")
    if diagnostic_counts:
        for key, value in diagnostic_counts.most_common():
            print("  %-26s %d" % (key, value))
    else:
        print("  —")

    print("\n러너 capability 참조:")
    print("  runner_version      :", capability.get("runner_version"))
    print("  multi_device        :", capability.get("multi_device"))
    print("  supported_actions   :", len(capability.get("supported_actions") or []))
    print(
        "  shell_actions       :",
        ", ".join(capability.get("shell_actions_available") or []),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1)
    parser.add_argument("--capability", type=Path, default=DEFAULT_CAPABILITY)
    args = parser.parse_args(argv)

    try:
        rows, capability = load_projection(args.stage1, args.capability)
    except (ProjectionInputError, OSError, KeyError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    render_projection(rows, capability)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
