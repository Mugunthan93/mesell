# MEESHO CATEGORY INTELLIGENCE — Single Source of Truth

**Status:** LOCKED  
**Date locked:** 2026-06-04  
**Authors:** meesell-data-engineer + founder (Mugunthan)  
**Derived from:** Full-corpus parse of 3,772 Meesho XLSX templates (`data/parsed/`) + 14 founder decisions  
**Drives:** backend data model, frontend primitive library, AI auto-fill strategy  

> This document is the authoritative reference for all MeeSell agents. When this document
> conflicts with any other file, **this document wins.** Agent memories, batch summaries, and
> draft analysis files are superseded by what is written here.
>
> To change anything in this document, the coordinator must present evidence and get explicit
> founder approval. Never edit silently.

---

## §1 — Scale & Scope

These numbers govern every architecture decision. They come from parsing all 3,772 leaves.

| Metric | Value |
|---|---|
| Meesho category leaves (total) | **3,772** |
| Parse failures | **0** |
| Distinct templates (after dedup) | **3,557** (5.7% dedup — schema stored by template, not by leaf) |
| Unique field names across corpus | **1,831** |
| TRUE universal fields (100% of all leaves) | **15** |
| Practical universal fields (≥99% of leaves) | **28** |
| Always-compulsory universal fields | **7** |
| Fields with category-dependent enum sources | **291** (the "Brand pattern") |
| `Recommended Field` marker instances | **0** (across all 3,772 leaves — V1 form is two-tier permanently) |
| `Compulsory Field` median range by super-category | **19 – 33** (data-driven wizard step count is mandatory) |
| Largest single field enum in corpus | **4,481** values (Compatible Models) |
| Second largest | **3,998** values (Brand — varies by category) |
| Image rule violations | **0** (4 slots, slot 1 compulsory — uniform across 3,772 leaves) |
| Canonical field-name alias families | **16+** |
| Onboarding compliance extensions confirmed | **6 super-categories** (Grocery, Kids, Electronics, Beauty, Books, Appliances) |
| Input primitive types needed to cover corpus | **10** |

**The single most important implication of 1,831 unique field names:** hand-coded form components do not scale. The data-driven primitive library + canonical-name normalisation + schema-by-template storage are non-negotiable architectural requirements, not optimisations.

---

## §2 — The 28 Practical Universals

Every product in every category has these fields. The V1 wizard always includes them.

### 7 always-compulsory (100% of 3,772 leaves, always compulsory)

These must appear in the wizard for every product, with no conditions.

| Field | Canonical name | Primitive |
|---|---|---|
| Product Name | `product_name` | `text_short` |
| Variation | `variation` | `dropdown_medium` (1–205 values, category-dependent) |
| Meesho Price | `meesho_price` | `currency` |
| MRP | `mrp` | `currency` |
| Inventory | `inventory` | `number` |
| Country of Origin | `country_of_origin` | `dropdown_large` (~194 values, global list) |
| Image 1 (Front) | `image_1` | `image_upload` |

### 8 always-optional (100% of 3,772 leaves, always optional)

These always appear in the wizard, always in the Optional tier.

| Field | Canonical name | Primitive |
|---|---|---|
| Image 2 | `image_2` | `image_upload` |
| Image 3 | `image_3` | `image_upload` |
| Image 4 | `image_4` | `image_upload` |
| Brand Name | `brand_name` | `text_short` (unbranded alternative to Brand picker) |
| Group ID | `group_id` | `dropdown_medium` (30–200 values, purpose opaque) — **show behind "Advanced fields" toggle** |
| Product ID / Style ID | `product_id` | `text_short` |
| SKU ID | `sku_id` | `text_short` |
| Product Description | `product_description` | `text_long` |

