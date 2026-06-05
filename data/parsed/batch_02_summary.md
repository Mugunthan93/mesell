# Batch 2 — DRAFT findings (Men Fashion)

**Coverage:** 106 / 106 (100%)
**Failed:** 0
**Date:** 2026-06-04 (parsed during morning IST session)
**Parser version:** 0.1 (unchanged from Batch 1)
**Executed by:** meesell-data-engineer (coordinator) — coordinator-implements fallback continues. Reason: `meesell-xlsx-parser` is **not registered** as a dispatchable subagent type (confirmed via Agent tool — "Agent type not found"); the hook isn't the only thing — the agent itself was never wired into Claude Code's subagent discovery. Founder's 7 PM IST hook-fix will need to do registration, not just edit settings.

> Draft artifact for coordinator + founder discussion. Integrated into `docs/MEESHO_CATEGORY_INTELLIGENCE.md` only with founder sign-off.

---

## 1. Field-count distribution (Batch 2)

| Metric | Compulsory | Recommended | Optional | Total |
|---|---|---|---|---|
| Min | 21 | 0 | 10 | 31 |
| Median | 27 | 0 | 13 | 40 |
| Mean | 27.1 | 0 | 13.8 | 40.8 |
| Max | 43 | 0 | 25 | 62 |

**Min compulsory leaf:** `10135` Gym Vests (21 compulsory)
**Max compulsory leaf:** `10148` Kurta Sets (43 compulsory)

Distribution holds: Batch 2 form length is essentially identical to Batch 1 (median 27 vs 28 compulsory). Hypothesis: **median compulsory ≈ 28** is a Meesho-wide constant. Worth tracking in Batches 3-12.

---

## 2. Confirmed: zero "Recommended" fields, two batches in

Across **285 leaves parsed so far (B1 + B2)**, exactly **0 fields** carry the `Recommended Field` marker. Increasingly confident Meesho's column-marker scheme is binary at the bulk-template level. V1 stays two-tier (Compulsory / Optional).

If Batch 3+ surfaces any Recommended fields, we re-open this. Until then, decision #3 from Batch 1 is reinforced.

---

## 3. **CROSS-BATCH (B1 ∩ B2): 26 TRUE universals locked**

Every one of Batch 1's 26 universals is also universal in Batch 2 — zero fell out. This is the rock-solid core form that every Meesho catalog will need.

### 18 always-compulsory universals (the "core wizard")
Product Name · Variation · Meesho Price · MRP · Net Weight (gms) · Inventory · Country of Origin · Generic Name · Image 1 (Front) · Manufacturer Name / Address / Pincode · Packer Name / Address / Pincode · Importer Name / Address / Pincode

### 8 always-optional universals
Image 2, 3, 4 · Product ID / Style ID · SKU ID · Brand Name · Group ID · Product Description

### 2 fields became universal in B2 that weren't quite in B1
| Field | B1 coverage | B2 coverage | Notes |
|---|---|---|---|
| Brand | 178/179 (99%) | 106/106 (100%) | Always-optional, but ~always present |
| Wrong/Defective Returns Price | 178/179 (99%) | 106/106 (100%) | Always-optional pricing field |

→ Reasonable to **promote these to universal** assuming Batches 3-12 don't break them.

---

## 4. **CRITICAL CROSS-BATCH FINDING: 82 fields share names but use different enums**

The "Brand pattern" you flagged in decision #2 is much larger than Brand alone. **82 distinct field names show category-dependent enum sources** across B1 + B2.

### Top 15 by enum-size variance
| Field | Enum range across categories | # instances |
|---|---|---|
| **Brand** | **1 – 3,998 values** | 284 |
| Variation | 1 – 205 | 285 |
| Group ID | 30 – 200 | 285 |
| Color | 17 – 178 | 249 |
| Bust Size | 25 – 133 | 48 |
| Waist Size | 27 – 133 | 64 |
| Length Size | 25 – 321 | 96 |
| Width Size | 30 – 321 | 22 |
| Foot Length Size | 12 – 251 | 16 |
| Shoulder Size | 10 – 126 | 41 |
| Product Weight | 20 – 326 | 21 |
| Chest Size | (B2-only, max 122) | 16 |
| Dupatta Length | 19 – 126 | 5 |
| Blouse Length | 2 – 126 | 3 |
| Size Length | 61 – 126 | 2 |

