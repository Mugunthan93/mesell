## MS-PAR-1 worktree + stray-branch cleanup — 2026-06-14

Post-migration housekeeping (develop @ 1baf6d0, main protected @ 9a2b25c, 0 open PRs).

**Worktrees:** 26 in-scope under /private/tmp/mesell-wt/. Removed 22 CLEAN with `git worktree remove --force`. SKIPPED 4 DIRTY (never force past uncommitted work):
- msC-integration → M .claude/agent-memory/meesell-backend-coordinator/MEMORY.md
- msC-routes-fix → M meesell-api-routes-builder/MEMORY.md + docs/status/STATUS_BACKEND.md
- msE-backend → M docs/status/STATUS_BACKEND.md
- w6c-cat → M frontend/pnpm-workspace.yaml
The dirty mods are mostly peer-agent MEMORY.md / STATUS files — NOT mine to commit or discard. Left for the owning agent/founder to resolve.

**Out-of-task-scope worktrees left untouched:** the `.claude/worktrees/agent-*` set (and docs+session-close-dual-pepper, chore/frontend/start-all) — task scoped only to /private/tmp/mesell-wt/ prefixes. 2 are `locked`. Did not enumerate-remove these.

**Stray remote branches — KEY SAFETY LESSON:** of 13 candidate origin/feature/microservices-{catalog,category,customer,iam}/* branches, only 3 were actually merged into origin/develop (the `/integration` tips for catalog, category, iam). The migration merged via the integration branches; the per-group leaf branches (db/infra/svc/backend) were NOT individually merged into develop (their content reached develop through the integration merge, but `git branch -r --merged` does not consider them merged because their tip commits aren't ancestors of develop). So `--merged origin/develop` is the correct, conservative gate — it deleted only the 3 truly-merged refs and protected the other 10. Deleted: catalog/integration, category/integration, iam/integration. Skipped 10 unmerged — left for founder decision.

**Stash:** intentionally-kept stash@{0} ("pre-develop-switch") left untouched (not a worktree).

Pattern to reuse: ALWAYS gate remote-branch deletion on `git branch -r --merged origin/develop` membership, re-confirm per-branch with `grep -qx`, never assume a feature's leaf branches are merged just because the feature is merged.

---
