# MeeSell Infrastructure — Terraform Conversion Plan

**Status:** Draft — awaiting founder review and decisions on open questions (Section 17)
**Playbook reference:** `docs/INFRASTRUCTURE_PLAYBOOK.md` (safety rules govern every decision here)
**Author:** meesell-infra-builder
**Date:** 2026-06-04

---

## 1. Goals and Non-Goals

### Goals

- Express every state-changing infrastructure decision (VM, firewall, namespaces, Kubernetes workloads) as Terraform code so it can be replayed identically for staging, prod, disaster recovery, and team hand-off.
- Make the Day 1 provisioning sequence reproducible with a single `terraform apply` (in two passes — see Section 11 for bootstrap order).
- Version-control infrastructure intent alongside application code.
- Preserve every [DANGER] and [SAFE] rule from Playbook Section 0 as Terraform lifecycle guards and explicit documentation.

### Non-Goals

- Replacing the playbook as the operator safety manual. The playbook's pre-flight checks (Section 1), daily ops (Section 11), incident runbooks (Section 12), and secret rotation (Section 10) remain imperative bash — they are operator procedures, not declarative state.
- Automating GitLab CI/CD (sketched in Section 16, not implemented now).
- Provisioning application workload images (owned by ci-cd-builder agent).
- Managing GCS buckets used by the application (application-layer concern).
- Multi-region or HA configuration. This is a single-node K3s cluster throughout MVP.

---

## 2. Directory Layout

> **SCOPE NOTE — R&D workspace is OUT OF SCOPE.**
> The directory `mesell/terraform/` is a live R&D flat workspace (state serial 68, last applied 2026-05-31). It manages `meesell-vm` and related supporting GCP resources for sandbox exploration only. Per founder decision (D6), `mesell/terraform/` is read-only from this plan's perspective. It will NOT be extended, modified, or have its state migrated. The three known safety gaps in that workspace (SSH open to world, no `prevent_destroy`, no billing budget) are acknowledged and held per founder direction. All production Terraform work described in this plan lives exclusively in `mesell/infra/terraform/` — a new directory that does not yet exist.

```
mesell/
├── Makefile.tf                          # Layer D: account-lock wrapper for all tf commands
├── scripts/
│   └── tf-preflight.sh                  # Layer E: identity + project gate (run before any apply)
│
└── infra/
    └── terraform/
        ├── README.md                    # Bootstrap order, ADC setup, account lock rationale
        ├── .terraform-version           # Pin tfenv version e.g. 1.8.5
        ├── .gitignore                   # *.tfstate*, *.tfvars (secrets), .terraform/
        │
        ├── environments/
        │   ├── dev.tfvars               # Variable values for dev (safe — no secrets)
        │   ├── staging.tfvars           # Day 7 values
        │   └── prod.tfvars              # Week 2 values
        │
        ├── modules/
        │   ├── vm/                      # GCP compute instance + boot disk + K3s cloud-init
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── firewall/                # Three firewall rules (http, https, k3s-api)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── k3s_bootstrap/           # cloud-init metadata for K3s install on VM
        │   │   ├── main.tf              # null_resource or cloud-init approach
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── artifact_registry/       # Production Artifact Registry (Docker format, asia-south1)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── asset_bucket/            # Production GCS asset bucket (versioning, public-blocked)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── ci_identity/             # CI service account + Workload Identity Federation (GitLab)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── app_secrets/             # Secret Manager entries (empty containers, values manual)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── billing_budget/          # google_billing_budget for meesell-dev-budget
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── namespaces/              # kubectl: dev, staging (prod deferred)
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── postgres/                # Kubernetes StatefulSet + PVC + Service
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── valkey/                  # Kubernetes StatefulSet + PVC + Service
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── supabase_studio/         # Kubernetes Deployment + Service
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── traefik_stack/           # Helm release for Traefik in traefik namespace
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   ├── cert_manager/            # Helm + CRDs + ClusterIssuer
        │   │   ├── main.tf
        │   │   ├── variables.tf
        │   │   └── outputs.tf
        │   │
        │   └── ingress/                 # Ingress resources per namespace/service
        │       ├── main.tf
        │       ├── variables.tf
        │       └── outputs.tf
        │
        ├── apis.tf                      # google_project_service for all required GCP APIs
        ├── providers.tf                 # Provider declarations + HARDCODED project/region (Section 19 Layer A)
        ├── backend.tf                   # State backend: backend "local" {} (D2 — GCS deferred)
        ├── main.tf                      # Root module: locals + data.google_project + account_lock_guard
        ├── variables.tf                 # Root-level variable declarations (NOT project_id — locked in providers.tf)
        ├── outputs.tf                   # Root-level outputs (vm_ip, kubeconfig_path, …)
        └── versions.tf                  # required_providers block with version pins
```

**Convention:** child modules own their own `variables.tf` and `outputs.tf`. The root `main.tf` calls each module and passes values down. No inline `resource` blocks in root `main.tf` (keep root a pure orchestrator). The root `apis.tf` is an exception — API-enable resources (`google_project_service`) live at root level and are applied first before any module that depends on an API being enabled.

---

## 3. Provider Strategy

### Required providers

| Provider | Purpose | Version pin |
|---|---|---|
| `hashicorp/google` | GCP compute, firewall, billing budget | `~> 5.30` |
| `hashicorp/google-beta` | `google_billing_budget` is in beta provider | `~> 5.30` |
| `hashicorp/kubernetes` | Namespaces, Secrets, StatefulSets, Deployments | `~> 2.30` |
| `hashicorp/helm` | Traefik and cert-manager Helm releases | `~> 2.13` |
| `hashicorp/random` | Only used if random_password approach is chosen (see Section 7) | `~> 3.6` |
| `hashicorp/null` | `null_resource` for remote-exec K3s bootstrap if cloud-init not chosen | `~> 3.2` |
| `hashicorp/tls` | Generating SSH key pair for VM access in CI | `~> 4.0` |
| `hashicorp/time` | `time_sleep` resource to insert wait between K3s ready and Kubernetes provider init | `~> 0.11` |

### The bootstrap chicken-and-egg problem (critical)

The `kubernetes`, `helm`, and any `kubectl` providers CANNOT be configured until the K3s cluster exists and the kubeconfig is reachable. The VM and K3s must be provisioned in Pass 1. The Kubernetes resources are applied in Pass 2.

Terraform solves this in one of two ways:

**Option A (recommended for MVP):** Split into two sequential `terraform apply` commands scoped with `-target`. Pass 1 targets `module.vm`, `module.firewall`, `module.k3s_bootstrap`, and `module.billing_budget`. After K3s is up and the kubeconfig is retrieved manually (or via `local-exec`), Pass 2 targets all remaining modules.

**Option B:** Use a single workspace but configure the kubernetes and helm providers with `host`, `client_certificate`, `client_key`, and `cluster_ca_certificate` drawn from Terraform outputs of the VM module. This works but only if K3s bootstrap is done via cloud-init (startup_script), so the API is available when Pass 2 runs. Requires a `time_sleep` resource of ~120 seconds after VM creation.

The plan recommends Option A for MVP — it matches the playbook's natural two-day flow (VM Day 1, workloads Day 1 afternoon) and makes debugging far easier for a solo founder.

### Provider initialisation in `versions.tf`

```hcl
terraform {
  required_version = ">= 1.8.0"
  required_providers {
    google      = { source = "hashicorp/google",      version = "~> 5.30" }
    google-beta = { source = "hashicorp/google-beta", version = "~> 5.30" }
    kubernetes  = { source = "hashicorp/kubernetes",  version = "~> 2.30" }
    helm        = { source = "hashicorp/helm",        version = "~> 2.13" }
    random      = { source = "hashicorp/random",      version = "~> 3.6"  }
    null        = { source = "hashicorp/null",        version = "~> 3.2"  }
    tls         = { source = "hashicorp/tls",         version = "~> 4.0"  }
    time        = { source = "hashicorp/time",        version = "~> 0.11" }
  }
}
```

---

## 4. State Backend

### Decision: GCS bucket (bootstrapped once, then used for all environments)

**Reasoning:**
- Solo founder today, but this repo will be handed off. GCS provides remote locking via Cloud Storage's built-in conditional updates (Terraform uses object versioning + lock blobs).
- Local state is simpler but creates a single-point-of-loss on the founder's laptop. One disk failure and all state is gone — unacceptable for a live SaaS.
- Terraform Cloud is overkill for a solo project and adds a SaaS dependency.
- GCS is already the chosen cloud provider, so no additional vendor.

**State bucket spec:**
- Bucket name: `meesell-tfstate` (globally unique; prefix with project ID if needed)
- Location: `ASIA-SOUTH1` (same region as VM)
- Storage class: `STANDARD`
- Versioning: enabled (30-day retention policy — allows rollback to previous state)
- Uniform bucket-level access: enabled
- Public access prevention: enforced

**`backend.tf`:**
```hcl
terraform {
  backend "gcs" {
    bucket  = "meesell-tfstate"
    prefix  = "terraform/state"
  }
}
```

**State locking:** GCS backend uses native object locking (`.tflock` blob). No DynamoDB needed. Concurrent applies are blocked automatically.

**Encryption:** GCS encrypts at rest by default with Google-managed keys. For MVP this is sufficient. The state file WILL contain sensitive data (see Section 7 for secret handling). Encryption at rest by GCS + access control via GCP IAM is the MVP approach.

**Bootstrap sequence for the state bucket itself:** The GCS bucket is the ONE resource that must be created imperatively before Terraform runs, because Terraform needs the backend before it can create anything. Create it once with `gcloud storage buckets create` (founder runs manually, one-time only). This is documented in the `terraform/README.md` bootstrap section.

---

## 5. Environment Strategy

### Decision: Directory-per-environment via `.tfvars` files, single workspace

**Why not workspaces:** Terraform workspaces share the same module code and use the same backend, but workspace isolation is subtle. For a small team (currently one person), having explicit `environments/dev.tfvars`, `environments/staging.tfvars`, and `environments/prod.tfvars` is more readable and auditable. The risk of `terraform workspace select prod` when intending `dev` is real.

**Why not separate directories per env:** The infrastructure is 90% identical across dev/staging/prod (same VM size, same modules). A single module tree parameterised by `environment` and `namespace` avoids code duplication. Only the `.tfvars` values differ.

**Mapping to playbook phases:**

