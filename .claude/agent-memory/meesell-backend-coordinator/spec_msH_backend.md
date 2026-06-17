# spec_msH_backend.md — catalog-service extraction (Session MS-H) — EXECUTABLE TASK SPEC

**Status:** AUTHORED 2026-06-12 (PHASE 1, hybrid step 1). **EXECUTION GATED ON
MS-5 WAVE OPEN** (MS-4 = category + iam both founder-gate-merged; catalog runs
ALONE — no parallel partner). THE LAST + RISKIEST extraction (the spine).
**Companion sub-plan:** `docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md`
(read it FIRST — this spec is the per-specialist breakdown; the sub-plan is the
contract).
**Authored by:** meesell-backend-coordinator. Mirrors the rigor of spec_msF_backend.md
+ spec_msA_backend.md.

---

## Dispatch sequence (critical path)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder  →  Alembic schema-split: 3 TENANT-SCOPED tables → schema `catalog`
                               (catalogs, products, product_drafts); cross-schema-FK pre-scan
  meesell-infra-builder     →  Dockerfile + K8s (largest pool, NO worker) + Postgres schema/role
                               + audit-DB grant + Traefik method-split route + Secret bindings
                               (on feature/microservices-catalog/infra — handoff_msH_infra.md,
                               DO NOT EXECUTE until MS-5)

