"""Image precheck pipeline gap tests — IMG-BE-13 through IMG-BE-23.

Wave: qa-image-ai (Wave A).

Closes every **partial/gap** row in §1.A of the IMAGE_AI_QA_WAVE_PLAN.md:

IMG-BE-13  precheck CMYK → failed_precheck, color_space='CMYK', all 6 keys
IMG-BE-14  precheck sub-1500 resolution → failed_precheck, resolution_pass=False
IMG-BE-15  precheck non-white-BG → failed_precheck, white_background=False
IMG-BE-16  precheck invalid-JPEG early exit → all 6 keys, watermark NOT called
IMG-BE-17  precheck watermark has_watermark=True → watermark_check='has_watermark'
IMG-BE-18  precheck watermark has_watermark=False → watermark_check='no_watermark'
IMG-BE-19  precheck watermark adapter-raise → watermark_check='uncertain'
IMG-BE-21  precheck audit row written — image.precheck.completed
IMG-BE-22  precheck GCS download fail → GcsAdapterError re-raised (retry path)
IMG-BE-23  write_precheck_result not-found → ImageNotFoundError

Invariants asserted throughout:
- ALL 6 precheck_jsonb keys present regardless of which step fails.
- Watermark is INFORMATIONAL — has_watermark/uncertain/skipped_budget NEVER
  changes final_status when the 4 deterministic checks all pass.
- GCS and Gemini mocked at the adapter seam — zero real calls.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters import GcsAdapterError
from app.modules.image import service as image_service
from app.modules.image import tasks as image_tasks
from app.modules.image.exceptions import ImageNotFoundError

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# Expected set of ALL 6 precheck_jsonb keys per §11.G
_EXPECTED_KEYS = frozenset(
    {"jpeg_valid", "color_space", "resolution_pass", "white_background",
     "watermark_check", "watermark_confidence"}
)


# ---------------------------------------------------------------------------
# Pillow helper factories
# ---------------------------------------------------------------------------
def _make_jpeg_bytes(mode: str = "RGB", size: tuple[int, int] = (1500, 1500),
                     bg: tuple = (255, 255, 255)) -> bytes:
    """Return valid JPEG bytes for the given Pillow mode/size/background."""
    from io import BytesIO
    from PIL import Image
    img = Image.new(mode, size, color=bg)
    if mode == "CMYK":
        # Pillow won't create CMYK with a tuple bg the same way; use zero
        img = Image.new("CMYK", size, color=(0, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _make_small_jpeg_bytes() -> bytes:
    """800x800 white JPEG — fails resolution check."""
    return _make_jpeg_bytes(size=(800, 800))


def _make_dark_corner_jpeg() -> bytes:
    """1500x1500 JPEG with dark corners — fails white-background check."""
    from io import BytesIO
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1500, 1500), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 10, 10], fill=(0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _make_corrupt_jpeg_bytes() -> bytes:
    """Bytes that JPEG-header-sniff but are not a valid decodable image."""
    # SOI marker but then garbage
    return b"\xff\xd8\xff" + b"\x00" * 50


# ---------------------------------------------------------------------------
# Shared: drive pipeline inline (sidestep Celery broker)
# ---------------------------------------------------------------------------
async def _drive_pipeline(image_id, user_id):
    return await image_tasks._run_precheck_pipeline(image_id, user_id)


# ===========================================================================
# IMG-BE-13 — CMYK → failed_precheck
# ===========================================================================
class TestPrecheckCMYK:
    """Pillow detects CMYK → color_space='CMYK' → failed_precheck.

    Watermark vision is NOT called (pipeline exits on deterministic failure).
    All 6 precheck keys are present regardless.
    """

    async def test_cmyk_jpeg_fails_precheck_color_space(
        self,
        db,
        user,
        product,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        cmyk_bytes = _make_jpeg_bytes(mode="CMYK")
        stub_gcs_download["set"](cmyk_bytes)

        upload = UploadFile(
            file=io.BytesIO(cmyk_bytes),
            filename="cmyk.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        # All 6 keys present
        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        # CMYK detection
        assert precheck_jsonb["color_space"] == "CMYK"
        # Deterministic failure → failed_precheck
        assert final_status == "failed_precheck"
        # jpeg_valid can still be True (valid JPEG encoding, wrong color space)
        assert isinstance(precheck_jsonb["jpeg_valid"], bool)


# ===========================================================================
# IMG-BE-14 — sub-1500 resolution → failed_precheck
# ===========================================================================
class TestPrecheckSubResolution:
    """800x800 JPEG → resolution_pass=False → failed_precheck.

    Watermark step behavior is secondary here.  The deterministic gate
    is the load-bearing assertion.
    """

    async def test_sub_resolution_fails_precheck(
        self,
        db,
        user,
        product,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        small_bytes = _make_small_jpeg_bytes()
        stub_gcs_download["set"](small_bytes)

        upload = UploadFile(
            file=io.BytesIO(small_bytes),
            filename="small.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        assert precheck_jsonb["resolution_pass"] is False
        assert final_status == "failed_precheck"
        assert precheck_jsonb["jpeg_valid"] is True


# ===========================================================================
# IMG-BE-15 — non-white background → failed_precheck
# ===========================================================================
class TestPrecheckNonWhiteBackground:
    """Dark-corner JPEG → white_background=False → failed_precheck."""

    async def test_dark_corner_fails_white_background(
        self,
        db,
        user,
        product,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        dark_bytes = _make_dark_corner_jpeg()
        stub_gcs_download["set"](dark_bytes)

        upload = UploadFile(
            file=io.BytesIO(dark_bytes),
            filename="dark.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        assert precheck_jsonb["white_background"] is False
        assert final_status == "failed_precheck"


# ===========================================================================
# IMG-BE-16 — invalid JPEG early exit (all 6 keys, vision NOT called)
# ===========================================================================
class TestPrecheckInvalidJpegEarlyExit:
    """Corrupt bytes → jpeg_valid=False → early exit with 6 keys.

    The vision (watermark) step MUST NOT be called when JPEG parsing fails.
    The skill's "cheap checks first, vision last" invariant is enforced here.
    """

    async def test_corrupt_bytes_exits_early_with_6_keys_no_vision(
        self,
        db,
        user,
        product,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        # Use valid JPEG bytes for the upload route (passes MIME + Pillow at
        # service layer), then swap GCS download to return corrupt bytes so the
        # Celery task sees the invalid data.
        minimal_jpeg = _make_jpeg_bytes()
        stub_gcs_download["set"](_make_corrupt_jpeg_bytes())

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        # All 6 keys present even on early exit
        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        assert precheck_jsonb["jpeg_valid"] is False
        assert final_status == "failed_precheck"
        # Vision stub must NOT have been invoked (no image bytes to send)
        assert stub_call_gemini_watermark()["calls"] == [], (
            "Vision step must NOT fire when JPEG decode fails (cheap checks first)"
        )


# ===========================================================================
# IMG-BE-17 — watermark detected → watermark_check='has_watermark'
# ===========================================================================
class TestPrecheckWatermarkDetected:
    """Vision returns has_watermark=True → watermark_check='has_watermark'.

    Watermark is INFORMATIONAL — final_status still 'ready' when all 4
    deterministic checks pass.  This is the §5 wave invariant.
    """

    async def test_watermark_detected_is_informational_not_blocking(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        stub_gcs_download["set"](minimal_jpeg_bytes)
        # Configure stub to return has_watermark=True
        stub_call_gemini_watermark(parsed={"has_watermark": True, "confidence": 0.92})

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        assert precheck_jsonb["watermark_check"] == "has_watermark"
        assert precheck_jsonb["watermark_confidence"] == pytest.approx(0.92)
        # INVARIANT: watermark detection does NOT change final_status for a
        # valid 1500x1500 white-BG RGB JPEG.
        assert final_status == "ready", (
            "Watermark detection is informational — must NOT block a valid image"
        )


# ===========================================================================
# IMG-BE-18 — watermark clean → watermark_check='no_watermark'
# ===========================================================================
class TestPrecheckWatermarkClean:
    """Vision returns has_watermark=False → watermark_check='no_watermark'."""

    async def test_watermark_clean_sets_no_watermark(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers

        stub_gcs_download["set"](minimal_jpeg_bytes)
        stub_call_gemini_watermark(parsed={"has_watermark": False, "confidence": 0.98})

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        assert precheck_jsonb["watermark_check"] == "no_watermark"
        assert final_status == "ready"


# ===========================================================================
# IMG-BE-19 — watermark adapter raise → watermark_check='uncertain'
# ===========================================================================
class TestPrecheckWatermarkAdapterRaise:
    """Gemini adapter raises an unexpected exception → 'uncertain' (fail-safe).

    The pipeline MUST complete and NOT propagate the adapter error.
    The 'uncertain' state is the fail-safe — never silently 'no_watermark'.
    """

    async def test_adapter_raise_yields_uncertain_and_pipeline_completes(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        monkeypatch,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers
        from app.ai_ops import client as ai_ops_client

        stub_gcs_download["set"](minimal_jpeg_bytes)

        # Adapter raises a generic exception (simulates transport failure)
        async def _raise_adapter(*args, **kwargs):
            raise RuntimeError("Simulated adapter failure for watermark test")

        monkeypatch.setattr(ai_ops_client, "call_gemini", _raise_adapter)

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        # Must not raise — pipeline completes with uncertain watermark
        precheck_jsonb, final_status = await _drive_pipeline(resp.image_id, user.id)

        assert set(precheck_jsonb.keys()) == _EXPECTED_KEYS
        assert precheck_jsonb["watermark_check"] == "uncertain"
        # Valid image deterministic checks pass → still ready
        assert final_status == "ready"


# ===========================================================================
# IMG-BE-21 — precheck audit row written
# ===========================================================================
class TestPrecheckAuditRowWritten:
    """Pipeline completion emits one image.precheck.completed audit row.

    The audit write is non-blocking (drops on failure) — this test
    asserts the HAPPY path where the write succeeds.
    """

    async def test_audit_row_written_after_pipeline(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers
        from sqlalchemy import select
        from app.shared.models.audit_event import AuditEvent

        stub_gcs_download["set"](minimal_jpeg_bytes)

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        await _drive_pipeline(resp.image_id, user.id)

        # Query the audit table for the row the pipeline emitted.
        rows = (
            await db.execute(
                select(AuditEvent).where(
                    AuditEvent.event_type == "image.precheck.completed",
                    AuditEvent.entity_type == "product_image",
                )
            )
        ).scalars().all()

        assert len(rows) >= 1, "Expected at least one image.precheck.completed audit row"
        audit_row = rows[0]
        assert audit_row.metadata_jsonb is not None
        assert "final_status" in audit_row.metadata_jsonb
        assert audit_row.metadata_jsonb["final_status"] in ("ready", "failed_precheck")


# ===========================================================================
# IMG-BE-22 — GCS download fail → GcsAdapterError re-raised (retry path)
# ===========================================================================
class TestPrecheckGCSDownloadFail:
    """GCS download failure → GcsAdapterError propagates from _run_precheck_pipeline.

    The Celery task wraps this with ``self.retry`` (autoretry_for=GcsAdapterError).
    The test asserts the exception propagates out of the pipeline runner so
    the Celery task can schedule the retry.
    """

    async def test_gcs_download_fail_raises_gcs_adapter_error(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_signed_url,
        stub_celery_delay,
        monkeypatch,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers
        from app.adapters import gcs as gcs_adapter

        # GCS download raises GcsAdapterError
        async def _raise_gcs(*args, **kwargs):
            raise GcsAdapterError("Simulated GCS download failure")

        monkeypatch.setattr(gcs_adapter, "download_bytes", _raise_gcs)

        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()

        with pytest.raises(GcsAdapterError):
            await _drive_pipeline(resp.image_id, user.id)


# ===========================================================================
# IMG-BE-23 — write_precheck_result not-found → ImageNotFoundError
# ===========================================================================
class TestWritePrecheckResultNotFound:
    """``write_precheck_result`` raises ``ImageNotFoundError`` for missing image."""

    async def test_write_precheck_result_not_found_raises(self, db, user) -> None:
        non_existent_id = uuid.uuid4()
        with pytest.raises(ImageNotFoundError):
            await image_service.write_precheck_result(
                image_id=non_existent_id,
                user_id=user.id,
                precheck_jsonb={"jpeg_valid": True},
                status="ready",
                db=db,
            )
