#!/usr/bin/env python3
"""ODIN2 Z0513U Data Popup Race repro loop.

USB 연결 상태에서 reboot 후 OdinConfirmDataDialog "사용" 응답에서
UI(mobile_data=ON) vs 실제 인터넷 도달이 일치하는지 N cycles 측정.
PASS 판정 = Android IS_VALIDATED (end-to-end). SKT IPv6-only/464XLAT 에서
IPv4 ICMP는 CLAT 미통과가 정상이라 ping4는 진단 신호로만 기록한다.

QXDM + ADB 셋업 가정: 도구는 adb 통로만 사용 (diag port 비방해).
USB composition 전환은 사용자 영역 (도구는 라벨만 기록).

사용법:
    python scripts/data_popup_repro_loop.py -n 3 --variant V1
    python scripts/data_popup_repro_loop.py -n 10 --variant V2 --serial f2bfcc3c
    python scripts/data_popup_repro_loop.py -n 3 --sample-times 0,15,60,180
    python scripts/data_popup_repro_loop.py -n 10 --variant V2 --serial f2bfcc3c --early-tap
    python scripts/data_popup_repro_loop.py -n 1 --variant V2-manual --serial f2bfcc3c --manual-tap
"""

import argparse
import csv
import datetime
import re
import subprocess
import sys
import time
from pathlib import Path

# Windows console default cp949 cannot encode some unicode chars.
# Force UTF-8 stdout so device-side Korean/unicode dump output is safe.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ADB = "adb"
DEVICE = None
EARLY_TAP = False  # --early-tap: skip adb-stable dwell, tap dialog ASAP (H-A test)
MANUAL_TAP = False  # --manual-tap: tool reboots+monitors, human taps the dialog
# Post-tap dwell capped at 60s then reboot: post-boot wait shown not to affect
# the verdict, so long sampling is unnecessary -> faster cycling, more reboots.
SAMPLE_TIMES_DEFAULT = "0,30,60"
BOOT_BUDGET = 120
DIALOG_BUDGET = 60
MANUAL_TAP_BUDGET = 180  # how long to wait for the human's manual tap (mobile_data flip)
RECOVER_BUDGET = 180  # FAIL -> watch for delayed recovery up to N s (0 disables)
RECOVER_POLL = 10
KNOWN_USE_BTN = (560, 952)  # OdinConfirmDataDialog button1 center, stable across 50+ cycles
ADB_STABLE_WINDOW = 20
ADB_STABLE_BUDGET = 150


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def ts_full():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_pair():
    """(KST local, UTC) wall-clock strings for QXDM offline join.
    Modem .qmdl timestamps are UTC; device local is KST (UTC+9)."""
    loc = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return loc, utc


# Decisive logcat lines for the per-cycle signature.txt (B) and
# the FAIL-0xffff-loop classifier (A). All logcat-observable; the
# modem PS-route/ACL chain itself is QXDM-only (see ANALYSIS doc).
_SIG_RE = re.compile(
    r"OdinConfirmDataBootReceiver: performOffData"
    r"|kt_skt_allowed_data_by_user"
    r"|OdinConfirmDataDialogActivity: (onCreate|showConfirmDataDialog|click)"
    r"|onDataEnabledChanged: enabled="
    r"|SETUP_DATA_CALL DataCallResponse: \{ cause="
    r"|validation (passed|failed)|IS_VALIDATED"
    r"|internet\.lguplus\.co\.kr, state="
    r"|(Detach|Attach) (request|accept|complete)"
)
_0XFFFF_RE = re.compile(r"SETUP_DATA_CALL DataCallResponse: \{ cause=ERROR_UNSPECIFIED\(0xffff\)")
# Cleanest BUG-25796 signal: framework gives up the internet PDN with 0xffff.
_INET_FAIL_RE = re.compile(
    r"onDataNetworkSetupDataFailed.*internet\.lguplus\.co\.kr.*ERROR_UNSPECIFIED\(0xffff\)")
_VALID_RE = re.compile(r"validation passed|IS_VALIDATED")
_INET_DISC_RE = re.compile(r"internet\.lguplus\.co\.kr, state=Disconnect")
# logcat threadtime prefix: "MM-DD HH:MM:SS.mmm ..."
_LOGTS_RE = re.compile(r"^(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})\.")


