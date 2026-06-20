"""``pricing`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §12.G (LOCKED 2026-06-05) as superseded by the
**W2 Price Calculator rework (census-confirmed settlement model, 2026-06-19)**.

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
PricingError (base)                           —        — (inherits MeesellError defaults)
InvalidPriceInputError                        400      validation.price.invalid_input
CategoryPricingUnavailableError               422      pricing.category.no_pricing_data
============================================  =======  ==========================================

W2 CHANGES vs #285
------------------
* ``CommissionMissingError`` REMOVED — commission is now an optional override
  (default 0 from lookup); there is no missing-commission failure mode.
* ``CategoryPricingUnavailableError`` ADDED — wraps
  :class:`~app.modules.pricing.pricing_lookup.UnknownCategoryError` raised
  when the product's ``meesho_leaf_id`` is absent from the pricing lookup.
  A seeded category with no pricing row is a data-integrity 4xx, NOT a 500.
  The router catches ``UnknownCategoryError`` and re-raises this class so the
  §4.F ``MeesellError`` handler emits the clean 422 envelope
  (``pricing.category.no_pricing_data``).
"""

from __future__ import annotations

from app.core.errors import MeesellError


class PricingError(MeesellError):
    """Base class for ``pricing`` module failures. Never raised directly."""

    code = "pricing.base"


class InvalidPriceInputError(PricingError):
    """Service-layer business-rule check beyond Pydantic validation.

    Pydantic catches ``selling_price <= 0`` and the percentage-range
    constraints at the route boundary.  This class is held for cross-field
    rules the schema cannot express declaratively (e.g. a deduction override
    combination that yields a non-finite result).
    """

    code = "pricing.invalid_price_input"
    status_code = 400
    validation_message_id = "validation.price.invalid_input"

    def __init__(self, detail: str = "Please enter a valid price.") -> None:
        super().__init__(detail=detail)


class CategoryPricingUnavailableError(PricingError):
    """The product's ``meesho_leaf_id`` is absent from the pricing lookup.

    A seeded Meesho category that has no entry in ``meesho_pricing_lookup.json``
    is a data-integrity gap — the static lookup is refreshed monthly alongside
    the category scrape.  This is a 422 (Unprocessable Entity), NOT a 500:
    the request itself is well-formed but cannot be processed with the current
    data state.

    The router catches
    :class:`~app.modules.pricing.pricing_lookup.UnknownCategoryError` and
    re-raises this class so the §4.F ``_meesell_error_handler`` emits the
    locked 422 envelope with ``code="pricing.category.no_pricing_data"``.
    """

    code = "pricing.category.no_pricing_data"
    status_code = 422
    validation_message_id = "pricing.category.no_pricing_data"

    def __init__(
        self,
        meesho_leaf_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        if detail is None:
            detail = (
                f"No pricing data found for category {meesho_leaf_id!r}. "
                "The pricing lookup is refreshed monthly — try again after the next "
                "scraper run or contact support."
                if meesho_leaf_id
                else "No pricing data available for this product category."
            )
        super().__init__(detail=detail)


__all__ = [
    "PricingError",
    "InvalidPriceInputError",
    "CategoryPricingUnavailableError",
]
