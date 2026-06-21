# Worktree Isolation for Code-Writing Specialists

> Adoption Step 2A. Reference: `docs/dev/CLAUDE_FEATURE_ADOPTION.md` §3.3 ("Agent worktree isolation").
> Landed 2026-06-21 by `meesell-infra-builder` (session `mesell-worktree-isolation-infra-session-1`).

## Goal

Code-writing specialists run in their **own isolated git worktree** so the MeeSell master tree
(`/Users/mugunthansrinivasan/Project/mesell`) can **never** be corrupted. This is *structural
prevention*, not a convention-by-discipline: the two master-tree-corruption incidents (2026-06-15
section-3, 2026-06-16 ui-ds-phase0) happened because a session or sub-agent ran
`git checkout` / `git commit` directly in the master checkout, flipping the founder's editor branch
and layering work onto the wrong place. Isolating every file-writing specialist into a worktree
makes that class of failure impossible by construction.

## Reliable mechanism = Director dispatch convention (source of truth)

The **authoritative** mechanism is the dispatch convention, not the agent frontmatter:

> When the master session (Director) dispatches a code-writing specialist, it passes
> `isolation: "worktree"` on the `Agent` call.

This means the specialist is run with a working directory set to an isolated worktree, and all of its
`Write`/`Edit`/`Bash git` operations land there — never in the master tree.

Frontmatter support for an `isolation` key may or may not be honored by the harness today. The
dispatch convention is therefore the **source of truth**; the per-spec frontmatter flag (see below)
is **belt-and-suspenders** — a declarative hint that travels with the spec and documents the intent
even if the harness ignores it.

## Scope: which agents are isolated

**IN — the 7 code-writing specialists** (they write files; each must run in its own worktree):

| Specialist | Model | Domain |
|---|---|---|
| `meesell-angular-component-builder` | sonnet | Angular page + UI components |
| `meesell-angular-service-builder` | sonnet | Angular services / RxJS / interceptors / guards |
| `meesell-angular-ui-styler` | sonnet | Tailwind / Material theming / layout |
| `meesell-services-builder` | opus | Backend service layer + Celery workers |
| `meesell-api-routes-builder` | sonnet | FastAPI route handlers + schemas |
| `meesell-auth-builder` | opus | OTP / JWT / auth + plan-guard + rate-limit middleware |
| `meesell-database-builder` | sonnet | SQLAlchemy models + Alembic migrations + seeders |

**EXCLUDED — coordinators and standalone leads** (spec / review only; no file writes):

- The 5 coordinators: `meesell-section-coordinator`, `meesell-backend-coordinator`,
  `meesell-frontend-coordinator`, `meesell-ai-coordinator`, `meesell-data-engineer`.
- The 2 standalone leads: `meesell-infra-builder`, `meesell-legal-writer`.

Coordinators produce task SPECs and run merge-gate reviews (HYBRID dispatch steps 1 and 3); they do
not author feature code, so they need no isolated worktree. Standalone leads execute directly against
their own owned surfaces under the existing master-tree guards.

## The 8GB concurrency cap (hard)

The dev box has **8GB RAM** and deadlocks on parallel `esbuild`/`ng build`. Therefore:

> **At most ONE build-specialist worktree may be active at a time.**

A second build-specialist worktree is opened **only after** the first one is merged (or its work is
torn down). This ties into the `meesell-env` RAM budget — do not run two isolated build worktrees
concurrently, and never rebuild all MFEs at once.

## Convention: how the worktree is created

Isolated worktrees follow the existing two-step merge gate unchanged:

- Created **off `origin/develop`**.
- Branch named **`feature/{slug}/{group}`** (e.g. `feature/auth-otp/backend`,
  `feature/price-calc/frontend`), so the existing flow holds:
  `feature/{slug}/{group}` --squash--> `feature/{slug}/integration` (coordinator merges)
  --merge-commit--> `develop` (founder merges).

Example:

```bash
git worktree add -b feature/<slug>/<group> /tmp/mesell-wt/<slug>-<group> origin/develop
cd /tmp/mesell-wt/<slug>-<group>   # all specialist work happens here
```

## Defense-in-depth + teardown

- `guard-master-tree-git.sh` (PreToolUse Bash guard) and the `.githooks/pre-commit` hook **remain in
  place** as belt-and-suspenders: even if a specialist is somehow launched without an isolated
  worktree, a `git commit` against the master checkout is still blocked
  (`MESELL_ALLOW_MASTER_GIT=1` is the deliberate-recovery override only).
- **Tear down at session end:** remove the worktree and prune:

  ```bash
  git worktree remove /tmp/mesell-wt/<slug>-<group>
  git worktree prune
  ```

  Stale worktrees waste disk and add to RAM/build confusion — prune them.

## Relationship to the dispatch protocol

This rule layers onto the HYBRID dispatch rule (CLAUDE.md MeeSell ecosystem rule 7): in
**code-heavy construction**, step 2 dispatches the named SPECIALIST — that dispatch now carries
`isolation: "worktree"`. Steps 1 and 3 (coordinator SPEC + merge-gate review) are unaffected
because coordinators are excluded from isolation.
