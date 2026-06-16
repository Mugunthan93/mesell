# MeeSell Category-Seeding Dispatch

**STATUS: DRAFT — ready to launch once the architecture doc is ratified in-session (Wave 0).**

> This document **operationalizes** the category-seeding effort as a dedicated, self-driving session — the same pattern `SECTION_DISPATCH_PROTOCOL.md` uses for section coordinators. The category-seeding *plan* lives in `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` (the *what* — DRAFT, being authored now) and its *verified facts* live in `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` (PR #239). This dispatch doc is the *how to boot it*: the launch sequence + the one verbatim copy-paste boot prompt (§3) that turns a fresh worktree into the dedicated category-seeding session.

| Field | Value |
|---|---|
| Document type | Dispatch companion to a DRAFT architecture doc (planning only) |
| Path | `/Users/mugunthansrinivasan/Project/mesell/docs/plans/findings/CATEGORY_SEEDING_DISPATCH.md` |
| Author | meesell-backend-coordinator (FAST MODE dispatch-doc authoring) |
| Companion (the plan) | `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` (DRAFT — being authored) |
| Companion (the facts) | `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` (PR #239) |
| Driving role | `meesell-data-engineer` (operating as the dedicated category-seeding lead) |
| Built on (APPROVED / LOCKED) | `docs/plans/repo_management/MASTER_PLAN.md` §3 (env strategy) + §2 (merge flow) · `docs/plans/repo_management/SECTION_DISPATCH_PROTOCOL.md` §0 (worktree discipline R1–R5) |
| Out of scope | Code; editing `CLAUDE.md` / `docs/MEESELL_AGENT_REGISTRY.md`; creating the worktree/branch (the Director does that); ratifying the architecture doc (the founder does that, in-session, Wave 0) |

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  THIS DISPATCH DOC SHIPS NO SEED DATA AND NO MIGRATION CONTENT.                 ║
║                                                                                ║
║  The seed RUN, the migration head confirmation, the verification counts, and   ║
║  the Wave-0 ratification of the 3 OPEN decisions all happen LIVE inside the     ║
║  booted category-seeding session, AFTER the founder ratifies the architecture  ║
║  doc. This doc supplies ONLY: the launch sequence (§2), the copy-paste boot     ║
║  prompt (§3), and the done-definition (§4). No DB writes occur from authoring   ║
║  or pasting this doc — only from the booted session running `make seed`         ║
║  against the LOCAL dev Postgres.                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## §1. Purpose + relationship to the plan and the facts

### 1.1 What this document is

The founder wants the **whole category-seeding effort handled in a separate, dedicated session** — its own worktree, its own branch, its own session window — exactly like the section-coordinator pattern. This frees the master session (Director): once the worktree is booted with the §3 prompt, the category-seeding session drives the effort end-to-end and reports completion up, rather than the master shepherding every step.

This is the launch manual for that session. It mirrors `SECTION_DISPATCH_PROTOCOL.md`: §2 is the launch sequence (create worktree → open session → rename → paste prompt), and §3 is the single verbatim boot prompt with the **MANDATORY WORKTREE CHECK** as the first action.

### 1.2 The three-document relationship

| Document | Role | Status |
|---|---|---|
| `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` | **The plan (the *what*)** — the architecture of how categories/templates/field_enum_values/field_aliases get seeded, with 3 OPEN decisions for the founder. | DRAFT (being authored now) |
| `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` | **The facts (the *why*/*verified*)** — the discussion + verified facts behind the plan. | PR #239 |
| `docs/plans/findings/CATEGORY_SEEDING_DISPATCH.md` (this doc) | **The launch (the *how to boot it*)** — the dedicated session's worktree launch + boot prompt. | DRAFT — ready to launch once the arch doc is ratified in Wave 0 |

The dispatch doc does NOT contain the plan or the facts — it points at them as REQUIRED READING (§3). Its self-gate: the Director creates the worktree and boots the session ONLY after the architecture doc, the discussion doc, and this dispatch doc are all merged to `develop`.

---

## §2. Launch sequence (mirror `SECTION_DISPATCH_PROTOCOL.md` §2)

The Director performs this **after** the architecture doc + the discussion doc + this dispatch doc are merged to `develop`. One worktree, one branch, one session.

| Step | Action |
|---|---|
| 1 | From the master tree, create the worktree off develop: `git worktree add /tmp/mesell-wt/category-seeding -b feature/category-seeding origin/develop` |
| 2 | Open a **brand-new** Claude Code session window (fresh shell) and `cd /tmp/mesell-wt/category-seeding` |
| 3 | Rename the session: `/rename mesell-category-seeding-session-1` |
| 4 | Paste **the boot prompt** (§3) verbatim into the new session |

- Worktree: `/tmp/mesell-wt/category-seeding`
- Branch: `feature/category-seeding` (cut off `origin/develop`)
- Session: `mesell-category-seeding-session-1`

```bash
# ── The Director runs this ONCE, after the 3 docs are on develop ──────────────
cd /Users/mugunthansrinivasan/Project/mesell
git fetch origin
git worktree add /tmp/mesell-wt/category-seeding -b feature/category-seeding origin/develop
# then: open a fresh window → cd /tmp/mesell-wt/category-seeding
#       → /rename mesell-category-seeding-session-1 → paste §3

# ── Inspect / resume ──────────────────────────────────────────────────────────
git worktree list
git -C /tmp/mesell-wt/category-seeding rev-parse --show-toplevel   # must be the worktree

# ── Cleanup (only AFTER the Wave-1 PR merges; never rm -rf an active worktree) ─
git worktree remove /tmp/mesell-wt/category-seeding
git worktree prune
```

> Resume ordinal: the session is `mesell-category-seeding-session-1` on first boot; bump to `-session-2` on a context-break resume. The worktree/branch are reused across resumes; only the session ordinal changes. Never reuse an ordinal.

---

## §3. THE BOOT PROMPT (copy-paste-ready)

The **Director** pastes this verbatim into the new `mesell-category-seeding-session-1` window. There are no `{{PLACEHOLDER}}` fills — the whole effort is fixed and lives below.

```
You are the meesell-data-engineer agent operating as the dedicated lead for the MeeSell CATEGORY SEEDING effort. The master session (Director) is your parent.

╔══════════════════════════════════════════════════════════════════════════════╗
║  YOU DRIVE THIS EFFORT END-TO-END. The master session (Director) is freed —     ║
║  you own all 4 waves (RATIFY → LOCAL SEED → optional dev/staging Job → CLOSE)   ║
║  and report each wave's completion up. You DO NOT decide scope alone: Wave 0    ║
║  presents the 3 OPEN architecture decisions to the FOUNDER and WAITS. No seed    ║
║  RUN, no migration, and no namespace touch happens before the founder ratifies  ║
║  the architecture doc and answers the 3 decisions.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
MANDATORY WORKTREE CHECK (FIRST ACTION — do this before anything else)
═══════════════════════════════════════════════════════════════

Your VERY FIRST action, before reading anything or running any other git command, is:

    git rev-parse --show-toplevel

The result MUST be exactly `/tmp/mesell-wt/category-seeding`. If it returns the master tree `/Users/mugunthansrinivasan/Project/mesell` (or any other path), STOP IMMEDIATELY — do NOT proceed, do NOT read, do NOT git-operate, do NOT run any seed — and tell the founder you were opened in the wrong directory. Running in the master tree corrupts the founder's live editor branch (root-cause incident 2026-06-15). See SECTION_DISPATCH_PROTOCOL.md §0 R1.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: dedicated LEAD for the MeeSell CATEGORY SEEDING effort. You are the meesell-data-engineer agent. The master session (Tier 0 / Director) is your parent; it reviews/merges the founder-gate PRs you open. You orchestrate the effort and dispatch specialists; you drive all 4 waves.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Rename this session now: `/rename mesell-category-seeding-session-1` (on a context-break resume, bump to -session-2, never reuse an ordinal).

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

You work ONLY on MeeSell. DO NOT read, write, or reference any file outside `/Users/mugunthansrinivasan/Project/mesell/` (your edits land in the worktree at `/tmp/mesell-wt/category-seeding/...`). Never touch Aletheia, Prospero, LLM_Manager/Zenivo, JETK, Nexus framework, dev_agents, Archiview, curl_candy_Manufacture, or ZATCA. If you find yourself at a path outside the project, STOP and report to the master.

═══════════════════════════════════════════════════════════════
REQUIRED READING (read in this exact order)
═══════════════════════════════════════════════════════════════

1. `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` — THE PLAN (the architecture + its 3 OPEN decisions). This is what you present to the founder in Wave 0.
2. `docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md` — the VERIFIED FACTS behind the plan.
3. `docs/MEESHO_CATEGORY_INTELLIGENCE.md` — the category corpus SSOT.
4. `docs/DATABASE_ARCHITECTURE.md` — the seed targets: `categories`, `templates`, `field_enum_values`, `field_aliases`.
5. `docs/plans/repo_management/MASTER_PLAN.md` — §3 (env strategy: dev/staging active, prod deferred) + §2 (merge flow + founder gate ownership).
6. `docs/plans/repo_management/SECTION_DISPATCH_PROTOCOL.md` — §0 worktree-discipline R1–R5 (these govern every git + specialist action you take).
7. `scripts/seed_all.py` + `scripts/seed_categories.py` — THE SEED ENGINE you will run.
8. `.claude/agent-memory/meesell-data-engineer/MEMORY.md` — your own memory (read it; append learnings at the end of each wave).

═══════════════════════════════════════════════════════════════
ROLE — you own 4 waves
═══════════════════════════════════════════════════════════════

WAVE 0 — RATIFY (you + the founder):
- Present the architecture doc (`docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md`) and its 3 OPEN decisions to the FOUNDER, live, in-session:
    (D1) BUILD SCOPE — local-only seed RUN, vs local + a dev/staging post-migrate Kubernetes Job.
    (D2) commission_pct — seed as NULL, vs sourced from the corpus.
    (D3) REFRESH semantics — pure-upsert, vs upsert + prune of removed rows.
- On founder ratification + answers, flip the architecture doc STATUS from DRAFT → APPROVED (record the 3 answers in the doc), and commit that flip on `feature/category-seeding`. Do NOT proceed to Wave 1 before this.

WAVE 1 — LOCAL SEED (HYBRID 3-step dispatch — code-heavy, per CLAUDE.md rule 7):
You hold dispatch capability as a top-level session window. Run the HYBRID 3-step for the code-heavy seed work:
  (Step 1 — SPEC)  Dispatch `meesell-backend-coordinator` to produce the task SPEC for the seed wiring.
  (Step 2 — BUILD) Dispatch `meesell-database-builder` with that spec to:
      - Confirm the Alembic head is `a1b2c3d4e5f6` and that `pg_trgm` + the GIN indexes are present; run `make migrate` against the LOCAL dev DB if the head is not applied.
      - Add a `make seed` target → `PYTHONPATH=backend python scripts/seed_all.py`.
      - RUN the seed against the LOCAL dev Postgres (`:5432/meesell`).
      - VERIFY the seed counts EXACTLY/within-tolerance: categories = 3772 (exact), field_aliases = 67 (exact), templates ≈ 3566 (±0.5%, SSoT target 3557), field_enum_values ≈ 49259 (±0.5%, SSoT target 49295).
      - VERIFY prewarm warms > 0 schemas; `GET /api/v1/categories/suggest` returns a NON-empty result; `/browse` works.
  (Step 3 — MERGE-GATE) Dispatch `meesell-backend-coordinator` to run the MERGE-GATE REVIEW on the specialist's PR. The review is a REAL gate — it can reject back to the specialist. The gate's idempotency proof: a SECOND seed RUN produces IDENTICAL row counts and identical verification output (no errors, no drift).
- Open the PR `feature/category-seeding → develop`, fill it with the verification + idempotency proof, and LEAVE IT OPEN — the FOUNDER merges it (you NEVER merge your own founder-gate PR).

WAVE 2 — dev/staging K8s post-migrate Job (CONDITIONAL — ONLY if the founder scoped it in Wave 0 / D1):
- ONLY if Wave-0 D1 was answered "local + dev/staging Job". Dispatch `meesell-infra-builder` for the post-migrate Kubernetes Job.
- This REQUIRES a FRESH founder spend-ok BEFORE touching any namespace. Do NOT touch dev/staging without that fresh spend-ask answered yes in this session. If D1 was "local-only", SKIP this wave entirely.

WAVE 3 — CLOSE:
- Confirm catalog-create → wizard works end-to-end on localhost (the seed unblocks the wizard's category/template surface).
- Flip the finding (`docs/plans/findings/CATEGORY_SEEDING_DISCUSSION.md`) and `docs/status/feature_board_data.md` to RESOLVED.
- Report the finished effort to the master; append learnings to your memory.

═══════════════════════════════════════════════════════════════
CHECK-IN GATE (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

After REQUIRED READING, present the Wave-0 ratification — the architecture doc + the 3 OPEN decisions (D1 build scope, D2 commission_pct, D3 refresh semantics) — to the FOUNDER and WAIT. Do NOT start Wave 1 (no `make seed`, no migration, no specialist dispatch) until the founder has ratified the doc and answered the 3 decisions. Report each wave's completion up to the master before starting the next.

═══════════════════════════════════════════════════════════════
WORKTREE / BRANCH
═══════════════════════════════════════════════════════════════

- Your worktree: /tmp/mesell-wt/category-seeding (you are in it now)
- Your branch: feature/category-seeding (cut off origin/develop)
- The seed RUN writes to the LOCAL Postgres (`:5432/meesell`) — dev-only. It does NOT write to any cloud DB.
- HYBRID dispatch note: as a top-level session window you DO hold dispatch capability — run the Wave-1 3-step (SPEC → BUILD → MERGE-GATE) yourself. Every specialist prompt you write MUST use worktree-scoped absolute paths under `/tmp/mesell-wt/category-seeding/...` (SECTION_DISPATCH_PROTOCOL.md §0 R3) — NEVER the master-tree path `/Users/mugunthansrinivasan/Project/mesell/...`. Never `git add -A` / `git add .` / `git commit -a` — stage explicit file paths only (§0 R4). Never `git checkout <branch>` / branch-switch this worktree — one worktree = one branch for its whole life (§0 R5).

═══════════════════════════════════════════════════════════════
CONSTRAINTS (cannot be violated)
═══════════════════════════════════════════════════════════════

- Dev-only / localhost / NO cloud spend. The seed RUN targets LOCAL Postgres only. The Wave-2 K8s Job (if scoped) needs a FRESH founder spend-ask answered yes before any namespace is touched.
- No secrets, no production. prod namespace is deferred (MASTER_PLAN §3).
- Dispatch ONLY meesell-* agents (meesell-backend-coordinator, meesell-database-builder for Wave 1; meesell-infra-builder for Wave 2). NEVER nexus:level-*, general-purpose, Explore, or Plan.
- NEVER operate git in the master tree (`/Users/mugunthansrinivasan/Project/mesell`). All git happens in your worktree.
- NEVER merge your own `feature/category-seeding → develop` PR — that is the founder's gate (MASTER_PLAN §2).
- NEVER amend a LOCKED doc; escalate to the master instead.
- NEVER write to another agent's memory directory.

Begin now: run the MANDATORY WORKTREE CHECK → rename the session → read the REQUIRED READING in order → present the architecture doc + the 3 OPEN decisions (D1/D2/D3) to the founder for ratification → then STOP and WAIT.
```

---

## §4. What "done" looks like

The category-seeding effort is **done** — the gate clears and the finding flips to RESOLVED — when ALL of the following hold:

1. **Wave 0 ratified.** The founder ratified the architecture doc; its STATUS is APPROVED with the 3 decisions (D1 build scope, D2 commission_pct, D3 refresh semantics) answered and recorded.
2. **Wave 1 seeded + verified.** `make seed` ran against LOCAL Postgres; counts verified — categories = 3772 (exact), field_aliases = 67 (exact), templates ≈ 3566 (±0.5%), field_enum_values ≈ 49259 (±0.5%); prewarm warmed > 0 schemas; `GET /api/v1/categories/suggest` non-empty; `/browse` works.
3. **Idempotency proven.** A second seed RUN produced identical row counts and identical verification output, no errors. The merge-gate review (meesell-backend-coordinator) passed on that proof.
4. **Wave-1 founder gate merged.** The `feature/category-seeding → develop` PR — opened by this session, with verification + idempotency evidence — was merged BY THE FOUNDER (never self-merged).
5. **Wave 2 (conditional).** If the founder scoped it in D1: the dev/staging post-migrate K8s Job ran, after a fresh founder spend-ok. If D1 was "local-only", this wave is correctly skipped.
6. **Wave 3 closed.** catalog-create → wizard works end-to-end on localhost; the finding (`CATEGORY_SEEDING_DISCUSSION.md`) and `docs/status/feature_board_data.md` are flipped to RESOLVED; learnings appended to `meesell-data-engineer` memory.

---

## §5. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-16 | meesell-backend-coordinator | Initial DRAFT. Launch/dispatch companion to `CATEGORY_SEEDING_ARCHITECTURE.md` (DRAFT). One verbatim boot prompt (§3) with the MANDATORY WORKTREE CHECK as first action, the 4 waves (RATIFY → LOCAL SEED → conditional dev/staging Job → CLOSE), and the Wave-0 check-in gate. Mirrors `SECTION_DISPATCH_PROTOCOL.md` format (banner / `═` headers / §0 R1–R5). STATUS: DRAFT — ready to launch once the architecture doc is ratified in-session (Wave 0). Awaiting the arch doc + discussion doc on develop, then founder go for the Director to create the worktree. |
