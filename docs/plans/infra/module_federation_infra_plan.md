# Module Federation Infrastructure Master Plan

**STATUS: APPROVED 2026-06-10 — ratified by founder. Hosting model LOCKED: Option C (shell in-cluster + 6 remotes GCS/CDN static at remotes.mesell.xyz). Gate-4 conditions C-RES-1/2, C-ROUTE-1, C-CI-1, C-CSP-1, C-STAGING-1 adopted as Sub-plan 7 requirements. See docs/plans/infra/GATE4_CONFIRMATION.md.**

**Scope:** Infrastructure changes required to evolve the MeeSell frontend from a single Angular nginx pod into a Module Federation topology — one shell app plus N independently built, deployed, and versioned remote micro-frontends.

**Source of truth read at draft time:** `docs/INFRASTRUCTURE_ARCHITECTURE.md`, `docs/DEVOPS_ARCHITECTURE.md`, `docs/status/STATUS_INFRA.md`, `k8s/frontend.yaml`, `k8s/ingress.yaml`, `.claude/agent-memory/meesell-infra-builder/MEMORY.md`.

**Constraint:** This is a planning document only. No K8s, Terraform, or code changes are part of this deliverable. Angular tooling specifics (webpack configs, `ModuleFederationPlugin` options) are noted only where they constrain infra; the wiring is owned by `meesell-frontend-coordinator`.

---

## Glossary (used throughout)

| Term | Meaning in this plan |
|---|---|
| **Shell** | The host Angular app at `https://dev.mesell.xyz`. Owns routing, layout chrome, auth context, and `loadRemoteModule()` calls. |
| **Remote** | An independently built Angular app exposing one or more standalone components/routes. The shell loads remotes at runtime. |
| **Manifest** | A small JSON file (`remotes.manifest.json`) the shell fetches at startup that maps remote name → URL. Decouples shell builds from remote URL changes. |
| **Entry file** | `remoteEntry.js` — the Webpack-emitted entry point of a remote. URL of this file IS the remote's address. |
| **`mfe-*`** | Slug prefix for remotes (e.g., `mfe-catalog`, `mfe-quality`). Matches a K8s app label and image stream name. |

### Provisional remote set (illustrative, owned by frontend coordinator)

Aligns with V1's 8 backend domains (matches `microservices_infra_plan.md` for symmetry). Final remote split is a frontend decision — this list is what infra plans against:

| # | Remote | Routes hosted | Owns backend dependency |
|---|---|---|---|
| 1 | `mfe-onboarding` | `/login`, `/verify-otp`, `/profile-setup` | svc-auth |
| 2 | `mfe-dashboard` | `/dashboard` | svc-catalog (read) |
| 3 | `mfe-catalog` | `/catalog/create`, `/catalog/:id`, `/sku/*` | svc-catalog, svc-image |
| 4 | `mfe-quality` | `/quality/:catalogId` | svc-quality |
| 5 | `mfe-pricing` | `/pricing/:skuId` | svc-pricing |
| 6 | `mfe-export` | `/export/:catalogId` | svc-export |
| 7 | `mfe-billing` | `/billing`, `/subscription` | svc-billing |
| 8 | `shell` | `/`, navbar, auth interceptor, route table | (composes the above) |

Total: 1 shell + 7 remotes = 8 frontend deploy units.

---

## 1. Current vs Target

### 1.1 Current

```
namespace: dev
  Deployment/frontend     2 replicas (planned — image not yet built)
  Service/frontend        ClusterIP :80 -> :80
  Ingress/dev.mesell.xyz  -> frontend
  Ingress/testing.mesell.xyz -> frontend
namespace: staging
  Ingress/staging.mesell.xyz -> frontend (no backend pods yet)
namespace: prod
  (Week 2 — Ingress/www.mesell.xyz pending)
```

Single Angular build → single image → single nginx pod serves index.html + all JS/CSS chunks for every page. Caching is per-asset (filename hashes), but any change to any route → rebuild + redeploy of the whole image.

### 1.2 Target

```
namespace: dev
  # Shell: routing, layout, auth, manifest fetch
  Deployment/mfe-shell                  2 replicas
  Service/mfe-shell                     ClusterIP :80 -> :80

  # Remotes: each independently deployed
  Deployment/mfe-onboarding             1 replica (or static — see §2)
  Deployment/mfe-dashboard              1 replica
  Deployment/mfe-catalog                1 replica
  Deployment/mfe-quality                1 replica
  Deployment/mfe-pricing                1 replica
  Deployment/mfe-export                 1 replica
  Deployment/mfe-billing                1 replica
  Service/mfe-<name>                    ClusterIP :80 -> :80 (one per remote)

  ConfigMap/remotes-manifest            served by mfe-shell at /assets/remotes.manifest.json

  # Ingress entry point — single host, path-based routing to remotes
  Ingress/dev.mesell.xyz                see §3 for the path structure
```

The shell still owns the public URL (`dev.mesell.xyz`). Remotes are served either from in-cluster nginx pods (Option A) OR from a GCS bucket + Cloud CDN (Option B). The strategy decision is §2.

### 1.3 Sizing comparison

