#!/usr/bin/env python3
"""THOR2_J in-call multitask memory-stress repro loop.

On a low-RAM device (THOR2_J / AT-M140, ~2.8GB + zram, ro.config.low_ram=true),
place an unattended MO call, then rapidly launch foreground apps (YouTube,
Messages, LINE, YouTube Music) to stress memory while the call is active, and
MEASURE the failure rate over N cycles.

Target verdict failures (decide the rate):
  - FAIL-CRASH : a launched test app FATAL-crashes / Force-closes
  - FAIL-ANR   : a launched test app ANRs / freezes

Context signals (recorded, NOT verdict — expected low-RAM behavior = NOTE):
  - background eviction storm (am_kill cached/empty), lmkd kills
  - foreground app restart "튕김" (a launched app evicted then cold-restarted)
  - jank (Choreographer Skipped frames)

Device truth captured during Phase 0 (serial B2700125BW000083):
  - dial    : am start -a android.intent.action.CALL -d tel:<callee>  (-> com.android.dialer)
  - gate    : dumpsys telecom 'state=ACTIVE' (~6s); audio mode is NOT reliable here
  - hangup  : input keyevent KEYCODE_ENDCALL  (NEVER Power: side Power=End but short=SLEEP)
  - focus   : dumpsys activity activities | topResumedActivity=  (NOT grep -m1 mFocusedApp)
  - signal  : logcat -b events am_kill / am_proc_died / am_proc_start (adj reason)
  - non-root user build; permission dialogs pre-granted so launches foreground cleanly.

Usage:
    venv/Scripts/python.exe scripts/multitask_call_stress.py \
        --serial B2700125BW000083 --callee <auto-answer-number> -n 5 \
        --apps com.google.android.youtube/.app.honeycomb.Shell$HomeActivity,\
com.android.mms/.ui.ConversationList,jp.naver.line.android/.activity.SplashActivity
    # control arm (no active call), same burst:
    ... --no-call
    # offline verification, no device:
    ... --classify-log path/to/saved_logcat.txt
"""

import argparse
import csv
import datetime
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ADB = "adb"
DEVICE = None  # pinned serial (wrong-device guard)

# ----------------------------------------------------------------------------
# Pure parse/classify core (unit-tested in tests/test_multitask_call_stress.py)
# ----------------------------------------------------------------------------

_MEMINFO_RE = re.compile(r"^(\w+):\s+(\d+)\s+kB", re.MULTILINE)
_TOPACT_RE = re.compile(r"topResumedActivity=ActivityRecord\{\S+ u\d+ (\S+)")
_EV_RE = re.compile(r"am_(kill|proc_died|proc_start)\b.*?\[([^\]]*)\]")
_SKIP_RE = re.compile(r"Skipped (\d+) frames")
_CRASH_RE = re.compile(r"FATAL EXCEPTION|ActivityManager.*has crashed|Force [Cc]losing")
# crash package extraction is tied to a crash block (NOT every "Process:" line —
# benign Zygote "Process 11886 exited" / procstats lines must not count):
#   FATAL block carries  "Process: <pkg>, PID: ..."  (colon + package-like token)
#   inline form          "Process <pkg> ... has crashed"
_CRASH_PROC_RE = re.compile(r"Process:\s+([a-zA-Z][\w.]*\.[\w.:]+)")
_CRASH_INLINE_RE = re.compile(r"Process\s+([a-zA-Z][\w.]*\.[\w.:]+)\s+.*has crashed")
_ANR_RE = re.compile(r"ANR in ([\w.][\w.]*)")
_LMKD_RE = re.compile(r"lowmemorykiller|lmkd|Kill '")


def _to_int(s):
    s = (s or "").strip()
    return int(s) if s.lstrip("-").isdigit() else None


def _base_pkg(pkg):
    """Process name -> base package (strip ':procname' suffix)."""
    return (pkg or "").split(":")[0]


def parse_meminfo(text):
    """`cat /proc/meminfo` -> {field: kB int}."""
    return {k: int(v) for k, v in _MEMINFO_RE.findall(text or "")}


def call_active(text):
    """True if any subscription is OFFHOOK (mCallState=2) in telephony.registry dump."""
    return "mCallState=2" in (text or "")


