## MS-B svc-dashboard INFRA extraction — 2026-06-13 (session mesell-ms-dashboard-infra-session-1)

**Context:** Second microservices extraction (MS-2 wave, parallel with MS-C image). Worktree-scoped bg session at `/tmp/mesell-wt/msB-infra` on `feature/microservices-dashboard/infra`. Authored manifests only — NO cluster deploy (cluster API 34.180.58.185:6443 unreachable from bg session; firewall /32-scoped to founder IP, expected). All git handled by the session.

**Template used:** svc-export (MS-A) pilot at `k8s/svc-export/*` + `backend/services/svc-export/Dockerfile` + `docs/runbooks/svc-export-rollback.md`. Copy-and-trim is the right move — dashboard is the LIGHTEST extraction.

**dashboard vs svc-export — the deltas that matter (memorize for MS-C/MS-D):**
- **NO Celery worker** → ONE Deployment (svc-dashboard-api), not two. Dockerfile has NO worker-override path; CMD is the only entrypoint. No CELERY_BROKER_URL/RESULT_BACKEND in the secret.
- **Owns ZERO tables** → I5 is an `audit-grant.sql`, NOT a `schema-role.sql`. NO `CREATE SCHEMA`, NO `ALTER SCHEMA OWNER`, NO table DML grants, NO ALTER DEFAULT PRIVILEGES. ONLY `GRANT USAGE ON SCHEMA public` + `GRANT INSERT ON public.audit_events` (the R3 cross-schema audit grant — needed for IMPORT-SAFETY of vendored audit_mw even though the read-only GET writes no row).
- **NO owned schema** → DATABASE_URL has NO `?options=-csearch_path%3D...` override (default public is correct). Contrast svc-export which pins `export,public`.
- **NO alembic** → Dockerfile copies ONLY requirements.txt + app/ (no alembic/, no alembic.ini). No per-service migration Job.
- **NO GCS (I6 skip)** → no GCS_* env, no GOOGLE_APPLICATION_CREDENTIALS, no gcs-sa.yaml.example. Dashboard touches no storage at all (not merely "keyless" — absent entirely).
- **mem limit 256Mi** (vs svc-export api 512Mi) — no XLSX build buffer. CPU req 50m, lim 200m (same api sizing).

**I4 METHOD-AWARE Traefik routing (the §13-DASHBOARD-D2 path-key collision) — KEY PATTERN:**
- `GET /api/v1/products` and `POST /api/v1/products` (catalog create) share ONE exact path key but are different services. Catalog extracts LAST (MS-5), so during dashboard's window only the GET moves.
- Matcher: `Host(`api.mesell.xyz`) && Method(`GET`) && Path(`/api/v1/products`)`.
  - `Method(GET)` — so the catalog POST is NOT hijacked (falls through to monolith host-Ingress).
  - `Path(...)` EXACT, NOT `PathPrefix` — page/limit are QUERY params not path segments; a PathPrefix would wrongly claim `/api/v1/products/{id}/images*` (MS-C) + `/{id}/export-xlsx` (MS-A). Traefik picks the most-specific rule.
- Parallel-lane discipline confirmed: dashboard (exact `/api/v1/products` + GET) and image (`/api/v1/products/{id}/images*` prefix) are DISJOINT — additive coexisting IngressRoute objects. Reusable rule: when two services collide on a path key, split on `Method()`; when one owns sub-paths, use `PathPrefix`/`PathRegexp`; never PathPrefix a leaf path another service shares.

**Trimmed ConfigMap pattern (I8):** created a DEDICATED `svc-dashboard-config` ConfigMap (APP_ENV + FEATURE_TRACKING_DASHBOARD_ENABLED only) rather than reusing the shared `meesell-config`. Applies the §5.D blast-radius trim to NON-secret config too — extracted pod doesn't inherit GEMINI_MODEL/GCS_*/LANGFUSE_*/other-flags. The shared meesell-config already carries the flag at k8s/config.yaml:64 (=true, monolith). Flag semantics: dev=true / staging=false; 404-on-read kill-switch (router.py:118). dev-only Sub-Plan → no staging overlay authored.

**Offline validation when cluster unreachable:** kubectl `--dry-run=client` STILL contacts the API server (RESTMapper/OpenAPI fetch) — `--validate=false` does NOT avoid it. From a bg session with no cluster route, fall back to a Python PyYAML structural parse + explicit field assertions (28 assertions here, all PASS). Document the cluster-unreachable reason in the report; do NOT treat it as a blocker (deploy is a deploy-window op, not this session's job). Beware grep false-positives on comment lines that DESCRIBE an absence ("NO CREATE SCHEMA") — re-grep anchored `^\s*` for executable statements.

**MS-2 capacity math (the D3 watch — NO trigger for Sub-Plan B):**
Sum of CPU REQUESTS at MS-2 on the e2-standard-2 (2 vCPU = 2000m) node:
- monolith api 2×200m=400m, monolith worker 2×250m=500m
- svc-export api 50m + worker 200m = 250m
- svc-dashboard api 50m (NO worker)
- svc-image api 50m + worker ~250m (rembg est.) = ~300m
≈ **1500m of 2000m requests** → FITS. svc-dashboard is the smallest contributor (50m). NO D3 e2-standard-4 ask for Sub-Plan B. If image's rembg worker req is higher than estimated and the sum approaches the ceiling at the MS-2 strangler window, STOP and flag founder (do NOT silently upgrade). Flagged in report as a watch, not a blocker.

**Files authored (8):** backend/services/svc-dashboard/Dockerfile (I1); k8s/svc-dashboard/{deployment,service,ingressroute,configmap}.yaml + secrets.yaml.example + audit-grant.sql (I2/I3/I4/I8/I7/I5); docs/runbooks/svc-dashboard-rollback.md. I6 skipped (no GCS — noted). I9 = doc-only note (max_connections=200 + PgBouncer already live MS-0 #181/#192; dashboard pool 2-3 conns in backend-lane shared/database.py).

**One new SM secret needed (inter-lead, founder):** `dev-dashboard-db-password` (per-service DB password for dashboard_user; NOT a new IAM grant; within §4 ceiling). Mirrors svc-export's `dev-export-db-password`. Founder creates SM container+version at bootstrap; infra composes into DATABASE_URL.

---
