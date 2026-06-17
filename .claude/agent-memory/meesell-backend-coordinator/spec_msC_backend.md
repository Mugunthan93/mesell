# SPEC — Microservices Sub-Plan C (`image` extraction) — BACKEND code work (HYBRID step 1)

**Session:** `mesell-ms-image-session-1` (2026-06-12, MS-C PHASE 1)
**Author:** meesell-backend-coordinator (HYBRID rule STEP 1 — SPEC only, NO code, NO git ops, NO dispatch)
**Plan basis:** `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3) + `SUB_PLAN_0C_image_extraction.md` (authored this session) + `SUB_PLAN_01_export_extraction.md` (shape template) + `spec_msA_backend.md` (§0.4 frozen contract table)
**EXECUTION GATE:** PHASE 2 is BLOCKED. Do NOT dispatch any specialist until BOTH: (1) MS-A `feature/microservices-export/integration`→develop founder gate MERGED, and (2) the MS-A extraction RECIPE exists in backend-lead memory. **Consume + reconcile the MS-A recipe BEFORE dispatch.** As of authoring, MS-A branches sit at `c859955` (= origin/develop tip) — founder gate OPEN, NOT merged.

---

## 0. GROUND TRUTH (re-verified from SOURCE @ origin/develop c859955 — see SUB_PLAN_0C §0 for full file:line table)

Key facts the specialists MUST honor (Wave-6 law — cite from source, never plan prose):
- **image = 8 module files** + owns 1 table `product_images` (schema `image` after split). ORM `shared/models/product_image.py`; joins `products` (`shared/models/product.py`) for tenancy (no direct user_id col, §11-IMAGE-D1).
- **2 mounted public routes** (main.py:46 import, :126 mount): `POST /api/v1/products/{id}/images` 202 (rate_limit image_upload 10/60 + audit image.upload.received + idx-fast-fail router.py:110); `GET /api/v1/products/{id}/images` 200 (rate_limit image_list 600/3600, no audit). Path param `{id}`.
- **image is AI-CONSUMING** (UNLIKE export): `tasks.py:206` `call_gemini(ctx,"watermark.v1",{},image_bytes=...)`, ctx=`AICallContext(workload="watermark",user_id=...)` (tasks.py:200), import tasks.py:198. -> **VENDOR ai_ops per D6/A1; SHARED budget brake Valkey DB 0.**
- **image's ONLY outbound HTTP shim = catalog** `assert_product_ownership(product_id,user_id,db=)` at service.py:162 + :248 (import service.py:53). catalog is MS-5 (LAST) -> shim base URL = **monolith ClusterIP** during MS-C.
- **image is a CALLEE of export** — MS-A FROZE `list_images(user_id,product_id,*,db)->ImagesListResponse` (service.py:232) as the `/internal/products/{id}/images` shim. **NOT `get_image_bytes`** (export calls list_images at export/service.py:185, import :83 — the §1.C MASTER_PLAN "get_image_bytes" cell is STALE; spec_msA §0.4 row 6 corrected it). Implement `list_images` shim; reconcile vs MS-A final contract; STOP+escalate on drift.
- **Celery:** task in-module `modules/image/tasks.py` (`name="image.precheck"`, tasks.py:415); `workers/celery_app.py` has NO `task_routes`/queue config (both tasks default queue). svc-image gets dedicated queue `svc-image`, keys `svc-image:`, broker DB1/results DB2, keeps `task_prerun` JWT re-validation for `image.precheck` only + all locked invariants (celery_app.py:108-119).
- **GCS** (moves with svc-image): upload_bytes/download_bytes/generate_signed_url at service.py:195/:254/:300/:340/:410 + tasks.py:285; path `meesell-images/{user_id}/{product_id}/{idx}.jpg` (service.py:96). ADC from pod SA.
- **rembg:** declared in requirements.txt:14, ZERO call sites in backend/app. DEFER from svc-image requirements (recommended, §3.G) — no live behavior to move; final call is Phase-2 founder/AI-lead confirm. Do NOT invent a call site.
- **§0.10 cross-schema hazard:** `product_images`<->`products` tenancy join breaks when product_images->schema `image` but products stays public/catalog. Recommended Option (b): scope by product_id post-ownership-shim. Fallback (a): transitional `GRANT SELECT ON public.products`. ESCALATE if MS-A recipe silent.
- **Test floor:** 649 `def test_` baseline (MONOTONIC); image's own = 29. Quote LIVE count at PR; never hardcode 823.

---

## 1. Builder sequence (3-phase, per SUB_PLAN_0C §2)
```
PHASE A (parallel):
  meesell-database-builder -> Alembic schema-split (product_images public->image), version_table_schema="image", Risk#5 pre-scan, §0.10 cross-schema decision (coordinate infra)
  [INFRA LANE — meesell-infra-builder per handoff_msC_infra.md]
