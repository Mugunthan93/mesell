# Hybrid-Mode CI Configuration — `svc-pricing` extraction window

**Status:** ACTIVE for the Sub-Plan D strangler window (2026-06-13 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `spec_msD_backend.md §3.A` (hybrid posture) + `SUB_PLAN_0D_pricing_extraction.md` + `CI_HYBRID_MODE_export.md` / `CI_HYBRID_MODE_dashboard.md` (the equivalents this mirrors)

---

## 0. The question this answers

> Which services must be docker-composed for `svc-pricing`'s HTTP-mode CI?

**Answer: NONE.** During the pricing extraction, both callees (catalog, category) are STILL IN-PROCESS in the monolith — `svc-pricing` is the only thing that moved out in this wave. pricing's HTTP shims point at the monolith ClusterIP (`MONOLITH_INTERNAL_BASE_URL`, default `http://monolith-svc:8001`). So:

- **Unit / contract CI for svc-pricing needs ZERO live callee services** — the shim transport is mocked with `httpx.MockTransport` (`tests/test_pricing_extraction.py` T3/T4). The mock stands in for the monolith ClusterIP and returns scripted real-shape JSON; no network, no compose.
- **There IS a PG-gated round-trip test** (unlike svc-dashboard). pricing OWNS the `pricing` schema (`pricing_calcs`) and writes a cross-schema `pricing.calculated` audit row to `public.audit_events`. The T6 round-trip (`test_t6_cross_schema_audit_insert_round_trip`) proves the genuine cross-schema INSERT→SELECT against a live PG 16. It is **PG-gated** (the auth-otp no-tunnel pattern): if `DATABASE_URL` points at a connectable PG, T6 runs LIVE; otherwise it skips (`_PG_SKIP`). SQLite is NOT a substitute — it cannot honour schema-qualified DDL. Every OTHER assertion (§16.G AST parity, wire-shape, T1 Decimal-golden, T3/T4 shim, model-binding, flag-parity) runs UNCONDITIONALLY with no infra.

There is no `docker-compose` of catalog-svc / category-svc, because those services do not exist yet (category extracts MS-3/F; catalog extracts LAST at MS-5/H). pricing's two shims (catalog `get_category_id` via the WIDENED ownership-check, category `get_commission`) are mock-tested for the whole strangler window.

---

## 1. How the svc-pricing suite is invoked

The service is a self-contained package rooted at `backend/services/svc-pricing/`:

```bash
cd backend/services/svc-pricing
PYTHONPATH=. python -m pytest tests/test_pricing_extraction.py -v   # 14 cases (T6 LIVE iff DATABASE_URL connectable, else skip)
PYTHONPATH=. python -m ruff check app tests                         # lint (clean)
```

- `pytest.ini` is local to the service tree (own rootdir; `asyncio_mode = auto`).
- `tests/conftest.py` populates dummy-but-well-formed env BEFORE `app` imports (the trimmed `Settings` SystemExits on a missing REQUIRED field). It also `os.environ.setdefault("DATABASE_URL", ...)` to the local PG `meesell` db — so where a developer/CI runner HAS a connectable PG, T6 exercises the real cross-schema write; where it does not, T6 skips cleanly.
- pytest-asyncio uses `asyncio_mode = auto` (no version drift vs the monolith pin).

Test composition (14 cases):
| Group | Count | Substrate |
|---|---|---|
| §16.G AST parity (incl. §0.6 real-delta sanity + import-rewire + ProductORM-absent AST scan) | 4 | none (AST of both service.py twins) |
| Wire-shape JSON-schema parity (PriceCalcRequest / PriceCalcAlert / PriceCalcResponse) | 3 | none (`model_json_schema()`) |
| T1 frozen Decimal-string golden (byte-compare) | 1 | none (`model_dump_json`) |
| T3/T4 shim round-trips (catalog get_category_id + 404 map; category commission Decimal-never-null + 404) | 3 | none (mocked `httpx.MockTransport`) |
| T6 cross-schema audit (model-binding UNCONDITIONAL + round-trip PG-GATED) | 2 | model-binding: none · round-trip: live PG 16 (gated) |
| Flag-parity regression guard (`FEATURE_PRICE_CALCULATOR_ENABLED` exists + truthy) | 1 | none (`app.shared.config.settings`) |

> **The flag-parity guard is the round-1 REJECT regression pin.** Round 1 of this merge gate REJECTED because the services-builder's trimmed `Settings` dropped `FEATURE_PRICE_CALCULATOR_ENABLED`, which `router.py:99` reads — every price-calc request would 500 with an `AttributeError` at the guard. Round 2 restored the field (`config.py:133`, `bool = True`, NOT in `REQUIRED_FIELDS` since it is a bool-with-default). `test_feature_flag_exists_on_trimmed_settings` pins this on every CI run.

---

## 2. Where it hooks into the existing CI gates

The monolith CI (`.github/workflows/ci.yml`) defines gates 1 (unit) / 2 (smoke) / 3 (lint) — blocking — and 4 (integration) / 5 (golden_roundtrip) — advisory per MASTER_PLAN §2.1. svc-pricing adds a NEW job lane that runs alongside, not inside, those monolith gates (the service tree is a separate rootdir):

- **svc-pricing lint** → folds into the existing Gate-3 lane (`ruff check backend/services/svc-pricing/` added to the lint step's path set). Currently CLEAN.
- **svc-pricing unit/contract** → a new job mirroring the Gate-1 shape but rooted at `backend/services/svc-pricing/` with `PYTHONPATH=.`. No callee service containers. The env block is the svc's trimmed set (`DATABASE_URL`, `VALKEY_URL`, `JWT_SECRET`, `AUDIT_PII_SALT`, `CORS_ALLOWED_ORIGINS`, `MONOLITH_INTERNAL_BASE_URL`, `APP_ENV`) + the bool-with-default `FEATURE_PRICE_CALCULATOR_ENABLED` — explicitly NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS/CELERY (pricing is DETERMINISTIC P&L math, §0.3: no AI, no Celery, no object storage).
- **Cross-schema round-trip gate (optional, PG-backed).** If the svc-pricing CI lane provisions a PG 16 service container with the `pricing` schema + `public.audit_events` and points `DATABASE_URL` at it, T6 runs LIVE and proves the cross-schema audit INSERT the I5 grant enables. Where no PG is provisioned, T6 skips — the contract is still fully covered by the unconditional AST/wire-shape/Decimal/shim/binding/flag assertions.

> **Infra dependency (handoff_msD_infra I5/I9):** pricing's Postgres need is a `pricing_user` role owning the `pricing` schema, plus `INSERT ON public.audit_events` (I5) for the cross-schema audit write. The transitional `SELECT ON public.products` (I9) is DELIBERATELY NOT granted — §0.6 Option B routes category_id through the catalog shim, not a cross-schema DB read. The one NEW Secret Manager entry is `dev-pricing-db-password` (the `pricing_user` password). CI's optional PG container exercises the I5 path; deploy needs the SM secret.

---

## 3. Strangler-window note

During the green window both trees coexist:
- The monolith's in-process `pricing` module + its tests stay live (the monolith Gate-1/2/3 still run `tests/modules/pricing/`).
- svc-pricing's suite runs in parallel.

The monolith `def test_` count must stay MONOTONIC (≥ baseline 698 as re-counted at develop tip `d4aa572`) for the whole window — the extraction ADDS the svc-pricing suite, removes none from the monolith until cutover. At cutover (post-window, a SEPARATE founder gate), the monolith pricing module + tests are deleted in one strangler commit and the count steps down by pricing's share; that is the ONLY sanctioned decrease. Until then, **the monolith price-calc endpoint stays LIVE and authoritative** — Traefik routes `POST /api/v1/products/{id}/price-calc` to svc-pricing only at the cutover flip, which is NOT taken at this gate.

---

## 4. Callees docker-composed for pricing's CI: NONE

| Callee | Shim | Status during window | Composed in CI? |
|---|---|---|---|
| catalog | `get_category_id` → `GET /internal/products/{id}/ownership-check` (WIDENED +category_id, Option B) | in-process in monolith (catalog extracts LAST, MS-5/H) | NO — mocked (`httpx.MockTransport`) |
| category | `get_commission` → `GET /internal/categories/{id}/commission` (`{commission_pct:"<decimal>"}` NEVER null) | in-process in monolith (category extracts MS-3/F) | NO — mocked (`httpx.MockTransport`) |

Neither `/internal/*` endpoint is live yet; both shims are mock-tested for the whole strangler window. No callee container exists. The widened ownership-check is Sub-Plan H's obligation; the commission endpoint is Sub-Plan F's — both frozen in `SHIM_CONTRACT_pricing_callees.md`.
