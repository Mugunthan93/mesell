"""customer-svc HTTP shim — re-exports the ``customer_service`` symbol surface.

Shims 1 of the 6 cross-module methods export consumes (spec §0.4):

* :func:`get_compliance_block` ← customer/service.py:648
  → ``GET /internal/seller-profile/{user_id}/compliance-block``.

Deserializes the monolith JSON into the VENDORED :class:`app.domain.ComplianceBlock`
dataclass (spec §3.A — the §16 "domain exchange currency": the monolith
``export.domain`` imported ``customer.domain.ComplianceBlock``; in svc-export
that became a vendored local dataclass, and THIS shim hydrates it from JSON).

Matches the ``service.py`` call site ``get_compliance_block(user_id, db)``
(positional ``db``, accepted + IGNORED — HTTP shim).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json
from app.domain import ComplianceBlock


# ── Typed error raised on the monolith's 4xx contract response ──────────────
class ProfileNotFoundError(MeesellError):
    """Mirror of ``customer.exceptions.ProfileNotFoundError`` — 404."""

    code = "customer.profile_not_found"
    status_code = 404
    validation_message_id = "customer.profile.not_found"

    def __init__(self, detail: str = "Seller profile not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed method (re-export the customer_service symbol surface) ──────────
async def get_compliance_block(
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> ComplianceBlock:
    """Compliance block ← ``GET /internal/seller-profile/{user_id}/compliance-block``.

    Hydrates the vendored :class:`app.domain.ComplianceBlock` from the monolith
    JSON.  Field shape mirrors ``customer/domain.py:76-94`` (9 LM fields +
    ``country_of_origin``; importer_* fields nullable).
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/seller-profile/{user_id}/compliance-block",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProfileNotFoundError() from exc
        raise

    return ComplianceBlock(
        manufacturer_name=str(payload["manufacturer_name"]),
        manufacturer_address=str(payload["manufacturer_address"]),
        manufacturer_pincode=str(payload["manufacturer_pincode"]),
        packer_name=str(payload["packer_name"]),
        packer_address=str(payload["packer_address"]),
        packer_pincode=str(payload["packer_pincode"]),
        importer_name=payload.get("importer_name"),
        importer_address=payload.get("importer_address"),
        importer_pincode=payload.get("importer_pincode"),
        country_of_origin=str(payload["country_of_origin"]),
    )


__all__ = [
    "ProfileNotFoundError",
    "get_compliance_block",
]
