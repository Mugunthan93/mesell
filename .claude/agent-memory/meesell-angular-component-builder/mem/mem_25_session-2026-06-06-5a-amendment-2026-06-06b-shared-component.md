## Session 2026-06-06 — §5A AMENDMENT 2026-06-06B Shared Component Lock {#5a-lock-batch1}

### Route touched
Shared components only (no page route). Components used across all 10 V1 routes.

### Pattern: §5A hex prohibition — three valid alternatives
1. `var(--mee-color-*)` CSS custom properties — for semantic design tokens (primary, surface, on-surface, error)
2. Tailwind semantic alias classes (`text-on-surface`, `bg-surface-variant`) — wired in tailwind.config.js to CSS vars
3. Tailwind palette classes (`bg-green-100`, `text-green-700`, `border-green-200`) — for non-semantic status tints where no design token exists
4. `mat-flat-button color="primary"` — Material themed button; background resolved automatically to `var(--mee-color-primary)` via _component-overrides.scss without any manual color

### Pattern: Tailwind [class] binding in Angular 18 merges with static class=
- `class="base-classes..."` + `[class]="dynamicClasses()"` — both apply simultaneously in Angular 18.
- Replaces the `[style]` binding pattern used in the old StatusBadge inline-style approach.
- STATUS_CLASSES is a plain `Record<string, string>` — no interface needed; values are Tailwind class strings.
- Default fallback: `const DEFAULT_CLASSES = 'bg-gray-100 text-gray-500 border-gray-200'` constant keeps the computed clean.

### Pattern: output<void>() vs @Output() EventEmitter
- Prefer `output<void>()` (Angular 18 function API) over `@Output() readonly foo = new EventEmitter<void>()`.
- Import: `output` from `@angular/core` — remove `EventEmitter` and `Output` from the import.
- Emit syntax identical: `this.ctaClick.emit()` works for both.

### Pattern: mat-icon 48px sizing without a design token
- `font-size:48px; width:48px; height:48px;` kept as inline style on `<mat-icon>` — 48px is a one-off size, not a semantic design token, no Tailwind class for this.
- Color removed from inline style; moved to `class="text-on-surface-variant"`.

### Pattern: mat-flat-button touch target
- `class="min-h-[44px]"` on `<button mat-flat-button>` for 44px touch target compliance.
- Do NOT set background via inline style — `color="primary"` handles it via Material theming.

### Build notes
- ng build --configuration development: ZERO errors, 5.493s
- Spec files NOT updated — @analogjs not yet installed; spec infra pass is a separate dispatch.

---
