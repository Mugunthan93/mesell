# MeeSell CI/CD Execution Plan — Terraform-first + Google Cloud Build

**Date:** 2026-05-30
**Author:** infra-builder (Nexus)
**Project:** mesell (GCP project `project-1f5cbf72-2820-4cdb-949`, org `698205129974`)
**Status:** Plan only — no code written. Director must approve before execution.

This document is the canonical, ordered execution plan to ship a working CI/CD
pipeline for MeeSell. It implements four already-made decisions:

1. **Terraform first** — `terraform apply` runs before any `.gitlab-ci.yml` edits because the pipeline needs the WIF provider name + CI SA email as inputs.
2. **Cloud Build builds Docker images** — GitLab CI does not run `docker build`; it triggers Cloud Build (first 120 min/day free, ephemeral workers, auto-cleanup).
3. **No SA key files** — org policy `constraints/iam.disableServiceAccountKeyCreation` is enforced. All GCP auth from CI is via Workload Identity Federation (GitLab OIDC JWT → STS → impersonate CI SA).
4. **Deploy via IAP SSH** — no SSH private key in GitLab. `gcloud compute ssh --tunnel-through-iap` with the CI SA holding `roles/iap.tunnelResourceAccessor` + `roles/compute.osLogin`. OS Login is required on the VM.

---

## Section 1 — Architecture Overview

```
+----------------------------------------------------------------------------+
| Developer                                                                  |
|   git push origin main                                                     |
+----------------------------------------------------------------------------+
                  | webhook
                  v
+----------------------------------------------------------------------------+
| GitLab CI Runner  (SaaS shared, lightweight — only spends ~2 min CI/min)  |
|                                                                            |
|  stage: test                                                               |
|    image: python:3.12-slim                                                 |
|    services: postgres:16-alpine + valkey/valkey:8-alpine                   |
|    runs:    ruff check + pytest tests/                                     |
|                                                                            |
|  stage: trigger-build                                                      |
|    image: google/cloud-sdk:slim                                            |
|    auth:  id_tokens.GCP_ID_TOKEN -> STS -> impersonate meesell-ci@        |
|    runs:  gcloud builds submit --no-source                                 |
|             --config=cloudbuild.yaml                                       |
|             --substitutions=_TAG=$CI_COMMIT_SHORT_SHA,...                  |
|           (this call BLOCKS until Cloud Build finishes)                    |
|                                                                            |
|  stage: deploy                                                             |
|    image: google/cloud-sdk:slim   (kubectl plugin installed)               |
|    auth:  WIF -> meesell-ci@                                               |
|    runs:                                                                   |
|      gcloud compute ssh meesell-vm --tunnel-through-iap \                  |
|        --zone=asia-south1-a --command='                                    |
|          kubectl -n meesell exec deploy/api -- alembic upgrade head &&    |
|          kubectl -n meesell set image deploy/api      api=IMG_API &&      |
|          kubectl -n meesell set image deploy/frontend frontend=IMG_FE &&  |
|          kubectl -n meesell set image deploy/worker   worker=IMG_API &&   |
|          kubectl -n meesell rollout status deploy/api      --timeout=120s && |
|          kubectl -n meesell rollout status deploy/frontend --timeout=120s && |
|          kubectl -n meesell rollout status deploy/worker   --timeout=120s'  |
+----------------------------------------------------------------------------+
       | OIDC JWT (id_tokens)                       | IAP TCP tunnel (22)
       v                                            v
+--------------------------+        +--------------------------------------+
| GCP IAM                  |        | GCE VM meesell-vm                    |
|  Workload Identity Pool  |        |  OS Login ON                         |
|   gitlab-pool            |        |  K3s single-node                     |
|    provider gitlab-oidc  |        |  containerd pulls from AR using      |
|     attribute_condition: |        |    meesell-workload SA token         |
|     project_path==mesell |        |    (metadata server, no key file)    |
|                          |        |                                      |
|  SA: meesell-ci@         |        |  Namespace: meesell                  |
|   roles:                 |        |   deploy/api      replicas: 2        |
|   - AR writer (scoped)   |        |   deploy/frontend replicas: 1        |
|   - iap.tunnelAccessor   |        |   deploy/worker   replicas: 2        |
|   - compute.osLogin      |        |   svc postgres, svc valkey           |
|   - cloudbuild.builds.editor (to submit/poll builds)                      |
+--------------------------+        +--------------------------------------+
       |                                              ^
       | gcloud builds submit                         | docker pull <sha>
       v                                              |
+----------------------------------------------------------------------------+
| Google Cloud Build  (ephemeral worker, dies after build)                  |
|                                                                            |
|  step 1: docker build -t IMG_API      ./backend                            |
|  step 2: docker build -t IMG_FRONTEND ./frontend                           |
|  step 3: implicit push of `images:` list -> Artifact Registry              |
|                                                                            |
|  Default SA: <project-num>-compute@developer.gserviceaccount.com          |
|    granted roles/artifactregistry.writer on meesell-images                 |
|  Source: --no-source (cloudbuild.yaml is uploaded inline; git ref baked   |
|          into substitutions). Alternative: hosted-git mirror; deferred.   |
|                                                                            |
|  Output: gs://<project>_cloudbuild/source/... (auto-deleted after 30 days)|
+----------------------------------------------------------------------------+
                                  |
                                  v
                +-----------------------------------------+
                | Artifact Registry meesell-images        |
                |  api:<sha>          api:latest          |
                |  frontend:<sha>     frontend:latest     |
                |  (cleanup: keep last 10 prod, drop      |
                |   untagged > 7 days)                    |
                +-----------------------------------------+
```

