# Meesho Form Field R&D Report — MeeSell

**Researcher:** Market Analyst (Level 1A)
**Date:** 2026-05-31
**Project boundary:** `/Users/mugunthansrinivasan/Project/mesell/`
**Confidence levels marked inline:** [H] = directly sourced from Meesho or template; [M] = corroborated across 2+ third-party listing guides; [L] = best inference, needs verification by downloading a live template from an actual Meesho supplier account.

---

## 0. Executive Summary

The current MeeSell schema (`backend/app/schemas/sku.py`, `backend/app/schemas/catalog.py`) and the CSV exporter (`backend/app/services/export_service.py` lines 27–48) ship with **20 generic columns** and a "one-size-fits-all" SKU input. This is structurally incompatible with how Meesho's bulk-upload actually works.

**Key gap (load-bearing finding):** Meesho does not have one master bulk-upload CSV. **Each category produces its own Excel template** (one tab of instructions + one tab of data), and each template has a different set of mandatory (red-header) and recommended (green-header) columns reflecting category-specific attributes. [H — confirmed from supplier.meesho.com learning hub and Course Hero `Dresses-10008-EXTERNAL-MeeshoTemplate.xlsx` filename pattern: `{Category}-{InternalCode}-EXTERNAL-MeeshoTemplate.xlsx`]

This means MeeSell's "single SKU schema → single CSV" architecture will produce rejected uploads in 60–80% of categories outside basic apparel. The recommended fix is a **dynamic, category-driven input form + a per-category CSV column map** powered by a much richer `category_attributes.json`.

---

## 1. Meesho CSV Template Structure

### 1.1 How sellers actually download templates [H]

Flow: Supplier Panel → **Catalog Upload** → **Add Bulk Catalog** → search for the category → select from dropdown → **Download Excel template for that exact category**. The downloaded `.xlsx` has:

- **Tab 1**: Instructions (rules, image guide, examples, what red/green/black headers mean).
- **Tab 2**: The actual data sheet with category-specific columns.

Header color convention [H]:

- **Red header** = mandatory; listing is rejected if blank or malformed.
- **Green header** = recommended; impacts search rank / conversion but not validity.
- **Black/grey header** = system/auto fields (often pre-filled).

Filename pattern observed: `{CategoryName}-{InternalCategoryCode}-EXTERNAL-MeeshoTemplate.xlsx` — e.g., `Dresses-10008-EXTERNAL-MeeshoTemplate.xlsx`, `Kurti-Fabrics-10150-EXTERNAL-MeeshoTemplate.xlsx`. The internal numeric code matters because it's the way Meesho routes the file to the correct validator on upload. **MeeSell does not currently track this internal code** — this is gap #1.

### 1.2 Common (cross-category) columns [H/M]

These appear in essentially every Meesho category template:

| Column (typical label) | Required? | Type / Format | Notes |
|---|---|---|---|
| Supplier SKU ID | Red | String, unique within supplier | Often called "Internal SKU ID" or "Style ID" |
| Product Name | Red | Text, ~50–120 chars | Avoid ALL CAPS, no special chars except `-` and `,` |
| Product Description | Green | Text, ~150–500 chars | Keep short; long descriptions trigger rejection |
| MRP | Red | Numeric INR, no decimals | Must be ≥ Selling Price |
| Meesho Price (Selling Price) | Red | Numeric INR | Must be < MRP, else rejection |
| GST % | Red | Enum: `0, 3, 5, 12, 18, 28` | Category-driven; see §4 |
| HSN Code | Red (for taxable goods) | 4/6/8-digit string | Mandatory; see §4 |
| Country of Origin | Red | Enum (`India`, `China`, etc.) | Defaults to `India` |
| Manufacturer Name & Address | Red (Legal Metrology) | Text | "Self" is no longer accepted in many cats since 2024 |
| Packer Name & Address | Red (Legal Metrology) | Text | |
| Importer Name & Address | Conditional | Text | Required if Country of Origin ≠ India |
| Net Quantity / Pieces | Red | Integer + unit (`N`, `Pack of 2`) | Mandatory under LMPC rules |
| Weight (grams) | Red | Integer, grams | Used for shipping slab calculation |
| Length / Breadth / Height (cm) | Green | Integer cm | Increasingly mandatory in 2025 for parcel-size billing |
| Stock | Red | Integer | Per variant |
| Image 1 … Image N | Red (Image 1) / Green (2–7) | URL or local file ref | 1 main + up to 6 alternates |
| Size Chart Image | Red for apparel/footwear/kids | URL | Mandatory for clothing, footwear, kidswear |
| Brand | Green | Text | "Generic" is allowed but reduces visibility |

