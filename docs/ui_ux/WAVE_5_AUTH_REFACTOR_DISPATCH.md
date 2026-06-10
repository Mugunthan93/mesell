# WAVE 5 — AUTH REFACTOR (F2/F3/F4) — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Auth Refactor (Login / Signup / OTP Verify) |
| **Date authored** | 2026-06-09 |
| **Status** | READY |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder |
| **Depends on** | Wave 3 UI Kit complete (mee-input, mee-otp-input, mee-button in `ui/index.ts`) + Wave 4 composites complete |
| **Nature** | REFACTOR — not a rebuild; 17 tests must still pass after |

---

## 1. Module Summary

| Property | Value |
|---|---|
| Routes | `/login`, `/signup`, `/otp-verify` |
| Components | `LoginComponent`, `SignupComponent`, `OtpVerifyComponent` |
| Selectors | `mee-login`, `mee-signup`, `mee-otp-verify` |
| Current file paths | `features/auth/login.component.ts`, `features/auth/signup.component.ts`, `features/auth/otp-verify/otp-verify.component.ts` |
| Purpose | Phone-OTP auth pages, simulated flow (no real API yet) |
| Current status | BUILT — but violate boundary rule (direct `primeng/...` imports) |
| Refactor goal | Swap every direct PrimeNG import/element for the equivalent `mee-*` UI Kit wrapper |

All three pages are already wired in `app.routes.ts` as top-level lazy routes. The `AuthLayoutComponent` (`mee-auth-layout`) uses `<ng-content />` — keep this pattern; do not change it.

---

## 2. Dependencies

**UI Kit primitives (from `../../ui` or `@mee/ui`):**

| Kit component | Selector | Replaces |
|---|---|---|
| `MeeInputComponent` | `mee-input` | `<input pInputText>` + `InputText` from `primeng/inputtext` |
| `MeeOtpInputComponent` | `mee-otp-input` | `<p-inputotp>` + `InputOtp` from `primeng/inputotp` |
| `MeeButtonComponent` | `mee-button` | `<p-button>` + `Button` from `primeng/button` |

**Composites:** none required for these three pages.

**Layout:** `AuthLayoutComponent` from `../../layouts/auth-layout/auth-layout.component` — already used, keep as-is.

**Services:** `AuthService` from `../../core/services/auth.service` (OtpVerifyComponent only, already injected).

**API endpoints:** SIMULATE — no HttpClient calls. `setTimeout(1500)` pattern retained from Wave 2C.

⚠️ BOUNDARY: after refactor, `grep -r "from 'primeng" features/auth/` MUST return ZERO lines. Every `primeng/...` import is removed; every PrimeNG element is replaced with a `mee-*` wrapper.

---

## 3. Files to Create / Modify

### Modified files (in-place edit — do NOT move or rename)

| File | Action |
|---|---|
| `features/auth/login.component.ts` | MODIFY — swap imports and template elements |
| `features/auth/signup.component.ts` | MODIFY — swap imports and template elements |
| `features/auth/otp-verify/otp-verify.component.ts` | MODIFY — swap imports and template elements |
| `features/auth/login.component.spec.ts` | MODIFY — update selectors from `p-button` to `mee-button`; stub `MeeInputComponent`, `MeeButtonComponent` |
| `features/auth/signup.component.spec.ts` | MODIFY — same as login spec treatment |
| `features/auth/otp-verify/otp-verify.component.spec.ts` | MODIFY — update selector from `p-inputotp` to `mee-otp-input`; stub `MeeOtpInputComponent`, `MeeButtonComponent` |

### No new files. `app.routes.ts` is NOT touched. Auth-layout is NOT touched.

### Exact import changes per file

**`login.component.ts`**

```
REMOVE:  import { InputText } from 'primeng/inputtext';
REMOVE:  import { Button } from 'primeng/button';
ADD:     import { MeeInputComponent } from '../../ui/input/input.component';
ADD:     import { MeeButtonComponent } from '../../ui/button/button.component';
```

**`signup.component.ts`**

```
REMOVE:  import { InputText } from 'primeng/inputtext';
REMOVE:  import { Button } from 'primeng/button';
ADD:     import { MeeInputComponent } from '../../ui/input/input.component';
ADD:     import { MeeButtonComponent } from '../../ui/button/button.component';
```

**`otp-verify/otp-verify.component.ts`**

```
REMOVE:  import { InputOtp } from 'primeng/inputotp';
REMOVE:  import { Button } from 'primeng/button';
ADD:     import { MeeOtpInputComponent } from '../../../ui/otp-input/otp-input.component';
ADD:     import { MeeButtonComponent } from '../../../ui/button/button.component';
```

