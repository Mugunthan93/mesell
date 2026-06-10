# WAVE 5 — PREVIEW — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature: Preview (F10) |
| **Date authored** | 2026-06-09 |
| **Status** | READY |
| **Agent** | `meesell-angular-component-builder` |
| **Recipient** | Sub-session executing Wave 5 group C |
| **Depends on** | Wave 3 UI Kit complete (ui/index.ts stable) + Wave 4 Composites complete |

---

## 1. Module Summary

| Property | Value |
|---|---|
| **Route** | `/catalogs/:id/preview` |
| **Component class** | `PreviewComponent` |
| **Selector** | `app-preview` |
| **Location** | `src/app/features/preview/preview/preview.component.ts` |
| **Shell relationship** | Child of `MeeShellComponent` (rendered via shell router-outlet) |
| **Purpose** | Read-only display of three Meesho-style mock renders (feed thumbnail, detail page, mobile card) so sellers can see how the listing looks before exporting. Shows title truncation warning at ~30 chars. No forms. |
| **Status** | NOT BUILT |

---

## 2. Dependencies

### UI Kit primitives (Layer 2 — mee-* only)
| Primitive | Usage |
|---|---|
| `mee-card` | Outer wrapper for each of the 3 preview surfaces |
| `mee-skeleton` | Loading state while preview data is fetched |
| `mee-button` | "Edit product" CTA (links back to `/catalogs/:id/edit`) |
| `mee-badge` | Tab/surface selector chip (Feed / Detail / Mobile) |

### Composites (Layer 3)
| Composite | Usage |
|---|---|
| `mee-page-header` | Page title "Product Preview" + subtitle |
| `mee-loading-skeleton` | Skeleton variant while preview JSON loads |
| `mee-status-badge` | Optional: show product status in header |

### Layout
- Shell child — no layout component import needed.

### API endpoints (V1_FEATURE_SPEC §5)
| Method | Path | Used for |
|---|---|---|
| `GET` | `/api/v1/products/{id}/preview` | Fetch preview JSON (title, price, image_url, category_path, variant) |

> **SIMULATE strategy:** On `ngOnInit`, set `loading.set(true)`, wait 800 ms, then set a hardcoded `PreviewData` object matching the journey step 8 scenario (Blue Cotton Kurti, MRP ₹899, 4 images, title long enough to trigger truncation warning). No HttpClient wiring.

> ⚠️ BOUNDARY: import ONLY from `../../ui`, `../../shared`, `../../layouts`, own services. ZERO `primeng/...` imports.

---

## 3. Files to Create / Modify

| Action | Path |
|---|---|
| Create | `src/app/features/preview/preview/preview.component.ts` |
| Create | `src/app/features/preview/preview/preview.component.spec.ts` |
| Create | `src/app/features/preview/preview/preview.model.ts` |
| Update | `docs/status/STATUS_FRONTEND.md` |

Do NOT modify `app.routes.ts` — route registration is coordinator scope.

---

## 4. Component Spec

This component is layout-heavy. Three distinct preview surfaces must be rendered side-by-side on desktop, stacked on mobile.

### ASCII layout — 360px mobile first

```
┌─────────────────────────────────────┐
│  mee-page-header                    │
│  "Product Preview"                  │
│  "How your listing looks on Meesho" │
├─────────────────────────────────────┤
│  SURFACE TABS (mee-badge chips)     │
│  [ Feed ]  [ Detail ]  [ Mobile ]   │
│  (mobile: shows one surface at a    │
│   time; desktop: all 3 side-by-side)│
├─────────────────────────────────────┤
│                                     │
│  SURFACE 1 — FEED THUMBNAIL         │
│  (mee-card wrapper)                 │
│  ┌───────────────────────────┐      │
│  │ [product image 160×200px] │      │
│  │ Blue Cotton Kurti With    │      │
│  │ Mir…          ← TRUNCATED │      │
│  │ ▲ "Title cuts at char 30" │      │  ← warning badge
│  │ ₹899          ★ 4.2 (120) │      │
│  │ FREE delivery             │      │
│  └───────────────────────────┘      │
│  Label: "Feed thumbnail"            │
│                                     │
│  SURFACE 2 — DETAIL PAGE            │
│  (mee-card wrapper)                 │
│  ┌───────────────────────────┐      │
│  │ [product image full-width]│      │
│  │ • • •  (image dots)       │      │
│  │ Blue Cotton Kurti With    │      │
│  │ Mirror Work               │      │  ← full title
│  │ ₹899                      │      │
│  │ Commission: 5%  GST: 5%   │      │
│  │ Category: Fashion > ...   │      │
│  │ [Add to cart]  [Buy now]  │      │  ← simulated CTA (non-interactive)
│  └───────────────────────────┘      │
│  Label: "Detail page"               │
│                                     │
│  SURFACE 3 — MOBILE CARD            │
│  (mee-card wrapper, 360px sim)      │
│  ┌───────────────────────────┐      │
│  │ [image]  [image]          │      │  ← 2-up mobile grid
│  │ Blue Co… ₹899             │      │  ← ~20 chars before cut
│  │ Blue Co… ₹899             │      │
│  └───────────────────────────┘      │
│  Label: "Mobile grid card"          │
│                                     │
├─────────────────────────────────────┤
│  TITLE TRUNCATION WARNING           │
│  ┌───────────────────────────┐      │
│  │ ⚠ "Blue Cotton Kurti With │      │
│  │ Mir…" — title cut at char │      │
│  │ 30 on mobile feed view.   │      │
│  │ Shortened title:          │      │
│  │ "Blue Cotton Kurti —      │      │
│  │ Mirror Work" (36 chars —  │      │
│  │ still long; aim for ≤30)  │      │
│  └───────────────────────────┘      │
│                                     │
│  [Edit product]    mee-button       │
│  (secondary, links to /edit)        │
└─────────────────────────────────────┘
```

