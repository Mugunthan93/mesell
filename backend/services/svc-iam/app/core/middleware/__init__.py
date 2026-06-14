"""svc-iam vendored middleware chain (6 middleware).

Runtime order (§4.H):
    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

``plan_guard_mw`` RUNS but is a NO-OP for iam (iam is plan_guard-excluded —
SUB_PLAN_0G §"Code surfaces").  ``audit_mw`` RUNS and FIRES on iam's auth write
``POST`` routes (``/auth/otp/verify`` / ``/auth/refresh`` / ``/auth/logout``)
plus the §7.I direct-ORM audit path in ``service.py`` — the 2xx path writes a
real cross-schema row into ``public.audit_events`` (``users`` lives in schema
``iam``).

NO ``request_context_mw``: iam is all-✗ in the cross-module call matrix
(SUB_PLAN_0G §0.4) — it makes ZERO outbound HTTP calls, so the extraction-support
shim-context middleware that pricing / dashboard carry is NOT vendored here.
The chain is exactly the §4.H 6-middleware shape.
"""
