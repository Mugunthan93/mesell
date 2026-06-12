"""svc-export — standalone FastAPI application entry point (spec §3.A).

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → request_context → auth_mw → tenancy_mw → rate_limit_mw
    → plan_guard_mw → (route) → audit_mw

The 6-middleware §4.H chain is vendored verbatim; ``plan_guard_mw`` RUNS but
NO-OPs for export (§0.7 / §14.A).  ``request_context_mw`` is an
extraction-support layer (NOT part of the 6-count) that feeds the
extracted_clients HTTP shims the caller's JWT + X-Request-ID.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

Router dependency
-----------------
The 2 export routes live in ``app.router`` (``router.py``), delivered by
meesell-api-routes-builder AFTER this services-builder slice (Phase B,
near-parallel once the service signatures freeze — spec §1).  The mount is
import-tolerant so this module imports clean before ``router.py`` lands; once
it lands, the 2 routes mount with no change here.
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
from app.shared.config import settings
from app.shared.valkey import aclose_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"svc-export starting (env={settings.APP_ENV})")
    yield
    await aclose_all()
    logger.info("svc-export shutting down")


app = FastAPI(
    title="MeeSell svc-export",
    description="Standalone Meesho XLSX export microservice (MS Sub-Plan A)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.
app.add_middleware(AuditMiddleware)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)          # NO-OP for export
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenancyContextMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestContextMiddleware)     # extraction-support (shim ctx)
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

# ── Router ─────────────────────────────────────────────────────────────────
# The 2 export routes are delivered by api-routes-builder in app/router.py.
# Import-tolerant so this module loads before that file lands (Phase B
# near-parallel dispatch — spec §1).
try:
    from app.router import router as export_router

    app.include_router(export_router)
    logger.info("svc-export: export router mounted")
except ImportError:  # pragma: no cover — only during the pre-routes window
    logger.warning(
        "svc-export: app.router not yet available — export routes NOT mounted. "
        "api-routes-builder delivers app/router.py in Phase B (spec §3.B)."
    )

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the
    readiness probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-export"}
