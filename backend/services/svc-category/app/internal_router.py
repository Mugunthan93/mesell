"""svc-category internal router — /internal/* shims for service-to-service calls.

These routes are cluster-internal ONLY.  They are NOT exposed to the public
internet (Traefik IngressRoute for ``/internal/*`` routes to the ClusterIP only).
They carry ``include_in_schema=False`` to hide them from the public OpenAPI docs.

Auth posture (§5.A / Sub-Plan F §F2)
-------------------------------------
Internal routes use service-to-service trust (forwarded JWT header per §5.A),
NOT the ``get_current_user`` UI flow.  The calling service (export-svc,
catalog-svc, pricing-svc, customer-svc) forwards the original user's JWT in the
``Authorization`` header — category-svc validates it locally (D7) and then
proceeds without inspecting the user identity further.

The ``x-internal-service`` header identifies the calling service for logging.
There is NO per-route rate-limit on internal routes (called by trusted pods
behind Traefik's cluster-internal route).

Frozen shim shapes (§F4)
-------------------------
Shim #1  — ``GET /internal/categories/{id}/schema``
    Returns ``SchemaResponse`` — the §5A.B 7-key envelope verbatim.
    Callers (post-extraction, over HTTP): export-svc, catalog-svc.
    FROZEN by MS-A.  NEVER rename or reshape.

Shim #2  — ``GET /internal/categories/{id}/field-enum/{field}``
    Returns ``FieldEnumResponse`` — {enum_entries:[{canonical,meesho,labels}],
    total, truncated}.
    Callers (post-extraction): export-svc.
    FROZEN by MS-A.  NEVER rename or reshape.

Defensive shims (§F4 Open Questions resolved)
---------------------------------------------
Shim #3  — ``GET /internal/categories/{id}/commission``
    Returns ``CommissionResponse`` — {"commission_pct": "<decimal-string>"}.
    Caller: pricing-svc (MS-D, already extracted; its category_client shim
    calls this path per spec_msD_backend.md §3.A).
    FROZEN by MS-D §1 — NEVER-NULL Decimal-string contract.  The service layer
    guarantees a non-None return (Decimal("0.00") for unseeded categories).

Shim #4  — ``GET /internal/super-categories``
    Returns a BARE JSON ARRAY ``["26", "19", ...]`` — body is ``list[str]``.
    The list contains distinct ``super_id`` STRING values (FROZEN-0E).
    Caller: customer-svc (MS-E, already extracted; its E3-A category_client shim
    iterates ``payload`` directly as ``[str(item) for item in payload]``).
    Shape confirmed by spec_msE_backend.md §9 FROZEN-0E + category_client.py:50-51.
    FROZEN-0E.  NEVER wrap in an object envelope.

``include_in_schema=False`` on every route (locked pattern from svc-image MS-C B2)
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app import service as category_service
from app.core.auth import get_current_user  # service-to-service: validates JWT locally
from app.schemas import (
    CommissionResponse,
    FieldEnumResponse,
    SchemaResponse,
)
from app.shared.database import get_db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Internal router — /internal prefix, hidden from public OpenAPI
# ─────────────────────────────────────────────────────────────────────────────
_internal_router = APIRouter(prefix="/internal", tags=["internal-category"])

# ─────────────────────────────────────────────────────────────────────────────
# Shim #1 — GET /internal/categories/{id}/schema   (FROZEN MS-A §F4)
# ─────────────────────────────────────────────────────────────────────────────
@_internal_router.get(
    "/categories/{id}/schema",
    response_model=SchemaResponse,
    summary="[INTERNAL] Compiled wizard schema for a category — callers: export-svc, catalog-svc",
    include_in_schema=False,
)
async def internal_get_category_schema(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    # Service-to-service JWT validation (D7 local — not the UI get_current_user flow)
    _user: Annotated[object, Depends(get_current_user)],
    x_internal_service: Annotated[str | None, Header(alias="x-internal-service")] = None,
) -> SchemaResponse:
    """FROZEN MS-A Shim #1 — schema envelope for category ``id``.

    Returns the ``templates.schema_jsonb`` envelope verbatim (§5A.B 7 keys).
    Shape LOCKED — NEVER add/remove keys.  export-svc and catalog-svc call
    this path; their category_client shims expect this exact shape.

    On category not found: propagates ``CategoryNotFoundError`` → 404 via
    ``core/errors.register_error_handlers``.
    """
    logger.debug(
        "internal_get_category_schema: id=%s caller=%s",
        id,
        x_internal_service or "unknown",
    )
    payload = await category_service.fetch_schema(id, db=db)
    return SchemaResponse.model_validate(payload)


# ─────────────────────────────────────────────────────────────────────────────
# Shim #2 — GET /internal/categories/{id}/field-enum/{field}  (FROZEN MS-A §F4)
# ─────────────────────────────────────────────────────────────────────────────
@_internal_router.get(
    "/categories/{id}/field-enum/{field}",
    response_model=FieldEnumResponse,
    summary="[INTERNAL] Field-Enum lookup — caller: export-svc",
    include_in_schema=False,
)
async def internal_get_field_enum(
    id: UUID,
    field: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[object, Depends(get_current_user)],
    x_internal_service: Annotated[str | None, Header(alias="x-internal-service")] = None,
) -> FieldEnumResponse:
    """FROZEN MS-A Shim #2 — field-enum entries for category ``id`` / field ``field``.

    Returns ``{enum_entries:[{canonical, meesho, labels}], total, truncated}``.
    Shape LOCKED — NEVER add/remove top-level keys.  export-svc calls this
    path; its category_client shim expects this exact shape.

    On not found: propagates ``CategoryNotFoundError`` / ``FieldEnumNotFoundError``
    → 404 via error handlers.
    """
    logger.debug(
        "internal_get_field_enum: id=%s field=%s caller=%s",
        id,
        field,
        x_internal_service or "unknown",
    )
    payload = await category_service.get_field_enum(id, field, db=db)
    return FieldEnumResponse.model_validate(payload)


# ─────────────────────────────────────────────────────────────────────────────
# Shim #3 — GET /internal/categories/{id}/commission  (FROZEN MS-D §1)
# ─────────────────────────────────────────────────────────────────────────────
@_internal_router.get(
    "/categories/{id}/commission",
    response_model=CommissionResponse,
    summary="[INTERNAL] Category commission_pct — caller: pricing-svc (NEVER-NULL Decimal-string)",
    include_in_schema=False,
)
async def internal_get_commission(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[object, Depends(get_current_user)],
    x_internal_service: Annotated[str | None, Header(alias="x-internal-service")] = None,
) -> CommissionResponse:
    """FROZEN MS-D §1 — commission_pct for category ``id``.

    Returns ``{"commission_pct": "<decimal-string>"}``.

    INVARIANT: ``commission_pct`` is NEVER None and NEVER a float.  Pydantic v2
    serialises ``Decimal`` fields as JSON strings by default (no json_encoders
    override).  The service layer guarantees Decimal("0.00") when the category
    has no seeded commission.

    pricing-svc's category_client shim calls this path and deserialises
    ``commission_pct`` as a Decimal.  If this field is ever null/float, the
    MS-D T1 golden test fails.

    On category not found: propagates ``CategoryNotFoundError`` → 404.
    """
    logger.debug(
        "internal_get_commission: id=%s caller=%s",
        id,
        x_internal_service or "unknown",
    )
    commission = await category_service.get_commission(id, db=db)
    return CommissionResponse(commission_pct=commission)


# ─────────────────────────────────────────────────────────────────────────────
# Shim #4 — GET /internal/super-categories  (FROZEN-0E)
# ─────────────────────────────────────────────────────────────────────────────
@_internal_router.get(
    "/super-categories",
    response_model=list[str],
    summary="[INTERNAL] Distinct super_id list as list[str] — caller: customer-svc (FROZEN-0E)",
    include_in_schema=False,
)
async def internal_list_super_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[object, Depends(get_current_user)],
    x_internal_service: Annotated[str | None, Header(alias="x-internal-service")] = None,
) -> list[str]:
    """FROZEN-0E — distinct super_id strings for customer-svc.

    Returns a BARE JSON ARRAY ``["26", "19", ...]`` — body IS the list,
    NOT wrapped in an object envelope.

    INVARIANT: response body is ``list[str]`` at the top level.
    customer-svc's E3-A category_client shim (category_client.py:50-51) does:
        payload = await request_json("GET", "/internal/super-categories")
        return [str(item) for item in payload]
    It iterates ``payload`` DIRECTLY — an object envelope would iterate dict
    KEYS, returning ``["super_categories"]`` instead of the actual ids.

    The service layer returns ``list[SuperCategoryInfo]``; this handler coerces
    to ``list[str]`` by extracting the ``super_id`` attribute from each info
    object.

    SUB_PLAN_0F §F4 + spec_msE §9 FROZEN-0E.
    """
    logger.debug(
        "internal_list_super_categories: caller=%s",
        x_internal_service or "unknown",
    )
    infos = await category_service.list_super_categories(db=db)
    # FROZEN-0E: coerce list[SuperCategoryInfo] → bare list[str] (super_id only)
    return [info.super_id for info in infos]


# ─────────────────────────────────────────────────────────────────────────────
# Compose internal router
# ─────────────────────────────────────────────────────────────────────────────
# Expose a single ``router`` symbol that main.py mounts:
#   app.include_router(internal_router)   ← from app.internal_router import router
# This follows the svc-image MS-C B2 pattern: _internal_router composed via
# router.include_router(_internal_router); main.py gets all 4 internal routes
# in one include_router call.
router = APIRouter()
router.include_router(_internal_router)

__all__ = ["router"]