**Why this shape:**

- GitLab CI minutes are spent only on `pytest` + `gcloud` calls — no `docker build`, no `dind`.
- Cloud Build is free for the first 120 minutes per day and auto-disposes its workspace.
- No SA keys anywhere (org-policy compliant).
- No SSH private key anywhere (IAP + OS Login).
- Image tag is the git short SHA — immutable, audit-friendly, rollback by re-running `kubectl set image` with a previous SHA.

---

## Section 2 — Execution order

This is the sequence the Director must follow. Each step lists its dependencies; steps without dependencies on each other may be parallelised (see Section 9).

| # | Action | Who | Depends on | Deliverable |
|---|--------|-----|-----------|-------------|
| 0 | **Pre-flight audit**: confirm `k8s/meesell-worker-sa-key.json` exists in working tree; capture its contents and confirm whether the key is active in GCP (`gcloud iam service-accounts keys list --iam-account=meesell-worker@...`). If active, rotate/disable BEFORE removal. | MANUAL | — | Known state of leaked credential. |
| 1 | **Remove `k8s/meesell-worker-sa-key.json` from git**: `git rm k8s/meesell-worker-sa-key.json`, add `*-sa-key.json` and `*-key.json` to `.gitignore`. Then purge from history with `git filter-repo --invert-paths --path k8s/meesell-worker-sa-key.json` (or `bfg --delete-files meesell-worker-sa-key.json`). Force-push to `main`. Notify any clones to re-clone. | MANUAL | 0 | History is clean, file gone from tree. |
| 2 | **Add `cloudbuild.googleapis.com` and `iap.googleapis.com`** to `local.required_services` in `terraform/main.tf`. | EDIT_FILE | — | Terraform will enable both APIs on next apply. |
| 3 | **Add two new variables** to `terraform/variables.tf`: `gitlab_project_path` (string, required, no default) and `gitlab_issuer_uri` (string, default `"https://gitlab.com"`). | EDIT_FILE | — | Inputs for WIF binding exist. |
| 4 | **Create `terraform/ci.tf`** with WIF pool, OIDC provider (attribute_condition pinned to the GitLab project path), `meesell-ci` service account, `roles/iam.workloadIdentityUser` binding on the SA scoped to `principalSet://.../attribute.project_path/<path>`, `roles/artifactregistry.writer` scoped to the `meesell-images` repo, `roles/iap.tunnelResourceAccessor` (project), `roles/compute.osLogin` (project), `roles/cloudbuild.builds.editor` (project — lets the SA submit + read builds), project metadata `enable-oslogin=TRUE`, and a firewall rule allowing tcp/22 from `35.235.240.0/20` (IAP forwarders). See Section 3 for the resource list. | NEW_FILE | 2, 3 | All CI-side GCP identity exists in TF. |
| 5 | **Grant Cloud Build default SA `roles/artifactregistry.writer` on the `meesell-images` repo** in `terraform/ci.tf` (or a new `terraform/cloudbuild.tf` if preferred). Use a `data "google_project" "this"` to derive the project number and member string `serviceAccount:<num>-compute@developer.gserviceaccount.com`. | NEW_FILE / EDIT_FILE | 4 | Cloud Build can push to AR. |
| 6 | **Add three outputs** to `terraform/outputs.tf`: `ci_workload_identity_provider` (full resource name), `ci_service_account_email`, `cloud_build_service_account_email`. | EDIT_FILE | 4, 5 | GitLab vars can be populated from `terraform output -raw …`. |
| 7 | **Set TF input `gitlab_project_path`** in `terraform/terraform.tfvars` (uncommitted; or pass via env). Value example: `mygroup/mesell`. Confirm GitLab project URL with Director. | MANUAL | 3 | TF apply has a valid input. |
| 8 | **`terraform plan` + review + `terraform apply`** from `terraform/` dir. Confirm zero destructive changes; the apply only adds resources. | MANUAL | 4, 5, 6, 7 | WIF pool, CI SA, IAP firewall, AR writer binding, OS Login flag all live in GCP. |
| 9 | **Fix K8s manifests**: in `k8s/api.yaml`, `k8s/worker.yaml`, `k8s/frontend.yaml`, replace `meesell/api:latest` with `meesell-images/api:latest` (and `meesell-images/frontend:latest` for the frontend), and replace `REPLACE-PROJECT-ID` with `project-1f5cbf72-2820-4cdb-949`. Manifests remain templates pinned to `:latest`; CI overrides with `:<sha>` via `kubectl set image`. Also remove the dead `iam.gke.io/gcp-service-account` annotation in `k8s/worker.yaml` (Workload Identity is not configured on K3s — the comment in the file says so). | EDIT_FILE | — | Manifests are deployable; image refs are valid. |
| 10 | **Set the 8 GitLab CI/CD variables** in *Settings → CI/CD → Variables* (group or project). All non-secret (Protected + Masked not required; no secrets are stored). See Section 6 for the exact table including how each value is derived. | GITLAB_SETTINGS | 8 | Pipeline can resolve `$GCP_*` vars at runtime. |
| 11 | **Create `cloudbuild.yaml`** at repo root. Two `docker build` + two `docker push` steps, plus an `images:` block listing both image refs (Cloud Build then pushes them implicitly and records SHA in build metadata). Substitutions: `_PROJECT_ID`, `_REGION`, `_REPO`, `_TAG`. Timeout: `1200s` (20 min — first builds are slow; cached subsequent builds finish in 3–5 min). Machine type: default (`E2_HIGHCPU_8` is optional for faster builds at higher cost; not needed for MVP). See Section 4 for the full structure. | NEW_FILE | — | Cloud Build has a buildable config. |
| 12 | **Create `.dockerignore` for backend and frontend**: `backend/.dockerignore` excludes `.venv/`, `__pycache__/`, `*.pyc`, `tests/`, `.pytest_cache/`, `alembic/versions/__pycache__/`, `.env`, `.git/`, `*.md`. `frontend/.dockerignore` excludes `node_modules/`, `dist/`, `.env*`, `.git/`, `*.md`, `coverage/`. Both files significantly reduce Cloud Build upload size when source is included. | NEW_FILE | — | Faster builds, smaller images. |
| 13 | **Create `.gitlab-ci.yml`** at repo root with three stages: `test`, `build`, `deploy`. `test` runs on every push; `build` and `deploy` only on `main`. See Section 5 for stage-by-stage design. | NEW_FILE | 9, 10, 11 | Pipeline exists. |
| 14 | **Smoke-test the test stage** (push to a feature branch) to confirm ruff + pytest pass with the Postgres + Valkey side-cars. No GCP auth involved — isolates lint/test problems early. | MANUAL | 13 | Test stage green on a feature branch. |
| 15 | **Smoke-test WIF auth + Cloud Build trigger** by merging a one-line README change to `main`. Watch (a) GitLab job logs for successful STS token exchange, (b) `gcloud builds list --ongoing` for the build, (c) the Cloud Build log stream URL printed by GitLab. | MANUAL | 8, 11, 13 | Cloud Build produces and pushes both images tagged with the merge commit's SHA. |
| 16 | **Smoke-test deploy stage** by checking pod image SHAs post-deploy: `kubectl -n meesell get deploy/api -o jsonpath='{.spec.template.spec.containers[0].image}'` should show the new SHA. Also confirm rollout finishes and `/health` returns 200. | MANUAL | 15 | End-to-end pipeline works; rollback path validated. |
| 17 | **Document rollback** in `docs/runbooks/rollback.md` (new file): the exact `kubectl set image` command with a previous SHA, plus `kubectl rollout undo deploy/<name>`. Out of scope for the pipeline itself, but Director should track it. | NEW_FILE | 16 | Operator can roll back in under 60 seconds. |

