## Session 2026-06-18 — PR #284 pricing rebase split-brain fix {#pr284-pricing-fix}

### Task
Fix `pricing.component.ts` rebase split-brain on branch `fix/ci-core-exports-and-icons`.
The old develop version of the component imported `computePnlBreakdown` and `PnlBreakdown`
(both DEAD per DECISION-1, MASTER_PLAN §7), while the branch's `pricing.utils.ts` and
`pricing.model.ts` had already removed those symbols. CI was failing to compile.

### Route touched
`/catalogs/:id/pricing` — mfe-pricing app.

### Services consumed
`PricingApiService` from `./pricing.service` (component-scoped, listed in providers[]).

### Root cause analysis
The branch `fix/ci-core-exports-and-icons` was rebased, and the rebase conflict resolution
took `pricing.component.ts` from the old develop version (pre-server-calc). The service
(`pricing.service.ts`) and model (`pricing.model.ts`) were kept from the newer branch version
that had already implemented DECISION-1. Result: component tried to import symbols that
no longer existed → TypeScript error.

### Fix applied
Replaced `pricing.component.ts` with the full correct implementation:
- Removed: `computePnlBreakdown`, `PnlBreakdown` imports, `sliderMrp`/`onSliderInput`/`onMrpInput`
  (slider retired per DECISION-1), `MeeProgressBarComponent`
- Added: `PricingApiService` (injected + providers[]), `MeeAlertBannerComponent`,
  `MeeOfflineBannerComponent`, `PriceCalcResponse`, `PriceCalcErrorShape`, `ALERT_MESSAGES`
- Form: `mrp`→`input_cost` (min 0.01), `target_margin`→`target_margin_pct` (min 0, max 500)
- `onCalculate()`: calls `service.calc(productId, {input_cost, target_margin_pct})`
  with subscribe(next/error/complete). next: checks `'kind' in result` to distinguish
  error shapes from success. complete: handles EMPTY (401 path).
- Added `_handleErrorShape()` private method with switch on `shape.kind`
- `errorState = signal<PricingErrorState>(null)` — 5 states including null
- `commissionMissingDetail` + `validationDetail` signals populated from server response
- Template: 4 error banner @if blocks + spinner + result table + POSITIVE/NEGATIVE badge
- `AfterViewChecked` + `_focusPending` flag for programmatic focus to `#resultRegion`

### Pattern: tsc --noEmit via cross-tree worktree
- The fix branch worktree (/tmp/mesell-wt/ci-core-fix) has NO node_modules (shared from
  parent project). Running tsc with the worktree's tsconfig but main project's
  node_modules/.bin/tsc gives accurate results.
- Command: `cd <worktree>/frontend && /path/to/main/node_modules/.bin/tsc --noEmit ...`
- Many "Cannot find module" errors from the worktree run are ALL environment errors
  (no node_modules in worktree) — they appear for every file uniformly.
- ONLY `pricing.component.ts` errors that are NOT "Cannot find module" or "tslib" are
  genuine code errors requiring fixes.
- Validation: run tsc from the MAIN project tree (where node_modules exist) to get the
  true zero-error baseline.

### Pattern: spec already correct — don't overwrite
- In this case `pricing.component.spec.ts` was already the correct version on the branch.
- The spec used pure-function Vitest tests (no TestBed) — no `computePnlBreakdown` imports.
- Always check the spec file before deciding it needs changes — reading it first saved work.

### Pattern: DECISION-1 is a PERMANENT auto-reject rule
- Any local-math fallback in pricing MUST be rejected at merge gate.
- Symptoms: `computePnlBreakdown`, `PnlBreakdown`, `COMMISSION_PCT`, `GST_PCT` in
  pricing.component.ts imports.
- The correct service is `PricingApiService.calc()` — server-calc only.

### Worktree management
- Created `/tmp/mesell-wt/ci-core-fix` via `git worktree add /tmp/mesell-wt/ci-core-fix origin/fix/ci-core-exports-and-icons`
  → detached HEAD.
- Needed tracking branch to push: `git checkout -b fix-pricing-server-calc --track origin/fix/ci-core-exports-and-icons`
- Push: `git push origin fix-pricing-server-calc:fix/ci-core-exports-and-icons`

### Build/test results
- tsc --noEmit (main tree): 0 errors for pricing.component.ts
- Contract scanner (--strict): FE-1/FE-2/FE-3/FE-4/FE-5 all CLEAN
- Commit: 4d65398 on branch fix/ci-core-exports-and-icons

---
