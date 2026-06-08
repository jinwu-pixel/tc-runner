# Redaction + Residual-Scan Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **COMMIT POLICY (tc-runner §7 / global commit policy):** Every `commit` step in this plan is **approval-gated**. Do NOT auto-commit. Accumulate changes and commit only on explicit user "commit now" (batch). Per-task commit steps below are written as the *unit boundary*, not an instruction to commit immediately.

**Goal:** Build a pure `src/redaction.py` (detect → redact → residual_scan → path_policy_findings) that enforces the Task 4.1 LOCKED redaction policy, so Task 4.2 APN/DebugScreen/SIM/DeviceInfo probe artifacts can become commit candidates.

**Architecture:** Pure, device-independent module (no `scripts`/`cli`/`action_runner`/`reporter`/`adb`/`mmi_converter` imports — AST layering guard, mirroring `menu_anchor`). `detect()` finds candidate spans; `redact()` applies per-run `KeyMap` tokenization (T) / drop (D) / keep; `residual_scan()` + `path_policy_findings()` form the commit-blocking gate. Raw XML is never modified — only derived JSON/MD/log-excerpt artifacts.

**Tech Stack:** Python 3.12, pytest, `venv/Scripts/python.exe`, `dataclasses`, `re`, `ast` (layering guard).

---

## LOCKED policy reference (Task 4.1, 2026-06-08)

- Token namespace = **per-run bundle** (one `run_id` shares one `KeyMap`).
- 11 fields → **T (token, correlation-preserving)** / **D (drop, no correlation)** / **Keep**:
  - T: IMSI, IMEI, ICCID, MSISDN, operator numeric, IPv4, IPv6, MAC, build fingerprint (full).
  - D: APN credential (user/password/auth), first call date / 개통일.
  - Keep: short build id / build label (e.g. `Z0604U`, `RY07260600S`, `AT-M140LZ0604U`).
- **operator numeric & IMSI: blind digit regex forbidden** — label-anchor + known KR PLMN set only.
- Token form `<KIND_n>` (T, per-kind 1-based, per-run). Drop form `<REDACTED:label>` (D, no number).
- raw XML (`catalog/raw/<run_id>/`) + keymap (`catalog/raw/<run_id>/_redaction_keymap.json`) = local carry only, **commit forbidden**. Only redacted sidecar/MD/log-excerpt are commit candidates.
- **residual-scan PASS required before commit.** Gate not implemented yet → this plan implements it.

### Locked decisions for this plan (resolved 2026-06-08)
- **KR_PLMN minimal set**: `45002, 45003, 45005, 45006, 45008, 45012`. Unregistered PLMN is **not** detected as operator numeric. Expand only with empirical (label + observed) basis.
- **residual_scan severity = `high` single** (commit gate is binary). A `medium` tier is deferred to a future reporting scanner, out of scope here.
- **KeyMap serialization belongs in Task 8** (not deferred to 4.2): `to_dict`/`from_dict`, local-carry-only, commit-forbidden.

---

## File Structure

| File | Responsibility | Kind |
|---|---|---|
| `src/redaction.py` | `Span`/`Finding`/`KeyMap` types · `detect` · `redact`/`redact_text` · `residual_scan` · `path_policy_findings` · constants (`KR_PLMN`, label anchors, patterns) | Create |
| `tests/test_redaction.py` | detect / redact / KeyMap (incl. serialization) / false-positive negatives / layering guard | Create |
| `tests/test_redaction_scan.py` | residual_scan gate + keymap/raw path policy | Create |
| `tests/fixtures/redaction/device_info_sample.json` | device_info-like dict with PII for the redact integration test | Create |

**4.2 wiring (probe writer calls `redact`, pre-commit calls scan/path-policy) is OUT OF SCOPE** — see Non-goals.

## Module API (shared across all tasks — keep types consistent)

