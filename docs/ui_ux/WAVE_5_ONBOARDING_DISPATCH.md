# WAVE 5 — ONBOARDING (F5) — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Onboarding (F5) |
| **Date authored** | 2026-06-09 |
| **Status** | READY |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder |
| **Depends on** | Wave 3 UI Kit complete (mee-input, mee-button, mee-steps in `ui/index.ts`) + Wave 4 composites complete |
| **Nature** | NEW page component — no existing code to preserve |

---

## 1. Module Summary

| Property | Value |
|---|---|
| Route | `/onboarding` |
| Component class | `OnboardingComponent` |
| Selector | `mee-onboarding` |
| File path | `features/account/onboarding/onboarding.component.ts` + `.spec.ts` |
| Purpose | Collect seller business basics after first successful OTP verification |
| Status | NOT BUILT — F5 in module inventory |
| Guard | `authGuard` (route must require a valid session) |
| Entry point | Navigated to from `OtpVerifyComponent` on first-login (when `profile_complete: false`) |
| Exit point | On submit → SIMULATE → navigate to `/dashboard` |

`AuthLayoutComponent` (`mee-auth-layout`) is reused here — onboarding is part of the auth funnel and shares the same centered-card layout.

---

## 2. Dependencies

**UI Kit primitives (from `../../ui` or `@mee/ui`):**

| Kit component | Selector | Use |
|---|---|---|
| `MeeInputComponent` | `mee-input` | Business name field, city field, GST field |
| `MeeButtonComponent` | `mee-button` | "Save & Continue" submit CTA |
| `MeeStepsComponent` | `mee-steps` | Optional progress indicator (see §4 — recommended for MVP) |

**Composites:** none required.

**Layout:** `AuthLayoutComponent` from `../../layouts/auth-layout/auth-layout.component` — centered card wrapper, `<ng-content />` pattern (same as auth pages).

**Services:** `Router` from `@angular/router` only. No `AuthService` interaction — session is already set before onboarding is reached.

**API endpoints:** SIMULATE — `PATCH /api/v1/seller-profile` is the eventual target (V1_FEATURE_SPEC §5 — seller profile upsert), but this wave does not wire it. Simulate with `setTimeout(1500)` + navigate to `/dashboard`.

⚠️ BOUNDARY: import ONLY from `../../ui`, `../../layouts`, `../../shared`, own services. ZERO `primeng/...` imports. ZERO `@angular/material/...` imports.

---

## 3. Files to Create / Modify

### New files

| File | Description |
|---|---|
| `features/account/onboarding/onboarding.component.ts` | Page component (template inline or extracted) |
| `features/account/onboarding/onboarding.component.spec.ts` | Vitest spec (sibling) |

### Modified files

| File | Change |
|---|---|
| `app.routes.ts` | Add `/onboarding` route inside the Shell's `canActivate: [authGuard]` children array |

### Route addition (paste into `app.routes.ts` children of the shell group)

```typescript
{
  path: 'onboarding',
  loadComponent: () =>
    import('./features/account/onboarding/onboarding.component')
      .then(m => m.OnboardingComponent),
},
```

> The route sits inside the auth-guarded shell group so `authGuard` is inherited. The component itself wraps in `<mee-auth-layout>` for the auth-funnel card look, not the full sidebar shell. This is intentional — onboarding is a transitional screen before the full app UI.

---

## 4. Component Spec

### Design decision: single form (recommended for MVP)

V1_FEATURE_SPEC describes onboarding as "collect seller basics post-OTP" — it lists no explicit step count or multi-step requirement. A single-page form collects all three fields in one submit. `mee-steps` is included as an OPTIONAL progress indicator (e.g. `steps: [{label:'Account'}, {label:'Business'}, {label:'Done'}]` with `active_index=1`) to give sellers context in the auth funnel without requiring multi-step logic.

**Recommendation:** single form + decorative `mee-steps` (no navigation between steps). If the founder later wants a true multi-step wizard, dispatch a follow-up with the step split defined.

### Form fields

| Field | Control | Validation | UI |
|---|---|---|---|
| `businessName` | required, minLength 2, maxLength 100 | Required | `mee-input [label]="'Business / Shop Name'" [required]="true"` |
| `city` | required, default `'Tirupur'`, maxLength 60 | Required | `mee-input [label]="'City'" [required]="true"` — pre-filled with 'Tirupur' |
| `gstNumber` | optional, pattern `/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/` when present | Optional | `mee-input [label]="'GST Number (optional)'"` |

### Signals / state

| Signal | Type | Purpose |
|---|---|---|
| `loading` | `signal<boolean>(false)` | Disable button + show spinner during simulate |
| `submitted` | `signal<boolean>(false)` | Guard double-submit |

No error state signal needed — `mee-input [error]` accepts a `computed()` string per field.

### Layout sketch (360px, inside mee-auth-layout card)

