# FE Contract Scanners — `frontend/tools/contracts/`

Five boundary-contract scanners for the MeeSell frontend design-system decoupling plan.
They mirror the backend `check_*.py` Gate-3 pattern (`BACKEND_ARCHITECTURE.md §16.E`)
and are dependency-free Node ESM (only `node:fs` + `node:path`).

---

## Contracts

| ID | File | Rule | Phase-0 status |
|----|------|------|---------------|
| **FE-1** | `fe1_no_primeng_outside_uikit.mjs` | No `primeng`/`@primeuix` ES import outside `libs/ui-kit/` | CLEAN (0 violations) |
| **FE-2** | `fe2_no_raw_pi_icons.mjs` | No raw `pi pi-*` class outside icon registry | WARN (3 known leaks) |
| **FE-3** | `fe3_chrome_shell_only.mjs` | MFEs must not import `ShellComponent` or chrome primitives | CLEAN (0 violations) |
| **FE-4** | `fe4_lib_dag.mjs` | Lib import DAG: `composites → layout → ui-kit` (no back-edges) | CLEAN (0 violations) |
| **FE-5** | `fe5_public_barrels_only.mjs` | Apps import `@mesell/*` public barrels only; no cross-MFE imports | CLEAN (0 violations) |

---

## How to run

All commands from `frontend/`:

```sh
# Run all 5 contracts (warn-only, always exits 0 in Phase 0):
node tools/contracts/run-all.mjs

# Run strict mode (exits 1 if any violation):
node tools/contracts/run-all.mjs --strict

# Run strict on specific contracts only (comma-list, no spaces):
node tools/contracts/run-all.mjs --strict=fe2,fe3

# Run a single scanner standalone (same output format as backend check_*.py):
node tools/contracts/fe1_no_primeng_outside_uikit.mjs
node tools/contracts/fe2_no_raw_pi_icons.mjs
# ... etc.
```

---

## Warn → Strict roadmap

| Phase | CI action | Contracts flipped |
|-------|-----------|------------------|
| **Phase 0** (now) | warn-only, non-blocking | none (all warn) |
| **Phase 1** | `--strict=fe2` after icon migration | FE-2 |
| **Phase 4** | `--strict=fe2,fe3` after chrome primitives land | FE-3 |
| **Phase 5** | `--strict` (all); job becomes a required status check (founder wires in branch protection, same as `frontend-boot-smoke` D1 gate) | FE-1, FE-4, FE-5 |

---

## Allow-list notes

### FE-2 — icon allow-list tightening (Phase 1)

**Phase 0:** the entire `libs/ui-kit/` tree is allowed (broad prefix). This covers
`mee-button`'s `MATERIAL_TO_PI` map and any other ui-kit internal `pi pi-*` usage.

**Phase 1 action:** narrow the constant `ALLOW_PREFIX_PHASE0` in `fe2_no_raw_pi_icons.mjs`
to exactly `libs/ui-kit/icon/icon.registry.ts`. After that single constant change,
`mee-button`'s map must also be migrated (or the button moved inside the registry file).

### FE-5 — lean-bundle deep imports (Phase 5)

The constant `PHASE0_ALLOWED_DEEP_PREFIXES` in `fe5_public_barrels_only.mjs` holds the
SP0 lean-bundle deep import set that PR #38 introduced:

```js
const PHASE0_ALLOWED_DEEP_PREFIXES = [
  '@mesell/ui-kit/',
  '@mesell/composites/',
  '@mesell/core/models',
];
```

**Phase 5 action (founder decision needed):**
- **Ratify:** keep these prefixes in the allow-list, wire `--strict` to ALL (they pass).
- **Refactor:** barrel-ize all deep imports first, then empty the allow-list, then wire strict.

The Phase-0 violation count (baseline) for FE-5 is recorded in the CI run for Phase 5's reference.

---

## File structure

```
tools/contracts/
├── _walk.mjs                          # shared recursive walker + utilities
├── run-all.mjs                        # orchestrator (run this from frontend/)
├── fe1_no_primeng_outside_uikit.mjs   # FE-1
├── fe2_no_raw_pi_icons.mjs            # FE-2
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
