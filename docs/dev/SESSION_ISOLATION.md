# Concurrent-Session Isolation for the MeeSell Repo

> Session-level analog of agent worktree isolation. References:
> `docs/dev/WORKTREE_ISOLATION.md` (agent/specialist isolation) and
> `docs/dev/CLAUDE_FEATURE_ADOPTION.md` (adoption program).
> Authored 2026-06-21 by `meesell-infra-builder` (session
> `mesell-session-isolation-infra-session-1`).

## Problem (observed 2026-06-21)

Multiple concurrent Claude sessions sharing **one** repo checkout (the master tree at
`/Users/mugunthansrinivasan/Project/mesell`) cause git collisions. All three of these were
observed in a single day:

- **A parallel session switched a worktree agent's branch out from under it.** One session ran
  `git checkout` in the shared checkout while another session was mid-task on that same checkout,
  flipping the active branch and pointing the second session's work at the wrong place.
- **A stale `origin/develop` ref swept an unrelated commit into a PR.** A branch cut with
  `git checkout -b X origin/develop` inherited a foreign, still-unmerged commit because the local
  `origin/develop` ref had been advanced by another session. The unrelated commit showed up in the
  PR diff and had to be rebased out (`git rebase --onto origin/develop <foreign-sha> <branch>` +
  force-push).
- **A foreign uncommitted memory edit had to be stashed around.** A master-tree sync found
  uncommitted agent-memory files written by *another* session; they had to be `git stash push -u`'d
  by path and `git stash pop`'d back so the sync (`merge --ff-only`) could proceed without
  discarding another session's work.

The agents recovered each time, but this class of collision **will corrupt work eventually** —
a force-push that drops the wrong commit, a `reset --hard` that eats an unstashed foreign edit, or
a branch flip caught too late.

## Rule

> Each concurrent session MUST operate in its **own** git worktree (or a separate clone) off
> `develop`. Never run two sessions doing git against the same master checkout. **The master tree
> is single-session-at-a-time** — only one session "owns" it.

This is the session-level analog of the specialist worktree rule in
`docs/dev/WORKTREE_ISOLATION.md`: that doc isolates each *code-writing specialist* into its own
worktree so the master tree can never be corrupted by a sub-agent; this doc isolates each
concurrent *session* for the same structural reason. The corruption mechanism (a second actor
running git against a shared checkout) is identical; only the actor differs (session vs specialist).

## How

Launch every additional concurrent session in its **own** worktree (or a separate clone), off the
true remote `origin/develop` — never off the possibly-stale local `develop`/`origin/develop` ref:

```bash
# Always fetch first so origin/develop is the true remote tip.
git fetch origin develop

# Option A — worktree (preferred; shares the object store, cheap):
git worktree add /private/tmp/mesell-wt/<session> -b <branch> origin/develop
cd /private/tmp/mesell-wt/<session>   # this session does ALL its git here

# Option B — separate clone (full isolation, heavier on disk):
git clone <remote-url> /private/tmp/mesell-clone/<session>
cd /private/tmp/mesell-clone/<session>
git checkout -b <branch> origin/develop
```

Then:

- **Exactly one** session owns the master checkout
  (`/Users/mugunthansrinivasan/Project/mesell`) at any time. Every other concurrent session works
  in its own worktree/clone.
- **Verify the PR diff after opening** — `gh pr view <#> --json files` — to catch a foreign commit
  that a stale local `origin/develop` may have swept in. If one slipped in, rebase it out
  (`git rebase --onto origin/develop <foreign-sha> <branch>`) and `git push --force-with-lease`.
- **Tear down at session end:** `git worktree remove /private/tmp/mesell-wt/<session>` +
  `git worktree prune` (or delete the clone). Stale worktrees waste disk and add to build/RAM
  confusion (see the 8GB cap in `docs/dev/WORKTREE_ISOLATION.md`).

## If you must touch the shared master checkout

When a sync against the master tree is unavoidable and another session may have left uncommitted
edits there (e.g. agent-memory appends), **never discard** them:

- Inspect every uncommitted path. If a path's content already exists on `origin/develop`
  (`git diff origin/develop -- <path>` is empty), it is safe to fast-forward over.
- If any path has **unique** content not on origin (foreign session work or this-session memory
  appends), stash by path before fast-forwarding and restore after:

  ```bash
  git stash push -u -- <those-paths>
  git merge --ff-only origin/develop
  git stash pop
  ```

- **NEVER `reset --hard`** when any path carries unique content. If `stash pop` conflicts, leave the
  stash in place and report rather than forcing a resolution that could lose another session's work.

## Relationship to the adoption program

This rule is part of the Claude Code feature-adoption program (`docs/dev/CLAUDE_FEATURE_ADOPTION.md`)
and sits alongside `docs/dev/WORKTREE_ISOLATION.md`. Together they make shared-checkout corruption
impossible by construction: specialists are isolated per-task, sessions are isolated per-session, and
the master tree stays single-owner.
