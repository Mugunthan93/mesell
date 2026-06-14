"""svc-catalog — standalone FastAPI application entry point (SUB_PLAN_0H).

THE SPINE — the LAST + RISKIEST extraction.  catalog is BOTH a heavy CALLEE
(4 inbound /internal/* shims) AND a multi-callee CALLER (5 outbound shims).

Middleware chain (§4.H locked runtime order)::

    CORS → request_id → request_context → auth_mw → tenancy_mw → rate_limit_mw
    → plan_guard_mw → (route) → audit_mw

The 6-middleware §4.H chain is vendored verbatim.  ``plan_guard_mw`` RUNS but
the real cap is in-service (``enforce_plan_limit`` for ``product_count`` inside
``create_product`` + ``ai_autofill_hourly`` inside ``autofill_product``).
``audit_mw`` RUNS and FIRES on catalog's 4 WRITE routes
(``catalog.product.created/updated/deleted`` + ``catalog.autofill.invoked`` →
cross-schema ``public.audit_events`` INSERTs).  ``request_context_mw`` is an
extraction-support layer (NOT part of the 6-count) that feeds the 5 outbound
extracted_clients shims the caller's JWT + X-Request-ID.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

FEATURE_CATALOG_FORM_ENABLED mount guard (R9 / row-26 — LOAD-BEARING)
---------------------------------------------------------------------
catalog is the ONLY domain whose PUBLIC router mounts behind a runtime flag.
When ``settings.FEATURE_CATALOG_FORM_ENABLED`` is False the entire
``/api/v1/products/*`` public surface falls through to FastAPI's default 404
(monolith main.py:126-127).  This guard is PRESERVED here — the mounted public
route count is CONDITIONAL.  (The ``/internal/*`` shims are NOT gated by this
flag — sibling services must reach ownership-check / export-snapshot /
list_products regardless of the public-form rollout state.)

NO Celery
---------
catalog has NO worker (SUB_PLAN_0H §Celery-NONE — the autosave ``product_drafts``
upsert is synchronous inside ``patch_product``).  svc-catalog ships NO
``celery_app.py`` / ``tasks.py``, no broker / result Valkey DB.

Router dependency
-----------------
``app.router`` (6 public routes) + ``app.internal_router`` (3-4 /internal/*
shims) are delivered by meesell-api-routes-builder (Phase B, near-parallel once
the service signature freezes).  Both mounts are import-tolerant so this module
boots clean before the routers land.
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
    """Startup and shutdown events.  catalog does NOT prewarm the category
    cache — the ``fetch_schema`` hot path is served from category-svc's own
    pre-warm cache over the outbound shim (Risk #1 mitigation)."""
    logger.info(f"svc-catalog starting (env={settings.APP_ENV})")
    yield
    await aclose_all()
    logger.info("svc-catalog shutting down")


app = FastAPI(
    title="MeeSell svc-catalog",
    description="Standalone catalog/product microservice — THE SPINE (MS Sub-Plan H)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.  For catalog
# this FIRES on the 4 write routes (cross-schema public.audit_events writes).
app.add_middleware(AuditMiddleware)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)            # runs; real cap is in-service
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

# ── Public router (6 routes) — FEATURE_CATALOG_FORM_ENABLED MOUNT GUARD ─────
# R9 / row-26: the public catalog router mounts ONLY when the flag is True —
# the mounted public route count is CONDITIONAL (preserved from monolith
# main.py:126-127).  Import-tolerant so this module boots before router.py lands.
if settings.FEATURE_CATALOG_FORM_ENABLED:
    try:
        from app.router import router as catalog_router  # noqa: E402

        app.include_router(catalog_router)
        logger.info("svc-catalog: public catalog router mounted (flag ON)")
    except ImportError:
        logger.warning(
            "svc-catalog: app.router not yet present — public catalog route NOT "
            "mounted (meesell-api-routes-builder delivers router.py next, Phase B)"
        )
else:
    logger.info(
        "svc-catalog: FEATURE_CATALOG_FORM_ENABLED is False — public catalog "
        "router NOT mounted (/api/v1/products/* falls through to 404)"
    )

# ── Internal router (3-4 /internal/* shims) — NOT flag-gated ───────────────
# ownership-check / export-snapshot / list_products (+ defensive validation-
# summary) — sibling services must reach these regardless of the public-form
# rollout flag.  Import-tolerant (api-routes-builder delivers internal_router.py).
try:
    from app.internal_router import router as catalog_internal_router  # noqa: E402

    app.include_router(catalog_internal_router)
    logger.info("svc-catalog: internal router mounted")
except ImportError:
    logger.warning(
        "svc-catalog: app.internal_router not yet present — /internal/* shims "
        "NOT mounted (meesell-api-routes-builder delivers internal_router.py next)"
    )

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the
    readiness probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-catalog"}
