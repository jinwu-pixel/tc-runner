# -*- coding: utf-8 -*-
"""STAGE1 CTF 산출물 자기검증 — 스키마 필수 필드 / 숫자 정합성 / source_trace 전수 / drop 없음."""
import glob, io, os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE1 = os.path.join(os.path.dirname(HERE), "stage1")

REQ_TOP = ["tc_id", "title", "source_type", "source_trace", "preconditions",
           "procedure_steps", "automation_summary", "manual_requirements", "risk_flags"]
VALID_CLASS = {"FULL_AUTO", "SEMI_AUTO", "MANUAL_REQUIRED", "AMBIGUOUS_NL", "OUT_OF_SCOPE"}
VALID_MODE = {"UI_AUTO", "SHELL_AUTO", "MANUAL_REQUIRED", "EXTERNAL_EVENT", "UNSUPPORTED"}
VALID_ROLE = {"ACTION", "ASSERT", "SETUP", "TEARDOWN"}
VALID_FEAS = {"text_literal", "element_presence", "focus_state", "screenshot", "infeasible"}
VALID_FLAG = {"EXTERNAL_DEVICE", "HUMAN_JUDGEMENT", "LONG_WAIT", "PHYSICAL_ACTION",
              "MULTI_DEVICE", "SERVER_DEPENDENCY", "UNKNOWN"}

errs, warns, rows = [], [], []
files = sorted(glob.glob(os.path.join(STAGE1, "*_canonical.yaml")))
for p in files:
    n = os.path.basename(p)
    try:
        d = yaml.safe_load(io.open(p, encoding="utf-8"))
    except Exception as e:
        errs.append("%s: YAML 파싱 실패 — %s" % (n, e)); continue

    for k in REQ_TOP:
        if k not in d:
            errs.append("%s: 필수 필드 누락 '%s'" % (n, k))

    steps = d.get("procedure_steps") or []
    s = d.get("automation_summary") or {}
    tot, a, m, amb = (s.get("total_steps"), s.get("auto_steps"),
                      s.get("manual_steps"), s.get("ambiguous_steps"))
    if None in (tot, a, m, amb):
        errs.append("%s: automation_summary 숫자 필드 누락" % n)
    else:
        if a + m + amb != tot:
            errs.append("%s: 숫자 불일치 total=%d != auto%d+manual%d+amb%d=%d"
                        % (n, tot, a, m, amb, a + m + amb))
        if tot != len(steps):
            errs.append("%s: total_steps=%d 인데 procedure_steps=%d (step drop 의심)"
                        % (n, tot, len(steps)))
    if s.get("tc_class") not in VALID_CLASS:
        errs.append("%s: tc_class 부적합 '%s'" % (n, s.get("tc_class")))

    seen_no, amb_cnt = set(), 0
    for st in steps:
        no = st.get("step_no")
        if no in seen_no:
            errs.append("%s: step_no 중복 %s" % (n, no))
        seen_no.add(no)
        if not st.get("raw_text"):
            errs.append("%s: step %s raw_text 없음" % (n, no))
        stc = st.get("source_trace") or {}
        for k in ("raw_segment", "source_phase", "position", "total_segments"):
            if k not in stc:
                errs.append("%s: step %s source_trace.%s 누락" % (n, no, k))
        if st.get("ambiguity"):
            amb_cnt += 1
            if not st.get("ambiguity_reason"):
                errs.append("%s: step %s ambiguity=true 인데 reason 없음" % (n, no))
        ec = st.get("execution_candidate") or {}
        if ec.get("mode") not in VALID_MODE:
            errs.append("%s: step %s mode 부적합 '%s'" % (n, no, ec.get("mode")))
        if ec.get("role") not in VALID_ROLE:
            errs.append("%s: step %s role 부적합 '%s'" % (n, no, ec.get("role")))
        ni = st.get("normalized_intent") or {}
        if "mutation_risk" not in ni:
            errs.append("%s: step %s mutation_risk 누락" % (n, no))
        for ex in (st.get("expected") or []):
            if ex.get("feasibility") not in VALID_FEAS:
                errs.append("%s: step %s feasibility 부적합 '%s'" % (n, no, ex.get("feasibility")))
    if amb != amb_cnt:
        warns.append("%s: ambiguous_steps=%d 인데 ambiguity=true step은 %d개" % (n, amb, amb_cnt))

    for f in (d.get("risk_flags") or []):
        if f.get("flag") not in VALID_FLAG:
            errs.append("%s: risk flag 부적합 '%s'" % (n, f.get("flag")))
        if f.get("flag") == "UNKNOWN" and not f.get("reason"):
            errs.append("%s: UNKNOWN flag에 reason 없음" % n)

    rows.append((d.get("tc_id"), s.get("tc_class"), tot, a, m, amb, len(d.get("risk_flags") or [])))

print("검사 파일: %d" % len(files))
print("%-42s %-16s %5s %5s %5s %5s %5s" % ("tc_id", "tc_class", "total", "auto", "man", "amb", "flags"))
for r in rows:
    print("%-42s %-16s %5s %5s %5s %5s %5s" % r)

from collections import Counter
c = Counter(r[1] for r in rows)
print("\ntc_class 분포:", dict(c))
print("step 총계:", sum(r[2] for r in rows),
      "| auto:", sum(r[3] for r in rows),
      "| manual:", sum(r[4] for r in rows),
      "| ambiguous:", sum(r[5] for r in rows))

if warns:
    print("\n[WARN] %d" % len(warns))
    for w in warns:
        print("  -", w)
if errs:
    print("\n[FAIL] %d" % len(errs))
    for e in errs:
        print("  -", e)
    sys.exit(1)
print("\n[OK] 스키마·숫자 정합성·source_trace 전수 통과")