**Note on Group ID:** Appears in 100% of leaves, always optional, purpose is not documented by Meesho. Shown in V1 behind an "Advanced fields" toggle (founder decision #12). Seller's choice to expand it acknowledges they may not understand the field.

### 13 near-universal (≥99% of leaves — the 9-field compliance block + 4 others)

These appear in all but the Eye-Serum leaf (id 12378). V1 treats them as universal.

**9-field compliance block (auto-filled from seller profile):**
| Field | Canonical name | Primitive |
|---|---|---|
| Manufacturer Name | `manufacturer_name` | `text_short` |
| Manufacturer Address | `manufacturer_address` | `text_long` |
| Manufacturer Pincode | `manufacturer_pincode` | `text_short` (6-digit) |
| Packer Name | `packer_name` | `text_short` |
| Packer Address | `packer_address` | `text_long` |
| Packer Pincode | `packer_pincode` | `text_short` (6-digit) |
| Importer Name | `importer_name` | `text_short` |
| Importer Address | `importer_address` | `text_long` |
| Importer Pincode | `importer_pincode` | `text_short` (6-digit) |

**4 other near-universals:**
| Field | Canonical name | Primitive |
|---|---|---|
| Net Weight (gms) | `net_weight_grams` | `number_with_unit` |
| Generic Name | `generic_name` | `dropdown_medium` |
| Wrong/Defective Returns Price | `defective_returns_price` | `currency` |
| Net Quantity (N) | `net_quantity` | `number` |

**The Eye-Serum exception (leaf id 12378):** Uses collapsed compliance fields — `Manufacturer Details`, `Packer Details`, `Importer Details` — as single text fields instead of the standard 3-field blocks. Seller profile stores the 9 standard fields universally. The Export Adapter concatenates them into the combined format **only when generating an XLSX for Eye-Serum** (founder decision #14-revised). Frontend always renders 9 standard fields. See §6 for canonical alias mapping.

---

## §3 — Two-Section Data Model (founder-locked)

Every field in the Meesho corpus belongs to one of two buckets. This is a foundational architectural decision made after Batch 1 review and confirmed by the full corpus.

### 🟢 Onboarding bucket — collected once on seller profile, auto-filled into every product

#### Base onboarding fields (10 fields — every seller, every category)

These are collected during the onboarding wizard and stored on `seller_profile`. They are injected automatically into the catalog XLSX export for every product.

```
Manufacturer Name (text)
Manufacturer Address (textarea)
Manufacturer Pincode (6-digit text)
Packer Name (text)
Packer Address (textarea)
Packer Pincode (6-digit text)
Importer Name (text)               — optional; many domestic sellers are also importer
Importer Address (textarea)
Importer Pincode (6-digit text)
Country of Origin (dropdown ~194)  — default: India
```

**Listing is blocked until onboarding is complete.** Seller profile must have all compulsory fields before any catalog can be submitted for export.

#### Conditional compliance extensions (6 confirmed super-categories)

Asked at onboarding **only if** the seller declares they sell in that super-category. Stored in `seller_profile.compliance_extensions JSONB` keyed by super-category slug.

| Super-category (slug) | Extension fields | Required? | Evidence |
|---|---|---|---|
| `grocery` | `fssai_license_number`, `fssai_expiry` | **COMPULSORY** | 321/321 Grocery leaves |
| `kids_toys` | `bis_isi_certification_number` | Optional | 28/284 leaves (trust signal) |
| `consumer_electronics` | `bis_isi_certification_number`, `r_number`, `is_number`, `cm_l_number` | Optional | 20–112 leaves |
| `beauty_health` | `license_registration_number`, `license_registration_type`, `license_expiry_date` | Conditional (if seller has licensed product) | 15–20/341 leaves |
| `books` | `isbn` | Optional | 163/493 leaves (Meesho is lenient — follow Meesho) |
| `appliances` | `bis_isi_certification_number`, `license_registration_number`, `license_expiry_date` | Optional | 6 instances |
| `pet` (food overlap only) | Reuses `fssai_license_number` from `grocery` | Conditional | 16 instances |

**Seller profile schema (relevant columns):**
```sql
CREATE TABLE seller_profile (
  user_id                UUID PRIMARY KEY REFERENCES users(id),
  -- 10 base compliance fields
  manufacturer_name      TEXT NOT NULL,
  manufacturer_address   TEXT NOT NULL,
  manufacturer_pincode   VARCHAR(6) NOT NULL,
  packer_name            TEXT NOT NULL,
  packer_address         TEXT NOT NULL,
  packer_pincode         VARCHAR(6) NOT NULL,
  importer_name          TEXT,
  importer_address       TEXT,
  importer_pincode       VARCHAR(6),
  country_of_origin      VARCHAR(64) NOT NULL DEFAULT 'India',
  -- conditional compliance, keyed by super-category slug
  compliance_extensions  JSONB NOT NULL DEFAULT '{}',
  -- e.g. {"grocery": {"fssai_license_number": "12345678", "fssai_expiry": "2027-12-31"},
  --       "books":   {"isbn": "978-..."}}
  active_super_categories TEXT[] NOT NULL DEFAULT '{}',
  onboarding_complete    BOOLEAN NOT NULL DEFAULT FALSE,
  ...
);
```

### 🔵 Catalog wizard bucket — collected per-product in the creation wizard

**Universal catalog core (present in every wizard for every product):**

| Field | Notes |
|---|---|
| Product Name | Always compulsory |
| Variation | Category-dependent dropdown (1–205 values) |
| Meesho Price, MRP | Both always compulsory |
| Net Weight, Inventory, Net Quantity | Always compulsory |
| Generic Name | Always present |
| Brand | API-backed search picker (large enum, category-dependent — see §5) |
| Images (1–4) | Image 1 compulsory, 2–4 optional — uniform rule, all 3,772 leaves |
| Product Description, SKU ID, Product ID, Brand Name, Group ID | Always optional |
| 9-field compliance block | Auto-populated from seller profile; shown read-only in wizard |

**Category-specific extension (variable by leaf):**

The wizard appends category-specific fields after the universal core. Compulsory count varies:

| Super-category | Median compulsory | Notable category-specific fields |
|---|---|---|
| Home & Kitchen | **33** (highest) | Dimensions (L×W×H), material, number of pieces, warranty |
| Women Fashion | 28 | Fabric, pattern, neck type, sleeve type, fit, colour |
| Men Fashion | 27 | Same as Women Fashion + Chest Size, Waterproof, Number of Pockets |
| Auto/Pet/Books/Bags | 26 | Books: title, author, genre, format, language |
| Beauty & Health | 25 | Concern, skin type, active ingredients, net content |
| Home & Living | 25 | Colour, material, set/pack count |
| Kids & Toys | 24 | Recommended age, safety material, assembly required, BIS certification |
| Consumer Electronics | 24 | Warranty Type, model name, voltage/wattage, compatible models |
| Grocery | 23 | Veg/Non-Veg, shelf life, net content, preservatives, organic flag |
| Office Supplies | 21 | Paper weight, number of sheets, ruling type |
| Sports & Musical | **19** (lowest) | Sport-specific niche fields |
| Long tail | 19 | Mobile specs, industrial attributes |

**Wizard step count formula (data-driven, not hard-coded):**
```
steps = ceiling(category_compulsory_count / 5)
min_steps = 3, max_steps = 8
```
- Compliance step (auto-filled from profile) is hidden by default — collapses to a read-only summary.
- Conditional extension step (BIS/FSSAI etc.) appears only if the leaf's super-category has a confirmed extension and the seller declared that category.
- Warranty step appears conditionally for Electronics, Appliances, and Home & Kitchen subsets (~190 leaves total).

---

## §4 — 10 Input Primitives

These 10 primitive component types cover all 1,831 unique field names in the corpus. The frontend builds these 10 components once; the wizard composes them per-category schema at runtime.

| Primitive | Classification rule | UI component | Examples |
|---|---|---|---|
| `text_short` | `data_type=text`, no special name pattern | Single-line `<input>` | Product Name, Brand Name, SKU ID |
| `text_long` | name matches `*description`, `*notes`, `*ingredients`, `*details` | `<textarea>` | Product Description, Active Ingredients |
| `number` | `data_type=number`, no unit companion field | Numeric `<input>` | Inventory, Net Quantity, Pages |
| `number_with_unit` | Numeric field with a companion `*_unit` dropdown field, OR name contains unit keyword (weight, wattage, voltage, capacity, frequency, length, width, height) | Number input + unit dropdown pair | Net Weight (gms) + unit, Voltage + unit, Packaging Dimensions |
| `currency` | name contains `price`, `mrp`, `returns price` | Numeric `<input>` with ₹ prefix | Meesho Price, MRP, Wrong/Defective Returns Price |
| `dropdown_small` | `enum_count` 1–20 | Native `<select>` or segmented control | Veg/NonVeg, Organic (Yes/No), Colour Family |
| `dropdown_medium` | `enum_count` 21–100 | Angular Material autocomplete (in-memory) | Color (some categories), Genre, Country of Origin subset |
| `dropdown_large` | `enum_count` 101–500 | Virtualised autocomplete | Length Size (321), Country of Origin (194), Apparel sizes |
| `dropdown_api_search` | `enum_count` > 500 | API-backed search input with "request to add" escape hatch | Brand (up to 3,998), Compatible Models (up to 4,481) |
| `image_upload` | `data_type=image_url` | Drag-drop image tile | Image 1 (compulsory), Images 2–4 (optional) |

**Special composite: `address_group`** — used only by the seller profile onboarding wizard, not the per-product catalog wizard. Renders 3 standard fields (Name, Address, Pincode) as a labelled group. Not a catalog primitive.

**Classification rules applied at parse time.** Each field in `templates.schema_jsonb` carries its `primitive_type` tag. The frontend reads the tag; it never re-derives types at render time.

**The `number_with_unit` special case:** When a field like "Net Weight (gms)" appears alongside a dropdown companion like "Weight Unit", both are emitted together as a single `number_with_unit` primitive. The parser links them by `companion_field_name`. The wizard renders them as a coupled pair. If no companion exists, the unit is inferred from the field name (e.g., "gms").

---

## §5 — 291 Brand-Pattern Fields

**291 fields share the same name across categories but have category-specific enum sources.** Brand was the first example; the pattern is pervasive across the corpus.

### What this means

A field called "Color" in Sarees has 237 values. The same field "Color" in Mobile Covers has 17 values. They share a field name but the enum is not shared — it is bound to the specific category.

These fields cannot use a single global enum table. They require per-`(category_id, field_name)` storage.

### Top instances by maximum enum size

| Field | Max enum size | # leaves it appears in |
|---|---|---|
| Brand | 3,998 | 3,731 |
| Compatible Models / Mobiles / Devices | 4,481 | ~1,800 |
| Color / Colour | 237 | 1,728 |
| Variation | 205 | 3,772 |
| Type | 201 | 1,003 |
| Group ID | 200 | 3,772 |
| Length Size | 321 | 193 |
| Product Breadth / Height / Length | 326 each | 775–779 |
| Product Weight | 326 | 557 |
| Packaging Weight | 326 | 557 |

### Backend storage requirement

```sql
-- Enum values for Brand-pattern fields stored per (category, field_name)
CREATE TABLE field_enum_values (
  category_id   UUID    NOT NULL REFERENCES categories(id),
  field_name    TEXT    NOT NULL,   -- canonical name
  values_jsonb  JSONB   NOT NULL,   -- array of string values
  enum_count    INTEGER NOT NULL,   -- true size (may be truncated in values_jsonb for large enums)
  PRIMARY KEY (category_id, field_name)
);

CREATE INDEX idx_field_enum_values_category ON field_enum_values(category_id);
```

For large enums (`enum_count` > 500), `values_jsonb` stores only the first 500 values. The full list for Brand and Compatible Models is loaded on-demand from the category-specific XLSX data at seed time and served via paginated API.

### API pattern for large enums

```
GET /api/v1/categories/{category_id}/field-enum/{field_name}?q=<search_term>&page=1&limit=20
```

This endpoint is called by the `dropdown_api_search` primitive as the user types. Response:
```json
{ "values": ["Nike", "Adidas", ...], "total": 3998, "page": 1, "limit": 20 }
```

The "request to add" flow (when brand is not in the list) is a V1.5 feature — V1 shows a message: "Brand not listed? Contact support."

---

## §6 — Canonical Field-Name Alias Map

Meesho's XLSX templates contain spelling variants, synonyms, and deliberate typos. MeeSell uses canonical names internally and maps to Meesho's exact strings only at XLSX export time.

**Rule:** Frontend renders `canonical_name`. Backend stores `canonical_name`. XLSX Exporter has a reverse map `(category_id, canonical_name) → meesho_column_header` to reconstruct the exact string Meesho's upload validator expects.

**Typos are intentional in the export map.** Meesho's upload validator uses exact string matching. "Primiary" and "Seconadry" must be emitted verbatim.

### Alias families (16 confirmed)

| Canonical name | Meesho variants | Notes |
|---|---|---|
| `color` | Color, Colour, Primary Colour, Secondary Colour, Bottom Color | Positional variants retain distinct canonical names where semantics differ |
| `battery_required` | Battery, Battery Required, Battery Available, Batteries Required, Batteries Included, Battery Operated, Chargable, Chargeable | All mean "does product need/include batteries" — 8 variants |
| `battery_type` | Battery Type, Battery Composition | — |
| `compatible_models` | Compatible Model, Compatible Models, Compatible Mobiles, Compatible Devices | 4 variants; max enum 4,481 |
| `brand` | Brand, brand, Brands | Lowercase and plural variants from Home & Kitchen |
| `no_of_sheets` | No. of Sheets, Number of Sheets, No. of Usable Sheets | Office Supplies |
| `veg_nonveg` | Veg/NonVeg, Veg/Non Veg | Separator variant only |
| `manufacturer_block` | {Name + Address + Pincode × 3} OR Manufacturer Details (combined) | 3-field vs collapsed; see §2 Eye-Serum exception |
| `net_weight_grams` | Net Weight (gms), Product weight (gms), Product Net Weight | Capitalisation + phrasing variants |
| `no_of_primary_cameras` | **No. of Primiary Cameras** | Meesho typo — "Primiary" — preserve in export |
| `no_of_secondary_cameras` | **No. of Seconadry Cameras** | Meesho typo — "Seconadry" — preserve in export |
| `assembly_required` | Assembly Required, Assembling Required | Kids & Toys |
| `warranty_*` | Warranty, Warranty Period, Warranty Type, Warranty Duration Months, Warranty Service Type | **NOT collapsed** — 5 distinct fields with different semantics; rendered as a coordinated "Warranty" step group |
| `license_registration_number` | License/Registration Number, License Number, License/Registration No. | Beauty, Appliances |
| `license_expiry_date` | License Expiry Date (DD/MM/YYYY), License/Registration Expiry Date | Pairs with above |
| `fssai_license_number` | Seller FSSAI License Number | Grocery; compulsory |
| `bis_isi_certification_number` | BIS/ISI Certification Number, BIS Certificate Number | Kids, Electronics, Appliances |
| `cable_length` | Cable Length, Cable Length Size | Electronics accessories |

**Full machine-readable version:** `data/parsed/canonical_field_aliases.json`

### XLSX round-trip rule

```
Inbound (parse):    Meesho column header  →  canonical_name  →  store
Outbound (export):  canonical_name  →  lookup field_aliases table by (category_id, canonical_name)  →  emit original Meesho header verbatim
```

The `field_aliases` table in PostgreSQL has a `for_xlsx_export BOOLEAN` column. Rows with `for_xlsx_export = TRUE` are used by the Export Adapter. This is how "Primiary" and "Seconadry" survive the round-trip without appearing in the seller-facing UI.

---

## §7 — Onboarding Compliance Extensions

Six super-categories have regulatory fields that are seller-level (not per-product). These are collected once at onboarding and auto-injected into every product export for that super-category.

| Super-category | Meesho super_id | Extension fields | Required? | Evidence strength |
|---|---|---|---|---|
| Grocery | 26 | `fssai_license_number` (COMPULSORY), `fssai_expiry` (optional) | **Hard required** — block listing | 321/321 leaves (100% of Grocery corpus) |
| Kids & Toys | 13 | `bis_isi_certification_number` | Optional | 28/284 leaves |
| Consumer Electronics | 16 | `bis_isi_certification_number`, `r_number`, `is_number`, `cm_l_number` | Optional | 20–112 leaves each |
| Beauty & Health | 19/36/37/14/88/34 | `license_registration_number`, `license_registration_type`, `license_expiry_date` | Conditional (if licensed product) | 15–20/341 leaves |
| Books | 80 | `isbn` | Optional (follow Meesho's lenient default) | 163/493 leaves |
| Appliances | 17 | `bis_isi_certification_number`, `license_registration_number`, `license_expiry_date` | Optional | 6 instances |
| Pet (food overlap) | 75 | Reuses `fssai_license_number` | Conditional | 16 instances |

**Onboarding wizard behaviour:**
1. Seller declares which super-categories they sell in (`active_super_categories[]`).
2. Onboarding wizard shows the base 10 compliance fields.
3. For each declared super-category that has an extension, a conditional wizard step appears.
4. Extension data is stored in `seller_profile.compliance_extensions JSONB`.

**At export time:**
- For a product in `grocery`, the Export Adapter reads `compliance_extensions.grocery.fssai_license_number` and populates the "Seller FSSAI License Number" column.
- If the column is missing and it is compulsory, the export is blocked with a user-facing error: "Complete your FSSAI details in your seller profile first."

---

## §8 — Corpus-Wide Invariants

These facts are confirmed across all 3,772 leaves and will not change without a Meesho schema version change. They can be hardcoded as constants in the codebase — no need to re-derive per category.

| Invariant | Value | Confidence |
|---|---|---|
| Image slots per product | **4** (Image 1 compulsory, 2–4 optional) | 3,772/3,772 (100%) |
| `Recommended Field` marker instances | **0** | 3,772/3,772 (100%) |
| V1 wizard tier structure | **Two-tier only** (Compulsory / Optional) | Permanently locked |
| Product Name | Always compulsory | 3,772/3,772 |
| Variation | Always compulsory | 3,772/3,772 |
| Meesho Price | Always compulsory | 3,772/3,772 |
| MRP | Always compulsory | 3,772/3,772 |
| Inventory | Always compulsory | 3,772/3,772 |
| Country of Origin | Always compulsory | 3,772/3,772 |
| Image 1 (Front) | Always compulsory | 3,772/3,772 |
| XLSX sheet structure | 5 sheets: Instructions, `{Name}-Fill this`, Example Sheet, Validation Sheet, Return Reasons | Confirmed across all 12 super-category clusters |
| User-fillable columns start at | Column index 4 (columns 1–3 are ERROR STATUS, ERROR MESSAGE meta) | Uniform |

**Implication for implementation:** The backend seed script and the frontend wizard renderer can hardcode these invariants. If a future Meesho scraper run detects a violation (e.g. a new `Recommended` marker), it must surface it as a `SCHEMA_VERSION_CHANGE` alert and block the seed until the coordinator reviews.

---

## §9 — Locked Decisions Index

All 14 founder decisions, as of 2026-06-04 evening. For full rationale and implementation detail, see `docs/MVP_ARCHITECTURE.md`.

| # | Decision | Status | One-liner |
|---|---|---|---|
| 1 | Seller profile auto-fills compliance block | ✅ LOCKED | 3,771/3,772 leaves confirm the 9-field block; listing blocked until profile complete |
| 2 | Brand picker = API-backed autocomplete + "request to add" | ✅ LOCKED | 291 Brand-pattern fields; Compatible Models (4,481) beats Brand (3,998); `dropdown_api_search` primitive handles both |
| 3 | V1 form is two-tier (Compulsory / Optional only) | ✅ LOCKED | 0 Recommended-Field markers in 3,772 leaves — third tier does not exist in Meesho's corpus |
| 4 | AI auto-fill is enum-constrained, never free-text | ✅ LOCKED | 291 dropdown fields; AI suggests only from validated enum lists; 3-layer enforcement (prompt + frontend + backend) |
| 5 | Wizard step count is data-driven, not hard-coded | ✅ LOCKED | Compulsory median ranges 19–33; formula: `ceiling(compulsory_count / 5)`, min 3, max 8 |
| 6 | 10-primitive input component library | ✅ LOCKED | 10 types cover all 1,831 field names; each field tagged at parse time; frontend renders by tag |
| 7 | Schema stored by template, not by leaf | ✅ LOCKED | 3,557 distinct templates serve 3,772 leaves (5.7% dedup); `categories` table maps many-to-one to `templates` |
| 8 | Smart Category Picker returns top-5 + "browse manually" | ✅ LOCKED | Near-duplicate categories in Women Fashion confirm top-3 is insufficient; manual escape hatch required |
| 9 | Conditional onboarding extensions per super-category | ✅ LOCKED | 6 super-categories confirmed; `compliance_extensions JSONB` on seller_profile; Grocery FSSAI is compulsory |
| 10 | Canonical field-name normalisation layer | ✅ LOCKED | 16+ alias families; `field_aliases` table; round-trip XLSX export uses original Meesho headers verbatim |
| 11 | Books ISBN = optional (follow Meesho's default) | ✅ LOCKED | Do not enforce stricter than Meesho; reduce friction for casual book sellers |
| 12 | Group ID = "Advanced fields" toggle (not hidden, not default-visible) | ✅ LOCKED (revised) | Philosophy Pattern 5 — opt-in opacity; seller's choice to expand acknowledges they may not understand the field |
| 13 | Warranty = per-product wizard step, not onboarding | ✅ LOCKED | Conditional step for Electronics + Appliances + Home & Kitchen appliance subset (~190 leaves); matches Meesho UX |
| 14 | Eye-Serum compliance = collect 9 standard fields universally; Export Adapter concatenates to 3 combined fields only at XLSX export | ✅ LOCKED (revised) | No duplicate storage; seller_profile has only the 9 standard fields; cleaner UX; Export Adapter handles the transformation per-category via `compliance_shape` flag |

**Bonus locked decisions from CORE_PHILOSOPHY.md** (that shape implementation but are not numbered above):
- Meesho typos in field names ("Primiary", "Seconadry") are corrected in the UI; emitted verbatim in XLSX export via reverse alias map.
- `meesho_column_header` is never read by the frontend. Display layer reads `display_label`, `display_help`, `validation_message` (canonical, human-friendly).
- Wizard step names are plain English, never generated codes.
- AI fills never invent values — source and confidence are shown for every AI suggestion.
- The Export Adapter is the single join point between seller-friendly internal model and Meesho-faithful XLSX format.

---

*End of document. Version: 1.0 (2026-06-04 locked). Next update requires founder approval.*
