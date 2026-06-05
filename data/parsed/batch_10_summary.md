# Batch 10 — DRAFT findings (Beauty + Health super-cluster, super_ids=19+36+37+14+88+34)

**Coverage:** 341 / 341 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed — **CRITICAL CORPUS-WIDE DISCOVERY**

### 1. 🚨 **Eye-Serum (leaf 12378) breaks the 26-universal claim**

Eye-Serum is a **template outlier** — it uses an alternate compliance representation:

| Standard pattern (3,771 leaves) | Eye-Serum pattern (1 leaf) |
|---|---|
| Manufacturer Name + Address + Pincode (3 fields) | **Manufacturer Details** (1 collapsed field) |
| Packer Name + Address + Pincode (3 fields) | **Packer Details** (1 collapsed field) |
| Importer Name + Address + Pincode (3 fields) | **Importer Details** (1 optional field) |
| Net Weight (gms) | Product weight (gms) (synonym!) |

→ The full-corpus **TRUE universal count = 15** (not 26 as B1-B4 suggested). But with canonical-name normalisation, **28 fields are PRACTICAL universals (≥99% coverage)**.

→ MVP implication: the form schema must accept BOTH representations. The Eye-Serum-style collapsed fields are legitimate — Meesho ships them, sellers fill them. Canonical-name layer maps:
- `Manufacturer Name + Address + Pincode` ↔ `Manufacturer Details` (combined)
- `Net Weight (gms)` ↔ `Product weight (gms)` (case + word order)

### 2. License/Registration compliance fields (cosmetic/AYUSH-equivalent)

| Field | In N | Compulsory |
|---|---|---|
| License/Registration Number | 20 | 20 (100%) |
| License/Registration Expiry Date | 15 | 15 (100%) |
| License/Registration Type | 20 | 20 (100%) |
| Seller FSSAI License Number | 15 | (food-overlap products like supplements) |

→ Beauty/Health adds an **onboarding extension**: License/Registration Number + Type + Expiry. Used for cosmetic/health products requiring licensing (some are AYUSH, some BIS, some state-board licensed — Meesho normalises to "License/Registration").

→ Onboarding extension map updates:
- + Beauty/Health: License/Registration (Number, Type, Expiry Date)
- + Beauty/Health (food overlap like supplements): FSSAI (also)

### 3. Beauty-specific consumer-attribute fields

| Field | In N | Compulsory |
|---|---|---|
| Concern | 110 | 70 | Skincare concerns (acne, dryness, anti-aging) |
| Skin Type | 63 | 53 | (oily, dry, combination) |
| Makeup Origin | 28 | 8 | (cruelty-free, vegan, organic) |
| Active Ingredients | 4 | 4 | |
| Item Form | 4 | 4 | (cream, gel, serum, powder) |

### 4. Voltage/Wattage hit 500 (max enum in B10)
Beauty + Health includes appliances (hair dryers, straighteners, electric massagers). These bring tech-spec dropdowns of up to 500 values. Confirms `number_with_unit` primitive design.

## Cross-batch impact

| | Before B10 | After B10 |
|---|---|---|
| **TRUE universals** (strict 100%) | 26 | **15** ← Eye-Serum outlier |
| **Practical universals** (≥99%) | — | **28** |
| Cumulative leaves | 2,816 | 3,157 (83.7%) |
| Recommended fields | 0 | 0 (3,157/3,157) |
| Image rule 4/1 | 100% | 100% |
| Onboarding extensions confirmed | Kids+BIS, Electronics+R/IS, Grocery+FSSAI | **+Beauty/Health+License/Registration** |

→ B10 forces the founder-relevant refinement: the universal core is **28 practical fields (≥99% coverage)**, not 26 strict. The 9-field compliance block is **near-universal**, with one outlier that uses a different representation.
