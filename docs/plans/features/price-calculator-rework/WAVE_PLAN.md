# Price Calculator Rework — WAVE PLAN

| Field | Value |
|---|---|
| Section | section-7 (canonical slug: `price-calculator`) — V1 Feature 7 |
| Tier-1 author | `meesell-section-coordinator` (this doc) — session `mesell-section-7-coordinator-session-1` |
| Status | SIGNED-OFF DECISIONS BAKED IN (2026-06-19) — all decision gates G-EXPORT/Q1, G-NETPROFIT, G-DOC, Q2, Q3, Q4 RESOLVED by the Director (see §5). Awaiting final Tier-0 check-in-gate "go" before any child dispatch. |
| Integration branch | `feature/section-7/integration` (off develop, F3 protection) |
| Group branches | `feature/section-7/frontend`, `feature/section-7/backend` (off integration) |
| Supersedes | merged PR #285 (backend wrong model) + open/gate-stopped PR #287 (FE wrong model) |
| Source of truth (math) | `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (confirmed 3,772/3,772 + real bank payout ₹61.78) |

---

## 0. Why this rework exists (the model correction)

> **AUTHORITATIVE SOURCE — ALL BUILDERS READ THIS, NOT THE STALE HANDOFF.** The ONLY math/model source of truth is `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (the getTransferPrice census model). The file `.claude/agent-memory/meesell-data-engineer/handoff_pricing_transfer_price.md` (round-4: `fetch-supplier-products` / "₹9 flat fee") is **SUPERSEDED and STALE** — do NOT follow it. The wrong live code calibrated to the retracted "₹106→₹47" misread that this rework REPLACES: `backend/app/modules/pricing/service.py` + `backend/app/shared/models/pricing_calc.py`. The stale data stubs to RETIRE: `backend/app/data/category_commissions.json` + `backend/app/data/meesho_shipping_slabs.json`.


The merged #285 backend and the #287 frontend implement a **catastrophically wrong** settlement model:
- They DEDUCT FULL shipping (~₹30–₹70 + brackets) from the seller. **WRONG** — the seller bears ONLY the 18% GST on shipping; the shipping itself is buyer-paid pass-through (real-order proof: SKU TTC-BL-OR-HP-NG-P4 → ₹61.78, matched the bank payout to the paise).
- They use a 4% commission default and fabricate logistics_fee / fixed_fee / TCS / RTO-loss terms. **WRONG** — commission = 0% across all 3,772 categories (an optional override param, not 4%); there are no logistics/fixed fees in the settlement; TCS = 0.
- They calibrate to a misread "₹106 → ₹47" sample (the round-3 misread, already retracted in the data handoff round-4 + round-13).

### THE CONFIRMED MODEL (the ONLY math this rework ships)
```
total_price     = price + shipping
gst_on_shipping = 0.18 × shipping            # API field name = gst_price
tds             = 0.001 × total_price
tcs             = 0
commission_fees = commission_pct × price     # commission_pct default 0, optional override
transfer_price  = price − commission_fees − gst_on_shipping − tds − tcs   # "Estimated Bank Settlement"
```
- `shipping` is a PER-CATEGORY CONSTANT looked up by `meesho_leaf_id` (= census `sscat_id`; price- AND weight-independent; founder-verified in portal + real order). NO live Meesho calls — runs fully offline from a shipped lookup file.
- **NET-PROFIT LAYER DEFERRED TO V1.5 (RESOLVED — G-NETPROFIT).** V1 ships ONLY the Meesho settlement breakdown — NO output-GST and NO landed-cost inputs/outputs anywhere (request, response, domain, model, UI). The optional `net_profit = transfer_price − output_GST_liability − landed_cost` layer is explicitly out of V1 scope.
- Disclaimer text (MUST appear near the result): *"Bank settlement amount may vary slightly based on the quantity in the order, Meesho commission policy at the time of the order and the actual weight of the product as calculated by our third party delivery partner."*

