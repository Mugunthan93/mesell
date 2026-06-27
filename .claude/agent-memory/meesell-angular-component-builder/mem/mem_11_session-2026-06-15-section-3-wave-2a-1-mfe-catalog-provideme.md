## Session 2026-06-15 — Section-3 Wave 2A.1 — mfe-catalog provideMeeUi bootstrap (GAP-3) {#s3-w2a1-providemeeui}

### Task
Add `provideMeeUi()` from `@mesell/ui-kit` to `frontend/apps/mfe-catalog/src/main.ts` dev-serve bootstrap.
This is a one-file, two-line addition to close GAP-3: PrimeNG Aura theme + MessageService +
ConfirmationService now available in standalone (non-federated) dev mode.

### Route touched
`/catalogs/*` — mfe-catalog remote (all 5 catalog routes via CATALOG_ROUTES)

### Pattern: provideMeeUi() spread placement in remote bootstrap
- Import AFTER `@mesell/core` interceptors import: `import { provideMeeUi } from '@mesell/ui-kit'`
- Place `...provideMeeUi()` immediately after `provideAnimationsAsync()` in providers array
- MUST spread (`...`) — `provideMeeUi()` returns `(Provider | EnvironmentProviders)[]` not a single provider
- This mirrors shell's `app.config.ts` which already calls `...provideMeeUi()` at line 41
- In federated (production) mode: remote inherits shell injector → provideMeeUi in shell covers PrimeNG
- In dev-serve mode (standalone bootstrap): remote has its OWN injector → must call provideMeeUi locally

### Pattern: R-SP3-1 comment block (lines 4-14) is LOAD-BEARING — never touch
- The large comment block at the top of main.ts explains Native Federation shared-mapping analysis
- DO NOT remove, reorder, or trim anything in the comment block or the CATALOG_ROUTES reference
- The FULL `provideRouter(CATALOG_ROUTES)` call must remain — Sheriff analyzes this for singleton graph

### Pattern: Pre-existing build errors in mfe-catalog — do not conflate with your change
- `smart-picker.component.ts` has pre-existing uncommitted NG8001/NG8002 errors (`mee-button` import missing)
- These errors existed BEFORE this task (confirmed: `git status` shows the file already modified)
- My change to `main.ts` adds zero new TypeScript errors
- `@mesell/ui-kit` path alias is declared in `frontend/tsconfig.json` → `libs/ui-kit/index.ts`
- `provideMeeUi` is exported from `libs/ui-kit/index.ts` → re-exports from `./providers`

### Commit
- Branch: feature/section-3/frontend
- Commit: 0ef003b — "T-S3-W2A: add provideMeeUi to mfe-catalog dev-serve bootstrap (GAP-3)"
- Files: `frontend/apps/mfe-catalog/src/main.ts` + `docs/status/STATUS_FRONTEND.md`

---
