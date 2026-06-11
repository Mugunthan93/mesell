# MeeSell Frontend Architecture

**Status:** APPROVED by founder — 2026-06-08
**Wave:** 2B scaffold → 2C UI Kit → 2D Shared → 2E+ Features
**Stack:** Angular 21 · PrimeNG 21 · Sakai-ng layout · Tailwind CSS 4 · TypeScript strict

---

## Core Principle

MeeSell frontend is built with a **component abstraction layer** that decouples business logic
from the underlying UI component library. PrimeNG is an implementation detail — not a
dependency of features, pages, or business logic.

**If PrimeNG is replaced tomorrow, only `src/app/ui/` changes. Zero feature files change.**

---

## SOLID Principles Applied

| Principle | Rule |
|-----------|------|
| **Single Responsibility** | Each layer has one job. `mee-table` wraps display. `catalog-list` owns filtering logic. Never mixed. |
| **Open/Closed** | `mee-button` is open for new `variant` values without modifying existing feature consumers. |
| **Liskov Substitution** | Any `mee-table` implementation (PrimeNG, Material, custom) replaces another without breaking `catalog-list`. |
| **Interface Segregation** | `mee-input` exposes only the 6 props MeeSell needs — not PrimeNG's full API surface. |
| **Dependency Inversion** | Features import from `@mee/ui` abstractions. `@mee/ui` imports from PrimeNG. Dependency arrow: Feature → Abstract ← PrimeNG. |

---

## The 4-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — FEATURES                                         │
│  dashboard · catalog-form · images · preview · export...    │
│  Rule: imports ONLY from @mee/ui, @mee/shared, @mee/layouts │
│  Rule: ZERO direct PrimeNG imports                          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — LAYOUTS + SHARED COMPOSITES                      │
│  MeeShellComponent · MeeAuthLayoutComponent                 │
│  mee-stat-card · mee-status-badge · mee-page-header         │
│  Rule: imports ONLY from @mee/ui primitives                 │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — MEE UI KIT  (the abstraction wall)               │
│  mee-button · mee-input · mee-table · mee-dialog · ...      │
│  Rule: PrimeNG lives HERE and nowhere else                  │
│  Rule: exposes MeeSell-semantic APIs only                   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — DESIGN SYSTEM                                    │
│  CSS custom properties · typography · motion · elevation    │
│  Rule: ZERO imports of any component library                │
│  Rule: pure CSS/SCSS only — survives any library swap       │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Design System

**Location:** `src/app/design-system/`

```
src/app/design-system/
├── _tokens.scss        # CSS custom properties — colors, spacing, radius, shadow
├── _typography.scss    # Font stack — Plus Jakarta Sans (primary), Inter (fallback)
├── _motion.scss        # Transition tokens — --mee-transition-fast, --mee-transition-base
├── _elevation.scss     # Box shadow scale — --mee-shadow-sm, --mee-shadow-md, --mee-shadow-lg
└── index.scss          # Barrel @forward for all design tokens
```

**Token contract (minimum required):**

```scss
// _tokens.scss
:root {
  // Brand
  --mee-color-primary:        #F26B23;   // MeeSell orange
  --mee-color-primary-light:  rgba(242,107,35,0.12);
  --mee-color-on-primary:     #FFFFFF;

  // Surface
  --mee-color-bg:             #f0f5f9;   // Page background
  --mee-color-surface:        #ffffff;   // Card surface
  --mee-color-on-surface:     #2a3547;   // Body text
  --mee-color-on-surface-muted: #5a6a85; // Secondary text

  // Sidebar
  --mee-color-sidebar:        #111c2d;   // Dark navy
  --mee-color-sidebar-text:   #9fafca;   // Sidebar nav text
  --mee-color-sidebar-active: #F26B23;   // Active nav indicator

  // Semantic
  --mee-color-error:          #DC2626;
  --mee-color-success:        #16A34A;
  --mee-color-warning:        #D97706;
  --mee-color-info:           #2563EB;

  // Border
  --mee-color-outline:        #e5eaef;
  --mee-color-outline-variant:#dfe5ef;

  // Radius
  --mee-radius-sm:  7px;
  --mee-radius-md:  16px;
  --mee-radius-lg:  18px;
  --mee-radius-full: 999px;

  // Spacing scale (4px base)
  --mee-space-1:  4px;
  --mee-space-2:  8px;
  --mee-space-3:  12px;
  --mee-space-4:  16px;
  --mee-space-5:  20px;
  --mee-space-6:  24px;
  --mee-space-8:  32px;
  --mee-space-10: 40px;
}
```