| Aspect | Current | Target (in-cluster Option A) | Target (GCS/CDN Option B) |
|---|---|---|---|
| Deployments | 1 (frontend) | 8 (shell + 7 remotes) | 1 (shell) + GCS storage |
| Services | 1 | 8 | 1 |
| Pods at rest | 2 | 1 shell × 2 + 7 remotes × 1 = 9 | 2 (shell only) |
| Independent build artifacts | 1 image | 8 images | 1 image + 7 GCS asset bundles |
| Independent rollouts | 1 | 8 | 8 (image-only for shell; GCS sync for remotes) |
| Total CPU req | ~200m | ~800m | ~200m |
| Total Mem req | ~256Mi | ~1024Mi | ~256Mi |
| Cache invalidation surface | 1 image's assets | 8 image rollouts | 7 CDN paths to purge |

---

## 2. Static Hosting Strategy

### 2.1 Options

| Option | Where remotes live | Where shell lives | Edge cache |
|---|---|---|---|
| **(A)** All in K3s — each remote in its own nginx pod | K3s pods | K3s pod | Cloudflare-on-top later |
| **(B)** All in GCS + Cloud CDN | GCS bucket per remote (or one bucket with per-remote prefixes) | GCS + Cloud CDN | GCP Cloud CDN |
| **(C)** Shell in K3s, remotes in GCS+CDN | GCS + Cloud CDN | K3s pod | Cloud CDN for remotes; pod for shell |

### 2.2 Trade-off matrix

| Dimension | (A) All K3s | (B) All GCS+CDN | (C) Hybrid |
|---|---|---|---|
| Setup complexity | Low (matches current frontend pattern) | Medium (new buckets, new IAM, CDN config) | Medium |
| Per-remote deploy cost | One Cloud Build + image push + rollout | `gsutil rsync` + cache invalidation | Mixed |
| Egress cost (asia-south1) | Cluster-internal traffic free; client downloads from VM IP (egress charged) | CDN egress is cheaper than VM egress; first byte time is lower globally | Mixed |
| Cache invalidation granularity | Pod restart (chunky) | Per-file with content-hashed filenames (fine) | Per-file for remotes; pod for shell |
| Memory pressure on K3s | +700Mi for 7 nginx pods | 0 | +0 (shell stays) |
| Free tier alignment | Pods on existing VM = no extra cost | GCS storage free up to 5GB; Cloud CDN egress free up to 1GB/mo | Best alignment |
| Failure isolation | Bad remote nginx = 502 for that route | Bad GCS object = 404 (cleaner) | Mixed |
| Dev experience | `ng serve` for local; deploy to K3s for staging | `ng serve` for local; deploy uploads to GCS | Mixed |
| TLS / CORS | Same origin (no CORS), shared cert on `dev.mesell.xyz` | CORS required (different origin); CDN needs its own cert | CORS required for remotes |
| Deploy rollback speed | `kubectl rollout undo` (~5s) | Re-`gsutil rsync` from prior bundle (~30s) | Mixed |

### 2.3 Recommendation

**Option (C) — Hybrid: shell in K3s, remotes in GCS + Cloud CDN — for V1. [LOCKED 2026-06-10 by founder.]** Shell stays in-cluster (backend-service swap on `dev.mesell.xyz`, no cert churn); the 6 remotes are GCS/CDN static at `remotes.mesell.xyz`, OUTSIDE K3s (zero pods, no VM upgrade for federation). The fallback to Option A below is therefore CLOSED — Option C is the committed model.

Why:
- Shell is the auth-aware piece that mutates per release (route table changes, auth interceptor changes). Keeping it in K3s makes it deploy through the same pipeline as the backend: image build, rollout, smoke check.
- Remotes are mostly static SPA bundles that change behind feature work. GCS + CDN gives:
  - Faster page loads (CDN edge in Mumbai matches our asia-south1 audience).
  - Cheaper egress than VM nginx (per the live cost model — VM egress is billed at the GCP per-GB rate; CDN is amortized over the free tier first).
  - Truly independent deploys (no pod restart; no CPU req allocation).
- CORS overhead is one-time config; once `Access-Control-Allow-Origin: https://dev.mesell.xyz` is set on the bucket, the rest is plumbing.

**Fallback to (A) if Wave 2B has tight V1 deadlines**: in-cluster nginx pods for ALL remotes is a faster path because the deploy pipeline already knows how to push images and roll Deployments. GCS+CDN can be a V1.5 migration (sub-plan MF-CDN-3).

Sub-plan MF-HOST-1 commits the strategy; MF-HOST-2 ships GCS+CDN provisioning.

### 2.4 GCS bucket layout (for Option B/C remotes)

```
gs://meesell-frontend-assets/
├── shell/                    # only if shell also moves to GCS (Option B) — not V1
└── remotes/
    ├── mfe-onboarding/
    │   ├── <sha1>/           # per-build directory; content-hash filenames within
    │   │   ├── remoteEntry.js
    │   │   ├── main.<hash>.js
    │   │   ├── chunks/
    │   │   └── manifest.json
    │   ├── <sha2>/
    │   └── current -> <sha2>   # symlink-equivalent (a marker file pointing to the active dir)
    ├── mfe-dashboard/
    │   └── ...
    └── ...
```

Each build pushes to a SHA-keyed directory; an atomic "promote" step rewrites the `current` marker, which the shell's manifest fetch resolves. Lets us roll back to any prior SHA by changing the marker file (no re-upload).

Bucket settings:
- `--uniform-bucket-level-access`
- Public read on the `remotes/` prefix (CORS allowed for `https://dev.mesell.xyz`, `https://www.mesell.xyz`)
- Versioning enabled (rollback safety net)
- Lifecycle: delete SHA directories older than 30 days (except those tagged `:prod`)
- Cache headers set on upload: `Cache-Control: public, max-age=31536000, immutable` for content-hashed files; `Cache-Control: public, max-age=60, must-revalidate` for `remoteEntry.js` (see §3.4)

