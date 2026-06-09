# WAVE 2C — AUTH PAGES — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 2C — Auth Pages (Login / Signup / OTP Verify) |
| **Date authored** | 2026-06-09 |
| **Status** | 📤 READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | mesell-design-system-2 |
| **Predecessor** | `WAVE_2B_SCAFFOLD_DISPATCH.md` — Gates 1–4 ✅ |
| **Agent** | `meesell-angular-component-builder` (sonnet) |
| **Scope** | 3 auth page components + otp-verify route + tests |

---

## 1. Routing State (current — do not change)

The founder modified routing after Wave 2B. The **current pattern** is:

```
app.routes.ts:
  '' → redirectTo: 'login'
  'login'      → LoginComponent     (top-level)
  'signup'     → SignupComponent    (top-level)
  ''           → ShellComponent (canActivate: authGuard)
                   children: dashboard / catalogs / catalogs/new / profile
  '**'         → redirectTo: 'login'
```

`AuthLayoutComponent` uses **`<ng-content />`** (not `<router-outlet />`).

**Pattern**: each auth page component wraps its own content in `<mee-auth-layout>`:
```html
<!-- login.component.html -->
<mee-auth-layout>
  <!-- form content -->
</mee-auth-layout>
```

Do NOT revert to the parent-route pattern. Do NOT add `<router-outlet />` back to `AuthLayoutComponent`.

---

## 2. Wave 2C Scope

### 2.1 New files to create

| File | Component | Route |
|---|---|---|
| `features/auth/login/login.component.ts` | `LoginComponent` | `/login` |
| `features/auth/signup/signup.component.ts` | `SignupComponent` | `/signup` |
| `features/auth/otp-verify/otp-verify.component.ts` | `OtpVerifyComponent` | `/otp-verify` |
| `features/auth/login/login.component.spec.ts` | Tests | — |
| `features/auth/signup/signup.component.spec.ts` | Tests | — |
| `features/auth/otp-verify/otp-verify.component.spec.ts` | Tests | — |

### 2.2 Files to modify

| File | Change |
|---|---|
| `app.routes.ts` | Add `/otp-verify` route (login + signup already present) |
| `features/auth/login.component.ts` | Replace current stub with full component (keep same path OR refactor to `features/auth/login/login.component.ts`) |
| `features/auth/signup.component.ts` | Same |

> **Note on file structure**: The current stubs are flat (`features/auth/login.component.ts`). You MAY keep them flat or refactor to subdirectories (`features/auth/login/login.component.ts`). Either is acceptable — just be consistent across all 3 auth pages and update `app.routes.ts` imports accordingly.

---

## 3. Auth Flow (no API — simulate only)

API integration is ON HOLD. Each page simulates the async call with a 1.5s delay then navigates. The simulation pattern:

```typescript
protected async onSubmit(): Promise<void> {
  if (this.form.invalid) return;
  this.loading.set(true);
  // Simulate backend call
  await new Promise(r => setTimeout(r, 1500));
  this.loading.set(false);
  this.router.navigate(['/otp-verify']);
}
```

### Flow

```
/login  → phone submit → (simulate) → /otp-verify
/signup → name+phone submit → (simulate) → /otp-verify
/otp-verify → 6-digit OTP submit → (simulate) → AuthService.setSession() → /dashboard
```

---

## 4. Component Specifications

### 4.1 LoginComponent (`/login`)

**Layout** (inside `<mee-auth-layout>`):
```
┌─────────────────────────────────┐
│  MeeSell (from auth-layout)     │
│                                 │
│  Welcome back                   │  ← h1, 22px, font-weight 700
│  Enter your mobile number       │  ← p, muted text
│                                 │
│  Mobile Number                  │  ← label above input
│  ┌───────────────────────────┐  │
│  │ +91  │  98765 43210       │  │  ← p-inputtext with +91 prefix
│  └───────────────────────────┘  │
│                                 │
│  [ Continue →  ]                │  ← p-button, full width, primary
│                                 │
│  Don't have an account?         │
│  Sign up                        │  ← routerLink /signup
└─────────────────────────────────┘
```

**Form fields:**
- `phone` — required, pattern `^[6-9]\d{9}$` (10-digit Indian mobile, no country code in input)
- `+91` prefix displayed as static text inside/before the input (not part of form value)

**Reactive Form:**
```typescript
form = this.fb.group({
  phone: ['', [Validators.required, Validators.pattern(/^[6-9]\d{9}$/)]],
});
```

