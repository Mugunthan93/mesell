# Founder Action Checklist — Microservices Migration Close-Out

> **Scope:** the MS-PAR-1 microservices extraction program (8 services, A–H). This is
> the single canonical list of what the founder still needs to do. Every item below
> was verified against the source files (service secret templates, the 8 founder-gate
> PR bodies, `BACKEND_ARCHITECTURE.md`, the §5.G compliance audit, and the infra
> memories) — not drafted from memory.

| Field | Value |
|---|---|
| **Program** | MS-PAR-1 — modular monolith → 8 microservices (strangler-fig) |
| **Status** | **PROGRAM COMPLETE** — all 8 services (A–H) extracted and merged to `develop` (founder-ratified 2026-06-14) |
| **Audit** | `docs/plans/microservices_migration/PROGRAM_COMPLIANCE_AUDIT_5G.md` — §5.G verdict **PROGRAM-COMPLETE-READY → ratified** |
| **`develop` tip** | `3992478` (at time of writing) |
| **Strangler posture** | **INTACT** — `backend/app/main.py` still mounts all 8 monolith routers; **ZERO cutover taken**. No live traffic routes to any `svc-*` yet. |
| **Nothing below blocks the merged code** | The 8 services are merged and green. The items below block a *dev deploy* of the services and capture *governance* + a *future cutover* phase — they are NOT a code gate. |

---

## Legend

- `[x]` = DONE (no action) · `[ ]` = OPEN (founder action)
- **🔴 BLOCKING (dev deploy)** — required before the 8 services can run in `dev`
- **🟡 GOVERNANCE** — not deploy-blocking; needed to close the paper trail
- **⚪ FUTURE (cutover)** — a separate future founder gate; explicitly NOT now

---

## 0. Already done — no action

- [x] **All 8 founder-gate PRs merged to `develop`** (D1 — the founder's gate, not the lead's):
  `#191` export · `#198` dashboard · `#207` image · `#216` pricing · `#211` customer · `#220` iam · `#221` category · `#223` catalog.
  *Why: each `feature/microservices-<svc>/integration → develop` gate is the founder's per Decision D1. The final three (#220 → #221 → #223) merged 2026-06-14, develop tip `5f8e2e1` at the time.*
- [x] **`MASTER_PLAN` PROGRAM COMPLETE stamp applied** (T2, founder-ratified) — `docs/plans/microservices_migration/MASTER_PLAN.md` Revision History v1.8.
- [x] **§5.G post-extraction compliance audit PASS** — all 8 audit areas PASS (strangler intact · Model-C governance · schema-split · shim freezes compose · shared invariants · secrets discipline · merge-order coherent · D3 footprint recorded).
- [x] **`develop` CI green + deploy hardened** — `#227` wrapped the IAP-SSH deploy in a 3-attempt retry (OS-Login key-propagation flake).

> One non-blocking observation recorded in the audit (no action required):
> `svc-category` vendored the FULL `core/auth.py` rather than the trimmed verify-core.
> The JWT local-validation path is still correct and shared-secret-validated — flagged
> only for a future consolidation-hygiene pass.

---

## 1. 🔴 BLOCKING (dev deploy) — Secret Manager populations

> **Why this blocks:** every `svc-*` Deployment consumes its secrets via
> `envFrom: secretRef`. The K8s Secrets are populated from GCP Secret Manager
> (project `project-1f5cbf72-2820-4cdb-949`). The per-service DB passwords below are
> **founder-to-create bootstrap items** — none are auto-provisioned. None of these
> block the *merged code*; they block *running the services in dev*.
>
> **Verified against** each service's `k8s/svc-<svc>/secrets.yaml.example` on
> `develop`. The per-service secret sets are deliberately minimal (the §5.D
> blast-radius trim): non-AI services carry only `DATABASE_URL` + `VALKEY_URL` +
> `JWT_SECRET`; only iam carries OTP/payment/pepper material.

