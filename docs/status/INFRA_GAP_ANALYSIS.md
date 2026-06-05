# Infrastructure Gap Analysis — MeeSell
**Produced by:** `meesell-infra-builder`
**Date:** 2026-06-05
**Based on:** Full scan of `infra/terraform/`, `k8s/`, `docs/MVP_ARCHITECTURE.md`, live GCP state

---

## Summary

Core infra (Pass 1 + 2 + 2b) is live and solid. `https://studio.mesell.xyz` is up.
Comparing the live infra against `MVP_ARCHITECTURE.md` reveals **11 gaps** before the
backend team can deploy and serve real traffic. Gaps are ranked P0–P3.

**P0 (deploy-breaking):** 4 gaps — nothing runs correctly without these.
**P1 (pre-first-user):** 4 gaps — deployment works but breaks at runtime.
**P2 (pre-AI-features):** 2 gaps — AI pipeline blocked without these.
**P3 (tracked, not urgent):** 1 gap.

---

## P0 — Deploy-Breaking (fix before ANY kubectl apply)

### GAP-01 · Namespace mismatch — CRITICAL
**What's wrong:**
All k8s manifests (`k8s/api.yaml`, `k8s/worker.yaml`, `k8s/frontend.yaml`,
`k8s/ingress.yaml`, `k8s/secrets.yaml.example`) use `namespace: meesell`.

Terraform (Pass 2) created namespaces: `dev`, `staging`, `traefik`.

The `meesell` namespace **does not exist** on the cluster. Every `kubectl apply`
will fail with `Error from server (NotFound): namespaces "meesell" not found`.

**Options:**
- **(A) Preferred** — Update all `k8s/` manifests to use `namespace: dev`.
  Matches the Terraform-managed namespace. Backend dev connects to
  `postgres.dev.svc.cluster.local` and `valkey.dev.svc.cluster.local` natively.
- **(B) Alternative** — Create a `meesell` namespace alongside `dev`.
  Cross-namespace DNS works (`postgres.dev.svc.cluster.local`) but adds
  confusion. Not recommended.

**Fix (Option A):**
`sed -i 's/namespace: meesell/namespace: dev/g' k8s/*.yaml`
Then update `postgres` host in `k8s/secrets.yaml.example`:
  `DATABASE_URL: postgresql+asyncpg://meesell:PASS@postgres.dev.svc.cluster.local:5432/meesell`
  `VALKEY_URL: redis://valkey.dev.svc.cluster.local:6379/0`
  (and CELERY_BROKER_URL, CELERY_RESULT_BACKEND similarly)

---

### GAP-02 · GCS bucket name mismatch
**What's wrong:**
Three different bucket names exist across project files:

| Source | Bucket name |
|--------|------------|
| Terraform (`dev.tfvars`) | `meesell-prod-assets` ← **actually provisioned** |
| `k8s/secrets.yaml.example` | `meesell-prod` |
| `MVP_ARCHITECTURE.md §10.8` | `meesell-images` |
| `MVP_ARCHITECTURE.md §11.5` | `meesell-audit-archive` |
| `k8s/worker.yaml` comment | `meesell-dev` ← the R&D bucket (wrong) |

The live bucket is `gs://meesell-prod-assets`. Workers will try to write to
wrong buckets (or fail on missing buckets). The audit archive bucket doesn't exist.

**Fix (recommended — single-bucket layout):**
Use `meesell-prod-assets` for everything via subdirectory paths:
```
gs://meesell-prod-assets/images/{user_id}/{product_id}/{idx}.jpg
gs://meesell-prod-assets/exports/{user_id}/{export_id}.zip
gs://meesell-prod-assets/audit-archive/{YYYY}/{MM}/{date}.jsonl.gz
```
- Update `k8s/secrets.yaml.example`: `GCS_BUCKET: "meesell-prod-assets"`
- Update `k8s/worker.yaml` comment to reference `meesell-prod-assets`
- Backend services use path prefixes to separate concerns — no new buckets needed
- Avoids bucket name global-uniqueness provisioning risk
- If separate buckets are preferred later, add a `audit_bucket` Terraform module

---

### GAP-03 · CORS domain mismatch
**What's wrong:**
`k8s/config.yaml` has:
```
CORS_ORIGINS: "https://meesell.in,https://www.meesell.in"
```
The actual domain is `mesell.xyz`. API will reject all frontend requests with CORS errors.

