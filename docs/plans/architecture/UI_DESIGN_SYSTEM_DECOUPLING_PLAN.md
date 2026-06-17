# UI Design-System Decoupling Plan

**Status:** Planning (decisions locked, implementation not started)
**Date:** 2026-06-16
**Owner:** Founder + `meesell-frontend-coordinator` (execution)
**Scope:** `frontend/` — `@mesell/ui-kit`, new `@mesell/layout`, `@mesell/composites`, `apps/shell`, all MFEs

---

## 1. Goal (plan statement)

Consolidate MeeSell's UI into a **three-tier, dependency-ordered design system**
(`ui-kit → layout → composites`) that is the *sole* UI surface every micro-frontend
imports — exposing MeeSell-named components, layout (page + chrome), icons, and grouped
aggregators with a stable MeeSell API — so that **PrimeNG, Sakai patterns, and PrimeIcons
are an internal, swappable implementation detail** with zero references in any MFE or app.

**Definition of done:**
- A grep for `primeng`, `@primeuix`, or `pi pi-` returns matches **only** inside the
  design-system libraries (and `pi pi-` only inside one icon-registry file).
- Every MFE builds importing only `@mesell/*` public barrels.
- Swapping the theme **or** the icon set is a **one-file change**.
- The frontend boundary-contract CI gate is green and **blocking**.

---

## 2. Why this plan (current state — measured, not assumed)

| Layer | State today | Evidence |
|-------|-------------|----------|
| Component decoupling | ✅ Done | **0** `primeng`/`@primeuix` imports outside `@mesell/ui-kit` (20 wrappers + 2 services + theme + providers all sealed). |
| Adoption | ✅ Wide | 25 MFE files import `@mesell/ui-kit`; 19 import `@mesell/composites`. |
| Theme seal | ✅ Done | `MeeSellPreset` (Aura) + `providePrimeNG` live only in `ui-kit/providers.ts`. |
| Icons | ❌ Leak | Raw `pi pi-*` in 3 files (shell ×2, smart-picker); `mee-button` has an ad-hoc `MATERIAL_TO_PI` map. No `mee-icon`. |
| Layout | ⚠️ Not reusable | App-shell chrome is a hand-rolled monolith in `apps/shell/.../layouts/shell/`; no reusable page/chrome primitives. |
| Pipes / directives | ❌ None | No `*.pipe.ts` / `*.directive.ts` in any lib. |
| Enforcement (FE) | ❌ None | No eslint config, no FE boundary contracts. (Backend has 10 blocking contracts — §16.E.) |

**Reframe:** this is **not** a greenfield "build a reusable module" task — ~70% exists
(`@mesell/ui-kit` already decouples PrimeNG at the component level). This plan **completes
the edges** (icons, layout, aggregators), **adds the missing tier** (`@mesell/layout`), and
**seals it with enforcement** so the decoupling can never silently regress.

> **Sakai note:** Sakai (`themes/sakai-ng/`) is a *vendored reference only* — the live app
> uses a custom shell + `@mesell/ui-kit` + the **Aura** preset, not Sakai code. This plan
> does not adopt Sakai's layout machinery; it borrows patterns at most.

---

## 3. Locked decisions

| # | Decision | Resolution |
|---|----------|------------|
| **1** | Module semantics | **Grouped aggregators + escape hatch.** Concern-scoped arrays spread into standalone `imports`. Services + `provideMeeUi()` remain providers (root, not imports). |
| **2** | Layout ownership | **Chrome → reusable lib primitives**; composed `ShellComponent` stays a **host singleton**; MFEs import **page primitives only** (`MEE_LAYOUT`), never chrome or `ShellComponent`. |
| **4** | Library structure | **Keep the layered split + add `@mesell/layout`.** DAG: `composites → layout → ui-kit → primeng`. |
| **3** | Icon strategy | **Semantic registry + `mee-icon`.** Central `MEE_ICONS` map (semantic → `pi` class); components accept semantic names; raw `pi pi-*` allowed in exactly one file. |
| **5** | Enforcement | **Scanner-script contract suite**, blocking CI gate (`frontend/tools/contracts/`), mirroring backend §16.E Contracts 8–10. |