def telecom_active(text):
    """True if a telecom call is in the ACTIVE (answered) state."""
    return "state=ACTIVE" in (text or "")


def parse_top_activity(text):
    """`dumpsys activity activities` -> 'pkg/activity' of the top resumed activity."""
    m = _TOPACT_RE.search(text or "")
    return m.group(1) if m else None


def parse_am_events(text):
    """logcat events buffer -> list of {type,pid,pkg,adj,reason} for am_kill/died/start.

    am_kill / am_proc_died : [user, pid, pkg, adj, reason]
    am_proc_start          : [user, pid, uid, pkg, reason, {component}]  (uid offset!)
    """
    out = []
    for kind, body in _EV_RE.findall(text or ""):
        f = [x.strip() for x in body.split(",")]
        try:
            if kind == "proc_start":
                rec = {"type": "start", "pid": _to_int(f[1]), "pkg": f[3],
                       "adj": None, "reason": f[4] if len(f) > 4 else ""}
            else:
                rec = {"type": "kill" if kind == "kill" else "died",
                       "pid": _to_int(f[1]), "pkg": f[2],
                       "adj": _to_int(f[3]) if len(f) > 3 else None,
                       "reason": f[4] if len(f) > 4 else ""}
        except IndexError:
            continue
        out.append(rec)
    return out


def summarize_evictions(events, launched_pkgs):
    """Background-eviction context counts + which *launched* apps got killed.

    'cached'/'empty' kills are expected low-RAM background eviction (NOTE).
    A launched app appearing here means a return to it would cold-restart.
    """
    launched = set(launched_pkgs or [])
    killed_launched = set()
    n_bg = 0
    n_kill = 0
    for e in events:
        if e["type"] != "kill":
            continue
        n_kill += 1
        reason = e.get("reason", "")
        if "cached" in reason or "empty" in reason:
            n_bg += 1
        if _base_pkg(e["pkg"]) in launched:
            killed_launched.add(_base_pkg(e["pkg"]))
    return {"n_bg_evict": n_bg, "n_kill_total": n_kill,
            "killed_launched_pkgs": sorted(killed_launched)}


def scan_signals(text, test_pkgs):
    """Scan main/system/crash logcat for crash / ANR / jank / lmkd signals.

    Returns crash & ANR packages (all), plus test-app-filtered subsets that
    decide FAIL-CRASH / FAIL-ANR. Jank (max Skipped frames) and lmkd count
    are context.
    """
    text = text or ""
    tset = set(test_pkgs or [])
    lines = text.splitlines()
    # only attribute a package when a crash marker is actually present, and
    # take the "Process:" from the same crash block (next few lines).
    crash_idx = [i for i, ln in enumerate(lines) if _CRASH_RE.search(ln)]
    crash_set = set()
    for i in crash_idx:
        inline = _CRASH_INLINE_RE.search(lines[i])
        if inline:
            crash_set.add(inline.group(1))
            continue
        for j in range(i, min(i + 5, len(lines))):
            m = _CRASH_PROC_RE.search(lines[j])
            if m:
                crash_set.add(m.group(1))
                break
    crash_pkgs = sorted(crash_set)
    anr_pkgs = sorted(set(_ANR_RE.findall(text)))
    frames = [int(x) for x in _SKIP_RE.findall(text)]
    return {
        "n_crash": len(crash_idx),
        "crash_pkgs": crash_pkgs,
        "test_crash_pkgs": [p for p in crash_pkgs if _base_pkg(p) in tset],
        "n_anr": len(_ANR_RE.findall(text)),
        "anr_pkgs": anr_pkgs,
        "test_anr_pkgs": [p for p in anr_pkgs if _base_pkg(p) in tset],
        "max_skipped_frames": max(frames) if frames else 0,
        "n_lmkd": len(_LMKD_RE.findall(text)),
    }


def classify_cycle(rec, jank_threshold=60):
    """Closed-set verdict with confound-first precedence (confounds never score FAIL)."""
    if rec.get("setup_failed"):
        return "ERROR-SETUP"
    if rec.get("rebooted"):
        return "WARN-REBOOT"
    if rec.get("call_dropped"):
        return "WARN-CALLDROP"
    if rec.get("test_crash_pkgs"):
        return "FAIL-CRASH"
    if rec.get("test_anr_pkgs"):
        return "FAIL-ANR"
    if rec.get("crash_pkgs") or rec.get("anr_pkgs"):
        return "WARN-REVIEW"
    if rec.get("fg_restart") or rec.get("fg_killed_not_restarted"):
        return "WARN-FGRESTART"
    if rec.get("max_skipped_frames", 0) >= jank_threshold:
        return "WARN-JANK"
    return "PASS"


