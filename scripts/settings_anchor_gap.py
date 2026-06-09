"""Read-only static decomposition of 23.Settings automation candidates.

Joins the ALT Basic audit join-CSV (EXPORT_TO_APPIUM rows for sheet
`23.Settings`) with the source Excel procedure text and the current device
menu-tree baseline, then classifies each TC's menu-tree *anchor gap*.

Hard guarantees:
- READ-ONLY. Never modifies the Excel, the CSV, the baseline, or the seed.
- NO device / ADB / Appium call. NO openpyxl import at module load.
- Entry points reachable only via deep-link/component are recorded as
  *_CANDIDATE — never promoted to a confirmed entry point before device
  measurement.
- This is a STATIC PROXY classification, not a device-validated result. It
  does not claim FULL_AUTO / RUNNABLE_NOW / automation-rate increases, and
  does not transfer FocusRule/Appium evidence onto ALT Basic TCs.

The pure parser / classifier functions carry no IO and are unit-tested with
synthetic inputs. Excel/CSV/baseline loading + report emission live in the
`load_*` / `main` helpers at the bottom.
"""
from __future__ import annotations

import argparse
import collections
import csv as _csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Pure: menu path parsing
# ---------------------------------------------------------------------------

# Tokens that trail a menu noun describing the *action* on it, not the node.
# Stripped from the end of a path segment so "검색 TAP 하드키" -> "검색".
_ACTION_TOKENS = {
    "TAP", "Tap", "tap",
    "터치", "하드키", "하드", "키",
    "진입", "선택", "클릭", "탭", "누름", "누르기", "실행", "이동",
}
_STEP_PREFIX_RE = re.compile(r"^\s*\d+\s*[.),]\s*")
_QUOTE_CHARS = "\"'“”‘’`"


def _clean_segment(seg: str) -> str:
    # Strip repeated step prefixes (e.g. "1. 1. 설정" -> "설정"; "1, 설정" -> "설정").
    prev = None
    while prev != seg:
        prev = seg
        seg = _STEP_PREFIX_RE.sub("", seg).strip()
    seg = seg.strip(_QUOTE_CHARS).strip()
    # Drop trailing action tokens (e.g. "네트워크 및 인터넷 진입" -> "네트워크 및 인터넷").
    tokens = seg.split()
    while tokens and tokens[-1].strip(_QUOTE_CHARS) in _ACTION_TOKENS:
        tokens.pop()
    return " ".join(tokens).strip(_QUOTE_CHARS).strip()


def parse_menu_path(procedure: Optional[str]) -> List[str]:
    """Extract the deepest ``설정 > A > B`` menu path from a procedure cell.

    Returns the cleaned segment list (e.g. ``["설정", "앱", "모두 보기"]``) or an
    empty list when no ``>``-separated path is present.
    """
    if not procedure or not str(procedure).strip():
        return []
    best_rooted: List[str] = []
    best_rooted_sep = -1
    best_any: List[str] = []
    best_any_sep = -1
    for line in str(procedure).splitlines():
        if ">" not in line:
            continue
        segs = [_clean_segment(s) for s in line.split(">")]
        segs = [s for s in segs if s]
        if not segs:
            continue
        sep = line.count(">")
        if segs[0] == "설정" and sep > best_rooted_sep:
            best_rooted, best_rooted_sep = segs, sep
        if sep > best_any_sep:
            best_any, best_any_sep = segs, sep
    # Prefer the deepest 설정-rooted line; only fall back to a non-rooted line
    # (a procedure that never names the Settings root) when none exists.
    return best_rooted if best_rooted else best_any


def compute_depth(path: List[str]) -> int:
    """Number of menu levels below the root ``설정`` node."""
    if not path:
        return 0
    return len(path) - 1 if path[0] == "설정" else len(path)


# ---------------------------------------------------------------------------
# Pure: per-TC trait classifiers (text-input / focus-nav / mutation)
# ---------------------------------------------------------------------------

