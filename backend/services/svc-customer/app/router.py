"""svc-customer router — 5 public endpoint handlers per §8.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``GET  /api/v1/seller-profile``                        — read current profile (§8.B.1)
2. ``PATCH /api/v1/seller-profile``                       — partial update base fields (§8.B.2)
3. ``PATCH /api/v1/seller-profile/active-categories``     — declare active super-categories (§8.B.3)
4. ``PATCH /api/v1/seller-profile/compliance/{super_id}`` — set compliance extension (§8.B.4)
5. ``GET  /api/v1/seller-profile/required-fields``        — drives onboarding wizard (§8.B.5)

Source traceability
-------------------
All 5 handlers are moved VERBATIM from:
  backend/app/modules/customer/router.py (monolith)

Line citations (source file):
  §8.B.1  GET  /seller-profile              — source lines 75-95
  §8.B.2  PATCH /seller-profile             — source lines 101-123
  §8.B.3  PATCH /seller-profile/active-categories — source lines 129-152
  §8.B.4  PATCH /seller-profile/compliance/{super_id} — source lines 158-192
  §8.B.5  GET  /seller-profile/required-fields — source lines 198-220

Route invariants (§8.B + §4.B):
- Every handler is ``async def``.
- Every handler requires ``Depends(get_current_user)`` — routes NEVER decode JWT themselves.
- Every handler receives ``db: AsyncSession = Depends(get_db)`` and forwards as keyword arg.
- NO business logic inlined — orchestration only (extract user_id, call service, return schema).
- NO error envelope formatting — exceptions raised are ``CustomerError`` subclasses which
  ``core/errors.register_error_handlers`` (§4.F) translates into the locked envelope automatically.

Rate-limit decorators (§4.G)
-----------------------------
§8.B specifies ``@rate_limit(scope=..., limit="60/h", key="user_id")``.  The Wave 1
``rate_limit`` decorator at ``app/core/middleware/rate_limit_mw.py`` exposes
``rate_limit(scope, limit: int, window: int)`` — no ``key=`` parameter (per the pre-existing
D2 deviation documented in the iam router).  Effective semantics with the existing decorator:

  * authenticated routes → keyed per ``user_id`` (middleware reads ``request.state.user_id``
    set by the ``TenancyContextMiddleware`` after ``AuthContextMiddleware`` resolves the JWT).
  * anonymous routes → keyed per IP.

So all three PATCH rate limits here are per-user-id, which IS the §8.B intent.  No deviation
flag required beyond the pre-existing D2 documented in the iam router.

DECISION FLAG §8-ROUTES-D1
---------------------------
The ``rate_limit`` decorator does NOT support ``key="user_id"`` as an explicit parameter;
it achieves per-user keying automatically for authenticated routes via
``request.state.user_id``.  This aligns exactly with the intent in §8.B —
no functional deviation.  Matches pre-existing iam router D2.

Router composition contract (for main.py)
------------------------------------------
Router object:   ``router``
Module path:     ``app.router``
Include call:    ``app.include_router(customer_router)`` (alias in main.py)
Prefix:          ``/api/v1``
Tags:            ``["seller-profile"]``
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app import service as customer_service
from app.exceptions import ProfileNotFoundError
from app.schemas import (
    PatchActiveCategoriesRequest,
    PatchComplianceExtensionRequest,
    PatchProfileRequest,
    RequiredFieldsResponse,
    SellerProfileResponse,
)
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["seller-profile"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /seller-profile  — §8.B.1
# Source: monolith backend/app/modules/customer/router.py:75-95
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/seller-profile",
    response_model=SellerProfileResponse,
    summary="Read current seller profile",
)
async def get_seller_profile(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerProfileResponse:
    """§8.B.1 — return the seller's current profile.

    Returns 200 + ``SellerProfileResponse`` when a profile row exists.
    Returns 404 ``customer.profile.not_found`` when no row exists (first-time
    seller); the frontend interprets this as a redirect to the onboarding wizard.

    No per-route rate limit (per-IP DDoS floor only, per §8.B.1).
    """
    profile = await customer_service.get_profile_or_none(user.user_id, db=db)
    if profile is None:
        raise ProfileNotFoundError()
    return SellerProfileResponse.model_validate(profile)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PATCH /seller-profile  — §8.B.2
# Source: monolith backend/app/modules/customer/router.py:101-123
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/seller-profile",
    response_model=SellerProfileResponse,
    summary="Partial update of base profile fields (Legal Metrology + country_of_origin)",
)
@rate_limit(scope="profile_update", limit=60, window=3600)
@audit_event("customer.profile_updated")
async def patch_seller_profile(
    payload: PatchProfileRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerProfileResponse:
    """§8.B.2 — upsert the 9 Legal Metrology fields + country_of_origin.

    Subset semantics: only fields present in the payload are updated.
    First PATCH creates the row; subsequent PATCHes update.
    Recomputes ``onboarding_complete`` on every call.

    Rate limit: 60/h per user_id (§8.B.2).
    Raises 422 on pincode regex failure (Pydantic constraint or service defensive check).
    """
    profile = await customer_service.upsert_profile(user.user_id, payload, db=db)
    return SellerProfileResponse.model_validate(profile)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PATCH /seller-profile/active-categories  — §8.B.3
# Source: monolith backend/app/modules/customer/router.py:129-152
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/seller-profile/active-categories",
    response_model=SellerProfileResponse,
    summary="Replace the seller's active super-category declarations entirely",
)
@rate_limit(scope="active_categories", limit=60, window=3600)
@audit_event("customer.active_categories.updated")
async def patch_active_categories(
    payload: PatchActiveCategoriesRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerProfileResponse:
    """§8.B.3 — replace active_super_categories entirely (NOT additive).

    Every super_id in the payload is validated against the global ``categories.super_id``
    distinct set (cached read via ``core/cache.py``).  Unknown super_id(s) →
    422 ``validation.super_category.unknown``.

    Rate limit: 60/h per user_id (§8.B.3).
    """
    profile = await customer_service.set_active_categories(
        user.user_id, payload.active_super_categories, db=db
    )
    return SellerProfileResponse.model_validate(profile)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PATCH /seller-profile/compliance/{super_id}  — §8.B.4
# Source: monolith backend/app/modules/customer/router.py:158-192
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/seller-profile/compliance/{super_id}",
    response_model=SellerProfileResponse,
    summary="Set the compliance extension payload for one declared super-category",
)
@rate_limit(scope="compliance_update", limit=60, window=3600)
@audit_event("customer.compliance_updated")
async def patch_compliance_extension(
    super_id: str,
    payload: PatchComplianceExtensionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerProfileResponse:
    """§8.B.4 — JSONB-merge the compliance extension for one super-category.

    ``super_id`` is a path param (string — matches Meesho's string super_id convention).

    Raises 404 ``customer.super_category.not_declared`` when the super_id is not in
    ``active_super_categories``.
    Raises 422 ``customer.compliance.missing_fields`` when required keys are absent.

    Rate limit: 60/h per user_id (§8.B.4).
    """
    # Extract the raw payload dict from the PatchComplianceExtensionRequest model.
    # ``model_dump()`` with no exclusions returns only the declared fields, but since
    # ``extra="allow"``, we use ``model_extra`` union with ``model_fields_set`` to
    # preserve any forward-compat optional keys sent by the client.
    raw_payload: dict[str, Any] = {
        **payload.model_dump(),
        **(payload.model_extra or {}),
    }
    profile = await customer_service.set_compliance_extension(
        user.user_id, super_id, raw_payload, db=db
    )
    return SellerProfileResponse.model_validate(profile)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /seller-profile/required-fields  — §8.B.5
# Source: monolith backend/app/modules/customer/router.py:198-220
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/seller-profile/required-fields",
    response_model=RequiredFieldsResponse,
    summary="Return all required fields for the onboarding wizard",
)
async def get_required_fields(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequiredFieldsResponse:
    """§8.B.5 — drive the frontend onboarding wizard.

    Returns a ``RequiredFieldsResponse`` containing:

    - ``base_fields``: the 10 always-required fields as §5A.C FieldSpec dicts.
    - ``extension_fields``: per-declared-super_id compliance fields.
    - ``completed``: dot-notation path → bool completion map.

    Response is cached 60 s per §4.D (key includes user_id + CACHE_VERSION).
    Invalidated on any PATCH to the profile.

    No per-route rate limit (per-IP DDoS floor only; response is cached — §8.B.5).
    """
    return await customer_service.get_required_fields(user.user_id, db=db)


__all__ = ["router"]
