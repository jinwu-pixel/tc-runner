"""
Remove PFW seed photos from F0 (AT-M140) and refresh media scan, with
residual-zero verification built in.

Target on device: /sdcard/DCIM/PFWSEED_C11/

Reused pattern: scripts/reset_gallery_media.py (adb helper, ensure_device,
collect-then-delete-then-scan). Not modified — this variant pins -s SERIAL
and adds a MediaStore residual-count verification gate per
MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md section 3/S3-2 — passing this
verification is the script's success condition, not merely running rm -rf.
"""

from __future__ import annotations

import subprocess
import sys
import time

SERIAL = "B06201249E0002F0"
DEVICE_DIR = "/sdcard/DCIM/PFWSEED_C11"

VERIFY_RETRY_DELAY_S = 2


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["adb", "-s", SERIAL, *args]
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def ensure_device() -> None:
    r = subprocess.run(["adb", "devices"], check=True, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip() and "device" in l and "List of" not in l]
    if not lines:
        sys.exit("ERROR: no adb device attached")
    if len(lines) > 1:
        sys.exit(f"ERROR: multiple devices attached (expected sole {SERIAL}):\n{r.stdout}")
    serials = [l.split()[0] for l in lines]
    if SERIAL not in serials:
        sys.exit(f"ERROR: expected device {SERIAL} not found. Attached: {serials}")


def query_residual_names() -> list[str]:
    r = adb(
        "shell",
        "content", "query",
        "--uri", "content://media/external/images/media",
        "--projection", "_display_name",
        check=False,
    )
    return [l for l in r.stdout.splitlines() if "PFWSEED" in l]


def verify_removed() -> list[str]:
    """Query MediaStore for residual PFWSEED rows; retry once after a short delay."""
    residual = query_residual_names()
    if not residual:
        return residual
    time.sleep(VERIFY_RETRY_DELAY_S)
    return query_residual_names()


def main() -> int:
    ensure_device()

    # Collect filenames before deletion so we can scan-remove them from MediaStore
    r = adb("shell", f"ls {DEVICE_DIR}", check=False)
    names = [n for n in r.stdout.splitlines() if n.strip()] if r.returncode == 0 else []

    # Hardcoded DEVICE_DIR only — no caller-supplied path accepted (safety per design).
    adb("shell", f"rm -rf {DEVICE_DIR}", check=False)

    # Broadcast scan on the (now missing) files so MediaStore removes them.
    for n in names:
        adb(
            "shell",
            "am", "broadcast",
            "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d", f"file://{DEVICE_DIR}/{n}",
            check=False,
        )

    residual = verify_removed()
    if residual:
        print(f"ERROR: residual PFWSEED entries remain in MediaStore ({len(residual)}):")
        for line in residual:
            print(f"  {line}")
        return 1

    print(f"Removed {DEVICE_DIR} ({len(names)} files). MediaStore residual check: 0 PFWSEED entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
