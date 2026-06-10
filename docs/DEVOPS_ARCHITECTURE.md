# MeeSell DevOps Architecture — Single Source of Truth

**Owner:** `meesell-infra-builder`
**Status:** LOCKED (open decisions flagged with `[FOUNDER DECISION REQUIRED]`)
**Last verified live:** 2026-06-10
**Companion docs:** `INFRASTRUCTURE_ARCHITECTURE.md` (live infra), `BACKEND_ARCHITECTURE.md §19.G + §20` (CI gates + deploy topology), `INFRASTRUCTURE_PLAYBOOK.md` (manual procedures)

This document is the single source of truth for MeeSell's CI/CD, build, deploy, environment, and observability pipeline. If anything in another doc conflicts with this one, this document wins. Update this file whenever the pipeline changes.

> **Discipline (post Phase D, ratified 2026-06-10):**
> 1. Every GCP-layer change goes through Terraform (no direct `gcloud iam`).
> 2. K8s app workloads (Deployments / Services / ConfigMaps / non-bootstrap Secrets) go through `k8s/*.yaml` manifests and the CI/CD pipeline (no direct `kubectl apply` from a laptop, except for emergency rollback).
> 3. Datastore StatefulSets (`postgres`, `valkey`) and Ingress resources are Terraform-owned and stay out of `kubectl apply`.
> 4. Every image deployed to a tracked namespace MUST come from `meesell-prod-images` Artifact Registry and carry both a SHA tag and `:latest` (or `:vX.Y.Z` on release).

---

## 1. Overview & Principles

**One-paragraph philosophy:** MeeSell ships small, immutable container images from a single trunk branch (`main`), tested by a 5-gate CI run that gates every PR, built once and tagged by git SHA, deployed via IAP-tunneled `kubectl` against a single K3s cluster, with environment separation expressed as K8s namespaces (`dev` / `staging` / `prod`). Secrets never live in code or CI files — they are pulled at runtime from GCP Secret Manager via the VM service account, or injected into CI as ephemeral test-safe values. A bad deploy rolls back in under two minutes via `kubectl rollout undo`.

### 1.1 Five Principles

| # | Principle | What it forbids |
|---|-----------|----------------|
| P1 | **Immutable images** | Editing a running pod in-place. Hot-patching. `kubectl edit` on a Deployment to swap an image. |
| P2 | **Environment parity** | Different code paths for `dev` vs `staging`. Branch-per-environment. "It works on staging" excuses. |
| P3 | **Secrets never in code** | Hard-coded keys in any committed file. Long-lived service account JSON keys. CI files containing real OTP / API tokens. |
| P4 | **Deploy what you tested** | Deploying a different SHA than what passed CI. "Quick fix in prod, will commit later." |
| P5 | **Rollback in < 2 min** | A deploy mechanism that requires more than `kubectl rollout undo` to revert. Migration patterns that can't be undone. |

### 1.2 Platform Decisions

| Concern | Decision | Why |
|---------|----------|-----|
| Source control | **GitHub** (`Mugunthan93/mesell`) | Founder choice. Migration from GitLab cost = zero (no pipelines actually ran on GitLab). |
| CI/CD orchestrator | **GitHub Actions** | First-party OIDC support for GCP WIF, free tier covers V1, no separate runner infra. |
| Image build location | **GCP Cloud Build** (triggered from Actions via `gcloud builds submit`) | Founder has no local Docker (disk constraint). Actions runners build fine for small images but Cloud Build keeps consistency with the manual Phase D builds. |
| Image registry | **GCP Artifact Registry** `meesell-prod-images` (asia-south1) | Already live (Phase A). Co-located with the deploy target. |
| Container orchestrator | **K3s single-node** on `meesell-dev` VM | Already live (Phase A). Production parity via namespaces, not separate clusters. |
| Deploy mechanism | **GCP IAP TCP tunnel** → `gcloud compute ssh --tunnel-through-iap` → `kubectl` | No port 6443 exposure to internet; OIDC WIF auth; zero firewall changes per deploy. |
| Secrets at runtime | **GCP Secret Manager** → in-cluster `backend-secrets` Secret | Already live (Phase A + D). Rotation = `gcloud secrets versions add` + `kubectl rollout restart`. |
| Test secrets in CI | **GitHub Actions environment variables** (dummy + GitHub Secrets) | Real production keys never enter Actions. Integration uses ephemeral CI containers. |
| Terraform state | **GCS backend** (`gs://meesell-tfstate/terraform/state/`) | Migrated 2026-06-10. Local backup retained as DR. CI does NOT run `terraform apply` — founder gate. |

---

## 2. Source Control Strategy

### 2.1 Repository

- **Host:** GitHub
- **Path:** `Mugunthan93/mesell`
- **Remote:** `https://github.com/Mugunthan93/mesell.git`
- **Default branch:** `main` (production-grade — every commit on `main` is deployable)

The Phase A WIF wiring originally targeted GitLab (`techades/mesell`). The GitLab pool + SA stay in place untouched (D6 RESOLVED — separate SAs). GitHub becomes the active CI/CD platform from Phase E onward.

### 2.2 Branch Model

| Branch type | Naming | Lifecycle | Triggers |
|-------------|--------|-----------|----------|
| `main` | (fixed) | Permanent | Every push → full CI + auto-deploy to `dev` |
| Feature | `claude/<task>-<short-id>` or `feat/<topic>` or `fix/<topic>` | Created from `main`, deleted after merge | Push → CI only (no deploy) |
| PR | (via GitHub UI) | Squash-merged into `main` | PR open / synchronize → CI run on the merge result |

**`main` is protected:**
- Require pull request before merging
- Require CI checks: `unit`, `smoke`, `lint`, `integration`, `golden_roundtrip` — all 5 green
- No direct pushes (linear history via squash-merge)
- Force pushes disabled

