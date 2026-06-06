# STATUS — FEATURE DASHBOARD

**Owner:** Dashboard Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_DASHBOARD.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/dashboard/`
**Routes owned:** `/dashboard`
**MF-remote target (Phase 2):** dashboard-mfe per FE-D13
**Special note:** dashboard owns the SideMenuComponent (left navigation reflecting the sub-session/MF-remote structure per founder note 2026-06-06)
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (bootstrapped — dispatch 1 in progress)

**Status:** ACTIVE — Dispatch 1 COMPLETE. Awaiting sub-session approval for Dispatch 2.

## Current Phase

CONSTRUCTION — Dispatch 1 complete; Dispatch 2 (ProductRowComponent) pending approval.

## Done

- All 9 mandatory reads complete (2026-06-06 bootstrap)
- Scaffold inventory confirmed: routes ✅, api-service stub (params wrong — see below) ✅,
  component stub ✅, components/ dir empty ✅
- API contract deltas identified (4 items — see bootstrap UPDATE below)
- Dispatch 1 COMPLETE (2026-06-06):
  - dashboard-api.service.ts: fixed params (status_filter + search), correct return type
    (DashboardResponse with products + profile_completeness)
  - dashboard.routes.ts: providers: [DashboardApiService] added
  - dashboard.component.ts: full implementation (MatTable + MatPaginator + chips + debounced search + signals)
  - en.json: dashboard namespace fully populated (filter.ready, table.*, noResults, profileBanner.*, untitled)
  - dashboard.component.spec.ts: 6 tests written, all passing
  - ng build --configuration=production: ZERO errors
  - vitest run: 91/91 tests passing (all 6 dashboard tests pass)

## In Progress

- None (awaiting Dispatch 2 approval)

## Blockers

- None blocking Dispatch 1.
- SideMenuComponent: AuthService exposes `userId` (JWT sub) but NOT phone number.
  Phone requires profile fetch. Will use `userId` as display fallback in V1 and
  note as a follow-up for the account session to resolve once ProfileService exists.
- Design system §5A values PARTIAL LOCK — component-builder proceeds with CSS
  custom-property placeholders per FE-D9.

## Next

1. Dispatch 1 returns → verify DashboardComponent (ng build + vitest)
2. Dispatch 2 — ProductRowComponent (depends on shared/ stubs — all present ✅)
3. Dispatch 3 — SideMenuComponent (depends on AuthService.logout() ✅ + userId ✅)

## Hand-offs

- DashboardComponent ready for Dispatch 2 (ProductRowComponent). The table rows are
  click-only navigation for now; ProductRowComponent adds the action menu + delete flow.
- en.json dashboard namespace is complete — no further i18n additions needed for Dispatch 1 surface.
- StatusBadge sub-component tests: overrideComponent stub pattern documented in
  dashboard.component.spec.ts. Future component tests with input.required() children should
  use this pattern to avoid NG0950 errors in mat-table rendering cycles.

## Updates Log

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created. Dashboard sub-session awaits founder bootstrap.
The side menu (founder note 2026-06-06) is owned by this session and
reflects the sub-session / MF-remote structure: My Catalogs / Create
Catalog / My Profile / Logout. Other sessions are downstream
navigation targets, not implementers of the menu itself.
=========

=== UPDATE: 2026-06-06 BOOTSTRAP ===
Dashboard sub-session bootstrapped by founder.

MANDATORY READS COMPLETE (9 files):
  1. STATUS_FEATURE_DASHBOARD.md — prior state: skeleton, not started ✅
  2. SESSION_PROMPTS_FEATURE_BASE.md — governance + universal rules ✅
  3. FRONTEND_ARCHITECTURE.md §0/§2.B/§3.C.4/§3.D/§4/§5A/§6/§9/§17/§19/§23 ✅
  4. MVP_ARCHITECTURE.md §3.4 — products endpoints confirmed ✅
  5. BACKEND_ARCHITECTURE.md §13 — dashboard module LOCKED ✅
  6. BACKEND_ARCHITECTURE.md §10 (B.5) — soft-delete 204 contract ✅
  7. CORE_PHILOSOPHY.md M9 — i18n structural, V1 EN only ✅
  8. STATUS_FRONTEND.md — scaffold complete (77/77 tests, ng build clean) ✅
  9. STATUS_DESIGN_SYSTEM.md — Phase 1 Round 1 curated; picks pending ✅

SCAFFOLD STATE:
  frontend/src/app/features/dashboard/
    dashboard.routes.ts         ✅ correct (lazy-loads DashboardComponent)
    dashboard-api.service.ts    ⚠️ params wrong, return type wrong (see deltas below)
    dashboard/
      dashboard.component.ts   ✅ stub, ready for component-builder
    components/                 ✅ empty dir, ready for ProductRow + SideMenu

SHARED/ DEPENDENCIES (all stubs present):
  <mee-empty-state>      ✅ (icon/headline/body/ctaLabel/ctaClick)
  <mee-status-badge>     ✅ (status input: ProductStatus | ExportStatus | ImagePrecheckResult)
  <mee-confirm-dialog>   ✅ (title/message/confirmLabel/cancelLabel/destructive/close)
  relative-time.pipe     ✅ implemented
  ProductStatus enum     ✅ ('draft'|'ready'|'exported'|'live'|'deleted')

API CONTRACT DELTAS — 4 issues found in scaffold vs §13 contract:
  DELTA-1: ProductListParams.status → must be status_filter (§13.B.1 param name)
  DELTA-2: ProductListParams.q → must be search (§13.B.1 param name)
  DELTA-3: Return type PaginatedResponse<Product> → needs DashboardResponse interface:
           { products: ProductListItem[], total, page, limit, profile_completeness }
           because backend returns 'products' (not 'data'), and includes
           profile_completeness (ProfileCompletenessSummary). Define locally in
           features/dashboard/ (not @core/models/ — BFF-specific shape per §9.C).
  DELTA-4: Session prompt says filter chips "draft / exported / live" — INCORRECT.
           §13.B.1 Literal is "draft" | "ready" | "exported". Chips = draft/ready/exported.
           The ProductStatus enum has 'live' as a future value; §13 does not use it in V1.

DISPATCH PLAN:
  Dispatch 1 — DashboardApiService correction + DashboardComponent full impl
    - Fix service: ProductListParams (status_filter + search) + DashboardResponse type
    - Implement DashboardComponent: MatTable + MatPaginator + 3 filter chips
      (draft/ready/exported) + 300ms debounced search + empty state + signals
  Dispatch 2 — ProductRowComponent (after Dispatch 1 returns + verifies)
  Dispatch 3 — SideMenuComponent
    NOTE: SideMenuComponent shows seller phone. AuthService exposes userId (JWT sub)
    only. Phone requires profile. V1 implementation: show userId as display fallback
    OR omit phone until ProfileService is available from account session.
    Surfacing this to master as a cross-session dependency.
=========

=== UPDATE: 2026-06-06 DISPATCH-1-COMPLETE ===
Phase: /dashboard — Dispatch 1: DashboardApiService + DashboardComponent
Done:
  dashboard-api.service.ts — REPLACED (breaking changes, not incremental):
    - ProductListParams: status_filter (was: status) + search (was: q)
    - New interfaces: ProductListItem, ProfileCompletenessSummary, DashboardResponse
    - DashboardResponse.products (was: PaginatedResponse<Product>.data)
    - Null/undefined param filtering before ApiClient.get() call
    - @Injectable() with no providedIn: 'root' (feature-scoped, per §3.D)

  dashboard.routes.ts — AMENDED:
    - providers: [DashboardApiService] added (was missing)

  dashboard.component.ts — FULLY IMPLEMENTED:
    - ChangeDetectionStrategy.OnPush, standalone, inject() for all DI
    - 7 signals: products, loading, totalCount, currentPage, pageSize,
      activeStatus, searchQuery, profileCompleteness
    - 3 computed helpers: hasProducts, isEmptyWithNoFilter, profileComplete
    - MatTable ([dataSource]="products()") + MatPaginator + MatChipListbox
    - FormControl searchCtrl with debounceTime(300) + distinctUntilChanged()
      via takeUntilDestroyed() in constructor (no manual unsubscribe)
    - Filter chips: "All" (null), "Draft", "Ready", "Exported" (NOT "live")
    - Empty state (mee-empty-state) when totalCount=0 AND no filter/search
    - "No results" paragraph when totalCount=0 but filter/search active
    - Profile completeness banner @if (!profileComplete())
    - Row click → navigate to /catalogs/{product_id}/edit (product_id, snake_case)
    - Keyboard nav: tabindex=0, keydown.enter, keydown.space on rows
    - Error handling: catchError → ErrorService.showError()
    - 44px touch targets: Material default chip + row height

  en.json — AMENDED (no keys removed; 6 new keys added):
    - dashboard.filter.ready: "Ready" (was missing)
    - dashboard.table.name, dashboard.table.status, dashboard.table.updated
    - dashboard.table.untitled: "Untitled"
    - dashboard.noResults: "No catalogs match your search."
    - dashboard.profileBanner.message, dashboard.profileBanner.link
    NOTE: dashboard.filter.live preserved (used by ProductStatus enum, even
    though no chip shows it in V1 — do not remove)

  dashboard.component.spec.ts — AUTHORED:
    6 tests, all passing:
    1. renders loading spinner while products are loading
    2. renders product rows when products return from API
    3. renders empty-state component when total=0 and no filter/search
    4. renders "no results" paragraph when total=0 and filter/search active
    5. calls API with status_filter when chip is selected
    6. calls API with search param after 300ms debounce (vi.useFakeTimers)

Tests: 91/91 passing (all 6 dashboard tests + 85 pre-existing)
Build: ng build --configuration=production — ZERO errors
  dashboard-component lazy chunk: 169.82 KB raw / 30.57 KB gzip (within §19 budget)

Deviations from spec:
  1. "Untitled" label goes through TranslocoService.translate() via displayName()
     helper method (not the pipe in template) — cleaner than a null-coalescing
     pipe expression; i18n key: dashboard.table.untitled.
  2. 'profile_completeness' signal typed as { profile_complete: boolean } | null
     (not full ProfileCompletenessSummary) to keep the computed helper minimal;
     the full type is in DashboardApiService and is consumed only in loadProducts().
  3. overrideComponent pattern used in tests to stub StatusBadgeComponent (which has
     input.required()) — this is the correct unit-test isolation pattern for Angular 18
     required inputs. NO_ERRORS_SCHEMA would not suppress runtime NG0950 errors.

Blockers resolved: none (all 4 API contract deltas from bootstrap resolved)
=========

## Questions for master

_(sub-session appends here)_

## Questions for sibling sessions

=== QUESTION FOR ACCOUNT SESSION (2026-06-06) ===
SideMenuComponent (owned by dashboard session) shows seller phone per the
session prompt. AuthService exposes userId (JWT sub) but not phone. Is there a
ProfileService in the account session that dashboard can inject via @core/ or
@shared/ to read the seller phone? If not, recommend:
  Option A: SideMenuComponent shows userId (masked) as V1 fallback, adds phone
            once account session exposes ProfileService in @core/models/.
  Option B: Sidebar header shows "My Account" with no phone (profile-free fallback).
Dashboard session will proceed with Option B unless account session confirms
Option A is available. Account session: please note response in
STATUS_FEATURE_ACCOUNT.md (if exists) or surface via master.
=== END QUESTION ===