def _log_line_tuple(line):
    """(month,day,hh,mm,ss) from a logcat threadtime line, else None.
    Buffers from `-b radio -b main` are concatenated (NOT globally
    time-sorted), so post-tap must be filtered by timestamp, not by
    line position."""
    m = _LOGTS_RE.match(line)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def write_signature(iter_dir, log_text, tap_wall_clock):
    """B: decisive lines -> signature.txt.
    A: time-filtered post-tap stats for the FAIL-0xffff-loop classifier.
    tap_wall_clock = "%Y-%m-%d %H:%M:%S" (local). Returns dict."""
    tap_tuple = None
    if tap_wall_clock:
        try:
            dt = datetime.datetime.strptime(tap_wall_clock, "%Y-%m-%d %H:%M:%S")
            tap_tuple = (dt.month, dt.day, dt.hour, dt.minute, dt.second)
        except ValueError:
            tap_tuple = None

    def is_post(line):
        if tap_tuple is None:
            return True
        t = _log_line_tuple(line)
        return t is not None and t >= tap_tuple

    lines = log_text.splitlines()
    sig = [ln for ln in lines if _SIG_RE.search(ln)]
    n_ffff = sum(1 for ln in lines if is_post(ln) and _0XFFFF_RE.search(ln))
    n_inet_fail = sum(1 for ln in lines if is_post(ln) and _INET_FAIL_RE.search(ln))
    validated = any(is_post(ln) and _VALID_RE.search(ln) for ln in lines)
    inet_disc = any(is_post(ln) and _INET_DISC_RE.search(ln) for ln in lines)
    (iter_dir / "signature.txt").write_text(
        f"# tap_wall_clock: {tap_wall_clock}  (post-tap = logcat ts >= tap, time-filtered)\n"
        f"# post-tap onDataNetworkSetupDataFailed internet.lguplus 0xffff: {n_inet_fail}\n"
        f"# post-tap SETUP_DATA_CALL cause=ERROR_UNSPECIFIED(0xffff): {n_ffff}\n"
        f"# post-tap validation passed/IS_VALIDATED present: {validated}\n"
        f"# post-tap internet.lguplus DisconnectedState: {inet_disc}\n\n"
        + "\n".join(sig) + "\n",
        encoding="utf-8", errors="replace")
    return {"n_0xffff_posttap": n_ffff,
            "n_inet_fail_posttap": n_inet_fail,
            "posttap_validated": validated,
            "internet_disconnected": inet_disc}


def write_qxdm_join(iter_dir, evlog):
    """C: reboot/boot/tap/sample anchors in KST+UTC for offline QXDM join."""
    body = ["# QXDM offline join — modem .qmdl=UTC, device local=KST(UTC+9)",
            "# event\tlocal(KST)\tUTC"]
    for label, loc, utc in evlog:
        body.append(f"{label}\t{loc}\t{utc}")
    (iter_dir / "qxdm_join.txt").write_text("\n".join(body) + "\n",
                                            encoding="utf-8", errors="replace")


def adb_cmd(args, timeout=30):
    cmd = [ADB]
    if DEVICE:
        cmd += ["-s", DEVICE]
    cmd += args
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, f"ERR:{e}"


def _adb_dead(rc, out):
    return (rc != 0
            or out == "TIMEOUT"
            or out.startswith("ERR:")
            or "device '" in out and "not found" in out
            or "device offline" in out
            or "no devices" in out)


def adb_alive(timeout=8):
    """Real round-trip check: echo sentinel through adb shell."""
    rc, out = adb_cmd(["shell", "echo __ADBOK__"], timeout=timeout)
    return (rc == 0) and ("__ADBOK__" in out)


def adb_reconnect():
    adb_cmd(["reconnect"], timeout=10)
    time.sleep(2)
    adb_cmd(["wait-for-device"], timeout=30)


def adb_sh(s, timeout=30, retry=True):
    rc, out = adb_cmd(["shell", s], timeout=timeout)
    if retry and _adb_dead(rc, out):
        adb_reconnect()
        rc, out = adb_cmd(["shell", s], timeout=timeout)
    return rc, out


def wait_for_adb_stable(stable_window=ADB_STABLE_WINDOW, poll=3, budget=ADB_STABLE_BUDGET):
    """Wait until adb is CONTINUOUSLY alive for `stable_window` seconds.

    Composition drift on this device causes a late USB re-enumeration
    (~60s after boot_completed). A single point check passes falsely,
    so require a sustained stable window; reset on any drop and
    issue adb reconnect to help Windows re-bind the USB driver."""
    start = time.time()
    deadline = start + budget
    stable_since = None
    while time.time() < deadline:
        if adb_alive():
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= stable_window:
                return True, round(time.time() - start, 1)
        else:
            stable_since = None
            adb_reconnect()
        time.sleep(poll)
    return False, round(time.time() - start, 1)


