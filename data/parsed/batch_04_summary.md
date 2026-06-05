# Batch 4 — DRAFT findings (Consumer Electronics)

**Coverage:** 248 / 248 (100%)
**Failed:** 0
**Date:** 2026-06-04
**Parser version:** 0.1 (one false-positive surfaced — see Section 11)
**Executed by:** meesell-data-engineer (coordinator) — fallback continues. Agent registration still pending.

> Draft for coordinator + founder discussion. Integrated into `docs/MEESHO_CATEGORY_INTELLIGENCE.md` only after founder sign-off.

---

## 1. Field-count distribution (Batch 4)

| Metric | Compulsory | Recommended | Optional | Total |
|---|---|---|---|---|
| Min | 19 | 0 | 10 | 29 |
| **Median** | **24** | 0 | 12 | 36 |
| Mean | 24.0 | 0 | 12.6 | 36.6 |
| Max | 39 | 0 | 26 | 62 |

**Min compulsory leaf:** `10347` Skins & Decals Sticker (19 compulsory) — surprisingly low for electronics
**Max compulsory leaf:** `10308` Bluetooth Speakers (39 compulsory)

### Median compulsory pattern continues
- B1 Women Fashion: 28
- B2 Men Fashion: 27
- B3 Kids & Toys: 24
- **B4 Consumer Electronics: 24**

→ **Fashion = ~28, everything else = ~24.** Strong evidence Fashion is the most attribute-rich super-category. Wizard sizing should default to the lighter pattern; Fashion-specific extensions kick in by category.

---

## 2. Recommended fields confirmed absent — 817/817 leaves

Across all four batches, exactly **0 fields** carry the `Recommended Field` marker. **Binary marker scheme is rock-solid at 817 leaves.** V1 stays two-tier.

---

## 3. TRUE UNIVERSALS — 26 fields locked across 4 batches (zero attrition)

The 26 core universal fields survived Batch 4 untouched. Every universal field from B1 ∩ B2 ∩ B3 is also universal in B4. The core form is now safe for production design.

---

## 4. **NEW: A field nearly broke into "universal" — Warranty Type**

| Field | B1 | B2 | B3 | B4 |
|---|---|---|---|---|
| Warranty Type | 0/179 | 0/106 | 0/284 | **149/248 (60%, all compulsory)** |

Warranty Type is **the biggest single-batch field surprise yet** — 149 leaves all-compulsory, only in Electronics. This is a category-specific super-strong field, not a universal. **MVP implication:** the wizard's "Warranty" step should be conditional on Consumer Electronics + similar (Appliances, possibly some Sports goods).

---

## 5. **NEW: A dropdown LARGER than Brand — Compatible Models (4,481 values)**

Until B4, Brand was the gold standard for "huge dropdown" — max 3,998 values in Sarees. Batch 4 introduces:

| Field | Max enum in B4 | Notes |
|---|---|---|
| **Compatible Models** | **4,481** | List of every phone/device the accessory fits |
| Brand | 2,057 | Lower than Fashion's 3,998 (Electronics has fewer brands) |
| Compatible Mobiles | 1,775 | Similar to Compatible Models but slightly narrower |
| Compatible Model | 260 | Singular variant — Meesho ships both |

→ The "Brand pattern" auto-classification by `enum_count` handles these without any new rules. Same primitive (API-backed search), different field name. This is exactly why decision #6 (data-driven primitive library) was the right call.

→ Three near-synonyms: `Compatible Model` / `Compatible Models` / `Compatible Mobiles`. Goes in the canonical-name normaliser.

---

## 6. **NEW pattern: Indian regulatory identifier fields (R / IS / CM-L Numbers)**

Batch 4 adds compliance fields that didn't appear before:

| Field | In N leaves | Compulsory | Purpose |
|---|---|---|---|
| IS Number | 112/248 | 0 (optional) | Indian Standard number — BIS certification reference |
| R Number | 106/248 | 0 (optional) | WPC / wireless equipment certification |
| BIS/ISI Certification Number | 20/248 | 0 (optional) | Repeat from B3 (Kids & Toys) |
| CM/L Number | 26/248 | 0 (optional) | Compulsory Marking License (BIS scheme) |

