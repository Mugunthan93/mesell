# Worktree protocol for parallel feature planning sub-sessions

**Owner:** `meesell-infra-builder`
**Audience:** Founder, future agents, anyone debugging "why are my sub-sessions clobbering each other?"
**Companion:** `scripts/launch-planning-session.sh`, `_status/README.md`

---

## 1. Why worktrees

V1 has 9 feature planning sessions. The founder runs many in parallel to compress wall-clock time. The first attempt at parallelism had every sub-session use the same physical working tree at `/Users/mugunthansrinivasan/Project/mesell/`. Each sub-session ran:

```
git checkout -b feature/{slug}/planning
```

Concurrent sub-sessions raced on `HEAD`. Symptoms observed:
- Sub-session A checks out `feature/auth-otp/planning`, sub-session B then runs `git checkout -b feature/smart-picker/planning`, A's working tree silently switches under it.
- File writes from A land on B's branch.
- Lost work (`git status` shows clean even though A authored files).
- `feature_planning_master.md` updates collided — last writer wins, earlier sub-sessions' rows reverted.

The fix is `git worktree`: each sub-session gets its own *physical* directory pointing at its own branch. Two sub-sessions can never collide on `HEAD` because they don't share `HEAD`. The shared `.git/` repo is fine — only the *checkout* is duplicated.

---

## 2. Architecture

```
/Users/mugunthansrinivasan/Project/mesell/        ← MASTER TREE
├── .git/                                          ← shared object store
├── .claude/
│   ├── agent-memory/      ← canonical (master writes here)
│   ├── agents/            ← canonical (master writes here)
│   └── settings.json      ← per-tree (NOT symlinked)
├── docs/
│   └── plans/features/
│       ├── _status/                ← sub-sessions write {slug}.yaml here
│       ├── _WORKTREE_PROTOCOL.md   ← this file
│       └── feature_planning_master.md ← regenerated from _status/*.yaml
├── scripts/launch-planning-session.sh
└── ...rest of the master tree...

/tmp/mesell-wt/                                   ← WORKTREE BASE
├── auth-otp/                                     ← worktree #1 (branch feature/auth-otp/planning)
│   ├── .claude/
│   │   ├── agent-memory → /Users/.../mesell/.claude/agent-memory   (symlink)
│   │   ├── agents       → /Users/.../mesell/.claude/agents         (symlink)
│   │   └── settings.json (worktree-local copy, NOT symlinked)
│   ├── docs/plans/features/auth-otp/FEATURE_PLAN.md  ← sub-session writes here
│   └── ...rest of branch checkout...
├── smart-picker/                                 ← worktree #2
├── catalog-form/                                 ← worktree #3
├── ai-autofill/                                  ← worktree #4
├── image-precheck/                               ← worktree #5
├── live-preview/                                 ← worktree #6
├── price-calculator/                             ← worktree #7
├── tracking-dashboard/                           ← worktree #8
└── xlsx-export/                                  ← worktree #9
```

Every worktree shares the same `.git/` (under the master tree). Each has its own checked-out files. Each has a symlink farm under `.claude/` so that agent memory and agent specs are the same physical files everywhere.

---

## 3. Per-worktree layout

### What lives in the worktree (per-branch, real files)
- `docs/plans/features/{slug}/FEATURE_PLAN.md` — authored by this sub-session
- `docs/plans/features/_status/{slug}.yaml` — written by this sub-session at session start + close (lives on the same branch as the FEATURE_PLAN.md)
- The rest of the branch's committed state — `backend/`, `frontend/`, `docs/`, etc. — for read context only; sub-sessions DO NOT modify production code in planning sessions

### What is symlinked (shared with master tree)
- `.claude/agent-memory/` — agent memories MUST be the same physical files across all worktrees, otherwise reads from sibling agents would see stale snapshots
- `.claude/agents/` — agent spec files; the live spec is the truth in master, worktrees just reference it

### What is per-worktree (NOT shared)
- `.claude/settings.json` — each worktree gets its own copy from the original branch checkout. Sub-sessions MUST NOT modify this (hooks, agent routing — see `meesell-infra-builder/MEMORY.md` 2026-06-04 entry)
- All non-`.claude/` working tree files — `node_modules/`, `__pycache__/`, build artifacts, etc.

