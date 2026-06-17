# Hybrid-Mode CI Configuration — `svc-catalog` extraction window (THE SPINE, LAST wave)

**Status:** ACTIVE for the Sub-Plan H strangler window (2026-06-14 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `spec_msH_backend.md` (hybrid posture) + `SUB_PLAN_0H_catalog_extraction.md` §Hybrid-mode CI note + `CI_HYBRID_MODE_pricing.md` / `CI_HYBRID_MODE_dashboard.md` (the equivalents this mirrors)

---

## 0. The question this answers

> Which services must be docker-composed for `svc-catalog`'s HTTP-mode CI?

**Answer for unit/contract CI: NONE — all shims mocked.** But catalog is the
**FIRST and ONLY extraction with BOTH directions of HTTP traffic live in
production** — it is BOTH a heavy CALLEE (4 callers dial its `/internal/*`) AND a
multi-callee CALLER (5 outbound shims → category-svc + customer-svc). For unit
CI this duality is collapsed to `httpx.MockTransport` on both sides; the live
both-directions wiring is exercised only in the in-cluster integration soak.

- **Unit / contract CI for svc-catalog needs ZERO live services.** The 5 outbound
  shims (category ×3, customer ×2) are mocked with `httpx.MockTransport`; the 4
  inbound `/internal/*` shapes are asserted at the response-MODEL level against
  the MERGED consumers (svc-pricing / svc-export / svc-dashboard) — no live
  caller pod required.
- **There IS a PG-gated cross-schema round-trip** (`test_cross_schema_audit_roundtrip_live`).
  catalog OWNS the `catalog` schema (catalogs/products/product_drafts) and writes
  audit rows into `public.audit_events` from TWO sources (the cost_tracker AI
  ledger AND audit_mw's 4 write-route rows). The round-trip is **PG-gated**
  (auth-otp no-tunnel pattern): runs LIVE iff `DATABASE_URL` is connectable
  (verified LIVE this gate against local PG 16 `meesell`), else skips. SQLite is
  NOT a substitute. Every OTHER assertion (§16.G AST parity, inbound/outbound
  shim shapes, budget keyspace, budget_cap Lua byte-identity, model-binding,
  Open-Q #1 probe) runs UNCONDITIONALLY with no infra.

---

## 1. The both-directions hybrid posture (UNIQUE to catalog)

At MS-5, all 7 sibling services are already extracted pods. catalog's wiring:

**OUTBOUND (catalog as CALLER → real sibling pods):**
| Callee | Shim methods | Target (real pod by MS-5) | CI |
|---|---|---|---|
| category-svc | `assert_category_exists` (Open-Q #1 → `/schema` probe), `fetch_schema` (hot path), `get_field_enum` | `CATEGORY_SVC_BASE_URL` ClusterIP | mocked (`httpx.MockTransport`) |
| customer-svc | `assert_eligible_for_super_id` (`/eligibility?super_id=`), `get_compliance_block` | `CUSTOMER_SVC_BASE_URL` ClusterIP | mocked (`httpx.MockTransport`) |

> NO `image_client` (R8): the `service.py:828/:980` `getattr(_image_module,
> "service")` branch is DEAD V1 code (`get_image_refs` never existed on
> image-svc); it travels verbatim, the `try: from app.modules import image` hits
> `ImportError` in svc-catalog → caught → `image_refs` stays `()`. Never fires.

**INBOUND (catalog as CALLEE ← 4 already-extracted caller pods):**
| Caller | Shim path | Shape (MERGED consumer WINS) |
|---|---|---|
| svc-image, svc-pricing, svc-export | `GET /internal/products/{id}/ownership-check` | `{owned, category_id}` — §0.6 WIDENED (pricing reads `category_id`) |
| svc-export | `GET /internal/products/{id}/export-snapshot` | 6-field `ExportSnapshotResponse` (MS-A FROZEN) |
| svc-dashboard | `GET /internal/products?page=&limit=` | `{items, total, page, limit}` |
| (defensive) | `GET /internal/products/{id}/validation-summary` | `ValidationSummaryInternalResponse` — no live caller at develop tip |

**The 2-hop chain:** export-snapshot internally calls category-svc `/schema`
(`service.py:962`) — export-svc → catalog-svc → category-svc. The hop is
cache-served on category-svc (top-100 pre-warm, ≥99% hit, ~10 ms). In unit CI the
nested hop is mocked; in the soak the real 2-hop fires.

---

## 2. How the svc-catalog suite is invoked

```bash
cd backend/services/svc-catalog
PYTHONPATH=. python -m pytest tests/ -v        # 62 cases (49 specialist + 13 lead); live audit round-trip iff DATABASE_URL connectable
PYTHONPATH=. python -m ruff check app tests    # lint (clean)
```

- `pytest.ini` is local to the service tree (`asyncio_mode = auto`).
- `tests/conftest.py` populates dummy-but-well-formed env BEFORE `app` imports
  (the trimmed `Settings` SystemExits on a missing REQUIRED field) and
  `setdefault`s `DATABASE_URL` to local PG `meesell` so the cross-schema round-trip
  runs live where PG exists, skips cleanly otherwise.
- **Run under Py 3.11/3.12 (`backend/.venv`), NEVER host 3.9.6** — PEP-604
  `Mapped[str | None]` unions false-fail on ORM boot.

Test composition (62):
| File | Count | Substrate |
|---|---|---|
| `test_catalog_svc_invariants.py` (specialist) | 20 | none (AST/config/ORM) + mocked shims |
| `test_svc_catalog_routes.py` (specialist) | 29 | none / mocked |
| `test_catalog_extraction.py` (LEAD) | 13 | mostly none; 1 PG-gated live round-trip |

---

## 3. Where it hooks into the existing CI gates

Monolith CI gates 1 (unit) / 2 (smoke) / 3 (lint) are blocking; 4 (integration)
/ 5 (golden_roundtrip) advisory per MASTER_PLAN §2.1. svc-catalog adds a NEW job
lane (separate rootdir):

- **svc-catalog lint** → folds into Gate-3 (`ruff check backend/services/svc-catalog/`). CLEAN.
- **svc-catalog unit/contract** → a new Gate-1-shaped job rooted at
  `backend/services/svc-catalog/` with `PYTHONPATH=.`. Env block: the svc's
  trimmed set (`DATABASE_URL`, `VALKEY_URL`, `JWT_SECRET`, `AUDIT_PII_SALT`,
  `CORS_ALLOWED_ORIGINS`, `CATEGORY_SVC_BASE_URL`, `CUSTOMER_SVC_BASE_URL`,
  `GEMINI_API_KEY`, `GEMINI_MODEL`, `LANGFUSE_*`, `AI_DAILY_BUDGET_INR`,
  `CACHE_VERSION`, `APP_ENV`) + the 3 bool feature flags
  (`FEATURE_CATALOG_FORM_ENABLED`, `FEATURE_AI_AUTOFILL_ENABLED`,
  `FEATURE_LIVE_PREVIEW_ENABLED`). Explicitly NO openpyxl/celery/msg91/razorpay
  (catalog has no XLSX, no worker, no OTP, no payments).
- **Cross-schema round-trip gate (optional, PG-backed).** If the lane provisions
  a PG 16 with the `catalog` schema + `public.audit_events` and points
  `DATABASE_URL` at it, the round-trip runs LIVE. Else it skips — the contract is
  still fully covered by the unconditional assertions.

> **Infra dependency (handoff_msH_infra):** `catalog_user` owns the `catalog`
> schema, plus `GRANT INSERT ON public.audit_events` covering BOTH the AI cost
> ledger AND the 4 write-route audit rows. NEW Secret Manager entry:
> `dev-catalog-db-password`. Shared `JWT_SECRET` (same secret iam-svc signs with,
> D7 local JWT). Method-split IngressRoute on `api-tls` (POST /api/v1/products →
> catalog, GET → dashboard).

---

## 4. Strangler-window note

Both trees coexist for the green window:
- The monolith's in-process `catalog` module + its tests stay live.
- svc-catalog's suite runs in parallel.

The monolith `def test_` count stays MONOTONIC (≥ baseline 705 as re-counted at
develop tip `0846940`) — the extraction ADDS the svc-catalog suite, removes none
until cutover. The branch touches ZERO monolith code (`git diff
origin/develop...HEAD -- backend/app backend/tests` = EMPTY). At cutover (post-
window, a SEPARATE founder gate), the monolith catalog module + tests are deleted
in one strangler commit; that is the ONLY sanctioned decrease. Until then **the
monolith catalog endpoints stay LIVE and authoritative** — Traefik flips
`/api/v1/products/*` (POST/PATCH/DELETE/autofill/preview/draft) AND
`/internal/products/*` to svc-catalog only at the cutover (4 networking surfaces
flip at once — the §3.B risk concentration; rollback is a 4-surface route-flip
back, per `docs/runbooks/svc-catalog-rollback.md`).

---

## 5. Callees docker-composed for catalog's CI: NONE (both directions mocked)

| Direction | Edge | Status during window | Composed in CI? |
|---|---|---|---|
| OUTBOUND | category-svc (×3) | real pod (MS-4 extracted) | NO — mocked |
| OUTBOUND | customer-svc (×2) | real pod (MS-3 extracted) | NO — mocked |
| INBOUND | svc-image / svc-pricing / svc-export ownership-check | real caller pods | NO — shape-asserted, no caller container |
| INBOUND | svc-export export-snapshot (2-hop) | real caller pod | NO — mocked |
| INBOUND | svc-dashboard list-products | real caller pod | NO — shape-asserted |

The both-directions live wiring is exercised in the in-cluster soak (all 8
services + the shrinking monolith on the dev node — the D3 e2-standard-4 spend
gets a FRESH founder ask before that deploy), NOT in unit CI.
