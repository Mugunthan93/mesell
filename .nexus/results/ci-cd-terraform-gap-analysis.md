# CI/CD ↔ Terraform Gap Analysis — MeeSell

**Date:** 2026-05-30
**Author:** infra-builder (Nexus)
**Project:** mesell (GCP project `project-1f5cbf72-2820-4cdb-949`, org `698205129974`)
**Scope:** What Terraform provisions today, what blocks a working `.gitlab-ci.yml`, and the exact additions required.

---

## TL;DR

Terraform has provisioned the **runtime** completely (VM, SA, Artifact Registry, GCS, Secret Manager, DNS, firewalls). What it has **not** provisioned is the **build/deploy plane**: there is no CI service account, no Workload Identity Federation (WIF) pool for GitLab, no `kubectl`-capable identity, and no `.gitlab-ci.yml`. Because the org enforces `constraints/iam.disableServiceAccountKeyCreation`, the only viable cloud-native CI auth path is **GitLab OIDC → WIF → impersonate a dedicated CI SA**. Add ~60 lines of HCL plus a `.gitlab-ci.yml` and the pipeline works.

---

## Section 1 — What Terraform already provides (usable by CI/CD)

Verified live with `gcloud` against the project.

### 1.1 Compute / Network
| Resource | TF resource | Live value |
|---|---|---|
| VM | `google_compute_instance.vm` | `meesell-vm` in `asia-south1-a`, e2-standard-2, Ubuntu 24.04, 50 GB pd-balanced |
| Static external IP | `google_compute_address.static` | `meesell-ip` (region `asia-south1`) — already attached as NAT IP |
| Firewall HTTP/HTTPS | `google_compute_firewall.allow_http_https` | tcp/80, tcp/443 from `0.0.0.0/0` → tag `meesell-public` |
| Firewall SSH | `google_compute_firewall.allow_ssh` | tcp/22 from `var.ssh_source_cidrs` (currently `0.0.0.0/0`) → tag `meesell-public` |
| SSH key | injected via VM `metadata.ssh-keys` | user `mugunthansrinivasan`, ed25519 |
| VM startup script | `templates/startup.sh` | passes `project_id`, `region`, `bucket_name`, `registry_url`, `workload_sa_email`, `domain` to the OS |

### 1.2 Service Accounts (verified live)
```
meesell-workload@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com  ← attached to VM, TF-managed
meesell-worker@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com    ← present but NOT in TF (drift)
888244156264-compute@developer.gserviceaccount.com                       ← default compute SA, unused
```

