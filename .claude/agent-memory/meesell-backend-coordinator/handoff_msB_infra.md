# HANDOFF → meesell-infra-builder — Sub-Plan B (`dashboard` extraction) INFRA work-package

> **WORKTREE FALLBACK COPY.** The main-tree write was BLOCKED by the
> bg-session worktree-isolation guard. This is the fallback under the docs
> worktree per the dispatch instruction. The session should relocate it to
> the main-tree memory dir.

**From:** meesell-backend-coordinator (session `mesell-ms-dashboard-session-1`, 2026-06-12, HYBRID STEP 1)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**Trigger:** **EXECUTION GATED — MS-2** (parallel with MS-C `image`). Infra work begins only when Sub-Plan A's founder gate is merged to develop AND the MS-A recipe is in the lead's memory. This handoff is authored NOW (Phase 1 docs); infra executes at MS-2.

---

## 0. Scope of this handoff
The svc-dashboard extraction's INFRA surfaces. Backend specialists own `backend/services/svc-dashboard/app/**` code; **infra lead owns everything below**, committed on `feature/microservices-dashboard/infra` (cut from `feature/microservices-dashboard/integration`), reviewed by the infra lead, merged into integration alongside the backend group PR.

**CUT POINT:** cut the integration branch from `origin/develop` (re-verify the live tip at dispatch — develop will have moved past `c859955` once MS-A merges). The worktree this was authored from (`/tmp/mesell-wt/msB-docs`) is at `c859955` == `origin/develop`; no divergence.

**KEY DIFFERENCE vs svc-export (MS-A):** dashboard owns **ZERO tables** and has **NO Celery worker**. So this handoff is LIGHTER than `handoff_msA_infra.md`: **no Postgres schema, no schema role grant on owned tables, no GCS service account, NO worker pod.**

---

## 1. Infra deliverables (all dev-namespace, current hardware)

| # | Surface | Spec | Source authority |
|---|---|---|---|
| I1 | `backend/services/svc-dashboard/Dockerfile` | FROM python:3.12-slim; install svc-dashboard `requirements.txt`; **api-only** entrypoint (NO worker — dashboard has no Celery). | infra plan §6 |
| I2 | `k8s/svc-dashboard/deployment.yaml` | **api 1 replica ONLY** (NO worker): req **50m CPU / 128Mi**, lim 200m/256Mi (smaller mem than svc-export — no XLSX build, no worker). | infra plan §6.3 (adapted: dashboard is the lightest service) |
| I3 | `k8s/svc-dashboard/service.yaml` | ClusterIP `svc-dashboard:8001`. | infra plan §6 |
| I4 | Traefik IngressRoute | Route **`GET /api/v1/products`** → `svc-dashboard:8001`. **METHOD-or-prefix-aware** per the §13-DASHBOARD-D2 path-key collision: `GET /api/v1/products` → svc-dashboard, but `POST /api/v1/products` (catalog create) STAYS on the monolith (catalog extracts LAST at MS-5). `/internal/*` NOT exposed (dashboard has none). | MASTER_PLAN §2.C, D4; SUB_PLAN_0B §0.4 |
| I5 | Postgres role (audit grant only — NO owned schema) | `GRANT INSERT ON public.audit_events TO dashboard_user` — for the INERT audit_mw import path (audit_mw writes NOTHING on the read-only GET, but the vendored middleware import-chain expects the audit write API wired). **NO `CREATE SCHEMA dashboard`** (dashboard owns zero tables). | MASTER_PLAN §5.B; SUB_PLAN_0B §0.8 |
| I6 | **(NO GCS service account)** | dashboard touches NO GCS (no images, no exports). Skip — contrast svc-export I6. | — |
| I7 | Secret injection | svc-dashboard pod needs: `DATABASE_URL` (NO owned schema — shared-session/get_db wiring + the inert audit path), `VALKEY_URL` (rate_limit DB 0 + audit), `JWT_SECRET` (shared — local JWT verify per D7/A2), `FEATURE_TRACKING_DASHBOARD_ENABLED`, `APP_ENV`. **NOT** GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS (dashboard is a pure read — no AI/SMS/payment/storage). | spec_msB_backend §3.A |
| I8 | `FEATURE_TRACKING_DASHBOARD_ENABLED` ConfigMap | The flag already exists for the monolith (landed via the flag-parity sweep, inter-lead `flag-parity` open). svc-dashboard's ConfigMap carries the SAME flag: **dev=true / staging=false** (the D3 kill-switch — 404-on-read intentional). | flag-parity inter-lead; SUB_PLAN_0B §0.4-FLAG |
| I9 | D5 / MS-DB-3 pool right-size | Per-service `pool_size` matrix in code + `postgresql.conf` `max_connections=200`. Ships BEFORE the service moves. **dashboard's pool is the SMALLEST (2–3 conns)** — it queries ~nothing (DB used only for mw/get_db wiring + the inert audit path). | infra plan §3.2, MS-DB-3; SUB_PLAN_0B §0.8 |

