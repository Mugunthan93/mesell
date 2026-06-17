# UI Design-System Decoupling — Phase 3 (Layout page primitives)

**Status:** BUILT + PR OPEN (founder merges). 2026-06-16/17.
**PR:** #265 `feat/ui-ds-phase3 → develop`. Commit `19c344d` (21 files, +1940/-13).
**Worktree:** `/tmp/mesell-wt/ui-ds-phase3` (dedicated per-phase worktree off `origin/develop @ d1916cd`). I (frontend-coordinator) drove this as standalone LEAD; master/Director freed.

## What shipped
`@mesell/layout` (rank 1) populated with 6 standalone OnPush signal-input page primitives + `MEE_LAYOUT` aggregator:
`mee-page` (maxWidth/padding/gap), `mee-section` (heading/description @if + body), `mee-toolbar` (default=start slot + `[mee-toolbar-end]` slot), `mee-grid` (cols 'auto'|1-4, mobile-first), `mee-stack` (direction/gap/align/justify/wrap), `mee-form-layout` (gap/maxWidth, reading-width cap).
- `layout.types.ts`: `MeeLayoutGap` scale → `MEE_GAP_TOKEN` → `var(--mee-space-*)` (single spacing source of truth).
- `aggregators.ts`: `MEE_LAYOUT` (6) `as const satisfies readonly Type<unknown>[]` — mirrors ui-kit P2 idiom.
- Barrel populated; Phase-0 `MEE_LAYOUT: never[]=[]` placeholder replaced; **"TODO(Phase 4): chrome" comment preserved**.
- `libs/layout/README.md` = the "storybook/demo" deliverable (no Storybook harness in repo).
- Coordinator SPEC = `docs/plans/architecture/UI_DS_PHASE3_SPEC.md`.

## HYBRID execution (what worked)
SPEC → `meesell-angular-component-builder` (built 17 files) → coordinator interim read → `meesell-angular-ui-styler` (polish) → coordinator merge-gate → commit/push/PR. **The ui-styler pass paid for itself** — caught 2 real defects the component-builder missed:
1. **WCAG 2.4.1 duplicate `<main>`**: `mee-page` rendered `<main>` nested inside the shell's existing `<main class="page-content">` (`apps/shell/.../shell/shell.component.html`). Fixed → `<div>`; shell is sole landmark owner. **Phase 4 carry:** if shell cedes the landmark, add opt-in `asMain` input to `mee-page` (public API change — plan it).
2. **Responsive**: `mee-grid cols=4` jumped 2→4 at `md` (~180px tiles on tablets) → fixed to 1/sm:2/md:3/lg:4.

## Contracts / gates (Phase 3 flips NONE)
FE-1 (PrimeNG seal) + FE-4 (lib DAG) hold **by construction**: layout primitives import ONLY `@angular/core` + local `./layout.types` — no primeng/@primeuix, no `@mesell/composites`. `run-all.mjs` → all 5 CLEAN. No scanner/ci.yml edit. tsc clean; build green (bundle delta 0 — primitives tree-shake, no consumer yet, adoption=Phase 6); 1163 tests pass (+69 layout specs).
- **Pre-existing debt (NOT mine, recurring):** `apps/shell/src/app/app.spec.ts` fails NG0201 missing `MessageService` — separate cleanup ticket. Expect this 1 failure on every UI-DS PR until fixed.

## Key conventions reused (for later phases)
- Component idiom: `page-header.component.ts` (Tailwind + signal inputs + computed + projection); `auth-layout.component.ts` (`styles:[]` + `:host{display:block}` + CSS-var tokens).
- Spec idiom: TestBed + `NoopAnimationsModule` (`card.component.spec.ts`). Test runner `@angular/build:unit-test` (vitest); spec glob `../../../libs/**/*.spec.ts` discovers `libs/layout/**`.
- Aggregator typing: `as const satisfies readonly Type<unknown>[]`; throwaway `imports:[...MEE_X]` component in a spec FAILS to evaluate statically (NG1010) when the array is cross-module — rely on tsc + `as const satisfies` for the spread proof, NOT a runtime throwaway component (same as ui-kit aggregators.spec.ts).
- **Build is SLOW on this 8GB machine cold** (~137s); warm ~3s. Don't block on a redundant cold build — trust the post-edit agent build + tsc + contracts.

## Workstream roadmap (remaining)
- **Phase 4** (next): chrome primitives (`mee-app-bar`/`side-nav`/`nav-item`/`user-menu`) into `@mesell/layout` + refactor `apps/shell` ShellComponent to compose them; flip **FE-3** strict. Builder: component + ui-styler. **Carry the `mee-page` asMain landmark question.**
- **Phase 5**: finalize FE-1/FE-4/FE-5 scanners; flip FE Gate to **blocking required check**.
- **Phase 6**: per-MFE adoption sweep (use `MEE_LAYOUT` + aggregators + `mee-icon`).
- **Phase 7**: swap-proof (2nd theme + icon-set swap = one-file each).
- **Discipline:** one phase = one fresh worktree off develop (`git worktree add -b feat/ui-ds-phaseN /tmp/mesell-wt/ui-ds-phaseN origin/develop`) = one branch = one PR. NEVER git in the master tree `/Users/.../Project/mesell` (contamination lesson — a prior phase parked it on stale `feat/ui-ds-phase0`). Founder merges every phase PR.
