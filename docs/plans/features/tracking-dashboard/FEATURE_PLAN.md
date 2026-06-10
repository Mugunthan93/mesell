# Tracking Dashboard — Feature Plan

**Status:** LOCKED — 2026-06-10
**Session:** `mesell-tracking-dashboard-planning-session-1`
**Output branch:** `feature/tracking-dashboard/planning` (SHA at plan authoring: `9a2b25c`)
**Operative spec:** `docs/BACKEND_ARCHITECTURE.md` §13, as amended by §13.A.1 (2026-06-07)
**Version:** 1.0 — Initial lock

---

## Table of Contents

1. [Status Preamble](#1-status-preamble)
   - 1.1 Pre-flight Reality Check
2. [Decisions (locked 2026-06-10)](#2-decisions-locked-2026-06-10)
   - 2.1 Operational Decisions
   - 2.2 Scope Decisions
3. [Code Surfaces](#3-code-surfaces)
   - 3.1 Backend
   - 3.2 Frontend
   - 3.3 AI (NONE)
   - 3.4 Data (NONE)
   - 3.5 Infra (NONE)
   - 3.6 Cross-cutting Docs
4. [Agent Lineup](#4-agent-lineup)
5. [Documentation Deliverables](#5-documentation-deliverables)
   - 5.1 Backend Documentation
   - 5.2 Frontend Documentation
   - 5.3 Cross-cutting Documentation
6. [Common Dispatch Template Preamble](#6-common-dispatch-template-preamble)
7. [Dispatch Templates](#7-dispatch-templates)
   - 7.1 `meesell-services-builder`
   - 7.2 `meesell-api-routes-builder`
   - 7.3 `meesell-angular-component-builder`
   - 7.4 `meesell-angular-service-builder`
8. [Review and Iteration Protocol](#8-review-and-iteration-protocol)
   - 8.1 Backend Review
   - 8.2 Frontend Review
   - 8.3 Re-dispatch Triggers
   - 8.4 Iteration Limit
9. [Acceptance Gate](#9-acceptance-gate)
10. [Risk Register](#10-risk-register)
11. [Revision History](#11-revision-history)

---

## 1. Status Preamble

### 1.1 Pre-flight Reality Check

Five reconciliations between `PLANNING_DISPATCH.md` and the operative `BACKEND_ARCHITECTURE.md §13.A.1` amendment (dated 2026-06-07). Decision D-D below is the authority resolution.

| # | PLANNING_DISPATCH.md stated | §13.A.1 operative (supersedes) |
|---|---|---|
| 1 | `status_filter` and `search` query params in scope for V1 | Both DEFERRED to V1.5. V1 `DashboardQuery` contains only `page` and `limit`. |
| 2 | Status enum `["draft", "ready", "exported"]` (3 values) | Narrowed to `["draft", "ready"]` for V1. "exported" and "live" defer to V1.5. |
| 3 | Method name `customer.service.get_profile_completeness` | CORRECTED. The operative §8.C signature is `customer.service.get_onboarding_completeness(user_id)`. The dispatch brief used the wrong name. This document uses the correct name throughout. |
| 4 | `Pagination` dataclass defined inside `dashboard/domain.py` | For V1, dashboard imports `Pagination` directly from `catalog.domain` (the §13.A.1 amendment collapses it to `page` + `limit`, which equals the catalog shape). Dashboard does NOT redefine it. |
| 5 | §13.J unit test #1 covers 5 rejection cases | Narrowed to 3 cases: `page < 1`, `limit < 1`, `limit > 100`. Cases for `status_filter` invalid Literal and `search > 100 chars` drop alongside those deferred params. |

These reconciliations are consequential. Leads dispatching against this plan use only the §13.A.1 operative scope. Any specialist output that reintroduces the deferred params is a re-dispatch trigger per §8.3.

---

## 2. Decisions (locked 2026-06-10 — founder approval in `mesell-tracking-dashboard-planning-session-1`)

### 2.1 Operational Decisions

#### D-A — Agent Lineup

2 leads x 2 specialists each.

- **Backend lead:** `meesell-backend-coordinator` dispatches `meesell-api-routes-builder` + `meesell-services-builder`.
- **Frontend lead:** `meesell-frontend-coordinator` dispatches `meesell-angular-component-builder` + `meesell-angular-service-builder`.

AI / data / infra leads are EXPLICITLY OMITTED. Rationale:
- Dashboard is non-AI per `BACKEND_ARCHITECTURE.md §13` and `§13.H` (no Gemini call, no `ai_ops` invocation, no `meesell-prompt-engineer` participation).
- No schema changes per `§13.D` and `§13.L` (dashboard owns ZERO tables; the 13-table schema at head `f31c75438e61` is unchanged).
- No infra / secrets / bucket / manifest changes (dashboard is in-process read aggregation over existing surfaces).

The roster is founder-locked. Leads CANNOT add specialists later without a FEATURE_PLAN.md amendment and a new revision history entry.

#### D-B — Branch Lifecycle

```
feature/tracking-dashboard/planning
  └── Created by Director THIS SESSION off develop at SHA 9a2b25c.
      FEATURE_PLAN.md commits here. PR opens to develop using backend PR template.

feature/tracking-dashboard  (parent)
  └── Created by the FIRST lead to dispatch (backend lead per priority D4)
      off the develop tip AT DISPATCH TIME.
      Commit message: chore(feature): create parent branch for tracking-dashboard

feature/tracking-dashboard/backend
  └── Created by meesell-backend-coordinator at first specialist dispatch
      off feature/tracking-dashboard.
      Rebase cadence: daily against the parent.

feature/tracking-dashboard/frontend
  └── Created by meesell-frontend-coordinator at first specialist dispatch
      off feature/tracking-dashboard.
      Rebase cadence: daily against the parent.
```

This matches `docs/plans/repo_management/MASTER_PLAN.md §1.2` (branches created when first group is about to start work, not speculatively).

#### D-C — Memory and Awareness Protocol

Four-stage cadence to prevent multi-feature memory blur across sessions:

**Stage 1 — Pre-seed at FEATURE_PLAN.md merge:**
- Both leads add `tracking-dashboard PENDING + FEATURE_PLAN.md commit hash` entry to their own MEMORY.md.
- PENDING row added to `docs/status/feature_board_{backend|frontend}.md`.

**Stage 2 — At dispatch:**
- Lead's prompt cites FEATURE_PLAN.md commit hash + specialist's prior memory state.
- Specialist opens `feature=tracking-dashboard session=N OPEN` entry in their own MEMORY.md.

**Stage 3 — At session close:**
- Specialist appends `feature=tracking-dashboard session=N CLOSED` tagged entry.
- Lead reviews and appends matching entry.
- Board row flips to IN REVIEW.

**Stage 4 — At merge:**
- Lead appends MERGED entry.
- FEATURE_PLAN.md revision history (§11) appends if any contract changed.

Every memory line is tagged with `feature=tracking-dashboard session=N` enabling grep-based context recovery when a single agent works multiple features concurrently.

#### D-D — Operative Spec (§13.A.1 Amendment — 2026-06-07)

**The `BACKEND_ARCHITECTURE.md §13.A.1` amendment dated 2026-06-07 IS THE OPERATIVE V1 SCOPE AUTHORITY.** `PLANNING_DISPATCH.md` text is SUPERSEDED where it conflicts.

The amendment was triggered by a D3 founder escalation on `meesell-backend-construction-13-dashboard-1`. The specific changes locked by §13.A.1:

- `status_filter` query param — DEFERRED to V1.5.
- `search` query param — DEFERRED to V1.5.
- Status enum — reduced from `Literal["draft", "ready", "exported"]` to `Literal["draft", "ready"]`. "exported" and "live" defer to V1.5.
- Tooltip "Live status manually set, Meesho has no API" — DEFERRED to V1.5 (no "live" status in V1 enum).
- Method name is `customer.service.get_onboarding_completeness(user_id)` per `§8.C`. Any reference to `get_profile_completeness` is incorrect.
- Response payload key is `onboarding_completeness` with shape `{base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete: bool}` — counters plus a boolean flag, NOT a percentage.
- §13.J unit test #1 expects 3 rejection cases (`page < 1`, `limit < 1`, `limit > 100`) — NOT 5.
- `Pagination` is imported from `catalog.domain` — dashboard does NOT redefine it.

Nothing else in §13 is amended. The no-repository structural exception (§13.D), `InvalidPaginationError` (§13.G), zero-adapter constraint (§13.H), cross-cutting posture (§13.I), and extraction notes (§13.K) all stand verbatim.

V1.5 restoration path: the §13.A.1 amendment is lifted when a §10 catalog amendment extends `Pagination` + `list_products` + `list_paginated` with `status_filter` + `search` predicates.

### 2.2 Scope Decisions

#### D1 — Onboarding-Completeness Banner

YES — render at top of `/dashboard` when the API returns `onboarding_complete: false` on the `onboarding_completeness` object. Banner shows base and extension counter progress (for example "8 of 10 base docs complete · 2 of 3 extensions complete"). CTA routes to `/profile`. Dismissible with "remind me tomorrow" via `localStorage` timestamp (24-hour snooze). Key: `dashboard.banner.snoozed_until` (Unix timestamp in ms).

Frontend consumes the `onboarding_completeness` key already returned by the §13.B endpoint response — no backend change needed for the banner. Trigger is the boolean `onboarding_complete: false`, not a percentage threshold.

#### D2 — Status Badge Colors

Two-value V1 contract:

- `"draft"` → `bg-gray-100 text-gray-700` (Tailwind defaults)
- `"ready"` → `bg-blue-100 text-blue-700` (Tailwind defaults)

Reserves green slot for V1.5 "exported" status. `StatusBadgeComponent` MUST NOT include "exported" or "live" code paths in V1. The two-value contract is directly enforced by the §13.A.1 amendment narrowing `ProductListItem.status` to `Literal["draft", "ready"]`.

#### D3 — Feature Flag Posture

- Flag name: `FEATURE_TRACKING_DASHBOARD_ENABLED`
- Dev default: `true`
- Staging default: `true` after one founder UX review
- Production default: `true`
- Posture: kill-switch (NOT staged rollout)

When OFF: `GET /api/v1/products` returns 404 and the `/dashboard` route shows "Dashboard temporarily disabled" placeholder. Flag readable at the backend route guard and at the frontend route guard.

#### D4 — Priority Ordering

Ships AFTER `catalog-form` because it consumes `catalog.service.list_products` — depends on catalog's `list_products` / `list_paginated` signatures being stable and the catalog module construction PR having landed on `feature/catalog-form` (or merged to develop). Backend lead MUST NOT open `feature/tracking-dashboard` until catalog-form's backend PR has landed.

Ships IN PARALLEL with `smart-picker` + `live-preview` — no shared-file contention (dashboard is pure read aggregation over surfaces those features also only consume, not modify).

Early ship is actively encouraged: dashboard provides login-to-end-to-end smoke coverage for all downstream features that produce dashboard rows.

---

## 3. Code Surfaces

### 3.1 Backend (group: `backend`, lead: `meesell-backend-coordinator`)

Owner specialists as noted. All paths are relative to `backend/app/`.

| File | Status | Owner specialist | Rationale |
|---|---|---|---|
| `modules/dashboard/__init__.py` | NEW | `meesell-services-builder` | Module init; exposes service surface only per `§16.A`. Inline comment documents absence of `repository.py` as intentional §13.D structural exception. |
| `modules/dashboard/router.py` | NEW | `meesell-api-routes-builder` | `GET /api/v1/products` route handler per §13.B. Applies `@rate_limit(scope="dashboard_list", key="ip")` per §13.I. `Depends(get_current_user)` per §4.B. |
| `modules/dashboard/schemas.py` | NEW | `meesell-api-routes-builder` | Pydantic v2 `DashboardQuery` (2 fields: `page`, `limit`; per §13.A.1 amendment), `ProductListItem` (status `Literal["draft", "ready"]`), `ProfileCompletenessSummary`, `DashboardResponse` per §13.E. |
| `modules/dashboard/service.py` | NEW | `meesell-services-builder` | `async list_products_for_dashboard(user_id, query)` public surface + module-private `_compose_response(paginated, completeness)` pure function per §13.C. |
| `modules/dashboard/domain.py` | NEW | `meesell-services-builder` | Minimal domain types per §13.F. NO local `Pagination` dataclass — imports `catalog.domain.Pagination` directly per §13.A.1 amendment. |
| `modules/dashboard/exceptions.py` | NEW | `meesell-services-builder` | `InvalidPaginationError` only (subclasses `MeesellError`; `status_code=400`, `validation_message_id="validation.dashboard.invalid_pagination"`) per §13.G. |
| `app/modules/dashboard/repository.py` | **EXPLICITLY DOES NOT EXIST** | N/A — structural exception per §13.D + memory turn 20 | Dashboard owns ZERO tables and performs NO data access. There is no `repository.py` file in this module's subtree. `ls modules/dashboard/` NOT containing `repository.py` is the structural proof of §2.7 "purest modular monolith discipline." Any specialist that creates this file MUST be re-dispatched. |
| `app/i18n/messages_en.py` | MODIFY | `meesell-services-builder` | Add 1 new entry: `"validation.dashboard.invalid_pagination"` → English string per §13.I. |
| `backend/tests/modules/dashboard/test_pagination_validation.py` | NEW | `meesell-services-builder` | 3 rejection cases per §13.J #1 (amended by §13.A.1): `page=0`, `limit=0`, `limit=101`. |
| `backend/tests/modules/dashboard/test_response_composition.py` | NEW | `meesell-services-builder` | `_compose_response` unit test in isolation with mocked services per §13.J #2. |
| `backend/tests/modules/dashboard/test_empty_state_response.py` | NEW | `meesell-services-builder` | Empty inventory returns 200 with `products=[]`, not 404, per §13.J #3. |
| `backend/tests/integration/test_dashboard_list_full_flow.py` | NEW | `meesell-api-routes-builder` | End-to-end: sign up → create 5 products → `GET /api/v1/products` per §13.J integration #1. |
| `backend/tests/integration/test_dashboard_cross_tenant_isolation.py` | NEW | `meesell-api-routes-builder` | Two-user cross-tenant boundary test per §13.J integration #2. |

**Schema note (§13.A.1 amendment):** `ProductListItem.status` is `Literal["draft", "ready"]` — a 2-value enum, NOT 3. This is referenced here, in §7.1 (services-builder dispatch), in §7.3 (component-builder dispatch), and in §8.3 (re-dispatch triggers for 3-value enum landing).

**Import-linter note:** `backend/tests/lint/import_rules.toml` Contract 1.dashboard (line 329 in the file as of 2026-06-10) is ALREADY PRESENT and verified. It forbids `app.modules.dashboard` from importing any other module's `repository.py`. This contract structurally enforces the §13.D no-repository rule at CI level. See §5.3 cross-cutting docs.

### 3.2 Frontend (group: `frontend`, lead: `meesell-frontend-coordinator`)

All paths are relative to `frontend/src/app/`.

| File | Status | Owner specialist | Rationale |
|---|---|---|---|
| `features/dashboard/dashboard.component.ts` | NEW | `meesell-angular-component-builder` | Page component using `mee-table` with server-side pagination, OnPush, signals. |
| `features/dashboard/dashboard.component.spec.ts` | NEW | `meesell-angular-component-builder` | Component spec: OnPush + async pipe verified; mock service injection. |
| `features/dashboard/product-row.component.ts` | NEW | `meesell-angular-component-builder` | Per-row component, OnPush. Renders product name, status badge, created date, delete action. |
| `features/dashboard/status-badge.component.ts` | NEW | `meesell-angular-component-builder` | Two-color contract only: gray for "draft", blue for "ready". Uses `mee-badge` from `@mee/ui`. NO "exported" or "live" branches. |
| `features/dashboard/profile-completeness-banner.component.ts` | NEW | `meesell-angular-component-builder` | Top banner when `onboarding_complete: false`. Shows base + extension counters. CTA to `/profile`. Dismissible 24h snooze via `localStorage` key `dashboard.banner.snoozed_until`. |
| `features/dashboard/services/dashboard.service.ts` | NEW | `meesell-angular-service-builder` | `DashboardService.list(query: {page, limit})` wrapping `HttpClient GET /api/v1/products`. Returns `Observable<DashboardResponse>`. JWT attached via existing `auth.interceptor.ts`. |
| `features/dashboard/services/dashboard.service.spec.ts` | NEW | `meesell-angular-service-builder` | `HttpTestingController` unit test verifying JWT pass-through and response mapping. |
| `features/dashboard/models/dashboard.model.ts` | NEW | `meesell-angular-service-builder` | TypeScript interfaces mirroring `DashboardResponse`, `ProductListItem`, `ProfileCompletenessSummary`. Status typed as `'draft' | 'ready'` (2-value, per §13.A.1 amendment). |
| `app.routes.ts` | MODIFY | `meesell-angular-component-builder` | Register `/dashboard` route with `AuthGuard`, lazy-loading `DashboardComponent`. Route comment documents the feature. |

### 3.3 AI (NONE)

Dashboard is a non-AI feature per `BACKEND_ARCHITECTURE.md §13`, `§13.H`, and `§13.I`. No Gemini call, no `ai_ops` invocation, no prompt-engineer participation. `meesell-ai-coordinator` and all AI specialists are OMITTED from this feature.

### 3.4 Data (NONE)

No schema changes. Dashboard owns ZERO tables per `§13.D`. The 13-table schema at Alembic head `f31c75438e61` is unchanged. `meesell-database-builder` and `meesell-data-engineer` are OMITTED from this feature.

### 3.5 Infra (NONE)

No new Kubernetes manifests, no new secrets, no new GCS buckets, no new environment variables. `meesell-infra-builder` is OMITTED from this feature. The feature flag `FEATURE_TRACKING_DASHBOARD_ENABLED` is a runtime config value read from the existing `shared/config.py` `Settings` object — it is NOT a new secret or a new infra primitive.

### 3.6 Cross-cutting Docs

The following documentation changes accompany the merged feature PR — they are acceptance gate items, not optional:

| Doc | Change | Trigger |
|---|---|---|
| `docs/V1_FEATURE_SPEC.md §F8` | Add "implemented YYYY-MM-DD via PR #N" stamp at the top of the Feature 8 block. | Merge of `feature/tracking-dashboard` to develop. |
| `docs/BACKEND_ARCHITECTURE.md §13` sentinel | Flip status line from `LOCKED-on-paper` to `LOCKED-on-disk via PR #N` (recording the PR URL). This is the §13 sentinel flip. | Merge of `feature/tracking-dashboard/backend` to `feature/tracking-dashboard`. |
| `backend/tests/lint/import_rules.toml` Contract 1.dashboard | VERIFY present and passing (it is — see §3.1 note). Document verified-present status in the backend lead's PR description. | PR open for `feature/tracking-dashboard/backend`. |
| `docs/MEESELL_AGENT_REGISTRY.md` | Verify `dashboard` service surface entry matches the locked §13 public method `list_products_for_dashboard`. No new entry required if already present; add if missing. | Pre-merge review by backend lead. |

---

## 4. Agent Lineup

| Lead | Specialists dispatched | What each specialist owns |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-services-builder` | `dashboard/service.py` (public `list_products_for_dashboard` + private `_compose_response`), `dashboard/domain.py`, `dashboard/exceptions.py`, `dashboard/__init__.py`, `i18n/messages_en.py` entry, 3 unit tests (§13.J #1/2/3). |
| `meesell-backend-coordinator` | `meesell-api-routes-builder` | `dashboard/router.py`, `dashboard/schemas.py`, 2 integration tests (§13.J int #1/2). |
| `meesell-frontend-coordinator` | `meesell-angular-component-builder` | `DashboardComponent`, `ProductRowComponent`, `StatusBadgeComponent`, `ProfileCompletenessBanner`, `DashboardComponent` spec, `app.routes.ts` modification. |
| `meesell-frontend-coordinator` | `meesell-angular-service-builder` | `DashboardService`, `DashboardService` spec, `dashboard.model.ts` interfaces. |
| `meesell-ai-coordinator` | OMITTED | Non-AI feature per §13. No Gemini call, no prompt-engineer, no `ai_ops` usage. |
| `meesell-data-engineer` | OMITTED | No schema changes; dashboard owns zero tables per §13.D. |
| `meesell-infra-builder` | OMITTED | No manifest / secret / bucket changes. |

---

## 5. Documentation Deliverables

### 5.1 Backend Documentation

The following documentation MUST exist in merged code alongside implementations. Backend lead verifies each at PR review.

**OpenAPI entry for `GET /api/v1/products`:**
- Query parameters: `page: int (default 1, min 1)`, `limit: int (default 20, min 1, max 100)`. No `status_filter`. No `search`. (Per §13.A.1 amendment.)
- Response `200`: full `DashboardResponse` shape including the `onboarding_completeness` sub-object with keys `base_complete_count`, `base_total_count`, `extension_complete_count`, `extension_total_count`, `onboarding_complete`.
- Response `400`: `validation.dashboard.invalid_pagination` trigger conditions enumerated (3 cases per §13.A.1 amendment).
- Response `401`: missing or invalid JWT.

**Service method docstring on `list_products_for_dashboard`:**
- Documents the 2-call composition pattern (§13.C): first calls `catalog.service.list_products(user_id, Pagination(page, limit))` per §10.C, then calls `customer.service.get_onboarding_completeness(user_id)` per §8.C.
- Documents the NO-repository structural deviation per §13.D: "This service method owns no data access. All reads flow through consumed service interfaces. There is no `dashboard/repository.py`."
- Documents why the cache helper is NOT used: high per-user write churn from product PATCH operations would produce a hit rate too low to justify the plumbing per §13.I.

**Inline comment on `dashboard/__init__.py`:**
- Explains the intentional absence of `repository.py` for future auditors: "dashboard is the modular monolith's purest BFF module — it owns no tables and performs no direct data access. The absence of repository.py is structural per §13.D, not an omission."

### 5.2 Frontend Documentation

**Route comment in `app.routes.ts`:**
- Documents the `/dashboard` route as Feature 8 (Tracking Dashboard), auth-guarded, lazy-loaded from `features/dashboard`.

**`DashboardComponent` docstring:**
- Documents use of `mee-table` from `@mee/ui` for product listing with server-side pagination.
- Documents OnPush change detection + signals pattern for loading state.
- Documents the `ProfileCompletenessBanner` trigger: `onboarding_complete: false` boolean from `DashboardService.list()` response.

**`StatusBadgeComponent` docstring:**
- Documents the explicit 2-color V1 contract: gray = "draft", blue = "ready".
- Documents explicit V1.5 forward-reference: "V1.5 amendment will add green = 'exported' when §13.A.1 is lifted and the 3-value status enum is restored."

**`ProfileCompletenessBanner` docstring:**
- Documents the dismiss-and-remind-tomorrow UX: triggered on `onboarding_complete: false`. Dismiss writes Unix timestamp `Date.now() + 86400000` to `localStorage` key `dashboard.banner.snoozed_until`. On mount, checks if current time exceeds stored value before rendering.
- Documents that snooze is bounded (max 24h) — there is no "remind never" option by founder decision D1.

### 5.3 Cross-cutting Documentation

**`docs/V1_FEATURE_SPEC.md §F8` implemented stamp:**
- Format: `> Implemented: YYYY-MM-DD via PR #N (feature/tracking-dashboard → develop)`
- Written by the backend lead at merge time.

**`backend/tests/lint/import_rules.toml` Contract 1.dashboard verification:**
- `Contract 1.dashboard` is present at line 329 of the file as of 2026-06-10 and is passing in CI.
- Backend lead includes verification evidence in the PR description: "import_rules.toml Contract 1.dashboard verified present and CI-green."

**`docs/BACKEND_ARCHITECTURE.md §13` sentinel flip:**
- Backend lead records the PR link in the §13 status line when merging the backend branch.

---

## 6. Common Dispatch Template Preamble

All four dispatch templates in §7.1–7.4 open with the following boilerplate verbatim. The `{group}` and `{N}` placeholders are filled by the dispatching lead at dispatch time.

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

SESSION: mesell-tracking-dashboard-{group}-session-{N}

## Feature context
Feature: Tracking Dashboard (Feature 8 per docs/V1_FEATURE_SPEC.md)
Operative spec: docs/BACKEND_ARCHITECTURE.md §13, as amended by §13.A.1 (2026-06-07)
Feature plan: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md (commit hash: {FEATURE_PLAN_COMMIT_HASH})
Your session ordinal: {N} (increment each re-dispatch; start at 1)

## First action
Before writing a single line of production code:
1. Read your own MEMORY.md at .claude/agent-memory/meesell-{specialist-role}/MEMORY.md.
2. Open a memory entry: "feature=tracking-dashboard session={N} OPEN — {today's date}".
3. Confirm the operative spec is §13.A.1 (2026-06-07): status_filter and search are DEFERRED,
   status enum is ["draft", "ready"] only, Pagination is imported from catalog.domain.
4. Confirm the method name is get_onboarding_completeness (NOT get_profile_completeness).

## Session naming
This session's name follows docs/plans/repo_management/MASTER_PLAN.md §4 convention:
  mesell-tracking-dashboard-{group}-session-{N}
where {group} is "backend" or "frontend" and {N} is the dispatch ordinal starting at 1.
```

---

## 7. Dispatch Templates

### 7.1 `meesell-services-builder` (dispatched by `meesell-backend-coordinator`)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

SESSION: mesell-tracking-dashboard-backend-session-{N}

## Feature context
Feature: Tracking Dashboard (Feature 8 per docs/V1_FEATURE_SPEC.md)
Operative spec: docs/BACKEND_ARCHITECTURE.md §13, as amended by §13.A.1 (2026-06-07)
Feature plan: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md (commit hash: {FEATURE_PLAN_COMMIT_HASH})
Your session ordinal: {N} (increment each re-dispatch; start at 1)

## First action
Before writing a single line of production code:
1. Read your own MEMORY.md at .claude/agent-memory/meesell-services-builder/MEMORY.md.
2. Open a memory entry: "feature=tracking-dashboard session={N} OPEN — {today's date}".
3. Confirm the operative spec is §13.A.1 (2026-06-07): status_filter and search are DEFERRED,
   status enum is ["draft", "ready"] only, Pagination is imported from catalog.domain.
4. Confirm the method name is get_onboarding_completeness (NOT get_profile_completeness).

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §13 — full module spec for dashboard (STATUS: LOCKED, AMENDED 2026-06-07)
   - §13.A.1 — the operative amendment (filter/search deferred; status 2-value; Pagination from catalog)
   - §13.C — service layer: list_products_for_dashboard signature + _compose_response pure function
   - §13.D — NO repository.py structural exception (CRITICAL — read before writing a single file)
   - §13.E — schemas: DashboardQuery (2 fields only), ProductListItem (status Literal["draft","ready"]), DashboardResponse
   - §13.F — domain.py: NO local Pagination; imports catalog.domain.Pagination
   - §13.G — exceptions: InvalidPaginationError only
   - §13.H — adapter usage: NONE (no Gemini, no GCS, no MSG91, no Razorpay)
   - §13.I — cross-cutting: rate-limit per-IP only; NO plan_guard; NO audit; NO cache; NO AI
   - §13.J — test plan: 3 unit test classes (test_pagination_validation = 3 cases per amendment)
2. docs/BACKEND_ARCHITECTURE.md §10.C — catalog.service.list_products signature:
   async def list_products(user_id: UUID, pagination: Pagination) -> PaginatedProducts
   This is the EXACT signature you call. Do not modify it. Do not add parameters.
3. docs/BACKEND_ARCHITECTURE.md §8.C — customer.service.get_onboarding_completeness signature:
   async def get_onboarding_completeness(user_id: UUID) -> ProfileCompleteness
   This is the EXACT method name. NOT get_profile_completeness. NOT get_completeness.
4. docs/BACKEND_ARCHITECTURE.md §16 — inter-module communication rules (service-layer only; no
   cross-module repository imports; domain type imports are permitted per §13.F observation 2)
5. backend/tests/lint/import_rules.toml — read Contract 1.dashboard (line ~329) to understand
   the CI rule that will fail if your code imports any other module's repository

## Mission
Implement the business logic layer for the dashboard module.

### Files to create
- backend/app/modules/dashboard/__init__.py
  Exposes only the service surface per §16.A. Include inline comment:
  "dashboard is the modular monolith's purest BFF module — it owns no tables and performs
  no direct data access. The absence of repository.py is intentional per §13.D."

- backend/app/modules/dashboard/service.py
  Public method:
    async def list_products_for_dashboard(
        user_id: UUID,
        query: DashboardQuery,
    ) -> DashboardResponse:
        """
        Compose the dashboard view by aggregating catalog.list_products
        and customer.get_onboarding_completeness for the requesting seller.
        Owns no data access; pure delegation + composition.

        Composition pattern (§13.C):
        1. Call catalog.service.list_products(user_id, Pagination(query.page, query.limit))
           per §10.C. Returns PaginatedProducts with product rows and pagination meta.
           scope_to_user(user_id) is enforced at catalog's repository layer — dashboard
           never sees a raw SQL query.
        2. Call customer.service.get_onboarding_completeness(user_id) per §8.C.
           Returns ProfileCompleteness with base/extension counts and onboarding_complete flag.
           scope_to_user(user_id) is enforced at customer's repository layer.
        3. Call _compose_response(paginated, completeness) to build DashboardResponse.

        No side effects. No data writes. No cache usage (high write churn per §13.I).
        No adapter calls (zero egress per §13.H — this is why P95 <= 200ms is achievable).
        """

  Module-private helper (same file or private _compose.py):
    def _compose_response(
        paginated: PaginatedProducts,
        completeness: ProfileCompleteness,
    ) -> DashboardResponse:
        """
        Pure function. Maps catalog.PaginatedProducts + customer.ProfileCompleteness
        into the wire-shaped DashboardResponse. No I/O. No side effects.
        Unit-tested in isolation per §13.J.

        Status mapping: ProductListItem.status is Literal["draft", "ready"] in V1 per §13.A.1
        amendment (2026-06-07). Do NOT add "exported" or any other status value here.
        """

- backend/app/modules/dashboard/domain.py
  Minimal domain types per §13.F. Do NOT define a local Pagination dataclass.
  Import Pagination from catalog.domain:
    from app.modules.catalog.domain import Pagination
  This is permitted per §13.F observation 2: domain-type imports across modules are
  first-class as long as no repository-layer call crosses the boundary.

- backend/app/modules/dashboard/exceptions.py
  One exception class only per §13.G:
    class InvalidPaginationError(DashboardError):
        status_code = 400
        validation_message_id = "validation.dashboard.invalid_pagination"

- backend/app/i18n/messages_en.py  (MODIFY — add one entry)
  Add: "validation.dashboard.invalid_pagination": "Page must be >= 1 and limit must be between 1 and 100."
  (Or equivalent English string; you own the copy, the ID is locked.)

### Tests to create
- backend/tests/modules/dashboard/test_pagination_validation.py
  Covers DashboardQuery Pydantic rejection paths (3 cases per §13.A.1 amendment):
  - page=0 → 400 validation.dashboard.invalid_pagination
  - limit=0 → 400
  - limit=101 → 400
  All happy-path defaults verified (page=1, limit=20, status_filter omitted, search omitted).
  DO NOT test status_filter rejection — that param does not exist in V1 per §13.A.1.
  DO NOT test search rejection — that param does not exist in V1 per §13.A.1.

- backend/tests/modules/dashboard/test_response_composition.py
  Tests _compose_response in isolation with mocked services:
  - Mocked catalog.list_products returns 3 products + total=42.
  - Mocked customer.get_onboarding_completeness returns specific counts.
  - Verify DashboardResponse.products has 3 items, total=42, page and limit echo the request,
    and onboarding_completeness mirrors the mocked completeness shape.

- backend/tests/modules/dashboard/test_empty_state_response.py
  Boundary case for first-time sellers:
  - Mocked catalog.list_products returns empty list + total=0.
  - Dashboard returns 200 with products=[] and total=0 (NOT 404 — empty inventory is valid).
  - onboarding_completeness still surfaces (the seller still has a profile).

## Acceptance criteria
- P95 latency <= 200ms measured against a 100-row product seed per §13.H zero-egress budget.
  Verify by running the integration test with timing assertions or by inspecting test logs.
- _compose_response is a pure function: no I/O, no side effects, no global state mutations.
- Unit tests pass: 3 cases in test_pagination_validation, response composition, empty state.
- No repository.py file exists under backend/app/modules/dashboard/ — verify with ls.
- catalog.service and customer.service are the ONLY modules imported in dashboard/service.py —
  verify by grepping for "from app.modules" in service.py.
- import-linter Contract 1.dashboard passes: run lint-imports from backend/ directory.
- i18n entry validation.dashboard.invalid_pagination present in messages_en.py.

## Hard constraints (NON-NEGOTIABLE)
- DO NOT create backend/app/modules/dashboard/repository.py. This file MUST NOT EXIST.
  §13.D documents the absence as intentional structural design. Creating it violates the
  modular monolith discipline and will trigger an immediate re-dispatch.
- DO NOT inject AsyncSession into dashboard/service.py. Dashboard performs zero DB access.
  All data flows through catalog.service + customer.service.
- DO NOT add status_filter or search parameters anywhere in the dashboard module. Both are
  deferred to V1.5 per §13.A.1 amendment. The DashboardQuery has exactly 2 fields: page, limit.
- DO NOT use Literal["draft", "ready", "exported"] — status is 2-value only per §13.A.1.
  Use Literal["draft", "ready"].
- DO NOT add cache helper participation. Per §13.I: high write churn from product PATCH
  operations would tank the hit rate. cache.py is not imported by dashboard.
- DO NOT add plan_guard participation. Per §13.I: dashboard is one of 3 modules excluded
  from plan_guard (alongside customer and pricing).
- DO NOT emit audit events. Per §13.I: read-only endpoint; audit_mw skips GET requests.
- DO NOT call any adapter (gemini, msg91, gcs, razorpay, langfuse). Dashboard has zero egress.
- DO NOT add a tasks.py file. Dashboard has no background jobs.
- DO NOT write to any table, any column, any row. Dashboard is strictly read-only.
- Method name is get_onboarding_completeness — NOT get_profile_completeness.
- Pagination is imported from catalog.domain — NOT redefined in dashboard.

## Files you MAY touch
- backend/app/modules/dashboard/__init__.py (NEW)
- backend/app/modules/dashboard/service.py (NEW)
- backend/app/modules/dashboard/domain.py (NEW)
- backend/app/modules/dashboard/exceptions.py (NEW)
- backend/app/i18n/messages_en.py (MODIFY — add 1 entry)
- backend/tests/modules/dashboard/test_pagination_validation.py (NEW)
- backend/tests/modules/dashboard/test_response_composition.py (NEW)
- backend/tests/modules/dashboard/test_empty_state_response.py (NEW)

## Files you MUST NOT touch
- backend/app/modules/dashboard/router.py (owned by meesell-api-routes-builder)
- backend/app/modules/dashboard/schemas.py (owned by meesell-api-routes-builder)
- backend/app/modules/dashboard/repository.py — THIS FILE MUST NOT BE CREATED
- Any file under backend/app/modules/catalog/ (do not modify catalog's service or domain)
- Any file under backend/app/modules/customer/ (do not modify customer's service or domain)
- Any file under backend/app/shared/ (do not modify shared models or database)
- Any file under backend/app/core/ (do not modify auth, cache, plan_guard, middleware)
- Any file under frontend/ (backend specialist only)
- docs/ (do not modify documentation — that is the lead's job at merge time)

## Final report format
After completing all tasks, produce a report with exactly these sections:

### Session close report — mesell-tracking-dashboard-backend-session-{N}
1. Files created: list each file path
2. Tests: [PASS/FAIL] for each test file, with pass count
3. P95 latency measurement: [value]ms against 100-row seed (or: "measured at integration test runtime")
4. import-linter Contract 1.dashboard: [PASS/FAIL]
5. ls backend/app/modules/dashboard/ output (must NOT include repository.py)
6. grep result: "from app.modules" in service.py (must show only catalog and customer)
7. Status enum verification: ProductListItem.status = Literal["draft", "ready"] confirmed
8. Memory entry: "feature=tracking-dashboard session={N} CLOSED — {date}" appended to MEMORY.md
9. Any deviation from the plan: [NONE or description]
```

---

### 7.2 `meesell-api-routes-builder` (dispatched by `meesell-backend-coordinator`)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

SESSION: mesell-tracking-dashboard-backend-session-{N}

## Feature context
Feature: Tracking Dashboard (Feature 8 per docs/V1_FEATURE_SPEC.md)
Operative spec: docs/BACKEND_ARCHITECTURE.md §13, as amended by §13.A.1 (2026-06-07)
Feature plan: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md (commit hash: {FEATURE_PLAN_COMMIT_HASH})
Your session ordinal: {N} (increment each re-dispatch; start at 1)

## First action
Before writing a single line of production code:
1. Read your own MEMORY.md at .claude/agent-memory/meesell-api-routes-builder/MEMORY.md.
2. Open a memory entry: "feature=tracking-dashboard session={N} OPEN — {today's date}".
3. Confirm the operative spec is §13.A.1 (2026-06-07): status_filter and search DEFERRED,
   status enum is ["draft", "ready"] only, DashboardQuery has exactly 2 fields.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §13.B — endpoint surface for GET /api/v1/products
   - §13.B.1 — query parameters (V1: page, limit ONLY — no status_filter, no search)
   - §13.B.1 — response 200 shape (DashboardResponse per §13.E)
   - §13.B.1 — status codes: 200, 400 (3 trigger cases per §13.A.1), 401
   - §13.B.1 — rate limit: @rate_limit(scope="dashboard_list", key="ip")
   - §13.B.1 — plan guard: NOT participating
   - §13.B.1 — JWT: Depends(get_current_user) per §4.B
2. docs/BACKEND_ARCHITECTURE.md §13.E — Pydantic v2 schemas:
   - DashboardQuery: page (ge=1, default=1), limit (ge=1, le=100, default=20)
     DO NOT add status_filter or search fields.
   - ProductListItem.status: Literal["draft", "ready"] — 2 values only per §13.A.1
   - ProfileCompletenessSummary shape
   - DashboardResponse shape
3. docs/BACKEND_ARCHITECTURE.md §13.G — InvalidPaginationError:
   status_code=400, validation_message_id="validation.dashboard.invalid_pagination"
4. docs/BACKEND_ARCHITECTURE.md §4.B — get_current_user dependency contract
5. docs/BACKEND_ARCHITECTURE.md §15 — rate_limit decorator usage pattern

## Mission
Implement the HTTP boundary layer for the dashboard module.

### Files to create
- backend/app/modules/dashboard/schemas.py
  Pydantic v2 models per §13.E, with §13.A.1 amendment applied:

    class DashboardQuery(BaseModel):
        page: int = Field(default=1, ge=1)
        limit: int = Field(default=20, ge=1, le=100)
        # NO status_filter field — deferred to V1.5 per §13.A.1
        # NO search field — deferred to V1.5 per §13.A.1

    class ProductListItem(BaseModel):
        product_id: UUID
        name: str | None
        category_id: UUID
        status: Literal["draft", "ready"]  # 2-value only per §13.A.1 amendment
        created_at: datetime
        updated_at: datetime

    class ProfileCompletenessSummary(BaseModel):
        base_complete_count: int
        base_total_count: int
        extension_complete_count: int
        extension_total_count: int
        onboarding_complete: bool

    class DashboardResponse(BaseModel):
        products: list[ProductListItem]
        total: int
        page: int
        limit: int
        onboarding_completeness: ProfileCompletenessSummary

- backend/app/modules/dashboard/router.py
  One route only per §13.B:

    router = APIRouter(prefix="/api/v1", tags=["dashboard"])

    @router.get("/products", response_model=DashboardResponse)
    @rate_limit(scope="dashboard_list", key="ip")
    async def list_products(
        query: DashboardQuery = Depends(),
        user: CurrentUser = Depends(get_current_user),
        service: DashboardService = Depends(),
    ) -> DashboardResponse:
        return await service.list_products_for_dashboard(user.user_id, query)

  Important notes:
  - NO status_filter query param. NO search query param.
  - NO plan_guard decorator.
  - NO audit emission (read-only endpoint per §13.I).
  - Rate limit key="ip" only — not per-user per §13.I.
  - InvalidPaginationError is raised by Pydantic DashboardQuery validation before the handler
    runs; the §4.F error handler chain renders it as 400 with the message ID.

### Tests to create
- backend/tests/integration/test_dashboard_list_full_flow.py
  End-to-end integration test per §13.J integration #1:
  - Seller signs up via iam (POST /otp/send + POST /otp/verify) → JWT.
  - Seller creates 5 products via catalog (POST /products x 5).
  - Seller calls GET /api/v1/products?page=1&limit=20 with JWT.
  - Response: 200, products length 5, total=5, onboarding_completeness present.

- backend/tests/integration/test_dashboard_cross_tenant_isolation.py
  Cross-tenant test per §13.J integration #2:
  - User A has 3 products, User B has 2 products.
  - User A GET /products returns only A's 3 + total=3.
  - User B GET /products returns only B's 2 + total=2.
  - Verifies scope_to_user is enforced end-to-end through dashboard.

## Acceptance criteria
- GET /api/v1/products?page=1&limit=20 returns 200 with valid DashboardResponse shape.
- GET /api/v1/products?page=0 returns 400 with validation.dashboard.invalid_pagination.
- GET /api/v1/products?limit=0 returns 400 with validation.dashboard.invalid_pagination.
- GET /api/v1/products?limit=101 returns 400 with validation.dashboard.invalid_pagination.
- GET /api/v1/products with missing JWT returns 401.
- DashboardQuery has exactly 2 fields (page, limit) — verified by schema inspection.
- ProductListItem.status is Literal["draft", "ready"] — 2 values, not 3.
- Both integration tests pass against a seeded DB.

## Hard constraints (NON-NEGOTIABLE)
- DO NOT add status_filter query param to DashboardQuery or the route. Deferred to V1.5.
- DO NOT add search query param to DashboardQuery or the route. Deferred to V1.5.
- DO NOT add plan_guard decorator to the route. Dashboard is plan_guard-excluded per §13.I.
- DO NOT emit audit events. Read-only endpoint; audit_mw handles this by default.
- DO NOT add any POST, PUT, PATCH, or DELETE endpoint under dashboard. Dashboard is read-only.
- DO NOT use Literal["draft", "ready", "exported"]. Status is 2-value only per §13.A.1.
- DO NOT create backend/app/modules/dashboard/repository.py. That file must not exist.
- DO NOT modify catalog or customer modules. Dashboard only consumes their service surfaces.

## Files you MAY touch
- backend/app/modules/dashboard/schemas.py (NEW)
- backend/app/modules/dashboard/router.py (NEW)
- backend/tests/integration/test_dashboard_list_full_flow.py (NEW)
- backend/tests/integration/test_dashboard_cross_tenant_isolation.py (NEW)

## Files you MUST NOT touch
- backend/app/modules/dashboard/service.py (owned by meesell-services-builder)
- backend/app/modules/dashboard/domain.py (owned by meesell-services-builder)
- backend/app/modules/dashboard/exceptions.py (owned by meesell-services-builder)
- backend/app/modules/dashboard/__init__.py (owned by meesell-services-builder)
- backend/app/modules/dashboard/repository.py — THIS FILE MUST NOT BE CREATED
- Any file under backend/app/modules/catalog/
- Any file under backend/app/modules/customer/
- Any file under frontend/
- docs/ (documentation is the lead's job at merge time)

## Final report format
After completing all tasks, produce a report with exactly these sections:

### Session close report — mesell-tracking-dashboard-backend-session-{N}
1. Files created: list each file path
2. Tests: [PASS/FAIL] for each test file, with pass count
3. DashboardQuery field count: [N] fields (must be 2: page, limit)
4. ProductListItem.status type: [value] (must be Literal["draft", "ready"])
5. OpenAPI entry for GET /api/v1/products: [confirmed present / not yet generated]
6. 400 trigger coverage: page<1 [PASS/FAIL], limit<1 [PASS/FAIL], limit>101 [PASS/FAIL]
7. 401 coverage: missing JWT [PASS/FAIL]
8. Integration test results: full_flow [PASS/FAIL], cross_tenant [PASS/FAIL]
9. Memory entry: "feature=tracking-dashboard session={N} CLOSED — {date}" appended to MEMORY.md
10. Any deviation from the plan: [NONE or description]
```

---

### 7.3 `meesell-angular-component-builder` (dispatched by `meesell-frontend-coordinator`)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

SESSION: mesell-tracking-dashboard-frontend-session-{N}

## Feature context
Feature: Tracking Dashboard (Feature 8 per docs/V1_FEATURE_SPEC.md)
Operative spec: docs/BACKEND_ARCHITECTURE.md §13, as amended by §13.A.1 (2026-06-07)
Feature plan: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md (commit hash: {FEATURE_PLAN_COMMIT_HASH})
Your session ordinal: {N} (increment each re-dispatch; start at 1)

## First action
Before writing a single line of production code:
1. Read your own MEMORY.md at .claude/agent-memory/meesell-angular-component-builder/MEMORY.md.
2. Open a memory entry: "feature=tracking-dashboard session={N} OPEN — {today's date}".
3. Confirm: StatusBadgeComponent has exactly 2 branches — "draft" (gray) and "ready" (blue).
   "exported" and "live" are NOT valid status values in V1 per §13.A.1 amendment.
4. Confirm: ProfileCompletenessBanner trigger is onboarding_complete: false (boolean), NOT
   a percentage threshold.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md — full architecture including 4-layer pattern:
   - Layer 2: src/app/ui/ — mee-table, mee-badge, mee-dialog, mee-button, mee-skeleton
   - Layer 3: src/app/shared/ — mee-status-badge (verify if exists; if not, StatusBadgeComponent
     belongs in features/dashboard/ per the feature-owns-it rule)
   - Layer 4: src/app/features/ — dashboard/ is the target directory
   - Non-negotiable rules: OnPush everywhere, signals for local state, no direct PrimeNG imports
2. CLAUDE.md — Angular 21, OnPush, standalone components, Tailwind CSS + PrimeNG via mee-* wrappers
3. docs/BACKEND_ARCHITECTURE.md §13.B.1 — DashboardResponse wire shape:
   - products: list of {product_id, name, category_id, status, created_at, updated_at}
   - status: Literal["draft", "ready"] — 2 values ONLY per §13.A.1
   - onboarding_completeness: {base_complete_count, base_total_count,
     extension_complete_count, extension_total_count, onboarding_complete: bool}
4. docs/plans/features/tracking-dashboard/FEATURE_PLAN.md §2.2 D1 (banner) + D2 (badge colors) + D4 (priority)

## Mission
Implement the Angular component layer for the dashboard feature.

### Files to create

backend/app/modules/dashboard/         ← DO NOT TOUCH (backend only)

frontend/src/app/features/dashboard/dashboard.component.ts
  Page component. Standalone, OnPush.
  - Uses mee-table from @mee/ui with server-side pagination.
  - Columns: product name, status badge, created date, actions (delete).
  - Page-size selector: 20 / 50 / 100 per §13.B pagination contract.
  - Loading state via mee-skeleton from @mee/ui.
  - Injects DashboardService (from meesell-angular-service-builder dispatch).
  - Uses signals: loading = signal(false); products = signal([]); pagination signals.
  - Empty state: "Create your first catalog" CTA routes to /catalogs/new when products = [].
  - Renders ProfileCompletenessBanner above the table when onboarding_complete === false
    AND the 24h snooze has expired (or was never set).
  - Docstring: documents mee-table + OnPush + banner trigger logic.

frontend/src/app/features/dashboard/dashboard.component.spec.ts
  Component spec:
  - Verifies OnPush change detection strategy is set.
  - Verifies async service call result renders product rows.
  - Mocks DashboardService.
  - Verifies banner renders when onboarding_complete === false.
  - Verifies banner does NOT render when snooze is active (mock localStorage).

frontend/src/app/features/dashboard/product-row.component.ts
  Per-row sub-component. Standalone, OnPush.
  - Input: product: ProductListItem
  - Output: deleteRequested = new EventEmitter<string>() (emits product_id)
  - Renders: product name, StatusBadgeComponent, created date (formatted), delete icon button.
  - Delete action opens mee-dialog confirm from @mee/ui; on confirm emits deleteRequested.
  - Keyboard-accessible confirm dialog.

frontend/src/app/features/dashboard/status-badge.component.ts
  Status badge sub-component. Standalone, OnPush.
  - Input: status: 'draft' | 'ready'
  - Renders mee-badge from @mee/ui with:
    - 'draft': severity='neutral', label='Draft', Tailwind: bg-gray-100 text-gray-700
    - 'ready': severity='info', label='Ready', Tailwind: bg-blue-100 text-blue-700
  - DO NOT add any 'exported', 'live', or third branch. 2-value contract per §13.A.1.
  - Docstring MUST include: "V1: 2-color contract (draft=gray, ready=blue).
    V1.5 forward: green='exported' when §13.A.1 is lifted."

frontend/src/app/features/dashboard/profile-completeness-banner.component.ts
  Profile completeness banner. Standalone, OnPush.
  - Input: completeness: ProfileCompletenessSummary
  - Output: dismissed = new EventEmitter<void>()
  - Renders only when: completeness.onboarding_complete === false
    AND (no snoozed_until in localStorage OR Date.now() > snoozed_until value)
  - Content: "X of Y base docs complete · A of B extensions complete"
    where X = base_complete_count, Y = base_total_count, A = extension_complete_count,
    B = extension_total_count
  - CTA "Complete Profile" button routes to /profile.
  - "Remind me tomorrow" button: writes Date.now() + 86400000 to
    localStorage key "dashboard.banner.snoozed_until", then emits dismissed.
  - Docstring documents the localStorage key shape, 24h snooze, and the boolean trigger
    (NOT a percentage).

### app.routes.ts modification
  Add /dashboard route with AuthGuard and lazy loadComponent:
    {
      path: 'dashboard',
      canActivate: [AuthGuard],
      // Feature 8: Tracking Dashboard — seller's product status overview
      loadComponent: () =>
        import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    }

## Acceptance criteria
- Angular build completes without errors: ng build.
- All component specs pass: ng test.
- OnPush detected on every new component: verify in spec.
- StatusBadgeComponent: exactly 2 status branches (draft, ready). No "exported". No "live".
- ProfileCompletenessBanner: triggered by onboarding_complete === false boolean (not percentage).
- Banner localStorage key is exactly "dashboard.banner.snoozed_until".
- Banner 24h snooze: dismiss writes Date.now() + 86400000.
- Soft-delete confirm dialog is keyboard-accessible (Tab + Enter confirms).
- Empty state CTA routes to /catalogs/new.
- Screenshots attached at 360px and 1280px viewport widths.
- No direct PrimeNG imports in any feature file (import from @mee/ui only).

## Hard constraints (NON-NEGOTIABLE)
- DO NOT add a filter dropdown. Filter is deferred to V1.5 per §13.A.1.
- DO NOT add a search input. Search is deferred to V1.5 per §13.A.1.
- DO NOT add "exported" or "live" status branches in StatusBadgeComponent. 2-value only.
- DO NOT use Literal["exported"] or Literal["live"] in any TypeScript interface.
- DO NOT trigger the banner on a percentage. Trigger is the boolean onboarding_complete: false.
- DO NOT import from 'primeng/...' in any feature file. Use @mee/ui wrappers.
- DO NOT use NgModules. All components are standalone: true.
- DO NOT use subscribe() in templates. Use async pipe or signals.
- DO NOT add BehaviorSubject for component state. Use signal() per architecture rule.
- All components MUST have changeDetection: ChangeDetectionStrategy.OnPush.

## Files you MAY touch
- frontend/src/app/features/dashboard/dashboard.component.ts (NEW)
- frontend/src/app/features/dashboard/dashboard.component.spec.ts (NEW)
- frontend/src/app/features/dashboard/product-row.component.ts (NEW)
- frontend/src/app/features/dashboard/status-badge.component.ts (NEW)
- frontend/src/app/features/dashboard/profile-completeness-banner.component.ts (NEW)
- frontend/src/app/app.routes.ts (MODIFY — add /dashboard route)

## Files you MUST NOT touch
- frontend/src/app/features/dashboard/services/ (owned by meesell-angular-service-builder)
- frontend/src/app/features/dashboard/models/ (owned by meesell-angular-service-builder)
- frontend/src/app/ui/ (UI kit — do not modify primitives)
- frontend/src/app/shared/ (shared composites — do not modify)
- frontend/src/app/core/ (guards, interceptors — do not modify)
- Any file under backend/
- docs/

## Final report format
After completing all tasks, produce a report with exactly these sections:

### Session close report — mesell-tracking-dashboard-frontend-session-{N}
1. Files created/modified: list each file path
2. Build: ng build [PASS/FAIL]
3. Tests: ng test [PASS count / FAIL count]
4. OnPush verification: [confirmed on all N new components]
5. StatusBadgeComponent branch count: [N] (must be 2)
6. Banner trigger: [onboarding_complete boolean / confirmed]
7. localStorage key: [value] (must be "dashboard.banner.snoozed_until")
8. Screenshots: 360px [attached/not attached], 1280px [attached/not attached]
9. PrimeNG direct imports: [NONE / list any found]
10. Memory entry: "feature=tracking-dashboard session={N} CLOSED — {date}" appended to MEMORY.md
11. Any deviation from the plan: [NONE or description]
```

---

### 7.4 `meesell-angular-service-builder` (dispatched by `meesell-frontend-coordinator`)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

SESSION: mesell-tracking-dashboard-frontend-session-{N}

## Feature context
Feature: Tracking Dashboard (Feature 8 per docs/V1_FEATURE_SPEC.md)
Operative spec: docs/BACKEND_ARCHITECTURE.md §13, as amended by §13.A.1 (2026-06-07)
Feature plan: docs/plans/features/tracking-dashboard/FEATURE_PLAN.md (commit hash: {FEATURE_PLAN_COMMIT_HASH})
Your session ordinal: {N} (increment each re-dispatch; start at 1)

## First action
Before writing a single line of production code:
1. Read your own MEMORY.md at .claude/agent-memory/meesell-angular-service-builder/MEMORY.md.
2. Open a memory entry: "feature=tracking-dashboard session={N} OPEN — {today's date}".
3. Confirm: DashboardService.list() takes only {page, limit} — no search, no filter params.
4. Confirm: DashboardResponse.products[].status is 'draft' | 'ready' only (2-value).

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §13.B.1 — GET /api/v1/products contract:
   - Query: page (int, default 1), limit (int, default 20, max 100)
   - Response 200: DashboardResponse shape (products, total, page, limit, onboarding_completeness)
   - No status_filter. No search. Per §13.A.1 amendment.
2. docs/FRONTEND_ARCHITECTURE.md — architecture rules:
   - Layer 4 features import from @mee/ui, @mee/shared, and their own services/models
   - HTTP: Angular HttpClient with jwt.interceptor passing Bearer token
   - State: signals for component state, RxJS for HTTP calls
3. CLAUDE.md — Angular 21 patterns: HttpClient, interceptors, strict TypeScript

## Mission
Implement the HTTP service layer and TypeScript models for the dashboard feature.

### Files to create

frontend/src/app/features/dashboard/models/dashboard.model.ts
  TypeScript interfaces mirroring the backend wire shape from §13.B.1:

    export interface ProfileCompletenessSummary {
      base_complete_count: number;
      base_total_count: number;
      extension_complete_count: number;
      extension_total_count: number;
      onboarding_complete: boolean;
    }

    export interface ProductListItem {
      product_id: string;    // UUID
      name: string | null;
      category_id: string;   // UUID
      status: 'draft' | 'ready';  // 2-value ONLY per §13.A.1 — DO NOT add 'exported'
      created_at: string;    // ISO8601
      updated_at: string;    // ISO8601
    }

    export interface DashboardResponse {
      products: ProductListItem[];
      total: number;
      page: number;
      limit: number;
      onboarding_completeness: ProfileCompletenessSummary;
    }

    export interface DashboardQuery {
      page: number;
      limit: number;
      // NO search field — deferred to V1.5
      // NO status_filter field — deferred to V1.5
    }

frontend/src/app/features/dashboard/services/dashboard.service.ts
  Angular service. Injectable at root.

    @Injectable({ providedIn: 'root' })
    export class DashboardService {
      private readonly http = inject(HttpClient);

      list(query: DashboardQuery): Observable<DashboardResponse> {
        /**
         * Fetch the paginated product listing for the current seller.
         * JWT is attached by auth.interceptor.ts automatically.
         * query supports only {page, limit} in V1 — filter and search are
         * deferred to V1.5 per §13.A.1 amendment.
         */
        const params = new HttpParams()
          .set('page', query.page.toString())
          .set('limit', query.limit.toString());
        return this.http.get<DashboardResponse>('/api/v1/products', { params });
      }
    }

  Notes:
  - DO NOT add a debounced search observable — search is deferred.
  - DO NOT add a filter param — filter is deferred.
  - DO NOT add write methods — dashboard is read-only.
  - JWT is passed automatically via the existing auth.interceptor.ts registered in app.config.ts.
    Do NOT re-implement JWT attachment in this service.

frontend/src/app/features/dashboard/services/dashboard.service.spec.ts
  Unit test using HttpTestingController:
  - Test: list({page: 1, limit: 20}) sends GET /api/v1/products?page=1&limit=20
  - Test: JWT Authorization header is present on the request (verify via the interceptor)
  - Test: 200 response is mapped to DashboardResponse correctly
  - Test: 401 response surfaces via catchError (if error handling is added)
  All tests use HttpClientTestingModule + HttpTestingController.

## Acceptance criteria
- DashboardService.list() sends GET to /api/v1/products with page and limit query params.
- JWT Bearer token attached via auth.interceptor.ts (verify in spec).
- HttpTestingController tests pass.
- DashboardQuery has exactly 2 fields: page and limit. No search. No filter.
- ProductListItem.status typed as 'draft' | 'ready' — NOT 'draft' | 'ready' | 'exported'.
- Service has no write methods.
- Angular build passes.

## Hard constraints (NON-NEGOTIABLE)
- DO NOT add search or debounce logic. Search is deferred to V1.5 per §13.A.1.
- DO NOT add filter param. Filter is deferred to V1.5 per §13.A.1.
- DO NOT add POST, PUT, PATCH, or DELETE methods. Dashboard is strictly read-only.
- DO NOT add 'exported' to the status type union. 2-value only.
- DO NOT re-implement JWT attachment. auth.interceptor.ts handles this globally.
- DO NOT use BehaviorSubject or store state in the service. DashboardService is stateless.
  State management belongs in the component (DashboardComponent) via signals.

## Files you MAY touch
- frontend/src/app/features/dashboard/services/dashboard.service.ts (NEW)
- frontend/src/app/features/dashboard/services/dashboard.service.spec.ts (NEW)
- frontend/src/app/features/dashboard/models/dashboard.model.ts (NEW)

## Files you MUST NOT touch
- frontend/src/app/features/dashboard/dashboard.component.ts (owned by component-builder)
- frontend/src/app/features/dashboard/product-row.component.ts (owned by component-builder)
- frontend/src/app/features/dashboard/status-badge.component.ts (owned by component-builder)
- frontend/src/app/features/dashboard/profile-completeness-banner.component.ts (owned by component-builder)
- frontend/src/app/app.routes.ts (owned by component-builder for this feature)
- frontend/src/app/core/interceptors/auth.interceptor.ts (global interceptor — do not modify)
- Any file under backend/
- docs/

## Final report format
After completing all tasks, produce a report with exactly these sections:

### Session close report — mesell-tracking-dashboard-frontend-session-{N}
1. Files created: list each file path
2. Build: ng build [PASS/FAIL]
3. Tests: ng test [PASS count / FAIL count]
4. DashboardQuery field count: [N] (must be 2: page, limit)
5. ProductListItem.status type: [value] (must be 'draft' | 'ready')
6. HttpTestingController test: JWT header present [PASS/FAIL]
7. Service write methods: [NONE / list any found]
8. Memory entry: "feature=tracking-dashboard session={N} CLOSED — {date}" appended to MEMORY.md
9. Any deviation from the plan: [NONE or description]
```

---

## 8. Review and Iteration Protocol

### 8.1 Backend Review (services-builder + api-routes-builder)

The backend lead (`meesell-backend-coordinator`) runs this checklist before approving any specialist PR onto `feature/tracking-dashboard/backend`:

**Structural integrity checks:**
- [ ] `backend/app/modules/dashboard/repository.py` does NOT exist. Run `ls backend/app/modules/dashboard/` and confirm absence. Presence = instant rejection.
- [ ] Only `catalog.service` and `customer.service` are imported in `dashboard/service.py`. Run: `grep "from app.modules" backend/app/modules/dashboard/service.py`. Any other module import = instant rejection.
- [ ] `dashboard/__init__.py` contains the inline comment documenting the intentional absence of `repository.py` per §13.D.

**Contract correctness (§13.A.1 amendment):**
- [ ] `DashboardQuery` has exactly 2 fields: `page` and `limit`. Inspect `schemas.py`.
- [ ] `ProductListItem.status` is `Literal["draft", "ready"]` — NOT 3 values. Inspect `schemas.py`.
- [ ] No `status_filter` parameter anywhere in `router.py` or `schemas.py`.
- [ ] No `search` parameter anywhere in `router.py` or `schemas.py`.
- [ ] `Pagination` is imported from `catalog.domain` — not redefined in `dashboard/domain.py`.
- [ ] Method call in `service.py` uses `get_onboarding_completeness` — NOT `get_profile_completeness`.

**Performance verification:**
- [ ] P95 latency <= 200ms measured against a 100-row product seed. Evidence in PR description (test timing output or profiling run).

**Test coverage:**
- [ ] 3 unit tests pass: `test_pagination_validation` (3 rejection cases), `test_response_composition`, `test_empty_state_response`.
- [ ] 2 integration tests pass: `test_dashboard_list_full_flow`, `test_dashboard_cross_tenant_isolation`.

**Import-linter:**
- [ ] `import-linter Contract 1.dashboard` passes in CI. Evidence: CI green on the PR.

**OpenAPI:**
- [ ] OpenAPI schema for `GET /api/v1/products` generated and matches `DashboardResponse` from §13.E exactly.

**i18n:**
- [ ] `validation.dashboard.invalid_pagination` key present in `backend/app/i18n/messages_en.py`.

### 8.2 Frontend Review (component-builder + service-builder)

The frontend lead (`meesell-frontend-coordinator`) runs this checklist before approving any specialist PR onto `feature/tracking-dashboard/frontend`:

**Architecture compliance:**
- [ ] No `import { ... } from 'primeng/...'` in any file under `features/dashboard/`. Run ESLint or grep.
- [ ] All 5 new components have `changeDetection: ChangeDetectionStrategy.OnPush`.
- [ ] No manual `.subscribe()` in templates. Async pipe or signals only.
- [ ] All components are `standalone: true`.

**StatusBadgeComponent contract:**
- [ ] Exactly 2 branches in `StatusBadgeComponent`: "draft" (gray) and "ready" (blue). NO "exported". NO "live". Inspect the component's template/logic.
- [ ] Docstring includes V1.5 forward reference for "exported" status.

**ProfileCompletenessBanner contract:**
- [ ] Banner trigger is `onboarding_complete === false` (boolean field). NOT a percentage comparison.
- [ ] `localStorage` key is exactly `"dashboard.banner.snoozed_until"`.
- [ ] Dismiss writes `Date.now() + 86400000` (24h in ms).
- [ ] No "remind never" option — snooze is bounded at 24h per D1.

**DashboardService:**
- [ ] `DashboardQuery` TypeScript interface has exactly 2 fields: `page`, `limit`. NO `search`. NO `filter`.
- [ ] `ProductListItem.status` type is `'draft' | 'ready'` — NOT 3-value.
- [ ] No write methods on `DashboardService`.
- [ ] JWT attached via `auth.interceptor.ts` verified in spec.

**Soft-delete:**
- [ ] Confirm dialog is keyboard-accessible (Tab to focus Confirm button, Enter to confirm).

**Visual evidence:**
- [ ] Screenshots attached at 360px viewport.
- [ ] Screenshots attached at 1280px viewport.

**Build:**
- [ ] `ng build` passes.
- [ ] `ng test` shows all specs green.

### 8.3 Re-dispatch Triggers

For each failure mode, the exact re-dispatch preamble to prepend to the base dispatch template follows. Increment the session ordinal `{N}` on each re-dispatch.

**Trigger: `repository.py` was created**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) created backend/app/modules/dashboard/repository.py.
This file MUST NOT EXIST. Delete it immediately:
  rm backend/app/modules/dashboard/repository.py

Rationale: §13.D documents the absence of repository.py as intentional structural design
("the purest demonstration of the modular monolith discipline"). Dashboard owns zero tables
and performs zero data access. All data flows via catalog.service + customer.service.
Any data access logic placed in a repository.py violates this design and will be rejected
at merge time regardless of test coverage.

After deleting the file, confirm with: ls backend/app/modules/dashboard/
Then re-read §13.D before resuming work.
```

**Trigger: Direct DB access found in service.py (AsyncSession injection)**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) injected AsyncSession into dashboard/service.py.
Dashboard is a BFF module — it owns no tables and performs zero direct DB access.

Remove the AsyncSession injection from service.py. Remove any import of get_db.
Remove any SQLAlchemy query (select, update, insert, delete) from service.py.

All data must flow through:
  await catalog.service.list_products(user_id, Pagination(page, limit))   per §10.C
  await customer.service.get_onboarding_completeness(user_id)             per §8.C

Re-read §13.C and §13.D before resuming.
```

**Trigger: P95 > 200ms**
```
PERFORMANCE CORRECTION REQUIRED:

Previous session (session-{N-1}) produced a P95 latency exceeding 200ms against the
100-row seed. Target: P95 <= 200ms per §13.H (zero-egress budget).

Debugging steps (in order):
1. Verify catalog.service.list_products applies pagination at the SQL level via
   catalog/repository.py list_paginated() — NOT in Python after fetching all rows.
   Run EXPLAIN ANALYZE on the generated query.
2. Verify no N+1 queries: list_paginated should return a list of Product rows in one
   query, not one query per product.
3. Verify customer.service.get_onboarding_completeness is a single SQL query, not
   an ORM traversal with lazy-loaded relationships.
4. Dashboard itself has zero adapter calls — if latency remains high after the above,
   the bottleneck is in catalog or customer, not dashboard. File a coordinator-level
   bug against the relevant module.

Re-read §13.H before resuming.
```

**Trigger: Filter or search param landed in DashboardQuery**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) added a status_filter or search query param.
Both are DEFERRED to V1.5 per §13.A.1 amendment (2026-06-07).

Remove the param from DashboardQuery in schemas.py.
Remove any usage of the param from router.py and service.py.
DashboardQuery must have exactly 2 fields: page and limit.

Re-read §13.A.1 before resuming.
```

**Trigger: 3-value status enum landed**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) used Literal["draft", "ready", "exported"] on
ProductListItem.status (or used the TypeScript 3-value union).

The §13.A.1 amendment (2026-06-07) narrowed this to Literal["draft", "ready"] for V1.
"exported" is deferred to V1.5.

Update ProductListItem.status (schemas.py) to: Literal["draft", "ready"]
Update the TypeScript interface in models/dashboard.model.ts to: 'draft' | 'ready'
Update StatusBadgeComponent to have exactly 2 branches (no "exported" branch).

Re-read §13.A.1 before resuming.
```

**Trigger: Banner triggered on percentage threshold (not boolean)**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) triggered ProfileCompletenessBanner on a percentage
calculation (e.g., base_complete_count / base_total_count < 1.0).

The trigger must be the boolean field: onboarding_complete === false

The onboarding_completeness response object already provides this precomputed boolean.
Do NOT recompute completeness percentages in the frontend. Use the boolean directly.

Update ProfileCompletenessBanner to: render when onboarding_complete === false.
The counter display (e.g., "8 of 10") can still use the count fields for human-readable text.

Re-read §13.B.1 DashboardResponse and FEATURE_PLAN.md §2.2 D1 before resuming.
```

**Trigger: Wrong localStorage key for banner snooze**
```
CORRECTION REQUIRED BEFORE ANY OTHER WORK:

Previous session (session-{N-1}) used an incorrect localStorage key for the banner snooze.

The locked key is: "dashboard.banner.snoozed_until"
Value format: Unix timestamp in ms (Date.now() + 86400000 for 24h snooze).

Update ProfileCompletenessBanner to use the exact key "dashboard.banner.snoozed_until".
Do not use any other key name or format.
```

### 8.4 Iteration Limit

Maximum 3 re-dispatches per specialist before escalating to the founder. Each re-dispatch increments the session ordinal (session-2, session-3, session-4). After 3 failed attempts the lead opens a founder-decision question via an Inter-lead Request documented in `docs/status/STATUS_BACKEND.md` or `docs/status/STATUS_FRONTEND.md` with a BLOCKER marker.

---

## 9. Acceptance Gate

This feature is "done" when ALL of the following are true. No partial-done state is acceptable.

**Branch and PR:**
- [ ] `feature/tracking-dashboard/planning` PR to `develop` open and CI-green using the backend PR template.
- [ ] `feature/tracking-dashboard/backend` merged to `feature/tracking-dashboard`.
- [ ] `feature/tracking-dashboard/frontend` merged to `feature/tracking-dashboard`.
- [ ] `feature/tracking-dashboard` PR to `develop` open using the backend PR template (most-involved lead: `meesell-backend-coordinator`).

**CI gates (must be green on ALL three PRs):**
- [ ] CI gate 1: lint (ruff, import-linter Contracts 1-7, Contract 1.dashboard specifically).
- [ ] CI gate 2: unit tests (backend pytest; frontend ng test).
- [ ] CI gate 3: integration tests (backend pytest integration; frontend e2e if configured).

**Backend correctness:**
- [ ] `backend/app/modules/dashboard/repository.py` does NOT exist (verified by `ls`).
- [ ] `DashboardQuery` has exactly 2 fields in production code.
- [ ] `ProductListItem.status` is `Literal["draft", "ready"]` in production code.
- [ ] P95 latency verified <= 200ms against a 100-row seed.
- [ ] OpenAPI schema updated for `GET /api/v1/products`.
- [ ] `import-linter Contract 1.dashboard` passes (verified in CI log).
- [ ] `validation.dashboard.invalid_pagination` key in `i18n/messages_en.py`.

**Frontend correctness:**
- [ ] `StatusBadgeComponent` has exactly 2 status branches in production code.
- [ ] `ProfileCompletenessBanner` trigger is `onboarding_complete === false` boolean.
- [ ] `localStorage` key is exactly `"dashboard.banner.snoozed_until"`.
- [ ] No direct PrimeNG imports in `features/dashboard/`.
- [ ] All 5 new components use `ChangeDetectionStrategy.OnPush`.
- [ ] Screenshots at 360px and 1280px reviewed and approved by founder.

**Documentation:**
- [ ] `docs/V1_FEATURE_SPEC.md §F8` implemented-stamp applied with PR link.
- [ ] `docs/BACKEND_ARCHITECTURE.md §13` sentinel flipped to `LOCKED-on-disk` with PR link.
- [ ] `docs/MEESELL_AGENT_REGISTRY.md` dashboard service surface verified.

**Memory:**
- [ ] Both leads appended MERGED entries tagged `feature=tracking-dashboard` to their MEMORY.md.
- [ ] `docs/status/feature_board_backend.md` and `docs/status/feature_board_frontend.md` rows flipped to MERGED.

---

## 10. Risk Register

**R1 — catalog.list_products N+1 query under high product counts**

Description: If `catalog/repository.py list_paginated()` is implemented with per-product sub-queries instead of a single paginated SQL call, P95 will exceed 200ms for sellers with more than ~20 products.

Mitigation: EXPLAIN ANALYZE checkpoint at backend lead review (see §8.1 performance check). If N+1 found, re-dispatch services-builder with the P95 trigger preamble from §8.3.

V1 risk level: Medium (catalog-form was built before dashboard — if its list_paginated already exists and is correct, risk is Low).

**R2 — pg_trgm GIN index missing for V1.5 search prep**

Description: When §13.A.1 is lifted in V1.5 and `search` is restored to `DashboardQuery`, the ILIKE query on `products.name` requires a GIN index on `products.name` with `pg_trgm` for acceptable latency. V1 does not need this index. If it is not added at V1.5 kickoff, search will be slow on sellers with large catalogs.

Mitigation: Open an inter-lead request to `meesell-data-engineer` at V1.5 kickoff — NOT now. This is a pre-planned future action, not a V1 action. Record this note in the data engineer's MEMORY.md at V1.5 feature planning time.

**R3 — ProfileCompletenessBanner dismiss-fatigue degrading to never-shown**

Description: If sellers see the banner on every login and dismiss it immediately, the snooze UX degrades over time as sellers become conditioned to dismiss before reading.

Mitigation: 24h snooze cap (not "remind never") enforced per D1. The cap ensures the banner resurfaces once daily until the seller actually completes the profile. There is no "never show again" option by founder decision.

**R4 — V1.5 amendment elevates dashboard to image/pricing/export summary composition**

Description: The §2.D matrix founder ruling kept the dashboard at exactly 8 cross-module calls (catalog + customer only). If V1.5 elevates dashboard to also call `image.service.summary`, `pricing.service.summary`, and `export.service.summary` (elevating to 11 cross-module calls), this forces a §13 amendment + new dispatch templates + new service composition logic.

Mitigation: Tracked as a known future scope expansion. At V1.5 planning, re-open this FEATURE_PLAN.md with a new revision history entry. The dispatch templates in §7.1 and §7.2 would need amendment sub-sections added. This is not a V1 action.

**R5 — Soft-delete race condition during paginated list query**

Description: If a product is soft-deleted (DELETE /api/v1/products/{id} via the catalog endpoint) while a dashboard paginated query is in flight, the deleted row may appear in the response and then be absent on the next page refresh.

Mitigation: `catalog/repository.py list_paginated()` applies `deleted_at IS NULL` filter at the SQL level on every query. This is a stable cursor — the filter is consistent. The race produces a one-refresh artifact (row appears then vanishes) which is acceptable UX. No distributed transaction or locking required. Document this in `services-builder` dispatch as: "the soft-delete filter race produces a one-refresh artifact — this is by design. Do not attempt to solve it with application-level locking."

---

## 11. Revision History

| Date | Author | Session | Change |
|---|---|---|---|
| 2026-06-10 | Director (`mesell-tracking-dashboard-planning-session-1`) | Initial | Initial lock — D-A/D-B/D-C/D-D operational + D1/D2/D3/D4 scope decisions; agent lineup; code surfaces; documentation deliverables; 4 dispatch templates (7.1–7.4) with full 7-sub-section structure; review + iteration protocol (8.1–8.4 including 7 re-dispatch triggers); acceptance gate (9); risk register (10). §13.A.1 amendment reconciliations documented in §1.1. |
