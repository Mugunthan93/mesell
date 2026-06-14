# backend/services/svc-catalog/Dockerfile
# ---------------------------------------------------------------------------
# svc-catalog — Sub-Plan H (catalog extraction, MS-5), INFRA deliverable I1.
#
# THE SPINE. The LAST + RISKIEST extraction (MS-5, runs ALONE after MS-4). This
# completes the 8-services-on-one-node picture (monolith + export + dashboard +
# image + pricing + customer + category + iam + catalog).
#
# SINGLE entrypoint — the FastAPI api process ONLY. svc-catalog has NO Celery
# worker (verified — handoff_msH_infra.md §1: "catalog has zero background tasks —
# autosave draft upsert is SYNCHRONOUS inside patch_product; verified no
# shared_task/Celery in modules/catalog/"). The autofill Gemini call is also
# SYNCHRONOUS in-request (vendored ai_ops, NOT enqueued). So the image ships NO
# worker entrypoint and k8s/svc-catalog/deployment.yaml spawns NO worker
# Deployment. (Contrast svc-image/svc-export which DO ship a Celery worker; same
# shape as svc-category/svc-pricing/svc-customer/svc-iam — api-only.)
#
# Mirrors the PROVEN AI-bearing svc-category Dockerfile recipe (MS-F,
# backend/services/svc-category/Dockerfile) — the closest template: AI-bearing
# (google-genai + langfuse) + api-only single-CMD + owns a schema + cross-schema
# audit grant. The exact blend: AI dep set like svc-category/svc-image; api-only
# single-CMD like svc-pricing/svc-customer/svc-iam; NO openpyxl/Pillow/celery.
#
# Authority:
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msH_infra.md §1 (Dockerfile)
#   - docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md (Infra table)
#   - MASTER_PLAN §2.A (FROM python:3.12-slim; own main.py; service-specific
#     requirements.txt) + §2.B (port 8001) + §2.E line 207 (catalog gets the
#     LARGEST pool — see deployment.yaml replicas).
#
# ── DEFERRED-VALIDATION POSTURE (same as MS-A/MS-D/MS-F) ──────────────────────
# Build context = backend/services/svc-catalog/ . The svc-catalog app tree
# (app/, requirements.txt) is authored by the backend specialist lanes (svc
# branch) IN PARALLEL with this infra lane. At the time this Dockerfile is
# authored ONLY the db branch (feature/microservices-catalog/db @ c5eaad5) has
# pushed alembic/ + the schema-move migration a8f3b2e9c1d5; the svc branch has
# NOT yet pushed app/ or requirements.txt to the integration branch. COPY targets
# + the api entrypoint are authored against the SPEC'd tree shape; the backend
# lead re-derives them against the LANDED tree at the integration merge gate (the
# MS-A merge-gate lesson, infra MEMORY.md 2026-06-12: re-derive entrypoint /
# module-path from the LANDED tree, `git show <svc-branch>:.../requirements.txt`,
# grep `app = FastAPI`, confirm NO `app/workers/`, never trust the spec-era
# comment).
#
#   backend/services/svc-catalog/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- services-builder (svc-catalog trimmed deps:
#   │                          fastapi, sqlalchemy, asyncpg, redis, httpx,
#   │                          google-genai, langfuse; NO openpyxl/Pillow/celery)
#   ├── app/                <- backend lanes (svc branch)
#   │   └── main.py         (FastAPI app `app` on :8001 — 6 catalog routes behind
#   │                        FEATURE_CATALOG_FORM_ENABLED + 3-4 /internal/* shims)
#   └── alembic/            <- database-builder (db branch; schema-move chain rooted
#                              at a8f3b2e9c1d5, version_table_schema="catalog")
#
# NOTE — NO celery_app.py: unlike svc-image/svc-export, svc-catalog has no Celery
# instance and no `-Q` worker invocation. The single CMD below (gunicorn api) is
# the ONLY runtime entrypoint; k8s/svc-catalog/deployment.yaml does NOT override it.
#
# ── FEATURE_CATALOG_FORM_ENABLED MOUNT GUARD (handoff §3 / SUB_PLAN_0H R9) ─────
# catalog's monolith mount is behind FEATURE_CATALOG_FORM_ENABLED (main.py:126).
# The extracted svc-catalog app PRESERVES this guard internally (backend handles
# the app-layer guard per spec_msH_backend.md row 89/106/117 — "PRESERVE
# FEATURE_CATALOG_FORM_ENABLED guard"); the image just needs the flag in env (it
# comes from svc-catalog-config, see deployment.yaml). No Dockerfile change for the
# guard — it is app-layer routing logic. The Traefik route is gated equivalently by
# the app's internal guard (a flag-off env makes the app 404 the catalog routes).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# libpq for asyncpg/psycopg, gcc for any C-extension wheels (mirrors the monolith
# image + svc-category + svc-image). NO Pillow/JPEG libs (catalog decodes no
# images — the product-image refs it stores are GCS URLs written by image-svc, not
# decoded here) and NO openpyxl native deps (catalog builds no XLSX — the
# export-snapshot shim returns a JSON envelope, export-svc owns the XLSX/GCS write).
# The minimal native footprint for an AI-text service.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below,
# mirrors the monolith backend/Dockerfile + svc-category + svc-image + svc-pricing).
# The services-builder is sole-writer of requirements.txt and ships
# uvicorn[standard] but NOT gunicorn — so the infra image layer installs gunicorn
# explicitly, pinned to the monolith's exact version (gunicorn==22.0.0,
# backend/requirements.txt) so the served runtime is byte-identical to the monolith
# + sibling services. (This is the MS-A merge-gate fix: requirements.txt is backend
# sole-writer; the image layer is the correct infra-owned place to add gunicorn.)
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# step (DEVOPS migration-before-deploy pattern, applied per-service) can run
# `alembic upgrade head` against the `catalog` schema inside this image — including
# the schema-move migration a8f3b2e9c1d5 (ALTER TABLE ... SET SCHEMA catalog for
# the 3 tenant-scoped spine tables: catalogs, products, product_drafts).
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-catalog listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map).
EXPOSE 8001

# The ONLY entrypoint = the api process. There is NO worker Deployment to override
# this command (catalog has no Celery task). Gunicorn with 2 Uvicorn workers
# mirrors the monolith api + svc-category + svc-image + svc-pricing.
#
# NOTE on autosave write-heaviness + gunicorn workers: catalog is the autosave
# WRITE-heavy spine (PATCH /products/{id} autosaves the draft synchronously). The
# api Deployment runs the LARGEST replica pool of any service (MASTER_PLAN §2.E
# line 207; see deployment.yaml replicas:2) to spread the write load. -w 2 per pod
# × 2 replicas = 4 uvicorn workers fronting the autosave path. --timeout 120 covers
# the synchronous autofill Gemini call (the slowest in-request operation).
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
