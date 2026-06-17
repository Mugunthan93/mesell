# UI Design-System Decoupling — Phase 1 BUILD SPEC (Icon abstraction)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-16
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §3.3 (icon model), §4 "Phase 1 — Icon abstraction", §3.4 (FE-2).
**Precondition:** Phase 0 MERGED to develop @ `c6e08865` (`@mesell/layout` skeleton + `frontend/tools/contracts/` 5 scanners + `run-all.mjs` with `--strict` / `--strict=fe2,fe3` + non-blocking `FE Gate: lint (5 contracts)` CI job, all warn-only). **This spec authors against develop tip, not the `docs/ui-design-system-plan` planning branch** (which predates the Phase-0 merge — the builder branches off develop).

**Phase 1 mandate (verbatim from parent §4):** create `ui-kit/icon/icon.registry.ts` (`MEE_ICONS` + `MeeIconName`) + `mee-icon` component; fold `mee-button`'s `MATERIAL_TO_PI` into the registry (`icon` inputs accept `MeeIconName`); migrate the 3 `pi pi-*` leaks; flip **FE-2** to strict. Deliverable: zero raw `pi pi-*` outside the registry; `mee-icon` shipped.

---

## 0. Hard guardrails for this phase

1. **`icon.registry.ts` is the ONLY file allowed to contain raw `pi pi-`** after this phase. Everything else uses `MeeIconName` semantics or `<mee-icon name="…">`.
2. **No aggregators.** Do NOT add `MEE_COMMON` / `MEE_FORM` / any `MEE_*` array — those are Phase 2. Phase 1 only barrel-exports `MeeIconComponent` + `MeeIconName` from `libs/ui-kit/index.ts`.
3. **No layout / chrome primitives.** `MEE_LAYOUT` stays empty. No `mee-page`/`mee-app-bar`/etc. (Phases 3–4).
4. **No theme/preset change.** Do not touch `libs/ui-kit/theme.ts`, `providers.ts`, `styles.css`, or any preset.
5. **No new npm deps.** PrimeIcons CSS is already loaded (PrimeNG ships it); `mee-icon` just renders an `<i class="pi pi-…">`. No icon-font/package install.
6. **No backend / k8s / LOCKED-doc edits.** `docs/FRONTEND_ARCHITECTURE.md` is LOCKED — no §2 boundary-doc edit here.
7. **Standalone Angular only** — no NgModules. `mee-icon` is standalone + `OnPush`.
8. **No behavior/visual change** beyond the icon-resolution refactor. Every migrated icon must render the **same glyph** it renders today.

---

## 1. Measured baseline (verified 2026-06-16 against the live worktree)

### 1.1 Every raw `pi pi-` occurrence in app/lib source (the FE-2 surface)

| File | Line(s) | Context | Phase-1 action |
|---|---|---|---|
| `apps/shell/.../shell/shell.component.ts` | 28,29,30,31,35,37 | `navItems[].icon` (4) + `userMenuItems[].icon` (2) | **MIGRATE** → semantic names |
| `apps/shell/.../shell/shell.component.html` | 50 | hamburger `<i class="pi pi-bars">` | **MIGRATE** → `<mee-icon>` |
| `apps/mfe-catalog/.../smart-picker/smart-picker.component.ts` | 112 | `<mee-button icon="pi pi-send">` | **MIGRATE** → `icon="send"` |
| `libs/ui-kit/button/button.component.ts` | 13–18 | `MATERIAL_TO_PI` map (6 entries) | **FOLD** into registry; remove local map |
| `libs/ui-kit/confirm-dialog/confirm-dialog.component.ts` | 20 | `icon: 'pi pi-exclamation-triangle'` (ConfirmationService config) | **REGISTRY-RESOLVE** (see §2.4 — stays inside ui-kit either way) |
| `libs/ui-kit/menu/menu.types.ts` | 9 | **doc comment** `(e.g. 'pi pi-user')` | rewrite comment to a `MeeIconName` example (see §4 note) |
| `libs/ui-kit/menu/menu.component.spec.ts` | 7,9 | spec fixtures `icon: 'pi pi-user'` | inside ui-kit → allowed by registry-file-only allow-list? **NO** — see §3.3 spec-handling |
| `libs/ui-kit/button/button.component.spec.ts` | 72–104 | spec assertions on `MATERIAL_TO_PI` mapping | rewrite for the new registry resolution (see §2.3) |

