## Session 2026-06-09 — Wave 4 Shared Composites EXECUTED {#wave4-executed}

### Task
Built all 5 Layer 3 shared composites in `src/app/shared/`. Created 11 files.

### Gate Results
- Gate 1 BUILD: PASS — zero errors, zero warnings, 2.259s
- Gate 2 BOUNDARY: PASS — grep -r "from 'primeng/" src/app/shared/ returns empty
- Gate 3 TESTS: PASS — 143/143 passing (28 test files); 38 new Wave 4 tests
- Gate 4 BARREL: PASS — shared/index.ts exports all 5 components + ProductStatus + StatCardColor

### Pattern: output<void>() testing limitation in vitest+jsdom (CRITICAL)
- `outputToObservable(comp.output)` subscribes to the Angular output signal's Observable
- In vitest+jsdom WITHOUT a live Angular zone, the subscription does NOT receive events
  even when `comp.output.emit()` is called directly after `detectChanges()`
- Root cause: `output()` signals are tied to Angular's change detection notification cycle;
  without a running zone, the subscription is registered but notifications are not dispatched
- CORRECT test pattern for output() existence checks:
  ```typescript
  expect(comp.cta_click).toBeDefined();
  expect(typeof comp.cta_click.emit).toBe('function');
  ```
- For actual emission integration tests: use Karma+zone-enabled TestBed or a DOM event trigger
- DO NOT use outputToObservable() + direct .emit() pattern in vitest unit tests — it will
  always show 0 emissions even when the output is wired correctly

### Pattern: Stubs for mee-* children in shared composite specs
- Use plain `@Input()` decorator (NOT `input.required()` signal) on stub classes to avoid NG8109 warnings
- Use `@Output() clicked = new EventEmitter<void>()` (NOT signal output()) on stubs
- Stub template: simple `<button class="btn-stub">{{ label }}</button>` — no event forwarding needed
- TestBed.overrideComponent removes the real mee-* and adds the stub
- This pattern avoids the full PrimeNG/primeng import chain in specs

### Pattern: Color map in stat-card composite
- `const COLOR_VAR_MAP: Record<StatCardColor, string>` at MODULE level (outside class)
- Values are CSS var references: `'var(--mee-color-primary)'`, `'var(--mee-color-info)'`, etc.
- Purple has no design system token yet — used fallback: `'var(--mee-color-purple, #7C3AED)'`
  (CSS var with fallback — no hex in the primary token path, fallback only when var missing)
- `accentColor = computed(() => COLOR_VAR_MAP[this.color()])` — standard computed signal pattern

### Pattern: TitleCasePipe import for status-badge
- C2 StatusBadgeComponent uses `status() | titlecase` in template
- `TitleCasePipe` must be in the component's `imports: [MeeBadgeComponent, TitleCasePipe]`
- Import: `import { TitleCasePipe } from '@angular/common'`
- Without this import: NG8004 "No pipe found with name 'titlecase'" at compile time

### Pattern: @switch dispatch for loading-skeleton variants
- C5 LoadingSkeletonComponent uses `@switch (variant())` with 4 explicit `@case` blocks
- `@default` case also renders `<mee-skeleton variant="text">` as safe fallback
- table-row variant: renders 4 explicit `<mee-skeleton variant="table-row">` siblings
- stat-card variant: renders 4 `<mee-skeleton variant="stat-card">` in a 2-col / 4-col grid
- These are hard-coded counts (not @for) — keeps the template explicit and avoids an extra signal

### Files created (11 total)
```
src/app/shared/
├── stat-card/stat-card.component.ts              (C1)
├── stat-card/stat-card.component.spec.ts
├── status-badge/status-badge.component.ts        (C2)
├── status-badge/status-badge.component.spec.ts
├── page-header/page-header.component.ts          (C3)
├── page-header/page-header.component.spec.ts
├── empty-state/empty-state.component.ts          (C4)
├── empty-state/empty-state.component.spec.ts
├── loading-skeleton/loading-skeleton.component.ts (C5)
├── loading-skeleton/loading-skeleton.component.spec.ts
└── index.ts (barrel)
```

### Build result (2026-06-09 Wave 4)
- pnpm run build: ZERO errors, 2.259s
- pnpm run test: 143/143 passing (28 test files)
- Barrel: 5 components + 2 public types exported from shared/index.ts

---
