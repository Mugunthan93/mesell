"""``image`` service — public business logic per §11.C (LOCKED 2026-06-05).

Per BACKEND_ARCHITECTURE.md §11.C, this module exposes 6 public
async functions:

Route-backing (2)
-----------------
* :func:`upload_image`    — POST /api/v1/products/{id}/images   (§11.B.1)
* :func:`list_images`     — GET  /api/v1/products/{id}/images   (§11.B.2)

Cross-module surfaces (4)
-------------------------
* :func:`get_image_urls`        — called by catalog.service.get_preview per §10.B.4
* :func:`get_image_bytes`       — called by export.service for ZIP packaging per §14
* :func:`write_precheck_result` — called by image.tasks worker per §11.E
* :func:`summary`               — OPTIONAL — called by dashboard.service per §13

Cross-cutting integration (§11.J)
---------------------------------
* Tenancy: every read/write goes through the repository, which uses
  :func:`scope_to_user` against ``products.user_id`` (§11-IMAGE-D1
  workaround for missing ``user_id`` column on ``product_images``).
* Plan-guard: NOT participating per §11.J — the 4-slot uniform rule
  is the structural DB-level limit (`UNIQUE(product_id, order_idx)` +
  `CHECK (order_idx BETWEEN 1 AND 4)` per `MVP_ARCH §2.5`).
* AI Ops: NOT invoked from this module — the watermark Gemini call
  fires ONLY inside :mod:`.tasks` (Celery worker context).
* Cache: NOT participating per §11.J — signed URLs are 1h TTL and
  per-product image data has low cache hit rate.
* Audit: ``image.precheck.completed`` audit row is written by
  :mod:`.tasks` via direct ORM write per §11.J + §15.E exception list.

DECISION FLAG §11-IMAGE-D3 (informational)
------------------------------------------
``catalog.service.get_preview`` line ~830 does
``tuple(str(u) for u in urls)`` against this surface's return list.
The catalog code expected stringifiable values; we satisfy this via
:meth:`ImageUrl.__str__` returning the bare ``signed_url`` (see
``.domain`` module).  A future cleanup may update catalog to use
``u.signed_url`` explicitly.
"""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import gcs as gcs_adapter
from app.modules.catalog import service as catalog_service
from app.modules.image import repository as image_repo
from app.modules.image.domain import (
    ImageStatusSummary,
    ImageUrl,
)
from app.modules.image.exceptions import (
    ImageNotFoundError,
    ImageSlotOccupiedError,
    ImageTooLargeError,
    InvalidImageFormatError,
    InvalidImageIdxError,
)
from app.modules.image.schemas import (
    ImageSummary,
    ImageUploadResponse,
    ImagesListResponse,
)
from app.shared.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB per CLAUDE.md API design
_ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/jpg"})
_ALLOWED_IDX: frozenset[int] = frozenset({1, 2, 3, 4})


def _gcs_path_for(user_id: UUID, product_id: UUID, idx: int) -> str:
    """Compose the locked GCS path per §6.D + `MVP_ARCH §10.8`.

    Shape::

        meesell-images/{user_id}/{product_id}/{idx}.jpg

    The leading bucket-segment ``meesell-images/`` is the §6.D path
    convention — NOT the GCS bucket name (which is ``settings.GCS_BUCKET``
    and applied by the adapter).  The user_id segment is the
    defence-in-depth tenancy seam per `MVP_ARCH §10.8`.
    """
    return f"meesell-images/{user_id}/{product_id}/{idx}.jpg"


def _read_pillow_metadata(data: bytes) -> tuple[int, int, str]:
    """Read width / height / color_space via Pillow in-memory.

    Used by :func:`upload_image` step 3 to capture metadata BEFORE the
    GCS write — the in-route read is lightweight (BytesIO + Image.open
    header parse) and lets us reject malformed JPEGs early.

    Returns ``(width, height, color_space)``.  Caller wraps
    :class:`InvalidImageFormatError` on any Pillow error.
    """
    # Imported lazily so non-image code paths do not pay the import cost.
    from io import BytesIO

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(data)) as img:
            # ``img.mode`` returns "RGB" | "CMYK" | "L" (grayscale) | "RGBA" | ...
            # Map "L" → "Gray" per §11.G PrecheckResult contract; other
            # exotic modes pass through verbatim (Pillow returns short
            # strings; ``color_space VARCHAR(8)`` per `MVP_ARCH §2.5`).
            raw_mode = img.mode
            if raw_mode == "L":
                color_space = "Gray"
            else:
                color_space = raw_mode[:8]  # truncate to column width
            width, height = img.size
        return width, height, color_space
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageFormatError() from exc


