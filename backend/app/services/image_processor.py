"""Image processing pipeline: rembg → white BG → resize → JPEG compress.

The full pipeline is exposed as :func:`run_pipeline`, used by the Celery
worker. Individual stages are kept pure (in-memory ``PIL.Image`` round-trips)
so they can be unit-tested without a worker.
"""

from __future__ import annotations

import asyncio
import io
import logging
import uuid

from PIL import Image as PILImage
from sqlalchemy import select

from app.database import async_session_maker
from app.models.catalog import Catalog
from app.models.image import Image as ImageModel
from app.models.sku import SKU
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

TARGET_SIZE = (1024, 1024)
JPEG_QUALITY_DEFAULT = 90
MAX_KB_DEFAULT = 500


def remove_background(image_bytes: bytes) -> PILImage.Image:
    """Run rembg on raw image bytes, returning an RGBA image.

    Rembg is heavy (ONNX model download on first call) — imported lazily so
    importing this module stays cheap during tests.
    """
    from rembg import remove  # type: ignore

    out_bytes = remove(image_bytes)
    return PILImage.open(io.BytesIO(out_bytes)).convert("RGBA")


def add_white_background(rgba: PILImage.Image) -> PILImage.Image:
    """Composite an RGBA image onto an opaque white canvas."""
    if rgba.mode != "RGBA":
        rgba = rgba.convert("RGBA")
    bg = PILImage.new("RGB", rgba.size, (255, 255, 255))
    bg.paste(rgba, mask=rgba.split()[3])
    return bg


def resize_and_pad(image: PILImage.Image, target: tuple[int, int] = TARGET_SIZE) -> PILImage.Image:
    """Scale ``image`` to fit ``target`` preserving aspect ratio, then center-pad with white."""
    rgb = image.convert("RGB")
    rgb.thumbnail(target, PILImage.Resampling.LANCZOS)
    canvas = PILImage.new("RGB", target, (255, 255, 255))
    canvas.paste(rgb, ((target[0] - rgb.width) // 2, (target[1] - rgb.height) // 2))
    return canvas


def compress_jpeg(
    image: PILImage.Image, quality: int = JPEG_QUALITY_DEFAULT, max_kb: int = MAX_KB_DEFAULT
) -> bytes:
    """Encode as JPEG, reducing quality until the result is under ``max_kb`` KB."""
    q = quality
    buf = io.BytesIO()
    while q >= 50:
        buf.seek(0)
        buf.truncate(0)
        image.save(buf, format="JPEG", quality=q, optimize=True)
        if buf.tell() / 1024 <= max_kb:
            break
        q -= 10
    return buf.getvalue()


def detect_watermark(image: PILImage.Image) -> bool:
    """Heuristic watermark detector.

    Watermarks tend to live in the corners and contain text or logos that
    raise the local edge density relative to the rest of the image. We
    compare the average gradient magnitude of the 4 corner patches with the
    central patch — a corner spike exceeding ``threshold×`` the centre is
    treated as a watermark.

    This is intentionally cheap (no OCR / ML) and tuned to flag obvious
    cases. False positives are preferred over false negatives for the
    QualityGate use case.
    """
    from PIL import ImageFilter, ImageStat

    gray = image.convert("L").filter(ImageFilter.FIND_EDGES)
    w, h = gray.size
    patch = min(w, h) // 6
    if patch < 16:
        return False

    def _mean(box: tuple[int, int, int, int]) -> float:
        return ImageStat.Stat(gray.crop(box)).mean[0]

    corners = [
        _mean((0, 0, patch, patch)),
        _mean((w - patch, 0, w, patch)),
        _mean((0, h - patch, patch, h)),
        _mean((w - patch, h - patch, w, h)),
    ]
    cx, cy = w // 2, h // 2
    center = _mean((cx - patch // 2, cy - patch // 2, cx + patch // 2, cy + patch // 2))
    if center < 1.0:
        center = 1.0
    return max(corners) > 2.5 * center


async def run_pipeline(image_id: uuid.UUID) -> dict:
    """Full pipeline: download → rembg → composite → resize → compress → upload → DB."""
    storage = get_storage()

    async with async_session_maker() as db:
        image = await db.get(ImageModel, image_id)
        if image is None:
            raise ValueError(f"Image {image_id} not found")
        sku = await db.get(SKU, image.sku_id)
        catalog = await db.get(Catalog, sku.catalog_id)
        user_id = catalog.user_id

        original_bytes = await _download(image.original_url)

        def _process() -> tuple[bytes, bool]:
            rgba = remove_background(original_bytes)
            white = add_white_background(rgba)
            sized = resize_and_pad(white, TARGET_SIZE)
            jpeg = compress_jpeg(sized, max_kb=MAX_KB_DEFAULT)
            wm = detect_watermark(sized)
            return jpeg, wm

        jpeg_bytes, has_watermark = await asyncio.to_thread(_process)

        processed_path = f"processed/{user_id}/{image.id}.jpg"
        processed_url = await storage.upload(jpeg_bytes, processed_path, "image/jpeg")

        image.processed_url = processed_url
        image.bg_removed = True
        image.resized = True
        image.width = TARGET_SIZE[0]
        image.height = TARGET_SIZE[1]
        image.file_size_kb = len(jpeg_bytes) // 1024
        image.format = "jpg"
        image.has_watermark = has_watermark
        image.is_compliant = not has_watermark
        image.compliance_note = "watermark detected" if has_watermark else None
        await db.commit()

        return {
            "image_id": str(image.id),
            "processed_url": processed_url,
            "size_kb": image.file_size_kb,
            "has_watermark": has_watermark,
        }


async def _download(url: str) -> bytes:
    """Read raw bytes from a storage URL (local file:// or http(s)://)."""
    if url.startswith("file://"):
        path = url[len("file://") :]

        def _read() -> bytes:
            with open(path, "rb") as fh:
                return fh.read()

        return await asyncio.to_thread(_read)

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
