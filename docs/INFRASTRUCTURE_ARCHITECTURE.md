# MeeSell Infrastructure Architecture — Single Source of Truth

**Owner:** `meesell-infra-builder`
**Last verified live:** 2026-06-07
**Project state:** Phase A + Phase B complete. All 5 application subdomains live with valid Let's Encrypt TLS. Application images not yet built (Phase D pending).

This is the single source of truth for MeeSell's production infrastructure. If anything in this document conflicts with another doc, this document wins. Update this file whenever live infrastructure changes.

---

## 1. Overview

MeeSell runs on a single-node K3s cluster hosted on one GCP Compute VM (`meesell-dev`) in `asia-south1-a`. PostgreSQL 16 and Valkey 8 run as StatefulSets in the `dev` namespace; Supabase Studio runs as a Deployment for DB administration. Traefik (Helm) is the ingress controller; cert-manager + Let's Encrypt issues TLS certs over HTTP-01 challenges. Off-cluster GCP services include Artifact Registry (`meesell-prod-images`) for container images, GCS (`gs://meesell-prod-assets`) for product images / exports / audit logs, and Secret Manager (7 secrets) for application credentials. CI/CD runs from GitLab (`techades/mesell`) using Workload Identity Federation — no service account keys leave Google. All infrastructure is managed by Terraform (`infra/terraform/`, 14 modules, local state); domain `mesell.xyz` is registered at Namecheap with five A records pointing to the VM's static external IP `35.234.223.66`.

---

## 2. Architecture Diagram

```
                                                  Internet
                                                      |
                                                      |
                            +-------------------------+--------------------------+
                            |  DNS: mesell.xyz (Namecheap)                       |
                            |    A studio.mesell.xyz    -> 35.234.223.66         |
                            |    A api.mesell.xyz       -> 35.234.223.66         |
                            |    A dev.mesell.xyz       -> 35.234.223.66         |
                            |    A testing.mesell.xyz   -> 35.234.223.66         |
                            |    A staging.mesell.xyz   -> 35.234.223.66         |
                            |    A www.mesell.xyz       -> (deferred to Week 2)  |
                            +-------------------------+--------------------------+
                                                      |
                                                  TCP 80/443
                                                      |
+---------------------------------------------------- v -----------------------------------------------------+
|                            GCP Project: project-1f5cbf72-2820-4cdb-949                                    |
|                            Region: asia-south1   Zone: asia-south1-a                                      |
|                                                                                                            |
|   +---- Firewall (3 rules) ----+        +-------- VM: meesell-dev (35.234.223.66) --------+               |
|   | meesell-dev-http   :80 ALL |--------|  e2-standard-2 (2 vCPU / 8 GB) / 50 GB SSD     |               |
|   | meesell-dev-https  :443 ALL|        |  Debian 12 / K3s v1.35.5+k3s1                  |               |
|   | meesell-dev-k3s-api:6443/  |        |  Service Account: 888244156264-compute@...     |               |
|   |   ISP CIDR ranges          |        |                                                  |               |
|   +----------------------------+        |  +-- namespace: traefik ------------------+     |               |
|                                          |  |  Helm release: traefik 28.3.0          |     |               |
|                                          |  |  Service: LoadBalancer (klipper-lb)    |     |               |
|                                          |  |  Routes by Host header -> in-cluster   |     |               |
|                                          |  |  Services. TLS termination here.       |     |               |
|                                          |  +-+-----+----------+--------+------------+     |               |
|                                          |    |     |          |        |                  |               |
|                                          |    |     |          |        |                  |               |
|                                          |  +-v-----v---+   +--v--------v-----+            |               |
|                                          |  | namespace |   | namespace       |            |               |
|                                          |  |   dev     |   |   staging       |            |               |
|                                          |  |           |   |                 |            |               |
|                                          |  |  +-----+  |   |  +-----------+  |            |               |
|                                          |  |  |     |  |   |  | frontend  |  |            |               |
|                                          |  |  | api |  |   |  | (pending) |  |            |               |
|                                          |  |  +--+--+  |   |  +-----+-----+  |            |               |
|                                          |  |     |     |   |        |       |            |               |
|                                          |  |  +--+----+ |   |        |       |            |               |
|                                          |  |  |worker | |   |        |       |            |               |
|                                          |  |  +---+---+ |   |        |       |            |               |
|                                          |  |      |    |   |        |       |            |               |
|                                          |  |  +---v-------+ +--------+-------+ +--------+ |               |
|                                          |  |  | postgres  | | valkey         | | studio | |               |
|                                          |  |  | STS PG16  | | STS Valkey 8   | | Deploy | |               |
|                                          |  |  | 20Gi PVC  | | 5Gi PVC        | |        | |               |
|                                          |  |  +-----------+ +----------------+ +--------+ |               |
|                                          |  +-------------------------------------------+   |               |
|                                          |                                                  |               |
|                                          |  +-- namespace: cert-manager ----------------+   |               |
|                                          |  |  cert-manager v1.14.5 (Helm: Jetstack)    |   |               |
|                                          |  |  ClusterIssuer: letsencrypt-prod (HTTP-01)|   |               |
|                                          |  +-------------------------------------------+   |               |
|                                          +-+----------------+--------------------+----------+               |
|                                            |                |                    |                          |
|             Workload Identity (VM SA)      |                |                    |                          |
|                                            v                v                    v                          |
|   +----------------------+   +---------------------+   +-------------------+   +------------------------+   |
|   | Artifact Registry    |   | GCS bucket          |   | Secret Manager    |   | Cloud Billing          |   |
|   | meesell-prod-images  |   | meesell-prod-assets |   | 7 secrets         |   | Budget: INR 25,000     |   |
|   | asia-south1 / Docker |   | asia-south1         |   | (see Section 4)   |   | 50 / 75 / 90 % alerts  |   |
|   +----------------------+   +---------------------+   +-------------------+   +------------------------+   |
|             ^                                                                                              |
|             | docker push (CI)                                                                             |
|             |                                                                                              |
|   +---------+----------------------------------------------------------------------------------+           |
|   | Workload Identity Federation                                                                |           |
|   |   Pool:     gitlab-prod-pool                                                                |           |
|   |   Provider: gitlab-prod-provider  (issuer: gitlab.com)                                      |           |
|   |   Bound to: techades/mesell  ->  SA: meesell-prod-ci@<project>.iam.gserviceaccount.com      |           |
|   +---------------------------------------------------------------------------------------------+           |
+------------------------------------------------------------------------------------------------------------+
```

