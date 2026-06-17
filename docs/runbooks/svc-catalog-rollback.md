# Runbook — `svc-catalog` Rollback (Microservices Sub-Plan H — THE SPINE)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan H — `catalog` module extraction (MS-5 wave; the LAST + RISKIEST extraction, runs ALONE after MS-4).
**Scope:** reverting the `catalog` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0H_catalog_extraction.md`, `handoff_msH_infra.md`, and the proven `svc-category-rollback.md` / `svc-pricing-rollback.md` / `svc-export-rollback.md` (the MS-F/MS-D/MS-A patterns this adapts).

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik / DB command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCES vs every earlier rollback (catalog is THE SPINE — the most coupled service):**
> - **catalog is BOTH a CALLEE and a CALLER, with a 4-SURFACE internal route flip.** 4 already-extracted services dial catalog's `/internal/products/*` shims: image-svc + pricing-svc + export-svc (ownership-check + export-snapshot) and dashboard-svc (list-products). Rolling back catalog means the `/internal/products/*` routes must flip BACK to the monolith, and those 4 callers' `catalog_client` shims must resolve in-process again (§16.G — 1-line revert each, but VERIFY all 4 reach the monolith, not a dead svc-catalog). catalog ALSO CALLS OUT to category-svc (×3) + customer-svc (×2) — rollback does NOT touch those callees (they keep serving the monolith's in-process catalog module the same way).
> - **catalog OWNS 3 READ-WRITE tenant-scoped tables** (catalogs, products, product_drafts) MOVED into the `catalog` schema by migration `a8f3b2e9c1d5`. *** UNLIKE category (read-only tables), catalog's tables hold LIVE TENANT DATA that is being MUTATED *** (autosave writes product_drafts continuously; create/patch/delete mutate products/catalogs). Rollback REVERSES the move (`alembic downgrade`) — it does NOT `DROP SCHEMA`. **Read Step 3 carefully — this is the SINGLE riskiest rollback step in the entire migration: there is live write traffic on these tables during the strangler window.**
> - **catalog IS AI-consuming (autofill).** Rollback must verify (a) the GLOBAL budget-brake keyspace (`ai:*` in Valkey DB 0) is UNTOUCHED (it is global/shared across category+catalog+image — rollback must NOT flush or re-prefix it; MS-5 is the LAST AI extraction so all 3 AI workloads share this one keyspace), and (b) the audit grant covering TWO writers (cost_tracker AI cost + audit_mw write-route rows) is the only audit surface — no PII.
> - **THE METHOD-SPLIT.** catalog claims ONLY `POST /api/v1/products`; `GET /api/v1/products` is svc-dashboard's. Deleting catalog's IngressRoute returns the POST half to the monolith; the GET half stays on svc-dashboard untouched. Verify the method-split unwinds cleanly (Step 1 note).

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan H is declared complete** (the 7-day hybrid-mode green window). Triggers:

- The autosave write path regresses — `PATCH /api/v1/products/{id}` (the keystroke-debounced autosave) drops/corrupts a product_draft, or the autosave P95 blows the budget (the backend integration test asserts autosave P95 — `tests/test_catalog_extraction.py`).
- A `/internal/products/{id}/ownership-check` or `/export-snapshot` shim returns a non-frozen shape (the MS-A-FROZEN contract — `spec_msA_backend.md §5`), breaking image-svc/pricing-svc/export-svc's already-built `catalog_client`.
- The `export-snapshot` 2-hop chain breaks: catalog-svc's `/internal/products/{id}/export-snapshot` internally calls category-svc's `/internal/categories/{id}/schema` (the nested outbound, `service.py:962`) — if that chain exceeds the §5.E timeout budget or category-svc is unreachable, export breaks. (The chain only fires on export, not on the autosave hot path.)
- The autofill Gemini seam mis-behaves OR the budget-brake carve-out is violated — the `ai:cost:*` / `ai:budget:*` keys got `catalog:`-prefixed (splitting the ₹500 global cap into N caps). **This is a P0** — the cap stops working globally across category+catalog+image. Verify the carve-out (§2 checklist) and roll back if it landed wrong.
- The cross-schema audit INSERT to `public.audit_events` fails because the I5 grant (`INSERT ON public.audit_events TO catalog_user`) is missing/revoked → BOTH the AI cost ledger (cost_tracker) AND the 4 write-route audit_mw rows silently drop (cost_tracker drops-on-failure with WARNING).
- The `FEATURE_CATALOG_FORM_ENABLED` mount guard dropped → catalog routes mount unconditionally in a flag-off env (R9, row-26 lesson). The merge-gate verifies mounted-route count with the flag ON; if it landed wrong, the app serves routes it should 404.
- **MS-5 wave overflows the node** (capacity — catalog is the LARGEST pool, 2×150m=300m; the COMBINED 8-service footprint is what could overflow). **STOP and flag to founder, do NOT silently upgrade the VM per D3.** (This is the documented D3 upgrade moment — see handoff §3 + the deployment.yaml D3 block.)
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik (public + internal) back to the monolith
Delete the svc-catalog IngressRoute so the host-only api Ingress (api.mesell.xyz → api:80, the monolith) reclaims catalog's public routes (the 6 catalog routes — POST /products + the 5 {id} sub-routes) AND the `/internal/products/*` shims. The monolith still has the in-process catalog_router (behind FEATURE_CATALOG_FORM_ENABLED) + the in-process `/internal/*` handlers mounted (NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Delete the svc-catalog IngressRoute. Its leaf-anchored rules
# (POST /api/v1/products; PATCH|DELETE /products/{id}; /{id}/autofill|preview|draft;
#  /internal/products + /internal/products/{id}/{ownership-check|export-snapshot|
#  validation-summary}) are all catalog-specific — NO sibling sub-route
# (/{id}/images, /{id}/price-calc, /{id}/export-xlsx) and NO GET /api/v1/products
# (svc-dashboard's) was captured, so deleting it affects ONLY catalog's surface.
kubectl -n dev delete ingressroute svc-catalog
kubectl -n dev get ingressroute -o wide
```

**METHOD-SPLIT NOTE:** catalog's IngressRoute claimed ONLY `POST /api/v1/products` (via `Method(\`POST\`) && Path(\`/api/v1/products\`)`). `GET /api/v1/products` (list) is svc-dashboard's, served by svc-dashboard's OWN IngressRoute — deleting catalog's route does NOT touch it. After the delete, `POST /api/v1/products` returns to the monolith; `GET /api/v1/products` stays on svc-dashboard. Verify both:

```bash
# POST should reach the monolith (catalog create) after the flip:
kubectl -n dev exec deploy/api -- curl -fsS -o /dev/null -w "%{http_code}\n" \
  -X POST "http://localhost:8000/api/v1/products" -H "Authorization: Bearer <test-jwt>" || true
# GET should STILL reach svc-dashboard (unchanged):
kubectl -n dev get ingressroute svc-dashboard -o yaml | grep -A2 "Method(\`GET\`)" || true
```

**SIBLING-PATH NOTE:** catalog's `{id}` rules were `$`-anchored leaf rules (`^/api/v1/products/[^/]+$` for the bare PATCH/DELETE; `…/autofill$`, `…/preview$`, `…/draft$` for the sub-routes) so they never captured `/{id}/images` (svc-image), `/{id}/price-calc` (svc-pricing), `/{id}/export-xlsx` (svc-export). Those keep flowing to their own services — nothing to restore.

> **TLS NOTE:** svc-catalog's IngressRoute correctly references the LIVE secret `api-tls` (per the svc-pricing/svc-category finding). No TLS action on rollback — deleting the route returns the path to the monolith's existing `api-tls`-served host Ingress.

### Step 2 — Shims: confirm ALL 4 callers reach the in-process catalog module
catalog is a CALLEE with 4 callers. After Step 1's route flip, `/internal/products/*` resolves to the MONOLITH again, so the callers' HTTP shims keep working transparently (§16.G — the route flip is the mechanism; their call sites are byte-identical). **VERIFY each of the 4 live callers still gets a valid response:**

```bash
# ownership-check — callers: image-svc, pricing-svc, export-svc
kubectl -n dev exec deploy/svc-image-api -- \
  curl -fsS -o /dev/null "http://api.mesell.xyz/internal/products/<known-product-id>/ownership-check" && echo "ownership-check OK (monolith) via image-svc"
kubectl -n dev exec deploy/svc-pricing-api -- \
  curl -fsS -o /dev/null "http://api.mesell.xyz/internal/products/<known-product-id>/ownership-check" && echo "ownership-check OK (monolith) via pricing-svc"
# export-snapshot (2-hop → category) — caller: export-svc
kubectl -n dev exec deploy/svc-export-api -- \
  curl -fsS -o /dev/null "http://api.mesell.xyz/internal/products/<known-product-id>/export-snapshot" && echo "export-snapshot OK (monolith, 2-hop) via export-svc"
# list-products — caller: dashboard-svc
kubectl -n dev exec deploy/svc-dashboard-api -- \
  curl -fsS -o /dev/null "http://api.mesell.xyz/internal/products?page=1&limit=20" && echo "list-products OK (monolith) via dashboard-svc"
```

If the monolith's in-process catalog module was modified to DELEGATE to svc-catalog (it was NOT in Sub-Plan H — both trees coexist untouched during the strangler window), the §16.G contract guarantees a 1-line revert PER caller: `core/extracted_clients/catalog_client.py` re-exports the in-process `catalog/service.py` symbol instead of issuing HTTP. During Sub-Plan H this is a **no-op** (the monolith catalog module was never pointed at a shim).

### Step 3 — Database: REVERSE the schema move (catalog OWNS 3 READ-WRITE tables — do NOT drop)
**THE SINGLE RISKIEST STEP IN THE MIGRATION.** Unlike category (read-only tables) and pricing (a recomputable audit table), catalog's 3 tables hold LIVE TENANT DATA that is being WRITTEN during the strangler window: `catalogs` + `products` (create/patch/delete) and `product_drafts` (continuous keystroke-debounced autosave). They have cross-schema FKs from/to users (iam) and categories (category). **DO NOT `DROP SCHEMA catalog CASCADE`** — that would delete live seller catalogs, products, and unsaved drafts.

Instead, REVERSE the schema-move migration (move the 3 tables BACK to `public`):

```bash
# FIRST — quiesce writes: scale svc-catalog-api to 0 so no new autosave/create
# lands mid-downgrade (the monolith still serves catalog in-process after Step 1's
# flip, so quiescing the SVC pods does not stop catalog from working — traffic is
# already on the monolith).
kubectl -n dev scale deployment/svc-catalog-api --replicas=0

# Run the reverse of migration a8f3b2e9c1d5 (documented downgrade: 3× ALTER TABLE
# catalog.<t> SET SCHEMA public, in reverse FK order: product_drafts, products,
# catalogs). Run as the superuser/migrator (SET SCHEMA needs ownership). The
# monolith reads/writes these tables from `public` — after downgrade they are back
# where the in-process module expects them.
#   Option A — from a one-off migrator pod / the monolith image against the catalog
#   Alembic chain head a8f3b2e9c1d5:
kubectl -n dev exec deploy/api -- sh -c \
  'cd /app && DATABASE_URL="$CATALOG_MIGRATOR_URL" alembic -c backend/services/svc-catalog/alembic.ini downgrade -1'
# (CATALOG_MIGRATOR_URL = superuser DSN on the meesell DB; the catalog Alembic env
#  tracks version in catalog.alembic_version — version_table_schema="catalog".)
```

After downgrade, verify the 3 tables are back in `public` and row counts are intact (no data loss):

```bash
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -c "\dt public.catalogs public.products public.product_drafts"
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -c \
  "SELECT 'catalogs' t, count(*) FROM public.catalogs
   UNION ALL SELECT 'products', count(*) FROM public.products
   UNION ALL SELECT 'product_drafts', count(*) FROM public.product_drafts;"
# Expect: tables present in public; counts MATCH the pre-rollback snapshot (take one
# BEFORE Step 3 — see §2 checklist).
```

> **DATA-SAFETY GATE:** take a row-count snapshot of all 3 tables (in the `catalog` schema) IMMEDIATELY BEFORE Step 3, and confirm the post-downgrade `public` counts match exactly. The downgrade is a metadata-only `SET SCHEMA` (PostgreSQL moves the table object, preserving all rows + indexes + FK objects) — it does NOT copy or delete data, so counts MUST be identical. A mismatch means something else touched the tables; STOP and investigate before declaring rollback complete.

### Step 4 — Verify the AI budget-brake carve-out is UNTOUCHED (P0 check)
catalog is the LAST AI extraction — after it, all 3 AI workloads (smart_picker=category, autofill=catalog, watermark=image) share the ONE global `ai:*` keyspace in Valkey DB 0. Rollback must NOT flush or re-prefix it (else the ₹500 cap splits/resets globally).

```bash
# Confirm the GLOBAL brake keys are present + UN-prefixed (NOT `catalog:`-prefixed):
kubectl -n dev exec deploy/api -- python3 -c "
import redis, os
r = redis.from_url(os.environ['VALKEY_URL'].rsplit('/',1)[0] + '/0')
keys = [k.decode() for k in r.keys('ai:*')]
bad  = [k.decode() for k in r.keys('catalog:ai:*')]
print('global ai:* keys:', keys[:5], '... total', len(keys))
print('MISPREFIXED catalog:ai:* keys (MUST be empty):', bad)
assert not bad, 'P0: ai:* keyspace got catalog:-prefixed — the global cap is split!'
print('budget-brake carve-out OK — ai:* keyspace is global/un-prefixed')
"
```
Do NOT `FLUSHDB` DB 0 — that would wipe the live brake counter AND the OTP store (shared DB 0). If the carve-out is the ONLY problem, the fix is a forward fix in the vendored ai_ops prefix config, not a flush.

### Step 5 — Tear down the svc-catalog k8s objects (optional, after data is safe)
Once Steps 1-4 confirm traffic + data + brake are back on the monolith, remove the svc-catalog Deployment/Service/Config/Secret (the IngressRoute was already deleted in Step 1):

```bash
kubectl -n dev delete deployment svc-catalog-api          # already scaled to 0 in Step 3
kubectl -n dev delete service svc-catalog
kubectl -n dev delete configmap svc-catalog-config
kubectl -n dev delete secret svc-catalog-secrets
# The `catalog` schema + catalog_user role are now EMPTY (tables moved back to
# public in Step 3). Leave them (idempotent re-create on a retry) OR drop the EMPTY
# schema + role if doing a clean teardown:
#   DROP SCHEMA IF EXISTS catalog;   -- safe ONLY after Step 3 moved the 3 tables out
#   DROP ROLE IF EXISTS catalog_user;
# *** NEVER DROP SCHEMA catalog CASCADE while the 3 tables are still in it. ***
```

### Step 6 — Re-point the deploy pipeline + record
- Ensure the next deploy does NOT re-create the svc-catalog IngressRoute (comment it out of the apply set, or gate it behind the cutover flag) until the fix-forward lands.
- Record the rollback in `STATUS_INFRA.md` (the deploy-window operator owns this) + flip the catalog feature-board row to BLOCKED with the trigger.

---

## 2. Pre-rollback checklist (run BEFORE Step 3)

- [ ] Snapshot the 3 catalog-table row counts (in the `catalog` schema) — the DATA-SAFETY GATE for Step 3.
- [ ] Confirm the monolith still has the in-process catalog module mounted (FEATURE_CATALOG_FORM_ENABLED=true on the monolith api) — it serves catalog after the Step 1 flip.
- [ ] Confirm all 4 callers (image/pricing/export/dashboard) are healthy pods (they will re-resolve `/internal/products/*` to the monolith after Step 1).
- [ ] Confirm the `ai:*` budget-brake keyspace is global/un-prefixed (Step 4 check) — do this BEFORE rollback too, to know the baseline.
- [ ] Confirm the `dev-catalog-db-password` SM secret + `catalog_user` role exist (a partial-deploy rollback may not have created them — skip the DB step if the schema move never ran).

---

## 3. Rollback decision tree (quick reference)

| Symptom | Step(s) | Notes |
|---|---|---|
| Public catalog routes 5xx / wrong shape | 1 | route flip back to monolith; method-split unwinds (POST→monolith, GET stays on dashboard) |
| A caller's `/internal/*` shim breaks | 1 → 2 | flip + verify all 4 callers reach the monolith |
| export-snapshot 2-hop chain times out | 1 → 2 | the chain (catalog→category) only fires on export; flip catalog back, category-svc unaffected |
| `ai:*` keyspace mis-prefixed (cap split) | 4 (forward-fix) | P0; do NOT flush DB 0; fix the vendored prefix config |
| audit INSERT failing | 1 (flip) + re-grant | re-run schema-role.sql §5 grant; both writers (cost_tracker + audit_mw) depend on it |
| Autosave corrupting drafts | 1 → 3 | flip + REVERSE the schema move (data-safety gate); product_drafts hold live unsaved work |
| Node overflow (capacity) | STOP → founder | D3 upgrade ask — do NOT silently provision (constraint §4) |

---

## 4. What this rollback does NOT do

- It does NOT touch the category-svc or customer-svc callees (catalog's OUTBOUND targets) — they keep serving the monolith's in-process catalog the same way.
- It does NOT flush Valkey (neither DB 0 brake/OTP nor DB 3 cache) — the global brake is shared + load-bearing.
- It does NOT drop the 3 tables — it MOVES them back to `public` (metadata-only SET SCHEMA, all rows preserved).
- It does NOT modify the monolith code — both modes coexist during the strangler window; the flip is the only mechanism.
