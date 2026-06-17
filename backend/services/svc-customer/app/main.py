"""svc-customer — standalone FastAPI application entry point (spec §3.A).

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → request_context → auth_mw → tenancy_mw → rate_limit_mw
    → plan_guard_mw → (route) → audit_mw

The 6-middleware §4.H chain is vendored.  ``plan_guard_mw`` RUNS but NO-OPs for
customer (customer gates no plan resource); ``audit_mw`` RUNS and IS active on
customer's 3 PATCH write endpoints (write-method gate → cross-schema INSERT into
``public.audit_events``).  ``request_context_mw`` is an extraction-support layer
(NOT part of the 6-count) that feeds the OUTBOUND category_client shim the
caller's JWT + X-Request-ID.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

NO Celery
---------
customer has NO background jobs — svc-customer runs NO Celery worker, has no
broker / result Valkey, and imports no ``celery_app``.

Routers
-------
* The 3 INBOUND ``/internal/*`` provider routes live in
  ``app.internal_routes`` (``internal_router``) — owned by this services-builder
  slice (the 3 FROZEN contracts: compliance-block / onboarding-completeness /
  eligibility).  Mounted unconditionally.
* The 5 PUBLIC ``/api/v1/seller-profile/*`` routes live in ``app.router``
  (``router.py``), delivered by meesell-api-routes-builder AFTER this slice
  (Phase B).  The mount is import-tolerant so this module boots clean before
  ``router.py`` lands; once it lands, the routes mount with no change here.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.errors import register_error_handlers
from app.core.middleware.audit_mw import AuditMiddleware
from app.core.middleware.auth_mw import AuthContextMiddleware
from app.core.middleware.plan_guard_mw import PlanGuardMiddleware
from app.core.middleware.rate_limit_mw import RateLimitMiddleware
from app.core.middleware.request_context_mw import RequestContextMiddleware
from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenancy_mw import TenancyContextMiddleware
from app.internal_routes import internal_router
from app.shared.config import settings
from app.shared.valkey import aclose_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"svc-customer starting (env={settings.APP_ENV})")
    yield
    await aclose_all()
    logger.info("svc-customer shutting down")


app = FastAPI(
    title="MeeSell svc-customer",
    description="Standalone seller-profile / onboarding microservice (MS Sub-Plan E)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.
app.add_middleware(AuditMiddleware)                # active on the 3 PATCH writes

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)            # NO-OP for customer
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenancyContextMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestContextMiddleware)       # extraction-support (shim ctx)
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

# ── INBOUND /internal/* provider routes (services-builder slice) ────────────
# The 3 FROZEN contracts (compliance-block / onboarding-completeness /
# eligibility).  Mounted unconditionally — owned by this slice.
app.include_router(internal_router)
logger.info("svc-customer: internal_router mounted (3 /internal/* routes)")

# ── PUBLIC router (meesell-api-routes-builder, Phase B) ─────────────────────
# The 5 /api/v1/seller-profile/* routes live in app/router.py, delivered AFTER
# this services-builder slice.  Import-tolerant so this module boots clean
# before router.py lands; once it lands, the routes mount with no change here.
try:
    from app.router import router as customer_router  # noqa: E402

    app.include_router(customer_router)
    logger.info("svc-customer: public customer router mounted")
except ImportError:
    logger.warning(
        "svc-customer: app.router not yet present — public routes NOT mounted "
        "(meesell-api-routes-builder delivers router.py next, Phase B)"
    )

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the readiness
    probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-customer"}
