# CI/CD Dev Pipeline — Dispatch Brief

**Agent:** `meesell-infra-builder`
**Session name:** `mesell-cicd-session-1`
**Task type:** Architecture authoring + implementation
**Outputs:**
- `docs/DEVOPS_ARCHITECTURE.md` — locked CI/CD architecture SSOT
- `.github/workflows/ci.yml` — corrected and completed (was a partial stub)
- `cloudbuild.yaml` — Cloud Build config (referenced by ci.yml build job, does not exist yet)
- `infra/terraform/modules/ci_identity/` — GitHub WIF pool + `meesell-github-ci` SA added

---

## PROMPT

```
You are meesell-infra-builder. You are operating on the MeeSell project.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch meesell-* agents. NEVER dispatch nexus:level-*, general-purpose, or Explore.

---

MISSION: CI/CD Dev Pipeline — Phase E through H.

Phase D deployed the V1 backend manually (direct kubectl apply, direct gcloud builds submit).
There is no automated CI/CD pipeline. Your job this session is to close that gap:

  1. Author docs/DEVOPS_ARCHITECTURE.md (all 13 sections)
  2. Fix and complete .github/workflows/ci.yml (existing stub has errors — see below)
  3. Create cloudbuild.yaml at repo root (referenced by ci.yml build job — does not exist)
  4. Extend infra/terraform/modules/ci_identity/ with GitHub Actions WIF pool + new SA

---

BEFORE STARTING — read these files in order:
1. .claude/agent-memory/meesell-infra-builder/MEMORY.md — your own memory
2. docs/sub_session_prompts/cicd_implementation/01-cicd-dev-pipeline-brief.md — FULL READ
   (this is your complete design contract — every decision is in this file)
3. .github/workflows/ci.yml — existing stub FULL READ before editing
4. .gitlab-ci.yml — 6-stage test logic to replicate as GitHub Actions jobs
5. infra/terraform/modules/ci_identity/main.tf — existing GitLab WIF module to extend
6. infra/terraform/variables.tf — variable patterns to follow
7. infra/terraform/main.tf — module invocation patterns
8. infra/terraform/backend.tf — state config (LOCAL — do not change in this session)
9. docs/INFRASTRUCTURE_ARCHITECTURE.md — live infra SSOT
10. docs/status/STATUS_INFRA.md — current state including Phase D D-flags
11. k8s/ — all manifest files (understand namespace=dev, deployment names, image names)

---

ERRORS IN EXISTING ci.yml — fix all of these:
- VM_NAME: meesell-vm  →  meesell-dev
- kubectl -n meesell   →  kubectl -n dev
- REPO: meesell-images →  meesell-prod-images
- python-version: "3.11" → "3.12"
- Single test job → expand to 5 sequential gates:
    unit (pytest -m "unit", no services)
    smoke (pytest -m "smoke", no services)
    lint (import-linter + 3 AST scanners, no services)
    integration (pytest -m "integration", needs postgres:16 + valkey:8)
    golden_roundtrip (pytest -m "golden_roundtrip", needs postgres:16 + valkey:8)
- Add nightly job: cron '0 1 * * *', runs pytest -m "slow or perf" + pytest -m "ai_eval",
  needs GEMINI_API_KEY GitHub Actions secret, only fires on schedule event

---

cloudbuild.yaml MUST:
- Clone repo (--no-source is used in the gcloud builds submit command)
- Build backend/Dockerfile → asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:${_TAG}
- Build backend/Dockerfile.worker → same registry/worker:${_TAG}
- Tag both as :latest
- Push both
- Build frontend/ (Angular ng build --configuration=production → Nginx image → frontend:${_TAG})
  NOTE: frontend/ does not exist yet — make this step conditional (skip if absent, do not fail)

---

TERRAFORM — extend ci_identity module (DO NOT run terraform apply):
- New WIF pool: github-actions-pool, issuer https://token.actions.githubusercontent.com
- New SA: meesell-github-ci (SEPARATE from meesell-prod-ci — founder decision D6)
- SA roles: artifactregistry.writer + secretmanager.secretAccessor + iap.tunnelResourceAccessor
  + compute.instanceAdmin.v1 (scoped to meesell-dev VM)
- WIF attribute condition: restrict to Mugunthan93/mesell repo only
- New variables.tf entries: github_repository, github_ci_service_account_id
- New outputs: github_wif_provider_name, github_ci_sa_email
- ALSO codify D-API-5 Cloud Build SA perms (see brief §4 for exact IAM bindings)
- Run terraform plan -var-file=environments/dev.tfvars and capture output — DO NOT apply

---

CRITICAL CONSTRAINTS:
- DO NOT run terraform apply (state is local — founder runs it manually)
- DO NOT modify the GitLab WIF pool (gitlab-prod-pool) or GitLab SA (meesell-prod-ci)
- DO NOT push to main branch — work on the current feature branch
- DO NOT touch docs/BACKEND_ARCHITECTURE.md
- DO NOT modify any k8s/ manifests

---

SUCCESS CRITERIA:
- docs/DEVOPS_ARCHITECTURE.md created (all 13 sections)
- .github/workflows/ci.yml corrected (5 CI gate jobs + nightly + all values fixed)
- cloudbuild.yaml created at repo root
- infra/terraform/modules/ci_identity/ extended (GitHub WIF + meesell-github-ci SA)
- infra/terraform/variables.tf updated (new variables)
- terraform plan captured, no apply
- docs/status/STATUS_INFRA.md updated with === UPDATE === block
- .claude/agent-memory/meesell-infra-builder/MEMORY.md updated

Full design context: docs/sub_session_prompts/cicd_implementation/01-cicd-dev-pipeline-brief.md
```
- `infra/terraform/variables.tf` — new variables for GitHub WIF

