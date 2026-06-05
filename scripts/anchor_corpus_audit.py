"""Read-only corpus anchor-extraction audit (menu-tree v1.2, Task 3).

Replays `extract_anchor_candidates` / `join_anchor_to_baseline` /
`classify_step` over the committed TC corpus to produce a summary dict. Pure
observation: NO device calls, NO TC mutation. JSON is written only when asked
(write_audit_json / --out); the default run never touches catalog/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# Allow standalone execution (`python scripts/anchor_corpus_audit.py`) to resolve
# the `src` package; under pytest the repo root is already on sys.path via conftest.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src import menu_anchor as ma


def _load_doc(path: Path) -> dict:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def discover_corpus(root) -> dict:
    root = Path(root)
    tc1 = root / "exported_tc1"
    top = sorted(tc1.glob("*.yaml"))
    auto = sorted((tc1 / "_autoconverted").glob("*.yaml"))
    ss = sorted((root / "exported_ss_call").glob("*.yaml"))
    golden = sorted((root / "golden_tc_set").glob("*.yaml"))
    return {
        "exported_tc1": top + auto,
        "exported_ss_call": ss,
        "golden_tc_set": golden,
        "_counts": {
            "exported_tc1": {"files": len(top) + len(auto),
                             "top_level": len(top), "autoconverted": len(auto)},
            "exported_ss_call": {"files": len(ss)},
            "golden_tc_set": {"files": len(golden)},
        },
    }


def _baseline_screens(baseline_path) -> list:
    if baseline_path is None:
        return []
    d = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    return d.get("screens", [])


def audit_corpus(root, baseline_path=None) -> dict:
    root = Path(root)
    disc = discover_corpus(root)
    counts = disc["_counts"]
    total_files = sum(c["files"] for c in counts.values())
    baseline_screens = _baseline_screens(baseline_path)
    baseline = {"schema_version": 1, "screens": baseline_screens}

    by_method: dict = {"deeplink": 0, "component": 0}
    by_domain: dict = {"settings": 0, "app": 0, "external": 0}
    app_packages: dict = {}
    settings_deeplinks: dict = {}     # action -> candidate count
    safety_counts: dict = {}
    total_cands = 0
    mapped = 0
    mapped_screen_ids: list = []
    mapped_actions: list = []

    for group in ("exported_tc1", "exported_ss_call", "golden_tc_set"):
        for path in disc[group]:
            tc = _load_doc(path)
            rel = path.relative_to(root).as_posix()

            for step in (tc.get("steps") or []):
                if not isinstance(step, dict):
                    continue
                name = ma.classify_step(step).safety.name
                safety_counts[name] = safety_counts.get(name, 0) + 1

            for c in ma.extract_anchor_candidates(tc, rel):
                total_cands += 1
                by_method[c.match_method] = by_method.get(c.match_method, 0) + 1
                parsed = ma._parse_am_start(c.entry_action)
                if c.domain == "settings":
                    by_domain["settings"] += 1
                    if parsed and parsed[0] == "deeplink":
                        settings_deeplinks[parsed[1]] = settings_deeplinks.get(parsed[1], 0) + 1
                elif c.domain.startswith("app:"):
                    by_domain["app"] += 1
                    pkg = c.domain.split(":", 1)[1]
                    app_packages[pkg] = app_packages.get(pkg, 0) + 1
                else:
                    by_domain["external"] += 1

                m = ma.join_anchor_to_baseline(c, baseline)
                if m.screen_id is not None:
                    mapped += 1
                    mapped_screen_ids.append(m.screen_id)
                    if parsed:
                        mapped_actions.append(parsed[1])

    return {
        "corpus": {**counts, "total_files": total_files},
        "candidates": {
            "total": total_cands,
            "by_method": by_method,
            "by_domain": by_domain,
            "app_packages": app_packages,
        },
        "settings_deeplinks": dict(sorted(settings_deeplinks.items())),
        "baseline": {
            "screens": len(baseline_screens),
            "mapped_candidates": mapped,
            "mapped_screen_ids": sorted(set(mapped_screen_ids)),
            "mapped_actions": sorted(set(mapped_actions)),
        },
        "action_safety": dict(sorted(safety_counts.items())),
    }


def write_audit_json(summary: dict, path) -> None:
    Path(path).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Read-only corpus anchor audit (no device).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--out", default=None, help="optional JSON output path")
    args = ap.parse_args(argv)
    summary = audit_corpus(args.root, baseline_path=args.baseline)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if args.out:
        write_audit_json(summary, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
