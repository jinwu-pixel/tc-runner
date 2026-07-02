# -*- coding: utf-8 -*-
"""batch10 KEEP_CONFIRMED F0 validation manifest assembly (무단말, 결정적·파생).

Set-diff: {batch10 canonical tc_id}  MINUS  union({기존 모든 VALIDATION_MANIFEST_*.csv tc_id})
  → 신규 queue 대상만 manifest 화. (271 − 35 추정은 방향성일 뿐, 실제 입력은 set-diff.)

원칙:
  - selector / literal 발명 0 — verifier_candidates 는 YAML 의 verifier_contract /
    step-level verify_text / expected_texts_candidate 만 사용. 미근거 시 review bucket.
  - 단말 접촉 0 (device_value 는 PENDING_F0 채록 대상으로만 남김).
  - 기존 18-col 포맷, byte-identical header (gen_batch11_manifest COLS 동일, utf-8-sig).
  - 미근거(verifier 신호 0 / safety_class 비안전 / 진입·절차 결손) 행은 manifest 에서 제외하고
    REVIEW_BUCKET CSV 로 분리 — 조작/날조 금지(사용자 hard rule).

출력:
  VALIDATION_MANIFEST_BATCH10_<DATE>.csv   (device-ready queue)
  REVIEW_BUCKET_BATCH10_<DATE>.csv         (있을 때만)
local-only scratch generator — 미스테이지(커밋 후보 아님).
"""
import glob, os, csv, io, yaml
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "..", "THOR2 - ALT Basic TC Audit")
B10 = os.path.join(BASE, "stage1_review_mapping_batch10")
HOFF = os.path.join(BASE, "handoff_device_validation")
DATE = "2026-06-25"
OUT = os.path.join(HOFF, "VALIDATION_MANIFEST_BATCH10_%s.csv" % DATE)
REVIEW = os.path.join(HOFF, "REVIEW_BUCKET_BATCH10_%s.csv" % DATE)

# 기존 manifest 와 동일한 18-col (byte-identical header)
COLS = ["tc_id", "batch", "title", "yaml_path", "source_file", "source_sheet", "source_row",
        "entry_method", "entry_detail", "leaf_presence", "verifier_candidates", "verifier_caveat",
        "cleanup", "risk", "redaction", "carrier_fit", "precondition", "handoff_status"]

# device-run 위험순 정렬용 (낮을수록 먼저). KEEP_CONFIRMED 안전등급 → rank.
# READ_ONLY = 순수 관찰(메뉴/토글 노출 확인) — NAVIGATION_ONLY 와 동급 최저위험.
#   (modal 호출 READ_ONLY[전원끄기·SOS·터치잠금]도 risk_note '절대 탭 금지' 로 제약 — risk 컬럼에 보존.)
SAFE_RANK = {"READ_ONLY": 1, "NAVIGATION_ONLY": 1, "OBSERVE_ONLY": 2,
             "SELECTION_GATED": 3, "INPUT_TRANSIENT": 4}
KNOWN_SAFE = set(SAFE_RANK)


def rel(path):
    return os.path.relpath(path, BASE).replace("\\", "/")


def entry_detail(d):
    # QA(2026-06-25) 정정: 기존 [:2] step 한정 + target[:40] truncation 이 후속 네비 step·
    # gesture qualifier(예 '길게', '추가 옵션 tap')를 누락 → 운영자 under-execute·false FAIL.
    # → 전 step, raw_text(소스 verbatim gesture 보존) 사용. cap 120(runaway 방지).
    segs = []
    for s in (d.get("procedure_steps") or []):
        ni = s.get("normalized_intent") or {}
        raw = (s.get("raw_text") or ni.get("target") or "").strip().replace("\n", " ")
        if len(raw) > 120:
            raw = raw[:120] + "…"
        segs.append("%s:%s" % (ni.get("type"), raw))
    return " > ".join(segs)


def verifier_parts(d):
    """(verifier_candidates 문자열, grounded?) — YAML 근거만 사용, 발명 0."""
    am = d.get("audit_meta") or {}
    vc = am.get("verifier_contract")
    lits = [e.get("target") for s in (d.get("procedure_steps") or [])
            for e in (s.get("expected") or [])
            if e.get("type") == "verify_text" and e.get("target")]
    elems = [e.get("target") for s in (d.get("procedure_steps") or [])
             for e in (s.get("expected") or [])
             if e.get("type") == "element_presence" and e.get("target")]
    etc = [t for t in (d.get("expected_texts_candidate") or []) if t]
    parts = []
    if vc:
        parts.append("[%s] %s" % (vc.get("assert"), vc.get("expectation", "")))
    if lits:
        parts.append("literal: " + " / ".join(lits))
    if elems:
        parts.append("element: " + " / ".join(elems))
    grounded = bool(vc or lits or elems or etc)
    if not parts and etc:
        parts = ["literal: " + " / ".join(etc)]
    if not parts:
        parts = ["—"]
    return " ; ".join(parts), grounded


def verifier_caveat(d):
    vt = (d.get("audit_meta") or {}).get("verifier_type")
    if vt == "focus_state":
        return ("무단말 — run1 dump로 focused=true 요소(resource-id·bounds) 채록·대조하여 "
                "PENDING_F0 확정 후 고정. 텍스트 assert 불가.")
    if vt == "element_presence":
        return "무단말 — run1 dump로 대상 element presence(resource-id·text) 확정 후 PENDING_F0 고정."
    return "무단말 — popup/화면 고정 literal run1 1차 관찰로 확정 후 고정."