### What NEVER lives in the worktree
- The master tracker `feature_planning_master.md` — this stays in the master tree only. Sub-sessions communicate state via `_status/{slug}.yaml`, not by editing the master tracker.
- Cross-feature plans, leads' specs, PR templates, governance docs — those are master-tree-only files; sub-sessions read them via the worktree (they ARE checked out — same branch base as develop) but should not modify them in a feature planning session.
- Worktree base `/tmp/mesell-wt/` itself — survives only until system reboot or manual cleanup; treat it as ephemeral compute, not persistent state. Persistent state lives in the branch and the `_status/` file (which is committed).

---

## 4. Launching a planning sub-session

Step-by-step from the master Director (or founder) terminal:

```bash
# 1. From the master tree, create / re-attach the worktree.
cd /Users/mugunthansrinivasan/Project/mesell
scripts/launch-planning-session.sh auth-otp
# → prints "WORKTREE READY" banner with the path + branch + symlinks

# 2. Open a brand-new terminal window or tab (so the new Claude session
#    has a fresh shell — do NOT reuse the same shell).

# 3. cd into the worktree:
cd /tmp/mesell-wt/auth-otp

# 4. Open a new Claude Code session in this directory.

# 5. Paste the prompt block from:
#    docs/plans/features/auth-otp/PLANNING_DISPATCH.md
#    (the section under "## PASTE THIS PROMPT INTO THE NEW SESSION")
```

The launcher script:
- Validates the slug is one of the 9 V1 features
- Computes the worktree path (`/tmp/mesell-wt/{slug}`) and branch name (`feature/{slug}/planning`)
- Re-attaches if the worktree already exists (idempotent), creates from local branch / remote branch / `origin/develop` as appropriate
- Symlinks `.claude/agent-memory/` and `.claude/agents/` so memory + specs stay shared

---

## 5. Cleanup

