"""Menu-tree v1.2 sidecar — physical ActionSafety derivation (Task 1).

Pure & device-independent. Classifies TC steps and baseline MenuElements by
*physical safety* (does the action mutate device state / is it reversible).

Layering (must hold):
- MUST NOT import `scripts.*` (src must not depend on scripts).
- MUST NOT import `src.mmi_converter.*` (AutomationClass mapping is a string/
  adapter concern handled in Task 2; consistency is asserted in tests only).

`ActionSafety` (physical safety) is a separate axis from AutomationClass
(automation grade). Unknown / unclassifiable inputs resolve conservatively to
`UNKNOWN_UNSAFE`.
"""
from __future__ import annotations

import enum
import json
from dataclasses import dataclass
from pathlib import Path


class ActionSafety(enum.Enum):
    READ_ONLY = "read_only"                # non-shell observation (verify_text/wait/screenshot)
    READ_ONLY_SHELL = "read_only_shell"    # getprop/dumpsys/logcat/settings get/...
    NAVIGATION_ONLY = "navigation_only"    # DPAD/BACK/HOME/swipe, am start (entry)
    SELECTION_GATED = "selection_gated"    # ENTER/CENTER/tap/toggle (allowlist-gated)
    INPUT_REQUIRED = "input_required"      # EditText / input_text
    DESTRUCTIVE = "destructive"            # reboot / content delete/insert/update
    PRIVILEGED_SHELL = "privileged_shell"  # settings put-delete / svc / pm grant-revoke
    UNKNOWN_UNSAFE = "unknown_unsafe"      # unknown shell/key/action, denylist -> conservative


@dataclass(frozen=True)
class SafetyVerdict:
    safety: ActionSafety
    reason: str


_READ_ONLY_ACTIONS = {
    "verify_text", "wait", "screenshot",
    "verify_gone", "verify_content_desc", "verify_focus_moved",
}
_TAP_ACTIONS = {"tap_text", "tap_id", "tap_xy", "tap_content_desc"}

# Shell head tokens that only observe state.
_READ_ONLY_SHELL_HEADS = {
    "getprop", "dumpsys", "logcat", "cat", "uiautomator", "ip", "ps", "df", "ls",
}
_PRIVILEGED_PM_SUBS = {
    "grant", "revoke", "clear", "install", "uninstall", "enable", "disable",
}
_READ_ONLY_PM_SUBS = {"list", "path", "dump"}

_NAV_KEYS = {"DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "BACK", "HOME"}
_SELECT_KEYS = {"DPAD_CENTER", "ENTER", "NUMPAD_ENTER"}
_UNSAFE_KEYS = {"POWER", "CALL", "ENDCALL", "SLEEP", "WAKEUP"}


def _classify_shell(command: str) -> SafetyVerdict:
    tokens = (command or "").strip().lower().split()
    head = tokens[0] if tokens else ""
    sub = tokens[1] if len(tokens) > 1 else ""

    if head == "am" and sub == "start":
        return SafetyVerdict(ActionSafety.NAVIGATION_ONLY, "shell:am_start")

    if head == "reboot":
        return SafetyVerdict(ActionSafety.DESTRUCTIVE, "shell:reboot")
    if head == "content":
        if sub in {"delete", "insert", "update", "call"}:
            return SafetyVerdict(ActionSafety.DESTRUCTIVE, f"shell:content_{sub}")
        if sub == "query":
            return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, "shell:content_query")

    if head == "settings":
        if sub in {"put", "delete"}:
            return SafetyVerdict(ActionSafety.PRIVILEGED_SHELL, f"shell:settings_{sub}")
        if sub in {"get", "list"}:
            return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, f"shell:settings_{sub}")
    if head == "svc":
        return SafetyVerdict(ActionSafety.PRIVILEGED_SHELL, "shell:svc")
    if head == "pm":
        if sub in _PRIVILEGED_PM_SUBS:
            return SafetyVerdict(ActionSafety.PRIVILEGED_SHELL, f"shell:pm_{sub}")
        if sub in _READ_ONLY_PM_SUBS:
            return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, f"shell:pm_{sub}")
    if head == "cmd" and "resolve-activity" in (command or "").lower():
        return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, "shell:cmd_resolve_activity")
    if head == "wm" and sub in {"size", "density"}:
        return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, f"shell:wm_{sub}")
    if head in _READ_ONLY_SHELL_HEADS:
        return SafetyVerdict(ActionSafety.READ_ONLY_SHELL, f"shell:{head}")

    return SafetyVerdict(ActionSafety.UNKNOWN_UNSAFE, f"shell:unknown:{head}")


