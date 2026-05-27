# TICKETS.md — MeeSell MVP Sprint Plan

> Each ticket is designed for a Claude Code agent to execute independently.
> Read the full ticket before starting. Check dependencies. One ticket per session.

---

## Sprint 1: Foundation (Week 1–2)

### T01: Project Setup & Config
**Priority:** P0 | **Depends on:** None | **Estimate:** 1 session

**Goal:** Set up FastAPI project with configuration, health endpoint, and dev environment.

**Tasks:**
- Create `backend/app/main.py` — FastAPI app with CORS middleware, lifespan handler
- Create `backend/app/config.py` — Pydantic Settings loading from env vars (DATABASE_URL, VALKEY_URL, GEMINI_API_KEY, GCS_BUCKET, MSG91_AUTH_KEY, JWT_SECRET, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, APP_ENV, CORS_ORIGINS)
- Create `backend/requirements.txt` with pinned versions: fastapi, uvicorn, gunicorn, sqlalchemy[asyncio], asyncpg, redis, celery, pydantic-settings, pyjwt, python-multipart, pillow, rembg, google-cloud-storage, google-generativeai, httpx, python-dotenv, alembic, pytest, pytest-asyncio, httpx
- Create `backend/Dockerfile` — Python 3.12-slim, install deps, copy app, run uvicorn
- Create `backend/.env.example` — all env vars with placeholder values
- Create `docker-compose.dev.yml` — api, valkey (valkey/valkey:8-alpine), postgres (postgres:16-alpine) services with volume mounts for hot reload
- Create `Makefile` with targets: dev, test, lint, migrate, build, deploy
- Create `.gitignore` — Python + Node + env + pycache + node_modules + .venv
- Health endpoint: `GET /health` returns `{"status": "healthy", "checks": {"postgres": "ok", "valkey": "ok"}}`

**Acceptance Criteria:**
- [ ] `docker-compose up` starts all 3 services without errors
- [ ] `curl localhost:8000/health` returns 200 with postgres + valkey status
- [ ] All env vars loaded from .env file via Pydantic Settings
- [ ] Hot reload works (change code → auto restart)

---

### T02: Database Models & Migrations
**Priority:** P0 | **Depends on:** T01 | **Estimate:** 1 session

**Goal:** Create all SQLAlchemy models and initial Alembic migration.

**Tasks:**
- Create `backend/app/database.py` — async engine, async sessionmaker, get_db dependency
- Create `backend/app/models/__init__.py` — import all models
- Create `backend/app/models/user.py` — User model (id UUID PK, phone UNIQUE, name, email, plan, plan_expires_at, razorpay_sub_id, catalogs_used INT, catalogs_limit INT, created_at, updated_at)
- Create `backend/app/models/catalog.py` — Catalog model (id UUID PK, user_id FK, name, status, category, subcategory, quality_score, created_at, updated_at)
- Create `backend/app/models/sku.py` — SKU model (id UUID PK, catalog_id FK, product_name, cost_price DECIMAL, selling_price DECIMAL, weight_grams INT, material, sizes, colors, ai_title TEXT, ai_description TEXT, ai_keywords TEXT, ai_category, ai_attributes JSONB, margin_amount, margin_percent, shipping_cost, return_provision, quality_checks JSONB, quality_score INT, sort_order, created_at)
- Create `backend/app/models/image.py` — Image model (id UUID PK, sku_id FK, original_url TEXT, processed_url TEXT, bg_removed BOOL, resized BOOL, width INT, height INT, file_size_kb INT, format VARCHAR, has_watermark BOOL, is_compliant BOOL, compliance_note TEXT, sort_order, created_at)
- Create `backend/app/models/export.py` — Export model (id UUID PK, user_id FK, catalog_id FK, export_type VARCHAR, file_url TEXT, created_at)
- Set up Alembic: `alembic init alembic`, configure alembic.ini and env.py for async
- Generate and run initial migration

**Acceptance Criteria:**
- [ ] `make migrate` creates all 5 tables in PostgreSQL
- [ ] All foreign keys and indexes present
- [ ] JSONB columns work (ai_attributes, quality_checks)
- [ ] UUID primary keys auto-generate
- [ ] TIMESTAMPTZ columns default to NOW()

---

### T03: Auth — OTP + JWT
**Priority:** P0 | **Depends on:** T02 | **Estimate:** 1 session