> **Critical scanner fact (drives §3):** the Phase-0 FE-2 scanner **includes `*.spec.ts`** and its Phase-0 allow-prefix is the **whole `libs/ui-kit/` tree**. When Phase 1 narrows the allow-list to *exactly* `libs/ui-kit/icon/icon.registry.ts`, the **two ui-kit spec files** (`menu.component.spec.ts`, `button.component.spec.ts`) that currently contain `pi pi-` will **start failing FE-2 strict** unless their `pi pi-` literals are removed/rewritten. The builder MUST clean these spec literals as part of the migration, or FE-2 strict will go red on a test file. This is the single most important non-obvious item in this spec.

### 1.2 The icon-name surface beyond raw `pi pi-` (semantic-name inventory)

`mee-button.icon` (and `page-header.cta_icon` → `mee-button`) **already accept material-style semantic names today**, resolved by the local `MATERIAL_TO_PI` map with a `?? i` fallthrough. Distinct payloads seen across all `icon=`/`cta_icon=`/`[icon]` call-sites:

| Payload | Host component | In `MATERIAL_TO_PI` today? | Notes |
|---|---|---|---|
| `auto_awesome` | mee-button (×2), page-header.cta | ✅ `pi pi-sparkles` | |
| `arrow_forward` | mee-button | ✅ `pi pi-arrow-right` | |
| `add` | page-header.cta (dashboard) | ❌ **falls through → broken class `add`** | **latent bug** Phase 1 fixes |
| `pi pi-send` | mee-button (smart-picker) | n/a (raw) | the only raw-`pi` button caller |
| `person_add`, `assignment`, `cloud_off`, `inventory_2`, `category`, `image_not_supported`, `edit_note`, `check_circle` | **`mee-empty-state` / `mee-stat-card`** (text-glyph render `{{ icon() }}`) | n/a | **NOT a `pi`-icon surface — OUT of Phase-1 scope** (see §6) |

**Decisive classification result** (every `icon=` caller, host-resolved):
- `mee-empty-state` / `mee-stat-card` callers render `{{ icon() }}` as **literal text** — they are a *separate text-glyph concern*, do **not** trip FE-2, and are **explicitly out of scope** for Phase 1 (parent §4 Phase 1 is `pi pi-` only). They are recorded here so the builder does not chase them and so a future phase can address text-glyph icons deliberately.
- True `mee-button [icon]` material-name callers that resolve through `MATERIAL_TO_PI`: `catalog-form.component.ts:478` (`arrow_forward`), `catalog-form.component.ts:323` (`auto_awesome`), and via `page-header.cta_icon`: `dashboard.component.ts:70` (`add`), `catalog-list.component.ts:72` (`auto_awesome`). Plus the raw `smart-picker:112` (`pi pi-send`).

---

## 2. Files to create / edit (manifest)