### 1.A — Per-service DB passwords (8 new SM secrets, one per service)

Each service's role (`<svc>_user`) gets its password from a dedicated SM secret. The
SAME value is used in the `ALTER ROLE <svc>_user WITH PASSWORD` (schema bootstrap) and
composed into that service's `DATABASE_URL`. These are per-service DB passwords, NOT new
IAM grants (within the §4 one-SA ceiling).

- [ ] **🔴 `dev-export-db-password`** → `export_user` (svc-export)
- [ ] **🔴 `dev-dashboard-db-password`** → `dashboard_user` (svc-dashboard; read-only role via audit-grant.sql — owns no tables but still needs its login password)
- [ ] **🔴 `dev-image-db-password`** → `image_user` (svc-image)
- [ ] **🔴 `dev-pricing-db-password`** → `pricing_user` (svc-pricing)
- [ ] **🔴 `dev-customer-db-password`** → `customer_user` (svc-customer)
- [ ] **🔴 `dev-iam-db-password`** → `iam_user` (svc-iam)
- [ ] **🔴 `dev-category-db-password`** → `category_user` (svc-category)
- [ ] **🔴 `dev-catalog-db-password`** → `catalog_user` (svc-catalog)

Create-and-populate (per secret):
```bash
gcloud secrets create dev-<svc>-db-password --project=project-1f5cbf72-2820-4cdb-949 --replication-policy=automatic   # once
printf '%s' '<PASSWORD>' | gcloud secrets versions add dev-<svc>-db-password --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
```
> Use the SAME value in the matching `ALTER ROLE <svc>_user WITH PASSWORD`. URL-encode
> any `+ / @` in the password with `urllib.parse.quote(pw, safe='')` when composing
> `DATABASE_URL` (base64 passwords otherwise break URL parsing).

### 1.B — Shared `JWT_SECRET` (ONE value, all 8 services)

