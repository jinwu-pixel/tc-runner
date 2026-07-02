#!/usr/bin/env python
# 1회성 실행 보조 — 복합 TC 비-재부팅 서브셋 순차 실행용 (2026-06-16).
# read-only/return-only 아님: 실제 단말 write 수행 (write 서브커맨드). reboot/IMS-Reset 미수행.
import subprocess, sys, time, re, os
import xml.etree.ElementTree as ET

DEV = "c4324122"
ROOT = r"ODIN2 - Engineer IMS\evidence\device\combined_run"

def adb(*args, timeout=90):
    return subprocess.run(["adb", "-s", DEV, *[str(a) for a in args]],
                          capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")

def dump():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    r = adb("exec-out", "cat", "/sdcard/ui.xml")
    return r.stdout

def nodes(xt):
    try:
        root = ET.fromstring(xt)
    except Exception:
        # strip junk before <?xml or <hierarchy
        i = xt.find("<hierarchy")
        root = ET.fromstring(xt[i:]) if i >= 0 else None
    return [n.attrib for n in root.iter("node")] if root is not None else []

def center(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
    return (int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2

def tap(x, y):
    adb("shell", "input", "tap", x, y)
    time.sleep(0.8)

def tap_text(xt, substr, exact=False):
    for a in nodes(xt):
        t = a.get("text", "")
        if (t == substr) if exact else (substr in t):
            x, y = center(a["bounds"]); tap(x, y); return True
    return False

def reset_top():
    for _ in range(6):
        adb("shell", "input", "swipe", 360, 420, 360, 1100, 200)
    time.sleep(0.6)

def find_and_tap(substr, max_scroll=10):
    reset_top()
    seen_last = None
    for _ in range(max_scroll):
        xt = dump()
        for a in nodes(xt):
            if substr in a.get("text", ""):
                x, y = center(a["bounds"]); tap(x, y); return True
        # detect bottom: hash of all texts
        sig = "|".join(a.get("text", "") for a in nodes(xt))
        if sig == seen_last:
            break
        seen_last = sig
        adb("shell", "input", "swipe", 360, 1000, 360, 420, 300); time.sleep(1)
    return False

def goto_ims():
    # force-stop guarantees the gate screen on relaunch (am start alone just resumes top activity)
    adb("shell", "am", "force-stop", "com.ls.teleengineer"); time.sleep(1.0)
    adb("shell", "am", "start", "-n", "com.ls.teleengineer/.EngineeringActivity"); time.sleep(2.0)
    xt = dump(); tap_text(xt, "Enter Engineering Mode"); time.sleep(1.6)
    xt = dump(); tap_text(xt, "IMS", exact=True); time.sleep(1.6)

def detail():
    xt = dump(); r = {}
    for a in nodes(xt):
        rid = a.get("resource-id", "")
        for key in ("tv_detail_value", "tv_detail_status", "tv_top_title", "et_detail_input", "btn_read", "btn_write", "btn_back"):
            if rid.endswith(key):
                r[key] = {"text": a.get("text", ""), "bounds": a.get("bounds", "")}
    return r, xt

def outdir(tcid):
    d = os.path.join(ROOT, tcid); os.makedirs(d, exist_ok=True); return d

def hook(path):
    r = adb("logcat", "-d")
    ls = [l for l in r.stdout.splitlines() if "QC_RIL_OEM_HOOK" in l or "TeleEngineer" in l or "INI_READ" in l or "INI_WRITE" in l or "QCRIL_JAVA" in l]
    open(path, "w", encoding="utf-8").write("\n".join(ls))
    return ls

def save(path, xt):
    open(path, "w", encoding="utf-8").write(xt)

def show(d):
    for k in ("tv_top_title", "tv_detail_value", "tv_detail_status", "et_detail_input"):
        if k in d: print(f"   {k:18s}= {d[k]['text']!r}")

def cmd_read(tcid, step, substr):
    o = outdir(tcid)
    goto_ims()
    if not find_and_tap(substr):
        print(f"!! item not found: {substr}"); return
    d, xt = detail(); save(os.path.join(o, f"{step}_01_pre.xml"), xt)
    adb("logcat", "-c")
    if "btn_read" in d:
        x, y = center(d["btn_read"]["bounds"]); tap(x, y); time.sleep(1.2)
    d, xt = detail(); save(os.path.join(o, f"{step}_02_read.xml"), xt)
    ls = hook(os.path.join(o, f"{step}_03_read_hook.log"))
    print(f"== READ {tcid}/{step} :: {substr}")
    show(d)
    print(f"   Way2 hook lines = {len(ls)}")
    for l in ls[-6:]:
        print("   | " + l[-160:])

def cmd_write(tcid, step, substr, value):
    o = outdir(tcid)
    goto_ims()
    if not find_and_tap(substr):
        print(f"!! item not found: {substr}"); return
    d, xt = detail()
    if "et_detail_input" not in d:
        print("!! no et_detail_input (radio item?) — use radio cmd"); save(os.path.join(o, f"{step}_noinput.xml"), xt); return
    ix, iy = center(d["et_detail_input"]["bounds"]); tap(ix, iy); time.sleep(0.4)
    adb("shell", "input", "keyevent", "123")
    adb("shell", "input", "keyevent", *(["67"] * 14))
    time.sleep(0.3)
    adb("shell", "input", "text", str(value)); time.sleep(0.5)
    d, xt = detail(); save(os.path.join(o, f"{step}_04_input.xml"), xt)
    got = d.get("et_detail_input", {}).get("text", "")
    print(f"== WRITE {tcid}/{step} :: {substr} <- {value}")
    print(f"   input field now = {got!r}  (intended {value!r})")
    if str(value) not in got:
        print("   !! input mismatch — ABORT write (재시도 필요)"); return
    adb("logcat", "-c")
    if "btn_write" in d:
        x, y = center(d["btn_write"]["bounds"]); tap(x, y); time.sleep(1.4)
    d, xt = detail(); save(os.path.join(o, f"{step}_05_post_write.xml"), xt)
    ls = hook(os.path.join(o, f"{step}_06_write_hook.log"))
    show(d)
    print(f"   Way2 hook lines = {len(ls)}")
    for l in ls[-8:]:
        print("   | " + l[-160:])

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "read":  cmd_read(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == "write": cmd_write(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else: print("usage: read <tcid> <step> <substr> | write <tcid> <step> <substr> <value>")
