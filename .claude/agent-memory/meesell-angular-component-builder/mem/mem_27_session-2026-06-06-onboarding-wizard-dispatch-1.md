## Session 2026-06-06 — Onboarding Wizard Dispatch 1 {#onboarding-dispatch-1}

### Route touched
`/onboarding` — features/account/onboarding/

### Services consumed
None (Dispatch 1 is a pure skeleton — no API calls, no service injection beyond Router).

### Pattern: mat-stepper with @ViewChild reference
- `@ViewChild('stepper') stepper!: MatStepper;` — use template variable `#stepper` on `<mat-stepper>`.
- Call `this.stepper?.next()` with optional chaining — ViewChild is defined after ngAfterViewInit,
  but for button-triggered calls it is always initialized. Optional chaining is safe.
- `MatStepperModule` import covers `mat-stepper`, `mat-step`, `matStepperPrevious`, `matStepLabel`, `MatStepper` class.
- `[linear]="false"` for skeleton — allows free navigation without step validators.

### Pattern: mat-step [completed] bound to a signal
- `[completed]="phase1Submitted()"` — `[completed]` is a boolean @Input on MatStep.
- Calling the signal `()` in the template binding is correct Angular 18 syntax.
- Setting signal (`this.phase1Submitted.set(true)`) + calling `stepper.next()` in the same
  method is the correct combined pattern.

### Pattern: mat-spinner inside a disabled button
- `<button mat-flat-button [disabled]="saving()">` — disabled state from signal.
- Inline spinner: `<mat-spinner diameter="16" class="inline-block mr-2">` inside `@if (saving())`.
- `MatProgressSpinnerModule` must be in imports[].

### Pattern: matStepperPrevious directive
- `<button mat-stroked-button matStepperPrevious>` — no (click) handler needed.
- Directive (from MatStepperModule) calls stepper.previous() internally.

### Pattern: Fake timers for setTimeout navigation tests (Vitest)
- `vi.useFakeTimers()` before calling the method under test.
- `vi.advanceTimersByTime(300)` to flush the 300ms timeout.
- `vi.useRealTimers()` in `afterEach()` for test isolation.
- `vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true)` — set spy BEFORE calling method.
- After `vi.advanceTimersByTime(300)`: saving() resets to false AND navigate spy is called in the same tick.

### Pattern: Asserting 3 mat-stepper steps in DOM
- `mat-step` is not a DOM element — renders as `.mat-step-header` entries.
- Query: `fixture.nativeElement.querySelectorAll('.mat-step-header')` → expect length 3.

### Tailwind classes verified for onboarding
- `bg-bg`, `bg-surface`, `bg-surface-variant`, `text-on-surface`, `text-on-surface-variant`
- `rounded-mee-lg`, `rounded-mee-md`, `shadow-mee-2`, `border-outline`
- `text-mee-sm`, `text-mee-lg`, `text-mee-2xl`
- NOTE: `border-b border-outline` — both classes required (`border-b` sets width, `border-outline` sets color).

### i18n flat-key format (en.json)
- en.json uses flat dot-notation keys: `"onboarding.steps.businessDetails": "..."`
- NOT nested JSON objects — that would break Transloco's flat-key parser.

### Build result (2026-06-06 onboarding dispatch 1)
- ng build --configuration=production: ZERO errors
- onboarding-component lazy chunk: 36.19 kB raw / 8.24 kB gzip (budget ≤80 kB gzip — PASS)
- 4/4 new tests pass; NG0914 + Material theme warnings in stderr are expected (pre-documented)

---
