## project: smart_picker_mobile_audit (2026-06-18)

Task: Responsive polish audit of SmartPickerComponent (/catalogs/new) — mobile-first for Tirupur sellers (360–390px Android).
Branch: design-figma-ui-screens (worktree)

Files read (all audited, only one modified):
  - frontend/apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts (inline template)
  - frontend/apps/mfe-catalog/src/app/smart-picker/category-card.component.ts (inline template + styles)
  - frontend/libs/ui-kit/textarea/textarea.component.ts (MODIFIED — font-size hardened)
  - frontend/libs/ui-kit/button/button.component.ts
  - frontend/libs/ui-kit/card/card.component.ts
  - frontend/libs/ui-kit/progress-bar/progress-bar.component.ts
  - frontend/libs/composites/page-header/page-header.component.ts
  - frontend/libs/composites/empty-state/empty-state.component.ts
  - frontend/libs/design-tokens/_tokens.css
  - frontend/apps/shell/src/styles.css

### Audit results (all 7 checklist items)

| Check | Result |
|-------|--------|
| Search textarea min-height | min-height: 44px — PASS |
| Search textarea font-size | Fixed: now explicit 1rem (16px). Was implicit browser default — same value but now load-bearing. |
| Category card touch target | grid-cols-1 on mobile + mee-button min-height:44px — PASS |
| "Browse if none match" button | min-h-[44px] Tailwind class; Tailwind scanned via @source "../.." in shell styles.css — PASS |
| Selected category display | N/A — picker routes away on pick |
| Overflow/scroll | Document flow; no viewport overflow — PASS |
| Step bar | Smart picker has NO step bar (separate route from catalog-form) — N/A |
| Fixed pixel widths | None found — PASS |

### Fix applied

frontend/libs/ui-kit/textarea/textarea.component.ts:
  Changed: style="min-height: 44px;"
  To:      style="min-height: 44px; font-size: 1rem;"

Rationale: PrimeNG Aura textarea has no explicit font-size token at the default size variant.
Font-size inherits from HTML root (browser default 16px). Relying on this implicit chain was fragile —
if any future body { font-size } override is added to styles.css, all textareas would suddenly zoom
on iOS. Explicit 1rem locks the 16px floor regardless of cascade.

RULE: Always set font-size: 1rem (minimum 16px) on <input> and <textarea> elements explicitly.
Do NOT rely on PrimeNG or browser defaults for this — it is a mobile safety invariant.

### Component architecture notes

SmartPickerComponent (/catalogs/new) is a SEPARATE route from CatalogFormComponent (/catalogs/:id/edit).
The wizard step bar (mee-steps / p-steps) is in catalog-form only — NOT in smart picker.
Smart picker → category card → routes to /catalogs/:id/edit on pick. No inline step progress needed.

The mee-catalog @source is covered by shell styles.css "@source '../..'".
Shell styles.css is the single Tailwind build; all mfe-* remotes' classes are scanned by it.
Design tokens are imported into shell styles.css; all remotes inherit them at runtime.

### tsc result
tsc --noEmit --project apps/mfe-catalog/tsconfig.app.json: ZERO errors (before and after fix).

---
