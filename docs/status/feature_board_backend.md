# Feature Board — Backend Lead

**Lead agent:** `meesell-backend-coordinator`
**Domain:** backend
**Last updated:** 2026-06-10 (session-end sweep, mesell-microservices-backend-session-1)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| microservices-export | feature/microservices-export/backend | IN PROGRESS | mesell-microservices-backend-session-1 | 2026-06-10 22:55 IST | none | Sub-Plan A (SUB_PLAN_01) authored DRAFT; awaiting founder ratification of A1 (ai_ops) + A2 (middleware). Step 4 extraction execution is POST-V1. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| housekeeping-v1 | feature/housekeeping-v1 (integration) | 2026-06-10 | #28 | Sweep correction: PILOT_REPORT shows backend group PR squash-merged `6da5b80`; board row was stale at IN REVIEW (F2 conservative path). Moved to MERGED. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/backend` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The backend group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until that group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

## Acceptance gate

Every `feature/{name}/backend` → `feature/{name}` PR must use `.github/PULL_REQUEST_TEMPLATE/backend.md` and pass the approval criteria in `.claude/agents/meesell-backend-coordinator.md` § "Merge gate". The lead (this agent) is the sole approver for this PR class per MASTER_PLAN.md D1.