Workload SA IAM (`iam.tf`):
- `roles/artifactregistry.reader` — VM `containerd` pulls images via metadata-server token
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`
- `roles/storage.objectAdmin` on `meesell-assets` bucket (`storage.tf`)
- `roles/secretmanager.secretAccessor` on every secret (`secrets.tf`)

### 1.3 Artifact Registry (verified live)
```
asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-images
```
Created 2026-05-27, DOCKER format, with cleanup policies (keep last 10 prod, delete untagged > 7 days). **The k8s manifests still point at `meesell/api:latest` not `meesell-images/api:latest` — name mismatch (see Gap 5).**

### 1.4 Secrets (Secret Manager)
Per `secrets.tf`, the following secrets exist with `meesell-` prefix and lowercase-dashed names:
- `meesell-jwt-secret` (random_password, 64 char)
- `meesell-postgres-password` (random_password, 32 char)
- `meesell-gemini-api-key`
- `meesell-msg91-auth-key`
- `meesell-msg91-template-id`
- `meesell-razorpay-key-id`
- `meesell-razorpay-key-secret`

Workload SA can read all of them. `scripts/secrets-from-gcp.sh` already materialises them into `k8s/secrets.yaml` on the VM.

> SUPERSEDED 2026-06-12: this section describes the `meesell-`-prefixed SM scheme the applied `app_secrets` module never used (it uses un-prefixed IDs: `gemini-api-key`, `jwt-secret`, etc.). `meesell-gemini-api-key` is a dead SM secret (HTTP 400, unreferenced by any live path). `scripts/secrets-from-gcp.sh` was deleted 2026-06-12; the live path populates the k8s Secret `backend-secrets` (dev ns) via `gcloud secrets versions add`. See `docs/INFRASTRUCTURE_ARCHITECTURE.md`.

### 1.5 Storage
- GCS bucket `project-1f5cbf72-2820-4cdb-949-meesell-assets` (UBLA, public-access-prevention enforced, versioned, 90-day archive lifecycle).

### 1.6 DNS
- Currently disabled (`manage_dns = false`, `domain = ""`). If turned on, TF will create the managed zone plus A records for apex, `www`, `api`.

### 1.7 APIs enabled
`compute`, `storage`, `artifactregistry`, `secretmanager`, `iam`, **`iamcredentials`** (already on — needed for WIF impersonation), `dns`.

### 1.8 Outputs (already wired)
`vm_name`, `vm_external_ip`, `ssh_command`, `bucket_name`, `artifact_registry_url`, `workload_service_account`, `secret_ids` (map), `registry_docker_login_hint`. CI can read any of these from Terraform state or be fed them as GitLab CI variables.

---

## Section 2 — The key constraint: no SA key files

### 2.1 What the policy means
`constraints/iam.disableServiceAccountKeyCreation` (org-level) blocks `gcloud iam service-accounts keys create …`. Any traditional CI pattern that ships a downloaded `key.json` to GitLab as a CI variable is **dead on arrival**. Two consequences:

1. The committed file `k8s/meesell-worker-sa-key.json` is either (a) a leaked legacy key that must be **rotated/deleted**, or (b) a placeholder. Either way it must not be re-introduced. The `worker.yaml` comment is correct: rely on the metadata server.
2. The `meesell-worker@` SA visible via `gcloud` was almost certainly created out-of-band (before policy enforcement or via a portal) and is **not in Terraform** — drift.

### 2.2 Authentication options for CI

**Option A — Workload Identity Federation (WIF) [RECOMMENDED]**
- GitLab CI exposes a signed OIDC JWT (`CI_JOB_JWT_V2` / `id_tokens:`) for every job.
- We register a Workload Identity Pool + GitLab OIDC provider in GCP.
- We create a dedicated `meesell-ci@…` SA with minimum rights (`roles/artifactregistry.writer` on `meesell-images`).
- The pool's provider is bound to that SA via `roles/iam.workloadIdentityUser`, scoped to one specific GitLab project path.
- In CI, `gcloud auth login --cred-file=<sts-token>` (or the `google-github-actions/auth`-equivalent shell snippet) trades the OIDC JWT for an STS token → impersonates `meesell-ci@…`. **No key file. No long-lived secret.** Compatible with the org policy because no key is ever created.

**Option B — SSH-only deploy (no GCP auth in CI)**
- CI never authenticates to GCP. It only `ssh`-es to the VM with a deploy key (stored as a GitLab CI variable) and runs `make build deploy` *inside the VM*. The VM already has Artifact Registry pull rights via its metadata-server identity.
- Pros: simpler, no WIF setup; works today.
- Cons: pushes the build load onto the production VM (e2-standard-2, only 2 vCPU / 8 GB — competes with API + workers + Postgres), couples build and runtime, and the SSH key still needs to live somewhere. Image build there is also ~3-5× slower than a fresh CI runner.

**Recommendation for MeeSell (single-VM MVP):** **Option A (WIF).** Setup is ~50 lines of HCL once, and the operational hygiene (no key rotation, no leaked secrets, audit trail per job) is worth it. The VM stays dedicated to serving traffic. SSH-for-deploy is still used for the final `kubectl set image` step (which is fine — it's a 1-second command, not a build).

---

## Section 3 — Complete gap list (prioritised)

Legend: **TF** = Terraform change, **VAR** = GitLab CI variable, **MAN** = manual step, **FILE** = new file. Effort: S ≤ 30 min, M ≤ 2 h, L > 2 h.

| # | Gap | Fix type | Effort | Priority |
|---|-----|---------|--------|----------|
| 1 | **No WIF pool/provider** — CI cannot authenticate to GCP because the org policy blocks SA keys. | TF | M | P0 |
| 2 | **No dedicated CI service account** — `meesell-workload` is over-privileged and rightly scoped to the VM; CI needs its own SA with only `artifactregistry.writer`. | TF | S | P0 |
| 3 | **No CI→deploy mechanism** — `Makefile` uses `ssh meesell-vm "kubectl …"` but there is no SSH host alias in CI and no deploy key. Need either (a) an SSH key dedicated to CI (added to VM `~/.ssh/authorized_keys` via TF `ssh-keys` metadata or `google_compute_instance.metadata`) **or** (b) use Identity-Aware Proxy (`gcloud compute ssh --tunnel-through-iap`) with the CI SA granted `roles/iap.tunnelResourceAccessor` + `roles/compute.osLogin`. IAP path avoids storing an SSH key. | TF + VAR | M | P0 |
| 4 | **K8s manifests have placeholder image refs** — `k8s/api.yaml` and `k8s/worker.yaml` hardcode `asia-south1-docker.pkg.dev/REPLACE-PROJECT-ID/meesell/api:latest`. Two issues: (a) `REPLACE-PROJECT-ID` is not substituted, (b) the registry repo is `meesell-images` per Terraform, not `meesell`. Need either `envsubst`, Kustomize, or `kubectl set image` in CI. | FILE | S | P0 |
| 5 | **Registry name mismatch** — `locals.tf` defines `registry_id = "${var.name_prefix}-images"` → `meesell-images`. Manifests reference `…/meesell/api:latest`. Pulls will 404. | FILE | S | P0 |
| 6 | **No frontend deployment manifest is referenced in deploy** — `Makefile` only updates `deployment/api`. The frontend image gets built and pushed but never rolled out. | FILE | S | P1 |
| 7 | **Test DB in CI** — `backend/tests/conftest.py` requires PostgreSQL on `localhost:5432` (or `TEST_DATABASE_URL`) and Valkey on `localhost:6379` + `localhost:6381`. Need GitLab CI `services:` (postgres:16-alpine, valkey/valkey:8). | FILE | S | P0 |
| 8 | **GitLab CI variables not defined** — full list below (Section 3.1). | VAR | S | P0 |
| 9 | **`.gitlab-ci.yml` does not exist.** | FILE | M | P0 |
| 10 | **`meesell-worker@` SA drift** — exists in GCP but not in `iam.tf`. Either import it into TF or delete it; the workload SA already has `storage.objectAdmin`. | TF / MAN | S | P1 |
| 11 | **`k8s/meesell-worker-sa-key.json` is checked in** — if real, this is a credential leak. Delete from repo + git history, ensure `.gitignore` covers `*-key.json`, and confirm it was never live (or rotate). | MAN | S | P0 (security) |
| 12 | **No `kubectl` on CI runner side** — once IAP/SSH works, the CI image still needs `gcloud` + `kubectl` or it runs commands via SSH. Pick `google/cloud-sdk:slim` + install `kubectl` plugin. | FILE | S | P1 |
| 13 | **Frontend Dockerfile copies `node_modules` because no `.dockerignore`** — slow build, fat image. Add `.dockerignore` for `frontend/` and `backend/`. | FILE | S | P2 |
| 14 | **Image tag strategy** — pipeline must tag images with `$CI_COMMIT_SHORT_SHA` not `latest` so rollback is possible. Manifests need to consume that tag. | FILE | S | P1 |
| 15 | **DB migration step** — `alembic upgrade head` is documented but not in CI. Must run *after* image push, *before* `kubectl set image`, via SSH into the VM (or a one-shot `kubectl run` job). | FILE | S | P1 |
| 16 | **DNS not active** — `manage_dns = false`, no `domain` set. CI doesn't care, but `k8s/ingress.yaml` hardcodes `meesell.in`; TLS will fail until DNS + cert-manager resolve. Not a CI gap per se. | TF / MAN | S | P2 |

### 3.1 GitLab CI variables required

| Variable | Type | Source | Where used |
|---|---|---|---|
| `GCP_PROJECT_ID` | normal | `project-1f5cbf72-2820-4cdb-949` | every job |
| `GCP_REGION` | normal | `asia-south1` | build/push |
| `GCP_AR_REPO` | normal | `meesell-images` | build/push |
| `GCP_WIF_PROVIDER` | normal | `projects/698205129974/locations/global/workloadIdentityPools/gitlab-pool/providers/gitlab-oidc` (full resource name, output by TF) | auth step |
| `GCP_CI_SA_EMAIL` | normal | `meesell-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` | auth step |
| `GCP_VM_NAME` | normal | `meesell-vm` | deploy via IAP |
| `GCP_VM_ZONE` | normal | `asia-south1-a` | deploy via IAP |
| `GITLAB_OIDC_AUDIENCE` | normal | `https://gitlab.com` (or workspace-specific) | id_tokens |

