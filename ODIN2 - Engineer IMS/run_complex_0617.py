#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Engineer Mode IMS 실기 런너 (ODIN2 com.ls.teleengineer). 단말 write/read + reboot + qmdl pull.
# 효율: caseset = 앱 1회 기동 안에서 한 케이스 전 설정 batch(force-stop 제거). preflight = 단말ID·캐리어 고정.
#       capture = 상태-게이트 pull. 실행 규칙·applicability 매트릭스 = RUNTIME_PLAYBOOK.md.
# 사용: caseset/preflight/capture/write/read/radio/mfield/reboot/pull/state (usage 하단).
import subprocess, sys, time, re, os
import xml.etree.ElementTree as ET

_DEFAULT_DEV = os.environ.get("ENG_DEV", "c4324122")  # ODIN2 default; override via ENG_DEV
APP = "com.ls.teleengineer"
EXPECT_MODEL = "AT-M150"  # ODIN2 — preflight WARNs if the active device isn't this

def _connected():
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return [l.split("\t")[0] for l in out.splitlines()[1:] if "\tdevice" in l]

def _resolve_dev():
    cs = _connected()
    if _DEFAULT_DEV in cs: return _DEFAULT_DEV
    return cs[0] if len(cs) == 1 else _DEFAULT_DEV  # single device → use it; else fall back (fails loudly)

DEV = _resolve_dev()
BASE = os.path.dirname(os.path.abspath(__file__))
RUN  = os.path.join(BASE, "log", "RUN_0617_complex")

