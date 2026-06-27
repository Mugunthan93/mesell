## MS-D Phase B — svc-pricing extraction (2026-06-13, branch feature/microservices-pricing/backend)

### Scope
Heavy lift for Sub-Plan D (pricing extraction, MS-3). Vendored service/repository/domain/exceptions byte-for-byte
from monolith `app/modules/pricing/`, built 2 outbound HTTP shims (catalog + category), resolved the §0.6
shared-ORM hazard, trimmed Settings, vendored 6-mw + core, standalone main.py (NO Celery). Worktree
`/tmp/mesell-wt/msD-backend/backend/services/svc-pricing/`. Phase A (schema-split 97c9dd63f587) was already done.

### §0.6 RESOLUTION = OPTION B (the contract item future sub-plans must honor)
Monolith service.calculate read `category_id` via `from app.shared.models.product import Product as ProductORM` +
`db.get(ProductORM, product_id)` (illegal cross-schema after extraction). RESOLVED by **widening the catalog
ownership shim** to ALSO return category_id, NOT by widening export-snapshot (Option A). New shim method
`catalog_client.get_category_id(product_id, user_id, db=db)` hits `GET /internal/products/{id}/ownership-check`
(the SAME endpoint as the ownership gate) and reads `{"category_id":"<uuid>"}` from the 200 body. The monolith's
`db.get(ProductORM)` + TOCTOU if-guard + `category_id = product.category_id` (3 statements) → ONE line. repository's
`products`-JOIN rewritten OUT (find_latest_by_product = bare product_id read; user-scoping upstream at ownership shim).
**Executable ProductORM/products refs = ZERO (AST-verified).** Merge gate greps for these — only docstring mentions
remain (they explain the elimination, same as dashboard/export precedent).

CONTRACT ITEMS emitted (callee sub-plans MUST implement):
- Sub-Plan H/catalog: WIDEN `GET /internal/products/{id}/ownership-check` (params: user_id) → 200
  `{"category_id":"<uuid>"}` on success; 404 (catalog.product.not_found) conflating not-found/cross-tenant/soft-deleted.
- Sub-Plan F/category: NEW `GET /internal/categories/{id}/commission` → 200 `{"commission_pct":"<decimal-string>"}`
  NEVER null (`"0.00"`=unseeded); 404 (category.lookup.not_found). (NEW vs MS-A SHIM_CONTRACT.)

### §16.G discipline — PROVEN
AST recursive-strip (imports + docstrings) diff of svc service.py vs monolith = a SINGLE block replacement (the §0.6
db.get elimination), 3 contiguous ast.dump hunks all part of that one block. The 3 protected cross-module call sites
are byte-for-byte: `await catalog_service.assert_product_ownership(product_id, user_id, db=db)` (×2, monolith :134/:241,
svc :151/:241) + `commission_pct = await category_service.get_commission(category_id, db=db)` (svc :165). _compute_pnl/
_q/_generate_alerts = verbatim; D2 golden mrp=157.96 confirmed. The 2 import rewires: catalog→catalog_client,
category→category_client (re-exported as catalog_service/category_service so call sites unchanged); plus the svc-tree
module flattening (app.modules.pricing.X → app.X: repository/domain/exceptions/schemas).

### Reusable extraction mechanics (held across SP01 export / MS-B dashboard / MS-D pricing)
- **svc-dashboard is the closest template for a NO-Celery service** (pricing copied its 7 middleware + core + shared
  shape). DELTA: pricing OWNS a table (pricing_calcs@pricing schema) so it KEEPS repository.py + shared/models/
  pricing_calc.py, and audit_mw FIRES (write POST) vs dashboard's read-only GET NO-OP. The 5 middleware
  (auth/tenancy/plan_guard/rate_limit/audit) are byte-identical to dashboard — `cp` them, then edit ONLY docstrings.
- **Owned-table ORM model in svc tree:** bind `{"schema":"<mod>"}` explicitly; DROP the SQLAlchemy `ForeignKey` +
  `relationship` to any catalog-owned table (Product) — keep the column as bare UUID; the DB-level cross-schema FK
  stays valid (dropped only at catalog extraction). This is the §0.6 elimination at the MODEL layer.
- **schemas.py + router.py are api-routes-builder's deliverables** — main.py mounts router import-tolerantly
  (try/except ImportError); service.py imports `from app.schemas import ...` so service.py won't import until
  schemas lands. To smoke-test service.py import + math, drop a THROWAWAY app/schemas.py stub, verify, then `rm` it
  (do NOT commit it). `import app.main` boots clean without schemas (router import-tolerant).
- **Shim transport (recipe §4) copied verbatim** from dashboard _transport.py — only the contextvar names change
  (svc_pricing_*). httpx.MockTransport patches `_transport.httpx.AsyncClient` to record requests + assert
  JWT+X-Request-ID forwarding + 503/504-only-retry.
- **check_scope_to_user allowlist** entry `app.modules.pricing.repository.insert_calc` carried as a doc note (svc
  lint context is Phase-C lead-owned).

### Validation run (real output)
ruff clean (app/). import-smoke `import app.main` OK (6 routes, 8 user_middleware). service.py rewire-identity +
D2 golden math PASS. Shim round-trip + 404-mapping + JWT-forward PASS. No-vendor grep = doc-only (EXPLICITLY-ABSENT
list + "no Celery"). Branch tip after push recorded in STATUS.

### Hand-offs
- api-routes-builder: router.py (1 route POST /products/{id}/price-calc 200, @rate_limit price_calc 600/3600 +
  @audit_event pricing.calculated, NO /internal/*) + schemas.py (9 bare Decimal fields verbatim, extra="forbid").
- infra/db: grant = INSERT ON public.audit_events TO pricing_user (audit FIRES); NO products SELECT (Option B=HTTP).
- LEAD Phase C: §16.G CI AST parity (single §0.6 hunk allowed); T1 Decimal byte-golden; T6 cross-schema audit
  round-trip; T3/T4 shim round-trips.

---