**Invariant:** No `@use 'primeng/...'` or any component library SCSS in this layer.

---

## Layer 2 — MeeSell UI Kit

**Location:** `src/app/ui/`
**Barrel export:** `src/app/ui/index.ts` — the only import path features use

```
src/app/ui/
├── button/
│   ├── button.component.ts     # mee-button
│   └── button.types.ts         # MeeButtonVariant, MeeButtonSize
├── input/
│   ├── input.component.ts      # mee-input
│   └── input.types.ts
├── otp-input/
│   └── otp-input.component.ts  # mee-otp-input
├── password-input/
│   └── password-input.component.ts
├── textarea/
│   └── textarea.component.ts   # mee-textarea
├── select/
│   ├── select.component.ts     # mee-select
│   └── select.types.ts         # MeeSelectOption
├── tree-select/
│   └── tree-select.component.ts # mee-tree-select (category picker)
├── table/
│   ├── table.component.ts      # mee-table
│   └── table.types.ts          # MeeColumn, MeeTableEvent
├── card/
│   └── card.component.ts       # mee-card
├── dialog/
│   ├── dialog.component.ts     # mee-dialog
│   └── dialog.types.ts
├── confirm-dialog/
│   └── confirm-dialog.component.ts
├── file-upload/
│   ├── file-upload.component.ts # mee-file-upload
│   └── file-upload.types.ts     # MeeFileUploadEvent
├── steps/
│   ├── steps.component.ts      # mee-steps
│   └── steps.types.ts          # MeeStep
├── progress-bar/
│   └── progress-bar.component.ts
├── badge/
│   ├── badge.component.ts      # mee-badge
│   └── badge.types.ts          # MeeBadgeSeverity
├── toast/
│   ├── toast.component.ts      # mee-toast (host component)
│   └── toast.service.ts        # MeeToastService (injected by features)
├── skeleton/
│   ├── skeleton.component.ts   # mee-skeleton
│   └── skeleton.types.ts       # MeeSkeletonVariant
└── index.ts                    # barrel — exports all components + types
```

### Component Contracts

#### `mee-button`
```typescript
@Input() label: string
@Input() variant: 'primary' | 'secondary' | 'ghost' | 'danger' = 'primary'
@Input() size: 'sm' | 'md' | 'lg' = 'md'
@Input() loading = false
@Input() disabled = false
@Input() fullWidth = false
@Input() icon?: string           // Material Symbol name
@Output() clicked = new EventEmitter<void>()
// Internal: wraps <p-button>
```

#### `mee-input`
```typescript
@Input() label?: string
@Input() placeholder = ''
@Input() type: 'text' | 'email' | 'number' | 'tel' = 'text'
@Input() prefix?: string          // e.g. '+91'
@Input() error?: string
@Input() hint?: string
@Input() disabled = false
@Input() required = false
// Two-way binding via ControlValueAccessor
// Internal: wraps <p-inputText>
```

#### `mee-otp-input`
```typescript
@Input() length = 6
@Input() disabled = false
@Output() completed = new EventEmitter<string>()
// Internal: wraps <p-inputOtp>
```

#### `mee-table`
```typescript
@Input() columns: MeeColumn[]     // { field: string; header: string; sortable?: boolean; width?: string }
@Input() rows: unknown[]
@Input() loading = false
@Input() paginator = false
@Input() rows_per_page = 10
@Input() total_records?: number
@Input() empty_message = 'No data found'
@Output() row_click = new EventEmitter<unknown>()
@Output() page = new EventEmitter<MeeTablePageEvent>()
@Output() sort = new EventEmitter<MeeTableSortEvent>()
// Internal: wraps <p-table>
```

#### `mee-dialog`
```typescript
@Input() header: string
@Input() visible = false
@Input() width = '480px'
@Input() closable = true
@Output() visibleChange = new EventEmitter<boolean>()   // two-way [(visible)]
@Output() closed = new EventEmitter<void>()
// Content via <ng-content>
// Internal: wraps <p-dialog>
```