**Goal:** Phone OTP login with JWT token issuance.

**Tasks:**
- Create `backend/app/services/otp_service.py`:
  - `send_otp(phone)` — generate 4-digit OTP, store in Valkey (`otp:{phone}`, TTL 300s), call MSG91 API
  - `verify_otp(phone, code)` — check Valkey, max 3 attempts, delete on success
  - For dev mode: if `APP_ENV=development`, accept OTP "1234" always (skip MSG91)
- Create `backend/app/middleware/auth.py`:
  - `create_token(user_id, plan)` — JWT with HS256, 7-day expiry, payload: {user_id, plan, exp}
  - `get_current_user(token)` — FastAPI Depends, decode JWT, fetch user from DB, raise 401 if invalid
  - `get_optional_user(token)` — same but returns None instead of raising (for public endpoints)
- Create `backend/app/schemas/auth.py`:
  - `SendOTPRequest(phone: str)` — validate Indian phone format (+91XXXXXXXXXX)
  - `VerifyOTPRequest(phone: str, otp: str)`
  - `AuthResponse(token: str, user: UserResponse)`
  - `UserResponse(id, phone, name, plan, catalogs_used, catalogs_limit)`
- Create `backend/app/routers/auth.py`:
  - `POST /api/v1/auth/send-otp` — send OTP
  - `POST /api/v1/auth/verify-otp` — verify, create user if new (plan=free), issue JWT
  - `GET /api/v1/auth/me` — return current user (requires auth)

**Acceptance Criteria:**
- [ ] Send OTP stores code in Valkey with 300s TTL
- [ ] Verify OTP with correct code returns JWT token
- [ ] Verify OTP with wrong code returns 401 (max 3 attempts)
- [ ] JWT token decodes correctly and loads user from DB
- [ ] New phone number auto-creates user with plan=free
- [ ] Dev mode accepts "1234" as valid OTP for any phone
- [ ] `GET /me` with valid token returns user profile

---

### T04: GCS Storage Service
**Priority:** P0 | **Depends on:** T01 | **Estimate:** 1 session

**Goal:** Google Cloud Storage service for uploading, downloading, and generating signed URLs.

**Tasks:**
- Create `backend/app/services/storage.py`:
  - `GCSStorage` class initialized with GCS client + bucket from config
  - `upload(file_bytes, path, content_type)` → returns public URL
  - `get_signed_url(path, expiry_minutes=60)` → returns signed download URL
  - `delete(path)` → deletes object
  - `upload_from_file(file_path, gcs_path)` → upload local file
- GCS path structure:
  - `originals/{user_id}/{image_id}.jpg`
  - `processed/{user_id}/{image_id}.jpg`
  - `exports/{user_id}/{catalog_id}.csv`
  - `exports/{user_id}/{catalog_id}_images.zip`
- For dev mode: if `APP_ENV=development`, use local filesystem (`/tmp/meesell/`) instead of GCS with same interface

**Acceptance Criteria:**
- [ ] Upload returns accessible URL
- [ ] Signed URLs expire correctly
- [ ] Delete removes object
- [ ] Dev mode uses local filesystem with same API
- [ ] Content-type set correctly for jpg/png/csv/zip

---

## Sprint 2: Image Pipeline (Week 3–4)

### T05: Image Upload Endpoint
**Priority:** P0 | **Depends on:** T02, T03, T04 | **Estimate:** 1 session

**Goal:** Upload product images to a SKU, store originals in GCS.

**Tasks:**
- Create `backend/app/schemas/image.py` — ImageResponse, ImageStatusResponse
- Create `backend/app/routers/images.py`:
  - `POST /api/v1/skus/{sku_id}/images` — multipart file upload
    - Validate: file is JPG/PNG, max 10MB, user owns the SKU
    - Save original to GCS: `originals/{user_id}/{image_id}.{ext}`
    - Create Image record in DB (original_url set, processed_url null)
    - Queue Celery task for background processing
    - Return ImageResponse with status "processing"
  - `GET /api/v1/images/{image_id}/status` — check processing status
  - `DELETE /api/v1/images/{image_id}` — delete image from DB + GCS

**Acceptance Criteria:**
- [ ] Upload accepts JPG/PNG up to 10MB
- [ ] Rejects non-image files with 400 error
- [ ] Original saved to GCS with correct path
- [ ] Image record created in DB
- [ ] Celery task queued (can verify in Valkey)
- [ ] Status endpoint returns processing/completed

