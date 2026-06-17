# FINAL EXECUTION SPEC — Microservices Sub-Plan C (`image` extraction) — BACKEND code work

**Session:** `mesell-ms-image-backend-session-1` (2026-06-13, MS-C PHASE 2 — EXECUTION step 1)
**Author:** meesell-backend-coordinator (HYBRID STEP 1 — SPEC reconciliation + git standup; NO code, NO dispatch)
**Supersedes:** `spec_msC_backend.md` (Phase-1 draft, 2026-06-12) where they conflict — THIS doc is the execution authority.
**LAW (FROZEN, reconciled against):**
- `docs/plans/microservices_migration/SHIM_CONTRACT_export_callees.md` (FROZEN on develop) — §2.6 `list_images` row is the byte-for-byte target.
- `recipe_ms_extraction.md` (VALIDATED MS-A SP01 pilot) — the proven step sequence + §7A Option-B pattern.
- PR #197 / develop `d4aa572` — §0.10 cross-schema tenancy RULED **OPTION B** (ownership HTTP shim, NO read-grant).
- `SUB_PLAN_0C_image_extraction.md` v1.1 on develop — §0.10 RULED block + dispatch order + C1/C2/C3 decisions.

**GATE STATUS:** SATISFIED. MS-A founder gate merged (squash `79525f3`); recipe in memory + on develop; SHIM_CONTRACT FROZEN on develop; §0.10 RULED Option B. Execution UNBLOCKED. Parallel-lane with MS-B (dashboard).

---

## 0. GROUND TRUTH — RE-VERIFIED FROM SOURCE @ origin/develop `d4aa572` (Wave-6 law)

This is a FRESH re-verification at the TRUE current develop tip — it CORRECTS the Phase-1 spec where develop moved.

### 0.1 Module surface (unchanged)
- image = 8 module files; owns 1 table `product_images` (→ schema `image` after split).
- 2 mounted public routes (`main.py:46` import `from app.modules.image import image_router`; `main.py:130` `app.include_router(image_router)`):
  - `POST /api/v1/products/{id}/images` → 202 (rate_limit image_upload 10/60 + audit `image.upload.received`)
  - `GET /api/v1/products/{id}/images` → 200 (rate_limit image_list 600/3600, no audit)
- image IS AI-consuming: `tasks.py` `call_gemini(ctx,"watermark.v1",...)`, `AICallContext(workload="watermark")`. → VENDOR ai_ops (C1/D6); SHARED budget brake Valkey DB 0.
- image's ONLY outbound HTTP shim = **catalog `assert_product_ownership`**. catalog = MS-5 (last) → shim base URL = monolith ClusterIP.

### 0.2 `list_images` shim — RECONCILED vs FROZEN SHIM_CONTRACT §2.6 — **NO DRIFT, contract wins, implement as frozen**

| Facet | FROZEN contract §2.6 | As-built monolith (verified @ d4aa572) | Reconciliation |
|---|---|---|---|
| Callee endpoint | `GET /internal/products/{product_id}/images?user_id={user_id}` | service.py:232 `list_images(user_id, product_id, *, db)` | MATCH — implement frozen path |
| Path param | `product_id` (UUID, path) | `{id}` on PUBLIC route; internal route uses `{product_id}` | Internal route uses `{product_id}` (frozen); public keeps `{id}` |
| Query param | `user_id` (UUID, query) | — | Internal route adds `?user_id=` query (frozen) |
| Callee source sig | image `service.py:232` `list_images(user_id: UUID, product_id: UUID, *, db: AsyncSession) -> ImagesListResponse` | EXACT MATCH @ service.py:232 (`*` kw-only `db`) | MATCH — DO NOT change signature |
| Response shape | `{ images: [ { image_id: uuid, idx: int, status: string, signed_url: string (1 h TTL), precheck_jsonb: object } ] }`, ordered idx ASC, len 0–4 | service.py builds `ImageSummary(image_id, idx, status, signed_url, precheck_jsonb)`; signed_url TTL = `settings.GCS_SIGNED_URL_TTL_SECONDS` | MATCH — confirm `GCS_SIGNED_URL_TTL_SECONDS` resolves to 3600 (1h) in trimmed Settings |
| Auth | forward JWT `Authorization: Bearer`; worker path forwards `X-Request-ID` only; `/internal/*` NOT Traefik-exposed | n/a (this is the NEW callee side) | Internal route trusts internal network; forwards JWT on API path |
| Error | 404 propagates (export wraps in front-image gate) | `assert_product_ownership` raises 404 on cross-tenant/not-found | MATCH — let 404 propagate |