| # | Path (relative to `frontend/`) | Action | Builder |
|---|---|---|---|
| G1 | `libs/ui-kit/icon/icon.registry.ts` | **CREATE** — `MEE_ICONS` + `MeeIconName` (the one raw-`pi` file) | component-builder |
| G2 | `libs/ui-kit/icon/icon.component.ts` | **CREATE** — `mee-icon` standalone OnPush | component-builder |
| G3 | `libs/ui-kit/icon/icon.component.spec.ts` | **CREATE** — registry-resolution + default tests | component-builder |
| G4 | `libs/ui-kit/index.ts` | **EDIT** — barrel-export `MeeIconComponent` + `MeeIconName` | component-builder |
| G5 | `libs/ui-kit/button/button.component.ts` | **EDIT** — remove local `MATERIAL_TO_PI`; resolve `icon` via registry; `icon` input typed `MeeIconName \| undefined` | component-builder |
| G6 | `libs/ui-kit/button/button.component.spec.ts` | **EDIT** — rewrite mapping assertions for registry resolution; remove raw `pi pi-` literals | component-builder |
| G7 | `libs/ui-kit/confirm-dialog/confirm-dialog.component.ts` | **EDIT** — resolve the warning icon via `MEE_ICONS['warning']` (no raw `pi pi-` literal) | component-builder |
| G8 | `libs/ui-kit/menu/menu.types.ts` | **EDIT** — `MeeMenuItem.icon` typed `MeeIconName`; rewrite doc-comment example (remove raw `pi pi-`) | component-builder |
| G9 | `libs/ui-kit/menu/menu.component.ts` | **EDIT (if needed)** — resolve `MeeMenuItem.icon` (`MeeIconName`) → `pi pi-…` class when handing to PrimeNG `<p-menu>` (see §2.5) | component-builder |
| G10 | `libs/ui-kit/menu/menu.component.spec.ts` | **EDIT** — replace fixture `icon: 'pi pi-user'` with `icon: 'user'` (`MeeIconName`); remove raw `pi pi-` | component-builder |
| G11 | `apps/shell/.../shell/shell.component.ts` | **EDIT** — `navItems[].icon` + `userMenuItems[].icon` → `MeeIconName` semantics | component-builder |
| G12 | `apps/shell/.../shell/shell.component.html` | **EDIT** — hamburger `<i class="pi pi-bars">` → `<mee-icon name="menu">`; nav `<i [class]="item.icon">` → `<mee-icon [name]="item.icon">` (see §2.6) | component-builder |
| G13 | `apps/mfe-catalog/.../smart-picker/smart-picker.component.ts` | **EDIT** — `icon="pi pi-send"` → `icon="send"` | component-builder |
| G14 | `frontend/tools/contracts/fe2_no_raw_pi_icons.mjs` | **EDIT** — narrow allow-prefix from `libs/ui-kit/` to exactly `libs/ui-kit/icon/icon.registry.ts` | component-builder (infra reviews) |
| G15 | `.github/workflows/ci.yml` | **EDIT** — FE Gate run step → `node tools/contracts/run-all.mjs --strict=fe2` | component-builder + **infra coordination** (§5) |
| G16 | `frontend/tools/contracts/README.md` | **EDIT** — mark FE-2 as flipped-to-strict in Phase 1; note the registry-only allow-list | component-builder |

> **No `app.routes.ts` / `app.config.ts` / `main.ts` change** — Phase 1 touches no root wiring. (Frontend Lead confirms: root wiring untouched.)

---

## 3. Per-file spec

### G1 — `libs/ui-kit/icon/icon.registry.ts` (CREATE) — the ONLY raw-`pi` file

**Purpose:** the single semantic-name → `pi pi-*` class map (parent §3.3). Every other surface references `MeeIconName`; the icon set swaps by editing this one file.

**Required content (behavioral — builder writes literal TS):**
- `export const MEE_ICONS = { … } as const;` — a flat object, semantic kebab-or-camel name → `'pi pi-…'` string. **MUST be `as const`** so `keyof typeof` yields a literal-union type.
- `export type MeeIconName = keyof typeof MEE_ICONS;`
- A `resolveIcon(name: MeeIconName): string` helper (or inline lookup) returning `MEE_ICONS[name]` — used by `mee-icon`, `mee-button`, `mee-menu`, `confirm-dialog`.
- A top-of-file comment: "This is the ONLY file permitted to contain raw `pi pi-` classes (FE-2 allow-list). Swap the icon set by editing the right-hand values here."

**The COMPLETE proposed `MEE_ICONS` map** (derived from the live inventory — every name an existing surface needs):

