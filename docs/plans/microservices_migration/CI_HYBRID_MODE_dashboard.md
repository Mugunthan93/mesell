# Hybrid-Mode CI Configuration — `svc-dashboard` extraction window

**Status:** ACTIVE for the Sub-Plan B strangler window (2026-06-13 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `spec_msB_backend.md §3.A` (hybrid posture) + `SUB_PLAN_0B_dashboard_extraction.md` + `CI_HYBRID_MODE_export.md` (the svc-export equivalent this mirrors)

---

## 0. The question this answers

> Which services must be docker-composed for `svc-dashboard`'s HTTP-mode CI?

**Answer: NONE.** During the dashboard extraction, both callees (catalog, customer) are STILL IN-PROCESS in the monolith — `svc-dashboard` is the only thing that moved out (alongside `svc-export` from Sub-Plan A, but the two are independent and neither calls the other). dashboard's HTTP shims point at the monolith ClusterIP (`MONOLITH_INTERNAL_BASE_URL`, default `http://monolith-svc:8001`). So:

- **Unit / contract CI for svc-dashboard needs ZERO live callee services** — the shim transport is mocked with `httpx.MockTransport` (`tests/test_dashboard_extraction.py`, `tests/test_dashboard_routes.py`). The mock stands in for the monolith ClusterIP and returns scripted real-shape JSON; no network, no compose.
- **There is NO PG-gated round-trip test** (unlike svc-export). dashboard owns ZERO tables (§13.D structural exception), so there is no `<mod>` schema and no cross-schema audit INSERT to prove. The vendored `audit_mw` import-chain is wired but INERT on the read-only `GET /api/v1/products` — no row is ever written. The I5 grant (`GRANT INSERT ON public.audit_events TO dashboard_user`) exists only so the vendored middleware import resolves; CI does not need a Postgres service container for dashboard at all.

There is no `docker-compose` of catalog-svc / customer-svc, because those services do not exist yet (catalog extracts LAST at MS-5/H; customer at MS-3/E). dashboard's two shims (catalog `list_products`, customer `get_onboarding_completeness`) are mock-tested for the whole strangler window.

---

## 1. How the svc-dashboard suite is invoked

The service is a self-contained package rooted at `backend/services/svc-dashboard/`:

```bash
cd backend/services/svc-dashboard
PYTHONPATH=. python -m pytest -q          # 30 test cases (28 def test_ + 2 parametrized)
PYTHONPATH=. python -m ruff check .       # lint (clean)
```

- `pytest.ini` is local to the service tree (own rootdir).
- `tests/conftest.py` populates dummy-but-well-formed env BEFORE `app` imports (the trimmed `Settings` SystemExits on a missing required field). The dummy values never reach a live service — the shim tests mock the transport.
- pytest-asyncio is pinned to the same `0.24.0` as the monolith CI (no version drift).

Test composition (30 cases):
| File | Count | Substrate |
|---|---|---|
| `test_import_sanity.py` | 5 | none (import graph; asserts NO celery, NO ai_ops, NO repository.py) |
| `test_dashboard_routes.py` | 11 | none (mounted-route inspection — 1 route `GET /api/v1/products`, flag-guard, rate-limit) |
| `test_dashboard_extraction.py` | 12 def test_ (+2 parametrized cases → 14) | §16.G AST parity + wire-shape JSON-schema parity + mocked httpx transport for both shims |

---

## 2. Where it hooks into the existing CI gates

The monolith CI (`.github/workflows/ci.yml`) defines gates 1 (unit) / 2 (smoke) / 3 (lint) — blocking — and 4 (integration) / 5 (golden_roundtrip) — advisory per MASTER_PLAN §2.1. svc-dashboard adds a NEW job lane that runs alongside, not inside, those monolith gates (the service tree is a separate rootdir):

- **svc-dashboard lint** → folds into the existing Gate-3 lane (`ruff check backend/services/svc-dashboard/` added to the lint step's path set). Currently CLEAN.
- **svc-dashboard unit/contract** → a new job mirroring the Gate-1 shape but rooted at `backend/services/svc-dashboard/` with `PYTHONPATH=.`. No service containers. The env block is the svc's trimmed set (`DATABASE_URL`, `VALKEY_URL`, `JWT_SECRET`, `FEATURE_TRACKING_DASHBOARD_ENABLED`, `APP_ENV`, `MONOLITH_INTERNAL_BASE_URL`) — explicitly NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS (dashboard is a pure read; smallest secret surface of any extracted service).
- **No cross-schema round-trip gate.** Unlike svc-export, svc-dashboard has nothing PG-gated to run — it owns no schema and writes no audit row. The contract is fully covered by the mocked-transport shim tests + the AST/JSON-schema parity assertions, which need no infra.

> **Infra dependency (handoff_msB_infra I5/I7):** dashboard's only Postgres need is a connectable role (`dashboard_user`, NO owned schema, default `public` search_path) with `INSERT ON public.audit_events` so the inert audit import resolves. The one NEW Secret Manager entry is `dev-dashboard-db-password` (the `dashboard_user` password, URL-encoded into `DATABASE_URL`). CI does not exercise this path — it is a deploy-time dependency, not a test-time one.

---

## 3. Strangler-window note

During the green window both trees coexist:
- The monolith's in-process `dashboard` module + its tests stay live (the monolith Gate-1/2/3 still run `tests/modules/dashboard/`).
- svc-dashboard's suite runs in parallel.

The monolith `def test_` count must stay MONOTONIC (≥ baseline 698) for the whole window — the extraction ADDS tests, removes none until cutover. At cutover (post-window, a SEPARATE founder gate), the monolith dashboard module + tests are deleted in one strangler commit and the count steps down by dashboard's share; that is the ONLY sanctioned decrease. Until then, **the monolith dashboard endpoint stays LIVE and authoritative** — Traefik routes `GET /api/v1/products` to svc-dashboard only at the cutover flip, which is NOT taken at this gate.

---

## 4. Callees docker-composed for dashboard's CI: NONE

| Callee | Shim | Status during window | Composed in CI? |
|---|---|---|---|
| catalog | `list_products` → `GET /internal/products` | in-process in monolith (catalog extracts LAST, MS-5/H) | NO — mocked (`httpx.MockTransport`) |
| customer | `get_onboarding_completeness` → `GET /internal/seller-profile/{user_id}/onboarding-completeness` | in-process in monolith (customer extracts MS-3/E) | NO — mocked (`httpx.MockTransport`) |

Neither `/internal/*` endpoint is live yet; both shims are mock-tested for the whole strangler window. No callee container exists.
