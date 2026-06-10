# WAVE 5 — DASHBOARD — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature Pages |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder (sonnet) |
| **Agent** | meesell-angular-component-builder |
| **Depends on** | Wave 3 UI Kit complete + Wave 4 composites complete |

---

## 1. Module Summary

| Field | Value |
|---|---|
| **Route** | `/dashboard` (shell child — auth-guarded) |
| **Component class** | `DashboardComponent` |
| **Selector** | `app-dashboard` |
| **Feature path** | `src/app/features/dashboard/dashboard.component.ts` |
| **Purpose** | Product list with status filters, stat cards by status count, empty state for new sellers |
| **Status** | F6 — NOT BUILT (Wave 5 target) |
| **V1 spec ref** | Feature 8 (Tracking Dashboard), §3 steps 4 + 12, §5 GET /api/v1/products, §6 /dashboard |

---

## 2. Dependencies

### UI Kit Primitives (Layer 2 — from `../../ui`)
| Primitive | Selector | Used for |
|---|---|---|
| MeeTableComponent | `mee-table` | Product list — columns: name, category, status, updated_at |
| MeeButtonComponent | `mee-button` | "New Catalog" CTA in page header; row-level action fallback |

### Composites (Layer 3 — from `../../shared`)
| Composite | Selector | Used for |
|---|---|---|
| MeeStatCardComponent | `mee-stat-card` | 4 status-count summary cards (draft / ready / exported / live) |
| MeeStatusBadgeComponent | `mee-status-badge` | Status cell in each table row |
| MeePageHeaderComponent | `mee-page-header` | "My Catalogs" title + "New Catalog" CTA button |
| MeeEmptyStateComponent | `mee-empty-state` | Zero-products state ("Create your first catalog") |
| MeeLoadingSkeletonComponent | `mee-loading-skeleton` | Loading state (variant: stat-card × 4 + table-row × 5) |

### Layout
Shell child — `DashboardComponent` is loaded inside `MeeShellComponent` via `<router-outlet>`. No layout wrapping inside the component itself.

### API Endpoints (V1_FEATURE_SPEC.md §5)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/products?page=1&limit=20` | Paginated product list; supports `status_filter`, `search` params |
| DELETE | `/api/v1/products/{id}` | Soft-delete (confirm modal before call) |

**Until API is available: SIMULATE** with 5 seed rows covering statuses `draft`, `ready`, `exported`, `live`, `draft`. Simulate 800 ms delay on load.

⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `../../layouts`, `./services/`. ZERO `primeng/...` imports in this file.

---

## 3. Files to Create / Modify

| File | Action |
|---|---|
| `features/dashboard/dashboard.component.ts` | CREATE — full page component |
| `features/dashboard/dashboard.component.spec.ts` | CREATE — minimum 5 tests |
| `features/dashboard/services/dashboard-api.service.ts` | CREATE — feature-scoped (if not yet present) |

Do NOT modify `app.routes.ts` — dashboard route already exists from Wave 2B scaffold.

---

## 4. Component Spec

### ASCII Sketch — 360px mobile-first

```
┌─────────────────────────────────────────┐
│ [sidebar collapsed / topbar on mobile]  │  ← MeeShellComponent (parent)
├─────────────────────────────────────────┤
│  My Catalogs          [ + New Catalog ] │  ← mee-page-header
├─────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────┐ │
│ │ Draft  │ │ Ready  │ │Exported│ │Live│ │  ← mee-stat-card ×4 (2×2 grid on 360px)
│ │   3    │ │   1    │ │   2    │ │  1 │ │    icon + count + label
│ └────────┘ └────────┘ └────────┘ └────┘ │
├─────────────────────────────────────────┤
│ [Search...]          [Status ▼]         │  ← native <input> + <select> (controlled)
├─────────────────────────────────────────┤
│  (if loading)                           │
│  ░░░░░░░░░░░░░  ░░░  ░░░░ ░░░░          │  ← mee-loading-skeleton (table-row ×5)
│                                         │
│  (if empty)                             │
│  ┌─────────────────────────────────┐   │
│  │ [icon]                          │   │  ← mee-empty-state
│  │ No catalogs yet                 │   │
│  │ Create your first catalog       │   │
│  │ [ + New Catalog ]               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  (if data)                              │
│  ┌─────────────────────────────────┐   │
│  │ Name    Cat   Status   Updated  │   │  ← mee-table
│  ├─────────────────────────────────┤   │
│  │ Kurti…  Eth…  [draft]  2h ago   │   │    mee-status-badge in status cell
│  │ Salwar… Eth…  [live]   1d ago   │   │    row_click → /catalogs/:id/edit
│  │ Tops…   Top…  [ready]  3d ago   │   │
│  └─────────────────────────────────┘   │
│  < 1 2 3 >  Showing 1–20 of 47         │  ← mee-table paginator
└─────────────────────────────────────────┘
```

