---
name: project-pricing-transfer-price-model
description: "EMPIRICALLY CONFIRMED Meesho pricing/settlement model for the Price Calculator (Feature 7). Source = getTransferPrice API census of all 3,772 categories (2026-06-19) + founder portal verification. Commission=0% everywhere; shipping=per-category CONSTANT (weight-independent, founder-confirmed in portal); formula verified on 100% of rows. Calculator can run fully OFFLINE from the category lookup. Supersedes the WRONG model in merged PR #285 (backend) + open PR #287 (FE)."
metadata:
  node_type: memory
  type: project
---

# Meesho Price Calculator — confirmed settlement model (Feature 7)

Empirically established 2026-06-19 via the `getTransferPrice` API census of **all 3,772 categories** (`logs/scraper/transfer_price_census.jsonl` + `_summary.json`), then the last open question was closed by the **founder verifying directly in the Meesho supplier portal**.

## The formula (verified on 3,772/3,772 rows, 0 failures)
```
total_price     = price + shipping
gst_on_shipping = 18% × shipping        # field name in API = gst_price
tds             = 0.1% × total_price
tcs             = 0
commission_fees = 0
transfer_price  = price − commission_fees − gst_on_shipping − tds − tcs
```
Founder's true-profit layer (on top of Meesho settlement):
```
net_profit = transfer_price − output_GST_liability − landed_cost
```
- output GST = configurable per-product input (GST slab); commission default 0, optional input.
- Sanity row: sscat_id 10949 (Extension Chords) @ price 100 → shipping 82, gst_price 14.76, tds 0.18, tcs 0, transfer_price 85.06, total 182.

## The two confirmed facts that make this offline-deterministic
1. **Commission = 0% across ALL 3,772 categories.** The "4% default_monetization_percent" shown in the panel is display-only and never charges. (`commission_analysis.non_zero_count = 0`.)
2. **Shipping = per-category CONSTANT.** Keyed to `sscat_id` only. **Price-independent** (census) AND **weight/dimension-independent** — FOUNDER CONFIRMED IN PORTAL 2026-06-19 that changing the declared weight does NOT change the shipping charge. The getTransferPrice endpoint doesn't even accept a weight field. Weight/volume is baked into Meesho's category default, not re-derived per listing. Range ₹48–₹8,435, 365 distinct values.

**Why:** because shipping is a per-category constant with no live inputs, the production calculator computes everything from a static lookup — NO live Meesho calls (zero ban risk), no weight input, no edge cases. Matches Meesho to the paise.

## Estimate vs. actual settlement (founder-surfaced disclaimer 2026-06-19)
Meesho shows this disclaimer when editing the catalog price: *"Bank settlement amount may vary slightly based on the quantity in the order, Meesho commission policy at the time of the order and the actual weight of the product as calculated by our third party delivery partner."*
- Confirms our model is the **listing-time ESTIMATE** (deterministic, category-keyed, weight-independent) — which is exactly what `getTransferPrice` returns and what a pre-order price calculator should show.
- The **actual** post-order settlement can drift for 3 reasons Meesho disclaims: (1) order quantity, (2) commission policy at order time (→ why commission stays a PARAMETER, not hardcoded 0), (3) courier's actual measured weight (declared weight doesn't move the listing estimate, but the courier reweighs at delivery and that CAN change the real payout).
- Product implication: label our output **"Estimated Bank Settlement"** (not a guarantee) and mirror Meesho's disclaimer text near the result. Sets the same expectation Meesho does and protects us from "your number was off by ₹X" complaints.

## REAL-ORDER VERIFICATION (founder's first actual payout, 2026-06-19)
Product: Handmade Woolen Hair Clips, SKU TTC-BL-OR-HP-NG-P4, qty 1. Sub-order 289264797669114560_1. Ordered 22 May, paid 8 Jun.
Actual payment breakdown: Sale Revenue ₹70, Shipping Revenue +₹45, Meesho Commission ₹0, Warehousing ₹0, Shipping Charge −₹53.10, TDS −₹0.12, **Bank Settlement ₹61.78**.
- KEY INSIGHT: Shipping Charge 53.10 = base shipping 45 × 1.18 (i.e. base + 18% GST). Shipping Revenue (+45) cancels the base of Shipping Charge → seller's REAL shipping cost = ONLY the 18% GST = ₹8.10. This is the gross presentation of our net formula.
- Formula reproduces the real payout to the paise: 70 − (18%×45=8.10) − 0.12 TDS − 0 commission = **61.78** ✓.
- This DEFINITIVELY kills the old #285/#287 model (which deducted FULL shipping ~₹50 from seller → would show ~₹11, catastrophically wrong). Seller bears only GST-on-shipping, NOT the shipping itself.
- SHIPPING FLUCTUATION CONFIRMED: calculator estimate used base shipping ₹50 (GST ₹9 → est. settlement ₹60.88); the actual delivered order used base shipping ₹45 (GST ₹8.10 → ₹61.78). Courier measured the real parcel lighter than the category default → seller got ₹0.90 MORE than estimated. Exactly the "actual weight by third-party delivery partner" disclaimer. Estimate vs actual drift ≈ 1.5% here.

## How to apply
- The lookup lives in the census summary: `logs/scraper/transfer_price_census_summary.json` → `lookup` (3,772 entries: `sscat_id → {leaf_name, path_str, commission_percentage, shipping_charges, transfer_price_at_100, formula_ok}`). Builders should productionize this as a shipped data file.
- **REFRESH CADENCE (founder ruling 2026-06-19): we ALREADY run a MONTHLY scrape to refresh the category tree. The per-category pricing lookup (commission + shipping per sscat_id via getTransferPrice) MUST be folded into that SAME monthly scrape job** — one run refreshes categories AND pricing together. Owner = `meesell-scraper-maintainer` + `meesell-data-engineer`. Do NOT build a separate pricing-refresh schedule; extend the existing monthly category scraper to also run the getTransferPrice census and emit the updated pricing lookup data file.
- Calculator inputs: price, sscat_id (→ shipping lookup), output GST slab (per-product), optional commission override. Outputs the 3 prices that feed the export.
- **PR #285 (backend, MERGED) and #287 (FE, OPEN/gate-stopped) are built on the WRONG model** (deducted shipping FROM seller, used 4% commission, fabricated logistics/fixed fees + TCS). Both MUST be re-reworked to THIS model. `docs/V1_FEATURE_SPEC.md` §Feature 7 and `docs/BACKEND_ARCHITECTURE.md` §12.M were amended for the wrong #285 model — re-reconcile.
- getTransferPrice contract (for refresh only, NEVER in prod): `POST https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice`, body `{"sscat_id":<int>,"gst_percentage":null,"price":100,"supplier_id":<id>,"duplicate_pid":null,"gst_type":"ENROLMENT"}`. Headers: identifier=oinpw, client-type=d-web, client-package-version=1.0.1, supplier-id=<id>. Read-only compute; password-login only (no OTP); reuse warm session `meesho_storage_state.json`.
- Detailed builder handoff: `.claude/agent-memory/meesell-data-engineer/handoff_pricing_transfer_price.md`.
