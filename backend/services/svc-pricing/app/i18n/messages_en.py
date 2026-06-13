"""svc-pricing i18n message registry — vendored SUBSET (spec §3.A).

Carries the 5 pricing ``validation_message_id`` strings VERBATIM from the
monolith ``app.i18n.messages_en`` (lines 163-178):

* ``validation.price.invalid_input``  ← :class:`InvalidPriceInputError`
* ``pricing.commission.missing``      ← :class:`CommissionMissingError`
* ``pricing.alert.low_margin``        ← LOW_MARGIN alert
* ``pricing.alert.high_mrp_multiplier`` ← HIGH_MRP_MULTIPLIER alert
* ``pricing.alert.thin_profit``       ← THIN_PROFIT alert

plus the cross-cutting registry IDs the vendored core layer
(errors/tenancy/plan_guard) may resolve.  The dynamic IDs the auth /
rate-limit exception classes raise (``auth.token_missing``,
``rate_limit.exceeded``, ``tenancy.cross_user_access``) are 2-segment and are
NOT registry keys — they fall through the resolver to verbatim and the
``core/errors`` handler substitutes the exception's draft prose (same posture
as the monolith — see services-builder D1).

The full monolith registry (55 IDs across 8 domains) is NOT vendored.
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── §12 pricing (5 module-specific IDs — verbatim from monolith) ─────────
    "validation.price.invalid_input": (
        "Please enter a valid price greater than zero."
    ),
    "pricing.commission.missing": (
        "We couldn't load the commission rate for this category. Please try again later."
    ),
    "pricing.alert.low_margin": (
        "Your profit margin is below the safe threshold. Consider raising your selling price."
    ),
    "pricing.alert.high_mrp_multiplier": (
        "Your MRP is much higher than your cost. Verify this is the price you want to advertise."
    ),
    "pricing.alert.thin_profit": (
        "Your profit per unit is low. Consider revising your cost or selling price."
    ),
    # ── §4.C tenancy (1 cross-cutting ID) ────────────────────────────────────
    "tenancy.cross_user.access": (
        "You do not have access to this resource."
    ),
    # ── §4.E plan_guard (1 cross-cutting ID) ─────────────────────────────────
    "plan.limit.exceeded": (
        "You've reached your plan's limit. Upgrade to continue."
    ),
    # ── §4.F server fallback (1 cross-cutting ID) ────────────────────────────
    "server.internal.error": (
        "Something went wrong on our end. Please try again."
    ),
}

__all__ = ["VALIDATION_MESSAGES"]
