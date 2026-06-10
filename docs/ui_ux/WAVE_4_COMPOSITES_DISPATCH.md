# WAVE 4 — SHARED COMPOSITES — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 4 — Shared Composites (C1–C5) |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder sub-session |
| **Agent** | `meesell-angular-component-builder` (sonnet) |
| **Depends-on** | Wave 3 — UI Kit (all 17 mee-* primitives built; `ui/index.ts` stable) |

---

## 1. Module Summary

| # | Selector | Class | Location | Purpose |
|---|---|---|---|---|
| C1 | `mee-stat-card` | `StatCardComponent` | `src/app/shared/stat-card/` | KPI tile: icon + label + value + optional trend. Wraps mee-card. |
| C2 | `mee-status-badge` | `StatusBadgeComponent` | `src/app/shared/status-badge/` | Maps `ProductStatus` enum → `MeeBadgeSeverity` and renders mee-badge. |
| C3 | `mee-page-header` | `PageHeaderComponent` | `src/app/shared/page-header/` | Title + subtitle + optional CTA button. Wraps mee-button. |
| C4 | `mee-empty-state` | `EmptyStateComponent` | `src/app/shared/empty-state/` | Centered icon + message + optional CTA. Wraps mee-button. |
| C5 | `mee-loading-skeleton` | `LoadingSkeletonComponent` | `src/app/shared/loading-skeleton/` | Shimmer placeholders for 4 variants. Wraps mee-skeleton. |

All 5 are standalone, OnPush, Layer 3 composites. They compose mee-* UI Kit primitives only — zero direct PrimeNG imports.

---

## 2. Dependencies

**UI Kit primitives consumed (from `../../ui`):**
- C1: `MeeCardComponent` (`mee-card`)
- C2: `MeeBadgeComponent` (`mee-badge`) + `MeeBadgeSeverity` type
- C3: `MeeButtonComponent` (`mee-button`)
- C4: `MeeButtonComponent` (`mee-button`)
- C5: `MeeSkeletonComponent` (`mee-skeleton`) + `MeeSkeletonVariant` type

**Composites consumed:** None — composites are Layer 3 peers; they do not compose each other.

**Layout:** N/A — shared components, no route, no layout wrapper.

**API endpoints:** None. All 5 are pure presentation composites.

**Barrel to update:** `src/app/shared/index.ts` — must export all 5 components and any public types.

> BOUNDARY: Import ONLY from `../../ui` (mee-* primitives) and `@angular/core` / `@angular/common`.
> ZERO `primeng/...` imports. ZERO `@angular/material/...` imports.

---

## 3. Files to Create / Modify

| Path | Action |
|---|---|
| `src/app/shared/stat-card/stat-card.component.ts` | CREATE |
| `src/app/shared/stat-card/stat-card.component.spec.ts` | CREATE |
| `src/app/shared/status-badge/status-badge.component.ts` | CREATE |
| `src/app/shared/status-badge/status-badge.component.spec.ts` | CREATE |
| `src/app/shared/page-header/page-header.component.ts` | CREATE |
| `src/app/shared/page-header/page-header.component.spec.ts` | CREATE |
| `src/app/shared/empty-state/empty-state.component.ts` | CREATE |
| `src/app/shared/empty-state/empty-state.component.spec.ts` | CREATE |
| `src/app/shared/loading-skeleton/loading-skeleton.component.ts` | CREATE |
| `src/app/shared/loading-skeleton/loading-skeleton.component.spec.ts` | CREATE |
| `src/app/shared/index.ts` | CREATE (barrel) |

---

## 4. Component Specs

### C1 — mee-stat-card (360px sketch)
```
┌─────────────────────────────┐
│  [icon]          [trend +%] │  ← icon: Material Symbol (48px); trend optional
│                             │
│  1,234                      │  ← value (large, bold)
│  Products created           │  ← label (muted, small)
└─────────────────────────────┘
```
**Inputs (from FRONTEND_ARCHITECTURE.md §Layer 3):**
- `label: string` (required)
- `value: string | number` (required)
- `icon: string` — Material Symbol name
- `trend?: number` — e.g. +12.5 or -3.2
- `trend_label?: string` — e.g. "vs last month"
- `color: 'orange' | 'blue' | 'green' | 'purple' = 'orange'`

**Signals:** `trendPositive = computed(() => (this.trend ?? 0) > 0)` for icon/color toggle.
**Color map:** Map color input → CSS var token for accent; no hex literals.

