"""svc-pricing vendored middleware chain (6 middleware).

Runtime order (§4.H):
    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

``plan_guard_mw`` RUNS but is a NO-OP for pricing (pricing is plan_guard-excluded
per §0.9 / §12.I).  ``audit_mw`` RUNS and FIRES on pricing's write ``POST``
(``/products/{id}/price-calc`` carries ``@audit_event("pricing.calculated")``) —
the 2xx path writes a real cross-schema row into ``public.audit_events``.
``request_context_mw`` is an extraction-support layer (NOT part of the 6-count)
that feeds the extracted_clients HTTP shims the caller's JWT + X-Request-ID.
"""