- [ ] **🔴 `JWT_SECRET`** — the SAME SM `jwt-secret` value is injected into all 8 services.
  *Why: iam-svc signs the access JWT (HS256); every other service validates it **LOCALLY** with the same secret + vendored verify-core — there is NO callback to iam (Risk #5 / D7 invariant). A mismatched value would 401 every authenticated cross-service request.*
  > SM `jwt-secret` already LIVE (version 1). Action is to bind the same value into each service's Secret at deploy.

### 1.C — AI services (image, category, catalog) — Gemini + LangFuse

- [ ] **🔴 `GEMINI_API_KEY`** → image, category, catalog *(SM `gemini-api-key` already LIVE)*
- [ ] **🔴 `LANGFUSE_SECRET_KEY`** → image, category, catalog *(SM `langfuse-secret-key` already LIVE)*
- [ ] **🔴 `LANGFUSE_PUBLIC_KEY`** → image, category, catalog
  *Why: the AI services vendor `ai_ops/`; the shared `ai:*` budget brake (global ₹500/day cap) and LangFuse tracing both need these. `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_HOST` are non-secret and live in each AI service's ConfigMap (`meesell-config`-sourced), not the Secret.*
  > iam, customer, dashboard, pricing, export are **NOT** AI services and must NOT receive `GEMINI_API_KEY` / `LANGFUSE_*` (blast-radius trim). export does, however, carry `GCS_BUCKET` + `GCS_PROJECT_ID` (it writes the XLSX to GCS); image carries Celery broker/result for rembg.

### 1.D — iam-svc only (the auth + payment authority — most secret-rich service)

iam-svc owns OTP/login/refresh + the Razorpay webhook + the refresh allowlist. Its
Secret (`iam-svc-secrets`) is the largest of any service. Bind:

- [ ] **🔴 `REFRESH_TOKEN_PEPPER`** *(SM `refresh-token-pepper`, LIVE)* — HMAC key for the FE-D5 refresh allowlist keyspace
- [ ] **🔴 `REFRESH_TOKEN_PEPPER_PREVIOUS`** *(SM `refresh-token-pepper`; equals current value if no rotation in flight)* — read-fallback during a dual-pepper grace window
- [ ] **🔴 `MSG91_AUTH_KEY`** *(SM `msg91-auth-key`, LIVE)* — OTP send
- [ ] **🔴 `MSG91_TEMPLATE_ID`** *(SM `msg91-template-id`, LIVE)* — OTP template
- [ ] **🔴 `RAZORPAY_KEY_ID`** *(SM `razorpay-key-id`, LIVE — TEST key in dev)*
- [ ] **🔴 `RAZORPAY_KEY_SECRET`** *(SM `razorpay-key-secret`, LIVE — TEST secret in dev)*
- [ ] **🔴 `RAZORPAY_WEBHOOK_SECRET`** *(SM `razorpay-webhook-secret`, LIVE)* — HMAC verify on `POST /api/v1/webhooks/razorpay`
- [ ] **🔴 `AUDIT_PII_SALT`** *(SM `audit-pii-salt`, LIVE)* — PII hashing for the §7.I direct-ORM audit writes

> `REFRESH_TOKEN_PEPPER_VERSION` + `JWT_ALGORITHM` + the FE-D5 TTLs + CORS are
> **non-secret** and live in `iam-svc-config` (ConfigMap), NOT the Secret.
> iam-svc deliberately carries **NO** `GEMINI_API_KEY`, **NO** `LANGFUSE_*`, **NO**
> `GCS_*`, **NO** Celery — it is auth/payment only.

---

## 2. 🔴 BLOCKING (dev deploy) — MSG91 dev-server-IP whitelist

- [ ] **🔴 Whitelist the dev server's egress IP in the MSG91 dashboard before the first OTP send.**
  *Why: MSG91 enforces its own IP allowlist independent of GCP. If the dev server's IP is not whitelisted, every `POST /api/v1/auth/otp/send` from iam-svc fails — even with a valid `MSG91_AUTH_KEY`. (MSG91 service name: `DEVOTP`.)*
  > Operational note: the founder's laptop IP rotates frequently and is tracked separately for the K3s firewall; the value to whitelist here is the **dev server's** outbound IP, not the laptop's.

---

## 3. 🔴 BLOCKING (dev deploy) — D3 VM spend (fresh founder approval)

- [ ] **🔴 Approve the `e2-standard-4` upgrade (~₹2,600/mo) before the 8-service node deploy.**
  *Why: D3 (the VM upgrade) is **plan-pre-approved only** — the actual spend gets an **explicit fresh founder ask at the moment services outgrow the node**, never on the plan pre-approval alone (`MASTER_PLAN §3.A.1`, master-session standing rule). It is **NOT auto-provisioned.***
  > **Capacity math:** the current dev node is `e2-standard-2` (2 vCPU = ~2000m allocatable). The svc-image (MS-2) projection already put the fan-out at **~2525m > 2000m** — i.e. monolith remnant + the 8 services overflow the current node. catalog is the single largest contributor (2 × 150m = 300m). The upgrade is therefore expected at deploy; it requires an explicit go-ahead, not silent provisioning.

---

## 4. 🟡 GOVERNANCE (not deploy-blocking) — approve the 8 LOCKED §7.3 amendments

> **Why:** each extraction carried an `Extracted to svc-<x> (V1.5)` note against a
> **LOCKED** section of `BACKEND_ARCHITECTURE.md`. Per §7.3, a LOCKED section is never
> self-amended by the lead — the note was carried to each founder-gate PR and awaits
> founder approval to land. **Verified §-numbers against `BACKEND_ARCHITECTURE.md` on
> `develop`** (module → section is canonical): these notes are **not yet applied** on
> `develop`.

- [ ] **🟡 §7 (iam)** — "Extracted to svc-iam V1.5" (FE-D5 cookie path `/api/v1/auth`, refresh allowlist) · PR #220
- [ ] **🟡 §8.B (customer)** — "Extracted to customer-svc V1.5" · PR #211
- [ ] **🟡 §9 / §9.D (category)** — "Extracted to svc-category V1.5" (GLOBAL module, no `scope_to_user`) · PR #221
- [ ] **🟡 §10 (catalog)** — "Extracted to svc-catalog V1.5" (4 inbound + 2 outbound shims) · PR #223
- [ ] **🟡 §11 (image)** — "Extracted to svc-image V1.5" · PR #207
- [ ] **🟡 §12 (pricing)** — "Extracted to svc-pricing V1.5" · PR #216
- [ ] **🟡 §13 (dashboard)** — "Extracted to svc-dashboard V1.5" · PR #198
- [ ] **🟡 §14 (export)** — "Extracted to svc-export V1.5" · PR #191

---

## 5. ⚪ FUTURE (cutover) — a separate founder gate, NOT now

> The migration program is COMPLETE but the strangler is **INTACT**: today's deploy
> rolls the **monolith only**, which still serves all 8 surfaces. Wiring the `svc-*`
> services into live traffic is a deliberate future phase, gated separately per service.

- [ ] **⚪ Wire `k8s/svc-*/` into the deploy** — today the deploy pipeline rolls the monolith image only; the per-service manifests exist but are not in the live roll-out.
- [ ] **⚪ Run the per-service schema-split migrations** (currently dormant: each owns a `<svc>` schema; `SET SCHEMA` migrations move tables off `public` with tested downgrades; iam first — it owns the `users` move and the cross-schema FK).
- [ ] **⚪ Per-service strangler-delete** — only after ≥7 days of hybrid-green per service, delete the monolith copy of that module. **`core/auth.py` stays** (it is the vendored verify-core, not strangler debt).
- [ ] **⚪ Traefik cutover** — flip the per-service IngressRoute to route live traffic to each `svc-*`, then retire the monolith route. One founder gate per service.
  > Cross-wave fix to land before any image/export cutover: the sibling `svc-image` / `svc-export` IngressRoutes referenced a nonexistent TLS secret `api-mesell-xyz-tls`; the live secret is `api-tls` (svc-catalog's method-split IngressRoute already uses `api-tls` correctly).

---

## 6. ⚪ DEFERRED to V1.5 (no action now)

- [ ] **⚪ JWT dual-secret grace window** — a parallel to the dual-pepper rotation, letting `JWT_SECRET` rotate without a synchronized all-pod restart. NOT a V1 blocker — dev rotates by restarting all pods within the access-token TTL window. Backend (auth-builder) owns the dual-secret read-path code if V1.5 needs it.

---

## Quick status roll-up

| # | Item | Class | Status |
|---|---|---|---|
| 0 | 8 gates merged · PROGRAM COMPLETE · §5.G PASS · CI green | — | **DONE** |
| 1 | SM populations (8 db-passwords + shared JWT_SECRET + AI keys + iam set) | 🔴 deploy-blocking | OPEN |
| 2 | MSG91 dev-server-IP whitelist | 🔴 deploy-blocking | OPEN |
| 3 | D3 `e2-standard-4` fresh spend-ask (~₹2,600/mo) | 🔴 deploy-blocking | OPEN |
| 4 | 8 LOCKED §7.3 `BACKEND_ARCHITECTURE.md` amendments | 🟡 governance | OPEN |
| 5 | Cutover (wire manifests · schema-split · strangler-delete · Traefik) | ⚪ future gate | NOT NOW |
| 6 | JWT dual-secret grace window | ⚪ V1.5 | DEFERRED |

---

*Authored by `meesell-backend-coordinator` (`mesell-founder-checklist-1`). Docs-only.
Every secret name, §-number, PR number, and the D3 figures were verified against the
service secret templates, the founder-gate PR bodies, `BACKEND_ARCHITECTURE.md`, the
§5.G compliance audit, and the infra memories — not the master's from-memory draft.*