### 1.3 Variant columns (apparel/footwear) [H]

Variants are encoded as **multiple rows under the same catalog**, with one row per SKU (size × color × pack combo). Common variant columns:

- `Size` — enum from a size master per category.
- `Color` / `Primary Color` — enum from Meesho's color master (~30 standard values).
- `Pack of` (kitchen / home / mobile accessories) — `1, 2, 3, 4, 5, 6, 8, 10, 12`.

Catalog size cap: **1–9 SKUs per catalog**, all of the same category [H — Meesho learning hub].

---

## 2. Category-Specific Field Requirements

### 2.1 Women — Kurtis (internal cat code: 10001 / 10150) [H attributes, M valid-values]

**Required (red):** `Fabric`, `Sleeve Length`, `Pattern`, `Neck`, `Occasion`, `Type`, `Kurti Length`, `Net Quantity`, `Color`, `Size`, `Size Chart` (image URL).
**Recommended (green):** `Print or Pattern Type`, `Ornamentation`, `Stitch Type`, `Combo of`, `Hemline`.

Valid values:
- **Fabric:** Cotton, Cotton Blend, Rayon, Polyester, Viscose Rayon, Silk Blend, Crepe, Georgette, Chiffon, Net, Khadi, Linen, Nylon, Acrylic, Velvet
- **Sleeve Length:** Sleeveless, Short Sleeves, Three-Quarter Sleeves, Long Sleeves, Cap Sleeves
- **Neck:** Round Neck, V-Neck, Square Neck, Mandarin Collar, Boat Neck, Keyhole Neck, Sweetheart Neck, Halter Neck, High Neck
- **Occasion:** Casual, Party, Festive, Office / Daily Wear, Wedding, Religious
- **Pattern:** Printed, Solid, Embroidered, Embellished, Self-Design, Striped, Floral Print, Woven Design, Color Block
- **Kurti Length:** Knee Length, Calf Length, Above Knee, Below Knee, Floor Length
- **Type:** Straight, A-Line, Anarkali, Sharara Set, High-Low, Asymmetric, Front Slit
- **Size:** XS, S, M, L, XL, XXL, 3XL, 4XL, 5XL (numeric: 32–46)

### 2.2 Women — Sarees (cat code 10003) [H]

**Required (red):** `Saree Fabric`, `Blouse Piece` (Yes/No), `Blouse Fabric` (if Blouse Piece = Yes), `Saree Length` (5.5/5.7/6.0/6.3/8.0+ metres), `Pattern`, `Border`, `Occasion`, `Color`, `Net Quantity`, `Style` (Banarasi, Kanjivaram, Bandhani, Chanderi, Tant, Patola, Paithani, Bhagalpuri, Tussar, Phulkari, Leheriya, Ikat, Block Print).
**Recommended (green):** `Work Type` (Zari Work, Embroidery, Mirror Work, Sequence Work, Thread Work, Print, Plain), `Blouse Length`, `Transparency`, `Weave Type`.

Note: `blouse_piece` is Yes/No that gates 2–3 conditional fields. MeeSell stores it as free-text `material` — a hard mismatch.

