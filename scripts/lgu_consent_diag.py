#!/usr/bin/env python3
"""ODIN2 Z0513U LGU+ consent-dialog diagnostic.

Why: on LGU+ SIM (45006), after USB-connected reboot the OdinConfirmData
consent dialog recreates once and tapping "use" does not reliably bring
mobile data up within the observation window, while it eventually settles.
Distinct from the SKT data-popup race. Root-cause unknown: does the tap
write Settings.Secure kt_skt_allowed_data_by_user=1, and does a late
performOffData (BOOT_COMPLETED / dynamic-APN-switch) reset it to 0?

This tool does NOT auto-tap. It reboots, captures ALL logcat buffers,
continuously samples the consent key + mobile_data + focused window with
wall-clock timestamps, dumps the dialog UI once, and lets the human tap
manually so the pre/at/post-tap key transitions are recorded.

Usage:
    python scripts/lgu_consent_diag.py --serial f2bfcc3c
    python scripts/lgu_consent_diag.py --serial f2bfcc3c --observe 240
"""

import argparse
import datetime
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # avoid cp949 crash on KR Windows
except Exception:
    pass

ADB = "adb"
DEVICE = None
SECURE_KEY = "kt_skt_allowed_data_by_user"
BOOT_BUDGET = 120


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def ts_full():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def adb_cmd(args, timeout=30):
    cmd = [ADB]
    if DEVICE:
        cmd += ["-s", DEVICE]
    cmd += args
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout,
                            text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, f"ERR:{e}"


def adb_sh(s, timeout=20):
    return adb_cmd(["shell", s], timeout=timeout)