---

### T06: Image Processing Worker (rembg + resize)
**Priority:** P0 | **Depends on:** T05 | **Estimate:** 1 session

**Goal:** Celery worker that removes background, adds white BG, resizes to 1024×1024.

**Tasks:**
- Create `backend/app/workers/celery_app.py` — Celery app with Valkey broker/backend, task routes
- Create `backend/app/services/image_processor.py`:
  - `remove_background(image_bytes)` → returns RGBA image with transparent BG (using rembg)
  - `add_white_background(rgba_image)` → returns RGB image with white BG
  - `resize_and_pad(image, target=(1024,1024))` → center-crop + white padding to exact size
  - `compress_jpeg(image, quality=90, max_kb=500)` → optimize file size
  - `detect_watermark(image)` → basic edge detection + text presence (returns bool)
- Create `backend/app/workers/image_tasks.py`:
  - `process_image(image_id)` Celery task:
    1. Download original from GCS
    2. Run rembg (remove background)
    3. Add white background
    4. Resize to 1024×1024
    5. Compress JPEG
    6. Upload processed to GCS: `processed/{user_id}/{image_id}.jpg`
    7. Run watermark detection
    8. Update Image record: processed_url, bg_removed=True, resized=True, width=1024, height=1024, is_compliant, has_watermark

**Acceptance Criteria:**
- [ ] Celery worker starts and connects to Valkey broker
- [ ] rembg removes background correctly (test with sample product photo)
- [ ] Output is 1024×1024 JPEG with white background
- [ ] Processed image uploaded to GCS
- [ ] Image DB record updated with processing results
- [ ] Watermark detection returns True for watermarked images
- [ ] Processing completes in < 10 seconds on CPU

---

## Sprint 3: AI Generation (Week 5–6)

### T07: Catalog & SKU CRUD
**Priority:** P0 | **Depends on:** T02, T03 | **Estimate:** 1 session

**Goal:** Full CRUD endpoints for catalogs and SKUs.

**Tasks:**
- Create `backend/app/schemas/catalog.py` — CatalogCreate, CatalogUpdate, CatalogResponse, CatalogListResponse (with pagination)
- Create `backend/app/schemas/sku.py` — SKUCreate, SKUUpdate, SKUResponse
- Create `backend/app/routers/catalogs.py`:
  - `POST /api/v1/catalogs` — create catalog (name required)
  - `GET /api/v1/catalogs` — list user's catalogs (paginated, filter by status)
  - `GET /api/v1/catalogs/{id}` — get catalog with SKUs and images
  - `PUT /api/v1/catalogs/{id}` — update catalog name/category
  - `DELETE /api/v1/catalogs/{id}` — soft delete
- Create `backend/app/routers/skus.py`:
  - `POST /api/v1/catalogs/{catalog_id}/skus` — add SKU
  - `PUT /api/v1/skus/{sku_id}` — update SKU (seller edits AI output)
  - `DELETE /api/v1/skus/{sku_id}` — remove SKU

**Acceptance Criteria:**
- [ ] Create catalog returns 201 with catalog data
- [ ] List catalogs supports `?status=draft&page=1&limit=20`
- [ ] Get catalog includes nested SKUs and their images
- [ ] Only catalog owner can access their catalogs (403 for others)
- [ ] Delete is soft delete (status → "deleted")

---

### T08: Gemini AI Text Generation
**Priority:** P0 | **Depends on:** T07 | **Estimate:** 1 session

**Goal:** Generate SEO-optimized titles, descriptions, keywords, and attributes using Gemini.

**Tasks:**
- Create `backend/app/services/ai_engine.py`:
  - `GeminiEngine` class with google.generativeai client
  - `generate_listing(product_name, category, material, sizes, colors, price, image_description=None)` → returns dict with title, description, keywords, category, attributes
  - Prompt template in `backend/app/data/prompts/catalog_generation.txt` (see tech spec for full prompt)
  - Response parsing: expect JSON, handle malformed responses gracefully
  - Category-specific prompt variations (fashion vs electronics vs home)
- Create `backend/app/workers/generation_tasks.py`:
  - `generate_catalog(catalog_id)` Celery task:
    1. Load all SKUs for catalog
    2. For each SKU: call Gemini API with product details
    3. Parse response → update SKU fields (ai_title, ai_description, ai_keywords, ai_category, ai_attributes)
    4. Auto-trigger QualityGate validation
    5. Update catalog status to "generated"
    6. Increment user.catalogs_used