---

## PROJECT BOUNDARY

You are working on project "mesell" at `/Users/mugunthansrinivasan/Project/mesell`.
DO NOT read, write, or reference files outside that path.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch `meesell-*` agents. NEVER dispatch `nexus:level-*` or `general-purpose`.

---

## MISSION

Phase D deployed the V1 backend manually (direct `kubectl apply`, direct Cloud Build submit).
There is no automated CI/CD pipeline for the dev environment. This session closes that gap:

1. **Author `docs/DEVOPS_ARCHITECTURE.md`** — the locked CI/CD architecture document
2. **Complete `.github/workflows/ci.yml`** — fix errors in the existing stub, expand to full 5-stage CI + nightly schedule
3. **Create `cloudbuild.yaml`** — the Cloud Build config referenced by the build job
4. **Extend Terraform `ci_identity` module** — add GitHub Actions WIF pool + new `meesell-github-ci` SA

After this session, every push to `main` triggers: test → build → deploy automatically.

---

## CRITICAL CONTEXT

### 1. The existing ci.yml is a stub — do not delete, fix it
`.github/workflows/ci.yml` exists and has the right structure (test → build → deploy) but contains errors:

| Error | Wrong value | Correct value |
|-------|-------------|---------------|
| VM name | `meesell-vm` | `meesell-dev` |
| K8s namespace | `kubectl -n meesell` | `kubectl -n dev` |
| Artifact Registry repo | `REPO: meesell-images` | `REPO: meesell-prod-images` |
| Python version | `3.11` | `3.12` |
| Test structure | Single job running all tests | 5 sequential gates (see §5 below) |
| Missing | no nightly schedule | add separate nightly workflow or job |

Read the full file before editing. The WIF provider and SA email placeholders
(`${{ vars.GCP_WIF_PROVIDER }}`, `${{ vars.GCP_CI_SA_EMAIL }}`) are correct — keep them.

### 2. cloudbuild.yaml does not exist — create it
The build job in ci.yml does:
```yaml
gcloud builds submit --no-source \
  --config=cloudbuild.yaml \
  --substitutions=_PROJECT_ID=...,_REGION=...,_REPO=...,_TAG=${{ github.sha }}
```
You must create `cloudbuild.yaml` at repo root. It must:
- Clone the repo (git clone step — since `--no-source` is used)
- Build `backend/Dockerfile` → `asia-south1-docker.pkg.dev/${_PROJECT_ID}/meesell-prod-images/api:${_TAG}`
- Build `backend/Dockerfile.worker` → `...worker:${_TAG}` (same registry)
- Also tag both as `:latest`
- Push both images
- Build `frontend/` (Angular 21 + `ng build --configuration=production`) → Nginx image → push as `frontend:${_TAG}`
  NOTE: `frontend/` directory does not exist yet — add a conditional check so the build does not fail if frontend is absent

### 3. GitHub Actions WIF — new SA, new pool (D6 RESOLVED)
The existing Terraform `ci_identity` module creates `meesell-prod-ci` SA + `gitlab-prod-pool`
(GitLab OIDC). This SA and pool are for GitLab CI and must NOT be modified.

