# SUB-PLAN D — `pricing` Service Extraction

**STATUS: DRAFT — PHASE 1 (spec authored) — awaiting founder review.**
Authored under session `mesell-ms-pricing-session-1` (2026-06-12) by
`meesell-backend-coordinator` (HYBRID rule-7 STEP 1 — docs/spec only; NO
extraction code is written this session). This is sub-plan **D** of the
Microservices Migration MASTER_PLAN (LOCKED 2026-06-10, **v1.3** —
`§3.A.1` dev-complete start condition). It implements MASTER_PLAN §4 row
**D** (`pricing`, complexity **S**), and wave-program position
**MS-3** (parallel with MS-E `customer`) per the parallel-program
dispatch (`docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`, founder ruling MS-PAR-1).

---

## EXECUTION GATE (read first)

> **PHASE 1 = THIS DOCUMENT (now).** Spec authoring only. No service code,
> no schema move, no specialist dispatch.
>
> **PHASE 2 = EXTRACTION EXECUTION — GATED. Opens ONLY when BOTH conditions hold:**
> 1. **MS-2 complete** — BOTH the **B `dashboard`** AND the **C `image`**
>    founder gates are merged to `develop` (per the wave table in
>    `00-ms-parallel-program-dispatch.md`: "MS-3 opens when MS-2 both merged").
> 2. **The MS-A extraction recipe exists** in the backend lead's memory
>    (`.claude/agent-memory/meesell-backend-coordinator/`) — the validated
>    pilot pattern (SP01-pilot equivalent) that waves MS-2..5 copy.
>
> As of authoring (2026-06-12) NEITHER condition holds: MS-A (export) is the
> first extraction and has not completed its founder gate; B and C are
> spec-authoring only. **Phase 2 of THIS sub-plan MUST NOT begin until the
> master session confirms MS-2 = both B+C founder-gate-merged.** Pricing also
> runs **parallel with MS-E (`customer`)** under shared-file discipline (rule 4).

---

> Authoritative inputs read for this sub-plan (all file:line citations are
> from SOURCE at `origin/develop` tip `c859955`, NOT plan prose — the Wave-6
> fabricated-shape reject class is LAW per rule 3):
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED **v1.3** — §2.B/§2.C/§2.D, §3.A/§3.A.1/§3.B/§3.C, §4 row D, §5.A–F, §6 risks)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the SHAPE TEMPLATE — A1/A2 LOCKED, §16.G call-site contract, hybrid CI posture)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (common rules 1–9; wave gating)
> - `docs/plans/infra/microservices_infra_plan.md` (APPROVED v1.1 — schema-per-service §3.1, PgBouncer §3.2, sizing §6.3)
> - As-built source (current `develop`): `backend/app/modules/pricing/` (7 files: `__init__.py`, `router.py`, `service.py`, `repository.py`, `domain.py`, `schemas.py`, `exceptions.py`), `backend/app/shared/models/pricing_calc.py`, `backend/app/shared/models/product.py`, `backend/app/main.py:130` (mount), `backend/app/modules/catalog/service.py:919` + `backend/app/modules/category/service.py:548` (callees)
> - LIVE frontend: `frontend/apps/mfe-pricing/src/app/{pricing.model.ts, pricing.utils.ts, pricing.component.ts}` — **see §"Frozen API contract" for a load-bearing finding about the live FE wiring.**

---

## 0. GROUND TRUTH — verified against source 2026-06-12

Re-verified everything against the live tree. **Findings (all cited file:line):**

