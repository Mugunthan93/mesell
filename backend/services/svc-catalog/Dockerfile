# backend/services/svc-catalog/Dockerfile
# ---------------------------------------------------------------------------
# svc-catalog — Sub-Plan H (catalog extraction — THE SPINE).
#
# PLACEHOLDER — the infra lead (meesell-infra-builder) authors the production
# Dockerfile + K8s manifests on feature/microservices-catalog/infra
# (handoff_msH_infra.md).  This stub exists so the service tree is complete and
# imports/tests run; the real image (multi-stage, non-root, healthcheck,
# LARGEST pool sizing — autosave write-heavy, NO worker) is the infra
# deliverable.
#
# SINGLE entrypoint — the FastAPI api process ONLY.  svc-catalog has NO Celery
# worker (catalog ships NO tasks.py — the autosave product_drafts upsert is
# synchronous inside patch_product).  The image carries NO worker entrypoint and
# the k8s manifest spawns NO worker Deployment.
#
# Authority:
#   - .claude/agent-memory/meesell-backend-coordinator/handoff_msH_infra.md
#   - docs/plans/microservices_migration/MASTER_PLAN.md §2.A / §2.B (port 8001)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