- Create `backend/app/routers/generation.py` (or add to catalogs.py):
  - `POST /api/v1/catalogs/{id}/generate` — check plan limits, queue Celery job, return job_id
  - `GET /api/v1/jobs/{job_id}` — check job status (stored in Valkey)
  - `POST /api/v1/skus/{id}/regenerate` — regenerate single SKU with new prompt variation

**Acceptance Criteria:**
- [ ] Gemini API call succeeds and returns structured JSON
- [ ] AI title is under 200 chars, SEO-optimized, Meesho-formatted
- [ ] AI description is 200-500 chars
- [ ] Attributes parsed correctly into JSONB
- [ ] Category mapped to valid Meesho taxonomy
- [ ] Plan limits enforced (free=5/mo, starter=50, etc.)
- [ ] Job status trackable via GET /jobs/{id}
- [ ] Regenerate produces different output (prompt variation)

---

### T09: Meesho Category Data
**Priority:** P1 | **Depends on:** T08 | **Estimate:** 1 session

**Goal:** Build the Meesho category taxonomy, required attributes per category, and banned words list.

**Tasks:**
- Create `backend/app/data/meesho_categories.json` — full Meesho category tree (Women > Ethnic Wear > Kurtis, etc.). Research and include top 50 categories.
- Create `backend/app/data/category_attributes.json` — required and optional attributes per category (e.g., kurtis: fabric REQUIRED, fit REQUIRED, wash_care OPTIONAL, etc.)
- Create `backend/app/data/banned_words.json` — words that cause Meesho rejection (branded names, misleading health claims, etc.)
- Create `backend/app/data/meesho_shipping_slabs.json` — weight slab pricing by zone
- Create utility function `get_category_config(category_name)` that returns required attrs, optional attrs, and validation rules for that category

**Acceptance Criteria:**
- [ ] 50+ Meesho categories mapped with parent hierarchy
- [ ] Each category has required_attributes and optional_attributes lists
- [ ] Banned words list has 100+ entries
- [ ] Shipping slab data matches Meesho's current rates
- [ ] Utility function returns correct config for any mapped category

---

## Sprint 4: QualityGate + Pricing (Week 7–8)

### T10: QualityGate Rules Engine
**Priority:** P0 | **Depends on:** T06, T08 | **Estimate:** 1 session

**Goal:** Pre-upload validation engine with 9 rules and weighted scoring.

**Tasks:**
- Create `backend/app/services/quality_engine.py`:
  - `QualityEngine` class with 9 rules (see tech spec section 5.3)
  - Each rule: check function, weight (5-15), severity (fail/warn), fix suggestion
  - Rules: image_size, white_bg, watermark, title_length, title_keywords, required_attributes, banned_words, duplicate_check, category_mapping
  - `validate_catalog(catalog_id)` → runs all checks, returns overall score + per-check results
  - Score calculation: sum of passed weights / total weight × 100
  - Pass condition: score >= 70 AND no fail-severity checks failed
- Create `backend/app/schemas/quality.py` — QualityCheckResult, QualityReport
- Create `backend/app/routers/quality.py`:
  - `POST /api/v1/catalogs/{id}/validate` — run validation, return report

**Acceptance Criteria:**
- [ ] All 9 rules execute correctly
- [ ] Score calculation is accurate
- [ ] Fail-severity rule failures block "pass" status regardless of score
- [ ] Fix suggestions are specific and actionable
- [ ] Duplicate check queries user's existing catalogs
- [ ] Banned words check covers title + description

---

### T11: PriceIntel Calculator
**Priority:** P0 | **Depends on:** T09 | **Estimate:** 1 session

**Goal:** Meesho-specific P&L calculator with weight slab optimization and alerts.

**Tasks:**
- Create `backend/app/services/pricing_engine.py`:
  - `calculate_pnl(selling_price, cost_price, weight_grams, category, return_rate=None, ad_spend=0, packaging=12)` → full P&L breakdown
  - Load shipping slabs from meesho_shipping_slabs.json
  - Load default return rates from category data
  - Calculate: commission (0%), shipping by zone, shipping GST (18%), payment processing (2%), return provision
  - Generate alerts: weight_slab_warning, low_margin, competitor_context
