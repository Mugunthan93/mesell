# Agent-memory restructure + verify tooling

Reusable tooling to keep each MeeSell agent's `.claude/agent-memory/<role>/MEMORY.md`
a **lean index** instead of an inline-prose journal, per
[`docs/dev/MEMORY_INDEX_CONVENTION.md`](../../docs/dev/MEMORY_INDEX_CONVENTION.md).
This is the remediation path the SessionStart guard
(`.claude/hooks/warn-agent-memory-size.sh`) points offenders at, and it closes the
`docs/GIT_WORKFLOW.md` **W10** deferred gap ("memory files grow unbounded via append;
a compaction/rotation strategy is to be defined").

> **Ownership boundary (CLAUDE.md rule 4):** each agent migrates **its own** file.
> No agent runs this against another agent's memory. The guard only *flags*; the
> owner *remediates*.

## Why prose drift matters

Each agent reads its own `MEMORY.md` at the **start of every task**. A fat journal
(some files reached 1,000+ lines) burns tens of thousands of tokens before any work
begins. PR #493 restructured 8 fat files down to lean indexes (~46K tokens saved per
dispatch). These scripts are the repeatable, zero-content-loss way to do that — and
to verify it.

## The two stages (both required)

Run them as a pair. Stage 1 transforms with a built-in preservation check; stage 2 is
an **independent** re-check against the git-HEAD blob. Zero content loss is the whole
point — never `--apply` if either stage reports anything unaccounted for.

### 1. `restructure_mem.py` — transform (dry-run by default)

Turns a fat `MEMORY.md` into: identity (kept inline) + an `## Index` of one-line
pointers + per-entry `mem/<slug>.md` detail files. Every original section body is
written **verbatim** to a detail file; a built-in verifier asserts every non-blank
original line reappears (>= original count) across the new fileset or is an
intentionally-dropped TOC/index line.

```bash
# DRY RUN — writes nothing, prints the plan + verification result:
python3 tools/agent_memory/restructure_mem.py \
  .claude/agent-memory/<role>/MEMORY.md

# APPLY — only proceeds if verification passes:
python3 tools/agent_memory/restructure_mem.py \
  .claude/agent-memory/<role>/MEMORY.md --apply
```

### 2. `verify_mem.py` — independent post-write diff

After `--apply`, independently diffs the new on-disk fileset (new `MEMORY.md` +
`mem/*.md`) against the **git-HEAD** version of `MEMORY.md`. Every non-blank content
line in HEAD must appear in the new set; the only allowed drops are TOC links / table
rows / index headers.

```bash
python3 tools/agent_memory/verify_mem.py <role> [<role> ...]
# e.g.
python3 tools/agent_memory/verify_mem.py meesell-frontend-coordinator
# -> [PASS] meesell-frontend-coordinator: ... unaccounted=0
```

`verify_mem.py` resolves the repo root from `CLAUDE_PROJECT_DIR`, then
`git rev-parse --show-toplevel`, then a hardcoded fallback.

## Worktree-safe landing (CRITICAL)

Memory lives under `.claude/`. Per
[`docs/dev/MEMORY_INDEX_CONVENTION.md`](../../docs/dev/MEMORY_INDEX_CONVENTION.md)
("worktree-safe append rule") and
[`docs/AGENT_MEMORY_PERSISTENCE.md`](../../docs/AGENT_MEMORY_PERSISTENCE.md), changes
to `.claude/` files must be persisted via **Bash / git-plumbing** (or a sanctioned
master-tree git path), never the `Edit`/`Write` tools from inside an isolated
worktree. `--apply` writes plain files on disk; commit them through the sanctioned
path for your context.

## Detection (what flags a file)

The SessionStart guard `.claude/hooks/warn-agent-memory-size.sh` counts **inline-prose
lines** (non-blank lines that are not a heading `#`, a blockquote `>`, an index entry
`- [..](..)` — optionally `⭐`-prefixed — or within the first ~12 identity lines) and
warns when a file exceeds the prose threshold or a total-lines backstop. Defaults are
`prose>120` or `total>300`, overridable via `MESELL_MEM_PROSE_MAX` /
`MESELL_MEM_LINES_MAX`. The guard is **warn-only** — it never blocks a session.
