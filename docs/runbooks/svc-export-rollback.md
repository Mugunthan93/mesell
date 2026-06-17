# Runbook — `svc-export` Rollback (Microservices Sub-Plan A)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan A — `export` module extraction (first extraction, §16.H order #1)
**Scope:** reverting the `export` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_01_export_extraction.md`, `SHIM_CONTRACT_export_callees.md`, `CI_HYBRID_MODE_export.md`, `handoff_msA_infra.md`.

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Postgres / Traefik command is a deploy-window operation, executed by whoever owns the window.

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan A is declared complete** (the 7-day hybrid-mode green window). Triggers:

- Hybrid-mode CI goes red on a contract surprise the strangler can't absorb.
- The cross-schema audit write fails in the dev cluster (R3 — `export_user` lacks `INSERT ON public.audit_events`).
- Postgres connection storm from monolith + svc-export coexisting (R-MS-1 — `max_connections` exhausted).
- svc-export + monolith remnant overflows the current node (capacity — STOP and flag to founder, do NOT silently upgrade the VM).
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

Because export is a **leaf consumer** (nothing calls it), rollback is low-blast-radius: no other service depends on svc-export being up.

---

## 1. The five rollback steps (in order)

### Step 1 — Traffic: re-point Traefik to the monolith
Route the export paths back to the monolith ClusterIP. Edit the Traefik IngressRoute (infra I4) so:
- `/api/v1/exports/*` → `monolith-svc:8001`
- `/api/v1/products/{product_id}/export-xlsx` → `monolith-svc:8001`

```bash
kubectl -n dev apply -f k8s/monolith/ingressroute-export-fallback.yaml   # restores monolith routing
# (or delete the svc-export IngressRoute so the monolith catch-all reclaims the paths)
kubectl -n dev get ingressroute -o wide
```
The monolith still has the in-process `export_router` mounted (it is NOT removed until cutover — `spec_msA_backend §4`), so traffic served immediately.

### Step 2 — Shims: re-export the in-process service (1 line per callee)
This step is only needed if the monolith module had been modified to delegate to svc-export (it was NOT in Sub-Plan A — both trees coexist untouched). For completeness, the §16.G contract guarantees a 1-line revert per callee: `core/extracted_clients/<callee>_client.py` re-exports the in-process `service.py` symbol instead of issuing HTTP. During Sub-Plan A this is a **no-op** — the monolith export module was never pointed at the shims.

### Step 3 — Schema: move `exports` back to `public`
Reverse the schema-split migration. The svc-export Alembic chain (`e7a3c1f9b42d`, `version_table_schema="export"`) has a tested downgrade that runs `ALTER TABLE exports SET SCHEMA public`.

```bash
cd backend/services/svc-export
alembic downgrade -1          # e7a3c1f9b42d → base : export.exports → public.exports
alembic current               # confirm head is below the schema-split
```
**ORDER DISCIPLINE (P0):** apply the downgrade to **dev FIRST, then staging** — NEVER the reverse. A head divergence between dev and staging is a P0 escalate-to-founder condition. Run the Risk#5 integrity pre-scan output check before the downgrade (every `exports.user_id` resolves to a real `users` row).

### Step 4 — Tear down the svc-export deployment
```bash
kubectl -n dev delete deployment svc-export                 # api + worker
kubectl -n dev delete service svc-export                    # ClusterIP
kubectl -n dev delete ingressroute svc-export-route         # if not already removed in Step 1
# Postgres role/schema grants (infra I5) may stay — harmless once the table is back in public.
```

### Step 5 — Re-run CI in pure in-process mode + log root cause
Run the monolith export tests (`tests/modules/export/` + `tests/integration/test_export_*.py`) to confirm the in-process path is green, then record the incident in the Rollback Log below.

```bash
cd backend && PYTHONPATH=. python -m pytest tests/modules/export tests/integration -k export -q
```

---

## 2. Post-rollback verification checklist

- [ ] `GET /api/v1/exports/{id}` and `POST /api/v1/products/{id}/export-xlsx` serve from the monolith (Traefik points at `monolith-svc`).
- [ ] `exports` table is back in the `public` schema (`\dt public.exports` returns 1 row; `\dt export.exports` returns 0).
- [ ] `alembic current` on dev == staging (no head divergence).
- [ ] Monolith export test suite green.
- [ ] No `svc-export` pods/services/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan A in execution 2026-06-12; no rollback has occurred)_ | | | | |
