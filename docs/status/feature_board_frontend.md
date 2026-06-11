# Feature Board — Frontend Lead

**Lead agent:** `meesell-frontend-coordinator`
**Domain:** `frontend`
**Last updated:** 2026-06-11 (SP02 mfe-export MERGED to integration #60; founder-gate #61 OPEN — Wave 1 parallel with SP03)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| mfe-onboarding | feature/mfe-onboarding/frontend | IN PROGRESS | mesell-mfe-onboarding-frontend-session-1 | 2026-06-11 | — | MF Sub-Plan 03. Extract features/account/onboarding + features/profile → apps/mfe-onboarding (TWO-expose remote). D21 PROMOTE AuthLayout→@mesell/composites (founder RULED APPROVED). D22 AuthService singleton C1–C5 = migration auth go/no-go. Concurrent with SP02 export (Wave 1). SP01 pilot MERGED to develop (#53, bb37f5f). |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| mfe-export | feature/mfe-export/integration | 2026-06-11 | #60 (squash 565d754) | MF Sub-Plan 02 (R6, F12 export). features/export → apps/mfe-export Native Federation remote; 2nd extraction, copied SP01 recipe (D15). Remote build 3.43s/shell 2.89s (esbuild preserved, <90s); 42 files/406 tests (== SP01 baseline, export spec discovered via apps/ glob, 0 drop, 0 fail); boundary 0 in apps/. NEW surfaces: two-remote manifest (pricing+export both remoteEntry 200 + chunk 200, broken→404; R-SP2-4 PASS) + D18 timer preserved across boundary (R100 rename, ngOnDestroy→clearInterval byte-identical). Integration→develop FOUNDER GATE PR #61 OPEN. §9.A: 5 PASS / 3 locally-proven (4,7,8) / 2 new-surface PASS / 0 FAIL. D13 hosting deferred to SP04-05 (no new infra request). WAVE 1 parallel with SP03. |
| mfe-pricing | feature/mfe-pricing/integration | 2026-06-11 | #52 (squash a82cfcf) | MF Sub-Plan 01 PILOT. features/pricing → apps/mfe-pricing Native Federation remote; first loadRemoteModule + D12 fallback. Remote 3.35s/shell 3.29s (esbuild preserved); 42/406 tests; boundary 0. Integration→develop FOUNDER GATE PR #53 OPEN. §9.A: 6 PASS / 3 locally-proven (4,7,8 — no headless browser / GCS hosting handed to infra). |
| mf-workspace-foundation | feature/mf-workspace-foundation/integration | 2026-06-10 | #40 (squash e51761b) | MF Sub-Plan 0. libs/ relocation (@mesell/*) + Native Federation init (zero remotes). 401/401 tests, build 3.1s, boundary 0 violations. Integration→develop PR #41 MERGED 2026-06-11 (5198ba7). |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | mfe-pricing | D13 Option-C hosting: GCS bucket + Cloud CDN + remotes.mesell.xyz DNS/cert + cloudbuild.remote.yaml upload pipeline + per-env manifest URL templating. Locally dev-validated (localhost remote); prod surface pending. See handoff_mf_pricing_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mfe-export | D19 second-remote prefix gs://meesell-frontend/{env}/mfe-export/{version}/ + confirm dorny/paths-filter matrix fans out apps/mfe-export/** as its own build unit (C-CI-1). RECORD-ONLY — D13 hosting deferred to SP04-05 per founder ruling; extends the open SP01 request, NOT a new active ask. See handoff_mf_export_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mf-workspace-foundation | CI matrix rewrite (C-CI-1) ready before Sub-Plan 1; confirm new frontend/libs/** paths resolve against build-frontend glob. See handoff_mf_ci_prep.md. NOTE: chore/ci-matrix-c-ci-1 worktree observed in flight 2026-06-11 — SP01 now adds apps/mfe-pricing/** as the first per-remote build unit (cloudbuild.remote.yaml). | 2026-06-10 | OPEN |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/frontend` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The frontend group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the active features table until the frontend group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

## Acceptance gate

Every `feature/{name}/frontend` → `feature/{name}` PR is reviewed against the checklist in `.github/PULL_REQUEST_TEMPLATE/frontend.md`. The lead does not merge until every box is checked: build < 90 s (CLAUDE.md Decision 12), bundle delta noted, screenshots at 360 px and 1280 px attached, accessibility checks confirmed, CI gates 1 + 3 green. See repo management master plan §2.1 + the Merge gate section of `.claude/agents/meesell-frontend-coordinator.md`.
