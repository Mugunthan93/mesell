# SP07 — Cutover & Hardening — INFRA handoff spec (for meesell-infra-builder — standalone, executes directly)

**Authored:** mesell-mfe-cutover-frontend-session-1 (HYBRID step 1 — SPEC ONLY)
**Authoritative source:** `docs/plans/module_federation/SUB_PLAN_07_cutover_hardening.md` (D42/D44/D45 — FOUNDER-FLAGs RULED 2026-06-11) + `docs/plans/infra/GATE4_CONFIRMATION.md` (the 6 C-conditions, infra-owned).
**Ground-truth tip:** `origin/develop` @ `756d070` — all 6 remotes (pricing 4201 / export 4202 / onboarding 4203 / dashboard 4204 / catalog 4205 / auth 4206) on develop; manifest = 6 localhost entries.
**Nature:** This is a CROSS-LEAD HANDOFF, NOT a frontend specialist dispatch. `meesell-infra-builder` is a standalone agent (opus) that executes directly. The frontend lead files this via the memo `handoff_mf_cutover.md` and adds an Inter-lead-request row to `feature_board_frontend.md` (48h SLA). Infra reads it + adds its OWN incoming-side row to its OWN board (decentralized memory protocol — frontend does NOT edit infra's board).

> NOTE: this spec is the FRONTEND LEAD's authored handoff content. The infra lead OWNS the mechanism decisions; the frontend lead owns the allowlist CONTENT + the gating discipline. Where this spec says "infra's call," it is genuinely infra's call — this is the requirements + constraints, not a prescription of infra internals.

---

## 0. What infra owns at SP07 (4 of the 6 Gate-4 conditions + the CSP mechanism + manifest templating)

| Item | Owner | Frontend dependency |
|---|---|---|
| CSP header MECHANISM (ADD-ONLY) | **infra** | frontend provides the allowlist CONTENT (below) |
| Dev CSP smoke (incl. 401→refresh→retry non-regression + remote-load proof) | **infra emits header; frontend+backend run the smoke** | joint |
| Per-env manifest envsubst templating + `remotes(-staging).mesell.xyz` buckets | **infra** | frontend provides the manifest SHAPE + no-`latest` discipline |
| C-RES-1, C-RES-2, C-ROUTE-1, C-CI-1, C-STAGING-1 | **infra** | frontend's C-CSP-1 allowlist is the joint piece |
| D13 GCS/CDN/LB provisioning (the 6-remote hosting wave) | **infra** | **GATED ON FOUNDER COST SIGN-OFF — see §4** |

The frontend lead owns: the CSP allowlist content (§1), the manifest shape + no-`latest` rule (handed to the component-builder, see `spec_sp07_frontend.md` B1), the full federated smoke orchestration, the §5.1 audit, and the Gate-4 discharge SIGN-OFF (collating infra's evidence).

---

## 1. THE CSP — frontend-owned ALLOWLIST + infra-owned ADD-ONLY MECHANISM (D42, RULED APPROVED 2026-06-11)

### 1.1 The frontend-owned allowlist CONTENT (the requirement infra implements)

The Native-Federation runtime + es-module-shims + Angular + PrimeNG/Tailwind demand these origins. **CONFIRM each token EMPIRICALLY on dev** (the public landing + public auth remotes are the proof surfaces — if a token is missing they white-screen):

```
default-src 'self'
script-src  'self' https://remotes.mesell.xyz 'wasm-unsafe-eval'
              # 'wasm-unsafe-eval' OR a per-response nonce — es-module-shims/Angular may need it;
              # CONFIRM on dev. Prefer a nonce over 'unsafe-inline' for scripts if feasible.
connect-src 'self' https://api.mesell.xyz https://remotes.mesell.xyz
              # the API + the federation.manifest.json fetch + every remoteEntry.json + chunk fetch
style-src   'self' 'unsafe-inline' https://remotes.mesell.xyz
              # Tailwind/PrimeNG inject runtime <style>; 'unsafe-inline' for styles is the pragmatic
              # V1 choice (style nonces are impractical with Angular component styles). CONFIRM.
font-src    'self' https://remotes.mesell.xyz data:
img-src     'self' data: https://remotes.mesell.xyz
```
(Staging swaps `remotes.mesell.xyz` → `remotes-staging.mesell.xyz` and `api.mesell.xyz` → the staging API host. The dev smoke uses `'self'` + the localhost remote origins — see §2.)

### 1.2 The infra-owned MECHANISM — TWO HARD CONSTRAINTS (this is the P0 of the whole cutover)

1. **ADD-ONLY.** Emit EXACTLY ONE response header: `Content-Security-Policy`. Two viable layers (infra's call):
   - (a) `add_header Content-Security-Policy "<policy>" always;` in the shell image's `nginx.conf`, OR
   - (b) a CSP-only Traefik `Middleware` CRD (`headers.customResponseHeaders.Content-Security-Policy`).
   Either is fine PROVIDED it only ADDS the CSP header.
2. **MUST NOT strip / override / reorder ANY of:**
   - the app's **CORS** response headers (`Access-Control-Allow-Origin` etc. — owned by the FastAPI app per BACKEND_ARCHITECTURE §4.G), and
   - the **refresh-token `Set-Cookie`** (HttpOnly + Secure + SameSite=Strict, `Path=/api/v1/auth`, owned by backend per FE-D5/FE-D6 + CLAUDE.md D14).
   **A broad "security headers" middleware that rewrites the whole header set is FORBIDDEN** — it is the exact R-SP7-1 P0 regression (silent logout-loops in prod). Use a narrow CSP-only addition.

### 1.3 Why this is load-bearing (R-SP4-5 + R-SP6-6)

`mfe-dashboard` exposes the PUBLIC landing (`/`) and `mfe-auth` exposes the PUBLIC `/login` `/signup` `/otp-verify` — all fetched by an UNAUTHENTICATED browser with no Authorization header. Their `remoteEntry.json` + chunks load cross-origin from `remotes.mesell.xyz` into the shell origin BEFORE any auth. If `script-src`/`connect-src` omit the remotes origin, every first-time visitor white-screens. These two remotes are the highest-stakes CSP surfaces in the migration (escalated from SP04/SP06 into SP07 — see `handoff_mf_auth_deploy.md`).

---

## 2. DEV CSP SMOKE PROCEDURE (gate the staging/prod cutover on a GREEN result)

Run on DEV FIRST (C-CSP-1: author + smoke on dev before any staging/prod ship). Three checks, ALL must be GREEN:

**(A) Remote-loading proof.** With the dev CSP header active on the shell origin:
- Load `/` (public landing → mfe-dashboard) and `/login` (public auth → mfe-auth) in a browser.
- Browser console shows ZERO `Refused to load the script`/`Refused to connect`/`violates the following Content Security Policy directive` errors.
- Both remotes MOUNT (landing renders; login form renders). Then an authenticated route (`/dashboard`, `/catalogs/:id/pricing`) also mounts.
- If a violation appears, add the missing token to the §1.1 allowlist (iterate on dev only) and re-run.

**(B) 401 → refresh → retry NON-REGRESSION (the R-SP7-1 P0 guard).** With the CSP active:
- Trigger an API call that 401s (expired access JWT). The frontend's refresh flow POSTs to the refresh endpoint; the backend returns a NEW access token AND re-sets the refresh `Set-Cookie`. The original request retries and succeeds.
- **VERIFY the refresh `Set-Cookie` is PRESENT on the refresh response (not stripped by the CSP mechanism) and the cookie attributes are intact (HttpOnly, Secure, SameSite=Strict, Path=/api/v1/auth).** This is the proof the ADD-ONLY mechanism didn't clobber the cookie. Run this WITH and WITHOUT the CSP and confirm identical behaviour.
- Backend/auth owns the refresh endpoint; coordinate the smoke with `meesell-backend-coordinator` (a lightweight verification note, not a backend code change — the refresh flow already exists). The frontend lead orchestrates this joint smoke.

**(C) CORS non-regression.** A cross-origin API call from the shell origin still gets the expected `Access-Control-Allow-Origin`/`-Credentials` headers WITH the CSP active.

**GATING RULE (RULED D42):** staging/prod remote cutover is BLOCKED until (A)+(B)+(C) are GREEN on dev. A regression in (B) or (C) is a HARD REJECT — re-coordinate the mechanism via the memo. Record the smoke evidence in the SP07 Gate-4 discharge (C-CSP-1).

---

## 3. PER-ENV MANIFEST TEMPLATING (D44 / C-STAGING-1)

The frontend component-builder authors the manifest SHAPE (`spec_sp07_frontend.md` B1): dev = localhost (unchanged); staging/prod = templates with `{ENV}`/`{VERSION}` tokens. **Infra owns the envsubst substitution + the buckets:**

- **Buckets (C-RES-2 / C-STAGING-1):** prod remotes at `gs://meesell-frontend/prod/mfe-<name>/<version>/`, served via CDN at `https://remotes.mesell.xyz/prod/mfe-<name>/<version>/remoteEntry.json`. Staging at `gs://meesell-frontend/staging/...` served at `https://remotes-staging.mesell.xyz/staging/...` (OFF-CLUSTER — no in-cluster staging remote pods).
- **`{VERSION}` is an EXACT build hash/semver per remote — NEVER the literal `latest`.** This is the R5 / R-SP7-6 contract-drift mitigation: the shell's deployed manifest pins the EXACT remote build it was tested against; a remote can't silently ship a breaking change because the shell loads the pinned hash until the manifest is updated in lockstep. Rollback = re-point the manifest `{VERSION}` at the prior build (atomic).
- **The C-CI-1 `shared/**`-rebuilds-all rule (carried from SP05 R5):** a `frontend/libs/**` (`@mesell/core`/`ui-kit`/`composites`/`design-tokens`) change must rebuild EVERY remote + bump every pinned `{VERSION}` in lockstep (because the shared singleton URL changes). Infra owns this lockstep in the cloudbuild matrix.
- **Singleton CDN rule (carried from `handoff_mf_auth_deploy.md`):** the CDN MUST serve the SAME `@mesell/core` / `@mesell/ui-kit` / `@mesell/composites` module URLs to the shell AND to every consuming remote. `mfe-onboarding` (profile → AuthService READ, C5) and `mfe-auth` (otp-verify → setSession WRITE, C4) are the two `@mesell/core` consumers — a per-remote stale duplicate of `@mesell/core` = singleton drift = the auth loop breaks at runtime. Both must resolve the identical `_mesell_core.js` URL as the shell.

---

## 4. ⛔ D13 HOSTING WORK-PACKAGE — FOUNDER COST GATE (do NOT provision before founder sign-off)

The founder deferred GCS/CDN/LB provisioning "until the SP04-05 era" — **that era is NOW** (SP07 is the cutover). BUT the actual provisioning of the real `remotes.mesell.xyz` GCS buckets + Cloud CDN + load balancer + managed certs carries a **monthly cost** that was sized at Gate-4 (C-CDN-1 / the GATE4_CONFIRMATION.md cost estimate).

**HARD GATE (founder ruling, D13 hosting timing):**
- **The founder signs off the GCS/CDN/LB monthly cost BEFORE infra provisions anything.** Infra prepares the work-package (the bucket layout, the CDN config, the cert plan, the cost estimate refreshed from Gate-4/C-CDN-1) and presents the COST to the founder via `STATUS_MASTER.md` (or the agreed founder surface). Infra does NOT create billable cloud resources until the founder approves the cost.
- **Dev-level validation MUST NOT depend on the hosted surface.** All SP07 dev validation (the relocation build, the test suite, the CSP smoke, the federated smoke) uses LOCALHOST-served remotes (ports 4201–4206). The frontend merge of the shell-strip + relocation + manifest shape to develop is NOT blocked on the hosted surface. Only the STAGING/PROD cutover blocks on it (R-SP7-4: the frontend cleanup can land on develop while the infra hosting + cost gate resolve in parallel; the migration is not COMPLETE until all 6 C-conditions discharge).

The hosting work-package items (the 6-remote consolidated wave — RECORD-ONLY rows already filed across `handoff_mf_{pricing,export,onboarding,dashboard,catalog,auth}_deploy.md`):
1. GCS prefixes `gs://meesell-frontend/{env}/mfe-<name>/{version}/` for all 6 remotes.
2. Cloud CDN fronting `remotes.mesell.xyz` (prod) + `remotes-staging.mesell.xyz` (staging), world-readable (public remotes loaded pre-auth), GCP-managed cert NOT cert-manager (C-ROUTE-1).
3. Namecheap A records for `remotes(-staging).mesell.xyz` (C-ROUTE-1).
4. The cloudbuild matrix split (C-CI-1): `cloudbuild.shell.yaml` + `cloudbuild.remote.yaml` + a `dorny/paths-filter` matrix where `apps/mfe-<name>/**` rebuilds only that remote and `libs/**` (`shared/**`) rebuilds ALL.

**Reconfirm with infra's own memory:** the C-CI-1 prep was requested at SP0 (`handoff_mf_ci_prep.md`) and a ci-matrix worktree was observed in flight at SP01 — check `.claude/agent-memory/meesell-infra-builder/MEMORY.md` for current state before re-deriving. Also note (frontend relocation impact on CI): the shell relocates to `apps/shell/**` at SP07 (D43), which makes the cloudbuild matrix UNIFORM (`apps/<name>/**` triggers `<name>`'s build for shell AND remotes) — infra should fold the `apps/shell/**` glob into the matrix and retire any `src/**`-special-case shell rule.

---

## 5. THE 6 GATE-4 C-CONDITIONS — infra-side discharge evidence (D45)

Infra returns evidence for the 4 infra-owned + the joint C-CSP-1; the frontend lead collates the discharge sign-off. NONE may be left open at SP07 close (but the staging/prod-dependent ones can land in parallel with the founder cost gate per §4 — the migration is COMPLETE only when all 6 are GREEN).

| Condition | Discharge | Evidence infra returns |
|---|---|---|
| C-RES-1 (Option A in-cluster INFEASIBLE) | Not taken — no in-cluster remote pods | `kubectl get deploy -n dev` shows only `mfe-shell` (+ api/worker), NO `mfe-*` remote pods |
| C-RES-2 (Option C: shell in-cluster, 6 remotes GCS/CDN) | shell Deployment swaps the retiring `frontend` Deployment (~0 net CPU); remotes in GCS | `kubectl describe node` CPU requests unchanged ±shell delta |
| C-ROUTE-1 (`remotes.mesell.xyz` Namecheap A + GCP-managed cert) | host resolves + serves over HTTPS | `curl -I https://remotes.mesell.xyz/<env>/mfe-pricing/<version>/remoteEntry.json` → 200 + valid GCP-managed cert |
| C-CI-1 (cloudbuild split + paths-filter matrix) | a remote-only change rebuilds only that remote; a `libs/**` change rebuilds all | a test push showing the matrix fan-out |
| C-CSP-1 (CSP ADD-ONLY, dev-smoked, no CORS/cookie regression) | §1+§2 above | the dev CSP smoke result (A+B+C all GREEN) |
| C-STAGING-1 (staging remotes off-cluster) | staging manifest → `remotes-staging.mesell.xyz` | the staging manifest + `kubectl get deploy -n staging` (no remote pods) |

---

## 6. Branch / merge mechanics (the FIRST two-group sub-plan)

- Infra cuts `feature/mfe-cutover/infra` from `feature/mfe-cutover/integration` (the frontend lead creates the integration branch off develop). Infra commits the CSP mechanism (nginx/Traefik), the cloudbuild matrix + envsubst templating, the per-env bucket config there.
- The infra group PR `feature/mfe-cutover/infra` → integration is REVIEWED by the FRONTEND lead (D1: lead merges group → integration) WITH the infra lead's content sign-off in the PR (the frontend lead is the domain merge gate; infra-content correctness is the infra lead's sign-off). The CSP-ADD-ONLY constraint (§1.2) is a HARD review item: if the mechanism strips a CORS/`Set-Cookie` header → REJECT + re-coordinate.
- The integration → develop PR is the FOUNDER's gate (D1 — not the lead's).
- This is the first sub-plan with TWO group branches (frontend + infra) into one integration — the §5.1 audit notes this as a real test of the multi-group merge gate.

