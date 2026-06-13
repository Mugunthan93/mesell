# FROZEN HTTP-Shim Contract — `svc-pricing` callees

**Status:** `FROZEN 2026-06-13`
**Owner:** meesell-backend-coordinator (backend lead)
**Session:** `mesell-ms-pricing-backend-session-1` (Sub-Plan D, Phase C — round 2)
**Authority:** `spec_msD_backend.md` §5 · `SUB_PLAN_0D_pricing_extraction.md` · `BACKEND_ARCHITECTURE.md §16.G` · `§0.6` ProductORM-elimination (founder-RULED Option B)
**Consumed by:** Sub-Plan F (`category` — implements the commission `/internal/*` endpoint) and Sub-Plan H (`catalog` — implements + WIDENS the ownership-check `/internal/*` endpoint). These sub-plans implement the callee endpoints below EXACTLY as frozen here.

> **This document is ADDITIVE to `SHIM_CONTRACT_export_callees.md`.** It does NOT rewrite any frozen export entry. svc-pricing is the FOURTH extraction (§16.H order position 4); it is a pure **leaf consumer** — it calls catalog + category, and NOTHING calls it (ZERO inbound `/internal/*`). During Sub-Plan D both callees are STILL IN-PROCESS in the monolith, so the shims point at the **monolith ClusterIP** (`http://monolith-svc:8001`, the `MONOLITH_INTERNAL_BASE_URL` default — R4 hybrid posture).

---

## 0. Why this document is FROZEN and program-level

When the callees (`category` at MS-3/F, `catalog` at MS-5/H) later extract, each must expose the `/internal/*` endpoint its pricing consumer already calls. **This document freezes that interface now** so the callee sub-plans implement a known target instead of inventing one. Any change to a contract row below requires a **founder-visible amendment** (the consumer shim is already shipped and tested against it — `tests/test_pricing_extraction.py` T3/T4, mocked `httpx.MockTransport`).

**The §0.6 novelty (NOT present in any earlier wave).** The pricing pipeline's monolith path did a direct `db.get(ProductORM, product_id)` to read `product.category_id` (a read of the catalog-owned `products` table). Under the founder-RULED **§0.6 Option B**, svc-pricing must NOT cross-schema-read `public.products`. The 3-statement ProductORM block collapses to ONE outbound shim call: `catalog_service.get_category_id(...)`. To serve it WITHOUT a second round-trip, the existing catalog `ownership-check` callee endpoint is **WIDENED** to additionally return `category_id` in its 200 body. That widening is **Sub-Plan H/catalog's obligation** (entry 1 below).

---

## 1. Transport contract (applies to BOTH endpoints)

Implemented in `backend/services/svc-pricing/app/core/extracted_clients/_transport.py`. Identical posture to the frozen export transport (`SHIM_CONTRACT_export_callees.md §1`):

| Property | Value |
|---|---|
| Client | `httpx.AsyncClient` |
| Timeout | **5 s read / 2 s connect** (`httpx.Timeout(timeout=5.0, connect=2.0)`) — proven by T3 `rec.timeouts[0].read == 5.0`, `.connect == 2.0` |
| Retry | **EXACTLY ONE**, ONLY on HTTP **503 / 504**. NO retry on 500 or any 4xx (T3/T4 assert `len(rec.requests) == 1` on 404) |
| Auth | Forward caller's user JWT in `Authorization: Bearer <token>` + request correlation in `X-Request-ID` (T3 asserts both forwarded verbatim) |
| Base URL | `MONOLITH_INTERNAL_BASE_URL` (default `http://monolith-svc:8001`), trailing-slash-trimmed |
| Error surface | Non-2xx final response → each shim catches the **404** contract code and maps it to a typed exception (below) |

The `/internal/*` routes are **NOT** exposed by Traefik (cluster-DNS only). pricing's own Traefik IngressRoute matches ONLY its single public route `PathRegexp(^/api/v1/products/[^/]+/price-calc$)`.

---

## 2. The 2 frozen endpoints

### 2.1 catalog-svc — `get_category_id` via the WIDENED ownership-check (the §0.6 replacement)

