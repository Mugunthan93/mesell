# MeeSell — V1 Feature Spec

Last updated: 2026-06-04
Status: V1 Locked — ready to build

Reference: `docs/VALIDATED_PAIN_POINTS.md` (themes T1–T6, new pains S3.x)

---

## Section 1: V1 Scope Summary

### In V1 (P0 — ship this week)
1. **Auth** — Phone OTP (MSG91) + JWT
2. **Smart Category Picker** — Product description → top-3 Meesho categories from 3,772-leaf tree
3. **Fast Catalog Form** — Category-specific form (≤50 fields, inline help from XLSX)
4. **AI Auto-fill** — Gemini suggests values for compulsory fields from description
5. **Image Pre-check** — JPEG, RGB (not CMYK), watermark detection, white-BG check
6. **Live Product Preview** — Meesho marketplace render before publish
7. **Price Calculator** — MRP / Meesho Price / Seller Price with category commission
8. **Tracking Dashboard** — User's products with status (draft / exported / live)
9. **XLSX Export** — Meesho-format XLSX for supplier-panel upload

### V1.5 (post-launch, 30–60 days)
- Bulk operations (multi-SKU upload)
- Analytics (CTR / conversion per product)
- Brand validator (vs 3,730 approved brands)
- Razorpay billing (Pro tier upgrade)
- Catalog versioning (revert to previous draft)

### Out of scope (V1 + V1.5)
- Multi-marketplace (Meesho only)
- Native mobile app (web responsive only)
- Team accounts / multi-user
- Service marketplace
- Real-time chat support

---

## Section 2: P0 Feature Specs

### Feature 1: Auth (Phone OTP + JWT)
**Pain solved:** Indian-seller onboarding friction; no password reset surface.

**User journey:**
1. User enters phone number on `/login`
2. System sends 6-digit OTP via MSG91, stores in Valkey (TTL 5 min)
3. User enters OTP → server validates → returns JWT (7-day expiry)
4. Frontend stores JWT in localStorage, attaches as `Authorization: Bearer` on every call

**Technical components:**
- Frontend: `LoginComponent`, `OtpVerifyComponent`, `AuthService`, `AuthInterceptor`
- Backend: `POST /api/v1/auth/otp/send`, `POST /api/v1/auth/otp/verify`
- Database: `users` table
- External: MSG91 SMS API, PyJWT, Valkey (DB 0 for OTP storage)

**Data model (users):**
| column | type | notes |
|---|---|---|
| id | UUID PK | gen_random_uuid() |
| phone | VARCHAR(15) UNIQUE | E.164 |
| email | VARCHAR(255) NULL | optional |
| plan | VARCHAR(20) | `free` / `pro` (V1 = `free`) |
| created_at | TIMESTAMPTZ | default now() |
| last_login_at | TIMESTAMPTZ | nullable |

**Acceptance criteria:**
- [ ] User receives OTP within 10 s of submit
- [ ] Wrong OTP rejected with `401`, correct OTP returns JWT
- [ ] OTP expires after 5 min; resend allowed after 30 s
- [ ] JWT valid for 7 days, refreshed silently on call within 24 h of expiry
- [ ] Rate limit: 3 OTP requests per phone per hour (Valkey sliding window)

**Edge cases:**
- Same phone signs up twice → reuse existing user record
- MSG91 fails → return `503` with retry hint, log incident
- JWT expired mid-session → 401 → frontend redirects to `/login`

**Effort estimate:** Backend 6 h · Frontend 4 h · **Total 10 h**

---

### Feature 2: Smart Category Picker
**Pain solved:** Theme 1 (CATEGORY SELECTION) — wrong category buries product; 3,772 leaves are too many dropdowns.

**User journey:**
1. User types product description (e.g., "blue cotton kurti with mirror work") on `/catalogs/new`
2. Frontend POSTs description to `/api/v1/categories/suggest`
3. Backend calls Gemini with description + compressed category tree → returns top-3 leaf categories with confidence
4. UI shows 3 cards (category path + confidence + sample attributes)
5. User picks one → catalog row created with `category_id` → routes to `/catalogs/:id/edit`

**Technical components:**
- Frontend: `SmartPickerComponent`, `CategoryCardComponent`
- Backend: `GET /api/v1/categories/suggest?q=<description>`
- Database: `categories` table (preseeded from scraped 3,772 leaves)
- External: Gemini 2.5 Flash

