# UI Design-System Decoupling — Phase 6a BUILD SPEC (`mee-page` padding parity tweak)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-17
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DS_PHASE6_SUBPLAN.md` → §4 "Phase 6a — `mee-page` padding parity tweak". Founder pick: **A + 6a + pricing pilot** (6a is the prerequisite primitive tweak that ships **first, as its own PR**, before the pilot).
**Grandparent:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` §4 Phase 6.
**Prior-phase idiom reference:** `docs/plans/architecture/UI_DS_PHASE3_SPEC.md` (this SPEC matches its structure/altitude; Phase 3 built `mee-page` + the layout primitives — see `.claude/agent-memory/meesell-frontend-coordinator/ui_ds_phase3.md`).
**Worktree:** `/tmp/mesell-wt/ui-ds-phase6a` on branch `feat/ui-ds-phase6a` (per-phase worktree off `origin/develop`). One phase = one worktree = one branch = one PR. **NEVER git in the master tree** (Phase-3 contamination lesson).

---

## 0. Hard guardrails for this phase

1. **`@mesell/layout` is the only library touched — and only TWO files of it carry logic.** Phase 6a edits exactly `frontend/libs/layout/layout.types.ts` (+1 type) and `frontend/libs/layout/page/page.component.ts` (the `padding` input + `hostClass()`), and updates `frontend/libs/layout/page/page.component.spec.ts`. **Zero `apps/**` edits, zero MFE edits, zero other-lib edits, zero other-primitive edits.** A diff touching any MFE/app, `mee-form-layout`, or any other primitive is out of scope and must be **rejected at review**.
2. **BACKWARD-COMPATIBLE, ADDITIVE ONLY.** The boolean `padding` input MUST keep working unchanged. `true` and `'default'` MUST resolve to the **byte-identical** current class string `px-4 py-6 sm:px-6 lg:px-8`. `false` and `'none'` MUST resolve to `''` (no padding) exactly as today. **No existing behaviour changes** — the only new capability is the `'tight'` value. This is a non-breaking API widening with **zero consumers** (`@mesell/layout` has no consumers on develop), so there is nothing to migrate.
3. **The strict FE Gate (5 contracts) must stay GREEN — and this change cannot touch it.** 6a is an additive type + an internal class-resolution change. It adds **no import** (no `primeng`, no `@primeuix`, no `pi pi-`, no `@mesell/composites`, no sibling UI lib, no new npm dep). FE-1/FE-2/FE-3/FE-4/FE-5 stay at **0 violations** by construction. **Do NOT edit any scanner, `run-all.mjs`, or `ci.yml`** — Phase 6a flips no contract.
4. **No new design tokens, no theme/preset edit, no `styles.css`, no providers.** The class strings are literal Tailwind utilities already in use today (they are baked into `mee-page`'s current `hostClass()`); 6a re-shapes how they are *selected*, it does not introduce a new spacing value. Do not touch `libs/design-tokens/_tokens.css`, `libs/ui-kit/theme.ts`, or `providers.ts`.
5. **Standalone Angular 21 only** — `mee-page` stays `standalone: true`, `ChangeDetectionStrategy.OnPush`, signal inputs (`input()`), `computed()` for derived class. No NgModule, no `@Input()` decorator, no structural rewrite. Touch only the `padding` input declaration and the `hostClass()` computed body.
6. **`mee-page`'s OTHER inputs and template are FROZEN.** `maxWidth`, `gap`, `gapValue()`, the `<div [class] [style.gap]>` template, the `:host { display: block; }` style, the WCAG `<div>`-not-`<main>` landmark decision, and the doc-comment landmark note — **all unchanged**. Only the `padding` input's type + the padding branch of `hostClass()` change. (Update the `padding` JSDoc to describe the new scale; do not alter the landmark JSDoc.)
7. **`mee-form-layout` is NOT touched in 6a.** Its `maxWidth` scale + token gap already cover the form parity cases; parity is **confirmed during the pricing pilot, not pre-emptively widened here**. Any change to `form-layout.component.ts` / `MeeFormMaxWidth` is **out of scope** — reject if present.
8. **Additive, self-contained diff.** No deletions of existing assertions; no edits outside the three named files + this SPEC doc. No README change required (the `mee-page` usage snippet in `libs/layout/README.md` shows `[padding]="true"` which **still works**; optionally add a one-line `padding="tight"` note — **builder's discretion, additive only**).

---

## 1. Measured baseline (verified 2026-06-17 against `develop`)

| Fact | Evidence (from `develop`) |
|---|---|
| `mee-page` `padding` input is **boolean**, default `true` | `frontend/libs/layout/page/page.component.ts`: `readonly padding = input<boolean>(true);` |
| `hostClass()` padding branch (the **exact** current strings) | `const pad = this.padding() ? 'px-4 py-6 sm:px-6 lg:px-8' : '';` then `return \`flex flex-col w-full mx-auto ${mw} ${pad}\`.trim();` |
| The parity gap | dashboard uses `px-4 py-6 sm:px-6` (**no `lg:px-8`**); no current `padding` value yields that → zero-visual-change adoption impossible until 6a |
| `layout.types.ts` exports | `MeeLayoutGap`, `MEE_GAP_TOKEN`, `MeePageMaxWidth`, `MeeFormMaxWidth` — 6a **adds** `MeePagePadding` alongside these |
| `MeePagePadding` does **not** exist yet | `grep -rn "MeePagePadding" frontend/libs/` → no matches today |
| `@mesell/layout` consumer count | **0** — no MFE/app imports any layout page primitive (sub-plan §1) → API widening is risk-free, nothing to migrate |
| Existing `page.component.spec.ts` padding coverage | two assertions: padding-true ⇒ `className` contains `px-4`; padding-false ⇒ `className` does NOT contain `px-4`. **Both must stay green** under the new resolution map. |
| Test runner | `@angular/build:unit-test` (vitest); specs discovered via `libs/**/*.spec.ts`; TestBed + `NoopAnimationsModule`; `fixture.componentRef.setInput(...)` to drive inputs (mirror existing `page.component.spec.ts`). |
| FE contracts baseline | `cd frontend && node tools/contracts/run-all.mjs` → all 5 CLEAN, exit `0`. Phase 6a must keep this. |
| Pre-existing debt (NOT this phase) | `apps/shell/src/app/app.spec.ts` NG0201 missing `MessageService` — expect this 1 failure on every UI-DS PR until its separate cleanup ticket; do **not** "fix" it here. |

**Reframe:** this is a **micro, additive, backward-compatible API widening inside one component** (~20 lines incl. spec). There is nothing to migrate (0 consumers) and the only literal strings introduced (`'px-4 py-6 sm:px-6'`) are a *subset* of strings already present. The single risk surface is accidentally changing the `true`/`'default'` (byte-identical) or `false`/`'none'` (empty) outputs — the spec plan (§4) pins those down with explicit assertions.

---

## 2. The locked 6a decision (encode precisely — do NOT redesign)

`mee-page`'s `padding` input becomes a **discrete scale, accepted as `boolean | MeePagePadding`**, fully backward-compatible. The resolution is:

| `padding` input value | Resolved padding class string | Status |
|---|---|---|
| `false` | `''` (edge-to-edge) | **UNCHANGED** (current `false` behaviour) |
| `'none'` | `''` (edge-to-edge) | **NEW alias** for `false` |
| `'tight'` | `'px-4 py-6 sm:px-6'` (no `lg:px-8`) | **NEW** — matches the dashboard's hand-rolled padding for pixel-parity adoption |
| `true` | `'px-4 py-6 sm:px-6 lg:px-8'` | **UNCHANGED** (current `true` / default behaviour — byte-identical) |
| `'default'` | `'px-4 py-6 sm:px-6 lg:px-8'` | **NEW alias** for `true` (the design-system standard for *new* pages) |

- **Default stays `true`** → existing default behaviour is byte-identical (no consumer, but the principle stands: `'default'` and `true` are interchangeable, both = the current default).
- `'tight'` exists **only** so an existing page (dashboard) can adopt `mee-page` with exact pixel-parity instead of a forced `lg:px-8` visual shift. New pages should prefer `'default'` (the `lg:px-8` desktop breathing room is the intended standard).
- This is the founder's locked decision from sub-plan §4 — **do not add a fourth scale value, do not rename, do not drop the boolean overload.**

---

## 3. File-by-file change list (exact before/after — builder writes literal TS)

### 3.1 `frontend/libs/layout/layout.types.ts` — ADD the `MeePagePadding` type

**Action:** add one exported union type. Place it near `MeePageMaxWidth` (it is a `mee-page` concern), with a short doc comment. **Do not touch** `MeeLayoutGap`, `MEE_GAP_TOKEN`, `MeePageMaxWidth`, or `MeeFormMaxWidth`.

**ADD (exact text):**
```ts
/**
 * Discrete horizontal/vertical padding scale for `mee-page`.
 *   'none'    → no padding (edge-to-edge); equivalent to the boolean `false`.
 *   'tight'   → 'px-4 py-6 sm:px-6'           (omits the lg:px-8 step — for
 *               pixel-parity adoption by pages that hand-roll this padding).
 *   'default' → 'px-4 py-6 sm:px-6 lg:px-8'   (the design-system standard;
 *               equivalent to the boolean `true`).
 *
 * `mee-page`'s `padding` input accepts `boolean | MeePagePadding` for backward
 * compatibility: `false ≡ 'none'`, `true ≡ 'default'`.
 */
export type MeePagePadding = 'none' | 'tight' | 'default';
```

> Optional (builder's discretion, additive): a `Record<MeePagePadding, string>` map in `layout.types.ts` mirroring `MEE_GAP_TOKEN` — e.g. `MEE_PAGE_PADDING_CLASS`. This is **encouraged** for greppability/consistency with the established `MEE_GAP_TOKEN` idiom, but the literal strings MUST exactly match §2. If used, the `hostClass()` resolution (§3.2) reads through it. Do **not** over-engineer beyond a flat map.

### 3.2 `frontend/libs/layout/page/page.component.ts` — widen the `padding` input + re-resolve `hostClass()`

Two edits, nothing else in this file changes.

**(a) The `padding` input declaration.**

BEFORE (on develop):
```ts
  /**
   * When true (default), applies responsive horizontal + vertical padding
   * (`px-4 py-6 sm:px-6 lg:px-8`). Set false for edge-to-edge layouts.
   */
  readonly padding = input<boolean>(true);
```

AFTER:
```ts
  /**
   * Page padding. Accepts a boolean (back-compat) or the `MeePagePadding`
   * scale:
   *   false / 'none'    → no padding (edge-to-edge)
   *   'tight'           → 'px-4 py-6 sm:px-6'           (no lg:px-8 step)
   *   true  / 'default' → 'px-4 py-6 sm:px-6 lg:px-8'   (design-system default)
   * Default is `true` (≡ 'default') — unchanged from before.
   */
  readonly padding = input<boolean | MeePagePadding>(true);
```
- The default value stays `true` (back-compat preserved; `mee-page` with no `padding` set is byte-identical to today).
- Add `MeePagePadding` to the existing type-only import from `../layout.types` (currently `MEE_GAP_TOKEN, type MeeLayoutGap, type MeePageMaxWidth`). If using the optional `MEE_PAGE_PADDING_CLASS` map (§3.1), import it as a value too.

**(b) The padding branch of `hostClass()`.**

BEFORE (on develop):
```ts
  readonly hostClass = computed<string>(() => {
    const mw = MAX_WIDTH_CLASS[this.maxWidth()];
    const pad = this.padding()
      ? 'px-4 py-6 sm:px-6 lg:px-8'
      : '';
    return `flex flex-col w-full mx-auto ${mw} ${pad}`.trim();
  });
```

AFTER (illustrative — builder writes the literal TS; the resolution map MUST match §2 exactly):
```ts
  readonly hostClass = computed<string>(() => {
    const mw = MAX_WIDTH_CLASS[this.maxWidth()];
    const pad = this.paddingClass();
    return `flex flex-col w-full mx-auto ${mw} ${pad}`.trim();
  });

  /** Resolve the boolean | MeePagePadding input → Tailwind padding class string. */
  private readonly paddingClass = computed<string>(() => {
    const p = this.padding();
    // Boolean back-compat: true ≡ 'default', false ≡ 'none'.
    if (p === false || p === 'none') return '';
    if (p === 'tight') return 'px-4 py-6 sm:px-6';
    // p === true || p === 'default'
    return 'px-4 py-6 sm:px-6 lg:px-8';
  });
```
- **Hard requirement:** for `p === true` and `p === 'default'` the returned string is **exactly** `'px-4 py-6 sm:px-6 lg:px-8'` (byte-identical to today). For `p === false` and `p === 'none'` it is exactly `''`. For `'tight'` it is exactly `'px-4 py-6 sm:px-6'`.
- The builder MAY inline the resolution directly in `hostClass()` instead of a separate `paddingClass()` computed, or read through the optional `MEE_PAGE_PADDING_CLASS` map — **any of these is acceptable** provided the outputs match §2 byte-for-byte and the boolean overload is handled first. Record the chosen idiom in the PR.
- **Do not touch** `MAX_WIDTH_CLASS`, `maxWidth`, `gap`, `gapValue()`, the template, or the styles.

### 3.3 `frontend/libs/layout/page/page.component.spec.ts` — keep existing green + add scale cases

**Action:** retain **every** existing assertion (creates, `<div>`-not-`<main>` landmark, the three `maxWidth` cases, the three `gap` cases, **and the two existing padding assertions**). The two existing padding cases (`padding=true` ⇒ contains `px-4`; `padding=false` ⇒ not contains `px-4`) MUST stay green unchanged — they prove back-compat survives.

**ADD** the following assertions (mirror the existing `fixture.componentRef.setInput('padding', …)` + `className` idiom):

1. **`'default'` ≡ `true` (byte-identical default class):** `setInput('padding', 'default')` ⇒ `className` contains `px-4`, `py-6`, `sm:px-6`, **and** `lg:px-8`.
2. **`true` includes `lg:px-8` (pin the default explicitly):** `setInput('padding', true)` ⇒ `className` contains `lg:px-8`. *(Tightens the existing `px-4`-only check so a regression dropping `lg:px-8` is caught.)*
3. **`'tight'` omits `lg:px-8`:** `setInput('padding', 'tight')` ⇒ `className` contains `px-4`, `py-6`, `sm:px-6` **and does NOT contain** `lg:px-8`. *(This is the load-bearing new behaviour — the dashboard-parity case.)*
4. **`'none'` ≡ `false` (no padding):** `setInput('padding', 'none')` ⇒ `className` does NOT contain `px-4` (and not `lg:px-8`).
5. *(Optional, recommended)* **boolean `false` still no padding** — already covered by the existing test; keep it.

> Assertion style note: prefer `toContain`/`not.toContain` on `container.className` (matches the existing spec). For the `'tight'` vs `'default'` distinction, the `lg:px-8` token is the discriminator — assert its presence for `'default'`/`true` and its absence for `'tight'`. Keep using `fixture.nativeElement.querySelector('div')` (the landmark decision means it's a `<div>`, not `<main>` — do not change that).

---

## 4. Files to create / edit (manifest)

| # | Path (relative to `frontend/`) | Action | Builder |
|---|---|---|---|
| F0 | `libs/layout/layout.types.ts` | **EDIT** — add `MeePagePadding` union (+ optional `MEE_PAGE_PADDING_CLASS` map). No other export touched. | component-builder |
| F1 | `libs/layout/page/page.component.ts` | **EDIT** — widen `padding` input to `boolean \| MeePagePadding` (default still `true`); re-resolve the padding branch of `hostClass()` per §3.2; import `MeePagePadding`. No other input/template/style change. | component-builder |
| F2 | `libs/layout/page/page.component.spec.ts` | **EDIT** — keep all existing assertions green; add the 4 scale/back-compat cases (§3.3). | component-builder |
| F3 | `docs/plans/architecture/UI_DS_PHASE6A_SPEC.md` | (this SPEC — already authored by coordinator) | — |
| F4 | `libs/layout/README.md` | **OPTIONAL EDIT** — additive one-line `padding="tight"` mention only. Skip if it risks scope creep. | component-builder |

> **No `apps/**`, no MFE, no other lib, no other primitive (`mee-form-layout` etc.), no scanner, no `run-all.mjs`, no `ci.yml`, no theme/token, no providers, no root-wiring, no new npm dep, no deletion.** Phase 6a flips **no** contract → **no `meesell-infra-builder` coordination** (same as Phase 3).

---

## 5. Which specialist builds this + coordination (HYBRID)

**Sole builder: `meesell-angular-component-builder`** — Phase 6a is a signal-input type widening + a `computed()` class-resolution edit on one standalone OnPush component + its spec. That is component territory (cf. Phase 3, where the component-builder built `mee-page` itself).

- **No `meesell-angular-ui-styler` pass required.** 6a introduces **no new visual output** for existing usages (`true`/`'default'`/`false`/`'none'` are byte-identical to today) and the one genuinely new string (`'tight'` = `px-4 py-6 sm:px-6`) is a literal subset of the existing default — there is no new responsive behaviour to review, no token to validate, no a11y surface change. The component-builder's spec assertions are the parity proof. *(The visual-parity judgement for `'tight'` belongs to the **pilot** — where it is screenshot-diffed against the real dashboard at 360/768/1280px — not to 6a, which only makes the class string expressible.)*
- **No `meesell-angular-service-builder` work** — no services, no API, no providers.
- **No infra coordination** — no scanner/`ci.yml`/branch-protection change.

**Coordinator (this session) runs the merge-gate** after the build — the §6 checklist is the gate; it can reject back to the component-builder.

---

## 6. Verification checklist (merge-gate evidence the builder must attach to the PR)

The coordinator will check **every** box before merging the `feature/.../frontend`-equivalent PR (here: `feat/ui-ds-phase6a → develop`, founder merges to develop per the UI-DS workstream pattern; this checklist is the frontend-lead gate).

1. **Type-check clean:** `cd frontend && npx tsc -p tsconfig.json --noEmit` → no errors. Proves the `padding = input<boolean | MeePagePadding>(true)` union, the `MeePagePadding` type, and the `hostClass()` resolution all type-check. Paste the clean output.
2. **Back-compat is byte-identical (the load-bearing proof):** the two **pre-existing** padding assertions (`padding=true` ⇒ contains `px-4`; `padding=false` ⇒ not contains `px-4`) stay **green unchanged**. Plus the new explicit `true ⇒ contains lg:px-8` and `'default' ⇒ contains lg:px-8` assertions pass. Paste the green spec lines. **If any pre-existing padding assertion was modified rather than kept, REJECT** — back-compat must be proven by the *original* tests still passing.
3. **`'tight'` parity assertion passes:** the new `'tight' ⇒ contains px-4/py-6/sm:px-6 AND not contains lg:px-8` test is green. Paste it. (This is the dashboard-parity capability the whole phase exists for.)
4. **`'none'` ≡ `false` assertion passes:** `'none' ⇒ not contains px-4`. Paste it.
5. **Tests green, no count drop:** the full layout spec suite passes with the existing count **+ ~4 new** `page.component.spec.ts` cases; **no other spec count changes** (no other file touched). Paste the new green lines + the suite total. *(The pre-existing `apps/shell/.../app.spec.ts` NG0201 `MessageService` failure is expected debt — note it, do not "fix" it.)*
6. **Build green + budget:** `cd frontend && npx ng build frontend --configuration development` succeeds; build time **< 90 s** (CLAUDE Decision 12). **Bundle delta ≈ 0** for every entry point — `@mesell/layout` still has 0 consumers, so the change tree-shakes out of all MFE bundles. Paste the bundle line; flag any initial-bundle movement (must be none).
7. **FE contracts green (NO regression, NO scanner edit):** `cd frontend && node tools/contracts/run-all.mjs; echo $?` → all 5 **CLEAN**, exit `0`. The strict FE Gate stays green. Paste the summary. **No scanner / `run-all.mjs` / `ci.yml` was edited** (confirm in the diff).
8. **No-new-import / no-new-surface grep proofs (paste each):**
   - `git diff develop -- frontend/libs/layout/ | grep -E '^\+' | grep -E "primeng|@primeuix|pi pi-|@mesell/composites"` → **no matches** (no PrimeNG/icon/composites surface added).
   - `git diff develop -- frontend/ | grep -E "^\+.*import"` → the **only** added import is `MeePagePadding` (and optionally `MEE_PAGE_PADDING_CLASS`) from `../layout.types`. No other new import.
9. **Diff scope:** `git diff --stat develop` shows **only** `libs/layout/layout.types.ts`, `libs/layout/page/page.component.ts`, `libs/layout/page/page.component.spec.ts`, this SPEC doc (+ optionally `libs/layout/README.md`). **No `apps/**`, no MFE, no other lib, no `mee-form-layout`, no scanner, no theme, no root-wiring, no deletion.** Paste `git diff --stat`.
10. **`mee-form-layout` untouched (explicit):** `git diff develop -- frontend/libs/layout/form-layout/` → **empty**. Confirms the sub-plan's "6a does not touch form-layout" constraint held.

---

## 7. Out-of-scope (explicit — refuse if asked in Phase 6a)

- **Any MFE / app / shell adoption** of `mee-page` or aggregators (changing any `imports:` to use `MEE_LAYOUT`, swapping a hand-rolled `<div>` for `mee-page`) — that is the **pricing pilot** (the B-step that follows 6a), and the **dashboard** migration is even later (sub-plan §5.1). 6a only makes `'tight'` *expressible*; it consumes nothing.
- **Touching `mee-form-layout` / `MeeFormMaxWidth`** — explicitly deferred to the pilot's per-form confirmation (sub-plan §4 + §7).
- **Any other layout primitive** (`mee-section`/`mee-toolbar`/`mee-grid`/`mee-stack`) — frozen.
- **A new `padding` scale value beyond `'none' | 'tight' | 'default'`**, renaming, or removing the boolean overload — the scale is founder-locked.
- **New design tokens / theme / preset / `styles.css` / providers edits; new npm deps; Storybook.**
- **Flipping any contract / editing any scanner or `ci.yml` / branch-protection** — 6a flips nothing.
- **The Phase 6 A-rule convention doc** (CLAUDE.md / CONTRIBUTING paragraph) and **Phase 7 swap-proof** — separate deliverables, not this PR.
- **Backend / k8s; `docs/FRONTEND_ARCHITECTURE.md`** (LOCKED).

---

## 8. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| `true`/`'default'` output drifts from the current `px-4 py-6 sm:px-6 lg:px-8` (silent visual regression for future consumers) | §3.2 pins the literal string; §6.2 keeps the **original** back-compat tests + adds explicit `lg:px-8`-present assertions; §2 is the byte-identical contract. |
| `false`/`'none'` accidentally emits a class | §3.2 handles `false`/`'none'` first → `''`; §6.4 asserts `'none' ⇒ no px-4`; existing `false ⇒ no px-4` test retained. |
| Boolean overload broken when widening the union | Default stays `true`; the union is `boolean \| MeePagePadding`; §6.2 proves boolean still resolves correctly. |
| Scope creep into `mee-form-layout` or an MFE | §0.1/§0.7 guardrails + §6.9/§6.10 diff-scope + form-layout-empty proofs; review rejects any out-of-scope file. |
| Builder edits a scanner / `ci.yml` to "make it pass" | §0.3 forbids it; §6.7 requires contracts green **without** scanner edits; §6.9 diff scope catches it. |
| `'tight'` string typo (e.g. keeps `lg:px-8`) | §6.3 asserts `'tight'` **does NOT** contain `lg:px-8` — a typo fails the gate. |

---

## 9. Things I (coordinator) want the builder to watch for

1. **Resolve the boolean cases FIRST** in `hostClass()`/`paddingClass()` (`false`/`'none'` → `''`), then `'tight'`, then fall through to default. A naive `Record<MeePagePadding,string>[this.padding()]` lookup **breaks on the boolean** (`true`/`false` aren't keys) — handle the boolean overload explicitly before any map lookup.
2. **Do not "improve" the default string.** Copy `px-4 py-6 sm:px-6 lg:px-8` verbatim from develop. The whole back-compat guarantee rests on it being byte-identical.
3. **Keep the original two padding tests intact** — don't rewrite them into the new parametrized cases. Their survival *is* the back-compat proof the gate checks (§6.2).
4. **Type-only import.** `MeePagePadding` is a type → add it to the existing `type`-qualified import from `../layout.types`. If you add the optional `MEE_PAGE_PADDING_CLASS` value map, import that **without** `type`.
5. **Leave the landmark `<div>`-not-`<main>` decision and its JSDoc alone** — only the `padding` JSDoc changes.
6. **One worktree, one branch, one PR.** Work in `/tmp/mesell-wt/ui-ds-phase6a` on `feat/ui-ds-phase6a`. Never git in the master tree.

---

*End of Phase 6a BUILD SPEC. Next HYBRID step: this session dispatches `meesell-angular-component-builder` with this spec (edit the 3 files), then `meesell-frontend-coordinator` runs the §6 merge-gate and opens `feat/ui-ds-phase6a → develop` for the founder to merge. The pricing pilot (B-step) follows in a separate SPEC once 6a is on develop.*

End the eventual commit body with:
Co-Authored-By: Claude Opus 4.8 (1M context)