def adb(*a, timeout=180):
    return subprocess.run(["adb", "-s", DEV, *[str(x) for x in a]],
                          capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

def dump():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    return adb("exec-out", "cat", "/sdcard/ui.xml").stdout

def nodes(xt):
    try:
        root = ET.fromstring(xt)
    except Exception:
        i = xt.find("<hierarchy")
        root = ET.fromstring(xt[i:]) if i >= 0 else None
    return [n.attrib for n in root.iter("node")] if root is not None else []

def center(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
    return (int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2

def tap(x, y, s=0.8):
    adb("shell", "input", "tap", x, y); time.sleep(s)

def tap_text(xt, substr, exact=False):
    for a in nodes(xt):
        t = a.get("text", "")
        if (t == substr) if exact else (substr in t):
            x, y = center(a["bounds"]); tap(x, y); return True
    return False

def reset_top():
    for _ in range(6):
        adb("shell", "input", "swipe", 360, 420, 360, 1100, 200)
    time.sleep(0.5)

def goto(tab):
    # force-stop guarantees gate on relaunch
    adb("shell", "am", "force-stop", "com.ls.teleengineer"); time.sleep(1.0)
    adb("shell", "am", "start", "-n", "com.ls.teleengineer/.EngineeringActivity"); time.sleep(2.0)
    xt = dump(); tap_text(xt, "Enter Engineering Mode"); time.sleep(1.6)
    xt = dump(); tap_text(xt, tab, exact=True); time.sleep(1.6)

def find_item(substr, max_scroll=12):
    reset_top(); last = None
    for _ in range(max_scroll):
        xt = dump()
        for a in nodes(xt):
            if a.get("resource-id", "").endswith("tv_item_title") and substr in a.get("text", ""):
                x, y = center(a["bounds"]); tap(x, y, 1.2); return True
        sig = "|".join(a.get("text", "") for a in nodes(xt) if a.get("resource-id", "").endswith("tv_item_title"))
        if sig == last: break
        last = sig
        adb("shell", "input", "swipe", 360, 1000, 360, 420, 300); time.sleep(0.9)
    return False

def detail():
    xt = dump(); r = {}
    for a in nodes(xt):
        rid = a.get("resource-id", "")
        key = rid.split("/")[-1]
        if key in ("tv_detail_value", "tv_detail_status", "tv_top_title", "et_detail_input",
                   "btn_read", "btn_write", "btn_reset", "btn_back"):
            r[key] = {"text": a.get("text", ""), "bounds": a.get("bounds", "")}
    return r, xt

def outdir(tcid):
    d = os.path.join(RUN, tcid); os.makedirs(d, exist_ok=True); return d

def hook(path):
    ls = [l for l in adb("logcat", "-d").stdout.splitlines()
          if any(k in l for k in ("QC_RIL_OEM_HOOK", "TeleEngineer", "INI_READ", "INI_WRITE", "QCRIL_JAVA"))]
    open(path, "w", encoding="utf-8").write("\n".join(ls)); return ls

def save(path, xt):
    open(path, "w", encoding="utf-8").write(xt)

def show(d):
    for k in ("tv_top_title", "tv_detail_value", "tv_detail_status", "et_detail_input"):
        if k in d: print(f"   {k:18s}= {d[k]['text']!r}")

# ---------- commands ----------
def cmd_read(tcid, tab, substr, step="r"):
    o = outdir(tcid); goto(tab)
    if not find_item(substr): print(f"!! not found: {substr}"); return
    d, xt = detail(); save(os.path.join(o, f"{step}_{substr[:10]}_pre.xml"), xt)
    adb("logcat", "-c")
    if "btn_read" in d:
        x, y = center(d["btn_read"]["bounds"]); tap(x, y, 1.2)
    d, xt = detail(); save(os.path.join(o, f"{step}_{substr[:10]}_read.xml"), xt)
    ls = hook(os.path.join(o, f"{step}_{substr[:10]}_read_hook.log"))
    print(f"== READ {tcid} :: {substr}"); show(d); print(f"   Way2 hook lines = {len(ls)}")
    for l in ls[-6:]: print("   | " + l[-150:])

def cmd_write(tcid, tab, substr, value, step="w"):
    o = outdir(tcid); goto(tab)
    if not find_item(substr): print(f"!! not found: {substr}"); return
    d, xt = detail()
    if "et_detail_input" not in d:
        print(f"!! no et_detail_input — radio/action item. dump saved."); save(os.path.join(o, f"{step}_{substr[:10]}_noinput.xml"), xt)
        print("   detail keys:", list(d.keys()))
        for a in nodes(xt):
            t = a.get("text","").strip(); rid=a.get("resource-id","").split("/")[-1]
            if t and rid not in ("",): print(f"     [{rid}] {t!r} {a.get('bounds','')}")
        return
    ix, iy = center(d["et_detail_input"]["bounds"]); tap(ix, iy, 0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 16))
    time.sleep(0.3)
    adb("shell", "input", "text", str(value).replace(" ", "%s")); time.sleep(0.5)
    d, xt = detail(); save(os.path.join(o, f"{step}_{substr[:10]}_input.xml"), xt)
    got = d.get("et_detail_input", {}).get("text", "")
    print(f"== WRITE {tcid} :: {substr} <- {value}")
    print(f"   input field now = {got!r}")
    if str(value).split("/")[0] not in got and str(value)[:6] not in got:
        print("   !! input mismatch — ABORT"); return
    adb("logcat", "-c")
    if "btn_write" in d:
        x, y = center(d["btn_write"]["bounds"]); tap(x, y, 1.4)
    d, xt = detail(); save(os.path.join(o, f"{step}_{substr[:10]}_post.xml"), xt)
    ls = hook(os.path.join(o, f"{step}_{substr[:10]}_hook.log"))
    show(d); print(f"   Way2 hook lines = {len(ls)}")
    for l in ls[-8:]: print("   | " + l[-150:])

def cmd_reboot():
    print("== REBOOT ..."); adb("reboot"); time.sleep(3)
    adb("wait-for-device", timeout=180); time.sleep(28)
    adb("shell", "svc", "power", "stayon", "true")
    adb("shell", "input", "keyevent", "224")
    adb("shell", "wm", "dismiss-keyguard"); time.sleep(1)
    xt = dump()
    if tap_text(xt, "사용") or tap_text(xt, "확인"):
        print("   DataPopup handled"); time.sleep(1)
    print("   boot done. radio settle wait ..."); time.sleep(20)

def cmd_pull(tcid, tag=""):
    o = outdir(tcid)
    md = adb("shell", "ls", "-t", "/sdcard/ls_log/modem/").stdout.split()
    qmdl = next((f for f in md if f.endswith(".qmdl")), None)
    if qmdl:
        dst = os.path.join(o, f"modem_{tag}_{qmdl}")
        adb("pull", f"/sdcard/ls_log/modem/{qmdl}", dst)
        print(f"   pulled modem: {qmdl} -> {os.path.getsize(dst)} bytes")
    mn = adb("shell", "ls", "-t", "/sdcard/ls_log/main/").stdout.split()
    log = next((f for f in mn if f.endswith(".log")), None)
    if log:
        dst = os.path.join(o, f"main_{tag}_{log}")
        adb("pull", f"/sdcard/ls_log/main/{log}", dst)
        print(f"   pulled main: {log}")

def _dismiss_popup():
    xt = dump()
    if tap_text(xt, "사용", exact=True): time.sleep(0.8); return True
    return False

def _btn_by_text(xt, label):
    for a in nodes(xt):
        if a.get("text", "") == label and a.get("resource-id", ""):
            return a
    return None

def cmd_radio(tcid, tab, substr, option_text, step="w"):
    o = outdir(tcid); goto(tab); _dismiss_popup(); goto(tab)
    if not find_item(substr): print(f"!! not found: {substr}"); return
    time.sleep(0.4); xt = dump()
    # tap radio whose text contains option_text
    rbs = [a for a in nodes(xt) if a.get("resource-id", "").split("/")[-1].startswith("rb_")]
    rb = next((a for a in rbs if a.get("text", "") == option_text), None)  # exact first
    if not rb:
        rb = next((a for a in rbs if option_text in a.get("text", "")), None)  # then substring
    if not rb: print(f"!! radio option not found: {option_text}"); return
    x, y = center(rb["bounds"]); tap(x, y, 0.5)
    adb("logcat", "-c")
    xt = dump(); w = _btn_by_text(xt, "Write")
    x, y = center(w["bounds"]); tap(x, y, 1.3)
    save(os.path.join(o, f"{step}_{substr[:10]}_post.xml"), dump())
    ls = hook(os.path.join(o, f"{step}_{substr[:10]}_hook.log"))
    # read back
    xt = dump(); r = _btn_by_text(xt, "Read")
    if r: x, y = center(r["bounds"]); tap(x, y, 1.1)
    xt = dump()
    cv = next((a.get("text", "") for a in nodes(xt) if a.get("resource-id", "").endswith("current_value")), None)
    print(f"== RADIO {tcid} :: {substr} <- {option_text}")
    print(f"   readback current_value = {cv!r}   Way2 hook lines = {len(ls)}")
    for l in ls[-6:]: print("   | " + l[-150:])

def cmd_mfield(tcid, tab, substr, fieldkey, value, step="w"):
    o = outdir(tcid); goto(tab); _dismiss_popup(); goto(tab)
    if not find_item(substr): print(f"!! not found: {substr}"); return
    time.sleep(0.4)
    # scroll until the field's textKey is on-screen (off-screen rows aren't in the dump)
    ns = []; i = None
    for _ in range(8):
        xt = dump(); ns = nodes(xt)
        i = next((k for k, a in enumerate(ns)
                  if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
        if i is not None: break
        adb("shell", "input", "swipe", 360, 1000, 360, 500, 300); time.sleep(0.7)
    if i is None: print(f"!! field not found: {fieldkey}"); return
    ev = bw = br = None
    for a in ns[i + 1:]:
        rid = a.get("resource-id", "").split("/")[-1]
        if rid == "editValue" and ev is None: ev = a
        if rid == "btnWrite" and bw is None: bw = a
        if rid == "btnRead" and br is None: br = a
        if ev and bw and br: break
    x, y = center(ev["bounds"]); tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123"); adb("shell", "input", "keyevent", *(["67"] * 10)); time.sleep(0.2)
    adb("shell", "input", "text", str(value)); time.sleep(0.3)
    adb("shell", "input", "keyevent", "111"); time.sleep(0.6)
    # re-dump AFTER IME dismiss — keyboard collapse shifts layout, stale bounds miss the button
    xt = dump(); ns = nodes(xt)
    i = next((k for k, a in enumerate(ns)
              if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
    bw = br = None
    for a in ns[i + 1:]:
        rid = a.get("resource-id", "").split("/")[-1]
        if rid == "btnWrite" and bw is None: bw = a
        if rid == "btnRead" and br is None: br = a
        if bw and br: break
    adb("logcat", "-c"); x, y = center(bw["bounds"]); tap(x, y, 1.3)
    save(os.path.join(o, f"{step}_{substr[:8]}_{fieldkey[:8]}_post.xml"), dump())
    ls = hook(os.path.join(o, f"{step}_{substr[:8]}_{fieldkey[:8]}_hook.log"))
    # readback
    x, y = center(br["bounds"]); tap(x, y, 1.1)
    xt = dump(); ns = nodes(xt)
    i = next((k for k, a in enumerate(ns) if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
    tv = next((a.get("text", "") for a in ns[i + 1:] if a.get("resource-id", "").endswith("textValue")), None)
    print(f"== MFIELD {tcid} :: {substr}/{fieldkey} <- {value}")
    print(f"   readback textValue = {tv!r}   Way2 hook lines = {len(ls)}")
    for l in ls[-6:]: print("   | " + l[-150:])

# ---------- in-session helpers (NO force-stop between items: app launched once) ----------
def _on_list():
    return any(a.get("resource-id", "").endswith("tv_item_title") for a in nodes(dump()))

def _back_to_list(tries=4):
    for _ in range(tries):
        xt = dump()
        if any(a.get("resource-id", "").endswith("tv_item_title") for a in nodes(xt)):
            return True
        b = next((a for a in nodes(xt) if a.get("resource-id", "").endswith("btn_back")), None)
        if b: x, y = center(b["bounds"]); tap(x, y, 0.8)
        else: adb("shell", "input", "keyevent", "4"); time.sleep(0.8)
    return _on_list()

# 각 _sess_*는 outdir o를 받아 write 직전 logcat -c → 직후 항목별 hook 파일 저장(Way2 항목별 귀속).
def _sess_text(o, substr, value):
    if not find_item(substr): return f"!nf {substr}"
    d, _ = detail()
    if "et_detail_input" not in d: _back_to_list(); return f"!not-text {substr}"
    ix, iy = center(d["et_detail_input"]["bounds"]); tap(ix, iy, 0.4)
    adb("shell", "input", "keyevent", "123"); adb("shell", "input", "keyevent", *(["67"] * 16)); time.sleep(0.3)
    adb("shell", "input", "text", str(value).replace(" ", "%s")); time.sleep(0.4)
    adb("shell", "input", "keyevent", "111"); time.sleep(0.3)
    d, _ = detail(); w = d.get("btn_write")
    adb("logcat", "-c")
    if w: x, y = center(w["bounds"]); tap(x, y, 1.2)
    d, _ = detail(); rv = d.get("tv_detail_value", {}).get("text", "")
    n = len(hook(os.path.join(o, f"cs_{substr[:12]}_hook.log")))
    _back_to_list(); return f"{substr}={rv!r} (Way2 {n})"

def _sess_radio(o, substr, option):
    # option: "rb_..." = resource-id 매칭(표시문자열·em-dash 비의존, 권장) / 그 외 = 텍스트 exact→substring.
    if not find_item(substr): return f"!nf {substr}"
    rbs = [a for a in nodes(dump()) if a.get("resource-id", "").split("/")[-1].startswith("rb_")]
    if option.startswith("rb_"):
        rb = next((a for a in rbs if a.get("resource-id", "").split("/")[-1] == option), None)
    else:
        rb = next((a for a in rbs if a.get("text", "") == option), None) or \
             next((a for a in rbs if option in a.get("text", "")), None)
    if not rb: _back_to_list(); return f"!no-opt {substr}/{option}"
    x, y = center(rb["bounds"]); tap(x, y, 0.5)
    adb("logcat", "-c")
    w = _btn_by_text(dump(), "Write")
    if w: x, y = center(w["bounds"]); tap(x, y, 1.2)
    n = len(hook(os.path.join(o, f"cs_{substr[:12]}_hook.log")))
    r = _btn_by_text(dump(), "Read")
    if r: x, y = center(r["bounds"]); tap(x, y, 1.0)
    cv = next((a.get("text", "") for a in nodes(dump()) if a.get("resource-id", "").endswith("current_value")), None)
    _back_to_list(); return f"{substr}={cv!r} (Way2 {n})"

def _sess_toggle(o, substr, want=None):
    if not find_item(substr): return f"!nf {substr}"
    def cur():
        return next((a.get("text", "") for a in nodes(dump())
                     if a.get("resource-id", "").endswith("tv_detail_value")), "")
    rd = _btn_by_text(dump(), "Read")
    if rd: x, y = center(rd["bounds"]); tap(x, y, 1.0)
    before = cur(); n = 0
    if want is None or want.upper() not in (before or "").upper():
        adb("logcat", "-c")
        w = next((a for a in nodes(dump()) if a.get("resource-id", "").endswith("btn_write")), None)
        if w: x, y = center(w["bounds"]); tap(x, y, 1.2)
        n = len(hook(os.path.join(o, f"cs_{substr[:12]}_hook.log")))
        rd = _btn_by_text(dump(), "Read")
        if rd: x, y = center(rd["bounds"]); tap(x, y, 1.0)
    after = cur(); _back_to_list(); return f"{substr}={after!r}(was {before!r}) (Way2 {n})"

def _sess_mfield(o, substr, fieldkey, value):
    if not find_item(substr): return f"!nf {substr}"
    i = None; ns = []
    for _ in range(8):
        ns = nodes(dump())
        i = next((k for k, a in enumerate(ns) if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
        if i is not None: break
        adb("shell", "input", "swipe", 360, 1000, 360, 500, 300); time.sleep(0.6)
    if i is None: _back_to_list(); return f"!no-field {fieldkey}"
    ev = next((a for a in ns[i + 1:] if a.get("resource-id", "").endswith("editValue")), None)
    x, y = center(ev["bounds"]); tap(x, y, 0.4)
    adb("shell", "input", "keyevent", "123"); adb("shell", "input", "keyevent", *(["67"] * 10)); time.sleep(0.2)
    adb("shell", "input", "text", str(value)); time.sleep(0.3); adb("shell", "input", "keyevent", "111"); time.sleep(0.5)
    ns = nodes(dump()); i = next((k for k, a in enumerate(ns) if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
    bw = next((a for a in ns[i + 1:] if a.get("resource-id", "").endswith("btnWrite")), None)
    adb("logcat", "-c"); x, y = center(bw["bounds"]); tap(x, y, 1.2)
    n = len(hook(os.path.join(o, f"cs_{substr[:8]}_{fieldkey[:10]}_hook.log")))
    ns = nodes(dump()); i = next((k for k, a in enumerate(ns) if a.get("resource-id", "").endswith("textKey") and fieldkey in a.get("text", "")), None)
    tv = next((a.get("text", "") for a in ns[i + 1:] if a.get("resource-id", "").endswith("textValue")), None) if i is not None else None
    _back_to_list(); return f"{substr}/{fieldkey}={tv!r} (Way2 {n})"

# 케이스별 설정 — (tab, [(item_substr, kind, value)]). kind: text|radio|mfield:<fieldkey>|toggle
# 적용시점/reboot영속/캐리어반영은 RUNTIME_PLAYBOOK.md 매트릭스 참조.
CASES = {
    "CMB_IMS_REG_A":   ("IMS", [("Domain", "text", "ims.mnc006.mcc450.3gppnetwork.org"),
                                ("PRID", "text", "alttest@ims.mnc006.mcc450.3gppnetwork.org"),
                                ("Register Expires", "text", "1200")]),
    "CMB_IMS_REG_B":   ("IMS", [("User Agent", "text", "ALT-UA-TEST/1.0"),
                                ("Subscribe Expires", "text", "3600"),
                                ("SIP Timer", "mfield:Timer_T1", "500")]),
    "CMB_IMS_VOICE":   ("IMS", [("Voice Codec Priority", "radio", "rb_voice_amr_wb_preferred"),
                                ("AMR Codec ModeSet", "text", "4"),
                                ("AMR-WB Codec ModeSet", "text", "8"),
                                ("HD Voice Setting", "radio", "rb_hd_on")]),
    "CMB_IMS_SESSION": ("IMS", [("Session Expires", "text", "1810"),
                                ("Session Refresher", "radio", "rb_refresher_uac"),
                                ("RTP Timer", "text", "15"),
                                ("Traffic Port", "mfield:speechStartPort", "50000"),
                                ("Traffic Port", "mfield:speechStopPort", "50010")]),
    "CMB_IMS_VIDEO":   ("IMS", [("Video Codec Priority", "radio", "rb_codec_h265"),
                                ("Traffic Port", "mfield:videoStartPort", "50020"),
                                ("Traffic Port", "mfield:videoStopPort", "50030"),
                                ("RTP Timer", "text", "15")]),
    "CMB_GEN_01":      ("GENERAL", [("HSPA Setting", "text", "5"),
                                    ("Auto Answer", "toggle", None)]),
    "CMB_LTE_01":      ("LTE", [("LTE ROHC", "radio", "rb_rohc_on"),
                                ("LTE CDRX FGI", "radio", "rb_cdrx_off")]),
}

def _device_ok():
    # wrong-device 가드: 활성 단말이 ODIN2(AT-M150) + engineer app인지 확인. caseset/capture 진입 시 강제.
    cs = _connected()
    if not cs:
        print("⚠ ABORT: no adb device connected."); return False
    model = adb("shell", "getprop", "ro.product.model").stdout.strip()
    app = APP in adb("shell", "pm", "list", "packages", APP).stdout
    if model != EXPECT_MODEL or not app:
        print(f"⚠ ABORT (wrong/absent target): active={DEV} model={model!r} engineer_app={app} "
              f"(expected {EXPECT_MODEL} + {APP}). ODIN2 연결 확인 후 재시도 (preflight 권장).")
        return False
    return True

def cmd_caseset(tcid):
    if tcid not in CASES:
        print("unknown case. known:", list(CASES)); return
    if not _device_ok(): return   # MED3: wrong-device 가드 강제
    tab, items = CASES[tcid]; o = outdir(tcid)
    goto(tab); _dismiss_popup()
    if not _on_list(): goto(tab)
    print(f"== CASESET {tcid} ({tab}) — {len(items)} settings in ONE app session (Way2 hook per item)")
    for substr, kind, value in items:   # MED4: 항목별 Way1(readback)+Way2(hook) — bulk 아님
        if kind == "text":            r = _sess_text(o, substr, value)
        elif kind == "radio":         r = _sess_radio(o, substr, value)
        elif kind == "toggle":        r = _sess_toggle(o, substr, value)
        elif kind.startswith("mfield:"): r = _sess_mfield(o, substr, kind.split(":", 1)[1], value)
        else:                         r = f"!badkind {kind}"
        print("   -", r)
        if not _on_list(): _back_to_list()
    print(f"   (per-item Way2 hooks -> {o}/cs_*_hook.log)")

def cmd_preflight():
    o = outdir("_session")
    cs = _connected()
    if not cs:
        print("⚠ PREFLIGHT ABORT: no adb device connected."); return None
    if DEV not in cs:
        print(f"⚠ PREFLIGHT: default ODIN2 {_DEFAULT_DEV} not connected — using {DEV} (connected: {cs})")
    g = lambda p: adb("shell", "getprop", p).stdout.strip()
    model = g("ro.product.model")
    app_present = APP in adb("shell", "pm", "list", "packages", APP).stdout
    if model != EXPECT_MODEL or not app_present:
        print(f"⚠ WRONG DEVICE: active={DEV} model={model!r} engineer_app={app_present} "
              f"(expected {EXPECT_MODEL} + {APP}). caseset/call 실행 전 단말 확인 필요.")
    reg = adb("shell", "dumpsys", "telephony.registry").stdout
    def grep1(pat):
        m = [re.search(pat, l) for l in reg.splitlines()]
        return next((x.group(0) for x in m if x), "?")
    boot = adb("shell", "cat", "/proc/sys/kernel/random/boot_id").stdout.strip()
    qmdl = next((f for f in adb("shell", "ls", "-t", "/sdcard/ls_log/modem/").stdout.split() if f.endswith(".qmdl")), None)
    info = (f"PREFLIGHT model={g('ro.product.model')} build={g('ro.build.version.incremental')} "
            f"carrier_sim={g('gsm.sim.operator.alpha')} carrier_net={g('gsm.operator.alpha')} "
            f"rat={grep1(r'getRilVoiceRadioTechnology=[0-9]+\([A-Z]+\)')} "
            f"ims={grep1(r'availableServices=\[[A-Z,]*\]')} boot_id={boot} qmdl={qmdl}")
    print(info)
    open(os.path.join(o, "preflight.txt"), "a", encoding="utf-8").write(info + "\n")
    return g("gsm.operator.alpha")

def cmd_capture(tcid, tag="cap", want="reg", timeout="60"):
    # state-gate: want=reg(IMS VOICE 등록 대기) | call(OFFHOOK 대기) | any(즉시). 도달 후 pull + 캐리어/UTC 기록.
    if not _device_ok(): return   # MED3: wrong-device 가드 (엉뚱한 단말 로그 pull 방지)
    o = outdir(tcid); polls = max(1, int(timeout) // 3); reached = (want == "any")
    for _ in range(polls):
        reg = adb("shell", "dumpsys", "telephony.registry").stdout
        if want == "any": break
        if want == "reg" and "availableServices=[VOICE" in reg: reached = True; break
        if want == "call" and "mCallState=2" in reg: reached = True; break   # OFFHOOK(발신/통화중)
        time.sleep(3)
    if not reached:
        print(f"   ⚠ want={want} 미도달(timeout {timeout}s) — pull 진행하나 조기/부분 가능. "
              f"call은 발신 직후~종료 전 호출, reg는 reboot 후 등록완료까지 대기 권장.")
    cmd_pull(tcid, tag)
    car = adb("shell", "getprop", "gsm.operator.alpha").stdout.strip()
    utc = adb("shell", "date", "-u", "+%Y-%m-%d %H:%M:%S").stdout.strip()
    line = f"capture {tag}: carrier={car} utc={utc} want={want}"
    open(os.path.join(o, f"capture_{tag}.txt"), "a", encoding="utf-8").write(line + "\n")
    print("  " + line)

def cmd_state():
    r = adb("shell", "dumpsys", "telephony.registry").stdout
    for kw in ("getRilVoiceRadioTechnology", "mVoiceRegState", "VOICE,SMS"):
        for l in r.splitlines():
            if kw in l: print("  ", l.strip()[:160]); break

if __name__ == "__main__":
    c = sys.argv[1]
    if   c == "caseset":  cmd_caseset(*sys.argv[2:])
    elif c == "preflight": cmd_preflight()
    elif c == "capture":  cmd_capture(*sys.argv[2:])
    elif c == "read":     cmd_read(*sys.argv[2:])
    elif c == "write":    cmd_write(*sys.argv[2:])
    elif c == "radio":    cmd_radio(*sys.argv[2:])
    elif c == "mfield":   cmd_mfield(*sys.argv[2:])
    elif c == "reboot":   cmd_reboot()
    elif c == "pull":     cmd_pull(*sys.argv[2:])
    elif c == "state":    cmd_state()
    else: print("usage: caseset <tc> | preflight | capture <tc> <tag> <reg|call|any> [timeout] | "
                "write/read/radio/mfield <args> | reboot | pull <tc> <tag> | state")
