"""svc-export vendored core layer — errors, tenancy, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  ``cache.py`` and
``plan_guard.py`` are NOT vendored — export participates in no plan_guard
resource (§14.A) and reads no application cache.  ``plan_guard_mw`` is
vendored but NO-OPs (A2 / §0.7).
"""
