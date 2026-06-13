# Memory — meesell-database-builder

## Agent Identity
Database specialist for MeeSell. Owns SQLAlchemy 2.0 async ORM models + Alembic migrations + seed scripts for the 13 V1 tables (supersedes old "7 V1 tables" reference — use MVP_ARCHITECTURE §2 + §10 as the contract).

---

## §19 multi-tenant regression CONSTRUCTED (2026-06-08, Wave 7 step 2)

### Scope
Sub-session `meesell-backend-construction-19-tests-1` — co-acted with meesell-services-builder. My portion: §19.H multi-tenant isolation regression test + review/refinement of the §19.D `db` pytest fixture posture.

### What I did (database-builder side — §19.D + §19.H)

#### tests/integration/test_multi_tenant_isolation.py (§19.H — 278 LOC)
- 4 attack vectors as separate test methods per `TestMultiTenantIsolation`:
  1. `test_user_b_cannot_get_user_a_product_preview` — Vector 1 (direct GET).
  2. `test_user_b_list_excludes_user_a_products` — Vector 2 (list endpoint leakage).
  3. `test_user_b_cannot_patch_user_a_product` — Vector 3 (autosave PATCH cross-user).
  4. `test_user_b_cannot_upload_image_to_user_a_product` — Vector 4 (image upload cross-user).
- Seeds via direct ORM INSERT (no OTP flow): `_create_user(phone)` + `_create_product(user_id)` — both helpers live in the test module so they stay co-located with their consumers.
- `app.core.auth.issue_access_token(user_id, plan)` mints the User B JWT; sent as `Authorization: Bearer ...` header.
- Asserts 404 (preferred per §15.B "leaks no info") OR 403 (acceptable as no-leak); only 200/204 would indicate a §15.B Layer 1 / Layer 2 breach.
- Picks a seeded leaf category via `SELECT id FROM categories WHERE is_leaf = true LIMIT 1` so the test holds regardless of which super_id is used. Skips with `pytest.skip` if no leaf category is seeded.
- Each test consumes all 5 mock adapter fixtures (`mock_msg91_adapter`, `mock_ai_ops_client`, `mock_gcs_adapter`, `mock_razorpay_adapter`) so the test surface is the HTTP authorization layer alone — vendor calls are deterministic.

#### tests/conftest.py `db` fixture posture (§19.D — review only)
- The pre-existing `db` fixture in `tests/conftest.py` already implements the §19.D LOCKED posture: real Postgres via dev tunnel + per-test transaction begin + ROLLBACK at teardown + NullPool engine per test (function-loop-bound). The fixture's loop_scope="function" + NullPool pattern correctly handles pytest-asyncio 0.24's function-scoped event loop without cross-loop Future attachment errors.
- **No changes needed** — the existing fixture matches the §19.D contract verbatim. The services-builder side appended the 5 NEW fixtures (`valkey`, `mock_ai_ops_client`, `mock_msg91_adapter`, `mock_gcs_adapter`, `mock_razorpay_adapter`); my review confirmed they don't conflict with the existing `db` / `db_engine` / `db_session` / `client` / `auth_client` / `use_live_valkey` / `dev_engine` fixtures.
- The `valkey` fixture (new) builds on `use_live_valkey` (existing) and adds an explicit 4-DB FLUSHDB teardown — the §19.D "per-test FLUSHDB on DB 0/1/2/3" requirement.

### Decisions made (database-builder side)
1. **Direct ORM INSERT for test users + products.** The §19.H test surface is the HTTP authorization layer (§15.B Layer 1 + Layer 2), NOT the OTP issuance pipeline (§7.B). Using `app.core.auth.issue_access_token` directly + ORM INSERT keeps the test bounded; the OTP flow is exercised separately in §7.J unit tests.
2. **Skip-not-error on missing leaf category.** If `SELECT FROM categories WHERE is_leaf = true LIMIT 1` returns empty, the test SKIPS rather than ERRORS — acknowledges the seed loader hasn't been invoked yet without blocking the entire test pipeline.
3. **404 OR 403 acceptable.** §15.B explicitly prefers 404 (no info leak) but the architecture isn't strict on the exact status. Accept either; only 200/204 fail the test. Documented inline in the assertion message.

### Tests
- 4 multi-tenant integration test methods collected cleanly via `pytest --co`.
- Execution requires the dev SSH tunnel (autossh → gcp-nexus:5433/6381) — currently down (tunnel state confirmed via `nc -zv localhost 5433` → "Connection refused"). Test PARSING + COLLECTION verified clean. Run verification deferred to master post-tunnel-restoration.

### Acceptance status (database-builder portion)

| # | Criterion | Status |
|---|---|---|
| 1 | §19.H 4 attack vectors enumerated as separate test methods | ✅ |
| 2 | §19.D `db` fixture matches LOCKED posture (real PG + per-test tx + ROLLBACK) | ✅ preserved unchanged |
| 3 | Multi-tenant regression PASSES against current codebase | ⏸ DEFERRED — tunnel down; awaiting infra restoration |

