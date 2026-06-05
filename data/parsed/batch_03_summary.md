# Batch 3 — DRAFT findings (Kids & Toys)

**Coverage:** 284 / 284 (100%)
**Failed:** 0
**Date:** 2026-06-04 (parsed during noon IST session)
**Parser version:** 0.1 (unchanged)
**Executed by:** meesell-data-engineer (coordinator) — fallback continues. Agent type `meesell-xlsx-parser` is not registered in Claude Code's subagent discovery (Agent tool error: "Agent type not found"). Founder's evening fix needs to do REGISTRATION, not just settings tweak.

> Draft for coordinator + founder discussion. Integrated into `docs/MEESHO_CATEGORY_INTELLIGENCE.md` only after founder sign-off.

---

## 1. Field-count distribution (Batch 3)

| Metric | Compulsory | Recommended | Optional | Total |
|---|---|---|---|---|
| Min | 20 | 0 | 10 | 32 |
| **Median** | **24** | 0 | 12 | 37 |
| Mean | 24.8 | 0 | 13.7 | 38.5 |
| Max | 42 | 0 | 28 | 60 |

**Min compulsory leaf:** `10181` Onesies & Rompers (20 compulsory)
**Max compulsory leaf:** `12597` Analog Watches (42 compulsory)

### Notable: Kids & Toys has SHORTER forms than Fashion
- B1 (Women Fashion) median: 28 compulsory
- B2 (Men Fashion) median: 27 compulsory
- **B3 (Kids & Toys) median: 24 compulsory** ← 14% shorter

→ Wizard step structure cannot be hard-coded. Even fundamental fields vary by super-category. Reinforces decision #5 (data-driven wizard).

---

## 2. Recommended fields confirmed absent — 569/569 leaves binary

Across all three batches now, exactly **0 fields** carry the `Recommended Field` marker. The pattern is solid at 569 leaves. V1 stays two-tier.

---

## 3. **TRUE UNIVERSALS — 26 fields locked, zero attrition through 3 batches**

Every one of the 26 B1∩B2 universals is also universal in Batch 3. **Zero fell out.**

### 18 always-compulsory universals (THE CORE WIZARD)
Product Name · Variation · Meesho Price · MRP · Net Weight (gms) · Inventory · Country of Origin · Generic Name · Image 1 (Front) · Manufacturer Name / Address / Pincode · Packer Name / Address / Pincode · Importer Name / Address / Pincode

### 8 always-optional universals
Image 2, 3, 4 · Product ID / Style ID · SKU ID · Brand Name · Group ID · Product Description

These 26 fields are now load-bearing assumptions for V1 architecture.

---

## 4. **CRITICAL FINDING — Kids & Toys introduces SAFETY-CRITICAL compliance fields**

Kids & Toys adds a tier of compliance fields that B1/B2 didn't have. These are legally and platform-mandated for child products:

| Field | In N leaves | Compulsory | Purpose |
|---|---|---|---|
| **Product Dimensions (L x B x H) in cm** | 133/284 | 133 (100%) | Physical safety + packaging |
| **Recommended Age** | 107/284 | 95 (89%) | Age-appropriateness — safety + compliance |
| **Kids Weight (In Kgs)** | 68/284 | 68 (100%) | Sizing for kid-wear |
| **Age** | 44/284 | 44 (100%) | Child-specific |
| **BIS/ISI Certification Number** | 28/284 | 0 (optional) | Indian safety standard — Bureau of Indian Standards |
| **Assembling/Assembly Required** | 39/284 | 37 (95%) | Safety warning |
| **Battery Required** | 19/284 | 18 (95%) | Safety warning |
| **Material Type** | 37/284 | 37 (100%) | Safety-relevant |

→ **MVP implication:** the Onboarding bucket may need to expand for sellers in Kids & Toys to capture BIS/ISI certification number once (rather than per product). Plus, the wizard needs a "Safety" step for category-conditional safety fields.

→ **Compliance complexity grows by super-category.** Books may add ISBN; Electronics may add BIS/IEC; Grocery may add FSSAI. The Onboarding bucket isn't a flat 10 fields — it's a base set + super-category extensions.

---

## 5. NEW field vocabulary — 149 fields introduced by Kids & Toys

Biggest expansion yet (vs 49 in B2). Kids & Toys is attribute-rich.

