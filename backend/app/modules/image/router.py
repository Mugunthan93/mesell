"""``image`` router — 2 endpoint handlers per §11.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``POST /api/v1/products/{id}/images`` — upload image (§11.B.1)
   - multipart/form-data: ``file`` (UploadFile JPEG), ``idx`` (1-4)
   - 202 ACCEPTED — ``ImageUploadResponse`` with Celery task id
   - 10/min/user rate limit (bandwidth-heavy)
2. ``GET  /api/v1/products/{id}/images`` — list product images (§11.B.2)
   - 200 OK — ``ImagesListResponse`` (length 0-4)
   - per-IP fallback only — polling endpoint

Route invariants (§11.B + §4.B)
-------------------------------
* Every handler is ``async def``.
* Every handler requires ``Depends(get_current_user)`` — routes NEVER
  decode JWT.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and
  forwards as kwarg.
* NO business logic inlined — orchestration only.
* NO error-envelope formatting — exceptions raised are ``ImageError``
  subclasses which ``core/errors.register_error_handlers`` (§4.F)
  translates into the locked envelope.

Audit posture (§11.J)
---------------------
* POST /products/{id}/images → ``image.upload.received`` (file bytes
  NEVER logged per `MVP_ARCH §11.9`; only path metadata).
* GET  /products/{id}/images → NONE (read-only polling).
* image.precheck Celery task → ``image.precheck.completed`` emitted
  via direct ORM write inside :mod:`.tasks`.

Rate-limit decorators (§4.G + §4.E)
-----------------------------------
* POST /products/{id}/images — 10/min/user (``image_upload``).
* GET  /products/{id}/images — 600/h per-IP only (polling).

Plan-guard NOT participating per §11.J — the 4-slot uniform rule is
a structural DB constraint per `MVP_ARCH §2.5`.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.image import service as image_service
from app.modules.image.exceptions import InvalidImageIdxError
from app.modules.image.schemas import (
    ImageUploadResponse,
    ImagesListResponse,
)
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["image"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products/{id}/images  — §11.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products/{id}/images",
    response_model=ImageUploadResponse,
    status_code=202,
    summary="Upload an image to a product slot (Feature 5)",
    description=(
        "Persists the JPEG to GCS and enqueues the 5-step precheck pipeline. "
        "Returns 202 ACCEPTED; the client polls GET /products/{id}/images "
        "until status='ready' or 'failed_precheck'."
    ),
)
@rate_limit(scope="image_upload", limit=10, window=60)
@audit_event("image.upload.received")
async def upload_image(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="JPEG image, max 10 MB.")],
    idx: Annotated[int, Form(description="Image slot index 1-4.")] = 0,
) -> ImageUploadResponse:
    """§11.B.1 — POST /products/{id}/images.

    Status codes:

    * 202 — upload persisted + precheck Celery task enqueued.
    * 400 — invalid format / too large / invalid idx.
    * 401 — missing or invalid JWT.
    * 404 — product does not exist OR cross-tenant
      (``catalog.product.not_found``).
    * 409 — slot already occupied (``image.slot.occupied``).
    """
    # ── Feature flag guard (FEATURE_PLAN.md D2) ──────────────────────────
    # Request-time check (reads settings inside handler, NOT at import time)
    # per the smart-picker pattern in category/router.py:117.
    if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image upload is disabled in this environment",
        )
    # FastAPI's Form() default cannot enforce the [1,4] range
    # declaratively (Pydantic schema lives in the Form arg, not a model).
    # Fail-fast at the route boundary so the service does not waste a
    # round-trip into catalog.assert_product_ownership before the
    # validation error fires.
    if idx not in (1, 2, 3, 4):
        raise InvalidImageIdxError()

    return await image_service.upload_image(
        user.user_id, id, file=file, idx=idx, db=db
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /products/{id}/images  — §11.B.2
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/images",
    response_model=ImagesListResponse,
    summary="List images for a product with precheck status",
    description=(
        "Returns up to 4 images for the product, ordered by slot index, "
        "with signed GCS URLs (TTL 1h) and verbatim precheck JSON for "
        "client-side rendering."
    ),
)
@rate_limit(scope="image_list", limit=600, window=3600)
async def list_images(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImagesListResponse:
    """§11.B.2 — GET /products/{id}/images.

    Status codes: 200, 401, 404 (``catalog.product.not_found``).

    No audit event per §11.J (read-only polling — would flood
    ``audit_events``).
    """
    # ── Feature flag guard (FEATURE_PLAN.md D2) ──────────────────────────
    # GET is read-only — sellers may have legacy images.  Return an empty
    # list (200) rather than 404 when the flag is OFF.
    if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
        return ImagesListResponse(images=[])
    return await image_service.list_images(user.user_id, id, db=db)


__all__ = ["router"]