def _classify_keys(keycodes: list) -> SafetyVerdict:
    norm = [str(k).upper().replace("KEYCODE_", "") for k in keycodes if k]
    if any(k in _UNSAFE_KEYS for k in norm):
        return SafetyVerdict(ActionSafety.UNKNOWN_UNSAFE, "key:unsafe")
    if any(k in _SELECT_KEYS for k in norm):
        return SafetyVerdict(ActionSafety.SELECTION_GATED, "key:select")
    if norm and all(k in _NAV_KEYS for k in norm):
        return SafetyVerdict(ActionSafety.NAVIGATION_ONLY, "key:nav")
    return SafetyVerdict(ActionSafety.UNKNOWN_UNSAFE, "key:unknown")


def classify_step(step: dict) -> SafetyVerdict:
    """Physical safety of a single TC step (tc_loader VALID_ACTIONS shape)."""
    action = step.get("action", "")

    if action in _READ_ONLY_ACTIONS:
        return SafetyVerdict(ActionSafety.READ_ONLY, f"action:{action}")
    if action in {"shell", "verify_shell"}:
        return _classify_shell(step.get("command", ""))
    if action == "input_text":
        return SafetyVerdict(ActionSafety.INPUT_REQUIRED, "action:input_text")
    if action == "manual_pause":
        # Mutates nothing itself, but gates on a human action -> not auto/read,
        # and kept distinct from a truly unclassified action.
        return SafetyVerdict(ActionSafety.SELECTION_GATED, "manual_pause requires human gate")
    if action == "swipe":
        return SafetyVerdict(ActionSafety.NAVIGATION_ONLY, "action:swipe")
    if action in _TAP_ACTIONS:
        return SafetyVerdict(ActionSafety.SELECTION_GATED, f"action:{action}")
    if action == "key":
        kc = step.get("keycode") or step.get("key")
        return _classify_keys([kc] if kc else [])
    if action == "key_sequence":
        return _classify_keys(step.get("keys", []))

    return SafetyVerdict(ActionSafety.UNKNOWN_UNSAFE, f"action:unknown:{action}")


# --- TCAnchorMapping: extract stage (source-side only) ---------------------
# entry_action key = raw `am start` launch. Baseline-side fields (screen_id,
# device_observed_texts, match_confidence) are NOT set here; they belong to the
# join stage so expected (source) and observed (device) never mix.


@dataclass(frozen=True)
class AnchorCandidate:
    tc_file: str
    entry_action: str       # raw "am start -a <action>" / "am start -n <pkg/comp>"
    domain: str             # "settings" / "app:<pkg>" / "external"
    match_method: str       # "deeplink" / "component"
    source_expected_texts: dict  # {"source": "tc_yaml", "texts": [...]}


def _parse_am_start(command: str):
    """Return (match_method, target_key, domain) for an `am start` launch, else None.

    `am force-stop` / `am broadcast` etc. are not launches -> None.
    """
    toks = (command or "").split()
    if len(toks) < 2 or toks[0] != "am" or toks[1] != "start":
        return None
    action = comp = None
    for i, t in enumerate(toks):
        if t == "-a" and i + 1 < len(toks):
            action = toks[i + 1]
        elif t == "-n" and i + 1 < len(toks):
            comp = toks[i + 1]
    if comp:
        pkg = comp.split("/", 1)[0]
        domain = "settings" if pkg == "com.android.settings" else f"app:{pkg}"
        return ("component", comp, domain)
    if action:
        domain = "settings" if action.startswith("android.settings.") else "external"
        return ("deeplink", action, domain)
    return None