```python
# src/redaction.py
from __future__ import annotations
from dataclasses import dataclass, field
import re

# --- known-value sets / anchors -------------------------------------------
KR_PLMN = {"45002", "45003", "45005", "45006", "45008", "45012"}  # locked minimal set

@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str            # IMSI IMEI ICCID MSISDN OPERATOR_NUMERIC IPV4 IPV6 MAC BUILD_FP APN_CRED FIRST_CALL_DATE
    value: str
    klass: str           # "T" | "D"
    drop_label: str | None = None   # D only: apn_user | apn_password | apn_auth | first_call_date

@dataclass
class KeyMap:                       # per-run bundle token store
    _by_kind: dict[str, dict[str, str]] = field(default_factory=dict)

    def token_for(self, kind: str, value: str) -> str: ...   # "<KIND_n>", 1-based per kind, reuse for same value
    def to_dict(self) -> dict: ...                            # local-carry serialization (commit forbidden)
    @classmethod
    def from_dict(cls, d: dict) -> "KeyMap": ...

@dataclass(frozen=True)
class Finding:
    kind: str
    value: str
    location: str
    severity: str = "high"

def detect(text: str) -> list[Span]: ...
def redact_text(text: str, keymap: KeyMap) -> str: ...
def redact(obj, keymap: KeyMap): ...                 # -> (redacted_obj, keymap); recurse dict/list/str
def residual_scan(obj) -> list[Finding]: ...         # applies to commit-candidate redacted artifacts only
def path_policy_findings(paths: list[str]) -> list[Finding]: ...
```

---

## Task 1 — Type skeleton + layering guard

**Files:**
- Create: `src/redaction.py`
- Test: `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations
import ast, inspect
from src import redaction as rd


def test_module_surface_exists():
    for name in ("Span", "Finding", "KeyMap", "detect", "redact", "redact_text",
                 "residual_scan", "path_policy_findings"):
        assert hasattr(rd, name), name


def test_redaction_does_not_import_scripts_runner_cli():
    tree = ast.parse(inspect.getsource(rd))
    mods = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mods.append(n.module or "")
    forbidden = {"scripts", "cli", "action_runner", "reporter", "adb",
                 "mmi_converter", "preflight", "app_explorer"}
    for m in mods:
        segs = set(m.split("."))
        assert not (segs & forbidden), (m, mods)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.redaction'`

- [ ] **Step 3: Write minimal implementation**

Write `src/redaction.py` with the full API block above, but every function a stub:

```python
from __future__ import annotations
from dataclasses import dataclass, field
import re

KR_PLMN = {"45002", "45003", "45005", "45006", "45008", "45012"}

@dataclass(frozen=True)
class Span:
    start: int; end: int; kind: str; value: str; klass: str
    drop_label: str | None = None

@dataclass
class KeyMap:
    _by_kind: dict = field(default_factory=dict)
    def token_for(self, kind, value): raise NotImplementedError
    def to_dict(self): raise NotImplementedError
    @classmethod
    def from_dict(cls, d): raise NotImplementedError

@dataclass(frozen=True)
class Finding:
    kind: str; value: str; location: str; severity: str = "high"

def detect(text): return []
def redact_text(text, keymap): return text
def redact(obj, keymap): return obj, keymap
def residual_scan(obj): return []
def path_policy_findings(paths): return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit** *(approval-gated — batch §7)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): module skeleton + layering guard"
```

## Task 2 — detect: network identifiers (IPv4 / IPv6 / MAC)

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

@pytest.mark.parametrize("text,kind,val", [
    ("IP 주소 192.0.0.4", "IPV4", "192.0.0.4"),
    ("2001:4430:41c7:b900::29e:4be2", "IPV6", "2001:4430:41c7:b900::29e:4be2"),
    ("9c:1e:ce:0c:36:e0", "MAC", "9c:1e:ce:0c:36:e0"),
])
def test_detect_network_ids(text, kind, val):
    spans = rd.detect(text)
    assert any(s.kind == kind and s.value == val and s.klass == "T" for s in spans), spans
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py::test_detect_network_ids -v`
Expected: FAIL — empty span list.

- [ ] **Step 3: Write minimal implementation**

In `detect()`, match longest-first so IPv6 is not split by the IPv4 matcher:

```python
_MAC_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{0,4}(?:::)?[0-9a-fA-F:]*\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

def _add(spans, m, kind, klass="T", drop_label=None):
    spans.append(Span(m.start(), m.end(), kind, m.group(0), klass, drop_label))