**Fix:**
Update `k8s/config.yaml`:
```yaml
CORS_ORIGINS: "https://mesell.xyz,https://www.mesell.xyz,https://app.mesell.xyz"
```
(Exact subdomains TBD — depends on whether frontend lands at `mesell.xyz` root or `app.mesell.xyz`.)

---

### GAP-04 · VM service account has no Artifact Registry pull permission
**What's wrong:**
The VM runs as the default Compute SA: `888244156264-compute@developer.gserviceaccount.com`

This SA was NOT granted `roles/artifactregistry.reader` during Pass 1.
The CI SA (`meesell-prod-ci@...`) has `artifactregistry.writer` but that's for CI push — not K3s pull.

K3s will fail to pull images from `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:latest` with:
`ErrImagePull: unauthorized: unauthenticated request`

**Fix:**
Option A (quick — no Terraform change):
```bash
gcloud artifacts repositories add-iam-policy-binding meesell-prod-images \
  --location=asia-south1 \
  --project=project-1f5cbf72-2820-4cdb-949 \
  --member="serviceAccount:888244156264-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

Option B (Terraform — add to `modules/artifact_registry/main.tf`):
Add a `google_artifact_registry_repository_iam_member` resource granting
the default Compute SA `artifactregistry.reader` so it's tracked in state.

**Recommended:** Option B (Terraform). The IAM binding stays in state, survives
a re-apply, and is documented. Add to `modules/artifact_registry/main.tf`.

---

## P1 — Pre-First-User (fix before going live)

### GAP-05 · Valkey `maxmemory` not configured
**What's wrong:**
Current Valkey args: `["--requirepass", "...", "--appendonly", "yes"]`

`MVP_ARCHITECTURE.md §6.9` specifies:
- `maxmemory 128mb`
- `maxmemory-policy allkeys-lru`

Without these, Valkey will grow unbounded and consume all 8 GB of the VM's RAM,
crowding out PostgreSQL, Celery workers, and the FastAPI pods.

**Fix:**
Edit `infra/terraform/modules/valkey/main.tf`, update args:
```hcl
args = [
  "--requirepass", "$(VALKEY_PASSWORD)",
  "--appendonly", "yes",
  "--maxmemory", "128mb",
  "--maxmemory-policy", "allkeys-lru"
]
```
Then run `terraform apply -target=module.valkey` (or include in Pass 3).
The StatefulSet will do a rolling restart — data on the 5GB PVC is preserved.

---

### GAP-06 · Missing production secrets
**What's wrong:**
`k8s/secrets.yaml.example` reveals 2 secrets needed at runtime that are not in
GCP Secret Manager (production namespace):

| Secret | Status | Impact if missing |
|--------|--------|------------------|
| `msg91-template-id` | **MISSING** — not in production SM | OTP send will fail at runtime (MSG91 requires template ID) |
| `audit-pii-salt` | **MISSING** — not in production SM | Audit PII scrubber crashes (§11.9) |
| `gcs-project-id` | Not a secret (use `project-1f5cbf72-2820-4cdb-949`) | N/A — put in ConfigMap |

Also note: `meesell-msg91-template-id` EXISTS in Secret Manager (R&D prefix) —
the template ID value is there, just under the wrong key name.

**Fix:**
```bash
# Retrieve from R&D secret (same MSG91 account)
TEMPLATE_ID=$(gcloud secrets versions access latest \
  --secret=meesell-msg91-template-id \
  --project=project-1f5cbf72-2820-4cdb-949 2>/dev/null)

# Populate production secret
printf "$TEMPLATE_ID" | gcloud secrets create msg91-template-id \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-