```
// ── Navigation / chrome (shell navItems, userMenu, hamburger) ──
dashboard   → 'pi pi-home'            // shell navItems Dashboard
catalog     → 'pi pi-list'            // shell navItems "My Catalogs"
add         → 'pi pi-plus-circle'     // shell "New Catalog" + page-header.cta "add"
user        → 'pi pi-user'            // shell Profile nav + userMenu "My Profile" + menu fixture
logout      → 'pi pi-sign-out'        // shell userMenu "Log out"
menu        → 'pi pi-bars'            // shell hamburger (was raw pi pi-bars)

// ── mee-button.icon (folded from MATERIAL_TO_PI + the unmapped 'add' + raw send) ──
sparkles    → 'pi pi-sparkles'        // was MATERIAL_TO_PI['auto_awesome']
forward     → 'pi pi-arrow-right'     // was MATERIAL_TO_PI['arrow_forward']
back        → 'pi pi-arrow-left'      // was MATERIAL_TO_PI['arrow_back']
check       → 'pi pi-check'           // was MATERIAL_TO_PI['check']
close       → 'pi pi-times'           // was MATERIAL_TO_PI['close']
delete      → 'pi pi-trash'           // was MATERIAL_TO_PI['delete']
send        → 'pi pi-send'            // was raw 'pi pi-send' (smart-picker)

// ── Internal ui-kit use ──
warning     → 'pi pi-exclamation-triangle'  // confirm-dialog ConfirmationService icon
```

**Naming judgment calls (flag for confirmation):**
- `auto_awesome → sparkles`, `arrow_forward → forward`, `arrow_back → back`: chose **MeeSell-semantic** names (per parent §3.3 "semantic name") over the material literals or directional-`pi` literals. The 13 material-name callers that flow into `mee-button`/`page-header` are migrated to these semantics (only `auto_awesome`/`arrow_forward`/`add` actually reach a button today — see §1.2).
- `add` vs `new-catalog`: chose generic **`add`** (`pi pi-plus-circle`) so both shell "New Catalog" and page-header CTA "add" share one entry. This is the entry that **fixes the latent `add → ?? i → broken class` bug** (was unmapped).
- Names are kept **short, action/noun semantic** (`dashboard`, `catalog`, `user`, `logout`, `menu`, `send`, `delete`, `back`, `forward`, `close`, `check`, `sparkles`, `add`, `warning`) — 15 entries total.

**Acceptance:** `tsc --noEmit` resolves `MeeIconName`; `MEE_ICONS` is `as const`; this is the only file matching `pi\s+pi-[a-z]` after migration.

### G2 — `libs/ui-kit/icon/icon.component.ts` (CREATE)

**Required (behavioral):** standalone, `ChangeDetectionStrategy.OnPush`, selector `mee-icon`. `readonly name = input.required<MeeIconName>();`. A `resolved = computed(() => MEE_ICONS[this.name()])` (or `resolveIcon(this.name())`). Template: `<i [class]="resolved()" aria-hidden="true"></i>`. **No PrimeNG import** (it renders a plain `<i>` with a `pi` class — PrimeIcons CSS already global). Keep `aria-hidden="true"` to match the existing decorative-icon convention (a11y: icons here are decorative; meaningful labels live in adjacent text).

**Acceptance:** `<mee-icon name="dashboard" />` renders `<i class="pi pi-home" aria-hidden="true">`; passing a non-`MeeIconName` is a compile error.

### G3 — `libs/ui-kit/icon/icon.component.spec.ts` (CREATE)

**Required:** Vitest spec (follow the `select.component.spec.ts` template — `setInput` + create + resolution assertion). Assert: creates; `name="dashboard"` → host `<i>` class is `pi pi-home`; `name="send"` → `pi pi-send`. **No raw `pi pi-` literal as a free string outside an assertion that reads it from the rendered DOM** — acceptable inside an `expect(...).toContain('pi pi-home')` since the spec lives *inside* `libs/ui-kit/` … **BUT** FE-2's allow-list is now registry-file-only (§3.3): the spec file will be scanned. **Therefore assert against `MEE_ICONS['dashboard']` (import the constant), not a hard-coded `'pi pi-home'` literal**, to keep the spec free of raw `pi pi-`. (This pattern also applies to G6/G10.)

### G4 — `libs/ui-kit/index.ts` (EDIT — additive)

Add to the Components block: `export { MeeIconComponent } from './icon/icon.component';`. Add to the Types block: `export type { MeeIconName } from './icon/icon.registry';`. **Do NOT** export `MEE_ICONS` (the map is an internal detail; only the type + component are public). **Do NOT** add any `MEE_*` aggregator array (Phase 2).

### G5 — `libs/ui-kit/button/button.component.ts` (EDIT)