**Data model (categories):**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| meesho_id | VARCHAR(64) | scraped Meesho identifier |
| name | VARCHAR(255) | leaf name |
| parent_id | UUID FK NULL | self-reference |
| path | TEXT | "Fashion > Women > Ethnic > Kurti" |
| commission_pct | NUMERIC(5,2) | from scraped data |
| attributes_jsonb | JSONB | field schema (compulsory/optional) |
| created_at | TIMESTAMPTZ | |

**Acceptance criteria:**
- [ ] Suggestion returns within 3 s P95
- [ ] Top-3 includes correct category in ≥80 % of seed-test descriptions (50 hand-labeled)
- [ ] Each suggestion shows full path + commission %
- [ ] User can fall back to manual tree search if none match
- [ ] Picker handles English-only descriptions (Hindi defer to V1.5)

**Edge cases:**
- Empty / <5-char description → 422 with "describe in ≥10 chars"
- Gemini timeout → fallback to keyword search over `categories.name`
- Multilingual input (Hindi/Tamil in text) → pass through Gemini as-is

**Effort estimate:** Backend 8 h · Frontend 5 h · **Total 13 h**

---

### Feature 3: Fast Catalog Form
**Pain solved:** Theme 3 (FORM CLARITY) — abstract field copy, no inline examples.

**User journey:**
1. User landed on `/catalogs/:id/edit` after picking category
2. Backend returns category-specific field schema (`categories.attributes_jsonb`) — fields split by Compulsory / Recommended / Optional
3. UI renders one section per group with inline help text (from XLSX)
4. User fills fields; autosave triggers every 10 s and on blur to `PATCH /api/v1/products/:id`

**Technical components:**
- Frontend: `CatalogFormComponent`, `FieldRendererComponent`, `AutosaveDirective`
- Backend: `GET /api/v1/categories/:id/schema`, `PATCH /api/v1/products/:id`
- Database: `products.fields_jsonb`
- External: none

**Acceptance criteria:**
- [ ] Form renders ≤50 fields without lag (<500 ms first paint after schema fetch)
- [ ] Every field shows the XLSX help text on hover/tap
- [ ] Compulsory fields marked with red asterisk; form cannot proceed if any blank
- [ ] Autosave writes to `products.fields_jsonb` and shows "Saved" indicator
- [ ] Browser reload resumes from last saved state

**Edge cases:**
- Field with `enum` constraint → render as dropdown, not free text
- User changes category mid-edit → warn "fields will reset" + confirm
- Network drop during autosave → queue locally, retry on reconnect

**Effort estimate:** Backend 5 h · Frontend 9 h · **Total 14 h**

---

### Feature 4: AI Auto-fill
**Pain solved:** Theme 2 (TIME) + Theme 3 (CLARITY) — Meesho's own data shows ~16 min/catalog baseline.

**User journey:**
1. After picking category and typing description, user clicks "AI fill"
2. Backend sends description + category schema to Gemini → returns suggested values for compulsory fields only
3. UI populates fields in yellow highlight; user can accept or edit each
4. User clicks "Accept all" or edits inline; values persist on next autosave

**Technical components:**
- Frontend: `AutofillButtonComponent`, `FieldDiffComponent`
- Backend: `POST /api/v1/products/:id/autofill`
- Database: writes to `products.fields_jsonb` + `products.ai_suggestions_jsonb`
- External: Gemini 2.5 Flash (JSON-mode call)

**Acceptance criteria:**
- [ ] Suggestion returns within 5 s P95
- [ ] Only compulsory fields populated (Recommended / Optional left blank)
- [ ] All suggested values pass field-schema validation (enum / length / regex)
- [ ] User edits override AI value and clear yellow highlight
- [ ] Autofill is idempotent — re-running replaces previous AI suggestions

**Edge cases:**
- Gemini returns invalid JSON → retry once, then surface error toast
- Suggested enum value not in allowed list → drop that field with a logged warning
- Field has no clear inference from description → leave blank, do not hallucinate

**Effort estimate:** Backend 7 h · Frontend 4 h · **Total 11 h**

---

### Feature 5: Image Pre-check
**Pain solved:** Section 3.1 (NEW pain — image policy rejection) + Theme 4 sub-pain. EcomSarthi's free checker proves user pull.

