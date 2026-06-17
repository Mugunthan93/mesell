# UI Design-System Decoupling — Phase 2 BUILD SPEC (Aggregators)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-16
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §3 decision #1, §3.1 (aggregator groups), §4 "Phase 2 — Aggregators".
**Preconditions (both MERGED to develop — this spec authors against develop tip, not the planning branch):**
- **P0 `c6e08865`** — `@mesell/layout` skeleton (empty `MEE_LAYOUT`), `frontend/tools/contracts/` (5 scanners + `run-all.mjs`, FE-2 strict, FE-1/3/4/5 warn-only), non-blocking `FE Gate: lint (5 contracts)` CI job.
- **P1 `d635aed3`** — `mee-icon` + `MEE_ICONS` registry (sole raw-`pi` file); all icon call-sites on `MeeIconName`; `MeeIconComponent` + `MeeIconName` barrel-exported from `libs/ui-kit/index.ts`. **This made the ui-kit barrel a 21-component surface** (icon is the new 21st).

**Phase 2 mandate (verbatim from parent §4):** "Add grouped aggregator arrays to `ui-kit/index.ts` (`MEE_FORM`…`MEE_COMMON`, `MEE_FILE`, `MEE_UI_ALL`). Document the two-pronged contract (aggregator arrays for `imports`, `provideMeeUi()` for providers). Deliverable: aggregators exported + documented. (MFE migration deferred to Phase 6.)"

---

## 0. Hard guardrails for this phase

1. **DEFINE + EXPORT + DOCUMENT only.** Phase 2 adds the aggregator arrays and their documentation. It changes **ZERO** MFE/app/shell import statements — no `imports: [...MEE_FORM]` adoption anywhere. That sweep is **Phase 6** (parent §4). A diff touching any `apps/**` or feature component's `imports:` array is out of scope and must be rejected at review.
2. **No new components / primitives.** Aggregators are arrays of **already-exported** classes. No new `mee-*` wrapper. No registry change.
3. **`MEE_LAYOUT` stays empty and stays in `@mesell/layout`.** Do **NOT** add a `MEE_LAYOUT` array to `@mesell/ui-kit`. The layout aggregator is owned by `@mesell/layout` and is populated in Phases 3–4 (parent §3.1 footnote: "*from `@mesell/layout`*"). `MEE_UI_ALL` is the spread of the **six ui-kit groups only** — it does **not** include layout.
4. **Services are NOT components — they MUST NOT appear in any aggregator array.** `MeeToastService` + `MeeConfirmService` stay **providers** (supplied at root via `provideMeeUi()` in `app.config.ts`). An aggregator array is for a standalone component's `imports: [...]`; a provider in an `imports` array is an Angular error. This is the single most important correctness invariant — see §3 and §4.
5. **No theme / preset / icon / registry change.** Do not touch `theme.ts`, `providers.ts`, `styles.css`, `icon/`, or any preset.
6. **No new npm deps.**
7. **No contract flips.** FE-1/3/4/5 stay warn-only; FE-2 stays strict. Phase 2 introduces no `pi pi-`, no PrimeNG import outside ui-kit, no deep-path or cross-MFE import — so all 5 scanners stay green with no scanner edit.
8. **No backend / k8s / LOCKED-doc edits.** `docs/FRONTEND_ARCHITECTURE.md` is LOCKED — no §2 boundary-doc edit here.
9. **Standalone Angular only.** No NgModules.
10. **Additive, tiny diff.** Net effect = one new file (or one barrel block) + one doc + one optional spec. No deletions, no behavior change, no bundle change for any consumer that does not yet import an aggregator (P6).

---

## 1. Measured baseline — the membership source of truth (verified 2026-06-16 against `origin/develop`)

The authoritative surface is the **post-P1 barrel** `frontend/libs/ui-kit/index.ts` on develop. It exports **21 component classes + 2 services + 2 provider/util fns + types**. The aggregators group **exactly the 21 component classes**; the 2 services are excluded (they are providers).

### 1.1 The 21 component classes (the complete aggregator universe)