| When | Action | Reason |
|---|---|---|
| Sub-session finishes and PR is opened | Leave the worktree in place | Founder may want to push fix-up commits during PR review |
| PR merged into `develop` | `git worktree remove /tmp/mesell-wt/{slug}` | Branch is no longer in active use, reclaim the checkout |
| PR merged AND branch is fully delivered | Optionally also `git branch -D feature/{slug}/planning` and `git push origin --delete feature/{slug}/planning` | History is preserved in the merge commit |
| PR still open (founder undecided) | DO NOT remove the worktree or delete the branch | Removing the worktree while a sub-session is active loses uncommitted edits |
| `/tmp` cleared by macOS reboot | The worktree directory disappears; `git worktree list` shows the stale entry. Run `git worktree prune` then re-launch | Files committed are safe (they're in `.git/`); uncommitted local edits in the worktree are LOST |

NEVER `rm -rf /tmp/mesell-wt/{slug}` directly while git considers it active — use `git worktree remove`. Direct `rm` leaves a dangling reference and `git worktree list` will keep printing the stale path until `git worktree prune` runs.

---

## 6. Master tracker reconciliation

```
┌─────────────────────────────┐
│ Sub-session (worktree #N)   │
│ feature: {slug}             │
│                             │
│ Writes:                     │
│  _status/{slug}.yaml        │
└──────────────┬──────────────┘
               │
               │  commits on feature/{slug}/planning
               │  pushes to origin
               │
               ▼
┌─────────────────────────────┐
│ Master Director session     │
│ (master tree, develop)      │
│                             │
│ Reads: _status/*.yaml       │
│ Regenerates:                │
│  feature_planning_master.md │
└─────────────────────────────┘
```

Flow:
1. Sub-session for `auth-otp` runs in `/tmp/mesell-wt/auth-otp`, writes `docs/plans/features/_status/auth-otp.yaml`, commits to `feature/auth-otp/planning`.
2. Master Director session (in the master tree on `develop`) pulls every feature branch's `_status/{slug}.yaml` (or reads from `_status/` once the planning PRs are merged).
3. Master regenerates the `## Planning state — 9 V1 features` table in `feature_planning_master.md` from the YAML rows.
4. Master appends a `## Recent updates log` line per state transition.
5. Master commits the regenerated tracker on `develop` directly (or via a short-lived `chore/aggregate-status` branch).

The aggregator implementation is a separate dispatch — this protocol document only describes the flow.

---

## 7. Gotchas + safeguards

### 7.1 Shared `.claude/agent-memory/` means concurrent same-file writes
Symlinking memory means two sub-sessions writing to the SAME memory file at the same time (e.g., both append to `meesell-backend-coordinator/MEMORY.md`) will race at the filesystem level. Safeguards:
- Same-file edits MUST be append-only — never rewrite, never edit in place.
- Each appended block MUST start with a unique session header line (`## Session mesell-{slug}-planning-session-{N} — YYYY-MM-DD`).
- If a sub-session needs to mutate existing content (correction), it appends a correction block instead of in-place edit.
- For higher-confidence isolation, prefer per-session topic files: `meesell-{role}/{feature_slug}_feature.md`. The master MEMORY.md just indexes them.

### 7.2 Don't delete `/tmp/mesell-wt/` while a sub-session is active
Removing the directory while another Claude Code window has files open in it kills uncommitted edits and leaves git's worktree metadata pointing nowhere. Use `git worktree list` to see what's active before any cleanup.

### 7.3 `git worktree list` is the canonical state check
The master Director session, before launching new sub-sessions or doing bulk cleanup:
```bash
cd /Users/mugunthansrinivasan/Project/mesell
git worktree list
```
This prints one line per active worktree (path + SHA + branch). The launcher script uses this same source-of-truth check to detect existing worktrees.

### 7.4 `git worktree prune` removes stale entries silently
If `/tmp/mesell-wt/{slug}` was deleted out-of-band (reboot, `rm`, container restart), the git metadata becomes a dangling reference. `git worktree prune` removes the dangling reference but does NOT recreate the worktree. Re-run `scripts/launch-planning-session.sh {slug}` to recreate.

### 7.5 Symlink loop guard
The launcher does NOT symlink `.claude/settings.json` because that file is per-tree (hooks, agent routing). If a future change to the launcher script symlinks more than `agent-memory/` + `agents/`, audit for loop hazards: a symlink from the worktree pointing at a directory in the master that contains another symlink pointing back can create infinite-loop traversals for tools that walk `.claude/`.

### 7.6 Watch for branch-tip drift
A worktree's branch tip moves only when *that worktree's* shell pushes a commit. If you push a fix-up commit to `feature/{slug}/planning` from the master tree (instead of the worktree), the worktree's `HEAD` will be one commit behind until you `git pull` inside the worktree. Rule of thumb: edits for a feature happen ONLY inside that feature's worktree.

### 7.7 `.gitignore` is shared via the branch
Each worktree gets the same `.gitignore` (it's a tracked file on the branch). If a sub-session adds a directory that's not in `.gitignore`, the master Director session may see it when it scans the master tree (because the worktree is technically also a checkout of the same repo).

---

## 8. Commands cheat sheet

| Goal | Command |
|---|---|
| Create / re-attach a worktree for a slug | `scripts/launch-planning-session.sh <slug>` |
| List all active worktrees | `git worktree list` |
| List with porcelain (machine-readable) | `git worktree list --porcelain` |
| Remove a worktree (clean exit) | `git worktree remove /tmp/mesell-wt/<slug>` |
| Force-remove (uncommitted edits will be LOST) | `git worktree remove --force /tmp/mesell-wt/<slug>` |
| Prune stale references | `git worktree prune` |
| Lock a worktree against accidental removal | `git worktree lock /tmp/mesell-wt/<slug>` |
| Unlock | `git worktree unlock /tmp/mesell-wt/<slug>` |
| Move a worktree to a new path | `git worktree move /tmp/mesell-wt/<slug> /new/path` |
| Check what branch a worktree is on | `git -C /tmp/mesell-wt/<slug> rev-parse --abbrev-ref HEAD` |

---

## 9. When NOT to use a worktree

- Single-session work in the master tree (founder running ad-hoc edits) — just edit in `/Users/mugunthansrinivasan/Project/mesell/`.
- Cross-cutting changes spanning multiple features (a worktree is per-feature; a cross-cutting change needs `develop` directly or a dedicated short-lived branch).
- Infra work owned by `meesell-infra-builder` — infra session works in the master tree, not in a feature worktree. (This dispatch is the meta-case: the infra builder authors the worktree TOOLING in the master tree; sub-sessions then USE that tooling in worktrees.)

---

## 10. References

- Launcher: `/Users/mugunthansrinivasan/Project/mesell/scripts/launch-planning-session.sh`
- Status format: `/Users/mugunthansrinivasan/Project/mesell/docs/plans/features/_status/README.md`
- Master tracker: `/Users/mugunthansrinivasan/Project/mesell/docs/plans/features/feature_planning_master.md`
- Per-feature dispatch prompts: `/Users/mugunthansrinivasan/Project/mesell/docs/plans/features/{slug}/PLANNING_DISPATCH.md`
- Branch model (forthcoming): `docs/plans/repo_management/MASTER_PLAN.md` §1
- Session naming (forthcoming): `docs/plans/repo_management/MASTER_PLAN.md` §4
- Infra builder memory: `.claude/agent-memory/meesell-infra-builder/MEMORY.md`
