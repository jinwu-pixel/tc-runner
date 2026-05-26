"""
Per-app Phase 0 preset setup.

각 앱의 preset 명세는 본 파일 내부 dict 로 유지한다.
범용 framework 화 하지 말 것 — 새 앱이 생기면 dict 1개 추가하는 수준으로만 확장.

Phase 0 공통 책임:
  1. /sdcard 루트 잔존 XML 정리
  2. output/<app>_preset/ 에 최소 preset 파일 생성 (idempotent)
  3. device_map 의 각 /sdcard/<dir> 로 push
  4. MediaScanner broadcast
  5. 권한 + 파일 개수 스냅샷 출력

재실행 가능하고 멱등적.

사용:
  venv/Scripts/python.exe scripts/setup_preset.py --app minifile
"""

from __future__ import annotations

import argparse
import math
import os
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# File generators (preset 파일 실제 생성 로직)
# ============================================================

def make_wav(path: Path, duration_sec: float, freq_hz: int) -> None:
    """PCM 16-bit mono WAV. freq_hz=0 이면 무음."""
    sample_rate = 22050
    n_samples = int(sample_rate * duration_sec)
    amplitude = 16000 if freq_hz > 0 else 0
    buf = bytearray()
    for i in range(n_samples):
        v = int(amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate)) if freq_hz > 0 else 0
        buf.extend(struct.pack("<h", v))
    data = bytes(buf)
    header = (
        b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
        + b"fmt " + struct.pack("<I", 16)
        + struct.pack("<H", 1) + struct.pack("<H", 1)
        + struct.pack("<I", sample_rate) + struct.pack("<I", sample_rate * 2)
        + struct.pack("<H", 2) + struct.pack("<H", 16)
        + b"data" + struct.pack("<I", len(data))
    )
    path.write_bytes(header + data)


def make_pdf(path: Path) -> None:
    """한 페이지 짜리 최소 유효 PDF."""
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 52>>stream\n"
        b"BT /F1 24 Tf 72 720 Td (MiniFile Preset Sample PDF) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000109 00000 n \n"
        b"0000000205 00000 n \n"
        b"0000000306 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n378\n%%EOF\n"
    )
    path.write_bytes(body)


