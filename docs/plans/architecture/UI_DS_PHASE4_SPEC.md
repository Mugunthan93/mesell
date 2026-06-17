# UI Design-System Decoupling — Phase 4 BUILD SPEC (Layout: chrome + shell refactor)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-17
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §3 decision #2 (layout ownership: chrome → reusable lib primitives, `ShellComponent` stays host singleton, MFEs never import chrome), §3.2 (target DAG), §3.4 (FE-3), §4 "Phase 4 — Layout: chrome + shell refactor", §7 (open item: chrome sub-entry vs lint-only seal).
**Preconditions:**
- **P0/P1/P2** merged to develop (`d1916cd`): `@mesell/layout` skeleton, contract harness, `mee-icon` registry (FE-2 strict), ui-kit aggregators.
- **P3 `19c344d` (PR #265, OPEN — this branch is STACKED on it):** `@mesell/layout` page primitives (`mee-page`/`section`/`toolbar`/`grid`/`stack`/`form-layout`) + `MEE_LAYOUT` + `layout.types.ts` (`MeeLayoutGap`/`MEE_GAP_TOKEN`) + `libs/layout/README.md`. **This phase builds on the Phase-3 barrel state.** Branch `feat/ui-ds-phase4` was cut off `feat/ui-ds-phase3` (not develop) to avoid a `libs/layout/index.ts` barrel conflict; its PR merges **after** #265.

**Phase 4 mandate (verbatim from parent §4):** "Extract chrome primitives into `@mesell/layout`: `mee-app-bar`, `mee-side-nav`, `mee-nav-item`, `mee-user-menu` (lift current `ShellComponent` HTML/CSS into them). Refactor `apps/shell/ShellComponent` to **compose** them + `navItems` data + `AuthService` wiring + `<router-outlet>`. Flip **FE-3** to blocking. **Deliverable:** thin host `ShellComponent`; chrome lives in lib; **visual parity with today**. **Depends on:** Phase 3; `ui-kit` (`mee-menu`/`mee-drawer`/`mee-button`)."

---

## 0. Hard guardrails for this phase

1. **VISUAL + BEHAVIORAL PARITY IS THE ACCEPTANCE BAR.** The refactor must produce a shell that is pixel- and behavior-identical to today: same 4 nav groups, same accent CTA, same active-route highlighting (exact vs prefix), same onboarding-hide, same mobile drawer, same hamburger, same avatar/user-menu, same responsive 1024px breakpoint. **`apps/shell/src/app/layouts/shell/shell.component.spec.ts` is the parity oracle — it must stay GREEN** (update query selectors only if the DOM structure genuinely moves, never weaken an assertion's intent).
2. **Two libraries touched + the shell:** create chrome primitives under `frontend/libs/layout/chrome/`, edit the `libs/layout` barrel, and refactor `apps/shell/.../layouts/shell/`. **No other MFE, no other lib, no backend/k8s.**
3. **Nav DATA + AuthService wiring STAY in `ShellComponent`** (parent §4). The `navGroups` array, the `onboardingComplete` predicate, `userMenuItems`, `userInitials`, `AuthService` injection, and the mobile-drawer `visible` signal remain shell-owned. The chrome primitives are **presentational** — they receive data via inputs and emit events; they hold no `AuthService`, no app routes table, no business state.
4. **FE-1 (PrimeNG seal) holds.** Chrome primitives may import `@mesell/ui-kit` wrappers (`MeeDrawerComponent`, `MeeMenuComponent`, `MeeIconComponent`, `MeeButtonComponent`) and `@angular/router` (`RouterLink`/`RouterLinkActive`/`RouterOutlet`) and `@angular/core` — but **NEVER `primeng`/`@primeuix` directly**. Router coupling is acceptable and expected for chrome (chrome is app-coupled by definition — that is *why* it is shell-only).
5. **FE-4 (lib DAG) holds.** Chrome lives in `@mesell/layout` (rank 1) → may import `@mesell/ui-kit` (rank 0) + `@mesell/core` (rank 0, for any shared type) — never `@mesell/composites` (rank 2).
6. **Chrome ships from the MAIN `@mesell/layout` barrel — NOT a `@mesell/layout/chrome` sub-path.** Rationale (resolves parent §7 open item): the shell (`apps/shell`) is the sole consumer; **FE-5** forbids apps from deep-importing `@mesell/<lib>/<subpath>`, so a `@mesell/layout/chrome` import from the shell would trip FE-5. Importing the chrome **symbols** from the barrel root keeps FE-5 clean, and **FE-3** already seals misuse by *symbol name* (`MeeAppBarComponent`, `MeeSideNavComponent`, `MeeNavItemComponent`, `MeeUserMenuComponent` are pre-seeded in `fe3_chrome_shell_only.mjs`) — any MFE importing a chrome symbol from anywhere is caught. **Therefore: NO `MEE_CHROME` aggregator in the public barrel** (an aggregator array symbol like `MEE_CHROME` is NOT in the FE-3 symbol list and would be a seal bypass). The shell references the four chrome components **directly by symbol**. (If a future need forces an aggregator, it must be added to the FE-3 symbol list in the same PR — out of scope here.)
7. **FE-3 flips to strict in CI** via the one-line flag change `--strict=fe2` → `--strict=fe2,fe3` in `.github/workflows/ci.yml` (the `fe-lint-contracts` step). The job stays **non-required** and **not** in `build.needs`/`deploy.needs` (Phase-5 makes it required) — so a red FE-3 is a loud PR signal, not a merge block. **No scanner edit** (FE-3 is forward-compat seeded). This is the **infra-coordinated** touch (see §6).
8. **Standalone Angular 18 only** — every chrome primitive is `standalone: true`, `OnPush`, signal inputs (`input()`/`input.required()`), `output()` for events, `viewChild` where needed (user-menu toggle). No NgModules.
9. **No new npm deps. No theme/preset/token-file change.** Chrome consumes existing `--mee-*` tokens (incl. the sidebar tokens `--mee-color-sidebar`/`-sidebar-text`/`-sidebar-active`).
10. **Lift, don't rewrite.** The chrome HTML/CSS is **moved** from `shell.component.{html,css}` into the primitives as faithfully as possible. Do not redesign, re-theme, or "improve" the visuals. Parity first.

---

## 1. Measured baseline (verified 2026-06-17 against `feat/ui-ds-phase4` @ `b0df842`)

### 1.1 The shell today (`apps/shell/src/app/layouts/shell/`)
| File | Lines | What it holds |
|---|---|---|
| `shell.component.ts` | ~130 | `NavItem`/`NavGroup` interfaces; `navGroups` (4 groups); `onboardingComplete` computed; `visibleItems()`; `userMenuItems`; `toggleUserMenu()`; `userInitials` getter; `AuthService` inject; `mobileSidebarVisible` signal; `userMenu` viewChild. Imports `RouterOutlet/RouterLink/RouterLinkActive`, `MeeDrawerComponent/MeeMenuComponent/MeeIconComponent`. |
| `shell.component.html` | ~95 | desktop `<nav class="sidebar-desktop">` (brand + groups + items); mobile `<mee-drawer class="mee-mobile-sidebar">` (same nav); `<header class="shell-header">` (hamburger + spacer + avatar + `<mee-menu #userMenu>`); `<main class="page-content"><router-outlet/></main>`. |
| `shell.component.css` | 197 | `.shell-layout`, `.sidebar-desktop`(+responsive hide), `.sidebar-brand`, `.nav-group(__label)`, `.sidebar-nav`, `.nav-item`(+`:hover`/`--active`/` i`/`--accent`/`--accent.--active`), `.shell-main`(+offset), `.shell-header`, `.hamburger`(+responsive show), `.header-spacer`, `.avatar`, `.page-content`, `::ng-deep .mee-mobile-sidebar .p-drawer*`. |
| `shell.component.spec.ts` | ~115 | **the parity oracle** — see §1.3. |

### 1.2 ui-kit pieces the chrome composes (already on develop — barrel-root imports)
- `MeeDrawerComponent` — `[visible]` model, `[modal]`, `[styleClass]`, projects content.
- `MeeMenuComponent` — `[items]` (`MeeMenuItem[]`), `.toggle(event)` (popup).
- `MeeIconComponent` — `[name]` (`MeeIconName`).
- (`MeeButtonComponent` available if a chrome button is wanted — the hamburger is currently a raw `<button>`; keep it a plain button or use mee-button, builder's call — parity of look is the constraint.)

### 1.3 The parity oracle — `shell.component.spec.ts` assertions (MUST stay green)
- `.sidebar-desktop .nav-group__label` text === `['Home','Catalogs','Categories','Account']`.
- `.nav-item` count ≥ 6.
- `.nav-item--accent` exists and contains "New Catalog".
- `.sidebar-desktop .nav-item` includes "Onboarding" by default; **excludes** it after `auth.setSession(..., { onboarding_complete: true })`.
- `componentInstance['userInitials']` === 'U' (no user) / 'MS' (Mugunthan S).
- `componentInstance['userMenuItems']` includes a `Log out` item.

> **Class-contract consequence:** because the spec queries by **CSS class across component boundaries** (the rendered DOM keeps classes regardless of which component emits them), the chrome primitives **MUST render the same class names** the spec queries: `nav-group__label`, `nav-item`, `nav-item--accent`, and the shell must keep `sidebar-desktop` on the desktop side-nav host. Preserve these exact class names in the lifted markup. `userInitials`/`userMenuItems`/`navGroups` stay as shell members (bracket-accessed by the spec). If a structural move is unavoidable, update the spec query but **never** the assertion intent, and record it in the PR.

---

## 2. The four chrome primitives (design — behavioral; builder writes literal TS)

All four: `standalone`, `OnPush`, selector `mee-*`, presentational (data in via inputs, events out via outputs), no `AuthService`/no routes table. They live in `frontend/libs/layout/chrome/<name>/`. The lifted CSS lives in each component's `styleUrls`/`styles` (or co-located `.css`). **Chrome contract types** (`MeeNavItem`, `MeeNavGroup`) live in `libs/layout/chrome/chrome.types.ts`.

### 2.0 Chrome nav contract types (`chrome.types.ts`)
```
export interface MeeNavItem {
  readonly label: string;
  readonly route: string;
  readonly icon: MeeIconName;            // import type from '@mesell/ui-kit'
  readonly accent?: boolean;             // filled CTA look (+ New Catalog)
  readonly exact?: boolean;              // routerLinkActive exact (true) vs prefix (false)
}
export interface MeeNavGroup {
  readonly label: string;
  readonly items: readonly MeeNavItem[];
}
```
> The shell's richer `NavItem` (with `prefixMatch` + `visible`) maps to this: shell computes `visibleNavGroups()` (applies the `visible` predicate, e.g. onboarding-hide) and maps `prefixMatch` → `exact: !prefixMatch` **before** passing `MeeNavGroup[]` to `mee-side-nav`. The visibility/auth logic stays in the shell; the lib type is the clean presentational contract.

### 2.1 `mee-nav-item` — single sidebar nav link
- **Selector:** `mee-nav-item`. **Imports:** `RouterLink`, `RouterLinkActive` (`@angular/router`), `MeeIconComponent` (`@mesell/ui-kit`).
- **Inputs:** `route: string` (required), `label: string` (required), `icon: MeeIconName` (required), `accent: boolean` (default false), `exact: boolean` (default true — exact active match; `false` = prefix match).
- **Output:** `navigated = output<void>()` — emitted on click (the mobile drawer listens to close itself).
- **Template (lifted):** `<a [routerLink]="route()" routerLinkActive="nav-item--active" [routerLinkActiveOptions]="{ exact: exact() }" class="nav-item" [class.nav-item--accent]="accent()" (click)="navigated.emit()"><mee-icon [name]="icon()" /><span>{{ label() }}</span></a>`.
- **CSS (lifted from shell):** `.nav-item`, `.nav-item:hover`, `.nav-item--active`, `.nav-item i`, `.nav-item--accent`, `.nav-item--accent:hover`, `.nav-item--accent.nav-item--active`. **Keep the exact class names** (parity oracle).
- **Acceptance:** renders `<a class="nav-item">` with icon+label; active route adds `nav-item--active`; `accent` adds `nav-item--accent`; click emits `navigated`.

### 2.2 `mee-side-nav` — sidebar (brand + groups), reused desktop + drawer
- **Selector:** `mee-side-nav`. **Imports:** `MeeNavItemComponent`.
- **Inputs:** `brand: string` (default `'MeeSell'`); `groups: readonly MeeNavGroup[]` (required).
- **Output:** `navigated = output<void>()` — re-emits any child `mee-nav-item.navigated` (so the mobile drawer can close on selection).
- **Template (lifted):** brand `<div class="sidebar-brand">{{ brand() }}</div>` then `@for (group of groups(); track group.label)` → `<div class="nav-group" role="group" [attr.aria-label]="group.label"><h2 class="nav-group__label">{{ group.label }}</h2><ul class="sidebar-nav">@for (item of group.items; track item.route){<li><mee-nav-item [route]="item.route" [label]="item.label" [icon]="item.icon" [accent]="item.accent ?? false" [exact]="item.exact ?? true" (navigated)="navigated.emit()" /></li>}</ul></div>`. **Empty groups are filtered by the shell before input** (so no `@if length>0` needed here — but a defensive `@if (group.items.length)` is acceptable).
- **CSS (lifted):** `.sidebar-brand`, `.nav-group`, `.nav-group + .nav-group`, `.nav-group__label`, `.sidebar-nav`. `:host` styles the sidebar surface: `background: var(--mee-color-sidebar); display:flex; flex-direction:column;` (the **inner** identity). **Positioning (width/fixed/responsive-hide) stays SHELL-side** on `.sidebar-desktop` (§3.2) — `mee-side-nav` is placement-agnostic so it works both fixed-desktop and inside the drawer.
- **Acceptance:** renders brand + one `.nav-group` per group with `.nav-group__label` + `mee-nav-item` per item; re-emits `navigated`.

### 2.3 `mee-app-bar` — top header bar
- **Selector:** `mee-app-bar`. **Imports:** `MeeIconComponent` (hamburger glyph).
- **Inputs:** none required (optional `menuLabel: string` default `'Open navigation'` for the hamburger aria-label).
- **Output:** `menuToggle = output<void>()` — emitted when the hamburger is clicked (shell opens the mobile drawer).
- **Projection:** default `<ng-content />` is the trailing actions region (the shell projects `<mee-user-menu>` here). Layout: hamburger (left, mobile-only) + `.header-spacer` (flex:1) + projected actions (right).
- **Template (lifted):** `<header class="shell-header"><button class="hamburger" [attr.aria-label]="menuLabel()" aria-haspopup="true" (click)="menuToggle.emit()"><mee-icon name="menu" /></button><div class="header-spacer"></div><ng-content /></header>`.
- **CSS (lifted):** `.shell-header`, `.hamburger`, `.hamburger` responsive `display:flex` at ≤1023px, `.header-spacer`. `:host { display:block; }` (or let `.shell-header` be the host element — builder's call; the sticky header + 60px height + surface bg + bottom border must be preserved).
- **Acceptance:** sticky 60px header; hamburger shows ≤1023px and emits `menuToggle`; projected actions sit right.

### 2.4 `mee-user-menu` — avatar + dropdown
- **Selector:** `mee-user-menu`. **Imports:** `MeeMenuComponent` (`@mesell/ui-kit`). `viewChild` the inner `mee-menu`.
- **Inputs:** `initials: string` (required); `items: MeeMenuItem[]` (required — `import type { MeeMenuItem } from '@mesell/ui-kit'`).
- **Behavior:** the avatar is a button-like element (`role="button"`, `tabindex=0`, keyboard `enter`/`space`) that calls the inner `mee-menu.toggle(event)` (internal `viewChild` + `toggleMenu(event)` method — lifted from the shell's `toggleUserMenu`).
- **Template (lifted):** `<div class="user-menu-trigger"><div class="avatar" role="button" tabindex="0" aria-haspopup="true" aria-label="User menu" (click)="toggle($event)" (keydown.enter)="toggle($event)" (keydown.space)="toggle($event)">{{ initials() }}</div><mee-menu #userMenu [items]="items()" /></div>`.
- **CSS (lifted):** `.avatar` (+ the `.user-menu-trigger` wrapper if present — add a minimal wrapper rule; today it's an unstyled `<div class="user-menu-trigger">`). Keep `.avatar` exact (36px circle, primary bg, 44px min touch target).
- **Acceptance:** renders `.avatar` with initials; click/enter/space toggles the menu; `items` drives the dropdown.

---

## 3. Shell refactor (`apps/shell/.../layouts/shell/`) — thin host

### 3.1 `shell.component.ts` (EDIT — slim down)
- **KEEP:** `AuthService` inject; `mobileSidebarVisible` signal; `onboardingComplete` computed; `navGroups` (shell's own `NavItem`/`NavGroup` with `prefixMatch`+`visible`); `userMenuItems`; `userInitials` getter; the `visible`-filtering logic.
- **ADD:** `visibleNavGroups = computed<MeeNavGroup[]>()` — applies the `visible` predicate per item, drops empty groups, maps `prefixMatch → exact: !prefixMatch`, returns the lib `MeeNavGroup[]` shape. (This replaces the template-side `visibleItems()`/`@if length>0` with a single computed feeding both desktop + drawer side-navs.)
- **REMOVE:** `userMenu` viewChild + `toggleUserMenu()` (now inside `mee-user-menu`); the `RouterLink`/`RouterLinkActive`/`MeeDrawerComponent`/`MeeMenuComponent`/`MeeIconComponent` imports that are no longer used directly (keep `RouterOutlet` + `MeeDrawerComponent` — the shell still owns the mobile drawer wrapper; add the 4 chrome component imports).
- **Final imports:** `RouterOutlet`, `MeeDrawerComponent` (mobile drawer host), `MeeAppBarComponent`, `MeeSideNavComponent`, `MeeUserMenuComponent` (and `MeeNavItemComponent` is transitively used by side-nav — not imported by shell). Import `MeeNavGroup` type from `@mesell/layout`.

### 3.2 `shell.component.html` (EDIT — compose)
```
<div class="shell-layout">
  <!-- desktop sidebar: positioning stays shell-side via .sidebar-desktop -->
  <mee-side-nav class="sidebar-desktop" brand="MeeSell" [groups]="visibleNavGroups()" />

  <!-- mobile: shell owns the drawer; side-nav is its content; close on navigate -->
  <mee-drawer [visible]="mobileSidebarVisible()" (visibleChange)="mobileSidebarVisible.set($event)"
              styleClass="mee-mobile-sidebar" [modal]="true">
    <mee-side-nav brand="MeeSell" [groups]="visibleNavGroups()" (navigated)="mobileSidebarVisible.set(false)" />
  </mee-drawer>

  <div class="shell-main">
    <mee-app-bar (menuToggle)="mobileSidebarVisible.set(true)">
      <mee-user-menu [initials]="userInitials" [items]="userMenuItems" />
    </mee-app-bar>
    <main class="page-content"><router-outlet /></main>
  </div>
</div>
```

### 3.3 `shell.component.css` (EDIT — keep ONLY composition/positioning)
- **KEEP (shell-owned):** `.shell-layout`; `.sidebar-desktop` (width 260px, `position:fixed`, inset, z-index) + its `@media (max-width:1023px){ display:none }`; `.shell-main` (flex column, `margin-left:260px`) + its `@media` offset reset; `.page-content` (padding, bg); `::ng-deep .mee-mobile-sidebar .p-drawer*` (the drawer panel overrides — the shell owns the `mee-drawer`, so these stay here).
- **REMOVE (moved into chrome primitives):** `.sidebar-brand`, `.nav-group*`, `.sidebar-nav`, `.nav-item*` (→ side-nav/nav-item); `.shell-header`, `.hamburger*`, `.header-spacer` (→ app-bar); `.avatar` (→ user-menu).
- **Parity note:** `.sidebar-desktop` background — `mee-side-nav` `:host` now paints `var(--mee-color-sidebar)`; the shell's `.sidebar-desktop` keeps width/position only (background may stay too — identical value, harmless). Verify no double-paint seam at the 260px edge.

### 3.4 `shell.component.spec.ts` (EDIT only if needed)
Run it first **unchanged**. The class-contract (§1.3) is designed so it should pass as-is (DOM keeps `.sidebar-desktop`/`.nav-group__label`/`.nav-item`/`.nav-item--accent`; `userInitials`/`userMenuItems` stay shell members). If a query breaks because a class moved, fix the **selector** (not the assertion). Add stubs for the new chrome selectors only if jsdom rendering requires it (the existing real-PrimeNG render works today, so the real chrome should render too). Record any change.

---

## 4. New chrome specs (co-located)
Each chrome primitive ships a `*.spec.ts` (TestBed + `NoopAnimationsModule`; mirror `card.component.spec.ts` / the Phase-3 layout specs):
- `mee-nav-item`: creates; renders `.nav-item` with label+icon; `accent=true` adds `.nav-item--accent`; click emits `navigated`. (Needs `provideRouter([])` for `routerLink`.)
- `mee-side-nav`: creates; renders one `.nav-group__label` per group + a `mee-nav-item` per item; `navigated` re-emits. (`provideRouter([])`.)
- `mee-app-bar`: creates; hamburger click emits `menuToggle`; projects trailing content.
- `mee-user-menu`: creates; renders `.avatar` with initials; `toggle` invokes the inner menu (assert no throw / viewChild present).

---

## 5. Barrel + CI (the two seams)

### 5.1 `libs/layout/index.ts` (EDIT — additive)
Add a `// Chrome primitives (shell-only — FE-3 sealed; MFEs must NOT import these)` block re-exporting the 4 component classes + the 2 chrome types:
```
export { MeeAppBarComponent }   from './chrome/app-bar/app-bar.component';
export { MeeSideNavComponent }  from './chrome/side-nav/side-nav.component';
export { MeeNavItemComponent }  from './chrome/nav-item/nav-item.component';
export { MeeUserMenuComponent } from './chrome/user-menu/user-menu.component';
export type { MeeNavItem, MeeNavGroup } from './chrome/chrome.types';
```
Update the barrel header: flip the "TODO(Phase 4): chrome primitives" line to past tense (chrome shipped). **No `MEE_CHROME` aggregator** (§0.6). `MEE_LAYOUT` (page primitives) is unchanged.

### 5.2 `.github/workflows/ci.yml` (EDIT — infra-coordinated, one line)
In the `fe-lint-contracts` step, change `run: node tools/contracts/run-all.mjs --strict=fe2` → `--strict=fe2,fe3`. Update the adjacent step comment (Phase 4 active). **Do NOT** add the job to `build.needs`/`deploy.needs`; **Do NOT** touch branch protection. (Same posture as the Phase-1 FE-2 flip — red-on-violation visible signal, non-required until Phase 5.)

---

## 6. Which specialist builds this + coordination (HYBRID)
- **Primary builder: `meesell-angular-component-builder`** — four standalone components extracted from the shell + the shell composition refactor + specs + barrel. Component territory.
- **Styling/parity pass: `meesell-angular-ui-styler`** — **the critical reviewer this phase.** Verifies pixel/behavior parity: sidebar (260px, fixed, dark bg, group dividers, label casing), nav-item (active left-border + bg tint, accent filled CTA, 44px touch targets), app-bar (60px sticky, hamburger ≤1023px), avatar (36px circle), mobile drawer (260px dark panel via `::ng-deep`), the 1024px breakpoint crossover (desktop sidebar hides ↔ hamburger appears), and the `.nav-item i` icon-size parity (note: cross-encapsulation — confirm the rendered glyph size matches today). Sequential after the component-builder; **styling/markup only, no input-API change.**
- **Infra coordination: `meesell-infra-builder`** for §5.2 (the `ci.yml` `--strict=fe2,fe3` flip). The component-builder applies the one-line change; **infra confirms at merge-gate** that (a) the job stays out of `build`/`deploy` `needs`, (b) branch protection is untouched, (c) `--strict=fe2,fe3` is the only change. Per HYBRID this is a review-time coordination touch, not a separate build dispatch.
- **Coordinator (this session) runs the merge-gate** (§8) — it can reject back to the specialist.

---

## 7. Out-of-scope (refuse if asked)
- **MFE adoption** of chrome or page primitives — Phase 6. (MFEs must NEVER import chrome — that is the FE-3 invariant, not an adoption task.)
- **Moving `auth-layout`** out of composites — deferred (parent §7).
- **A `@mesell/layout/chrome` sub-entry / `MEE_CHROME` aggregator** — explicitly rejected (§0.6).
- **Flipping FE-1/FE-4/FE-5 to strict / making the FE Gate a required check** — Phase 5.
- **Re-theming, redesigning, or "improving" the shell visuals** — parity only.
- **New page primitives, pipes/directives, theme/preset/token edits, new npm deps.**
- **`mee-page` `asMain` landmark input** (the Phase-3 carry) — only act if the shell's `<main>` ownership actually changes here; it does **not** (the shell keeps `<main class="page-content">`), so **leave it**.
- **Backend/k8s; `docs/FRONTEND_ARCHITECTURE.md`** (LOCKED).

---

## 8. Verification checklist (merge-gate evidence in the PR)
1. **Type-check:** `npx tsc -p tsconfig.json --noEmit` → 0 errors.
2. **Shell parity oracle GREEN:** `npx ng test frontend --watch=false` → `shell.component.spec.ts` all pass (note any selector update + why). Report the full pass/fail line; the only acceptable failure is the **pre-existing** `apps/shell/src/app/app.spec.ts` NG0201 `MessageService` (separate ticket).
3. **New chrome specs green:** +4 chrome `*.spec.ts` discovered + passing. Report new count.
4. **Build green:** `npx ng build frontend --configuration development` succeeds. Report the shell/chrome chunk + initial-bundle line. (Bundle may shift slightly — chrome moved lib-side — but the shell lazy chunk should be ~parity; flag any large delta.)
5. **FE contracts:** `node tools/contracts/run-all.mjs --strict=fe2,fe3; echo $?` → **exit 0**, FE-2 + FE-3 strict-clean, all 5 CLEAN. Then also run plain `node tools/contracts/run-all.mjs` and paste the table. **FE-3 must be 0** (no MFE imports chrome).
6. **Grep proofs (paste):**
   - `grep -rEn "^\s*import.*(primeng|@primeuix)" libs/layout/chrome/` → none (FE-1).
   - `grep -rEn "@mesell/composites" libs/layout/chrome/` → none (FE-4).
   - `grep -rn "pi pi-" libs/layout/chrome/` → none (FE-2).
   - `grep -rn "ShellComponent\|MeeAppBar\|MeeSideNav\|MeeNavItem\|MeeUserMenu" apps/mfe-*/` → none (FE-3 by construction).
7. **CI flag:** `git diff .github/workflows/ci.yml` shows ONLY `--strict=fe2` → `--strict=fe2,fe3` (+ comment), job still not in `build`/`deploy` `needs`.
8. **Diff scope:** `git diff --stat` shows only `libs/layout/chrome/**`, `libs/layout/index.ts`, `apps/shell/.../layouts/shell/**`, `.github/workflows/ci.yml`, and this spec. No other MFE/lib, no theme/token, no backend.
9. **Visual parity statement (ui-styler):** explicit confirmation each chrome region matches today (sidebar/nav-item/app-bar/avatar/drawer/breakpoint), with DOM-class or screenshot evidence where possible.

---

## 9. Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| Shell visual regression (chrome extraction) | Parity oracle spec stays green; ui-styler parity pass (§6); lifted CSS keeps exact class names + token values. |
| Spec breaks on moved classes | §1.3 class-contract preserves `.sidebar-desktop`/`.nav-group__label`/`.nav-item`/`.nav-item--accent` in the DOM; fix selector not intent. |
| `.nav-item i` icon size lost across encapsulation | ui-styler confirms rendered glyph size matches; if the rule was already a no-op today, parity = leave it; else `::ng-deep` inside nav-item. |
| Mobile drawer panel styling (`::ng-deep .mee-mobile-sidebar`) | Stays shell-side (shell owns `mee-drawer`); side-nav inside renders identical nav markup. |
| FE-5 trip if shell deep-imports chrome | §0.6: chrome from barrel **root**; no sub-path import. |
| FE-3 false-green if a `MEE_CHROME` aggregator is added | §0.6: no aggregator; shell imports the 4 symbols directly (each FE-3-seeded). |
| `ci.yml` flip over-reaches (gates build) | §5.2 + infra confirm: only the flag string changes; job stays non-required. |

---

## 10. Decisions for the founder to confirm before/at merge
1. **[CONFIRM — stacked PR]** `feat/ui-ds-phase4` is cut off `feat/ui-ds-phase3` (not develop) to avoid a barrel conflict; **its PR must merge AFTER #265**. If you merge #265 first, the Phase-4 diff against develop becomes clean automatically. Confirm the stack ordering.
2. **[CONFIRM — chrome from main barrel, no sub-entry, no MEE_CHROME] §0.6** resolves parent §7 in favor of the lint-only seal (FE-3 by symbol) + barrel-root import (FE-5 clean). Confirm (vs a `@mesell/layout/chrome` sub-path, which would trip FE-5 from the shell).
3. **[CONFIRM — FE-3 strict, non-required] §5.2:** CI flips `--strict=fe2,fe3`; job stays non-required until Phase 5 (red = visible signal, not a merge block). Confirm.
4. **[NOTE — parity is the bar]** No visual change intended; the ui-styler pass + the parity oracle spec are the gate.

---

*End of Phase 4 BUILD SPEC. Next HYBRID step: this session dispatches `meesell-angular-component-builder` (extract the 4 chrome primitives + refactor the shell + barrel + ci.yml flag + specs), runs an interim coordinator check, dispatches `meesell-angular-ui-styler` for the parity pass, coordinates `meesell-infra-builder` review of the ci.yml flip, then runs the §8 merge-gate and opens the PR for the founder.*

End the eventual commit body with:
Co-Authored-By: Claude Opus 4.8 (1M context)