- Remove the local `const MATERIAL_TO_PI` map entirely.
- Change `readonly icon = input<string | undefined>(undefined);` → `readonly icon = input<MeeIconName | undefined>(undefined);` (import `MeeIconName`).
- `pgIcon` computed → `const i = this.icon(); return i ? MEE_ICONS[i] : undefined;` (import `MEE_ICONS`/`resolveIcon` from `../icon/icon.registry`). **Removes the `?? i` fallthrough** — `MeeIconName` is now compile-checked, so there is no unmapped-string path.
- Public API stays: `icon` input name unchanged, just retyped. All callers passing a `MeeIconName` keep working; callers passing an old material/raw string are updated in G11/G13 and the composite passthrough (see §2 note on `page-header`).

> **`page-header.cta_icon` passthrough:** `page-header.component.ts` declares `cta_icon = input<string | undefined>()` and binds `[icon]="cta_icon()"` to `mee-button`. Once `mee-button.icon` is `MeeIconName`, **`page-header.cta_icon` should also be retyped `MeeIconName | undefined`** for type-soundness, and its 2 callers (`dashboard:70` `add`, `catalog-list:72` `auto_awesome`→`sparkles`) updated. **Flag:** this is a small composites edit (G-extra). Builder: add `libs/composites/page-header/page-header.component.ts` retype + the 2 caller edits to the manifest (they are required for `tsc` to pass once button is strict-typed). Listed explicitly here so it is not missed:
> - `libs/composites/page-header/page-header.component.ts` — `cta_icon` → `MeeIconName | undefined`.
> - `apps/mfe-dashboard/.../dashboard.component.ts:70` — `cta_icon="add"` (already matches `add` registry name; no value change, just now type-valid).
> - `apps/mfe-catalog/.../catalog-list.component.ts:72` — `cta_icon="auto_awesome"` → `cta_icon="sparkles"`.
> - `apps/mfe-catalog/.../catalog-form/catalog-form.component.ts:478` — `icon="arrow_forward"` → `icon="forward"`.
> - `apps/mfe-catalog/.../catalog-form/catalog-form.component.ts:323` — `icon="auto_awesome"` → `icon="sparkles"`.

### G6 — `button.component.spec.ts` (EDIT)

Rewrite the 6 `pgIcon should map …` tests: assert `icon="sparkles"` → `pgIcon() === MEE_ICONS['sparkles']`, etc. Remove the `it('… passes through unknown')` test at line 103 (`icon: 'pi pi-user'`) — the unknown-passthrough path no longer exists (strict `MeeIconName`); replace with a `name="user"` → `MEE_ICONS['user']` assertion. **No raw `pi pi-` literals** — assert against `MEE_ICONS[...]`.

### G7 — `confirm-dialog.component.ts` (EDIT)

`icon: 'pi pi-exclamation-triangle'` → `icon: MEE_ICONS['warning']` (import `MEE_ICONS`). Stays inside ui-kit; removes the raw literal so the registry remains the sole raw-`pi` file. PrimeNG `ConfirmationService.confirm({ icon })` expects a class string — `MEE_ICONS['warning']` supplies it.

### G8 / G9 / G10 — `mee-menu` (EDIT)

- **G8 `menu.types.ts`:** `MeeMenuItem.icon?: string` → `icon?: MeeIconName`; rewrite the doc comment `(e.g. 'pi pi-user')` → `(e.g. 'user')`.
- **G9 `menu.component.ts`:** PrimeNG `<p-menu [model]>` expects each `MenuItem.icon` to be a CSS class. So `mee-menu` must **map** `MeeIconName` → `pi pi-…` when building the PrimeNG model: `{ ...item, icon: item.icon ? MEE_ICONS[item.icon] : undefined }`. Inspect the current `menu.component.ts` model-construction and insert the resolve. (If the component currently passes `items` straight through, add a `computed` that maps icons.)
- **G10 `menu.component.spec.ts`:** fixtures `icon: 'pi pi-user'` / `'pi pi-sign-out'` → `icon: 'user'` / `'logout'` (`MeeIconName`). Removes raw `pi pi-` from the spec (required for FE-2 strict).