### 3.1 Aggregator groups (decision #1)

| Aggregator | Members (wrappers) |
|------------|--------------------|
| `MEE_FORM` | input, textarea, select, treeselect, password, otp |
| `MEE_OVERLAY` | dialog, drawer, confirm-dialog |
| `MEE_FEEDBACK` | toast, badge, skeleton, spinner, progress-bar |
| `MEE_DATA` | table, steps |
| `MEE_COMMON` | button, card, menu, **icon** |
| `MEE_FILE` | file-upload |
| `MEE_LAYOUT` | page, section, toolbar, grid, form-layout *(from `@mesell/layout`)* |
| `MEE_UI_ALL` | spread of all ui-kit groups (escape hatch) |

Usage: `imports: [...MEE_FORM, ...MEE_FEEDBACK]`. **Providers stay separate:**
`provideMeeUi()` + `MeeToastService` / `MeeConfirmService` in `app.config.ts`.

### 3.2 Target architecture (decisions #2 + #4)

```
@mesell/ui-kit      atoms — PrimeNG wrappers + mee-icon + MEE_ICONS + aggregators
      ↑
@mesell/layout      NEW — page primitives (MEE_LAYOUT, MFE-importable)
                          + chrome primitives (mee-app-bar/side-nav/nav-item/user-menu, shell-only)
      ↑
@mesell/composites  content patterns (stat-card, status-badge, page-header, empty-state, …)
      ↑
apps/shell (host)   ShellComponent = composes chrome + navItems data + AuthService + <router-outlet>
MFEs                import MEE_* aggregators + MEE_LAYOUT + composites — and nothing else
```

### 3.3 Icon model (decision #3)

```ts
// @mesell/ui-kit/icon/icon.registry.ts   ← the ONLY file with raw 'pi pi-'
export const MEE_ICONS = {
  dashboard: 'pi pi-home',  catalog: 'pi pi-list',  add: 'pi pi-plus-circle',
  delete: 'pi pi-trash',    back: 'pi pi-arrow-left', user: 'pi pi-user',
  logout: 'pi pi-sign-out', /* …one entry per icon used… */
} as const;
export type MeeIconName = keyof typeof MEE_ICONS;
```
`<mee-icon name="dashboard" />` · `<mee-button icon="add" />`. Swap icon set = edit this map.

### 3.4 Frontend boundary contracts (decision #5)

| # | Contract | Rule | Scanner |
|---|----------|------|---------|
| FE-1 | PrimeNG seal | no `primeng`/`@primeuix` import outside `@mesell/ui-kit` | `fe1_no_primeng_outside_uikit.mjs` |
| FE-2 | Icon seal | no raw `pi pi-*` outside `ui-kit/icon/icon.registry.ts` | `fe2_no_raw_pi_icons.mjs` |
| FE-3 | Chrome shell-only | MFEs never import chrome primitives or `ShellComponent` | `fe3_chrome_shell_only.mjs` |
| FE-4 | Lib DAG | imports flow `composites → layout → ui-kit` (no back-edges/cycles) | `fe4_lib_dag.mjs` |
| FE-5 | Public barrels | MFEs import `@mesell/*` barrels only — no deep paths, no cross-MFE | `fe5_public_barrels_only.mjs` |

CI job **"FE Gate: lint (5 contracts)"** runs `node tools/contracts/run-all.mjs` → exit 1 on any violation.

---

## 4. Phased implementation plan

Sequenced by dependency. Each phase is independently shippable (one PR), CI green, no behavior regression.

