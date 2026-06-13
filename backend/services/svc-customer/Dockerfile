# backend/services/svc-customer/Dockerfile
# ---------------------------------------------------------------------------
# svc-customer — Sub-Plan E (customer extraction), INFRA deliverable I1.
#
# ONE image, ONE process: the FastAPI api server on :8001.
#
# *** NO WORKER ENTRYPOINT *** (contrast k8s/svc-export/Dockerfile + deployment,
# which carry a Celery worker override). customer has NO Celery app — it is a pure
# FastAPI request/response CRUD service (SUB_PLAN_0E §2 "ships NO Celery app";
# spec_msE_backend.md:17 "no tasks.py — grep shared_task customer/ = 0"). There is
# therefore no command override anywhere; this CMD is the only entrypoint.
#
# Authority:
#   - docs/plans/microservices_migration/SUB_PLAN_0E_customer_extraction.md §2/§3
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A (same py3.12 base; own
#     main.py; service-specific requirements.txt) + §2.B (port 8001)
#   - handoff_msE_infra.md §1 I1 (FROM python:3.12-slim; single api process; NO worker)
#   - mirrors backend/services/svc-dashboard/Dockerfile (the lightest api-only twin)
#     EXCEPT customer OWNS a schema → this image also copies alembic/ (dashboard owns
#     no tables and has no alembic; customer has a schema-split migration chain).
#
# Build context = backend/services/svc-customer/ . The svc-customer app tree
# (app/, alembic/, requirements.txt) is authored by the backend specialist lanes in
# parallel (spec_msE_backend.md PHASE A + PHASE B). This Dockerfile is validated at
# the infra merge gate against the ACTUAL landed tree on the backend branch (the
# MS-A lesson: validate the entrypoint/module-path against the landed code, never
# the spec-era comment). Expected tree shape (spec_msE_backend.md:58):
#
#   backend/services/svc-customer/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- backend lane (NO celery/gemini/langfuse/openpyxl/gcs)
#   ├── app/                <- backend lane (main.py 6-mw + plan_guard NO-OP; vendored
#   │   │                       shared/{database,config,valkey}.py TRIMMED; core/*;
#   │   │                       router.py 5 public + internal_routes.py 3 /internal/*;
#   │   │                       service/repository/domain/exceptions; category_client shim)
#   │   └── main.py         (FastAPI app `app` on :8001 — public /api/v1/seller-profile/*
#   │                        + internal /internal/seller-profile/*; NO celery_app.py)
#   └── alembic/            <- backend lane (customer-schema-rooted migration chain;
#                              version_table_schema="customer"; the schema-split
#                              migration a9f3b2c5e1d8 moves seller_profile public→customer)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# + sibling-service images). customer is query-light CRUD — no Pillow/JPEG libs
# (no images), no rembg, no openpyxl (no XLSX), no GCS client.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + every sibling service). The backend
# lane's svc-customer requirements.txt ships uvicorn[standard] but NOT gunicorn (it
# is sole-writer for that file; infra must not edit it) — so the infra image layer
# installs gunicorn explicitly, pinned to the monolith's exact version
# (gunicorn==22.0.0, backend/requirements.txt) so the served runtime is byte-identical
# to the monolith and the sibling services. (MS-A gate lesson: gunicorn is NOT in the
# service requirements.txt — add it in the image layer, never edit the backend file.)
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# (DEVOPS migration-before-deploy pattern) can run `alembic upgrade head` against the
# `customer` schema inside this image (version_table_schema="customer"; the schema-
# split migration moves seller_profile public→customer).
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-customer listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map →
# customer-svc:8001).
EXPOSE 8001

# DEFAULT (and ONLY) entrypoint = the api process. There is NO worker override
# anywhere (customer has no Celery). Gunicorn with 2 Uvicorn workers mirrors the
# monolith api; customer is light (5 public CRUD endpoints + 3 /internal shims), so
# 1 replica × 2 gunicorn workers is ample.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
