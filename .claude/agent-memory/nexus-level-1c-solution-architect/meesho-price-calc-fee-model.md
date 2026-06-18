---
name: meesho-price-calc-fee-model
description: Cracked Meesho seller P&L fee/tax model for the MeeSell Price Calculator — fixed vs fluctuating components, real public rates + citations, recommended calculator architecture
metadata:
  type: project
---

Definitive fee/tax model for the MeeSell Price Calculator (advisory report delivered 2026-06-18).

**Why:** Founder needed to "crack" the Meesho payout model by reconciling internal scrape findings (data-engineer rounds 1-4) + the founder's cost_management.xlsx with Meesho's actual public structure.

**How to apply:** When any meesell-* agent designs/builds the Price Calculator, this is the reconciled model.

## Cracked model (reconciled internal scrape + public sources)
- **Commission/referral fee = 0%** for most categories (Meesho's "0% commission" model is real, public + confirmed by live scrape: payout = seller_price − flat ₹9, no %). Treat commission as a SELLER INPUT defaulting to 0% (account-level default_monetization_percent=4.0 exists for some accounts → optional hint). NOT seedable per-category (dynamic by category×price-slab×promo — Wave 1.5 won't-fix).
- **Fixed/collection fee:** small FLAT fee (live scrape = ₹9 on a low-price hair band; varies by category/price-slab/weight at scale). Public sources call it "0 collection fee" but a fixed/handling component exists in practice. Model as a lookup/seller-input flat fee, NOT a %.
- **Shipping:** BUYER-PAID pass-through on standard (free-delivery) listings — neutral to seller payout. customer_price = seller_price + shipping_charges (EXACT in scrape). Weight×zone slab; seller cannot edit. Under a seller-absorbed-shipping promo the seller bears it.
- **GST on shipping = 18%** (confirmed public + the ₹9-on-₹50 scrape reconciliation: 18%×₹50≈₹9). This is the real per-order Meesho deduction on the shipping component.
- **TDS (Income-Tax §194-O) = 0.1%** on gross order value — REDUCED from 1% to 0.1% eff. 1-Oct-2024 (Budget 2024). Founder's 0.1% is CORRECT (post-2024). Only above ₹5L/FY gross.
- **GST-TCS (§52) = 0.5%** (0.25% CGST + 0.25% SGST intra-state / 0.5% IGST inter-state) — REDUCED from 1% eff. 10-Jul-2024. **Founder's model OMITS TCS — this is the one correction.** It's creditable (not a true cost) but reduces immediate payout. Add as optional line.
- **Output GST liability** = seller's own product GST = listing_price − listing_price/(1+gst%). Slab from HSN: hair accessories HSN 9615 = 12%/18%; textile-based 6217 = 12%. Source via an HSN→GST lookup table keyed by category.
- **RTO/returns:** seller bears REVERSE shipping on customer returns (not on pure RTO-undelivered). Model as RTO-rate × reverse-cost seller input (V1.5 per spec).
- **3 prices confirmed:** MRP (ceiling) > Meesho/listing price (drives payout) > WDRP (wrong-defective, lower band). Scrape: payout_wdrp = seller_wdrp − same flat fee.

## Component classification
- FIXED constants: TDS 0.1%, GST-TCS 0.5%, GST-on-shipping 18%, formula shape.
- SELLER INPUT: listing price, delivery mode, landed cost, commission% (default 0), RTO rate, MRP/WDRP.
- LOOKUP TABLES to build: HSN→output-GST-rate (by category), shipping weight×zone bands (have meesho_shipping_slabs.json stub), category→flat-fee (optional).

## Export wiring
3 prices map to Meesho XLSX template price columns: MRP→"MRP", Meesho price→"Price"/"Product Price", WDRP→"Wrong/Defective Product Price". Calculator output flows into the XLSX export adapter.

## Note on current code
`pricing_calcs` model + V1_FEATURE_SPEC Feature 7 are STRUCTURALLY THIN vs this model (single derived MRP, commission-from-categories=NULL, no shipping/TDS/TCS/fixed-fee lines, no WDRP). The data-engineer handoff (`handoff_pricing_transfer_price.md`) already flagged this to backend. See [[meesho-price-calc-fee-model]] cross-refs in meesell-data-engineer/MEMORY.md (rounds 3-4).