### Hand-offs queued
- **meesell-infra-builder**: restore dev SSH tunnel so master can verify multi-tenant regression.
- **Master**: post-tunnel verification of all 4 vectors. Expected outcome — all 4 PASS (the §15.B 3-layer defense was constructed in §10 + §11 + §13 + §14 sub-sessions and verified in those sub-sessions' own §X.J integration tests; this regression is the consolidated cross-cutting sentinel).

---

## §5 shared CONSTRUCTED (2026-06-06)

### Scope
Joint dispatch with `meesell-services-builder` against `BACKEND_ARCHITECTURE.md` §5 (`shared/` Foundation Layer).

### What I did (database-builder side — §5.E)
- Migrated all 13 ORM models verbatim from `backend/app/models/` → `backend/app/shared/models/`.
- Internal `from app.models.<sibling>` references rewritten to `from app.shared.models.<sibling>`.
- Authored `shared/models/__init__.py` — single canonical import surface for `from app.shared.models import (User, SellerProfile, Template, Category, FieldEnumValue, FieldAlias, Catalog, Product, ProductImage, PricingCalc, Export, AuditEvent, ProductDraft)` (the locked §5.E import path).
- Authored `shared/models/base.py` — re-exports `Base` from `shared/database.py` for backward-compat with the existing model-side import convention.
- NO schema changes. Alembic head remains `f31c75438e61`. No new migrations authored.
- Legacy `backend/app/models/` tree DELETED. Legacy `app/models/base.py` DELETED.

### Cutover scope (joint with services-builder)
Updated 14 legacy importers (master originally listed 6 — found 8 more by grep):
- `app/main.py`, `app/routers/auth.py`, `app/middleware/auth.py`, `app/middleware/plan_guard.py`
- `app/workers/celery_app.py`
- `app/services/otp_service.py`, `app/services/ai_engine.py`, `app/services/storage.py`
- `alembic/env.py`
- `tests/conftest.py`, `tests/test_database.py`, `tests/test_config.py`, `tests/test_worker_db_isolation.py`, `tests/test_middleware_auth.py`, `tests/test_middleware_plan_guard.py`

### Tests
- 42/42 schema tests (`tests/test_database.py`) — PASS against live dev Postgres via SSH tunnel (gcloud-managed, port 5433).
- 7/7 boot integration tests (`tests/test_app_boot_integration.py`) — PASS.

### Acceptance criteria status
| # | Criterion | Status |
|---|---|---|
| 1 | §5.E — 13 model files in shared/models/ matching Alembic head f31c75438e61 | PASS |
| 2 | §5.E — `__init__.py` exports all 13 single import surface | PASS |
| 3 | §5.E — SQLAlchemy 2.0 `Mapped[T]` style preserved | PASS (verbatim migration) |
| 4 | §5.E — `Base` re-exported by `shared/models/base.py` | PASS |
| 5 | 42/42 schema tests continue PASS | PASS |
| 6 | Ruff clean on touched files | PASS |

### Hand-offs queued
- §4 `core/` construction can now consume `from app.shared.models import …` per the locked single-import-surface rule.
- §4 `core/auth.py` (FE-D5 amendment) consumes `shared/database.py:get_db` + `shared/valkey.py:get_valkey_otp` + the Lua script registration helpers (`load_lua_script`, `eval_lua_script`).
- §7 (`iam` module) dispatch will populate Secret Manager values for `refresh-token-pepper` and `razorpay-webhook-secret` (declared in `shared/config.py:Settings` per §5.D, currently dev-placeholder in `.env`).

---

## Phase 1 — ORM Models COMPLETE (2026-06-05)

### Head revision
Phase 1 is models-only.  No Alembic revision applied yet (Phase 2).
Existing legacy migration `2651e548010e` covers the OLD schema (users, catalogs, skus, images, exports) and has NOT been applied to any shared DB.  Phase 2 baseline migration will replace it.

### Files authored (all in `backend/app/models/`)
| File | Table | LOC |
|---|---|---|
| `__init__.py` | exports all 13 models | 93 |
| `base.py` | re-exports Base from app.database | 10 |
| `user.py` | users | 97 |
| `seller_profile.py` | seller_profile | 136 |
| `template.py` | templates | 124 |
| `category.py` | categories | 112 |
| `field_enum_value.py` | field_enum_values | 95 |
| `field_alias.py` | field_aliases | 61 |
| `catalog.py` | catalogs | 90 |
| `product.py` | products | 146 |
| `product_image.py` | product_images | 102 |
| `pricing_calc.py` | pricing_calcs | 88 |
| `export.py` | exports | 95 |
| `audit_event.py` | audit_events | 99 |
| `product_draft.py` | product_drafts | 89 |

`database.py` was already correct (async engine, NullPool Celery variant, get_db dependency, settings.DATABASE_URL). No changes made.

### 4 schema deltas applied (pre-approved by coordinator)

1. **`seller_profile` — 3 collapsed columns DROPPED** (`manufacturer_details`, `packer_details`, `importer_details`).
   Only the 9 standard fields are stored.  Export Adapter concatenates at XLSX time.
   Source: §12.6 final ruling (overrides §2.2 DDL).

2. **`templates.compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'`** added.
   CHECK constraint: `IN ('standard', 'collapsed')`.
   Source: §5.5.13 + §12.6.

3. **`field_enum_values.enum_entries JSONB`** (richer structure) instead of `enum_values JSONB`.
   Shape: `[{"canonical": "...", "meesho": "...", "labels": {"en": "..."}}]`.
   Source: §5.6.4.

4. **`field_aliases.for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE`** added.
   Source: §12.2 + MEESHO_CATEGORY_INTELLIGENCE §6.

### SQLAlchemy 2.0 conventions locked in
- Typed style: `Mapped[T] = mapped_column(...)` throughout
- `from __future__ import annotations` + `TYPE_CHECKING` guards for all cross-model forward refs
- String-based `relationship("ClassName", ...)` — resolved by mapper at first access
- Import order in `__init__.py` follows FK dependency chain (topological)
- `server_default=text("gen_random_uuid()")` for all UUID PKs — requires pgcrypto (confirm in Phase 2 migration)
- `DateTime(timezone=True)` → `TIMESTAMP(timezone=True)` from `sqlalchemy.dialects.postgresql` — used consistently
- `JSONB` from `sqlalchemy.dialects.postgresql` throughout
- `ARRAY(String)` for `seller_profile.active_super_categories`
- `Computed("order_idx = 1", persisted=True)` for `product_images.is_front` GENERATED ALWAYS AS column
- `BigInteger + Identity(always=True)` for `audit_events.id` BIGSERIAL PK
- ForeignKeyConstraint in `__table_args__` for multi-column FKs (seller_profile, product_drafts, field_enum_values)

### Gotchas / learnings
- `Computed(persisted=True)` is the correct SQLAlchemy 2.0 way to map PostgreSQL GENERATED ALWAYS AS ... STORED columns.  Do NOT use server_default or init=False approach.
- `Identity(always=True)` maps to GENERATED ALWAYS AS IDENTITY (SQL standard) which is equivalent to BIGSERIAL but more correct on PG10+.
- `ARRAY(String)` for TEXT[] columns — import from sqlalchemy.dialects.postgresql.
- GIN index for ARRAY column: `Index("name", "col", postgresql_using="gin")` in `__table_args__`.
- Circular import resolution pattern: `from __future__ import annotations` + `TYPE_CHECKING` import guards in each model file.  The `__init__.py` import order resolves everything at mapper-configuration time — no bottom-of-file deferred imports needed.
- `ForeignKeyConstraint` (not `ForeignKey`) needed when the FK col is part of a composite PK (e.g. seller_profile.user_id, product_drafts composite PK).
- `export.py` got a V1 addition: `error_message TEXT` (not in V1_FEATURE_SPEC §4 DDL but required by §5.5.8 Celery task for failure surfacing).  Document this delta if coordinator asks.
- `catalog.py` has `category_id` as nullable FK (ON DELETE SET NULL) — not in original §2.4 DDL, but correct: the category is set when the seller picks a leaf, and the original §2.4 DDL already showed `category_id UUID REFERENCES categories(id)` without NOT NULL, so nullable is consistent.
- `Base` lives in `app.database` (already existed, well-commented).  `app.models.base` re-exports it.  Alembic `env.py` imports `Base` from `app.models` for autogenerate.

### pgcrypto dependency
All UUID PKs use `server_default=text("gen_random_uuid()")`.
pgcrypto extension must be enabled in Phase 2 baseline migration:
`CREATE EXTENSION IF NOT EXISTS pgcrypto;`
Supabase self-hosted image bundles pgcrypto — confirmed safe assumption.

### Pre-existing legacy models (not deleted)
The old model files `image.py` and `sku.py` still exist in `backend/app/models/` but are NOT imported from `__init__.py` and do NOT register tables with Base.  They are dead code.  Phase 2 coordinator task: confirm deletion OK or archive.  Do not delete them in Phase 1 without explicit coordinator instruction.

---

## Phase 2 — Alembic Baseline Migration COMPLETE (2026-06-05)

### Head revision
`935e55b4852c` — file: `backend/alembic/versions/935e55b4852c_v1_baseline_13_tables.py`
Applied to dev Postgres (`postgres-0`, namespace `dev`). Not applied to staging/prod.

### Legacy cleanup done
- Deleted `backend/app/models/sku.py` (pre-V1 dead code)
- Deleted `backend/app/models/image.py` (pre-V1 dead code)
- Deleted `backend/alembic/versions/2651e548010e_initial_schema.py` (pre-V1 schema, never applied)
- Post-deletion import check: `Base.metadata` still has 13 tables, import clean.

### alembic/env.py patched
- Removed `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` call.
  Reason: DATABASE_URL contains `%2F` and `%3D` (URL-encoded password chars) that trigger
  Python configparser `%`-interpolation errors when passed through `set_main_option`.
  Fix: use `create_async_engine(settings.DATABASE_URL, ...)` directly in `run_async_migrations()`,
  bypassing configparser entirely.  `run_migrations_offline()` already passes url= directly so it
  was unaffected.
  LESSON: Never route DATABASE_URL through configparser when it contains percent-encoded characters.

### Manual patches applied to autogenerated migration
Two patches were required:

1. **pgcrypto extension** — Prepended `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")`
   as the very first statement in `upgrade()`, before any `op.create_table()`.
   Reason: autogenerate never emits extension creates; `gen_random_uuid()` server_default on
   all 12 UUID-PK tables requires pgcrypto.
   Confirmed: Supabase self-hosted PG16 image has pgcrypto — applied cleanly.

2. **`drop_index` invalid kwarg** — Removed `postgresql_using='gin'` from the autogenerated
   `op.drop_index('idx_seller_profile_super_cats', ..., postgresql_using='gin')` in `downgrade()`.
   Reason: `op.drop_index()` does not accept `postgresql_using` — that kwarg is only valid on
   `op.create_index()`.  Autogenerate erroneously mirrors the create_index kwargs in the
   corresponding drop_index call.  Safe to drop — Postgres doesn't need the index type to drop.

### Autogenerate quality assessment
Everything else was generated correctly:
- JSONB server_defaults (`'{}'::jsonb`, `'{}'::text[]`) — present
- CHECK constraints (`ck_templates_compliance_shape`, `ck_product_images_order_idx`) — present
- `sa.Computed('order_idx = 1', persisted=True)` for `is_front` — present
- `sa.Identity(always=True)` for `audit_events.id` — present
- GIN index `postgresql_using='gin'` on `idx_seller_profile_super_cats` (upgrade) — present
- All 12 UUID PK server_defaults — present (after pgcrypto extension patch)
- ForeignKeyConstraint for composite PK tables — present
- Composite PK for product_drafts — present

### Drift check
Passed — clean. Drift check migration `79a8741a5d39` had `pass` in both upgrade() and downgrade().
Deleted the drift check file.

### pgcrypto on Supabase self-hosted PG16
CONFIRMED: `CREATE EXTENSION IF NOT EXISTS pgcrypto` succeeded on the K3s dev Supabase Postgres image.
`gen_random_uuid()` is available and functional.

---

## Phase 3 — Seed Scripts COMPLETE (2026-06-05)

### Files authored (all under `scripts/`)
| File | Purpose | LOC |
|---|---|---|
| `seed_field_aliases.py` | UPSERT field_aliases from canonical_field_aliases.json | 223 |
| `build_template_schemas.py` | Transform batch JSONs → templates (dedup by schema_hash) | 597 |
| `seed_categories.py` | UPSERT categories from meesho_category_tree.json | 205 |
| `seed_field_enum_values.py` | UPSERT field_enum_values from batch JSONs | 290 |
| `seed_all.py` | Orchestrator: runs all 4 in order, smoke checks, verification queries | 289 |

### Actual seeded row counts
| Table | Actual | Target | Status |
|---|---|---|---|
| `field_aliases` | 67 | 67 (exact) | OK |
| `templates` | 3,566 | 3,557 ±0.5% | OK (within [3539,3575]) |
| `categories` | 3,772 | 3,772 (exact) | OK |
| `field_enum_values` | 49,259 | 49,295 ±0.5% | OK (within [49048,49542]) |

### Intermediate artifact
`data/parsed/leaf_id_to_schema_hash.json` — 3,772-entry map produced by `build_template_schemas.py`
and consumed by `seed_categories.py` to look up `template_id` FKs.

### Schema hash strategy
Hash computed over all raw field properties EXCEPT `enum_values` (but INCLUDING `enum_count`,
`enum_source`, `help_text`, raw field name pre-alias normalisation).
- Full-with-enum_values → 3772 (every leaf unique due to per-category brand lists)
- Struct-only (name+dtype+marker+col+enum_count) → 3219 (too aggressive)
- Full-minus-enum_values → **3566** (within ±0.5% of 3557 target) — this is the one used

### compliance_shape discriminator
`templates.compliance_shape = 'collapsed'` when any field in the leaf's raw fields[] has a
`name` in: `{"Manufacturer Details", "Packer Details", "Importer Details"}`.
Exactly 1 template has `compliance_shape='collapsed'` (Eye-Serum, leaf 12378).

### Verified sample queries (on dev Postgres)
- `templates WHERE compliance_shape='collapsed'` = 1 (correct: Eye-Serum only)
- `field_aliases WHERE for_xlsx_export=TRUE` = 66 (all 67 variants are non-canonical; 1 would be
  canonical==variant if that ever occurred; in V1 data all 67 variants differ from their canonicals)
- `super_name, COUNT(*) top 5`: Home & Kitchen 816, Sports & Fitness 362, Grocery 321, Office Supplies 312, Kids & Toys 284
- `MAX(value_count) in field_enum_values` = 4,481 (matches SSoT §5: Compatible Models)

### Idempotency
Confirmed: second `seed_all.py` run produces identical row counts, no errors, no FK violations.
ON CONFLICT DO UPDATE on PKs (variant_name, schema_hash, meesho_leaf_id, composite(category_id+field_name)).

### Performance
Total seed pipeline wall time: ~40s for all 4 tables (~49K + 3.8K + 3.6K + 67 rows).
Bulk insert performance: ~2,600 rows/sec for field_enum_values (chunked at 500 rows).
Templates chunked at 50 rows due to large JSONB payloads (up to 71 fields × full schema objects).

### Data anomalies observed
1. **36 duplicate canonical field_name pairs per category** — two fields in the same leaf both
   map to the same canonical_name (alias collision). Handled: skip second occurrence, log at DEBUG.
   These are valid fields in the source that happen to share a canonical after normalisation.
2. **Category tree path includes leaf_name as last element** — the `path` array in
   `meesho_category_tree.json` already ends with `leaf_name`. DB path = `" > ".join(path)`.
   The dispatch brief's cheat-sheet said `path + [leaf_name]` which would be incorrect (double leaf).
3. **field_display_overrides.json uses `image_1_front` not `image_1`** as the override key for
   Image 1. In the batch JSON, the raw field name is "Image 1 (Front)" which slugifies to
   `image_1_front_`. The display override key mismatch is harmless — V1 simply falls back to
   title-case for image fields.
4. **`wrong_defective_returns_price` canonical** — the override file uses this key but the alias
   map has no explicit variant for it; the raw name "Wrong/Defective Returns Price" slugifies to
   `wrong_defective_returns_price` correctly without alias. Match works via slugify.

### Chunking pattern for large JSONB inserts
asyncpg/asyncio port-forward connections drop if a single statement is too large (>1000 params).
Use CHUNK_SIZE=50 for templates (4 cols × 50 rows = 200 params; safe margin).
Use CHUNK_SIZE=500 for field_enum_values (5 cols × 500 rows = 2500 params; safe for asyncpg).

---

## Phase 4 — Smoke Tests COMPLETE (2026-06-05)

### Files authored / patched
| File | Purpose | LOC |
|---|---|---|
| `backend/tests/conftest.py` | PATCHED — added dev_engine (session) + db (function, loop_scope=function) fixtures | +77 |
| `backend/tests/test_database.py` | NEW — 40 smoke tests across 8 categories | 621 |

### Test results (all pass)
- 40/40 tests pass — 0 failures
- Wall time: 83.05s
- Zero test data leaked to dev Postgres (all 9 mutable tables still at 0 rows post-run)
- Seeded reference counts unchanged: templates=3566, categories=3772, field_enum_values=49259, field_aliases=67

### Test categories and counts
| Category | Tests | Result |
|---|---|---|
| A. CRUD per table | 13 (one per model) | 13/13 pass |
| B. JSONB round-trip | 8 (one per JSONB column) | 8/8 pass |
| C. FK enforcement | 5 | 5/5 pass |
| D. Unique constraint enforcement | 3 | 3/3 pass |
| E. CHECK constraint enforcement | 2 | 2/2 pass |
| F. Computed column (is_front) | 2 | 2/2 pass |
| G. Server-default verification | 3 | 3/3 pass |
| H. Seeded data sanity (read-only) | 4 | 4/4 pass |
| Total | 40 | 40/40 |

### Real schema bugs surfaced
None. All constraints, defaults, and computed columns behaved exactly as modeled.

### Critical gotcha: pytest-asyncio 0.24 + asyncpg loop scoping
Problem: pytest.ini has asyncio_default_fixture_loop_scope = session.
SESSION-scoped async fixtures run in the session event loop.
FUNCTION-scoped tests and fixtures run in a per-test function-scoped loop.
asyncpg Protocols attach Futures to the event loop running when the connection is established.
Cross-scope access raises: RuntimeError: Task got Future attached to a different loop

Fix (canonical for this project):
  Use @pytest_asyncio.fixture(loop_scope="function") on the db fixture.
  Create a fresh NullPool engine INSIDE the fixture body.
  Every engine/connection/Protocol/Future is created and disposed within the same function loop.

Pattern for future test files that need transaction rollback:
  @pytest_asyncio.fixture(loop_scope="function")
  async def db() -> AsyncSession:
      eng = create_async_engine(DEV_URL, poolclass=NullPool, echo=False)
      try:
          async with eng.connect() as conn:
              await conn.begin()
              Session = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
              session = Session()
              try:
                  yield session
              finally:
                  await session.close()
                  await conn.rollback()
      finally:
          await eng.dispose()

For read-only session-scoped fixtures (section H pattern), session-scoped NullPool engine works
because there is no SQLAlchemy async greenlet switching — plain conn.execute(text(...)) only.

### Timestamp comparison tolerance
test_server_default_created_at uses 30s tolerance for created_at vs local now().
Port-forward adds ~5ms latency. 30s is safe. Do not tighten below 10s without on-cluster access.

### Conftest app.main guard
Legacy routers (catalogs.py, skus.py, images.py) still import deleted models (app.models.image, app.models.sku).
conftest.py guards the import with try/except. client and auth_client fixtures call pytest.skip() when app is None.
api-routes-builder must delete or rewrite those legacy routers before route tests can run.

### Final database track summary
- 13 tables validated against PG16 (Supabase self-hosted, K3s dev namespace)
- Baseline migration: 935e55b4852c
- Seed counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
- All 40 smoke tests pass, zero test data leakage
- DATABASE TRACK COMPLETE — ready for backend API track

---

---

## Phase 5 — Code-side Gap Fixes (G6, G7, G10-index) COMPLETE (2026-06-05)

### New head revision
`f31c75438e61` — `backend/alembic/versions/f31c75438e61_add_idx_product_drafts_saved_at.py`
Parent: `a1b2c3d4e5f6` (pg_trgm + category GIN indexes, applied by another agent between Phase 4 and Phase 5).
Applied to dev Postgres.

Note on `a1b2c3d4e5f6`: This revision was authored by database-builder in Session 2 (G4 gap pass).
It adds pg_trgm GIN indexes on categories (idx_categories_leaf_name_trgm, idx_categories_path_trgm,
idx_categories_super_name_trgm). These indexes are NOT declared in the Category ORM model.
`alembic revision --autogenerate` always reports these 3 as "removed" — that is expected drift,
not an error. Do NOT attempt to drop those indexes; they are live and required for the browse endpoint.

### Files created
| File | Purpose | LOC |
|---|---|---|
| `backend/app/i18n/__init__.py` | Package init with docstring explaining the versioning discipline | 16 |
| `backend/app/i18n/step_assignment.py` | STEP_ASSIGNMENT + STEP_ORDER + assign_step() + RULESET_VERSION="v1" | 108 |
| `backend/app/i18n/primitive_classifier.py` | UNIT_KEYWORDS + CURRENCY_PATTERNS + LONG_PATTERNS + classify_primitive() + CLASSIFIER_VERSION="v1" | 116 |
| `backend/tests/test_step_assignment.py` | 23 tests (3 smoke + 15 parametrised regression + 5 edge case) | 120 |
| `backend/tests/test_primitive_classifier.py` | 33 tests (4 smoke + 15 parametrised regression + 14 edge case) | 152 |
| `backend/alembic/versions/f31c75438e61_add_idx_product_drafts_saved_at.py` | G10 migration — idx_product_drafts_saved_at on saved_at | 45 |

### Files modified
- `scripts/build_template_schemas.py`: inline STEP_ASSIGNMENT/STEP_ORDER removed; classify_primitive()
  and assign_step_id() now delegate to i18n modules. Canonical source is backend/app/i18n/.
- `backend/app/models/product_draft.py`: Added Index("idx_product_drafts_saved_at", "saved_at") to
  __table_args__ so future autogenerate stays in sync.

### Test results
- test_step_assignment.py: 23/23 PASS
- test_primitive_classifier.py: 33/33 PASS
- test_database.py (Phase 4 suite): 40/40 PASS (no regression)
- Total: 96/96 tests pass

### Re-seed verification
- alembic current: f31c75438e61 (head)
- product_drafts has idx_product_drafts_saved_at btree (saved_at)
- seed_all.py re-run counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259 (identical)
- Spot-check: schema_hash=a315f724... → product_name step_id=basics primitive=text_short (IDENTICAL pre/post)
- CONCLUSION: Refactor is behavior-preserving. No schema_jsonb drift.

### backend/app/i18n/ pattern (for future agents)
- Versioned rule modules under backend/app/i18n/ for any constant/function driving schema_jsonb shape.
- Each module MUST have a *_VERSION constant (start "v1"; bump on any rule change).
- Seed script MUST import from these modules — never define constants inline in scripts/.
- Regression tests MUST pin ~15+ canonical tuples covering all output values.
- Bumping a version = re-seed + confirm row counts + spot-check schema_jsonb intentionally changed.

### Gotcha: autogenerate false positives for GIN trgm indexes
Migration a1b2c3d4e5f6 (database-builder, Session 2) added GIN trgm indexes on categories without
updating the Category ORM model (ORM models are intentionally not updated for indexes added in
post-baseline migrations). Autogenerate will always report idx_categories_*_trgm as "removed" in
future drift checks. When you see these 3 as false positives, discard them — the indexes are real
and correct, just not reflected in the ORM metadata.

---

---

## Session 2 Gap Pass — G4+G1 COMPLETE (2026-06-05)

### Revision authored
`a1b2c3d4e5f6` — `backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py`
This revision was authored by this agent (database-builder) in Session 2, NOT api-routes-builder
(prior Phase 5 note was in error).

### CONCURRENTLY in Alembic async — working pattern (IMPORTANT)

`op.get_context().autocommit_block()` + `transaction_per_migration=True` in env.py.

Required env.py change (already applied):
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    transaction_per_migration=True,  # required for autocommit_block() to work correctly
)
```

Migration pattern:
```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # inside transaction — OK
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_path_trgm ON categories USING GIN (path gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_leaf_name_trgm ON categories USING GIN (leaf_name gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_super_name_trgm ON categories USING GIN (super_name gin_trgm_ops)")
```

Failed approaches (do NOT retry):
1. `conn.execution_options(isolation_level="AUTOCOMMIT")` — fails if transaction already begun
2. `engine.raw_connection()` + cursor.execute() — asyncpg shim carries transaction; CONCURRENTLY silently no-ops
3. `conn.execute(sa.text("COMMIT"))` before CONCURRENTLY — asyncpg prepare-execute protocol blocks it

### is_advanced wiring — confirmed correct, no code changes needed
ADVANCED_CANONICAL_NAMES = {"group_id"} at line 84 of scripts/build_template_schemas.py (D2-locked).
3566 templates have group_id field with is_advanced=true. 0 templates have product_name as advanced.

### CRITICAL: is_advanced JSONB test query pattern
The LIKE pattern `schema_jsonb::text LIKE '%"canonical_name": "product_name"%' AND '%"is_advanced": true%'`
gives false positives — both strings match anywhere in the JSON blob. Use jsonb_array_elements instead:
```sql
SELECT count(*) FROM templates t
WHERE EXISTS (
    SELECT 1 FROM jsonb_array_elements(t.schema_jsonb -> 'fields') AS f
    WHERE f->>'canonical_name' = 'product_name'
    AND (f->>'is_advanced')::boolean = true
)
```

### Parallel migration chain awareness
Always run `alembic current` before `downgrade -1`. The -1 flag goes one step back from CURRENT head.
If other agents have applied migrations since your revision, -1 undoes their work, not yours.
Full chain as of this session: 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61

### Test suite
42/42 tests pass (was 40/40 after Phase 4; Phase 5 added more; +2 is_advanced tests in Session 2)

---

## Session 3 — GIN trgm ORM sync (2026-06-05)

### Task
Sync `backend/app/models/category.py` with migration `a1b2c3d4e5f6` by declaring the
3 GIN trigram indexes in `Category.__table_args__` so autogenerate no longer emits
false-positive drop_index operations.

### GIN trigram index declaration pattern (canonical)

```python
Index(
    "idx_categories_path_trgm",
    "path",
    postgresql_using="gin",
    postgresql_ops={"path": "gin_trgm_ops"},
),
Index(
    "idx_categories_leaf_name_trgm",
    "leaf_name",
    postgresql_using="gin",
    postgresql_ops={"leaf_name": "gin_trgm_ops"},
),
Index(
    "idx_categories_super_name_trgm",
    "super_name",
    postgresql_using="gin",
    postgresql_ops={"super_name": "gin_trgm_ops"},
),
```

Key: `postgresql_ops` is a dict keyed by column name string (NOT the column object).
`postgresql_using="gin"` is the access method kwarg.

### Drift check result
`alembic revision --autogenerate -m "drift_check_should_be_empty"` produced
`pass` in both `upgrade()` and `downgrade()`. No-op file deleted. Drift is clean.

### Test suite after change
98/98 pass (was reported as 96/96 in prior phases; Session 2 G4 pass added 2 more tests).
All 98 pass with no regression.

### api-routes-builder migration a1b2c3d4e5f6 ORM sync
Migration `a1b2c3d4e5f6` (pg_trgm + 3 GIN indexes on categories) is now fully
ORM-synchronized. Future autogenerate runs will not report these indexes as drift.

---

---

## Phase 7 — DATABASE_ARCHITECTURE.md authored (2026-06-05)

### Canonical reference doc
`docs/DATABASE_ARCHITECTURE.md` is the single source of truth for the as-built MeeSell
database. It supersedes `docs/MVP_ARCHITECTURE.md` §2 for column-level DDL. It is 1,669 LOC,
14 sections.

### Section ownership map
| Section | Content | Phase/Dispatch that established it |
|---|---|---|
| §0 | Purpose + cross-references | Phase 7 (this dispatch) |
| §1 | High-level overview | Phase 7 — compiled from Phases 1-6 |
| §2.1-2.13 | Table-by-table (as-built) | Phase 7 — sourced from ORM models |
| §3 | ER diagram + cascade chains | Phase 7 |
| §4.1-4.9 | JSONB column contracts | Phase 7 — previously undocumented |
| §5 | Index inventory (44 indexes) | Phase 7 — compiled from ORM + migrations |
| §6 | Migration chain history | Phase 7 — sourced from alembic/versions/ |
| §7 | Seed pipeline architecture | Phase 7 — sourced from scripts/ + MEMORY |
| §8 | Connection patterns | Phase 7 — sourced from database.py + env.py |
| §9 | Multi-tenancy model | Phase 7 |
| §10 | Audit log + autosave | Phase 7 — cross-ref to MVP_ARCHITECTURE §10 |
| §11 | Testing strategy | Phase 7 — sourced from conftest.py + test files |
| §12 | Operational invariants | Phase 7 — sourced from MEMORY + seed smoke checks |
| §13 | V1 trade-offs + deferrals | Phase 7 |
| §14 | Maintenance + handoff | Phase 7 |

### Key decisions documented in this file
1. `docs/DATABASE_ARCHITECTURE.md` supersedes `MVP_ARCHITECTURE.md §2` for column-level DDL.
   Data-engineer should update §2 using this doc as source (G1, G2, G4, G11 gap items).
2. JSONB column contracts (Section 4) were previously undocumented anywhere — this is the
   canonical location. Any code writing JSONB must reference these shapes.
3. Section 5 lists 44 indexes total. After any migration, verify count with:
   `SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';`
4. K3s cluster API server at 34.180.58.185:6443 was unreachable during Phase 7 (connection
   refused). Live DB verification via `kubectl exec` was blocked. Schema documentation was
   verified entirely against ORM source files (which are the ground truth).

### Maintenance reminder
Every future dispatch that touches a model, migration, or seed MUST also update
`docs/DATABASE_ARCHITECTURE.md`. The doc will drift if this is not enforced.
Specifically: add a row to the Section 5 index table, add a new §2.N subsection for new
tables, update the head revision in Section 1 and Section 6.

---

## Memory index
| Entry | Type | Summary |
|---|---|---|
| Phase 1 complete | project | 13 ORM models authored, all schema deltas applied, imports verified |
| Phase 2 complete | project | Baseline migration 935e55b4852c applied, 13 tables + alembic_version in dev |
| Phase 3 complete | project | 5 seed scripts, all smoke checks passed, idempotency confirmed |
| Phase 4 complete | project | 40 smoke tests pass, 0 data leaked, all DB properties validated |
| Phase 5 complete | project | G6+G7 i18n modules + G10 index migration f31c75438e61; 96/96 tests pass; re-seed identical |
| Session 2 G4+G1 complete | project | a1b2c3d4e5f6 migration (pg_trgm + GIN indexes); is_advanced confirmed; 42/42 tests pass |
| Session 3 GIN trgm ORM sync | project | category.py synced with a1b2c3d4e5f6; autogenerate clean; 98/98 tests pass |
| Phase 7 DB architecture doc | project | docs/DATABASE_ARCHITECTURE.md authored (1669 LOC, 14 sections); canonical reference from here forward |
| GIN trigram index declaration pattern | reference | Index(..., postgresql_using="gin", postgresql_ops={"col": "gin_trgm_ops"}) — ops dict keyed by col name string |
| CONCURRENTLY in Alembic async | reference | Use autocommit_block() + transaction_per_migration=True in env.py — see Session 2 section |
| is_advanced JSONB query pattern | reference | Use jsonb_array_elements operator; LIKE gives false positives on nested arrays |
| backend/app/i18n/ pattern | reference | Versioned rule modules for seed pipeline constants; *_VERSION bump on any change; regression tests required |
| autogenerate trgm false positives | reference | RESOLVED in Session 3 — indexes now declared in ORM; no more false positives |
| env.py configparser fix | reference | Never use set_main_option for URLs with % chars — use create_async_engine directly |
| drop_index + postgresql_using | reference | op.drop_index() does NOT accept postgresql_using kwarg — autogenerate bug, remove it |
| pgcrypto confirmed on Supabase PG16 | reference | CREATE EXTENSION IF NOT EXISTS pgcrypto works; gen_random_uuid() available |
| Computed() for generated columns | reference | Correct SA 2.0 pattern for GENERATED ALWAYS AS ... STORED |
| Circular import pattern | reference | from __future__ + TYPE_CHECKING + init order — no bottom-of-file hacks |
| Schema hash strategy (Phase 3) | reference | Full-minus-enum_values gives 3566 within tolerance; see Phase 3 section |
| compliance_shape discriminator | reference | collapsed if leaf contains "Manufacturer Details" | "Packer Details" | "Importer Details" |
| JSONB chunk size pattern | reference | CHUNK_SIZE=50 for templates; CHUNK_SIZE=500 for field_enum_values |
| category tree path anomaly | reference | path array already includes leaf_name as last element — do NOT append leaf_name again |
| pytest-asyncio 0.24 loop scope | reference | Use loop_scope="function" + fresh NullPool engine per test — see Phase 4 section |
| Timestamp tolerance for created_at | reference | 30s tolerance is safe for port-forward latency; do not tighten below 10s |
| Conftest app.main guard | reference | Legacy routers import deleted models — try/except guard + pytest.skip in client fixture |
| DATABASE_ARCHITECTURE.md canonical | reference | docs/DATABASE_ARCHITECTURE.md supersedes MVP_ARCHITECTURE §2 for DDL; update on every schema change |
| JSONB shapes in §4 | reference | All 9 JSONB column contracts documented in DATABASE_ARCHITECTURE.md §4 — canonical location |
| K3s unreachable during Phase 7 | feedback | kubectl exec / port-forward verification blocked; documented in memory; all schema facts sourced from ORM files |

## MS Sub-Plan A Phase A — svc-export Alembic schema-split COMPLETE (2026-06-12)

### Scope
Sub-session dispatched by `meesell-backend-coordinator` per `spec_msA_backend.md` §3.C. Task: author and validate the standalone Alembic migration chain for `svc-export`, effecting the `public.exports` → `export.exports` schema move called for by MASTER_PLAN §2.D (schema-per-service isolation, V1.5 prep). Commit 5747189 on `feature/microservices-export/backend` (worktree `/tmp/mesell-wt/msA-backend/`).

### What was built (4-file standalone chain)

| File | Path | Purpose |
|---|---|---|
| `alembic.ini` | `backend/services/svc-export/alembic.ini` | Standalone chain config. `sqlalchemy.url` intentionally blank — URL injected via `DATABASE_URL` env var to avoid configparser `%`-interpolation. `script_location = alembic`. |
| `env.py` | `backend/services/svc-export/alembic/env.py` | Async env with `version_table_schema="export"` — the chain's version row lands in `export.alembic_version`, not `public.alembic_version`. `target_metadata = None` (hand-authored DDL only). `transaction_per_migration=True`. |
| `script.py.mako` | `backend/services/svc-export/alembic/script.py.mako` | Standard Alembic mako template (unmodified default). |
| `e7a3c1f9b42d_move_exports_to_export_schema.py` | `backend/services/svc-export/alembic/versions/` | Revision `e7a3c1f9b42d`, `down_revision=None` (root of chain). |

`upgrade()`: (1) Risk#5 integrity pre-scan — orphaned `exports.user_id` count; raises `RuntimeError` with up to 20 detail rows on non-zero (hard abort, no partial move); (2) `CREATE SCHEMA IF NOT EXISTS export`; (3) `ALTER TABLE public.exports SET SCHEMA export`. `downgrade()`: `ALTER TABLE export.exports SET SCHEMA public`.

### Monolith head status
`f31c75438e61` — UNCHANGED. The two chains are fully independent (different version tables in different schemas).

### Validated round-trip (local Homebrew Postgres 16.11 — NOT the dev tunnel)
Dev tunnel down (`nc -zv localhost 5433` refused). Scratch DB `meesell_svc_export_test` seeded with valid users/exports pair. Results: upgrade → `e7a3c1f9b42d (head)` in export schema, `public.exports` gone, `export.exports` + `export.alembic_version` present; orphan-abort test PASSED (RuntimeError, clean rollback); downgrade restored `public.exports`; full round-trip PASSED.

### Critical env.py gotcha — schema must exist BEFORE context.configure()
Alembic's `_ensure_version_table()` runs at `context.configure()` time and needs `export.alembic_version` creatable — if the schema doesn't exist yet, Postgres errors before any migration code runs. Fix (load-bearing): in `do_run_migrations()`, execute `CREATE SCHEMA IF NOT EXISTS export` + `connection.commit()` BEFORE `context.configure(...)`. The commit is required so the schema DDL is visible to configure-time internal queries (asyncpg implicit-transaction visibility).

### Reusable schema-split recipe (for waves MS-2..5)
1. `backend/services/<svc>/alembic.ini` with `sqlalchemy.url =` blank — URL via env var only (configparser `%`-interpolation trap).
2. `env.py`: `version_table_schema="<svc_schema>"` (one distinct schema per chain, never reuse); `target_metadata = None` unless the service owns its own ORM Base; `transaction_per_migration=True`; `CREATE SCHEMA IF NOT EXISTS <svc_schema>` + `connection.commit()` at top of `do_run_migrations()` BEFORE `context.configure()`.
3. First migration: `down_revision = None` (root); `ALTER TABLE public.<table> SET SCHEMA <svc_schema>`.
4. Local Homebrew PG16 is a valid validation substitute when the dev tunnel is down — identical DDL behavior to K3s Supabase PG16 for these operations.
5. Risk#5 pattern: always pre-scan FK integrity before a schema move; `SELECT COUNT(*) ... WHERE NOT EXISTS (...)` + raise on non-zero + emit up to 20 detail rows.

### Memory index entry
| Entry | Type | Summary |
|---|---|---|
| MS Sub-Plan A Phase A svc-export schema-split | project | 4-file standalone Alembic chain; head e7a3c1f9b42d; version_table_schema="export"; monolith head f31c75438e61 unchanged; round-trip validated on local Homebrew PG 16.11 |
| schema-split env.py gotcha | reference | CREATE SCHEMA + commit MUST precede context.configure() — _ensure_version_table() needs schema visible at configure time |
| schema-split recipe for MS-2..5 | reference | version_table_schema per service; blank sqlalchemy.url; Risk#5 orphan-abort pattern; commit DDL before context.configure() |

---

## MS Sub-Plan B Phase A — svc-dashboard DB attestation B4 (2026-06-13) [meesell-database-builder AUTHORITATIVE]

### Scope
VERIFY-ONLY task. Independently verified (as the correct meesell-database-builder owner per CLAUDE.md rule 1) that the dashboard module (`backend/app/modules/dashboard/`) owns ZERO tables and introduces NO Alembic chain. Worktree: `/tmp/mesell-wt/msB-backend/`, source commit `98f6a96`.

### Evidence — all 6 files read in full + grep results

Files confirmed present and read:
- `__init__.py` (lines 1-37): module docstring + `from app.modules.dashboard.router import router as dashboard_router`. No imports from SQLAlchemy, alembic, or any DB layer.
- `domain.py` (lines 1-41): post-§13.A.1 amendment — intentionally empty (`__all__: list[str] = []`). Only `from __future__ import annotations`. No ORM, no DB.
- `exceptions.py` (lines 1-62): `DashboardError` + `InvalidPaginationError` both subclass `app.core.errors.MeesellError`. No DB access, no SQLAlchemy imports.
- `schemas.py` (lines 1-98): 4 Pydantic v2 models (`DashboardQuery`, `ProductListItem`, `ProfileCompletenessSummary`, `DashboardResponse`). `from pydantic import BaseModel` only — NOT SQLAlchemy Base.
- `router.py` (lines 1-131): `GET /api/v1/products` handler. `db: Annotated[AsyncSession, Depends(get_db)]` declared as FastAPI DI parameter; immediately forwarded to `dashboard_service.list_products_for_dashboard(user_id=..., query=..., db=db)` at line 124-128 — no direct query.
- `service.py` (lines 1-150): `list_products_for_dashboard` makes exactly 2 awaits: `catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)` (line 78) and `customer_service.get_onboarding_completeness(user_id=user_id, db=db)` (line 84-87). `_compose_response` is pure (no I/O, no await, no DB). `db` is never used to execute any query in this file.

#### Grep results (file:line evidence)

**SQLAlchemy ORM terms** (`Base`, `__tablename__`, `Mapped[`, `mapped_column`, `Column(`, `declarative_base`):
- `schemas.py:25` — `from pydantic import BaseModel, ConfigDict, Field` (Pydantic, NOT SQLAlchemy)
- `schemas.py:28,42,61,81` — class definitions `(BaseModel)` (Pydantic, NOT SQLAlchemy)
- `exceptions.py:35` — prose docstring "Base class for dashboard module failures" (English prose, NOT SQLAlchemy Base)
- Result: ZERO SQLAlchemy ORM hits

**Alembic terms** (`op.`, `revision`, `down_revision`, `alembic`):
- Result: NO MATCHES (zero hits across all 6 files)

**Raw query execution** (`select(`, `.execute(`, `scalars`, `scalar_one`, `fetchall`, `fetchone`, `text(`, `db.`, `session.`):
- Result: NO MATCHES (zero hits in `service.py`; `db` parameter appears only in function signatures as `AsyncSession` type annotation, never as a call site)

#### Structural checks
- `repository.py`: DOES NOT EXIST in `/tmp/mesell-wt/msB-backend/backend/app/modules/dashboard/` — deliberate §13.D deviation confirmed.
- `backend/services/`: contains only `svc-export/` — `svc-dashboard/` DOES NOT EXIST.
- `backend/alembic/versions/`: 3 files — `935e55b4852c_v1_baseline_13_tables.py`, `a1b2c3d4e5f6_pg_trgm_and_category_gin.py`, `f31c75438e61_add_idx_product_drafts_saved_at.py`. The word "dashboards" appears only at `f31c75438e61_add_idx_product_drafts_saved_at.py:10` in prose: "staleness dashboards, manual cleanup runs during V1" — zero schema action related to any dashboard table.
- Monolith Alembic head: `f31c75438e61` — UNCHANGED.

### Learning (§13.D pattern for future reference)
When a module is a pure consumer (leaf in the §2.D dependency matrix) that composes results from two other modules' service functions, the correct database-builder stance is to author NO migration, NO model file, NO Alembic chain, and NO repository.py — the §13.D structural deviation is load-bearing, not an oversight. The verification discipline for such modules is: grep for `__tablename__`, `Mapped[`, `Base`, `alembic` across the subtree (must all be zero for ORM / migration terms); confirm `AsyncSession` appears only as a forwarded parameter, never as a query-issuing call site; confirm no `repository.py` exists; confirm no entry in `backend/services/`. This pattern generalises to any future "view-only aggregation" module (e.g., a reporting module that reads from catalog + pricing).

### Memory index entry
| Entry | Type | Summary |
|---|---|---|
| MS-B B4 svc-dashboard DB attestation (AUTHORITATIVE) | project | meesell-database-builder owner; ZERO tables, ZERO migrations, ZERO model files, NO repository.py; monolith head f31c75438e61 unchanged; verified @ commit 98f6a96; all 6 files read + grep evidence at file:line |
| §13.D no-repository pattern | reference | Pure consumer modules own no DB objects; AsyncSession forwarded not queried; grep __tablename__/Mapped[/Base to confirm clean; generalises to any aggregation-only module |