### Golden anchors every wave's tests must reproduce
1. **Real-order:** price 70, shipping 45 → 70 − (0.18×45=8.10) − (0.001×115=0.12 → ₹0.12) − 0 = **₹61.78** (TDS on total 115 = 0.115 → rounds to 0.12; settlement 70 − 8.10 − 0.12 = 61.78). ✓ to the paise.
2. **Census sanity:** sscat_id 10949 @ price 100 → shipping 82, gst_price 14.76, tds 0.18, transfer_price **85.06**.
3. **Census-wide:** the engine, fed each `lookup[sscat_id].shipping_charges` at price 100, reproduces `transfer_price_at_100` for a sampled set (all rows have `formula_ok=true`).

---

## 1. Current-state file inventory (what each wave reworks)

**Backend (modular monolith, the live path — NOT the extracted `backend/services/svc-pricing` which is dormant):**
- `backend/app/modules/pricing/schemas.py` — wrong: `target_margin`-era fields, full deduction stack, TCS, logistics/fixed fees.
- `backend/app/modules/pricing/service.py` — wrong: `_estimate_payout` deducts full shipping + fabricated fees, calibrated to ₹106→₹47.
- `backend/app/modules/pricing/domain.py` — wrong dataclasses (`PnLBreakdown` with logistics_fee/fixed_fee/rto_expected_loss).
- `backend/app/modules/pricing/router.py` — endpoint shape OK (POST `/api/v1/products/{id}/price-calc`), feature-flag + ownership gate KEEP; response model swaps.
- `backend/app/modules/pricing/repository.py` — `insert_calc(...)` signature must change with the new column set.
- `backend/app/shared/models/pricing_calc.py` — has many wrong nullable columns (logistics_fee, fixed_fee, rto_expected_loss, etc.).
- `backend/app/data/` — NO pricing lookup file exists yet. RETIRE the stale stubs `category_commissions.json` (commission-based) AND `meesho_shipping_slabs.json` (slab/weight-based — contradicts the per-category-constant model) — both belong to the retracted wrong model. Retirement happens in W2 alongside the engine rewrite (the engine stops reading them; the files are deleted in the same squash).
- Census source: `logs/scraper/transfer_price_census_summary.json` → `lookup` (3,772 entries).
- Refresh script: `backend/scripts/meesho_transfer_price_census.py` (standalone today); monthly scrape entry = `backend/scripts/meesho_scrape_trigger.sh` + `meesho_batch_scraper.py`.

**Frontend (`frontend/apps/mfe-pricing`, federation remote `mfe-pricing` @ :4201):**
- `src/app/pricing.model.ts` — STALEST of all: still pre-#285 mock (`target_margin_pct`, `seller_price`, `commission_amount`, MRP-as-output, alert codes `HIGH_MRP_MULTIPLIER`/`THIN_PROFIT`). Total rewrite.
- `src/app/pricing.service.ts` (113 lines), `src/app/pricing.component.ts` (708 lines), `src/app/pricing.utils.ts`, `*.spec.ts` — rework to the confirmed breakdown.

**Docs (LOCKED — founder-gated edits):**
- `docs/V1_FEATURE_SPEC.md` §Feature 7 (lines 274–324) — amended for #285 wrong model.
- `docs/BACKEND_ARCHITECTURE.md` §2.6 `pricing` (lines 427–452) + the §12.M amendment references — written for wrong model.

**Export (Feature 9, `backend/app/modules/export`):** currently does NOT consume any pricing field (grep-confirmed: no price/payout wiring in export domain/service/schemas). The seller's listing **price** lives in `products.attributes` JSONB via the schema-driven catalog form, NOT a dedicated column. RESOLVED (G-EXPORT/Q1): export feeds the calculator's SELLING PRICE into the Meesho template's native **MRP / Meesho Price** column — see W4.

**Category → sscat_id mapping (RESOLVED — Q2):** `categories.meesho_leaf_id` **IS** the census `sscat_id` — 100% overlap verified (3,772/3,772). The engine joins directly on `meesho_leaf_id`; **NO category-mapping unit is needed** in W1 or W2.