Desktop (1280px): all 3 surfaces rendered as a 3-column horizontal row in one `mee-card` strip. No tab switching needed — all visible simultaneously. Truncation warning panel sits below the strip.

### Surface tab behavior (mobile only)
- `activeTab = signal<'feed' | 'detail' | 'mobile'>('feed')`
- Clicking a tab chip switches the visible surface on mobile
- Desktop: `@if (isDesktop())` shows all 3; mobile: `@switch (activeTab())` shows one

### Signals / state
```
loading = signal<boolean>(true)
preview = signal<PreviewData | null>(null)
activeTab = signal<'feed' | 'detail' | 'mobile'>('feed')
titleTruncated = computed(() => (preview()?.title?.length ?? 0) > 30)
truncatedTitle = computed(() => preview()?.title?.slice(0, 30) + '…')
isDesktop = signal<boolean>(window.innerWidth >= 1024)
```

### Behaviors
- `ngOnInit`: `setTimeout(() => { this.preview.set(SIMULATED_PREVIEW); this.loading.set(false); }, 800)`
- `onTabChange(tab)`: `this.activeTab.set(tab)` — mobile only
- `onEditProduct()`: `router.navigate(['/catalogs', productId, 'edit'])`
- Resize listener (optional V1): toggle `isDesktop` on window resize

---

## 5. UI Kit Usage Map

| UI element | mee-* component | Key inputs/outputs |
|---|---|---|
| Surface wrapper | `mee-card` | content projection for each preview surface |
| Loading state | `mee-skeleton` | `variant="card"` x3 while loading |
| Tab chip | `mee-badge` | `[value]="tab.label"`, click handler sets `activeTab` |
| Edit CTA | `mee-button` | `label="Edit product"`, `variant="secondary"`, `(clicked)` |
| Page header | `mee-page-header` | `title="Product Preview"`, `subtitle="How your listing looks on Meesho"` |
| Composite skeleton | `mee-loading-skeleton` | wraps the 3-surface area during load |

---

## 6. API / Data

### Feature-local model (`preview.model.ts`)
```
PreviewData {
  product_id: string
  title: string
  mrp: number
  category_path: string      // e.g. "Fashion > Women > Ethnic > Kurti"
  commission_pct: number
  gst_pct: number
  primary_image_url: string  // GCS signed URL or placeholder
  image_urls: string[]       // ordered list, up to 6
  variant_label: string | null  // e.g. "M / Blue"
}
```

### Simulated data (journey step 8)
```
title: "Blue Cotton Kurti With Mirror Work"   // 35 chars → triggers truncation warning
mrp: 899
category_path: "Fashion > Women > Ethnic > Kurti"
commission_pct: 5
gst_pct: 5
primary_image_url: "/assets/placeholder-product.png"
image_urls: ["/assets/placeholder-product.png", ...]  // 4 items
variant_label: "M / Blue"
```

---

## 7. Constraints

- `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush`
- Use `inject()` for all DI (ActivatedRoute, Router)
- `signal()` for all local state; `computed()` for derived display values
- NO Reactive Forms — this is a read-only display component
- Surfaces are rendered via Angular 18 native control flow `@if`/`@switch` — no `*ngIf`
- Design tokens only — no hex literals; use `var(--mee-color-*)` or mee-* Tailwind classes
- The 3 inner preview surfaces mimic Meesho visual style via Tailwind utilities — they are static HTML, not separate child components (avoids nesting depth violation)
- Truncation warning uses `var(--mee-color-warning)` token for the alert color
- All interactive controls have `min-height: 44px`
- ZERO `primeng/...` imports