_INPUT_CUE = re.compile(r"(검색|입력|키보드|쿼티|IME|천지인|타이핑)")
_FOCUS_CUE = re.compile(r"(하드 ?키|방향키|포커스|focus|D-?pad|확인키|상하 ?키)", re.I)
_MUTATION_CUE = re.compile(
    r"(켜기|끄기|토글|\bON\b|\bOFF\b|\bOn\b|\bOff\b|추가|삭제|적용|변경|전환|"
    r"사용 ?설정|사용 ?안|등록|해제|초기화|재설정|활성화|비활성화)"
)
# Result-form state change in the *expected result* — a state-change verb in a
# *declarative* result ending (된다/됐다/되었다/됨/됩니다). The declarative form is
# what distinguishes a mutation the test performs ("밝기가 0% 설정된다") from a state
# observation ("설정되어 있음") or an adnominal noun ("설정된 시간으로 노출된다"). And
# observation/navigation verbs are excluded — 노출/표시/확인/진입, and 전환 (which in
# this corpus is "…화면으로 전환된다" navigation, not a persistent change) — so menu
# lists and screen transitions are NOT misread as mutations.
_MUTATION_RESULT_CUE = re.compile(
    r"(변경|추가|삭제|적용|해제|초기화|재설정|저장|등록|설정|변환|복원|갱신)"
    r"\s*(된다|됐다|되었다|됩니다|됨)"
)


def text_input_required(proc_text: Optional[str], csv_safety: Optional[str]) -> bool:
    """True when reaching/verifying the TC needs on-screen text entry.

    Sourced from the CSV ``safety_class`` prior (``INPUT_REQUIRED``) or a
    keyboard/search cue in the procedure text.
    """
    if (csv_safety or "").strip() == "INPUT_REQUIRED":
        return True
    return bool(_INPUT_CUE.search(proc_text or ""))


def focus_nav_required(proc_text: Optional[str]) -> bool:
    """True when the procedure relies on hard-key / directional focus movement."""
    return bool(_FOCUS_CUE.search(proc_text or ""))


def mutation_suspected(
    proc_text: Optional[str], expected_text: Optional[str] = None
) -> bool:
    """True when the procedure or expected result implies a state change.

    The procedure side catches imperative mutation cues; the expected-result
    side catches result-form state changes ("이름이 변경된다") that never appear in
    the procedure (e.g. a rename whose procedure only navigates + taps). A flag
    only — mutation-suspected TCs are NOT promoted to probe priority.
    """
    if _MUTATION_CUE.search(proc_text or ""):
        return True
    return bool(expected_text and _MUTATION_RESULT_CUE.search(expected_text))


# ---------------------------------------------------------------------------
# Pure: baseline index + anchor resolution + entry method
# ---------------------------------------------------------------------------

_LABEL_SPLIT_RE = re.compile(r"\s*[/·,]\s*")


def _norm(s: Optional[str]) -> str:
    """Spacing/case-insensitive key for fuzzy-equal Korean label matching."""
    return re.sub(r"\s+", "", (s or "")).strip().lower()


def _flatten_observed(observed) -> List[str]:
    if isinstance(observed, dict):
        out: List[str] = []
        for key in ("ko", "en", "other"):
            out.extend(observed.get(key) or [])
        return out
    if isinstance(observed, list):
        return list(observed)
    return []


def build_baseline_index(baseline: dict) -> dict:
    """Map every d1 area alias of the menu-tree baseline to its screen record.

    Aliases come from ``nav_path[1]`` and the ``/ · ,``-split ``label_ko``. The
    record carries the screen's flattened ``observed_texts`` (and a spacing-
    insensitive variant) plus reach/entry provenance used by anchor resolution
    and entry-method classification.
    """
    index: dict = {}
    for screen in baseline.get("screens", []):
        aliases = set()
        nav = screen.get("nav_path") or []
        if len(nav) >= 2:
            aliases.add(nav[1])
        label = screen.get("label_ko")
        if label:
            for part in _LABEL_SPLIT_RE.split(label):
                part = part.strip()
                if part:
                    aliases.add(part)
        observed = _flatten_observed(screen.get("observed_texts"))
        entry = screen.get("entry") or {}
        rec = {
            "screen_id": screen.get("screen_id"),
            "observed_texts": set(observed),
            "observed_norm": {_norm(t) for t in observed},
            "reach_status": screen.get("reach_status"),
            "entry_method": entry.get("method"),
            "entry_action": entry.get("action"),
            "entry_component": entry.get("component"),
        }
        for alias in aliases:
            index[alias] = rec
    return index


def _lookup_screen(area: Optional[str], index: dict) -> Optional[dict]:
    if not area:
        return None
    if area in index:
        return index[area]
    na = _norm(area)
    for key, rec in index.items():
        if _norm(key) == na:
            return rec
    return None


def _area_of(path: List[str]) -> Optional[str]:
    if not path:
        return None
    if path[0] == "설정" and len(path) >= 2:
        return path[1]
    return path[0]


