## §9 category services slice CONSTRUCTED (2026-06-07)

### Scope
Sub-session `meesell-backend-construction-9-category-1` — services-builder
slice (api-routes-builder runs in parallel for router.py + schemas.py +
main.py mount).  Built repository + service + exceptions + domain for §9
per BACKEND_ARCHITECTURE.md §9 (LOCKED 2026-06-05).

### Files created (4)
- `backend/app/modules/category/exceptions.py` — `CategoryError` base + 4
  subclasses per §9.G (CategoryNotFoundError 404, FieldEnumNotFoundError 404,
  SuggestQueryInvalidError 400, BrowseQueryInvalidError 400).
- `backend/app/modules/category/domain.py` — 2 frozen dataclasses per §9.F
  (CategoryRow, SuperCategoryInfo).
- `backend/app/modules/category/repository.py` — 7 module-private async
  methods per §9.D.  **No `scope_to_user`** (categories/templates/
  field_enum_values are §4.C global data — §19 linter exempts).
- `backend/app/modules/category/service.py` — 8 PUBLIC async methods per
  §9.C.  Returns plain `dict` payloads (NOT Pydantic shapes — schemas.py
  is owned by api-routes-builder dispatched in parallel).

### Files modified (1)
- `backend/app/core/cache.py` — `prewarm_top_categories` rewritten from V1
  stub to real implementation.  Lazy-imports `app.modules.category.service`
  inside the function to avoid the circular core/→modules/ import.  Uses
  `make_worker_session()` (lifespan ctx has no get_db).  Warms
  category_tree GLOBAL key + schema:{id} for top n categories (taken as
  the first n in canonical (super_id, leaf_name) order for V1; replaced
  with traffic-driven ranking in V1.5).  Failure-mode = try/except per
  step, never blocks boot.

### Tests added (5 unit modules + 3 integration modules)

Unit (`tests/modules/category/`):
- `test_trigram_search_uses_gin_index.py` (2 tests) — EXPLAIN ANALYZE
  asserts Bitmap Index Scan on one of the 3 GIN trgm indexes
  (idx_categories_path_trgm / _leaf_name_trgm / _super_name_trgm shipped
  in migration a1b2c3d4e5f6).  P95 over 100 iterations < 200 ms target.
- `test_schema_fetch_envelope_conformance.py` (4 tests) — 5 random
  category_ids each; 7-key envelope, compliance_shape ∈ {standard,
  collapsed}, total = compulsory + optional, fields[] carry the
  5 §5A.C-derived keys (canonical_name, data_type, primitive, marker,
  is_advanced).
- `test_field_enum_returns_labelled_payload.py` (2 tests) — entries
  carry {canonical, meesho, labels.en}; single-flight dedupe verified
  via monkeypatched call-counter.
- `test_suggest_graceful_fallback_on_budget.py` (2 tests) — covers BOTH
  paths: (a) `BudgetExceededError` raised through `call_gemini` →
  200 + empty + fallback_offered=True, (b) `AIResponse.parsed.
  fallback_offered=True` returned → same.
- `test_suggest_layer2_invalid_id_retry.py` (1 test) — AI returns an
  invalid UUID; service's final-pass guardrail rejects + emits empty
  fallback envelope.

Integration (`tests/integration/`):
- `test_category_smart_picker_to_schema_flow.py` — HTTP /suggest (mocked
  call_gemini) → /{id}/schema (200 + 7-key envelope).
- `test_category_browse_to_schema_flow.py` — HTTP /browse → /{id}/schema.
- `test_category_etag_roundtrip.py` — GET /categories ETag → 304 via
  If-None-Match.

All 3 integration tests pytest.skip on 404 from the category router so
they don't fail when api-routes-builder hasn't shipped router.py yet.
They ERROR on the pre-existing test-infra blocker (audit_events relation
missing on ephemeral test DB) — SAME issue as §8 customer integration
tests (memory D3); separate test-infra dispatch.

### Test counts
- Category unit: **15/15 PASS** (4 pre-existing picker_helpers + 11 new) in 28.4 s.
- Core/cache regression: **5/5 PASS** (`test_prewarm_top_categories_stub_no_raise`
  still passes because the rewritten prewarm catches all exceptions and
  returns).
- Boot regression: **7/7 PASS**.
- Combined: **27/27 PASS**.

### Decisions FLAGGED (NEW)

D1 — **Service returns `dict` payloads (NOT Pydantic models).**  `schemas.py`
is owned by api-routes-builder dispatched IN PARALLEL with this slice.
Returning dicts decouples the service tests from the schema author cycle;
the router does `XxxResponse.model_validate(dict)` at the boundary.  No
double-validation cost — the cache layer JSON-roundtrips already.  When
schemas.py lands the service signatures can be widened to return Pydantic
models without breaking callers (the dict shape == the Pydantic model
shape by construction).

