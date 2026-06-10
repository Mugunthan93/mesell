# Feature Board — Frontend Lead

**Lead agent:** `meesell-frontend-coordinator`
**Domain:** `frontend`
**Last updated:** 2026-06-10 (initial creation)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|

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
