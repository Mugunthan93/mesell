"""customer-svc HTTP shim — re-exports the ``customer_service`` symbol surface.

catalog's ``service.py`` imports this module ``as customer_service`` so the 2
outbound call sites stay BYTE-FOR-BYTE identical (§16.G).  The 2 shimmed methods
mirror the monolith ``app.modules.customer.service`` surface catalog consumes
(SUB_PLAN_0H §H5):

* :func:`assert_eligible_for_super_id` ← service.py:406 (create_product
  PROFILE_INCOMPLETE_FOR_CATEGORY gate)
  → ``GET /internal/seller-profile/{user_id}/eligibility?super_id=...``
* :func:`get_compliance_block` ← service.py:839 (get_preview compliance block)
  → ``GET /internal/seller-profile/{user_id}/compliance-block`` [MS-A/MS-E
  FROZEN — customer-svc (MS-3) already serves it]

Target pod (SUB_PLAN_0H §H5)
----------------------------
customer-svc is an extracted service by MS-5, so these shims point at
``settings.CUSTOMER_SVC_BASE_URL`` (the customer-svc ClusterIP), NOT the
monolith.

Verified against the as-built customer-svc internal router
(``backend/services/svc-customer/app/internal_routes.py``): BOTH paths are
served — ``/seller-profile/{user_id}/compliance-block`` (200 ``asdict``, 404 on
no profile) and ``/seller-profile/{user_id}/eligibility?super_id=...`` (200
``{}`` on success, 422 ``customer.profile_incomplete_for_category`` on failure).
This RESOLVES SUB_PLAN_0H Open Q #2 (customer-svc serves both).  NOTE: the
eligibility path uses a ``?super_id=`` QUERY param (not a ``/{super_id}`` path
param as the spec sketch suggested) — matched here to the as-built contract.

§16.D domain-exchange currency
------------------------------
``get_compliance_block`` returns a VENDORED :class:`ComplianceBlock` dataclass
(the 10 Legal-Metrology fields, declaration order) deserialized from the
customer-svc JSON body — catalog's ``get_preview`` reads it as object
attributes (``block.manufacturer_name`` …).  This mirrors the MS-A pattern on
export's side.

Call-site signature parity
--------------------------
Both methods accept the monolith call-site signature (``db=db`` kwarg) — the
``db`` arg is accepted and IGNORED (HTTP shim), so the preserved ``service.py``
call sites are byte-for-byte unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json
from app.shared.config import settings


# ── Vendored §16.D domain currency — the 10-field standard compliance block ──
@dataclass(frozen=True)
class ComplianceBlock:
    """Vendored mirror of ``customer.domain.ComplianceBlock`` (the 9 standard
    Legal-Metrology fields + ``country_of_origin``).  catalog's ``get_preview``
    reads these 10 attributes.  Declaration order matches customer-svc's
    ``asdict`` serialization.
    """

    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str


# ── Typed errors raised on the customer-svc 4xx contract responses ──────────
class ProfileNotFoundError(MeesellError):
    """Mirror of ``customer.exceptions.ProfileNotFoundError`` — 404 when no
    seller profile row exists (``/compliance-block``).
    """

    code = "customer.profile_not_found"
    status_code = 404
    validation_message_id = "customer.profile.not_found"

    def __init__(self, detail: str = "Seller profile not found.") -> None:
        super().__init__(detail=detail)


class ProfileIncompleteForCategoryError(MeesellError):
    """Mirror of ``customer.exceptions.ProfileIncompleteForCategoryError`` —
    422 when the seller is not eligible for the category's ``super_id``
    (``/eligibility``).
    """

    code = "customer.profile_incomplete_for_category"
    status_code = 422
    validation_message_id = "customer.profile.incomplete_for_category"

    def __init__(
        self, detail: str = "Seller profile incomplete for this category."
    ) -> None:
        super().__init__(detail=detail)


def _base_url() -> str:
    """The customer-svc ClusterIP base URL (real sibling pod by MS-5)."""
    return settings.CUSTOMER_SVC_BASE_URL


# ── Shimmed methods (re-export the customer_service symbol surface) ──────────
async def assert_eligible_for_super_id(
    user_id: UUID,
    super_id: str,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> None:
    """Eligibility gate ← ``GET /internal/seller-profile/{uid}/eligibility?super_id=``.

    Returns ``None`` on success (200 ``{}``); raises
    :class:`ProfileIncompleteForCategoryError` on a 422 contract response
    (byte-for-byte parity with the monolith
    ``customer.service.assert_eligible_for_super_id`` — used at service.py:406).
    """
    import httpx

    try:
        await request_json(
            "GET",
            f"/internal/seller-profile/{user_id}/eligibility",
            base_url=_base_url(),
            params={"super_id": str(super_id)},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            raise ProfileIncompleteForCategoryError() from exc
        if exc.response.status_code == 404:
            raise ProfileNotFoundError() from exc
        raise


async def get_compliance_block(
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> ComplianceBlock:
    """Compliance block ← ``GET /internal/seller-profile/{uid}/compliance-block``.

    Returns the vendored :class:`ComplianceBlock` (10 fields) deserialized from
    the customer-svc JSON body (used at service.py:839 — the catalog preview
    composes the §5A.F compliance block from its attributes).  Raises
    :class:`ProfileNotFoundError` on a 404 contract response.  NOTE: catalog's
    ``get_preview`` wraps this call in a tolerant ``try/except Exception`` and
    falls back to an empty compliance block — so a missing profile degrades the
    preview gracefully (it does not fail the request).
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/seller-profile/{user_id}/compliance-block",
            base_url=_base_url(),
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProfileNotFoundError() from exc
        raise

    data = payload if isinstance(payload, dict) else {}
    return ComplianceBlock(
        manufacturer_name=data.get("manufacturer_name"),
        manufacturer_address=data.get("manufacturer_address"),
        manufacturer_pincode=data.get("manufacturer_pincode"),
        packer_name=data.get("packer_name"),
        packer_address=data.get("packer_address"),
        packer_pincode=data.get("packer_pincode"),
        importer_name=data.get("importer_name"),
        importer_address=data.get("importer_address"),
        importer_pincode=data.get("importer_pincode"),
        country_of_origin=data.get("country_of_origin"),
    )


__all__ = [
    "ComplianceBlock",
    "ProfileIncompleteForCategoryError",
    "ProfileNotFoundError",
    "assert_eligible_for_super_id",
    "get_compliance_block",
]