def is_failure(verdict):
    """Counts toward the failure numerator (the user's target: crash / ANR)."""
    return verdict in ("FAIL-CRASH", "FAIL-ANR")


def is_excluded(verdict):
    """Confound — excluded from numerator AND denominator, reported separately."""
    return verdict in ("ERROR-SETUP", "WARN-REBOOT", "WARN-CALLDROP")


CSV_HEADER = [
    "cycle", "iter_start_ts", "arm", "boot_id_pre", "boot_id_post", "rebooted",
    "mem_avail_pre_kb", "mem_avail_post_kb", "mem_drained_kb", "swapfree_pre_kb",
    "swapfree_post_kb", "call_state_pre", "telecom_reached", "call_dropped",
    "dial_attempts", "burst_size", "burst_rounds", "apps_launched", "n_focus_confirmed",
    "n_crash", "crash_pkgs", "test_crash_pkgs", "n_anr", "anr_pkgs",
    "test_anr_pkgs", "max_skipped_frames", "n_lmkd", "n_bg_evict",
    "killed_launched_pkgs", "fg_restart", "verdict", "artifact_dir",
]


def record_to_row(rec):
    def cell(v):
        if isinstance(v, (list, tuple, set)):
            return ";".join(str(x) for x in v)
        if isinstance(v, bool):
            return "1" if v else "0"
        return "" if v is None else v
    return [cell(rec.get(k)) for k in CSV_HEADER]


# ----------------------------------------------------------------------------
# adb plumbing (integration; mirrors scripts/data_popup_repro_loop.py contract)
# ----------------------------------------------------------------------------

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def run_id_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    except Exception as e:  # noqa: BLE001
        return -1, f"ERR:{e}"


def _adb_dead(rc, out):
    return (rc != 0 or out == "TIMEOUT" or out.startswith("ERR:")
            or ("device '" in out and "not found" in out)
            or "device offline" in out or "no devices" in out)


def adb_alive(timeout=8):
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


def get_boot_id():
    _, out = adb_sh("cat /proc/sys/kernel/random/boot_id")
    return out.strip()


def assert_target(expected_serial):
    """Wrong-device guard: confirm the pinned serial + AT-M140 class."""
    _, sn = adb_sh("getprop ro.boot.serialno", timeout=10, retry=False)
    _, model = adb_sh("getprop ro.product.model", timeout=10, retry=False)
    sn, model = sn.strip(), model.strip()
    if expected_serial and sn and sn != expected_serial:
        raise SystemExit(f"WRONG DEVICE: ro.boot.serialno={sn!r} != --serial {expected_serial!r}")
    if model and "AT-M140" not in model and "AT_M140" not in model:
        raise SystemExit(f"WRONG DEVICE CLASS: ro.product.model={model!r} (expected AT-M140)")
    return sn, model


def read_meminfo():
    _, out = adb_sh("cat /proc/meminfo")
    return parse_meminfo(out)


def is_call_active():
    _, out = adb_sh("dumpsys telephony.registry | grep mCallState")
    return call_active(out)


def is_telecom_active():
    _, out = adb_sh("dumpsys telecom | grep -m1 'state='")
    return telecom_active(out)


def get_pid(pkg):
    _, out = adb_sh(f"pidof {pkg}")
    out = out.strip()
    return out.split()[0] if out else None


def ensure_awake():
    adb_sh("input keyevent KEYCODE_WAKEUP")
    adb_sh("wm dismiss-keyguard")
    time.sleep(0.5)


def setup_logcat_for_cycle():
    for buf in ("main", "system", "events", "crash"):
        adb_sh(f"logcat -G 16M -b {buf}", timeout=10)
    adb_sh("logcat -c -b all", timeout=10)


def dump_logcat(buffers):
    _, out = adb_sh(f"logcat -d -b {buffers} -v brief", timeout=60)
    return out