#### `mee-file-upload`
```typescript
@Input() accept = 'image/*'
@Input() max_size_mb = 5
@Input() multiple = false
@Input() label = 'Drop files here or click to upload'
@Output() files_selected = new EventEmitter<MeeFileUploadEvent>()
@Output() upload_error = new EventEmitter<string>()
// Internal: wraps <p-fileUpload>
```

#### `mee-steps`
```typescript
@Input() steps: MeeStep[]         // { label: string; route?: string }
@Input() active_index = 0
@Output() active_index_change = new EventEmitter<number>()
// Internal: wraps <p-steps>
```

#### `mee-badge`
```typescript
@Input() value: string
@Input() severity: 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral'
// Internal: wraps <p-tag>
```

#### `mee-tree-select`
```typescript
@Input() nodes: MeeTreeNode[]     // { label, value, children? }
@Input() placeholder = 'Select category'
@Input() loading = false
@Output() value_change = new EventEmitter<MeeTreeNode>()
// Internal: wraps <p-treeSelect>
```

#### `mee-select`
```typescript
@Input() options: MeeSelectOption[]  // { label: string; value: unknown }
@Input() placeholder = 'Select'
@Input() disabled = false
@Input() label?: string
@Input() error?: string
@Output() value_change = new EventEmitter<unknown>()
// ControlValueAccessor support
// Internal: wraps <p-select> (PrimeNG 21 renamed from p-dropdown)
```

#### `mee-skeleton`
```typescript
@Input() variant: 'text' | 'card' | 'table-row' | 'stat-card' = 'text'
@Input() lines = 1                 // for variant='text'
// Internal: wraps <p-skeleton>
```

#### `mee-progress-bar`
```typescript
@Input() value: number             // 0–100
@Input() label?: string
@Input() show_value = true
// Internal: wraps <p-progressBar>
```

#### `mee-confirm-dialog`
```typescript
// Service-based — triggered via MeeConfirmService
// MeeConfirmService.confirm({ message, header, accept, reject })
// Internal: wraps <p-confirmDialog> + ConfirmationService
```

#### `mee-toast` (host component + service)
```typescript
// Place <mee-toast /> once in app shell
// Use MeeToastService anywhere:
// this.toast.success('Catalog saved')
// this.toast.error('Upload failed')
// this.toast.warn('Profile incomplete')
// Internal: wraps <p-toast> + MessageService
```

---

## Layer 3 — Layouts

**Location:** `src/app/layouts/`

```
src/app/layouts/
├── shell/
│   ├── shell.component.ts        # MeeShellComponent — sidebar + topbar + router-outlet
│   ├── sidebar/
│   │   └── sidebar.component.ts  # Collapsible dark navy sidebar (#111c2d)
│   └── topbar/
│       └── topbar.component.ts   # Top header with user menu
└── auth-layout/
    └── auth-layout.component.ts  # Centered card layout for login/signup/onboarding
```

**Shell sidebar nav items (V1):**
```
Dashboard          → /dashboard
My Catalogs        → /catalogs
New Catalog        → /catalogs/new
─────────────────
Profile            → /profile
```

**Design spec:**
- Sidebar width: 270px open / 80px collapsed (icon-only)
- Sidebar bg: `var(--mee-color-sidebar)` = #111c2d
- Active indicator: `var(--mee-color-sidebar-active)` = #F26B23
- Font: Plus Jakarta Sans
- Mobile: `p-sidebar` overlay drawer (360px — full width, slide over content)

---

## Layer 3 — Shared Composites

**Location:** `src/app/shared/`

```
src/app/shared/
├── stat-card/
│   └── stat-card.component.ts     # mee-stat-card
├── status-badge/
│   └── status-badge.component.ts  # mee-status-badge
├── page-header/
│   └── page-header.component.ts   # mee-page-header
├── empty-state/
│   └── empty-state.component.ts   # mee-empty-state
└── loading-skeleton/
    └── loading-skeleton.component.ts
```

#### `mee-stat-card`
```typescript
@Input() label: string
@Input() value: string | number
@Input() icon: string              // Material Symbol
@Input() trend?: number            // +12.5 or -3.2
@Input() trend_label?: string      // 'vs last month'
@Input() color: 'orange' | 'blue' | 'green' | 'purple' = 'orange'
// Uses: mee-card internally
```

