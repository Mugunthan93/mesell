# MeeSell — MVP Technical Specification

> AI-powered operating system for Meesho suppliers  
> Version: MVP (Month 1–3)  
> Modules in scope: CatalogAI · QualityGate · PriceIntel (Calculator only)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                  CLIENT LAYER                     │
│  React SPA (Vite) + Tailwind CSS + PWA           │
│  Mobile-first · Hindi/English toggle              │
└────────────────────┬─────────────────────────────┘
                     │ HTTPS (REST JSON)
┌────────────────────▼─────────────────────────────┐
│              API GATEWAY (FastAPI)                 │
│  Auth middleware · Rate limiter · CORS             │
│  Uvicorn + Gunicorn (4 workers)                   │
├───────────┬───────────┬───────────┬──────────────┤
│ /auth     │ /catalog  │ /quality  │ /pricing     │
│ OTP login │ AI gen    │ Validate  │ Calculator   │
│ JWT issue │ CRUD      │ Score     │ P&L          │
└─────┬─────┴─────┬─────┴─────┬─────┴──────┬───────┘
      │           │           │            │
┌─────▼───────────▼───────────▼────────────▼───────┐
│              SHARED SERVICES                      │
├──────────────┬──────────────┬─────────────────────┤
│ AI Engine    │ Image Engine │ File Store           │
│ Gemini Flash │ rembg + PIL  │ S3 / Cloudflare R2  │
└──────┬───────┴──────┬───────┴──────────┬──────────┘
       │              │                  │
┌──────▼──────────────▼──────────────────▼──────────┐
│              DATA LAYER                            │
│  PostgreSQL 16 (RDS) · Redis 7 (ElastiCache)      │
└───────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| Frontend | React + Vite | 18.x / 5.x | Fast builds, PWA-ready |
| Styling | Tailwind CSS | 3.x | Utility-first, mobile-responsive |
| State | Zustand | 4.x | Lightweight, no boilerplate |
| Backend | FastAPI (Python) | 0.110+ | Async, fast, AI/ML ecosystem |
| ASGI Server | Uvicorn + Gunicorn | Latest | Production async server |
| AI Text | Google Gemini 2.5 Flash | Latest | ₹0.12/catalog, best price-quality |
| AI Vision | rembg (open source) | Latest | Free BG removal, self-hosted |
| Image Processing | Pillow (PIL) | 10.x | Resize, white BG, format conversion |
| Database | PostgreSQL | 16 | Relational, JSONB for attributes |
| Cache / Sessions | Redis | 7.x | Session store, rate limiting, queues |
| File Storage | AWS S3 | — | Product images, generated catalogs |
| Auth | MSG91 (OTP) + PyJWT | — | Phone OTP login, JWT tokens |
| Payments | Razorpay Subscriptions | — | Indian payments, auto-renewal |
| Task Queue | Celery + Redis broker | 5.x | Background AI generation jobs |
| Hosting | AWS ap-south-1 (Mumbai) | — | Low latency India |
| CDN | CloudFront | — | Image delivery |
| Monitoring | Sentry + PostHog | — | Error tracking + product analytics |

---

## 3. Database Schema

