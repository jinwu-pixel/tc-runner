"""
Remove gallery TC preset media from ODIN2 and refresh media scan.

Target on device: /sdcard/DCIM/MyGallery_TC/
"""

from __future__ import annotations

import subprocess
import sys

DEVICE_DIR = "/sdcard/DCIM/MyGallery_TC"


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *args], check=check, capture_output=True, text=True)


def ensure_device() -> None:
    r = adb("devices")
    lines = [l for l in r.stdout.splitlines() if l.strip() and "device" in l and "List of" not in l]
    if not lines:
        sys.exit("ERROR: no adb device attached")
    if len(lines) > 1:
        sys.exit(f"ERROR: multiple devices attached:\n{r.stdout}")


def main() -> int:
    ensure_device()

    # Collect filenames before deletion so we can scan-remove them from MediaStore
    r = adb("shell", f"ls {DEVICE_DIR}", check=False)
    names = [n for n in r.stdout.splitlines() if n.strip()] if r.returncode == 0 else []

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

    print(f"Removed {DEVICE_DIR} ({len(names)} files). MediaStore scan triggered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
