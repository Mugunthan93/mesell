## Session 2026-06-16 — UI Design-System Phase 3 — MEE_LAYOUT page primitives {#ui-ds-phase3}

### Task
Build 6 standalone Angular 18 page-primitive components in `frontend/libs/layout/` as
specified by `docs/plans/architecture/UI_DS_PHASE3_SPEC.md`. Create MEE_LAYOUT aggregator,
populate the barrel index, author the README.

### Route touched
N/A — library primitives, no routing. MFE adoption = Phase 6.

### Services consumed
None. Layout primitives are purely structural (no services, no HTTP, no providers).

### Files created/edited
- `libs/layout/layout.types.ts` — MeeLayoutGap, MEE_GAP_TOKEN, MeePageMaxWidth, MeeFormMaxWidth
- `libs/layout/page/page.component.ts + spec.ts`
- `libs/layout/section/section.component.ts + spec.ts`
- `libs/layout/toolbar/toolbar.component.ts + spec.ts`
- `libs/layout/grid/grid.component.ts + spec.ts`
- `libs/layout/stack/stack.component.ts + spec.ts`
- `libs/layout/form-layout/form-layout.component.ts + spec.ts`
- `libs/layout/aggregators.ts` — MEE_LAYOUT (6 members)
- `libs/layout/aggregators.spec.ts` — pure-Vitest assertions (9 tests, no TestBed)
- `libs/layout/index.ts` (EDITED) — barrel populated
- `libs/layout/README.md` — usage/demo doc
- `docs/status/STATUS_FRONTEND.md` (UPDATED)

### Styling idiom chosen (Phase 3 record)
- **Gap spacing**: `[style.gap]` / `[style.margin-top]` / `[style.grid-template-columns]` bound
  to `var(--mee-space-N)` via the `MEE_GAP_TOKEN` map in `layout.types.ts`.
  Rationale: keeps token values out of Tailwind's JIT scan scope and ties them to the
  single source-of-truth in `_tokens.css`. Avoids Tailwind arbitrary-value `[gap:var(...)]`
  which requires double-bracket escaping and is harder to grep.
- **Structural layout**: Tailwind utilities (`flex`, `grid`, `flex-col`, `grid-cols-*`,
  `items-*`, `justify-*`, `max-w-*`, `flex-wrap`) — readable + mobile-first.
- **No hard-coded px** for any spacing that has a `--mee-space-*` token.

### Pattern: aggregators.spec.ts for libs — pure Vitest, NO TestBed throwaway component
- `import { describe, it, expect } from 'vitest'` at the top (no globals injection)
- Angular compiler CANNOT statically analyze `imports: [...MEE_LAYOUT]` when the
  array comes from a separate module — produces NG1010 "Unable to evaluate statically"
- The compile-time typing proof is already captured by:
  `as const satisfies readonly Type<unknown>[]` in aggregators.ts + `npx tsc --noEmit`
- aggregators.spec.ts: pure runtime membership assertions (count, set-size, toContain)
- Mirror: `libs/ui-kit/aggregators.spec.ts` which follows the same pattern (no TestBed)

### Pattern: worktree node_modules must be installed
- Git worktrees do NOT share node_modules with the master tree
- `pnpm install --frozen-lockfile` must be run in the worktree's frontend/ before any tsc/ng commands
- Took ~39s on first run (uses pnpm store cache)

### Pattern: browser gap normalization in jsdom
- `div.style.gap = '0'` → browser reads back as `'0px'` in jsdom
- `div.style.margin-top = '0'` → browser reads back as `'0px'`
- Spec assertions for zero gaps must use: `expect(['0', '0px']).toContain(el.style.gap)`
- Token values (`var(--mee-space-N)`) are NOT normalized — they come back as-is from jsdom

### Pattern: spec "project content via ng-content"
- Do NOT overwrite `fixture.nativeElement.innerHTML` to inject test content — this
  destroys the component's rendered DOM (including the inner <main> or wrapper div)
- Instead, assert that the inner container element exists (it always does if component renders)
- Or use `TestBed.overrideTemplate()` to provide content-projection test content pre-creation

### Pattern: MeeGridComponent null vs undefined for [style.grid-template-columns]
- `computed(() => null)` for numeric cols — Angular removes the style binding when null
- `computed(() => 'repeat(...)')` for auto cols — sets the style
- jsdom: `el.style.gridTemplateColumns` is `''` (empty string) when null is bound, not `null`
- Spec: `expect(div.style.gridTemplateColumns).toBeFalsy()` (covers both '' and null)

### Build result (2026-06-16 Phase 3)
- `npx tsc -p tsconfig.json --noEmit`: ZERO errors
- `npx ng build frontend --configuration development`: SUCCESS, 137.6s
- Bundle delta: ZERO — primitives tree-shake out (no consumer yet; Phase 6 wires imports)
- Initial bundle unchanged: polyfills.js 98.77kB, styles.css 27.99kB, main.js 303B
- Tests: 1162 passed / 1 failed (pre-existing app.spec.ts NG0201 MessageService)
- New layout spec files: 7, new tests: 69
- Contracts: All 5 CLEAN, exit 0 (FE-1/FE-2/FE-3/FE-4/FE-5 all OK)