PHASE B (depends on A — service code targets the new schema + vendored libs + sibling pods):
  meesell-services-builder  →  extract service.py + repository.py + domain.py + exceptions.py;
                               VENDOR ai_ops (trimmed, autofill_v1 ONLY) + core/middleware + core/*
                               + i18n + shared/*; author 5 OUTBOUND shims (category_client ×3,
                               customer_client ×2); wire SHARED budget brake; standalone main.py
                               (6-mw chain, PRESERVE FEATURE_CATALOG_FORM_ENABLED guard, NO Celery)
  meesell-api-routes-builder→  extract router.py (6 public routes verbatim) + author
                               internal_router.py (3 LIVE + 1 defensive /internal/* shims);
                               regen OpenAPI (parallel w/ services-builder once signatures freeze)

PHASE C (depends on B — integration):
  meesell-backend-coordinator → hybrid-mode CI wiring (BOTH directions live — first time);
                                test_catalog_extraction.py (3-source budget-brake + frozen-shim
                                + scope_to_user-leak + autosave-P95); merge-gate review; board MERGED
```

**Iteration cap: 3** per specialist; the 3rd re-dispatch triggers a founder consult.

---

## meesell-services-builder (the HEAVIEST lift in the program)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell (worktrees under /tmp/mesell-wt/ included). DO NOT read/write outside.
SESSION: mesell-microservices-catalog-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md (THIS plan — esp. H3 ai_ops vendoring + SHARED budget brake, H4 inbound shims, H5 OUTBOUND shims)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.E (Valkey namespacing line 209, largest pool line 207)/§3.A/§3.C/§5.A (local JWT + internal-endpoint auth line 338)/§5.B; D6 line 221 (ai_ops vendored); D7 line 330 (mw vendored + local JWT)
- docs/BACKEND_ARCHITECTURE.md §10 (catalog contract) + §6A (ai_ops layer) + §16.G (call-site preservation)
- backend/app/modules/catalog/{service,repository,domain,exceptions}.py (as-built — service.py 1070 lines)
- backend/app/ai_ops/{client,budget_cap,cost_tracker,guardrail,prompt_registry}.py + prompts/autofill_v1.py (the vendoring source)
- The 4 inbound callers (for shim shapes): image/service.py:53,162,248; pricing/service.py:65,134,241; export/service.py:57,174,177,314; dashboard/service.py:36,78
- .claude/agent-memory/meesell-services-builder/MEMORY.md

## Your mission
Extract the `catalog` module into backend/services/svc-catalog/.
Move service.py + repository.py + domain.py + exceptions.py VERBATIM.
VENDOR (byte-identical) the trimmed ai_ops path (client, budget_cap, cost_tracker,
guardrail, prompt_registry, eval, metrics + ONLY prompts/autofill_v1.py), the 6-mw
chain, core/{auth,cache,plan_guard,errors,tenancy,metrics}, the i18n subset, shared/*.
Author the 5 OUTBOUND HTTP-shim clients (category_client: exists+schema+field_enum;
customer_client: eligibility+compliance_block) pointing at the REAL sibling pods'
ClusterIPs (category-svc + customer-svc are extracted pods by MS-5 — NOT the monolith).
Build standalone main.py: 6-mw chain (CORS → request_id → auth_mw → tenancy_mw →
rate_limit_mw → plan_guard_mw → audit_mw), local JWT (D7), the 6 public routes +
3-4 /internal/* shims mounted, /health + /metrics. NO Celery (catalog has no worker).

THE FIVE LOAD-BEARING INVARIANTS:
1. §16.G CALL-SITE PRESERVATION (outbound) — change ONLY the 2 import lines
   (service.py:98 `from app.modules.category import service as category_service` and
   :99 `from app.modules.customer import service as customer_service`) to import the
   extracted_clients re-exporting the SAME symbol names. The 8 outbound call sites
   (category fetch_schema ×6 @ :463,:506,:620,:800,:962,:1034; assert_category_exists
   @ :401; get_field_enum @ :309; customer assert_eligible_for_super_id @ :406;
   get_compliance_block @ :839) stay BYTE-IDENTICAL.
2. SHARED BUDGET BRAKE (H3.c) — vendored budget_cap.py + cost_tracker.py reach the
   SAME Valkey DB 0 + SAME audit_events DB. The budget keyspace (`ai:cost:daily:{date}`,
   `ai:cost:pending:{date}`, `ai:budget:reservation:{id}`, `ai:cost:user:{uid}:hourly:{hr}`)
   MUST NOT get the `catalog:` §2.E prefix — it stays GLOBAL so the ₹500 cap is shared
   across category+catalog+image. Apply the prefix ONLY in shared/valkey.py cache-DB-3 factory.
3. scope_to_user PRESERVED — catalog is FULLY tenant-scoped (unlike category). Every
   product/catalog read keeps scope_to_user (repository.py:87,:108,:126,:143). The §10
   leak rule: find_by_id collapses not-found/wrong-owner/soft-deleted to None uniformly.
4. FEATURE_CATALOG_FORM_ENABLED MOUNT GUARD preserved — the router mounts behind the flag
   (main.py:126-127). svc-catalog main.py preserves the guard (route count is conditional —
   row-26 lesson).
5. DEAD IMAGE BRANCH untouched — service.py:828,:980 `getattr(_image_module,"service")`
   + `hasattr(image_service,"get_image_refs")` is DEAD (get_image_refs does not exist on
   image-svc). Travels VERBATIM (§16.G), never fires; image_refs stays empty tuple. Author
   NO image_client shim.

## Acceptance criteria
- [ ] service.py diff vs monolith = ONLY the 2 import-line rewires + vendoring; ZERO call-site changes.
- [ ] ai_ops vendored TRIMMED: only autofill_v1.py prompt (NOT smart_picker/watermark).
- [ ] Budget keyspace `ai:*` UN-prefixed (global); catalog cache keys `catalog:`-prefixed.
- [ ] Vendored budget_cap.py Lua (_RESERVE_LUA, _RELEASE_LUA) byte-identical to source.
- [ ] cost_tracker writes audit_events via cross-schema INSERT; audit_mw ALSO writes 4 write-route audit rows (GRANT INSERT covers both).
- [ ] 5 outbound shims authored (category ×3, customer ×2) targeting sibling ClusterIPs; httpx.AsyncClient 5s read/2s connect, 1 retry on 503/504, forward JWT + X-Request-ID.
- [ ] scope_to_user on every product/catalog read; repository bound to schema `catalog`.
- [ ] 6-mw chain registered; local JWT (D7); 5 rate-limit scopes + 4 audit + 3 feature-flag guards preserved.
- [ ] FEATURE_CATALOG_FORM_ENABLED mount guard preserved.
- [ ] NO Celery (no celery_app.py, no tasks.py).
- [ ] Dead image getattr branch verbatim + never fires (no image_client authored).
- [ ] Trimmed Settings: GEMINI_*/LANGFUSE_*/AI_DAILY_BUDGET_INR/JWT_SECRET/DATABASE_URL@catalog/VALKEY_URL/CACHE_VERSION/FEATURE_* flags; NO openpyxl/celery/msg91/razorpay; largest pool.

## Hard constraints
- DO NOT modify backend/app/modules/catalog/ during extraction (strangler — both coexist).
- DO NOT touch frontend/, k8s/, infra/terraform/ (infra lead owns manifests).
- DO NOT author an image_client shim (the image edge is dead V1 code).
- DO NOT prefix the `ai:*` budget keyspace with `catalog:` (breaks the global cap — R4).
- DO NOT drop scope_to_user (tenant leak — R7).
- DO NOT drop the FEATURE_CATALOG_FORM_ENABLED mount guard (R9).