---

## Section 3 — Terraform changes in detail

### 3.1 `terraform/main.tf` (EDIT)

Add to `local.required_services` list:

- `cloudbuild.googleapis.com`
- `iap.googleapis.com`

No other change in this file.

### 3.2 `terraform/variables.tf` (EDIT — append)

```
variable "gitlab_project_path" {
  description = "Full GitLab project path (e.g. mygroup/mesell). Restricts which GitLab project may exchange OIDC tokens for the CI SA."
  type        = string
}

variable "gitlab_issuer_uri" {
  description = "GitLab OIDC issuer. https://gitlab.com for SaaS; the self-hosted URL otherwise."
  type        = string
  default     = "https://gitlab.com"
}
```

### 3.3 `terraform/ci.tf` (NEW)

Resources (names listed; HCL body follows the pattern in `.nexus/results/ci-cd-terraform-gap-analysis.md` §5):

| Resource type | TF name | Purpose |
|---|---|---|
| `google_iam_workload_identity_pool` | `gitlab` (`workload_identity_pool_id = "gitlab-pool"`) | Container for GitLab federation. |
| `google_iam_workload_identity_pool_provider` | `gitlab` (`workload_identity_pool_provider_id = "gitlab-oidc"`) | OIDC trust config; `attribute_condition` pins `project_path` to `var.gitlab_project_path`; `allowed_audiences = [var.gitlab_issuer_uri]`. |
| `google_service_account` | `ci` (`account_id = "${var.name_prefix}-ci"` → `meesell-ci`) | The identity GitLab impersonates. |
| `google_service_account_iam_member` | `ci_wif_binding` | Grants `roles/iam.workloadIdentityUser` on `meesell-ci` to `principalSet://iam.googleapis.com/<pool-name>/attribute.project_path/<gitlab path>`. |
| `google_artifact_registry_repository_iam_member` | `ci_ar_writer` | `roles/artifactregistry.writer` on the `meesell-images` repo only — not project-wide. |
| `google_artifact_registry_repository_iam_member` | `cloudbuild_ar_writer` | Same role for the Cloud Build default SA (`<project-number>-compute@developer.gserviceaccount.com`). Uses a `data "google_project" "this"` to look up the number. |
| `google_project_iam_member` | `ci_iap_tunnel` | `roles/iap.tunnelResourceAccessor`. |
| `google_project_iam_member` | `ci_os_login` | `roles/compute.osLogin`. |
| `google_project_iam_member` | `ci_cloudbuild_editor` | `roles/cloudbuild.builds.editor` — required so the SA can run `gcloud builds submit` and poll the result. |
| `google_compute_project_metadata_item` | `enable_oslogin` | Project metadata `enable-oslogin = TRUE`. **Side effect:** the existing VM `metadata.ssh-keys` entry stops being honoured. Document in the Terraform README so the Director's own laptop SSH path switches to IAP. |
| `google_compute_firewall` | `allow_ssh_iap` | tcp/22 from `35.235.240.0/20` to tag `meesell-public`. Allows IAP forwarders even after the legacy `allow_ssh` (`0.0.0.0/0`) is tightened. |
| `data "google_project"` | `this` | Used to compose the Cloud Build SA member string. |

