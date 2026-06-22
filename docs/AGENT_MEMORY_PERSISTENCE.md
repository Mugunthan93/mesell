# Agent-Memory Persistence & Permissions

> Landed 2026-06-22 by `meesell-infra-builder` (session `mesell-fix-agent-memory-selfheal-infra-session-1`).
> Companion to `docs/dev/MEMORY_INDEX_CONVENTION.md` (the worktree-safe append rule) and
> `docs/dev/WORKTREE_ISOLATION.md` (why dispatched agents are worktree-isolated).

## Why this exists

Each MeeSell agent reads and appends to its own memory under
`.claude/agent-memory/meesell-<role>/`. Two recurring failure modes silently break that loop:

1. **Wrong launch user** — a session launched as `root` (or via `sudo`) creates memory files owned
   by `root`, which a later non-root agent cannot append to. The whole decentralized-memory ecosystem
   (CLAUDE.md rules 2–4) depends on every agent being able to write its own memory.
2. **Wrong write tool from an isolated agent** — every *dispatched* agent runs in a harness-managed
   throwaway worktree (`.claude/worktrees/agent-*`). An `Edit`/`Write` to a shared-tree memory file
   from there is redirected to that throwaway copy and is lost when the worktree is reaped.

The two rules below are the durable fixes; a `SessionStart` hook provides a best-effort self-heal for
case 1.

## Rule 1 — Launch as `mugunthansrinivasan`, not root / sudo

Launch every MeeSell Claude session as the founder user `mugunthansrinivasan` (group `staff`), never
as `root` and never under `sudo`.

- Root-created files under `.claude/agent-memory/` become `root`-owned and block non-root agents from
  appending — the failure is silent (the append errors out, the learning is dropped).
- The durable fix is the **launch user**. The memory root is owned `mugunthansrinivasan:staff` with
  directories `setgid` + group-writable so any `staff` process can append.

### SessionStart self-heal (mitigation, not a substitute)

`.claude/settings.json` wires a `SessionStart` hook
(`.claude/hooks/heal-agent-memory-perms.sh`) that, on every session start, defensively makes
`.claude/agent-memory` group-writable + `setgid` so a future root-created file does not re-block the
group:

```sh
#!/usr/bin/env bash
d="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/.claude/agent-memory"
[ -d "$d" ] || exit 0
chmod -R g+w "$d" 2>/dev/null || true
find "$d" -type d -exec chmod g+s {} + 2>/dev/null || true
exit 0
```

It does **not** `chown` (that needs root and would noise/fail for the normal non-root session). It
always `exit 0`, so it can never block session start. It is a mitigation only — **Rule 1 (the launch
user) is the real fix.**

## Rule 2 — Isolated agents persist shared memory via git-plumbing/Bash, not Edit/Write

A *dispatched* (isolated) agent is worktree-isolated by the harness, so the `Edit`/`Write` tools write
to a throwaway worktree copy that never reaches the shared main tree. Such an agent MUST persist any
shared-tree memory through a **Bash / git-plumbing append to the main tree**, never via `Edit`/`Write`.

This is the same sanctioned scribe pattern already documented in
`docs/dev/MEMORY_INDEX_CONVENTION.md` → *"The worktree-safe append rule (CRITICAL)"*. In short:
append with a shell redirect (or `git hash-object` / `update-index` plumbing) against the absolute path
in the main tree, e.g.:

```bash
cat >> /Users/mugunthansrinivasan/Project/mesell/.claude/agent-memory/meesell-<role>/MEMORY.md <<'EOF'

- [topic-slug detail (YYYY-MM-DD)](topic-slug.md) — one-line takeaway.
EOF
```

Standalone leads with a sanctioned master-tree git path (`MESELL_ALLOW_MASTER_GIT=1`) satisfy this
rule too — that is still a Bash/plumbing write, not an `Edit`-tool write. The append stays atomic at
the filesystem level and independent of the harness's tracked-file view.

> Ownership boundary still applies (CLAUDE.md rule 4): an agent persists only **its own** memory this
> way; no agent writes another agent's memory directory.
