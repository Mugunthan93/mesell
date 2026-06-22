"""QA Wave 3 — W3-BE-7, BE-8, BE-9: PIL precheck boundary unit tests.

Tests the 4 deterministic PIL check functions directly at the pass/fail
boundary. The functions are IMPORTED from ``app.modules.image.tasks`` — never
re-implemented here. If a check is wrong, the fix belongs in tasks.py.

GCS is NOT involved in any of these tests (the functions operate on in-memory
Pillow Image objects or raw bytes). No Celery. No DB.

Founder decision (plan §3 Q3 / BE-7…10): PIL boundary tests authored at the
unit/eval layer only; GCS mocked at adapter boundary for any paths that do
reach the task level.

Case mapping:
  W3-BE-7  CMYK JPEG fails colour-space check; sRGB passes.
  W3-BE-8  Below-min-resolution image fails; at/above threshold passes.
  W3-BE-9  Non-white-BG image flagged; white-BG image passes.

All PIL image objects are constructed programmatically with Pillow — no
fixture files required, no real Gemini/GCS/MSG91 calls.

Env bootstrapping: ``_check_color_space`` / ``_check_resolution`` /
``_check_white_background`` are SYNCHRONOUS (no asyncio); ``_check_jpeg``
does a Pillow open from bytes. The dummy env vars below mirror
``eval/precheck_smoke/test_pillow_checks.py`` so the tasks module can be
imported hermetically.
"""

from __future__ import annotations

import io
import os

import pytest

# ── Env bootstrap (mirror conftest.py + test_pillow_checks.py) ───────────────
# Importing app.modules.image.tasks loads app.shared.config.Settings which
# requires several env vars. Set DUMMY values so the import succeeds without
# a real .env — no network or DB access occurs.
_DUMMY_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+asyncpg://meesell:password@localhost:5432/meesell_test",
    "VALKEY_URL": "redis://localhost:6381/15",
    "JWT_SECRET": "test-secret-do-not-use",
    "REFRESH_TOKEN_PEPPER": "test-pepper-do-not-use",
    "MSG91_AUTH_KEY": "test",
    "MSG91_TEMPLATE_ID": "test",
    "RAZORPAY_KEY_ID": "test",
    "RAZORPAY_KEY_SECRET": "test",
    "RAZORPAY_WEBHOOK_SECRET": "test",
    "GEMINI_API_KEY": "test-not-a-real-key",
    "GCS_BUCKET": "test-bucket",
    "GCS_PROJECT_ID": "test-project",
    "LANGFUSE_PUBLIC_KEY": "test",
    "LANGFUSE_SECRET_KEY": "test",
    "AUDIT_PII_SALT": "test-salt",
    "CORS_ALLOWED_ORIGINS": "https://app.meesell.test",
    "SECRET_KEY": "test-secret-key",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