def grant_permissions(pkgs):
    """Pre-grant the launch-time runtime permissions so GrantPermissionsActivity
    never intercepts the foreground (Phase 0 confound)."""
    common = ["POST_NOTIFICATIONS", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"]
    line_extra = ["READ_CONTACTS", "WRITE_CONTACTS", "READ_PHONE_STATE", "CALL_PHONE",
                  "CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION", "READ_MEDIA_IMAGES",
                  "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO", "GET_ACCOUNTS", "READ_PHONE_NUMBERS"]
    for pkg in pkgs:
        perms = common + (line_extra if "line" in pkg else [])
        for perm in perms:
            adb_sh(f"pm grant {pkg} android.permission.{perm}", timeout=10)


def dial_call(callee, dial_retries, verify_budget):
    """Place MO call, gate on telecom ACTIVE. Returns (ok, attempts, reached_state)."""
    for attempt in range(1, dial_retries + 1):
        ensure_awake()
        adb_sh(f"am start -a android.intent.action.CALL -d tel:{callee}")
        deadline = time.time() + verify_budget
        while time.time() < deadline:
            if is_telecom_active():
                return True, attempt, "ACTIVE"
            time.sleep(1)
        best_effort_endcall()  # abort this dial before retry
    return False, dial_retries, "NOT_ACTIVE"


def best_effort_endcall():
    """Hang up on every exit path. Idempotent; never raises. Power key is forbidden."""
    for _ in range(2):
        adb_sh("input keyevent KEYCODE_ENDCALL")
        time.sleep(1.5)
        if not is_call_active():
            return True
    return not is_call_active()


def launch_app(activity, force_stop=False):
    pkg = activity.split("/")[0]
    if force_stop:
        adb_sh(f"am force-stop {pkg}", timeout=10)
    # quote so Shell$HomeActivity '$' is literal to the device shell
    adb_sh(f"am start -n '{activity}'", timeout=15)


def run_cycle(idx, args, out_root, expected_serial):
    arm = "NOCALL" if args.no_call else "CALL"
    iter_dir = out_root / f"iter_{idx:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    rec = {"cycle": idx, "iter_start_ts": ts(), "arm": arm,
           "burst_size": min(args.burst_size, len(args.apps)),
           "artifact_dir": str(iter_dir)}

    assert_target(expected_serial)
    rec["boot_id_pre"] = get_boot_id()
    mem_pre = read_meminfo()
    rec["mem_avail_pre_kb"] = mem_pre.get("MemAvailable")
    rec["swapfree_pre_kb"] = mem_pre.get("SwapFree")
    setup_logcat_for_cycle()

    # (b) call setup (CALL arm only)
    if arm == "CALL":
        ok, attempts, reached = dial_call(args.callee, args.dial_retries, args.dial_verify_budget)
        rec["dial_attempts"] = attempts
        rec["telecom_reached"] = reached
        if not ok:
            rec["setup_failed"] = True
            best_effort_endcall()
            return _finalize(rec, iter_dir, args, [], "")
        rec["call_state_pre"] = 2
        time.sleep(args.call_settle)

    # (c) foreground burst — burst_rounds passes over the app list (churn).
    # app1 (args.apps[0]) is the return-to target; enough distinct apps after it
    # evict it -> returning shows a cold restart = the user-visible "튕김".
    launched, first_app, first_pid = [], None, None
    burst = args.apps[:rec["burst_size"]]
    n_focus_ok = 0
    rec["burst_rounds"] = args.burst_rounds
    try:
        for r in range(args.burst_rounds):
            for i, activity in enumerate(burst):
                if arm == "CALL" and not is_call_active():
                    rec["call_dropped"] = True
                    break
                pkg = activity.split("/")[0]
                launch_app(activity, force_stop=False)
                if pkg not in launched:
                    launched.append(pkg)
                # self-verified inter-launch delay -> fixed fallback
                deadline = time.time() + args.launch_verify_budget
                confirmed = False
                while time.time() < deadline:
                    _, act = adb_sh("dumpsys activity activities | grep -m1 topResumedActivity=")
                    top = parse_top_activity(act)
                    if top and top.split("/")[0] == pkg:
                        confirmed = True
                        break
                    time.sleep(0.4)
                if confirmed:
                    n_focus_ok += 1
                else:
                    time.sleep(args.inter_launch_delay)
                if r == 0 and i == 0:
                    first_app, first_pid = pkg, get_pid(pkg)
            if rec.get("call_dropped"):
                break
        # (return-to-first) test the user-visible "튕김": did app1 cold-restart?
        if first_app and not rec.get("call_dropped"):
            launch_app(args.apps[0])
            time.sleep(args.launch_verify_budget)
            last_pid = get_pid(first_app)
            if first_pid and last_pid and last_pid != first_pid:
                rec["fg_restart"] = True
            elif first_pid and not last_pid:
                rec["fg_killed_not_restarted"] = True
    finally:
        if arm == "CALL":
            best_effort_endcall()
        adb_sh("input keyevent KEYCODE_HOME")

    rec["apps_launched"] = launched
    rec["first_app"] = first_app
    rec["n_focus_confirmed"] = n_focus_ok

    # (e) brief recovery watch then capture
    time.sleep(args.recover_budget)
    if arm == "CALL":
        # confound check: did the call survive the whole burst?
        pass
    main_log = dump_logcat("main,system,crash")
    evt_log = dump_logcat("events")
    rec["boot_id_post"] = get_boot_id()
    rec["rebooted"] = bool(rec.get("boot_id_pre") and rec["boot_id_post"]
                           and rec["boot_id_pre"] != rec["boot_id_post"])
    mem_post = read_meminfo()
    rec["mem_avail_post_kb"] = mem_post.get("MemAvailable")
    rec["swapfree_post_kb"] = mem_post.get("SwapFree")
    if rec.get("mem_avail_pre_kb") and rec.get("mem_avail_post_kb"):
        rec["mem_drained_kb"] = rec["mem_avail_pre_kb"] - rec["mem_avail_post_kb"]
    return _finalize(rec, iter_dir, args, parse_am_events(evt_log), main_log, evt_log)


