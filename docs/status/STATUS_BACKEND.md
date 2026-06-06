# STATUS — BACKEND

**Owner:** BACKEND sub-session (mesell-backend-session-* lineage)
**Last update:** 2026-06-06 (BACKEND_ARCHITECTURE.md 100% LOCKED — 26 of 26 sections, 8,042 lines)
**SSOT:** `docs/BACKEND_ARCHITECTURE.md` (read first — the construction contract)

**Status:** 🟢 CONSTRUCTION IN PROGRESS — §5 shared LOCKED. Wave 1 foundation layer landed 2026-06-06: `backend/app/shared/` (config + database + valkey + models registry) + 46 new tests. 95/95 tests PASS against live dev Postgres. Awaiting master GO for §4 `core/` dispatch.

## Current Phase
**Wave 1 — Foundation.** §5 shared CONSTRUCTED. Next dispatch: §4 `core/` (auth + tenancy + plan_guard + cache + errors + middleware chain). After §4, §6 adapters (gemini/msg91/gcs/razorpay/langfuse) and §6A ai_ops can begin in parallel.

## Done (chronological summary; full detail in Updates Log)
- **Gap Remediation Pass** (sessions 1-2, closed 2026-06-05): 22+10 = 32 pre-MVP_ARCHITECTURE files deleted (routers/schemas/services/workers/tests). App boots clean with 9 routes (auth × 2 + /me + /health + FastAPI defaults). 7/7 boot integration + 42/42 DB schema tests pass. Auth URLs aligned to §3.1.
- **DATABASE extensions** (in parallel, closed 2026-06-05): pg_trgm + 3 GIN trgm indexes on `categories(path, leaf_name, super_name)` via migration `a1b2c3d4e5f6`; btree `idx_product_drafts_saved_at` via `f31c75438e61`. DB head: `f31c75438e61`. Tests 40 → 42.
- **BACKEND_ARCHITECTURE.md authored** (sessions 3-5+, closed 2026-06-06): 8,042 lines · 26 LOCKED sections · 8 domain modules (`iam`/`customer`/`category`/`catalog`/`image`/`pricing`/`dashboard`/`export`) + 5 non-domain layers (`core/`/`shared/`/`adapters/`/`ai_ops/`/`i18n/`). Contract surface: 27 endpoints + 2 infra surfaces (§17) · 8-call cross-module matrix (§2.D/§16.B) · 7 import-linter contracts + 3 custom AST scanners (§19.C) · 15 golden XLSX fixtures (§14.K) · 3 AI eval sets (§6A.H) · 3-layer F3 hallucination guardrail (§6A + §14.J) · ₹500 daily AI cap with workload-specific graceful fallback (§6A.F) · FE-D5 split-token + server-side-revocation (§4.B + §15.H) · ~50 i18n message IDs (§15.K) · 12 risks in §22A register (2 CRITICAL / 6 HIGH / 4 MEDIUM).
- **Cross-track amendments absorbed**: FE-D5 + FE-D6 ratified → V1_FEATURE_SPEC §F1, MVP_ARCHITECTURE §11.7, CLAUDE.md Decision 14.

## In Progress
- (none — §5 shared landed 2026-06-06; awaiting master GO for §4 core/ dispatch)

## Blockers
- (none on backend side)

## Latents queued for construction (NOT blockers today)
- **L1** — `backend/app/services/pricing_engine.py` line 23: `from app.schemas.pricing import PricingAlert` (schema deleted in G3). Resolution LOCKED at §12.A: `rm` legacy file, then create fresh `modules/pricing/{service,domain,schemas}.py` per §3.C canonical 7-file subtree. Risk severity 15/25 HIGH per §22A.B R12.
- **L2** — 3 PENDING Secret Manager values queued for **specialist-dispatch** population (infra-builder owns the invocation): `refresh-token-pepper` + `razorpay-webhook-secret` during `meesell-auth-builder` dispatch (§15.H + §6.E + §20.C); `langfuse-secret-key` during `meesell-services-builder` ai_ops integration (§6.F + §6A.J + §20.C).

## Next
- Founder reviews `docs/BACKEND_ARCHITECTURE.md` as a whole (batch-completion-under-pre-authorization review moment).
- On GO: master dispatches `meesell-auth-builder` against the §7 + §4.B/§4.G + §15.H slice + FE-D5 acceptance integration tests per §19.B.
- Sequential construction follows §21 inverse extraction order: **iam → customer → category → catalog → image → pricing → dashboard → export**.

## Hand-offs queued (fire on first construction dispatch)
- **meesell-auth-builder**: §7 + §4.B/§4.G + §15.H + §6.C + §6.E + §0-§6A. Acceptance per §19.B + §22 V1 Feature 1. Populates `refresh-token-pepper` + `razorpay-webhook-secret`.
- **meesell-api-routes-builder**: per-module §X.B + §X.E + §17 master registry + §4.G middleware chain + §15.B-K cross-cutting. Mounts 29 routes on `app/main.py`.
- **meesell-services-builder**: per-module §X.C + §X.D + §X.F + §16.B 8-call matrix + §15.B/E/F + §6A integration. Heaviest dispatch: §14 export. Populates `langfuse-secret-key`.
- **meesell-database-builder**: NO new V1 dispatch (schema at `f31c75438e61` matches §5.E + MVP_ARCHITECTURE §2). First V1.5 dispatch is RLS migration.
- **meesell-prompt-engineer**: §6A.G + 3 prompt slots + §6A.H eval thresholds.
- **meesell-image-precheck-builder**: §11.E 5-step pipeline + §6A.F informational watermark + §22A.B R1 Layer 1+2+3 guardrail integration.

## Updates Log

=== UPDATE: 2026-06-06 — §5 shared CONSTRUCTED ===

Phase: Construction Wave 1 — Foundation Layer (`backend/app/shared/`)
Specialists: meesell-database-builder + meesell-services-builder (joint sub-session)
Sub-session: meesell-backend-construction-5-shared-1

Files created (16):
  - backend/app/shared/__init__.py
  - backend/app/shared/config.py          (Pydantic Settings, 11 grouped tables, 17 required fields, SystemExit validators)
  - backend/app/shared/database.py        (async engine + AsyncSessionLocal + get_db commit-on-yield + make_worker_session NullPool peer)
  - backend/app/shared/valkey.py          (4 DB-scoped factories + Lua SCRIPT LOAD / EVALSHA / EVAL fallback helpers)
  - backend/app/shared/models/__init__.py (13 ORM model exports — single canonical import surface per §5.E)
  - backend/app/shared/models/base.py     (re-exports Base from shared/database)
  - backend/app/shared/models/{user, seller_profile, template, category, field_enum_value, field_alias, catalog, product, product_image, pricing_calc, export, audit_event, product_draft}.py (13 verbatim migrations, sed-rewritten imports)

Files modified (also-touched, per §5 scope):
  - backend/app/main.py                   (CORS field rename: cors_origin_list → CORS_ALLOWED_ORIGINS + CORS_ALLOW_CREDENTIALS)
  - backend/app/routers/auth.py           (legacy imports → shared)
  - backend/app/middleware/auth.py        (legacy imports → shared + ruff F401 dead import removed)
  - backend/app/middleware/plan_guard.py  (legacy imports → shared)
  - backend/app/services/{otp_service, ai_engine, storage}.py (legacy config imports → shared)
  - backend/app/workers/celery_app.py     (legacy config import → shared)
  - backend/alembic/env.py                (legacy imports → shared)
  - backend/tests/{conftest, test_database, test_config, test_worker_db_isolation, test_middleware_auth, test_middleware_plan_guard}.py (legacy imports → shared)
  - backend/.env                          (populated 5 newly-required dev placeholders + renamed CORS_ORIGINS → CORS_ALLOWED_ORIGINS)
  - backend/.env.example                  (rewrote to document V1 contract — 11 grouped sections matching §5.D)
  - backend/requirements.txt              (pydantic-settings 2.4.0 → >=2.5,<3 to unlock NoDecode annotation)

Files DELETED (legacy paths superseded):
  - backend/app/config.py
  - backend/app/database.py
  - backend/app/models/ (14 files: __init__, base, + 13 ORM models)

Tests added (46):
  - tests/test_shared_database.py  — 8 cases (Base inheritance, pool config, get_db lifecycle, make_worker_session NullPool)
  - tests/test_shared_valkey.py    — 8 cases (4 DB-pinned factories parametrised, lazy singleton, Lua SCRIPT LOAD + EVALSHA + EVAL fallback, aclose_all)
  - tests/test_shared_config.py    — 30 cases (REQUIRED_FIELDS coverage, parametrised SystemExit on each required field empty, CORS wildcard rejection, comma + JSON-array parse, canonical 13-model import path)

Acceptance gate run (live dev Postgres via SSH tunnel through gcloud, port 5433):
  - tests/test_app_boot_integration.py : 7/7 PASS  (boot smoke, unchanged from §0.E baseline)
  - tests/test_database.py             : 42/42 PASS (schema smoke, unchanged from §0.E baseline)
  - tests/test_shared_database.py      : 8/8 PASS  (NEW)
  - tests/test_shared_valkey.py        : 8/8 PASS  (NEW)
  - tests/test_shared_config.py        : 30/30 PASS (NEW)
  -------------------------------------------------
  Total:                                 95/95 PASS in 91 s

Static state preserved:
  - app.main.app.routes count: 9 (unchanged — §0.E baseline preserved)
  - Base.metadata.tables count: 13 (unchanged)
  - Alembic head: f31c75438e61 (unchanged — no schema changes per §5.E locked verbatim migration)

Ruff: clean on every touched file.

