# WAVE 5 — F13 PROFILE — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature Pages, Parallel Group A |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder sub-session |
| **Agent** | `meesell-angular-component-builder` (sonnet) |
| **Depends-on** | Wave 3 (UI Kit) + Wave 4 (Composites) + `AuthService.currentUser` signal available |

---

## 1. Module Summary

| Field | Value |
|---|---|
| **Route** | `/profile` |
| **Component class** | `ProfileComponent` |
| **Selector** | `app-profile` |
| **Location** | `src/app/features/profile/profile.component.ts` |
| **Purpose** | Account settings page for authenticated seller. Displays seller name + phone (read from `AuthService.currentUser`). Allows editable name (display name). Shows plan tier badge. Log out button. |
| **Status** | Stub exists at `features/profile/profile.component.ts`. Replace with full component. |

**Auth:** Shell child — rendered inside `MeeShellComponent`. Requires `authGuard` (already registered in `app.routes.ts` for the shell group).

---

## 2. Dependencies

**UI Kit primitives consumed (from `../../ui`):**
- `MeeInputComponent` (`mee-input`) — editable display name field
- `MeeButtonComponent` (`mee-button`) — Save button + Log out button
- `MeeCardComponent` (`mee-card`) — wraps the profile form section

**Composites consumed (`../../shared`):**
- `MeeStatusBadgeComponent` (`mee-status-badge`) — shows plan tier (map 'free'→'neutral', 'pro'→'success')

**Layout:** Shell child — `MeeShellComponent` provides the sidebar + topbar frame via `<router-outlet />`. `ProfileComponent` renders its own content inside the outlet. No additional layout wrapper needed.

**API endpoints:**
- `PATCH /api/v1/seller-profile` — save updated display name (API on hold — SIMULATE for Wave 5)
- Auth data (name, phone, plan) read from `AuthService.currentUser` signal — no extra GET needed.

**Services consumed:**
- `AuthService` (core, `inject(AuthService)`) — `currentUser` signal provides `{ name, phone, plan }`. `logout()` for the Log out button.
- `Router` — navigate to `/login` after logout.

> BOUNDARY: import ONLY from `../../ui`, `../../shared`, `@angular/core`, `@angular/router`,
> `@angular/forms` (ReactiveFormsModule + FormBuilder). ZERO `primeng/...` imports.
> ZERO `@angular/material/...` imports.

---

## 3. Files to Create / Modify

| Path | Action |
|---|---|
| `src/app/features/profile/profile.component.ts` | MODIFY (replace stub with full component) |
| `src/app/features/profile/profile.component.spec.ts` | CREATE |

The stub renders a placeholder. Replace entirely — keep the file path.

---

## 4. Component Spec

### Layout sketch (360px mobile-first, shell child)
```
┌──────────────────────────────────────┐  ← Shell sidebar + topbar provided by MeeShellComponent
│  Profile                             │  ← mee-page-header style (inline, no composite needed)
│  Manage your account                 │
├──────────────────────────────────────┤
│  ┌────────────────────────────────┐  │
│  │  [avatar initial]  Mugunthan  │  │  ← avatar: first letter of name, orange circle
│  │  +91 98765 43210  [Free plan]  │  │  ← phone (read-only) + mee-status-badge
│  └────────────────────────────────┘  │
│                                      │
│  Display Name                        │  ← label
│  ┌───────────────────────────────┐   │
│  │ Mugunthan Srinivasan          │   │  ← mee-input (editable)
│  └───────────────────────────────┘   │
│  Phone (read-only)                   │
│  ┌───────────────────────────────┐   │
│  │ +91 98765 43210               │   │  ← mee-input [disabled]="true"
│  └───────────────────────────────┘   │
│                                      │
│  [ Save changes ]   (primary)        │  ← mee-button, [loading]="saving()"
│                                      │
│  ──────────────────────────────────  │
│  [ Log out ]        (danger)         │  ← mee-button variant="danger"
└──────────────────────────────────────┘
```

At 768px+: content width capped at 560px, centered in the shell main area.

### Reactive Form
```typescript
form = this.fb.group({
  name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(60)]],
});
```
Phone is displayed but NOT in the form (read-only display, never patched). Plan displayed via badge.

**Form population on init:** `this.form.patchValue({ name: this.auth.currentUser()?.name ?? '' })` in `ngOnInit()`.

### Signals / state
```
saving  = signal(false)           // true while simulated save in progress
saved   = signal(false)           // true for 3s after successful save (shows "Saved!" feedback)
errorMessage = signal<string | null>(null)
```

`displayPhone = computed<string>(() => {
  const p = this.auth.currentUser()?.phone ?? '';
  return p.startsWith('+91') ? p.slice(3) : p;
})`

`planSeverity = computed<MeeBadgeSeverity>(() =>
  this.auth.currentUser()?.plan === 'pro' ? 'success' : 'neutral')`