def wait_for_boot(timeout=BOOT_BUDGET):
    adb_cmd(["wait-for-device"], timeout=timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out = adb_sh("getprop sys.boot_completed", timeout=10, retry=False)
        if out.strip() == "1":
            return True
        time.sleep(2)
    return False


def get_boot_id():
    rc, out = adb_sh("cat /proc/sys/kernel/random/boot_id")
    return out.strip()


def get_usb_config():
    rc, out = adb_sh("getprop sys.usb.config")
    return out.strip()


def wait_for_usb_ready(required_funcs, stable_window=ADB_STABLE_WINDOW, budget=ADB_STABLE_BUDGET):
    """Ensure adb channel is sustained-stable, then read sys.usb.config.

    Returns (stable_ok, funcs_ok, final_config, elapsed_sec).
    - stable_ok: adb survived continuously for stable_window (re-enum settled)
    - funcs_ok: required_funcs all present in sys.usb.config (warn-only;
      this device drifts composition across reboots so not enforced)"""
    stable_ok, elapsed = wait_for_adb_stable(stable_window=stable_window, budget=budget)
    cfg = get_usb_config() if stable_ok else ""
    funcs_ok = bool(cfg) and all(f in cfg for f in required_funcs)
    return stable_ok, funcs_ok, cfg, elapsed


def setup_logcat_for_cycle():
    """Enlarge all ring buffers and clear, so this cycle starts fresh.
    -b all covers main/radio/system/events/crash for framework + RIL + NAS
    signals across the longer (~4 min) cycle with 180s recovery-watch."""
    for buf in ("main", "radio", "system", "events", "crash"):
        adb_sh(f"logcat -G 16M -b {buf}", timeout=10)
    adb_sh("logcat -c -b all", timeout=10)


def dump_cycle_logcat(out_path):
    """Per-cycle logcat snapshot (PASS and FAIL both, for comparison)."""
    rc, log = adb_sh("logcat -d -b all -v threadtime", timeout=60)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(log, encoding="utf-8", errors="replace")
    return out_path, log


def get_focused_window():
    rc, out = adb_sh("dumpsys window | grep mCurrentFocus")
    return out.strip()


def wake_and_unlock():
    """After reboot the device sits on keyguard; the consent dialog only
    appears once keyguard is dismissed. Replicates the user's wake+swipe."""
    adb_sh("input keyevent KEYCODE_WAKEUP")
    time.sleep(1)
    adb_sh("wm dismiss-keyguard")
    time.sleep(2)


def detect_dialog(budget=DIALOG_BUDGET, poll=2, focus_only=False):
    """Detect the carrier mobile-data consent dialog.

    Activity = com.android.phone/.OdinConfirmDataDialogActivity on ODIN2
    (Lens* on other devices). Match generically on 'ConfirmDataDialog'.
    Fallback = UI dump containing the dialog's stable resource-ids.

    focus_only: skip the ~3s per-iteration uiautomator-dump fallback. On
    ODIN2 the dialog always grabs mCurrentFocus, so for early-tap this
    cuts detection lag without losing reliability."""
    deadline = time.time() + budget
    last = ""
    while time.time() < deadline:
        if not adb_alive():
            adb_reconnect()
            time.sleep(poll)
            continue
        win = get_focused_window()
        last = win
        if "ConfirmDataDialog" in win:
            return True, win
        if not focus_only:
            rc, xml = adb_sh("uiautomator dump //sdcard/_chk.xml >/dev/null 2>&1 && cat //sdcard/_chk.xml", timeout=12)
            if rc == 0 and ("com.android.phone:id/message" in xml or "ConfirmDataDialog" in xml):
                return True, win + " (UI-dump fallback)"
        time.sleep(poll)
    return False, last or get_focused_window()


def _node_center(xml, attr, value):
    """Center (cx,cy) of the <node> whose attr equals value, else None."""
    for m in re.finditer(r'<node\b[^>]*?/?>', xml):
        node = m.group(0)
        if f'{attr}="{value}"' in node:
            b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def tap_use_button():
    """Tap the positive button. Primary anchor = android:id/button1
    (locale-independent). Fallback = text 'Use' / '사용'."""
    rc, _ = adb_sh("uiautomator dump //sdcard/_dlg.xml", timeout=15)
    if rc != 0:
        return False, "DUMP_FAIL"
    rc, xml = adb_sh("cat //sdcard/_dlg.xml", timeout=10)
    if rc != 0 or not xml:
        return False, "CAT_FAIL"
    center = _node_center(xml, "resource-id", "android:id/button1")
    anchor = "button1"
    if center is None:
        for txt in ("Use", "사용"):
            center = _node_center(xml, "text", txt)
            if center:
                anchor = f"text:{txt}"
                break
    if center is None:
        return False, "NO_USE_BTN"
    cx, cy = center
    adb_sh(f"input tap {cx} {cy}")
    return True, f"{anchor}({cx},{cy})"


def sample_state():
    out = {}
    if not adb_alive():
        adb_reconnect()
        if not adb_alive():
            return {"adb_lost": True, "mobile_data": "ADB_LOST", "data_conn_state": "-",
                    "rmnet_ipv4": "-", "default_route": "-", "validated": 0,
                    "ping6_ok": 0, "ping_ok": 0, "ping_ms": "-"}
    _, m1 = adb_sh("settings get global mobile_data")
    out["mobile_data"] = m1.strip()
    _, ds = adb_sh("dumpsys telephony.registry | grep -E 'mDataConnectionState=' | head -1")
    m = re.search(r'mDataConnectionState=(\d+)', ds)
    out["data_conn_state"] = m.group(1) if m else "?"
    _, ip = adb_sh("ip -o addr show | grep -E 'rmnet_data[0-9]+ +inet '")
    m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip)
    out["rmnet_ipv4"] = m.group(1) if m else "-"
    _, rt = adb_sh("ip route show default")
    rt = rt.strip()
    if "rmnet" in rt:
        out["default_route"] = "rmnet"
    elif rt:
        out["default_route"] = "other"
    else:
        out["default_route"] = "-"
    # PRIMARY truth = Android end-to-end validation. SKT is IPv6-only + 464XLAT,
    # so IPv4 ICMP to a literal never traverses CLAT even on a working connection.
    # IS_VALIDATED means Android's own HTTP probe reached the internet.
    _, nai = adb_sh("dumpsys connectivity | grep -E 'NetworkAgentInfo.*ni.MOBILE'", timeout=15)
    validated = 0
    for ln in nai.splitlines():
        if "CONNECTED" in ln and "IS_VALIDATED" in ln and "INTERNET" in ln:
            validated = 1
            break
    out["validated"] = validated
    # AUX = IPv6 reachability (works on IPv6-only/464XLAT; classify does not gate on it)
    _, p6 = adb_sh("ping6 -c 2 -W 2 2001:4860:4860::8888", timeout=15)
    out["ping6_ok"] = 1 if "2 received" in p6 else 0
    # DIAGNOSTIC only = legacy IPv4 ICMP. Expected to fail on SKT (CLAT). Not gating.
    _, p = adb_sh("ping -c 2 -W 2 8.8.8.8", timeout=15)
    if "2 received" in p:
        out["ping_ok"] = 1
        mm = re.search(r'rtt[^=]+=\s*[\d.]+/([\d.]+)/', p)
        out["ping_ms"] = mm.group(1) if mm else "?"
    elif "1 received" in p:
        out["ping_ok"] = 0
        out["ping_ms"] = "1of2"
    else:
        out["ping_ok"] = 0
        out["ping_ms"] = "-"
    return out


