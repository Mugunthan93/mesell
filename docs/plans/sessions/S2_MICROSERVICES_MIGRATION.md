# Session Dispatch: Microservices Migration
**Session name:** `mesell-microservices-backend-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** BLOCKED — requires Session 1 (repo-management) complete first

---

## Prerequisite
Session 1 (repo-management) must be COMPLETE before this session starts.
`develop` and `staging` branches must exist.

---

## Mission
Review and ratify the Microservices Migration Master Plan. Lock the
architecture decisions. Author Sub-Plan A (export service extraction)
and begin execution of the first extraction.

---

## Read first (in this order)
1. `docs/plans/microservices_migration/MASTER_PLAN.md` — the plan to ratify
2. `docs/plans/infra/microservices_infra_plan.md` — infra constraints that affect
   code decisions (database schema-per-service, PgBouncer, connection pool limits)
3. `docs/BACKEND_ARCHITECTURE.md` — current modular monolith state
4. `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`

---

## Open decisions — get founder answer in this session

1. **ai_ops module placement (MUST DECIDE BEFORE Sub-Plan F)**
   - Option A: vendor `ai_ops/` as a Python package inside each AI-consuming
     service (`catalog`, `category`) — no dedicated microservice
   - Option B: dedicated `ai-ops-svc` microservice, other services call it via HTTP
   - Recommendation: Option A in V1.5 (simpler, no network hop for AI calls),
     Option B in V2 (when AI cost tracking per-service matters)

2. **MS-CI-1: Container image strategy**
   - Option A: 8 distinct Docker images (one per service)
   - Option B: 1 base image + 8 thin layers (extend the base)
   - Recommendation: 8 distinct images for V1.5 — no shared-layer bugs,
     independent versioning

3. **Sub-Plan A start: which extraction first?**
   - Locked extraction order: export → dashboard → image → pricing →
     customer → category → iam → catalog
   - Session 1 = export service extraction (smallest, no upstream service deps)
   - Confirm this order or adjust

---

## What to produce

### Step 1 — Ratify the plan
- Change STATUS in `docs/plans/microservices_migration/MASTER_PLAN.md` → APPROVED
- Record the 3 decisions above in a `## Decisions` section at the top of the plan

### Step 2 — Create the feature branch
- Create `feature/microservices-export/backend` from `develop`

### Step 3 — Author Sub-Plan A
Dispatch `meesell-backend-coordinator` to produce:
`docs/plans/microservices_migration/SUB_PLAN_A_EXPORT_SERVICE.md`
covering: file list to extract, new Dockerfile, new K8s manifest placeholders,
Alembic migration split procedure, HTTP client contract, CI changes

### Step 4 — Execute Sub-Plan A
After the plan is reviewed by founder:
Dispatch `meesell-backend-coordinator` → `meesell-services-builder` to
execute the export service extraction on `feature/microservices-export/backend`

### Step 5 — Commit + PR
Commit on `feature/microservices-export/backend`
Open PR to `feature/microservices-export` using `.github/PULL_REQUEST_TEMPLATE/backend.md`
Update `docs/status/feature_board_backend.md`

---

## Acceptance gate — session is DONE when
- [ ] MASTER_PLAN.md status = APPROVED
- [ ] All 3 decisions recorded in the plan
- [ ] `feature/microservices-export/backend` branch exists
- [ ] SUB_PLAN_A committed
- [ ] Export service extraction committed + PR open

---

## Constraints
- Only work inside `backend/` and `docs/plans/microservices_migration/`
- Do NOT touch `frontend/`, `k8s/`, `infra/terraform/`
- Do NOT extract more than one service per session — strangler fig, one step at a time
