## 2026-06-12 — MS-H catalog-service extraction sub-plan AUTHORED (PHASE 1, hybrid step 1) — THE FINAL EXTRACTION

**project** — Session mesell-ms-catalog-session-1. Authored SUB_PLAN_0H_catalog_extraction.md (804 lines) +
spec_msH_backend.md + handoff_msH_infra.md on feature/microservices-catalog/docs-subplan0h. Catalog is the LAST +
RISKIEST extraction (the spine, MASTER_PLAN §4 row H, complexity XL); wave MS-5, runs ALONE, gated on MS-4
(category + iam) both founder-gate-merged.

**reference (AS-BUILT ground truth, file:line — for the MS-5 coding session):**
- Catalog router is FLAG-GUARDED: `if settings.FEATURE_CATALOG_FORM_ENABLED: app.include_router(catalog_router)`
  (main.py:126-127). The ONLY domain router behind a runtime flag — route count is CONDITIONAL (row-26 lesson).
- 6 mounted public routes (router.py:98 prefix /api/v1): POST /products(:141), PATCH /products/{id}(:170),
  POST /products/{id}/autofill(:202), GET /products/{id}/preview(:275), DELETE /products/{id}(:329),
  GET /products/{id}/draft(:352). 5 distinct rate-limit scopes, 4 @audit_event, 3 feature-flag guards
  (catalog-form mount, ai_autofill 404, live_preview 404-default-False).
- §3.4 "Catalog & product (11)" MINGLES other modules' /products/* routes — catalog OWNS exactly 6.
- INBOUND (catalog is the most-called module — __init__.py:8-13): image(:53), pricing(:65), export(:57),
  dashboard(:36). Methods: assert_product_ownership(service.py:921 — image/pricing/export), get_product_for_export
  (:945 — export, the 2 MS-A frozen shims), list_products(:999 — dashboard).
- OUTBOUND (the spine's caller side): category(service.py:98 — fetch_schema ×6 @ :463,:506,:620,:800,:962,:1034;
  assert_category_exists @ :401; get_field_enum @ :309) + customer(:99 — assert_eligible_for_super_id @ :406;
  get_compliance_block @ :839). 5 outbound shims → REAL sibling pods (category=MS-4, customer=MS-3 already extracted).
- autofill: service.py:638 call_gemini(ctx,"autofill.v1",...), AICallContext(workload="autofill") @ :628, graceful
  fallback @ :649. ai_ops vendored TRIMMED (autofill_v1 prompt ONLY). SHARED `ai:*` budget brake (same carve-out as MS-F).
- 3 tenant-scoped tables: catalogs/products/product_drafts (repository.py:59-61). scope_to_user on every read
  (:87,:108,:126,:143) — §10 leak rule MUST preserve (contrast: category is GLOBAL, no scope_to_user).
- NO Celery worker (grep confirms doc-comment only).

**feedback (TRUE-BRANCH-TIP discipline — report contradictions, don't paper over):**
- get_validation_summary: documented dashboard-consumed (__init__.py:11) but NO live caller at develop tip. →
  latent surface; defensive /internal shim + Open Question; docstring correction flagged. (Same pattern as
  SUB_PLAN_0F's list_super_categories latent-shim handling.)
- catalog→image edge is DEAD: service.py:828,:980 hasattr(image_service,"get_image_refs") — get_image_refs does NOT
  exist on image/service.py. → NO image_client authored; dead getattr travels verbatim, never fires; image_refs=().
- export-snapshot is a 2-HOP chain: export-svc→catalog-svc→category-svc (get_product_for_export calls
  category_service.fetch_schema @ :962). Shim timeout must account for the nested hop.

**reference (PATTERN for any future LAST-in-a-program extraction):** the MS-H PHASE-2 TAIL is unique — after the
service's founder gate, encode T1 (§5.G post-extraction repo-management compliance audit, MASTER_PLAN line 397,
owner: backend-coordinator + master review) → T2 (MASTER_PLAN completion stamp, gated on T1, founder ratifies —
the lead does NOT self-declare program completion). The program (A–H) is NOT complete until T1 passes (§4 row H line 308).

**reference (Traefik nuance for catalog cutover):** shared path key /api/v1/products needs METHOD-SPLIT routing
(POST→catalog-svc, GET→dashboard-svc) because dashboard's list shares the key (main.py:138-140). Flagged in
handoff_msH_infra.md. Catalog cutover flips 4 networking surfaces at once (image/pricing/export/dashboard) — de-risked
by MS-5 running ALONE.

**user (validation floor):** live `def test_` count at 2026-06-12 = 698 (was 649 at MS-A, 698 now after the
flag/catalog waves). Quote live at PR time, do NOT hardcode. Catalog's own = 24.