**Execution model (MeeSell HYBRID rule):** each code-heavy phase = (1) `meesell-frontend-coordinator`
writes the task SPEC → (2) the named specialist builds (`meesell-angular-component-builder` /
`meesell-angular-service-builder` / `meesell-angular-ui-styler`) → (3) coordinator runs the
merge-gate review. Contract/CI wiring touching infra coordinates with `meesell-infra-builder`.

### Phase 0 — Scaffolding & contract harness *(foundation, no behavior change)*
- Create `@mesell/layout` lib skeleton: `libs/layout/index.ts` + `tsconfig` path `@mesell/layout`.
- Create `frontend/tools/contracts/` + `run-all.mjs` runner (rules start **warn-only**).
- Add CI job **"FE Gate: lint (5 contracts)"** — initially **non-blocking** (reports only).
- **Deliverable:** empty layout lib + green (warn-only) contract harness wired into CI.
- **Depends on:** —

### Phase 1 — Icon abstraction *(closes FE-2)*  ·  builder: component
- `ui-kit/icon/icon.registry.ts` (`MEE_ICONS` + `MeeIconName`) + `mee-icon` component.
- Fold `mee-button`'s `MATERIAL_TO_PI` into the registry; `icon` inputs accept `MeeIconName`.
- Migrate the 3 `pi pi-*` leaks (shell ×2, smart-picker) → semantic names / `mee-icon`.
- Flip **FE-2** to blocking.
- **Deliverable:** zero raw `pi pi-*` outside the registry; `mee-icon` shipped.
- **Depends on:** Phase 0.

### Phase 2 — Aggregators *(decision #1)*  ·  builder: component
- Add grouped aggregator arrays to `ui-kit/index.ts` (`MEE_FORM`…`MEE_COMMON`, `MEE_FILE`, `MEE_UI_ALL`).
- Document the two-pronged contract (aggregator arrays for `imports`, `provideMeeUi()` for providers).
- **Deliverable:** aggregators exported + documented. (MFE migration deferred to Phase 6.)
- **Depends on:** Phase 0 (parallel to Phase 1).

### Phase 3 — Layout: page primitives *(decisions #2/#4)*  ·  builder: component + ui-styler
- Build in `@mesell/layout`: `mee-page`, `mee-section`, `mee-toolbar`, `mee-grid`/`mee-stack`, `mee-form-layout`.
- Export `MEE_LAYOUT` aggregator. (`auth-layout` stays in `composites` for now — revisit.)
- **Deliverable:** `MEE_LAYOUT` page primitives shipped + storybook/demo usage.
- **Depends on:** Phase 0; `ui-kit`.

### Phase 4 — Layout: chrome + shell refactor *(decision #2; closes FE-3)*  ·  builder: component + ui-styler
- Extract chrome primitives into `@mesell/layout`: `mee-app-bar`, `mee-side-nav`, `mee-nav-item`, `mee-user-menu` (lift current `ShellComponent` HTML/CSS into them).
- Refactor `apps/shell/ShellComponent` to **compose** them + `navItems` data + `AuthService` wiring + `<router-outlet>`.
- Flip **FE-3** to blocking.
- **Deliverable:** thin host `ShellComponent`; chrome lives in lib; visual parity with today.
- **Depends on:** Phase 3; `ui-kit` (`mee-menu`/`mee-drawer`/`mee-button`).

### Phase 5 — Seal & DAG contracts *(decision #5 capstone)*
- Finalize scanners **FE-1** (lock the already-true PrimeNG seal), **FE-4** (lib DAG), **FE-5** (public barrels).
- Flip the **FE Gate to blocking** (required status check on `develop`).
- **Deliverable:** all 5 contracts enforced; gate required.
- **Depends on:** Phases 1–4.