### Top 15 new fields
| Field | In N leaves | Compulsory | Notes |
|---|---|---|---|
| Product Dimensions (L x B x H) in cm | 133 | 133 | Compulsory wherever it appears |
| Recommended Age | 107 | 95 | Safety + compliance |
| Kids Weight (In Kgs) | 68 | 68 | |
| Age | 44 | 44 | |
| Material Type | 37 | 37 | |
| Product Width (cm) | 31 | 31 | |
| Assembling Required | 29 | 29 | Safety |
| Product Length (cm) | 29 | 29 | |
| BIS/ISI Certification Number | 28 | 0 | Optional but high-trust signal |
| Gender | 25 | 21 | |
| Product Height (cm) | 24 | 24 | |
| Colour | 21 | 18 | Note: "Colour" ≠ "Color" — Meesho mixes spellings |
| Battery Required | 19 | 18 | Safety |
| Battery | 11 | 11 | |
| Assembly Required | 10 | 8 | Synonym for Assembling Required |

### Spelling drift detected
- "Colour" (British) vs "Color" (American) — both appear; same semantic field
- "Assembly Required" vs "Assembling Required" — same field name family
- "Battery" vs "Battery Required" vs "Battery Available" — three variants for the same concept

→ **Data quality issue at the source.** When mapping schema, the field-name normaliser must handle these. Recommend storing a `canonical_field_name` alongside the raw name.

---

## 6. Cross-batch field analysis (B1+B2+B3)

| Metric | Value |
|---|---|
| Total leaves parsed cumulative | 569 / 3,772 (15.1%) |
| Unique field names across 3 batches | **557** |
| Fields appearing in ALL THREE batches | 141 |
| TRUE universals (in 100% of all 3 batches) | 26 |
| Fields with variable enum size (Brand pattern) | **106** (up from 82 after B2) |
| Recommended marker instances | 0 |
| Image rule "4 slots, 1 compulsory" coverage | 569/569 (100%) |
| Median compulsory across batches | 24–28 (super-category dependent) |

→ Per-batch new-field growth: B2 added 49 / B3 added 149. **Extrapolating to Batch 12, we'll see ~1,500-2,000 unique field names total.** No way to hand-code 1,500 form components — the data-driven primitive library is non-negotiable.

---

## 7. Same-name-different-enum (Brand pattern) — now 106 fields

| Field | Enum range | # instances |
|---|---|---|
| Brand | 1 – 3,998 | 568 |
| Variation | 1 – 205 | 569 |
| Group ID | 30 – 200 | 569 |
| Color | 5 – 178 | 489 |
| Length Size | 25 – 321 | 142 |
| Width Size | 30 – 321 | 27 |
| Top Length Size | 20 – 291 | 45 |
| Foot Length Size | 12 – 251 | 37 |
| Top Chest Size | 50 – 191 | 11 |
| Waist Size | 27 – 133 | 97 |
| Bust Size | 25 – 133 | 70 |

→ Brand-pattern field count grows ~25/batch. Will likely reach 200+ by Batch 12. The auto-classification rule by `enum_count` continues to hold.

---

## 8. Dropdown distribution (Batch 3)

| Field | Max in B3 |
|---|---|
| Brand | 1,345 |
| Top Length Size | 291 |
| Foot Length Size | 251 |
| Country of Origin | 194 |
| Top Chest Size | 191 |
| Length Size | 151 |
| Width Size, Bedsheet Length/Width | 150 each |
| Bottom Length Size | 131 |
| Bust Size, Bottom Waist Size | 130 each |
| Product Weight | 106 |

→ Brand in Kids & Toys (max 1,345) is **smaller** than in Sarees (3,998) — confirms brand lists are category-scoped. Backend API endpoint design: `GET /brands/search?q=&category_id=` returns the right slice. Don't bundle one global brand list to the client.

---

## 9. Image rules — UNIFORM across 569 leaves

100% of Batch 3 has the same 4-slot, 1-compulsory pattern. Image UI design is permanently locked. Across all 569 leaves: ZERO variance.

---

## 10. Template-vs-leaf deduplication

| Batch | Leaves | Distinct templates | Dedup % |
|---|---|---|---|
| B1 (Women Fashion) | 179 | 169 | 5.6% |
| B2 (Men Fashion) | 106 | 105 | 0.9% |
| **B3 (Kids & Toys)** | **284** | **247** | **13.0%** |

→ Kids & Toys has **2-3× more template reuse** than Fashion. Meesho's leaf taxonomy is finer-grained in Kids (lots of leaf-variants per template). Schema-by-template (decision #7) saves more storage here than in Fashion.

