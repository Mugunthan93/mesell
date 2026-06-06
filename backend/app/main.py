"""MeeSell API — FastAPI application entry point.

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route) → audit_mw

Starlette applies middleware in REVERSE order of registration — the last
``add_middleware`` call wraps closest to the outside, the first wraps
closest to the route.  To achieve the locked runtime order:

* ``AuditMiddleware`` is registered FIRST so it sits deepest, wrapping the
  route handler and observing the response (it is the only post-handler
  middleware).
* Then each pre-route middleware is registered in REVERSE of runtime
  order: PlanGuard → RateLimit → TenancyContext → AuthContext → RequestId.
* Finally CORS is registered LAST so it sits outermost — preflight
  OPTIONS requests must short-circuit before auth-state setup.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.cache import prewarm_top_categories
from app.core.errors import register_error_handlers
from app.core.middleware.audit_mw import AuditMiddleware
from app.core.middleware.auth_mw import AuthContextMiddleware
from app.core.middleware.plan_guard_mw import PlanGuardMiddleware
from app.core.middleware.rate_limit_mw import RateLimitMiddleware
from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenancy_mw import TenancyContextMiddleware
from app.modules.iam import iam_router
from app.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events.

    The DB engine + Valkey client are kept on ``app.state`` so the legacy
    ``/health`` checks below can reach them.  ``prewarm_top_categories``
    runs after the engine is live but BEFORE we ``yield`` — failure here
    is logged and swallowed so a cold cache does not block boot.
    """
    logger.info(f"MeeSell API starting (env={settings.APP_ENV})")
    app.state.db_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    app.state.valkey = redis.from_url(settings.VALKEY_URL, decode_responses=True)

    try:
        await prewarm_top_categories()
    except Exception as exc:  # noqa: BLE001 — startup hook must not block boot
        logger.warning("prewarm_top_categories failed at startup: %s", exc)

    yield
    await app.state.valkey.aclose()
    await app.state.db_engine.dispose()
    logger.info("MeeSell API shutting down")


app = FastAPI(
    title="MeeSell API",
    description="AI-powered operating system for Meesho suppliers",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) ─────────────────────────
# Registered DEEPEST-FIRST.  See module docstring for the runtime-vs-
# registration-order rationale.

# Innermost — runs AFTER the route handler, observes the response.
app.add_middleware(AuditMiddleware)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)        # V1 no-op
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenancyContextMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestIdMiddleware)

# Outermost — handles CORS preflight before any auth-state setup.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers (§4.F) ──────────────────────────────────────────────────
register_error_handlers(app)

# ── Routers ────────────────────────────────────────────────────────────────
# §7 iam — owns /api/v1/auth/* (otp/send, otp/verify, refresh, logout, me)
# + /api/v1/webhooks/razorpay per BACKEND_ARCHITECTURE.md §7.B (LOCKED 2026-06-05).
app.include_router(iam_router)

if settings.is_dev:
    import os

    from fastapi.staticfiles import StaticFiles

    os.makedirs("/tmp/meesell", exist_ok=True)
    app.mount("/dev-static", StaticFiles(directory="/tmp/meesell"), name="dev-static")


# ── Health check (preserved from baseline) ─────────────────────────────────
async def _check_postgres() -> str:
    try:
        async with app.state.db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.warning(f"Postgres health check failed: {exc}")
        return "error"


async def _check_valkey() -> str:
    try:
        pong = await app.state.valkey.ping()
        return "ok" if pong else "error"
    except Exception as exc:
        logger.warning(f"Valkey health check failed: {exc}")
        return "error"


@app.get("/health")
async def health():
    """Health check endpoint with PostgreSQL and Valkey connectivity."""
    checks = {"postgres": await _check_postgres(), "valkey": await _check_valkey()}
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