---

## 3. GCP Resources

### 3.1 Account and project pin

| Field | Value |
|---|---|
| GCP owner account | `vaishnaviramoorthy@gmail.com` |
| GCP project ID | `project-1f5cbf72-2820-4cdb-949` |
| GCP project number | `888244156264` |
| Billing account | `01620D-6785AB-0E4698` (INR-denominated) |
| Region | `asia-south1` |
| Zone | `asia-south1-a` |
| ADC actor (workaround) | `mugunthanks93@gmail.com` (must use `GOOGLE_OAUTH_ACCESS_TOKEN` — see Runbook 12.2) |

### 3.2 Resources

| Resource | Name / ID | Spec | Status |
|---|---|---|---|
| Compute VM | `meesell-dev` | e2-standard-2, 50 GB SSD, Debian 12, external IP `35.234.223.66` (static) | RUNNING |
| VM Service Account | `888244156264-compute@developer.gserviceaccount.com` | Default Compute Engine SA; granted `artifactregistry.reader` + `storage.objectAdmin` | Active |
| Firewall: HTTP | `meesell-dev-http` | TCP 80, source `0.0.0.0/0`, target tag `http-server` | Active |
| Firewall: HTTPS | `meesell-dev-https` | TCP 443, source `0.0.0.0/0`, target tag `https-server` | Active |
| Firewall: K3s API | `meesell-dev-k3s-api` | TCP 6443, source ISP CIDR ranges (`122.164.64.0/18` Airtel TN, `152.57.80.0/21` Jio), target tag `k3s-server` | Active |
| Artifact Registry | `meesell-prod-images` | Docker repo in `asia-south1`; CI SA writer, VM SA reader | Active (empty — Phase D pending) |
| GCS bucket | `gs://meesell-prod-assets` | `asia-south1`, uniform access, public access prevention, versioning enabled; CI SA + VM SA objectAdmin | Active (empty) |
| Cloud Billing budget | `meesell-dev-budget` (UUID `95c5e193-c796-44a3-8c2b-8a66e36308d5`) | INR 25,000 with alerts at 50 / 75 / 90 % | Active |
| CI Service Account | `meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` | Roles: `artifactregistry.writer` (project), `storage.objectAdmin` (bucket) | Active |
| Workload Identity Pool | `gitlab-prod-pool` | Global | Active |
| Workload Identity Provider | `gitlab-prod-provider` | OIDC issuer `gitlab.com`, attribute mapping on `repository` | Active |
| WIF binding | `principalSet://iam.googleapis.com/projects/888244156264/locations/global/workloadIdentityPools/gitlab-prod-pool/attribute.repository/techades/mesell` | Impersonates CI SA | Active |
| Account lock (Terraform) | `null_resource.account_lock_guard` | Preconditions: project ID + billing account both match expected values | Enforced |

