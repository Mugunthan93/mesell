## Session: razorpay-dev-mock FE model (2026-06-20)

**Branch/commit:** feature/razorpay-dev-mock @ b3d60f0
**Worktree:** /tmp/mesell-wt/razorpay-dev-mock
**Spec:** docs/plans/features/razorpay-integration/DEV_MOCK_MODE_SPEC.md §4.2

### Change summary
Added `mock?: boolean` (optional) to the `BillingCheckout` interface in
`frontend/apps/mfe-billing/src/app/billing.model.ts` (line 68, after `tier`).

### Why optional (not required)
Backend sets `mock: bool = Field(default=False)` — it is always present on the wire but
defaults False. TypeScript optional (`?`) makes existing test fixtures that omit the field
still structurally valid, avoiding spec churn. A non-optional `boolean` would also work
since the backend always includes it, but optional is more defensive for any mock stubs.

### DTO mapping: none needed
`BillingApiService.subscribe()` uses `api.post<BillingSubscribeResponse>(...)` — raw typed
generic pass-through. No explicit DTO transform exists in the service. `mock` flows from
JSON → typed interface automatically. RULE: when adding a field to a billing model, always
grep the service for explicit `{ checkout: { ... } }` construction or `map()` operators
that would drop the new field. In this case: none found.

### tsc pattern for worktree (no node_modules)
Worktrees have no node_modules. Pattern: `ln -s /main/project/frontend/node_modules worktree/frontend/node_modules`
Then: `cd worktree/frontend && node_modules/.bin/tsc --noEmit -p apps/<mfe>/tsconfig.app.json`

### ng test isolation problem on 8GB machine
`ng test mfe-billing` builds entire workspace → hits pre-existing mfe-pricing spec TS errors
(TS2352 / TS2367 — confirmed pre-existing from pricing-fe-rework session). Cannot be isolated.
WORKAROUND: use `vitest run --globals <spec-file>` for specs that only use local imports.
Specs needing TestBed (Angular DI / jsdom / `window`) or `@mesell/*` path aliases MUST use
`ng test` and cannot be run safely bare. For model-only changes, confirm clean via:
  1. tsc --noEmit on tsconfig.app.json (compile gate)
  2. tsc --noEmit on tsconfig.spec.json (spec type gate, filter known pre-existing)
  3. vitest run on any pure-function spec that imports from the changed model

### Hand-off
Component builder next: add `if (resp.checkout.mock)` branch in plans.component.ts
`subscribe()` next: handler per DEV_MOCK_MODE_SPEC.md §4.3.