**User journey:**
1. User on `/catalogs/:id/images` drags up to 6 images (max 10 MB each)
2. Frontend uploads to `POST /api/v1/products/:id/images` (multipart)
3. Backend stores in GCS, queues Celery job to run checks
4. Worker runs: JPEG check, RGB/CMYK check (Pillow), resolution ≥1500×1500, white-BG heuristic, watermark detection (Gemini vision)
5. UI polls `GET /api/v1/products/:id/images` until status updates; shows pass/fail per check with fix hints

**Technical components:**
- Frontend: `ImageUploaderComponent`, `PrecheckReportComponent`
- Backend: `POST /api/v1/products/:id/images`, `GET /api/v1/products/:id/images`
- Database: `product_images` table
- External: GCS, Gemini 2.5 Flash vision (watermark check), Pillow

**Data model (product_images):**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK | |
| gcs_path | TEXT | |
| order_idx | INT | 0-based position |
| width | INT | px |
| height | INT | px |
| color_space | VARCHAR(8) | `RGB` / `CMYK` / `OTHER` |
| precheck_jsonb | JSONB | `{jpeg:true, rgb:true, min_res:true, white_bg:false, no_watermark:true}` |
| status | VARCHAR(16) | `pending` / `pass` / `fail` |
| created_at | TIMESTAMPTZ | |

**Acceptance criteria:**
- [ ] All 5 checks complete within 8 s per image (worker)
- [ ] User sees per-check pass/fail with one-line fix hint ("Convert image to RGB before upload")
- [ ] Failed images marked red; user can re-upload to replace
- [ ] Watermark check accuracy ≥85 % on 30-image seed test
- [ ] Total upload size capped at 60 MB per product (6 × 10 MB)

**Edge cases:**
- Upload not JPEG/PNG → reject at API with 415
- GCS upload fails → return 503, do not enqueue check
- Gemini vision unavailable → mark `no_watermark` as `skipped`, allow user to proceed with warning

**Effort estimate:** Backend 12 h · Frontend 6 h · **Total 18 h**

---

### Feature 6: Live Product Preview
**Pain solved:** Theme 4 (IMAGE PREVIEW MISSING) — strongly validated, no competitor has it.

**User journey:**
1. User on `/catalogs/:id/preview` sees three mock views: feed thumbnail, product detail page, mobile card
2. Backend assembles preview JSON from `products.fields_jsonb` + first image
3. Frontend renders Meesho-style components (CSS clone) with the user's title, price, image, variant
4. Title truncation indicator shows where Meesho mobile cuts (≈30 chars)

**Technical components:**
- Frontend: `PreviewFeedComponent`, `PreviewDetailComponent`, `PreviewMobileComponent`
- Backend: `GET /api/v1/products/:id/preview`
- Database: read-only from `products`, `product_images`
- External: none

**Acceptance criteria:**
- [ ] All three previews render within 1 s after page load
- [ ] Title truncation marker matches Meesho mobile (≈30 char) in feed thumbnail
- [ ] Image carousel shows uploaded order; swipe works on mobile
- [ ] If <1 image or title missing, preview shows placeholder with "fill required fields" CTA
- [ ] Visual diff vs real Meesho card ≤10 % (qualitative — manual check by founder)

**Edge cases:**
- Variant swatches: V1 shows first variant only (full variant matrix is V1.5)
- Very long descriptions truncated at 200 chars in detail preview

**Effort estimate:** Backend 3 h · Frontend 10 h · **Total 13 h**

---

### Feature 7: Price Calculator
**Pain solved:** Theme 5 (PRICING CONFUSION) — strongly validated, 5+ external calculators exist.

**User journey:**
1. User on `/catalogs/:id/pricing` enters MRP and target seller-payout
2. Frontend POSTs to `/api/v1/products/:id/price-calc`
3. Backend computes: commission (from `categories.commission_pct`), GST (from category HSN), Meesho price, seller price, gross margin
4. UI shows breakdown table + margin %; user adjusts MRP slider to hit target margin
5. On accept, values stored in `pricing_calcs`

**Technical components:**
- Frontend: `PricingComponent`, `PnlBreakdownComponent`, `MarginSliderComponent`
- Backend: `POST /api/v1/products/:id/price-calc`
- Database: `pricing_calcs`
- External: none

**Data model (pricing_calcs):**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK | |
| mrp | NUMERIC(10,2) | |
| meesho_price | NUMERIC(10,2) | |
| seller_price | NUMERIC(10,2) | |
| commission_pct | NUMERIC(5,2) | snapshot |
| gst_pct | NUMERIC(5,2) | snapshot |
| margin | NUMERIC(10,2) | absolute |
| margin_pct | NUMERIC(5,2) | |
| created_at | TIMESTAMPTZ | |

