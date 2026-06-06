"""``core/`` — cross-cutting foundation layer.

Per BACKEND_ARCHITECTURE.md §3.D + §4, this package holds the non-domain
foundation every other module depends on:

* :mod:`app.core.auth` — ``get_current_user`` FastAPI dep (owner: auth-builder).
* :mod:`app.core.tenancy` — ``assert_owned`` + ``scope_to_user`` helpers.
* :mod:`app.core.cache` — Valkey DB 3 read-through helper.
* :mod:`app.core.plan_guard` — feature-budget enforcement.
* :mod:`app.core.errors` — ``MeesellError`` root + handler registration.
* :mod:`app.core.middleware` — the seven-stage request middleware chain.

This file is intentionally empty (no re-exports) — every caller imports
from the leaf module so import-direction discipline (§4.I) is auditable
at grep-time.
"""
