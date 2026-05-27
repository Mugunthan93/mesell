"""Image-pipeline stage tests (no rembg — that needs ONNX model download)."""

import io

import pytest
from PIL import Image, ImageDraw

from app.services.image_processor import (
    add_white_background,
    compress_jpeg,
    detect_watermark,
    resize_and_pad,
)


def _rgba(size, fill):
    return Image.new("RGBA", size, fill)


def test_add_white_background_converts_to_rgb_and_fills_transparent():
    src = _rgba((100, 100), (0, 0, 0, 0))  # fully transparent
    out = add_white_background(src)
    assert out.mode == "RGB"
    # Centre pixel was transparent → should now read as white.
    assert out.getpixel((50, 50)) == (255, 255, 255)


def test_add_white_background_preserves_opaque_pixels():
    src = _rgba((10, 10), (200, 100, 50, 255))
    out = add_white_background(src)
    assert out.getpixel((5, 5)) == (200, 100, 50)


def test_add_white_background_accepts_rgb_input():
    src = Image.new("RGB", (10, 10), (50, 50, 50))
    out = add_white_background(src)
    assert out.mode == "RGB"


def test_resize_and_pad_exact_target_size():
    src = Image.new("RGB", (800, 600), (255, 0, 0))
    out = resize_and_pad(src, (1024, 1024))
    assert out.size == (1024, 1024)
    # Corners should be white from padding.
    assert out.getpixel((0, 0)) == (255, 255, 255)


def test_resize_and_pad_preserves_aspect_ratio_via_thumbnail():
    src = Image.new("RGB", (2000, 500), (255, 0, 0))  # 4:1 aspect
    out = resize_and_pad(src, (1024, 1024))
    # The image scales down to fit the 1024 width, height becomes 256.
    # Centre pixel of the image-band (row ~512) should be red.
    assert out.getpixel((512, 512)) == (255, 0, 0)
    # Top/bottom padding bands should be white.
    assert out.getpixel((512, 100)) == (255, 255, 255)
    assert out.getpixel((512, 900)) == (255, 255, 255)


def test_compress_jpeg_under_size_budget():
    src = Image.new("RGB", (1024, 1024), (128, 128, 128))
    data = compress_jpeg(src, max_kb=100)
    assert len(data) / 1024 <= 100
    # Output is decodable.
    Image.open(io.BytesIO(data)).load()


def test_compress_jpeg_steps_down_quality_to_meet_budget():
    """A gradient image should fit under the budget after the quality loop runs."""
    src = Image.new("RGB", (1024, 1024))
    pixels = [(i % 256, (i * 2) % 256, (i * 3) % 256) for i in range(1024 * 1024)]
    src.putdata(pixels)
    data = compress_jpeg(src, quality=95, max_kb=300)
    assert len(data) / 1024 <= 300


def test_compress_jpeg_terminates_on_uncompressible_input():
    """Pure noise can't compress to <100KB; the loop must exit and still produce a JPEG."""
    import random
    random.seed(42)
    src = Image.new("RGB", (1024, 1024))
    src.putdata([(random.randrange(256), random.randrange(256), random.randrange(256)) for _ in range(1024 * 1024)])
    data = compress_jpeg(src, quality=95, max_kb=100)
    assert len(data) > 0
    Image.open(io.BytesIO(data)).load()


def test_detect_watermark_false_on_flat_image():
    src = Image.new("RGB", (1024, 1024), (180, 180, 180))
    assert detect_watermark(src) is False


def test_detect_watermark_true_on_corner_text_block():
    src = Image.new("RGB", (1024, 1024), (180, 180, 180))
    d = ImageDraw.Draw(src)
    # Thick black-and-white pattern in the top-left corner.
    d.rectangle([10, 10, 180, 80], fill=(0, 0, 0))
    d.rectangle([20, 20, 170, 75], fill=(255, 255, 255))
    d.rectangle([30, 30, 160, 70], fill=(0, 0, 0))
    assert detect_watermark(src) is True


def test_detect_watermark_short_circuits_for_tiny_images():
    src = Image.new("RGB", (40, 40), (180, 180, 180))
    # patch < 16 px → must not crash, must return False.
    assert detect_watermark(src) is False
