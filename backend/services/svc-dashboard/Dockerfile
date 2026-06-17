# backend/services/svc-dashboard/Dockerfile
# ---------------------------------------------------------------------------
# svc-dashboard — Sub-Plan B (dashboard extraction), INFRA deliverable I1.
#
# ONE image, ONE process: the FastAPI api server. UNLIKE svc-export, dashboard
# has NO Celery worker (no background jobs — it is a pure read-only GET that
# fans out to 2 HTTP shims: catalog.list_products + customer.get_onboarding_
# completeness). So this image ships an api-only entrypoint; there is NO worker
# Deployment that overrides the command (contrast k8s/svc-export/deployment.yaml).
#
# Authority:
#   - handoff_msB_infra.md §1 I1 (api-only — NO Celery worker entrypoint)
#   - docs/plans/microservices_migration/SUB_PLAN_0B_dashboard_extraction.md
#     §0.6 (leaf consumer, 2 outbound shims, NO worker) + §0.7 (5-of-6 mw chain,
#     audit_mw present-but-inert)
#   - MASTER_PLAN.md §2.A (same Python 3.12 base; own main.py; service-specific
#     requirements.txt) + §2.B (port 8001)
#   - mirrors backend/Dockerfile (monolith api: gunicorn -w 2 UvicornWorker on
#     8000) so the served runtime is byte-identical — only the port differs.
#
# Build context = backend/services/svc-dashboard/ . The svc-dashboard app tree
# (app/, requirements.txt) is authored by the backend specialist lane in
# parallel; this Dockerfile is validated at the infra merge gate against the
# spec'd tree shape (SUB_PLAN_0B "Code surfaces" table):
#
#   backend/services/svc-dashboard/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- backend lane (svc-dashboard TRIMMED deps:
#   │                          fastapi, uvicorn, sqlalchemy[asyncio], asyncpg,
#   │                          redis, pydantic-settings, PyJWT, httpx for the
#   │                          2 outbound shims. NO openpyxl, NO celery,
#   │                          NO gemini/langfuse/msg91/razorpay/gcs.)
#   └── app/                <- backend lane (main.py, vendored shared/ + core/,
#       ├── main.py            router/service, 6-mw chain per §0.7)
#       │                      (FastAPI app `app` on :8001 — the SINGLE public
#       │                       route GET /api/v1/products; NO /internal/*, §0.6)
#       └── (NO celery_app.py — dashboard has no Celery, §0.6)
#
# NOTE — NO alembic/ COPY (contrast svc-export I1): dashboard owns ZERO tables
# (§0.8), so there is no per-service migration chain to run. No `alembic upgrade
# head` Job exists for svc-dashboard. The DATABASE_URL is needed only because the
# vendored middleware chain + Depends(get_db) signature expect a session (query
# volume ~0); there are no owned-schema migrations. If the backend lane's tree
# happens to vendor an alembic.ini for shared-config import symmetry, it is NOT
# copied here and is NOT run.
#
# VALIDATE this Dockerfile against the ACTUAL landed tree on
# origin/feature/microservices-dashboard/backend at the infra merge gate (the
# MS-A lesson: confirm COPY targets requirements.txt + app/ exist; confirm
# entrypoint app.main:app — main.py `app = FastAPI(...)`; confirm there is NO
# app/celery_app.py and NO worker Deployment referencing this image).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# + svc-export images so the build is a known quantity).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + svc-export I1). The backend lane's
# svc-dashboard requirements.txt ships uvicorn[standard] but NOT gunicorn (it is
# sole-writer for that file; infra must not edit it) — so the infra image layer
# installs gunicorn explicitly, pinned to the monolith's exact version
# (gunicorn==22.0.0, backend/requirements.txt) so the served runtime is
# byte-identical to the monolith.
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code only — NO alembic/ (dashboard owns zero tables; see header).
COPY app/ ./app/

# svc-dashboard listens on 8001 (MASTER_PLAN §2.B / §2.C gateway map).
EXPOSE 8001

# SINGLE entrypoint = the api process. There is NO worker Deployment overriding
# this command (dashboard has no Celery — §0.6). Gunicorn with 2 Uvicorn workers
# mirrors the monolith api; the dashboard GET is light (2 HTTP shim fan-out +
# response composition), so 1 replica × 2 gunicorn workers is ample for dev
# zero-traffic.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
