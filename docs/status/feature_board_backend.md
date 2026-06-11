# Feature Board — Backend Lead

**Lead agent:** `meesell-backend-coordinator`
**Domain:** backend
**Last updated:** 2026-06-11 (dual-pepper-rotation backlog row added — R5 pre-V1.5-prod gate)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| microservices-export | feature/microservices-export/backend | IN PROGRESS | mesell-microservices-backend-session-1 | 2026-06-10 22:55 IST | none | Sub-Plan A (SUB_PLAN_01) authored DRAFT; awaiting founder ratification of A1 (ai_ops) + A2 (middleware). Step 4 extraction execution is POST-V1. |
| dual-pepper-rotation | — (not started) | PENDING | — | 2026-06-11 | none | **R5 follow-up — pre-V1.5-prod GATE** (founder ruling 2026-06-11 AM; must land before V1.5 goes to prod, NOT blocking V1). Today `REFRESH_TOKEN_PEPPER` is single/unversioned — rotating it invalidates ALL live sessions. Backend work: version-tag the Valkey DB 0 allowlist key prefix (`cache:refresh:{version}:{hmac}`) so dual-pepper reads work during the grace window. Mechanism doc: `docs/runbooks/auth-secret-rotation.md` §2 (lands on develop via auth-otp integration PR #46). Owner: meesell-auth-builder when scheduled. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| auth-otp (integration→develop) | develop | 2026-06-11 | #46 (merge cad0a9a) | **Founder-gated merge MERGED.** `feature/auth-otp/integration` → `develop` = backend group #44 + infra group #45. auth-otp (V1 Feature 1, FE-D5 split-token) now fully on develop. Backend post-merge sentinels stamped: V1_FEATURE_SPEC.md Feature 1 + BACKEND_ARCHITECTURE.md §7 (this PR). |
| auth-otp (backend group) | feature/auth-otp/integration | 2026-06-11 | #44 (squash af6a619) | Backend group merge-gate. Re-audit: iam backend 100% built/contract-correct (plan said ~95%); no construction diff — iam already on develop. 11/11 §Review checks PASS. Now subsumed into develop via #46 (cad0a9a). |
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