# Generate audit PII salt
printf "$(openssl rand -hex 32)" | gcloud secrets create audit-pii-salt \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
```
Also add `msg91-template-id` and `audit-pii-salt` to `dev.tfvars`
`app_secret_ids` list so future `terraform apply` manages them.

---

### GAP-07 · `api.mesell.xyz` DNS record and Traefik Ingress not configured
**What's wrong:**
Only `studio.mesell.xyz` has a DNS A record and Traefik Ingress + TLS cert.

The backend team needs `api.mesell.xyz → 35.234.223.66` to be reachable
with HTTPS. Frontend needs either `mesell.xyz` root or `app.mesell.xyz`.

The existing `infra/terraform/modules/ingress/main.tf` only wires `studio.{domain}`.

**Fix — three-step:**
1. **DNS** (Namecheap): Add A records:
   - `api.mesell.xyz → 35.234.223.66`
   - `app.mesell.xyz → 35.234.223.66` (or `@` for root — TBD with frontend team)

2. **Terraform Ingress module** — extend `modules/ingress/main.tf` to add
   a second `rule` block for `api.{var.domain}` routing to the API service,
   and a third for `app.{var.domain}` / root routing to the frontend service.
   Add TLS entries for both new hostnames.

3. **cert-manager** — add `api.mesell.xyz` and `app.mesell.xyz` to the existing
   `Certificate` resource (or use a wildcard cert `*.mesell.xyz`).
   Wildcard requires DNS-01 challenge (Namecheap DNS provider plugin for cert-manager)
   vs HTTP-01 (simpler, already working for studio). For V1, two separate HTTP-01
   certs is simpler. Wildcard deferred to V1.5.

**Founder decision needed:** does frontend land at `mesell.xyz` root or `app.mesell.xyz`?

---

### GAP-08 · VM default SA needs GCS write permission on `meesell-prod-assets`
**What's wrong:**
Worker pods (Celery, image processor) run as VM SA
`888244156264-compute@developer.gserviceaccount.com`.
`k8s/worker.yaml` says pods use GCE metadata server for keyless auth —
meaning they authenticate as this SA.

But this SA has no IAM binding on `gs://meesell-prod-assets` (our production bucket).
Workers will fail to write product images and exports with `403 Forbidden`.

**Fix:**
```bash
gcloud storage buckets add-iam-policy-binding gs://meesell-prod-assets \
  --member="serviceAccount:888244156264-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin" \
  --project=project-1f5cbf72-2820-4cdb-949
```
Also add this binding to `modules/asset_bucket/main.tf` to keep it in Terraform state.

---

## P2 — Pre-AI-Features

### GAP-09 · LangFuse not provisioned
**What's wrong:**
`MVP_ARCHITECTURE.md §9.6` requires LangFuse SDK for tracing all 3 Gemini
workloads (picker, autofill, watermark). No infra exists for it.

**Two options — founder decision needed:**

| Option | Complexity | Cost | Infra work |
|--------|-----------|------|-----------|
| **SaaS (langfuse.com)** | Low | Free tier generous (~50K traces/month) | Add `langfuse-public-key` + `langfuse-secret-key` to Secret Manager |
| **Self-hosted on K3s** | Medium | ~100–150MB RAM on the VM | New Terraform K8s Deployment module + Postgres schema extension |

**Recommendation for V1:** SaaS. The free tier covers early launch easily.
Switch to self-hosted when traces exceed free tier or data-sovereignty matters.

**Fix (SaaS path):**
1. Founder creates account at cloud.langfuse.com, creates a project.
2. Populate two new secrets:
   ```bash
   printf "$LANGFUSE_PUBLIC_KEY" | gcloud secrets create langfuse-public-key \
     --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
   printf "$LANGFUSE_SECRET_KEY" | gcloud secrets create langfuse-secret-key \
     --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
   ```
3. Add both to `k8s/secrets.yaml.example` and backend team wires them in `config.py`.

---

### GAP-10 · Celery workers not in Terraform (raw k8s manifests only)
**What's wrong:**
`k8s/worker.yaml` exists as a hand-written manifest (from R&D era).
No `modules/worker/` in `infra/terraform/modules/`.

This means Celery worker pods are outside Terraform state — no drift detection,
no version-pinned rollouts, inconsistent with how all other K8s resources are managed.

This is a consistency gap, not a blocking gap — `kubectl apply -f k8s/worker.yaml`
will still work once GAP-01 namespace is fixed.

**Fix (Pass 3 Terraform work):**
Add `modules/worker/` to manage the Celery Deployment alongside Pass 2 resources.
Include in the same Pass 3 plan as `modules/backend/` and `modules/frontend/`.
Defer until backend image is built and pushed (nothing to manage until image exists).

---

## Decisions — LOCKED (2026-06-05)