| Facet | Value |
|---|---|
| Consumer call site | pricing `service.py` `category_id = await catalog_service.get_category_id(product_id, user_id, db=db)` — the single statement that replaces the monolith's 3-statement ProductORM block (§0.6) |
| Shim | `catalog_client.py` `get_category_id(product_id: UUID, user_id: UUID, db: Any = None) -> UUID` |
| **Callee endpoint (FROZEN + WIDENED)** | `GET /internal/products/{id}/ownership-check?user_id={user_id}` |
| Path params | `id` (UUID, path) |
| Query params | `user_id` (UUID, query) |
| **Response JSON shape (WIDENED — Option B)** | The existing export-frozen ownership-check returned a body that pricing's ownership gate ignores. For pricing it is **WIDENED** to additionally carry `category_id`: `{ ..., "category_id": "<uuid>" }`. The shim deserialises `category_id` into a real `UUID` (T3 asserts `result == cid`, a genuine deserialisation, not mock identity). |
| Error mapping | `404` → `catalog_client.ProductNotFoundError` (conflates not-found + cross-tenant per §4.C) — NO retry (T3 proves single attempt) |
| **OBLIGATION — Sub-Plan H/catalog MUST honour** | When `catalog` extracts (MS-5/H), its `/internal/products/{id}/ownership-check` endpoint MUST include `category_id` in the 200 body. The export consumer reads only the ownership 2xx; the pricing consumer ADDITIONALLY reads `category_id`. The widening is ADDITIVE — it does not break the export contract (export ignores the extra key). |

> **Why widen instead of a 2nd endpoint:** §0.6 Option B forbids a cross-schema `products` read from `pricing_user` (I9 grant DELIBERATELY omitted — see `k8s/svc-pricing/schema-role.sql`). The category_id must therefore arrive over the SAME ownership round-trip pricing already makes (the ownership gate), not a separate DB read or a separate HTTP call. One round-trip, two facts (ownership + category_id).

### 2.2 category-svc — `get_commission` (Decimal-NEVER-null)

| Facet | Value |
|---|---|
| Consumer call site | pricing `service.py` `commission_pct = await category_service.get_commission(category_id, db=db)` — byte-for-byte preserved from the monolith (§16.G) |
| Shim | `category_client.py` `get_commission(category_id: UUID, db: Any = None) -> Decimal` |
| **Callee endpoint (FROZEN)** | `GET /internal/categories/{id}/commission` |
| Path params | `id` (UUID, path) |
| **Response JSON shape (FROZEN)** | `{ "commission_pct": "<decimal>" }` — a JSON **STRING** (Decimal-as-string, NEVER a float). The shim deserialises it into an exact `Decimal` with no float intermediary (T4 asserts `val == Decimal("15.00")` and `isinstance(val, Decimal)`). |
| **Decimal-NEVER-null contract** | `commission_pct` is **NEVER `null`**. An UNSEEDED category returns `"0.00"` (the missing-commission signal the pricing P&L treats deterministically), NOT `null` and NOT a 404 (T4 asserts `"0.00"` → `Decimal("0.00")`, `is not None`). |
| Error mapping | `404` → `category_client.CategoryNotFoundError` (T4 asserts the typed raise) |
| **OBLIGATION — Sub-Plan F/category MUST implement** | When `category` extracts (MS-3/F), its `/internal/categories/{id}/commission` endpoint MUST return `{"commission_pct": "<decimal>"}` as a STRING, NEVER null, with `"0.00"` for an unseeded category. A `null` or float emission would break the pricing P&L's frozen Decimal contract (a runtime correctness defect, not just a 4xx). |

---

## 3. Inbound surface: NONE

svc-pricing exposes **ZERO `/internal/*` routes**. It is a pure leaf consumer (price-calc is computed FROM the catalog + category lookups; nothing downstream reads pricing data over a shim in V1.5). Its only public route is `POST /api/v1/products/{id}/price-calc`. This is the §16.H position-4 leaf property — confirmed by the merge-gate route inventory (1 mounted POST, zero `/internal/*`).