### 0.1 Branch / tree state — ACT ON THIS FIRST (at Phase 2 dispatch)
- **origin/develop tip = `c859955`** (PR #179 — final dev redeploy board/STATUS; carries MASTER_PLAN **v1.3** with §3.A.1). Confirmed via `git ls-remote origin develop`.
- **Local `develop` HEAD = `6d6ee51`** (`docs(dispatch): MS parallel program …`) is a DIVERGED local-only commit that is NOT the origin tip. The local working-tree MASTER_PLAN.md is the **stale v1.2** text (no §3.A.1); origin's is **v1.3**.
- **CONSEQUENCE:** cut ALL branches (this Phase-1 docs branch AND the Phase-2 extraction branches) from **`origin/develop` (`c859955`)**, NOT local `develop`. Same divergence pattern flagged in MS-A (`spec_msA_backend.md §0.1`). The local divergence is a master-tree hygiene matter; flag to founder, but it does not block — use origin as the cut point.

### 0.2 Pricing module = 7 files — CONFIRMED (NOT 8 — pricing has NO `tasks.py`)
`backend/app/modules/pricing/`: `__init__.py`, `router.py`, `service.py`, `repository.py`, `domain.py`, `schemas.py`, `exceptions.py` = **7 files.** Unlike `export` (8 files, has `tasks.py`), **pricing has NO Celery task** — it is synchronous deterministic math. There is no `pricing/tasks.py` and no `image.tasks`/`export.tasks`-style worker. This SIMPLIFIES the extraction vs export: no Celery app, no broker/results Valkey DB, no queue, no `asyncio.run` task wrapper.

### 0.3 Pricing has NO ai_ops dependency — CONFIRMED (A1/D6 does NOT touch pricing)
`grep -rn "ai_ops" backend/app/modules/pricing/` = **ZERO refs.** `__init__.py:16-17` states verbatim: *"NO AI track collaboration — pricing is deterministic math per §6A + §12.H (no `ai_ops.client` import, no Gemini call, no vendor adapter)."* The A1/D6 ruling (`ai_ops` vendored into AI-consuming services) does NOT apply to svc-pricing. svc-pricing's `requirements.txt` carries **NO gemini/langfuse**, and NO msg91/razorpay/gcs either (pricing touches no vendor at all).

### 0.4 Pricing has ZERO inbound callers — CONFIRMED (leaf consumer, like export)
`grep -rn "modules.pricing\|pricing_service\|pricing_router\|get_last_calc" backend/app` (outside `modules/pricing/`) returns ONLY:
- `backend/app/main.py:47` `from app.modules.pricing import pricing_router`
- `backend/app/main.py:130` `app.include_router(pricing_router)`

Nothing else in `backend/app/` imports pricing. The `get_last_calc` cross-module surface (`service.py:221`) is documented as consumed by `dashboard.service.summary` (§13 OPTIONAL), BUT the §2.D matrix is kept at 8 ✓ — **V1 dashboard does NOT call `get_last_calc`** (grep of `backend/app/modules/dashboard/` for `pricing` = 0 refs). **CONSEQUENCE: pricing is a LEAF CONSUMER — it needs OUTBOUND shims but exposes NO `/internal/*` endpoint of its own** (same posture as export). This is verified, not assumed.
- NOTE for the V1.5-dashboard-opt-in future: IF a later sub-plan elevates the §2.D matrix to 9 ✓ (dashboard → pricing.get_last_calc), svc-pricing would then need to add ONE `/internal/products/{id}/last-calc` endpoint. That is OUT OF SCOPE for this extraction (matrix is locked at 8 ✓) — but it is the only inbound seam that could ever appear, so it is named here for the record.

### 0.5 The 2 outbound cross-module call sites — RE-CITED FROM SOURCE
Authoritative list of every cross-module `<callee>_service.<method>` invocation in `backend/app/modules/pricing/service.py`:

| # | Call site (pricing/service.py) | Callee method (signature cited from callee SOURCE) | Returns |
|---|---|---|---|
| 1 | `:134` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` (route path) **and** `:241` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` (`get_last_calc` path) | `catalog/service.py:919` `assert_product_ownership(product_id: UUID, user_id: UUID, db: AsyncSession) -> None` | None (raises `ProductNotFoundError` 404 / `catalog.product.not_found`) |
| 2 | `:165` `category_service.get_commission(category_id, db=db)` | `category/service.py:548` `get_commission(category_id: UUID, db: AsyncSession) -> Decimal` | `Decimal` commission_pct as-stored; **NEVER None** — returns `Decimal("0.00")` when unseeded (callee docstring `:553-555`) |

**Imports to rewire (service.py:65-66):**
```python
from app.modules.catalog import service as catalog_service     # service.py:65  → shim
from app.modules.category import service as category_service   # service.py:66  → shim
```
Per §16.G these two import lines become:
```python
from app.core.extracted_clients import catalog_client as catalog_service
from app.core.extracted_clients import category_client as category_service
```
…re-exporting the SAME symbol name so the 3 call sites (`:134`, `:165`, `:241`) stay **byte-for-byte unchanged**. This is the §16.G absolute contract — the merge-gate `git diff` must show ONLY these 2 import-line changes (plus the §0.6 shared-ORM resolution below) in the service pipeline.

### 0.6 The SHARED-ORM read — the ONE non-obvious extraction hazard (cite it, do not gloss it)
`service.py:151-153` does a **direct shared-ORM read of a CATALOG-owned table**, NOT a cross-module service call:
```python
from app.shared.models.product import Product as ProductORM   # service.py:151 (local import)
product = await db.get(ProductORM, product_id)                # service.py:153
category_id = product.category_id                              # service.py:162
```
The in-line comment at `service.py:138-150` explicitly explains WHY: catalog exposes no bare `get_category_id(product_id)` surface in V1, so pricing reads the shared `Product` ORM directly (legal in the monolith per §16 — "the violation is calling another module's *repository*, not reading the shared ORM"). **AFTER EXTRACTION this is a hazard:** once catalog owns its own Postgres schema (`catalog`) and pricing owns `pricing`, `db.get(ProductORM, ...)` is a **CROSS-SCHEMA read that the §2.D "no cross-schema SQL — HTTP only" rule FORBIDS** (MASTER_PLAN §2.D: *"a service that needs another service's data goes through HTTP, never SQL"*). The repository's `find_latest_by_product` (`repository.py:147-155`) has the SAME problem — it JOINs `products` (catalog table) to scope-by-user.

**RESOLUTION (Phase-2 services-builder task — flagged here so it is not discovered late):** pricing needs `category_id` (and, for `get_last_calc`, a user-scoped product existence check) from catalog. Two clean options, services-builder picks one at build:
- **Option A (recommended) — widen the catalog `/internal/*` contract** so `get_product_for_export` (or a leaner `get_product_pricing_context`) returns `{category_id, user_id}`. Pricing's shim calls catalog-svc `/internal/products/{id}/...` and reads `category_id` from the HTTP response instead of `db.get(ProductORM)`. The repository's user-scoping JOIN is replaced by the ownership already asserted via the shim (the `assert_product_ownership` shim is the tenancy gate; the JOIN was belt-and-suspenders).
- **Option B — collapse step 3 into step 2** — extend the `assert_product_ownership` `/internal/*` shim to return `category_id` on success (currently returns None). Then pricing never touches `ProductORM` at all.

**Either way, the `from app.shared.models.product import Product` import (service.py:151) and `db.get(ProductORM)` (service.py:153) are DELETED in svc-pricing, and `repository.find_latest_by_product`'s JOIN through `products` (repository.py:149) is REWRITTEN** to not reference the catalog-owned `products` table. This is the single material code change beyond the 2 import rewires — it is NOT a §16.G violation (the §16.G contract covers the 3 cross-module *service-call* sites, which stay byte-for-byte; the shared-ORM read was never a §16.G-protected call site). **The merge gate must verify this resolution explicitly** — see Acceptance gate.

### 0.7 Router — CONFIRMED (1 route, NOT 2)
`router.py:62` `APIRouter(prefix="/api/v1", tags=["pricing"])`; **1 route only**:
- `router.py:68-75` `POST /products/{id}/price-calc` → **200** (not 202 — synchronous compute, returns the result inline), `response_model=PriceCalcResponse`, `@rate_limit(scope="price_calc", limit=600, window=3600)` (`router.py:74` — **per-IP, 600/h**; the high limit is deliberate per the `router.py:28-32` docstring: "lightweight stateless math; per-user limit would degrade typing-rapid-iteration UX"), `@audit_event("pricing.calculated")` (`router.py:75`), `Depends(get_current_user)` + `Depends(get_db)` (`router.py:79-80`).
- NOTE the exact path param is `{id}` (NOT `{product_id}` — pricing uses `id`, catalog/image/export use `{product_id}`). Cite this exactly; the Traefik route must match `{id}`.
- **MOUNTED-route verification (rule 3, the row-26 lesson):** `pricing_router` IS mounted at `main.py:130`. Exactly **1** `APIRoute` object mounts for pricing (verified — not schema-existence). svc-pricing must mount exactly 1 public route.

### 0.8 Celery — N/A (pricing has no task)
Per §0.2 pricing has no `tasks.py`. **svc-pricing has NO Celery app, NO broker/results Valkey DB, NO queue, NO `svc-pricing:` key prefix for tasks.** (Pricing may still use Valkey DB 3 cache via `core/cache.py` IF any path is cached — but grep of `modules/pricing/` for `cache`/`get_or_set` = **0 refs**: pricing is NOT a cache consumer either. So svc-pricing touches Valkey ONLY for the vendored `rate_limit_mw` sliding-window counter in DB 0, per §5.C.)

### 0.9 A2/D7 (middleware vendored, local JWT) — applies; pricing uses 4 of 6, plan_guard NO-OP
svc-pricing vendors the 6-mw chain (CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw). **`plan_guard_mw` RUNS but is NO-OP for pricing** — `router.py:33-37` docstring + `__init__.py`: *"plan-guard NOT participating (§12.I + §4.E) — pricing is one of the 3 V1 modules excluded from plan_guard alongside customer (§8) and dashboard (§13)."* JWT verified LOCALLY via vendored `core/auth.py` + shared `JWT_SECRET` (D7/A2). The middlewares pricing actually exercises: `auth_mw` (`Depends(get_current_user)`), `tenancy_mw` (`request.state.user_id`), `rate_limit_mw` (`@rate_limit price_calc 600/3600`), `audit_mw` (`@audit_event("pricing.calculated")` → `public.audit_events` cross-schema write), plus `request_id_mw` + CORS. = 4 active of 6 (plan_guard NO-OP, but present in the chain).

### 0.10 Test count — re-counted (rule 9 validation floor)
`grep -rn "def test_" backend/tests/` = **649** test functions (same baseline as MS-A `spec_msA_backend.md §0.9`; the "~823+" figure in dispatch prompts is a collected-items / parametrize-expanded count from a different measure, NOT the `def test_` count). Pricing's own tests = the 6 files under `backend/tests/modules/pricing/` (`test_pnl_formula.py`, `test_alerts.py`, `test_ownership_gate.py`, `test_commission_missing.py`) + `backend/tests/integration/{test_pricing_full_flow.py, test_pricing_persistence.py}`. **Validation rule for the merge gate: full-suite `def test_` count MONOTONIC (≥ 649) — the extraction ADDS svc-pricing tests, removes none until the strangler 7-day window closes.** Do NOT assert "823"; assert monotonic-vs-baseline-649 and quote the live count at PR time.

---

## Frozen API contract — `POST /api/v1/products/{id}/price-calc`

**ZERO response-shape drift is allowed.** The wire shape is `PriceCalcResponse`
(`backend/app/modules/pricing/schemas.py:88-104`). Every field below is cited
from that source with its serialization type.

### Request — `PriceCalcRequest` (schemas.py:32-67)
| Field | Type | Constraint (cited) | Serialization |
|---|---|---|---|
| `input_cost` | `Decimal` | `gt=0`, `decimal_places=2` (schemas.py:42-46) | **Decimal-string** in JSON |
| `target_margin_pct` | `Decimal` | `default=Decimal("30")`, `ge=0`, `le=Decimal("500")`, `decimal_places=2` (schemas.py:47-53) | **Decimal-string** |
| `override_commission_pct` | `Decimal \| None` | `default=None`, `ge=0`, `le=100`, 2dp (schemas.py:54-60) | Decimal-string or null — **V1 IGNORES** (V1.5 Pro) |
| `override_gst_pct` | `Decimal \| None` | `default=None`, `ge=0`, `le=100`, 2dp (schemas.py:61-67) | Decimal-string or null — **V1 IGNORES** |
- `model_config = ConfigDict(extra="forbid")` (schemas.py:40) — **unknown request fields are 422**. svc-pricing MUST preserve `extra="forbid"`.

### Response — `PriceCalcResponse` (schemas.py:88-104) — THE LOAD-BEARING SHAPE
| Field | Type | Decimal-string? | Notes (cited) |
|---|---|---|---|
| `mrp` | `Decimal` | **YES — Decimal-string** | quantized ROUND_HALF_EVEN 2dp (service.py:294, §12.B.1 step 6) |
| `meesho_price` | `Decimal` | **YES** | `= mrp` in V1 (service.py:297) |
| `seller_price` | `Decimal` | **YES** | `input_cost × (1 + target_margin/100)` (service.py:275) |
| `commission_pct` | `Decimal` | **YES** | from `category.get_commission` (service.py:165) |
| `commission_amount` | `Decimal` | **YES** | `mrp × commission_pct/100` (service.py:295) |
| `gst_pct` | `Decimal` | **YES** | constant `Decimal("18")` V1 (service.py:82) |
| `gst_amount` | `Decimal` | **YES** | `commission_amount × gst_pct/100` (service.py:296) |
| `profit` | `Decimal` | **YES** | `seller_price − input_cost` (service.py:298) |
| `profit_pct` | `Decimal` | **YES** | `profit / input_cost × 100` (service.py:299) |
| `alerts` | `list[PriceCalcAlert]` | n/a (array) | 0..3 alerts (see below) |
| `calculated_at` | `datetime` | **ISO-8601 string** | `persisted.created_at or now(tz=utc)` (service.py:214) |

**9 of the 11 fields are Decimal-strings.** This is because `PriceCalcResponse`
declares each as a bare `Decimal` with **NO `json_encoders` override, NO
`field_serializer`, and NO global Decimal→float encoder anywhere**
(verified: `grep json_encoders/field_serializer` in schemas.py = 0; `grep
Decimal/ORJSONResponse/default=str` in `main.py` + `core/errors.py` = none
that re-encode Decimal). **Pydantic v2's default Decimal serialization emits a
JSON STRING** (e.g. `"mrp": "157.96"`, not `157.96`). The existing tests assert
this at the Python-object boundary (`test_pricing_full_flow.py:179`
`assert response.mrp == Decimal("157.96")`). **svc-pricing MUST reproduce the
identical wire shape: bare `Decimal` fields, same `ROUND_HALF_EVEN` 2dp
quantization (`service.py:364-370` `_q`), NO float conversion.** A merge-gate
golden test must JSON-serialize one response and byte-compare against a frozen
fixture captured from the monolith — string-typed monetary fields, not floats.

### `PriceCalcAlert` (schemas.py:73-83) — array element shape
| Field | Type (cited) |
|---|---|
| `code` | `Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]` (schemas.py:78) |
| `message_id` | `str` — `validation_message_id` per §5A.H, e.g. `pricing.alert.low_margin` (schemas.py:79-81) |
| `severity` | `Literal["warning", "info"]` (schemas.py:82) |
Alert thresholds (service.py:94-100): LOW_MARGIN `profit_pct < 10` (warning); HIGH_MRP_MULTIPLIER `mrp/input_cost > 3` (warning); THIN_PROFIT `profit < 50` INR (info). Multiple may fire (service.py:323).

### Status codes (router.py:84-94)
200 OK (compute success) · 400 `validation.price.invalid_input` (Pydantic / V1.5 cross-field) · 401 (JWT) · 404 `catalog.product.not_found` (ownership gate bubble-up — `catalog.exceptions.ProductNotFoundError`) · 422 `pricing.commission.missing` (`CommissionMissingError`, exceptions.py:74-100). svc-pricing must reproduce the SAME `core/errors` 4-field envelope `{detail, code, validation_message_id, request_id}` (vendored `core/errors.py`).

### ⚠️ LOAD-BEARING FINDING — the LIVE frontend does NOT consume this contract today
**The dispatch premise ("the frontend contract is LIVE, Decimal-string
serialization is load-bearing, zero response-shape drift allowed") must be
read against this verified fact:** the live `mfe-pricing` micro-frontend
(`frontend/apps/mfe-pricing/src/app/`) is a **CLIENT-SIDE-ONLY simulation** —
it does **NOT call the backend `/products/{id}/price-calc` endpoint at all**:
- `pricing.utils.ts:6-33` `computePnlBreakdown(mrp, targetMargin)` computes the
  P&L **locally in TypeScript** with **hardcoded `COMMISSION_PCT=5`,
  `GST_PCT=5`** (utils.ts:4-5) and a `meesho_price = round(mrp*0.5)` heuristic.
  The docstring says verbatim: *"All arithmetic is client-side (no HTTP call
  required in V1 simulation)."*
- `pricing.component.ts` has **NO `HttpClient`, NO `.post(`, NO `api/v1`
  reference** (grep = 0). It only reads `route.snapshot.paramMap.get('id')`
  (component.ts:289) for the product id and clamps an MRP input (component.ts:307-308).
- The FE model `pricing.model.ts` (`PnlBreakdown`) uses a **DIFFERENT field set
  AND type** than the backend: `commission_amt`/`gst_amt`/`seller_payout`/
  `net_margin`/`net_margin_pct` as **`number`** (model.ts:1-11) — NOT the
  backend's `commission_amount`/`gst_amount`/`seller_price`/`profit`/`profit_pct`
  as **Decimal-string**.

**INTERPRETATION & RULING-REQUEST (flag for master/founder):** The backend
`/price-calc` contract is still the **FROZEN published OpenAPI shape** and the
extraction MUST preserve it byte-for-byte (zero drift) — that requirement
stands unconditionally, because (a) the contract is the V1_FEATURE_SPEC §F7
acceptance surface, (b) the FE is expected to wire to it before launch, and
(c) the extraction must not be the thing that changes it. BUT the **"breaking
the live FE at runtime" risk is currently ZERO** because no FE call site exists
yet — there is no runtime coupling to break during the strangler window. This
is GOOD for extraction safety (Risk reduced) but it is a **product gap the
master session should be aware of**: when the FE finally wires the real
endpoint, it must adopt the backend's Decimal-string shape (`commission_amount`,
not `commission_amt`; `net_margin`→`profit`; etc.) OR the backend contract gets
a FE-coordinated rename via a backend↔frontend memo BEFORE that wiring. **The
extraction does NOT resolve that mismatch — it freezes the backend side as-is.**
This is recorded so the wave program does not mistake "FE has a pricing screen"
for "FE consumes the pricing endpoint."