Enabled GCP APIs (9): `serviceusage`, `compute`, `iam`, `iamcredentials`, `cloudresourcemanager`, `secretmanager`, `artifactregistry`, `storage`, `sts`, plus `cloudbilling` and `billingbudgets` (10 + 1 enabled by `module.app_secrets` cascade).

### 3.3 R&D / out-of-scope resources (DO NOT TOUCH)

| Resource | Purpose | Reason |
|---|---|---|
| `meesell-vm` (34.93.9.139) | R&D / sandbox VM (separate `mesell/terraform/` state) | Playbook §0 [DANGER] — out of scope |
| `shotfox-platform`, `shotfox-mvp1-alpha-dev` | Other projects' VMs | Playbook §0 [DANGER] — out of scope |
| `meesell-msg91-template-id`, other `meesell-*` secrets in R&D | R&D Secret Manager entries | Read-only — used as source for prod `msg91-template-id` |

---

## 4. Secret Manager

All 7 production secrets are populated with version 1. Local backups live at `~/.meesell-secrets/` (dir `chmod 700`, files `chmod 600`). Workloads read these via the VM SA at runtime — no keys are ever written to ConfigMaps or images.

| Secret ID | Purpose | Status | Notes |
|---|---|---|---|
| `msg91-auth-key` | MSG91 OTP service auth key | LIVE (v1) | Service: DEVOTP. MSG91 IP whitelist on `122.164.85.200`; refresh whitelist if founder IP rotates. |
| `msg91-template-id` | MSG91 OTP template ID | LIVE (v1) | Sourced from R&D `meesell-msg91-template-id` (11 chars). |
| `gemini-api-key` | Google Gemini 2.5 Flash API key | LIVE (v1) | Used by `services/ai_engine.py`. |
| `jwt-secret` | JWT signing secret | LIVE (v1) | `openssl rand -hex 64` (128-char hex). |
| `razorpay-key-id` | Razorpay TEST key ID | LIVE (v1) | Replace with LIVE key during prod cut-over. |
| `razorpay-key-secret` | Razorpay TEST key secret | LIVE (v1) | Replace with LIVE secret during prod cut-over. |
| `audit-pii-salt` | 32-byte salt for audit-log PII hashing (`MVP_ARCHITECTURE.md §11.9`) | LIVE (v1) | `openssl rand -hex 32` (64-char hex). |

Read pattern (from a workload pod, via VM SA metadata server):
```bash
gcloud secrets versions access latest --secret=<secret-id> --project=project-1f5cbf72-2820-4cdb-949
```

The Terraform module (`module.app_secrets`) manages only the secret containers, not their values — `lifecycle.ignore_changes` discipline keeps `terraform plan` clean across founder-side `gcloud secrets versions add` operations.

---

## 5. Kubernetes Cluster

| Field | Value |
|---|---|
| Cluster type | K3s single-node (server, `--disable=traefik`) |
| K3s version | `v1.35.5+k3s1` |
| Node | `meesell-dev-master` (Ready, `control-plane,master`) |
| Kubeconfig (founder laptop) | `~/.kube/meesell-dev.yaml` (`chmod 600`) |
| Kubeconfig API endpoint | `https://35.234.223.66:6443` (rewritten from `127.0.0.1` post-scp) |
| Container runtime | containerd (bundled with K3s) |
| CNI | flannel (K3s default) |
| Storage class | `local-path` (Rancher local-path-provisioner, K3s default) |
| LoadBalancer | klipper-lb (K3s default; internal IP `10.160.0.7` — external traffic enters via VM IP + firewall) |
| DNS | CoreDNS (K3s default) |