def make_txt(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def make_zip(path: Path, members: dict) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in members.items():
            zf.writestr(name, body)


# ============================================================
# 앱별 preset 명세
# ============================================================

MINIFILE = {
    "pkg": "com.example.mnnr_files",
    "preset_dirname": "minifile_preset",
    "device_map": {
        "audio":    ("/sdcard/Music",     ["minifile_silent.wav", "minifile_tone_440.wav"]),
        "docs":     ("/sdcard/Documents", ["minifile_sample.txt", "minifile_sample.pdf"]),
        "download": ("/sdcard/Download",  ["minifile_readme.txt", "minifile_sample.zip"]),
    },
    "root_xml_patterns": ["ui_*.xml", "dlg.xml", "trash_sel*.xml", "ui.xml"],
    "file_generators": {
        "minifile_silent.wav":    lambda p: make_wav(p, 2.0, 0),
        "minifile_tone_440.wav":  lambda p: make_wav(p, 1.5, 440),
        "minifile_sample.txt":    lambda p: make_txt(p, "MiniFile preset text document.\nDocuments 카테고리 검증용.\n"),
        "minifile_sample.pdf":    make_pdf,
        "minifile_readme.txt":    lambda p: make_txt(p, "MiniFile preset - Download folder sample.\n"),
        "minifile_sample.zip":    lambda p: make_zip(p, {"readme.txt": "MiniFile preset inside zip.\n"}),
    },
    "snapshot_extra_dirs": ["/sdcard/DCIM/MyGallery_TC", "/sdcard/Movies", "/sdcard/DCIM/Camera"],
    "snapshot_file_prefix": "minifile_",
}

APPS = {
    "minifile": MINIFILE,
}


# ============================================================
# 실행 로직 (app dict 파라미터화)
# ============================================================

def adb(app: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["adb", "-s", app["device_serial"], *args]
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def ensure_device(app: dict) -> None:
    r = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    if app["device_serial"] not in r.stdout:
        sys.exit(f"ERROR: device {app['device_serial']} not attached\n{r.stdout}")


def clean_root_xml(app: dict) -> int:
    removed = 0
    for pat in app["root_xml_patterns"]:
        r = adb(app, "shell", f"ls /sdcard/{pat} 2>/dev/null", check=False)
        files = [l.strip() for l in r.stdout.splitlines() if l.strip() and "No such" not in l]
        for f in files:
            adb(app, "shell", f"rm -f '{f}'", check=False)
            removed += 1
    return removed


def preset_dir(app: dict) -> Path:
    return PROJECT_ROOT / "output" / app["preset_dirname"]


def generate_preset(app: dict) -> None:
    pdir = preset_dir(app)
    pdir.mkdir(parents=True, exist_ok=True)
    for name, gen in app["file_generators"].items():
        p = pdir / name
        if not p.exists():
            gen(p)


def push_preset(app: dict) -> dict:
    pdir = preset_dir(app)
    counts = {}
    for bucket, (dest_dir, names) in app["device_map"].items():
        adb(app, "shell", f"mkdir -p {dest_dir}")
        for n in names:
            src = pdir / n
            adb(app, "push", str(src), f"{dest_dir}/{n}")
            adb(
                app, "shell", "am", "broadcast",
                "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d", f"file://{dest_dir}/{n}",
                check=False,
            )
        counts[bucket] = len(names)
    return counts


def snapshot(app: dict) -> None:
    pkg = app["pkg"]

    print("\n=== Runtime perms ===")
    r = adb(app, "shell", f"dumpsys package {pkg} | grep -A12 'runtime permissions'", check=False)
    print(r.stdout.rstrip())

    print("\n=== Appops (MANAGE_EXTERNAL_STORAGE / PACKAGE_USAGE_STATS) ===")
    r = adb(app, "shell", f"dumpsys package {pkg} | grep -E 'MANAGE_EXTERNAL_STORAGE|PACKAGE_USAGE_STATS'", check=False)
    print(r.stdout.rstrip())

    print("\n=== File count snapshot ===")
    prefix = app["snapshot_file_prefix"]
    for _, (dest_dir, _) in app["device_map"].items():
        r = adb(app, "shell", f"ls {dest_dir}/ 2>/dev/null | grep '^{prefix}' | wc -l | tr -d ' '", check=False)
        print(f"  {dest_dir} {prefix}*: {r.stdout.strip() or '0'}")
    for d in app["snapshot_extra_dirs"]:
        r = adb(app, "shell", f"ls {d}/ 2>/dev/null | wc -l | tr -d ' '", check=False)
        print(f"  {d}: {r.stdout.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-app Phase 0 preset setup.")
    parser.add_argument("--app", required=True, choices=sorted(APPS.keys()),
                        help="대상 앱 키 (내부 dict 에 등록된 값)")
    parser.add_argument("--serial", default=None,
                        help="adb device serial (또는 ANDROID_SERIAL env)")
    args = parser.parse_args()

    serial = args.serial or os.environ.get("ANDROID_SERIAL")
    if not serial:
        parser.error("--serial argument or ANDROID_SERIAL env variable required")

    app = dict(APPS[args.app])
    app["device_serial"] = serial
    pdir = preset_dir(app)

    ensure_device(app)
    print(f"[app={args.app}  pkg={app['pkg']}  serial={app['device_serial']}]")

    print("[1/4] Cleaning /sdcard root XML ...")
    n = clean_root_xml(app)
    print(f"      removed: {n}")

    print(f"[2/4] Generating preset in {pdir} ...")
    generate_preset(app)
    for p in sorted(pdir.iterdir()):
        print(f"      {p.name}  ({p.stat().st_size} B)")

    print(f"[3/4] Pushing to {app['device_serial']} ...")
    counts = push_preset(app)
    for k, v in counts.items():
        print(f"      {k}: {v} files")

    print("[4/4] Snapshot")
    snapshot(app)

    print(f"\nDONE. Launch {app['pkg']} to verify preset visibility.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