No secret variables are needed — that's the whole point of WIF. The only credentials the pipeline carries are the short-lived OIDC JWT (issued per-job) and the STS token (10 min TTL).

---

## Section 4 — Recommended architecture for MeeSell

```
┌────────────────────────────────────────────────────────────────────────────┐
│  GitLab CI Runner (shared)                                                 │
│                                                                            │
│  stage: test       postgres:16-alpine + valkey:8 services → pytest         │
│  stage: lint       ruff check                                              │
│  stage: build      docker build api  &&  docker build frontend             │
│  stage: auth       id_tokens → STS → impersonate meesell-ci@…              │
│  stage: push       docker push  asia-south1-docker.pkg.dev/.../api:<sha>   │
│                    docker push  …/frontend:<sha>                           │
│  stage: migrate    gcloud compute ssh meesell-vm --tunnel-through-iap \    │
│                       -- 'kubectl -n meesell exec deploy/api -- \          │
│                           alembic upgrade head'                            │
│  stage: deploy     gcloud compute ssh … --tunnel-through-iap -- \          │
│                       'kubectl -n meesell set image deploy/api    \        │
│                           api=…/api:<sha>;                                 │
│                        kubectl -n meesell set image deploy/frontend \      │
│                           frontend=…/frontend:<sha>;                       │
│                        kubectl rollout status deploy/api --timeout=120s'   │
└────────────────────────────────────────────────────────────────────────────┘
                                  │ OIDC JWT (no SA key)
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  GCP project-1f5cbf72-…                                                    │
│                                                                            │
│   Workload Identity Pool (gitlab-pool)                                     │
│       └─ Provider (gitlab-oidc, attribute_condition pinned to mesell repo) │
│            │ workloadIdentityUser                                          │
│            ▼                                                               │
│   SA: meesell-ci@…   (roles/artifactregistry.writer on meesell-images,    │
│                       roles/iap.tunnelResourceAccessor,                    │
│                       roles/compute.osLogin,                               │
│                       roles/iam.serviceAccountUser on meesell-workload     │
│                          [only if it needs to ssh as that SA — not needed  │
│                           when using OS Login user identity])              │
│                                                                            │
│   Artifact Registry: meesell-images  ◀── docker push                       │
│                                                                            │
│   IAP tunnel to meesell-vm:22  ◀── gcloud compute ssh                      │
│                                                                            │
│   VM (meesell-workload SA) → K3s → kubectl set image → containerd pulls    │
│                                     from Artifact Registry using its own   │
│                                     metadata-server token (already works)  │
└────────────────────────────────────────────────────────────────────────────┘
```

