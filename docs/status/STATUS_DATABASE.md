# STATUS — DATABASE

**Owner:** DATABASE sub-session (mesell-database-session-1)
**Last update:** 2026-06-05 (extended — pg_trgm + 3 GIN trgm indexes + idx_product_drafts_saved_at; tests 40 → 42)
**Coordinator:** master session (direct dispatch — sanctioned exception, no backend-coordinator hop)
**Primary agent:** `meesell-database-builder` (Sonnet)

**Status:** 🟢 DATABASE TRACK COMPLETE — head `f31c75438e61` (baseline `935e55b4852c` → pg_trgm/GIN `a1b2c3d4e5f6` → `idx_product_drafts_saved_at`). 42/42 smoke tests pass. Drift clean. Ready for API track hand-off.

## Current Phase
ALL 4 PHASES DONE — track complete 2026-06-05 ~00:40 IST; extended same day with §7 Search GIN indexes + §10 autosave index per BACKEND_ARCHITECTURE alignment.

## Phase Plan (founder pre-authorized full sequential execution — completed overnight)
- **Phase 0:** ✅ DONE — all 8 context files read, Postgres confirmed live, seed inputs verified.
- **Phase 1:** ✅ DONE — 13 SQLAlchemy 2.0 async ORM models in `backend/app/models/` (1,542 LOC, import-verified).
- **Phase 2:** ✅ DONE — Alembic baseline `935e55b4852c` applied on dev; 13 tables + alembic_version; drift check clean; pgcrypto enabled.
- **Phase 3:** ✅ DONE — 5 seed scripts; reference data live; idempotency confirmed; counts within ±0.5% of SSoT.
- **Phase 4:** ✅ DONE — 40/40 pytest smoke tests pass (CRUD × 13, JSONB × 8, FK × 5, UNIQUE × 3, CHECK × 2, computed × 2, defaults × 3, seed sanity × 4); 83s wall time; zero test data persisted.

## Morning Briefing Block (founder reads this)

**Database is fully validated and seeded on dev. Three things to know before starting the API track:**

1. **Schema is locked at revision `935e55b4852c`.** 13 tables + alembic_version. Drift check clean. pgcrypto enabled.

2. **Reference data is live and immutable** (until quarterly Meesho refresh):
   - 67 field_aliases (with `for_xlsx_export` markers for round-trip)
   - 3,566 templates (1 collapsed-compliance — Eye-Serum)
   - 3,772 categories (exact match to SSoT)
   - 49,259 field_enum_values (max enum size 4,481 — Compatible Models, matches SSoT)

3. **Legacy router files will block FastAPI startup.** During Phase 1 the builder deleted `models/sku.py` and `models/image.py` (pre-V1 schemas). But `backend/app/routers/catalogs.py`, `routers/skus.py`, `routers/images.py` still import them. **First action of the API track must be: delete or rewrite these 3 legacy routers before any route-level work starts.** Other routers in `backend/app/routers/` (`auth.py`, `exports.py`, `generation.py`, `pricing.py`, `quality.py`, `research.py`) may have similar issues — to be evaluated by api-routes-builder.

**What the next track unlocks:**
- `meesell-api-routes-builder`: wire `/api/v1/categories/*`, `/api/v1/categories/{id}/schema`, `/api/v1/categories/{id}/field-enum/{name}`, `/api/v1/seller-profile/*` against the live ORM
- `meesell-services-builder`: implement Export Adapter, service-layer query patterns against templates/categories/field_enum_values
- `meesell-ai-coordinator`: Smart Picker can hit `categories.suggest` with real data; enum-constrained Auto-fill can pull `enum_entries` from real `field_enum_values`

**Test fixture pattern (reusable):** `backend/tests/conftest.py` has the `db` fixture using transaction-rollback. Use it for service-layer tests too. `loop_scope="function"` + per-fixture NullPool engine avoids pytest-asyncio 0.24 cross-loop bugs.

---

## Phase 5 — Code-side gap fixes (G6, G7, G10-index) — COMPLETE 2026-06-05

