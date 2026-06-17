# Master-Tree Guard — permanent fix for "a session overrode the master tree"

**Status:** ACTIVE (this PR). Root-cause fix for the recurring contamination incidents
(2026-06-15 section-3; 2026-06-16 ui-ds-phase0).

## The problem

Sessions / sub-agents sometimes run `git checkout <branch>` or `git commit` **directly
in the MeeSell master working tree** (`/Users/mugunthansrinivasan/Project/mesell`)
instead of an isolated worktree. That flips the founder's VS Code branch off `develop`
and layers commits / uncommitted work onto the wrong place.

The existing safeguards — `SECTION_DISPATCH_PROTOCOL.md` §0 R1–R5 and the "MANDATORY
WORKTREE CHECK" in boot prompts — are **documentation**. They only work if every actor
reads and obeys them every time, which fails after context compaction, for sub-agents
that never read the protocol, or as a simple reflex (`git checkout -b` is muscle memory).
Prose cannot enforce a prose-compliance problem. This guard makes it **mechanical**.

## The fix — two layers

### Layer 1 (primary): Claude Code PreToolUse `Bash` hook
`.claude/hooks/guard-master-tree-git.sh`, wired in `.claude/settings.json`. The harness
runs it before every Bash call and **blocks** the contaminating git ops when they target
the master tree. No install — Claude Code loads project hooks automatically.

| In the master tree | Result |
|---|---|
| `git checkout -b …`, `git switch -c …` | 🚫 block (branch creation) |
| `git checkout <feature>`, `git switch <feature>` | 🚫 block (switch off base) |
| `git commit`, `git add`, `git merge`, `git rebase`, `git cherry-pick`, `git revert` | 🚫 block |
| `git reset --hard/--merge/--keep`, `git branch -f/-D/-M` | 🚫 block |
| `git checkout develop` / `main`, `git checkout -- <file>` | ✅ allow (master belongs on base) |
| `git worktree …`, `git fetch`, `git pull --ff-only`, `git status/log/…`, `git stash`, `gh …` | ✅ allow |
| **Anything in a worktree** (`/tmp/mesell-wt/*`, `.claude/worktrees/*`) | ✅ allow everything |

The guard is **fail-open**: any parse error / missing `jq` / unmatched shape → allow. A
guard bug can never brick sessions; worst case it degrades to today's behavior. Tested by
`.claude/hooks/guard-master-tree-git.test.sh` (38 cases, block + allow + worktree + override).

### Layer 2 (secondary): git `pre-commit` hook
`.githooks/pre-commit` refuses commits made in the master tree via paths the Bash guard
can't see (VS Code git UI, raw terminal). Activate once per clone:

```bash
bash scripts/install-git-guards.sh   # sets git config core.hooksPath .githooks
```

> Git has no `pre-checkout` hook, so branch *switching* can't be blocked at the git layer —
> that's why Layer 1 (which sees the command before it runs) is the primary guard. Layer 2
> closes the commit vector for non-Claude tools.

## Deliberate override (rare Director / founder recovery)

A legitimate master-tree recovery (e.g. restoring it to `develop`, stashing churn) is
exactly the kind of op the guard blocks. Prefix the command with the override token:

```bash
MESELL_ALLOW_MASTER_GIT=1 git checkout develop     # honored by both layers
```

`git checkout develop` / `git checkout main` are allowed **without** the override (the
master tree is supposed to live on its base) — the override is only needed for the
genuinely unusual ops.

## The correct pattern (unchanged)

Every section / phase / fix runs in its own worktree off `origin/develop`:

```bash
git worktree add -b feature/<name> /tmp/mesell-wt/<name> origin/develop
cd /tmp/mesell-wt/<name>
```

One worktree = one branch = one PR. The founder merges every PR. See
`SECTION_DISPATCH_PROTOCOL.md` §0.