For GitHub Actions you must add to the same module:
- New WIF pool: `github-actions-pool` with issuer `https://token.actions.githubusercontent.com`
- New SA: `meesell-github-ci` (short ID) — **separate account, founder decision D6 confirmed**
- SA roles needed:
  - `roles/artifactregistry.writer` on `meesell-prod-images` repo
  - `roles/secretmanager.secretAccessor` on the GCP project (for CI test secrets)
  - `roles/iap.tunnelResourceAccessor` on the `meesell-dev` VM (for IAP SSH deploy)
  - `roles/compute.instanceAdmin.v1` scoped to `meesell-dev` VM (for gcloud compute ssh)
- WIF attribute condition: restrict to `Mugunthan93/mesell` repository only

Add new variables to `variables.tf`:
- `github_repository` (string, default: `"Mugunthan93/mesell"`)
- `github_ci_service_account_id` (string, default: `"meesell-github-ci"`)

### 4. Cloud Build SA quirk (D-API-5) — must be in Terraform
Phase D discovered: Cloud Build in this project runs as the **Compute Engine default SA**
(`888244156264-compute@developer.gserviceaccount.com`), NOT the standard Cloud Build SA.

These permissions were granted MANUALLY during Phase D — they must be codified in Terraform:
- `roles/storage.admin` on GCS bucket `gs://project-1f5cbf72-2820-4cdb-949_cloudbuild`
  → member: `888244156264-compute@developer.gserviceaccount.com`
- `roles/artifactregistry.writer` on `meesell-prod-images` repo
  → member: `888244156264-compute@developer.gserviceaccount.com`

Add these as `google_storage_bucket_iam_member` and `google_artifact_registry_repository_iam_member`
resources in the `ci_identity` module (or a new `cloudbuild_permissions.tf` file in root).

### 5. CI test stages — expand from 1 job to 5 sequential gates
The existing ci.yml has a single `test` job running `pytest tests/`. Replace it with 5 jobs
matching the 6 stages in `.gitlab-ci.yml`:

```
unit → smoke → lint → integration → golden_roundtrip
```

Each job needs:
- `unit`: `pytest -m "unit"` — no services (postgres/valkey not needed)
- `smoke`: `pytest -m "smoke"` — no services
- `lint`: `python -m import_linter` + 3 AST scanners (see `.gitlab-ci.yml` for exact commands) — no services
- `integration`: `pytest -m "integration"` — needs postgres:16 + valkey:8 services
- `golden_roundtrip`: `pytest -m "golden_roundtrip"` — needs postgres:16 + valkey:8 services

All run from `backend/` working directory.

**Nightly job** (separate from the main CI run):
- Trigger: schedule (`cron: '0 1 * * *'` — 1 AM UTC = 6:30 AM IST)
- Jobs: `pytest -m "slow or perf"` + `pytest -m "ai_eval"` (needs postgres + valkey)
- Requires `GEMINI_API_KEY` injected from GitHub Actions secret (CI-safe value, not production key)
- Add to ci.yml as a separate job block with `if: github.event_name == 'schedule'`

### 6. Terraform state is LOCAL — do not run terraform apply in CI yet
Terraform state lives at `infra/terraform/terraform.tfstate` on the founder's laptop.
The state GCS migration is a separate session (see Dispatch 2).

For this session: make all Terraform MODULE changes (add GitHub WIF resources),
but do NOT add `terraform apply` to the GitHub Actions workflow.
After the Terraform migration session completes (GCS state), the CI pipeline
can add a `terraform plan` check.

Document in `docs/DEVOPS_ARCHITECTURE.md` that `terraform apply` is a founder-only
manual step until state migrates to GCS.

### 7. GitHub repository settings — document but do not automate
After `terraform apply` (founder runs locally), the founder must set these GitHub
repository variables in Settings → Secrets and variables → Actions → Variables:
- `GCP_WIF_PROVIDER` — output of `terraform output github_wif_provider_name`
- `GCP_CI_SA_EMAIL` — output of `terraform output github_ci_sa_email`

Document this as a one-time founder action in `docs/DEVOPS_ARCHITECTURE.md` §4.

---

## WHAT TO READ BEFORE STARTING

Read in order — do not start writing until all are read:

