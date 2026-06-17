"""svc-export vendored middleware chain (6 middleware).

Runtime order (§4.H):
    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

``plan_guard_mw`` RUNS but is a NO-OP for export (§0.7 / §14.A).
"""
