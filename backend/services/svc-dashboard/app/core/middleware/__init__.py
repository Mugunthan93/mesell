"""svc-dashboard vendored middleware chain (6 middleware).

Runtime order (§4.H):
    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

``plan_guard_mw`` RUNS but is a NO-OP for dashboard (dashboard is
plan_guard-excluded per §13.I).  ``audit_mw`` RUNS but NO-OPs on dashboard's
read-only GET (it gates on write-methods only — §13.B).
"""