_REACHED = {"REACHED", "REACHED_EXTERNAL_PACKAGE"}


def resolve_anchor(path: List[str], index: dict) -> dict:
    """Classify a menu path against the baseline as RESOLVED/PARTIAL/MISSING/UNKNOWN.

    The 17-screen baseline is a *shallow single-pass* observation; absence of a
    leaf string is recorded as PARTIAL ("may exist deeper"), never as proof the
    leaf does not exist. Confidence stays capped accordingly.
    """
    if not path:
        return {
            "baseline_screen_id": None,
            "anchor_state": "UNKNOWN",
            "anchor_reason": "no parseable menu path",
            "confidence": 0.0,
        }
    area = _area_of(path)
    leaf = path[-1]
    depth = compute_depth(path)
    rec = _lookup_screen(area, index)
    if rec is None:
        return {
            "baseline_screen_id": None,
            "anchor_state": "MISSING",
            "anchor_reason": f"no baseline d1 screen for area '{area}'",
            "confidence": 0.3,
        }
    screen_id = rec["screen_id"]
    reached = rec["reach_status"] in _REACHED
    if depth <= 1:
        if reached:
            state, reason, conf = (
                "TARGET_REACHED",
                "d1 target screen reached in baseline",
                0.7,
            )
        else:
            state, reason, conf = (
                "PARTIAL",
                f"d1 screen in baseline but reach_status={rec['reach_status']}",
                0.4,
            )
    elif _norm(leaf) in rec["observed_norm"]:
        if reached:
            state, reason, conf = (
                "LEAF_LABEL_OBSERVED",
                "leaf label seen in d1 single-pass observation (label only, target not entered)",
                0.7,
            )
        else:
            state, reason, conf = (
                "PARTIAL",
                f"leaf label seen but screen reach_status={rec['reach_status']}",
                0.5,
            )
    else:
        state, reason, conf = (
            "PARTIAL",
            "d1 screen in baseline; leaf not in single-pass observation (may exist deeper)",
            0.4,
        )
    return {
        "baseline_screen_id": screen_id,
        "anchor_state": state,
        "anchor_reason": reason,
        "confidence": conf,
    }


def classify_entry_method(path: List[str], proc_text: Optional[str], index: dict):
    """Return ``(entry_method, entry_evidence)``.

    Deep-link / component entries are device-grounded in the baseline only at
    the d1 level, so they are labelled ``*_CANDIDATE`` — the specific leaf entry
    is never promoted to a confirmed entry point before device measurement.
    """
    if focus_nav_required(proc_text):
        return "HARDKEY_NAVIGATION", "hard-key / directional focus cue in procedure"
    if path and any(seg == "검색" for seg in path):
        return "SEARCH_CANDIDATE", "reached via Settings 검색 in menu path"
    if not path:
        return "UNKNOWN", "no parseable menu path"
    rec = _lookup_screen(_area_of(path), index)
    if rec is not None:
        method = rec.get("entry_method")
        if method == "deeplink":
            return (
                "DEEPLINK_CANDIDATE",
                f"baseline launched {rec.get('entry_action')} (d1 candidate; leaf unconfirmed)",
            )
        if method == "component":
            return (
                "COMPONENT_CANDIDATE",
                f"baseline component {rec.get('entry_component')} (d1 candidate; leaf unconfirmed)",
            )
    return "MENU_NAVIGATION", "no baseline deep-link for area; tap-navigation required"


_ANCHOR_RESOLVED_STATES = ("TARGET_REACHED", "LEAF_LABEL_OBSERVED")


def recommend_probe(
    anchor_state: str, mutation_suspected_flag: bool, text_input_required_flag: bool
) -> str:
    """Pick a *menu-tree deepening* bucket for the TC's anchor.

    Scope: this decides whether the menu-tree baseline needs deepening to ground
    the anchor — NOT whether the TC as a whole is verified. Anchor-resolved TCs
    (target reached OR leaf label already in baseline observation) need no
    further deepening. Among the GAP candidates (PARTIAL / MISSING),
    mutation-suspected and input-required TCs are deferred, not promoted, so
    device exploration is driven by clean read-only navigation gaps.
    """
    if anchor_state in _ANCHOR_RESOLVED_STATES:
        return "NO_ANCHOR_DEEPEN_NEEDED"
    if anchor_state == "UNKNOWN":
        return "REVIEW_SOURCE"
    if mutation_suspected_flag:
        return "PROBE_DEFER_MUTATION"
    if text_input_required_flag:
        return "PROBE_DEFER_INPUT"
    if anchor_state == "PARTIAL":
        return "PROBE_PRIORITY_HIGH"
    if anchor_state == "MISSING":
        return "PROBE_PRIORITY_MEDIUM"
    return "REVIEW_SOURCE"


