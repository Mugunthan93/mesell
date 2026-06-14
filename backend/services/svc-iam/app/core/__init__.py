"""svc-iam vendored core layer — errors, tenancy, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  ``cache.py`` and
``plan_guard.py`` are NOT vendored — iam participates in no plan_guard resource
(it is plan_guard-excluded, alongside customer + dashboard + pricing) and reads
no application cache (no DB 3).  ``plan_guard_mw`` is vendored but NO-OPs;
``audit_mw`` is vendored and FIRES on iam's auth write POSTs
(``/auth/otp/verify`` / ``/auth/refresh`` / ``/auth/logout`` →
cross-schema ``public.audit_events`` INSERT).  ``core/auth.py`` is vendored
byte-for-byte by the auth-builder (NOT this services-builder dispatch) — iam is
the only service that also runs the issuance / rotation half of it from a route.
"""
