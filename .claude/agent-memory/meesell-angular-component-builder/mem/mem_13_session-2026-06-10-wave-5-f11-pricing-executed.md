## Session 2026-06-10 — Wave 5 F11 Pricing EXECUTED {#wave5-f11-pricing}

### Task
Built/fixed F11 PricingComponent at `/catalogs/:id/pricing`. Client-side P&L breakdown with
reactive form (MRP + target margin), native range slider (no mee-slider primitive), margin badge
(POSITIVE/NEGATIVE), and Save & Continue nav. Spec described all 4 files. The component,
model, and utils files were pre-existing and correct. Only the spec was broken.

### Gate Results
- Gate 1 BUILD: PASS -- pnpm run build: zero errors (2.862s)
- Gate 2 ROUTE: INFO -- route not yet in app.routes.ts (coordinator scope -- not my gate)
- Gate 3 TESTS: PASS -- 29/29 pricing spec tests passing (7 describe blocks, pure function)
- Gate 4 BOUNDARY: PASS -- zero primeng imports in features/pricing/

### Problem: spec had describe-is-not-defined at line 10
- The pre-existing spec.ts was missing `import { describe, it, expect } from 'vitest'`
- Vitest does NOT auto-inject globals unless `globals: true` is set in vitest config
- This project has NO vitest.config.ts -- the runner uses the Angular build:unit-test builder
- All specs that use TestBed had been set up in a different context (test-setup.ts with zone.js)
- Pure-function spec files MUST explicitly import `{ describe, it, expect }` from `'vitest'`
- Reference: preview.component.spec.ts first line: `import { describe, it, expect } from 'vitest'`

### Problem: TestBed tests also present in original spec
- The original spec mixed pure-function tests with TestBed-based component tests
- TestBed tests would crash with the documented PrimeNG 21 ngModule null error
- Dispatch mandated the proven workaround: extract to pricing.model.ts, test pure functions only
- Rewrote entire spec as 100% pure-function Vitest tests -- 29 tests across 7 describe blocks

### Pattern: Math.round(0.5) = 1 in JavaScript
- dispatch doc showed commission_amt=22 (450 * 0.05 = 22.5 -> "rounded to 22")
- Actual JS: Math.round(22.5) = 23 (rounds .5 UP, not banker's rounding)
- Spec values for MRP=899, margin=150: commission=23, gst=1, payout=426, net_margin=276
- The important invariant (net_margin > 0 = positive badge) still holds correctly at 276 > 0
- LESSON: always verify formula against actual JS Math.round behavior, not mental arithmetic

### Pattern: native range slider (V1 pattern)
- No mee-slider in UI Kit; dispatch specifies native `<input type="range">`
- `[value]="sliderMrp()"` -- one-way binding from signal to DOM value
- `(input)="onSliderInput($event)"` -- fires on every drag tick (not mouseup)
- `(event.target as HTMLInputElement).valueAsNumber` -- type-safe cast required
- `accent-color: var(--mee-color-primary)` -- MeeSell orange thumb via CSS
- `min-height: 44px` on the input element for 44px touch target
- Document this as "native range for V1 margin slider" pattern

### Pattern: two-way sync between range slider and text input
- `onSliderInput(event)`: set `sliderMrp.set(val)` AND `form.patchValue({ mrp: val })`
- `onMrpInput()`: read `form.controls.mrp.value`, clamp to [100, 5000], `sliderMrp.set(clamped)`
- The clamp prevents slider from jumping to invalid MRP values during manual text entry
- IMPORTANT: patchValue does NOT trigger (input) event -- no infinite loop risk

### Pattern: client-side P&L simulation (no HTTP wiring)
- `onCalculate()`: if form valid, call `computePnlBreakdown(mrp, margin)` synchronously
- `calculating` signal set true/false around the call but call is synchronous (no async needed)
- `breakdown.set(result)` updates template via OnPush change detection
- `marginIsPositive = computed(() => breakdown()?.net_margin > 0)` drives badge color
- Design tokens: `var(--mee-color-success)` for positive, `var(--mee-color-error)` for negative

### Build result (2026-06-10 Wave 5 F11 Pricing)
- pnpm run build: ZERO errors (2.862s)
- 29/29 pricing spec tests passing (7 describe blocks)
- pricing-component lazy chunk: not visible in build output (route not yet registered)

---
