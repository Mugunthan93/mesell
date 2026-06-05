# Session 2 — Gap Pass (2026-06-05)

## What was asked
Produce a formal gap remediation plan BEFORE backend construction begins. No code writing. Analysis + plan only.

## Evidence gathered (file-grounded, all paths absolute)

### Router audit (10 files in backend/app/routers/)
- `auth.py` — uses User only. KEEP-AS-IS structurally; routes `/api/v1/auth/send-otp` and `/verify-otp` are correct shape. Will need rewrite of OTP service contract later but the router file itself is sound.
- `catalogs.py` — imports `app.models.image.Image` and `app.models.sku.SKU` (both DELETED in burn-rebuild). Imports `app.schemas.catalog` which depends on `app.schemas.image`. DELETE.
- `skus.py` — imports `app.models.sku.SKU`. DELETE.
- `images.py` — imports `app.models.image.Image`, `app.models.sku.SKU`. DELETE.
- `pricing.py` — imports `app.models.sku.SKU`, `app.models.catalog.Catalog`. Pricing endpoint shape `/api/v1/pricing/calculate` doesn't match authoritative §3.4 `POST /api/v1/products/{id}/price-calc`. DELETE.
- `generation.py` — imports User + Catalog. Imports `app.routers.catalogs._load_owned_catalog` and `app.routers.skus._load_owned_sku` (both will be deleted). DELETE.
- `quality.py` — imports `app.routers.catalogs._load_owned_catalog`. Endpoint `POST /catalogs/{id}/validate` not in §3 authoritative inventory. DELETE.
- `exports.py` — imports `app.routers.catalogs._load_owned_catalog`. Endpoint `POST /catalogs/{id}/export/meesho-csv` does not match §3.4 `POST /products/{id}/export-xlsx`. DELETE.
- `research.py` — competitive scraping. Out of V1 scope (no entry in §3). DELETE.

### Import blast radius of deleted symbols
- `app.models.sku.SKU` (file doesn't exist): referenced by catalogs.py, skus.py, images.py, pricing.py
- `app.models.image.Image` (file doesn't exist): referenced by catalogs.py, images.py
- `app.schemas.image` / `app.schemas.sku` / `app.schemas.catalog` (old shapes): chain-referenced
- `app.routers.catalogs._load_owned_catalog`: chain-referenced by exports.py, generation.py, quality.py, research.py
- `app.routers.skus._load_owned_sku`: chain-referenced by generation.py
- `app.middleware.auth.get_current_user`: USED by all routers, lives at `backend/app/middleware/auth.py` — exists. SAFE.

### main.py state
- Imports all 9 router modules. App will fail at import time on `from app.models.sku import SKU` triggered transitively when uvicorn loads any router.

### Seed state — is_advanced gap (G1)
- `scripts/build_template_schemas.py` line 83-85: `ADVANCED_CANONICAL_NAMES = {"group_id"}`
- Line 291: `is_advanced = canonical_name in ADVANCED_CANONICAL_NAMES`
- Line 302-303: override path — `if override.get("is_advanced") is True: is_advanced = True`
- So is_advanced IS wired in code. Real gap: (a) seed hasn't been re-run after refactor, and (b) no override entries currently mark anything else as advanced beyond `group_id`. Verification needed against actual `templates.schema_jsonb` row contents.

### pg_trgm / search index gap (G4)
- Migration `935e55b4852c_v1_baseline_13_tables.py` does not contain `CREATE EXTENSION pg_trgm` or any GIN trigram index
- §7.4 specifies 3 GIN indexes (`path`, `leaf_name`, `super_name`) all created CONCURRENTLY
- §7.5 budget: P95 ≤ 200 ms for combined q+super_id query

### DB deltas already shipped
- `templates.compliance_shape` (line 94 of models/template.py, NOT NULL DEFAULT 'standard', CHECK in/('standard','collapsed'))
- `field_aliases.for_xlsx_export` (line 50 of models/field_alias.py, BOOL NOT NULL DEFAULT FALSE, plus B-tree index on it)

### Endpoint inventory reconciliation
Recount of §3 + §7.7 = 2 (auth) + 5 (seller-profile) + 5 (categories/schema) + 11 (catalog/product/exports) + 1 (browse) = 24. The 25th is most likely an async-job poll (`GET /api/v1/jobs/{job_id}`) implied by §11.6's tracing requirement but not enumerated in §3. Flag this as a §3 doc-gap to resolve when construction starts on autofill/image-precheck (those are async).

## Decisions taken
- Treat §11.1 as stale per founder ruling
- Authoritative inventory = §3 + §7.7 + §11.6 = approximately 25 endpoints
- Burn-and-rebuild already happened at model/migration layer; must now extend to router/schema/service layer
- No Agent dispatch tool in this turn — coordinator-direct analysis; full specialist dispatch deferred to construction phase invoked from parent session

## Open items for next turn
- Founder greenlight on gap remediation plan
- Resolve 25 vs 24 endpoint count (probably `GET /jobs/{job_id}`)
- Decide: delete legacy routers OR keep as `*.legacy.py.bak` (default recommendation: delete; git history preserves)