Why this shape:
- **No SA keys anywhere** (policy-compliant).
- **Build happens on CI**, not on the production VM (VM stays focused on serving traffic).
- **Deploy is a 2-second SSH** via IAP — no SSH key file to manage, audited via IAP logs.
- **CI SA is single-purpose** (push images, tunnel SSH). Workload SA stays scoped to runtime.
- **Image tags are immutable SHAs**; rollback = `kubectl set image` with the previous SHA.

---

## Section 5 — Exact Terraform additions needed

Create `terraform/ci.tf`:

```hcl
# ---------------------------------------------------------------------------
# CI/CD identity. Lets GitLab CI authenticate via OIDC (Workload Identity
# Federation) and impersonate a dedicated SA. No SA keys are created, so the
# org policy constraints/iam.disableServiceAccountKeyCreation is honoured.
# ---------------------------------------------------------------------------

variable "gitlab_project_path" {
  description = "Full GitLab project path (e.g. mygroup/mesell). Restricts which GitLab project may assume the CI SA."
  type        = string
}

variable "gitlab_issuer_uri" {
  description = "GitLab OIDC issuer. gitlab.com for SaaS, your GitLab URL for self-hosted."
  type        = string
  default     = "https://gitlab.com"
}

resource "google_iam_workload_identity_pool" "gitlab" {
  workload_identity_pool_id = "gitlab-pool"
  display_name              = "GitLab CI Pool"
  description               = "Federated identity for GitLab CI jobs."
  depends_on                = [google_project_service.enabled]
}

resource "google_iam_workload_identity_pool_provider" "gitlab" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.gitlab.workload_identity_pool_id
  workload_identity_pool_provider_id = "gitlab-oidc"
  display_name                       = "GitLab OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.project_path"     = "assertion.project_path"
    "attribute.ref"              = "assertion.ref"
    "attribute.ref_type"         = "assertion.ref_type"
    "attribute.pipeline_source"  = "assertion.pipeline_source"
  }

  # Only jobs from THIS GitLab project may exchange a token. Prevents any
  # other GitLab project from impersonating meesell-ci@.
  attribute_condition = "attribute.project_path == \"${var.gitlab_project_path}\""

  oidc {
    issuer_uri        = var.gitlab_issuer_uri
    allowed_audiences = [var.gitlab_issuer_uri]
  }
}

resource "google_service_account" "ci" {
  account_id   = "${var.name_prefix}-ci"
  display_name = "MeeSell CI service account"
  description  = "Impersonated by GitLab CI via Workload Identity Federation. Push images + deploy via IAP SSH."
  depends_on   = [google_project_service.enabled]
}

# Only allow tokens minted by *our* GitLab project to act as this SA.
resource "google_service_account_iam_member" "ci_wif_binding" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member = format(
    "principalSet://iam.googleapis.com/%s/attribute.project_path/%s",
    google_iam_workload_identity_pool.gitlab.name,
    var.gitlab_project_path,
  )
}

# Push images to Artifact Registry (scoped to the meesell-images repo only).
resource "google_artifact_registry_repository_iam_member" "ci_ar_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci.email}"
}

# IAP TCP tunnel for SSH (so CI doesn't need a public SSH key).
resource "google_project_iam_member" "ci_iap_tunnel" {
  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# OS Login lets the SA SSH as itself (mapped to a POSIX user) without keys.
resource "google_project_iam_member" "ci_os_login" {
  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# Enable OS Login on the VM (project-wide is simplest).
resource "google_compute_project_metadata_item" "enable_oslogin" {
  key   = "enable-oslogin"
  value = "TRUE"
}

# Add IAP source range to existing SSH firewall (or replace it).
resource "google_compute_firewall" "allow_ssh_iap" {
  name          = "${var.name_prefix}-allow-ssh-iap"
  network       = "default"
  source_ranges = ["35.235.240.0/20"]   # IAP TCP forwarders
  target_tags   = ["meesell-public"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  depends_on = [google_project_service.enabled]
}
```

