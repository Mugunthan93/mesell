# Session Dispatch: Repo Management
**Session name:** `mesell-repo-management-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — start this session first
**Must complete before:** S2 (Microservices), S3 (Module Federation), S4 (Infra-MS), S5 (Infra-MF)

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-repo-management-session-1
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
Execute the Repo Management Master Plan end-to-end.
This session MUST complete before any feature session starts — it creates
the develop/staging branches and lead agent specs that all other sessions depend on.

## Step 0 — Read the master plan FIRST
Read `docs/plans/repo_management/MASTER_PLAN.md` completely before doing anything else.
That document is your ground truth. Follow it. Every decision in this session
must trace back to a section in that plan.

Also read:
- `docs/plans/module_federation/MASTER_PLAN.md` — understand the 6-remote structure
  that defines what a "feature" looks like on the frontend side
- `docs/plans/microservices_migration/MASTER_PLAN.md` — understand the 8-service
  structure that defines what a "feature" looks like on the backend side
- `.claude/agents/meesell-backend-coordinator.md` — current spec, to be evolved into lead
- `.claude/agents/meesell-frontend-coordinator.md`
- `.claude/agents/meesell-ai-coordinator.md`
- `.claude/agents/meesell-data-engineer.md`
- `.claude/agents/meesell-infra-builder.md`

## Step 1 — Surface open decisions to the founder
Before executing anything, ask the founder to decide the following 3 questions.
Do NOT proceed to Step 2 until you have answers.

Decision 1 — Merge gate ownership
  When a feature/{name}/{group} branch is ready to merge into feature/{name},
  who reviews and approves?
  - Option A: Lead agent reviews + merges (group → feature); Founder reviews (feature → develop) only
  - Option B: Founder reviews every merge at every level
  - Recommendation: Option A — leads are being created specifically to own this gate

Decision 2 — feature_board.md update trigger
  When does a specialist update their lead's feature_board.md?
  - Option A: On PR open only
  - Option B: On PR merge only
  - Option C: Both — IN REVIEW on PR open, MERGED on PR merge
  - Recommendation: Option C — board always reflects current real state

Decision 3 — Lead spec rewrite scope
  Do the new lead specs REPLACE or EXTEND the coordinator specs?
  - Option A: Replace — coordinator concept is retired, files are rewritten top-to-bottom
  - Option B: Extend — keep coordinator content, append lead responsibilities
  - Recommendation: Option A — clean break, no ambiguity about which section governs

Record all 3 answers at the top of `docs/plans/repo_management/MASTER_PLAN.md`
under a new `## Decisions` section before continuing.

## Step 2 — Ratify the plan
Change the STATUS header in `docs/plans/repo_management/MASTER_PLAN.md`
from DRAFT → APPROVED.

## Step 3 — Create long-lived branches
Following the branch model in §1 of the master plan:
- Create `develop` branch from `main`
- Create `staging` branch from `main`
- Configure branch protection on `main`: require CI pass + founder review before merge
- Configure branch protection on `staging`: require CI pass before merge
- Set `develop` as the default PR target in GitHub repo settings

## Step 4 — PR templates
Dispatch `meesell-backend-coordinator` to author all 5 PR templates
following the template specs in §5 of the master plan:
- `.github/PULL_REQUEST_TEMPLATE/backend.md`
- `.github/PULL_REQUEST_TEMPLATE/frontend.md`
- `.github/PULL_REQUEST_TEMPLATE/ai.md`
- `.github/PULL_REQUEST_TEMPLATE/data.md`
- `.github/PULL_REQUEST_TEMPLATE/infra.md`

Each template must include:
- Session name + branch name fields (so every PR is traceable to its session)
- Group-specific evidence section (migrations for backend, terraform plan for infra, etc.)
- Acceptance gate checklist from the master plan §2 merge flow
- Reviewer reminder: "Reviewer = Founder for feature→develop; Lead = reviewer for group→feature"

## Step 5 — Lead agent spec rewrites
Dispatch each coordinator to rewrite their own `.claude/agents/` spec file
following §7 of the master plan (Lead Responsibilities).

Each rewritten spec MUST add these new sections on top of existing content:
- **Owns**: `docs/status/feature_board_{domain}.md` — lead is the sole writer
- **Merge gate**: Lead reviews and approves group → feature/{name} PRs for their domain
- **Update protocol**: How specialists notify the lead when work is complete
- **Cross-lead coordination**: How to request work from another lead domain
  (write a memo to their MEMORY.md, do not modify their feature_board directly)
- **Session naming**: Enforce `mesell-{feature}-{group}-session-{N}` in all dispatches

Agents to rewrite (one dispatch each, can run in parallel):
- `meesell-backend-coordinator.md`
- `meesell-frontend-coordinator.md`
- `meesell-ai-coordinator.md`
- `meesell-data-engineer.md`
- `meesell-infra-builder.md`

DO NOT rewrite any specialist agent spec — only coordinators become leads.

## Step 6 — Initialise feature_board.md files
Create one feature board file per lead following the template in §6 of the master plan.
Initial state: header populated, features table empty (no features in flight yet).

Files to create:
- `docs/status/feature_board_backend.md`
- `docs/status/feature_board_frontend.md`
- `docs/status/feature_board_ai.md`
- `docs/status/feature_board_data.md`
- `docs/status/feature_board_infra.md`

## Step 7 — Commit everything
Create branch `repo-management/foundation` from `develop`.
Stage and commit all changes from Steps 2–6:

```
feat(repo): establish Model C branch model, lead agents, PR templates, feature boards

- MASTER_PLAN.md ratified (DRAFT → APPROVED)
- develop + staging branches created with protection rules
- 5 PR templates added to .github/PULL_REQUEST_TEMPLATE/
- 5 coordinator specs evolved into lead specs
- 5 feature_board.md files initialised (empty)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Open a PR from `repo-management/foundation` → `develop` using the backend PR template
as a reference format.

## Acceptance gate — this session is complete when ALL are true
- [ ] `docs/plans/repo_management/MASTER_PLAN.md` status = APPROVED, 3 decisions recorded
- [ ] `develop` branch exists in GitHub with protection rules
- [ ] `staging` branch exists in GitHub with protection rules
- [ ] `.github/PULL_REQUEST_TEMPLATE/` contains all 5 group templates
- [ ] All 5 coordinator specs rewritten as lead specs (session naming + merge gate + board ownership)
- [ ] All 5 `docs/status/feature_board_*.md` files exist
- [ ] All changes committed on `repo-management/foundation`

## Hard constraints
- Do NOT touch any file in `backend/`, `frontend/`, `k8s/`, `infra/`
- Do NOT create any `feature/*` branch — that is each feature session's job
- Do NOT rewrite any specialist spec (only the 5 coordinator files change)
- Do NOT merge `repo-management/foundation` → `develop` in this session —
  leave the PR open for founder review
```
