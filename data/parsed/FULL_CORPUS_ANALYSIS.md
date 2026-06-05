# Meesho Corpus — Full Analysis Across All 12 Batches

**Status:** Draft synthesis for founder + coordinator → SSoT (`docs/MEESHO_CATEGORY_INTELLIGENCE.md`)
**Coverage:** 3,772 / 3,772 leaves (100%) | 0 parse failures | Parser v0.2
**Date:** 2026-06-04

> This is the comprehensive integrated picture across the full corpus. The per-batch summaries (batch_NN_summary.md) cover deltas; this document is the **truth** that drives MVP architecture.

---

## 1. The Single Most Important Number

**1,831 unique field names exist across 3,772 leaves.**

This is far beyond what hand-coded form components can scale to. The data-driven input primitive library + canonical-name normalisation + schema-by-template are not optional — they are the only viable approach.

---

## 2. The TRUE Universal Core — 15 strict, 28 practical

### 15 fields are in 100% of all 3,772 leaves (strict universal)

**7 always-compulsory** (these MUST appear in V1 wizard for every product):
- Product Name
- Variation
- Meesho Price
- MRP
- Inventory
- Country of Origin
- Image 1 (Front)

**8 always-optional** (these always appear, always optional):
- Image 2 / Image 3 / Image 4
- Brand Name
- Group ID
- Product ID / Style ID
- SKU ID
- Product Description

### 13 more fields are in ≥99% of leaves (practical universal)

The 9-field compliance block (Manufacturer / Packer / Importer × Name/Address/Pincode) appears in **3,771 / 3,772 leaves**. The single missing leaf is Eye-Serum (id 12378), which uses a collapsed alternative ("Manufacturer Details" / "Packer Details" / "Importer Details" as single fields).

Plus: Net Weight (gms), Generic Name, Wrong/Defective Returns Price, Net Quantity (N).

**Practical universal set used for MVP design: 28 fields.**

---

## 3. The Two-Section Data Model (founder-locked) — concrete fields

### 🟢 Onboarding bucket (10 base + 5 conditional extensions)

#### Base — for every seller (10 fields)
| Field | Validation | Notes |
|---|---|---|
| Manufacturer Name | text | Legal Metrology Act |
| Manufacturer Address | textarea | |
| Manufacturer Pincode | text (6-digit) | |
| Packer Name | text | Often same as Manufacturer |
| Packer Address | textarea | |
| Packer Pincode | text (6-digit) | |
| Importer Name | text | Optional in some categories |
| Importer Address | textarea | |
| Importer Pincode | text (6-digit) | |
| Country of Origin | dropdown (~194 values) | |

**Alternate representation** (for legacy Eye-Serum-style templates):
- Manufacturer Details (combined)
- Packer Details (combined)
- Importer Details (combined, optional)

Backend stores both; frontend renders whichever format matches the selected category's template.

#### Conditional extensions (asked at onboarding if seller declares super-category)

| Super-category | Extension fields | Source evidence |
|---|---|---|
| **Grocery** | Seller FSSAI License Number | 321/321 Grocery leaves COMPULSORY |
| **Kids & Toys** | BIS/ISI Certification Number | 28/284 (optional, trust signal) |
| **Consumer Electronics** | BIS/ISI Cert + R Number + IS Number + CM/L Number | 20-112 leaves (regulatory IDs) |
| **Beauty & Health** | License/Registration Number + Type + Expiry Date | 15-20/341 (cosmetic/AYUSH) |
| **Books** | ISBN (optional declaration) | 163/493 (optional) |
| **Pet (food overlap)** | Reuses FSSAI from Grocery | 16 instances |
| **Home & Kitchen (appliances)** | License Number + Expiry Date | 6 instances |

**Seller profile schema:**
```sql
CREATE TABLE seller_profile (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  -- 10 base compliance fields
  manufacturer_name TEXT NOT NULL,
  manufacturer_address TEXT NOT NULL,
  manufacturer_pincode VARCHAR(6) NOT NULL,
  packer_name TEXT NOT NULL,
  packer_address TEXT NOT NULL,
  packer_pincode VARCHAR(6) NOT NULL,
  importer_name TEXT,
  importer_address TEXT,
  importer_pincode VARCHAR(6),
  country_of_origin VARCHAR(64) DEFAULT 'India',
  -- conditional compliance per super-category
  compliance_extensions JSONB DEFAULT '{}',
  -- e.g. {"grocery": {"fssai_license_number": "...", "fssai_expiry": "..."},
  --       "books": {"isbn_publisher_id": "..."}, ...}
  active_super_categories TEXT[],  -- which super-cats this seller sells in
  ...
);
```

