"""svc-dashboard English message registry — vendored SUBSET.

Carries ONLY:

* the 1 dashboard module-specific ID (raised by ``app.exceptions`` /
  the Pydantic ``DashboardQuery`` validator): ``validation.dashboard.invalid_pagination``;
* the cross-cutting IDs the vendored core layer raises:
  ``tenancy.cross_user_access`` (core/tenancy), ``rate_limit.exceeded``
  (core/middleware/rate_limit_mw), the 3 auth IDs (core/auth), and
  ``server.internal_error`` (the generic-exception fallback).

Every key matches the §5A.H locked regex
``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$`` EXCEPT ``server.internal_error``
which is a 2-segment dynamic envelope value (not a true registry key — same
§5A D1 precedent as the monolith; it falls through to the supplied fallback
prose in ``core/errors``).
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── §13 dashboard (module-specific) ──────────────────────────────────
    "validation.dashboard.invalid_pagination": (
        "Page or limit is out of range."
    ),
    # ── cross-cutting (raised by the vendored core layer) ────────────────
    "tenancy.cross_user_access": "You do not have access to this resource.",
    "rate_limit.exceeded": "Too many requests. Please slow down and try again.",
    "auth.token_missing": "Authorization token missing or malformed.",
    "auth.token_expired": "Your session has expired. Please sign in again.",
    "auth.user_not_found": "Authenticated user no longer exists.",
}


__all__ = ["VALIDATION_MESSAGES"]
