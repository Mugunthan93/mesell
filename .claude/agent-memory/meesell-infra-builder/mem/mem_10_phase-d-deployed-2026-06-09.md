## Phase D DEPLOYED — 2026-06-09

**Live state:**
- `Deployment/api` 2/2 Running, `Deployment/worker` 2/2 Running in `dev` namespace
- Images: `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:v1.0.0` + `worker:v1.0.0` (worker reuses api image + celery CMD)
- Alembic head: `f31c75438e61` confirmed in pod
- `https://api.mesell.xyz/health` → 200 `{"status":"healthy","checks":{"postgres":"ok","valkey":"ok"}}`

**K8s Secret `backend-secrets` in `dev` namespace:**
- 20 keys. Created from GCP SM (10 app secrets) + in-cluster PG/Valkey credentials.
- KEY LESSON: Base64 passwords contain `+`, `/`, `@` — these BREAK Redis URL parsing if embedded raw. Always URL-encode with `urllib.parse.quote(pass, safe='')` when composing DATABASE_URL, VALKEY_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND.
- APP_ENV must be `"development"` (or `"staging"` or `"production"`) — NOT `"dev"`. The Pydantic Settings model uses a Literal type. Double-check before setting.

**Cloud Build SA quirk (2026-06-09):**
- Cloud Build in this project runs builds as `888244156264-compute@developer.gserviceaccount.com` (Compute Engine default SA), NOT `888244156264@cloudbuild.gserviceaccount.com`.
- Required granting both the compute SA and the Cloud Build SA: `roles/storage.admin` on `gs://project-1f5cbf72-2820-4cdb-949_cloudbuild` bucket AND `roles/artifactregistry.writer` on `meesell-prod-images`.
- The Cloud Build SA permissions were irrelevant (compute SA was the actual runner). Add a note on this when setting up CI/CD pipeline.

**K3s AR auth (2026-06-09):**
- K3s node does NOT have Docker or `docker-credential-gcr`. No `registries.yaml` was pre-configured.
- Solution: configure `/etc/rancher/k3s/registries.yaml` with metadata-server token (oauth2accesstoken from `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token`), restart K3s.
- Refresh cron installed: `/usr/local/bin/refresh-ar-token.sh` runs every 45 min, updates `registries.yaml`.
- For production, replace with `kubelet-credential-providers` config + GCP auth provider binary. The `registries.yaml` approach works fine for dev.
- Note: restarting K3s takes ~10s and all pods restart. Existing pods recover from existing images (no pull needed for cached layers).

**Dockerfile fix (2026-06-09):**
- Original `backend/Dockerfile` only copied `app/` directory. Missing: `alembic/`, `alembic.ini`, `scripts/`. Added all three. Without alembic, `alembic upgrade head` fails inside the pod.
- Worker Dockerfile (`Dockerfile.worker`) had V0 Playwright/Chromium install removed and CMD updated.

**CPU tuning for single-node dev VM (e2-standard-2, 2 vCPU):**
- Default resource requests (api: 500m, worker: 1000m) exceeded capacity with infra pods. Reduced to api: 200m, worker: 250m.
- Limits kept at api: 1000m, worker: 1000m (burst OK). Revisit on staging/prod with larger VM.

**Seeding status:**
- `seed_field_aliases.py` does NOT exist in `backend/scripts/`. No seed scripts were written in V1 backend construction. Deferred to backend team.
- The `data/` directory in `app/` has static JSON files (categories, shipping slabs, field aliases). At startup, `prewarm_top_categories` loads category data. No seed scripts needed for core functionality.

**Secret Manager — all 10 containers now populated:**
| Secret ID | Status |
|---|---|
| `refresh-token-pepper` | ✅ VERSION 1 LIVE |
| `razorpay-webhook-secret` | ✅ VERSION 1 LIVE (2026-06-09) |
| `langfuse-secret-key` | ✅ VERSION 1 LIVE (2026-06-09) |

All 10 SM secrets have at least 1 version. `backend-secrets` K8s secret contains: LANGFUSE_PUBLIC_KEY="pk-lf-disabled-v1" (V1 stub) and LANGFUSE_HOST="https://cloud.langfuse.com" (from configmap AND secret — secret takes precedence via envFrom order).

**Commits on branch `claude/meesell-project-setup-Tl7DS`:**
- `814d4c7` fix(worker): remove V0 playwright/chromium, fix celery -A path
- `880cc3d` fix(deploy): add alembic+scripts to Dockerfile, tune dev CPU requests

---
