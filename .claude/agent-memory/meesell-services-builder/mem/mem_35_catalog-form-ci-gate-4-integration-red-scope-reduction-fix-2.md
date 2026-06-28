## catalog-form CI Gate-4 (integration) RED — scope-reduction fix (2026-06-16, branch feature/catalog-form-fix)

CI Gate 4 RED on PR #257. `tests/modules/catalog/test_integration.py::TestFullProductLifecycle::test_full_lifecycle`
FAILED: `ValidationFailedError: application_area: not in category enum`. ROOT CAUSE = over-reach in e6980c6:
I had rerouted ALL 6 catalog/service.py `fetch_schema` call sites (incl. patch_product/validate_product) to
`fetch_schema_dto` (flat §5A.C). The mapper derives `enum_resolver="category"` for every dropdown → the catalog
validator then calls `get_field_enum(category_id, "application_area")` → `FieldEnumNotFoundError` (no enum seeded
for that field in the test's beauty_category) → value rejected. On develop the validator read the RICH shape where
`enum_resolver` is ABSENT → defaulted to lenient "static" → accepted. Rerouting the VALIDATOR changed behavior.

FIX (scope the mapper to the /schema route ONLY):
- REVERTED all 6 catalog/service.py call sites + 2 comment/docstring lines → `fetch_schema` (rich). catalog/service.py
  is now BYTE-IDENTICAL to develop (`git diff develop -- catalog/service.py` empty). Validator behavior restored.
- KEPT `category/router.py:263` `/schema` route on `fetch_schema_dto` (the actual FE wizard fix — bugs #1/#2/#3).
- KEPT mapper (`_map_field_to_dto`/`_map_envelope_to_dto`/`fetch_schema_dto`) + `tests/test_schema_dto_mapper.py`.
- export/service.py:452 + core/cache.py:232 prewarm STAY rich `fetch_schema` (unchanged).
- Fixed BACKEND_ARCHITECTURE §5A amendment: removed the false "read by catalog.validate_product" claim; now states
  the §5A.C flat shape is the WIRE shape served via GET /categories/{id}/schema (`fetch_schema_dto`), and
  `catalog.validate_product` continues to read the RICH shape via `fetch_schema` (validator alignment = DEFERRED).
  DATABASE_ARCHITECTURE §4.2 note only mentioned the wizard → left as-is (accurate).

LESSON (reusable): the catalog FORM bugs are FE `/schema`-consumer bugs. The catalog VALIDATOR (PATCH per-field
validation) reads the SAME schema fn but its enum-resolution semantics are load-bearing — a read-time projection that
DERIVES `enum_resolver` flips lenient→strict and rejects valid dropdown values whose per-category enum isn't seeded.
SCOPE a wire-shape projection to the wire route (router) ONLY; never reroute the validator without a separate test.

TEST HARNESS (local, no 5433 port-forward): the integration `db` fixture falls through to localhost:5433 when neither
TEST_DATABASE_URL nor DEV_DATABASE_URL is set. Live local Postgres is on :5432 (db `meesell`, 3772 seeded categories).
Run with `DEV_DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell` + `TEST_VALKEY_URL=redis://localhost:6379/0`
+ `CORE_TEST_VALKEY_URL=redis://localhost:6379`, env sourced from master `.env`, 3.11 venv, PYTHONPATH=worktree/backend.
Per-test transaction rolls back so the seeded categories aren't polluted. Result: 36 integration passed (incl.
test_full_lifecycle), 110 unit passed, ruff clean.
