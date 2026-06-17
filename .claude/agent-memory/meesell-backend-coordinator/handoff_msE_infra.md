# HANDOFF -> meesell-infra-builder — Sub-Plan E (`customer` extraction) INFRA work-package

**From:** meesell-backend-coordinator (session `mesell-ms-customer-session-1`, 2026-06-12)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**Trigger / gate:** EXECUTION GATED on MS-2 (B dashboard + C image founder gates merged). customer runs at MS-3 in parallel with MS-D pricing. This handoff is AUTHORED now (parallel-program spec phase); the infra lane begins at MS-3 dispatch, NOT now.

---

## 0. Scope of this handoff
The svc-customer extraction's INFRA surfaces. Backend specialists own `backend/services/svc-customer/app/**` code; infra lead owns everything below, committed on `feature/microservices-customer/infra` (cut from `feature/microservices-customer/integration`), reviewed by the infra lead, merged into integration alongside the backend group PR.

**CUT POINT:** cut the integration branch from **origin/develop** (tip `c859955` at authoring) at MS-3 dispatch, not from a local-only commit.

---

## 1. Infra deliverables (all dev-namespace, current hardware)

| # | Surface | Spec | Source authority |
|---|---|---|---|
| I1 | `backend/services/svc-customer/Dockerfile` | FROM python:3.12-slim; install svc-customer requirements.txt; single api process (NO worker — customer has no Celery). | infra plan §6 |
| I2 | `k8s/svc-customer/deployment.yaml` | **api 1 replica:** req ~50m CPU / 128Mi, lim 200m/512Mi. Query-light, no worker, no AI. Smallest service alongside pricing. | infra plan §6.3 |
| I3 | `k8s/svc-customer/service.yaml` | ClusterIP `customer-svc:8001`. | infra plan §6 |
| I4 | Traefik IngressRoute | Route `/api/v1/seller-profile/*` -> `customer-svc:8001`. `/internal/*` NOT Traefik-exposed (cluster-DNS only). | MASTER_PLAN §2.C, D4 |
| I5 | Postgres schema + role | `CREATE SCHEMA customer; GRANT USAGE ON SCHEMA customer TO customer_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA customer TO customer_user;` PLUS **`GRANT INSERT ON public.audit_events TO customer_user`** (cross-schema audit write — the 3 @audit_event PATCH routes; integration test asserts an audit row lands). | MASTER_PLAN §2.D / §5.B |
| I6 | Secret injection | customer-svc pod needs: `DATABASE_URL` (@schema customer), `VALKEY_URL`, `JWT_SECRET` (shared — local JWT verify per D7/A2), `CACHE_VERSION`, `APP_ENV`. **NOT** GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS (customer is deterministic CRUD — no AI/SMS/payment/storage). | spec_msE_backend §3.A |
| I7 | Cross-service base-URL re-point at cutover | At customer's cutover flip: export-svc + dashboard-svc `customer_client` base URLs re-point from `monolith-svc:8001` -> `customer-svc:8001` (config/env flip, NOT code — §16.G). customer-svc's OWN `category_client` (E3-A outbound shim) base URL points at `monolith-svc:8001` during MS-3 (category not yet extracted), re-points to `category-svc:8001` at MS-4. | sub-plan §2, §3 |
| I8 | D5 / MS-DB-3 pool right-size | Per-service `pool_size` (SMALL for customer) + `max_connections=200` (already shipped MS-0 wave). customer's pool is tiny (query-light, no worker). | infra plan §3.2, MS-DB-3 |

NO GCS service account (customer touches no object storage). NO Celery queue (customer has no task). These are the two MS-A surfaces customer does NOT need.

---

## 2. D5 / PgBouncer sequencing
- MS-DB-3 (pool right-size + max_connections=200) ships in the MS-0 wave, before any service moves.
- MS-DB-4 (PgBouncer transaction-pool) = mandatory before traffic-bearing PROD cutover ONLY. customer is dev-only / zero-traffic -> PgBouncer NOT a customer blocker. PgBouncer async caveat (pool_pre_ping=False + executemany_mode='values_only') flagged for when MS-DB-4 lands; not needed for dev customer.
ORDER for customer: schema/role (I5) -> image+deploy (I1/I2/I3) -> Traefik (I4) -> secrets (I6) -> cutover base-URL re-points (I7).

---

## 3. Hardware / VM — D3 checkpoint re-evaluated by master at MS-3 deploy
- customer-svc at ~50m/128Mi (api only, no worker) is the SMALLEST service alongside pricing. customer + pricing both deploy at MS-3.
- **D3 (VM e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** The spend gets an EXPLICIT FRESH FOUNDER ASK at the moment a wave's deploy doesn't fit the current node (master-session standing rule, MASTER_PLAN §3.A.1 / MS-PAR-1 D3 checkpoint). By MS-3 the node holds the monolith remnant + export-svc (MS-1) + dashboard-svc + image-svc (MS-2). **If the master session's capacity math shows monolith + 4 small services + customer + pricing overflows the node at MS-3, STOP and ask the founder for D3 — do NOT silently upgrade.** customer itself commits NO money.

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests.
- NO terraform beyond dev-scope sanctioned by the infra plan. Anything bigger (new node pool, new bucket, IAM beyond the customer role grant) -> flag to founder, do not execute.
- `/internal/*` NOT Traefik-exposed (absence of IngressRoute = sufficient isolation; NetworkPolicy is V2).
- Infra branch = `feature/microservices-customer/infra`, infra-lead-reviewed, squash into integration. Founder gates integration->develop (NOT me, NOT infra lead).

---

## 5. What I (backend lead) need back from infra (acceptance items the backend merge gate depends on)
- I5 confirmed: `customer_user` HAS `INSERT ON public.audit_events` (else the integration test asserting an audit row on PATCH fails).
- I7 confirmed: export-svc + dashboard-svc `customer_client` base URLs re-point to customer-svc at cutover; customer-svc's `category_client` base URL points at monolith during MS-3.
- I2 confirmed deployed at the ~50m sizing (so I can confirm "fits current node, no D3 ask at MS-3" OR flag the master-session D3 checkpoint if the wave's total overflows).
- I8 confirmed: max_connections=200 applied (so the strangler-window connection count from monolith + extracted services doesn't storm Postgres).

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I open the Inter-lead request row on my board when MS-3 execution opens.
