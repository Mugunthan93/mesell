# backend/services/svc-image/Dockerfile
# ---------------------------------------------------------------------------
# svc-image — Sub-Plan C (image extraction), INFRA deliverable I1.
#
# ONE image serves BOTH the FastAPI api process AND the dedicated Celery worker
# process. The entrypoint differs at runtime (k8s/svc-image/deployment.yaml
# overrides the command for the worker container); the image is identical.
# Mirrors the PROVEN MS-A svc-export Dockerfile recipe (backend/services/svc-export/
# Dockerfile) — svc-image is the recipe-copy with the image-specific deps below.
#
# Authority:
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msC_infra.md §1 I1
#   - spec_msC_backend_EXECUTION.md §0.5 / §1.B1 (requirements set)
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A (one image, own main.py,
#     service-specific requirements.txt) + §2.B (port 8001)
#
# ── IMAGE-SIZE RATIONALE (handoff §1 I1 IMAGE-SIZE FLAG; §3 D3 mitigation) ──────
#   svc-image is the HEAVIEST early-wave service. Its image carries, BEYOND the
#   svc-export baseline (fastapi/sqlalchemy/asyncpg/celery/redis/httpx + gunicorn):
#     • Pillow                (~30 MB native libs — JPEG/PNG decode for precheck +
#                              the ai_ops watermark composite)
#     • google-cloud-storage  (image upload/download + v4 signed URLs)
#     • the vendored ai_ops deps: google-generativeai (Gemini SDK) + langfuse
#                              (tracing) — image IS AI-consuming (watermark.v1),
#                              UNLIKE the deterministic svc-export.
#   This lands a meaningfully larger image than svc-export but stays in the
#   low-hundreds-of-MB range (slim base + Pillow + two pure-python-ish SDKs).
#
#   *** rembg is DELIBERATELY DEFERRED (NOT installed). ***
#   Rationale (handoff §1 I1 + spec §0.5 + §3.G):
#     • ZERO live call sites — `rembg` was declared in the monolith requirements
#       (requirements.txt:14) but never invoked anywhere in backend/app. Carrying
#       it into svc-image would ship dead weight.
#     • Carrying rembg pulls in onnxruntime (~300 MB+) AND forces pre-baking the
#       u2net ONNX model (~170 MB) into the image to avoid a first-run pod
#       download — a multi-hundred-MB layer + a fat runtime working set.
#     • Deferring rembg is the CHEAPEST D3 VM-fit mitigation (handoff §3): it cuts
#       both the image size AND the worker's resident memory ceiling (no ONNX
#       session in RAM), keeping svc-image inside the current e2-standard-2 node.
#   If the founder/AI-lead later decide to carry rembg (a FRESH decision per §3.G),
#   add `rembg` + `onnxruntime` here, PRE-BAKE the u2net model, and RE-RUN the §3
#   capacity math (the +~470 MB image + ONNX working set likely tips the node →
#   D3 e2-standard-4 founder ask). Until then: NOT installed.
#
# Build context = backend/services/svc-image/ . The svc-image app tree (app/,
# alembic/, requirements.txt) is authored by the backend specialist lanes
# (database-builder + services-builder + api-routes-builder) IN PARALLEL with this
# infra lane; at the time this Dockerfile is authored that tree is NOT yet on the
# integration branch. COPY targets are validated against the spec'd tree shape
# (spec §1.B1) at the backend lead's integration merge gate — the SAME deferred-
# validation posture the MS-A svc-export Dockerfile used (it was validated against
# the landed backend tree at the merge gate, see its header).
#
#   backend/services/svc-image/
#   ├── Dockerfile          <- this file (I1)
#   ├── requirements.txt    <- services-builder (svc-image trimmed deps; NO rembg,
#   │                          NO openpyxl, NO msg91/razorpay; +pillow +gcs +ai_ops)
#   ├── app/                <- backend lanes
#   │   ├── main.py         (FastAPI app `app` on :8001 — public /api/v1/products/{id}/images
#   │   │                    ×2 + internal /internal/products/{product_id}/images)
#   │   └── celery_app.py   (Celery instance `celery_app`; single image task on the
#   │                        DEDICATED `svc-image` queue — task_default_queue=svc-image)
#   └── alembic/            <- database-builder (image-schema-rooted migration chain;
#                              version_table_schema="image")
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Native deps:
#   libpq-dev  — asyncpg/psycopg build + runtime (mirrors monolith + svc-export).
#   gcc        — C-extension wheels.
#   libjpeg62-turbo, zlib1g — Pillow runtime image codecs (JPEG/PNG). Pillow wheels
#                ship most natives, but the turbo JPEG lib + zlib are the safe
#                runtime set for product-image decode (svc-export did NOT need these
#                — this is the image-specific delta).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first for build-cache efficiency.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# gunicorn is the production process manager for the api container (CMD below),
# mirroring the monolith backend/Dockerfile + the svc-export image. The
# services-builder is sole-writer of requirements.txt and ships uvicorn[standard]
# but NOT gunicorn — so the infra image layer installs gunicorn explicitly, pinned
# to the monolith's exact version (gunicorn==22.0.0, backend/requirements.txt) so
# the served runtime is byte-identical to the monolith + svc-export.
RUN pip install --no-cache-dir gunicorn==22.0.0

# Application code + migrations. Alembic is required so the per-service migration
# step (DEVOPS migration-before-deploy pattern) can run `alembic upgrade head`
# against the `image` schema inside this image.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# svc-image listens on 8001 (MASTER_PLAN §2.B / §2.C path-prefix gateway map).
EXPOSE 8001

# DEFAULT entrypoint = the api process. The worker Deployment overrides this
# `command`/`args` with the Celery invocation (see k8s/svc-image/deployment.yaml).
# Gunicorn with 2 Uvicorn workers mirrors the monolith api + svc-export; the api is
# light for svc-image (upload submit + list/poll + signed-URL gen), so 1 replica ×
# 2 gunicorn workers is ample.
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "--timeout", "120"]
