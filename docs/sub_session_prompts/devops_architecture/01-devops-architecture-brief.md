# DevOps Architecture — Dispatch Brief

**Agent:** `meesell-infra-builder`
**Session name:** `mesell-devops-architecture-session-1`
**Task type:** Architecture authoring (docs only — no code, no infra changes this session)
**Output:** `docs/DEVOPS_ARCHITECTURE.md` — the single source of truth for MeeSell's
CI/CD, build, deploy, environment, and observability pipeline.

---

## PROJECT BOUNDARY

You are working on project "mesell" at `/Users/mugunthansrinivasan/Project/mesell`.
DO NOT read, write, or reference files outside that path.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).

---

## MISSION

MeeSell's V1 backend construction is complete (§22 accepted 2026-06-09). The next step
is to deploy it and keep it running. Before any deployment work starts, we need a locked
DevOps architecture document that every future session can reference.

Your job this session is to **read, analyse, and author `docs/DEVOPS_ARCHITECTURE.md`**.
No infra changes. No GitHub Actions files yet. Architecture document only.

---

## CRITICAL CONTEXT (read carefully before designing)

### 1. Source control platform: GITHUB (not GitLab)
MeeSell source code lives on **GitHub**, not GitLab.
- The existing `INFRASTRUCTURE_ARCHITECTURE.md` mentions GitLab (`techades/mesell`) and
  a GitLab-based Workload Identity Federation setup — **that WIF is for GitLab and will
  NOT work with GitHub Actions**.
- The `.gitlab-ci.yml` at repo root is a GitLab CI artifact from the backend session.
  It has the right test stages but is the wrong platform. It must be replaced with
  GitHub Actions workflows.
- GitHub Actions Workload Identity Federation (OIDC) requires a **separate WIF provider
  pool** for `token.actions.githubusercontent.com`. The GitLab WIF pool already set up
  (for `gitlab.com`) is a different pool — you cannot reuse it.

### 2. Build constraint: no local Docker
The founder does not build Docker images locally (disk space constraint).
All Docker builds must happen in GCP infrastructure or GitHub Actions runners.
Preferred approach: **GitHub Actions + `docker/build-push-action`** using OIDC WIF to
authenticate to Artifact Registry. No Cloud Build service needed unless GH Actions
build minutes become a concern.

### 3. Existing infra (LIVE — do not break)
- GCP Project: `project-1f5cbf72-2820-4cdb-949`
- VM: `meesell-dev` @ `35.234.223.66`, asia-south1-a, e2-standard-2, 50 GB SSD
- K3s: v1.35.5+k3s1, single-node
- Artifact Registry repo: `meesell-prod-images` (asia-south1)
- K8s namespaces: `dev` (live), `staging` (live — namespace + Ingress + LE cert active, app workloads pending), `prod` (pending)
- GCP Secret Manager: 10 containers, 8 populated, 2 zero-version (`razorpay-webhook-secret`, `langfuse-secret-key`) — see INFRASTRUCTURE_ARCHITECTURE.md §7
- TLS: cert-manager v1.14.5, Let's Encrypt, 5 subdomains live
- Existing GitLab WIF SA: `meesell-prod-ci` — has Artifact Registry Writer + Secret Manager Accessor roles. **NOT reused for GitHub Actions** (see §4 — D6 RESOLVED: separate SA).

### 4. Current Dockerfiles
- `backend/Dockerfile` — API image: python:3.12-slim, gunicorn+uvicorn, port 8000. CLEAN.
- `backend/Dockerfile.worker` — Worker image: has a **V0 CMD** (`-Q scraping,generation,images`).
  V1 Celery only uses `image.precheck` + `export.xlsx` queues (per §18). The CMD must
  be corrected to: `celery -A app.workers.celery_app worker --concurrency=4
  --max-tasks-per-child=100 --loglevel=info` (no `-Q` flag — queue scoping is handled
  by the `INCLUDE` list in `celery_app.py` per §18.B). The Playwright install
  in the worker Dockerfile is also V0 leftover — not needed in V1. Flag this as a
  Dockerfile correction task for the implementation session.

