#!/usr/bin/env python3
"""TC YAML 스키마 검증기.

사용법:
    python validate_tc.py DEMO_01.yaml
    python validate_tc.py exported/*.yaml          # 여러 파일 일괄 검증
    python validate_tc.py --dir golden_tc_set/     # 디렉토리 내 전체 검증

변환 파이프라인에서의 위치:
    원본 TC → 클로드코드 변환 → [이 스크립트로 검증] → tc_loader 로드 → 실행
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.execution_contract import (
    NormalizationResult,
    normalize_step,
    normalize_tc,
    validate_canonical_tc,
)

SCHEMA_PATH = Path(__file__).parent / "tc_step_schema.json"

# ─── PR 1 lint 상수 ───
LINT_TOOL_VERSION = "pr1-lint-v1"
LINT_SCHEMA_VERSION = 1
LINT_RULE_IDS = {"TAP_XY_USED", "LONG_FIXED_WAIT", "WEAK_VERIFY_TEXT"}
LONG_WAIT_THRESHOLD_SECONDS = 10
WEAK_VERIFY_MAX_LENGTH = 2


# ─── 경량 검증기 (jsonschema 의존성 없이 동작) ───

def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalization_errors(result: NormalizationResult) -> list[str]:
    return [
        f"{finding.code} [{finding.path}]: {finding.detail}"
        for finding in result.findings
        if finding.severity == "ERROR"
    ]


def validate_tc(tc: dict, schema: dict) -> list[str]:
    """Raw TC를 한 번 정규화한 뒤 위반 사항 목록 반환. 빈 리스트 = 통과."""
    source = str(tc.get("tc_name") or tc.get("name") or "<memory>")
    normalized = normalize_tc(tc, source=source)
    return _normalization_errors(normalized) + validate_canonical_tc(
        normalized.value, schema
    )


# ─── PR 1 lint 엔진 ───

def _normalize_wait_seconds(step: dict):
    """wait step의 대기 시간을 초 단위로 normalize.

    canonical contract와 동일하게 seconds alias를 정확한 duration(ms)로
    변환한다. canonical/alias 충돌 또는 단위 변환 실패 시 None을 반환한다.
    기존 direct helper 호출은 action 없는 부분 step도 허용한다.
    """
    wait_step = {"action": "wait", **step}
    normalized = normalize_step(wait_step, path="wait")
    if normalized.blocking:
        return None
    if "duration" in normalized.value:
        try:
            return float(normalized.value["duration"]) / 1000.0
        except (TypeError, ValueError):
            return None
    return None


def _canonical_wait_seconds(step: dict):
    """Read duration(ms) from an already-normalized wait step."""
    if "duration" not in step:
        return None
    try:
        return float(step["duration"]) / 1000.0
    except (TypeError, ValueError):
        return None


def _make_finding(rule_id, level, tc_path, tc_id, step_index, action,
                  message, suggested_fix, evidence, suppressed):
    return {
        "rule_id": rule_id,
        "level": level,
        "tc_path": str(tc_path),
        "tc_id": tc_id,
        "step_index": step_index,
        "action": action,
        "message": message,
        "suggested_fix": suggested_fix,
        "evidence": dict(evidence),
        "suppressed": bool(suppressed),
    }


def validate_lint_dsl_fields(tc: dict) -> list[str]:
    """TC의 lint 관련 DSL 필드를 검증. lint finding 생성과 분리된 단일 source-of-truth.

    invalid lint_allow rule_id 등 TC DSL 오류를 errors 리스트로 반환.

    중요: 본 함수는 --no-lint 옵션과 무관하게 항상 호출되어야 한다.
    invalid lint_allow는 lint 경고가 아니라 TC DSL 오류이므로,
    lint finding 생성을 끄더라도 DSL 검증은 끄지 않는다.
    """
    errors: list[str] = []
    steps = tc.get("steps", [])
    for i, step in enumerate(steps):
        lint_allow = step.get("lint_allow") or []
        for rid in lint_allow:
            if rid not in LINT_RULE_IDS:
                errors.append(
                    f"steps[{i}]: lint_allow에 미허용 rule_id '{rid}' "
                    f"(허용: {sorted(LINT_RULE_IDS)})"
                )
    return errors


def lint_tc(tc: dict, tc_path, tc_id: str) -> tuple[list[dict], list[str]]:
    """Raw TC를 canonical view로 정규화한 뒤 lint."""
    normalized = normalize_tc(tc, source=str(tc_path))
    return _lint_normalized_tc(normalized.value, tc_path, tc_id)


def _lint_normalized_tc(
    tc: dict, tc_path, tc_id: str
) -> tuple[list[dict], list[str]]:
    """TC를 lint하여 (findings, lint_dsl_errors) 반환.

    PR 1 lint 룰:
    - TAP_XY_USED (INFO): tap_xy 액션 사용
    - LONG_FIXED_WAIT (WARN): wait normalized seconds >= 10
    - WEAK_VERIFY_TEXT (WARN): verify_text normalized text/target 길이 <= 2 (verify_gone 제외)

    suppression 정책:
    - lint_allow에 rule_id가 있으면 해당 finding은 suppressed=true (sidecar에는 보존)
    - wait_intent='timer_modeling'은 LONG_FIXED_WAIT suppression 근거
    - selector_fallback_reason은 TAP_XY_USED finding의 evidence (suppression 근거 아님)

    DSL 오류:
    - validate_lint_dsl_fields()에 위임 (단일 source-of-truth).
      --no-lint 상태에서도 main()이 직접 validate_lint_dsl_fields()를 호출하므로
      invalid lint_allow는 lint 비활성 여부와 무관하게 항상 잡힌다.
    """
    findings: list[dict] = []
    dsl_errors = validate_lint_dsl_fields(tc)
    steps = tc.get("steps", [])

    for i, step in enumerate(steps):
        action = step.get("action")
        lint_allow = step.get("lint_allow") or []

        if action == "tap_xy":
            evidence: dict = {}
            sfr = step.get("selector_fallback_reason")
            if sfr:
                evidence["selector_fallback_reason"] = sfr
            findings.append(_make_finding(
                rule_id="TAP_XY_USED",
                level="INFO",
                tc_path=tc_path,
                tc_id=tc_id,
                step_index=i,
                action=action,
                message=f"tap_xy used at ({step.get('x')}, {step.get('y')})",
                suggested_fix="가능하면 tap_text 또는 tap_id 사용. 좌표 사용이 필수면 selector_fallback_reason 명시",
                evidence=evidence,
                suppressed=("TAP_XY_USED" in lint_allow),
            ))

        elif action == "wait":
            seconds = _canonical_wait_seconds(step)
            if seconds is not None and seconds >= LONG_WAIT_THRESHOLD_SECONDS:
                wait_intent = step.get("wait_intent")
                evidence = {"normalized_seconds": seconds}
                if wait_intent:
                    evidence["wait_intent"] = wait_intent
                suppressed = (
                    wait_intent == "timer_modeling"
                    or "LONG_FIXED_WAIT" in lint_allow
                )
                findings.append(_make_finding(
                    rule_id="LONG_FIXED_WAIT",
                    level="WARN",
                    tc_path=tc_path,
                    tc_id=tc_id,
                    step_index=i,
                    action=action,
                    message=f"fixed wait of {seconds}s (>= {LONG_WAIT_THRESHOLD_SECONDS}s)",
                    suggested_fix="가능하면 verify_text/verify_shell polling으로 대체. SUT 타이머 모델링이 필요하면 wait_intent: timer_modeling 명시",
                    evidence=evidence,
                    suppressed=suppressed,
                ))

        elif action == "verify_text":
            # WEAK_VERIFY_TEXT은 positive text assertion의 약함을 잡는 룰.
            # verify_gone은 negative assertion이라 짧은 target도 정상 케이스가 될 수 있어 PR 1 범위에서 제외.
            value = step.get("target") or step.get("text") or ""
            normalized = value.strip() if isinstance(value, str) else ""
            if 0 < len(normalized) <= WEAK_VERIFY_MAX_LENGTH:
                evidence = {"normalized_text": normalized, "length": len(normalized)}
                findings.append(_make_finding(
                    rule_id="WEAK_VERIFY_TEXT",
                    level="WARN",
                    tc_path=tc_path,
                    tc_id=tc_id,
                    step_index=i,
                    action=action,
                    message=f"verify text too short: '{normalized}' (length={len(normalized)})",
                    suggested_fix=f"식별력 있는 문구로 교체(>{WEAK_VERIFY_MAX_LENGTH}자) 또는 verify_shell + dumpsys 등 대체 검증",
                    evidence=evidence,
                    suppressed=("WEAK_VERIFY_TEXT" in lint_allow),
                ))

    return findings, dsl_errors


def build_sidecar(findings: list[dict], scan_scope: dict, run_id: str) -> dict:
    """findings 리스트를 lint sidecar dict로 빌드.

    summary는 suppressed=False finding만 카운트.
    findings[]에는 suppressed=True 포함 전체 보존 (evidence accumulation).

    scan_scope는 object 형태:
    - target_paths: list[str]  (스캔 시도 경로 전체)
    - tc_count: int            (성공 파싱된 TC 수)
    - step_count: int          (성공 파싱된 TC들의 step 합)
    """
    by_rule: dict[str, int] = {}
    total_infos = 0
    total_warnings = 0
    for f in findings:
        if f.get("suppressed"):
            continue
        rid = f["rule_id"]
        by_rule[rid] = by_rule.get(rid, 0) + 1
        if f["level"] == "INFO":
            total_infos += 1
        elif f["level"] == "WARN":
            total_warnings += 1

    return {
        "schema_version": LINT_SCHEMA_VERSION,
        "tool_version": LINT_TOOL_VERSION,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_scope": dict(scan_scope),
        "summary": {
            "total_infos": total_infos,
            "total_warnings": total_warnings,
            "by_rule": by_rule,
        },
        "findings": list(findings),
    }


def write_sidecar(sidecar: dict, run_id: str, out_dir=None) -> Path:
    """sidecar dict를 reports/lint/<run_id>.json (또는 out_dir/<run_id>.json)에 기록."""
    if out_dir is None:
        out_dir = Path("reports/lint")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2)
    return out_path


def validate_file(path: Path, schema: dict) -> tuple[str, list[str]]:
    """파일 하나를 검증하고 (파일명, 에러목록) 반환."""
    try:
        with open(path, encoding="utf-8") as f:
            tc = yaml.safe_load(f)
    except Exception as e:
        return (str(path), [f"YAML 파싱 실패: {e}"])

    if not isinstance(tc, dict):
        return (str(path), ["최상위가 dict가 아님"])

    return (str(path), validate_tc(tc, schema))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="TC YAML 스키마 검증기 + lint")
    parser.add_argument("files", nargs="*", help="검증할 YAML 파일들")
    parser.add_argument("--dir", help="디렉토리 내 *.yaml 전체 검증")
    parser.add_argument("--no-lint", action="store_true",
                        help="lint 비활성화 및 sidecar 미생성")
    parser.add_argument("--run-id",
                        help="lint sidecar run_id (기본: 현재 UTC 타임스탬프)")
    args = parser.parse_args()

    paths: list[Path] = []
    if args.dir:
        paths.extend(Path(args.dir).glob("*.yaml"))
    for f in args.files or []:
        p = Path(f)
        if p.is_dir():
            paths.extend(p.glob("*.yaml"))
        else:
            paths.append(p)

    if not paths:
        print("검증할 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    schema = load_schema()
    total = 0
    failed = 0
    all_findings: list[dict] = []
    scan_scope: dict = {
        "target_paths": [],
        "tc_count": 0,
        "step_count": 0,
    }

    for path in sorted(paths):
        total += 1
        scan_scope["target_paths"].append(str(path))

        try:
            with open(path, encoding="utf-8") as f:
                tc = yaml.safe_load(f)
        except Exception as e:
            failed += 1
            print(f"\n✗ FAIL  {path}")
            print(f"    → YAML 파싱 실패: {e}")
            continue

        if not isinstance(tc, dict):
            failed += 1
            print(f"\n✗ FAIL  {path}")
            print(f"    → 최상위가 dict가 아님")
            continue

        scan_scope["tc_count"] += 1
        scan_scope["step_count"] += len(tc.get("steps", []) or [])

        normalized = normalize_tc(tc, source=str(path))
        canonical_tc = normalized.value
        errors = _normalization_errors(normalized) + validate_canonical_tc(
            canonical_tc, schema
        )
        # lint_allow DSL 검증은 --no-lint 와 무관하게 항상 수행.
        # invalid lint_allow는 lint 경고가 아니라 TC DSL 오류이므로 validate FAIL로 합산.
        lint_dsl_errors = validate_lint_dsl_fields(canonical_tc)
        if not args.no_lint:
            findings, _ = _lint_normalized_tc(
                canonical_tc, path, canonical_tc.get("tc_name", "")
            )
            all_findings.extend(findings)

        all_errors = errors + lint_dsl_errors
        if all_errors:
            failed += 1
            print(f"\n✗ FAIL  {path}")
            for e in all_errors:
                print(f"    → {e}")
        else:
            print(f"✓ PASS  {path}")

    # lint sidecar 생성 (validate FAIL과 독립)
    if not args.no_lint:
        run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sidecar = build_sidecar(all_findings, scan_scope, run_id)
        out_path = write_sidecar(sidecar, run_id)
        print(f"\nlint sidecar: {out_path}")
        print(f"  INFO (unsuppressed): {sidecar['summary']['total_infos']}")
        print(f"  WARN (unsuppressed): {sidecar['summary']['total_warnings']}")

    print(f"\n{'─' * 40}")
    print(f"총 {total}건 검증, {total - failed}건 통과, {failed}건 실패")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