**Status:** All 3 code-side database gaps resolved. Doc-side gaps (G1, G2, G4, G11) and decision-bound gaps (G10 TTL value, G12 keying) deferred — need data-engineer dispatch + founder ruling respectively.

### Done
- **G6 (code-lock STEP_ASSIGNMENT):** `backend/app/i18n/step_assignment.py` (108 LOC) — RULESET_VERSION="v1", 13 patterns, `assign_step()` function. `scripts/build_template_schemas.py` now imports from here.
- **G7 (code-lock primitive classifier):** `backend/app/i18n/primitive_classifier.py` (116 LOC) — CLASSIFIER_VERSION="v1", `classify_primitive()` with constants. Seed script imports from here.
- **G10 (index part):** new Alembic revision `f31c75438e61` adds `idx_product_drafts_saved_at` btree index on `product_drafts.saved_at`. Model updated. Applied to dev. (TTL value + Celery beat task still pending founder ruling + services-builder dispatch.)
- **Regression tests:** 56 new tests (23 step_assignment + 33 primitive_classifier) — all green
- **Phase 4 tests still pass:** 40/40
- **Total test count on database track: 96/96 green**

### Re-seed idempotency verification
- `alembic current` shows `f31c75438e61` (head)
- `seed_all.py` re-run row counts UNCHANGED: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
- Sample `templates.schema_jsonb` field spot-check: identical before/after refactor → refactor is **behavior-preserving**
- Eye-Serum invariant holds: 1 collapsed-compliance template
- Max enum size invariant: 4,481

### Cross-track issue surfaced (flagged for master session)

**Migration `a1b2c3d4e5f6` (pg_trgm and category GIN indexes) was created by `meesell-api-routes-builder` between Phases 4 and 5 — outside the database track scope.**

- The migration itself is CORRECT — implements §7.4 MVP_ARCHITECTURE (pg_trgm extension + 3 GIN indexes on `categories.path`, `categories.leaf_name`, `categories.super_name`)
- All 3 indexes confirmed present on dev: `idx_categories_path_trgm`, `idx_categories_leaf_name_trgm`, `idx_categories_super_name_trgm`
- BUT the corresponding ORM model `backend/app/models/category.py` was NOT updated to declare these indexes in `__table_args__`
- Consequence: every future `alembic revision --autogenerate` reports these 3 indexes as "removed" — false positives that will noise up future migrations

**Scope question:** `backend/app/models/` is owned by `meesell-database-builder` per spec (Scope IN). The api-routes-builder editing models is technically out of their scope.

**Recommendation:** quick fix dispatch to database-builder — add 3 `Index(...)` lines to `category.py.__table_args__` (5-min edit). OR if api-routes-builder is now authorized to touch models, document the scope expansion.

**Recommended owner:** founder rules. Database track is paused on this drift question — autogenerate noise is non-blocking for now but should be cleaned before the next schema migration.

### Phase 6 — Cross-track drift fix (2026-06-05) — RESOLVED

Founder ruled option 1. Database-builder dispatched for a 5-min sync.

**Done:**
- `backend/app/models/category.py.__table_args__` extended with 3 `Index(...)` declarations for the GIN trigram indexes (`idx_categories_path_trgm`, `idx_categories_leaf_name_trgm`, `idx_categories_super_name_trgm`) using `postgresql_using="gin"` + `postgresql_ops={"...": "gin_trgm_ops"}` pattern
- Existing 3 B-tree indexes preserved
- Drift check: EMPTY (autogenerate upgrade/downgrade both `pass`) — false-positive eliminated
- Test suite: 98/98 still pass (track total grew from 96 to 98 — 2 additional is_advanced tests added during Phase 5 follow-up)

**Outcome:** ORM and migration history are now back in sync. Any future `alembic --autogenerate` will produce a clean revision on first run. The api-routes-builder's `a1b2c3d4e5f6` migration stays unchanged (correct as authored).

