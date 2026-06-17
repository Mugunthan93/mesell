"""``core/middleware/`` — the seven-stage request chain.

Per BACKEND_ARCHITECTURE.md §4.G/§4.H, the runtime order is::

    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route) → audit_mw

Registration in ``app/main.py`` is the **reverse** of this order (Starlette
wraps later additions further out) plus ``audit_mw`` first so it runs
deepest, after the route handler.

This file is intentionally empty (no re-exports) — every caller imports
from the leaf module.
"""