---

## 2. Wave overview + critical path

| Wave | Goal | Owner specialist(s) | Coordinator gate | Branch | Type | Depends on |
|---|---|---|---|---|---|---|
| **W1** | Productionize the census `lookup` → shipped versioned data file + loader | `meesell-data-engineer` (build) → `meesell-database-builder` (loader code, if needed) | `meesell-data-engineer` self-review + `meesell-backend-coordinator` | backend | code+data | — (root) |
| **W2** | Rework pricing engine + schemas + domain + repository + model to confirmed formula | `meesell-services-builder` (engine+domain), `meesell-api-routes-builder` (schemas+router+repo), `meesell-database-builder` (model+migration) | `meesell-backend-coordinator` | backend | code | **W1 (hard barrier)** |
| **W3** | Rework FE price calculator UI to confirmed breakdown + disclaimer | `meesell-angular-service-builder` (model+service), `meesell-angular-component-builder` (component), `meesell-angular-ui-styler` (layout/disclaimer) | `meesell-frontend-coordinator` | frontend | code | **W2 (hard barrier — binds to BE contract)** |
| **W4** | Feed calculator SELLING PRICE into export template's native MRP / Meesho Price column(s) (settlement/net-profit NOT exported) | `meesell-data-engineer` (confirm canonical/`meesho_column_header`) + `meesell-services-builder` (export consume) | `meesell-backend-coordinator` | backend | code | **W2 (hard barrier)** |
| **W5** | Reconcile LOCKED docs (V1_FEATURE_SPEC §F7 + BACKEND_ARCH §12.M) to confirmed model | `meesell-backend-coordinator` (direct, fast-mode docs) | FOUNDER PR review (LOCKED-doc edit) | backend (docs) | docs | W2 frozen contract (overlap-OK after W2 contract is fixed) |
| **W6** | Fold pricing-lookup refresh into the EXISTING MONTHLY category scrape | `meesell-scraper-maintainer` (build) + `meesell-data-engineer` (census + emit) | `meesell-data-engineer` + `meesell-backend-coordinator` | backend | code+ops | **W1 (data-file contract)**; overlap with W3/W4 |

**Critical path:** `W1 → W2 → W3` (FE binds to the BE contract). W4 also blocks on W2. W5 + W6 are off the critical path.

