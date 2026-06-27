## Founder-parked master-tree UI-refactor stash — MESELL_ALLOW_MASTER_GIT override — 2026-06-18

**Task class:** founder-authorized master-tree git op (single-agent fast mode, dev-only, ₹0). Founder said "stash it now, deal with later." This DELIBERATELY OVERRIDES my standing master-tree contract ("ONLY git pull --ff-only; never stash/reset/checkout") — the documented escape hatch is the env var `MESELL_ALLOW_MASTER_GIT=1` prefixed on the git command.

**NEW knowledge — the master-tree guard's escape hatch:** `MESELL_ALLOW_MASTER_GIT=1` is the intended override for deliberate, founder-approved master-tree git operations. Use it ONLY when explicitly authorized in the prompt. My memory previously only ever recorded the contract's RESTRICTION (ff-only, no stash) — this is the first time the escape hatch was exercised. The guard is presumably a pre-commit/pre-tooluse hook; the env var bypasses it for the one command it prefixes.

**Exact command that worked (PATHSPEC stash — only the listed paths touched):**
```
MESELL_ALLOW_MASTER_GIT=1 git -C /Users/.../mesell stash push -m "<msg>" -- <path1> <path2> ... <path16>
```
Listing each path explicitly after `--` is the safety mechanism: a pathspec stash touches ONLY those paths, leaving every other dirty/untracked file in the working tree. This is how you surgically park a SUBSET of a dirty tree.

**What got parked (16 paths):** the pre-existing UI refactor — `frontend/apps/{mfe-auth,mfe-catalog,mfe-dashboard,mfe-export,mfe-onboarding,mfe-pricing,shell}/...` components + `frontend/libs/{composites/auth-layout,ui-kit/input,ui-kit/textarea}` + `shell/public/federation.manifest.json` + shell layout (ts/html/css). New stash ref: **stash@{0}** with message "master-tree UI refactor + 43xx local-dev manifest — founder-parked 2026-06-18 (recover with stash apply)".

**CRITICAL EXCLUSIONS (left in working tree, NOT stashed — pathspec made this trivial):**
- `backend/app/i18n/messages_en.py` — LIVE i18n hot-patch the running --reload backend (:8000) is serving (`validation.generic.missing` fallback for required-field 422s, the 4th missing-key fix per master memory finding-i18n-generic-missing-gap). Stashing it would REVERT tonight's fix. Confirmed survived: `grep -c validation.generic.missing` = 1 BEFORE and AFTER.
- `docs/status/STATUS_*.md` (4) + `.claude/agent-memory/*/MEMORY.md` (6) — current-session records.
- untracked `.claude/statusline-monitor.sh`, `frontend/.claude/` — left alone (pathspec doesn't touch untracked anyway).

**RECOVERY command (give to founder / for later):**
```
MESELL_ALLOW_MASTER_GIT=1 git -C /Users/.../mesell stash apply stash@{0}
```
Use `apply` (not `pop`) to keep the stash entry until confident. NOTE: stash refs SHIFT — `stash@{0}` is only valid until another stash is pushed (then it becomes `{1}`, `{2}`...). The repo already has 12 stashes (now 13). To recover later, match by the MESSAGE not the index: `git stash list | grep "founder-parked 2026-06-18"` → use that ref.

**5-point verification (all PASS):**
1. `git stash list` → new entry is stash@{0} with exact message.
2. `git status -s` → none of the 16 paths modified (reverted to HEAD b6bda89/#275); messages_en.py + 4 STATUS + 6 MEMORY still ` M`.
3. `grep -c validation.generic.missing messages_en.py` = 1 (hot-patch survived).
4. `curl :8000/health` = healthy (--reload did NOT revert i18n — the file was never touched, so no reload fired on it).
5. `curl :4200/` = 200, `:4205/` = 200 (those serve from the long-lived rebuild-4205 worktree, NOT the master tree — wholly unaffected by a master-tree stash).

**CAVEAT recorded:** if a concurrent session had any of the 16 files open mid-edit, the stash reverted them ON DISK (their unsaved buffer would clobber on next save, OR their on-disk edits are now in stash@{0}). Recoverable via stash apply. Not observed this session (the :4200/:4205 servers run from a separate worktree, not the master tree).

**Why the master tree is dirty at all:** the :4200 shell + :4205 mfe-catalog now serve from the `/private/tmp/mesell-wt/rebuild-4205` worktree (per the same-day shell-swap + advance memory entries). The master tree's 20+ uncommitted source edits are the founder's parked UI-refactor WIP — now formally stashed (the 16 FE paths) while the i18n/status/memory churn stays as live records.

---
