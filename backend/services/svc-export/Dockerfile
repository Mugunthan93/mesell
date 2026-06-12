# backend/services/svc-export/Dockerfile
# ---------------------------------------------------------------------------
# svc-export — Sub-Plan A (export extraction), INFRA deliverable I1.
#
# ONE image serves BOTH the FastAPI api process AND the Celery worker process.
# The entrypoint differs at runtime (k8s/svc-export/deployment.yaml overrides the
# command for the worker container); the image is identical.
#
# Authority:
#   - docs/plans/infra/microservices_infra_plan.md §6 (one image, entrypoint differs)
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A (FROM the same Python
#     3.12 base; own main.py; service-specific requirements.txt) + §2.B (port 8001)
#   - mirrors backend/Dockerfile (api) + backend/Dockerfile.worker (worker) so the
#     integration build is a known quantity.
#
# Build context = backend/services/svc-export/ . The svc-export app tree
# (app/, alembic/, requirements.txt) is authored by the backend specialist lane
# in parallel; this Dockerfile is validated at integration against the spec'd
# tree shape (infra plan §2.2 / MASTER_PLAN §2.A):
#
#   backend/services/svc-export/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- backend lane (svc-export trimmed deps)
#   ├── app/                <- backend lane (main.py, vendored shared/ + core/, modules/export/)
#   │   ├── main.py         (FastAPI app on :8001 — public /api/v1/* + internal /internal/*)
#   │   └── workers/celery_app.py  (Celery app; export.xlsx task on default `celery` queue)
#   └── alembic/            <- backend lane (export-schema-rooted migration chain)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code + migrations. Alembic is required so the per-service migration
# Job (DEVOPS migration-before-deploy pattern, applied per-service) can run
# `alembic upgrade head` against the `export` schema inside this image.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-export listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map).
EXPOSE 8001

# DEFAULT entrypoint = the api process. The worker Deployment overrides this
# `command`/`args` with the Celery invocation (see k8s/svc-export/deployment.yaml).
# Gunicorn with 2 Uvicorn workers mirrors the monolith api; api is light for
# svc-export (job submission + poll), so 1 replica × 2 gunicorn workers is ample.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
