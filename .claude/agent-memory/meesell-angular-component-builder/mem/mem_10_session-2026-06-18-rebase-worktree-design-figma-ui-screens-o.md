## Session 2026-06-18 — Rebase worktree-design-figma-ui-screens onto origin/develop {#rebase-2026-06-18}

### Task
Rebased `worktree-design-figma-ui-screens` (6 commits) onto `origin/develop` which was 241 commits ahead. Resolved all conflicts according to a defined resolution strategy, then force-pushed.

### Rebase summary
- Branch had 6 real commits (after stripping the old merge-commit ancestors)
- Rebase stopped at 3 commit boundaries with 2+2+2 conflicting files respectively
- All 6 commits applied cleanly; rebase completed successfully

### Conflict resolution pattern (for future branches from this worktree)

**Rule 1 — OURS** (our branch wins):
- `frontend/libs/ui-kit/input/input.component.ts` — NgControl CVA upgrade; develop has old NG_VALUE_ACCESSOR pattern
- `frontend/libs/ui-kit/textarea/textarea.component.ts` — same upgrade; always keep OURS on these two files

**Rule 2 — THEIRS** (develop wins):
- All MFE app components (mfe-auth, mfe-catalog, mfe-dashboard, mfe-export, mfe-onboarding, mfe-pricing)
- All `federation.config.js` files, `federation.manifest.json`
- Shell components (shell.component.ts/html/css, app.config.ts)
- `frontend/libs/composites/auth-layout/auth-layout.component.ts`
- `frontend/libs/core/services/auth.service.ts`, `auth-api.service.ts`, `index.ts`
- All agent memory files (`.claude/agent-memory/**`)
- `docs/status/STATUS_FRONTEND.md`

**Rule 3 — git rm** (accept deletion):
- `frontend/apps/mfe-catalog/src/app/preview/preview/preview.component.ts` — deleted on develop

### Pattern: stash before rebase, pop after
- If worktree has uncommitted changes (M  files in `git status --short`), stash first
- `git stash` → `git rebase origin/develop` → resolve → `git rebase --continue` → `git stash pop`
- stash pop auto-merges STATUS_FRONTEND.md cleanly if rebase kept THEIRS for that file

### Pattern: GIT_EDITOR=true for headless rebase continue
- `GIT_EDITOR=true git rebase --continue` accepts the default commit message without opening an editor
- Required in non-interactive agent sessions

### Pattern: git checkout --ours / --theirs with absolute paths
- Must use absolute paths when the cwd might not be the repo root
- `git checkout --ours /absolute/path/to/file` works correctly from any directory

### Pattern: DU (delete/unmerged) in git status
- `DU frontend/apps/mfe-catalog/src/app/preview/preview/preview.component.ts` = "deleted in HEAD, modified in our branch"
- Resolution: `git rm <file>` — accept the deletion; never `git checkout --theirs` on a DU file

### Pattern: add/add conflict
- `CONFLICT (add/add): Merge conflict in frontend/libs/core/services/auth-api.service.ts`
- Both branches added this file with different content
- `git checkout --theirs` picks develop's version (correct per Rule 2)
- `git add` to stage, then continue

### tsc result
- ZERO errors after rebase (verified with `pnpm exec tsc --noEmit` from `frontend/`)

### PR status
- PR #283: `"mergeable":"MERGEABLE"` — no conflicts
- `"mergeStateStatus":"BLOCKED"` = branch protection (required reviews) — not a conflict issue

---