### Namespaces

| Namespace | Purpose | Status | Notes |
|---|---|---|---|
| `dev` | Active development workloads (DB, cache, studio, API, worker, frontend) | Active | Labelled `env=dev` |
| `staging` | Pre-production staging (workloads pending Phase D) | Active | Labelled `env=staging`; frontend ingress live |
| `traefik` | Traefik ingress controller | Active | Helm-managed |
| `cert-manager` | cert-manager + webhook + cainjector | Active | Helm-managed (Jetstack chart) |
| `kube-system` | K3s system pods (coredns, local-path, metrics-server, svclb) | Active | Untouched |
| `prod` | Production workloads | **NOT CREATED** | Deferred to Week 2 (per playbook §15c, after staging clean for 1 full week) |

### Helm releases

| Release | Namespace | Chart | Version | Source |
|---|---|---|---|---|
| `traefik` | `traefik` | `traefik/traefik` | 28.3.0 | https://traefik.github.io/charts |
| `cert-manager` | `cert-manager` | `jetstack/cert-manager` | v1.14.5 | https://charts.jetstack.io |

---

## 6. Workloads

### Namespace `dev`

| Workload | Kind | Replicas | Image | Resources (req / limit) | Storage | Status |
|---|---|---|---|---|---|---|
| `postgres` | StatefulSet | 1 | `postgres:16` | 200m / 1000m CPU, 500Mi / 1Gi mem | 20Gi PVC (`local-path`, `prevent_destroy`) | Running, accepting connections |
| `valkey` | StatefulSet | 1 | `valkey/valkey:8` | 100m / 500m CPU, 200Mi / 512Mi mem | 5Gi PVC (`local-path`, `prevent_destroy`) | Running, `maxmemory 128mb allkeys-lru` |
| `supabase-studio` | Deployment | 1 | `supabase/studio:latest` | 100m / 500m CPU, 256Mi / 512Mi mem | (stateless) | Running |
| `api` | Deployment | 2 | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:latest` | TBD | (stateless) | **NOT DEPLOYED** (Phase D — image not built) |
| `worker` | Deployment | 2 | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:latest` | TBD | (stateless) | **NOT DEPLOYED** (Phase D — image not built) |
| `frontend` | Deployment | 1 | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/frontend:latest` | TBD | (stateless) | **NOT DEPLOYED** (Phase D — image not built) |

### Namespace `staging`

| Workload | Kind | Status |
|---|---|---|
| Frontend Ingress (`staging-frontend-tls`) | Ingress + Certificate | Live (cert issued); backend service `frontend:80` will exist when Phase D ships staging deployment |

### Namespace `traefik`

| Workload | Kind | Replicas | Image |
|---|---|---|---|
| `traefik` | Deployment | 1 | `traefik:v3.x` (chart-managed) |
| `traefik` Service | LoadBalancer | — | klipper-lb backend, ports 80 + 443 |

### Namespace `cert-manager`

| Workload | Kind | Replicas | Image |
|---|---|---|---|
| `cert-manager` | Deployment | 1 | `quay.io/jetstack/cert-manager-controller:v1.14.5` |
| `cert-manager-webhook` | Deployment | 1 | `quay.io/jetstack/cert-manager-webhook:v1.14.5` |
| `cert-manager-cainjector` | Deployment | 1 | `quay.io/jetstack/cert-manager-cainjector:v1.14.5` |

`startupapicheck` is **disabled** (`startupapicheck.enabled = false`) — it hit `BackoffLimitExceeded` on a single-node cluster; cert issuance works correctly without it.

---

## 7. Networking and Ingress

### DNS (Namecheap)

All A records resolve to the VM's external IP `35.234.223.66`.

| Hostname | Type | Target |
|---|---|---|
| `studio.mesell.xyz` | A | `35.234.223.66` |
| `api.mesell.xyz` | A | `35.234.223.66` |
| `dev.mesell.xyz` | A | `35.234.223.66` |
| `testing.mesell.xyz` | A | `35.234.223.66` |
| `staging.mesell.xyz` | A | `35.234.223.66` |
| `www.mesell.xyz` | A | (deferred to Week 2 — prod) |
| `*.mesell.xyz` | A | `35.234.223.66` (wildcard; currently routes everything not above to the cluster; used as a safety net) |

### Ingress (Traefik)

All 5 Ingress resources use:
- `ingressClassName: traefik`
- `traefik.ingress.kubernetes.io/router.entrypoints: websecure`
- `cert-manager.io/cluster-issuer: letsencrypt-prod`

| Host | Backend Service | Namespace | TLS Secret | Cert Issued | Notes |
|---|---|---|---|---|---|
| `studio.mesell.xyz` | `supabase-studio:3000` | `dev` | `studio-tls` | 2026-06-04 | Admin UI; not exposed to end users |
| `api.mesell.xyz` | `api:80` (-> pod :8000) | `dev` | `api-tls` | 2026-06-05 | FastAPI backend (service exists; pods pending Phase D) |
| `dev.mesell.xyz` | `frontend:80` | `dev` | `dev-frontend-tls` | 2026-06-05 | Dev environment frontend |
| `testing.mesell.xyz` | `frontend:80` | `dev` | `testing-frontend-tls` | 2026-06-05 | QA / testing frontend (same backend as dev) |
| `staging.mesell.xyz` | `frontend:80` | `staging` | `staging-frontend-tls` | 2026-06-05 | Staging frontend |
| `www.mesell.xyz` | (frontend, prod ns) | `prod` | — | — | Deferred to Week 2 |

### TLS / cert-manager

| Field | Value |
|---|---|
| ClusterIssuer | `letsencrypt-prod` |
| ACME server | `https://acme-v02.api.letsencrypt.org/directory` |
| ACME email | (from `dev.tfvars` `acme_email` = `vaishnaviramoorthy@gmail.com`) |
| Challenge type | HTTP-01 via Traefik ingress |
| Private key Secret | `letsencrypt-prod-key` (cluster-scoped) |
| Renewal | Automatic, ~30 days before expiry (cert-manager default) |
| Wildcard cert | Not configured (would require DNS-01 + Namecheap cert-manager plugin; deferred to V1.5) |