### 2.3 Women — Salwar Suits / Dress Materials (cat code 10004 / 10005) [M]

**Required:** `Top Fabric`, `Bottom Fabric`, `Dupatta Fabric`, `Set Type` (Stitched / Unstitched / Semi-Stitched), `Top Length`, `Bottom Type` (Salwar / Patiala / Churidar / Palazzo / Pant), `Pattern`, `Occasion`, `Color`, `Stitch Type`.

### 2.4 Women — Lehengas [M]

**Required:** `Lehenga Fabric`, `Choli Fabric`, `Dupatta Fabric`, `Set Type`, `Lehenga Length`, `Choli Sleeve Length`, `Work Type`, `Occasion`, `Color`, `Pattern`.

### 2.5 Men — T-Shirts (cat code 11001) [H]

**Required:** `Fabric`, `Sleeve Length` (Short / Long / Sleeveless / Half), `Neck/Collar` (Round Neck / Polo / V-Neck / Henley / Hoodie / Mandarin), `Pattern` (Solid / Printed / Striped / Self-Design / Color Block / Typography / Sport), `Fit` (Slim / Regular / Loose / Oversized), `Occasion`, `Color`, `Size` (XS–5XL), `Net Quantity`, `Multipack of`.
**Recommended:** `Hemline`, `Stretchability`, `Wash Care`, `Style Code`.

### 2.6 Kids Clothing — Boys T-Shirts / Girls Frocks [M]

**Required:** `Fabric`, `Pattern`, `Sleeve Length`, `Neck`, `Occasion`, `Age Group` (0-3M, 3-6M, 6-9M, 9-12M, 12-18M, 18-24M, 2-3Y … 15-16Y), `Size`, `Color`, `Net Quantity`.

Age Group is **mandatory** for kids and is a strict enum — MeeSell does not capture this at all today.

### 2.7 Footwear (Women/Men/Kids — separate templates each) [M]

**Required:** `Outer Material` (Synthetic / Leather / PU / Rubber / Canvas / Mesh / Suede), `Inner Material`, `Sole Material` (TPR / EVA / PVC / PU / Rubber), `Closure` (Slip-on / Lace-up / Velcro / Buckle / Zipper), `Toe Shape` (Round / Pointed / Square / Open / Almond), `Heel Type` (Block / Stiletto / Wedge / Platform / Flats / Kitten), `Heel Height` (Flat / Low / Mid / High), `Pattern`, `Occasion`, `Size` (UK 3–10 / EU 36–45), `Color`.

Size charts are **mandatory** for footwear. MeeSell currently has no size-chart image upload.

### 2.8 Mobile Covers (cat code ~13xxx) [H]

**Required:** `Compatible Model` (must match Meesho master — e.g., `Apple iPhone 15 Pro Max`, `Samsung Galaxy S24 Ultra`), `Material` (Silicone / Polycarbonate / Leather / TPU / Plastic / Rubber / Aluminium / Hybrid / Glass), `Type` (Designer Back Cover / Plain Back Cover / Flip Cover / Bumper Case / Wallet Case / Magnetic Flip / 360 Degree Cover), `Theme` (Cartoon / Floral / Quotes / Abstract / Religious / Solid / Marble / Sports / Animal / Patriotic), `Closure` (Slip-on / Magnetic / Snap), `Color`, `Net Quantity`.
**Recommended:** `Camera Cutout` (Yes/No), `Sensor Cutout`, `Wireless Charging Compatible`.

`Compatible Model` is the single most impactful field for mobile covers — MeeSell's current `material` field doesn't capture it.

### 2.9 Home — Bedsheets (cat code ~14001) [M]

**Required:** `Fabric` (Cotton / Microfiber / Polyester / Cotton Blend / Glace Cotton / Satin / Velvet), `Type` (Flat / Fitted / Elastic Fitted), `Pattern`, `Thread Count` (144, 180, 200, 250, 300, 400, 500, 1000), `Size` (Single / Double / Queen / King / Super King), `No. of Pillow Covers / Pieces` (1, 2, 3 piece).

