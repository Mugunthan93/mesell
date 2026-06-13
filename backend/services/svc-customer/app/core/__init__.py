"""svc-customer vendored core layer — errors, tenancy, cache, metrics, auth, middleware.

Trimmed copies of the monolith ``app.core`` layer.  UNLIKE svc-dashboard,
svc-customer DOES vendor ``cache.py`` (the customer service is a read-through
cache consumer — required_fields 60 s + super_category_set 3600 s, §4.D /
§8.B.5 / §8.I).  ``plan_guard.py`` is NOT vendored — customer participates in
no plan_guard resource; ``plan_guard_mw`` is vendored but NO-OPs; ``audit_mw``
is vendored and IS active on customer's 3 PATCH endpoints (write-method gate).
"""