### Inbound traffic flow

```
Browser  -> 35.234.223.66:443
        -> GCP firewall  (meesell-dev-https)
        -> VM eth0 (NAT)
        -> klipper-lb (svclb-traefik) DaemonSet on host net
        -> Traefik pod (ClusterIP svc 'traefik')
        -> Traefik routes by Host header + TLS SNI
        -> Backend Service ClusterIP
        -> Pod
```

---

## 8. In-Cluster Service Discovery

Application config (`k8s/secrets.yaml.example`, `k8s/config.yaml`) MUST use these hostnames. The `meesell` namespace referenced in some legacy manifests does not exist — everything is in `dev`.

| Service | Hostname | Port | Protocol | Backed by |
|---|---|---|---|---|
| PostgreSQL | `postgres.dev.svc.cluster.local` | 5432 | TCP | StatefulSet `postgres` (headless svc) |
| Valkey | `valkey.dev.svc.cluster.local` | 6379 | TCP (Redis protocol) | StatefulSet `valkey` (headless svc) |
| API | `api.dev.svc.cluster.local` | 80 -> 8000 | HTTP | Deployment `api` (Phase D) |
| Frontend | `frontend.dev.svc.cluster.local` | 80 | HTTP | Deployment `frontend` (Phase D) |
| Supabase Studio | `supabase-studio.dev.svc.cluster.local` | 3000 | HTTP | Deployment `supabase-studio` |
| Traefik | `traefik.traefik.svc.cluster.local` | 80 / 443 | HTTP / HTTPS | Helm release `traefik` |

### Connection-string templates

```
DATABASE_URL    = postgresql+asyncpg://meesell:<password>@postgres.dev.svc.cluster.local:5432/meesell
VALKEY_URL      = redis://:<password>@valkey.dev.svc.cluster.local:6379/0
CELERY_BROKER   = redis://:<password>@valkey.dev.svc.cluster.local:6379/1
CELERY_RESULT   = redis://:<password>@valkey.dev.svc.cluster.local:6379/2
GCS_BUCKET      = meesell-prod-assets
GCS_PROJECT_ID  = project-1f5cbf72-2820-4cdb-949
```

Credentials are sourced from K8s Secrets (`dev/postgres-credentials`, `dev/valkey-credentials`) via `secretKeyRef`. Never inline passwords in committed YAML.

---

## 9. Terraform Module Map