> If `ui/index.ts` barrel is stable, use `@mee/ui` path alias for all three adds.

---

## 4. Component Spec

All three pages retain existing business logic, signals, and form definitions. Only the template elements change.

### 4.1 LoginComponent — template element changes

```
360px layout (inside mee-auth-layout):
┌─────────────────────────────────────┐
│  MeeSell                            │  ← from auth-layout
│                                     │
│  Welcome back              [h1]     │
│  Enter your mobile number  [p]      │
│                                     │
│  Mobile Number             [label]  │
│  ┌───────────────────────────────┐  │
│  │  mee-input prefix="+91"      │  │  ← was: <div.phone-field> + <input pInputText>
│  └───────────────────────────────┘  │
│  [error span if touched+invalid]    │
│                                     │
│  [ mee-button "Continue →" ]        │  ← was: <p-button>
│                                     │
│  Don't have an account?             │
│  Sign up                [routerLink]│
└─────────────────────────────────────┘
```

**Template swaps:**
- Remove the `<div class="phone-field">` wrapper + `<span class="prefix">` + `<input pInputText>`.
- Replace with `<mee-input [label]="'Mobile Number'" [prefix]="'+91'" [placeholder]="'10-digit number'" [error]="phoneError()" formControlName="phone" [required]="true">`.
- Remove `<p-button ...>`, replace with `<mee-button [label]="'Continue →'" [loading]="loading()" [disabled]="form.invalid" [fullWidth]="true" (clicked)="onSubmit()">`.
- The `<form (ngSubmit)="onSubmit()">` wrapper stays; type="submit" is removed from `mee-button` (use `(clicked)` output instead).
- Add `readonly phoneError = computed(() => this.form.get('phone')?.touched && this.form.get('phone')?.invalid ? 'Enter a valid 10-digit mobile number' : undefined);`

**Signals retained:** `loading = signal(false)`. Form definition unchanged.

**Styles:** Remove `:host ::ng-deep .p-button` and `:host ::ng-deep p-button` pierce rules — `mee-button` owns its own sizing. Remove `.phone-field` and `.prefix` rules — `mee-input` owns prefix rendering. Keep heading/subtitle/label/error-text/footer styles.

### 4.2 SignupComponent — template element changes

Same pattern as Login. Additional field: `name` input.
- `<input pInputText id="signup-name" formControlName="name">` → `<mee-input [label]="'Full Name'" formControlName="name" [required]="true" [error]="nameError()">`.
- `<div class="phone-field">` + `<input pInputText>` → `<mee-input [label]="'Mobile Number'" [prefix]="'+91'" formControlName="phone" [required]="true" [error]="phoneError()">`.
- `<p-button label="Create Account">` → `<mee-button [label]="'Create Account'" [loading]="loading()" [disabled]="form.invalid" [fullWidth]="true" (clicked)="onSubmit()">`.
- Add `nameError` and `phoneError` computed signals analogous to Login.

### 4.3 OtpVerifyComponent — template element changes

```
360px layout:
┌─────────────────────────────────────┐
│  MeeSell                            │
│                                     │
│  Verify your number        [h1]     │
│  We sent a 6-digit code    [p]      │
│                                     │
│  Enter OTP                 [label]  │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐    │  ← mee-otp-input [length]=6
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘    │    was: <p-inputotp>
│  [error span if touched+invalid]    │
│                                     │
│  [ mee-button "Verify OTP" ]        │  ← was: <p-button>
│                                     │
│  Resend code in 30s (or Resend link)│
│  ← Back to login          [link]    │
└─────────────────────────────────────┘
```

**Template swaps:**
- Remove `<p-inputotp formControlName="otp" [length]="6" [integerOnly]="true">`.
- Replace with `<mee-otp-input [length]="6" (completed)="onOtpCompleted($event)">`.
- `mee-otp-input` uses the `completed` output (emits string of 6 digits). The `formControlName` binding is dropped in favour of writing the value into a signal on `completed`.
  - Add `readonly otpValue = signal('');`
  - `onOtpCompleted(val: string): void { this.otpValue.set(val); }`
  - In `onSubmit()`: use `this.otpValue()` instead of `this.form.get('otp')?.value`.
  - Keep form guard: `if (this.otpValue().length < 6) return;`
- Remove `<p-button label="Verify OTP">`, replace with `<mee-button [label]="'Verify OTP'" [loading]="loading()" [disabled]="otpValue().length < 6" [fullWidth]="true" (clicked)="onSubmit()">`.
- Remove `:host ::ng-deep .p-inputotp` and `p-button` pierce rules.
- `NgOnDestroy` + interval logic unchanged. `countdown` signal unchanged. `AuthService.setSession()` call unchanged (FE-D5 preserved).

