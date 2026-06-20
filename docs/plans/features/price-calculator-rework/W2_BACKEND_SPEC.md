# W2 — BACKEND ENGINE BUILD SPEC (Price Calculator Rework)

| Field | Value |
|---|---|
| Wave | **W2** (critical path — replaces the wrong #285 engine; W3/W4 bind to the response contract here) |
| Section | section-7 (`price-calculator`) — V1 Feature 7 |
| Author | `meesell-backend-coordinator` (Backend Lead) — HYBRID step-1 SPEC (no build, no dispatch) |
| Builders (step-2) | `meesell-services-builder`, `meesell-api-routes-builder`, `meesell-database-builder` |
| Merge-gate (step-3) | `meesell-backend-coordinator` (§2.1 squash review) |
| Branch | `feature/section-7/backend` (off `feature/section-7/integration`, **after #301 / W1 merges to integration**) |
| Type | code |
| Session | `mesell-price-calculator-backend-session-1` |
| Authoritative model | `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (confirmed 2026-06-19) |
| Depends on | **W1 (hard barrier)** — loader `backend/app/modules/pricing/pricing_lookup.py` (`get_shipping`, `get_commission_default`, `UnknownCategoryError`) + data file `meesho_pricing_lookup.json`. Branch off develop ONLY after #301 merges. |
| SUPERSEDES | merged PR #285 engine (`service.py`, `schemas.py`, `domain.py`, `pricing_calc.py`, `repository.py`, `router.py` notes) |

> **READ THE CENSUS MODEL, NOT THE STALE HANDOFF.** Only math source = `project_pricing_transfer_price_model.md`. `handoff_pricing_transfer_price.md` is SUPERSEDED/STALE — do NOT follow it. The wrong code being replaced is calibrated to the retracted "106→47" misread.

---

## 0. The confirmed formula (the ONLY math this wave ships — verbatim)

```
shipping        = pricing_lookup.get_shipping(meesho_leaf_id)   # per-category constant (W1 loader)
commission_pct  = request override, else 0 (default)
commission_fees = commission_pct × selling_price               # rounded 2dp
total_price     = selling_price + shipping
gst_on_shipping = 0.18 × shipping                              # rounded 2dp
tds             = 0.001 × total_price                          # rounded 2dp
tcs             = 0                                             # always 0
estimated_bank_settlement = selling_price − commission_fees − gst_on_shipping − tds − tcs
```

- **Rounding (Q4 RESOLVED):** `Decimal`, `ROUND_HALF_UP`, 2 dp. Each term (`commission_fees`, `gst_on_shipping`, `tds`) is quantized to 2dp **first, then subtracted**. Match census/real-order to the paise.
- **NET-PROFIT layer DEFERRED to V1.5 (G-NETPROFIT):** NO `input_cost`, NO `output_gst`, NO `landed_cost`, NO `net_profit`, NO `margin`, NO `markup`, NO `wdrp`, NO `mrp`, NO `return_rate`, NO `rto`, NO `logistics_fee`, NO `fixed_fee` anywhere (request/response/domain/model/migration). A CI grep gate enforces zero references to these tokens under `app/modules/pricing/`.
- Negative `estimated_bank_settlement` returns **200** with a `NEGATIVE_SETTLEMENT` alert — never a 400.

---

## 1. Service rework — `meesell-services-builder`

**Files owned:** `backend/app/modules/pricing/service.py`, `backend/app/modules/pricing/domain.py`.

### 1.1 `domain.py` — replace dataclasses
- **DELETE** `PnLBreakdown` (logistics_fee/fixed_fee/rto/markup/margin/wdrp). **DELETE** the wrong fields on `PricingCalc` domain.
- **NEW** `SettlementBreakdown` (frozen dataclass), exactly these fields, all `Decimal`:
  `selling_price, shipping, total_price, commission_pct, commission_fees, gst_on_shipping, tds, tcs, estimated_bank_settlement`.
- **KEEP** `PricingAlert` but change the `code` Literal to `["NEGATIVE_SETTLEMENT"]` only (drop LOW_MARGIN / SHIPPING_DOMINATES — they referenced margin/deductions that no longer exist; V1 ships ONE alert).
- **NEW** `PricingCalc` domain dataclass mirrors the new persisted column set (see §3) — `id, product_id, selling_price, shipping, total_price, commission_pct, commission_fees, gst_on_shipping, tds, tcs, estimated_bank_settlement, meesho_leaf_id, created_at`.

### 1.2 `service.py` — rewrite
- **DELETE** all wrong constants: `WDRP_DELTA`, `SHIPPING_BRACKET`, `SHIPPING_FLAT`, `SHIPPING_HIGH`, `DEFAULT_GST_PCT`, `DEFAULT_TCS_PCT`, `DEFAULT_TDS_PCT`, `DEFAULT_LOGISTICS_FEE`, `DEFAULT_FIXED_FEE`, `_bracketed_shipping`, the `106→47` calibration docstring. Change `DEFAULT_COMMISSION_PCT` to `Decimal("0")`.
- Replace `_q` rounding mode from `ROUND_HALF_EVEN` → **`ROUND_HALF_UP`** (Q4).
- **NEW pure function** `_compute_settlement(*, selling_price: Decimal, shipping: int, commission_pct: Decimal) -> SettlementBreakdown` implementing §0 exactly. No I/O, no DB, no Meesho calls.
- **`calculate(user_id, product_id, request, *, db)`** new orchestration:
  1. `await catalog_service.assert_product_ownership(product_id, user_id, db=db)` (M6 gate — unchanged).
  2. Resolve the category leaf: `meesho_leaf_id = await catalog_service.get_product_meesho_leaf_id(product_id, user_id, db=db)` (NEW catalog accessor — see §1.3). This is the canonical source — the API does NOT take a category from the client (see §2 decision).
  3. `shipping = pricing_lookup.get_shipping(meesho_leaf_id)` — may raise `UnknownCategoryError`. Do NOT catch it in the service; let it bubble to the router (§2.3) which maps it to a clean 4xx.
  4. `commission_pct = request.commission_pct if request.commission_pct is not None else pricing_lookup.get_commission_default(meesho_leaf_id)` (the lookup returns `Decimal('0')` for V1; reading through the accessor honors W6 refreshes).
  5. `breakdown = _compute_settlement(selling_price=request.selling_price, shipping=shipping, commission_pct=commission_pct)`.
  6. `alerts = _generate_alerts(breakdown)` — ONLY the `NEGATIVE_SETTLEMENT` rule (`estimated_bank_settlement < 0`).
  7. Persist via `pricing_repo.insert_calc(...)` (new signature, §3).
  8. Return `PriceCalcResponse` (§2.2).
- **`get_last_calc`** — keep; map to the new domain/response shape.
- **Cross-module imports:** `from app.modules.catalog import service as catalog_service` (ownership gate + NEW leaf accessor) and `from app.modules.pricing import pricing_lookup`. The `category` import that #285 retired stays retired (we reach the leaf via catalog, not category directly — preserves the §2.D matrix; see §5 risk).

### 1.3 NEW catalog accessor (cross-module dependency — flagged to api-routes-builder NOT to author)
`catalog.service.get_product_meesho_leaf_id(product_id, user_id, *, db) -> str` — resolves product → `category_id` → `categories.meesho_leaf_id`, scoped to `user_id`, raises `ProductNotFoundError` on miss/cross-tenant. **OWNER DECISION:** this is a catalog-module surface, so it is built by `meesell-services-builder` as part of this wave but in `modules/catalog/service.py` (NOT a pricing file). It reads `category.service.get_super_id`-style. This is an EXISTING allowed edge (pricing→catalog is already ✓ in §2.D); no new ✗→✓ matrix change. The accessor may internally call a new `category.service.get_meesho_leaf_id(category_id, db)` (mirrors `get_commission`/`get_super_id`) — catalog→category is also already ✓.

---

## 2. Schemas + router — `meesell-api-routes-builder`

**Files owned:** `backend/app/modules/pricing/schemas.py`, `backend/app/modules/pricing/router.py`, `backend/app/modules/pricing/repository.py` (signature only — model/migration is database-builder).

### 2.1 Request schema `PriceCalcRequest`
**DECISION — the API does NOT take a category identifier.** The current request takes none; the product already carries `category_id` and the seller is calculating for a known product (`POST /products/{id}/price-calc`). Resolving leaf server-side (§1.2 step 2) is the single-source-of-truth path and avoids a client/category drift bug. Keep the request minimal:
```
PriceCalcRequest:
  selling_price: Decimal  = Field(gt=0, decimal_places=2)   # the listed Meesho price
  commission_pct: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
  model_config = ConfigDict(extra="forbid")
```
**REMOVE** every other field: `meesho_price` (renamed → `selling_price`), `input_cost`, `return_rate_pct`, `mrp`, all `override_*`. (`extra="forbid"` means a stale FE sending old fields gets a 422 — coordinate via the W3 handoff so FE ships the new body in lockstep.)

### 2.2 Response schema `PriceCalcResponse` — **THE CONTRACT W3/W4 BIND TO**
All monetary fields `Decimal` serialized as **string** (2dp, preserves precision; FE parses via `Number()`):
```
PriceCalcResponse:
  selling_price:              Decimal     # echo of request
  shipping:                   Decimal     # per-category constant (from lookup; serialized 2dp)
  total_price:                Decimal     # selling_price + shipping
  commission_pct:             Decimal     # the pct actually applied (override or 0)
  commission_fees:            Decimal     # commission_pct × selling_price
  gst_on_shipping:            Decimal     # 0.18 × shipping
  tds:                        Decimal     # 0.001 × total_price
  tcs:                        Decimal     # always 0.00
  estimated_bank_settlement:  Decimal     # the headline output
  disclaimer:                 str         # STATIC verbatim Meesho text (see below)
  alerts:                     list[PriceCalcAlert]   # 0 or 1 (NEGATIVE_SETTLEMENT)
  calculated_at:              datetime
```
`PriceCalcAlert`: `{ code: Literal["NEGATIVE_SETTLEMENT"], message_id: str, severity: Literal["warning"] }`.

**`disclaimer` exact string (verbatim from the model memory — DO NOT paraphrase):**
> Bank settlement amount may vary slightly based on the quantity in the order, Meesho commission policy at the time of the order and the actual weight of the product as calculated by our third party delivery partner.

(Ship it as a literal in the response. A `disclaimer_message_id` i18n key MAY be added later; V1 ships the literal English string to unblock W3 — flag to i18n owner as a follow-up, not a blocker.)

### 2.3 Router `router.py`
- KEEP: path `POST /api/v1/products/{id}/price-calc`, `Depends(get_current_user)`, `get_db`, `@rate_limit(scope="price_calc", limit=600, window=3600)`, the `FEATURE_PRICE_CALCULATOR_ENABLED` 404 flag guard, plan-guard NON-participation.
- SWAP `response_model` to the new `PriceCalcResponse`.
- `@audit_event` payload → `{product_id, selling_price, estimated_bank_settlement}` (drop margin_pct/input_cost — they no longer exist).
- **NEW error mapping:** `pricing_lookup.UnknownCategoryError` → register a handler (in `pricing/exceptions.py` + `core/errors`) translating it to **422** `pricing.category.no_pricing_data` (NOT 500). A seeded category with no pricing row is a clean data-integrity 4xx, surfaced via the locked error envelope. Update `pricing/exceptions.py` with a `CategoryPricingUnavailableError` wrapping it if the §4.F handler pattern requires a `PricingError` subclass.
- DELETE the docstring note about the `pricing.commission.missing` 422 (commission is now optional, never missing).

### 2.4 Repository `repository.py`
- Rewrite `insert_calc(...)` signature to the new column set (§3): `product_id, selling_price, shipping, total_price, commission_pct, commission_fees, gst_on_shipping, tds, tcs, estimated_bank_settlement, meesho_leaf_id`. Stop writing every #285 column.
- `find_latest_by_product` + `_orm_to_domain` map only the new columns. Keep the tenancy JOIN through `products`.

---

## 3. Migration + model — `meesell-database-builder`

**Files owned:** `backend/app/shared/models/pricing_calc.py`, `backend/alembic/versions/<new>_pricing_confirmed_model.py`.

**Q3 RESOLVED — KEEP-NULLABLE (do NOT drop).** #285 is on develop, not prod.

### 3.1 Model `pricing_calc.py`
- **ADD** new nullable columns: `selling_price NUMERIC(10,2)`, `shipping NUMERIC(10,2)`, `total_price NUMERIC(10,2)`, `commission_fees NUMERIC(10,2)`, `gst_on_shipping NUMERIC(10,2)`, `tds NUMERIC(10,2)`, `tcs NUMERIC(10,2)`, `estimated_bank_settlement NUMERIC(10,2)`, `meesho_leaf_id VARCHAR(16)`. Keep existing `commission_pct NUMERIC(5,2)`, `created_at`, `product_id`, `id`.
- **KEEP-NULLABLE & STOP WRITING** the wrong #285 columns: `mrp, meesho_price, seller_price, gst_pct, margin, margin_pct, estimated_payout, referral_commission, shipping_charge, logistics_fee, fixed_fee, gst_on_fees, rto_expected_loss, return_rate_pct, markup_pct, wdrp_price`. Leave the column definitions in the model with a `# DEPRECATED #285 wrong-model column — kept nullable per Q3, never written` comment. Do NOT drop, do NOT alter their nullability (they are already nullable).

### 3.2 Alembic migration
- `down_revision = "c2d3e4f5a6b7"` (current live monolith head — re-verify at build time; W1 adds NO migration so head is unchanged by W1).
- `upgrade()`: `op.add_column(...)` for the 9 new columns (all nullable). NO drops.
- `downgrade()`: `op.drop_column(...)` the 9 added columns only. Test upgrade+downgrade locally; no head divergence dev↔staging.
- NO `output_gst`/`landed_cost`/`net_profit` columns (V1.5).

---

## 4. Golden tests — owned by `meesell-services-builder` (engine) + api-routes-builder (router/integration)

**File:** rewrite `backend/tests/modules/pricing/test_pnl_formula.py` → `test_settlement_formula.py`; rewrite `test_estimator_calibration.py` → golden anchors; delete/rewrite `test_alerts.py` to the single alert.

| Test | Assertion |
|---|---|
| `test_real_order` | `_compute_settlement(selling_price=70, shipping=45, commission_pct=0)` → `estimated_bank_settlement == Decimal("61.78")` EXACT (gst_on_shipping=8.10; tds on total 115 = 0.115 → 0.12 via ROUND_HALF_UP; 70−8.10−0.12 = 61.78). SKU anchor TTC-BL-OR-HP-NG-P4. |
| `test_census_sanity` | `selling_price=100, shipping=82, commission_pct=0` → `estimated_bank_settlement == 85.06`, `gst_on_shipping == 14.76`, `tds == 0.18`, `total_price == 182`. (sscat_id 10949) |
| `test_census_wide` | For a sampled N≥50 sscat_ids from `meesho_pricing_lookup.json`, `_compute_settlement(100, lookup[id].shipping, 0).estimated_bank_settlement` reproduces the census `transfer_price_at_100` (read from `logs/scraper/transfer_price_census_summary.json`) within `Decimal("0.01")`. |
| `test_commission_override` | `commission_pct=2, selling_price=100` → `commission_fees == 2.00`, settlement reduced by exactly 2.00 vs the `commission_pct=0` case. |
| `test_tcs_always_zero` | `tcs == Decimal("0.00")` for every case. |
| `test_negative_settlement_is_200_alert` | router-level: a selling_price small enough vs shipping that settlement < 0 → HTTP 200 + one `NEGATIVE_SETTLEMENT` alert (NOT 400). |
| `test_unknown_category_is_4xx` | router-level: product whose category leaf is absent from the lookup → `UnknownCategoryError` surfaces as **422** `pricing.category.no_pricing_data`, NOT 500. |
| `test_ownership_404_preserved` | cross-tenant / missing product → 404 `catalog.product.not_found` (M6 gate). |
| `test_flag_off_404` | `FEATURE_PRICE_CALCULATOR_ENABLED=false` → 404. |
| `test_no_dead_tokens_grep` | grep gate: zero `WDRP\|logistics_fee\|fixed_fee\|rto\|markup\|input_cost\|net_profit\|output_gst\|landed_cost\|margin_pct` under `app/modules/pricing/`. |

Backend integration test: `backend/tests/test_price_calculator_integration.py` (lead-authored at merge-gate) exercises the full route end-to-end with a seeded product + real lookup → asserts the response contract shape + ₹61.78 golden.

CI gates 1 (unit), 2 (smoke), 3 (lint) MUST be green. Gate 5 golden_roundtrip N/A (no XLSX surface in W2) — justify in PR.

---

## 5. File ownership map (no overlap; W2 touches NO frontend/export/docs)

| File | Owner | Action |
|---|---|---|
| `backend/app/modules/pricing/domain.py` | services-builder | rewrite (SettlementBreakdown, single alert) |
| `backend/app/modules/pricing/service.py` | services-builder | rewrite (`_compute_settlement`, new `calculate`) |
| `backend/app/modules/catalog/service.py` | services-builder | ADD `get_product_meesho_leaf_id` accessor (additive only) |
| `backend/app/modules/category/service.py` | services-builder | ADD `get_meesho_leaf_id(category_id, db)` if needed (additive; mirrors `get_commission`) |
| `backend/app/modules/pricing/schemas.py` | api-routes-builder | rewrite request + response |
| `backend/app/modules/pricing/router.py` | api-routes-builder | swap response_model, audit payload, UnknownCategoryError→422 mapping |
| `backend/app/modules/pricing/repository.py` | api-routes-builder | new `insert_calc` signature + `_orm_to_domain` |
| `backend/app/modules/pricing/exceptions.py` | api-routes-builder | add `CategoryPricingUnavailableError` (if §4.F needs a PricingError subclass) |
| `backend/app/core/errors.py` | api-routes-builder | register the 422 handler (additive) |
| `backend/app/shared/models/pricing_calc.py` | database-builder | add 9 nullable columns; deprecate-comment #285 columns (keep) |
| `backend/alembic/versions/<new>_pricing_confirmed_model.py` | database-builder | NEW additive migration, down_rev `c2d3e4f5a6b7` |
| `backend/tests/modules/pricing/test_settlement_formula.py` (+ rewrite siblings) | services + api-routes | golden + router tests |

**W2 does NOT touch:** `frontend/**` (W3), `backend/app/modules/export/**` (W4), `docs/V1_FEATURE_SPEC.md` / `docs/BACKEND_ARCHITECTURE.md` (W5 — LOCKED, founder-gated), `meesho_pricing_lookup.json` / `pricing_lookup.py` / `build_pricing_lookup.py` (W1 — READ ONLY).

---

## 6. Dependencies & sequencing

- **Hard barrier:** branch off develop ONLY after #301 (W1) merges. W2 imports `pricing_lookup` and reads `meesho_pricing_lookup.json`.
- **W3 (FE)** binds to §2.2 response contract — frozen here. **W4 (export)** binds to W2 only for `selling_price` provenance (it reads `products.attributes`, not the response).
- **i18n follow-up (non-blocking):** `pricing.alert.negative_settlement` message key + (optional) `pricing.disclaimer` key → flag to i18n owner. Existing `pricing.alert.negative_payout` is renamed; coordinate the key.
- **Cross-lead handoff (backend↔frontend):** memo `handoff_contract_price-calculator.md` to frontend lead with the §2.2 contract once W2 merges to integration — the `extra="forbid"` request rename (`meesho_price`→`selling_price`, drop `input_cost`) is a breaking change FE must ship in lockstep, else 422.