#### `mee-status-badge`
```typescript
@Input() status: ProductStatus     // draft | ready | exported | live | deleted | processing | pending | failed
// Maps status → MeeBadgeSeverity automatically
// Uses: mee-badge internally
```

#### `mee-page-header`
```typescript
@Input() title: string
@Input() subtitle?: string
@Input() cta_label?: string
@Input() cta_icon?: string
@Output() cta_click = new EventEmitter<void>()
// Uses: mee-button internally
```

---

## Layer 4 — Features

**Location:** `src/app/features/`

```
src/app/features/
├── landing/
├── account/
│   ├── login/
│   ├── signup/
│   └── onboarding/
├── dashboard/
├── smart-picker/           # /catalogs/new — AI category suggestion
├── catalog-form/           # /catalogs/:id/edit
├── images/                 # /catalogs/:id/images
├── preview/                # /catalogs/:id/preview
├── pricing/                # /catalogs/:id/pricing
├── export/                 # /export
└── profile/                # /profile
```

**Enforcement rules (must be linted/reviewed):**
1. No `import { ... } from 'primeng/...'` in any feature file
2. No `import { ... } from '@angular/material/...'` in any feature file
3. Feature components import ONLY from:
   - `../../ui` (or `@mee/ui` path alias)
   - `../../shared`
   - `../../layouts`
   - Their own `./services/`, `./models/`, `./guards/`
   - Angular core (`@angular/core`, `@angular/router`, `@angular/forms`)
   - RxJS
   - The generated API client

---

## Project Structure (full)

```
mesell/frontend/
├── src/
│   ├── app/
│   │   ├── design-system/      # Layer 1
│   │   │   ├── _tokens.scss
│   │   │   ├── _typography.scss
│   │   │   ├── _motion.scss
│   │   │   ├── _elevation.scss
│   │   │   └── index.scss
│   │   ├── ui/                 # Layer 2 — PrimeNG wrappers
│   │   │   ├── button/
│   │   │   ├── input/
│   │   │   ├── otp-input/
│   │   │   ├── password-input/
│   │   │   ├── textarea/
│   │   │   ├── select/
│   │   │   ├── tree-select/
│   │   │   ├── table/
│   │   │   ├── card/
│   │   │   ├── dialog/
│   │   │   ├── confirm-dialog/
│   │   │   ├── file-upload/
│   │   │   ├── steps/
│   │   │   ├── progress-bar/
│   │   │   ├── badge/
│   │   │   ├── toast/
│   │   │   ├── skeleton/
│   │   │   └── index.ts
│   │   ├── layouts/            # Layer 3
│   │   │   ├── shell/
│   │   │   └── auth-layout/
│   │   ├── shared/             # Layer 3 composites
│   │   │   ├── stat-card/
│   │   │   ├── status-badge/
│   │   │   ├── page-header/
│   │   │   ├── empty-state/
│   │   │   └── loading-skeleton/
│   │   ├── features/           # Layer 4
│   │   │   ├── landing/
│   │   │   ├── account/
│   │   │   ├── dashboard/
│   │   │   ├── smart-picker/
│   │   │   ├── catalog-form/
│   │   │   ├── images/
│   │   │   ├── preview/
│   │   │   ├── pricing/
│   │   │   ├── export/
│   │   │   └── profile/
│   │   ├── core/               # Guards, interceptors, services
│   │   │   ├── guards/
│   │   │   │   └── auth.guard.ts
│   │   │   ├── interceptors/
│   │   │   │   ├── auth.interceptor.ts   # Attaches JWT Bearer token
│   │   │   │   └── error.interceptor.ts  # Global error handling
│   │   │   └── services/
│   │   │       └── auth.service.ts
│   │   ├── app.routes.ts
│   │   ├── app.config.ts       # bootstrapApplication config
│   │   └── app.component.ts
│   ├── styles.scss             # @use design-system/index + Tailwind directives
│   ├── index.html
│   └── main.ts                 # bootstrapApplication
├── tailwind.config.js          # extend with design-system tokens
├── angular.json
├── package.json                # Angular 21 + PrimeNG 21 + Tailwind 4
└── tsconfig.json               # strict: true + path aliases
```