### 3.4 `terraform/outputs.tf` (EDIT — append)

```
output "ci_workload_identity_provider" {
  description = "Full WIF provider resource name. Set as GitLab CI variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.gitlab.name
}

output "ci_service_account_email" {
  description = "Set as GitLab CI variable GCP_CI_SA_EMAIL."
  value       = google_service_account.ci.email
}

output "cloud_build_service_account_email" {
  description = "Default Cloud Build SA email. Documented for audit only; CI does not need it."
  value       = "${data.google_project.this.number}-compute@developer.gserviceaccount.com"
}
```

### 3.5 What is NOT changed in Terraform

- `iam.tf` — workload SA stays exactly as is.
- `registry.tf` — no change to the repo definition; only a new IAM binding (in `ci.tf`).
- `secrets.tf` — no change; CI does not read secrets, the VM does.
- VM definition — no change. OS Login is enabled at project level (`google_compute_project_metadata_item`), not on the VM resource.

---

## Section 4 — Cloud Build design

### 4.1 How Cloud Build is triggered

**Two options, recommendation first.**

**A. `gcloud builds submit` from GitLab CI (RECOMMENDED for MVP)**

```
gcloud builds submit \
  --no-source \
  --config=cloudbuild.yaml \
  --substitutions=_PROJECT_ID=$GCP_PROJECT_ID,_REGION=$GCP_REGION,_REPO=$GCP_AR_REPO,_TAG=$CI_COMMIT_SHORT_SHA \
  --region=$GCP_REGION
```

- Synchronous: the command blocks until the build finishes; non-zero exit on failure. No polling logic needed in GitLab YAML.
- `--no-source` means "don't upload my git tree". Cloud Build steps clone the repo themselves via a `gcr.io/cloud-builders/git` step (cheap; the only source uploaded is `cloudbuild.yaml`).
- One-line invocation; works out of the box once the CI SA has `roles/cloudbuild.builds.editor`.

**B. Pre-created Cloud Build Trigger + `gcloud builds triggers run` (NOT for MVP)**

- Requires connecting GitLab as a Cloud Build source (currently only GitHub/Bitbucket/Cloud Source Repos/Mirrored are first-class; GitLab integration is preview as of writing).
- Triggers can be invoked via REST but the indirection adds no value for a single-repo MVP.
- **Defer until** there is a second repo or a second team needing isolated build identities.

**Decision:** Use **Option A** for the MVP.

### 4.2 `cloudbuild.yaml` structure (file lives at repo root)

The file must contain:

