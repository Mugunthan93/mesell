# Microservices Infrastructure Master Plan

**STATUS: APPROVED 2026-06-10 — ratified by founder via S4 ratification package. D3 VM e2-standard-4 pre-approved (execution-time, ~₹2,600/mo, founder cost-gate sign-off). D4 Traefik path-prefix gateway. D5 pools right-size → PgBouncer-before-cutover.**

**Scope:** Infrastructure changes required to evolve the MeeSell backend from a single FastAPI api + Celery worker deployment into 8 independently deployable FastAPI microservices (each with its own Celery worker) on the existing K3s cluster.

**Source of truth read at draft time:** `docs/INFRASTRUCTURE_ARCHITECTURE.md`, `docs/DEVOPS_ARCHITECTURE.md`, `docs/status/STATUS_INFRA.md`, `k8s/*.yaml`, `.claude/agent-memory/meesell-infra-builder/MEMORY.md`.

**Constraint:** This is a planning document only. No K8s, Terraform, or code changes are part of this deliverable.

---

## Glossary (used throughout)

| Term | Meaning in this plan |
|---|---|
| **Service** | One of the 8 target FastAPI microservices (e.g., `auth`, `catalog`, `quality`, etc.) |
| **Worker** | The Celery worker process tied to a service. Reuses the service's container image. |
| **api/worker** (lowercase) | The current single monolithic Deployments named `api` and `worker` in the `dev` namespace |
| **Domain** | A vertical slice owned by one service (data + routes + worker tasks + service module) |
| **East-west traffic** | Service-to-service calls inside the cluster |
| **North-south traffic** | External traffic from `api.mesell.xyz` into the cluster |

For this plan, the 8 services correspond to the 8 backend domains carried in `backend/app/` today:

| # | Service slug | Domain it owns | Origin in current code |
|---|---|---|---|
| 1 | `svc-auth` | OTP + JWT issuance + refresh token allowlist | `app/routers/auth.py`, `app/services/otp_service.py` |
| 2 | `svc-catalog` | Catalog + SKU CRUD | `app/routers/catalogs.py`, `app/routers/skus.py` |
| 3 | `svc-image` | Image upload, rembg pipeline, GCS write | `app/routers/images.py`, `app/services/image_processor.py` |
| 4 | `svc-quality` | QualityGate rules engine | `app/routers/quality.py`, `app/services/quality_engine.py` |
| 5 | `svc-pricing` | P&L + shipping calculator | `app/routers/pricing.py`, `app/services/pricing_engine.py` |
| 6 | `svc-ai` | Gemini calls, prompt management, AI ops budget meter | `app/services/ai_engine.py` |
| 7 | `svc-export` | XLSX / CSV / ZIP generation for Meesho bulk upload | `app/routers/exports.py`, `app/services/export_service.py` |
| 8 | `svc-billing` | Razorpay subscription lifecycle + plan-guard | `app/middleware/plan_guard.py`, Razorpay webhook handler |

The slugs (`svc-*`) are used consistently in K8s resource names, image names, and CI matrix entries.

> **SUPERSEDED 2026-06-10 (founder ratification, this revision) — the 8 service slugs above are NOT authoritative.** The 8-table glossary above was drafted against a pre-LOCK guess at the domain split and invented two non-existent services (`svc-quality`, `svc-billing`) while omitting real modules. The AUTHORITATIVE 8 services are the 8 domain modules locked in `docs/plans/microservices_migration/MASTER_PLAN.md` §1.A / §2.A / §2.D — namely **`iam`, `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`** (extracted as `iam-svc`, `customer-svc`, … `export-svc`). There is no `svc-quality` (QualityGate is not a V1 module) and no `svc-billing` (Razorpay webhook + plan_guard live inside `iam`/`core`, not a standalone service). Wherever this document writes `svc-auth`/`svc-quality`/`svc-billing`/etc., read the MASTER_PLAN's module-named services. The DB-schema map (MASTER_PLAN §2.D), the Traefik path-prefix map (MASTER_PLAN §2.C, D4), and the extraction order (MASTER_PLAN §3.B) are the load-bearing authorities.

---

## 1. Current vs Target

### 1.1 Current

```
namespace: dev
  Deployment/api      (2 replicas)    image: meesell-prod-images/api:<sha>
  Deployment/worker   (2 replicas)    image: meesell-prod-images/api:<sha>   (worker reuses api image, different CMD)
  Service/api         ClusterIP :80 -> :8000
  Ingress/api         Host: api.mesell.xyz -> Service/api
  StatefulSet/postgres
  StatefulSet/valkey
  ConfigMap/meesell-config
  Secret/backend-secrets
```

All 8 domains live inside the single `api` pod. One bad import or one slow route slows down (or crashes) all 8. One deploy redeploys all 8. Connection-pool budget is computed once for the whole monolith. Celery has one worker pool sharing one Valkey broker DB.

### 1.2 Target

```
namespace: dev (one namespace — see §2.1 for rationale)
  Deployment/svc-auth-api          (2 replicas)
  Deployment/svc-auth-worker       (1 replica, no HTTP)
  Service/svc-auth                 ClusterIP :80 -> :8000   (HTTP API)
  Deployment/svc-catalog-api       (2 replicas)
  Deployment/svc-catalog-worker    (1 replica)
  Service/svc-catalog              ClusterIP :80 -> :8000
  ... (same shape for the other 6 services) ...

  Deployment/api-gateway           (2 replicas)     <- the only Deployment exposed via Ingress
  Service/api-gateway              ClusterIP :80 -> :8000
  Ingress/api                      Host: api.mesell.xyz -> Service/api-gateway

  StatefulSet/postgres             (single shared instance — schema-per-service, see §3)
  StatefulSet/valkey               (single shared instance — DB-per-service, see §4)
  ConfigMap/meesell-shared-config
  ConfigMap/svc-<name>-config      (per-service, optional, only if a service has unique env)
  Secret/backend-shared-secrets    (shared keys: JWT signing, GCS bucket name, etc.)
  Secret/svc-<name>-secrets        (per-service: e.g., svc-billing holds razorpay-* keys)
```

Each `svc-*-api` + `svc-*-worker` pair is one independently deployable unit. The api-gateway is a thin Traefik-routed front door — discussed in §2.4.

### 1.3 Sizing comparison

