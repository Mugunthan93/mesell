## project: mfe_dashboard_responsive_audit (2026-06-18)

Task: Responsive polish audit for mfe-dashboard page (DashboardComponent + shared composites).
Branch: design-figma-ui-screens (worktree)
Files audited:
  - frontend/apps/mfe-dashboard/src/app/dashboard.component.ts (inline template)
  - frontend/apps/mfe-dashboard/src/app/landing.component.ts (inline template + styles)
  - frontend/libs/composites/stat-card/stat-card.component.ts
  - frontend/libs/composites/page-header/page-header.component.ts
  - frontend/libs/composites/empty-state/empty-state.component.ts
  - frontend/libs/composites/loading-skeleton/loading-skeleton.component.ts

Files edited:
  - frontend/apps/mfe-dashboard/src/app/dashboard.component.ts (2 cleanups)

### Audit results

| Checklist item | Result | Notes |
|---|---|---|
| Stat cards grid-cols-2 sm:grid-cols-4 | PASS | Present on line 64; mirrored in loading-skeleton stat-card case |
| Table overflow-x-auto wrapper | PASS | `overflow-x-auto rounded-xl` on table wrapper |
| Page header stacks on mobile | PASS | mee-page-header uses flex-col sm:flex-row |
| Empty state centred at 360px | PASS | items-center justify-center text-center in EmptyStateComponent |
| Bottom spacing for tab bar | PASS | Shell .page-content provides padding-bottom: calc(60px + safe-area) at ≤639px. MFE components do NOT need their own pb-[60px] — shell covers it. |
| Fixed pixel widths causing overflow | PASS | max-w-[200px] / max-w-[120px] are truncate helpers inside overflow-x-auto; no overflow |
| Font sizes ≥ 14px | PASS | All controls use text-sm = 14px |
| Touch targets ≥ 44px | PASS | <td> has min-h-[44px]; delete/pagination buttons have min-h-[44px] min-w-[44px]; inputs have min-h-[44px] |

### Fixes applied

1. Removed dead `focus-ring-color` from <input> inline style (not a valid CSS property).
   Was: `style="border-color:...; color:...; background:...; focus-ring-color: var(--mee-color-primary);"` 
   `focus-ring-color` is not a standard CSS property. The Tailwind `focus:ring-2` class handles the ring — no CSS property override needed.

2. Removed dead `min-height: 44px` from <tr> inline style.
   `min-height` on `<tr>` elements does NOT work in Chrome/Safari (table-row display ignores it).
   Actual 44px row height is correctly provided by `class="px-4 py-3 min-h-[44px]"` on the name `<td>`.
   Kept only `border-bottom: 1px solid var(--mee-color-outline)` which is the load-bearing part.

### KEY RULE: Shell padding-bottom covers all MFE pages at mobile

`shell.component.css` @media (max-width: 639px) sets:
  `.page-content { padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)); }`
This padding applies to the scroll container that hosts all MFE remote content.
Therefore: NO individual MFE page component needs its own `pb-[60px]` at mobile.
Adding it would double the bottom gap. Do not add redundant pb-[60px] to dashboard or other pages.

### RULE: min-height on <tr> is ineffective — use min-h-[44px] on <td> instead

`min-height: 44px` on a `<tr>` does not work in browsers (display: table-row ignores min-height).
To enforce 44px row height, add `min-h-[44px]` or `py-3` (which gives ~42px with text) to the `<td>` cells.
The leading content cell (name column) driving row height should carry the `min-h-[44px]` class.

tsc --noEmit: ZERO errors before and after edits.

---
