# -*- coding: utf-8 -*-
"""판정 원장 재집계 도구 (P-3 — 수기 집계·추정치 드리프트 방지).

배경 (FAILURE_TAXONOMY C1): summary 수치가 단일 원장(CSV)과 어긋나는 드리프트가
반복됐다(수기 카운트·추정치 병기). 판정 CSV를 **단일 원장**으로 두고 summary는
본 스크립트로 **결정적 재집계**한다. `judge_method`(auto/human) 컬럼으로 자동/사람
판정을 분리해, cue 단독 판정과 사람 확정을 구분 가능하게 한다.

분모 명명 원칙([[feedback_metric_denominator_naming]]): 미판단분(undecided)은
비율 분모에서 제외하고 `total`(전체)과 `judged`(판단분)를 이름 붙여 병기한다.

순수 함수(단위 테스트 대상):
  - tally(rows, key)                       — 단일 키 분포
  - cross_tally(rows, key_a, key_b)        — 교차 분포(중첩 dict, JSON-safe)
  - recompute_ledger_summary(rows, verdict_key, method_key, undecided_values)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter


def tally(rows, key) -> dict:
    """rows에서 key 값의 분포. 키 부재/None은 빈 문자열 버킷으로 집계."""
    c = Counter((r.get(key) or "") for r in rows)
    return dict(c)


def cross_tally(rows, key_a, key_b) -> dict:
    """key_a × key_b 교차 분포 → {a_value: {b_value: count}} (JSON-safe 중첩 dict)."""
    out: dict = {}
    for r in rows:
        a = r.get(key_a) or ""
        b = r.get(key_b) or ""
        out.setdefault(a, {})
        out[a][b] = out[a].get(b, 0) + 1
    return out


def recompute_ledger_summary(rows, verdict_key, method_key, undecided_values=()) -> dict:
    """단일 원장(rows)에서 summary를 결정적으로 재집계.

    total  = 전체 행 수
    judged = undecided_values(미판단)에 속하지 않는 행 수 (비율 분모)
    by_verdict / by_method / by_verdict_method = 분포.
    """
    undecided = set(undecided_values)
    total = len(rows)
    judged = sum(1 for r in rows if (r.get(verdict_key) or "") not in undecided)
    return {
        "total": total,
        "judged": judged,
        "by_verdict": tally(rows, verdict_key),
        "by_method": tally(rows, method_key),
        "by_verdict_method": cross_tally(rows, verdict_key, method_key),
    }


def read_csv(path) -> list:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="판정 원장 재집계 (결정적, 수기 집계 대체)")
    ap.add_argument("csv_path")
    ap.add_argument("--verdict-key", default="disposition")
    ap.add_argument("--method-key", default="judge_method")
    ap.add_argument("--undecided", action="append", default=[],
                    help="미판단 판정값 (비율 분모 제외, 반복 가능)")
    args = ap.parse_args(argv)

    rows = read_csv(args.csv_path)
    summary = recompute_ledger_summary(
        rows, args.verdict_key, args.method_key, undecided_values=tuple(args.undecided)
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
