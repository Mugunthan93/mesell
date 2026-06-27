# MeeSell Git Workflow

> Canonical source of truth for branching, worktrees, and merging. Revised 2026-06-21 (founder-locked). Supersedes the legacy ticket-flow and section-parallel branch conventions.

## The flow

```
feature/{slug}/{group}  --squash-->  feature/{slug}/integration  --merge-commit-->  develop  -->  staging  -->  main
  (Director/coordinator merges)             (founder merges)                              (founder merges, tagged)
   group in {backend, frontend, ai, data, infra}
```

## How many branches per feature
1 integration branch + 1 branch per discipline the feature touches (1-5). Create the integration branch first (off develop), then each group branch off integration. Only create group branches for disciplines actually touched. Each group branch gets its own worktree + its own localhost/build environment.

## Worktrees
- **W1** One worktree = one branch = one PR = one isolated localhost/build environment, created off develop.
- **W2** Never `git checkout`/switch the tree you are in; create a new worktree instead. (Code-enforced in the master tree.)
- **W3** Materialize a branch only via `git worktree add`, never by checking it out.
- **W4** Worktrees live at `/private/tmp/mesell-wt/{name}`.
- **W5** First action of a session: confirm you are in your own worktree, not master - else STOP.
- **W6** Edit via the worktree's own path, never the master-tree path.
- **W7** `git worktree list` is the canonical state check.
- **W8** Keep a worktree while its PR is open; `git worktree remove` after merge (never `rm -rf`); `git worktree prune` stale refs after reboot.
- **W9** `.claude/agent-memory/` is symlinked in; `.claude/settings.json` is per-worktree (do not symlink).
- **W11** Symlink master `.terraform` into a worktree before `init` to save disk (never commit it).
- **W10** (deferred) Memory files grow unbounded via append; a compaction/rotation strategy is to be defined.

## Branches
- **B1** Long-lived branches: main, staging, develop.
- **B2** Naming: `feature/{slug}/{group}`, group in {backend, frontend, ai, data, infra}; each group is its own branch.
- **B3** Integration parent: `feature/{slug}/integration` (must be `/integration`, not bare `feature/{slug}` - a git ref cannot be both a file and a directory).
- **B5** Slug = kebab-case, <=30 chars, never renamed mid-feature.
- **B6** Branch from the right parent: group <- integration <- develop; rebase, do not merge, when pulling.
- **B7** No auto-delete. Branches are pruned manually after their PR merges.
- **B8** No age-based stale rule. A branch is a cleanup target only once its PR is merged - never because it is old (MFE/microservice lines legitimately run for weeks).
- **B9** (enforced) Creating a branch in the master tree is blocked.
- **B10** (enforced) Force-move/delete a branch from the master tree is blocked.
- **B11** Held branches (never delete): feature/google-auth + gauth-live.
- **B12** (enforced) `MESELL_ALLOW_MASTER_GIT=1` is the deliberate override for safe recovery ops only.
- **B13** Squash-merged branches appear "unmerged" to git; delete with `-D`, matched against the merged-PR list.
- **B14** (enforced) `feature/{slug}/integration` branches are GitHub-protected (CLI delete blocked; use the UI).

## Merging / PRs
- **M1** Two-step gate: group -> integration (step 1), integration -> develop (step 2).
- **M2** Step 1 (group -> integration): Director/coordinator merges, squash.
- **M3** Step 2 (integration -> develop): founder merges, merge-commit.
- **M4** CI gates 1-3 green for step 1; all 5 gates + nightly eval for step 2.
- **M5** Founder merges all develop PRs; Director/lead never does.
- **M6** develop -> staging -> main; tag the main merge; never force-push main.
- **M7** Rollback = `git revert -m 1 <merge-sha>`; fix on a fresh branch.
- **M8** PR templates must have zero placeholders left before merge.
- **M9** HYBRID dispatch merge-gate (coordinator SPEC -> specialist BUILD -> coordinator review).
- **M10** (enforced) Commits/merges/rebase/etc. in the master tree are blocked.
- **M11** (enforced) develop branch protection: 0 review(s) required, strict=false, enforce_admins=false, 15 required CI contexts (see M12). main: protected against force-push + deletion, NO required CI checks (reconciled 2026-06-21 to match the 2026-06-12 founder ruling; enforce_admins=false, 0 reviews required, required_conversation_resolution=true left as-found pending separate founder decision).
- **M12** develop required CI contexts (15): "CI Gate 1: unit", "CI Gate 2: smoke", "CI Gate 3: lint (10 contracts)", "CI Gate 4: integration", "CI Gate 5: golden_roundtrip", "Frontend: detect changed workspace units", "Frontend: shell", "Frontend: mfe-pricing", "Frontend: mfe-catalog", "Frontend: mfe-onboarding", "Frontend: mfe-dashboard", "Frontend: mfe-auth", "Frontend: mfe-export", "FE Gate: lint (5 contracts)", "Frontend: mfe-billing".
- **M13** `--admin` is how green PRs land on a single account; --admin-over-red needs a fresh founder grant.
- **M14** Board status flips may be a direct commit to the integration branch (no PR).
- **M15** (enforced) Integration branches: PR-only, 0 reviews required, no force-push/deletion.
- **M16** (enforced) Dev deploys fire from develop only, push-only.
- **M17** (enforced) CI triggers: push/PR to main & develop, nightly cron, manual dispatch.
- **M18** `gh pr merge --delete-branch` fails from a worktree (merge still works; verify via API).
- **M19** Persist-on-finish (Rule A, founder-ruled 2026-06-22). A task is not done until its durable outputs are **committed AND pushed to the remote** — never left as uncommitted master-tree dirt. Durable outputs = `.claude/agent-memory/**`, `docs/status/STATUS_*.md`, `docs/status/feature_board_*.md`, and any spec/doc the task produced. Worktree agents commit them to the feature branch so they ride the PR; fast-mode coordinators / standalone agents push via a dedicated `chore/<slug>-scribe` branch + PR or the git-plumbing route for write-protected `.claude/` files; isolated builders that cannot self-write memory REPORT learnings and the dispatching coordinator scribes AND pushes them. "Definition of Done" includes "artifacts are on the remote." Full text: `.claude/skills/meesell-task-completion-protocol/SKILL.md`.
- **M20** Rebuild-localhost-on-merge (Rule B, founder-ruled 2026-06-22). Every merge to develop MUST be followed by an affected-scope localhost rebuild so the running dev stack matches develop — a merge is not done until localhost matches develop. Pull develop into the baseline checkout, then: frontend/federation merge -> `python3 tools/meesell_env.py baseline refresh` (shell + changed remotes); backend merge -> restart the baseline backend (`uvicorn --reload` on :8000); docs-only merge -> no rebuild. Verify affected ports with `python3 tools/meesell_env.py status` and refresh the :7700 dev-manager. The merging agent (or the master session that merged) triggers it. Command flow: `docs/dev/ENV_MANAGER.md` + `.claude/skills/meesell-task-completion-protocol/SKILL.md`.

## Enforcement summary
Code-enforced today: master-tree git guard (Bash hook + pre-commit, with the MESELL_ALLOW_MASTER_GIT=1 override), meesell-*/nexus: agent allow-list, develop branch protection (server-side), ci.yml ref-guards (deploy only from develop). Everything else is documented convention.