# ─────────────────────────────────────────────────────────────────────────────
# 1. upload_image — backs POST /api/v1/products/{id}/images
# ─────────────────────────────────────────────────────────────────────────────
async def upload_image(
    user_id: UUID,
    product_id: UUID,
    file: UploadFile,
    idx: int,
    *,
    db: AsyncSession,
) -> ImageUploadResponse:
    """§11.B.1 — POST /api/v1/products/{id}/images.

    8-step locked flow per §11.B.1:

    1. ``catalog.service.assert_product_ownership(product_id, user_id)``
       — raises 404 ``catalog.product.not_found`` for non-existent /
       cross-tenant / soft-deleted.  FIRST call site; bytes are not
       consumed yet.
    2. Validate idx is in {1,2,3,4}; raise 400 ``InvalidImageIdxError``.
    3. Read file bytes + validate MIME + size; raise 400
       ``InvalidImageFormatError`` / ``ImageTooLargeError``.
    4. Read Pillow metadata (width, height, color_space).
    5. Check slot occupancy via :func:`repository.find_by_slot`; raise
       409 ``ImageSlotOccupiedError`` if occupied.
    6. ``adapters.gcs.upload_bytes`` to locked path.
    7. Repository ``insert`` with status='pending', precheck_jsonb={}.
    8. Enqueue Celery task ``image.precheck`` via .delay(image_id,
       user_id); return 202 ``ImageUploadResponse``.
    """
    # 1. Ownership gate — FIRST action; bytes not yet read.
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)

    # 2. Validate idx.
    if idx not in _ALLOWED_IDX:
        raise InvalidImageIdxError()

    # 3. Read bytes + validate MIME + size.
    # ``content_type`` is the multipart-declared MIME; ``file.read()``
    # streams in-memory.  V1 cap is 10 MB so memory is bounded.
    declared_mime = (file.content_type or "").lower()
    if declared_mime not in _ALLOWED_MIME_TYPES:
        raise InvalidImageFormatError()

    file_bytes = await file.read()
    if not isinstance(file_bytes, (bytes, bytearray)):
        # FastAPI's UploadFile.read should return bytes — defensive.
        raise InvalidImageFormatError()

    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise ImageTooLargeError()

    file_bytes = bytes(file_bytes)

    # 4. Pillow metadata — raises InvalidImageFormatError on malformed file.
    width, height, color_space = _read_pillow_metadata(file_bytes)

    # 5. Slot uniqueness check.
    existing = await image_repo.find_by_slot(db, user_id, product_id, idx)
    if existing is not None:
        raise ImageSlotOccupiedError()

    # 6. GCS write — §6.D path convention.
    gcs_path = _gcs_path_for(user_id, product_id, idx)
    await gcs_adapter.upload_bytes(
        path=gcs_path,
        data=file_bytes,
        content_type="image/jpeg",
    )

    # 7. Repository insert.
    image = await image_repo.insert(
        db,
        user_id=user_id,
        product_id=product_id,
        gcs_path=gcs_path,
        idx=idx,
        width=width,
        height=height,
        color_space=color_space,
    )

    # 8. Celery enqueue.  Lazy import avoids a circular at module-import
    # time (tasks.py imports service for write_precheck_result).
    from app.modules.image.tasks import image_precheck_task

    async_result = image_precheck_task.delay(str(image.id), str(user_id))
    enqueued_task_id = str(async_result.id) if async_result is not None else ""

    return ImageUploadResponse(
        image_id=image.id,
        gcs_path=gcs_path,
        status="pending",
        idx=idx,
        enqueued_task_id=enqueued_task_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. list_images — backs GET /api/v1/products/{id}/images
# ─────────────────────────────────────────────────────────────────────────────
async def list_images(
    user_id: UUID,
    product_id: UUID,
    *,
    db: AsyncSession,
) -> ImagesListResponse:
    """§11.B.2 — GET /api/v1/products/{id}/images.

    Flow:

    1. ``catalog.service.assert_product_ownership(product_id, user_id)``.
    2. Repository ``find_by_product`` — non-deleted rows ordered by idx.
    3. For each row, generate a 1-hour signed GCS URL via
       :func:`adapters.gcs.generate_signed_url` per §6.D.
    4. Compose response with verbatim ``precheck_jsonb``.
    """
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)

    images = await image_repo.find_by_product(db, user_id, product_id)

    summaries: list[ImageSummary] = []
    for img in images:
        signed_url = await gcs_adapter.generate_signed_url(
            path=img.gcs_path,
            ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS,
            method="GET",
        )
        summaries.append(
            ImageSummary(
                image_id=img.id,
                idx=img.order_idx,
                status=img.status if img.status in ("pending", "ready", "failed_precheck") else "pending",
                signed_url=signed_url,
                precheck_jsonb=dict(img.precheck_jsonb or {}),
                is_front=bool(img.is_front),
                width=img.width,
                height=img.height,
                color_space=img.color_space,
                created_at=img.created_at,
            )
        )

    return ImagesListResponse(images=summaries)