def extract_anchor_candidates(tc: dict, tc_file: str) -> list:
    """Parse `am start` launches from a TC into source-side anchor candidates.

    Dedups repeated launches of the same target. expected texts come from
    verify_text steps (target/text), order-preserving + deduped.
    """
    steps = tc.get("steps", []) or []
    texts: list = []
    for s in steps:
        if s.get("action") == "verify_text":
            t = s.get("text") or s.get("target")
            if t and t not in texts:
                texts.append(t)
    candidates: list = []
    seen = set()
    for s in steps:
        if s.get("action") != "shell":
            continue
        cmd = (s.get("command") or "").strip()
        parsed = _parse_am_start(cmd)
        if parsed is None:
            continue
        method, target, domain = parsed
        if (method, target) in seen:
            continue
        seen.add((method, target))
        candidates.append(AnchorCandidate(
            tc_file=tc_file,
            entry_action=cmd,
            domain=domain,
            match_method=method,
            source_expected_texts={"source": "tc_yaml", "texts": list(texts)},
        ))
    return candidates


# --- TCAnchorMapping: join stage (candidate + baseline) --------------------
# match_confidence is a *relative* ordering (deeplink > settings-component >
# unmatched), NOT a PASS/FAIL value. 0.3 means "extraction trusted, baseline
# join did not resolve" (e.g. app:<pkg> / event domains) — not low-quality data.

CONFIDENCE_DEEPLINK = 0.9
CONFIDENCE_SETTINGS_COMPONENT = 0.8
CONFIDENCE_UNMATCHED = 0.3
CONFIDENCE_TEXT_FALLBACK = 0.2  # reserved; text-method not implemented in v1.2 Task 2

_OBSERVED_BUCKET_ORDER = ("ko", "en", "other")


@dataclass(frozen=True)
class TCAnchorMapping:
    tc_file: str
    entry_action: str
    domain: str
    match_method: str
    source_expected_texts: dict   # source side (expected) — never mixed with observed
    screen_id: object             # str | None (null allowed)
    device_observed_texts: list   # device side (observed)
    match_confidence: float

    def to_dict(self) -> dict:
        return {
            "tc_file": self.tc_file,
            "entry_action": self.entry_action,
            "domain": self.domain,
            "match_method": self.match_method,
            "source_expected_texts": self.source_expected_texts,
            "screen_id": self.screen_id,
            "device_observed_texts": self.device_observed_texts,
            "match_confidence": self.match_confidence,
        }

    @staticmethod
    def from_dict(d: dict) -> "TCAnchorMapping":
        return TCAnchorMapping(
            tc_file=d["tc_file"],
            entry_action=d["entry_action"],
            domain=d["domain"],
            match_method=d["match_method"],
            source_expected_texts=d["source_expected_texts"],
            screen_id=d["screen_id"],
            device_observed_texts=d["device_observed_texts"],
            match_confidence=d["match_confidence"],
        )


def _iter_screens(baseline) -> list:
    if baseline is None:
        return []
    if hasattr(baseline, "to_dict"):
        return baseline.to_dict().get("screens", [])
    if isinstance(baseline, dict):
        return baseline.get("screens", [])
    return list(baseline)


def _flatten_observed(observed: dict) -> list:
    out: list = []
    for bucket in _OBSERVED_BUCKET_ORDER:
        out.extend(observed.get(bucket, []) or [])
    return out