**Error messages (inline, below input):**
- `phone` invalid + touched → "Enter a valid 10-digit mobile number"

**Submit button states:**
- Default: "Continue →"
- Loading: p-button `[loading]="loading()"` — spinner replaces icon
- Disabled while loading or form invalid

**PrimeNG components to use:**
- `InputText` (`pInputText` directive on `<input>`) — phone field
- `Button` (`p-button`) — full width CTA
- `Message` (`p-message`) — optional inline error banner (if backend error)

### 4.2 SignupComponent (`/signup`)

**Layout** (inside `<mee-auth-layout>`):
```
┌─────────────────────────────────┐
│  MeeSell (from auth-layout)     │
│                                 │
│  Create your account            │  ← h1
│  Start selling smarter          │  ← p, muted
│                                 │
│  Your Name                      │
│  ┌───────────────────────────┐  │
│  │ Mugunthan                 │  │  ← p-inputtext
│  └───────────────────────────┘  │
│                                 │
│  Mobile Number                  │
│  ┌───────────────────────────┐  │
│  │ +91  │  98765 43210       │  │
│  └───────────────────────────┘  │
│                                 │
│  [ Create Account ]             │  ← p-button, full width, primary
│                                 │
│  Already have an account?       │
│  Log in                         │  ← routerLink /login
└─────────────────────────────────┘
```

**Form fields:**
- `name` — required, minLength 2, maxLength 60
- `phone` — same validation as LoginComponent

**Error messages:**
- `name` invalid + touched → "Enter your full name (min 2 characters)"
- `phone` invalid + touched → "Enter a valid 10-digit mobile number"

**Navigates to**: `/otp-verify` on successful submit simulation.

### 4.3 OtpVerifyComponent (`/otp-verify`)

**Layout** (inside `<mee-auth-layout>`):
```
┌─────────────────────────────────┐
│  MeeSell (from auth-layout)     │
│                                 │
│  Verify your number             │  ← h1
│  We sent a 6-digit code to      │
│  +91 98765 43210                │  ← p, show phone from router state
│  (or placeholder if no state)   │
│                                 │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐  │  ← p-inputotp length=6
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘  │    (auto-advances between boxes)
│                                 │
│  [ Verify OTP ]                 │  ← p-button, full width, primary
│                                 │
│  Resend code in 30s             │  ← countdown timer, signal-based
│  (becomes "Resend OTP" link     │    once timer hits 0)
│                                 │
│  ← Back to login                │  ← routerLink /login
└─────────────────────────────────┘
```

**Form:**
```typescript
form = this.fb.group({
  otp: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(6)]],
});
```

**PrimeNG component:**
- `InputOtp` (`p-inputotp`) — `[length]="6"` — handles auto-advance between digit boxes natively

**Countdown timer (signal-based):**
```typescript
protected countdown = signal(30);
private timerInterval: ReturnType<typeof setInterval> | null = null;

ngOnInit(): void {
  this.timerInterval = setInterval(() => {
    this.countdown.update(v => {
      if (v <= 1) { clearInterval(this.timerInterval!); return 0; }
      return v - 1;
    });
  }, 1000);
}

ngOnDestroy(): void {
  if (this.timerInterval) clearInterval(this.timerInterval);
}

protected resendOtp(): void {
  this.countdown.set(30);
  this.startTimer();
}
```

**On successful OTP submit (simulated):**
```typescript
this.auth.setSession('mock-token', { id: 1, name: 'Seller', phone: '+91xxxxxxxxxx' });
this.router.navigate(['/dashboard']);
```

---

## 5. Shared Visual Rules (all 3 pages)

| Rule | Value |
|---|---|
| Wrapping component | `<mee-auth-layout>` (ng-content pattern) |
| Layout import | `AuthLayoutComponent` in `imports: []` |
| Heading size | `text-[22px] font-bold` Tailwind or `font-size: 22px; font-weight: 700` |
| Subtitle/muted | `text-sm text-[var(--mee-color-on-surface-muted)]` |
| Label style | `block text-sm font-medium mb-1.5 text-[var(--mee-color-on-surface)]` |
| Input width | `w-full` (100% of card width) |
| CTA button | `w-full`, `severity="primary"`, `size="large"` |
| Error text | `text-xs text-[var(--mee-color-error)] mt-1` |
| Switch link | `text-sm text-[var(--mee-color-primary)] font-medium` with `routerLink` |
| Min-height touch target | 44px on all interactive elements |
| Change detection | `ChangeDetectionStrategy.OnPush` |
| Reactive state | Angular signals (`signal()`, `computed()`) |
| Forms | `ReactiveFormsModule` + `FormBuilder` |

