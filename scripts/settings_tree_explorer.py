"""Device Settings menu-tree baseline explorer (v1, read-only deep-link enum).

Driver/orchestration only. Imports src.menu_tree (pure schema) and
scripts.menu_mapper (parsers). All ADB access routes through GuardedADB,
which enforces a read-only / navigation-safe command allowlist:
  - launch (am start -a/-n), scroll (input swipe), read-only dump/focus/getprop
  - ONLY HOME/BACK navigation keys — no semantic tap, no POWER/ENTER/DPAD_CENTER,
    no text input, no settings put / pm / am force-stop / install / rm·mv·cp,
    no arbitrary shell passthrough.

Task 6 scope = GuardedADB + allowlist. Reach/explore/scroll/emit/CLI land in
later tasks. The real `adb` is injected (src.adb.ADB) so tests use a stub.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, ".."))   # repo root -> enables `from src...`
sys.path.append(_HERE)                        # scripts/ -> enables `import menu_mapper`
from src import menu_tree as mt          # noqa: E402,F401  (used by later tasks)
import menu_mapper as mm                 # noqa: E402,F401  (used by later tasks)
from src.adb import ADB                  # noqa: E402,F401  (instantiated in CLI, later task)

# --- read-only / navigation-safe command allowlist ------------------------
# Token-anchored (^...$) so a substring can't slip a mutation through. Only
# HOME/BACK keyevents are allowed; every other keyevent — numeric ENTER (66),
# DPAD_CENTER (23), POWER (26), or any KEYCODE_* — is denied by construction.
_ALLOWED_PATTERNS = [
    # Component is single-quoted so the device shell treats a `$Xxx` activity-alias
    # literally (unquoted, the device sh expands `$Xxx` to empty -> launch collapses
    # to base `.../Settings`). The `$`-anchored quote pair blocks injection.
    re.compile(r"^am start (-a [\w.]+|-n '[\w./$]+')$"),
    re.compile(r"^input swipe \d+ \d+ \d+ \d+( \d+)?$"),
    re.compile(r"^input keyevent (KEYCODE_HOME|KEYCODE_BACK)$"),
    re.compile(r"^uiautomator dump /sdcard/[\w.]+$"),
    re.compile(r"^cat /sdcard/[\w.]+$"),
    re.compile(r"^dumpsys window$"),
    re.compile(r"^getprop [\w.]+$"),
    re.compile(r"^wm (size|density)$"),   # read-only viewport/dpi query (device baseline)
]
# NOTE: `am force-stop` is intentionally NOT in the allowlist — it is an opt-in
# stuck-recovery op gated solely inside force_stop_settings() (future
# --force-stop-on-stuck) and is never reachable via raw_shell. `rm`/`mv`/`cp`
# and other device mutations are never allowed; the temp uiautomator dump path
# is overwritten in place on each dump rather than removed.


# Component validated BEFORE single-quoting so the quoting can't be broken out of:
# no quote / `;` / whitespace / `$()` / backtick reaches the device shell. Only
# pkg/activity chars (incl. `$` for the activity-alias and `.` for relative names).
_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+$")


def is_allowed_command(command: str) -> bool:
    return any(p.match(command.strip()) for p in _ALLOWED_PATTERNS)


class CommandNotAllowed(RuntimeError):
    pass


def build_component_command(comp: str) -> str:
    """Build `am start -n '<component>'` with the component single-quoted.

    Validates the component against `_COMPONENT_RE` first, then single-quotes it so
    the device shell receives a `$Xxx` activity-alias literally (instead of expanding
    it to empty and collapsing the launch to base `.../Settings`). Raises
    CommandNotAllowed on a component that fails the safe pattern (quote/`;`/space/
    substitution injection).
    """
    if not _COMPONENT_RE.match(comp):
        raise CommandNotAllowed(
            f"blocked: component {comp!r} "
            f"(reason: fails safe component pattern {_COMPONENT_RE.pattern})")
    return f"am start -n '{comp}'"


class GuardedADB:
    """Narrow read-only facade over src.adb.ADB. Logs + validates every op."""

    def __init__(self, adb, allow_force_stop: bool = False):
        self._adb = adb
        self._allow_force_stop = allow_force_stop
        self.command_log: list[str] = []
        self.violations = 0

    def _guard(self, command: str) -> None:
        self.command_log.append(command)
        if not is_allowed_command(command):
            self.violations += 1
            raise CommandNotAllowed(
                f"blocked: {command!r} (reason: not in read-only/navigation-safe allowlist)")

    def raw_shell(self, command: str) -> str:
        self._guard(command)
        return self._adb.shell(command)

    def launch_action(self, action: str) -> str:
        return self.raw_shell(f"am start -a {action}")

    def launch_component(self, comp: str) -> str:
        return self.raw_shell(build_component_command(comp))

    def scroll_up(self, x1, y1, x2, y2, duration=300):
        self._guard(f"input swipe {x1} {y1} {x2} {y2} {duration}")
        self._adb.swipe(x1, y1, x2, y2, duration)

    def home(self):
        self.key("KEYCODE_HOME")

    def back(self):
        self.key("KEYCODE_BACK")

    def key(self, keycode: str):
        # _guard rejects anything but HOME/BACK (single source of truth = allowlist).
        self._guard(f"input keyevent {keycode}")
        self._adb.key(keycode)

    def force_stop_settings(self):
        # Opt-in only (future --force-stop-on-stuck); bypasses the generic allowlist
        # by design (flag-gated + logged). Never reachable via raw_shell.
        if not self._allow_force_stop:
            raise CommandNotAllowed(
                "blocked: 'am force-stop com.android.settings' "
                "(reason: disabled; requires --force-stop-on-stuck opt-in)")
        cmd = "am force-stop com.android.settings"
        self.command_log.append(cmd)
        self._adb.shell(cmd)

    def dump(self) -> str:
        # Guarded read flow: write temp dump, read it. No `rm` (device mutation);
        # the temp path is overwritten in place on the next dump.
        remote = "/sdcard/ui_dump.xml"
        self.raw_shell(f"uiautomator dump {remote}")
        return self.raw_shell(f"cat {remote}")

    def getprop(self, name: str) -> str:
        return self.raw_shell(f"getprop {name}").strip()

    def current_focus(self) -> str:
        out = self.raw_shell("dumpsys window")
        m = re.search(r"mCurrentFocus=\S+ u0 ([\w.]+)/([\w.$]+)", out)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
        m = re.search(r" ([\w.]+)/([\w.$]+)\}", out)
        return f"{m.group(1)}/{m.group(2)}" if m else "unknown/unknown"


# --- Task 7: per-screen reach classification + dump/parse -----------------
_SETTINGS_PKG = "com.android.settings"
_VIEWPORT = (480, 800)  # THOR2_K; swipe geometry source (used in Task 8)


def _launch(g: GuardedADB, entry: dict) -> tuple[str | None, str | None]:
    """Returns (launched_cmd, None) or (None, 'NO_ACTION')."""
    if entry.get("action"):
        cmd = f"am start -a {entry['action']}"
        g.launch_action(entry["action"])
        return cmd, None
    if entry.get("component"):
        cmd = build_component_command(entry["component"])  # quoted form actually sent
        g.launch_component(entry["component"])
        return cmd, None
    return None, "NO_ACTION"


def _classify_reach(focus: str, expect_regex: str) -> tuple[str, str | None, bool]:
    """Returns (reach_status, reach_kind, activity_match).

    Boundary (reach ladder, kept deliberately separate):
      settings pkg + activity_match                  -> REACHED (internal)
      settings pkg + no activity_match               -> FOCUS_MISMATCH
      external pkg + activity_match + allowlist pkg   -> REACHED_EXTERNAL_PACKAGE
      external pkg otherwise                         -> FOCUS_MISMATCH

    activity_match (expect_activity_regex vs observed focus) is the external
    discriminator: an allowlisted pkg reached UNEXPECTEDLY (e.g. the home
    launcher) is FOCUS_MISMATCH, never a successful external routing.
    """
    pkg = focus.split("/")[0] if "/" in focus else focus
    activity_match = bool(re.search(expect_regex, focus)) if expect_regex else False
    if pkg == _SETTINGS_PKG:
        if activity_match:
            return "REACHED", "internal", True
        return "FOCUS_MISMATCH", None, False
    if activity_match and pkg in mm.ALLOWLIST_PACKAGES:
        return "REACHED_EXTERNAL_PACKAGE", "external", True
    return "FOCUS_MISMATCH", None, activity_match


def is_denylisted(node: dict) -> bool:
    label = (node.get("text") or node.get("content-desc") or "").lower()
    return any(d.lower() in label for d in mm.DENYLIST)


def _elements_from_xml(xml: str) -> list:
    els = []
    for n in mm.extract_nodes(xml):
        if not (n.get("text") or n.get("content-desc")):
            continue
        els.append(mt.build_element(n, is_denylisted(n)))
    return els


def _scroll_sweep(g: GuardedADB, els: list, max_passes: int):
    """Read-only scroll sweep. 1 pass = single swipe-up + 1 dump.

    Merges newly revealed *elements* (full MenuElement — kind/risk/source_class
    preserved, de-duped by label) into the running list. Terminates on the first
    pass that reveals no new label (`no_new`) or after `max_passes` (`max_passes`).
    Empty/failed dump stops safely as `no_new`. Only swipe + dump are issued — no
    tap / key / mutation (all via GuardedADB).
    """
    w, h = _VIEWPORT
    x = w // 2
    y1, y2 = int(h * 0.75), int(h * 0.25)   # swipe up within the list area
    seen = {e.label for e in els if e.label}
    merged = list(els)
    swipes: list[dict] = []
    new_per_pass: list[int] = []
    terminated = "no_new"
    passes = 0
    for _ in range(max_passes):
        g.scroll_up(x, y1, x, y2)
        swipes.append({"dir": "up", "x1": x, "y1": y1, "x2": x, "y2": y2})
        passes += 1
        xml = g.dump()
        if not xml or "<node" not in xml:        # failed/empty dump -> safe stop
            new_per_pass.append(0)
            terminated = "no_new"
            break
        added = 0
        for e in _elements_from_xml(xml):
            if e.label and e.label not in seen:
                seen.add(e.label)
                merged.append(e)                  # keep full element, not just text
                added += 1
        new_per_pass.append(added)
        if added == 0:
            terminated = "no_new"
            break
    else:
        terminated = "max_passes"
    return mt.ScrollInfo(passes=passes, swipes=swipes,
                         new_texts_per_pass=new_per_pass, terminated=terminated), merged


def explore_screen(g: GuardedADB, seed: dict, run_id: str,
                   max_passes: int = 8, settle: float = 1.2, raw_writer=None):
    entry = dict(seed.get("entry") or {})
    nav_path = seed.get("nav_path", [])
    label_ko = seed.get("label_ko", "")
    screen_id = seed["id"]
    expect_regex = seed.get("expect_activity_regex", "")

    launched_cmd, no_action = _launch(g, entry)
    entry_rec = {"method": "deeplink", "action": entry.get("action"),
                 "component": entry.get("component"), "launched_cmd": launched_cmd}
    empty_scroll = mt.ScrollInfo()

    # (1) no action/component -> UNREACHABLE_NO_ACTION
    if no_action == "NO_ACTION":
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "UNREACHABLE_NO_ACTION", None, "unknown/unknown", expect_regex, False,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="no_launch", dump_size=0, raw_present=False), [], None)

    if settle:
        time.sleep(settle)
    focus = g.current_focus()

    # (2) launched but no focus -> LAUNCH_FAILED (kept distinct from FOCUS_MISMATCH)
    if focus in ("unknown/unknown", ""):
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "LAUNCH_FAILED", None, focus or "unknown/unknown", expect_regex, False,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="no_focus", dump_size=0, raw_present=False), [], None)

    # (3/4/5) reach classification by pkg + activity_match
    reach_status, reach_kind, activity_match = _classify_reach(focus, expect_regex)
    if reach_status == "FOCUS_MISMATCH":
        g.home()  # HOME-only recovery
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            reach_status, reach_kind, focus, expect_regex, activity_match,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error=None, dump_size=0, raw_present=False), [], None)

    # (6) reached but dump empty/no nodes -> DUMP_REJECTED (only after reach OK)
    xml = g.dump()
    dump_size = len(xml)
    if not xml or "<node" not in xml:
        return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
            "DUMP_REJECTED", reach_kind, focus, expect_regex, activity_match,
            None, mt.bucket_texts([]), [], empty_scroll,
            mt.DumpInfo(dump_error="empty_or_no_nodes", dump_size=dump_size, raw_present=False),
            [], None)

    # (7) reached + dump/parse success -> REACHED(/EXTERNAL)
    els = _elements_from_xml(xml)
    scroll, els = _scroll_sweep(g, els, max_passes)
    fingerprint = mm.generate_fingerprint(focus, mm.extract_nodes(xml))
    risk_flags = sorted({e.label for e in els if e.risk == "denylist"})  # record-only
    raw_ref = None
    if raw_writer:                       # raw persistence is orchestration-owned (Task 9)
        raw_writer(screen_id, xml)
        raw_ref = f"catalog/raw/{run_id}/{screen_id}.xml"
    g.home()  # HOME-only recovery before next screen
    return mt.MenuScreen(screen_id, label_ko, nav_path, entry_rec,
        reach_status, reach_kind, focus, expect_regex, activity_match,
        fingerprint, mt.bucket_texts(els), els, scroll,
        mt.DumpInfo(dump_error=None, dump_size=dump_size, raw_present=True),
        risk_flags, raw_ref)


# --- Task 9: orchestration + device baseline + emit + CLI -----------------
class TargetMismatch(RuntimeError):
    pass


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def preflight_serial(adb, target: str, allow_mismatch: bool) -> bool:
    """Returns target_mismatch_ack. Raises TargetMismatch on mismatch unless allowed."""
    actual = adb.device_serial()
    if actual and target and actual != target:
        if not allow_mismatch:
            raise TargetMismatch(f"connected {actual} != seed target {target} "
                                 f"(use --allow-target-mismatch to proceed)")
        return True
    return False


def capture_device_baseline(g: GuardedADB, serial: str) -> mt.DeviceBaseline:
    gp = g.getprop
    try:
        viewport = g.raw_shell("wm size").split(":")[-1].strip() or "480x800"
    except Exception:
        viewport = "480x800"
    try:
        dpi = g.raw_shell("wm density").split(":")[-1].strip() or "220"
    except Exception:
        dpi = "220"
    return mt.DeviceBaseline(
        serial=serial or (g._adb.device_serial() or "unknown"),
        model=gp("ro.product.model"), product=gp("ro.product.name"),
        device=gp("ro.product.device"), build_fingerprint=gp("ro.build.fingerprint"),
        build_id=gp("ro.build.id"), android=gp("ro.build.version.release"),
        locale_persist=gp("persist.sys.locale"), locale_product=gp("ro.product.locale"),
        viewport=viewport, dpi=dpi, sim=gp("gsm.sim.operator.alpha") or "unknown")


def dry_run_plan(seed: dict) -> str:
    """Pure: renders the launch plan with NO device/ADB interaction."""
    lines = [f"target_serial: {seed.get('target_serial')}",
             f"screens: {len(seed.get('screens', []))}"]
    for s in seed.get("screens", []):
        e = s.get("entry") or {}
        cmd = (f"am start -a {e['action']}" if e.get("action")
               else build_component_command(e['component']) if e.get("component")
               else "(no action)")
        lines.append(f"  - {s['id']}: {cmd}")
    return "\n".join(lines)


def run_explore(g: GuardedADB, seed: dict, run_id: str, out_dir: str,
                settle: float = 1.2, max_passes: int = 8,
                target_mismatch_ack: bool = False) -> mt.MenuTreeBaseline:
    base = os.path.join(out_dir, f"menu_tree_baseline_{run_id}")
    # append-only: refuse to overwrite an existing baseline (fail-fast, pre-device).
    for ext in (".json", ".md"):
        if os.path.exists(base + ext):
            raise FileExistsError(f"refusing to overwrite existing baseline: {base + ext}")

    serial = seed.get("target_serial", "")
    device = capture_device_baseline(g, serial)
    raw_root = os.path.join(out_dir, "raw", run_id)

    def raw_writer(screen_id: str, xml: str):
        os.makedirs(raw_root, exist_ok=True)
        with open(os.path.join(raw_root, f"{screen_id}.xml"), "w", encoding="utf-8") as fh:
            fh.write(xml)

    # one failed screen never aborts the run — explore_screen returns a status row.
    screens = [explore_screen(g, s, run_id=run_id, max_passes=max_passes,
                              settle=settle, raw_writer=raw_writer)
               for s in seed.get("screens", [])]
    baseline = mt.MenuTreeBaseline(
        schema_version=mt.SCHEMA_VERSION, tool_version=mt.TOOL_VERSION,
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        run_id=run_id, device=device, package=seed.get("package", "com.android.settings"),
        seed_ref={"source_menu_tree": seed.get("source_menu_tree"),
                  "seed_version": seed.get("seed_version"),
                  "seed_path": seed.get("__seed_path__", "")},
        target_mismatch_ack=target_mismatch_ack,
        summary=mt.compute_summary(screens), screens=screens)

    os.makedirs(out_dir, exist_ok=True)
    with open(base + ".json", "w", encoding="utf-8") as fh:
        fh.write(baseline.to_json())
    with open(base + ".md", "w", encoding="utf-8") as fh:
        fh.write(baseline.to_md())
    return baseline


def main():
    import yaml
    p = argparse.ArgumentParser(
        description="Device Settings menu-tree baseline explorer (read-only, append-only).")
    p.add_argument("--seed", required=True, help="seed YAML path")
    p.add_argument("--out-dir", required=True, help="output dir (e.g. 'THOR2_K - Settings/catalog')")
    p.add_argument("--serial", help="ADB target serial")
    p.add_argument("--allow-target-mismatch", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="render launch plan; no device calls")
    args = p.parse_args()

    with open(args.seed, encoding="utf-8") as fh:
        seed = yaml.safe_load(fh)
    seed["__seed_path__"] = args.seed
    if args.dry_run:
        print(dry_run_plan(seed))
        return

    adb = ADB(device_serial=args.serial)
    ack = preflight_serial(adb, target=seed.get("target_serial", ""),
                           allow_mismatch=args.allow_target_mismatch)
    g = GuardedADB(adb)
    run_id = _now_run_id()
    baseline = run_explore(g, seed, run_id=run_id, out_dir=args.out_dir,
                           target_mismatch_ack=ack)
    s = baseline.summary
    print(f"device smoke: baseline bundle 생성 run_id={run_id}, "
          f"{s['reached'] + s['reached_external']}/{s['screen_count']} REACHED, "
          f"allowlist violations={g.violations}")


if __name__ == "__main__":
    main()