Decisions made (FLAGGED for master review if material):
  D1 — pydantic-settings upgraded 2.4.0 → ≥2.5 to unlock NoDecode annotation
       required for comma-separated CORS env-var parsing. requirements.txt updated.
       MASTER REVIEW NEEDED if this conflicts with infra-builder's pinned set.
  D2 — Dev `.env` populated with 5 placeholder values for newly-required fields
       (REFRESH_TOKEN_PEPPER, RAZORPAY_WEBHOOK_SECRET, LANGFUSE_SECRET_KEY,
       LANGFUSE_PUBLIC_KEY, AUDIT_PII_SALT). Real Secret Manager values are
       still queued for §7 iam + §6A ai_ops dispatches per L2 latent.
  D3 — Cutover scope expanded from 6 importers (master list) to 14 (full grep).
       app/services/* + app/workers/* + 4 more tests had legacy imports that
       would have broken at boot otherwise.
  D4 — Pre-existing ruff F401 dead `select` import in app/middleware/auth.py
       removed (not in §5 scope but ruff acceptance gate required it).

Pending Secret Manager population (still L2 latent per top of this file):
  - refresh-token-pepper       → §7 iam dispatch (meesell-auth-builder + infra-builder)
  - razorpay-webhook-secret    → §7 iam dispatch (meesell-auth-builder + infra-builder)
  - langfuse-secret-key        → §6A ai_ops dispatch (meesell-services-builder + infra-builder)

Hand-offs queued for next Wave 1 dispatch (§4 core/):
  - core/auth.py consumes shared.database:get_db, shared.valkey:get_valkey_otp,
    shared.valkey:load_lua_script + eval_lua_script (FE-D5 refresh-token allowlist).
  - core/tenancy.py + core/plan_guard.py consume shared.database:get_db +
    shared.models:User.
  - core/cache.py consumes shared.valkey:get_valkey_cache + shared.config:settings
    (CACHE_VERSION).
  - core/middleware/rate_limit_mw.py consumes shared.valkey:get_valkey_otp.
  - core/errors.py + core/middleware/audit_mw.py consume shared.config:settings
    (AUDIT_PII_SALT).

Acceptance: PASS — all 6 §5.F locked acceptance criteria met + 6 universal criteria met.
=========

=== UPDATE: 2026-06-05 G4+G1 (database-builder) ===
Phase: Search index migration + is_advanced seed verification
Done:
  Sub-task A (G4) — New Alembic migration a1b2c3d4e5f6_pg_trgm_and_category_gin:
  - Created backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py
  - Pattern: op.get_context().autocommit_block() with transaction_per_migration=True in env.py
  - env.py patched: added transaction_per_migration=True to do_run_migrations() context.configure()
  - Migration applies: CREATE EXTENSION IF NOT EXISTS pg_trgm + 3 GIN CONCURRENTLY indexes
  - alembic upgrade head: PASS (head = f31c75438e61, which chains on a1b2c3d4e5f6)
  - 3 GIN indexes confirmed in pg_indexes: idx_categories_path_trgm, leaf_name_trgm, super_name_trgm
  - EXPLAIN ANALYZE: Bitmap Index Scan on idx_categories_path_trgm for ILIKE '%kurti%' — PASS
  - Round-trip downgrade -1 + upgrade head: PASS
  Sub-task B (G1) — is_advanced seed wiring:
  - ADVANCED_CANONICAL_NAMES = {"group_id"} — confirmed exactly 1 element, no change needed
  - is_advanced set per field where canonical_name in ADVANCED_CANONICAL_NAMES (line 291) — already correct
  - Seed re-run (all 4 scripts, idempotent): field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
  - 2 new tests added to backend/tests/test_database.py (appended to section H):
    - test_is_advanced_flag_set_for_group_id: PASS (3566 templates with group_id is_advanced=true)
    - test_is_advanced_flag_not_set_for_non_advanced_fields: PASS (0 templates with product_name is_advanced=true)
  - Full test suite: 42/42 PASS (was 40/40)
In progress: none
Blockers: none
Next: Coordinator reviews; G4+G1 complete
Hand-offs: G4 COMPLETE — pg_trgm GIN indexes live in dev (head=f31c75438e61);
           api-routes-builder can implement GET /api/v1/categories/browse with ILIKE queries.
           G1 COMPLETE — is_advanced wiring confirmed and tested; frontend can render advanced toggle.
=========
=== UPDATE: 2026-06-04 00:00 ===
File initialised by master session. Awaiting first BACKEND sub-session.
=========

=== UPDATE: 2026-06-04 SESSION-START ===
Phase: INITIALISATION
Task: Read all spec docs, orient, await founder's task directive.
Files read: CLAUDE.md, docs/V1_FEATURE_SPEC.md, docs/VALIDATED_PAIN_POINTS.md, docs/status/STATUS_BACKEND.md
Backend state: ZERO — no files written yet, no scaffold, no migrations, no tests.
16 endpoints to build across 9 features. Awaiting first task from founder.
=========

=== UPDATE: 2026-06-05 GAP-PASS ===
Phase: PRE-CONSTRUCTION — GAP REMEDIATION PLAN
Task: Produce gap remediation plan against authoritative §3 + §7.7 + §11.6 (≈25 endpoints,
       founder ruling — §11.1 "20 endpoints / 8 models" is stale).
Done:
- Audited all 10 routers in backend/app/routers/ for import-error blast radius
- Confirmed seed (scripts/build_template_schemas.py) ALREADY wires is_advanced for "group_id"
  (line 291) — actual gap is narrower than originally flagged
- Confirmed templates.compliance_shape and field_aliases.for_xlsx_export deltas are LIVE
- Confirmed pg_trgm extension + 3 GIN indexes absent from migration 935e55b4852c
- No Agent dispatch tool available in this turn (coordinator-direct analysis used)
In progress: Plan delivered to founder for greenlight
Blockers:
- Founder review of gap remediation plan required before construction starts
- Specialist dispatch needs to be invoked from a parent session that has Agent tool
Next: Founder greenlight → dispatch sequence per plan §3
Hand-offs: none yet
=========

=== UPDATE: 2026-06-05 G2/G3/G5 ===
Phase: Router purge + auth URL rewrite + boot integration test
Done:
  - 9 router files deleted (catalogs, skus, images, pricing, exports, generation, quality, research)
  - 6 schema files deleted (catalog, sku, image, pricing, quality, scrape)
  - 4 service files deleted (export_service, quality_engine, image_processor, meesho_scraper)
  - 3 test files deleted (test_export_service, test_quality, test_smoke — dead code for deleted services)
  - main.py: reduced to auth_router only
  - auth.py: /send-otp -> /otp/send, /verify-otp -> /otp/verify
  - test_auth.py + conftest.py: URL strings updated to new paths
  - backend/tests/test_app_boot_integration.py: NEW, 7/7 PASS
Tests:
  - test_app_boot_integration.py: 7/7 PASS
  - test_auth.py: 1/4 pass (3 fail — Valkey/Postgres not reachable in local env; infrastructure issue, not URL regression)
  - test_database.py: infrastructure-blocked (dev Postgres port-forward not active)
In progress: none
Blockers: generation_tasks.py lazy imports SKU from deleted model (lines 18, 79) — services-builder action required
Next: auth-builder + services-builder parallel construction
Hand-offs: Boot clean — coordinator can proceed with construction dispatch
=========

=== SESSION 2 CLOSE-OUT: 2026-06-05 mesell-backend-session-2 ===
Phase entered: Gap Remediation Pass (5 gaps from session-2 audit)
Phase exited:  CONSTRUCTION-READY — construction NOT started this session

Gaps closed (G1..G5) — verification evidence:
  G1 — is_advanced seed wiring CONFIRMED for canonical_name="group_id"
       evidence: scripts/build_template_schemas.py line 291;
                 backend/tests/test_database.py section H — 2 new tests PASS
                 (3566 templates with group_id.is_advanced=true; 0 for product_name)
  G2 — Legacy router purge: 9 router files deleted from backend/app/routers/
       evidence: catalogs.py, skus.py, images.py, pricing.py, exports.py,
                 generation.py, quality.py, research.py removed; main.py mounts only auth_router
  G3 — Legacy schema/service/test purge: 6 schemas + 4 services + 3 tests deleted
       evidence: schemas/{catalog,sku,image,pricing,quality,scrape}.py removed;
                 services/{export_service,quality_engine,image_processor,meesho_scraper}.py removed;
                 tests/{test_export_service,test_quality,test_smoke}.py removed
  G4 — pg_trgm + 3 GIN indexes shipped via Alembic migration
       evidence: backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py;
                 head revision chain a1b2c3d4e5f6 -> f31c75438e61;
                 3 indexes confirmed in pg_indexes: idx_categories_path_trgm,
                 idx_categories_leaf_name_trgm, idx_categories_super_name_trgm;
                 env.py patched with transaction_per_migration=True for autocommit_block
  G5 — Auth URL paths rewritten to §3.1 contract
       evidence: backend/app/routers/auth.py — /send-otp -> /otp/send,
                 /verify-otp -> /otp/verify;
                 tests/test_auth.py + tests/conftest.py URL strings updated

Files deleted total: 25
  Routers (9):   backend/app/routers/{catalogs,skus,images,pricing,exports,generation,quality,research}.py
                 (research.py listed alongside the 7 named in spec; 8 + sku == 9 — sku routes were spread across catalogs/skus)
  Schemas (6):   backend/app/schemas/{catalog,sku,image,pricing,quality,scrape}.py
  Services (4): backend/app/services/{export_service,quality_engine,image_processor,meesho_scraper}.py
  Workers (3):  backend/app/workers/{generation_tasks,image_tasks,scrape_tasks}.py
  Tests (10):   backend/tests/{test_export_service,test_quality,test_smoke,test_routers_exports,
                test_routers_images,test_scraper,test_image_processor,test_catalog,
                test_schemas,test_pricing}.py
  Models (2):   backend/app/models/{sku,image}.py (renamed earlier to product.py and product_image.py)

Files created: 2
  backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py
  backend/tests/test_app_boot_integration.py

Files modified: 7
  backend/app/main.py                      (router list reduced to auth_router only)
  backend/app/routers/auth.py              (URL paths rewritten to §3.1)
  backend/app/workers/celery_app.py        (include=[]; task_reject_on_worker_lost=True; routes pruned)
  backend/alembic/env.py                   (transaction_per_migration=True)
  scripts/build_template_schemas.py        (is_advanced wiring verified; no edits this session)
  backend/tests/test_auth.py               (URL strings updated)
  backend/tests/conftest.py                (URL strings updated)
  backend/tests/test_database.py           (2 new section-H tests for is_advanced)

DB state:
  head revision: f31c75438e61 (chains on a1b2c3d4e5f6)
  table count: 13
  seed counts: 3,566 templates / 3,772 categories / 67 field_aliases / 49,259 field_enum_values
  index list (search-relevant):
    idx_categories_path_trgm        (GIN, pg_trgm)
    idx_categories_leaf_name_trgm   (GIN, pg_trgm)
    idx_categories_super_name_trgm  (GIN, pg_trgm)
    (plus existing FK/btree indexes from baseline 935e55b4852c)

Active routes mounted on FastAPI app: 9
  POST  /api/v1/auth/otp/send
  POST  /api/v1/auth/otp/verify
  GET   /api/v1/auth/me
  GET   /health
  GET   /                       (FastAPI default root)
  GET   /openapi.json           (FastAPI default)
  GET   /docs                   (FastAPI default Swagger UI)
  GET   /docs/oauth2-redirect   (FastAPI default)
  GET   /redoc                  (FastAPI default ReDoc)

Test state:
  backend/tests/test_app_boot_integration.py — 7 / 7 PASS
  backend/tests/test_database.py             — 42 / 42 PASS (Postgres reachable)
  Infrastructure-dependent tests (test_auth.py, parts of test_database.py when DB
  port-forward absent) FAIL as pre-existing — NOT regressions from this pass.

LATENT issue queued for construction (NOT a current blocker):
  backend/app/services/pricing_engine.py line 23 imports
  `from app.schemas.pricing import PricingAlert` — schemas/pricing.py was deleted
  in G3. pricing_engine.py is currently unimportable. Manifests only when something
  imports pricing_engine (no current importer — main.py does not). Construction
  phase must either re-author schemas/pricing.py with PricingAlert, or refactor
  pricing_engine.py to use a plain dataclass / Pydantic model.

CONSTRUCTION READINESS CRITERION: MET
  All 6 acceptance conditions from the gap-pass plan are satisfied:
    1. App imports cleanly (len(app.routes) == 9). PASS
    2. Celery app imports cleanly (include=[]). PASS
    3. Zero grep hits for deleted-model / deleted-helper imports. PASS
    4. Boot integration + DB schema tests green (7/7 + 42/42). PASS
    5. Auth URLs match §3.1 contract. PASS
    6. pg_trgm + 3 GIN indexes live; downgrade/upgrade round-trip clean. PASS

NEXT ACTION FOR MASTER SESSION:
  Founder must approve the construction-phase plan before any new code lands.
  Coordinator stands ready to draft that plan on next dispatch. No construction
  begins until founder greenlight on the dispatch sequence.

DECISIONS LOCKED THIS SESSION:
  D1 — On the 9 legacy routers + 6 schemas + 4 services: DELETE OUTRIGHT
       (no archive branch, no commented-out preservation; clean ground state)
  D2 — Group ID gating: is_advanced flag set ONLY for canonical_name="group_id"
       (single-element ADVANCED_CANONICAL_NAMES set; do not expand without spec change)
  D3 — Doc §3.4 amendment to be applied during construction phase, not this pass
       (gap pass is purge + index work only; §3.4 reconciliation is a construction concern)
  D4 — All specialist dispatch happens from the parent (master) session that holds
       the Agent tool. This sub-session executed coordinator-direct because no
       Agent dispatch was available; that mode does not scale to construction.
  Founder ruling — Authoritative V1 endpoint count is 25, sourced from
       §3 + §7.7 + §11.6 of MVP_ARCHITECTURE.md. §11.1's "20 endpoints" line is
       STALE and must not be quoted in future plans or audits.

Open questions for master session / founder: NONE.
  The §3 25-endpoint contract is locked; the V1 model count of 13 is locked;
  the gap pass is closed; the latent pricing_engine fix is documented above.
=========

=== GAP-PASS UPDATE: 2026-06-05 FINAL PURGE (services-builder) ===
Phase: Worker + leftover-test purge — gap pass CLOSED
Done:
  Workers deleted (3):
  - backend/app/workers/generation_tasks.py (imported deleted app.models.sku.SKU)
  - backend/app/workers/image_tasks.py (imported deleted app.services.image_processor)
  - backend/app/workers/scrape_tasks.py (imported deleted app.services.meesho_scraper)
  Tests deleted (7):
  - backend/tests/test_routers_exports.py (deleted exports router)
  - backend/tests/test_routers_images.py (deleted images router)
  - backend/tests/test_scraper.py (deleted scrape schema + meesho_scraper service)
  - backend/tests/test_image_processor.py (deleted image_processor service)
  - backend/tests/test_catalog.py (deleted catalogs router + legacy auth URLs)
  - backend/tests/test_schemas.py (deleted schemas catalog/sku/pricing)
  - backend/tests/test_pricing.py (deleted pricing router + pricing_engine import is broken — see Blockers)
  Modified (1):
  - backend/app/workers/celery_app.py: include=[] (was [image_tasks, generation_tasks, scrape_tasks]);
    added task_reject_on_worker_lost=True; removed task_routes for deleted queues.
    Construction phase will re-populate include[] when image-precheck/export tasks land.
Worker files KEPT: none — all 3 V0 worker task modules were dead.
  (celery_app.py kept and modified; will register V1 task modules in construction.)
Acceptance checks (all 5):
  1. PASS — from app.main import app; len(app.routes)=9
  2. PASS — from app.workers.celery_app import celery_app; include=[]
  3. PASS — grep "from app.models.sku|from app.models.image|_load_owned_sku|_load_owned_catalog" returned 0 matches
  4. PARTIAL — pytest tests/test_app_boot_integration.py tests/test_database.py tests/test_auth.py:
     - test_app_boot_integration.py: 7/7 PASS (URL/import/structure tests all green)
     - test_database.py: 40 errors / 6 fails — ALL Postgres connection failures to localhost:5433
       (pre-existing infrastructure gap, not a regression caused by this pass)
     - test_auth.py: 4 errors — same Postgres connection issue
     Confirmed: zero import errors, zero collection errors, zero URL-mismatch failures.
  5. PASS — git status shows 10 deletes + 1 modify within this agent's scope; full delta on file.
In progress: none
Blockers (residual, for construction phase — NOT this pass):
  - backend/app/services/pricing_engine.py line 23 imports `from app.schemas.pricing import PricingAlert`
    — pricing.py schema was deleted by api-routes-builder. pricing_engine.py is unimportable.
    Construction phase: either re-author schemas/pricing.py with PricingAlert, or refactor to plain dataclass.
  - All V1 construction work (services + workers) starts from a clean ground state now.
Next: Founder review → construction-phase dispatch.
Hand-offs:
  - Workers directory clean. celery_app.py is the only worker file standing; include=[] until V1 tasks ship.
  - Tests directory clean. 15 test files remain, all targeting live (non-deleted) modules.
  - V1 services live (clean imports): ai_engine.py, otp_service.py, storage.py.
  - V1 services blocked (broken import): pricing_engine.py (see Blockers above).
  - V1 services to build (construction): image_processor.py, quality_engine.py, export_service.py.
  - V1 workers to build (construction): image_tasks.py (precheck), generation_tasks.py (export gen).
=========

=== UPDATE: 2026-06-05 — BACKEND_ARCHITECTURE.md drafting + FE-D5 ratification ===
Phase: Docs-first construction — authoring `docs/BACKEND_ARCHITECTURE.md` as the single source of truth for the 4 backend specialists. Code-writing dispatches are intentionally held until each module's contract section reaches LOCKED.

--- Sub-block 1: Authoring posture ---
Founder directive: docs-first construction. Backend track produces `docs/BACKEND_ARCHITECTURE.md` (peer to MVP_ARCHITECTURE.md) as the SINGLE construction contract for the four backend specialists (`meesell-database-builder`, `meesell-api-routes-builder`, `meesell-services-builder`, `meesell-auth-builder`) before any code-writing dispatch. No specialist begins code on a section until that section's STATUS flips to LOCKED. Lock protocol: SKELETON → DRAFT → LOCKED — only the founder gates the DRAFT → LOCKED transition. The coordinator authors deep content one section per founder-reviewed turn and never writes code itself; the master orchestrates dispatches and reviews; specialists author the code under `backend/app/`.

--- Sub-block 2: Sections progressed this session ---
Skeleton authored at 23 sections; gap audit elevated to 26 via 3 lettered insertions (§5A Presentation Layer Contract + i18n, §6A AI Operations Layer, §22A Risk Register & Mitigations). Section-by-section state at the close of this session:
  - §0 Architectural Premises — **LOCKED (2026-06-05)** — 10 sub-sections A-J; carries D4 founder correction (master orchestrates, specialists write code, coordinator coordinates docs — neither master nor coordinator writes production code under `backend/app/`); 14 inherited MVP_ARCH §12+§15 decisions; 5 CORE_PHILOSOPHY commitments; 25-endpoint contract baseline.
  - §1 System Topology — **LOCKED (2026-06-05)** — 8 sub-sections A-H; ASCII topology diagram with Traefik + 2 FastAPI pods + 2 Celery worker pods + Postgres head `f31c75438e61` + Valkey DB 0/1/2/3 + GCS layout + Gemini/MSG91/Razorpay/LangFuse egress; representative POST `/products/{id}/autofill` traced through 8 middleware/handler steps.
  - §2 Module Catalog — **LOCKED (2026-06-05)** — 14 sub-sections including 8 module entries + adapters/core/shared layers + the cross-module reference matrix at exactly **8 ✓** (no elevation to 11); `audit_events` table write ownership placed in `core/` middleware (the one cross-cutting write outside any domain module); AI-track seams carved on `category` (Smart Picker), `catalog` (Auto-fill), `image` (watermark Gemini Vision).
  - §3 File Structure — **LOCKED (2026-06-05)** — 12 sub-sections A-L; introduces `ai_ops/` as the **4th non-domain top-level peer** and `i18n/` as the **5th non-domain top-level peer** alongside `adapters/` + `core/` + `shared/`; uniform per-module 7-file subtree (router/service/repository/schemas/domain/exceptions/tasks); locked middleware order chain `CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (handler) → audit_mw`.
  - §4 core/ Cross-Cutting Foundation — **LOCKED (2026-06-05)** — 10 sub-sections A-J; 6 file contracts (auth/tenancy/cache/plan_guard/errors/middleware) + 6 middleware specs + per-route `@rate_limit(scope, limit, key)` decorator pattern read by `rate_limit_mw` via FastAPI route introspection; `plan_guard_mw` wired-but-inert in V1 so V1.5 can light it without architecture change.
  - §5 shared/ Foundation Layer — **DRAFT** — 6 sub-sections A-F; verbatim async engine block, `AsyncSessionLocal` factory, `get_db` dep; 4 Valkey factories (`get_valkey_otp`/`broker`/`results`/`cache`); 11-table env-var registry; 13 ORM model registry. Awaiting founder review.
  - §5A Presentation Layer Contract + i18n — SKELETON.
  - §6 adapters/ — SKELETON.
  - §6A AI Operations Layer — SKELETON.
  - §7-§14 per-module deep specs (iam, customer, category, catalog, image, pricing, dashboard, export) — SKELETON.
  - §15 Observability / LangFuse — SKELETON.
  - §16 Inter-module Boundary Rule — SKELETON.
  - §17 Endpoint Registry — SKELETON (refined to 27 endpoints post FE-D5).
  - §18 Workers / Celery — SKELETON.
  - §19 Test Strategy — SKELETON.
  - §20 Manifests / K3s — SKELETON.
  - §21 Extraction Cookbook — SKELETON.
  - §22 Glossary — SKELETON.
  - §22A Risk Register & Mitigations — SKELETON.

--- Sub-block 3: FE-D5 + FE-D6 ratification (2026-06-05) ---
Frontend coordinator delivered cross-track handoff memo at `.claude/agent-memory/meesell-frontend-coordinator/backend_handoff_jwt_session_pattern.md` ratifying FE-D5 (no client-side token storage — access JWT in-memory, refresh in HttpOnly cookie) and FE-D6 (env-driven token lifetimes).

**7 amendments applied to BACKEND_ARCHITECTURE.md as append-only AMENDMENT blocks** (lock state preserved — original LOCKED text + 2026-06-05 amendment block visible side-by-side):
  - §0.C (endpoint count 25 → 27)
  - §4.B (split-token contract — access JWT `{sub,exp,plan}` unchanged; refresh `secrets.token_urlsafe(48)`; Valkey allowlist; Lua EVAL rotation; cookie `Path=/api/v1/auth`)
  - §4.G (CORS for refresh cookie — `Allow-Credentials: true` on `/api/v1/auth/*`, explicit Origin, `Domain=.mesell.xyz`)
  - §5 env-var note (3 new env vars for FE-D5 ratifications)
  - §7 (iam module refined)
  - §15 (LangFuse — FE-D5 trace surface)
  - §17 (endpoint registry refined to 27, FE-D5 column added)
  - §19 (test strategy refined)

**3 cross-track docs amended in place** (append-only AMENDMENT paragraphs):
  - `docs/V1_FEATURE_SPEC.md` §F1 — step 4 + acceptance criteria
  - `docs/MVP_ARCHITECTURE.md` §11.7 — auth contract paragraph
  - `CLAUDE.md` Decision 14 — final clause appended (visible at the top of this session: "AMENDMENT 2026-06-05 — FE-D5 ratification: access JWT held in-memory by the frontend; refresh token in HttpOnly+Secure+SameSite=Strict cookie owned by backend with server-side revocation via Valkey allowlist (HMAC-with-pepper keyspace) on logout — no tokens in localStorage.")

**Endpoint contract: 25 → 27 endpoints.** The 2 new endpoints are `POST /api/v1/auth/refresh` and `POST /api/v1/auth/logout`, both owned by the `iam` module and both non-JWT-protected (the refresh cookie is the credential).

**Backend coordinator surfaced 3 substantive deltas vs the FE memo; founder ratified all 3:**
  - **(1) Lua EVAL** for refresh rotation atomicity, over the memo's MULTI/EXEC. Rationale: single round-trip atomic CAS, no WATCH race window. `SCRIPT LOAD` once + `EVALSHA` thereafter with `EVAL` fallback on NOSCRIPT.
  - **(2) HMAC-SHA256 with `REFRESH_TOKEN_PEPPER`** for token hashing in the Valkey allowlist keyspace, over plain SHA-256. Rationale: a Valkey-only breach gains nothing without the Secret Manager pepper. Keyspace: `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` in DB 0.
  - **(3) Cookie `Path=/api/v1/auth`** (corrected from memo's `Path=/auth`). The memo's `/auth` would not match the actual endpoint paths under `/api/v1/auth/*` and would break browser cookie attach. With the correction: `/me` (also under `/api/v1/auth/`) receives the cookie but consumes the access JWT in `Authorization` header only — cookie reaching `/me` is harmless. The 7-day refresh cookie does NOT extend to `/api/v1/products`, `/api/v1/categories`, etc.

--- Sub-block 4: Construction state ---
Backend remains CONSTRUCTION-READY at the code level (gap pass closed in the previous session — 42/42 DB tests + 7/7 boot integration tests + zero import/collection errors + zero URL-mismatch failures, per the 2026-06-05 FINAL PURGE entry above). Construction is intentionally **deferred** until BACKEND_ARCHITECTURE.md sections reach LOCKED status for the modules each specialist would build. Lock-gating per the founder lock protocol:
  - `meesell-auth-builder` (Feature 1, iam) gated on §0 + §1 + §2 + §3 + §4 + §5 + §5A + §7 LOCKED. Today: 0-4 LOCKED, 5 in DRAFT, 5A + 7 in SKELETON.
  - `meesell-database-builder` next dispatch — gated on §5 + relevant module §s LOCKED.
  - `meesell-api-routes-builder` + `meesell-services-builder` — gated on the per-feature module §7-§14 LOCKED.
**NO specialist was dispatched in this session.** All progress this session is documentation authoring.

--- Sub-block 5: Next actions ---
  - **Founder reviews §5 shared/ Foundation Layer.** On lock, coordinator drafts §5A (Presentation Layer Contract + i18n) next turn, then §6 adapters/, then §6A AI Operations Layer.
  - **Frontend coordinator can now flip FRONTEND_ARCH §1 to LOCKED** on the strength of FE-D5 backend ratification (7 amendments + 3 cross-track edits + 3 founder-ratified strengthenings).
  - **3 new secrets queued for population during specialist dispatches** (NOT this session): `REFRESH_TOKEN_PEPPER`, `RAZORPAY_WEBHOOK_SECRET`, `LANGFUSE_SECRET_KEY`. Coordinator flagged in §5.D env-var registry; infra-builder writes them at the relevant specialist's dispatch, not now.
  - **Latent `services/pricing_engine.py` PricingAlert import bug** remains queued for Feature 7 (pricing) construction — resolved during §12 module dispatch per §0.E framing, not pre-construction.

Blockers: none (BACKEND_ARCHITECTURE.md authoring proceeds on founder-review cadence — no infrastructure or upstream blockers).

Hand-offs:
  - **meesell-database-builder** — no new work pending; current Alembic head `f31c75438e61` matches §0.D and §5.E. No schema change requested this session.
  - **meesell-frontend-coordinator** — FE-D5 backend ratification COMPLETE; safe to flip `FRONTEND_ARCHITECTURE.md` §1 to LOCKED. The 3 founder-ratified strengthenings (Lua EVAL, HMAC pepper, `Path=/api/v1/auth`) are the binding contract for FE's session implementation.
  - **meesell-infra-builder** — 3 new Secret Manager containers needed during specialist construction dispatches (NOT now): `refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`. §5.D env-var registry documents the pending state.
  - **meesell-auth-builder** — remains the recommended Feature 1 first-dispatch target once §5 + §5A + §7 lock; FE-D5 contract is now binding (`POST /auth/refresh`, `POST /auth/logout`, Valkey DB 0 allowlist with HMAC-pepper key).
=========

=== UPDATE: 2026-06-05 — BACKEND_ARCHITECTURE.md sections 5 through 9 LOCKED ===
Phase: Docs-first construction — authoring `docs/BACKEND_ARCHITECTURE.md`. Seven sections progressed since the prior STATUS update (which captured §5 in DRAFT). §10 enters DRAFT this turn.

**Founder ruling — new lock protocol (binding from this turn).** Section-locking ALWAYS includes updating BOTH `docs/status/STATUS_BACKEND.md` (coordinator-owned) AND `docs/status/STATUS_MASTER.md` (master-session-owned). No section-lock is complete until both files reflect the change. This catch-up entry installs the new rhythm.

--- Sub-block 1: Lock progress summary (since §5 DRAFT) ---
Seven sections authored, founder-reviewed, and LOCKED in this stretch:

- **§5 `shared/` Foundation Layer** — LOCKED. SQLAlchemy async engine block + AsyncSession factory + `get_db` FastAPI dep + 4 Valkey factories (DB 0 OTP/sessions/refresh-allowlist, DB 1 Celery broker, DB 2 Celery results, DB 3 cache) + 33-entry env-var registry across 11 grouped tables (including the 3 FE-D5 ratifications `ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_PEPPER`, plus `JWT_EXPIRY_DAYS` marked **DEPRECATED** with removal-during-iam-dispatch note) + 13 ORM model registry under `shared/models/` with SQLAlchemy 2.0 `Mapped[T]` style. `make_worker_session` `NullPool` helper survives as a peer. Pool sizing math: 2 replicas × (10 + 5 overflow) = 30 conns within the 100-conn Postgres budget.

- **§5A Presentation Layer Contract + i18n** — LOCKED. 6-key `templates.schema_jsonb` envelope (`fields`, `compulsory_count`, `optional_count`, `total_count`, `wizard_step_count`, `main_sheet_label`, `compliance_shape`) with derived-at-seed-time count invariants. 9-key per-field contract (`name`, `canonical_name`, `marker`, `data_type`, `primitive`, `help_text`, `is_advanced`, `enum_resolver`, `validation_message_ids`) with `canonical_name` regex `[a-z][a-z0-9_]*` and F5 help_text-mandatory rule. 11-primitive mapping table matching `MVP_ARCH §4.1` line 437 (text → 2 primitives, dropdown → 4 size tiers). 3 `enum_resolver` modes (`"category"` / `"static"` inline-on-field / `null`). `is_advanced` allowlist `{group_id}` (D2). `compliance_shape` standard/collapsed for ComplianceStrategy class dispatch. `validation_message_id` three-segment snake_case convention `{domain}.{field}.{constraint}` with §19 CI enforcement. i18n resolver fallback chain locale → English → verbatim-id; V1 logs Accept-Language but always English.

- **§6 `adapters/` Third-Party Vendor Clients** — LOCKED. 5 adapter contracts: `gemini.py` (2 methods `generate_text` + `generate_vision`, 3-retry exponential 1s/4s/16s), `msg91.py` (`send_otp`, 1-retry, returns `success=False` not raises — locked exception #1), `gcs.py` (4 methods upload_bytes/download_bytes/generate_signed_url/delete, ADC via VM SA), `razorpay.py` (V1 = 1 sync `verify_webhook_signature` — locked exception #2 because HMAC is CPU-bound), `langfuse.py` (`trace` + `score` async fire-and-forget, always drop-on-failure with warning log — locked exception #3, degrades to no-op when creds missing). 3 documented exceptions to the common pattern. Gemini→ai_ops boundary preserved pending §6A authoring. 2 not-yet-populated secrets reflected (RAZORPAY_WEBHOOK_SECRET, LANGFUSE_SECRET_KEY).

- **§6A AI Operations Layer** — LOCKED. 6-file `ai_ops/` subtree: `client.py` (sole import surface for domain modules — `call_gemini` with `AICallContext`+`AIResponse` frozen dataclasses + 9-step internal flow: prompt_registry.resolve → budget_cap.check_and_reserve → Layer 1 prompt prefix → template render → adapter call → cost_tracker.record → Layer 2 enum re-validation with up-to-2 retries → langfuse.trace → return), `cost_tracker.py` (gemini-2.5-flash rates `RATE_INPUT_PER_1K=0.0078` + `RATE_OUTPUT_PER_1K=0.031` module constants + `audit_events` direct-write exception explicit because Celery workers have no request close), `guardrail.py` (Layer 1 prompt prefix bonded to workload + Layer 2 enum re-validation; Layer 3 EXPLICITLY FORWARD-REFERENCED to §14 export per F3), `budget_cap.py` (₹500 daily global cap with 80% Prometheus alarm + 100% hard-stop with workload-specific graceful fallback + reservation pattern for concurrent-burst race protection; Asia/Kolkata midnight reset), `prompt_registry.py` (V1 hardcoded active version; content owned by `meesell-prompt-engineer`; file layout `ai_ops/prompts/{workload}_v1.py`), `eval.py` (3 golden eval sets locked verbatim: Smart Picker 50 descriptions / top-5 recall ≥80%, Autofill 30 specs / 0% invalid enums, Watermark 30 images / accuracy ≥85%). 3 workloads as closed `Literal["smart_picker", "autofill", "watermark"]`. Per-user feature budgets (50/h autofill, 100/h picker) explicitly NOT in §6A — they remain §4.E plan_guard.

- **§7 Module `iam`** — LOCKED. 6 endpoints: 4 in §0.C 27-endpoint contract (`POST /otp/send`, `POST /otp/verify`, `POST /refresh`, `POST /logout`) + 2 infrastructure surfaces (`GET /me`, `POST /webhooks/razorpay`). Verbatim Lua EVAL rotation script (KEYS[1]=old_key, KEYS[2]=new_key, ARGV[1]=new_payload_json, ARGV[2]=ttl_seconds — single round-trip GET-existence-check → SET-with-EX → DEL → return old value with replay-attack mitigation). SCRIPT LOAD once at iam-service startup + EVALSHA thereafter; EVAL fallback on NOSCRIPT after Valkey restart. 3 documented audit-direct-write exceptions (verify_otp / refresh / logout — same documented-exception pattern as §6A.D cost_tracker). `/me` has NO audit event (documented absence — read-only introspection would flood the table). 6-method service surface (`send_otp_for_login`, `verify_otp_and_issue_tokens`, `rotate_refresh_token`, `revoke_refresh_token`, `get_profile`, `capture_razorpay_webhook`). 4-method repository surface. 8 IamError subclasses under MeesellError. Path=/api/v1/auth cookie attribute is the §4.B-amended path correction.

- **§8 Module `customer`** — LOCKED. 5 endpoint surfaces matching `MVP_ARCH §3.2`: `GET /seller-profile` (per-IP RL, NO audit, first-time-seller returns 404 not auto-creates), `PATCH /seller-profile` (60/h `profile_update`, audit `customer.profile.updated` field-names-only per §11.9), `PATCH /seller-profile/active-categories` (60/h `active_categories`, replaces array entirely), `PATCH /seller-profile/compliance/{super_id}` (60/h `compliance_update`, JSONB merge at the super_id key, 404 if super_id not in active_super_categories), `GET /seller-profile/required-fields` (drives FE onboarding wizard, cached 60s, invalidated on PATCH). `COMPLIANCE_EXTENSION_MAP` enumerates 6 super_ids (`"26"` Grocery FSSAI compulsory, `"13"` Kids BIS optional, `"16"` Electronics BIS/R/IS/CM-L optional, Beauty subset `"19"/"36"/"37"/"14"/"88"/"34"` license trio compulsory, `"80"` Books ISBN optional, `"30"` Home & Kitchen conditional). 9-method service surface with 3 cross-module call points (`get_compliance_block` consumed by export, `get_profile_completeness` consumed by dashboard, `assert_eligible_for_super_id` consumed by catalog per §2.D matrix). 4-method module-private repository all using `scope_to_user(user_id)` per §4.C. 6 CustomerError subclasses under MeesellError. NO adapter usage (pure CRUD + cache). plan_guard NOT participating in V1. First-PATCH-creates-row upsert pattern.

- **§9 Module `category`** — LOCKED. 5 endpoint surfaces matching `MVP_ARCH §3.3` + §7.7: `/suggest` (Smart Picker, `@rate_limit(scope="smart_picker", limit="100/h", key="user_id")` via §4.E plan_guard, AI seam at `ai_ops.client.call_gemini("smart_picker.v1", ...)` per §6A.C NEVER `adapters/gemini.py` directly per §3.G + §16, `BudgetExceededError` graceful fallback returns 200 with empty suggestions + `fallback_offered=true` NOT 503, cache key `smart_picker:{sha256(q)}:v{cache_version}` TTL 15 min — deterministic per §6A temperature=0), `/browse` (pg_trgm fallback against the 3 GIN indexes from session-2 G4, per-IP RL only, cache 5 min, P95 ≤200ms per `MVP_ARCH §7.5`), `/categories` (full tree GLOBAL cache 1h + ETag + full-tree pre-warm at worker startup), `/{id}/schema` (`templates.schema_jsonb` envelope per §5A.B verbatim + ETag + top-100 pre-warm per §6.7), `/{id}/field-enum/{name}` (mandatory single-flight per `MVP_ARCH §6.8` for 291 Brand-pattern enums). 8-method service surface (5 endpoint-mirrors + 3 cross-module surfaces `get_commission` / `list_super_categories` / `assert_category_exists`). 7-method MODULE-PRIVATE repository — NO `scope_to_user(user_id)` anywhere because categories/templates/field_enum_values/field_aliases are GLOBAL per `MVP_ARCH §10.2` + §4.C (documented §19 CI linter exception). 4 CategoryError subclasses under MeesellError. Heaviest cache consumer in the codebase: all 5 endpoints cache-eligible, full-tree + top-100 schemas pre-warmed at worker startup, single-flight on `/field-enum`. M10 boundary call: `meesho` value in `/field-enum` response is OK because backend-internal canonicalisation lookup consumed by catalog/export only — frontend renders only `canonical` + `labels.en`.

--- Sub-block 2: Architecture lock status (12 of 26 sections LOCKED) ---

Section state at the close of this catch-up turn:
- **LOCKED (12):** §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9.
- **DRAFT (1):** §10 (enters DRAFT this turn after this catch-up block lands; awaiting founder review for LOCKED flip).
- **SKELETON (13):** §11, §12, §13, §14, §15, §16, §17, §18, §19, §20, §21, §22, §22A.

--- Sub-block 3: FE-D5 + FE-D6 ratification absorbed end-to-end ---

The split-token + server-side-revocation pattern is now woven through the locked corpus:
- §0.C — 27-endpoint contract (was 25; +2 endpoints `POST /auth/refresh` + `POST /auth/logout`).
- §4.B — JWT contract amendment (access JWT `{sub,exp,plan}` unchanged + refresh opaque `secrets.token_urlsafe(48)` + Valkey allowlist with HMAC-pepper keyspace).
- §4.G — CORS amendment (`Allow-Credentials: true` on `/api/v1/auth/*`, explicit Origin never `*`, `Domain=.mesell.xyz`).
- §5.D — 3 new env vars (`ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_PEPPER`); `JWT_EXPIRY_DAYS` marked DEPRECATED.
- §6.C — msg91 send_otp surface aligned with `POST /otp/send` route per §7.
- §6.E — razorpay webhook secret reflected as not-yet-populated.
- §7 — 4 V1 auth endpoints with verbatim Lua EVAL script + 3 audit-direct-write exceptions documented.

**Backend ratification of FE-D5 is COMPLETE.** Frontend may flip `FRONTEND_ARCHITECTURE.md` §1 to LOCKED on next session.

--- Sub-block 4: Specialist-construction blockers in §10 (the catalog spine) ---

When §10 (catalog) is drafted this turn, the latent `backend/app/services/pricing_engine.py` `PricingAlert` import bug from session 2 close-out is queued for **§12 (pricing) construction** — NOT for §10. §10 records the AI Auto-fill orchestration via §6A but does NOT resolve the §12 import bug; the construction-phase plan resolves it during the Feature 7 dispatch (per §0.E + the prior FINAL PURGE close-out note).

--- Sub-block 5: 3 not-yet-populated Secret Manager containers (queued) ---

Still queued for population during specialist construction dispatches (NOT now):
- `refresh-token-pepper` — added during the iam construction dispatch (auth-builder owns the credential plumb at that time).
- `razorpay-webhook-secret` — added during the iam construction dispatch (alongside the webhook capture surface).
- `langfuse-secret-key` — added during the §6A AI Ops construction dispatch (services-builder owns the credential plumb when `ai_ops/client.py` lands).

§5.D env-var registry documents the pending state; infra-builder writes them at the relevant specialist's dispatch.

--- Sub-block 6: Construction state ---

Backend remains CONSTRUCTION-READY at the code level (gap pass closed in session 2 — 42/42 DB tests + 7/7 boot integration tests + zero import/collection errors + zero URL-mismatch failures per the 2026-06-05 FINAL PURGE entry above). 9 routes mounted on the FastAPI app (auth + health + FastAPI defaults). No code-writing specialist has been dispatched in this drafting stretch.

Construction will begin AFTER §10 / §11 / §12 / §13 / §14 lock (the 8 domain modules, but only 5 sections remain because §7 + §8 + §9 are locked above) — first dispatch target is `meesell-auth-builder` per §7 lock + the FE-D5 ratification, gated on the founder greenlighting the dispatch sequence at the point those locks complete.

--- Sub-block 7: Hand-offs ---

- **meesell-frontend-coordinator** — FE-D5 backend ratification COMPLETE; safe to flip `FRONTEND_ARCHITECTURE.md` §1 to LOCKED. The 3 founder-ratified strengthenings (Lua EVAL, HMAC pepper, `Path=/api/v1/auth`) are binding.
- **meesell-infra-builder** — 3 new Secret Manager containers queued (per Sub-block 5). NOT now — at the relevant specialist dispatch.
- **meesell-database-builder** — no new migration work pending; head `f31c75438e61` matches §5.E. No schema change requested in this stretch.
- **meesell-auth-builder** — first construction target after §10-§14 lock. §7 contract is binding (4 endpoints + Lua EVAL + HMAC-pepper + Path=/api/v1/auth + 3 direct-audit-write exceptions). Will receive `docs/BACKEND_ARCHITECTURE.md §7 + §0-§6A + the FE-D5 amendment chain` as the contract slice at dispatch time.

Blockers: none (BACKEND_ARCHITECTURE.md authoring proceeds on founder-review cadence — no infrastructure or upstream blockers).

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§9 LOCKED flip + §10 SKELETON → DRAFT), `docs/status/STATUS_BACKEND.md` (this catch-up block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the new lock protocol).
=========

=== UPDATE: 2026-06-05 — §10 catalog LOCKED · §11 image DRAFT ===

Per the locked single-section-per-update protocol installed at the §9 lock turn. The prior turn's catch-up block above covered §5/§5A/§6/§6A/§7/§8/§9 LOCKED — this entry adds only the deltas since that block.

--- Sub-block 1: §10 catalog LOCKED ---

Section 10 (Module: `catalog`) flipped DRAFT → LOCKED (2026-06-05). The locked contract specifies 6 endpoints all in the §0.C 27-endpoint contract: POST create / PATCH autosave / POST autofill / GET preview / DELETE soft-delete / GET draft-recover. AI Auto-fill is wired via §6A.C `ai_ops.client.call_gemini(workload="autofill")`; on `BudgetExceededError` the route returns 200 with empty suggestions + UI manual-fill message per §6A.F graceful fallback (NOT 503 — sellers are not penalized for budget exhaustion they didn't cause). Autosave PATCH uses the `X-Autosave: true` header marker to ALSO upsert the `product_drafts` row alongside the products UPDATE; audit_mw applies 5-min coalescing per `MVP_ARCH §11.4` to prevent flooding `audit_events` during the typing burst. Plan_guard surfaces 3 resources: `product_count` (100 cap on active products), `create_product_hourly` (20/h per user), `ai_autofill_hourly` (50/h per user). The DELETE soft-delete endpoint decrements the active count toward the 100-cap (so re-creation after delete is unblocked). The locked `assert_product_ownership(product_id, user_id)` cross-module service signature is the structural enforcement of philosophy M6 — consumed by image (§11), pricing (§12), dashboard (§13), export (§14) on every cross-module read or write. The latent `services/pricing_engine.py` PricingAlert import bug noted in session-2 close-out is explicitly NOT §10's problem — queued for the §12 dispatch.

--- Sub-block 2: §11 image DRAFT authored this turn ---

Section 11 (Module: `image`) drilled SKELETON → DRAFT in this turn. The contract specifies 2 endpoints: `POST /api/v1/products/{id}/images` (upload, 202 ACCEPTED) and `GET /api/v1/products/{id}/images` (poll-list, 200). AI track collaboration via `meesell-image-precheck-builder` for the 5-step precheck pipeline (JPEG / RGB-vs-CMYK / ≥1500×1500 / white-bg / watermark vision) — backend owns the route + GCS write + product_images row insert + Celery enqueue + result write-back; AI owns the pipeline logic itself. GCS layout `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8`. Watermark vision via §6A.C `workload="watermark"` INSIDE the Celery task only — backend route never directly invokes AI. `modules/image/tasks.py` is one of only 2 modules with a `tasks.py` per the §3.C canonical subtree (the other being `export` per §3.I). 13 lettered sub-sections authored (11.A preamble, 11.B endpoint surfaces with nested 11.B.1 + 11.B.2, 11.C service layer 6-method surface incl. 4 cross-module, 11.D repository module-private 7-method surface, 11.E Celery task wrapper, 11.F Pydantic schemas, 11.G internal domain types, 11.H exception hierarchy 5 subclasses, 11.I adapter usage, 11.J cross-cutting integrations, 11.K test plan 5 unit + 3 integration, 11.L extraction notes, 11.M scope-out). Section length 497 lines (within 380-480 target +17, well under the 560 trim threshold). One product decision locked: watermark step is **informational, not blocking** — on budget exhaustion `precheck_jsonb.watermark_check = "skipped_budget"` AND overall image status still resolves to "ready" if the 4 deterministic Pillow-based steps pass.

--- Sub-block 3: Architecture lock status ---

13 of 26 sections LOCKED: §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10. §11 in DRAFT awaiting founder review. 13 SKELETON remaining: §12, §13, §14, §15, §16, §17, §18, §19, §20, §21, §22, §22A. The §11 → §12 cadence continues the founder-review one-section-at-a-time protocol established at §0.

--- Sub-block 4: Construction blockers ---

NONE new. Construction remains gated on §11/§12/§13/§14 locking (4 module sections remaining) + the founder dispatch greenlight. The pricing_engine.py PricingAlert latent import bug stays queued for §12.

--- Sub-block 5: Hand-offs ---

- **meesell-image-precheck-builder** (AI track) — §11 contract is binding once locked. Specialist receives `docs/BACKEND_ARCHITECTURE.md §11 + §6A + §0-§6` as contract slice at construction dispatch. AI track owns the 5-step pipeline algorithm internals + watermark vision prompt (`prompt-engineer`); backend owns the Celery wrapper + DB write-back.
- **meesell-prompt-engineer** — `watermark.v1` prompt template authoring queued for §6A.G dispatch. Layer 1 hallucination prefix + few-shot examples + Layer 2 enum re-validation shape `{has_watermark: bool, confidence: float}` are §6A.E locked.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§10 LOCKED flip + §11 SKELETON → DRAFT), `docs/status/STATUS_BACKEND.md` (this single-section update block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-05 — §11 image LOCKED · §12 pricing DRAFT ===

Per the locked single-section-per-update protocol installed at the §9 lock turn. The prior turn's block above covered §10 LOCKED + §11 DRAFT — this entry adds only the deltas since that block.

--- Sub-block 1: §11 image LOCKED ---

Section 11 (Module: `image`) flipped DRAFT → LOCKED (2026-06-05). The locked contract specifies 2 endpoints: `POST /api/v1/products/{id}/images` (upload, 202 ACCEPTED) + `GET /api/v1/products/{id}/images` (poll-list, 200). 4-slot uniform pattern (idx 1-4, slot 1 required) per `MVP_ARCH §0` premise #3 is enforced as a structural DB CHECK constraint on `product_images` per §2.5 — NOT via plan_guard (4-slot is structural, not a billing-gated cap). 10 MB cap, JPEG only at the route boundary. GCS layout `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8`; signed URLs at 1h TTL. Celery task `image.precheck` (one of the only 2 modules with a `tasks.py` per §3.C — the other being `export` per §3.I) runs the 5-step pipeline: JPEG / RGB-vs-CMYK / ≥1500×1500 / white-background heuristic = deterministic Pillow steps; watermark = §6A.C `workload="watermark"`. **Watermark step is INFORMATIONAL, not blocking** — on `BudgetExceededError`, `precheck_jsonb.watermark_check = "skipped_budget"` AND the overall `status` still resolves to `"ready"` if the 4 deterministic Pillow steps pass (consistent with the §10 autofill founder principle: "do not penalize sellers for budget exhaustion they didn't cause"). Plan_guard NOT participating — the 4-slot DB CHECK is the structural limit, not a guard-gated cap. `modules/image/tasks.py` is one of only 2 modules with a `tasks.py` per the §3.C canonical subtree.

--- Sub-block 2: §12 pricing DRAFT this turn ---

Section 12 (Module: `pricing`) drilled SKELETON → DRAFT in this turn. The contract specifies 1 endpoint: `POST /api/v1/products/{id}/price-calc`. Deterministic P&L math — no AI track collaboration, no `ai_ops` invocation, no adapter usage. The 12-sub-section layout (12.A preamble + 12.B endpoint surface + nested 12.B.1 + 12.C service layer + 12.D repository + 12.E schemas + 12.F internal domain types + 12.G exception hierarchy + 12.H adapter usage + 12.I cross-cutting integrations + 12.J test plan + 12.K extraction notes + 12.L scope-out) lands at ~352 lines (within 300-400 target). **§12 formally resolves the latent `services/pricing_engine.py` PricingAlert import bug** flagged in §0.E + session 2 gap pass close-out. The fix is: DELETE the legacy `services/pricing_engine.py` (V0 code incompatible with the modular monolith file structure per §3.B) + CREATE `modules/pricing/service.py` from scratch + CREATE `modules/pricing/domain.py` with the new `PricingAlert` frozen dataclass + CREATE `modules/pricing/schemas.py` with the Pydantic v2 wire-shape models (which replaces the legacy `backend/app/schemas/pricing.py` deleted in session 2 gap pass). The resolution path is **delete legacy + write clean**, NOT "patch the import" — formally scoped to the §12 construction dispatch. Cross-module surfaces locked: `category.get_commission(category_id) -> Decimal | None` per §9.C (commission lookup) + `catalog.assert_product_ownership(product_id, user_id)` per §10.C (ownership gate). Plan_guard NOT participating (pricing is one of the 3 modules excluded from §4.E plan_guard alongside customer and dashboard). Rate-limit per-IP only (typing-rapid-iteration UX). 5 i18n keys queued for `messages_en.py` during services-builder dispatch (1× 400 input invalid + 1× 422 commission missing + 3× alert codes LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT). 3 alert rules locked at §12.F: `profit_pct < 10` → LOW_MARGIN, `mrp/input_cost > 3` → HIGH_MRP_MULTIPLIER, `profit < 50` → THIN_PROFIT (Tirupur-seller economics). Decimal precision throughout — banker's rounding ROUND_HALF_EVEN per CLAUDE.md numeric precision rule.

--- Sub-block 3: Architecture lock status ---

**14 of 26 sections LOCKED (54% — past halfway).** Locked: §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11. §12 in DRAFT awaiting founder review for LOCKED flip. SKELETON remaining (12): §13 dashboard, §14 export, §15 cross-cutting walkthrough, §16 inter-module rules, §17 endpoint inventory, §18 background jobs, §19 test strategy, §20 deployment topology, §21 extraction path, §22 acceptance, §22A risk register.

--- Sub-block 4: Construction blockers ---

No new blockers. The latent `pricing_engine.py` PricingAlert import bug noted in session 2 close-out is now formally scoped to the §12 construction dispatch as **delete + replace, not patch** — the legacy file is deleted at construction time, the new `modules/pricing/` files are written clean. Construction remains gated on §11/§12/§13/§14 module locks (3 module sections remaining after §11 locked this turn) + the cross-cutting §15-§22A sections + the founder dispatch greenlight.

--- Sub-block 5: Hand-offs ---

- **meesell-services-builder** — §12 construction dispatch (when contracted) MUST delete `backend/app/services/pricing_engine.py` outright as step 1 and create `modules/pricing/` from the §12 contract. The new `PricingAlert` lives in `modules/pricing/domain.py` per §12.F — NOT in `schemas/`. The `modules/pricing/schemas.py` Pydantic v2 file replaces the deleted legacy `backend/app/schemas/pricing.py`. No patch path; clean rewrite.
- **meesell-api-routes-builder** — receives `docs/BACKEND_ARCHITECTURE.md §12 + §10.C + §9.C + §0-§6A` as contract slice at construction dispatch. 1 endpoint surface (`POST /products/{id}/price-calc`) with rate-limit per-IP only and NO plan_guard.
- **meesell-database-builder** — no new migration work pending for §12; `pricing_calcs` table already exists per current head `f31c75438e61`.
- **meesell-prompt-engineer** — NOT participating. Pricing is deterministic.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§11 LOCKED flip + §12 SKELETON → DRAFT, full deep content), `docs/status/STATUS_BACKEND.md` (this single-section UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-05 — §12 pricing LOCKED · §13 dashboard DRAFT ===

Per the locked single-section-per-update protocol installed at the §9 lock turn. The prior turn's block above covered §11 LOCKED + §12 DRAFT — this entry adds only the deltas since that block.

--- Sub-block 1: §12 pricing LOCKED ---

Section 12 (Module: `pricing`) flipped DRAFT → LOCKED (2026-06-05). The locked contract specifies 1 endpoint: `POST /api/v1/products/{id}/price-calc`. Deterministic P&L math — no AI track collaboration, no `ai_ops` invocation, no adapter usage. Latent `services/pricing_engine.py` PricingAlert import bug resolution path is now formally LOCKED: DELETE legacy `backend/app/services/pricing_engine.py` + CREATE fresh `modules/pricing/{service.py, domain.py, schemas.py}`. The new `PricingAlert` frozen dataclass lives in `modules/pricing/domain.py` per §3.C per-module subtree, NOT in `schemas/` (the legacy `backend/app/schemas/pricing.py` was already deleted in session 2 gap pass). Banker's rounding (ROUND_HALF_EVEN) on all monetary values per CLAUDE.md numeric precision rule. 3 alert codes locked at §12.F: LOW_MARGIN (`profit_pct < 10`), HIGH_MRP_MULTIPLIER (`mrp/input_cost > 3`), THIN_PROFIT (`profit < 50`). plan_guard NOT participating (pricing is one of the 3 modules excluded from §4.E plan_guard alongside customer and dashboard).

--- Sub-block 2: §13 dashboard DRAFT this turn ---

Section 13 (Module: `dashboard`) drilled SKELETON → DRAFT in this turn. The contract specifies 1 endpoint: `GET /api/v1/products` (paginated product listing for Feature 8 Tracking Dashboard). **This is the purest demonstration of modular monolith discipline in the entire codebase** — dashboard owns ZERO tables, reads NOTHING directly, has NO `repository.py` file in its subtree (a structural deviation from the §3.C canonical 7-file layout, locked here explicitly so the absence reads as intentional design). It calls only `catalog.service.list_products(user_id, Pagination)` per §10.C + `customer.service.get_profile_completeness(user_id)` per §8.C. Per §2 founder ruling matrix kept at exactly 8 ✓ — V1 dashboard does NOT opt into `image.service.summary` (§11.C OPTIONAL) / `pricing.service.summary` (§12.C OPTIONAL) / `export.service.summary` (§14 OPTIONAL when authored) for richer status badges; V1.5 amendment may elevate the matrix to 11 ✓ but NOT now. 12 sub-sections authored (13.A preamble + 13.B endpoint surfaces with nested 13.B.1 + 13.C service layer 1-method surface + 13.D repository (NONE — structural absence locked) + 13.E Pydantic schemas + 13.F internal domain types + 13.G 1-class exception hierarchy + 13.H adapter usage NONE + 13.I cross-cutting integrations + 13.J test plan 3 unit + 2 integration + 13.K extraction notes + 13.L scope-out). Section length 310 lines (within 260-360 target). 1 i18n key queued for `messages_en.py` (`validation.dashboard.invalid_pagination`).

--- Sub-block 3: Architecture lock status ---

**15 of 26 sections LOCKED (58% — past halfway by 4 points).** Locked: §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12. §13 in DRAFT awaiting founder review for LOCKED flip. SKELETON remaining (11): §14 export, §15 cross-cutting walkthrough, §16 inter-module rules, §17 endpoint inventory, §18 background jobs, §19 test strategy, §20 deployment topology, §21 extraction path, §22 acceptance, §22A risk register. **Only ONE domain module section remains in SKELETON: §14 export** — the largest and densest of the 8 domain modules per the §5.5 Export Adapter contract.

--- Sub-block 4: Construction blockers ---

No new construction blockers. The latent `pricing_engine.py` PricingAlert import bug is now formally scoped to the §12 construction dispatch as **delete + replace, not patch**.

--- Sub-block 5: Hand-offs ---

- **meesell-services-builder** — §13 construction dispatch (when contracted) does NOT create a `modules/dashboard/repository.py` file. The 5-file dashboard subtree is locked: `__init__.py`, `router.py`, `service.py`, `schemas.py`, `domain.py`, `exceptions.py` only. The §19 CI linter that asserts per-module 7-file completeness must allowlist `dashboard` as a documented exception per §13.D.
- **meesell-api-routes-builder** — receives `docs/BACKEND_ARCHITECTURE.md §13 + §10.C + §8.C + §0-§6A` as contract slice at construction dispatch. 1 endpoint surface (`GET /api/v1/products`) with rate-limit per-IP only and NO plan_guard.
- **meesell-database-builder** — NOT participating for §13 (dashboard owns no tables).
- **meesell-prompt-engineer** — NOT participating (dashboard has no AI seam).

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§12 LOCKED flip + §13 SKELETON → DRAFT, full deep content), `docs/status/STATUS_BACKEND.md` (this single-section UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-05 — §13 dashboard LOCKED · §14 export DRAFT (FINAL domain module) ===

Per the locked single-section-per-update protocol installed at the §9 lock turn. The prior turn's block above covered §12 LOCKED + §13 DRAFT — this entry adds only the deltas since that block.

--- Sub-block 1: §13 dashboard LOCKED ---

Section 13 (Module: `dashboard`) flipped DRAFT → LOCKED (2026-06-05). The locked contract specifies 1 endpoint: `GET /api/v1/products` (paginated product listing for Feature 8 Tracking Dashboard). Dashboard owns ZERO tables — the only domain module with no DDL footprint at all per `MVP_ARCH §2`. NO `repository.py` file exists in `modules/dashboard/`'s subtree — a structural deviation from the §3.C canonical per-module 7-file layout, locked at §13.D explicitly so the absence reads as intentional design (not omission). The §19 CI linter that asserts per-module 7-file completeness carries `dashboard` as a documented allowlist exception. All reads flow through `catalog.service.list_products(user_id, Pagination)` per §10.C + `customer.service.get_profile_completeness(user_id)` per §8.C — the `scope_to_user(user_id)` enforcement happens at those services' own repository layers per §4.C. The §2.D cross-module matrix is preserved at exactly **8 ✓** — V1 dashboard does NOT opt into `image.service.summary` / `pricing.service.summary` / `export.service.summary` OPTIONAL surfaces for richer status badges; the V1.5 amendment may elevate the matrix to 11 ✓ but explicitly NOT now. Dashboard becomes its own BFF pod at V1.5 extraction with **zero data-layer migration** (no Alembic detach, no FK cascade redirect, no row-lock coordination) — one of the easiest extraction targets per §13.K alongside `export`.

--- Sub-block 2: §14 export DRAFT this turn — the FINAL domain module ---

Section 14 (Module: `export`) drilled SKELETON → DRAFT in this turn. **This is the LAST domain module section.** The contract specifies 2 endpoints: `POST /api/v1/products/{id}/export-xlsx` (initiate, 202) + `GET /api/v1/exports/{id}` (poll, 200). The entire **Export Adapter from `MVP_ARCH §5.5`** lives here: the 9-step pipeline orchestrator (one named method per step in `service.py` for unit-test isolation) + 2 `ComplianceStrategy` concrete subclasses (`StandardComplianceStrategy` pass-through for the 3,771 templates + `CollapsedComplianceStrategy` 9→3 derivation for the 1 Eye-Serum template at leaf 12378 per §0.G §12.6) + `MarketplaceExportAdapter` ABC for V2 readiness (V1 ships exactly one concrete subclass `MeeshoExportAdapter`; V2 will add Amazon / Flipkart / Etsy concretes per `MVP_ARCH §14`) + the 15 golden round-trip fixtures coverage matrix per `MVP_ARCH §5.7`. **The most-cross-module module in the codebase** per §2.D (4 outbound ✓ calls — to catalog, customer, category, image). Cross-module quad consumer: `catalog.get_product_for_export` + `customer.get_compliance_block` + `category.fetch_schema/get_field_enum/fetch_xlsx_aliases` + `image.list_images/get_image_bytes`. 13 lettered sub-sections authored (14.A preamble + 14.B endpoint surfaces with nested 14.B.1 + 14.B.2 + 14.C service layer 9-step pipeline as 9 named worker-internal helpers + 14.D repository 5 module-private methods + 14.E Celery task wrapper with the full 9-step flow comment + 14.F internal domain types — 5 frozen dataclasses + ComplianceStrategy ABC + 2 concretes + MarketplaceExportAdapter ABC + MeeshoExportAdapter concrete + 14.G Pydantic schemas + 14.H exception hierarchy 7 subclasses + 14.I adapter usage GCS-only + 14.J cross-cutting integrations + 14.K test plan + 15 golden fixtures matrix + 14.L extraction notes + 14.M scope-out). Section length **816 lines** (within 600-800 target +16, well under the 900 trim threshold).

**Philosophy M10 lives here.** Meesho format knowledge is structurally encapsulated: the three symbols `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` exist ONLY in `modules/export/{domain.py, service.py, tasks.py}` + the `adapters/gcs.py` write paths. They NEVER appear in API responses, AI prompts, or cache payloads outside this module. The §19 CI linter must enforce this with a forbidden-import rule on these three symbols — §14.J locks the structural enforcement.

**Layer 3 hallucination guardrail forward-reference RESOLVED.** Per `MVP_ARCH §9.7` + the §6A.E forward-reference, the Layer 3 deterministic enum re-validation lives at step 5 of the pipeline (`_translate_enums`) — every canonical enum value is looked up in `field_enum_values.enum_entries` via `category.service.get_field_enum`; unknown canonical raises `ExportEnumValidationError` (one of the 7 §14.H exception classes). This is the deterministic safety-net even if Layers 1+2 in §6A were bypassed by a future bug — three layers of F3-philosophy defence, the third independent of the AI stack entirely.

Plan_guard NOT participating in V1 — exports are core seller value (capping would damage the primary value prop). V1.5 may introduce per-tier export caps. Audit `export.initiated` on POST 2xx (middleware), `export.completed` / `export.failed` written directly from `tasks.py` (same documented-exception pattern as §6A.D cost_tracker + §7.B verify_otp + §11.E precheck task — worker tasks have no request-close hook for `audit_mw`). Rate-limit `export_initiate` 10/h/user on POST; per-IP only on GET poll. Tenancy enforced both at the application layer (`scope_to_user` on all 5 repository methods) AND at the object-store layer (`meesell-exports/{user_id}/...` GCS path prefix per §6.D). 7 i18n keys queued for `messages_en.py` during services-builder dispatch.

--- Sub-block 3: Architecture lock status ---

**16 of 26 sections LOCKED (62%).** Locked: §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12, §13. §14 in DRAFT awaiting founder review for LOCKED flip. **All 8 domain modules are now either LOCKED (7) or in DRAFT (1) after this turn.** SKELETON remaining (10): §15 cross-cutting walkthrough, §16 inter-module rules, §17 endpoint inventory, §18 background jobs, §19 test strategy, §20 deployment topology, §21 extraction path, §22 acceptance, §22A risk register — 10 cross-cutting / inventory / test / deployment / risks sections, lighter weight per-section than the per-module specs.

--- Sub-block 4: Construction state ---

Backend remains CONSTRUCTION-READY at the code level. After §14 locks, ALL 8 domain modules will be locked. Specialist construction can begin AFTER §14 lock IF founder rules to start parallel (per the new module-first construction model); otherwise the safer cadence is dispatching `meesell-auth-builder` first after §14 lock (per the FE-D5-ratified §7 contract), and dispatching the remaining specialists once the relevant cross-cutting §s (notably §19 test strategy + §18 background jobs) also land. No code-writing specialist has been dispatched in this drafting stretch.

--- Sub-block 5: Hand-offs ---

- **meesell-services-builder** — §14 construction dispatch (when contracted) will be the HEAVIEST single dispatch in the backend track (the entire Export Adapter from `MVP_ARCH §5.5` + ComplianceStrategy ABC + 2 concretes + MarketplaceExportAdapter ABC + MeeshoExportAdapter concrete + 9-step pipeline + 15 golden fixtures + 7 i18n keys + the Layer 3 guardrail at step 5). Receives `docs/BACKEND_ARCHITECTURE.md §14 + §10.C + §8.C + §9.C + §11.C + §6A + §0-§6` as the contract slice.
- **meesell-api-routes-builder** — receives §14 + §0-§6A + §10.C as contract slice for the 2 endpoint surfaces (POST initiate + GET poll).
- **meesell-database-builder** — NOT participating for §14 (the `exports` table already exists per current head `f31c75438e61`; no schema change requested).
- **meesell-prompt-engineer** — NOT participating (export is deterministic; no AI seam).
- **meesell-frontend-coordinator** — §14 surface contract is binding once locked. Frontend Feature 9 export-trigger UX consumes the `ExportRequest` + `ExportInitiatedResponse` + `ExportResponse` Pydantic shapes verbatim per §14.G.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§13 LOCKED flip + §14 SKELETON → DRAFT, full deep content), `docs/status/STATUS_BACKEND.md` (this single-section UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-05 — §14 export LOCKED (all 8 domain modules complete) · §15 cross-cutting DRAFT ===

Per the locked single-section-per-update protocol installed at the §9 lock turn. The prior turn's block above covered §13 LOCKED + §14 DRAFT — this entry adds only the deltas since that block.

--- Sub-block 1: §14 export LOCKED ---

Section 14 (Module: `export`) flipped DRAFT → LOCKED (2026-06-05). The entire Export Adapter from `MVP_ARCH §5.5` is now normative: 2 endpoints (`POST /api/v1/products/{id}/export-xlsx` initiate 202 + `GET /api/v1/exports/{id}` poll 200) + the 9-step pipeline orchestrator (one named method per step in `service.py` for unit-test isolation) + 2 `ComplianceStrategy` concrete subclasses (`StandardComplianceStrategy` 9→9 pass-through for the 3,771 templates + `CollapsedComplianceStrategy` 9→3 derivation for the 1 Eye-Serum template at leaf 12378 per §0.G §12.6) + `MarketplaceExportAdapter` ABC future-proofing for V2 multi-marketplace (V1 ships exactly one concrete subclass `MeeshoExportAdapter`) + 15 golden round-trip fixtures coverage matrix per `MVP_ARCH §5.7`. Layer 3 hallucination guardrail per `MVP_ARCH §9.7` LOCKED at step 5 of the pipeline (`_translate_enums`) — every canonical enum value is looked up in `field_enum_values.enum_entries` via `category.service.get_field_enum`; unknown canonical raises `ExportEnumValidationError`. The F3 three-layer defense is now FULLY WIRED across §6A Layers 1+2 (prompt prefix + parser re-validation with retries) + §14 Layer 3 (deterministic re-validation at export time, independent of the AI stack). Philosophy M10 STRUCTURALLY ENFORCED via §19 CI linter forbidden-import rule on the 3 symbols (`meesho_column_header` / `meesho_column_index` / `enum_codes_map`) — they exist ONLY in `modules/export/{domain.py, service.py, tasks.py}` + `adapters/gcs.py` write paths, NEVER in API responses or AI prompts. 7 exception subclasses under MeesellError, 7 i18n keys queued, GCS path `meesell-exports/{user_id}/{export_id}.zip` per §6.D + §11.E pattern. The most-cross-module module in the codebase per §2.D (4 outbound ✓ calls — catalog, customer, category, image). Plan_guard NOT participating (exports are core seller value; capping would damage the primary value prop — V1.5 may add per-tier export caps).

--- Sub-block 2: §15 cross-cutting walkthrough DRAFT this turn ---

Section 15 (Cross-Cutting Systems Walkthrough) drilled SKELETON → DRAFT in this turn. **This is the FIRST consolidation section** — it synthesizes multi-tenancy / caching / search / audit / AI ops / plan_guard / session-management / CSRF / observability / i18n across all 8 LOCKED domain modules. **No new contracts** — every claim cites the original locking section; §15 is the single-source-of-truth walkthrough that future readers consult when asking "how does X work across modules". 12 lettered sub-sections authored (15.A preamble + 15.B multi-tenancy + 15.C caching + 15.D search/indexing + 15.E audit log + coalescing + 15.F AI ops + 15.G plan_guard + 15.H session management + 15.I CSRF + 15.J observability + 15.K i18n + 15.L scope-out). 8 per-module matrices present (one per concern that varies across modules: multi-tenancy 8 rows + caching 8 rows + audit 8 rows + AI 8 rows + plan_guard 8 rows + i18n module-count summary; search/session/CSRF/observability are architectural singletons that do not need per-module matrices). The §15.B 3-layer multi-tenancy defence (app-level filter + service-layer ownership gate + GCS path prefix) is the consolidation of §4.C + `MVP_ARCH §10.4` + the per-module §I bullets. The §15.E audit table consolidates the 7 documented direct-write exceptions (cost_tracker / login / refresh / logout / precheck / export / razorpay) all citing the same "middleware cannot observe these events from the request close hook" rationale. The §15.F AI ops matrix confirms the closed `Literal["smart_picker", "autofill", "watermark"]` workload set with the orthogonality lock between the daily ₹500 cap (§6A.F global) and the per-user hourly plan_guard limits (§4.E). The §15.H FE-D5 session management subsection is the consolidated reference for the 3 founder-ratified coordinator counter-proposals (Lua EVAL atomicity + HMAC-pepper key + Path=/api/v1/auth correction). The §15.I CSRF subsection is the structural proof that V1 needs no CSRF token middleware (refresh cookie `SameSite=Strict` + access token Bearer-only). The §15.L deferral lists 8 sections that §15 explicitly does NOT cover (§16 inter-module rules through §22A risk register).

--- Sub-block 3: Architecture lock status — ALL 8 DOMAIN MODULES COMPLETE ---

**17 of 26 sections LOCKED (65%).** Locked: §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12, §13, §14. §15 in DRAFT awaiting founder review for LOCKED flip. **All 8 domain modules are now LOCKED** (§7 iam, §8 customer, §9 category, §10 catalog, §11 image, §12 pricing, §13 dashboard, §14 export). SKELETON remaining (9 — all consolidation / inventory / cross-cutting sections, NOT new design): §16 inter-module rules, §17 endpoint inventory, §18 background jobs / Celery, §19 test strategy, §20 deployment topology, §21 extraction path, §22 acceptance checklist, §22A risk register, plus §15 currently in DRAFT pending lock. The remaining sections are PRIMARILY CONSOLIDATION — they synthesize what's already locked across the per-module specs, not new contracts.

--- Sub-block 4: Construction state ---

Backend remains CONSTRUCTION-READY at the code level. With all 8 domain modules LOCKED, the consolidation sections §15-§22A are PRIMARILY documentation. Founder may dispatch specialist construction in parallel with §15-§22A authoring if desired — the per-feature contracts (§7-§14) are sufficient to dispatch individual specialists today. Recommended cadence: continue authoring §15 → §22A first (faster than expected since consolidation, not new design — §15 itself authored at 378 lines without introducing a single new lock), then dispatch construction with the complete architecture in hand. The latent `pricing_engine.py` PricingAlert import bug from session 2 close-out remains queued for §12 construction dispatch as DELETE legacy + CREATE clean (NOT patch the import). Decision deferred to founder: parallel-dispatch-now vs sequential-after-§22A.

--- Sub-block 5: Hand-offs ---

- **meesell-services-builder** — once §15-§22A also lock (or founder rules parallel dispatch), §14 export construction is the heaviest single dispatch in the backend track (entire Export Adapter + ComplianceStrategy ABC + 2 concretes + MarketplaceExportAdapter ABC + MeeshoExportAdapter concrete + 9-step pipeline + 15 golden fixtures + 7 i18n keys + Layer 3 guardrail at step 5). Receives `BACKEND_ARCHITECTURE.md §14 + §10.C + §8.C + §9.C + §11.C + §6A + §0-§6 + §15.B + §15.E + §15.F + §15.K` as contract slice.
- **meesell-api-routes-builder** — receives §14 + §0-§6A + §10.C + §15.B + §15.G for the 2 endpoint surfaces (POST initiate + GET poll).
- **meesell-database-builder** — NOT participating for §14 (the `exports` table already exists per current head `f31c75438e61`; no schema change requested).
- **meesell-prompt-engineer** — NOT participating (export is deterministic; no AI seam).
- **meesell-frontend-coordinator** — §14 surface contract is now BINDING. Frontend Feature 9 export-trigger UX consumes the `ExportRequest` + `ExportInitiatedResponse` + `ExportResponse` Pydantic shapes verbatim per §14.G.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§14 LOCKED flip + §15 SKELETON → DRAFT, full deep content at 378 lines / 12 sub-sections), `docs/status/STATUS_BACKEND.md` (this single-section UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-06 — §15 cross-cutting walkthrough LOCKED · §16 inter-module rules DRAFT ===

Per the locked single-section-per-update protocol. The prior turn's block above covered §14 LOCKED + §15 DRAFT — this entry adds only the deltas since that block.

--- Sub-block 1: §15 cross-cutting walkthrough LOCKED ---

Section 15 (Cross-Cutting Systems Walkthrough) flipped DRAFT → LOCKED (2026-06-06). The single source of truth for **10 cross-cutting concerns** across all 8 LOCKED domain modules is now normative: multi-tenancy (§15.B) + caching strategy (§15.C) + search & indexing (§15.D) + audit log + autosave coalescing (§15.E) + AI operations (§15.F) + plan_guard (§15.G) + session management / refresh-token allowlist + FE-D5 (§15.H) + CSRF posture V1 (§15.I) + observability — Prometheus + LangFuse (§15.J) + i18n + locale fallback (§15.K). 8 per-module participation matrices locked (multi-tenancy / caching / audit / AI / plan_guard / i18n + scope-out + preamble). No new contracts — every claim cites the original locking section (§4.C for app-level filtering, §4.D for cache keys, §4.E for plan_guard limits, §6A for AI workloads, §11.8 / §11.9 for audit table + field-names-only PII redaction, FE-D5 amendments at §4.B + §4.G, etc.). ~50 i18n message IDs consolidated across the 8 modules + the cross-cutting `core/` + `server` buckets. Layer 3 hallucination guardrail wiring confirmed across §6A Layers 1+2 + §14.J Layer 3 (the structural M10 enforcement of the 3 meesho-format symbols confined to `modules/export/{domain,service,tasks}.py` + `adapters/gcs.py` write paths via §19 forbidden-import rule). The §15.H FE-D5 session-management subsection is the consolidated reference for the 3 founder-ratified coordinator counter-proposals (Lua EVAL atomicity + HMAC-pepper key + `Path=/api/v1/auth` cookie correction). The §15.I CSRF subsection is the structural proof that V1 needs no CSRF token middleware (refresh cookie `SameSite=Strict` + access token Bearer-only).

--- Sub-block 2: §16 inter-module rules DRAFT this turn ---

Section 16 (Inter-Module Communication Rules) drilled SKELETON → DRAFT in this turn at **427 lines** (within 380-500 target) across **9 lettered sub-sections** (16.A preamble + 16.B the 8 allowed calls + 16.C 4 file-level rules + 16.D cross-cutting layer exception + 16.E import-linter configuration + 16.F 2 documented structural exceptions + 16.G V1.5 extraction preserves call sites + 16.H catalog spine rule + extraction order + 16.I scope-out). **Operationalizes** the §2.D matrix (8 ✓ cross-module calls) into CI-enforced `import-linter` rules + file-level public/private boundaries (`service.py` = PUBLIC, `repository.py` = PRIVATE, `schemas.py` = PRIVATE wire-shape, `domain.py` = exchange currency via service-return-type signatures, `router.py` + `tasks.py` = NEVER cross-module). The 8-call matrix at §16.B is a verbatim consolidation of the §2.D ✓ cells — caller→callee→method→purpose→locking section. The export 8th-row expansion (§16.B.1) enumerates the 4 distinct callees (catalog `get_product_for_export` + customer `get_compliance_block` + category `fetch_schema` + `get_field_enum` + image `get_image_bytes`). §16.B.2 clarifies that the 8-count is the matrix count not the service-method count (6 distinct methods power 8 ✓ cells via shared seam pattern — `assert_product_ownership` consumed by image + pricing, `fetch_schema` consumed by catalog + export). §16.E ships a 7-contract `tests/lint/import_rules.toml` sketch (repository-private + adapters.gemini-forbidden + M10 symbols + schemas-private + ai_ops 3-consumer-only + domain.py signature-based rule deferred to PR review + router/tasks not cross-module). The 2 documented structural exceptions preserved verbatim from their original locking sections: dashboard NO repository per §13.D + category NO user_id per §9.D — both with CI linter allowlist instructions for §19. The V1.5-extraction-preserves-call-sites contract locked at §16.G with before/after Python code example showing catalog's `await fetch_schema(...)` call site UNCHANGED across V1 in-process vs V1.5 HTTP-shim modes (the shim lives at `core/extracted_clients/category_client.py` per §16.D.4). §16.H locks the catalog-spine rule + the 8-step extraction order (export first, catalog last, with rationale per step). §16 does NOT introduce a single new cross-module call site — every allowed call cites the §2.D matrix.

--- Sub-block 3: Architecture lock status — 18 of 26 sections LOCKED (69%) ---

Section state at the close of this turn:
- **LOCKED (18):** §0, §1, §2, §3, §4, §5, §5A, §6, §6A, §7, §8, §9, §10, §11, §12, §13, §14, §15.
- **DRAFT (1):** §16 (enters DRAFT this turn; awaiting founder review for LOCKED flip).
- **SKELETON (7):** §17 endpoint inventory, §18 background jobs (Celery), §19 test strategy, §20 deployment topology, §21 extraction path, §22 acceptance & sign-off, §22A risk register.

The 7 SKELETON sections remaining are PRIMARILY CONSOLIDATION + INVENTORY — they synthesize what's already locked across §0-§15 + the per-module specs, not new contracts. Pace expected to stay brisk (§15 authored at 378 lines without introducing a single new lock; §16 at 427 lines is similarly consolidation-only).

--- Sub-block 4: Construction state ---

Backend remains CONSTRUCTION-READY at the code level. With all 8 domain modules + §15 now LOCKED, the consolidation sections §16-§22A are PRIMARILY documentation. The §16 import-linter rule set is locked and §19 will implement the executable wiring; specialists building code today MUST pre-respect the §16.C 4 file-level rules + §16.D adapter/ai_ops boundary even though the CI linter lands at §19 dispatch time. The latent `pricing_engine.py` PricingAlert import bug from session 2 close-out remains queued for §12 construction dispatch as DELETE legacy + CREATE clean (NOT patch the import). Decision deferred to founder: parallel-dispatch-now vs sequential-after-§22A. **No new construction blockers introduced this turn.**

--- Sub-block 5: Hand-offs ---

- **meesell-services-builder** — when dispatched, MUST respect §16.C 4 file-level rules + §16.D adapter/ai_ops boundary BEFORE §19 CI linter lands. The 8 allowed cross-module calls per §16.B are the ONLY allowed inter-module service-call surface; any new call requires a §2.D matrix amendment.
- **meesell-api-routes-builder** — receives §16 as binding contract for endpoint registration in `app/main.py` (router imports cross-module are allowed at main.py per §16.E contract 7 ignore_imports allowlist; routers MUST NOT cross-module import other routers).
- **meesell-database-builder** — NOT participating for §16 (no schema change; §16 is pure communication-rule).
- **meesell-frontend-coordinator** — informational: the V1.5 extraction-preserves-call-sites contract per §16.G is the backend's guarantee that FE service contracts (the 27 endpoints per §17) will NEVER change shape during V1.5 extraction. Wire shapes are stable across V1 → V1.5 because the §16.G shim preserves both the Python signature internally AND the HTTP envelope externally.
- **meesell-infra-builder** — informational: per §16.H 8-step extraction order, the V1.5 manifests must support per-module pod extraction in this order: export → dashboard → image → pricing → customer → category → iam → catalog. The exact K3s manifest pattern lives in §20.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch): 3 — `docs/BACKEND_ARCHITECTURE.md` (§15 LOCKED flip + §16 SKELETON → DRAFT, full deep content at 427 lines / 9 sub-sections), `docs/status/STATUS_BACKEND.md` (this single-section UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-06 — BACKEND_ARCHITECTURE.md COMPLETE (26 of 26 sections LOCKED) ===

Founder pre-authorized batch completion: §16 LOCKED flip + §17 through §22A drafted and self-locked in a single coordinator turn under the new batch-completion-under-pre-authorization protocol. Founder will review the complete architecture as a whole; no per-section review cycle for these 7 final sections. **BACKEND_ARCHITECTURE.md is now 100% complete at 8,042 lines across 26 LOCKED sections.**

--- Sub-block 1: Architecture state — 26 of 26 sections LOCKED = 100% complete ---

Final section state (all LOCKED):
- **§0 Architectural Premises** — LOCKED (2026-06-05). 27-endpoint contract, 13 tables, premises.
- **§1 System Topology** — LOCKED (2026-06-05). ASCII diagram, request/job flows, vendor egress map.
- **§2 Module Catalog** — LOCKED (2026-06-05). 8 domain modules + 5 non-domain layers + 8 ✓ cross-module matrix.
- **§3 File Structure** — LOCKED (2026-06-05). Canonical 7-file subtree, decision tree, `ai_ops/` + `i18n/` additions.
- **§4 `core/` Cross-Cutting Foundation** — LOCKED (2026-06-05). auth + tenancy + cache + plan_guard + errors + 6-middleware chain + FE-D5 CORS amendment.
- **§5 `shared/` Foundation Layer** — LOCKED (2026-06-05). database, valkey, config (11 env-var groups), 13 ORM models.
- **§5A Presentation Layer Contract + i18n** — LOCKED (2026-06-05). schema_jsonb envelope, 11 primitives, enum_resolver, 3-segment message_id convention.
- **§6 `adapters/` Third-Party Vendor Clients** — LOCKED (2026-06-05). 5 adapter contracts (gemini/msg91/gcs/razorpay/langfuse).
- **§6A AI Operations Layer** — LOCKED (2026-06-05). 6 files, 3 workloads, ₹500 daily cap, 3-layer guardrail, 3 golden eval sets.
- **§7 Module: iam** — LOCKED (2026-06-05). 4 V1 contract + 2 infrastructure surfaces, Lua rotation script verbatim.
- **§8 Module: customer** — LOCKED (2026-06-05). 5 surfaces, 9-method service, COMPLIANCE_EXTENSION_MAP.
- **§9 Module: category** — LOCKED (2026-06-05). 5 surfaces, no scope_to_user (global), single-flight cache.
- **§10 Module: catalog** — LOCKED (2026-06-05). 6 surfaces, the central spine, assert_product_ownership seam.
- **§11 Module: image** — LOCKED (2026-06-05). 2 surfaces, 5-step Celery precheck, informational watermark.
- **§12 Module: pricing** — LOCKED (2026-06-05). 1 surface, deterministic P&L, pricing_engine.py delete-and-rewrite resolution.
- **§13 Module: dashboard** — LOCKED (2026-06-05). 1 surface, ZERO tables, NO repository.
- **§14 Module: export** — LOCKED (2026-06-05). 2 surfaces, 9-step pipeline, 2 ComplianceStrategy concretes, 15 golden fixtures.
- **§15 Cross-Cutting Systems Walkthrough** — LOCKED (2026-06-06). 10 concerns + ~50 i18n keys consolidated.
- **§16 Inter-Module Communication Rules** — LOCKED (2026-06-06). 8-call matrix operationalized, 7 import-linter contracts, V1.5 extraction-preserves-call-sites.
- **§17 Endpoint Inventory** — LOCKED (2026-06-06). 27 + 2 = 29 routes master registry, auth/rate-limit/plan-guard/audit columns; 172 lines.
- **§18 Background Jobs (Celery)** — LOCKED (2026-06-06). 2 task contracts (image.precheck + export.generate), retry policy, no-DLQ-V1 policy, worker JWT re-validation; 174 lines.
- **§19 Test Strategy** — LOCKED (2026-06-06). 6-layer pyramid, 10 CI linter contracts (7 import-linter + 3 custom AST), performance budgets, coverage targets, multi-tenant isolation regression; 228 lines.
- **§20 Deployment Topology V1** — LOCKED (2026-06-06). 4-pod topology, env-var injection per §5.D, 3 PENDING secrets flagged, K3s manifest sketches, V1.5 extraction-prep posture; 248 lines.
- **§21 Extraction Path V1.5/V2** — LOCKED (2026-06-06). 8-step extraction order consolidated from §16.H, per-module readiness checklist, V1.5/V2 milestones, hybrid-mode operating posture; 153 lines.
- **§22 Acceptance & Sign-Off** — LOCKED (2026-06-06). V1_FEATURE_SPEC Features 1-9 backend criteria + cross-cutting + sign-off responsibilities; 167 lines.
- **§22A Risk Register & Mitigations** — LOCKED (2026-06-06). 12 backend risks with severity scores 8-20/25, top-3 critical, post-V1 review cadence; 160 lines.

--- Sub-block 2: Key facts ---

- **8 domain modules locked** (`iam`, `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`).
- **5 non-domain layers locked** (`core/`, `shared/`, `adapters/`, `ai_ops/`, `i18n/`).
- **10 cross-cutting concerns walked** in §15 (multi-tenancy + caching + search + audit + AI ops + plan_guard + session mgmt + CSRF + observability + i18n).
- **~50 i18n message IDs** consolidated across the 8 modules + `core/` + `server` buckets per §15.K.
- **27 contract endpoints + 2 infrastructure surfaces = 29 routes** mounted on `app/main.py` per §17.B.
- **8 ✓ cross-module matrix** per §2.D, operationalized as CI-enforced rules per §16.
- **7 import-linter contracts + 3 custom AST scanners = 10 CI gates** per §19.C.
- **15 golden round-trip XLSX fixtures** per §14.K + §19.B Layer 3.
- **3 golden AI eval sets** per §6A.H + §19.B Layer 4 (Smart Picker recall ≥80% / Autofill 0% invalid enums / Watermark accuracy ≥85%).
- **3-layer F3 hallucination guardrail** spanning §6A Layers 1+2 + §14.J Layer 3 (Layer 3 deterministic re-validation at export time as safety net per §22A.B R1).
- **4 plan_guard resources** per §4.E (product_count + ai_autofill_hourly + smart_picker_hourly + create_product_hourly).
- **Daily ₹500 AI budget cap** with graceful fallback per workload per §6A.F (Smart Picker → empty list, Autofill → empty 200, Watermark → skipped_budget).
- **FE-D5 split-token + server-side-revocation pattern** per §4.B + §15.H amendments (access JWT in-memory + refresh cookie HttpOnly+Secure+SameSite=Strict + HMAC-pepper Valkey allowlist + Lua EVAL atomic rotation).
- **12 risks in §22A register** with severity scores 8-20/25; 2 CRITICAL (R1 AI hallucination + R6 FSSAI compulsory at signup), 6 HIGH, 4 MEDIUM, 0 LOW.

--- Sub-block 3: Construction state ---

Backend remains **CONSTRUCTION-READY at code level**. With all 26 sections LOCKED, the architecture is now the complete contract specialists construct against. Recommended sequence:
1. Founder reviews whole architecture (this is the founder's pre-authorized review-as-a-whole moment).
2. On founder approval, dispatch first construction target: **`meesell-auth-builder`** for §7 (iam module) per the session 2 first-action recommendation, with the FE-D5 split-token + server-side-revocation pattern as the construction contract slice.
3. Sequential construction follows the §21 extraction-order INVERSE — easiest to extract = easiest to construct = first to ship. Actual construction order recommendation: iam first (auth unblocks every other module's `get_current_user` dep) → customer → category → catalog → image → pricing → dashboard → export.

The latent `pricing_engine.py` PricingAlert import bug from session 2 close-out remains queued for §12 construction dispatch as **DELETE legacy + CREATE clean** per §12.A locked resolution path. First action of §12 dispatch is `rm backend/app/services/pricing_engine.py`, then create fresh `modules/pricing/{service,domain,schemas}.py` per §3.C canonical 7-file subtree.

--- Sub-block 4: 3 Secret Manager containers still PENDING ---

The infra-builder Phase A populated 7 of 10 backend-side secrets. **3 secrets remain PENDING** and MUST be populated by infra-builder during the corresponding specialist construction dispatch:
- `refresh-token-pepper` — to be populated during `meesell-auth-builder` (iam) construction dispatch per §15.H + §20.C.
- `razorpay-webhook-secret` — to be populated during `meesell-auth-builder` (iam) construction dispatch per §6.E + §20.C.
- `langfuse-secret-key` — to be populated during `meesell-services-builder` (ai_ops integration) construction dispatch per §6.F + §6A.J + §20.C.

Per §5.D + §20.C the populate command is `gcloud secrets versions add <secret-id> --project=project-1f5cbf72-2820-4cdb-949 --data-file=- <<< "$VALUE"`. Coordinator does NOT populate (per §5.D infra-side rule); the infra-builder owns the invocation when the specialist signals readiness.

--- Sub-block 5: Latent bugs queued ---

- **§12 pricing_engine.py** — DELETE-AND-REWRITE path LOCKED at §12.A. First action of construction dispatch: `rm backend/app/services/pricing_engine.py`. Then specialist creates `modules/pricing/service.py` + `modules/pricing/domain.py` (with new `PricingAlert` frozen dataclass) + `modules/pricing/schemas.py` per §3.C subtree + §12.F design. Risk severity 15/25 HIGH per §22A.B R12.

--- Sub-block 6: Specialist hand-offs queued ---

When founder dispatches construction, the specialists receive their per-module section + the cross-cutting sections relevant to their scope as contract slice:

- **meesell-auth-builder** (FIRST DISPATCH RECOMMENDATION) — receives §7 + §4.B + §4.G + §15.H + §6.C + §6.E + §0-§6A as contract slice. Acceptance: 4 V1 contract endpoints + 2 infrastructure surfaces + Lua EVAL rotation + FE-D5 acceptance integration tests per §19.B. Populates `refresh-token-pepper` + `razorpay-webhook-secret` PENDING secrets via infra-builder.
- **meesell-database-builder** — NO new dispatch needed in V1 (the 13-table schema at head `f31c75438e61` matches §5.E + `MVP_ARCH §2`). V1.5 RLS migration is its first V1.5 dispatch.
- **meesell-api-routes-builder** — receives per-module §X.B + §X.E sections + §17 master registry + §4.G middleware chain + §15.B-K cross-cutting as contract slice. Mounts the 29 routes on `app/main.py` per §17.B + §17.B.2.
- **meesell-services-builder** — receives per-module §X.C + §X.D + §X.F sections + §16.B 8-call matrix + §15.B tenancy + §15.E audit + §15.F AI ops + §6A integration as contract slice. Heaviest single dispatch is §14 export (entire ComplianceStrategy ABC + 2 concretes + 9-step pipeline + 15 golden fixtures + Layer 3 guardrail). Populates `langfuse-secret-key` PENDING secret via infra-builder.
- **meesell-prompt-engineer** (AI track) — receives §6A.G + the 3 prompt slots (`smart_picker.v1`, `autofill.v1`, `watermark.v1`) per §6A.A + §6A.H eval set thresholds as contract slice.
- **meesell-image-precheck-builder** (AI track) — receives §11.E 5-step pipeline + §6A.F informational watermark posture + §22A.B R1 Layer 1+2+3 guardrail integration as contract slice.

--- Sub-block 7: Next steps for master session ---

1. **Founder reviews the complete architecture as a whole** (per the batch-completion-under-pre-authorization protocol).
2. On founder approval, master session dispatches the **first construction target: `meesell-auth-builder`** for §7 iam module + FE-D5 acceptance integration tests.
3. Infra-builder populates the 2 PENDING auth-side secrets (`refresh-token-pepper`, `razorpay-webhook-secret`) before or during the auth-builder dispatch.
4. Construction sequence proceeds per the recommended order in Sub-block 3.
5. STATUS_BACKEND.md continues per-section update protocol — each construction dispatch returns 1 UPDATE block.

--- Sub-block 8: Cross-track blockers ---

**No new cross-track blockers introduced this turn.** All cross-track contracts are stable:
- FE-D5 + FE-D6 amendments preserved at §4.B + §4.G + §15.H.
- 27 endpoint contract locked at §0.C amendment with §17 master registry consolidation.
- V1.5 extraction-preserves-call-sites contract locked at §16.G with §21 per-module roadmap.

Blockers: none.

Files touched this turn (coordinator-direct, no specialist dispatch — batch completion under founder pre-authorization): **3** — `docs/BACKEND_ARCHITECTURE.md` (§16 LOCKED flip + §17-§22A SKELETON → LOCKED full deep content at ~1,302 lines new content / 7 sections), `docs/status/STATUS_BACKEND.md` (this comprehensive completion UPDATE block), `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (batch-completion turn entry). STATUS_MASTER.md NOT touched (master session owns it per the locked lock protocol).
=========

=== UPDATE: 2026-06-06 — §5 shared/ CONSTRUCTED (sub-session: meesell-backend-construction-5-shared-1) ===

**Wave 1/10 first construction sub-session complete.** §5 Foundation Layer code is in place and acceptance-verified by master session. This entry is master-applied because the sub-session reported completion without writing its own STATUS entry per protocol §5.1; the code passes all acceptance criteria — only the documentation update was missing.

**Files created** (`backend/app/shared/`):
- `database.py` — SQLAlchemy 2.0 async engine + `Base` (DeclarativeBase) + `AsyncSessionLocal` factory + `get_db` FastAPI dependency + `make_worker_session` NullPool helper for Celery
- `valkey.py` — `redis.asyncio` client + 4 DB-selector factories (`get_valkey_otp` DB 0 / `get_valkey_broker` DB 1 / `get_valkey_results` DB 2 / `get_valkey_cache` DB 3) + `aclose_all` lifecycle hook
- `config.py` — Pydantic Settings singleton with the full §5.D env-var registry
- `models/__init__.py` — single canonical import path for all 13 ORM models per §5.E lock
- `models/{user,seller_profile,template,category,field_enum_value,field_alias,catalog,product,product_image,pricing_calc,export,audit_event,product_draft}.py` — 13 ORM models + `models/base.py` re-export

**Tests added** (`backend/tests/`):
- `test_shared_config.py` — 28 tests (env-var registry coverage, validators, defaults, secret-sourcing)
- `test_shared_database.py` — 8 tests (engine + AsyncSession + get_db lifecycle + make_worker_session NullPool)
- `test_shared_valkey.py` — 10 tests (4 factory DB selectors + aclose_all idempotency + lazy-init pattern)
- **§5 new tests subtotal: 46/46 pass**

**Acceptance verification (master-run):**
1. ✅ Architecture lock count: 26/26 LOCKED unchanged
2. ✅ `pytest tests/test_app_boot_integration.py`: 7/7 pass (no regression)
3. ✅ `pytest tests/test_database.py`: 42/42 pass (no regression)
4. ✅ `pytest tests/test_shared_*.py`: 46/46 pass (new §5 tests)
5. ✅ `ruff check app/shared/`: clean ("All checks passed!")
6. ✅ Total pytest: 95/95 passing
7. ✅ Import-linter contracts not yet applicable (no domain modules yet to enforce against — §16.E rules engage at §7 dispatch)

**Decisions made by sub-session (verified consistent with locked architecture):**
- `Base` (DeclarativeBase) lives in `shared/database.py` and is re-exported from `shared/models/base.py` for backward-compat with the existing `backend/app/models/base.py` pattern from session 2 Phase 1 (per §5.E locked rule).
- `make_worker_session` survives as a peer helper in `shared/database.py` with `NullPool` for Celery's `asyncio.run()` Future-binding reason (per §5.B locked rule).
- ORM style: SQLAlchemy 2.0 `Mapped[T]` typed throughout (per database-builder Phase 1 conventions; consistent with §5.E lock).
- `models/__init__.py` import order follows FK topological dependency chain so relationships resolve on first access without manual `configure_mappers()`.

**Hand-offs to §4 core/ (next dispatch, Wave 1 step 2):**
- `core/auth.py` can now `from app.shared.database import get_db` + `from app.shared.models import User`
- `core/cache.py` can now `from app.shared.valkey import get_valkey_cache`
- `core/middleware/rate_limit_mw.py` can now `from app.shared.valkey import get_valkey_otp`
- `core/errors.py` can now `from app.shared.config import settings`
- All 13 models importable via `from app.shared.models import Foo, Bar` per the §5.E canonical import path

**Pending secrets (Wave 1 has none for §5):** N/A.
**Latent bugs:** None for §5.
**Documentation gaps backfilled by master this entry:** This STATUS_BACKEND UPDATE block (sub-session did not write its own). Master will also update STATUS_MASTER.md. Specialist memory append remains pending; the STATUS files are the authoritative trail.

**Sub-session acceptance verdict:** ✅ **PASS**

**Next dispatch target per protocol §1.3 Wave 1 sequence:** §4 `core/` Cross-Cutting Foundation — prompt at `docs/sub_session_prompts/wave_1_foundation_construction/02-section-4-core-construction.md`. The §4 sub-session consumes the §5 contracts locked above as its upstream dependency.

=========

=== UPDATE: 2026-06-06 — §4 core/ CONSTRUCTED ===

Files created (13 files / ~1,940 LOC):
- `backend/app/core/__init__.py` (16)
- `backend/app/core/auth.py` (405) — owner: meesell-auth-builder; CurrentUser + get_current_user + issue_access_token + issue_refresh_token + refresh_allowlist_key (HMAC-with-pepper) + REFRESH_ROTATE_LUA + rotate_refresh_token (EVALSHA→EVAL fallback) + TokenMissingError / TokenExpiredError / UserNotFoundError. Per §4.B + FE-D5 amendment.
- `backend/app/core/tenancy.py` (~130) — assert_owned + scope_to_user + TenantViolationError. Per §4.C.
- `backend/app/core/cache.py` (~160) — get_or_set + etag_for + prewarm_top_categories (stub). Versioned key `meesell:v{cache_version}:{key}`. SET NX EX single-flight + polling fallback. Per §4.D.
- `backend/app/core/plan_guard.py` (~200) — enforce_plan_limit over 4 V1 resources (product_count + ai_autofill_hourly + smart_picker_hourly + create_product_hourly) + V1_LIMITS_FREE + PlanLimitExceededError. Sliding-window on Valkey DB 0; product_count via DB COUNT(*). Per §4.E.
- `backend/app/core/errors.py` (~250) — MeesellError root + register_error_handlers (5 handlers: MeesellError + RequestValidationError + PydanticValidationError + HTTPException + Exception) + i18n resolver as deferred wire (try/except ImportError fallback). Per §4.F.
- `backend/app/core/middleware/__init__.py` (13)
- `backend/app/core/middleware/request_id.py` (~60) — UUIDv4 generation + X-Request-ID header propagation.
- `backend/app/core/middleware/auth_mw.py` (119) — owner: meesell-auth-builder; AuthContextMiddleware fail-open opportunistic decode → request.state.user. Per §4.G.
- `backend/app/core/middleware/tenancy_mw.py` (~35) — TenancyContextMiddleware pure-copy of user_id.
- `backend/app/core/middleware/rate_limit_mw.py` (~240) — per-IP + per-route sliding-window via Valkey DB 0 sorted-sets. Per-route via @rate_limit decorator attaching __rate_limit__ to handler; middleware walks app.router.routes[r].matches(scope). Inline JSONResponse on 429 (BaseHTTPMiddleware bypasses error handlers — documented).
- `backend/app/core/middleware/plan_guard_mw.py` (~30) — V1 NO-OP placeholder.
- `backend/app/core/middleware/audit_mw.py` (~290) — post-2xx audit_events insert + PII scrubbing (phone SHA-256 with AUDIT_PII_SALT; FSSAI/GST stripped) + 5-min coalescing for autosave path + drop-on-failure per §1.E.
- `backend/app/main.py` rewired — 7 middleware registered in REVERSE for §4.H canonical runtime order: CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route) → audit_mw. CORS reads CORS_ALLOWED_ORIGINS + CORS_ALLOW_CREDENTIALS from settings (never "*"). register_error_handlers(app) invoked. prewarm_top_categories(100) hooked into lifespan startup (try/except so prewarm failure does not block boot).

Tests added (12 files / 53 new cases — all PASS):
- test_core_errors.py — 6 cases (envelope shape, 4 registered handlers, i18n deferred wire fallback).
- test_core_tenancy.py — 5 cases (assert_owned ok/violation; scope_to_user adds WHERE; multi-user isolation).
- test_core_cache.py — 5 cases (versioned key, miss-then-hit, single-flight dedupes 10 concurrent, etag_for quoted sha256, prewarm stub).
- test_core_plan_guard.py — 9 cases (3 sliding-window resources + batch + recover + product_count DB path).
- test_core_middleware_ordering.py — 4 cases (boot-time §4.H ordering assertion, 7-middleware count, names).
- test_core_audit_mw.py — 7 cases (2xx writes + PII scrubbing, 4xx/5xx skip, autosave coalesce, non-autosave no-coalesce).
- test_core_rate_limit_mw.py — 3 cases (per-IP 429, per-route 429, fail-open on Valkey unreachable).
- test_core_auth.py — 9 cases (issue tokens, claim shape, HMAC key, compare_tokens, get_current_user happy/missing/expired/malformed/unknown).
- test_core_auth_middleware.py — 5 cases (fail-open on no-header/malformed/expired, attaches on valid).
- test_core_auth_rotation.py — 4 cases (3 live-Valkey + 1 sanity): atomic swap, replay-after-rotation returns False, EVALSHA→EVAL fallback. 3 skip cleanly when Valkey DB-0 broker port 6381 not tunnel-routed.
- `tests/conftest.py` — `use_live_valkey` fixture rewritten to use monkeypatch.setattr on every consumer namespace (no module singleton mutation; per-test fresh client in current loop). Fixes pytest-asyncio + module-singleton cross-loop binding (root cause: previous fixture mutated `app.shared.valkey._cache_client` which carried session-loop bindings across function-scope tests).

Decisions made (FLAGGED — not in locked architecture):
1. `oauth2_scheme.tokenUrl="/api/v1/auth/otp/verify"` — points OpenAPI Authorize button at the issuance endpoint.
2. Malformed-vs-missing token both raise `TokenMissingError` (401 / auth.token_missing); expired alone is `TokenExpiredError` (401 / auth.token_expired). §4.B states "missing/malformed → token_missing" — honoured.
3. `RateLimitMiddleware` returns `JSONResponse` inline (does NOT raise) because `BaseHTTPMiddleware` exceptions bypass FastAPI's registered exception handlers. Envelope still matches `{detail, code, validation_message_id, request_id}`. `RateLimitExceededError` class still exposed for service-layer use.
4. `plan_guard.enforce_plan_limit(product_count, ...)` requires `db: AsyncSession` kwarg — picked `SELECT COUNT(*)` over Valkey-counter to avoid dual-source-of-truth drift with the products table.
5. Per-route rate-limit lookup walks `app.router.routes[r].matches(scope)` manually (request.scope["route"] is None at BaseHTTPMiddleware entry; Starlette populates during routing).
6. errors.py registers both `RequestValidationError` (FastAPI body validation) AND bare `PydanticValidationError` (service-layer model_validate) with the same handler — §4.F mentioned only the latter; both cover the wire.
7. `use_live_valkey` rewritten to monkeypatch-based fixture (not singleton-pivot) — robust against pytest-asyncio multi-loop scope.

Hand-offs queued:
- §5A `i18n/` — consumes `core/errors.py:_resolve_message_id` deferred wire. When i18n/resolver.py lands, the try/except ImportError block automatically activates real resolution; no errors.py change required.
- §7 `iam` (next dispatch) — consumes `core/auth.py:get_current_user` + `core/auth.py:issue_access_token` + `core/auth.py:issue_refresh_token` + `core/auth.py:refresh_allowlist_key` + `core/auth.py:rotate_refresh_token` + `AuthContextMiddleware`. Will delete `backend/app/middleware/auth.py` legacy and rewrite `app/routers/auth.py` against the new core/ surface.
- §9 `category` — consumes `core/cache.py:get_or_set` + `core/cache.py:etag_for` + replaces `prewarm_top_categories` stub with real top-100 warm.
- §10 `catalog` — consumes `core/tenancy.py:scope_to_user` + `core/tenancy.py:assert_owned` + `core/plan_guard.py:enforce_plan_limit("product_count" | "create_product_hourly" | "ai_autofill_hourly")`.
- Every later module — subclasses `MeesellError`; uses `core/tenancy.py` scoping; touches `core/cache.py` on cached reads; trips `core/plan_guard.py` on budgeted writes.
- §17 routes-builder — uses `@rate_limit("scope", limit, window)` decorator + `@audit_event("event.name")` decorator on every route.

Acceptance: PASS
- 49 baseline tests (test_app_boot_integration.py + test_database.py) STILL PASS against live dev Postgres.
- 54 §4 new tests PASS (53 unit/integration + 1 rotation sanity); 3 rotation live-hit skips when Valkey DB 0 tunnel port 6381 not bound.
- Full sweep: **103 passed, 3 skipped, 0 failed in 227s**.
- `ruff check app/core/ app/main.py tests/conftest.py tests/test_core_*.py` → **All checks passed**.
- App boots cleanly: `from app.main import app` resolves; 7 middleware registered; 5 error handlers registered.
- `core/` import-direction discipline honoured: zero `app.modules.*` or `app.adapters.*` imports under `app/core/`. (Pre-§19 manual grep substitute.)

PENDING for §7 iam dispatch (master-tracked):
- Populate `refresh-token-pepper` Secret Manager value (infra-builder, per §15.H + §20.C).
- Populate `razorpay-webhook-secret` Secret Manager value (infra-builder, per §6.E + §20.C).
- Delete legacy `backend/app/middleware/{auth,rate_limit,plan_guard}.py` once `app/routers/auth.py` is rewritten against `core/auth.py` (auth-builder, §7 dispatch).
- Delete legacy `tests/test_middleware_{auth,rate_limit,plan_guard}.py` once the legacy middleware files are deleted (auth-builder, §7 dispatch).
- Wire `@rate_limit` + `@audit_event` decorators onto every §17 route at routes-builder dispatch.

Next dispatch target per Wave 1 protocol: §7 `iam` module construction — first domain module per the §21 inverse extraction-order. Auth-builder gets §7 + §4.B + §4.G + §15.H + §6.C + §6.E + §0–§6A as contract slice.
=========

=== UPDATE: 2026-06-06 — §5A i18n CONSTRUCTED ===

Phase: Construction Wave 1 — Presentation Layer Contract + i18n package
Specialist: meesell-services-builder (solo)
Sub-session: meesell-backend-construction-5A-i18n-1

Files created (4 new + 1 rewritten + 1 wired):
  - backend/app/i18n/messages_en.py          (NEW — VALIDATION_MESSAGES dict, 54 IDs)
  - backend/app/i18n/resolver.py             (NEW — resolve(message_id, locale="en") -> str)
  - backend/app/i18n/schema_contract.py      (NEW — SchemaEnvelope + FieldSpec TypedDicts + locked enums)
  - backend/app/i18n/advanced_canonical.py   (NEW — ADVANCED_CANONICAL_NAMES = frozenset({"group_id"}))
  - backend/app/i18n/__init__.py             (REWRITTEN — docstring documents 3 concerns)
  - backend/app/core/errors.py               (WIRED — _resolve_message_id now calls app.i18n.resolver.resolve)

Tests added (4 modules / 140 cases — all PASS):
  - tests/test_messages_en_id_regex.py         (6 + 54-key parametrised regex = 80 cases)
  - tests/test_resolver_fallback.py            (7 cases — fallback chain locale→en→verbatim + WARNING log)
  - tests/test_schema_jsonb_envelope_keys.py   (8 cases — 7 envelope keys + invariants)
  - tests/test_per_field_shape_keys.py         (45 cases — 9 field keys + 8/11/2/3 enum cardinalities)
  - tests/test_core_errors.py::test_i18n_resolver_wired (REWRITTEN from deferred-wire variant)

Acceptance gate run:
  - Boot smoke: `from app.main import app` → 9 routes, 13 ORM tables, 54 message IDs registered, resolver returns expected English string for `server.internal.error`. PASS.
  - Schema smoke: app.shared.database.Base.metadata.tables count = 13 (unchanged). PASS.
  - Unit tests on new + touched files: 140 PASS / 0 fail.
  - Full Wave 1 regression: tests/test_app_boot_integration + test_database + test_shared_* + test_core_* + test_messages_en_id_regex + test_resolver_fallback + test_schema_jsonb_envelope_keys + test_per_field_shape_keys = **268 PASS, 0 fail in 110s** (live dev Postgres).
  - Auxiliary auth/classifier regression: tests/test_core_auth* + test_primitive_classifier + test_step_assignment = **71 PASS, 3 skip** (skips are expected — Valkey port 6381 not tunnel-bound on this run).
  - `ruff check app/i18n/ app/core/errors.py tests/test_messages_en_id_regex.py tests/test_resolver_fallback.py tests/test_schema_jsonb_envelope_keys.py tests/test_per_field_shape_keys.py tests/test_core_errors.py` → **All checks passed.**

Static state preserved:
  - app.main.app.routes count: 9 (unchanged)
  - Base.metadata.tables count: 13 (unchanged)
  - Alembic head: f31c75438e61 (unchanged)
  - 7 middleware registered in §4.H runtime order (unchanged)
  - 5 error handlers registered (unchanged; MeesellError + RequestValidationError + PydanticValidationError + HTTPException + Exception)

Message ID inventory (54 in messages_en.py):
  - core/auth.py (3): auth.token.missing, auth.token.expired, auth.user.not_found
  - §7 iam (8): validation.phone.invalid_format, validation.otp.invalid_format, validation.webhook.malformed_payload, auth.otp.invalid, auth.otp.attempts_exceeded, auth.msg91.unavailable, auth.refresh.invalid, auth.webhook.signature_invalid
  - §8 customer (6): validation.pincode.invalid_format, validation.super_category.unknown, customer.profile.not_found, customer.super_category.not_declared, customer.compliance.missing_fields, customer.profile.incomplete_for_category
  - §9 category (4): category.lookup.not_found, category.field_enum.not_found, validation.suggest_q.too_short_or_long, validation.browse.invalid_pagination
  - §10 catalog (8): catalog.product.not_found, catalog.catalog.not_found, catalog.draft.missing, catalog.autofill.internal_error, catalog.profile.incomplete_for_category, validation.fields.unknown_key, validation.body.malformed_json, validation.completeness.missing_compulsory, validation.product_name.too_short, validation.product_name.too_long, validation.product_name.no_special_chars, validation.description.too_short_or_long (the last 4 are dynamic per-field examples that land in registry during §10 dispatch)
  - §11 image (5): validation.image.invalid_format, validation.image.too_large, validation.image.invalid_idx, image.slot.occupied, image.not.found
  - §12 pricing (5): validation.price.invalid_input, pricing.commission.missing, pricing.alert.low_margin, pricing.alert.high_mrp_multiplier, pricing.alert.thin_profit
  - §13 dashboard (1): validation.dashboard.invalid_pagination
  - §14 export (7): export.not.found, export.product.not_ready, export.front_image.missing, export.enum.validation_failed, export.compliance.strategy_failed, export.xlsx.build_failed, export.round_trip.mismatch
  - §4 core (3): tenancy.cross_user.access, plan.limit.exceeded, server.internal.error

Decisions made (FLAGGED for master review):

  D1 — `server.internal_error` and `http.{N}` envelope IDs stay 2-segment.
  These are DYNAMIC envelope `validation_message_id` values built at runtime in core/errors.py for fall-through handlers (generic Exception, HTTPException). §5A.H line 1688 says the CI Contract 10 regex scans the registry (i18n/messages_en.py), not dynamic envelope values. Registry has 3-segment `server.internal.error` as the canonical key; existing tests asserting `body["validation_message_id"] == "server.internal_error"` and `"http.418"` preserved as-is.

  D2 — Spec §7.G/§8/§14.J inline 2-segment IDs (e.g. `auth.otp_invalid`, `customer.profile_not_found`, `export.not_found`) NORMALISED to 3-segment registry keys (`auth.otp.invalid`, `customer.profile.not_found`, `export.not.found`) to conform to §5A.H regex. The §5A.H regex is the authoritative lock; §7.G/§8/§14.J use 2-segment shorthand inline.  ESCALATION NEEDED if master prefers updating §5A.H to permit 2-segment.

  D3 — Spec §5A.B example envelope shows 7 keys (fields, compulsory_count, optional_count, total_count, wizard_step_count, main_sheet_label, compliance_shape); construction prompt's "6-key envelope" summary was honoured to the spec example (7).

  D4 — `validation_message_ids` (plural list[str]) is the §5A.C locked key name; not `validation_message_id` (singular) as the prompt summary used.

Hand-offs:
  - §6 adapters (no consumption) + §6A ai_ops (no consumption).
  - §7 iam — every IamError raises with one of the 8 iam IDs + 3 core/auth.py IDs in the registry; core/errors.py resolves to English automatically. Acceptance per §19.B will read the registry.
  - §8 customer / §9 category / §10 catalog / §11 image / §12 pricing / §13 dashboard / §14 export — exceptions.py per module raises with the registered IDs; new dynamic per-field IDs added to messages_en.py at the relevant module's dispatch (§5A.J grow-as-needed contract).
  - §19 CI Contract 10 — `test_messages_en_id_regex.py` IS the gate; CI consumes it.
  - schema_contract.py — §9 `category.service.fetch_schema` return type → `SchemaEnvelope`; §10 `catalog.service.patch_product` dispatches on `DATA_TYPE_VALUES` / `PRIMITIVE_VALUES` / `ENUM_RESOLVER_VALUES`; §14 `_select_strategy` dispatches on `COMPLIANCE_SHAPE_VALUES`.
  - ADVANCED_CANONICAL_NAMES — seed scripts already enforce; §10 catalog validator imports for symmetry.

Acceptance: PASS
=========

=== UPDATE: 2026-06-06 — §6 adapters CONSTRUCTED ===

Phase: Construction Wave 1 — `backend/app/adapters/` (§6 vendor isolation layer)
Specialist: meesell-services-builder (solo)
Sub-session: meesell-backend-construction-6-adapters-1
Attempt: #1

Files created (6):
  - backend/app/adapters/__init__.py        (AdapterError root + 5 vendor subclasses)
  - backend/app/adapters/gemini.py          (~230 LOC — generate_text + generate_vision + 3-retry 1s/4s/16s)
  - backend/app/adapters/msg91.py           (~180 LOC — send_otp; LOCKED NEVER-raises returns Msg91Response(success=False))
  - backend/app/adapters/gcs.py             (~200 LOC — upload/download/sign-url(TTL=3600)/delete; raises GcsAdapterError)
  - backend/app/adapters/razorpay.py        (~80 LOC  — verify_webhook_signature SYNC, returns bool, never raises)
  - backend/app/adapters/langfuse.py        (~190 LOC — trace + score; drop-on-failure with WARNING; httpx-direct POST)

Tests added (5 modules, 73 tests, all PASS):
  - tests/test_gemini_adapter.py       — 17 tests (happy/retry/non-retry/envelope/boundary)
  - tests/test_msg91_adapter.py        — 13 tests (happy/4xx/5xx-retry/connect-err/timeout/+stripping/no-raise)
  - tests/test_gcs_adapter.py          — 16 tests (upload/download/sign-url TTL=3600/delete/path conventions)
  - tests/test_razorpay_adapter.py     — 14 tests (iscoroutinefunction=False/HMAC valid/invalid/defensive)
  - tests/test_langfuse_adapter.py     — 13 tests (trace/score egress/drop-on-failure/creds-missing one-shot warning)

Acceptance gate (all green):
  - Ruff: ALL CHECKS PASSED on all 11 touched files (4 F401 fixes applied: asyncio/timedelta/pytest unused imports)
  - Boot smoke: `from app.main import app` → routes=9 unchanged, all 5 adapter modules import clean
  - Adapter unit suite:        73/73 PASS  in 5.69 s
  - §5+§4+§5A regression:     216/216 PASS in 0.64 s (non-DB)
  - Live-DB schema smoke:      42/42 PASS  in 153 s (SSH tunnel to GCP Postgres dev)
  - GRAND TOTAL THIS DISPATCH: 331/331 PASS

Static state preserved:
  - app.main.app.routes count: 9 (unchanged — §0.E baseline preserved)
  - Base.metadata.tables count: 13 (unchanged)
  - Alembic head: f31c75438e61 (unchanged — adapters touch no schema)

Decisions FLAGGED (not in locked architecture):
  D1 — LangFuse implementation = httpx direct POST to `{LANGFUSE_HOST}/api/public/ingestion`
       (batch envelope `{batch: [{id, timestamp, type, body}]}`). NO new dependency.
       Rationale: httpx already pinned; fire-and-forget makes SDK batching value moot
       for V1 volume; swap-in for `langfuse` SDK in V1.5 is a single-file change.
       FLAGGED in `adapters/langfuse.py` docstring under "Decision flag D1".
       MASTER REVIEW NEEDED if the SDK is preferred — trivial swap, no API change.
  D2 — `adapters/__init__.py` re-exports the 5 typed subclasses so callers can
       `from app.adapters import GeminiAdapterError` without touching the per-vendor module.
  D3 — `_reset_for_testing()` helper on every async-stateful adapter (4 of 5; razorpay is
       stateless). Required for pytest-asyncio loop hygiene across the function-scope tests.
  D4 — Gemini `_RETRY_DELAYS_S=(1.0, 4.0, 16.0)` exposed at module level so tests
       can monkeypatch to zero — gates run in 5.69 s, not 21+ s per retry-exhaustion test.
  D5 — Razorpay sync-vs-async source-grep test (`test_verify_webhook_signature_signature_is_def_not_async_def`)
       reads the function's source first line. Defensive against accidental rewrites.

Pending Secret Manager values (still L2 latent — adapters consume from settings.*):
  - razorpay-webhook-secret → §7 iam dispatch (meesell-auth-builder + infra-builder)
  - langfuse-secret-key     → §6A ai_ops dispatch (meesell-services-builder + infra-builder)
  Adapters do NOT pre-validate; missing values surface via the locked failure modes
  (msg91 returns success=False; razorpay returns False; langfuse drops with WARNING).

Hand-offs queued for next dispatches:
  - §6A `ai_ops/client.py`     — sole consumer of `adapters/gemini.py` per §3.G boundary
                                  rule; sole consumer of `adapters/langfuse.py` per §6.F.
  - §7  `iam.service.send_otp_for_login`         — consumes `adapters/msg91.send_otp`
  - §7  `iam.router.razorpay_webhook`            — consumes `adapters/razorpay.verify_webhook_signature` (SYNC call, no await)
  - §11 `image.service` + `image.tasks`          — consume `adapters/gcs.{upload_bytes,download_bytes,generate_signed_url}`
  - §14 `export.service` + `export.tasks`        — consume `adapters/gcs.{upload_bytes,download_bytes,generate_signed_url}`
  - §19 CI Contract 2 import-linter              — `adapters/gemini` may be imported ONLY by `app.ai_ops`; rejected anywhere under `app/modules/`

Acceptance: PASS — all 8 §6 acceptance criteria met + 6 universal criteria met.
=========


=== UPDATE: 2026-06-06 — §6A ai_ops CONSTRUCTED (sub-session: meesell-backend-construction-6A-aiops-1) ===

Files created (10):
  - backend/app/ai_ops/__init__.py            (re-exports the 7 public surface symbols)
  - backend/app/ai_ops/cost_tracker.py        (~220 LOC — rate constants + Workload Literal + record() + audit_events direct write + Asia/Kolkata helpers)
  - backend/app/ai_ops/budget_cap.py          (~280 LOC — BudgetExceededError(MeesellError) + BudgetStatus + check_and_reserve / release_reservation atomic Lua + 80% alarm + 100% hard-stop + 2-counter race protection)
  - backend/app/ai_ops/guardrail.py           (~210 LOC — Layer 1 _LAYER1_PREFIX dict + Layer 2 per-workload shape validators + build_retry_prompt)
  - backend/app/ai_ops/prompt_registry.py     (~140 LOC — resolve() dynamic-import + render() {{var}} substitution + PromptResolutionError)
  - backend/app/ai_ops/client.py              (~290 LOC — AICallContext + AIResponse frozen dataclasses + 9-step call_gemini flow + per-workload graceful fallback + arg-validation)
  - backend/app/ai_ops/eval.py                (~160 LOC — EvalReport + FixtureResult + _TARGET_METRICS locked + run_eval skeleton + CLI entry)
  - backend/app/ai_ops/prompts/__init__.py
  - backend/app/ai_ops/prompts/smart_picker_v1.py  (V1 baseline draft; prompt-engineer refines in §19)
  - backend/app/ai_ops/prompts/autofill_v1.py      (V1 baseline draft; prompt-engineer refines in §19)
  - backend/app/ai_ops/prompts/watermark_v1.py     (V1 baseline draft; vision-rendered; prompt-engineer refines in §19)

Files modified (1):
  - backend/app/i18n/messages_en.py — added "ai_ops.budget.exhausted" cross-cutting ID (3-segment, conforms to §5A.H regex)

Tests added (6 modules, 80 tests, all PASS):
  - tests/test_ai_ops_cost_tracker.py       — 15 tests (rate constants + compute_cost_inr + record audit shape + reservation wired + audit failure swallowed + user hourly counter + getters)
  - tests/test_ai_ops_guardrail.py          — 22 tests (Layer 1 per-workload prefix + enum block + Layer 2 smart_picker 7 invariants + autofill enum 5 + watermark 3 + build_retry_prompt)
  - tests/test_ai_ops_prompt_registry.py    — 11 tests (3 V1 versions resolve + workload-mismatch / malformed / unknown raise + render substitution + missing placeholder + non-str stringify)
  - tests/test_ai_ops_budget_cap.py         — 14 tests (BudgetExceededError envelope + happy reserve + default estimate + hard-stop + 80% alarm + release noop + release accounting + get_budget_status 3 states + race protection)
  - tests/test_ai_ops_client.py             — 10 tests (frozen dataclasses + 9-step order + budget fallback per 3 workloads + Layer 2 retry succeed + Layer 2 retry exhaust + caller-arg guards)
  - tests/test_ai_ops_eval.py               — 8 tests (frozen dataclasses + 3 golden targets locked + 3 workloads only + missing fixtures = 0/0 failed + 3-fixture file = 3 results)

Acceptance gate (all green):
  - Ruff: ALL CHECKS PASSED on all 11 new source files + 6 new test files + 1 modified i18n file (2 unused imports auto-fixed via ruff --fix)
  - Boot smoke: `from app.main import app; import app.ai_ops` → imports clean; routes=9 (unchanged §0.E baseline); Base.metadata.tables=13 (unchanged §0.D baseline); Workload Literal = `Literal['smart_picker', 'autofill', 'watermark']` exactly
  - ai_ops unit suite:           80/80 PASS  in 0.66 s
  - §0/§4/§5/§5A/§6/§6A in-memory regression: 395 PASS, 3 skip (pre-existing Valkey tunnel)
  - Live-DB schema smoke:        42/42 PASS  in 85 s (SSH tunnel to GCP Postgres dev)
  - GRAND TOTAL THIS DISPATCH:   437 PASS, 3 skip

Static state preserved:
  - app.main.app.routes count: 9 (unchanged — §0.E baseline preserved)
  - Base.metadata.tables count: 13 (unchanged — §0.D baseline preserved)
  - Alembic head: f31c75438e61 (unchanged — ai_ops touches no schema)

Decisions FLAGGED (not in locked architecture):
  D1 — Cost rates configurable via `getattr(settings, "AI_RATE_*", MODULE_CONSTANT)` rather than adding fields to §5.D Settings.
       Rationale: §6A.D says "configurable via env if rates change"; adding Settings fields is a future amendment. The getattr
       pattern lets infra add the env var without re-locking §5.D. MASTER REVIEW NEEDED if explicit Settings fields preferred.
  D2 — Reservation pattern uses 2 Valkey counters (`committed` + `pending`) instead of 1. Hard-stop check is against
       `committed + pending`; release moves pending → committed. Lua script atomically reads + writes both. §6A.F mandated
       race-safety but did not specify the counter layout.
  D3 — Reservation safety-net TTL = 300 s (5 min). Worst-case Gemini call ≈ 100 s; 300 s leaves 3× safety margin. Crash
       recovery: pending counter self-heals in ≤ 5 min.
  D4 — Audit row uses `event_type="ai.call"` (7 chars, fits the 40-char column lock). Metadata jsonb shape:
       `{workload, input_tokens, output_tokens, cost_inr}`. diff_jsonb is NULL (no field-delta concept for an AI call).
  D5 — AIResponse stays exactly 5 fields per §6A.C — no `fallback_offered` top-level field added. The workload-specific
       `parsed` dict carries `"fallback_offered": True` (smart_picker/autofill) or `"watermark_check": "skipped_budget"`
       (watermark). Domain modules branch on the parsed-dict key. Keeps the locked shape intact.
  D6 — prompt-engineer track NOT dispatched as a sub-agent. Authored V1 baseline prompt templates inline (storage
       layout is locked here; content is a draft). Per dispatch prompt's coordinator-of-coordinator avoidance guidance.
       Refinement deferred to §19 golden-eval tuning. FLAGGED in prompt-engineer MEMORY.
  D7 — Per-workload graceful fallback intercepts BudgetExceededError INSIDE client.py (not at the consumer module).
       Per dispatch prompt acceptance criterion #7 + locked rule "DO NOT raise BudgetExceededError from
       smart_picker/autofill/watermark paths". Spec §6A.F text says "the error maps to a graceful fallback at the
       calling module" — dispatch prompt amends this to be wrapped inside `client.call_gemini` so domain modules
       NEVER see the exception.
  D8 — Spec text says autofill graceful fallback returns 503; dispatch prompt overrides to HTTP 200 with
       `fallback_offered=True`. Honoured dispatch prompt (more recent lock). The `BudgetExceededError` class still
       defaults to status=503 for callers who may directly surface it (V1.5 direct-paths) but client.py converts to
       AIResponse for V1.

Pending Secret Manager values still queued (NOT a blocker):
  - langfuse-secret-key — adapters.langfuse already drops-on-failure with WARNING when unset; ai_ops.client consumes
    via the adapter; no pre-validation at this layer. Populated by meesell-infra-builder during §20 deployment.

Hand-offs queued for next dispatches:
  - §9  `category.service.suggest_categories`     — consumes `call_gemini(ctx, "smart_picker.v1", {description, compressed_tree})`
  - §10 `catalog.service.autofill_product`        — consumes `call_gemini(ctx, "autofill.v1", {product_spec, schema}, allowed_enums={...})`
  - §11 `image.tasks.precheck_image`              — consumes `call_gemini(ctx, "watermark.v1", {}, image_bytes=...)` in Celery worker context
  - §14 `export.service`                          — Layer 3 enum re-validation per §6A.E + §14 (no direct ai_ops import)
  - §19 CI Contract 2 import-linter               — must reject `from app.ai_ops.cost_tracker|guardrail|budget_cap import ...` under `app/modules/`; only `app.ai_ops.client.call_gemini` (plus the 3 re-exported types) is the legal domain-import surface
  - §19 CI Contract 1 import-linter               — `adapters/gemini` may be imported ONLY by `app.ai_ops` (locked by §6 already; §6A.J reinforces)
  - §19 tests/eval/{smart_picker,autofill,watermark}/fixtures.json — populated by category-picker-builder / prompt-engineer / image-precheck-builder during §19; until then `run_eval()` returns `passed=False` with 0/0 (V1 baseline — intended CI signal)
  - meesell-prompt-engineer                       — refines the 3 V1 baseline prompts during §19 golden-eval tuning; storage layout locked here; templates owned by prompt-engineer going forward
  - meesell-infra-builder                         — populates `langfuse-secret-key` Secret Manager value during §20 deployment

Acceptance: PASS — all 9 §6A acceptance criteria met + 6 universal criteria met.
=========
