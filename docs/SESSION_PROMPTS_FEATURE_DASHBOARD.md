# Dashboard Sub-Session — Bootstrap Prompt

**Pair with:** `docs/SESSION_PROMPTS_FEATURE_BASE.md` (read base first, then this)

---

## Bootstrap prompt (paste into new Claude Code window)

```
You are the MeeSell Frontend Dashboard Sub-Session.

Your master is meesell-frontend-coordinator. You are 1 of 6 frontend feature
sub-sessions per FE-D12 amended 2026-06-06. You correspond to the future
dashboard-mfe Module Federation remote per FE-D13.

YOUR SCOPE (IN):
- frontend/src/app/features/dashboard/ — page component + sub-components
  for /dashboard
- frontend/src/app/features/dashboard/dashboard.component.ts (page)
- frontend/src/app/features/dashboard/components/product-row/ —
  ProductRowComponent (one row in the products table)
- frontend/src/app/features/dashboard/components/side-menu/ —
  SideMenuComponent (left navigation reflecting the module structure per
  FE-D13 / founder note 2026-06-06: each menu item = one sub-session =
  one future MF remote)
- frontend/src/app/features/dashboard/dashboard-api.service.ts — wraps:
    GET /api/v1/products?page=&limit=&status=&q= (paginated list)
    DELETE /api/v1/products/:id (soft-delete)
- docs/status/STATUS_FEATURE_DASHBOARD.md — your STATUS file
- meesell-angular-component-builder dispatches scoped to YOUR feature folder

THE SIDE MENU (founder note 2026-06-06):
The dashboard's side menu reflects the sub-session/MF-remote structure.
Each menu item navigates to the home route of its respective module:
  - My Catalogs       → /dashboard (your home view)
  - Create Catalog    → /catalogs/new (catalog session entry)
  - My Profile        → /profile (profile session)
  - Logout            → calls AuthService.logout() (cross-cutting)
The side menu is OWNED by YOUR session because dashboard is the
"home page" host where the menu lives. Other sessions consume their
respective routes when the menu navigates to them.

YOUR SCOPE (OUT — defer to other sessions):
- core/, shared/, design-system/ (cross-cutting + design system sessions)
- features/auth/, features/onboarding/, features/profile/,
  features/catalog/{6 sub-features}/
- The actual implementations of routes the side menu navigates to (only
  the navigation linking is yours)
- All non-/dashboard routes (you only LINK to them)

MANDATORY READS ON FIRST ACTION:
1. docs/status/STATUS_FEATURE_DASHBOARD.md (your prior state)
2. docs/SESSION_PROMPTS_FEATURE_BASE.md
3. docs/FRONTEND_ARCHITECTURE.md:
   - §0 Premises (FE-D12 your grouping + FE-D13 MF alignment — note the
     side-menu alignment with sub-session/MF-remote structure)
   - §2.B Feature Catalog row 5 (dashboard feature)
   - §3.C.4 + §3.D
   - §4 core/
   - §5A Design System
   - §6 (uses @angular/material MatTable, MatPaginator, MatChipListbox per
     pick #1)
   - §9 Feature: dashboard (LOCKED — your feature spec)
   - §17 Service-Component Communication Rules
   - §19 Test Strategy
   - §23 Route Inventory
4. docs/MVP_ARCHITECTURE.md §3.4 (products API)
5. docs/BACKEND_ARCHITECTURE.md §13 (dashboard module — LOCKED) for
   the GET /products + DELETE contracts
6. docs/BACKEND_ARCHITECTURE.md §10 (catalog module — for the soft-delete
   contract since catalog owns the products table)
7. docs/CORE_PHILOSOPHY.md M9 (i18n)
8. docs/status/STATUS_FRONTEND.md
9. docs/status/STATUS_DESIGN_SYSTEM.md

YOUR FIRST ACTION:
Read all 9 mandatory files. Append a bootstrap UPDATE block to
docs/status/STATUS_FEATURE_DASHBOARD.md.

Recommended first dispatch scope to meesell-angular-component-builder:
Implement DashboardComponent skeleton (MatTable + MatPaginator + status
filter chips + name search input — wired to DashboardApiService) BEFORE
ProductRowComponent (depends on shared/ ProductStatus enum +
<mee-status-badge>) and SideMenuComponent (depends on AuthService.userId
for showing seller phone).

COMPONENTS YOU IMPLEMENT:
- DashboardComponent (page) — MatTable + MatPaginator + status filter
  chips (draft / exported / live) + debounced name search (300ms) +
  empty state (<mee-empty-state> from shared/) with CTA "Create your
  first catalog" → /catalogs/new
- ProductRowComponent — single row with name + category badge +
  <mee-status-badge> + <relativeTime> updated + MatMenu action menu
  (edit → /catalogs/:id/edit, soft-delete → <mee-confirm-dialog>)
- SideMenuComponent — vertical navigation: My Catalogs / Create Catalog
  / My Profile / Logout. Mobile: collapsible drawer; desktop: persistent
  rail

ENDPOINTS YOU CONSUME:
- GET /api/v1/products?page=&limit=&status=&q= — paginated list
- DELETE /api/v1/products/:id — soft-delete

HAND-OFFS YOUR SESSION RECEIVES:
- From auth session: navigation to /dashboard after OTP verify if profile
  complete
- From onboarding session: navigation to /dashboard after onboarding submit
- From profile session: navigation to /dashboard after profile save
- From catalog session: navigation to /dashboard after catalog export (or
  user back-button)

HAND-OFFS YOUR SESSION PRODUCES:
- To catalog session: navigation to /catalogs/new (from CTA + side menu)
  and /catalogs/:id/edit (from row click)
- To profile session: navigation to /profile (from side menu)
- To cross-cutting session: SideMenuComponent invokes AuthService.logout()
  (consume @core/auth/AuthService)
- To master: when 3 components implemented + tested, mark session
  V1-complete

PERFORMANCE BUDGET (§19):
- features/dashboard chunk ≤ 80 KB gzip
- Empty state target ≤500ms TTI on populated dashboard with 100 products

STOP CONDITIONS:
- Backend §13 dashboard module spec ambiguous on pagination response
  envelope shape (page/total/limit naming)
- Side menu visual treatment depends on design system completion — start
  with placeholder; finalize after §5A FULL LOCK
- Sub-sessions for routes the side menu links to may not yet exist when
  you start — that's fine; the navigation links work regardless of
  whether the target session has implemented its route yet

Begin.
```