**Cross-track scope question still open for founder:** is api-routes-builder authorized to create migrations / edit models, or should they stay in their lane (routes only)? Recommendation: keep model + migration ownership with database-builder. If api-routes-builder needs a schema change, they request via STATUS file and database-builder executes.

### Phase 7 — Canonical reference doc (2026-06-05) — COMPLETE

**Done:** `docs/DATABASE_ARCHITECTURE.md` authored (73 KB, 1,669 LOC, 14 sections).

**Contents:**
- §0–§1: Purpose + stack + 13-table overview
- §2: Table-by-table reference (13 subsections — current as-built columns supersede MVP §2 stale entries)
- §3: Mermaid ER diagram + cascade chains
- §4: 9 JSONB column contracts with shape specs, examples, write/read paths
- §5: Full index inventory (44 indexes — verified against live DB)
- §6: Migration chain history (3 revisions + how-to-create rules + gotchas)
- §7: Seed pipeline architecture (diagram, bridge artifact, idempotency contract, smoke gates)
- §8: Connection patterns (port-forward, URL-encoding gotcha, async session factory)
- §9: Multi-tenancy model (per-table user_id scope map)
- §10: Audit log + autosave lifecycle
- §11: Testing strategy (98 tests, transaction-rollback fixture, pytest-asyncio gotcha)
- §12: 9 operational invariants with runnable SQL — VERIFIED LIVE on dev
- §13: V1 trade-offs + V1.5 deferrals
- §14: Maintenance rules + cross-track scope ruling + open doc gaps

**Live invariant verification (post-doc):**
| Invariant | Expected | Live | Status |
|---|---|---|---|
| templates count | 3,566 ±0.5% | 3,566 | ✅ |
| categories count | 3,772 exact | 3,772 | ✅ |
| field_enum_values count | 49,259 ±0.5% | 49,259 | ✅ |
| field_aliases count | 67 exact | 67 | ✅ |
| collapsed-compliance templates | 1 (Eye-Serum) | 1 | ✅ |
| max enum size | 4,481 (Compatible Models) | 4,481 | ✅ |

**Hand-off:** all downstream agents (api-routes-builder, services-builder, ai-coordinator) should read `docs/DATABASE_ARCHITECTURE.md` BEFORE touching schema or storage. This prevents repeats of the Phase 6 cross-track drift incident.

### NEW GAP SURFACED — G19 (track-internal, not blocking)

**G19 — Redundant index on `categories.meesho_leaf_id`**

Discovered during Phase 7 documentation. Live schema has TWO btree indexes on the same column:
- `categories_meesho_leaf_id_key` (UNIQUE, auto-generated by SQLAlchemy from `unique=True` on the column)
- `idx_categories_meesho_leaf` (manually declared in `__table_args__`)

Both target `meesho_leaf_id`. The UNIQUE constraint is enforced by the auto-named index; the manual one is redundant index bloat.

**Severity:** NON-BLOCKER (correctness unaffected; only storage + write amplification cost)
**Source:** Phase 1 model authoring — declared both because SSoT §6 says "index on meesho_leaf_id" and the unique constraint already creates one
**Proposed fix:** Drop `idx_categories_meesho_leaf` in a future migration; keep only `ix_categories_meesho_leaf_id` (the UNIQUE one). Update `category.py` `__table_args__` to remove the manual declaration.
**Owner:** meesell-database-builder (5-min fix when convenient)
**Effort:** S (15 min including new Alembic revision + apply)
**Defer:** to next batch of schema cleanup (with G10 TTL infrastructure or G12 ruling-driven changes)

---

## Sidebar — MVP Architecture Gap Analysis (cross-track)

Per founder instruction (2026-06-05 morning), meesell-data-engineer was dispatched to audit `docs/MVP_ARCHITECTURE.md` against the as-built database. Deliverable: **`docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md`** (42 KB, 18 gaps).