PHASE B (depends on A):
  meesell-services-builder  -> service/tasks/repository/domain/exceptions; catalog_client shim; ai_ops VENDORING; main.py (6-mw, plan_guard NO-OP); single-task Celery app (queue svc-image)
  meesell-api-routes-builder-> router.py (2 public) + schemas.py + /internal/products/{id}/images shim route (near-parallel once service sigs frozen)
PHASE C (lead-owned):
  meesell-backend-coordinator -> hybrid CI; test_image_extraction.py; merge-gate STEP 3; board MERGED flip
```
Dispatch order: database-builder FIRST (|| infra handoff) -> services-builder -> api-routes-builder -> lead Phase C. Iteration cap **3** per specialist.

---

## 2. Branch plan (Model C — cut from origin/develop c859955)
| Branch | Cut from | Purpose |
|---|---|---|
| `feature/microservices-image/integration` | origin/develop | integration; merge commits; F3 protection |
| `feature/microservices-image/backend` | …/integration | backend specialist work |
| `feature/microservices-image/infra` | …/integration | infra lane |
Worktrees `/tmp/mesell-wt/msC-*`. NEVER `git add -A` — scope to `backend/services/svc-image/`. group->integration = LEAD gate (squash); integration->develop = FOUNDER gate (left OPEN). Parallel-lane with MS-B (dashboard): diffs stay in svc-image surfaces; shared files additive.

---

## 3. Per-specialist SPECs

### 3.A meesell-services-builder (opus) — heavy lift
**TASK:** Extract image service/tasks/repository/domain/exceptions into `backend/services/svc-image/app/`; rewire the catalog import to an HTTP shim; VENDOR ai_ops (D6); build standalone main.py (6-mw, plan_guard NO-OP) + single-task Celery app (queue svc-image).

**Files to CREATE** (svc-image tree — see SUB_PLAN_0C §3 table for full list): main.py, service.py (catalog import service.py:53 -> `from app.core.extracted_clients import catalog_client as catalog_service`; call sites :162/:248 BYTE-FOR-BYTE), tasks.py (ai_ops imports -> vendored app.ai_ops), repository.py (§0.10 resolution), domain.py, exceptions.py, celery_app.py (queue svc-image, keys svc-image:, keep image.precheck prerun JWT handler), core/extracted_clients/catalog_client.py (assert_product_ownership -> monolith ClusterIP), **app/ai_ops/** (VENDORED: client/cost_tracker/guardrail/budget_cap/prompt_registry/eval + prompts/watermark_v1.py; budget keys UN-prefixed in shared DB0), app/adapters/gcs.py (vendored), app/shared/{database,config,valkey}.py (TRIMMED: DATABASE_URL@image, VALKEY_URL, JWT_SECRET, GCS_*, GEMINI_API_KEY, LANGFUSE_*, AI_OPS_*, APP_ENV — NO MSG91/RAZORPAY), core/middleware/* (6 vendored), core/{auth,tenancy,errors,audit,cache}.py, i18n/messages_en.py (5 image IDs), requirements.txt (fastapi/sqlalchemy/asyncpg/celery/redis/httpx/pillow/google-cloud-storage + ai_ops deps; rembg conditional per §3.G; NO openpyxl/msg91/razorpay).

**ACCEPTANCE (merge-gate, lead verifies):**
- [ ] `git diff` extracted service.py vs monolith = ONLY catalog import line (:53) changed; ZERO changes to call sites :162/:248 (§16.G absolute).
- [ ] catalog_client shim: httpx.AsyncClient, 5s read/2s connect, 1 retry on 503/504, forwards JWT + X-Request-ID, base URL = monolith ClusterIP.
- [ ] ai_ops VENDORED in-process; watermark call still `call_gemini(ctx,"watermark.v1",...)`; budget brake hits SHARED Valkey DB 0 (un-prefixed `ai:cost:daily/pending` keys).
- [ ] Celery keys `svc-image:` prefix; broker DB1/results DB2; `image.precheck` prerun JWT handler preserved; all locked invariants present.
- [ ] Trimmed Settings carries GEMINI+LANGFUSE (image IS AI-consuming) but NO MSG91/RAZORPAY/openpyxl.
- [ ] `image.precheck.completed` direct-ORM audit to public.audit_events (cross-schema INSERT) preserved (tasks.py:370).
- [ ] §0.10 cross-schema-products resolved (Option b scoped-by-product_id OR documented transitional grant) — no silent cross-schema SQL.
- [ ] PR template fully filled, no `<>` placeholders.

**RE-DISPATCH triggers:** call site changed beyond imports -> §16.G; shim missing JWT -> §5.A; ai_ops made an HTTP call instead of vendored -> §2.E/D6; budget keys svc-image-prefixed (breaks global cap) -> C1/D6; rembg call site invented -> §3.G "zero call sites"; cross-schema products SQL survives -> §0.10/§2.D.

### 3.B meesell-api-routes-builder (sonnet)
**TASK:** Move 2 public routes + schemas; ADD the `/internal/products/{id}/images` callee shim route (image IS a callee of export — UNLIKE export which had none).
**Files:** router.py (2 routes verbatim, preserve both `@rate_limit` + POST `@audit_event` + idx fast-fail line 110), schemas.py (ImageUploadResponse/ImageSummary/ImagesListResponse), internal route `GET /internal/products/{id}/images` -> `service.list_images(user_id,product_id,db=db)` -> ImagesListResponse (forwards JWT; NOT Traefik-exposed). Regenerate OpenAPI.
**ACCEPTANCE:** 2 public + 1 internal route mounted; all async; public routes `Depends(get_current_user)`+`Depends(get_db)`; rate-limit decorators preserved; NO business logic inlined (handlers call service only); `/internal` shape matches MS-A frozen `list_images` (§3.E); OpenAPI 2 public endpoints + 3 schemas. PR template filled.
**RE-DISPATCH:** business logic inlined -> §14.B; `/internal` returns get_image_bytes shape instead of list_images -> spec_msA §0.4 row 6 + STOP/escalate; invented endpoint -> re-cite router.py.

### 3.C meesell-database-builder (sonnet) — Phase A, dispatch FIRST
**TASK:** Alembic schema-split moving `product_images` from public to schema `image`.
**Files:** `backend/services/svc-image/alembic/` chain, `version_table_schema="image"`; upgrade `ALTER TABLE product_images SET SCHEMA image`; tested downgrade `SET SCHEMA public`; Risk#5 pre-scan (every product_images row's product_id->products->user_id resolves; emit scan log); **§0.10 decision:** if Option (a), document the transitional `GRANT SELECT ON public.products TO image_user` for infra; if Option (b), confirm repository no longer SQL-joins products (services-builder coordinates).
**ACCEPTANCE:** upgrade+downgrade round-trip clean; version_table_schema="image"; dev applied BEFORE staging (NEVER reverse — head-divergence = P0 escalate); single head; §0.10 path documented.
**RE-DISPATCH:** head divergence dev<->staging -> P0 STOP escalate.

---

## 4. ai_ops vendoring (D6/A1) — precise (see SUB_PLAN_0C §4)
Copy `backend/app/ai_ops/`: client.py / cost_tracker.py / guardrail.py / budget_cap.py / prompt_registry.py / eval.py / __init__.py + prompts/watermark_v1.py. Budget brake SHARED via Valkey DB 0 keys `ai:cost:daily:{date}`+`ai:cost:pending:{date}`+`ai:budget:reservation:{id}` (budget_cap.py:26-48) — UN-prefixed (global ₹500 cap per D6). Confirm `prompt_registry.resolve()` doesn't eager-import autofill/smart_picker prompts (trim if safe). Env: GEMINI_API_KEY, LANGFUSE_*, AI_OPS_*. Cross-lane: `watermark.v1` pin must not drift — handoff to AI lead.

## 5. Monolith-side strangler (LEAD-owned, AT cutover only — NOT now)
main.py:46+:126 remove image_router; celery_app.py:103 remove image.tasks from include + :125 drop image.precheck from prerun set. Minimal+additive; PLANNED not executed at extraction start.

## 6. Merge-gate validation (lead, Phase C)
Full suite `def test_` MONOTONIC >=649 (live count at PR); image 29 tests green both modes + export/test_front_image_check.py:140 list_images-not-called assertion satisfiable; ruff clean; import-linter Contracts 2+5 hold (image is allowed ai_ops consumer); §16.G diff; ai_ops budget cross-service counter test; NO tautological tests (real audit row + real /internal shape + watermark skipped_budget->ready path); rollback runbook; §0.10 resolved.

## 7. GATE NOTE (NON-NEGOTIABLE)
Do NOT execute (cut branches / dispatch specialists) until MS-A founder gate merged + MS-A recipe exists. CONSUME the recipe and RECONCILE the `/internal/list-images` shim against MS-A's final contract doc FIRST. On any contract drift (esp. get_image_bytes vs list_images) -> STOP, escalate to master session, never improvise. D3 VM-fit (§7 SUB_PLAN_0C): svc-image is heaviest container — fresh founder D3 ask if node overflows at MS-2 deploy.