## Files you MAY touch
backend/services/svc-catalog/** ONLY (plus the sub-plan's "Rollback Log" if a rollback fires).

## Files you must NOT touch
backend/app/modules/catalog/**, backend/app/main.py, backend/app/ai_ops/**, backend/app/modules/{image,pricing,dashboard,export,category,customer}/**, k8s/**, frontend/**, infra/**

## Final report format
Files created (count + paths); service.py diff-line-count vs monolith (target: 2 import lines + vendoring, zero call-site); confirmation `ai:*` un-prefixed + cache prefixed; budget_cap.py Lua byte-identical; scope_to_user preserved; mount-guard preserved; dead-image-branch verbatim confirmation; PR-template-ready Test evidence.
```

---

## meesell-api-routes-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-catalog-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md (THIS plan — §H4 the inbound /internal/* shims)
- backend/app/modules/catalog/router.py + schemas.py (as-built — 6 routes, 5 rate-limit scopes, 4 audit decorators, 3 feature-flag guards)
- docs/BACKEND_ARCHITECTURE.md §10.B (6 endpoint contracts)
- The MS-A frozen shim contract (sub-plan §H4 reproduces the 2 catalog-owned shapes verbatim — FROZEN, never rename/reshape)

## Your mission
(1) Move the 6 public catalog routes into backend/services/svc-catalog/app/router.py VERBATIM:
    POST /products (rate_limit create_product 20/3600 + audit catalog.product.created),
    PATCH /products/{id} (rate_limit product_patch 600/3600 + audit catalog.product.updated +
    X-Autosave header), POST /products/{id}/autofill (rate_limit ai_autofill 50/3600 + audit
    catalog.autofill.invoked + FEATURE_AI_AUTOFILL_ENABLED 404 guard), GET /products/{id}/preview
    (rate_limit product_preview 600/3600 + FEATURE_LIVE_PREVIEW_ENABLED 404 guard, raises
    MeesellError code=feature.live_preview.disabled), DELETE /products/{id} (rate_limit
    product_delete 60/3600 + audit catalog.product.deleted, 204), GET /products/{id}/draft
    (rate_limit product_draft_read 600/3600, 204 when no snapshot). All async, all
    Depends(get_current_user) + Depends(get_db). NO business logic inlined.
(2) Author backend/services/svc-catalog/app/internal_router.py with the shims:
       POST /internal/products/{id}/ownership-check       ← service.assert_product_ownership(product_id, user_id, db)  [MS-A FROZEN — 204/404]
       GET  /internal/products/{id}/export-snapshot        ← service.get_product_for_export(product_id, user_id, db)  [MS-A FROZEN — ExportSnapshotInternal]
       GET  /internal/products?page=&limit=                ← service.list_products(user_id, pagination, db)           [dashboard — PaginatedProductsInternal]
       GET  /internal/products/{id}/validation-summary     ← service.get_validation_summary(...)  [DEFENSIVE — author per Open Question; default YES]
    Internal routes use forwarded-JWT service-to-service auth (§5.A line 338 — user_id from sub claim),
    NOT the get_current_user UI flow. Return the EXACT frozen shapes (NO rename, NO reshape).
(3) Regenerate the standalone OpenAPI.

## Acceptance criteria
- [ ] 6 public routes mounted verbatim; 5 rate-limit scopes + 4 audit decorators + 3 feature-flag guards preserved.
- [ ] 2 MS-A-frozen /internal/* shims (ownership-check, export-snapshot) return EXACT frozen shapes.
- [ ] list_products shim (#3) matches SUB_PLAN_0B's dashboard contract (Open Question); validation-summary (#4) defensive.
- [ ] Internal routes do NOT use get_current_user UI flow (forwarded-JWT s2s auth).
- [ ] No business logic inlined — handlers call service methods only.
- [ ] OpenAPI regenerated; 6 public + 3-4 internal endpoints present.

## Hard constraints / MAY touch / must NOT touch / report
(same boundary + report shape as services-builder; scoped to router.py + internal_router.py + schemas.py)
Re-dispatch trigger: any /internal/* shape deviates from the MS-A frozen contract → re-dispatch quoting sub-plan §H4.
```

---

## meesell-database-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-catalog-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0H_catalog_extraction.md (THIS plan — §as-built DB tables, R6 cross-schema FK)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.D (schema-per-service) + §6 Risk #5 (cross-schema FK integrity)
- backend/alembic/ (current head — read the chain at session start)
- backend/app/modules/catalog/repository.py:59-61 (the 3 ORM-imported tables: Catalog/Product/ProductDraft)
- .claude/agent-memory/meesell-database-builder/MEMORY.md

## Your mission
Author the schema-split Alembic migration moving the 3 TENANT-SCOPED catalog tables from
`public` to a dedicated `catalog` schema: catalogs, products, product_drafts. Set
version_table_schema="catalog". Write upgrade (ALTER TABLE ... SET SCHEMA catalog, all 3)
+ tested downgrade (SET SCHEMA public). CRITICAL (Risk #5): products.user_id FKs to users
(an iam-owned table) — this becomes a CROSS-SCHEMA reference. Run the §6-Risk#5 integrity
pre-scan: verify every products.user_id resolves to a real users row BEFORE any FK
adjustment (catalog drops NO FK, but emit the scan output to a migration log). Preserve all
indexes (SET SCHEMA preserves them — assert via post-migration EXPLAIN on a scoped product
list query). Row counts preserved.

## Acceptance criteria
- [ ] All 3 tables moved to schema `catalog`; upgrade + downgrade round-trip clean locally.
- [ ] version_table_schema="catalog"; alembic_version lands in catalog schema.
- [ ] Risk #5 cross-schema-FK integrity pre-scan emitted to migration log (products.user_id → users).
- [ ] Indexes survive (post-migration EXPLAIN confirms index usage on a scoped product query).
- [ ] No head divergence dev↔staging (apply dev FIRST — infra ordering rule; P0 if diverged).
- [ ] Row counts preserved (products, catalogs, product_drafts).

## Hard constraints / MAY touch / must NOT touch / report
(boundary scoped to backend/services/svc-catalog/alembic/** + the migration file)
Re-dispatch trigger: head divergence dev↔staging → P0, escalate to founder; lost index → re-dispatch.
```

---

## Backend-lead integration test (Phase C — coordinator-authored)

`backend/services/svc-catalog/tests/test_catalog_extraction.py`:
- **Hybrid-mode**: 6 public routes respond in-process AND via svc-catalog pod (flag ON).
- **Frozen shim shapes**: `/internal/products/{id}/ownership-check` (204/404),
  `/internal/products/{id}/export-snapshot` (ExportSnapshotInternal) match MS-A frozen shapes.
- **2-hop chain**: export-snapshot internally reaches category-svc's
  `/internal/categories/{id}/schema` (assert the nested outbound fires + within timeout).
- **3-source budget-brake-shared**: `check_and_reserve` from catalog-svc + category-svc +
  monolith all move the SAME `ai:cost:daily:{date}` counter (assert `ai:*` NOT `catalog:`-prefixed).
- **Vendoring parity**: `budget_cap._RESERVE_LUA`/`_RELEASE_LUA` byte-identical to source.
- **scope_to_user leak**: a cross-tenant product fetch returns 404 (collapsed to None — §10 leak rule).
- **autosave P95**: `fetch_schema` hot-path served from category pre-warm cache; P95 within §15.E budget.
- **autofill graceful fallback**: BudgetExceededError → fallback_offered=True (real behavior, NOT assert True).

---

## Merge-gate checklist (lead, STEP 3 — real gate, can reject)

Per the backend.md PR template + sub-plan §Acceptance gate. Reject-class triggers:
- service.py call-site changed beyond the 2 import rewires → reject quoting §16.G.
- `ai:*` budget keys got the `catalog:` prefix → reject quoting H3.c R4 (breaks global cap).
- scope_to_user dropped on any product read → reject quoting §10 leak rule R7.
- FEATURE_CATALOG_FORM_ENABLED mount guard dropped → reject quoting row-26 lesson R9.
- /internal/* shape deviates from MS-A frozen contract → reject quoting §H4.
- an image_client shim authored (dead branch) → reject quoting §H5 R8.
- AI prompt other than autofill_v1 vendored → reject (trim violation).
- tautological test → reject (pricing lesson).
- PR-template field left as `<placeholder>` → refuse to merge.
- Alembic head divergence dev↔staging → P0 founder escalation.

## PHASE-2 TAIL (post founder-gate, MS-H ONLY — the program close-out)
After catalog's founder gate merges:
- T1: §5.G post-extraction repo-management compliance audit (owner: backend-coordinator + master review).
- T2: MASTER_PLAN completion stamp (gated on T1; founder ratifies — lead does NOT self-declare).
