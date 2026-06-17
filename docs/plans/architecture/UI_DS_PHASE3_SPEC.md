# UI Design-System Decoupling — Phase 3 BUILD SPEC (Layout: page primitives)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-16
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §3 decision #2 (layout ownership) + #4 (lib structure), §3.1 (`MEE_LAYOUT` group), §3.2 (target architecture DAG), §4 "Phase 3 — Layout: page primitives", §3.4 (FE-1/FE-4).
**Preconditions (all MERGED to develop — this spec authors against develop tip `d1916cd`, not the planning branch):**
- **P0 `c6e08865`** — `@mesell/layout` skeleton (`libs/layout/index.ts` with empty `MEE_LAYOUT: readonly never[] = []`, tsconfig path `@mesell/layout` + `@mesell/layout/*`), `frontend/tools/contracts/` (5 scanners + `run-all.mjs`), non-blocking `FE Gate: lint (5 contracts)` CI job.
- **P1 `d635aed3` (#259)** — `mee-icon` + `MEE_ICONS` registry; FE-2 strict.
- **P2 `d1916cd` (#260)** — six ui-kit aggregator arrays (`MEE_FORM`…`MEE_FILE`, `MEE_UI_ALL`) in `libs/ui-kit/aggregators.ts`; `libs/ui-kit/README.md`. **`MEE_LAYOUT` was deliberately left to `@mesell/layout` — this phase populates it.**

**Phase 3 mandate (verbatim from parent §4):** "Build in `@mesell/layout`: `mee-page`, `mee-section`, `mee-toolbar`, `mee-grid`/`mee-stack`, `mee-form-layout`. Export `MEE_LAYOUT` aggregator. (`auth-layout` stays in `composites` for now — revisit.) **Deliverable:** `MEE_LAYOUT` page primitives shipped + storybook/demo usage. **Depends on:** Phase 0; `ui-kit`."

---

## 0. Hard guardrails for this phase

1. **`@mesell/layout` is the only library touched.** Phase 3 creates files under `frontend/libs/layout/` and edits `libs/layout/index.ts`. **Zero `apps/**` edits, zero `libs/ui-kit/**` edits, zero `libs/composites/**` edits.** A diff touching any MFE/app or another lib is out of scope and must be rejected at review.
2. **PAGE primitives only — NO chrome.** `mee-app-bar`, `mee-side-nav`, `mee-nav-item`, `mee-user-menu`, and the `ShellComponent` refactor are **Phase 4**. Do **not** build, stub, or reference them. The `index.ts` "TODO(Phase 4): chrome primitives" comment stays as-is.
3. **FE-1 (PrimeNG seal) is the load-bearing invariant of this phase.** `@mesell/layout` primitives **must NOT** `import` anything from `primeng` or `@primeuix`. Page primitives are pure structural layout — plain Angular + Tailwind/CSS, content projection, signal inputs. They need **no** PrimeNG and (in practice) **no** `@mesell/ui-kit` import either (see §3.0). If a primitive ever needs an atom, it consumes it through `@mesell/ui-kit` — never PrimeNG directly. **Phase 3 does NOT flip FE-1 to strict** (that is Phase 5) but the diff must keep FE-1 at **0 violations**.
4. **FE-4 (lib DAG) must stay green.** `@mesell/layout` is **rank 1**: it may import `@mesell/ui-kit` (rank 0) and the rank-0 shared bases (`@mesell/core`, `@mesell/design-tokens`, `@mesell/env`). It must **NEVER** import `@mesell/composites` (rank 2) — that is a back-edge and an instant FE-4 violation. Spec target: layout imports **no sibling UI lib at all** (pure primitives) → FE-4 stays trivially clean.
5. **`auth-layout` stays in `@mesell/composites`.** Do NOT move it, copy it, or re-home it (parent §4 + §7 open item — deferred). It is referenced here only as a styling-convention exemplar.
6. **No new npm deps.** Tailwind + the `--mee-*` design tokens (`libs/design-tokens/_tokens.css`) are already global. Primitives render plain elements with Tailwind classes and/or `styles:[]` referencing `var(--mee-*)`.
7. **Standalone Angular 18 only** — every primitive is `standalone: true`, `ChangeDetectionStrategy.OnPush`, signal inputs (`input()` / `input.required()`), `computed()` for derived class/style. No NgModules. No `@Input()` decorators.
8. **No theme / preset / token-file change.** Do not edit `libs/design-tokens/_tokens.css`, `libs/ui-kit/theme.ts`, `providers.ts`, or `styles.css`. Primitives *consume* tokens; they do not define them.
9. **No behavior/runtime wiring.** No services, no router, no `AuthService`, no HTTP. Page primitives are presentational shells (structure + projection). `app.config.ts` / `app.routes.ts` / `main.ts` untouched.
10. **Additive, self-contained diff.** New files under `libs/layout/` + the `index.ts` barrel population + the README + the demo doc. No deletions, no edits outside `libs/layout/`.

---

## 1. Measured baseline (verified 2026-06-16 against develop `d1916cd`)

| Fact | Evidence |
|---|---|
| `libs/layout/` contains exactly **one** file: `index.ts` | `find libs/layout -type f` → `libs/layout/index.ts` |
| `MEE_LAYOUT` is `export const MEE_LAYOUT: readonly never[] = [] as const;` | current barrel |
| tsconfig paths already wired | `@mesell/layout` → `libs/layout/index.ts`; `@mesell/layout/*` → `libs/layout/*` |
| FE contracts baseline | `node tools/contracts/run-all.mjs` → **0 warnings across all 5** |
| Test runner | `@angular/build:unit-test` (vitest), specs discovered via `../../../libs/**/*.spec.ts`; TestBed + `NoopAnimationsModule` pattern (see `libs/ui-kit/card/card.component.spec.ts`) |
| Build builder | `@angular-architects/native-federation:build`; `npx ng build frontend --configuration development` |
| Styling conventions (two sanctioned idioms, both in-tree) | **(a)** Tailwind utilities + inline `style="…var(--mee-color-*)"` — `libs/composites/page-header/page-header.component.ts`; **(b)** `styles:[]` block with `:host{display:block}` + `var(--mee-space-*)` / `var(--mee-radius-*)` — `libs/composites/auth-layout/auth-layout.component.ts` |
| Signal-input + computed convention | `page-header.component.ts`: `input.required<string>()`, `input<T \| undefined>(undefined)`, `output<void>()`, `computed(() => …)` |
| Available design tokens (the layout palette) | spacing `--mee-space-1..10`; radius `--mee-radius-sm/md/lg/full`; shadow `--mee-shadow-sm/md/lg`; color `--mee-color-surface/bg/outline/outline-variant/on-surface/on-surface-muted/…`; transition `--mee-transition-fast/base/slow` |

**Reframe:** this is a **greenfield additive** phase inside one empty lib. There is nothing to migrate and no existing consumer to break (MFE adoption is Phase 6). The only risk surfaces are (a) accidentally importing PrimeNG/composites (FE-1/FE-4), and (b) the test-discovery glob (specs must live under `libs/layout/**` to be picked up).

---

## 2. The six page primitives (design — behavioral, builder writes literal TS)

> **§3.1-vs-§4 reconciliation (decision, recorded):** parent §3.1's `MEE_LAYOUT` row names five members ("page, section, toolbar, grid, form-layout") where **"grid" stands for the grid/stack pair**; parent §4 Phase 3 spells it "`mee-grid`/`mee-stack`". **Resolution: build six components — `mee-grid` and `mee-stack` are distinct siblings** (grid = 2-D auto-fill columns; stack = 1-D flex line with gap). Both go in `MEE_LAYOUT`. This is the natural reading of §4 and gives consumers both a column grid and a gap-stack without overloading one component. (Flagged in §10 for founder confirm — trivial.)

All six are **structural/presentational**: a host element + Tailwind/token layout + content projection. None imports PrimeNG, none imports a sibling UI lib, none holds state beyond `computed()` over its inputs. Selector prefix `mee-`. All `aria`/semantics are layout-neutral (a `<div>`/`<section>`/`<main>` host; meaningful labels come from projected content).

### 2.0 Shared authoring rules (apply to every primitive)

- `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush`.
- Host: `:host { display: block; }` (grid/stack may use `display: grid|flex` on host — see each).
- Inputs are **signal inputs** with explicit union/literal types and safe defaults; derive any class/style string with `computed()`.
- **Tailwind-driven layout** is the default idiom (flex/grid/max-width/padding/responsive `sm: md: lg:` prefixes). Where a value must come from a **design token** (gap/padding spacing), bind it via `[style.gap]`/`[style.padding]` to `var(--mee-space-N)` through a `computed()` map, **or** a Tailwind arbitrary value `[gap:var(--mee-space-4)]`. Builder picks whichever keeps the template readable; **record the choice in the PR**. Do NOT hard-code px for spacing that a token exists for.
- A `gap`/`padding`/`maxWidth` **size scale** is shared across primitives — use a single union type `MeeLayoutGap = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'` mapping to tokens:
  `none→0`, `xs→--mee-space-1`, `sm→--mee-space-2`, `md→--mee-space-4`, `lg→--mee-space-6`, `xl→--mee-space-8`. Define it **once** in `libs/layout/layout.types.ts` and import it into each primitive (keeps the surface consistent + greppable).
- Every primitive ships a co-located `*.spec.ts` (TestBed + `NoopAnimationsModule`, mirror `card.component.spec.ts`): asserts (1) creates, (2) projects content, (3) a representative input drives the expected host class/style.

### 2.1 `mee-page` — top-level page container
- **Selector:** `mee-page`. **Host:** `display:block`.
- **Purpose:** the outermost shell of a routed page — centers content at a max readable width, applies responsive horizontal padding, and provides vertical rhythm between its child sections.
- **Inputs:**
  - `maxWidth: 'sm' | 'md' | 'lg' | 'xl' | 'full'` (default `'lg'`) → maps to a max-width (`sm≈640px, md≈768px, lg≈1024px, xl≈1280px, full=none`). Use Tailwind `max-w-screen-sm/md/lg/xl` or `max-w-none`; center with `mx-auto`.
  - `padding: boolean` (default `true`) → responsive horizontal+vertical padding (`px-4 py-6 sm:px-6 lg:px-8`) when true; none when false.
  - `gap: MeeLayoutGap` (default `'lg'`) → vertical gap between projected blocks (host is a flex column or applies `space-y` via token).
- **Template:** single default `<ng-content />` inside a `<main class="… mx-auto w-full">` (host wraps; or host itself is the flex column). One projection slot.
- **Acceptance:** `<mee-page>` centers, `maxWidth="md"` narrows the container, `padding="false"` removes padding, children are vertically spaced by `gap`.

### 2.2 `mee-section` — titled content section
- **Selector:** `mee-section`. **Host:** `display:block`.
- **Purpose:** a labeled sub-region within a page (e.g. "Account details", "Recent catalogs").
- **Inputs:**
  - `heading: string | undefined` (default `undefined`) — when set, renders an `<h2>` (token color `--mee-color-on-surface`, `text-lg font-semibold`).
  - `description: string | undefined` (default `undefined`) — optional `<p>` under the heading (`text-sm`, `--mee-color-on-surface-muted`).
  - `gap: MeeLayoutGap` (default `'md'`) — vertical gap between the header block and the projected body.
- **Projection:** default `<ng-content />` for the section body. The heading/description render **only** when their input is set (`@if`).
- **Acceptance:** no heading input → no `<h2>` in DOM; heading set → `<h2>` with the text; body always projects.

### 2.3 `mee-toolbar` — horizontal action bar
- **Selector:** `mee-toolbar`. **Host:** `display:block`.
- **Purpose:** a horizontal bar with a leading region (title / filters) and a trailing region (actions/buttons), space-between, wrapping on small screens.
- **Inputs:**
  - `gap: MeeLayoutGap` (default `'sm'`) — gap between items.
  - `align: 'start' | 'center' | 'end'` (default `'center'`) — cross-axis alignment (`items-*`).
- **Projection — TWO named slots + default:**
  - default `<ng-content />` → the **start** (leading) region.
  - `<ng-content select="[mee-toolbar-end]" />` → the **end** (trailing) region, pushed right.
  - Layout: `flex flex-wrap items-center justify-between gap-…`; the end slot wrapped in a right-aligned flex container. (Mirror the named-slot pattern; the start slot is the default projection, the end slot is attribute-selected.)
- **Acceptance:** content in default slot sits left; `<div mee-toolbar-end>` content sits right; wraps below ~`sm`.

### 2.4 `mee-grid` — responsive 2-D grid
- **Selector:** `mee-grid`. **Host:** may be `display:grid` directly (cleanest) or wrap a grid `<div>`.
- **Purpose:** responsive card/tile grid.
- **Inputs:**
  - `cols: 'auto' | 1 | 2 | 3 | 4` (default `'auto'`) — `'auto'` → `grid-template-columns: repeat(auto-fill, minmax(<minItemWidth>, 1fr))`; a number → that many columns at `md+`, collapsing to 1 column below `sm` (mobile-first; Tirupur-seller mobile priority — see CLAUDE/Section-3 a11y notes).
  - `minItemWidth: string` (default `'16rem'`) — used only when `cols='auto'`.
  - `gap: MeeLayoutGap` (default `'md'`).
- **Template:** single default `<ng-content />`; grid applied on the host/wrapper. Use Tailwind `grid grid-cols-1 sm:grid-cols-2 …` for numeric cols, or a computed `gridTemplateColumns` style for `'auto'`.
- **Acceptance:** `cols=3` → three tracks at `md`, one at mobile; `cols='auto'` → auto-fill tracks ≥ `minItemWidth`; `gap` spacing applied.

### 2.5 `mee-stack` — 1-D flex line with gap
- **Selector:** `mee-stack`. **Host:** `display:flex` (or block wrapping a flex div).
- **Purpose:** lay out children in a single direction with a consistent gap — the workhorse spacer.
- **Inputs:**
  - `direction: 'vertical' | 'horizontal'` (default `'vertical'`) → `flex-col` / `flex-row`.
  - `gap: MeeLayoutGap` (default `'md'`).
  - `align: 'start' | 'center' | 'end' | 'stretch'` (default `'stretch'`) → `items-*`.
  - `justify: 'start' | 'center' | 'end' | 'between'` (default `'start'`) → `justify-*`.
  - `wrap: boolean` (default `false`) → `flex-wrap` (mostly for horizontal).
- **Template:** single default `<ng-content />`.
- **Acceptance:** `direction='horizontal'` lays children in a row; `gap='lg'` applies `--mee-space-6`; `justify='between'` spreads.

### 2.6 `mee-form-layout` — vertical form field layout
- **Selector:** `mee-form-layout`. **Host:** `display:block`.
- **Purpose:** a vertical column tuned for stacked form fields — consistent field gap, full-width fields, optional constrained reading width so long forms stay legible.
- **Inputs:**
  - `gap: MeeLayoutGap` (default `'lg'`) — vertical gap between fields (default `--mee-space-6`).
  - `maxWidth: 'sm' | 'md' | 'lg' | 'full'` (default `'md'`) — constrain the form column (`max-w-screen-sm` ≈ `'md'` here → builder maps to a sensible form width; a single-column form reads best ≤ ~560–640px) with `mx-auto` optional; default is left-aligned constrained.
- **Template:** single default `<ng-content />`; children stretch full width (`w-full` on the flex column).
- **Acceptance:** projected `mee-input`/fields stack with the field gap; column is width-constrained; works mobile-first.

> **Why `mee-form-layout` is distinct from `mee-stack`** (so the builder does not collapse them): `mee-stack` is a generic gap-line with no semantic; `mee-form-layout` encodes the *form* defaults (field gap, full-width children, reading-width cap) so a feature author writes `<mee-form-layout>` once instead of re-deriving the right `mee-stack` props per form. Keep both.

---

## 3. `MEE_LAYOUT` aggregator + barrel (the deliverable export)

### 3.0 Imports posture (FE-1/FE-4 proof)
The six primitives import **only** from `@angular/core` (`Component`, `ChangeDetectionStrategy`, `input`, `computed`, `Type`) and their local `./layout.types`. **No `primeng`, no `@primeuix`, no `@mesell/ui-kit`, no `@mesell/composites`.** This keeps FE-1 at 0 and FE-4 trivially clean (layout imports no sibling UI lib). If a future primitive needs an atom, route through `@mesell/ui-kit` (rank 0, allowed) — but Phase 3 needs none.

### 3.1 `MEE_LAYOUT` membership (6 components)
Mirror the ui-kit `aggregators.ts` typing idiom exactly (`as const satisfies readonly Type<unknown>[]`):

| Aggregator | Count | Members (barrel symbols) |
|---|---|---|
| `MEE_LAYOUT` | **6** | `MeePageComponent`, `MeeSectionComponent`, `MeeToolbarComponent`, `MeeGridComponent`, `MeeStackComponent`, `MeeFormLayoutComponent` |

`export const MEE_LAYOUT = [MeePageComponent, …] as const satisfies readonly Type<unknown>[];`
**This replaces** the Phase-0 placeholder `export const MEE_LAYOUT: readonly never[] = [] as const;`.

### 3.2 Barrel (`libs/layout/index.ts`)
- Keep the existing Phase-0 header doc comment (DAG explanation) — update the "TODO(Phase 3)" line to past tense ("Phase 3: page primitives shipped — see below") and **leave the "TODO(Phase 4): chrome primitives" line intact**.
- Add a `// Page primitives` block: one `export { MeeXxxComponent } from './xxx/xxx.component';` per primitive.
- Add a `// Public types` block: `export type { MeeLayoutGap } from './layout.types';` (+ any per-component literal types you choose to surface, e.g. `MeePageMaxWidth` — surface only what a consumer needs).
- Replace the placeholder `MEE_LAYOUT` with the populated aggregator (define it in a sibling `libs/layout/aggregators.ts` re-exported by the barrel — **mirror the ui-kit `aggregators.ts` precedent**; keeps the barrel a pure manifest). The aggregator's doc comment states the imports-vs-providers contract is N/A here (layout has no services) and that `MEE_LAYOUT` spreads alongside `MEE_FORM` etc.

---

## 4. Demo / usage doc (the "storybook/demo usage" deliverable)

Parent §4 requires "storybook/demo usage." There is **no Storybook harness in this repo** (no `.storybook/`, no `storybook` dep — verified). **Deliverable = a `libs/layout/README.md`** (mirror `libs/ui-kit/README.md`) with:
- One **usage code block per primitive** (copy-paste `@Component` snippets showing inputs + projection), e.g. a page composed of `mee-page > mee-section > mee-grid` and a `mee-toolbar` with an end slot, and a `mee-form-layout` wrapping `MEE_FORM` fields.
- The **`MEE_LAYOUT` spread pattern**: `imports: [...MEE_LAYOUT, ...MEE_FORM]`.
- The **`MeeLayoutGap` scale table** (size → token).
- A note that **MFE adoption is Phase 6** (primitives ship unused now) and **chrome is Phase 4**.

A runnable demo *component* is **out of scope** (it would land in `apps/**`, which Phase 3 must not touch). The README snippets are the demo surface; Phase 6 wires real consumers.

---

## 5. Files to create / edit (manifest)

| # | Path (relative to `frontend/`) | Action | Builder |
|---|---|---|---|
| L0 | `libs/layout/layout.types.ts` | **CREATE** — `MeeLayoutGap` union + the gap→token map helper (and any shared literal types) | component-builder |
| L1 | `libs/layout/page/page.component.ts` | **CREATE** — `MeePageComponent` | component-builder |
| L2 | `libs/layout/page/page.component.spec.ts` | **CREATE** | component-builder |
| L3 | `libs/layout/section/section.component.ts` | **CREATE** — `MeeSectionComponent` | component-builder |
| L4 | `libs/layout/section/section.component.spec.ts` | **CREATE** | component-builder |
| L5 | `libs/layout/toolbar/toolbar.component.ts` | **CREATE** — `MeeToolbarComponent` | component-builder |
| L6 | `libs/layout/toolbar/toolbar.component.spec.ts` | **CREATE** | component-builder |
| L7 | `libs/layout/grid/grid.component.ts` | **CREATE** — `MeeGridComponent` | component-builder |
| L8 | `libs/layout/grid/grid.component.spec.ts` | **CREATE** | component-builder |
| L9 | `libs/layout/stack/stack.component.ts` | **CREATE** — `MeeStackComponent` | component-builder |
| L10 | `libs/layout/stack/stack.component.spec.ts` | **CREATE** | component-builder |
| L11 | `libs/layout/form-layout/form-layout.component.ts` | **CREATE** — `MeeFormLayoutComponent` | component-builder |
| L12 | `libs/layout/form-layout/form-layout.component.spec.ts` | **CREATE** | component-builder |
| L13 | `libs/layout/aggregators.ts` | **CREATE** — `MEE_LAYOUT` (6) `as const satisfies readonly Type<unknown>[]` + doc comment | component-builder |
| L14 | `libs/layout/aggregators.spec.ts` | **CREATE (recommended)** — `MEE_LAYOUT.length === 6`, no-dup `new Set().size === 6`, each member present | component-builder |
| L15 | `libs/layout/index.ts` | **EDIT** — populate barrel: component re-exports + type re-exports + re-export `MEE_LAYOUT` from `./aggregators`; update Phase-3 TODO comment (keep Phase-4 TODO) | component-builder |
| L16 | `libs/layout/README.md` | **CREATE** — usage/demo doc (§4) | component-builder (ui-styler reviews snippets) |

> **No `apps/**`, no `libs/ui-kit/**`, no `libs/composites/**`, no scanner, no theme/token, no root-wiring, no CI/`ci.yml` change.** (Contrast P1, which edited `ci.yml` for the FE-2 flip — Phase 3 flips **no** contract, so **no CI/infra change** and **no `meesell-infra-builder` coordination** is required.)

---

## 6. Which specialist builds this + coordination (HYBRID)

**Primary builder: `meesell-angular-component-builder`** — Phase 3 is six standalone OnPush components + their specs + the typed aggregator + barrel. That is component territory (cf. P1, where the component-builder built `mee-icon`).

**Styling pass: `meesell-angular-ui-styler`** — parent §4 names "builder: component + ui-styler." After the component-builder lands structure, the ui-styler does a **review-and-polish pass**: verifies Tailwind responsive breakpoints (mobile-first for Tirupur sellers), token usage (no hard-coded px where a `--mee-space-*` exists), `gap`/`align`/`justify` correctness, and a11y-neutral semantics (`<main>`/`<section>`/`<h2>` where appropriate, no role traps). To avoid two agents racing the same files, dispatch is **sequential**: component-builder → (coordinator interim check) → ui-styler. The ui-styler edits the same primitive files for styling only — no API/input changes.

**No `meesell-angular-service-builder` work** — no services, no API client, no providers (layout has none).
**No infra coordination** — no `ci.yml`/scanner/branch-protection change in this phase.

**Coordinator (this session) runs the merge-gate** after the build: the §7 verification checklist is the gate; it can reject back to the specialist.

---

## 7. Verification checklist (merge-gate evidence the builder must attach to the PR)

1. **Type-check clean:** `npx tsc -p tsconfig.json --noEmit` → no errors. Proves signal-input types, the `MeeLayoutGap` union, and the `MEE_LAYOUT` `as const satisfies` typing hold.
2. **`MEE_LAYOUT` spreads into a throwaway standalone component** (load-bearing typing proof): a scratch `@Component({ standalone: true, imports: [...MEE_LAYOUT], template: '' })` compiles under `tsc` (may live transiently in `aggregators.spec.ts`; **not** committed to `apps/**`). Paste the passing compile.
3. **`MEE_LAYOUT` membership:** `aggregators.spec.ts` asserts `MEE_LAYOUT.length === 6` and `new Set(MEE_LAYOUT).size === 6` (no dup/omission). Paste the green line.
4. **Build green + budget:** `npx ng build frontend --configuration development` succeeds; build time **< 90 s** (CLAUDE Decision 12). **Bundle delta ≈ 0** for every existing entry point — no consumer imports a primitive yet (Phase 6), so the primitives tree-shake out. Paste the bundle line; flag any initial-bundle movement (must be none).
5. **Tests green, no count drop:** `npx ng test` (or the project test cmd) → P2-baseline count **+** the 6 component specs + `aggregators.spec.ts` (~7 new spec files). Confirm `libs/layout/**/*.spec.ts` are **discovered** (the `../../../libs/**/*.spec.ts` glob covers them — watch for the SP0 discovery gotcha). Paste the new green lines.
6. **FE contracts green (NO regression, NO scanner edit):** `cd frontend && node tools/contracts/run-all.mjs; echo $?` → all 5 **CLEAN**, exit `0`. Critically: **FE-1 = 0** (no PrimeNG import in `libs/layout/`) and **FE-4 = 0** (layout imports no `@mesell/composites`). Paste the summary table. (Phase 3 keeps warn-only mode; it flips no contract — but the table must show 0 across the board so Phase 5's strict flip stays clean.)
7. **Grep proofs (paste each):**
   - `grep -rE "primeng|@primeuix" libs/layout/` → **no matches** (FE-1 by construction).
   - `grep -rE "@mesell/composites" libs/layout/` → **no matches** (FE-4 by construction).
   - `grep -rn "pi pi-" libs/layout/` → **no matches** (no raw icons; FE-2 stays clean).
8. **Diff scope:** `git diff --stat` shows **only** files under `libs/layout/` + `docs/plans/architecture/UI_DS_PHASE3_SPEC.md`. **No `apps/**`, no other lib, no scanner, no theme, no root-wiring, no deletion.** Paste `git diff --stat`.
9. **Visual/a11y sanity (ui-styler):** confirm mobile-first collapse (grid → 1 col, toolbar wraps), token-driven spacing, and that headings use semantic tags. Note any screenshot or DOM-class evidence.

---

## 8. Out-of-scope (explicit — refuse if asked in Phase 3)

- **Chrome primitives** (`mee-app-bar`/`mee-side-nav`/`mee-nav-item`/`mee-user-menu`) + the `apps/shell` `ShellComponent` refactor — **Phase 4**.
- **Moving `auth-layout`** out of `@mesell/composites` — deferred (parent §7).
- **MFE / app / shell / feature adoption** of the primitives (changing any `imports:` to use `MEE_LAYOUT`) — **Phase 6**. Primitives ship unused.
- **Flipping any contract to strict / making the FE Gate required / editing any scanner or `ci.yml`** — Phases 4/5.
- **New components beyond the six**, pipes/directives (parent §7 — none until a concrete need), theme/preset/token edits, new npm deps, a Storybook harness, a runnable demo component in `apps/**`.
- **Backend / k8s; `docs/FRONTEND_ARCHITECTURE.md`** (LOCKED).
- **Importing PrimeNG/@primeuix into `@mesell/layout`** — forbidden by FE-1; route any atom need through `@mesell/ui-kit`.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| A primitive accidentally imports PrimeNG (FE-1 red at Phase 5) | §3.0 imports-posture: primitives import only `@angular/core` + local types; §7.7 grep proof catches it. |
| Layout imports composites (FE-4 back-edge) | Pure primitives need no sibling lib; §7.7 grep proof. |
| `mee-stack` and `mee-form-layout` collapse into one | §2.6 rationale: keep both (generic gap-line vs form-semantic defaults). |
| Tailwind arbitrary-value vs `style`-binding inconsistency | §2.0: one shared `MeeLayoutGap`→token map; builder records the chosen idiom in the PR. |
| Specs not discovered (silent 0-new-tests) | §7.5: confirm new spec count rises; specs live under `libs/layout/**`. |
| ui-styler & component-builder race the same files | §6: **sequential** dispatch (component → ui-styler), coordinator interim check between. |

---

## 10. Decisions for the master session / founder to confirm before the build step

1. **[CONFIRM — grid+stack = 6 components] §2 reconciliation:** parent §3.1 says five (grid covers grid/stack); §4 says `mee-grid`/`mee-stack`. **Recommendation: build six (grid and stack distinct), both in `MEE_LAYOUT`.** Trivial — confirm or collapse to a single `mee-grid`.
2. **[CONFIRM — demo = README, no Storybook] §4:** no Storybook harness exists; recommendation is a `libs/layout/README.md` with per-primitive usage snippets (mirrors `libs/ui-kit/README.md`), and **no** runnable demo component (would breach the no-`apps/**` guardrail). Confirm.
3. **[CONFIRM — aggregator in sibling file] §3.3:** define `MEE_LAYOUT` in `libs/layout/aggregators.ts` re-exported by the barrel (mirrors ui-kit P2). Confirm or inline into `index.ts`.
4. **[CONFIRM — styling idiom] §2.0:** Tailwind-driven, with token spacing via `[style.gap]`→`var(--mee-space-N)` **or** Tailwind arbitrary `[gap:var(--mee-space-4)]`, builder's call recorded in the PR. The non-negotiable invariant: **no PrimeNG import, no hard-coded px where a token exists, mobile-first.** Confirm the builder's-discretion latitude is acceptable.
5. **[NOTE — no contract flip / no infra touch]** Phase 3 flips no contract and edits no `ci.yml`/scanner — so (unlike P1) no `meesell-infra-builder` coordination. Confirm.

---

*End of Phase 3 BUILD SPEC. Next HYBRID step: this session dispatches `meesell-angular-component-builder` with this spec (build the six primitives + aggregator + barrel + README), runs an interim coordinator check, dispatches `meesell-angular-ui-styler` for the responsive/token/a11y polish pass, then `meesell-frontend-coordinator` runs the §7 merge-gate and opens the PR for the founder to merge.*

End the eventual commit body with:
Co-Authored-By: Claude Opus 4.8 (1M context)
