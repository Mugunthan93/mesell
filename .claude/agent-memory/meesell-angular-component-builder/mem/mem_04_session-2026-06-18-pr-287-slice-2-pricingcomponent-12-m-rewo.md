## Session 2026-06-18 — PR #287 slice-2 — PricingComponent §12.M rework {#pricing-slice-2}

### Task
HYBRID step 2 (builder): Rewrite pricing.component.ts to the §12.M Price Calculator contract
on branch feat/pricing-fe-rework. Worktree: /private/tmp/mesell-wt/pricing-fe-rework.

### Route touched
`/catalogs/:id/pricing` — mfe-pricing (standalone bootstrap + federated via shell)

### Services consumed
`PricingApiService` (from pricing.service.ts authored in slice 1) — inject() pattern, route-scoped provider.

### §12.M contract changes implemented
- PRIMARY input: meesho_price (selling price) → estimated_payout hero
- DELETED: target_margin_pct, targetMarginError(), commission_missing error state
- NEW inputs: commission_pct (default "4"), return_rate_pct (default "0"), mrp (optional)
- HERO: estimated_payout "You pocket ₹X" — positive/negative badge + WDRP footnote
- RATIOS: margin_pct (% of meesho_price = "Margin") + markup_pct (% of input_cost = "Markup")
- 3-PRICE STRIP: mrp (null → "—") · meesho_price · wdrp_price
- DEDUCTION TABLE: 8 rows + bold total_deductions (all from server response, DECISION-1)
- ALERTS: server PriceCalcAlert[] mapped via ALERT_MESSAGES[message_id] to MeeAlertBanner
- LIVE RECALC: form.valueChanges → debounceTime(350) → distinctUntilChanged → switchMap(calc)

### Pattern: _buildRequestBody return type must be PriceCalcRequest not object
- `_buildRequestBody` originally returned `object` — TypeScript strict allows this but
  `PricingApiService.calc(productId, body)` expects `PriceCalcRequest` → TS2345 compile error.
- Fix: change return type to `PriceCalcRequest`, build body as `PriceCalcRequest` directly
  and use `body.commission_pct = ...` (dot notation) instead of `body['key'] = ...`
- ALSO: add `PriceCalcRequest` to the `import type { ... }` from pricing.model.ts

### Pattern: Worktree branch state (correctly checked out)
- Slice-1 commit had already checked out `feat/pricing-fe-rework` as a tracking branch
  (NOT a detached HEAD this time — git worktree was created by the coordinator correctly)
- `git branch --show-current` → `feat/pricing-fe-rework`
- `git push origin feat/pricing-fe-rework` pushes directly to the PR branch

### Pattern: ng test mfe-pricing has no test target
- `mfe-pricing` project in angular.json only has: build, serve, esbuild, serve-original
- There is NO test target on mfe-pricing; tests are in the `frontend` project (ng test)
- `ng test --include="..."` fails because NativeFederation build target is incompatible
- Correct invocation for pricing specs only: `./node_modules/.bin/vitest run apps/mfe-pricing/src/app/pricing.component.spec.ts`
- pricing.service.spec.ts requires @mesell/core path alias → cannot run via bare vitest;
  runs correctly through `ng test` (Angular build resolves tsconfig paths)
- pricing.component.spec.ts: 129/129 PASS (all pure-function, no TestBed, no path aliases)

### Pattern: Pre-existing ng test build failures from mfe-auth/mfe-onboarding
- `ng test` fails at build stage: TS2339 errors on OtpVerifyComponent, LoginComponent, SignupComponent
  (errorMessage property missing from those components' public API)
- These are pre-existing develop failures, NOT caused by mfe-pricing work
- Pricing spec results confirmed clean via vitest direct invocation

### Pattern: commission_missing cleanup in spec type aliases
- Slice 1 updated ALERT_MESSAGES and model types but left local type aliases in spec describe blocks
  using `type PricingErrorState = 'unavailable' | 'commission_missing' | ...`
- Slice 2 task: remove `'commission_missing'` from those local aliases (4 occurrences)
- Safe occurrences to KEEP: JSDoc file header, section separator comments, describe() labels —
  these document the ABSENCE of commission_missing, not its presence as a live type value
- Safe occurrences in component.ts: `*   - commission_missing...` lines in DELETED JSDoc block

### Build result (2026-06-18 slice-2)
- mfe-pricing build: GREEN — Application bundle generation complete, 3.618s, zero TS errors
- pricing.component.spec.ts: 129/129 pass (7 added meeshoPriceError tests, TODO markers gone)
- Commit: 5199ac2 on feat/pricing-fe-rework (pushed to PR #287)
- STATUS_FRONTEND.md updated at /private/tmp/mesell-wt/pricing-fe-rework/docs/status/STATUS_FRONTEND.md

---
