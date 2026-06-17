# SPEC — Microservices Sub-Plan D (`pricing` extraction) — BACKEND code work

**Session:** `mesell-ms-pricing-session-1` (2026-06-12)
**Author:** meesell-backend-coordinator (HYBRID rule-7 STEP 1 — SPEC only, no code)
**Plan basis:** `MASTER_PLAN.md` (v1.3, §3.A.1 dev-complete) + `SUB_PLAN_0D_pricing_extraction.md` (DRAFT, this session) + `SUB_PLAN_01_export_extraction.md` (shape template)
**Wave:** MS-3 (parallel w/ MS-E customer). **EXECUTION GATE: Phase 2 opens ONLY at MS-2 = both B dashboard + C image founder gates merged to develop + MS-A recipe in lead memory. NOT YET.**
**Mirrors:** `spec_msA_backend.md` structure.

---

## 0. GROUND TRUTH — verified against source 2026-06-12 (cite file:line, NOT plan prose)

### 0.1 Branch / tree
- **origin/develop tip = `c859955`** (PR #179). Cut Phase-2 branches from origin/develop, NOT local `develop` (`6d6ee51`, DIVERGED — local MASTER_PLAN is stale v1.2; origin is v1.3 w/ §3.A.1).

### 0.2 Module = 7 files (NOT 8 — pricing has NO tasks.py)
`backend/app/modules/pricing/`: `__init__.py`, `router.py`, `service.py`, `repository.py`, `domain.py`, `schemas.py`, `exceptions.py`. **NO Celery, no worker, no broker/results Valkey DB, no queue.** Simpler than export.

### 0.3 NO ai_ops, NO vendor — A1/D6 N/A
`grep ai_ops modules/pricing/` = 0. `__init__.py:16-17` "deterministic math". svc-pricing requirements: NO gemini/langfuse/msg91/razorpay/gcs.

### 0.4 ZERO inbound callers — LEAF CONSUMER
Only `main.py:47` import + `main.py:130` mount reference pricing outside the module. `get_last_calc` (service.py:221) is a cross-module surface for dashboard.summary (§13 OPTIONAL) but **dashboard does NOT call it** (matrix 8 ✓). **→ pricing needs OUTBOUND shims only, NO `/internal/*` of its own.** (Future: IF V1.5 elevates matrix to 9 ✓, ONE `/internal/products/{id}/last-calc` appears — OUT OF SCOPE now.)

### 0.5 The 2 outbound cross-module call sites (§16.G — stay byte-for-byte)
| # | Call site | Callee (cited) | Returns |
|---|---|---|---|
| 1 | `service.py:134` + `:241` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` | `catalog/service.py:919` `assert_product_ownership(product_id, user_id, db) -> None` | None (raises ProductNotFoundError 404) |
| 2 | `service.py:165` `category_service.get_commission(category_id, db=db)` | `category/service.py:548` `get_commission(category_id, db) -> Decimal` | Decimal, NEVER None (`0.00`=unseeded, callee docstring :553-555) |

Imports to rewire (service.py:65-66):
```python
from app.modules.catalog import service as catalog_service     # → catalog_client as catalog_service
from app.modules.category import service as category_service   # → category_client as category_service
```
Re-export same symbol so the 3 call sites (:134,:165,:241) are unchanged.

### 0.6 THE shared-ORM hazard (the novel part — do not gloss)
`service.py:151-153`: `from app.shared.models.product import Product as ProductORM` + `db.get(ProductORM, product_id)` + `:162` `category_id = product.category_id`. This is a SHARED-ORM read of a CATALOG-owned table (legal in monolith per §16). `repository.py:147-155` `find_latest_by_product` JOINs `products` for user-scoping. **After extraction both VIOLATE §2.D (no cross-schema SQL — HTTP only).**
- **RESOLUTION (services-builder picks A or B):**
  - A (recommended): widen catalog `/internal/*` (the export ownership/snapshot shim) to return `category_id`; pricing reads it from HTTP, deletes `db.get(ProductORM)`.
  - B: extend the `assert_product_ownership` `/internal/*` shim to return `category_id` on success.
- Either way: DELETE `Product` import (service.py:151) + `db.get(ProductORM)` (service.py:153); REWRITE repository's `products` JOIN (repository.py:149) to not reference catalog's table. NOT a §16.G violation (that covers the 3 service-call sites only).
- **Merge gate: grep extracted service.py + repository.py for `ProductORM`/`products` — REJECT if present.** (RD1 risk.)

### 0.7 Router = 1 route (NOT 2)
`router.py:62` `APIRouter(prefix="/api/v1", tags=["pricing"])`; `router.py:68-75` `POST /products/{id}/price-calc` → **200** (synchronous, NOT 202), `response_model=PriceCalcResponse`, `@rate_limit(scope="price_calc", limit=600, window=3600)` per-IP (router.py:74), `@audit_event("pricing.calculated")` (router.py:75), `Depends(get_current_user)`+`Depends(get_db)`. **Path param is `{id}` NOT `{product_id}`.** MOUNTED-verified (main.py:130), exactly 1 APIRoute.

### 0.8 Celery N/A; cache N/A
No tasks.py (§0.2). `grep cache/get_or_set modules/pricing/` = 0 — pricing is NOT a cache consumer. svc-pricing touches Valkey ONLY for vendored rate_limit_mw sliding-window (DB 0).

### 0.9 A2/D7 — 6-mw vendored, plan_guard NO-OP
plan_guard_mw runs but NO-OP (pricing excluded per §12.I/§4.E, alongside customer+dashboard). 4 active mw: auth, tenancy, rate_limit, audit (+request_id, CORS). Local JWT verify (shared JWT_SECRET).

### 0.10 Test floor = 649 `def test_` (monotonic). Pricing's own = 6 files: `tests/modules/pricing/{test_pnl_formula,test_alerts,test_ownership_gate,test_commission_missing}.py` + `tests/integration/{test_pricing_full_flow,test_pricing_persistence}.py`.

---

## 1. The frozen Decimal-string contract (zero drift)
`PriceCalcResponse` (schemas.py:88-104): **9 of 11 fields are bare `Decimal` → Pydantic v2 emits JSON STRINGS** (no json_encoders anywhere; verified main.py + core/errors.py). Fields: mrp, meesho_price, seller_price, commission_pct, commission_amount, gst_pct, gst_amount, profit, profit_pct (all Decimal-string); alerts (array of PriceCalcAlert{code,message_id,severity}); calculated_at (ISO-8601). Quantize ROUND_HALF_EVEN 2dp (`_q`, service.py:364-370). Request `extra="forbid"` (schemas.py:40). **svc-pricing MUST preserve bare Decimal fields verbatim — NO float, NO json_encoders.** Golden byte-compare test T1.
- **LIVE FE NON-CONSUMPTION (flag):** mfe-pricing (`pricing.utils.ts`) is client-side sim, does NOT call the endpoint; uses different shape (`net_margin`/`seller_payout` as number). Backend contract still FROZEN (pre-launch wiring expected) but ZERO runtime coupling to break now.

---

## 2. Builder sequence (3-phase)
```
PHASE A:  meesell-database-builder → pricing_calcs schema-split (public→pricing), version_table_schema="pricing", Risk#5 pre-scan, tested downgrade; KEEP cross-schema FK to public.products valid (catalog still in-process at MS-3)
          [INFRA LANE — meesell-infra-builder — handoff_msD_infra.md]
PHASE B:  meesell-services-builder → extract service/repository/domain/exceptions; 2 shims (catalog_client + category_client) under core/extracted_clients/; THE §0.6 shared-ORM resolution; trimmed Settings (NO vendor); standalone main.py (NO Celery)
          meesell-api-routes-builder → 1 route + schemas (Decimal verbatim); NO /internal/*; OpenAPI (1 endpoint + 3 schemas)
PHASE C:  meesell-backend-coordinator → hybrid CI + test_pricing_extraction.py (incl. T1 Decimal golden) + merge gate + board MERGED flip
```
Dispatch order: database-builder FIRST (+ infra parallel) → services-builder (heavy lift incl. §0.6) → api-routes-builder (once signatures frozen) → lead Phase C. Iteration cap 3.

---

## 3. Per-specialist SPECs

### 3.A meesell-services-builder (opus) — heavy lift
**Files (svc-pricing tree):** main.py (no Celery), service.py (calculate/get_last_calc/_compute_pnl/_generate_alerts/_q byte-for-byte; 2 import rewires + §0.6 resolution), repository.py (insert_calc + find_latest_by_product with products-JOIN rewritten), domain.py (3 dataclasses verbatim, self-contained), exceptions.py (3 classes), core/extracted_clients/{catalog_client,category_client}.py, shared/{database,config,valkey}.py (trimmed: DATABASE_URL@pricing, VALKEY_URL, JWT_SECRET, APP_ENV — NO gemini/langfuse/msg91/razorpay/gcs; smallest pool), core/{middleware/*,auth,errors,tenancy,audit,metrics}.py vendored, i18n/messages_en.py (5 pricing keys), requirements.txt (fastapi/sqlalchemy/asyncpg/httpx/redis — NO celery/openpyxl/gemini).
**ACCEPTANCE:** §16.G diff (only 2 import lines + §0.6 deletion; 3 call sites unchanged); §0.6 verified (no ProductORM/products in extracted service+repo); 2 shims httpx 5s read/2s connect, 1 retry 503/504, forward JWT + X-Request-ID; trimmed Settings no vendor; pricing.calculated audit → public.audit_events cross-schema; category shim returns NEVER null (`0.00`=unseeded); PR template filled.
**RE-DISPATCH:** call site changed beyond imports → §16.G + the 3-line list; shared-ORM read survives → §0.6 + RD1; vendor dep introduced → §0.3; missing JWT forward → §5.A.

### 3.B meesell-api-routes-builder (sonnet)
**Files:** router.py (1 route `POST /products/{id}/price-calc` 200, preserve `@rate_limit price_calc 600/3600` + `@audit_event pricing.calculated`; NO /internal/*), schemas.py (PriceCalcRequest/PriceCalcAlert/PriceCalcResponse — **bare Decimal fields verbatim**, `extra="forbid"`). Regenerate OpenAPI (1 endpoint + 3 schemas; count MOUNTED routes = 1, row-26 lesson).
**ACCEPTANCE:** 1 route mounted, async, Depends(get_current_user)+Depends(get_db); rate_limit+audit decorators preserved; NO business logic inlined; NO /internal/*; Decimal fields unchanged. PR template filled.
**RE-DISPATCH:** business logic inlined → §14.B-equiv; Decimal→float drift → §1 frozen contract; invented route shape → re-cite router.py.

### 3.C meesell-database-builder (sonnet) — Phase A, FIRST
**Files:** alembic/ rooted at schema `pricing`; `version_table_schema="pricing"`; migration upgrade `ALTER TABLE pricing_calcs SET SCHEMA pricing` + tested downgrade `SET SCHEMA public`; Risk#5 integrity pre-scan (every pricing_calcs.product_id resolves to a real products row — emit scan log). KEEP the cross-schema FK to `public.products` valid (catalog is MS-5, still in-process at MS-3 — the FK is dropped at catalog extraction, NOT here).
**ACCEPTANCE:** upgrade+downgrade round-trip clean; version_table_schema="pricing"; dev applied BEFORE staging (NEVER reverse — head divergence dev↔staging = P0 escalate); single head.
**RE-DISPATCH:** head divergence dev↔staging → P0 STOP escalate.

---

## 4. Monolith-side strangler (LEAD-owned, AT cutover only)
- `backend/app/modules/pricing/` (7 files) — KEEP until hybrid CI green ≥7 days, THEN delete.
- `backend/app/main.py:130` — remove in-process `pricing_router` mount at cutover (Traefik routes `/price-calc` to svc-pricing). Minimal+additive (shared file, rule 4).

---

## 5. Documentation deliverables (gate conditions)
- svc-pricing standalone OpenAPI (1 endpoint, 3 schemas).
- HTTP-shim contract doc — the 2 `/internal/*` callees pricing's shims target: catalog `/internal/products/{id}/ownership-check` (+ category_id per §0.6) ← `assert_product_ownership` (catalog/service.py:919); category `/internal/categories/{id}/commission` ← `get_commission` (category/service.py:548), returns `{commission_pct:"<decimal>"}` NEVER null. **Category /commission is NEW vs MS-A — Sub-Plan F must implement; catalog category_id widening — Sub-Plan H must honor.**
- `BACKEND_ARCHITECTURE.md §12` amendment ("Extracted to svc-pricing V1.5") — **§12 LOCKED → FOUNDER APPROVAL (§7.3).** Do NOT self-amend.
- `MASTER_PLAN.md §4 row D` annotation flip.
- `docs/runbooks/svc-pricing-rollback.md`.
- Hybrid CI note: during MS-3 catalog+category still in-process → shims point at monolith ClusterIP; NO callee standalone needed for pricing's OWN extraction CI.

---

## 6. Validation (merge-gate)
- full-suite `def test_` MONOTONIC ≥ 649; quote live at PR time.
- pricing's 6 source test files green in extracted tree + new T1 Decimal golden + T6 audit-row + T3/T4 shim round-trips.
- ruff clean svc-pricing; import-linter (no domain→adapters.gemini — trivial; carry `check_scope_to_user` allowlist entry `app.modules.pricing.repository.insert_calc` from tests/lint/check_scope_to_user.py:78).
- shim-contract doc complete (2 methods, source-cited).
- rollback runbook present.
- **NO tautological tests (Wave-6D PRICING lesson — BE-PRICING-LASTCALC-TX-1):** T1 byte-compares real JSON strings; T6 asserts a real audit row; T3/T4 assert real 404/422 over real shim HTTP. Never `assert True`.

---

## 7. Rollback (MASTER_PLAN §3.C, specialized)
1. Traefik `/price-calc` → monolith ClusterIP. 2. shims re-export in-process service.py (1-revert §16.G). 3. pricing_calcs schema → public (alembic downgrade; FK to public.products never dropped at MS-3 → no FK restore). 4. `kubectl delete deployment svc-pricing`. 5. re-run hybrid CI in-process; log root cause in runbook. Allowed any time before 7-day-green complete.

---

## 8. Constraints
- dev namespace ONLY; current node (svc-pricing api 50m/128Mi, lighter than export — no worker pod). NO D3 VM change (fresh founder ask at node-outgrow). Infra surfaces = handoff (`handoff_msD_infra.md`).
- **Traefik flag:** `/api/v1/products/{id}/price-calc` nests under catalog `/api/v1/products/*` — priority-rank ABOVE the catalog catch-all (shared concern w/ image+export; recommend master own a single priority table). RD4.
- §12 LOCKED — no self-amend.
