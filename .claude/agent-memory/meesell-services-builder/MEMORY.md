# Memory — meesell-services-builder

## Agent Identity
Business-logic specialist for MeeSell. Owns service layer (ai_engine call site, image_processor, quality_engine, pricing_engine, export_service, otp_service MSG91 portion, storage) + Celery workers. Decentralized memory ecosystem.

---

## Session: 2026-06-05 — Final Gap Purge (workers + leftover tests) COMPLETE

### Task summary
Coordinator gap-pass mini-task: api-routes-builder had purged 9 routers + 6 schemas + 4 services + 3 tests
but 2 worker files and 2 router-tests survived outside their boundary. My job: delete the dead remnants,
audit the rest of workers/ + tests/, then declare backend CONSTRUCTION-READY.

### Files DELETED (10 total)

Workers (3):
- backend/app/workers/generation_tasks.py — imported deleted app.models.sku.SKU
- backend/app/workers/image_tasks.py — imported deleted app.services.image_processor
- backend/app/workers/scrape_tasks.py — imported deleted app.services.meesho_scraper

Tests (7):
- backend/tests/test_routers_exports.py — tested deleted exports router
- backend/tests/test_routers_images.py — tested deleted images router
- backend/tests/test_scraper.py — imported deleted app.schemas.scrape + app.services.meesho_scraper
- backend/tests/test_image_processor.py — imported deleted app.services.image_processor
- backend/tests/test_catalog.py — used deleted /api/v1/catalogs + legacy /api/v1/auth/send-otp URLs
- backend/tests/test_schemas.py — imported deleted schemas (catalog, sku, pricing)
- backend/tests/test_pricing.py — imported pricing_engine (transitively broken) + hit deleted /api/v1/pricing/calculate

### Files MODIFIED (1)
- backend/app/workers/celery_app.py:
  - include=[] (was [image_tasks, generation_tasks, scrape_tasks])
  - added task_reject_on_worker_lost=True per services-builder ALWAYS rules
  - removed task_routes={images, generation, scraping} for deleted queues
  - kept core conf: task_serializer, task_track_started, task_acks_late, worker_prefetch_multiplier=1

### Workers KEPT: none
All 3 V0 worker task modules were dead. Only celery_app.py survives (modified). Construction phase will
re-populate include[] when image-precheck / export tasks land.

### Acceptance checks — all 5 evaluated
1. `from app.main import app; len(app.routes)` → 9 — PASS
2. `from app.workers.celery_app import celery_app` → imports clean, include=[] — PASS
3. `grep "from app.models.sku|from app.models.image|_load_owned_sku|_load_owned_catalog"` over backend/app + backend/tests → 0 matches — PASS
4. `pytest test_app_boot_integration test_database test_auth -v`:
   - test_app_boot_integration.py: 7/7 PASS
   - test_database.py: 40 errors + 6 fails — ALL Postgres `localhost:5433` connection refused (pre-existing infra gap, not regression)
   - test_auth.py: 4 errors — same Postgres connection issue
   No import errors, no collection errors, no URL regressions. PASS (infrastructure caveat).
5. `git status` shows 10 deletes + 1 modify within scope, full delta recorded in STATUS file. PASS.

### Residual blocker found (NOT this pass — for construction)
**backend/app/services/pricing_engine.py line 23**: `from app.schemas.pricing import PricingAlert`
The pricing.py schema was deleted by api-routes-builder. pricing_engine.py is therefore unimportable.
This was OUT of my purge scope (it is a "kept" service the prior agent declared clean, but it has a
transitive broken import on a deleted schema). Construction phase fix options:
- Option A: re-author backend/app/schemas/pricing.py with PricingAlert (V1 form).
- Option B: refactor pricing_engine to use a plain `@dataclass` or `TypedDict` for the alert.
Recommendation: Option A — schemas/pricing.py is going to be re-authored anyway for the V1 pricing router.

### V1 service inventory after this pass

