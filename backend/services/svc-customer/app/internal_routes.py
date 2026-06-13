"""INBOUND ``/internal/*`` provider routes — the 3 FROZEN customer contracts.

customer is the CALLEE for 3 cross-module surfaces (spec §3.A / §3.B / §9).
This module owns the SERVER side: each handler invokes the byte-for-byte
service method and serialises the EXACT frozen JSON the deployed caller shims
expect.  The api-routes-builder mounts this router (Phase B) alongside the 5
public routes; the service-builder owns the handler logic + the frozen
serialization here.

Internal-network trust (§3.A): these routes carry the user JWT forwarded by the
caller's ``_transport`` (``Authorization`` bearer) + the ``X-Request-ID``.  The
vendored ``get_current_user`` dependency re-verifies the JWT locally and proves
the tenant.  ``user_id`` is in the path; the forwarded JWT lets the callee
re-verify the tenant matches the path ``user_id``.

The 3 FROZEN contracts
----------------------
1. ``GET /internal/seller-profile/{user_id}/compliance-block`` — FROZEN-0A
   (callers: svc-export, monolith-catalog).  Source:
   ``customer/service.py:648 get_compliance_block``.  200 → the 10-field
   :class:`ComplianceBlock` JSON; 404 → ``customer.profile_not_found`` envelope
   (the ``ProfileNotFoundError`` the service raises).

2. ``GET /internal/seller-profile/{user_id}/onboarding-completeness`` —
   FROZEN-0B (caller: svc-dashboard).  Source:
   ``customer/service.py:682 get_onboarding_completeness``.  200 → the 5-field
   :class:`ProfileCompleteness` JSON.  MUST NOT 404 on a missing profile — a
   first-time seller with no profile row returns the all-zero / 10-base shape
   at 200 (the service method already returns this; it never raises).

3. ``GET /internal/seller-profile/{user_id}/eligibility?super_id=...`` —
   frozen-0H (caller: monolith-catalog reverse shim, Phase C).  Source:
   ``customer/service.py:735 assert_eligible_for_super_id``.  200 with an empty
   JSON object ``{}`` on success (the service returns ``None``); 422 with the
   ``ProfileIncompleteForCategoryError`` envelope
   (``customer.profile_incomplete_for_category``) on failure — produced
   automatically by the ``MeesellError`` handler.

The JSON for #1 and #2 is the asdict() of the frozen domain dataclasses, so
the field SET + ORDER mirror ``domain.ComplianceBlock`` (10 fields) /
``domain.ProfileCompleteness`` (5 fields) exactly — zero drift vs the
deserialization targets in the caller shims.
"""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import service as customer_service
from app.core.auth import CurrentUser, get_current_user
from app.shared.database import get_db

internal_router = APIRouter(prefix="/internal", tags=["customer-internal"])


@internal_router.get("/seller-profile/{user_id}/compliance-block")
async def get_compliance_block_internal(
    user_id: UUID,
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FROZEN-0A — the 10-field compliance block.

    404 ``customer.profile_not_found`` when no profile row exists (the
    :class:`ProfileNotFoundError` the service raises bubbles to the
    ``MeesellError`` handler → 404 envelope).
    """
    block = await customer_service.get_compliance_block(user_id, db)
    # asdict() of the frozen ComplianceBlock — 10 fields, in declaration order.
    return asdict(block)


@internal_router.get("/seller-profile/{user_id}/onboarding-completeness")
async def get_onboarding_completeness_internal(
    user_id: UUID,
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FROZEN-0B — the 5-field onboarding completeness.

    MUST NOT 404 — a first-time seller with no profile row returns the
    all-zero / 10-base shape at 200 (the service method returns this and never
    raises).
    """
    completeness = await customer_service.get_onboarding_completeness(user_id, db)
    # asdict() of the frozen ProfileCompleteness — 5 fields, in declaration order.
    return asdict(completeness)


@internal_router.get("/seller-profile/{user_id}/eligibility")
async def assert_eligibility_internal(
    user_id: UUID,
    super_id: str = Query(..., description="The super_id to check eligibility for"),
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """frozen-0H — eligibility assertion for a (user, super_id) pair.

    200 ``{}`` on success (the service ``assert_eligible_for_super_id`` returns
    ``None``).  On failure the service raises
    :class:`ProfileIncompleteForCategoryError` → 422 envelope
    (``customer.profile_incomplete_for_category``) via the ``MeesellError``
    handler.  The Phase-C monolith-catalog reverse shim depends on this exact
    path + query shape.
    """
    await customer_service.assert_eligible_for_super_id(user_id, super_id, db)
    return {}


__all__ = ["internal_router"]
