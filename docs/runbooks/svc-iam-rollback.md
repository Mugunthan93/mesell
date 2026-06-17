# Runbook — `svc-iam` Rollback (Microservices Sub-Plan G)

**Owner:** `meesell-backend-coordinator` (backend lead) + `meesell-infra-builder` (infra steps)
**Feature:** Microservices Sub-Plan G — `iam` module extraction (seventh extraction, §16.H order #7; Wave MS-4, parallel with MS-F category)
**Scope:** reverting the `iam` extraction back to the in-process monolith module.
**Companion docs:** `MASTER_PLAN.md §3.C` (generic strangler rollback), `SUB_PLAN_0G_iam_extraction.md §"Rollback"`, `handoff_msG_infra.md`, `auth-secret-rotation.md` (the dual-pepper grace window — unaffected by this rollback), and the proven `svc-export-rollback.md` / `svc-dashboard-rollback.md` / `svc-pricing-rollback.md` / `customer-svc-rollback.md` patterns this adapts.

> **Apply at DEPLOY / INCIDENT time only.** Nothing here runs during the build/docs session. Every cluster / Traefik / DB / Valkey command is a deploy-window operation, executed by whoever owns the window.

> **KEY DIFFERENCES vs every earlier rollback (iam is structurally unique):**
> - **iam is all-✗ — it has NO callers and NO `/internal/*` shim.** There is NO `core/extracted_clients/` step to revert (contrast export/pricing/customer). Nothing in the codebase calls iam over HTTP — every service validates JWTs LOCALLY via vendored `core/auth.py` + shared `JWT_SECRET` (G1/A2/D7). So tearing down svc-iam affects ONLY login/refresh/logout/me/webhook; **every existing valid access token keeps working for its TTL** with zero iam involvement. This is the Risk #2 mitigation that makes iam the LOWEST-blast-radius critical-path extraction.
> - **The refresh allowlist is in SHARED Valkey DB 0, NOT in the iam pod.** `cache:refresh:v{N}:{hmac}` lives in the shared Valkey instance every service connects to. Moving/deleting svc-iam pods does NOT touch DB 0 — **live refresh sessions survive the rollback unchanged** (no backfill, unlike export's Celery keyspace).
> - **`core/auth.py` is NEVER deleted from the monolith.** It is the vendored source-of-truth every still-monolithic AND every extracted service imports. The rollback does not touch it.
> - **The highest-blast-radius infra constraint is the FE-D5 cookie `Path=/api/v1/auth`.** A Traefik mis-route on rollback that strips/rewrites `/api/v1/auth` would silently break the refresh cookie for every live session. Step 1's verification asserts the cookie Path round-trips after re-pointing.

---

## 0. When to roll back

Rollback is allowed **any time BEFORE Sub-Plan G is declared complete** (the 7-day hybrid-mode green window). Triggers:

- The FE-D5 refresh flow breaks through Traefik against svc-iam — most likely a Traefik path-strip/rewrite that drops the `/api/v1/auth` prefix, so `Set-Cookie: refresh_token=...; Path=/api/v1/auth` no longer matches the request path and the browser stops sending the refresh cookie (SUB_PLAN_0G §0.6 / R2). Symptom: every live user is silently logged out on next refresh.
- `core/auth.py` drift is detected between the svc-iam copy and the monolith/other-service copies (an HS256 `JWT_SECRET` mismatch OR a `{sub, exp, plan}` claim-shape divergence) → iam-issued JWTs fail to validate elsewhere, or vice-versa (R5). The merge-gate `diff` guard pins this, but watch a staging env that injects a different `JWT_SECRET`.
- The dual-pepper allowlist read regresses — a rotation runbook (`auth-secret-rotation.md §2`) grace window stops accepting `vN-1` keys, mass-logging-out users mid-rotation.
- OTP send/verify breaks — MSG91 dev-IP whitelist not applied to the svc-iam egress IP, or the trimmed Settings dropped an `MSG91_*` / `RAZORPAY_*` field (flag-parity class — the LEAD `test_flag_parity_every_settings_read_resolves` pins this, but watch staging-env defaults).
- The cross-schema FK drop caused a data-integrity surprise (Risk #5) — the Risk#5 pre-scan aborts on orphans before any drop, but a post-extraction forensic orphan-scan finds a dangling `<table>.user_id`.
- The `users` schema-move migration mis-fires on dev (head divergence dev↔staging is a P0 — STOP and escalate, do NOT roll staging forward to match dev).
- MS-4 wave overflows the current node (capacity — STOP and flag to founder; do NOT silently upgrade the VM per D3). iam is a light contributor (api-only, NO Celery, NO XLSX/rembg, small footprint, 2-replica min + HPA burst).
- Any P0 where reverting to the known-good in-process path is faster than fixing forward.

---

## 1. The rollback steps (in order)

### Step 1 — Traffic: re-point Traefik back to the monolith (FE-D5 cookie-path aware)
Route `/api/v1/auth/*` + `/api/v1/webhooks/razorpay` back to the monolith. The monolith still has the in-process `iam_router` mounted at `main.py:114` (it is NOT removed until cutover; both modes coexist during the strangler window), so traffic serves immediately.

```bash
# Delete the svc-iam IngressRoute so the host-only api Ingress
# (api.mesell.xyz → api:80, the monolith) reclaims /api/v1/auth/* + the webhook.
kubectl -n dev delete ingressroute svc-iam
kubectl -n dev get ingressroute -o wide
```

**PATH-AWARE NOTE (the FE-D5 invariant):** the svc-iam IngressRoute matched two iam-owned prefixes —
`Host(\`api.mesell.xyz\`) && PathPrefix(\`/api/v1/auth\`)` and `... && PathPrefix(\`/api/v1/webhooks/razorpay\`)` —
with **NO strip/rewrite middleware** (so the `/api/v1/auth` prefix reached svc-iam verbatim and the
`Set-Cookie ...; Path=/api/v1/auth` scoping held). After deleting it, the monolith api Ingress reclaims
those prefixes; the monolith's in-process router ALSO sets the cookie with `Path=/api/v1/auth`, so the
cookie scoping is identical on both paths. **Verify the cookie Path round-trips** (Step "verification" below)
before declaring the rollback done — a refresh that silently fails to send the cookie is the R2 failure mode.

> **TLS NOTE:** svc-iam's IngressRoute correctly references the LIVE secret `api-tls` (verified against the
> live cluster 2026-06-13 — the MS-D cross-wave finding is heeded here). No TLS change is needed on rollback;
> the monolith api Ingress already uses `api-tls`.

### Step 2 — Shims: NO-OP (iam has no callers, no `/internal/*`)
**iam is all-✗ (SUB_PLAN_0G §0.4).** There is no `core/extracted_clients/iam_client.py` anywhere — no service ever called iam over HTTP; every service validates JWTs locally. There is nothing to re-export. This step, which is real work for export/pricing/customer, is a **no-op for iam**. (Recorded explicitly so its absence reads as intentional, not an omission.)

### Step 3 — Database: move `users` back to `public` + RESTORE the dropped cross-schema FKs
The svc-iam migration `b1c2d3e4f5a6` did `ALTER TABLE public.users SET SCHEMA iam` and dropped the residual cross-schema FKs to `users.id` (the live `pg_constraint` cross-check set — up to the §0.7 six: `audit_events`, `seller_profile`, `catalogs`, `products`, `exports`, `product_drafts`). The tested downgrade reverses BOTH.

```bash
# Run the svc-iam alembic downgrade (moves iam.users → public.users + restores
# each cross-schema FK it dropped, guarded by an IF-NOT-EXISTS / DO$$ block).
cd backend/services/svc-iam
DATABASE_URL='postgresql+asyncpg://<superuser>@<host>:5432/<db>' \
  alembic downgrade -1
```

```sql
-- Verify the reversal:
SELECT relnamespace::regnamespace AS schema FROM pg_class WHERE relname = 'users';   -- expect: public
SELECT conname, conrelid::regclass FROM pg_constraint WHERE confrelid = 'public.users'::regclass;
-- expect the restored cross-schema FKs to users.id to be present again.
```

> **Risk #5 caution:** the downgrade RESTORES FKs. If any `<table>.user_id` row was orphaned WHILE the FK
> was absent (i.e. a `users` row was deleted during the strangler window with the FK dropped), the
> `ADD CONSTRAINT` will fail. Run the same orphan pre-scan the upgrade ran, in reverse, BEFORE the
> downgrade's `ADD CONSTRAINT`, and clean any orphan first. (In practice the monolith's app-layer
> `assert_owned`/`scope_to_user` defence + RESTRICT/CASCADE ondelete made orphaning unlikely.)

### Step 4 — Valkey: LEAVE THE ALLOWLIST UNTOUCHED
The refresh allowlist `cache:refresh:v{N}:{hmac}` lives in **shared Valkey DB 0**, which svc-iam and the monolith both connect to. **Do NOT flush it.** The monolith's in-process iam reads/writes the SAME keys with the SAME `core/auth.py` derivation (byte-identical) + the same `REFRESH_TOKEN_PEPPER` — so every live session continues seamlessly after Step 1 re-points traffic. There is no backfill and no DB-0 step. (Contrast export, whose Celery keyspace needed care — iam's state is fully shared and survives.)

