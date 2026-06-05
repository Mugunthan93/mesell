# MeeSell — MVP Architecture (Phase 3 deliverable)

**Status:** Draft — produced by `meesell-data-engineer` from full-corpus parse findings. Awaiting founder review.
**Date:** 2026-06-04
**Drives:** BACKEND, FRONTEND, AI sub-session work
**Grounded in:** `data/parsed/FULL_CORPUS_ANALYSIS.md` (3,772/3,772 Meesho leaves parsed cleanly)

> This document translates the 10 founder-locked decisions and the corpus-wide data findings into a concrete architecture that BACKEND/FRONTEND/AI coordinators can build against. It is NOT a re-statement of V1_FEATURE_SPEC.md — it specifies HOW the V1 features are realised given what we now know about Meesho's actual schema.

---

## Section 0 — Architectural premises (from corpus data)

These are no longer hypotheses. They are facts from parsing every Meesho category template:

1. **3,772 categories share 15 strict-universal fields + 13 near-universals (28 practical universals).** A V1 wizard built around these handles ≥99% of products without special-casing.
2. **No "Recommended" tier exists** in Meesho's templates. The form is binary (Compulsory / Optional).
3. **Image rules are 100% uniform**: 4 slots, slot 1 required. Build once, reuse everywhere.
4. **1,831 unique field names** exist corpus-wide. Hand-coded per-field components are infeasible. **10 input primitives** (auto-classified by `data_type` + `enum_count`) cover the entire field universe.
5. **291 "Brand-pattern" fields** have the same name but different enum sources per category. Backend stores enums per `(category_id, field_name)`. Frontend resolves via API.
6. **Form length varies 19–33 median compulsory fields by super-category.** Wizard step count is data-driven.
7. **Compliance varies by super-category.** 6 conditional onboarding extensions confirmed: Grocery+FSSAI (COMPULSORY), Kids+BIS, Electronics+R/IS/CM-L, Beauty+License, Books+ISBN, Appliances+License.
8. **Spelling/synonym drift exists in Meesho's source.** Canonical field-name normalisation is mandatory before backend seed.
9. **3,557 distinct templates serve 3,772 leaves.** Schema storage keyed by template; leaves map many-to-one.
10. **Eye-Serum represents an alternate compliance shape** ("Manufacturer Details" combined fields). Backend accepts both representations.

---

## Section 1 — System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Angular 18 PWA  (Tailwind + Material, signals + RxJS)           │
│  ──────────────────────────────────────────────────────────────  │
│  10 input primitives   │  Data-driven wizard   │  Auth + nav    │
│       │                          │                       │       │
└───────│──────────────────────────│───────────────────────│──────┘
        │ HTTPS + JWT              │                       │
