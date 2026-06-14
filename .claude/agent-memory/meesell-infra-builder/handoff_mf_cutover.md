# Handoff (infra → frontend lead) — SP07 cutover infra deliverables

**From:** meesell-infra-builder (Infra Lead) · **Session:** mesell-mfe-cutover-infra-session-1 · **Date:** 2026-06-11
**Re:** the incoming cross-lead request `spec_sp07_infra.md` + `handoff_mf_auth_deploy.md` (R-SP6-6 / C-CSP-1).
**Branch:** `feature/mfe-cutover/infra` (cut from `origin/develop` @ be2a888 — see NOTE below re: integration branch).
**Status:** infra group branch PUSHED + PR opened to the integration branch. NOT merged — the FRONTEND lead runs the joint multi-group merge gate (spec §6 / D1). This memo is infra's content sign-off + the discharge evidence.

## What infra delivered (the 4 infra-owned items + joint C-CSP-1)

1. **CSP mechanism (D42) — CHOICE = nginx `add_header` in the shell image (PRIMARY); Traefik CSP-only Middleware = documented ALTERNATIVE.**
   - Files: `frontend/docker/{nginx.conf.template,csp-policy.env,docker-entrypoint.sh,Dockerfile.shell}` + `k8s/csp/csp-middleware.yaml`.
   - ADD-ONLY proven: the Middleware YAML offline-validates to a single `customResponseHeaders: {Content-Security-Policy}` and NOTHING else (no stsSeconds/frameDeny/etc.). The nginx template has exactly one `add_header Content-Security-Policy` and NO API proxy block — so it is structurally off the CORS/Set-Cookie path (those come from api.mesell.xyz, a different origin). This is the R-SP7-1 P0 guarantee.
   - Allowlist CONTENT consumed VERBATIM from your spec §1.1 (per-env in csp-policy.env). I did NOT invent tokens. If the dev smoke surfaces a missing token, you revise the allowlist, I update csp-policy.env + the Middleware in lockstep.
   - Rationale doc: `docs/plans/infra/SP07_CSP_AND_HOSTING.md` §1.

2. **Dev CSP smoke procedure** — authored, ready to run: `SP07_CSP_AND_HOSTING.md` §3 (A remote-load proof, B 401→refresh→retry non-regression incl. the Set-Cookie attribute check, C CORS non-regression). All localhost-served (ports 4201–4206) — does NOT depend on the hosted surface. Cluster was unreachable from my machine, so I offline-validated the manifests with `yaml.safe_load_all` (NOT --dry-run=client) and deferred the server dry-run to deploy time per playbook §15 [MANDATORY GATE]. Check (B) needs a lightweight backend verification note — coordinate with meesell-backend-coordinator (no backend code change).

3. **Staging/prod cutover gating** — codified: `SP07_CSP_AND_HOSTING.md` §4. NO staging/prod CSP flip or remote cutover until the dev smoke is GREEN on all 3 checks AND (for the hosted surface) the founder cost gate clears. Frontend cleanup can land on develop in parallel (R-SP7-4).

4. **D13 hosting work-package + cost sheet — PREPARED, NOT PROVISIONED (HARD FOUNDER COST GATE).**
   - Work-package: `SP07_CSP_AND_HOSTING.md` §5 (GCS `gs://meesell-frontend` + Cloud CDN + remotes(-staging).mesell.xyz LB + GCP-managed cert C-ROUTE-1 + Namecheap A records + the 1 IAM grant).
   - Cost sheet: `docs/plans/infra/SP07_HOSTING_COST_SHEET.md` — **~₹1,600–1,800/mo, LB-dominated** (>₹500/mo gate). Includes 3 cost options; infra recommends Option C (defer the standing LB to V1.5 prod) for V1.
   - Provisioning happens ONLY in a separate post-sign-off session. The cloudbuild publish-remotes step stays INERT (`_REMOTES_BUCKET`/`_REMOTES_ENV` both empty) until then.

5. **C-CI-1 matrix completion** — `.github/workflows/ci.yml` extended from {shell, mfe-pricing} to all 6 remotes + shell, with D43 relocation awareness (the `shell` filter matches BOTH `frontend/src/**` and `frontend/apps/shell/**`). `cloudbuild.yaml` publish-remotes now uses the version-pinned `{env}/mfe-<name>/{version}/` layout (no `latest`, R-SP7-6). `docs/DEVOPS_ARCHITECTURE.md` §9 synced.

## The 6 Gate-4 C-conditions — infra discharge status (your collation)
See `SP07_CSP_AND_HOSTING.md` §7. C-RES-1 DISCHARGED (Option A not taken). C-RES-2 / C-CI-1 mechanism-ready (DISCHARGED-pending-activation). C-CSP-1 mechanism-ready, smoke PENDING (discharges when §3 GREEN). C-ROUTE-1 / C-STAGING-1 work-package-ready, gated on the founder cost sign-off. None left open at SP07 close per se — the staging/prod-dependent ones land in parallel with the cost gate (R-SP7-4); migration COMPLETE only when all 6 GREEN.

## NOTE — integration branch
At my session time, `feature/mfe-cutover/integration` did NOT yet exist on origin (only `feature/mfe-cutover/frontend` @ be2a888). Per spec §6, YOU (frontend lead) create the integration branch off develop. I cut `feature/mfe-cutover/infra` from `origin/develop` (same tip be2a888) so it is mergeable into integration once you create it. If the PR base needs retargeting to integration, it's a clean fast-forward base swap (no content conflict — my files are all new except ci.yml/cloudbuild.yaml/DEVOPS which are additive).

## What I did NOT touch (spec §7)
frontend/ SOURCE (apps/**, src/** — your component-builder's lane; my only frontend-tree files are under frontend/docker/, the CSP DELIVERY mechanism). No CORS/Set-Cookie strip. No broad security-headers middleware. No billable resource provisioned. No feature_board_frontend.md edit (I added the incoming row to my own board). No merge.