### 3.1 Users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           VARCHAR(15) UNIQUE NOT NULL,
    name            VARCHAR(100),
    email           VARCHAR(255),
    plan            VARCHAR(20) DEFAULT 'free',  -- free | starter | pro | growth
    plan_expires_at TIMESTAMPTZ,
    razorpay_sub_id VARCHAR(100),
    catalogs_used   INTEGER DEFAULT 0,           -- monthly counter
    catalogs_limit  INTEGER DEFAULT 5,           -- based on plan
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_plan ON users(plan);
```

### 3.2 Catalogs

```sql
CREATE TABLE catalogs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(20) DEFAULT 'draft',  -- draft | generated | validated | exported
    category        VARCHAR(100),
    subcategory     VARCHAR(100),
    quality_score   INTEGER,                      -- 0-100 from QualityGate
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_catalogs_user ON catalogs(user_id);
CREATE INDEX idx_catalogs_status ON catalogs(status);
```

### 3.3 SKUs (Products within a catalog)

```sql
CREATE TABLE skus (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_id      UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    
    -- Seller input
    product_name    VARCHAR(255) NOT NULL,
    cost_price      DECIMAL(10,2),
    selling_price   DECIMAL(10,2),
    weight_grams    INTEGER,
    material        VARCHAR(100),
    sizes           VARCHAR(255),                 -- "S,M,L,XL,XXL"
    colors          VARCHAR(255),                 -- "Red,Blue,Green"
    
    -- AI generated
    ai_title        TEXT,
    ai_description  TEXT,
    ai_keywords     TEXT,                         -- comma-separated
    ai_category     VARCHAR(100),                 -- Meesho category mapping
    ai_attributes   JSONB,                        -- {"fabric":"cotton", "fit":"straight", ...}
    
    -- Pricing
    margin_amount   DECIMAL(10,2),
    margin_percent  DECIMAL(5,2),
    shipping_cost   DECIMAL(10,2),
    return_provision DECIMAL(10,2),
    
    -- Quality
    quality_checks  JSONB,                        -- {"image_size": "pass", "title_length": "pass", ...}
    quality_score   INTEGER,
    
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skus_catalog ON skus(catalog_id);
```

### 3.4 Images

```sql
CREATE TABLE images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_id          UUID REFERENCES skus(id) ON DELETE CASCADE,
    
    original_url    TEXT NOT NULL,                 -- S3 path: originals/{user_id}/{filename}
    processed_url   TEXT,                          -- S3 path: processed/{user_id}/{filename}
    
    -- Processing status
    bg_removed      BOOLEAN DEFAULT FALSE,
    resized         BOOLEAN DEFAULT FALSE,
    width           INTEGER,
    height          INTEGER,
    file_size_kb    INTEGER,
    format          VARCHAR(10),                  -- jpg | png
    
    -- Quality checks
    has_watermark   BOOLEAN DEFAULT FALSE,
    is_compliant    BOOLEAN DEFAULT FALSE,
    compliance_note TEXT,
    
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_images_sku ON images(sku_id);
```

### 3.5 Export History

```sql
CREATE TABLE exports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    catalog_id      UUID REFERENCES catalogs(id),
    export_type     VARCHAR(20) NOT NULL,         -- meesho_csv | images_zip
    file_url        TEXT,                          -- S3 download URL
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.6 OTP Sessions (Redis — not PostgreSQL)

```
Key:    otp:{phone}
Value:  {"code": "1234", "attempts": 0, "created_at": "..."}
TTL:    300 (5 minutes)
```

---

## 4. API Endpoints

### 4.1 Auth Module

```
POST   /api/v1/auth/send-otp
       Body: { "phone": "+919876543210" }
       → Sends OTP via MSG91, stores in Redis
       Response: { "message": "OTP sent", "expires_in": 300 }

POST   /api/v1/auth/verify-otp
       Body: { "phone": "+919876543210", "otp": "1234" }
       → Verifies OTP, creates user if new, issues JWT
       Response: { "token": "eyJ...", "user": { id, phone, name, plan } }

GET    /api/v1/auth/me
       Headers: Authorization: Bearer {token}
       → Returns current user profile + plan details
       Response: { "user": { id, phone, name, plan, catalogs_used, catalogs_limit } }
```

### 4.2 Catalog Module

```
POST   /api/v1/catalogs
       Headers: Authorization: Bearer {token}
       Body: { "name": "Cotton Kurti Collection" }
       → Creates empty catalog shell
       Response: { "catalog": { id, name, status: "draft" } }

GET    /api/v1/catalogs
       → List user's catalogs (paginated)
       Query: ?status=draft&page=1&limit=20
       Response: { "catalogs": [...], "total": 42, "page": 1 }

GET    /api/v1/catalogs/{catalog_id}
       → Get catalog with all SKUs and images
       Response: { "catalog": { ..., "skus": [ { ..., "images": [...] } ] } }

DELETE /api/v1/catalogs/{catalog_id}
       → Soft delete catalog
```

### 4.3 SKU Module

```
POST   /api/v1/catalogs/{catalog_id}/skus
       Body: { "product_name": "...", "cost_price": 220, "selling_price": 599, 
               "weight_grams": 350, "material": "cotton", "sizes": "S,M,L,XL" }
       → Add SKU to catalog
       Response: { "sku": { id, product_name, ... } }

PUT    /api/v1/skus/{sku_id}
       Body: { "ai_title": "edited title...", "selling_price": 649 }
       → Update SKU (seller edits AI output or changes price)

DELETE /api/v1/skus/{sku_id}
```

### 4.4 Image Upload + Processing

```
POST   /api/v1/skus/{sku_id}/images
       Content-Type: multipart/form-data
       Body: file (JPG/PNG, max 10MB)
       → Uploads original to S3, queues background processing job
       Response: { "image": { id, original_url, status: "processing" } }

       Background job (Celery):
         1. Run rembg → remove background
         2. Add white background (255,255,255)
         3. Resize to 1024×1024 (center crop + pad)
         4. Save processed image to S3
         5. Update image record: processed_url, bg_removed=true, resized=true
         6. Run watermark detection (basic CV)
         7. Update compliance status

GET    /api/v1/images/{image_id}/status
       → Check processing status
       Response: { "status": "completed", "processed_url": "..." }
```

### 4.5 AI Generation

```
POST   /api/v1/catalogs/{catalog_id}/generate
       → Triggers AI generation for all SKUs in catalog
       → Checks plan limit (catalogs_used < catalogs_limit)
       → Queues Celery job for each SKU
       Response: { "job_id": "...", "status": "processing", "sku_count": 6 }

       Background job per SKU (Celery):
         1. Build prompt with product_name, material, category, image analysis
         2. Call Gemini 2.5 Flash API
         3. Parse response → ai_title, ai_description, ai_keywords, ai_attributes
         4. Auto-map Meesho category
         5. Save to SKU record
         6. Increment user.catalogs_used
         7. Trigger QualityGate auto-check

GET    /api/v1/jobs/{job_id}
       → Check generation job status
       Response: { "status": "completed", "skus_done": 6, "skus_total": 6 }

POST   /api/v1/skus/{sku_id}/regenerate
       → Regenerate AI content for single SKU (with different prompt variation)
```

### 4.6 QualityGate

```
POST   /api/v1/catalogs/{catalog_id}/validate
       → Runs all quality checks on catalog
       Response: { 
         "overall_score": 92,
         "status": "pass",
         "checks": [
           { "check": "image_size", "status": "pass", "detail": "All 24 images 1024×1024" },
           { "check": "white_bg", "status": "pass", "detail": "..." },
           { "check": "watermark", "status": "pass", "detail": "..." },
           { "check": "title_length", "status": "pass", "detail": "..." },
           { "check": "required_attributes", "status": "warn", "detail": "Missing wash_care for 2 SKUs" },
           { "check": "duplicate", "status": "pass", "detail": "..." },
           { "check": "banned_words", "status": "pass", "detail": "..." },
           { "check": "category_mapping", "status": "pass", "detail": "..." }
         ]
       }
```

### 4.7 PriceIntel (Calculator)

```
POST   /api/v1/pricing/calculate
       Body: {
         "selling_price": 599,
         "cost_price": 220,
         "weight_grams": 350,
         "category": "kurtis",
         "return_rate": 0.18,        // optional, defaults to category avg
         "ad_spend_per_order": 0,     // optional
         "packaging_cost": 12         // optional, defaults to 12
       }
       → Returns full P&L breakdown
       Response: {
         "selling_price": 599,
         "cost_price": 220,
         "commission": 0,
         "shipping_cost": 58,
         "shipping_gst": 10.44,
         "payment_processing": 11.98,
         "packaging": 12,
         "return_provision": 10.44,
         "net_profit": 276.14,
         "margin_percent": 46.1,
         "weight_slab": "0-500g",
         "alerts": [
           { "type": "weight_warning", "message": "350g — close to 500g slab jump (+₹24 shipping)" },
           { "type": "competitor_context", "message": "Category avg price: ₹499-649" }
         ]
       }

       Note: This endpoint is PUBLIC (no auth required for free calculator).
       Unauthenticated users get basic calculation.
       Authenticated users get return_rate from their own data + competitor context.
```

### 4.8 Export

```
POST   /api/v1/catalogs/{catalog_id}/export/meesho-csv
       → Generates Meesho bulk upload CSV
       → Columns match Meesho's template exactly:
         catalog_name, product_title, description, category, subcategory,
         mrp, selling_price, gst_percent, hsn_code, sizes, colors,
         material, brand, country_of_origin, manufacturer_details,
         image_1, image_2, image_3, image_4, ...
       Response: { "download_url": "https://s3.../exports/{user_id}/catalog_123.csv", "expires_in": 3600 }

POST   /api/v1/catalogs/{catalog_id}/export/images-zip
       → Zips all processed images for the catalog
       → Named: {sku_name}_1.jpg, {sku_name}_2.jpg, etc.
       Response: { "download_url": "https://s3.../exports/{user_id}/catalog_123_images.zip", "expires_in": 3600 }
```

---

## 5. AI Pipeline Detail

### 5.1 Gemini Prompt Template

```python
CATALOG_GENERATION_PROMPT = """
You are a Meesho product listing expert. Generate an optimized product listing 
for the Meesho marketplace.

Product Details:
- Name: {product_name}
- Category: {category}
- Material: {material}
- Sizes Available: {sizes}
- Colors: {colors}
- Price Range: ₹{selling_price}

Image Analysis: {image_description}

Generate the following in JSON format:
{{
  "title": "SEO-optimized title for Meesho (max 200 chars). Include: product type, 
            material, fit, occasion, gender. Example format: 
            'Women Cotton Kurti Straight Fit Casual Wear Printed A-Line Kurta'",
  "description": "Compelling product description (200-500 chars). Highlight material, 
                   comfort, occasion, care instructions.",
  "keywords": ["keyword1", "keyword2", ...],  // 10-15 search keywords
  "category": "Meesho category path (e.g. Women > Ethnic Wear > Kurtis)",
  "attributes": {{
    "fabric": "...",
    "fit": "...",
    "occasion": "...",
    "sleeve_type": "...",
    "neck_type": "...",
    "wash_care": "...",
    "country_of_origin": "India"
  }}
}}

Rules:
- Title must be in English, SEO-friendly, no special characters
- Include primary keyword within first 80 characters of title
- Description should address common buyer questions
- Map to exact Meesho category taxonomy
- All attributes must match Meesho's accepted values for this category
"""
```

### 5.2 Image Processing Pipeline

```python
# Celery task: process_image

async def process_image(image_id: str):
    image = await db.get_image(image_id)
    
    # 1. Download original from S3
    original = download_from_s3(image.original_url)
    
    # 2. Background removal (rembg)
    from rembg import remove
    no_bg = remove(original)
    
    # 3. Add white background
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, mask=no_bg.split()[3])
    result = white_bg.convert("RGB")
    
    # 4. Resize to 1024×1024 (center-crop + pad)
    result = resize_and_pad(result, target=(1024, 1024), fill=(255, 255, 255))
    
    # 5. Optimize file size (JPEG quality 90, target < 500KB)
    buffer = compress_jpeg(result, quality=90, max_kb=500)
    
    # 6. Upload processed to S3
    processed_url = upload_to_s3(buffer, f"processed/{user_id}/{image_id}.jpg")
    
    # 7. Basic watermark detection
    has_watermark = detect_watermark(result)  # edge detection + text OCR
    
    # 8. Update database
    await db.update_image(image_id, {
        "processed_url": processed_url,
        "bg_removed": True,
        "resized": True,
        "width": 1024,
        "height": 1024,
        "has_watermark": has_watermark,
        "is_compliant": not has_watermark
    })
```

### 5.3 QualityGate Rules Engine

```python
QUALITY_RULES = {
    "image_size": {
        "check": lambda img: img.width == 1024 and img.height == 1024,
        "weight": 15,
        "severity": "fail",
        "fix": "Image will be auto-resized to 1024×1024"
    },
    "white_bg": {
        "check": lambda img: detect_white_background(img),  # >90% white in corners
        "weight": 15,
        "severity": "fail",
        "fix": "Background will be auto-removed and replaced with white"
    },
    "watermark": {
        "check": lambda img: not img.has_watermark,
        "weight": 10,
        "severity": "fail",
        "fix": "Remove watermarks/text overlays before uploading"
    },
    "title_length": {
        "check": lambda sku: len(sku.ai_title) <= 200,
        "weight": 10,
        "severity": "fail",
        "fix": "Title exceeds 200 characters. Will be auto-trimmed."
    },
    "title_keywords": {
        "check": lambda sku: has_primary_keyword_in_first_80(sku),
        "weight": 10,
        "severity": "warn",
        "fix": "Move main keyword to beginning of title for better SEO"
    },
    "required_attributes": {
        "check": lambda sku: all_required_attrs_present(sku),
        "weight": 10,
        "severity": "warn",
        "fix": "Add missing attributes to reduce rejection risk"
    },
    "banned_words": {
        "check": lambda sku: no_banned_words(sku),
        "weight": 15,
        "severity": "fail",
        "fix": "Remove prohibited terms (branded names, misleading claims)"
    },
    "duplicate_check": {
        "check": lambda sku, user: no_duplicate_catalog(sku, user),
        "weight": 10,
        "severity": "warn",
        "fix": "Similar catalog exists. Meesho may reject duplicates."
    },
    "category_mapping": {
        "check": lambda sku: valid_meesho_category(sku.ai_category),
        "weight": 5,
        "severity": "fail",
        "fix": "Category not found in Meesho taxonomy. Remapping..."
    }
}

# Score = sum of passed checks × weight / total weight × 100
# Status: "pass" if score >= 70 and no "fail" severity checks failed
```

---

## 6. Meesho CSV Export Format

```python
MEESHO_CSV_COLUMNS = [
    "catalog_name",
    "product_title",
    "product_description",
    "category",
    "sub_category",
    "mrp",
    "selling_price",
    "gst_percentage",
    "hsn_code",
    "size",
    "color",
    "brand",
    "material",
    "country_of_origin",
    "manufacturer_name",
    "manufacturer_address",
    "packer_name",
    "packer_address",
    "image_1",          # Primary image URL or local filename
    "image_2",
    "image_3",
    "image_4",
    "weight_grams",
    "length_cm",
    "width_cm",
    "height_cm",
    # Category-specific attributes appended dynamically
]

# Export generates CSV matching Meesho's bulk upload template exactly.
# Images referenced by filename (seller uploads images separately to Meesho).
```

---

## 7. Pricing Engine (Meesho-specific)

```python
MEESHO_SHIPPING_SLABS = {
    # weight_range: { zone_a, zone_b, zone_c, zone_d, zone_e }
    "0-500":    { "a": 29, "b": 58, "c": 68, "d": 78, "e": 88 },
    "500-1000": { "a": 42, "b": 82, "c": 92, "d": 102, "e": 112 },
    "1000-2000":{ "a": 55, "b": 106, "c": 116, "d": 126, "e": 136 },
    "2000-5000":{ "a": 80, "b": 156, "c": 176, "d": 196, "e": 216 },
}

CATEGORY_RETURN_RATES = {
    "kurtis": 0.18,
    "sarees": 0.12,
    "t_shirts": 0.22,
    "jeans": 0.25,
    "shoes": 0.28,
    "home_decor": 0.08,
    "electronics": 0.10,
    # ... populated from Meesho public data + seller community knowledge
}

def calculate_pnl(selling_price, cost_price, weight_grams, category, 
                  return_rate=None, ad_spend=0, packaging=12):
    
    weight_slab = get_weight_slab(weight_grams)
    shipping = MEESHO_SHIPPING_SLABS[weight_slab]["b"]  # default Zone B
    shipping_gst = shipping * 0.18
    commission = 0  # Meesho currently charges 0% commission
    payment_processing = selling_price * 0.02
    
    if return_rate is None:
        return_rate = CATEGORY_RETURN_RATES.get(category, 0.15)
    
    return_provision = shipping * return_rate
    
    net_profit = (selling_price - cost_price - commission - shipping 
                  - shipping_gst - payment_processing - packaging 
                  - return_provision - ad_spend)
    
    margin_percent = (net_profit / selling_price) * 100
    
    # Alerts
    alerts = []
    next_slab_threshold = get_next_slab_threshold(weight_grams)
    if next_slab_threshold and (next_slab_threshold - weight_grams) < 150:
        next_shipping = MEESHO_SHIPPING_SLABS[get_weight_slab(next_slab_threshold)]["b"]
        alerts.append({
            "type": "weight_warning",
            "message": f"{weight_grams}g — close to {next_slab_threshold}g slab "
                       f"(+₹{next_shipping - shipping} shipping)"
        })
    
    if margin_percent < 15:
        alerts.append({
            "type": "low_margin",
            "message": f"Margin {margin_percent:.1f}% is below 15% threshold"
        })
    
    return { ... }
```

---

## 8. Authentication Flow

```
1. User enters phone number
2. POST /auth/send-otp → MSG91 sends SMS OTP
3. OTP stored in Redis: key=otp:+919876543210, TTL=300s
4. User enters OTP
5. POST /auth/verify-otp → verify against Redis
6. If new user → INSERT into users table (plan=free)
7. Issue JWT (HS256, 7-day expiry, contains user_id + plan)
8. Frontend stores JWT in httpOnly cookie
9. All subsequent requests include Authorization: Bearer {jwt}
10. Middleware validates JWT + checks plan limits per request
```

---

## 9. Rate Limiting & Plan Enforcement

```python
PLAN_LIMITS = {
    "free":    { "catalogs_per_month": 5,   "quality_checks_per_day": 3,  "images_per_catalog": 4 },
    "starter": { "catalogs_per_month": 50,  "quality_checks_per_day": -1, "images_per_catalog": 9 },
    "pro":     { "catalogs_per_month": 200, "quality_checks_per_day": -1, "images_per_catalog": 9 },
    "growth":  { "catalogs_per_month": -1,  "quality_checks_per_day": -1, "images_per_catalog": 9 },
}

# -1 = unlimited

# Rate limiting via Redis sliding window:
# Key: ratelimit:{user_id}:{endpoint}:{window}
# Window: per-minute (60s) and per-day (86400s)

RATE_LIMITS = {
    "/catalog/generate":  { "per_minute": 5,  "per_day": 50 },
    "/images/upload":     { "per_minute": 20, "per_day": 200 },
    "/pricing/calculate": { "per_minute": 30, "per_day": 500 },
}
```

---

## 10. Project Structure

```
meesell/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, middleware
│   │   ├── config.py               # Environment config (pydantic settings)
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── image.py
│   │   │   └── export.py
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── quality.py
│   │   │   └── pricing.py
│   │   ├── routers/                # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── catalogs.py
│   │   │   ├── skus.py
│   │   │   ├── images.py
│   │   │   ├── quality.py
│   │   │   ├── pricing.py
│   │   │   └── exports.py
│   │   ├── services/               # Business logic
│   │   │   ├── ai_engine.py        # Gemini API calls + prompt management
│   │   │   ├── image_processor.py  # rembg + PIL pipeline
│   │   │   ├── quality_engine.py   # QualityGate rules engine
│   │   │   ├── pricing_engine.py   # P&L calculator
│   │   │   ├── export_service.py   # CSV/ZIP generation
│   │   │   ├── otp_service.py      # MSG91 integration
│   │   │   └── storage.py          # S3 upload/download
│   │   ├── workers/                # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── image_tasks.py      # Background image processing
│   │   │   └── generation_tasks.py # Background AI generation
│   │   ├── middleware/
│   │   │   ├── auth.py             # JWT validation
│   │   │   ├── rate_limit.py       # Redis sliding window
│   │   │   └── plan_guard.py       # Plan limit enforcement
│   │   └── data/
│   │       ├── meesho_categories.json    # Meesho category taxonomy
│   │       ├── meesho_shipping_slabs.json
│   │       ├── banned_words.json
│   │       └── category_attributes.json  # Required attrs per category
│   ├── alembic/                    # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/                    # API client (axios)
│   │   │   └── client.js
│   │   ├── stores/                 # Zustand stores
│   │   │   ├── authStore.js
│   │   │   └── catalogStore.js
│   │   ├── pages/
│   │   │   ├── Onboarding.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CatalogCreate.jsx
│   │   │   ├── CatalogPreview.jsx
│   │   │   ├── QualityCheck.jsx
│   │   │   ├── PriceCalculator.jsx
│   │   │   └── ExportPage.jsx
│   │   ├── components/
│   │   │   ├── ImageUploader.jsx
│   │   │   ├── QualityScorecard.jsx
│   │   │   ├── PnLBreakdown.jsx
│   │   │   ├── CatalogCard.jsx
│   │   │   └── Navbar.jsx
│   │   └── utils/
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── infra/
│   ├── terraform/                  # AWS infrastructure
│   │   ├── main.tf
│   │   ├── rds.tf
│   │   ├── s3.tf
│   │   ├── ec2.tf
│   │   └── cloudfront.tf
│   └── docker-compose.prod.yml
│
├── .env.example
├── Makefile
└── README.md
```

---

## 11. Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell
REDIS_URL=redis://localhost:6379/0

# AI
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# Storage
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=meesell-prod
AWS_REGION=ap-south-1
CLOUDFRONT_DOMAIN=d123.cloudfront.net

# Auth
MSG91_AUTH_KEY=...
MSG91_TEMPLATE_ID=...
JWT_SECRET=super-secret-key-change-this
JWT_EXPIRY_DAYS=7

# Payments
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_PLAN_STARTER=plan_...
RAZORPAY_PLAN_PRO=plan_...
RAZORPAY_PLAN_GROWTH=plan_...

# App
APP_ENV=production
CORS_ORIGINS=https://meesell.in,https://www.meesell.in
CELERY_BROKER_URL=redis://localhost:6379/1
```

---

## 12. Deployment (MVP)

```yaml
# docker-compose.prod.yml

services:
  api:
    build: ./backend
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - redis

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
    env_file: .env
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

# PostgreSQL on AWS RDS (not in Docker for production)
# S3 for file storage (not in Docker)
# CloudFront CDN in front of S3
```

**MVP Server:** Single AWS EC2 t3.small (2 vCPU, 2GB RAM) + RDS db.t3.micro  
**GPU for rembg:** g4dn.xlarge spot instance (on-demand, ~₹25/hour, used only during image processing bursts)  
**Estimated monthly cost:** ₹7,800

---

## 13. MVP Milestones (12 Weeks)

| Week | Deliverable |
|------|-------------|
| 1-2 | Project setup, DB schema, auth (OTP + JWT), basic CRUD for catalogs/SKUs |
| 3-4 | Image upload pipeline: S3 + rembg + resize + Celery workers |
| 5-6 | AI generation: Gemini integration, prompt engineering, category mapping |
| 7-8 | QualityGate: rules engine, validation endpoint, scorecard UI |
| 9-10 | PriceIntel calculator, Meesho CSV export, images ZIP export |
| 11 | Frontend polish: Dashboard, onboarding flow, mobile responsive |
| 12 | Testing, bug fixes, landing page, deploy to production |

---

*End of MVP Technical Specification — MeeSell v0.1*
