# FE Contract Scanners — `frontend/tools/contracts/`

Five boundary-contract scanners for the MeeSell frontend design-system decoupling plan.
They mirror the backend `check_*.py` Gate-3 pattern (`BACKEND_ARCHITECTURE.md §16.E`)
and are dependency-free Node ESM (only `node:fs` + `node:path`).

---

## Contracts

| ID | File | Rule | Status |
|----|------|------|--------|
| **FE-1** | `fe1_no_primeng_outside_uikit.mjs` | No `primeng`/`@primeuix` ES import outside `libs/ui-kit/` | **STRICT (Phase 5)** — CI exits 1 on violation |
| **FE-2** | `fe2_no_raw_pi_icons.mjs` | No raw icon class string outside `libs/ui-kit/icon/icon.registry.ts` | **STRICT (Phase 1)** — CI exits 1 on violation |
| **FE-3** | `fe3_chrome_shell_only.mjs` | MFEs must not import `ShellComponent` or chrome primitives | **STRICT (Phase 4)** — CI exits 1 on violation |
| **FE-4** | `fe4_lib_dag.mjs` | Lib import DAG: `composites → layout → ui-kit` (no back-edges) | **STRICT (Phase 5)** — CI exits 1 on violation |
| **FE-5** | `fe5_public_barrels_only.mjs` | Apps import `@mesell/*` public barrels only; no cross-MFE imports | **STRICT (Phase 5)** — CI exits 1 on violation |

> **Phase 5 — SEALED.** All 5 contracts are now strict (`--strict`, all). The
> **FE Gate** (`FE Gate: lint (5 contracts)`) is a **required status check on
> `develop`** (wired in branch protection) — a red gate blocks merge. The FE-5
> deep-import allow-list (`PHASE0_ALLOWED_DEEP_PREFIXES`) is **emptied** (0 deep
> imports exist; apps import barrel roots only). The icon/theme swap-proof
> demonstration (prove a one-file PrimeNG→other swap with these seals holding) is
> **Phase 7**, not here.

---

## How to run

All commands from `frontend/`:

```sh
# Run all 5 contracts (FE-2 strict, others warn-only):
node tools/contracts/run-all.mjs --strict=fe2

# Run all strict (exits 1 if ANY violation — Phase 5):
node tools/contracts/run-all.mjs --strict

# Run strict on specific contracts only (comma-list, no spaces):
node tools/contracts/run-all.mjs --strict=fe2,fe3

# Run warn-only (always exits 0):
node tools/contracts/run-all.mjs

# Run a single scanner standalone (same output format as backend check_*.py):
node tools/contracts/fe1_no_primeng_outside_uikit.mjs
node tools/contracts/fe2_no_raw_pi_icons.mjs
# ... etc.
```

---

## Warn → Strict roadmap

| Phase | CI action | Contracts flipped |
|-------|-----------|------------------|
| **Phase 0** (complete) | warn-only, non-blocking | none (all warn) |
| **Phase 1** (complete) | `--strict=fe2` — icon migration complete; `mee-icon` + registry shipped | **FE-2 strict** |
| **Phase 4** (complete) | `--strict=fe2,fe3` after chrome primitives land | FE-3 |
| **Phase 5** (current — SEALED) | `--strict` (all); FE Gate becomes a **required status check** on `develop` (founder wires in branch protection, same as `frontend-boot-smoke` D1 gate); FE-5 allow-list emptied | FE-1, FE-4, FE-5 |

---

## Allow-list notes

### FE-2 — icon allow-list (Phase 1 — ACTIVE)

**Phase 0:** the entire `libs/ui-kit/` tree was allowed (broad prefix). This covered
`mee-button`'s `MATERIAL_TO_PI` map and any other ui-kit internal icon class usage.

**Phase 1 (current):** allow-list narrowed to **exactly** `libs/ui-kit/icon/icon.registry.ts`.
This is the ONLY file permitted to contain raw icon class strings. All other files use
`MeeIconName` semantic keys (`dashboard`, `user`, `sparkles`, etc.) resolved via
`resolveIcon()` or `MEE_ICONS[name]`.

What was migrated in Phase 1:
- `mee-button/button.component.ts` — removed `MATERIAL_TO_PI` map; `icon` input retyped to `MeeIconName`
- `confirm-dialog/confirm-dialog.component.ts` — `ConfirmationService.confirm({ icon })` now uses `MEE_ICONS['warning']`
- `menu/menu.types.ts` — `MeeMenuItem.icon` retyped to `MeeIconName | undefined`
- `menu/menu.component.ts` — `primeItems()` resolves `item.icon` through `MEE_ICONS[item.icon]`
- `apps/shell/.../shell.component.ts` — nav group icons and user menu items now use `MeeIconName`
- `apps/shell/.../shell.component.html` — hamburger + nav item icons use `<mee-icon>`
- `apps/mfe-catalog/.../smart-picker.component.ts` — `icon="send"` (was `icon="pi pi-send"`)
- `button.component.spec.ts` + `menu.component.spec.ts` — spec fixtures use `MeeIconName` keys

### FE-5 — deep-import allow-list (Phase 5 — EMPTIED)

The constant `PHASE0_ALLOWED_DEEP_PREFIXES` in `fe5_public_barrels_only.mjs` was a
vestigial seed for the SP0 lean-bundle deep-import pattern anticipated in PR #38.
That pattern was **never committed** — 0 deep `@mesell/<lib>/<subpath>` imports exist
in `apps/**`, so the allow-list guarded nothing.

**Phase 5: emptied.** The seal is now final — apps import `@mesell/*` barrel ROOTS
only (no deep subpath, no cross-MFE):

```js
const PHASE0_ALLOWED_DEEP_PREFIXES = [];
```

With `--strict` (all 5) active, ANY deep `@mesell/<lib>/<subpath>` import in `apps/**`
now fails the FE Gate. Baseline today: FE-5 = 0 violations.

---

## File structure

```
tools/contracts/
├── _walk.mjs                          # shared recursive walker + utilities
├── run-all.mjs                        # orchestrator (run this from frontend/)
├── fe1_no_primeng_outside_uikit.mjs   # FE-1
├── fe2_no_raw_pi_icons.mjs            # FE-2 (strict Phase 1)
├── fe3_chrome_shell_only.mjs          # FE-3
├── fe4_lib_dag.mjs                    # FE-4
├── fe5_public_barrels_only.mjs        # FE-5
└── README.md                          # this file
```

---

## DAG reference (FE-4)

```
rank 0 (base)  @mesell/ui-kit        atoms — PrimeNG wrappers
rank 0 (base)  @mesell/core          interceptors, guards, services, models
rank 0 (base)  @mesell/design-tokens CSS custom-property definitions
rank 0 (base)  @mesell/env           env-aware config
rank 1         @mesell/layout        page primitives + chrome (Phase 3/4)
rank 2         @mesell/composites    cross-lib composed patterns
```

A lib at rank R may only import libs with rank < R. Back-edges (rank >= R) are flagged.
