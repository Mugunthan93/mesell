## project: export_page_responsive_polish (2026-06-18)

Task: Responsive polish audit for mfe-export ExportComponent.
Branch: design-figma-ui-screens (worktree)
File changed: frontend/apps/mfe-export/src/app/export.component.ts (template only — 2 changes)

### Component structure discovered

ExportComponent is a validation-gate + status-state-machine design (NOT a format-picker).
- LEFT column (lg:w-2/5): pre-export checklist table (4 rows) + Generate button
- RIGHT column (lg:w-3/5): conditional status cards (idle / processing+progress / ready+download / failed+retry)
- Both columns are flex-col on mobile (lg:flex-row only at >=1024px)
- No CSV/ZIP format cards, no summary stats, no export history list in V1

### Audit results

| Checklist item | Result | Action |
|---|---|---|
| Format cards single-col | N/A — no format cards in this component | None |
| Progress bar full-width | PASS | None |
| Download button full-width + 44px | PASS — [fullWidth] + minHeight:44px from ui-kit | None |
| Catalog summary wraps at 360px | N/A — no summary section | None |
| Export history list | N/A — no history in V1 | None |
| Bottom spacing pb-[60px] | NOT NEEDED — shell covers it | No per-MFE padding |
| Fixed widths causing scroll | PASS | None |
| min-w-0 on flex columns | MISSING | FIXED |
| Table column width anchoring | MISSING | FIXED |

### Fixes applied (2 changes)

FIX 1: min-w-0 on flex column children
  Before: class="lg:w-2/5 space-y-4" / class="lg:w-3/5 space-y-4"
  After:  class="min-w-0 lg:w-2/5 space-y-4" / class="min-w-0 lg:w-3/5 space-y-4"
  RULE: flex children with fractional widths ALWAYS need min-w-0.

FIX 2: Checklist table column anchoring
  Label <th>/<td>: added w-full
  Result <th>/<td>: added w-px whitespace-nowrap pl-3
  At 360px (~280px usable), w-full on label absorbs space; w-px on result keeps badge at minimum width.
  RULE: 2-column label+status tables: w-full on label, w-px whitespace-nowrap pl-3 on status column.

### CRITICAL RULE RE-CONFIRMED: Shell padding-bottom covers all MFE pages at mobile

shell.component.css @media (max-width: 639px):
  .page-content { padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)); }

DO NOT add pb-[60px] to individual MFE page wrappers — creates double gap (120px dead space).
First established in dashboard audit; confirmed again here for export.
Apply this rule consistently to ALL remaining MFE responsive audits.

### tsc result
tsc --noEmit --project apps/mfe-export/tsconfig.app.json: ZERO errors.

---
