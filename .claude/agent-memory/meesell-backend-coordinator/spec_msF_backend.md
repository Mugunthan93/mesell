# spec_msF_backend.md — category-service extraction (Session MS-F) — EXECUTABLE TASK SPEC

**Status:** AUTHORED 2026-06-12 (PHASE 1, hybrid step 1). **EXECUTION GATED ON
MS-4 WAVE OPEN** (MS-3 = pricing + customer both founder-gate-merged; parallel
with MS-G iam).
**Companion sub-plan:** `docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md`
(read it FIRST — this spec is the per-specialist breakdown; the sub-plan is the
contract).
**Authored by:** meesell-backend-coordinator. Mirrors the rigor of the MS-A
spec (which was absent from this worktree — see sub-plan §header note).

---

## Dispatch sequence (critical path)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder  →  Alembic schema-split: 4 GLOBAL tables → schema `category`
                               (categories, templates, field_enum_values, field_aliases)
  meesell-infra-builder     →  Dockerfile + K8s + Postgres schema/role + audit-DB grant
                               + Valkey-DB-3 cache mount + Secret bindings
                               (on feature/microservices-category/infra, infra-lead-reviewed
                               — handoff_msF_infra.md, DO NOT EXECUTE until MS-4)

PHASE B (depends on A — service code targets the new schema + vendored libs):
  meesell-services-builder  →  extract service.py + picker.py + repository.py + domain.py
                               + exceptions.py; VENDOR ai_ops (trimmed) + core/middleware
                               + core/* + i18n + shared/*; wire SHARED budget brake;
                               build standalone main.py (6-mw chain + cache pre-warm)
  meesell-api-routes-builder→  extract router.py (5 public routes verbatim) + author
                               internal_router.py (2-3 /internal/* shims); regen OpenAPI
                               (parallel w/ services-builder once method signatures freeze)
  (verify) meesell-category-picker-builder → confirm smart-picker ranking pipeline +
                               calibration constants survive vendoring (golden ≥80% recall)

PHASE C (depends on B — integration):
  meesell-backend-coordinator → hybrid-mode CI wiring; test_category_extraction.py
                                (PRIMITIVE_VALUES parity + budget-brake-shared assertion
                                + vendoring parity); merge-gate review; board MERGED flip
```

**Iteration cap: 3** per specialist; the 3rd re-dispatch triggers a founder consult.

---

## meesell-services-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell (worktrees under /tmp/mesell-wt/ included). DO NOT read/write outside.
SESSION: mesell-microservices-category-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md (THIS plan — esp. F3 ai_ops vendoring + SHARED budget brake, F5 PRIMITIVE_VALUES)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.B/§2.D/§2.E (Valkey namespacing)/§3.A/§3.C/§5; D6 line 221 (ai_ops vendored); D7 line 328 (mw vendored + local JWT)
- docs/BACKEND_ARCHITECTURE.md §9 (category contract) + §6A (ai_ops layer) + §16.G (call-site preservation)
- backend/app/modules/category/{service,picker,repository,domain,exceptions}.py (as-built)
- backend/app/ai_ops/{client,budget_cap,cost_tracker,guardrail,prompt_registry}.py + prompts/smart_picker_v1.py (the vendoring source)
- backend/app/i18n/schema_contract.py (PRIMITIVE_VALUES :175 — the zero-drift lock)
- .claude/agent-memory/meesell-services-builder/MEMORY.md

## Your mission
Extract the `category` module from the monolith into backend/services/svc-category/.
Move service.py + picker.py + repository.py + domain.py + exceptions.py VERBATIM.
VENDOR (byte-identical copies) the trimmed ai_ops path (client, budget_cap,
cost_tracker, guardrail, prompt_registry, eval, metrics + ONLY prompts/smart_picker_v1.py),
the 6-middleware chain, core/{auth,cache,plan_guard,errors,tenancy,metrics}, the i18n
contract lib (schema_contract + messages_en subset + resolver + primitive_classifier),
and shared/{database,config,valkey}. Build the standalone main.py: 6-mw chain (CORS →
request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw), local JWT
validation (D7 — JWT_SECRET from Secret Manager, NEVER call iam-svc), the 5 public routes
+ /internal/* shims mounted, /health + /metrics, and worker-startup cache pre-warm
(full-tree + top-100 schemas per §6.7).

THE TWO LOAD-BEARING INVARIANTS:
1. §16.G CALL-SITE PRESERVATION — the ai_ops import path stays `from app.ai_ops import
   client as ai_client` (vendored package, same path); service.py:262 `call_gemini(ctx,
   "smart_picker.v1", ...)` is BYTE-IDENTICAL. Diff of service.py pipeline vs monolith
   shows ZERO call-site changes (only the package being vendored, not its import string).
2. SHARED BUDGET BRAKE (F3.c) — the vendored budget_cap.py + cost_tracker.py reach the
   SAME Valkey DB 0 and SAME audit_events DB as the monolith. The budget keyspace
   (`ai:cost:daily:{date}`, `ai:cost:pending:{date}`, `ai:budget:reservation:{id}`,
   `ai:cost:user:{user_id}:hourly:{hr}`) MUST NOT get the `category:` §2.E prefix —
   it stays GLOBAL/un-prefixed so the ₹500 cap is shared. category's OWN cache keys
   (smart_picker:{hash}, category_tree, schema:{id}, field_enum:{id}:{field}) DO get
   the `category:` prefix. This carve-out is in shared/valkey.py — apply the prefix
   only to the cache-DB-3 factory, NOT to the budget keys built by vendored ai_ops.

## Acceptance criteria
- [ ] service.py pipeline diff vs monolith = ZERO call-site changes (only vendoring).
- [ ] ai_ops vendored TRIMMED: only smart_picker_v1.py prompt (NOT autofill/watermark).
- [ ] Budget keyspace `ai:*` UN-prefixed (global); category cache keys `category:`-prefixed.
- [ ] Vendored budget_cap.py Lua scripts (_RESERVE_LUA, _RELEASE_LUA) byte-identical to source.
- [ ] cost_tracker writes audit_events via cross-schema INSERT (GRANT INSERT ON public.audit_events).
- [ ] Trimmed Settings carries GEMINI_*/LANGFUSE_*/AI_DAILY_BUDGET_INR/JWT_SECRET/DATABASE_URL@category/VALKEY_URL/CACHE_VERSION; NO openpyxl/celery/msg91/razorpay vars.
- [ ] picker.py travels as PURE code (imports no ai_ops — verify the monolith picker.py:69-72 import block is unchanged).
- [ ] NO scope_to_user anywhere (category is GLOBAL — §9.D); repository bound to schema `category`.
- [ ] 6-mw chain registered; local JWT (D7); /suggest carries @rate_limit(scope="smart_picker",limit=100,window=3600).
- [ ] Worker-startup cache pre-warm (full-tree + top-100 schemas) wired.

