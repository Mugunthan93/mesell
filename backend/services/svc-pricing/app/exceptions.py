"""``pricing`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §12.G (LOCKED 2026-06-05).  Vendored byte-for-byte
into svc-pricing (spec §3.A); ``MeesellError`` resolves to the vendored
``app.core.errors`` in this service.

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

Two pricing-specific IDs live in ``app/i18n/messages_en.py`` per §5A.I
(already shipped with the §5A construction):

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
PricingError (base)                           —        — (inherits MeesellError defaults)
InvalidPriceInputError                        400      validation.price.invalid_input
CommissionMissingError                        422      pricing.commission.missing
============================================  =======  ==========================================

DECISION FLAG §12-PRICING-D3
----------------------------
§12.G prose enumerates 3 exception classes (PricingError base +
:class:`InvalidPriceInputError` + :class:`CommissionMissingError`).  The
master prompt's "5 exception classes" tally appears to count the 5 i18n
validation_message_id keys (which include the 3 alert codes — but alerts
are NOT raised as exceptions per §12.F; they are domain dataclass values
embedded in the 200 OK response).  Implementing per spec: 3 classes.

DECISION FLAG §12-PRICING-D3a — 3-segment validation_message_id convention
-------------------------------------------------------------------------
§12.G prose lists ``pricing.commission_missing`` (2-segment shorthand) but
the §5A.H regex locks 3-segment and ``app/i18n/messages_en.py`` ships the
canonical 3-segment ID ``pricing.commission.missing``.  Wire to the
canonical 3-segment IDs already registered — same precedent as §7 iam
(memory D2), §8 customer (memory D5), §9 category (services-builder D3),
§10 catalog (D3).
"""

from __future__ import annotations

from app.core.errors import MeesellError


class PricingError(MeesellError):
    """Base class for ``pricing`` module failures. Never raised directly."""

    code = "pricing.base"


class InvalidPriceInputError(PricingError):
    """Service-layer business-rule check beyond Pydantic validation.

    Pydantic catches ``input_cost <= 0`` and ``target_margin_pct < 0`` at
    the route boundary (the schema's :class:`~pydantic.Field` constraints
    do this).  This class is held for forward-compatibility: V1.5 may add
    cross-field rules such as
    ``target_margin_pct > some-function-of-commission`` that Pydantic
    cannot express declaratively.

    V1 never raises this exception in practice — it exists as a slot in
    the contract so the §4.F error envelope and the §5A.H i18n key are
    pre-registered before V1.5 lands.
    """

    code = "pricing.invalid_price_input"
    status_code = 400
    validation_message_id = "validation.price.invalid_input"

    def __init__(self, detail: str = "Please enter a valid price.") -> None:
        super().__init__(detail=detail)


class CommissionMissingError(PricingError):
    """The resolved category has no usable commission for pricing.

    Raised when :func:`category.service.get_commission` returns
    ``Decimal("0.00")`` — the §9 cross-module surface signals "missing /
    unseeded commission" via a zero return value (per the §9.C docstring:
    "categories without a seeded commission have no pricing surface in
    V1; the pricing service fails over to a default").

    DECISION FLAG §12-PRICING-D1
    ----------------------------
    §12.B.1 step 5 prose says "If ``None`` → raise CommissionMissingError"
    but the §9 implementation (Wave 3 LOCKED) returns
    ``Decimal("0.00")`` for the missing case, never ``None``.  Pricing
    treats the zero-return as the missing-signal per §9's documented
    intent.  A legitimately 0% commission category does not exist on
    Meesho per §9 prose, so the conflation is safe in V1; V1.5 can widen
    the §9 surface with a separate ``get_commission_or_none`` if a
    legitimately 0% category is ever seeded.
    """

    code = "pricing.commission_missing"
    status_code = 422
    validation_message_id = "pricing.commission.missing"

    def __init__(self, detail: str = "Commission rate is missing for this category.") -> None:
        super().__init__(detail=detail)


__all__ = [
    "PricingError",
    "InvalidPriceInputError",
    "CommissionMissingError",
]