- `substitutions:` — declared user substitutions (`_PROJECT_ID`, `_REGION`, `_REPO`, `_TAG`). Cloud Build also exposes `$PROJECT_ID` and `$SHORT_SHA` as built-ins, but we pass our own to keep the GitLab side as the source of truth.
- `options:` — `machineType: E2_MEDIUM` (default; bump to `E2_HIGHCPU_8` later if build minutes become a bottleneck), `logging: CLOUD_LOGGING_ONLY` (avoids the need for a build-logs bucket).
- `timeout: 1200s` — 20 minutes hard ceiling. Typical build is 4–6 min; the buffer handles cold-cache and network blips.
- A `git clone` step (or skip if `--no-source` is replaced with `--source=.` later), then four `docker` steps (`build api`, `push api`, `build frontend`, `push frontend`).
- `images:` block listing both fully-qualified image refs — Cloud Build records them in build metadata (used by `gcloud builds describe`) and re-pushes any image not pushed manually. Including this block is best practice even when steps push explicitly.

Skeleton (DO NOT execute — for plan review only):

```
substitutions:
  _PROJECT_ID: ""
  _REGION:     ""
  _REPO:       ""
  _TAG:        ""

options:
  machineType: E2_MEDIUM
  logging:     CLOUD_LOGGING_ONLY

timeout: 1200s

steps:
  - id: clone
    name: gcr.io/cloud-builders/git
    args: ["clone", "--depth=1", "--branch=main", "https://gitlab.com/<group>/mesell.git", "src"]

  - id: build-api
    name: gcr.io/cloud-builders/docker
    dir: src/backend
    args: ["build", "-t", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/api:${_TAG}",
                  "-t", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/api:latest", "."]

  - id: push-api
    name: gcr.io/cloud-builders/docker
    args: ["push", "--all-tags", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/api"]

  - id: build-frontend
    name: gcr.io/cloud-builders/docker
    dir: src/frontend
    args: ["build", "-t", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend:${_TAG}",
                  "-t", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend:latest", "."]

  - id: push-frontend
    name: gcr.io/cloud-builders/docker
    args: ["push", "--all-tags", "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend"]

images:
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/api:${_TAG}
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend:${_TAG}
```

**Note on cloning:** if the repo is private, the `git clone` step needs a GitLab token. The simplest path is to publish a GitLab "deploy token" with `read_repository` scope and embed it via Cloud Build Secret Manager substitution (`availableSecrets`). For a public repo, no auth is needed. Out of MVP scope to wire up if private — Director must decide. **If the repo is private, prefer uploading source from GitLab CI** (`gcloud builds submit --source=.`) which uses Cloud Storage as the transport — no token in the build config.

### 4.3 Workspace cleanup

Cloud Build runs each build on a fresh worker VM; the worker is destroyed when the build completes (success or fail). There is nothing to clean up manually. The only persistent artifact is the staging bucket `gs://<project>_cloudbuild/source/<uuid>.tar.gz` which Google auto-deletes after 30 days. No action required from us.

### 4.4 Permissions summary (granted in Terraform step 5)

- **Cloud Build default SA** (`<project-number>-compute@developer.gserviceaccount.com`):
  - `roles/artifactregistry.writer` on `meesell-images` repo (only).
- **CI SA** (`meesell-ci@…`):
  - `roles/cloudbuild.builds.editor` (project) — to submit and poll builds.
  - `roles/iam.serviceAccountUser` on the Cloud Build SA is NOT required for `--no-source` submissions; only required if we later switch to a non-default builder SA. **Skip for MVP.**

---

## Section 5 — `.gitlab-ci.yml` design (description, not code)

### Top-level

- `stages: [test, build, deploy]`
- `default.image: python:3.12-slim` (overridden per job).
- `variables:` — declare `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_AR_REPO`, `GCP_WIF_PROVIDER`, `GCP_CI_SA_EMAIL`, `GCP_VM_NAME`, `GCP_VM_ZONE`, `GITLAB_OIDC_AUDIENCE`, plus two computed convenience vars: `IMAGE_API` and `IMAGE_FRONTEND` (each `"${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_AR_REPO}/<name>:${CI_COMMIT_SHORT_SHA}"`).

### Reusable WIF auth snippet

Define a YAML anchor `.gcp_auth` (`id_tokens.GCP_ID_TOKEN.aud=$GITLAB_OIDC_AUDIENCE`) plus a `before_script` that:

1. Writes `$GCP_ID_TOKEN` to `/tmp/oidc.jwt`.
2. Writes a `/tmp/wif.json` external_account credential file pointing at `audience://iam.googleapis.com/${GCP_WIF_PROVIDER}` and `service_account_impersonation_url` for `$GCP_CI_SA_EMAIL`.
3. Runs `gcloud auth login --cred-file=/tmp/wif.json --quiet`.
4. Runs `gcloud config set project "$GCP_PROJECT_ID"`.

Jobs that need GCP merge this snippet via `extends:` or `<<: *gcp_auth`.

