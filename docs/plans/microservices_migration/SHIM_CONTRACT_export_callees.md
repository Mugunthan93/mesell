# FROZEN HTTP-Shim Contract — `svc-export` callees

**Status:** `FROZEN 2026-06-12`
**Owner:** meesell-backend-coordinator (backend lead)
**Session:** `mesell-ms-export-backend-session-1` (Sub-Plan A, Phase C)
**Authority:** `spec_msA_backend.md` §0.4 + §5 · `SUB_PLAN_01_export_extraction.md` · `BACKEND_ARCHITECTURE.md §16.G`
**Consumed by:** Sub-Plans C (image), E (customer), F (category), H (catalog) — these sub-plans implement the `/internal/*` callee endpoints below EXACTLY as frozen here.

---

## 0. Why this document is FROZEN and program-level

`svc-export` is the FIRST extraction (§16.H order position 1). It is a pure **leaf consumer**: it calls 4 other modules but nothing calls it. During Sub-Plan A those 4 callees are STILL IN-PROCESS in the monolith, so the shims point at the **monolith ClusterIP** (`http://monolith-svc:8001`, the `MONOLITH_INTERNAL_BASE_URL` default — R4 hybrid posture).

When callees E/F/H/C later extract, each must expose the `/internal/*` endpoint its consumer already calls. **This document freezes that interface now** so the callee sub-plans implement a known target instead of inventing one. Any change to a contract row below requires a **founder-visible amendment** (the consumer shim is already shipped and tested against it).

**Scope correction (vs the original plan text):** the plan mis-named 2 shims. The authoritative list is **6 methods across 4 callees** — catalog (2) + category (2) + customer (1) + image (1). The plan's `image.get_image_bytes` and `category.fetch_xlsx_aliases` are WRONG: export calls `image.list_images` (consumes signed-URL refs, not raw bytes), and never calls `fetch_xlsx_aliases` (alias reversal is a SEED-time concern, not a runtime category call). See `spec_msA_backend.md §0.4`.

---

## 1. Transport contract (applies to ALL 6 endpoints)

Implemented in `backend/services/svc-export/app/core/extracted_clients/_transport.py`:

| Property | Value | Source |
|---|---|---|
| Client | `httpx.AsyncClient` | `_transport.py:95` |
| Timeout | **5 s read / 2 s connect** (`httpx.Timeout(timeout=5.0, connect=2.0)`) | `_transport.py:41` |
| Retry | **EXACTLY ONE**, ONLY on HTTP **503 / 504** (`_RETRYABLE_STATUSES`). NO retry on 500 or any 4xx. | `_transport.py:42,98-106` |
| Auth | Forward caller's user JWT in `Authorization: Bearer <token>` when present (API path); request correlation in `X-Request-ID`. Worker path forwards `X-Request-ID` only (internal-network trust on `/internal/*`). | `_transport.py:61-70` |
| Base URL | `MONOLITH_INTERNAL_BASE_URL` (default `http://monolith-svc:8001`), trailing-slash-trimmed | `_transport.py:73-75` |
| Error surface | Non-2xx final response → `httpx.raise_for_status()` → `httpx.HTTPStatusError`; each shim catches the **404** contract code and maps it to a typed exception (below); unexpected 5xx surfaces as a pipeline failure. | `_transport.py:108` |

The `/internal/*` routes are **NOT** exposed by Traefik (cluster-DNS only — infra handoff I4); there is no public ingress to them.

---

## 2. The 6 frozen endpoints

For each: the consumer call site (export `service.py`), the shim implementation (`extracted_clients/*`), the callee endpoint the future sub-plan must implement, and the source signature on the CALLEE side. Call-site line numbers are byte-for-byte preserved (§16.G); callee `def`-line numbers are quoted live as of 2026-06-12 and may drift with edits — match on **signature**, not line.

### 2.1 catalog-svc — `assert_product_ownership` (ownership gate)

