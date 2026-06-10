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
from prometheus_client import make_asgi_app
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
from app.modules.catalog import catalog_router
from app.modules.category import category_router
from app.modules.customer import customer_router
from app.modules.dashboard import dashboard_router
from app.modules.export import export_router
from app.modules.iam import iam_router
from app.modules.image import image_router
from app.modules.pricing import pricing_router
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

# §8 customer — owns /api/v1/seller-profile/* (5 endpoints per §8.B LOCKED 2026-06-05).
app.include_router(customer_router)

# §9 category — owns /api/v1/categories/* (5 endpoints per §9.B LOCKED 2026-06-05).
app.include_router(category_router)

# §10 catalog — owns /api/v1/products/* (6 endpoints per §10.B LOCKED 2026-06-05).
app.include_router(catalog_router)

# §11 image — owns /api/v1/products/{id}/images (2 endpoints per §11.B LOCKED 2026-06-05).
app.include_router(image_router)

# §12 pricing — owns /api/v1/products/{id}/price-calc (1 endpoint per §12.B LOCKED 2026-06-05).
# Latent bug §0.E resolved: legacy services/pricing_engine.py deleted at construction time.
app.include_router(pricing_router)

# §13 dashboard — owns GET /api/v1/products (1 endpoint per §13.B LOCKED 2026-06-05;
# AMENDED 2026-06-07 §13.A.1 — status_filter + search deferred to V1.5).
# NOTE: GET /api/v1/products shares the path key /api/v1/products with §10 catalog's
# POST /api/v1/products. FastAPI registers them as two distinct APIRoute objects;
# distinct-path count stays at 27, raw APIRoute count rises from 26 to 27.
app.include_router(dashboard_router)

# §14 export — owns POST /api/v1/products/{id}/export-xlsx + GET /api/v1/exports/{id}
# (2 endpoints per §14.B LOCKED 2026-06-05). Adds 2 new distinct path keys;
# expected_count rises from 27 → 29.
app.include_router(export_router)

if settings.is_dev:
    import os

    from fastapi.staticfiles import StaticFiles

    os.makedirs("/tmp/meesell", exist_ok=True)
    app.mount("/dev-static", StaticFiles(directory="/tmp/meesell"), name="dev-static")


# ── Prometheus metrics scrape (§15.J / F-15-2) ─────────────────────────────
# Mounted LAST — after every router — so it never shadows a domain path.
# The 7 §15.J metrics are defined in ``app.core.metrics`` and incremented /
# observed / set at their respective call sites.  The fail-open auth_mw lets
# the scrape through without a 401 (see auth_mw.py docstring).
app.mount("/metrics", make_asgi_app())


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