def wait_for_boot(timeout=BOOT_BUDGET):
    adb_cmd(["wait-for-device"], timeout=timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, out = adb_sh("getprop sys.boot_completed", timeout=10)
        if out.strip() == "1":
            return True
        time.sleep(2)
    return False


def _clean(o):
    """ADB-drop sentinel: don't write raw 'device not found' into the CSV."""
    s = o.strip()
    if ("not found" in s or s == "TIMEOUT" or s.startswith("ERR:")
            or "no devices" in s or "offline" in s):
        adb_cmd(["reconnect"], timeout=8)
        return "ADB_LOST"
    return s


def get_secure_key():
    _, o = adb_sh(f"settings get secure {SECURE_KEY}")
    return _clean(o)


def get_mobile_data():
    _, o = adb_sh("settings get global mobile_data")
    return _clean(o)


def get_focus():
    _, o = adb_sh("dumpsys window | grep mCurrentFocus")
    s = _clean(o)
    return s if s == "ADB_LOST" else s.replace("mCurrentFocus=", "")


def auto_tap_use():
    """Locate android:id/button1 ('Use') via uiautomator dump and tap its
    center. Returns (ok, info). Captures the LGU+ dialog XML as a side effect."""
    rc, _ = adb_sh("uiautomator dump /sdcard/_lgu_tap.xml", timeout=15)
    _, xml = adb_sh("cat /sdcard/_lgu_tap.xml", timeout=10)
    if "<hierarchy" not in xml:
        return False, f"DUMP_FAIL(len={len(xml)})"
    import re
    for m in re.finditer(r'<node\b[^>]*?/?>', xml):
        n = m.group(0)
        if 'resource-id="android:id/button1"' in n or '"Use"' in n or '"사용"' in n:
            b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                adb_sh(f"input tap {cx} {cy}")
                return True, f"button1({cx},{cy})"
    return False, "NO_BUTTON1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--serial", default=None)
    p.add_argument("--observe", type=int, default=200,
                   help="seconds to observe after boot (default 200)")
    p.add_argument("--auto-tap", action="store_true",
                   help="tool auto-taps button1 when dialog detected (else human taps)")
    args = p.parse_args()

    global DEVICE
    DEVICE = args.serial
    auto_tap = args.auto_tap

    run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out = Path("logs") / "lgu_consent_diag" / run_id
    out.mkdir(parents=True, exist_ok=True)
    timeline = out / "timeline.csv"
    events = out / "events.log"
    logcat_path = out / "logcat_all.txt"

    def ev(msg):
        line = f"[{ts_full()}] {msg}"
        print(line, flush=True)
        with open(events, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    sim = adb_sh("getprop gsm.sim.operator.numeric")[1].strip()
    build = adb_sh("getprop ro.bootimage.build.date")[1].strip()
    ev(f"run_id={run_id} serial={DEVICE} SIM={sim} build={build}")
    ev(f"out={out}  observe={args.observe}s  secure_key={SECURE_KEY}")
    if sim != "45006":
        ev(f"WARN: SIM operator {sim} != 45006 (LGU+). Continuing anyway.")

    ev("pre-reboot secure_key=%s mobile_data=%s" % (get_secure_key(), get_mobile_data()))
    ev("adb reboot")
    adb_cmd(["reboot"], timeout=15)
    time.sleep(40)
    if not wait_for_boot():
        ev("BOOT_FAIL: sys.boot_completed never 1. abort.")
        return
    t_boot = time.time()
    ev("boot_completed=1")

    # full-buffer logcat from as early as possible (captures relaunch reason)
    adb_cmd(["logcat", "-b", "all", "-c"], timeout=10)
    lf = open(logcat_path, "w", encoding="utf-8", errors="replace")
    lc = subprocess.Popen(
        [ADB] + (["-s", DEVICE] if DEVICE else []) + ["logcat", "-b", "all", "-v", "threadtime"],
        stdout=lf, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    ev(f"logcat -b all capture started -> {logcat_path.name}")

    adb_sh("input keyevent KEYCODE_WAKEUP")
    time.sleep(1)
    adb_sh("wm dismiss-keyguard")
    time.sleep(1)
    ev("screen woken + keyguard dismissed")
    if auto_tap:
        ev(f">>> AUTO-TAP mode: tool taps button1 when dialog detected. "
           f"Recording {args.observe}s of key/md/focus transitions. <<<")
    else:
        ev(f">>> MANUAL mode: tap '사용/Use' on the device whenever you decide. "
           f"Tool will NOT tap. Recording {args.observe}s of transitions. <<<")

    with open(timeline, "w", encoding="utf-8") as tf:
        tf.write("wall_clock,t_since_boot,secure_key,mobile_data,focus\n")

    last = None
    dialog_dumped = False
    tapped_done = False
    deadline = t_boot + args.observe
    while time.time() < deadline:
        sk = get_secure_key()
        md = get_mobile_data()
        fw = get_focus()
        tsb = round(time.time() - t_boot, 1)
        snap = (sk, md, ("CONFIRMDATA" if "ConfirmData" in fw else
                         "OTHER" if fw else "-"))
        with open(timeline, "a", encoding="utf-8") as tf:
            tf.write(f"{ts_full()},{tsb},{sk},{md},\"{fw[:70]}\"\n")
        if snap != last:
            ev(f"t+{tsb}s  secure_key={sk}  mobile_data={md}  focus={fw[:60]}")
            last = snap
        if (not dialog_dumped) and "ConfirmData" in fw:
            adb_sh("uiautomator dump /sdcard/_lgu_dlg.xml", timeout=15)
            _, xml = adb_sh("cat /sdcard/_lgu_dlg.xml", timeout=10)
            if "<hierarchy" in xml:  # retry-until-valid: don't lock in a bad dump
                (out / "dialog_ui.xml").write_text(xml, encoding="utf-8", errors="replace")
                ev(f"dialog UI dumped -> dialog_ui.xml ({len(xml)} bytes)")
                dialog_dumped = True
            else:
                ev(f"dialog dump not valid yet (len={len(xml)}), will retry")
        if auto_tap and (not tapped_done) and "ConfirmData" in fw:
            ok, info = auto_tap_use()
            ev(f"AUTO-TAP @ t+{round(time.time()-t_boot,1)}s -> {ok} {info} "
               f"(compare vs performOffData timestamps in odin_consent_grep)")
            if ok:
                tapped_done = True
        time.sleep(0.5)

    ev(f"observation window ended (t+{round(time.time()-t_boot,1)}s)")
    ev("final secure_key=%s mobile_data=%s focus=%s"
       % (get_secure_key(), get_mobile_data(), get_focus()[:60]))
    try:
        lc.terminate()
        lc.wait(timeout=10)
    except Exception:
        lc.kill()
    lf.close()
    ev(f"logcat capture stopped. evidence dir: {out}")

    # quick post-hoc extraction of the key sequence from full logcat
    try:
        txt = logcat_path.read_text(encoding="utf-8", errors="replace")
        keys = [ln for ln in txt.splitlines()
                if ("OdinConfirmData" in ln or SECURE_KEY in ln
                    or "dynamic Switch Apn" in ln or "USER_PRESENT" in ln
                    or "BOOT_COMPLETED" in ln)]
        (out / "odin_consent_grep.txt").write_text("\n".join(keys), encoding="utf-8")
        ev(f"odin_consent_grep.txt written ({len(keys)} lines)")
    except Exception as e:
        ev(f"grep extract failed: {e}")


if __name__ == "__main__":
    main()
