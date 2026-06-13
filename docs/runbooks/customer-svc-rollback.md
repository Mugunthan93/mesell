# Runbook — `customer-svc` Rollback (Microservices Sub-Plan E)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan E — `customer` module extraction (MS-3 wave, parallel with MS-D `pricing`; §16.H order #4 among the callee services).
**Scope:** reverting the `customer` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0E_customer_extraction.md`, `handoff_msE_infra.md`, and the proven `svc-export-rollback.md` (MS-A) + `svc-dashboard-rollback.md` (MS-B) patterns this adapts.

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik / `alembic` command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCES vs the leaf-consumer rollbacks (export/dashboard):**
> 1. customer **OWNS a table** (`seller_profile`, schema-split `public` → `customer` by migration `a9f3b2c5e1d8`), so this rollback HAS a database step (`alembic downgrade` → `SET SCHEMA public` + re-add the severed FK).
> 2. customer is a **PROVIDER, not a leaf** — three callers depend on it: the **monolith `catalog`** (reverse shim, this PR), **svc-export** (`get_compliance_block`), and **svc-dashboard** (`get_onboarding_completeness`). Rolling back customer-svc means re-pointing ALL THREE callers back at the in-process / monolith path.
> 3. customer has **NO Celery worker** — there is no worker teardown step.

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan E is declared complete** (the 7-day hybrid-mode green window). Triggers:

- Hybrid-mode CI goes red on a contract surprise the strangler can't absorb — e.g. a `ComplianceBlock` (10-field) / `ProfileCompleteness` (5-field) shim deserialization mismatch, or the eligibility 422 envelope (`customer.profile_incomplete_for_category`) failing to round-trip `super_id` / `missing_keys`.
- The schema-split migration `a9f3b2c5e1d8` corrupts or orphans data (the Risk#5 pre-scan should have aborted before this, but a post-migration integrity surprise is a P0).
- The OUTBOUND super-categories shim (FROZEN-0E, customer → category `GET /internal/super-categories → list[str]`) returns a non-`list[str]` shape (e.g. SUB_PLAN_0F MS-4 ships `list[SuperCategoryInfo]` against the frozen contract).
- A caller breaks: catalog `create_product` eligibility gate (`catalog/service.py:406`) or `get_preview` compliance block (`:839`) misbehaves through the reverse shim; or svc-export / svc-dashboard fail against customer-svc `/internal/*`.
- MS-3 wave overflows the current node (capacity — STOP and flag to founder, do NOT silently upgrade the VM). customer is small (api-only, ~50m/128Mi, query-light, no worker/AI).
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik back to the monolith
Route `/api/v1/seller-profile/*` (the 5 public routes) back to the monolith. The monolith still has the in-process `customer_router` mounted (`main.py:117` — NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Delete the svc-customer IngressRoute so the host-only api Ingress
# (api.mesell.xyz → api:80, the monolith) reclaims /api/v1/seller-profile/*.
kubectl -n dev delete ingressroute svc-customer
kubectl -n dev get ingressroute -o wide
```

### Step 2 — Callers: revert the THREE callers to the in-process / monolith path

**2a. Monolith `catalog` reverse shim (this PR's strangler change).**
If cutover had flipped the import at `catalog/service.py:99` to
`from app.core.extracted_clients import customer_client as customer_service`,
revert that ONE line back to
`from app.modules.customer import service as customer_service` (§16.G: 1-line revert; call sites at `:406` + `:839` are byte-for-byte unchanged either way).
**During Sub-Plan E (pre-cutover) this is a NO-OP** — the live import was never flipped; the reverse shim was built + hybrid-CI-tested only.

**2b. svc-export `customer_client` base URL.**
Re-point svc-export's `core/extracted_clients/customer_client` base URL from the customer-svc ClusterIP back to the **monolith** ClusterIP (config flip, infra lane — `handoff_msA_infra.md`). The monolith serves `/internal/seller-profile/{user_id}/compliance-block` once its in-process customer module is the live path again.

**2c. svc-dashboard `customer_client` base URL.**
Re-point svc-dashboard's `customer_client` base URL from customer-svc back to the monolith (config flip, infra lane — `handoff_msB_infra.md`). The monolith serves `/internal/seller-profile/{user_id}/onboarding-completeness`.

> NOTE: 2b/2c only apply once those services have been cut over to call customer-svc directly. During the MS-3 hybrid window they still call the monolith ClusterIP, so 2b/2c are NO-OPs too. They are listed so the FULL provider-rollback is documented for the cutover scenario.

### Step 3 — Database: downgrade the schema-split (customer OWNS `seller_profile`)
Reverse migration `a9f3b2c5e1d8` — `SET SCHEMA customer → public` and re-add the severed FK `fk_seller_profile_user_id` (→ `public.users.id`, `ON DELETE CASCADE`).

```bash
# Run from the svc-customer alembic root (version_table_schema="customer").
cd backend/services/svc-customer
alembic downgrade -1
# The downgrade:
#   1. ALTER TABLE customer.seller_profile SET SCHEMA public
#   2. ADD CONSTRAINT fk_seller_profile_user_id FOREIGN KEY (user_id)
#        REFERENCES public.users(id) ON DELETE CASCADE
# The GIN index idx_seller_profile_super_cats follows the table back to public.
```

> **DEV BEFORE STAGING — NEVER REVERSE.** Apply the downgrade to `dev` first; only touch `staging` after `dev` is confirmed clean. Head divergence dev↔staging is a P0 — escalate to founder.
> **PRE-CONDITION:** `public.users` must exist (the `users` table is NEVER extracted — it stays in the monolith), so the FK re-add is always satisfiable.

### Step 4 — Tear down the svc-customer deployment
```bash
kubectl -n dev delete deployment svc-customer-api      # api only (NO worker — customer has no Celery)
kubectl -n dev delete service svc-customer             # ClusterIP
kubectl -n dev delete configmap svc-customer-config    # trimmed flag/APP_ENV ConfigMap
kubectl -n dev delete secret svc-customer-secrets      # trimmed secret (DATABASE_URL@customer, JWT_SECRET, VALKEY_URL)
kubectl -n dev delete ingressroute svc-customer        # if not already removed in Step 1
# The customer_user Postgres role + its grants on the `customer` schema +
# INSERT ON public.audit_events may stay (harmless) OR be dropped for hygiene
# AFTER confirming no svc-customer pod is still connected.
```

### Step 5 — Re-run hybrid CI in pure in-process mode + log root cause
Run the monolith customer tests to confirm the in-process path is green, then record the incident in the Rollback Log below. The hybrid CI mode reverts to pure in-process (the shim env var / mode flag selecting HTTP-vs-in-process is set back to in-process — see `CI_HYBRID_MODE_customer` if present, else the MS-A `CI_HYBRID_MODE_export` pattern).

```bash
cd backend && PYTHONPATH=. python -m pytest \
  tests/modules/customer tests/integration -k customer \
  tests/test_customer_extraction.py -q
```

---

## 2. Post-rollback verification checklist

- [ ] The 5 public `/api/v1/seller-profile/*` routes serve from the monolith (Traefik no longer has a svc-customer rule; the host-only api Ingress reclaims them).
- [ ] The 3 PATCH routes still write an audit row to `public.audit_events` (`@audit_event` preserved on the in-process path).
- [ ] catalog `create_product` eligibility gate (`assert_eligible_for_super_id`) fires correctly on the in-process path (eligible ⇒ proceeds; missing compulsory key ⇒ 422 `customer.profile_incomplete_for_category`).
- [ ] catalog `get_preview` compliance block (`get_compliance_block`) returns the 10-field block in-process (404 `customer.profile_not_found` when absent).
- [ ] svc-export + svc-dashboard (if cut over) resolve the customer `/internal/*` contracts against the monolith ClusterIP again.
- [ ] `seller_profile` is back in `public` schema with the `fk_seller_profile_user_id` FK restored and the GIN index intact (`\d+ public.seller_profile`).
- [ ] Monolith customer test suite + `tests/test_customer_extraction.py` green (in-process / reverse-shim-mock mode).
- [ ] No `svc-customer` pods/services/configmaps/secrets/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan E authored 2026-06-12; MS-3 execution 2026-06-13; no rollback has occurred)_ | | | | |
