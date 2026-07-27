# -*- coding: utf-8 -*-
"""워크플로 agent untracked 오염 스캔 (P-2 — read-only).

배경 (FAILURE_TAXONOMY C7 phantom): 합성 워크플로 agent가 구조화 반환 대신
yaml 파일을 batch dir에 **직접 기록**(untracked, git 미추적)해 산출물을 오염시켰다.
합성 agent는 read-only/return-only여야 하며, 실행 후 보호 디렉토리에 예상 외
untracked 파일이 생겼는지 반드시 스캔한다.

순수 함수(단위 테스트 대상):
  - scan_contamination(untracked, protected_prefixes, allow_globs)
      → 보호 prefix 하위이면서 allow_globs에 해당하지 않는 untracked 경로 목록

IO wrapper (git, read-only):
  - git_untracked(cwd)  — `git status --porcelain` 의 '??' 항목
  - main()              — 스캔 후 오염 발견 시 exit 1
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _under_prefix(norm_path: str, prefix: str) -> bool:
    pre = _norm(prefix).rstrip("/")
    return norm_path == pre or norm_path.startswith(pre + "/")


def scan_contamination(untracked, protected_prefixes, allow_globs) -> list:
    """보호 prefix 하위이면서 허용 glob에 해당하지 않는 untracked 경로 목록 반환.

    경로는 forward-slash로 정규화해 비교. prefix는 경계 단위(디렉토리)로만 매칭
    ('...Audit2'가 '...Audit' prefix에 오탐되지 않음).
    """
    flagged: list = []
    for raw in untracked:
        norm = _norm(raw)
        if not any(_under_prefix(norm, pre) for pre in protected_prefixes):
            continue
        if any(fnmatch.fnmatch(norm, g) for g in allow_globs):
            continue
        flagged.append(norm)
    return flagged


def git_untracked(cwd=".") -> list:
    """`git status --porcelain` 의 untracked('??') 경로 목록 (read-only)."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout
    paths: list = []
    for line in out.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:].strip().strip('"'))
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="워크플로 agent untracked 오염 스캔 (read-only)")
    ap.add_argument("--protected", action="append", default=[],
                    help="보호 디렉토리 prefix (반복 가능)")
    ap.add_argument("--allow", action="append", default=[],
                    help="허용 untracked glob (반복 가능, 예: */scratch/*)")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args(argv)

    if not args.protected or any(
        not prefix.strip() or prefix != prefix.strip()
        for prefix in args.protected
    ):
        print(
            "error: --protected requires exact non-blank prefixes "
            "without surrounding whitespace",
            file=sys.stderr,
        )
        return 2

    try:
        untracked = git_untracked(args.cwd)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"infra failure: {exc}", file=sys.stderr)
        return 3
    flagged = scan_contamination(untracked, args.protected, args.allow)
    if flagged:
        print("=== ⚠ untracked 오염 의심 (보호 prefix 하위·미허용) ===")
        for p in flagged:
            print("  ", p)
        print(f"총 {len(flagged)}건 — 합성 agent file side-effect 여부 확인 필요")
        return 1
    print("untracked 오염 없음 (보호 prefix 하위 미허용 untracked 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