def join_anchor_to_baseline(candidate, baseline) -> TCAnchorMapping:
    """Resolve a candidate against a baseline -> screen_id / observed / confidence."""
    screens = _iter_screens(baseline)
    parsed = _parse_am_start(candidate.entry_action)
    screen_id = None
    confidence = CONFIDENCE_UNMATCHED
    observed: list = []

    if parsed is not None:
        method, target, _domain = parsed
        if method == "deeplink":
            for sc in screens:
                if (sc.get("entry") or {}).get("action") == target:
                    screen_id = sc.get("screen_id")
                    confidence = CONFIDENCE_DEEPLINK
                    observed = _flatten_observed(sc.get("observed_texts") or {})
                    break
        elif method == "component" and candidate.domain == "settings":
            for sc in screens:
                if (sc.get("entry") or {}).get("component") == target:
                    screen_id = sc.get("screen_id")
                    confidence = CONFIDENCE_SETTINGS_COMPONENT
                    observed = _flatten_observed(sc.get("observed_texts") or {})
                    break
        # app:<pkg> component / event / external -> stays unmatched (null/0.3/[])

    return TCAnchorMapping(
        tc_file=candidate.tc_file,
        entry_action=candidate.entry_action,
        domain=candidate.domain,
        match_method=candidate.match_method,
        source_expected_texts=dict(candidate.source_expected_texts),
        screen_id=screen_id,
        device_observed_texts=observed,
        match_confidence=confidence,
    )


# --- ActionSafety -> AutomationClass adapter (string-based) -----------------
# String mapping only. Production must NOT import src.mmi_converter.models;
# a test-only consistency check asserts each value is a valid AutomationClass.

_SAFETY_TO_AUTOMATION = {
    ActionSafety.READ_ONLY: "FULL_AUTO",
    ActionSafety.READ_ONLY_SHELL: "FULL_AUTO",
    ActionSafety.NAVIGATION_ONLY: "SEMI_AUTO",
    ActionSafety.SELECTION_GATED: "MANUAL_REQUIRED",
    ActionSafety.INPUT_REQUIRED: "MANUAL_REQUIRED",
    ActionSafety.PRIVILEGED_SHELL: "MANUAL_REQUIRED",
    ActionSafety.DESTRUCTIVE: "MANUAL_REQUIRED",
    ActionSafety.UNKNOWN_UNSAFE: "MANUAL_REQUIRED",
}


def safety_to_automation_class(safety: ActionSafety) -> str:
    """Conservative ActionSafety -> AutomationClass(name) mapping."""
    return _SAFETY_TO_AUTOMATION[safety]


def classify_element(element) -> SafetyVerdict:
    """Physical safety of a baseline MenuElement (kind/risk; duck-typed)."""
    if getattr(element, "risk", "") == "denylist":
        return SafetyVerdict(ActionSafety.UNKNOWN_UNSAFE, "element:denylist")
    if getattr(element, "kind", "") == "input":
        return SafetyVerdict(ActionSafety.INPUT_REQUIRED, "element:input")
    if getattr(element, "risk", "") in {"toggle", "checkable"} \
            or getattr(element, "kind", "") == "toggle":
        return SafetyVerdict(ActionSafety.SELECTION_GATED, f"element:{element.risk}")
    return SafetyVerdict(ActionSafety.READ_ONLY, f"element:{getattr(element, 'kind', '')}")


# --- IssueProbePoint: issue-reproduction coordinate sidecar (Task 5) --------
# Append-only reproduction coordinate (screen_id + condition + trials + verdict).
# Built from ledger-summary values, NOT the raw probe bundles (local carry).
# Distinct from anchor text mapping: no source_expected/device_observed fields.

ISSUE_PROBE_VERDICTS = (
    "observed_one_off", "not_regression", "regression_candidate", "inconclusive",
)


def make_trials_summary(total: int, valid: int, mismatch_count: int) -> dict:
    rate = round(mismatch_count / valid, 6) if valid else 0.0
    return {"total": total, "valid": valid,
            "mismatch_count": mismatch_count, "mismatch_rate": rate}