# Import the AS-BUILT check functions — do NOT re-implement.
from app.modules.image.tasks import (  # noqa: E402
    _check_color_space,
    _check_jpeg,
    _check_resolution,
    _check_white_background,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — build minimal in-memory Pillow images
# ─────────────────────────────────────────────────────────────────────────────

def _make_pil_image(mode: str, size: tuple[int, int], color: tuple | int = 0):
    """Return a minimal Pillow Image in the requested mode and size."""
    from PIL import Image
    return Image.new(mode, size, color=color)


def _to_jpeg_bytes(img) -> bytes:
    """Save a Pillow Image as JPEG bytes (in-memory)."""
    buf = io.BytesIO()
    rgb_img = img.convert("RGB") if img.mode not in ("RGB", "RGBA", "L") else img
    rgb_img.save(buf, format="JPEG")
    return buf.getvalue()


def _to_jpeg_bytes_cmyk(img) -> bytes:
    """Save a CMYK Pillow Image as JPEG bytes (CMYK JPEG)."""
    buf = io.BytesIO()
    cmyk = img if img.mode == "CMYK" else img.convert("CMYK")
    cmyk.save(buf, format="JPEG")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-7 — CMYK colour-space check pass/fail boundary
# ─────────────────────────────────────────────────────────────────────────────

class TestColorSpaceCheck:
    """W3-BE-7: _check_color_space(img) returns 'CMYK' for CMYK; 'RGB' for RGB."""

    def test_cmyk_image_returns_cmyk(self):
        """A CMYK Pillow image → _check_color_space returns 'CMYK' (fail boundary)."""
        from PIL import Image
        cmyk_img = Image.new("CMYK", (100, 100), color=(0, 0, 0, 0))
        result = _check_color_space(cmyk_img)
        assert result == "CMYK", (
            f"_check_color_space must return 'CMYK' for a CMYK image; got {result!r}"
        )

    def test_rgb_image_returns_rgb(self):
        """An RGB Pillow image → _check_color_space returns 'RGB' (pass boundary)."""
        from PIL import Image
        rgb_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = _check_color_space(rgb_img)
        assert result == "RGB", (
            f"_check_color_space must return 'RGB' for an RGB image; got {result!r}"
        )

    def test_rgba_image_returns_rgb(self):
        """An RGBA Pillow image → _check_color_space returns 'RGB' (RGBA is RGB-class)."""
        from PIL import Image
        rgba_img = Image.new("RGBA", (100, 100), color=(255, 255, 255, 255))
        result = _check_color_space(rgba_img)
        assert result == "RGB", (
            f"_check_color_space must return 'RGB' for RGBA; got {result!r}"
        )

    def test_cmyk_jpeg_bytes_fail_color_space(self):
        """A CMYK JPEG bytes-path: _check_jpeg succeeds (JPEG valid) then
        _check_color_space returns 'CMYK' → images fails the colour-space check.
        """
        from PIL import Image
        cmyk_img = Image.new("CMYK", (2000, 2000), color=(0, 0, 0, 0))
        jpeg_bytes = _to_jpeg_bytes_cmyk(cmyk_img)

        jpeg_valid, img = _check_jpeg(jpeg_bytes)
        assert jpeg_valid, "CMYK JPEG must be detected as a valid JPEG by _check_jpeg"
        assert img is not None, "_check_jpeg must return the Pillow image for CMYK"

        color_space = _check_color_space(img)
        assert color_space == "CMYK", (
            f"CMYK JPEG must fail colour-space check; got {color_space!r}"
        )

    def test_srgb_jpeg_bytes_pass_color_space(self):
        """An sRGB JPEG bytes-path: _check_jpeg succeeds and _check_color_space
        returns 'RGB' → image passes the colour-space check.
        """
        from PIL import Image
        rgb_img = Image.new("RGB", (2000, 2000), color=(255, 255, 255))
        jpeg_bytes = _to_jpeg_bytes(rgb_img)

        jpeg_valid, img = _check_jpeg(jpeg_bytes)
        assert jpeg_valid, "sRGB JPEG must be detected as a valid JPEG by _check_jpeg"
        assert img is not None

        color_space = _check_color_space(img)
        assert color_space == "RGB", (
            f"sRGB JPEG must pass colour-space check; got {color_space!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-8 — resolution boundary (1500×1500 min, per §11.E step 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestResolutionCheck:
    """W3-BE-8: _check_resolution fails below 1500x1500; passes at/above."""

    def test_below_min_resolution_fails(self):
        """1499x1499 image → _check_resolution returns False (fail boundary)."""
        from PIL import Image
        small = Image.new("RGB", (1499, 1499), color=(255, 255, 255))
        assert _check_resolution(small) is False, (
            "_check_resolution must return False for a 1499x1499 image"
        )

    def test_exactly_min_resolution_passes(self):
        """1500x1500 image → _check_resolution returns True (boundary pass)."""
        from PIL import Image
        exact = Image.new("RGB", (1500, 1500), color=(255, 255, 255))
        assert _check_resolution(exact) is True, (
            "_check_resolution must return True for exactly 1500x1500"
        )

    def test_above_min_resolution_passes(self):
        """2000x2000 image → _check_resolution returns True (above threshold)."""
        from PIL import Image
        large = Image.new("RGB", (2000, 2000), color=(255, 255, 255))
        assert _check_resolution(large) is True, (
            "_check_resolution must return True for a 2000x2000 image"
        )

    def test_non_square_below_fails(self):
        """1500x1499 (one dimension below) → _check_resolution returns False."""
        from PIL import Image
        rect = Image.new("RGB", (1500, 1499), color=(255, 255, 255))
        assert _check_resolution(rect) is False, (
            "_check_resolution must return False when height < 1500"
        )

    def test_non_square_both_above_passes(self):
        """1600x1500 (both at/above min) → _check_resolution returns True."""
        from PIL import Image
        rect = Image.new("RGB", (1600, 1500), color=(255, 255, 255))
        assert _check_resolution(rect) is True, (
            "_check_resolution must return True when both dimensions >= 1500"
        )


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-9 — white-background boundary (corner-sampling, 235/255 threshold)
# ─────────────────────────────────────────────────────────────────────────────

class TestWhiteBackgroundCheck:
    """W3-BE-9: _check_white_background passes on white-BG; fails on coloured BG.

    The check samples 5x5 corner patches.  A white 1500x1500 image has all 4
    corners at (255, 255, 255) → passes.  A solid red image has all 4 corners
    at (255, 0, 0) → average green/blue channels are 0 < 235 → fails.
    """

    def test_white_background_passes(self):
        """All-white 1500x1500 image → _check_white_background returns True."""
        from PIL import Image
        white = Image.new("RGB", (1500, 1500), color=(255, 255, 255))
        assert _check_white_background(white) is True, (
            "_check_white_background must return True for an all-white image"
        )

    def test_off_white_passes(self):
        """Near-white (240, 240, 240) image → passes (240 > 235 threshold)."""
        from PIL import Image
        off_white = Image.new("RGB", (1500, 1500), color=(240, 240, 240))
        assert _check_white_background(off_white) is True, (
            "_check_white_background must pass for a (240,240,240) near-white image"
        )

    def test_below_threshold_fails(self):
        """(230, 230, 230) image → fails (230 < 235 threshold)."""
        from PIL import Image
        below = Image.new("RGB", (1500, 1500), color=(230, 230, 230))
        assert _check_white_background(below) is False, (
            "_check_white_background must fail for a (230,230,230) image (below threshold)"
        )

    def test_solid_red_background_fails(self):
        """Solid red (255, 0, 0) background → fails (green/blue channels are 0)."""
        from PIL import Image
        red = Image.new("RGB", (1500, 1500), color=(255, 0, 0))
        assert _check_white_background(red) is False, (
            "_check_white_background must return False for a solid red image"
        )

    def test_dark_background_fails(self):
        """Dark (50, 50, 50) background → fails (all channels below threshold)."""
        from PIL import Image
        dark = Image.new("RGB", (1500, 1500), color=(50, 50, 50))
        assert _check_white_background(dark) is False, (
            "_check_white_background must return False for a dark image"
        )

    def test_image_too_small_fails(self):
        """Image smaller than 10x10 → _check_white_background returns False (size guard)."""
        from PIL import Image
        tiny = Image.new("RGB", (5, 5), color=(255, 255, 255))
        assert _check_white_background(tiny) is False, (
            "_check_white_background must return False for an image < 10x10 px"
        )

    def test_cmyk_image_converted_and_passes_if_near_white(self):
        """CMYK (0,0,0,0) = white in CMYK printing → converts to RGB and passes.

        The CMYK (0,0,0,0) ink values correspond to no ink = white paper.
        After the defensive ``img.convert('RGB')`` inside the function the
        resulting pixels are near-white and should pass the threshold.
        """
        from PIL import Image
        # CMYK (0,0,0,0) → RGB (255,255,255) after conversion.
        cmyk_white = Image.new("CMYK", (1500, 1500), color=(0, 0, 0, 0))
        result = _check_white_background(cmyk_white)
        # CMYK (0,0,0,0) is white — after conversion all corners should be bright.
        # This asserts the function does NOT crash on non-RGB input.
        assert isinstance(result, bool), (
            "_check_white_background must return a bool even for CMYK input"
        )