```
┌──────────────────────────────────────┐
│  MeeSell              (from layout)  │
│                                      │
│  [Step indicator — mee-steps]        │  ← decorative, active_index=1
│  Account · Business · Done           │
│                                      │
│  Set up your business                │  ← h1, 22px bold
│  Tell us about your shop             │  ← p, muted
│                                      │
│  Business / Shop Name   [label]      │
│  ┌────────────────────────────────┐  │
│  │  My Textile Shop               │  │  ← mee-input required
│  └────────────────────────────────┘  │
│                                      │
│  City                   [label]      │
│  ┌────────────────────────────────┐  │
│  │  Tirupur               [pre]   │  │  ← mee-input, default "Tirupur"
│  └────────────────────────────────┘  │
│                                      │
│  GST Number (optional)  [label]      │
│  ┌────────────────────────────────┐  │
│  │  29ABCDE1234F1Z5               │  │  ← mee-input, optional
│  └────────────────────────────────┘  │
│                                      │
│  [ mee-button "Save & Continue" ]    │  ← full width, primary
│                                      │
│  You can update this later.          │  ← p, muted, text-sm
└──────────────────────────────────────┘
```

### Behaviors

- On mount: `city` control pre-filled with `'Tirupur'` via `FormBuilder` initial value.
- On submit (valid form): `loading.set(true)` → `setTimeout(1500)` → `loading.set(false)` → `router.navigate(['/dashboard'])`.
- Submit button disabled when `form.invalid || loading()`.
- GST field: pattern validator applied only when value is non-empty (use custom `optionalGstValidator` — analogous to `optionalPincodeValidator` pattern documented in agent memory).
- `mee-steps` `[active_index]="1"` is static — no navigation between steps.

---

## 5. UI Kit Usage Map

| Element | mee-* component | Key @Input | Key @Output |
|---|---|---|---|
| Steps indicator | `mee-steps` | `[steps]="steps"`, `[active_index]="1"` | none (decorative) |
| Business name field | `mee-input` | `[label]`, `[required]="true"`, `[error]="businessNameError()"`, `formControlName="businessName"` | CVA two-way |
| City field | `mee-input` | `[label]`, `[required]="true"`, `[error]="cityError()"`, `formControlName="city"` | CVA two-way |
| GST field | `mee-input` | `[label]`, `[error]="gstError()"`, `formControlName="gstNumber"` | CVA two-way |
| Submit CTA | `mee-button` | `[label]="'Save & Continue'"`, `[loading]="loading()"`, `[disabled]="form.invalid || loading()"`, `[fullWidth]="true"`, `[variant]="'primary'"` | `(clicked)` → `onSubmit()` |

`mee-steps` contract: `steps: MeeStep[]` where `MeeStep = { label: string; route?: string }`. For decorative use, `route` is omitted.

---

## 6. API / Data

No API call in this wave. Simulate only.

```
onSubmit():
  if (form.invalid || loading()) return;
  loading.set(true);
  setTimeout(() => {
    loading.set(false);
    router.navigate(['/dashboard']);
  }, 1500);
```

Eventual real endpoint (Wave 6 API integration):
- `PATCH /api/v1/seller-profile` — body: `{ business_name, city, gst_number? }`
- Response 200 → navigate `/dashboard`. Response 4xx → `MatSnackBar.open(errorMsg)`.

Wave 6 will replace the `setTimeout` block with an `AuthApiService.updateOnboarding()` call. No other changes needed in this component.

---

## 7. Constraints

| Constraint | Rule |
|---|---|
| Zero PrimeNG imports | `grep "from 'primeng" features/account/onboarding/` → ZERO |
| Standalone + OnPush | `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush` |
| Reactive Forms | `inject(FormBuilder)` — no template-driven forms |
| Signals for local state | `loading`, `submitted`, error computeds — all `signal()` or `computed()` |
| 44px touch targets | `mee-button [fullWidth]="true"` + `mee-input` ensure ≥44px height |
| Auth-layout wrapper | `<mee-auth-layout>` ng-content pattern — not a shell child layout |
| AuthGuard on route | Route added inside shell `canActivate: [authGuard]` children |
| No API calls | SIMULATE with setTimeout(1500) |
| No hardcoded hex | CSS custom properties only: `var(--mee-color-*)` |
| Mobile-first 360px | AuthLayoutComponent card handles max-width; no fixed widths inside |
| Optional GST validator | Custom validator that skips pattern check when value is empty |
| File size | Component must stay under 400 lines |

---

## 8. Out of Scope

| Item | Owner / Wave |
|---|---|
| Real PATCH /seller-profile API wiring | Wave 6 (API integration) |
| Multi-step wizard navigation (step 1 → step 2) | V1.5 if ever needed |
| Super-category selection (business type) | V1_FEATURE_SPEC underspecifies — defer to V1.5 or founder decision (see Ambiguity flag below) |
| Business logo upload | V1.5 |
| Address / pincode collection | V1.5 |
| Skip onboarding option | Out of scope (V1 requires completion) |
| i18n Tamil/Hindi | V1.5 |
| Onboarding completion flag in AuthService | Service-builder scope (Wave 6) |

---