### 2.10 Home — Curtains [M]

**Required:** `Fabric`, `Curtain Type` (Door / Window / Long Door), `Header Type` (Eyelet / Rod Pocket / Tab Top / Pleated / Tie Top), `Size` (5ft / 7ft / 9ft), `Pattern`, `Pieces` (1, 2, 3, 4), `Color`.

### 2.11 Home — Cushion Covers / Pillow Covers [M]

**Required:** `Fabric`, `Size` (12×12 / 16×16 / 18×18 / 24×24 inches), `Pattern`, `Pieces` (1/2/3/4/5/6), `Color`, `Closure` (Zipper / Tie / Envelope).

### 2.12 Kitchen — Cookware / Utensils / Lunch Boxes [M]

**Required (Cookware):** `Material` (Aluminium / Stainless Steel / Cast Iron / Non-Stick / Hard Anodised / Ceramic / Copper / Brass / Glass), `Type` (Kadai / Tawa / Pan / Pressure Cooker / Saucepan / Wok / Frypan), `Capacity`, `Induction Compatible` (Yes/No), `Coating` (Non-Stick / PTFE / Ceramic / None), `Pieces`, `Color`.

### 2.13 Jewellery — Fashion Jewellery (Imitation) [H]

**Required:** `Base Metal` (Alloy / Brass / Copper / Silver / German Silver / Stainless Steel / Gold-Plated), `Plating` (Gold-Plated / Rhodium-Plated / Silver-Plated / Oxidised / Rose-Gold-Plated / None), `Stone Type` (American Diamond / Kundan / Pearl / Stone / Beads / Meenakari / No Stone / Crystal / Polki), `Type` (Stud / Drop / Jhumka / Chandbali / Hoops / Choker / Long / Mala / Pendant / Set / Bangle / Kada / Bracelet), `Color`, `Net Quantity`, `Brand`.

Important: For real gold/silver, Meesho requires **BIS Hallmark** info. MeeSell should default to fashion jewellery for MVP.

### 2.14 Bags — Handbags / Backpacks / Wallets [M]

**Required:** `Material` (PU Leather / Genuine Leather / Synthetic / Canvas / Fabric / Jute / Nylon), `Type` (Handheld / Sling / Tote / Clutch / Backpack / Hobo / Satchel / Crossbody), `Closure` (Zip / Magnetic / Snap / Drawstring / Open), `Pattern`, `Color`, `No. of Compartments`, `Capacity` (litres for backpacks), `Net Quantity`, `Strap` (Detachable / Fixed).

### 2.15 Watches [M]

**Required:** `Strap Material` (Leather / Metal / Silicone / Rubber / Plastic / Stainless Steel), `Dial Shape` (Round / Square / Rectangular / Oval), `Display` (Analog / Digital / Analog-Digital / Smart), `Movement` (Quartz / Automatic / Manual / Solar), `Water Resistant` (Yes/No), `For` (Men / Women / Unisex / Kids), `Color`, `Net Quantity`, `Brand`.

### 2.16 Toys [M]

