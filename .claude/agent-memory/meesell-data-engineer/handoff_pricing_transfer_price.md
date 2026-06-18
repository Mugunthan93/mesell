# Handoff: Price Calculator — REAL per-product payout via `fetch-supplier-products`

**From:** data lead (meesell-data-engineer), session mesell-price-calculator-data-session-3
**To:** backend lead (meesell-backend-coordinator)
**Date:** 2026-06-18
**Topic:** ground-truth payout/commission source for the Price Calculator

## What changed (new fact)
Read-only scrape round 3 of the Curl Candy supplier account (supplier_id=3661229,
identifier=kdwec) found that the Meesho catalog LISTING page fires an authenticated XHR:

```
GET https://supplier.meesho.com/api/growth/activation/fetch-supplier-products  → 200
```

It returns, PER PRODUCT, the real price/payout model:
- `current_price`               — the buyer-facing listing (Meesho) price
- `current_transfer_price`      — the SELLER PAYOUT (price net of ALL Meesho deductions: commission + shipping/logistics + fees, blended)
- `current_wdrp_price`          — wrong/defective-return price (the lower price band)
- `current_wdrp_transfer_price` — payout under the WDRP band
- `minimum_recommendation_price`
- `minimum_wdrp_price`

Observed sample (one product): `current_price=106, current_transfer_price=47, minimum_recommendation_price=84, current_wdrp_price=86, current_wdrp_transfer_price=27, minimum_wdrp_price=72`.

Sibling XHR (smart-pricing tab): `GET /api/services/ipp/fetch-smart-pricing-products`.

This source is reachable WITHOUT the e-signature wall (`is_agreement_accepted` is still
false) — unlike the referral-fee rate-card and the per-order settlement page, both of
which remain e-sig-blocked.

## What this means for the pricing model
1. **Effective total deduction is derivable per product:** `current_price − current_transfer_price`
   (sample: 106 − 47 = 59 ≈ 56% blended). This is NOT a flat 4% — `transfer_price` already
   nets commission + shipping + logistics + fees together.
2. There is STILL no clean per-category commission %. `transfer_price` is a single blended
   net number and (consistent with the Wave-1.5 finding) varies per product and per date.
   Do NOT try to back out a static `commission_pct` from it.
3. **3-price structure is confirmed real:** MRP/listing (`current_price`) vs payout
   (`current_transfer_price`) vs wrong-defective band (`current_wdrp_*`). The current model's
   `meesho_price = mrp` assumption is wrong.

## What the backend lead should do (acceptance)
- Price Calculator for EXISTING products: use `current_transfer_price` as the ground-truth
  payout (and `current_price` as the listing price); show real net margin from the actual
  numbers rather than a derived MRP. Sourcing is a per-product authenticated fetch (the data
  layer can supply the captured field shape; a live integration is a backend/infra decision —
  Meesho has no public API, so this is scrape-sourced, not a stable contract).
- Price Calculator for NEW products (no transfer_price yet): keep the seller-input commission
  (default 4% account flat) + explicit deduction line-items (shipping ~₹70 bracketed at ₹1000,
  logistics fee, RTO-weighted loss, GST-on-fee 18%, TCS 1% / TDS) — same recommendation as the
  round-1 settlement handoff.
- Do NOT add a `commission_pct` migration to the categories table for this; commission stays
  NULL (founder-locked). The payout truth lives per-product, not per-category.

## Open follow-up (data side)
The edit-view DOM commission display and the create-flow live payout widget were NOT reached
this run (Akamai 403 hard-stop on the 2nd listing nav). A future PACED re-run of
`backend/scripts/meesho_catalog_commission_probe.py` (snapshot-regex now patched to capture the
full `fetch-supplier-products` body + reach phases 2-3) can return the FULL per-product table
(all ~15 catalogs, with category names) and confirm whether the create flow shows a live
"you'll receive ₹X" preview and via which endpoint. Not blocking the model decision above.

---

## ROUND-4 CORRECTION (2026-06-18, session mesell-price-calculator-data-session-4) — READ THIS, IT SUPERSEDES THE "56% BLENDED" FRAMING ABOVE

The round-3 single-point read (106→47 ≈ "56% blended deduction") was a **MISREAD**.
Round-4 captured the FULL `fetch-supplier-products` body for ALL 14 products (raw:
`logs/scraper/fetch_supplier_products_2026-06-18_17-52.json`, gitignored) and the payload
has MORE structure than round-3 parsed. The truth is a **FLAT-FEE** model, not a percentage.

### The real per-product payload structure
Each item under `data.items[]` has BOTH:
- `customer_price_details` = { current_price, current_wdrp_price, minimum_recommendation_price, minimum_wdrp_price } — the BUYER-facing prices
- `seller_price_details`   = { current_price, current_wdrp_price, minimum_recommendation_price, minimum_wdrp_price } — the SELLER's own set price (cost basis)
- top-level `current_price` (= customer current_price), `current_transfer_price` (= PAYOUT), `shipping_charges`, `current_wdrp_*`, `catalog_id`, `product_id`, `category_id`, `sku_id`, `name`, `variations`.

### The proven arithmetic (EXACT across all 14 products)
- `customer_price = seller_price + shipping_charges`   (56+50=106, 70+50=120, 81+54=135, …)
- `payout (current_transfer_price) = seller_price − ₹9`  (₹9 FLAT on every product: seller-price range 43→86, BOTH categories 753948 & 754435, AND on the WDRP band: seller_wdrp − 9 = payout_wdrp)

### What this means (corrects points 1 above)
1. There is **NO percentage commission** for this seller's range. The "deduction %" looked
   variable (43–63% of customer_price, 10.5–20.9% of seller_price) ONLY because a CONSTANT ₹9
   fee is a bigger fraction of a smaller price. Do not model a flat-% off MRP — it is wrong.
2. **Shipping is buyer-paid pass-through, neutral to the seller.** The ₹50–54 inflates
   customer_price but the seller neither receives it nor is deducted for it (Meesho collects it
   from the buyer to pay the courier). Dividing the customer↔payout gap by customer_price
   double-counts shipping and massively overstates the "deduction" — that is the round-3 error.
3. **Model shape for the estimator:** `payout = seller_price − flat_fee(category, price_slab)`,
   where flat_fee ≈ ₹9 for this low-price hair-accessory band. Shipping is shown to the buyer
   but excluded from the seller's payout math. Only 2 low-price categories were sampled, so the
   flat fee MAY vary by category/price-slab at scale — but it is a small FLAT FEE, not a %.
4. `seller_price_details` and `customer_price_details` are DISTINCT objects — do not assume
   meesho_price == seller_price; the difference is exactly shipping_charges.

### Acceptance (updated)
- EXISTING products: payout = `current_transfer_price` (ground truth) — unchanged from round 3.
- NEW products: model `payout = seller_input_price − flat_fee` (default the flat fee small,
  category-hinted; NOT a 4% slice off MRP). Add shipping as a buyer-side line that does not
  reduce seller payout. Keep RTO-weighted loss + GST-on-fee + TCS/TDS as separate explicit
  line-items where applicable.
- `commission_pct` stays NULL (founder-locked) — confirmed again; the fee is per-product flat,
  not a per-category percentage.

### Goal-2 status note for backend (not blocking pricing)
The e-signature is NOT signed server-side on this account (clickwrap fields all "-",
is_agreement_accepted=false) despite the founder's belief — so the referral-fee rate-card and
per-order settlement remain unreachable (and the account has 0 delivered orders anyway). The
flat-fee finding above came entirely from the e-sig-FREE `fetch-supplier-products` source, so
pricing work is NOT blocked by the e-sig question.
