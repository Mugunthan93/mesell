"""category-svc HTTP shim — re-exports the ``category_service`` symbol surface.

Shims the 1 cross-module method pricing consumes from category (spec §0.5):

* :func:`get_commission` ← category/service.py:548
  → ``GET /internal/categories/{id}/commission`` (returns the commission
  ``Decimal``).

Re-exports :class:`CategoryNotFoundError` because the monolith
``category.service.get_commission`` raises it (category/service.py:560) when no
category row exists; in svc-pricing that maps to a 404 contract response from
the commission route.

CONTRACT — get_commission NEVER returns None (frozen — callee docstring :553-555)
---------------------------------------------------------------------------------
The monolith ``get_commission`` returns a ``Decimal`` ALWAYS — categories
without a seeded commission return ``Decimal("0.00")`` (the unseeded signal),
NEVER ``None`` (category/service.py:562-566).  The pricing service treats the
``0.00`` return as the "missing commission" signal and raises
:class:`CommissionMissingError` (service.py:168-169).  This shim preserves that
contract EXACTLY: it deserialises the JSON ``commission_pct`` string into a
``Decimal`` and NEVER returns ``None``.

CONTRACT ITEM for Sub-Plan F / category (NEW vs MS-A — must implement):
``GET /internal/categories/{id}/commission`` returns ``200`` with body
``{"commission_pct": "<decimal>"}`` (a decimal STRING, e.g. ``"15.00"`` or
``"0.00"`` for unseeded) — NEVER ``null`` — and ``404``
(``category.lookup.not_found``) when the category row does not exist.

``get_commission`` accepts the monolith call-site signature
``get_commission(category_id, db=db)`` (service.py:165) — ``db`` is accepted +
IGNORED (HTTP shim), so the call site is byte-for-byte unchanged.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Typed error raised on the monolith's 4xx contract response ──────────────
class CategoryNotFoundError(MeesellError):
    """Mirror of ``category.exceptions.CategoryNotFoundError`` — 404.

    Raised by the monolith ``category.service.get_commission`` when no category
    row exists (category/service.py:560).  In svc-pricing this maps to a 404
    contract response from ``GET /internal/categories/{id}/commission``.
    """

    code = "category.not_found"
    status_code = 404
    validation_message_id = "category.lookup.not_found"

    def __init__(self, detail: str = "Category not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed method (re-export the category_service symbol surface) ──────────
async def get_commission(
    category_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> Decimal:
    """Category commission ← ``GET /internal/categories/{id}/commission``.

    Returns the ``commission_pct`` as a :class:`~decimal.Decimal`.  NEVER
    returns ``None`` — the frozen contract guarantees a decimal STRING on the
    200 body (``"0.00"`` for unseeded categories — the pricing service treats
    that zero as the missing-commission signal and raises
    :class:`CommissionMissingError`).  Raises :class:`CategoryNotFoundError` on
    a 404 contract response.
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/categories/{category_id}/commission",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CategoryNotFoundError() from exc
        raise

    commission = (payload or {}).get("commission_pct")
    if commission is None:
        # The frozen contract guarantees a non-null decimal string; treat a
        # missing key as the unseeded signal (Decimal("0.00")) so this shim
        # NEVER returns None — preserving the callee contract exactly.
        return Decimal("0.00")
    # Construct from str() so a JSON number or string both deserialise to an
    # exact Decimal (no float intermediary — frozen Decimal contract §1).
    return Decimal(str(commission))


__all__ = [
    "CategoryNotFoundError",
    "get_commission",
]
