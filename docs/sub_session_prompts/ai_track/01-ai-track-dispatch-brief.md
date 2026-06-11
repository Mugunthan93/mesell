# AI Track — Session Dispatch Brief

**Session name:** `mesell-ai-track-session-1`
**Date authored:** 2026-06-11 (master session, founder-approved track launch)
**Status:** READY — track was 🔴 Not started, fully unblocked

---

## What this session is

You are a dedicated sub-session for the MeeSell **AI track**. Your job is to stand up V1 Features 2, 4, and 5 — the AI core of the product — by dispatching `meesell-ai-coordinator` (which dispatches its 3 specialists: `meesell-prompt-engineer`, `meesell-category-picker-builder`, `meesell-image-precheck-builder`).

**Only `meesell-*` agents may execute MeeSell work.** Never dispatch nexus/general-purpose/Explore agents.

## Required reading (in order, before any dispatch)

1. `CLAUDE.md` (project root) — ecosystem rules
2. `docs/V1_FEATURE_SPEC.md` — Features 2 (Smart Category Picker), 4 (AI Autofill), 5 (Image Pre-check)
3. `docs/plans/repo_management/MASTER_PLAN.md` — Model C git conventions (v1.1, pilot-hardened)
4. `docs/status/STATUS_AI.md` + `docs/status/feature_board_ai.md` — current (empty) track state
5. `.claude/agent-memory/meesell-ai-coordinator/MEMORY.md` — coordinator's own memory
6. `docs/MEESHO_CATEGORY_INTELLIGENCE.md` — the category SSoT (3,772 leaves parsed by data track)
7. `backend/app/services/ai_engine.py` + `backend/app/data/` — the as-built call sites and data files

## Mission (sequenced)

1. **Plan first**: dispatch `meesell-ai-coordinator` to author the AI track execution plan (canonical pattern v2.1 — fence-aware section audit: `awk '/^(```|~~~)/{f=!f; next} !f && /^## /' <file>`). Plans for Features 2/4/5 already exist under `docs/plans/features/` (category-suggest, ai-autofill, image-precheck — all LOCKED). The coordinator's plan is the EXECUTION sequencing across the three, not a re-plan.
2. **Execute Feature 2 first** (category picker — highest user value, data foundation ready), then 4, then 5, unless the coordinator's plan justifies a different order.
3. Deliverables per the coordinator's spec: prompt registry index, JSON-mode contracts + parsers, golden test fixtures, eval suite, cost meter (Gemini spend tracking with budget brake).

## Git conventions (Model C — NON-NEGOTIABLE)

- ALL branch work in worktrees under `/tmp/mesell-wt/` — NEVER switch the master tree's branch (it stays on `develop`).
- Integration branch: `feature/{name}/integration` (F1 ruling). Group branches: `feature/{name}/ai`.
- Group → integration: lead-gated SQUASH merge (§2.1). Record the gate decision as a **PR comment** (single-account self-approval is blocked), merge with `--admin`.
- Integration → develop: **FOUNDER-ONLY** (§2.2). Open the PR titled `[FOUNDER GATE — DO NOT MERGE]` and leave it open. NOTE: the founder merges via CLI/delegation — the UI merge button is blocked by the review-count rule.
- `gh pr merge --delete-branch` from a worktree fails local cleanup ("develop already used by worktree") — the merge still lands; delete the remote ref via `gh api -X DELETE repos/Mugunthan93/mesell/git/refs/heads/<branch>`, then `git worktree remove`.
- Status/board flips: F2 status-only direct commits to develop are allowed for `docs/status/` files.
- Explicit-path staging only — never `git add -A`.

## Hard constraints

- **Cost**: Gemini 2.5 Flash only. Live API evals need `GEMINI_API_KEY` in `backend/.env` (founder provides; NEVER committed, NEVER printed). If no key available, run offline-fixture evals and flag the live-eval gap.
- **Memory**: each agent reads its own memory at start, appends at end. NO agent writes another agent's memory. Cross-agent needs → STATUS file blocker mechanism.
- **Boundaries**: AI track owns `backend/app/services/ai_engine.py` evolution, prompt assets, eval fixtures, and its own status surfaces. Backend service-layer changes beyond AI call sites → inter-lead request to `meesell-backend-coordinator` on the board, not direct edits.
- **Parallel tracks live**: frontend MF extractions (SP01+) and infra CI work are running in other sessions. Do not touch `frontend/`, `.github/workflows/`, `k8s/`, or terraform.
- Escalate genuine blockers to the founder in-session; record them on `STATUS_AI.md`.

## Session end

Update `STATUS_AI.md` (UPDATE block) + `feature_board_ai.md` + the coordinator's memory. Report to the founder: PRs opened/merged, founder-gate PRs awaiting, eval scorecards, Gemini spend.