┌───────▼──────────────────────────▼───────────────────────▼──────┐
│  FastAPI (async, Python 3.12)                                   │
│  ───────────────────────────────────────────────────────────────│
│  /api/v1/auth/*           /api/v1/categories/*                  │
│  /api/v1/seller-profile/* /api/v1/categories/{id}/field-enum/*  │
│  /api/v1/products/*       /api/v1/exports/*                     │
└───────┬──────────────────────────┬───────────────────────┬──────┘
        │                          │                       │
  ┌─────▼──────┐         ┌────────▼────────┐      ┌───────▼──────┐
  │ PostgreSQL │         │ Valkey (Redis)  │      │ Celery       │
  │ 16         │         │ DB 0: OTP/RL    │      │ workers      │
  │            │         │ DB 1: broker    │      │ (image, gen) │
  │ tables:    │         │ DB 2: results   │      │              │
  │ - users    │         └─────────────────┘      └──────┬───────┘
  │ - seller_  │                                         │
  │   profile  │         ┌─────────────────┐             │
  │ - templates│         │ GCS bucket      │◄────────────┤
  │ - categor- │         │ images/exports  │             │
  │   ies      │         └─────────────────┘             │
  │ - field_   │                                         │
  │   enum_    │         ┌─────────────────┐             │
  │   values   │         │ Gemini 2.5 Flash│◄────────────┘
  │ - field_   │         │ (text + vision) │
  │   aliases  │         └─────────────────┘
  │ - products │
  │ - product_ │
  │   images   │
  │ - pricing_ │
  │   calcs    │
  │ - exports  │
  └────────────┘
```

All on K3s single-node GCP VM (`meesell-dev`) in asia-south1. Traefik ingress + cert-manager. Three namespaces: `dev` / `staging` / `prod`.

---

## Section 2 — Data Model (PostgreSQL DDL)

### 2.1 User identity (mostly unchanged from V1_FEATURE_SPEC)

```sql
CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone             VARCHAR(15) UNIQUE NOT NULL,
  email             VARCHAR(255),
  plan              VARCHAR(20) DEFAULT 'free',
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  last_login_at     TIMESTAMPTZ
);
```

### 2.2 Seller profile — the **Onboarding bucket** (NEW, founder decision #1 + #9)

```sql
CREATE TABLE seller_profile (
  user_id                  UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

  -- 9-field Legal Metrology compliance block (in 3,771/3,772 categories)
  manufacturer_name        TEXT NOT NULL,
  manufacturer_address     TEXT NOT NULL,
  manufacturer_pincode     VARCHAR(6) NOT NULL,
  packer_name              TEXT NOT NULL,
  packer_address           TEXT NOT NULL,
  packer_pincode           VARCHAR(6) NOT NULL,
  importer_name            TEXT,
  importer_address         TEXT,
  importer_pincode         VARCHAR(6),

  -- Alternate compliance representation (for Eye-Serum-style templates)
  -- Filled if seller's selected categories use the collapsed format.
  manufacturer_details     TEXT,
  packer_details           TEXT,
  importer_details         TEXT,

  -- Universal-ish
  country_of_origin        VARCHAR(64) NOT NULL DEFAULT 'India',

  -- Conditional compliance extensions (per super-category)
  -- Keyed by Meesho super_id (e.g. "26"="Grocery"). Example payload:
  --   {"26": {"fssai_license_number": "10012345678901",
  --           "fssai_expiry": "2027-12-31"},
  --    "13": {"bis_isi_certification_number": "IS-1234-2024"},
  --    "16": {"bis_isi_cert": "...", "r_number": "...", "is_number": "..."}}
  compliance_extensions    JSONB NOT NULL DEFAULT '{}',

  -- Super-categories this seller declares they will sell in
  -- (drives which onboarding extension steps appear)
  active_super_categories  TEXT[] NOT NULL DEFAULT '{}',

  -- Bookkeeping
  profile_complete         BOOLEAN NOT NULL DEFAULT FALSE,
  created_at               TIMESTAMPTZ DEFAULT NOW(),
  updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_seller_profile_super_cats
  ON seller_profile USING GIN (active_super_categories);
```

**Onboarding extension specification (founder decision #9):**

| Super-category | super_id | Required keys in `compliance_extensions[super_id]` | Trigger |
|---|---|---|---|
| Grocery | 26 | `fssai_license_number` (required), `fssai_expiry` (recommended) | When seller declares Grocery |
| Kids & Toys | 13 | `bis_isi_certification_number` (optional, trust signal) | Optional even when declared |
| Consumer Electronics | 16 | `bis_isi_certification_number`, `r_number`, `is_number`, `cm_l_number` (all optional) | Optional |
| Beauty & Health | 19,36,37,14,88,34 | `license_registration_number`, `license_registration_type`, `license_expiry_date` (compulsory if seller has licensed products) | Compulsory subset |
| Books | 80 | `isbn_publisher_id` (optional — Meesho is lenient) | Optional |
| Home & Kitchen (appliance subset) | 30 | `license_number`, `license_expiry_date` | When dealing with electrical appliances |

### 2.3 Schema storage — `templates`, `categories`, `field_enum_values` (founder decision #7)

```sql
-- 3,557 distinct template schemas (vs 3,772 leaves)
CREATE TABLE templates (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_hash     VARCHAR(64) UNIQUE NOT NULL,  -- sha256 of canonical schema
  schema_jsonb    JSONB NOT NULL,
  -- structure: {
  --   "fields": [
  --     {"name": "Product Name", "canonical_name": "product_name",
  --      "marker": "compulsory", "data_type": "text", "primitive": "text_short",
  --      "help_text": "Please enter the product name. No special chars..."},
  --     {"name": "Variation", "canonical_name": "variation",
  --      "marker": "compulsory", "data_type": "dropdown", "primitive": "dropdown_api_search",
  --      "enum_resolver": "category"},  -- look up in field_enum_values
  --     ...
  --   ],
  --   "compulsory_count": 28,
  --   "optional_count": 14,
  --   "total_count": 42,
  --   "wizard_step_count": 6,
  --   "main_sheet_label": "Sarees-Fill this"
  -- }
  parsed_from_xlsx_at  TIMESTAMPTZ DEFAULT NOW(),
  parser_version       VARCHAR(8) NOT NULL DEFAULT '0.2'
);

-- 3,772 leaves, each mapping many-to-one to a template
CREATE TABLE categories (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meesho_leaf_id      VARCHAR(16) UNIQUE NOT NULL,    -- e.g. "10003"
  super_id            VARCHAR(8) NOT NULL,            -- e.g. "11" = Women Fashion
  super_name          VARCHAR(64) NOT NULL,           -- "Women Fashion"
  path                TEXT NOT NULL,                  -- "Women Fashion > Ethnic Wear > Sarees ..."
  leaf_name           VARCHAR(255) NOT NULL,
  template_id         UUID NOT NULL REFERENCES templates(id),
  commission_pct      NUMERIC(5,2),
  created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_categories_super       ON categories(super_id);
CREATE INDEX idx_categories_template    ON categories(template_id);
CREATE INDEX idx_categories_meesho_leaf ON categories(meesho_leaf_id);

-- 291 Brand-pattern fields: same name, different enum source per category (founder decision #2)
CREATE TABLE field_enum_values (
  category_id     UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  field_name      VARCHAR(128) NOT NULL,         -- canonical name
  enum_values     JSONB NOT NULL,                 -- array of strings
  value_count     INT NOT NULL,                   -- materialised for query speed
  truncated       BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE if stored values are a sample of a larger set
  PRIMARY KEY (category_id, field_name)
);
CREATE INDEX idx_field_enum_value_count ON field_enum_values(value_count);

-- Canonical field-name normalisation (founder decision #10)
CREATE TABLE field_aliases (
  variant_name      VARCHAR(128) PRIMARY KEY,     -- as it appears in Meesho XLSX
  canonical_name    VARCHAR(128) NOT NULL,        -- normalised internal name
  source            VARCHAR(32) NOT NULL          -- 'corpus' (auto), 'manual' (curated)
);
CREATE INDEX idx_field_aliases_canonical ON field_aliases(canonical_name);
```

### 2.4 Catalogs and products — Catalog wizard bucket

```sql
CREATE TABLE catalogs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name            VARCHAR(255) NOT NULL,
  category_id     UUID REFERENCES categories(id),
  status          VARCHAR(20) DEFAULT 'draft',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  catalog_id           UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
  user_id              UUID NOT NULL REFERENCES users(id),
  category_id          UUID NOT NULL REFERENCES categories(id),
  name                 VARCHAR(512),
  description          TEXT,

  -- Catalog wizard fields — keyed by canonical field name
  -- Mirrors the template schema; backend validates at PATCH time
  fields_jsonb         JSONB NOT NULL DEFAULT '{}',

  -- AI auto-fill suggestions (with confidence + source)
  ai_suggestions_jsonb JSONB NOT NULL DEFAULT '{}',
  -- structure: {"product_name": {"value": "...", "confidence": 0.91,
  --                              "source": "gemini-2.5-flash", "accepted": true}}

  status               VARCHAR(20) DEFAULT 'draft',
  deleted_at           TIMESTAMPTZ,
  created_at           TIMESTAMPTZ DEFAULT NOW(),
  updated_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_products_user     ON products(user_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_status   ON products(status);
```

### 2.5 Product images, pricing, exports

These follow V1_FEATURE_SPEC closely. **One new fact from corpus:** image rules are 100% uniform (4 slots, slot 1 compulsory). The `product_images` table needs no per-category variation.

```sql
CREATE TABLE product_images (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  gcs_path        TEXT NOT NULL,
  order_idx       INT NOT NULL CHECK (order_idx BETWEEN 1 AND 4),
  is_front        BOOLEAN GENERATED ALWAYS AS (order_idx = 1) STORED,
  width           INT, height INT,
  color_space     VARCHAR(8),
  precheck_jsonb  JSONB,
  status          VARCHAR(16) DEFAULT 'pending',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, order_idx)
);

CREATE TABLE pricing_calcs (...);  -- per V1_FEATURE_SPEC §4
CREATE TABLE exports       (...);  -- per V1_FEATURE_SPEC §4
```

### 2.6 Migration ordering

Alembic migration order:
1. `users`
2. `seller_profile` (depends on users)
3. `templates`
4. `categories` (depends on templates)
5. `field_enum_values` (depends on categories)
6. `field_aliases`
7. `catalogs` (depends on users)
8. `products` (depends on catalogs, categories)
9. `product_images` (depends on products)
10. `pricing_calcs`, `exports` (depend on products, users)

Seed order:
1. `field_aliases` from `data/parsed/canonical_field_aliases.json`
2. `templates` from per-batch parsed JSON (dedup by `schema_hash`)
3. `categories` from `backend/app/data/meesho_category_tree.json` joined to templates
4. `field_enum_values` from per-batch parsed JSON

---

## Section 3 — API Surface

### 3.1 Auth (unchanged from V1_FEATURE_SPEC)
- `POST /api/v1/auth/otp/send`
- `POST /api/v1/auth/otp/verify`

### 3.2 Seller profile (NEW — Onboarding bucket)

```
GET    /api/v1/seller-profile                 → current profile + completion flag
PATCH  /api/v1/seller-profile                 → update base compliance fields
PATCH  /api/v1/seller-profile/active-categories  → declare super-categories;
                                                    response includes required extensions
PATCH  /api/v1/seller-profile/compliance/{super_id}
                                              → set per-super-category extension values
GET    /api/v1/seller-profile/required-fields → returns the list of currently-required
                                                fields based on active_super_categories
```

The frontend uses `/required-fields` to decide which onboarding wizard steps to render.

### 3.3 Categories & schema

```
GET    /api/v1/categories/suggest?q=<desc>           → top-5 leaves + confidence
                                                       (Smart Picker; founder decision #8)
GET    /api/v1/categories                            → tree for manual browse fallback
GET    /api/v1/categories/{id}                       → leaf metadata + super_id + path
GET    /api/v1/categories/{id}/schema                → compiled wizard schema
                                                       (template fields + step layout)
GET    /api/v1/categories/{id}/field-enum/{name}
       ?q=<prefix>&page=&limit=                      → paginated enum values for a field
                                                       (handles Brand, Compatible Models,
                                                        and 289 other Brand-pattern fields)
```

**Seller-profile-incomplete error pattern** (for cross-category expansion, item #8):

When a seller tries to create a catalog in a super-category they haven't declared in `seller_profile.active_super_categories`, `POST /api/v1/products` returns:

```http
HTTP 422 Unprocessable Entity
{
  "error_code": "PROFILE_INCOMPLETE_FOR_CATEGORY",
  "message": "Please add your FSSAI license to your profile before listing in Grocery.",
  "missing_super_category": "26",
  "missing_super_name": "Grocery",
  "missing_compliance_fields": ["fssai_license_number", "fssai_expiry"],
  "profile_url": "/profile"
}
```

Frontend displays a modal pointing the seller to `/profile`. The seller adds the super-category, reactively the form expands to collect the missing compliance fields, saves, and returns to the listing flow. This is V1's "add super-category later" flow — simple profile CRUD with reactive sections, no inline modal flow at pick-time. V1.5 may add inline guided expansion.

The `schema` endpoint compiles the template into a wizard-ready payload:

```json
{
  "category_id": "...",
  "meesho_leaf_id": "10003",
  "super_id": "11",
  "fields": [
    {
      "canonical_name": "product_name",
      "display_name": "Product Name",
      "marker": "compulsory",
      "primitive": "text_short",
      "help_text": "...",
      "max_length": 200
    },
    {
      "canonical_name": "brand",
      "display_name": "Brand",
      "marker": "optional",
      "primitive": "dropdown_api_search",
      "enum_endpoint": "/api/v1/categories/{id}/field-enum/brand",
      "enum_count": 3730
    },
    ...
  ],
  "wizard_steps": [
    {"title": "Basics", "fields": ["product_name", "variation", ...]},
    {"title": "Pricing", "fields": ["meesho_price", "mrp", ...]},
    {"title": "Sizing", "fields": ["length_size", "width_size", ...]},
    {"title": "Compliance", "fields": [], "auto_fill_from": "seller_profile"},
    {"title": "Images", "fields": ["image_1", "image_2", "image_3", "image_4"]}
  ]
}
```

Step generator algorithm (frontend-friendly):
- Group fields by semantic cluster (auto-derived from canonical name prefixes)
- Onboarding-auto-filled fields go into a dedicated "Compliance" step shown as a summary
- Image fields always go in their own step (uniform corpus-wide)
- Min 3 steps, max 8 steps, target 5±1
- Sort steps so manual-entry steps come before auto-filled steps

### 3.4 Catalog and product (mostly per V1_FEATURE_SPEC §5)

```
POST   /api/v1/products                              → create draft
PATCH  /api/v1/products/{id}                         → autosave
POST   /api/v1/products/{id}/autofill                → Gemini suggestions
                                                       (enum-constrained per decision #4)
POST   /api/v1/products/{id}/images                  → upload + queue pre-check
GET    /api/v1/products/{id}/images                  → poll
GET    /api/v1/products/{id}/preview                 → assembled preview
POST   /api/v1/products/{id}/price-calc              → pricing
POST   /api/v1/products/{id}/export-xlsx             → generate Meesho-format XLSX
GET    /api/v1/products                              → dashboard list
DELETE /api/v1/products/{id}                         → soft delete
GET    /api/v1/exports/{id}                          → poll export
```

---

## Section 4 — Frontend Architecture

### 4.1 The 10 input primitives (founder decision #6)

A single Angular standalone component module, classified at template-compile time:

| Primitive | Component | Selection rule | Examples |
|---|---|---|---|
| `text_short` | `<mee-text-short>` | `data_type=text`, no name-pattern match | Product Name, SKU ID, Manufacturer Name |
| `text_long` | `<mee-text-long>` | name matches `*description|notes|ingredients|address` | Product Description, Manufacturer Address |
| `number` | `<mee-number>` | `data_type=number`, no unit suffix | Inventory, Pages, Number of Pockets |
| `number_with_unit` | `<mee-number-unit>` | numeric field that has a companion `*_unit` field, OR name matches `*weight|voltage|wattage|frequency|capacity` | Net Weight (gms), Voltage (V), Packaging Weight + Packaging Weight unit |
| `currency` | `<mee-currency>` | name matches `*price|mrp` (renders ₹ prefix) | Meesho Price, MRP, Wrong/Defective Returns Price |
| `dropdown_small` | `<mee-dropdown-small>` | `enum_count` 1–20 (radio or simple select) | Veg/NonVeg, Organic, Compulsory? |
| `dropdown_medium` | `<mee-dropdown-medium>` | `enum_count` 21–100 (Material `mat-autocomplete`, in-memory) | Saree Fabric, Genre |
| `dropdown_large` | `<mee-dropdown-large>` | `enum_count` 101–500 (virtualised autocomplete) | Length Size, Country of Origin |
| `dropdown_api_search` | `<mee-dropdown-api>` | `enum_count` >500 (debounced API call) | Brand (up to 3,998), Compatible Models (up to 4,481) |
| `image_upload` | `<mee-image-upload>` | `data_type=image_url` (matches `^Image\s+\d+`) | Image 1 (Front), Image 2–4 |

Plus 1 composite for legacy templates:
| `address_group` | `<mee-address-group>` | name matches `*Details` and the seller has the collapsed-compliance flag set | Manufacturer Details, Packer Details |

**Total: 11 primitive components, covering 1,831 corpus-wide field names.**

### 4.2 Wizard renderer

```typescript
// frontend/src/app/wizard/wizard-renderer.component.ts
@Component({
  selector: 'mee-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-stepper #stepper linear>
      @for (step of schema().wizard_steps; track step.title) {
        <mat-step [label]="step.title">
          @for (fieldName of step.fields; track fieldName) {
            <mee-field
              [schema]="resolveField(fieldName)"
              [value]="model()[fieldName]"
              (valueChange)="patch(fieldName, $event)"
              [aiSuggestion]="aiSuggestions()[fieldName]"
            />
          }
        </mat-step>
      }
    </mat-stepper>
  `
})
export class WizardRenderer { ... }
```

The `mee-field` component dispatches to one of the 11 primitives based on `schema.primitive`. No category-specific code anywhere — pure data-driven.

### 4.3 Onboarding wizard

Two phases:
1. **Base step** — collect 9 compliance fields + Country of Origin (always required)
2. **Super-category declaration step** — multi-select chips for super-categories the seller will sell in
3. **Conditional steps** — one per declared super-category that has compliance extensions (Grocery → FSSAI, Kids → BIS optional, etc.)

Backend's `GET /api/v1/seller-profile/required-fields` drives which steps render.

### 4.4 State management

- Forms: Reactive Forms (`FormBuilder`)
- Per-component reactive state: `signal()` + `computed()`
- Shared state (Auth, current catalog): RxJS `BehaviorSubject` in services
- No NgRx (locked decision per CLAUDE.md)

### 4.5 Route layout (mostly unchanged from V1_FEATURE_SPEC §6)

Add to route list:
- `/onboarding` → seller profile wizard (separate from catalog wizard)
- `/profile` → edit seller profile

---

## Section 5 — AI Pipeline Architecture

### 5.1 Smart Category Picker (V1 Feature 2 + founder decision #8)

```
User description → POST /api/v1/categories/suggest
                ↓
        ┌───────┴────────────────────────────────┐
        │ 1. Embed description with Gemini       │
        │ 2. Pre-filter via SQL ILIKE on path    │
        │    (keyword shortcut for common terms) │
        │ 3. Send description + compressed tree  │
        │    (super_name → super_id mapping)     │
        │    to Gemini with JSON-mode contract:  │
        │    {"top_n": [{"leaf_id": "10003",     │
        │                "confidence": 0.93}]}   │
        │ 4. Return TOP-5 (not top-3, per #8)    │
        │    + "browse manually" fallback link   │
        │ 5. Cache for 24h on description hash   │
        └────────────────────────────────────────┘
```

**Compressed tree (token budget):** instead of sending all 3,772 leaves to Gemini, send a 3-level hierarchy (super → category → top 10 leaves per category). Estimated tokens: ~8,000 vs ~120,000 for the full tree.

**Acceptance:** golden test with 50 descriptions, ≥80% recall in top-5.

### 5.2 AI Auto-fill (V1 Feature 4 + founder decision #4 — enum-constrained)

```
PRE-CONDITION: product has description + category
                ↓
POST /api/v1/products/{id}/autofill
                ↓
        ┌───────┴────────────────────────────────┐
        │ 1. Load category schema (compiled)     │
        │ 2. Identify compulsory fields not yet  │
        │    filled                              │
        │ 3. For each enum field, attach the     │
        │    list of allowed values to prompt    │
        │ 4. Prompt Gemini with JSON-mode:       │
        │    "For each field below, suggest a    │
        │     value or null. Enum fields: choose │
        │     ONLY from the allowed_values list. │
        │     Never invent values."              │
        │ 5. Parse + validate each suggestion    │
        │    against schema (enum membership,    │
        │    type, length)                       │
        │ 6. Reject + drop invalid suggestions   │
        │ 7. Store in products.ai_suggestions    │
        │    with confidence + "rejected_reason" │
        │    where applicable                    │
        └────────────────────────────────────────┘
```

**Guardrail:** the prompt template enforces enum constraints at the language model level. The parser enforces them at the API level. **Two-layer guardrail** so a single failure (LLM ignoring the rule) doesn't let invalid data through.

**Token budget:** category schema compressed to ~3,000 tokens (only compulsory fields + their enums). Plus description (~200 tokens). Gemini Flash response in JSON mode.

### 5.3 Image pre-check (V1 Feature 5, mostly unchanged but data-confirmed)

Pipeline:
1. JPEG check (Pillow)
2. RGB vs CMYK (Pillow)
3. Resolution ≥1500×1500 (Pillow)
4. White-background heuristic (Pillow + numpy edge detection)
5. Watermark check (Gemini 2.5 Flash vision, 1 image per call, ≥85% accuracy on 30-image golden set)

**Data-confirmed:** every category needs the same 4-slot image layout (corpus-wide uniform). No per-category image-rule variation.

### 5.4 Prompt registry

```
backend/app/ai/prompts/
├── category_picker.py       # Smart Picker
├── autofill_per_category.py # Auto-fill template (per-category schema injected)
└── watermark_vision.py      # Image vision check

backend/app/ai/parsers/
├── category_picker_parser.py
├── autofill_parser.py        # enum-constraint enforcer
└── watermark_parser.py

evals/
├── category_picker_golden.yaml  # 50 descriptions
├── autofill_golden.yaml         # 30 product specs per super-category
└── watermark_golden/            # 30 sample images
```

---

## Section 5.5 — Export Adapter

The Export Adapter is the **sole component in the system that knows about Meesho's wire format** (per philosophy M10 + F8). All other components — backend services, frontend renderer, AI prompts, validators — work with canonical names + display labels. The adapter translates at the boundary.

### 5.5.1 Responsibilities

1. Given a `product_id`, produce a Meesho-compatible XLSX file
2. Apply the correct **compliance shape** for the product's category template (standard 9-field or Eye-Serum-style collapsed 3-field)
3. Restore Meesho's **exact column headers**, including typos ("Primiary", "Seconadry")
4. Translate **canonical enum values → Meesho enum codes** per category
5. Restore Meesho's **column order** as it appears in the original XLSX template
6. Generate the image ZIP file accompanying the XLSX
7. Run **round-trip validation** — re-parse the generated XLSX and assert canonical equivalence
8. Upload to GCS, return a signed URL (TTL 1 hour)

### 5.5.2 Architectural pattern — three patterns layered

- **Adapter (GoF)** — the core: canonical model → Meesho wire format. Single responsibility.
- **Strategy** — handles per-category transformations (compliance shape). Adding a new shape later = adding a new Strategy class, no other code changes.
- **Pipeline** — the translation runs as a 9-step ordered chain so each step is independently testable, replaceable, and traceable in logs.

The whole thing sits inside a **Hexagonal Architecture** pattern: the adapter is an outbound port. When V2 adds Amazon, Flipkart, Etsy — each gets its own adapter implementing the same `MarketplaceExportAdapter` interface. The core domain never learns about marketplace specifics.

### 5.5.3 File structure

```
backend/app/services/export_adapter/
├── __init__.py
├── interface.py            # MarketplaceExportAdapter (abstract base for V2-readiness)
├── adapter.py              # MeeshoExportAdapter (the main class)
├── pipeline/
│   ├── schema_resolver.py      # Step 1: load template + Meesho column mapping
│   ├── row_builder.py          # Step 3: merge product + seller_profile into canonical row
│   ├── enum_translator.py      # Step 5: canonical enum value → Meesho enum code
│   ├── column_orderer.py       # Step 6: reorder dict to Meesho's expected order
│   ├── alias_restorer.py       # Step 7: rename canonical keys to Meesho column headers (incl. typos)
│   ├── xlsx_writer.py          # Step 8: openpyxl wrapper, preserves Meesho's 5-sheet structure
│   └── round_trip_validator.py # Step 9: re-parse + assert equality
├── strategies/
│   ├── base.py                 # ComplianceStrategy ABC (Step 4 dispatcher)
│   ├── standard.py             # StandardComplianceStrategy (9 fields → 9 columns)
│   └── collapsed.py            # CollapsedComplianceStrategy (9 fields → 3 columns, Eye-Serum)
├── exceptions.py
└── tests/
    └── golden_fixtures/        # per-super-category: canonical product → expected XLSX
```

### 5.5.4 The 9-step pipeline

```python
class MeeshoExportAdapter(MarketplaceExportAdapter):
    def export(self, product_id: UUID) -> ExportResult:
        # Load all dependencies (single transaction, read-only)
        product = self.product_repo.get(product_id)
        seller_profile = self.profile_repo.get_for_user(product.user_id)
        category = self.category_repo.get(product.category_id)
        template = self.template_repo.get(category.template_id)

        # Step 1: schema resolution
        schema = self.schema_resolver.resolve(template)

        # Step 2: pick the compliance strategy
        strategy = self.strategy_factory.for_shape(template.compliance_shape)
        # → StandardComplianceStrategy() or CollapsedComplianceStrategy()

        # Step 3: build canonical row
        canonical_row = self.row_builder.build(product, seller_profile, schema)

        # Step 4: apply compliance strategy (collapses if Eye-Serum)
        compliance_row = strategy.apply(canonical_row, seller_profile)

        # Step 5: translate enum values
        translated_row = self.enum_translator.translate(compliance_row, schema)

        # Step 6: reorder columns to Meesho's expected sequence
        ordered_row = self.column_orderer.order(translated_row, schema)

        # Step 7: restore Meesho column headers (including typos)
        meesho_row = self.alias_restorer.restore(ordered_row, schema)

        # Step 8: generate XLSX (preserves Meesho's 5-sheet structure)
        xlsx_bytes = self.xlsx_writer.write(template, meesho_row)

        # Step 9: round-trip validate
        self.round_trip_validator.validate(
            xlsx_bytes,
            canonical_expected=canonical_row,
            template=template,
        )

        # Final: package image ZIP, upload to GCS
        image_zip = self.image_packager.pack(product.images)
        xlsx_url = self.gcs.upload(xlsx_bytes, ttl_seconds=3600)
        zip_url = self.gcs.upload(image_zip, ttl_seconds=3600)

        return ExportResult(xlsx_url=xlsx_url, zip_url=zip_url, ...)
```

### 5.5.5 Compliance Strategy classes

```python
class ComplianceStrategy(ABC):
    @abstractmethod
    def apply(self, row: dict, seller_profile: SellerProfile) -> dict: ...

class StandardComplianceStrategy(ComplianceStrategy):
    """Used by 3,771 of 3,772 categories. 9 separate fields → 9 columns."""
    def apply(self, row: dict, sp: SellerProfile) -> dict:
        return {
            **row,
            "manufacturer_name": sp.manufacturer_name,
            "manufacturer_address": sp.manufacturer_address,
            "manufacturer_pincode": sp.manufacturer_pincode,
            "packer_name": sp.packer_name,
            "packer_address": sp.packer_address,
            "packer_pincode": sp.packer_pincode,
            "importer_name": sp.importer_name or "",
            "importer_address": sp.importer_address or "",
            "importer_pincode": sp.importer_pincode or "",
        }

class CollapsedComplianceStrategy(ComplianceStrategy):
    """Used by Eye-Serum (1 leaf in V1). Concatenates 9 → 3 columns."""
    def apply(self, row: dict, sp: SellerProfile) -> dict:
        return {
            **row,
            "manufacturer_details": self._combine(sp.manufacturer_name, sp.manufacturer_address, sp.manufacturer_pincode),
            "packer_details":       self._combine(sp.packer_name, sp.packer_address, sp.packer_pincode),
            "importer_details":     self._combine(sp.importer_name, sp.importer_address, sp.importer_pincode),
        }

    @staticmethod
    def _combine(name: str, addr: str, pincode: str) -> str:
        parts = [p for p in (name, addr, f"PIN: {pincode}" if pincode else "") if p]
        return ", ".join(parts)
```

### 5.5.6 The data shape the adapter relies on

The adapter reads from `templates.schema_jsonb`. Each field entry carries:

```json
{
  "canonical_name": "no_of_primary_cameras",
  "display_label": "Number of Primary Cameras",
  "display_help": "How many main cameras on the back of the phone?",
  "meesho_column_header": "No. of Primiary Cameras",
  "meesho_column_index": 23,
  "primitive": "number",
  "marker": "compulsory",
  "is_advanced": false,
  "enum_codes_map": null,
  "compliance_role": null
}
```

For enum fields the `enum_codes_map` is `{"canonical_value": "meesho_enum_code", ...}`. For most enums these are identical strings (Color values, Size values). For codified enums (material codes "PE-HD"), the map captures the translation.

`compliance_role` is set on the 9 standard compliance fields (one of `manufacturer_name`, `manufacturer_address`, `manufacturer_pincode`, etc.) so the Strategy knows where to pull from `seller_profile`.

`templates.compliance_shape` is `"standard"` or `"collapsed"` — selects the Strategy.

### 5.5.7 Round-trip validation — the contract

```python
class RoundTripValidator:
    """Asserts that what we export → what we parse → equals what we started with."""
    def __init__(self, parser: MeeshoXLSXParser):
        self.parser = parser

    def validate(self, xlsx_bytes: bytes, canonical_expected: dict, template: Template):
        parsed = self.parser.parse_bytes(xlsx_bytes)
        for canonical_key, expected_value in canonical_expected.items():
            actual = parsed.fields.get(canonical_key)
            if actual != expected_value:
                raise RoundTripValidationError(
                    field=canonical_key, expected=expected_value, actual=actual,
                    template_id=template.id,
                )
```

Run inline on every export (cost: ~500ms — acceptable for V1's 15s budget). Also runs in CI on golden fixtures (one per super-category, 12 fixtures total).

### 5.5.8 Celery + API wiring

```python
# backend/app/workers/export_tasks.py
@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def generate_xlsx_export(self, product_id: str, export_id: str):
    """Async XLSX generation. Frontend polls via /api/v1/exports/{export_id}."""
    try:
        adapter = MeeshoExportAdapter.from_config()
        result = adapter.export(UUID(product_id))
        update_export_record(export_id, status="ready",
                             xlsx_url=result.xlsx_url, zip_url=result.zip_url)
    except RoundTripValidationError as e:
        update_export_record(export_id, status="failed",
                             error_message=f"Internal validation failed: {e}")
        # Surface to engineer; this is a bug, not a seller-facing issue
    except (TemplateNotFoundError, MissingComplianceError) as e:
        update_export_record(export_id, status="failed",
                             error_message=str(e))  # seller-facing
```

```python
# backend/app/routers/exports.py
@router.post("/products/{product_id}/export-xlsx")
async def trigger_export(product_id: UUID, user: User = Depends(...)):
    export_record = await create_export_record(product_id, user.id, status="processing")
    generate_xlsx_export.delay(str(product_id), str(export_record.id))
    return {"export_id": export_record.id, "status": "processing"}

@router.get("/exports/{export_id}")
async def poll_export(export_id: UUID, user: User = Depends(...)):
    return await get_export_record(export_id, user.id)
```

### 5.5.9 Future-proofing — the `MarketplaceExportAdapter` interface

```python
class MarketplaceExportAdapter(ABC):
    """Outbound port for marketplace export.

    V1 implementation: MeeshoExportAdapter (XLSX).
    V2 plans: AmazonExportAdapter (CSV), FlipkartExportAdapter (XML), EtsyExportAdapter (JSON).
    Core domain knows nothing about which marketplace it's exporting to.
    """
    @abstractmethod
    def export(self, product_id: UUID) -> ExportResult: ...

    @abstractmethod
    def supported_categories(self) -> set[UUID]: ...
        # so the UI can show "Available for Meesho only" when V2 ships
```

### 5.5.10 Performance budget (1 product + 6 images)

| Step | Budget |
|---|---|
| Pipeline steps 1-7 (in-memory) | ~500 ms |
| XLSX generation (step 8) | ~200 ms |
| Round-trip validation (step 9) | ~500 ms |
| Image ZIP packaging | ~3-5 s |
| GCS upload (xlsx + zip) | ~1-2 s |
| **Total** | **~5-9 s** |

V1 spec budget: 15s per 1-product export. Well within budget.

### 5.5.11 Testing strategy

| Test layer | Coverage |
|---|---|
| **Unit** | Each pipeline step independently. Strategy classes. Validator. Mock fixtures. |
| **Integration** | Full adapter on 3 representative products (Saree, Spice, Eye-Serum). |
| **Golden round-trip** | One canonical-product-fixture per super-category (12 total). On every PR that touches adapter / schema / aliases / templates. |
| **Smoke** | Generate XLSX, attempt actual upload to Meesho staging panel (manual, pre-release only). |

Golden fixtures live in `backend/app/services/export_adapter/tests/golden_fixtures/`. Each is a JSON of canonical product + seller_profile + expected parsed-equivalent. The test runs: export → parse → assert equality.

### 5.5.12 Error taxonomy

| Exception | HTTP status | Seller-facing? |
|---|---|---|
| `TemplateNotFoundError` | 422 | Yes — "Category not yet supported. We're working on it." |
| `MissingComplianceError` | 400 | Yes — "Complete your seller profile to export." Link to `/profile`. |
| `EnumNotFoundError` | 500 | No — engineering bug; upstream validators should have caught it |
| `RoundTripValidationError` | 500 | No — engineering bug; surface to monitoring |
| `XLSXWriteError` | 500 | No — openpyxl failure; engineering bug |
| `GCSUploadError` | 503 | Yes — "Storage temporarily unavailable. Retrying..." |

### 5.5.13 What this section adds to the data model (delta from §2)

`templates.schema_jsonb` is now strictly defined to include per-field:
- `meesho_column_header` (string, verbatim from Meesho XLSX)
- `meesho_column_index` (int, column position in Meesho's wire format)
- `enum_codes_map` (object | null, canonical→Meesho enum code translation)
- `compliance_role` (enum | null, only set on the 9 compliance fields)

`templates.compliance_shape` (`"standard"` | `"collapsed"`) — the field has been mentioned earlier; this section makes it load-bearing.

No new tables. The data is structured inside the existing `schema_jsonb`.

---

## Section 5.6 — Presentation Layer in `templates.schema_jsonb`

The data model already mentions `templates.schema_jsonb` in §2 and §5.5. This section formalises it — the **per-field schema that satisfies the philosophy's three-layer pattern** (Display / Canonical / Export).

### 5.6.1 The full per-field schema

Each field entry in `templates.schema_jsonb.fields[]` has these properties. Naming convention enforces the layer separation: `display_*` goes to UI, `meesho_*` goes to Export Adapter, everything else is canonical/internal.

```json
{
  // ── CANONICAL layer (internal — services, validators, AI) ──
  "canonical_name":     "net_weight_grams",        // primary key
  "data_type":          "number",                  // text | number | dropdown | image_url | date | boolean
  "primitive":          "number_with_unit",        // one of 11 primitives
  "marker":             "compulsory",              // compulsory | optional
  "is_advanced":        false,                     // hide behind "Advanced fields" toggle (Pattern 5)
  "is_hidden":          false,                     // never render in UI (Pattern 2) — for opaque/internal fields
  "compliance_role":    null,                      // null | manufacturer_name | packer_address | importer_pincode | ...
  "step_id":            "inventory",               // wizard step grouping
  "max_length":         null,                      // for text
  "min_length":         null,
  "regex":              null,                      // validation pattern
  "min_value":          0,                         // for numbers
  "max_value":          null,
  "unit_suffix":        "g",                       // for number_with_unit primitive (e.g. "g", "V", "W", "Hz", "mAh")

  // ── DISPLAY layer (UI — seller sees these) ──
  "display_label":      { "en": "Weight per package" },
  "display_help":       { "en": "How much does ONE piece weigh, in grams? Example: a shirt is about 200g." },
  "display_placeholder":{ "en": "200" },
  "display_unit_label": { "en": "grams" },         // friendlier than "g" — shown beside the input
  "validation_message": { "en": "Please enter the weight per package in grams." },
  "help_url":           null,                      // optional external link (e.g. FSSAI portal)

  // ── EXPORT layer (Meesho wire format — Export Adapter only) ──
  "meesho_column_header": "Net Weight (gms)",       // verbatim Meesho XLSX column
  "meesho_column_index":  8,                        // position in Meesho's expected column order
  "meesho_default":       null,                     // value to export if seller didn't fill (for is_hidden fields)

  // ── ENUM-only properties ──
  "enum_codes_map":     null,                       // { "canonical_value": "meesho_enum_code" }
  "enum_labels":        null                        // { "canonical_value": { "en": "Friendly label" } }
}
```

Most properties are nullable. For a Brand picker field, `data_type` is `dropdown`, `primitive` is `dropdown_api_search`, enum data lives in `field_enum_values` table (per category), and `enum_codes_map` / `enum_labels` apply only when needed.

### 5.6.2 Locale handling (philosophy M9 — structural localization)

Every seller-facing string is stored as a **locale map**, not a bare string:

```json
"display_label": {
  "en": "Weight per package",
  "ta": "ஒரு பேக்கின் எடை",
  "hi": "एक पैकेज का वजन"
}
```

**V1 ships English only.** Tamil and Hindi keys can be empty/absent. V1.5 fills them in without a schema migration — just by writing into the existing JSONB.

Backend serves the correct locale from `Accept-Language` header (fallback: `en`). If a requested locale is missing for a field, fall back to `en` per field. No schema migration ever needed for new locales.

### 5.6.3 Wizard step composition

Wizard steps are **not stored per template**. They're derived at runtime by grouping fields by `step_id`.

Standard step IDs and their titles (global map in code):

| step_id | Title (en) | When it appears |
|---|---|---|
| `basics` | "Tell us about your product" | Always |
| `pricing` | "Set your price" | Always |
| `inventory` | "Stock and weight" | Always |
| `sizing` | "Sizing" | For apparel + footwear (when fields like `length_size`, `bust_size` exist) |
| `materials` | "Materials and pattern" | For apparel (when fields like `fabric`, `pattern` exist) |
| `food` | "Food details" | Grocery (when fields like `veg_nonveg`, `shelf_life` exist) |
| `tech_specs` | "Specifications" | Electronics (when fields like `voltage`, `wattage`, `ram` exist) |
| `safety` | "Safety information" | Kids & Toys + appliances (when fields like `recommended_age`, `battery_required` exist) |
| `warranty` | "Warranty" | Electronics + Appliances + Cookware (when warranty fields exist) |
| `compliance` | "Your seller details" | Always — read-only summary, auto-filled from `seller_profile` |
| `photos` | "Add photos" | Always |
| `description` | "Description (optional)" | Always |
| `advanced` | "Advanced fields" | Only if at least one `is_advanced: true` field exists in this template |

**Wizard composer algorithm:**
1. Read all fields from `templates.schema_jsonb`
2. Group by `step_id`
3. Drop empty steps
4. Sort steps by canonical order (table above)
5. Pull step titles from `STEP_TITLES` constant; render in seller's locale

The frontend wizard renderer (§4) is fed this composed step list — never sees `meesho_*` properties.

### 5.6.4 Field-enum extension for dropdown labels

The `field_enum_values` table (§2.3) currently stores `enum_values: jsonb` as a string array. **Extend it to store entries with optional friendly labels:**

```sql
ALTER TABLE field_enum_values
  ADD COLUMN enum_entries JSONB;  -- richer structure
-- Migrate existing enum_values arrays to enum_entries:
--   ["Cotton", "Silk", "Polyester"]
-- becomes
--   [{"canonical": "Cotton",     "meesho": "Cotton",     "labels": {"en": "Cotton"}},
--    {"canonical": "Silk",       "meesho": "Silk",       "labels": {"en": "Silk"}},
--    {"canonical": "Polyester",  "meesho": "Polyester",  "labels": {"en": "Polyester"}}]
```

- For most enums, `canonical == meesho` and `labels.en == canonical`. No translation.
- For codified enums (e.g. material codes "PE-HD", "MDF"), `labels.en` provides a friendly name ("High-density Polyethylene", "Medium-density Fiberboard").
- The Export Adapter writes `meesho` to XLSX. The frontend renders `labels[locale]`. AI auto-fill reasons in `canonical` then validates against the entry list.

V1 ships with `canonical == meesho == labels.en` for all enums (mechanical migration). V1.5 curates friendly labels for the dropdowns where it matters most.

### 5.6.5 Migration — how parsed JSON becomes `schema_jsonb`

Currently we have raw parsed data in `data/parsed/batch_NN_*.json`. The seed pipeline transforms it:

```
data/parsed/batch_NN_*.json
            │
            ▼
   scripts/build_template_schemas.py     (NEW — one-shot transformer)
            │
            ▼
   For each unique template (deduped by schema hash):
     - Build fields[] array with the full schema shape above
     - Map parsed field name → canonical_name (using canonical_field_aliases.json)
     - meesho_column_header  = raw field name from parsed JSON (verbatim)
     - meesho_column_index   = "col" property from parsed JSON
     - display_label         = FRIENDLY_LABELS[canonical_name] OR title-cased canonical_name
     - display_help          = FRIENDLY_HELP[canonical_name] OR parsed help_text OR null
     - validation_message    = derived from VALIDATION_MESSAGES library by data_type
     - primitive             = inferred from data_type + enum_count
     - step_id               = inferred from STEP_ASSIGNMENT rules (field name patterns)
     - compliance_role       = matches the 9 compliance field names
     - is_advanced           = TRUE for Group ID and a small allowlist; FALSE otherwise
     - is_hidden             = FALSE for V1
            │
            ▼
   INSERT INTO templates (schema_jsonb, schema_hash, ...) VALUES (...)
   INSERT INTO categories (... template_id ...) VALUES (...)
   INSERT INTO field_enum_values (category_id, field_name, enum_entries, ...) VALUES (...)
```

This script is **idempotent** (recomputes schema_hash; INSERTs only if hash is new) and **diffable** (output a report of which templates changed when re-run after Meesho refresh).

### 5.6.6 Content curation strategy

The corpus has **1,831 unique field names**. Hand-writing display labels and help text for all of them is impractical for V1. Tiered approach:

| Tier | Field count | Friendly copy strategy |
|---|---|---|
| Tier A — Universal core | 28 (15 strict + 13 near-universal) | **V1: hand-curated.** Founder + coordinator write friendly `display_label` + `display_help` for each. ~1.5 hour of writing. |
| Tier B — Onboarding extensions | ~10 (FSSAI, BIS, ISBN, License family) | **V1: hand-curated.** Same as Tier A. |
| Tier C — Common (in ≥50 leaves) | ~150 | **V1: title-cased canonical_name + Meesho's original help_text.** Mostly OK; revisit if seller testing shows confusion. |
| Tier D — Niche (in <50 leaves) | ~1,640 | **V1: title-cased canonical_name only.** No help_text. Defer to V1.5. Acceptable because most sellers list in popular categories. |
| Tier E — Future imports | New fields from Meesho refresh | **Default: title-case + Meesho help_text.** Flag for curation in monthly review. |

Curated copy lives in `data/parsed/field_display_overrides.json`:
```json
{
  "product_name": {
    "display_label": {"en": "Product name"},
    "display_help":  {"en": "What customers will see in search. Be specific — say 'Blue cotton kurti with mirror work' instead of just 'Kurti'."},
    "display_placeholder": {"en": "Blue cotton kurti with mirror work"}
  },
  "net_weight_grams": {
    "display_label": {"en": "Weight per package"},
    "display_help":  {"en": "How much does ONE piece weigh, in grams? Example: a shirt is about 200g."},
    "display_unit_label": {"en": "grams"}
  },
  ...
}
```

The seed script merges this with the auto-derived data. Founder owns this file; updates land in source control.

### 5.6.7 Validation message library

A small set of message templates parameterized by `{label}`, `{max_length}`, `{min_value}`, etc. Defined in code, not in `schema_jsonb` (so they're locale-bundled with the app):

```python
# backend/app/i18n/validation_messages.py
VALIDATION_MESSAGES = {
    "required_missing":      {"en": "Please fill in {label}."},
    "max_length_exceeded":   {"en": "{label} should be {max_length} characters or less."},
    "min_length_unmet":      {"en": "{label} needs at least {min_length} characters."},
    "below_min_value":       {"en": "{label} should be at least {min_value}."},
    "above_max_value":       {"en": "{label} can be at most {max_value}."},
    "enum_not_in_list":      {"en": "Please pick {label} from the list."},
    "invalid_pincode":       {"en": "Please enter a valid 6-digit pincode."},
    "invalid_phone":         {"en": "Please enter a valid 10-digit Indian mobile number."},
    "invalid_email":         {"en": "Please enter a valid email like name@example.com."},
    "invalid_jpeg":          {"en": "Please upload a JPEG image (.jpg or .jpeg)."},
    "image_too_small":       {"en": "Image must be at least 1500×1500 pixels."},
    "image_wrong_color":     {"en": "Image must be in RGB color (not CMYK). Try saving from Photoshop with 'sRGB'."},
    "image_has_watermark":   {"en": "Please remove the watermark from the image."},
    "image_not_white_bg":    {"en": "Background should be plain white."},
    "field_format_invalid":  {"en": "{label} doesn't look right. Please check the example."},
    ...
}
```

Field-level `validation_message` in `schema_jsonb` can OVERRIDE the library default with field-specific phrasing. Most fields will use library defaults.

### 5.6.8 Sample — the schema for "Product Name" (full three-layer view)

```json
{
  "canonical_name": "product_name",
  "data_type": "text",
  "primitive": "text_short",
  "marker": "compulsory",
  "is_advanced": false,
  "is_hidden": false,
  "compliance_role": null,
  "step_id": "basics",
  "max_length": 200,
  "min_length": 3,
  "regex": null,

  "display_label":       {"en": "Product name"},
  "display_help":        {"en": "What customers will see in search. Be specific — say 'Blue cotton kurti with mirror work' instead of just 'Kurti'."},
  "display_placeholder": {"en": "Blue cotton kurti with mirror work"},
  "validation_message":  {"en": "Please give your product a name (3 characters minimum)."},
  "help_url": null,

  "meesho_column_header": "Product Name",
  "meesho_column_index":  4,
  "meesho_default":       null,

  "enum_codes_map": null,
  "enum_labels":    null
}
```

This single 20-line object satisfies the entire philosophy for one field:
- **Seller sees**: friendly label + plain-English help + helpful placeholder
- **System works with**: canonical_name + data_type + primitive + step_id + validation rules
- **Meesho receives**: "Product Name" column at index 4 with the seller's text value

### 5.6.9 What this section adds to the data model (delta from §2)

| Change | Impact |
|---|---|
| `templates.schema_jsonb` shape is now strictly defined per §5.6.1 | All consumers (Backend, Frontend, AI, Export Adapter) write against the same contract |
| `field_enum_values.enum_entries` JSONB column added (replaces `enum_values`) | Supports per-value Meesho code translation + friendly labels |
| `data/parsed/field_display_overrides.json` (new) | Hand-curated friendly copy for ~38 universal + onboarding fields |
| `scripts/build_template_schemas.py` (new) | Idempotent transformer: parsed JSON → seeded templates |
| `backend/app/i18n/validation_messages.py` (new) | Plain-English validation message library |

No new tables. Most of the work is structural — formalising the JSONB shape and writing the seed transformer.

---

## Section 5.7 — Round-trip Test Plan

The philosophy makes round-trip integrity sacred (M6, F7). This section specifies HOW we test it.

### 5.7.1 What round-trip testing proves

For every test fixture, the loop is:

```
canonical product ─→ ExportAdapter ─→ XLSX bytes ─→ parser ─→ parsed dict
                                                                   │
                                                                   ▼
                                                          must equal canonical
                                                          (field-by-field)
```

If the loop closes (canonical == parsed), four guarantees hold simultaneously:
- The Export Adapter wrote every canonical field to the XLSX
- The XLSX matches Meesho's expected column structure (our parser was built from Meesho's templates)
- Enum codes and column headers are restored correctly (typos preserved per F2)
- The Strategy classes (compliance shape) work bidirectionally

Round-trip is the **single concrete test** that proves the Export Adapter is doing its job correctly. It's the technical contract that backs philosophy M6.

### 5.7.2 Two execution contexts

| Context | When it runs | Cost | Failure response |
|---|---|---|---|
| **Inline** (in `MeeshoExportAdapter.export()` pipeline step 9) | Every product export | ~500 ms | Mark export as `failed`, log internal error, surface generic "Try again" to seller, page engineer |
| **CI** (golden fixtures) | Every PR that touches adapter / parser / aliases / template seeds | ~7.5 s total for 15 fixtures | Block merge until fixed |

Inline catches bugs caused by data drift (a specific catalog has an edge case we didn't anticipate). CI catches bugs from code changes before they reach production.

### 5.7.3 The 15 golden fixtures (V1 coverage matrix)

Each fixture is a canonical product + canonical seller_profile + the expected round-trip result. Chosen to cover each meaningful axis of variation:

| # | Fixture | Super-category | Primary edge case tested |
|---|---|---|---|
| 1 | `b01_saree_10003.yaml` | Women Fashion | Brand enum size 3,730 (largest) — search-as-you-type primitive |
| 2 | `b01_lehenga_10157.yaml` | Women Fashion | 47 compulsory fields (max in corpus) — wizard step generation |
| 3 | `b02_mens_shirt_xxxxx.yaml` | Men Fashion | Apparel sizing dropdown (Length Size, Chest Size) |
| 4 | `b03_kids_onesies_10181.yaml` | Kids & Toys | Min compulsory (20) — short-form rendering |
| 5 | `b03_kids_toy_with_bis.yaml` | Kids & Toys | BIS/ISI onboarding extension export |
| 6 | `b04_mobile_webcam_13508.yaml` | Consumer Electronics | **Typo restoration** ("No. of Primiary Cameras") + Warranty step |
| 7 | `b05_kitchen_cookware.yaml` | Home & Kitchen | Unit-suffix companion fields (weight_unit, voltage_unit) + median 33 compulsory |
| 8 | `b07_grocery_chaat_masala_14366.yaml` | Grocery | **FSSAI onboarding extension** (compulsory!) + Veg/NonVeg + Shelf Life |
| 9 | `b08_office_pen.yaml` | Office Supplies | Simple short form (21 compulsory), no extensions |
| 10 | `b09_cricket_bat.yaml` | Sports | Min form (19 compulsory) — wizard with only 3 steps |
| 11 | `b10_eye_serum_12378.yaml` | Beauty & Health | **Collapsed compliance Strategy** (the only one in the corpus) |
| 12 | `b10_cream_with_license.yaml` | Beauty & Health | License/Registration extension export |
| 13 | `b11_book_with_isbn.yaml` | Books | ISBN extension (optional, demonstrates Pattern 5 advanced field rendering) |
| 14 | `b12_smartphone.yaml` | Mobiles & Tablets | RAM, OS, Battery Capacity tech-spec primitives |
| 15 | `b12_electric_kettle.yaml` | Appliances | BIS extension + Warranty step + License extension |

Coverage axes confirmed:
- **Compulsory range**: 19 (fixture 10) ↔ 47 (fixture 2)
- **Compliance shape**: standard (14 fixtures) + collapsed (fixture 11 — Eye-Serum)
- **All 6 onboarding extensions**: FSSAI (8), BIS (5, 15), R/IS/CM-L (6, optional in 14), License (12, 15), ISBN (13). Combined with universal (no extension) in fixtures 9, 10, etc.
- **Typo restoration**: fixture 6 (Webcam "Primiary"/"Seconadry")
- **Brand-pattern enum sizes**: small (10, 13), medium (3, 12), large (1)
- **All wizard steps**: basics, pricing, inventory (always), sizing (3), materials (3), food (8), tech_specs (6, 14), safety (5), warranty (6, 15), compliance (always), photos (always), description (always), advanced (13 with ISBN)
- **All input primitives**: 11 primitives × at least one fixture exercising each

### 5.7.4 Fixture file format

YAML for human readability and easy diff in code review:

```yaml
fixture_id: b07_grocery_chaat_masala_14366
description: Tests FSSAI extension + Veg/NonVeg + Shelf Life for a typical Tirupur spice seller
super_category_id: "26"
super_category_name: Grocery
meesho_leaf_id: "14366"

canonical_seller_profile:
  manufacturer_name: "Tirupur Spice Co."
  manufacturer_address: "12 Avinashi Road, Tirupur"
  manufacturer_pincode: "641604"
  packer_name: "Tirupur Spice Co."
  packer_address: "12 Avinashi Road, Tirupur"
  packer_pincode: "641604"
  importer_name: "Not Applicable"
  importer_address: "Not Applicable"
  importer_pincode: "000000"
  country_of_origin: "India"
  compliance_extensions:
    "26":   # Grocery super_id
      fssai_license_number: "10012345678901"
      fssai_expiry: "2027-12-31"

canonical_product:
  product_name: "Tirupur Chaat Masala 200g"
  variation: "Standard"
  meesho_price: 99
  mrp: 149
  inventory: 50
  net_weight_grams: 200
  net_quantity_n: 1
  generic_name: "Chaat Masala"
  brand: ""                    # not in Meesho's list, left blank per V1 escape hatch
  brand_name: "Tirupur Spice"  # free-text fallback used instead
  veg_nonveg: "Veg"
  maximum_shelf_life: "12 months"
  added_preservatives: "No"
  packaging_type: "Pouch"
  image_1_front_url: "gs://meesell-images/test/chaat_masala_front.jpg"
  image_2_url: "gs://meesell-images/test/chaat_masala_side.jpg"

expected_round_trip:
  same_as: canonical_product  # alias: assert parsed_dict == canonical_product

edges_tested:
  - FSSAI extension column appears in XLSX with correct value
  - Veg/NonVeg renders as compulsory dropdown
  - Brand blank but Brand Name populated — V1 escape hatch works
  - Compliance fields auto-filled from seller_profile
  - Image 2 present, Images 3 and 4 absent

skip_reason: null   # set to a string if this fixture is temporarily quarantined
```

Fixtures live in `backend/app/services/export_adapter/tests/golden_fixtures/`.

### 5.7.5 The validator's pass/fail checks

```python
class RoundTripValidator:
    def validate(self, xlsx_bytes: bytes, canonical: dict, template: Template) -> ValidationReport:
        parsed = self.parser.parse_bytes(xlsx_bytes)

        # Check 1 — every canonical field appears in parsed with same value
        missing = {k: v for k, v in canonical.items() if k not in parsed.fields}
        # Check 2 — no spurious fields in parsed
        extra = {k: v for k, v in parsed.fields.items() if k not in canonical}
        # Check 3 — value equality (with type-aware comparison)
        mismatches = {
            k: (canonical[k], parsed.fields[k])
            for k in set(canonical) & set(parsed.fields)
            if not self._equal(canonical[k], parsed.fields[k])
        }
        # Check 4 — image rule preserved (4 slots, slot 1 compulsory)
        image_rule_violated = (
            sum(1 for f in parsed.fields if f.startswith("image_")) != 4
        )
        # Check 5 — compliance shape correctly applied
        if template.compliance_shape == "collapsed":
            assert "manufacturer_details" in parsed.fields  # combined field present
        else:
            assert "manufacturer_name" in parsed.fields     # 9-field standard

        return ValidationReport(
            passed = not (missing or extra or mismatches or image_rule_violated),
            missing = missing,
            extra = extra,
            mismatches = mismatches,
            image_rule_violated = image_rule_violated,
        )
```

`_equal` handles common type coercions (str vs int for numeric fields, ISO date vs datetime, trimmed whitespace) so trivial differences don't flag.

### 5.7.6 Failure modes + diagnostics

When a round-trip fails, the validator produces a diff like:

```
Fixture: b07_grocery_chaat_masala_14366
Step: 9 (round-trip validation)
Result: FAILED

Missing in parsed (lost in pipeline):
  - fssai_license_number  (expected: "10012345678901")

Mismatches:
  - net_weight_grams: expected 200, got "200g" (type leaked: number → string)

Diagnostic:
  → Check Step 4 (compliance strategy) for fssai_license_number routing
  → Check Step 5 (enum translator) for net_weight_grams type coercion
```

Each failure points the engineer at which pipeline step likely broke. Step numbers from §5.5.4. This makes debugging deterministic instead of guesswork.

### 5.7.7 Fixture maintenance (when Meesho changes templates)

Quarterly Meesho refresh flow (owned by `meesell-scraper-maintainer`):

1. Scraper re-fetches XLSX templates → updates `data/meesho_templates/`
2. Parser produces new `data/parsed/batch_NN_*.json`
3. `scripts/build_template_schemas.py` re-builds schema_jsonb
4. **Round-trip test sweep**: run all 15 fixtures against new schemas
5. Diff report:
   - Fixtures that still pass → no action
   - Fixtures that fail → likely the template's column structure changed
   - Engineer investigates, updates fixtures or adapter, re-runs

If a STRICT universal field changed type, this is a schema migration event (rare). Otherwise, fixture updates suffice.

### 5.7.8 Smoke test (manual, pre-release)

Round-trip with our own parser proves internal consistency, but **the ultimate ground truth is Meesho's actual upload validator.** Before each release:

1. Manually generate XLSX for 3-5 representative products (pick from the fixture list)
2. Upload each to Meesho's **staging supplier panel** (`supplier.meesho.com` test account)
3. Verify Meesho's validator accepts each one
4. If rejected: document the exact rejection reason in `docs/release_notes.md`, fix the adapter, re-test, then re-release
5. If accepted: ship

The smoke test is manual and runs maybe quarterly (per release). Not a CI gate. But it's the only test that catches a divergence between our parser's understanding of Meesho's format and Meesho's actual validator.

### 5.7.9 Performance budget

| Test | Duration | Notes |
|---|---|---|
| Single fixture round-trip (parse + validate) | ~500 ms | Dominated by XLSX read |
| All 15 fixtures sequentially | ~7.5 s | Within CI budget |
| All 15 fixtures parallelised | ~600 ms | If CI runner has 4+ cores |
| Inline round-trip on every product export | ~500 ms | Added to step 9 of the adapter pipeline |

### 5.7.10 Test code structure

```
backend/app/services/export_adapter/tests/
├── round_trip_runner.py            # Pytest plugin — discovers fixtures, runs validation
├── golden_fixtures/                 # 15 YAML fixtures (§5.7.3)
│   ├── README.md                    # Coverage matrix mirrored from §5.7.3
│   ├── b01_saree_10003.yaml
│   ├── ... (14 more)
├── conftest.py                      # Pytest fixtures: ExportAdapter instance, parser, mock GCS
└── test_round_trip.py               # @pytest.mark.parametrize over all fixtures
```

CI configuration:

```yaml
# .gitlab-ci.yml (excerpt)
round_trip_tests:
  stage: test
  script:
    - pytest backend/app/services/export_adapter/tests/test_round_trip.py -v
  only:
    changes:
      - backend/app/services/export_adapter/**/*
      - scripts/parse_meesho_xlsx.py
      - data/parsed/canonical_field_aliases.json
      - data/parsed/field_display_overrides.json
      - backend/alembic/versions/*templates*.py
```

The path-based triggers mean round-trip tests only run when relevant code changes — fast feedback for unrelated PRs.

### 5.7.11 What this section adds to the architecture

| Change | Where |
|---|---|
| 15 golden fixture YAML files | `backend/app/services/export_adapter/tests/golden_fixtures/` |
| `RoundTripValidator` class (used by Adapter + tests) | `backend/app/services/export_adapter/pipeline/round_trip_validator.py` |
| Smoke-test runbook | `docs/release_runbook.md` (new file, owned by `meesell-deployer` when registered) |
| CI gate | `.gitlab-ci.yml` round_trip_tests job |
| No new tables, no new APIs, no new primitives | The Adapter and Parser already exist; this section specifies their test contract |

---

## Section 6 — Caching Strategy

**Philosophy anchors:** M10 + F8 govern what may be cached and at what layer. Any cached payload that contains `meesho_column_header`, `meesho_enum_code`, or `meesho_column_index` is a philosophy violation — those fields must only be materialised inside the Export Adapter, never in a cacheable API response.

---

## 6.1 What Gets Cached

| Cache class | Source table | Why it's hot |
|---|---|---|
| **Template schema** | `templates.schema_jsonb` | 3,557 schemas; every wizard load hits one. Average JSONB size ~8 KB. |
| **Field enum values** | `field_enum_values.enum_entries` | 291 Brand-pattern fields; largest sets have up to 4,481 entries. Served on every dropdown keystroke. |
| **Category tree** | `categories` (all rows, path + super info) | Sent as compressed tree to Gemini for Smart Picker; also the manual browse fallback. Rarely changes. |
| **Seller profile** | `seller_profile` | Read on every `/api/v1/products` POST and during wizard render (compliance step auto-fill). |
| **Category picker suggestion** | `categories/suggest` response | Gemini call costs ~1,500 tokens; identical product descriptions should reuse the result for 24h. |

**Excluded from caching:** `products`, `product_images`, `pricing_calcs`, `exports`. These are user-owned mutable state — per-user, per-session, no shared cache benefit.

---

## 6.2 Cache Tiers

Three tiers compose the caching stack:

```
[Angular PWA / browser]
      │ HTTP Cache-Control + ETag
      ▼
[FastAPI worker — in-memory LRU (per-process)]
      │ miss → Valkey lookup
      ▼
[Valkey DB 3 — shared app cache]
      │ miss → PostgreSQL query
      ▼
[PostgreSQL 16]
```

**Valkey DB assignment (per CLAUDE.md locked convention):**

| DB | Purpose |
|---|---|
| DB 0 | Sessions, OTP, rate limits (existing) |
| DB 1 | Celery broker (existing) |
| DB 2 | Celery result backend (existing) |
| **DB 3** | **Application cache — template schemas, enum values, category tree, seller profiles** |

Connection: `redis://valkey:6379/3` (Valkey uses Redis protocol; library: `redis.asyncio`).

---

## 6.3 TTLs per Cache Class

| Cache class | Valkey TTL | Worker LRU TTL | Browser Cache-Control |
|---|---|---|---|
| Template schema | 24 h | 15 min | `max-age=86400, stale-while-revalidate=3600` |
| Field enum values | 24 h | 15 min | `max-age=86400, stale-while-revalidate=3600` |
| Category tree (full) | 24 h | 30 min | `max-age=86400` |
| Category picker suggestion | 24 h | — | `max-age=86400` |
| Seller profile | 5 min | — | `no-store` (user-specific, sensitive) |

Rationale: templates and enum values are updated only on the quarterly Meesho refresh cycle. A 24-hour TTL is conservative relative to that cycle. Seller profile is personal compliance data and must never be stale longer than 5 minutes — a seller updating their FSSAI number must see it reflected on the next API call.

---

## 6.4 Cache Key Patterns

Schema versioning is embedded in every key so a quarterly refresh invalidates atomically without a cache flush command.

```
# Template schema — version-tagged for atomic quarterly refresh
cache:template:{template_id}:v{schema_version}

# Field enum values — keyed by category + field name
cache:enum:{category_id}:{canonical_field_name}:v{schema_version}

# Category tree (full serialised JSON)
cache:category_tree:v{schema_version}

# Smart Picker suggestion — keyed by SHA-256 of the description
cache:category_suggest:{description_sha256}

# Seller profile — keyed by user_id, no version (TTL-based invalidation)
cache:seller_profile:{user_id}
```

`schema_version` is a short string derived from `templates.parser_version` + the quarterly refresh date stamp, e.g. `"0.2-2026Q1"`. It is stored as a single Valkey key `cache:schema_version` (type: string) and read once at worker startup into a process-level constant.

**Philosophy guardrail (M10 + F8):** template schema cached in Valkey stores the **display + canonical layers only** — `display_label`, `display_help`, `canonical_name`, `primitive`, `marker`, etc. The `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` fields are **stripped before serialisation into cache**. The Export Adapter fetches the full `schema_jsonb` directly from PostgreSQL (or a separate, adapter-internal cache keyed `adapter:template:{template_id}`) so that Meesho wire format is never accessible through the public cache namespace.

---

## 6.5 Invalidation Flow

### 6.5.1 Quarterly Meesho refresh

1. `meesell-xlsx-parser` re-parses all Meesho XLSX files; `scripts/build_template_schemas.py` runs (idempotent).
2. Script increments `schema_version` (e.g. `"0.2-2026Q2"`) and writes it to `cache:schema_version` in Valkey.
3. All old version-tagged keys (`cache:template:*:v0.2-2026Q1`) are now unreachable — they expire naturally within 24 h. No `FLUSHDB` required.
4. New keys are populated lazily on first request after the version bump.
5. Worker in-memory LRU is invalidated on the next request (cache miss triggers a Valkey fetch with new version key).

### 6.5.2 Seller profile PATCH

Any `PATCH /api/v1/seller-profile` or `PATCH /api/v1/seller-profile/compliance/{super_id}` handler calls:

```python
await valkey.delete(f"cache:seller_profile:{user_id}")
```

immediately after committing the database transaction. The 5-minute TTL serves as a safety net; explicit deletion ensures sub-second consistency.

### 6.5.3 No schema hot-patching in V1

If a single template is corrected outside the quarterly cycle (e.g. a critical typo in a help string), the fix is deployed by incrementing `schema_version` for that batch only. This is a deliberate V1 simplification — full refresh is quick enough (<2 min) that selective invalidation is not worth the complexity.

---

## 6.6 HTTP Cache Headers

Responses that serve cacheable data include explicit cache headers. The FastAPI service layer sets them via a `CacheHeaders` helper.

```
# Template schema endpoint
GET /api/v1/categories/{id}/schema
→ Cache-Control: public, max-age=86400, stale-while-revalidate=3600
→ ETag: "{template_id}-{schema_version}"
→ Last-Modified: {templates.parsed_from_xlsx_at}

# Field enum endpoint (large, paginated)
GET /api/v1/categories/{id}/field-enum/{name}
→ Cache-Control: public, max-age=86400, stale-while-revalidate=3600
→ ETag: "{category_id}-{field_name}-{schema_version}"

# Category tree
GET /api/v1/categories
→ Cache-Control: public, max-age=86400
→ ETag: "{schema_version}"

# Seller profile (private, sensitive)
GET /api/v1/seller-profile
→ Cache-Control: no-store
→ (no ETag — stale data is never acceptable here)
```

The browser honours these headers natively. The Angular `HttpClient` respects `ETag` / `If-None-Match` — a 304 Not Modified response avoids parsing 8 KB of JSON on every wizard load. For enum endpoints, the PWA service worker (Angular's `@angular/pwa`) pre-caches the top-100-category enum responses on first load via the `ngsw-config.json` asset strategy.

---

## 6.7 Hot/Cold Tier Strategy

The in-process LRU on FastAPI workers handles the top 100 categories by traffic forecast. This avoids a Valkey round-trip (~0.5–1 ms on the same K3s node) for the most frequent lookups.

```python
# backend/app/cache/lru.py
from functools import lru_cache
from typing import Any

_TEMPLATE_LRU: dict[str, Any] = {}   # populated from Valkey on first miss
_MAX_HOT_TEMPLATES = 100             # covers top-100 categories by traffic

# Worker startup: pre-warm LRU with top-100 categories
# (category IDs ranked by historical traffic or, at launch, by super-category size proxy)
async def prewarm_lru(valkey: Redis, top_category_ids: list[str]) -> None:
    for cat_id in top_category_ids[:_MAX_HOT_TEMPLATES]:
        key = f"cache:template:{cat_id}:v{SCHEMA_VERSION}"
        data = await valkey.get(key)
        if data:
            _TEMPLATE_LRU[cat_id] = json.loads(data)
```

| Data class | Hot tier (worker LRU) | Cold tier (Valkey DB 3) |
|---|---|---|
| Template schemas | Top 100 categories | All 3,557 templates |
| Enum values | Top 100 × top 10 fields = 1,000 entries | All 291 Brand-pattern fields (all categories) |
| Category tree | Full tree (single object, ~150 KB) | Same — Valkey as fallback |
| Seller profile | Not in LRU (user-specific) | Valkey only (5-min TTL) |

The 100-category threshold is a V1 approximation. Traffic instrumentation in V1.5 will replace the static list with a Redis Sorted Set of live request counts.

---

## 6.8 Cache Stampede Protection

When a Valkey cache miss occurs for a hot key (e.g. a popular Brand enum with 3,730 values), concurrent requests must not all race to rebuild from PostgreSQL simultaneously.

**Pattern: single-flight via Valkey `SET NX` lock**

```python
async def get_or_populate(valkey: Redis, key: str, build_fn, ttl: int) -> Any:
    # 1. Try cache hit
    cached = await valkey.get(key)
    if cached:
        return json.loads(cached)

    # 2. Acquire build lock (NX = only first caller wins, PX = 5s expiry)
    lock_key = f"lock:{key}"
    acquired = await valkey.set(lock_key, "1", nx=True, px=5000)

    if acquired:
        # 3. Lock winner: build + populate
        try:
            value = await build_fn()
            await valkey.setex(key, ttl, json.dumps(value))
            return value
        finally:
            await valkey.delete(lock_key)
    else:
        # 4. Lock losers: short-poll until lock releases (max 2s)
        for _ in range(20):
            await asyncio.sleep(0.1)
            cached = await valkey.get(key)
            if cached:
                return json.loads(cached)
        # 5. Fallback: go to PostgreSQL directly if lock holder timed out
        return await build_fn()
```

This keeps concurrent enum fetches at peak load from spawning 50 simultaneous PostgreSQL queries for the same Brand enum. The 5-second lock TTL ensures the lock self-heals if the winning worker crashes mid-build.

In-process LRU pre-warming (§6.7) eliminates stampede risk entirely for the top-100-category keys, since they're populated at worker startup.

---

## 6.9 Estimated Valkey Memory Footprint

| Corpus segment | Count | Avg size | Total (uncompressed) |
|---|---|---|---|
| Template schemas (display+canonical layers only, meesho layer stripped) | 3,557 | ~5 KB | ~17.8 MB |
| Field enum values — small sets (≤100 values) | ~200K values ÷ ~30 avg = ~6,700 keys | ~2 KB | ~13.4 MB |
| Field enum values — large sets (Brand-pattern, up to 4,481 values) | 291 fields × varies | ~50 KB avg | ~14.6 MB |
| Category tree (full compressed JSON) | 1 key | ~150 KB | ~0.2 MB |
| Seller profiles (5-min TTL, active sellers at peak) | 500 concurrent sessions (V1 est.) | ~2 KB | ~1.0 MB |
| Category picker suggestions | Variable (24h TTL) | ~0.5 KB | ~0.5 MB (steady-state) |
| **Estimated total** | | | **~47 MB** |

With Valkey's default overhead (hash table, per-key metadata ~100 bytes/key), add ~20% headroom:

**~57 MB peak working set for application cache (DB 3).**

The K3s Valkey pod is configured with `maxmemory 128mb` (shared across DB 0–3). The ~57 MB app cache sits comfortably below this ceiling alongside the OTP/session and Celery data in DB 0–2, which add at most 10–15 MB at peak. The `maxmemory-policy` should be set to `allkeys-lru` so that under pressure, the least-recently-used cache entries are evicted first — natural for a corpus where top categories dominate traffic.

> Compression note: Most template schemas and enum arrays compress well. If memory pressure becomes an issue, serialising cache values with `zstd` or `msgpack` instead of plain JSON cuts the 47 MB estimate to ~18–22 MB. Defer until measured.


---

## Section 7 — Search & Indexing (Manual Browse Fallback)

**Scope:** Category browse and search for 3,772 Meesho leaf nodes on PostgreSQL 16 (self-hosted Supabase image, K3s).

---

## 7.1 Two Search Paths

MeeSell exposes category selection through two parallel flows that share the same `categories` table but use entirely different execution paths:

| Path | Trigger | Backend entry point |
|---|---|---|
| **Smart Picker** (§5.1) | Seller enters a product description; Gemini suggests top-5 leaves with confidence | `GET /api/v1/categories/suggest?q=<desc>` |
| **Manual Browse** (this section) | AI confidence < 70%, AI timeout, or seller prefers to navigate the tree | `GET /api/v1/categories/browse?q=&super_id=&limit=&offset=` |

The two paths are independent. Smart Picker owns the Gemini embedding + compressed-tree prompt chain. Manual Browse owns the trigram index queries defined in this section.

---

## 7.2 Manual Browse — Query Types

Manual Browse handles three overlapping query patterns against `categories`:

1. **Prefix match** — seller types "kurti"; returns leaves whose `leaf_name` begins with or closely matches that prefix. Tolerates one transposition ("kurtee", "kurti").
2. **Substring / path search** — seller types "ethnic"; matches anywhere in the full `path` column (e.g. "Women Fashion > Ethnic Wear > Kurtis"). Enables mid-tree discovery without knowing the exact leaf name.
3. **Hierarchical drilldown** — seller browses top-level super-categories (`super_name`), then narrows to leaves within a chosen `super_id`. No text query required; uses `super_id` filter alone.

All three patterns are served by the single `/browse` endpoint using optional parameters.

---

## 7.3 PostgreSQL FTS vs pg_trgm — Recommendation: pg_trgm

**Decision: use `pg_trgm` (trigram similarity), not `tsvector` full-text search.**

Reasoning:

- **Category names are short tokens, not documents.** FTS (`tsvector`/`tsquery`) is optimised for free-text documents where stemming, stop-word removal, and ranking by term frequency add value. A leaf name like "Sarees" or a path segment like "Ethnic Wear" produces no useful lexemes after stemming and no meaningful tf-idf signal.
- **Trigram handles spelling variation without configuration.** Meesho source data contains drift ("Primiary", "Seconadry" are present in templates). Sellers typing on mobile keyboards make similar errors. `pg_trgm` similarity matching catches these without maintaining a synonym dictionary.
- **Prefix and substring queries map directly to GIN trigram operators.** `ILIKE '%kurti%'` accelerates via a GIN trigram index with zero extra application code. FTS requires `plainto_tsquery` + lexeme normalisation for the same coverage and still cannot match mid-string substrings without `pg_trgm` anyway.
- **3,772 rows is a small working set.** The performance ceiling of trigram GIN on this cardinality is well inside the 200 ms budget even on shared K3s resources.

FTS remains appropriate for long-text matching (product descriptions, AI prompt inputs) but is the wrong tool for this 3-column category browse.

---

## 7.4 Index DDL

Enable the extension once (idempotent migration step):

```sql
-- Migration: 0007_category_search_indexes.sql
-- Run with: alembic upgrade head
-- Concurrent creation avoids locking categories for seeding

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Primary browse index: full path string ("Women Fashion > Ethnic Wear > Sarees")
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_path_trgm
  ON categories
  USING GIN (path gin_trgm_ops);

-- Leaf-name index: prefix + fuzzy match on the terminal category name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_leaf_name_trgm
  ON categories
  USING GIN (leaf_name gin_trgm_ops);

-- Super-name index: top-level drilldown (e.g. "Women Fashion", "Home & Kitchen")
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_super_name_trgm
  ON categories
  USING GIN (super_name gin_trgm_ops);

-- B-tree on super_id retained from §2.3 DDL — drives filter-only drilldown
-- CREATE INDEX idx_categories_super ON categories(super_id);  -- already exists per §2.3
```

All three GIN indexes are built `CONCURRENTLY` so the table remains readable during initial seed and during quarterly refreshes. The existing B-tree on `super_id` (defined in §2.3) handles the filter-only drilldown case without a trigram scan.

---

## 7.5 Query Performance Budget

| Operation | Target P95 | Notes |
|---|---|---|
| Prefix / fuzzy leaf name match | ≤ 100 ms | GIN trigram on `leaf_name`; 3,772 rows, small index |
| Full path substring search | ≤ 150 ms | GIN trigram on `path`; path strings up to ~80 chars |
| Super-category drilldown (filter only) | ≤ 50 ms | B-tree `super_id` index; no text scan |
| Combined query (q + super_id filter) | ≤ 200 ms | GIN + B-tree bitmap AND; PostgreSQL 16 planner handles this well |

At 3,772 rows the entire `categories` table fits comfortably in PostgreSQL's shared_buffers (default 128 MB). After the first query the working set is hot in buffer cache, keeping subsequent queries under 10 ms in practice. The 200 ms budget is the contract ceiling, not the expected steady-state.

---

## 7.6 Ranking Strategy

Results are ordered by a two-factor score computed in SQL:

```sql
SELECT
  id,
  meesho_leaf_id,
  leaf_name,
  path,
  super_name,
  -- Factor 1: trigram similarity to query (0.0–1.0)
  GREATEST(
    similarity(leaf_name, :q),
    similarity(path,      :q)
  ) AS match_score,
  -- Factor 2: popularity weight (uniform 1.0 for V1; replaced by traffic data in V1.5)
  1.0 AS popularity_weight
FROM categories
WHERE
  (path      % :q OR leaf_name % :q)  -- GIN trigram shortlist
  AND (:super_id IS NULL OR super_id = :super_id)
ORDER BY (match_score * popularity_weight) DESC
LIMIT :limit OFFSET :offset;
```

**V1 popularity weight is uniform (1.0).** Seasonal / category traffic data is not available at launch. When Meesho quarterly refresh data includes view or GMV signals, the `categories` table gains a `popularity_score NUMERIC(6,4) DEFAULT 1.0` column and the weight becomes data-driven without changing the query shape.

The `%` operator (trigram similarity threshold) uses PostgreSQL's default `pg_trgm.similarity_threshold = 0.3`, which is appropriate for short category-name tokens. Tune downward (e.g. 0.2) if recall is insufficient during acceptance testing.

---

## 7.7 API Endpoint Shape

```
GET /api/v1/categories/browse
    ?q=<text>          — optional; trigram search against leaf_name + path
    &super_id=<id>     — optional; filter to one super-category (drilldown)
    &limit=<int>       — default 20, max 50
    &offset=<int>      — default 0

Response 200 OK:
{
  "items": [
    {
      "id": "uuid",
      "meesho_leaf_id": "10003",
      "leaf_name": "Sarees",
      "path": "Women Fashion > Ethnic Wear > Sarees & Petticoats > Sarees",
      "super_id": "11",
      "super_name": "Women Fashion",
      "match_score": 0.82
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0,
  "q": "saree",
  "super_id": null
}
```

When `q` is absent and `super_id` is absent, the endpoint returns all 3,772 leaves ordered by `super_name`, `path` — the full tree for initial render. The frontend Smart Picker component pre-fills `q` with the original seller description when triggering the fallback redirect.

---

## 7.8 Seed and Refresh

**Initial seed** (first deploy):
1. Alembic migration `0007` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` and all three `CREATE INDEX CONCURRENTLY` statements.
2. `meesho_categories.json` and `meesho_category_tree.json` (already in `backend/app/data/`) are loaded via the seeding script defined in §2.6 of MVP_ARCHITECTURE.md.
3. GIN indexes are built automatically after row insertion completes.

**Quarterly Meesho refresh** (new XLSX batch from `meesell-xlsx-parser`):
1. New rows are inserted into `categories` using `INSERT ... ON CONFLICT (meesho_leaf_id) DO UPDATE`.
2. GIN indexes update incrementally on each row write — no manual `REINDEX` required for normal refreshes.
3. If a full rebuild is ever needed (e.g. after a bulk schema change), run:
   ```sql
   REINDEX INDEX CONCURRENTLY idx_categories_path_trgm;
   REINDEX INDEX CONCURRENTLY idx_categories_leaf_name_trgm;
   REINDEX INDEX CONCURRENTLY idx_categories_super_name_trgm;
   ```
   `CONCURRENTLY` keeps the table readable throughout. This is safe on PostgreSQL 16 for both `CREATE` and `REINDEX`.

---

## 7.9 Smart Picker Fallback Handoff

When the Smart Picker (`GET /api/v1/categories/suggest`) returns a low-confidence or timed-out result, the frontend automatically redirects to Manual Browse:

**Trigger conditions (either):**
- All returned suggestions have `confidence < 0.70`
- The `/suggest` request exceeds 8 s (Gemini Flash P95 is ~3 s; 8 s is the hard timeout)

**Handoff mechanism:**
1. Frontend Angular service detects the trigger condition in the `suggest` response handler.
2. Router navigates to `/catalog/create/browse` with the original description pre-filled as the `q` query parameter.
3. The `/browse` endpoint runs immediately with the seller's description as the search string — the seller sees pre-filtered results without re-typing.
4. If the seller selects a leaf from Browse, the catalog creation flow resumes identically to a Smart Picker acceptance.

This keeps the handoff invisible to the seller: the description they typed continues driving the search, just through the trigram path instead of the Gemini path.


---

## Section 8 — AI Model Operations (Gemini 2.5 Flash)

MeeSell uses **Google Gemini 2.5 Flash** (locked decision per CLAUDE.md item 3) for three core AI workloads: Smart Category Picker (text→JSON), AI Auto-fill (text+schema→JSON), and Image Watermark Detection (vision→JSON). This section specifies operational constraints, cost ceilings, fallback behavior, and monitoring for V1 launch.

---

## 9.1 Three Workloads and Rate Limits

### Smart Category Picker
- **Input:** seller's natural-language product description (e.g., "Blue cotton saree with mirror work")
- **Output:** JSON `{"top_n": [{"leaf_id": "10003", "confidence": 0.93}, ...]}` (TOP-5 leaves)
- **Gemini API usage:** 1 call per picker request; ~8K input tokens (compressed 3-level category tree) + ~200 output tokens
- **Rate limit ceiling per seller per hour:** 100 calls/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 500 calls/day for V1 launch

### AI Auto-fill
- **Input:** product description + schema (compulsory fields + allowed enum values); ~3K input tokens
- **Output:** JSON `{"field_1": {"value": "...", "confidence": 0.91}, ...}` + validation pass/fail per field
- **Gemini API usage:** 1 call per product; ~3K input tokens (per-category schema) + ~1K output tokens (JSON mode)
- **Rate limit ceiling per seller per hour:** 50 calls/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 200 calls/day for V1 launch

### Image Watermark Detection
- **Input:** single JPEG image (already validated for resolution + RGB)
- **Output:** JSON `{"has_watermark": boolean, "confidence": 0.87, "explanation": "..."}`
- **Gemini API usage:** 1 vision call per image; ~10K token equivalent (image embedding + analysis)
- **Rate limit ceiling per seller per hour:** 30 images/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 100 images/day for V1 launch

**Gemini 2.5 Flash published limits (verify before launch):** 2,000 RPM per project, 400,000 TPM. MeeSell's per-hour ceilings ensure we stay well below these.

---

## 9.2 Token Budget and Estimated Cost Per Call

### Smart Category Picker
| Component | Tokens | Notes |
|-----------|--------|-------|
| Compressed category tree (3 levels) | 8,000 | Precomputed once per day, reused |
| Seller's description | 150–300 | Variable; safety budget 500 |
| JSON schema contract | 100 | Fixed prompt instruction |
| **Input total** | ~8,500 | |
| **Output (top-5 + confidence)** | ~200–300 | JSON mode; predictable |
| **Cost per call** | ₹0.02–0.03 | At ~₹0.05 per 1K input + ₹0.20 per 1K output |

### AI Auto-fill
| Component | Tokens | Notes |
|-----------|--------|-------|
| Product description | 200–400 | Seller provided |
| Category schema (compulsory fields only) | 2,500–3,000 | Per-category enum-constrained list |
| Prompt instructs enum enforcement | 150 | Fixed |
| **Input total** | ~3,000–3,500 | |
| **Output (field suggestions JSON)** | 800–1,200 | JSON mode; parser validates |
| **Cost per call** | ₹0.02–0.04 | |

### Image Watermark Detection
| Component | Tokens | Notes |
|-----------|--------|-------|
| Image (base64 embedded in request) | ~10,000 equiv. | Gemini counts images as fixed cost (~4K tokens per image) |
| Prompt instructions | 100 | Fixed |
| **Input total** | ~10,100 equiv. | |
| **Output (JSON)** | 100–300 | Text analysis of image; JSON mode |
| **Cost per call** | ₹0.01–0.02 | Vision pricing differs from text; verify against Gemini rate card |

**Cost ceiling per call (all three workloads combined):** target ≤₹0.05 average. Current estimates are **within budget**.

---

## 9.3 Fallback Strategy on Outage

### Smart Category Picker
- **On timeout or error:** return HTTP 200 with `fallback: true` and empty `top_n` array
- **Frontend behavior:** display manual browse UI (per §3.3 MVP_ARCHITECTURE.md — seller can search/filter the full category tree)
- **Seller impact:** ~3 extra taps to find category manually; no blocker to catalog creation

### AI Auto-fill
- **On timeout or error:** return HTTP 200 with `skipped: true` and empty suggestions object
- **Frontend behavior:** show toast banner "AI is temporarily busy. Please fill these fields manually."
- **Seller impact:** seller must type values directly; form validation still enforces enum constraints

### Image Watermark Detection
- **On timeout or error:** return `{"watermark_check": "skipped", "skipped_reason": "service_error"}`
- **Frontend behavior:** show info banner "Watermark check skipped. Please verify your image has no visible branding or watermarks."
- **Seller impact:** image uploads succeed but marked as "pending_manual_review"; compliance officer flags at export time if needed

**Timeout threshold:** 10 seconds per call (Celery task timeout). If exceeded, graceful degradation, not error.

---

## 9.4 Prompt Versioning and A/B Testing

Prompt templates live in `/backend/app/ai/prompts/`:

```
backend/app/ai/prompts/
├── category_picker_v1.py         # Current production (high-precision, top-5)
├── category_picker_v2.py         # Experimental (faster, top-3)
├── autofill_v1.py                # Current production (enum-constrained, confidence > 0.80)
├── autofill_v1_5.py              # Experimental (adds user-intent inference)
└── watermark_vision_v1.py        # Current production (binary + explanation)
```

Active version configured in `backend/app/config.py`:

```python
class AIConfig(BaseSettings):
    CATEGORY_PICKER_VERSION: str = "v1"  # env var, can switch without restart
    AUTOFILL_VERSION: str = "v1"
    WATERMARK_VERSION: str = "v1"
```

**A/B testing in V1.5:** introduce a `user.ai_experiment_group` field; dispatch ~10% of calls to v2 variants, track accuracy + latency separately.

---

## 9.5 Eval Framework and Golden Test Sets

### Category Picker Golden Set
- **File:** `evals/category_picker_golden.yaml`
- **Size:** 50 natural-language descriptions (diverse: apparel, food, electronics, beauty)
- **Ground truth:** hand-annotated top-3 correct leaf IDs (seller or coordinator manually categorizes each example)
- **Pass criteria:** ≥80% recall@5 (the model's top-5 must include the correct leaf for ≥40 of 50 examples)
- **Automation:** CI runs this before every Gemini API version upgrade

### Auto-fill Golden Set
- **File:** `evals/autofill_golden.yaml`
- **Size:** 30 product specs (5 per super-category: Apparel, Grocery, Electronics, Beauty, Home & Kitchen)
- **Ground truth:** hand-filled product data for each spec (e.g., "Blue cotton saree" → brand="...", fabric="Cotton", weight_grams="200")
- **Pass criteria:** (1) **0% invalid enum values** — no suggestion outside the allowed enum for that category; (2) **≥70% field accuracy** — suggestion exactly matches ground truth or is synonymous (e.g., "Silk" vs "Mulberry Silk" both correct for fabric)
- **Automation:** CI fails if any invalid enum leaked through; tracking scores per super-category

### Image Watermark Golden Set
- **File:** `evals/watermark_golden/` (30 sample JPEGs)
- **Composition:** 15 images with visible watermarks (brand logo, URL stamp, copyright mark), 15 without
- **Ground truth:** binary label per image (has_watermark: true/false)
- **Pass criteria:** ≥85% accuracy (28 of 30 correct classifications)
- **Automation:** nightly run against Gemini, alert if accuracy drops below threshold

**Eval runner:** `/scripts/run_ai_evals.py` (Bash + Python). Output: JSON report with per-workload metrics, printed to stdout and appended to `.evals/eval_log.jsonl` for trending.

---

## 9.6 Tracing and Observability via LangFuse

Every AI call is traced using **LangFuse SDK** (Python `langfuse` library, async decorator pattern).

### Tracing instrumentation

```python
from langfuse.decorators import observe

@observe(name="category_picker")
async def suggest_categories(description: str) -> dict:
    """Calls Gemini category picker, traces input/output/cost."""
    # LangFuse automatically captures:
    # - input: {"description": "..."}
    # - output: {"top_n": [...]}
    # - tokens_in, tokens_out (from Gemini response)
    # - latency_ms
    # - cost_usd (computed from token counts)
    result = await gemini_client.suggest_categories(description)
    return result
```

### LangFuse dashboard metrics

- **Per-call trace:** input, output, tokens, latency, cost, error (if any)
- **Cost attribution:** tag with `user_id` + `workload` so costs are rolled up per seller
- **Golden test eval result:** if trace matches golden test ID, append `eval_passed: true/false`
- **Latency distribution:** P50 / P95 / P99 per workload
- **Error rate:** % of calls returning error or timeout

### Alerts

- **Cost threshold:** alert when any user's daily AI cost > ₹2
- **Error rate:** alert if error rate > 5% in 1-hour window
- **Latency regression:** alert if P95 latency > 8 seconds (baseline)

---

## 9.7 Hallucination Guardrails (M7 Enforcement)

**MANDATE M7** (Core Philosophy) states: "AI works in canonical space. Validation checks against the Meesho enum codes. **AI never produces values that wouldn't survive export.**"

Three-layer enforcement:

### Layer 1: Prompt-level constraint
Gemini's prompt instruction explicitly forbids free-text enum suggestions:

```
"For each enum field below, you MUST choose ONLY from the allowed_values list. 
Never invent or suggest values outside this list. 
If no good match exists, return null."

Example:
  FIELD: Fabric
  ALLOWED: ["Cotton", "Silk", "Polyester", "Wool", "Linen"]
  SELLER INPUT: "cotton-silk blend"
  YOUR SUGGESTION: "Silk" (closest match in list) OR null (too ambiguous)
  NEVER: "Cotton-Silk blend" (not in list)
```

### Layer 2: Parser-level rejection
The `autofill_parser.py` validates every suggestion before storage:

```python
def validate_autofill_suggestion(field: FieldSchema, suggestion: str) -> bool:
    """Reject suggestions outside the field's enum."""
    if field.data_type != "dropdown":
        return True  # non-enum fields always valid
    
    if suggestion not in field.allowed_values:
        logger.warning(f"Invalid enum: {field.name}={suggestion}")
        return False  # drop this suggestion
    
    return True
```

Invalid suggestions are dropped silently (not stored in `ai_suggestions_jsonb`).

### Layer 3: Backend re-validation at export time
When exporting (Export Adapter), the system re-validates every enum value before writing to XLSX:

```python
def validate_for_export(row: dict, schema: TemplateSchema) -> None:
    """Final check: no invalid enums make it to Meesho."""
    for field in schema.fields:
        if field.data_type == "dropdown":
            value = row.get(field.canonical_name)
            if value and value not in field.allowed_values:
                raise EnumNotFoundError(
                    f"{field.name}: {value} is not in Meesho's allowed list"
                )
```

**Result:** even if Layers 1 and 2 fail, Layer 3 catches the error before XLSX generation, preventing invalid exports.

---

## 9.8 Cost Monitoring and Budget Alarms

### Daily cost dashboard
Backend exposes `/api/v1/admin/costs?date=2026-06-04` (coordinator-only):

```json
{
  "date": "2026-06-04",
  "global_total_usd": 0.83,
  "global_total_inr": 69,
  "by_workload": {
    "category_picker": {"calls": 340, "cost_usd": 0.34},
    "autofill": {"calls": 210, "cost_usd": 0.42},
    "watermark": {"calls": 95, "cost_usd": 0.07}
  },
  "by_seller_top_10": [
    {"seller_id": "seller_123", "cost_usd": 0.12},
    ...
  ]
}
```

Data sourced from Valkey `cost:{date}` hash updated in real-time by each AI call.

### Cost alarm triggers

1. **Per-seller per-day cap:** ₹2
   - When seller's daily cost > ₹2, backend returns HTTP 429 for subsequent AI calls
   - Seller sees: "You've reached your daily AI quota. Try again tomorrow."

2. **Global daily cap:** ₹500
   - Hard stop: when global cost > ₹500, ALL non-admin users get 429
   - Admin/coordinator can force-allow for urgent cases
   - Alert email sent immediately to founder + operations

3. **Error rate alarm:** >5% error rate in 1-hour window
   - Indicates possible Gemini outage or quota exhaustion
   - Alert to ops Slack channel; on-call engineer investigates

4. **Latency alarm:** P95 latency > 10 seconds
   - Possible regional Gemini service degradation
   - Alert to ops; no auto-mitigation (fallback is soft, not hard)

---

## 9.9 Observability Checklist

- [ ] LangFuse SDK initialized in `backend/app/config.py` (project key injected)
- [ ] All three workloads wrapped with `@observe` decorator
- [ ] Cost tracking per user stored in Valkey `cost:{user_id}:{date}` (updated per call)
- [ ] Daily cost roll-up cron job at 00:00 UTC → `/admin/costs` endpoint
- [ ] Golden test eval runner CI integration (runs before merge, passes/fails PR)
- [ ] Alert configuration in monitoring tool (Prometheus / CloudWatch / custom)
- [ ] Prompt versioning config in `backend/app/config.py` (switch via env var)

---

## 9.10 V1 Operational Readiness

Before launch, confirm:

1. **Rate limit ceiling testing:** load-test picker with 100 calls/min, autofill with 50 calls/min, ensure no 429 from Gemini (we stay within 2K RPM)
2. **Cost math signed off:** founder confirms ₹2/seller/day + ₹500/day global caps are acceptable burn
3. **Fallback UX tested:** picker fallback to manual browse, autofill fallback to manual fill, watermark fallback to skip — all three flows tested end-to-end
4. **Golden evals baselined:** all three golden sets run, baseline accuracy recorded (picker ≥80%, autofill 0% invalid, watermark ≥85%)
5. **LangFuse dashboard live:** cost + latency + error rate visible in real-time
6. **On-call runbook written:** if Gemini goes down or costs spike, what does the duty engineer do?

**Estimated readiness sprint:** 3–4 days (post-backend-foundation).

---

**Total AI operational cost for V1:** ~₹0.50–0.70/product created (picker + autofill + ~2 images watermark-checked). At ₹500/day cap ≈ 700–1,000 products/day can use AI fully. Sustainable for Phase 1 (100–200 active sellers expected at launch).


---

## Section 9 — Multi-tenancy and Data Isolation

## 10.1 Tenancy Model: Single-Seller-Per-Account (V1)

MeeSell V1 is **single-seller-per-account**. One user (phone + JWT) = one tenant = one Meesho seller. Each `user_id` in the `users` table is a complete, independent tenant.

**V1.5+:** Team accounts deferred. Future implementation will add a `teams` table, per-team rate limits, and replace `user_id` filtering with `team_id` filtering. For V1, zero team infrastructure exists.

---

## 10.2 Data Isolation: App-Level Filtering (No RLS for V1)

**V1 Decision: Application-level `user_id` scoping with PostgreSQL foreign keys. Row-Level Security (RLS) deferred to V1.5.**

### Why app-level for V1?

✓ **Simpler logic**: Every service method takes `user_id` as explicit parameter
✓ **Easier testing**: Swap `user_id` in test fixtures; no RLS policy debugging
✓ **Fewer footguns**: Intent is explicit in Python code, not hidden in DB policies

✗ **No DB-level guarantee**: Developers must remember to filter; RLS provides automatic protection

**V1.5 evaluation:** Consider RLS when team accounts ship and codebase stabilizes.

### Implementation: Foreign Keys + Mandatory Filtering

```sql
CREATE TABLE catalogs (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ...
);

CREATE TABLE products (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id),
  catalog_id      UUID NOT NULL REFERENCES catalogs(id),
  ...
);

CREATE INDEX idx_catalogs_user           ON catalogs(user_id);
CREATE INDEX idx_products_user           ON products(user_id);
CREATE INDEX idx_products_user_status    ON products(user_id, status);
```

**Rule:** Every query touching `catalogs`, `products`, `product_images`, `pricing_calcs`, `exports` **must** include `WHERE user_id = :user_id`. Linter enforces this in CI.

---

## 10.3 JWT Claims and Tenant Injection

JWT payload from `/api/v1/auth/otp/verify`:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1719000000,
  "plan": "free"
}
```

FastAPI middleware extracts `sub` → `user_id` and injects into every route handler:

```python
async def get_current_user(token: str = Depends(HTTPBearer())) -> CurrentUser:
    payload = jwt.decode(token.credentials, settings.JWT_SECRET, ["HS256"])
    return CurrentUser(user_id=UUID(payload["sub"]), plan=payload["plan"])

@router.get("/api/v1/products")
async def list_products(
    user: CurrentUser = Depends(get_current_user),
    service: ProductService = Depends(),
):
    return await service.list_products(user_id=user.user_id)
```

---

## 10.4 Service-Layer Enforcement

Every service method querying tenant data takes `user_id` as explicit parameter:

```python
class ProductService:
    async def get_product(self, user_id: UUID, product_id: UUID) -> Product:
        stmt = select(Product).where(
            (Product.id == product_id) & (Product.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404)
        return product
```

**CI Linter:** Reject any service method that queries owned tables without `user_id` in signature.

**Tests:** Every fixture creates unique `user_id`; isolation tests verify User A cannot read User B's products:

```python
@pytest.mark.asyncio
async def test_product_isolation():
    user_a_id = UUID("00000000-0000-0000-0000-000000000001")
    user_b_id = UUID("00000000-0000-0000-0000-000000000002")

    product = await service.create_product(user_a_id, ...)

    with pytest.raises(HTTPException):
        await service.get_product(user_b_id, product.id)
```

---

## 10.5 Cross-Tenant Risk Assessment

| Data | Risk | Mitigation |
|---|---|---|
| Products & Catalogs | LOW | `user_id` WHERE clause on every query |
| Seller Profile | LOW | `user_id` PRIMARY KEY (one per user) |
| GCS Images | LOW | Signed URLs scoped to single product (§10.8) |
| AI Suggestions | LOW | Stored in `products.ai_suggestions_jsonb`, scoped by `user_id` |
| Pricing & Exports | LOW | Both owned by `user_id` foreign key |

**Non-existent in V1 (no risk):**
- Shared analytics (V1.5)
- Cross-seller recommendations
- Admin panel (SQL read-only replica only in V1)

---

## 10.6 Admin Access: V1 = SQL, V1.5 = Admin Panel

**V1:** Read-only PostgreSQL replica on GCP VM. All admin SQL queries logged to `audit_events` table (§11).

**V1.5:** Separate `admin_users` table + JWT claim `is_admin: true`. Routes: `/api/v1/admin/sellers/:user_id/...`. Full audit trail.

---

## 10.7 Rate Limiting Per Tenant (Valkey)

All limits are per-user to prevent one seller starving others:

| Action | Limit | Window | Key |
|---|---|---|---|
| OTP send | 3 | 1 hour | `ratelimit:otp:send:{phone}:3600` |
| Autofill | 50 | 1 hour | `ratelimit:autofill:{user_id}:3600` |
| Smart picker | 100 | 1 hour | `ratelimit:picker:{user_id}:3600` |
| Create product | 20 | 1 hour | `ratelimit:create_product:{user_id}:3600` |

Sliding-window in Valkey: `INCR key; EXPIRE key 3600 if count==1`.

---

## 10.8 GCS Bucket Layout: Signed URLs Scoped per Product

```
gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg
```

Signed URLs are scoped to **one image**, not the entire product folder:

```python
def get_signed_url(user_id: UUID, product_id: UUID, image_idx: int) -> str:
    bucket = storage_client.bucket("meesell-images")
    blob = bucket.blob(f"{user_id}/{product_id}/{image_idx}.jpg")
    return blob.generate_signed_url(version="v4", expiration=timedelta(hours=1))
```

Leaked URL = access to one image only, not catalog-wide.

---

## 10.9 Plan-Based Limits (V1 = 100 products, V1.5 = Tiered)

V1: All sellers are "free" plan with soft cap of **100 active products**.

```python
async def check_product_limit(user_id: UUID, db: AsyncSession):
    active = await db.execute(
        select(func.count(Product.id)).where(
            (Product.user_id == user_id) & (Product.status != "deleted")
        )
    )
    if active.scalar() >= 100:
        raise HTTPException(status_code=429, detail="Product limit reached")
```

**V1.5 divergence:**
- "pro": 500 products, 200 autofill/hour
- "free": 100 products, 50 autofill/hour

---

## 10.10 Multi-Tenancy Test Checklist

1. ✓ Unique `user_id` per test (UUID per fixture)
2. ✓ Seed seller_profile + user
3. ✓ Create tenant-scoped entities (products, catalogs)
4. ✓ Assert isolation: User A data invisible to User B
5. ✓ Verify: same `product_id` returns 404 for different user

**Indexes for efficiency:**

```sql
CREATE INDEX idx_catalogs_user            ON catalogs(user_id);
CREATE INDEX idx_products_user            ON products(user_id);
CREATE INDEX idx_products_user_status     ON products(user_id, status);
CREATE INDEX idx_catalogs_user_created    ON catalogs(user_id, created_at DESC);
```


---

## Section 10 — Audit Log and Autosave Events

**Feeds into:** `MVP_ARCHITECTURE.md` (pending founder review before merge)

---

## 11.1 What Gets Logged

Every write that changes persistent state is an audit candidate. The rule is: **if a seller would care later that it happened, log it.**

| Event Type | Trigger | Logged |
|---|---|---|
| `product.patch` | `PATCH /api/v1/products/{id}` (includes autosave) | Yes |
| `product.export` | `POST /api/v1/exports` | Yes |
| `seller_profile.update` | `PATCH /api/v1/seller-profile` | Yes |
| `auth.login` | Successful OTP verify | Yes |
| `GET *` | Any read | **No** — too noisy, zero recovery value |
| AI suggestions (pre-accept) | Gemini response before seller accepts | **No** — PII surface, no durable value |
| OTP value | Any OTP send/verify | **No** — never stored, never logged |
| Password / JWT secret | N/A — we use OTP auth | **No** |

---

## 11.2 Schema

Append-only. No `UPDATE`, no `DELETE` path exists in the application layer. Archive-then-purge handles lifecycle (§11.5).

```sql
CREATE TABLE audit_events (
  id               BIGSERIAL PRIMARY KEY,
  user_id          UUID NOT NULL REFERENCES users(id),
  event_type       VARCHAR(40) NOT NULL,   -- "product.patch" | "product.export"
                                           -- | "seller_profile.update" | "auth.login"
  entity_type      VARCHAR(20),            -- "product" | "seller_profile" | "user"
  entity_id        UUID,                   -- null for auth.login
  diff_jsonb       JSONB,                  -- {"before": {...}, "after": {...}}
                                           -- null for events with no delta (e.g. auth.login)
  metadata_jsonb   JSONB,                  -- ip, user_agent, request_id, session_id
  occurred_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Primary query patterns (§11.8)
CREATE INDEX idx_audit_user_time   ON audit_events(user_id, occurred_at DESC);
CREATE INDEX idx_audit_entity      ON audit_events(entity_type, entity_id);
```

`diff_jsonb` stores only fields that changed. For `product.patch`, the before/after values use **canonical field names** (never Meesho column headers — respects CORE_PHILOSOPHY F8). Sensitive fields are scrubbed before insertion (§11.9).

---

## 11.3 Write Path

The application never writes to `audit_events` synchronously inside a request transaction. This avoids write amplification from the 10-second autosave cadence and prevents audit I/O from slowing the primary write path.

```
PATCH /api/v1/products/{id}
  │
  ├── 1. SQLAlchemy transaction → writes to products table → COMMIT
  │
  ├── 2. FastAPI middleware detects successful write (no exception raised)
  │       serialises {user_id, event_type, diff, metadata} → JSON
  │       pushes to Valkey DB 1 key: "audit:queue" (RPUSH, fire-and-forget)
  │
  └── 3. Celery worker (audit_flush_task, runs every 30 s)
          pops batch of ≤500 events from Valkey queue
          inserts via bulk INSERT INTO audit_events ... (single round-trip)
          acknowledges batch
```

**Critical constraint:** If the primary transaction is rolled back (validation error, constraint violation), the middleware does NOT push to the Valkey queue. Failures are never logged. The middleware checks response status >= 400 before enqueuing.

---

## 11.4 Autosave Coalescing

Raw autosave cadence: one `PATCH` every 10 seconds. For a seller filling a form for 30 minutes, that is 180 raw events for a single product. Stored naively, 1,000 sellers each working 30 min/day produces 5.4 million raw rows/day — clearly wrong.

**Coalescing window: 5 minutes, per (user_id, product_id).**

The Celery flush task applies this rule before inserting:

1. Pull all pending `product.patch` events from the queue.
2. Group by `(user_id, entity_id)`.
3. For each group, find events whose `occurred_at` falls within the same 5-minute bucket (floor to 5 min).
4. Collapse the group: `diff_jsonb.before` = before-value from the **earliest** event in the window; `diff_jsonb.after` = after-value from the **latest** event in the window. `occurred_at` = latest event timestamp. Intermediate states are discarded.
5. Insert one row per (user, product, 5-min window).

**Result:** A seller autosaving a product for 60 minutes generates at most 12 coalesced audit rows (60 min / 5-min window), not 360. The first and last value within each window are preserved for exact delta reconstruction.

Non-autosave events (`product.export`, `seller_profile.update`, `auth.login`) are **never coalesced** — each occurrence is a distinct audit fact.

---

## 11.5 Retention Policy

| Phase | Duration | Storage | Action |
|---|---|---|---|
| Hot | 0–90 days | PostgreSQL `audit_events` | Live, indexed, queryable |
| Warm archive | 91 days – 1 year | GCS `gs://meesell-audit-archive/YYYY/MM/` | Gzipped JSONL, one file per day |
| Expiry | > 1 year | — | Delete from GCS (unless legal hold flag is set) |

Archive job: Celery beat task runs nightly. Selects rows where `occurred_at < NOW() - INTERVAL '90 days'`, streams to GCS as gzipped JSONL, then hard-deletes from Postgres. Archive is immutable once written — no GCS object versioning overwrites. Legal hold is implemented by a Valkey key `audit:legal_hold:{user_id}` that the archive job checks before deleting.

---

## 11.6 Autosave Recovery: `product_drafts` Table

`audit_events` is the **immutable history**. It is NOT the recovery mechanism — it is too coalesced and too append-only for fast crash recovery. A separate table serves that purpose.

```sql
CREATE TABLE product_drafts (
  user_id     UUID NOT NULL REFERENCES users(id),
  product_id  UUID NOT NULL REFERENCES products(id),
  draft_jsonb JSONB NOT NULL,         -- full current field state, not a diff
  saved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, product_id)
);
```

**Lifecycle:**
- On every successful `PATCH /api/v1/products/{id}`, the service layer upserts `product_drafts` with the full current field state (one row per product, ON CONFLICT DO UPDATE).
- On successful `POST /api/v1/exports`, the corresponding `product_drafts` row is deleted.
- On browser reload / crash recovery, the frontend calls `GET /api/v1/products/{id}/draft` which returns the `draft_jsonb` and re-hydrates the wizard.

`product_drafts` is mutable, low-latency, and ephemeral. `audit_events` is append-only, durable, and coalesced. They serve orthogonal purposes and must not be conflated.

---

## 11.7 Abuse Detection Signals

The same Celery flush task that coalesces audit events also feeds a rules engine. Rules are evaluated against **rolling counts in Valkey** (not against Postgres — latency must be sub-second).

| Signal | Rule | Response |
|---|---|---|
| Bot / automated fill | > 100 `product.patch` events/minute for a single user_id | Set Valkey key `abuse:bot:{user_id}` TTL 1 hour; API returns 429 |
| OTP brute force | > 10 failed OTP attempts/hour for a single phone | Set `abuse:otp:{phone}` TTL 1 hour; block further OTP sends |
| Scraper / mass create | > 1,000 `products` created in any rolling 24-hour window | Set `abuse:scraper:{user_id}` TTL 24 hours; alert ops Slack webhook |
| Unusual IP switch | Same session, IP changes mid-session | Log to `metadata_jsonb`, flag for manual review (no auto-block V1) |

All blocks are implemented as Valkey key checks in the `rate_limit.py` middleware — already on the request path for OTP rate limiting. No new middleware layer needed.

---

## 11.8 Query Patterns

Two primary access patterns, both served by the indexes defined in §11.2:

**Pattern A — Product history ("what changed on this product yesterday?"):**
```sql
SELECT * FROM audit_events
WHERE entity_type = 'product'
  AND entity_id   = :product_id
  AND occurred_at BETWEEN :start AND :end
ORDER BY occurred_at DESC;
-- Uses: idx_audit_entity
```

**Pattern B — User activity ("show all activity for user X"):**
```sql
SELECT * FROM audit_events
WHERE user_id    = :user_id
  AND occurred_at > NOW() - INTERVAL '7 days'
ORDER BY occurred_at DESC
LIMIT 100;
-- Uses: idx_audit_user_time (covering index)
```

Both are exposed as admin-only endpoints (`/api/v1/admin/audit`) behind an `is_admin` JWT claim check. Sellers do not have direct access to the raw audit table in V1; they see a simplified activity summary on the dashboard.

---

## 11.9 PII Safety in `diff_jsonb`

Before any event is pushed to the Valkey queue, a scrubber function strips or hashes fields that are sensitive:

| Field | Treatment |
|---|---|
| `phone` | Replace with SHA-256(phone + PII_SALT) — preserves abuse correlation without exposing the number |
| `fssai_license_number` | Redact to `[REDACTED-FSSAI]` |
| `gst_number` | Redact to `[REDACTED-GST]` |
| `otp` | Never reaches diff — OTP values are never written to products/seller_profile |
| All other fields | Stored as-is — product field values (title, description, price) have no PII concern |

`PII_SALT` is a per-deployment secret in `backend/.env` (`AUDIT_PII_SALT`). It is rotated annually. The hash is one-way: sufficient to detect "same phone across two accounts" in abuse analysis, but not reversible by a DB read.

---

## 11.10 Volume Estimate

| Variable | Value |
|---|---|
| Active sellers (V1 target) | 1,000 |
| Raw `product.patch` events per seller per day | ~10 (2 products, 5 autosave sessions each) |
| After 5-min coalescing | ~3 events/seller/day |
| Total coalesced events/day | 3,000 |
| Total events/year | ~1.1 million |
| Row size estimate | ~800 bytes avg (UUID + JSONB diff) |
| Annual storage (Postgres) | ~880 MB — trivially within single-node budget |

At 1M rows with the two indexes defined above, both query patterns (§11.8) return in < 5 ms on the existing `meesell-dev` VM. No partitioning required until seller count exceeds 50,000.

---

## Dependencies and Constraints

- `audit_events` MUST be append-only. Application code contains no `UPDATE` or `DELETE` on this table. Archive-and-purge is the only deletion path, and it runs outside the application (Celery beat, admin-only).
- `product_drafts` is separate from `audit_events`. Do not merge them.
- PII scrubbing (§11.9) is mandatory on every event before queue push. It is not optional at any traffic level.
- Coalescing (§11.4) is a write-time operation in the Celery flush task, not a read-time view. The raw intermediate states are intentionally discarded — they are not needed for recovery (§11.6 handles that) and bloat the table.
- The `audit:queue` Valkey key uses DB 1 (Celery broker DB, per `CLAUDE.md`). A dedicated DB 3 may be added if queue depth monitoring shows contention with Celery task dispatch — deferred to V1.5.


---

## Section 11 — Hand-off Contracts

### 11.1 DATA → BACKEND (`meesell-backend-coordinator`)

**Inputs delivered (ready now):**
- `data/parsed/batch_{01..12}_*.json` — per-leaf parsed schema
- `data/parsed/FULL_CORPUS_ANALYSIS.md` — synthesis
- This document (DDL in §2)
- Pending: `data/parsed/canonical_field_aliases.json` (will produce alongside this doc)

**Backend's job:**
1. Implement the 8 SQLAlchemy models per §2
2. Author Alembic migration sequence per §2.6
3. Author seed scripts to populate `templates`, `categories`, `field_enum_values`, `field_aliases` from parsed JSONs
4. Implement 20 API endpoints per §3
5. Tests: per-route + per-service. Multi-tenant isolation tests.

**Acceptance:**
- All 16 V1 endpoints from V1_FEATURE_SPEC §5 + 4 new (seller-profile suite)
- Seed scripts produce 3,557 templates + 3,772 categories + ~200K field_enum_value rows
- Golden migration: full DB rollback + replay
- Per-route tests cover 100% of endpoints; service-level tests cover business logic

### 11.2 DATA → FRONTEND (`meesell-frontend-coordinator`)

**Inputs delivered:**
- This document (§4)
- Locked decisions (#5 data-driven wizard, #6 primitive library)

**Frontend's job:**
1. Build 11 primitive components per §4.1 (10 + address_group)
2. Build `<mee-wizard>` renderer per §4.2
3. Build onboarding wizard per §4.3 (calls `/seller-profile/required-fields`)
4. Build category browser (manual fallback for Smart Picker)
5. Build dashboard, preview, pricing, image-upload, export pages (per V1_FEATURE_SPEC §6)
6. Tests: each primitive has visual + interaction spec; wizard has E2E test

**Acceptance:**
- 11 primitives + composition pass storybook (or equivalent visual diff)
- Onboarding journey completes (10 base fields + 1-4 extension steps)
- Catalog wizard renders 47-field Lehenga form without lag on Pixel 6a
- Touch targets ≥44px throughout (Tirupur mobile-first)

### 11.3 DATA → AI (`meesell-ai-coordinator`)

**Inputs delivered:**
- This document (§5)
- Locked decisions (#4 enum-constrained, #8 top-5)
- `data/parsed/batch_*_summary.md` — patterns to be aware of
- `backend/app/data/meesho_category_tree.json` — for compression

**AI's job:**
1. Author 3 prompt families per §5.4
2. Build per-category schema compression utility (template → ≤3,000 tokens)
3. Build category tree compression utility (3,772 leaves → ≤8,000 tokens)
4. Build evaluation harness with 3 golden sets
5. Build cost tracker (per-call tokens × ₹/1K tokens)

**Acceptance:**
- Smart Picker recall ≥80% in top-5 (50-description golden)
- Auto-fill: 0% invalid enum values (enforced by guardrail)
- Auto-fill: ≥70% useful (founder qualitative review of 30 outputs)
- Watermark check ≥85% accuracy on 30 golden images
- Per-call cost ≤ ₹0.05 average

### 11.4 BACKEND on Caching (§6)
- Implement Valkey DB 3 cache layer per §6.1 (DBs 0-2 reserved for OTP/Celery)
- Version-tagged cache keys with auto-invalidation on quarterly Meesho refresh
- Strip `meesho_column_header`, `meesho_column_index`, `enum_codes_map` from cached payloads (philosophy M10/F8 — Meesho format never leaks past Export Adapter)
- HTTP `Cache-Control` + `ETag` on schema and enum API responses
- Single-flight `SET NX` on the 291 large Brand-pattern enum keys (stampede protection)
- Pre-warm top 100 categories into FastAPI worker LRU on startup
- **Acceptance**: P95 schema fetch ≤ 50 ms (cache hit), ≤ 200 ms (cache miss with DB lookup)

### 11.5 BACKEND on Search & Indexing (§7)
- Enable `pg_trgm` extension; create 3 GIN indexes per §7.2 (`path`, `leaf_name`, `super_name`)
- All indexes built `CONCURRENTLY` so quarterly refresh stays online
- Implement `GET /api/v1/categories/browse?q=&super_id=&limit=&offset=` with breadcrumb path in response
- Wire Smart Picker fallback: when confidence < 70% or timeout, frontend pivots to `/browse` with original query pre-filled
- **Acceptance**: P95 browse search ≤ 200 ms on 3,772 rows

### 11.6 AI on Operations (§8)
- Per-call cost tracking persisted per request (tokens × ₹/1K)
- Three-layer hallucination guardrail: prompt-level instruction + parser-level enum check + Export Adapter re-validation (M7 + F3)
- Per-seller rate limits: 50 autofill/hour, 100 picker/hour (coordinated with §9.7)
- Daily global cap ₹500 — alarm at 80%, hard-stop at 100% with graceful fallback ("AI is busy, fill manually")
- LangFuse traces on every Gemini call (input, output, tokens, latency, cost, eval result if golden)
- Eval golden sets: 50 descriptions for picker (≥80% top-5 recall), 30 product specs for autofill (0% invalid enum), 30 images for watermark (≥85% accuracy)
- **Acceptance**: zero invalid enum values reach Export Adapter; per-call cost ≤ ₹0.05 average; daily total ≤ ₹500

### 11.7 BACKEND on Multi-tenancy (§9)
- App-level `user_id` foreign key on every owned table (catalogs, products, product_images, pricing_calcs, exports, seller_profile)
- JWT claim shape: `{sub: user_id, exp, plan: "free" | "pro"}`. Middleware injects `user_id` into every route handler.
- CI linter rejects any service method that touches owned tables without `user_id` in signature
- 4 per-user rate limits in Valkey: OTP 3/h, Auto-fill 50/h, Smart Picker 100/h, Create-product 20/h
- GCS bucket layout: `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` — signed URLs scoped per image, TTL 1h
- Soft cap: 100 active products per "free" seller in V1
- **Acceptance**: per-PR isolation regression test asserts User A cannot read User B's products

### 11.8 BACKEND on Audit Log & Autosave (§10)
- Create `audit_events` (append-only, BIGSERIAL PK) and `product_drafts` (latest unsaved state per user×product) tables per §10.2
- Middleware logs events AFTER successful write; failed/rolled-back transactions do NOT log
- Celery flush coalesces `product.patch` events in 5-minute windows per `(user_id, product_id)` — 30× volume reduction
- Retention: 90 days hot in Postgres → nightly Celery beat archives older rows to GCS as gzipped JSONL → delete after 1 year (unless `audit:legal_hold` Valkey key blocks)
- Abuse detection rules on Valkey counters: >100 patches/min = bot, >10 failed OTPs/h = brute-force, >1000 creates/24h = scraper. TTL-bound block keys read by existing `rate_limit.py`.
- PII scrubbing on `diff_jsonb` — strip phone, FSSAI numbers, GST numbers before storage
- **Acceptance**: yearly volume stays ≤ 2M rows for 1,000 active sellers

---

## Section 12 — Founder-Locked Decisions (2026-06-04)

All six prior open questions are now resolved. Implementation rules below are normative.

### 12.1 Books ISBN → **Follow Meesho (optional)**
- Books category renders `isbn` as a regular optional field. No special "required" treatment.
- The `mee-text-short` primitive labels it just like any other optional field.
- `compliance_extensions` for Books super_id (80) keeps `isbn_publisher_id` as `required: false`.

### 12.2 Meesho source typos → **Auto-correct internally, restore on XLSX export**
- `canonical_field_aliases.json` maps `No. of Primiary Cameras` → canonical `no_of_primary_cameras` (corrected).
- UI displays the corrected canonical name everywhere ("Primary", "Secondary").
- The XLSX exporter has a reverse map (`canonical → category-specific raw variant`) and emits the typo verbatim when generating Meesho-format files. **Round-trip test required** on Mobiles & Tablets categories.
- Implementation: extend `field_aliases` table with a `for_xlsx_export` boolean — TRUE for entries that should be reversed on export.

### 12.3 Long-tail super-categories → **Include all 3,772 in V1**
- No filter on Smart Picker by leaf-count.
- Seed scripts populate all 3,772 leaves and 3,557 templates regardless of size.
- Reuses the existing 11 primitives — no extra component work.

### 12.4 Group ID → **Show behind "Advanced fields" toggle** (revised per philosophy lock)
- `is_advanced = true` on the field metadata in `templates.schema_jsonb`.
- Wizard renders an "Advanced fields" expandable section at the bottom of relevant steps; Group ID lives there.
- Seller's choice to expand acknowledges the field's opacity — relaxes philosophy F5 ("never show a field without explanation").
- Export Adapter writes whatever the seller filled, blank if they didn't expand. Meesho accepts blank for optional.
- Documented as "advanced field, V1.5 investigation" in `canonical_field_aliases.json`.
- Sits between Pattern 2 (fully hidden) and a regular visible field — see `docs/CORE_PHILOSOPHY.md` Pattern 5.

### 12.5 Warranty → **Per-product wizard step (match Meesho)**
- Wizard adds a conditional "Warranty" step for categories that have warranty fields (Electronics + Appliances + some Cookware, ~190 leaves).
- Warranty is NOT an onboarding extension. Seller fills warranty per product.
- Warranty fields (`warranty_period`, `warranty_type`, etc.) follow the regular schema flow.
- `compliance_extensions` map (§2.2) does NOT include warranty.

### 12.6 Eye-Serum collapsed compliance → **Collect 9 standard fields universally, transform at export** (revised per philosophy lock)
- `seller_profile` stores ONLY the 9 standard compliance fields (manufacturer_name/address/pincode × 3 — manufacturer, packer, importer). The 3 combined "Details" columns are dropped from the seller_profile schema.
- Onboarding wizard always collects the 9 standard fields (cleaner UX — typing into clearly-labeled inputs beats one mushy "Details" textarea).
- Export Adapter (§5.5) concatenates 9 → 3 combined strings ONLY when exporting an XLSX for the Eye-Serum template (template's `compliance_shape = "collapsed"`).
- For every other category (3,771 of 3,772), the Export Adapter sends the 9 standard columns verbatim.
- **Rationale (philosophy F4):** never store data we don't need. The 3 combined fields are derived data — re-built from the 9 standard fields at export time.
- Implementation: `templates.schema_jsonb` keeps the `compliance_shape: "standard" | "collapsed"` flag. The CollapsedComplianceStrategy class (§5.5.5) handles the transformation. Frontend renders only the 9-field form.
- **Faithfulness to Meesho:** the philosophy preserves the founder's intent ("keep it like how meesho handle it") at the EXPORT boundary, not in the internal model. Meesho still gets exactly what its template expects.

---

## Section 13 — Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| AI hallucination on autofill produces invalid data | Bad listings, seller frustration | Two-layer enum guardrail (prompt + validator). Reject invalid suggestions. |
| Brand picker P95 latency >2s for 4,000-value categories | Form feels slow | Server-side pagination (50/page). Client-side cache by `(category, query_prefix)`. |
| Eye-Serum-style template not covered → form breaks | One category unusable | Backend accepts both representations. Frontend `<mee-address-group>` for collapsed format. |
| Meesho changes XLSX schema (new field marker tier) | Parser may break | Parser handles `recommended` regex already. Quarterly refresh + diff report (scraper-maintainer agent owns). |
| 1,831 unique field names → form-renderer bugs in edge cases | Some leaves render badly | Per-template visual test for top 100 leaves by traffic. Bug-fix per leaf as discovered. |
| Compulsory median 33 in Home & Kitchen overwhelms user | Drop-off mid-wizard | Multi-step wizard with progress bar. AI auto-fill reduces manual input. |
| FSSAI field is compulsory for Grocery → seller blocked at signup | Lost sign-ups in Grocery segment | Onboarding wizard makes the requirement obvious before signup. "Don't have FSSAI yet? Apply here" link to Indian govt portal. |
| Canonical-name normalisation breaks Meesho XLSX export | XLSX rejected by Meesho upload | XLSX exporter reverses canonical → original variant. Round-trip golden test per super-category. |
| RLS deferred to V1.5 (V1 uses app-level `user_id` scoping only) | Tenant isolation depends on CI linter discipline; a hotfix bypassing the lint could leak across sellers | Per-PR isolation regression test (§9.4) asserts User A cannot read User B's products; service-signature linter rejects PRs lacking `user_id` parameter. Defense-in-depth review noted in §9.2. |
| Valkey single point of failure (cache + rate limits + Celery broker + audit queue all rely on it) | Outage simultaneously degrades hot-path schema loads, AI rate limiting, background jobs, and autosave coalescing | Monitor Valkey SLA; backend falls back to direct PostgreSQL on cache miss; rate limiting fails open (allow) with alarm; V1.5 evaluate Valkey HA / Sentinel deployment |
| AI cost overrun — daily ₹500 cap hit during traffic spike | Service degrades or stops mid-day; sellers see "AI busy" until next day | Per-seller per-hour rate limits already in place (§8.4); cost alarm at 80% of daily cap; graceful fallback to "fill manually" UX when cap reached; review pricing weekly during launch month |

---

## Section 14 — Phased Rollout

### V1 (this 7-day sprint) — corpus-grounded
- All 9 P0 features from V1_FEATURE_SPEC
- 10 input primitives + wizard renderer
- Onboarding with base + 6 conditional extensions
- Schema-by-template seeded for all 3,557 templates
- AI auto-fill enum-guardrailed

### V1.5 (post-launch, 30-60 days)
- Brand validator (`brand_master.json` from corpus)
- Brand "request to add" workflow (Pattern 3 dedicated UX — V1 uses free-text `Brand Name` field as the escape hatch)
- Inline guided "add super-category later" flow (V1 uses simple `/profile` CRUD with reactive form sections; V1.5 adds modal at pick-time for a smoother expansion experience)
- Bulk multi-SKU upload (one description → N products)
- Razorpay billing + tiered plans (free/pro divergence in product caps and AI rate limits — see §9.9)
- Analytics dashboard
- **Row-Level Security migration** — replace app-level `user_id` scoping with PostgreSQL RLS once codebase stabilises and team accounts approach (§9.2)
- **Admin panel** — replace V1's read-only SQL replica access with a thin admin UI scoped to `admin_users` table + JWT claim `is_admin: true` (§9.6)
- **Team accounts** — multi-user per business: add `teams` table, per-team rate limits, replace `user_id` filtering with `team_id` (§9.1)
- **A/B testing for AI prompts** — `prompts/{name}_v1.py` vs `_v2.py`, active version per Valkey config flag (§8.5 prompt versioning ready)
- **Valkey HA evaluation** — Sentinel or Cluster deployment if launch traffic exposes the SPOF risk in §13
- **Friendly dropdown labels** for codified enums (e.g. "PE-HD" → "High-density Polyethylene") — backfill Tier C/D fields per §5.6.6

### V2 (later)
- Variant matrix (5 sizes × 4 colors as a single matrix UI)
- Father-Son parent-child SKU support (the `*-Dad` fields revealed in Batch 2)
- Multi-marketplace (Amazon, Flipkart, Etsy)
- Native mobile via Ionic/Capacitor (per CLAUDE.md Phase 2)

---

## Section 15 — Sign-off

**Founder decisions reflected:** 14 of 14 — 8 from initial batch review + 6 from architecture review. Decisions #12 (Group ID) and #14 (Eye-Serum compliance) revised after the philosophy lock — see `docs/CORE_PHILOSOPHY.md` for the rulebook those revisions enforce.

**Corpus-grounded:** every architectural choice traceable to a line in `FULL_CORPUS_ANALYSIS.md` (3,772/3,772 leaves parsed, 0 failures).

**Philosophy-locked:** 10 mandates + 8 forbids + 5 structural patterns in `docs/CORE_PHILOSOPHY.md`. Every section in this document checked against the rulebook.

**Pending laptop session:**
- SSoT co-authorship (`docs/MEESHO_CATEGORY_INTELLIGENCE.md`) — the locked rule is "founder + coordinator write it together"
- Final sign-off on this document

**On approval, this document unblocks:**
- `meesell-backend-coordinator` (and its 4 specialists) — gets §2 data model, §3 API surface, §5.5 Export Adapter, §6 caching, §7 search, §9 multi-tenancy, §10 audit log
- `meesell-frontend-coordinator` (and its 3 specialists) — gets §4 frontend architecture, §5.6 presentation layer, §5.7 round-trip test plan, §12.4 advanced-fields toggle pattern
- `meesell-ai-coordinator` (and its 3 specialists) — gets §5 AI pipeline, §8 operational details, §5.6.7 validation message library, enum-constrained guardrail (M7 + F3)

The DATA / SCRAPER foundation work is complete. Phase 3 deliverable is this document plus `CORE_PHILOSOPHY.md`, `canonical_field_aliases.json`, `field_display_overrides.json`. Phases 4 (V1 feature validation) and 5 (Micro-PoC) are blocked on founder approval per original session brief.
