# Memory Index Convention

> Adoption item `memory-index-convention-doc`. Reference: `docs/dev/CLAUDE_FEATURE_ADOPTION.md`.
> Landed 2026-06-21 by `meesell-infra-builder` (session `mesell-memory-index-convention-infra-session-1`).
>
> **GUIDANCE ONLY.** This document defines the convention. It does **not** rewrite any existing
> `MEMORY.md`. Per MeeSell ecosystem rule 4 (decentralized memory), **no agent edits another agent's
> memory** — each agent migrates its own index to this convention on its own schedule.

## Why this exists

Each MeeSell agent reads its own `.claude/agent-memory/meesell-<role>/MEMORY.md` at the **start of
every task**. That read is pure overhead — it buys recall, but every token spent re-reading old
narrative is a token not spent on the task. Several agent `MEMORY.md` files have grown to **1,000+
lines** because learnings were appended as full prose blocks directly into the index. At that size the
mandatory start-of-task read can cost tens of thousands of tokens **before any work begins**, on every
single task.

The fix is structural, not disciplinary: keep `MEMORY.md` as a **lean index** and push the detail into
**linked topic files** that are read only when relevant.

> **Target:** a one-line-per-entry index is roughly **10x smaller** to load than the same knowledge
> kept inline. The start-of-task read becomes cheap, and the agent still finds the detail by following
> the one link that matters for the current task.

## The convention

### 1. `MEMORY.md` is an index, not a journal

`MEMORY.md` contains:

- A short identity / scope blurb (a few lines — who the agent is, what it owns).
- A **newest-first** list of one-line index entries, each linking to a detail file.

It does **not** contain multi-paragraph learnings, command dumps, tables, or run logs. Those live in
detail files.

### 2. One line per entry, newest-first

Each index entry is a single Markdown list item in this shape:

```markdown
- [topic-slug detail (YYYY-MM-DD)](topic-slug.md) — one-sentence summary of the takeaway, ≤ ~200 chars.
```

Rules for the line:

- **Newest entries go at the top** of the list. The most recent context is the most likely to matter,
  and it is the first thing read.
- The **link target** is a sibling file in the same memory directory
  (`.claude/agent-memory/meesell-<role>/topic-slug.md`).
- The **summary** is one sentence — enough to decide *"do I need to open this for the current task?"*
  without opening it. Lead with a marker (e.g. a status word) when it aids triage.
- **No blank lines between entries** — the list stays scannable in one screen.

### 3. Detail files hold everything else

A detail file (`.claude/agent-memory/meesell-<role>/<topic-slug>.md`) holds the full learning:
commands, tables, gotchas, decisions, evidence, run logs. It is read **only when** its index line tells
the agent it is relevant to the current task. One topic per file — no monster files; if a topic grows
two distinct concerns, split it and add a second index line.

### 4. Writing a new learning

After a meaningful task:

1. Write (or append to) the relevant `<topic-slug>.md` detail file with the full learning.
2. Add **one** newest-first index line to `MEMORY.md` pointing at it (or update the existing line's
   date + summary if the topic already has an entry — do not add a duplicate line).

Never paste the full learning into `MEMORY.md` itself.

## The worktree-safe append rule (CRITICAL)

Agent memory lives under `.claude/`. The harness tracks file state for files edited via the `Edit` /
`Write` tools, and code-writing specialists run in **isolated worktrees** (see
`docs/dev/WORKTREE_ISOLATION.md`). A memory append made with the `Edit` tool from inside a worktree —
or any context where the harness's tracked view of the file diverges from disk — can be lost, clobber a
concurrent append, or land in the wrong checkout.

> **Rule:** memory files under `.claude/` MUST be modified via **Bash / git-plumbing append**, never
> the `Edit` tool.

In practice, append with a shell redirect against the absolute path in the **master tree**, e.g.:

```bash
cat >> /Users/mugunthansrinivasan/Project/mesell/.claude/agent-memory/meesell-<role>/MEMORY.md <<'EOF'

- [topic-slug detail (2026-06-21)](topic-slug.md) — one-line summary of the takeaway.
EOF
```

and write the detail file the same way (heredoc to the absolute path). This keeps the append atomic at
the filesystem level and independent of the harness's tracked-file view, so it is safe even when a
specialist is operating from a worktree.

> Some standalone leads run memory appends through their own sanctioned master-tree git path
> (`MESELL_ALLOW_MASTER_GIT=1`); that is compatible with this rule because it is still a Bash/plumbing
> write, not an `Edit`-tool write.

## Ownership boundary (rule 4)

This is **guidance for how each agent maintains its own index**. It does **not** authorize anyone to
reformat or trim another agent's `MEMORY.md`:

- **No agent edits another agent's memory directory.** Migration to this convention is each agent's own
  responsibility, performed against its own `MEMORY.md` and its own detail files.
- When you need context that lives in another agent's memory, **read** it
  (`.claude/agent-memory/meesell-<other-role>/MEMORY.md` → follow the one relevant link); never rewrite
  it. If the info you need is missing there, escalate via the STATUS-file blocker mechanism rather than
  writing into their memory.

## Migration (optional, per-agent, lazy)

No big-bang rewrite is required or wanted. When an agent next touches a bloated `MEMORY.md`, it may, on
its own behalf:

1. Move each inline learning block into a `<topic-slug>.md` detail file (Bash/heredoc, master tree).
2. Replace the block in `MEMORY.md` with a single newest-first index line linking to it.
3. Leave already-linked entries as they are.

Until then, mixed indexes (some inline blocks, some links) are tolerated — the convention is the target
state, applied lazily, by each owner, to its own file.
