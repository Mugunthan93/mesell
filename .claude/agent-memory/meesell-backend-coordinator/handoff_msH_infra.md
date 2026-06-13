# handoff_msH_infra.md — catalog-service infra surfaces (Session MS-H)

**FROM:** meesell-backend-coordinator
**TO:** meesell-infra-builder
**DATE:** 2026-06-12
**Status:** **DO NOT EXECUTE until MS-5 wave opens** (MS-4 = category + iam both
founder-gate-merged; catalog extracts ALONE — no parallel partner). This memo is the
infra surface inventory the infra lead turns into real `feature/microservices-catalog/infra`
commits AT MS-5. Dev cluster only — no staging/prod, no terraform beyond dev-scope manifests.
**Companion:** `docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md` (§H-infra),
`spec_msH_backend.md`. Mirrors the MS-A / MS-F infra-handoff shape. THE LAST extraction.

---

## Surfaces to author (placeholders backend provides → infra makes real)

### 1. Dockerfile — `backend/services/svc-catalog/Dockerfile`
- FROM python:3.12-slim. Installs `requirements.txt` (fastapi, sqlalchemy, asyncpg, redis,
  httpx, **google-genai**, langfuse — catalog HAS AI (autofill); NO openpyxl/celery — no
  XLSX/worker).
- **NO Celery worker process** (catalog has zero background tasks — autosave draft upsert is
  synchronous inside patch_product; verified no shared_task/Celery in modules/catalog/).

### 2. K8s — `k8s/svc-catalog/`
- `deployment.yaml`: API replicas (autosave WRITE-heavy — size the LARGEST pool per
  MASTER_PLAN §2.E line 207 "catalog gets the largest pool"; per infra plan §6.3).
  **NO worker deployment.**
- No cache pre-warm sidecar needed on catalog itself — catalog's hot path (fetch_schema)
  is served by CATEGORY-svc's pre-warm cache, not catalog's own. catalog mounts Valkey DB 3
  only for its own small cache keys (`catalog:`-prefixed).
- `service.yaml`: ClusterIP :8001.

### 3. Traefik IngressRoute — ⚠️ METHOD-SPLIT NUANCE
- `/api/v1/products/*` → svc-catalog:8001 for the 6 catalog routes: POST /products,
  PATCH /products/{id}, POST /products/{id}/autofill, GET /products/{id}/preview,
  DELETE /products/{id}, GET /products/{id}/draft.
- **⚠️ SHARED PATH KEY `/api/v1/products` — METHOD-SPLIT REQUIRED.** `POST /api/v1/products`
  is catalog's (create_product); `GET /api/v1/products` is DASHBOARD's (list — dashboard-svc,
  MS-2). FastAPI registered them as 2 distinct APIRoute objects on one path key (main.py:138-140).
  At catalog's cutover Traefik must route `/api/v1/products` BY METHOD: POST → svc-catalog,
  GET → svc-dashboard. The other 5 catalog paths (PATCH/DELETE/{id}, autofill, preview, draft)
  are unambiguous sub-paths. Confirm the Traefik matcher supports method-based routing on the
  shared key (Method(`POST`) && Path(`/api/v1/products`)).
