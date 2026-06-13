"""svc-image router — 2 public endpoint handlers + 1 internal callee shim.

Public endpoints (§11.B, verbatim from monolith backend/app/modules/image/router.py)
---------------------------------------------------------------------------------------
1. ``POST /api/v1/products/{id}/images`` — upload image (§11.B.1)
   Source: monolith router.py:75-124 (line-for-line preservation of
   decorators, status codes, auth deps, rate-limit, audit, feature flag, idx
   fast-fail, and service call shape).

   - multipart/form-data: ``file`` (UploadFile JPEG), ``idx`` (1-4 Form int)
   - 202 ACCEPTED — ``ImageUploadResponse`` with Celery task id
   - 10/min/user ``@rate_limit(scope="image_upload", limit=10, window=60)``
   - ``@audit_event("image.upload.received")`` (file bytes NEVER logged)
   - Feature flag guard (``settings.FEATURE_IMAGE_PRECHECK_ENABLED``)
   - idx fast-fail BEFORE catalog round-trip (saves DB query)

2. ``GET /api/v1/products/{id}/images`` — list product images (§11.B.2)
   Source: monolith router.py:130-158 (line-for-line preservation).

   - 200 OK — ``ImagesListResponse`` (length 0-4, idx ASC)
   - 600/h per-IP fallback ``@rate_limit(scope="image_list", limit=600, window=3600)``
   - NO ``@audit_event`` (read-only polling — §11.J + §4.G read-flood rule)
   - Feature flag guard: when OFF returns ``ImagesListResponse(images=[])``

/internal/* callee shim (FROZEN SHIM_CONTRACT §2.6)
----------------------------------------------------
3. ``GET /internal/products/{product_id}/images?user_id={user_id}``
   — list-images shim consumed by svc-export.

   Per SHIM_CONTRACT_export_callees.md §2.6 (FROZEN 2026-06-12):
   * Path: ``/internal/products/{product_id}/images``
   * Method: GET
   * Path param: ``product_id`` (UUID)
   * Query param: ``user_id`` (UUID)
   * Service call: ``service.list_images(user_id=user_id, product_id=product_id, db=db)``
   * Response: ``ImagesListResponse`` — ``{ images: [ { image_id, idx, status,
     signed_url, precheck_jsonb } ] }``, idx ASC, len 0-4, signed_url TTL 1 h.
   * NOT Traefik-exposed (cluster-DNS only, no ingress annotation).
   * Auth: NO ``get_current_user`` dependency — cluster-internal network trust.
     The caller (svc-export worker) forwards ``X-Request-ID`` only; the JWT
     context-var may be empty on the worker path (per _transport.py:set_worker_context).
   * Error: 404 from ``service.list_images`` propagates (export caller wraps it
     in the front-image gate — consistent with in-process behaviour).

Route invariants (§11.B + §4.B)
---------------------------------
* Every public handler is ``async def``.
* Every public handler requires ``Depends(get_current_user)`` — routes NEVER
  decode JWT.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and forwards
  as kwarg.
* NO business logic inlined — service dispatch only.
* NO error-envelope formatting — exceptions are ``ImageError`` subclasses which
  ``core/errors.register_error_handlers`` (§4.F) translates.

Audit posture (§11.J)
----------------------
* POST /products/{id}/images → ``image.upload.received`` (explicit decorator).
* GET  /products/{id}/images → NONE (read-only).
* /internal/* route → NONE (internal infrastructure — no seller-facing event).

Router composition contract (for B1 main.py)
--------------------------------------------
Router object:   ``router``
Module path:     ``app.router``
Include call:    ``app.include_router(router)``
Mirrors:         svc-export precedent (``from app.router import router as ...``)
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
from app import service as image_service
from app.exceptions import InvalidImageIdxError
from app.schemas import (
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

# Separate internal router — NOT exposed via Traefik ingress (cluster-DNS only)
_internal_router = APIRouter(prefix="/internal", tags=["image-internal"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products/{id}/images  — §11.B.1
# Source: monolith backend/app/modules/image/router.py:75-124
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
# Source: monolith backend/app/modules/image/router.py:130-158
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


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /internal/products/{product_id}/images  — FROZEN §2.6 callee shim
# Consumed by: svc-export image_client.py:56 list_images()
# NOT Traefik-exposed — cluster-DNS only.
# ─────────────────────────────────────────────────────────────────────────────
@_internal_router.get(
    "/products/{product_id}/images",
    response_model=ImagesListResponse,
    summary="[INTERNAL] List images for svc-export callee shim (SHIM_CONTRACT §2.6)",
    description=(
        "Cluster-internal endpoint for svc-export. NOT exposed via Traefik. "
        "Accepts user_id as a query param (forwarded by the svc-export "
        "image_client shim). Returns the same ImagesListResponse shape as "
        "the public GET endpoint — images ordered idx ASC, signed GCS URLs "
        "TTL 1 h, len 0-4. Auth: internal-network trust (no JWT required)."
    ),
    include_in_schema=False,  # exclude from public OpenAPI docs
)
async def internal_list_images(
    product_id: UUID,
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImagesListResponse:
    """§2.6 frozen callee shim — GET /internal/products/{product_id}/images.

    Called pod-to-pod by svc-export's ``image_client.list_images()`` shim
    (``_transport.py`` worker path: JWT context-var is empty, X-Request-ID
    forwarded; internal-network trust posture per SHIM_CONTRACT §1).

    Wraps ``service.list_images`` — the service's assert_product_ownership
    shim call provides tenancy gating via the catalog ownership check.

    Status codes:

    * 200 — images returned (list may be empty — ``[]``).
    * 404 — product does not exist OR cross-tenant (``catalog.product.not_found``
      raised by ``service.list_images`` → ``assert_product_ownership``).
    """
    return await image_service.list_images(
        user_id=user_id,
        product_id=product_id,
        db=db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Compose: merge public + internal sub-router into the exported router object.
# B1's main.py calls: from app.router import router; app.include_router(router)
# Both public routes (/api/v1/products/{id}/images) and the internal route
# (/internal/products/{product_id}/images) will be reachable after one
# include_router call, because _internal_router is included into router here.
# ─────────────────────────────────────────────────────────────────────────────
router.include_router(_internal_router)


__all__ = ["router"]
