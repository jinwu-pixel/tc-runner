# -*- coding: utf-8 -*-
"""원본 HTML 시험방법 항목 수와 STAGE1 procedure_steps 수를 대조한다."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from html2txt import html_to_text


TOOLS_DIR = Path(__file__).resolve().parent
TRACK_DIR = TOOLS_DIR.parent
REPO_ROOT = TRACK_DIR.parent
DEFAULT_STAGE1 = TRACK_DIR / "stage1"
SOURCE_FILENAME = "CD_20_LGU_디바이스_5G_시험절차서_V02_00_00.html"
TARGET = (
    "1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5",
    "3.1", "3.2", "3.3", "3.4", "3.5",
    "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7",
    "11.1", "11.2", "11.3", "11.4", "11.5", "11.6", "11.7", "19.1",
)
NUMITEM = re.compile(r"^\s*(\d{1,2})\)\s")
H2_SECTION = re.compile(r"##H2## (\d{1,2}\.\d{1,2})\s")


class CoverageInputError(ValueError):
    pass


def discover_source(repo_root: Path = REPO_ROOT) -> Path:
    carrier_root = repo_root / "새 폴더 (2)" / "LGU+"
    matches = (
        list(carrier_root.glob(f"*/{SOURCE_FILENAME}"))
        if carrier_root.is_dir()
        else []
    )
    if not matches:
        raise CoverageInputError(
            f"원본 HTML 없음: --source로 {SOURCE_FILENAME} 경로를 지정하세요"
        )
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise CoverageInputError(f"원본 HTML 중복 {len(matches)}건: {rendered}")
    return matches[0]


def count_source_steps(source: Path, targets: tuple[str, ...]) -> dict[str, int]:
    if not source.is_file():
        raise CoverageInputError(f"원본 HTML 없음: {source}")
    lines = html_to_text(source.read_text(encoding="utf-8")).splitlines()
    h2_idx = [(index, line) for index, line in enumerate(lines) if line.startswith("##H2## ")]

    counts: dict[str, int] = {}
    for position, (start, line) in enumerate(h2_idx):
        match = H2_SECTION.match(line)
        if not match or match.group(1) not in targets:
            continue
        section = match.group(1)
        end = h2_idx[position + 1][0] if position + 1 < len(h2_idx) else len(lines)
        body = lines[start:end]
        cut = next(
            (
                index
                for index, body_line in enumerate(body)
                if body_line.startswith("##H3## ") and "판정기준" in body_line
            ),
            len(body),
        )
        numbers = {
            int(match.group(1))
            for body_line in body[:cut]
            if (match := NUMITEM.match(body_line))
        }
        counts[section] = len(numbers)
    return counts


def count_ctf_steps(stage1_dir: Path) -> dict[str, int]:
    if not stage1_dir.is_dir():
        raise CoverageInputError(f"STAGE1 디렉토리 없음: {stage1_dir}")
    files = sorted(stage1_dir.glob("*_canonical.yaml"))
    if not files:
        raise CoverageInputError(f"CTF 입력 0건: {stage1_dir}")

    counts: dict[str, int] = {}
    for path in files:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        row = (document.get("source_trace") or {}).get("row")
        if row in counts:
            raise CoverageInputError(f"source_trace.row 중복: {row}")
        counts[row] = len(document.get("procedure_steps") or [])
    return counts


def render_report(
    source_counts: dict[str, int],
    ctf_counts: dict[str, int],
    targets: tuple[str, ...],
) -> int:
    print("%-7s %-10s %-10s %s" % ("절", "원문 항목", "CTF step", "판정"))
    bad = 0
    total_source = total_ctf = 0
    for section in targets:
        source_missing = section not in source_counts
        ctf_missing = section not in ctf_counts
        source_value = source_counts.get(section, 0)
        ctf_value = ctf_counts.get(section, 0)
        total_source += source_value
        total_ctf += ctf_value
        ok = not source_missing and not ctf_missing and source_value == ctf_value
        if not ok:
            bad += 1
        status = "OK" if ok else "MISSING" if source_missing or ctf_missing else "MISMATCH"
        print("%-7s %-10d %-10d %s" % (section, source_value, ctf_value, status))
    print(
        "\n합계  원문 %d / CTF %d  — 불일치 %d건"
        % (total_source, total_ctf, bad)
    )
    return 0 if bad == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="LGU+ 시험절차서 HTML")
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1)
    parser.add_argument("--target", action="append", dest="targets")
    args = parser.parse_args(argv)

    try:
        source = args.source or discover_source()
        targets = tuple(args.targets) if args.targets else TARGET
        source_counts = count_source_steps(source, targets)
        ctf_counts = count_ctf_steps(args.stage1)
    except (CoverageInputError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return render_report(source_counts, ctf_counts, targets)


if __name__ == "__main__":
    raise SystemExit(main())
