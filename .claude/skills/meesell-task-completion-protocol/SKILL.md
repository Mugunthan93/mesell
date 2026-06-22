---
name: meesell-task-completion-protocol
description: >-
  MeeSell's two NON-NEGOTIABLE standing rules that define when a task is actually
  DONE: (A) Persist-on-finish — durable outputs must be COMMITTED and PUSHED to the
  remote, never left as uncommitted master-tree dirt; and (B) Rebuild-localhost-on-merge
  — every merge to develop is followed by an affected-scope localhost rebuild so the
  running dev stack matches develop. Use this skill WHENEVER you are finishing any task,
  about to report "done", deciding whether work is complete, persisting memory / STATUS /
  board / spec artifacts, or you just merged (or are about to merge) anything to develop —
  even if the user does not say "commit", "push", or "rebuild" explicitly. This is the
  canonical home of both rules; CLAUDE.md, docs/GIT_WORKFLOW.md, and docs/dev/ENV_MANAGER.md
  point here. Applies to every meesell-* agent and skill.
---

# MeeSell Task Completion Protocol (NON-NEGOTIABLE)

> Founder-ruled standing process for the entire `meesell-*` fleet (agents + skills),
> 2026-06-22. This is the single source of truth for the two rules below. The root
> `CLAUDE.md`, `docs/GIT_WORKFLOW.md`, and `docs/dev/ENV_MANAGER.md` reference this skill
> rather than duplicating the full text. If any of those ever disagrees with this skill on
> the *mechanics*, fix the disagreement — there is one canonical wording, here.

There are two rules. Both change the **Definition of Done**.

---

## RULE A — Persist-on-finish (commit + push artifacts)

**A task is NOT done until its durable outputs are committed AND pushed to the remote.**
Durable outputs are never left as uncommitted changes in the master tree.

**Scope of "durable outputs":**

- `.claude/agent-memory/**` — `MEMORY.md` and every other memory file
- `docs/status/STATUS_*.md`
- `docs/status/feature_board_*.md`
- any spec / doc the task produced or edited

**Definition of Done explicitly includes "the artifacts are on the remote"**, not merely
edited on disk. "I updated my memory" is only true once that memory is pushed.

**How each kind of agent satisfies Rule A:**

1. **Agents working in a worktree on a feature branch.** Commit the durable outputs to the
   feature branch so they ride the PR. They are pushed the moment the PR opens / updates —
   nothing extra to do.
2. **Fast-mode coordinators / standalone agents editing in the master tree.** You must
   commit **and push** them — never leave them as uncommitted master-tree dirt. Two
   sanctioned routes:
   - a dedicated `chore/<slug>-scribe` branch + PR (cut off `origin/develop` in an isolated
     worktree, `git add` ONLY your own files, push, open the PR); **or**
   - the **git-plumbing route** for write-protected `.claude/` files:
     `git hash-object -w <file>` → `git update-index --add --cacheinfo
     100644,<blob>,<path>` → `git commit` → `git push`. (The PreToolUse boundary hook blocks
     `Edit`/`Write` on `.claude/`, so plumbing is the route there. Verify the staged diff is
     pure-append for `MEMORY.md`-style files before committing.)
3. **Isolated builders that cannot write their own memory.** REPORT your learnings in your
   final message. The **dispatching coordinator scribes them AND pushes them** — the
   coordinator's task is not done until the builder's owed memory is on the remote.

**The anti-pattern Rule A kills:** edits sitting dirty in the shared master working tree.
They are invisible to everyone else, they collide with the next session, and they are one
`reset --hard` away from gone. If your output isn't pushed, your task isn't finished.

---

## RULE B — Rebuild-localhost-on-merge

**Every merge to `develop` MUST be followed by a localhost rebuild so the running dev stack
reflects the merge.** A merge is not "done" until localhost matches `develop`.

The merging agent (or the master session that performed the merge) triggers the rebuild.

**Affected scope only — scope it sensibly:**

- **Frontend / federation merge** → rebuild the affected baseline (shell + the changed
  remotes; the develop checkout is slot 0 / the shared baseline that every worktree
  federates from, so it is refreshed as a unit).
- **Backend merge** → restart the baseline backend (`uvicorn --reload` on `:8000`).
- **Docs-only merge** → **no rebuild.** Do not force a full 8-port rebuild for a trivial
  docs/board/status merge.

**Exact command flow (mechanical — run from the develop/baseline checkout):**

```bash
# 0. Be in the baseline (develop) checkout = slot 0. The dev-manager always reads the
#    baseline tree's .nexus/ state regardless of which worktree invokes it.

# 1. Pull the merge into the baseline checkout.
git pull --ff-only origin develop

# 2A. FRONTEND / FEDERATION merge — rebuild the baseline (shell + all MFEs, serialized
#     under the single build lock; the baseline is the shared fallback, kept consistent).
python3 tools/meesell_env.py baseline refresh
#     (targeted, per-worktree rebuilds use `up <wt> --mfe a,b`; the develop baseline
#      itself rebuilds as a unit via `baseline refresh`.)

# 2B. BACKEND merge — restart the baseline backend (uvicorn --reload on :8000).
#     Stop the old uvicorn, then relaunch it against the pulled tree.

# 2C. DOCS-ONLY merge — skip the rebuild entirely.

# 3. Verify the affected ports are healthy (live HTTP probes, not stale PIDs).
python3 tools/meesell_env.py status
#     Expect: shell :4200, MFEs :4201-4207 (the changed ones rebuilt), backend :8000 = up.
#     Spot-check with curl: e.g. curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4200/

# 4. Refresh the :7700 dev-manager dashboard so it reflects the new state.
#     (If not already running: python3 tools/meesell_env.py dashboard --port 7700)
```

See `docs/dev/ENV_MANAGER.md` for the full env-manager semantics (slot model, RAM guard,
build lock, baseline reuse) and `docs/dev/ENV_DASHBOARD.md` for the `:7700` dashboard.

**The anti-pattern Rule B kills:** "merged to develop, walked away" while the running
localhost still serves the pre-merge bundle — so the founder tests stale code, files a
phantom bug, and a fix gets chased that already landed. A merge that isn't reflected on
localhost is a merge that isn't done.

---

## Quick gate before you say "done"

- [ ] **Rule A** — every durable output (memory, STATUS, board, produced specs/docs) is
      committed **and pushed** (rode a PR, or landed via a `chore/*-scribe` PR / git-plumbing
      commit). Nothing left dirty in the master tree.
- [ ] **Rule A (isolated builder)** — if you cannot write your own memory, you REPORTED the
      learnings and the dispatching coordinator owns scribing + pushing them.
- [ ] **Rule B** — if you merged to develop, you ran the affected-scope localhost rebuild
      and verified the affected ports are healthy (or it was a docs-only merge → correctly
      skipped).
