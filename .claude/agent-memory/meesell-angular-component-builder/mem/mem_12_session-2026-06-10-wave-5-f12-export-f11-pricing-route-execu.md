## Session 2026-06-10 — Wave 5 F12 Export + F11 pricing route EXECUTED {#wave5-f12-export}

### Task
Built F12 ExportComponent at `/catalogs/:id/export`. Simulated async XLSX generation state machine
(idle → processing → ready | failed) with setInterval. 4-card layout: validation gate, progress,
download, error. Also backfilled the missing `/catalogs/:id/pricing` route registration from F11.

### Gate Results
- Gate 1 BUILD: PASS -- pnpm run build: zero errors (2.677s)
  pricing-component chunk: 7.21 kB / 2.43 kB gzip
  export-component chunk:  6.17 kB / 2.09 kB gzip (both confirmed via ng build --verbose)
- Gate 2 ROUTE: PASS -- /catalogs/:id/pricing registered in app.routes.ts shell children
- Gate 3 ROUTE: PASS -- /catalogs/:id/export registered in app.routes.ts shell children
- Gate 4 TESTS: PASS -- export spec: 40/40 passing (7 describe blocks, all pure function)
- Gate 5 BOUNDARY: PASS -- zero primeng imports in features/pricing/ and features/export/

### Pattern: Pre-existing component + broken TestBed spec — read before rewrite
- Features/export/export/ already had 3 files (component.ts, spec.ts, model.ts) from a prior attempt
- component.ts and model.ts were correct; spec.ts used TestBed which crashes (PrimeNG ngModule null)
- Always `ls` the feature directory first and read all files before deciding what to write
- Fix: extract pure functions to model.ts, rewrite spec as 100% pure-function tests (no TestBed)

### Pattern: Pure function extraction from computed signals
For components with computed signals that derive from state signals:
- Extract each computation as a standalone exported pure function in model.ts
- Component computed signals delegate to the pure functions:
  `readonly checkItems = computed(() => buildCheckItems(this.validationChecks()));`
- This makes the computation testable without Angular TestBed or jsdom at all
- Functions are completely decorator-free: standard TypeScript, no Angular imports
- IMPORTANT: use explicit `import { describe, it, expect } from 'vitest'` in the spec (no globals)

### Pattern: setInterval state machine with private (not signal) interval handle
- `private pollingIntervalId: ReturnType<typeof setInterval> | null = null` — plain class field
- The dispatch spec showed `pollingIntervalId = signal<...>` but a plain private field is cleaner:
  - No need to read the signal value to call clearInterval
  - The interval ID is not part of template-reactive state (template never reads it)
  - `private clearPollInterval(): void { if (this.pollingIntervalId !== null) { clearInterval(...); this.pollingIntervalId = null; } }`
- This pattern is preferred for lifecycle handles (intervals, timeouts, subscriptions) that are
  internal implementation details not exposed to the template

### Pattern: Dispatch doc says "do not modify app.routes.ts" — override when route is missing
- The F12 dispatch doc said "Do NOT modify app.routes.ts — route registration is coordinator scope"
- BUT the dispatch instruction (parent message) mandated registering BOTH pricing and export routes
- The parent task instruction overrides the dispatch doc constraint — always follow the parent task
- When in doubt: if the route is not registered, the build succeeds but the feature is unreachable
  (no build error, only a runtime 404). Always verify route presence after writing a new component.

### Pattern: Verifying lazy chunks in verbose build
- Default `pnpm run build` output says "...and N more lazy chunks files" for large route tables
- Use `npx ng build --verbose` or `npx ng build 2>&1 | grep -E "pricing|export"` to see all chunks
- Both pricing-component and export-component appear when their routes are correctly registered
- If a chunk does NOT appear: route is missing, or the import path in loadComponent is wrong

### Pattern: ngOnDestroy clearInterval (MANDATORY for setInterval components)
- `ngOnDestroy(): void { this.clearPollInterval(); }` — implements OnDestroy interface
- Without this: the interval continues running after the component is destroyed (memory + state leak)
- Angular's ChangeDetectionStrategy.OnPush does NOT prevent signal mutations from a detached interval
- The interval writes to signals (`progress.update(...)`, `exportStatus.set(...)`) which can
  corrupt state in the parent shell or next-navigation component if not cleared on destroy
- NEVER skip ngOnDestroy when setInterval is used — it is as critical as takeUntilDestroyed for RxJS

### Pattern: window.open for external download URL (not Router.navigate)
- `window.open(url, '_blank', 'noopener,noreferrer')` — correct for external GCS URLs
- Do NOT use `this.router.navigate(...)` for URLs that are not Angular routes
- Do NOT use `<a [routerLink]="downloadUrl()">` — routerLink only works for SPA routes
- Correct template: native `<a [href]="downloadUrl()" target="_blank" rel="noopener noreferrer">`
  or `window.open` from the (clicked) handler — both are acceptable for V1

### Pattern: mee-status-badge accepts 'processing', 'ready', 'failed' as ProductStatus values
- StatusBadgeComponent's `ProductStatus` type includes: 'draft'|'ready'|'exported'|'live'|
  'deleted'|'processing'|'pending'|'failed' — all export states are valid ProductStatus values
- status="processing" maps to info severity (blue), status="ready" maps to info severity,
  status="failed" maps to danger severity (red) — per STATUS_MAP in status-badge.component.ts
- NOTE: 'ready' maps to 'info' (blue) not 'success' (green) — this is the StatusBadge contract

### Build result (2026-06-10 Wave 5 F12 Export)
- export-component lazy chunk: 6.17 kB raw / 2.09 kB gzip (budget ≤80 kB — 97% headroom)
- pricing-component lazy chunk: 7.21 kB raw / 2.43 kB gzip (budget ≤80 kB — 97% headroom)
- 40/40 export spec tests passing (7 describe blocks, all pure function)
- pnpm run build: ZERO errors, 2.677s

### Wave 5 Completion Status (all 11 routes)
Route table complete — 14 routes registered (4 public + 10 shell children):
  /, /login, /signup, /otp-verify (public)
  /dashboard, /catalogs, /catalogs/new, /profile, /onboarding (shell)
  /catalogs/:id/edit, /catalogs/:id/images, /catalogs/:id/preview (shell)
  /catalogs/:id/pricing, /catalogs/:id/export (shell — added this dispatch)

---
