# Hybrid-Mode CI Configuration — `svc-category` extraction window

**Status:** ACTIVE for the Sub-Plan F strangler window (2026-06-14 → +7 green days)
**Owner:** meesell-backend-coordinator (backend lead)
**Authority:** `SUB_PLAN_0F_category_extraction.md` (hybrid posture) + `spec_msF_backend.md` + `CI_HYBRID_MODE_export.md` / `CI_HYBRID_MODE_dashboard.md` / `CI_HYBRID_MODE_pricing.md` (the equivalents this mirrors)

---

## 0. The question this answers

> Which services must be docker-composed for `svc-category`'s HTTP-mode CI?

**Answer: NONE.** `category` is a pure CALLEE — it makes ZERO outbound domain
calls (SUB_PLAN_0F "Cross-module edges — category as CALLER: ZERO"). It exposes
`/internal/*` shims that its callers dial; it dials nobody. So there is no
sibling service to compose for category's own CI.

- **Unit / contract CI for svc-category needs ZERO live callee services** — the
  service has no outbound HTTP shim clients to mock at all. Its own suite mocks
  Valkey (DB-0 rate-limit + DB-3 cache) and the audit-DB session via the
  `patch_singletons` autouse fixture (`tests/test_svc_category_routes.py`); no
  network, no compose.
- **No PG-gated round-trip test is REQUIRED in the lead suite.** Unlike pricing
  (which writes a cross-schema `pricing.calculated` audit row), category's 5
  public routes are ALL read-only → **zero audit rows** (SUB_PLAN_0F as-built
  inventory: "All 5 are read-only → NO audit rows"). The one cross-schema write
  category's vendored `ai_ops/cost_tracker.py` can make is the AI-cost ledger
  INSERT into `public.audit_events` — but that fires only on a live `call_gemini`
  (Smart Picker), which the suite mocks. The cross-schema grant
  (`GRANT INSERT ON public.audit_events TO category_user`) is provisioned by
  infra (`k8s/svc-category/schema-role.sql`) and exercised at deploy, not in the
  build-time suite. The db-migration round-trip (the 4 GLOBAL tables → `category`
  schema, GIN preserved) is owned + round-tripped by the database-builder on the
  db branch.

There is no `docker-compose` of export-svc / pricing-svc / catalog-svc, because
category does not CALL them — they call category. During the strangler window,
category's callers (export-svc + pricing-svc, both pods at MS-4; catalog-svc
still in-monolith until MS-5) reach category via their already-built
`category_client` HTTP shims pointing at the monolith ClusterIP; at cutover the
Traefik route for `/internal/categories/*` + `/api/v1/categories/*` flips to
svc-category with ZERO call-site diff (§16.G).

---

## 1. How the svc-category suite is invoked

The service is a self-contained package rooted at `backend/services/svc-category/`:

```bash
cd backend/services/svc-category
PYTHONPATH=. python -m pytest tests/ -v          # 56 cases (routes + invariants + lead extraction)
PYTHONPATH=. python -m pytest tests/test_category_extraction.py -v   # 11 lead Phase-C cases
PYTHONPATH=. python -m ruff check app tests      # lint (clean)
```

- `pytest.ini` is local to the service tree (own rootdir; `asyncio_mode = auto`).
- `tests/conftest.py` populates dummy-but-well-formed env via
  `os.environ.setdefault` BEFORE `app` imports (the trimmed `Settings`
  SystemExits on a missing REQUIRED field).
- **Python version:** run on **Python 3.11/3.12** (the service uses PEP-604
  `X | Y` unions at runtime). The host system `python3` is **3.9.6** — running
  the suite under 3.9 raises spurious union-resolution / ORM-boot failures that
  are interpreter artifacts, NOT real test failures. Use the backend venv
  (`backend/.venv`, Py3.11) or CI Linux Py3.12.

Test composition (56 cases):
| Group | Count | Substrate |
|---|---|---|
| svc routes (5 public) — flag-guards, ETag/304, rate-limit, shim shapes | ~45 | mocked Valkey (`patch_singletons`) |
| svc invariants | (in the 45/56) | none |
| **lead Phase-C `test_category_extraction.py`** | **11** | none (AST + value compares) |

The 11 lead Phase-C cases (the CI-enforced re-proof of the extraction):
| # | Assertion | Method |
|---|---|---|
| 1 | §16.G `service.py` executable body byte-identical (NO §0.6 delta — pure callee) | AST recursive import+docstring strip |
| 2 | raw service.py trees DIFFER (import-strip parity not vacuous) | AST raw dump |
| 3 | `picker.py` byte-identical (golden top-5 recall preserved) | byte compare |
| 4 | `budget_cap.py` + `cost_tracker.py` byte-identical (Lua + key formats) | byte compare |
| 5 | `ai:*` budget keyspace NOT `category:`-prefixed (R1/P0 SHARED cap carve-out) | source token scan |
| 6 | `schema_contract` frozensets byte-identical, pinned 11/7/9/8/2/3 (FE wizard guard) | AST `literal_eval` value compare |
| 7 | `/super-categories` shim = `response_model=list[str]` BARE ARRAY (round-1 reject guard, FROZEN-0E) | AST decorator parse |
| 8 | `/commission` shim = `CommissionResponse` w/ bare `Decimal` (never-null) | AST decorator + field parse |
| 9 | schema + field-enum shims = object envelopes (unchanged) | AST decorator parse |
| 10 | exactly 4 `/internal/*` shims mounted (no leak, no miss) | AST decorator parse |
| 11 | `FEATURE_SMART_PICKER_ENABLED` on trimmed Settings (MS-D flag-parity lesson) | settings probe |

---

## 2. Route table (independently re-verified, not trusted from the builder)

`svc-category` mounts: **5 public** routes (`/api/v1/categories/suggest`,
`/browse`, `/categories`, `/{id}/schema`, `/{id}/field-enum/{name}`) + **4
internal** shims (`/internal/categories/{id}/schema`, `/field-enum/{field}`,
`/commission`, `/internal/super-categories`) + `/health`. No leaked surface.

---

## 3. The budget-brake carve-out (the load-bearing CI invariant)

The single most important CI invariant for category (vs export/dashboard which
have no AI): the `ai:cost:*` / `ai:budget:*` Valkey DB-0 keys stay **global /
un-prefixed** so the ₹500 daily cap is SHARED across every AI service. Test #5
(`test_budget_keyspace_is_not_category_prefixed`) pins this — a `category:ai:*`
split-cap key is a **P0** (the cap silently stops working globally). The carve-out
is also a named acceptance item in SUB_PLAN_0F §F-acceptance + Risk R1, and is
re-verified in the rollback runbook (`docs/runbooks/svc-category-rollback.md` §5a).