> Note: `mee-otp-input` does not participate in a Reactive Form via `formControlName` — it emits via `(completed)` output. The form group for `otp` control can be removed from `OtpVerifyComponent` entirely, simplifying the component.

---

## 5. UI Kit Usage Map

| Template element | mee-* component | Key inputs | Key outputs |
|---|---|---|---|
| Phone text input (Login) | `mee-input` | `[label]`, `[prefix]="+91"`, `[placeholder]`, `[error]`, `[required]`, `formControlName="phone"` | CVA two-way |
| Name text input (Signup) | `mee-input` | `[label]`, `[error]`, `[required]`, `formControlName="name"` | CVA two-way |
| Phone text input (Signup) | `mee-input` | `[label]`, `[prefix]="+91"`, `[error]`, `[required]`, `formControlName="phone"` | CVA two-way |
| Submit button (Login) | `mee-button` | `[label]`, `[loading]`, `[disabled]`, `[fullWidth]="true"` | `(clicked)` |
| Submit button (Signup) | `mee-button` | `[label]`, `[loading]`, `[disabled]`, `[fullWidth]="true"` | `(clicked)` |
| OTP 6-box input | `mee-otp-input` | `[length]="6"`, `[disabled]="loading()"` | `(completed)` |
| Verify button | `mee-button` | `[label]`, `[loading]`, `[disabled]="otpValue().length < 6"`, `[fullWidth]="true"` | `(clicked)` |

All `mee-*` components have `ChangeDetectionStrategy.OnPush` — the `[error]` binding must use `computed()` signals so change detection propagates correctly.

---

## 6. API / Data

No API calls in this wave. Simulation pattern retained from Wave 2C:

```
Login/Signup: loading.set(true) → setTimeout(1500) → loading.set(false) → router.navigate(['/otp-verify'])
OtpVerify:    loading.set(true) → setTimeout(1500) → loading.set(false) → auth.setSession('mock-token', {...}) → router.navigate(['/dashboard'])
```

FE-D5 constraint: `setSession()` is called ONLY in `OtpVerifyComponent.onSubmit()` after simulated success. Not in Login, not in Signup.

---

## 7. Constraints

| Constraint | Rule |
|---|---|
| Zero PrimeNG imports | `grep -r "from 'primeng" features/auth/` must return ZERO |
| Standalone + OnPush | All 3 components keep `standalone: true` + `ChangeDetectionStrategy.OnPush` |
| Signals for local state | `loading`, `countdown`, `otpValue`, `phoneError`, `nameError` all `signal()` or `computed()` |
| Reactive Forms | Keep `ReactiveFormsModule` + `FormGroup` in Login + Signup; OtpVerify may drop form group (see §4.3) |
| Auth-layout wrapper | `<mee-auth-layout>` ng-content pattern is preserved — do NOT change |
| Flat routing | `app.routes.ts` not touched — routes stay as top-level lazy `loadComponent` |
| 44px touch targets | `mee-button [fullWidth]="true"` + `mee-input` both ensure ≥44px height internally |
| FE-D5 | `setSession()` only in OtpVerify on success |
| No `::ng-deep` | Remove all PrimeNG pierce rules; mee-* wrappers own their own styling |
| Test count maintained | 17 tests were passing before refactor; at least 17 must pass after |
| No backend calls | SIMULATE only |
| Tokens only | No hardcoded hex — `var(--mee-color-*)` CSS custom properties |
| Build gate | `cd frontend && pnpm run build` — zero errors after refactor |

---

## 8. Out of Scope

| Item | Owner / Wave |
|---|---|
| Real MSG91 OTP API wiring | Wave 6 (API integration) |
| Phone state passed between pages via router state | Wave 6 |
| `mee-input` or `mee-otp-input` implementation | Wave 3 (UI Kit) — must be done before this wave |
| JWT interceptor / RefreshInterceptor | Wave 6 |
| i18n / Tamil / Hindi labels | V1.5 |
| Countdown timer duration change | Out of scope (stays at 30 s) |
| Changing routing structure | Coordinator scope |
| Visual design changes (colours, spacing) | meesell-angular-ui-styler |

---

## 9. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| 1 BUILD | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| 2 ROUTES | Dev server: `/login`, `/signup`, `/otp-verify` | All three render, no blank screen, no console errors |
| 3 VALIDATION | Manual: empty form submit → error shown; valid form → button enables | Inline error text visible; button enables on valid input |
| 4 TESTS | `cd frontend && pnpm run test` | At minimum 17 tests pass (pre-refactor count); zero regressions |
| 5 VISUAL | Grep check | `grep -r "from 'primeng" features/auth/` → ZERO matches |

