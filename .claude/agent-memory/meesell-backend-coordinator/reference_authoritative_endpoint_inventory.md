# Reference — Authoritative Endpoint Inventory (post founder ruling 2026-06-05)

Founder ruling: §11.1's "16 + 4 = 20 endpoints" is stale (just like its "8 SQLAlchemy models" claim, where the truth is 13). Authoritative source = §3 + §7.7 + §11.6 = ~25 endpoints.

## §3.1 Auth (2)
- POST /api/v1/auth/otp/send
- POST /api/v1/auth/otp/verify

## §3.2 Seller profile (5)
- GET   /api/v1/seller-profile
- PATCH /api/v1/seller-profile
- PATCH /api/v1/seller-profile/active-categories
- PATCH /api/v1/seller-profile/compliance/{super_id}
- GET   /api/v1/seller-profile/required-fields

## §3.3 Categories & schema (5)
- GET /api/v1/categories/suggest?q=
- GET /api/v1/categories
- GET /api/v1/categories/{id}
- GET /api/v1/categories/{id}/schema
- GET /api/v1/categories/{id}/field-enum/{name}

## §3.4 Catalog & product (11)
- POST   /api/v1/products
- PATCH  /api/v1/products/{id}
- POST   /api/v1/products/{id}/autofill
- POST   /api/v1/products/{id}/images
- GET    /api/v1/products/{id}/images
- GET    /api/v1/products/{id}/preview
- POST   /api/v1/products/{id}/price-calc
- POST   /api/v1/products/{id}/export-xlsx
- GET    /api/v1/products
- DELETE /api/v1/products/{id}
- GET    /api/v1/exports/{id}

## §7.7 Manual browse (1)
- GET /api/v1/categories/browse?q=&super_id=&limit=&offset=

## §11.6 AI ops (implied async job poll — 1, unenumerated in §3)
- GET /api/v1/jobs/{job_id} (probable 25th endpoint; LangFuse tracing + autofill/image-precheck async polling)

**Total: 24 enumerated + 1 implied = 25** matches founder count.