### Stage 1 — `test:backend`

| Setting | Value |
|---|---|
| `stage` | `test` |
| `image` | `python:3.12-slim` |
| `services` | `postgres:16-alpine` (alias `postgres`), `valkey/valkey:8-alpine` (alias `valkey`) |
| `variables` | `POSTGRES_DB=meesell_test`, `POSTGRES_USER=meesell`, `POSTGRES_PASSWORD=password`, `TEST_DATABASE_URL=postgresql+asyncpg://meesell:password@postgres:5432/meesell_test`, `VALKEY_URL=redis://valkey:6379/15`, `CELERY_BROKER_URL=redis://valkey:6379/11`, `CELERY_RESULT_BACKEND=redis://valkey:6379/12`, `JWT_SECRET=test-secret-do-not-use` |
| `before_script` | `cd backend && pip install --no-cache-dir -r requirements.txt` |
| `script` | `python -m ruff check app/` then `python -m pytest tests/ -v` |
| `rules` | run on all pushes (no `if`) |
| `cache` | `paths: [backend/.cache/pip]` keyed on `requirements.txt` hash — saves ~45 s per run |

### Stage 2 — `trigger-build`

| Setting | Value |
|---|---|
| `stage` | `build` |
| `image` | `google/cloud-sdk:slim` |
| `extends` | `.gcp_auth` |
| `rules` | `if: $CI_COMMIT_BRANCH == "main"` only |
| `needs` | `[test:backend]` |
| `script` | single line: `gcloud builds submit --no-source --config=cloudbuild.yaml --region=$GCP_REGION --substitutions=_PROJECT_ID=$GCP_PROJECT_ID,_REGION=$GCP_REGION,_REPO=$GCP_AR_REPO,_TAG=$CI_COMMIT_SHORT_SHA` |
| Behaviour | Blocks until build finishes; non-zero exit if any Cloud Build step fails. The GitLab log streams the Cloud Build log URL (`Logs are available at [https://console.cloud.google.com/cloud-build/builds/<id>?project=<num>]`). |

### Stage 3 — `deploy`

| Setting | Value |
|---|---|
| `stage` | `deploy` |
| `image` | `google/cloud-sdk:slim` |
| `extends` | `.gcp_auth` |
| `rules` | `if: $CI_COMMIT_BRANCH == "main"` only |
| `needs` | `[trigger-build]` |
| `before_script` (extends parent) | additionally install `kubectl`: `gcloud components install kubectl --quiet` (cached in slim image after first run) |
| `script` | single SSH-through-IAP command that runs: 1. `kubectl -n meesell exec deploy/api -- alembic upgrade head`; 2. `kubectl -n meesell set image deploy/api api=$IMAGE_API`; 3. `kubectl -n meesell set image deploy/worker worker=$IMAGE_API` (worker shares the api image); 4. `kubectl -n meesell set image deploy/frontend frontend=$IMAGE_FRONTEND`; 5. `kubectl -n meesell rollout status deploy/api --timeout=120s`; 6. same for `deploy/frontend`, `deploy/worker`. All chained with `&&`. |
| `environment.name` | `production` — gives a deploy-history view in the GitLab UI. |
| `environment.url` | `https://meesell.in` (or whatever the public URL is) |

**On migration order:** the spec says "migrate before set-image". This is the FORWARD-COMPATIBLE pattern: migrations are written so the OLD pod code is still happy after `alembic upgrade head` runs (e.g. additive columns, no drops). The new image starts AFTER the migration, so DB schema is always ahead of code by zero or more versions. Document this rule in `docs/runbooks/migrations.md` (out of MVP scope).

---

## Section 6 — GitLab CI variables (complete list)

Set under **Project Settings → CI/CD → Variables**. None require Masked or Protected — they are not secrets.

| Variable | Value | How to derive | Type |
|---|---|---|---|
| `GCP_PROJECT_ID` | `project-1f5cbf72-2820-4cdb-949` | `terraform output -raw project_id` (or known constant) | Plain |
| `GCP_REGION` | `asia-south1` | `terraform output` / known | Plain |
| `GCP_AR_REPO` | `meesell-images` | `terraform output -raw artifact_registry_url` (take the tail segment) | Plain |
| `GCP_WIF_PROVIDER` | e.g. `projects/698205129974/locations/global/workloadIdentityPools/gitlab-pool/providers/gitlab-oidc` | `terraform output -raw ci_workload_identity_provider` (set after step 8) | Plain |
| `GCP_CI_SA_EMAIL` | `meesell-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` | `terraform output -raw ci_service_account_email` | Plain |
| `GCP_VM_NAME` | `meesell-vm` | `terraform output -raw vm_name` | Plain |
| `GCP_VM_ZONE` | `asia-south1-a` | TF var / known | Plain |
| `GITLAB_OIDC_AUDIENCE` | `https://gitlab.com` | matches the `allowed_audiences` set in TF (must equal `var.gitlab_issuer_uri`) | Plain |

