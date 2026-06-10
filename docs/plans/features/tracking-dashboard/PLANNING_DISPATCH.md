# Session Dispatch: Tracking Dashboard — Seller's Product Status Overview
**Session name:** `mesell-tracking-dashboard-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/tracking-dashboard/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; catalog-form shipped (dashboard reads from catalog.service.list_products — the cross-module signature locked at `BACKEND_ARCHITECTURE.md §13.D` and §10.C)
**Lead involvement:** Backend (dashboard module — owns ZERO tables, the "purest demonstration of modular monolith discipline" per memory turn 20; 1 endpoint `GET /api/v1/products` composing across catalog + customer) · Frontend (dashboard page + product row + status badge + filters)

---

## Why this session exists
Tracking Dashboard is the **seller's home surface** — the page they land on after every login. It sets the daily-use UX tone. Per `BACKEND_ARCHITECTURE.md §13` (LOCKED) it is also the architectural pure-composition reference module: dashboard owns ZERO tables, has NO `repository.py` (a documented structural deviation from §3.C canonical 7-file layout per memory turn 20), and reads NOTHING directly. Every byte of dashboard's response comes from calling `catalog.service.list_products(user_id, Pagination)` per §10.C + `customer.service.get_profile_completeness(user_id)` per §8.C. This makes the dashboard module the canonical V1 demonstration of the modular monolith pattern that the microservices extraction order locks in `BACKEND_ARCHITECTURE.md §16.H` (dashboard extracts cleanly second — service 2 of 8 — because it owns no schema).

The dashboard is also the cheapest construction in V1 (3h backend + 5h frontend per `V1_FEATURE_SPEC §7`) which makes it an early-ship candidate that doesn't block downstream features. It can be the first feature dispatched in parallel with the catalog-form spine because it consumes only the catalog read surface; its merge to `develop` provides early end-to-end smoke coverage. Per memory turn 20, dashboard is one of 3 plan_guard-excluded modules in V1 — confirming the deterministic non-AI nature of this surface.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-tracking-dashboard-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/tracking-dashboard/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Tracking Dashboard feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for tracking-dashboard. Verify:
pwd                                          # must print /private/tmp/mesell-wt/tracking-dashboard or /tmp/mesell-wt/tracking-dashboard
git worktree list | grep tracking-dashboard      # must show this worktree
git branch --show-current                     # must print feature/tracking-dashboard/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh tracking-dashboard (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates, §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F8 (Feature 8: Tracking Dashboard) — load ≤500ms with 100 products, color-coded status badge (gray draft / blue exported / green live), pagination >20 products, search by name (ILIKE on products.name) ≤500ms, soft-delete via modal confirm, empty state "Create your first catalog", "Live" status manually set by user with tooltip clarifying Meesho has no API
- docs/BACKEND_ARCHITECTURE.md §13 (dashboard module LOCKED — 1 endpoint GET /api/v1/products paginated listing for Feature 8; owns ZERO tables, reads NOTHING directly, NO repository.py; calls catalog.service.list_products per §10.C + customer.service.get_profile_completeness per §8.C; per §2 founder ruling matrix kept at exactly 8 ✓ — V1 dashboard does NOT opt into image/pricing/export.service.summary OPTIONAL surfaces — V1.5 amendment may elevate to 11 ✓ but NOT now; 1-method public service surface list_products_for_dashboard + 1-method module-private _compose_response pure function; 1 InvalidPaginationError exception class; NO adapter usage zero egress per §1.E confirming P95 ≤200ms budget; plan_guard NOT participating in V1; rate-limit per-IP only; audit NONE on read-only endpoint; cache helper NOT participating high write churn from product PATCH would tank hit rate; 1 i18n key validation.dashboard.invalid_pagination)
- docs/FRONTEND_ARCHITECTURE.md — dashboard page lives in mfe-dashboard (4th remote in federation order per module_federation MASTER_PLAN §4.2); pre-federation under frontend/src/app/pages/dashboard/; DashboardComponent + ProductRowComponent + StatusBadgeComponent + filter dropdown
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — dashboard is service 2 of 8 in extraction order per §16.H (cleanest extraction because owns no tables — pure composition over HTTP shims to catalog + customer post-extraction)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — dashboard is part of mfe-dashboard (4th remote in federation order); pre-federation in the shell
- CLAUDE.md — OnPush change detection, async pipe, mat-paginator + mat-table from Angular Material per Tailwind+Material decision
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md
- Each involved lead's MEMORY.md (especially backend-coordinator turn 20 for the §13 module deep content + the "purest modular monolith" framing)
- Each involved lead's docs/status/feature_board_{backend|frontend}.md (verify tracking-dashboard is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/tracking-dashboard.yaml instead.

Create (or overwrite) docs/plans/features/_status/tracking-dashboard.yaml with:
feature: "tracking-dashboard"
session: "mesell-tracking-dashboard-planning-session-1"
worktree: "/tmp/mesell-wt/tracking-dashboard"
branch: "feature/tracking-dashboard/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F8? Specifically:
    - Load ≤500ms with 100 products (P95 ≤200ms backend per §13 budget; UI render adds the remaining ~300ms budget)
    - Pagination: page=1&limit=20 default, with explicit page-size selector (20/50/100)
    - Status badge color-coded: gray (draft) / blue (exported) / green (live)
    - Search by name: ILIKE on products.name with pg_trgm index (already established in foundation pass per memory)
    - Filter by status: client-side filter on the fetched page OR server-side filter via query param (recommendation: server-side via query param for >100-product accounts)
    - Soft-delete via modal confirm — DELETE /api/v1/products/{id} (this is a catalog endpoint, NOT a dashboard endpoint) writes deleted_at column; dashboard list filters out soft-deleted rows
    - Empty state: "Create your first catalog" CTA routes to /catalogs/new (smart-picker page)
    - "Live" status is manually set by user (Meesho has no API to confirm); UI tooltip clarifies
  Also resolve: Does the dashboard show profile-completeness banner (customer.service.get_profile_completeness)? Recommendation: yes for V1 — a "Complete your seller profile (compliance docs)" banner at the top of the dashboard when get_profile_completeness < 100% — this is the only reason §13 calls customer.service. Confirm or override.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_TRACKING_DASHBOARD_ENABLED). Dev default: true. Staging default: true after a single round of founder UX review (the dashboard is the seller's home; flagging it off means logging in to a blank shell which is unusable — so the flag is more of a kill-switch than a soft launch). When disabled, GET /api/v1/products returns 404 and the /dashboard route shows "Dashboard temporarily disabled" placeholder.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend per-module code: app/modules/dashboard/ (greenfield — no contention)
    - Backend shared code: NONE (dashboard owns no tables, no shared models touched)
    - Backend cross-module calls: catalog.service.list_products (consumed only, no contention) + customer.service.get_profile_completeness (consumed only, no contention)
    - Frontend per-feature code: frontend/src/app/pages/dashboard/ (greenfield)
  Confirm: tracking-dashboard ships after catalog-form (list_products dependency). It can ship in PARALLEL with smart-picker and live-preview because it consumes only the catalog read surface. Early ship is encouraged because the dashboard provides login-to-end-to-end smoke coverage for all downstream features that produce dashboard rows.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder | api-routes-builder: GET /api/v1/products route + Pagination Pydantic schema + ProductListResponse with product rows + pagination meta + ProfileCompletenessBanner sub-shape (per Decision 1); InvalidPaginationError exception per §13; services-builder: dashboard.service.list_products_for_dashboard(user_id, pagination) — calls catalog.service.list_products + customer.service.get_profile_completeness per §13.C; pure-function _compose_response helper for the shape transformation per §13.D; NO repository.py per §13 documented structural deviation (mark this absence explicitly in the dispatch — specialists must NOT create dashboard/repository.py); database-builder NOT involved (zero schema changes per §13.D) |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: DashboardComponent (page with mat-table + mat-paginator + filter dropdown + search input) + ProductRowComponent (per-row) + StatusBadgeComponent (color-coded badge per Decision 1) + ProfileCompletenessBanner (top banner when <100% per Decision 1), under frontend/src/app/pages/dashboard/; soft-delete modal confirm via MatDialog; empty-state CTA route to /catalogs/new; angular-service-builder: DashboardService.list(pagination, filters) wrapping HttpClient call; debounced search input fires server-side query per 300ms after typing stops |
| meesell-ai-coordinator | (no work) | Dashboard is non-AI per §13. Confirm. |
| meesell-data-engineer | (no work) | No data changes; categories/products already seeded. Confirm. |
| meesell-infra-builder | (no work) | No new secrets, no new buckets, no manifest changes. Confirm. |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/dashboard/routes.py (NEW), app/modules/dashboard/schemas.py (NEW — Pagination, ProductListResponse, ProductRow, ProfileCompletenessBanner, InvalidPaginationError), app/modules/dashboard/service.py (NEW — list_products_for_dashboard + _compose_response), app/modules/dashboard/__init__.py (NEW — empty init exposing service surface only per §16.A), app/modules/dashboard/repository.py (EXPLICITLY DOES NOT EXIST — §13.D documented structural deviation; add a README or `__init__.py` comment explaining the absence so the import-linter rules don't flag it), backend/tests/test_dashboard_unit.py (NEW — compose-response shape tests with mocked catalog + customer services), backend/tests/test_tracking_dashboard_integration.py (NEW — end-to-end dashboard load + pagination + search)
- Frontend: frontend/src/app/pages/dashboard/dashboard.component.ts (NEW), frontend/src/app/pages/dashboard/product-row.component.ts (NEW), frontend/src/app/pages/dashboard/status-badge.component.ts (NEW), frontend/src/app/pages/dashboard/profile-completeness-banner.component.ts (NEW), frontend/src/app/services/dashboard.service.ts (NEW), frontend/src/app/app.routes.ts (MODIFY — register /dashboard route with AuthGuard), frontend/src/app/pages/dashboard/dashboard.component.spec.ts (NEW)
- AI: NONE
- Data: NONE
- Infra: NONE
- Docs: docs/V1_FEATURE_SPEC.md §F8 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §13 sentinel flip (LOCKED-on-paper → LOCKED-on-disk via PR link), docs/MEESELL_AGENT_REGISTRY.md cross-reference (verify dashboard service surface matches §13 lock), tests/lint/import_rules.toml MODIFY (add §13.D dashboard-no-repository allowlist entry per §16.G + memory turn 20)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entry for GET /api/v1/products with Pagination query params + ProductListResponse shape including profile_completeness_banner sub-shape; inline service-method docstring on list_products_for_dashboard documenting the 2-call composition pattern per §13.C + the documented absence of repository.py per §13.D
- Frontend: route entry comment in app.routes.ts; DashboardComponent docstring describing the mat-table + paginator + search-debounce flow; StatusBadgeComponent docstring documenting the 3-color contract; ProfileCompletenessBanner docstring on the dismiss-and-remind-tomorrow UX
- AI: N/A
- Data: N/A
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F8 marked "implemented YYYY-MM-DD" with PR link; import_rules.toml entry per memory turn 20 documenting the dashboard-no-repository structural exception

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-tracking-dashboard-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., services-builder reads §13 + §10.C catalog.list_products signature + §8.C customer.get_profile_completeness signature + the NO-repository structural deviation; api-routes-builder reads §13.B endpoint + InvalidPaginationError shape)
- Acceptance criteria (specific to that specialist's slice — e.g., services-builder: list_products_for_dashboard P95 ≤200ms with 100 products, _compose_response is a pure function with no side effects, NO repository.py created, NO direct DB access, all data flows through catalog + customer service surfaces; api-routes-builder: GET /products with limit=20 default, max limit=100, InvalidPaginationError on limit>100 or page<1)
- Hard constraints (e.g., NO repository.py in modules/dashboard/ — §13.D structural deviation; NO direct DB access — all reads via catalog.service or customer.service; NO writes — dashboard is read-only; NO cache helper participation — write churn would tank hit rate per §13)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch (especially flag: do NOT create app/modules/dashboard/repository.py — this is the documented structural exception)
- Final report format (P95 latency measurement, compose-response test pass count, OpenAPI shape verification)

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: dashboard/repository.py does NOT exist; only catalog.service + customer.service are imported in dashboard/service.py; P95 latency measured under 200ms with 100-row seed; import_rules.toml has the §13.D allowlist entry; frontend lead checks: mat-table + paginator from Angular Material; OnPush change detection; search debounce 300ms confirmed in chrome DevTools network tab; soft-delete confirm modal accessible by keyboard)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (cross-module contract section — list_products + get_profile_completeness signatures match §10.C and §8.C exactly) + `.github/PULL_REQUEST_TEMPLATE/frontend.md` (build evidence + visual screenshots)
- What triggers a re-dispatch (specific failure modes — repository.py exists → re-dispatch services-builder with "delete dashboard/repository.py — §13.D documented absence; all data flows via service-layer cross-module calls"; direct DB query found → re-dispatch with "no AsyncSession injection in dashboard/service.py — call catalog.service or customer.service only"; P95 >200ms → re-dispatch with "verify catalog.list_products applies pagination at SQL level not in Python; verify pg_trgm GIN index on products.name is hit per EXPLAIN ANALYZE for search queries"; search debounce missing → re-dispatch frontend with "verify debounceTime(300) operator on searchInput.valueChanges")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/tracking-dashboard/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1, including the profile-completeness-banner decision)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3 — INCLUDING the explicit no-repository-py callout)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., catalog.list_products N+1 query under high product counts, search ILIKE missing pg_trgm index plan, profile-completeness banner becoming a daily-dismiss-fatigue UX, V1.5 amendment elevating dashboard to image/pricing/export composition forcing a rewrite, soft-delete-filter race when a delete commits during a paginated list query)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/tracking-dashboard/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/tracking-dashboard.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/tracking-dashboard/FEATURE_PLAN.md
git add docs/plans/features/_status/tracking-dashboard.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock tracking-dashboard feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-tracking-dashboard-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/tracking-dashboard/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/tracking-dashboard/planning \
  --title "docs(plan): lock tracking-dashboard feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update tracking-dashboard status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md (including profile-completeness-banner Decision 1 resolution)
- [ ] Agent lineup table fully filled out (backend 2 + frontend 2 specialists named; AI / data / infra explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify (INCLUDING the explicit NO-repository-py rule)
- [ ] Documentation deliverables enumerated (OpenAPI with banner sub-shape, no-repo structural docstring, import_rules.toml allowlist entry, V1_FEATURE_SPEC §F8 implemented stamp)
- [ ] One dispatch template per specialist drafted (4 templates total)
- [ ] Review + iteration protocol defined (with NO-repository / direct-DB-access / P95 / search-debounce failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/tracking-dashboard/planning
- [ ] PR opened to develop using backend PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/dashboard/, frontend/src/app/pages/dashboard/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-tracking-dashboard-{group}-session-{N}` per master plan §4
- The NO-repository.py structural exception is the architectural distinctive — any dispatch template that allows repository creation must be rejected (it violates §13.D and memory turn 20)
- Dashboard is read-only — any dispatch template that allows writes to any table must be rejected (writes happen in catalog module via DELETE /products/{id}; dashboard only lists)
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend) has reviewed their section's dispatch templates
- [ ] PR open to develop using the backend PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The NO-repository.py and read-only invariants are non-negotiable per §13.D

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