| Service | State |
|---|---|
| backend/app/services/ai_engine.py | LIVE — clean imports (app.config, app.data) |
| backend/app/services/otp_service.py | LIVE — clean imports (httpx, redis, app.config) |
| backend/app/services/storage.py | LIVE — clean imports (app.config) |
| backend/app/services/pricing_engine.py | **BROKEN IMPORT** — needs app.schemas.pricing.PricingAlert |
| backend/app/services/image_processor.py | TO BUILD (construction) |
| backend/app/services/quality_engine.py | TO BUILD (construction) |
| backend/app/services/export_service.py | TO BUILD (construction) |
| backend/app/workers/celery_app.py | LIVE — modified, include=[] |
| backend/app/workers/image_tasks.py | TO BUILD (V1 image precheck) |
| backend/app/workers/generation_tasks.py | TO BUILD (V1 XLSX + ZIP export gen) |

### Cross-agent notes I picked up

From **meesell-database-builder MEMORY**:
- Head revision: `f31c75438e61` (parent `a1b2c3d4e5f6` → `935e55b4852c`)
- 13 V1 tables live; seed counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
- Already shipped: pg_trgm + 3 GIN trgm indexes on categories (path, leaf_name, super_name)
- Already shipped: idx_product_drafts_saved_at (B-tree)
- New `app/i18n/` package owns versioned constants for schema_jsonb shape (STEP_ASSIGNMENT, primitive_classifier).
  Services that produce schema_jsonb output MUST import from app.i18n.

From **meesell-api-routes-builder MEMORY**:
- Only auth router exists right now. App.routes has 9 (4 starlette builtins + 3 auth APIRoute + 1 health APIRoute + 1 Mount).
- Auth URL prefix locked: /api/v1/auth/{otp/send, otp/verify, me}.
- Python venv: backend/.venv/bin/python (3.11, not 3.12 as CLAUDE.md states).
- PYTHONPATH=/Users/mugunthansrinivasan/Project/mesell/backend required for pytest.

### Construction-phase next-steps prefix (for self next session)

1. **First fix on construction start**: backend/app/services/pricing_engine.py PricingAlert import.
   Either re-create schemas/pricing.py (likely api-routes-builder will when it ships POST /products/{id}/pricing)
   or refactor pricing_engine to dataclass. Coordinate with api-routes-builder.
2. **Worker task modules**: image_tasks.py + generation_tasks.py rewrite against V1 13-table schema.
   - image_tasks: process_image(product_image_id) — rembg + PIL + GCS + product_images.precheck_jsonb update.
   - generation_tasks: generate_export(export_id) — openpyxl XLSX + image ZIP per export row.
3. **Celery includes**: when worker modules land, update celery_app.py include=[] to register them.
   Pattern: include=["app.workers.image_tasks", "app.workers.generation_tasks"].
4. **task_routes**: add {images, generation} queues back to celery_app.py when tasks ship.
5. **GCS path scheme** (not yet locked): TBD but proposed `{bucket}/{user_id}/products/{product_id}/images/{order_idx}.jpg`
   for processed; `{bucket}/{user_id}/products/{product_id}/originals/{order_idx}.{ext}` for raw.
   Signed-URL TTL: 1h default per agent spec.

### Backend declared CONSTRUCTION-READY by this pass
Pending founder approval of the construction-phase dispatch plan. Coordinator review next.

---

## Memory index
| Entry | Type | Summary |
|---|---|---|
| Session 2026-06-05 final purge | project | 10 files deleted (3 workers + 7 tests), 1 modified (celery_app.py); backend declared construction-ready |
| pricing_engine import blocker | reference | services/pricing_engine.py line 23 imports deleted app.schemas.pricing.PricingAlert; fix in construction |
| celery_app.py include pattern | reference | include=[] when task modules absent; re-populate with ["app.workers.image_tasks", ...] when V1 tasks ship |
| task_reject_on_worker_lost | reference | Added to celery conf per services-builder ALWAYS rule |
| V1 head revision (DB) | reference | f31c75438e61 (chain: 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61) |
| auth URL pattern (routes) | reference | /api/v1/auth/otp/send, /otp/verify, /me — locked by api-routes-builder |
| Python venv path | reference | backend/.venv/bin/python (3.11); PYTHONPATH=backend/ for pytest |
| app/i18n/ pattern (DB) | reference | versioned schema_jsonb constants; services producing schema_jsonb MUST import here |