def _finalize(rec, iter_dir, args, events, main_log, evt_log=""):
    sig = scan_signals(main_log, args.pkgs)
    rec.update(sig)
    evic = summarize_evictions(events, rec.get("apps_launched", []))
    rec.update(evic)
    # 튕김 signal (events-based): a *launched* app was evicted during the burst,
    # so returning to it shows a cold restart (lost state). lmkd often kills a
    # heavier launched app (chrome/maps) before app1, so this is not app1-specific.
    if evic["killed_launched_pkgs"]:
        rec["fg_restart"] = True
    rec["verdict"] = classify_cycle(rec, jank_threshold=args.jank_threshold)
    (iter_dir / "signature.txt").write_text(
        f"# verdict: {rec['verdict']}  arm={rec.get('arm')}\n"
        f"# n_crash={sig['n_crash']} test_crash={sig['test_crash_pkgs']} "
        f"n_anr={sig['n_anr']} test_anr={sig['test_anr_pkgs']}\n"
        f"# max_skipped_frames={sig['max_skipped_frames']} n_lmkd={sig['n_lmkd']} "
        f"n_bg_evict={evic['n_bg_evict']} killed_launched={evic['killed_launched_pkgs']}\n"
        f"# fg_restart={rec.get('fg_restart')} mem_drained_kb={rec.get('mem_drained_kb')}\n",
        encoding="utf-8", errors="replace")
    if main_log:
        (iter_dir / "logcat_main.txt").write_text(main_log, encoding="utf-8", errors="replace")
    if evt_log:
        (iter_dir / "logcat_events.txt").write_text(evt_log, encoding="utf-8", errors="replace")
    return rec


