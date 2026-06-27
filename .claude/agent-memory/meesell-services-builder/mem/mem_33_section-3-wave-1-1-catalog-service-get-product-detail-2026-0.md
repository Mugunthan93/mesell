## section-3 Wave 1.1 — catalog.service.get_product_detail (2026-06-15, branch feature/section-3/backend)

### Scope
Single new PUBLIC read method on `app/modules/catalog/service.py` (GAP-1: catalog-form FE
recovers `category_id` on hard reload / direct-URL nav without router state). The 11th public
catalog surface. Commits 71960c4 (code+tests) + 5f19111 (STATUS) on feature/section-3/backend.

### Method (mirrors existing get_validation_summary / get_preview shape exactly)
```
async def get_product_detail(user_id, product_id, db) -> Product:
    await assert_product_ownership(product_id, user_id, db=db)   # leak-collapse gate
    row = await catalog_repo.find_by_id(db, user_id, product_id)  # canonical scoped accessor
    if row is None: raise ProductNotFoundError()                  # TOCTOU None-guard
    return _orm_to_domain(row)
```
- Returns `catalog.domain.Product` (frozen dataclass, carries category_id). NOT "ProductDomain"
  (no such name). Raises `ProductNotFoundError` (404 / catalog.product.not_found) collapsing
  missing/cross-tenant/soft-deleted — identical to assert_product_ownership semantics.
- `catalog_repo.find_by_id(db, user_id, product_id)` is POSITIONAL (db FIRST). Filters
  deleted_at IS NULL + scope_to_user, returns None on any of the 3 miss cases.
- Zero new imports — Product, assert_product_ownership, catalog_repo, ProductNotFoundError,
  _orm_to_domain all already in service.py. Edits: __all__ (alpha after get_draft) + docstring
  inventory line only.

### Tests (tests/modules/catalog/test_service_unit.py — class TestGetProductDetail, 4 fns)
Reused existing `_seed_product`/`_seed_catalog` helpers + fixtures `db,user,other_user,
beauty_category,use_live_valkey`. _seed_product takes `deleted=True` for soft-delete case.
Tests are marked integration (need Postgres on localhost:5432 — reachable; NOT the 5433 tunnel).

### Infra gotcha confirmed AGAIN (carried from §19 memory)
`TestAutofillGracefulFallback::test_budget_exceeded_*` in the SAME file fails locally with
redis ConnectionError to localhost:6381 (the `use_live_valkey` tunnel port, not running on
laptop). PRE-EXISTING — proven via `git stash` baseline run. My 4 tests pass independently
(autofill is the only Valkey-touching test in that file). When running this file locally,
filter `-k "not Autofill"` or stand up the 6381 tunnel.

### Branch/worktree note
The repo root checkout was on `develop`; `feature/section-3/integration` was checked out in a
SEPARATE worktree (git showed `+` prefix). Target `feature/section-3/backend` existed already.
Committed by: stash my 2 files → checkout target → stash pop → add ONLY my files → commit.
Other unrelated dirty files (memory MDs, STATUS_FRONTEND, smart-picker.ts) were left untouched.

---
