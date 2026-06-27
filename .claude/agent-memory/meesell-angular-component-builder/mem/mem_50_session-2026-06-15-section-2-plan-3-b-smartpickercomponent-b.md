## Session 2026-06-15 — Section-2 Plan 3-B: SmartPickerComponent browse button fix {#sec2-plan3b}

### Route touched
`/catalogs/new` — apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts

### Services consumed
None changed. CategoryService.browseRedirect() handler (onBrowse) unchanged.

### Task
Single targeted fix: replace the raw `<button>` "Browse if none match" fallback element with
`<mee-button variant="ghost" size="sm" [fullWidth]="false" (clicked)="onBrowse()" />`.

### Pattern: Worktree file path vs main project file path
- This project uses git worktrees: `feature/section-2/frontend` lives at `/tmp/mesell-wt/section-2-frontend/`
- The main project at `/Users/mugunthansrinivasan/Project/mesell/` is on `develop`
- ALWAYS edit the worktree file at `/tmp/mesell-wt/section-2-frontend/frontend/apps/...`, NOT the main project file
- The task prompt says "Work in /tmp/mesell-wt/section-2-frontend" — trust that; find the file under that path first
- Accidentally editing the develop branch file in the main project creates a partial/broken state in develop

### Pattern: MeeButtonComponent (ui-kit barrel) — confirmed API
- Selector: `mee-button`
- Barrel: `@mesell/ui-kit` (libs/ui-kit/index.ts exports `MeeButtonComponent`)
- Inputs: `label` (required), `variant` ('primary'|'secondary'|'ghost'|'danger', default 'primary'),
  `size` ('sm'|'md'|'lg', default 'md'), `fullWidth` (boolean, default false),
  `loading` (boolean), `disabled` (boolean), `icon` (string|undefined)
- Output: `clicked` (void) — emits when p-button onClick fires
- Path confirmed: `libs/ui-kit/button/button.component.ts` (NOT `libs/ui-kit/src/lib/button/...`)
  The task prompt had the wrong path; actual path is one level up from what the coordinator described

### Pattern: ui-kit barrel path in this codebase
- Barrel: `/Users/mugunthansrinivasan/Project/mesell/frontend/libs/ui-kit/index.ts`
- NOT `frontend/libs/ui-kit/src/index.ts` (that path does not exist)
- Component files: `frontend/libs/ui-kit/<component-name>/<component-name>.component.ts`

### Pattern: Adding to existing @mesell/ui-kit destructured import
- When another mee-* component is already imported from @mesell/ui-kit, add to the existing destructured import
- DO NOT add a second `import { X } from '@mesell/ui-kit'` line — merge into the existing destructure

### Verification checks
- `grep -n "<button" <file>` must return ZERO hits — absence of raw button confirmed
- `grep -n "primeng" <file>` must return ZERO hits — no direct PrimeNG imports
- Build in worktree fails due to missing node_modules (pnpm install not run in worktree) — not a code defect

### Commit
- Exact message: `sec2: replace hand-rolled browse button with mee-button ghost (Plan 3-B)`
- Branch: feature/section-2/frontend @ 2a290b0 — PUSHED to origin

---