### G11 — `shell.component.ts` (EDIT)

- `navItems`: `icon: 'pi pi-home'`→`'dashboard'`, `'pi pi-plus-circle'`→`'add'`, `'pi pi-list'`→`'catalog'`, `'pi pi-user'`→`'user'`. Type the array element `icon` as `MeeIconName` (the `as const` keeps literals; ensure they satisfy `MeeIconName`).
- `userMenuItems` (`MeeMenuItem[]`): `'pi pi-user'`→`'user'`, `'pi pi-sign-out'`→`'logout'`. (Now type-valid via G8.)

### G12 — `shell.component.html` (EDIT)

- Hamburger: `<i class="pi pi-bars" aria-hidden="true"></i>` → `<mee-icon name="menu" />`. Add `MeeIconComponent` to the shell component `imports` (G11).
- Nav-item icon (×2 — desktop + drawer): `<i [class]="item.icon" aria-hidden="true"></i>` → `<mee-icon [name]="item.icon" />` (now `item.icon` is `MeeIconName`).

### G13 — `smart-picker.component.ts` (EDIT)

`<mee-button … icon="pi pi-send" …>` → `icon="send"`. (The `category` at line 176 is a `mee-empty-state` text-glyph — **leave it**, out of scope per §6.)

### G14 — `fe2_no_raw_pi_icons.mjs` (EDIT — the strict-flip mechanics)

Change the allow-list from the whole ui-kit tree to **exactly the registry file**. Concretely, in the scanner:
```
// Phase 0:
const ALLOW_PREFIX_PHASE0 = 'libs/ui-kit/';
if (relPath.startsWith(ALLOW_PREFIX_PHASE0)) continue;
// Phase 1 → replace with an exact-file allow:
const ALLOW_REGISTRY_FILE = 'libs/ui-kit/icon/icon.registry.ts';
if (relPath === ALLOW_REGISTRY_FILE) continue;
```
Update the scanner's header doc-comment Phase-0/Phase-1 notes accordingly. **After this narrowing, the scanner must report 0 violations** (every `pi pi-` outside the registry has been migrated, including the two ui-kit spec files). If it reports >0, the migration is incomplete — the builder fixes the flagged file, never widens the allow-list.

### G15 — `.github/workflows/ci.yml` (EDIT — infra-coordinated)

Change the FE Gate run step (currently `run: node tools/contracts/run-all.mjs`) to:
```
run: node tools/contracts/run-all.mjs --strict=fe2
```
Update the inline step comment (`# Phase 0: exits 0 (warn-only). Phase 1+: add --strict=fe2 here.`) to reflect Phase 1 is now active. The `run-all.mjs` `--strict=fe2,fe3` comma-list machinery already exists (Phase 0) — `--strict=fe2` exits 1 only if FE-2 has violations, leaving FE-1/3/4/5 warn-only. **Do NOT add the job to `build.needs`/`deploy.needs`** and **do NOT change branch protection** — see §1 decision below.

### G16 — `tools/contracts/README.md` (EDIT)

Mark FE-2 as **strict (Phase 1)**; record the allow-list is now `libs/ui-kit/icon/icon.registry.ts` only; note FE-1/3/4/5 remain warn-only (flip at Phases 4/5).

---

## 4. The FE-2 strict-flip decision (recommended interpretation — FLAG for confirmation)

**Parent-plan position:** the FE-gate becomes a *required* status check only at **Phase 5** (parent §4 Phase 5: "Flip the FE Gate to blocking (required status check on `develop`)"). Phase 1 only flips the FE-2 *contract* to strict.

**Recommended interpretation (confirm):** In Phase 1, set the CI run step to `--strict=fe2`. This makes `run-all.mjs` **exit 1** (the job goes **red**) on any new raw `pi pi-` outside the registry. **But because the `FE Gate: lint (5 contracts)` job is NOT a required status check and is NOT in `build.needs`/`deploy.needs` (Phase 0 wiring, preserved), a red job does NOT block merge yet.** It is a loud, visible signal on the PR — the founder still must click merge. Making it *required* is deferred to Phase 5 exactly as the plan says.