# ---------------------------------------------------------------------------
# Pure: per-TC record assembly (locked output schema)
# ---------------------------------------------------------------------------

FIELDNAMES = (
    "tc_id",
    "title",
    "source_sheet",
    "source_row",
    "area",
    "menu_path",
    "depth",
    "entry_method",
    "entry_evidence",
    "text_input_required",
    "focus_nav_required",
    "mutation_suspected",
    "baseline_screen_id",
    "anchor_state",
    "anchor_reason",
    "confidence",
    "recommended_probe",
)


def _title_area(title: Optional[str]) -> str:
    if not title:
        return ""
    return title.split("/")[-1].strip()


def enrich_row(
    csv_row: dict,
    proc_text: Optional[str],
    index: dict,
    expected_text: Optional[str] = None,
) -> dict:
    """Assemble the locked 17-field decomposition record for one TC."""
    safety = csv_row.get("safety_class")
    path = parse_menu_path(proc_text)
    area = _area_of(path) or _title_area(csv_row.get("excel_title"))
    entry_method, entry_evidence = classify_entry_method(path, proc_text, index)
    tir = text_input_required(proc_text, safety)
    fnr = focus_nav_required(proc_text)
    mut = mutation_suspected(proc_text, expected_text)
    anchor = resolve_anchor(path, index)
    rec = {
        "tc_id": csv_row.get("excel_tc_id"),
        "title": csv_row.get("excel_title"),
        "source_sheet": csv_row.get("source_sheet"),
        "source_row": csv_row.get("source_row_range"),
        "area": area,
        "menu_path": " > ".join(path),
        "depth": compute_depth(path),
        "entry_method": entry_method,
        "entry_evidence": entry_evidence,
        "text_input_required": tir,
        "focus_nav_required": fnr,
        "mutation_suspected": mut,
        "baseline_screen_id": anchor["baseline_screen_id"],
        "anchor_state": anchor["anchor_state"],
        "anchor_reason": anchor["anchor_reason"],
        "confidence": anchor["confidence"],
        "recommended_probe": recommend_probe(anchor["anchor_state"], mut, tir),
    }
    return rec


# ---------------------------------------------------------------------------
# IO: join key / loaders / record build / reports / main
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"#?([\d.]+)$")
_EXPORT_ACTION = "EXPORT_TO_APPIUM"
_SETTINGS_SHEET = "23.Settings"

_DEFAULT_CSV = "THOR2 - ALT Basic TC Audit/overlap_join_2026-06-08.csv"
_DEFAULT_EXCEL = "doc/[THOR 2] ALT Basic Test Case_FULL.xlsx"
_DEFAULT_BASELINE = "THOR2_K - Settings/catalog/menu_tree_baseline_20260604T102316Z.json"
_DEFAULT_OUT_CSV = "THOR2 - ALT Basic TC Audit/settings_anchor_gap_enriched_2026-06-09.csv"
_DEFAULT_OUT_MD = "THOR2 - ALT Basic TC Audit/SETTINGS_ANCHOR_GAP_SUMMARY_2026-06-09.md"


def _join_key(raw) -> str:
    """Canonical join key shared by CSV ``excel_tc_id`` and Excel ``TC ID``."""
    s = str(raw).strip()
    m = _NUM_RE.search(s)
    if m:
        s = m.group(1)
    try:
        f = float(s)
        return f"{f:g}.0" if f == int(f) else str(f)
    except ValueError:
        return s


def _sort_key(tc_id: Optional[str]) -> float:
    try:
        return float(_join_key(tc_id))
    except ValueError:
        return float("inf")


def load_export_rows(csv_path: str) -> List[dict]:
    """Return the 23.Settings EXPORT_TO_APPIUM rows from the audit join CSV."""
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    return [
        r
        for r in rows
        if r.get("source_sheet") == _SETTINGS_SHEET
        and r.get("recommended_next_action") == _EXPORT_ACTION
    ]


