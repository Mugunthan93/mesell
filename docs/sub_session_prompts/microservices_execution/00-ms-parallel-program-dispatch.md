# Microservices Migration — Parallel Program Dispatch

**Authored:** 2026-06-12 (master session, founder ruling: "prepare a parallel plan for micro service")
**Founder ruling encoded here (MS-PAR-1):** the LOCKED serial A→H order is upgraded to the proven federation pattern — **pilot alone → parallel pairs → riskiest last**. Sub-plan AUTHORING for all services may start immediately (docs-only, fully parallel); EXECUTION is wave-gated.
**Status condition:** DEV-COMPLETE declared 2026-06-12. MASTER_PLAN v1.3 §3.A.1 start condition SATISFIED.

---

## The wave structure (execution gating)

| Wave | Services | Execution opens when |
|---|---|---|
| **MS-0** | PgBouncer + pool right-sizing (infra, D5 prerequisite) | NOW |
| **MS-1 (pilot)** | **A export** — proves the extraction toolchain | NOW (spec already authored by master session) |
| **MS-2** | **B dashboard ‖ C image** | A's founder gate merged |
| **MS-3** | **D pricing ‖ E customer** | MS-2 both merged |
| **MS-4** | **F category ‖ G iam** | MS-3 both merged |
| **MS-5** | **H catalog** — riskiest, ALONE, last | MS-4 both merged |

**⚠️ D3 VM checkpoint:** the current e2-standard-2 node fits roughly the monolith + 2–3 small services. When a wave's deploy doesn't fit, STOP and ask the founder for the D3 upgrade (e2-standard-4, ~₹2,600/mo) — plan-level pre-approval exists, but the SPEND gets a fresh founder ask at that moment. Never provision without it.

## Common rules (EVERY session — paste-checked at session start)

1. Read `CLAUDE.md` (rules 1–7, esp. HYBRID rule 7) + `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3) + `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the shape template) + your service's module under `backend/app/modules/`.
2. **Only `meesell-*` agents.** Hybrid dispatch: backend lead authors the SPEC → session dispatches the named specialists (services-builder / api-routes-builder / database-builder) → backend lead runs the MERGE GATE (real gate, can reject). Infra surfaces (Dockerfile, k8s, Traefik route, Postgres role) = handoff to `meesell-infra-builder`, never specialist work.
3. **Wave-6 lessons are LAW:** every enum/contract cited file:line from SOURCE (never plan prose — the fabricated-enum reject); verify MOUNTED routes in `main.py`, not schema existence (the row-26 lesson); tautological tests are a reject-class offense (the pricing lesson); report TRUE branch tips; barrel/lane discipline equivalents apply.
4. **Shared-file discipline** (the Wave-6 parallel pattern): `backend/app/main.py` (router removal), gateway/Traefik config, `k8s/` shared files — edits minimal + additive; integration branch merges `origin/develop` BEFORE the founder-gate PR opens; union-merge conflicts keep-both.
5. **Shim contracts:** if your service CALLS another module (or is called), the `/internal/*` HTTP-shim contract doc is a deliverable — frozen file:line-cited shapes. Callee services implement the shims their callers froze. Check `handoff_msA_*` + earlier waves' contract docs before inventing anything.
6. Model C git: `feature/microservices-<svc>/integration` off develop + group branches; worktrees `/tmp/mesell-wt/ms<X>-*`; F3 protection; founder-gate PR `[FOUNDER GATE — DO NOT MERGE]` LEFT OPEN; squash group merges, lead-gate as PR comment, `--admin`, ref-delete via `gh api`. NEVER switch the master tree's branch; NEVER blanket-stage in the master tree.
7. **Dev cluster only.** No staging/prod, no D13/production-move items, no terraform beyond dev-scope manifests. Strangler-fig: the monolith keeps serving until the founder-gated cutover flip per service; rollback contract per MASTER_PLAN.
8. Boards: `feature_board_backend.md` row per service (F2 discipline); STATUS_BACKEND UPDATE blocks; own memory only.
9. Validation floor: full backend suite (count it at session start, ~823+) monotonic zero failures; the service's own tests green in BOTH the monolith (pre-flip) and the extracted service; ruff clean; rollback procedure documented and tested in dev.

## Session prompts (one per new window)

### Session MS-0 — `mesell-ms-pgbouncer-session-1` (start NOW)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-0: dispatch meesell-infra-builder to implement MASTER_PLAN D5 step 1 — PostgreSQL pool right-sizing (max_connections=200) + PgBouncer (transaction pooling) on the dev cluster, per docs/plans/infra/microservices_infra_plan.md. Dev namespace only, current hardware, ₹0. Offline-validate manifests; server dry-run per playbook §15 where reachable. This is the D5 prerequisite — MANDATORY before any service cutover flip (extraction work proceeds in parallel regardless). Founder-gate the PR.
```

### Session MS-A — `mesell-ms-export-session-1` (the PILOT — start NOW)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-A: the export-service extraction (Sub-Plan A / SUB_PLAN_01_export_extraction.md, A1/A2 LOCKED). NOTE: the master session already dispatched the backend lead's spec authoring — check .claude/agent-memory/meesell-backend-coordinator/ for spec_msA_backend.md + handoff_msA_infra.md and CONSUME them if present (do not re-author; if absent, author per hybrid step 1). Then run hybrid steps 2–3: specialists build per the spec's sequence, infra handoff to meesell-infra-builder, lead merge-gate, founder-gate PR left open. Deliverable beyond the service: the validated EXTRACTION RECIPE (the SP01-pilot equivalent) recorded in the backend lead's memory for waves MS-2..5 to copy, and the frozen 6-endpoint /internal/* shim-contract doc for callee sub-plans C/E/F/H.
```

