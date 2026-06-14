"""svc-iam — standalone FastAPI application entry point (SUB_PLAN_0G §"Code surfaces").

SCAFFOLD NOTE (services-builder seam)
-------------------------------------
This file is the services-builder Phase-B SCAFFOLD: it wires the 6-middleware
chain + error handlers + health/metrics + an IMPORT-TOLERANT router mount so the
auth-builder's and api-routes-builder's modules import cleanly when they land on
this SAME branch AFTER this dispatch.  It deliberately imports NEITHER
``app.service`` NOR ``app.core.auth`` (both owned byte-for-byte by the
auth-builder).  The router (``app.router``, owned by api-routes-builder) is
mounted import-tolerantly; once it lands the 6 iam routes mount with no change
here.  The auth-builder may extend this module (e.g. a startup hook that
SCRIPT-LOADs the refresh-rotation Lua) — that is its surface to own.

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

The 6-middleware §4.H chain is vendored.  ``plan_guard_mw`` RUNS but NO-OPs for
iam (iam is plan_guard-excluded).  ``audit_mw`` RUNS and FIRES on iam's auth
write ``POST``s (``/auth/otp/verify`` / ``/auth/refresh`` / ``/auth/logout`` →
cross-schema ``public.audit_events`` INSERT).  There is NO ``request_context_mw``
— iam is all-✗ in the call matrix (SUB_PLAN_0G §0.4: zero outbound HTTP shims),
so the shim-context middleware that pricing / dashboard carry is absent here.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

NO Celery
---------
iam has no ``tasks.py`` (SUB_PLAN_0G §0.2) — svc-iam runs NO Celery worker, has
no broker / result Valkey DB, and imports no ``celery_app``.

NO /internal/* route
--------------------
iam exposes ONLY its 6 public routes through Traefik (SUB_PLAN_0G §0.4 — iam's
contract to other services is the vendored ``core/auth.py`` + the shared
``JWT_SECRET``, NOT an HTTP shim).  Inventing an iam ``/internal/*`` route is a
reject-class offense (G1 / G2 / §5.A A2/D7).
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
from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenancy_mw import TenancyContextMiddleware
from app.shared.config import settings
from app.shared.valkey import aclose_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events.

    The auth-builder may add a startup hook here to ``SCRIPT LOAD`` the
    refresh-rotation Lua (``REFRESH_ROTATE_LUA`` from the vendored
    ``core/auth.py``) and cache its SHA1 — that is the auth-builder's surface.
    The scaffold's lifespan only closes the Valkey client on shutdown.
    """
    logger.info(f"svc-iam starting (env={settings.APP_ENV})")
    yield
    await aclose_all()
    logger.info("svc-iam shutting down")


app = FastAPI(
    title="MeeSell svc-iam",
    description="Standalone identity / OTP / token-issuance microservice (MS Sub-Plan G)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.  For iam
# this FIRES on the auth write POSTs (cross-schema public.audit_events write).
app.add_middleware(AuditMiddleware)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)            # NO-OP for iam
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenancyContextMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestIdMiddleware)

# Outermost — handles CORS preflight before any auth-state setup.  FE-D5 sends
# the refresh cookie cross-origin with credentials, so allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers (§4.F) ──────────────────────────────────────────────────
register_error_handlers(app)

# ── Router ─────────────────────────────────────────────────────────────────
# The 6 iam routes live in app/router.py (meesell-api-routes-builder), delivered
# AFTER this services-builder scaffold on the SAME branch.  Import-tolerant so
# this module boots clean before router.py lands; once it lands, the 6 routes
# mount with no change here.  NO /internal/* route is ever mounted (§0.4).
try:
    from app.router import router as iam_router  # noqa: E402

    app.include_router(iam_router)
    logger.info("svc-iam: iam router mounted")
except ImportError:
    logger.warning(
        "svc-iam: app.router not yet present — iam routes NOT mounted "
        "(meesell-api-routes-builder delivers router.py next, Phase B)"
    )

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the
    readiness probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-iam"}