### Why this matters for the input primitive library

A field with name `Brand` in Sarees has 3,730 enum values; the same field in Gym Vests has ~250. The frontend cannot ship one canonical "Brand picker" with a static enum. **The renderer must pick the right primitive at runtime based on `enum_count` per (category, field) pair.**

Proposed classification rule (auto-derived from parser output):
| enum_count range | Primitive |
|---|---|
| 0 (no enum) | text / number / date / textarea (per `data_type`) |
| 1–20 | radio buttons or small native dropdown |
| 21–100 | searchable Material autocomplete (in-memory) |
| 101–500 | searchable autocomplete with virtualisation |
| > 500 | API-backed search picker (`GET /api/v1/{field}/search?q=&category_id=`) |

This rule is automatic. No hand-curation needed. Decision #6 (input primitive library) is now data-driven.

---

## 5. NEW field vocabulary introduced by Batch 2 (49 fields not seen in B1)

Menswear adds its own attribute language on top of the 174 shared fields.

### Most common new fields (in 5+ leaves)
| Field | In N leaves | Likely cluster |
|---|---|---|
| Chest Size | 16 | Tops, Shirts, T-Shirts |
| Waterproof | 15 | Outerwear, footwear |
| Originals | 14 | (purpose unclear — needs investigation) |
| Number of Pockets | 9 | Cargos, jackets |
| Toe Shape | 5 | Footwear |

### Niche new fields (in 1-4 leaves)
Fastening, Trends, Stretchability, Hemline, Scarf Color, Season, Main Trend, Scarf Fabric, Length Size - Dad, Top Chest Size, Bottom Closure, Chest Size - Dad, Compatible Model, Bottom Hem, Diameter If Round, …

→ "Dad" suffixed fields (`Length Size - Dad`, `Chest Size - Dad`) suggest **parent-child product variants** within Meesho's schema — likely "Father-Son combo" SKUs. Will investigate during Batch 12 (long tail) if needed.

---

## 6. Onboarding vs Catalog classification (your two-section model applied)

Applying decision #1 + your structural lock to the 26 true universals:

### 🟢 Onboarding bucket — 10 universal fields
Collected ONCE on seller profile, auto-filled per product:
- Manufacturer Name / Address / Pincode (3)
- Packer Name / Address / Pincode (3)
- Importer Name / Address / Pincode (3)
- Country of Origin (1)

### 🔵 Catalog wizard bucket — 16 universal fields
Collected per product:
- Product Name, Variation, Meesho Price, MRP, Net Weight, Inventory, Generic Name
- Brand, Brand Name, Group ID, SKU ID, Product ID/Style ID, Product Description
- Image 1, 2, 3, 4

### Plus per category: variable-count category-specific fields
- B1 (Women Fashion): up to 21 additional fields per leaf (e.g. Sarees adds Pallu, Border, Drape Style…)
- B2 (Men Fashion): up to 17 additional fields per leaf (e.g. Shirts add Chest Size, Sleeve Styling, Fit…)

→ A Tirupur Men Fashion seller types **10 fields ONCE at onboarding, then 16 + (up to 17 category-specific) per product**. With AI auto-fill (guardrailed to enum lists), manual input drops to ~5–8 per product.

---

## 7. Dropdown size distribution (Batch 2)

### Dropdowns with ≥ 100 values
| Field | Max in B2 | Notes |
|---|---|---|
| Brand | 3,210 | API-resolved picker |
| Foot Length Size | 251 | Same pattern as B1 |
| Group ID | 200 | Universal — unclear purpose |
| Country of Origin | 194 | Onboarding bucket |
| Chest Size | 122 | NEW in B2 |
| Length Size | 121 | |
| Shoulder Size | 121 | |
| Product Weight | 106 | |
| Originals | 102 | NEW in B2 |
| Foot Width Size | 101 | |
| Waist Size | 100 | |

11 dropdowns ≥ 100 in B2 alone (vs 15 in B1). Pattern is consistent.

---

## 8. Image rules — uniform across BOTH batches