def suggest_verdict(mismatch_rate: float) -> str:
    """Mechanical hint only; the authoritative verdict is analyst-set."""
    if mismatch_rate == 0.0:
        return "not_regression"
    if mismatch_rate >= 0.5:
        return "regression_candidate"
    return "inconclusive"


@dataclass(frozen=True)
class IssueProbePoint:
    issue_id: str
    probe_id: str
    source_runs: list
    screen_id: str
    domain: str
    entry_action: object        # str | None
    entry_component: object     # str | None
    observed_condition: str
    hypothesis: str
    trials_summary: dict        # make_trials_summary(...)
    verdict: str                # one of ISSUE_PROBE_VERDICTS
    evidence_refs: dict         # {"ledger_path": ..., "artifact_paths": [...]}
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "probe_id": self.probe_id,
            "source_runs": self.source_runs,
            "screen_id": self.screen_id,
            "domain": self.domain,
            "entry_action": self.entry_action,
            "entry_component": self.entry_component,
            "observed_condition": self.observed_condition,
            "hypothesis": self.hypothesis,
            "trials_summary": self.trials_summary,
            "verdict": self.verdict,
            "evidence_refs": self.evidence_refs,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "IssueProbePoint":
        return IssueProbePoint(
            issue_id=d["issue_id"],
            probe_id=d["probe_id"],
            source_runs=d["source_runs"],
            screen_id=d["screen_id"],
            domain=d["domain"],
            entry_action=d.get("entry_action"),
            entry_component=d.get("entry_component"),
            observed_condition=d["observed_condition"],
            hypothesis=d["hypothesis"],
            trials_summary=d["trials_summary"],
            verdict=d["verdict"],
            evidence_refs=d["evidence_refs"],
            notes=d.get("notes", ""),
        )


def write_probe_json(probe: IssueProbePoint, path) -> None:
    Path(path).write_text(
        json.dumps(probe.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")


def load_probe_json(path) -> IssueProbePoint:
    return IssueProbePoint.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# --- failure_reason classification (Task 6, design only) -------------------
# Pure mapping; NO runner/reporter integration, NO summary schema bump.
# Priority: reach_status > input > risky > text(no_device|missing) > document.

FAILURE_REASONS = (
    "unreachable", "focus_mismatch", "text_missing", "no_device_observation",
    "risky_action", "input_required", "document_drift",
)

_RISKY_SAFETY = {
    ActionSafety.SELECTION_GATED, ActionSafety.PRIVILEGED_SHELL,
    ActionSafety.DESTRUCTIVE, ActionSafety.UNKNOWN_UNSAFE,
}


def classify_failure_reason(reach_status=None, action_safety=None,
                            expected_texts=None, observed_texts=None,
                            document_mismatch=False):
    """Map failure signals to a failure_reason, or None if nothing failed.

    `no_device_observation` (expected exists but no device/baseline observation
    at all) is kept distinct from `text_missing` (observation exists but lacks
    an expected text) so issue-probe verdicts stay decisive.
    """
    if reach_status in {"UNREACHABLE_NO_ACTION", "LAUNCH_FAILED"}:
        return "unreachable"
    if reach_status == "FOCUS_MISMATCH":
        return "focus_mismatch"
    if action_safety == ActionSafety.INPUT_REQUIRED:
        return "input_required"
    if action_safety in _RISKY_SAFETY:
        return "risky_action"
    if expected_texts:
        if not observed_texts:
            return "no_device_observation"
        if any(t not in observed_texts for t in expected_texts):
            return "text_missing"
    if document_mismatch:
        return "document_drift"
    return None


def closest_menu_node(failed_screen=None, baseline=None):
    """TODO(I3): nearest baseline node by fingerprint/text distance.

    Deferred in v1.2 (Task 6) — interface stub only, always returns None.
    """
    return None