### C2 — mee-status-badge
```
  [ draft ]    [ ready ]    [ exported ]    [ live ]
  (gray)       (info)       (warning)        (success)
```
**Input:**
- `status: ProductStatus` — union: `'draft' | 'ready' | 'exported' | 'live' | 'deleted' | 'processing' | 'pending' | 'failed'`

**Status → Severity map:**
```
draft      → 'neutral'
ready      → 'info'
exported   → 'warning'
live       → 'success'
deleted    → 'danger'
processing → 'info'
pending    → 'neutral'
failed     → 'danger'
```
**Signal:** `severity = computed<MeeBadgeSeverity>(() => STATUS_MAP[this.status()] ?? 'neutral')`
Define `ProductStatus` as a string union type in the component file or a sibling `status-badge.types.ts`.

### C3 — mee-page-header (360px sketch)
```
┌─────────────────────────────────────────────┐
│  My Catalogs                  [+ New Catalog]│
│  Manage your product listings               │
└─────────────────────────────────────────────┘
```
**Inputs:**
- `title: string` (required)
- `subtitle?: string`
- `cta_label?: string`
- `cta_icon?: string` — Material Symbol name
**Output:** `cta_click = output<void>()`
**Signals:** `hasCta = computed(() => !!this.cta_label())`

### C4 — mee-empty-state (360px sketch)
```
┌─────────────────────────────┐
│                             │
│      [inventory icon]       │
│   No products yet           │
│   Create your first catalog │
│                             │
│   [ + Create Catalog ]      │
└─────────────────────────────┘
```
**Inputs:**
- `icon: string` — Material Symbol name
- `message: string`
- `cta_label?: string`
**Output:** `cta_click = output<void>()`
**Signals:** `hasCta = computed(() => !!this.cta_label())`

### C5 — mee-loading-skeleton
**Variants (input):** `variant: 'text' | 'card' | 'table-row' | 'stat-card' = 'text'`
- `text` — delegates to `<mee-skeleton variant="text" [lines]="lines">`
- `card` — delegates to `<mee-skeleton variant="card">`
- `table-row` — 4 rows of `<mee-skeleton variant="text">` stacked
- `stat-card` — 4 side-by-side `<mee-skeleton variant="stat-card">` blocks

Additional inputs: `lines = 1` (used for text variant only).
Uses `@switch/@case` Angular 18 control flow — no `ngSwitch`.

---

## 5. UI Kit Usage Map

| Component | UI element | mee-* used | Key @Inputs | @Outputs |
|---|---|---|---|---|
| C1 stat-card | Card wrapper | `mee-card` | content projection | — |
| C2 status-badge | Colored label | `mee-badge` | `[value]="status() | titlecase"` `[severity]="severity()"` | — |
| C3 page-header | CTA button | `mee-button` | `[label]="cta_label()"` `[icon]="cta_icon()"` `variant="primary"` | `(clicked)="cta_click.emit()"` |
| C4 empty-state | CTA button | `mee-button` | `[label]="cta_label()"` `variant="primary"` | `(clicked)="cta_click.emit()"` |
| C5 loading-skeleton | Shimmer rows | `mee-skeleton` | `[variant]="..."` `[lines]="lines()"` | — |

All mee-* contracts sourced from `FRONTEND_ARCHITECTURE.md` §Layer 2 Component Contracts.

---

## 6. API / Data

None. All 5 composites are pure presentation — no HTTP calls, no services injected.

---

## 7. Constraints

- `standalone: true, changeDetection: ChangeDetectionStrategy.OnPush` on all 5.
- `inject()` for DI — no constructor parameter injection.
- Signal inputs: use `input<T>()` / `input.required<T>()` API (Angular 21 signal inputs).
- Signal outputs: use `output<T>()` API (not `@Output() EventEmitter`).
- `computed()` for all derived values.
- **No hex literals** — use `var(--mee-color-*)` tokens or Tailwind semantic classes.
- **44px touch targets** on all interactive elements (mee-button handles this internally).
- **ZERO `primeng/...` imports** — composites sit at Layer 3; PrimeNG lives behind the ui/ wall.
- `@if`, `@for`, `@switch` — Angular 18 native control flow; no `*ngIf` / `*ngFor`.
- `src/app/shared/index.ts` barrel must re-export all 5 components + public types.

---

## 8. Out of Scope

- Any feature-page logic (data fetching, routing, form handling).
- Analytics or tracking instrumentation.
- i18n / Tamil/Hindi locale pipes — V1.5.
- Animation beyond CSS transitions already in design tokens.
- Modification of `src/app/ui/` — that is Wave 3 territory.