### 🔵 Catalog wizard bucket — per-product

Universal core (16 fields → reduce to 7 typed + 9 auto-filled if pre-filled by AI):
- Product Name (text)
- Variation (dropdown)
- Meesho Price, MRP (currency-number)
- Net Weight (gms), Inventory, Net Quantity (number)
- Generic Name (dropdown)
- Brand (API-search picker, large enum)
- Brand Name (text — alternative for unbranded)
- Group ID (dropdown — purpose unclear, hide by default)
- SKU ID, Product ID / Style ID (text)
- Product Description (textarea)
- Image 1 (compulsory), Image 2/3/4 (optional)

Plus **category-specific extension** (variable count by leaf):
- Fashion (B1+B2): apparel sizing, fabric, pattern, neck/sleeve/fit (28 median compulsory)
- Kids & Toys (B3): age/safety attributes (24 median)
- Electronics (B4): warranty, model, voltage/wattage, compatible models (24 median)
- Home & Kitchen (B5): dimensions, weight units, materials (33 median — HIGHEST)
- Grocery (B7): veg/non-veg, shelf life, preservatives (23 median)
- Office Supplies (B8): paper specs (21 median)
- Sports & Musical (B9): skill level, sport specs (19 median — LOWEST)
- Beauty & Health (B10): concern, skin type, active ingredients (24 median)
- Books (B11): title, genre, author, format (Books-specific cluster)
- Long tail (B12): mobile specs, industrial products (19 median)

---

## 4. The 10 INPUT PRIMITIVES (data-driven library)

Auto-classified from `data_type` + `enum_count` + name patterns:

| Primitive | Classification rule | Examples |
|---|---|---|
| `text_short` | `data_type=text`, no name-pattern match | Product Name, Brand Name |
| `text_long` | name matches `*description`, `*notes`, `*ingredients` | Product Description, Active Ingredients |
| `number` | `data_type=number`, no unit suffix | Inventory, Pages |
| `number_with_unit` | numeric field with companion `*_unit` field OR name has unit keyword | Net Weight (gms), Voltage, Wattage, Packaging Weight + Packaging Weight unit |
| `currency` | name contains "price" or "mrp" | Meesho Price, MRP, Wrong/Defective Returns Price |
| `dropdown_small` | `enum_count` 1-20 | Veg/NonVeg, Organic, Boolean-style |
| `dropdown_medium` | `enum_count` 21-100 (in-memory Material autocomplete) | Color (some), Genre, Variation (some) |
| `dropdown_large` | `enum_count` 101-500 (virtualised autocomplete) | Length Size, Country of Origin |
| `dropdown_api_search` | `enum_count` >500 (backend API) | Brand (up to 3998), Compatible Models (up to 4481) |
| `image_upload` | `data_type=image_url` | Image 1, Image 2, Image 3, Image 4 |
| `address_group` | name pattern `*Details` (combined) | Manufacturer Details (Eye-Serum style) |

**10 primitive types cover 1,831 fields.** Decision #6 validates perfectly.

---

## 5. The Brand-Pattern Universe — 291 fields

**291 fields share names but have category-dependent enum sources.** Brand was just the first example; the pattern is pervasive.

Top 25 by max enum size:
| Field | Enum range | # instances |
|---|---|---|
| Brand | 1 – 3,998 | 3,731 |
| Compatible Mobiles | 48 – 1,775 | 3 |
| Model Name | 120 – 728 | 4 |
| Wattage | 1 – 500 | 130 |
| Voltage | 2 – 500 | 153 |
| Color | 2 – 237 | 1,728 |
| Variation | 1 – 205 | 3,772 |
| Type | 1 – 201 | 1,003 |
| Product Breadth/Height/Length | up to 326 each | 775-779 |
| Product Weight | 4 – 326 | 557 |
| Packaging Weight | 41 – 326 | 557 |
| Length Size | 10 – 321 | 193 |

**Backend implication:** dropdown enums for these 291 fields are stored per `(category_id, field_name)` in a `field_enum_values` table or join. They are NOT stored as global lists.

