# Session Dispatch: Module Federation
**Session name:** `mesell-module-federation-frontend-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — S1 complete, Model C ACTIVE (2026-06-10), pilot-hardened (PILOT_REPORT.md). **Priority pair: S3 + S5 (federation-first ruling).**

---

## Prerequisite
Session 1 (repo-management) is COMPLETE. Model C is ACTIVE (2026-06-10).

---

## Mission
The Module Federation Master Plan is **already APPROVED** (2026-06-10) and the
Wave 6 vs federation ordering decision is **already locked**: founder ruling is
**FEDERATION FIRST** (federate before Wave 6 real-API wiring). Ratification and
the ordering decision are DONE — do NOT re-ratify or re-decide.

Remaining scope for this session is the plan's later steps: author Sub-Plan 0
(Workspace Foundation) in detail per MF MASTER_PLAN §5 row 0, and execute it —
a pure reorganisation with zero user-facing changes.

**Two hard gates block Sub-Plan 0 EXECUTION (but NOT this session's authoring work):**
- **Gate 3 — TestBed-38 triage:** the 38 pre-existing Angular 21 + Vitest
  TestBed failures must be triaged in a SEPARATE dispatch that runs in parallel.
- **Gate 4 — infra confirmation:** S5 (infra-module-federation) must confirm K3s
  + Traefik can host the shell + 6 remotes and that CSP is editable.
Author Sub-Plan 0 fully now; gate its EXECUTION on Gates 3 + 4 clearing.

---

## Read first (in this order)
1. `docs/plans/module_federation/MASTER_PLAN.md` — APPROVED plan (FEDERATION FIRST)
2. `docs/plans/repo_management/PILOT_REPORT.md` — Model C pilot findings (F1–F3)
3. `docs/plans/repo_management/MASTER_PLAN.md` §1.2/§6.5/§9.5 as amended v1.1 (F1–F3)
4. `docs/plans/infra/module_federation_infra_plan.md` — hosting strategy that
   affects frontend build decisions (Option C: shell K3s + remotes GCS+CDN)
5. `docs/FRONTEND_ARCHITECTURE.md` — current single-app state
6. `docs/ui_ux/FRONTEND_WAVE_EXECUTION_PLAN.md` — Wave 6 status
7. `docs/status/STATUS_FRONTEND.md`
8. `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`

---

## Open decisions — get founder answer FIRST before any work begins

1. **CRITICAL: Wave 6 (real API wiring) vs Module Federation — which runs first?**
   Running both simultaneously is the single highest risk flagged in the plan.
   - Option A: Complete Wave 6 first (wire all 11 features to real API), THEN federate
   - Option B: Federate first (Sub-Plan 0 workspace foundation), THEN wire API inside remotes
   - Option C: Explicit deprioritisation — mark Wave 6 as V1.5, federation is V1 completion
   - This decision BLOCKS everything else in this session

2. **38 pre-existing Angular 21 + Vitest TestBed test failures — disposition**
   - Option A: Fix them before federation starts (clean baseline)
   - Option B: Acknowledge and label them `pre-existing` — federation proceeds,
     failures are not attributed to federation work
   - Recommendation: Option B for speed. Create a tracking file listing the 38.

3. **MF-ENV-1: Remote asset storage**
   - Option A: Separate GCS bucket per env (`gs://mesell-remotes-dev`,
     `gs://mesell-remotes-staging`)
   - Option B: Single bucket with env prefix (`gs://mesell-remotes/dev/`,
     `gs://mesell-remotes/staging/`)
   - Recommendation: Option A — clean IAM, no env bleed risk

---

## What to produce

### Step 1 — Ratify the plan + Wave 6 decision — DONE (do not repeat)
- ✅ MASTER_PLAN.md = APPROVED (2026-06-10).
- ✅ Wave 6 decision locked: **FEDERATION FIRST** (federate before Wave 6 API wiring).
- No re-ratification or re-decision needed.

### Step 2 — Create the feature branch
- Create `feature/module-federation-foundation/frontend` from `develop`
- **F1 (pilot ruling):** the integration branch for this feature is
  `feature/module-federation-foundation/integration` — open the group PR against
  the integration branch, NOT a bare `feature/module-federation-foundation`.

### Step 3 — Author Sub-Plan 0 (Workspace Foundation)
Dispatch `meesell-frontend-coordinator` to produce:
`docs/plans/module_federation/SUB_PLAN_00_WORKSPACE_FOUNDATION.md`
covering: pnpm workspace setup, `libs/ui-kit`, `libs/composites`, `libs/core`,
`libs/design-tokens` extraction, empty shell project scaffold, Native Federation
install, per-remote `angular.json` projects, CI changes

### Step 4 — Execute Sub-Plan 0
Dispatch `meesell-frontend-coordinator` → specialists to execute workspace
foundation on `feature/module-federation-foundation/frontend`
This is REORGANISATION ONLY — no feature code changes, no API wiring

### Step 5 — Commit + PR
Commit on `feature/module-federation-foundation/frontend`
Open PR to `feature/module-federation-foundation/integration` (F1)
Update `docs/status/feature_board_frontend.md`

---

## Acceptance gate — session is DONE when
- [x] Wave 6 decision recorded + MASTER_PLAN.md = APPROVED (done 2026-06-10, FEDERATION FIRST)
- [ ] Sub-Plan 0 authored in detail per MF §5 row 0
- [ ] 38 test failures disposition documented (Gate 3 — parallel dispatch)
- [ ] `libs/ui-kit`, `libs/composites`, `libs/core`, `libs/design-tokens` exist
- [ ] Empty shell project scaffolded
- [ ] Native Federation installed, build passes
- [ ] Per-remote angular.json projects registered
- [ ] All existing features still pass build (no regressions from reorganisation)
- [ ] PR open against `feature/module-federation-foundation/integration` (F1)

> NOTE: Sub-Plan 0 EXECUTION (the items above the PR line) is gated on Gate 3
> (TestBed-38 triage) and Gate 4 (S5 infra confirmation). Authoring Sub-Plan 0
> is NOT gated and is this session's core deliverable.

---

## Constraints
- Do NOT extract any remote in this session — workspace foundation only
- Do NOT touch `backend/`, `k8s/`, `infra/`
- Do NOT change any feature's UI or behaviour — pure structural reorganisation
- Build must pass at start AND end of session
