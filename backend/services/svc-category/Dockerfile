# backend/services/svc-category/Dockerfile
# ---------------------------------------------------------------------------
# svc-category — Sub-Plan F (category extraction, MS-4), INFRA deliverable I1.
#
# SINGLE entrypoint — the FastAPI api process ONLY. svc-category has NO Celery
# worker (verified: backend/app/modules/category/ ships NO tasks.py — category is
# read-heavy, cache-fronted: 5 public GET routes + 2-3 /internal/* shims; smart
# picker calls Gemini SYNCHRONOUSLY in-request via vendored ai_ops, NOT enqueued).
# The image therefore carries NO worker entrypoint and the k8s manifest spawns NO
# worker Deployment. (Contrast svc-image/svc-export which DO ship a Celery worker.)
#
# Mirrors the PROVEN AI-bearing svc-image Dockerfile recipe
# (backend/services/svc-image/Dockerfile) MINUS the Celery worker path, and the
# pricing/customer recipe (api-only, no worker) PLUS the AI SDK deps. The exact
# blend: AI dep set (google-genai + langfuse) like svc-image; api-only single-CMD
# like svc-pricing/svc-customer; NO openpyxl/Pillow/celery.
#
# Authority:
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msF_infra.md §1 (Dockerfile)
#   - docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md (Infra table)
#   - MASTER_PLAN §2.A (FROM python:3.12-slim; own main.py; service-specific
#     requirements.txt) + §2.B (port 8001)
#
# Build context = backend/services/svc-category/ . The svc-category app tree
# (app/, alembic/, requirements.txt) is authored by the backend specialist lanes
# (svc / db branches) IN PARALLEL with this infra lane; at the time this Dockerfile
# is authored the app/ tree is NOT yet on the integration branch (the db branch has
# alembic/ + the schema-move migration c4f1e7a9d302; the svc branch has not yet
# pushed app/). COPY targets are validated against the LANDED tree shape at the
# backend lead's integration merge gate — the SAME deferred-validation posture the
# MS-A svc-export + MS-D svc-pricing Dockerfiles used (validated against the landed
# backend tree at the merge gate; see MS-A merge-gate lesson in infra MEMORY.md
# 2026-06-12: re-derive entrypoint / module-path / queue from the LANDED tree,
# never the spec-era comment).
#
#   backend/services/svc-category/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- services-builder (svc-category trimmed deps:
#   │                          fastapi, sqlalchemy, asyncpg, redis, httpx,
#   │                          google-genai, langfuse; NO openpyxl/Pillow/celery)
#   ├── app/                <- backend lanes (svc branch)
#   │   └── main.py         (FastAPI app `app` on :8001 — 5 public GET routes +
#   │                        2-3 /internal/* shims; cache pre-warm in the lifespan)
#   └── alembic/            <- database-builder (db branch; schema-move chain rooted
#                              at c4f1e7a9d302, version_table_schema="category")
#
# NOTE — NO celery_app.py: unlike svc-image/svc-export, svc-category has no Celery
# instance and no `-Q` worker invocation. The single CMD below (gunicorn api) is the
# ONLY runtime entrypoint; k8s/svc-category/deployment.yaml does NOT override it.
#
# ── CACHE PRE-WARM (handoff §2 — heaviest cache consumer) ──────────────────────
# The full-tree + top-100-schema pre-warm runs INSIDE the FastAPI lifespan (app
# startup), NOT as a separate init container or build step. The readiness probe
# (deployment.yaml) gates traffic until the lifespan completes — so the pod reports
# Ready only AFTER the Valkey DB-3 cache is warm. No Dockerfile change is needed for
# the pre-warm; it is app-layer lifespan logic. The image just needs the redis
# client (in requirements.txt) reachable at the VALKEY_URL DB-3 mount (secrets I7).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# image + svc-image + svc-pricing). NO Pillow/JPEG libs (category decodes no images)
# and NO openpyxl native deps (category builds no XLSX) — the minimal native
# footprint for an AI-text service.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + svc-image + svc-pricing). The
# services-builder is sole-writer of requirements.txt and ships uvicorn[standard]
# but NOT gunicorn — so the infra image layer installs gunicorn explicitly, pinned
# to the monolith's exact version (gunicorn==22.0.0, backend/requirements.txt) so
# the served runtime is byte-identical to the monolith + sibling services.
# (This is the MS-A merge-gate fix: requirements.txt is backend sole-writer; the
# image layer is the correct infra-owned place to add gunicorn.)
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# step (DEVOPS migration-before-deploy pattern, applied per-service) can run
# `alembic upgrade head` against the `category` schema inside this image — including
# the schema-move migration c4f1e7a9d302 (ALTER TABLE ... SET SCHEMA category for
# the 4 global tables: categories, templates, field_enum_values, field_aliases).
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-category listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map).
EXPOSE 8001

# The ONLY entrypoint = the api process. There is NO worker Deployment to override
# this command (category has no Celery task). Gunicorn with 2 Uvicorn workers
# mirrors the monolith api + svc-image + svc-pricing.
#
# NOTE on the cache pre-warm + gunicorn workers: the full-tree pre-warm runs in the
# FastAPI lifespan, which executes ONCE PER gunicorn worker process. With -w 2 the
# pre-warm runs twice (once per worker) — both populate the SAME shared Valkey DB-3
# keyspace (idempotent single-flight per handoff §2: the 291 brand-pattern enums are
# single-flighted so the second worker's pre-warm is a cheap cache-hit pass). This
# is acceptable for dev. The readiness probe's initialDelaySeconds budget
# (deployment.yaml) accounts for the lifespan pre-warm latency.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