| # | Decision | Answer |
|---|---------|--------|
| D1 | Frontend subdomains | `dev.mesell.xyz` (dev), `testing.mesell.xyz` (QA), `staging.mesell.xyz` (staging), `www.mesell.xyz` (prod) |
| D2 | LangFuse hosting | **DEFERRED to V1.5** — GAP-09 moved to P3 |
| D3 | GCS layout | **Single bucket** `meesell-prod-assets` with subdirectory paths |
| D4 | API routing | **`api.mesell.xyz`** subdomain |

---

## Remediation Plan — Ordered Execution

### Phase A — Infra-only fixes (no backend needed, can do now)
| Task | Gap | Who | Time |
|------|-----|-----|------|
| A1. Grant default Compute SA `artifactregistry.reader` | GAP-04 | infra-builder | 2 min |
| A2. Grant default Compute SA `storage.objectAdmin` on `meesell-prod-assets` | GAP-08 | infra-builder | 2 min |
| A3. Configure Valkey `maxmemory 128mb + allkeys-lru` in TF + apply | GAP-05 | infra-builder | 10 min |
| A4. Populate `msg91-template-id` + `audit-pii-salt` in Secret Manager | GAP-06 | infra-builder | 5 min |
| A5. Add missing SM entries to `dev.tfvars` + TF module | GAP-06 | infra-builder | 5 min |

### Phase B — Decisions locked, ready to execute after Phase A
| Task | Gap | Who | Est. |
|------|-----|-----|------|
| B1. Add 5 DNS A records via Playwright MCP (api, dev, testing, staging, www → 35.234.223.66) | GAP-07 | infra-builder (Playwright) | 5 min |
| B2. Extend `modules/ingress/main.tf` — add routes for api + dev + staging + www; TLS SAN cert for all 5 | GAP-07 | infra-builder | 25 min |
| B3. Update `k8s/config.yaml` CORS_ORIGINS to all 4 frontend subdomains on mesell.xyz | GAP-03 | infra-builder | 2 min |
| B4. Update all `k8s/` manifests: `namespace: meesell` → `namespace: dev` | GAP-01 | infra-builder | 5 min |
| B5. Update `k8s/secrets.yaml.example`: bucket name → `meesell-prod-assets`, service hosts → `*.dev.svc.cluster.local` | GAP-02 + GAP-01 | infra-builder | 5 min |
| B6. `terraform apply` extended ingress (certs issue for 4 new subdomains ~2 min each) | GAP-07 | infra-builder | 15 min |

DNS records needed (all A → 35.234.223.66):
- `api.mesell.xyz`
- `dev.mesell.xyz`
- `testing.mesell.xyz`
- `staging.mesell.xyz`
- `www.mesell.xyz`

TLS strategy: multi-domain SAN Certificate via HTTP-01 (5 hostnames in one cert-manager Certificate resource).
Wildcard `*.mesell.xyz` deferred — requires DNS-01 + Namecheap cert-manager plugin (V1.5).

### Phase C — Deferred (LangFuse)
GAP-09 moved to P3. No action needed until V1.5.

### Phase D — After backend image is built (deferred)
| Task | Gap | Who | Time |
|------|-----|-----|------|
| D1. Add `modules/worker/` Terraform module | GAP-10 | infra-builder | 30 min |
| D2. Add `modules/backend/` and `modules/frontend/` Terraform modules | — | infra-builder | 45 min |

---

## What This Unblocks

After Phases A + B:
- ✅ Backend team can `kubectl apply` all manifests without errors
- ✅ API accessible at `https://api.mesell.xyz` with TLS
- ✅ Worker pods can write to `gs://meesell-prod-assets`
- ✅ K3s can pull Docker images from Artifact Registry
- ✅ CORS allows frontend requests
- ✅ All 7 required secrets available in Secret Manager

After Phase C:
- ✅ AI pipeline tracing active from first Gemini call

After Phase D:
- ✅ All K8s resources in Terraform state (full drift detection)

---

## Appendix — Live Infra Reference

| Resource | Value |
|----------|-------|
| VM external IP | `35.234.223.66` |
| VM service account | `888244156264-compute@developer.gserviceaccount.com` |
| Production GCS bucket | `gs://meesell-prod-assets` |
| Artifact Registry | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images` |
| PostgreSQL (in-cluster) | `postgres.dev.svc.cluster.local:5432` |
| Valkey (in-cluster) | `valkey.dev.svc.cluster.local:6379` |
| Terraform state | `mesell/infra/terraform/terraform.tfstate` (local) |
| K8s config | `~/.kube/meesell-dev.yaml` |
