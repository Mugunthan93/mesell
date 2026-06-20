# UI Design-System Decoupling — Phase 6a (`mee-page` padding parity tweak)

**Status:** SPEC AUTHORED (HYBRID step 1). 2026-06-17. Builder not yet dispatched.
**SPEC:** `docs/plans/architecture/UI_DS_PHASE6A_SPEC.md` (written in worktree `/tmp/mesell-wt/ui-ds-phase6a`, branch `feat/ui-ds-phase6a` off develop).
**Parent:** sub-plan `UI_DS_PHASE6_SUBPLAN.md` §4. Founder pick = **A (standing rule) + 6a (this) + pricing pilot**. NOT full C sweep.

## The locked decision (do not redesign)
`mee-page` `padding` input: `boolean` → `boolean | MeePagePadding` where `MeePagePadding = 'none' | 'tight' | 'default'`.
Resolution: `false`/`'none'` → `''`; `'tight'` → `'px-4 py-6 sm:px-6'` (NEW, dashboard-parity, no `lg:px-8`); `true`/`'default'` → `'px-4 py-6 sm:px-6 lg:px-8'` (UNCHANGED default, byte-identical). Default stays `true`. Backward-compatible, 0 consumers → nothing to migrate.

## Why 6a exists
Dashboard hand-rolls `px-4 py-6 sm:px-6` (no `lg:px-8`). Old boolean `padding` had no value for that → zero-visual-change adoption was impossible. `'tight'` makes it expressible. 6a ONLY makes the class string exist; actual adoption = the pricing pilot (next) and dashboard (later, sub-plan §5.1).

## Scope = 3 files, ~20 lines
`layout.types.ts` (+`MeePagePadding`, optional `MEE_PAGE_PADDING_CLASS` map), `page/page.component.ts` (widen input + re-resolve `hostClass()`), `page/page.component.spec.ts` (keep originals green + 4 new cases). `mee-form-layout` NOT touched (deferred to pilot). Flips NO contract → no ui-styler pass, no infra coord.

## Builder = `meesell-angular-component-builder` ONLY
No ui-styler (no new visual output for existing usages; `'tight'` parity judgement belongs to the pilot's screenshot diff, not 6a). No service-builder. No infra.

## Merge-gate watch-items (when reviewing the PR)
1. **Back-compat proof = the ORIGINAL two padding tests stay green unchanged** (if rewritten → REJECT). Plus explicit `true`/`'default'` ⇒ contains `lg:px-8`.
2. `true`/`'default'` output BYTE-IDENTICAL to develop's `px-4 py-6 sm:px-6 lg:px-8`.
3. `'tight'` ⇒ contains `sm:px-6` but NOT `lg:px-8` (the load-bearing new behaviour + typo guard).
4. FE Gate 5 contracts CLEAN without any scanner/ci.yml edit. Bundle delta ≈ 0 (still 0 consumers, tree-shakes).
5. Diff scope = only the 3 files (+SPEC, +optional README). `form-layout/` diff EMPTY.

## Gotcha flagged to builder
Resolve boolean FIRST in `hostClass()` — a naive `Record<MeePagePadding,string>[padding()]` breaks because `true`/`false` aren't keys. Handle boolean overload before any map lookup.

## Reused conventions (from Phase 3, see ui_ds_phase3.md)
Per-phase worktree off develop; NEVER git master tree. Spec idiom = TestBed + NoopAnimationsModule + `fixture.componentRef.setInput()` + `container.className` toContain/not.toContain. Build slow cold (~137s) warm ~3s. Expect pre-existing `apps/shell/app.spec.ts` NG0201 MessageService failure on every UI-DS PR (separate cleanup ticket) — do not fix here.
