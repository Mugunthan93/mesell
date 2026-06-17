# Runbook — Secret Manager Bootstrap for the 8-Service Deploy

> **Command reference. Founder runs this manually.** Nothing here is executed by an
> agent. This runbook creates the GCP Secret Manager (SM) secrets and explains how
> they reach each `svc-*` pod **before** the 8-service `dev` deploy.
>
> | Field | Value |
> |---|---|
> | **Owner** | `meesell-infra-builder` (authored) → **founder runs** |
> | **GCP project** | `project-1f5cbf72-2820-4cdb-949` (numeric `888244156264`) |
> | **GCP account** | `vaishnaviramoorthy@gmail.com` |
> | **Region** | `asia-south1` (SM uses `automatic` replication — see §1) |
> | **Namespace** | `dev` only (V1; `staging` Day-7+, `prod` deferred to V1.5) |
> | **Playbook authority** | `docs/INFRASTRUCTURE_PLAYBOOK.md` §10 (Secret Management Discipline) |
> | **Verified against** | `docs/FOUNDER_ACTION_CHECKLIST.md` §1 + each `k8s/svc-<svc>/{secrets.yaml.example,configmap.yaml}` on `develop` `61d9137` |
>
> ## ⛔ This runbook deploys nothing
>
> Creating the SM secrets is necessary but **not sufficient** to run the services.
> The 8-service `dev` rollout is still gated on:
> 1. The **D3 VM spend decision** (`e2-standard-4`, ~₹2,600/mo) — checklist §3. The
>    projected MS-2 fan-out (~2525m) overflows the current `e2-standard-2` node
>    (~2000m allocatable). **Do not deploy the 8 services until this is approved.**
> 2. The **MSG91 dev-server-IP whitelist** — checklist §2 (blocks the first OTP send).
> 3. Wiring `k8s/svc-*/` into the deploy — checklist §5 (a separate future cutover gate;
>    today the pipeline rolls the monolith only, strangler INTACT).
>
> SM secret creation is **₹0** and **safe** (no compute, no traffic). It just removes the
> §1.A "BLOCKING (dev deploy)" items from the founder checklist ahead of the D3 decision.

---

## 0. How a secret reaches a pod (read this first)

The SM→k8s flow this project uses (per playbook §10 + `k8s/secrets.yaml.example` header):

```
GCP Secret Manager          K8s Secret (dev ns)              Pod
(authoritative value)  -->  svc-<svc>-secrets          -->  envFrom: secretRef
gcloud secrets ...          kubectl create secret ...        (deployment.yaml)
                            from `gcloud secrets versions
                            access latest`
```

- **Authoritative source of every value is GCP Secret Manager.** Never inline a value in
  committed YAML (playbook §0, §10). The `k8s/svc-<svc>/secrets.yaml.example` files are
  TEMPLATES with `REPLACE-ME` placeholders — they are NOT applied directly.
- **The SM→k8s sync is MANUAL bootstrap** for V1: the founder reads each value from SM
  with `gcloud secrets versions access latest` and pipes it into a `kubectl create secret`
  (the exact pattern the live `backend-secrets` Secret was built with — see infra MEMORY
  "Phase D DEPLOYED" and the `k8s/secrets.yaml.example` header). **external-secrets-operator
  is deferred to V1.5** — there is no operator auto-syncing SM→k8s today.
- **Each `svc-*` Deployment consumes its Secret via `envFrom: secretRef: { name: svc-<svc>-secrets }`**
  (verified in each `deployment.yaml`). So the K8s Secret keys must match the env var
  names the service's Pydantic Settings expect — they do (this runbook's names are taken
  verbatim from each `secrets.yaml.example`).
