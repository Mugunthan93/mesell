# Batch 1 — DRAFT findings (Women Fashion + Women)

**Coverage:** 179 / 179 (100%)
**Failed:** 0
**Date:** 2026-06-04 (parsed during morning IST session)
**Parser version:** 0.1
**Executed by:** meesell-data-engineer (coordinator) — second-level fallback after nexus:level-3:python-developer-agent stopped mid-recon after 28 tool calls. Memory continuity preserved in meesell-xlsx-parser/MEMORY.md with attribution.

> This is a DRAFT artifact for coordinator + founder discussion. Findings accepted from this discussion get integrated manually into `docs/MEESHO_CATEGORY_INTELLIGENCE.md`.

---

## 1. Field-count distribution across 179 leaves

| Metric | Compulsory | Recommended | Optional | Total |
|---|---|---|---|---|
| Min | 19 | 0 | 10 | 29 |
| Median | 28 | 0 | 14 | 42 |
| Mean | 27.7 | 0 | 14.7 | 42.5 |
| Max | 47 | 0 | 31 | 71 |

**Min compulsory leaf:** `11186` Women Trousers (19 compulsory, 32 total)
**Max compulsory leaf:** `10157` Lehenga (47 compulsory, 71 total)

**Compulsory-count distribution:**
| Bucket | Leaves | % |
|---|---|---|
| < 25 compulsory | 48 | 27% |
| 25–29 | 77 | 43% |
| 30–34 | 38 | 21% |
| 35–39 | 12 | 7% |
| 40+ | 4 | 2% |

→ **Even the lightest Women Fashion form has 19 compulsory fields.** No category in this batch is a "short form."

---

## 2. **CRITICAL FINDING:** Zero "Recommended" fields anywhere

Across all 179 leaves, **not a single field is marked `Recommended Field`**. Meesho's column-marker scheme in this batch is binary: `* Compulsory Field` or `Optional Field`.

The "Mandatory vs Recommended" pain mentioned in `VALIDATED_PAIN_POINTS.md` Theme 3 may apply to other categories — needs verification in Batches 2-12. **For Women Fashion + Women, V1 form rendering only needs two field tiers, not three.**

---

## 3. Universal fields — 26 fields present in ALL 179 leaves

### Always compulsory (18 fields)
| Field | Data type | Notes |
|---|---|---|
| Product Name | text | Core product identifier |
| Variation | dropdown | Up to 205 enum values across batch |
| Meesho Price | number | |
| MRP | text (but numeric) | |
| Net Weight (gms) | number | |
| Inventory | text (but numeric) | |
| Country of Origin | dropdown | Up to 194 enum values |
| Generic Name | dropdown | |
| Image 1 (Front) | image_url | Only image field that is compulsory |
| **Compliance block (9 fields, all text):** | | Legal Metrology Act requirement |
| Manufacturer Name | text | |
| Manufacturer Address | text | |
| Manufacturer Pincode | text | |
| Packer Name | text | |
| Packer Address | text | |
| Packer Pincode | text | |
| Importer Name | text | |
| Importer Address | text | |
| Importer Pincode | text | |

### Always optional (8 fields)
| Field | Data type | Notes |
|---|---|---|
| Image 2, 3, 4 | image_url | Total of 4 image slots, only #1 required |
| Product ID / Style ID | text | Seller-internal SKU |
| SKU ID | text | |
| Brand Name | text | Free-text variant (see also "Brand" dropdown below) |
| Group ID | dropdown | |
| Product Description | text | |

---

## 4. Near-universal fields (in 80–99% of leaves)

| Field | In | % | Compulsory | Notes |
|---|---|---|---|---|
| Wrong/Defective Returns Price | 178/179 | 99% | always optional | |
| Brand | 178/179 | 99% | always optional | **Up to 3,998 enum values** |
| Net Quantity (N) | 174/179 | 97% | always compulsory | |
| Color | 153/179 | 85% | 141 compulsory | Up to 178 enum values |

---