---

## 9. Verification Gates

1. **BUILD** — `cd frontend && pnpm run build` — zero errors, zero new warnings.
2. **ROUTES RESOLVE** — N/A (no routes). Verify each composite renders correctly by importing into a test harness or checking spec rendering.
3. **BOUNDARY** — `grep -r "primeng" src/app/shared/` returns zero lines (no PrimeNG imports).
4. **TESTS** — `pnpm run test` — minimum 3 tests per composite = 15 new tests, all passing. Tests must use `TestBed.configureTestingModule` standalone pattern. Stub any mee-* child components via `TestBed.overrideComponent`.
5. **FOUNDER VISUAL** — Founder reviews stat-card + status-badge + page-header at 360px and 1280px against the Sakai-ng reference.

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 4 — SHARED COMPOSITES (C1–C5)
Agent: meesell-angular-component-builder (sonnet)
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Wave 3 UI Kit gate must be confirmed before starting:
  • All 17 mee-* primitives built in src/app/ui/
  • ui/index.ts barrel exports all components + types
  • Smoke tests passing for all 17

This dispatch authors the 5 Layer 3 Shared Composites.
They compose mee-* primitives — ZERO direct PrimeNG usage.

BOUNDARY (NON-NEGOTIABLE)
───────────────────────────
  • Import ONLY from ../../ui (mee-* primitives), @angular/core, @angular/common
  • ZERO primeng/... imports in shared/ files
  • Run: grep -r "primeng" src/app/shared/ → must return empty

══════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  src/app/shared/stat-card/stat-card.component.ts          + spec.ts
  src/app/shared/status-badge/status-badge.component.ts    + spec.ts
  src/app/shared/page-header/page-header.component.ts      + spec.ts
  src/app/shared/empty-state/empty-state.component.ts      + spec.ts
  src/app/shared/loading-skeleton/loading-skeleton.component.ts + spec.ts
  src/app/shared/index.ts  (barrel — export all 5 + types)

══════════════════════════════════════════════════════════════════

COMPOSITE SPECS
───────────────

C1 — mee-stat-card
  @inputs: label: string, value: string|number, icon: string,
           trend?: number, trend_label?: string,
           color: 'orange'|'blue'|'green'|'purple' = 'orange'
  Wraps: <mee-card> with content projection
  Trend: computed() trendPositive → icon/color; hide when trend undefined

C2 — mee-status-badge
  @input: status: ProductStatus (signal input required)
  Maps → MeeBadgeSeverity:
    draft→neutral  ready→info  exported→warning  live→success
    deleted→danger  processing→info  pending→neutral  failed→danger
  Wraps: <mee-badge [value]="..." [severity]="severity()">

C3 — mee-page-header
  @inputs: title: string (required), subtitle?: string,
           cta_label?: string, cta_icon?: string
  @output: cta_click = output<void>()
  Wraps: <mee-button> for CTA (hidden when no cta_label)

C4 — mee-empty-state
  @inputs: icon: string, message: string, cta_label?: string
  @output: cta_click = output<void>()
  Wraps: <mee-button> for CTA (hidden when no cta_label)

C5 — mee-loading-skeleton
  @inputs: variant: 'text'|'card'|'table-row'|'stat-card' = 'text',
           lines = 1
  Uses @switch/@case for variant dispatch
  Wraps: <mee-skeleton [variant]="..." [lines]="lines()">

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone + OnPush + signal inputs (input<T>()) + signal outputs (output<T>())
  • computed() for all derived state (severity, hasCta, trendPositive)
  • No hex literals — var(--mee-color-*) or Tailwind semantic classes only
  • 44px touch targets (mee-button handles internally)
  • @if/@for/@switch control flow (no *ngIf/*ngFor)
  • Barrel: shared/index.ts exports all 5 + public types

OUT OF SCOPE
  ✗ Feature-page logic, routing, HTTP
  ✗ i18n / locale pipes (V1.5)
  ✗ Modification of src/app/ui/

VERIFICATION GATES
──────────────────
Gate 1 BUILD:    pnpm run build → zero errors
Gate 2 BOUNDARY: grep -r "primeng" src/app/shared/ → empty
Gate 3 TESTS:    pnpm run test → min 15 new tests (3 per composite), all pass
Gate 4 BARREL:   shared/index.ts exports all 5 components + ProductStatus type
Gate 5 VISUAL:   Founder reviews stat-card + status-badge + page-header at 360px

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-09 | meesell-frontend-coordinator (master) | Initial authoring — Wave 4 composites; Option A-full architecture |