All Terraform code lives at `infra/terraform/`. State is **local** (`infra/terraform/terraform.tfstate`); GCS backend migration is tracked as a deferred follow-up.

### Apply order

1. **Pass 1 (GCP):** APIs -> ci_identity -> artifact_registry -> asset_bucket -> app_secrets -> vm -> firewall -> billing_budget
2. **Pass 2 (K8s base):** namespaces -> postgres -> valkey -> supabase_studio -> traefik_stack
3. **Pass 2b (TLS + ingress):** cert_manager -> ingress
4. **Pass 3 (apps — pending):** api -> worker -> frontend (modules not yet created)

Managed via `Makefile.tf` at workspace root: `make -f Makefile.tf tf-plan-pass1`, `tf-apply-pass1`, `tf-plan-pass2`, etc. Preflight gate at `scripts/tf-preflight.sh` (Layer E of the account lock).

### Modules

| Module | Path | Owns |
|---|---|---|
| `module.vm` | `infra/terraform/modules/vm/` | GCP Compute Instance `meesell-dev`, boot disk, K3s cloud-init startup script |
| `module.firewall` | `infra/terraform/modules/firewall/` | 3 firewall rules: HTTP, HTTPS, K3s API (ISP CIDR ranges in `dev.tfvars`) |
| `module.artifact_registry` | `infra/terraform/modules/artifact_registry/` | AR repo `meesell-prod-images`, cleanup policy, CI SA writer binding |
| `module.asset_bucket` | `infra/terraform/modules/asset_bucket/` | GCS bucket `meesell-prod-assets`, uniform access, versioning, CI SA + VM SA bindings |
| `module.ci_identity` | `infra/terraform/modules/ci_identity/` | CI SA, WIF pool, WIF provider, WIF impersonation binding |
| `module.app_secrets` | `infra/terraform/modules/app_secrets/` | 7 Secret Manager secret containers (values managed out-of-band) |
| `module.billing_budget` | `infra/terraform/modules/billing_budget/` | Cloud Billing budget INR 25,000 + 3 alert thresholds |
| `module.namespaces` | `infra/terraform/modules/namespaces/` | K8s namespaces `dev`, `staging` (+ `env` label) |
| `module.postgres_dev` | `infra/terraform/modules/postgres/` | Postgres StatefulSet, headless Service, K8s Secret (`postgres-credentials`), 20Gi PVC |
| `module.valkey_dev` | `infra/terraform/modules/valkey/` | Valkey StatefulSet, headless Service, K8s Secret (`valkey-credentials`), 5Gi PVC, maxmemory args |
| `module.supabase_studio_dev` | `infra/terraform/modules/supabase_studio/` | Supabase Studio Deployment + ClusterIP Service |
| `module.traefik_stack` | `infra/terraform/modules/traefik/` | `traefik` namespace + Helm release |
| `module.cert_manager` | `infra/terraform/modules/cert_manager/` | `cert-manager` namespace + Helm release (Jetstack, v1.14.5) + settle sleep |
| `module.ingress` | `infra/terraform/modules/ingress/` | ClusterIssuer `letsencrypt-prod` + all 5 Ingress resources |

### Module naming gotcha

Some modules carry an environment suffix in the root `main.tf` even though the module directory does not — for example `module.valkey_dev` lives at `modules/valkey/`, `module.postgres_dev` at `modules/postgres/`, `module.supabase_studio_dev` at `modules/supabase_studio/`. Always resolve with `terraform state list | grep <pattern>` before using `-target=`.

---

## 10. CI/CD

### Current state

- **Workload Identity Federation:** wired and verified. GitLab pipeline jobs running on `techades/mesell` can impersonate `meesell-prod-ci@<project>` without a service account key.
- **GitLab CI variable to set:** `GCP_WORKLOAD_IDENTITY_PROVIDER` = `projects/888244156264/locations/global/workloadIdentityPools/gitlab-prod-pool/providers/gitlab-prod-provider`
- **GitLab CI service account variable:** `GCP_SERVICE_ACCOUNT` = `meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`
- **Pipeline file (`.gitlab-ci.yml`):** **NOT YET WRITTEN**.

### What's needed