def classify(samples, sample_times):
    """PASS = Android IS_VALIDATED (end-to-end) at any sample.

    The consent->mobile_data flip propagates a few seconds AFTER tap, so
    md is often still 0 at T+0 on a genuine repro. Gating MOBILE_OFF on
    T+0 alone mislabels the bug as benign -> only call MOBILE_OFF when md
    stayed 0 for the WHOLE window. (Trial 20260519T192342 surfaced this.)"""
    present = [samples[t] for t in sample_times if t in samples]
    if not present:
        return "NO-SAMPLE", -1
    for idx, t in enumerate(sample_times):
        s = samples.get(t)
        if s and s.get("validated") == 1:
            return ("PASS", -1) if idx == 0 else ("PASS-delayed", t)
    if all(s.get("adb_lost") for s in present):
        return "ADB_LOST", -1
    # mobile_data never turned on across the whole window = consent didn't apply.
    if all(str(s.get("mobile_data")) != "1" for s in present):
        return "MOBILE_OFF", -1
    # md ON at some point but never validated through last sample = the bug path
    # (refined to FAIL-0xffff-loop by the post-tap signature in run_iteration).
    return "FAIL-novalidate", -1


def recovery_watch(tap_epoch, budget=None, poll=None):
    """BUG-25796 is FAIL-then-(often)-delayed-recovery, not always permanent.
    The 60s sample window is too short to see recovery, so after a FAIL keep
    polling until Android validates the connection or `budget` expires.

    Returns (recovered: bool, recover_sec: float|-1, last: dict).
    recover_sec = seconds from tap to first IS_VALIDATED."""
    if budget is None:
        budget = RECOVER_BUDGET
    if poll is None:
        poll = RECOVER_POLL
    if budget <= 0 or not tap_epoch:
        return False, -1, {}
    deadline = time.time() + budget
    last = {}
    print(f"[{ts()}] FAIL -> recovery watch up to {budget}s (poll {poll}s)", flush=True)
    while time.time() < deadline:
        last = sample_state()
        rec_s = round(time.time() - tap_epoch, 1)
        if last.get("validated") == 1:
            print(f"[{ts()}] RECOVERED at tap+{rec_s}s "
                  f"(md={last.get('mobile_data')} dc={last.get('data_conn_state')} "
                  f"ip={last.get('rmnet_ipv4')})", flush=True)
            return True, rec_s, last
        if last.get("adb_lost"):
            adb_reconnect()
        print(f"[{ts()}] watch tap+{rec_s}s: md={last.get('mobile_data')} "
              f"dc={last.get('data_conn_state')} ip={last.get('rmnet_ipv4')} "
              f"val={last.get('validated')}", flush=True)
        time.sleep(poll)
    print(f"[{ts()}] NO recovery within {budget}s -> FAIL-persistent", flush=True)
    return False, -1, last


