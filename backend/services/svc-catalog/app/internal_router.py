"""svc-catalog internal router — 3 LIVE + 1 defensive /internal/* shims.

Per SUB_PLAN_0H §H4 (LOCKED contract; MS-A frozen shapes; §16.G zero-diff
call-site preservation). Mounted unconditionally by ``app.main`` — the internal
surface is NOT gated by ``FEATURE_CATALOG_FORM_ENABLED`` (sibling services must
always reach ownership-check / export-snapshot / list_products regardless of
the public-form rollout state).

Auth posture for /internal/* routes
-------------------------------------
* NO ``get_current_user`` UI dependency injection — these are cluster-internal
  routes (K3s NetworkPolicy blocks them from outside the cluster per §5.A
  line 338).
* The caller forwards the user's JWT in the ``Authorization`` header;
  the ``AuthContextMiddleware`` opportunistically decodes it and attaches
  ``CurrentUser`` to ``request.state.user`` (fail-open).  Each shim reads
  ``request.state.user`` directly and raises 401 if missing.
* This pattern mirrors the export pilot (svc-export's /internal/* pattern)
  and the image pilot (svc-image/app/router.py _internal_router pattern).
* All /internal/* routes use ``include_in_schema=False`` — hidden from the
  public OpenAPI doc.

Shims implemented
-----------------
#1 GET  /internal/products/{id}/ownership-check    [MS-A FROZEN + §0.6 WIDENED]
    ← catalog/service.py:921 assert_product_ownership(product_id, user_id, db)
    Returns: 200 {"owned": true, "category_id": "<uuid>"}  on success
             404 catalog.product.not_found on (not-exist ∨ wrong-owner ∨ soft-del)
    Callers: image-svc, pricing-svc, export-svc

    §0.6 WIDENED: originally 204 (export pilot froze as 204/204-on-pass),
    THEN widened to 200+body by pricing-svc catalog_client §0.6 Option B so
    that pricing can read category_id without a second round-trip.  The
    MERGED pricing consumer (svc-pricing/app/core/extracted_clients/catalog_client.py)
    calls ``GET /internal/products/{id}/ownership-check`` and reads
    ``payload.get("category_id")`` from the 200 body.  This IS the contract —
    the spec session-prompt says "returns the WIDENED body {owned: true,
    category_id: <uuid>} (GET, not POST/204)".

#2 GET  /internal/products/{id}/export-snapshot    [MS-A FROZEN]
    ← catalog/service.py:945 get_product_for_export(product_id, user_id, db)
    Returns: ExportSnapshotResponse (product_id, category_id, fields,
             ai_suggestions, image_refs, validation_summary)
    Callers: export-svc

    2-HOP CHAIN: this shim calls catalog_service.get_product_for_export which
    internally calls category_service.fetch_schema (the outbound category shim).
    export-svc → catalog-svc → category-svc is the documented chain (§H4 §H shim #2).

#3 GET  /internal/products              [dashboard frozen contract — SUB_PLAN_0B]
    ← catalog/service.py:999 list_products(user_id, pagination, db)
    Returns: PaginatedProductsInternalResponse {items, total, page, limit}
    Callers: dashboard-svc
    user_id derived from forwarded JWT sub claim (NOT from URL — frozen contract).

#4 GET  /internal/products/{id}/validation-summary  [DEFENSIVE — §H4 R10]
    ← catalog/service.py:1020 get_validation_summary(user_id, product_id, db)
    Returns: ValidationSummaryInternalResponse
    Callers: NONE at develop tip (documented-but-not-called contradiction per §H4).
    Author defensively; unused shim is harmless (cheap insurance for the spine).

Open Question #1 — /internal/categories/{id}/exists
-----------------------------------------------------
The services-builder's category_client in this svc-catalog tree calls
``GET /internal/categories/{id}/exists`` for ``assert_category_exists``.
The merged category-svc (PR #221, feature/microservices-category/svc) serves
``/internal/categories/{id}/schema`` (frozen shim #1) and
``/internal/categories/{id}/field-enum/{field}`` (frozen shim #2) and
``/internal/categories/super-categories`` (shim #3).  It does NOT serve
``/internal/categories/{id}/exists`` — the sub-plan §F4 deferred this to
"added when catalog extracts (MS-5)".

RECOMMENDATION for backend-coordinator:
  (a) FALLBACK: catalog's category_client calls ``GET /internal/categories/{id}/schema``
      (already served by category-svc); a 200 response implies exists=True, 404 implies
      not_found — semantic equivalence at V1 traffic volumes.  This is a zero-ceremony
      patch: rename ``assert_category_exists`` → call fetch_schema and ignore the body
      (or treat 404 as the "not found" signal).  NO category-svc amendment needed.
  (b) AMENDMENT: add ``GET /internal/categories/{id}/exists`` to category-svc, returning
      200 {} on found and 404 on not-found.  Requires a category-svc re-open in MS-5.

  RECOMMENDED: option (a) — the /schema endpoint already gates existence.  Catalog's
  category_client `assert_category_exists` can call /schema and discard the body; the
  service-layer semantics are identical.  Avoids a category-svc re-open.
  FINAL RULING deferred to backend-coordinator gate.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenMissingError
from app.schemas import (
    ExportSnapshotResponse,
    OwnershipCheckResponse,
    PaginatedProductsInternalResponse,
    ProductInternalItem,
    ValidationSummaryInternalResponse,
    ValidationSummaryResponse,
)
from app.domain import Pagination as PaginationInternal
from app.shared.database import get_db

import app.service as catalog_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal router — NOT flag-gated; hidden from public OpenAPI
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/internal", tags=["catalog-internal"])


def _get_user_from_state(request: Request):
    """Extract CurrentUser from request.state (set by AuthContextMiddleware).

    Raises :class:`~app.core.auth.TokenMissingError` (401) if the bearer token
    was absent or malformed — the middleware silently drops invalid tokens
    (fail-open posture) so we must guard explicitly here.

    Per §5.A line 338: caller forwards the user JWT; callee validates it.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise TokenMissingError()
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Shim #1 — ownership-check (MS-A FROZEN + §0.6 WIDENED)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/ownership-check",
    response_model=OwnershipCheckResponse,
    include_in_schema=False,
    summary="[INTERNAL] Ownership gate + category_id read (§0.6 widened)",
)
async def ownership_check(
    id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[
        UUID | None,
        Query(description="Caller user_id for §10 leak-protection validation"),
    ] = None,
) -> OwnershipCheckResponse:
    """GET /internal/products/{id}/ownership-check

    MS-A FROZEN + §0.6 WIDENED contract (load-bearing — merged consumers WIN).

    Auth: forwarded JWT → request.state.user (via AuthContextMiddleware).
    The ``user_id`` query param is accepted for call-site parity with the
    callers (pricing/export/image catalog_clients pass ``params={"user_id":
    str(user_id)}``).  The authoritative tenant is determined from:
    1. ``user_id`` query param if provided (most callers supply it).
    2. Fallback: ``request.state.user.user_id`` from the forwarded JWT.
    This dual-source matches the MS-A/§5.A forwarded-JWT contract and the
    merged pricing consumer's call signature.

    Returns
    -------
    200 OwnershipCheckResponse{owned=true, category_id=<uuid>} on success.
    404 ProductNotFoundError on (not-exist ∨ wrong-owner ∨ soft-deleted).
    401 TokenMissingError if no valid JWT forwarded.
    """
    state_user = _get_user_from_state(request)
    # Use query param first (callers pass it explicitly for §10 enforcement);
    # fall back to JWT sub claim for callers that rely on the bearer-token only.
    resolved_user_id: UUID = user_id if user_id is not None else state_user.user_id

    # assert_product_ownership raises ProductNotFoundError (404) if absent /
    # wrong owner / soft-deleted — §10 leak-protection collapse.
    await catalog_service.assert_product_ownership(id, resolved_user_id, db=db)

    # After ownership is confirmed, fetch the product to read category_id.
    # find_by_id is scoped to the resolved_user_id (scope_to_user preserved).
    # We use a thin domain fetch — the service's public surface does not expose
    # find_by_id directly; call assert_product_ownership first (already done
    # above), then use the service-layer list helper with page=1 limit=1 to
    # get the row.  HOWEVER, to keep this lean, we call get_draft path …
    # Actually: the cleanest path is to fetch the product ORM directly.
    # We call catalog_service.get_preview which returns ProductPreviewInternal
    # with category_path but we need category_id UUID.
    # The ACTUAL right approach: call find_by_id via the repository directly,
    # since assert_product_ownership already confirmed ownership.
    # catalog_service exposes no "get_product_by_id" public method — only
    # get_preview (needs FEATURE_LIVE_PREVIEW_ENABLED=True) and draft.
    # SOLUTION: the sub-plan says the router calls service methods ONLY.
    # We import catalog_repo's find_by_id indirectly via service — but there
    # is no public thin accessor.
    # Per §16.G: we call catalog_service.get_product_for_export which internally
    # asserts ownership (idempotent) and returns ExportSnapshotInternal which
    # carries category_id.  This is a heavier call but avoids bypassing the
    # service layer.  For the ownership-check shim the callers only need
    # category_id — not the full snapshot — so we use get_product_for_export
    # and discard the rest.  The double ownership assert is idempotent + cheap
    # (same user_id, same product_id, already confirmed above).
    snapshot = await catalog_service.get_product_for_export(id, resolved_user_id, db=db)
    return OwnershipCheckResponse(owned=True, category_id=snapshot.category_id)