### 5. Existing CI stages (from .gitlab-ci.yml — logic is CORRECT, platform is wrong)
The 6 test stages are well-designed and should be preserved as GitHub Actions jobs:
1. `unit` — `pytest -m "unit"` (no services needed)
2. `smoke` — `pytest -m "smoke"` (no services needed)
3. `lint` — 10 CI contracts (import-linter + 3 AST scanners)
4. `integration` — `pytest -m "integration"` (needs Postgres 16 + Valkey 8 services)
5. `golden_roundtrip` — `pytest -m "golden_roundtrip"` (needs Postgres + Valkey)
6. `nightly` — `pytest -m "slow or perf"` + `pytest -m "ai_eval"` (schedule-only)
All run from `backend/` directory. Secrets injected via env vars — never hard-coded.

### 6. Frontend
Angular 18 app in `frontend/`. Build: `ng build --configuration=production`.
Output: `frontend/dist/`. Deployed as a K8s Deployment serving static files
(or Nginx container). `k8s/frontend.yaml` exists but is not yet wired.
DevOps architecture must include frontend build + deploy pipeline.

---

## WHAT TO READ BEFORE DESIGNING

Read these files in order. Do not start designing until you have read all of them:

1. `.claude/agent-memory/meesell-infra-builder/MEMORY.md` — your own memory
2. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — live infra SSOT (full read)
3. `docs/BACKEND_ARCHITECTURE.md` §19.G (CI gates), §20 (deployment topology) — the
   construction contract sections that define what the pipeline must enforce
4. `docs/MVP_ARCHITECTURE.md` §1 (system topology), §9 (multi-tenancy) — product context
5. `.gitlab-ci.yml` — existing CI stage logic (reuse as GitHub Actions jobs)
6. `k8s/` — all manifest files (understand what gets deployed)
7. `backend/Dockerfile` + `backend/Dockerfile.worker` — images to build
8. `k8s/secrets.yaml.example` — secret injection pattern
9. `docs/status/STATUS_INFRA.md` — current infra state

---

## SCOPE OF THE DEVOPS_ARCHITECTURE.md DOCUMENT

The document must cover all sections below. Use SKELETON → DRAFT → LOCKED protocol
identical to BACKEND_ARCHITECTURE.md. Sections should be numbered §1–§N.

### Required sections

**§1 — Overview & Principles**
- One-paragraph philosophy: immutable images, environment parity, secrets never in code,
  deploy-what-you-tested, rollback in < 2 min
- Platform decisions table (GitHub Actions for CI/CD, GCP Artifact Registry, K3s deploy)

**§2 — Source Control Strategy**
- Repository: GitHub (org/repo name — confirm from git remote)
- Branch model: `main` (production-grade) → feature branches → PRs
- Merge rules: must pass CI gates before merge to main
- Tag strategy: `v{major}.{minor}.{patch}` semver for releases
- Protected branches: main is protected, no direct push

**§3 — Environment Strategy**
- 3 environments: `dev` / `staging` / `prod` (all on same K3s cluster, separate namespaces)
- Promotion path: PR merge to `main` → auto-deploy to `dev` → manual gate → `staging` → manual gate → `prod`
- Environment-specific config: APP_ENV, CORS_ALLOWED_ORIGINS, log levels
- URL mapping: api.mesell.xyz (dev), staging.mesell.xyz (staging), (prod TBD)

