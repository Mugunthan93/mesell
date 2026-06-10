"""``category`` router — 5 endpoint handlers per §9.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``GET  /api/v1/categories/suggest?q=<description>``     — Smart Category Picker (§9.B.1)
2. ``GET  /api/v1/categories/browse``                      — Manual Browse pg_trgm (§9.B.2)
3. ``GET  /api/v1/categories``                             — Full category tree (§9.B.3)
4. ``GET  /api/v1/categories/{id}/schema``                 — Compiled wizard schema (§9.B.4)
5. ``GET  /api/v1/categories/{id}/field-enum/{name}``      — Field-Enum lookup (§9.B.5)

Route invariants (§9.B + §4.B):
- Every handler is ``async def``.
- Every handler requires ``Depends(get_current_user)`` — routes NEVER decode JWT.
- Every handler receives ``db: AsyncSession = Depends(get_db)`` and forwards as kwarg.
- NO business logic inlined — orchestration only (extract params, call service, wrap schema).
- NO error envelope formatting — exceptions raised are ``CategoryError`` subclasses which
  ``core/errors.register_error_handlers`` (§4.F) translates into the locked envelope.

Audit posture (§9.B + §4.G):
- ALL 5 endpoints are read-only → NO audit rows per ``MVP_ARCH §11.3`` flood-prevention
  rationale.  Same posture as §7.B.5 ``/me`` and §8.B.1 / §8.B.5 read endpoints.

Rate-limit decorators (§4.G + §4.E):
- ``GET /suggest``  — ``@rate_limit(scope="smart_picker", limit=100, window=3600)``
  (plan_guard enforced INSIDE ``service.suggest_categories`` per §9.B.1 flow step 2,
  not in the router — follows the §8 customer router precedent where plan_guard lives
  inside the service, not the handler).
- ``GET /browse``, ``GET /categories``, ``GET /{id}/schema``, ``GET /{id}/field-enum/{name}``
  — no per-route decorator; per-IP floor from ``RateLimitMiddleware`` applies.

ETag handling (§9.B.3 + §9.B.4 + §4.D):
- ``GET /categories`` and ``GET /categories/{id}/schema`` set the ``ETag`` response
  header via ``core.cache.etag_for(json.dumps(payload).encode())``.
- When the request carries ``If-None-Match`` matching the computed ETag, the handler
  returns ``Response(status_code=304)`` with no body (per RFC 7232 §4.1 — 304 MUST
  NOT include a message body).

DECISION FLAG §9-ROUTES-D1
---------------------------
``@rate_limit`` decorator is placed ABOVE ``@router.get`` so Starlette sees the
innermost function (the route handler) rather than the decorated wrapper.  This
matches the order used in the customer router (§8) and is the locked pattern for
MeeSell decorated routes.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.cache import etag_for
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.category import service as category_service
from app.modules.category.schemas import (
    BrowseResponse,
    CategoryTreeResponse,
    FieldEnumResponse,
    SchemaResponse,
    SuggestResponse,
)
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["category"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /categories/suggest  — §9.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/categories/suggest",
    response_model=SuggestResponse,
    summary="AI-ranked Smart Category Picker — top-5 suggestions for a product description",
)
@rate_limit(scope="smart_picker", limit=100, window=3600)
async def suggest_categories(
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=500,
            description="Free-text product description (1–500 chars)",
        ),
    ],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuggestResponse:
    """§9.B.1 — Smart Category Picker.

    Returns top-5 AI-ranked category suggestions for the seller's product
    description.  ``fallback_offered=True`` when the AI track cannot produce
    valid suggestions (budget cap, retry exhaustion) — the frontend surfaces
    the manual ``/browse`` UI in that case.

    Plan-guard ``smart_picker_hourly`` (100/h/user) is enforced INSIDE the
    service (step 2 of the §9.B.1 pipeline), not in this handler.

    Rate limit: 100 calls/h per user_id via ``@rate_limit`` decorator (§4.E).
    """
    payload = await category_service.suggest_categories(
        user.user_id, q, db=db
    )
    return SuggestResponse.model_validate(payload)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /categories/browse  — §9.B.2
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/categories/browse",
    response_model=BrowseResponse,
    summary="pg_trgm-powered manual category browse with optional super-category filter",
)
async def browse_categories(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(max_length=100, description="Optional search query (max 100 chars)"),
    ] = None,
    super_id: Annotated[
        str | None,
        Query(description="Optional super-category filter"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Page size (1–100, default 20)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Page offset (>=0, default 0)"),
    ] = 0,
) -> BrowseResponse:
    """§9.B.2 — Manual Browse fallback.

    pg_trgm ILIKE against the 3 GIN indexes (path, leaf_name, super_name).
    Results ordered by similarity score; super_id filter narrows to one
    parent bucket.

    No per-route rate limit (per-IP DDoS floor only — incremental typing
    is a legitimate burst pattern per §9.B.2).

    Status codes: 200; 400 (``validation.browse.invalid_pagination``); 401.
    """
    payload = await category_service.browse_categories(
        q, super_id, limit, offset, db=db
    )
    return BrowseResponse.model_validate(payload)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /categories  — §9.B.3
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/categories",
    response_model=CategoryTreeResponse,
    summary="Full hierarchical category tree (all super-categories + leaf children)",
)
async def get_category_tree(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_none_match: Annotated[str | None, Header(alias="if-none-match")] = None,
) -> Response | CategoryTreeResponse:
    """§9.B.3 — Full category tree.

    Returns all 3,772 category leaves grouped under their super-categories.
    Cached GLOBAL with TTL 1 h + ETag per §4.D + §6.6.

    ETag behaviour:
    - Response includes ``ETag`` header on 200.
    - If the request sends ``If-None-Match`` matching the ETag, responds
      304 Not Modified (no body).

    No per-route rate limit (per-IP DDoS floor only).
    """
    payload = await category_service.get_category_tree(db=db)
    etag_value = etag_for(json.dumps(payload, default=str).encode())

    # 304 short-circuit when client already has current tree.
    if if_none_match and if_none_match == etag_value:
        return Response(status_code=304)

    return Response(
        content=json.dumps(
            CategoryTreeResponse.model_validate(payload).model_dump(mode="json"),
            default=str,
        ),
        media_type="application/json",
        headers={"ETag": etag_value},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /categories/{id}/schema  — §9.B.4
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/categories/{id}/schema",
    response_model=SchemaResponse,
    summary="Compiled wizard schema for a category (templates.schema_jsonb envelope)",
)
async def get_category_schema(
    id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_none_match: Annotated[str | None, Header(alias="if-none-match")] = None,
) -> Response | SchemaResponse:
    """§9.B.4 — Compiled wizard schema.

    Returns the ``templates.schema_jsonb`` envelope per §5A.B verbatim
    (7 keys: ``fields[]``, ``compulsory_count``, ``optional_count``,
    ``total_count``, ``wizard_step_count``, ``main_sheet_label``,
    ``compliance_shape``).

    Cached GLOBAL per ``category_id`` with TTL 1 h + ETag per §4.D + §6.6.
    Pre-warmed for top-100 categories at startup.

    ETag behaviour mirrors ``GET /categories`` (304 on match).

    Cross-module consumers: ``catalog.service.validate_product`` (§2.4 + §16)
    and ``export.service.build_xlsx_sheet`` (§2.8) both call
    ``category.service.fetch_schema`` directly — this HTTP surface is for
    the frontend wizard and API clients.

    Status codes: 200; 401; 404 (``category.lookup.not_found``).
    """
    payload = await category_service.fetch_schema(id, db=db)
    etag_value = etag_for(json.dumps(payload, default=str).encode())

    if if_none_match and if_none_match == etag_value:
        return Response(status_code=304)

    return Response(
        content=json.dumps(
            SchemaResponse.model_validate(payload).model_dump(mode="json"),
            default=str,
        ),
        media_type="application/json",
        headers={"ETag": etag_value},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /categories/{id}/field-enum/{name}  — §9.B.5
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/categories/{id}/field-enum/{name}",
    response_model=FieldEnumResponse,
    summary="Field-Enum lookup for Brand-pattern fields (canonical + meesho + labels)",
)
async def get_field_enum(
    id: UUID,
    name: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FieldEnumResponse:
    """§9.B.5 — Field-Enum lookup.

    Returns the complete enum value list for a Brand-pattern field within a
    category.  Each ``EnumEntry`` carries:

    - ``canonical`` — used by catalog validator for input acceptance.
    - ``meesho``    — consumed by export adapter only; never rendered in wizard.
    - ``labels``    — ``{locale: label}``; V1 contains only ``"en"``.

    Cached GLOBAL per ``(category_id, field_name)`` with TTL 1 h.  Single-flight
    mandatory per ``MVP_ARCH §6.8`` (enum payloads can be 50–200 KB each).

    Status codes: 200; 401; 404 (``category.lookup.not_found`` if category_id
    invalid; ``category.field_enum.not_found`` if field_name has no enum for
    this category).
    """
    payload = await category_service.get_field_enum(id, name, db=db)
    return FieldEnumResponse.model_validate(payload)


__all__ = ["router"]
