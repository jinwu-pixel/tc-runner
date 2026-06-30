"""TDD for the pure parse/classify core of scripts/multitask_call_stress.py.

Fixtures are real logcat/dumpsys snippets captured from THOR2_J
(AT-M140, serial B2700125BW000083) during Phase 0 characterization of the
in-call multitask memory-stress scenario, so the parsers are pinned to
this device's actual output format.
"""
import importlib.util
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parents[1] / "scripts" / "multitask_call_stress.py"
_spec = importlib.util.spec_from_file_location("multitask_call_stress", _MOD_PATH)
mcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcs)


# --- parse_meminfo -------------------------------------------------------
def test_parse_meminfo_extracts_available_and_swap():
    text = ("MemTotal:        2882372 kB\n"
            "MemAvailable:    1397128 kB\n"
            "SwapFree:         842692 kB\n")
    m = mcs.parse_meminfo(text)
    assert m["MemAvailable"] == 1397128
    assert m["SwapFree"] == 842692
    assert m["MemTotal"] == 2882372


def test_parse_meminfo_missing_key_absent():
    m = mcs.parse_meminfo("MemFree:           42904 kB\n")
    assert m.get("MemAvailable") is None
    assert m["MemFree"] == 42904


# --- call_active (telephony.registry mCallState) -------------------------
def test_call_active_true_when_offhook():
    assert mcs.call_active("    mCallState=2") is True


def test_call_active_false_when_idle():
    assert mcs.call_active("    mCallState=0") is False


def test_call_active_true_if_any_subscription_offhook():
    assert mcs.call_active("mCallState=0\nmCallState=2") is True


# --- telecom_active (dumpsys telecom state=ACTIVE) -----------------------
def test_telecom_active_true_on_active_state():
    assert mcs.telecom_active("[Call id=TC@3, state=ACTIVE, tpac=...]") is True


def test_telecom_active_false_on_dialing():
    assert mcs.telecom_active("[Call id=TC@3, state=DIALING, tpac=...]") is False


# --- parse_top_activity (dumpsys activity activities) --------------------
def test_parse_top_activity_returns_pkg_slash_activity():
    text = ("topResumedActivity=ActivityRecord{3c49088 u0 "
            "com.google.android.youtube/.app.honeycomb.Shell$HomeActivity t39}")
    assert mcs.parse_top_activity(text) == (
        "com.google.android.youtube/.app.honeycomb.Shell$HomeActivity")


def test_parse_top_activity_none_when_absent():
    assert mcs.parse_top_activity("no resumed activity here") is None


# --- parse_am_events (logcat -b events) ----------------------------------
def test_parse_am_kill_event_fields():
    ev = mcs.parse_am_events("I/am_kill ( 1354): [0,24696,com.android.mms,945,empty #5]")
    assert len(ev) == 1
    assert ev[0]["type"] == "kill"
    assert ev[0]["pid"] == 24696
    assert ev[0]["pkg"] == "com.android.mms"
    assert ev[0]["adj"] == 945
    assert ev[0]["reason"] == "empty #5"


def test_parse_am_proc_died_event_fields():
    ev = mcs.parse_am_events("I/am_proc_died( 1354): [0,24696,com.android.mms,945,19]")
    assert ev[0]["type"] == "died"
    assert ev[0]["pid"] == 24696
    assert ev[0]["pkg"] == "com.android.mms"


def test_parse_am_proc_start_event_has_uid_offset():
    # am_proc_start inserts uid before the package: [user,pid,uid,pkg,reason,{cmp}]
    line = ("I/am_proc_start( 1354): [0,25936,10115,com.google.android.youtube,"
            "next-top-activity,{com.google.android.youtube/.app.honeycomb.Shell$HomeActivity}]")
    ev = mcs.parse_am_events(line)
    assert ev[0]["type"] == "start"
    assert ev[0]["pid"] == 25936
    assert ev[0]["pkg"] == "com.google.android.youtube"


def test_parse_am_events_multiline_skips_noise():
    text = ("I/am_kill ( 1354): [0,22962,com.android.vending,940,cached #5]\n"
            "I/am_proc_died( 1354): [0,22962,com.android.vending,940,16]\n"
            "I/SomethingElse( 1354): not an am event")
    ev = mcs.parse_am_events(text)
    assert len(ev) == 2


# --- summarize_evictions -------------------------------------------------
def test_summarize_evictions_counts_background_and_flags_launched():
    text = ("I/am_kill ( 1354): [0,22962,com.android.vending,940,cached #5]\n"
            "I/am_kill ( 1354): [0,25936,com.google.android.youtube,930,cached #5]\n"
            "I/am_proc_died( 1354): [0,25936,com.google.android.youtube,930,16]")
    ev = mcs.parse_am_events(text)
    s = mcs.summarize_evictions(ev, launched_pkgs=["com.google.android.youtube", "com.android.mms"])
    assert s["n_bg_evict"] == 2
    assert "com.google.android.youtube" in s["killed_launched_pkgs"]
    assert "com.android.vending" not in s["killed_launched_pkgs"]


# --- scan_signals --------------------------------------------------------
def test_scan_signals_jank_reports_max_frames():
    text = ("I/Choreographer(25936): Skipped 65 frames!  The application may be doing too much work\n"
            "I/Choreographer(25936): Skipped 99 frames!  The application may be doing too much work")
    s = mcs.scan_signals(text, test_pkgs=["com.google.android.youtube"])
    assert s["max_skipped_frames"] == 99
    assert s["n_crash"] == 0
    assert s["n_anr"] == 0


