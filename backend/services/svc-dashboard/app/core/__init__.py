"""svc-dashboard vendored core layer — errors, tenancy, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  ``cache.py`` and
``plan_guard.py`` are NOT vendored — dashboard participates in no plan_guard
resource (it is plan_guard-excluded per §13.I) and reads no application cache.
``plan_guard_mw`` is vendored but NO-OPs; ``audit_mw`` is vendored but NO-OPs
on dashboard's read-only GET (A2 / D7 / §13.B / §13.I).
"""
