## Session 2026-06-18 — PR #289 data-table spec — replace require() with ESM imports {#dt-require-fix}

### Task
Merge-gate blocker fix: `data-table.component.spec.ts` had 6 inline CommonJS `require()` calls
in the scenario-3 describe block. The Angular CI gate (`ng test`, @angular/build:unit-test,
strict ESM) fails compile with TS2591 "Cannot find name 'require'" × 6, preventing all 28 tests
from running.

### Fix
Added two ESM imports at the top of the spec file (after the existing `vitest` + `@angular/core` imports):
```typescript
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
```
Then deleted the three pairs of inline `const { ... } = require(...)` lines (one pair per test in
scenario 3). The test logic itself is unchanged — only the import mechanism changed.

### Pattern: inline require() in Vitest specs under @angular/build:unit-test → TS2591 ALWAYS FAILS
- `@angular/build:unit-test` (esbuild + strict ESM) does not define `require` as a global.
- `require(...)` inside a spec body compiles fine in older CommonJS setups but fails with
  TS2591 in this project's CI gate.
- FIX RULE: any `require(...)` in a spec file MUST be hoisted to a top-level ESM `import`.
- Applies to dynamic `require()` calls too — convert to `import(...)` (async) if truly dynamic.
- The symptom is "28/28 pass" in local dev (Node.js provides `require` as a runtime global)
  but "0/28 run + TS2591 × N" in CI. This gap is invisible unless you run `ng test` explicitly.

### Pattern: worktree with detached HEAD — checkout tracking branch before push
- `git worktree add /path origin/feat/branch` → detached HEAD at the remote tip.
- Must `git checkout -b local-branch --track origin/feat/branch` before committing.
- Push: `git push origin local-branch:feat/branch` maps local to remote PR branch.
- This is required because the feature branch is already checked out in a different worktree
  or the master tree cannot switch branches (guard-master-tree-git hook).

### Result
- `grep -n "require(" spec.ts` → 0 matches
- `tsc -p apps/shell/tsconfig.app.json --noEmit 2>&1 | grep data-table` → 0 errors
- Commit: 7fe0644 pushed to origin/feat/mee-data-table (PR #289)

---