- Create `backend/app/schemas/pricing.py` — PricingRequest, PricingResponse, PricingAlert
- Create `backend/app/routers/pricing.py`:
  - `POST /api/v1/pricing/calculate` — PUBLIC endpoint (no auth required, this is the lead magnet)
  - Authenticated users get enhanced response (return_rate from their data)

**Acceptance Criteria:**
- [ ] P&L calculation matches manual verification
- [ ] Weight slab correctly selected based on weight_grams
- [ ] Return provision calculated using category default rate
- [ ] Weight warning alert fires when within 150g of next slab
- [ ] Low margin alert fires when margin < 15%
- [ ] Endpoint works without authentication (public)
- [ ] Authenticated users get richer response

---

## Sprint 5: Export + Frontend (Week 9–10)

### T12: Meesho CSV + ZIP Export
**Priority:** P0 | **Depends on:** T07, T08 | **Estimate:** 1 session

**Goal:** Generate downloadable Meesho bulk upload CSV and processed images ZIP.

**Tasks:**
- Create `backend/app/services/export_service.py`:
  - `generate_meesho_csv(catalog_id)` → creates CSV matching Meesho's bulk upload template (columns: catalog_name, product_title, product_description, category, sub_category, mrp, selling_price, gst_percentage, hsn_code, size, color, brand, material, country_of_origin, manufacturer_name, image_1..image_4, weight_grams, etc.)
  - `generate_images_zip(catalog_id)` → downloads all processed images from GCS, creates ZIP with naming: `{product_name}_1.jpg`, `{product_name}_2.jpg`
  - Upload generated files to GCS exports/ path
  - Create Export record in DB
- Create `backend/app/routers/exports.py`:
  - `POST /api/v1/catalogs/{id}/export/meesho-csv` → generate and return signed download URL (1hr expiry)
  - `POST /api/v1/catalogs/{id}/export/images-zip` → generate and return signed download URL

**Acceptance Criteria:**
- [ ] CSV columns match Meesho's exact template format
- [ ] CSV opens correctly in Excel without encoding issues (UTF-8 BOM)
- [ ] ZIP contains all processed images named correctly
- [ ] Download URLs are signed with 1-hour expiry
- [ ] Export record saved to DB for history tracking

---

### T13: Frontend — Project Setup + Auth
**Priority:** P0 | **Depends on:** T03 | **Estimate:** 1 session

**Goal:** React + Vite + Tailwind project with auth flow (OTP login).

**Tasks:**
- Initialize Vite React project in `frontend/`
- Install and configure: tailwindcss, postcss, autoprefixer, zustand, axios, react-router-dom
- Create `frontend/src/api/client.js` — Axios instance with baseURL, JWT interceptor (read token from Zustand/localStorage, attach to Authorization header, handle 401 by redirecting to login)
- Create `frontend/src/stores/authStore.js` — Zustand store: user, token, login(), logout(), isAuthenticated
- Create `frontend/src/pages/Onboarding.jsx` — 3-step flow: phone input → OTP input → welcome + first upload CTA
- Create `frontend/src/App.jsx` — React Router with routes: / (onboarding), /dashboard, /catalog/new, /catalog/:id, /quality/:id, /pricing, /export/:id
- Create `frontend/src/components/Navbar.jsx` — top nav with logo, plan badge, logout
- PWA manifest in `public/manifest.json`

**Acceptance Criteria:**
- [ ] `npm run dev` starts Vite dev server on :5173
- [ ] Tailwind utility classes work
- [ ] OTP login flow works end-to-end (send → verify → redirect to dashboard)
- [ ] JWT stored in Zustand, attached to all API requests
- [ ] 401 response redirects to login
- [ ] Mobile responsive (viewport meta, mobile nav)

---

### T14: Frontend — Dashboard + Catalog Create
**Priority:** P0 | **Depends on:** T13 | **Estimate:** 1 session

**Goal:** Dashboard home screen and catalog creation flow (upload → generate → preview).

**Tasks:**
- Create `frontend/src/pages/Dashboard.jsx`:
  - Stats row: catalogs count, avg margin, return rate, estimated revenue
  - Quick action buttons: Create Catalog, Check Quality, Price Calculator
  - Recent catalogs list with status badge and quality score