**§4 — Workload Identity Federation (GitHub Actions → GCP)**
- WIF Provider: `token.actions.githubusercontent.com` (GitHub OIDC)
- New WIF Pool: `github-actions-pool` (separate from existing GitLab pool)
- New dedicated SA: `meesell-github-ci` — **D6 RESOLVED (founder 2026-06-09): separate account** — do NOT share `meesell-prod-ci` (GitLab SA) with GitHub Actions
- Required SA roles: Artifact Registry Writer + Secret Manager Secret Accessor
- No service account keys — OIDC token exchange only
- Terraform module update required: add `github_wif_provider` to `infra/terraform/modules/ci_identity/`
- ⚠️ **Terraform state is LOCAL** (on founder's laptop) — must migrate to GCS backend BEFORE Phase E runs `terraform apply` in CI. CI runners cannot access local state files.

**§5 — CI Pipeline (GitHub Actions)**
- Trigger: every push + every PR to `main`
- Jobs (sequential gate): `unit` → `smoke` → `lint` → `integration` → `golden_roundtrip`
- Services for integration+: `postgres:16` container + `valkey/valkey:8` container
- Secrets in GH Actions: injected via GitHub Actions Secrets (populate from GCP SM values)
- Caching: pip wheels cached on `requirements.txt` hash
- Workflow file: `.github/workflows/ci.yml`
- The 10 §16.E CI contracts must ALL pass in the `lint` job — this is a hard gate

**§6 — Docker Build Pipeline**
- Trigger: push to `main` after CI passes (on `workflow_run` or in same workflow post-test)
- Builder: `docker/build-push-action` in GitHub Actions (uses OIDC WIF, no local Docker)
- API image: `asia-south1-docker.pkg.dev/<project>/meesell-prod-images/api:<sha>`
- Worker image: `asia-south1-docker.pkg.dev/<project>/meesell-prod-images/worker:<sha>`
- Tag strategy: `sha-<7-char-git-sha>` for every build + `latest` on main + `v{semver}` on tags
- Multi-platform: linux/amd64 only (K3s VM is x86)
- Dockerfile.worker correction: specify the V1 CMD fix required (remove Playwright, fix queues)
- Workflow file: `.github/workflows/build.yml` (or combined with deploy as `ci-cd.yml`)

**§7 — CD Pipeline (GitHub Actions → K3s)**
- Trigger: successful image build on `main` (auto-deploy to `dev`); manual `workflow_dispatch`
  with environment selector for `staging`/`prod`
- Deploy method (recommended): GitHub Actions → **GCP IAP TCP tunnel** → `kubectl` on K3s VM.
  IAP tunnel requires zero firewall changes, zero public exposure of port 6443, and authenticates
  via OIDC WIF (same SA). Command pattern in the deploy job:
  `gcloud compute start-iap-tunnel meesell-dev 6443 --local-host-port=localhost:6443 &`
  then `kubectl --server=https://localhost:6443 set image deploy/meesell-api ...`
- Rejected: opening port 6443 to GitHub Actions IP ranges (~18 CIDR blocks, some /16) —
  unacceptable attack surface for a K3s cluster serving production traffic.
- Alembic migrations: `kubectl exec deploy/meesell-api -- alembic upgrade head` — run BEFORE
  rolling update of new image (migration-before-deploy pattern)
- Health check gate: poll `https://api.mesell.xyz/health` for 200 before marking deploy done
- Rollback: `kubectl rollout undo deploy/meesell-api` if health check fails
- Workflow file: `.github/workflows/deploy.yml`

**§8 — Secrets Pipeline (GCP SM → GitHub Actions → K8s)**
- Source of truth: GCP Secret Manager (10 secrets)
- GitHub Actions: environment secrets populated from GCP SM values (one-time founder action
  per environment; rotation = update GH secret + K8s secret)
- K8s Secret (`backend-secrets`): created by infra-builder from SM values; NOT managed by
  GitHub Actions (static, updated manually on rotation)
- What GitHub Actions secrets need: CI test secrets (DATABASE_URL/VALKEY_URL for integration
  stage — use ephemeral CI Postgres/Valkey, not production), build auth (OIDC WIF — no secret
  needed), deploy auth (OIDC WIF — no secret needed)
- Do NOT inject production secrets into GH Actions — they only need CI-safe values for tests

**§9 — Frontend Build & Deploy**
- Build: `ng build --configuration=production` in GitHub Actions (Node 20)
- Output: `frontend/dist/` → Docker image (Nginx serving static files)
- `k8s/frontend.yaml`: already complete — 47-line Deployment + Service manifest (1 replica, port 80, readiness probe). Only missing the image build. Do NOT rewrite it.
- Subdomain: `dev.mesell.xyz` (dev), `staging.mesell.xyz` (staging)
- CDN: deferred to V1.5 (GCS static hosting or Cloud CDN); V1 serves from Nginx pod

**§10 — K8s Manifest Strategy**
- Where manifests live: `k8s/` directory (current — keep)
- Image tag substitution: use `kustomize` overlays per environment OR simple `sed`/`envsubst`
  in the deploy workflow to inject the built image SHA
- Config per environment: `k8s/config.yaml` has APP_ENV — evaluate using Kustomize patches
  vs separate `k8s/overlays/dev|staging|prod/` directories
- Decision: recommend overlay strategy if 3+ environments; flat `k8s/` acceptable for V1 dev

**§11 — Observability Pipeline**
- Metrics: `/metrics` endpoint is LIVE (Prometheus format, 7 §15.J metrics). Phase D must
  wire a Prometheus scrape config pointing at the api pods.
- Recommended stack: Prometheus + Grafana deployed as K8s pods in a `monitoring` namespace
- Alerting: Grafana alerting for AI budget (ai_ops_budget_alarm_total) + auth failures
  (auth_token_refresh_failed_total) + HTTP error rate (http_requests_total{status_code=~"5.."})
- Log aggregation: deferred to V1.5 (Loki) — V1 uses kubectl logs
- Celery queue depth: `celery_queue_depth` Gauge wired in V1.5 (per metrics.py TODO comment)

**§12 — Rollback & Recovery**
- Application rollback: `kubectl rollout undo` (K8s built-in, zero-downtime)
- DB rollback: Alembic downgrade (document procedure; test with dry-run)
- Image rollback: re-tag a prior SHA as `latest` + re-deploy
- Full DR: VM snapshot + PVC backup (backup-cronjob.yaml exists in k8s/)

**§13 — Implementation Roadmap**
Break implementation into phases. Each phase is a separate meesell-infra-builder dispatch:

| Phase | Work | Dispatch |
|-------|------|----------|
| Phase D-pre | Refresh `docs/INFRASTRUCTURE_ARCHITECTURE.md` SSOT (stale — last updated 2026-06-07, misses §20 deploy topology) | New dispatch |
| Phase D | Manual first deploy (SSH to VM, kubectl) | `01-phase-d-infra-deploy.md` (exists) |
| Phase E | GitHub Actions WIF setup + Terraform module update | New dispatch |
| Phase F | CI workflow (.github/workflows/ci.yml) | New dispatch |
| Phase G | Docker build workflow (.github/workflows/build.yml) | New dispatch |
| Phase H | CD deploy workflow (.github/workflows/deploy.yml) | New dispatch |
| Phase I | Prometheus + Grafana monitoring namespace | New dispatch |
| Phase J | Frontend build + deploy pipeline | New dispatch |

---

## OUTPUT REQUIREMENTS

1. **Produce `docs/DEVOPS_ARCHITECTURE.md`** — use the same quality bar as
   `docs/BACKEND_ARCHITECTURE.md`. Every section: SKELETON → DRAFT → present to
   master for LOCK decision before moving to next.

2. **Flag open decisions** — anywhere the architecture has 2+ valid options, document
   both and mark with `[FOUNDER DECISION REQUIRED]`. Do not pick unilaterally on
   security-affecting or cost-affecting choices.

3. **Do NOT:**
   - Create any GitHub Actions workflow files yet
   - Run any Terraform commands
   - Touch `docs/BACKEND_ARCHITECTURE.md` (§5.0 is permanent)
   - Modify any K8s manifests
   - Make any git commits (architecture document only — founder reviews first)

4. **Agent dispatch rule**: All implementation phases (D-pre through J) MUST use
   `meesell-infra-builder` exclusively. NEVER dispatch `nexus:level-*`, `general-purpose`,
   or any non-`meesell-*` agent for MeeSell work.

5. **After producing the document**, append an `=== UPDATE ===` block to
   `docs/status/STATUS_INFRA.md` with: "DEVOPS_ARCHITECTURE.md drafted — N sections,
   M open decisions, ready for founder review." Update your own memory at
   `.claude/agent-memory/meesell-infra-builder/MEMORY.md`.

---

## KEY OPEN DECISIONS (pre-identified — architect must make recommendations)

| # | Decision | Options | Recommendation hint |
|---|----------|---------|-------------------|
| D1 | Deploy method: K3s API access from GH Actions | (a) **IAP TCP tunnel** (recommended); (b) Open port 6443 to GH IP ranges | (a) IAP — no firewall changes, no public port exposure, OIDC WIF auth handles everything |
| D2 | K8s manifest env strategy | (a) Flat `k8s/` + envsubst; (b) Kustomize overlays | (b) for 3 environments |
| D3 | Frontend serving | (a) Nginx pod in K3s; (b) GCS static + Cloud CDN | (a) for V1 simplicity |
| D4 | Build + deploy workflow structure | (a) 3 separate workflows (ci / build / deploy); (b) 1 combined ci-cd.yml | (a) cleaner separation |
| D5 | Nightly AI eval trigger | GitHub Actions schedule cron; needs GEMINI_API_KEY in GH Secrets | must document secret injection |
| D6 | GitHub Actions CI SA | (a) Reuse `meesell-prod-ci` (GitLab SA); (b) New dedicated `meesell-github-ci` | **✅ RESOLVED — (b) separate account** (founder decision 2026-06-09) |

---

## AUTHORED BY

Master session (mesell-master-session-2), 2026-06-09.
