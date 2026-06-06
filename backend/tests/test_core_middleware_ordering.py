"""Test the §4.H canonical middleware ordering on the actual app.

Starlette stores user middleware in registration order INSIDE
``app.user_middleware``; the LAST-registered is at index 0 and wraps
OUTERMOST.  We register deepest-first in ``app/main.py``, so the
``app.user_middleware`` list — read index 0 → N-1 — directly mirrors the
runtime chain order.
"""

from __future__ import annotations

from app.main import app

# Locked §4.H runtime order:
#   CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw
EXPECTED_RUNTIME_ORDER = [
    "CORSMiddleware",
    "RequestIdMiddleware",
    "AuthContextMiddleware",
    "TenancyContextMiddleware",
    "RateLimitMiddleware",
    "PlanGuardMiddleware",
    "AuditMiddleware",
]


def test_middleware_count_is_seven() -> None:
    """Exactly the seven middleware listed in §4.H — no more, no fewer."""
    assert len(app.user_middleware) == 7, (
        f"Expected 7 user middleware, found {len(app.user_middleware)}: "
        f"{[m.cls.__name__ for m in app.user_middleware]}"
    )


def test_middleware_runtime_order_matches_lock() -> None:
    """Runtime order matches §4.H canonical sequence."""
    actual = [m.cls.__name__ for m in app.user_middleware]
    assert actual == EXPECTED_RUNTIME_ORDER, (
        f"Middleware order mismatch.  Expected {EXPECTED_RUNTIME_ORDER}; "
        f"got {actual}."
    )


def test_audit_middleware_runs_last() -> None:
    """``audit_mw`` is the innermost (last in user_middleware list)."""
    assert app.user_middleware[-1].cls.__name__ == "AuditMiddleware"


def test_cors_middleware_runs_first() -> None:
    """``CORS`` is the outermost (first in user_middleware list)."""
    assert app.user_middleware[0].cls.__name__ == "CORSMiddleware"
