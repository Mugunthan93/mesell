# MeeSell Repo Management — Master Plan

**STATUS: APPROVED 2026-06-10 — ratified by founder. Now executable.**

| Field | Value |
|---|---|
| Document type | Master plan (planning only — zero code changes) |
| Scope | Workflow + governance for parallel agent work across all five MeeSell groups (`backend`, `frontend`, `ai`, `data`, `infra`) |
| Path | `/Users/mugunthansrinivasan/Project/mesell/docs/plans/repo_management/MASTER_PLAN.md` |
| Related plans | `docs/plans/module_federation/MASTER_PLAN.md` (frontend) · `docs/plans/microservices_migration/` (backend, when authored) · `docs/plans/infra/` · `docs/plans/lead_agent_specs/` |
| Source of truth | `docs/status/STATUS_MASTER.md`, the five `docs/status/STATUS_*.md` files, `CLAUDE.md`, `.github/workflows/ci.yml` |
| Author | meesell-backend-coordinator |
| Out of scope | Code changes; PR template files themselves; lead-agent CLAUDE.md rewrites; running git commands (all those are sub-plans listed in §9) |

---

## Decisions (locked 2026-06-10 — founder approval)

| # | Question | Locked answer |
|---|---|---|
| D1 | Merge gate ownership for `feature/{name}/{group}` → `feature/{name}` | Lead agent for the group reviews and merges. Founder reviews and merges only the subsequent `feature/{name}` → `develop` PR. |
| D2 | `feature_board.md` update trigger | Specialist marks `IN REVIEW` on PR open. Lead marks `MERGED` on PR merge. Board reflects current real state at every transition. |
| D3 | Lead spec rewrite scope | Replace, not extend. The 5 coordinator/standalone specs at `.claude/agents/meesell-{backend,frontend,ai}-coordinator.md`, `.claude/agents/meesell-data-engineer.md`, `.claude/agents/meesell-infra-builder.md` are rewritten top-to-bottom as lead specs. The "coordinator" term is retired in those files; the agent slugs stay unchanged (no rename). |

These three answers are inputs to §2 (Merge Flow), §6 (feature_board.md), §7 (Lead Responsibilities), and §9.1 (Lead spec rewrites) below.

---

## 0. Why this plan exists

MeeSell is moving from a **single-agent, linear** workflow (one coordinator, one feature at a time) to a **parallel-agent, feature-centric** model. Multiple agents now work on multiple features simultaneously. That introduces five concrete operational risks the current setup does not guard against:

1. **File conflict risk.** Two agents modifying the same files at the same time produces merge hell. The current "one branch, one coordinator" pattern does not scale.
2. **Status fragmentation.** Eighteen separate `MEMORY.md` files plus seven `STATUS_*.md` files mean nobody — not even the founder — can answer "how is Feature X going?" in under five minutes.
3. **Session chaos.** No naming convention for agent sessions means resuming work after a context window break requires archaeology.
4. **Missing merge governance.** There is no agreed flow from feature branches to `main`. Today work goes straight from a coordinator's working branch to `main` via a single human review.
5. **No PR discipline per domain.** Backend PRs look different from infra PRs — same single template would either over-specify infra concerns for backend authors or under-specify backend concerns for infra reviewers.

The **architecture decisions** that enable parallel work — backend microservices extraction (per `BACKEND_ARCHITECTURE.md §16.H` 8-step order) and frontend module federation (per `docs/plans/module_federation/MASTER_PLAN.md` 6 remotes) — were already made in earlier sessions. This plan operationalises the **workflow and governance** that makes those parallel surfaces *safe and auditable*.

Decisions already locked in this session (do NOT re-litigate):

- **Model C branching** (described in §1 below)
- **Five agent groups**: `backend`, `frontend`, `ai`, `data`, `infra`
- **Lead agent layer**: the existing 5 coordinators evolve into leads — they gate merges from `feature/{name}/{group}` to `feature/{name}` and own the per-domain `feature_board.md`
- **V1 environments**: `dev` + `staging` only; `prod` deferred to V1.5

---

## 1. Branch Structure

### 1.1 Long-lived branches

| Branch | Purpose | Created when | Protection | Who can merge into it |
|---|---|---|---|---|
| `main` | Production-deployable. Tagged for release. | Already exists. | Protected — admin-only direct push; merge ONLY via PR from `staging`; require 1 approving review (founder); require all CI gates green. | Founder (PR merge button only). |
| `staging` | Pre-prod integration. Mirrors what will land on `main` at the next release. | **Sub-plan §9.4** (one-shot, before any feature work starts). Branched from `main` at the moment of creation. | Protected — merge ONLY via PR from `develop`; require all CI gates green + nightly suite green; founder approval. | Founder (PR merge button only). |
| `develop` | Integration of all completed features. Continuously deployable to `dev` namespace. | **Sub-plan §9.4** (one-shot, before any feature work starts). Branched from `main` at the moment of creation. | Protected — merge ONLY via PR from `feature/{name}`; require all CI gates green; lead-agent approval (NOT specialist approval). | Lead agents (any of the 5 leads can approve a feature PR; the lead whose group is the largest contributor to the feature signs off). |

Order of creation (one-shot):

```
main (exists) ──┬──► branch ──► staging
                └──► branch ──► develop
```

`staging` and `develop` are created **on the same day** before any feature branches. Until they exist, the founder must not approve any feature PR.

### 1.2 Feature branches

**Convention:** `feature/{feature-slug}/{group}`

Where:

- `feature-slug` is **kebab-case**, **short** (≤ 30 chars), derived from the V1 feature name or epic ticket. The slug is the **stable identifier** for the feature across all groups, all status docs, and all session names. Never rename a slug mid-feature.
- `group` ∈ `{backend, frontend, ai, data, infra}`. No other values permitted.

| Branch | Created when | Created by | Merges into | Deleted when |
|---|---|---|---|---|
| `feature/{name}` | First group is about to start the feature. | Founder (or the lead whose group starts first). | `develop` (via PR — see §2) | After PR to `develop` merges. |
| `feature/{name}/{group}` | Group's lead dispatches a specialist on this feature. | Lead agent for that group. | `feature/{name}` (via PR — see §2) | After PR to `feature/{name}` merges. |

`feature/{name}` is the **integration branch** for that feature across all groups. It is branched **from `develop`** when the feature starts and is the parent of every `feature/{name}/{group}` branch.