**Acceptance criteria:**
- [ ] Calculation returns within 200 ms
- [ ] Breakdown shows: MRP, Meesho Price, Commission, GST, Seller Payout, Net Margin
- [ ] Slider updates breakdown live (<100 ms refresh)
- [ ] Commission and GST snapshotted at calculation time (resilient to later edits)
- [ ] Negative-margin scenarios show red warning

**Edge cases:**
- MRP < seller payout → return 400 with helpful message
- Category missing commission → fallback to category-group average, flag in response
- RTO/shipping deferred to V1.5 (note in UI: "Shipping not included in V1")

**Effort estimate:** Backend 4 h · Frontend 5 h · **Total 9 h**

---

### Feature 8: Tracking Dashboard
**Pain solved:** Theme 2 sub-pain (no saved drafts) + table-stakes for SaaS UX.

**User journey:**
1. User lands on `/dashboard` after login
2. Frontend GETs `/api/v1/products?page=1&limit=20`
3. UI shows table: name, category, status (draft/exported/live), updated_at, actions (edit/export/delete)
4. Filter by status; search by name
5. Clicking row navigates to `/catalogs/:id/edit`

**Technical components:**
- Frontend: `DashboardComponent`, `ProductRowComponent`, `StatusBadgeComponent`
- Backend: `GET /api/v1/products`, `DELETE /api/v1/products/:id`
- Database: reads from `products`, joins `catalogs`, `categories`
- External: none

**Acceptance criteria:**
- [ ] Dashboard loads ≤500 ms with 100 products
- [ ] Status badge color-coded (gray draft / blue exported / green live)
- [ ] Pagination works for >20 products
- [ ] Search returns results within 500 ms (ILIKE on `products.name`)
- [ ] Delete confirms with modal, soft-delete (`deleted_at` column)

**Edge cases:**
- Zero products → empty state with "Create your first catalog" CTA
- "Live" status is manually set by user (since Meesho has no API to confirm) → tooltip clarifies

**Effort estimate:** Backend 3 h · Frontend 5 h · **Total 8 h**

---

### Feature 9: XLSX Export
**Pain solved:** Theme 2 + Section 3.5 (bulk template errors) — Meesho has no third-party API; XLSX is the only path.

**User journey:**
1. User on `/catalogs/:id/export` clicks "Generate XLSX"
2. Backend validates all compulsory fields present + ≥1 image uploaded
3. Worker generates Meesho-format XLSX (matching scraped category template) + ZIP of images
4. GCS signed URL returned; user downloads
5. `products.status` → `exported`; `exports` row inserted

**Technical components:**
- Frontend: `ExportComponent`, `ExportProgressComponent`
- Backend: `POST /api/v1/products/:id/export-xlsx`, `GET /api/v1/exports/:id`
- Database: `exports` table
- External: GCS, openpyxl, Pillow

**Data model (exports):**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK | |
| user_id | UUID FK | |
| xlsx_gcs_path | TEXT | |
| zip_gcs_path | TEXT | |
| status | VARCHAR(16) | `processing` / `ready` / `failed` |
| download_url | TEXT | signed, expires 1 h |
| created_at | TIMESTAMPTZ | |

**Acceptance criteria:**
- [ ] Generated XLSX opens cleanly in Excel + LibreOffice
- [ ] Column order matches Meesho's category-specific template
- [ ] Image ZIP filenames match XLSX image-reference column
- [ ] Generation completes within 15 s for 1 product with 6 images
- [ ] Validation blocks export with clear error list ("Title missing, 2 images missing")

**Edge cases:**
- Category XLSX template missing in seed data → return 422 with "category not yet supported"
- Image not yet `pass` in pre-check → block export with warning
- Failed generation → mark `failed`, allow retry

**Effort estimate:** Backend 10 h · Frontend 4 h · **Total 14 h**

---

## Section 3: End-to-End User Journey

A new Tirupur seller signs up and exports their first catalog:

