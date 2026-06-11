# Session Dispatch: Auth — Phone OTP Login + JWT
**Session name:** `mesell-auth-otp-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/auth-otp/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop. No upstream feature dependency — this is the prerequisite for every other feature.
**Lead involvement:** Backend (primary — iam module + MSG91 + JWT) · Frontend (3 pages + AuthService + interceptor + guard) · Infra (Secret Manager rotation + refresh-token-pepper)

---

## Why this session exists
Auth is the foundation. Every other V1 feature (Smart Picker, Catalog Form, AI Autofill, Image Pre-check, Live Preview, Price Calculator, Tracking Dashboard, XLSX Export) requires a logged-in seller — every endpoint in §5 of `V1_FEATURE_SPEC.md` is JWT-protected except `/auth/otp/*`. If auth ships broken, every other feature is unreachable in `staging`.

Auth is also the most contract-sensitive feature in V1 because the FE-D5 ratification (2026-06-05, recorded in `BACKEND_ARCHITECTURE.md §0.C + §4.B + §4.G`) split the simple "JWT in localStorage" pattern from `V1_FEATURE_SPEC §F1` into a server-rotated refresh-cookie model. That split adds 2 new endpoints (`/auth/refresh`, `/auth/logout`), a Valkey allowlist with HMAC-pepper hashing, a Lua rotation script, an `HttpOnly` cookie with `Path=/api/v1/auth`, and a new infra secret. This planning session must lock how those 5 surfaces compose before the iam module is constructed — getting it wrong forces a re-do of every other feature's auth wiring.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-auth-otp-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/auth-otp/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Auth — Phone OTP Login + JWT feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for auth-otp. Verify:
pwd                                          # must print /private/tmp/mesell-wt/auth-otp or /tmp/mesell-wt/auth-otp
git worktree list | grep auth-otp      # must show this worktree
git branch --show-current                     # must print feature/auth-otp/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh auth-otp (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates, §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F1 (Feature 1: Auth) — INCLUDING the FE-D5 amendment block on access JWT in-memory + refresh cookie + Lua rotation + 15-min access / 7-day refresh TTLs
- docs/BACKEND_ARCHITECTURE.md §0.C amendment block (27-endpoint total, 2 new auth endpoints), §4.B amendment (split-token contract + Lua + HMAC pepper), §4.G amendment (CORS for refresh cookie), §7 (iam module — endpoints, service surface, repository, exceptions, audit events)
- docs/FRONTEND_ARCHITECTURE.md — auth-layout, AuthService contract, JWT interceptor, RefreshInterceptor, AuthGuard, withCredentials behavior on /api/v1/auth/*
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — iam is service 7 of 8 in extraction order (per BACKEND_ARCHITECTURE.md §16.H)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — auth-layout is the 6th/last federated remote (login/signup/otp-verify live in the shell until then)
- CLAUDE.md — Decision 14 (MSG91 + JWT + FE-D5 amendment), Valkey DB 0 routing, agent fleet
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-infra-builder.md
- Each involved lead's MEMORY.md
- Each involved lead's docs/status/feature_board_{backend|frontend|infra}.md (verify auth-otp is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/auth-otp.yaml instead.

Create (or overwrite) docs/plans/features/_status/auth-otp.yaml with:
feature: "auth-otp"
session: "mesell-auth-otp-planning-session-1"
worktree: "/tmp/mesell-wt/auth-otp"
branch: "feature/auth-otp/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/auth-otp/FEATURE_PLAN.md
feature_plan_line_count: null
pr_number: null
pr_url: null
outstanding_founder_decisions: []
notes: |
  Planning session opened in worktree.
 
DO NOT commit this file yet — it will be committed alongside FEATURE_PLAN.md in Step 8.

If your status file already exists and shows IN_PROGRESS (a prior session was interrupted): proceed but flag this in the ## Decisions section of your FEATURE_PLAN.md so the founder knows.
## Step 1 — Surface scope decisions to the founder
Before drafting the plan, ask the founder to lock these 3 questions:

Decision 1 — Scope confirmation
  Does this feature still match V1 spec §F1 INCLUDING the FE-D5 amendment block? Specifically:
    - Access JWT held in-memory by the frontend, NOT localStorage
    - Refresh token as HttpOnly+Secure+SameSite=Strict cookie at Path=/api/v1/auth
    - Lua-script atomic rotation on Valkey allowlist (DB 0)
    - HMAC-SHA256 with REFRESH_TOKEN_PEPPER hash key shape (not bare SHA-256)
    - 15-min access / 7-day refresh TTLs (env-driven via ACCESS_TOKEN_TTL_SECONDS / REFRESH_TOKEN_TTL_SECONDS)
    - 2 new endpoints: POST /api/v1/auth/refresh, POST /api/v1/auth/logout
  Any cuts, additions, or scope flexes since FE-D5 was ratified?

Decision 2 — Feature flag posture
  Per master plan §3.2, a half-built feature can land on develop only behind a feature flag. Confirm the flag name (suggested: FEATURE_AUTH_OTP_ENABLED) and the dev/staging defaults. Caveat: because every other feature depends on auth, a "disabled" auth flag effectively disables every catalog/category/image route — so the flag likely defaults to true in BOTH dev and staging once any auth code lands, and is removed entirely at the first release. Confirm this rationale.

Decision 3 — Priority ordering vs sibling features
  This feature touches the same shared code (backend/app/core/auth.py middleware, frontend libs/core/AuthService, infra Secret Manager) as ALL other V1 features that need a logged-in seller. Auth must land first. Confirm: auth-otp ships before any sibling feature's PR is opened to develop. (Smart Picker and Tracking Dashboard are the next candidates per V1_FEATURE_SPEC §7 build order.) If founder wants parallel UI work on, e.g., Tracking Dashboard mocked against a fake AuthService while auth-otp is in flight, capture that.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | auth-builder (primary), database-builder, api-routes-builder, services-builder | auth-builder: JWT issuance/verification, RefreshInterceptor server-side logic, Lua rotation script, HMAC-pepper key derivation, MSG91 adapter integration, cookie attributes; database-builder: users table model + first migration; api-routes-builder: /otp/send /otp/verify /refresh /logout /me route handlers + Pydantic schemas in iam module; services-builder: otp_service.py (Valkey DB 0 OTP store with 5-min TTL + 3/h/phone rate limit), rate-limit decorator |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: LoginComponent, SignupComponent, OtpVerifyComponent (3 standalone components with reactive forms); angular-service-builder: AuthService (signal-based access token in memory), JwtInterceptor (attaches Authorization header), RefreshInterceptor (silent /auth/refresh on 401), AuthGuard (route protection) |
| meesell-infra-builder | (standalone) | GCP Secret Manager entries for REFRESH_TOKEN_PEPPER, MSG91_AUTH_KEY, JWT_SECRET; IAM Workload Identity binding for the backend service account; namespace env wiring for ACCESS_TOKEN_TTL_SECONDS / REFRESH_TOKEN_TTL_SECONDS in dev (60s/300s) and staging (900s/604800s) per BACKEND_ARCHITECTURE.md §5.D table |

Only include leads + specialists who actually have work. AI / Data tracks have NO work on this feature — omit.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain. Include:
- Backend: routes (app/modules/iam/routes.py), schemas (app/modules/iam/schemas.py), services (app/modules/iam/service.py, app/modules/iam/repository.py), models (app/shared/models/user.py), middleware (app/core/auth.py for get_current_user dep), Lua script (app/modules/iam/lua/rotate_refresh.lua), MSG91 adapter (app/adapters/msg91.py), Alembic migration (app/alembic/versions/<rev>_iam_users.py), tests (backend/tests/test_iam_unit.py, backend/tests/test_auth_otp_integration.py)
- Frontend: pages (frontend/src/app/pages/login/login.component.ts, signup/signup.component.ts, otp-verify/otp-verify.component.ts), services (frontend/src/app/services/auth.service.ts), interceptors (frontend/src/app/core/interceptors/jwt.interceptor.ts, refresh.interceptor.ts), guard (frontend/src/app/core/guards/auth.guard.ts), routes (frontend/src/app/app.routes.ts), tests (frontend/src/app/services/auth.service.spec.ts, frontend/src/app/pages/login/login.component.spec.ts)
- AI: NONE (no AI work for auth)
- Data: NONE
- Infra: k8s/dev/api-secrets.yaml (env-var refs for REFRESH_TOKEN_PEPPER + MSG91_AUTH_KEY + JWT_SECRET), k8s/dev/api-deployment.yaml (env block additions for ACCESS_TOKEN_TTL_SECONDS + REFRESH_TOKEN_TTL_SECONDS), k8s/staging mirror of both, terraform/secret-manager/refresh-token-pepper.tf (new secret resource), terraform/iam/api-sa-bindings.tf (Workload Identity grant)
- Docs: docs/V1_FEATURE_SPEC.md §F1 (mark FE-D5 acceptance criteria as "implemented" once shipped — no spec rewrite), docs/BACKEND_ARCHITECTURE.md §7 (flip iam module STATUS from LOCKED-on-paper to LOCKED-on-disk via a sentinel commit reference)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entries for POST /otp/send, POST /otp/verify, POST /refresh, POST /logout, GET /me — auto-generated from Pydantic schemas, reviewed in PR
- Frontend: route entries in app.routes.ts comment-block, AuthService inline docstring describing the in-memory signal + RefreshInterceptor flow
- AI: N/A
- Data: N/A
- Infra: deployment runbook addendum in docs/runbooks/auth-secret-rotation.md (NEW) — how to rotate REFRESH_TOKEN_PEPPER without invalidating all live sessions (Lua script supports key versioning per BACKEND_ARCHITECTURE.md §4.B)
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F1 marked "implemented YYYY-MM-DD" with PR link

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-auth-otp-{group}-session-{N}` format)
- Mandatory reads for the specialist
- Acceptance criteria (specific to that specialist's slice)
- Hard constraints
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format

Specialists to template:
- meesell-auth-builder (backend lead dispatches) — JWT + Lua rotation + HMAC pepper + cookie attrs
- meesell-database-builder (backend lead dispatches) — users table model + migration
- meesell-api-routes-builder (backend lead dispatches) — 5 iam routes + schemas
- meesell-services-builder (backend lead dispatches) — otp_service.py + rate limiter
- meesell-angular-component-builder (frontend lead dispatches) — Login/Signup/OtpVerify
- meesell-angular-service-builder (frontend lead dispatches) — AuthService + 2 interceptors + guard
- meesell-infra-builder (standalone — founder dispatches directly per CLAUDE.md hierarchy) — Secret Manager + namespace env

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: Lua script is `EVALSHA`-with-`EVAL`-fallback per §4.B; HMAC uses `secrets.compare_digest`; cookie Path is `/api/v1/auth` not `/auth`; access JWT TTL reads from ACCESS_TOKEN_TTL_SECONDS not deprecated JWT_EXPIRY_DAYS)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (or frontend / infra as appropriate)
- What triggers a re-dispatch (specific failure modes — e.g., Lua script uses MULTI/EXEC instead of EVAL → re-dispatch with §4.B counter-proposal 1 quoted; AuthService stores token in localStorage → re-dispatch with FE-D5 quoted; cookie missing SameSite=Strict → re-dispatch)
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/auth-otp/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., MSG91 staging credit exhaustion, Lua script EVAL incompatibility with older Valkey versions, HMAC pepper rotation breaking live sessions, cookie domain mismatch in dev vs staging, FE refresh storm under network flap)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/auth-otp/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/auth-otp.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/auth-otp/FEATURE_PLAN.md
git add docs/plans/features/_status/auth-otp.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock auth-otp feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-auth-otp-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/auth-otp/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/auth-otp/planning \
  --title "docs(plan): lock auth-otp feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update auth-otp status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md
- [ ] Agent lineup table fully filled out (backend 4 specialists + frontend 2 specialists + infra standalone named)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI, AuthService docstring, secret-rotation runbook, V1_FEATURE_SPEC §F1 implemented stamp)
- [ ] One dispatch template per specialist drafted (7 templates total)
- [ ] Review + iteration protocol defined (with Lua/HMAC/cookie-path failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/auth-otp/planning
- [ ] PR opened to develop using backend PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/iam/, frontend/src/app/services/auth.service.ts, k8s/, terraform/, ai_ops/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-auth-otp-{group}-session-{N}` per master plan §4
- Every dispatch template MUST cite the specific BACKEND_ARCHITECTURE.md amendment block (§0.C / §4.B / §4.G / §7) the specialist must read — FE-D5 ratification is the contract
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend, infra) has reviewed their section's dispatch templates
- [ ] PR open to develop using the backend PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- FE-D5 ratification (BACKEND_ARCHITECTURE.md §0.C + §4.B + §4.G + §7 amendments) is the binding contract — any plan that contradicts FE-D5 must be flagged for founder re-ratification before FEATURE_PLAN.md is committed

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