| Aspect | Current | Target |
|---|---|---|
| Deployments | 2 (api, worker) | 17 (8 api + 8 worker + 1 gateway) |
| ClusterIP Services | 1 (api) | 9 (8 service + 1 gateway) |
| Ingresses | 1 (api.mesell.xyz) | 1 (still api.mesell.xyz — fronted by gateway) |
| Independent build artifacts | 1 image | 8 images (or 1 multi-target image — see §5.2) |
| Independent rollouts | 1 | 8 services × 2 deployment kinds = up to 16 |
| Pods at rest | 4 (2 api + 2 worker) | 24 (8×2 api + 8×1 worker + 2 gateway) |
| Total CPU request | ~900m (current tuning) | ~2400m to ~3600m (see §6.3 sizing) |

The pod-count and CPU jump is the dominant infrastructure cost of microservicing on the current `e2-standard-2` node. §6 dimensions this.

---

## 2. K8s Architecture for Microservices

### 2.1 Namespace strategy — recommend ONE namespace per environment

| Option | Pros | Cons |
|---|---|---|
| **(A) Single `dev` ns for all 8 services** (recommended) | Shared `backend-shared-secrets`; shared ConfigMap; cluster DNS short names (`svc-catalog`) work without FQDN; matches current `staging` + `prod` pattern | Per-service NetworkPolicy is more verbose (must match by label) |
| (B) One namespace per service (`ms-auth`, `ms-catalog`, ...) | Stronger blast-radius isolation; per-ns ResourceQuota; cleaner RBAC | 8× the ConfigMap / Secret duplication; cluster DNS resolution uses `svc-auth.ms-auth.svc.cluster.local`; namespace sprawl across 3 envs = 24 namespaces |
| (C) One namespace per domain *family* (e.g. `core`, `ai`, `billing`) | Middle ground — quota/RBAC at domain-family boundary | Arbitrary boundary; doesn't match team structure for V1 (single-team) |

**Recommendation: (A)** for V1. Cluster is single-tenant (one team), single-node, and the cost of namespace duplication outweighs blast-radius gains. Revisit when the team grows past 2 backend engineers or when staging+prod isolation needs intra-cluster firewalling.

Per-service isolation inside the shared namespace is achieved via:

- K8s labels: every resource carries `app: svc-<name>` and `component: api|worker|migration`
- NetworkPolicy: default-deny-ingress in `dev`, then per-service allow rules (only api-gateway can hit `svc-*` from the ingress side; `svc-*` can call other `svc-*` services on port 8000 internally)
- RBAC: a per-service `ServiceAccount` (`svc-<name>-sa`) is created; deployments bind to their own SA. Workload Identity (Phase 2) maps each SA to a distinct GCP IAM identity so a compromised svc-image pod cannot read svc-billing's Razorpay secret.

### 2.2 Per-service Deployment + Service manifest

Each service has 4 K8s objects (excluding ingress):

```
k8s/services/svc-<name>/
├── deployment-api.yaml       # FastAPI HTTP server
├── deployment-worker.yaml    # Celery worker
├── service.yaml              # ClusterIP, port 80 -> 8000
└── serviceaccount.yaml       # Per-service SA for Workload Identity (Phase 2)
```

The `deployment-api.yaml` declares:

- 2 replicas (V1 default; tunable per service)
- `envFrom`:
  - `configMapRef: meesell-shared-config` (cluster URLs, env flags)
  - `secretRef: backend-shared-secrets` (DB/Valkey URLs, JWT secret)
  - `secretRef: svc-<name>-secrets` (only if the service holds domain-specific secrets)
- Probes `/health` (readiness 15s/10s, liveness 30s/30s) — every service exposes this
- Resource requests/limits sized per §6.3
- Image: `meesell-prod-images/svc-<name>-api:<sha>` (or `:<sha>` of a shared monorepo image with `CMD=...` driving the service — see §5.2)

The `deployment-worker.yaml` is identical to `deployment-api.yaml` except:

