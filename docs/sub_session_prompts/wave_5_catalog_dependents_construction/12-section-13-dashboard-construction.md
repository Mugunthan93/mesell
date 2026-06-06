# Sub-Session Prompt: §13 Module `dashboard`
# Wave 5 of 10 — CONSTRUCTION (parallel-safe with §11 image + §12 pricing)
# Specialist agents: meesell-api-routes-builder + meesell-services-builder
# Renames session to: meesell-backend-construction-13-dashboard-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §13 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder agents operating in a dedicated construction sub-session for MeeSell §13 (Module `dashboard`).

§13 is the **purest demonstration of modular monolith discipline** — owns ZERO tables, reads NOTHING directly, has NO `repository.py` as a structural deviation from §3.C canonical layout (locked explicitly so absence reads as intentional design).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §13 Module `dashboard` — 1 endpoint `GET /api/v1/products` paginated listing for Feature 8
- Specialist agents: meesell-api-routes-builder (router + Pydantic schemas + pagination validation) + meesell-services-builder (composition logic only — no repository)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-13-dashboard-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §13 — A through L (esp. §13.A no-repository structural deviation locked; §13.B 1 endpoint paginated; §13.C 1 public + 1 module-private service surface; NO repository.py; §13.G exceptions; §13.H NO adapter usage; §13.I cross-cutting incl. plan_guard NOT participating, rate-limit per-IP only, audit NONE on read-only, cache helper NOT participating; §13.J 3 unit + 2 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4 (core/), §5 (shared/), §8 customer (CONSTRUCTED Wave 3; consumes `get_profile_completeness`), §10 catalog (CONSTRUCTED Wave 4; consumes `list_products` + `get_validation_summary`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §3.4 (endpoints), Feature 8 Tracking Dashboard.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-api-routes-builder.md`, `meesell-services-builder.md`.

6. Memory files.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-4 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C with the §13 structural exception:

```
backend/app/modules/dashboard/
├── __init__.py
├── router.py            # FastAPI APIRouter; 1 endpoint
├── service.py           # 1 public method `list_products_for_dashboard` + 1 module-private `_compose_response` pure function
├── schemas.py           # DashboardQuery (pagination + filters), DashboardResponse, ProductCard
├── domain.py            # ProductCard, ProfileCompleteness value objects
└── exceptions.py        # 1 InvalidPaginationError
```

**NO `repository.py` — structural exception locked at §13.D + §3.C deviation + §16.F.1.** The §19 CI linter has an allowlist for this absence. Dashboard reads NOTHING directly; calls only `catalog.service.list_products(user_id, Pagination)` + `customer.service.get_profile_completeness(user_id)`.

Plus: register `dashboard_router` in `backend/app/main.py`.

Locked invariants:
- 1 endpoint: `GET /api/v1/products?page=1&limit=20&status_filter=...&search=...` per §13.B.
- Per §2.D founder ruling matrix kept at exactly 8 ✓ — V1 dashboard does NOT opt into image / pricing / export `summary` OPTIONAL surfaces (V1.5 amendment may elevate to 11 ✓ but NOT V1).
- Calls ONLY: `catalog.service.list_products(user_id, Pagination)` + `customer.service.get_profile_completeness(user_id)`. No other cross-module calls.
- NO adapter usage (zero egress per §1.E confirming P95 ≤ 200 ms budget).
- plan_guard NOT participating (dashboard is one of 3 plan_guard-excluded modules alongside customer + pricing).
- Rate-limit per-IP only (no JWT-keyed limit).
- Audit NONE on this read-only endpoint.
- Cache helper NOT participating (high write churn from product PATCH would tank hit rate).
- 1 i18n key: `validation.dashboard.invalid_pagination`.
- `_compose_response` is a pure function (no I/O, no DB).
- Empty inventory returns 200 with `products=[]` + `total=0` — NOT 404 (empty is valid state for first-time sellers).

Construction protocol:

1. **Tests first** per §13.J (3 unit + 2 integration):

   **Unit** (`backend/tests/modules/dashboard/`):
   - `test_pagination_validation` — `page=0` → 400; `limit=0` → 400; `limit=101` → 400; `status_filter="invalid"` → 400 (Pydantic Literal rejection); `search` with 101 chars → 400; happy-path defaults verified.
   - `test_response_composition` — mocked `catalog.list_products` returns 3 products + total=42; mocked `customer.get_profile_completeness` returns specific counts; verify `DashboardResponse.products` has 3 items, `total=42`, `page` + `limit` echo request, `profile_completeness` mirrors mock.
   - `test_empty_state_response` — mocked `catalog.list_products` returns empty + total=0 → 200 with `products=[]` + `total=0` (NOT 404); `profile_completeness` still surfaces.

   **Integration** (`backend/tests/integration/test_dashboard_*.py`):
   - `test_dashboard_list_full_flow` — seller signs up via §7 → creates 5 products via §10 → `GET /api/v1/products?page=1&limit=20` with JWT → 200, products length 5, total=5, profile_completeness reflects onboarding state.
   - `test_dashboard_cross_tenant_isolation` — User A 3 products + User B 2 products; A's `GET /products` returns ONLY A's 3 + total=3; B's returns ONLY B's 2 + total=2. End-to-end tenancy contract guarding against future refactors.

   Fixtures: real Postgres; seeded users + products from §7 + §10 fixtures (reuse, NOT duplicate); NO vendor stubs needed (dashboard has no egress).

2. **Implementation** per §13.B-§13.I with locked signatures.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT create `modules/dashboard/repository.py` — structural absence is intentional design (§13.D + §3.C deviation).
- DO NOT call any module other than `catalog.service` and `customer.service` (matrix kept at 8 ✓ for V1).
- DO NOT import any adapter.
- DO NOT call `ai_ops.client`.
- DO NOT participate in plan_guard.
- DO NOT use Valkey cache (high write churn would tank hit rate per §13.I).
- DO NOT return 404 on empty inventory — 200 with `products=[]`.
- DO NOT emit audit events (read-only endpoint).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — router + schemas + pagination validation.
- `meesell-services-builder` — service composition (pure function).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §13)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 1 endpoint mounted per §13.B.
2. NO `modules/dashboard/repository.py` file (verified by `ls`).
3. Only 2 cross-module calls: `catalog.service.list_products` + `customer.service.get_profile_completeness` (grep-verifiable).
4. NO adapter imports.
5. NO `ai_ops.client` imports.
6. Empty inventory returns 200 with `products=[]`.
7. `_compose_response` is pure (no I/O, no DB calls).
8. 1 i18n key registered: `validation.dashboard.invalid_pagination`.
9. 3 unit + 2 integration tests PASS per §13.J.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §13 dashboard CONSTRUCTED ===
   Files created: modules/dashboard/{5 files}; main.py mount
   Structural exception: NO repository.py (§13.D + §3.C deviation; §19 CI linter allowlist required at §19 construction)
   Tests added: 3 unit + 2 integration
   Decisions made: <list>
   Hand-offs: §14 export construction next (no consumption); §19 CI linter must allowlist dashboard no-repository exception
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Pagination shape mismatch with `catalog.list_products` signature.
- §2.D matrix elevation request (V1 locked at 8 ✓).
- Empty state edge case (e.g. profile_completeness on a brand-new user with no products).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-13-dashboard-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-4 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §13 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 5 of 10
- **Sequential dependency:** Wave 1-4 CONSTRUCTED (esp. §8 customer + §10 catalog).
- **Parallel-safe?:** Yes — runs in parallel with §11 image + §12 pricing.
- **Expected duration estimate:** ~4-6 hours (lightest module).
- **Acceptance verification by master:** (1) `ls backend/app/modules/dashboard/repository.py` confirms absence; (2) `grep -r "from app.adapters" backend/app/modules/dashboard/` returns nothing; (3) `grep -r "ai_ops" backend/app/modules/dashboard/` returns nothing; (4) tests PASS; (5) STATUS_BACKEND.md UPDATE block present.
