"""customer-svc HTTP shim — re-exports the ``customer_service`` symbol surface.

Shims the 1 cross-module method dashboard consumes from customer (spec §0.4):

* :func:`get_onboarding_completeness` ← customer/service.py:682
  → ``GET /internal/seller-profile/{user_id}/onboarding-completeness``.

**Method name is ``get_onboarding_completeness``, NOT ``get_profile_completeness``**
(SUB_PLAN_0B §0.5 PLAN-TEXT CORRECTION — a wrong name is a re-dispatch trigger).

The call site is byte-for-byte preserved (``dashboard/service.py:84``)::

    await customer_service.get_onboarding_completeness(user_id=user_id, db=db)

so :func:`get_onboarding_completeness` accepts ``user_id`` + ``db`` exactly.
``db`` is accepted and IGNORED (HTTP shim).  ``user_id`` IS placed in the URL
path; the forwarded JWT lets the callee re-verify the tenant matches the path
``user_id`` (frozen contract, SUB_PLAN_0B §"Shim 2").

Deserializes the monolith JSON into the VENDORED :class:`ProfileCompleteness`
dataclass (5 fields, mirror of ``customer/domain.py:98``).

NOTE (spec §3.A): the monolith does NOT yet expose this ``/internal/*``
endpoint — customer extracts at MS-3/MS-E.  That is expected; this shim is
built against the FROZEN contract and is mock-tested (``httpx.MockTransport``).
Live wiring happens at the founder-gated cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Deserialization target (mirror customer/domain.py:98) ───────────────────
@dataclass(frozen=True)
class ProfileCompleteness:
    """Mirror of ``customer.domain.ProfileCompleteness`` (customer/domain.py:98).

    Consumed by ``dashboard.service._compose_response`` for the completeness
    badge.  ``base_total_count`` is always 10 (9 LM fields + country_of_origin)
    per §8.F.
    """

    base_complete_count: int
    base_total_count: int  # always 10 (9 LM fields + country_of_origin)
    extension_complete_count: int
    extension_total_count: int  # depends on active_super_categories
    onboarding_complete: bool  # mirrors seller_profile.onboarding_complete


# ── Typed error raised on the monolith's 4xx contract response ──────────────
class ProfileNotFoundError(MeesellError):
    """Mirror of ``customer.exceptions.ProfileNotFoundError`` — 404.

    NOTE: ``get_onboarding_completeness`` does NOT 404 on a missing profile —
    a first-time seller with no profile row returns the all-zero / 10-base
    shape at 200 (frozen contract, SUB_PLAN_0B §"Shim 2").  This type exists
    for shim-contract parity with the customer ``/internal/*`` error surface.
    """

    code = "customer.profile_not_found"
    status_code = 404
    validation_message_id = "customer.profile.not_found"

    def __init__(self, detail: str = "Seller profile not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed method (re-export the customer_service symbol surface) ──────────
async def get_onboarding_completeness(
    *,
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> ProfileCompleteness:
    """Onboarding completeness ← ``GET /internal/seller-profile/{user_id}/onboarding-completeness``.

    Hydrates the vendored :class:`ProfileCompleteness` from the monolith JSON
    (5 fields).  The forwarded JWT lets the callee re-verify the tenant matches
    the path ``user_id``.
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/seller-profile/{user_id}/onboarding-completeness",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProfileNotFoundError() from exc
        raise

    return ProfileCompleteness(
        base_complete_count=int(payload["base_complete_count"]),
        base_total_count=int(payload["base_total_count"]),
        extension_complete_count=int(payload["extension_complete_count"]),
        extension_total_count=int(payload["extension_total_count"]),
        onboarding_complete=bool(payload["onboarding_complete"]),
    )


__all__ = [
    "ProfileCompleteness",
    "ProfileNotFoundError",
    "get_onboarding_completeness",
]