## Hard constraints
- DO NOT modify backend/app/modules/category/ during extraction (strangler — both coexist).
- DO NOT touch frontend/, k8s/, infra/terraform/ (infra lead owns manifests).
- DO NOT author outbound HTTP-shim clients — category has ZERO outbound domain calls (sub-plan §as-built "category as CALLER: ZERO").
- DO NOT prefix the `ai:*` budget keyspace with `category:` (breaks the global cap — R1).
- DO NOT re-shape the §5A.B envelope or PRIMITIVE_VALUES — vendor schema_contract read-only.

## Files you MAY touch
backend/services/svc-category/** ONLY (plus the sub-plan's "Rollback Log" if a rollback fires).

## Files you must NOT touch
backend/app/modules/category/**, backend/app/main.py, backend/app/ai_ops/**, backend/app/i18n/**, k8s/**, frontend/**, infra/**, scripts/build_template_schemas.py

## Final report format
Files created (count + paths); service.py pipeline diff-line-count vs monolith (target: vendoring only, zero call-site); confirmation `ai:*` keys un-prefixed + cache keys prefixed; budget_cap.py Lua byte-identical confirmation; PR-template-ready Test evidence.
```

---

## meesell-api-routes-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-category-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md (THIS plan — §F4 the two frozen /internal/* shims)
- backend/app/modules/category/router.py + schemas.py (as-built — 5 routes, ETag/304, flag guard)
- docs/BACKEND_ARCHITECTURE.md §9.B (5 endpoint contracts) + §5A.B (envelope)
- The MS-A frozen shim contract (sub-plan §F4 reproduces the two shapes verbatim — these are FROZEN, never rename/reshape)

## Your mission
(1) Move the 5 public category routes into backend/services/svc-category/app/router.py
    VERBATIM: GET /categories/suggest (rate_limit smart_picker 100/3600 + FEATURE_SMART_PICKER_ENABLED
    404 guard), GET /categories/browse, GET /categories (ETag/304), GET /categories/{id}/schema
    (ETag/304), GET /categories/{id}/field-enum/{name} (single-flight). All async, all
    Depends(get_current_user) + Depends(get_db). NO business logic inlined.
(2) Author backend/services/svc-category/app/internal_router.py with the 2 FROZEN shims:
       GET /internal/categories/{id}/schema       ← service.fetch_schema(id, db)
       GET /internal/categories/{id}/field-enum/{field} ← service.get_field_enum(id, field, db)
    Internal routes use service-to-service auth (forwarded JWT per §5.A), NOT the get_current_user
    UI flow. Return the EXACT frozen shapes (schema = §5A.B 7-key envelope; field-enum =
    {enum_entries:[{canonical,meesho,labels}],total,truncated}).
(3) DEFENSIVE shims (author only if Open Question resolves they are called over HTTP):
       GET /internal/categories/{id}/commission       ← service.get_commission(id, db)   [pricing-svc, MS-D, likely YES]
       GET /internal/categories/super-categories       ← service.list_super_categories(db) [customer-svc, MS-E, verify]
(4) Regenerate the standalone OpenAPI.

## Acceptance criteria
- [ ] 5 public routes mounted verbatim; ETag/304 logic + flag guard preserved.
- [ ] 2 frozen /internal/* shims return EXACT MS-A-frozen shapes (no rename, no reshape).
- [ ] Internal routes do NOT use get_current_user UI flow (service-to-service auth).
- [ ] No business logic inlined — handlers call service methods only.
- [ ] OpenAPI regenerated; public + internal endpoints present.
- [ ] commission/super-categories shims authored per Open Question resolution (default: author commission, hold super-categories).

## Hard constraints / MAY touch / must NOT touch / report
(same boundary + report shape as services-builder; scoped to router.py + internal_router.py + schemas.py)
Re-dispatch trigger: any /internal/* shape deviates from the MS-A frozen contract → re-dispatch quoting sub-plan §F4.
```

---

## meesell-database-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-category-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md (THIS plan — §as-built DB tables)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.D (schema-per-service) + §3.A line 187 (category schema = 4 GLOBAL tables)
- backend/alembic/ (current head f31c75438e61; chain 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61)
- backend/app/modules/category/repository.py:42-44 (the 3 ORM-imported tables) + :14 (field_aliases ref)
- .claude/agent-memory/meesell-database-builder/MEMORY.md

## Your mission
Author the schema-split Alembic migration moving the 4 GLOBAL category tables from
`public` to a dedicated `category` schema: categories, templates, field_enum_values,
field_aliases. Set version_table_schema="category" so svc-category's Alembic chain tracks
its own alembic_version inside the category schema. Write upgrade (ALTER TABLE ... SET
SCHEMA category, all 4) + tested downgrade (SET SCHEMA public). CRITICAL: the categories
table carries the pg_trgm GIN indexes (from migration a1b2c3d4e5f6) — verify they survive
the schema move (SET SCHEMA preserves indexes, but assert it: post-migration EXPLAIN ANALYZE
of a browse ILIKE must still show Bitmap Index Scan). The 3,772 leaf rows + 291 field-enum
blobs migrate intact. field_aliases moves for locality (seed-time consumer only — NOT read
by category-svc runtime, per the MS-A correction carried in §as-built).

## Acceptance criteria
- [ ] All 4 tables moved to schema `category`; upgrade + downgrade round-trip clean.
- [ ] pg_trgm GIN indexes survive (post-migration EXPLAIN shows Bitmap Index Scan on browse).
- [ ] version_table_schema="category"; alembic_version lands in category schema.
- [ ] No head divergence dev↔staging (apply dev FIRST — infra ordering rule; P0 if diverged).
- [ ] Row counts preserved (categories 3,772 leaves; field_enum_values 291 brand-pattern blobs).

## Hard constraints / MAY touch / must NOT touch / report
(boundary scoped to backend/services/svc-category/alembic/** + the migration file)
Re-dispatch trigger: head divergence dev↔staging → P0, escalate to founder; lost index → re-dispatch quoting §G4 pg_trgm pattern.
```

---

## meesell-category-picker-builder (verify-only, Phase B)

```
PROJECT BOUNDARY: as above. SESSION: mesell-microservices-category-backend-session-{N}
## Mission: verify the smart-picker ranking pipeline survives vendoring.
- Confirm picker.py (compress_tree, calibrate_confidence, select_top_k) is byte-identical post-vendor.
- Run the vendored ai_ops/eval.py Smart Picker golden set: top-5 recall ≥80% (the §6A locked floor).
- Confirm the call site service.py:262 call_gemini("smart_picker.v1", prompt_vars={description, compressed_tree}) is unchanged.
## Acceptance: golden recall ≥80%; zero picker logic drift; report recall number.
```

---

## Backend-lead integration test (Phase C — coordinator-authored)

`backend/services/svc-category/tests/test_category_extraction.py`:
- **Hybrid-mode**: 5 public routes respond in-process AND via svc-category pod.
- **PRIMITIVE_VALUES parity**: vendored `schema_contract.PRIMITIVE_VALUES` == monolith
  (11 values); `ENVELOPE_KEYS`==7, `FIELD_SHAPE_KEYS`==9, `DATA_TYPE_VALUES`==8,
  `COMPLIANCE_SHAPE_VALUES`==2, `ENUM_RESOLVER_VALUES`==3.
- **Envelope conformance**: every served `templates.schema_jsonb` has all 7 keys; every
  field all 9; every `primitive` ∈ the 11.
- **Budget-brake-shared**: a `check_and_reserve("smart_picker", ...)` from svc-category +
  one from the monolith both move the SAME `ai:cost:daily:{date}` counter (assert the
  `ai:*` keys are NOT `category:`-prefixed).
- **Vendoring parity**: `budget_cap._RESERVE_LUA`/`_RELEASE_LUA` byte-identical to source.
- **Frozen shim shapes**: `/internal/categories/{id}/schema` + `/field-enum/{field}` match
  the MS-A frozen shapes.

---

## Merge-gate checklist (lead, STEP 3 — real gate, can reject)

Per the backend.md PR template + sub-plan §Acceptance gate. Reject-class triggers:
- service.py call-site changed beyond vendoring → reject quoting §16.G.
- `ai:*` budget keys got the `category:` prefix → reject quoting F3.c R1 (breaks global cap).
- `/internal/*` shape deviates from MS-A frozen contract → reject quoting §F4.
- PRIMITIVE_VALUES / envelope drift → reject quoting §F5 (LIVE frontend).
- AI prompt other than smart_picker_v1 vendored → reject (trim violation).
- PR-template field left as `<placeholder>` → refuse to merge.
- Alembic head divergence dev↔staging → P0 founder escalation.
```