**Desktop note (1280px):** stat cards render 4-across in a single row; table shows full column widths; sidebar is expanded (270px). Layout handled by shell — component uses `w-full` container.

### Signals / State
```typescript
readonly loading     = signal(true);
readonly products    = signal<ProductListItem[]>([]);
readonly totalCount  = signal(0);
readonly statusCounts = signal({ draft: 0, ready: 0, exported: 0, live: 0 });
readonly page        = signal(1);
readonly searchQuery = signal('');
readonly statusFilter = signal<string>('');
```

### Behaviors
- On init: fetch product list (simulated); derive status counts from response
- Search: debounce 400 ms; re-fetch on query change
- Status filter: `<select>` drives `statusFilter` signal; re-fetch on change
- Row click on `mee-table` `row_click` output → `router.navigate(['/catalogs', row.id, 'edit'])`
- Empty state CTA click → `router.navigate(['/catalogs/new'])`
- Pagination: `mee-table` `page` output → update `page` signal → re-fetch
- Delete: confirm dialog via `MeeConfirmService` → call API → refresh list

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key @Input / @Output |
|---|---|---|
| Page title + CTA | `mee-page-header` | `[title]="'My Catalogs'"` `[cta_label]="'New Catalog'"` `[cta_icon]="'add'"` `(cta_click)="onNewCatalog()"` |
| Draft count card | `mee-stat-card` | `[label]="'Draft'"` `[value]="statusCounts().draft"` `[icon]="'edit_note'"` `[color]="'blue'"` |
| Ready count card | `mee-stat-card` | `[label]="'Ready'"` `[value]="statusCounts().ready"` `[icon]="'check_circle'"` `[color]="'green'"` |
| Exported count card | `mee-stat-card` | `[label]="'Exported'"` `[value]="statusCounts().exported"` `[icon]="'download'"` `[color]="'purple'"` |
| Live count card | `mee-stat-card` | `[label]="'Live'"` `[value]="statusCounts().live"` `[icon]="'storefront'"` `[color]="'orange'"` |
| Product list | `mee-table` | `[columns]="columns"` `[rows]="products()"` `[loading]="loading()"` `[paginator]="true"` `[total_records]="totalCount()"` `(row_click)="onRowClick($event)"` `(page)="onPage($event)"` |
| Status column cell | `mee-status-badge` | `[status]="row.status"` — rendered inside mee-table body template |
| Loading state | `mee-loading-skeleton` | `[variant]="'table-row'"` — shown via `@if (loading())` |
| Empty state | `mee-empty-state` | `[title]="'No catalogs yet'"` `[message]="'Create your first catalog to get started'"` `[cta_label]="'New Catalog'"` `(cta_click)="onNewCatalog()"` |

---

## 6. API / Data

### GET /api/v1/products
**Request params:** `page`, `limit=20`, `status_filter?`, `search?`

**Response shape (expected):**
```typescript
interface ProductListResponse {
  products: ProductListItem[];
  total: number;
  page: number;
}
interface ProductListItem {
  id: string;
  name: string;
  category_name: string;
  status: 'draft' | 'ready' | 'exported' | 'live' | 'deleted';
  updated_at: string;   // ISO timestamp
}
```

**Simulation strategy:** Seed 5 `ProductListItem` objects inline in the service. `loadProducts()` returns `of({ products: SEED, total: 5, page: 1 })` piped through `delay(800)`. Status counts derived from `SEED` via `Array.reduce`.

### DELETE /api/v1/products/{id}
**Simulation:** `of(null).pipe(delay(500))`. On success: remove row from `products()` signal, decrement count.

---

## 7. Constraints

| Rule | Detail |
|---|---|
| Standalone + OnPush | `@Component({ standalone: true, changeDetection: ChangeDetectionStrategy.OnPush })` |
| Signals for local state | `signal()` / `computed()` — no `BehaviorSubject` in component class |
| No PrimeNG imports | Feature file imports ONLY from `../../ui`, `../../shared`, `@angular/core`, `@angular/router`, `@angular/forms`, rxjs |
| 44px touch targets | Row click area min-height 44px; stat card min-height 44px; all interactive controls |
| Reactive Forms only | If a form control is needed (search input), use `FormControl` — no template-driven |
| Design tokens only | Colors via `var(--mee-color-*)` tokens — no hardcoded hex in component |
| Service scoping | `DashboardApiService` provided via feature route `providers:[]`, not `providedIn: 'root'` |
| takeUntilDestroyed | Any RxJS subscription in constructor uses `takeUntilDestroyed()` from `@angular/core/rxjs-interop` |

---

## 8. Out of Scope

