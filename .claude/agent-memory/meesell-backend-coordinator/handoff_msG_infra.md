# HANDOFF → meesell-infra-builder — Sub-Plan G (`iam` extraction) INFRA work-package

**From:** meesell-backend-coordinator (session `mesell-ms-iam-session-1`, 2026-06-12)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**Trigger:** PHASE 1 (this spec) authored now. PHASE 2 (infra execution) GATED on **Wave MS-3 complete** (both D pricing + E customer founder gates merged). Parallel partner: MS-F (category).

---

## 0. Scope of this handoff

The svc-iam extraction's INFRA surfaces. Backend specialists own `backend/services/svc-iam/app/**`
code; **infra lead owns everything below**, committed on `feature/microservices-iam/infra` (cut from
`feature/microservices-iam/integration`), reviewed by the infra lead, merged into integration
alongside the backend group PR.

**CUT POINT:** cut the integration branch from `origin/develop` (live tip at Phase-2 dispatch —
re-verify `git ls-remote origin develop`; MS-2/MS-3 will have moved develop forward).

**⚠️ HIGHEST-BLAST-RADIUS CONSTRAINT IN THE WHOLE MIGRATION:** the Traefik route for iam-svc MUST
preserve the cookie path `/api/v1/auth` EXACTLY — see I4. A path strip/rewrite silently breaks every
live frontend session's refresh cookie. Read I4 first.

---

## 1. Infra deliverables (all dev-namespace, current hardware)