All eight are plain text. The principle "no secrets in GitLab" is the entire reason we adopted WIF; if any of these grew sensitive we would have lost the value of the design.

---

## Section 7 — K8s manifest fixes

| File | Change |
|---|---|
| `k8s/api.yaml` | Line 18: replace `meesell/api:latest` with `meesell-images/api:latest`. Replace `REPLACE-PROJECT-ID` with `project-1f5cbf72-2820-4cdb-949`. Keep `:latest` tag — it acts as the bootstrap default; CI uses `kubectl set image` to override with `:<sha>` on every deploy. `imagePullPolicy: Always` stays (necessary for `:latest` to ever refresh). |
| `k8s/worker.yaml` | Line 25: same two substitutions. Additionally **delete** lines 15–22 (the `iam.gke.io/gcp-service-account` annotation + its comment) — Workload Identity is not configured on K3s, the annotation is dead metadata. The metadata-server pattern in the rest of the comment is correct and should stay as a docstring (move to a `# Note:` line above the container). |
| `k8s/frontend.yaml` | Line 18: replace `meesell/frontend:latest` with `meesell-images/frontend:latest`. Replace `REPLACE-PROJECT-ID` with `project-1f5cbf72-2820-4cdb-949`. |

**Image tag strategy — recommendation: keep `:latest` in manifests, override at deploy time.**

Reasoning:
- Manifests stay as a clean, hand-applicable template (`kubectl apply -f k8s/` still works for first-boot).
- Pipeline owns the SHA — every `kubectl set image` writes the immutable tag, so the running Deployment's `spec.template.spec.containers[0].image` always tells you which commit is live (`kubectl get deploy/api -o jsonpath='{.spec.template.spec.containers[0].image}'`).
- Rollback is a one-liner: `kubectl set image deploy/api api=<registry>/api:<previous-sha>` — no git revert, no re-build, no Cloud Build call.
- The downside (manifests don't reflect what's actually running) is true but acceptable for a single-environment MVP. When a staging env is added, switch to Kustomize overlays that template the tag.

**Alternative considered and rejected:** baking `:<sha>` into the manifest and re-applying with `envsubst`. Adds a templating layer, makes `kubectl apply` non-deterministic, and the manifest's tag drifts from reality the moment anyone runs `kubectl set image` by hand. Not worth the friction at MVP scale.

---

## Section 8 — Risk and rollback

