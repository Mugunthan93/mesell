# Worktree + branch cleanup (2026-06-27)

> Session `mesell-worktree-branch-cleanup-infra-session-1`. Founder-directed git hygiene on the 8GB dev box. ₹0 — pure git hygiene, no cluster/cloud/secret/cost change. No PR for worktree removal (commits nothing). This memory recorded via a short-lived worktree off `origin/develop`.

## Headline: the brief's premise was stale — `git worktree list` was already lean

The brief expected `git worktree list` to show ~50 worktrees "most flagged prunable." Reality: **only 14 registered worktrees** (1 master + 13 under `.claude/worktrees/`), NONE prunable. `git worktree prune` (step A) removed nothing. A prior prune session + the harness had already kept the registered set lean. **LESSON: always re-derive the actual state before acting on a brief's stated counts — `git worktree list` + `git worktree prune -v` first; the founder's snapshot can be hours/days stale.**

## The 13 registered non-master worktrees are ALL harness-managed (`.claude/worktrees/`) → OFF-LIMITS

Every registered worktree besides master lives at `.claude/worktrees/agent-*` (12) or `.claude/worktrees/fix-auth-refresh-storm` (1). Safety gate #2 forbids touching `.claude/worktrees/*` (active/recent dispatched agents). The `.git/worktrees/` admin records matched these 13 exactly. So there were **zero worktrees in my removable scope** (`/private/tmp/mesell-wt/*` or `/private/tmp/mesell-*`). I removed no worktrees. Final `git worktree list` = 14, unchanged, all `.claude/worktrees/agent-*` intact.

## The ~46 `/private/tmp/mesell-wt/*` dirs are NOT worktrees — left for review

There ARE ~46 root-owned dirs under `/private/tmp/mesell-wt/` (+ 5 more `/private/tmp/mesell-*`: presync-20260621, qa-cat-e2e, reserve, serve-nostore, wt-category-guard). BUT:
- ALL 46 have **NO `.git` file** → not git worktrees.
- `git worktree list` mentions ZERO `/private/tmp` paths.
- Total disk = **24K** (empty directory skeletons — `total 0` regular files; leftover dir trees from worktrees already `git worktree remove`d).
- Owner = `root` (this harness session ran as root, against the persistence rule "launch as mugunthansrinivasan, not root/sudo").

My sanctioned tools (safety gate #1: `git worktree remove`/`prune` ONLY) **cannot act on these** — git doesn't know them — and `rm -rf` is forbidden by the brief. They cost negligible disk and don't inflate `git worktree list`. **Decision: SKIP + report under needs-review.** A session running as `mugunthansrinivasan` could `rm -rf` them (24K) if desired; not worth a root `rm`. **LESSON: "orphaned filesystem dir (no .git, not in .git/worktrees/)" ≠ "worktree" — the brief's worktree-removal toolset is inapplicable; don't escalate to rm -rf just because a dir sits in the worktree path namespace.**

## Local branch prune (step D) — the substantive win: 144 → 58

Built sets with fast set-ops (a per-branch bash loop over 144 branches TIMED OUT at 2min — use `comm`/`grep -Fxf` against pre-dumped files, not a loop):
- `merged_refs.txt` = `gh pr list --state merged --limit 400 --json ... headRefName` (386 refs)
- `open_refs.txt` = open PRs (2: `chore/infra-housekeeping-scribe` #473, `feature/category-monitor/notifications-route` #489)
- `checkedout_refs.txt` = `git worktree list --porcelain | awk '/^branch/'` (14)
- classify each local branch → del-candidate iff in merged set AND not (held | integration | checked-out | open).

**Deleted 86 local branches with `git branch -D`** (B13: squash-merged branches look unmerged; `-D` matched to the merged-PR list), needing `MESELL_ALLOW_MASTER_GIT=1` (B10 blocks branch delete in master tree). 86/86 OK, 0 failures.
- EXCLUDED & kept: held `feature/google-auth` (B11); 10 integration branches (`*/integration` + odd locals `_integration`, `__gate_integration`) per gate #6 / step-D "exclude integration"; 13 checked-out (active worktree) branches; 1 open-PR branch.
- **GOTCHA averted:** `feat/google-auth-backend` (#295), `feat/google-auth-frontend` (#296), `feature/google-auth-fix/auth` (#372), `feature/gauth-catalog-logout/auth` (#374) are SEPARATE merged branches — NOT the HELD `feature/google-auth`/`gauth-live`. The held-exclusion is an EXACT match on those two names only, so the gauth *derivatives* correctly delete. Re-asserted a guard grep (`grep -xE 'feature/google-auth|gauth-live' candidates` must be empty) right before deleting.
- 31 branches landed in **needs-review** (not matched to any merged PR — e.g. `tmp-rebase-457/460/461`, `*-local` land branches, `backup/master-develop-presync-20260622`, some `docs/qa-*` board branches, `feature/qa-wave-3/{backend,frontend}`, `feature/qa-wave-infra/infra`). Bias-to-caution: SKIPPED all 31 (could be merged-without-PR, closed-unmerged, or never-PR'd). Did NOT delete.

## Remote stray branches (step E) — 82 candidates LISTED, NOT deleted

`remote ∩ merged − (integration|held|open|checked-out)` = **82 remote branches** clearly merged. The brief allows `git push origin --delete` OR "if in any doubt, just LIST." **Chose to LIST** (did not delete remotely): I'm running as root, 13 harness worktrees are concurrently active, remote deletion is irreversible, and the brief frames listing as the safe default. The 82-branch list is in the session report for the founder to bulk-delete via UI/CLI when ready. (`git remote prune origin` was run — safe, only cleans local remote-tracking refs.)

## Co-tenancy (rule #6, AGAIN) — origin/develop was a MOVING TARGET mid-session

- Master working tree was on local `develop` @ `ad4713d`, **BEHIND** `origin/develop` (which advanced to `7fae4f0` during the session), with a root-owned STALE 1430-line `MEMORY.md` and a dirty `docs/status/feature_board_frontend.md` (a sibling's). Committed NOTHING from the master tree.
- **Memory restructure landed mid-window:** `origin/develop` `MEMORY.md` flip-flopped between a fetched lean 120-line view and a large-inline view across two fetches SECONDS apart — a fetch race while PRs #493 (restructure 8 fat MEMORY.md → lean index + `mem/` detail files) + #494 (SessionStart prose-drift guard, closes W10) were settling. Re-fetched to a single stable tip before trusting anything: `7fae4f0` = lean 120-line `MEMORY.md` + **74 `mem/mem_NN_*.md` files** (highest = mem_74). **LESSON: when origin/develop is advancing under concurrent sessions, never act on a single `git show origin/...` read — re-fetch and re-confirm tip + line-count + file-count are mutually consistent before appending.**
- New memory format: `MEMORY.md` is now a lean index (newest-first; index line shape `- [topic (date)](mem/mem_NN_slug.md) — summary`), detail in `mem/`. Mixed state tolerated (recent entries still fat `>` blocks at top; older migrated to `mem/`). This entry IS that new detail file (`mem_75`).

## Final state
- `git worktree list`: 14 before, 14 after (all `.claude/worktrees/*` harness + master — untouched; confirmed 12 `agent-*` still present).
- Local branches: 144 → 58.
- Remote: 0 deleted (82 listed); `git remote prune origin` run.
- Never `rm -rf`'d anything; never touched `.claude/worktrees/agent-*`; never deleted a held/integration/open-PR branch.
