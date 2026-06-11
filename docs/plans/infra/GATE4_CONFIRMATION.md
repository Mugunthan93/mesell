# MF MASTER_PLAN §9 Gate 4 — Infra Hosting Confirmation

**Author:** `meesell-infra-builder` · **Session:** `mesell-gate4-confirmation-infra-session-1` · **Date:** 2026-06-10
**Gate reference:** `docs/plans/module_federation/MASTER_PLAN.md` §9 item 4 — *"`meesell-infra-builder` confirms K3s + Traefik can host N+1 services and CSP is editable."*
**Scope:** technical confirmation ONLY. This document does NOT ratify the DRAFT infra plan (`docs/plans/infra/module_federation_infra_plan.md`) — the founder's S5 window owns ratification. This is evidence + a verdict.

**Topology under test:** 1 shell + 6 remotes (`mfe-auth`, `mfe-onboarding`, `mfe-dashboard`, `mfe-catalog`, `mfe-pricing`, `mfe-export`) per MASTER_PLAN §2.2. (The DRAFT infra plan §0 plans against an *illustrative* 7-remote set; the authoritative remote count is the MASTER_PLAN's 6. The math below uses 6.)

**Cluster verification posture:** the kubeconfig (`~/.kube/meesell-dev.yaml`) WAS reachable from this machine. All cluster facts below are from READ-ONLY `kubectl get/describe/top` against `meesell-dev-master` (K3s `v1.35.5+k3s1`). Zero mutations. Doc facts cross-checked against `INFRASTRUCTURE_ARCHITECTURE.md` §5–§8 and `infra/terraform/modules/ingress/main.tf`.

---

## Answer 1 — Routing (Traefik can route shell + 6 remotes)

**CONFIRMED.** Traefik (self-managed in the `traefik` namespace; K3s bundled Traefik disabled per playbook §3.2/§8.1) already routes 5 production hosts today, all **host-based** (`Host` header + TLS SNI), each backed by its own per-host Ingress resource and **per-host** Let's Encrypt cert (`infra/terraform/modules/ingress/main.tf`: each host block has its own `tls { hosts; secret_name }` + `cert-manager.io/cluster-issuer: letsencrypt-prod`, HTTP-01 solver). There is **no wildcard cert** — TLS is one cert per host.

The DRAFT infra plan proposes **Option C (hybrid)**: shell stays on the existing host (`dev.mesell.xyz` → `mfe-shell:80`, a pure backend-service swap on the already-live Ingress, no cert change) and remotes are served from a NEW host `remotes.mesell.xyz` (GCS + Cloud CDN, GCP-managed cert — NOT cert-manager). The current per-host Ingress/cert pattern fully supports the shell swap with zero cert churn. The remote host is net-new and lives OUTSIDE Traefik/K3s (on a GCP HTTPS LB), so it does not consume a Traefik route at all.

If the fallback **Option A (all-in-cluster)** is taken instead, Traefik supports path-prefix routing (`dev.mesell.xyz/mfe-<name>/*`) — same origin, shared `dev-frontend-tls` cert, no new cert. Traefik path-prefix routing is a standard Ingress feature and the controller already runs. Either model is routable. **Condition C-ROUTE-1:** if Option C ships, `remotes.mesell.xyz` needs a new Namecheap A record + a GCP-managed SSL cert (NOT cert-manager — see Answer 4 / risk R-MF-14); cert-manager only covers K3s-fronted hosts.

## Answer 2 — Deployability (7 independently deployable units)

**CONFIRMED.** Shell ships exactly like the existing `api`/`frontend` workloads: a Deployment + ClusterIP Service in `dev` (manifest pattern proven by `k8s/frontend.yaml`). Independent rollout via `kubectl rollout` / image-tag injection (DEVOPS §10.3).

- **Image strategy / AR capacity:** the single Artifact Registry repo `meesell-prod-images` (asia-south1) already holds multiple image *streams* by name (`api`, `frontend`). Adding `mfe-shell` is just another stream in the same repo — **no AR capacity limit, no new repo, no new IAM** (VM SA already has `artifactregistry.reader`; CI SA has `artifactregistry.writer`). K3s containerd pulls via the GCE metadata-server token (`registries.yaml`, runbook 12.8) — no `imagePullSecrets` per Deployment.
- **6 remotes do NOT become 6 Nginx pods under the recommended Option C** — they are static bundles in GCS behind Cloud CDN, deployed by `gsutil rsync` + a manifest-ConfigMap patch. Zero in-cluster pods, zero AR streams for remotes. This is what makes Answer 3 pass.
- **CI build path per remote:** DRAFT §4.3 uses a `dorny/paths-filter` matrix — only changed units rebuild; a `shared/**` change rebuilds all. The existing `cloudbuild.yaml` `precheck-frontend` conditional (DEVOPS §9.2) is the migration anchor — it must be retired in favour of `cloudbuild.shell.yaml` (image) + `cloudbuild.remote.yaml` (GCS) per DRAFT §4.4. **Condition C-CI-1:** the current single-frontend conditional build must be replaced, not extended, when the multi-project Angular workspace lands (frontend-coordinator owns the workspace; infra owns the two new cloudbuild files + the matrix).

## Answer 3 — Resources (headroom math) — **this is the binding constraint**

**CONFIRMED ONLY FOR OPTION C (GCS/CDN remotes). NOT CONFIRMED for Option A (all-in-cluster) in `dev` today.**

Live `kubectl describe node meesell-dev-master` (read-only, this session):

| Metric | Allocatable | Requested now | Headroom |
|---|---|---|---|
| CPU | **2000m** | **1650m (82%)** | **~350m** |
| Memory | **~7.94Gi (8129624Ki)** | **3528Mi (44%)** | **~4.4Gi** |

Per-pod CPU requests summing to 1650m: api 2×200m, worker 2×250m, postgres 200m, valkey 100m, studio 100m, coredns 100m, metrics-server 100m, cert-manager 3×50m. The frontend Deployment (2× of `frontend.yaml`'s 50m/64Mi baseline) is **not yet deployed**. Actual usage is low (`kubectl top node`: 190m CPU / 3130Mi mem) — but the **scheduler gates on requests, not usage**, and only ~350m CPU is requestable.

- **Option A (all-in-cluster), DRAFT §1.3:** shell 2×(~100m) + 6 remotes ×(~50m) = ~500m new CPU requests against ~350m headroom → **the 6 remote pods + a 2-replica shell will NOT all schedule on the dev node.** They would sit `Pending` (Insufficient cpu). Memory is fine (~600Mi vs 4.4Gi free); **CPU is the wall.**
- **Option C (recommended), DRAFT §1.3 + §2.3:** remotes live in GCS+CDN → **0 in-cluster CPU**. Only the shell swaps in for the retiring `frontend` Deployment (net CPU delta ≈ shell − frontend ≈ ~0). **Fits dev comfortably.**

**Dev vs dev+staging:** all numbers above are `dev` only. `staging` currently runs an Ingress + cert only (no workload pods — INFRA_ARCH §6). If staging later mirrors dev's api/worker/postgres/valkey AND adds in-cluster remotes, it would hit the same single-node 2-vCPU wall. Conditions C-RES-1 and C-RES-2 below.

**Conditions:**
- **C-RES-1:** Option A (in-cluster remotes) is INFEASIBLE on the current `e2-standard-2` (2 vCPU) dev node — would require a VM machine-type bump (founder approval, >₹500/mo) OR explicit per-remote CPU requests of ≤25m with no shell replica increase (fragile). Recommend NOT taking Option A on the current node.
- **C-RES-2:** Option C is the resource-safe path: remotes off-cluster (GCS/CDN), shell in-cluster. This is what the headroom supports without a VM change.

## Answer 4 — CSP editability (shell can load remote JS)

**CONFIRMED — and it is a greenfield surface (nothing to un-break).** A full read-only sweep (`grep -rln "Content-Security-Policy" frontend/ k8s/ infra/`) finds **NO CSP header set anywhere in owned surfaces today** — the only matches are inside `frontend/node_modules`. There is **no `frontend/Dockerfile`, no `frontend/nginx.conf`, and no Traefik `Middleware` CRD** (the sole `middleware`/`headers` hit in `k8s/` is the comment block in the superseded `k8s/ingress.yaml`). So CSP isn't "editable" in the sense of changing an existing value — it does **not exist yet**, which means we author it from scratch with full control.

**Where CSP WILL be set (two viable layers, per-environment editable):**
1. **Nginx conf in the shell image (recommended).** Wave 2B's frontend Dockerfile (DEVOPS §9.3 recommends `nginx:alpine` runtime) will ship a `nginx.conf`; CSP goes there as `add_header Content-Security-Policy "...";`. Per-environment editability comes from templating that header value at build/deploy time (the same envsubst path the DRAFT uses for the env.json/manifest). Angular 21 also ships `auto-csp` build tooling (`@angular/build` `auto-csp.js`) which can emit a hash/nonce-based CSP at build — an option for the shell.
2. **Traefik `Middleware` CRD (`headers.customResponseHeaders`)** attached to the shell Ingress — sets CSP at the edge, per-host, edited via `kubectl`/Terraform without rebuilding the image. CRITICAL CONSTRAINT (per `k8s/ingress.yaml` comment block + BACKEND_ARCHITECTURE §4.G): a Traefik headers middleware MUST NOT strip/override the app's CORS response headers or the `Set-Cookie` refresh-token cookie. A CSP-only middleware that adds exactly one response header is safe; a broad headers middleware is not.

**Directives federation needs** (shell loading remote JS from a different origin, Option C):
- `script-src 'self' https://remotes.mesell.xyz` (load `remoteEntry.js` + chunks). Angular may need `'wasm-unsafe-eval'` or a nonce; frontend-coordinator confirms exact token set.
- `connect-src 'self' https://api.mesell.xyz https://remotes.mesell.xyz` (XHR/fetch for federation manifest + remote fetches + API).
- `style-src`, `font-src`, `img-src` extended to `https://remotes.mesell.xyz` as needed.
- For Option A (same-origin path-prefix), `'self'` already covers script/connect — CSP is trivial.

**Condition C-CSP-1:** the exact CSP directive string (and whether it lives in nginx.conf vs a Traefik Middleware) is a joint infra ↔ frontend deliverable in Sub-plan 7 — infra owns the header mechanism + per-env templating; frontend-coordinator owns the precise allowlist of origins/tokens the federation runtime demands. CSP must be authored and smoke-tested on `dev` BEFORE the first remote is wired, or the shell will silently fail to load remotes (MASTER_PLAN §7 P2 watch-item).

---

## VERDICT: **CONFIRMED-WITH-CONDITIONS**

K3s + Traefik **can** host the shell + 6 remotes, and CSP **is** authorable/editable. The confirmation is conditional because the live `dev` node has only ~350m CPU headroom, which forces the off-cluster (GCS/CDN) remote-hosting model and rules out the all-in-cluster fallback on the current VM.

### Conditions (these become Sub-plan 7 / MF infra-plan requirements)
- **C-RES-1** — Option A (in-cluster Nginx per remote) is INFEASIBLE on the current `e2-standard-2` dev node (~350m CPU free vs ~500m needed). Do not take Option A without a founder-approved VM machine-type bump (>₹500/mo cost gate).
- **C-RES-2** — Ship **Option C (hybrid)**: shell in K3s (swaps the retiring `frontend` Deployment, ~0 net CPU), 6 remotes in GCS + Cloud CDN (0 in-cluster CPU). This is the only resource-safe path on current hardware.
- **C-ROUTE-1** — New host `remotes.mesell.xyz` needs a Namecheap A record + a **GCP-managed** SSL cert (NOT cert-manager; cert-manager only covers K3s-fronted hosts). Document the cert-renewal difference.
- **C-CI-1** — Replace the single-frontend `cloudbuild.yaml` conditional with `cloudbuild.shell.yaml` (image) + `cloudbuild.remote.yaml` (GCS) + a `dorny/paths-filter` matrix when the multi-project Angular workspace lands.
- **C-CSP-1** — CSP is authored from scratch (none exists today). Mechanism = nginx.conf in the shell image OR a CSP-only Traefik Middleware; must NOT touch the app's CORS headers or the refresh-token `Set-Cookie`. Exact `script-src`/`connect-src` origin allowlist is a joint infra ↔ frontend deliverable; author + smoke-test on `dev` BEFORE the first remote is wired.
- **C-STAGING-1** — staging has no workload pods today; if staging later mirrors dev AND adds in-cluster remotes it hits the same 2-vCPU wall. Keep staging remotes off-cluster too (separate `remotes-staging.mesell.xyz` CDN bucket per DRAFT §5.2).

### What S5's ratification session should lock as a result
1. **Hosting model = Option C (hybrid).** Lock it, closing DRAFT sub-question MF-ENV-1 (recommend separate per-env buckets for blast-radius isolation).
2. **Remote count = 6** (MASTER_PLAN §2.2), reconciling the DRAFT infra plan's illustrative 7-remote set down to 6.
3. **No `dev` VM machine-type change for V1** — accept Option C precisely so the current 2-vCPU node suffices (or explicitly approve a VM bump if Option A is ever desired).
4. **CSP ownership split** — infra owns the header mechanism + per-env templating; frontend-coordinator owns the origin/token allowlist; both land in Sub-plan 7 before the first remote cutover.
5. **Cost sign-off** for the GCS bucket(s) + Cloud CDN + the `remotes.mesell.xyz` HTTPS LB (a global external LB forwarding rule carries a standing hourly charge — flag against the >₹500/mo gate during MF-CDN-1 estimation).
