# Runbook — `svc-pricing` Rollback (Microservices Sub-Plan D)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan D — `pricing` module extraction (fourth extraction, §16.H order #4; MS-3 wave)
**Scope:** reverting the `pricing` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0D_pricing_extraction.md`, `handoff_msD_infra.md`, `SHIM_CONTRACT_pricing_callees.md`, and the proven `svc-export-rollback.md` / `svc-dashboard-rollback.md` (the MS-A/MS-B patterns this adapts).

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik / DB command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCES vs the earlier rollbacks:**
> - vs **svc-dashboard** (owns zero tables): pricing OWNS the `pricing` schema (`pricing_calcs`), so this rollback HAS a database step (Step 3 — copy any `pricing.pricing_calcs` rows back to the monolith table before dropping the schema, if the strangler window ever wrote real rows).
> - vs **svc-export** (Celery worker + multi-callee): pricing is DETERMINISTIC math (§0.3) — **NO Celery worker to tear down**, **NO ai_ops**, only TWO outbound shims (catalog + category) and ZERO inbound. The blast radius is small.

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan D is declared complete** (the 7-day hybrid-mode green window). Triggers:

- Hybrid-mode CI goes red on a contract surprise the strangler can't absorb — e.g. the catalog WIDENED ownership-check stops returning `category_id` (§0.6), or the category `get_commission` shim deserialises a `null`/float instead of the frozen `{commission_pct:"<decimal>"}` Decimal-string (`SHIM_CONTRACT_pricing_callees.md §2`).
- The frozen Decimal-string response contract drifts — a `json_encoders`/float regression that emits any of the 9 `PriceCalcResponse` Decimal fields as a number instead of a JSON string (the `T1` golden would catch this in CI, but if it lands at deploy it is a frontend-breaking contract surprise).
- The `FEATURE_PRICE_CALCULATOR_ENABLED` 404 kill-switch behaves differently in the extracted service than in the monolith (this is the ROUND-1 REJECT class — the trimmed Settings dropped the flag; the flag-parity guard now pins it, but watch for a staging env that sets it to a different default).
- The tight Traefik `PathRegexp(^/api/v1/products/[^/]+/price-calc$)` mis-routes — e.g. it captures a path it should not, or the price-calc POST 404s when the flag is on.
- The cross-schema audit INSERT to `public.audit_events` fails because the I5 grant (`INSERT ON public.audit_events TO pricing_user`) is missing or revoked.
- MS-3 wave overflows the current node (capacity — STOP and flag to founder, do NOT silently upgrade the VM per D3). pricing is a light contributor (50m, api-only, no worker).
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

Because pricing is a **leaf consumer** (nothing in the codebase imports `app.modules.pricing.*` cross-module; pricing CALLS catalog+category but is called by nothing), rollback is low-blast-radius: no other service depends on svc-pricing being up.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik (the POST) back to the monolith
Route `POST /api/v1/products/{id}/price-calc` back to the monolith. The monolith still has the in-process `pricing_router` mounted (it is NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Delete the svc-pricing IngressRoute so the host-only api Ingress
# (api.mesell.xyz → api:80, the monolith) reclaims the price-calc POST.
kubectl -n dev delete ingressroute svc-pricing
kubectl -n dev get ingressroute -o wide
```

**PATH-AWARE NOTE:** the svc-pricing IngressRoute matched ONLY the tight
`Host(\`api.mesell.xyz\`) && PathRegexp(\`^/api/v1/products/[^/]+/price-calc$\`)`.
No OTHER `/api/v1/products/...` route was captured by it (catalog create, image
upload, dashboard list all stayed on the monolith), so deleting this IngressRoute
affects ONLY the price-calc POST. There is nothing else to "restore."

> **TLS NOTE (cross-wave finding, carried to the founder gate):** svc-pricing's
> IngressRoute correctly references the LIVE secret `api-tls` (verified against the
> live cluster 2026-06-13). The sibling svc-image / svc-export IngressRoutes
> reference the NONEXISTENT `api-mesell-xyz-tls` — fix THEIR routes before their
> cutover. svc-pricing is unaffected.

