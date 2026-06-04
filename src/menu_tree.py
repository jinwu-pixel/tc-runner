"""Canonical device-sourced Settings menu-tree baseline (v1).

Pure & device-independent: dataclasses + classifiers + JSON/MD emitters.
MUST NOT import scripts.menu_mapper (layering: src must not depend on scripts).
The driver parses nodes via scripts.menu_mapper and passes node dicts +
denylist booleans into build_element().
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1
TOOL_VERSION = "menu-tree-baseline-v1"

_TOGGLE_CLASSES = {
    "android.widget.Switch", "android.widget.CheckBox", "android.widget.RadioButton",
}
_INPUT_CLASSES = {"android.widget.EditText", "android.widget.AutoCompleteTextView"}


def detect_script(text: str) -> str:
    """Bucket a label by dominant script: 'ko' (Hangul) > 'en' (Latin) > 'other'."""
    for c in text:
        if "가" <= c <= "힣" or "ᄀ" <= c <= "ᇿ":
            return "ko"
    has_latin = any("a" <= c.lower() <= "z" for c in text)
    has_cjk_or_kana = any(ord(c) >= 0x3000 for c in text)
    if has_latin and not has_cjk_or_kana:
        return "en"
    return "other"


def classify_kind(node: dict) -> str:
    cls = node.get("class", "")
    if node.get("checkable") == "true" or cls in _TOGGLE_CLASSES:
        return "toggle"
    if cls in _INPUT_CLASSES:
        return "input"
    if cls == "android.widget.Button":
        return "button"
    clickable = node.get("clickable") == "true" or node.get("inherited_clickable") == "true"
    focusable = node.get("focusable") == "true" or node.get("inherited_focusable") == "true"
    label = node.get("text") or node.get("content-desc") or ""
    if clickable or focusable:
        return "menu_row"
    if label:
        return "title"
    return "unknown"


def text_role_hint(node: dict) -> str:
    rid = node.get("resource-id", "") or ""
    if rid.endswith("/title") or rid.endswith(":id/title"):
        return "primary"
    if "summary" in rid:
        return "summary"
    return "unknown"


@dataclass
class MenuElement:
    label: str
    resource_id: str | None
    kind: str
    source_class: str
    text_role_hint: str
    clickable: bool
    focusable: bool
    checkable: bool
    risk: str
    bounds: str | None = None


def build_element(node: dict, denylisted: bool) -> MenuElement:
    label = node.get("text") or node.get("content-desc") or ""
    kind = classify_kind(node)
    cls = node.get("class", "")
    checkable = node.get("checkable") == "true"
    if denylisted:
        risk = "denylist"
    elif cls in _TOGGLE_CLASSES:
        risk = "toggle"
    elif checkable:
        risk = "checkable"
    else:
        risk = "none"
    return MenuElement(
        label=label,
        resource_id=(node.get("resource-id") or None),
        kind=kind,
        source_class=cls,
        text_role_hint=text_role_hint(node),
        clickable=node.get("clickable") == "true",
        focusable=node.get("focusable") == "true",
        checkable=checkable,
        risk=risk,
        bounds=(node.get("bounds") or None),
    )


def bucket_texts(elements: list[MenuElement]) -> dict:
    buckets: dict[str, set] = {"ko": set(), "en": set(), "other": set()}
    for e in elements:
        if not e.label:
            continue
        buckets[detect_script(e.label)].add(e.label)
    return {k: sorted(v) for k, v in buckets.items()}


import json


@dataclass
class ScrollInfo:
    passes: int = 0
    swipes: list[dict] = field(default_factory=list)
    new_texts_per_pass: list[int] = field(default_factory=list)
    terminated: str = "no_new"


@dataclass
class DumpInfo:
    dump_error: str | None = None
    dump_size: int = 0
    raw_present: bool = False


@dataclass
class MenuScreen:
    screen_id: str
    label_ko: str
    nav_path: list[str]
    entry: dict
    reach_status: str
    reach_kind: str | None
    observed_focus: str
    expect_activity_regex: str
    activity_match: bool
    fingerprint: str | None
    observed_texts: dict
    elements: list[MenuElement]
    scroll: ScrollInfo
    dump_info: DumpInfo
    risk_flags: list[str]
    raw_dump_ref: str | None


@dataclass
class DeviceBaseline:
    serial: str
    model: str
    product: str
    device: str
    build_fingerprint: str
    build_id: str
    android: str
    locale_persist: str
    locale_product: str
    viewport: str
    dpi: str
    sim: str


_REACH_STATUSES = (
    "REACHED", "REACHED_EXTERNAL_PACKAGE", "UNREACHABLE_NO_ACTION",
    "LAUNCH_FAILED", "FOCUS_MISMATCH", "DUMP_REJECTED",
)


def compute_summary(screens: list[MenuScreen]) -> dict:
    status_count = {s: 0 for s in _REACH_STATUSES}
    for sc in screens:
        status_count[sc.reach_status] = status_count.get(sc.reach_status, 0) + 1
    return {
        "screen_count": len(screens),
        "reached": status_count["REACHED"],
        "reached_external": sum(1 for sc in screens if sc.reach_kind == "external"),
        "unreachable": status_count["UNREACHABLE_NO_ACTION"],
        "launch_failed": status_count["LAUNCH_FAILED"],
        "focus_mismatch": status_count["FOCUS_MISMATCH"],
        "dump_rejected": status_count["DUMP_REJECTED"],
        "denylist_recorded": sum(len(sc.risk_flags) for sc in screens),
        "observed_texts_total": sum(
            len(v) for sc in screens for v in sc.observed_texts.values()),
        "scroll_passes_total": sum(sc.scroll.passes for sc in screens),
    }


def _element_dict(e: MenuElement) -> dict:
    return {
        "label": e.label, "resource_id": e.resource_id, "kind": e.kind,
        "source_class": e.source_class, "text_role_hint": e.text_role_hint,
        "clickable": e.clickable, "focusable": e.focusable, "checkable": e.checkable,
        "risk": e.risk, "bounds": e.bounds,
    }


def _screen_dict(sc: MenuScreen) -> dict:
    return {
        "screen_id": sc.screen_id, "label_ko": sc.label_ko, "nav_path": sc.nav_path,
        "entry": sc.entry, "reach_status": sc.reach_status, "reach_kind": sc.reach_kind,
        "observed_focus": sc.observed_focus, "expect_activity_regex": sc.expect_activity_regex,
        "activity_match": sc.activity_match, "fingerprint": sc.fingerprint,
        "observed_texts": sc.observed_texts,
        "elements": [_element_dict(e) for e in sc.elements],
        "scroll": {"passes": sc.scroll.passes, "swipes": sc.scroll.swipes,
                   "new_texts_per_pass": sc.scroll.new_texts_per_pass,
                   "terminated": sc.scroll.terminated},
        "dump_info": {"dump_error": sc.dump_info.dump_error, "dump_size": sc.dump_info.dump_size,
                      "raw_present": sc.dump_info.raw_present},
        "risk_flags": sc.risk_flags, "raw_dump_ref": sc.raw_dump_ref,
    }


@dataclass
class MenuTreeBaseline:
    schema_version: int
    tool_version: str
    generated_at_utc: str
    run_id: str
    device: DeviceBaseline
    package: str
    seed_ref: dict
    target_mismatch_ack: bool
    summary: dict
    screens: list[MenuScreen]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "tool_version": self.tool_version,
            "generated_at_utc": self.generated_at_utc, "run_id": self.run_id,
            "device": self.device.__dict__, "package": self.package,
            "seed_ref": self.seed_ref, "target_mismatch_ack": self.target_mismatch_ack,
            "summary": self.summary, "screens": [_screen_dict(s) for s in self.screens],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    def to_md(self) -> str:
        d = self.device
        lines = [
            "# Settings Menu Tree Baseline",
            "",
            f"- run_id: `{self.run_id}` · generated_at_utc: `{self.generated_at_utc}`",
            f"- device: {d.model} `{d.serial}` · build `{d.build_id}` · {d.locale_persist}"
            f" · {d.viewport}@{d.dpi} · SIM {d.sim}",
            f"- package: `{self.package}` · schema v{self.schema_version} ({self.tool_version})",
            "",
            "## Summary",
            "```yaml",
        ]
        for k, v in self.summary.items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("")
        for sc in self.screens:
            lines.append(f"## {sc.label_ko}  (`{sc.screen_id}`)")
            lines.append(f"- nav_path: {' → '.join(sc.nav_path)}")
            lines.append(f"- reach: `{sc.reach_status}` (kind={sc.reach_kind}) · "
                         f"focus `{sc.observed_focus}` · fp `{sc.fingerprint}`")
            counts = ", ".join(f"{k}={len(v)}" for k, v in sc.observed_texts.items())
            lines.append(f"- observed_texts: {counts} · scroll {sc.scroll.passes} pass "
                         f"({sc.scroll.terminated})")
            if sc.risk_flags:
                lines.append(f"- risk_flags (record-only): {', '.join(sc.risk_flags)}")
            lines.append("")
            lines.append("| label | kind | role | risk |")
            lines.append("|---|---|---|---|")
            for e in sc.elements:
                lines.append(f"| {e.label} | {e.kind} | {e.text_role_hint} | {e.risk} |")
            lines.append("")
        return "\n".join(lines)
