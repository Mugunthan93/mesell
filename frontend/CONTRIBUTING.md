# Contributing — MeeSell Frontend

## UI Component Conventions

All **new or touched** MFE code must use the canonical design-system surface. Do not
import PrimeNG, `@primeuix`, or raw `pi pi-*` class strings from MFE files — the FE Gate
will block the PR if you do.

### Import rules

| Need | Use | Never |
|------|-----|-------|
| UI components | `MEE_FORM`, `MEE_OVERLAY`, `MEE_FEEDBACK`, `MEE_DATA`, `MEE_COMMON`, `MEE_FILE` from `@mesell/ui-kit` | `primeng/*` directly |
| Page layout | `MEE_LAYOUT` (or individual `MeePageComponent` etc.) from `@mesell/layout` | hand-rolled `<div class="px-4 py-6 …">` wrappers |
| Icons | `<mee-icon name="…">` or `mee-button [icon]="'…'"` with a `MeeIconName` | raw `<i class="pi pi-…">` |
| Providers | `provideMeeUi()` in `app.config.ts` | `providePrimeNG()` directly in MFEs |

Aggregator adoption rule: adopt a concern group (`...MEE_FORM`) when the MFE uses
**≥ half** its members; import individually otherwise. Angular's AOT compiler
tree-shakes unused standalone imports, but verify with a bundle-delta check (≤ +2 KB gzip).

Leave **bespoke layout elements raw** if a primitive can't reproduce them pixel-for-pixel —
that is contract-clean. Forcing a primitive to tick a box is worse than leaving the div.

### Reference exemplar

**PR #275** (`feat/ui-ds-phase6-dashboard` → develop) is the canonical exemplar:
`apps/mfe-dashboard/src/app/dashboard.component.ts` adopts `MeePageComponent` with
`padding="tight"` and `maxWidth="xl"` for a zero-visual-change migration. Refer to it
when migrating an existing MFE page.

### Swapping the theme or icon set

See `frontend/libs/ui-kit/SWAP_GUIDE.md` — both swaps are one-file changes.