1. **Land on `/`** — Hero: "Create a Meesho catalog in 3 minutes." CTA: "Start free."
2. **`/signup` → enter phone** — MSG91 sends OTP.
3. **`/login` OTP screen** — Enter 6-digit OTP → JWT issued → redirect `/dashboard`.
4. **`/dashboard`** — Empty state: "Create your first catalog." Click CTA.
5. **`/catalogs/new` (Smart Category Picker)** — User types: "Blue cotton kurti with mirror work for women, size M to XXL." → 3 cards returned: "Fashion > Women > Ethnic > Kurti" (94 %), "Fashion > Women > Ethnic > Kurta Set" (71 %), "Fashion > Women > Tops > Tunic" (52 %). User picks Kurti.
6. **`/catalogs/:id/edit`** — Form renders 32 Kurti-specific fields. User clicks "AI fill" → compulsory fields populate yellow. User reviews, edits brand name, accepts rest. Autosave fires.
7. **`/catalogs/:id/images`** — User drags 4 images. Pre-check runs: image #2 fails CMYK; user converts and re-uploads. All 4 pass.
8. **`/catalogs/:id/preview`** — User sees feed thumbnail, detail page, mobile card. Title cuts at "Blue Cotton Kurti With Mir…" — user shortens to "Blue Cotton Kurti — Mirror Work."
9. **`/catalogs/:id/pricing`** — Enters MRP ₹899, target margin ₹150. Calculator shows commission 5 %, GST 5 %, Meesho price ₹450, seller payout ₹408, net margin ₹158 (positive — green).
10. **`/catalogs/:id/export`** — Validation passes. XLSX + image ZIP generated. Download URL displayed.
11. **Outside MeeSell** — User uploads to Meesho supplier panel.
12. **Back in `/dashboard`** — User marks the product "live" once Meesho QC approves.

---

## Section 4: Data Model (PostgreSQL)

```sql
-- users
CREATE TABLE users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone        VARCHAR(15) UNIQUE NOT NULL,
  email        VARCHAR(255),
  plan         VARCHAR(20) DEFAULT 'free',
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  last_login_at TIMESTAMPTZ
);

-- categories (preseeded from 3,772-leaf tree)
CREATE TABLE categories (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meesho_id       VARCHAR(64) UNIQUE,
  name            VARCHAR(255) NOT NULL,
  parent_id       UUID REFERENCES categories(id),
  path            TEXT NOT NULL,
  commission_pct  NUMERIC(5,2),
  attributes_jsonb JSONB NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_categories_parent ON categories(parent_id);

-- catalogs (a logical grouping; V1 = 1 catalog per product)
CREATE TABLE catalogs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  name        VARCHAR(255) NOT NULL,
  category_id UUID REFERENCES categories(id),
  status      VARCHAR(20) DEFAULT 'draft',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- products
CREATE TABLE products (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  catalog_id          UUID NOT NULL REFERENCES catalogs(id),
  user_id             UUID NOT NULL REFERENCES users(id),
  category_id         UUID REFERENCES categories(id),
  name                VARCHAR(512),
  description         TEXT,
  fields_jsonb        JSONB DEFAULT '{}'::jsonb,
  ai_suggestions_jsonb JSONB DEFAULT '{}'::jsonb,
  status              VARCHAR(20) DEFAULT 'draft',
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_products_user ON products(user_id);
CREATE INDEX idx_products_status ON products(status);

-- product_images
CREATE TABLE product_images (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  gcs_path        TEXT NOT NULL,
  order_idx       INT NOT NULL,
  width           INT, height INT,
  color_space     VARCHAR(8),
  precheck_jsonb  JSONB,
  status          VARCHAR(16) DEFAULT 'pending',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- pricing_calcs
CREATE TABLE pricing_calcs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  mrp             NUMERIC(10,2),
  meesho_price    NUMERIC(10,2),
  seller_price    NUMERIC(10,2),
  commission_pct  NUMERIC(5,2),
  gst_pct         NUMERIC(5,2),
  margin          NUMERIC(10,2),
  margin_pct      NUMERIC(5,2),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- exports
CREATE TABLE exports (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID NOT NULL REFERENCES products(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  xlsx_gcs_path   TEXT,
  zip_gcs_path    TEXT,
  status          VARCHAR(16) DEFAULT 'processing',
  download_url    TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Section 5: API Endpoints (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/otp/send` | Send 6-digit OTP via MSG91 |