---

## Project Structure (as-built — federated workspace)

> **Founder-approved §7.3 amendment — 2026-06-11.** ADDITIVE as-built sync only. This section
> records the federated workspace topology delivered by the Module Federation program (SP00–SP07,
> `docs/plans/module_federation/MASTER_PLAN.md` APPROVED 2026-06-10). **No design decision changes**:
> the 4-layer architecture, the PrimeNG abstraction wall, SOLID rules, and the LOCKED technology
> decisions above are unchanged. The single-app "Project Structure (full)" block above describes the
> Wave-2B design intent; this block describes what the strangler-fig federation migration actually
> built. Both are kept (additive). The path-alias re-mapping (`@mee/*` design intent → `@mesell/*`
> as-built) is captured in the "Path Aliases" section below.

The single Angular app was migrated to a **federated shell + 6 remotes** workspace (Native
Federation on the preserved `@angular/build:application` esbuild builder — NOT Webpack MF). The
shell is the host; each remote owns a co-changing slice of the user journey; the four `libs/`
packages are the shared singletons. The `frontend/` directory is one Angular workspace with N+1
projects (shell + 6 remotes).

```
mesell/frontend/
├── apps/                                # all Angular projects (uniform topology — D43)
│   ├── shell/                           # the HOST application (relocated from src/ at SP07 / D43)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── core/                # HOST concerns ONLY (no feature code)
│   │   │   │   │   ├── load-remote.ts            # loadRemoteWithFallback / loadRemoteRoutesWithFallback
│   │   │   │   │   ├── remote-failure.component.ts  # D12 graceful-degradation fallback
│   │   │   │   │   └── csp-smoke.spec.ts         # dev CSP smoke harness (SP07 / D42)
│   │   │   │   ├── layouts/shell/        # shell chrome (sidebar + topbar + router-outlet)
│   │   │   │   ├── app.config.ts         # bootstrap providers (router, http, providePrimeNG ONCE)
│   │   │   │   ├── app.routes.ts         # top-level routes — lazy-load remotes via loadRemote*
│   │   │   │   ├── app.ts / app.html / app.css
│   │   │   ├── main.ts / bootstrap.ts    # initFederation() → bootstrapApplication
│   │   │   ├── index.html / styles.css   # the SINGLE Tailwind build (@import "tailwindcss" + @source ../../../libs)
│   │   │   └── public/
│   │   │       ├── federation.manifest.json          # DEV — localhost:4201-4206
│   │   │       ├── federation.manifest.staging.json  # version-pinned template (D44)
│   │   │       └── federation.manifest.prod.json      # version-pinned template (D44)
│   │   ├── federation.config.js          # name: 'shell' (dynamic-host)
│   │   └── tsconfig.app.json
│   ├── mfe-auth/                         # R1 — F2 login · F3 signup · F4 otp-verify        (port 4206)
│   ├── mfe-onboarding/                   # R2 — F5 onboarding · F13 profile                 (port 4203)
│   ├── mfe-dashboard/                    # R3 — F1 landing (public) · F6 dashboard          (port 4204)
│   ├── mfe-catalog/                      # R4 — F7 smart-picker · F8 form · F9 images · F10 preview (port 4205)
│   ├── mfe-pricing/                      # R5 — F11 pricing (PILOT)                         (port 4201)
│   └── mfe-export/                       # R6 — F12 export                                  (port 4202)
│       └── (each remote: src/app/<feature>/ · main.ts · federation.config.js · index.html · tsconfig.app.json)
├── libs/                                 # shared workspace packages (the singletons)
│   ├── ui-kit/                           # @mesell/ui-kit — the mee-* PrimeNG wrappers (Layer 2 abstraction wall)
│   ├── composites/                       # @mesell/composites — Layer 3 composites + AuthLayout (promoted SP03/D21)
│   ├── core/                             # @mesell/core — AuthService (+ authGuard); singleton:true in every remote
│   └── design-tokens/                    # @mesell/design-tokens — _tokens.css (Layer 1; pure CSS, not a runtime singleton)
├── angular.json                          # N+1 projects; every remote's styles[0] = apps/shell/src/styles.css (single Tailwind build)
├── docker/                               # nginx.conf.template (CSP ADD-ONLY) + csp-policy.env (SP07 / D42 — infra-owned)
├── package.json                          # start:shell (4200) + start:mfe-<name> (4201-4206)
└── tsconfig.json                         # strict: true + @mesell/* path aliases (incl. deep @mesell/ui-kit/*)
```