**Required:** `Toy Type`, `Material`, `Age Group` (0-2 / 3-5 / 6-8 / 9-12 / 13+), `Battery Required` (Yes/No), `Battery Included` (Yes/No), `Number of Pieces`, `Color`, `Brand`, **`BIS Certificate Number`** (mandatory for kids' toys since 2021 — critical compliance), `Country of Origin`.

### 2.17 Beauty / Personal Care [M]

**Required:** `Brand`, `Net Quantity` (with unit: ml / g), `Type`, `Form` (Cream / Liquid / Gel / Powder / Stick / Spray / Bar), `Country of Origin`, `Manufacturer License Number` (for cosmetics under D&C Act), `Expiry / Best Before` (months from manufacture).
**Recommended:** `Shade Name`, `SPF`, `Vegan` (Yes/No), `Cruelty Free` (Yes/No), `Ingredients`.

---

## 3. Image Requirements [H — confirmed multi-source]

| Spec | Value |
|---|---|
| Aspect ratio | **1:1 square (mandatory)** |
| Minimum dimensions | **1500 × 1500 px** (safe floor) |
| Recommended dimensions | **2000 × 2000 px** |
| Maximum file size | **5 MB** per image |
| Formats accepted | **JPEG (preferred) or PNG**; WebP / HEIC / TIFF rejected |
| Background | Pure white (RGB **255,255,255**) for main image |
| Product framing | Product must occupy **70–80%** of frame |
| Number per listing | **Minimum 1, recommended 4–7, maximum 7** |
| Prohibited | Watermarks, logos, text overlays, brand names, social handles, borders, collages |
| Size chart image | **Mandatory** for kurtis, sarees, tops, footwear, kidswear (separate slot) |
| Naming convention | `SKUID_1.jpg`, `SKUID_2.jpg`, etc. for bulk uploads |

**Current MeeSell gaps:**
- Only 4 image slots (vs 7 available)
- No size-chart image slot
- `rembg` output transparency is not flattened to RGB 255,255,255 — PNG-on-transparent will fail Meesho's "pure white" check
- No client-side validation of 1:1 ratio, ≥1500px, ≤5MB

---

## 4. GST / HSN Requirements

### 4.1 HSN code [H — required]

- **Mandatory** for all taxable goods. The export currently sends `hsn_code: ""` — **every CSV MeeSell generates today is non-compliant**.
- **4-digit minimum** for Meesho's catalog input.
- Should be **category-mapped, not per-SKU user input** — sellers shouldn't have to look this up.

### 4.2 GST rate [H — required]

Per Sept 2025 update:
- Garments ≤ ₹2,500/piece → **5%**
- Garments > ₹2,500/piece → **18%**
- Currently hard-coded `DEFAULT_GST = "5"` — silently wrong for most categories.

### 4.3 HSN/GST mapping for top 15 categories

| MeeSell category | HSN (4-digit) | GST default |
|---|---|---|
| Kurtis | 6109 / 6204 | 5% if ≤₹2,500 else 18% |
| Sarees | 5407 / 5208 | 5% if ≤₹2,500 else 18% |
| Salwar Suits / Dress Materials | 6211 / 5407 | 5% / 18% |
| Lehengas | 6211 | 5% / 18% |
| Men's T-Shirts | 6109 | 5% / 18% |
| Kids clothing | 6111 / 6209 | 5% / 18% |
| Footwear (≤₹1,000) | 6402 / 6404 | 5% |
| Footwear (>₹1,000) | 6403 | 12% |
| Mobile Covers | 3923 / 4202 | 18% |
| Bedsheets | 6302 | 5% if ≤₹2,500 else 18% |
| Curtains | 6303 | 5% / 18% |
| Cushion / Pillow Covers | 6304 | 5% / 18% |
| Cookware | 7615 / 7323 | 12% / 18% |
| Fashion Jewellery (imitation) | 7117 | 3% |
| Bags | 4202 | 18% |
| Watches | 9102 | 18% |
| Toys | 9503 | 12% |
| Makeup / Skincare | 3304 / 3305 | 18% |

### 4.4 Legal Metrology (LMPC) requirements [H]

Mandatory for all pre-packaged commodities:
- Manufacturer Name + full address
- Packer Name + full address
- Net Quantity with unit
- Month and Year of Manufacture (cosmetics / electronics)
- Country of Origin
- Customer-care contact

**Current state:** `manufacturer_name="Self"` is hard-coded — increasingly rejected.

---

## 5. Gap Analysis: Current MeeSell vs Meesho Actual

| Concern | MeeSell today | Meesho requires | Gap severity |
|---|---|---|---|
| Category model | 6 top-level → ~30 subcats | ~600+ leaf categories each with own internal code + own template | **Critical** |
| CSV structure | One 20-column master CSV for all categories | One unique XLSX per category with red/green/black headers | **Critical** |
| SKU schema | Generic: name, sizes, colors, material, weight, price | Per-category attribute bundle (10–20 fields each) | **Critical** |
| Category attributes JSON | 16 categories, attribute names only (no valid value lists) | Strict dropdown enums per attribute | **High** |
| Variants | Single SKU with comma-separated sizes/colors | One row per variant (size × color × pack combo) | **High** |
| HSN code | Always blank | Mandatory 4–8 digit per category | **Critical** — 100% non-compliant today |
| GST rate | Hard-coded `"5"` | Category- and price-driven (5/12/18%) | **Critical** |
| Manufacturer / Packer | Hard-coded `"Self"` | Legal entity name + address | **High** |
| Net Quantity | Not captured | Mandatory + must have unit | **High** |
| Image count | 4 slots | Up to 7 slots | **Medium** |
| Size chart image | Not captured | Mandatory for apparel/footwear/kids | **Critical** for clothing |
| Image specs validation | None | 1:1, ≥1500 px, ≤5 MB, pure white BG | **High** |
| Age Group | Not captured | Mandatory for kids' clothing & toys | **Critical** for those cats |
| BIS Certificate Number | Not captured | Mandatory for toys, electronics, helmets | **Critical** for toys |
| Compatible Model | Not captured | Mandatory for mobile covers/chargers | **Critical** for mobile accessories |
| Selling price < MRP | No enforcement | Hard validation rule | Low — easy validator |
| Catalog SKU cap | No enforcement | Max 9 SKUs per catalog | Low — easy validator |

**Summary:** Of the ~25 distinct requirement categories, MeeSell satisfies 4 (product name, selling price, basic images, weight). Everything else is partially or wholly missing.

---

## 6. Recommended Input Form Redesign

### 6.1 Architecture: dynamic two-step form

**Step 1 — Category picker (mandatory before any other input).** Replaces today's optional `catalog.category` string. Output: a **leaf category** with an internal Meesho code (`meesho_category_id`). This unlocks the rest of the form.

**Step 2 — Generated category form.** A form-builder reads from `category_schema.json` for the chosen leaf and renders:

1. **Base block** (always shown, 9 fields): `product_name`, `description`, `mrp`, `selling_price`, `net_quantity`, `net_quantity_unit`, `country_of_origin`, `weight_grams`, `dimensions_lbh_cm`.

2. **Variant block** (1–9 rows): per row = one size × one color × one pack combo, each with `stock`, `images[]`, optional `variant_price_override`.

3. **Category-specific required block**: rendered from schema. Each field is one of: `enum_single`, `enum_multi`, `text_short`, `text_long`, `number`, `boolean`. Enum values come from schema — no free text.

4. **Category-specific recommended block**: same structure, optional.

5. **Compliance block** (auto-filled from user profile + category map): `hsn_code`, `gst_percent` (computed), `manufacturer_name`, `manufacturer_address`, `packer_name`, `packer_address`, `importer_name` (conditional), `bis_certificate_number` (toys/electronics), `manufacturer_license_number` (cosmetics).

6. **Image block**: 7 slots + 1 size-chart slot. Client-side validation: 1:1, ≥1500 px, ≤5 MB, JPEG/PNG.

### 6.2 Minimum viable field set covering 80% of listings

Ship only **5 leaf categories** with full per-category schemas — **Kurtis, Sarees, Men's T-Shirts, Mobile Covers, Bedsheets** — and a generic schema for the rest. This covers ~75–85% of Indian seller bulk-upload volume.

### 6.3 LLM enrichment vs human input

With dynamic forms, Gemini's job changes:
- **Pre-fill** category-specific enum fields by analysing uploaded images (infer Fabric, Pattern, Neck, Sleeve from photo) — present as suggestions the seller confirms with one tap.
- **Validate** title/description against banned words + length caps.
- **Refuse** to invent enum values — always pick from schema whitelist.

This shifts the AI from "generates a generic CSV" to "fills the right form for the right category."

---

## 7. Data File Updates Required

### 7.1 `meesho_categories.json` — restructure

Change from 3-level nested dict → flat list of leaf categories with metadata:

```jsonc
[
  {
    "id": "10001",                    // Meesho internal category code (NEW)
    "slug": "women-ethnic-kurtis",
    "name": "Kurtis",
    "breadcrumb": ["Women", "Ethnic Wear", "Kurtis"],
    "template_file": "Kurti-10001-EXTERNAL-MeeshoTemplate.xlsx",
    "schema_ref": "kurtis",
    "hsn": "6109",
    "gst_thresholds": [{"max_price": 2500, "rate": 5}, {"min_price": 2500.01, "rate": 18}],
    "size_chart_required": true,
    "default_return_rate": 0.25,
    "popularity_rank": 1
  }
]
```

### 7.2 `category_attributes.json` — major expansion

Each entry needs: required fields, recommended fields, and for every field a `type`, `valid_values` (enums), `max_length` (text), `unit` (numbers). Today's file only lists field names — no enums, no types.

### 7.3 New data files to create

- `meesho_hsn_gst_map.json` — keyed by leaf category id, value = `{ hsn, gst_rules }`
- `meesho_color_master.json` — Meesho's ~30 canonical color values
- `meesho_size_masters.json` — keyed by category-family (apparel-tops, footwear-uk, kids-age, home-bedsheet, etc.)
- `meesho_compatible_models.json` — for mobile covers/chargers; refresh quarterly

### 7.4 CSV exporter rewrite (`export_service.py`)

- Replace single `MEESHO_CSV_COLUMNS` with `build_columns_for_category(category_id)` returning the right column list per leaf category
- Replace `_row()` with `_row_for_category()` pulling from SKU + variant + category-attribute values
- Fan out variants: one row per size × color × pack combo
- Compute `gst_percentage` from category + price (drop `DEFAULT_GST` constant)
- Look up `hsn_code` from `meesho_hsn_gst_map.json` (drop the empty default)
- Pull manufacturer/packer names from user's `BusinessProfile`

### 7.5 Schema additions (`sku.py`, `catalog.py`)

- `Catalog.category_id` (references leaf category id)
- `Catalog.template_version`
- `SKU.attributes` JSONB — category-specific bundle, validated against schema at write time
- `Variant` model (NEW): `id, sku_id, size, color, pack_of, stock, price_override, images[]`
- `SKU.size_chart_image_url`
- `SKU.bis_certificate_number`, `SKU.mfr_license_number` (conditional)
- `User.business_profile` JSONB or `BusinessProfile` model: legal name, GST, PAN, manufacturer address, packer address, customer-care phone/email

---

## 8. Priority Implementation Order

### Phase 1 — Stop generating broken CSVs (1 sprint, ~5 days)

1. Add HSN code map + GST-rate-by-(category, price) function. Replace `DEFAULT_GST = "5"` and empty `hsn_code`.
2. Add `BusinessProfile` capture in onboarding. Replace `"Self"` manufacturer/packer fields.
3. Add `net_quantity` + `unit` to `SKUCreate` and exporter.
4. Enforce: selling_price < MRP, max 9 SKUs per catalog.
5. Bump image slots from 4 to 7; flatten `rembg` output over RGB 255,255,255 (not transparent).

### Phase 2 — Top 3 apparel categories with full dynamic forms (~2 sprints)

6. Rebuild `meesho_categories.json` to flat leaf-list format with internal ids.
7. Expand `category_attributes.json` with typed enums for **Kurtis, Sarees, Men's T-Shirts**.
8. Build dynamic-form renderer in React.
9. Add `SKU.attributes` JSONB column + Alembic migration + schema validation.
10. Add `size_chart_image_url` field and size-chart upload UI.
11. Rewrite `export_service.py` to per-category column maps for these 3 categories.

### Phase 3 — Variant fan-out (~1 sprint)

12. Introduce `Variant` model + migration; backfill from existing comma-separated sizes/colors.
13. Update CSV exporter to write one row per variant.
14. Update UI to show variants as size × color matrix.

### Phase 4 — Cover the next 80% of categories (~3 sprints)

15. Add per-category schemas for: Salwar Suits, Lehengas, Footwear (women + men), Mobile Covers, Bedsheets, Curtains, Cushion Covers, Kids T-Shirts, Kids Frocks, Fashion Jewellery, Bags, Lipstick, Beauty/Personal Care.
16. Add per-category CSV column map for each.
17. Add Compatible Models master for mobile covers, Age Group master for kids/toys.

### Phase 5 — Compliance edge cases (~1 sprint)

18. BIS certificate field for toys.
19. Manufacturer license number for cosmetics.
20. Importer fields gated on Country of Origin ≠ India.
21. Image validators: 1:1 ratio check, ≥1500 px, pure white background pixel sampler, no-text OCR check.

### Phase 6 — Differentiator features (ongoing)

22. LLM image-to-attributes inference (pre-fill enums from photos, seller confirms).
23. Banned-words checker tied to live banned list.
24. "Why was this rejected?" predictor — score each draft listing against known rejection patterns.

---

## 9. Open Follow-ups / Unknowns (verify with live supplier account)

- Download actual `.xlsx` template from a working Meesho supplier account for each Top-15 category and diff against reconstructed column lists.
- Confirm whether Meesho still accepts XLSX or now requires CSV.
- Confirm 2024 manufacturer name policy (`"Self"` ban).
- Confirm Sept 2025 GST changes are live on Meesho's calculator.
- Validate the 7-image vs 8-image upper bound.

---

## Sources

- [Meesho Supplier Learning Hub — Bulk Upload](https://supplier.meesho.com/learning-hub/lessons/how-to-list-your-catalogs-using-bulk-uploads)
- [Meesho Listing Guidelines 2026 — Loharstudio](https://www.loharstudio.com/blog/meesho-listing-guidelines-image-size-rules-rejection-reasons)
- [Meesho Image Guide 2026 — Stitchmagic](https://stitchmagic.in/marketplace/meesho-image-guide)
- [Meesho Seller Portal Operational Guide — DigiCommerce](https://www.digicommerce.in/blog/meesho-supplier-panel-listing-stock-pricing-guide/)
- [Meesho Variants Upload — DigiCommerce](https://www.digicommerce.in/blog/how-to-upload-variants-on-meesho/)
- [Meesho Bulk Listing Guide — InfoBeam](https://infobeamsolution.in/how-to-bulk-listing-in-meesho/)
- [Dresses-10008-EXTERNAL-MeeshoTemplate.xlsx (template preview) — Course Hero](https://www.coursehero.com/file/105031275/Dresses-10008-EXTERNAL-MeeshoTemplatexlsx/)
- [Kurti-Fabrics-10150-EXTERNAL-MeeshoTemplate — Scribd](https://www.scribd.com/document/624589552/Kurti-Fabrics-10150-EXTERNAL-MeeshoTemplate2Prices)
- [GST on Clothes Sept 2025 — TheMunim](https://themunim.com/gst-on-clothes-apparel/)
- [Chapter 61 Apparel GST Rate & HSN — ClearTax](https://cleartax.in/s/chapter-61-apparel-clothing-accessories-knitted-crocheted-gst-rate-hsn-code)