---

## 6. PrimeNG Imports (per component)

> **READ FIRST — local API reference now exists.** Before writing any PrimeNG markup,
> read the relevant file in `docs/primeng/` (generated from installed `primeng@21.1.9`
> type defs — ground truth for prop names and import paths):
> - `docs/primeng/inputtext.md` — ⚠️ **DIRECTIVE** (`<input pInputText>`), NOT `<p-inputtext>`
> - `docs/primeng/inputotp.md` — `<p-inputotp [length]="6">`, works with `formControlName`
> - `docs/primeng/button.md`
> - `docs/primeng/message.md` — ⚠️ `text` prop deprecated → use content projection
> - `docs/primeng/INDEX.md` — full component map

```typescript
// Login + Signup
import { InputText } from 'primeng/inputtext';   // directive — apply to <input pInputText>
import { Button } from 'primeng/button';
import { Message } from 'primeng/message';  // optional error banner
import { ReactiveFormsModule } from '@angular/forms';

// OTP Verify
import { InputOtp } from 'primeng/inputotp';
import { Button } from 'primeng/button';
import { ReactiveFormsModule } from '@angular/forms';
```

---

## 7. Route to Add (app.routes.ts)

Add between signup and shell group:
```typescript
{
  path: 'otp-verify',
  loadComponent: () =>
    import('./features/auth/otp-verify/otp-verify.component')
      .then(m => m.OtpVerifyComponent),
},
```

---

## 8. Tests (minimum per component)

### LoginComponent (3 tests)
1. Renders inside `<mee-auth-layout>` (selector `mee-auth-layout` present)
2. Submit button disabled when phone is empty
3. Submit button disabled when phone has fewer than 10 digits (e.g. '12345')

### SignupComponent (3 tests)
1. Renders inside `<mee-auth-layout>`
2. Submit button disabled when name is empty
3. Submit button disabled when phone is invalid

### OtpVerifyComponent (3 tests)
1. Renders inside `<mee-auth-layout>`
2. Countdown starts at 30
3. `logout()` is not called on init (smoke test — no auth side-effects on load)

> Minimum 9 tests total. Keep tests simple — no HTTP mocking, no navigation assertions (those belong in integration tests). Focus on render + form validation state.

---

## 9. Constraints

| Constraint | Rule |
|---|---|
| **`ng-content` pattern** | Each page wraps `<mee-auth-layout>` — NOT a router child of it |
| **No hardcoded hex** | All colours via `var(--mee-color-*)` tokens or `mee-*` Tailwind classes |
| **FE-D5** | `setSession()` called only after successful OTP verify — no token stored elsewhere |
| **Standalone + OnPush** | All 3 components |
| **Signals for local state** | `loading`, `countdown`, `errorMessage` — all `signal<T>()` |
| **ReactiveFormsModule** | FormGroup + FormBuilder — no template-driven forms |
| **Mobile 360px** | Card already handles width via AuthLayoutComponent — don't add fixed widths inside |
| **No API calls** | Simulate with `setTimeout(1500)` — no HttpClient wiring yet |
| **Only `meesell-*` agents** | Per CLAUDE.md rules |
| **Timer cleanup** | `ngOnDestroy` clears interval to prevent memory leaks |

---

## 10. Out of Scope

| Item | When |
|---|---|
| Real MSG91 OTP API call | Wave 2F (API integration) |
| Phone number persistence between pages (router state) | Wave 2F |
| Form error snackbar/toast | Wave 2C+ (keep inline errors only for now) |
| "Resend" actually calling backend | Wave 2F |
| i18n (Tamil/Hindi labels) | V1.5 |
| Onboarding redirect after signup OTP verify | Wave 2D |
| Dashboard page content | Wave 2D |
| JWT interceptor wiring | Wave 2F |

---

## 11. Verification Gates

### Gate 1 — BUILD
```bash
cd frontend && pnpm run build
```
Pass: zero errors, zero new warnings.

### Gate 2 — ROUTES RESOLVE
```bash
cd frontend && pnpm start
```
Visit:
- `http://localhost:4200/login` → LoginComponent renders (no blank/error)
- `http://localhost:4200/signup` → SignupComponent renders
- `http://localhost:4200/otp-verify` → OtpVerifyComponent renders (not 404)