---

## 2. D5 / PgBouncer sequencing — EXPLICIT order (founder-ruled D5)

Per infra plan §3.2 (APPROVED v1.1), same as MS-A:
- **MS-DB-3** (pool right-size + `max_connections=200`) = ships FIRST, before any service moves. Counts as I9 above. May run in parallel with backend extraction.
- **MS-DB-4** (PgBouncer transaction-pool) = **mandatory before traffic-bearing PROD cutover ONLY.** Sub-Plan B is **dev-only / zero-traffic** → PgBouncer is **NOT a Sub-Plan-B blocker.** dashboard owns no schema → its DB footprint is ~0, so even the pool concern is minimal.

**ORDER for Sub-Plan B:** MS-DB-3 (I9) → audit grant (I5) → image+deploy (I1/I2/I3) → Traefik (I4) → secrets+ConfigMap (I7/I8). PgBouncer deferred (not in B).

---

## 3. Hardware / VM — NO D3 trigger for Sub-Plan B (smallest service)

- svc-dashboard at 50m/128Mi (api-only, NO worker) is the **LIGHTEST service of any extraction** (owns no tables, no Celery, no GCS). It **fits the current `e2-standard-2` node** alongside the monolith remnant + svc-export + svc-image at the MS-2 wave (early extractions A `export` + B `dashboard` fit at locked 50m sizing per MASTER_PLAN §3.A.1).
- **D3 (VM e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** The spend gets an **EXPLICIT FRESH FOUNDER ASK at the moment services outgrow the current node** (master-session standing rule, MASTER_PLAN §3.A.1) — NOT at execution start, NOT for Sub-Plan B. Sub-Plan B commits NO money.
- **MS-2 capacity watch:** MS-2 deploys monolith remnant + svc-export + svc-dashboard + svc-image simultaneously. If the infra lead's capacity math shows the node overflows during the MS-2 strangler window, STOP and flag to founder (do not silently upgrade). dashboard is the smallest contributor; image (with its Celery worker + rembg surface) is the heavier MS-2 partner.

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests in Sub-Plan B.
- NO terraform beyond what the infra plan's dev-scope sanctions. Anything bigger (new node pool, new bucket, IAM) → flag to founder, do not execute. (dashboard needs NO new bucket / NO new SA.)
- `/internal/*` routes — N/A for dashboard (it exposes none; it is a leaf consumer).
- Infra branch = `feature/microservices-dashboard/infra`, infra-lead-reviewed, squash into integration. Founder gates integration→develop (NOT me, NOT infra lead).
- **Parallel-lane discipline with MS-C image:** the shared Traefik routing table gets additive/keep-both edits; dashboard (`GET /api/v1/products`) and image (`/api/v1/products/{id}/images*`) touch DISJOINT path prefixes.

---

## 5. What I (backend lead) need back from infra (acceptance items the backend merge gate depends on)
- I5 confirmed: `dashboard_user` HAS `INSERT ON public.audit_events` (so the vendored audit_mw import is safe — even though no row is ever written on the read-only GET).
- I4 confirmed: Traefik routes `GET /api/v1/products` → svc-dashboard while `POST /api/v1/products` stays on monolith (the §13-DASHBOARD-D2 method/path collision is handled).
- I8 confirmed: `FEATURE_TRACKING_DASHBOARD_ENABLED` injected into svc-dashboard's ConfigMap (dev=true / staging=false) — so the 404 kill-switch behaves identically in the extracted service.
- I2 confirmed deployed at the 50m/128Mi api-only sizing (so I can confirm "fits current node, no D3 ask" in the §4 row-B annotation).

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I will open the Inter-lead request row on my board at Phase 2 dispatch (NOT now — this is the gated Phase-1 freeze).