100% of 106 leaves in Batch 2 have exactly **4 image slots, only Image 1 (Front) compulsory** — identical to Batch 1. Confirmed across 285 leaves now. Image UI is permanently solved for V1.

---

## 9. Template-vs-leaf deduplication

**105 distinct templates serve 106 leaves** in Batch 2 (1 leaf shares a template with another). Same pattern as Batch 1 (169 for 179). Decision #7 (schema-by-template, not by-leaf) is reinforced. Estimated savings for full corpus: ~95-97% storage retention; dedup factor ~3-5%.

---

## 10. Anomalies / parser warnings (Batch 2)

- **Zero parse failures.** All 106 files parsed cleanly.
- Zero parser anomalies in the output JSON.
- Parser v0.1 unchanged — heuristics generalised perfectly from Batch 1's Women Fashion to Batch 2's Men Fashion. Strong sign the schema is corpus-wide stable.
- Known carry-over: `MRP` and `Inventory` still typed as `text` (semantically `number`). Will fix in v0.2 with a name-pattern override in `infer_data_type`.

---

## 11. Suggested discussion points (Batch 2's contribution to MVP)

1. **TRUE universals are stable at 26.** Two batches in, the core hasn't shrunk. Reasonable to start designing the universal section of the wizard now, in parallel with continuing batches.

2. **Brand pattern generalises to 82 fields.** The input primitive library auto-classifies by `enum_count` — no manual rules per field. This data-driven mapping is now the law of the renderer.

3. **Recommended tier confirmed absent (285/285 leaves).** Decision #3 holds. Two-tier form is final.

4. **Median compulsory ~ 28 across batches.** If this holds through Batch 12, the wizard will need to accommodate **28 ± 5 compulsory fields per category** as the default expectation. Multi-step wizard structure plan: 6 steps × ~5 fields each, with onboarding-filled compliance step hidden by default.

5. **Group ID is universal but its purpose is opaque** (dropdown, 30-200 values, always optional). Recommend: hide from V1 wizard with a "show advanced" toggle. Revisit if Batches 3-12 give clarity.

6. **"Originals" and "Waterproof" are NEW universals-in-niche** for menswear** — boolean-like dropdowns. The primitive library needs a `yes_no_dropdown` primitive distinct from "small dropdown" (better UX as toggle/checkbox).

7. **`-Dad` suffixed fields** (Length Size - Dad, Chest Size - Dad) suggest Meesho has a parent-child SKU pattern. Out of scope for V1 but worth noting for V2 variant matrix work.

8. **Cross-batch field analysis (the "Brand pattern" map) is now valuable data on its own.** Suggest we publish it as `data/parsed/cross_batch/field_enum_variance.json` after every batch so the frontend renderer can ingest it as the runtime decision table.

---

## 12. Cross-batch cumulative stats (B1 + B2 combined)

| Metric | B1 | B2 | Cumulative |
|---|---|---|---|
| Leaves parsed | 179 | 106 | **285 / 3,772 (7.6%)** |
| Failed | 0 | 0 | 0 |
| Templates | 169 | 105 | 273 distinct |
| Total unique field names | 359 | 223 | **408 unique cumulative** (174 shared) |
| True universals (in all batches) | — | — | **26** |
| Recommended-field instances | 0 | 0 | **0** |
| Image rule "4 slots, 1 compulsory" | 100% | 100% | **100%** |
| Median compulsory per leaf | 28 | 27 | 27–28 |
| Fields with variable enum size | — | — | **82** |

---

## 13. Next steps

- **Founder review of this Batch 2 draft.** Note differences from Batch 1; accept / reject Batch 2 contributions to MVP design.
- **At laptop:** sit together and write the first integrated SSoT entry covering **Batches 1 + 2 combined** in `docs/MEESHO_CATEGORY_INTELLIGENCE.md`.
- **Workspace agent fix:** the agent isn't just hook-blocked — it's **not registered** in Claude Code's subagent discovery at all (confirmed by Agent tool error: "Agent type 'meesell-xlsx-parser' not found"). Hook fix alone won't be enough. The evening reminder prompt may need updating.
- **Batch 3:** Kids & Toys (super_id=13, 284 leaves) — likely surfaces age/safety attributes not seen in B1/B2.