- **ConfigMap vs Secret:** non-secret config (`APP_ENV`, feature flags, `JWT_ALGORITHM`,
  TTLs, CORS, `CACHE_VERSION`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`) lives in a ConfigMap
  (`svc-<svc>-config` / `iam-svc-config` / `customer-svc-config`), NOT in SM. SM holds
  ONLY the genuinely-secret values. `LANGFUSE_PUBLIC_KEY` is **NOT a secret** — it is
  ConfigMap material (founder checklist §1.C correction). Only `LANGFUSE_SECRET_KEY` is a
  secret.
- **URL-encoding gotcha (composing `DATABASE_URL`/`VALKEY_URL`):** base64 / random
  passwords can contain `+ / @`, which break URL parsing. URL-encode the password segment
  with `urllib.parse.quote(pw, safe='')` when composing any connection URL (infra MEMORY
  Phase-D lesson). The `DATABASE_URL` for each service also carries its schema search_path
  (`?options=-csearch_path%3D<svc>,public`) per the schema-split — copy it verbatim from
  the service's `secrets.yaml.example`.

### Conventions used below

- **SM replication policy:** `--replication-policy=automatic`. This matches the
  established project convention (founder checklist §1.A and the prior bootstrap of
  `dev-export-db-password` / `refresh-token-pepper` etc.). `automatic` is Google-managed
  multi-region; the `--locations=asia-south1` user-managed form is **NOT** used here
  because all prior secrets in this project are `automatic`. **Stay consistent** — do not
  mix policies on a project.
- **Create once, then add a version:** `gcloud secrets create` makes the empty container;
  `gcloud secrets versions add ... --data-file=-` writes the value. Idempotent re-runs:
  `gcloud secrets describe <id>` exits 0 if it already exists → skip the create, just add
  a new version (adding a version does NOT disable prior versions; `latest` auto-points to
  the newest — infra MEMORY rotation note).
- **Value placeholders in this runbook:**
  - `<FOUNDER-PROVIDED: ...>` = an external credential the founder pastes (Gemini, MSG91,
    Razorpay, LangFuse, GCS).
  - `# machine-generatable: openssl rand -hex 32` = an internal secret the founder
    generates at runtime. **The generate command is a COMMENT — it is shown, not run by
    this runbook.** Never commit or print a real value.
- **Already-LIVE secrets:** several SM containers already have a live version (see the
  table in §3 and the infra MEMORY "Secret Manager population" log). For those, **no
  create/add is needed** — they are listed only so the founder knows which K8s Secret
  binds them. The genuinely-new creates are the **8 per-service DB passwords** (§2.1).

---

## 1. Pre-flight (read-only — confirm you are in the right project)

```bash
gcloud auth list                              # expect: * vaishnaviramoorthy@gmail.com
gcloud config get-value project               # expect: project-1f5cbf72-2820-4cdb-949
# If not:
# gcloud config set project project-1f5cbf72-2820-4cdb-949

# See what already exists (so you only create what's missing):
gcloud secrets list --project=project-1f5cbf72-2820-4cdb-949 \
  --format="table(name, replication.automatic.list(), createTime)"
```

---

## 2. SHARED secrets (created/confirmed FIRST — every service binds these)

### 2.1 — The 8 per-service DB passwords (THE NEW WORK — one per service)

Each service logs in as its own Postgres role (`<svc>_user`) with a password from a
dedicated SM secret. **The SAME value** is used in (a) the `ALTER ROLE <svc>_user WITH
PASSWORD '...'` in that service's `k8s/svc-<svc>/schema-role.sql` and (b) the
`DATABASE_URL` composed into its K8s Secret. These are per-service DB passwords, NOT new
IAM grants (stays within the §4 one-SA ceiling).

```bash
PROJECT=project-1f5cbf72-2820-4cdb-949

for SVC in export dashboard image pricing customer iam category catalog; do
  SECRET="dev-${SVC}-db-password"
  # create container once (skip if `gcloud secrets describe $SECRET` already exits 0):
  gcloud secrets create "$SECRET" --project="$PROJECT" --replication-policy=automatic
  # add the value — generate a strong password at runtime, do NOT hard-code it here:
  #   # machine-generatable: openssl rand -base64 32 | tr -d '\n'
  printf '%s' '<FOUNDER-PROVIDED: generated DB password for '"$SVC"'_user>' \
    | gcloud secrets versions add "$SECRET" --project="$PROJECT" --data-file=-
done
```

> Per service, the value created above is reused TWICE:
> 1. In `schema-role.sql`: `ALTER ROLE <svc>_user WITH PASSWORD '<that value>';`
> 2. In the K8s Secret `DATABASE_URL` (URL-encode `+ / @` with `urllib.parse.quote`).
>
> `dev-dashboard-db-password` → `dashboard_user` is a **read-only** role (via
> `k8s/svc-dashboard/audit-grant.sql`) — it owns no tables but still needs a login
> password.

### 2.2 — Shared `JWT_SECRET` (ONE value, all 8 services) — ALREADY LIVE

SM `jwt-secret` is **already LIVE** (version 1; `openssl rand -hex 64`). No create needed.

```bash
# Confirm it exists (read-only):
gcloud secrets versions list jwt-secret --project=project-1f5cbf72-2820-4cdb-949 \
  --filter="state=ENABLED" --format="value(name,state)"
# To (re)create only if it did NOT exist:
#   gcloud secrets create jwt-secret --project=project-1f5cbf72-2820-4cdb-949 --replication-policy=automatic
#   # machine-generatable: openssl rand -hex 64
#   printf '%s' '<generated 64-byte hex>' | gcloud secrets versions add jwt-secret --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
```

> **Why one value everywhere:** iam-svc signs the access JWT (HS256); every other service
> validates it LOCALLY with the SAME secret + vendored verify-core (D7 invariant — no
> callback to iam). A mismatched value 401s every authenticated cross-service request.

---

## 3. Per-service secrets

For each service: the create/add commands (only for what is NOT already live), then the
manual SM→k8s bind. **Order:** shared (§2) first, then the services below.

> **Most external creds below are ALREADY LIVE in SM** (Gemini, MSG91 ×2, Razorpay ×3,
> LangFuse secret, refresh-token-pepper, audit-pii-salt — see infra MEMORY). For those,
> the founder only needs the §3.9 **bind** step. The genuinely-new creates are the 8
> DB passwords (§2.1). The create commands are shown per service for completeness /
> disaster-recovery, guarded by `gcloud secrets describe`.

### 3.1 — svc-export (deterministic XLSX; NO AI, NO auth, NO payment)

K8s Secret: **`svc-export-secrets`** · keys (from `secrets.yaml.example`):

| Secret key | Source |
|---|---|
| `DATABASE_URL` | composed from `dev-export-db-password` (§2.1), schema `export` |
| `VALKEY_URL` | composed from `valkey-credentials` (live K8s Secret), DB 0 |
| `CELERY_BROKER_URL` | same Valkey, DB 1 |
| `CELERY_RESULT_BACKEND` | same Valkey, DB 2 |
| `JWT_SECRET` | SM `jwt-secret` (§2.2, LIVE) |
| `APP_ENV` | literal `development` (non-secret, carried in the Secret here as there is no svc-export ConfigMap) |
| `GCS_BUCKET` | `<FOUNDER-PROVIDED>` — `meesell-prod-assets` (export writes XLSX to GCS) |
| `GCS_PROJECT_ID` | `project-1f5cbf72-2820-4cdb-949` |

No SM creates beyond `dev-export-db-password` (§2.1). `GCS_BUCKET`/`GCS_PROJECT_ID` are
non-secret literals bound at §3.9.

### 3.2 — svc-dashboard (read-only metrics)

K8s Secret: **`svc-dashboard-secrets`** · ConfigMap: `svc-dashboard-config`
(`APP_ENV`, `FEATURE_TRACKING_DASHBOARD_ENABLED`).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | composed from `dev-dashboard-db-password` (§2.1) — read-only `dashboard_user` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |

No new SM creates beyond `dev-dashboard-db-password`.

### 3.3 — svc-image (AI-consuming; rembg deferred; dedicated Celery worker)

K8s Secret: **`svc-image-secrets`** · no ConfigMap (config carried in the Secret).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-image-db-password` (§2.1), schema `image` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `CELERY_BROKER_URL` | same Valkey, DB 1 |
| `CELERY_RESULT_BACKEND` | same Valkey, DB 2 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |
| `GEMINI_API_KEY` | SM `gemini-api-key` (LIVE) — `<FOUNDER-PROVIDED>` if recreating |
| `LANGFUSE_SECRET_KEY` | SM `langfuse-secret-key` (LIVE) — `<FOUNDER-PROVIDED>` if recreating |
| `APP_ENV` | literal `development` |

`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_HOST` are **ConfigMap** (non-secret), sourced from the
shared `meesell-config` — NOT created in SM.

### 3.4 — svc-pricing (deterministic P&L; NO AI)

K8s Secret: **`svc-pricing-secrets`** · no ConfigMap.

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-pricing-db-password` (§2.1), schema `pricing` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |
| `APP_ENV` | literal `development` |

### 3.5 — svc-customer (customer profiles)

K8s Secret: **`customer-svc-secrets`** (note: `customer-svc-`, not `svc-customer-`) ·
ConfigMap: `customer-svc-config` (`APP_ENV`, `CACHE_VERSION`).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-customer-db-password` (§2.1), schema `customer` |
| `VALKEY_URL` | live `valkey-credentials`, **DB 3** (customer uses DB 3, not 0 — copy verbatim) |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |

### 3.6 — svc-iam (auth + payment authority — MOST secret-rich)

K8s Secret: **`iam-svc-secrets`** (note: `iam-svc-`, not `svc-iam-`) ·
ConfigMap: `iam-svc-config` (`APP_ENV`, `JWT_ALGORITHM`, `ACCESS_TOKEN_TTL_SECONDS`,
`REFRESH_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_PEPPER_VERSION`, `CORS_ALLOWED_ORIGINS`,
`CORS_ALLOW_CREDENTIALS`).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-iam-db-password` (§2.1), schema `iam` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |
| `REFRESH_TOKEN_PEPPER` | SM `refresh-token-pepper` (LIVE) |
| `REFRESH_TOKEN_PEPPER_PREVIOUS` | SM `refresh-token-pepper` (same value when no rotation in flight) |
| `MSG91_AUTH_KEY` | SM `msg91-auth-key` (LIVE) — `<FOUNDER-PROVIDED>` if recreating |
| `MSG91_TEMPLATE_ID` | SM `msg91-template-id` (LIVE) — `<FOUNDER-PROVIDED>` if recreating |
| `RAZORPAY_KEY_ID` | SM `razorpay-key-id` (LIVE, TEST key) — `<FOUNDER-PROVIDED>` |
| `RAZORPAY_KEY_SECRET` | SM `razorpay-key-secret` (LIVE, TEST) — `<FOUNDER-PROVIDED>` |
| `RAZORPAY_WEBHOOK_SECRET` | SM `razorpay-webhook-secret` (LIVE) — `<FOUNDER-PROVIDED>` |
| `AUDIT_PII_SALT` | SM `audit-pii-salt` (LIVE) |

> All iam external creds are already LIVE. `REFRESH_TOKEN_PEPPER_VERSION`, `JWT_ALGORITHM`,
> the FE-D5 TTLs, and CORS are **ConfigMap** (non-secret) — not SM. iam carries NO Gemini,
> NO LangFuse, NO GCS, NO Celery (it is auth/payment only).
>
> Create commands for the LIVE external creds, only if a value is ever missing
> (machine-generatable internal ones shown as comments):
> ```bash
> # ALL of these already exist (gcloud secrets describe <id> exits 0). DO NOT recreate.
> # If a container were ever missing:
> #   gcloud secrets create refresh-token-pepper --project=project-1f5cbf72-2820-4cdb-949 --replication-policy=automatic
> #   # machine-generatable: openssl rand -hex 32
> #   printf '%s' '<generated>' | gcloud secrets versions add refresh-token-pepper --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
> #   gcloud secrets create audit-pii-salt --project=project-1f5cbf72-2820-4cdb-949 --replication-policy=automatic
> #   # machine-generatable: openssl rand -hex 32
> #   printf '%s' '<generated>' | gcloud secrets versions add audit-pii-salt --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
> #   # External (founder pastes the value from the provider dashboard):
> #   for ID in msg91-auth-key msg91-template-id razorpay-key-id razorpay-key-secret razorpay-webhook-secret gemini-api-key langfuse-secret-key; do
> #     gcloud secrets create "$ID" --project=project-1f5cbf72-2820-4cdb-949 --replication-policy=automatic
> #     printf '%s' '<FOUNDER-PROVIDED: paste from provider dashboard>' | gcloud secrets versions add "$ID" --project=project-1f5cbf72-2820-4cdb-949 --data-file=-
> #   done
> ```

### 3.7 — svc-category (AI-consuming; GLOBAL module)

K8s Secret: **`svc-category-secrets`** · ConfigMap: `svc-category-config`
(`APP_ENV`, `CACHE_VERSION`, `FEATURE_SMART_PICKER_ENABLED`, plus `LANGFUSE_PUBLIC_KEY`
+ `LANGFUSE_HOST` sourced from shared `meesell-config`).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-category-db-password` (§2.1), schema `category` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |
| `GEMINI_API_KEY` | SM `gemini-api-key` (LIVE) |
| `LANGFUSE_SECRET_KEY` | SM `langfuse-secret-key` (LIVE) |

### 3.8 — svc-catalog (AI-consuming)

K8s Secret: **`svc-catalog-secrets`** · ConfigMap: `svc-catalog-config`
(`APP_ENV`, `CACHE_VERSION`, `FEATURE_CATALOG_FORM_ENABLED`, `FEATURE_AI_AUTOFILL_ENABLED`,
`FEATURE_LIVE_PREVIEW_ENABLED="false"` — ships dark; plus `LANGFUSE_PUBLIC_KEY` +
`LANGFUSE_HOST` from shared `meesell-config`).

| Secret key | Source |
|---|---|
| `DATABASE_URL` | from `dev-catalog-db-password` (§2.1), schema `catalog` |
| `VALKEY_URL` | live `valkey-credentials`, DB 0 |
| `JWT_SECRET` | SM `jwt-secret` (LIVE) |
| `GEMINI_API_KEY` | SM `gemini-api-key` (LIVE) |
| `LANGFUSE_SECRET_KEY` | SM `langfuse-secret-key` (LIVE) |

### 3.9 — SM → K8s bind (the step that makes SM secrets reach the pods)

Creating the SM secret is **not enough**. Each `svc-*` pod reads a K8s Secret named
`<svc>-secrets` via `envFrom`. Build that K8s Secret from the SM values + the in-cluster
datastore passwords. This is the MANUAL bootstrap (external-secrets deferred to V1.5).

**Prerequisite:** `kubectl` reachable to the dev cluster (the dev server K3s node, port
6443 firewalled to the operator IP — see playbook §12.3 if it times out). The live
`postgres-credentials` / `valkey-credentials` K8s Secrets already exist in `dev`
(Day-1 bootstrap, playbook §5.1/§6.1).

> ⚠️ This bind step belongs to the **deploy** phase and runs only AFTER the D3 VM
> decision (§3 of the founder checklist). It is documented here so the founder sees the
> full chain. It is `kubectl`, not `gcloud`, and it mutates the cluster — DO NOT run it
> as part of "just create the SM secrets."

Sketch (per service — read SM values, compose URLs, create the K8s Secret):

```bash
# Example: svc-pricing (a simple, non-AI service). Adapt keys per the §3.x table.
PROJECT=project-1f5cbf72-2820-4cdb-949
get(){ gcloud secrets versions access latest --secret="$1" --project="$PROJECT"; }

PRICING_DB_PW=$(get dev-pricing-db-password)
VALKEY_PW=$(kubectl -n dev get secret valkey-credentials -o jsonpath='{.data.password}' | base64 -d)
JWT=$(get jwt-secret)

# URL-encode the password segments (base64/random can contain + / @):
enc(){ python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$1"; }

DATABASE_URL="postgresql+asyncpg://pricing_user:$(enc "$PRICING_DB_PW")@postgres.dev.svc.cluster.local:5432/meesell?options=-csearch_path%3Dpricing,public"
VALKEY_URL="redis://:$(enc "$VALKEY_PW")@valkey.dev.svc.cluster.local:6379/0"

kubectl -n dev create secret generic svc-pricing-secrets \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=VALKEY_URL="$VALKEY_URL" \
  --from-literal=JWT_SECRET="$JWT" \
  --from-literal=APP_ENV="development" \
  --dry-run=client -o yaml | kubectl apply -f -

unset PRICING_DB_PW VALKEY_PW JWT DATABASE_URL VALKEY_URL
```

> Repeat per service, adding ONLY that service's keys (see the §3.x tables): AI services
> (`image`, `category`, `catalog`) add `GEMINI_API_KEY` + `LANGFUSE_SECRET_KEY`; `iam`
> adds the pepper/MSG91/Razorpay/salt set; `export` adds the Celery + `GCS_*` keys;
> `image` adds the Celery keys; `customer` uses Valkey **DB 3**. Mind the two off-pattern
> Secret NAMES: `customer-svc-secrets` and `iam-svc-secrets`.
>
> **Never** `kubectl get secret -o yaml` and share the output; never echo a value
> (playbook §10).

---

## 4. Verify (read-only)

```bash
PROJECT=project-1f5cbf72-2820-4cdb-949

# 4.1 — All 8 per-service DB passwords exist with an ENABLED version:
for SVC in export dashboard image pricing customer iam category catalog; do
  echo -n "dev-${SVC}-db-password: "
  gcloud secrets versions list "dev-${SVC}-db-password" --project="$PROJECT" \
    --filter="state=ENABLED" --format="value(name)" | head -1 || echo "MISSING"
done

# 4.2 — The shared + external SM containers exist (no values printed):
gcloud secrets list --project="$PROJECT" \
  --filter="name:jwt-secret OR name:gemini-api-key OR name:msg91-auth-key OR name:msg91-template-id OR name:razorpay-key-id OR name:razorpay-key-secret OR name:razorpay-webhook-secret OR name:refresh-token-pepper OR name:audit-pii-salt OR name:langfuse-secret-key" \
  --format="table(name)"

# 4.3 — After the §3.9 bind (deploy phase only): the 8 K8s Secrets exist in dev:
kubectl -n dev get secret \
  svc-export-secrets svc-dashboard-secrets svc-image-secrets svc-pricing-secrets \
  customer-svc-secrets iam-svc-secrets svc-category-secrets svc-catalog-secrets \
  -o name 2>/dev/null || echo "(bind not done yet — that's expected pre-deploy)"
```

> **None of the above deploys anything.** §4.1 / §4.2 are pure SM reads. §4.3 only checks
> that K8s Secrets exist — it does not roll any pod. The 8-service rollout remains gated on
> the D3 `e2-standard-4` spend decision (founder checklist §3) and the MSG91 IP whitelist
> (§2). When those clear, the deploy wires `k8s/svc-*/` per the cutover gate (checklist §5).

---

## Appendix A — Master secret table

Secret name → consumer service(s) → Secret vs ConfigMap → external vs machine-generated →
the K8s `secretKeyRef`/env key it backs.

| SM secret / value | Consumed by | Secret or ConfigMap | Origin | Backs K8s env key |
|---|---|---|---|---|
| `jwt-secret` | all 8 | Secret | machine-gen (`openssl rand -hex 64`) — LIVE | `JWT_SECRET` |
| `dev-export-db-password` | export | Secret | machine-gen (`openssl rand -base64 32`) — **NEW** | `DATABASE_URL` |
| `dev-dashboard-db-password` | dashboard | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-image-db-password` | image | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-pricing-db-password` | pricing | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-customer-db-password` | customer | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-iam-db-password` | iam | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-category-db-password` | category | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `dev-catalog-db-password` | catalog | Secret | machine-gen — **NEW** | `DATABASE_URL` |
| `valkey-credentials` (live K8s Secret) | all 8 | Secret | machine-gen — LIVE (Day-1) | `VALKEY_URL` / `CELERY_*` |
| `gemini-api-key` | image, category, catalog | Secret | external `<FOUNDER-PROVIDED>` — LIVE | `GEMINI_API_KEY` |
| `langfuse-secret-key` | image, category, catalog | Secret | external `<FOUNDER-PROVIDED>` — LIVE | `LANGFUSE_SECRET_KEY` |
| `LANGFUSE_PUBLIC_KEY` | image, category, catalog | **ConfigMap** (`meesell-config`) | external `<FOUNDER-PROVIDED>` — **not SM** | `LANGFUSE_PUBLIC_KEY` |
| `LANGFUSE_HOST` | image, category, catalog | **ConfigMap** (`meesell-config`) | literal `https://cloud.langfuse.com` — **not SM** | `LANGFUSE_HOST` |
| `refresh-token-pepper` | iam | Secret | machine-gen (`openssl rand -hex 32`) — LIVE | `REFRESH_TOKEN_PEPPER` (+`_PREVIOUS`) |
| `msg91-auth-key` | iam | Secret | external `<FOUNDER-PROVIDED>` — LIVE | `MSG91_AUTH_KEY` |
| `msg91-template-id` | iam | Secret | external `<FOUNDER-PROVIDED>` — LIVE | `MSG91_TEMPLATE_ID` |
| `razorpay-key-id` | iam | Secret | external `<FOUNDER-PROVIDED>` (TEST) — LIVE | `RAZORPAY_KEY_ID` |
| `razorpay-key-secret` | iam | Secret | external `<FOUNDER-PROVIDED>` (TEST) — LIVE | `RAZORPAY_KEY_SECRET` |
| `razorpay-webhook-secret` | iam | Secret | external `<FOUNDER-PROVIDED>` — LIVE | `RAZORPAY_WEBHOOK_SECRET` |
| `audit-pii-salt` | iam | Secret | machine-gen (`openssl rand -hex 32`) — LIVE | `AUDIT_PII_SALT` |
| `GCS_BUCKET` | export | Secret (literal here) | external `<FOUNDER-PROVIDED>` (`meesell-prod-assets`) | `GCS_BUCKET` |
| `GCS_PROJECT_ID` | export | Secret (literal here) | literal `project-1f5cbf72-2820-4cdb-949` | `GCS_PROJECT_ID` |
| `APP_ENV` | all 8 | ConfigMap (or Secret literal for export/image/pricing) | literal `development` | `APP_ENV` |
| feature flags, TTLs, CORS, `CACHE_VERSION`, `JWT_ALGORITHM` | various | **ConfigMap** | literal — **not SM** | (per ConfigMap) |

> **Only the 8 `dev-<svc>-db-password` secrets are genuinely NEW work.** Everything else
> marked LIVE already has an ENABLED SM version. Non-secret config is ConfigMap, never SM.

---

## Appendix B — K8s Secret names (mind the two off-pattern names)

| Service | K8s Secret name | K8s ConfigMap name |
|---|---|---|
| export | `svc-export-secrets` | (none — config in Secret) |
| dashboard | `svc-dashboard-secrets` | `svc-dashboard-config` |
| image | `svc-image-secrets` | (none — config in Secret) |
| pricing | `svc-pricing-secrets` | (none — config in Secret) |
| customer | **`customer-svc-secrets`** | `customer-svc-config` |
| iam | **`iam-svc-secrets`** | `iam-svc-config` |
| category | `svc-category-secrets` | `svc-category-config` |
| catalog | `svc-catalog-secrets` | `svc-catalog-config` |