`avatarInitial = computed<string>(() => {
  const name = this.auth.currentUser()?.name ?? '';
  return name.charAt(0).toUpperCase() || 'S';
})`

### Key behaviors
- **Save (simulated):** `onSubmit()` → if form invalid return → `saving.set(true)` → `await new Promise(r => setTimeout(r, 800))` → `saving.set(false)` → `saved.set(true)` → `setTimeout(() => saved.set(false), 3000)`.
- **Log out:** calls `this.auth.logout()` → navigate to `/login`.
- **Error surface:** `errorMessage` shown via inline text below the Save button (no toast for V1 wave). Use `mee-button [loading]="saving()"` to disable button during save.
- **Phone is read-only:** render as a `mee-input [disabled]="true"` with the phone value pre-set. Not part of the form group.

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key @Inputs | @Outputs |
|---|---|---|---|
| Profile card wrapper | `mee-card` | content projection | — |
| Plan tier label | `mee-status-badge` | `[status]="auth.currentUser()?.plan"` (requires mapping — see note) | — |
| Display name input | `mee-input` | `[label]="'Display Name'"` `formControlName="name"` `[error]="nameError()"` | — |
| Phone display | `mee-input` | `[label]="'Phone'"` `[disabled]="true"` `[value]="displayPhone()"` | — |
| Save button | `mee-button` | `[label]="saved() ? 'Saved!' : 'Save changes'"` `variant="primary"` `[loading]="saving()"` `[disabled]="form.invalid || saving()"` | `(clicked)="onSubmit()"` |
| Log out button | `mee-button` | `label="Log out"` `variant="danger"` | `(clicked)="onLogout()"` |

**Note on mee-status-badge:** The badge `status` input expects `ProductStatus` union. Plan tier ('free', 'pro') is not part of that union. Options:
1. Use `mee-badge` (Layer 2 primitive) directly with `[severity]="planSeverity()"` `[value]="planLabel()"` — avoids the type mismatch.
2. OR extend `ProductStatus` type to include 'free' | 'pro' (requires modifying the shared type — cross-cutting scope).

**Preferred approach for Wave 5:** Use `mee-badge` directly with `[severity]="planSeverity()"` (computed as 'success' for 'pro', 'neutral' for 'free') and `[value]` set to the plan label. This avoids type system drift. Document as a TODO for the shared type extension if plan badges appear in more places.

All mee-* contracts from `FRONTEND_ARCHITECTURE.md` §Layer 2 Component Contracts.

---

## 6. API / Data

**SIMULATE (API on hold):** Wave 5 simulates the PATCH save with a `setTimeout(800)`. No `HttpClient` call. No service injection beyond `AuthService`.

When Wave 6 API wiring lands, the component will inject a `ProfileApiService` (provided at route level, NOT `providedIn: 'root'`) and replace the simulation with a real `PATCH /api/v1/seller-profile` call. The existing `ProfileApiService` scaffold at `features/profile/` (built in a prior dispatch) may already exist — check before creating a new one.

**Data source for display:** `AuthService.currentUser` signal — already populated from the OTP verify flow (`setSession()`). If `currentUser` returns null (token expired), the auth guard redirects to `/login` before this component renders.

---

## 7. Constraints

- `standalone: true, changeDetection: ChangeDetectionStrategy.OnPush`.
- `inject()` for DI — no constructor parameter injection.
- Reactive Form via `inject(FormBuilder)`.
- `signal()` for `saving`, `saved`, `errorMessage`. `computed()` for `displayPhone`, `planSeverity`, `avatarInitial`.
- `takeUntilDestroyed()` if any Observable subscription is added; use `inject(DestroyRef)` explicitly when not in constructor.
- **SIMULATE save** — no `HttpClient` in Wave 5. `setTimeout(800)` is the stand-in.
- **No hex literals** — `var(--mee-color-*)` tokens only.
- **44px touch targets** on Save and Log out buttons (mee-button handles this internally).
- **Shell child** — do NOT add `<mee-shell>` or `<mee-auth-layout>` wrappers; the shell provides the frame.
- **ZERO `primeng/...` imports**.
- **ZERO `@angular/material/...` imports**.
- Form error inline below field via `mee-input [error]` prop — no separate error div.

---

## 8. Out of Scope

| Item | When |
|---|---|
| Real PATCH API call | Wave 6 (API wiring) |
| Email field or password reset | V1.5 |
| Avatar image upload | V1.5 |
| Plan upgrade flow / Razorpay | V1.5 |
| i18n / Tamil copy | V1.5 |
| Super-category compliance fields (onboarding extension) | V1.5 |
| Delete account | V1.5 |

---

## 9. Verification Gates