| Playbook phase | tfvars file | Key differences |
|---|---|---|
| Day 1 | `environments/dev.tfvars` | `namespace = "dev"`, `postgres_storage_gb = 20`, `valkey_storage_gb = 5` |
| Day 7 (Section 15 staging) | `environments/staging.tfvars` | `namespace = "staging"`, same VM (it's the same cluster), mirrors dev values |
| Week 2 (prod) | `environments/prod.tfvars` | `namespace = "prod"`, `prevent_destroy = true` hardened, tighter resource limits |

**Apply command pattern:**
```
terraform apply -var-file=environments/dev.tfvars
terraform apply -var-file=environments/staging.tfvars
```

Staging and prod are new namespaces on the SAME K3s cluster (as per the playbook). No separate VM for staging at MVP.

---

## 6. Resource Mapping Table

| Playbook section | Playbook action | Terraform resource | Notes / gotchas |
|---|---|---|---|
| 2.2 VM | `gcloud compute instances create meesell-dev` | `google_compute_instance.meesell_dev` | Machine type, disk, labels, tags in `module.vm` |
| 2.2 VM | Boot disk 30GB pd-balanced Ubuntu 22.04 | `google_compute_disk` embedded in instance or `google_compute_instance.boot_disk` | Use `image = "ubuntu-os-cloud/ubuntu-2204-lts"` in `initialize_params` |
| 2.3 Firewall | `meesell-dev-http` (tcp:80, 0.0.0.0/0) | `google_compute_firewall.meesell_dev_http` | `module.firewall` |
| 2.3 Firewall | `meesell-dev-https` (tcp:443, 0.0.0.0/0) | `google_compute_firewall.meesell_dev_https` | `module.firewall` |
| 2.3 Firewall | `meesell-dev-k3s-api` (tcp:6443, founder IP/32) | `google_compute_firewall.meesell_dev_k3s_api` | [DANGER] source_ranges MUST be `var.founder_ip` + `/32`, never hardcoded `0.0.0.0/0` |
| 3.2 K3s | `curl -sfL https://get.k3s.io | sh -s - server ...` | `google_compute_instance.meesell_dev` with `metadata.startup-script` (cloud-init) | See Section 8 for full analysis |
| 4 Namespaces | `kubectl create namespace dev/staging` | `kubernetes_namespace.dev`, `kubernetes_namespace.staging` | Labels via `metadata.labels.env` |
| 5.1 PG secret | `kubectl create secret generic postgres-credentials` | See Section 7 — NOT a random_password resource | `module.postgres` |
| 5.2 PG StatefulSet | StatefulSet + headless Service + PVC | `kubernetes_stateful_set.postgres`, `kubernetes_service.postgres` | PVC template inside StatefulSet spec; `lifecycle { prevent_destroy = true }` on PVC |
| 6.1 Valkey secret | `kubectl create secret generic valkey-credentials` | See Section 7 — NOT a random_password resource | `module.valkey` |
| 6.2 Valkey StatefulSet | StatefulSet + headless Service + PVC | `kubernetes_stateful_set.valkey`, `kubernetes_service.valkey` | Same lifecycle guard on PVC |
| 7 Supabase Studio | Deployment + ClusterIP Service | `kubernetes_deployment.supabase_studio`, `kubernetes_service.supabase_studio` | `module.supabase_studio` |
| 8.1 Traefik | `helm upgrade --install traefik traefik/traefik` | `helm_release.traefik` | `module.traefik_stack`; namespace `traefik` created as `kubernetes_namespace.traefik` |
| 8.2 cert-manager | `kubectl apply -f cert-manager.yaml` | `helm_release.cert_manager` (use Jetstack's Helm chart, not raw apply) | Helm chart bundles CRDs; version pin to `v1.14.5` equivalent |
| 8.3 ClusterIssuer | `kubectl apply -f letsencrypt.yaml` | `kubernetes_manifest.cluster_issuer_letsencrypt_prod` | Requires `cert-manager` CRDs installed first — explicit `depends_on = [helm_release.cert_manager]` |
| 9 Ingress | `kubectl apply -f ingress-studio.yaml` | `kubernetes_manifest.ingress_studio` (or `kubernetes_ingress_v1.studio`) | Parameterised by `var.domain`; only applied after DNS is confirmed |
| 13 Billing budget | `gcloud beta billing budgets create ...` | `google_billing_budget.meesell_dev_budget` | `module.billing_budget`; uses `google-beta` provider alias |
| PLAN-ADD | Production Artifact Registry (Docker, asia-south1) | `google_artifact_registry_repository.meesell_prod_images` | `module.artifact_registry`; format=DOCKER, location=asia-south1; cleanup policy: keep last 10 untagged images, keep all tagged |
| PLAN-ADD | GCS production asset bucket | `google_storage_bucket.meesell_prod_assets` | `module.asset_bucket`; asia-south1, uniform bucket-level access, public access prevention enforced, versioning enabled; optional 30-day delete lifecycle rule on `temp/` prefix |
| PLAN-ADD | CI service account | `google_service_account.meesell_prod_ci` | `module.ci_identity`; email: `meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` |
| PLAN-ADD | CI SA IAM binding — Artifact Registry writer | `google_project_iam_member` (`roles/artifactregistry.writer` on CI SA) | `module.ci_identity`; scoped to project level (AR RBAC handles repo-level) |
| PLAN-ADD | CI SA IAM binding — GCS object admin | `google_storage_bucket_iam_member` (`roles/storage.objectAdmin` on CI SA, scoped to asset bucket) | `module.ci_identity`; bucket-scoped, not project-wide |
| PLAN-ADD | CI SA IAM binding — service account user (if needed) | `google_project_iam_member` (`roles/iam.serviceAccountUser` on CI SA) | `module.ci_identity`; only if Cloud Build or impersonation flows require it |
| PLAN-ADD | Workload Identity Federation pool (GitLab) | `google_iam_workload_identity_pool.gitlab_prod` | `module.ci_identity`; pool id: `gitlab-prod-pool`; display name: MeeSell Prod GitLab |
| PLAN-ADD | Workload Identity Federation provider (GitLab OIDC) | `google_iam_workload_identity_pool_provider.gitlab_prod` | `module.ci_identity`; OIDC; issuer: `https://gitlab.com`; attribute mapping: `google.subject=assertion.sub`, `attribute.aud=assertion.aud`, `attribute.repository=assertion.project_path`, `attribute.repository_path=assertion.project_path`, `attribute.ref_path=assertion.ref_path`; attribute condition: `attribute.repository == var.gitlab_repository_path` |
| PLAN-ADD | WIF → CI SA impersonation binding | `google_service_account_iam_member` (WIF pool principal → `roles/iam.workloadIdentityUser` on CI SA) | `module.ci_identity`; principal: `principalSet://iam.googleapis.com/.../attribute.repository/techades/mesell` |
| PLAN-ADD | Secret Manager entry — gemini-api-key | `google_secret_manager_secret.gemini_api_key` | `module.app_secrets`; empty initial version; `lifecycle.ignore_changes = [secret_data]` on version; founder populates via `gcloud secrets versions add` |
| PLAN-ADD | Secret Manager entry — msg91-auth-key | `google_secret_manager_secret.msg91_auth_key` | `module.app_secrets`; same lifecycle pattern |
| PLAN-ADD | Secret Manager entry — jwt-secret | `google_secret_manager_secret.jwt_secret` | `module.app_secrets`; same lifecycle pattern |
| PLAN-ADD | Secret Manager entry — razorpay-key-id | `google_secret_manager_secret.razorpay_key_id` | `module.app_secrets`; same lifecycle pattern |
| PLAN-ADD | Secret Manager entry — razorpay-key-secret | `google_secret_manager_secret.razorpay_key_secret` | `module.app_secrets`; same lifecycle pattern |

---

## 7. Secret Bootstrap Pattern

### The problem
Kubernetes Secrets for `postgres-credentials` and `valkey-credentials` must exist before Postgres and Valkey pods can start. The passwords must be random and strong. They must not be readable by anyone who has `git log` access. They must also survive `terraform destroy` + re-apply without data loss (you can destroy the pod but the PVC still has the data — the new pod must get the same password).

### Four options evaluated

**Option (a): `random_password` in Terraform state**
- How it works: `random_password.postgres` generates a password. `kubernetes_secret.postgres_credentials` stores it. Both live in state.
- Problem: Terraform state stored in GCS would contain the plaintext password in base64. GCS state bucket has IAM access control, so only the service account can read it. This is acceptable for many teams. BUT the playbook's [DANGER] rule says "NEVER expose secrets in logs, commits, shell history." The state file is not a commit, but it IS a file that could be read by anyone with bucket access.
- Verdict: **acceptable risk for MVP IF** the state bucket has strict IAM (only `meesell-tf-runner` service account). The convenience is high — secrets rotate cleanly, `terraform apply` is idempotent.

**Option (b): Google Secret Manager (`google_secret_manager_secret` + `google_secret_manager_secret_version`)**
- How it works: Terraform creates the GSM secret resource. The actual secret value is either injected manually or via a `local-exec` that calls `gcloud secrets versions add`. Kubernetes pods read from GSM at runtime via workload identity + a sidecar or init container.
- Problem: adds significant complexity (GSM SDK in pods, workload identity binding). Not aligned with the playbook's `secretKeyRef` approach.
- Verdict: **over-engineered for MVP.** Reserve for Week 2 when app secrets (GEMINI_API_KEY, RAZORPAY_KEY_SECRET) also need management.

**Option (c): SOPS-encrypted file**
- How it works: passwords generated once, encrypted with a GCP KMS key using SOPS, committed to git as `.sops.yaml`. Terraform decrypts at apply time.
- Problem: requires KMS key (cost), SOPS toolchain setup, and additional bootstrap steps. More moving parts than MVP warrants.
- Verdict: **good long-term pattern, not MVP.**

**Option (d): `kubernetes_secret` with `lifecycle.ignore_changes` + manual seeding (recommended for MVP)**
- How it works:
  1. Terraform creates the `kubernetes_secret` resource with placeholder values OR with a `sensitive` variable passed at apply time.
  2. The first apply sets the secret. After that, `lifecycle { ignore_changes = [data] }` prevents Terraform from ever overwriting it.
  3. Actual password generation stays in the playbook's Section 5.1 / 6.1 (openssl rand, saved to `~/.meesell-secrets/`), and is injected once at first apply via a `-var` flag or a `secret.auto.tfvars` file NOT committed to git.
- Problem: the password value is still in state on first apply.
- Mitigation: same as option (a) — state bucket IAM is the control.

### Chosen approach: Option (d) with a `sensitive` variable

```hcl
# In variables.tf
variable "postgres_password" {
  type      = string
  sensitive = true
  default   = null  # must be supplied at first apply
}
```

```hcl
# In module/postgres/main.tf
resource "kubernetes_secret" "postgres_credentials" {
  metadata { name = "postgres-credentials"; namespace = var.namespace }
  data = {
    username = "meesell"
    password = var.postgres_password
    database = "meesell"
  }
  lifecycle {
    ignore_changes = [data]   # never overwrite after first apply
  }
}
```

At first apply: `terraform apply -var="postgres_password=$PG_PASSWORD" -var-file=environments/dev.tfvars`

The password is generated by the founder using the playbook's existing command (`openssl rand -base64 32`) and stored in `~/.meesell-secrets/dev-postgres-password` exactly as the playbook describes. The `~/.meesell-secrets/` directory is never touched by Terraform — it remains the playbook's domain for secret rotation (Section 10).

**What lives in Terraform state vs playbook:** Terraform knows the Kubernetes Secret exists. After `ignore_changes = [data]`, the in-cluster secret data drifts from state — that is intentional. The playbook's Section 10 rotation procedure remains the authoritative rotation path.

**Trade-off explicitly stated:** The password IS in the GCS state file after first apply. This is the same risk as using the google provider for many secrets. Mitigation: (1) restrict GCS bucket ACL to only the Terraform service account, (2) enable bucket versioning + 30-day retention, (3) never share state file contents.

### Secret Manager entries for production app-level secrets

The five production app secrets (`gemini-api-key`, `msg91-auth-key`, `jwt-secret`, `razorpay-key-id`, `razorpay-key-secret`) managed by `module.app_secrets` follow the SAME `lifecycle.ignore_changes` discipline as the Kubernetes secrets above. The pattern is:

1. Terraform creates the `google_secret_manager_secret` container (the label/metadata resource).
2. Terraform creates an initial `google_secret_manager_secret_version` with a placeholder value (e.g., `"PLACEHOLDER_SET_MANUALLY"`) and `lifecycle { ignore_changes = [secret_data] }` so subsequent applies never overwrite it.
3. The founder populates the real value once, manually, using ADC as `vaishnaviramoorthy@gmail.com`:
   ```
   gcloud secrets versions add gemini-api-key \
     --account=vaishnaviramoorthy@gmail.com \
     --data-file=- <<< "$GEMINI_KEY"
   ```
4. After manual population, Terraform state retains only the placeholder — the real secret value never enters Terraform state. This is strictly stronger than the `kubernetes_secret` approach where the value IS in state after first apply.

The `app_secrets` module is a Pass 1 resource (applied alongside VM, firewall, AR, GCS, and CI identity) because the secret containers must exist before the K3s workloads that read them are deployed in Pass 2. Value population by the founder can happen at any point before Pass 2 executes.

---

## 8. K3s Install Strategy

### The problem
K3s is installed on the VM via `curl | sh` with flags `--disable=traefik --tls-san=<PUBLIC_IP> --write-kubeconfig-mode=644`. This is an imperative SSH operation. Terraform must either own it, trigger it, or leave it manual.

### Four options evaluated

| Option | Mechanism | Idempotency | Debuggability | TLS SAN issue |
|---|---|---|---|---|
| (a) cloud-init startup_script | `google_compute_instance.metadata.startup-script` | Good — runs once on first boot only | Hard — must SSH in to read `/var/log/syslog` | Solvable: `curl -s ifconfig.me` inside the script runs ON the VM, gets VM's public IP correctly |
| (b) `null_resource` + `remote-exec` | Provisioner over SSH after VM create | Moderate — provisioners don't re-run unless tainted | Moderate — output visible in `terraform apply` log | Solvable: `$(curl -s ifconfig.me)` runs on the VM via remote-exec |
| (c) `local-exec` calling a local shell script | Runs on founder's laptop, SSHes to VM | Poor — re-runs every apply | Good — script is readable | Hard: `curl -s ifconfig.me` from laptop gives laptop IP, not VM IP |
| (d) Keep manual, document trigger | No Terraform resource for K3s | N/A | Best | Not a problem — manual step |

### Chosen approach: Option (a) — cloud-init startup_script

**Reasoning:**
- The VM is provisioned once and never replaced (single-node K3s). The startup_script fires exactly once on first boot.
- No SSH provisioner means no private key management in Terraform state.
- The `--tls-san=$(curl -s ifconfig.me)` command runs on the VM, so `ifconfig.me` returns the VM's external IP — correct and idempotent.
- The startup_script is version-controlled inside the `module/vm/main.tf` `templatefile()` call.

**The TLS SAN issue in detail:**
```bash
# This runs ON the VM during boot, so ifconfig.me returns the VM's own external IP.
# Terraform does not need to know the IP at plan time.
curl -sfL https://get.k3s.io | sh -s - server \
  --disable=traefik \
  --tls-san=$(curl -s ifconfig.me) \
  --write-kubeconfig-mode=644 \
  --node-name=meesell-dev-master
```
This works correctly as a startup_script because the VM's NIC IP is what `ifconfig.me` returns when called from the VM.

**Idempotency:** The K3s installer script is idempotent (re-running it upgrades or is a no-op if same version). Startup scripts fire once on first boot only — no re-run on VM restart. This matches the playbook's intent.

**Debuggability:** To check K3s install status after VM creation, the operator SSHes and runs `sudo systemctl status k3s`. This is documented in the terraform/README.md bootstrap instructions. It is the same debugging path as the playbook's Section 3.2.

**kubeconfig retrieval:** After K3s is up, the founder retrieves the kubeconfig with the playbook's Section 3.3 `gcloud compute scp` command. This remains a manual step — Terraform does NOT automate kubeconfig retrieval because it would require storing the kubeconfig on the founder's laptop path, which is an environment-specific local file, not infrastructure state.

**Terraform pass boundary:** The kubernetes provider is configured AFTER kubeconfig retrieval. This is the dividing line between Pass 1 and Pass 2.

---

## 9. Module Boundaries

### Module: `vm`
- **Purpose:** Google Compute instance, attached boot disk, labels, tags, cloud-init startup_script for K3s.
- **Inputs:** `project_id`, `zone`, `machine_type`, `vm_disk_size_gb`, `vm_name`, `startup_script_template`
- **Outputs:** `vm_external_ip`, `vm_instance_self_link`, `vm_name`
- **Dependencies:** None (root-level GCP resources)

### Module: `firewall`
- **Purpose:** Three firewall rules (http, https, k3s-api).
- **Inputs:** `project_id`, `network`, `founder_ip`, `target_vm_tags`
- **Outputs:** `firewall_rule_names` (list)
- **Dependencies:** `module.vm` (for tag reference, though tag is a string — can be parallel)
- **Critical:** `founder_ip` used for k3s-api rule must be `var.founder_ip`, never a literal. A `validation` block enforces it is not `0.0.0.0`.

### Module: `billing_budget`
- **Purpose:** `google_billing_budget` with 50/75/90% thresholds.
- **Inputs:** `billing_account_id`, `budget_amount_usd`, `display_name`
- **Outputs:** `budget_name`
- **Dependencies:** None (GCP-level resource, no K3s needed)

### Module: `k3s_bootstrap`
- **Purpose:** Logical module — holds the cloud-init script template and the `time_sleep` resource that Pass 2 waits on.
- **Inputs:** None beyond what is baked into startup_script via `module.vm`
- **Outputs:** `k3s_ready_trigger` (a sentinel output used by Pass 2 `depends_on`)
- **Note:** This module exists to encapsulate the startup_script template in one place. The `time_sleep.k3s_boot` resource (`duration = "120s"`) is referenced by Pass 2 modules as their `depends_on`.

### Module: `namespaces`
- **Purpose:** `kubernetes_namespace` for `dev` and `staging` with `env` labels.
- **Inputs:** `namespaces` (list of objects with `name` and `env` label)
- **Outputs:** `namespace_names` (list)
- **Dependencies:** kubernetes provider (Pass 2)

### Module: `postgres`
- **Purpose:** Kubernetes Secret (postgres-credentials), headless Service, StatefulSet with PVC template.
- **Inputs:** `namespace`, `postgres_password` (sensitive), `storage_gb`, `cpu_request`, `cpu_limit`, `memory_request`, `memory_limit`, `image_tag`
- **Outputs:** `service_hostname` (e.g., `postgres.dev.svc.cluster.local`), `secret_name`
- **Dependencies:** `module.namespaces`

### Module: `valkey`
- **Purpose:** Kubernetes Secret (valkey-credentials), headless Service, StatefulSet with PVC template.
- **Inputs:** `namespace`, `valkey_password` (sensitive), `storage_gb`, resource limits
- **Outputs:** `service_hostname`, `secret_name`
- **Dependencies:** `module.namespaces`

### Module: `supabase_studio`
- **Purpose:** Kubernetes Deployment + ClusterIP Service. References postgres secret.
- **Inputs:** `namespace`, `image_tag`, `postgres_secret_name`, resource limits
- **Outputs:** `service_name`, `service_port`
- **Dependencies:** `module.postgres` (for `postgres_secret_name`)

### Module: `traefik_stack`
- **Purpose:** `kubernetes_namespace.traefik` + `helm_release.traefik`. Creates the `traefik` namespace and installs Traefik with LoadBalancer service.
- **Inputs:** `chart_version`, `namespace`, `dashboard_enabled` (default false)
- **Outputs:** `traefik_lb_ip` (obtained from Kubernetes service status — may be empty until LB assigns)
- **Dependencies:** `module.namespaces` (technically independent but apply after namespaces for consistency)

### Module: `cert_manager`
- **Purpose:** `helm_release.cert_manager` (installs CRDs + controller) + `kubernetes_manifest.cluster_issuer` (ClusterIssuer for Let's Encrypt).
- **Inputs:** `chart_version`, `acme_email`, `domain`
- **Outputs:** `cluster_issuer_name`
- **Dependencies:** `module.traefik_stack` (Traefik must be running for HTTP01 challenge solver)

### Module: `ingress`
- **Purpose:** `kubernetes_manifest.ingress_studio` (and later API/frontend Ingresses). Parameterised by domain.
- **Inputs:** `namespace`, `domain`, `service_name`, `service_port`, `tls_secret_name`, `cluster_issuer_name`
- **Outputs:** `ingress_host`
- **Dependencies:** `module.cert_manager`, DNS records (cannot be Terraform-managed unless using Cloud DNS — out of scope for MVP)
- **Guarded by:** `var.domain` must be set (non-empty string). If `domain = ""`, ingress module outputs a warning and creates nothing.

### Module: `billing_budget`
- **Purpose:** `google_billing_budget.meesell_dev_budget`.
- **Inputs:** `billing_account_id`, `budget_amount_usd`
- **Outputs:** `budget_name`
- **Dependencies:** None

### Module: `artifact_registry`
- **Purpose:** Production Docker Artifact Registry repository. Fully isolated from the R&D workspace's `meesell-images` repository.
- **Inputs:** `location` (default `"asia-south1"`), `repository_id` (e.g., `"meesell-prod-images"`), `format` (hardcoded `"DOCKER"` in module)
- **Outputs:** `repository_id`, `repository_url` (full URL for `docker push`)
- **Dependencies:** `google_project_service` for `artifactregistry.googleapis.com` must be enabled first. This is a root-level `apis.tf` precondition — the module does not enable APIs itself. Enforced by `depends_on = [google_project_service.apis]` in the root `main.tf` call.

### Module: `asset_bucket`
- **Purpose:** Production GCS asset bucket for images, exports, and application file storage.
- **Inputs:** `bucket_name` (globally unique — see variable `gcs_asset_bucket_name`), `location` (default `"ASIA-SOUTH1"`), `lifecycle_rules` (list of rule objects — a `temp/` prefix 30-day rule is pre-configured as a default), `force_destroy` (default `false`)
- **Outputs:** `bucket_name`, `bucket_url` (e.g., `gs://meesell-prod-assets`)
- **Dependencies:** `google_project_service` for `storage.googleapis.com` must be enabled. `prevent_destroy = true` is set on the bucket resource inside the module — removal requires a deliberate code change.

### Module: `ci_identity`
- **Purpose:** CI pipeline identity — creates the GitLab CI service account, the Workload Identity Federation pool and OIDC provider, and the IAM bindings that allow GitLab CI jobs in the `techades/mesell` repository to impersonate the CI service account without storing a JSON key.
- **Inputs:** `service_account_id` (default `"meesell-prod-ci"`), `gitlab_repository_path` (e.g., `"techades/mesell"` — used in the WIF attribute condition), `project_id` (passed from root — locked constant), `artifact_registry_repository_id` (to scope the AR writer binding), `asset_bucket_name` (to scope the GCS binding)
- **Outputs:** `ci_sa_email`, `wif_pool_provider_resource_name` (full resource name used in GitLab CI variable `WORKLOAD_IDENTITY_PROVIDER`), `ci_sa_impersonation_target` (the SA email GitLab CI sets as `SERVICE_ACCOUNT_EMAIL`)
- **Dependencies:** APIs `iam.googleapis.com`, `iamcredentials.googleapis.com`, `sts.googleapis.com` must be enabled. `module.artifact_registry` and `module.asset_bucket` must exist (their IDs are needed for scoped IAM bindings).

### Module: `app_secrets`
- **Purpose:** Creates the Secret Manager secret containers for the five production app-level secrets. Does NOT populate secret values — that is the founder's manual step. Values never enter Terraform state.
- **Inputs:** `secret_ids` (list of strings — default `["gemini-api-key", "msg91-auth-key", "jwt-secret", "razorpay-key-id", "razorpay-key-secret"]`), `namespace_label` (a label tag added to each secret for organisational filtering)
- **Outputs:** `secret_resource_names` (map of secret_id → full resource name, e.g., `projects/project-1f5cbf72-2820-4cdb-949/secrets/gemini-api-key`)
- **Dependencies:** `google_project_service` for `secretmanager.googleapis.com` must be enabled.

---

## 10. Variables and Outputs

### Root-level input variables (`variables.tf`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `project_id` | `string` | — | GCP project ID (`project-1f5cbf72-2820-4cdb-949`) |
| `zone` | `string` | `"asia-south1-a"` | GCP zone |
| `region` | `string` | `"asia-south1"` | GCP region |
| `vm_name` | `string` | `"meesell-dev"` | Compute instance name |
| `machine_type` | `string` | `"e2-standard-2"` | GCP machine type |
| `vm_disk_size_gb` | `number` | `30` | Boot disk size |
| `founder_ip` | `string` | — | Founder's current public IP for firewall rule (no default — must be supplied) |
| `billing_account_id` | `string` | — | GCP billing account ID |
| `budget_amount_usd` | `number` | `300` | Monthly budget cap |
| `domain` | `string` | `""` | Purchased domain (empty = skip ingress/TLS) |
| `acme_email` | `string` | `"vaishnaviramoorthy@gmail.com"` | Let's Encrypt registration email |
| `environment` | `string` | `"dev"` | Target environment (`dev`, `staging`, `prod`) |
| `postgres_storage_gb` | `number` | `20` | Postgres PVC size |
| `valkey_storage_gb` | `number` | `5` | Valkey PVC size |
| `postgres_image_tag` | `string` | `"16"` | Postgres Docker image tag |
| `valkey_image_tag` | `string` | `"8"` | Valkey Docker image tag |
| `supabase_studio_image_tag` | `string` | `"latest"` | Supabase Studio image tag |
| `traefik_chart_version` | `string` | `"28.3.0"` | Traefik Helm chart version pin |
| `cert_manager_chart_version` | `string` | `"v1.14.5"` | cert-manager Helm chart version pin |
| `kubeconfig_path` | `string` | `"~/.kube/meesell-dev.yaml"` | Path to kubeconfig on founder's laptop (Pass 2 only) |
| `postgres_password` | `string` (sensitive) | — | Postgres password — injected at first apply, never committed |
| `valkey_password` | `string` (sensitive) | — | Valkey password — injected at first apply, never committed |
| `namespaces_to_create` | `list(string)` | `["dev", "staging"]` | Which namespaces to create. Prod excluded until Week 2 |
| `gcs_asset_bucket_name` | `string` | `"meesell-prod-assets"` | GCS asset bucket name — must be globally unique. Founder should override if the default is already taken (unlikely but possible). See Q10. |
| `artifact_registry_repo_id` | `string` | `"meesell-prod-images"` | Artifact Registry repository ID for production Docker images |
| `ci_service_account_id` | `string` | `"meesell-prod-ci"` | Service account short ID for the CI pipeline identity |
| `gitlab_repository_path` | `string` | `"techades/mesell"` | GitLab repository path used in the WIF attribute condition (restricts which GitLab project can impersonate the CI SA). See Q9 for confirmation. |
| `app_secret_ids` | `list(string)` | `["gemini-api-key", "msg91-auth-key", "jwt-secret", "razorpay-key-id", "razorpay-key-secret"]` | Secret Manager secret IDs to create. Maps 1:1 to `backend/.env.example` variables: `GEMINI_API_KEY`, `MSG91_AUTH_KEY`, `JWT_SECRET`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`. |
| `gcp_api_services` | `list(string)` | `["compute.googleapis.com", "artifactregistry.googleapis.com", "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com", "secretmanager.googleapis.com", "storage.googleapis.com", "billingbudgets.googleapis.com"]` | GCP APIs to enable via `google_project_service` in `apis.tf`. Applied first, before any module that depends on an API being active. |

**Note on `project_id` and `billing_account_id`:** These are NOT declared as variables in `variables.tf`. They are hardcoded constants in `providers.tf` and `modules/billing_budget/main.tf` respectively (Section 19, Layer A). This removes the risk of accidentally running the workspace against a different project.

### Root-level outputs (`outputs.tf`)

| Output | Source | Description |
|---|---|---|
| `vm_external_ip` | `module.vm.vm_external_ip` | VM public IP — also needed for firewall update if founder IP changes |
| `kubeconfig_reminder` | static string | "Run: gcloud compute scp meesell-dev:/etc/rancher/k3s/k3s.yaml ..." — a post-apply instruction |
| `postgres_service_host` | `module.postgres.service_hostname` | In-cluster PG hostname |
| `valkey_service_host` | `module.valkey.service_hostname` | In-cluster Valkey hostname |
| `traefik_lb_ip` | `module.traefik_stack.traefik_lb_ip` | External IP for DNS A records |
| `billing_budget_name` | `module.billing_budget.budget_name` | GCP budget display name |
| `ingress_host` | `module.ingress.ingress_host` | Studio URL when domain is set |
| `artifact_registry_url` | `module.artifact_registry.repository_url` | Full Docker push URL (e.g., `asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images`) |
| `asset_bucket_url` | `module.asset_bucket.bucket_url` | GCS bucket URL (e.g., `gs://meesell-prod-assets`) |
| `ci_sa_email` | `module.ci_identity.ci_sa_email` | CI service account email — set as `SERVICE_ACCOUNT_EMAIL` in GitLab CI variables |
| `wif_provider_name` | `module.ci_identity.wif_pool_provider_resource_name` | Full WIF provider resource name — set as `WORKLOAD_IDENTITY_PROVIDER` in GitLab CI variables |
| `app_secret_resource_names` | `module.app_secrets.secret_resource_names` | Map of secret ID → full resource name for reference |

---

## 11. Bootstrap Order

### Pre-Terraform steps (manual, one-time)

1. Run all Section 1 pre-flight checks from the playbook. Confirm `vaishnaviramoorthy@gmail.com`, project `project-1f5cbf72-2820-4cdb-949`, zone `asia-south1-a`, billing OPEN.
2. Run `mesell/scripts/tf-preflight.sh` — the Layer E gate confirms ADC identity, project, and zone before any Terraform command (see Section 19).
3. **State backend:** `backend "local" {}` — no GCS bucket bootstrap step required. State is stored on the founder's laptop at `mesell/infra/terraform/terraform.tfstate`. Risk acknowledged (D2). Migration to GCS via `terraform init -migrate-state` is deferred.
4. Generate passwords and save them per playbook Section 5.1 / 6.1:
   ```
   mkdir -p ~/.meesell-secrets && chmod 700 ~/.meesell-secrets
   openssl rand -base64 32 | tr -d '\n' > ~/.meesell-secrets/dev-postgres-password
   openssl rand -base64 32 | tr -d '\n' > ~/.meesell-secrets/dev-valkey-password
   chmod 600 ~/.meesell-secrets/dev-postgres-password ~/.meesell-secrets/dev-valkey-password
   ```
5. Capture founder IP:
   ```
   export FOUNDER_IP=$(curl -s ifconfig.me)
   ```

### Pass 1 — GCP resources only (APIs → identity → registry → bucket → secrets → VM → firewall → billing budget)

The ordered application sequence within Pass 1 prevents dependency failures:

1. **Enable APIs** (`apis.tf` root-level resources) — `google_project_service` for all eight APIs. Applied first because every module that follows depends on at least one API.
2. **`module.ci_identity`** — CI service account + WIF pool + provider + bindings. Applied before registry and bucket because IAM bindings reference those resource IDs.
3. **`module.artifact_registry`** — Docker AR repository. Depends on `artifactregistry.googleapis.com` enabled.
4. **`module.asset_bucket`** — GCS asset bucket. Depends on `storage.googleapis.com` enabled.
5. **`module.app_secrets`** — Secret Manager containers (empty). Depends on `secretmanager.googleapis.com` enabled. Values populated manually by founder after this step.
6. **`module.vm`** — Compute instance with K3s cloud-init startup script.
7. **`module.firewall`** — Three firewall rules (http, https, k3s-api scoped to `$FOUNDER_IP`).
8. **`module.billing_budget`** — Billing budget with 50/75/90% thresholds against billing account `01620D-6785AB-0E4698`.

Apply command (using `Makefile.tf` wrapper per Section 19 Layer D):

```
cd mesell
make tf-init
make tf-plan-pass1 FOUNDER_IP=$FOUNDER_IP
# Review plan output — show to founder before applying
make tf-apply-pass1 FOUNDER_IP=$FOUNDER_IP
```

Or directly:
```
cd mesell/infra/terraform
terraform init
terraform apply \
  -var-file=environments/dev.tfvars \
  -var="founder_ip=$FOUNDER_IP" \
  -target=google_project_service.apis \
  -target=module.ci_identity \
  -target=module.artifact_registry \
  -target=module.asset_bucket \
  -target=module.app_secrets \
  -target=module.vm \
  -target=module.firewall \
  -target=module.billing_budget
```

After Pass 1 completes:

5. Retrieve kubeconfig per playbook Section 3.3:
   ```
   VM_IP=$(terraform output -raw vm_external_ip)
   gcloud compute scp meesell-dev:/etc/rancher/k3s/k3s.yaml ~/.kube/meesell-dev.yaml \
     --zone=asia-south1-a
   sed -i.bak "s/127.0.0.1/${VM_IP}/g" ~/.kube/meesell-dev.yaml
   chmod 600 ~/.kube/meesell-dev.yaml
   export KUBECONFIG=~/.kube/meesell-dev.yaml
   kubectl get nodes    # must return Ready before continuing
   ```
6. Validate K3s per playbook Section 3.2 before proceeding.

### Pass 2 — Kubernetes workloads (all remaining modules)

Before running Pass 2: populate the Secret Manager entries manually (see Section 20 — `app_secrets` module population procedure) so that app pods can reference them at deploy time.

```
cd mesell/infra/terraform
terraform apply \
  -var-file=environments/dev.tfvars \
  -var="founder_ip=$FOUNDER_IP" \
  -var="kubeconfig_path=$HOME/.kube/meesell-dev.yaml" \
  -var="postgres_password=$(cat ~/.meesell-secrets/dev-postgres-password)" \
  -var="valkey_password=$(cat ~/.meesell-secrets/dev-valkey-password)"
```

This apply targets all remaining modules: `module.namespaces`, `module.postgres`, `module.valkey`, `module.supabase_studio`, `module.traefik_stack`, `module.cert_manager`. The `module.ingress` is only included if `var.domain` is non-empty.

### Steady-state (after bootstrap)

Once both passes are complete, a full `terraform apply` without `-target` is safe and idempotent. Any infrastructure drift is corrected. Secrets are protected by `lifecycle.ignore_changes`.

### Day 7 — Adding staging workloads

```
cd mesell/infra/terraform
terraform apply \
  -var-file=environments/staging.tfvars \
  -var="founder_ip=$FOUNDER_IP" \
  -var="postgres_password=$(cat ~/.meesell-secrets/staging-postgres-password)" \
  -var="valkey_password=$(cat ~/.meesell-secrets/staging-valkey-password)"
```

The `namespaces_to_create` variable in `staging.tfvars` still includes `["dev", "staging"]`. Terraform detects `dev` namespace already exists (no-op) and creates staging workloads. No VM changes.

### Week 2 — Adding prod namespace

New `environments/prod.tfvars` with `environment = "prod"`, `namespaces_to_create = ["dev", "staging", "prod"]`. Before running, staging must pass acceptance for one full week (playbook Section 15).

---

## 12. Mapping from Playbook Commands to Terraform

| Playbook section | Imperative command | Terraform equivalent |
|---|---|---|
| 2.2 | `gcloud compute instances create meesell-dev ...` | `google_compute_instance.meesell_dev` in `module.vm` |
| 2.2 | `gcloud compute instances describe meesell-dev ...` | `terraform output vm_external_ip` |
| 2.3 | `gcloud compute firewall-rules create meesell-dev-http` | `google_compute_firewall.meesell_dev_http` in `module.firewall` |
| 2.3 | `gcloud compute firewall-rules create meesell-dev-https` | `google_compute_firewall.meesell_dev_https` in `module.firewall` |
| 2.3 | `gcloud compute firewall-rules create meesell-dev-k3s-api` | `google_compute_firewall.meesell_dev_k3s_api` in `module.firewall` |
| 2.3 | `gcloud compute firewall-rules update meesell-dev-k3s-api --source-ranges=...` | `terraform apply -var="founder_ip=<NEW_IP>"` — Terraform updates the resource |
| 3.2 | `curl -sfL https://get.k3s.io | sh -s - server ...` | `metadata.startup-script` in `google_compute_instance` via `module.vm` |
| 4 | `kubectl create namespace dev` | `kubernetes_namespace.dev` in `module.namespaces` |
| 4 | `kubectl create namespace staging` | `kubernetes_namespace.staging` in `module.namespaces` |
| 4 | `kubectl label namespace dev env=dev` | `metadata.labels = { env = "dev" }` in namespace resource |
| 5.1 | `kubectl create secret generic postgres-credentials` | `kubernetes_secret.postgres_credentials` in `module.postgres` |
| 5.2 | `kubectl apply -f postgres.yaml` | `kubernetes_stateful_set.postgres` + `kubernetes_service.postgres` in `module.postgres` |
| 6.1 | `kubectl create secret generic valkey-credentials` | `kubernetes_secret.valkey_credentials` in `module.valkey` |
| 6.2 | `kubectl apply -f valkey.yaml` | `kubernetes_stateful_set.valkey` + `kubernetes_service.valkey` in `module.valkey` |
| 7 | `kubectl apply -f supabase-studio.yaml` | `kubernetes_deployment.supabase_studio` + `kubernetes_service.supabase_studio` in `module.supabase_studio` |
| 8.1 | `helm upgrade --install traefik traefik/traefik` | `helm_release.traefik` in `module.traefik_stack` |
| 8.2 | `kubectl apply -f cert-manager.yaml` | `helm_release.cert_manager` in `module.cert_manager` (Helm chart installs CRDs) |
| 8.3 | `kubectl apply -f letsencrypt.yaml` | `kubernetes_manifest.cluster_issuer_letsencrypt_prod` in `module.cert_manager` |
| 9 | `kubectl apply -f ingress-studio.yaml` | `kubernetes_manifest.ingress_studio` in `module.ingress` |
| 13 | `gcloud beta billing budgets create ...` | `google_billing_budget.meesell_dev_budget` in `module.billing_budget` |

---

## 13. What the Playbook Still Owns

These sections remain imperative bash. They are operator procedures, not infrastructure state, and Terraform has no legitimate role in them.

| Playbook section | Why it stays imperative |
|---|---|
| Section 1 (pre-flight) | Environment validation, not resource provisioning. Runs before every session. |
| Section 3.3 (kubeconfig copy) | Local file path is environment-specific; storing kubeconfig paths in state is fragile. |
| Section 5.3 / 6 backup commands | Backup is an operational action, not a state declaration. Backup CronJob manifest is committed separately. |
| Section 10 (secret rotation) | Secret rotation is a controlled operator action. Terraform's `ignore_changes` on secret data keeps Terraform out of the rotation loop intentionally. |
| Section 11 (daily ops checklist) | Health checks are observational, not state-changing. |
| Section 12 (incident runbooks) | Incident response is not declarative — it follows conditional logic based on symptoms observed in real time. |
| Section 14 acceptance gates | Manual verification ticks. Some acceptance items can be automated in CI eventually, but this is not Terraform's job. |
| Supporting infrastructure operational procedures (AR push workflow, GCS lifecycle management, CI SA key rotation, Secret Manager value rotation and access audit) | REQUIRES A PLAYBOOK ADDENDUM. These four operational areas are created by the new modules (`artifact_registry`, `asset_bucket`, `ci_identity`, `app_secrets`) but are NOT yet covered by any section of `INFRASTRUCTURE_PLAYBOOK.md`. This plan doc temporarily carries the operational procedure in Section 20 until a follow-up writing task extends the playbook. The playbook must NOT be modified in this dispatch. Recommended timing for the addendum: after Day 1 production VM is up and both Pass 1 and Pass 2 have been validated (see Q11). |

---

## 14. Rollback and Destroy Discipline

### The core risk: `terraform destroy` + `prevent_destroy`

`terraform destroy` would tear down the VM, all Kubernetes resources, and the PVCs. Data in Postgres and Valkey would be lost permanently. This directly violates the playbook's [DANGER] rules.

### Resources that MUST carry `lifecycle { prevent_destroy = true }`

| Resource | Reasoning |
|---|---|
| `google_compute_instance.meesell_dev` | Destroying the VM destroys everything. Requires founder-level approval per playbook. |
| `kubernetes_stateful_set.postgres` | Data lives in the PVC; removing the StatefulSet without the PVC delete grace is dangerous. |
| `kubernetes_persistent_volume_claim.data_postgres_0` | Direct data loss. Playbook says "ONLY with founder approval." |
| `kubernetes_stateful_set.valkey` | Valkey AOF is persistent state. |
| `kubernetes_persistent_volume_claim.data_valkey_0` | AOF loss. |
| `google_billing_budget.meesell_dev_budget` | Accidentally removing the budget removes cost protection. |

### Terraform plan interaction with [DANGER] rules

1. Any `terraform plan` showing a resource with `# forces replacement` on a `prevent_destroy` resource will FAIL the plan with an error. This is the correct behavior — the founder MUST manually remove the `prevent_destroy` flag (a code change requiring review) before a destroy can proceed. This replaces the "founder approval" step with a code-review gate.

2. The playbook's rollback commands (`gcloud compute instances delete meesell-dev --quiet`) are still valid as emergency procedures. They bypass Terraform state. If run directly, the resource is destroyed but Terraform state still shows it exists — the next `terraform apply` would try to recreate it. This is the correct behavior for disaster recovery: the founder runs the playbook's rollback, then runs `terraform apply` to rebuild.

3. For staging and prod: the `prevent_destroy` flag is set identically. Namespace-level resources in `prod` should additionally carry a `prod_guard` variable check:
   ```hcl
   lifecycle {
     prevent_destroy = true
   }
   ```
   With a `precondition` block: `condition = var.environment == "prod" ? false : true` is NOT used (that prevents all prod applies). Instead the flag stays always-on and removal requires a deliberate code change.

### Firewall IP drift (recurring operational concern)

When the founder's IP changes, `terraform apply -var="founder_ip=<NEW_IP>"` updates the `meesell-dev-k3s-api` firewall rule. This is cleaner than the playbook's manual update command because Terraform validates that `founder_ip` never equals `0.0.0.0` via a `validation` block in `module.firewall/variables.tf`.

---

## 15. Migration Paths

### (a) Fresh dev provision — this week

1. Complete pre-Terraform steps: create GCS state bucket, generate passwords, capture `FOUNDER_IP`.
2. Run `terraform init` inside `terraform/`.
3. Run Pass 1 apply (VM, firewall, billing budget). Confirm acceptance: `gcloud compute instances list` shows `meesell-dev RUNNING`, three firewall rules present, k3s-api scoped to `/32`.
4. Retrieve kubeconfig per playbook Section 3.3. Run `kubectl get nodes` — must show `Ready`.
5. Run Pass 2 apply (all Kubernetes workloads). Pass passwords via `-var` flags.
6. Run Section 14 acceptance gate. All 15 items must tick.
7. Commit `terraform/` directory (excluding `.terraform/`, `*.tfvars` with secrets, `*.tfstate*`) to the MeeSell git repo.

**Acceptance gates before next step:** Section 14 fully ticked.

### (b) Adding staging — Day 7

1. Verify `dev` has been running cleanly for the full development period.
2. Create `~/.meesell-secrets/staging-postgres-password` and `staging-valkey-password` (same openssl rand procedure).
3. Run:
   ```
   terraform apply \
     -var-file=environments/staging.tfvars \
     -var="postgres_password=$(cat ~/.meesell-secrets/staging-postgres-password)" \
     -var="valkey_password=$(cat ~/.meesell-secrets/staging-valkey-password)"
   ```
4. In `staging.tfvars`: `environment = "staging"`, `namespace` references staging workloads. The `namespaces_to_create` list already includes staging (created Day 1) — Terraform detects no-op for namespace creation, only the PostgreSQL and Valkey StatefulSets in the staging namespace are new resources.
5. Validate: `kubectl -n staging get pods` — all Running.
6. Deploy app images to staging namespace via kubectl/GitLab CI (outside Terraform scope — deploy-operator's domain).

**Changes in Terraform code:** Only the `.tfvars` file differs. No module changes. The `namespace` variable drives which Kubernetes namespace each resource is deployed into.

**Acceptance gates:** Staging namespace PostgreSQL and Valkey both healthy. A smoke-test API deployment in staging passes health check.

### (c) Adding prod — Week 2

**Prerequisites:** Staging has run for one full week. Section 14 (adapted for staging) fully ticked. Founder has explicitly approved prod namespace creation.

1. Create `environments/prod.tfvars` with `environment = "prod"`, tighter resource limits, and `namespaces_to_create = ["dev", "staging", "prod"]`.
2. Add `prevent_destroy = true` to prod-specific PVC and StatefulSet resources — this is already in place from Section 14.
3. Create `~/.meesell-secrets/prod-postgres-password` and `prod-valkey-password` with fresh passwords (do NOT reuse dev/staging passwords).
4. Run: `terraform apply -var-file=environments/prod.tfvars -var="postgres_password=..." -var="valkey_password=..."`
5. Validate: `kubectl -n prod get pods` — all Running.
6. DNS records for prod domain must point to Traefik LB IP.
7. Playbook [DANGER] rule: "NEVER push directly to prod without going through staging." This maps to: no CI pipeline deploys to prod namespace without a passing staging run first.

**Changes in Terraform code:** New `prod.tfvars`, prod namespace added to `namespaces_to_create`, no module code changes needed for MVP.

**Acceptance gates:** Same 15-point checklist from Section 14 applied to prod namespace. Cert-manager issues TLS certificate for prod domain. One full staging acceptance run must precede prod.

---

## 16. CI/CD Integration (sketch — not implemented now)

The `terraform/` directory layout must not preclude GitLab CI integration. This sketch shows the intended pipeline structure.

### GitLab CI structure

```yaml
# .gitlab-ci.yml (excerpt — future)
stages:
  - validate
  - plan
  - apply

terraform:validate:
  stage: validate
  script:
    - terraform init -backend=false
    - terraform validate
  rules:
    - if: $CI_MERGE_REQUEST_IID

terraform:plan:
  stage: plan
  script:
    - terraform init
    - terraform plan -var-file=environments/${ENVIRONMENT}.tfvars -out=tfplan
  artifacts:
    paths: [tfplan]
  rules:
    - if: $CI_MERGE_REQUEST_IID

terraform:apply:
  stage: apply
  script:
    - terraform apply tfplan
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  environment:
    name: $ENVIRONMENT
```

### GCP service account for CI

- Create a dedicated service account `meesell-tf-runner@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`.
- Grant: `roles/compute.instanceAdmin.v1`, `roles/iam.serviceAccountUser`, `roles/billing.viewer`, `roles/storage.admin` (for state bucket).
- The JSON key is stored as a GitLab CI variable `GOOGLE_CREDENTIALS` (masked, not protected, never committed).
- The state bucket IAM must also allow this service account.

### State locking in CI

GCS backend handles locking natively. Two simultaneous pipeline runs will queue — the second waits for the lock to release. No additional infrastructure needed.

### PR vs merge to main

- On PR: run `terraform plan` only. The plan output is posted as a merge request comment.
- On merge to main: run `terraform apply` with the saved plan artifact. Environment selection via a CI variable `ENVIRONMENT=dev` (or `staging`, `prod`) set per GitLab environment.

### Kubernetes provider in CI

The CI runner needs access to the K3s API server. Options: (a) allow CI runner IP in the `meesell-dev-k3s-api` firewall rule — adds operational maintenance, (b) deploy an in-cluster GitLab runner — preferred long-term approach. For now (MVP), CI only runs Terraform validate/plan; actual Kubernetes workload deployments are done by the `deploy-operator` agent from the founder's machine.

---

## 17. Decisions and Open Questions

### Resolved decisions (locked — no longer open)

| # | Topic | Resolution |
|---|---|---|
| Q1 | Domain | RESOLVED — `var.domain = ""` for first apply. Domain supplied later tonight. cert-manager + Ingress wiring deferred until domain is provided. |
| Q2 | State backend | RESOLVED — `backend "local" {}` now. Migration to GCS via `terraform init -migrate-state` deferred. Risk acknowledged (laptop disk failure before migration = state loss). |
| Q3 | Secret management approach | RESOLVED — Section 7 approach: `kubernetes_secret` + `lifecycle.ignore_changes` + sensitive var injected at first apply. Same `lifecycle.ignore_changes` discipline applied to Secret Manager entries (Section 20). |
| Q4 | Day 1 namespaces | RESOLVED — `dev` and `staging` created Day 1. `prod` deferred to Week 2 per playbook. |
| Q5 | Billing account ID | RESOLVED — `01620D-6785AB-0E4698` (OPEN, owns the $300 free credit). |
| Q6 | meesell-vm identity | RESOLVED — R&D workspace, out of scope. `meesell-vm` at 34.93.9.139 is sandbox only. Production scaffold creates a fresh `meesell-dev` VM in `mesell/infra/terraform/`. |
| Q7 | Supporting infrastructure strategy | RESOLVED — FULL ISOLATION. Production workspace creates its own Artifact Registry, GCS asset bucket, CI service account, WIF pool + provider, and Secret Manager entries. No sharing with R&D resources. |
| Q8 | Production workspace directory | RESOLVED — `mesell/infra/terraform/` (new directory, not yet created at time of this plan). |

### Open questions (non-blocking — work can proceed with defaults)

| # | Question | Default used | Blocks |
|---|---|---|---|
| Q9 | **GitLab repository path for WIF binding.** The WIF attribute condition restricts which GitLab project can impersonate the CI service account. Default is `techades/mesell` per workspace conventions. Founder to confirm the exact GitLab namespace/repo slug or override the default. | `"techades/mesell"` (via `var.gitlab_repository_path`) | NOT BLOCKING — the default is a workable value; easy to change in `dev.tfvars` before first apply. |
| Q10 | **GCS asset bucket name global uniqueness.** Default is `meesell-prod-assets`. GCS bucket names are globally unique across all GCP accounts. The default should be available; founder to confirm or override if there is a collision (unlikely). | `"meesell-prod-assets"` (via `var.gcs_asset_bucket_name`) | NOT BLOCKING — `terraform apply` will fail fast with a clear error if the name is taken; founder can then override. |
| Q11 | **Playbook addendum timing.** The four new modules (AR, GCS, CI identity, Secret Manager) need operational procedures added to `INFRASTRUCTURE_PLAYBOOK.md`. When does the founder want this writing task dispatched? Recommendation: after Day 1 production VM is up and both Pass 1 + Pass 2 have been validated successfully. | Operational procedures are carried in Section 20 of this plan doc in the interim. | NOT BLOCKING for scaffolding. Becomes BLOCKING before first production incident response. |

---

## 18. Next Step

This plan is approved per locked decisions D1–D9. The first scaffold deliverable creates `mesell/infra/terraform/` (a new directory that does not yet exist) with the following files — no `.tf` files touch live infrastructure, and no `terraform apply` runs until the founder reviews the plan output and approves.

**Files to create in the scaffold deliverable:**

1. `mesell/infra/terraform/versions.tf` — `required_providers` block with version pins for google, google-beta, kubernetes, helm, random, null, tls, time (Section 3).
2. `mesell/infra/terraform/providers.tf` — google/google-beta provider blocks with HARDCODED `project = "project-1f5cbf72-2820-4cdb-949"` and `region = "asia-south1"` (Section 19, Layer A). Kubernetes and Helm providers commented out, to be uncommented in Pass 2 after kubeconfig is retrieved.
3. `mesell/infra/terraform/backend.tf` — `backend "local" {}` (D2).
4. `mesell/infra/terraform/main.tf` — `locals` block + `data "google_project" "current"` + `null_resource.account_lock_guard` with `lifecycle.precondition` checking that the ADC project matches the locked constant (Section 19, Layer B + C).
5. `mesell/infra/terraform/variables.tf` — root variable declarations for all variables listed in Section 10. Does NOT include `project_id` or `billing_account_id` (locked constants — not variables).
6. `mesell/infra/terraform/apis.tf` — `google_project_service` resources for all eight APIs in `var.gcp_api_services` (Section 10). Applied first.
7. `mesell/infra/terraform/modules/vm/` — `main.tf`, `variables.tf`, `outputs.tf`. Compute instance with cloud-init startup script that installs K3s with `--disable=traefik --tls-san=$(curl -s ifconfig.me) --write-kubeconfig-mode=644 --node-name=meesell-dev-master` (Section 8). `prevent_destroy = true` on the instance.
8. `mesell/infra/terraform/modules/firewall/` — `main.tf`, `variables.tf`, `outputs.tf`. Three rules: `meesell-dev-http` (tcp:80), `meesell-dev-https` (tcp:443), `meesell-dev-k3s-api` (tcp:6443, source = `${var.founder_ip}/32`). Validation block: `founder_ip` must not be `"0.0.0.0"` or `""`.
9. `mesell/infra/terraform/modules/billing_budget/` — `main.tf`, `variables.tf`, `outputs.tf`. `google_billing_budget` resource with billing account `01620D-6785AB-0E4698` hardcoded, 50/75/90% thresholds, `prevent_destroy = true`.
10. `mesell/infra/terraform/modules/artifact_registry/` — `main.tf`, `variables.tf`, `outputs.tf`. Docker AR, asia-south1, cleanup policy (keep last 10 untagged, keep all tagged).
11. `mesell/infra/terraform/modules/asset_bucket/` — `main.tf`, `variables.tf`, `outputs.tf`. GCS bucket with uniform access, public access prevention, versioning, optional `temp/` 30-day lifecycle rule, `prevent_destroy = true`.
12. `mesell/infra/terraform/modules/ci_identity/` — `main.tf`, `variables.tf`, `outputs.tf`. CI SA + WIF pool (`gitlab-prod-pool`) + OIDC provider + IAM bindings (AR writer, GCS objectAdmin scoped to bucket, WIF impersonation binding).
13. `mesell/infra/terraform/modules/app_secrets/` — `main.tf`, `variables.tf`, `outputs.tf`. `google_secret_manager_secret` + initial placeholder version with `lifecycle.ignore_changes = [secret_data]` for each secret in `var.app_secret_ids`.
14. `mesell/Makefile.tf` — Layer D wrapper targets: `tf-init`, `tf-plan-pass1`, `tf-apply-pass1`, `tf-plan`, `tf-apply`. All targets call `scripts/tf-preflight.sh` first (Section 19, Layer D).
15. `mesell/scripts/tf-preflight.sh` — Layer E gate: checks `gcloud config get-value account` == `vaishnaviramoorthy@gmail.com`, `gcloud config get-value project` == `project-1f5cbf72-2820-4cdb-949`, `gcloud config get-value compute/zone` == `asia-south1-a`. Exits non-zero on any mismatch (Section 19, Layer E).
16. `mesell/infra/terraform/README.md` — bootstrap order (pre-flight → tf-preflight.sh → init → Pass 1 → kubeconfig retrieval → Secret Manager population → Pass 2), ADC setup instructions, account lock rationale.

**K8s modules deferred to second iteration:** `modules/namespaces/`, `modules/postgres/`, `modules/valkey/`, `modules/supabase_studio/`, `modules/traefik_stack/`, `modules/cert_manager/`, `modules/ingress/`. These ship after Pass 1 is applied, K3s is confirmed running, and kubeconfig is retrieved.

**Approval gate before scaffold:** Founder reviews this updated plan doc and confirms. Then scaffold is created. Then `make tf-init && make tf-plan-pass1 FOUNDER_IP=<current_ip>` is run and the plan output is shown. No `terraform apply` until the founder reviews the plan output and approves in that session.

---

## 19. Account Lock and Free-Tier Discipline

The production workspace operates against GCP account `vaishnaviramoorthy@gmail.com`, project `project-1f5cbf72-2820-4cdb-949`, and billing account `01620D-6785AB-0E4698`. The $300 free credit attached to this billing account is the only available compute budget. An accidental apply against a different project or account could create billable resources outside the credit pool. The six-layer lock strategy below makes such an accident require multiple deliberate bypasses.

### Layer A — Project hardcoded in providers.tf (not a variable)

`project_id` is NOT declared as a `variable` in `variables.tf`. It is a hardcoded literal in `providers.tf`:

```hcl
# mesell/infra/terraform/providers.tf
provider "google" {
  project = "project-1f5cbf72-2820-4cdb-949"
  region  = "asia-south1"
}

provider "google-beta" {
  project = "project-1f5cbf72-2820-4cdb-949"
  region  = "asia-south1"
}
```

A PR diff that changes these strings is immediately visible in code review. There is no `-var="project_id=..."` flag that can silently redirect an apply to a different project.

### Layer B — data.google_project confirms the authenticated project at plan time

```hcl
# mesell/infra/terraform/main.tf
data "google_project" "current" {}

locals {
  expected_project = "project-1f5cbf72-2820-4cdb-949"
}
```

The `data "google_project" "current"` block resolves at plan time using the ADC identity. Its `project_id` attribute is used in Layer C.

### Layer C — null_resource precondition fails the plan if project drifts

```hcl
# mesell/infra/terraform/main.tf (continued)
resource "null_resource" "account_lock_guard" {
  lifecycle {
    precondition {
      condition     = data.google_project.current.project_id == local.expected_project
      error_message = "ACCOUNT LOCK VIOLATION: ADC project '${data.google_project.current.project_id}' does not match the locked project '${local.expected_project}'. Run tf-preflight.sh and ensure gcloud is authenticated as vaishnaviramoorthy@gmail.com."
    }
  }
}
```

If `gcloud auth application-default login` was run as the wrong account and the ADC project resolves to anything other than `project-1f5cbf72-2820-4cdb-949`, `terraform plan` fails with the error message above before any resource diffs are computed. No apply is possible.

### Layer D — Makefile.tf wraps every tf command (forces preflight)

```makefile
# mesell/Makefile.tf
SHELL    := /bin/bash
TF_DIR   := mesell/infra/terraform
PREFLIGHT := mesell/scripts/tf-preflight.sh

.PHONY: tf-init tf-plan-pass1 tf-apply-pass1 tf-plan tf-apply

tf-init:
	@bash $(PREFLIGHT)
	cd $(TF_DIR) && terraform init

tf-plan-pass1: tf-init
	@bash $(PREFLIGHT)
	cd $(TF_DIR) && terraform plan \
	  -var-file=environments/dev.tfvars \
	  -var="founder_ip=$(FOUNDER_IP)" \
	  -target=google_project_service.apis \
	  -target=module.ci_identity \
	  -target=module.artifact_registry \
	  -target=module.asset_bucket \
	  -target=module.app_secrets \
	  -target=module.vm \
	  -target=module.firewall \
	  -target=module.billing_budget \
	  -out=tfplan-pass1

tf-apply-pass1:
	@bash $(PREFLIGHT)
	cd $(TF_DIR) && terraform apply tfplan-pass1

tf-plan:
	@bash $(PREFLIGHT)
	cd $(TF_DIR) && terraform plan \
	  -var-file=environments/dev.tfvars \
	  -var="founder_ip=$(FOUNDER_IP)" \
	  -var="kubeconfig_path=$(KUBECONFIG_PATH)" \
	  -var="postgres_password=$(shell cat ~/.meesell-secrets/dev-postgres-password)" \
	  -var="valkey_password=$(shell cat ~/.meesell-secrets/dev-valkey-password)" \
	  -out=tfplan

tf-apply:
	@bash $(PREFLIGHT)
	cd $(TF_DIR) && terraform apply tfplan
```

Running `terraform` directly from `mesell/infra/terraform/` bypasses the Makefile wrapper but still hits Layers A, B, and C. The Makefile is a convenience gate, not a security boundary.

### Layer E — tf-preflight.sh exits non-zero on identity mismatch

```bash
#!/usr/bin/env bash
# mesell/scripts/tf-preflight.sh
set -euo pipefail

EXPECTED_ACCOUNT="vaishnaviramoorthy@gmail.com"
EXPECTED_PROJECT="project-1f5cbf72-2820-4cdb-949"
EXPECTED_ZONE="asia-south1-a"

check() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "PREFLIGHT FAIL [$label]: expected '$expected', got '$actual'" >&2
    echo "Fix: gcloud config set $label $expected" >&2
    exit 1
  fi
  echo "PREFLIGHT OK  [$label]: $actual"
}

check "account"      "$EXPECTED_ACCOUNT" "$(gcloud config get-value account 2>/dev/null)"
check "project"      "$EXPECTED_PROJECT" "$(gcloud config get-value project 2>/dev/null)"
check "compute/zone" "$EXPECTED_ZONE"    "$(gcloud config get-value compute/zone 2>/dev/null)"

echo "Preflight passed. ADC identity confirmed."
```

### Layer F — Billing budget + free-tier exit review point

The `module.billing_budget` resource creates a GCP billing budget against account `01620D-6785AB-0E4698` at $300 total with alerts at 50%, 75%, and 90% consumed. Email alerts go to the account email `vaishnaviramoorthy@gmail.com`.

**Free-tier exit review:** When the billing alert at 50% ($150) fires, the founder reviews GCP Console → Billing → Credits to confirm the free credit is still the primary source. If the credit is exhausted, production infra must be sized down or migrated before cost continues. At 90% ($270), all non-essential workloads are paused per Playbook Section 13.

**Lock removal procedure (if intentional project migration is ever needed):**
1. Remove the `precondition` block in `null_resource.account_lock_guard` in a PR.
2. Update `providers.tf` project and region strings in the same PR.
3. Update `expected_*` constants in `tf-preflight.sh`.
4. Have the founder review and merge the PR.
5. Re-run `make tf-init` (re-initialises providers for new project) then `make tf-plan`.
The three-file change in a single PR ensures no undetected project migration.

---

## 20. Supporting Infrastructure — AR, GCS, CI Identity, Secret Manager

This section details the four modules added by D8 (Full Isolation strategy). These modules create GCP infrastructure that the playbook does not currently cover. Operational procedures are carried here until a follow-up playbook addendum is written (Q11).

### 20.1 Module: artifact_registry

**Purpose:** A production Docker Artifact Registry repository isolated from the R&D workspace's `meesell-images` repository. GitLab CI pushes built images here; K3s pulls from here.

**GCP resource created:** `google_artifact_registry_repository.meesell_prod_images`
- Repository ID: `meesell-prod-images`
- Location: `asia-south1`
- Format: `DOCKER`
- Cleanup policy: keep all tagged images; delete untagged images older than 7 days; keep the most recent 10 untagged images regardless of age.

**IAM bindings (in `module.ci_identity`):**
- `roles/artifactregistry.writer` granted to `meesell-prod-ci` service account — allows `docker push` from GitLab CI.
- `roles/artifactregistry.reader` granted to the VM's default compute service account (or a workload SA) — allows K3s nodes to pull images.

**Key configuration choices:**
- `location = "asia-south1"` — same region as the VM minimises pull latency and egress cost.
- Cleanup policy on untagged images prevents unbounded registry growth from CI branch builds.

**Playbook gap (REQUIRES ADDENDUM):** The playbook has no procedure for:
- Authenticating Docker to the registry before first push (`gcloud auth configure-docker asia-south1-docker.pkg.dev`).
- Tagging and pushing a built image.
- Rotating CI SA credentials (covered by WIF — no key rotation needed; WIF tokens are short-lived).
- Manually cleaning up images if the cleanup policy misses something.

### 20.2 Module: asset_bucket

**Purpose:** A production GCS bucket for application file storage — product images, exports (CSV/ZIP), and temporary uploads. Isolated from the R&D bucket `project-1f5cbf72-2820-4cdb-949-meesell-assets`.

**GCP resource created:** `google_storage_bucket.meesell_prod_assets`
- Bucket name: `meesell-prod-assets` (globally unique — see Q10)
- Location: `ASIA-SOUTH1`
- Storage class: `STANDARD`
- Uniform bucket-level access: `true`
- Public access prevention: `enforced`
- Versioning: enabled
- Lifecycle rule (optional, enabled by default): delete objects under prefix `temp/` after 30 days. This covers temporary upload staging areas.

**IAM bindings (in `module.ci_identity`):**
- `roles/storage.objectAdmin` on this bucket granted to `meesell-prod-ci` — allows CI to upload built artifacts if needed.
- `roles/storage.objectAdmin` on this bucket granted to the workload SA used by FastAPI pods — allows the app to upload and read product images. (This binding is in a `workload_identity` module or the root `main.tf` once the VM's workload SA is defined.)

**Key configuration choices:**
- `public_access_prevention = "enforced"` — images are served via signed URLs from the FastAPI backend, not via public bucket access. This is required by the app's storage service (`backend/app/services/storage.py`).
- `bucket_force_destroy = false` inside the module — Terraform will refuse to destroy the bucket if it contains objects. This is an additional guard on top of `prevent_destroy = true` on the resource.
- The `temp/` lifecycle rule maps to the `GCS_BUCKET/temp/` path the image processor writes to before background processing.

**Playbook gap (REQUIRES ADDENDUM):** No procedure for:
- Generating signed URLs for object access.
- Manually reviewing lifecycle rule execution logs.
- Restoring a versioned object after accidental deletion.

### 20.3 Module: ci_identity

**Purpose:** The complete GitLab CI pipeline identity — a service account and a Workload Identity Federation pool + OIDC provider that allows GitLab CI jobs to obtain short-lived GCP credentials without a stored JSON key.

**GCP resources created:**

| Resource | ID/Name |
|---|---|
| `google_service_account.meesell_prod_ci` | `meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` |
| `google_iam_workload_identity_pool.gitlab_prod` | pool ID: `gitlab-prod-pool` |
| `google_iam_workload_identity_pool_provider.gitlab_prod` | provider ID: `gitlab-oidc` |
| `google_service_account_iam_member` (WIF impersonation) | principal: `principalSet://iam.googleapis.com/projects/<project_number>/locations/global/workloadIdentityPools/gitlab-prod-pool/attribute.repository/techades/mesell` |
| `google_project_iam_member` (AR writer) | `roles/artifactregistry.writer` on CI SA |
| `google_storage_bucket_iam_member` (GCS admin) | `roles/storage.objectAdmin` on `meesell-prod-assets`, bound to CI SA |

**Workload Identity Federation — GitLab-specific attribute mapping:**

```hcl
attribute_mapping = {
  "google.subject"              = "assertion.sub"
  "attribute.aud"               = "assertion.aud"
  "attribute.repository"        = "assertion.project_path"
  "attribute.repository_path"   = "assertion.project_path"
  "attribute.ref_path"          = "assertion.ref_path"
  "attribute.namespace_path"    = "assertion.namespace_path"
}

attribute_condition = "attribute.repository == \"${var.gitlab_repository_path}\""
```

The `attribute_condition` restricts impersonation to CI jobs running inside the `techades/mesell` repository (or whatever `var.gitlab_repository_path` is set to — see Q9). No other GitLab repository can impersonate the CI SA even if they have the WIF provider resource name.

**GitLab CI variable configuration (operator manual step, not Terraform):**
```yaml
# In GitLab project CI/CD Variables (masked, protected):
WORKLOAD_IDENTITY_PROVIDER: "projects/<project_number>/locations/global/workloadIdentityPools/gitlab-prod-pool/providers/gitlab-oidc"
SERVICE_ACCOUNT_EMAIL:       "meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com"
```

Both values are emitted as Terraform outputs `wif_provider_name` and `ci_sa_email` (Section 10 outputs). The operator copies them to GitLab CI variables after Pass 1 is applied.

**GitLab CI authentication snippet (for `.gitlab-ci.yml`):**
```yaml
id_tokens:
  GOOGLE_ID_TOKEN:
    aud: https://iam.googleapis.com/projects/<project_number>/locations/global/workloadIdentityPools/gitlab-prod-pool/providers/gitlab-oidc

before_script:
  - echo "$GOOGLE_ID_TOKEN" > /tmp/gcp-token.json
  - gcloud iam workload-identity-pools create-cred-config \
      "$WORKLOAD_IDENTITY_PROVIDER" \
      --service-account="$SERVICE_ACCOUNT_EMAIL" \
      --output-file=/tmp/gcp-creds.json \
      --credential-source-file=/tmp/gcp-token.json
  - export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-creds.json
  - gcloud auth login --cred-file=/tmp/gcp-creds.json
  - gcloud auth configure-docker asia-south1-docker.pkg.dev
```

**Playbook gap (REQUIRES ADDENDUM):** No procedure for:
- Setting the GitLab CI variables after Pass 1.
- Testing the WIF flow (`gcloud auth print-identity-token` from a CI job).
- Revoking CI SA access (remove the WIF IAM binding in Terraform and apply).

### 20.4 Module: app_secrets

**Purpose:** Create the Secret Manager containers for the five production app-level secrets. The containers exist in GCP after Pass 1. The actual secret values are never stored in Terraform state — they are populated manually by the founder after Pass 1.

**GCP resources created (one per entry in `var.app_secret_ids`):**

| Secret ID | Maps to `backend/.env.example` variable |
|---|---|
| `gemini-api-key` | `GEMINI_API_KEY` |
| `msg91-auth-key` | `MSG91_AUTH_KEY` |
| `jwt-secret` | `JWT_SECRET` |
| `razorpay-key-id` | `RAZORPAY_KEY_ID` |
| `razorpay-key-secret` | `RAZORPAY_KEY_SECRET` |

Each secret is created as:
```hcl
resource "google_secret_manager_secret" "app_secrets" {
  for_each  = toset(var.secret_ids)
  secret_id = each.key
  labels    = { managed_by = "terraform", env = var.namespace_label }
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "app_secrets_placeholder" {
  for_each    = google_secret_manager_secret.app_secrets
  secret      = each.value.id
  secret_data = "PLACEHOLDER_SET_MANUALLY"
  lifecycle {
    ignore_changes = [secret_data]
  }
}
```

The `ignore_changes = [secret_data]` means Terraform will never overwrite the placeholder after the founder populates the real value. The placeholder itself is not sensitive — it is just a known string that signals "this version has not been populated yet."

**Founder-side population procedure (run after Pass 1, before Pass 2):**
```bash
# Set each secret. Source the real values from secure storage (1Password, .env file on laptop, etc).
# NEVER commit these values. NEVER put them in terminal history where possible — use files.

gcloud secrets versions add gemini-api-key \
  --account=vaishnaviramoorthy@gmail.com \
  --data-file=- <<< "$GEMINI_KEY"

gcloud secrets versions add msg91-auth-key \
  --account=vaishnaviramoorthy@gmail.com \
  --data-file=- <<< "$MSG91_AUTH_KEY"

gcloud secrets versions add jwt-secret \
  --account=vaishnaviramoorthy@gmail.com \
  --data-file=- <<< "$JWT_SECRET"

gcloud secrets versions add razorpay-key-id \
  --account=vaishnaviramoorthy@gmail.com \
  --data-file=- <<< "$RAZORPAY_KEY_ID"

gcloud secrets versions add razorpay-key-secret \
  --account=vaishnaviramoorthy@gmail.com \
  --data-file=- <<< "$RAZORPAY_KEY_SECRET"
```

**Verification (check all five are populated):**
```bash
for secret in gemini-api-key msg91-auth-key jwt-secret razorpay-key-id razorpay-key-secret; do
  latest=$(gcloud secrets versions list "$secret" \
    --account=vaishnaviramoorthy@gmail.com \
    --filter="state=ENABLED" \
    --format="value(name)" | tail -1)
  value=$(gcloud secrets versions access "$latest" \
    --secret="$secret" \
    --account=vaishnaviramoorthy@gmail.com)
  if [[ "$value" == "PLACEHOLDER_SET_MANUALLY" ]]; then
    echo "WARNING: $secret still has placeholder value"
  else
    echo "OK: $secret is populated (value hidden)"
  fi
done
```

Do not proceed to Pass 2 until all five secrets show OK (non-placeholder).

**Playbook gap (REQUIRES ADDENDUM):** No procedure for:
- Secret rotation (adding a new version and updating the app to read the latest version).
- Granting app pod access (WIF or SA-based `secretmanager.secretAccessor` binding — needed for pods to read secrets at runtime; this IAM binding is outside the scope of the `app_secrets` module itself and should be in a `workload_identity` or `app_secrets_iam` sub-module in the K8s pass).
- Auditing who accessed a secret (`gcloud secrets versions list` + Cloud Audit Logs).

---

## Appendix: Playbook Rules That Were Difficult to Translate

| Playbook rule | Terraform translation difficulty | Resolution taken |
|---|---|---|
| [DANGER] NEVER run `gcloud ... delete` without founder approval | `lifecycle { prevent_destroy = true }` provides a code-change gate | Any `terraform destroy` or plan showing resource replacement on guarded resources fails. Founder must edit code to override — stronger than "ask for approval." |
| [SAFE] ALWAYS show diff before applying | `terraform plan` is the equivalent | The plan document must be shown to founder before every apply. The CI sketch enforces plan-on-PR, apply-on-merge. |
| [SAFE] ALWAYS use `--dry-run=client -o yaml` first, then apply | `terraform plan` subsumes this. The kubernetes provider uses server-side validation internally. | No clean Terraform equivalent of the YAML preview, but `terraform plan` output shows every resource attribute. |
| Section 10 rotation — secret rotation stays imperative | `lifecycle.ignore_changes = [data]` means Terraform will not overwrite the secret after initial creation. The rotation procedure in Section 10 stays fully manual and continues to work. | Terraform is explicitly kept out of the rotation loop. Trade-off: state drifts from actual secret value after rotation. This is acceptable and documented. |
| [DANGER] NEVER open firewall port 6443 to 0.0.0.0/0 | Enforced by `validation` block in `module/firewall/variables.tf` on `var.founder_ip` | Validation rule: `condition = var.founder_ip != "0.0.0.0" && var.founder_ip != ""`. Terraform plan fails if someone passes the wrong value. |
| K3s `--tls-san=$(curl -s ifconfig.me)` | The command works correctly in cloud-init startup_script (runs on VM), not in local-exec (would get laptop IP). | Cloud-init approach chosen. The startup_script template uses the exact same curl command. Since cloud-init runs on the VM, ifconfig.me returns the VM's own external IP — correct. |
| Section 14 acceptance gate (15 manual ticks) | Not automatable in Terraform | Acceptance gate remains a manual checklist. The Terraform `output` block surfaces the VM IP, PG host, and Valkey host to make the checklist faster to work through, but the ticks are human-verified. |
