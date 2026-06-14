# HANDOFF → meesell-infra-builder — Sub-Plan A (`export` extraction) INFRA work-package

**From:** meesell-backend-coordinator (session `mesell-ms-export-spec-session-1`, 2026-06-12)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**Trigger:** dev-complete DECLARED 2026-06-12; MASTER_PLAN §3.A.1 (v1.3) execution gate SATISFIED; founder "ms go" in force. First extraction (§3.B order #1 = export).

---

## 0. Scope of this handoff
The svc-export extraction's INFRA surfaces. Backend specialists own `backend/services/svc-export/app/**` code; **infra lead owns everything below**, committed on `feature/microservices-export/infra` (cut from `feature/microservices-export/integration`), reviewed by the infra lead, merged into integration alongside the backend group PR.

**CUT POINT WARNING:** local `develop` (`f23d84a`) is DIVERGED and stale; **origin/develop tip = `afea672`** (PR #178, the rekey). Cut the integration branch from `origin/develop`, not local develop. (`git fetch origin && git checkout -b feature/microservices-export/integration origin/develop`.)

---

## 1. Infra deliverables (all dev-namespace, current hardware)

| # | Surface | Spec | Source authority |
|---|---|---|---|
| I1 | `backend/services/svc-export/Dockerfile` | FROM python:3.12-slim; install svc-export `requirements.txt`; one image serves both api + worker (entrypoint differs). | infra plan §6 |
| I2 | `k8s/svc-export/deployment.yaml` | **api 1 replica:** req **50m CPU / 128Mi**, lim 200m/512Mi. **worker 1 replica:** req **200m CPU / 512Mi**, lim per infra plan. (Infra §6.3: svc-export is api-light, worker-heavy because XLSX build is CPU+mem.) | infra plan §6.3 table |
| I3 | `k8s/svc-export/service.yaml` | ClusterIP `svc-export:8001`. | infra plan §6 |
| I4 | Traefik IngressRoute | Route `/api/v1/exports/*` AND `/api/v1/products/{id}/export-xlsx` → `svc-export:8001`. NOTE exact path param is `{product_id}` (export/router.py:90). `/internal/*` NOT exposed by Traefik (cluster-DNS only). | MASTER_PLAN §2.C, D4 |
| I5 | Postgres schema + role | `CREATE SCHEMA export; GRANT USAGE ON SCHEMA export TO export_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA export TO export_user;` PLUS **`GRANT INSERT ON public.audit_events TO export_user`** (cross-schema audit write — Sub-Plan A R3; the integration test asserts an audit row lands). | MASTER_PLAN §2.D / §5.B |
| I6 | GCS service account | SA with `storage.objectAdmin` scoped to export's GCS path prefix (`meesell-exports/{user_id}/...`). | MASTER_PLAN §2.E |
| I7 | Secret injection | svc-export pod needs: `DATABASE_URL` (@schema export), `VALKEY_URL`, `JWT_SECRET` (shared — local JWT verify per D7/A2), `GCS_*`, `APP_ENV`. **NOT** GEMINI/LANGFUSE/MSG91/RAZORPAY (export is deterministic — no AI/SMS/payment). | spec_msA_backend §3.A |
| I8 | D5 / MS-DB-3 pool right-size | Per-service `pool_size` matrix in code + `postgresql.conf` `max_connections=200`. Ships BEFORE the service moves. Low risk. | infra plan §3.2, MS-DB-3 |

---

## 2. D5 / PgBouncer sequencing — EXPLICIT order (founder-ruled D5)

Per infra plan §3.2 (APPROVED v1.1):
- **MS-DB-3** (pool right-size + `max_connections=200`) = ships FIRST, before any service moves. Counts as I8 above. May run in parallel with backend extraction.
- **MS-DB-4** (PgBouncer transaction-pool) = **mandatory before traffic-bearing PROD cutover ONLY.** Sub-Plan A is **dev-only / zero-traffic** → PgBouncer is **NOT a Sub-Plan-A blocker.** The extraction proceeds on the current node without it.
- **PgBouncer async caveat (flag for when MS-DB-4 lands):** transaction-pool mode forbids prepared statements spanning txns; SQLAlchemy/asyncpg must use `pool_pre_ping=False` + `executemany_mode='values_only'`. Smoke-test each service's integration suite against PgBouncer in a `pre-pgbouncer-cutover` env (infra plan R-MS-8). Not needed for dev A.

**ORDER for Sub-Plan A:** MS-DB-3 (I8) → schema/role (I5) → image+deploy (I1/I2/I3) → Traefik (I4) → GCS SA (I6) → secrets (I7). PgBouncer deferred (not in A).

---

## 3. Hardware / VM — NO D3 trigger for Sub-Plan A

- svc-export at 50m/128Mi (api) + 200m/512Mi (worker) **fits the current `e2-standard-2` node** (infra §6.3; early extractions A export + B dashboard fit at locked 50m sizing per MASTER_PLAN §3.A.1).
- **D3 (VM e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** The spend gets an **EXPLICIT FRESH FOUNDER ASK at the moment services outgrow the current node** (master-session standing rule, MASTER_PLAN §3.A.1) — NOT at execution start, NOT for Sub-Plan A. Sub-Plan A commits NO money.
- If infra lead's capacity math shows svc-export + monolith remnant overflows the node during the strangler window, STOP and flag to founder (do not silently upgrade).

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests in Sub-Plan A.
- NO terraform beyond what the infra plan's dev-scope sanctions. Anything bigger (new node pool, new bucket, IAM beyond the one export SA) → flag to founder, do not execute.
- `/internal/*` routes are NOT Traefik-exposed in V1.5 (absence of IngressRoute = sufficient isolation; NetworkPolicy is a V2 concern).
- Infra branch = `feature/microservices-export/infra`, infra-lead-reviewed, squash into integration. Founder gates integration→develop (NOT me, NOT infra lead).

---

## 5. What I (backend lead) need back from infra (acceptance items the backend merge gate depends on)
- I5 confirmed: `export_user` HAS `INSERT ON public.audit_events` (else R3 fires — the integration test that asserts an audit row will fail).
- I8 confirmed: `max_connections=200` applied to the dev Postgres (so the strangler-window connection count from monolith + svc-export doesn't storm Postgres — R-MS-1).
- I2 confirmed deployed at the 50m/200m sizing (so I can confirm "fits current node, no D3 ask" in the §4 row-A annotation).

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I will open the Inter-lead request row on my board today.
