# MEMORY append — meesell-backend-coordinator — MS-B (dashboard extraction) Phase 1

> **WORKTREE FALLBACK.** The main-tree append to MEMORY.md was BLOCKED by the
> bg-session worktree-isolation guard. This is the standalone entry the
> session must splice into the main-tree
> `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (and index it
> alongside the MS migration session entries).

## Session mesell-ms-dashboard-session-1 — 2026-06-12 — MS-B Sub-Plan B (`dashboard` extraction) SPEC AUTHORED (HYBRID STEP 1, EXECUTION GATED MS-2)

Worktree `/tmp/mesell-wt/msB-docs` on branch `docs/msB-subplan-0B` @ TRUE tip **`c8599556`** (== `origin/develop`; no divergence, unlike MS-A which found stale local develop at `f23d84a`). Docs-only Phase 1 — NO extraction code, NO git ops (session handles git). Mirrors the MS-A pattern (`spec_msA_backend.md` + `handoff_msA_infra.md`).

**5 deliverables landed:**
1. `docs/plans/microservices_migration/SUB_PLAN_0B_dashboard_extraction.md` (DRAFT) — canonical SUB_PLAN_01 section shape: §0 GROUND TRUTH (file:line cited from SOURCE), Decisions B1-B4, Agent lineup, Branch setup (Model C), Code surfaces, Documentation deliverables, FROZEN /internal/* shim contracts, Memory protocol, Review+iteration, Acceptance gate, Risk register R1-R6, Revision history.
2. FROZEN /internal/* shim-contract section (2 endpoints) inside SUB_PLAN_0B.
3. `spec_msB_backend.md` + `handoff_msB_infra.md` — WORKTREE FALLBACK copies (main-tree blocked by bg-isolation guard).
4. board + STATUS UPDATE (worktree, additive).
5. this memory entry.

**Load-bearing AS-BUILT facts (re-verified, supersede stale plan/prompt prose):**
- **dashboard = 6 files, NO repository.py** (deliberate §13.D deviation, __init__.py:9-11). Owns ZERO tables. `domain.py` empty-but-legal (`__all__ = []`).
- **NO ai_ops, NO Celery, NO tasks.py** — pure read. svc-dashboard is api-only (NO worker pod, NO broker/result Valkey). LIGHTEST extraction of all 8.
- **Mounted route = exactly 1** (counted from router.py decorators, row-26 lesson): `GET /api/v1/products` 200, `@rate_limit(dashboard_list,600,3600)` router.py:86, `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard router.py:118. Mount main.py:43 (import) + main.py:141 (include_router). **Prompt said mount at main.py:137 — AS-BUILT is 141.**
- **2 cross-module call sites** (dashboard/service.py:36-42 imports; :78 + :84 call sites):
  - catalog `list_products(user_id, pagination, db)` (catalog/service.py:999) -> `PaginatedProductsInternal` (catalog/domain.py:170)
  - customer `get_onboarding_completeness(user_id, db)` (customer/service.py:682) -> `ProfileCompleteness` (customer/domain.py:98)
- **dashboard is a LEAF CONSUMER** — only main.py:43 imports it; NOTHING reads from dashboard.* -> svc-dashboard exposes NO /internal/*. 2 outbound shims, zero inbound.

**KEEPER LESSON — PLAN-TEXT CORRECTION (the fabricated/stale-name trap):** MASTER_PLAN §1.C AND the dispatch prompt's grounding facts BOTH named the dashboard->customer method `get_profile_completeness`. **WRONG against source — AS-BUILT is `get_onboarding_completeness`** (customer/service.py:682; dashboard/service.py:84; __init__.py:15). The `get_profile_completeness` name is the early §8.C LOCK name that was renamed during construction. ALWAYS re-cite cross-module method names from the callee `def` line, never from plan prose or even the dispatch's own grounding facts. This is the same class as MS-A's mis-named `image.get_image_bytes`/`fetch_xlsx_aliases` corrections — plan prose drifts from as-built; SOURCE wins.

**Decisions consumed (nothing new to ratify):** B1 ai_ops N/A (dashboard makes zero AI calls); B2 mw inherited D7/A2 (6-mw vendored, plan_guard+audit INERT, JWT local); B3 order confirmation (dashboard second, first of MS-2 pair w/ image); B4 database-builder VERIFY-ONLY (dashboard owns no schema -> NO schema-split, the cheapest db lane).

**Shim-style REUSE (rule 5):** copied MS-A's frozen-contract style verbatim — `/internal/<resource>/*` cluster-DNS-only path prefix; JWT-forward auth (no separate s2s token); MeesellError 4-field envelope; httpx 5s read/2s connect, 1 retry on 503/504. customer shim path `/internal/seller-profile/{user_id}/onboarding-completeness` mirrors MS-A's `/internal/seller-profile/{user_id}/compliance-block`. During MS-2 the callees (catalog, customer) are STILL in-process -> shim base URL = monolith ClusterIP (R4 hybrid posture).

**EXECUTION GATE (MS-2):** Phase 2 specialist dispatch opens ONLY when Sub-Plan A founder gate merged to develop AND the MS-A extraction recipe exists in this memory. Parallel with MS-C (image) under shared-file additive discipline: main.py mount removal + Traefik table = additive/keep-both; dashboard `GET /api/v1/products` vs image `/api/v1/products/{id}/images*` = DISJOINT prefixes. §13-DASHBOARD-D2 path-key collision (GET shares /api/v1/products with catalog POST) -> Traefik method/prefix-aware; only GET routes to svc-dashboard (catalog extracts LAST at MS-5, so POST never moves during dashboard's window).

**D3 VM:** dashboard is the smallest service (50m/128Mi api-only, no worker, no schema, no GCS) — fits current node at MS-2 alongside monolith + svc-export + svc-image. D3 spend (e2-standard-4 ~₹2,600/mo) re-asked fresh ONLY if MS-2 deploy overflows the node (standing rule). No money committed.

**Process notes:** worktree-isolation guard blocked ALL main-tree writes (spec/handoff/memory) — wrote fallback copies under `/tmp/mesell-wt/msB-docs/.claude/agent-memory/meesell-backend-coordinator/`; session must relocate. Test floor: 698 `def test_` full-suite in worktree (develop advanced past MS-A's 649), 36 dashboard-own — validation = MONOTONIC vs live baseline at PR time, never hardcode.
