"""svc-customer vendored middleware chain (6 middleware).

Runtime order (§4.H):
    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

``plan_guard_mw`` RUNS but is a NO-OP for customer (customer gates no plan
resource).  ``audit_mw`` RUNS and IS active on customer's 3 PATCH endpoints
(write-method gate fires for POST/PATCH/PUT/DELETE) — it writes the audit fact
to ``public.audit_events`` cross-schema.  ``request_context_mw`` is an
extraction-support layer (NOT part of the 6-count) that feeds the OUTBOUND
category_client shim the caller's JWT + X-Request-ID.
"""