- No HTTP port exposed
- No readiness/liveness probe (use Celery's `--max-tasks-per-child` + restart policy)
- CMD: `celery -A app.<service>.workers.celery_app worker --concurrency=2 --max-tasks-per-child=100 -Q svc_<name>`
- 1 replica by default (the queue is the work distributor; horizontal scaling is per-queue, not per-pod)

### 2.3 Service discovery (east-west)

All east-west calls use K8s DNS. Inside the `dev` namespace, a pod calls `svc-catalog` (short name) — K8s resolves to `svc-catalog.dev.svc.cluster.local`. Service URLs are injected via the shared ConfigMap:

```yaml
# ConfigMap/meesell-shared-config (excerpt)
SVC_AUTH_URL:    http://svc-auth.dev.svc.cluster.local
SVC_CATALOG_URL: http://svc-catalog.dev.svc.cluster.local
SVC_IMAGE_URL:   http://svc-image.dev.svc.cluster.local
SVC_QUALITY_URL: http://svc-quality.dev.svc.cluster.local
SVC_PRICING_URL: http://svc-pricing.dev.svc.cluster.local
SVC_AI_URL:      http://svc-ai.dev.svc.cluster.local
SVC_EXPORT_URL:  http://svc-export.dev.svc.cluster.local
SVC_BILLING_URL: http://svc-billing.dev.svc.cluster.local
```

Per-environment overlays (staging/prod) inherit the same names because K8s DNS is namespace-scoped — `svc-catalog` in `staging` resolves to the staging Service object automatically. No environment string interpolation needed.

**Auth context propagation:** the api-gateway validates the JWT once and forwards a signed `X-User-Context` header (or re-signs a short-lived internal JWT). Downstream services trust the gateway's claim — they do NOT re-validate the public JWT. This pattern is documented for the backend coordinator; the infra-side responsibility is to ensure the gateway → svc network path is trusted (NetworkPolicy + the per-service ServiceAccount).

### 2.4 API Gateway — recommend Traefik IngressRoute, not Kong/nginx

| Option | Pros | Cons |
|---|---|---|
| **(A) Traefik IngressRoute + per-service prefix rules** (recommended) | Traefik is already deployed; no new pod cost; native K8s CRD-based routing | Less feature-rich than Kong; no built-in API key mgmt / rate-limit-per-key |
| (B) Kong Ingress Controller | Plugins for rate-limit, auth, API key | New deployment to operate; OSS Kong adds ~500MB RAM; CRD set is large |
| (C) Custom FastAPI gateway pod (`api-gateway`) | Full code control; can do request enrichment | New code to maintain; another deploy unit |
| (D) Nginx Ingress | Familiar | Replaces Traefik (current live ingress) — large blast radius |

**Recommendation: (A) Traefik IngressRoute.** Add path-prefix rules under `api.mesell.xyz`:

```
api.mesell.xyz/auth/*    -> svc-auth
api.mesell.xyz/catalog/* -> svc-catalog
api.mesell.xyz/sku/*     -> svc-catalog        (sku is part of catalog domain)
api.mesell.xyz/image/*   -> svc-image
api.mesell.xyz/quality/* -> svc-quality
api.mesell.xyz/pricing/* -> svc-pricing
api.mesell.xyz/ai/*      -> svc-ai
api.mesell.xyz/export/*  -> svc-export
api.mesell.xyz/billing/* -> svc-billing
api.mesell.xyz/health    -> svc-auth (or any service — used by deploy smoke check)
```

**[OPEN DECISION — MS-GW-1]:** path-prefix routing (above, simpler) vs Host-based subdomains (`auth.api.mesell.xyz`, `catalog.api.mesell.xyz`, ...). Path-prefix is recommended for V1 because:
- Single TLS cert covers `api.mesell.xyz` (already issued)
- Frontend / mobile clients can keep one `API_BASE_URL`
- CORS config doesn't fan out per-service

Host-based adds 8 DNS records, 8 cert renewals, and CORS fan-out — defer to V1.5 unless team boundaries demand it.

**Option C (custom gateway pod)** is added back to the menu if any of these become real V1 needs:
- Cross-service request orchestration (e.g., `/catalog/create` fans out to svc-catalog + svc-image + svc-ai in one call)
- Backend-for-Frontend (BFF) pattern with mobile-specific response shaping
- Request enrichment beyond what Traefik middlewares can do

### 2.5 Health checks per service

Every service implements `/health` returning 200 with JSON:

```json
{
  "status": "healthy",
  "service": "svc-catalog",
  "version": "<git sha>",
  "checks": {
    "postgres": "ok",
    "valkey": "ok",
    "<dependency>": "ok"
  }
}
```

The gateway's `/health` endpoint (proxied from a chosen service, e.g. `svc-auth`) is what GitHub Actions hits during deploy smoke check (`DEVOPS_ARCHITECTURE.md §7.3 step 6`).

**Aggregate health:** the deploy smoke check is extended (see §5.6) to also iterate `for s in svc-auth svc-catalog ...; do curl https://api.mesell.xyz/$s/health; done`. Any non-200 fails the smoke and triggers rollback.

---

## 3. Database Strategy

### 3.1 Shared Postgres with schema-per-service — recommended

| Option | Pros | Cons |
|---|---|---|
| **(A) Shared Postgres + schema-per-service** (recommended) | Single PVC, single backup, single connection pool budget to reason about, single Alembic chain per schema; preserves cross-domain JOINs during migration (use cautiously) | Cross-service schema migration ordering must be coordinated; one DB crash takes down all services |
| (B) Database-per-service (one PG per `svc-*`) | True isolation; per-service backup; failure isolation | 8 StatefulSets × 20Gi PVC = 160Gi minimum on the node (vs current 20Gi); 8 connection pools to budget; massive infra overhead for V1 single-node |
| (C) Logical PG cluster with publication / subscription (Postgres pub/sub) | Per-service DB + replication for shared reference tables | Complex, fragile, not needed at V1 traffic |

**Recommendation: (A) schema-per-service.** Inside the existing `postgres` database:

```
postgres database: meesell
├── schema: shared           # cross-service reference: meesho_categories, shipping_slabs (read-only seed)
├── schema: svc_auth         # users, otps, refresh_token_allowlist
├── schema: svc_catalog      # catalogs, skus, catalog_meta
├── schema: svc_image        # image_assets, processing_jobs
├── schema: svc_quality      # quality_checks, rule_evaluations
├── schema: svc_pricing      # pnl_calculations, pricing_overrides
├── schema: svc_ai           # ai_ops_ledger, prompt_versions, ai_budget_state
├── schema: svc_export       # export_jobs, export_history
└── schema: svc_billing      # subscriptions, razorpay_webhooks, plan_guard_state
```

Each service connects with its own DB role:

```
psql role svc_auth          GRANT USAGE ON SCHEMA svc_auth TO svc_auth;
                            GRANT ALL ON ALL TABLES IN SCHEMA svc_auth TO svc_auth;
                            GRANT USAGE ON SCHEMA shared TO svc_auth;       # read-only on shared
                            GRANT SELECT ON ALL TABLES IN SCHEMA shared TO svc_auth;
```

Roles + schema creation lives in a bootstrap migration (`alembic` step zero, owned by infra). Each service's `DATABASE_URL` includes `search_path=svc_<name>,shared` so its Alembic migrations only see its own schema:

```
DATABASE_URL = postgresql+asyncpg://svc_auth:<pw>@postgres.dev.svc.cluster.local:5432/meesell?options=-csearch_path%3Dsvc_auth,shared
```

### 3.2 Alembic per service

| Aspect | Approach |
|---|---|
| Migration ownership | Each service owns `<service>/alembic/` directory in its repo / monorepo path |
| Migration head | Per-schema head — `svc_auth` head is independent of `svc_catalog` head |
| When migrations run | In the CI/CD pipeline, **before** the service's new image rolls (DEVOPS §7.4 migration-before-deploy pattern, applied per-service) |
| Migration runner | A short-lived K8s Job per service: `Job/svc-<name>-migrate-<sha>` that runs `alembic upgrade head` against its schema, succeeds, then the rolling Deployment update kicks off |
| Migration role | A privileged DB role `<service>_migrator` with DDL on its own schema (`svc_<name>`) but NOT on others |
| Backup before migration | The nightly `backup-cronjob` (already exists) covers DR; for risky migrations, an ad-hoc `pg_dump --schema=svc_<name>` runs before the migration Job |

The deploy script changes from one Alembic call to N. The deploy section (§5.6) shows the matrix-aware version.

### 3.3 Connection pool sizing — IMPORTANT

Current monolith budget (verified in MEMORY 2026-06-08):
- Postgres `max_connections = 100`, baseline 6 idle backend connections.
- 2 api × pool_size=15 + 2 worker × pool_size=15 = 60 connections at full load. 60 + 6 = 66 < 100. OK.

After microservicing (worst case, all 8 services live with default 2+1 replica shape):
- 8 × (2 api × pool_size=15 + 1 worker × pool_size=15) = 8 × 45 = **360 connections**.
- 360 + 6 = **366 connections — far exceeds `max_connections=100`.**

This is the single most important infra constraint of the migration.

**Mitigation, in priority order:**

1. **Right-size per-service pool_size in code.** Most services don't need pool_size=15. A reasonable starting matrix:

   | Service | api pool_size | worker pool_size | Notes |
   |---|---|---|---|
   | svc-auth | 10 | 5 | High request rate; OTP send/validate is fast |
   | svc-catalog | 10 | 5 | Read-heavy CRUD |
   | svc-image | 5 | 5 | Image work is I/O bound on GCS, not DB |
   | svc-quality | 5 | 2 | Eval is CPU-bound, DB used to fetch + write result |
   | svc-pricing | 5 | 2 | Mostly arithmetic |
   | svc-ai | 5 | 5 | LLM calls dominate; DB used for ledger writes |
   | svc-export | 3 | 5 | Worker-heavy; api is just job submission |
   | svc-billing | 5 | 2 | Low request rate (webhooks) |
   | **Subtotal pools** | **48** | **31** | |
   | **Total at 2 api + 1 worker replica each** | **2 × 48 = 96** | **1 × 31 = 31** | Sum = 127 |

   With the matrix above: 127 + 6 = 133 connections. Still over 100. Either raise `max_connections` to 200 (modest memory cost, ~5MB/conn = +500MB on postgres pod), or:

2. **Introduce PgBouncer in transaction-pool mode** between the services and Postgres. PgBouncer with `pool_mode=transaction` lets 200 application connections multiplex onto 20 real backend connections. This is the standard pattern for microservices on shared Postgres.

   New K8s objects:
   ```
   Deployment/pgbouncer     (2 replicas)
   Service/pgbouncer        ClusterIP :6432 -> :6432
   ConfigMap/pgbouncer-config   (pool sizing per-database; auth via userlist.txt)
   Secret/pgbouncer-userlist    (per-service DB credentials)
   ```
   Services connect to `pgbouncer:6432` instead of `postgres:5432`. **Caveat:** transaction-pool mode forbids SET LOCAL / prepared statements that span transactions; SQLAlchemy must be configured with `pool_pre_ping=False` and `executemany_mode='values_only'` for asyncpg. Test driver compatibility before committing.

3. **Bump `max_connections` to 200** as a stopgap if PgBouncer slips. Cost: ~+500MB postgres pod memory. Acceptable on `e2-standard-2`.

**Recommended path:** Sub-plan MS-DB-3 ships per-service pool sizing in code + `max_connections=200` (low risk). Sub-plan MS-DB-4 introduces PgBouncer (medium risk) before staging cutover. PgBouncer becomes mandatory before any traffic-bearing prod traffic.

### 3.4 What stays in the `shared` schema (read-only seeds)

- `meesho_categories` (loaded from `app/data/meesho_categories.json` at startup)
- `meesho_shipping_slabs`
- `category_attributes`
- `banned_words`

Owned by infra (a bootstrap migration). Mutations are forbidden at runtime; loaded once on app startup. Sub-plan MS-DB-1 covers the schema bootstrap.

---

## 4. Valkey Strategy

### 4.1 Current DB allocation (verified live in MEMORY)

```
DB 0: sessions, OTP, rate limits (the current monolith's auth + middleware state)
DB 1: Celery broker
DB 2: Celery result backend
DB 3: reserved / unused
```

Valkey supports 16 logical DBs by default (DB 0-15). Each DB is a fully isolated keyspace. This is enough for V1's 8 services without spinning up a second Valkey instance.

### 4.2 Target allocation (recommended)

| Valkey DB | Purpose | Owner |
|---|---|---|
| 0 | Shared sessions + global rate limits | svc-auth + api-gateway |
| 1 | Celery broker — `svc-auth` queue | svc-auth-worker |
| 2 | Celery broker — `svc-catalog` queue | svc-catalog-worker |
| 3 | Celery broker — `svc-image` queue | svc-image-worker |
| 4 | Celery broker — `svc-quality` queue | svc-quality-worker |
| 5 | Celery broker — `svc-pricing` queue | svc-pricing-worker |
| 6 | Celery broker — `svc-ai` queue | svc-ai-worker |
| 7 | Celery broker — `svc-export` queue | svc-export-worker |
| 8 | Celery broker — `svc-billing` queue | svc-billing-worker |
| 9-15 | Celery result backend (shared, prefixed by service) | all workers |

This keeps each service's queue isolated (one service's queue depth doesn't crowd another), reduces single-service blast radius if a queue blocks, and stays within the 16-DB limit.

**Alternative (deferred):** separate Valkey instance per service (`valkey-auth`, `valkey-catalog`, …). Cost: 8 × 200Mi pod memory, 8 × 5Gi PVCs. Defer to V1.5 only if cross-service Valkey contention shows up as latency in metrics.

### 4.3 Per-service prefix namespacing

Inside a shared DB (DB 0 for sessions, DBs 9-15 for results), keys are namespaced by service:

```
session:svc-auth:<jwt-jti>
ratelimit:svc-catalog:user-<uuid>:60
celery-result:svc-export:<task-id>
```

Documented in the shared ConfigMap and enforced by code review (no infra-side enforcement primitive — Valkey doesn't have per-key ACL granularity).

### 4.4 Memory budget

Current Valkey limit: `maxmemory 128mb`, `maxmemory-policy allkeys-lru`. 8 services using 8 broker DBs + shared sessions can blow this budget if queue depth gets large.

**Recommendation:** raise `maxmemory` to `512mb` as part of the migration (Sub-plan MS-CACHE-1). Tuning of `--maxmemory-policy` may shift from `allkeys-lru` to `volatile-lru` so Celery queue keys (which have no TTL by design) aren't evicted while session keys (which have TTL) are.

PVC sizing stays at 5Gi (Valkey is mostly in-memory; AOF on disk is small).

---

## 5. CI/CD Changes

### 5.1 Current

- Single `cloudbuild.yaml` builds `api` + `worker` images (worker reuses api image, different CMD).
- Single GitHub Actions job sequence (5 CI gates → 1 build → 1 deploy).
- Deploy is `kubectl set image deployment/api ... && kubectl set image deployment/worker ...` → smoke check `https://api.mesell.xyz/health`.

### 5.2 Target — recommend monorepo with matrix build, 8 image targets

**Code-layout assumption (out of infra scope, but pipeline cares):** the backend stays a single monorepo with per-service subdirectories:

```
backend/
├── shared/                  # SQLAlchemy base, common middleware, shared utils
├── services/
│   ├── svc-auth/
│   │   ├── Dockerfile
│   │   ├── app/
│   │   ├── alembic/
│   │   └── pyproject.toml
│   ├── svc-catalog/
│   │   ├── Dockerfile
│   │   ...
│   └── svc-billing/
└── cloudbuild.yaml          # 8-image build orchestration
```

Each service has its own `Dockerfile` so it can be built independently.

**[OPEN DECISION — MS-CI-1]:** Multi-image vs one-image-multi-CMD.

| Option | Build cost | Image size | Deploy granularity |
|---|---|---|---|
| **(A) 8 distinct images** (recommended) | 8× build time on full rebuild (mitigated by Cloud Build cache + path-filter triggers) | Each ~400MB; total registry footprint ~3.2GB per SHA | Per-service: changing svc-pricing doesn't rebuild svc-auth |
| (B) 1 monolith image, 8 CMDs | 1× build time | Each pod pulls ~1.2GB (whole monolith); registry footprint 1.2GB per SHA | Coarse: every service rolls on every build |
| (C) 1 base image + 8 thin app images (multi-stage with shared base) | 1× shared build + 8× thin app builds | Base 800MB cached, app layers 100MB each | Per-service rebuild on app-layer change; base rebuild when shared deps change |

**Recommendation: (A) for V1**, **(C) as the V1.5 optimization** once Cloud Build minutes become a real cost. (A) maximizes independence — the whole point of microservicing. (B) defeats the purpose.

### 5.3 Path-filter triggers (build only the changed service)

GitHub Actions `on.push.paths` filter (or `paths-filter` action) examines the diff:

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            svc-auth:    'backend/services/svc-auth/**'
            svc-catalog: 'backend/services/svc-catalog/**'
            svc-image:   'backend/services/svc-image/**'
            svc-quality: 'backend/services/svc-quality/**'
            svc-pricing: 'backend/services/svc-pricing/**'
            svc-ai:      'backend/services/svc-ai/**'
            svc-export:  'backend/services/svc-export/**'
            svc-billing: 'backend/services/svc-billing/**'
            shared:      'backend/shared/**'

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.services != '[]'
    strategy:
      matrix:
        service: ${{ fromJSON(needs.detect-changes.outputs.services) }}
    steps:
      - run: gcloud builds submit --config=cloudbuild.yaml --substitutions=_SERVICE=${{ matrix.service }} ...
```

**Rule:** if `shared/**` changed, ALL 8 services rebuild (the diff to `shared` invalidates every downstream image).

**Migration matrix entries** are derived the same way — each service's `Job/svc-<name>-migrate-<sha>` is created only for services in the diff. Order:

```
matrix: [svc-auth, svc-catalog, ...]   # in parallel
  └─► run migration Job for that service
  └─► wait until Job succeeds
  └─► kubectl set image deployment/svc-<name>-api  + svc-<name>-worker
  └─► kubectl rollout status   (per service, parallel)
  └─► smoke-check that service's /health
  └─► if any failed: kubectl rollout undo for that service
```

### 5.4 cloudbuild.yaml changes

Today's `cloudbuild.yaml` has 2 image targets (api + worker, with conditional frontend). Target:

```yaml
# cloudbuild.yaml (after microservicing)
substitutions:
  _SERVICE: ""               # set by GitHub Actions matrix; one of svc-auth, svc-catalog, ...
  _TAG: ""                   # github.sha
  _PROJECT_ID: project-1f5cbf72-2820-4cdb-949
  _REGION: asia-south1
  _REPO: meesell-prod-images

steps:
  - id: clone
    name: gcr.io/cloud-builders/git
    args: ['clone', '--depth=1', '--branch=main', 'https://github.com/Mugunthan93/mesell.git', '/workspace/src']

  - id: build
    name: gcr.io/cloud-builders/docker
    args:
      - build
      - -t
      - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/${_SERVICE}:${_TAG}
      - -t
      - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/${_SERVICE}:latest
      - -f
      - /workspace/src/backend/services/${_SERVICE}/Dockerfile
      - /workspace/src/backend

  - id: push
    name: gcr.io/cloud-builders/docker
    args: [push, --all-tags, ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/${_SERVICE}]

images:
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/${_SERVICE}:${_TAG}
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/${_SERVICE}:latest

timeout: 1200s
```

The current frontend conditional precheck pattern stays (in a separate Cloud Build invocation triggered by the frontend matrix branch — already present).

### 5.5 Artifact Registry layout

| Today | Target |
|---|---|
| `meesell-prod-images/api` | `meesell-prod-images/svc-auth`, `.../svc-catalog`, ... (8 image streams) |
| `meesell-prod-images/worker` | NONE — worker reuses the service's image (`svc-auth`, `svc-catalog`, etc.) with a different CMD |
| `meesell-prod-images/frontend` | unchanged |

AR cleanup policy is per-stream: keep last 10 SHAs + all `:latest` + all `:v*.*.*` per service. No infra-side change needed (policy is already cleanup-on-count, not stream-specific).

### 5.6 Deploy job changes

Today's deploy is a single IAP-tunneled SSH that runs `kubectl set image deployment/api` + `kubectl set image deployment/worker`. After microservicing:

```bash
# inside the IAP-tunneled SSH, for the changed service set $SERVICE
IMAGE=asia-south1-docker.pkg.dev/${PROJECT_ID}/meesell-prod-images/${SERVICE}:${TAG}

# 1. Apply shared/per-svc manifests (idempotent)
kubectl apply -f ~/mesell/k8s/shared/
kubectl apply -f ~/mesell/k8s/services/${SERVICE}/

# 2. Run the migration Job (per-service)
kubectl delete job ${SERVICE}-migrate-${TAG} -n dev --ignore-not-found
envsubst < ~/mesell/k8s/services/${SERVICE}/migration-job.yaml | kubectl apply -f -
kubectl wait --for=condition=complete job/${SERVICE}-migrate-${TAG} -n dev --timeout=300s

# 3. Roll the api + worker for THIS service only
kubectl -n dev set image deployment/${SERVICE}-api    ${SERVICE}-api=${IMAGE}
kubectl -n dev set image deployment/${SERVICE}-worker ${SERVICE}-worker=${IMAGE}
kubectl -n dev rollout status deployment/${SERVICE}-api    --timeout=180s
kubectl -n dev rollout status deployment/${SERVICE}-worker --timeout=180s

# 4. Smoke check that service's /health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.mesell.xyz/${SERVICE#svc-}/health)
[ "$HTTP_CODE" = "200" ] || { kubectl rollout undo deployment/${SERVICE}-api -n dev; exit 1; }
```

GitHub Actions runs this for each entry in the `detect-changes` matrix in parallel. Cross-service rollouts that need ordering (e.g., schema change in `shared` consumed by both svc-catalog and svc-pricing) are handled with a `needs: [<other-svc>]` dependency in the workflow.

### 5.7 Rollback behavior

`kubectl rollout undo deployment/svc-<name>-api` reverts only that service. The previous SHA's image is still in AR (cleanup policy keeps the last 10). One bad service no longer drags down the others — the principal CI/CD win of microservicing.

---

## 6. Dev + Staging Environment Design

### 6.1 Dev — recommendation: single K3s node, all 8 services

The existing `meesell-dev` VM is `e2-standard-2` (2 vCPU, 8 GB RAM). Today's workload:

| Pod | CPU req | Memory req |
|---|---|---|
| postgres | 200m | 500Mi |
| valkey | 100m | 200Mi |
| supabase-studio | 100m | 256Mi |
| traefik | (Helm default) ~100m | ~150Mi |
| cert-manager (3 pods) | ~150m | ~300Mi |
| K3s system pods (coredns, local-path, metrics-server, svclb) | ~150m | ~250Mi |
| api × 2 | 400m | 1024Mi |
| worker × 2 | 500m | 1024Mi |
| **Subtotal** | **~1700m / 2000m** | **~3700Mi / 8192Mi** |

CPU is the binding constraint. After microservicing with the §6.3 sizing matrix, the new app-pod CPU request is **2160m** for 24 service pods — by itself this OVER-subscribes the 2 vCPU node before counting infra pods.

**Conclusion:** the current `e2-standard-2` cannot host all 8 microservices at 2 api + 1 worker replicas with safe requests. Two options:

| Option | Spec | Monthly cost (asia-south1) | Notes |
|---|---|---|---|
| **(A) Keep current VM, run services at 1 api + 1 worker replica each, with reduced CPU requests** | `e2-standard-2` | unchanged (~₹2,600/mo full-time) | Loses HA at the api layer; acceptable for dev only |
| **(B) Upgrade dev VM to `e2-standard-4`** (4 vCPU, 16 GB) | `e2-standard-4` | ~₹5,200/mo | Lets dev run the full 2+1 shape; matches future staging spec |
| **(C) Keep `e2-standard-2` dev, accept that some services are co-tenanted (sidecar-style)** | `e2-standard-2` | unchanged | Adds complexity to k8s manifests; rejected for V1 |

**Recommendation: (A) for V1 dev**, **(B) when budget allows or when the team grows past 1 backend engineer.** The current ₹25,000 budget cap (`meesell-dev-budget`) is well under the upgraded-VM cost — Option B is affordable from the GCP free credit standpoint.

> **SUPERSEDED 2026-06-10 (D3 founder ruling, this revision).** The "Option (A) for V1 dev" recommendation above is overtaken by **founder ruling D3: the dev VM upgrade `e2-standard-2 → e2-standard-4` is PRE-APPROVED (~₹2,600/mo), to take effect ONLY when extraction begins post-V1.** This is a plan lock, not a purchase — the upgrade is held until the first extraction (Sub-Plan A) is dispatched, then executed via Sub-Plan **MS-ENV-2**. The founder explicitly signed off above the ₹500/mo cost gate, so the §6.3 CPU-budget surgery on `e2-standard-2` (Option A mitigations) is NO LONGER the V1.5 extraction path: **Option (B) `e2-standard-4` is the ratified target the moment extraction starts.** Option (A) remains valid ONLY for the pre-extraction V1 monolith (which already fits the 2 vCPU node). Read every downstream "fit on `e2-standard-2`" mitigation in §6.3 / R-MS-2 / R-MS-13 as a fallback that D3 makes unnecessary at extraction time.

### 6.2 Staging — recommendation: separate VM (`meesell-staging`)

Today's `staging` is a namespace on `meesell-dev`. After microservicing, the per-pod count goes from 4 to 24 *per environment*. Cramming dev + staging on the same `e2-standard-2` node is unsafe. Three options:

| Option | What changes | Pros | Cons |
|---|---|---|---|
| **(A) Same VM, separate staging namespace** | No infra change; staging adds ~24 more pods to the dev VM | Cheapest; mirrors live "staging-as-namespace" pattern from DEVOPS doc | The 2 vCPU node is already over capacity; staging traffic will degrade dev |
| **(B) Separate VM for staging** (recommended) | New `meesell-staging` VM (`e2-standard-2` initially, `e2-standard-4` later); separate K3s cluster | Clean blast-radius separation; staging can test infra changes (K3s version, Traefik upgrades) | New TF module; new VM cost (~₹2,600/mo); two clusters to operate |
| **(C) GKE multi-node cluster shared by dev + staging + prod** | Replace K3s with GKE; node pools per environment | Production-grade; auto-scaling | Large rewrite of infra; GKE control-plane cost (~$70/mo); deferred to V1.5 |

**Recommendation: (B)** — a sibling VM `meesell-staging` with its own single-node K3s. Same Terraform modules, parameterized by environment. Re-use the existing TF `vm` + `firewall` + ingress modules. K3s control plane on each VM is cheap (~200MB RAM).

Sub-plan MS-ENV-1 covers the VM provisioning. The existing `meesell-prod-budget` covers spend; no new budget needed.

### 6.3 Resource estimates per service (e2-standard-2 dev sizing)

Per service, with 1 api + 1 worker replica (dev V1):

| Service | api CPU req | api Mem req | worker CPU req | worker Mem req | Justification |
|---|---|---|---|---|---|
| svc-auth | 100m | 256Mi | 50m | 128Mi | Light; OTP send is mostly outbound HTTP |
| svc-catalog | 150m | 384Mi | 100m | 256Mi | Read-heavy CRUD; cache hits dominate |
| svc-image | 100m | 256Mi | 250m | 512Mi | Worker runs rembg (CPU-bound) |
| svc-quality | 100m | 256Mi | 100m | 256Mi | Rules engine is CPU; eval is in worker |
| svc-pricing | 50m | 128Mi | 50m | 128Mi | Mostly arithmetic |
| svc-ai | 100m | 256Mi | 150m | 384Mi | LLM calls are I/O bound; worker holds prompt-template cache |
| svc-export | 50m | 128Mi | 200m | 512Mi | XLSX generation is CPU + memory-heavy |
| svc-billing | 50m | 128Mi | 50m | 128Mi | Webhook receiver + low job volume |
| api-gateway | 100m | 128Mi | n/a | n/a | Thin proxy |
| **Subtotal** | **800m** | **1920Mi** | **950m** | **2304Mi** | |
| **Grand total app pods** | **1750m** | **~4.1Gi** | | | |

Plus infra pods at ~700m / ~1.7Gi (unchanged). Total ~2450m CPU request on a 2 vCPU node = **OVER capacity** by ~450m.

**Mitigations to fit on `e2-standard-2`:**

1. Drop replicas to 1 api / 1 worker per service in dev (already assumed above).
2. Right-size requests further (e.g., svc-billing at 25m CPU request).
3. Use `priorityClass` to prefer api over worker on contention.
4. Accept that scheduling will reject the 8th-or-9th pod when the budget overflows — visible failure, then tune.

The honest read: §6.1 Option (B) (upgrade to `e2-standard-4`) is the path that just-works. (A) requires CPU-budget surgery.

### 6.4 Where prod fits

Prod stays deferred per the playbook (Week 2 after staging clean for a week). With microservicing, prod's spec target jumps from `e2-standard-2` to **at least `e2-standard-4`**, possibly `e2-highmem-4` if Postgres connection-pool memory grows. Sub-plan MS-ENV-3 details the prod sizing — out of V1 scope.

---

## 7. Sub-Plans

Each sub-plan is one self-contained infra change. Complexity: S (≤ 1 day), M (2-3 days), L (≥ 4 days). Dependencies refer to other sub-plan IDs.

| ID | Name | Description | Complexity | Dependency | Effort |
|---|---|---|---|---|---|
| MS-DB-1 | Schema bootstrap migration | Create `shared` + 8 `svc_*` schemas; create per-service DB roles + grants; seed `shared` from JSON files | M | — | 2d |
| MS-DB-2 | Per-service Alembic chains | Split current single Alembic chain into 8 per-service chains; document head-per-schema | M | MS-DB-1 | 2d |
| MS-DB-3 | Connection pool resizing + max_connections=200 | Per-service `pool_size` matrix in code; `postgresql.conf` bump | S | — | 1d |
| MS-DB-4 | PgBouncer in transaction-pool mode | Deployment + Service + Secret/userlist; verify asyncpg + transaction pooling compatibility | L | MS-DB-3 | 4d |
| MS-CACHE-1 | Valkey DB-allocation + maxmemory bump | Update ConfigMap with Valkey DB map; bump `maxmemory` to 512mb; switch to `volatile-lru` | S | — | 1d |
| MS-K8S-1 | Per-service K8s manifest skeleton | Author `k8s/services/svc-<name>/` for all 8 services (Deployment×2, Service, SA) | M | MS-DB-1 | 3d |
| MS-K8S-2 | Shared ConfigMap + Secret refactor | Split `meesell-config` and `backend-secrets` into shared + per-service; move Razorpay to svc-billing only | M | MS-K8S-1 | 2d |
| MS-K8S-3 | NetworkPolicy default-deny + per-svc allow | Default-deny ingress in `dev` ns; per-service allow rules; gateway ingress allow | M | MS-K8S-1 | 2d |
| MS-K8S-4 | Workload Identity per service (GCP IAM) | New TF `module.svc_workload_identity` mapping each svc SA to GCP IAM; grant svc-image → GCS bucket only, svc-billing → razorpay secrets only | L | MS-K8S-1 | 4d |
| MS-GW-1 | Traefik IngressRoute for path-prefix routing | Replace single `api` Ingress with IngressRoute CRD listing all 8 services; preserve TLS cert | M | MS-K8S-1 | 2d |
| MS-GW-2 | Aggregate health endpoint (gateway) | Implement gateway `/health/aggregate` that hits all 8 svc-*/health; replace deploy smoke check | S | MS-GW-1 | 1d |
| MS-CI-1 | Monorepo path-filter + matrix build | `dorny/paths-filter` job; matrix build per service; `cloudbuild.yaml` parameterized on `_SERVICE` | M | MS-K8S-1 | 3d |
| MS-CI-2 | Per-service migration Jobs in deploy step | Replace `kubectl exec ... alembic upgrade head` with per-service Job + wait | M | MS-DB-2, MS-CI-1 | 2d |
| MS-CI-3 | Per-service rolling deploy + rollback | Restructure deploy script to per-service `kubectl set image` + per-service smoke check + per-service rollout undo | M | MS-CI-1 | 2d |
| MS-ENV-1 | Provision `meesell-staging` VM | New TF env (`environments/staging.tfvars`); reuse `module.vm` + `module.firewall`; install K3s | M | — | 3d |
| MS-ENV-2 | Upgrade dev VM to `e2-standard-4` (optional, recommended) | `terraform plan -var "vm_machine_type=e2-standard-4"`; cordon + drain + resize | S | — | 1d |
| MS-ENV-3 | Prod VM sizing + namespace | Defer to Week 2 prod cutover; document sizing matrix | M | MS-ENV-1 | 3d |
| MS-OBS-1 | Per-service Prometheus scrape config | Phase I monitoring stack treats each `svc-*` as a separate scrape job; per-service dashboards | M | (Phase I) | 3d |
| MS-OBS-2 | Service-level SLO + alert per service | 8 `Slo`+`PrometheusRule` resources; gateway-level 5xx burn alert | M | MS-OBS-1 | 2d |
| MS-DOC-1 | Update INFRASTRUCTURE_ARCHITECTURE.md SSOT | Add §6.5 microservices topology; refresh diagram; document new service DNS map | S | MS-K8S-1, MS-GW-1 | 1d |
| MS-DOC-2 | Update DEVOPS_ARCHITECTURE.md | Replace §6 + §7 with matrix-build + per-service deploy; document MS-CI-* changes | S | MS-CI-3 | 1d |

**Suggested execution order:**

1. Foundations (parallel-safe): MS-DB-1, MS-CACHE-1, MS-ENV-1
2. Data layer: MS-DB-2, MS-DB-3
3. K8s layer: MS-K8S-1, MS-K8S-2, MS-K8S-3
4. Gateway: MS-GW-1, MS-GW-2
5. CI/CD: MS-CI-1, MS-CI-2, MS-CI-3
6. Hardening: MS-DB-4, MS-K8S-4
7. Cut over to staging using new pipeline; observe a week
8. Cut over prod (MS-ENV-3)
9. Docs (MS-DOC-1, MS-DOC-2) — running alongside, finalized at end

**Total estimated effort:** ~45 engineer-days for infra alone (excluding backend domain refactor).

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-MS-1 | Connection pool storm crashes Postgres on first staging cutover | High | Critical | MS-DB-3 (right-size pools) ships before any service moves; MS-DB-4 (PgBouncer) is mandatory before traffic-bearing prod cutover. Pre-flight: load test with `pgbench -c 360` against staging. |
| R-MS-2 | Single-node K3s cannot fit all 8 services + infra pods on `e2-standard-2` | Certain | High | MS-ENV-2 (upgrade dev VM) or §6.3 mitigations (smaller requests, 1 replica). Budget allows the upgrade; recommend taking it. |
| R-MS-3 | Cross-service migration ordering causes service B to boot against pre-migrated schema | Medium | High | MS-CI-2 ships migration Jobs that block the rollout. Migrations are forward-compatible (DEVOPS doc §12.2 rule). Cross-service schema changes go through the `shared` schema, owned by infra, applied first. |
| R-MS-4 | Default-deny NetworkPolicy locks out svc-to-svc traffic, taking down prod silently | Medium | Critical | MS-K8S-3 ships allow rules first, default-deny later, behind a feature flag. Validation gate: `pytest -m "integration"` exercises all svc-to-svc paths before flip. |
| R-MS-5 | Path-prefix routing breaks current `https://api.mesell.xyz/<route>` clients (mobile + frontend) | Medium | High | MS-GW-1 introduces prefixes incrementally: gateway initially proxies all paths to a single `svc-monolith` (current api pod) while individual services are peeled off. The cut-over per service is one PR each. |
| R-MS-6 | Workload Identity per-service IAM mapping leaks blast radius (one svc can read another's secrets) | Medium | Critical | MS-K8S-4 is a deliberate hardening step (not the V1 default). For V1, all services keep the shared VM SA; per-service SAs ship in V1.5 after the GKE evaluation. |
| R-MS-7 | Cloud Build minutes overshoot free tier when all 8 services rebuild from a `shared/` change | Medium | Medium | Sub-plan MS-CI-1 includes Docker BuildKit + layer caching; revisit MS-CI-1 with multi-stage shared-base (Option C in §5.2) if cost shows up in billing alerts. |
| R-MS-8 | PgBouncer transaction-pool mode breaks SQLAlchemy async features (LISTEN/NOTIFY, prepared statements) | Medium | High | MS-DB-4 validation step: smoke-test each service's full integration suite against PgBouncer in a dedicated `pre-pgbouncer-cutover` test environment. Fall back to session-pool mode (lower multiplexing) if transaction mode fails. |
| R-MS-9 | One service's runaway memory leak triggers OOMKilled cascade as kubelet evicts neighbors | High | High | Per-pod memory LIMITS (not just requests). Set `memory: limit = 2 × request`. Configure K3s `--system-reserved-memory=512Mi` and `--kube-reserved-memory=512Mi`. |
| R-MS-10 | Migration window grows from ~5s (monolith) to ~90s (8 sequential Job invocations) | High | Medium | MS-CI-2: run migration Jobs in parallel per-service since each only touches its own schema. Document the path: migrations remain forward-compatible so order doesn't matter for the same SHA. |
| R-MS-11 | Loss of cross-domain DB integrity (FKs that span schemas) | Medium | Medium | Backend coordinator owns this — a code-side concern. Infra documents which schema each table lives in (MS-DB-1 deliverable). Soft-FKs (UUID, no DB enforcement) become the pattern across schema boundaries. |
| R-MS-12 | TLS cert renewal failure on cert-manager because path-prefix routing's IngressRoute structure confuses ACME HTTP-01 challenge | Low | High | MS-GW-1 validation: trigger a manual cert renewal (`cmctl renew`) on staging before going live. Have a rollback Ingress (`k8s/ingress.yaml`) ready to re-apply. |
| R-MS-13 | Increased control-plane chatter (24 pods churning) saturates K3s etcd on a 2 vCPU VM | Low | Medium | K3s uses sqlite by default (not etcd). Monitor `apiserver_request_duration_seconds`. If saturation appears, MS-ENV-2 (upgrade dev VM) becomes mandatory. |

---

## 9. What this plan deliberately does NOT cover

- Backend code refactor (how to split `app/services/*.py` into per-service packages) — owned by `meesell-backend-coordinator`
- Per-service test strategy / contract tests between services — owned by backend coordinator
- Feature-flag system for incremental cut-over (svc-by-svc gradual rollout) — out of infra scope
- Service mesh (Linkerd / Istio) — explicitly deferred; the single-node + 8-services scale doesn't justify a mesh in V1
- Cross-region deployment / multi-AZ — out of V1
- Cost reduction by spot-VM workers — out of V1
- Per-service docs/runbooks — owned by individual specialist agents after the migration lands

---

**End of plan. APPROVED 2026-06-10 — founder-ratified via the S4 ratification package.**

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1.0 | 2026-06-10 | meesell-infra-builder | Initial DRAFT — infra changes to evolve the monolith into 8 microservices on K3s. |
| v1.1 | 2026-06-10 | meesell-backend-coordinator (landing founder rulings D3–D7) | DRAFT → **APPROVED**. Two must-fix deltas landed: (1) §6.1 Option (A) recommendation SUPERSEDED by **D3** — `e2-standard-4` VM upgrade pre-approved (~₹2,600/mo, founder cost-gate sign-off), execution-time at first extraction via MS-ENV-2; the `e2-standard-2` CPU-budget mitigations become fallback-only. (2) Glossary invented service names (`svc-quality`, `svc-billing`) SUPERSEDED — authoritative 8 services are the MASTER_PLAN §1.A modules (`iam`/`customer`/`category`/`catalog`/`image`/`pricing`/`dashboard`/`export`). Header STATUS records **D4** (Traefik path-prefix gateway) + **D5** (pools right-size → PgBouncer-before-cutover) per the §3.3 / §2.4 recommendations the founder concurred with. |