1. `.claude/agent-memory/meesell-infra-builder/MEMORY.md` — your own memory
2. `docs/sub_session_prompts/devops_architecture/01-devops-architecture-brief.md` — the full DevOps architecture spec (your design contract for `docs/DEVOPS_ARCHITECTURE.md`)
3. `.github/workflows/ci.yml` — existing stub (FULL READ before editing)
4. `.gitlab-ci.yml` — 6-stage test logic to replicate (FULL READ)
5. `infra/terraform/modules/ci_identity/main.tf` — existing GitLab WIF module to extend
6. `infra/terraform/variables.tf` — variable patterns to follow
7. `infra/terraform/main.tf` — module invocation patterns
8. `infra/terraform/backend.tf` — state config (LOCAL — do not change in this session)
9. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — live infra SSOT
10. `docs/status/STATUS_INFRA.md` — current state including Phase D D-flags
11. `k8s/` — all manifest files (understand namespace = `dev`, deployment names, image names)

---

## SESSION ACTION PLAN

### Part 1 — Architecture document
Author `docs/DEVOPS_ARCHITECTURE.md` using the design brief in
`docs/sub_session_prompts/devops_architecture/01-devops-architecture-brief.md`.

All 13 sections required. Use SKELETON → DRAFT → LOCKED protocol.
Mark any remaining open decisions with `[FOUNDER DECISION REQUIRED]`.

D6 is already RESOLVED (separate account). D1 is already RESOLVED (IAP tunnel).
Remaining open decisions: D2, D3, D4 — document recommendations, let founder confirm.

### Part 2 — Fix .github/workflows/ci.yml
Apply all corrections from the table in §1 above.
Expand test job into 5 sequential gate jobs.
Add nightly schedule block.
Keep the build and deploy job structure — fix values only.

### Part 3 — Create cloudbuild.yaml
Create at repo root. Must handle:
- API image build + push (always)
- Worker image build + push (always)
- Frontend image build + push (conditional — only if `frontend/` exists)
- Tag strategy: `sha-<7-char-sha>` + `:latest` on both

### Part 4 — Extend Terraform ci_identity module
Add GitHub WIF pool + SA + roles as described in §3 above.
Do NOT modify the existing GitLab WIF resources — only add new resources.
Add new outputs: `github_wif_provider_name`, `github_ci_sa_email`.
Add new variables to `variables.tf`.

**DO NOT run `terraform apply`** — output the plan for founder review only.
Run: `cd infra/terraform && terraform plan -var-file=environments/dev.tfvars` and capture output.

---

## OPEN DECISION BLOCKERS

The following decisions block `terraform apply` — flag them for the founder:

| # | Decision | Options | Recommendation |
|---|----------|---------|---------------|
| WIF-1 | GitHub repo attribute condition | (a) Any branch in `Mugunthan93/mesell`; (b) `main` branch only | (a) any branch — CI runs on PRs too |
| IAP-1 | IAP SSH deploy target | `meesell-dev` VM (dev namespace only) | Confirmed — same as Phase D |

---

## DO NOT

- Run `terraform apply` (state is local — founder must run it)
- Modify the GitLab WIF pool (`gitlab-prod-pool`) or GitLab SA (`meesell-prod-ci`)
- Push to `main` branch (architecture + workflow changes go on a feature branch for founder review)
- Touch `docs/BACKEND_ARCHITECTURE.md`
- Modify any K8s manifests
- Make any changes to the K3s cluster or GCP VM

---

## OUTPUT REQUIREMENTS

1. `docs/DEVOPS_ARCHITECTURE.md` — complete, all 13 sections
2. `.github/workflows/ci.yml` — corrected + expanded
3. `cloudbuild.yaml` — created at repo root
4. `infra/terraform/modules/ci_identity/main.tf` — extended with GitHub WIF resources
5. `infra/terraform/variables.tf` — new GitHub WIF variables added
6. `infra/terraform/outputs.tf` (or module outputs) — `github_wif_provider_name` + `github_ci_sa_email`
7. Terraform plan output captured (do not apply)
8. Append `=== UPDATE ===` block to `docs/status/STATUS_INFRA.md`
9. Update own memory at `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

---

## D-FLAGS FROM PHASE D TO RESOLVE IN THIS SESSION

| Flag | Action Required |
|------|----------------|
| D-API-5 | Add Cloud Build Compute SA permissions to Terraform (`ci_identity` module) |
| D-API-6 | Document `registries.yaml` + cron in `docs/DEVOPS_ARCHITECTURE.md` §7 (acknowledged pattern for dev; production fix in Phase I) |

---

## AUTHORED BY

Master session (mesell-master-session-2), 2026-06-10.
Triggered by: Phase D deployment gap review — no automated CI/CD.