- Create `frontend/src/pages/CatalogCreate.jsx`:
  - Step 1: Upload product photos (drag-drop, max 9 images)
  - Step 2: Enter product details form (name, material, sizes, colors, price, category)
  - Step 3: Click "Generate with AI" → show processing animation
  - Step 4: Preview generated content (side-by-side: images + AI text)
  - Edit inline: click title/description to edit, regenerate button
  - Approve → navigate to export
- Create `frontend/src/components/ImageUploader.jsx` — drag-drop + file picker, preview thumbnails, remove button
- Create `frontend/src/stores/catalogStore.js` — Zustand store for current catalog state

**Acceptance Criteria:**
- [ ] Dashboard loads catalogs from API and displays correctly
- [ ] Image uploader supports drag-drop and file selection
- [ ] Upload shows progress indicator
- [ ] AI generation shows real-time progress (polling job status)
- [ ] Preview shows processed images + generated text side by side
- [ ] Inline edit allows changing AI-generated title/description
- [ ] All states handle loading and error correctly

---

### T15: Frontend — QualityGate + Pricing + Export
**Priority:** P0 | **Depends on:** T14 | **Estimate:** 1 session

**Goal:** QualityGate scorecard, pricing calculator, and export download pages.

**Tasks:**
- Create `frontend/src/pages/QualityCheck.jsx`:
  - Overall score circle (0-100 with color: green >80, yellow >60, red <60)
  - 8 check items with pass/warn/fail icon + detail text
  - "Fix Warnings" button and "Export" button
- Create `frontend/src/components/QualityScorecard.jsx` — reusable scorecard component
- Create `frontend/src/pages/PriceCalculator.jsx`:
  - Input form: selling price, cost price, weight, category dropdown
  - P&L breakdown table (each line item with amount)
  - Net profit highlighted (green if positive)
  - Alerts section (weight warning, low margin)
  - This page works without login (public lead magnet)
- Create `frontend/src/components/PnLBreakdown.jsx` — reusable P&L table component
- Create `frontend/src/pages/ExportPage.jsx`:
  - Two download cards: Meesho CSV + Images ZIP
  - Download buttons that trigger export API and download file
  - Instructions section: "How to upload to Meesho Supplier Panel"

**Acceptance Criteria:**
- [ ] Quality scorecard displays all checks correctly
- [ ] Score circle animates and uses correct color
- [ ] Pricing calculator works without authentication
- [ ] P&L breakdown adds up correctly (visual verification)
- [ ] Export triggers download of actual CSV/ZIP files
- [ ] All pages are mobile responsive

---

## Sprint 6: Polish & Deploy (Week 11–12)

### T16: Rate Limiting & Plan Guards
**Priority:** P1 | **Depends on:** T03 | **Estimate:** 1 session

**Goal:** Enforce plan limits and rate limiting via Valkey.

**Tasks:**
- Create `backend/app/middleware/rate_limit.py`:
  - Sliding window rate limiter using Valkey
  - Per-endpoint limits: /generate (5/min, 50/day), /images (20/min, 200/day), /pricing (30/min, 500/day)
  - Return 429 Too Many Requests with Retry-After header
- Create `backend/app/middleware/plan_guard.py`:
  - Check plan limits: catalogs_used vs catalogs_limit
  - Check daily quality check limits for free plan
  - Return 403 with upgrade message when limit reached
  - Reset catalogs_used monthly (on billing cycle or 1st of month for free users)

**Acceptance Criteria:**
- [ ] Rate limits enforced correctly per user per endpoint
- [ ] 429 response includes Retry-After header
- [ ] Plan limits block generation when exceeded
- [ ] 403 response includes "upgrade to Pro" message
- [ ] Free plan: 5 catalogs/month, 3 QC checks/day enforced

---

### T17: K8s Manifests & Deployment
**Priority:** P1 | **Depends on:** All backend tickets | **Estimate:** 1 session

**Goal:** Production K8s manifests and deployment script.

**Tasks:**
- Create all K8s YAML files in `k8s/` directory (see infra spec for full manifests):
  - namespace.yaml, secrets.yaml.example, config.yaml
  - postgres.yaml (deployment + PVC + service)
  - valkey.yaml (deployment + PVC + service)
  - api.yaml (deployment 2 replicas + service)
  - worker.yaml (deployment 2 replicas)
  - frontend.yaml (deployment 1 replica + service)
  - ingress.yaml (Traefik with TLS)
  - backup-cronjob.yaml (daily pg_dump to GCS)
