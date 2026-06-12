# handoff_msF_infra.md — category-service infra surfaces (Session MS-F)

**FROM:** meesell-backend-coordinator
**TO:** meesell-infra-builder
**DATE:** 2026-06-12
**Status:** **DO NOT EXECUTE until MS-4 wave opens** (MS-3 = pricing + customer both
founder-gate-merged; category extracts in parallel with MS-G iam). This memo is the
infra surface inventory the infra lead turns into real `feature/microservices-category/infra`
commits AT MS-4. Dev cluster only — no staging/prod, no terraform beyond dev-scope manifests.
**Companion:** `docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md` (§F-infra),
`spec_msF_backend.md`. Mirrors the MS-A infra-handoff shape.

---

## Surfaces to author (placeholders backend provides → infra makes real)

### 1. Dockerfile — `backend/services/svc-category/Dockerfile`
- FROM python:3.12-slim. Installs `requirements.txt` (fastapi, sqlalchemy, asyncpg, redis,
  httpx, **google-genai**, langfuse — category HAS AI; NO openpyxl/celery — no XLSX/worker).
- No Celery worker process (category has no background tasks — unlike export/image).

### 2. K8s — `k8s/svc-category/`
- `deployment.yaml`: API replicas (read-heavy, cache-fronted — size per infra plan §6.3).
  **NO worker deployment** (category has no Celery tasks).
- **Cache pre-warm**: category is the HEAVIEST cache consumer (full-tree pre-warm +
  top-100 schemas pre-warm + single-flight on 291 brand-pattern enums — §6.7). Wire the
  pre-warm as a pod-startup step (init logic in the app's lifespan, OR an init step). The
  pod mounts **Valkey DB 3** (application cache) — confirm the DB-3 connection is reachable
  and the pre-warm runs before the pod reports ready.
- `service.yaml`: ClusterIP :8001.

### 3. Traefik IngressRoute
- `/api/v1/categories/*` → svc-category:8001 (the 5 public routes).
- `/internal/categories/*` → svc-category:8001 (the 2-3 `/internal/*` shims:
  schema, field-enum, + commission/super-categories per Open Question).
- **Cutover = route flip**: at category's cutover, these routes move from monolith-svc to
  svc-category. export-svc's already-built `category_client` (MS-A) + pricing-svc's
  `category_client` (MS-D) reach `/internal/categories/*` — the flip is transparent to
  their call sites (§16.G). Rollback = flip back to monolith-svc.

### 4. Postgres — schema + role + GRANTS (CRITICAL — two grants)
- `CREATE SCHEMA category;`
- `CREATE ROLE category_user ...; GRANT USAGE/SELECT ON ALL TABLES IN SCHEMA category TO category_user;`
  (category tables are READ-ONLY after seed — categories, templates, field_enum_values,
  field_aliases.)
- **`GRANT INSERT ON public.audit_events TO category_user;`** — the SHARED AI cost ledger.
  category-svc's vendored `cost_tracker.py` writes every AI call's committed cost to
  `public.audit_events` (cross-schema INSERT, F3.c). **Without this grant, the budget
  brake's cost-ledger write silently drops (cost_tracker drops-on-failure with WARNING) —
  the ₹500 cap would still enforce via Valkey but the audit trail breaks.** This mirrors
  the MS-A `GRANT INSERT ON public.audit_events TO export_user` pattern (§5.B).

### 5. Secret Manager bindings
- **`JWT_SECRET`** — the SAME secret iam-svc signs tokens with (D7 local-JWT — category
  validates locally, NEVER calls iam-svc per-request). MS-G (iam) extracts in the SAME
  wave; both services bind the same `JWT_SECRET`. This is what makes the parallel
  extraction safe — no request-path coupling.
- **`GEMINI_API_KEY`** — category's smart_picker workload calls Gemini via vendored ai_ops.
- **`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`** — ai_ops traces flow from the vendored
  `client.py` with `service="category"` tag (§5.F).
- `DATABASE_URL` @ schema `category`, `VALKEY_URL` (shared instance), `CACHE_VERSION`,
  `AI_DAILY_BUDGET_INR` (=500), `APP_ENV`.

---

## ⚠️ The Valkey budget-keyspace carve-out (infra MUST NOT namespace these)

MASTER_PLAN §2.E (line 209) locks per-service Valkey key namespacing (`{service_name}:`
prefix). **EXCEPTION — the AI budget brake keyspace stays GLOBAL/un-prefixed:**
- `ai:cost:daily:{YYYY-MM-DD}`        (committed spend — the ₹500 cap)
- `ai:cost:pending:{YYYY-MM-DD}`      (reserved headroom)
- `ai:budget:reservation:{id}`        (per-call 5-min reservation)
- `ai:cost:user:{user_id}:hourly:{hr}` (per-user accumulator)

These live in **Valkey DB 0** and are SHARED across all AI-consuming services
(category/catalog/image) so the ₹500 daily cap is ONE global counter. If infra's
namespacing config (or the one-off backfill script that re-prefixes existing keys at
extraction) prefixes the `ai:*` keys, the cap splits into N independent caps. **The
backend services-builder handles this in `shared/valkey.py` (prefix applied to the
cache-DB-3 factory only, not to the budget keys), but if infra runs a key-migration
backfill at cutover, EXCLUDE the `ai:*` keyspace from re-prefixing.** Category's OWN cache
keys (`smart_picker:{hash}`, `category_tree`, `schema:{id}`, `field_enum:{id}:{field}` in
DB 3) DO get the `category:` prefix — those are service-local.

---

## D3 VM checkpoint (per MS-PAR-1)

At MS-4 the deploy is monolith + export + dashboard + image + pricing + customer +
category + iam on the dev node. **This is the wave most likely to outgrow the
e2-standard-2 node.** The e2-standard-4 upgrade (~₹2,600/mo) is plan-pre-approved (D3) BUT
the SPEND gets a fresh founder ask at the moment the deploy doesn't fit. **STOP and ask
the founder before provisioning** — never on the plan-level pre-approval alone.

---

## Inter-lead request row

A row is added to `feature_board_backend.md` → "Inter-lead requests open" pointing at this
memo, marked gated-on-MS-4 (no SLA pressure until the wave opens).