---

## 8. Out of Scope

| Item | Deferred to |
|---|---|
| Real GET /preview API call | Wave 6 API wiring |
| Image carousel swipe gesture | V1.5 |
| Full variant matrix preview | V1.5 |
| Side-by-side A/B title comparison | V1.5 |
| Real-time title character counter | V1.5 |

---

## 9. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| 1 BUILD | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| 2 ROUTE | Navigate to `/catalogs/test-id/preview` | PreviewComponent renders in shell |
| 3 LOADING | Observe 800 ms skeleton | Skeleton shows then transitions to 3 surfaces |
| 4 TESTS | `pnpm run test` | Min 4 tests pass (renders, titleTruncated computed, activeTab tab switch, loading false after sim) |
| 5 VISUAL | Review at 360px + 1280px | 360: tabs + single surface; 1280: all 3 surfaces side-by-side; truncation warning visible |

---

## 10. Paste-Ready Dispatch Block

```
════════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — F10 PREVIEW (/catalogs/:id/preview)
Agent: meesell-angular-component-builder
════════════════════════════════════════════════════════════════════

CONTEXT
───────
Waves 3+4 complete. This dispatch builds the Preview feature page (F10).
This is layout-heavy — 3 Meesho-style mock surfaces must be rendered
correctly at 360px (tab-switched) and 1280px (all 3 side-by-side).
Simulate GET /preview — no HttpClient wiring yet (Wave 6).

ROUTE: /catalogs/:id/preview (shell child)
COMPONENT: PreviewComponent (read-only — NO forms)

════════════════════════════════════════════════════════════════════

FILES TO CREATE
───────────────
  src/app/features/preview/preview/preview.component.ts
  src/app/features/preview/preview/preview.component.spec.ts
  src/app/features/preview/preview/preview.model.ts

════════════════════════════════════════════════════════════════════

UI KIT USAGE
────────────
  mee-card              → wrapper for each preview surface
  mee-skeleton          → loading state (variant="card") x3
  mee-badge             → tab chips (Feed / Detail / Mobile)
  mee-button            → "Edit product" CTA (secondary)
  mee-page-header       → page title + subtitle
  mee-loading-skeleton  → composite skeleton for 3-surface area

════════════════════════════════════════════════════════════════════

3 PREVIEW SURFACES (Feature 6 — V1_FEATURE_SPEC.md)
────────────────────────────────────────────────────
  Surface 1 — Feed thumbnail:
    160×200px image, title truncated at ~30 chars, price, rating mock
    Shows "Title cuts at char 30" warning badge above truncated text

  Surface 2 — Detail page:
    Full-width image, full title, price, commission%, GST%, category path
    Simulated "Add to cart" / "Buy now" buttons (non-interactive)

  Surface 3 — Mobile card:
    2-up grid style (two product tiles side-by-side), ~20 char title

  Title truncation warning panel (below surfaces):
    title = "Blue Cotton Kurti With Mirror Work" (35 chars)
    Truncated feed: "Blue Cotton Kurti With Mir…"
    Warning uses var(--mee-color-warning)

════════════════════════════════════════════════════════════════════

SIGNALS
───────
  loading = signal<boolean>(true)
  preview = signal<PreviewData | null>(null)
  activeTab = signal<'feed' | 'detail' | 'mobile'>('feed')
  titleTruncated = computed(() => title.length > 30)
  truncatedTitle = computed(() => title.slice(0, 30) + '…')

SIMULATION: setTimeout(800) → set preview to journey-step-8 data

════════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────
  • standalone + OnPush + signals + inject()
  • NO Reactive Forms
  • ZERO primeng/... imports
  • Design tokens only (no hex literals)
  • 44px touch targets on all interactive controls
  • 3 inner surfaces = static HTML in component template (not child components)
    to avoid nesting depth violation (max 3 levels)

════════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────
  Gate 1 BUILD:  pnpm run build → zero errors
  Gate 2 ROUTE:  /catalogs/:id/preview renders in shell
  Gate 3 LOAD:   800ms skeleton → 3 surfaces visible
  Gate 4 TESTS:  ≥4 tests pass
  Gate 5 VISUAL: 360px tabs work; 1280px 3-col layout

════════════════════════════════════════════════════════════════════
END DISPATCH
════════════════════════════════════════════════════════════════════
```