**Net effect:** new icon leaks turn the FE Gate red immediately (regression caught at PR time), without changing branch-protection or coupling to the build. This is the cleanest reading and requires **zero infra/branch-protection change** in Phase 1.

**Alternative considered (NOT recommended for Phase 1):** make the job a required check *for FE-2 only* now. Rejected because (a) GitHub required-status-checks are per-job, not per-contract — you cannot mark "FE-2 only" required without also gating FE-1/3/4/5 which are still warn-only and would need their own clean state; (b) it pulls the Phase-5 capstone forward, contradicting the plan's staged rollout. **Recommendation: keep the job non-required in Phase 1; red-on-FE-2-violation is sufficient.**

**→ MASTER-SESSION / FOUNDER CONFIRM:** "Phase 1 = FE-2 strict (job goes red on violation) but job stays non-required (no branch-protection change); required-check deferred to Phase 5." Confirm before the build step.

---

## 5. Which specialist builds this + coordination

**Primary builder: `meesell-angular-component-builder`** — this phase is component + registry + migration of templates/component data (component territory). `mee-icon` is a standalone OnPush component; the migrations are template/TS edits in components.

**No `meesell-angular-ui-styler` work** — no new styling (icons inherit existing PrimeIcons CSS; `<i class="pi …">` is unchanged visually). **No `meesell-angular-service-builder` work** — no services/interceptors.

**Coordination: `meesell-infra-builder`** for G15 (the one-line `ci.yml` run-step change). The Lead authors the exact change in this spec; the component-builder applies it; **infra-builder confirms at merge-gate review** that: (a) the job remains NOT in `build`/`deploy` `needs`, (b) branch-protection required checks are untouched, (c) `--strict=fe2` is the only flag change. Per the HYBRID rule this is a coordination touch at review, not a separate dispatch.

---

## 6. Out-of-scope (explicit — refuse if asked in Phase 1)

- **Text-glyph icons on `mee-empty-state` / `mee-stat-card`** (`person_add`, `assignment`, `cloud_off`, `inventory_2`, `category`, `image_not_supported`, `edit_note`, `check_circle`): these render as `{{ icon() }}` literal text, are NOT `pi` classes, do NOT trip FE-2, and are a separate concern. **Do NOT migrate them.** (A future phase may unify text-glyph icons under the registry; not Phase 1.)
- **Aggregators** (`MEE_COMMON`/`MEE_FORM`/`MEE_UI_ALL` …) — Phase 2.
- **Layout / chrome primitives, `MEE_LAYOUT` population** — Phases 3–4.
- **Flipping FE-1/FE-3/FE-4/FE-5 to strict** — FE-1/FE-4/FE-5 at Phase 5, FE-3 at Phase 4. Phase 1 flips **only FE-2**.
- **Making the FE Gate a required status check** — Phase 5.
- **Theme/preset/styles changes; new npm deps; `app.config`/`app.routes`/`main.ts`; backend/k8s; `docs/FRONTEND_ARCHITECTURE.md`** (LOCKED).

---

## 7. Verification checklist (merge-gate evidence the builder must attach)

The PR body must show:

1. **FE-2 strict is green:** `cd frontend && node tools/contracts/run-all.mjs --strict=fe2; echo $?` → **`0`** (FE-2 = 0 violations after narrowing the allow-list). Paste the summary table.
2. **Zero raw `pi pi-` outside the registry:** `grep -rn "pi pi-" apps libs --include="*.ts" --include="*.html" | grep -v node_modules | grep -v "libs/ui-kit/icon/icon.registry.ts"` → **no output** (the ONLY match is the registry file). Paste the command + empty result.
3. **FE-2 scanner standalone:** `node tools/contracts/fe2_no_raw_pi_icons.mjs` → `FE-2: 0 violations.`
4. **Type-check clean:** `./node_modules/.bin/tsc -p tsconfig.json --noEmit` (or the project equivalent) → no errors — proves `MeeIconName` is satisfied at every `icon=`/`cta_icon=`/`MeeMenuItem.icon` site (including the `add → 'add'` fix and the `sparkles`/`forward` renames).
5. **Build green + budget:** `./node_modules/.bin/ng build frontend` (or `pnpm build`) succeeds; build time noted **< 90 s** (CLAUDE.md Decision 12 — expected ~3 s; `mee-icon` is tiny). Bundle delta noted (expected negligible — one small component, map of strings; the local `MATERIAL_TO_PI` map is removed).
6. **Tests green, no count drop:** `pnpm test` → SP0-baseline count + the new `icon.component.spec.ts` (expect ~+3 tests; `button`/`menu` spec rewrites keep their counts). No drop = no silent non-discovery. (Watch the `../apps/**`+`../libs/**` discovery globs per the SP0 test-discovery gotcha.)
7. **`mee-icon` renders correctly:** screenshots at **360 px** and **1280 px** of the shell (hamburger + nav icons via `<mee-icon>`) + smart-picker Send button — confirm every migrated glyph is visually identical to pre-migration (zero visual delta is the acceptance bar). a11y: `<mee-icon>` emits `aria-hidden="true"`; keyboard nav on shell nav + hamburger unaffected.
8. **CI delta is exactly the run-step flag:** `git diff .github/workflows/ci.yml` shows ONLY the `run:` line gaining `--strict=fe2` (+ the comment) — the job is NOT added to any `needs:` of build/deploy; branch-protection untouched. (infra-builder confirms at review.)
9. **No out-of-scope edits:** `git diff --stat` matches the G1–G16 manifest (+ the §5/G5 page-header passthrough edits). No empty-state/stat-card text-glyph file touched; no aggregator; `MEE_LAYOUT` still empty; no theme/preset edit; no `app.config`/`app.routes`/`main.ts`.

---

## 8. Risks / decisions for the master session to confirm before the build step

1. **[BLOCKING-CONFIRM] FE-2 strict-flip semantics (§4):** confirm "FE-2 strict → job red on violation, job stays NON-required (no branch-protection change); required deferred to Phase 5." If the founder instead wants FE-2 required-now, that is a branch-protection change owned by the founder and changes G15's scope.
2. **[NON-OBVIOUS, HIGH-IMPACT] Two ui-kit spec files contain `pi pi-`** (`menu.component.spec.ts`, `button.component.spec.ts`). The Phase-0 broad ui-kit allow-prefix masked them; narrowing to registry-file-only makes them FE-2 violations. The spec mandates rewriting their literals to `MEE_ICONS[...]` / `MeeIconName` (G6/G10). **Confirm the builder is told this explicitly** — missing it = FE-2 strict goes red on a test file and the migration looks "done but failing."
3. **[SCOPE] `page-header.cta_icon` + 5 caller retypes** (§5/G5 note): retyping `mee-button.icon` to `MeeIconName` forces a `page-header.cta_icon` retype and small value edits at 4–5 call-sites (`auto_awesome`→`sparkles`, `arrow_forward`→`forward`, `add` stays). These are **required for `tsc` to pass** and are listed so they're not surprises. Confirm the builder includes the composites edit.
4. **[NAMING] Semantic-name choices** (`sparkles`/`forward`/`back`/`add`/`menu` …, §G1): 15 names. Confirm the master session/founder is fine with MeeSell-semantic names over material literals. (Trivial to rename pre-merge; locked after callers migrate.)
5. **[LATENT BUG FIXED] `add` was unmapped** (`MATERIAL_TO_PI` had no `add`; `page-header cta_icon="add"` rendered the broken class `add`). Phase 1 fixes it via the `add → pi pi-plus-circle` registry entry. Flagged as an intended behavior *improvement* (a previously-broken icon now renders) — confirm this is acceptable (it is a fix, not a regression).
6. **[OUT-OF-SCOPE recorded] text-glyph icons** (`mee-empty-state`/`mee-stat-card`, §6): 8 material-name text glyphs remain as-is. Not a leak (no `pi pi-`); deliberately deferred. Flagged so a reviewer doesn't mistake them for missed migrations.

---

*End of Phase 1 BUILD SPEC. Next HYBRID step: master session dispatches `meesell-angular-component-builder` with this spec; `meesell-frontend-coordinator` then runs the merge-gate review (with `meesell-infra-builder` signing off the `ci.yml` hunk).*
