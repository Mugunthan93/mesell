# Feature Board — Infra Lead

**Lead agent:** `meesell-infra-builder`
**Domain:** infra
**Last updated:** 2026-06-11 (ci-activation — DEPLOY-to-K3s job REACHED for the first time; 3 root causes peeled + fixed; live dev rollout GREEN (api 2/2 + worker 2/2 on def60521, /health 200); fix branch fix/ci-deploy-k3s → develop awaiting founder develop→main)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| ci-activation | fix/ci-deploy-k3s (→ develop) | IN REVIEW | — | 2026-06-11 | FOUNDER develop→main merge to ship the manifest + ci.yml deploy fixes (deploy job clones origin/main). NOT a code blocker — fix verified live by hand. | **DEPLOY-to-K3s job REACHED for the FIRST time + all 3 first-run gaps fixed.** Prior: run 27358799380 (PR #114, 88c585bd) RED at deploy on `compute.projects.get` → founder granted compute.viewer live + codified PR #116 → run **27360475090** (def60521): Gates 1-5 ALL ✅, Frontend 8/8 ✅, **Build ✅** (act-as PR #113 working), deploy got PAST auth, RED at `rollout status timed out`. **3 root causes peeled:** (1) `compute.projects.get` 401 — instance-scoped instanceAdmin lacks project read; FIXED PR #116 (`github_ci_compute_viewer`=roles/compute.viewer read-only) already on main. (2) `ImagePullBackOff 401` — K3s registries.yaml AR token 46h STALE; 45-min refresh CRON was never installed on live VM; FIXED: installed `/etc/cron.d/refresh-ar-token` (root user field) + refreshed token + restarted k3s (reads file only at startup). (3) rollout deadlock — `maxSurge:1/maxUnavailable:0` can't fit a surge pod on CPU-saturated single node; FIXED: flipped api+worker to `maxSurge:0/maxUnavailable:1` (kill-before-surge). ci.yml hardened with deploy-time token-refresh+k3s-restart+readyz-wait. **Live dev now GREEN by hand:** api 2/2 + worker 2/2 on def60521; `https://api.mesell.xyz/health`→200 pg+valkey ok. Repo changes (manifest flip + ci.yml) on `fix/ci-deploy-k3s`→PR develop; effective on next deploy after FOUNDER merges develop→main. Cost ₹0. |
| auth-otp | feature/auth-otp/infra | IN REVIEW | — | 2026-06-11 | — | FE-D5 env-var wiring (dev=30/120; staging overlay=60/300) + auth-secret-rotation runbook. Base=feature/auth-otp/integration. |
| mfe-cutover | feature/mfe-cutover/infra | IN REVIEW | — | 2026-06-11 | founder cost gate for D13 hosting (~₹1,600-1,800/mo >₹500/mo) — NOT a merge blocker (R-SP7-4); dev CSP smoke joint w/ frontend+backend | SP07 infra group (FIRST two-group sub-plan; frontend lead runs joint merge gate). CSP mechanism (D42) = nginx add_header in shell image (PRIMARY) + Traefik CSP-only Middleware (ALT), both ADD-ONLY-validated (no CORS/Set-Cookie strip — R-SP7-1 P0). Dev CSP smoke procedure (A remote-load + B 401→refresh→retry + C CORS) authored. Staging/prod cutover gated on dev-smoke-GREEN. D13 hosting work-package + cost sheet PREPARED, NOT PROVISIONED (founder cost gate). C-CI-1 matrix → all 6 remotes + D43 shell glob; cloudbuild version-pinned `{env}/mfe-<name>/{version}` (no latest, R-SP7-6). Branch cut from origin/develop (integration branch not yet created by FE lead — see handoff_mf_cutover.md NOTE). Files: frontend/docker/{nginx.conf.template,csp-policy.env,docker-entrypoint.sh,Dockerfile.shell}, k8s/csp/csp-middleware.yaml, docs/plans/infra/{SP07_CSP_AND_HOSTING.md,SP07_HOSTING_COST_SHEET.md}, .github/workflows/ci.yml, cloudbuild.yaml, docs/DEVOPS_ARCHITECTURE.md §9. Cluster unreachable → yaml.safe_load_all offline-validated; server dry-run deferred (playbook §15). Cost authored ₹0; provisioning gated. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| dual-pepper-secret-refs | develop | 2026-06-11 | #69 (squash) | R5 inter-lead (from backend PR #65/#66) RESOLVED. Added REFRESH_TOKEN_PEPPER_PREVIOUS+VERSION to k8s/secrets.yaml.example + SM onboarding note in INFRASTRUCTURE_ARCHITECTURE.md §4 (NOT new SM secrets — PREVIOUS=prior pepper SM version kept ENABLED during grace window per runbook §2; VERSION=operator int). Docs/example only, no cluster/SM ops. Cost ₹0. |
| mf-ci-c-ci-1 | develop | 2026-06-11 | #50 (squash 86e67c8) | C-CI-1 DISCHARGED-pending-activation: ci.yml frontend paths-filter matrix (shell + mfe-pricing pilot, libs fan-out) REPLACING single-frontend conditional; cloudbuild shell-image + INERT GCS remote publish (`_REMOTES_BUCKET`). Config+docs only. Cost ₹0. |
| auth-otp | feature/auth-otp/integration | 2026-06-11 | #45 (squash d2b734e) | FE-D5 env wiring (dev=30/120; staging overlay=60/300) + auth-secret-rotation runbook. Founder-flags F1 (APP_ENV), F2 (single-pepper backend follow-up), F3 (dry-run-server at deploy). Cost ₹0. |
| gate4-confirmation | develop | 2026-06-10 | #33 (merge f30d61f) | MF §9 Gate 4 hosting confirmation — VERDICT CONFIRMED-WITH-CONDITIONS (6 conditions feed Sub-plan 7) |
| housekeeping-v1 | feature/housekeeping-v1 | 2026-06-10 | #27 (squash 6096244) | dead GitLab CI removal + SA key disk hygiene |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| frontend-coordinator (incoming) | mf-workspace-foundation | MF CI prep C-CI-1 (handoff_mf_ci_prep.md) — replace single-frontend CI with paths-filter matrix before SP1 | 2026-06-10 | RESOLVED via PR #50 (merged develop) — frontend lead marks CLOSED on its own board |
| frontend-coordinator (incoming) | mfe-cutover | SP07 cutover infra (spec_sp07_infra.md + handoff_mf_auth_deploy.md R-SP6-6/C-CSP-1): CSP ADD-ONLY mechanism (D42) + dev smoke + per-env manifest templating + the 4 infra-side Gate-4 C-conditions + D13 hosting work-package. Delivered on feature/mfe-cutover/infra (PR to integration); my content sign-off in handoff_mf_cutover.md. CSP=nginx add_header (primary)+Traefik Middleware (alt), both ADD-ONLY. Hosting NOT provisioned — founder cost gate (~₹1,600-1,800/mo). FE lead runs joint merge gate + collates Gate-4 discharge. | 2026-06-11 | OPEN — FE lead marks CLOSED on its own board when SP07 ships dev-validated CSP + the hosting wave (post cost-gate) |
| backend-coordinator | ci-activation | First main pipeline RED — Gate 1 `pytest -m unit` fails at COLLECTION: `from app.shared.database import` → `ModuleNotFoundError: No module named 'app'`. CI runs `pytest` in `working-directory: backend` with no PYTHONPATH and no installable pkg (`pytest.ini` §19.D LOCKED has no `pythonpath`; no pyproject/setup.py). Fix is backend-owned: add `pythonpath = .` to pytest.ini (founder OK — §19.D locked) OR add pyproject/setup.py + `pip install -e .`. See handoff_ci_gate1_collection.md. | 2026-06-11 | RESOLVED — backend pythonpath fix (#73/#74) closed collection; infra PR #76 (0f44d72) closed the resulting §5.D env-guard gap. Both sides done. |
| backend-coordinator | ci-activation | §19.D gate markers (`unit`/`smoke`/`integration`/`golden_roundtrip`/`slow`/`perf`/`ai_eval`) are REGISTERED in pytest.ini but applied to ZERO of 823 tests (0 files match `pytest.mark.<m>` for all 7; no `pytest_collection_modifyitems` hook). `pytest -m "unit"` selects 0 → exit 5 → RED. SYSTEMIC across all marker-gated gates + nightly; fixing only `unit` just moves red to Gate-2. Fix backend-owned: tag the suite per §19.D bucket (explicit `@pytest.mark` OR conftest auto-marking hook), complete across all buckets so each gate selects >0. First seen on PR #78 run 27320321536; RE-CONFIRMED on the develop trigger path — push run 27320468096 RED at Gate-1 exit-5. See handoff_ci_gate_markers.md. | 2026-06-11 | RESOLVED via PR #85 (`34d8b47`, merged develop) — 823 tests now §19.D-tagged; run 27323036548 Gates 1-3 GREEN. Backend marks CLOSED on its own board. |
| backend-coordinator | ci-activation | Gate 4 (integration) RED on run 27323036548 — `21 failed, 23 passed, 151 errors`. Backend test-harness (`backend/tests/conftest.py`) does not honor the CI-provided `TEST_DATABASE_URL`/`TEST_VALKEY_URL` for its live/dev fixtures: `_DEV_DATABASE_URL` (L56-58) hardcodes the K3s-dev cluster password on 5433/db `meesell` (only `DEV_DATABASE_URL`-overridable) → `asyncpg InvalidPasswordError`; live-Redis fixtures (L183/398) default `CORE_TEST_VALKEY_URL=localhost:6379` (CI maps Valkey to 6381) → `redis.ConnectionError`; integration DB setup lacks `CREATE EXTENSION pg_trgm` + migrations/seed → `gin_trgm_ops`/`categories does not exist`; plus async loop-scope + `assert 2==1`/`assert 200==429` logic bugs. The infra ci.yml Gate-4 service+env block is CORRECT (verified) — fix is backend (conftest honors TEST_* + pg_trgm + seed + loop/assert fixes). See handoff_ci_gate4_integration.md. | 2026-06-11 | RESOLVED — 4 backend PRs (#104/#107/#108/#110) merged to develop; Gate 4 GREEN on run 27331720017. Backend marks CLOSED on its own board. |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/infra` branch exists; lead is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead self-review approval. |
| `MERGED` | The infra group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until the infra group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval criteria live in the infra PR template at `.github/PULL_REQUEST_TEMPLATE/infra.md`. The lead approves a `feature/{name}/infra` → `feature/{name}` PR only when the template is filled completely — including the `terraform plan` output (`Plan: X to add, Y to change, Z to destroy`), `kubectl apply --dry-run=server` clean output, secret refs documented with no JSON keys, Workload Identity Federation paths confirmed, smoke deploy to `dev` succeeded (`kubectl get pods -n dev` Ready), cost impact estimate recorded (with explicit founder sign-off for any change > ₹500/month) — plus CI gate-3 (lint — manifest validation) green and the rollback procedure for the resource type documented per `docs/INFRASTRUCTURE_PLAYBOOK.md`.