## 9. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| 1 BUILD | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| 2 ROUTES | Dev server: `/onboarding` resolves after login | Component renders in auth-layout card; no blank screen; no 404 |
| 3 VALIDATION | Manual: submit empty form → error shown on required fields; GST invalid format → error; valid form → button enables | All inline error texts visible; submit button enables only when required fields valid |
| 4 TESTS | `cd frontend && pnpm run test` | All pre-existing tests pass + 4 new onboarding tests pass |
| 5 VISUAL | Founder review at 360px | mee-steps visible, city pre-filled "Tirupur", orange primary CTA, Plus Jakarta Sans font |

### Minimum 4 new tests (spec)

1. Component renders inside `<mee-auth-layout>`.
2. Submit button is disabled when `businessName` is empty.
3. `city` control default value is `'Tirupur'`.
4. GST field is optional — form is valid when GST is empty and required fields are filled.

---

## 10. Paste-Ready Dispatch Block

```
═══════════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — ONBOARDING (F5)
Agent: meesell-angular-component-builder (sonnet)
═══════════════════════════════════════════════════════════════════════

CONTEXT
───────
Wave 3 (UI Kit) + Wave 4 (Composites) must be complete before executing this.
This is a NEW page component — no existing code to preserve.
Onboarding appears after first OTP verify (profile_complete: false).
Route: /onboarding — inside shell authGuard children.
Component wraps in <mee-auth-layout> (same card as auth pages).
API integration ON HOLD — simulate with setTimeout(1500).

═══════════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  features/account/onboarding/onboarding.component.ts   NEW
  features/account/onboarding/onboarding.component.spec.ts  NEW

FILES TO MODIFY
───────────────
  app.routes.ts — add /onboarding inside shell authGuard children:
    {
      path: 'onboarding',
      loadComponent: () =>
        import('./features/account/onboarding/onboarding.component')
          .then(m => m.OnboardingComponent),
    }

═══════════════════════════════════════════════════════════════════════

COMPONENT SPEC
──────────────
Selector: mee-onboarding
Layout:   <mee-auth-layout> wrapping (ng-content pattern — same as login/signup)
Form (single page — no multi-step navigation):

  businessName  required, minLength 2, maxLength 100
  city          required, maxLength 60, default 'Tirupur'
  gstNumber     optional, pattern /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/

Signals:
  loading   = signal<boolean>(false)
  submitted = signal<boolean>(false)

Computed error helpers (one per field, return string | undefined):
  businessNameError = computed(() => ...)
  cityError         = computed(() => ...)
  gstError          = computed(() => ...)

On submit: loading.set(true) → setTimeout(1500) → loading.set(false) → router.navigate(['/dashboard'])
Submit disabled when: form.invalid || loading()

═══════════════════════════════════════════════════════════════════════

UI KIT USAGE
────────────
  mee-steps  [steps]="steps" [active_index]="1"   (decorative — no nav)
  mee-input  businessName, city (default 'Tirupur'), gstNumber
  mee-button [label]="'Save & Continue'" [loading]="loading()" [disabled]="..." [fullWidth]="true" (clicked)="onSubmit()"

BOUNDARY: ZERO primeng/... imports. ZERO @angular/material/... imports.
Imports from: ../../ui, ../../layouts, ../../shared, @angular/core, @angular/forms, @angular/router

═══════════════════════════════════════════════════════════════════════

KEY CONSTRAINTS
───────────────
  • Standalone + OnPush
  • ReactiveFormsModule + FormBuilder (inject())
  • Signals for local state
  • 44px touch targets (mee-button + mee-input)
  • mee-auth-layout wrapper (not shell layout)
  • authGuard on route (inherited from shell children)
  • No API calls — simulate only
  • optionalGstValidator skips pattern when value is empty
  • No hardcoded hex — var(--mee-color-*) only
  • Component < 400 lines

TESTS (minimum 4):
  1. <mee-auth-layout> present in output
  2. Submit disabled when businessName empty
  3. city default value is 'Tirupur'
  4. Form valid when GST empty + required fields filled

VERIFICATION:
  1. pnpm run build → zero errors
  2. /onboarding route resolves, mee-auth-layout card renders
  3. Required field validation visible on touch+invalid
  4. pnpm run test → all pass including 4 new tests

═══════════════════════════════════════════════════════════════════════
END DISPATCH
═══════════════════════════════════════════════════════════════════════
```

---

## Ambiguity Flag

**V1_FEATURE_SPEC underspecifies onboarding fields.** The spec (§Feature 1 / §3 journey step 3) names no explicit onboarding fields — it states only "onboarding" as the post-OTP destination. The three fields above (`businessName`, `city`, `gstNumber`) are the minimal seller-identity fields visible across the rest of the V1 spec (catalog ownership, export XLSX header) and matching the `seller_profile` table implied by Auth Dispatch 3's `/seller-profile` check.

The following are deliberately excluded from V1 scope pending founder decision:
- Super-category / business type (e.g. "Garments", "Accessories") — the smart-picker handles this contextually per product, not at onboarding
- Registered business address / pincode
- Business logo
- Bank account details (payment/payout — out of V1 scope entirely)

If the founder wants additional fields at onboarding, a follow-up dispatch with explicit field list is required before Wave 6 API wiring.
