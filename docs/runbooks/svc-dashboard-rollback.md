# Runbook — `svc-dashboard` Rollback (Microservices Sub-Plan B)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan B — `dashboard` module extraction (second extraction, §16.H order #2; MS-2 wave, parallel with MS-C `image`)
**Scope:** reverting the `dashboard` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0B_dashboard_extraction.md`, `handoff_msB_infra.md`, and the proven `svc-export-rollback.md` (MS-A pattern this adapts).

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCE vs svc-export rollback:** dashboard owns ZERO tables and has NO Celery worker, so this rollback is LIGHTER — there is **NO database/schema rollback step** (no `alembic downgrade`, no `SET SCHEMA`) and **NO worker teardown**. The audit grant (I5) is harmless and stays.

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan B is declared complete** (the 7-day hybrid-mode green window). Triggers:

- Hybrid-mode CI goes red on a contract surprise the strangler can't absorb (e.g. a `PaginatedProductsInternal` / `ProfileCompleteness` shim deserialization mismatch — §0.5).
- The method-aware Traefik split misfires — e.g. `POST /api/v1/products` (catalog create) is wrongly routed to svc-dashboard, or `GET /api/v1/products` 404s when the flag is on (R3, §13-DASHBOARD-D2).
- The `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 kill-switch behaves differently in the extracted service than in the monolith (R6 — un-gated in staging, or stuck-404 in dev).
- MS-2 wave overflows the current node (capacity — STOP and flag to founder, do NOT silently upgrade the VM). dashboard is the smallest contributor (50m, api-only), so it is the LAST thing to evict; image (Celery worker + rembg) is the heavier MS-2 partner.
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

Because dashboard is a **leaf consumer** (§0.6 — nothing in the codebase imports `app.modules.dashboard.*`), rollback is low-blast-radius: no other service depends on svc-dashboard being up.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik (the GET) back to the monolith
Route `GET /api/v1/products` back to the monolith. The monolith still has the in-process `dashboard_router` mounted (`main.py:141` — it is NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Simplest revert: delete the svc-dashboard IngressRoute so the host-only api
# Ingress (api.mesell.xyz → api:80, the monolith) reclaims GET /api/v1/products.
kubectl -n dev delete ingressroute svc-dashboard
kubectl -n dev get ingressroute -o wide
```

**METHOD-AWARE NOTE:** the svc-dashboard IngressRoute matched ONLY
`Method(\`GET\`) && Path(\`/api/v1/products\`)`. The catalog `POST /api/v1/products`
was NEVER routed to svc-dashboard (it always stayed on the monolith), so deleting
this IngressRoute affects ONLY the GET. There is no POST route to "restore."

### Step 2 — Shims: re-export the in-process service (1 line per callee)
Only needed if the monolith module had been modified to delegate to svc-dashboard (it was NOT in Sub-Plan B — both trees coexist untouched during the strangler window). For completeness, the §16.G contract guarantees a 1-line revert per callee: `core/extracted_clients/<callee>_client.py` re-exports the in-process `service.py` symbol instead of issuing HTTP. dashboard's 2 outbound shims are `catalog.list_products` + `customer.get_onboarding_completeness` (§0.5) — but those are dashboard CALLING OUT, served by the still-in-process catalog/customer modules; the monolith's `dashboard_router` itself was never pointed at a shim. During Sub-Plan B this step is a **no-op**.

### Step 3 — Database: NONE (dashboard owns zero tables)
**There is NO database rollback for svc-dashboard.** dashboard owns ZERO tables and ZERO schema (§0.8 / I5) — there is no `alembic downgrade`, no `ALTER TABLE ... SET SCHEMA`, nothing to reverse. The `dashboard_user` role + its `INSERT ON public.audit_events` grant (I5) are harmless and may stay (the role logs in but owns nothing; a service that no longer exists simply stops connecting). Optionally drop the role for hygiene: `DROP ROLE IF EXISTS dashboard_user;` — but ONLY after Step 4 confirms no svc-dashboard pod is still connected.

### Step 4 — Tear down the svc-dashboard deployment
```bash
kubectl -n dev delete deployment svc-dashboard-api          # api only (NO worker — dashboard has no Celery)
kubectl -n dev delete service svc-dashboard                 # ClusterIP
kubectl -n dev delete configmap svc-dashboard-config        # trimmed flag/APP_ENV ConfigMap (I8)
kubectl -n dev delete secret svc-dashboard-secrets          # trimmed secret (I7)
kubectl -n dev delete ingressroute svc-dashboard            # if not already removed in Step 1
# Postgres role/grant (I5) may stay — harmless (see Step 3). Drop only if desired.
```

### Step 5 — Re-run hybrid CI in pure in-process mode + log root cause
Run the monolith dashboard tests to confirm the in-process path is green, then record the incident in the Rollback Log below. The hybrid CI mode reverts to pure in-process (the shim env var / mode flag that selects HTTP-vs-in-process is set back to in-process; see `CI_HYBRID_MODE_dashboard` if present, else the MS-A `CI_HYBRID_MODE_export` pattern).

```bash
cd backend && PYTHONPATH=. python -m pytest tests/modules/dashboard tests/integration -k dashboard -q
# (dashboard's own suite — tests/modules/dashboard/{test_empty_state,test_feature_flag,
#  test_pagination_validation,test_response_composition}.py + tests/integration/
#  test_dashboard_list_flow.py + test_dashboard_cross_tenant.py — §0.9)
```

---

## 2. Post-rollback verification checklist

- [ ] `GET /api/v1/products` serves from the monolith (Traefik no longer has a svc-dashboard rule; the host-only api Ingress reclaims it).
- [ ] `POST /api/v1/products` (catalog create) STILL serves from the monolith (it never moved — confirm no regression).
- [ ] The `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 kill-switch fires correctly on the in-process path (flag off ⇒ 404; flag on ⇒ 200).
- [ ] NO database change to verify (dashboard owns no tables — Step 3 is a no-op by design).
- [ ] Monolith dashboard test suite green (in-process mode).
- [ ] No `svc-dashboard` pods/services/configmaps/secrets/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan B authored 2026-06-13; no rollback has occurred)_ | | | | |