- Create `scripts/setup-vm.sh` — full VM setup script (install K3s, cert-manager, apply manifests)
- Create `frontend/Dockerfile` — build React app, serve with nginx
- Update `Makefile` with deploy target (build → push to Artifact Registry → kubectl rolling update)

**Acceptance Criteria:**
- [ ] All manifests are valid YAML (kubectl apply --dry-run)
- [ ] Resource requests/limits fit within 8GB RAM budget
- [ ] PVCs configured for postgres (20Gi) and valkey (2Gi)
- [ ] Ingress routes meesell.in → frontend, api.meesell.in → api
- [ ] Backup CronJob configured for 2 AM IST daily
- [ ] Setup script works on fresh Ubuntu 24.04 VM

---

### T18: Frontend Polish & Landing Page
**Priority:** P1 | **Depends on:** T14, T15 | **Estimate:** 1 session

**Goal:** UI polish, error handling, loading states, and public landing page.

**Tasks:**
- Add loading skeletons to all pages (Dashboard, Catalog, Quality, Export)
- Add error boundaries with retry buttons
- Add toast notifications for success/error actions
- Create landing page at `/` (for non-authenticated users):
  - Hero section: "Create Meesho catalogs in 30 seconds with AI"
  - Features section: CatalogAI, QualityGate, PriceIntel highlights
  - Pricing section: 4 tier cards (Free/Starter/Pro/Growth)
  - CTA: "Start Free" → onboarding
  - Public profit calculator link
- Mobile responsive pass on all pages
- PWA: service worker, offline page, app icon

**Acceptance Criteria:**
- [ ] All async operations show loading state
- [ ] Errors show user-friendly messages with retry option
- [ ] Toast notifications for: catalog created, export ready, OTP sent
- [ ] Landing page looks professional and is mobile responsive
- [ ] Pricing cards display correctly
- [ ] PWA installable on mobile Chrome

---

### T19: Testing & Bug Fixes
**Priority:** P1 | **Depends on:** All tickets | **Estimate:** 1 session

**Goal:** Integration tests for critical flows and bug fixes.

**Tasks:**
- Create `backend/tests/conftest.py` — test DB setup, test client, auth fixtures
- Create `backend/tests/test_auth.py` — OTP send, verify, JWT validation, protected routes
- Create `backend/tests/test_catalog.py` — CRUD, pagination, ownership guard
- Create `backend/tests/test_quality.py` — all 9 rules, score calculation, pass/fail logic
- Create `backend/tests/test_pricing.py` — P&L calculation, weight slab selection, alerts
- Fix any bugs found during testing
- Verify full end-to-end flow: signup → upload → generate → validate → export

**Acceptance Criteria:**
- [ ] All tests pass with `make test`
- [ ] Auth flow tested: send OTP → verify → get token → access protected route
- [ ] Catalog CRUD tested: create → add SKU → update → delete
- [ ] Quality rules each tested individually
- [ ] Pricing calculations verified against manual spreadsheet
- [ ] E2E flow works without errors

---

## Ticket Tracking

| Ticket | Sprint | Status | Depends On |
|--------|--------|--------|------------|
| T01 | 1 | ⬜ TODO | — |
| T02 | 1 | ⬜ TODO | T01 |
| T03 | 1 | ⬜ TODO | T02 |
| T04 | 1 | ⬜ TODO | T01 |
| T05 | 2 | ⬜ TODO | T02, T03, T04 |
| T06 | 2 | ⬜ TODO | T05 |
| T07 | 3 | ⬜ TODO | T02, T03 |
| T08 | 3 | ⬜ TODO | T07 |
| T09 | 3 | ⬜ TODO | T08 |
| T10 | 4 | ⬜ TODO | T06, T08 |
| T11 | 4 | ⬜ TODO | T09 |
| T12 | 5 | ⬜ TODO | T07, T08 |
| T13 | 5 | ⬜ TODO | T03 |
| T14 | 5 | ⬜ TODO | T13 |
| T15 | 5 | ⬜ TODO | T14 |
| T16 | 6 | ⬜ TODO | T03 |
| T17 | 6 | ⬜ TODO | All backend |
| T18 | 6 | ⬜ TODO | T14, T15 |
| T19 | 6 | ⬜ TODO | All |