→ All optional. They're "high-trust signals" — sellers who fill them rank higher in search/quality.
→ **All four are seller-specific certifications, not per-product.** Strong candidates for the `compliance_extensions: jsonb` Onboarding extension (decision #9, pending).

### Updated Onboarding bucket prediction (cross-batch)
- Base (all sellers): 10 fields
- + Kids & Toys seller: BIS/ISI Cert Number
- + Electronics seller: BIS/ISI + R Number + IS Number + CM/L Number
- + Grocery (predicted): FSSAI license
- + Books (predicted): ISBN registry
- + Health & Wellness (predicted): AYUSH license

---

## 7. Tech-spec attributes introduced by Electronics

| Field | In N leaves | Compulsory |
|---|---|---|
| Voltage | 59 | 59 (100%) |
| Wattage | 30 | 30 (100%) |
| Capacity | 8 | 6 (75%) |
| Frequency | 5 | 0 |
| Battery Type | 5 | 0 |
| Number of Ports | 5 | 0 |
| Operating Voltage | 4 | 4 (100%) |
| USB Ports | 3 | 1 |
| Operating System | 2 | 1 |
| Storage Capacity | 2 | 0 |
| Connectivity | 2 | 0 |
| Bluetooth Version | 2 | 0 |
| Bluetooth Range | 2 | 2 (100%) |
| SSD Capacity | 2 | 0 |

→ Most tech-specs appear in <10 leaves each — they're hyper-specific (Bluetooth Range only matters for Bluetooth speakers, SSD Capacity for laptops, etc.). The "long tail" of category-specific fields keeps growing.

→ **Number-with-unit fields surface here** (Voltage: V, Wattage: W, Frequency: Hz, Capacity: mAh). Decision #6's input primitive library needs a `number_with_unit` primitive (numeric input + unit suffix label). Will be a single component class for V, W, Hz, mAh, mm, cm, g, kg, etc.

---

## 8. Same-name-different-enum (cumulative across 4 batches) — now 136 fields

| Field | Enum range | # instances |
|---|---|---|
| Brand | 1 – 3,998 | 815 |
| Compatible Mobiles | 48 – 1,775 | 3 |
| Product Weight | 20 – 326 | 26 |
| Length Size | 25 – 321 | 150 |
| Width Size | 30 – 321 | 32 |
| Top Length Size | 20 – 291 | 45 |
| Foot Length Size | 12 – 251 | 37 |
| Variation | 1 – 205 | 817 |
| Type | 1 – 201 | 288 |
| Group ID | 30 – 200 | (~817) |

→ Brand-pattern field count grew 106 → 136 (added 30 in B4). Tracking continues.

---

## 9. Dropdown distribution (Batch 4) — top by max enum

| Field | Max in B4 |
|---|---|
| **Compatible Models** | **4,481** ← new champion |
| Brand | 2,057 |
| Compatible Mobiles | 1,775 |
| Product Weight | 326 |
| Compatible Model | 260 |
| Type | 201 |
| Country of Origin | 194 |
| Length Size | 191 |
| Cable Length Size | 181 |
| Wattage | 101 |
| Length | 100 |

→ 11 dropdowns ≥ 100 values in B4 alone. Pattern holds.

---

## 10. Image rules — STILL uniform (apparent break was a parser bug)

The cross-batch analysis flagged "B4 image rule uniform = False." Investigation reveals **this is a false alarm caused by a parser misclassification**:

- 247/248 leaves have the standard pattern (4 slots, slot 1 compulsory)
- 1 leaf (Webcams, leaf 13508) APPEARS to have 5 image fields, but the 5th is **"Still Image Sensor Resolution"** — a tech-spec dropdown (camera megapixels), NOT an image upload.
- Parser bug: `infer_data_type` classifies any field name containing "image" as `image_url`. "Still Image Sensor Resolution" got mis-tagged.

**True state:** image rule is 100% uniform across all 817 leaves cumulative. The pattern holds.

**Parser fix for v0.2:** restrict `image_url` detection to fields matching the canonical pattern (`^Image \d+`, `^Front Image$`, `^Back Image$`, etc.) — not loose substring matching.

---

## 11. Anomalies / parser warnings

- **Zero parse failures.** All 248 files loaded.
- Zero anomalies in output JSON.
- **One classification false-positive** (Webcams' "Still Image Sensor Resolution"). See Section 10. Parser v0.2 fix queued.
- Spelling/synonym drift continues:
  - "Battery" / "Battery Required" / "Battery Available" / "Batteries Required" / "Batteries Included" / "Battery Type" (six variants)
  - "Compatible Model" / "Compatible Models" / "Compatible Mobiles" / "Compatible Devices"
  - "Cable Length" / "Cable Length Size"
  - Canonical-name layer needs to handle this growing alias soup.

---

## 12. NEW field vocabulary — 151 fields introduced by B4

Already covered above in Sections 4–7. Total novel field count by batch:
| Batch | New unique fields |
|---|---|
| B1 (foundation) | 359 |
| B2 (Men Fashion) | 49 |
| B3 (Kids & Toys) | 149 |
| **B4 (Consumer Electronics)** | **151** |

→ Cumulative unique field names: **708**. Trajectory still suggests 1,500-2,000 by Batch 12.

---

## 13. Suggested discussion points (Batch 4's MVP contributions)

1. **The 26 true universals are DONE.** Four batches × completely different domains × zero attrition. We can ship the universal section of the wizard with full confidence. The risk that Batches 5-12 break this is now very low.

2. **Median compulsory split confirmed: Fashion=~28, everything else=~24.** Wizard step count varies by super-category. Fashion gets an extra step or two.

3. **Warranty Type is a strong category-conditional universal** — appears in 60% of Electronics leaves, all compulsory. Wizard adds a "Warranty" step for Electronics, Appliances, possibly Sports goods. Will refine in B10.

4. **Indian regulatory identifiers (BIS, R Number, IS Number, CM/L) are seller-specific certifications, NOT per-product fields.** They're optional in the templates because not every seller has them, but for sellers who do, they should auto-fill. **Strong evidence for decision #9** (conditional onboarding extensions). Recommend locking decision #9 now — pattern is clear.

5. **Compatible Models / Mobiles is the new largest dropdown (4,481).** Beats Brand. Same primitive (API-backed search). Validates decision #6.

6. **Number-with-unit primitive** needed — Voltage (V), Wattage (W), Frequency (Hz), Capacity (mAh), dimensions (cm/mm), weight (g/kg). One component, configurable unit suffix.

7. **Canonical field-name layer cannot wait.** 6 variants for Battery alone in B4 + earlier spelling drift = the alias map needs to start being built now, alongside the parser. Recommend `data/parsed/canonical_field_aliases.json` maintained per batch.

8. **Parser v0.2 fix queued** — tighten `image_url` detection to canonical patterns only.

---

## 14. Cross-batch cumulative tracker

| Metric | After B1 | After B2 | After B3 | **After B4** |
|---|---|---|---|---|
| Leaves parsed | 179 (4.7%) | 285 (7.6%) | 569 (15.1%) | **817 (21.7%)** |
| TRUE universals | — | 26 | 26 | **26 (HELD)** |
| Unique field names | 359 | 408 | 557 | **708** |
| Brand-pattern fields | — | 82 | 106 | **136** |
| Recommended-field instances | 0 | 0 | 0 | **0** |
| Image rule canonical | 100% | 100% | 100% | **100%** (parser bug, not real break) |
| Median compulsory (super-cat dependent) | 28 | 27 | 24 | **24** |

---

## 15. Next

- **Founder review** of this Batch 4 draft. Especially:
  - Decision #9 (conditional onboarding compliance extensions) — propose to lock now.
  - Number-with-unit primitive (decision #6 extension) — propose to add to library now.
  - Canonical field-name normalisation layer — needs ownership decision.
- **Batch 5:** Home & Kitchen — part A (super_id=30, ~280 leaves). Will be the first batch of the BIG home cluster. Expected: kitchenware specs, FSSAI for food-storage products, voltage for appliances.