def detect(text):
    spans, taken = [], []
    def free(s, e): return all(e <= a or s >= b for a, b in taken)
    for rx, kind in ((_MAC_RE, "MAC"), (_IPV6_RE, "IPV6"), (_IPV4_RE, "IPV4")):
        for m in rx.finditer(text):
            if free(m.start(), m.end()) and ":" in m.group(0) or kind == "IPV4":
                if free(m.start(), m.end()):
                    _add(spans, m, kind); taken.append((m.start(), m.end()))
    return spans
```

(The `taken` overlap guard prevents IPv4 inside an IPv6 from double-matching. Refine the IPv6 regex during GREEN if it over/under-matches the test vector.)

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py::test_detect_network_ids -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detect IPv4/IPv6/MAC (T)"
```

## Task 3 — detect: identity ids (IMSI / IMEI / ICCID / MSISDN) with label-anchor + precedence

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
def test_imei_label_anchored():
    assert any(s.kind == "IMEI" and s.klass == "T" for s in rd.detect("IMEI: 350000000000001"))

def test_imsi_label_anchored_not_imei():
    kinds = {s.kind for s in rd.detect("IMSI 450060000000001")}
    assert "IMSI" in kinds and "IMEI" not in kinds

def test_iccid_longest_first():
    assert any(s.kind == "ICCID" for s in rd.detect("ICCID 8982000000000000001"))

def test_msisdn_label_or_format():
    assert any(s.kind == "MSISDN" for s in rd.detect("전화번호 +821012345678"))