**Findings summary:**
- 18 total gaps (11 validated from database coordinator's list + 7 new)
- 4 BLOCKER-V1: G1 (§2 schema drift, 4 deltas), G2 (pricing_calcs/exports legacy pointer), G8 (15 export adapter golden fixtures unauthored), G16 (CI gate `.gitlab-ci.yml` references non-existent script path — doubly hollow)
- 1 DEFER-V1.5: G15 (ContextVar for current_user_id — V1 trade-off already accepted in §9.2)
- 13 NON-BLOCKER but should-fix

**Reconciliation plan (5 phases, ~5-6 person-days total):**
- R1 (3-4 hr): §2 rewrite + inline pricing_calcs/exports DDL — doc-only, parallelisable
- R2 (2-3 hr): code-lock for step assignment + primitive inference — move from prose to `backend/app/i18n/`
- R3 (4-6 hr): section numbering fix + cross-reference hygiene
- R4 (3-4 days, founder-bounded): author 15 export adapter golden fixtures + 3 AI eval golden sets — long pole
- R5 (1 hr V1 only): product_drafts TTL cleanup task

**Database track is NOT blocked by any of these.** Schema is locked at `935e55b4852c` and the as-built reflects the correct (newer) layers of the architecture doc, not §2. The gap analysis exists to protect future agents from reading the stale §2 as authoritative.

**Founder decision points for the morning:**
1. Authorize R1+R3+R2 in parallel (doc-only, no risk to the live schema)?
2. R4 fixture authoring requires your time per fixture (realistic seller profiles + products) — schedule that?
3. R5-G10 (product_drafts TTL) — fix now or defer?

See `docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md` for the full inventory + per-gap dispatch prompts.

## Done
- Phase 0 complete: all 8 context files read, seed inputs verified on disk, Postgres connectivity confirmed via `kubectl exec`

## In Progress
- (none — awaiting founder GO for Phase 1)

## Blockers
- none

## Phase 0 Findings (2026-06-04)

### Table count — 13 V1 tables
From MVP_ARCHITECTURE §2 (11 tables) + §10 (2 audit/autosave tables):

| # | Table | Section | Notes |
|---|---|---|---|
| 1 | `users` | §2.1 | Identity |
| 2 | `seller_profile` | §2.2 | Onboarding compliance bucket |
| 3 | `templates` | §2.3 | 3,557 distinct templates |
| 4 | `categories` | §2.3 | 3,772 leaves, FK to templates |
| 5 | `field_enum_values` | §2.3 | 291 Brand-pattern fields, (category_id, field_name) PK |
| 6 | `field_aliases` | §2.3 | Canonical alias map + XLSX export reverse map |
| 7 | `catalogs` | §2.4 | User catalog container |
| 8 | `products` | §2.4 | Product per catalog, fields_jsonb |
| 9 | `product_images` | §2.5 | 4-slot image (uniform corpus-wide) |
| 10 | `pricing_calcs` | §2.5 | Per V1_FEATURE_SPEC §4 (placeholder in §2.5) |
| 11 | `exports` | §2.5 | Per V1_FEATURE_SPEC §4 (placeholder in §2.5) |
| 12 | `audit_events` | §10/§11.2 | Append-only, BIGSERIAL PK, 90d hot retention |
| 13 | `product_drafts` | §10/§11.6 | Latest unsaved state per (user_id, product_id) |

**Note:** meesell-database-builder agent spec says "7 V1 tables" (old V1_FEATURE_SPEC reference). MVP_ARCHITECTURE §2 + §10 supersedes. Dispatching against 13 tables.

### Schema gaps to address in Phase 1 (database-internal decisions — no founder ruling needed)
1. `field_aliases.for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE` — required by §12.2 and MEESHO_CATEGORY_INTELLIGENCE §6, missing from §2.3 DDL
2. `templates.compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'` — required by §5.5.13 and §12.6, missing from §2.3 templates DDL
3. `field_enum_values.enum_entries JSONB` — added per §5.6.4 (richer structure replacing simple `enum_values` array)
4. `pricing_calcs` and `exports` DDL not in §2.5 (says "per V1_FEATURE_SPEC §4") — meesell-database-builder must read V1_FEATURE_SPEC §4 for these two tables

### Seed inputs verified
| File | Leaves/Entries | Status |
|---|---|---|
| `data/parsed/batch_01_*.json` … `batch_12_*.json` | 3,772 total (0 failures) | ✅ |
| `data/parsed/canonical_field_aliases.json` | 23 alias families | ✅ |
| `data/parsed/field_display_overrides.json` | 43 curated entries | ✅ |
| `backend/app/data/meesho_category_tree.json` | 3,772 leaves (hierarchical) | ✅ |

### Postgres reachability
- `postgres-0` pod: Running, 6h+ uptime
- `SELECT version()`: `PostgreSQL 16.14 (Debian 16.14-1.pgdg13+1) on x86_64-pc-linux-gnu`
- Credentials secret `dev/postgres-credentials`: keys `database`, `password`, `username` present
- Access method: `kubectl exec -n dev postgres-0 -- psql -U <user> -d <db>` ✅

## Inputs Ready (verified on disk)
- `docs/MVP_ARCHITECTURE.md` §2 — DDL for V1 tables (the contract)
- `docs/MEESHO_CATEGORY_INTELLIGENCE.md` §3, §6, §8 — data model + alias families + invariants
- `data/parsed/batch_01_*.json` … `batch_12_*.json` — 3,772 leaves, raw + summary
- `data/parsed/canonical_field_aliases.json` — 23 alias families (16+ as stated in SSoT)
- `data/parsed/field_display_overrides.json` — 43 curated entries (39 per original status)
- `backend/app/data/meesho_category_tree.json` — 3,772-leaf hierarchical tree

## Infra Hand-offs (from INFRA, already live)
- **Postgres host:** `postgres.dev.svc.cluster.local:5432` (PG16, 20GB PVC, `prevent_destroy` on)
- **Credentials:** K8s Secret `dev/postgres-credentials` (ref via `secretKeyRef` from app pods)
- **Local access (founder laptop):** kubectl port-forward `svc/postgres 5433:5432 -n dev` (matches CLAUDE.md convention)

## Hand-offs (will queue post-phases)
- **DATABASE → BACKEND** (post Phase 2): `backend/app/models/` ready; `meesell-api-routes-builder` and `meesell-services-builder` can begin against the ORM contract
- **DATABASE → AI** (post Phase 3): `categories`, `templates`, `field_enum_values`, `field_aliases` seeded — Smart Category Picker + enum-guardrailed Auto-fill can hit real data
- **DATABASE → FRONTEND** (post Phase 3): primitive component values for `field_display_overrides` and onboarding compliance extensions are queryable

## Stop Conditions
- Migration would drop existing data
- Head divergence between `dev` and any other namespace
- Seed row counts diverge from SSoT-declared counts by more than 0.5%
- Specialist agent failure outside the playbook
- Anything that needs a founder ruling

## Updates Log
=== UPDATE: 2026-06-05 phase-4-complete + TRACK DONE ===
Phase: 4 — Pytest smoke tests against dev Postgres
Done:
  - backend/tests/conftest.py PATCHED (+77 LOC): dev_engine (session, NullPool), db (function, loop_scope='function', NullPool, ROLLBACK teardown), pytest.skip() guard on app.main import
  - backend/tests/test_database.py CREATED (621 LOC): 40 tests
  - Test breakdown (all 40 PASS):
    * A. CRUD per table: 13/13 — all 13 models verified create+read+delete
    * B. JSONB round-trip: 8/8 — compliance_extensions, schema_jsonb, enum_entries, fields_jsonb, ai_suggestions_jsonb, precheck_jsonb, diff_jsonb, draft_jsonb
    * C. FK enforcement: 5/5 — IntegrityError on bad FK, CASCADE on user/catalog parent delete
    * D. UNIQUE constraint: 3/3 — users.phone, categories.meesho_leaf_id, product_images.(product_id, order_idx)
    * E. CHECK constraint: 2/2 — templates.compliance_shape, product_images.order_idx BETWEEN 1 AND 4
    * F. Computed column: 2/2 — product_images.is_front for order_idx=1 vs 2
    * G. Server defaults: 3/3 — gen_random_uuid(), NOW(), JSONB '{}' default
    * H. Seeded data sanity: 4/4 — Grocery>=321, Eye-Serum collapsed=1, max enum=4481, for_xlsx_export>=1
  - Wall time: 83.05s
  - Post-run dev DB verified clean — all 9 mutable tables = 0 rows; seeded tables unchanged
Findings:
  - pytest-asyncio 0.24 cross-loop bug: needs loop_scope='function' + per-fixture NullPool engine (documented in conftest comments + memory)
  - LEGACY ROUTERS BLOCK FastAPI startup: backend/app/routers/catalogs.py, skus.py, images.py import deleted models — api-routes-builder must clean before route work
In progress: nothing
Blockers: none for database; flagged legacy-router cleanup as first action for the API track
Next: Hand-off to backend API track (api-routes-builder)
Hand-offs RELEASED:
  - meesell-api-routes-builder: ORM contract + live reference data ready for /api/v1/categories/*, /seller-profile/* endpoints
  - meesell-services-builder: schema_jsonb shape verified; Export Adapter unblocked
  - meesell-ai-coordinator: categories + field_enum_values queryable for Smart Picker + enum-constrained Autofill
=========

=== UPDATE: 2026-06-05 phase-3-complete ===
Phase: 3 — Seed scripts for reference data
Done:
  - 5 seed scripts created (1,604 LOC total):
    * scripts/seed_field_aliases.py (223)
    * scripts/build_template_schemas.py (597) — canonical transformer, dedup by schema_hash
    * scripts/seed_categories.py (205)
    * scripts/seed_field_enum_values.py (290)
    * scripts/seed_all.py (289) — orchestrator with smoke checks
  - Intermediate: data/parsed/leaf_id_to_schema_hash.json (3,772 entries — bridges templates and categories seeders)
  - Smoke counts verified directly against dev Postgres:
    * field_aliases: 67 (67 expected, exact)
    * templates: 3,566 (3,557 expected, +0.25% — within ±0.5%)
    * categories: 3,772 (3,772 expected, exact)
    * field_enum_values: 49,259 (~49,295 expected, -0.073% — within ±0.5%)
  - Idempotency verified: second seed_all.py run = no-op (zero new rows, zero errors, identical counts)
  - Sample query proofs:
    * compliance_shape='collapsed' templates: exactly 1 (Eye-Serum — matches SSoT)
    * MAX(value_count) field_enum_values: 4,481 (Compatible Models — matches SSoT §5)
    * Top super: Home & Kitchen 816, Sports & Fitness 362, Grocery 321, Office 312, Kids 284
Findings (non-blocking — within tolerance):
  - 36 (category_id, canonical_field) collisions silently deduped at insert (two raw names → same canonical)
  - +9 templates beyond SSoT 3,557 = 157 schema groups split on enum_source/help_text differences
  - Cheat-sheet bug in dispatch brief: tree path[] already includes leaf_name as last element; builder corrected
  - 39 (not 43) real display overrides — file has 4 comment-marker keys with underscore prefix
In progress: Phase 4 dispatch
Blockers: none
Hand-offs READY (downstream sessions unblocked for read against seeded data):
  - meesell-ai-coordinator: can hit real categories + templates + field_enum_values for Smart Picker + enum-guardrailed Autofill
  - meesell-api-routes-builder: can wire /api/v1/categories/*, /api/v1/categories/{id}/schema, /api/v1/categories/{id}/field-enum/{name} endpoints against live data
=========

=== UPDATE: 2026-06-05 phase-2-complete ===
Phase: 2 — Alembic baseline migration
Done:
  - Legacy cleanup: removed backend/app/models/sku.py, image.py, backend/alembic/versions/2651e548010e_initial_schema.py
  - env.py bugfix: removed config.set_main_option(sqlalchemy.url) — configparser treats URL-encoded %2F as %-interpolation; replaced with direct create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
  - Baseline migration: backend/alembic/versions/935e55b4852c_v1_baseline_13_tables.py (head=935e55b4852c)
  - Manual patches to autogenerate output:
    * Patch 1: prepended op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto") as first upgrade op
    * Patch 2: removed invalid postgresql_using='gin' kwarg from op.drop_index in downgrade body
  - Applied to dev Postgres via kubectl port-forward (5433→5432). alembic current shows head.
  - Verified: 13 application tables + alembic_version (kubectl \dt confirmed)
  - Drift check: clean (autogenerate produced empty pass body — deleted the no-op revision)
In progress: Phase 3 dispatch
Blockers: none
Next: meesell-database-builder for seed scripts
Hand-offs: DDL surface ready for API/services builders to wire reads/writes
=========

=== UPDATE: 2026-06-05 phase-1-complete ===
Phase: 1 — SQLAlchemy 2.0 async ORM models
Done:
  - 13 ORM models created in backend/app/models/ (1,542 LOC total)
    - base.py (10), __init__.py (93)
    - user.py (97), seller_profile.py (136), template.py (124), category.py (112),
      field_enum_value.py (95), field_alias.py (61), catalog.py (90), product.py (146),
      product_image.py (102), pricing_calc.py (88), export.py (95),
      audit_event.py (99), product_draft.py (89)
  - backend/app/database.py already correct (async engine + AsyncSession + get_db dep)
  - All 4 schema deltas applied:
    * field_aliases.for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE
    * templates.compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard' + CHECK
    * field_enum_values.enum_entries JSONB (richer structure per §5.6.4)
    * seller_profile: dropped 3 collapsed compliance fields (per §12.6 revised)
  - All 13 models import-verified (Base.metadata has 13 tables registered)
  - Column-type decisions documented:
    * catalog.category_id: nullable FK ON DELETE SET NULL (§2.4 implicit)
    * export.error_message: TEXT NULL (added per §5.5.8 Celery requirement)
    * product_images.is_front: GENERATED ALWAYS AS (order_idx = 1) STORED
    * audit_events.id: BigInteger + Identity(always=True) = BIGSERIAL semantics
    * product_drafts: composite PK (user_id, product_id) via ForeignKeyConstraint
  - pgcrypto extension confirmed required for gen_random_uuid() — Phase 2 will enable
Findings (require Phase 2 action):
  - Legacy files backend/app/models/sku.py + image.py exist (pre-V1, NOT in __init__.py exports)
  - Legacy migration backend/alembic/versions/2651e548010e_initial_schema.py exists
  - Decision: Phase 2 will delete legacy files + old migration, then generate clean baseline
In progress: Phase 2 dispatch
Blockers: none
Next: meesell-database-builder dispatched for Alembic baseline + apply on dev
Hand-offs: pending Phase 2 completion
=========

=== UPDATE: 2026-06-04 phase-0-complete ===
Phase: 0 — Orientation
Done:
  - Read all 8 context files: CLAUDE.md, MVP_ARCHITECTURE.md, MEESHO_CATEGORY_INTELLIGENCE.md,
    STATUS_DATABASE.md, meesell-database-builder.md spec, MEMORY.md (blank), STATUS_INFRA.md, STATUS_DATA.md
  - Verified: 13 V1 tables (11 from §2 + 2 from §10 audit/autosave)
  - Verified: all 12 batch JSONs present (3,772 leaves, 0 failures)
  - Verified: canonical_field_aliases.json (23 families), field_display_overrides.json (43 entries),
    meesho_category_tree.json (3,772 leaves)
  - Verified: postgres-0 pod Running, PostgreSQL 16.14, credentials secret present
  - Identified: 4 schema gap decisions (for_xlsx_export column, compliance_shape column,
    enum_entries column, pricing_calcs/exports DDL from V1_FEATURE_SPEC §4)
  - Updated STATUS_DATABASE.md with full Phase 0 findings
In progress: none
Blockers: none
Next: Founder GO for Phase 1
Hand-offs: none yet (Phase 1 gate)
=========

=== UPDATE: 2026-06-04 init ===
File initialised by master session (mesell-master-session-2). Awaiting first DATABASE sub-session start.
=========