| # | Barrel symbol | Source module | Group assigned (§1.2) |
|---|---|---|---|
| 1 | `MeeIconComponent` | `./icon/icon.component` | `MEE_COMMON` |
| 2 | `MeeButtonComponent` | `./button/button.component` | `MEE_COMMON` |
| 3 | `MeeInputComponent` | `./input/input.component` | `MEE_FORM` |
| 4 | `MeeOtpInputComponent` | `./otp-input/otp-input.component` | `MEE_FORM` |
| 5 | `MeeBadgeComponent` | `./badge/badge.component` | `MEE_FEEDBACK` |
| 6 | `MeeCardComponent` | `./card/card.component` | `MEE_COMMON` |
| 7 | `MeeTableComponent` | `./table/table.component` | `MEE_DATA` |
| 8 | `MeeDialogComponent` | `./dialog/dialog.component` | `MEE_OVERLAY` |
| 9 | `MeeFileUploadComponent` | `./file-upload/file-upload.component` | `MEE_FILE` |
| 10 | `MeeStepsComponent` | `./steps/steps.component` | `MEE_DATA` |
| 11 | `MeeSelectComponent` | `./select/select.component` | `MEE_FORM` |
| 12 | `MeeTreeSelectComponent` | `./tree-select/tree-select.component` | `MEE_FORM` |
| 13 | `MeeSkeletonComponent` | `./skeleton/skeleton.component` | `MEE_FEEDBACK` |
| 14 | `MeeProgressBarComponent` | `./progress-bar/progress-bar.component` | `MEE_FEEDBACK` |
| 15 | `MeeSpinnerComponent` | `./spinner/spinner.component` | `MEE_FEEDBACK` |
| 16 | `MeeToastComponent` | `./toast/toast.component` | `MEE_FEEDBACK` |
| 17 | `MeeConfirmDialogComponent` | `./confirm-dialog/confirm-dialog.component` | `MEE_OVERLAY` |
| 18 | `MeePasswordInputComponent` | `./password-input/password-input.component` | `MEE_FORM` |
| 19 | `MeeTextareaComponent` | `./textarea/textarea.component` | `MEE_FORM` |
| 20 | `MeeDrawerComponent` | `./drawer/drawer.component` | `MEE_OVERLAY` |
| 21 | `MeeMenuComponent` | `./menu/menu.component` | `MEE_COMMON` |

### 1.2 EXCLUDED from every aggregator (providers + non-class exports)

| Barrel symbol | Why excluded |
|---|---|
| `MeeToastService` | **Provider** (root, via `provideMeeUi()`). Never in an `imports` array. |
| `MeeConfirmService` | **Provider** (root, via `provideMeeUi()`). Never in an `imports` array. |
| `provideMeeUi` | Provider fn (root bootstrap). |
| `MeeSellPreset` | Theme constant (consumed by `provideMeeUi`). |
| all `MeeXxx` **types** | Type-only exports — not runtime values, not importable into a component. |

> **Provenance fact the builder must honor:** `MeeToastComponent` (a component, line 16) and `MeeToastService` (a provider, line 18) are two distinct exports from the same `toast/` folder; likewise `MeeConfirmDialogComponent` (line 19) vs `MeeConfirmService` (line 19, re-exported from the same file). The **Component** goes in the aggregator; the **Service** does not. Do not conflate them.

---

## 2. Mapped membership — the seven arrays (exact, mapped to barrel symbols)

Each member is named by its **exact barrel export symbol** (§1.1). Mapping uses the parent §3.1 plain-name table; the resolution from plain name → symbol is given so the builder copies no guesswork.

| Aggregator | Count | Plain names (parent §3.1) | Exact barrel symbols |
|---|---|---|---|
| **`MEE_FORM`** | **6** | input, textarea, select, treeselect, password, otp | `MeeInputComponent`, `MeeTextareaComponent`, `MeeSelectComponent`, `MeeTreeSelectComponent`, `MeePasswordInputComponent`, `MeeOtpInputComponent` |
| **`MEE_OVERLAY`** | **3** | dialog, drawer, confirm-dialog | `MeeDialogComponent`, `MeeDrawerComponent`, `MeeConfirmDialogComponent` |
| **`MEE_FEEDBACK`** | **5** | toast, badge, skeleton, spinner, progress-bar | `MeeToastComponent`, `MeeBadgeComponent`, `MeeSkeletonComponent`, `MeeSpinnerComponent`, `MeeProgressBarComponent` |
| **`MEE_DATA`** | **2** | table, steps | `MeeTableComponent`, `MeeStepsComponent` |
| **`MEE_COMMON`** | **4** | button, card, menu, **icon** | `MeeButtonComponent`, `MeeCardComponent`, `MeeMenuComponent`, `MeeIconComponent` |
| **`MEE_FILE`** | **1** | file-upload | `MeeFileUploadComponent` |
| **`MEE_UI_ALL`** | **21** | spread of all six groups (escape hatch) | `[...MEE_FORM, ...MEE_OVERLAY, ...MEE_FEEDBACK, ...MEE_DATA, ...MEE_COMMON, ...MEE_FILE]` |

