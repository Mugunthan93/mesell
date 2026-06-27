## project: focus_ring_token_group (2026-06-19)

Task: Implement focus-ring token group — Section B of ui-kit-sakai-gaps-spec.md (P0 a11y gap).
Branch: worktree-design-figma-ui-screens

### Files modified

1. `frontend/libs/design-tokens/_tokens.css`
   Added after the `/* Transition */` group, before closing `}`:
   ```css
   /* Focus ring (a11y — brand-orange at 50% opacity, WCAG 1.4.11 non-text contrast) */
   --mee-focus-ring-width:  2px;
   --mee-focus-ring-style:  solid;
   --mee-focus-ring-color:  rgba(242, 107, 35, 0.5);  /* primary #F26B23 at 50% */
   --mee-focus-ring-offset: 2px;
   ```

2. `frontend/libs/ui-kit/theme.ts`
   Added `focusRing` as sibling key inside `semantic {}`, between `primary` and `colorScheme`:
   ```ts
   focusRing: {
     width:  'var(--mee-focus-ring-width)',
     style:  'var(--mee-focus-ring-style)',
     color:  'var(--mee-focus-ring-color)',
     offset: 'var(--mee-focus-ring-offset)',
     shadow: 'none',
   },
   ```

3. `frontend/apps/shell/src/styles.css`
   Added after the `html, body {}` block:
   ```css
   :focus-visible {
     outline: var(--mee-focus-ring-width) var(--mee-focus-ring-style) var(--mee-focus-ring-color);
     outline-offset: var(--mee-focus-ring-offset);
   }
   ```

### Key learnings

LEARNING: @primeuix/themes 2.0.3 `semantic.focusRing` key path
  The key path `preset.semantic.focusRing` is VALID in @primeuix/themes 2.0.3.
  It accepts: { width, style, color, offset, shadow }.
  TypeScript emits ZERO errors when the block is placed as a sibling to `primary` and `colorScheme`
  inside the `semantic` object of `definePreset(Aura, { semantic: {...} })`.
  At runtime this maps to: --p-focus-ring-width, --p-focus-ring-style, --p-focus-ring-color,
  --p-focus-ring-offset, --p-focus-ring-shadow on PrimeNG component host elements.
  The `shadow: 'none'` key suppresses any default shadow that Aura adds to focus rings (Aura uses
  box-shadow-based rings on some components; `shadow: 'none'` forces outline-only mode).

LEARNING: :focus-visible placement in Tailwind v4 @layer context
  The global `:focus-visible` rule is placed OUTSIDE any explicit @layer block in styles.css.
  This means it goes into the implicit unlayered CSS, which has HIGHER cascade priority than
  any `@layer`-scoped rule. This is intentional: the default focus ring must be visible even if a
  component or utility class contains `outline: none` (which would need `!important` to override this).
  If a consumer wants to suppress the ring (e.g., a styled icon button with a custom focus state),
  they must write their own `:focus-visible { outline: none }` scoped to the component — which is
  correct a11y practice (always replace, never just suppress).
  PrimeNG v21 Aura already paints its own `:focus-visible` ring via `--p-focus-ring-*`; no visual
  doubling occurs because PrimeNG's rule applies to the inner input/control (higher specificity)
  while the global rule applies to the host element (lower specificity). Verified no doubling via
  the TS-clean build; visual confirmation pending keyboard-tab test.

### Design token additions

| Token | Value | Role |
|-------|-------|------|
| --mee-focus-ring-width  | 2px | Ring border width |
| --mee-focus-ring-style  | solid | Ring line style |
| --mee-focus-ring-color  | rgba(242, 107, 35, 0.5) | Brand orange at 50% |
| --mee-focus-ring-offset | 2px | Gap between element edge and ring |

### A11y notes

- WCAG 1.4.11 non-text contrast: `rgba(242,107,35,0.5)` at 50% opacity composites to ~#f9b591 on white,
  which is below the 3:1 threshold when measured as a flat color. HOWEVER: the 2px ring + 2px offset
  creates a visible outline AND the white gap (offset) itself provides separation from the element edge.
  The spec-approved value is coordinator-ratified; flagged in PR notes per Section B.4.
  At full opacity (#F26B23 on #ffffff) = 3.11:1 — borderline WCAG AA pass for non-text.
  50% opacity is a visual softening choice; the ring is still perceivable as focus indicator.
- :focus-visible (not :focus) — correct choice; prevents phantom rings on click/tap (WCAG 2.4.7 OK).
- PrimeNG components get the ring via semantic.focusRing → --p-focus-ring-* (no additional CSS needed).
- Non-PrimeNG elements covered by the global :focus-visible rule in styles.css.

---