| Item | When |
|---|---|
| Real `GET /api/v1/products` HTTP call | Wave 6 API wiring |
| Real `DELETE /api/v1/products/{id}` | Wave 6 API wiring |
| Bulk operations (multi-select delete) | V1.5 |
| Analytics columns (CTR, conversion) | V1.5 |
| Export shortcut from dashboard row | V1.5 |
| "Live" status sync via Meesho API | Out of scope — manual only |

---

## 9. Verification Gates

### Gate 1 — BUILD
```bash
cd frontend && pnpm run build
```
Pass: zero errors, zero new warnings.

### Gate 2 — ROUTES RESOLVE
```bash
cd frontend && pnpm start
```
Visit `http://localhost:4200/dashboard` (after login) — DashboardComponent renders, stat cards visible, table populated with simulated rows.

### Gate 3 — VALIDATION / INTERACTION
- Empty-state renders when seed data removed (set `SEED = []`)
- Status filter dropdown filters visible rows
- Row click navigates to `/catalogs/mock-id/edit`
- Pagination controls visible with total > 20

### Gate 4 — TESTS
```bash
cd frontend && pnpm run test
```
Minimum 5 tests:
1. Renders `mee-page-header` with title "My Catalogs"
2. Renders 4 `mee-stat-card` elements
3. Shows `mee-empty-state` when `products()` is empty
4. `onNewCatalog()` navigates to `/catalogs/new`
5. `onRowClick(row)` navigates to `/catalogs/{row.id}/edit`

### Gate 5 — VISUAL (founder)
Founder reviews at 360px and 1280px:
- Orange stat card for "Live" count
- Status badges color-coded (gray draft / green live / blue exported)
- Table row hover highlight
- Empty state illustration + CTA

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — DASHBOARD (F6)
Agent: meesell-angular-component-builder (sonnet)
Depends on: Wave 3 UI Kit + Wave 4 Composites
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Option A-full architecture (founder ratified 2026-06-09).
Dashboard is a shell child — no layout wrapping inside component.
API NOT available — simulate with 5 seed rows + delay(800).
Status counts derived from seed array via reduce.

BOUNDARY (enforced)
───────────────────
Import ONLY from:
  ../../ui            (mee-* UI Kit)
  ../../shared        (composites)
  ../../layouts       (if needed — unlikely for shell child)
  ./services/         (DashboardApiService, feature-scoped)
  @angular/core, @angular/router, @angular/forms, rxjs

ZERO primeng/... imports in features/dashboard/**.

══════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  features/dashboard/dashboard.component.ts      (page component)
  features/dashboard/dashboard.component.spec.ts (min 5 tests)
  features/dashboard/services/dashboard-api.service.ts

══════════════════════════════════════════════════════════════════

COMPONENT SUMMARY
─────────────────
Route:      /dashboard (shell child)
Class:      DashboardComponent
Selector:   app-dashboard

UI Kit used:
  mee-page-header   — title "My Catalogs" + "New Catalog" CTA
  mee-stat-card     — ×4 (draft/ready/exported/live counts)
  mee-table         — columns: name, category, status, updated_at
  mee-status-badge  — inside table status cell
  mee-empty-state   — zero products + CTA → /catalogs/new
  mee-loading-skeleton — while loading (table-row variant)

Signals:
  loading, products, totalCount, statusCounts, page, searchQuery, statusFilter

Behaviors:
  row_click output → router.navigate /catalogs/:id/edit
  empty-state cta_click → /catalogs/new
  search: debounce 400ms, re-fetch
  status filter: re-fetch on change
  pagination: mee-table page output → update page signal

──────────────────────────────────────────────────────────────────

API (SIMULATED)
───────────────
GET  /api/v1/products?page&limit&status_filter&search
  → { products: ProductListItem[], total: number, page: number }
DELETE /api/v1/products/{id}   → null (204)

Seed 5 rows spanning draft/ready/exported/live/draft.
of(SEED).pipe(delay(800)) pattern.

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone: true, changeDetection: OnPush
  • signal() for all local state — no BehaviorSubject in component
  • DashboardApiService: @Injectable() no providedIn — route providers[]
  • takeUntilDestroyed() for any RxJS in constructor
  • 44px touch targets on all interactive elements
  • var(--mee-color-*) tokens — no hardcoded hex
  • ReactiveFormsModule if search FormControl used

OUT OF SCOPE
────────────
  ✗ Real HTTP calls (Wave 6)
  ✗ Bulk delete (V1.5)
  ✗ Analytics columns (V1.5)

VERIFICATION GATES
──────────────────
Gate 1 BUILD:      pnpm run build → zero errors
Gate 2 ROUTES:     /dashboard renders — stat cards + table
Gate 3 INTERACTION: filter/search/pagination/empty-state work
Gate 4 TESTS:      pnpm run test → 5+ new tests passing
Gate 5 VISUAL:     ⏳ founder reviews at 360px + 1280px

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```
