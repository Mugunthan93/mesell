# backend/services/svc-iam/Dockerfile
# ---------------------------------------------------------------------------
# svc-iam — Sub-Plan G (iam extraction, THE AUTH AUTHORITY), INFRA deliverable I1.
#
# ONE image, ONE process: the FastAPI api server on :8001.
#
# *** NO WORKER ENTRYPOINT *** (contrast k8s/svc-export/Dockerfile + deployment,
# which carry a Celery worker override). iam has NO Celery app — it ships NO tasks.py
# (SUB_PLAN_0G §0.2 "iam has NO tasks.py (no Celery — confirmed by MASTER_PLAN §1.A
# 'Celery? no' for iam)"; handoff_msG_infra.md §1 I1). There is therefore no command
# override anywhere; this CMD is the only entrypoint. Same shape as svc-customer /
# svc-dashboard (the api-only twins).
#
# Authority:
#   - docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md §0.2 / "Code surfaces"
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A (same py3.12 base; own
#     main.py; service-specific requirements.txt) + §2.B (port 8001)
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msG_infra.md §1 I1
#     (FROM python:3.12-slim; single api process; NO worker;
#      requirements: fastapi/sqlalchemy/asyncpg/pydantic/redis/pyjwt/httpx —
#      NO gemini/langfuse/gcs/celery)
#   - mirrors backend/services/svc-customer/Dockerfile (the lightest api-only twin that
#     also OWNS a schema → this image likewise copies alembic/; iam owns schema `iam`
#     with the `users` schema-move migration chain).
#
# Build context = backend/services/svc-iam/ . The svc-iam app tree (app/,
# alembic/, requirements.txt, alembic.ini) is authored by the backend specialist lanes
# in parallel on feature/microservices-iam/backend (SUB_PLAN_0G "Agent lineup" —
# auth-builder owns the heavy lift incl. requirements.txt; services-builder owns the
# vendored shared scaffolding; database-builder owns the alembic chain). This Dockerfile
# is validated at the infra merge gate against the ACTUAL landed tree on the backend
# branch (the MS-A lesson: validate the entrypoint/module-path against the landed code,
# never the spec-era comment). Expected tree shape (SUB_PLAN_0G "Code surfaces"):
#
#   backend/services/svc-iam/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- backend lane: fastapi, uvicorn[standard], pydantic-settings,
#   │                          sqlalchemy[asyncio], asyncpg, redis, pyjwt, httpx,
#   │                          prometheus-client (NO celery/gemini/langfuse/gcs/openpyxl/rembg)
#   ├── alembic.ini         <- backend lane
#   ├── app/                <- backend lane (main.py 6-mw chain + plan_guard NO-OP;
#   │   │                       vendored core/auth.py BYTE-FOR-BYTE [A2/D7];
#   │   │                       vendored shared/{database,config,valkey}.py TRIMMED;
#   │   │                       router.py 6 public routes incl. FE-D5 cookie helpers;
#   │   │                       service/repository/domain/exceptions/schemas;
#   │   │                       *** NO /internal/* routes *** — iam is all-✗ [§0.4])
#   │   └── main.py         (FastAPI app `app` on :8001 — /api/v1/auth/* + /me +
#   │                        /api/v1/webhooks/razorpay; NO celery_app.py)
#   └── alembic/            <- backend lane (iam-schema-rooted migration chain;
#                              version_table_schema="iam"; the public.users → iam.users
#                              SET SCHEMA move + the 6-cross-schema-FK DROP, §0.7)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# + sibling-service images). iam is auth/payment CRUD — no Pillow/JPEG libs (no
# images), no rembg, no openpyxl (no XLSX), no GCS client. It DOES need libpq for the
# async Postgres driver (users table + audit_events INSERT).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + every sibling service). The backend
# lane's svc-iam requirements.txt ships uvicorn[standard] but NOT gunicorn (it is
# sole-writer for that file; infra must not edit it) — so the infra image layer
# installs gunicorn explicitly, pinned to the monolith's exact version
# (gunicorn==22.0.0, backend/requirements.txt) so the served runtime is byte-identical
# to the monolith and the sibling services. (MS-A gate lesson: gunicorn is NOT in the
# service requirements.txt — add it in the image layer, never edit the backend file.)
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# (DEVOPS migration-before-deploy pattern) can run `alembic upgrade head` against the
# `iam` schema inside this image (version_table_schema="iam"; the schema-move
# migration moves users public→iam + drops the 6 cross-schema FKs).
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-iam listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map →
# iam-svc:8001).
EXPOSE 8001

# DEFAULT (and ONLY) entrypoint = the api process. There is NO worker override
# anywhere (iam has no Celery). Gunicorn with 2 Uvicorn workers per pod mirrors the
# monolith api; iam runs 2 REPLICAS (Risk #2 — auth authority, no SPOF), so the
# cluster serves 2 pods × 2 gunicorn workers = 4 worker processes for login/refresh.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