| POST | `/api/v1/auth/otp/verify` | Verify OTP, return JWT |
| POST | `/api/v1/auth/login` | Reserved (V1.5 email/password) |
| GET  | `/api/v1/categories/suggest?q=<desc>` | Smart picker — top-3 Gemini suggestions |
| GET  | `/api/v1/categories/{id}/schema` | Field schema for category |
| POST | `/api/v1/products` | Create draft product |
| PATCH | `/api/v1/products/{id}` | Autosave field changes |
| POST | `/api/v1/products/{id}/autofill` | Gemini auto-fill |
| POST | `/api/v1/products/{id}/images` | Upload image + queue pre-check |
| GET  | `/api/v1/products/{id}/images` | List images + check status |
| GET  | `/api/v1/products/{id}/preview` | Live preview JSON |
| POST | `/api/v1/products/{id}/price-calc` | Pricing breakdown |
| GET  | `/api/v1/products` | List for dashboard (paginated) |
| DELETE | `/api/v1/products/{id}` | Soft delete |
| POST | `/api/v1/products/{id}/export-xlsx` | Trigger XLSX generation |
| GET  | `/api/v1/exports/{id}` | Poll export status + download URL |

All endpoints require JWT in `Authorization: Bearer` header, except `/auth/otp/*`.

---

## Section 6: Frontend Routes (Angular 18)

| Route | Component | Purpose |
|---|---|---|
| `/` | `LandingComponent` | Hero + CTA |
| `/signup` | `SignupComponent` | Phone entry → OTP |
| `/login` | `LoginComponent` | Phone + OTP |
| `/dashboard` | `DashboardComponent` | Product list + filters |
| `/catalogs/new` | `SmartPickerComponent` | Description → category |
| `/catalogs/:id/edit` | `CatalogFormComponent` | Form + autofill |
| `/catalogs/:id/images` | `ImageUploaderComponent` | Upload + pre-check report |
| `/catalogs/:id/preview` | `PreviewComponent` | Feed / detail / mobile previews |
| `/catalogs/:id/pricing` | `PricingComponent` | Calculator + margin slider |
| `/catalogs/:id/export` | `ExportComponent` | XLSX trigger + download |

Auth guarded routes: everything except `/`, `/signup`, `/login`.

---

## Section 7: Effort Summary

| Feature | Backend hrs | Frontend hrs | Total |
|---|---:|---:|---:|
| 1. Auth (OTP + JWT) | 6 | 4 | 10 |
| 2. Smart Category Picker | 8 | 5 | 13 |
| 3. Fast Catalog Form | 5 | 9 | 14 |
| 4. AI Auto-fill | 7 | 4 | 11 |
| 5. Image Pre-check | 12 | 6 | 18 |
| 6. Live Product Preview | 3 | 10 | 13 |
| 7. Price Calculator | 4 | 5 | 9 |
| 8. Tracking Dashboard | 3 | 5 | 8 |
| 9. XLSX Export | 10 | 4 | 14 |
| Infra / seed / glue (categories preload, GCS setup, K3s deploy, auth middleware, error pages) | 8 | 4 | 12 |
| **TOTAL V1** | **66** | **56** | **122 h** |

**Fit in 7 days with AI-agent leverage:**
- Solo founder, 12 productive hours/day × 7 = 84 hours of direct hands-on time
- AI agents handle ~30 % of code generation (boilerplate, schemas, simple components)
- Effective throughput: 84 h human + ~38 h agent leverage = ~122 h coverage
- **Day 1:** Auth + categories seed + dashboard scaffold (Features 1, 8)
- **Day 2:** Smart picker + form schema rendering (Features 2, 3)
- **Day 3:** AI autofill + form polish (Feature 4)
- **Day 4:** Image upload + pre-check pipeline (Feature 5)
- **Day 5:** Live preview (Feature 6)
- **Day 6:** Price calculator + XLSX export (Features 7, 9)
- **Day 7:** End-to-end testing, bug fixes, GCP deploy

Buffer: tight. If image pre-check slips, move watermark detection to V1.5 (other 4 checks are cheap).

---

## Section 8: V1 Done — Acceptance Checklist

- [ ] User can sign up + login via phone OTP
- [ ] User can create a catalog from any of 3,772 categories via Smart Picker
- [ ] User can fill the category-specific form with AI auto-fill assistance
- [ ] User can upload up to 6 images with all 5 pre-checks reporting pass/fail
- [ ] User sees live Meesho-style preview (feed / detail / mobile) before publish
- [ ] User sees price calculation with commission, GST, and net margin
- [ ] User can export a Meesho-format XLSX + image ZIP and download via signed URL
- [ ] User can see all their drafts/exports in dashboard with status filters
- [ ] All routes auth-guarded; JWT refresh works
- [ ] End-to-end journey completes in <10 minutes for a first-time user (founder time-trial)

---
