"""Pure PII redaction for menu-tree v1.2 phone/network issue-probe artifacts.

Implements the Task 4.1 LOCKED redaction policy (2026-06-08): detect -> redact
-> residual_scan -> path_policy_findings. Pure and device-independent — must not
import scripts/runner/cli layers (enforced by an AST layering-guard test, mirror
of src.menu_anchor). Raw XML ground truth is never modified; only derived
JSON/MD/log-excerpt artifacts are redacted.

See docs/superpowers/plans/2026-06-08-redaction-residual-scan.md.

Task 1: type skeleton + layering guard. detect/redact/scan are stubs filled in
Tasks 2-10.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Known KR PLMN (MCCMNC) minimal set — locked 2026-06-08. operator numeric is
# detected ONLY for these values AND with a label anchor (blind digit regex is
# forbidden by policy). Expand only with an observed empirical basis.
KR_PLMN = {"45002", "45003", "45005", "45006", "45008", "45012"}

# --- network identifier patterns (Task 2) ---------------------------------
_MAC_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
# IPv6: full 8-group form OR compressed "::" form.
_IPV6_RE = re.compile(
    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}"
)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# --- identity id patterns (Task 3) ----------------------------------------
# A maximal run of digits (optionally space-grouped). Classification requires a
# label anchor — a bare digit run is NEVER redacted (blind digit regex forbidden).
_DIGITS_RE = re.compile(r"\d[\d ]{5,24}\d")
# Explicit MSISDN format (KR mobile), accepted without a label.
_MSISDN_FMT_RE = re.compile(r"(?:\+82|0)1[016789]\d{7,8}")
# Label tokens that must appear within 24 chars before the digit run.
_ID_LABELS = {
    "ICCID": ("iccid", "sim 일련", "sim serial"),
    "IMSI": ("imsi",),
    "IMEI": ("imei",),
    "MSISDN": ("msisdn", "전화번호", "phone number"),
}
# Length gates, evaluated longest-first: ICCID -> IMSI/IMEI(15) -> MSISDN.
_ID_LEN = {
    "ICCID": lambda n: 19 <= n <= 20,
    "IMSI": lambda n: n == 15,
    "IMEI": lambda n: n == 15,
    "MSISDN": lambda n: 10 <= n <= 12,
}
_ID_ORDER = ("ICCID", "IMSI", "IMEI", "MSISDN")


def _label_before(text: str, start: int, keys: tuple[str, ...]) -> bool:
    # Window is line-local: a label must not be borrowed across a newline from a
    # neighbouring record (prevents cross-line false positives in report text).
    line_start = text.rfind("\n", 0, start) + 1
    head = text[max(line_start, start - 24):start].lower()
    return any(k in head for k in keys)


def _detect_identity(text, spans, claim):
    # Explicit MSISDN format first (most specific) so it owns its region.
    for m in _MSISDN_FMT_RE.finditer(text):
        if claim(m.start(), m.end()):
            spans.append(Span(m.start(), m.end(), "MSISDN", m.group(0), "T"))
    # Label-anchored digit runs, longest-first precedence.
    for m in _DIGITS_RE.finditer(text):
        n = len(m.group(0).replace(" ", ""))
        for kind in _ID_ORDER:
            if _ID_LEN[kind](n) and _label_before(text, m.start(), _ID_LABELS[kind]):
                if claim(m.start(), m.end()):
                    spans.append(Span(m.start(), m.end(), kind, m.group(0).strip(), "T"))
                break


# --- operator numeric / MCCMNC (Task 4) -----------------------------------
# Standalone 5-6 digit token only (word-boundaried). The \b guard means a
# MCCMNC prefix inside a longer identity run (IMSI/ICCID) is never sliced out.
# Detected ONLY when the value is a known KR PLMN AND a label anchor precedes
# it — blind 5-6 digit redaction is forbidden by policy.
_OP_NUM_RE = re.compile(r"\b\d{5,6}\b")
_OP_LABELS = ("operator", "numeric", "plmn", "mccmnc", "통신사 코드")


def _detect_operator(text, spans, claim):
    for m in _OP_NUM_RE.finditer(text):
        v = m.group(0)
        if v in KR_PLMN and _label_before(text, m.start(), _OP_LABELS):
            if claim(m.start(), m.end()):
                spans.append(Span(m.start(), m.end(), "OPERATOR_NUMERIC", v, "T"))


# --- build fingerprint (Task 5) -------------------------------------------
# Full Android fingerprint: BRAND/PRODUCT/DEVICE:RELEASE/ID/INCREMENTAL:TYPE/TAGS
# Structurally self-identifying (slashes + colons + a user|userdebug|eng/...keys
# tail) so it needs no label. A short build id (e.g. "Z0604U", "RY07260600S") has
# no such structure and is kept as analysis context. Claimed first in detect() so
# the INCREMENTAL build-id inside a fingerprint is never sliced out separately.
_BUILD_FP_RE = re.compile(
    r"[\w.\-]+/[\w.\-]+/[\w.\-]+:[\w.\-]+/[\w.\-]+/[\w.\-]+:(?:user|userdebug|eng)/[\w.\-]+"
)


def _detect_build(text, spans, claim):
    for m in _BUILD_FP_RE.finditer(text):
        if claim(m.start(), m.end()):
            spans.append(Span(m.start(), m.end(), "BUILD_FP", m.group(0), "T"))


# --- D-class drop: APN credential + first call date (Task 6) --------------
# D-class redacts the VALUE only (the key is a kept label) and never tokenizes,
# so correlation is broken (no number, no KeyMap entry). password/auth/bearer are
# strong (context-free); bare "user=" needs an APN/carriers context. The auth key
# is bounded so ordinary words like "author" are not matched.
_APN_CTX = ("apn", "carriers", "telephony")
_CRED_PATTERNS = [
    (re.compile(r"\b(?:password|passwd|pwd)\b\s*[=:]?\s*(\S+)", re.I), "apn_password", False),
    (re.compile(r"\b(?:auth(?:type|token|_token)?|bearer)\b\s*[=:]?\s*(\S+)", re.I), "apn_auth", False),
    (re.compile(r"\buser\b\s*[=:]?\s*(\S+)", re.I), "apn_user", True),  # context-gated
]
_FCD_LABELS = ("첫 통화 개시일", "개통일", "첫 통화일", "first call")
_DATE_VAL_RE = re.compile(r"\d{4}[-.]\d{1,2}[-.]\d{1,2}")


def _apn_context_near(text: str, pos: int) -> bool:
    # APN/carriers context must be on the SAME line as the bare "user=" match,
    # so an APN keyword elsewhere in a report does not enable it globally.
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    line = text[line_start:line_end if line_end != -1 else len(text)].lower()
    return any(c in line for c in _APN_CTX)


def _detect_dclass(text, spans, claim):
    for rx, label, ctx_gated in _CRED_PATTERNS:
        for m in rx.finditer(text):
            if ctx_gated and not _apn_context_near(text, m.start()):
                continue
            vs, ve = m.span(1)  # value group only — keep the key label
            if claim(vs, ve):
                spans.append(Span(vs, ve, "APN_CRED", m.group(1), "D", label))
    for m in _DATE_VAL_RE.finditer(text):
        if _label_before(text, m.start(), _FCD_LABELS) and claim(m.start(), m.end()):
            spans.append(
                Span(m.start(), m.end(), "FIRST_CALL_DATE", m.group(0), "D", "first_call_date")
            )


@dataclass(frozen=True)
class Span:
    """A detected sensitive region within a single text value."""

    start: int
    end: int
    kind: str            # IMSI IMEI ICCID MSISDN OPERATOR_NUMERIC IPV4 IPV6 MAC BUILD_FP APN_CRED FIRST_CALL_DATE
    value: str
    klass: str           # "T" (tokenize) | "D" (drop)
    drop_label: str | None = None   # D only: apn_user | apn_password | apn_auth | first_call_date


@dataclass
class KeyMap:
    """Per-run-bundle token store. Same value -> same token within one run.

    Serialized form is local carry only — committing it is forbidden by policy
    (see path_policy_findings).
    """

    _by_kind: dict = field(default_factory=dict)

    def token_for(self, kind: str, value: str) -> str:
        d = self._by_kind.setdefault(kind, {})
        if value not in d:
            d[value] = f"<{kind}_{len(d) + 1}>"
        return d[value]

    def to_dict(self) -> dict:
        # Local-carry serialization (committing this is forbidden by policy).
        return {"by_kind": {k: dict(v) for k, v in self._by_kind.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "KeyMap":
        km = cls()
        km._by_kind = {k: dict(v) for k, v in d.get("by_kind", {}).items()}
        return km


@dataclass(frozen=True)
class Finding:
    """A commit-blocking residual-PII (or, in Task 10, forbidden-path) finding."""

    kind: str
    message: str
    location: str       # json-path for content scan; file path for path policy
    excerpt: str
    severity: str = "high"


def detect(text: str) -> list[Span]:
    spans: list[Span] = []
    taken: list[tuple[int, int]] = []

    def _claim(start: int, end: int) -> bool:
        if any(start < e and s < end for s, e in taken):
            return False
        taken.append((start, end))
        return True

    # Build fingerprint first: claim the whole structure so its INCREMENTAL
    # build-id is not later sliced out by identity/operator detectors.
    _detect_build(text, spans, _claim)

    # MAC before IPv6/IPv4 so a MAC's colons are not re-consumed as an address.
    for rx, kind in ((_MAC_RE, "MAC"), (_IPV6_RE, "IPV6"), (_IPV4_RE, "IPV4")):
        for m in rx.finditer(text):
            if _claim(m.start(), m.end()):
                spans.append(Span(m.start(), m.end(), kind, m.group(0), "T"))

    _detect_identity(text, spans, _claim)
    _detect_operator(text, spans, _claim)
    _detect_dclass(text, spans, _claim)

    spans.sort(key=lambda s: s.start)
    return spans


def redact_text(text: str, keymap: KeyMap) -> str:
    spans = detect(text)  # ascending document order
    # Assign tokens in forward order so token numbering follows reading order...
    repls = {}
    for s in spans:
        repls[(s.start, s.end)] = (
            f"<REDACTED:{s.drop_label}>" if s.klass == "D"
            else keymap.token_for(s.kind, s.value)
        )
    # ...then splice back-to-front to keep offsets valid.
    out = text
    for s in sorted(spans, key=lambda s: s.start, reverse=True):
        out = out[:s.start] + repls[(s.start, s.end)] + out[s.end:]
    return out


def redact(obj, keymap: KeyMap):
    # Recurse dict/list/str. Dict keys are never redacted (only string values);
    # numbers/bool/None pass through unchanged. The same keymap is threaded so a
    # per-run bundle of sidecars shares one token namespace.
    if isinstance(obj, str):
        return redact_text(obj, keymap), keymap
    if isinstance(obj, list):
        return [redact(item, keymap)[0] for item in obj], keymap
    if isinstance(obj, dict):
        return {key: redact(value, keymap)[0] for key, value in obj.items()}, keymap
    return obj, keymap


def _excerpt(text: str, start: int, end: int, pad: int = 12) -> str:
    return text[max(0, start - pad):min(len(text), end + pad)]


# A detected span whose value is EXACTLY an allowed redaction placeholder is
# already-redacted output, not residual PII. This matters for D-class: it keeps
# the key label and drops only the value, so "password=<REDACTED:apn_password>"
# survives and the credential detector re-captures the placeholder as a "value"
# — a false positive. The allow-set is closed and matched with fullmatch, so a
# malformed label (<REDACTED:apn_password_bogus>) or a glued plaintext prefix
# (prefix<IPV4_1>) is NOT treated as clean and stays flagged.
_REDACTION_DROP_LABELS = ("apn_user", "apn_password", "apn_auth", "first_call_date")
_REDACTION_TOKEN_KINDS = (
    "IMSI", "IMEI", "ICCID", "MSISDN", "OPERATOR_NUMERIC",
    "IPV4", "IPV6", "MAC", "BUILD_FP",
)
_ALLOWED_PLACEHOLDER_RE = re.compile(
    r"<(?:REDACTED:(?:%s)|(?:%s)_\d+)>"
    % ("|".join(_REDACTION_DROP_LABELS), "|".join(_REDACTION_TOKEN_KINDS))
)


def residual_scan(obj, _loc: str = "$") -> list[Finding]:
    # Applies to commit-candidate REDACTED artifacts only (JSON/MD/log excerpt),
    # never to raw XML ground truth. Reuses detect(); a standalone token (<KIND_n>,
    # <REDACTED:label>) matches no detector, and a span whose captured value is
    # EXACTLY an allowed placeholder (D-class kept label) is skipped — so a clean
    # output is empty. Recurses dict/list values (dict keys are not scanned —
    # conservative, in line with redact() which never rewrites keys). severity is
    # high-only (binary gate).
    findings: list[Finding] = []
    if isinstance(obj, str):
        for s in detect(obj):
            if _ALLOWED_PLACEHOLDER_RE.fullmatch(s.value):
                continue  # already-redacted placeholder, not residual PII
            findings.append(Finding(
                s.kind,
                f"residual {s.kind} ({s.klass}-class) in redacted output",
                _loc,
                _excerpt(obj, s.start, s.end),
            ))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            findings.extend(residual_scan(item, f"{_loc}[{i}]"))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            findings.extend(residual_scan(value, f"{_loc}.{key}"))
    return findings


def path_policy_findings(paths: list[str]) -> list[Finding]:
    # Path gate, separate from residual_scan (content). Blocks local-carry-only
    # artifacts from commit: the redaction keymap, anything under a raw/ capture
    # directory, and raw XML dumps (*_raw_*.xml). Allowed commit candidates
    # (redacted sidecar .json, ledger/digest .md, RESULT_*.md) are not flagged.
    findings: list[Finding] = []
    for p in paths:
        low = p.replace("\\", "/").lower()
        base = p.replace("\\", "/").rsplit("/", 1)[-1]
        low_base = low.rsplit("/", 1)[-1]
        reason = None
        if "_redaction_keymap.json" in low:
            reason = "redaction keymap is local-carry only — commit forbidden"
        elif "raw" in low.split("/"):
            reason = "raw capture directory is local-carry ground truth — commit forbidden"
        elif low_base.endswith(".xml") and "raw" in low_base:
            reason = "raw XML dump is local-carry ground truth — commit forbidden"
        if reason:
            findings.append(Finding("PATH_POLICY", reason, p, base))
    return findings