### Session MS-B — `mesell-ms-dashboard-session-1` (spec NOW · execute at MS-2)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-B: dashboard-service extraction. PHASE 1 (now): hybrid step 1 — the backend lead authors SUB_PLAN_0B_dashboard_extraction.md (canonical pattern, grounded in the AS-BUILT backend/app/modules/dashboard at current develop, file:line citations, mounted routes only) + the task spec. PHASE 2 (execution): GATED — begin only when Sub-Plan A's founder gate is merged to develop AND the MS-A recipe exists; then specialists → infra handoff → lead gate → founder gate. Parallel-lane discipline with Session MS-C (image): your diffs stay in your service's surfaces; shared files additive; integration merges develop pre-gate.
```

### Session MS-C — `mesell-ms-image-session-1` (spec NOW · execute at MS-2)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-C: image-service extraction (includes the Celery image-tasks worker split + rembg surface). PHASE 1 (now): backend lead authors SUB_PLAN_0C_image_extraction.md + spec (as-built grounding incl. workers/image_tasks + the GCS storage call sites; image is a CALLEE of export — implement the /internal/* shims the MS-A contract doc froze for you). PHASE 2: GATED on MS-A founder-gate merged + recipe; parallel with MS-B under shared-file discipline.
```

### Session MS-D — `mesell-ms-pricing-session-1` (spec NOW · execute at MS-3)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-D: pricing-service extraction. PHASE 1 (now): backend lead authors SUB_PLAN_0D_pricing_extraction.md + spec (as-built /price-calc per the Wave-6D wiring — the frontend contract is LIVE, Decimal-string serialization is load-bearing, zero response-shape drift allowed). PHASE 2: GATED on MS-2 (both B+C founder gates merged); parallel with MS-E under shared-file discipline.
```

### Session MS-E — `mesell-ms-customer-session-1` (spec NOW · execute at MS-3)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-E: customer-service extraction (seller profiles / Legal-Metrology domain). PHASE 1 (now): backend lead authors SUB_PLAN_0E_customer_extraction.md + spec (as-built per the Wave-6B onboarding wiring — SellerProfile contract is LIVE; customer is a CALLEE of export — implement your frozen /internal/* shims). PHASE 2: GATED on MS-2 complete; parallel with MS-D.
```

### Session MS-F — `mesell-ms-category-session-1` (spec NOW · execute at MS-4)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-F: category-service extraction (3,772-leaf tree + schema contract + smart-picker AI surface). PHASE 1 (now): backend lead authors SUB_PLAN_0F_category_extraction.md + spec. CRITICAL: A1/D6 ruling — ai_ops is VENDORED into AI-consuming services for V1.5 (no ai-ops-svc until V2); the smart-picker call sites + budget brake (shared via Valkey/DB) move per the ruling. category is a CALLEE of export. The i18n/schema_contract.py PRIMITIVE_VALUES surface is load-bearing for the live frontend — zero drift. PHASE 2: GATED on MS-3 complete; parallel with MS-G.
```

### Session MS-G — `mesell-ms-iam-session-1` (spec NOW · execute at MS-4)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-G: iam-service extraction (OTP/login/refresh/me — the auth authority). PHASE 1 (now): backend lead authors SUB_PLAN_0G_iam_extraction.md + spec. CRITICAL: A2/D7 ruling — JWT verification stays LOCAL in every service (vendored middleware); iam-svc owns ONLY issue/refresh/revoke; gateway-JWT was REJECTED. The FE-D5 cookie contract (Path=/api/v1/auth, HMAC allowlist, dual-pepper) is LIVE and frozen — the gateway route must preserve the cookie path exactly. PHASE 2: GATED on MS-3 complete; parallel with MS-F.
```

### Session MS-H — `mesell-ms-catalog-session-1` (spec NOW · execute at MS-5, ALONE)
```
Read docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md (common rules) and execute Session MS-H: catalog-service extraction — the LAST and RISKIEST (largest module: products, drafts, autosave, autofill AI surface, field-enum, the spine everything calls). PHASE 1 (now): backend lead authors SUB_PLAN_0H_catalog_extraction.md + spec (ai_ops vendoring per A1/D6 for the autofill call site; catalog is the largest CALLEE of export). PHASE 2: GATED on MS-4 complete — runs ALONE (no parallel partner; the MS-5 wave is catalog only). After your founder gate: the migration's §5.1-equivalent compliance audit + the MASTER_PLAN completion stamp.
```

## Master-session coordination (this stays with the master window)

- The master session merges founder gates on delegation, opens waves, fields the D3 ask, and resolves cross-session conflicts — exactly the Wave-6 pattern.
- Board source of truth: `feature_board_backend.md` rows per service.
- If two sessions deadlock on a shared file or a shim contract, STOP and escalate to the master session — never improvise a contract.