def test_scan_signals_fatal_crash_attributes_process():
    text = ("E/AndroidRuntime(12345): FATAL EXCEPTION: main\n"
            "E/AndroidRuntime(12345): Process: com.android.mms, PID: 12345\n"
            "E/AndroidRuntime(12345): java.lang.RuntimeException: boom")
    s = mcs.scan_signals(text, test_pkgs=["com.android.mms"])
    assert s["n_crash"] == 1
    assert "com.android.mms" in s["crash_pkgs"]
    assert "com.android.mms" in s["test_crash_pkgs"]


def test_scan_signals_system_crash_not_in_test_pkgs():
    text = ("E/AndroidRuntime( 642): FATAL EXCEPTION: Thread-2\n"
            "E/AndroidRuntime( 642): Process: com.google.android.gms, PID: 642\n")
    s = mcs.scan_signals(text, test_pkgs=["com.android.mms"])
    assert "com.google.android.gms" in s["crash_pkgs"]
    assert s["test_crash_pkgs"] == []


def test_scan_signals_ignores_zygote_process_exit():
    # real THOR2_J NOCALL line — a benign process exit, NOT a crash.
    # Must not populate crash_pkgs (was a false WARN-REVIEW source).
    text = "I/Zygote  (  753): Process 11886 exited due to signal 9 (Killed)"
    s = mcs.scan_signals(text, test_pkgs=["com.android.mms"])
    assert s["n_crash"] == 0
    assert s["crash_pkgs"] == []
    assert s["test_crash_pkgs"] == []


def test_scan_signals_process_line_without_crash_marker_ignored():
    # a bare "Process: <pkg>" with no FATAL/crash marker is not a crash
    text = "I/ActivityManager( 1354): Process: com.android.mms is now in foreground"
    s = mcs.scan_signals(text, test_pkgs=["com.android.mms"])
    assert s["crash_pkgs"] == []
    assert s["test_crash_pkgs"] == []


def test_scan_signals_anr_attributes_package():
    text = ("E/ActivityManager( 1354): ANR in com.android.mms (com.android.mms/.ui.ConversationList)\n"
            "E/ActivityManager( 1354): Reason: Input dispatching timed out")
    s = mcs.scan_signals(text, test_pkgs=["com.android.mms"])
    assert s["n_anr"] == 1
    assert "com.android.mms" in s["anr_pkgs"]
    assert "com.android.mms" in s["test_anr_pkgs"]


def test_scan_signals_counts_lmkd():
    text = "I/lmkd    (  800): Kill 'com.android.vending' (22962), uid 10140, oom_adj 940"
    s = mcs.scan_signals(text, test_pkgs=[])
    assert s["n_lmkd"] >= 1


# --- classify_cycle (closed-set, confound-first precedence) --------------
def test_classify_setup_failed_is_error_setup():
    assert mcs.classify_cycle({"setup_failed": True}) == "ERROR-SETUP"


def test_classify_reboot_takes_precedence_over_crash():
    assert mcs.classify_cycle(
        {"rebooted": True, "test_crash_pkgs": ["com.android.mms"]}) == "WARN-REBOOT"


def test_classify_calldrop_excluded_before_fail():
    assert mcs.classify_cycle(
        {"call_dropped": True, "test_anr_pkgs": ["com.android.mms"]}) == "WARN-CALLDROP"


def test_classify_test_app_crash_is_fail_crash():
    assert mcs.classify_cycle({"test_crash_pkgs": ["com.android.mms"]}) == "FAIL-CRASH"


def test_classify_test_app_anr_is_fail_anr():
    assert mcs.classify_cycle({"test_anr_pkgs": ["com.android.mms"]}) == "FAIL-ANR"


def test_classify_crash_beats_anr():
    assert mcs.classify_cycle(
        {"test_crash_pkgs": ["x"], "test_anr_pkgs": ["y"]}) == "FAIL-CRASH"


def test_classify_non_test_crash_is_warn_review():
    assert mcs.classify_cycle(
        {"crash_pkgs": ["com.google.android.gms"], "test_crash_pkgs": []}) == "WARN-REVIEW"


def test_classify_fg_restart_is_warn_fgrestart():
    assert mcs.classify_cycle({"fg_restart": True}) == "WARN-FGRESTART"


def test_classify_jank_over_threshold_is_warn_jank():
    assert mcs.classify_cycle({"max_skipped_frames": 80}, jank_threshold=60) == "WARN-JANK"


def test_classify_jank_under_threshold_is_pass():
    assert mcs.classify_cycle({"max_skipped_frames": 30}, jank_threshold=60) == "PASS"


def test_classify_clean_cycle_is_pass():
    assert mcs.classify_cycle({}) == "PASS"


# --- verdict accounting (numerator / denominator) ------------------------
def test_is_failure_only_true_for_crash_and_anr():
    assert mcs.is_failure("FAIL-CRASH") is True
    assert mcs.is_failure("FAIL-ANR") is True
    assert mcs.is_failure("WARN-FGRESTART") is False
    assert mcs.is_failure("PASS") is False


def test_is_excluded_true_for_confounds():
    for v in ("ERROR-SETUP", "WARN-REBOOT", "WARN-CALLDROP"):
        assert mcs.is_excluded(v) is True
    assert mcs.is_excluded("FAIL-CRASH") is False
    assert mcs.is_excluded("PASS") is False