`feature/{name}/{group}` branches are short-lived (target: hours to days, not weeks). If a group's work on a feature exceeds 5 calendar days without a merge, the lead must escalate to the founder.

### 1.3 Examples grounded in MeeSell V1 features

Drawn from `docs/V1_FEATURE_SPEC.md` and the current locked features:

```
main
├── staging
└── develop
    ├── feature/auth-otp                ← parent integration branch
    │   ├── feature/auth-otp/backend    ← iam module + MSG91 wiring + Lua rotation
    │   ├── feature/auth-otp/frontend   ← Login + OTP-Verify pages, AuthService
    │   ├── feature/auth-otp/infra      ← Secret Manager rotation, refresh-token-pepper
    │   └── (no ai / data branches for this feature)
    │
    ├── feature/smart-picker
    │   ├── feature/smart-picker/backend   ← category module /suggest endpoint
    │   ├── feature/smart-picker/frontend  ← Smart Picker page + service
    │   ├── feature/smart-picker/ai        ← prompt registry smart_picker.v1, golden set
    │   └── feature/smart-picker/data      ← (rarely — only if category seed needs a tweak)
    │
    ├── feature/catalog-form
    │   ├── feature/catalog-form/backend
    │   ├── feature/catalog-form/frontend
    │   ├── feature/catalog-form/ai        ← Auto-fill prompt + enum guardrail
    │   └── feature/catalog-form/data
    │
    ├── feature/price-calculator
    │   ├── feature/price-calculator/backend  ← pricing module endpoint
    │   └── feature/price-calculator/frontend ← P&L breakdown component
    │
    ├── feature/xlsx-export
    │   ├── feature/xlsx-export/backend
    │   ├── feature/xlsx-export/frontend
    │   └── feature/xlsx-export/data         ← ComplianceStrategy variants
    │
    └── feature/image-precheck
        ├── feature/image-precheck/backend
        ├── feature/image-precheck/frontend
        ├── feature/image-precheck/ai
        └── feature/image-precheck/infra      ← GCS bucket policy + signed URL TTL
```

**Slug discipline:**

- ✅ `feature/auth-otp/backend`
- ✅ `feature/smart-picker/ai`
- ✅ `feature/xlsx-export/data`
- ❌ `feature/Authentication/backend` (PascalCase)
- ❌ `feature/auth_otp/backend` (snake_case)
- ❌ `feature/auth-otp-and-jwt/backend` (compound — split into two features instead)
- ❌ `feature/auth-otp/be` (abbreviated group)

A group only gets a branch **if and when** that group has work to do for that feature. Most features will not need branches in all five groups.

### 1.4 Branch lifecycle invariants

1. **Branch from the right parent.** `feature/{name}/{group}` is branched from `feature/{name}` — NEVER from `develop` or `main`. `feature/{name}` is branched from `develop` — NEVER from `main` or `staging`.
2. **Rebase, don't merge, on integration pulls.** When `feature/{name}` advances (because a sibling group merged), the in-flight `feature/{name}/{group}` branches **rebase** onto the new tip. This keeps history linear and PR diffs readable.
3. **Delete after merge.** The branch is deleted (locally and on GitHub) within 24 hours of its PR merging. GitHub's "auto-delete" setting should be enabled for feature branches.
4. **No long-lived feature branches.** If a `feature/{name}` branch exists for more than 14 calendar days without merging to `develop`, the founder is notified via the `STATUS_MASTER.md` blockers section.

---

## 2. Merge Flow (Governance)

```
                   ┌─────────────────────────────────────────────────┐
                   │  feature/{name}/{group}                          │  ← specialists push
                   │   (specialist branches — short-lived)            │     here
                   └────────────────┬────────────────────────────────┘
                                    │  STEP 1: group PR + CI + lead approval
                                    ▼
                   ┌─────────────────────────────────────────────────┐
                   │  feature/{name}                                  │  ← cross-group
                   │   (feature integration branch)                   │     integration here
                   └────────────────┬────────────────────────────────┘
                                    │  STEP 2: feature PR + integration tests + lead consensus
                                    ▼
                   ┌─────────────────────────────────────────────────┐
                   │  develop                                         │  ← all features
                   │   (continuously deployed to dev namespace)       │     integrated here
                   └────────────────┬────────────────────────────────┘
                                    │  STEP 3: sprint PR + full regression + founder approval
                                    ▼
                   ┌─────────────────────────────────────────────────┐
                   │  staging                                         │  ← release candidate
                   │   (deployed to staging namespace)                │
                   └────────────────┬────────────────────────────────┘
                                    │  STEP 4: release PR + smoke verified + founder approval
                                    ▼
                   ┌─────────────────────────────────────────────────┐
                   │  main                                            │  ← production-ready,
                   │   (tagged; production deploys when V1.5 lights)  │     tagged for release
                   └─────────────────────────────────────────────────┘
```

### 2.1 STEP 1 — `feature/{name}/{group}` → `feature/{name}`

