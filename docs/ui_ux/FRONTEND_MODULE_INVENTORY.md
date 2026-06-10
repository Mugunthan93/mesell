# MeeSell Frontend — Complete UI Module Inventory

| Field | Value |
|---|---|
| **Document type** | Module collection (step 1 of 3) |
| **Date** | 2026-06-09 |
| **Author** | meesell-frontend-coordinator (master) |
| **Source of truth** | `V1_FEATURE_SPEC.md` §3/§6, `FRONTEND_ARCHITECTURE.md` (LOCKED 2026-06-08) |
| **Purpose** | Authoritative list of every UI module, its layer, dependencies, and build status |

---

## The Locked 4-Layer Architecture

```
Layer 1 — Design System   (tokens, type, motion, elevation)   ← no dependencies
    ▼
Layer 2 — UI Kit          (17 mee-* primitives wrapping PrimeNG)
    ▼
Layer 3 — Composites      (5 mee-* composites) + Layouts (shell, auth-layout)
    ▼
Layer 4 — Features         (11 feature pages)                  ← consume Layers 2+3 only
```

**Non-negotiable rule (FRONTEND_ARCHITECTURE.md §Non-Negotiable #1):**
> `import { ... } from 'primeng/...'` is allowed ONLY in `src/app/ui/` files.

---

## Build Status Snapshot (verified on disk 2026-06-09)

| Layer | Module group | On disk? | Status |
|---|---|---|---|
| 1 | Design System (`design-system/`) | `_tokens.css` only | 🟡 PARTIAL (typography/motion/elevation tokens inline in CSS, not split files) |
| 2 | UI Kit (`ui/`) | ❌ absent | 🔴 NOT BUILT |
| 3 | Composites (`shared/`) | ❌ absent | 🔴 NOT BUILT |
| 3 | Layouts (`layouts/`) | shell + auth-layout | 🟢 DONE (Wave 2B) |
| 4 | Auth (`features/auth/`) | login/signup/otp-verify | 🟠 BUILT — but imports PrimeNG directly (**violates boundary rule**) |
| 4 | All other features | stubs only | 🔴 NOT BUILT |

⚠️ **Divergence:** Wave 2C built auth pages with direct PrimeNG imports instead of the planned Layer 2 UI Kit. This is the architectural fork that gates the rest of this plan (see end of doc).

---

## Layer 2 — UI Kit Modules (17 primitives)

**Location:** `src/app/ui/` · **All wrap a PrimeNG component** · **Barrel:** `ui/index.ts`

| # | Module | Selector | Wraps | Key contract |
|---|---|---|---|---|
| K1 | Button | `mee-button` | `p-button` | variant, size, loading, icon, `clicked` |
| K2 | Input | `mee-input` | `pInputText` | label, prefix, error, CVA two-way |
| K3 | OTP Input | `mee-otp-input` | `p-inputotp` | length=6, `completed` |
| K4 | Password Input | `mee-password-input` | `p-password` | CVA, toggle mask |
| K5 | Textarea | `mee-textarea` | `pTextarea` | label, error, CVA |
| K6 | Select | `mee-select` | `p-select` | options, CVA, `value_change` |
| K7 | Tree Select | `mee-tree-select` | `p-treeSelect` | nodes, `value_change` (category picker) |
| K8 | Table | `mee-table` | `p-table` | columns, rows, paginator, sort events |
| K9 | Card | `mee-card` | `p-card` | content projection |
| K10 | Dialog | `mee-dialog` | `p-dialog` | header, `[(visible)]`, `closed` |
| K11 | Confirm Dialog | `mee-confirm-dialog` | `p-confirmDialog` | service-based (`MeeConfirmService`) |
| K12 | File Upload | `mee-file-upload` | `p-fileUpload` | accept, max_size, `files_selected` |
| K13 | Steps | `mee-steps` | `p-steps` | steps[], active_index |
| K14 | Progress Bar | `mee-progress-bar` | `p-progressBar` | value 0–100, label |
| K15 | Badge | `mee-badge` | `p-tag` | value, severity |
| K16 | Toast | `mee-toast` + service | `p-toast` | host once in shell, `MeeToastService` |
| K17 | Skeleton | `mee-skeleton` | `p-skeleton` | variant: text/card/table-row/stat-card |

**Internal dependency:** K1–K17 are mostly independent of each other → **high parallelism**.
Priority order (per arch): button → input → otp-input → badge → card → table → dialog → file-upload → steps → select → tree-select → skeleton → progress-bar → toast → confirm-dialog → password-input → textarea.

---

## Layer 3 — Composite Modules (5) + Layouts

**Location:** `src/app/shared/` · **Each composes Layer 2 primitives**

| # | Module | Selector | Composes | Used by |
|---|---|---|---|---|
| C1 | Stat Card | `mee-stat-card` | mee-card | Dashboard |
| C2 | Status Badge | `mee-status-badge` | mee-badge | Dashboard, Catalog Form, Export |
| C3 | Page Header | `mee-page-header` | mee-button | every feature page |
| C4 | Empty State | `mee-empty-state` | mee-button | Dashboard, lists |
| C5 | Loading Skeleton | `mee-loading-skeleton` | mee-skeleton | every async page |

**Layouts (DONE):** `shell` (sidebar+topbar), `auth-layout` (centered card).

**Dependency:** C1–C5 depend on Layer 2 → must come **after** UI Kit. Independent of each other → parallel.

---

## Layer 4 — Feature Modules (11)

**Location:** `src/app/features/` · **Import ONLY from `ui/`, `shared/`, `layouts/`, own services**

| # | Module | Route | Component | Core UI Kit / Composites used | API endpoints | Status |
|---|---|---|---|---|---|---|
| F1 | Landing | `/` | `LandingComponent` | mee-button | — (public) | 🔴 |
| F2 | Login | `/login` | `LoginComponent` | mee-input, mee-button | `auth/otp/send` | 🟠 redo via kit |
| F3 | Signup | `/signup` | `SignupComponent` | mee-input, mee-button | `auth/otp/send` | 🟠 redo via kit |
| F4 | OTP Verify | `/login` (OTP step) | `OtpVerifyComponent` | mee-otp-input, mee-button | `auth/otp/verify` | 🟠 redo via kit |
| F5 | Onboarding | `/onboarding` | `OnboardingComponent` | mee-input, mee-steps, mee-button | (profile patch) | 🔴 |
| F6 | Dashboard | `/dashboard` | `DashboardComponent` | mee-table, mee-stat-card, mee-status-badge, mee-empty-state, mee-page-header | `GET products` | 🔴 |
| F7 | Smart Picker | `/catalogs/new` | `SmartPickerComponent` | mee-input/textarea, mee-card, mee-tree-select, mee-progress-bar | `categories/suggest` | 🔴 |
| F8 | Catalog Form | `/catalogs/:id/edit` | `CatalogFormComponent` | mee-input, mee-select, mee-button, mee-toast, mee-status-badge | `products`, `autofill`, `{id}/schema` | 🔴 |
| F9 | Images | `/catalogs/:id/images` | `ImageUploaderComponent` | mee-file-upload, mee-progress-bar, mee-badge | `{id}/images` | 🔴 |
| F10 | Preview | `/catalogs/:id/preview` | `PreviewComponent` | mee-card, mee-skeleton | `{id}/preview` | 🔴 |
| F11 | Pricing | `/catalogs/:id/pricing` | `PricingComponent` | mee-input, mee-card (P&L), slider | `{id}/price-calc` | 🔴 |
| F12 | Export | `/catalogs/:id/export` | `ExportComponent` | mee-button, mee-progress-bar, mee-status-badge | `export-xlsx`, `exports/{id}` | 🔴 |
| F13 | Profile | `/profile` | `ProfileComponent` | mee-input, mee-button, mee-card | (user patch) | 🔴 |

> Note: F2–F4 (auth) are built but bypass the UI Kit. "Redo via kit" applies only under Option A below.

**Dependency:** every feature depends on Layers 2+3. Features are **independent of each other** → highest parallelism once the kit exists.

---

## Dependency Graph (determines parallelization)

```
Layer 1 (tokens) ✅
      │
      ▼
Layer 2 UI Kit (K1–K17) ────────────┐   ← parallel batch, gates everything
      │                             │
      ▼                             ▼
Layer 3 Composites (C1–C5)     [auth refactor F2–F4]
      │
      ▼
Layer 4 Features (F1, F5–F13) ← parallel fan-out, each its own session
```

**Hard ordering:** Kit → Composites → Features. **Within each tier:** fully parallel.

---

## ⚠️ The Fork That Gates Everything

Wave 2C auth pages import PrimeNG directly. This breaks the locked Layer-2 boundary. Two ways forward — this choice determines the entire wave structure and all dispatch docs:

### Option A — Keep the 4-layer architecture (as LOCKED)
- Build Layer 2 UI Kit (17 primitives) first
- Refactor F2–F4 auth pages to use `mee-input` / `mee-otp-input` / `mee-button`
- Then composites, then features
- **Pro:** library-swap-proof, ESLint-enforceable, matches locked spec, consistent
- **Con:** ~17 + 5 extra modules before any new feature; auth redo

### Option B — Flatten to direct-PrimeNG (amend the architecture)
- Drop Layer 2 UI Kit entirely; features import PrimeNG directly (like auth already does)
- Keep design tokens (Layer 1) for brand consistency
- **Pro:** fewer files, faster to features, auth already fits, fewer waves
- **Con:** loses abstraction boundary, harder to swap PrimeNG later, no enforced consistency, the locked architecture must be formally amended

**This decision changes: number of waves, whether a UI Kit wave exists, whether auth is refactored, and the content of all ~12 dispatch docs.**