D2 — **`repository.fetch_schema_uncached` merges `templates.compliance_shape`
into the §5A.B envelope at read time.**  The seeded `templates.schema_jsonb`
JSONB carries 6 top-level keys (`fields`, `compulsory_count`,
`optional_count`, `total_count`, `wizard_step_count`, `main_sheet_label`);
the 7th key (`compliance_shape`) lives on the dedicated `templates.
compliance_shape` column for indexability.  The repository SELECTs both
in one JOIN and assembles the 7-key envelope per §5A.B spec.

D3 — **The 4 §9.G validation_message_ids in the dispatch prompt are
2-segment shorthand.**  §5A.H regex locks 3-segment.  Used the canonical
3-segment IDs already shipped by §5A construction
(`category.lookup.not_found`, `category.field_enum.not_found`,
`validation.suggest_q.too_short_or_long`,
`validation.browse.invalid_pagination`).  Same precedent as §7 iam
(memory D2) and §8 customer (memory D5).  ESCALATION QUEUED if master
prefers updating §5A.H to permit 2-segment.

D4 — **Integration tests `pytest.skip` on router 404** so they survive
the parallel api-routes-builder dispatch.  Once the router lands, the
skips fall away and the assertions exercise the HTTP surface end-to-end.

D5 — **`get_commission` returns `Decimal('0.00')` when `commission_pct`
IS NULL** (rather than raising).  The 404 path (no row) still raises
`CategoryNotFoundError`; the NULL-commission row is treated as "no
commission rule seeded yet — pricing service may apply a default at the
call site".  Documented in service docstring; pricing-builder will refine
on §12 dispatch.

### Hand-offs queued

- **meesell-api-routes-builder (parallel)** — service surface returns
  dicts.  Router wraps each in `SuggestResponse.model_validate(payload)`
  (etc.).  For GET /categories: compute `etag_for(json.dumps(payload).
  encode())`; set ETag header; on If-None-Match match return 304.  For
  GET /categories/{id}/schema: same ETag pattern.

- **§10 catalog** — `catalog.service.create_product` calls
  `category.service.assert_category_exists(category_id, db)` BEFORE the
  insert.  `catalog.service.validate_product` calls
  `category.service.fetch_schema(category_id, db)` to retrieve the
  §5A.B envelope.  Both raise `CategoryNotFoundError` (404).

- **§12 pricing** — `pricing.service.calculate_price` calls
  `category.service.get_commission(category_id, db)`.  Returns
  `Decimal` (never None; falls back to `Decimal('0.00')` when
  `commission_pct` is NULL).

- **§8 customer (back-edge)** — `customer.service.set_active_categories`
  already uses a customer-private `_get_super_id_set` distinct read.
  When the api-routes dispatch lands, customer can switch to
  `category.service.list_super_categories(db)` for the canonical
  `SuperCategoryInfo` cross-module type.  The legacy cache key
  `customer.super_category_set` and the new `super_category_list` are
  separate by design (cache keyspace already includes the caller name).

- **§19 import-linter** — register the category module's repository
  surface as a §16 boundary: `from app.modules.category.repository
  import` MUST NOT appear under any other `app/modules/<other>/`.
  `from app.adapters.gemini import` MUST NOT appear under
  `app/modules/category/` (already clean — grep verified).

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §9 category services slice 2026-06-07 | project | 4 source + 1 cache.py rewrite + 5 unit (15 tests) + 3 integration; 27 regression PASS |
| category global-data carve-out | reference | repository carries NO `scope_to_user` — §4.C exception listed in `core/tenancy._GLOBAL_TABLES` |
| category cache key inventory | reference | smart_picker (900s) / browse (300s) / category_tree (3600s + ETag) / schema:{id} (3600s + ETag) / field_enum:{id}:{name} (3600s, single_flight=True) / super_category_list (3600s) |
| service returns dict not Pydantic (D1) | reference | service surface dict-typed; router wraps in `.model_validate(payload)` — schemas.py owned by api-routes-builder |
| fetch_schema 7-key envelope merge (D2) | reference | repository SELECTs schema_jsonb + compliance_shape column together; merges into §5A.B 7-key envelope |
| ID normalisation D3 (3-segment) | reference | category IDs use `category.lookup.not_found`/`category.field_enum.not_found` registered in i18n; matches §5A.H regex |
| prewarm_top_categories real impl | reference | lazy-imports category.service from inside the fn (avoids circular); uses `make_worker_session()`; warms tree + top n schemas; try/except per step |
| integration test skip-on-404 (D4) | reference | category integration tests skip when router 404s — survives parallel api-routes-builder dispatch |
| get_commission None→Decimal('0.00') (D5) | reference | no-row → CategoryNotFoundError; row + null commission → 0.00 (pricing applies default at call site) |