- `/internal/products/*` → svc-catalog:8001 (the 3-4 /internal/* shims:
  ownership-check, export-snapshot, list-products, + defensive validation-summary).
- **Cutover = 4-SURFACE route flip**: at catalog's cutover, the `/internal/products/*` routes
  move from monolith-svc to svc-catalog. The 4 already-extracted callers reach them:
  image-svc + pricing-svc + export-svc (ownership-check + export-snapshot) and dashboard-svc
  (list-products). The flip is transparent to their call sites (§16.G). Rollback = flip all 4
  back to monolith-svc in one IngressRoute revert.
- **⚠️ MOUNT GUARD:** catalog's monolith mount is behind `FEATURE_CATALOG_FORM_ENABLED`
  (main.py:126). If that flag governs whether catalog serves at all in an env, the Traefik
  route must be gated equivalently (or the svc-catalog app preserves the guard internally —
  backend handles the latter). Confirm with the backend lead which layer enforces the flag.

### 4. Postgres — schema + role + GRANTS (CRITICAL — the audit grant covers TWO writers)
- `CREATE SCHEMA catalog;`
- `CREATE ROLE catalog_user ...; GRANT USAGE/SELECT/INSERT/UPDATE/DELETE ON ALL TABLES IN
  SCHEMA catalog TO catalog_user;` (catalog is READ-WRITE — products/catalogs/product_drafts
  are mutated by create/patch/autosave/delete, unlike category's read-only tables).
- **`GRANT INSERT ON public.audit_events TO catalog_user;`** — the SHARED ledger. catalog-svc
  writes audit_events from TWO sources: (a) the vendored `cost_tracker.py` AI committed-cost
  write (H3.c), AND (b) the `audit_mw` write-route audit rows for the 4 write routes
  (catalog.product.created/updated/deleted + catalog.autofill.invoked). One grant covers both.
  Mirrors the MS-A `export_user` + MS-F `category_user` audit-grant pattern (§5.B).
- **Cross-schema FK note (Risk #5):** `products.user_id` references `users` (iam-owned). After
  iam (MS-4) + catalog (MS-5) both extract, this is a cross-schema reference. The database-
  builder runs the integrity pre-scan; catalog drops NO FK; infra ensures catalog_user has
  USAGE on the schema holding `users` if the FK constraint must resolve at write time
  (coordinate with iam's MS-4 schema grants).

### 5. Secret Manager bindings
- **`JWT_SECRET`** — the SAME secret iam-svc signs tokens with (D7 local-JWT — catalog
  validates locally, NEVER calls iam-svc per-request). iam (MS-4) is already extracted; bind
  the same `JWT_SECRET`.
- **`GEMINI_API_KEY`** — catalog's autofill workload calls Gemini via vendored ai_ops.
- **`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`** — ai_ops traces with `service="catalog"` (§5.F).
- `DATABASE_URL` @ schema `catalog`, `VALKEY_URL` (shared instance), `CACHE_VERSION`,
  `AI_DAILY_BUDGET_INR` (=500), `FEATURE_CATALOG_FORM_ENABLED` / `FEATURE_AI_AUTOFILL_ENABLED`
  / `FEATURE_LIVE_PREVIEW_ENABLED` (the 3 catalog feature flags), `APP_ENV`.

---

## ⚠️ The Valkey budget-keyspace carve-out (infra MUST NOT namespace these)

Same carve-out as MS-F (the budget brake is GLOBAL across category + catalog + image).
MASTER_PLAN §2.E (line 209) locks per-service Valkey key namespacing (`{service_name}:`
prefix). **EXCEPTION — the AI budget brake keyspace stays GLOBAL/un-prefixed:**
- `ai:cost:daily:{YYYY-MM-DD}`        (committed spend — the ₹500 cap)
- `ai:cost:pending:{YYYY-MM-DD}`      (reserved headroom)
- `ai:budget:reservation:{id}`        (per-call 5-min reservation)
- `ai:cost:user:{user_id}:hourly:{hr}` (per-user accumulator)

These live in **Valkey DB 0**, SHARED across category/catalog/image so the ₹500 daily cap is
ONE global counter. If infra's namespacing config (or a key-migration backfill at cutover)
prefixes the `ai:*` keys, the cap splits into N independent caps. The backend services-builder
handles this in `shared/valkey.py` (prefix on the cache-DB-3 factory only, not budget keys),
but if infra runs a backfill at cutover, **EXCLUDE the `ai:*` keyspace from re-prefixing.**
catalog's OWN cache keys (DB 3) DO get the `catalog:` prefix.

> **MS-5 is the LAST AI extraction** — after catalog, all 3 AI workloads (smart_picker,
> autofill, watermark) run from vendored copies hitting this one shared keyspace. The MS-5
> integration test asserts a 3-source reservation moves the same counter. Do NOT touch the
> `ai:*` keyspace during the catalog cutover.

---

## D3 VM checkpoint (per MS-PAR-1) — likely the upgrade moment

At MS-5 the deploy is monolith (now nearly empty) + export + dashboard + image + pricing +
customer + category + iam + catalog (8 services + shrinking monolith) on the dev node.
**MS-4 already likely triggered the e2-standard-4 ask; if it did not, MS-5 almost certainly
does** — catalog gets the LARGEST pool and this is the full 8-service fan-out. The upgrade
(~₹2,600/mo) is plan-pre-approved (D3) BUT the SPEND gets a fresh founder ask at the moment
the deploy doesn't fit. **STOP and ask the founder before provisioning** — never on the
plan-level pre-approval alone (master-session standing rule).

---

## Inter-lead request row

A row is added to `feature_board_backend.md` → "Inter-lead requests open" pointing at this
memo, marked gated-on-MS-5 (no SLA pressure until the wave opens).