**Coverage proof (the builder must reproduce as a comment + as the §5 spec assertion):**
`6 + 3 + 5 + 2 + 4 + 1 = 21` = the exact component-class count in §1.1. **Every one of the 21 classes appears in exactly one of the six concern groups — no class omitted, no class duplicated.** `MEE_UI_ALL.length === 21`. The 2 services are in **zero** groups.

> **`MEE_OVERLAY` includes `confirm-dialog` (the Component), not `MeeConfirmService`.** `MEE_FEEDBACK` includes `toast` (the Component), not `MeeToastService`. This is the §1.2 component-vs-service split applied to the two dual-export folders.

> **No `MEE_LAYOUT` here.** Parent §3.1 lists `MEE_LAYOUT` (page, section, toolbar, grid, form-layout) but explicitly sources it `from @mesell/layout`. It is **out of scope** for this ui-kit phase and is **not** part of `MEE_UI_ALL` (which is "spread of all **ui-kit** groups"). Adding it here would (a) create a phantom cross-lib re-export and (b) reference primitives that do not exist until Phases 3–4.

---

## 3. File placement decision (RECOMMENDED + justified)

**Recommendation: a NEW sibling file `frontend/libs/ui-kit/aggregators.ts`, re-exported by the barrel `index.ts`.** Not inline-in-the-barrel.

**Justification:**
1. **Single-responsibility barrel.** `index.ts` is a pure re-export manifest (one line per symbol). The aggregators are *authored values* (arrays with member references + a doc comment block) — authored code belongs in a module, the barrel stays a manifest. This mirrors the P1 precedent where `icon.registry.ts` (authored values) is a separate file the barrel merely re-exports.
2. **The services-are-providers doc block (§4) needs a home.** A multi-line comment-block contract reads naturally at the top of a dedicated `aggregators.ts`; it would clutter the manifest barrel.
3. **`MEE_UI_ALL` references the other six arrays.** Defining all seven in one cohesive module (where `MEE_UI_ALL` spreads the locally-declared arrays) is cleaner than scattering or forward-referencing inside a re-export file.
4. **Future-proof for `MEE_LAYOUT`.** When `@mesell/layout` ships its own `aggregators.ts` (Phases 3–4), the two libs mirror each other's structure — predictable, greppable.

**Barrel wiring:** `index.ts` gains a re-export of the seven arrays, e.g. a single block `export { MEE_FORM, MEE_OVERLAY, MEE_FEEDBACK, MEE_DATA, MEE_COMMON, MEE_FILE, MEE_UI_ALL } from './aggregators';` placed under a new `// Aggregators (for component imports — NOT providers)` comment. (`export *` is acceptable too, but the explicit named re-export keeps the barrel self-documenting.)

---

## 4. Typing decision (RECOMMENDED + worked example)

