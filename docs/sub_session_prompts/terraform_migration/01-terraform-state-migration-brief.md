# Terraform State Migration & Phase D Codification — Dispatch Brief

**Agent:** `meesell-infra-builder`
**Session name:** `mesell-terraform-migration-session-1`
**Task type:** Infrastructure — state migration + Terraform codification of manual changes
**Outputs:**
- `infra/terraform/backend.tf` — updated to GCS backend
- `infra/terraform/modules/cloudbuild_permissions/` (new) — Cloud Build SA IAM bindings
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` — refreshed SSOT (stale since 2026-06-07)
- `docs/status/STATUS_INFRA.md` — updated

---

## PROMPT

```
You are meesell-infra-builder. You are operating on the MeeSell project.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch meesell-* agents. NEVER dispatch nexus:level-*, general-purpose, or Explore.

---

MISSION: Terraform State Migration + Phase D Codification.

Phase D deployed the V1 backend by granting GCP IAM permissions manually (gcloud iam commands
outside Terraform). Terraform state also lives on the founder's laptop — a single point of
failure. Your job this session:

  1. Migrate Terraform state from local file to GCS bucket (meesell-tfstate)
  2. Codify the Phase D manual GCP IAM changes into Terraform
  3. Codify the K3s AR auth cron (registries.yaml) in Terraform or document it
  4. Refresh docs/INFRASTRUCTURE_ARCHITECTURE.md to reflect actual Phase D live state

Principle going forward: ALL GCP infrastructure changes go through Terraform. No direct gcloud
iam commands on tracked resources.

---

BEFORE STARTING — read these files in order:
1. .claude/agent-memory/meesell-infra-builder/MEMORY.md — your own memory
2. docs/sub_session_prompts/terraform_migration/01-terraform-state-migration-brief.md — FULL READ
   (complete task specification — stop conditions, exact commands, success criteria all in here)
3. infra/terraform/backend.tf — migration procedure already documented, you will execute it
4. infra/terraform/terraform.tfstate — current state (understand what is already managed)
5. infra/terraform/main.tf — module structure and patterns
6. infra/terraform/modules/ci_identity/main.tf — module pattern to follow for new module
7. docs/INFRASTRUCTURE_ARCHITECTURE.md — full read (identify stale sections)
8. docs/status/STATUS_INFRA.md — Phase D D-flags

---

STEP 1 — Pre-flight (run ALL checks before touching anything):
  gcloud auth application-default print-access-token 2>&1 | head -3  (must succeed)
  gcloud config get account  (must be vaishnaviramoorthy@gmail.com)
  cd infra/terraform && terraform plan -var-file=environments/dev.tfvars
  (must show "No changes" — if drift found STOP and report to founder)
  gcloud storage buckets describe gs://meesell-tfstate --project=project-1f5cbf72-2820-4cdb-949
  (check if bucket already exists before creating)

STEP 2 — Create GCS bucket if not exists:
  gcloud storage buckets create gs://meesell-tfstate \
    --project=project-1f5cbf72-2820-4cdb-949 \
    --location=ASIA-SOUTH1 \
    --uniform-bucket-level-access
  gcloud storage buckets update gs://meesell-tfstate --versioning

STEP 3 — Update backend.tf to GCS, migrate state:
  Edit infra/terraform/backend.tf: replace backend "local" block with:
    backend "gcs" {
      bucket = "meesell-tfstate"
      prefix = "terraform/state"
    }
  Run: terraform init -migrate-state
  Confirm: gcloud storage ls gs://meesell-tfstate/terraform/state/  (must show default.tfstate)
  DO NOT delete local terraform.tfstate until GCS copy confirmed.

STEP 4 — Codify Cloud Build SA permissions (D-API-5):
  Create infra/terraform/modules/cloudbuild_permissions/main.tf with:
  - google_storage_bucket_iam_member: roles/storage.admin on
    gs://project-1f5cbf72-2820-4cdb-949_cloudbuild
    → member: 888244156264-compute@developer.gserviceaccount.com
  - google_artifact_registry_repository_iam_member: roles/artifactregistry.writer on
    meesell-prod-images repo
    → member: 888244156264-compute@developer.gserviceaccount.com
  Add module invocation to infra/terraform/main.tf.
  Run: terraform plan -target=module.cloudbuild_permissions -var-file=environments/dev.tfvars
  Run: terraform apply -target=module.cloudbuild_permissions -var-file=environments/dev.tfvars

