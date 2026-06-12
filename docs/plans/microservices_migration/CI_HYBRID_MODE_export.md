# Hybrid-Mode CI Configuration — `svc-export` extraction window

**Status:** ACTIVE for the Sub-Plan A strangler window (2026-06-12 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `spec_msA_backend.md §3.A` (hybrid posture) + §5 (doc deliverable) + `SUB_PLAN_01_export_extraction.md`

---

## 0. The question this answers

> Which services must be docker-composed for `svc-export`'s HTTP-mode CI?

**Answer: NONE.** During the export extraction, all 4 callees (catalog, category, customer, image) are STILL IN-PROCESS in the monolith — `svc-export` is the only thing that moved out. The HTTP shims point at the monolith ClusterIP (`MONOLITH_INTERNAL_BASE_URL`, default `http://monolith-svc:8001`). So:

- **Unit / contract CI for svc-export needs ZERO live callee services** — the shim transport is mocked with `httpx.MockTransport` (`tests/test_extracted_clients.py`, `tests/test_export_extraction.py`). The mock stands in for the monolith ClusterIP and returns scripted real-shape JSON; no network, no compose.
- **The one PG-gated test** (`test_cross_schema_audit_insert_round_trip`) needs a reachable Postgres with the `export` + `public` schemas — NOT a callee service. It SKIPS with a documented reason when no connectable Postgres is configured (auth-otp no-tunnel pattern), so the suite is green on a no-DB CI runner.

There is no `docker-compose` of catalog-svc / category-svc / customer-svc / image-svc, because those services do not exist yet.

---

## 1. How the svc-export suite is invoked

The service is a self-contained package rooted at `backend/services/svc-export/`:

```bash
cd backend/services/svc-export
PYTHONPATH=. python -m pytest -q          # all 37 tests
PYTHONPATH=. python -m ruff check .       # lint (clean)
```

- `pytest.ini` is local to the service tree (own rootdir).
- `tests/conftest.py` populates dummy-but-well-formed env BEFORE `app` imports (the trimmed `Settings` SystemExits on a missing required field). The dummy values never reach a live service — the shim tests mock the transport.
- pytest-asyncio is pinned to the same `0.24.0` as the monolith CI (no version drift).

Test composition (37 total):
| File | Count | Substrate |
|---|---|---|
| `test_import_sanity.py` | 5 | none (import graph) |
| `test_export_routes.py` | 7 | none (mounted-route inspection) |
| `test_extracted_clients.py` | 12 (params → 14 cases) | mocked httpx transport |
| `test_export_extraction.py` | 11 | AST parity + mocked transport + Pydantic JSON-schema + 1 PG-gated round-trip |

---

## 2. Where it hooks into the existing CI gates

The monolith CI (`.github/workflows/ci.yml`) defines gates 1 (unit) / 2 (smoke) / 3 (lint) — blocking — and 4 (integration) / 5 (golden_roundtrip) — advisory per MASTER_PLAN §2.1. svc-export adds a NEW job lane that runs alongside, not inside, those monolith gates (the service tree is a separate rootdir):

- **svc-export lint** → folds into the existing Gate-3 lane (`ruff check backend/services/svc-export/` added to the lint step's path set). Currently CLEAN.
- **svc-export unit/contract** → a new job mirroring the Gate-1 shape but rooted at `backend/services/svc-export/` with `PYTHONPATH=.`. No service containers. The env block is the svc's trimmed set (DATABASE_URL @schema export, VALKEY_URL, JWT_SECRET, GCS_*, APP_ENV, MONOLITH_INTERNAL_BASE_URL) — explicitly NO GEMINI/LANGFUSE/MSG91/RAZORPAY.
- **svc-export cross-schema round-trip** → ADVISORY (like Gate-4). It is PG-gated; on a runner with a Postgres service container that has the `export_user` role + `export`/`public` schemas (infra I5 + I8), the round-trip runs and asserts the real cross-schema INSERT. Without it, the test skips green and the unconditional model-binding + row-content assertions still cover the contract.

> **Infra dependency for the round-trip gate (handoff_msA_infra I5):** when CI wants the round-trip to actually execute (not skip), the Postgres service must grant `INSERT ON public.audit_events` to the export role and have both schemas. The local Phase-C run created `svc_export` + `meesell_test` with these grants and the round-trip PASSED — proving the path works end-to-end on PG 16.

---

## 3. Strangler-window note

During the 7-day green window both trees coexist:
- The monolith's in-process `export` module + its tests stay live (the monolith Gate-1/2/3 still run `tests/modules/export/` + `tests/integration/test_export_*.py`).
- svc-export's suite runs in parallel.

The monolith `def test_` count must stay MONOTONIC (≥ baseline) for the whole window — the extraction ADDS tests, removes none until cutover. At cutover (post-window), the monolith export module + tests are deleted in one strangler commit and the count steps down by export's share; that is the ONLY sanctioned decrease.
