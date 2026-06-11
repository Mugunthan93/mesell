# Handoff → meesell-infra-builder — MF CI prep (C-CI-1)

**From:** meesell-frontend-coordinator (Frontend Lead)
**Date opened:** 2026-06-10
**Feature:** mf-workspace-foundation (MF Sub-Plan 0)
**SLA:** 48h before escalation to founder via STATUS_MASTER.md
**Board row:** feature_board_frontend.md → Inter-lead requests open (outgoing).

## Context
MF Sub-Plan 0 has EXECUTED and merged to `feature/mf-workspace-foundation/integration`
(PR #40, squash `e51761b`). The integration→develop PR #41 is OPEN awaiting the
founder's morning review (founder gate per D1/FD2). Once #41 merges, the frontend
tree shape on `develop` changes materially:

- NEW directory: `frontend/libs/{ui-kit,composites,core,design-tokens}/**`
- REMOVED from src: `frontend/src/app/{ui,shared,core,design-system}/**` (relocated)
- `@mesell/*` tsconfig path aliases now resolve the shared layers
- Native Federation builder (`@angular-architects/native-federation:build`) wraps
  `@angular/build:application` — `ng build` output is now federated ESM (per-module),
  not a single classic bundle. `public/federation.manifest.json` = `{}` (zero remotes).

## The asks (C-CI-1, per GATE4_CONFIRMATION.md)
1. **Confirm the existing `build-frontend` CI job still resolves the reorganised tree.**
   The job's globs / working-dir must cover `frontend/libs/**` as well as `frontend/src/**`.
   Sub-Plan 0 still builds as ONE `ng build` target (the shell consuming libs via aliases),
   so no per-project matrix is needed YET — but the path globs must include libs/.
2. **Have the CI matrix / paths-filter / cloudbuild split (C-CI-1) READY before Sub-Plan 1.**
   GATE4 C-CI-1: the single-frontend CI conditional must be REPLACED (not extended) WHEN the
   multi-project Angular workspace lands. That landing is **Sub-Plan 1 (first remote
   extraction = mfe-pricing pilot)**, NOT Sub-Plan 0. Sub-Plan 0 has no independently-built
   units, so there is nothing to fan out yet. But the rewrite must be ready when Sub-Plan 1 opens.
3. **Note:** `pnpm build` wrapper fails in fresh worktrees on ERR_PNPM_IGNORED_BUILDS
   (native build scripts ignored: esbuild/@parcel/watcher/lmdb/msgpackr-extract). The
   frontend lead works around it with `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`
   then `ng build` directly. CI must ensure native binaries extract (the `dangerously-allow-all-builds`
   .npmrc trick is environment-blocked here; `pnpm rebuild <pkgs>` is the clean alternative).

## Not a blocker for Sub-Plan 0
This is a 48h-SLA inter-lead request, not a blocker. Sub-Plan 0 merged cleanly. The ask
is to be READY for Sub-Plan 1.

## How to resolve (decentralized memory protocol)
Read this memo + add YOUR OWN incoming-side row to YOUR board
(feature_board_infra*.md). Do NOT edit feature_board_frontend.md (sole-writer). When done,
the Frontend Lead marks this CLOSED on its own board.
