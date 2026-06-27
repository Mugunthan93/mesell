## Session 2026-06-06 — Shared UI Polish Dispatch {#shared-ui-polish-dispatch}

### Routes touched
Shared components only (no specific page route). Components usable across all 10 V1 routes.

### Pattern: StatusBadge via computed() style string
- Use a `computed()` signal that derives a full inline `style` attribute string from the status input.
- Bind via `[style]="badgeStyle()"` on the inner `<span>`.
- Advantage over `[class]`: no external SCSS needed; works with inline-style-only components.
- Status map as `Record<string, BadgeStyle>` with a DEFAULT_STYLE fallback for unknown statuses.
- Cast `status()` with `as string` when indexing a plain object map to avoid TS strict index error.

### Pattern: EmptyState — native <button> instead of MatButton
- When a component spec says "no MatButton import needed", use a native `<button>` with all styles inlined.
- Still set `min-height:44px; min-width:44px` for 44px touch target compliance (Tirupur mobile-first).
- Import MatIconModule only; no need for CommonModule or NgIf — use `@if` control flow.
- Remove `<ng-content />` from stub templates when replacing with a fully specified template.

### Pattern: LoadingSkeletonComponent — CSS @keyframes inline in styles[]
- Define `@keyframes shimmer { from ... to ... }` inside the component `styles: [...]` array.
- Apply via a CSS class `.shimmer-box` defined in the same `styles: []` block.
- Use `@switch/@case` Angular 18 control flow for variant dispatch.
- For table-row variant: `computed()` returns an array of `{index, width}` objects — `@for` iterates with `track row.index`.
- The `statBoxes = [0,1,2,3]` field is a plain array constant (not signal) — fine for static iteration inside `@for`.

### Pattern: FormFieldComponent — <ng-content /> pass-through
- `<ng-content />` passes child form controls through without wrapping logic.
- `@if` control flow replaces `*ngIf` — no CommonModule import needed.
- `role="alert"` on error div ensures screen reader announcement.
- The `required` input is `input<boolean>(false)` — a falsy default, no required validator logic in this component.

### Pattern: StatCardComponent — Material icon font via inline font-family
- Without importing MatIconModule, render Material icon names as text inside a `<span>` with `font-family:'Material Icons','Material Symbols Outlined',sans-serif`.
- This works only when the Material icon font CSS is loaded globally (it is via styles.scss / angular.json).
- If icon font is not available, the icon name renders as text fallback — acceptable for V1 stat cards.

### Pattern: PageHeaderComponent — MatIconModule for optional icon
- Import MatIconModule explicitly when using `<mat-icon>` in a template.
- Use `@if (ctaIcon())` inside the button to conditionally render the icon.
- `mat-icon` inline style: `font-size:18px; width:18px; height:18px; line-height:18px` to constrain size inside a button.

### Build notes (2026-06-06)
- ng build --configuration development: ZERO errors, 4.023s
- All 7 modified/created files compile cleanly under TypeScript strict mode

---