### Port registry (dev serve)

| Project | Port | Manifest key |
|---|---|---|
| `shell` (host) | **4200** | — (the host; loads the manifest) |
| `mfe-pricing` (R5) | **4201** | `mfe-pricing` |
| `mfe-export` (R6) | **4202** | `mfe-export` |
| `mfe-onboarding` (R2) | **4203** | `mfe-onboarding` |
| `mfe-dashboard` (R3) | **4204** | `mfe-dashboard` |
| `mfe-catalog` (R4) | **4205** | `mfe-catalog` |
| `mfe-auth` (R1) | **4206** | `mfe-auth` |

Ports are pinned via the `start:*` npm scripts (script flags, NOT `angular.json`) so the dev manifest
stays stable. The dev manifest (`apps/shell/public/federation.manifest.json`) points at
`http://localhost:420{1-6}/remoteEntry.json`.

### Version-pinned manifest (staging / prod — D44)

The shell loads remotes at runtime from a per-environment manifest. Dev = localhost. Staging/prod are
infra-templated from `federation.manifest.{staging,prod}.json`, each remote URL of the form
`https://remotes{-staging}.mesell.xyz/{ENV}/mfe-<name>/{VERSION}/remoteEntry.json`. **`{VERSION}` is an
exact immutable build hash/semver per remote — NEVER the literal `latest`** (R5 / R-SP7-6 contract-drift
mitigation: the shell pins the exact remote build it was tested against; rollback = re-point `{VERSION}`).
`{ENV}`/`{VERSION}` are infra envsubst tokens substituted at deploy time. Staging uses the
`remotes-staging.mesell.xyz` subdomain (off-cluster, C-STAGING-1).

---

## Path Aliases (tsconfig.json)

```json
{
  "compilerOptions": {
    "paths": {
      "@mee/ui":     ["src/app/ui/index.ts"],
      "@mee/shared": ["src/app/shared/index.ts"],
      "@mee/design": ["src/app/design-system/index.scss"],
      "@mee/core":   ["src/app/core/index.ts"]
    }
  }
}
```

> **As-built (founder-approved §7.3 amendment 2026-06-11):** the federation migration moved the
> aliases from the single-app `@mee/*` design intent above to `@mesell/*` workspace packages under
> `libs/`. The barrel contract is preserved — only the path alias moved (`from '../../ui'` →
> `from '@mesell/ui-kit'`). As-built aliases:
>
> ```json
> {
>   "compilerOptions": {
>     "paths": {
>       "@mesell/ui-kit":        ["libs/ui-kit/index.ts"],
>       "@mesell/ui-kit/*":      ["libs/ui-kit/*"],          // deep imports (lean-bundle pattern)
>       "@mesell/composites":    ["libs/composites/index.ts"],
>       "@mesell/composites/*":  ["libs/composites/*"],
>       "@mesell/core":          ["libs/core/index.ts"],      // AuthService singleton
>       "@mesell/design-tokens": ["libs/design-tokens/_tokens.css"]
>     }
>   }
> }
> ```

---

## Technology Decisions (LOCKED)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Component library | PrimeNG 21 | MIT, Angular 21, Tailwind 4, Sakai starter, standalone |
| Layout starter | Sakai-ng Free | MIT, 13 pre-built pages, no paywall, Feb 2026 |
| Utility CSS | Tailwind CSS 4 | Included in Sakai-ng, MeeSell standard |
| Angular version | 21 | Matches PrimeNG 21 / Sakai-ng 21 |
| Icon library | Material Symbols Outlined | CDN via Google Fonts |
| Typography | Plus Jakarta Sans | MeeSell brand font |
| Abstraction pattern | Wrapper components in `ui/` | SOLID DIP — library swap without feature rewrites |
| State management | Angular Signals + RxJS | Angular 21 standard; no NgRx for V1 |
| Auth | MSG91 OTP + JWT (PyJWT) | Backend-driven, phone-first for Indian sellers |
| HTTP client | Angular HttpClient | Standard; interceptors for JWT + error handling |
| Forms | Angular Reactive Forms | Strong typing + validation |