---

## 11. Onboarding vs Catalog classification — extended

### 🟢 Onboarding bucket — UNCHANGED at 10 universal fields
9 compliance fields + Country of Origin. None of Batch 3's new fields are seller-constant.

### 🔵 Catalog wizard bucket — extends per super-category
- Universal core (16 fields, locked)
- Category-specific extension (variable count per leaf)

### 🟡 NEW BUCKET PROPOSAL: Conditional onboarding — for category-specialised sellers
Kids & Toys reveals a third pattern:
- A seller who only lists toys benefits from being asked at onboarding: "Do you have BIS/ISI certification? Y/N → If Y, enter once → autofill on every toy product."
- A seller who lists across multiple super-categories may need a "compliance profile per category" sub-section in onboarding.

**Recommendation:** the seller-profile schema gets a `compliance_extensions: jsonb` field that holds per-super-category compliance values (BIS, FSSAI, ISBN, etc.). Onboarding wizard adds conditional steps based on the super-categories the seller declares they'll sell.

This pattern will probably grow with each batch (Grocery → FSSAI, Books → ISBN, Electronics → BIS, Health & Wellness → AYUSH license). Track over Batches 4-12.

---

## 12. Anomalies / parser warnings

- **Zero parse failures.** All 284 files parsed cleanly.
- Zero anomalies in the output JSON.
- Parser v0.1 generalises perfectly to Kids & Toys.
- **Data-quality issues at the SOURCE** (not parser):
  - Field name spelling drift ("Colour" / "Color")
  - Synonym field names ("Assembly" / "Assembling")
  - Recommend a `canonical_field_name` mapping layer

---

## 13. Suggested discussion points (Batch 3's MVP contributions)

1. **The 26 true universals are EXTREMELY stable.** Three batches × very different domains × zero attrition. We can start designing the universal section of the wizard with confidence.

2. **The Onboarding bucket likely grows per super-category** (BIS for Kids, FSSAI for Grocery, ISBN for Books). Recommend seller-profile schema reserves a `compliance_extensions: jsonb` field. Onboarding wizard has conditional steps.

3. **Spelling drift / synonyms exist at the source.** Need a `canonical_field_name` normalisation table maintained alongside `category_attributes.json`.

4. **Compulsory median DROPPED in Kids & Toys (24 vs 27-28 in Fashion).** Wizard cannot have a fixed step count. Data-driven step boundaries (decision #5) is the only viable approach.

5. **Safety-conditional fields** (Recommended Age, Battery Required, BIS) need to surface as a "Safety" step in the wizard for relevant categories. Pattern will recur in Electronics (Battery, IEC) and others.

6. **Brand list IS category-scoped.** Max Brand enum dropped from 3,998 (Sarees) to 1,345 (Kids). API endpoint must accept `category_id` to return the right slice.

7. **Template dedup is bigger in Kids (13%) than Fashion (1-6%).** Storage-by-template strategy is even more important. Estimated storage savings on full corpus: 5-15% (variable by super-category).

8. **149 new fields in one batch.** Total unique field names may reach ~1,500 by Batch 12. The data-driven input primitive library is no longer a nice-to-have — it's the only way the form renderer scales.

---

## 14. Cross-batch cumulative tracker

| Metric | After B1 | After B2 | **After B3** |
|---|---|---|---|
| Leaves parsed | 179 (4.7%) | 285 (7.6%) | **569 (15.1%)** |
| Templates | 169 | 273 | **520** |
| Unique field names | 359 | 408 | **557** |
| TRUE universals | — | 26 | **26 (held!)** |
| Brand-pattern fields | — | 82 | **106** |
| Recommended-field instances | 0 | 0 | **0** |
| Image rule "4 slots, 1 compulsory" | 100% | 100% | **100%** |

---

## 15. Next

- **Founder review of this Batch 3 draft.** Especially decisions about the safety-field bucket and conditional onboarding.
- **At laptop:** co-author the first integrated SSoT entry covering B1 + B2 + B3 in `docs/MEESHO_CATEGORY_INTELLIGENCE.md`.
- **Workspace fix:** agent registration + (possibly) hook tweak.
- **Batch 4:** Consumer Electronics (super_id=16, 248 leaves) — likely surfaces tech-spec attributes (RAM, Battery Capacity, Connectivity, IEC certification).