**Decision: type each array as `readonly Type<unknown>[]` (or the project's component-array idiom) and declare it with `as const` member-by-member is NOT required — but the array binding itself should be `export const MEE_FORM = [...] as const`-free.** Concretely, the recommended shape:

- Each group: `export const MEE_FORM = [MeeInputComponent, /* … */] as const satisfies readonly Type<unknown>[];`
  - **`as const`** makes the array a fixed-length readonly tuple — good for the `MEE_UI_ALL.length === 21` invariant and prevents accidental mutation/`.push`.
  - **`satisfies readonly Type<unknown>[]`** (import `Type` from `@angular/core`) keeps the elements constrained to Angular component classes **without widening** the tuple type — so spreading still works and a non-component slipping in is a compile error.
- `MEE_UI_ALL`: `export const MEE_UI_ALL = [...MEE_FORM, ...MEE_OVERLAY, ...MEE_FEEDBACK, ...MEE_DATA, ...MEE_COMMON, ...MEE_FILE] as const;` — spreads the six tuples into one.

**Why this spreads correctly into Angular `imports`:** Angular's standalone `imports` accepts `(Type | readonly any[])[]` and recursively flattens, but the **clean, idiomatic** consumer pattern is the spread `imports: [...MEE_FORM]`. A `readonly` `as const` tuple spreads into a mutable array literal without error (spread copies elements; the target literal is fresh and mutable). The `satisfies Type<unknown>[]` constraint guarantees every spread element is a valid standalone import. **The builder MUST prove the spread compiles** (§6 checklist item 2) — this is the one place a typing choice can bite.

> **Fallback if `as const satisfies` proves awkward with the project's TS config:** plain `export const MEE_FORM: readonly Type<unknown>[] = [MeeInputComponent, …];` is acceptable. It loses the fixed-length tuple (so the `.length === 21` test asserts a runtime value, still fine) but spreads identically. The builder picks whichever keeps `tsc` clean and the spread valid; record the choice in the PR body. **Do NOT** type them as plain `any[]` (loses the component-class guarantee) and **do NOT** type them mutable-without-readonly (invites a consumer `.push`).

### 4.1 Worked usage example (DOC-ONLY — goes in the doc/comment, NOT applied to any real component in Phase 2)

```ts
// A standalone feature component would consume aggregators like this (Phase 6, illustrative only):
import { Component } from '@angular/core';
import { MEE_FORM, MEE_FEEDBACK } from '@mesell/ui-kit';

@Component({
  selector: 'app-example',
  standalone: true,
  imports: [...MEE_FORM, ...MEE_FEEDBACK],   // spreads 6 + 5 = 11 component classes
  template: `…`,
})
export class ExampleComponent {}
```

```ts
// Providers stay SEPARATE — in app.config.ts, NOT in any component imports:
import { provideMeeUi } from '@mesell/ui-kit';   // wraps MeeToastService + MeeConfirmService + theme
export const appConfig: ApplicationConfig = {
  providers: [ ...provideMeeUi() /* , … */ ],
};
// MeeToastService / MeeConfirmService are injected from this root provision —
// they NEVER appear in an aggregator array.
```

> **Bundle/lean-import note (carry-forward from the PR#38 bundle gotcha):** importing aggregators from the barrel pulls the referenced component classes. This is fine for **feature** components (lazy chunks) but the **root** (`app.config.ts`/`main.ts`) must continue to deep-import `provideMeeUi` from `@mesell/ui-kit/providers` and must **never** import an aggregator (a root aggregator import would drag wrappers into the initial bundle and breach the 1 MB budget). Phase 2 ships **no** consumer, so this is a documented guardrail for Phase 6, not an action here.

---

## 5. Services-are-providers documentation (MANDATORY deliverable)

Per parent §4 "Document the two-pronged contract." Two surfaces, both required:

1. **A comment block at the top of `aggregators.ts`** stating verbatim the contract:
   - Aggregator arrays are for a standalone component's `imports: [...]` ONLY.
   - `MeeToastService` and `MeeConfirmService` are **providers**, supplied at root via `provideMeeUi()` in `app.config.ts`. They are deliberately **absent** from every array. Putting a service in `imports` is an Angular error.
   - `MEE_UI_ALL` is the escape hatch (all six ui-kit groups); prefer the concern-scoped groups for tree-shaking. `MEE_LAYOUT` is **not** here — it lives in `@mesell/layout`.
2. **A short note in a `libs/ui-kit/README.md`** (CREATE — there is no ui-kit README on develop today). A new `## Aggregators` section: the seven arrays + counts, the imports-vs-providers split, the one-line "services stay in `provideMeeUi()`" rule, and a pointer that MFE adoption is Phase 6. **Alternatively** append the same section to `frontend/tools/contracts/README.md` (which already documents the design-system decoupling). **Recommendation: a dedicated `libs/ui-kit/README.md`** — it co-locates the doc with the library it documents and is the natural home a future MFE author greps. (Builder may instead extend `tools/contracts/README.md` if the Lead prefers a single doc surface — record the choice.)

---

## 6. Files to create / edit (manifest)

| # | Path (relative to `frontend/`) | Action | Builder |
|---|---|---|---|
| A1 | `libs/ui-kit/aggregators.ts` | **CREATE** — the 7 arrays (§2) + typing (§4) + services-are-providers comment block (§5.1) | service-builder |
| A2 | `libs/ui-kit/index.ts` | **EDIT (additive)** — re-export the 7 arrays under a new `// Aggregators` block (§3). No other line changes. | service-builder |
| A3 | `libs/ui-kit/README.md` | **CREATE** — `## Aggregators` doc section (§5.2). *(Or extend `tools/contracts/README.md` — Lead's call.)* | service-builder |
| A4 | `libs/ui-kit/aggregators.spec.ts` | **CREATE (recommended, tiny)** — membership + length + no-service assertions (§6.1) | service-builder |

> **No root-wiring change.** `app.config.ts`, `app.routes.ts`, `main.ts`, `index.html` are **untouched** (Frontend Lead confirms). **No `apps/**` change** (Phase 6). **No scanner change** (Phase 2 introduces no contract-relevant import). **No theme/registry/preset change.**

### 6.1 The optional spec (A4) — recommended assertions

A Vitest spec (no TestBed needed — these are static value assertions; follow the lightweight pattern). Assert:
- `MEE_FORM.length === 6`, `MEE_OVERLAY.length === 3`, `MEE_FEEDBACK.length === 5`, `MEE_DATA.length === 2`, `MEE_COMMON.length === 4`, `MEE_FILE.length === 1`.
- `MEE_UI_ALL.length === 21`.
- The union of the six groups has **no duplicates** (`new Set(MEE_UI_ALL).size === 21`).
- `MEE_COMMON` includes `MeeIconComponent` (the P1 addition — explicit guard so a future barrel edit can't silently drop it).
- **Neither `MeeToastService` nor `MeeConfirmService` is referenceable in any array** — assert by importing both and checking `MEE_UI_ALL` does not `.includes` them (compile-time this is already impossible if typing is `Type<unknown>`, but the runtime assertion documents intent and survives a typing regression).

---

## 7. Which specialist builds this + coordination

**Primary builder: `meesell-angular-service-builder`.**

**Justification:** Phase 2 has **no new component, no template, no styling, no UI behavior**. It is a **barrel / exports / typing surface** — declaring typed constant arrays, wiring a re-export, and writing a `satisfies Type<unknown>[]` typing contract + a docs section. That is library-plumbing and TypeScript-typing work, the service-builder's lane (it owns typed surfaces, the `ApiClient`, exports/structure). The `meesell-angular-component-builder` is the wrong fit precisely because **nothing is a component here** — P1 (which created `mee-icon`, an actual component) correctly used the component-builder; P2 creates no component. `meesell-angular-ui-styler` has zero work (no styling, no theme, no a11y surface — arrays of class references render nothing).

**Coordination:** **none required.** No infra touch (no `ci.yml` change — scanners unchanged, no new required check). No cross-lead memo (no backend/ai/infra/data contract surface). This is a self-contained frontend-internal additive change. (Contrast P1, which needed `meesell-infra-builder` for the `ci.yml` `--strict=fe2` flip — P2 has no such edit.)

---

## 8. Out-of-scope (explicit — refuse if asked in Phase 2)

- **MFE / app / shell / feature adoption** — changing any component's `imports:` to use an aggregator is **Phase 6**. Phase 2 ships the arrays unused.
- **`MEE_LAYOUT`** — owned by `@mesell/layout`, populated Phases 3–4; not added to ui-kit, not in `MEE_UI_ALL`.
- **Layout / chrome primitives** (`mee-page`/`mee-app-bar`/etc.) — Phases 3–4.
- **Flipping any contract** — FE-1/3/4/5 stay warn-only; FE-2 stays strict; no scanner edit; no required-check change.
- **New components / wrappers / registry entries / theme / preset / styles / npm deps.**
- **Root wiring** (`app.config.ts`/`app.routes.ts`/`main.ts`/`index.html`).
- **Backend / k8s; `docs/FRONTEND_ARCHITECTURE.md`** (LOCKED).
- **Putting `MeeToastService`/`MeeConfirmService` (or `provideMeeUi`/`MeeSellPreset`) into any array** — they are providers/constants, excluded by design (§1.2).

---

## 9. Verification checklist (merge-gate evidence the builder must attach)

The PR body must show:

1. **Type-check clean:** `./node_modules/.bin/tsc -p tsconfig.json --noEmit` → no errors. Proves the `satisfies Type<unknown>[]` typing holds and `MEE_UI_ALL`'s spread type-checks.
2. **Aggregators spread into a throwaway standalone component without error** (the load-bearing proof): a scratch `@Component({ standalone: true, imports: [...MEE_FORM, ...MEE_FEEDBACK], template: '' })` compiles under `tsc` (may live transiently in the spec file or a tsc-only fixture; **not** committed to `apps/**`). Paste the passing compile. This is the one check that catches a bad typing choice.
3. **`MEE_UI_ALL.length === total component count:`** the A4 spec asserts `=== 21` and `new Set(MEE_UI_ALL).size === 21` (no dup/no omission). Paste the green test line. Cross-check: `6+3+5+2+4+1 = 21` = §1.1 barrel component count.
4. **Per-group counts:** A4 asserts `6/3/5/2/4/1`. Paste green.
5. **No service in any array:** A4 asserts neither `MeeToastService` nor `MeeConfirmService` is in `MEE_UI_ALL`. Paste green. (And `grep`-confirm the two service symbols appear in `aggregators.ts` **only** inside the doc-comment, never in an array literal.)
6. **FE Gate still green (no scanner regression):** `cd frontend && node tools/contracts/run-all.mjs --strict=fe2; echo $?` → **`0`** (FE-2 strict still 0 violations; FE-1/3/4/5 still warn-only/clean). Phase 2 adds no `pi pi-`, no PrimeNG import outside ui-kit, no deep/cross-MFE import — so all 5 stay green with **zero scanner edit**. Paste the summary table.
7. **Build green + budget:** `./node_modules/.bin/ng build frontend` (or `pnpm build`) succeeds; build time **< 90 s** (CLAUDE.md Decision 12 — expected ~3 s). **Bundle delta ≈ 0** for every existing entry point — because **no consumer imports an aggregator yet** (Phase 6), the arrays are dead code that tree-shakes out of every current bundle. Paste the bundle line; flag if the initial bundle moved at all (it must not).
8. **Tests green, no count drop:** `pnpm test` → P1-baseline count **+** the new `aggregators.spec.ts` (expect ~+6 assertions in 1 new file). No drop = no silent non-discovery (watch the `../apps/**` + `../libs/**` discovery globs per the SP0 test-discovery gotcha — `libs/ui-kit/aggregators.spec.ts` must be discovered).
9. **Diff is additive-only and matches the A1–A4 manifest:** `git diff --stat` shows **only** `libs/ui-kit/aggregators.ts` (new), `libs/ui-kit/index.ts` (additive re-export block — no existing line changed), `libs/ui-kit/README.md` (new, or the `tools/contracts/README.md` extension), `libs/ui-kit/aggregators.spec.ts` (new). **No `apps/**`, no scanner, no theme, no root-wiring, no LOCKED-doc, no deletion.** Paste `git diff --stat`.
10. **`index.ts` barrel diff is purely additive:** `git diff libs/ui-kit/index.ts` shows ONLY the new `// Aggregators` re-export block appended — no existing component/service/type re-export line touched.

---

## 10. Risks / decisions for the master session to confirm before the build step

1. **[CONFIRM — file placement] `aggregators.ts` sibling vs inline barrel (§3).** Recommendation: **sibling `aggregators.ts`** re-exported by the barrel (matches the P1 `icon.registry.ts` precedent; keeps the barrel a pure manifest; gives the services-are-providers comment block a home). Low-stakes — confirm or override to inline.
2. **[CONFIRM — typing] `as const satisfies readonly Type<unknown>[]` vs plain `readonly Type<unknown>[]` (§4).** Recommendation: try `as const satisfies` first (fixed-length tuple + component-class guarantee), fall back to plain `readonly Type<unknown>[]` if the project TS config makes `as const satisfies` awkward. **The non-negotiable invariant is: the array spreads into `imports: [...MEE_FORM]` and `tsc` stays clean** (checklist item 2) — the exact annotation is the builder's call within those two constraints. Confirm the fallback is acceptable.
3. **[CONFIRM — doc home] dedicated `libs/ui-kit/README.md` vs extending `tools/contracts/README.md` (§5.2).** Recommendation: **new `libs/ui-kit/README.md`** (co-located with the lib). Trivial — confirm or redirect to the existing contracts README.
4. **[NON-OBVIOUS — services exclusion] The two dual-export folders** (`toast/` → Component+Service; `confirm-dialog/` → Component+Service). The **Component** goes in `MEE_FEEDBACK`/`MEE_OVERLAY`; the **Service** is excluded (provider). Confirm the builder is told explicitly so it does not mistakenly add `MeeToastService`/`MeeConfirmService` to an array (the §6.1/§9.5 assertion guards this, but flag it up-front).
5. **[NO LAYOUT] `MEE_LAYOUT` is deliberately NOT in this phase and NOT in `MEE_UI_ALL`** (§2 note). Parent §3.1 lists it but sources it from `@mesell/layout` (Phases 3–4). Confirm the master session agrees `MEE_UI_ALL` = the six ui-kit groups only (21 classes), with layout's aggregator landing later in its own lib.

---

*End of Phase 2 BUILD SPEC. Next HYBRID step: master session dispatches `meesell-angular-service-builder` with this spec; `meesell-frontend-coordinator` then runs the merge-gate review (no infra sign-off needed — no `ci.yml`/scanner change in this phase).*
