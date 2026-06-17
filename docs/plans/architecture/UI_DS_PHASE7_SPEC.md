# UI Design-System Decoupling — Phase 7 BUILD SPEC (Swap-Proof Closer)

**Status:** BUILT (branch `feat/ui-ds-phase7`)
**Date:** 2026-06-17
**Author:** `meesell-frontend-coordinator` (HYBRID dispatch SPEC)
**Specialist:** `meesell-angular-component-builder`
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §4 Phase 7 "Swap-proof"
**Preconditions (all MERGED to develop):**
- P0 `#259` — icon seal (FE-2 strict)
- P1 `#260` — aggregators (FE-2 strict)
- P2 `#265` — `@mesell/layout` page primitives + `MEE_LAYOUT`
- P3 `#267` — chrome primitives + thin-host shell + FE-3 strict
- P4 (Phase 5) — all 5 FE contracts strict + gate required
- P5 (Phase 6a) `#273` — `mee-page` padding scale
- P6 (Phase 6 dashboard) `#275` — dashboard MFE `mee-page` adoption pilot

**Phase 7 mandate (verbatim from parent §4):** "Prove the DoD: swapping theme or icon set is a
one-file change. Add alt theme + alt icon registry + selector indirection. Add vitest swap spec.
Write SWAP_GUIDE.md. The live defaults MUST NOT change."

---

## 0. Locked Decisions

| ID | Decision |
|---|---|
| D7-1 | Alt theme (`MeeSellAltPreset`) is a fully independent file — does NOT import from `theme.ts`. |
| D7-2 | Alt icon registry (`MEE_ICONS_ALT`) must contain zero `pi pi-*` strings (FE-2 contract). |
| D7-3 | `icon.selector.ts` is the ONLY file that selects the active icon set — `ActiveIcons` is the public export. |
| D7-4 | `MeeIconComponent` reads `ActiveIcons` (not `MEE_ICONS` directly) — behavior-preserving because `ActiveIcons === MEE_ICONS` by default. |
| D7-5 | `providers.ts` is unchanged — theme swap is documented but NOT activated (live default stays orange). |
| D7-6 | The existing `icon.component.spec.ts` is NOT modified — back-compat of the component spec is a merge gate criterion. |
| D7-7 | `icon.swap.spec.ts` uses vitest (no Angular TestBed) — same import pattern as `aggregators.spec.ts`. |

---

## 1. File-by-File Change List

| # | Path | Action | Key constraint |
|---|---|---|---|
| F1 | `frontend/libs/ui-kit/theme.alt.ts` | NEW — `MeeSellAltPreset` (green `#2E7D32`) | Must NOT import from `theme.ts` |
| F2 | `frontend/libs/ui-kit/icon/icon.registry.alt.ts` | NEW — `MEE_ICONS_ALT` (Material Icons strings) | Zero `pi pi-*` strings; `satisfies Record<MeeIconName, string>` |
| F3 | `frontend/libs/ui-kit/icon/icon.selector.ts` | NEW — `export const ActiveIcons = MEE_ICONS` | The single swap point; no other logic |
| F4 | `frontend/libs/ui-kit/icon/icon.component.ts` | EDIT — import `ActiveIcons` from `./icon.selector`; keep `MeeIconName` as type-only import from `./icon.registry` | Behavior-preserving; no template change |
| F5 | `frontend/libs/ui-kit/icon/icon.swap.spec.ts` | NEW — vitest swap assertions (see §2) | No TestBed; pure module import tests |
| F6 | `frontend/libs/ui-kit/SWAP_GUIDE.md` | NEW — one-page swap procedure | Documents both seams + verification steps |

Additionally, `frontend/libs/ui-kit/index.ts` receives additive barrel exports for the three new public symbols (see §3).

The coordinator SPEC file (`docs/plans/architecture/UI_DS_PHASE7_SPEC.md`) is produced alongside
the build files — not counted in the 6 deliverables above.

---

## 2. Test Plan (`icon.swap.spec.ts`)

Six assertion groups, all pure module-level (no DOM, no Angular Zone):

| # | Assertion | Rationale |
|---|---|---|
| S1 | `MeeSellAltPreset !== MeeSellPreset` | Module independence — two `definePreset()` calls produce distinct objects |
| S2 | `ActiveIcons === MEE_ICONS` | Default state unchanged — selector points at primary registry |
| S3 | `Object.keys(MEE_ICONS_ALT).sort()` deep-equals `Object.keys(MEE_ICONS).sort()` | Key parity — alt set covers every semantic name; no regressions if a key is added to primary |
| S4 | Every `MEE_ICONS_ALT` value is a non-empty string containing `'material-icons'` | Structural validity of the alt map |
| S5 | No `MEE_ICONS_ALT` value matches `/pi\s+pi-[a-z]/` | FE-2 contract — alt registry is clean |
| S6 | Every `MeeIconName` resolves to a defined non-empty string in `MEE_ICONS_ALT` | Full coverage — no missing key at runtime if selector is flipped |

---

## 3. Barrel Additions (`index.ts`)

Three additive exports appended to the end of `libs/ui-kit/index.ts` (no existing exports changed):

```ts
export { MeeSellAltPreset } from './theme.alt';
export { MEE_ICONS_ALT }    from './icon/icon.registry.alt';
export { ActiveIcons }      from './icon/icon.selector';
```

These allow consumers to import swap artifacts from `@mesell/ui-kit` without reaching into
sub-paths (FE-5 contract: barrel-only imports from libs).

---

## 4. Merge-Gate Criteria (12 checks)

| # | Check | Owner |
|---|---|---|
| G1 | `icon.component.spec.ts` passes unchanged (pre-existing spec — back-compat) | Specialist |
| G2 | `icon.swap.spec.ts` all assertions pass (S1–S6) | Specialist |
| G3 | `aggregators.spec.ts` passes unchanged (no aggregator count change) | Specialist |
| G4 | `node tools/contracts/run-all.mjs` → all 5 CLEAN (0 violations) | Specialist |
| G5 | `node tools/contracts/run-all.mjs --strict` exits 0 | Specialist |
| G6 | FE-2 scanner does NOT flag `icon.registry.alt.ts` or `icon.swap.spec.ts` | Specialist |
| G7 | `ng build mfe-dashboard` passes with 0 errors (or `ng build shell` if unavailable) | Specialist |
| G8 | `icon.component.ts` references `ActiveIcons`, NOT `MEE_ICONS` (value import) | Coordinator review |
| G9 | `theme.alt.ts` does NOT import from `theme.ts` | Coordinator review |
| G10 | `providers.ts` is UNCHANGED — live orange default preserved | Coordinator review |
| G11 | `icon.selector.ts` contains only the `ActiveIcons` export (no other logic) | Coordinator review |
| G12 | `index.ts` additions are purely additive (no existing export line changed) | Coordinator review |

---

## 5. What Stays Unchanged

- Live production behavior: `provideMeeUi()` still uses `MeeSellPreset` (orange)
- `MeeIconComponent` behavior: `resolved()` still returns `MEE_ICONS[name]` (via `ActiveIcons`)
- All MFEs: zero changes in any `apps/mfe-*/` directory
- All FE contracts: scanners untouched, all 5 still strict
- `theme.ts`, `icon.registry.ts`: primary files are read-only for this phase
- `icon.component.spec.ts`: pre-existing spec is never modified