**Tag strategy:**
- Release tags: `v{MAJOR}.{MINOR}.{PATCH}` (semver). First release tag will be `v1.0.0` once the V1 production cut-over is done.
- Build artifacts always carry the git SHA as the primary tag; `:latest` is a moving alias that always points to the most recent `main` build; release tags are signed and pushed manually.

### 2.3 Commit Conventions

| Prefix | Use |
|--------|-----|
| `feat:` | New feature / capability |
| `fix:` | Bug fix |
| `chore:` | Tooling, configs, build files |
| `docs:` | Documentation only |
| `refactor:` | No behaviour change |
| `test:` | Test changes only |

Co-author trailer when an agent contributed:
`Co-Authored-By: <agent-name> <noreply@anthropic.com>`

---

## 3. Environment Strategy

Three environments share the single K3s cluster. Isolation is at the K8s namespace boundary, not at the cluster boundary.

| Env | Namespace | URL | Status | Auto-deploy from |
|-----|-----------|-----|--------|------------------|
| `dev` | `dev` | `api.mesell.xyz`, `dev.mesell.xyz` | **LIVE** (api+worker 2/2) | `main` (every push) |
| `staging` | `staging` | `staging.mesell.xyz` | Ingress + cert live, app pods pending | Manual `workflow_dispatch` |
| `prod` | `prod` | `www.mesell.xyz` | Namespace not yet created (gated on 1 wk clean staging per playbook §15c) | Manual `workflow_dispatch` + founder approval |

### 3.1 Promotion Path

```
PR merge to main
  └─► CI gates (5 jobs) PASS
  └─► Cloud Build builds api:<sha>, worker:<sha>, frontend:<sha>
  └─► Auto-deploy to dev/  (kubectl set image)
        └─► Smoke check (curl /health, expect 200)
        └─► If smoke FAILS → kubectl rollout undo + Slack alert + halt promotion
  
Manual workflow_dispatch (env=staging)
  └─► Re-tag <sha> as 'staging' in AR
  └─► Deploy <sha> to staging/  (kubectl set image)
        └─► Same smoke check
  └─► Soak for 1 week with eyes on Grafana

Manual workflow_dispatch (env=prod) + founder approval
  └─► Re-tag <sha> as 'prod' in AR  
  └─► Deploy <sha> to prod/  (kubectl set image)
        └─► Same smoke check + canary read of 5xx rate for 10 min
```

### 3.2 Environment-Specific Config

Per-env values come from two sources:

| Source | What lives there |
|--------|------------------|
| `k8s/overlays/{env}/configmap.yaml` (Kustomize patch) | `APP_ENV`, `CORS_ALLOWED_ORIGINS`, `LOG_LEVEL`, `RL_PER_IP_PER_MINUTE` |
| `backend-secrets` K8s Secret (per namespace) | All credentials (DB URL, JWT secret, API keys) sourced from GCP SM |

**APP_ENV literal gotcha:** the Pydantic `Settings` model enforces `APP_ENV ∈ {development, staging, production}`. Use `development` for the `dev` namespace, NOT `dev` (Phase D bug — fix logged in §10.2).

---

## 4. Workload Identity Federation (GitHub Actions → GCP)

GitHub Actions authenticates to GCP using OpenID Connect tokens exchanged for short-lived GCP access tokens. No service account JSON keys leave Google.

### 4.1 Resources (codified in `infra/terraform/modules/ci_identity/`)

| Resource | ID | Owner |
|----------|----|----|
| WIF pool (existing — GitLab) | `gitlab-prod-pool` | Phase A — untouched in Phase E |
| WIF pool (new — GitHub) | `github-actions-pool` | Phase E (this session) |
| WIF provider (existing — GitLab) | `gitlab-prod-provider` (issuer `gitlab.com`) | Phase A |
| WIF provider (new — GitHub) | `github-actions-provider` (issuer `token.actions.githubusercontent.com`) | Phase E (this session) |
| SA (existing — GitLab) | `meesell-prod-ci@<proj>.iam.gserviceaccount.com` | Phase A — UNUSED for GitHub |
| SA (new — GitHub) | `meesell-github-ci@<proj>.iam.gserviceaccount.com` | Phase E (this session) — **D6 RESOLVED: separate SA** |

**Why a separate SA?** Founder decision D6 (2026-06-09): a single SA used by both GitLab (legacy) and GitHub (active) makes blast radius unclear. If GitHub Actions is ever compromised, revoking the SA is one atomic action that doesn't take GitLab down. They share no roles.

### 4.2 GitHub SA Roles

The `meesell-github-ci` SA holds the minimum roles required to run the pipeline:

