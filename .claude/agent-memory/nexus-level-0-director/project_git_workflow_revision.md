---
name: git-workflow-revision
description: 2026-06-21 founder-locked git workflow — feature/{slug}/{group} → integration → develop two-step gate; canonical doc GIT_WORKFLOW.md; submodules rejected (stay monorepo)
metadata:
  type: project
---

Founder-locked revision of the MeeSell git workflow (2026-06-21). Canonical source of truth is now `docs/GIT_WORKFLOW.md` (landed via PR #329; CLAUDE.md + MASTER_SESSION_DISPATCH.md + `_WORKTREE_PROTOCOL.md §9` reconciled via PR #330).

**The locked model:**
- Branches: `feature/{slug}/{group}`, group ∈ {backend, frontend, ai, data, infra}; each group is its own branch + own worktree + own localhost/build env.
- Flow: `feature/{slug}/{group}` --squash--> `feature/{slug}/integration` --merge-commit--> `develop` --> staging --> main (tagged).
- Step 1 (group→integration): Director/coordinator merges, squash. Step 2 (integration→develop): FOUNDER merges, merge-commit.
- Per new feature: 1 integration branch + 1 branch per discipline touched (1–5; max 6). Integration created first off develop, group branches off integration.
- No auto-delete (manual prune after merge). No age-based stale rule — a branch is a cleanup target only once its PR is merged. Held: feature/google-auth + gauth-live.

**Live GitHub protection (probed 2026-06-21, was wrong in old memory):** develop = **0 reviews required**, strict=false, enforce_admins=false, **15 required CI contexts**. main IS protected (13 contexts, conversation-resolution=true) — CONTRADICTS the 2026-06-12 "no protection on main" ruling; flagged to founder (risk: could deadlock a future staging→main PR). Auto-delete-on-merge=OFF (matches policy).

**Submodules REJECTED (2026-06-21).** Founder considered git submodules per-MFE / per-microservice, then dropped it. Reason: MeeSell is a solo-founder/single-product monorepo (6 MFEs + 6 libs frontend via Module Federation; 8 backend svc-* pods) — module independence already exists without repo-splitting; submodules add the commit-pointer dance + blow up the single-repo branching model + no atomic cross-cutting PRs, with no offsetting benefit until there are multiple teams/orgs. Stay MONOREPO. If stronger boundaries ever wanted: Nx module-boundary lint (frontend, no nx.json today) / import-linter (backend), NOT submodules.

**Why:** founder is consolidating working-style rules into enforceable repo settings; the old docs described a stale ticket-flow / section-parallel model that no longer matches how work actually happens.
**How to apply:** treat GIT_WORKFLOW.md as canonical; dispatch all feature work on `feature/{slug}/{group}` branches in per-group worktrees; never re-propose submodules without a multi-dev trigger. See [[project_meesell_ci_hardening_complete]] for the main-protection history.
