"""svc-export router — 2 endpoint handlers per §3.B + §14.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``POST /api/v1/products/{product_id}/export-xlsx`` — Initiate Meesho XLSX
   export for a product (§14.B.1).
   - Request body: ``ExportRequest`` (format=xlsx_only|xlsx_with_images).
   - 202 ACCEPTED — ``ExportInitiatedResponse`` with Celery task id.
   - 10/h/user rate limit (bandwidth + CPU-heavy operation).

2. ``GET  /api/v1/exports/{export_id}`` — Poll export status + download URLs
   (§14.B.2).
   - 200 OK — ``ExportResponse`` (status, signed URLs when ready, error when
     failed).
   - Per-IP only rate limit (polling endpoint; frontend uses exponential
     backoff per FRONTEND_ARCH §11).

Route invariants (§14.B + §4.B)
--------------------------------
* Every handler is ``async def``.
* Every handler requires ``Depends(get_current_user)`` — routes NEVER decode
  JWT themselves.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and forwards
  as kwarg.
* NO business logic inlined — every handler calls ``service.<method>`` only.
* NO error-envelope formatting — exceptions raised are ``ExportError``
  subclasses (or ``catalog.exceptions.ProductNotFoundError`` bubbled from the
  cross-module ownership gate) which ``core/errors.register_error_handlers``
  (§4.F) translates into the locked envelope.

Audit posture (§14.J + §4.G)
-----------------------------
* POST /products/{product_id}/export-xlsx → ``export.initiated`` emitted by
  ``audit_mw`` post-handler on 2xx (NOT an explicit ``@audit_event`` decorator
  — middleware observes the 2xx POST response automatically per §4.G).
  Worker emits ``export.completed`` / ``export.failed`` via direct ORM write.
* GET /exports/{export_id} → NONE (read-only polling — documented absence per
  §14.J + §4.G read-flood rule).

Rate-limit decorators (§4.E + §14.J)
--------------------------------------
* POST /products/{product_id}/export-xlsx — ``@rate_limit(scope="export_initiate",
  limit=10, window=3600)`` per-user (keyed automatically via
  ``request.state.user_id`` from ``TenancyContextMiddleware``).
* GET  /exports/{export_id} — per-IP fallback only (``RateLimitMiddleware``
  120/min DDoS floor); NO ``@rate_limit`` decorator per §14.J.

Plan-guard
----------
NOT participating in V1 per §14.A / §14.J. Exports are core seller value.

/internal/* routes
------------------
ZERO. Export is a leaf consumer — it calls other services via HTTP shims
(extracted_clients) but exposes NO /internal/* routes of its own.
The svc-export OpenAPI contains exactly 2 /api/v1 routes.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.rate_limit_mw import rate_limit
from app import service as export_service
from app.schemas import (
    ExportInitiatedResponse,
    ExportRequest,
    ExportResponse,
)
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["export"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products/{product_id}/export-xlsx — §14.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products/{product_id}/export-xlsx",
    response_model=ExportInitiatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate Meesho XLSX export for a product (Feature 9)",
    description=(
        "Validates product ownership + readiness + front-image availability, "
        "inserts an exports row with status='pending', and enqueues the "
        "9-step Celery pipeline (task name 'export.xlsx'). "
        "Poll GET /exports/{export_id} until status='ready' or 'failed'. "
        "Rate limit: 10 requests/hour per user."
    ),
)
@rate_limit(scope="export_initiate", limit=10, window=3600)
async def initiate_export(
    product_id: UUID,
    payload: ExportRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportInitiatedResponse:
    """§14.B.1 — POST /api/v1/products/{product_id}/export-xlsx.

    Status codes:

    * 202 — export row inserted + Celery task enqueued.
    * 400 — invalid format (Pydantic ``extra="forbid"`` + Literal catches
      non-enumerated format values before this handler runs).
    * 401 — JWT missing or invalid (handled by §4.A auth middleware).
    * 404 — product does not exist OR cross-tenant
      (``catalog.product.not_found`` from ``assert_product_ownership``).
    * 422 — product ``status != 'ready'``
      (``export.product_not_ready``) or front image missing when
      ``format='xlsx_with_images'`` (``export.front_image_missing``).
    """
    return await export_service.initiate_export(
        user_id=user.user_id,
        product_id=product_id,
        request=payload,
        db=db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /exports/{export_id} — §14.B.2
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/exports/{export_id}",
    response_model=ExportResponse,
    summary="Poll export status and retrieve download URLs (Feature 9)",
    description=(
        "Returns the current status of the export pipeline. "
        "When status='ready', ``xlsx_signed_url`` (and ``zip_signed_url`` "
        "for xlsx_with_images format) are populated with fresh GCS signed URLs "
        "valid for 1 hour — re-poll to refresh expired URLs. "
        "When status='failed', ``error_code`` and ``error_message`` are set. "
        "No audit event (read-only polling — §14.J)."
    ),
)
async def get_export(
    export_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportResponse:
    """§14.B.2 — GET /api/v1/exports/{export_id}.

    Status codes:

    * 200 — export found (any status: pending / ready / failed).
    * 401 — JWT missing or invalid.
    * 404 — export does not exist OR cross-tenant
      (``export.not_found``; the repository's ``scope_to_user`` filter
      conflates the two per §4.C privacy posture).
    """
    return await export_service.get_export(
        user_id=user.user_id,
        export_id=export_id,
        db=db,
    )


__all__ = ["router"]
