"""``pricing`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §12.G (LOCKED 2026-06-05) as superseded by the
**§12.M AMENDMENT 2026-06-18 — Price Calculator forward-estimator rework**.

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
PricingError (base)                           —        — (inherits MeesellError defaults)
InvalidPriceInputError                        400      validation.price.invalid_input
============================================  =======  ==========================================

§12.M (4) — ``CommissionMissingError`` REMOVED
----------------------------------------------
Commission is now a seller-entered input (default 4%), so there is no
missing-commission failure mode.  The 422 (``pricing.commission.missing``)
path and the ``category.service.get_commission`` cross-module call are
DELETED.  A negative estimated payout does NOT raise — it returns 200 with
the ``NEGATIVE_PAYOUT`` alert.  ``InvalidPriceInputError`` (400) is
RETAINED for malformed input.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class PricingError(MeesellError):
    """Base class for ``pricing`` module failures. Never raised directly."""

    code = "pricing.base"


class InvalidPriceInputError(PricingError):
    """Service-layer business-rule check beyond Pydantic validation.

    Pydantic catches ``meesho_price <= 0`` / ``input_cost <= 0`` and the
    percentage-range constraints at the route boundary.  This class is held
    for cross-field rules the schema cannot express declaratively (e.g. a
    deduction override combination that yields a non-finite result).
    """

    code = "pricing.invalid_price_input"
    status_code = 400
    validation_message_id = "validation.price.invalid_input"

    def __init__(self, detail: str = "Please enter a valid price.") -> None:
        super().__init__(detail=detail)


__all__ = [
    "PricingError",
    "InvalidPriceInputError",
]
