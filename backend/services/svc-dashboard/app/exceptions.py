"""``dashboard`` module exceptions per §13.G.

All subclass :class:`app.core.errors.MeesellError` so that the §4.F handler
registered in ``app/main.py`` resolves them into the locked error envelope.

V1 ships **one** concrete exception class — :class:`InvalidPaginationError`.
Most failures surfaced by the dashboard endpoint come from the underlying
``catalog`` and ``customer`` services and propagate through cleanly:

* **401 Unauthorized** — raised by ``auth_mw`` per §4.B before the handler
  runs; never reaches dashboard code.
* **404 Not Found (product-level)** — not applicable; dashboard returns a
  list, and an empty list is a valid 200 (NOT 404 — empty seller inventory
  is a real state for first-time sellers).
* **500 Internal Server Error** — raised generically by the §4.F handler if
  ``catalog.service.list_products`` or
  ``customer.service.get_onboarding_completeness`` throws an unexpected
  exception; the underlying module's error code surfaces in the response
  body.

The Pydantic :class:`schemas.DashboardQuery` validator catches ``page < 1``
/ ``limit < 1`` / ``limit > 100`` BEFORE handler execution; the §4.F handler
chain renders the resulting ``ValidationError`` as 400 with
``validation.dashboard.invalid_pagination`` per §5A.D convention.
:class:`InvalidPaginationError` exists for the (rare) service-layer path
that may need to raise it explicitly — kept for parity with §13.G surface.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class DashboardError(MeesellError):
    """Base class for dashboard module failures. Never raised directly."""

    code = "dashboard.error"
    status_code = 500
    validation_message_id = "server.internal_error"


class InvalidPaginationError(DashboardError):
    """Raised when ``page`` / ``limit`` are out of the §13.B locked range.

    Per §13.G (LOCKED 2026-06-05): maps to HTTP 400 with
    ``validation_message_id = "validation.dashboard.invalid_pagination"``.
    The English string lives at
    :data:`app.i18n.messages_en.VALIDATION_MESSAGES["validation.dashboard.invalid_pagination"]`.
    """

    code = "dashboard.pagination.invalid"
    status_code = 400
    validation_message_id = "validation.dashboard.invalid_pagination"

    def __init__(self, detail: str = "Page or limit is out of range.") -> None:
        super().__init__(detail=detail)


__all__ = [
    "DashboardError",
    "InvalidPaginationError",
]
