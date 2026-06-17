# HANDOFF → meesell-infra-builder — Sub-Plan D (`pricing` extraction) INFRA work-package

**From:** meesell-backend-coordinator (session `mesell-ms-pricing-session-1`, 2026-06-12)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**Wave:** MS-3 (parallel w/ MS-E customer). **GATED:** Phase 2 (incl. this infra package) executes ONLY when the master session confirms MS-2 = both B dashboard + C image founder gates merged to develop + MS-A recipe exists. THIS IS A PHASE-1 SPEC — do NOT provision until the gate opens.
**Mirrors:** `handoff_msA_infra.md` structure.

---

## 0. Scope
svc-pricing extraction INFRA surfaces. Backend specialists own `backend/services/svc-pricing/app/**`; **infra lead owns everything below**, committed on `feature/microservices-pricing/infra` (cut from `feature/microservices-pricing/integration`), reviewed by the infra lead, merged into integration alongside the backend group PR.

**CUT POINT:** local `develop` (`6d6ee51`) is DIVERGED/stale; **origin/develop tip = `c859955`** (PR #179). Cut the integration branch from `origin/develop`.

---

## 1. Infra deliverables (all dev-namespace, current hardware)

| # | Surface | Spec | Source |
|---|---|---|---|
| I1 | `backend/services/svc-pricing/Dockerfile` | FROM python:3.12-slim; install svc-pricing `requirements.txt`. **SINGLE entrypoint — api ONLY. NO worker** (pricing has no Celery task — verified, modules/pricing has no tasks.py). | infra plan §6 |
| I2 | `k8s/svc-pricing/deployment.yaml` | **api 1 replica ONLY**, req **50m CPU / 128Mi**, lim **200m / 256Mi**. **NO worker pod** (lighter than svc-export which is worker-heavy; pricing is stateless lightweight math — 1 INSERT + ≤1 SELECT per request). | infra plan §6.3 (scaled down — no XLSX build) |
| I3 | `k8s/svc-pricing/service.yaml` | ClusterIP `svc-pricing:8001`. | infra plan §6 |
| I4 | Traefik IngressRoute | Route `/api/v1/products/{id}/price-calc` → `svc-pricing:8001`. **⚠️ Path param is `{id}` (pricing/router.py:69 uses `{id}`, NOT `{product_id}`).** `/internal/*` NOT exposed (pricing has NO `/internal/*` — leaf consumer). **PRIORITY FLAG below.** | MASTER_PLAN §2.C ("except images, price-calc, exports"), D4 |
| I5 | Postgres schema + role | `CREATE SCHEMA pricing; GRANT USAGE ON SCHEMA pricing TO pricing_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA pricing TO pricing_user;` PLUS **`GRANT INSERT ON public.audit_events TO pricing_user`** (the `@audit_event("pricing.calculated")` decorator writes a cross-schema row — R3; the integration test asserts an audit row lands). | MASTER_PLAN §2.D / §5.B |
| I6 | GCS service account | **NONE.** pricing touches NO GCS (no images, no exports — verified: no gcs adapter import). Do NOT provision a pricing GCS SA. | — |
| I7 | Secret injection | svc-pricing pod needs ONLY: `DATABASE_URL` (@schema pricing), `VALKEY_URL` (DB 0 rate-limit only), `JWT_SECRET` (shared — local JWT verify per D7/A2), `APP_ENV`. **NOT** GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS (pricing is deterministic — no AI/SMS/payment/storage). The smallest secret surface of any service. | spec_msD_backend §3.A |
| I8 | D5 / MS-DB-3 pool right-size | Per-service `pool_size` (pricing = SMALLEST pool — stateless math) + `postgresql.conf` `max_connections=200`. Ships BEFORE the service moves (MS-0). | infra plan §3.2, MS-DB-3 |
| I9 | Transitional cross-schema SELECT (CONDITIONAL — confirm with backend lead) | IF the §0.6 shared-ORM resolution cannot fully eliminate the `public.products` read at MS-3, `pricing_user` needs `GRANT SELECT ON public.products TO pricing_user` (TRANSITIONAL — revoked when catalog extracts at MS-5). **PREFERRED: the catalog `/internal/*` shim eliminates the products read entirely → this grant is NOT needed.** DO NOT grant until backend lead confirms the shim resolution did NOT land clean. | spec_msD_backend §0.6, SUB_PLAN_0D DB surface |

---

## 2. ⚠️ Traefik priority — `/price-calc` nests under catalog's `/api/v1/products/*` (CROSS-WAVE)

The pricing path `/api/v1/products/{id}/price-calc` is a SUB-path of the catalog-owned prefix `/api/v1/products/*` (MASTER_PLAN §2.C → catalog-svc). Same nesting class as image (`/products/{id}/images*`, MS-2) and export (`/products/{id}/export-xlsx`, MS-1).

- **The Traefik IngressRoute for `/price-calc` MUST be priority-ranked ABOVE the catalog `/api/v1/products` catch-all**, else catalog-svc swallows the pricing request.
- MASTER_PLAN §2.C carves out images/price-calc/exports as exceptions to the catalog prefix — the carve-out is PLANNED, but the priority ORDERING must be implemented explicitly.
- **CROSS-WAVE CONCERN:** three sub-path carve-outs (`/images*` MS-2, `/export-xlsx` MS-1, `/price-calc` MS-3) all sit under the catalog catch-all (MS-5). **Their Traefik priorities must be coherent across MS-1/2/3 — do NOT let three sessions each invent a different scheme.** I have RECOMMENDED to the master session that ONE Traefik priority table own the `/api/v1/products/*` family. Infra lead: implement against that table when it lands; if it does not exist yet, flag to master before inventing a pricing-only priority.

---

## 3. Hardware / VM — NO D3 trigger for Sub-Plan D
- svc-pricing at 50m/128Mi (api, no worker) is the LIGHTEST service — easily fits the current node alongside the monolith + export + dashboard + image.
- **D3 (VM e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** Fresh founder ask at node-outgrow (master-session standing rule, MASTER_PLAN §3.A.1) — NOT at execution start, NOT for Sub-Plan D. Sub-Plan D commits NO money.
- IF MS-3's combined footprint (monolith remnant + export + dashboard + image + pricing + customer) overflows the node, STOP and flag to founder (do not silently upgrade). pricing's tiny footprint is unlikely to be the trigger, but customer (MS-E, parallel) lands the same wave — watch the combined wave-3 footprint.

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests.
- NO terraform beyond dev-scope. Anything bigger (new node pool, IAM beyond the one pricing Postgres role) → flag to founder.
- `/internal/*` NOT Traefik-exposed — N/A for pricing anyway (pricing exposes none).
- Infra branch = `feature/microservices-pricing/infra`, infra-lead-reviewed, squash into integration. Founder gates integration→develop (NOT me, NOT infra lead).

---

## 5. What I (backend lead) need back from infra (acceptance items the merge gate depends on)
- I5 confirmed: `pricing_user` HAS `INSERT ON public.audit_events` (else R3 fires — the integration test asserting a `pricing.calculated` audit row fails).
- I8 confirmed: `max_connections=200` applied to dev Postgres.
- I2 confirmed deployed at 50m/256Mi api-only (so I can confirm "fits current node, no D3 ask, no worker pod").
- I9 confirmed: NO `public.products` grant issued UNLESS I explicitly confirm the §0.6 shim resolution failed (preferred path needs no grant).
- Traefik priority for `/price-calc` ranks above the catalog catch-all (RD4) — confirm against the master's `/api/v1/products/*` priority table.

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I open the Inter-lead request row on my board at Phase-2 dispatch (NOT now — this is Phase 1 spec).