### Gate 3 — FORM VALIDATION
On each page:
- Submit button disabled on empty form ✓
- Error text appears after blur on invalid field ✓
- Submit button enables once form valid ✓

### Gate 4 — FUNCTIONAL
```bash
cd frontend && pnpm run test
```
Pass: all existing 8 tests + 9 new tests = **17+ tests, all pass**.

### Gate 5 — VISUAL (founder)
Founder reviews all 3 auth pages at 360px and 1280px. Confirms:
- Orange primary CTA button (`#F26B23`)
- Plus Jakarta Sans font
- MeeSell branding in auth card header
- OTP 6-box layout

### 11.1 Gate tracking

| Gate | Status | Owner |
|---|---|---|
| 1 BUILD | ⏳ | design-system-2 |
| 2 ROUTES | ⏳ | design-system-2 |
| 3 FORM VALIDATION | ⏳ | design-system-2 |
| 4 FUNCTIONAL | ⏳ | design-system-2 |
| 5 VISUAL | ⏳ | Founder |

---

## 12. Dispatch Notification (paste-ready block)

```
══════════════════════════════════════════════════════════════════
📨 MASTER → DESIGN-SYSTEM NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 2C — AUTH PAGES (Login / Signup / OTP Verify)
Agent: meesell-angular-component-builder (sonnet)
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Wave 2B scaffold passed Gates 1–4. Foundation confirmed:
  Angular 21 + PrimeNG 21 + Tailwind 4 + MeeSell tokens.

Routing was updated by founder after Wave 2B:
  • auth-layout.component.ts now uses <ng-content /> NOT <router-outlet />
  • login/signup are top-level routes (NOT children of auth-layout)
  • KEEP this pattern — do not revert

Wave 2C builds the 3 auth pages. API integration is still ON HOLD.
Simulate backend calls with setTimeout(1500) + navigate.

⚠️ READ BEFORE CODING — local PrimeNG API reference now exists:
  docs/primeng/inputtext.md  → DIRECTIVE: <input pInputText>, NOT <p-inputtext>
  docs/primeng/inputotp.md   → <p-inputotp [length]="6"> + formControlName
  docs/primeng/button.md
  docs/primeng/message.md    → text prop deprecated, use content projection
  docs/primeng/INDEX.md      → full component map
These are generated from installed primeng@21.1.9 type defs = ground truth.

══════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  • features/auth/login/login.component.ts      + spec.ts
  • features/auth/signup/signup.component.ts    + spec.ts
  • features/auth/otp-verify/otp-verify.component.ts + spec.ts

FILES TO MODIFY
───────────────
  • app.routes.ts — add /otp-verify route
  • Replace existing flat stubs (features/auth/login.component.ts
    + features/auth/signup.component.ts) with full components
    (OR refactor to subdirs — be consistent, update imports)

══════════════════════════════════════════════════════════════════

ROUTING PATTERN (ng-content, NOT router-child)
───────────────────────────────────────────────
Each auth page wraps itself:
  <mee-auth-layout>
    <!-- form content here -->
  </mee-auth-layout>

  imports: [AuthLayoutComponent, ...]

Do NOT add router-outlet back to AuthLayoutComponent.
Do NOT make auth pages children of AuthLayoutComponent in routes.

══════════════════════════════════════════════════════════════════

AUTH FLOW (simulated — no API)
───────────────────────────────
  /login      → phone → setTimeout(1500) → navigate /otp-verify
  /signup     → name+phone → setTimeout(1500) → navigate /otp-verify
  /otp-verify → 6-digit OTP → setTimeout(1500) →
                auth.setSession('mock-token', {...}) → /dashboard

══════════════════════════════════════════════════════════════════

COMPONENT SPECS
───────────────

LOGIN (/login)
  Heading: "Welcome back" (22px bold)
  Subtitle: "Enter your mobile number"
  Form fields:
    phone — required, pattern /^[6-9]\d{9}$/ (10-digit Indian mobile)
    +91 prefix as static display text (not in form value)
  Error: "Enter a valid 10-digit mobile number" (inline, below field)
  CTA: "Continue →" — p-button full-width — [loading]="loading()"
  Footer: "Don't have an account? Sign up" → routerLink /signup

SIGNUP (/signup)
  Heading: "Create your account"
  Subtitle: "Start selling smarter"
  Form fields:
    name — required, minLength 2, maxLength 60
    phone — same as login
  Errors: inline below each field
  CTA: "Create Account" — p-button full-width
  Footer: "Already have an account? Log in" → routerLink /login

OTP VERIFY (/otp-verify)
  Heading: "Verify your number"
  Subtitle: "We sent a 6-digit code to +91 xxxxxxxxxx"
  Form: p-inputotp [length]="6" (auto-advances between boxes)
    otp — required, minLength 6, maxLength 6
  CTA: "Verify OTP" — p-button full-width
  Countdown timer:
    countdown = signal(30)
    setInterval dec every 1s; clearInterval on destroy
    Shows "Resend code in Xs" while counting
    Shows "Resend OTP" clickable link when 0
  Footer: "← Back to login" → routerLink /login

══════════════════════════════════════════════════════════════════

VISUAL RULES (all 3 pages)
──────────────────────────
  Heading:       text-[22px] font-bold text-[var(--mee-color-on-surface)]
  Subtitle:      text-sm text-[var(--mee-color-on-surface-muted)] mb-6
  Label:         block text-sm font-medium mb-1.5
  Input:         w-full (p-inputtext or p-inputotp)
  Error text:    text-xs text-[var(--mee-color-error)] mt-1
  CTA button:    w-full, severity unset (uses primary preset), size="large"
  Switch link:   text-sm text-[var(--mee-color-primary)] font-medium
  Touch targets: min-height 44px
  No hardcoded hex — use var(--mee-color-*) or mee-* Tailwind classes

══════════════════════════════════════════════════════════════════

PRIMENG IMPORTS
───────────────
  Login + Signup: InputText, Button, Message, ReactiveFormsModule
  OTP Verify:     InputOtp, Button, ReactiveFormsModule

══════════════════════════════════════════════════════════════════

TESTS (minimum 9 total — 3 per component)
──────────────────────────────────────────
  Login:
    1. <mee-auth-layout> present in rendered output
    2. Submit disabled when phone empty
    3. Submit disabled when phone < 10 digits

  Signup:
    1. <mee-auth-layout> present
    2. Submit disabled when name empty
    3. Submit disabled when phone invalid

  OTP Verify:
    1. <mee-auth-layout> present
    2. countdown initialises at 30
    3. no auth side-effects on init

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • ng-content pattern — keep as is
  • No hardcoded hex
  • FE-D5 — setSession() only after OTP verify success
  • Standalone + OnPush + signals
  • ReactiveFormsModule — no template-driven forms
  • Mobile 360px — no fixed widths inside auth-layout card
  • No API calls — simulate only
  • ngOnDestroy clears OTP timer interval
  • Only meesell-* agents

OUT OF SCOPE:
  ✗ Real MSG91 API wiring
  ✗ Phone state between pages
  ✗ JWT interceptor
  ✗ i18n / Tamil
  ✗ Dashboard content (Wave 2D)

══════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────
Gate 1 BUILD:           pnpm run build → zero errors
Gate 2 ROUTES RESOLVE:  /login, /signup, /otp-verify all render
Gate 3 FORM VALIDATION: submit disabled on invalid; error text shows
Gate 4 FUNCTIONAL:      pnpm run test → 17+ tests all pass
Gate 5 VISUAL:          ⏳ founder reviews all 3 at 360px + 1280px

══════════════════════════════════════════════════════════════════

STATUS UPDATE (append to STATUS_DESIGN_SYSTEM.md)
───────────────────────────────────────────────────
  ═══════════════════════════════════════
  UPDATE 2026-06-09 — WAVE 2C AUTH PAGES
  ═══════════════════════════════════════
  Components built: LoginComponent / SignupComponent / OtpVerifyComponent
  Route added: /otp-verify
  Tests added: [N] | Tests passing: [N/M]
  Gate 1 BUILD:          ✅/❌
  Gate 2 ROUTES:         ✅/❌
  Gate 3 FORM VALID:     ✅/❌
  Gate 4 FUNCTIONAL:     ✅/❌
  Gate 5 VISUAL:         ⏳ pending founder
  Open questions: [blockers for master]

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## 13. What Comes After Wave 2C

| Wave | Content | Trigger |
|---|---|---|
| **2D — Dashboard page** | Stat cards + recent activity + quick-action buttons using PrimeNG widgets | After Wave 2C Gate 5 ✅ |
| **2E — Catalog pages** | Catalog list (p-table) + new catalog form (p-steps wizard) | After 2D ✅ |
| **2F — API integration** | Wire HttpClient + JWT interceptor + real OTP + real auth flow | After all pages visually confirmed |

---

## 14. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-09 | meesell-frontend-coordinator (master) | Initial authoring — accounts for founder routing change (ng-content pattern) |