**Parallelism:**
- W1 is the single root. Nothing else starts until W1's data-file format is fixed (hard barrier — W2 and W6 both bind to it).
- After W2 merges to `…/integration` (hard barrier): **W3, W4, W5, W6 may all run in parallel** (different file owners; see §3 ownership map — zero overlap).
- W6 only needs W1's data-file path/format contract (not W2's engine), so W6 *could* overlap W2 — but to keep the dispatch simple and avoid the section-coordinator juggling two open BE sub-sessions, W6 is sequenced into the post-W2 parallel fan-out. (Director may approve W6//W2 overlap if schedule pressure warrants — it is a soft dependency.)

---

## 3. File ownership map (no two parallel waves touch the same file)

| File | Owning wave | Notes |
|---|---|---|
| `backend/app/data/meesho_pricing_lookup.json` (NEW) | W1 (create), W6 (refresh-overwrite) | versioned: top-level `{version, generated_at, census_price:100, lookup:{...}}`. W1 creates; W6 is the ONLY other writer (monthly refresh) — they never run concurrently. |
| `backend/app/data/__init__.py` (loader registration, if pattern requires) | W1 | additive only. |
| `backend/app/modules/pricing/pricing_lookup.py` (NEW loader, if not via service) | W1 | OR W1 adds a `_load_lookup()` into service.py — decide in W1 SPEC. Prefer a dedicated small loader module to keep service.py clean. |
| `backend/app/modules/pricing/service.py` | W2 | full rewrite of `_estimate_payout` → confirmed formula; reads shipping from W1 lookup by `sscat_id`. |
| `backend/app/modules/pricing/domain.py` | W2 | new `SettlementBreakdown` dataclass (price, shipping, total_price, gst_on_shipping, tds, tcs, commission_pct, commission_fees, transfer_price). Drop logistics/fixed/rto. NO net_profit/output_gst/landed_cost (V1.5). |
| `backend/app/modules/pricing/schemas.py` | W2 | request: `price`, `sscat_id`, optional `commission_pct` (default 0). response: the confirmed settlement breakdown + `disclaimer_message_id` + `calculated_at`. NO output_gst/landed_cost (V1.5). |
| `backend/app/modules/pricing/router.py` | W2 | keep endpoint path + flag + ownership gate; swap response_model; drop the commission-missing 422 note. |
| `backend/app/modules/pricing/repository.py` | W2 | `insert_calc(...)` new column set. |
| `backend/app/shared/models/pricing_calc.py` | W2 (model) | add the confirmed columns; KEEP-NULLABLE the wrong #285 fields and stop writing them (Q3 RESOLVED — do NOT drop). |
| `backend/alembic/versions/<new>_pricing_confirmed_model.py` (NEW) | W2 (database-builder) | add `shipping`, `gst_on_shipping`, `tds`, `commission_fees`, `transfer_price`, `sscat_id` snapshot. KEEP-NULLABLE the wrong #285 columns (Q3 — do NOT drop; stop writing them). NO output_gst/landed_cost/net_profit columns (V1.5). |
| `backend/app/data/category_commissions.json` + `backend/app/data/meesho_shipping_slabs.json` (DELETE) | W2 | RETIRE both stale wrong-model stubs in the W2 squash; engine no longer reads them. |
| `backend/tests/modules/pricing/*` | W2 | rewrite `test_pnl_formula.py`→`test_settlement_formula.py`, `test_estimator_calibration.py`→golden ₹61.78 + census; rework `test_alerts.py`. |
| `frontend/apps/mfe-pricing/src/app/pricing.model.ts` | W3 | total rewrite to confirmed contract. |
| `frontend/apps/mfe-pricing/src/app/pricing.service.ts` | W3 | new request/response shape; carries `sscat_id`. |
| `frontend/apps/mfe-pricing/src/app/pricing.component.ts` | W3 | breakdown rows: Selling price / Commission fee (x%, default 0) / GST (0.18×shipping) / TDS / Estimated Bank Settlement + disclaimer text. NO net-profit/output-GST/landed-cost panel (V1.5). |
| `frontend/apps/mfe-pricing/src/app/pricing.utils.ts` + `*.spec.ts` | W3 | formatters + tests. |
| `backend/app/modules/export/service.py` (+ schemas/domain) | W4 | write the calculator SELLING PRICE (`products.attributes` JSONB) into the template's native MRP / Meesho Price column(s). Bank settlement / net profit are NOT exported (on-screen seller-facing only). |
| `backend/app/data/` template-fields source (`template_fields`) | W4 (read-only confirm) | `meesell-data-engineer` confirms the exact canonical + `meesho_column_header` for the MRP / Meesho Price field(s) before export writes. |
| `docs/V1_FEATURE_SPEC.md` §F7 | W5 | LOCKED — founder approval. |
| `docs/BACKEND_ARCHITECTURE.md` §2.6 + §12.M | W5 | LOCKED — founder approval. |
| `backend/scripts/meesho_scrape_trigger.sh` + `meesho_batch_scraper.py` (or a new `meesho_monthly_refresh.py` orchestrator) | W6 | fold the getTransferPrice census into the monthly run; emit the W1 data-file. |
| `backend/scripts/meesho_transfer_price_census.py` | W6 | refactor to be callable from the monthly orchestrator + emit `backend/app/data/meesho_pricing_lookup.json` directly. |

No file appears under two waves that run in parallel. `meesho_pricing_lookup.json` is written by W1 (once) and W6 (monthly) — never concurrently.

---

## 4. Per-wave detail

### WAVE 1 — Productionize the census lookup (DATA LAYER) — ROOT
**Goal:** ship the 3,772-entry `sscat_id → {commission_percentage, shipping_charges}` map as a versioned backend data file + a load path the pricing engine reads. The lookup key (`sscat_id`) is joined from `categories.meesho_leaf_id` (Q2 RESOLVED — 100% overlap; NO mapping unit).

**Hybrid dispatch (code+data):**
1. SPEC — `meesell-data-engineer` produces the task SPEC: exact file path `backend/app/data/meesho_pricing_lookup.json`, schema `{version:"2026-06-19", generated_at, census_price:100, lookup:{ "<sscat_id>": {commission_percentage, shipping_charges, transfer_price_at_100, leaf_name, path_str} }}`, the loader contract (dedicated `pricing_lookup.py` with `get_shipping(sscat_id) -> int` + `get_commission_default(sscat_id) -> Decimal` + raises a typed `UnknownCategoryError` on miss), and the source-of-truth derivation from `logs/scraper/transfer_price_census_summary.json`.
2. BUILD — `meesell-data-engineer` generates the data file from the census summary; `meesell-database-builder` (or services-builder, decided in SPEC) writes the loader module if it touches `app/` code.
3. MERGE-GATE — `meesell-data-engineer` reviews the file (3,772 rows, all `formula_ok`), `meesell-backend-coordinator` reviews the loader code → squash to `feature/section-7/backend`.

**Acceptance / tests:**
- File has exactly 3,772 entries; every entry has integer `shipping_charges` and `commission_percentage:0.0`.
- Loader unit test: `get_shipping(10949) == 82`; `get_shipping(<unknown>)` raises `UnknownCategoryError`.
- Spot-check 3 entries against the census summary verbatim.
- File is committed (not gitignored) — it is shipped production data.

**Barrier:** HARD. W2 and W6 both bind to this file's path + schema. Nothing downstream starts until W1 is merged to `…/integration`.

**Category key (RESOLVED — Q2):** lookup is keyed by `sscat_id` = `categories.meesho_leaf_id` (100% overlap, 3,772/3,772 verified). The engine joins the product's category directly on `meesho_leaf_id`. **NO mapping-unit contingency** — removed from W1 scope.

---

### WAVE 2 — Rework the pricing engine (BACKEND) — critical path
**Goal:** replace the entire #285 wrong engine with the confirmed formula; engine reads shipping from the W1 lookup. **All builders follow the census model** (`.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md`), NOT the SUPERSEDED stale handoff (`handoff_pricing_transfer_price.md`). Wrong code being replaced: `service.py` + `pricing_calc.py` (calibrated to the retracted "106→47" misread). RETIRE the stale stubs `category_commissions.json` + `meesho_shipping_slabs.json` in this squash.

**Hybrid dispatch (code-heavy, multi-specialist — coordinator sequences within the BE Tier-2 sub-session):**
1. SPEC — `meesell-backend-coordinator` produces ONE consolidated SPEC covering: the confirmed formula (verbatim from §0), the new request/response contract, the domain dataclass, the repository signature, the model+migration column changes, and the test set. The SPEC freezes the FE-facing contract (W3 binds to it).
2. BUILD (parallel within the BE sub-session, but single squash):
   - `meesell-services-builder` → `service.py` (`_compute_settlement`), `domain.py` (`SettlementBreakdown`). Engine signature: `compute(price, sscat_id, commission_pct=0)`. NO output_gst_pct / landed_cost params (V1.5).
   - `meesell-api-routes-builder` → `schemas.py` (request/response), `router.py` (swap response_model, drop 422 commission-missing), `repository.py` (`insert_calc`).
   - `meesell-database-builder` → `pricing_calc.py` model + new Alembic migration.
3. MERGE-GATE — `meesell-backend-coordinator` runs the §2.1 squash review → `feature/section-7/backend`.

**Confirmed request/response contract (the contract W3 binds to):**
- Request: `{ price: Decimal>0, sscat_id: int, commission_pct?: Decimal (default 0) }`. NOTE: `input_cost`/`target_margin`/all `override_*` fields are REMOVED. NO output_gst_pct / landed_cost (V1.5).
- Response: `{ price, shipping, total_price, gst_on_shipping (field `gst_price`), tds, tcs, commission_pct, commission_fees, transfer_price (="Estimated Bank Settlement"), disclaimer_message_id, calculated_at }`. All money = Decimal-as-string (R-W6-6). NO output_gst_liability / landed_cost / net_profit (V1.5).

**Acceptance / tests (the golden gate):**
- **ROUNDING (RESOLVED — Q4):** all money uses `Decimal` with `ROUND_HALF_UP` to 2 decimal places. Each term (gst_on_shipping, tds, commission_fees) is rounded to 2dp, THEN subtracted. Builders MUST match the census / real-order to the paise. Pinned golden anchor: SKU **TTC-BL-OR-HP-NG-P4** @ price 70, shipping 45 → settlement **₹61.78**; plus the census `transfer_price_at_100` values.
- `test_settlement_formula.py::test_real_order` — SKU TTC-BL-OR-HP-NG-P4, price 70, shipping 45 → transfer_price **61.78** (exact; TDS 0.115 → 0.12 via ROUND_HALF_UP).
- `test_settlement_formula.py::test_census_sanity` — sscat_id 10949 @ price 100 → 85.06; gst_on_shipping 14.76; tds 0.18.
- `test_settlement_formula.py::test_census_wide` — for a sampled N≥50 `sscat_id`, engine(price=100, shipping=lookup) reproduces `transfer_price_at_100` within ₹0.01 (to the paise).
- `test_settlement_formula.py::test_commission_override` — commission_pct=2 deducts `0.02×price`.
- Negative transfer_price returns 200 (alert), not 400. Ownership gate (404) + feature-flag (404) tests preserved.
- TCS == 0 always; no logistics/fixed/rto terms exist anywhere (grep gate). NO net_profit/output_gst/landed_cost anywhere (grep gate — deferred to V1.5).

**Barrier:** HARD before W3 (FE binds to the contract) and W4 (export consumes the output).

**Risk:** Decimal rounding order must match Meesho (TDS on `total_price`, ROUND_HALF_UP each term to 2dp then subtract) — golden tests enforce to the paise. (Q2 sscat_id resolution is RESOLVED — direct join on `categories.meesho_leaf_id`.)

---

### WAVE 3 — Rework the FE price calculator (FRONTEND) — critical path tail
**Goal:** rebuild the calculator UI to the confirmed breakdown + disclaimer; kill the stale pre-#285 contract entirely.

**Hybrid dispatch (code-heavy, frontend Tier-2 sub-session):**
1. SPEC — `meesell-frontend-coordinator` SPEC: the W2-frozen wire contract → `pricing.model.ts` DTOs; service `calc(productId, {price, sscat_id, commission_pct?})`; component breakdown rows + disclaimer. NO net-profit/output-GST/landed-cost panel (V1.5).
2. BUILD: `meesell-angular-service-builder` (model + service), `meesell-angular-component-builder` (component logic), `meesell-angular-ui-styler` (breakdown table layout + disclaimer styling).
3. MERGE-GATE — `meesell-frontend-coordinator` §2.1 squash → `feature/section-7/frontend`.

**Breakdown UI (exact rows — V1 final):** Selling price · Commission fee (x%, default 0) · GST (0.18×shipping) · TDS (0.001×total) · **Estimated Bank Settlement** (emphasized). Disclaimer text rendered near the result verbatim from §0. NO net-profit / output-GST / landed-cost panel (deferred to V1.5).

**Acceptance / tests:**
- `pricing.service.spec.ts` — posts the new body; parses `transfer_price` via `Number()`; maps the typed error shapes.
- `pricing.component.spec.ts` — renders all 5 core rows + disclaimer; "Estimated Bank Settlement" label present; negative-settlement alert renders red.
- ZERO references to `target_margin_pct`/`seller_price`/`commission_amount`/`HIGH_MRP_MULTIPLIER`/`THIN_PROFIT` remain (grep gate).
- Builds clean; `mfe-pricing` remote rebuilds (post-merge the master/localhost session rebuilds :4201 per the federation rebuild workflow).

**Barrier:** binds to W2 (HARD). Can run in parallel with W4/W5/W6.

---

### WAVE 4 — Export wiring (BACKEND)
**Goal (RESOLVED — G-EXPORT/Q1):** feed the calculator's **SELLING PRICE** into the Meesho export template's native **MRP / Meesho Price** column(s). The buyer-facing selling/listing price IS what the template's MRP / Meesho Price columns expect. **Bank settlement and net profit are NOT exported** — they are seller-facing on-screen only (the calculator), never an export column. No fabricated payout in the XLSX.

**First task (data confirmation):** `meesell-data-engineer` confirms the EXACT canonical + `meesho_column_header` for the price field(s) — MRP and Meesho Price — from `template_fields`. Then export writes the selling price (which lives in `products.attributes` JSONB) into that column.

**Hybrid dispatch (code):**
1. CONFIRM — `meesell-data-engineer` resolves the canonical/`meesho_column_header` for MRP + Meesho Price from `template_fields`.
2. SPEC — `meesell-backend-coordinator` SPEC: read selling price from `products.attributes`, map it into the confirmed MRP / Meesho Price column(s) in the export row.
3. BUILD — `meesell-services-builder` (export.service consume).
4. MERGE-GATE — `meesell-backend-coordinator` §2.1 squash → `feature/section-7/backend`.

**Acceptance / tests:** export round-trip test writes the selling price into the correct MRP / Meesho Price column(s); NO bank-settlement / net-profit / fabricated-payout value appears in the XLSX.

**Barrier:** binds to W2. Backend-only (no FE). Parallel with W3/W5/W6.

---

### WAVE 5 — Spec reconciliation (DOCS — FOUNDER-GATED) — APPROVED (G-DOC)
**Goal (G-DOC APPROVED):** rewrite `docs/V1_FEATURE_SPEC.md` §Feature 7 and `docs/BACKEND_ARCHITECTURE.md` §12.M to the confirmed model. Founder reviews the diff in the PR before merge.

**Dispatch (docs fast-mode):** `meesell-backend-coordinator` executes directly (no specialist ceremony per founder rule 7).

**Content of the rewrite:**
- V1_FEATURE_SPEC §F7: replace the #285 amendment with the confirmed formula; inputs = price + sscat_id + optional commission_pct (default 0); output = Selling price / Commission fee / GST (0.18×shipping) / TDS (0.001×total) / Estimated Bank Settlement + disclaimer; remove logistics/fixed/TCS/RTO/4%-commission language; remove the "₹106→₹47 calibration" claim; cite the census + real-order proof. State the net-profit (output-GST + landed-cost) layer is DEFERRED to V1.5.
- BACKEND_ARCH §2.6 `pricing`: shipping is a per-category constant from the shipped lookup (W1 file), commission is an optional override (default 0), the engine reads the data file (not `category.service`), zero Meesho calls in prod.

**FOUNDER-DECISION GATE:** these are LOCKED docs. The section-coordinator does NOT mark them auto-approved. W5's output is a docs PR/diff handed to the founder for explicit approval. (The section-coordinator never amends a LOCKED doc on its own authority — escalate per `SUB_SESSION_PROTOCOL §5.0`.)

**Sequencing:** may overlap W3/W4 once the W2 contract is frozen (W5 documents W2's contract).

---

### WAVE 6 — Refresh integration into the MONTHLY scrape
**Goal:** fold the per-category pricing-lookup refresh into the EXISTING monthly category-scrape job — one run refreshes categories AND re-runs the getTransferPrice census, emitting an updated `meesho_pricing_lookup.json` into `backend/app/data/`.

**Hybrid dispatch (code+ops):**
1. SPEC — `meesell-data-engineer` + `meesell-scraper-maintainer` joint SPEC: how the monthly orchestrator (`meesho_scrape_trigger.sh` / `meesho_batch_scraper.py`) invokes the census; the getTransferPrice contract (read-only compute, password-login only, reuse warm session `meesho_storage_state.json`, ~1 call/2.5s, hard-stop on 401/403/429/463 per the census script header); and the emit path → `backend/app/data/meesho_pricing_lookup.json` (the W1 file).
2. BUILD — `meesell-scraper-maintainer` (orchestrator wiring) + `meesell-data-engineer` (census refactor to emit the W1 file directly).
3. MERGE-GATE — `meesell-data-engineer` reviews the census/emit, `meesell-backend-coordinator` reviews the orchestrator → squash to `feature/section-7/backend`.

**Acceptance / tests:**
- Dry-run (no live Meesho call) test: the orchestrator step that builds the lookup from a fixture census JSONL emits a valid W1-format file (3,772 rows, schema-valid).
- The monthly job is a SINGLE schedule (NO separate pricing-refresh cron — founder ruling).
- Documented hard-stop + pacing safety; NO go-live / submit / listing calls; compute-API only.
- The refreshed file lands in `backend/app/data/` and the running backend picks it up on next deploy/restart (document the reload semantics — file is read at process start).

**Barrier:** binds to W1 (data-file contract). Parallel with W3/W4/W5. Soft-dependency on W2 only (does not import the engine).

**Risk:** Meesho session/auth (SMS-OTP cold-login gating noted in the data handoff). This is a no-spend, no-secrets, dev-only refresh; the actual live monthly run is operated by the data/scraper owners with a warm session — NOT executed by this rework. W6 ships the *wiring*, not a live scrape run.

---

## 5. Decision gates — ALL RESOLVED (Director, 2026-06-19)

| Gate | Wave | Resolution |
|---|---|---|
| **G-DOC** | W5 | **APPROVED.** Keep W5; rewrite V1_FEATURE_SPEC §F7 + BACKEND_ARCH §12.M to the confirmed model. Founder reviews the diff in the PR before merge. |
| **G-EXPORT (Q1)** | W4 | **RESOLVED.** Export feeds the calculator's SELLING PRICE into the template's native MRP / Meesho Price column(s). Bank settlement + net profit are NOT exported (on-screen seller-facing only). data-engineer confirms the canonical/`meesho_column_header` from `template_fields` first; selling price lives in `products.attributes` JSONB. |
| **G-NETPROFIT** | — | **RESOLVED — DEFERRED TO V1.5.** Net-profit layer (output GST + landed cost) removed from V1 scope entirely. V1 shows only the Meesho settlement breakdown + disclaimer. |
| **Q2** | W1/W2 | **RESOLVED.** `categories.meesho_leaf_id` IS the census `sscat_id` (100% overlap, 3,772/3,772). Engine joins directly on `meesho_leaf_id`. NO mapping unit. |
| **Q3** | W2 | **RESOLVED — KEEP-NULLABLE.** Keep the wrong #285 columns nullable in `pricing_calcs` and stop writing them (safest; #285 is on develop, not prod). Additive migration adds the confirmed columns. |
| **Q4** | W2 | **RESOLVED.** Decimal, ROUND_HALF_UP to 2dp; builders match the census/real-order to the paise. Golden pins SKU TTC-BL-OR-HP-NG-P4 @ price 70, shipping 45 → ₹61.78, and the census `transfer_price_at_100` values. |
| **G-CHECKIN** | all | The wave plan itself — Tier-0 check-in-gate "go" before ANY dispatch (only remaining gate). |

## 6. Open questions

ALL prior open questions (Q1–Q4) are RESOLVED — see §5. No open questions remain. Only the Tier-0 check-in-gate "go" is outstanding before dispatch.

## 7. Standing constraints honored
- Dev-only, no-spend, no-secrets. W6 ships wiring only — no live Meesho scrape executed by this rework.
- Only `meesell-*` agents. Founder merges all `…/integration → develop` PRs (section-coordinator opens, never merges).
- Section-coordinator dispatches ONLY the two Tier-2 coordinators (`meesell-frontend-coordinator`, `meesell-backend-coordinator`); they own their specialists.
