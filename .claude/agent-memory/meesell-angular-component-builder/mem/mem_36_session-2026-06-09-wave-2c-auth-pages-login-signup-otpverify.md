## Session 2026-06-09 — Wave 2C Auth Pages — Login + Signup + OtpVerify {#wave-2c-auth-pages}

### Routes touched
`/login` + `/signup` + `/otp-verify` — features/auth/

### Services consumed
`AuthService` (core, `setSession()` + `isAuthenticated()`) — existing; `Router` — existing

### Pattern: Vitest uses toBeTruthy()/toBeFalsy(), NOT Jasmine's toBeTrue()/toBeFalse()
- This project uses `@vitest/expect` (Vitest 4.1.8) — NOT Jasmine.
- Jasmine matchers `toBeTrue()` + `toBeFalse()` do NOT exist in Vitest — TS2339 compile error.
- CORRECT: `toBeTruthy()` / `toBeFalsy()` — these are standard Vitest/Jest matchers.
- The task spec provided `toBeTrue()` / `toBeFalse()` in the spec examples — override them.
- The distinction is only in the Jasmine → Vitest migration context; always use Vitest matchers here.

### Pattern: Option A (flat stubs updated in place + otp-verify subdir)
- login.component.ts and signup.component.ts updated in place at `features/auth/` flat level.
- otp-verify lives in `features/auth/otp-verify/otp-verify.component.ts`.
- app.routes.ts import paths: `./features/auth/login.component`, `./features/auth/signup.component`, `./features/auth/otp-verify/otp-verify.component`.

### Pattern: /otp-verify as top-level route (not under auth layout parent)
- AuthLayoutComponent uses `<ng-content />` — NOT `<router-outlet />`.
- Each auth page wraps itself in `<mee-auth-layout>...</mee-auth-layout>`.
- `/otp-verify` is added as a SIBLING to `/login` and `/signup` in app.routes.ts (same top-level array).
- DO NOT nest auth pages under an AuthLayoutComponent parent route.

### Pattern: setInterval countdown with signal.update()
- `private intervalId?: ReturnType<typeof setInterval>` — use this type for cross-platform compatibility.
- `countdown.update(v => v - 1)` + `clearInterval(this.intervalId)` when countdown reaches 0.
- Extract to `private startCountdown(): void` so `ngOnInit()` and `resendOtp()` both call it.
- `ngOnDestroy(): void { clearInterval(this.intervalId); }` prevents interval leak on route change.

### Pattern: PrimeNG InputOtp with ReactiveFormsModule
- `p-inputotp` (PrimeNG 21) + `formControlName="otp"` — reactive form binding works directly.
- Import: `InputOtp` from `'primeng/inputotp'` (standalone class, not NgModule).
- `[length]="6"` sets the number of OTP input boxes.
- For 6-digit OTP: `Validators.minLength(6), Validators.maxLength(6)` on the FormControl.
- `styleClass="w-full justify-center"` centers the OTP input boxes.

### Pattern: auth.setSession() called ONLY on successful OTP verify
- Login/Signup: navigate to `/otp-verify`, do NOT call setSession.
- OtpVerifyComponent.onSubmit(): setTimeout → setSession → navigate('/dashboard').
- FE-D5 compliant: token stored in-memory via AuthService signal, never localStorage.

### Build result (2026-06-09 Wave 2C)
- otp-verify-component lazy chunk: 11.70 kB raw / 3.86 kB transfer
- signup-component lazy chunk: 3.49 kB raw / 1.31 kB transfer
- login-component lazy chunk: 3.01 kB raw / 1.20 kB transfer
- 17/17 tests passing (6 spec files)
- ng build: ZERO errors, 2.497s

---
