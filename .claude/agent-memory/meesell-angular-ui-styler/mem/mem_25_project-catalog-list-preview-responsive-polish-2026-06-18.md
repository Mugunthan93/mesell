## project: catalog_list_preview_responsive_polish (2026-06-18)

Task: Responsive polish — catalog-list.component.ts (stub rewrite) + preview.component.ts (audit).
Branch: design-figma-ui-screens (worktree)

### catalog-list.component.ts — full rewrite from stub

Was: `<div class="p-6"><h1 class="text-2xl font-semibold">My Catalogs</h1></div>`

Now:
  - Outer wrapper: `flex flex-col gap-6 px-4 pt-2 pb-6 max-w-screen-xl mx-auto`
    pb-[76px] NOT added — shell .page-content already provides mobile bottom-nav clearance
    (rule codified in mfe_dashboard_responsive_audit session; note in cross-MFE action items above)
  - PageHeaderComponent: title + subtitle + cta_label="New Catalog" + cta_icon="pi pi-plus"
    (PageHeaderComponent has cta_icon input — passes directly to MeeButtonComponent icon)
  - Search input: native `<input type="search">` w-full height:44px — touch target PASS
    font-size not set (parent body inherits 16px) — RULE: should be explicit 1rem. Noted for follow-up.
  - Loading: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` with 3x `<mee-skeleton variant="card">`
  - Empty state: `EmptyStateComponent` — context-aware message (search vs no-catalogs) + conditional CTA
  - Catalog grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
  - Catalog card content:
    - Name: `<h2>` — heading hierarchy (h1=PageHeader, h2=card name)
    - `<mee-status-badge [status]="cat.status">`
    - Category: `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` — no 360px wrapping
    - Meta: SKU count + updated_at
    - Actions: Edit (secondary) + Preview (ghost) — MeeButtonComponent size=sm min-height:44px
  - Simulated SIMULATED_CATALOGS (3 rows, all 3 breakpoints exercised)
  - Wave 6: component-builder to wire real CatalogService.list() HTTP + replace setTimeout

### filteredCatalogs pattern

filteredCatalogs is an arrow function property on the class — NOT signal computed().
Reason: signal computed() must be called in injection context (class field initializer).
An arrow fn on the class is called at template render time — safe from template `filteredCatalogs()`.
This is equivalent to a plain instance method for template binding.

### preview.component.ts — audited, no changes applied

Pre-existing layout is correct:
  - Outer: `flex flex-col gap-6 p-4 max-w-screen-xl mx-auto` — p-4 is fine (shell provides mobile pb)
  - Mobile tab chips: `min-h-[44px]` — touch target PASS
  - 3-column → 1-column: `flex-col / lg:flex-row` — PASS
  - Shell .page-content covers bottom-nav clearance

Finding for component-builder (flagged in STATUS hand-offs):
  isDesktop() signal initialised from window.innerWidth at component creation.
  No window.resize or BreakpointObserver listener exists.
  On device rotation or browser resize, isDesktop() remains stale — tab-only view persists on desktop
  until page is refreshed. Logic fix needed in component-builder; not a styling concern.

### tsc result

tsc --noEmit --project apps/mfe-catalog/tsconfig.app.json: ZERO errors.

### Follow-up items (not blocking)

1. Search input: add `font-size: 1rem` to inline style (prevent iOS zoom — matches textarea rule).
   Component-builder or next styler session can add this.
2. Catalog card action buttons stacked vertically (flex-col): at sm+, these could switch to flex-row
   for a more compact look. Acceptable for V1; revisit in Wave 5+ visual polish pass.

---