| Role | Scope | Purpose |
|------|-------|---------|
| `roles/artifactregistry.writer` | `meesell-prod-images` repo | Push images during Cloud Build |
| `roles/storage.admin` | `gs://project-1f5cbf72-2820-4cdb-949_cloudbuild` | Upload source tarballs for Cloud Build (Cloud Build's compute SA needs this separately — see `module.cloudbuild_permissions`) |
| `roles/cloudbuild.builds.editor` | Project | Trigger `gcloud builds submit` |
| `roles/secretmanager.secretAccessor` | Project | Read CI-only secrets (e.g. test webhook signing key) |
| `roles/iap.tunnelResourceAccessor` | `meesell-dev` VM | Establish IAP TCP tunnel to the VM |
| `roles/compute.instanceAdmin.v1` | `meesell-dev` VM | Run `gcloud compute ssh --tunnel-through-iap` |

**Scoping discipline:** `compute.instanceAdmin.v1` is granted at the VM resource level (`google_compute_instance_iam_member`), NOT project level. Grants the minimum needed to SSH to one specific VM.

### 4.3 WIF Attribute Condition

The provider's attribute condition restricts which GitHub Actions runs can exchange a token for `meesell-github-ci`:

```hcl
attribute_condition = "assertion.repository == \"Mugunthan93/mesell\""
```

**[FOUNDER DECISION REQUIRED — WIF-1]:** Should the condition be tighter?

| Option | Behaviour | Recommendation |
|--------|-----------|----------------|
| (a) Repository only — `assertion.repository == "Mugunthan93/mesell"` | Any branch / any workflow / any ref in this repo can deploy | **Recommended for V1.** CI must run on PRs to gate them, and PRs run from feature branches. |
| (b) Repository + `main` ref only — `assertion.repository == "..." && assertion.ref == "refs/heads/main"` | Only `main` can deploy; PRs can still build but not push | Cleaner blast radius but blocks deploy from manual `workflow_dispatch` on a feature branch. Use after V1 GA. |

### 4.4 GitHub Repository Settings (one-time founder action)

After `terraform apply` (founder runs locally — see §6), the founder must set these GitHub repository variables in **Settings → Secrets and variables → Actions → Variables**:

| Variable | Source | Example |
|----------|--------|---------|
| `GCP_WIF_PROVIDER` | `terraform output github_wif_provider_name` | `projects/888244156264/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider` |
| `GCP_CI_SA_EMAIL` | `terraform output github_ci_sa_email` | `meesell-github-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` |

These are **variables, not secrets** — neither value is sensitive. Storing them as repo variables makes the workflow file self-documenting.

### 4.5 Terraform State + Apply Gate

**Status:** `backend.tf` was migrated to GCS (`gs://meesell-tfstate/terraform/state/`) on 2026-06-10. CI runners with WIF auth COULD now run `terraform plan` / `terraform apply`.

**Current discipline:** Even though state is in GCS, `terraform apply` remains a **founder-only manual step** for V1:
- The plan output is reviewed by the founder before every apply.
- Layer C account-lock preconditions still need the ADC token to belong to `vaishnaviramoorthy@gmail.com`; CI doesn't have that identity yet (Layer G hardening will add a `google_client_openid_userinfo` precondition that catches identity mismatch).
- Adding `terraform apply` to CI is tracked as a Phase K deliverable (after Layer G ships + production cutover).

For Phase E–H: CI does NOT run any `terraform` command. The founder runs `terraform plan` + `terraform apply` from the laptop after merging this session's Terraform changes.

---

## 5. CI Pipeline (GitHub Actions)

### 5.1 Workflow File

`.github/workflows/ci.yml` — single workflow with 8 jobs: 5 sequential gates + a build job + a deploy job + a nightly cron job.

### 5.2 Triggers

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 1 * * *'   # 01:00 UTC = 06:30 IST (nightly)
```

Every push and PR runs the 5 gates. Nightly fires the slow + AI eval jobs (and skips the 5 gates because they're not what nightly is for).

### 5.3 The Five Gates (sequential)

| # | Job | What it runs | Services needed | Approx duration |
|---|-----|--------------|-----------------|-----------------|
| 1 | `unit` | `pytest -m "unit"` | none | < 30s |
| 2 | `smoke` | `pytest -m "smoke"` | none | < 10s |
| 3 | `lint` | `lint-imports` + 3 AST scanners (Contracts 1–10) | none | < 60s |
| 4 | `integration` | `pytest -m "integration"` | postgres:16 + valkey:8 | ~3 min |
| 5 | `golden_roundtrip` | `pytest -m "golden_roundtrip"` | postgres:16 + valkey:8 | ~1 min |

Each job declares `needs:` on its predecessor — a fast-fail at gate 1 cancels everything downstream. The lint contracts are 100% deterministic — gate 3 fails the build hard if any contract is violated.

### 5.4 Per-Gate Detail

All gates run from the `backend/` working directory (where `pytest.ini` lives).

#### `unit`
- Python 3.12
- `pip install -r backend/requirements.txt` (cached on `requirements.txt` hash)
- Env: dummy `SECRET_KEY`, `JWT_SECRET`, `MSG91_*`, `RAZORPAY_*`, `REFRESH_TOKEN_PEPPER`, `AUDIT_PII_SALT` (CI-safe placeholders, NOT production values)
- Command: `pytest -m "unit"`

#### `smoke`
- Same Python / deps / env as `unit`
- Command: `pytest -m "smoke"` (boots FastAPI app + asserts schema shape)

#### `lint`
- Same Python / deps as `unit`
- 4 commands (all from `backend/`):
  ```bash
  lint-imports --config tests/lint/import_rules.toml   # Contracts 1-7
  python tests/lint/check_scope_to_user.py             # Contract 8
  python tests/lint/check_no_meesho_symbols_outside_export.py   # Contract 9
  python tests/lint/check_message_id_regex.py          # Contract 10
  ```
- A single failed contract fails the gate.

#### `integration`
- Same Python / deps
- Service containers (GitHub Actions native `services:` block):
  - `postgres:16-alpine` mapped 5432 → 5433 (matches conftest fixture)
  - `valkey/valkey:8-alpine` mapped 6379 → 6381
- Env vars point at the service containers:
  ```
  TEST_DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5433/meesell_test
  TEST_VALKEY_URL=redis://localhost:6381/0
  ```
- Command: `pytest -m "integration"`

#### `golden_roundtrip`
- Same setup as `integration`
- Command: `pytest -m "golden_roundtrip"` (15 XLSX round-trip fixtures from `backend/tests/golden/`)

### 5.5 Nightly Job

Separate from the 5 gates, fires only on the schedule trigger:

```yaml
nightly:
  if: github.event_name == 'schedule'
  needs: []
```

Runs two stages in parallel:
- `pytest -m "slow or perf"` — flow tests, perf benchmarks (PYTEST_RUN_SLOW=1)
- `pytest -m "ai_eval"` — Gemini eval suite (RUN_AI_EVAL=1, needs `GEMINI_API_KEY` from GitHub Actions secret)

**`GEMINI_API_KEY` source:** founder sets `GEMINI_API_KEY_CI` in GitHub repo **Secrets** (NOT variables) — a CI-safe Gemini key with low quota, distinct from the production key in GCP Secret Manager. Workflow references it as `secrets.GEMINI_API_KEY_CI`.

### 5.6 Caching

Pip wheels are cached keyed on `backend/requirements.txt`:
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
    cache-dependency-path: backend/requirements.txt
```

First run: ~90s install. Cached runs: ~10s.

---

## 6. Docker Build Pipeline

### 6.1 Trigger

The `build` job in `ci.yml` runs after all 5 CI gates pass, but only on direct push to `main`:

```yaml
build:
  needs: [unit, smoke, lint, integration, golden_roundtrip]
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

PRs run the 5 gates but NEVER trigger a build — no `pr:<sha>` images in the registry, no accidental "deploy a PR" path.

### 6.2 Build Mechanism

The build step calls `gcloud builds submit` against the repo-root `cloudbuild.yaml`. Cloud Build runs as the project's Compute Engine default SA (the quirk codified in `module.cloudbuild_permissions` — see INFRASTRUCTURE_ARCHITECTURE.md §10.2).

```yaml
- run: |
    gcloud builds submit --no-source \
      --config=cloudbuild.yaml \
      --project=${{ env.PROJECT_ID }} \
      --substitutions=_PROJECT_ID=${{ env.PROJECT_ID }},_REGION=${{ env.REGION }},_REPO=${{ env.REPO }},_TAG=${{ github.sha }} \
      --timeout=1800s
```

`--no-source` tells Cloud Build to NOT upload the workspace from the runner — `cloudbuild.yaml`'s `clone` step does a fresh `git clone` of the repo on the Cloud Build worker, pinned to `main`. This keeps the runner upload small.

### 6.3 What `cloudbuild.yaml` Does

Three image targets, each tagged with `:${_TAG}` (the git SHA) AND `:latest`:

| Image | Built from | Push target |
|-------|-----------|-------------|
| `api` | `backend/Dockerfile` | `${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/api:{SHA, latest}` |
| `worker` | `backend/Dockerfile.worker` | `.../worker:{SHA, latest}` |
| `frontend` | `frontend/Dockerfile` | `.../frontend:{SHA, latest}` |

The `frontend` build is **conditional**: a precheck step runs `test -f /workspace/src/frontend/Dockerfile` and skips the frontend build + push if the Dockerfile is absent (Wave 2B may not have produced one yet).

### 6.4 Tag Strategy

| Tag | Lifecycle | Source of truth |
|-----|-----------|-----------------|
| `:<sha>` (40-char or 7-char git SHA) | Permanent — never overwritten | The exact commit that was built |
| `:latest` | Moving alias — always points at the newest `main` build | Whatever the last build pushed |
| `:vX.Y.Z` | Permanent — pushed only by the release workflow | Founder release |
| `:staging` | Moving alias — points at the SHA promoted to staging | Manual promotion workflow |
| `:prod` | Moving alias — points at the SHA promoted to prod | Manual promotion workflow |

**Discipline:** Deployments NEVER reference `:latest` in K8s manifests — they get the SHA injected by the deploy workflow. `:latest` exists for human convenience (`docker pull .../api:latest` on a debugging laptop).

### 6.5 Why Cloud Build, Not Actions-Native `docker/build-push-action`?

Two options were considered. Cloud Build won for V1:

| Mechanism | Pro | Con |
|-----------|-----|-----|
| **Cloud Build** (chosen) | Same path as Phase D manual builds. Builds run inside GCP, push is local to the registry, lower egress. Free tier covers V1 (120 build-min/day). Compute SA quirk already codified. | One more service to monitor. Cold-start adds ~30s. |
| `docker/build-push-action` in Actions runner | Simpler config (one YAML). | Builds run on GitHub-hosted runner (egress to AR over public internet). Free Actions minutes have a tighter cap. |

Revisit in V1.5 if Cloud Build cost or latency becomes an issue.

---

## 7. CD Pipeline (GitHub Actions → K3s)

### 7.1 Trigger

The `deploy` job in `ci.yml` runs after `build`:

```yaml
deploy:
  needs: build
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

Auto-deploys every successful build on `main` to the `dev` namespace.

### 7.2 Deploy Method — IAP TCP Tunnel **(D1 RESOLVED)**

The workflow uses GCP IAP TCP tunneling to reach the VM. No port 6443 exposure, no firewall changes per deploy, OIDC WIF handles authentication.

```yaml
- run: |
    gcloud compute ssh meesell-dev \
      --zone=asia-south1-a \
      --tunnel-through-iap \
      --project=${{ env.PROJECT_ID }} \
      --command="<rolling deploy script — see below>"
```

The K3s API stays unreachable from the public internet (still scoped to the founder's ISP CIDR ranges). All deploys flow through the SA's `iap.tunnelResourceAccessor` permission.

**Why not open port 6443 to GitHub IP ranges?** Rejected. The published GitHub Actions IP CIDR set is ~18 blocks, some as wide as `/16`. Opening 6443 to that surface would put the K3s API in reach of every GitHub-hosted runner globally — unacceptable for a cluster serving production traffic. The IAP tunnel adds a single SSH-mediated layer with per-SA IAM control instead.

### 7.3 What the Deploy Script Does (on the VM, inside the IAP-tunneled SSH)

```bash
set -e
IMAGE_TAG=${{ github.sha }}
API_IMAGE=asia-south1-docker.pkg.dev/${PROJECT_ID}/meesell-prod-images/api:${IMAGE_TAG}
FRONTEND_IMAGE=asia-south1-docker.pkg.dev/${PROJECT_ID}/meesell-prod-images/frontend:${IMAGE_TAG}

# 1. Refresh the manifest checkout so any non-app k8s/*.yaml change ships too.
if [ -d ~/mesell/.git ]; then
  git -C ~/mesell fetch origin main && git -C ~/mesell reset --hard origin/main
else
  git clone --depth=1 https://github.com/Mugunthan93/mesell.git ~/mesell
fi

# 2. Apply non-Deployment manifests (ConfigMap, Service, plus Deployments at their current image).
#    kubectl apply is idempotent — no-op if unchanged.
kubectl apply -f ~/mesell/k8s/config.yaml
kubectl apply -f ~/mesell/k8s/api.yaml
kubectl apply -f ~/mesell/k8s/worker.yaml
# kubectl apply -f ~/mesell/k8s/frontend.yaml   # Phase D: enable when frontend image exists.

# 3. Run Alembic migrations on the CURRENT (old) api pod BEFORE rolling the image.
#    Migration-before-deploy: schema changes land first; new code expects the new schema.
kubectl exec -n dev deploy/api -- alembic upgrade head

# 4. Roll the new images.
kubectl -n dev set image deployment/api    api=${API_IMAGE}
kubectl -n dev set image deployment/worker worker=${API_IMAGE}    # worker uses api image
# kubectl -n dev set image deployment/frontend frontend=${FRONTEND_IMAGE}   # gated on frontend image

# 5. Wait for rollouts.
kubectl -n dev rollout status deployment/api    --timeout=180s
kubectl -n dev rollout status deployment/worker --timeout=180s
# kubectl -n dev rollout status deployment/frontend --timeout=180s

# 6. Smoke check.
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.mesell.xyz/health)
if [ "${HTTP_CODE}" != "200" ]; then
  echo "Health check failed: HTTP ${HTTP_CODE}. Rolling back."
  kubectl -n dev rollout undo deployment/api
  kubectl -n dev rollout undo deployment/worker
  exit 1
fi
echo "Deploy complete: ${IMAGE_TAG}"
```

### 7.4 Migration-Before-Deploy Order (Critical)

Schema changes MUST land before the new pod boots:

```
... build complete ...
kubectl apply -f config.yaml + api.yaml + worker.yaml   ← shapes still reference current image
kubectl exec deploy/api -- alembic upgrade head         ← runs on OLD pod, against the live DB
kubectl set image deploy/api api=<new sha>              ← NEW pod boots, expects NEW schema
kubectl rollout status deploy/api                       ← wait for rollout
```

If migration fails, the rollout never starts — fail-safe. If the new pod boots and fails health, `kubectl rollout undo` reverts to the previous SHA without any DB downgrade (forward-compatible migrations only — see §12.2).

### 7.5 Staging / Prod Deploys (Manual)

A separate `workflow_dispatch` workflow (TBD — Phase F deliverable) lets the founder select `environment={staging,prod}` and a SHA. The flow is identical to §7.3 except:
- `kubectl -n {staging|prod} set image ...`
- Smoke check hits `staging.mesell.xyz` or `www.mesell.xyz`

`prod` deploys additionally require a GitHub Environments approval gate ("`prod` deploys require Mugunthan93's review").

### 7.6 D-API-6 Acknowledgement — K3s AR Auth (registries.yaml + cron)

The deploy script implicitly relies on K3s pulling the new image from Artifact Registry. K3s does not bundle a GCR/AR credential helper, so Phase D set up:
- `/etc/rancher/k3s/registries.yaml` with an oauth2accesstoken from the GCE metadata server
- `/usr/local/bin/refresh-ar-token.sh` refreshed every 45 minutes via cron

This is codified in `infra/terraform/modules/vm/templates/startup.sh.tftpl` (Phase E codification, 2026-06-10) — re-provisioned VMs install it automatically. **Production upgrade path:** `kubelet-credential-providers` + `cloud-provider-gcp` `auth-provider-gcp` binary, eliminating the 60-min token window. Tracked as Phase I deliverable.

---

## 8. Secrets Pipeline

Three independent secret stores; each owns a different rotation surface.

```
┌──────────────────────────────────────┐
│  GCP Secret Manager (10 secrets)     │   ← SOURCE OF TRUTH for runtime secrets
│  Owned by: meesell-infra-builder     │
└──────────────────────────────────────┘
            │
            │  gcloud secrets versions access latest   (manual, by infra-builder)
            ▼
┌──────────────────────────────────────┐
│  In-cluster K8s Secret               │
│  `dev/backend-secrets` (20 keys)     │
│  Created by infra-builder, rotated   │
│  on demand via patch + rollout       │
└──────────────────────────────────────┘
            │
            │  envFrom: secretRef
            ▼
┌──────────────────────────────────────┐
│  api + worker Pods                   │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  GitHub Actions secrets              │   ← CI-only, NEVER production values
│  - GEMINI_API_KEY_CI (low-quota key) │
│  Variables (non-secret):             │
│  - GCP_WIF_PROVIDER, GCP_CI_SA_EMAIL │
└──────────────────────────────────────┘
            │
            │  ${{ secrets.X }} / ${{ vars.X }}
            ▼
┌──────────────────────────────────────┐
│  GitHub Actions runner               │
│  (used only for nightly ai_eval +    │
│   for WIF auth setup)                │
└──────────────────────────────────────┘
```

### 8.1 What GitHub Actions Needs

| Name | Type (secret / variable) | Source |
|------|--------------------------|--------|
| `GCP_WIF_PROVIDER` | Variable | `terraform output github_wif_provider_name` |
| `GCP_CI_SA_EMAIL` | Variable | `terraform output github_ci_sa_email` |
| `GEMINI_API_KEY_CI` | Secret | Founder creates a separate low-quota Gemini key for CI ai_eval. Distinct from the prod `gemini-api-key` in GCP SM. |

No other secrets are needed. CI gates 1–3 use dummy values inline in the workflow. Gates 4–5 use ephemeral service-container credentials (postgres/valkey) — not real DB.

### 8.2 What GitHub Actions Does NOT Have Access To

| Secret | Why CI doesn't need it |
|--------|------------------------|
| `jwt-secret` | Tests use a dummy JWT secret; production value stays in GCP SM. |
| `msg91-auth-key`, `msg91-template-id` | Tests don't send real OTPs; they mock the MSG91 client. |
| `razorpay-*` | Tests use webhook signature fixtures, not real Razorpay traffic. |
| `audit-pii-salt`, `refresh-token-pepper` | Tests use dummy salts; production values stay in GCP SM. |
| `langfuse-secret-key` | LangFuse tracing is V1.5; tests don't emit traces. |
| Postgres / Valkey passwords | CI uses ephemeral service containers with weak passwords. |

This is intentional: a leaked GitHub Actions token cannot exfiltrate production credentials, because the production credentials simply aren't there.

### 8.3 Rotation Procedure

**Production secret rotation (e.g. `jwt-secret`):**
```bash
# 1. Generate new value, push as a new SM version (does NOT disable old version)
NEW_JWT=$(openssl rand -hex 64)
printf '%s' "$NEW_JWT" | gcloud secrets versions add jwt-secret \
  --project=project-1f5cbf72-2820-4cdb-949 --data-file=-

# 2. Patch the in-cluster secret
kubectl -n dev patch secret backend-secrets \
  --type='json' \
  -p='[{"op": "replace", "path": "/data/JWT_SECRET", "value": "'$(echo -n "$NEW_JWT" | base64)'"}]'

# 3. Rolling restart picks up the new value
kubectl rollout restart deployment/api -n dev
kubectl rollout restart deployment/worker -n dev

# 4. After 24h with no incidents, disable old SM version
gcloud secrets versions disable <OLD_VERSION_NUMBER> --secret=jwt-secret \
  --project=project-1f5cbf72-2820-4cdb-949
```

**CI secret rotation (e.g. `GEMINI_API_KEY_CI`):**
1. Founder rotates in Google Cloud Console, copies new value
2. Founder updates the GitHub Actions secret `GEMINI_API_KEY_CI` in repo Settings
3. Next nightly run uses the new key — no other action

---

## 9. Frontend Build & Deploy

### 9.1 Current State

| Asset | Status |
|-------|--------|
| `frontend/` Angular sources | EXISTS (Wave 2B in progress) |
| `frontend/Dockerfile` | **MISSING** (Wave 2B not yet completed the Nginx wrapper) |
| `k8s/frontend.yaml` Deployment + Service | EXISTS (Phase D) |
| Frontend image in AR | NOT YET BUILT |
| `dev.mesell.xyz` Ingress | LIVE (cert valid until 2026-09-03) — currently returns 503 because the frontend Service has no backend pods |

### 9.2 Build Pipeline

The `cloudbuild.yaml` frontend step is **conditional** — it precheck-tests for `frontend/Dockerfile` and skips silently if absent:

```yaml
- id: precheck-frontend
  name: bash
  args:
    - -c
    - |
      if [ -f /workspace/src/frontend/Dockerfile ]; then
        touch /workspace/.frontend-buildable
        echo "Frontend Dockerfile present — will build"
      else
        echo "Frontend Dockerfile missing — skipping frontend build"
      fi
  waitFor: [clone]

- id: build-frontend
  name: gcr.io/cloud-builders/docker
  entrypoint: bash
  args:
    - -c
    - |
      if [ ! -f /workspace/.frontend-buildable ]; then
        echo "Skipping frontend build (no Dockerfile)."
        exit 0
      fi
      cd src/frontend
      docker build -t "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend:${_TAG}" \
                   -t "${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/frontend:latest" .
  waitFor: [precheck-frontend]
```

This means the pipeline does not break when frontend isn't ready — Wave 2B can land at its own pace and the next CI run after `frontend/Dockerfile` lands will start producing images.

### 9.3 Frontend Image Shape (recommended pattern for Wave 2B)

Multi-stage Dockerfile with Node 20 build stage → `nginx:alpine` runtime:

```dockerfile
# stage 1 — build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build -- --configuration=production

# stage 2 — runtime
FROM nginx:alpine
COPY --from=build /app/dist/frontend/browser/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`nginx.conf` should set the SPA fallback (`try_files $uri /index.html`) and forward `/api/*` to the api Service if direct routing through Ingress is not used.

### 9.4 Deploy

Once the image exists, the deploy script (§7.3) uncomments the frontend lines. `dev.mesell.xyz` immediately starts serving the SPA after the next push to `main`.

### 9.5 CDN (Deferred to V1.5)

Static hosting via GCS + Cloud CDN is faster and cheaper than Nginx-in-pod but adds a deploy step (push to GCS) and cache-invalidation complexity. Defer until V1 is in production for at least one month.

---

## 10. K8s Manifest Strategy

### 10.1 Current Layout

```
k8s/
├── namespace.yaml       (dev, staging — Terraform-owned, listed here for read-only reference)
├── config.yaml          (ConfigMap meesell-config — flat, dev namespace)
├── api.yaml             (Deployment api + Service api)
├── worker.yaml          (Deployment worker)
├── frontend.yaml        (Deployment frontend + Service frontend — image-pending)
├── secrets.yaml.example (template — never committed populated)
├── ingress.yaml         (DOCUMENTATION-ONLY — superseded by Terraform module.ingress)
├── postgres.yaml        (DOCUMENTATION-ONLY — Terraform StatefulSet)
└── valkey.yaml          (DOCUMENTATION-ONLY — Terraform StatefulSet)
```

Three application Deployments + one ConfigMap + one app Secret are CI-deployable. Datastores, namespaces, Ingress, and certs are Terraform-owned and bypass `kubectl apply`.

### 10.2 [FOUNDER DECISION REQUIRED — D2] Per-Environment Strategy

V1 ships only to `dev`, so the flat layout works. For staging + prod the config must diverge (APP_ENV, CORS origins, possibly replica counts).

| Option | Mechanism | Pro | Con | Recommendation |
|--------|-----------|-----|-----|----------------|
| (a) **Kustomize overlays** | `k8s/base/` + `k8s/overlays/{dev,staging,prod}/` | Clean separation; standard tool; supports JSON patches | Slight learning curve; refactor of current flat layout | **Recommended** for 3+ environments |
| (b) `envsubst` in deploy script | One set of templated YAML + per-env env-file | No refactor needed; simplest mental model | Brittle across env diffs; one typo in the env file breaks staging | Acceptable if staging stays close to dev |

**Default for V1:** start with (b) `envsubst` to keep moving; refactor to (a) Kustomize when `staging` workloads go live (Week 2 of cutover). Document both options here so the founder can pick at staging time.

### 10.3 Image Tag Injection

Both options resolve image tags at deploy time, not commit time:

| Strategy | How |
|----------|-----|
| Kustomize | `kustomize edit set image asia-south1-docker.pkg.dev/.../api=<sha>` then `kubectl apply -k overlays/dev/` |
| envsubst | `IMAGE_TAG=<sha> envsubst < k8s/api.yaml \| kubectl apply -f -` (manifest uses `${IMAGE_TAG}` placeholder) |
| Current Phase D | `kubectl set image deployment/api api=<full image>` (no manifest edit; just patches the live Deployment) |

**Current Phase D approach (`kubectl set image`) is acceptable for V1 dev** because the deploy script does both `kubectl apply` (for non-image changes) AND `kubectl set image` (for the image). The trade-off: the live Deployment can drift from the `k8s/api.yaml` image field. Mitigated by always running both commands every deploy.

---

## 11. Observability Pipeline

### 11.1 Current State (LIVE as of 2026-06-09)

| Capability | Status | Detail |
|------------|--------|--------|
| `/health` endpoint | LIVE | Returns 200 + status JSON (Postgres + Valkey reachability). Used by readiness + liveness probes + deploy smoke check. |
| `/metrics` endpoint | LIVE | Prometheus-format. 7 metrics from §15.J: `http_requests_total`, `http_request_duration_seconds`, `ai_ops_*`, `auth_token_refresh_failed_total`, `image_precheck_*`, `export_xlsx_*`, etc. |
| Pod logs | Captured | `kubectl logs -n dev deploy/api` and `deploy/worker`. No aggregation. |
| Cloud Logging | Implicit | Containerd writes to journald; gcloud VM agent ships to Cloud Logging. Useful for VM-level events but verbose. |

### 11.2 Pending — Phase I (Prometheus + Grafana)

```
monitoring/ (new namespace)
├── Deployment: prometheus
│     - scrape config:
│         - job: api,      target: api.dev.svc.cluster.local:8000/metrics
│         - job: worker,   target: (worker has no HTTP — use celery_queue_depth from api)
│         - job: kube,     kubernetes_sd_configs
│     - PVC: prometheus-data (10Gi local-path)
├── Deployment: grafana
│     - dashboards: meesell-api, meesell-ai-budget, meesell-auth, meesell-celery
│     - PVC: grafana-data (1Gi local-path)
└── Ingress: grafana.mesell.xyz (cert via letsencrypt-prod)
```

Tracked as Phase I.

### 11.3 Alerting Rules (recommended for Phase I)

| Alert | PromQL | Threshold | Action |
|-------|--------|-----------|--------|
| AI daily budget | `sum(ai_ops_inr_spent_today) / on() group_left() ai_ops_daily_budget_inr` | > 0.80 (80%) for 5 min | Slack-ping founder |
| Auth refresh failure | `rate(auth_token_refresh_failed_total[5m])` | > 5 / min | Slack-ping founder + open GitHub issue |
| HTTP 5xx rate | `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | > 0.01 (1%) for 5 min | Slack-ping founder |
| Postgres connection saturation | `pg_stat_database_numbackends / pg_settings_max_connections` | > 0.80 | Slack-ping founder |
| Deploy smoke failure | (sourced from GitHub Actions) | any failure | Slack-ping + auto-rollback (already in deploy script) |

### 11.4 Log Aggregation (Loki) — Deferred to V1.5

`kubectl logs` is sufficient for V1. Loki adds query power but increases infra footprint by ~500MB RAM. Revisit when log volume exceeds what one engineer can grep through.

---

## 12. Rollback & Recovery

### 12.1 Application Rollback (< 30s)

A bad deploy is reverted by:
```bash
kubectl rollout undo deployment/api    -n dev
kubectl rollout undo deployment/worker -n dev
kubectl rollout status deployment/api  -n dev
```

The deploy script already does this automatically if the post-deploy `/health` smoke check fails (§7.3 step 6). For a delayed failure (caught by alerting hours later), the founder runs the commands manually.

### 12.2 DB Migration Rollback

**Forward-compatible migrations** (rule, not optional):
- Adding a column with a default — safe (old code ignores; new code uses).
- Adding a new table — safe.
- Renaming a column — **forbidden** without a 3-step dance (add new column, dual-write, drop old).
- Removing a column — only after one full release of being unused.

Because all migrations are forward-compatible, **rolling back the application image alone is the rollback path 99% of the time.** A schema downgrade is rarely needed.

If a downgrade IS needed:
```bash
# Inspect the migration to revert
kubectl exec -n dev deploy/api -- alembic history --verbose

# Dry-run the downgrade
kubectl exec -n dev deploy/api -- alembic downgrade -1 --sql

# Apply
kubectl exec -n dev deploy/api -- alembic downgrade -1
```

### 12.3 Image Rollback (re-tag prior SHA as `:latest`)

If the bad SHA already moved `:latest`:
```bash
PRIOR_SHA=<the SHA you want to restore>
gcloud artifacts docker tags add \
  asia-south1-docker.pkg.dev/.../api:${PRIOR_SHA} \
  asia-south1-docker.pkg.dev/.../api:latest
```
Then re-run the deploy workflow on the prior commit — or `kubectl set image` directly with the prior SHA.

### 12.4 Full Disaster Recovery

VM snapshot + PVC backup:
- **VM snapshot:** `gcloud compute disks snapshot meesell-dev --zone=asia-south1-a --snapshot-names=meesell-dev-pre-incident-$(date +%Y%m%d)`
- **Postgres backup:** `k8s/backup-cronjob.yaml` (CronJob, runs nightly, writes to `gs://meesell-prod-assets/backups/postgres/<date>.sql.gz`)
- **Valkey backup:** `valkey-cli BGSAVE` + `kubectl cp` (manual; Valkey state is mostly cache, low DR priority)

### 12.5 Rollback Drill (quarterly)

Run a controlled rollback on `dev` once per quarter to verify the procedure still works:
1. Deploy a known-good SHA
2. Tag a deliberate "bad" image (e.g. a previous SHA known to fail smoke)
3. Roll forward to the bad SHA
4. Confirm deploy script auto-rolls back via smoke failure
5. Confirm `/health` returns 200 within 60s of rollback

---

## 13. Implementation Roadmap

| Phase | Work | Owner | Status |
|-------|------|-------|--------|
| **Phase D-pre** | Refresh `INFRASTRUCTURE_ARCHITECTURE.md` SSOT | `meesell-infra-builder` | ✅ DONE (2026-06-05 + 2026-06-10) |
| **Phase D** | Manual first deploy (api+worker live in `dev`) | `meesell-infra-builder` | ✅ DONE (2026-06-09) |
| **Phase D codification** | Terraform state → GCS, codify D-API-5 + D-API-6 | `meesell-infra-builder` | ✅ DONE (2026-06-10) |
| **Phase E** | GitHub Actions WIF setup + Terraform `ci_identity` extension | `meesell-infra-builder` | 🚧 THIS SESSION — Terraform written; founder runs `apply` |
| **Phase F** | Author `cloudbuild.yaml` + `ci.yml` 5-gate + nightly + deploy job | `meesell-infra-builder` | 🚧 THIS SESSION — workflow files written |
| **Phase G** | Frontend Dockerfile + `frontend.yaml` deploy enable | `meesell-frontend-coordinator` for the Dockerfile, `meesell-infra-builder` for the deploy wiring | Not started — gated on Wave 2B Dockerfile |
| **Phase H** | Staging + prod `workflow_dispatch` deploy workflow | `meesell-infra-builder` | Not started — after staging namespace populated |
| **Phase I** | Prometheus + Grafana monitoring namespace | `meesell-infra-builder` | Not started |
| **Phase J** | K3s AR auth production fix (kubelet credential providers) | `meesell-infra-builder` | Not started |
| **Phase K** | Move `terraform apply` into CI (after Layer G + production cutover) | `meesell-infra-builder` | Not started |

### 13.1 Founder Action Items After This Session

In order:
1. Review the Terraform plan output (saved in `STATUS_INFRA.md` update for this session)
2. Run `terraform apply -target=module.ci_identity -var-file=environments/dev.tfvars` from the laptop (account-lock guard will verify the right identity)
3. Run `terraform output github_wif_provider_name` and `terraform output github_ci_sa_email`
4. Set both as **Variables** (NOT Secrets) in GitHub repo Settings → Actions → Variables
5. Generate a low-quota Gemini API key for CI; set as GitHub Secret `GEMINI_API_KEY_CI`
6. Configure branch protection on `main` to require the 5 CI checks
7. Merge this feature branch to `main` — the first push will trigger the full pipeline

### 13.2 Open Decisions Summary

| # | Decision | Status | Recommendation |
|---|----------|--------|----------------|
| D1 | Deploy method | ✅ RESOLVED | IAP TCP tunnel |
| D2 | K8s manifest env strategy | ❓ OPEN | (b) envsubst for V1 → migrate to (a) Kustomize when staging populated |
| D3 | Frontend serving | ✅ RESOLVED | Nginx pod V1; GCS+CDN V1.5 |
| D4 | Workflow file structure | ❓ OPEN — recommended | One `ci.yml` for V1 (the existing stub structure is single-file). Split into separate `ci.yml` / `build.yml` / `deploy.yml` only when promotion workflow lands. |
| D5 | Nightly AI eval trigger | ✅ DOCUMENTED | `GEMINI_API_KEY_CI` as GitHub Secret (low-quota, separate from prod) |
| D6 | GitHub Actions SA | ✅ RESOLVED | Separate `meesell-github-ci` SA (NOT shared with GitLab `meesell-prod-ci`) |
| WIF-1 | WIF attribute condition tightness | ❓ OPEN | (a) Repository-only — recommend for V1; tighten to repo+ref after V1 GA |

---

**End of document. If this conflicts with another doc, this document wins. Update on every pipeline change.**