def dump_fail_evidence(out_dir, iteration):
    """Additional evidence on FAIL (logcat already dumped per-cycle separately)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    _, tel = adb_sh("dumpsys telephony.registry", timeout=15)
    (out_dir / "dumpsys_telephony.txt").write_text(tel, encoding="utf-8", errors="replace")
    _, conn = adb_sh("dumpsys connectivity", timeout=15)
    (out_dir / "dumpsys_connectivity.txt").write_text(conn, encoding="utf-8", errors="replace")
    adb_sh("uiautomator dump //sdcard/_fail.xml", timeout=15)
    _, ui = adb_sh("cat //sdcard/_fail.xml", timeout=10)
    (out_dir / "ui_dump.xml").write_text(ui, encoding="utf-8", errors="replace")
    adb_sh("screencap -p //sdcard/_fail.png", timeout=10)
    adb_cmd(["pull", "//sdcard/_fail.png", str(out_dir / "screen.png")], timeout=15)


def do_sampling(sample_times, label="T"):
    """Sample at each offset (seconds from now). Abort early if adb is lost."""
    samples = {}
    start = time.time()
    for t in sample_times:
        wait = (start + t) - time.time()
        if wait > 0:
            time.sleep(wait)
        s = sample_state()
        samples[t] = s
        print(f"[{ts()}] {label}+{t}s: md={s['mobile_data']} dc={s['data_conn_state']} "
              f"ip={s['rmnet_ipv4']} route={s.get('default_route','-')} "
              f"val={s.get('validated','-')} p6={s.get('ping6_ok','-')} ping4={s['ping_ok']}", flush=True)
        if s.get("adb_lost"):
            print(f"[{ts()}] adb lost mid-sampling -> aborting remaining samples", flush=True)
            break
    return samples


def run_iteration(i, total, sample_times, out_root, required_funcs):
    row = {"iter": i, "iter_start": ts_full()}
    evlog = []  # (label, local, utc) anchors for QXDM offline join (C)
    print(f"\n===== iter {i}/{total} [{ts()}] =====", flush=True)

    row["boot_id_pre"] = get_boot_id()
    row["usb_config_pre"] = get_usb_config()
    print(f"[{ts()}] pre boot_id={row['boot_id_pre'][:8]} usb={row['usb_config_pre']}", flush=True)

    print(f"[{ts()}] adb reboot", flush=True)
    evlog.append(("reboot_issued", *now_pair()))
    adb_cmd(["reboot"], timeout=15)
    time.sleep(45)
    if not wait_for_boot():
        row.update({"boot_id_post": "", "usb_config_post": "", "usb_ready_sec": -1,
                    "tap_status": "BOOT_FAIL", "tap_coords": "",
                    "classify": "BOOT_FAIL", "recover_sec": -1})
        return row, {}
    t_boot = time.time()
    evlog.append(("boot_completed", *now_pair()))

    row["boot_id_post"] = get_boot_id()
    print(f"[{ts()}] boot_completed=1, post boot_id={row['boot_id_post'][:8]}", flush=True)
    if row["boot_id_post"] == row["boot_id_pre"]:
        print(f"[{ts()}] WARN: boot_id unchanged (USB glitch?)", flush=True)

    if EARLY_TAP or MANUAL_TAP:
        # H-A test: the standard flow's sustained adb-stable dwell delays the
        # tap to boot+~36-42s, which may let a boot-time data-attach race
        # resolve before tap. Here we proceed the instant boot completes so
        # the dialog comes up fast (auto-tap, or human tap in --manual-tap).
        usb_cfg = get_usb_config()
        usb_elapsed = round(time.time() - t_boot, 1)
        row["usb_config_post"] = usb_cfg
        row["usb_ready_sec"] = usb_elapsed
        funcs_ok = bool(usb_cfg) and all(f in usb_cfg for f in required_funcs)
        _lbl = "MANUAL-TAP" if MANUAL_TAP else "EARLY-TAP"
        print(f"[{ts()}] {_lbl}: skip stabilization, proceed at boot+{usb_elapsed:.1f}s. usb.config={usb_cfg}", flush=True)
    else:
        stable_ok, funcs_ok, usb_cfg, usb_elapsed = wait_for_usb_ready(required_funcs)
        row["usb_config_post"] = usb_cfg
        row["usb_ready_sec"] = usb_elapsed
        if not stable_ok:
            print(f"[{ts()}] ADB never stabilized after {usb_elapsed:.1f}s (USB re-enum loop). Cycle aborted.", flush=True)
            row.update({"tap_status": "ADB_LOST", "tap_coords": "", "classify": "ADB_LOST", "recover_sec": -1})
            return row, {}
        print(f"[{ts()}] adb stable {ADB_STABLE_WINDOW}s window (total {usb_elapsed:.1f}s). usb.config={usb_cfg}", flush=True)
    if not funcs_ok:
        print(f"[{ts()}] WARN: required funcs {required_funcs} not all in usb.config (composition drift). QXDM correlation may be partial.", flush=True)

    setup_logcat_for_cycle()
    print(f"[{ts()}] logcat ring buffers enlarged + cleared for this cycle", flush=True)

    wake_and_unlock()
    print(f"[{ts()}] screen woken + keyguard dismissed", flush=True)

    if MANUAL_TAP:
        # A fast human dismisses the dialog before detect_dialog() can catch
        # it, so don't gate on dialog detection here -- the mobile_data flip
        # below IS the tap signal.
        dialog_ok, win = True, "(manual mode: dialog detection skipped)"
    else:
        print(f"[{ts()}] detecting dialog (budget {DIALOG_BUDGET}s)", flush=True)
        dialog_ok, win = detect_dialog(poll=0.5 if EARLY_TAP else 2, focus_only=EARLY_TAP)
    if not dialog_ok:
        row["tap_status"] = "NO-POPUP"
        row["tap_coords"] = win[:60]
        print(f"[{ts()}] NO-POPUP. focused: {win[:80]}", flush=True)
        samples = do_sampling(sample_times)
        c, rec = classify(samples, sample_times)
        row["classify"] = "NO-POPUP" if c == "PASS" else f"NO-POPUP/{c}"
        row["recover_sec"] = rec
        iter_dir = out_root / f"iter_{i:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        dump_cycle_logcat(iter_dir / "logcat_radio_main.txt")
        print(f"[{ts()}] cycle logcat saved: {iter_dir / 'logcat_radio_main.txt'}", flush=True)
        return row, samples

    if not MANUAL_TAP:
        print(f"[{ts()}] dialog detected: {win[:80]}", flush=True)
    if MANUAL_TAP:
        print(f"[{ts()}] >>> MANUAL: tap '사용/Use' on the device NOW "
              f"(waiting up to {MANUAL_TAP_BUDGET}s for mobile_data flip) <<<", flush=True)
        deadline = time.time() + MANUAL_TAP_BUDGET
        while time.time() < deadline:
            _, md = adb_sh("settings get global mobile_data", timeout=10)
            if md.strip() == "1":
                break
            time.sleep(0.5)
        else:
            row.update({"tap_status": "NO-MANUAL-TAP", "tap_coords": "",
                        "classify": "NO-MANUAL-TAP", "recover_sec": -1})
            print(f"[{ts()}] NO-MANUAL-TAP: mobile_data never flipped within {MANUAL_TAP_BUDGET}s", flush=True)
            iter_dir = out_root / f"iter_{i:03d}"
            iter_dir.mkdir(parents=True, exist_ok=True)
            dump_cycle_logcat(iter_dir / "logcat_radio_main.txt")
            return row, {}
        row["tap_status"] = "MANUAL-TAPPED"
        row["tap_coords"] = "manual"
        row["tap_wall_clock"] = ts_full()
        row["tap_after_boot_sec"] = round(time.time() - t_boot, 1)
        row["_tap_epoch"] = time.time()
        evlog.append(("tap", *now_pair()))
        print(f"[{ts()}] manual tap detected (mobile_data=1) at {row['tap_wall_clock']} "
              f"(boot+{row['tap_after_boot_sec']}s)", flush=True)
    else:
        if EARLY_TAP:
            # Fast path: skip the ~3s uiautomator dump used to locate the
            # button. button1 center has been (560,952) for 50+ cycles on
            # this fixed device. Tap it, then verify mobile_data flipped;
            # if not, fall back to the dump-based locate (no reliability loss).
            kx, ky = KNOWN_USE_BTN
            adb_sh(f"input tap {kx} {ky}")
            time.sleep(1.5)
            _, _md = adb_sh("settings get global mobile_data", timeout=10)
            if _md.strip() == "1":
                tapped, info = True, f"fast({kx},{ky})"
            else:
                print(f"[{ts()}] fast-tap not confirmed, fallback to UI-dump locate", flush=True)
                tapped, info = tap_use_button()
        else:
            tapped, info = tap_use_button()
        if not tapped:
            row.update({"tap_status": "TAP-FAIL", "tap_coords": info, "classify": "TAP-FAIL", "recover_sec": -1})
            print(f"[{ts()}] TAP FAILED: {info}", flush=True)
            return row, {}
        row["tap_status"] = "TAPPED"
        row["tap_coords"] = info
        row["tap_wall_clock"] = ts_full()
        row["tap_after_boot_sec"] = round(time.time() - t_boot, 1)
        row["_tap_epoch"] = time.time()
        evlog.append(("tap", *now_pair()))
        print(f"[{ts()}] tapped Use button: {info} (boot+{row['tap_after_boot_sec']}s)", flush=True)

    evlog.append(("sample_start", *now_pair()))
    samples = do_sampling(sample_times)
    evlog.append(("sample_end", *now_pair()))
    c, rec = classify(samples, sample_times)

    iter_dir = out_root / f"iter_{i:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    _, log_text = dump_cycle_logcat(iter_dir / "logcat_radio_main.txt")
    print(f"[{ts()}] cycle logcat saved: {iter_dir / 'logcat_radio_main.txt'}", flush=True)

    # B: per-cycle decisive-line summary + A: post-tap signature stats
    sig = write_signature(iter_dir, log_text, row.get("tap_wall_clock"))
    # A: refine the generic FAIL into the confirmed BUG-25796 signature when the
    # post-tap PDN bring-up loops on ERROR_UNSPECIFIED(0xffff) for the internet
    # APN and no post-tap validation occurred. Primary signal =
    # onDataNetworkSetupDataFailed(internet.lguplus, 0xffff); raw SETUP_DATA_CALL
    # 0xffff as fallback. (ps_route/ACL chain itself is QXDM-side, not logcat.)
    if (c == "FAIL-novalidate" and not sig["posttap_validated"]
            and (sig["n_inet_fail_posttap"] >= 2 or sig["n_0xffff_posttap"] >= 3)):
        c = "FAIL-0xffff-loop"
    row["classify"] = c
    row["recover_sec"] = rec
    row["sig_0xffff_posttap"] = sig["n_0xffff_posttap"]
    print(f"[{ts()}] classify={c} (post-tap inet_fail x{sig['n_inet_fail_posttap']}, "
          f"0xffff x{sig['n_0xffff_posttap']}, inet_disc={sig['internet_disconnected']})", flush=True)

    # BUG-25796 is FAIL-then-(often)-delayed-recovery. Keep the signature
    # verdict as fail_phase, then watch for recovery -> FAIL-recover(latency)
    # vs FAIL-persistent. recover_sec = tap->IS_VALIDATED seconds.
    if c.startswith("FAIL") and RECOVER_BUDGET > 0:
        row["fail_phase"] = c
        recovered, rsec, _ = recovery_watch(row.get("_tap_epoch"))
        if recovered:
            c = "FAIL-recover"
            row["recover_sec"] = rsec
            evlog.append(("recovered", *now_pair()))
        else:
            c = "FAIL-persistent"
            evlog.append(("recover_timeout", *now_pair()))
        row["classify"] = c
        print(f"[{ts()}] final classify={c} recover_sec={row['recover_sec']} "
              f"(fail_phase={row['fail_phase']})", flush=True)

    # C: QXDM offline join anchors (KST+UTC)
    write_qxdm_join(iter_dir, evlog)

    if c.startswith("FAIL"):
        print(f"[{ts()}] FAIL -> dumping additional evidence to {iter_dir}", flush=True)
        dump_fail_evidence(iter_dir, i)

    return row, samples


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--iterations", type=int, default=3)
    p.add_argument("--variant", default="?", help="USB composition label (V1=MODEM+DM+ADB / V2=+RMNET+ADPL+QDSS / ?)")
    p.add_argument("--serial", default=None)
    p.add_argument("--sample-times", default=SAMPLE_TIMES_DEFAULT)
    p.add_argument("--require-funcs", default="diag,adb",
                   help="comma-separated USB functions to verify after boot (default: diag,adb for QXDM+ADB)")
    p.add_argument("--early-tap", action="store_true",
                   help="H-A test: skip adb-stable dwell, tap consent dialog ASAP after boot")
    p.add_argument("--manual-tap", action="store_true",
                   help="tool reboots+monitors only; human taps the dialog (waits for mobile_data flip)")
    p.add_argument("--recover-budget", type=int, default=180,
                   help="after FAIL, watch for delayed recovery up to N s (default 180, 0=disable)")
    args = p.parse_args()

    global DEVICE, EARLY_TAP, MANUAL_TAP, RECOVER_BUDGET
    DEVICE = args.serial
    EARLY_TAP = args.early_tap
    MANUAL_TAP = args.manual_tap
    RECOVER_BUDGET = args.recover_budget

    sample_times = [int(s) for s in args.sample_times.split(",")]
    required_funcs = [f.strip() for f in args.require_funcs.split(",") if f.strip()]
    run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out_root = Path("logs") / "data_popup_repro" / run_id
    out_root.mkdir(parents=True, exist_ok=True)
    csv_path = out_root / "results.csv"

    usb_now = get_usb_config()
    mode = ("MANUAL-TAP (human taps, tool monitors)" if MANUAL_TAP
            else "EARLY-TAP (skip stabilization)" if EARLY_TAP
            else "standard (adb-stable dwell)")
    print(f"[{ts_full()}] run_id={run_id} variant={args.variant} mode={mode} sys.usb.config={usb_now}", flush=True)
    print(f"[{ts_full()}] out={out_root}", flush=True)
    print(f"[{ts_full()}] N={args.iterations} samples={sample_times}", flush=True)
    print(f"[{ts_full()}] require_funcs={required_funcs}", flush=True)
    print(f"[{ts_full()}] NOTE: QXDM bookmark sync - wall-clock timestamps in [HH:MM:SS]", flush=True)

    cols = ["iter", "iter_start", "tap_wall_clock", "tap_after_boot_sec",
            "boot_id_pre", "boot_id_post",
            "usb_config_pre", "usb_config_post", "usb_ready_sec",
            "tap_status", "tap_coords", "classify", "fail_phase", "recover_sec", "sig_0xffff_posttap"]
    for t in sample_times:
        cols += [f"t{t}_md", f"t{t}_dc", f"t{t}_ip", f"t{t}_rt",
                 f"t{t}_val", f"t{t}_p6", f"t{t}_ping4", f"t{t}_ms"]

    results = []
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in range(1, args.iterations + 1):
            row, samples = run_iteration(i, args.iterations, sample_times, out_root, required_funcs)
            csv_row = [row.get(k, "") for k in ["iter", "iter_start", "tap_wall_clock",
                                                  "tap_after_boot_sec", "boot_id_pre",
                                                  "boot_id_post", "usb_config_pre", "usb_config_post",
                                                  "usb_ready_sec", "tap_status", "tap_coords",
                                                  "classify", "fail_phase", "recover_sec",
                                                  "sig_0xffff_posttap"]]
            for t in sample_times:
                s = samples.get(t, {})
                csv_row += [s.get("mobile_data", ""), s.get("data_conn_state", ""), s.get("rmnet_ipv4", ""),
                            s.get("default_route", ""), s.get("validated", ""), s.get("ping6_ok", ""),
                            s.get("ping_ok", ""), s.get("ping_ms", "")]
            w.writerow(csv_row)
            f.flush()
            results.append(row)

    print(f"\n===== summary [{ts_full()}] =====", flush=True)
    tally = {}
    for r in results:
        c = r.get("classify", "?")
        tally[c] = tally.get(c, 0) + 1
    print(f"variant: {args.variant}", flush=True)
    print(f"sys.usb.config(initial): {usb_now}", flush=True)
    print(f"require_funcs: {required_funcs}", flush=True)
    print(f"tally: {tally}", flush=True)
    recs = [r["recover_sec"] for r in results if str(r.get("classify", "")).startswith("FAIL-recover")]
    if recs:
        print(f"recover stats: n={len(recs)} avg={sum(recs)/len(recs):.1f}s max={max(recs)}s", flush=True)
    usb_ready = [r.get("usb_ready_sec", -1) for r in results if isinstance(r.get("usb_ready_sec"), (int, float)) and r.get("usb_ready_sec", -1) >= 0]
    if usb_ready:
        print(f"usb ready stats: n={len(usb_ready)} avg={sum(usb_ready)/len(usb_ready):.1f}s max={max(usb_ready):.1f}s", flush=True)
    print(f"csv: {csv_path}", flush=True)
    print(f"out: {out_root}", flush=True)

    summary_path = out_root / "summary.txt"
    summary_path.write_text(
        f"run_id: {run_id}\nvariant: {args.variant}\nsys.usb.config(initial): {usb_now}\n"
        f"require_funcs: {required_funcs}\niterations: {args.iterations}\nsample_times: {sample_times}\n\n"
        f"tally:\n" + "\n".join(f"  {k}: {v}" for k, v in tally.items()) + "\n",
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
