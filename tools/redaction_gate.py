"""Redaction pre-commit gate (Task 4.2 T5).

Independent content + path gate for commit-candidate redaction artifacts. For
each explicitly-given path it runs:

  - path gate: `redaction.path_policy_findings` blocks local-carry-only paths
    (a raw/ capture dir, a `_redaction_keymap.json`, a raw `*_raw_*.xml`)
    regardless of content.
  - content gate: `redaction.residual_scan` over JSON / MD / TXT / CSV content.
  - a binary image (.png/.jpg/...) FAILs with BINARY_IMAGE — it cannot be
    content-scanned for residual PII (screenshots are local-carry only;
    only redacted text artifacts are commit candidates).
  - a missing path or an unsupported extension is a FAILURE, never silently
    skipped (the gate refuses to pass files it cannot prove clean).

Any finding -> exit 1. A clean redacted artifact -> exit 0.

READ-ONLY w.r.t. git: this tool NEVER runs git add / stage / commit / push, and
it does NOT auto-discover staged files — it checks only the path arguments given.

Usage:
    python tools/redaction_gate.py <path> [<path> ...] [--format text|json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, ".."))   # repo root -> enables `from src...`
from src import redaction as rd               # noqa: E402

SUPPORTED_CONTENT_EXTS = (".json", ".md", ".txt", ".csv")
# Image binaries cannot be content-scanned for residual PII. A commit-candidate
# image FAILs with a dedicated kind (screenshots are local-carry only per the
# redaction policy — only redacted text artifacts are commit candidates).
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
TOOL_VERSION = "redaction-gate-v1"


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _as_dict(path: str, finding) -> dict:
    return {
        "path": _norm(path),
        "kind": finding.kind,
        "severity": finding.severity,
        "location": finding.location,
        "message": finding.message,
    }


def _read_text(path: str) -> str:
    # Strict UTF-8: an undecodable "text" artifact is suspicious -> surfaced as a
    # READ_ERROR by the caller, never silently mangled with replacement chars.
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _finding(path: str, kind: str, message: str) -> dict:
    norm = _norm(path)
    return {"path": norm, "kind": kind, "severity": "high",
            "location": norm, "message": message}


def scan_path(path: str) -> List[dict]:
    """Gate a single path; return a list of finding dicts (empty == clean).

    Order: path policy first (a forbidden carry path is blocked regardless of
    content and is never read), then existence / directory, then extension
    support, then read, then the content scan. A missing path, a directory, an
    unsupported extension, an unreadable file, or malformed JSON each FAIL — the
    gate never passes a file it cannot prove to be a clean, valid commit candidate.
    """
    # 1. path policy — forbidden carry paths (raw dir/file, keymap) blocked first.
    path_findings = rd.path_policy_findings([path])
    if path_findings:
        return [_as_dict(path, f) for f in path_findings]

    # 2. existence / directory — neither is a scannable commit candidate.
    if not os.path.exists(path):
        return [_finding(path, "MISSING_PATH", "path does not exist")]
    if os.path.isdir(path):
        return [_finding(path, "INVALID_PATH",
                         "path is a directory; the gate checks individual files only "
                         "(no recursion)")]

    # 3. extension support — unsupported (e.g. binary) is a failure, not a skip.
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return [_finding(path, "BINARY_IMAGE",
                         f"binary image ({ext}) cannot be content-scanned for residual "
                         f"PII; screenshots are local-carry only — commit forbidden "
                         f"(redacted text artifacts only)")]
    if ext not in SUPPORTED_CONTENT_EXTS:
        return [_finding(path, "UNSUPPORTED_EXT",
                         f"unsupported extension {ext!r}; cannot content-scan "
                         f"(supported: {', '.join(SUPPORTED_CONTENT_EXTS)})")]

    # 4. read — an unreadable / undecodable file FAILs (no traceback leak).
    try:
        text = _read_text(path)
    except (OSError, UnicodeDecodeError) as e:
        return [_finding(path, "READ_ERROR",
                         f"cannot read/decode file: {e.__class__.__name__}")]

    # 5. content scan — JSON must be VALID JSON (no raw-text fallback); MD/TXT as
    #    text. A malformed JSON FAILs even when it carries no detectable PII.
    if ext == ".json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            return [_finding(path, "INVALID_JSON",
                             f"not valid JSON (a commit-candidate sidecar must "
                             f"parse): {e.msg} at line {e.lineno}")]
        findings = rd.residual_scan(obj)
    else:
        findings = rd.residual_scan(text)
    return [_as_dict(path, f) for f in findings]


def run_gate(paths: List[str]) -> dict:
    """Gate every path; aggregate findings. verdict == FAIL iff any finding."""
    findings: List[dict] = []
    for p in paths:
        findings.extend(scan_path(p))
    return {
        "tool_version": TOOL_VERSION,
        "verdict": "FAIL" if findings else "PASS",
        "checked": [_norm(p) for p in paths],
        "findings": findings,
    }


def render_text(result: dict) -> str:
    lines = [f"redaction-gate: {result['verdict']} "
             f"({len(result['checked'])} path(s), {len(result['findings'])} finding(s))"]
    for f in result["findings"]:
        lines.append(
            f"  FAIL {f['path']} [{f['kind']}/{f['severity']}] {f['location']}: {f['message']}"
        )
    if result["verdict"] == "PASS":
        lines.append("  all checked paths are clean redacted commit candidates")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=("Redaction pre-commit gate (content + path). READ-ONLY; "
                     "never runs git and never auto-discovers staged files."),
    )
    ap.add_argument("paths", nargs="+", help="commit-candidate artifact path(s) to gate")
    ap.add_argument("--format", choices=["text", "json"], default="text", dest="fmt")
    args = ap.parse_args(argv)

    result = run_gate(args.paths)
    if args.fmt == "json":
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    else:
        payload = render_text(result)
    sys.stdout.buffer.write(payload.encode("utf-8"))
    return 1 if result["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
