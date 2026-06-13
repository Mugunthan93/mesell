"""``image`` Pydantic v2 request/response models per §11.F (LOCKED 2026-06-05).

EXTRACTION NOTE (MS Sub-Plan C — spec §1 B1)
============================================
Vendored verbatim from the monolith ``app.modules.image.schemas``.  No
intra-``app`` imports (pydantic only) so ZERO import-line changes were needed.

NOTE (B2 hand-off — FROZEN SHIM_CONTRACT §2.6): the ``/internal`` list-images
shim (built by api-routes-builder) serialises :class:`ImageSummary`.  The
FROZEN export-consumer contract reads keys ``image_id, idx, status,
signed_url, precheck_jsonb`` — all present as field names below.  The extra
fields (``is_front``, ``width``, ``height``, ``color_space``, ``created_at``)
are additive and tolerated by the export consumer (it reads only the 5 frozen
keys).  Do NOT rename the 5 frozen field names.

Wire shapes for the 2 endpoints in :mod:`.router` (owned by api-routes-builder):

* :class:`ImageUploadResponse` — 202 ACCEPTED body for POST /products/{id}/images
* :class:`ImageSummary`        — single image entry inside :class:`ImagesListResponse`
* :class:`ImagesListResponse`  — 200 OK body for GET /products/{id}/images

Request shape is ``multipart/form-data`` (``file: UploadFile`` + ``idx: int``)
per CLAUDE.md API design rule — the router receives these via FastAPI's
``UploadFile`` + ``Form()`` dependencies, NOT a Pydantic model.  See §11.B.1.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImageUploadResponse(BaseModel):
    """202 ACCEPTED response body per §11.B.1.

    Returned synchronously after the GCS write + ``product_images`` row
    insert + Celery task enqueue.  The 5-step precheck pipeline runs
    asynchronously; the client polls
    ``GET /api/v1/products/{id}/images`` until ``status == "ready"``.

    ``enqueued_task_id`` is informational only — the polling endpoint is
    the canonical way to discover precheck completion; the Celery task
    id is exposed for client-side correlation when debugging.
    """

    model_config = ConfigDict(extra="forbid")

    image_id: UUID
    gcs_path: str = Field(
        description=(
            "GCS object path (no scheme), e.g. "
            "'meesell-images/{user_id}/{product_id}/{idx}.jpg' per §6.D."
        ),
    )
    status: Literal["pending"]
    idx: int = Field(ge=1, le=4, description="1-4 slot index")
    enqueued_task_id: str = Field(description="Celery task id for client-side correlation")


class ImageSummary(BaseModel):
    """Single image entry inside :class:`ImagesListResponse`.

    Carries:

    * domain identifiers (``image_id``, ``idx``),
    * lifecycle status (``status``, ``created_at``),
    * the seller-facing presigned URL (``signed_url``, TTL 1h),
    * the verbatim precheck JSON (``precheck_jsonb``) so the frontend
      can render per-step pass/fail without a second roundtrip,
    * cached Pillow-read metadata (``width``, ``height``, ``color_space``).
    """

    model_config = ConfigDict(extra="forbid")

    image_id: UUID
    idx: int = Field(ge=1, le=4)
    status: Literal["pending", "ready", "failed_precheck"]
    signed_url: str = Field(description="GCS signed URL, TTL 1 h per §6.D + MVP_ARCH §10.8")
    precheck_jsonb: dict = Field(
        default_factory=dict,
        description=(
            "Structured 5-step precheck result — 5 keys: "
            "jpeg_valid, color_space, resolution_pass, white_background, watermark_check."
        ),
    )
    is_front: bool = Field(description="True iff idx == 1 — generated column per MVP_ARCH §2.5")
    width: int | None = None
    height: int | None = None
    color_space: str | None = Field(
        default=None,
        description="'RGB' | 'CMYK' | 'Gray' — Pillow ``Image.mode``",
    )
    created_at: datetime


class ImagesListResponse(BaseModel):
    """200 OK response body for GET /api/v1/products/{id}/images per §11.B.2.

    ``images`` is the per-product list ordered by ``idx`` ASC, length 0-4
    per `MVP_ARCH §0` premise #3 (4-slot uniform rule).
    """

    model_config = ConfigDict(extra="forbid")

    images: list[ImageSummary] = Field(default_factory=list)


__all__ = [
    "ImageSummary",
    "ImageUploadResponse",
    "ImagesListResponse",
]