STEP 5 — Codify K3s AR auth (D-API-6):
  The VM has /etc/rancher/k3s/registries.yaml + /usr/local/bin/refresh-ar-token.sh + cron
  (45-min token refresh). Either:
    Option A (preferred): Add null_resource remote-exec provisioner in vm module to ensure
      registries.yaml + cron are reproducible on re-provision
    Option B (fallback): Add detailed manual procedure to INFRASTRUCTURE_ARCHITECTURE.md §11
  Choose the option you can complete reliably. Document your choice in STATUS_INFRA.md.

STEP 6 — Full plan verify:
  terraform plan -var-file=environments/dev.tfvars
  Must show "No changes" or only expected additions from new modules.

STEP 7 — Refresh docs/INFRASTRUCTURE_ARCHITECTURE.md:
  Update these stale sections to reflect Phase D actual state:
  - VM workloads: api 2/2, worker 2/2 Running in dev namespace
  - Secret Manager: all 10 containers now have ≥1 version
  - CI identity: Cloud Build SA quirk (Compute Engine default SA, not Cloud Build SA)
  - New: K3s AR auth section (registries.yaml + cron)
  - New: Terraform discipline principle at top
  Do NOT rewrite accurate sections.

---

STOP CONDITIONS — escalate to founder before proceeding:
  - terraform plan shows unexpected destroy or drift before migration
  - gs://meesell-tfstate already exists with different project state
  - ADC identity is not vaishnaviramoorthy@gmail.com
  - terraform init -migrate-state errors

---

SCOPE OUT:
  - .github/workflows/ci.yml — CI/CD session handles this
  - infra/terraform/modules/ci_identity/ GitHub WIF changes — CI/CD session handles this
  - K8s application resources (Deployments, Services, Secrets) — NOT in Terraform scope
  - Staging or prod namespace — dev only
  - DO NOT run terraform destroy on any resource
  - DO NOT commit terraform.tfstate or terraform.tfstate.backup to git

---

SUCCESS CRITERIA:
  - gcloud storage ls gs://meesell-tfstate/terraform/state/default.tfstate → exists
  - backend.tf uses GCS backend
  - terraform plan shows no unexpected diff
  - Cloud Build SA perms in Terraform (module.cloudbuild_permissions applied)
  - INFRASTRUCTURE_ARCHITECTURE.md Phase D sections updated
  - STATUS_INFRA.md updated with === UPDATE === block
  - .claude/agent-memory/meesell-infra-builder/MEMORY.md updated

Full task specification: docs/sub_session_prompts/terraform_migration/01-terraform-state-migration-brief.md
```

---

## PROJECT BOUNDARY

You are working on project "mesell" at `/Users/mugunthansrinivasan/Project/mesell`.
DO NOT read, write, or reference files outside that path.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch `meesell-*` agents. NEVER dispatch `nexus:level-*` or `general-purpose`.

---

## MISSION

Phase D deployed the V1 backend by applying K8s manifests directly (`kubectl apply`) and granting
GCP IAM permissions manually (`gcloud iam ...`). These manual changes are now **outside Terraform**
— there is no source of truth for them.

This session establishes the principle: **all GCP infrastructure changes go through Terraform only**.
It does this in two parts:

1. **Migrate Terraform state from local to GCS** — enables future CI-managed `terraform plan` checks
2. **Codify Phase D manual GCP changes in Terraform** — Cloud Build SA permissions
3. **Refresh `docs/INFRASTRUCTURE_ARCHITECTURE.md`** — SSOT is stale (last updated 2026-06-07)

> **Scope boundary**: K8s application deployments (api, worker, frontend Deployments/Services/ConfigMaps/Secrets)
> are managed by K8s manifests in `k8s/` + CI/CD pipeline — NOT by Terraform. Do NOT add K8s
> application resources to Terraform. Terraform owns GCP-layer resources only.

---

## CRITICAL CONTEXT

### 1. Terraform state is LOCAL — this is the #1 risk
State file: `infra/terraform/terraform.tfstate` on founder's laptop.
If the laptop is lost or the file is deleted, all Terraform state is gone — manual reconciliation
of 49+ resources.

The migration procedure is already documented in `infra/terraform/backend.tf` comments:
```
1. Create GCS bucket:  gs://meesell-tfstate  (ASIA-SOUTH1, uniform-bucket-level-access)
2. Replace backend block with: backend "gcs" { bucket = "meesell-tfstate"; prefix = "terraform/state" }
3. Run: terraform init -migrate-state
4. Verify state in GCS before deleting local .tfstate
```

**This session EXECUTES that migration.**

⚠️ Pre-check: verify `gs://meesell-tfstate` does NOT already exist before creating.
⚠️ ADC check: ensure `gcloud auth application-default login` is active as `vaishnaviramoorthy@gmail.com`
   before any `terraform` or `gcloud` command.

### 2. Phase D manual GCP changes not in Terraform (D-API-5)

