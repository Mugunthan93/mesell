"""svc-image vendored core layer — errors, tenancy, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  ``cache.py`` and
``plan_guard.py`` are NOT vendored — image participates in no plan_guard
resource (§11.J — the 4-slot uniform rule is the structural DB limit) and
reads no application cache.  ``plan_guard_mw`` is vendored but NO-OPs (A2).
``extracted_clients`` holds the catalog-ownership HTTP shim.
"""
