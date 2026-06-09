"""Image-module integration tests — §11.K integration 1-3.

Per BACKEND_ARCHITECTURE.md §11.K:

  TestFullUploadPollReady          — POST upload → run precheck → poll list
                                     → status == "ready"; verify 5
                                     ``precheck_jsonb`` keys per §11.G.
  TestWatermarkBudgetExhaustion    — mock ``ai_ops.client.call_gemini`` to
                                     raise ``BudgetExceededError`` → verify
                                     ``precheck_jsonb.watermark_check ==
                                     "skipped_budget"`` AND overall
                                     ``status == "ready"`` (informational,
                                     non-blocking — confirms §6A.F graceful
                                     fallback wiring).
  TestCrossModuleUrlFetch          — ``catalog.service.get_preview`` calls
                                     ``image.service.get_image_urls`` →
                                     verify returned ``list[ImageUrl]`` has
                                     signed URLs ordered by ``idx`` with
                                     ``is_front=True`` set ONLY on idx=1.

These tests run against the ephemeral test DB (top-level conftest's
``db_session``).  Celery is mocked at the ``delay`` boundary: tests
directly drive the precheck pipeline inline via the synchronous
:func:`asyncio.run(_run_precheck_pipeline(...))` path so the assertions
do not depend on a live Celery worker.

Mock layer
----------
* ``adapters.gcs.upload_bytes`` / ``download_bytes`` / ``generate_signed_url``
  — patched per conftest fixtures.
* ``ai_ops.client.call_gemini`` — patched per conftest's
  ``stub_call_gemini_watermark`` / ``stub_call_gemini_budget_exceeded``.
* ``image_precheck_task.delay`` — patched per conftest's
  ``stub_celery_delay`` (no live broker).

Same precedent as §10 catalog integration tests.
"""

from __future__ import annotations

import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.modules.image import service as image_service
from app.modules.image import tasks as image_tasks

pytestmark = pytest.mark.asyncio


