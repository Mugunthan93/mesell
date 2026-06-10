# Session Dispatch: Microservices Migration
**Session name:** `mesell-microservices-backend-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — S1 complete, Model C ACTIVE (2026-06-10), pilot-hardened (PILOT_REPORT.md)

---

## Prerequisite
Session 1 (repo-management) is COMPLETE. Model C is ACTIVE (2026-06-10).
`develop` and `staging` branches exist.

---

## Mission
The Microservices Migration Master Plan is **already ratified** — LOCKED
2026-06-10 as the **post-V1 roadmap** (revision v1.1 carries the
compliance-audit §5.G). Ratification is DONE; do NOT re-ratify.

Remaining scope for this session is the plan's later steps: author Sub-Plan A
(export service extraction) and begin execution of the first extraction.

**Context — execution is post-V1.** Impact analysis found that full extraction
of the 8-service topology forces a VM upgrade to **≥ e2-standard-4** (the
extracted topology needs ≈1600m+ CPU vs the ~950m the current free
e2-standard-2 affords). This is the concern owned by the S4 sibling
(infra-microservices) — sequence accordingly.

---

## Read first (in this order)
1. `docs/plans/microservices_migration/MASTER_PLAN.md` — the LOCKED plan (post-V1 roadmap, v1.1)
2. `docs/plans/repo_management/PILOT_REPORT.md` — Model C pilot findings (F1–F3)
3. `docs/plans/repo_management/MASTER_PLAN.md` §1.2/§6.5/§9.5 as amended v1.1 (F1–F3)
4. `docs/plans/infra/microservices_infra_plan.md` — infra constraints that affect
   code decisions (database schema-per-service, PgBouncer, connection pool limits)
5. `docs/BACKEND_ARCHITECTURE.md` — current modular monolith state
6. `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`

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

### Step 1 — Ratify the plan — DONE (do not repeat)
- ✅ Plan already LOCKED 2026-06-10 as the post-V1 roadmap (revision v1.1,
  §5.G compliance audit). No re-ratification needed.
- The 3 decisions below remain OPEN sub-plan-authoring questions — resolve them
  while authoring Sub-Plan A, not as a master-plan ratification gate.

### Step 2 — Create the feature branch
- Create `feature/microservices-export/backend` from `develop`
- **F1 (pilot ruling):** the integration branch for this feature is
  `feature/microservices-export/integration` — open the group PR against the
  integration branch, NOT a bare `feature/microservices-export`.

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
Open PR to `feature/microservices-export/integration` (F1) using `.github/PULL_REQUEST_TEMPLATE/backend.md`
Update `docs/status/feature_board_backend.md`

---

## Acceptance gate — session is DONE when
- [x] MASTER_PLAN.md status = LOCKED (done 2026-06-10, post-V1 roadmap v1.1)
- [ ] 3 sub-plan-authoring decisions recorded in Sub-Plan A
- [ ] `feature/microservices-export/backend` branch exists
- [ ] SUB_PLAN_A committed
- [ ] Export service extraction committed + PR open against `feature/microservices-export/integration` (F1)

---

## Constraints
- Only work inside `backend/` and `docs/plans/microservices_migration/`
- Do NOT touch `frontend/`, `k8s/`, `infra/terraform/`
- Do NOT extract more than one service per session — strangler fig, one step at a time
