#!/usr/bin/env python3
"""Deterministic PIL generator for the 20-image precheck smoke fixture (D2 Gate 2).

Produces the 20 binary fixtures under ``fixtures/`` plus ``fixtures.json``
so the repo stays fully reproducible without committing camera photos. Every
image is a synthetic solid-colour / gradient render — tiny when compressed.

The fixture composition mirrors ``FEATURE_PLAN.md`` §978-990:

  KNOWN-BAD (10 → must resolve to ``failed_precheck``)
    1.  PNG (not JPEG)                              -> jpeg fail
    2.  CMYK JPEG, 1500x1500, white-ish             -> colorspace fail
    3.  1000x1000 RGB JPEG, white BG                -> resolution fail
    4.  dark-gray-BG RGB JPEG, 1500x1500            -> white_bg fail
    5.  800x800 PNG                                 -> jpeg + resolution fail
    6.  CMYK 1200x1200 JPEG                          -> colorspace + resolution fail
    7.  colourful textured BG RGB JPEG, 1500x1500   -> white_bg fail
    8.  hue-tinted (non-pure-white) RGB JPEG        -> white_bg fail
    9.  black-BG RGB JPEG, 1500x1500                -> white_bg fail
    10. grass/lifestyle BG RGB JPEG, 1500x1500      -> white_bg fail

  KNOWN-GOOD (10 → must resolve to ``ready``)
    1500x1500 (or larger) RGB JPEG with a PURE-WHITE background. The 4 corner
    5x5 patches are forced to brightness >= 240 so they clear the AS-BUILT
    white-BG check (4 corners x 5x5 patch x threshold 235) with margin.

The 4 deterministic checks are owned by ``app.modules.image.tasks`` and are
NOT re-implemented here — this generator only manufactures inputs whose
ground-truth outcome under those checks is known by construction.

Run (regenerate fixtures + fixtures.json):
    python3 backend/tests/eval/precheck_smoke/gen_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

_HERE = Path(__file__).resolve().parent
_FIXTURES_DIR = _HERE / "fixtures"
_FIXTURES_JSON = _HERE / "fixtures.json"

# White-BG corner brightness for GOOD images: >= 240 clears the as-built
# 235 threshold with margin even after JPEG quantisation of solid white.
_WHITE = (255, 255, 255)
_GOOD_SIZE = 1500


def _save_jpeg(img: Image.Image, path: Path) -> None:
    # quality=95 keeps solid white corners well above the 235 threshold.
    img.save(path, format="JPEG", quality=95)


def _save_png(img: Image.Image, path: Path) -> None:
    img.save(path, format="PNG")


def _white_canvas(size: int) -> Image.Image:
    return Image.new("RGB", (size, size), _WHITE)


def _draw_centered_product(img: Image.Image, color: tuple[int, int, int]) -> None:
    """Draw a centred coloured rectangle (the 'product') leaving white margins.

    The corners stay the canvas background colour so the white-BG corner
    sampler reads the background, not the product.
    """
    w, h = img.size
    d = ImageDraw.Draw(img)
    # Product occupies the central 50% — corners untouched.
    x0, y0 = int(w * 0.28), int(h * 0.28)
    x1, y1 = int(w * 0.72), int(h * 0.72)
    d.rectangle([x0, y0, x1, y1], fill=color)


def _gradient_canvas(size: int) -> Image.Image:
    """Colourful textured gradient — corners are NON-white (white_bg fail)."""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            px[x, y] = ((x * 255) // size, (y * 255) // size, 128)
    return img


# Down-sample gradient generation for speed: build small then resize.
def _gradient_canvas_fast(size: int) -> Image.Image:
    small = 64
    base = Image.new("RGB", (small, small))
    px = base.load()
    for y in range(small):
        for x in range(small):
            px[x, y] = ((x * 255) // small, (y * 255) // small, 128)
    return base.resize((size, size), Image.NEAREST)


def build() -> list[dict]:
    _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    # ───────────────────────── KNOWN-BAD (10) ─────────────────────────

    # bad_01 — PNG (not JPEG). White BG, 1500, RGB; only jpeg fails.
    p = _FIXTURES_DIR / "bad_01_png.png"
    img = _white_canvas(_GOOD_SIZE)
    _draw_centered_product(img, (40, 90, 200))
    _save_png(img, p)
    entries.append(
        {
            "id": "bad_01_png",
            "file": "fixtures/bad_01_png.png",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["jpeg"],
        }
    )

    # bad_02 — CMYK JPEG, 1500, light BG. colorspace fails.
    p = _FIXTURES_DIR / "bad_02_cmyk.jpg"
    img = _white_canvas(_GOOD_SIZE)
    _draw_centered_product(img, (40, 90, 200))
    img.convert("CMYK").save(p, format="JPEG", quality=95)
    entries.append(
        {
            "id": "bad_02_cmyk",
            "file": "fixtures/bad_02_cmyk.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["color_space"],
        }
    )

    # bad_03 — 1000x1000 RGB JPEG, white BG. resolution fails.
    p = _FIXTURES_DIR / "bad_03_small.jpg"
    img = _white_canvas(1000)
    _draw_centered_product(img, (40, 90, 200))
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_03_small",
            "file": "fixtures/bad_03_small.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["resolution"],
        }
    )

    # bad_04 — dark-gray BG RGB JPEG, 1500. white_bg fails.
    p = _FIXTURES_DIR / "bad_04_dark_bg.jpg"
    img = Image.new("RGB", (_GOOD_SIZE, _GOOD_SIZE), (60, 60, 60))
    _draw_centered_product(img, (200, 200, 200))
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_04_dark_bg",
            "file": "fixtures/bad_04_dark_bg.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["white_bg"],
        }
    )

    # bad_05 — 800x800 PNG. jpeg + resolution fail.
    p = _FIXTURES_DIR / "bad_05_png_small.png"
    img = _white_canvas(800)
    _draw_centered_product(img, (40, 90, 200))
    _save_png(img, p)
    entries.append(
        {
            "id": "bad_05_png_small",
            "file": "fixtures/bad_05_png_small.png",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["jpeg", "resolution"],
        }
    )

    # bad_06 — CMYK 1200x1200 JPEG. colorspace + resolution fail.
    p = _FIXTURES_DIR / "bad_06_cmyk_small.jpg"
    img = _white_canvas(1200)
    _draw_centered_product(img, (40, 90, 200))
    img.convert("CMYK").save(p, format="JPEG", quality=95)
    entries.append(
        {
            "id": "bad_06_cmyk_small",
            "file": "fixtures/bad_06_cmyk_small.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["color_space", "resolution"],
        }
    )

    # bad_07 — colourful textured (gradient) BG RGB JPEG, 1500. white_bg fails.
    p = _FIXTURES_DIR / "bad_07_textured_bg.jpg"
    img = _gradient_canvas_fast(_GOOD_SIZE)
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_07_textured_bg",
            "file": "fixtures/bad_07_textured_bg.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["white_bg"],
        }
    )

    # bad_08 — hue-tinted (non-pure-white) BG RGB JPEG, 1500. white_bg fails.
    # Light blue (200,210,255): blue channel ~255 but R/G ~200 < 235 -> fail.
    p = _FIXTURES_DIR / "bad_08_hue_tint.jpg"
    img = Image.new("RGB", (_GOOD_SIZE, _GOOD_SIZE), (200, 210, 255))
    _draw_centered_product(img, (40, 90, 200))
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_08_hue_tint",
            "file": "fixtures/bad_08_hue_tint.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["white_bg"],
        }
    )

    # bad_09 — black BG RGB JPEG, 1500. white_bg fails.
    p = _FIXTURES_DIR / "bad_09_black_bg.jpg"
    img = Image.new("RGB", (_GOOD_SIZE, _GOOD_SIZE), (0, 0, 0))
    _draw_centered_product(img, (220, 220, 220))
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_09_black_bg",
            "file": "fixtures/bad_09_black_bg.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["white_bg"],
        }
    )

    # bad_10 — grass/lifestyle BG RGB JPEG, 1500. white_bg fails.
    p = _FIXTURES_DIR / "bad_10_grass_bg.jpg"
    img = Image.new("RGB", (_GOOD_SIZE, _GOOD_SIZE), (74, 124, 47))  # grass green
    _draw_centered_product(img, (190, 120, 60))  # earthy product
    _save_jpeg(img, p)
    entries.append(
        {
            "id": "bad_10_grass_bg",
            "file": "fixtures/bad_10_grass_bg.jpg",
            "category": "bad",
            "expected_status": "failed_precheck",
            "expected_fail_reasons": ["white_bg"],
        }
    )

    # ───────────────────────── KNOWN-GOOD (10) ────────────────────────
    # 1500x1500 RGB JPEG, pure-white BG; corners stay 255 (>= 240 margin).
    good_products = [
        (200, 40, 40),    # red
        (40, 160, 40),    # green
        (40, 40, 200),    # blue
        (200, 160, 40),   # amber
        (160, 40, 200),   # purple
        (40, 180, 180),   # teal
        (120, 80, 40),    # brown
        (90, 90, 90),     # gray product on white
        (220, 80, 140),   # pink
        (50, 50, 120),    # navy
    ]
    for i, color in enumerate(good_products, start=1):
        fname = f"good_{i:02d}.jpg"
        p = _FIXTURES_DIR / fname
        # Vary size slightly to prove >= 1500 (not exactly 1500) also passes.
        size = _GOOD_SIZE if i % 2 == 0 else _GOOD_SIZE + 100
        img = _white_canvas(size)
        _draw_centered_product(img, color)
        _save_jpeg(img, p)
        entries.append(
            {
                "id": f"good_{i:02d}",
                "file": f"fixtures/{fname}",
                "category": "good",
                "expected_status": "ready",
                "expected_fail_reasons": [],
            }
        )

    _FIXTURES_JSON.write_text(json.dumps(entries, indent=2) + "\n")
    return entries


if __name__ == "__main__":
    built = build()
    total_bytes = sum(
        (_HERE / e["file"]).stat().st_size for e in built
    )
    print(f"generated {len(built)} fixtures, total {total_bytes} bytes")
    print(f"wrote {_FIXTURES_JSON}")