Add to `terraform/outputs.tf`:

```hcl
output "ci_workload_identity_provider" {
  description = "Full resource name to set as GitLab CI variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.gitlab.name
}

output "ci_service_account_email" {
  description = "Set as GitLab CI variable GCP_CI_SA_EMAIL."
  value       = google_service_account.ci.email
}
```

Also enable `iap.googleapis.com` in `main.tf`'s `required_services` list.

Notes:
- IAP SSH requires `enable-oslogin = TRUE` (set above) and that the firewall accepts traffic from `35.235.240.0/20`. The current `allow_ssh` rule already lets anyone in (0.0.0.0/0) so IAP works today; the explicit `allow_ssh_iap` rule is included so we can tighten `ssh_source_cidrs` later without breaking CI.
- Once OS Login is on, the existing `metadata.ssh-keys` entry stops being honoured. Switch to `gcloud compute ssh --tunnel-through-iap` from your laptop too. (Document in `terraform/README.md`.)

---

## Section 6 — Exact `.gitlab-ci.yml` skeleton

Place at repo root. Uses GitLab's `id_tokens:` (CI_JOB_JWT_V2 is being deprecated).

```yaml
# .gitlab-ci.yml
stages: [test, build, push, migrate, deploy]

variables:
  # set as GitLab CI/CD variables (Settings → CI/CD → Variables), all non-secret
  GCP_PROJECT_ID:        $GCP_PROJECT_ID
  GCP_REGION:            $GCP_REGION           # asia-south1
  GCP_AR_REPO:           $GCP_AR_REPO          # meesell-images
  GCP_WIF_PROVIDER:      $GCP_WIF_PROVIDER     # projects/698205129974/locations/global/workloadIdentityPools/gitlab-pool/providers/gitlab-oidc
  GCP_CI_SA_EMAIL:       $GCP_CI_SA_EMAIL
  GCP_VM_NAME:           meesell-vm
  GCP_VM_ZONE:           asia-south1-a
  IMAGE_API:             "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_AR_REPO}/api:${CI_COMMIT_SHORT_SHA}"
  IMAGE_FRONTEND:        "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_AR_REPO}/frontend:${CI_COMMIT_SHORT_SHA}"

# -----------------------------------------------------------------------------
# Reusable auth snippet: exchange the GitLab OIDC JWT for a GCP access token.
# -----------------------------------------------------------------------------
.gcp_auth: &gcp_auth
  id_tokens:
    GCP_ID_TOKEN:
      aud: https://gitlab.com
  before_script:
    - echo "$GCP_ID_TOKEN" > /tmp/oidc.jwt
    - |
      cat > /tmp/wif.json <<EOF
      {
        "type": "external_account",
        "audience": "//iam.googleapis.com/${GCP_WIF_PROVIDER}",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "token_url": "https://sts.googleapis.com/v1/token",
        "service_account_impersonation_url":
          "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${GCP_CI_SA_EMAIL}:generateAccessToken",
        "credential_source": { "file": "/tmp/oidc.jwt" }
      }
      EOF
    - gcloud auth login --cred-file=/tmp/wif.json --quiet
    - gcloud config set project "$GCP_PROJECT_ID"

# -----------------------------------------------------------------------------
# TEST
# -----------------------------------------------------------------------------
test:backend:
  stage: test
  image: python:3.12-slim
  services:
    - name: postgres:16-alpine
      alias: postgres
    - name: valkey/valkey:8-alpine
      alias: valkey
  variables:
    POSTGRES_DB:         meesell_test
    POSTGRES_USER:       meesell
    POSTGRES_PASSWORD:   password
    TEST_DATABASE_URL:   "postgresql+asyncpg://meesell:password@postgres:5432/meesell_test"
    VALKEY_URL:          "redis://valkey:6379/15"
    CELERY_BROKER_URL:   "redis://valkey:6379/11"
    CELERY_RESULT_BACKEND: "redis://valkey:6379/12"
    JWT_SECRET:          "test-secret-do-not-use"
  before_script:
    - cd backend
    - pip install --no-cache-dir -r requirements.txt
  script:
    - python -m ruff check app/
    - python -m pytest tests/ -v

# -----------------------------------------------------------------------------
# BUILD (docker:dind on the shared runner)
# -----------------------------------------------------------------------------
.build_base:
  stage: build
  image: docker:27
  services: [docker:27-dind]
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'

build:api:
  extends: .build_base
  script:
    - docker build -t "$IMAGE_API" ./backend
    - docker save "$IMAGE_API" > image-api.tar
  artifacts: { paths: [image-api.tar], expire_in: 1 hour }

build:frontend:
  extends: .build_base
  script:
    - docker build -t "$IMAGE_FRONTEND" ./frontend
    - docker save "$IMAGE_FRONTEND" > image-frontend.tar
  artifacts: { paths: [image-frontend.tar], expire_in: 1 hour }

# -----------------------------------------------------------------------------
# PUSH (needs GCP auth)
# -----------------------------------------------------------------------------
.push_base:
  stage: push
  image: google/cloud-sdk:slim
  services: [docker:27-dind]
  variables: { DOCKER_TLS_CERTDIR: "/certs" }
  <<: *gcp_auth
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  script:
    - apt-get update && apt-get install -y docker.io >/dev/null
    - gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
    - docker load < "$IMAGE_TAR"
    - docker push "$IMAGE_NAME"

push:api:
  extends: .push_base
  needs: [build:api]
  variables: { IMAGE_TAR: image-api.tar,      IMAGE_NAME: $IMAGE_API }

push:frontend:
  extends: .push_base
  needs: [build:frontend]
  variables: { IMAGE_TAR: image-frontend.tar, IMAGE_NAME: $IMAGE_FRONTEND }

# -----------------------------------------------------------------------------
# MIGRATE (run alembic against prod DB via IAP SSH → kubectl exec)
# -----------------------------------------------------------------------------
migrate:
  stage: migrate
  image: google/cloud-sdk:slim
  needs: [push:api]
  <<: *gcp_auth
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  script:
    - |
      gcloud compute ssh "$GCP_VM_NAME" \
        --zone "$GCP_VM_ZONE" \
        --tunnel-through-iap \
        --command "kubectl -n meesell set image deploy/api api=${IMAGE_API} --record && \
                   kubectl -n meesell rollout status deploy/api --timeout=120s && \
                   kubectl -n meesell exec deploy/api -- alembic upgrade head"

# -----------------------------------------------------------------------------
# DEPLOY (frontend rollout)
# -----------------------------------------------------------------------------
deploy:frontend:
  stage: deploy
  image: google/cloud-sdk:slim
  needs: [push:frontend, migrate]
  <<: *gcp_auth
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  script:
    - |
      gcloud compute ssh "$GCP_VM_NAME" \
        --zone "$GCP_VM_ZONE" \
        --tunnel-through-iap \
        --command "kubectl -n meesell set image deploy/frontend frontend=${IMAGE_FRONTEND} --record && \
                   kubectl -n meesell rollout status deploy/frontend --timeout=120s"
```

Once the Terraform additions are applied and the eight variables in §3.1 are set in GitLab, pushing to `main` will:
1. lint + test on a fresh runner (with Postgres + Valkey side-cars),
2. build both images with the commit SHA tag,
3. authenticate to GCP via OIDC (no SA key), push to Artifact Registry,
4. SSH into the VM through IAP (no SSH key file), set new image, run migrations, roll out.

Total moving parts added: 1 Terraform file (`ci.tf`), 2 output entries, 1 added API (`iap.googleapis.com`), and 1 `.gitlab-ci.yml`. Existing runtime infra is untouched.
