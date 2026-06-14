---
name: meesell-ci-activation
description: CI activation session-1 (2026-06-11). TF applied Phase E; github-actions-pool + meesell-github-ci SA live; PR #64 open; GEMINI secret + check-contexts pending.
metadata:
  type: project
---

# MeeSell CI Activation — Session 1 (2026-06-11)

## What was done

**Terraform apply (Phase E) — COMPLETE:**
- WIF pool: `github-actions-pool` (pool ID) with OIDC provider `github-actions-provider`
- SA: `meesell-github-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`
- IAM roles: AR writer, Cloud Build editor, Secret Manager accessor, IAP tunnel, VM-scoped instanceAdmin (meesell-dev only)
- APIs enabled: cloudbuild (adopt), iap (new)
- WIF → SA impersonation binding scoped to `Mugunthan93/mesell` repo
- GCS state serial after apply: 119+

**GitHub variables updated:**
- `GCP_WIF_PROVIDER` → `projects/888244156264/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider`
- `GCP_CI_SA_EMAIL` → `meesell-github-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`
- Updated 2026-06-11 (replaced 2026-05-31 out-of-band values pointing to `github-pool` + `meesell-ci`)

**Legacy orphans (harmless, NOT deleted):**
- WIF pool `github-pool` with provider `github-oidc` — out-of-band, pre-existing, still ACTIVE
- SA `meesell-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com` — out-of-band, still exists
- These can be deleted in a future cleanup session: `gcloud iam workload-identity-pools delete github-pool --location=global --project=...` + SA delete

## Pending founder actions

1. **`GEMINI_API_KEY_CI` GitHub secret** — nightly-job-only, NOT blocking first run. Founder creates low-quota key at aistudio.google.com/apikey and sets via `gh secret set GEMINI_API_KEY_CI`.

2. **Merge PR #64** (develop → main) — fires the first pipeline. URL: https://github.com/Mugunthan93/mesell/pull/64

3. **Branch protection check contexts** — DEFERRED until after first run. Expected context names:
   - "CI Gate 1: unit"
   - "CI Gate 2: smoke"
   - "CI Gate 3: lint (10 contracts)"
   - "CI Gate 4: integration"
   - "CI Gate 5: golden_roundtrip"
   - "Frontend: detect changed workspace units"
   - "Frontend: shell"
   - "Frontend: mfe-pricing"
   Add to main (and staging/develop) branch protection after verifying them from the first pipeline run.

## Why: backend tests may fail on first run

The backend test suite has known issues from the knowledge-sync audit:
- `test_config.py` imports `app.shared.config` but `app.config` was the old path — 5 tests likely fail
- Lint gate (import-linter + AST scanners) depends on `tests/lint/` files existing

If the first run is RED, the infra-builder will diagnose. The likely fix is backend test fixes (not infra scope).

**Why:** CI gates require the codebase to be GREEN. First pipeline failure on test issues is expected; escalate to backend-coordinator.

---

> **Scribe note:** the section below was appended by `meesell-infra-builder` acting as authorized scribe for the master/Director session (the Director's own bg-write guard blocks it from writing here). EXPLICIT exception to memory-ownership rule 4, content dictated by the master session. No other part of this file or directory was modified.

## CI ACTIVATION COMPLETE — 2026-06-12

**CI/CD PIPELINE IS ACTIVE.** Run 9 (`27366269839`, merge SHA `62713935`, PR #132) = the **FIRST FULLY GREEN end-to-end pipeline** in project history: 5 gates + 8 frontend + Cloud Build + IAP deploy (token refresh → k3s restart → readyz → applies → settle wait → alembic migrate → image roll → rollout status → in-pipeline health check) + external health 200.

**The 6-rung deploy-bug ladder, all codified (PR by PR):**
1. **act-as on the compute SA** — `meesell-github-ci` lacked `roles/iam.serviceAccountUser` on the `888244156264-compute@…` Cloud Build runner SA. **PR #113.**
2. **compute.viewer** — instance-scoped `instanceAdmin.v1` doesn't grant project-level `compute.projects.get`/`zones.get` for IAP-SSH target resolution. **PR #116.**
3. **AR pull auth** — K3s `registries.yaml` metadata-server token mechanism (SA-key alt #121 closed by org policy; puller resources TF-destroyed). **PR #119.**
4. **shallow-clone FETCH_HEAD** — VM clone has no `origin/main` ref; switched to `git fetch origin main` + reset to FETCH_HEAD. **PR #123.**
5. **unescaped `$(seq)`** — runner-side expansion inside `gcloud compute ssh --command`; replaced with a `\$`-escaped substitution-free loop. **PR #127.**
6. **exec-on-terminating-pod settle wait** — `kubectl apply` rollout raced the migrate `exec` (SIGKILL exit 137); inserted `rollout status` between applies and the alembic exec. **PR #131.**

**Branch protection — develop ONLY (founder-ruled 2026-06-12):** 13 required contexts (5 gates + `detect` + 7 frontend units) + strict + 1 review. `main` intentionally left without required checks.

**Still pending (founder, non-blocking):** `GEMINI_API_KEY_CI` GitHub secret (quota-capped key from aistudio.google.com/apikey; nightly `ai_eval` only).

**Process lesson:** never chain branch-delete unconditionally after a PR merge — gate on `merged: true` (PR #124 incident, recovered via #126).