### Step 2 — Shims: re-export the in-process services (1 line per callee)
Only needed if the monolith pricing module had been modified to delegate to svc-pricing (it was NOT in Sub-Plan D — both trees coexist untouched during the strangler window). For completeness, the §16.G contract guarantees a 1-line revert per callee: `core/extracted_clients/<callee>_client.py` re-exports the in-process `service.py` symbol instead of issuing HTTP. pricing's 2 outbound shims are `catalog.get_category_id` (the §0.6 widened-ownership replacement) + `category.get_commission` — but those are pricing CALLING OUT, served by the still-in-process catalog/category modules; the monolith's `pricing_router` itself was never pointed at a shim. During Sub-Plan D this step is a **no-op**.

### Step 3 — Database: copy-back then drop the `pricing` schema (pricing OWNS a table)
Unlike svc-dashboard, pricing owns the `pricing` schema (`pricing.pricing_calcs`). The monolith's in-process `pricing` module still writes to the original `public.pricing_calcs` (or its schema-split parent — confirm against the Alembic head) during the strangler window, so under normal coexistence the svc-pricing `pricing.pricing_calcs` may be empty or hold only svc-routed rows.

```sql
-- 3a. If svc-pricing wrote any rows during the window, copy them back to the
--     monolith's table BEFORE dropping (price-calc is idempotent/recomputable, so
--     this is usually a no-op — pricing_calcs is an audit-trail of computations,
--     not source-of-truth state; verify with product before deciding to copy).
INSERT INTO public.pricing_calcs SELECT * FROM pricing.pricing_calcs
  ON CONFLICT (id) DO NOTHING;   -- adjust column list / PK to the live schema

-- 3b. Drop the extracted schema + role grants.
DROP SCHEMA IF EXISTS pricing CASCADE;
-- The pricing_user role + its INSERT ON public.audit_events grant (I5) are harmless
-- and may stay (a service that no longer exists simply stops connecting). Drop for
-- hygiene only AFTER Step 4 confirms no svc-pricing pod is still connected:
--   DROP ROLE IF EXISTS pricing_user;
```

> The cross-schema audit rows (`pricing.calculated` in `public.audit_events`) are
> already in `public` (append-only, no FK) — they STAY; there is nothing to reverse
> there. Only the `pricing` schema's own table needs handling.

### Step 4 — Tear down the svc-pricing deployment
```bash
kubectl -n dev delete deployment svc-pricing-api          # api only (NO worker — pricing has no Celery)
kubectl -n dev delete service svc-pricing                 # ClusterIP
kubectl -n dev delete configmap svc-pricing-config        # trimmed flag/APP_ENV ConfigMap
kubectl -n dev delete secret svc-pricing-secrets          # trimmed secret (incl. dev-pricing-db-password)
kubectl -n dev delete ingressroute svc-pricing            # if not already removed in Step 1
# Postgres role/grant (I5) may stay — harmless (see Step 3). Drop only if desired.
```

### Step 5 — Re-run hybrid CI in pure in-process mode + log root cause
Run the monolith pricing tests to confirm the in-process path is green, then record the incident in the Rollback Log below.

```bash
cd backend && PYTHONPATH=. python -m pytest tests/modules/pricing -q
# (the monolith pricing suite — deterministic P&L math + the price-calc route +
#  the FEATURE_PRICE_CALCULATOR_ENABLED 404 guard, all in-process)
```

---

## 2. Post-rollback verification checklist

- [ ] `POST /api/v1/products/{id}/price-calc` serves from the monolith (Traefik no longer has a svc-pricing rule; the host-only api Ingress reclaims it).
- [ ] The 9-field `PriceCalcResponse` still emits Decimals as JSON STRINGS on the in-process path (frozen Decimal contract §1 — no float regression).
- [ ] The `FEATURE_PRICE_CALCULATOR_ENABLED` 404 kill-switch fires correctly on the in-process path (flag off ⇒ 404; flag on ⇒ 200).
- [ ] `pricing` schema handled per Step 3 (rows copied back if any; schema dropped); `public.audit_events` `pricing.calculated` rows UNCHANGED (they stay).
- [ ] Monolith pricing test suite green (in-process mode).
- [ ] No `svc-pricing` pods/services/configmaps/secrets/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan D authored 2026-06-13; no rollback has occurred)_ | | | | |
