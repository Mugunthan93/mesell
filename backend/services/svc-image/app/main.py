"""svc-image — standalone FastAPI application entry point (spec §1 B1).

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → request_context → auth_mw → tenancy_mw → rate_limit_mw
    → plan_guard_mw → (route) → audit_mw

The 6-middleware §4.H chain is vendored verbatim; ``plan_guard_mw`` RUNS but
NO-OPs for image (§11.J).  ``rate_limit_mw`` + ``audit_mw`` are ACTIVE.
``request_context_mw`` is an extraction-support layer (NOT part of the 6-count)
that feeds the catalog-ownership HTTP shim the caller's JWT + X-Request-ID.

JWT is verified LOCALLY (A2/D7) via the vendored ``core/auth.py`` + the shared
``JWT_SECRET`` — svc-image issues no tokens, it only verifies.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

Router dependency (B2 hand-off)
-------------------------------
The 2 public image routes + the ``/internal/products/{product_id}/images``
shim live in ``app.router`` (``router.py``), delivered by
meesell-api-routes-builder (B2).  The import path is ``from app.router import
router as image_router`` — the svc-export precedent (``from app.router import
router as export_router``).  This path is NOT pinned by the EXECUTION spec, so
it follows that precedent; B2 + the lead verify it composes (NOTED for the
lead).  The mount is import-tolerant ordering: this module imports clean only
once ``router.py`` lands (mirrors svc-export — the router is a hard import at
module bottom, so the package is fully importable only after B2 merges).
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
    logger.info(f"svc-image starting (env={settings.APP_ENV})")
    yield
    await aclose_all()
    logger.info("svc-image shutting down")


app = FastAPI(
    title="MeeSell svc-image",
    description="Standalone image upload + precheck microservice (MS Sub-Plan C)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.
app.add_middleware(AuditMiddleware)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)          # NO-OP for image (§11.J)
app.add_middleware(RateLimitMiddleware)          # ACTIVE
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
# The 2 public image routes + the /internal list-images shim live in
# app/router.py (meesell-api-routes-builder — B2).
from app.router import router as image_router  # noqa: E402

app.include_router(image_router)
logger.info("svc-image: image router mounted")

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the
    readiness probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-image"}
