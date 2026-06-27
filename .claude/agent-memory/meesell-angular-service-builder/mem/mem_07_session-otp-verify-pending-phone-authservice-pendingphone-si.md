## Session: otp-verify-pending-phone — AuthService pendingPhone signal (2026-06-20)

**Branch/commit:** fix/otp-verify-pending-phone @ e7e919c
**Worktree:** /tmp/mesell-wt/otp-fix

### Root cause (diagnosed by coordinator SPEC)
history.state is wiped by Native Federation's full-document reload on first remote fetch.
otp-verify.component.ts ngOnInit (L176) hard-redirects to /login when state.phone is missing.
Fix: carry the pending phone in an in-memory signal on AuthService (the existing root singleton)
so it survives across the step navigation. FE-D5: never persisted.

### API added to AuthService

Location: `frontend/libs/core/services/auth.service.ts`
Private field: `private readonly _pendingPhone: WritableSignal<string | null> = signal<string | null>(null);`

Public methods:
  - `setPendingPhone(phone: string): void` — call in login.component.ts after OTP send success,
    before router.navigate(['/otp-verify'])
  - `pendingPhone(): string | null` — call in otp-verify.component.ts ngOnInit instead of
    history.state?.phone; returns null when no phone is waiting
  - `clearPendingPhone(): void` — call in otp-verify.component.ts after consuming the phone
    (success + ngOnDestroy) to prevent stale state

Barrel export: no change needed — `export { AuthService }` in `frontend/libs/core/index.ts`
already re-exports all public methods. Components import via `@mesell/core` alias as always.

CRITICAL design choices:
  - DOES NOT clear on logout() or forceLogout() — the component owns the lifecycle.
    A forceLogout during OTP verification must not lose the phone before the component
    can redirect cleanly. The component calls clearPendingPhone() in ngOnDestroy.
  - WritableSignal<string|null> not BehaviorSubject — matches the existing signal style
    on _token and _user. Consistent with Decision 10 (no NgRx; signals for component-local
    reactive state; BehaviorSubject for shared Observable streams — phone is not a stream).
  - This is strictly in-memory. Adding a signal field to AuthService is zero-cost and
    cheaper than a new dedicated PendingAuthService (avoided the extra barrel export + DI token).

### Spec coverage (6 new tests, auth.service.spec.ts)
- pendingPhone() is null by default
- setPendingPhone sets; pendingPhone() returns it
- clearPendingPhone resets to null
- setPendingPhone overwrites a previous value
- pendingPhone does NOT clear on logout()
- pendingPhone does NOT clear on forceLogout()

### tsc results
- mfe-auth tsconfig.app.json: EXIT 0
- shell tsconfig.app.json: EXIT 0
- workspace tsconfig.spec.json: 0 NEW errors (only pre-existing mfe-pricing TS2352/TS2367)
- ng test: blocked by same pre-existing mfe-pricing build error (known, unrelated)

### Component-builder hand-off spec (for next dispatch)
login.component.ts:
  1. Inject AuthService (already injected).
  2. After OTP send API succeeds (before navigating), call: `this.auth.setPendingPhone(this.phoneForm.value.phone)`.
  3. Then: `this.router.navigate(['/otp-verify'])`.

otp-verify.component.ts:
  1. Inject AuthService (already injected).
  2. In ngOnInit, REPLACE: `const phone = this.route.snapshot.data?.['phone'] ?? history.state?.phone`
     WITH: `const phone = this.auth.pendingPhone();`
  3. If phone is null/empty → redirect to /login (existing behaviour preserved).
  4. Else → proceed with OTP verify using the phone.
  5. After consuming phone (on success path): call `this.auth.clearPendingPhone()`.
  6. In ngOnDestroy (or DestroyRef): call `this.auth.clearPendingPhone()` to handle back-nav.
