# Feature Board — Frontend Lead

**Lead agent:** `meesell-frontend-coordinator`
**Domain:** `frontend`
**Last updated:** 2026-06-11 (mfe-pricing pilot MERGED to integration #52; founder-gate #53 OPEN)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| mfe-pricing | feature/mfe-pricing/integration | 2026-06-11 | #52 (squash a82cfcf) | MF Sub-Plan 01 PILOT. features/pricing → apps/mfe-pricing Native Federation remote; first loadRemoteModule + D12 fallback. Remote 3.35s/shell 3.29s (esbuild preserved); 42/406 tests; boundary 0. Integration→develop FOUNDER GATE PR #53 OPEN. §9.A: 6 PASS / 3 locally-proven (4,7,8 — no headless browser / GCS hosting handed to infra). |
| mf-workspace-foundation | feature/mf-workspace-foundation/integration | 2026-06-10 | #40 (squash e51761b) | MF Sub-Plan 0. libs/ relocation (@mesell/*) + Native Federation init (zero remotes). 401/401 tests, build 3.1s, boundary 0 violations. Integration→develop PR #41 MERGED 2026-06-11 (5198ba7). |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | mfe-pricing | D13 Option-C hosting: GCS bucket + Cloud CDN + remotes.mesell.xyz DNS/cert + cloudbuild.remote.yaml upload pipeline + per-env manifest URL templating. Locally dev-validated (localhost remote); prod surface pending. See handoff_mf_pricing_deploy.md | 2026-06-11 | OPEN |
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
