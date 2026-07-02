"""
PFW seed photo preset: generate 5 JPEGs with deterministic content, no EXIF.

Layout:
  - Count:  5 photos
  - Size:   1280x720 (HD) for all
  - Colors: 5 distinct solid backgrounds (no gradient/GPS — kept minimal for
            a single-purpose gate-clear seed, unlike gen_gallery_photos.py's
            25-photo date/size/GPS matrix)
  - Label:  large centered text "PFWSEED P1".."PFWSEED P5"
  - EXIF:   none (no piexif import/use — no GPS, no date, no device meta)

Output: output/pfwseed_photos/PFWSEED_{01..05}.jpg

Reused pattern: scripts/gen_gallery_photos.py (font lookup + draw_photo
layout). Not modified — this is a reduced, deterministic variant per
MEDIA_SEED_DESIGN_C11_GAP8_2026-07-02.md section 3.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "output" / "pfwseed_photos"

SIZE_HD = (1280, 720)

COLORS = {
    1: (200, 60, 60),    # red
    2: (60, 140, 200),   # blue
    3: (70, 170, 90),    # green
    4: (210, 170, 40),   # amber
    5: (140, 80, 190),   # purple
}


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("malgun.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_photo(seq: int) -> Image.Image:
    w, h = SIZE_HD
    bg = COLORS[seq]
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    big = _find_font(size=max(72, h // 6))

    label = f"PFWSEED P{seq}"
    tw = draw.textlength(label, font=big)
    draw.text(((w - tw) / 2, (h - big.size) / 2), label, fill=(255, 255, 255), font=big)

    return img


def filename(seq: int) -> str:
    return f"PFWSEED_{seq:02d}.jpg"


def main() -> int:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for seq in range(1, 6):
        img = draw_photo(seq)
        out = OUT_DIR / filename(seq)
        # No exif= kwarg -> no EXIF block written (PII 0 per design section 2-3)
        img.save(out, format="JPEG", quality=85)
        print(f"  {out.name}  {SIZE_HD[0]}x{SIZE_HD[1]}  color={COLORS[seq]}")

    print(f"\nGenerated 5 photos -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