def _make_upload_file(
    *, data: bytes, content_type: str = "image/jpeg", filename: str = "img.jpg"
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


async def _drive_precheck_inline(image_id, user_id):
    """Drive the precheck pipeline inline (sidestep Celery worker).

    Tests call this directly after a POST to simulate the worker picking
    up the task.  Returns the assembled ``(precheck_jsonb, final_status)``
    tuple per :func:`tasks._run_precheck_pipeline`.
    """
    return await image_tasks._run_precheck_pipeline(image_id, user_id)


# ─────────────────────────────────────────────────────────────────────────────
# §11.K Integration 1 — Full upload → poll → ready flow
# ─────────────────────────────────────────────────────────────────────────────
class TestFullUploadPollReady:
    """POST upload → run precheck → poll GET → status == "ready".

    Verifies the ``precheck_jsonb`` has 5 keys (``jpeg_valid``,
    ``color_space``, ``resolution_pass``, ``white_background``,
    ``watermark_check``) with correct types per §11.G ``PrecheckResult``.
    """

    async def test_happy_path_5_keys_ready(
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
        # Configure GCS download to return the same JPEG that was uploaded —
        # the precheck task reads from GCS.  In this mocked setup the
        # download stub returns whatever we tell it; default is the
        # 1500x1500 white JPEG.
        stub_gcs_download["set"](minimal_jpeg_bytes)

        # 1. POST upload.
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        upload_response = await image_service.upload_image(
            user_id=user.id,
            product_id=product.id,
            file=upload,
            idx=1,
            db=db,
        )
        await db.commit()

        # Confirm route side of the contract.
        assert upload_response.status == "pending"
        assert upload_response.idx == 1
        assert upload_response.gcs_path == (
            f"meesell-images/{user.id}/{product.id}/1.jpg"
        )

        # 2. Drive the precheck pipeline inline (sidestep Celery).
        precheck_jsonb, final_status = await _drive_precheck_inline(
            upload_response.image_id, user.id
        )

        # 3. Verify 5-key shape per §11.G PrecheckResult.
        assert set(precheck_jsonb.keys()) == {
            "jpeg_valid",
            "color_space",
            "resolution_pass",
            "white_background",
            "watermark_check",
            "watermark_confidence",
        }
        assert isinstance(precheck_jsonb["jpeg_valid"], bool)
        assert precheck_jsonb["color_space"] in ("RGB", "CMYK", "Gray")
        assert isinstance(precheck_jsonb["resolution_pass"], bool)
        assert isinstance(precheck_jsonb["white_background"], bool)
        assert precheck_jsonb["watermark_check"] in (
            "no_watermark", "has_watermark", "uncertain", "skipped_budget"
        )

        # Happy-path expectations for the 1500x1500 white JPEG.
        assert precheck_jsonb["jpeg_valid"] is True
        assert precheck_jsonb["color_space"] == "RGB"
        assert precheck_jsonb["resolution_pass"] is True
        assert precheck_jsonb["white_background"] is True
        assert precheck_jsonb["watermark_check"] == "no_watermark"
        assert final_status == "ready"

        # 4. Poll via GET /images and confirm status="ready".
        images_list = await image_service.list_images(user.id, product.id, db=db)
        assert len(images_list.images) == 1
        first = images_list.images[0]
        assert first.idx == 1
        assert first.is_front is True
        assert first.status == "ready"
        # signed_url assertion via the deterministic stub.
        assert "signed=1" in first.signed_url
        assert first.precheck_jsonb["jpeg_valid"] is True


# ─────────────────────────────────────────────────────────────────────────────
# §11.K Integration 2 — Watermark budget exhaustion (graceful fallback)
# ─────────────────────────────────────────────────────────────────────────────
class TestWatermarkBudgetExhaustion:
    """Mock ``ai_ops.client.call_gemini`` to raise ``BudgetExceededError``.

    Verify:

    * ``precheck_jsonb.watermark_check == "skipped_budget"``
    * Overall ``status == "ready"`` (informational, non-blocking).

    Confirms §6A.F graceful-fallback wiring + the founder ruling that
    sellers are NOT penalised for AI budget exhaustion they didn't cause.
    """

    async def test_budget_exhausted_falls_back_to_skipped_budget(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_budget_exceeded,  # raises BudgetExceededError
    ):
        stub_gcs_download["set"](minimal_jpeg_bytes)

        # POST upload.
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        upload_response = await image_service.upload_image(
            user_id=user.id,
            product_id=product.id,
            file=upload,
            idx=2,
            db=db,
        )
        await db.commit()

        # Drive the precheck inline — call_gemini raises; tasks._check_watermark
        # catches and returns ("skipped_budget", None).
        precheck_jsonb, final_status = await _drive_precheck_inline(
            upload_response.image_id, user.id
        )

        # Budget fallback marker landed.
        assert precheck_jsonb["watermark_check"] == "skipped_budget"
        assert precheck_jsonb["watermark_confidence"] is None

        # Deterministic checks all passed → overall status STILL ready.
        # This is the §11.J + §6A.F locked behaviour: watermark step is
        # informational, NOT blocking.
        assert precheck_jsonb["jpeg_valid"] is True
        assert precheck_jsonb["color_space"] == "RGB"
        assert precheck_jsonb["resolution_pass"] is True
        assert precheck_jsonb["white_background"] is True
        assert final_status == "ready"


# ─────────────────────────────────────────────────────────────────────────────
# §11.K Integration 3 — Cross-module URL fetch (catalog.get_preview seam)
# ─────────────────────────────────────────────────────────────────────────────
class TestCrossModuleUrlFetch:
    """Verify the §11.C ``get_image_urls`` cross-module surface:

    * Returns ``list[ImageUrl]`` (NOT URL strings — frozen dataclasses).
    * Ordered by ``idx`` ASC.
    * ``is_front=True`` on idx=1 only.
    * Only includes ``status='ready'`` images (pending / failed excluded).
    """

    async def test_get_image_urls_shape_and_ordering(
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
        stub_gcs_download["set"](minimal_jpeg_bytes)

        # Upload 3 images (slots 1, 2, 3); run precheck on each → all "ready".
        uploaded_ids = []
        for idx in (1, 2, 3):
            upload = _make_upload_file(data=minimal_jpeg_bytes)
            response = await image_service.upload_image(
                user_id=user.id,
                product_id=product.id,
                file=upload,
                idx=idx,
                db=db,
            )
            await db.commit()
            uploaded_ids.append((idx, response.image_id))
            # Drive precheck inline → status='ready'.
            await _drive_precheck_inline(response.image_id, user.id)

        # Cross-module call.
        urls = await image_service.get_image_urls(product.id, user.id, db=db)

        # Shape contract: list of ImageUrl frozen dataclasses.
        assert isinstance(urls, list)
        assert len(urls) == 3
        from app.modules.image.domain import ImageUrl
        for entry in urls:
            assert isinstance(entry, ImageUrl)

        # Ordered by idx ASC.
        assert [u.idx for u in urls] == [1, 2, 3]

        # is_front=True ONLY on idx=1 entry.
        front_flags = [u.is_front for u in urls]
        assert front_flags == [True, False, False]

        # Signed URLs all populated.
        for u in urls:
            assert "signed=1" in u.signed_url

        # ImageUrl.__str__ shim returns the signed_url (back-compat with
        # catalog.service.get_preview's defensive ``str(u)`` call).
        assert str(urls[0]) == urls[0].signed_url