1. `.gitlab-ci.yml` at repo root with stages: `lint` -> `test` -> `build` -> `push` -> `deploy`
2. Image build step: `docker build -t asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:$CI_COMMIT_SHA backend/`
3. Image push step: auth via WIF (`google-github-actions/auth` equivalent for GitLab) then `gcloud auth configure-docker asia-south1-docker.pkg.dev` then `docker push`
4. Deploy step: SSH to VM (or use kubeconfig from a CI runner with K3s API access from the runner's IP) and `kubectl set image deployment/api api=... -n dev`
5. Manual gate for `staging` -> `prod` promotion

### Container image targets

| Component | Image | Build context |
|---|---|---|
| API + Worker | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:<tag>` | `backend/` (FastAPI + Celery, same image, different entrypoint) |
| Frontend | `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/frontend:<tag>` | `frontend/` (Angular build + nginx) |

Pull authentication on the VM: VM SA `888244156264-compute@...` has `roles/artifactregistry.reader` on `meesell-prod-images`. K3s uses the GCE metadata server for keyless pulls — no `imagePullSecrets` needed.

---

## 11. Pending (Phase D)

Application image builds and deployments. Nothing here blocks core infra availability — only application traffic.

- [ ] Write `backend/Dockerfile` and `frontend/Dockerfile` (multi-stage builds, distroless or slim base)
- [ ] First image build + push to Artifact Registry (`api:latest`, `frontend:latest`)
- [ ] Write `.gitlab-ci.yml` covering lint / test / build / push / deploy
- [ ] Fix `k8s/api.yaml`, `k8s/worker.yaml`, `k8s/frontend.yaml` — change `namespace: meesell` -> `namespace: dev`
- [ ] Fix `k8s/secrets.yaml.example` — service hosts to `*.dev.svc.cluster.local`, bucket to `meesell-prod-assets`
- [ ] Fix `k8s/config.yaml` — `CORS_ORIGINS` to include `dev.mesell.xyz`, `testing.mesell.xyz`, `staging.mesell.xyz`, `www.mesell.xyz`
- [ ] Create `k8s/secrets.yaml` from `.example` with real values (NEVER commit)
- [ ] Apply `k8s/api.yaml`, `k8s/worker.yaml`, `k8s/frontend.yaml` once images are present
- [ ] Optional Pass 3 Terraform: `modules/api/`, `modules/worker/`, `modules/frontend/` so application Deployments are in Terraform state

---

## 12. Operational Runbooks

### 12.1 Founder IP rotation (firewall — no longer requires terraform apply)

**Firewall now uses ISP CIDR ranges** (`dev.tfvars: founder_ip_ranges`), not individual `/32` addresses.
Dynamic IP rotation within the same ISP is automatically covered — no action needed.

| ISP | CIDR | Dynamic pool |
|-----|------|-------------|
| Airtel TN broadband | `122.164.64.0/18` | `122.164.64.0`–`122.164.127.255` |
| Reliance Jio mobile | `152.57.80.0/21` | `152.57.80.0`–`152.57.87.255` |

**If `kubectl` still times out** (new ISP / travel / VPN):
```bash
# Find your new ISP block
curl -s https://ipinfo.io/$(curl -4 -s ifconfig.me)/json | jq '{ip,org}'
whois $(curl -4 -s ifconfig.me) | grep route | head -3

# Add the new CIDR to dev.tfvars founder_ip_ranges, then:
TOKEN=$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)
export GOOGLE_OAUTH_ACCESS_TOKEN=$TOKEN
terraform -chdir=infra/terraform plan \
  -target=module.firewall \
  -var-file=environments/dev.tfvars \
  -var "postgres_password=$(cat ~/.meesell-secrets/dev-postgres-password)" \
  -var "valkey_password=$(cat ~/.meesell-secrets/dev-valkey-password)" \
  -out=.tflogs/firewall-isp-ranges.tfplan
