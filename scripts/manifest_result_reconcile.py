# -*- coding: utf-8 -*-
"""manifest ↔ 구현 ↔ 결과 tc_id 조인 reconcile (P-4).

배경 (FAILURE_TAXONOMY C12): 조인 무결성이 스크립트별 재구현에 의존해 chunk-N /
구현 / 결과 수치가 ±1~3 어긋나고, annex·probe가 manifest 밖에서 실행돼(orphan)
결과 집계가 새어나갔다. tc_id는 4종 manifest 전반에서 안정적 조인 키이므로,
(manifest 선언 · 구현 yaml · RESULT 판정) 3원을 tc_id로 자동 reconcile한다.

순수 함수(단위 테스트 대상):
  - reconcile_by_tcid(expected, implemented, results)
      → {"rows": [tc_id별 조인 상태], "summary": {불일치 4종}}

IO wrapper: read_manifest_tcids / read_yaml_stems / read_result_dispositions / main.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys


def reconcile_by_tcid(expected, implemented, results) -> dict:
    """tc_id 조인으로 3원 reconcile.

    expected    : manifest 선언 tc_id (iterable)
    implemented : 구현된 yaml tc_id (iterable)
    results     : {tc_id: disposition}
    반환 summary:
      reconciled              — 3원 모두 존재
      manifest_not_implemented— 선언됐으나 미구현
      implemented_no_result   — 구현됐으나 결과 없음
      orphan_result           — 결과인데 manifest에 없음 (annex 밖 실행)
    """
    expected = set(expected)
    implemented = set(implemented)
    result_ids = set(results.keys())
    all_ids = expected | implemented | result_ids

    rows = [
        {
            "tc_id": t,
            "in_manifest": t in expected,
            "implemented": t in implemented,
            "result": results.get(t, ""),
        }
        for t in sorted(all_ids)
    ]
    summary = {
        "reconciled": sorted(expected & implemented & result_ids),
        "manifest_not_implemented": sorted(expected - implemented),
        "implemented_no_result": sorted(implemented - result_ids),
        "orphan_result": sorted(result_ids - expected),
    }
    return {"rows": rows, "summary": summary}


# ─────────────────────────── IO wrapper ───────────────────────────

def read_manifest_tcids(csv_path, tcid_col="tc_id") -> list:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        return [r[tcid_col].strip() for r in csv.DictReader(f) if r.get(tcid_col)]


def read_yaml_stems(yaml_dir, pattern="ALTBASIC_*.yaml") -> list:
    stems = []
    for f in glob.glob(os.path.join(yaml_dir, pattern)):
        stems.append(
            os.path.basename(f).replace("_canonical.yaml", "").replace(".yaml", "")
        )
    return stems


def read_result_dispositions(csv_path, tcid_col="tc_id", verdict_col="result") -> dict:
    out = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            t = (r.get(tcid_col) or "").strip()
            if t:
                out[t] = (r.get(verdict_col) or "").strip()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="manifest ↔ 구현 ↔ 결과 tc_id reconcile")
    ap.add_argument("--manifest", required=True, help="manifest CSV (tc_id 컬럼)")
    ap.add_argument("--yaml-dir", required=True, help="구현 yaml 디렉토리")
    ap.add_argument("--result", help="RESULT CSV (tc_id, result 컬럼)")
    args = ap.parse_args(argv)

    expected = read_manifest_tcids(args.manifest)
    implemented = read_yaml_stems(args.yaml_dir)
    results = read_result_dispositions(args.result) if args.result else {}

    rec = reconcile_by_tcid(expected, implemented, results)
    print(json.dumps(rec["summary"], ensure_ascii=False, indent=2, sort_keys=True))
    s = rec["summary"]
    drift = s["manifest_not_implemented"] or s["implemented_no_result"] or s["orphan_result"]
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
