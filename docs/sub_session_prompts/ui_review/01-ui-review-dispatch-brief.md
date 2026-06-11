# UI Review — Session Dispatch Brief

**Session name:** `mesell-ui-review-session-1`
**Date authored:** 2026-06-11 (master session, founder-requested lane)
**Status:** READY — the founder is PRESENT in this session (his eyes are the gate)

---

## What this session is

You are a dedicated sub-session for **visual UI review and polish** — this closes the long-pending **Gate 5 visual review** AND verifies the federated UI (3 remotes are now live on develop). The founder drives a browser; you guide, record findings, and dispatch fixes.

Working agent: `meesell-angular-ui-styler` (the UI specialist — it executes styling fixes directly). For findings beyond styling (logic, routing, services), record them as findings and hand them to the master session — do NOT fix logic here. **Only `meesell-*` agents may execute MeeSell work.**

## Required reading (in order)

1. `CLAUDE.md` (project root) — esp. ecosystem rule 7 (hybrid) and the frontend conventions
2. `frontend/README.md` — the run commands and ports
3. `docs/status/STATUS_FRONTEND.md` — current state
4. `.claude/agent-memory/meesell-angular-ui-styler/MEMORY.md`
5. `docs/plans/module_federation/MASTER_PLAN.md` — what "shell" vs "remote" means here

## Setup (founder runs these, session verifies)

```bash
cd frontend
pnpm install --config.dangerously-allow-all-builds=true   # only if fresh
# Terminal 1-3 (remotes):
pnpm start:mfe-pricing      # :4201
pnpm start:mfe-export       # :4202
pnpm start:mfe-onboarding   # :4203
# Terminal 4 (shell):
pnpm start:shell            # :4200
```
Sanity: `curl -s -o /dev/null -w "%{http_code}" http://localhost:4201/remoteEntry.json` → 200 (repeat for 4202/4203).

## The review protocol (founder looks, session records)

For EVERY route, at TWO widths — **360px (phone)** and **1280px (desktop)** via browser dev-tools device toolbar:

- All 11 V1 routes (onboarding, dashboard, catalog list/create/preview, quality check, price calculator, export, login, signup, otp-verify)
- The 3 **federated** routes specifically: pricing (`/catalogs/<id>/pricing`), export, onboarding — confirm they load from their remotes (network tab shows :4201/:4202/:4203 fetches)
- The **fallback test**: kill one remote's terminal, reload its route → expect the friendly RemoteFailureComponent, not a crash; restart, works again

Record EVERY finding in `docs/ui-review/GATE5_FINDINGS.md` (create): route, width, severity (P0 broken / P1 ugly / P2 polish), screenshot filename if the founder drops one in `docs/ui-review/`, and a one-line description. The founder's words are the finding — transcribe, don't editorialize.

## Fixing (hybrid rule applies)

- **Pure styling fixes** (spacing, overflow, contrast, responsive breaks): `meesell-angular-ui-styler` fixes them directly in this session — batch them per route, one branch `feature/ui-polish-gate5/frontend` → integration `feature/ui-polish-gate5/integration` per Model C (worktree under /tmp/mesell-wt/ui-review-*, NEVER switch the master tree's branch; founder-gate PR left OPEN).
- **Anything touching logic/routing/services/federation config**: finding only — goes in GATE5_FINDINGS.md for the master session to dispatch properly.
- Validation per fix batch: build green, full Vitest suite no regressions, PrimeNG boundary grep zero.

## Parallel-lane caution

Wave 2 (SP04 dashboard + SP05 catalog extractions) is running — dashboard and catalog pages may move into `apps/` while you review. If a route 404s or moves mid-session, note it and continue; do NOT touch `apps/`, `app.routes.ts`, `angular.json`, `federation.manifest.json`, or `package.json` (all Wave 2 conflict surfaces). Styling fixes inside page/component files are safe.

## Session end

GATE5_FINDINGS.md complete (even if empty = gate passes clean), fix-batch PR(s) opened, STATUS_FRONTEND.md UPDATE block, styler memory appended. Report: gate verdict (PASS / PASS-with-P2s / FAIL items), founder-gate PR number if fixes were made, and the handoff list for the master session.