| Facet | Value |
|---|---|
| Consumer call site | export `service.py:160` `await catalog_service.assert_product_ownership(product_id, user_id, db=db)` |
| Shim | `catalog_client.py:81` `assert_product_ownership(product_id: UUID, user_id: UUID, db: Any = None) -> None` |
| **Callee endpoint (FROZEN)** | `GET /internal/products/{product_id}/ownership-check?user_id={user_id}` |
| Path params | `product_id` (UUID, path) |
| Query params | `user_id` (UUID, query) |
| Callee source signature | catalog `service.py:921` `assert_product_ownership(product_id: UUID, user_id: UUID, db: AsyncSession) -> None` |
| Success response | `2xx` with any body (body ignored) → shim returns `None` |
| Error mapping | `404` → `catalog_client.ProductNotFoundError` (code `catalog.product_not_found`, `validation_message_id="catalog.product.not_found"`) — conflates not-found + cross-tenant per §4.C |

### 2.2 catalog-svc — `get_product_for_export` (export snapshot)

| Facet | Value |
|---|---|
| Consumer call sites | export `service.py:163` + `:300` `await catalog_service.get_product_for_export(product_id, user_id, db=db)` |
| Shim | `catalog_client.py:105` `get_product_for_export(product_id: UUID, user_id: UUID, db: Any = None) -> ExportSnapshotInternal` |
| **Callee endpoint (FROZEN)** | `GET /internal/products/{product_id}/export-snapshot?user_id={user_id}` |
| Path params | `product_id` (UUID, path) |
| Query params | `user_id` (UUID, query) |
| Callee source signature | catalog `service.py:945` `get_product_for_export(product_id: UUID, user_id: UUID, db: AsyncSession) -> ExportSnapshotInternal` |
| **Response JSON shape (FROZEN)** | `{ product_id: uuid, category_id: uuid, fields: object, ai_suggestions: object, image_refs: string[] (GCS object paths, NOT signed URLs), validation_summary: { status: string, product_id: uuid?, compulsory_filled: int?, compulsory_total: int?, optional_filled: int?, optional_total: int?, has_validation_errors: bool? } }` |
| Pipeline attribute reads | `snapshot.validation_summary.status`, `snapshot.category_id`, `snapshot.fields`, `snapshot.ai_suggestions`, `snapshot.image_refs` (mirror `catalog/domain.py` ExportSnapshotInternal) |
| Error mapping | `404` → `ProductNotFoundError` |

### 2.3 category-svc — `fetch_schema` (compiled wizard schema)

| Facet | Value |
|---|---|
| Consumer call sites | export `service.py:438` `await category_service.fetch_schema(category_id, db=db)` |
| Shim | `category_client.py:61` `fetch_schema(category_id: UUID, db: Any = None) -> dict` |
| **Callee endpoint (FROZEN)** | `GET /internal/categories/{category_id}/schema` |
| Path params | `category_id` (UUID, path) |
| Callee source signature | category `service.py:467` `fetch_schema(category_id: UUID, db: AsyncSession) -> dict` |
| **Response JSON shape (FROZEN)** | the §5A.B envelope dict (returned verbatim as `dict`) — keys include `fields[]`, `compliance_shape`, `main_sheet_label`, `total_count` (the export pipeline reads the field list + compliance_shape) |
| Error mapping | `404` → `category_client.CategoryNotFoundError` (code `category.not_found`) |
| Caching note | callee caches per `category_id` TTL 1 h; the shim does NOT add a client-side cache (the monolith is the cache authority during the strangler window) |

### 2.4 category-svc — `get_field_enum` (field-enum lookup)

| Facet | Value |
|---|---|
| Consumer call site | export `service.py:~645` `await category_service.get_field_enum(category_id, col.canonical_name, db)` (positional `db`) |
| Shim | `category_client.py:80` `get_field_enum(category_id: UUID, field_name: str, db: Any = None) -> dict[str, Any]` |
| **Callee endpoint (FROZEN)** | `GET /internal/categories/{category_id}/field-enum/{field_name}` |
| Path params | `category_id` (UUID, path), `field_name` (str, path) |
| Callee source signature | category `service.py:491` `get_field_enum(category_id: UUID, field_name: str, db: AsyncSession) -> dict[str, Any]` |
| **Response JSON shape (FROZEN)** | enum payload dict (single-flight on the callee for the 291 Brand-pattern enums per §9.D; the `meesho` canonicalisation value MAY be present — M10-compliant backend-internal lookup) |
| Error mapping | `404` → `category_client.FieldEnumNotFoundError` (code `category.field_enum_not_found`) — the callee uses ONE 404 for both "category not found" and "field has no enum"; the export pipeline catches both identically and passes the value through untranslated |

