## 2026-06-21 — env-manager doc verification (PR #335)
- Landed `## Verification (2026-06-21)` in `docs/dev/ENV_MANAGER.md` (PR #335, squash `793dafd`, develop HEAD). RAM guard verified correct (uses free+inactive+speculative, not pure-free); dep-tree fix = `cd frontend && CI=true pnpm install` for dangling @angular/cli symlink from pruned worktree; `baseline up` KNOWN ISSUE = esbuild --service deadlock before first MFE (not OOM). GOTCHA: `git branch -D` from master tree is blocked by guard-master-tree-git — use `MESELL_ALLOW_MASTER_GIT=1` prefix (founder-authorized) for the local-branch delete; `git push origin --delete` is fine; `git worktree remove` is fine.

---
