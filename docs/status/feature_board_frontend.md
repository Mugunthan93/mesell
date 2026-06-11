# Feature Board — Frontend Lead

**Lead agent:** `meesell-frontend-coordinator`
**Domain:** `frontend`
**Last updated:** 2026-06-10 (mf-workspace-foundation in review)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| mf-workspace-foundation | feature/mf-workspace-foundation/integration | 2026-06-10 | #40 (squash e51761b) | MF Sub-Plan 0. libs/ relocation (@mesell/*) + Native Federation init (zero remotes). 401/401 tests, build 3.1s, boundary 0 violations. Integration→develop PR #41 OPEN — FOUNDER GATE. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | mf-workspace-foundation | CI matrix rewrite (C-CI-1) ready before Sub-Plan 1; confirm new frontend/libs/** paths resolve against build-frontend glob. See handoff_mf_ci_prep.md | 2026-06-10 | OPEN |

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