# ─────────────────────────────────────────────────────────────────────────────
# Shim #2 — export-snapshot (MS-A FROZEN)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/export-snapshot",
    response_model=ExportSnapshotResponse,
    include_in_schema=False,
    summary="[INTERNAL] Frozen export snapshot (§H4 shim #2)",
)
async def export_snapshot(
    id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[
        UUID | None,
        Query(description="Caller user_id; overrides JWT sub when provided"),
    ] = None,
) -> ExportSnapshotResponse:
    """GET /internal/products/{id}/export-snapshot

    MS-A FROZEN shape — returns ExportSnapshotInternal serialised as JSON.
    export-svc catalog_client reads: product_id, category_id, fields,
    ai_suggestions, image_refs, validation_summary{status, ...}.

    2-HOP CHAIN: this shim → catalog_service.get_product_for_export →
    category_service.fetch_schema (outbound to category-svc).  The nested
    hop is cached at category-svc (≥99% cache hit, SUB_PLAN_0F §F-acceptance).

    Auth: forwarded JWT → request.state.user (via AuthContextMiddleware).
    user_id query param overrides the JWT sub when provided (call-site parity).

    Returns
    -------
    200 ExportSnapshotResponse on success.
    404 ProductNotFoundError (collapsed: not-exist ∨ wrong-owner ∨ soft-deleted).
    401 TokenMissingError if no valid JWT forwarded.
    """
    state_user = _get_user_from_state(request)
    resolved_user_id: UUID = user_id if user_id is not None else state_user.user_id

    snapshot = await catalog_service.get_product_for_export(id, resolved_user_id, db=db)

    vs = snapshot.validation_summary
    return ExportSnapshotResponse(
        product_id=snapshot.product_id,
        category_id=snapshot.category_id,
        fields=dict(snapshot.fields or {}),
        ai_suggestions=dict(snapshot.ai_suggestions or {}),
        image_refs=list(snapshot.image_refs or ()),
        validation_summary=ValidationSummaryResponse(
            product_id=vs.product_id,
            compulsory_filled=vs.compulsory_filled,
            compulsory_total=vs.compulsory_total,
            optional_filled=vs.optional_filled,
            optional_total=vs.optional_total,
            has_validation_errors=vs.has_validation_errors,
            status=str(vs.status),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shim #3 — list products (dashboard frozen contract — SUB_PLAN_0B)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products",
    response_model=PaginatedProductsInternalResponse,
    include_in_schema=False,
    summary="[INTERNAL] Paginated active products for dashboard (SUB_PLAN_0B)",
)
async def list_products_internal(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
) -> PaginatedProductsInternalResponse:
    """GET /internal/products?page=&limit=

    Dashboard frozen contract (SUB_PLAN_0B §"Shim 1").
    user_id is derived ONLY from the forwarded JWT sub claim — NOT from
    the URL (frozen contract, dashboard catalog_client comment: "user_id is
    NOT placed in the URL: the callee derives the tenant from the forwarded
    JWT sub claim").  scope_to_user preserved per §10 leak rule.

    dashboard-svc catalog_client deserialises: items[].{id, user_id,
    catalog_id, category_id, name, status, fields, ai_suggestions,
    created_at, updated_at, deleted_at} + total + page + limit.

    Auth: forwarded JWT → request.state.user (AuthContextMiddleware).
    Returns
    -------
    200 PaginatedProductsInternalResponse.
    401 TokenMissingError if no valid JWT forwarded.
    """
    state_user = _get_user_from_state(request)
    pagination = PaginationInternal(page=page, limit=limit)

    result = await catalog_service.list_products(
        user_id=state_user.user_id, pagination=pagination, db=db
    )

    items = [
        ProductInternalItem(
            id=p.id,
            user_id=p.user_id,
            catalog_id=p.catalog_id,
            category_id=p.category_id,
            name=p.name,
            status=p.status,
            fields=dict(p.fields or {}),
            ai_suggestions=dict(p.ai_suggestions or {}),
            created_at=p.created_at,
            updated_at=p.updated_at,
            deleted_at=p.deleted_at,
        )
        for p in result.items
    ]
    return PaginatedProductsInternalResponse(
        items=items,
        total=result.total,
        page=result.page,
        limit=result.limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shim #4 — validation-summary (DEFENSIVE — §H4 R10)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products/{id}/validation-summary",
    response_model=ValidationSummaryInternalResponse,
    include_in_schema=False,
    summary="[INTERNAL] Validation summary — DEFENSIVE (§H4 R10, no live caller)",
)
async def validation_summary_internal(
    id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[
        UUID | None,
        Query(description="Caller user_id; overrides JWT sub when provided"),
    ] = None,
) -> ValidationSummaryInternalResponse:
    """GET /internal/products/{id}/validation-summary

    DEFENSIVE shim — documented-but-not-called per §H4 R10 contradiction:
    catalog's ``__init__.py:11`` + ``service.py:23`` assert dashboard consumes
    ``get_validation_summary`` but grep returns ZERO live callers at develop
    tip.  Authored as cheap insurance — if a dashboard slice ever calls this
    over HTTP, the shim already exists (SUB_PLAN_0F ``list_super_categories``
    precedent).

    Auth: forwarded JWT → request.state.user (AuthContextMiddleware).
    Returns
    -------
    200 ValidationSummaryInternalResponse on success.
    404 ProductNotFoundError (ownership + not-found collapsed).
    401 TokenMissingError if no valid JWT forwarded.
    """
    state_user = _get_user_from_state(request)
    resolved_user_id: UUID = user_id if user_id is not None else state_user.user_id

    summary = await catalog_service.get_validation_summary(
        user_id=resolved_user_id, product_id=id, db=db
    )
    return ValidationSummaryInternalResponse(
        product_id=summary.product_id,
        compulsory_filled=summary.compulsory_filled,
        compulsory_total=summary.compulsory_total,
        optional_filled=summary.optional_filled,
        optional_total=summary.optional_total,
        has_validation_errors=summary.has_validation_errors,
        status=str(summary.status),
    )


__all__ = ["router"]