### 2.5 Cloud CDN config

Single backend bucket attached to a global external HTTPS load balancer. Path-based routing:

```
remotes.mesell.xyz/<remote>/*  ->  gs://meesell-frontend-assets/remotes/<remote>/<current-sha>/*
```

Or, more cleanly using URL rewrites: `remotes.mesell.xyz/mfe-catalog/remoteEntry.js` → bucket object `remotes/mfe-catalog/<current-sha>/remoteEntry.js`. The `current-sha` is fetched once at load balancer config time; the rewrite is implemented either with a small Cloud Run "manifest resolver" sitting in front of CDN, or by serving the manifest from the bucket and letting the shell resolve URLs itself.

**Simplification for V1: skip the rewrite layer.** Shell fetches `remotes.mesell.xyz/manifest.json` (which carries `{"mfe-catalog": "https://remotes.mesell.xyz/mfe-catalog/<sha>/remoteEntry.js"}`) and `loadRemoteModule()` uses the absolute URL directly. The CDN serves bucket objects with no rewriting — just the cache layer.

Sub-plan MF-CDN-1 covers CDN provisioning. MF-CDN-2 covers the manifest server.

---

## 3. Routing Strategy

### 3.1 Manifest-driven remote discovery

The shell needs to know where each remote lives at runtime. Hard-coding URLs into the shell defeats independent deployability. Recommended pattern: a `remotes.manifest.json` fetched at shell bootstrap.

```json
// /assets/remotes.manifest.json (served by shell pod, or by GCS+CDN)
{
  "mfe-onboarding": {
    "url":     "https://remotes.mesell.xyz/mfe-onboarding/a3f7c92/remoteEntry.js",
    "version": "a3f7c92",
    "exposes": ["./Routes"]
  },
  "mfe-catalog": {
    "url":     "https://remotes.mesell.xyz/mfe-catalog/b8d1e44/remoteEntry.js",
    "version": "b8d1e44",
    "exposes": ["./Routes"]
  },
  ...
}
```

The shell's `app.config.ts` uses `@angular-architects/native-federation` (or `module-federation`) `loadManifest()` at app bootstrap before `bootstrapApplication`.

### 3.2 Where the manifest lives

| Option | Pros | Cons |
|---|---|---|
| (a) Inside the shell image | Simplest; ships with the build | Shell rebuild required to promote a remote → defeats independence |
| **(b) Served from the shell's nginx as a mounted ConfigMap** (recommended for V1) | Independent of shell image; updated via `kubectl patch configmap`; remote promotion = ConfigMap update + shell pod restart (or volume reload) | Requires shell pod to reread the file (use `nginx -s reload` via a sidecar / use Reloader operator) |
| (c) Served from a separate `manifest-server` Deployment | Fully independent | New service to operate; another deploy unit |
| (d) Served from GCS | Matches Option B/C from §2 | Adds a network hop; clients hit GCS before shell can render |

