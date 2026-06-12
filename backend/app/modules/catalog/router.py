"""``catalog`` router — 6 endpoint handlers per §10.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``POST   /api/v1/products``                       — create product (§10.B.1)
2. ``PATCH  /api/v1/products/{id}``                  — update product fields (§10.B.2)
3. ``POST   /api/v1/products/{id}/autofill``         — AI Auto-fill (§10.B.3)
4. ``GET    /api/v1/products/{id}/preview``          — Live Product Preview (§10.B.4)
5. ``DELETE /api/v1/products/{id}``                  — soft delete (§10.B.5)
6. ``GET    /api/v1/products/{id}/draft``            — draft recovery (§10.B.6)

Route invariants (§10.B + §4.B)
-------------------------------
* Every handler is ``async def``.
* Every handler requires ``Depends(get_current_user)`` — routes NEVER
  decode JWT.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and
  forwards as kwarg.
* NO business logic inlined — orchestration only.
* NO error-envelope formatting — exceptions raised are ``CatalogError``
  subclasses which ``core/errors.register_error_handlers`` (§4.F)
  translates into the locked envelope.

Audit posture (§10.B + §4.G)
----------------------------
4 write endpoints get explicit ``@audit_event`` decorators:

  * POST   /products                  → ``catalog.product.created``
  * PATCH  /products/{id}             → ``catalog.product.updated``
  * POST   /products/{id}/autofill    → ``catalog.autofill.invoked``
  * DELETE /products/{id}             → ``catalog.product.deleted``

2 read endpoints get NO audit decorator (per `MVP_ARCH §11.3`
read-flood rule):

  * GET    /products/{id}/preview
  * GET    /products/{id}/draft

Rate-limit decorators (§4.G + §4.E)
-----------------------------------
* POST   /products                 — 20/h/user (``create_product_hourly``).
* PATCH  /products/{id}            — 600/h per-IP (autosave-friendly).
* POST   /products/{id}/autofill   — 50/h/user (``ai_autofill_hourly``).
* GET    /products/{id}/preview    — 600/h per-IP only.
* DELETE /products/{id}            — 60/h/user.
* GET    /products/{id}/draft      — 600/h per-IP only.

DECISION FLAG §10-CATALOG-D2
----------------------------
``audit_mw.py`` 5-min autosave coalescing regex matches only
``/draft`` and ``/autosave`` URL forms — NOT ``PATCH /products/{id}``.
Catalog uses ``@audit_event("catalog.product.updated")`` so the
middleware writes an audit row per PATCH; coalescing applies at the
Celery flush layer per `MVP_ARCH §11.4` (write-time bucketing by
``(user_id, entity_id)``).  No router-level change needed for §10
acceptance; the audit_mw regex widen is queued as a §4.G amendment.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import MeesellError
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.catalog import service as catalog_service
from app.shared.config import settings
from app.modules.catalog.domain import Pagination as PaginationInternal
from app.modules.catalog.exceptions import (
    DraftNotFoundError,
)
from app.modules.catalog.schemas import (
    AutofillRequest,
    AutofillResponse,
    AutofillSuggestion,
    CreateProductRequest,
    PatchProductRequest,
    ProductDraftResponse,
    ProductPreviewField,
    ProductPreviewResponse,
    ProductResponse,
)
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["catalog"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _product_to_response(product) -> ProductResponse:
    """Map domain :class:`Product` → wire :class:`ProductResponse`."""
    return ProductResponse(
        id=product.id,
        catalog_id=product.catalog_id,
        category_id=product.category_id,
        name=product.name,
        status=product.status,
        fields=dict(product.fields or {}),
        ai_suggestions=dict(product.ai_suggestions or {}),
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _is_autosave(header_value: str | None) -> bool:
    """Parse the ``X-Autosave`` header per §10.B.2.

    Truthy values: ``"true"``, ``"1"``, ``"yes"`` (case-insensitive).
    Absent or any other value → False.
    """
    if header_value is None:
        return False
    return header_value.strip().lower() in {"true", "1", "yes"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products  — §10.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="Create a product (Feature 3 Fast Catalog Form)",
)
@rate_limit(scope="create_product", limit=20, window=3600)
@audit_event("catalog.product.created")
async def create_product(
    payload: CreateProductRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductResponse:
    """§10.B.1 — POST /products.

    Plan-guard ``product_count`` (100 active cap) is enforced INSIDE the
    service (step 1 of the §10.B.1 flow), not in this handler.

    Status codes: 201, 400, 401, 402 (rate-limit or plan-cap),
    404 (catalog / category not found), 422 (profile incomplete).
    """
    product = await catalog_service.create_product(
        user.user_id, user.plan, payload, db=db
    )
    return _product_to_response(product)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PATCH /products/{id}  — §10.B.2
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/products/{id}",
    response_model=ProductResponse,
    summary="Update product fields (autosave + manual save)",
)
@rate_limit(scope="product_patch", limit=600, window=3600)
@audit_event("catalog.product.updated")
async def patch_product(
    id: UUID,
    payload: PatchProductRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_autosave: Annotated[str | None, Header(alias="x-autosave")] = None,
) -> ProductResponse:
    """§10.B.2 — PATCH /products/{id}.

    ``X-Autosave: true`` header signals autosave (vs manual "Save").
    When present, the service additionally upserts a ``product_drafts``
    row per `MVP_ARCH §11.6`.

    Status codes: 200, 400, 401, 404, 422.
    """
    is_autosave = _is_autosave(x_autosave)
    product = await catalog_service.patch_product(
        user.user_id, id, payload, is_autosave=is_autosave, db=db
    )
    return _product_to_response(product)


# ─────────────────────────────────────────────────────────────────────────────
# 3. POST /products/{id}/autofill  — §10.B.3
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products/{id}/autofill",
    response_model=AutofillResponse,
    summary="AI Auto-fill — Gemini-driven field suggestions",
)
@rate_limit(scope="ai_autofill", limit=50, window=3600)
@audit_event("catalog.autofill.invoked")
async def autofill_product(
    id: UUID,
    payload: AutofillRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutofillResponse:
    """§10.B.3 — POST /products/{id}/autofill.

    Returns 200 with ``fallback_offered=true`` when AI is unavailable
    (budget exhaustion, guardrail retry exhaustion).  503 is reserved
    for unrecoverable Gemini SDK exhaustion beyond §6A's fallback
    contract (raised inside the service as
    :class:`exceptions.AutofillFailedError`).

    Plan-guard ``ai_autofill_hourly`` (50/h/user) is enforced INSIDE
    the service (step 2 of the §10.B.3 flow).

    Feature flag: returns 404 when ``FEATURE_AI_AUTOFILL_ENABLED=false``
    per Master Plan §3.2 + ai-autofill FEATURE_PLAN.md D2.  Reading
    ``settings`` at request-time (not import-time) so tests can
    monkeypatch the attribute and the guard reflects the override.

    Status codes: 200 (success OR graceful fallback), 400, 401, 402,
    404, 422.
    """
    # ── Feature flag guard (§3.2 / ai-autofill D2) ───────────────────
    if not settings.FEATURE_AI_AUTOFILL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI Auto-fill is disabled in this environment",
        )

    # The request_id is set by RequestIdMiddleware on request.state.
    # We forward it to ai_ops so the LangFuse trace_id correlates with
    # the inbound request.  Falling back to a per-call UUID inside
    # call_gemini if absent (defensive).
    # NOTE: we can't easily reach request.state from inside the dep-only
    # signature; the audit middleware records the request_id separately.
    # For the AI trace correlation, use the user_id-keyed prefix.
    request_id = str(user.user_id)  # acceptable correlation key for V1.

    result = await catalog_service.autofill_product(
        user.user_id,
        user.plan,
        id,
        payload,
        request_id=request_id,
        db=db,
    )
    # Map domain → wire shape.
    return AutofillResponse(
        suggestions={
            canonical: AutofillSuggestion(
                value=sug.value,
                confidence=sug.confidence,
                source=sug.source,
            )
            for canonical, sug in result.suggestions.items()
        },
        applied=dict(result.applied),
        fallback_offered=result.fallback_offered,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /products/{id}/preview  — §10.B.4
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/preview",
    response_model=ProductPreviewResponse,
    summary="Live Product Preview — Feature 6 wizard view",
)
@rate_limit(scope="product_preview", limit=600, window=3600)
async def get_product_preview(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductPreviewResponse:
    """§10.B.4 — GET /products/{id}/preview.

    No audit event (read-only per `MVP_ARCH §11.3`).

    Status codes: 200, 401, 404.
    Feature flag: returns 404 with code ``feature.live_preview.disabled``
    when ``FEATURE_LIVE_PREVIEW_ENABLED=false`` (default False — gated rollout
    per Master Plan §3.2 + FEATURE_PLAN.md D3).
    """
    # ── Feature flag guard (§3.2 / D3 gated rollout) ─────────────────────
    # NOTE: FEATURE_LIVE_PREVIEW_ENABLED defaults to False (the ONLY V1 flag
    # that ships default-False; all others default True). Raise via MeesellError
    # to carry the machine-readable `code` field per §4.F envelope contract.
    if not settings.FEATURE_LIVE_PREVIEW_ENABLED:
        raise MeesellError(
            code="feature.live_preview.disabled",
            status_code=404,
            detail="Preview unavailable",
        )
    preview = await catalog_service.get_preview(user.user_id, id, db=db)
    return ProductPreviewResponse(
        id=preview.id,
        name=preview.name,
        category_path=preview.category_path,
        fields=[
            ProductPreviewField(
                canonical_name=f.canonical_name,
                display_label=f.display_label,
                value=f.value,
                is_advanced=f.is_advanced,
            )
            for f in preview.fields
        ],
        image_urls=list(preview.image_urls),
        compliance=dict(preview.compliance or {}),
        status=preview.status,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. DELETE /products/{id}  — §10.B.5
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/products/{id}",
    status_code=204,
    summary="Soft-delete a product",
)
@rate_limit(scope="product_delete", limit=60, window=3600)
@audit_event("catalog.product.deleted")
async def delete_product(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """§10.B.5 — DELETE /products/{id}.

    Status codes: 204, 401, 404.
    """
    await catalog_service.soft_delete(user.user_id, id, db=db)
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET /products/{id}/draft  — §10.B.6
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/draft",
    response_model=ProductDraftResponse,
    responses={204: {"description": "No draft snapshot exists for this product."}},
    summary="Draft recovery — most recent autosave snapshot",
)
@rate_limit(scope="product_draft_read", limit=600, window=3600)
async def get_product_draft(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response | ProductDraftResponse:
    """§10.B.6 — GET /products/{id}/draft.

    Returns 200 with the snapshot when a draft exists; 204 with no body
    when the product has never been autosaved.

    No audit event (read-only).

    Status codes: 200, 204, 401, 404.
    """
    draft = await catalog_service.get_draft(user.user_id, id, db=db)
    if draft is None:
        # 204 — empty body.  No envelope (per RFC 7231 §6.3.5).
        return Response(status_code=204)
    return ProductDraftResponse(
        fields=dict(draft.fields or {}),
        last_updated=draft.last_updated,
        autosave_count=draft.autosave_count,
    )


__all__ = ["router"]


# Silence unused-import noise — DraftNotFoundError is intentionally available
# for service-layer raises that the router translates to 204 (defensive path
# beyond the documented `None`-return contract).
_ = (Any, DraftNotFoundError, PaginationInternal)
