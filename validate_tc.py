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


def validate_tc(tc: dict, schema: dict) -> list[str]:
    """TC dict를 스키마와 대조하여 위반 사항 목록 반환. 빈 리스트 = 통과."""
    errors: list[str] = []

    # 1. 필수 최상위 필드
    for field in schema.get("required", []):
        if field not in tc:
            errors.append(f"필수 필드 누락: '{field}'")

    # 2. tc_name 형식
    tc_name = tc.get("tc_name", "")
    if tc_name:
        import re
        pattern = schema["properties"]["tc_name"].get("pattern", "")
        if pattern and not re.match(pattern, tc_name):
            errors.append(f"tc_name 형식 불일치: '{tc_name}' (허용: 영문/숫자/_/-)")

    # 3. metadata 검증
    meta = tc.get("metadata", {})
    meta_schema = schema["properties"]["metadata"]
    for field in meta_schema.get("required", []):
        if field not in meta:
            errors.append(f"metadata 필수 필드 누락: '{field}'")

    tc_class = meta.get("tc_class", "")
    valid_classes = meta_schema["properties"]["tc_class"]["enum"]
    if tc_class and tc_class not in valid_classes:
        errors.append(f"tc_class 값 불일치: '{tc_class}' (허용: {valid_classes})")

    # 3-b. execution_type / manual_detail 검증
    VALID_EXEC_TYPES = {"AUTO", "MANUAL_LOCAL", "EXTERNAL_EVENT"}
    VALID_DETAIL_TOKENS = {
        "NONE", "CALL_RECEIVE", "CALL_PLACE", "APP_INSTALL",
        "BUTTON_TOUCH", "PHYSICAL_ACTION", "PAIRING",
        "MULTI_DEVICE", "SERVER_CALLBACK", "UNKNOWN",
    }

    exec_type = meta.get("execution_type")
    manual_detail = meta.get("manual_detail")

    if exec_type is None:
        errors.append("metadata 필수 필드 누락: 'execution_type'")
    elif exec_type not in VALID_EXEC_TYPES:
        errors.append(f"execution_type 값 불일치: '{exec_type}' (허용: {sorted(VALID_EXEC_TYPES)})")

    if manual_detail is None:
        errors.append("metadata 필수 필드 누락: 'manual_detail'")
    else:
        detail_str = str(manual_detail)
        tokens = detail_str.split("|")
        for token in tokens:
            if token not in VALID_DETAIL_TOKENS:
                errors.append(f"manual_detail 토큰 불일치: '{token}' (허용: {sorted(VALID_DETAIL_TOKENS)})")

    # 3-c. execution_type / manual_detail / has_manual_steps 상호 일관성
    if exec_type and manual_detail is not None:
        detail_str = str(manual_detail)
        if exec_type == "AUTO" and detail_str != "NONE":
            errors.append(f"일관성 오류: execution_type=AUTO 이면 manual_detail='NONE' 이어야 함 (현재: '{detail_str}')")
        if exec_type != "AUTO" and detail_str == "NONE":
            errors.append(f"일관성 오류: execution_type={exec_type} 이면 manual_detail='NONE' 이 아니어야 함")

    has_manual = meta.get("has_manual_steps")
    if exec_type and has_manual is not None:
        if exec_type == "AUTO" and has_manual is True:
            errors.append("일관성 오류: execution_type=AUTO 이면 has_manual_steps=false 이어야 함")
        if exec_type in ("MANUAL_LOCAL", "EXTERNAL_EVENT") and has_manual is False:
            errors.append(f"일관성 오류: execution_type={exec_type} 이면 has_manual_steps=true 이어야 함")

    # 3-d. execution_type vs step-level 정합성 (파생 계산 검증)
    steps = tc.get("steps", [])
    has_external_step = any(
        s.get("execution_mode") == "EXTERNAL_EVENT" for s in steps
    )
    has_manual_step = any(
        s.get("action") == "manual_pause" or s.get("execution_mode") == "MANUAL_REQUIRED"
        for s in steps
    )

    if exec_type:
        expected_exec_type = "AUTO"
        if has_manual_step:
            expected_exec_type = "MANUAL_LOCAL"
        if has_external_step:
            expected_exec_type = "EXTERNAL_EVENT"

        if exec_type != expected_exec_type:
            errors.append(
                f"일관성 오류: step 분석 결과 execution_type='{expected_exec_type}' "
                f"이어야 하나, metadata에 '{exec_type}' 으로 설정됨"
            )

    # 3-e. runnable_reason 정합 (B-6 — STAGE1 신호 소비 기록의 내부 정합만 감사)
    #   runnable_reason이 존재할 때만 검사 → legacy TC(필드 없음)는 무영향(backward-compat).
    #   validate는 CTF/fixture 입력이 없어 게이트를 재도출하지 못한다 — STAGE2가 판정 producer,
    #   본 가드는 기록된 사유가 runnable=false와 정합하고 enum에 속하는지만 확인한다.
    VALID_RUNNABLE_REASONS = {
        "FIXTURE_REQUIRED", "MUTATION_UNMANAGED", "INFEASIBLE_VERIFIER",
        "UNRESOLVED_PARAMS", "MANUAL_FALLBACK",
    }
    runnable_reason = meta.get("runnable_reason")
    if runnable_reason is not None:
        if not isinstance(runnable_reason, list):
            errors.append(
                f"runnable_reason 형식 오류: 배열이어야 함 (현재: {type(runnable_reason).__name__})"
            )
        else:
            for reason in runnable_reason:
                if reason not in VALID_RUNNABLE_REASONS:
                    errors.append(
                        f"runnable_reason 토큰 불일치: '{reason}' "
                        f"(허용: {sorted(VALID_RUNNABLE_REASONS)})"
                    )
            if runnable_reason and meta.get("runnable") is True:
                errors.append(
                    "일관성 오류: runnable_reason이 비어있지 않으면 runnable=false "
                    "이어야 함 (현재 runnable=True)"
                )

    # 4. steps 검증
    steps = tc.get("steps", [])
    if not steps:
        errors.append("steps가 비어 있음")

    step_schema = schema["$defs"]["step"]
    valid_actions = step_schema["properties"]["action"]["enum"]
    valid_modes = step_schema["properties"]["execution_mode"]["enum"]
    valid_roles = step_schema["properties"]["step_role"]["enum"]

    # action별 필수 필드 매핑 (allOf/if-then에서 추출)
    action_required: dict[str, list[str]] = {}
    for rule in step_schema.get("allOf", []):
        action_val = rule.get("if", {}).get("properties", {}).get("action", {}).get("const")
        req_fields = rule.get("then", {}).get("required", [])
        if action_val:
            action_required[action_val] = req_fields

    for i, step in enumerate(steps):
        prefix = f"steps[{i}]"

        action = step.get("action")
        if not action:
            errors.append(f"{prefix}: 'action' 누락")
            continue

        if action not in valid_actions:
            errors.append(f"{prefix}: 미지원 action '{action}' (허용: {valid_actions})")
            continue

        # execution_mode 검증
        mode = step.get("execution_mode")
        if mode and mode not in valid_modes:
            errors.append(f"{prefix}: 미지원 execution_mode '{mode}'")

        # step_role 검증
        role = step.get("step_role")
        if role and role not in valid_roles:
            errors.append(f"{prefix}: 미지원 step_role '{role}'")

        # action별 필수 필드 검증
        for field in action_required.get(action, []):
            if field == "action":
                continue
            if field not in step or not step[field]:
                errors.append(f"{prefix}: action='{action}'에 필수 필드 '{field}' 누락")

        # manual_pause 특수 검증
        if action == "manual_pause":
            if not step.get("description"):
                errors.append(f"{prefix}: manual_pause에 description 누락 (작업자 지시 필수)")
            on_timeout = step.get("on_timeout")
            if on_timeout and on_timeout not in ["fail", "skip", "warn"]:
                errors.append(f"{prefix}: on_timeout '{on_timeout}' 불일치 (허용: fail/skip/warn)")

        # shell placeholder 잔존 검증
        if action in ("shell", "verify_shell"):
            cmd = step.get("command", "")
            if "{" in cmd and "}" in cmd:
                errors.append(f"{prefix}: command에 미해결 placeholder 잔존: '{cmd}'")

    return errors


# ─── PR 1 lint 엔진 ───

def _normalize_wait_seconds(step: dict):
    """wait step의 대기 시간을 초 단위로 normalize.

    action_runner._wait()와 동일한 단위 해석:
    - seconds 필드 우선 (초 단위)
    - duration 필드 fallback (밀리초 단위)
    둘 다 없거나 변환 실패 시 None 반환.
    """
    if "seconds" in step:
        try:
            return float(step["seconds"])
        except (TypeError, ValueError):
            return None
    if "duration" in step:
        try:
            return float(step["duration"]) / 1000.0
        except (TypeError, ValueError):
            return None
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
            seconds = _normalize_wait_seconds(step)
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

        errors = validate_tc(tc, schema)
        # lint_allow DSL 검증은 --no-lint 와 무관하게 항상 수행.
        # invalid lint_allow는 lint 경고가 아니라 TC DSL 오류이므로 validate FAIL로 합산.
        lint_dsl_errors = validate_lint_dsl_fields(tc)
        if not args.no_lint:
            findings, _ = lint_tc(tc, path, tc.get("tc_name", ""))
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
