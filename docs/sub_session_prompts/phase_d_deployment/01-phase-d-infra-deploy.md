# Phase D — Infra Deploy Dispatch Prompt

**Agent:** `meesell-infra-builder`
**Trigger:** §22 V1 GO achieved (9/9 PASS, Attempt #3, 2026-06-09)
**Goal:** Deploy V1 backend to `dev` namespace on K3s cluster (meesell-dev VM, asia-south1)
**Branch:** `claude/meesell-project-setup-Tl7DS`

---

```
You are meesell-infra-builder. You are operating on the MeeSell project.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask.

---

MISSION: Phase D — Deploy V1 backend to the `dev` namespace on the K3s cluster on the GCP VM
(meesell-dev, asia-south1). The V1 backend has passed §22 acceptance (9/9). Your job is to get
it running on the cluster.

CONTEXT:
- Backend code is on branch `claude/meesell-project-setup-Tl7DS` (committed, not yet pushed)
- GCP Secret Manager: 10 containers. Verify `razorpay-webhook-secret` and `langfuse-secret-key`
  have at least 1 version BEFORE step 5 (`gcloud secrets versions list --secret=razorpay-webhook-secret`).
  If zero versions, STOP and ask the founder to populate them. All other 8 secrets are confirmed populated.
- K8s manifests are in `k8s/` — api.yaml, worker.yaml, config.yaml, namespace.yaml,
  secrets.yaml.example
- DB migration head: `f31c75438e61` (baseline → pg_trgm/GIN → product_drafts_saved_at)
- GCP VM: meesell-dev @ 35.234.223.66, K3s v1.35.5+k3s1
- Artifact Registry: see docs/INFRASTRUCTURE_ARCHITECTURE.md for repo URL

BEFORE STARTING — read these files in order:
1. docs/INFRASTRUCTURE_PLAYBOOK.md — full deployment protocol (your primary contract)
2. docs/status/STATUS_INFRA.md — current infra state
3. k8s/secrets.yaml.example — GCP → K8s secret mappings with exact gcloud commands
4. k8s/config.yaml — non-secret env vars (LANGFUSE_PUBLIC_KEY = "pk-lf-disabled-v1" for V1)
5. backend/alembic/versions/ — confirm migration head
6. .claude/agent-memory/meesell-infra-builder/MEMORY.md — your own memory

PHASE D ACTION PLAN:
1. SSH to GCP VM (`meesell-dev`, 35.234.223.66) — verify K3s cluster health (`kubectl get nodes`)
2. Fix `backend/Dockerfile.worker` BEFORE building:
   a. Remove the `RUN playwright install --with-deps chromium` line (V0 leftover, not needed in V1)
   b. Replace the CMD with: `CMD ["celery", "-A", "app.workers.celery_app", "worker",
      "--concurrency=4", "--max-tasks-per-child=100", "--loglevel=info"]`
      (no `-Q` flag — queue scoping is handled by celery_app.py INCLUDE list per §18.B)
   c. Commit the fix to branch `claude/meesell-project-setup-Tl7DS`
3. Push branch `claude/meesell-project-setup-Tl7DS` to GitHub origin
   (git push origin claude/meesell-project-setup-Tl7DS)
   NOTE: MeeSell is on GitHub, NOT GitLab. Confirm remote URL with `git remote -v` first.
4. Build + push Docker API image: `backend/Dockerfile` → Artifact Registry
   (asia-south1-docker.pkg.dev/... as per INFRA docs). Tag: `v1.0.0`
   BUILD LOCATION: No local Docker available (disk constraint). Build on the GCP VM:
   SSH to VM → authenticate to Artifact Registry → `docker build` + `docker push` from VM.
   If Docker is not installed on VM: use `gcloud builds submit --tag <image-url> backend/`
   as a one-time Cloud Build fallback.
5. Build + push Docker worker image: `backend/Dockerfile.worker` → Artifact Registry. Tag: `v1.0.0`
   (same build location rules as step 4 — build on VM or Cloud Build)
6. Create `backend-secrets` K8s Secret in `dev` namespace using values from GCP Secret Manager:
   DATABASE_URL, VALKEY_URL, JWT_SECRET, REFRESH_TOKEN_PEPPER (← refresh-token-pepper),
   MSG91_AUTH_KEY, MSG91_TEMPLATE_ID, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
   RAZORPAY_WEBHOOK_SECRET (← razorpay-webhook-secret), GEMINI_API_KEY,
   GCS_BUCKET, GCS_PROJECT_ID, LANGFUSE_PUBLIC_KEY (pk-lf-disabled-v1),
   LANGFUSE_SECRET_KEY (← langfuse-secret-key), LANGFUSE_HOST (https://cloud.langfuse.com),
   AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS (https://studio.mesell.xyz), APP_ENV (dev).
   See k8s/secrets.yaml.example for exact gcloud commands.
7. Update k8s/config.yaml LANGFUSE_PUBLIC_KEY to "pk-lf-disabled-v1" if not already set.
8. Apply K8s manifests in order:
   namespace.yaml → postgres (if not running) → valkey (if not running) → api.yaml → worker.yaml
9. Run Alembic migrations:
   `kubectl exec -n dev deploy/meesell-api -- alembic upgrade head`
10. Smoke test: `curl https://api.mesell.xyz/health` → expect HTTP 200 `{"status": "ok"}`
11. Run seed scripts if DB is fresh:
    `kubectl exec -n dev deploy/meesell-api -- python scripts/seed_field_aliases.py`
    (and category seed if needed)

SUCCESS CRITERIA:
- API pod 2/2 replicas Running
- Worker pod 2/2 replicas Running
- `curl https://api.mesell.xyz/health` returns 200
- `curl https://api.mesell.xyz/api/v1/categories` returns 200 (categories seeded)
- Alembic head = f31c75438e61

SCOPE OUT:
- Do NOT touch meesell-vm (34.93.9.139, R&D) — only meesell-dev is in scope
- Do NOT commit docs/BACKEND_ARCHITECTURE.md (it has an uncommitted 208-line working-tree mod
  — leave it untouched, not your concern)
- Do NOT modify other projects (Aletheia, Prospero, JETK, etc.)
- Do NOT deploy to staging or prod namespace — dev only for now

After completing, append an `=== UPDATE: 2026-06-... — Phase D DEPLOYED ===` block to
docs/status/STATUS_INFRA.md with: what was deployed, image tags used, migration head confirmed,
smoke test result, any D-flags. Update your own memory at
.claude/agent-memory/meesell-infra-builder/MEMORY.md.
```

---

## Reference: Pre-flight checklist

| Item | Status |
|------|--------|
| 8 GCP secrets populated | ✅ verified §22 attempt #3 |
| `razorpay-webhook-secret` has ≥1 version | ⏳ infra-builder to verify (step 1 pre-check) |
| `langfuse-secret-key` has ≥1 version | ⏳ infra-builder to verify (step 1 pre-check) |
| `backend/Dockerfile` present | ✅ |
| `backend/Dockerfile.worker` present | ✅ |
| `k8s/*.yaml` manifests present | ✅ |
| `k8s/secrets.yaml.example` with gcloud commands | ✅ |
| `k8s/config.yaml` LANGFUSE_PUBLIC_KEY placeholder | ⏳ infra-builder to set |
| GCP VM SSH reachable | ⏳ infra-builder to verify |
| K3s cluster healthy | ⏳ infra-builder to verify |
| `backend-secrets` K8s Secret | ⏳ needs creation |
| `Dockerfile.worker` V0 CMD fixed | ⏳ infra-builder step 2 |
| Branch pushed to GitHub | ⏳ infra-builder step 3 |

## Reference: Secret Manager → K8s Secret mapping

| K8s env var | GCP Secret Manager name |
|-------------|------------------------|
| REFRESH_TOKEN_PEPPER | refresh-token-pepper |
| RAZORPAY_WEBHOOK_SECRET | razorpay-webhook-secret |
| LANGFUSE_SECRET_KEY | langfuse-secret-key |
| LANGFUSE_PUBLIC_KEY | pk-lf-disabled-v1 (hardcoded placeholder) |
| All others | Already in infra / derive from existing SM values |

## Reference: What Phase D does NOT need to do

- No Terraform changes — infra is fully provisioned (49 TF resources, drift clean)
- No cert-manager changes — TLS already live on all 5 subdomains
- No Valkey config changes — maxmemory=128MB + allkeys-lru already set
- No DB schema changes — migration head f31c75438e61 is the final V1 schema

## Authored by

Master session (mesell-master-session-2), 2026-06-09. Based on backend session Phase D
handoff block in docs/status/STATUS_BACKEND.md Updates Log (bottom entry).
