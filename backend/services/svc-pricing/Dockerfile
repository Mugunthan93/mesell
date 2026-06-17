# backend/services/svc-pricing/Dockerfile
# ---------------------------------------------------------------------------
# svc-pricing — Sub-Plan D (pricing extraction), INFRA deliverable I1.
#
# SINGLE entrypoint — the FastAPI api process ONLY. svc-pricing has NO Celery
# worker (verified: backend/app/modules/pricing/ ships NO tasks.py — pricing is
# deterministic, stateless P&L math: 1 INSERT (the pricing.calculated audit row)
# + ≤1 SELECT per request; nothing is enqueued). The image therefore carries NO
# worker entrypoint and the k8s manifest spawns NO worker Deployment.
#
# Mirrors the PROVEN MS-A svc-export Dockerfile recipe
# (backend/services/svc-export/Dockerfile, validated at the #190 merge gate) — but
# svc-pricing is the LEANEST recipe-copy: no Pillow, no GCS, no AI SDKs, no Celery
# (svc-export carried Celery for its worker; pricing drops it entirely). The image
# is the smallest of any extracted service.
#
# Authority:
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msD_infra.md §1 I1
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A (FROM the same Python
#     3.12 base; own main.py; service-specific requirements.txt) + §2.B (port 8001)
#
# Build context = backend/services/svc-pricing/ . The svc-pricing app tree
# (app/, alembic/, requirements.txt) is authored by the backend specialist lanes
# IN PARALLEL with this infra lane; at the time this Dockerfile is authored that
# tree is NOT yet on the integration branch. COPY targets are validated against the
# spec'd tree shape at the backend lead's integration merge gate — the SAME
# deferred-validation posture the MS-A svc-export Dockerfile used (it was validated
# against the landed backend tree at the merge gate, see its header).
#
#   backend/services/svc-pricing/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- services-builder (svc-pricing trimmed deps; NO openpyxl,
#   │                          NO pillow/gcs, NO celery, NO gemini/langfuse,
#   │                          NO msg91/razorpay; the smallest dep set of any service)
#   ├── app/                <- backend lanes
#   │   └── main.py         (FastAPI app `app` on :8001 — public
#   │                        POST /api/v1/products/{id}/price-calc; NO /internal/*)
#   └── alembic/            <- database-builder (pricing-schema-rooted migration chain;
#                              version_table_schema="pricing")
#
# NOTE — NO celery_app.py: unlike svc-export/svc-image, svc-pricing has no Celery
# instance and no `-Q` worker invocation. The single CMD below (gunicorn api) is the
# ONLY runtime entrypoint; k8s/svc-pricing/deployment.yaml does NOT override it.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# image + svc-export). No Pillow/JPEG libs (pricing decodes no images) — the
# minimal native footprint of any service.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + svc-export). The services-builder is
# sole-writer of requirements.txt and ships uvicorn[standard] but NOT gunicorn — so
# the infra image layer installs gunicorn explicitly, pinned to the monolith's exact
# version (gunicorn==22.0.0, backend/requirements.txt) so the served runtime is
# byte-identical to the monolith + svc-export.
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# step (DEVOPS migration-before-deploy pattern, applied per-service) can run
# `alembic upgrade head` against the `pricing` schema inside this image.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-pricing listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map).
EXPOSE 8001

# The ONLY entrypoint = the api process. There is NO worker Deployment to override
# this command (pricing has no Celery task). Gunicorn with 2 Uvicorn workers mirrors
# the monolith api + svc-export; the api is light for svc-pricing (a single
# deterministic price-calc handler), so 1 replica × 2 gunicorn workers is ample.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