**Recommendation: (b) for V1**, with a [stretch.io/reloader](https://github.com/stakater/Reloader) operator watching the `remotes-manifest` ConfigMap and triggering a shell rollout when it changes. The shell image stays static across remote promotions.

When a remote ships:
1. CI builds the remote, uploads to GCS, tags `:current = <sha>`
2. CI patches `ConfigMap/remotes-manifest`: `data.<remote-name> = {"url": "...", "version": "<sha>"}`
3. Reloader observes the ConfigMap change, triggers `kubectl rollout restart deployment/mfe-shell`
4. New shell pods serve the new manifest; clients fetching `index.html` see the new manifest on next page load

### 3.3 Environment-specific manifest URLs

Per-environment, the manifest carries different URLs:

| Env | Shell URL | Manifest base for remotes |
|---|---|---|
| Local dev (`ng serve`) | `http://localhost:4200` | `http://localhost:4201` ... `:4207` (one per remote, webpack-dev-server) |
| Dev (K3s) | `https://dev.mesell.xyz` | `https://remotes.mesell.xyz/...` (if GCS+CDN) OR `https://dev.mesell.xyz/remotes/<name>/*` (if in-cluster) |
| Staging | `https://staging.mesell.xyz` | `https://remotes-staging.mesell.xyz/...` (separate CDN backend bucket for staging) |
| Prod | `https://www.mesell.xyz` | `https://remotes.mesell.xyz/...` (production CDN) |

The shell does NOT hard-code these — they live in the manifest fetched at startup. Per-environment manifests are templated by the deploy pipeline (envsubst into the ConfigMap).

### 3.4 Cache strategy for remoteEntry.js

This is the linchpin file — it's what the shell loads to discover what the remote exposes. Caching trade-off:

| Caching of remoteEntry.js | Behavior | Trade-off |
|---|---|---|
| `Cache-Control: public, max-age=31536000, immutable` | Once cached, never re-fetched | Promoting a new remote SHA in the manifest doesn't change anything unless the URL itself changes |
| `Cache-Control: public, max-age=60, must-revalidate` | Re-checked every minute | Tiny tail-latency cost; remote promotion takes effect within 60s globally |
| `Cache-Control: no-cache` | Always re-validated | Higher latency on each load; defeats CDN purpose |

**Recommendation: short-cache `remoteEntry.js` (60s, must-revalidate)** + immutable cache for content-hashed chunks. The remote's URL includes the SHA (`mfe-catalog/a3f7c92/remoteEntry.js`), so promoting a new SHA produces a new URL — the manifest update is what drives the cut-over. With this pattern, the 60s short-cache is a safety net; the URL change is the primary mechanism.

### 3.5 Ingress rules for frontend routing

```yaml
# Ingress on dev.mesell.xyz — V1 Option C (hybrid)
spec:
  ingressClassName: traefik
  tls:
    - hosts: [dev.mesell.xyz]
      secretName: dev-frontend-tls
  rules:
    - host: dev.mesell.xyz
      http:
        paths:
          - path: /assets/remotes.manifest.json   # manifest from ConfigMap
            backend: { service: { name: mfe-shell, port: { number: 80 } } }
          - path: /                               # everything else -> shell (SPA fallback)
            backend: { service: { name: mfe-shell, port: { number: 80 } } }
```

The remotes live on `remotes.mesell.xyz` (separate hostname, separate cert). New DNS A records:
```
remotes.mesell.xyz          A    <CDN forwarding rule IP>     # asset CDN
remotes-staging.mesell.xyz  A    <CDN forwarding rule IP>
```

If staying in-cluster (Option A only): remotes live at `dev.mesell.xyz/mfe-catalog/*` etc. — path-prefix Ingress rules. Simpler routing, but loses the CDN edge benefit.

---

## 4. Build Pipeline Changes

### 4.1 Current

`cloudbuild.yaml` builds one Angular app (`frontend/Dockerfile`) → one image `meesell-prod-images/frontend:<sha>` → one nginx pod.

### 4.2 Target — N+1 independent builds (shell + N remotes)

Repo layout (frontend coordinator's call; infra plans against this shape):

```
frontend/
├── projects/
│   ├── shell/
│   │   ├── src/
│   │   ├── webpack.config.js          # ModuleFederationPlugin: name=shell, remotes={} (resolved at runtime)
│   │   ├── Dockerfile                 # multi-stage: node build -> nginx
│   │   └── nginx.conf
│   ├── mfe-onboarding/
│   │   ├── src/
│   │   ├── webpack.config.js          # ModuleFederationPlugin: name=mfe-onboarding, exposes={ './Routes': ... }
│   │   └── (no Dockerfile — GCS-deployed)
│   ├── mfe-dashboard/
│   │   ...
│   └── mfe-billing/
├── angular.json                       # multi-project Angular workspace
├── package.json                       # single pnpm/npm workspace (shared deps)
└── cloudbuild.frontend.yaml           # 8-target build orchestration
```

### 4.3 Path-filter triggers

GitHub Actions matrix with `dorny/paths-filter`:

```yaml
detect-frontend-changes:
  outputs:
    units: ${{ steps.filter.outputs.changes }}
  steps:
    - uses: dorny/paths-filter@v3
      id: filter
      with:
        filters: |
          shell:           'frontend/projects/shell/**'
          mfe-onboarding:  'frontend/projects/mfe-onboarding/**'
          mfe-dashboard:   'frontend/projects/mfe-dashboard/**'
          mfe-catalog:     'frontend/projects/mfe-catalog/**'
          mfe-quality:     'frontend/projects/mfe-quality/**'
          mfe-pricing:     'frontend/projects/mfe-pricing/**'
          mfe-export:      'frontend/projects/mfe-export/**'
          mfe-billing:     'frontend/projects/mfe-billing/**'
          shared:          'frontend/projects/shared/**'   # shared lib

build-shell:
  needs: detect-frontend-changes
  if: contains(needs.detect-frontend-changes.outputs.units, 'shell') || contains(needs.detect-frontend-changes.outputs.units, 'shared')
  steps:
    - run: gcloud builds submit --config=cloudbuild.shell.yaml --substitutions=_TAG=${{ github.sha }}

build-remote:
  needs: detect-frontend-changes
  strategy:
    matrix:
      remote: ${{ fromJSON(needs.detect-frontend-changes.outputs.units) }}
      exclude:
        - remote: shell
        - remote: shared
  steps:
    - run: gcloud builds submit --config=cloudbuild.remote.yaml --substitutions=_REMOTE=${{ matrix.remote }},_TAG=${{ github.sha }}
```

If `shared/**` changes, every unit rebuilds. Otherwise only the changed units rebuild.

### 4.4 cloudbuild — two files

**`cloudbuild.shell.yaml`** — builds the shell as an image (K3s deploy):

```yaml
substitutions:
  _TAG: ""
  _PROJECT_ID: project-1f5cbf72-2820-4cdb-949
  _REGION: asia-south1
  _REPO: meesell-prod-images

steps:
  - id: clone
    name: gcr.io/cloud-builders/git
    args: ['clone', '--depth=1', '--branch=main', 'https://github.com/Mugunthan93/mesell.git', '/workspace/src']

  - id: build
    name: gcr.io/cloud-builders/docker
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/mfe-shell:${_TAG}',
                    '-t', '${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/mfe-shell:latest',
                    '-f', '/workspace/src/frontend/projects/shell/Dockerfile',
                    '/workspace/src/frontend']

  - id: push
    name: gcr.io/cloud-builders/docker
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/mfe-shell']

images:
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/mfe-shell:${_TAG}
  - ${_REGION}-docker.pkg.dev/${_PROJECT_ID}/${_REPO}/mfe-shell:latest

timeout: 1200s
```

**`cloudbuild.remote.yaml`** — builds a remote as static assets (GCS deploy):

```yaml
substitutions:
  _REMOTE: ""   # set per matrix entry
  _TAG: ""
  _PROJECT_ID: project-1f5cbf72-2820-4cdb-949
  _BUCKET: meesell-frontend-assets

steps:
  - id: clone
    name: gcr.io/cloud-builders/git
    args: ['clone', '--depth=1', '--branch=main', 'https://github.com/Mugunthan93/mesell.git', '/workspace/src']

  - id: build
    name: node:20-alpine
    entrypoint: bash
    args:
      - -c
      - |
        cd /workspace/src/frontend
        corepack enable && pnpm install --frozen-lockfile
        pnpm exec ng build ${_REMOTE} --configuration=production --output-path=dist/${_REMOTE}/${_TAG}

  - id: upload
    name: gcr.io/cloud-builders/gsutil
    args:
      - -m
      - -h
      - 'Cache-Control:public,max-age=31536000,immutable'
      - rsync
      - -r
      - -x
      - 'remoteEntry\.js$'
      - /workspace/src/frontend/dist/${_REMOTE}/${_TAG}
      - gs://${_BUCKET}/remotes/${_REMOTE}/${_TAG}

  - id: upload-entry
    name: gcr.io/cloud-builders/gsutil
    args:
      - -h
      - 'Cache-Control:public,max-age=60,must-revalidate'
      - cp
      - /workspace/src/frontend/dist/${_REMOTE}/${_TAG}/remoteEntry.js
      - gs://${_BUCKET}/remotes/${_REMOTE}/${_TAG}/remoteEntry.js

timeout: 1200s
```

Two Cache-Control headers — immutable for everything except the entry, 60s for the entry — implemented as two `gsutil` invocations.

### 4.5 Shared node_modules cache

`pnpm install --frozen-lockfile` runs against the entire workspace. Cloud Build can cache `node_modules/` via Cloud Build caching feature or by using `kaniko` with a separate cache layer.

V1 pragmatic path: each Cloud Build run does a fresh `pnpm install`. ~60s overhead per build. Acceptable. Optimization (sub-plan MF-CI-2) ships when build minutes become a cost concern.

For the matrix-of-remotes case, the parallel builds each do their own `pnpm install` (one VM per matrix entry). The pnpm content-addressable store is per-VM — no sharing across matrix entries unless we mount a shared volume (deferred).

### 4.6 Deploy job — two modes

**Shell deploy (image, K3s):**
- Same as backend `kubectl set image` pattern.
- Smoke check: `curl https://dev.mesell.xyz/` returns 200 + HTML containing `<app-root>`.

**Remote deploy (GCS):**
- After Cloud Build pushes to `gs://meesell-frontend-assets/remotes/<remote>/<sha>/`, the deploy job:
  1. Updates a "current" marker: `gsutil cp - gs://.../remotes/<remote>/current.json <<< '{"version":"<sha>"}'`
  2. Patches the shell's `remotes-manifest` ConfigMap with the new URL via IAP-tunneled `kubectl patch`
  3. Reloader triggers a `kubectl rollout restart deployment/mfe-shell` (or shell reads the manifest fresh on next request)
  4. Smoke check: `curl https://remotes.mesell.xyz/<remote>/<sha>/remoteEntry.js` returns 200

**Rollback:**
- Shell: `kubectl rollout undo deployment/mfe-shell`
- Remote: revert the `current.json` marker + revert the ConfigMap patch + restart shell. All within 30s.

### 4.7 Artifact Registry changes

| Today | Target |
|---|---|
| `meesell-prod-images/frontend` | `meesell-prod-images/mfe-shell` (single stream — only the shell ships as an image) |

Remotes don't go to AR — they go to GCS. AR cleanup policy unchanged.

---

## 5. Dev + Staging Environment Design

### 5.1 Local dev — all remotes on different ports

Each remote ships a `webpack.config.js` with `devServer.port` set:

```
http://localhost:4200    shell                    (ng serve --project=shell --port=4200)
http://localhost:4201    mfe-onboarding           (ng serve --project=mfe-onboarding --port=4201)
http://localhost:4202    mfe-dashboard
http://localhost:4203    mfe-catalog
http://localhost:4204    mfe-quality
http://localhost:4205    mfe-pricing
http://localhost:4206    mfe-export
http://localhost:4207    mfe-billing
```

The shell's local manifest (`projects/shell/src/assets/remotes.manifest.local.json`) points at `localhost:42xx`. Founder runs `pnpm run dev` which spawns 8 `ng serve` processes via `concurrently`.

CORS: each remote dev server allows `http://localhost:4200` via Angular's `--proxy-config` or `webpack-dev-server`'s `headers` option.

### 5.2 Staging URLs

| Env | Shell | Remotes (CDN) |
|---|---|---|
| Local | `localhost:4200` | `localhost:42xx` (one per remote) |
| Dev | `dev.mesell.xyz` | `remotes.mesell.xyz` (shared CDN; `/mfe-<name>/...` paths) |
| Staging | `staging.mesell.xyz` | `remotes-staging.mesell.xyz` (separate CDN backend bucket) |
| Testing | `testing.mesell.xyz` | `remotes.mesell.xyz` (re-uses dev's remotes — QA tests against latest dev SHA) |
| Prod | `www.mesell.xyz` | `remotes.mesell.xyz` (production CDN; tagged SHAs promoted) |

**[OPEN DECISION — MF-ENV-1]:** separate buckets per env vs shared bucket with env-prefixed paths.

| Option | Pros | Cons |
|---|---|---|
| (a) `gs://meesell-frontend-assets-dev`, `-staging`, `-prod` (separate buckets) | Clean ACL boundary; per-env lifecycle policies | 3 buckets to manage; 3 CDN backend configs |
| (b) `gs://meesell-frontend-assets/{dev,staging,prod}/remotes/...` (shared bucket, prefix per env) | One bucket; one CDN backend with path-rewrite | Single ACL surface — a misconfigured policy affects all envs |

**Recommendation: (a) separate buckets** because blast-radius isolation between envs is worth the small mgmt cost. Aligns with the K8s namespace-per-env pattern.

### 5.3 Environment config injection — runtime vs build time

| Strategy | Trade-off |
|---|---|
| Build time — Angular `fileReplacements` per env | Requires N builds (dev, staging, prod) per remote. Defeats "build once, deploy many." |
| Runtime — fetch config on shell bootstrap | One build per remote; env config arrives from the manifest or a separate `env.json`. Recommended. |

The shell fetches `/assets/env.json` (served from a per-env ConfigMap mount) at bootstrap. This contains:

```json
{
  "API_BASE_URL": "https://api.mesell.xyz",
  "REMOTES_BASE_URL": "https://remotes.mesell.xyz",
  "ENV": "dev",
  "SENTRY_DSN": "<dev-dsn>"
}
```

Remotes don't fetch their own env — they accept config from the shell via `provide()` injection at lazy-load time. Sub-plan MF-CFG-1 covers the env.json + injection pattern.

### 5.4 Compatibility with current ingress (preservation guarantee)

Existing 5 ingress hosts (`dev.mesell.xyz`, `testing.mesell.xyz`, `staging.mesell.xyz`, plus prod-bound `www.mesell.xyz`) all keep their TLS certs and routes. The shift is: the backend service behind those Ingresses changes from `frontend` (single) to `mfe-shell` (the host). No new TLS cert renewals required because the hostnames are unchanged.

New hostname `remotes.mesell.xyz` is the only DNS/cert addition. Cert issuance via cert-manager + Let's Encrypt HTTP-01 — same pattern as current 5 hosts. Sub-plan MF-CDN-1 covers the DNS + cert provisioning.

---

## 6. CDN / Cache Strategy

### 6.1 Per-remote versioning by content hash

Webpack's `output.filename: '[name].[contenthash].js'` produces filenames like `main.a3f7c92b.js`. Every changed file gets a new hash. Cache strategy:

| File type | Cache-Control | Why |
|---|---|---|
| `*.[hash].js`, `*.[hash].css`, `*.[hash].png` | `public, max-age=31536000, immutable` | Filename changes when content changes — cache forever |
| `remoteEntry.js` (no hash in name by design) | `public, max-age=60, must-revalidate` | Bootstrap file the shell discovers each remote by; must reflect new SHA quickly |
| `index.html` | `public, max-age=0, must-revalidate` | Tiny; lets new builds take effect immediately |
| `assets/i18n/*.json`, `assets/icons/*.svg` | `public, max-age=86400` | Non-content-hashed assets refresh daily |

### 6.2 Per-remote cache invalidation

When a remote's SHA promotes:

1. New SHA's files are already at a different path (`/remotes/mfe-catalog/<new-sha>/...`). No invalidation needed for those.
2. Only `remoteEntry.js` at the manifest-pointed URL could be cached. Its 60s short-cache means within 60s, clients fetch the new version.
3. `remotes.manifest.json` (served by shell pod) is updated when the ConfigMap is patched. Reloader restarts shell; cache headers on the manifest itself are `no-cache` (always re-validated).

**Result:** new remote takes effect for new clients within 60-120s. Existing clients (already-running shell instances in browsers) continue using their cached version until they reload the page.

For force-invalidation (security fix, rollback), Cloud CDN has a per-pattern invalidation API:
```
gcloud compute url-maps invalidate-cdn-cache mfe-cdn-url-map --path="/remotes/mfe-catalog/<sha>/*"
```
But the URL-versioned scheme makes this almost never needed.

### 6.3 CORS headers

Remotes serve assets from `remotes.mesell.xyz`; shell loads from `dev.mesell.xyz`. Cross-origin. GCS bucket CORS config:

```json
[
  {
    "origin": [
      "https://dev.mesell.xyz",
      "https://testing.mesell.xyz",
      "https://staging.mesell.xyz",
      "https://www.mesell.xyz",
      "http://localhost:4200"
    ],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type", "Cache-Control"],
    "maxAgeSeconds": 3600
  }
]
```

Set via `gsutil cors set cors.json gs://meesell-frontend-assets-<env>`. Sub-plan MF-CDN-3 covers CORS provisioning (Terraform `google_storage_bucket.cors` block).

### 6.4 Subresource Integrity (SRI) — deferred to V1.5

SRI hashes on `remoteEntry.js` would protect against a CDN-side tamper. Angular's `subresourceIntegrity: true` build option emits hashes; the shell would have to include them in the manifest. Complexity isn't worth it for V1 (we trust GCP). Track as MF-SEC-1.

### 6.5 Edge geo / Cloud CDN region

Cloud CDN has POPs across India (Mumbai, Chennai, Delhi). Default global CDN config picks the nearest POP per client. No region pin needed.

---

## 7. Sub-Plans

Complexity: S (≤ 1 day), M (2-3 days), L (≥ 4 days). Dependencies refer to other sub-plan IDs.

| ID | Name | Description | Complexity | Dependency | Effort |
|---|---|---|---|---|---|
| MF-HOST-1 | Commit hosting strategy (Option C — hybrid) | Founder decision; document in INFRA_ARCH; close MF-ENV-1 sub-question | S | — | 1d |
| MF-HOST-2 | Provision GCS bucket for frontend assets | `module.frontend_assets_bucket` Terraform (dev + staging + prod buckets); IAM grants to CI SA | M | MF-HOST-1 | 2d |
| MF-CDN-1 | Provision Cloud CDN + LB + DNS for `remotes.mesell.xyz` | New TF `module.frontend_cdn`: backend bucket, URL map, HTTPS LB, managed cert; Namecheap A record | L | MF-HOST-2 | 4d |
| MF-CDN-2 | CORS + cache-control headers on bucket | Terraform `google_storage_bucket.cors` + lifecycle rules; documented header policy | S | MF-CDN-1 | 1d |
| MF-CDN-3 | Per-env CDN URL maps (dev/staging/prod) | 3 URL maps, 3 hostnames, 3 certs | M | MF-CDN-1 | 2d |
| MF-K8S-1 | Per-MFE K8s manifest skeleton (shell only — in-cluster) | Author `k8s/frontend/mfe-shell.yaml` (Deployment + Service); deprecate `k8s/frontend.yaml` | S | — | 1d |
| MF-K8S-2 | `remotes-manifest` ConfigMap + Reloader | Add Reloader operator Helm release; create initial ConfigMap with manifest stub | M | MF-K8S-1 | 2d |
| MF-K8S-3 | Per-env `env.json` ConfigMap | Mount in shell pod; templated by CI per env | S | MF-K8S-1 | 1d |
| MF-CI-1 | Path-filter detect-changes job + matrix | `dorny/paths-filter` job; matrix dispatch to shell-build and remote-build | M | — | 2d |
| MF-CI-2 | `cloudbuild.shell.yaml` (image-based) | Shell-only image build; AR push; image-tag injection at deploy | S | MF-CI-1 | 1d |
| MF-CI-3 | `cloudbuild.remote.yaml` (GCS-based) | Per-remote build → `gsutil rsync` → tag `current.json`; parameterized by `_REMOTE` | M | MF-CI-1, MF-HOST-2 | 3d |
| MF-CI-4 | Deploy job: shell rollout + remote ConfigMap patch | Replace single `kubectl set image` with shell-rollout + ConfigMap-patch flow; smoke check both | M | MF-K8S-2, MF-CI-2, MF-CI-3 | 2d |
| MF-CI-5 | Cache (pnpm store) between matrix entries | Cloud Build cache config; shared pnpm-store mount | M | MF-CI-3 | 2d |
| MF-CFG-1 | `env.json` injection from shell → remotes | Document the contract; shell `provide()` injection at `loadRemoteModule` | S | MF-K8S-3 | 1d |
| MF-DNS-1 | New A records: `remotes.mesell.xyz`, `remotes-staging.mesell.xyz` | Namecheap Playwright helper add 2 A records pointing at CDN forwarding rule | S | MF-CDN-1 | 1d |
| MF-OBS-1 | Per-remote synthetic monitoring | Cloud Monitoring uptime checks against `remotes.mesell.xyz/<remote>/current/remoteEntry.js` | M | MF-CDN-3 | 2d |
| MF-SEC-1 | SRI hashes on remoteEntry.js (deferred) | Angular subresourceIntegrity:true; manifest carries hash; shell verifies | M | MF-CFG-1 | 2d |
| MF-DOC-1 | Update INFRASTRUCTURE_ARCHITECTURE.md SSOT | Add §7.x Module Federation topology; refresh diagram | S | MF-CI-4 | 1d |
| MF-DOC-2 | Update DEVOPS_ARCHITECTURE.md | Replace §9 frontend build/deploy with split build + GCS deploy | S | MF-CI-4 | 1d |

**Suggested execution order:**

1. Decision + provisioning: MF-HOST-1, MF-HOST-2, MF-CDN-1, MF-CDN-2, MF-DNS-1
2. K8s shell scaffolding: MF-K8S-1, MF-K8S-2, MF-K8S-3
3. CI pipeline: MF-CI-1, MF-CI-2, MF-CI-3, MF-CI-4
4. Multi-env hardening: MF-CDN-3
5. Cut over dev → staging using new pipeline; observe a week
6. Optimisation: MF-CI-5, MF-OBS-1
7. Hardening: MF-SEC-1
8. Docs (MF-DOC-1, MF-DOC-2) — finalized at end

**Total estimated effort:** ~30 engineer-days for infra alone (excluding frontend domain refactor — splitting Angular projects, configuring `ModuleFederationPlugin` per remote, writing the manifest loader).

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-MF-1 | Singleton version mismatch — shell loads `@angular/core@18.1`, remote built against `@angular/core@18.2`; runtime breaks with cryptic injector errors | High | Critical | Strict `singleton: true, requiredVersion: '18.x'` on all shared deps in every webpack config. CI gate: `pnpm ls @angular/core` reports a single version across all projects. |
| R-MF-2 | A remote's `remoteEntry.js` URL goes stale in a long-lived browser session; shell can't load it | Medium | High | 60s short-cache on `remoteEntry.js`. Sub-plan MF-CFG-1: shell catches `loadRemoteModule` failure and triggers a full page reload, which re-fetches the manifest. |
| R-MF-3 | Cloud CDN cache miss storm on first prod cutover (cold cache) | Medium | Medium | Pre-warm by hitting each remote's `remoteEntry.js` from the CI runner after deploy. Documented in MF-CI-4 deploy script. |
| R-MF-4 | CORS misconfiguration on bucket blocks all remote loads — visible only after deploy | Medium | Critical | MF-CDN-2 includes a CI gate: a deploy-time `curl -H "Origin: https://dev.mesell.xyz"` against a remote URL must return `Access-Control-Allow-Origin`. Pre-flight on every deploy. |
| R-MF-5 | GCS bucket public-access misconfiguration leaks internal assets | Low | High | Public read scoped to `/remotes/` prefix only (via IAM condition). `gsutil iam ch publicRead:objectViewer gs://bucket/remotes/*` syntax via TF `google_storage_bucket_iam_member` with condition. CI gate: `gsutil iam get gs://bucket` snapshots the IAM policy and asserts. |
| R-MF-6 | Manifest ConfigMap patch is non-atomic — two simultaneous deploys race | Low | Medium | `kubectl patch --type=strategic` is server-side atomic. Sequential deploys in the matrix per GitHub Actions semantics. Worst case: last writer wins; smoke check catches mismatch. |
| R-MF-7 | Reloader's shell rollout takes 30s; new clients see stale manifest in that window | Medium | Low | The manifest URL is `/assets/remotes.manifest.json` — served by the shell. During rollout, the old pod serves the old manifest, new pod serves the new. Clients hitting old pods get old manifest → load old remotes → no breakage. |
| R-MF-8 | `pnpm install` runs 8× in matrix (8 separate Cloud Build VMs) — minutes blow up | Medium | Medium | MF-CI-5: shared pnpm-store cache. Until shipped, monitor Cloud Build minutes vs free-tier cap (120 build-min/day). |
| R-MF-9 | Path-filter triggers miss a shared-lib change because the lib is referenced indirectly | Medium | High | The `shared` filter triggers rebuild of ALL units. Conservative; minor over-build is preferable to silent miss. |
| R-MF-10 | Mid-deploy: shell updated to point at new remote SHA, but remote files not yet uploaded to GCS | Medium | High | MF-CI-4 deploy order: upload to GCS first, then patch the manifest. Validation gate: `gsutil ls gs://bucket/remotes/<remote>/<sha>/remoteEntry.js` returns 0 before the patch. |
| R-MF-11 | A remote's bundle size grows past 5MB; affects first-load time | Medium | Medium | Cloud CDN edge + Brotli compression help, but the real fix is in Angular code (lazy load within the remote). Out of infra scope — flag for frontend coordinator. |
| R-MF-12 | Federated singleton (RxJS) conflicts across remotes built on different RxJS minors | Medium | High | Same singleton pattern as R-MF-1. RxJS pinned in workspace `package.json`; lockfile enforced via `pnpm install --frozen-lockfile`. |
| R-MF-13 | Auth context not propagated to remotes — each remote calls auth differently | High | High | `env.json` injection provides shared `AuthService` token; documented contract in MF-CFG-1. Frontend coordinator owns the runtime — infra ensures the manifest carries the right service reference (`provide(AUTH_SERVICE, useExisting: shell.AuthService)` pattern). |
| R-MF-14 | Cert renewal on `remotes.mesell.xyz` fails because the CDN's managed cert provisioning is different from cert-manager | Medium | High | MF-CDN-1: use GCP-managed SSL cert (not cert-manager). GCP auto-renews. Document the difference; cert-manager is K3s-only. |
| R-MF-15 | Loss of single-image rollback simplicity: a bad cross-cutting change (shell + 3 remotes) needs 4 rollbacks instead of 1 | Medium | Medium | Document the rollback runbook: roll back shell first (reverts the manifest to the prior version), which transparently reverts the remote references. Per-remote `current.json` is a secondary rollback only. |
| R-MF-16 | DEV vs PROD config drift — local dev manifest hand-maintained gets out of sync | Medium | Low | MF-CFG-1: shell's local manifest generated by a `pnpm run gen-manifest` script that reads the current `angular.json` projects. CI gate: `git diff` on the generated manifest must be clean. |

---

## 9. What this plan deliberately does NOT cover

- Splitting the existing Angular app into shell + N remotes (`ModuleFederationPlugin` configs, `loadRemoteModule` wiring, `provide()` boundary contracts) — owned by `meesell-frontend-coordinator`
- Mobile app (Ionic + Capacitor) wrap of the shell — Phase 2, separate plan
- Service worker / PWA caching strategy for offline — V1.5
- A/B testing or canary remote rollout — V1.5
- Multi-region asset replication beyond Cloud CDN's POPs — out of V1
- Per-remote feature flags — code-side concern
- Type-safe contracts between shell and remotes (TypeScript ambient module declarations for federated modules) — frontend coordinator owns

---

**End of plan.**

---

## 10. Revision History

| Date | Status | Change | By |
|---|---|---|---|
| 2026-06-10 | DRAFT | Initial draft authored. | meesell-infra-builder |
| 2026-06-10 | APPROVED | Ratified by founder via master-session ruling. Hosting model LOCKED = Option C (shell in-cluster + 6 remotes GCS/CDN static at `remotes.mesell.xyz`); Option A fallback CLOSED. Gate-4 conditions C-RES-1, C-RES-2, C-ROUTE-1, C-CI-1, C-CSP-1, C-STAGING-1 adopted as binding Sub-plan 7 requirements. CSP authored greenfield (shell nginx.conf or CSP-only Traefik Middleware) — must NOT disturb CORS/refresh-cookie behavior. See `docs/plans/infra/GATE4_CONFIRMATION.md`. | meesell-infra-builder (S5 — master dispatch) |