def cmd_classify_log(path, pkgs, jank_threshold):
    """Offline verification: scan a saved logcat, print verdict. No device."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    sig = scan_signals(text, pkgs)
    events = parse_am_events(text)
    rec = dict(sig)
    rec.update(summarize_evictions(events, pkgs))
    rec["verdict"] = classify_cycle(rec, jank_threshold=jank_threshold)
    print(f"verdict={rec['verdict']}  n_crash={sig['n_crash']} test_crash={sig['test_crash_pkgs']} "
          f"n_anr={sig['n_anr']} test_anr={sig['test_anr_pkgs']} "
          f"max_skipped_frames={sig['max_skipped_frames']} n_bg_evict={rec['n_bg_evict']}")
    return rec["verdict"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", help="pinned device serial (wrong-device guard)")
    ap.add_argument("--callee", help="MO auto-answer test number (never hardcoded)")
    ap.add_argument("-n", "--cycles", type=int, default=20)
    ap.add_argument("--apps", default=(
        "com.google.android.youtube/.app.honeycomb.Shell$HomeActivity,"
        "com.android.mms/.ui.ConversationList,"
        "jp.naver.line.android/.activity.SplashActivity,"
        "com.google.android.apps.youtube.music/.activities.MusicActivity,"
        "com.android.chrome/com.google.android.apps.chrome.Main,"
        "com.google.android.apps.maps/com.google.android.maps.MapsActivity,"
        "com.android.settings/.Settings,"
        "com.hnlens.contacts/com.android.contacts.activities.PeopleActivity"),
        help="comma-separated pkg/activity launch list (app1 = the return-to/튕김 target)")
    ap.add_argument("--burst-size", type=int, default=99)
    ap.add_argument("--burst-rounds", type=int, default=1,
                    help="passes over the app list per cycle (escalation knob)")
    ap.add_argument("--inter-launch-delay", type=float, default=0.8)
    ap.add_argument("--launch-verify-budget", type=float, default=3.0)
    ap.add_argument("--dial-retries", type=int, default=2)
    ap.add_argument("--dial-verify-budget", type=float, default=15.0)
    ap.add_argument("--call-settle", type=float, default=2.0)
    ap.add_argument("--recover-budget", type=float, default=8.0)
    ap.add_argument("--jank-threshold", type=int, default=60)
    ap.add_argument("--no-call", action="store_true", help="control arm: same burst, no call")
    ap.add_argument("--no-grant", action="store_true", help="skip permission pre-grant")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--classify-log", help="offline: scan a saved logcat, print verdict, exit")
    args = ap.parse_args(argv)

    args.apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    args.pkgs = [a.split("/")[0] for a in args.apps]

    if args.classify_log:
        cmd_classify_log(args.classify_log, args.pkgs, args.jank_threshold)
        return 0

    global DEVICE
    DEVICE = args.serial
    if not args.no_call and not args.callee:
        ap.error("--callee is required unless --no-call")

    run_id = args.run_id or run_id_utc()
    out_root = Path(args.out_root) if args.out_root else (
        Path("logs") / "multitask_call_stress" / run_id)
    out_root.mkdir(parents=True, exist_ok=True)
    csv_path = out_root / "results.csv"

    print(f"[{ts()}] run_id={run_id} arm={'NOCALL' if args.no_call else 'CALL'} "
          f"serial={DEVICE} cycles={args.cycles} apps={len(args.apps)}")
    sn, model = assert_target(args.serial)
    print(f"[{ts()}] device ok: {model} {sn}")
    if not args.no_grant:
        grant_permissions(args.pkgs)

    rows = []
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)
            for i in range(1, args.cycles + 1):
                rec = run_cycle(i, args, out_root, args.serial)
                rows.append(rec)
                w.writerow(record_to_row(rec))
                f.flush()
                print(f"[{ts()}] cycle {i}/{args.cycles}: {rec['verdict']} "
                      f"mem_drained={rec.get('mem_drained_kb')} "
                      f"bg_evict={rec.get('n_bg_evict')} jank={rec.get('max_skipped_frames')}")
    finally:
        best_effort_endcall()

    _print_summary(rows, csv_path)
    return 0


def _print_summary(rows, csv_path):
    counted = [r for r in rows if not is_excluded(r["verdict"])]
    fails = [r for r in counted if is_failure(r["verdict"])]
    excluded = [r for r in rows if is_excluded(r["verdict"])]
    denom = len(counted)
    print("\n==== SUMMARY ====")
    print(f"cycles={len(rows)} counted(denominator)={denom} excluded={len(excluded)}")
    pct = (100.0 * len(fails) / denom) if denom else 0.0
    print(f"FAIL (crash/ANR): {len(fails)}/{denom} = {pct:.1f}%")
    from collections import Counter
    vc = Counter(r["verdict"] for r in rows)
    for v, c in vc.most_common():
        print(f"  {v}: {c}")
    print(f"results.csv -> {csv_path}")


if __name__ == "__main__":
    raise SystemExit(main())