Phase D discovered: Cloud Build in `project-1f5cbf72-2820-4cdb-949` runs as the
**Compute Engine default SA**, NOT the standard Cloud Build SA.

The following IAM bindings were granted **manually via gcloud** during Phase D — they are NOT
in Terraform and must be codified:

| Resource | IAM role | Member |
|----------|----------|--------|
| GCS bucket `project-1f5cbf72-2820-4cdb-949_cloudbuild` | `roles/storage.admin` | `888244156264-compute@developer.gserviceaccount.com` |
| Artifact Registry repo `meesell-prod-images` | `roles/artifactregistry.writer` | `888244156264-compute@developer.gserviceaccount.com` |

Add these as Terraform resources. The recommended location:
`infra/terraform/modules/cloudbuild_permissions/main.tf` (new module) OR inline in
`infra/terraform/main.tf` as root-level resources — your call, document the choice.

### 3. K3s Artifact Registry auth (D-API-6) — codify the cron, not replace it

Phase D set up `/etc/rancher/k3s/registries.yaml` on the VM + a cron job to refresh the
metadata server token every 45 minutes. This is the working dev-environment approach.

For this session: **codify it in Terraform** — use a `null_resource` with `remote-exec` provisioner
(or a startup script update) to ensure `registries.yaml` and the cron are idempotent and
reproducible. Do NOT replace with `kubelet-credential-providers` yet — that is a staging/prod upgrade.

If the provisioner approach is complex, document the manual steps clearly in
`docs/INFRASTRUCTURE_ARCHITECTURE.md` §11 (new section: AR node authentication) so any
re-provision can reproduce it. Either codify or document — do not leave it undocumented.

### 4. INFRASTRUCTURE_ARCHITECTURE.md is stale (Phase D-pre)

`docs/INFRASTRUCTURE_ARCHITECTURE.md` was last updated 2026-06-07. It predates Phase D and
does not reflect:
- API + worker pods running in `dev` namespace
- `backend-secrets` K8s Secret (20 keys)
- `meesell-config` ConfigMap
- All 10 GCP SM secrets now having ≥1 version
- Cloud Build SA quirk
- `registries.yaml` + cron on VM
- CPU request adjustments (api: 200m, worker: 250m)
- Alembic migration head: `f31c75438e61`

**Update the relevant sections** to reflect actual live state. Do NOT rewrite sections that are
still accurate. Focus on: VM workloads section, Secret Manager section, CI identity section.

### 5. What is NOT in scope for this session

- `.github/workflows/ci.yml` — handled by CI/CD session (Dispatch 1)
- `infra/terraform/modules/ci_identity/` GitHub WIF changes — handled by CI/CD session
- K8s manifest changes — not your concern
- Staging or prod namespace — dev only
- Any frontend work

---

## WHAT TO READ BEFORE STARTING

Read in order — do not start working until all are read:

1. `.claude/agent-memory/meesell-infra-builder/MEMORY.md` — your own memory
2. `infra/terraform/backend.tf` — migration procedure (already documented, execute it)
3. `infra/terraform/terraform.tfstate` — current state (to understand what is managed)
4. `infra/terraform/main.tf` — module structure
5. `infra/terraform/modules/ci_identity/main.tf` — existing CI module (to understand pattern for new module)
6. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — full read (identify stale sections)
7. `docs/status/STATUS_INFRA.md` — current state including Phase D D-flags
8. `k8s/` — all manifests (to understand what is K8s-managed vs GCP-managed)

---

## SESSION ACTION PLAN

### Step 1 — Pre-flight checks
```bash
# Verify ADC identity
gcloud auth application-default print-access-token 2>&1 | head -5
gcloud config get account  # must be vaishnaviramoorthy@gmail.com

# Verify Terraform state is clean before migrating
cd infra/terraform && terraform plan -var-file=environments/dev.tfvars
# Must show: "No changes" — if drift exists, STOP and report to founder before migrating

# Check if GCS bucket already exists
gcloud storage buckets describe gs://meesell-tfstate --project=project-1f5cbf72-2820-4cdb-949 2>&1
```

### Step 2 — Create GCS bucket (if not exists)
```bash
gcloud storage buckets create gs://meesell-tfstate \
  --project=project-1f5cbf72-2820-4cdb-949 \
  --location=ASIA-SOUTH1 \
  --uniform-bucket-level-access
```
Enable versioning for state protection:
```bash
gcloud storage buckets update gs://meesell-tfstate --versioning
```

### Step 3 — Update backend.tf
Replace the `backend "local"` block with `backend "gcs"` as documented in `backend.tf` comments.
Then run:
```bash
cd infra/terraform && terraform init -migrate-state -backend-config='bucket=meesell-tfstate' \
  -backend-config='prefix=terraform/state'
```
Confirm state was copied to GCS:
```bash
gcloud storage ls gs://meesell-tfstate/terraform/state/
# Must show: default.tfstate
```

