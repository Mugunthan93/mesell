## Session 2026-06-20 — razorpay-dev-mock — PlansComponent mock guard {#razorpay-dev-mock-2026-06-20}

### Task
Add a dev-mock early-return guard in PlansComponent.subscribe() next-handler.
Worktree: /tmp/mesell-wt/razorpay-dev-mock, branch: feature/razorpay-dev-mock.

### Route touched
`/billing/plans` — mfe-billing (PlansComponent)

### Services consumed
`BillingApiService.subscribe()` (response carries `BillingCheckout` with optional `mock?: boolean`)

### Pattern: DEV-MOCK early return before widget open
- The mock guard lives in the `next:` handler of `this.billing.subscribe(tier).subscribe({...})`
- Insert at the TOP of the `next:` callback, BEFORE `this.rzpCheckout.openWidget(...)`:
  ```typescript
  if (resp.checkout.mock) {
    this.checkoutState.set('pending');
    this._startPolling(tier);
    return;
  }
  ```
- The `return` must come after the two state-setter + poll calls — it exits the `next:` callback only
- No change to `openWidget`, `_startPolling`, `_clearPoll`, poll utils, trial, or cancel
- `BillingCheckout.mock?: boolean` is already optional — when absent (normal path) the guard is a falsy no-op

### Pattern: PlansStateProxy spec technique — mock branch mirroring
- The spec uses a `PlansStateProxy` plain class to mirror the component's state machine
- When extending the component's `subscribe()` next-handler, the PROXY's `subscribe()` must also get the same guard so existing spec tests remain consistent
- Add the mock field to the proxy's inline type: `{ checkout: { key_id: string; tier: string; mock?: boolean } }`
- New `describe` block verifies: (1) widget skipped + state=pending, (2) poll activates, (3) normal path unaffected

### Vitest runner note
- Direct vitest invocation: `./node_modules/.bin/vitest run apps/mfe-billing/src/app/plans/plans.component.spec.ts`
- Plans + plan-card: 61/61 pass (45 plans including 3 new mock-branch, 16 plan-card)
- tsc --noEmit on both mfe-billing/tsconfig.app.json and tsconfig.spec.json: CLEAN
  (pre-existing mfe-pricing spec errors TS2352/TS2367 remain — NOT new)

### Commit
- Branch: feature/razorpay-dev-mock
- Commit: 57099df
- Files: `frontend/apps/mfe-billing/src/app/plans/plans.component.ts` + `.spec.ts` only
- git add by explicit path (NOT git add -A)

---