### Step 5 — Tear down the svc-iam deployment
```bash
kubectl -n dev delete deployment svc-iam-api          # api only (2-replica; NO worker — iam has no Celery)
kubectl -n dev delete hpa svc-iam-api                  # the HPA burst (Risk #2)
kubectl -n dev delete service svc-iam                  # ClusterIP iam-svc:8001
kubectl -n dev delete configmap svc-iam-config         # trimmed APP_ENV/CORS/flag ConfigMap
kubectl -n dev delete secret svc-iam-secrets           # trimmed secret (incl. dev-iam-db-password, MSG91/RAZORPAY/peppers)
kubectl -n dev delete ingressroute svc-iam             # if not already removed in Step 1
# Postgres role/grant (iam_user + GRANT INSERT public.audit_events) may stay — harmless
# (a service that no longer exists simply stops connecting). Drop only for hygiene AFTER
# Step 3 confirms users is back in public:
#   DROP ROLE IF EXISTS iam_user;
```

### Step 6 — Re-run hybrid CI in pure in-process mode + log root cause
Run the monolith iam tests to confirm the in-process auth path is green, then record the incident in the Rollback Log below.

```bash
cd backend && PYTHONPATH=. python -m pytest tests/modules/iam tests/integration/test_iam_* -q
# (the monolith iam suite — OTP send/verify, refresh rotation, logout, /me, razorpay
#  webhook, all in-process against the public.users table + shared Valkey DB 0)
```