### Phase 6 — MFE adoption sweep
- Per MFE (auth, catalog, dashboard, export, onboarding, pricing): migrate to aggregators, `MEE_LAYOUT` page primitives, and `mee-icon` semantic names; remove any remaining ad-hoc imports.
- **Deliverable:** every MFE on the canonical surface; contracts green per MFE.
- **Depends on:** Phases 1–5. *(Can be done MFE-by-MFE in parallel PRs.)*

### Phase 7 — Swap-proof regression *(proves the DoD)*
- Add a second theme preset (dark or alt-brand) toggled in **one file**; verify the app restyles with no other change. Same for an icon-set swap (edit `MEE_ICONS` only).
- Document the swap procedure in this doc's appendix.
- **Deliverable:** demonstrated one-file theme/icon swap; DoD met.
- **Depends on:** all.

### Dependency graph
```
P0 ──┬─ P1(icons) ───────────────┐
     ├─ P2(aggregators) ─────────┤
     └─ P3(page layout) ─ P4(chrome+shell) ─┤
                                            └─ P5(seal) ─ P6(MFE sweep) ─ P7(swap proof)
```

---

## 5. Scope

**In:** `@mesell/layout` lib · `mee-icon` + registry · page + chrome primitives · grouped
aggregators · 5 scanner contracts + blocking CI gate · MFE adoption · swap-proof test.

**Out (for now):** rewriting working `ui-kit` wrappers · adopting Sakai's layout machinery
wholesale · visual redesign · components no MFE needs yet · moving `auth-layout` (deferred).

---

## 6. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Aggregators hurt tree-shaking if too wide | Concern-scoped groups (decision #1); MFEs import only needed groups; `MEE_UI_ALL` is an escape hatch, not the default. |
| Chrome extraction regresses shell visuals | Phase 4 acceptance = visual parity; ui-styler review; screenshot diff. |
| Contracts flake / false positives | Warn-only first (Phase 0), flip to blocking only after each rule is clean (Phases 1/4/5). |
| MFE sweep is large | Phase 6 is per-MFE parallel PRs, not one big-bang. |

---

## 7. Open items (non-blocking)

- `auth-layout` placement — keep in `composites` or move to `@mesell/layout` (defer).
- Pipes/directives layer — none exist yet; add only when a concrete need appears (out of initial scope).
- Whether `@mesell/layout` chrome needs a separate sub-entry vs lint-only `shell-only` enforcement (FE-3 handles it for now).

---

## 8. Appendix — swap procedure *(filled in Phase 7)*

Phase 7 (`feat/ui-ds-phase7`, commit `a979b6e`, PR #276) demonstrated both swaps.
Full procedure: `frontend/libs/ui-kit/SWAP_GUIDE.md`. Summary below.

### Theme swap (one file: `providers.ts`)

```ts
// Before (live default — do not change in production without a brand decision):
import { MeeSellPreset } from '@mesell/ui-kit';
// ...
preset: MeeSellPreset,

// After (alt brand — swap by changing import + preset reference):
import { MeeSellAltPreset } from '@mesell/ui-kit';
// ...
preset: MeeSellAltPreset,
```

No MFE, no other `ui-kit` file, no contract scanner needs to change.

### Icon-set swap (one file: `icon/icon.selector.ts`)

```ts
// Before (live default):
import { MEE_ICONS } from './icon.registry';
export const ActiveIcons = MEE_ICONS;

// After (alt set — Material Icons demo):
import { MEE_ICONS_ALT } from './icon.registry.alt';
export const ActiveIcons = MEE_ICONS_ALT;
```

Every `<mee-icon>` instance in every MFE resolves through `ActiveIcons` — no MFE
file needs to change. FE-2 stays clean because `icon.registry.alt.ts` contains no
`pi pi-*` strings.

### Verification after either swap
1. `ng build mfe-dashboard` (or any MFE) — must pass
2. `node tools/contracts/run-all.mjs --strict` — all 5 CLEAN
3. Visual check at 360 / 768 / 1280px — expected: all icons/colors reflect the new set