def load_excel_texts(xlsx_path: str, sheet: str = _SETTINGS_SHEET) -> Dict[str, dict]:
    """Map ``TC ID`` -> ``{"proc": ..., "expected": ...}``.

    Folds continuation rows (blank TC ID) into their owning TC for both the
    procedure (col E) and expected-result (col F) columns. Read-only; the source
    workbook is never modified. ``openpyxl`` is imported lazily so the pure
    functions above never require it.
    """
    import openpyxl  # lazy: not needed by pure functions / most tests

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        texts: Dict[str, dict] = {}
        last_key: Optional[str] = None
        for row in ws.iter_rows(min_row=2, values_only=True):
            tid = row[0] if len(row) > 0 else None
            proc = row[4] if len(row) > 4 else None
            exp = row[5] if len(row) > 5 else None
            proc_text = "" if proc is None else str(proc).strip()
            exp_text = "" if exp is None else str(exp).strip()
            if tid is not None and str(tid).strip():
                key = _join_key(tid)
                texts[key] = {"proc": proc_text, "expected": exp_text}
                last_key = key
            elif last_key is not None and (proc_text or exp_text):
                rec = texts[last_key]
                if proc_text:
                    rec["proc"] = (rec["proc"] + "\n" + proc_text).strip()
                if exp_text:
                    rec["expected"] = (rec["expected"] + "\n" + exp_text).strip()
        return texts
    finally:
        wb.close()


def load_baseline_index(baseline_path: str) -> Tuple[dict, Optional[str]]:
    """Load the baseline JSON and return ``(index, run_id)``."""
    data = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    return build_baseline_index(data), data.get("run_id")


def build_records(rows: List[dict], text_map: Dict[str, dict], index: dict) -> List[dict]:
    """Join each export row to its Excel text and emit sorted enriched records."""
    records = []
    for row in rows:
        texts = text_map.get(_join_key(row.get("excel_tc_id")), {})
        records.append(
            enrich_row(
                row,
                texts.get("proc", ""),
                index,
                expected_text=texts.get("expected", ""),
            )
        )
    records.sort(key=lambda r: _sort_key(r["tc_id"]))
    return records


def write_enriched_csv(records: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=list(FIELDNAMES), lineterminator="\n")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def _count(records: List[dict], field: str) -> List[Tuple[str, int]]:
    ctr = collections.Counter(str(r[field]) for r in records)
    return sorted(ctr.items(), key=lambda kv: (-kv[1], kv[0]))


