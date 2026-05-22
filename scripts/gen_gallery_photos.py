"""
Gallery TC preset: generate 25 JPEGs with deterministic content and EXIF.

Layout:
  - Dates:  idx 0-9   -> t-2   (10 photos)
            idx 10-19 -> t-1   (10 photos)
            idx 20-24 -> t0    (5  photos)
  - Size:   idx 0-14  -> 4K  (3840x2160)
            idx 15-24 -> HD  (1280x720)
  - GPS:    idx {0, 5, 11, 18, 22}  (5 photos with GPS EXIF)

Output: output/gallery_photos/IMG_{YYYYMMDD}_{seq:03d}.jpg
"""

from __future__ import annotations

import os
import sys
import shutil
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import piexif

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "output" / "gallery_photos"

TODAY = date(2026, 4, 21)
DATE_T_MINUS_2 = TODAY - timedelta(days=2)  # 2026-04-19
DATE_T_MINUS_1 = TODAY - timedelta(days=1)  # 2026-04-20
DATE_T_0 = TODAY                             # 2026-04-21

SIZE_4K = (3840, 2160)
SIZE_HD = (1280, 720)

GPS_INDICES = {0, 5, 11, 18, 22}
GPS_SITES = {
    0:  ("Seoul",    37.5665, 126.9780),
    5:  ("Busan",    35.1796, 129.0756),
    11: ("Daegu",    35.8714, 128.6014),
    18: ("Incheon",  37.4563, 126.7052),
    22: ("Gwangju",  35.1595, 126.8526),
}

MAKE = "ALTech"
MODEL = "AT-M150"


def photo_date(idx: int) -> date:
    if idx < 10:
        return DATE_T_MINUS_2
    if idx < 20:
        return DATE_T_MINUS_1
    return DATE_T_0


def photo_size(idx: int) -> tuple[int, int]:
    return SIZE_4K if idx < 15 else SIZE_HD


def hue_color(idx: int) -> tuple[int, int, int]:
    # Spread hues evenly so each photo is visually distinct
    h = (idx * 360 // 25) % 360
    # Simple HSV -> RGB (S=0.55, V=0.85)
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h / 360.0, 0.55, 0.85)
    return int(r * 255), int(g * 255), int(b * 255)


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("malgun.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_photo(idx: int) -> Image.Image:
    w, h = photo_size(idx)
    bg = hue_color(idx)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # Vertical gradient overlay for visual interest
    for y in range(h):
        alpha = int(40 * (y / h))
        draw.line([(0, y), (w, y)], fill=(bg[0] - alpha if bg[0] > alpha else 0,
                                           bg[1] - alpha if bg[1] > alpha else 0,
                                           bg[2] - alpha if bg[2] > alpha else 0))

    big = _find_font(size=max(72, h // 6))
    small = _find_font(size=max(28, h // 28))

    label = f"IMG {idx:02d}"
    tw = draw.textlength(label, font=big)
    draw.text(((w - tw) / 2, h * 0.30), label, fill=(255, 255, 255), font=big)

    d = photo_date(idx)
    sub = f"{d.isoformat()}   {w}x{h}"
    sw = draw.textlength(sub, font=small)
    draw.text(((w - sw) / 2, h * 0.55), sub, fill=(255, 255, 255), font=small)

    if idx in GPS_INDICES:
        site, lat, lon = GPS_SITES[idx]
        tag = f"GPS: {site} ({lat:.4f}, {lon:.4f})"
        gw = draw.textlength(tag, font=small)
        draw.text(((w - gw) / 2, h * 0.68), tag, fill=(255, 240, 100), font=small)

    return img


def _to_deg_min_sec(val: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    val = abs(val)
    deg = int(val)
    rem = (val - deg) * 60
    minute = int(rem)
    sec = (rem - minute) * 60
    return ((deg, 1), (minute, 1), (int(sec * 10000), 10000))


def build_exif(idx: int) -> bytes:
    d = photo_date(idx)
    # distribute capture minutes so ordering within a date is stable (00,03,06,...)
    minute = (idx % 10) * 3
    dt_str = f"{d.year:04d}:{d.month:02d}:{d.day:02d} 12:{minute:02d}:00"

    w, h = photo_size(idx)

    zeroth_ifd = {
        piexif.ImageIFD.Make: MAKE.encode("ascii"),
        piexif.ImageIFD.Model: MODEL.encode("ascii"),
        piexif.ImageIFD.DateTime: dt_str.encode("ascii"),
        piexif.ImageIFD.Software: b"mygalleryapp-tc-preset",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: dt_str.encode("ascii"),
        piexif.ExifIFD.DateTimeDigitized: dt_str.encode("ascii"),
        piexif.ExifIFD.PixelXDimension: w,
        piexif.ExifIFD.PixelYDimension: h,
    }
    gps_ifd: dict = {}
    if idx in GPS_INDICES:
        _, lat, lon = GPS_SITES[idx]
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: _to_deg_min_sec(lat),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: _to_deg_min_sec(lon),
        }

    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None}
    return piexif.dump(exif_dict)


def filename(idx: int) -> str:
    d = photo_date(idx)
    return f"IMG_{d.year:04d}{d.month:02d}{d.day:02d}_{idx:03d}.jpg"


def set_mtime(path: Path, idx: int) -> None:
    # set file mtime to match capture datetime (some apps use fs time as fallback)
    import time
    d = photo_date(idx)
    minute = (idx % 10) * 3
    t = time.mktime((d.year, d.month, d.day, 12, minute, 0, 0, 0, -1))
    os.utime(path, (t, t))


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for idx in range(25):
        img = draw_photo(idx)
        exif_bytes = build_exif(idx)
        out = OUT_DIR / filename(idx)
        img.save(out, format="JPEG", quality=85, exif=exif_bytes)
        set_mtime(out, idx)
        tag = " [GPS]" if idx in GPS_INDICES else ""
        print(f"  {out.name}  {photo_size(idx)[0]}x{photo_size(idx)[1]}  {photo_date(idx)}{tag}")

    print(f"\nGenerated 25 photos -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
