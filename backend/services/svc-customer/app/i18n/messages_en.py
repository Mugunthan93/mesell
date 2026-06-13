"""svc-customer English message registry — vendored SUBSET.

Carries:

* the 6 §8.G customer module-specific IDs raised by ``app.exceptions``:
  ``validation.pincode.invalid_format``, ``validation.super_category.unknown``,
  ``customer.profile.not_found``, ``customer.super_category.not_declared``,
  ``customer.compliance.missing_fields``,
  ``customer.profile.incomplete_for_category``;
* ``validation.body.malformed_json`` — referenced in
  ``service._BASE_FIELD_DEFINITIONS`` as a base-field ``validation_message_id``;
* the cross-cutting IDs the vendored core layer raises:
  ``tenancy.cross_user_access`` (core/tenancy), ``rate_limit.exceeded``
  (core/middleware/rate_limit_mw), the 3 auth IDs (core/auth), and
  ``server.internal_error`` (the generic-exception fallback).

Every key matches the §5A.H locked regex
``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$`` EXCEPT ``server.internal_error``
(a 2-segment dynamic envelope value, not a true registry key — same §5A D1
precedent as the monolith + svc-dashboard; it falls through to the supplied
fallback prose in ``core/errors``).  The 3 auth IDs follow the svc-dashboard
2-segment convention (the vendored ``core/auth`` raises them verbatim).
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── §8 customer (6 module-specific IDs) ──────────────────────────────
    "validation.pincode.invalid_format": (
        "Please enter a valid 6-digit pincode."
    ),
    "validation.super_category.unknown": (
        "We don't recognise that category group. Please pick from the list."
    ),
    "customer.profile.not_found": (
        "We couldn't find your seller profile. Please complete onboarding."
    ),
    "customer.super_category.not_declared": (
        "Please select your seller category group before listing this product."
    ),
    "customer.compliance.missing_fields": (
        "Some compliance details are missing from your profile. "
        "Please complete them to continue."
    ),
    "customer.profile.incomplete_for_category": (
        "Your seller profile is incomplete for this category. "
        "Please update your profile to list here."
    ),
    # ── base-field validation id (service._BASE_FIELD_DEFINITIONS) ───────
    "validation.body.malformed_json": (
        "The data we received couldn't be read. Please try again."
    ),
    # ── cross-cutting (raised by the vendored core layer) ────────────────
    "tenancy.cross_user_access": "You do not have access to this resource.",
    "rate_limit.exceeded": "Too many requests. Please slow down and try again.",
    "auth.token_missing": "Authorization token missing or malformed.",
    "auth.token_expired": "Your session has expired. Please sign in again.",
    "auth.user_not_found": "Authenticated user no longer exists.",
}


__all__ = ["VALIDATION_MESSAGES"]