---

## DB surface

### Tables svc-pricing OWNS
| Table | Schema (V1.5) | Cited |
|---|---|---|
| `pricing_calcs` | `pricing` (moved from `public`) | ORM `backend/app/shared/models/pricing_calc.py:33`; MASTER_PLAN §2.D table |

`pricing_calcs` columns (pricing_calc.py:35-77): `id` (uuid PK), `product_id`
(FK → `products.id` ON DELETE CASCADE, pricing_calc.py:40-44), `mrp`/`meesho_price`/
`seller_price`/`margin` (Numeric(10,2)), `commission_pct`/`gst_pct`/`margin_pct`
(Numeric(5,2)), `created_at` (TIMESTAMPTZ default NOW()). One index
`idx_pricing_calcs_product_id` (pricing_calc.py:87). Append-only audit trail —
`insert_calc` is the only mutator, no UPDATE (repository.py:43-47).

### Tables svc-pricing READS but does NOT own (the cross-schema hazard)
| Table | Owner service | Where pricing touches it | Resolution |
|---|---|---|---|
| `products` | catalog-svc (schema `catalog`) | `service.py:153` `db.get(ProductORM)`; `repository.py:149` JOIN `products` for user-scoping; `pricing_calc.py:42` FK `products.id` | Per §0.6 — replace shared-ORM read + JOIN with the catalog `/internal/*` shim that returns `category_id`. **The `products.id` FK on `pricing_calcs` becomes a cross-schema FK** (`pricing.pricing_calcs.product_id REFERENCES catalog.products(id)`). Per MASTER_PLAN §2.D *"we drop cross-schema FKs as part of the iam extraction … rely on application-layer enforcement"* — BUT the products FK is dropped during **catalog** extraction (MS-5), not pricing. **At pricing extraction (MS-3) catalog is STILL in `public` schema** (catalog is MS-5, extracted LAST). So at MS-3: the FK `pricing_calcs.product_id → products.id` survives as a cross-schema FK (`pricing.pricing_calcs → public.products`), which PostgreSQL supports. The database-builder migration KEEPS the FK valid by ensuring `products` is still reachable; the FK is formally dropped only when catalog moves at MS-5 (a catalog-sub-plan concern, named here for ordering clarity). |

