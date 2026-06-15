# Plan 1 — Manual Browse Fallback Page

**Status:** PENDING (FE lane, wave 4 in serialization order: after Plan 4 merges)
**Type:** FE-only
**Branch:** feature/section-2/frontend
**Specialists:** meesell-angular-component-builder

---

## Business context

The category suggest endpoint returns `fallback_offered: true` when AI is unavailable or budget is exceeded. The FE currently calls `browseRedirect()` which navigates to `/categories/browse` — but that route does not exist. The browse backend (`GET /categories/browse`) is already implemented and working.

This plan closes the gap: create the `/categories/browse` page and wire it into the Angular router.

---

## Backend contract (already exists — DO NOT change)

`GET /api/v1/categories/browse?q=<text>&super_id=<optional>&limit=20&offset=0`

Response: `BrowseResultRow[]` — each row has `category_id`, `super_id`, `super_name`, `path`, `leaf_name`, `similarity` (0.0 in V1, reserved).

pg_trgm fuzzy search over `path / leaf_name / super_name`, best-match-first, paginated, TTL 300s.

Error IDs: `validation.browse.invalid_pagination` (400/422).

---

## FE deliverables

1. **Route**: Add `categories/browse` to `frontend/apps/mfe-catalog/src/app/catalog.routes.ts` with `loadComponent` lazy-load.
2. **Component**: `frontend/apps/mfe-catalog/src/app/categories/browse/browse.component.ts`
   - Standalone, OnPush
   - `mee-input` or `mee-textarea` for search box (pre-filled from query param `?q=` if present)
   - Real-time search on input change (debounce 400ms) calling `CategoryService.browse()`
   - Render results as `<mee-category-card>` or similar mee-* composite
   - Fallback empty state using `<mee-empty-state>` when no results
   - Pagination (prev/next) using browse endpoint's offset/limit
   - Loading skeleton using `<mee-skeleton>`
   - On row select: call `CategoryService.selectCategory(categoryId)` — same outcome as smart-picker selection
3. **CategoryService**: Add a `browse(q, superId?, limit?, offset?)` method wrapping the GET endpoint (if not already present in `category.service.ts`).

---

## Acceptance criteria

- `GET /categories/browse` route resolves to the BrowseComponent (no 404)
- Entering text shows matching categories from the backend
- Selecting a category navigates to `/catalogs/:id/edit`
- Empty query shows an empty state, not an error
- `validation.browse.invalid_pagination` surfaces correctly (see Plan 2-W2)
- `ng lint mfe-catalog` zero errors; zero direct primeng imports in the browse component

---

## Serialization constraint

Must run AFTER Plan 4 merges to integration (Plan 4 touches `catalog.routes.ts` and smart-picker layout — avoids merge conflict on route file).