---

## 10. Paste-Ready Dispatch Block

```
═══════════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — AUTH REFACTOR (F2/F3/F4)
Agent: meesell-angular-component-builder (sonnet)
═══════════════════════════════════════════════════════════════════════

CONTEXT
───────
Wave 3 (UI Kit) + Wave 4 (Composites) must be complete before executing this.
Auth pages at features/auth/ are BUILT but violate the Layer-2 boundary rule:
they import primeng/... directly. Option A-full (ratified 2026-06-09) requires
ZERO primeng imports in any feature file. This dispatch refactors them.

This is NOT a rebuild. Business logic, routing, and tests are preserved.
Only the template elements and their imports change.

═══════════════════════════════════════════════════════════════════════

FILES TO MODIFY (no new files, no renames, no routing changes)
──────────────────────────────────────────────────────────────
  features/auth/login.component.ts              MODIFY
  features/auth/signup.component.ts             MODIFY
  features/auth/otp-verify/otp-verify.component.ts  MODIFY
  features/auth/login.component.spec.ts         MODIFY (update stubs + selectors)
  features/auth/signup.component.spec.ts        MODIFY (update stubs + selectors)
  features/auth/otp-verify/otp-verify.component.spec.ts  MODIFY (update stubs)

═══════════════════════════════════════════════════════════════════════

IMPORT CHANGES (exact — apply per file)
───────────────────────────────────────
login.component.ts:
  REMOVE: import { InputText } from 'primeng/inputtext';
  REMOVE: import { Button } from 'primeng/button';
  ADD:    import { MeeInputComponent } from '../../ui/input/input.component';
  ADD:    import { MeeButtonComponent } from '../../ui/button/button.component';

signup.component.ts:
  REMOVE: import { InputText } from 'primeng/inputtext';
  REMOVE: import { Button } from 'primeng/button';
  ADD:    import { MeeInputComponent } from '../../ui/input/input.component';
  ADD:    import { MeeButtonComponent } from '../../ui/button/button.component';

otp-verify/otp-verify.component.ts:
  REMOVE: import { InputOtp } from 'primeng/inputotp';
  REMOVE: import { Button } from 'primeng/button';
  ADD:    import { MeeOtpInputComponent } from '../../../ui/otp-input/otp-input.component';
  ADD:    import { MeeButtonComponent } from '../../../ui/button/button.component';

═══════════════════════════════════════════════════════════════════════

TEMPLATE SWAPS
──────────────
Login + Signup:
  <div.phone-field> + <input pInputText> → <mee-input [prefix]="'+91'" [label]="..." [error]="phoneError()" formControlName="phone">
  <input pInputText> (name field, Signup only) → <mee-input [label]="'Full Name'" [error]="nameError()" formControlName="name">
  <p-button> → <mee-button [label]="..." [loading]="loading()" [disabled]="form.invalid" [fullWidth]="true" (clicked)="onSubmit()">
  Add computed() signals: phoneError(), nameError() (return string | undefined)

OTP Verify:
  <p-inputotp formControlName="otp"> → <mee-otp-input [length]="6" [disabled]="loading()" (completed)="onOtpCompleted($event)">
  Add: otpValue = signal<string>('');  onOtpCompleted(v: string): void { this.otpValue.set(v); }
  Form group for otp control can be removed (mee-otp-input does not use formControlName)
  <p-button> → <mee-button [label]="'Verify OTP'" [loading]="loading()" [disabled]="otpValue().length < 6" [fullWidth]="true" (clicked)="onSubmit()">

STYLES:
  Remove all :host ::ng-deep .p-button / p-button / .p-inputotp pierce rules
  Remove .phone-field and .prefix CSS rules (mee-input owns prefix rendering)
  Retain: h1, .subtitle, label, .error-text, .footer-text, .resend-* rules

═══════════════════════════════════════════════════════════════════════

KEY CONSTRAINTS
───────────────
  • Zero primeng imports in features/auth/ after refactor
  • 17+ tests must pass (no regressions)
  • ng-content auth-layout pattern unchanged
  • app.routes.ts unchanged
  • FE-D5: setSession() only in OtpVerify on success
  • No API calls — simulate only

VERIFICATION (run in this order):
  1. pnpm run build → zero errors
  2. grep -r "from 'primeng" features/auth/ → ZERO matches
  3. pnpm run test → 17+ pass, zero regressions

═══════════════════════════════════════════════════════════════════════
END DISPATCH
═══════════════════════════════════════════════════════════════════════
```
