# Session Dispatch: Module Federation
**Session name:** `mesell-module-federation-frontend-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** BLOCKED — requires Session 1 (repo-management) complete first

---

## Prerequisite
Session 1 (repo-management) must be COMPLETE before this session starts.

---

## Mission
Review and ratify the Module Federation Master Plan. Lock the Wave 6 vs
federation ordering decision. Author Sub-Plan 0 (Workspace Foundation) and
execute it — this is a pure reorganisation with zero user-facing changes.

---

## Read first (in this order)
1. `docs/plans/module_federation/MASTER_PLAN.md` — the plan to ratify
2. `docs/plans/infra/module_federation_infra_plan.md` — hosting strategy that
   affects frontend build decisions (Option C: shell K3s + remotes GCS+CDN)
3. `docs/FRONTEND_ARCHITECTURE.md` — current single-app state
4. `docs/ui_ux/FRONTEND_WAVE_EXECUTION_PLAN.md` — Wave 6 status
5. `docs/status/STATUS_FRONTEND.md`
6. `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`

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

### Step 1 — Ratify the plan
- Change STATUS in `docs/plans/module_federation/MASTER_PLAN.md` → APPROVED
- Record Wave 6 decision prominently at top of the plan

### Step 2 — Create the feature branch
- Create `feature/module-federation-foundation/frontend` from `develop`

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
Open PR to `feature/module-federation-foundation`
Update `docs/status/feature_board_frontend.md`

---

## Acceptance gate — session is DONE when
- [ ] Wave 6 decision recorded + MASTER_PLAN.md = APPROVED
- [ ] 38 test failures disposition documented
- [ ] `libs/ui-kit`, `libs/composites`, `libs/core`, `libs/design-tokens` exist
- [ ] Empty shell project scaffolded
- [ ] Native Federation installed, build passes
- [ ] Per-remote angular.json projects registered
- [ ] All existing features still pass build (no regressions from reorganisation)
- [ ] PR open against `feature/module-federation-foundation`

---

## Constraints
- Do NOT extract any remote in this session — workspace foundation only
- Do NOT touch `backend/`, `k8s/`, `infra/`
- Do NOT change any feature's UI or behaviour — pure structural reorganisation
- Build must pass at start AND end of session