### The Postgres role split (per MASTER_PLAN §2.D / §5.B — infra handoff item)
- `CREATE SCHEMA pricing; GRANT USAGE ON SCHEMA pricing TO pricing_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA pricing TO pricing_user;`
- **`pricing_calcs` is append-only-insert in practice** but the grant includes UPDATE/DELETE for parity (no app path uses them).
- **`GRANT INSERT ON public.audit_events TO pricing_user`** — the `@audit_event("pricing.calculated")` decorator (router.py:75) writes a cross-schema audit row. Without this grant the audit write fails (same R3 pattern as export `handoff_msA_infra.md` I5). The integration test asserts an audit row lands.
- **Cross-schema SELECT on `public.products`** during the MS-3 window (until catalog extracts at MS-5) — IF Option B of §0.6 cannot fully eliminate the products read at MS-3, `pricing_user` needs `GRANT SELECT ON public.products TO pricing_user` as a TRANSITIONAL grant, revoked when catalog extracts. **PREFERRED: eliminate the read entirely via the §0.6 catalog `/internal/*` shim so NO cross-schema products grant is ever needed.** Flag to infra: if the shim resolution lands clean, this transitional grant is NOT required — confirm with backend lead before granting.

---

## Dependency analysis (the "does pricing need shims?" finding)

