# -*- coding: utf-8 -*-
"""
이통3사 단말 규격 코퍼스 인덱서.

규격 PDF/HTML 전량을 스캔해 조문(section) 단위 인덱스를 만든다.
  조문 ID ↔ 제목 ↔ 문서 ↔ 페이지  를 한 파일에 누적한다.

빌드는 1회, 이후 검색은 인덱스만 읽는다 (원본 재파싱 없음).

usage:
  python spec_corpus_index.py build  [--root PATH] [--out PATH] --poppler BIN_DIR
  python spec_corpus_index.py search <질의> [--carrier KT|LGU+|SKT] [--limit N]
  python spec_corpus_index.py doc    <문서명 일부>
  python spec_corpus_index.py stats

산출:
  catalog/corpus_index.json   기계 판독용 (조문 전량)
  catalog/CORPUS_INDEX.md     사람 판독용 (문서 목록 + 조문 수)

주의:
  - KT 한글 PDF는 목차/머리글 페이지의 폰트에 ToUnicode 매핑이 없어 한글이 추출되지 않는다.
    본문 페이지는 정상 추출되므로 본 인덱서는 본문 헤딩만 신뢰한다 (TOC 라인은 배제).
  - 판정 근거로 쓰기 전 원문 페이지를 반드시 확인할 것. 인덱스는 위치 안내용이다.
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 경로 설정

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = Path(HERE).parents[1]
DEFAULT_ROOT = "새 폴더 (2)"
DEFAULT_OUT = os.path.join(os.path.dirname(HERE), "catalog")
POPPLER_ENV = "TC_RUNNER_POPPLER_BIN"

CARRIER_DIR = {
    "KT": "KT",
    "LGU+": "LGU+",
    "THOR3_SKT_Requirements": "SKT",
}

# ---------------------------------------------------------------- 패턴

# 본문 조문 헤딩:  "3.4.4.2. RRC Connection Reconfiguration"  /  "7.13.1. 디바이스 디버그 스크린"
SECTION_RE = re.compile(r"^[ \t]{0,10}(\d{1,2}(?:\.\d{1,3}){0,4})\.?[ \t]+(\S.{0,90}?)[ \t]*$")
# 목차 라인 = 점 리더 또는 끝에 페이지번호만 남는 형태 → 배제
TOC_LEADER_RE = re.compile(r"\.{4,}|[.\u2026]{3,}\s*\d+\s*$")
PAGE_ONLY_RE = re.compile(r"^\d{1,4}$")
# \uac1c\uc815\uc774\ub825 \ud45c\uc758 \ud589\uc740 "1.2.4  2019.06.27 \u2022 ..." \ucc98\ub7fc \uc870\ubb38 \ud5e4\ub529\uacfc \ud615\ud0dc\uac00 \uac19\ub2e4 \u2192 \ub0a0\uc9dc \uc120\ub450\uba74 \ubc30\uc81c
REVHIST_RE = re.compile(r"^\d{4}[.\-/]\s?\d{1,2}[.\-/]\s?\d{1,2}")
HANGUL = re.compile(r"[\uac00-\ud7a3]")
HAN = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")
VERSION_RE = re.compile(r"[Vv](?:er)?[ _.]?(\d+(?:\.\d+){1,3})")


def _run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return p.stdout
    except Exception:
        return b""


def resolve_corpus_root(root):
    requested = Path(root)
    resolved = requested if requested.is_absolute() else REPO_ROOT / requested
    resolved = resolved.resolve()
    try:
        recorded = resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        recorded = resolved.as_posix()
    return resolved, recorded


def resolve_poppler_tools(poppler, environ=None):
    environment = os.environ if environ is None else environ
    configured = poppler or environment.get(POPPLER_ENV)
    if not configured:
        raise ValueError("build requires --poppler or %s" % POPPLER_ENV)

    bin_dir = Path(configured).resolve()
    tools = []
    for name in ("pdftotext", "pdfinfo"):
        executable = bin_dir / (name + ".exe")
        if not executable.is_file():
            executable = bin_dir / name
        if not executable.is_file():
            raise ValueError("Poppler executable not found: %s" % name)
        tools.append(executable)
    return tuple(tools)


def page_count(path, pdfinfo):
    out = _run([pdfinfo, path], timeout=90)
    m = re.search(rb"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def lang_of(text):
    ko, han, la = len(HANGUL.findall(text)), len(HAN.findall(text)), len(LATIN.findall(text))
    if ko + han + la == 0:
        return "NO-TEXT"
    if han > ko * 3 and han > 100:
        return "ZH"
    if ko > 200:
        return "KO"
    if la > 400:
        return "EN"
    return "SPARSE"


def is_toc_line(raw, title):
    if TOC_LEADER_RE.search(raw):
        return True
    if PAGE_ONLY_RE.match(title.strip()):
        return True
    if REVHIST_RE.match(title.strip()):
        return True
    # 제목이 비었거나 숫자/기호만
    if not re.search(r"[A-Za-z\uac00-\ud7a3\u4e00-\u9fff]", title):
        return True
    return False


def extract_pdf_sections(path, pdftotext):
    """PDF 본문에서 조문 헤딩을 뽑는다. 반환 (sections, lang, sample_text)."""
    raw = _run([pdftotext, "-layout", "-enc", "UTF-8", path, "-"], timeout=600)
    text = raw.decode("utf-8", "replace")
    pages = text.split("\f")
    sections, seen = [], set()
    for pno, page in enumerate(pages, start=1):
        for line in page.splitlines():
            m = SECTION_RE.match(line)
            if not m:
                continue
            sid, title = m.group(1), m.group(2).strip()
            if is_toc_line(line, title):
                continue
            title = re.sub(r"\s{2,}", " ", title).rstrip(". ")
            if not title:
                continue
            key = (sid, title[:40])
            if key in seen:
                continue
            seen.add(key)
            sections.append({"id": sid, "title": title, "page": pno})
    return sections, lang_of(text), text


def strip_html(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"(?is)<style.*?</style>", "", raw)
    raw = re.sub(r"(?is)<script.*?</script>", "", raw)
    raw = re.sub(r"(?is)<head.*?</head>", "", raw)
    return raw


def extract_html_sections(path):
    raw = strip_html(path)
    sections = []
    for m in re.finditer(r"(?is)<h([1-4])[^>]*>(.*?)</h\1>", raw):
        level = int(m.group(1))
        t = re.sub(r"(?s)<[^>]+>", "", m.group(2))
        t = re.sub(r"\s+", " ", t).strip()
        if not t:
            continue
        sm = re.match(r"^(\d{1,2}(?:\.\d{1,3}){0,4})\.?\s+(.*)$", t)
        if sm:
            sections.append({"id": sm.group(1), "title": sm.group(2).strip(), "page": None,
                             "level": level})
        else:
            sections.append({"id": None, "title": t, "page": None, "level": level})
    body = re.sub(r"(?s)<[^>]+>", " ", raw)
    return sections, lang_of(body)


def build(root, out_dir, *, pdftotext, pdfinfo, recorded_root):
    os.makedirs(out_dir, exist_ok=True)
    docs = []
    targets = []
    for base, _dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        top = rel.split(os.sep)[0]
        if top not in CARRIER_DIR:
            continue
        for fn in files:
            if fn.lower().endswith((".pdf", ".html")):
                targets.append((CARRIER_DIR[top], os.path.join(base, fn)))

    targets.sort(key=lambda t: (t[0], t[1]))
    total = len(targets)
    for i, (carrier, path) in enumerate(targets, start=1):
        relp = os.path.relpath(path, root)
        name = os.path.basename(path)
        sys.stderr.write("[%3d/%d] %s\n" % (i, total, name[:78]))
        sys.stderr.flush()
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
        vm = VERSION_RE.search(name)
        if path.lower().endswith(".pdf"):
            secs, lang, _ = extract_pdf_sections(path, pdftotext)
            pages = page_count(path, pdfinfo)
            kind = "pdf"
        else:
            secs, lang = extract_html_sections(path)
            pages = None
            kind = "html"
        docs.append({
            "carrier": carrier,
            "file": name,
            "rel": relp.replace("\\", "/"),
            "kind": kind,
            "pages": pages,
            "lang": lang,
            "version": vm.group(1) if vm else None,
            "sha256_16": sha,
            "is_sat": ("SAT" in name),
            "section_count": len(secs),
            "sections": secs,
        })

    # byte-identical 중복 표시
    by_sha = {}
    for d in docs:
        by_sha.setdefault(d["sha256_16"], []).append(d["rel"])
    for d in docs:
        grp = by_sha[d["sha256_16"]]
        d["duplicate_of"] = [r for r in grp if r != d["rel"]] or None

    index = {
        "schema_version": 1,
        "tool": "spec_corpus_index-v1",
        "root": recorded_root,
        "doc_count": len(docs),
        "section_count": sum(d["section_count"] for d in docs),
        "docs": docs,
    }
    jp = os.path.join(out_dir, "corpus_index.json")
    io.open(jp, "w", encoding="utf-8").write(json.dumps(index, ensure_ascii=False, indent=1))
    write_markdown(index, os.path.join(out_dir, "CORPUS_INDEX.md"))
    print("built: %s  (%d docs, %d sections)" % (jp, index["doc_count"], index["section_count"]))
    return index


def write_markdown(index, path):
    L = []
    L.append("# 이통3사 단말 규격 코퍼스 인덱스\n")
    L.append("`spec_corpus_index.py build` 산출물. 조문 전량은 `corpus_index.json` 참조.\n")
    L.append("문서 %d건 · 조문 %d건\n" % (index["doc_count"], index["section_count"]))
    L.append("> 인덱스는 **위치 안내용**이다. 판정 근거로 쓰기 전 원문 페이지를 확인할 것.\n")
    for carrier in ("KT", "LGU+", "SKT"):
        ds = [d for d in index["docs"] if d["carrier"] == carrier]
        if not ds:
            continue
        L.append("\n## %s — 문서 %d건\n" % (carrier, len(ds)))
        L.append("| 문서 | 버전 | 페이지 | 언어 | 조문 | SAT | 중복 |")
        L.append("|---|---|---:|---|---:|---|---|")
        for d in sorted(ds, key=lambda x: x["file"]):
            L.append("| %s | %s | %s | %s | %d | %s | %s |" % (
                d["file"].replace("|", "\\|"),
                d["version"] or "—",
                d["pages"] if d["pages"] else "—",
                d["lang"],
                d["section_count"],
                "SAT" if d["is_sat"] else "—",
                "중복" if d["duplicate_of"] else "—",
            ))
    io.open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def load(out_dir):
    p = os.path.join(out_dir, "corpus_index.json")
    if not os.path.exists(p):
        sys.exit("인덱스가 없다. 먼저 `build`를 실행할 것: %s" % p)
    return json.load(io.open(p, encoding="utf-8"))


def cmd_search(args):
    idx = load(args.out)
    q = args.query.lower()
    hits = []
    for d in idx["docs"]:
        if args.carrier and d["carrier"] != args.carrier:
            continue
        for s in d["sections"]:
            if q in s["title"].lower():
                hits.append((d, s))
    if not hits:
        print("일치 조문 없음: %s" % args.query)
        return
    print("조문 %d건 일치 — '%s'\n" % (len(hits), args.query))
    for d, s in hits[:args.limit]:
        loc = "p.%s" % s["page"] if s.get("page") else "—"
        print("  [%-4s] %-9s %-52s  %s  %s" % (
            d["carrier"], s["id"] or "—", s["title"][:52], loc, d["file"][:46]))
    if len(hits) > args.limit:
        print("\n  ... %d건 더 (--limit 조정)" % (len(hits) - args.limit))


def cmd_doc(args):
    idx = load(args.out)
    q = args.name.lower()
    ds = [d for d in idx["docs"] if q in d["file"].lower()]
    if not ds:
        print("일치 문서 없음: %s" % args.name)
        return
    for d in ds:
        print("\n=== %s [%s] ===" % (d["file"], d["carrier"]))
        print("    %s | %s | %s쪽 | 조문 %d | ver %s" % (
            d["rel"], d["lang"], d["pages"], d["section_count"], d["version"] or "—"))
        if d["duplicate_of"]:
            print("    중복(byte-identical): %s" % ", ".join(d["duplicate_of"]))
        for s in d["sections"][:args.limit]:
            loc = "p.%s" % s["page"] if s.get("page") else "—"
            print("      %-10s %-58s %s" % (s["id"] or "—", s["title"][:58], loc))
        if d["section_count"] > args.limit:
            print("      ... %d건 더" % (d["section_count"] - args.limit))


def cmd_stats(args):
    idx = load(args.out)
    print("문서 %d · 조문 %d\n" % (idx["doc_count"], idx["section_count"]))
    for carrier in ("KT", "LGU+", "SKT"):
        ds = [d for d in idx["docs"] if d["carrier"] == carrier]
        if not ds:
            continue
        langs = {}
        for d in ds:
            langs[d["lang"]] = langs.get(d["lang"], 0) + 1
        print("%-5s 문서 %3d · 조문 %5d · SAT %2d · 중복 %2d · %s" % (
            carrier, len(ds), sum(d["section_count"] for d in ds),
            sum(1 for d in ds if d["is_sat"]),
            sum(1 for d in ds if d["duplicate_of"]),
            langs))


def main():
    ap = argparse.ArgumentParser(description="이통3사 규격 코퍼스 인덱서")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="코퍼스 전수 인덱싱")
    b.add_argument("--root", default=DEFAULT_ROOT)
    b.add_argument("--out", default=DEFAULT_OUT)
    b.add_argument(
        "--poppler",
        help="Poppler bin directory (or set %s)" % POPPLER_ENV,
    )

    s = sub.add_parser("search", help="조문 제목 검색")
    s.add_argument("query")
    s.add_argument("--carrier", choices=["KT", "LGU+", "SKT"])
    s.add_argument("--limit", type=int, default=40)
    s.add_argument("--out", default=DEFAULT_OUT)

    d = sub.add_parser("doc", help="문서 1건의 조문 목록")
    d.add_argument("name")
    d.add_argument("--limit", type=int, default=60)
    d.add_argument("--out", default=DEFAULT_OUT)

    t = sub.add_parser("stats", help="코퍼스 통계")
    t.add_argument("--out", default=DEFAULT_OUT)

    a = ap.parse_args()
    if a.cmd == "build":
        try:
            root, recorded_root = resolve_corpus_root(a.root)
            pdftotext, pdfinfo = resolve_poppler_tools(a.poppler)
        except (OSError, ValueError) as error:
            ap.error(str(error))
        build(
            root,
            a.out,
            pdftotext=pdftotext,
            pdfinfo=pdfinfo,
            recorded_root=recorded_root,
        )
    elif a.cmd == "search":
        cmd_search(a)
    elif a.cmd == "doc":
        cmd_doc(a)
    elif a.cmd == "stats":
        cmd_stats(a)


if __name__ == "__main__":
    main()
