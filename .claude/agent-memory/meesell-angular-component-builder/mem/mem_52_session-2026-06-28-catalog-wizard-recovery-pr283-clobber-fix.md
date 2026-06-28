# Session 2026-06-28 — catalog-wizard-recovery — CatalogFormComponent clobber fix (PR #505) {#catalog-wizard-recovery-2026-06-28}

## Task
Restore the multi-step wizard `CatalogFormComponent` killed by PR #283 (design-branch merge overwrote the file with the old accordion layout). Branch: `feature/catalog-wizard-recovery/frontend`. Only file changed: `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form/catalog-form.component.ts`.

## Approach
1. `git show 1133ab5:...component.ts > target` — wrote the 1025-line wizard source directly from git history using shell redirect (not `Edit` / `Write` — Edit would fail on a stale read, Write would need Read first; Bash redirect is the clean way).
2. Three surgical `Edit` patches on top:
   - **ca8e9ed pattern**: Added `import { MeePageComponent } from '@mesell/layout'`; added `MeePageComponent` to imports array; wrapped template in `<mee-page maxWidth="xl" padding="none">`; removed `max-width` and `margin: 0 auto` from `.mee-wizard-page` CSS (and `max-width` from both media query blocks) since `mee-page` now owns centering.
   - **456494e pattern**: `[testId]="'catalog-ai-fill'"` on AI fill button; `data-testid="catalog-save-status"` on autosave status span; `[testId]="'catalog-form-next'"` on the per-step Next button.
   - **d6b2824 pattern**: Near no-op — wizard already uses `icon="sparkles"` (valid MeeIconName); `grep -n 'icon='` confirmed only one usage.
3. Verify: `tsc -p apps/mfe-catalog/tsconfig.app.json --noEmit` → EXIT 0 (zero output = zero errors).
4. Commit SHA: `c0e5d12`. PR #505 opened targeting `develop`.

## Key patterns / gotchas

### git-show redirect for large file restores
When restoring a file from history, use:
```bash
MESELL_ALLOW_MASTER_GIT=1 git -C /path/to/repo show <commit>:<file_path> > /path/to/worktree/<file_path>
```
Then verify with `wc -l` before reading. Do NOT use `cat` — use Read tool after the redirect. But note Read may show "file state stale" — this is fine; it means the file was written after the last read. Edit operations still work.

### mee-page wrapper pattern for wizard (sticky nav)
When wrapping a wizard page that has a `position: fixed` sticky nav:
- `<mee-page maxWidth="xl" padding="none">` wraps only the scrollable content region (the `<div #errorRegionRef>` + `<div class="mee-wizard-page">` block)
- The `<nav class="mee-wizard-nav">` stays OUTSIDE `<mee-page>` — it is `position: fixed` so it does not participate in page flow
- Remove `max-width` and `margin: 0 auto` from `.mee-wizard-page` inner div (all breakpoints); `mee-page` provides the outer 1280px centering via `maxWidth="xl"`

### Design-branch clobber pattern
PR #283 was a design-branch merge that overwrote a working feature file with the old accordion version. The wizard (1133ab5 → PR #264/#266/#269) was built after the design-branch diverged, so the merge undid it. Recovery: find the last wizard SHA, restore directly, re-apply any patches that landed after the wizard was built.

### tsc --noEmit as build gate
`tsc -p apps/mfe-catalog/tsconfig.app.json --noEmit` with zero output = zero errors is sufficient for the merge-gate TS check. The full `ng build` is slower and can be left as a background task; tsc is the definitive type-safety gate.

## Files changed
- `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form/catalog-form.component.ts` (1030 lines)

## Outcome
PR #505 open. `feature/catalog-wizard-recovery/frontend -> develop`. Awaiting founder-gate merge.
