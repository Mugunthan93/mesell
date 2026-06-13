"""svc-pricing vendored core layer — errors, tenancy, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  ``cache.py`` and
``plan_guard.py`` are NOT vendored — pricing participates in no plan_guard
resource (it is plan_guard-excluded per §0.9 / §12.I, alongside customer +
dashboard) and reads no application cache (§0.8).  ``plan_guard_mw`` is
vendored but NO-OPs; ``audit_mw`` is vendored and FIRES on pricing's write POST
(``/products/{id}/price-calc`` → cross-schema ``public.audit_events`` INSERT).
"""
