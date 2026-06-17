# MeeSell UI Kit — Swap Guide

This guide documents the two one-file swaps that the UI Design-System Decoupling workstream (Phase 7)
makes possible. All changes are isolated to the seam files — no MFE, no app code, no FE contract
edits are ever needed.

---

## Theme Swap (orange → green or any future brand)

**File to edit:** `frontend/libs/ui-kit/providers.ts`

**Current (orange default):**
```ts
import { MeeSellPreset } from './theme';

// inside provideMeeUi():
providePrimeNG({ theme: { preset: MeeSellPreset, ... } })
```

**After swap (alt green):**
```ts
import { MeeSellAltPreset } from './theme.alt';

// inside provideMeeUi():
providePrimeNG({ theme: { preset: MeeSellAltPreset, ... } })
```

That is a single `import` line change and a single `preset:` value change — two lines total in one
file. No MFE needs to be rebuilt, because every MFE inherits the theme via the shell's
`provideMeeUi()` call at bootstrap. The individual `apps/mfe-*/src/main.ts` files do not import
the preset directly.

---

## Icon Swap (PrimeIcons → Material Icons or any future icon set)

**File to edit:** `frontend/libs/ui-kit/icon/icon.selector.ts`

**Current (PrimeIcons default):**
```ts
import { MEE_ICONS } from './icon.registry';
// import { MEE_ICONS_ALT } from './icon.registry.alt';  // ← uncomment to swap

export const ActiveIcons = MEE_ICONS;
```

**After swap (Material Icons):**
```ts
// import { MEE_ICONS } from './icon.registry';
import { MEE_ICONS_ALT } from './icon.registry.alt';  // ← uncommented

export const ActiveIcons = MEE_ICONS_ALT;
```

`MeeIconComponent` reads from `ActiveIcons` — so every `<mee-icon name="dashboard" />` in every
MFE automatically resolves through the new registry. No MFE template, no shell nav item, no
button component needs to change.

---

## What NOT to Change

| File | Why it must not change |
|---|---|
| `theme.ts` | The primary orange preset. Leave it untouched so the swap is reversible with a one-line diff. |
| `icon.registry.ts` | The only file allowed to contain raw `pi pi-*` strings (FE-2 contract). Altering it changes the primary icon set, not the swap seam. |
| Any MFE (`apps/mfe-*/`) | MFEs consume `ActiveIcons` and the theme indirectly through `mee-icon` and `provideMeeUi()`. They have zero direct icon-set or preset awareness. |
| `providers.ts` (for icon swap) | Theme and icon are independent seams. Icon swap touches only `icon.selector.ts`. |
| `icon.selector.ts` (for theme swap) | Icon and theme are independent seams. Theme swap touches only `providers.ts`. |

---

## Adding a Third Icon Set

1. Create `icon/icon.registry.<name>.ts` — must `satisfies Record<MeeIconName, string>`.
2. Verify zero `pi pi-` strings in the new file (`node tools/contracts/run-all.mjs`).
3. In `icon.selector.ts`: import the new registry, assign to `ActiveIcons`.
4. No other file changes.

---

## Verification After a Swap

After making either change, run:

```bash
# 1. Check FE contracts (icon.registry.alt.ts must stay FE-2 clean)
cd frontend && node tools/contracts/run-all.mjs

# 2. Build any MFE to confirm no TypeScript errors
cd frontend && ng build mfe-dashboard

# 3. Run the swap spec (vitest)
cd frontend && npx vitest run libs/ui-kit/icon/icon.swap.spec.ts
```

All 5 FE contracts must remain CLEAN. `ng build` must pass with 0 errors. The swap spec must
pass all assertions.

---

## Reference Files

| Purpose | File |
|---|---|
| Primary theme (orange) | `libs/ui-kit/theme.ts` — `MeeSellPreset` |
| Alt theme (green) | `libs/ui-kit/theme.alt.ts` — `MeeSellAltPreset` |
| Primary icon registry (PrimeIcons) | `libs/ui-kit/icon/icon.registry.ts` — `MEE_ICONS` |
| Alt icon registry (Material Icons) | `libs/ui-kit/icon/icon.registry.alt.ts` — `MEE_ICONS_ALT` |
| Icon swap point | `libs/ui-kit/icon/icon.selector.ts` — `ActiveIcons` |
| Theme swap point | `libs/ui-kit/providers.ts` — `provideMeeUi()` |
| Swap spec | `libs/ui-kit/icon/icon.swap.spec.ts` |