---

## 7. What infra must NOT do

- Do NOT strip/override/reorder the app's CORS headers or the refresh-token `Set-Cookie` (§1.2 — the R-SP7-1 P0).
- Do NOT use a broad "security headers" middleware — CSP-only ADD.
- Do NOT provision billable GCS/CDN/LB resources before the founder cost sign-off (§4).
- Do NOT edit `feature_board_frontend.md` (frontend lead's sole-writer surface) — add the incoming-side row to infra's OWN board.
- Do NOT touch the frontend shell relocation (that is the component-builder's, `spec_sp07_frontend.md`) — infra's frontend-facing surface is ONLY the angular.json `apps/shell/**` glob awareness for the CI matrix (read-only awareness; the relocation edits are the component-builder's).

---

## 8. How to resolve (decentralized memory protocol)

Infra reads this spec + the memo `handoff_mf_cutover.md` (the frontend lead files it) + adds its OWN incoming-side row to `feature_board_infra*.md`. When the CSP mechanism + per-env templating + the 4 infra-side C-conditions are delivered (and the founder cost gate cleared for the hosted surface), the FRONTEND lead marks the inter-lead row CLOSED on its own board and folds the evidence into the SP07 Gate-4 discharge. 48h SLA before escalation to founder via `STATUS_MASTER.md`.