def test_bare_15_digits_without_label_not_identity():
    assert not any(s.kind in ("IMSI", "IMEI") for s in rd.detect("순번 350000000000001"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "imei or imsi or iccid or msisdn or bare_15" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Add label-anchored detection. A digit run is classified ONLY when an adjacent label is present (blind digit runs are ignored):

```python
_DIGITS_RE = re.compile(r"\d[\d ]{5,24}\d")
_LABELS = {
    "IMSI": ("imsi",),
    "IMEI": ("imei",),
    "ICCID": ("iccid", "sim 일련", "sim serial"),
    "MSISDN": ("msisdn", "전화번호", "phone number"),
}

def _label_before(text, start, keys):
    head = text[max(0, start - 24):start].lower()
    return any(k in head for k in keys)

def _detect_identity(text, spans):
    for m in _DIGITS_RE.finditer(text):
        raw = m.group(0).replace(" ", "")
        n = len(raw)
        for kind in ("ICCID", "IMSI", "IMEI", "MSISDN"):   # longest-first precedence
            ok_len = {"ICCID": 19 <= n <= 20, "IMSI": n == 15,
                      "IMEI": n == 15, "MSISDN": 10 <= n <= 12}[kind]
            if ok_len and _label_before(text, m.start(), _LABELS[kind]):
                spans.append(Span(m.start(), m.end(), kind, m.group(0).strip(), "T"))
                break
    # MSISDN also accepted by explicit +82 / 010 format
    for m in re.finditer(r"(?:\+82|0)1[016789]\d{7,8}", text):
        spans.append(Span(m.start(), m.end(), "MSISDN", m.group(0), "T"))
```

Call `_detect_identity(text, spans)` inside `detect()`. IMSI vs IMEI (both 15) are disambiguated purely by label.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "imei or imsi or iccid or msisdn or bare_15" -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detect IMSI/IMEI/ICCID/MSISDN (label-anchored, no blind regex)"
```

## Task 4 — detect: operator numeric (known KR PLMN set + label only)

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("v", ["45005", "45006", "45008"])
def test_known_plmn_detected(v):
    assert any(s.kind == "OPERATOR_NUMERIC" and s.value == v for s in rd.detect(f"numeric={v}"))

@pytest.mark.parametrize("noise", ["23376", "123456", "450999"])
def test_unknown_5_6_digit_not_operator(noise):
    assert not any(s.kind == "OPERATOR_NUMERIC" for s in rd.detect(noise))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "plmn or operator" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
_OP_LABELS = ("numeric", "operator", "plmn", "mccmnc")

def _detect_operator(text, spans):
    for m in re.finditer(r"\b\d{5,6}\b", text):
        v = m.group(0)
        if v in KR_PLMN and _label_before(text, m.start(), _OP_LABELS):
            spans.append(Span(m.start(), m.end(), "OPERATOR_NUMERIC", v, "T"))
```

Membership in `KR_PLMN` AND a label anchor are both required. No blind 5–6 digit redaction.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "plmn or operator" -v`
Expected: PASS

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detect operator numeric (KR_PLMN set + label only)"
```

## Task 5 — detect: full build fingerprint (token) vs short build id (keep)

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
FP = "ALT/alt_thor2/thor2:14/UP1A.231005.007/RY07260600S:user/release-keys"

def test_full_fingerprint_detected():
    assert any(s.kind == "BUILD_FP" and s.value == FP and s.klass == "T" for s in rd.detect(FP))

@pytest.mark.parametrize("keep", ["RY07260600S", "Z0604U", "AT-M140LZ0604U"])
def test_short_build_id_kept(keep):
    assert not any(s.kind == "BUILD_FP" for s in rd.detect(keep))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "fingerprint or build_id" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
_FP_RE = re.compile(r"[\w.]+/[\w.]+/[\w.]+:[\w.]+/[\w.]+:[\w./]*:user/release-keys")

def _detect_build_fp(text, spans):
    for m in _FP_RE.finditer(text):
        spans.append(Span(m.start(), m.end(), "BUILD_FP", m.group(0), "T"))
```

Only the slash-form fingerprint terminating in `:user/release-keys` matches. Short build ids/labels are not matched (Keep). Adjust the regex during GREEN to fit the exact `FP` vector.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "fingerprint or build_id" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detect full build fingerprint, keep short build id"
```

## Task 6 — detect: D-class (APN credential, first call date) with tightened scope

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`

- [ ] **Step 1: Write the failing test**

```python
def test_password_is_strong_credential():
    s = next(x for x in rd.detect("password=secret123") if x.kind == "APN_CRED")
    assert s.klass == "D" and s.drop_label == "apn_password"

def test_apn_user_in_carriers_context_is_credential():
    spans = rd.detect("content://telephony/carriers ... user=lguplus")
    assert any(s.kind == "APN_CRED" and s.drop_label == "apn_user" for s in spans)

def test_plain_user_without_apn_context_not_credential():
    assert not any(s.kind == "APN_CRED" for s in rd.detect("user=admin"))

def test_first_call_date_is_drop_class():
    s = next(x for x in rd.detect("첫 통화 개시일 2024-10-10") if x.kind == "FIRST_CALL_DATE")
    assert s.klass == "D" and s.drop_label == "first_call_date"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "credential or first_call or plain_user" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
_APN_CTX = ("apn", "carriers", "telephony")           # context gate for weak fields

def _detect_apn_cred(text, spans):
    low = text.lower()
    apn_ctx = any(c in low for c in _APN_CTX)
    # password / auth / authtype: strong — flagged regardless of APN context
    for m in re.finditer(r"\b(password|pwd|auth(?:type|token)?)\s*=\s*\S+", text, re.I):
        label = "apn_password" if "p" in m.group(1).lower()[:1] else "apn_auth"
        spans.append(Span(m.start(), m.end(), "APN_CRED", m.group(0), "D", label))
    # user: weak — only inside APN/carriers context
    if apn_ctx:
        for m in re.finditer(r"\buser\s*=\s*\S+", text, re.I):
            spans.append(Span(m.start(), m.end(), "APN_CRED", m.group(0), "D", "apn_user"))

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_FCD_LABELS = ("첫 통화 개시일", "개통일", "first call")

def _detect_first_call_date(text, spans):
    for m in _DATE_RE.finditer(text):
        if _label_before(text, m.start(), tuple(s.lower() for s in _FCD_LABELS)):
            spans.append(Span(m.start(), m.end(), "FIRST_CALL_DATE", m.group(0), "D", "first_call_date"))
```

`password`/`auth*` are strong (context-free); bare `user=` requires APN/carriers context; dates require the 개통일/첫 통화 label.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "credential or first_call or plain_user" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "feat(redaction): detect APN credential (context-gated) + first call date (D)"
```

## Task 7 — false-positive prevention (negative tests)

**Files:** Modify `tests/test_redaction.py` (and tighten `src/redaction.py` if any case over-matches)

- [ ] **Step 1: Write the failing test** (passes only when `detect()` returns nothing for benign text)

```python
@pytest.mark.parametrize("benign", [
    "27% 사용 - 23.37GB 사용 가능",   # number + unit
    "2024-10-10",                      # date with no 개통일 label
    "16개 중 7개의 앱",                # counts
    "Android 버전 14",                # version
    "123456",                          # 6-digit not in KR_PLMN
    "순번 350000000000001",           # 15-digit without identity label
])
def test_benign_text_not_redacted(benign):
    assert rd.detect(benign) == [], rd.detect(benign)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py::test_benign_text_not_redacted -v`
Expected: FAIL only if a detector over-matches; otherwise diagnoses which detector to tighten.

- [ ] **Step 3: Tighten regex boundaries** (no new functions — narrow Task 3/4/6 anchors)

Ensure: `_DIGITS_RE` identity classification fires only with a label; `23.37GB`/percent are excluded (digit-run guard requires a label); bare dates need the 개통일/첫 통화 label; KR_PLMN membership is exact. Adjust word boundaries / label windows as the failing case dictates.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py::test_benign_text_not_redacted -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py
git commit -m "test(redaction): false-positive guards for benign text"
```

## Task 8 — redact() + KeyMap per-run token consistency + serialization

**Files:** Modify `src/redaction.py`, `tests/test_redaction.py`; Create `tests/fixtures/redaction/device_info_sample.json`

- [ ] **Step 1: Write the failing test**

```python
import json, pathlib

def test_same_value_same_token_per_run():
    km = rd.KeyMap()
    a, _ = rd.redact({"ip": "192.0.0.4"}, km)
    b, _ = rd.redact({"again": "192.0.0.4"}, km)
    assert a["ip"] == b["again"] and a["ip"].startswith("<IPV4_")

def test_new_run_new_keymap_new_namespace():
    a, _ = rd.redact({"ip": "192.0.0.4"}, rd.KeyMap())
    assert a["ip"] == "<IPV4_1>"

def test_d_class_dropped_without_number():
    out, _ = rd.redact({"pw": "password=secret"}, rd.KeyMap())
    assert "<REDACTED:apn_password>" in out["pw"] and "secret" not in out["pw"]

def test_label_preserved_value_only():
    out, _ = rd.redact({"IP 주소": "192.0.0.4"}, rd.KeyMap())
    assert "IP 주소" in out and out["IP 주소"] == "<IPV4_1>"

def test_redact_walks_nested_lists():
    out, _ = rd.redact({"ko": ["a", "9c:1e:ce:0c:36:e0"]}, rd.KeyMap())
    assert out["ko"][1].startswith("<MAC_")

def test_keymap_roundtrip_preserves_tokens():
    km = rd.KeyMap()
    rd.redact({"ip": "192.0.0.4"}, km)
    km2 = rd.KeyMap.from_dict(km.to_dict())
    out, _ = rd.redact({"ip2": "192.0.0.4"}, km2)   # same value after roundtrip
    assert out["ip2"] == "<IPV4_1>"

def test_keymap_counter_continues_after_roundtrip():
    km = rd.KeyMap()
    rd.redact({"a": "192.0.0.4"}, km)
    km2 = rd.KeyMap.from_dict(km.to_dict())
    out, _ = rd.redact({"b": "10.0.0.9"}, km2)       # new value continues counter
    assert out["b"] == "<IPV4_2>"

def test_redact_device_info_fixture():
    p = pathlib.Path("tests/fixtures/redaction/device_info_sample.json")
    obj = json.loads(p.read_text(encoding="utf-8"))
    out, _ = rd.redact(obj, rd.KeyMap())
    flat = json.dumps(out, ensure_ascii=False)
    assert "192.0.0.4" not in flat and "9c:1e:ce:0c:36:e0" not in flat
    assert "Z0604U" in flat   # short build id kept
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "token or keymap or redact or device_info or nested or label_preserved or d_class" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation + fixture**

`KeyMap`:

```python
@dataclass
class KeyMap:
    _by_kind: dict = field(default_factory=dict)

    def token_for(self, kind, value):
        d = self._by_kind.setdefault(kind, {})
        if value not in d:
            d[value] = f"<{kind}_{len(d) + 1}>"
        return d[value]

    def to_dict(self):
        return {"by_kind": {k: dict(v) for k, v in self._by_kind.items()}}

    @classmethod
    def from_dict(cls, d):
        km = cls()
        km._by_kind = {k: dict(v) for k, v in d.get("by_kind", {}).items()}
        return km
```

`redact_text` / `redact`:

```python
def redact_text(text, keymap):
    spans = sorted(detect(text), key=lambda s: s.start, reverse=True)
    out = text
    for s in spans:
        repl = (f"<REDACTED:{s.drop_label}>" if s.klass == "D"
                else keymap.token_for(s.kind, s.value))
        out = out[:s.start] + repl + out[s.end:]
    return out

def redact(obj, keymap):
    if isinstance(obj, str):
        return redact_text(obj, keymap), keymap
    if isinstance(obj, list):
        return [redact(x, keymap)[0] for x in obj], keymap
    if isinstance(obj, dict):
        return {k: redact(v, keymap)[0] for k, v in obj.items()}, keymap
    return obj, keymap
```

Fixture `tests/fixtures/redaction/device_info_sample.json`:

```json
{
  "screen_id": "settings_d1_device_info",
  "observed_texts": {
    "en": ["AT-M140LZ0604U", "9c:1e:ce:0c:36:e0"],
    "ko": ["IP 주소", "192.0.0.4", "첫 통화 개시일 2024-10-10"],
    "other": []
  }
}
```

> **NOTE:** `_redaction_keymap.json` (the dumped KeyMap) is **local carry only — commit forbidden**. Task 10 enforces this on commit-candidate path sets. The keymap is never a commit candidate.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction.py -k "token or keymap or redact or device_info or nested or label_preserved or d_class" -v`
Expected: PASS

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction.py tests/fixtures/redaction/device_info_sample.json
git commit -m "feat(redaction): redact() + per-run KeyMap with serialization"
```

## Task 9 — residual_scan() gate (commit-candidate artifacts only)

**Files:** Create `tests/test_redaction_scan.py`; Modify `src/redaction.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations
from src import redaction as rd


def test_clean_redacted_output_has_no_findings():
    out, _ = rd.redact({"IP 주소": "192.0.0.4", "IMEI": "IMEI 350000000000001"}, rd.KeyMap())
    assert rd.residual_scan(out) == []

def test_residual_pii_flagged_high():
    leaked = {"note": "fallback IP 주소 192.0.0.4 남음"}
    findings = rd.residual_scan(leaked)
    assert findings and all(f.severity == "high" for f in findings)
    assert any(f.kind == "IPV4" for f in findings)

def test_tokens_and_drops_not_flagged():
    assert rd.residual_scan({"x": "<IPV4_1>", "y": "<REDACTED:apn_password>"}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction_scan.py -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
def residual_scan(obj, _loc="$"):
    findings = []
    if isinstance(obj, str):
        for s in detect(obj):
            findings.append(Finding(s.kind, s.value, _loc, "high"))
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            findings += residual_scan(x, f"{_loc}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            findings += residual_scan(v, f"{_loc}.{k}")
    return findings
```

Tokens `<KIND_n>` and `<REDACTED:...>` do not match any detector, so a correctly-redacted artifact yields `[]`.

> **SCOPE:** `residual_scan` is applied to **commit-candidate redacted artifacts only** (redacted JSON / MD / log excerpt). It is **never** applied to raw XML ground truth — raw legitimately contains PII and is blocked from commit by `path_policy_findings` (Task 10), not by content scan.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction_scan.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit** *(approval-gated)*

```bash
git add src/redaction.py tests/test_redaction_scan.py
git commit -m "feat(redaction): residual_scan commit gate (content)"
```

## Task 10 — keymap / raw path policy gate

**Files:** Modify `src/redaction.py`, `tests/test_redaction_scan.py`

- [ ] **Step 1: Write the failing test**

```python
def test_keymap_path_is_forbidden_commit():
    paths = ["catalog/anchors/x.json",
             "catalog/raw/20260608T000000Z/_redaction_keymap.json"]
    f = rd.path_policy_findings(paths)
    assert any(x.kind == "FORBIDDEN_COMMIT_PATH" and "_redaction_keymap" in x.value for x in f)

def test_raw_dir_is_forbidden_commit():
    f = rd.path_policy_findings(["catalog/raw/20260608T000000Z/settings_d1_apn.xml"])
    assert any(x.kind == "FORBIDDEN_COMMIT_PATH" for x in f)

def test_redacted_sidecar_path_ok():
    assert rd.path_policy_findings(["catalog/probes/apn_lgu.json",
                                    "catalog/anchors/debugscreen.json"]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction_scan.py -k "forbidden or raw_dir or sidecar_path" -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
def path_policy_findings(paths):
    findings = []
    for p in paths:
        norm = p.replace("\\", "/")
        if "_redaction_keymap.json" in norm or "/catalog/raw/" in f"/{norm}":
            findings.append(Finding("FORBIDDEN_COMMIT_PATH", p, p, "high"))
    return findings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_redaction_scan.py -k "forbidden or raw_dir or sidecar_path" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Full suite + commit** *(approval-gated)*

Run: `venv/Scripts/python.exe -m pytest tests/ -q`
Expected: prior 617 + new redaction tests all PASS.

```bash
git add src/redaction.py tests/test_redaction_scan.py
git commit -m "feat(redaction): path policy gate (keymap/raw forbidden from commit)"
```

> Per §7, the above commits are a single approval-gated batch. Do not run them until the user says "commit now".

---

## Task 4.2 wiring — gate location (OUT OF SCOPE here; wired in 4.2)

1. The probe/sidecar writer calls `redact(obj, run_keymap)` **before** writing any sidecar to disk — one `KeyMap` shared per `run_id`.
2. The keymap is dumped (`KeyMap.to_dict`) to `catalog/raw/<run_id>/_redaction_keymap.json` — **local only**, never a commit candidate.
3. Pre-commit gate: run `residual_scan()` (content) over commit-candidate redacted artifacts AND `path_policy_findings()` (paths) over the staged set. Any Finding ⇒ block commit. Wire into / alongside `tools/git_safe_push_audit.py`.
4. Raw XML is not passed to `redact` (it stays original); it is kept out of commits by path policy only.

## Non-goals
- device / runner / reporter / cli integration (that is Task 4.2). This plan = pure module + gate logic only.
- raw XML in-place modification.
- actual edits to `tools/git_safe_push_audit.py` or `.gitignore` (separate approval).
- retroactive redaction of the existing `menu_tree` baseline device block.
- real device probe / real sidecar generation.
- a `medium` severity reporting scanner.

## Resolved decisions (locked 2026-06-08)
- KR_PLMN = `45002/45003/45005/45006/45008/45012` minimal set; unregistered PLMN not detected; expand only with empirical basis.
- residual_scan severity = `high` single (binary gate).
- KeyMap serialization (`to_dict`/`from_dict`) included in Task 8; keymap = local carry only, commit forbidden.
- APN credential: `password`/`auth*` strong (context-free); bare `user=` only inside APN/carriers context; not broadly redacted.
- residual_scan applies to commit-candidate redacted artifacts only; raw XML blocked by path policy, never content-scanned.

## Remaining open issues (non-blocking; flag at execution)
- IPv6 regex exact boundary for the `2001:4430:41c7:b900::29e:4be2` vector — refine during Task 2 GREEN; add a compressed-`::` plus full-form variant test if the single vector proves brittle.
- Whether `path_policy_findings` should also consult `.gitignore` ignore-status (defense in depth) — deferred to 4.2 wiring.
- KR_PLMN MVNO additions require an observed sample before being added (kept out until then).

---

## Self-review (plan vs spec)

**Spec coverage** — required tests ① 11 fields = Tasks 2–6; ② per-run consistency = Task 8; ③ D-class drop = Tasks 6, 8; ④ build handling = Task 5; ⑤ false-positive = Task 7; ⑥ label-anchor / blind-regex-forbidden = Tasks 3, 4; ⑦ residual-scan gate = Task 9; ⑧ keymap policy = Task 10. detect/residual_scan role separation = API + Tasks 1/9. KeyMap serialization = Task 8. APN credential scope-gating = Task 6. residual_scan target clarity = Task 9 SCOPE note. raw-not-modified = Non-goals + Task 9/10. All five review revisions incorporated.

**Placeholder scan** — every code/test step contains concrete code and exact commands; no TBD/TODO.

**Type consistency** — `Span(start,end,kind,value,klass,drop_label)`, `KeyMap.token_for/to_dict/from_dict`, `Finding(kind,value,location,severity)`, `detect/redact/redact_text/residual_scan/path_policy_findings` consistent across all tasks.
