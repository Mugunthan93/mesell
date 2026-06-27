## Session 2026-06-09 — Wave 5 F13 Profile Page {#wave5-f13-profile}

### Route touched
`/profile` — features/profile/

### Services consumed
`AuthService` (core, `currentUser` signal + `logout()`) + `Router` (navigate to `/login`)

### Finding: Component was already substantially complete
`profile.component.ts` was well-authored from a prior session with correct structure:
- Standalone + OnPush, inject(FormBuilder), inject(AuthService), inject(Router)
- Reactive form with `name` control (required, minLength 2, maxLength 60)
- `saving`, `saved`, `errorMessage` signals
- `displayPhone`, `formattedPhone`, `planSeverity`, `planLabel`, `avatarInitial` computed signals
- Correct mee-* imports from `../../ui/...` — ZERO PrimeNG, ZERO Angular Material
- Route in app.routes.ts inside shell canActivate:[authGuard] (pre-existing)
- Full spec with 16 tests already authored

Two bugs found and fixed:

### Bug 1: computed() signal for FormControl-derived state
**Problem:** `nameError` was a `computed()` signal that reads `this.form.get('name')?.valid`,
  `ctrl.pristine`, `ctrl.hasError('required')` etc. These are FormControl properties, NOT
  Angular signals. `computed()` has no way to track FormControl state changes as reactive
  dependencies. The computed value would be stale after `setValue()` + `markAsDirty()`.
**Root cause:** Angular's `computed()` only tracks signals (or `Signal<T>` wrappers) as
  dependencies. FormControl state is plain JS object mutation — invisible to `computed()`.
**Fix:** Convert `nameError` from `computed<string | undefined>(() => {...})` to a plain
  getter method `nameError(): string | undefined { ... }`.
**Template impact:** `[error]="nameError()"` in the template calls it as a method — Angular
  re-evaluates on every change detection cycle. Works identically with OnPush when
  `markAllAsTouched()` is called (which triggers CD).
**Rule:** NEVER use `computed()` to wrap FormControl state properties (valid, invalid,
  pristine, dirty, touched, errors, hasError). Use a plain getter method instead.

### Bug 2: Promise-wrapped setTimeout + vi.useFakeTimers incompatibility
**Problem:** `onSubmit()` used `void new Promise<void>(resolve => setTimeout(resolve, 800)).then(...)`.
  With `vi.useFakeTimers()`, `vi.advanceTimersByTime(800)` advances the clock, which fires
  the `setTimeout` callback (resolving the Promise). BUT the `.then()` callback is now queued
  as a **microtask**. `vi.advanceTimersByTime()` does NOT flush the microtask queue — it only
  advances macrotask timers. The `.then()` callback containing `saving.set(false)` never ran
  synchronously, leaving `saving()` stuck at `true`.
**Fix:** Replace `new Promise + .then()` with direct nested `setTimeout` calls:
  ```typescript
  setTimeout(() => {
    this.saving.set(false);
    this.saved.set(true);
    setTimeout(() => { if (this.saved()) this.saved.set(false); }, 3000);
  }, 800);
  ```
  Direct `setTimeout` callbacks ARE fired synchronously by `vi.advanceTimersByTime()`.
**Rule:** In Angular components that need to be testable with Vitest fake timers:
  - Use direct `setTimeout(callback, ms)` for delayed state updates.
  - NEVER wrap them in `new Promise<void>(resolve => setTimeout(resolve, ms)).then(...)`.
  - If async/await is needed, use `async onSubmit()` with `await new Promise(r => setTimeout(r, ms))`
    AND flush microtasks explicitly with `await Promise.resolve()` AFTER `vi.advanceTimersByTime()`.

### Bug 3: TestBed contamination in full suite (pre-existing, not profile-specific)
**Problem:** When run in the full suite, a prior failing spec (catalog-form.spec.ts NG0300 error)
  leaves TestBed in an instantiated state. The profile spec's `beforeEach` then fails with
  "Cannot configure the test module when the test module has already been instantiated."
**Fix:** Add `TestBed.resetTestingModule()` at the TOP of `beforeEach()`, BEFORE `configureTestingModule`.
**Rule:** Any spec that has `afterEach(() => { TestBed.resetTestingModule(); })` should ALSO
  add a defensive `TestBed.resetTestingModule()` at the start of `beforeEach()`. This provides
  protection from contamination by OTHER test files that fail to reset properly.

### Build result (2026-06-09 Wave 5 F13 Profile)
- pnpm run build: ZERO errors, 3.253s
- profile-component lazy chunk: 4.30 kB raw / 1.70 kB gzip (budget ≤80 kB — PASS)
- 16/16 profile tests pass in full suite run (13/16 were passing before; 3 fixed)
- Full suite: 213/264 passing; 51 pre-existing failures in unrelated files
  Pre-existing failures: shell.spec.ts, catalog-new.spec.ts, dashboard.spec.ts,
  catalog-form.spec.ts, images.spec.ts, preview.spec.ts, pricing.spec.ts
- Boundary: features/profile/ has ZERO primeng imports, ZERO @angular/material imports

---
