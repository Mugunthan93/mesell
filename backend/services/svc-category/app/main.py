"""svc-category — standalone FastAPI application entry point (Sub-Plan F).

Middleware chain (§4.H locked runtime order — the 6-middleware chain, F2/D7)::

    CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw
    → (route) → audit_mw

The 6-middleware §4.H chain is vendored verbatim.  ``rate_limit_mw`` is ACTIVE
(``/categories/suggest`` carries ``@rate_limit(scope="smart_picker",
limit=100, window=3600)``).  ``plan_guard_mw`` RUNS but the actual
``smart_picker_hourly`` cap is enforced INSIDE ``service.suggest_categories``
(``enforce_plan_limit``, §4.E), not in the middleware decorator.  ``audit_mw``
RUNS but NO-OPs for category — all 5 public routes are read-only GETs (zero
audit rows); the ai_ops cost ledger writes ``public.audit_events`` directly
from the vendored ``cost_tracker`` (NOT via audit_mw).

There is NO ``request_context_mw`` — category has ZERO outbound domain calls
(it is a pure callee; no HTTP shim client needs the forwarded-JWT context).

JWT is verified LOCALLY (D7/A2) via the vendored ``core/auth.py`` + the shared
``JWT_SECRET`` — category issues no tokens, it only verifies.  iam-svc (MS-G,
extracting in parallel) is NEVER consulted per-request.

Starlette applies middleware in REVERSE registration order — register
deepest-first.

Worker-startup cache pre-warm (§6.7)
------------------------------------
The lifespan startup warms the full ``category_tree`` GLOBAL key + the top-100
``schema:{id}`` keys via the vendored ``core.cache.prewarm_top_categories``,
so the catalog-autosave hot path (``fetch_schema``) hits a warm DB-3 cache
(≥99% hit, R4).  Wrapped in try/except so a cold DB/Valkey never blocks boot.

Router dependency (B-phase hand-off)
------------------------------------
The 5 public routes (``app.router``) + the 2-3 ``/internal/*`` shims
(``app.internal_router``) are delivered by meesell-api-routes-builder.  Both
mounts are import-tolerant (try/except ImportError) so this module boots clean
before those files land (svc-pricing precedent).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.cache import prewarm_top_categories
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

    Startup runs the §6.7 cache pre-warm (full-tree + top-100 schemas) so the
    catalog-autosave hot path hits a warm cache from the first request.  The
    pre-warm is wrapped here in try/except for defense-in-depth (the helper is
    also internally fail-safe) — a cold DB/Valkey at boot never blocks startup.
    """
    logger.info(f"svc-category starting (env={settings.APP_ENV})")
    try:
        await prewarm_top_categories(n=100)
    except Exception as exc:  # noqa: BLE001 — startup hook must not block boot
        logger.warning("svc-category: cache pre-warm failed at startup: %s", exc)
    yield
    await aclose_all()
    logger.info("svc-category shutting down")


app = FastAPI(
    title="MeeSell svc-category",
    description="Standalone category tree + Smart Picker + schema microservice (MS Sub-Plan F)",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware registration (§4.H canonical order) — DEEPEST-FIRST ─────────
# Innermost — runs AFTER the route handler, observes the response.
app.add_middleware(AuditMiddleware)              # RUNS but NO-OP (read-only GETs)

# Pre-route middleware, in REVERSE of runtime order:
app.add_middleware(PlanGuardMiddleware)          # smart_picker cap enforced in-service
app.add_middleware(RateLimitMiddleware)          # ACTIVE (smart_picker 100/3600)
app.add_middleware(TenancyContextMiddleware)
app.add_middleware(AuthContextMiddleware)        # LOCAL JWT verify (D7)
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

# ── Routers (import-tolerant — api-routes-builder deliverables) ─────────────
# The 5 public category routes live in app/router.py; the 2-3 /internal/*
# shims live in app/internal_router.py.  Both mounts are import-tolerant so
# this module boots before those files land (svc-pricing precedent).
try:
    from app.router import router as category_router  # noqa: E402

    app.include_router(category_router)
    logger.info("svc-category: public router mounted")
except ImportError as exc:
    logger.warning("svc-category: public router not yet available (%s)", exc)

try:
    from app.internal_router import router as internal_router  # noqa: E402

    app.include_router(internal_router)
    logger.info("svc-category: internal router mounted")
except ImportError as exc:
    logger.warning("svc-category: internal router not yet available (%s)", exc)

# ── Prometheus metrics scrape ───────────────────────────────────────────────
app.mount("/metrics", make_asgi_app())


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    """Liveness probe.  DB / Valkey deep checks are deferred to the
    readiness probe wired by the infra lane.
    """
    return {"status": "healthy", "service": "svc-category"}