### Step 4 — Codify Cloud Build SA permissions in Terraform
Create `infra/terraform/modules/cloudbuild_permissions/main.tf` with:
- `google_storage_bucket_iam_member` for the `_cloudbuild` bucket
- `google_artifact_registry_repository_iam_member` for `meesell-prod-images`

Both targeting `888244156264-compute@developer.gserviceaccount.com`.

Add module invocation in `infra/terraform/main.tf`.

Run plan + apply to import the existing bindings into Terraform state:
```bash
terraform plan -var-file=environments/dev.tfvars -target=module.cloudbuild_permissions
terraform apply -var-file=environments/dev.tfvars -target=module.cloudbuild_permissions
```

### Step 5 — Codify or document K3s AR auth cron
Option A (preferred): Add a `null_resource` with `remote-exec` provisioner to the `vm` module
or as a root-level resource that SSHes to `meesell-dev` and ensures `/etc/rancher/k3s/registries.yaml`
+ `/usr/local/bin/refresh-ar-token.sh` + crontab entry are present. Use `triggers = { always_run = timestamp() }` pattern.

Option B (fallback): Document the exact setup procedure in `docs/INFRASTRUCTURE_ARCHITECTURE.md`
as a reproducible manual procedure.

### Step 6 — Run full terraform plan to verify clean state
```bash
cd infra/terraform && terraform plan -var-file=environments/dev.tfvars
# Must show: "No changes" or only the new Cloud Build SA resources
```

### Step 7 — Update docs/INFRASTRUCTURE_ARCHITECTURE.md
Refresh the stale sections listed in §4 above. Add a new principle at the top:

> **Infrastructure discipline (post Phase D):** All GCP-layer infrastructure changes
> MUST go through Terraform. Direct `gcloud iam` or `gcloud compute` modifications are
> forbidden for tracked resources. K8s application deployments are managed by CI/CD pipeline.

---

## SUCCESS CRITERIA

| Check | Pass condition |
|-------|---------------|
| State in GCS | `gcloud storage ls gs://meesell-tfstate/terraform/state/default.tfstate` → exists |
| Local state not used | `infra/terraform/terraform.tfstate` — still present as backup but `backend.tf` no longer references it |
| Cloud Build SA perms in TF | `terraform plan` shows no diff for `module.cloudbuild_permissions` |
| Full plan clean | `terraform plan -var-file=environments/dev.tfvars` → "No changes" (or only expected additions) |
| INFRA_ARCH doc updated | Phase D state reflected in `docs/INFRASTRUCTURE_ARCHITECTURE.md` |

---

## STOP CONDITIONS — escalate to founder before proceeding

1. `terraform plan` shows unexpected drift BEFORE migration (unexpected destroy or change)
2. `gs://meesell-tfstate` already exists with state in it (different project may have created it)
3. ADC identity is not `vaishnaviramoorthy@gmail.com`
4. `terraform init -migrate-state` errors with a conflict

---

## DO NOT

- Run `terraform destroy` on any resource
- Modify the GitLab WIF pool or `meesell-prod-ci` SA
- Add K8s application resources (Deployments, Services, Secrets, ConfigMaps) to Terraform
- Change `k8s/*.yaml` manifests
- Touch `.github/workflows/ci.yml` (CI/CD session scope)
- Commit `terraform.tfstate` or `terraform.tfstate.backup` to git
- Delete the local `terraform.tfstate` until GCS copy is confirmed

---

## OUTPUT REQUIREMENTS

1. `infra/terraform/backend.tf` — GCS backend configured
2. `infra/terraform/modules/cloudbuild_permissions/main.tf` (+ `variables.tf`, `outputs.tf`) — new module
3. `infra/terraform/main.tf` — new module invocation added
4. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — Phase D state reflected
5. Append `=== UPDATE ===` block to `docs/status/STATUS_INFRA.md` with: state migrated to GCS, Cloud Build SA perms codified, INFRA_ARCH doc refreshed
6. Update own memory at `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

---

## SESSION ORDERING NOTE

This session (Dispatch 2 — Terraform migration) and the CI/CD session (Dispatch 1) are
**independent** and can run in either order.

However, Dispatch 1 adds new Terraform resources (GitHub WIF module). If Dispatch 1 runs first,
the new resources will be in local state. The migration in this session will carry all of them to GCS
regardless — no conflict. Run whichever is convenient.

---

## AUTHORED BY

Master session (mesell-master-session-2), 2026-06-10.
Triggered by: Phase D deployment gap review — manual GCP changes outside Terraform,
local Terraform state at risk.