---

## Wave Implementation Sequence

### Wave 2B — Scaffold + Design System
**Deliverables:**
- `ng new mesell-frontend` with Angular 21 + PrimeNG 21 + Sakai-ng layout
- Layer 1 complete: `_tokens.scss`, `_typography.scss`, `_motion.scss`, `_elevation.scss`
- `MeeShellComponent` (dark navy sidebar, topbar, router-outlet)
- `MeeAuthLayoutComponent` (centered card)
- `app.routes.ts` with all V1 routes wired (lazy-loaded, auth guard on shell)
- `auth.interceptor.ts`, `error.interceptor.ts`
- `tailwind.config.js` extended with design tokens
- Build passes, dev server responds HTTP 200

### Wave 2C — UI Kit Primitives
**Deliverables:** All 17 components in `src/app/ui/`
**Priority order:** button → input → otp-input → badge → card → table → dialog → file-upload → steps → select → tree-select → skeleton → progress-bar → toast → confirm-dialog → password-input → textarea
**Each component:** standalone, OnPush, typed inputs/outputs, ControlValueAccessor where applicable

### Wave 2D — Shared Composites
**Deliverables:** `mee-stat-card`, `mee-status-badge`, `mee-page-header`, `mee-empty-state`, `mee-loading-skeleton`

### Wave 2E — Feature Pages (one session per feature)
**Sequence:** auth (login/signup/onboarding) → dashboard → smart-picker → catalog-form → images → preview → pricing → export → profile
**Each session:** reads matching Sakai-ng page from `themes/sakai-ng/` as layout reference, implements with `mee-*` components, wires to API services

---

## Sakai-ng as Layout Reference

Sakai-ng (`themes/signal-admin/` or fresh clone of sakai-ng) is used as a VISUAL and LAYOUT reference only during Wave 2E. Features read the Sakai page structure, adapt it to MeeSell's data model, and implement using `mee-*` wrappers — they do NOT copy PrimeNG component code directly.

The clone is at `themes/` and must NOT be imported into the Angular build.

---

## Non-Negotiable Rules

1. **PrimeNG import boundary:** `import { ... } from 'primeng/...'` is allowed ONLY in `src/app/ui/` files. ESLint rule to enforce this.
2. **No NgModules:** All components are `standalone: true`. No `declarations: []` arrays.
3. **OnPush everywhere:** `changeDetection: ChangeDetectionStrategy.OnPush` on all components.
4. **Signals for local state:** Use `signal()`, `computed()`, `effect()` — not `BehaviorSubject` for component-local state.
5. **RxJS for async:** HTTP calls, WebSocket, timers — RxJS. Component state — Signals.
6. **Typed strictly:** `strict: true` in tsconfig. No `any`. No `as unknown`.
7. **Mobile-first:** All layouts designed at 360px first, then 768px, then 1280px.

---

*Architecture owner: Director (master session)*
*Approved: 2026-06-08*
*Next: Wave 2B scaffold — new session*

---

## Revision History

| Date | Change | Author | Authority |
|---|---|---|---|
| 2026-06-08 | Initial APPROVAL — 4-layer architecture, PrimeNG abstraction wall, SOLID rules, single-app project structure, LOCKED technology decisions | Director (master session) | Founder approval (LOCKED) |
| 2026-06-11 | **Founder-approved §7.3 amendment — ADDITIVE as-built sync.** Added "Project Structure (as-built — federated workspace)" (apps/shell + apps/mfe-* 6 remotes + libs/ + the port registry 4200–4206 + the version-pinned staging/prod manifest shape) documenting the Module Federation program (SP00–SP07) as-built topology. Added the `@mesell/*` as-built path-alias block alongside the `@mee/*` design intent. Added this revision history. **No design decisions changed** — the 4-layer architecture, abstraction wall, SOLID rules, and LOCKED technology decisions are unchanged. Pure additive sync per the repo-management master plan §7.3 LOCKED-doc amendment rule. | `meesell-frontend-coordinator` (session `mesell-mfe-cutover-closeout-session-1`) | Founder-approved §7.3 amendment 2026-06-11 |
