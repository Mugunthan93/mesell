"""``catalog`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §10.G (LOCKED 2026-06-05).

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

Five catalog-specific IDs already live in ``app/i18n/messages_en.py`` per
§5A.I (the strings shipped with the §5A construction):

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
CatalogError (base)                           —        — (inherits MeesellError defaults)
ProductNotFoundError                          404      catalog.product.not_found
CatalogNotFoundError                          404      catalog.catalog.not_found
ValidationFailedError                         422      validation.<field>.<constraint> (dynamic)
DraftNotFoundError                            204      — (sentinel; router converts to 204)
AutofillFailedError                           500      catalog.autofill.internal_error
============================================  =======  ==========================================

Plus :class:`PlanLimitExceededError` is consumed FROM
:mod:`app.core.plan_guard` — catalog does NOT define its own plan-limit
exception (the cross-cutting one in core/plan_guard.py is the contract).

DECISION FLAG §10-CATALOG-D3
----------------------------
§10.G prose lists the 5 ``validation_message_id`` IDs as 2-segment
shorthand (``catalog.product_not_found``).  The §5A.H regex locks
3-segment.  ``app/i18n/messages_en.py`` ships the canonical 3-segment IDs
(``catalog.product.not_found``, ``catalog.catalog.not_found``,
``catalog.autofill.internal_error``).  Wire to the canonical 3-segment
IDs already registered — same precedent as §7 iam (memory D2), §8
customer (memory D5), §9 category (services-builder D3).
"""

from __future__ import annotations

from typing import Any

from app.core.errors import MeesellError


class CatalogError(MeesellError):
    """Base class for ``catalog`` module failures. Never raised directly."""

    code = "catalog.base"


class ProductNotFoundError(CatalogError):
    """Raised by :func:`catalog.service.assert_product_ownership` and every
    downstream service method when a product:

    * does not exist, OR
    * is owned by a different ``user_id``, OR
    * has ``deleted_at IS NOT NULL`` (soft-deleted).

    All three cases collapse to the same envelope so the API does NOT leak
    existence-vs-ownership of soft-deleted resources to non-owners.

    Cross-module surface — ``image``, ``pricing``, ``dashboard``, and
    ``export`` all see this exception bubble up through
    :func:`catalog.service.assert_product_ownership` per §10.C + §2.D.
    """

    code = "catalog.product_not_found"
    status_code = 404
    validation_message_id = "catalog.product.not_found"

    def __init__(self, detail: str = "Product not found.") -> None:
        super().__init__(detail=detail)


class CatalogNotFoundError(CatalogError):
    """Raised by :func:`catalog.service.create_product` when the caller
    passes a ``catalog_id`` that is not owned by the seller.

    Per §10.B.1 mapping: 404 / ``catalog.catalog.not_found``.  Same
    leak-protection rationale as :class:`ProductNotFoundError` — we do not
    distinguish "no such catalog" from "exists but owned by someone else".
    """

    code = "catalog.catalog_not_found"
    status_code = 404
    validation_message_id = "catalog.catalog.not_found"

    def __init__(self, detail: str = "Catalog not found.") -> None:
        super().__init__(detail=detail)


class ValidationFailedError(CatalogError):
    """Raised by :func:`catalog.service.patch_product` (and the readiness
    transition inside it) when one or more fields fail schema-driven
    validation per §5A.C + §5A.D.

    Per §10.G: ``validation_message_id`` is DYNAMIC — set per-field per
    §5A.H convention.  Examples:

      * ``validation.fields.unknown_key`` — unknown canonical_name.
      * ``validation.<canonical>.too_long`` — text overflow.
      * ``validation.<canonical>.invalid_enum_value`` — enum miss.
      * ``validation.completeness.missing_compulsory`` — readiness gate.

    When multiple violations are collected, the envelope's
    ``validation_message_id`` carries the FIRST and ``details: list[str]``
    carries the remaining IDs — matches the §4.F MeesellError envelope
    shape via the ``detail`` field.

    Attribute ``details`` is the trailing-violation list (canonical names
    plus optional ``: <constraint>`` suffixes) so callers + tests can
    enumerate without re-parsing.
    """

    code = "catalog.validation_failed"
    status_code = 422
    validation_message_id = "validation.fields.unknown_key"  # default; usually overridden

    def __init__(
        self,
        *,
        validation_message_id: str,
        detail: str = "One or more fields failed validation.",
        details: list[str] | None = None,
    ) -> None:
        super().__init__(
            validation_message_id=validation_message_id,
            detail=detail,
        )
        self.details: list[str] = list(details or [])

    def to_envelope_extras(self) -> dict[str, Any]:
        """Helper for tests + structured-logging callers.

        The §4.F handler does NOT consume this — it's a convenience for
        the unit tests in §10.J #2 that need to inspect the trailing
        violations.
        """
        return {"details": list(self.details)}


class DraftNotFoundError(CatalogError):
    """Sentinel — caught by the router and converted to 204 (no body).

    NOT surfaced through the §4.F envelope — instead the router branches
    on ``draft is None`` from :func:`service.get_draft` and returns an
    empty 204 ``Response``.  This subclass exists so the inventory in
    §10.G enumerates 6 catalog exceptions, even though the exception is
    not raised in practice (the service returns ``None`` and the router
    short-circuits — see §10.B.6 flow).

    Defensive raises in the service layer ARE allowed; the router treats
    the raise identically to the ``None`` return — both produce 204.
    """

    code = "catalog.draft_not_found"
    status_code = 204
    validation_message_id = "catalog.draft.missing"

    def __init__(self, detail: str = "No draft snapshot for this product.") -> None:
        super().__init__(detail=detail)


class AutofillFailedError(CatalogError):
    """Raised ONLY for unrecoverable §6A failures NOT covered by the
    graceful fallback contract.

    Per §10.G: ``BudgetExceededError`` (and Layer-2 retry exhaustion)
    produce a 200 ``AutofillResponse(suggestions={}, applied={},
    fallback_offered=True)`` via :func:`catalog.service.autofill_product`
    — that path NEVER reaches this exception.

    Reaching this exception means either an SDK bug or a bug in the §6A.E
    guardrail retry budget; P1 page.
    """

    code = "catalog.autofill_internal_error"
    status_code = 500
    validation_message_id = "catalog.autofill.internal_error"

    def __init__(self, detail: str = "Auto-fill ran into an internal problem.") -> None:
        super().__init__(detail=detail)


__all__ = [
    "AutofillFailedError",
    "CatalogError",
    "CatalogNotFoundError",
    "DraftNotFoundError",
    "ProductNotFoundError",
    "ValidationFailedError",
]
