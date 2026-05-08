"""Synthetic Delta Measurement (PR 7A small implementation).

Read-only XML pair measurement. Computes basic metrics (sha256, visible
text Jaccard, added/removed texts, target presence) and emits a verdict in
{stable, meaningful_delta, insufficient}.

Hard guarantees:
- Does NOT write files (no reports/, generated/, catalog/ output).
- Does NOT mutate fixture inputs.
- Does NOT call git, network, or any subprocess.
- Outputs JSON to stdout only.

PR 7A scope: 3 fixture branches (identical_snapshot, text_only_change,
insufficient_evidence). Markdown output, full 5-fixture corpus, threshold
tuning are PR 7B scope (deferred).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional, Sequence, Set
from xml.etree import ElementTree as ET

SCHEMA_VERSION = 1
TOOL_VERSION = "pr7-delta-measurement-v1"

MIN_TEXT_COUNT = 3


def extract_visible_texts(root: ET.Element) -> Set[str]:
    out: Set[str] = set()
    for node in root.iter():
        for attr in ("text", "content-desc"):
            v = node.attrib.get(attr)
            if v is None:
                continue
            v = v.strip()
            if v:
                out.add(v)
    return out


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jaccard(a: Set[str], b: Set[str]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def classify_verdict(
    *,
    xml_sha256_equal: bool,
    visible_texts_before_count: int,
    visible_texts_after_count: int,
    added_texts: Set[str],
    removed_texts: Set[str],
    target_text: Optional[str],
    target_presence_before: bool,
    target_presence_after: bool,
) -> str:
    after_insufficient = visible_texts_after_count < MIN_TEXT_COUNT
    before_insufficient = visible_texts_before_count < MIN_TEXT_COUNT
    target_present_anywhere = target_presence_before or target_presence_after

    if after_insufficient and not target_present_anywhere:
        return "insufficient"
    if before_insufficient and after_insufficient:
        return "insufficient"

    if xml_sha256_equal:
        return "stable"

    if target_text is not None:
        if target_presence_before and not target_presence_after:
            return "meaningful_delta"
        if target_presence_after and not target_presence_before:
            return "meaningful_delta"

    if added_texts or removed_texts:
        return "meaningful_delta"

    return "stable"


def measure_pair(
    before_xml: bytes,
    after_xml: bytes,
    target_text: Optional[str],
) -> dict:
    before_root = ET.fromstring(before_xml)
    after_root = ET.fromstring(after_xml)
    before_set = extract_visible_texts(before_root)
    after_set = extract_visible_texts(after_root)
    sha_before = sha256_hex(before_xml)
    sha_after = sha256_hex(after_xml)
    added = after_set - before_set
    removed = before_set - after_set
    j = jaccard(before_set, after_set)
    target_in_before = target_text in before_set if target_text else False
    target_in_after = target_text in after_set if target_text else False
    verdict = classify_verdict(
        xml_sha256_equal=(sha_before == sha_after),
        visible_texts_before_count=len(before_set),
        visible_texts_after_count=len(after_set),
        added_texts=added,
        removed_texts=removed,
        target_text=target_text,
        target_presence_before=target_in_before,
        target_presence_after=target_in_after,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "verdict": verdict,
        "xml_sha256": {
            "before": sha_before,
            "after": sha_after,
            "equal": sha_before == sha_after,
        },
        "visible_texts": {
            "before_count": len(before_set),
            "after_count": len(after_set),
            "jaccard": j,
            "added": sorted(added),
            "removed": sorted(removed),
        },
        "target": {
            "text": target_text,
            "before": target_in_before,
            "after": target_in_after,
        },
    }


def measure_fixture(fixture_dir: Path) -> dict:
    before_path = fixture_dir / "before.xml"
    after_path = fixture_dir / "after.xml"
    expected_path = fixture_dir / "expected.json"
    if not before_path.exists() or not after_path.exists():
        raise FileNotFoundError(
            f"fixture missing before.xml/after.xml under {fixture_dir}"
        )
    expected: dict = {}
    if expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    target = expected.get("target_text")
    before_xml = before_path.read_bytes()
    after_xml = after_path.read_bytes()
    result = measure_pair(before_xml, after_xml, target)
    result["fixture"] = {
        "name": expected.get("name") or fixture_dir.name,
        "expected_verdict": expected.get("expected_verdict"),
    }
    if expected.get("expected_verdict"):
        result["match"] = result["verdict"] == expected["expected_verdict"]
    return result


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="synthetic_delta_measure",
        description="PR 7A synthetic delta measurement (read-only, JSON stdout).",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--fixture-dir",
        type=Path,
        help="Path to a fixture directory containing before.xml/after.xml/expected.json",
    )
    g.add_argument(
        "--before",
        type=Path,
        help="Path to before XML (requires --after)",
    )
    p.add_argument(
        "--after",
        type=Path,
        help="Path to after XML (used with --before)",
    )
    p.add_argument(
        "--target",
        type=str,
        default=None,
        help="Optional target text to track presence (used with --before/--after)",
    )
    return p


def _emit_json(result: dict) -> None:
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    data = payload.encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.flush()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)
    if args.fixture_dir:
        result = measure_fixture(args.fixture_dir)
    else:
        if not args.after:
            parser.error("--after required when --before is given")
        result = measure_pair(
            args.before.read_bytes(),
            args.after.read_bytes(),
            args.target,
        )
    _emit_json(result)
    if "match" in result:
        return 0 if result["match"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