---

## 2. Post-rollback verification checklist

- [ ] `/api/v1/auth/*` + `/api/v1/webhooks/razorpay` serve from the monolith (Traefik no longer has a svc-iam rule; the host-only api Ingress reclaims them).
- [ ] **FE-D5 cookie Path round-trips:** a live `POST /api/v1/auth/refresh` against the monolith path sets `Set-Cookie: refresh_token=...; Domain=.mesell.xyz; Path=/api/v1/auth; Secure; HttpOnly; SameSite=Strict` and the browser sends it back on the next refresh (no silent logout — the R2 failure mode is absent).
- [ ] An access JWT issued before the rollback still validates (it validates LOCALLY everywhere — the rollback does not touch `core/auth.py` or `JWT_SECRET`).
- [ ] `users` is back in schema `public`; the dropped cross-schema FKs to `users.id` are RESTORED; zero orphans.
- [ ] The refresh allowlist in shared Valkey DB 0 is UNTOUCHED; live sessions survive.
- [ ] `public.audit_events` rows written by svc-iam during the window STAY (append-only, cross-schema — nothing to reverse).
- [ ] Monolith iam test suite green (in-process mode).
- [ ] No `svc-iam` pods/services/HPA/configmaps/secrets/ingressroutes remain in `dev`.
- [ ] Root cause recorded in the Rollback Log.

---

## 3. Rollback Log

> Append one entry per rollback. Keep newest at the top.

| Date | Trigger | Steps run | Root cause | Re-attempt plan |
|---|---|---|---|---|
| _(none yet — Sub-Plan G authored 2026-06-12, executed 2026-06-14; no rollback has occurred)_ | | | | |