| # | Surface | Spec | Source authority |
|---|---|---|---|
| I1 | `backend/services/svc-iam/Dockerfile` | FROM python:3.12-slim; install svc-iam `requirements.txt` (fastapi, sqlalchemy, asyncpg, pydantic, redis, pyjwt, httpx — **NO gemini/langfuse/gcs/celery**). **Single api process** (iam has NO Celery worker — unlike export/image). | infra plan §6 |
| I2 | `k8s/svc-iam/deployment.yaml` | **api 2 replicas MINIMUM** (Risk #2 — iam is the auth authority; a single replica is a SPOF for login/refresh). req **50m CPU / 128Mi**, lim 200m/512Mi (api-light, no XLSX/rembg/AI). **HPA: 4-replica burst** on OTP-send traffic spikes (per MASTER_PLAN §6 Risk #2 mitigation). NO worker deployment. | MASTER_PLAN §6 Risk #2; infra plan §6.3 |
| I3 | `k8s/svc-iam/service.yaml` | ClusterIP `iam-svc:8001`. | infra plan §6 |
| I4 | **Traefik IngressRoute — PATH-PRESERVING** | Route `/api/v1/auth/*` (covers otp/send, otp/verify, refresh, logout, me) AND `/api/v1/webhooks/razorpay` → `iam-svc:8001`. **CRITICAL: NO path-strip, NO path-rewrite of the `/api/v1/auth` prefix.** The FE-D5 refresh cookie is scoped `Set-Cookie: ...; Path=/api/v1/auth` (router.py:64). If Traefik strips or rewrites `/api/v1/auth`, the browser stops sending the refresh cookie on `/refresh`/`/logout` and EVERY live session silently fails. Use a `PathPrefix` matcher with NO `StripPrefix` middleware on this route. `/internal/*` NOT exposed (iam has NONE — §0.4). | MASTER_PLAN §2.C, D4, §5.A; SUB_PLAN_0G §0.6 |
| I5 | Postgres schema + role | `CREATE SCHEMA iam; GRANT USAGE ON SCHEMA iam TO iam_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA iam TO iam_user;` PLUS **`GRANT INSERT ON public.audit_events TO iam_user`** (cross-schema audit write — iam's §7.I direct-ORM audit path writes auth.login.success / auth.token.refreshed / auth.logout rows to public.audit_events). The schema-MOVE migration (`public.users → iam.users`) + the 6-cross-schema-FK DROP is BACKEND (database-builder), NOT infra — infra only creates the schema + role + grants. | MASTER_PLAN §2.D / §5.B; SUB_PLAN_0G §0.7 |
| I6 | Secret injection | svc-iam pod needs: `DATABASE_URL` (@schema iam), `VALKEY_URL`, **`JWT_SECRET` + `JWT_ALGORITHM`** (shared HS256 — iam OWNS issuance; every other service vendors the SAME secret for LOCAL verification per A2/D7), **`REFRESH_TOKEN_PEPPER` + `REFRESH_TOKEN_PEPPER_PREVIOUS` + `REFRESH_TOKEN_PEPPER_VERSION`** (dual-pepper, R5/PR #66), **`MSG91_*`** (OTP send), **`RAZORPAY_*` incl. `RAZORPAY_WEBHOOK_SECRET`** (webhook HMAC verify), `AUDIT_PII_SALT`, `CORS_ALLOWED_ORIGINS` + `CORS_ALLOW_CREDENTIALS`, `APP_ENV`. **NOT** GEMINI/LANGFUSE/GCS (iam has no AI/storage). | SUB_PLAN_0G §Code-surfaces; MASTER_PLAN §5.D |
| I7 | GCS service account | **NONE.** iam touches no object storage (no image/export). Do NOT provision a GCS SA for iam-svc. | SUB_PLAN_0G §Code-surfaces |
| I8 | Valkey DB 0 — SHARED, no migration | The refresh allowlist (`cache:refresh:v{N}:{hmac}`) + OTP keys (`otp:{phone}`) live in the SHARED Valkey DB 0. iam-svc connects to the SAME Valkey instance. **NO key-backfill needed** (unlike export's Celery keyspace) — moving iam pods does not touch DB 0 state; live sessions survive the cutover. Per-service Valkey key NAMESPACING (`{svc}:` prefix, §2.E) does NOT apply to the FE-D5 allowlist/OTP keys — those keyspaces are LOCKED-VERBATIM (the frontend + the dual-pepper rotation runbook depend on the exact `cache:refresh:v{N}:` / `otp:` shapes). Preserve them unprefixed. | MASTER_PLAN §2.E, §5.C; SUB_PLAN_0G §0.6, R4 |

---

## 2. Secret-ownership note (JWT_SECRET rotation — A2/D7)

Per MASTER_PLAN §5.A: **iam-svc OWNS the `JWT_SECRET` rotation.** Other services discover the new
secret via Kubernetes secret reload (V1.5 — pod restart) or hot-reload from Secret Manager (V2).
Because verification is LOCAL in every service (no callback to iam), a secret rotation MUST be a
coordinated roll: rotate the Secret Manager value → restart iam-svc → restart every other service
within the access-token TTL window, OR run a dual-secret grace window analogous to the dual-pepper
pattern. The dual-pepper grace window (`docs/runbooks/auth-secret-rotation.md` §2, landed PR #46)
covers the REFRESH pepper; the JWT_SECRET rotation is a SEPARATE concern — flag whether a parallel
dual-JWT-secret grace window is needed for V1.5-prod (it is NOT a V1 blocker; dev rotates by
restarting all pods). Infra owns the rotation runbook section; backend (auth-builder) owns any
dual-secret read-path code if V1.5 needs it.

---

## 3. Hardware / VM — D3 checkpoint for Wave MS-4

- svc-iam is SMALL (api-only, 2×50m/128Mi, no Celery worker, no AI, no XLSX/rembg). On its own it
  fits the current node easily.
- **BUT Wave MS-4 deploys iam-svc AND category-svc (MS-F, parallel) simultaneously, on top of the
  already-extracted A–E services + the still-monolithic catalog remnant.** category-svc is the HEAVY
  cache consumer (full-tree pre-warm + top-100 schemas + single-flight on 291 brand-pattern enums) —
  it is the likely node-capacity tipping point, NOT iam.
- **D3 (VM e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** The spend gets an EXPLICIT FRESH
  FOUNDER ASK at the moment the MS-4 deploy doesn't fit the current node (master-session standing rule,
  MASTER_PLAN §3.A.1 + MS-PAR-1 D3 checkpoint). If the infra capacity math shows iam-svc + category-svc
  + monolith remnant overflows the node, STOP and flag to founder — do NOT silently upgrade. Sub-Plan G
  commits NO money on its own.

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests in Sub-Plan G.
- NO terraform beyond the infra plan's dev-scope. Anything bigger (new node pool, IAM beyond the iam_user role + the Secret Manager bindings) → flag to founder.
- `/internal/*` — N/A (iam exposes none). No NetworkPolicy concern for iam internal routes (there are none).
- Infra branch = `feature/microservices-iam/infra`, infra-lead-reviewed, squash into integration. Founder gates integration→develop (NOT me, NOT infra lead).
- Shared-file discipline with MS-F (category): k8s/Traefik edits are NEW svc-iam manifests (not edits to category's); integration merges develop pre-gate; union keep-both.

---

## 5. What I (backend lead) need back from infra (acceptance items the backend merge gate depends on)
- **I4 confirmed (THE critical one):** the Traefik route for `/api/v1/auth/*` does NOT strip/rewrite the prefix — a live `POST /api/v1/auth/otp/verify` → `POST /api/v1/auth/refresh` round-trip through Traefik preserves the `Set-Cookie: ...; Path=/api/v1/auth` scoping and the browser re-sends the cookie on `/refresh`. (The acceptance gate asserts this end-to-end.)
- **I5 confirmed:** `iam_user` has `INSERT ON public.audit_events` (else iam's §7.I auth.login.success / auth.token.refreshed audit writes fail).
- **I6 confirmed:** `JWT_SECRET` is the SAME value injected into iam-svc AND every other service (so an iam-issued JWT validates LOCALLY elsewhere — the Risk #5 / G1 invariant; the integration test asserts cross-service local validation).
- **I2 confirmed deployed at 2-replica minimum + HPA burst** (Risk #2 — no SPOF on the auth authority).

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I open the Inter-lead request row on my board at Phase-1 close (today).
