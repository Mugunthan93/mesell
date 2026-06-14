# Runbook — `svc-category` Rollback (Microservices Sub-Plan F)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan F — `category` module extraction (MS-4 wave; parallel with MS-G iam)
**Scope:** reverting the `category` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0F_category_extraction.md`, `handoff_msF_infra.md`, and the proven `svc-pricing-rollback.md` / `svc-export-rollback.md` / `svc-dashboard-rollback.md` (the MS-D/MS-A/MS-B patterns this adapts).

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik / DB command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCES vs the earlier rollbacks (category is the most coupled so far):**
> - **category is a CALLEE, not a leaf.** export-svc + pricing-svc (already pods at MS-4) dial category's `/internal/*` shims; at MS-5 catalog joins them. So rolling back category means the route for `/internal/categories/*` must flip BACK to the monolith, and those callers' `category_client` shims must resolve in-process again (§16.G — 1-line revert each, but VERIFY they reach the monolith, not a dead svc-category).
> - **category OWNS 4 read-only tables** (categories, templates, field_enum_values, field_aliases) MOVED into the `category` schema by migration `c4f1e7a9d302` (ALTER TABLE ... SET SCHEMA). Rollback REVERSES the move (`alembic downgrade`), it does NOT just `DROP SCHEMA` — the tables hold real seed data and have cross-schema FKs from `public.catalogs`/`public.products`. **Read Step 3 carefully — this is the riskiest rollback step in the migration so far.**
> - **category IS AI-consuming + the HEAVIEST cache consumer.** Rollback must verify (a) the GLOBAL budget-brake keyspace (`ai:*` in Valkey DB 0) is UNTOUCHED (it is global/shared — rollback must NOT flush or re-prefix it), and (b) the monolith's category cache pre-warm is intact (the monolith never stopped pre-warming during the strangler window, so this is usually a no-op).

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan F is declared complete** (the 7-day hybrid-mode green window). Triggers:

- Hybrid-mode CI goes red on a contract surprise the strangler can't absorb — e.g. a `/internal/categories/{id}/schema` shim returns a non-frozen envelope (the §F5 PRIMITIVE_VALUES zero-drift contract — 11/7/9 cardinalities — drifts), breaking export-svc/catalog's already-built `category_client`.
- The PRIMITIVE_VALUES / ENVELOPE_KEYS frozensets in the vendored `schema_contract` drift from the monolith source (the `test_primitive_values_parity` / `test_*_vendoring_parity` golden would catch this in CI; if it lands at deploy it is a **frontend-breaking** contract surprise — the live Angular wizard renders fields off the `primitive` value of each schema field, §F5).
- The `get_commission` `/internal/*` shim deserialises wrong for pricing-svc's already-built `category_client` (pricing is ALREADY a pod and dials category at MS-4 — a commission-shape regression breaks live price-calc).
- The Smart Picker golden eval drops below 80% top-5 recall on the extracted service (the smart_picker ranking pipeline mis-ranks post-extraction).
- The budget-brake carve-out is violated — the `ai:cost:*` / `ai:budget:*` keys got `category:`-prefixed (splitting the ₹500 global cap into N caps). **This is a P0** — the cap stops working globally. Verify the carve-out (§2 checklist) and roll back if it landed wrong.
- The cross-schema audit INSERT to `public.audit_events` fails because the I5 grant (`INSERT ON public.audit_events TO category_user`) is missing or revoked → the AI cost ledger silently drops rows (cost_tracker drops-on-failure with WARNING).
- The cache pre-warm wedges the pod (the lifespan pre-warm of the full 3,772-leaf tree + top-100 schemas + 291 brand enums never completes → readiness never goes green → no traffic served). Watch the readiness `initialDelaySeconds: 30` budget; if the pre-warm genuinely needs longer, that is a tune-forward (bump the probe), but a HANG is a rollback trigger.
- MS-4 wave overflows the current node (capacity — STOP and flag to founder, do NOT silently upgrade the VM per D3). category is a 100m api-only contributor; the COMBINED MS-4 footprint is what could overflow.
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik (public + internal) back to the monolith
Delete the svc-category IngressRoute so the host-only api Ingress (api.mesell.xyz → api:80, the monolith) reclaims BOTH the public `/api/v1/categories/*` routes AND the `/internal/categories/*` shims. The monolith still has the in-process `category_router` + the in-process `/internal/*` handlers mounted (NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Delete the svc-category IngressRoute. Its two PathPrefix rules
# (/api/v1/categories + /internal/categories) are category-EXCLUSIVE — no other
# service's route was captured by it, so deleting it affects ONLY category's
# surface (public + internal). The monolith host-Ingress reclaims both.
kubectl -n dev delete ingressroute svc-category
kubectl -n dev get ingressroute -o wide
```

**PATH-AWARE NOTE:** the svc-category IngressRoute matched ONLY `Host(\`api.mesell.xyz\`) && PathPrefix(\`/api/v1/categories\`)` and `PathPrefix(\`/internal/categories\`)`. No `/api/v1/products/...` route (catalog/image/export/pricing/dashboard) was captured by it, so deleting this IngressRoute affects ONLY category's paths. There is nothing else to "restore."

> **TLS NOTE:** svc-category's IngressRoute correctly references the LIVE secret `api-tls` (per the svc-pricing finding 2026-06-13). No TLS action on rollback — deleting the route returns the path to the monolith's existing `api-tls`-served host Ingress.

### Step 2 — Shims: confirm callers reach the in-process category module
category is a CALLEE. Its callers — export-svc, pricing-svc (both pods at MS-4), and at MS-5 catalog-svc — dial `/internal/categories/*` via their `category_client`. After Step 1's route flip, `/internal/categories/*` resolves to the MONOLITH again, so the callers' HTTP shims keep working transparently (§16.G — the route flip is the mechanism; their call sites are byte-identical). **VERIFY** each live caller still gets a valid response:

```bash
# From inside a caller pod (or via the gateway), confirm the internal shims serve
# from the monolith after the flip. Example (schema shim — export-svc + catalog):
kubectl -n dev exec deploy/svc-export-api -- \
  curl -fsS "http://api.mesell.xyz/internal/categories/<known-cat-id>/schema" >/dev/null && echo "schema shim OK (monolith)"
# Commission shim (pricing-svc — ALREADY a pod, dials this at MS-4):
kubectl -n dev exec deploy/svc-pricing-api -- \
  curl -fsS "http://api.mesell.xyz/internal/categories/<known-cat-id>/commission" >/dev/null && echo "commission shim OK (monolith)"
```

If the monolith's in-process `category` module was modified to DELEGATE to svc-category (it was NOT in Sub-Plan F — both trees coexist untouched during the strangler window), the §16.G contract guarantees a 1-line revert: `core/extracted_clients/category_client.py` re-exports the in-process `category/service.py` symbol instead of issuing HTTP. During Sub-Plan F this is a **no-op** (the monolith category module was never pointed at a shim).

### Step 3 — Database: REVERSE the schema move (category OWNS 4 tables — do NOT drop)
**This is the riskiest step.** Unlike pricing (which `DROP SCHEMA`s a recomputable audit table), category's 4 tables hold REAL SEED DATA (categories, templates, field_enum_values, field_aliases — the 3,772-leaf tree + schema envelopes the live frontend renders off) and have cross-schema FKs from `public.catalogs.category_id` and `public.products.category_id`. **DO NOT `DROP SCHEMA category CASCADE`** — that would delete the tables the running monolith still reads.

Instead, REVERSE the schema-move migration (move the 4 tables BACK to `public`):

```bash
# Run the reverse of migration c4f1e7a9d302 (it has a documented downgrade that does
# the 4× ALTER TABLE category.<t> SET SCHEMA public). Run as the superuser/migrator
# (the migration uses SET SCHEMA which needs ownership). The monolith reads these
# tables from `public` — after downgrade they are back where the in-process module
# expects them.
kubectl -n dev exec deploy/svc-category-api -- alembic downgrade -1
# (or, if the svc-category pod is already gone, run from a one-off migrator pod /
#  the monolith image against the category Alembic chain head c4f1e7a9d302.)
```

```sql
-- VERIFY the 4 tables are back in public and the cross-schema FKs resolve:
--   \dt public.categories   public.templates   public.field_enum_values   public.field_aliases   -- all present in public
--   \dt category.*           -- empty (only alembic_version may remain)
--   SELECT conname, conrelid::regclass FROM pg_constraint
--     WHERE confrelid = 'public.categories'::regclass;   -- catalogs/products FKs resolve to public.categories
```

> **Cross-schema FK safety:** during the strangler window the FKs `public.catalogs.category_id → category.categories.id` and `public.products.category_id → category.categories.id` were cross-schema but VALID (PostgreSQL supports cross-schema FKs in the same DB). The downgrade moves `categories` back to `public`, restoring same-schema FKs. No FK is dropped/recreated by the downgrade beyond the SET SCHEMA itself.

> **The cross-schema audit rows** (category AI-cost rows in `public.audit_events`) are already in `public` (append-only, no FK) — they STAY; nothing to reverse there.

Only AFTER Step 4 confirms no svc-category pod is connected, drop the now-empty schema + role for hygiene (optional):

```sql
DROP SCHEMA IF EXISTS category CASCADE;     -- ONLY after the 4 tables are confirmed back in public (Step 3 verify)
DROP ROLE IF EXISTS category_user;          -- harmless to leave; drop for hygiene only
```

### Step 4 — Tear down the svc-category deployment
```bash
kubectl -n dev delete deployment svc-category-api          # api only (NO worker — category has no Celery)
kubectl -n dev delete service svc-category                 # ClusterIP
kubectl -n dev delete configmap svc-category-config        # trimmed APP_ENV/CACHE_VERSION/flag ConfigMap
kubectl -n dev delete secret svc-category-secrets          # trimmed secret (incl. dev-category-db-password)
kubectl -n dev delete ingressroute svc-category            # if not already removed in Step 1
# Postgres role/grant (I5) may stay — harmless. Drop only after Step 3 (see above).
```

### Step 5 — AI / cache verification (category-specific)
```bash
# 5a. BUDGET-BRAKE CARVE-OUT — the GLOBAL ai:* keys MUST be UNTOUCHED + un-prefixed.
#     Rollback must NOT flush or re-prefix them (they are shared across monolith +
#     every AI service — the ₹500/day cap is ONE counter). Confirm the global keys
#     still exist un-prefixed and there is NO `category:ai:*` split-cap key:
kubectl -n dev exec valkey-0 -- valkey-cli -n 0 --scan --pattern 'ai:cost:*' | head
kubectl -n dev exec valkey-0 -- valkey-cli -n 0 --scan --pattern 'category:ai:*' | head  # MUST be EMPTY (no split cap)

# 5b. CATEGORY CACHE — the monolith's in-process category pre-warm is intact (it never
#     stopped during the strangler window). category's OWN DB-3 cache keys ARE
#     `category:`-prefixed; they can be left (the monolith re-populates) or flushed:
kubectl -n dev exec valkey-0 -- valkey-cli -n 3 --scan --pattern 'category:*' | head
#     Optional: bump the monolith CACHE_VERSION (k8s/config.yaml) to bust + re-warm.
```

### Step 6 — Re-run hybrid CI in pure in-process mode + log root cause
```bash
cd backend && PYTHONPATH=. python -m pytest tests/modules/category -q
# (the monolith category suite — smart picker ranking, schema/browse/tree/field-enum
#  routes, the /internal/* in-process handlers, the PRIMITIVE_VALUES parity, all
#  in-process)
```

---

## 2. Post-rollback verification checklist

- [ ] The 5 public `/api/v1/categories/*` routes serve from the monolith (Traefik no longer has a svc-category rule; the host-only api Ingress reclaims them).
- [ ] The 2-3 `/internal/categories/*` shims (schema, field-enum, commission, super-categories) serve from the monolith; export-svc + pricing-svc `category_client` calls succeed (§16.G — callers transparently reach the monolith).
- [ ] **PRIMITIVE_VALUES / envelope contract intact on the in-process path** (11/7/9 cardinalities — no frontend-breaking drift; the live Angular wizard renders correctly).
- [ ] **The 4 category tables are BACK in `public`** (Step 3 downgrade) — `categories`, `templates`, `field_enum_values`, `field_aliases` — and the cross-schema FKs from `public.catalogs`/`public.products` resolve same-schema again.
- [ ] `public.audit_events` category AI-cost rows UNCHANGED (they stay — append-only).
- [ ] **GLOBAL budget brake intact** — `ai:cost:*` / `ai:budget:*` keys in Valkey DB 0 are UNTOUCHED + un-prefixed; NO `category:ai:*` split-cap key exists (the §F3.b/c carve-out held).
- [ ] Monolith category cache pre-warm intact (monolith never stopped warming; `category:*` DB-3 keys present or re-populating).
- [ ] Monolith category test suite green (in-process mode); Smart Picker golden eval ≥80% top-5 recall in-process.
- [ ] No `svc-category` pods/services/configmaps/secrets/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan F authored 2026-06-14; no rollback has occurred)_ | | | | |
