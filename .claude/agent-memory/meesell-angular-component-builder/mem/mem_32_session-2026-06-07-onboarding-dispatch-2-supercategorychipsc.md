## Session 2026-06-07 — Onboarding Dispatch 2 — SuperCategoryChipsComponent {#onboarding-dispatch-2}

### Route touched
`/onboarding` — features/account/components/super-category-chips/

### Services consumed
None. Pure UI component — no API calls.

### Pattern: MatChipListboxChange event shape
- `MatChipListboxChange` imported from `@angular/material/chips` (same module as `MatChipsModule`).
- `event.value` is the ARRAY of currently selected chip values — NOT a single value.
- When all chips are deselected, `event.value` is `null` (not an empty array).
- Safe emit: `(event.value as string[]) ?? []` — null-coalesce always.
- MatChipListbox fires `(change)` event, NOT `(selectionChange)` (that is mat-selection-list).

### Pattern: mat-chip-option color="primary" with Spike design system overrides
- `color="primary"` resolves selected chip state to `var(--mat-sys-primary)` (MeeSell orange) via Spike/Material M3 theme in _theme.scss.
- Unselected state: add `class="bg-light-primary"` from _component-overrides.scss §17.
- `bg-light-primary` sets `background-color: var(--mee-color-primary-light)` = `rgba(242, 107, 35, 0.12)`.
- Both classes coexist without conflict — `color="primary"` owns selected state; `bg-light-primary` owns unselected light-tint.

### Pattern: matChipAvatar for icons inside mat-chip-option
- `<mat-icon matChipAvatar>icon_name</mat-icon>` — matChipAvatar constrains icon sizing inside the chip.
- `MatChipsModule` covers matChipAvatar; `MatIconModule` still needed separately for `<mat-icon>`.
- `class="text-mee-base"` on mat-icon sets font-size to 1rem via Tailwind token.

### Pattern: NG0303 aria-label on mat-chip-listbox in jsdom tests
- `[aria-label]="..."` property binding on `mat-chip-listbox` causes NG0303 warning in jsdom tests.
- At runtime this works correctly — Angular Material handles it as a native attribute pass-through.
- Warning is benign; all 4 tests pass despite it.
- To suppress warning: use interpolation `aria-label="{{ 'key' | transloco }}"` instead of property binding.

### Pattern: testing @Output() EventEmitter with vi.spyOn
- `vi.spyOn(component.selectionChange, 'emit')` spies on EventEmitter's `.emit` method directly.
- Trigger by calling `component.onSelectionChange(mockEvent)` (no DOM click needed).
- EventEmitter `.emit` is a plain method — vi.spyOn works correctly.

### Build result (2026-06-07 onboarding dispatch 2)
- ng build --configuration=production: ZERO errors
- onboarding-component chunk: 4.97 kB raw / 1.53 kB gzip (budget ≤80 kB gzip — PASS)
- 4/4 new tests passing

---