| Field | Value |
|---|---|
| Preconditions | (a) Specialist's slice is complete per the dispatched acceptance criteria. (b) Group's PR template (§5) filled out. (c) `feature_board.md` for that group's lead updated to `IN REVIEW`. (d) Branch rebased on current `feature/{name}` tip — no merge commits. |
| Who opens the PR | The specialist who did the work. |
| Who merges | **Lead agent for that group.** (Backend lead reviews backend group's PR, etc.) |
| Merge type | PR with squash-merge. One commit per group's contribution to a feature. |
| CI gate requirement | Gates 1+2+3 (unit, smoke, lint) MUST pass. Gates 4+5 (integration, golden_roundtrip) are advisory at this step — they SHOULD pass but a lead may merge with a documented blocker if the blocker is owned by another group (e.g., backend cannot run integration without infra's DB migration landing first). |
| Rollback | If the merge breaks `feature/{name}` for sibling groups, the lead reverts via `git revert -m 1 <merge-sha>` on `feature/{name}`. The specialist re-opens a new PR with the fix; the reverted PR is closed not reopened. |

### 2.2 STEP 2 — `feature/{name}` → `develop`

| Field | Value |
|---|---|
| Preconditions | (a) ALL groups participating in the feature have merged their `feature/{name}/{group}` PRs. (b) Integration tests authored by the backend coordinator (`backend/tests/test_*_integration.py`) and the frontend coordinator (Playwright/Cypress E2E if applicable) pass on `feature/{name}`. (c) All 5 CI gates green. (d) Every participating lead has marked the feature `IN REVIEW` on their `feature_board.md`. (e) Acceptance criteria from `V1_FEATURE_SPEC.md` confirmed met. |
| Who opens the PR | The lead whose group has the largest contribution (typically `backend` for backend-heavy features, `frontend` for UI-heavy ones). |
| Who merges | **Founder.** (V1 rule — V1.5 may delegate to a designated lead for low-risk features.) |
| Merge type | PR with merge-commit (NOT squash) — preserves the per-group commit history for archaeology. |
| CI gate requirement | All 5 CI gates green. AI eval (nightly) for the relevant workload green on its last run. |
| Rollback | If merging to `develop` breaks a sibling feature already in `develop`, the founder reverts via `git revert -m 1 <merge-sha>` on `develop`. The participating leads coordinate a fix on a new `feature/{name}-fix` branch, NOT on the original branch. |

### 2.3 STEP 3 — `develop` → `staging`

| Field | Value |
|---|---|
| Preconditions | (a) Sprint complete per the founder's sprint definition. (b) Full regression suite green on `develop` (unit + smoke + lint + integration + golden_roundtrip + all 3 AI eval sets). (c) `dev` namespace deployment of `develop` HEAD has been live for at least 24 hours without P0/P1 alerts. (d) Each lead has signed off in `STATUS_MASTER.md` "sprint-ready" subsection. |
| Who opens the PR | Master session (founder + master Claude window). |
| Who merges | **Founder.** |
| Merge type | PR with merge-commit. The PR title encodes the sprint number (e.g., "Sprint 04 — auth + smart-picker + price-calc"). |
| CI gate requirement | All 5 gates green + nightly suite green within the last 24 hours. |
| Rollback | If a regression surfaces in `staging` post-deploy, the founder reverts the merge commit on `staging` and the master session opens a `hotfix/{slug}` branch from `staging`-pre-revert to investigate. Do NOT revert on `develop` — debug there first. |

### 2.4 STEP 4 — `staging` → `main`

| Field | Value |
|---|---|
| Preconditions | (a) `staging` namespace soak: at least 48 hours live without P0/P1 alerts and at least one round of human smoke testing by the founder. (b) Release notes drafted (sub-plan; see V1.5 backlog). (c) Database migration upgrade-and-downgrade rehearsed against a `staging`-clone DB. (d) All 5 CI gates green on `staging` tip. |
| Who opens the PR | Master session. |
| Who merges | **Founder.** |
| Merge type | PR with merge-commit. The merge commit is annotated-tagged with the release version (`v1.0.0`, `v1.0.1`, etc.) immediately after merge. |
| CI gate requirement | All 5 gates green. Tag-triggered build job pushes the release artifacts to Artifact Registry. |
| Rollback | Tag-based rollback: if `main` after release exhibits a P0, the founder retags the previous release as `latest` and the deployment pipeline rolls back. The bad merge is reverted on `main` via `git revert` and the fix flows back through `develop` → `staging` → `main`. NEVER force-push `main`. |

### 2.5 Decision tree — partial group completion

The most common scenario: **"Backend group is done but frontend group is still in progress."** What flows?

```
Q1: Has backend's PR (feature/{name}/backend → feature/{name}) been opened?
    ├── No  → Backend lead opens it as soon as the slice is complete. Don't block on frontend.
    └── Yes
        │
        Q2: Have CI gates 1+2+3 passed on backend's PR?
            ├── No  → Specialist fixes failing gates. Stays in feature/{name}/backend.
            └── Yes
                │
                Q3: Does the backend slice break the frontend's in-flight feature/{name}/frontend
                    when frontend rebases onto it?
                    ├── Yes → Two paths:
                    │         (a) Backend lead merges anyway; frontend rebases and fixes its
                    │             slice on feature/{name}/frontend. PREFERRED when the break is
                    │             a contract change frontend was already going to adapt to.
                    │         (b) Backend lead holds the PR open; backend and frontend specialists
                    │             coordinate via the coordinator memos until both are ready.
                    │             USE ONLY for contract changes that surprised the frontend
                    │             (signals a coordination failure — escalate to founder).
                    └── No  → Backend lead merges to feature/{name}.
                              Frontend rebases on the new tip and continues.

Q4: feature/{name} → develop is BLOCKED until ALL participating groups have merged.
    The feature is NOT "done" until every group's slice is in feature/{name}.
    The feature_board.md for each participating lead shows IN REVIEW for the missing
    groups, and the founder does not approve the feature PR until they are all MERGED.
```

**The key invariant:** `feature/{name}/{group}` PRs land independently and quickly. `feature/{name}` → `develop` is the **single coordination point** where all groups must converge. This minimises blocking while preserving the integration-before-`develop` guarantee.

---

## 3. Environment Strategy

V1 scope is **dev + staging only**. `prod` is deferred to V1.5 — when it lights, this plan is amended in place (`§3.4` slot reserved).

### 3.1 What runs where

| Branch | Deploys to | Cadence | Namespace | Purpose |
|---|---|---|---|---|
| `develop` | `dev` K3s namespace | Continuously (every merge to `develop` triggers deploy) | `dev` | Active development testing, lead-driven smoke tests, AI eval re-runs |
| `staging` | `staging` K3s namespace | On every merge to `staging` (sprint cadence) | `staging` | Pre-prod integration, founder smoke verification, migration rehearsal |
| `main` | (V1.5) `prod` namespace | (V1.5) On tagged release only | (V1.5) `prod` | Production. Deferred. |

`feature/{name}` and `feature/{name}/{group}` branches do **NOT** auto-deploy anywhere. They are tested in the developer's local Docker Compose dev stack or via the `dev` namespace if the lead manually triggers a "preview" deploy (V1.5 may automate per-feature preview environments — out of scope here).

### 3.2 Feature flag / partial-feature gating

Because `feature/{name}` → `develop` is the single integration point, **a half-built feature can land on `develop` only if it is feature-flagged**. The flag protocol:

- **Backend.** Feature flags are environment variables on the FastAPI app (e.g., `FEATURE_SMART_PICKER_ENABLED=false`). The relevant route handler checks the flag and returns `404` if disabled. Owned by `meesell-services-builder` per feature.
- **Frontend.** Feature flags are runtime booleans on the `core/services/feature-flags.service.ts` (V1.5 may add a remote config feed; V1 uses build-time env). Routes are guarded by a `featureFlagGuard`. Owned by `meesell-angular-service-builder` per feature.
- **AI.** Workload flags live in the prompt registry (`ai_ops/prompt_registry.py`) as the active version pin. A disabled workload returns a graceful fallback per `BACKEND_ARCHITECTURE.md §6A.F`.
- **Data.** Schema and seed gating uses Alembic migration ordering (a migration may be present but no router consumes its tables yet) and is gated implicitly.
- **Infra.** Resource creation gating uses Terraform variables (`var.enable_feature_x = false`).

A feature is **dev-enabled, staging-disabled** when its flag is `true` in `dev` env vars and `false` in `staging`. This lets `develop` carry forward partial work without exposing it on `staging`.

The feature flag is removed when the feature ships to `main`. Carrying a flag past one release is a debt item.

### 3.3 Database migration strategy

| Step | Environment | Who runs `alembic upgrade head` | When |
|---|---|---|---|
| 1 | Local dev | The backend specialist who authored the migration | When developing the feature locally. |
| 2 | `dev` namespace | CI/CD pipeline (post-merge to `develop`) automatically. | On every deploy to `dev`. Migration is idempotent — if HEAD matches, no-op. |
| 3 | `staging` namespace | CI/CD pipeline (post-merge to `staging`) automatically. | On every deploy to `staging`. |
| 4 | `staging`-clone (rehearsal) | Master session, manually, BEFORE the `staging → main` PR is opened | At least once per release. Validates upgrade-and-downgrade against a snapshot of staging data. |
| 5 | (V1.5) `prod` namespace | (V1.5) CI/CD pipeline on tagged release | (V1.5) On tagged release deploy. |

**Migration rules (carry forward from backend coordinator memory):**

- One migration per feature (squash within a feature if the specialist authors multiple revisions).
- Never hand-edit a migration after it has been applied to a shared DB (`dev`, `staging`).
- Downgrade path MUST be implemented (even if it `raise NotImplementedError` for irreversible data ops — at least the intent is documented).
- Alembic head divergence between `dev` and `staging` is a P0 blocker — escalate immediately.

### 3.4 Secrets per environment

- **`dev` secrets** are in GCP Secret Manager under labels `env=dev`. Specialists request a secret by name; the infra lead grants access via IAM (per-secret, not project-wide). `dev` secrets may use test-mode credentials (e.g., MSG91 test sender, Razorpay test keys).
- **`staging` secrets** are in GCP Secret Manager under labels `env=staging`. **Production-grade** credentials (real MSG91 sender, real Razorpay test mode but production-grade rate limits). Access is founder-only.
- CI/CD pipelines use **Workload Identity Federation** to access secrets — no JSON keys (per `.github/workflows/ci.yml` line 25).
- Per `CLAUDE.md`: no `.env` files committed; `backend/.env.example` lists keys with placeholder values only.

V1.5 will add a `prod` label and rotation runbooks.

---

## 4. Session Naming Convention

### 4.1 The convention

**Format:** `mesell-{feature-slug}-{group}-session-{N}`

| Token | Meaning | Example |
|---|---|---|
| `mesell` | Project prefix. Always lowercase, always `mesell` (matches the workspace folder, even though `MeeSell` is the brand name). | `mesell` |
| `feature-slug` | The feature's stable kebab-case identifier from §1.2. | `auth-otp` |
| `group` | One of `backend`, `frontend`, `ai`, `data`, `infra`. | `backend` |
| `session-{N}` | Ordinal session number within the (feature × group) tuple, starting at 1. | `session-3` |

**Examples:**

- `mesell-auth-otp-backend-session-1` — first backend session on the auth-otp feature.
- `mesell-auth-otp-backend-session-2` — context window broke, this is the resumption.
- `mesell-smart-picker-ai-session-1` — first AI session on smart picker.
- `mesell-xlsx-export-data-session-1` — first data session on XLSX export.

### 4.2 Where the session name is recorded

The session name appears in **three places**, listed in priority order:

1. **Branch name (when started).** The first commit of `feature/{name}/{group}` is annotated with the session name in the commit message footer:
   ```
   feat: scaffold iam module skeleton

   Session: mesell-auth-otp-backend-session-1
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```
   Subsequent commits on the same branch by the same session do not need the footer (the branch is the session). When a new session resumes work on the branch, that session's first commit re-records the footer with the new session number.

2. **Specialist's memory file.** The specialist appends a session entry to their own `.claude/agent-memory/meesell-<role>/MEMORY.md` at session start. The entry header includes the session name: e.g., `## Session mesell-auth-otp-backend-session-2 — 2026-06-11`.

3. **Lead's `feature_board.md`.** The "current session" column for the feature × group row is updated to the session name when a session opens, cleared when it closes.

### 4.3 What N means

`N` is the **ordinal** of sessions for the (feature × group) tuple. Specifically:

- A new (feature × group) starts at `session-1`.
- When a context window break forces a resume, the next session is `session-2`. This is true even if the work resumes minutes later.
- `N` is monotonically increasing — a closed session never reopens with the same `N`.
- The (feature × group) ordinal counter resets to `1` for each new feature. It does NOT continue across features.

There is NO global session counter and NO timestamp embedded in the session name. Disambiguation by timestamp belongs in the commit and memory entry, not the session ID.

### 4.4 How to resume

When a context break occurs and a new agent (or the same agent in a fresh window) needs to pick up work:

1. The new session reads `STATUS_MASTER.md` to identify which feature × group is in flight.
2. It opens the relevant `feature_board.md` to find the last session number for that (feature × group).
3. It checks out the `feature/{name}/{group}` branch.
4. It reads the last commit message footer to confirm the last session number.
5. It reads the lead's memory file to absorb any in-flight context.
6. It opens session `session-{N+1}`, updates the `feature_board.md` "current session" column, and continues.

The convention is **deliberately stupid**: any agent can compute the next session number from `last + 1`. No ambiguity, no clever lookups, no central counter to break.

---

## 5. PR Template per Group

Five templates, one per group. **All five share three always-required sections** (summary, what changed, test evidence) and add group-specific sections.

V1 reviewer rule: **the founder is always the reviewer.** Every template includes a one-line reminder.

The template files themselves are authored in **sub-plan §9.2** — this section specifies the *content*.

### 5.1 Shared sections (in all 5 templates)

```markdown
## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: <auth-otp>
- V1_FEATURE_SPEC.md section: <§F1>
- BACKEND_ARCHITECTURE.md / FRONTEND_ARCHITECTURE.md section: <§7>

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste `pytest -m "unit"` summary or `ng test` output).
- Smoke results (paste `pytest -m "smoke"` summary).
- Lint results (`make lint` or `pnpm lint` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder
**V1: founder is the sole reviewer. Do not request review from other agents.**

## Session
- Session name: `mesell-{feature}-{group}-session-{N}`
- Lead: `meesell-<lead-name>` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/{group}` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings
```

### 5.2 Backend PR template (`.github/PULL_REQUEST_TEMPLATE/backend.md`)

Adds these sections after the shared block:

```markdown
## Backend-specific evidence

### Database migration
- [ ] Migration authored under `backend/alembic/versions/`
- Revision: `<slug>` (e.g., `f31c75438e61`)
- Down-revision: `<parent_slug>`
- Upgrade tested locally: ✅ / N/A
- Downgrade tested locally: ✅ / N/A (note if irreversible and why)
- Alembic head divergence check between dev and staging: ✅

### Module(s) touched
- [ ] List each `app/modules/<module>/` subtree touched.
- [ ] Import-linter rules updated if a new cross-module call landed (BACKEND_ARCHITECTURE.md §16).
- [ ] §2.D cross-module matrix still holds (no new ✗ → ✓ without an architecture amendment).

### Contract changes (alerts FRONTEND + AI)
- [ ] New / changed endpoint shape documented in commit body
- [ ] If endpoint added: counted toward §17 endpoint inventory (currently 28 mounted)
- [ ] OpenAPI regenerated and reviewed

### Integration test
- Integration test file: `backend/tests/test_<feature>_integration.py`
- Result: pasted in "Test evidence"

### CI gates relevant to this PR
- gate-1 unit · gate-2 smoke · gate-3 lint · gate-4 integration · gate-5 golden_roundtrip (if XLSX touched)
```

### 5.3 Frontend PR template (`.github/PULL_REQUEST_TEMPLATE/frontend.md`)

```markdown
## Frontend-specific evidence

### Components / pages touched
- [ ] List each `frontend/src/app/<area>/` subtree touched.
- [ ] PrimeNG imports remain inside `src/app/ui/` (architecture boundary — see FRONTEND_ARCHITECTURE.md).

### Layer architecture compliance
- [ ] Layer 1 (design-system) untouched OR token addition documented
- [ ] Layer 2 (ui kit) untouched OR new `mee-*` primitive added with tests
- [ ] Layer 3 (shared composites) untouched OR new composite documented
- [ ] Layer 4 (features) is the typical landing zone — confirm

### Build evidence
- `pnpm build` succeeded in <X> seconds (target: < 90 s per CLAUDE.md Decision 12)
- Bundle size delta: `<+/- KB>` (paste relevant `stats.json` excerpt)

### Routes
- [ ] New / changed routes registered in `app.routes.ts`
- [ ] Auth guard correctly applied (or correctly not applied for public)

### Visual evidence
- Screenshot at 360 px width: <attach>
- Screenshot at 1280 px width: <attach>

### Accessibility
- [ ] Keyboard nav works on new interactive elements
- [ ] Color contrast checked on new color usage
- [ ] aria-* attributes added where appropriate

### CI gates relevant to this PR
- gate-1 unit (frontend tests) · gate-3 lint (`ng lint`) · build-frontend
```

### 5.4 AI PR template (`.github/PULL_REQUEST_TEMPLATE/ai.md`)

```markdown
## AI-specific evidence

### Prompt(s) touched
- Workload(s): `smart_picker` / `autofill` / `watermark`
- Prompt registry version bumped: `<old_version>` → `<new_version>` (e.g., `v1` → `v2`)
- File: `backend/app/ai_ops/prompts/<workload>_<version>.py`

### Eval evidence (MUST be green to merge)
- `smart_picker` golden set: top-5 recall = <XX>% (target ≥ 80%)
- `autofill` golden set: invalid-enum rate = <X>% (target = 0%)
- `watermark` golden set: accuracy = <XX>% (target ≥ 85%)
- Eval command: `pytest tests/eval/<workload>/`

### Cost analysis
- Per-call cost on the new prompt: ₹<X.XX> (target ≤ ₹0.05 per MVP_ARCH §8.2)
- Daily projected spend at current QPS: ₹<XX> (₹500 hard cap per BACKEND_ARCHITECTURE.md §6A.F)
- LangFuse trace sample link: <paste>

### Guardrail compliance
- [ ] Layer 1 prompt-prefix constraint preserved
- [ ] Layer 2 enum re-validation passes for the new prompt
- [ ] Layer 3 (Export Adapter) untouched OR change coordinated with backend lead

### CI gates relevant to this PR
- gate-1 unit · ai_eval (nightly job — must be green within last 24 h)
```

### 5.5 Data PR template (`.github/PULL_REQUEST_TEMPLATE/data.md`)

```markdown
## Data-specific evidence

### Source change
- [ ] XLSX template touched: <name + sheet>
- [ ] Category JSON / seed touched: <path>
- [ ] Field alias / enum touched: <table + count delta>

### Parser / scraper evidence
- Run command: `python scripts/<parser>.py --input <X>`
- Output stats: <X> rows parsed, <Y> warnings, <Z> errors
- Diff vs previous run: `<delta>` rows changed

### Schema impact (alerts BACKEND)
- [ ] No schema change — pure data
- [ ] Schema change — Alembic migration coordinated with backend lead

### MVP_ARCHITECTURE.md / MEESHO_CATEGORY_INTELLIGENCE.md amendment
- [ ] Doc amendment included in this PR (preferred)
- [ ] Doc amendment deferred to follow-up PR (justified)

### CI gates relevant to this PR
- gate-1 unit (parser tests) · gate-5 golden_roundtrip (if XLSX touched)
```

### 5.6 Infra PR template (`.github/PULL_REQUEST_TEMPLATE/infra.md`)

```markdown
## Infra-specific evidence

### Terraform plan
- [ ] `terraform plan` run against the affected state file
- Plan output (paste relevant excerpt):
  ```
  Plan: X to add, Y to change, Z to destroy.
  ```
- [ ] No `destroy` actions on production-tier resources without explicit founder sign-off in PR body

### K3s manifest
- [ ] Manifest under `k8s/` touched
- [ ] `kubectl apply --dry-run=server -f <file>` ran clean
- [ ] Namespace target verified (`dev` / `staging`)

### Secrets / IAM
- [ ] Secret Manager refs added / removed listed
- [ ] IAM binding changes listed with principal + role
- [ ] No JSON keys committed
- [ ] Workload Identity Federation paths confirmed

### Deployment evidence
- [ ] Smoke deploy to `dev` succeeded: <pod status paste>
- [ ] Rollback procedure documented if change is high-blast-radius

### Cost impact
- New monthly cost estimate: ₹<XX> (call out if > ₹500/month)

### CI gates relevant to this PR
- gate-3 lint (manifest validation) · deploy-dev (auto-fires post-merge)
```

---

## 6. `feature_board.md` Template

The `feature_board.md` is a **per-lead status tracking file**. Each lead owns one. Specialists update it during their work; the founder/director queries it to get domain status.

### 6.1 File locations (per lead)

| Lead | File |
|---|---|
| Backend lead (`meesell-backend-coordinator`) | `docs/status/feature_board_backend.md` |
| Frontend lead (`meesell-frontend-coordinator`) | `docs/status/feature_board_frontend.md` |
| AI lead (`meesell-ai-coordinator`) | `docs/status/feature_board_ai.md` |
| Data lead (`meesell-data-engineer`) | `docs/status/feature_board_data.md` |
| Infra lead (`meesell-infra-builder`) | `docs/status/feature_board_infra.md` |

These are created on the lead's first use of the board (sub-plan §9.3).

### 6.2 Template structure

```markdown
# Feature Board — {Lead Name}

**Lead agent:** `meesell-<lead-role>`
**Domain:** {backend | frontend | ai | data | infra}
**Last updated:** YYYY-MM-DD HH:MM (Asia/Kolkata)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| auth-otp | feature/auth-otp/backend | IN PROGRESS | mesell-auth-otp-backend-session-2 | 2026-06-10 14:30 | none | Lua rotation script done; awaiting MSG91 sandbox test |
| smart-picker | feature/smart-picker/backend | IN REVIEW | — | 2026-06-10 11:00 | none | PR #42 open; awaiting lead approval |
| catalog-form | feature/catalog-form/backend | BLOCKED | mesell-catalog-form-backend-session-1 | 2026-06-09 18:00 | data — field aliases not seeded | Pinged data lead 2026-06-09 |
| xlsx-export | — | PENDING | — | — | depends on catalog-form | Will start once catalog-form merges to feature/xlsx-export |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| price-calculator | feature/price-calculator | 2026-06-08 | #38 | Clean merge; rolled into develop the same day |
| image-precheck | develop | 2026-06-05 | #35 | Required backend + ai coordination — 2 PRs |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| data | catalog-form | Field aliases for `brand` and `material` need seed update | 2026-06-09 | OPEN |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/{group}` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the active features table until that group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.
```

### 6.3 Status vocabulary (canonical, 5 values)

`PENDING` · `IN PROGRESS` · `IN REVIEW` · `MERGED` · `BLOCKED`

These five values are the only permitted statuses. Do not introduce variants ("WAITING", "PARTIAL", "REVIEW2") — promote to a new value via this master plan amendment first.

### 6.4 "Blocking issues" format

The Blocking column is scannable in **10 seconds or less**. Format:

- `none` — no blocker.
- `{group} — {one-line reason}` — blocked on another group. E.g., `data — field aliases not seeded`.
- `founder — {decision needed}` — blocked on a founder decision. E.g., `founder — confirm 11.7 rate cap`.
- `infra — {resource}` — blocked on infra (secret, DB, etc.). E.g., `infra — MSG91 sandbox key`.
- `tests — {gate name}` — blocked on test failure that the specialist can't resolve. E.g., `tests — gate-4 integration`.

If the blocker text would exceed one line, put a summary on the row and link to a detailed note in `Notes` or the lead's memory file.

### 6.5 Update protocol

| Trigger | Who updates | Field updated |
|---|---|---|
| Lead dispatches specialist on a new feature | Lead | New row added; `Status=IN PROGRESS`; `Current session=...session-1`; `Last touched=now` |
| Specialist pushes commits to `feature/{name}/{group}` | Specialist | `Last touched=now` (always); `Current session=...session-{N}` (if resumed) |
| Specialist opens PR to `feature/{name}` | Specialist | `Status=IN REVIEW`; clear `Current session` |
| Lead approves and merges group PR | Lead | `Status=MERGED`; move row to "Recently merged" within the same edit |
| Specialist hits a blocker | Specialist | `Status=BLOCKED`; populate `Blocking` column; `Notes` if needed |
| Inter-lead request created | Originating lead | Add a row to "Inter-lead requests open" |
| Inter-lead request closed | Resolving lead (the one being asked) | Mark row `CLOSED` and move to bottom of section |

The lead **must** sweep the board at session start and end. Stale entries (older than 7 days untouched) generate a flag in `STATUS_MASTER.md`.

### 6.6 Query protocol (founder/director)

The founder/director queries a lead's status by:

1. Reading the lead's `feature_board.md` (single file, scannable in under a minute).
2. If more detail needed: reading the lead's `STATUS_<domain>.md` (Updates Log).
3. If still more detail needed: reading the lead's `MEMORY.md`.

The lead's response to "how is X going?" should be: "see `feature_board_<domain>.md` row for X — last updated <date>". This forces the lead to keep the board current and avoids re-reporting status verbally.

---

## 7. Lead Agent Responsibilities

Each of the five leads — `meesell-backend-coordinator`, `meesell-frontend-coordinator`, `meesell-ai-coordinator`, `meesell-data-engineer`, `meesell-infra-builder` — has the same **shape** of responsibilities, with content varying by domain.

### 7.1 Universal lead responsibilities

| Concern | Who owns | Detail |
|---|---|---|
| `feature_board_<domain>.md` | Lead | Authored, swept, kept current |
| `STATUS_<domain>.md` | Lead | Updates Log appended after every meaningful chunk |
| Lead's own memory `MEMORY.md` | Lead | Read at session start; appended at session end |
| Specialist dispatch | Lead | Lead dispatches the domain's specialists with the project-boundary preamble |
| Group PR approval | Lead | Lead is the approver on `feature/{name}/{group}` → `feature/{name}` PRs |
| Domain architecture doc | Lead | Backend lead owns `BACKEND_ARCHITECTURE.md`; frontend owns `FRONTEND_ARCHITECTURE.md`; etc. |
| Cross-lead coordination | Lead | Lead opens inter-lead requests on `feature_board_<own>.md` and tracks closure |

### 7.2 Decisions the lead can make without escalation

- Specialist task slicing within an already-approved feature.
- PR approval / rejection on `feature/{name}/{group}` → `feature/{name}` merges.
- Per-feature acceptance criteria within the bounds of the feature spec.
- Branch creation and deletion at the `feature/{name}/{group}` level.
- Choice of test fixtures, test data, and unit test design.
- Choice of file organisation within the existing domain architecture.

### 7.3 Decisions that require escalation to founder

- Architecture amendments (any change to a `LOCKED` section of `BACKEND_ARCHITECTURE.md` / `FRONTEND_ARCHITECTURE.md` / etc.).
- New endpoint contracts that change `V1_FEATURE_SPEC.md`.
- Cost-impactful infra changes (>₹500/month new spend).
- Cross-group decisions where leads disagree (escalate to founder rather than negotiate beyond two rounds).
- Adding or removing a feature from V1 scope.
- Modifying branch protection rules.
- Approving a `feature/{name}` → `develop` PR (V1 rule — only the founder approves these).

### 7.4 Handoff protocol — specialist → lead

When a specialist completes their slice:

1. Specialist pushes final commit to `feature/{name}/{group}` and runs CI gates locally.
2. Specialist opens PR using the group's template (§5).
3. Specialist updates `feature_board_<domain>.md` row to `IN REVIEW`, clears `Current session`.
4. Specialist appends a session-close entry to their own memory file.
5. Lead reviews PR against the acceptance criteria + group PR template.
6. Lead either approves+merges, or comments+returns. No "blocking with no comments" — the lead must articulate what's missing.
7. After merge, lead updates `feature_board_<domain>.md` row to `MERGED`, moves to "Recently merged".

### 7.5 Cross-lead coordination

When two leads need to coordinate (e.g., backend API contract change affects frontend):

1. The **initiating lead** opens a row in their own `feature_board_<domain>.md` "Inter-lead requests open" section.
2. The initiating lead writes a one-paragraph memo to `.claude/agent-memory/meesell-<initiator>/handoff_<topic>.md` — the resolving lead reads this directly (per decentralized memory protocol).
3. The **resolving lead** acknowledges by reading the memo and adding a corresponding row to their own board's "Inter-lead requests open" — incoming side.
4. When resolved: both leads close their respective rows.
5. If the request is not acknowledged within 48 hours: escalate to founder via `STATUS_MASTER.md` blockers section.

**Common cross-lead pairs:**

- backend ↔ frontend: API contract changes (endpoint shape, response model)
- backend ↔ ai: prompt registry changes (workload addition, version pin)
- backend ↔ data: schema or seed changes (new field alias, new template)
- backend ↔ infra: secret rotation, DB migration apply, namespace config
- frontend ↔ ai: feature flag gating for AI-driven UI affordances
- frontend ↔ infra: CDN, ingress, CSP changes (esp. for Phase 2 federation)
- data ↔ ai: golden eval set updates when category data shifts
- data ↔ infra: bucket layout, ETL pipeline scheduling

---

## 8. Cross-Feature Conflict Resolution

Two features that touch the same file = the "shared file problem". Microservices + module federation reduce this dramatically — but it does NOT eliminate it. Shared code still exists in:

- `backend/app/shared/` (foundation layer — 13 ORM models, async session factory, Pydantic settings)
- `backend/app/core/` (auth, tenancy, cache, plan_guard, errors, middleware)
- `backend/app/i18n/` (validation messages)
- `frontend/libs/core/` (AuthService, ApiClient, interceptors per module federation plan)
- `frontend/libs/ui-kit/` (17 `mee-*` primitives)
- `frontend/libs/composites/` (5 composites)
- `frontend/libs/design-tokens/` (SCSS tokens)
- Alembic migrations (single linear chain — even after extraction, V1 lives in one repo)

### 8.1 Detection (pre-merge)

**Static.** A `check-shared-touches` CI job runs on every `feature/{name}/{group}` PR:

- Computes the diff vs `feature/{name}` parent.
- If the diff touches any file under the shared paths above, the job posts a comment:
  > `⚠️ This PR touches shared code. Confirm coordination with other in-flight features. Run \`git log --all --since="14 days" -- <file>\` to find concurrent work.`

The comment is **informational**, not blocking. The merge isn't blocked, but the lead is alerted.

**Dynamic.** When two `feature/{name}/{group}` branches concurrently touch the same shared file, the second one to rebase onto `feature/{name}` (or onto `develop` for transitive contention) will hit a merge conflict — the standard git mechanism. The conflict is resolved by the specialist on the second branch with the lead's review.

### 8.2 Resolution protocol — who breaks the tie

| Conflict type | Who breaks the tie |
|---|---|
| Conflict in shared code BUT in different functions / different lines | Specialist on the conflicting branch — standard rebase resolution. |
| Conflict in shared code at the same lines, no semantic change | Specialist on the conflicting branch — accept incoming, re-test. |
| Conflict in shared code with **semantic disagreement** (both features need the function to behave differently) | Owning lead (e.g., backend lead for `app/shared/` and `app/core/`). |
| Conflict across leads' domains (e.g., backend's API contract change vs frontend's consumer expectations) | Both leads coordinate via the §7.5 cross-lead protocol. |
| Lead-to-lead deadlock | Founder. |

### 8.3 The "shared code extraction" pattern

When a piece of shared code is contested by two features:

1. The owning lead recognises the contention (via §8.1 detection).
2. **Promote the shared piece to its own library / module FIRST**, on a precursor branch (e.g., `feature/extract-pricing-helper`).
3. Get the extraction PR merged through `feature` → `develop` quickly (it should be a pure refactor — no behaviour change).
4. The two contesting features then rebase on the new `develop` and each integrates with the extracted shared piece independently.

This pattern is the **single most effective** conflict reducer. It is mandatory when:

- Three or more features all touch the same function in a single sprint.
- A shared file has been the source of two or more reverts in the last 30 days.

### 8.4 What microservices + module federation do NOT solve

| Surface | Reduction | Residual contention |
|---|---|---|
| Backend per-module code | High — each module's `service.py` / `repository.py` is touched by one feature at a time, typically | Cross-module call edges (`§2.D` matrix in `BACKEND_ARCHITECTURE.md`) still couple consumers and producers |
| Backend shared code | Low — `shared/`, `core/`, `i18n/` are touched by many features | This is where most conflicts will land |
| Frontend per-remote code | High (once federation lands) | Each remote owns its routes and components |
| Frontend shared libs | Low — `@mesell/ui-kit`, `@mesell/core`, `@mesell/composites` are touched by many features | Same issue as backend shared code |
| Alembic migrations | Medium — single linear chain forces ordering | Two features both adding a migration must coordinate the parent revision |
| Single-instance singletons (Auth, Toast) | Low — by definition, one instance | Contract changes affect all consumers |

The conflict resolution protocol above (§8.1–§8.3) is built to handle the residual contention.

---

## 9. Sub-Plans List

Each sub-plan is authored AFTER this MASTER_PLAN is ratified by the founder. Each has a single author and a target location. Sub-plans are scoped narrowly so that they can be approved independently.

### 9.1 Lead agent CLAUDE.md spec rewrites (one per lead)

| Field | Value |
|---|---|
| Purpose | Update each lead agent's spec file at `.claude/agents/meesell-<role>.md` to reflect the new lead-agent responsibilities (§7), `feature_board.md` ownership (§6), branch model awareness (§1), and PR template usage (§5). |
| Author | Each lead authors their own update on a `feature/lead-spec-update/<lead>` branch. |
| Stored at | `.claude/agents/meesell-backend-coordinator.md` (and the other four). |
| Acceptance | Founder reviews each rewrite individually. |
| Sequence | Can be done in parallel. None blocks another. |

### 9.2 PR template files authoring

| Field | Value |
|---|---|
| Purpose | Create the five PR template files specified in §5. |
| Author | Backend coordinator drafts all five (they share structure); each lead reviews their own group's template. |
| Stored at | `.github/PULL_REQUEST_TEMPLATE/backend.md`, `frontend.md`, `ai.md`, `data.md`, `infra.md`. |
| Acceptance | Founder approves the five templates as a single PR. |
| Sequence | Must land BEFORE the first `feature/{name}/{group}` PR is opened. |

### 9.3 `feature_board.md` initial state creation (one per lead)

| Field | Value |
|---|---|
| Purpose | Create the initial empty `feature_board_<domain>.md` for each lead, per the §6 template. |
| Author | Each lead authors their own. |
| Stored at | `docs/status/feature_board_backend.md` (and the other four). |
| Acceptance | Lead self-creates on first use; founder reviews the structure once across all five. |
| Sequence | Can be created lazily — first time a lead dispatches a specialist on a feature, they create the board. |

### 9.4 `develop` and `staging` branch creation

| Field | Value |
|---|---|
| Purpose | Create the two long-lived integration branches off `main`. |
| Author | Founder, manually, via the GitHub UI or `git push origin main:develop && git push origin main:staging`. |
| Stored at | GitHub repo `mesell` — branches `develop` and `staging`. |
| Acceptance | Founder confirms branches exist. |
| Sequence | Must land BEFORE the first `feature/{name}` branch is created. |

### 9.5 Branch protection rules

| Field | Value |
|---|---|
| Purpose | Configure GitHub branch protection on `main`, `staging`, `develop` per §1.1. |
| Author | Founder, via GitHub Settings → Branches. |
| Stored at | GitHub repo settings (not in version control). |
| Acceptance | Founder confirms the three rules apply and that "Include administrators" is checked where appropriate. |
| Sequence | Must land BEFORE the first PR is merged into `develop`. |

### 9.6 Sub-plan sequence (recommended order)

```
1. §9.4 develop + staging branches            ─┐
2. §9.5 branch protection rules               ─┤  (all three are pre-requisites)
3. §9.2 PR template files                     ─┘
4. §9.1 lead agent CLAUDE.md rewrites         (parallel; needed before next feature dispatch)
5. §9.3 feature_board.md initialisation       (lazy; first-use basis)
```

---

## 10. Acceptance Gate

This plan is **not executable** until the following three preconditions are met. Until then, this plan remains DRAFT and no agent acts on it.

1. **Founder reviews and APPROVES this MASTER_PLAN.md.** Approval is signalled by flipping the STATUS header from `DRAFT` to `APPROVED YYYY-MM-DD`. The founder may amend any section before approving; amendments are recorded in §11 revision history.
2. **The two prerequisite architecture plans are APPROVED.** Specifically:
   - `docs/plans/module_federation/MASTER_PLAN.md` (currently DRAFT 2026-06-10). This plan defines the six frontend remotes — which is what a "feature" looks like on the frontend side.
   - `docs/plans/microservices_migration/...MASTER_PLAN.md` (not yet authored as of 2026-06-10; backend-coordinator owned). This plan defines the eight backend module-to-microservice extraction sequence per `BACKEND_ARCHITECTURE.md §16.H` — which is what a "feature" looks like on the backend side post-extraction.
3. **`develop` and `staging` branches exist in the GitHub remote.** Per sub-plan §9.4. This unblocks the entire merge flow described in §2.

Once all three are met, the master session announces "Repo Management plan ACTIVE" in `STATUS_MASTER.md` and the leads may begin operating under the convention.

If any of the three preconditions slips (e.g., microservices plan rejected and returned for redesign), this plan stays DRAFT and any partial operationalisation already underway is paused. Active feature branches are NOT deleted, but no new feature branches are opened until the plan re-enters APPROVED status.

---

## 11. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial DRAFT authored. Awaiting founder review. |
| 1.0 | 2026-06-10 | founder + meesell-backend-coordinator | Ratified DRAFT → APPROVED. Decisions D1/D2/D3 locked. Status: executable. |
