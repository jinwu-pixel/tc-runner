"""Git Safe Push Audit (PR 6A skeleton).

Read-only pre-push audit. Inspects local git state and reports whether the
working tree is in a shape worth pushing to a base ref (default origin/master).

Hard guarantees:
- Does NOT modify the index, working tree, or HEAD.
- Does NOT execute push, commit, reset, checkout, or any rewrite.
- May call `git fetch <remote> <branch>` (read-only on local refs);
  pass --no-fetch to suppress even that.
- Does NOT validate TC content (semantics, schema, runtime). It only
  inspects the git surface — branch, ahead/behind, staging, untracked,
  and path policy.

Exit code: 0 on PASS, 0 on WARN, 1 on FAIL. Output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import time
import uuid
from typing import List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1
TOOL_VERSION = "pr6-git-audit-v1"

FORBIDDEN_BASENAME_PATTERNS: Tuple[str, ...] = (
    "probe_*.xml",
    "_probe_*.py",
    "probe_dump_*.xml",
    "ui_*.xml",
    "popup_*.xml",
    "screenshot_*.png",
)

FORBIDDEN_DIRECTORY_PREFIXES: Tuple[str, ...] = (
    "generated/",
    "reports/",
)

FORBIDDEN_DIRECTORY_NAMES: Tuple[str, ...] = (
    "catalog",
)

NOTE_READ_ONLY = "READ-ONLY git audit only — does not validate TC content"


def normalize_path(path: str) -> str:
    if not path:
        return path
    s = path.replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    return s


def matches_forbidden(path: str) -> Optional[str]:
    norm = normalize_path(path)
    if not norm:
        return None
    basename = norm.rsplit("/", 1)[-1]
    for pat in FORBIDDEN_BASENAME_PATTERNS:
        if fnmatch.fnmatchcase(basename, pat):
            return f"basename:{pat}"
    for prefix in FORBIDDEN_DIRECTORY_PREFIXES:
        prefix_clean = prefix.rstrip("/")
        if norm == prefix_clean or norm.startswith(prefix):
            return f"prefix:{prefix}"
    parts = norm.split("/")
    for name in FORBIDDEN_DIRECTORY_NAMES:
        if name in parts[:-1]:
            return f"dir-name:{name}"
    return None


def under_any_prefix(path: str, prefixes: Sequence[str]) -> bool:
    norm = normalize_path(path)
    for prefix in prefixes:
        p = normalize_path(prefix)
        if not p:
            continue
        p_clean = p.rstrip("/")
        if norm == p_clean or norm.startswith(p_clean + "/"):
            return True
    return False


def _run_git(args: Sequence[str], cwd: str) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, out, err


def git_branch_current(cwd: str) -> str:
    rc, out, _ = _run_git(["branch", "--show-current"], cwd)
    if rc != 0:
        return ""
    return out.strip()


def git_fetch(cwd: str, base: str) -> Tuple[bool, str]:
    if "/" not in base:
        return False, f"base {base!r} not in 'remote/branch' form"
    remote, _, branch = base.partition("/")
    rc, _, err = _run_git(["fetch", remote, branch, "--quiet"], cwd)
    if rc != 0:
        return False, err.strip()
    return True, ""


def git_ahead_behind(cwd: str, base: str) -> Tuple[Optional[int], Optional[int], str]:
    rc, out, err = _run_git(
        ["rev-list", "--left-right", "--count", f"HEAD...{base}"], cwd
    )
    if rc != 0:
        return None, None, err.strip()
    parts = out.strip().split()
    if len(parts) != 2:
        return None, None, f"unexpected rev-list output: {out!r}"
    try:
        return int(parts[0]), int(parts[1]), ""
    except ValueError:
        return None, None, f"non-integer rev-list output: {out!r}"


def git_staged_files(cwd: str) -> List[str]:
    rc, out, _ = _run_git(["diff", "--cached", "--name-only", "-z"], cwd)
    if rc != 0 or not out:
        return []
    return [normalize_path(p) for p in out.split("\x00") if p]


def git_porcelain(cwd: str) -> Tuple[List[str], List[str]]:
    rc, out, _ = _run_git(
        ["status", "--porcelain", "-z", "--untracked-files=all"], cwd
    )
    tracked_dirty: List[str] = []
    untracked: List[str] = []
    if rc != 0 or not out:
        return tracked_dirty, untracked
    entries = [e for e in out.split("\x00") if e]
    i = 0
    while i < len(entries):
        entry = entries[i]
        if len(entry) < 4:
            i += 1
            continue
        xy = entry[:2]
        path = entry[3:]
        norm = normalize_path(path)
        if xy[0] == "R":
            i += 2  # rename: skip the 'from' path on the next iteration
        else:
            i += 1
        if xy == "??":
            untracked.append(norm)
            continue
        x, y = xy[0], xy[1]
        if x != "?" and y != " ":
            tracked_dirty.append(norm)
    return tracked_dirty, untracked


def aggregate_verdict(checks: List[dict]) -> str:
    if any(c["status"] == "FAIL" for c in checks):
        return "FAIL"
    if any(c["status"] == "WARN" for c in checks):
        return "WARN"
    return "PASS"


def run_audit(
    *,
    cwd: str,
    base: str = "origin/master",
    expected_ahead: Optional[int] = None,
    expected_paths: Optional[Sequence[str]] = None,
    allowed_prefixes: Optional[Sequence[str]] = None,
    do_fetch: bool = True,
) -> dict:
    checks: List[dict] = []

    branch = git_branch_current(cwd)
    is_master = branch == "master"
    checks.append({
        "id": "branch_current",
        "status": "PASS" if is_master else "WARN",
        "detail": f"current branch: {branch!r}",
        "data": {"current": branch, "is_master": is_master},
    })

    if do_fetch:
        ok, err = git_fetch(cwd, base)
        checks.append({
            "id": "remote_fetch",
            "status": "PASS" if ok else "FAIL",
            "detail": "fetched" if ok else f"fetch failed: {err}",
            "data": {"base": base, "fetched": ok},
        })
    else:
        checks.append({
            "id": "remote_fetch",
            "status": "INFO",
            "detail": "fetch skipped (--no-fetch)",
            "data": {"base": base, "fetched": False, "skipped": True},
        })

    ahead, behind, ab_err = git_ahead_behind(cwd, base)
    if ahead is None or behind is None:
        checks.append({
            "id": "ahead_behind_count",
            "status": "FAIL",
            "detail": f"ahead/behind parse failed: {ab_err}",
            "data": {"ahead": None, "behind": None, "base": base},
        })
    else:
        checks.append({
            "id": "ahead_behind_count",
            "status": "PASS",
            "detail": f"ahead={ahead} behind={behind} base={base}",
            "data": {"ahead": ahead, "behind": behind, "base": base},
        })

    if behind is None:
        checks.append({
            "id": "head_minus_origin_empty",
            "status": "FAIL",
            "detail": "behind unknown (ahead_behind_count failed)",
            "data": {},
        })
    else:
        empty = behind == 0
        checks.append({
            "id": "head_minus_origin_empty",
            "status": "PASS" if empty else "FAIL",
            "detail": f"behind={behind} (commits in {base} not in HEAD)",
            "data": {"behind": behind, "empty": empty},
        })

    if ahead is None:
        checks.append({
            "id": "origin_minus_head_count",
            "status": "FAIL",
            "detail": "ahead unknown (ahead_behind_count failed)",
            "data": {},
        })
    elif expected_ahead is None:
        checks.append({
            "id": "origin_minus_head_count",
            "status": "INFO",
            "detail": f"ahead={ahead} (no --expected-ahead given)",
            "data": {"ahead": ahead, "expected_ahead": None},
        })
    else:
        ok = ahead == expected_ahead
        checks.append({
            "id": "origin_minus_head_count",
            "status": "PASS" if ok else "FAIL",
            "detail": f"ahead={ahead} expected={expected_ahead}",
            "data": {"ahead": ahead, "expected_ahead": expected_ahead, "match": ok},
        })

    staged = git_staged_files(cwd)
    checks.append({
        "id": "staged_files_list",
        "status": "INFO",
        "detail": f"{len(staged)} staged",
        "data": {"staged": staged, "count": len(staged)},
    })

    tracked_dirty, untracked = git_porcelain(cwd)

    tracked_dirty_forbidden = [
        {"path": p, "pattern": m}
        for p in tracked_dirty
        if (m := matches_forbidden(p)) is not None
    ]
    if tracked_dirty_forbidden:
        td_status, td_detail = "FAIL", (
            f"{len(tracked_dirty_forbidden)} tracked-dirty path(s) match forbidden patterns"
        )
    elif tracked_dirty:
        td_status, td_detail = "WARN", f"{len(tracked_dirty)} tracked file(s) dirty (not staged)"
    else:
        td_status, td_detail = "PASS", "no tracked files dirty"
    checks.append({
        "id": "tracked_dirty",
        "status": td_status,
        "detail": td_detail,
        "data": {
            "tracked_dirty": tracked_dirty,
            "forbidden": tracked_dirty_forbidden,
        },
    })

    untracked_forbidden = [
        {"path": p, "pattern": m}
        for p in untracked
        if (m := matches_forbidden(p)) is not None
    ]
    checks.append({
        "id": "untracked_count",
        "status": "INFO",
        "detail": f"{len(untracked)} untracked",
        "data": {"count": len(untracked)},
    })
    checks.append({
        "id": "untracked_forbidden_report",
        "status": "WARN" if untracked_forbidden else "PASS",
        "detail": (
            f"{len(untracked_forbidden)} untracked path(s) match forbidden patterns"
            if untracked_forbidden
            else "no untracked path matches forbidden patterns"
        ),
        "data": {"forbidden": untracked_forbidden},
    })

    if allowed_prefixes:
        norm_prefixes = [normalize_path(p) for p in allowed_prefixes]
        violations = [p for p in staged if not under_any_prefix(p, norm_prefixes)]
        checks.append({
            "id": "allowed_whitelist_match",
            "status": "FAIL" if violations else "PASS",
            "detail": (
                f"{len(violations)} staged path(s) outside allowed prefixes"
                if violations
                else "all staged paths under allowed prefixes"
            ),
            "data": {"prefixes": norm_prefixes, "violations": violations},
        })
    else:
        checks.append({
            "id": "allowed_whitelist_match",
            "status": "INFO",
            "detail": "no --allowed-prefix given",
            "data": {},
        })

    staged_forbidden = [
        {"path": p, "pattern": m}
        for p in staged
        if (m := matches_forbidden(p)) is not None
    ]
    checks.append({
        "id": "forbidden_path_guard",
        "status": "FAIL" if staged_forbidden else "PASS",
        "detail": (
            f"{len(staged_forbidden)} staged path(s) match forbidden patterns"
            if staged_forbidden
            else "no staged path matches forbidden patterns"
        ),
        "data": {"forbidden": staged_forbidden},
    })

    if expected_paths is not None:
        expected_set = sorted({normalize_path(p) for p in expected_paths})
        staged_set = sorted(set(staged))
        missing = sorted(set(expected_set) - set(staged_set))
        unexpected = sorted(set(staged_set) - set(expected_set))
        ok = not missing and not unexpected
        checks.append({
            "id": "candidate_whitelist_match",
            "status": "PASS" if ok else "FAIL",
            "detail": (
                "staged set matches expected set exactly"
                if ok
                else f"missing={len(missing)} unexpected={len(unexpected)}"
            ),
            "data": {
                "expected": expected_set,
                "staged": staged_set,
                "missing": missing,
                "unexpected": unexpected,
            },
        })
    else:
        checks.append({
            "id": "candidate_whitelist_match",
            "status": "INFO",
            "detail": "no --expected-path given",
            "data": {},
        })

    checks.append({
        "id": "force_prohibition_notice",
        "status": "INFO",
        "detail": "force / force-with-lease prohibited; use plain `git push <remote> <branch>`",
        "data": {"force_prohibited": True},
    })

    verdict = aggregate_verdict(checks)
    remote_name = base.partition("/")[0] if "/" in base else "origin"
    push_command = (
        f"git push {remote_name} {branch}" if branch else f"git push {remote_name}"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "run_id": uuid.uuid4().hex,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "branch": {"current": branch, "is_master": is_master},
        "staging": {
            "staged": staged,
            "tracked_dirty": tracked_dirty,
            "untracked_count": len(untracked),
        },
        "path_policy": {
            "expected_paths": [normalize_path(p) for p in (expected_paths or [])],
            "allowed_prefixes": [normalize_path(p) for p in (allowed_prefixes or [])],
            "forbidden_staged": staged_forbidden,
            "forbidden_untracked": untracked_forbidden,
            "forbidden_tracked_dirty": tracked_dirty_forbidden,
        },
        "checks": checks,
        "recommended": {
            "push_command": push_command,
            "force_prohibited": True,
            "human_review_required": True,
            "note": NOTE_READ_ONLY,
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only git push audit (PR 6A skeleton; JSON output only).",
    )
    parser.add_argument("--base", default="origin/master")
    parser.add_argument("--expected-ahead", type=int, default=None)
    parser.add_argument("--expected-path", action="append", default=[])
    parser.add_argument("--allowed-prefix", action="append", default=[])
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args(argv)

    result = run_audit(
        cwd=args.cwd,
        base=args.base,
        expected_ahead=args.expected_ahead,
        expected_paths=args.expected_path or None,
        allowed_prefixes=args.allowed_prefix or None,
        do_fetch=not args.no_fetch,
    )
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(payload.encode("utf-8"))
    return {"PASS": 0, "WARN": 0, "FAIL": 1}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