# ─────────────────────────────────────────────────────────────────────────────
# 3. get_image_urls — cross-module call from catalog.service.get_preview
# ─────────────────────────────────────────────────────────────────────────────
async def get_image_urls(
    product_id: UUID,
    user_id: UUID,
    *,
    db: AsyncSession,
) -> list[ImageUrl]:
    """§11.C — called by ``catalog.service.get_preview`` per §10.B.4 + §2.D.

    Returns signed URLs ONLY for ``status='ready'`` images.  The list
    is ordered by ``idx`` ASC with ``is_front=True`` set on the idx=1
    entry per §11.K integration test #3.

    Skips ``pending`` and ``failed_precheck`` images — the preview
    should only show seller-visible "good" images.
    """
    images = await image_repo.find_by_product(db, user_id, product_id)
    result: list[ImageUrl] = []
    for img in images:
        if img.status != "ready":
            continue
        signed_url = await gcs_adapter.generate_signed_url(
            path=img.gcs_path,
            ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS,
            method="GET",
        )
        result.append(
            ImageUrl(
                image_id=img.id,
                idx=img.order_idx,
                signed_url=signed_url,
                is_front=bool(img.is_front),
            )
        )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. get_image_bytes — cross-module call from export.service
# ─────────────────────────────────────────────────────────────────────────────
async def get_image_bytes(
    image_id: UUID,
    user_id: UUID,
    *,
    db: AsyncSession,
) -> bytes:
    """§11.C — called by ``export.service`` for ZIP packaging per §14.

    Downloads raw bytes from GCS — does NOT generate a signed URL.
    The export pipeline streams these bytes into the in-process ZIP
    rather than handing the seller a presigned URL list (the export
    is consumed by Meesho via XLSX + ZIP, not by the seller's browser).

    Raises :class:`ImageNotFoundError` (404 ``image.not.found``) if the
    image does not exist OR is owned by another user OR is
    soft-deleted.  Same leak protection as
    :class:`catalog.exceptions.ProductNotFoundError`.
    """
    image = await image_repo.find_by_id(db, user_id, image_id)
    if image is None:
        raise ImageNotFoundError()
    return await gcs_adapter.download_bytes(path=image.gcs_path)


# ─────────────────────────────────────────────────────────────────────────────
# 5. write_precheck_result — cross-module call from image.tasks worker
# ─────────────────────────────────────────────────────────────────────────────
async def write_precheck_result(
    image_id: UUID,
    user_id: UUID,
    precheck_jsonb: dict,
    status: Literal["ready", "failed_precheck"],
    *,
    db: AsyncSession,
) -> None:
    """§11.C — called by :mod:`image.tasks` Celery worker per §11.E step 8.

    Atomic single-row UPDATE of ``product_images.precheck_jsonb`` +
    ``status``.  No service-level audit write — the worker emits the
    ``image.precheck.completed`` audit row directly per §11.J + §15.E
    (locked exception to the audit_mw post-commit pattern; the worker
    has no request-close hook).

    Tenancy: repository :func:`update_precheck_result` re-scopes through
    ``products.user_id`` — even though the worker context trusts the
    ``user_id`` from the task payload, the join is the structural
    backstop.
    """
    try:
        await image_repo.update_precheck_result(
            db,
            user_id=user_id,
            image_id=image_id,
            precheck_jsonb=precheck_jsonb,
            status=status,
        )
    except LookupError as exc:
        # Repository raises LookupError when the image is not found
        # under the user's scope.  Translate to the canonical 404 even
        # though the worker is the only caller — keeps the error model
        # consistent for future re-use.
        raise ImageNotFoundError() from exc


# ─────────────────────────────────────────────────────────────────────────────
# 6. summary — OPTIONAL cross-module call from dashboard.service
# ─────────────────────────────────────────────────────────────────────────────
async def summary(
    user_id: UUID,
    product_ids: list[UUID],
    *,
    db: AsyncSession,
) -> dict[UUID, ImageStatusSummary]:
    """§11.C — OPTIONAL surface for ``dashboard.service.summary`` per §13.

    Returns per-product image status summaries with the front-image
    signed URL (when slot 1 is ready).  The repository returns the
    front-image PATH; this surface promotes path → signed URL.
    """
    if not product_ids:
        return {}

    raw = await image_repo.summarize_by_products(db, user_id, product_ids)

    # Promote front_image PATH → signed URL.  Repository returns
    # ImageStatusSummary with ``front_image_signed_url`` carrying the
    # path; we re-wrap with the actual URL here at the service boundary.
    promoted: dict[UUID, ImageStatusSummary] = {}
    for pid, partial in raw.items():
        front_url: str | None = None
        if partial.front_image_signed_url:
            front_url = await gcs_adapter.generate_signed_url(
                path=partial.front_image_signed_url,
                ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS,
                method="GET",
            )
        promoted[pid] = ImageStatusSummary(
            product_id=partial.product_id,
            total_images=partial.total_images,
            ready_count=partial.ready_count,
            failed_count=partial.failed_count,
            pending_count=partial.pending_count,
            front_image_signed_url=front_url,
        )
    return promoted


__all__ = [
    "get_image_bytes",
    "get_image_urls",
    "list_images",
    "summary",
    "upload_image",
    "write_precheck_result",
]