terraform -chdir=infra/terraform apply .tflogs/firewall-isp-ranges.tfplan
```

**Rule:** `founder_ip_ranges` must never contain `0.0.0.0/0`. Use ISP CIDR blocks only (Playbook §2.3).

**Validate:** `kubectl get nodes` returns `meesell-dev-master Ready`.

**Side effect:** MSG91 has its own IP whitelist — separate from GCP. If OTP sends fail during testing, update MSG91's whitelist in the dashboard to match your current IP.

### 12.2 ADC token workaround (Terraform auth)

**Why:** ADC (`~/.config/gcloud/application_default_credentials.json`) is currently authenticated as `mugunthanks93@gmail.com`, but the project owner is `vaishnaviramoorthy@gmail.com`. ADC re-auth is fragile across browser sessions; the workaround injects a short-lived OAuth token from the active gcloud account.

**Pattern:** prefix every Terraform plan / apply with:
```bash
TOKEN=$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)
export GOOGLE_OAUTH_ACCESS_TOKEN=$TOKEN
```

The token is valid for ~1 hour. Re-export as needed during long sessions.

**Permanent fix (not yet done):**
```bash
gcloud auth application-default login \
  --account=vaishnaviramoorthy@gmail.com \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```
This is tracked as a follow-up — the OAuth-token workaround is reliable enough that ADC re-auth has not been forced.

### 12.3 Terraform state debugging (silent "No changes")

**Symptom:** a targeted plan (`-target=module.X`) returns "No changes" but live state clearly differs.

**Cause:** the `-target` address does not match any resource in state — Terraform does NOT warn when `-target` matches zero resources.

**Fix:**
```bash
terraform -chdir=infra/terraform state list | grep <pattern>
```

**Common gotcha:** modules with environment suffix in root (`module.valkey_dev`, `module.postgres_dev`, `module.supabase_studio_dev`) but no suffix in the module directory name.

### 12.4 Secret verification

```bash
gcloud secrets versions access latest \
  --secret=<secret-id> \
  --project=project-1f5cbf72-2820-4cdb-949
```

Local backups: `~/.meesell-secrets/<secret-id>` (`chmod 600`). Directory `chmod 700`.

**NEVER** echo a secret in chat, logs, `kubectl describe`, or `kubectl get secret -o yaml`. Rotation procedure is in Playbook §10.

### 12.5 cert-manager chart version note

cert-manager `v1.14.x` uses the Helm value `installCRDs = true`. cert-manager `v1.15+` switched to `crds.enabled = true`. The current install is `v1.14.5`; if upgrading, swap the value name in `modules/cert_manager/main.tf`.

Additionally, `startupapicheck.enabled = false` is set explicitly — the default startup probe Job hits `BackoffLimitExceeded` on a single-node K3s cluster. Cert issuance still works correctly without it.

### 12.6 Pod won't start

```bash
kubectl -n <ns> describe pod <pod>
kubectl -n <ns> logs <pod> --tail=100
kubectl -n <ns> logs <pod> --previous --tail=100 2>/dev/null
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -20
```

See Playbook §12.1 for the full runbook.

### 12.7 K3s API unreachable from laptop

See 12.1 (firewall IP rotation) — that's the cause 95% of the time. If the rule is correct, see Playbook §12.3.

---

## 13. Deferred Work

| Item | Why deferred | Target |
|---|---|---|
| `www.mesell.xyz` DNS + Ingress + prod namespace | Production cut-over gated on 1 week of clean staging (Playbook §15c) | Week 2 |
| `prod` namespace creation | Same as above | Week 2 |
| Terraform state migration: local -> GCS | Local laptop disk failure currently = state loss. Migration via `terraform init -migrate-state` is straightforward but no-one has scheduled the downtime. | Before any second engineer joins |
| LangFuse for AI tracing | `MVP_ARCHITECTURE.md §9.6` requirement; deferred per gap analysis D2 | V1.5 |
| Wildcard cert `*.mesell.xyz` | Requires DNS-01 challenge + Namecheap cert-manager plugin; HTTP-01 multi-SAN works for V1 | V1.5 |
| Off-VM backup storage | Postgres and Valkey backups currently land on the founder's laptop. Need to push to `gs://meesell-prod-assets/backups/` on a CronJob. | Pre-launch |
| Observability stack (Prometheus / Grafana / Loki) | Not yet required; Cloud Logging captures VM-level logs | Week 2 |
| Layer G account-lock hardening | Detect ADC identity mismatch at plan time via `data.google_client_openid_userinfo` precondition | Tracked, no urgency |
| Pass 3 Terraform modules (api, worker, frontend) | Nothing to manage until application images exist | Phase D |
| Persistent Playwright session for Namecheap | Avoid future device-verification rate limits | When next DNS edit is needed |

---

**End of document. If this conflicts with another doc, this document wins. Update on every live infra change.**