def redaction_flag(d):
    sheet = (d.get("source_trace") or {}).get("sheet", "")
    if any(k in sheet for k in ("Call", "Contacts", "Message")):
        return "CHECK"  # dump 이 기존 연락처/통화/메시지 PII 부수 채록 가능 — 마스킹 확인
    return "not_required"


def precondition(d):
    return " ; ".join((p.get("text") or "") for p in (d.get("preconditions") or [])) or "—"


def risk_field(d, rank):
    am = d.get("audit_meta") or {}
    return "[R%d][%s] %s" % (rank, am.get("safety_class"), (am.get("risk_note") or "")[:160])


def review_reasons(d):
    """manifest 부적격(=review bucket) 사유 enumerate. 빈 리스트면 device-ready."""
    am = d.get("audit_meta") or {}
    out = []
    if not verifier_parts(d)[1]:
        out.append("no_grounded_verifier")
    sc = am.get("safety_class")
    if sc not in KNOWN_SAFE:
        out.append("safety_class_review:%s" % sc)
    if not (d.get("procedure_steps")):
        out.append("no_procedure_steps")
    if not am.get("entry_type"):
        out.append("no_entry_type")
    if (am.get("export_status") != "STAGE1_DRAFT"):
        out.append("export_status:%s" % am.get("export_status"))
    return out


def existing_manifest_ids(exclude=None):
    """기존 모든 VALIDATION_MANIFEST_*.csv 의 tc_id union (already-manifested 집합).

    exclude: 현재 (재)생성 중인 출력 파일 — 자기 출력을 already 로 오집계하지 않도록 제외(idempotent)."""
    ids = {}
    excl = os.path.normcase(os.path.abspath(exclude)) if exclude else None
    for f in sorted(glob.glob(os.path.join(HOFF, "VALIDATION_MANIFEST_*.csv"))):
        if excl and os.path.normcase(os.path.abspath(f)) == excl:
            continue
        with io.open(f, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                t = (r.get("tc_id") or "").strip()
                if t:
                    ids.setdefault(t, []).append(os.path.basename(f))
    return ids


def main():
    already = existing_manifest_ids(exclude=OUT)
    files = sorted(glob.glob(B10 + "/*.yaml"))
    total = len(files)
    queued, review, already_hit = [], [], []
    for f in files:
        d = yaml.safe_load(io.open(f, encoding="utf-8"))
        tid = d["tc_id"]
        if tid in already:
            already_hit.append(tid)
            continue
        rs = review_reasons(d)
        rank = SAFE_RANK.get((d.get("audit_meta") or {}).get("safety_class"), 3)
        (review if rs else queued).append((rank, d, f, rs))
    queued.sort(key=lambda r: (r[0], (r[1].get("source_trace") or {}).get("sheet", ""), r[1]["tc_id"]))

    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for rank, d, f, _ in queued:
            am = d["audit_meta"]; st = d.get("source_trace") or {}
            vc_str, _g = verifier_parts(d)
            w.writerow([
                d["tc_id"], "batch10", d.get("title", ""), rel(f),
                st.get("file", ""), st.get("sheet", ""), st.get("row", ""),
                am.get("entry_type", ""), entry_detail(d), "—",
                vc_str, verifier_caveat(d),
                am.get("cleanup_candidate", ""), risk_field(d, rank),
                redaction_flag(d), am.get("carrier_fit", "not_applicable"),
                precondition(d), "DEVICE_VALIDATION_READY_CANDIDATE",
            ])

    if review:
        with io.open(REVIEW, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["tc_id", "yaml_path", "source_sheet", "verifier_type", "review_reasons", "title"])
            for rank, d, f, rs in sorted(review, key=lambda r: r[1]["tc_id"]):
                w.writerow([d["tc_id"], rel(f), (d.get("source_trace") or {}).get("sheet", ""),
                            (d.get("audit_meta") or {}).get("verifier_type", ""),
                            ";".join(rs), d.get("title", "")])

    # ---- breakdown (set-diff 보고) ----
    print("=== batch10 KEEP_CONFIRMED → F0 validation manifest (%s) ===" % DATE)
    print("batch10 KEEP_CONFIRMED total :", total)
    print("already-manifested           :", len(already_hit))
    print("newly-queued                 :", len(queued))
    print("excluded-for-review          :", len(review))
    print("check sum                    :",
          len(already_hit) + len(queued) + len(review), "== total", total,
          "OK" if len(already_hit) + len(queued) + len(review) == total else "MISMATCH")
    print()
    print("queued by verifier_type :", dict(Counter((d.get("audit_meta") or {}).get("verifier_type") for _, d, _, _ in queued)))
    print("queued by safety_class  :", dict(Counter((d.get("audit_meta") or {}).get("safety_class") for _, d, _, _ in queued)))
    print("queued by risk_rank     :", dict(Counter(r for r, _, _, _ in queued)))
    print("queued by sheet         :", dict(sorted(Counter((d.get("source_trace") or {}).get("sheet", "") for _, d, _, _ in queued).items())))
    print("redaction CHECK (queued):", sum(1 for _, d, _, _ in queued if redaction_flag(d) == "CHECK"))
    if review:
        print("review reasons          :", dict(Counter(rr for _, _, _, rs in review for rr in rs)))
    print()
    print("manifest ->", os.path.relpath(OUT, os.path.dirname(__file__)).replace("\\", "/"))
    if review:
        print("review   ->", os.path.relpath(REVIEW, os.path.dirname(__file__)).replace("\\", "/"))


if __name__ == "__main__":
    main()
