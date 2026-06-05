# Batch 7 — DRAFT findings (Grocery, super_id=26)

**Coverage:** 321 / 321 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed — **MAJOR FOUNDER PREDICTION CONFIRMED**

### 1. **🚨 FSSAI license is UNIVERSAL COMPULSORY in Grocery**

| Field | In N leaves | Compulsory |
|---|---|---|
| **Seller FSSAI License Number** | **321/321 (100%)** | **321 (100%)** |

→ **Founder's prediction (after Batch 3): "Grocery → FSSAI license" is now confirmed.** Every single Grocery template requires a Seller FSSAI License Number. This is a seller-specific certification, NOT a per-product field.

→ **Locks decision #9** (conditional onboarding extensions). A seller selling in Grocery MUST be asked at onboarding: "Provide your FSSAI license number." It then auto-fills on every grocery product.

### 2. Food-specific compulsory fields surface

| Field | In N | Compulsory | Notes |
|---|---|---|---|
| Veg/NonVeg | 270 | 270 | Universal food classification |
| Volumetric Weight | 270 | 15 | Mostly optional |
| Maximum Shelf Life | 46 | 46 | Compulsory in some categories |
| Added Preservatives | 37 | 37 | Compulsory |
| Organic | 44 | 44 | Yes/No flag, all compulsory |
| Flavour | 43 | 36 | Dropdown |
| Packaging Type | 30 | 30 | Compulsory |

→ Grocery wizard step structure (in addition to universals + FSSAI onboarding extension):
- **Food classification step**: Veg/NonVeg, Organic, Preservatives flag
- **Shelf life step**: Max Shelf Life, Best Before
- **Packaging step**: Packaging Type, Weight, Net Quantity

### 3. **Shorter forms** (median compulsory 23)
Grocery forms are SHORT compared to Fashion (28) and Home (33). Food products are simpler to describe than apparel. Wizard adapts step count down.

### 4. Spelling variants in same batch
- "Veg/NonVeg" (270 leaves) vs "Veg/Non Veg" (45 leaves) — same field, different separator
- Canonical-name layer **must** dedupe these.

### 5. Brand list scoped to Grocery
- Brand max enum = 1,269 in B7 (vs 3,998 in Sarees)
- Confirms decision: Brand API endpoint takes `category_id` parameter.

## Cross-batch impact

| | Before B7 | After B7 |
|---|---|---|
| TRUE universals | 26 | 26 (held) |
| Cumulative leaves | 1,672 | 1,993 (52.8%) |
| Recommended fields | 0 | 0 |
| Image rule 4/1 | 100% | 100% |
| Onboarding extensions confirmed | Kids+BIS, Electronics+R/IS/CM-L | **+Grocery+FSSAI (COMPULSORY!)** |

→ Decision #9 (conditional onboarding) status: **strong evidence accumulating**. FSSAI is the clearest case yet — 100% compulsory in 321 leaves.