## 5. Batch-1-specific fields — 312 unique fields appearing in ≤30 leaves

**Total unique field names across batch: 359**

Selected niche fields with category clusters:
| Field | In N leaves | Cluster |
|---|---|---|
| Neck, Sleeve Styling, Fit/Shape, Stitch Type | 25–30 | Tops / Kurtis / Shirts |
| Sole Material, Heel Height, Heel Type, Toe Type, Ankle Height, CM/L Number, IS Number | 14–22 | Footwear (Bellies, Boots, Flipflops, Formal Shoes) |
| Base Metal, Stone Type, Plating | 16–17 | Jewellery (Anklets, Necklaces, Pendants) |
| Dupatta Fabric, Bottom Fabric, Bottom Length, Bottom Waist | 14–15 | Suits / Lehengas / Western Gowns |
| Waist Rise | 15 | Jeans / Jeggings / Briefs |
| Bust Size, Waist Size | up to 133 each as dropdowns | Sized apparel |
| Lehenga Waist Size, Dupatta Length, Blouse Length | 11–15 | Lehenga-specific |
| Saree Length, Border Type, Pallu | (needs explicit search) | Saree-specific |

→ Confirms the founder's intuition: each sub-category brings its own attribute vocabulary on top of the universal core.

---

## 6. Dropdown size distribution

### TOP 15 largest single dropdowns (BIGGEST MVP DESIGN ISSUE)

| Field | Max enum size | Sample leaf |
|---|---:|---|
| **Brand** | **3,998** | 10004 |
| Brand | 3,730 | 10003 (Sarees) |
| Brand | 3,102 | 10002 |
| Brand | 2,840 | 10265 |
| Brand | 2,373 | 10007 |
| Brand | 2,283 | 10008 |
| Brand | 2,027 | 10109 |
| Brand | 1,940 | 10253 |

→ **The Brand dropdown is so large that a native `<select>` is unusable. Need autocomplete with API-backed search + lazy load. Same field, wildly different enum lists per category (Sarees = 3,730 brands, but a niche category = 250 brands).**

### Other dropdowns with ≥100 values

| Field | Max | Type |
|---|---:|---|
| Product Weight | 326 | All packaging dimensions are 200+ enum dropdowns |
| Length / Width Size | 321 each | Apparel sizing |
| Silver Weight | 239 | Jewellery |
| Foot Length Size | 231 | Footwear |
| Variation | 205 | |
| Product / Packaging × Length/Breadth/Height | 201 each | 6 separate fields × 201 = lots of pickers |
| Group ID | 200 | |
| Country of Origin | 194 | |
| Color | 178 | |
| Packaging Weight | 159 | |
| Lehenga Waist Size | 134 | Lehenga-specific |
| Bust Size, Waist Size | 133 each | |
| Diameter, Height Size | 131 each | |
| Shoulder, Size Length, Dupatta Length, Blouse Length, Bottomwear Length | 126 each | |
| Lehenga Length Size | 121 | |
| Print or Pattern Type | 116 | |
| Gowns | 114 | |
| Foot Width Size | 101 | |
| Length In Inch, Weight In Gm | 100 each | |

→ Even ignoring Brand, the form has **15+ dropdowns with 100+ values**. A V1 form with naive native selects will be hostile on mobile. Need consistent search-pickers.

---

## 7. Image rules — REMARKABLY UNIFORM

**100% of 179 leaves have:** 4 image slots, only Image 1 (Front) is compulsory. Images 2, 3, 4 are optional. No category in this batch has unusual image rules.

→ The image-upload UI is the **simplest** part of the form. Build once, reuse across all 179 categories. No category-specific image logic needed.

---

## 8. Taxonomy oddity — 169 distinct templates serve 179 leaves

Only 169 unique main-sheet names across 179 leaves → **10 leaves share templates with other leaves**. This means the leaf taxonomy in `meesho_category_tree.json` is finer-grained than Meesho's actual XLSX template taxonomy.

