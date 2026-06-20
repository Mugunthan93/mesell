# WAVE 4 — Export Wiring BUILD SPEC (Price Calculator Rework)

**Status:** SPEC ONLY — no build, no dispatch in this run.
**Owner (merge gate):** `meesell-backend-coordinator`
**Author:** backend lead, 2026-06-19
**Founder gate G-EXPORT/Q1:** RESOLVED (WAVE_PLAN §5) — export feeds the calculator's
**SELLING PRICE** into the Meesho template's native price column(s). Bank settlement and
net profit are **NOT** exported (seller-facing on-screen only).
**Barrier:** blocks on **W2** (hard). May run in parallel with W3/W5/W6 once W2 freezes.

---

## 0. TL;DR (the load-bearing finding)

The Meesho export **already emits any canonical present in `products.fields_jsonb`** into its
template column under that field's `meesho_column_header` — *including* the price fields
(`meesho_price`, `mrp`). **The export needs no change to carry the selling price.**

The real gap is **upstream**: the price calculator persists the chosen price ONLY to the
`pricing_calcs` audit table — it does **NOT** write back to `products.fields_jsonb`. So unless
the seller *also* typed the price into the catalog/wizard form, the calculator's chosen price
never reaches the export.

→ **W4 is therefore: (a) a verification + golden-roundtrip test (export already works), plus
(b) ONE founder-gated convenience action — "apply calculated price to product" — that writes
the chosen selling price into `products.fields_jsonb` so it flows to export.**

---

## 1. Investigation findings (evidence)

### 1.1 Exact Meesho price field(s) — canonical + `meesho_column_header`

Meesho's create-flow `fetchProductDetailsV3.product_size_data` (per-variation columns;
data-engineer MEMORY L340, triple-confirmed) carries exactly these price fields:

| Meesho display name | Canonical (`canonical_name`) | Required | Notes |
|---|---|---|---|
| **Meesho Price** | `meesho_price` | mandatory (min 2 / max 10000) | the listed/selling price |
| **MRP** | `mrp` (a.k.a. `product_mrp`) | mandatory (max 30000) | strike-through MRP |
| Wrong/Defective Returns Price | `only_wrong_return_price` | optional | not a calculator output in V1 |

**The exact XLSX `meesho_column_header` string is DB/seed-sourced**, NOT hardcoded — it lives
in `templates.schema_jsonb.fields[*].meesho_column_header` and the export reads it verbatim
(`export/service.py` L519–540, D7; typo-preserved per `MVP_ARCH §3`). The only header string
pinned in-repo today is the test fixture `mrp → "MRP (Rs)"` (`test_database.py` L598).

> **W4 FIRST TASK (data confirmation, `meesell-data-engineer`, read-only):** resolve the
> live `meesho_column_header` string(s) for `meesho_price` and `mrp` from `template_fields` /
> `templates.schema_jsonb` (DB may be down → fall back to the parsed template corpus
> `data/parsed/batch_*.json` or the create-flow schema dump). Pin the exact strings before the
> golden test asserts them. The i18n classifier confirms the field IS price-typed
> (`primitive_classifier.CURRENCY_PATTERNS` includes `"price"`, `"mrp"`;
> `step_assignment` rule `(price|mrp|...) → pricing`).

### 1.2 Where the selling price lives — and does it flow to export today?

- **Selling price storage:** `products.fields_jsonb` (the column the WAVE_PLAN calls
  `products.attributes` JSONB), flat dict keyed by canonical, e.g. `{"meesho_price": 106,
  "mrp": 120, ...}`. Set via the schema-driven catalog/wizard form
  (`catalog.service.update_fields_jsonb`). Verified `test_database.py` L652–680.
- **Export read path:** `export/service._build_row` → `_value_from_snapshot(canonical, snapshot)`
  (L489–505) reads `snapshot.fields` which is `dict(products.fields_jsonb)` built by
  `catalog.service.get_product_for_export` (L1201). **It iterates ALL schema fields** and emits
  each canonical's value under its `meesho_column_header`. So **if `meesho_price`/`mrp` are in
  the schema (they are) and present in `fields_jsonb`, the export ALREADY carries them.**
  → **Does the price flow to export today? YES — but ONLY if the seller typed it into the form.**
- **Calculator persistence (the gap):** `pricing.service.calculate` writes the chosen price to
  the **`pricing_calcs` audit table only** (`pricing_repo.insert_calc`, service L188–192) — it
  does **NOT** touch `products.fields_jsonb`. Export never reads `pricing_calcs`.
  → **The calculator's chosen price does NOT auto-reach the export.**

### 1.3 Relationship (confirmed)

The calculator *helps* the seller choose a selling price; the export carries that chosen price
under Meesho's native price column. Bank settlement / net profit are derived, on-screen,
seller-facing — and are **never** an export column (no fabricated payout in the XLSX).

---

## 2. W4 scope

**Verdict: minimal code + verification — NOT a pure no-op.** The export is correct as-is; the
missing link is persisting the calculator's chosen price into `products.fields_jsonb`.

### 2.A Verify-only portion (no code)
- The export emits `meesho_price` / `mrp` from `fields_jsonb` with no change. Locked by the
  golden roundtrip test (§4).

### 2.B Code portion — the "apply calculated price to product" action (FOUNDER-GATED, see §5)
A thin convenience seam so the seller's chosen price lands in `fields_jsonb` → export:

- **NEW service method** in pricing module — `apply_price_to_product(product_id, user_id,
  meesho_price, mrp, db)`: asserts ownership (`catalog.service.assert_product_ownership`), then
  calls `catalog.service.update_fields_jsonb` (the EXISTING write path, §2.D-allowed) to merge
  `{"meesho_price": ..., "mrp": ...}` into `products.fields_jsonb`. **Reuses the form's
  validation path** (enum/range checks) — no new write surface, no schema bypass.
- **NEW route** `POST /products/{id}/apply-price` (api-routes-builder) wrapping the service
  method; counts toward §17 endpoint inventory (29 mounted after merge — confirm count).
- **NO change to `export/`** (domain/service/schemas) — explicitly out of scope; export already
  works. If §5 gate returns "verify-only", drop §2.B entirely → W4 = §2.A + §4 only.

### Cross-module guard
`pricing → catalog.service.update_fields_jsonb` and `pricing → catalog.service.assert_product_ownership`
must already be ✓ in the `BACKEND_ARCHITECTURE.md §2.D` matrix (pricing reads catalog/products
today via `find_latest_by_product`'s JOIN). **If `update_fields_jsonb` is a new pricing→catalog
edge (✗→✓), STOP — founder architecture amendment required (§7.3).** Verify the matrix before build.

---

## 3. Specialist + file ownership (if §5 gate = "build")

| File | Specialist | Change |
|---|---|---|
| `backend/app/modules/pricing/service.py` | `meesell-services-builder` | NEW `apply_price_to_product()`; calls `catalog.service.update_fields_jsonb` |
| `backend/app/modules/pricing/router.py` | `meesell-api-routes-builder` | NEW `POST /products/{id}/apply-price` route + Pydantic request schema |
| `backend/app/modules/pricing/schemas.py` | `meesell-api-routes-builder` | `ApplyPriceRequest` (`meesho_price: Decimal`, `mrp: Decimal`) |
| `backend/tests/test_price_export_roundtrip_integration.py` | `meesell-backend-coordinator` (lead authors integration test) | §4 golden roundtrip |
| `template_fields` / `templates.schema_jsonb` | `meesell-data-engineer` (read-only) | confirm `meesho_column_header` strings (§1.1) |

**Dispatch order:** data-engineer confirm → services-builder → api-routes-builder → lead authors
golden test → merge-gate review.
**Export module is read-only this wave** — no `meesell-services-builder` change to `export/`.

---

## 4. Acceptance test (golden export roundtrip)

`backend/tests/test_price_export_roundtrip_integration.py`:

1. Seed a product in a category whose schema includes `meesho_price` + `mrp`.
2. **(if §2.B built)** `POST /products/{id}/apply-price {"meesho_price": 106, "mrp": 120}`
   → assert `products.fields_jsonb["meesho_price"] == 106` and `["mrp"] == 120`.
   **(verify-only path)** instead set the two fields via the existing form PATCH.
3. `POST /products/{id}/export-xlsx` → parse the emitted XLSX (reuse export test harness).
4. **ASSERT:** the cell under the confirmed `meesho_price` `meesho_column_header` == `"106"` and
   under the `mrp` header (`"MRP (Rs)"` or live string) == `"120"`.
5. **NEGATIVE ASSERT (the founder constraint):** NO column named/containing
   `settlement` / `payout` / `net_profit` / `transfer_price` / `commission` appears in the XLSX;
   no `pricing_calcs` value leaks into any cell.
6. Roundtrip parse-back (export's Step 7 `restore` path) preserves both price cells.

CI gates 1 (unit) + 3 (lint) green required; gate 4 (integration) carries this test (advisory
per repo-mgmt §2.1 but must be GREEN before merge for this wave given it is the core assertion).

---

## 5. OPEN founder/Director decision gate

**G-W4-APPLY:** Should the calculator **auto-save** (or one-click "apply") the chosen selling
price into `products.fields_jsonb`, or stay **verify-only** (seller re-types the price into the
catalog form, export already carries it)?

- **Option A — "apply" action (§2.B):** one-click "Use this price" on the calculator → writes
  `meesho_price`/`mrp` to the product → flows to export. Best UX; +1 endpoint; needs the §2.D
  matrix check.
- **Option B — verify-only:** ship §2.A + §4 only; document that the seller enters the price in
  the catalog form (where it already exports). Zero new surface; lowest risk.
- **NOT auto-save-on-calc:** even if Option A, do **not** silently mutate the product on every
  `calculate` call (the calculator is an exploration tool; the product should change only on an
  explicit seller action). This sub-ruling is recommended regardless.

**Recommendation:** Option A (explicit "apply" action), no silent auto-save — but HOLD build of
§2.B until the Director/founder confirms. Until then, W4 = §2.A verify + §4 golden test (always
safe to build).

---

## 6. Notes / risks

- `pricing/service.py` still reflects the WRONG #285 model (per the transfer-price memo); the
  rework is W2's job. **W4 does not depend on W2's formula** — it only persists the seller's
  CHOSEN `meesho_price`/`mrp` (raw inputs), not any derived settlement. Safe to spec
  independently; only the `apply_price_to_product` signature should land after W2 freezes the
  module's public surface to avoid a merge collision in `pricing/service.py`.
- DB-down caveat: header strings (§1.1) MUST be confirmed against live `template_fields` before
  the golden test asserts a literal — do not hardcode `"MRP (Rs)"` blindly (it is a test fixture,
  not a confirmed production header).
