"""LGU+ HTML을 구조 마커가 보존된 텍스트로 변환한다."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


def html_to_text(raw: str) -> str:
    """HTML 문자열을 H1~H4 구조 마커가 포함된 평문으로 변환한다."""
    # drop style/script (contains megabytes of base64 fonts)
    raw = re.sub(r"(?is)<style.*?</style>", "", raw)
    raw = re.sub(r"(?is)<script.*?</script>", "", raw)
    raw = re.sub(r"(?is)<head.*?</head>", "", raw)
    # images -> placeholder with alt
    raw = re.sub(r'(?is)<img[^>]*alt="([^"]*)"[^>]*>', r"[IMG: \1]", raw)
    raw = re.sub(r"(?is)<img[^>]*>", "[IMG]", raw)

    # structural markers
    raw = re.sub(r"(?i)<h1[^>]*>", "\n\n##H1## ", raw)
    raw = re.sub(r"(?i)<h2[^>]*>", "\n\n##H2## ", raw)
    raw = re.sub(r"(?i)<h3[^>]*>", "\n\n##H3## ", raw)
    raw = re.sub(r"(?i)<h4[^>]*>", "\n\n##H4## ", raw)
    raw = re.sub(r"(?i)</h[1-6]>", "\n", raw)
    raw = re.sub(r"(?i)<table[^>]*>", "\n[TABLE]\n", raw)
    raw = re.sub(r"(?i)</table>", "\n[/TABLE]\n", raw)
    raw = re.sub(r"(?i)</tr>", "\n", raw)
    raw = re.sub(r"(?i)<t[dh][^>]*>", " | ", raw)
    raw = re.sub(r"(?i)<li[^>]*>", "\n  - ", raw)
    raw = re.sub(r"(?i)</p>", "\n", raw)
    raw = re.sub(r"(?i)<br[^>]*>", "\n", raw)
    raw = re.sub(r"(?i)<figcaption[^>]*>", "\n[CAP] ", raw)

    raw = re.sub(r"(?s)<[^>]+>", "", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\xa0]+", " ", raw)
    raw = re.sub(r" *\n *", "\n", raw)
    return re.sub(r"\n{3,}", "\n\n", raw)


def convert_file(source: Path, destination: Path) -> str:
    converted = html_to_text(source.read_text(encoding="utf-8"))
    destination.write_text(converted, encoding="utf-8")
    return converted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)

    converted = convert_file(args.source, args.destination)
    print(args.destination, len(converted), "chars", converted.count("\n"), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
