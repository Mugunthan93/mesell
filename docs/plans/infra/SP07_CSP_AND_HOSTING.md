# SP07 — CSP Mechanism, Dev Smoke, Cutover Gating & D13 Hosting Work-Package

**Author:** `meesell-infra-builder` · **Session:** `mesell-mfe-cutover-infra-session-1` · **Date:** 2026-06-11
**Spec consumed (read-only):** `.claude/agent-memory/meesell-frontend-coordinator/spec_sp07_infra.md` (frontend lead's handoff) + `handoff_mf_auth_deploy.md` (R-SP6-6 / C-CSP-1 escalation).
**Authoritative refs:** `docs/plans/infra/GATE4_CONFIRMATION.md` (the 6 C-conditions, Option C) · `docs/INFRASTRUCTURE_PLAYBOOK.md` §8/§9/§10/§15 · `docs/DEVOPS_ARCHITECTURE.md` §6/§9.
**Branch:** `feature/mfe-cutover/infra` → (frontend-lead-gated) `feature/mfe-cutover/integration`.
**Cost of everything in THIS doc as authored:** ₹0/month (no billable resource created — §4 is gated on founder cost sign-off).

---

## 1. The CSP mechanism choice (D42) — nginx add_header in the shell image (PRIMARY)

Two viable layers per spec §1.2 (infra's call). **CHOSEN: (a) nginx `add_header` in the shell image.** The Traefik CSP-only Middleware (`k8s/csp/csp-middleware.yaml`) is delivered as a documented ALTERNATIVE/hotfix layer, not the primary.

### Why nginx add_header (not the Traefik Middleware) is the primary

The P0 constraint (spec §1.2 / R-SP7-1) is: **the CSP mechanism MUST NOT strip / override / reorder the app's CORS headers or the refresh-token `Set-Cookie`.** The strongest guarantee is a mechanism that is *physically incapable* of touching those headers:

1. **The shell nginx serves ONLY the shell's own static assets** (index.html, federated JS chunks, the manifest) from the shell origin. The CORS headers and the refresh `Set-Cookie` are emitted by the **API origin** (`api.mesell.xyz`) — a different pod, a different origin. The browser calls the API **directly** (CSP `connect-src` allows `api.mesell.xyz`); the shell nginx is **never a reverse proxy in front of the API**. So the shell nginx is not in the CORS / cookie path at all — it cannot clobber what it never sees. (Hard rule encoded in `nginx.conf.template`: no `location /api/ { proxy_pass }` block — adding one would re-open R-SP7-1.)
2. **ADD-ONLY by construction.** `nginx.conf.template` contains exactly one security header directive: `add_header Content-Security-Policy "${CSP_POLICY}" always;`. There is no `proxy_hide_header`, no `more_clear_headers`, no header rewrite. `envsubst` substitutes only `${CSP_POLICY}`.
3. **Per-env templating** (spec §3 / C-CSP-1): `docker-entrypoint.sh` selects `CSP_POLICY_{dev,staging,prod}` from `csp-policy.env` by `$APP_ENV` and renders the template at container start. One image, three CSPs.
4. **`auto-csp` option:** Angular 21's `@angular/build` `auto-csp` can emit a hash/nonce CSP at build time — noted for a future hardening pass (replace `'wasm-unsafe-eval'`/`'unsafe-inline'` with nonces). Not taken for V1: the dev smoke (§3) confirms the static allowlist first; nonces are a follow-up.

### Why the Traefik Middleware is the documented ALTERNATIVE (not primary)

It is real and safe **if** scoped CSP-only (`headers.customResponseHeaders` with exactly `Content-Security-Policy`, attached to the shell Ingress only — see `k8s/csp/csp-middleware.yaml`, which the offline validator proves is ADD-ONLY). Its advantage is kubectl/Terraform edit without an image rebuild. Its risk is that a *future* careless edit could add `stsSeconds`/`frameDeny`/etc. and broaden into a header-rewriting middleware (the forbidden R-SP7-1 shape). The nginx layer has no such failure mode. **Use the Middleware only for a dev-only allowlist hotfix; the shipped CSP is the nginx one.** Never attach a CSP middleware to the `api.mesell.xyz` Ingress.

### Files delivered (mechanism)
| File | Role |
|---|---|
| `frontend/docker/nginx.conf.template` | ADD-ONLY nginx CSP, `${CSP_POLICY}` placeholder, SPA fallback, no API proxy |
| `frontend/docker/csp-policy.env` | per-env CSP values (allowlist CONTENT is frontend-owned, consumed verbatim from spec §1.1) |
| `frontend/docker/docker-entrypoint.sh` | `envsubst` renderer keyed on `$APP_ENV` |
| `frontend/docker/Dockerfile.shell` | reference shell image wiring the 3 files above (relocation reconciles per §6) |
| `k8s/csp/csp-middleware.yaml` | ALTERNATIVE Traefik CSP-only Middleware (dev + staging), ADD-ONLY-validated |

> **Allowlist ownership (spec §0/§1.1):** the directive CONTENT is frontend-owned. Infra consumed the §1.1 tokens verbatim. If the dev smoke (§3(A)) reveals a missing token, the frontend lead revises the allowlist and infra updates `csp-policy.env` + `csp-middleware.yaml` in lockstep — infra does NOT invent tokens.

---

## 2. CSP allowlist (consumed from spec §1.1 — frontend-owned content)

Per-env, as encoded in `csp-policy.env`:

- **dev** (smoke surface): `'self'` (shell origin) + the six localhost remote origins `http://localhost:4201..4206` on `script-src`/`connect-src`/`style-src`/`font-src`/`img-src`, + `https://api.mesell.xyz` on `connect-src`. `'wasm-unsafe-eval'` on `script-src`, `'unsafe-inline'` on `style-src` (spec §1.1 pragmatic V1 — CONFIRM on dev).
- **staging**: `https://remotes-staging.mesell.xyz` + `https://staging-api.mesell.xyz`.
- **prod** (V1.5): `https://remotes.mesell.xyz` + `https://api.mesell.xyz`.

All three add `base-uri 'self'` and `object-src 'none'` (defense-in-depth, no functional cost). `default-src 'self'` is the floor.

---

## 3. DEV CSP SMOKE PROCEDURE (gate the staging/prod cutover on a GREEN result)

Run on **dev FIRST** (C-CSP-1). All three checks (A)+(B)+(C) must be GREEN before any staging/prod CSP flip (§4 gating). The shell + 6 remotes are served from **localhost (ng serve 4201–4206)** — the smoke does NOT depend on the hosted CDN surface (spec §4 / R-SP7-4).

### Preconditions
- Shell relocation (`apps/shell`, D43) + per-env manifest shape (component-builder lane) merged on the integration branch.
- All 6 remotes serving locally: `ng serve mfe-pricing --port 4201` … `mfe-auth --port 4206` (frontend lead orchestrates).
- Shell built/served with the **dev** CSP active. Two ways to put the dev CSP on the shell origin for the smoke:
  - run the shell image with `APP_ENV=development` (entrypoint renders `CSP_POLICY_dev`), OR
  - if smoking against `dev.mesell.xyz` via Traefik, `kubectl apply --dry-run=server` then apply `k8s/csp/csp-middleware.yaml` (dev Middleware) and attach it to the shell Ingress (annotation `traefik.ingress.kubernetes.io/router.middlewares: dev-csp-shell@kubernetescrd`). **[MANDATORY GATE] playbook §15: server-side dry-run MUST pass before the real apply.**

### (A) Remote-loading proof  [frontend+infra]
With the dev CSP header active on the shell origin:
1. Load `/` (public landing → `mfe-dashboard`) and `/login` (public auth → `mfe-auth`) in a browser as an **unauthenticated** user (no Authorization header).
2. Browser console shows ZERO `Refused to load the script` / `Refused to connect` / `violates the following Content Security Policy directive` errors.
3. Both PUBLIC remotes MOUNT (landing renders; login form renders) — these are the two highest-stakes pre-auth surfaces (spec §1.3 / R-SP6-6).
4. Then an authenticated route (`/dashboard`, `/catalogs/:id/pricing`) also mounts.
5. Verify the CSP header is actually present: `curl -sI https://dev.mesell.xyz/ | grep -i content-security-policy` (or browser DevTools → Network → response headers).
- **If a violation appears:** add the missing token to `csp-policy.env` (dev value) — iterate on **dev only** — and re-run. Record each iteration.

### (B) 401 → refresh → retry NON-REGRESSION  [the R-SP7-1 P0 guard — joint with backend]
With the CSP active:
1. Trigger an API call that 401s (expired access JWT). The frontend refresh flow POSTs to the refresh endpoint; the backend returns a NEW access token AND re-sets the refresh `Set-Cookie`; the original request retries and succeeds.
2. **VERIFY the refresh `Set-Cookie` IS PRESENT on the refresh response** (not stripped) AND its attributes are intact: `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/v1/auth`.
   - DevTools → Network → the refresh request → Response Headers → confirm `Set-Cookie`.
   - Because the chosen mechanism (nginx on the shell origin) is NOT in the API path, this header comes straight from `api.mesell.xyz` — the proof is that the CSP did not change it.
3. Run the flow **WITH and WITHOUT** the CSP active and confirm IDENTICAL behaviour (same cookie, same retry success).
- Coordinate with `meesell-backend-coordinator` — a lightweight verification note, not a backend code change (the refresh flow already exists). Frontend lead orchestrates.
- **A regression here is a HARD REJECT** of the mechanism (spec §2 gating). Re-coordinate via memo.

### (C) CORS NON-REGRESSION  [joint]
With the CSP active, a cross-origin API call from the shell origin still receives the expected `Access-Control-Allow-Origin` / `Access-Control-Allow-Credentials` headers (owned by FastAPI per BACKEND_ARCHITECTURE §4.G):
- `curl -sI -H 'Origin: https://dev.mesell.xyz' https://api.mesell.xyz/api/v1/... | grep -i access-control` shows the ACAO/ACAC headers unchanged vs the no-CSP baseline.
- Same reasoning as (B): the CSP nginx is not in front of the API, so CORS is structurally untouched — (C) is the empirical confirmation.

### GATING RULE (RULED D42)
Staging/prod remote cutover is **BLOCKED** until (A)+(B)+(C) are GREEN on dev. A regression in (B) or (C) is a HARD REJECT. Record the smoke evidence (the curl/DevTools captures) in the SP07 Gate-4 discharge (C-CSP-1).

---

## 4. ⛔ STAGING / PROD CUTOVER GATING (codified — D42)

> **NO staging or prod CSP flip — and no staging/prod remote cutover — until the §3 dev CSP smoke is GREEN on all three checks (A+B+C).**

Codified as an ordered gate:

1. **Dev smoke GREEN** (§3 A+B+C) — recorded evidence. ← hard precondition for everything below.
2. **Founder cost sign-off** for the hosted surface (§5) — hard precondition for provisioning `remotes(-staging).mesell.xyz`.
3. **Staging:** provision `gs://meesell-frontend/staging/...` + `remotes-staging.mesell.xyz` (CDN + GCP-managed cert + Namecheap A record). Apply the staging CSP (nginx `APP_ENV=staging`, or the staging Middleware after `--dry-run=server`). Smoke the staging public landing + auth. Per playbook §0: never ship to staging without the dev pass; never ship to prod without staging.
4. **Prod (V1.5):** prod namespace is DEFERRED per master plan §3.1 — do NOT create until V1.5 acceptance lights it. The prod CSP value + prod Middleware are authored at that lighting, not now.

The frontend cleanup (shell-strip + relocation + manifest shape) can land on `develop` in parallel — it is NOT blocked on the hosted surface (R-SP7-4). Only the staging/prod CUTOVER blocks on §3 + §5.

---

## 5. D13 HOSTING WORK-PACKAGE — FOUNDER COST GATE (NOT PROVISIONED)

> **HARD FOUNDER COST GATE.** Everything in this section is a PREPARED work-package + cost estimate. Infra creates ZERO billable cloud resources until the founder signs off the monthly cost (>₹500/mo rule). Provisioning is targeted at cutover week, AFTER the dev smoke is GREEN and the cost is approved.

### 5.1 What gets provisioned (the 6-remote consolidated wave — Option C, GATE4 C-RES-2)

| # | Resource | Detail |
|---|---|---|
| 1 | GCS bucket `meesell-frontend` (asia-south1, uniform-bucket-level-access, versioning ON) | prefixes `gs://meesell-frontend/{env}/mfe-<name>/{version}/` for all 6 remotes + the shell-served manifest; `{env}∈{staging,prod}`, `{version}`=exact build hash/semver (NEVER `latest` — R-SP7-6). Objects world-readable (public remotes loaded pre-auth). |
| 2 | Cloud CDN + global external HTTPS LB | backend-bucket origin = the GCS bucket; URL maps `remotes.mesell.xyz` (prod) + `remotes-staging.mesell.xyz` (staging) → the bucket prefixes. **This LB forwarding rule is the cost driver.** |
| 3 | GCP-managed SSL cert (C-ROUTE-1) | `google_compute_managed_ssl_certificate` for `remotes.mesell.xyz` + `remotes-staging.mesell.xyz`. **NOT cert-manager** — cert-manager only covers K3s-fronted hosts; the CDN/LB host is off-cluster. |
| 4 | Namecheap A / forwarding records (C-ROUTE-1) | `remotes.mesell.xyz` + `remotes-staging.mesell.xyz` → the LB's global anycast IP. Founder owns the Namecheap account → founder action (infra supplies the IP post-provision). |
| 5 | Cloud Build SA bucket grant | `roles/storage.objectAdmin` on `gs://meesell-frontend` for `888244156264-compute@developer.gserviceaccount.com` (the actual Cloud Build runner SA, per D-API-5). Terraform-owned, additive `google_storage_bucket_iam_member`. The only IAM add. |

These are RECORD-ONLY consolidations of the 6 per-remote rows already filed across `handoff_mf_{pricing,export,onboarding,dashboard,catalog,auth}_deploy.md`.

### 5.2 Terraform module plan (authored as a PLAN, not applied)

A new module `infra/terraform/modules/frontend_cdn/` (to be authored + applied ONLY post-sign-off) would hold:
- `google_storage_bucket.frontend` (+ `uniform_bucket_level_access`, `versioning`, `public_access_prevention=inherited`, object-level `allUsers:objectViewer` via `google_storage_bucket_iam_member` for world-read).
- `google_compute_backend_bucket.remotes` (`enable_cdn=true`, cache mode `CACHE_ALL_STATIC`).
- `google_compute_url_map` + `google_compute_target_https_proxy` + `google_compute_global_forwarding_rule` (the standing-charge resource).
- `google_compute_managed_ssl_certificate.remotes` (domains: both hosts).
- `google_storage_bucket_iam_member` (objectAdmin for the Cloud Build compute SA).
- `_REMOTES_BUCKET` substitution in `cloudbuild.yaml` flips from `""` → `gs://meesell-frontend` at activation (the publish-remotes step is already INERT-until-set — see `cloudbuild.yaml` step 8).

**Not authored as live `.tf` in this PR** — authoring + `terraform plan`/`apply` happens in the post-sign-off provisioning session. This doc + the cost sheet are the work-package the founder reviews.

### 5.3 Cost sheet → `docs/plans/infra/SP07_HOSTING_COST_SHEET.md`

Refreshed from GATE4 C-CDN-1. Headline: **~₹1,600–1,800/month, LB-dominated.** This is **> the ₹500/month founder cost gate** → explicit founder sign-off REQUIRED before provisioning. Full breakdown in the cost sheet.

---

## 6. CI matrix + manifest templating (C-CI-1 / D44 / D43 relocation)

See `docs/DEVOPS_ARCHITECTURE.md` §9 (sole-writer; updated in this PR). Summary of the SP07 changes to `.github/workflows/ci.yml` + `cloudbuild.yaml`:

- **ci.yml frontend matrix extended** from {shell, mfe-pricing} to all 6 remotes + shell. Each remote gets one `paths-filter` block + one matrix `include` entry (the spec's "one-line addition in two places", now done for all 6).
- **D43 relocation awareness:** the `shell` filter now matches BOTH `frontend/src/**` (pre-D43) AND `frontend/apps/shell/**` (post-D43), so the matrix is forward-compatible with the shell relocation regardless of which side lands first. The relocation edits themselves are the component-builder's (spec §7) — infra only folds the glob.
- **`libs/**` fan-out unchanged:** a `frontend/libs/**` (`@mesell/core`/`ui-kit`/`composites`/`design-tokens`) change rebuilds EVERY unit (C-CI-1 / SP05 R5) — the shared-singleton-URL lockstep.
- **cloudbuild.yaml:** the `publish-remotes` step already globs `dist/mfe-*/browser` (all 6, no per-remote edit needed) and is INERT until `_REMOTES_BUCKET` is set (§5.2). `{VERSION}` pinning (no `latest`) is the manifest contract (D44 / R-SP7-6); the manifest SHAPE is the component-builder's, infra owns the envsubst substitution + the bucket prefix.

---

## 7. The 6 Gate-4 C-conditions — infra-side discharge status (D45)

| Condition | Status at this PR | Evidence / next |
|---|---|---|
| C-RES-1 (Option A infeasible) | DISCHARGED (not taken) | Option C only; no in-cluster remote pods. `kubectl get deploy -n dev` will show only shell (+api/worker) at cutover. |
| C-RES-2 (Option C: shell in-cluster, remotes GCS/CDN) | MECHANISM READY | shell image (Dockerfile.shell) swaps the retiring `frontend` Deployment; remotes → GCS (§5). Provision gated on §5. |
| C-ROUTE-1 (`remotes.mesell.xyz` A record + GCP cert) | WORK-PACKAGE READY (§5) | NOT provisioned — founder cost gate. `curl -I` evidence captured at provisioning. |
| C-CI-1 (cloudbuild split + paths-filter matrix) | DISCHARGED-pending-activation | ci.yml 6-remote matrix + cloudbuild INERT publish. Fan-out test at cutover. |
| C-CSP-1 (CSP ADD-ONLY, dev-smoked, no CORS/cookie regression) | MECHANISM READY; smoke PENDING | §1–§3. Discharges when §3 (A+B+C) GREEN on dev. |
| C-STAGING-1 (staging remotes off-cluster) | WORK-PACKAGE READY (§5) | staging manifest → `remotes-staging.mesell.xyz`; no staging remote pods. |

NONE may be left open at SP07 close, but the staging/prod-dependent ones (C-ROUTE-1, C-RES-2 provision, C-STAGING-1) land in parallel with the founder cost gate (§4). The migration is COMPLETE only when all 6 are GREEN.

---

## 8. What infra did NOT do (spec §7 + hard constraints)

- Did NOT strip/override/reorder CORS or the refresh `Set-Cookie` (nginx is off the API path by construction; Middleware is ADD-ONLY-validated).
- Did NOT use a broad "security headers" middleware — CSP-only.
- Did NOT provision any billable GCS/CDN/LB resource (founder cost gate, §5).
- Did NOT edit `feature_board_frontend.md` (sole-writer) — added the incoming-side row to `feature_board_infra.md`.
- Did NOT touch the frontend shell relocation / `frontend/apps/**` / `frontend/src/**` SOURCE (component-builder lane). The only frontend-tree files authored are under `frontend/docker/` (the CSP DELIVERY mechanism, infra-owned) — not app source.
- Did NOT merge — the frontend lead runs the joint multi-group merge gate (§6 of the spec).
- No `terraform apply`, no cluster mutation, no Secret Manager op.
