"""Image-module unit tests — §11.K units 1-5.

Per BACKEND_ARCHITECTURE.md §11.K:

  TestOwnershipGateEnforcement   — 1 method (cross-tenant → 404)
  TestFileValidation             — 3 methods (non-JPEG / too-large / invalid-idx)
  TestSlotUniqueness             — 1 method (409 image.slot.occupied)
  TestGcsPathConstruction        — 1 method (path exactly matches §6.D + MVP_ARCH §10.8)
  TestCeleryTaskEnqueue          — 1 method (image_precheck_task.delay called correctly)

Tests run against the ephemeral test DB (top-level conftest's
``db_session``; reset per test) with mocked GCS + Celery so they do
NOT depend on live infra.
"""

from __future__ import annotations

import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.image import service as image_service
from app.modules.image.exceptions import (
    ImageSlotOccupiedError,
    ImageTooLargeError,
    InvalidImageFormatError,
    InvalidImageIdxError,
)

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _make_upload_file(
    *, data: bytes, content_type: str = "image/jpeg", filename: str = "img.jpg"
) -> UploadFile:
    """Build a FastAPI UploadFile suitable for service-level invocation.

    The Starlette UploadFile constructor accepts a ``file`` (a
    BytesIO) plus headers carrying ``content-type``.
    """
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Unit 1: Ownership gate enforcement
# ─────────────────────────────────────────────────────────────────────────────
class TestOwnershipGateEnforcement:
    """§11.K unit #1 — POST to a product owned by another user MUST 404
    BEFORE any GCS bytes are read.

    Verifies ``catalog.service.assert_product_ownership`` is the FIRST
    call site in :func:`image.service.upload_image`.
    """

    async def test_cross_tenant_product_raises_404(
        self,
        db,
        user,
        other_product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        with pytest.raises(ProductNotFoundError):
            await image_service.upload_image(
                user_id=user.id,
                product_id=other_product.id,  # owned by other_user
                file=upload,
                idx=1,
                db=db,
            )
        # GCS upload MUST NOT have been called — ownership gate fires first.
        assert stub_gcs_upload["calls"] == []
        assert stub_celery_delay["calls"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Unit 2: File validation (3 methods)
# ─────────────────────────────────────────────────────────────────────────────
class TestFileValidation:
    """§11.K unit #2 — 3 separate validations, each its own test method.

    * non-JPEG MIME    → 400 ``validation.image.invalid_format``
    * size > 10 MB     → 400 ``validation.image.too_large``
    * idx not in [1,4] → 400 ``validation.image.invalid_idx``
    """

    async def test_non_jpeg_mime_raises_invalid_format(
        self,
        db,
        user,
        product,
        small_png_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        upload = _make_upload_file(
            data=small_png_bytes, content_type="image/png", filename="x.png"
        )
        with pytest.raises(InvalidImageFormatError):
            await image_service.upload_image(
                user_id=user.id,
                product_id=product.id,
                file=upload,
                idx=1,
                db=db,
            )
        # Never hits GCS.
        assert stub_gcs_upload["calls"] == []

    async def test_oversize_payload_raises_too_large(
        self,
        db,
        user,
        product,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        # 10 MB + 1 byte — should reject before GCS.
        over_limit = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024)
        upload = _make_upload_file(data=over_limit)
        with pytest.raises(ImageTooLargeError):
            await image_service.upload_image(
                user_id=user.id,
                product_id=product.id,
                file=upload,
                idx=1,
                db=db,
            )
        assert stub_gcs_upload["calls"] == []

    async def test_invalid_idx_raises_invalid_idx(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        with pytest.raises(InvalidImageIdxError):
            await image_service.upload_image(
                user_id=user.id,
                product_id=product.id,
                file=upload,
                idx=5,
                db=db,
            )
        assert stub_gcs_upload["calls"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Unit 3: Slot uniqueness
# ─────────────────────────────────────────────────────────────────────────────
class TestSlotUniqueness:
    """§11.K unit #3 — POST with ``idx=2`` when a non-deleted image
    already occupies slot 2 → 409 ``ImageSlotOccupiedError``.
    """

    async def test_occupied_slot_raises_409(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        # First upload — happy path.
        first_upload = _make_upload_file(data=minimal_jpeg_bytes)
        await image_service.upload_image(
            user_id=user.id,
            product_id=product.id,
            file=first_upload,
            idx=2,
            db=db,
        )
        await db.commit()

        # Second upload to same slot — must 409.
        second_upload = _make_upload_file(data=minimal_jpeg_bytes)
        with pytest.raises(ImageSlotOccupiedError):
            await image_service.upload_image(
                user_id=user.id,
                product_id=product.id,
                file=second_upload,
                idx=2,
                db=db,
            )

        # Exactly one GCS upload + one enqueue from the first call.
        assert len(stub_gcs_upload["calls"]) == 1
        assert len(stub_celery_delay["calls"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Unit 4: GCS path construction
# ─────────────────────────────────────────────────────────────────────────────
class TestGcsPathConstruction:
    """§11.K unit #4 — confirm GCS path EXACTLY equals
    ``meesell-images/{user_id}/{product_id}/{idx}.jpg`` per §6.D +
    `MVP_ARCH §10.8`.

    Verified via mock ``adapters.gcs.upload_bytes`` assertion.
    """

    async def test_path_matches_locked_convention(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        await image_service.upload_image(
            user_id=user.id,
            product_id=product.id,
            file=upload,
            idx=3,
            db=db,
        )

        assert len(stub_gcs_upload["calls"]) == 1
        call = stub_gcs_upload["calls"][0]
        expected_path = f"meesell-images/{user.id}/{product.id}/3.jpg"
        assert call["path"] == expected_path
        assert call["content_type"] == "image/jpeg"
        # data_len should match the JPEG payload — non-zero + finite.
        assert 0 < call["data_len"] <= 10 * 1024 * 1024


# ─────────────────────────────────────────────────────────────────────────────
# Unit 5: Celery task enqueue
# ─────────────────────────────────────────────────────────────────────────────
class TestCeleryTaskEnqueue:
    """§11.K unit #5 — verify ``image_precheck_task.delay`` was called
    with ``(image_id, user_id)`` after a successful POST.
    """

    async def test_enqueue_called_with_image_id_and_user_id(
        self,
        db,
        user,
        product,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_celery_delay,
    ):
        upload = _make_upload_file(data=minimal_jpeg_bytes)
        response = await image_service.upload_image(
            user_id=user.id,
            product_id=product.id,
            file=upload,
            idx=1,
            db=db,
        )

        assert len(stub_celery_delay["calls"]) == 1
        call = stub_celery_delay["calls"][0]
        args = call["args"]
        # Service serialises UUIDs to strings before .delay (Celery JSON safety).
        assert len(args) == 2
        assert str(response.image_id) == str(args[0])
        assert str(user.id) == str(args[1])

        # Response contract.
        assert response.status == "pending"
        assert response.idx == 1
        assert response.enqueued_task_id.startswith("fake-task-")