**API endpoint pattern:**
```
GET /api/v1/categories/{category_id}/field-enum/{field_name}?q=&page=
```

---

## 6. Form-length distribution (locked)

| Super-category cluster | Median compulsory |
|---|---|
| Home & Kitchen | 33 — **highest** |
| Women Fashion | 28 |
| Men Fashion | 27 |
| Auto/Pet/Books/Bags | 26 |
| Beauty & Health, Home & Living, Kids & Toys, Consumer Electronics | 24-25 |
| Grocery | 23 |
| Office Supplies | 21 |
| Sports & Musical | 19 — **lowest** |
| Long tail | 19 |

**Range: 19-33 compulsory median.** Wizard step count must be **data-driven** — not hard-coded.

Suggested step strategy:
- Steps = ceiling(category's compulsory count / 5)
- Min 3 steps, max 8 steps
- "Compliance" step (Manufacturer/Packer/Importer) is hidden by default — already filled from onboarding
- "Conditional extensions" step appears only if applicable per super-category

---

## 7. Confirmed corpus-wide invariants (these never change)

| Pattern | Status |
|---|---|
| Image rule: 4 slots, slot 1 compulsory | **100% uniform across 3,772 leaves** |
| Recommended Field marker | **0 instances anywhere in 3,772 leaves** (V1 stays two-tier) |
| 7 always-compulsory universals (Product Name, Variation, Meesho Price, MRP, Inventory, Country of Origin, Image 1) | **100% present, 100% compulsory** |

---

## 8. Canonical Field-Name Normalization Map (NEW deliverable)

Examples discovered across batches. The complete map must be built before backend seed:

| Canonical name | Variants discovered |
|---|---|
| Color | Color, Colour, Primary Colour, Secondary Colour, Bottom Color |
| Battery (presence) | Battery, Battery Required, Battery Available, Batteries Required, Batteries Included, Chargable, Battery Operated |
| Battery Type | Battery Type, Battery Composition |
| Brand | Brand, Brands, brand (lowercase) |
| Compatible Model | Compatible Model, Compatible Models, Compatible Mobiles, Compatible Devices |
| No. of Sheets | No. of Sheets, Number of Sheets, No. of Usable Sheets |
| Veg/Non-Veg | Veg/NonVeg, Veg/Non Veg |
| Manufacturer compliance | Manufacturer Name + Address + Pincode, Manufacturer Details |
| Packer compliance | Packer Name + Address + Pincode, Packer Details |
| Importer compliance | Importer Name + Address + Pincode, Importer Details |
| Net Weight | Net Weight (gms), Product weight (gms), Product Net Weight |
| Number of Cameras | No. of Primiary Cameras (typo!), No. of Seconadry Cameras (typo!) |
| Assembly Required | Assembly Required, Assembling Required |
| Warranty | Warranty, Warranty Period, Warranty Type, Warranty Duration Months, Warranty Service Type |
| License (cosmetic/AYUSH) | License/Registration Number, License Number, License/Registration No. |
| License Expiry | License Expiry Date (DD/MM/YYYY), License/Registration Expiry Date |

**Required deliverable:** `data/parsed/canonical_field_aliases.json` keyed by canonical name → list of variants. Build before backend seed.

---

## 9. MVP Architecture (data-grounded)

### Backend data model
```sql
-- Templates (deduplicated from leaves)
CREATE TABLE templates (
  id UUID PRIMARY KEY,
  hash TEXT UNIQUE,  -- hash of canonical schema for dedup
  schema_jsonb JSONB NOT NULL  -- the parsed schema
);

-- Categories (3,772 leaves, mapped many-to-one to templates)
CREATE TABLE categories (
  id UUID PRIMARY KEY,
  meesho_id VARCHAR(64) UNIQUE,
  super_category_id VARCHAR(8),
  path TEXT,
  template_id UUID REFERENCES templates(id),
  ...
);

-- Field enums (Brand-pattern fields — per category, per field)
CREATE TABLE field_enum_values (
  category_id UUID,
  field_name TEXT,  -- canonical name
  values_jsonb JSONB,  -- the enum list (or pointer to a global brand table)
  PRIMARY KEY (category_id, field_name)
);

-- Canonical field name aliases
CREATE TABLE field_aliases (
  variant_name TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL
);

-- Seller profile (Onboarding)
CREATE TABLE seller_profile (
  user_id UUID PRIMARY KEY,
  -- 10 base compliance fields (see Section 3)
  ...
  compliance_extensions JSONB DEFAULT '{}',
  active_super_categories TEXT[]
);
```

### Frontend architecture
- Component library: 10 input primitives (Section 4)
- Per-category wizard: composed from template schema at runtime
- Step count: data-driven from compulsory field count
- Onboarding: base 10 fields + conditional steps per declared super-category

### AI auto-fill (V1 Feature 4)
- Constrained to enum values where dropdowns exist (no hallucination — founder decision #4)
- For text fields, suggests from product description with confidence score
- Per-category prompt template includes the category's specific schema in compressed form

---

## 10. Eight founder decisions — STATUS AFTER FULL CORPUS

| # | Decision | Status after 3,772 leaves |
|---|---|---|
| 1 | Seller profile auto-fills compliance | ✅ Lock — 3,771/3,772 leaves use the 9-field pattern (Eye-Serum uses collapsed alt) |
| 2 | Brand picker is API-backed | ✅ Lock — 291 Brand-pattern fields, max enum 4,481 (Compatible Models, beats Brand!) |
| 3 | Two-tier form (Compulsory / Optional) | ✅ Lock — 0 Recommended-Field markers in 3,772 leaves |
| 4 | AI auto-fill enum-constrained | ✅ Lock — 291 dropdown fields confirm enum-only constraint critical |
| 5 | Wizard data-driven, not hard-coded | ✅ Lock — median compulsory varies 19-33 across super-categories |
| 6 | Input primitive library | ✅ Lock + extended — 10 primitives cover the corpus (Section 4) |
| 7 | Schema by template, not by leaf | ✅ Lock — 3,557 distinct templates serve 3,772 leaves (5.7% dedup) |
| 8 | Smart picker top-5 + manual browse | ✅ Lock — corpus has many near-duplicate categories |
| 9 | Conditional onboarding extensions | ✅ **STRONGLY LOCK** — 6 super-categories confirmed: Grocery+FSSAI (compulsory!), Kids+BIS, Electronics+R/IS/CM-L/BIS, Beauty+License, Books+ISBN, Appliances+License |
| 10 | Canonical field-name layer | ✅ **STRONGLY LOCK** — 16+ alias families discovered (Section 8) |

---

## 11. Open questions / Discussion points for founder

1. **Books ISBN is OPTIONAL** in Meesho's templates. Should V1 enforce ISBN-required for new sellers (more trust) or follow Meesho's lenient default?

2. **Eye-Serum's collapsed compliance ("Manufacturer Details" single field)** — is this a Meesho bug or a deliberate stripped flow? Worth user-testing with a beauty seller.

3. **Typos in Meesho's source** ("Primiary", "Seconadry"). Do we preserve verbatim for exact-match XLSX export OR auto-correct? Recommend: store both — `canonical_name` for display + alias map for round-trip to Meesho XLSX format.

4. **Group ID is universal optional, purpose opaque** (max 200 enum, always optional). Hide in V1 with "Advanced" toggle, surface in V1.5 after user research.

5. **Long-tail super-categories with <10 leaves** (Mobiles & Tablets = 2, Home Utility = 1) — should we ship V1 supporting them, or de-scope to keep wizard testing simpler? Recommend: include for completeness, since they reuse the same primitives.

6. **Warranty fields show 5 variants** across batches. Should warranty be an Onboarding question ("do you provide warranty as default?") OR per-product? Currently per-product in Meesho — recommend match Meesho's UX.

---

## 12. Numbers summary

| Metric | Value |
|---|---|
| Leaves parsed | 3,772 / 3,772 (100%) |
| Parse failures | 0 |
| Distinct templates | 3,557 (5.7% dedup) |
| Unique field names | 1,831 |
| TRUE universals (100% coverage) | 15 |
| Practical universals (≥99%) | 28 |
| Always-compulsory universals | 7 |
| Brand-pattern fields | 291 |
| Recommended-field marker instances | 0 |
| Image-rule canonical violations | 0 |
| Median compulsory range | 19 – 33 |
| Onboarding extensions confirmed | 6 (Grocery, Kids, Electronics, Beauty, Books, Appliances) |
| Canonical-name alias families discovered | 16+ |
| Input primitives needed | 10 |

---

This document is ready for founder review. After founder annotation, the accepted findings get integrated into `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (the SSoT) and `docs/MVP_ARCHITECTURE.md` (Phase 3 deliverable).
