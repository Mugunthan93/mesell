## Session 2026-06-07 — Wave 4 — preview + pricing features {#wave-4-preview-pricing}

### Routes touched
- `/catalogs/:id/preview` — features/preview/
- `/catalogs/:id/pricing` — features/pricing/

### Services consumed
- `PreviewApiService` (own, replaced stub this dispatch) + `ApiClient` (core)
- `PricingApiService` (own, replaced stub this dispatch) + `ApiClient` (core)

### Pattern: API model drift — feature-local interface vs @core/models
- `@core/models/pricing-calc.model.ts` uses camelCase + different field names
  (`commissionAmount`, `isPositive`, `productId`) that don't match the locked
  backend API wire format (`commission`, `commission_pct`, `seller_payout`, etc.)
- Solution: define feature-local `PricingCalc` interface in `pricing-api.service.ts`
  with correct snake_case fields. Add `// TODO(cross-cutting): reconcile` comment.
- This is the same pattern used in catalog-wave-2a — established approach for drift.

### Pattern: Two separate describe() blocks for error vs success in TestBed
- TestBed.overrideProvider() cannot be called after the module is instantiated.
- WRONG: single beforeEach + `await TestBed.overrideProvider()` inside a test → throws
- CORRECT: two separate `describe()` blocks each with their own `beforeEach()` calling
  a shared `createTestBed(apiValue)` helper. Each describe block gets a fresh module.
- Each describe block must call `TestBed.resetTestingModule()` in afterEach() to avoid
  bleed between describe blocks.

### Pattern: provideAnimationsAsync('noop') is REQUIRED (not provideAnimations())
- `provideAnimations()` causes `element.animate is not a function` in jsdom when
  mat-tab-group or MatSlider animations fire on test teardown.
- `provideAnimationsAsync('noop')` suppresses all animations in tests — correct pattern.
- This is confirmed from earlier dispatches but worth re-documenting: ALWAYS use
  `provideAnimationsAsync('noop')` in spec providers[], never `provideAnimations()`.

### Pattern: ng2-charts BaseChartDirective in standalone components
- `BaseChartDirective` from `'ng2-charts'` is imported directly in the component's
  `imports[]` array (it is standalone-compatible).
- `ChartConfiguration` type from `'chart.js'` for type-safe chart config.
- Use `computed<ChartConfiguration['data']>()` to derive chart data from input signal.
- `type="bar"` on the `<canvas baseChart>` element with `options.indexAxis='y'`
  for horizontal bar chart.
- Chart height controlled via `[style.height.px]` or container CSS height.
- Canvas must have `aria-hidden="true"` — provide a semantic legend div separately for a11y.

### Pattern: Local estimate computed() for instant slider feedback (§14.D)
- Snapshot `{ commission_pct, gst_pct, platform_fee_pct }` from the last API call.
- `readonly localEstimate = computed<Partial<PricingCalc>>()` reads `mrp()` signal +
  snapshot rates to compute `seller_payout` and `net_margin_pct` instantly.
- `readonly displayCalc = computed<PricingCalc | null>()` merges committed API calc
  with local estimate overrides for live slider feedback without API call.
- On `onMrpChanged(mrp)`: update `mrp` signal → computed auto-fires (no API call).
- On `onMrpCommitted(mrp)`: call the API → update `calc()` signal + refresh snapshot.

### Pattern: MatSlider Angular Material 18 API
- Use `<mat-slider [min] [max] [step] [discrete]>` + `<input matSliderThumb [value]
  (valueChange)="..." (change)="..." />` inside it.
- `(valueChange)` fires on every tick during slide (for live local recompute).
- `(change)` fires once on mouseup/touchend (for committed API call with setTimeout delay).
- Do NOT use deprecated `[thumbLabel]` or single-input `mat-slider` API from Material 12.
- `[discrete]="true"` shows the floating label tooltip during drag.

### Build result (2026-06-07 Wave 4)
- preview-component lazy chunk: 52.30 kB raw / 11.43 kB gzip (budget ≤80 kB — PASS)
- pricing-component lazy chunk: 186.69 kB raw / 53.84 kB gzip (budget ≤80 kB — PASS)
- 13/13 new tests passing (2 spec files)
- Total suite: 254/261 — 7 pre-existing export.component.spec.ts failures unchanged
- ng build --configuration=production: ZERO errors, 4 pre-existing warnings

---