Implication: when seeding the `categories` table, we may have rows that point to the same field schema. Worth deduplicating field-schema storage by template, not by leaf, to save space and stay DRY.

---

## 9. Anomalies / parser warnings

- **Zero parse failures.** All 179 files loaded and produced field records.
- Zero "Recommended Field" markers detected — parser handles this correctly; the data genuinely doesn't contain them.
- `Variation` shows enum=1 in some samples (e.g. Sarees probe) but up to 205 in others — Meesho uses the same field name with wildly different enum sources per category. The parser captures this faithfully; the *application* needs to handle that.
- `Brand` is a dropdown (always optional, 99% of leaves) AND `Brand Name` is a text field (always optional, 100% of leaves). Meesho ships both — unclear whether seller fills one, both, or either. Discussion point.
- `MRP` and `Inventory` are typed as `text` by the parser (no data validation rules detected) but their semantic data type is `number`. Heuristic could be improved with a name-pattern rule.

---

## 10. Suggested discussion points for founder + coordinator (MVP-shaping)

1. **Compliance auto-fill is P0.** The 9-field Manufacturer / Packer / Importer block (universal compulsory) is the same for every product a seller lists. Should be stored on `users` (or a `seller_compliance_profile` table) and auto-filled on every form. Without this, sellers re-type 9 fields × N products — pure waste. **Big Theme 2 (time) win.**

2. **Brand picker cannot be a native `<select>`.** Up to 3,998 values. Need backend endpoint `GET /api/v1/brands/search?q=<prefix>&category_id=<id>` returning paginated results. Frontend uses Angular Material autocomplete with debounced API calls.

3. **Form length is medium-to-long for EVERY category.** Lowest is 19 compulsory, median 28, max 47. Single-page long form will fatigue Tirupur mobile sellers. **Multi-step wizard** or **AI auto-fill** is not optional — it's load-bearing. Validates AI Auto-fill (V1 Feature 4) as P0.

4. **The Recommended/Compulsory pain mentioned in VALIDATED_PAIN_POINTS does not apply here.** This batch is binary. May still apply elsewhere — keep watch in Batches 2-12. Two-tier form UI is sufficient for Women Fashion.

5. **15+ dropdowns ≥100 values** → need one reusable "searchable picker" component, not 15 bespoke ones. Tailwind + Angular Material autocomplete with virtual scroll for size lists.

6. **Image UI is solved.** 4 slots, slot 1 required, slots 2-4 optional. Use the existing Feature 5 (Image Pre-check) design as-is. Don't over-engineer.

7. **Smart Category Picker accuracy threshold** (V1 Feature 2: ≥80% top-3 on 50-description golden set) is harder than it looks. The 179 Women Fashion + Women leaves include very similar pairs (Kurti, Kurti With Bottomwear, Kurtis, Suits, etc.) — disambiguation by description alone may struggle. Consider showing top-5 and letting user filter by sub-category breadcrumbs.

8. **Schema-storage strategy:** Store field schema as `categories.attributes_jsonb` keyed by template, not by leaf. Multiple leaves can share a template (proven: 10 do). Save space, avoid update skew.

---

## 11. Raw stats appendix

| Metric | Value |
|---|---|
| Total leaves parsed | 179 |
| Total field instances across batch | 7,599 |
| Total unique field names | 359 |
| Sum of max dropdown sizes (upper bound on unique enum values) | 17,264 |
| Number of distinct main-sheet templates | 169 |
| Parse failures | 0 |
| Parser anomalies | 0 |

---

## 12. Recommended next steps

- **Founder review of this draft** — accept / reject / annotate each finding
- After acceptance: coordinator + founder write `docs/MEESHO_CATEGORY_INTELLIGENCE.md` with the integrated findings
- Then: **fix the workspace agent-routing hook** (evening reminder at 7 PM IST) so `meesell-xlsx-parser` (the real specialist) takes over for Batch 2 onward, using the same parser script
- Batch 2 = Men Fashion (super_id 10, 106 leaves)