1. **BUILD** — `cd frontend && pnpm run build` — zero errors, zero new warnings.
2. **ROUTE RESOLVES** — `pnpm start` → visit `http://localhost:4200/profile` (with a valid mock session) → ProfileComponent renders inside shell (no 404, no redirect loop).
3. **FORM VALIDATION** — Save button disabled when name is empty or < 2 chars; enabled when valid.
4. **TESTS** — `pnpm run test` — minimum 3 tests, all passing:
   - (1) Component creates without errors, form initialises.
   - (2) Save button disabled when name field is empty.
   - (3) Log out calls `auth.logout()`.
5. **FOUNDER VISUAL** — Founder reviews at 360px and 1280px inside the shell: avatar initial, phone read-only, plan badge, Save + Log out buttons visible.

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — F13 PROFILE (route: /profile)
Agent: meesell-angular-component-builder (sonnet)
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Waves 3 (UI Kit) + 4 (Composites) must be confirmed complete.
Route /profile is a shell child — auth-guarded, rendered inside MeeShellComponent.
This dispatch replaces the profile stub with the full account settings page.

BOUNDARY (NON-NEGOTIABLE)
───────────────────────────
  • Import ONLY from ../../ui, ../../shared, @angular/core,
    @angular/router, @angular/forms
  • ZERO primeng/... imports
  • ZERO @angular/material/... imports

══════════════════════════════════════════════════════════════════

FILES TO MODIFY / CREATE
────────────────────────
  MODIFY: src/app/features/profile/profile.component.ts (replace stub)
  CREATE: src/app/features/profile/profile.component.spec.ts

══════════════════════════════════════════════════════════════════

REACTIVE FORM
─────────────
  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(60)]],
  });
  ngOnInit(): patchValue({ name: auth.currentUser()?.name ?? '' })
  Phone: display only (mee-input [disabled]="true") — NOT in form group

SIGNALS / STATE
───────────────
  saving = signal(false)
  saved  = signal(false)   — true for 3s after save, shows "Saved!" label
  errorMessage = signal<string | null>(null)
  displayPhone = computed(() => strip +91 prefix from currentUser().phone)
  planSeverity = computed(() => plan === 'pro' ? 'success' : 'neutral')
  avatarInitial = computed(() => name.charAt(0).toUpperCase() || 'S')

DATA SOURCE
───────────
  AuthService.currentUser signal — no extra GET needed
  SIMULATE save: setTimeout(800) — no HttpClient in Wave 5
  Log out: auth.logout() → router.navigate(['/login'])

LAYOUT SKETCH (360px)
─────────────────────
  [Shell topbar + sidebar provided by MeeShellComponent]
  Page content:
    Heading: "Profile" + subtitle "Manage your account"
    mee-card:
      Avatar initial circle + name + phone + mee-badge (plan)
    Display Name: mee-input [formControlName]="name" + error
    Phone: mee-input [disabled]="true" [value]="displayPhone()"
    mee-button primary "Save changes" [loading]="saving()"
    divider
    mee-button danger "Log out"

UI KIT USAGE
────────────
  mee-card      → profile section wrapper
  mee-badge     → plan tier (severity from planSeverity computed)
  mee-input     → name (editable) + phone (disabled)
  mee-button    → Save (primary, loading) + Log out (danger)
  NOTE: use mee-badge (Layer 2) not mee-status-badge (Layer 3)
        for plan tier — avoids ProductStatus type mismatch

CONSTRAINTS
───────────
  • standalone + OnPush
  • inject(FormBuilder) + inject(AuthService) + inject(Router)
  • signal() for saving/saved/errorMessage; computed() for derived values
  • No hex literals — var(--mee-color-*) tokens only
  • 44px touch targets (mee-button handles internally)
  • Shell child — NO shell/auth-layout wrapper in this component
  • ZERO primeng/... + ZERO @angular/material/... imports

OUT OF SCOPE
  ✗ Real PATCH API (Wave 6)
  ✗ Email / password reset (V1.5)
  ✗ Avatar upload (V1.5)
  ✗ Plan upgrade / Razorpay (V1.5)
  ✗ i18n (V1.5)

TESTS (min 3)
─────────────
  1. Component creates + form initialises
  2. Save disabled when name empty
  3. Log out calls auth.logout()

VERIFICATION GATES
──────────────────
Gate 1 BUILD:        pnpm run build → zero errors
Gate 2 ROUTE:        /profile renders inside shell (no 404)
Gate 3 FORM:         save disabled on invalid name; enabled on valid
Gate 4 TESTS:        pnpm run test → min 3 new tests, all pass
Gate 5 VISUAL:       founder reviews 360px + 1280px inside shell

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-09 | meesell-frontend-coordinator (master) | Initial authoring — Wave 5 Profile (F13); Option A-full; mee-badge (not mee-status-badge) for plan tier to avoid type mismatch |