**FINDING — pricing needs OUTBOUND shims but NO `/internal/*` of its own.**

### What pricing IMPORTS from other modules (outbound — needs shims)
Cited from `service.py:65-69`:
| Import | Purpose | Becomes |
|---|---|---|
| `from app.modules.catalog import service as catalog_service` (service.py:65) | `assert_product_ownership` (`:134`, `:241`) | HTTP shim → catalog-svc `/internal/products/{id}/ownership-check` (the SAME shim MS-A froze for export — see below) |
| `from app.modules.category import service as category_service` (service.py:66) | `get_commission` (`:165`) | HTTP shim → category-svc `/internal/categories/{id}/commission` (**NEW shim — NOT in the MS-A export contract; pricing is the FIRST caller of `get_commission`**) |
| `from app.shared.models.product import Product` (service.py:151, local) | `db.get` for `category_id` | **NOT a shim — DELETED**; `category_id` comes from the catalog ownership/context shim per §0.6 |
| `from app.modules.catalog.exceptions import ProductNotFoundError` (service.py:159, local) | re-raise on TOCTOU race | vendored exception shape OR mapped from the catalog shim's 404 response (the shim translates catalog-svc 404 → local `ProductNotFoundError` so the envelope is identical) |

### What imports pricing (inbound — needs `/internal/*`)
**NOTHING (verified §0.4).** pricing exposes NO `/internal/*` endpoint. The only
theoretical inbound seam (`dashboard → get_last_calc`) is NOT wired in V1 (matrix
8 ✓). **CONCLUSION: pricing is a leaf consumer — outbound shims only, zero
inbound surface.** This makes pricing one of the cleaner extractions (like
export), gated to MS-3 only because the wave program sequences it there, not
because of inbound complexity.

### Shim contract — the 2 `/internal/*` endpoints pricing's callees must expose
These are CALLEE-side deliverables (catalog-svc / category-svc implement them
when THEY extract). svc-pricing's shims target them; during the MS-3 window both
callees are STILL IN-PROCESS (catalog=MS-5, category=MS-4 — both extract AFTER
pricing), so per the §3.A hybrid posture **pricing's shims point at the
monolith ClusterIP (`monolith-svc:8001`)**, not at not-yet-existent
catalog-svc/category-svc.

| Shim (svc-pricing) | Calls (HTTP) | Frozen from SOURCE | Callee implements at |
|---|---|---|---|
| `catalog_client.assert_product_ownership(product_id, user_id) -> None` (+ returns `category_id` per §0.6 resolution) | `GET monolith-svc/internal/products/{id}/ownership-check` (404 → `ProductNotFoundError`); response body `{category_id}` | `catalog/service.py:919` (+ §0.6 widening) | MS-5 (catalog sub-plan H) — **ALREADY the export-contract shim; pricing reuses it, adds the `category_id` field need** |
| `category_client.get_commission(category_id) -> Decimal` | `GET monolith-svc/internal/categories/{id}/commission`; response `{commission_pct: "<decimal-string>"}` (NEVER null — `0.00` = unseeded) | `category/service.py:548` | MS-4 (category sub-plan F) — **NEW: pricing is the first/only caller of `get_commission`; export uses `fetch_schema`+`get_field_enum`, NOT commission** |

**Cross-wave note (flag to master):** the `category /internal/.../commission`
shim is NEW vs the MS-A export contract — Sub-Plan F (category) must add it to
its `/internal/*` surface. And the catalog ownership shim needs the §0.6
`category_id`-on-response widening — Sub-Plan H (catalog) must honor that. Both
are recorded in the shim contract doc deliverable so the callee sub-plans
implement them. **Pricing extraction at MS-3 does NOT require the callees to be
extracted** (hybrid: shims hit the monolith) — but it DOES require the
`/internal/*` route shapes to be frozen now so F and H build them.

---

## Code surfaces

The `backend/services/svc-pricing/` tree is the new home; the old
`backend/app/modules/pricing/` tree is DELETED only after hybrid-mode CI passes
≥7 days (MASTER_PLAN §3.C) — until then both coexist (strangler fig).

