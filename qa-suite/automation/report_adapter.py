# report_adapter.py — qa-suite 실행 결과 → tc-runner runtime bundle summary.json 계약 변환
# 새 포맷을 만들지 않는다. 기준 계약 = tc-runner src/reporter.py write_summary_json
# (schema_version=1 / run_id=YYYYMMDDTHHMMSSZ UTC / device / summary / results[].steps[]).
# orchestrator 아님 — 단방향 변환 adapter 만 제공한다.
import json
import os
from datetime import datetime, timezone

SCHEMA_VERSION = 1
TOOL_VERSION = "qa-suite-bugrunner-v1"

# tc-runner steps[] 필드 계약 (tests/test_reporter.py shape 단언과 동일 집합)
_STEP_FIELDS = ("index", "action", "passed", "duration_s", "message", "execution_mode",
                "manual_action", "skip_reason", "paused", "screenshot_path")


def new_run_id():
    """tc-runner preflight._now_run_id 와 동일 포맷 (UTC, 로컬시간 금지)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _step(index, status, reason, artifact):
    is_skip = status == "SKIP"
    passed = status in ("PASS", "SKIP")
    art_posix = str(artifact).replace("\\", "/") if artifact else None
    if status == "PASS" or is_skip:
        message = ""
    else:
        message = f"[{status}] {reason}" if reason else f"[{status}]"
        if art_posix:
            # 아티팩트 포인터는 message 로 항상 보존 (screencap 실패 시에도 추적선 유지)
            message += f" | artifacts: {art_posix}"
    # screenshot 은 실재 파일만 evidence 로 기록 — 깨진 링크 금지
    screenshot = None
    if art_posix and os.path.isfile(os.path.join(str(artifact), "screen.png")):
        screenshot = art_posix + "/screen.png"
    return {
        "index": index,
        "action": "iteration",
        "passed": passed,
        "duration_s": 0.0,
        "message": message,
        "execution_mode": "auto",
        "manual_action": "skip" if is_skip else "",
        "skip_reason": reason if is_skip else "",
        "paused": False,
        "screenshot_path": screenshot,
    }


def build_summary_payload(run_id, device, tests_results, generated_at=None):
    """tests_results: {test_name: [(status, reason, artifact_dir|None), ...]}

    summary 집계 의미 주의 — legacy Reporter 와 다름 (필드 shape 만 v1 호환):
      qa-suite: 시험당 단일 분류(비중복). all-SKIP → skipped(passed=False),
                WARN/FAIL/INFRA 포함 → failed, 그 외(PASS·PASS+SKIP 혼합) → passed.
      legacy Reporter: skip step 포함 TC 가 passed 와 skipped 에 중복 계산될 수 있음.
    의미 통합은 트랙 B 이관 (selftest test_result_level_semantics_pinned 에 고정).
    """
    results = []
    n_passed = n_skipped = n_failed = 0
    for name, rows in tests_results.items():
        statuses = [s for s, _, _ in rows]
        steps = [_step(i + 1, s, r, a) for i, (s, r, a) in enumerate(rows)]
        all_skip = bool(statuses) and all(s == "SKIP" for s in statuses)
        test_passed = bool(statuses) and all(s in ("PASS", "SKIP") for s in statuses) \
            and not all_skip
        if all_skip:
            n_skipped += 1
        elif test_passed:
            n_passed += 1
        else:
            n_failed += 1
        results.append({
            "name": name,
            "description": "",
            "passed": test_passed,
            "duration_s": 0.0,
            "steps": steps,
        })

    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "generated_at": ts,
        "device": dict(device or {}),
        "summary": {
            "total": len(results),
            "passed": n_passed,
            "skipped": n_skipped,
            "failed": n_failed,
        },
        "results": results,
    }


def write_summary_json(report_root, run_id, payload):
    bundle_dir = os.path.join(report_root, run_id)
    os.makedirs(bundle_dir, exist_ok=True)
    path = os.path.join(bundle_dir, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
