# MeeSell Postman Collection

Postman v2.1 collection covering all 30 operations (25 paths) of the MeeSell V1 API,
plus a reproducible regeneration script.

## Files

| File | Purpose |
|---|---|
| `meesell.postman_collection.json` | Postman v2.1 collection — 30 requests, 8 folders |
| `meesell.postman_environment.json` | Environment variables (`base_url`, `access_token`) |
| `openapi.json` | Raw OpenAPI 3.1 spec (generated from the FastAPI app — do not edit by hand) |

## Import

1. Open Postman.
2. Click **Import** (top-left).
3. Drop in both `meesell.postman_collection.json` and `meesell.postman_environment.json`.
4. Select **MeeSell Local Dev** as the active environment.

## Run the Login flow

1. Expand the **Auth > Login (dev)** folder.
2. Send **1 — OTP Send** with `{"phone": "+919876543210"}` (or your test phone).
3. Send **2 — OTP Verify (auto-sets token)** with `{"phone": "+919876543210", "otp": "000000"}`.
   - The test script on this request automatically sets `{{access_token}}` in the environment.
   - **Dev OTP bypass**: `otp=000000` works when the backend is running with `DEV_OTP_BYPASS_CODE=000000`.
4. All other requests inherit Bearer auth from the collection-level auth and are now runnable.

## Collection auth

- **Collection-level**: Bearer `{{access_token}}` — all requests inherit this by default.
- **Public endpoints** (OTP send/verify, health, Razorpay webhook) override to `auth: noauth`.
- If `{{access_token}}` is empty, protected requests return `401 Unauthorized`.

## Variables

| Variable | Default | Description |
|---|---|---|
| `base_url` | `http://localhost:8000` | Backend URL — change for staging/prod |
| `access_token` | _(empty)_ | Auto-populated by the OTP Verify test script |
| `product_id` | _(empty)_ | Set after creating a product via POST /products |
| `export_id` | _(empty)_ | Set after initiating an export via POST /products/{id}/export-xlsx |

## Folders

| Folder | Requests | Notes |
|---|---|---|
| Auth > Login (dev) | 2 | OTP send + verify with auto-token test script |
| Auth | 2 | Refresh, logout, me |
| Seller Profile | 5 | Onboarding wizard endpoints |
| Categories | 5 | Smart Picker, browse, tree, schema, field-enum |
| Products | 9 | CRUD + autofill + preview + draft recovery |
| Images | 2 | Multipart upload + list |
| Pricing | 1 | P&L calculator |
| Exports | 2 | Initiate + poll status |
| Webhooks | 1 | Razorpay webhook capture |
| Health | 1 | Connectivity check |

**Total: 30 requests across 25 paths.**

## Regeneration

The collection is generated from the FastAPI app's OpenAPI spec.
To regenerate after route or schema changes:

```bash
# From the project root (mesell/):
bash backend/scripts/gen_postman.sh
```

This does:
1. Dumps `backend/postman/openapi.json` from `app.main` in-process (no server needed).
2. Converts to a raw Postman collection via `npx openapi-to-postmanv2`.
3. Writes `backend/postman/meesell.postman_collection.json`.

**Requirements:**
- Node.js 18+ (for `npx`)
- Backend venv activated (`.venv` at `backend/.venv/`), OR `PYTHONPATH=backend python3`
- All 18 required env vars set, OR rely on the sentinel injection in `gen_openapi.py`

**Running server fallback:**
If the in-process import fails (e.g. venv missing), the script falls back to:
```bash
MEESELL_OPENAPI_URL=http://localhost:8000/openapi.json bash backend/scripts/gen_postman.sh
```

**Dump OpenAPI only (no Postman conversion):**
```bash
PYTHONPATH=backend python3 backend/scripts/gen_openapi.py --out backend/postman/openapi.json
```

**Note:** The auto-generated collection from `gen_postman.sh` is a starting point.
The hand-authored `meesell.postman_collection.json` in this directory has richer
example bodies, the OTP auto-token test script, proper auth overrides, and folder
descriptions. After regeneration, you may want to selectively merge improvements.

## Feature flags

Several endpoints return 404 when their feature flag is OFF (default on dev):

| Flag | Default | Affected endpoint(s) |
|---|---|---|
| `FEATURE_SMART_PICKER_ENABLED` | `true` | POST /categories/suggest |
| `FEATURE_AI_AUTOFILL_ENABLED` | `true` | POST /products/{id}/autofill |
| `FEATURE_IMAGE_PRECHECK_ENABLED` | `true` | POST + GET /products/{id}/images |
| `FEATURE_LIVE_PREVIEW_ENABLED` | **`false`** | GET /products/{id}/preview |
| `FEATURE_PRICE_CALCULATOR_ENABLED` | `true` | POST /products/{id}/price-calc |
| `FEATURE_XLSX_EXPORT_ENABLED` | `true` | POST /products/{id}/export-xlsx |
| `FEATURE_TRACKING_DASHBOARD_ENABLED` | `true` | GET /products |
| `FEATURE_CATALOG_FORM_ENABLED` | `true` | All POST/PATCH/DELETE /products routes |

Set the flag to `true` in `backend/.env` (or K3s ConfigMap) to enable.