def render_summary_md(records: List[dict], meta: dict) -> str:
    """Render the deterministic decomposition summary (no wall-clock timestamp)."""
    L: List[str] = []
    L.append("# 23.Settings Menu-Tree Anchor-Gap Decomposition")
    L.append("")
    L.append("> STATIC PROXY classification — NOT device-validated. No FULL_AUTO /")
    L.append("> RUNNABLE_NOW / automation-rate claim. FocusRule/Appium evidence is NOT")
    L.append("> transferred. Expected text is NOT device-observed text. Deep-link /")
    L.append("> component entries are *_CANDIDATE until device measurement.")
    L.append("")
    L.append("## Population & filter")
    L.append(f"- source CSV: `{meta['csv_path']}`")
    L.append(f"- source Excel (read-only): `{meta['excel_path']}`")
    L.append(f"- baseline: `{meta['baseline_path']}` (run_id `{meta['baseline_run_id']}`)")
    L.append(
        f"- filter: `source_sheet={_SETTINGS_SHEET}` AND "
        f"`recommended_next_action={_EXPORT_ACTION}`"
    )
    L.append(
        f"- population: **{meta['population']}** TC · Excel join "
        f"{meta['matched']}/{meta['population']} (missing {meta['missing']})"
    )
    L.append("")

    # area × anchor_state matrix
    states = ["TARGET_REACHED", "LEAF_LABEL_OBSERVED", "PARTIAL", "MISSING", "UNKNOWN"]
    by_area: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in records:
        by_area[r["area"]][r["anchor_state"]] += 1
    L.append("## area × anchor_state")
    L.append("> TARGET_REACHED = d1 target screen reached. LEAF_LABEL_OBSERVED = leaf")
    L.append("> label seen in the d1 single-pass observation only (label, not a reached")
    L.append("> target). Neither requires menu-tree deepening.")
    L.append("| area | TARGET_REACHED | LEAF_LABEL_OBSERVED | PARTIAL | MISSING | UNKNOWN | total |")
    L.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for area in sorted(by_area):
        c = by_area[area]
        tot = sum(c.values())
        cells = " | ".join(str(c[s]) for s in states)
        L.append(f"| {area} | {cells} | {tot} |")
    overall = collections.Counter(r["anchor_state"] for r in records)
    all_cells = " | ".join(str(overall[s]) for s in states)
    L.append(f"| **ALL** | {all_cells} | {len(records)} |")
    L.append("")

    def _block(title: str, field: str) -> None:
        L.append(f"## {title}")
        for k, v in _count(records, field):
            L.append(f"- {k}: {v}")
        L.append("")

    L.append("## depth distribution")
    depth_ctr = collections.Counter(r["depth"] for r in records)
    for d in sorted(depth_ctr):
        L.append(f"- depth {d}: {depth_ctr[d]}")
    L.append("")
    _block("entry_method distribution", "entry_method")
    _block("recommended_probe distribution", "recommended_probe")

    tir = sum(1 for r in records if r["text_input_required"])
    fnr = sum(1 for r in records if r["focus_nav_required"])
    mut = sum(1 for r in records if r["mutation_suspected"])
    L.append("## trait counts")
    L.append(f"- text_input_required: {tir}")
    L.append(f"- focus_nav_required: {fnr}")
    L.append(f"- mutation_suspected: {mut}")
    L.append("")

    # baseline-deepen recommendation: areas ranked by clean (non-mutation,
    # non-input) PARTIAL+MISSING gaps — the high-yield read-only probe targets.
    deepen: Dict[str, int] = collections.Counter()
    for r in records:
        if r["recommended_probe"] in ("PROBE_PRIORITY_HIGH", "PROBE_PRIORITY_MEDIUM"):
            deepen[r["area"]] += 1
    L.append("## baseline-deepen recommendation (clean read-only gaps by area)")
    if deepen:
        for area, n in sorted(deepen.items(), key=lambda kv: (-kv[1], kv[0])):
            L.append(f"- {area}: {n}")
    else:
        L.append("- (none)")
    L.append("")
    L.append("## heuristic limits")
    L.append("- menu_path / depth parsed from Korean procedure text (deepest 설정-rooted `>` line).")
    L.append("- entry_method beyond hard-key/search is baseline-derived candidacy only.")
    L.append("- baseline is a shallow single-pass observation; PARTIAL means")
    L.append("  'leaf not observed yet', never 'leaf absent'. Confidence is capped.")
    L.append("- LEAF_LABEL_OBSERVED is a label sighting on the d1 dashboard, NOT a")
    L.append("  reached/verified target — it only means menu-tree deepening is unneeded.")
    L.append("- mutation_suspected reads the expected-result column too (result-form")
    L.append("  state-change verbs); observation verbs (노출/표시) are not mutations.")
    L.append("- deferral (mutation/input) applies to GAP candidates (PARTIAL/MISSING)")
    L.append("  only; anchor-resolved TCs are excluded from deepening regardless.")
    L.append("")
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only static decomposition of 23.Settings anchor gaps."
    )
    parser.add_argument("--csv", default=_DEFAULT_CSV)
    parser.add_argument("--excel", default=_DEFAULT_EXCEL)
    parser.add_argument("--baseline", default=_DEFAULT_BASELINE)
    parser.add_argument("--out-csv", default=_DEFAULT_OUT_CSV)
    parser.add_argument("--out-md", default=_DEFAULT_OUT_MD)
    parser.add_argument("--sheet", default=_SETTINGS_SHEET)
    args = parser.parse_args(argv)

    index, baseline_run_id = load_baseline_index(args.baseline)
    rows = load_export_rows(args.csv)
    text_map = load_excel_texts(args.excel, sheet=args.sheet)
    matched = sum(1 for r in rows if _join_key(r.get("excel_tc_id")) in text_map)
    records = build_records(rows, text_map, index)

    meta = {
        "csv_path": args.csv,
        "excel_path": args.excel,
        "baseline_path": args.baseline,
        "baseline_run_id": baseline_run_id,
        "population": len(rows),
        "matched": matched,
        "missing": len(rows) - matched,
    }
    write_enriched_csv(records, args.out_csv)
    Path(args.out_md).write_text(render_summary_md(records, meta), encoding="utf-8")

    overall = collections.Counter(r["anchor_state"] for r in records)
    sys.stdout.write(
        f"population={len(rows)} join={matched}/{len(rows)} "
        f"TARGET_REACHED={overall['TARGET_REACHED']} "
        f"LEAF_LABEL_OBSERVED={overall['LEAF_LABEL_OBSERVED']} "
        f"PARTIAL={overall['PARTIAL']} MISSING={overall['MISSING']} "
        f"UNKNOWN={overall['UNKNOWN']}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