### Backend — new service tree (`backend/services/svc-pricing/`)
| File | Tag | Description | Owner |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI; mounts pricing router (1 route); registers the 6-mw chain (plan_guard NO-OP) + `core/errors` handlers; `/health` + `/metrics`. **NO Celery, NO worker entrypoint.** | services-builder |
| `app/router.py` | NEW (from `modules/pricing/router.py`) | 1 public route `POST /products/{id}/price-calc` 200 verbatim (preserve `@rate_limit price_calc 600/3600` + `@audit_event pricing.calculated`); no `/internal/*`. | api-routes-builder |
| `app/service.py` | NEW (from `modules/pricing/service.py`) | `calculate` + `get_last_calc` + `_compute_pnl` + `_generate_alerts` + `_q` byte-for-byte; the 2 cross-module imports (service.py:65-66) → `extracted_clients` shims; the §0.6 shared-ORM read DELETED + replaced with shim-sourced `category_id`. | services-builder |
| `app/repository.py` | NEW (from `modules/pricing/repository.py`) | `insert_calc` + `find_latest_by_product`; bound to schema `pricing`; the `products` JOIN (repository.py:149) REWRITTEN per §0.6 (no catalog-table reference). | services-builder |
| `app/domain.py` | NEW (from `modules/pricing/domain.py`) | `PricingCalc`, `PnLBreakdown`, `PricingAlert` frozen dataclasses verbatim (no cross-module domain import — pricing's domain is self-contained, unlike export's `ComplianceBlock` import). | services-builder |
| `app/schemas.py` | NEW (from `modules/pricing/schemas.py`) | `PriceCalcRequest`/`PriceCalcAlert`/`PriceCalcResponse` (PRIVATE wire-shape) — **bare `Decimal` fields preserved verbatim for the Decimal-string contract**; `extra="forbid"` preserved. | api-routes-builder |
| `app/exceptions.py` | NEW (from `modules/pricing/exceptions.py`) | `PricingError`/`InvalidPriceInputError`/`CommissionMissingError` (3 classes per §12-PRICING-D3). | services-builder |
| `app/core/extracted_clients/catalog_client.py` | NEW | shim `assert_product_ownership` (+ `category_id` per §0.6) → catalog `/internal/*`. **Reuses the MS-A export catalog shim pattern.** Base URL = monolith ClusterIP during MS-3 (hybrid). | services-builder |
| `app/core/extracted_clients/category_client.py` | NEW | shim `get_commission` → category `/internal/categories/{id}/commission`. **NEW shim (not in MS-A).** | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored) | TRIMMED Settings: `DATABASE_URL`@schema `pricing`, `VALKEY_URL` (DB 0 rate-limit only), `JWT_SECRET`, `APP_ENV` ONLY. **NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS** (pricing touches no vendor — §0.3). Smallest pool of any service (lightweight stateless math, 1 insert + 0..1 select per request). | services-builder |
| `app/core/middleware/*` | NEW (vendored) | 6-mw chain (A2/D7). plan_guard NO-OP for pricing. | services-builder |
| `app/core/{auth,errors,tenancy,audit,metrics}.py` | NEW (vendored) | local JWT verify (auth.py), 4-field envelope (errors.py), `scope_to_user` (tenancy.py), audit write (audit.py), 7 Prometheus singletons (metrics.py per §5.F). | services-builder |
| `app/i18n/messages_en.py` | NEW (vendored subset) | ONLY pricing's IDs: `validation.price.invalid_input`, `pricing.commission.missing`, `pricing.alert.low_margin`, `pricing.alert.high_mrp_multiplier`, `pricing.alert.thin_profit` (5 keys, exceptions.py:13-19 + domain.py alert codes). | services-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, httpx, redis. **NO celery/openpyxl** (no task), **NO gemini/langfuse** (no AI). PIN versions to monolith (R5). | services-builder |
| `Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; **single entrypoint (api only — no worker)**; infra lead authors the real one. | infra-builder |
| `alembic/` | NEW | Own chain rooted at schema `pricing`; `version_table_schema="pricing"`. | database-builder |
| `tests/test_pricing_extraction.py` | NEW | Hybrid-mode integration test (in-process + HTTP-shim) + the Decimal-string golden byte-compare. | backend-coordinator |

### Backend — monolith-side changes (during strangler window, LEAD-owned)
| File | Tag | Description |
|---|---|---|
| `backend/app/modules/pricing/` (7 files) | KEEP-then-DELETE | Live until hybrid CI green ≥7 days, then deleted. |
| `backend/app/main.py:130` | MODIFY (at cutover) | Remove the in-process `pricing_router` mount (Traefik routes `/api/v1/products/{id}/price-calc` to svc-pricing). Until cutover, stays mounted (both modes run). Minimal + additive edit per rule 4 (shared file). |

### Infra (placeholders only — owned by infra lead, land on infra branch) — see `handoff_msD_infra.md`
| File | Tag | Description |
|---|---|---|
| `k8s/svc-pricing/deployment.yaml` | NEW | **api 1 replica ONLY (no worker pod — pricing has no Celery)**; req 50m/128Mi, lim 200m/256Mi (lighter than export — no XLSX build). |
| `k8s/svc-pricing/service.yaml` | NEW | ClusterIP `svc-pricing:8001`. |
| Traefik IngressRoute | NEW | `/api/v1/products/{id}/price-calc` → svc-pricing:8001. **⚠️ NESTS under the catalog-owned `/api/v1/products/*` prefix — see routing flag below.** |
| Postgres schema `pricing` + role | NEW | `CREATE SCHEMA pricing; GRANT … TO pricing_user;` + `GRANT INSERT ON public.audit_events`. |

### ⚠️ Traefik routing flag — `/price-calc` nests under catalog's `/api/v1/products/*`
The pricing path `/api/v1/products/{id}/price-calc` is a SUB-path of the
catalog-owned prefix `/api/v1/products/*` (MASTER_PLAN §2.C routes
`/api/v1/products/*` → catalog-svc). This is the SAME class of nesting as
image (`/api/v1/products/{id}/images*` → image-svc) and export
(`/api/v1/products/{id}/export-xlsx` → export-svc). **The Traefik rule needs an
explicit MORE-SPECIFIC match for `/price-calc` that takes priority over the
catalog catch-all** — Traefik IngressRoute priority must rank the
`PathRegexp` for `…/price-calc` ABOVE the catalog `/api/v1/products` prefix
rule, else catalog-svc swallows the pricing request. MASTER_PLAN §2.C already
carves out images and price-calc as exceptions to the catalog prefix ("except
images, price-calc, exports") — so the carve-out is PLANNED, but the infra lead
must implement the priority ordering explicitly. **This is flagged to infra in
`handoff_msD_infra.md` and to the master session as a cross-cutting gateway
concern shared with image (MS-2) and export (MS-1):** the priority ordering of
these three sub-path carve-outs vs the catalog catch-all must be coherent across
all of MS-1/MS-2/MS-3 — do not let three sessions each invent a different
priority scheme. **RECOMMEND the master session own a single Traefik priority
table** for the `/api/v1/products/*` family.

---

## Strangler-fig cutover + rollback

### Cutover (Phase 2, founder-gated)
1. Hybrid-mode CI green in BOTH modes (in-process monolith + svc-pricing-as-pod calling in-process catalog/category via shim → monolith ClusterIP) for ≥7 days.
2. Traefik IngressRoute for `/api/v1/products/{id}/price-calc` flips from monolith ClusterIP → `svc-pricing:8001` (priority-ranked above the catalog prefix).
3. Remove the in-process `pricing_router` mount at `main.py:130`.
4. Monolith keeps serving everything else (catalog, category still in-process at MS-3).

### Rollback (per MASTER_PLAN §3.C, specialized for pricing)
1. Traefik IngressRoute for `/price-calc` → back to monolith ClusterIP.
2. `core/extracted_clients/{catalog,category}_client.py` re-export the in-process `service.py` (1-line / 1-revert per §16.G).
3. `pricing_calcs` schema → back to `public` (`alembic downgrade` the schema-split). The cross-schema FK to `public.products` was never dropped (catalog still in-process at MS-3), so no FK restore step.
4. `kubectl delete deployment svc-pricing`.
5. Re-run hybrid-mode CI in pure in-process mode; document root cause in `docs/runbooks/svc-pricing-rollback.md` "Rollback Log".
Rollback allowed any time BEFORE Sub-Plan D declared complete (7-day green window).

---

## Test plan

**Pricing's own tests must be green in BOTH modes** (monolith pre-flip AND
extracted svc-pricing): the 6 source test files (§0.10) port to
`backend/services/svc-pricing/tests/`. Plus a new hybrid integration test.

| # | Test | Asserts REAL behavior (NOT tautological) |
|---|---|---|
| T1 | Decimal-string golden byte-compare | JSON-serialize a `PriceCalcResponse` from svc-pricing and byte-compare against a frozen fixture captured from the monolith — the 9 monetary fields are JSON **strings** (`"157.96"`), not floats; `calculated_at` is ISO-8601. **This is the zero-drift guard.** |
| T2 | P&L formula parity | `_compute_pnl(input_cost=100, target_margin_pct=30, commission=15, gst=18)` → `mrp == Decimal("157.96")` (§12-PRICING-D2, test_pricing_full_flow.py:179), `seller_price==130.00`, `profit==30.00`, `profit_pct==30.00`. Same `ROUND_HALF_EVEN`. |
| T3 | Ownership-gate shim | A product owned by another user → the catalog `/internal/*` shim returns 404 → svc-pricing surfaces `ProductNotFoundError` (404 `catalog.product.not_found`) with the identical envelope. Forwards the user JWT (R-pricing). |
| T4 | Commission-missing shim | `get_commission` shim returns `"0.00"` → svc-pricing raises `CommissionMissingError` (422 `pricing.commission.missing`). Real HTTP round-trip, not a stubbed `assert True`. |
| T5 | Alerts | LOW_MARGIN/HIGH_MRP_MULTIPLIER/THIN_PROFIT fire on the right thresholds; multiple-alert case (test_alerts.py). |
| T6 | Audit row lands | After a 200 calc, a `pricing.calculated` row is INSERTed into `public.audit_events` via the cross-schema grant (asserts a REAL row, not a mock — the R3/audit-grant guard). |
| T7 | `extra="forbid"` | Unknown request field → 422 (preserve schemas.py:40). |

**TAUTOLOGICAL TESTS ARE A REJECT-CLASS OFFENSE (rule 3 — and this lesson came
FROM pricing, Wave 6D):** the Gate-4 saga (`BE-PRICING-LASTCALC-TX-1`, board
2026-06-11) surfaced that `test_pricing_persistence.py::test_get_last_calc`
depended on a non-deterministic created_at tiebreak under the savepoint harness;
the fix made the timestamps deterministic (110→base/120→+1s/150→+2s) rather than
asserting a tautology. **Every svc-pricing test must assert observable behavior**
(a string-typed JSON field, a real audit row, a real 404 from a real shim
call) — never an `assert True`-class echo. The T1 golden byte-compare and T6
audit-row assertion are the explicit anti-tautology anchors.

**Validation floor (rule 9):** full backend suite `def test_` count MONOTONIC
≥ **649** (§0.10) — quote the live count at PR time; the extraction ADDS tests,
removes none until the 7-day strangler window closes. `ruff` clean on
`backend/services/svc-pricing/`. import-linter: svc-pricing must not introduce a
`domain→adapters.gemini` edge (Contract 2 — trivially satisfied, pricing has no
AI); the `check_scope_to_user.py` allowlist entry
`app.modules.pricing.repository.insert_calc` (tests/lint/check_scope_to_user.py:78)
must carry over to the extracted tree's lint config.

---

## Agent lineup + dispatch order (Phase 2 — GATED)

| Lead | Specialist | Builds |
|---|---|---|
| `meesell-backend-coordinator` | — | Authors this sub-plan; owns the merge gate `feature/microservices-pricing/backend` → `…/integration`; reviews vs §16.G + the §0.6 shared-ORM resolution + the Decimal-string golden; updates `feature_board_backend.md`. |
| → `meesell-database-builder` (sonnet) | Phase A | `pricing_calcs` schema-split Alembic (`public`→`pricing`), `version_table_schema="pricing"`, Risk#5 integrity pre-scan, tested downgrade. **Keeps the cross-schema FK to `public.products` valid (catalog not yet extracted at MS-3).** |
| → `meesell-services-builder` (opus) | Phase B | Extract service/repository/domain/exceptions; the 2 outbound shims; the §0.6 shared-ORM resolution (the heavy/novel part); trimmed Settings (no vendor); standalone main.py (no Celery). |
| → `meesell-api-routes-builder` (sonnet) | Phase B | Extract the 1 route + schemas (Decimal fields verbatim); confirm NO `/internal/*`; regenerate OpenAPI (1 endpoint + 3 schemas). |

**Dispatch order:** `database-builder` (Phase A) FIRST + infra handoff in
parallel → `services-builder` (Phase B heavy lift incl. §0.6) → `api-routes-builder`
(Phase B, once service signatures frozen). Iteration cap **3** per specialist.

```
PHASE A:  database-builder → schema-split migration   ‖   [infra lane → handoff_msD_infra.md]
PHASE B:  services-builder → extract + 2 shims + §0.6 resolution + standalone main.py
          api-routes-builder → 1 route + schemas (Decimal verbatim) + OpenAPI
PHASE C:  backend-coordinator → hybrid CI + test_pricing_extraction.py + merge gate + board flip
```

---

## Branch plan (Model C — rule 6)

Cut from **origin/develop (`c859955`)** — see §0.1. (Phase-1 docs branch this
session: `feature/microservices-pricing/docs-subplan`. Phase-2 extraction
branches below are created at MS-3 dispatch, NOT now.)

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-pricing/integration` | `origin/develop` | Integration; merge commits only; F3 protection at creation | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-pricing/backend` | `…/integration` | Backend specialist extraction | backend specialists |
| `feature/microservices-pricing/infra` | `…/integration` | Dockerfile, K8s, Postgres schema/role, Traefik route | meesell-infra-builder |

Worktrees per dispatch under `/tmp/mesell-wt/msD-*`. NEVER `git add -A` in a
worktree — scope every stage to `backend/services/svc-pricing/`. PR flow: group
→ integration = LEAD gate (squash); integration → develop = **FOUNDER gate (left
OPEN — lead does NOT approve)**, per D1.

---

## Acceptance gate (Phase 2 — DONE when)

- [ ] `feature/microservices-pricing/backend` PR merged to `…/integration` (backend lead gate)
- [ ] `feature/microservices-pricing/infra` PR merged to `…/integration` (infra lead gate)
- [ ] **§16.G:** `git diff` of extracted `service.py` shows ONLY the 2 import-line changes (service.py:65-66) + the §0.6 shared-ORM deletion — ZERO changes to the 3 cross-module call sites (`:134`, `:165`, `:241`)
- [ ] **§0.6 resolution verified:** `from app.shared.models.product import Product` and `db.get(ProductORM)` are GONE from svc-pricing; `category_id` comes from the catalog shim; repository's `products` JOIN rewritten
- [ ] **Decimal-string golden (T1) green:** the 9 monetary response fields serialize to JSON strings, byte-identical to the monolith fixture
- [ ] Hybrid-mode CI green in BOTH modes ≥7 days (shim → monolith ClusterIP, catalog/category still in-process)
- [ ] `cd backend && pytest services/svc-pricing/tests/test_pricing_extraction.py` green; pricing's 6 source test files green in the extracted tree
- [ ] full-suite `def test_` count MONOTONIC ≥ 649; `ruff` clean; import-linter clean
- [ ] Audit row lands (T6) via `GRANT INSERT ON public.audit_events TO pricing_user`
- [ ] Documentation deliverables landed (standalone OpenAPI 1 endpoint + 3 schemas; shim-contract doc with the 2 `/internal/*` shapes; `svc-pricing-rollback.md` runbook; `MASTER_PLAN §4 row D` annotation flip)
- [ ] **`BACKEND_ARCHITECTURE.md §12` amendment** ("Extracted to svc-pricing V1.5" note) — **§12 is LOCKED → FOUNDER APPROVAL REQUIRED** before this amendment lands (§7.3). Do NOT self-amend a LOCKED section.
- [ ] V1_FEATURE_SPEC §F7 (Price Calculator) acceptance still met against the extracted service
- [ ] CI gates 1/2/3 green; gates 4/5 advisory
- [ ] `feature_board_backend.md` row reflects MERGED
- [ ] Founder approval on `feature/microservices-pricing/integration` → `develop` PR
- [ ] **EXECUTION GATE confirmed at dispatch:** MS-2 (B dashboard + C image founder gates) merged AND MS-A recipe in lead memory — verified by the master session before Phase 2 begins

---

## Risk register (pricing-specific)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RD1 | The §0.6 shared-ORM `db.get(ProductORM)` cross-schema read is missed at extraction and svc-pricing silently SELECTs `public.products` cross-schema (violating §2.D HTTP-only) | **Medium** | High | Flagged explicitly in §0.6 + as a dedicated Acceptance-gate checkbox. services-builder MUST replace it with the catalog shim; merge gate greps the extracted `service.py`/`repository.py` for any `ProductORM`/`products` reference and REJECTS if present. |
| RD2 | Decimal-string drift — the extracted `PriceCalcResponse` serializes monetary fields as floats (e.g. an inadvertent `float()` cast or a `json_encoders` addition) | Low | **High** | T1 golden byte-compare against a monolith-captured fixture; bare `Decimal` fields preserved verbatim; NO `json_encoders` added. The contract is FROZEN even though no live FE consumes it yet (the FE wires it pre-launch). |
| RD3 | The NEW `category /internal/.../commission` shim shape is invented rather than cited from `category/service.py:548` | Medium | Medium | Shim contract doc freezes `get_commission(category_id) -> Decimal` from source `:548`; returns `{commission_pct: "<decimal-string>"}`, NEVER null (`0.00`=unseeded). Sub-Plan F (category) implements it. |
| RD4 | Traefik `/price-calc` sub-path is swallowed by the catalog `/api/v1/products/*` catch-all (priority misorder) | Medium | High | §"Traefik routing flag" + infra handoff: explicit priority ranking; recommend master session own a single Traefik priority table for the `/api/v1/products/*` family across MS-1/2/3. |
| RD5 | `CommissionMissingError` conflation (D1 — `get_commission` returns `0.00` for missing, never None) breaks if category-svc shim returns null instead of `0.00` | Low | Medium | Shim contract pins "NEVER null — `0.00` = unseeded" from callee docstring (`category/service.py:553-555`). T4 asserts the `0.00`→422 path over a real HTTP round-trip. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-pricing-session-1 (meesell-backend-coordinator) | Initial DRAFT — PHASE 1 spec authored per MASTER_PLAN v1.3 §4 row D + SUB_PLAN_01 shape. Grounded in AS-BUILT `modules/pricing/` (7 files, file:line cited). Findings: pricing = LEAF CONSUMER (outbound 2 shims, ZERO `/internal/*`); NO Celery, NO AI, NO vendor; the §0.6 shared-ORM `db.get(ProductORM)` cross-schema hazard; the NEW `category /commission` shim; the Decimal-string contract (9/11 fields); the LIVE-FE-does-NOT-consume-the-endpoint finding; the Traefik `/price-calc`-under-`/products` nesting flag. EXECUTION GATE: Phase 2 opens only at MS-2 (B+C founder gates merged) + MS-A recipe. Awaiting founder review. |

---

**END OF SUB-PLAN D — DRAFT (PHASE 1), awaiting founder review.**