**RESULT: ZERO material drift between FROZEN §2.6 and the as-built `list_images`. NO escalation.** The internal route is implemented EXACTLY as §2.6: `GET /internal/products/{product_id}/images?user_id={user_id}` → `service.list_images(user_id=user_id, product_id=product_id, db=db)` → `ImagesListResponse`. The ONE shape note for the api-routes-builder: the FROZEN response uses key `signed_url` (NOT `image_url`) and `idx` (NOT `order_idx`) — match the contract's JSON keys, which are the `ImageSummary` Pydantic field names. Verify `ImageSummary` field names against the frozen 5 keys at build time; if the as-built `ImageSummary` field names differ from the frozen key names, the FROZEN contract wins (it is the already-shipped, already-tested export consumer expectation) — adapt the schema field names/aliases, NOT the contract.

### 0.3 §0.10 cross-schema tenancy — **OPTION B (RULED, locked)** — repository-layer change list

Ruling (PR #197 / `d4aa572`, verbatim intent): "resolve image-service tenancy via the catalog `assert_product_ownership` HTTP shim, NOT a cross-schema DB read-grant. Repository scopes by `product_id` alone (post-shim); products join REMOVED; `image_user` granted NO products read access; transitional read-grant (former Option A) DISCARDED." Matches recipe §7A reusable pattern + LOCKED §2.D.

**What this means concretely:** the repository currently joins `products` (catalog-owned, → schema `catalog` at MS-5) in EVERY method via `scope_to_user(select(ProductORM.id), user_id)`. Under Option B, svc-image MUST NOT issue ANY cross-schema SQL read against `products`. The ownership shim (`assert_product_ownership`, called in `service.py` BEFORE every repository call) already proves tenancy. The repository scopes by `product_id` alone.

**EXACT repository.py change list (file:line @ d4aa572 — for the database-builder + services-builder to action together):**
- `repository.py:50` — `from app.core.tenancy import scope_to_user` → REMOVE (no longer used once joins drop). Confirm no other use.
- `repository.py:52` — `from app.shared.models.product import Product as ProductORM` → REMOVE (no products read in svc-image).
- `repository.py:84-95` `_owned_product_ids_subquery(user_id, product_id)` — the helper builds `scope_to_user(select(ProductORM.id), user_id).where(ProductORM.id == product_id).where(ProductORM.deleted_at.is_(None))`. → REPLACE: filter directly by `ProductImageORM.product_id == product_id` (no products subquery). The ownership shim upstream already guaranteed the seller owns `product_id`.
- `repository.py:164` (`update_precheck_result`) — `owned_product_ids = scope_to_user(select(ProductORM.id), user_id)` + `.where(ProductImageORM.product_id.in_(owned_product_ids))` → REPLACE with a direct `.where(ProductImageORM.id == image_id)` scope. NOTE: the worker path has no upstream shim call (it acts on a trusted `image_id` from the task payload, which was created post-ownership-check at upload). The `user_id` in the payload was validated at enqueue + by the `task_prerun` JWT re-validation handler (`celery_app.py:_revalidate_user_pre_task`). Scope by `image_id` alone is SAFE here — the row's existence under that `image_id` is the gate; the products join was redundant. **services-builder: document this worker-path tenancy reasoning in a code comment so the §16.G diff reviewer sees it is intentional, not a leak.**
- `repository.py:206` (`soft_delete_by_idx`) — same `scope_to_user(select(ProductORM.id), user_id)` + `.product_id.in_(...)` → REPLACE with `.where(ProductImageORM.product_id == product_id)` direct. (Internal helper, not router-exposed; called by catalog cascade which already owns tenancy.)
- `repository.py:235` (`find_by_product`) — uses `_owned_product_ids_subquery` → after helper rewrite, becomes `.where(ProductImageORM.product_id == product_id)` direct.
- `repository.py:264` (`find_by_id`) — `scope_to_user(...)` + `.product_id.in_(...)` → REPLACE with `.where(ProductImageORM.id == image_id)` direct.
- `repository.py:297` (`find_by_slot`) — uses `_owned_product_ids_subquery` → `.where(ProductImageORM.product_id == product_id)` direct.
- `repository.py:340-342` (`summarize_by_products`) — builds its own `scope_to_user(select(ProductORM.id), user_id).where(ProductORM.id.in_(product_ids)).where(ProductORM.deleted_at.is_(None))` → REPLACE with `.where(ProductImageORM.product_id.in_(product_ids))` direct. (Consumed by dashboard summary — caller owns tenancy via its own shim; svc-image scopes by the product_id list it was handed.)

**CRITICAL §16.G nuance for this wave (DEVIATES from MS-A export):** MS-A's §16.G law was "ONLY the import line changes; ZERO changes to method bodies." **Image CANNOT honor that for `repository.py`** — Option B REQUIRES rewriting the repository method bodies (removing the products join). This is a RULED, founder-approved deviation from the byte-for-byte rule, scoped to `repository.py` ONLY and ONLY for the products-join removal. **`service.py` and `tasks.py` STILL honor byte-for-byte** (only their import lines change — the `assert_product_ownership` call sites at service.py:162 + :248 are UNCHANGED). The §16.G AST-parity CI check (recipe §2) must therefore be run on `service.py` + `tasks.py` (expect byte-identical after import strip) but EXEMPTED for `repository.py` (expect the documented products-join-removal diff). **services-builder: produce a precise repository.py diff showing ONLY the scope_to_user→product_id-direct changes + the 2 import removals; nothing else may change.** The merge-gate (Phase C) asserts: (a) zero `ProductORM` / `scope_to_user` / `products` references survive in svc-image repository.py; (b) service.py + tasks.py AST-identical to monolith twins after import strip; (c) the `assert_product_ownership` shim is the SOLE tenancy gate.

`repository.py:14` / `:19` grep-anchor docstrings reference `scope_to_user` as the §19 tenancy anchor — UPDATE the docstring to reflect Option B (tenancy now via the upstream ownership shim, not a local join). The §19 import-linter `check_scope_to_user` AST scanner expects `scope_to_user` in product_images-touching methods — svc-image's repository is EXEMPT from that anchor (document in the svc import_rules allowlist; the shim is the new anchor). Coordinate this with the database-builder's Risk#5 pre-scan (which still validates every `product_images.product_id` resolves to a real `products` row IN THE MONOLITH at migration time — that pre-scan reads products in the monolith DB, which is fine; only the RUNTIME svc-image path drops the read).

### 0.4 Celery / queue — **PR #143 HAS MERGED — re-grounded at live state** (CORRECTION vs Phase-1)

Phase-1 flagged PR #143 as OPEN. **It is now MERGED to develop** (`celery_app.py:126-127` @ d4aa572):
```
task_routes={
    "image.precheck": {"queue": "image-tasks"},
}
```
- Monolith now routes `image.precheck` → queue `image-tasks` (NOT default). `export.xlsx` stays default queue (deliberately absent from task_routes, `celery_app.py:123-125`).
- Broker = Valkey DB 1 (`celery_app.py:91`); results = DB 2 (`:92`). include = `["app.modules.image.tasks", "app.modules.export.tasks"]` (`:102-104`).
- `task_prerun` `_revalidate_user_pre_task` enforces §18.F worker JWT re-validation for `{"image.precheck","export.xlsx"}` (`:136-137`).
- Locked worker invariants (move verbatim to svc-image): `task_serializer/result_serializer/accept_content="json"`, `task_acks_late=True`, `task_reject_on_worker_lost=True`, `worker_prefetch_multiplier=1`, `timezone="Asia/Kolkata"`+`enable_utc=True`, `task_track_started=True`.

**svc-image target (UNCHANGED by #143):** svc-image gets its OWN dedicated single-task Celery app — `include=["app.tasks"]`, queue **`svc-image`** (NOT `image-tasks`, NOT default), broker DB 1 / results DB 2, keys prefixed `svc-image:`. Keep `task_prerun` JWT re-validation for `image.precheck` ONLY + all locked invariants.

**MONOLITH-SIDE STRANGLER (Phase C / cutover, NOT now) — UPDATED for #143:** at cutover the monolith removal must drop THREE things (Phase-1 listed two):
1. `main.py:46` import + `main.py:130` `include_router(image_router)`.
2. `celery_app.py:103` `"app.modules.image.tasks"` from include + `image.precheck` from the `:136` prerun set.
3. **NEW (because #143 merged):** `celery_app.py:126-127` `task_routes={"image.precheck": {"queue": "image-tasks"}}` entry — drop it (the `image-tasks` queue is monolith-only; svc-image uses `svc-image`). PLANNED, not executed at extraction start. Re-read celery_app.py at cutover from the THEN-live develop.

### 0.5 GCS / rembg / ai_ops (carried forward UNCHANGED from Phase-1 frozen)
- GCS upload/download/signed-URL move with svc-image; path `meesell-images/{user_id}/{product_id}/{idx}.jpg`; ADC from pod SA (gcs.py reads instance metadata).
- **rembg DEFERRED** — declared in requirements.txt:14, ZERO call sites in backend/app. Do NOT add a call site; do NOT carry into svc-image requirements (recommended; §3.G). Cheapest D3-mitigation. Final confirm: founder/AI-lead at Phase 2 (raise if they want it carried).
- **ai_ops VENDORED** (C1/D6): copy `backend/app/ai_ops/` (client/cost_tracker/guardrail/budget_cap/prompt_registry/eval/__init__ + prompts/watermark_v1.py). Budget brake SHARED via Valkey **DB 0** keys `ai:cost:daily:{date}` + `ai:cost:pending:{date}` + `ai:budget:reservation:{id}` — **UN-prefixed** (global ₹500 cap per D6). Confirm `prompt_registry.resolve()` does not eager-import autofill/smart_picker prompts (trim if safe). Cross-lane: `watermark.v1` pin must not drift — handoff to AI lead.
- A2/D7 middleware: vendor the 6-mw chain (`request_id, auth_mw, tenancy_mw, rate_limit_mw, plan_guard_mw, audit_mw` + CORS); LOCAL JWT verify via vendored `core/auth.py` + shared `JWT_SECRET`. `plan_guard_mw` RUNS but is NO-OP for image (§11.J). `rate_limit_mw` + `audit_mw` ACTIVE.
- `image.precheck.completed` worker audit = direct ORM write to `public.audit_events` (cross-schema INSERT, §15.E exception) — bind vendored AuditEvent model `{"schema":"public"}` explicitly (recipe §5). This WRITE stays cross-schema by design; the §5 audit grant `GRANT INSERT ON public.audit_events TO image_user` is REQUIRED (distinct from the §0.3 products READ which is removed).

### 0.6 VALIDATION FLOOR — RE-COUNTED at d4aa572 (CORRECTION vs Phase-1)
- **Full-suite `def test_` in `backend/tests/` = 698** (LIVE, re-counted from source @ d4aa572). NOT the Phase-1 spec's "649" — develop advanced (+49 from MS-A merge + chores). MONOTONIC floor = **698** for this branch. Recipe §7 confirms: branch cuts from a NEWER tip, the +49 are NOT from this branch (which touches zero monolith code — prove via `git diff --stat origin/develop...HEAD -- backend/app backend/tests` = EMPTY).
- **image's own tests = 14 `def test_`** across `backend/tests/modules/image/` @ d4aa572: `test_flag_gate.py` (4), `test_integration.py` (3), `test_service_unit.py` (7). CORRECTION vs Phase-1's "29" — the test layout changed since Phase-1 authoring. The svc-image tests must keep these 14 satisfiable (relocated/adapted to the svc tree) + green in BOTH monolith (pre-flip) AND svc-image.
- Cross-module assertion to keep satisfiable: `backend/tests/modules/export/test_front_image_check.py` asserts `list_images` NOT called for `xlsx_only` — svc-image's `/internal` shim must not break this.
- Quote the LIVE `def test_` count at PR time; assert monotonic ≥ 698. Do NOT hardcode "823" (collected-items count, not `def test_`).

---

## 1. ORDERED PER-SPECIALIST BUILD SEQUENCE (the session dispatches these in this order)

Aligned to `recipe_ms_extraction.md` §1 + SUB_PLAN_0C §2 dispatch order. Iteration cap **3** per specialist.

### PHASE A (parallel — no inter-dependency)
**A1. `meesell-database-builder` (sonnet) — DISPATCH FIRST**
- Group branch: `feature/microservices-image/db` (cut from `…/integration`)
- Worktree: `/tmp/mesell-wt/msC-db`
- Scope: standalone Alembic chain under `backend/services/svc-image/alembic/`; `version_table_schema="image"`; upgrade `ALTER TABLE product_images SET SCHEMA image`; TESTED downgrade `SET SCHEMA public`; Risk#5 orphan pre-scan (every `product_images.product_id` resolves to a real `products` row IN THE MONOLITH DB at migration time — emit scan log). **§0.10 OPTION B: grant NO `products` read access to `image_user`** — the repository scopes by `product_id` alone (no cross-schema read to grant). Confirm in the migration's grant block / handoff that the ONLY cross-schema grant is `GRANT INSERT ON public.audit_events` (audit write), NOT any `products` SELECT.
- dev applied BEFORE staging — NEVER reverse (head divergence = P0 escalate). Single head.
- Depends on: nothing. Coordinates with infra lane (Postgres role/grant surface) + services-builder (confirms repository drops the products join so the no-grant is sound).

**A2. INFRA LANE — `meesell-infra-builder`** (NOT a backend specialist; via `handoff_msC_infra.md`)
- Group branch: `feature/microservices-image/infra` (cut from `…/integration`); worktree infra-lead-chosen.
- Runs parallel; see updated handoff (Option B → NO products grant).

### PHASE B (depends on A — service code targets the new schema)
**B1. `meesell-services-builder` (opus) — HEAVY-LIFT OWNER**
- Group branch: `feature/microservices-image/svc` (cut from `…/integration`)
- Worktree: `/tmp/mesell-wt/msC-svc`
- Scope: extract `service.py / tasks.py / repository.py / domain.py / exceptions.py` into `backend/services/svc-image/app/`. `service.py` + `tasks.py` = BYTE-FOR-BYTE except import lines (the `from app.modules.catalog import service as catalog_service` at service.py:53 → `from app.core.extracted_clients import catalog_client as catalog_service`; ai_ops imports in tasks.py → vendored `app.ai_ops`). `repository.py` = the §0.3 Option-B rewrite (products join removed, scope by product_id; documented diff ONLY). Build: `core/extracted_clients/catalog_client.py` (`assert_product_ownership` → monolith ClusterIP, transport per recipe §4); VENDORED `app/ai_ops/**` (C1/D6, un-prefixed DB-0 budget keys); vendored `app/adapters/gcs.py`; trimmed `app/shared/{database,config,valkey}.py` (DATABASE_URL@schema image, VALKEY_URL, JWT_SECRET, GCS_*, GEMINI_API_KEY, LANGFUSE_*, AI_OPS_*, APP_ENV — NO MSG91/RAZORPAY/openpyxl); vendored `core/middleware/*` (6) + `core/{auth,tenancy,errors,audit,cache}.py`; `i18n/messages_en.py` (5 image IDs); standalone `main.py` (6-mw, plan_guard NO-OP); single-task Celery app (`celery_app.py` queue `svc-image`, keys `svc-image:`, broker DB1/results DB2, `image.precheck` prerun JWT handler + locked invariants); `requirements.txt` (fastapi/sqlalchemy/asyncpg/celery/redis/httpx/pillow/google-cloud-storage + ai_ops/gemini/langfuse deps; rembg DEFERRED; NO openpyxl/msg91/razorpay). The `/internal` shim BODY = `service.list_images` (already present, unchanged).
- Depends on: A1 (schema target) + the §0.3 change list above.

**B2. `meesell-api-routes-builder` (sonnet) — near-parallel once B1 service signatures frozen**
- Group branch: `feature/microservices-image/routes` (cut from `…/integration`)
- Worktree: `/tmp/mesell-wt/msC-routes`
- Scope: move `router.py` (2 public routes verbatim — preserve both `@rate_limit` + POST `@audit_event` + idx fast-fail) + `schemas.py` (`ImageUploadResponse`, `ImageSummary`, `ImagesListResponse`); ADD the internal route `GET /internal/products/{product_id}/images?user_id={user_id}` → `service.list_images(user_id=user_id, product_id=product_id, db=db)` → `ImagesListResponse` (forwards JWT; NOT Traefik-exposed). **Match the FROZEN §2.6 response keys: `image_id, idx, status, signed_url, precheck_jsonb`** — verify `ImageSummary` field names equal these 5; if any differ, the frozen contract wins (adapt schema field/alias, not contract). Regenerate standalone OpenAPI (2 public endpoints + schemas).
- Depends on: B1 (service signatures). The `/internal` route can be cut on the routes branch; merge order at integration is db → svc → routes (or svc+routes together) — LEAD sequences merges so the integration build stays green.

### PHASE C (LEAD-owned — NOT a specialist; SEPARATE later dispatch)
**C. `meesell-backend-coordinator`** — hybrid-mode CI wiring; `backend/services/svc-image/tests/test_image_extraction.py` (§16.G AST parity on service.py+tasks.py [EXEMPT repository.py]; wire-shape JSON-schema parity via `model_json_schema()`; `/internal` shim JWT-forward/real-deserialize against FROZEN §2.6; cross-schema audit round-trip; ai_ops budget cross-service DB-0 coherence; Option-B no-products-read assertion); rollback runbook; MASTER_PLAN §4 row-C flip; board MERGED flip; recipe append. Merge-gate review of each group PR (group → integration = LEAD squash gate). Integration → develop = FOUNDER gate (I do NOT approve, D1).

**Heavy-lift owner: `meesell-services-builder`** (B1). Specialists needed: all three of {database-builder, services-builder, api-routes-builder}. auth-builder NOT needed (image has no auth surface; JWT verify is vendored core/auth.py, no MSG91/OTP/rotation).

---

## 2. BRANCH / GIT PLAN (Model C — all cut from `…/integration`)

| Branch | Cut from | Worktree | Owner | Gate |
|---|---|---|---|---|
| `feature/microservices-image/integration` | origin/develop `d4aa572` | `/tmp/mesell-wt/msC-integration` (STOOD UP) | lead | integration→develop = FOUNDER (left OPEN) |
| `feature/microservices-image/db` | …/integration | `/tmp/mesell-wt/msC-db` | database-builder | →integration = LEAD squash |
| `feature/microservices-image/svc` | …/integration | `/tmp/mesell-wt/msC-svc` | services-builder | →integration = LEAD squash |
| `feature/microservices-image/routes` | …/integration | `/tmp/mesell-wt/msC-routes` | api-routes-builder | →integration = LEAD squash |
| `feature/microservices-image/infra` | …/integration | infra-lead-chosen | infra lead | →integration (infra-lead-reviewed) |

Rules: NEVER `git add -A` — stage exact `backend/services/svc-image/...` paths. Apply F3 protection on integration (PR-only, review-count 0, checks=[], no force-push, enforce_admins false). NEVER switch the master tree's branch. Parallel-lane with MS-B (dashboard): svc-image diffs stay in `backend/services/svc-image/` + `k8s/svc-image/`; shared files additive/union-merge.

---

## 3. ESCALATIONS
**NONE.** The `list_images` shim reconciles cleanly against FROZEN §2.6 (zero material drift). §0.10 is RULED (Option B). The two corrections (PR #143 merged; test floor 698 / 14 image tests) are LIVE-STATE re-groundings, not conflicts — they tighten the spec, no founder ask needed. The §16.G repository.py deviation is founder-RULED (Option B requires it) — documented above as a scoped, approved exception; not an escalation.

The only forward-looking flag (NOT a blocker now): D3 VM-fit at MS-2 deploy — svc-image is the heaviest container; infra runs capacity math before deploy and raises a FRESH founder D3 ask if the node overflows (handoff §3). rembg-deferred is the cheapest mitigation.