| Failure mode | Blast radius | Recovery |
|---|---|---|
| **Cloud Build fails** (compile error, missing dependency, image push 403) | Zero — GitLab pipeline halts at `trigger-build`, deploy stage never runs, existing pods keep serving traffic with the previous SHA. | Read Cloud Build log URL from GitLab job output. Fix in code, re-push. No infra touched. |
| **`gcloud compute ssh` fails to tunnel** (IAP firewall not applied, OS Login disabled, SA missing `iap.tunnelResourceAccessor`) | Zero — deploy stage fails, pods unchanged. | Verify TF apply included `enable-oslogin=TRUE` and the IAP firewall. Verify CI SA has both IAP + OS Login roles. Test from a laptop: `gcloud compute ssh meesell-vm --tunnel-through-iap --zone=asia-south1-a` impersonating the CI SA. |
| **`kubectl set image` fails** (image SHA doesn't exist, registry 401) | Zero — Kubernetes rejects the update; previous ReplicaSet keeps running. | `kubectl -n meesell rollout undo deploy/<name>` to revert to the previous ReplicaSet. Or re-run pipeline once the registry issue is fixed. |
| **`kubectl rollout status` times out (120 s)** because new pods crash-loop | Partial — 1 of 2 replicas may already be the new (bad) image. Service still has the 1 old replica. Real users see ~50% errors. | Same as above: `kubectl rollout undo`. Investigate crash reason (`kubectl logs <new pod>`). |
| **`alembic upgrade head` fails** | Mid-deploy — DB schema may be partially migrated; new image is NOT yet rolled (migration runs first in our design). | **Forward-only strategy:** every migration must be idempotent + reversible-by-forward-migration. If a migration fails, fix it in a follow-up commit (`alembic revision -m 'fix-XYZ'`) and re-run pipeline. **No downgrade.** Justification: prod databases over a single VM with a single writer cannot meaningfully test downgrade paths; forcing the team to write forward-only migrations is safer than relying on `alembic downgrade -1`. Document this rule in `docs/runbooks/migrations.md`. |
| **WIF auth fails** (clock skew, audience mismatch, attribute_condition mismatch) | Zero — `gcloud auth login` returns non-zero, every downstream stage is skipped. | Run `gcloud auth print-identity-token --impersonate-service-account=$GCP_CI_SA_EMAIL` locally to verify the trust chain. Most common cause: `gitlab_project_path` in TF doesn't match the actual GitLab namespace. Re-apply TF with the correct path. |
| **Rollback to a previous SHA** | N/A — preventative. | `kubectl -n meesell set image deploy/api api=asia-south1-docker.pkg.dev/<proj>/meesell-images/api:<old-sha> && kubectl rollout status deploy/api`. To find old SHAs: `gcloud artifacts docker tags list asia-south1-docker.pkg.dev/<proj>/meesell-images/api`. Repository policy keeps the last 10 production tags — that's ~10 deploys of headroom. |

---

## Section 9 — Estimated effort per step

| # | Step | Hours | Parallelisable with |
|---|------|-------|---------------------|
| 0 | Audit leaked SA key state | 0.25 | 2, 3, 9 |
| 1 | Remove key from git + history rewrite | 0.5 | 2, 3 |
| 2 | Add 2 APIs to required_services | 0.1 | 3, 9, 12 |
| 3 | Add 2 TF variables | 0.1 | 2, 9, 12 |
| 4 | Create `terraform/ci.tf` | 1.5 | 9, 12 |
| 5 | Cloud Build SA IAM binding (TF) | 0.25 | 9, 12 |
| 6 | Add 3 TF outputs | 0.1 | 9, 12 |
| 7 | Set `gitlab_project_path` tfvar | 0.1 | 9, 12 |
| 8 | `terraform plan` + apply | 0.5 (+ 2-3 min wait) | nothing (gate) |
| 9 | Fix K8s manifests (3 files) | 0.5 | 2–7, 11, 12 |
| 10 | Set 8 GitLab CI variables | 0.25 | 11, 12 |
| 11 | Write `cloudbuild.yaml` | 0.75 | 9, 12, 13 |
| 12 | Write 2 `.dockerignore` files | 0.25 | 2–11, 13 |
| 13 | Write `.gitlab-ci.yml` | 1.5 | (depends on 9, 10, 11) |
| 14 | Smoke test stage on feature branch | 0.5 | nothing (gate) |
| 15 | Smoke test build via WIF + Cloud Build | 0.75 | nothing (gate) |
| 16 | Smoke test deploy via IAP SSH | 0.75 | nothing (gate) |
| 17 | Write rollback runbook | 0.5 | post-MVP |

**Total: ~9.0 engineering hours**, plus ~10 minutes of `terraform apply` wait and ~20 minutes across the three smoke tests.

**Critical path (cannot be parallelised):** 0 → 1 → 2/3/4/5/6/7 (parallel) → 8 → 10 → 13 → 14 → 15 → 16. Everything else is concurrent with the critical path.

---

## Appendix A — Files this plan will create or modify

**New files:**
- `terraform/ci.tf`
- `cloudbuild.yaml`
- `.gitlab-ci.yml`
- `backend/.dockerignore`
- `frontend/.dockerignore`
- `docs/runbooks/rollback.md` (step 17, post-MVP)
- `docs/runbooks/migrations.md` (referenced by Section 8, post-MVP)

**Modified files:**
- `terraform/main.tf` — add 2 APIs
- `terraform/variables.tf` — add 2 variables
- `terraform/outputs.tf` — add 3 outputs
- `k8s/api.yaml` — fix image ref
- `k8s/worker.yaml` — fix image ref + remove dead annotation
- `k8s/frontend.yaml` — fix image ref
- `.gitignore` — add `*-sa-key.json`, `*-key.json`

**Deleted files:**
- `k8s/meesell-worker-sa-key.json` (plus history purge)

**Untouched on purpose:**
- `terraform/iam.tf`, `terraform/registry.tf`, `terraform/secrets.tf` — runtime infra stays as is.
- `Makefile` — keep for local dev; the CI pipeline does not call `make`.
- `docker-compose.dev.yml` / `docker-compose.prod.yml` — orthogonal to CI/CD.

---

## Appendix B — Open questions for the Director

1. **GitLab project path** — what is the full `<group>/<project>` slug? Required for TF `gitlab_project_path`.
2. **Repo visibility** — is the GitLab repo public or private? Affects whether Cloud Build's `git clone` step needs a deploy token, or whether to switch to `gcloud builds submit --source=.`.
3. **Worker deployment** — is `deploy/worker` currently in the cluster? `k8s/worker.yaml` exists but the deploy stage in this plan tries to roll it. Confirm before running step 16, else remove the worker line from the deploy script.
4. **Domain** — `manage_dns = false` and `var.domain = ""`. Not blocking CI/CD, but `environment.url` in the deploy job needs a value.
5. **`meesell-worker@` SA drift** — listed as a P1 in the gap analysis; this plan does not touch it. Confirm whether the Director wants it imported into TF or deleted in a follow-up.