### 2.5 customer-svc — `get_compliance_block` (LM compliance fields)

| Facet | Value |
|---|---|
| Consumer call site | export `service.py:489` `await customer_service.get_compliance_block(user_id, db)` (positional `db`) |
| Shim | `customer_client.py:40` `get_compliance_block(user_id: UUID, db: Any = None) -> ComplianceBlock` |
| **Callee endpoint (FROZEN)** | `GET /internal/seller-profile/{user_id}/compliance-block` |
| Path params | `user_id` (UUID, path) |
| Callee source signature | customer `service.py:648` `get_compliance_block(user_id: UUID, db: AsyncSession) -> ComplianceBlock` |
| **Response JSON shape (FROZEN)** | `{ manufacturer_name, manufacturer_address, manufacturer_pincode, packer_name, packer_address, packer_pincode, importer_name?, importer_address?, importer_pincode?, country_of_origin }` — 9 standard LM fields + `country_of_origin`; the 3 `importer_*` fields are nullable (mirror `customer/domain.py` ComplianceBlock). Deserialised into the **vendored** `app.domain.ComplianceBlock` dataclass (the §16 domain-exchange-currency, vendored not HTTP per `spec_msA_backend §0.4`). |
| Error mapping | `404` → `customer_client.ProfileNotFoundError` (code `customer.profile_not_found`) |

### 2.6 image-svc — `list_images` (product image list, signed URLs)

| Facet | Value |
|---|---|
| Consumer call site | export `service.py:171` `await image_service.list_images(user_id=user_id, product_id=product_id, db=db)` (keyword args) |
| Shim | `image_client.py:56` `list_images(user_id: UUID, product_id: UUID, *, db: Any = None) -> ImagesListResponse` |
| **Callee endpoint (FROZEN)** | `GET /internal/products/{product_id}/images?user_id={user_id}` |
| Path params | `product_id` (UUID, path) |
| Query params | `user_id` (UUID, query) |
| Callee source signature | image `service.py:232` `list_images(user_id: UUID, product_id: UUID, *, db: AsyncSession) -> ImagesListResponse` |
| **Response JSON shape (FROZEN)** | `{ images: [ { image_id: uuid, idx: int, status: string, signed_url: string (1 h TTL), precheck_jsonb: object } ] }` — ordered by `idx` ASC, length 0–4. The export front-image gate reads `img.idx` + `img.status`. |
| Error mapping | a 404 / error propagates — the only export caller wraps this in the `xlsx_with_images` front-image gate, where a missing product surfaces as the broader pipeline failure (matches in-process behaviour) |

> **PLAN-TEXT CORRECTION (frozen):** this shim is `list_images`, NOT `get_image_bytes`. `get_image_bytes` exists in the monolith image service but export NEVER calls it. Sub-Plan C (image extraction) implements `/internal/products/{id}/images` per this row.

---

## 3. Amendment protocol

This contract is FROZEN. To change any row:

1. The proposing sub-plan opens a founder-visible amendment note (the consumer shim is already shipped + tested — see `backend/services/svc-export/tests/test_extracted_clients.py` and `test_export_extraction.py`).
2. Update the corresponding `extracted_clients/*` shim AND this doc in the SAME change.
3. Re-run the svc-export suite (the shim deserialization tests assert the REAL shape — a contract drift will go red).
4. The change flows through the standard group → integration → develop gates.

**The 4 sub-plans that implement these endpoints (C/E/F/H) MUST treat this doc as the spec.** Do not invent a `/internal/*` shape — copy the row.
