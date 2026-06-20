# Runbook — Razorpay Subscriptions Go-Live (Celery beat + secrets + webhook + CSP)

> **Deploy-time operator checklist. Founder / infra runs this manually.** Nothing here
> is executed by an agent or during a docs/manifests authoring session. Every
> `gcloud` / `kubectl` / dashboard step is a deploy-window operation.
>
> | Field | Value |
> |---|---|
> | **Owner** | `meesell-infra-builder` (authored) → **founder/infra runs at deploy time** |
> | **Feature** | razorpay-integration (PR #323 → `develop`) — Waves 1–5 |
> | **GCP project** | `project-1f5cbf72-2820-4cdb-949` (numeric `888244156264`) |
> | **GCP account** | `vaishnaviramoorthy@gmail.com` |
> | **Region** | `asia-south1` (SM replication `automatic`) |
> | **Namespace** | `dev` first (V1), then `staging`. `prod` is **deferred to V1.5** (repo MASTER §3.1) — every `prod` step below is V1.5-forward, do NOT create the `prod` namespace yet. |
> | **Playbook authority** | `docs/INFRASTRUCTURE_PLAYBOOK.md` §6 (Valkey), §10 (Secret discipline), §15 (deploy template + mandatory `--dry-run=server` gate) |
> | **Companion runbooks** | `secret-bootstrap.md` (SM→K8s bind pattern, `iam-svc-secrets`), `auth-secret-rotation.md` (SM versioning conventions), `svc-iam-rollback.md` (iam rollback) |
> | **Code verified against** | `feature/razorpay` @ `63ce1e7` — `backend/app/workers/celery_app.py`, `backend/app/modules/iam/tasks.py`, `backend/app/modules/iam/router.py`, `backend/app/modules/iam/service.py`, `backend/app/shared/config.py`, `frontend/docker/csp-policy.env` |
>
> ## ⛔ This runbook deploys nothing on its own
>
> The Razorpay subscription system goes live only when ALL SIX sections below are
> done **in order**. The single highest-risk omission is **§1 (the beat process)** —
> without a running `celery beat`, the two periodic billing tasks are registered but
> **never fire** (the `beat_schedule` is inert). The second is **§2/§3 (the 5 plan IDs
> + webhook secret)** — these are Razorpay-dashboard-generated and must exist BEFORE a
> real subscribe is attempted.

---

## 0. How the pieces fit (read this first)

PR #323 ships the Razorpay subscription system across 5 waves. The deploy-time infra
surface is four things plus a federation reminder:

```
  Razorpay dashboard            our cluster (dev/staging)             our code
  ──────────────────            ─────────────────────────             ────────
  5 Plan objects        ──IDs──► RAZORPAY_PLAN_ID_* (K8s Secret)  ──► iam tier→plan map
  webhook + signing key ──key──► RAZORPAY_WEBHOOK_SECRET          ──► HMAC verify (svc)
  checkout.js (browser) ──────►  CSP allowlist (nginx/Traefik)    ──► Wave 5 checkout
                                 celery beat Deployment           ──► billing.reconcile
                                                                      billing.trial_sweep
```

- **iam owns billing.** The subscription/payment authority is the `iam` module
  (`backend/app/modules/iam/`). In the **8-service split** the K8s Secret is
  **`iam-svc-secrets`** and the ConfigMap is **`iam-svc-config`** (see
  `secret-bootstrap.md` Appendix B — mind the off-pattern `iam-svc-` prefix). In the
  **current monolith deploy** the live `dev` pods read **`backend-secrets`** +
  **`meesell-config`** (`k8s/api.yaml` / `k8s/worker.yaml`). This runbook documents BOTH
  bindings; use whichever matches the namespace you are deploying (today `dev` = monolith
  `backend-secrets`; the svc-* split is the V1.5 cutover gate per `secret-bootstrap.md`).
- **The 9 `RAZORPAY_*` settings** live in `backend/app/shared/config.py` (`Settings`).
  Three are genuine secrets (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`,
  `RAZORPAY_WEBHOOK_SECRET`). The 5 plan IDs + `RAZORPAY_LTD_PRICE_PAISE` are opaque,
  non-confidential dashboard/config values — but for simplicity all 9 are bound through
  the same K8s Secret here (they ride alongside the key/secret in `iam-svc-secrets` /
  `backend-secrets`). `RAZORPAY_LTD_PRICE_PAISE` has a code default (499900) and is
  optional to override.
- **`FEATURE_BILLING_ENABLED`** (ConfigMap, dev default `true`) gates whether the four
  `/api/v1/billing/*` routes are mounted. Keep it `true` for go-live; flip to `false` to
  dark the billing surface without touching secrets.

---

## 1. Celery beat process deploy (THE NEW INFRA — first beat_schedule in the repo)

> Supersedes `docs/plans/features/razorpay-integration/handoff_celery_beat_razorpay.md`
> (the Wave-4 beat memo). That memo is the source; this section is the executable
> runbook form.

### 1.1 What the beat process must run

`backend/app/workers/celery_app.py` carries the repo's **first `beat_schedule`** (two
fixed-cadence billing sweeps). Cadences are interpreted in `timezone="Asia/Kolkata"`
(with `enable_utc=True`), so the hours below are **IST**. The cadences are founder-ruled
(R1/R2) and are **NOT env-tunable** for V1.5.

| beat entry | task name | cadence | crontab (verbatim from code) |
|---|---|---|---|
| `billing-reconcile-every-6h` | `billing.reconcile` | every 6h — 00:00 / 06:00 / 12:00 / 18:00 **IST** | `crontab(minute=0, hour="*/6")` |
| `billing-trial-expiry-sweep-daily-0200` | `billing.trial_expiry_sweep` | daily **02:00 IST** | `crontab(minute=0, hour=2)` |

- `billing.reconcile` — lost/mis-ordered-webhook recovery: pulls Razorpay's authoritative
  state per non-terminal Razorpay-backed subscription and converges local state, plus a
  local-clock terminal sweep that downgrades lapsed `cancelled`/`halted`/`completed` subs.
- `billing.trial_expiry_sweep` — makes the 14-day app-side Pro trial → Free drop
  observable (writes a `billing.trial.expired` audit row; no Razorpay round-trip).

### 1.2 [DANGER] beat must run on EXACTLY ONE replica

**Two beat processes double-fire every scheduled task.** This is a hard `replicas: 1`
rule (or a single `-B` worker). The Valkey DB-0 singleton locks the tasks acquire —
`billing:reconcile:lock` and `billing:trial_sweep:lock` (`SET … NX EX 600`,
compare-and-delete release, in `backend/app/modules/iam/tasks.py`) — are a **safety net,
not a license to scale beat**. They make an accidental double-fire state-safe (the second
pass no-ops), but the correct deploy still runs ONE beat. Never set `replicas: 2` on the
beat Deployment, and never run `-B` on more than one worker replica.

### 1.3 Two options — recommendation

| Option | Command | When |
|---|---|---|
| **(a) Dedicated single-replica `celery beat` Deployment** | `celery -A app.workers.celery_app beat --loglevel=info` | **RECOMMENDED** — clean separation; beat lifecycle is independent of worker scaling; the obvious `replicas: 1` invariant lives on its own object. |
| (b) `celery worker -B` on a single worker | `celery -A app.workers.celery_app worker -B -Q celery,image-tasks …` | Only when there is **exactly one** worker replica. The current `k8s/worker.yaml` runs `replicas: 2` — so `-B` is **NOT** usable as-is (it would double-fire). |

**RECOMMENDED: Option (a), a dedicated single-replica `celery beat` Deployment.**

Rationale for the single-node K3s dev/staging cluster: the worker today runs `replicas: 2`
(`k8s/worker.yaml`) precisely so image/export throughput can scale. Option (b) `-B` would
force the worker to `replicas: 1` (or double-fire), coupling the beat-singleton constraint
to worker throughput. A dedicated beat Deployment with `replicas: 1` keeps the invariant
isolated, is cheap (beat is near-idle — it only enqueues), and survives worker scaling
untouched. No `redbeat`/`django-celery-beat` is needed — `celery==5.4.0` ships built-in
beat (in-process schedule, persisted to a small `celerybeat-schedule` file). The cron is
fixed in code, so the default file scheduler is sufficient; no PV is required (a restart
just re-reads the in-code schedule — it may fire one sweep slightly early after a restart,
which the idempotent task bodies absorb).

### 1.4 Manifest — `k8s/beat.yaml`

Matches `k8s/worker.yaml` conventions exactly (same image, `envFrom`, ADC-via-metadata
note, dev resource sizing). The ONLY differences: `replicas: 1`, `Recreate` strategy (a
beat singleton must never have two pods overlapping during a rollout), the `beat`
sub-command (no `-Q`, beat does not consume queues), and smaller resource requests (beat
only enqueues — it does no task work).

```yaml
# k8s/beat.yaml
# Celery BEAT Deployment — Razorpay Wave 4 (first beat_schedule in the repo).
# Mirrors k8s/worker.yaml conventions; the deltas are documented inline.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: beat
  namespace: dev
spec:
  # [DANGER] EXACTLY ONE replica. Two beat processes double-fire every scheduled
  # task. The Valkey singleton locks (billing:reconcile:lock / billing:trial_sweep:lock)
  # are a safety net, NOT a license to scale. NEVER set this above 1.
  replicas: 1
  strategy:
    # Recreate (not RollingUpdate): a beat singleton must never have two pods
    # overlapping. Kill the old beat pod before the new one starts. A few seconds
    # with no beat is harmless (the next tick still fires on schedule).
    type: Recreate
  selector:
    matchLabels:
      app: beat
  template:
    metadata:
      labels:
        app: beat
    spec:
      containers:
        - name: beat
          # Same image as api/worker (worker reuses the api image + a different CMD).
          image: asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:latest
          imagePullPolicy: Always
          command: ["celery"]
          args:
            - "-A"
            - "app.workers.celery_app"
            - "beat"
            - "--loglevel=info"
            # NO -Q here: beat ENQUEUES tasks, it does not consume any queue.
            # The worker (k8s/worker.yaml, -Q celery,image-tasks) executes them.
          envFrom:
            # Monolith dev binding (matches worker.yaml). For the 8-service split,
            # swap to the iam secret/config: secretRef iam-svc-secrets + configMapRef
            # iam-svc-config (see secret-bootstrap.md Appendix B). beat needs the
            # same iam billing env (RAZORPAY_*, DATABASE_URL, VALKEY_URL) the tasks read.
            - configMapRef:
                name: meesell-config
            - secretRef:
                name: backend-secrets
          # NOTE: GOOGLE_APPLICATION_CREDENTIALS absent — ADC via GCE metadata server
          # (VM SA 888244156264-compute@... ). Same as worker.yaml. Razorpay adapter
          # uses RAZORPAY_KEY_ID/_KEY_SECRET (env), not GCP creds; this note is for parity.
          resources:
            requests:
              # Beat only enqueues — far lighter than the worker (250m/512Mi). On the
              # 2-vCPU dev VM, keep beat tiny so it never contends with api/worker.
              cpu: "50m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
```

> The beat task BODIES open their own worker DB session (`make_worker_session`, NullPool)
> and their own Valkey DB-0 client for the lock — so beat needs `DATABASE_URL` +
> `VALKEY_URL` + the `RAZORPAY_*` keys in its env, exactly the iam set the worker already
> has. `envFrom backend-secrets` (monolith) / `iam-svc-secrets` (split) supplies all of it.
> No NEW env var is required for Wave 4 (the W4 memo confirms this).

### 1.5 Deploy + validate (per playbook §15 — `--dry-run=server` is mandatory)

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
NS=dev   # or staging
kubectl -n "$NS" diff -f k8s/beat.yaml || true
# [MANDATORY GATE — playbook §15] clean server-side dry-run before any real apply:
kubectl -n "$NS" apply -f k8s/beat.yaml --dry-run=server
kubectl -n "$NS" apply -f k8s/beat.yaml
kubectl -n "$NS" rollout status deployment/beat --timeout=120s
kubectl -n "$NS" get pods -l app=beat            # expect exactly ONE pod, 1/1 Running
# Confirm beat registered the two schedules (no task fired yet):
kubectl -n "$NS" logs deployment/beat | grep -iE "beat: Starting|billing-reconcile|trial-expiry"
```

Expected log lines include `beat: Starting...` and the two schedule names. The first real
fire is at the next 6h boundary (reconcile) / next 02:00 IST (trial sweep).

**Rollback:** `kubectl -n "$NS" delete -f k8s/beat.yaml`. The periodic tasks simply stop
firing (the system reverts to webhook-only state convergence — correct but without the 6h
reconcile safety net). No data is lost; re-apply to resume.

---

## 2. Razorpay secrets provisioning (the 9 `RAZORPAY_*` keys)

### 2.1 The 9 settings (one-line purpose each)

| `config.py` setting | Secret? | Purpose |
|---|---|---|
| `RAZORPAY_KEY_ID` | **secret** | Razorpay API key id (adapter + checkout) — `rzp_test_*` / `rzp_live_*`. |
| `RAZORPAY_KEY_SECRET` | **secret** | Razorpay API key secret (server-side adapter auth). NEVER sent to the browser. |
| `RAZORPAY_WEBHOOK_SECRET` | **secret** | HMAC signing secret for inbound webhook verification (§3). Dashboard-generated. |
| `RAZORPAY_PLAN_ID_STARTER_MONTHLY` | dashboard id | Plan-object id for the Starter monthly tier. |
| `RAZORPAY_PLAN_ID_PRO_MONTHLY` | dashboard id | Plan-object id for the Pro monthly tier. |
| `RAZORPAY_PLAN_ID_PRO_ANNUAL` | dashboard id | Plan-object id for the Pro annual tier. |
| `RAZORPAY_PLAN_ID_BUSINESS_MONTHLY` | dashboard id | Plan-object id for the Business monthly tier. |
| `RAZORPAY_PLAN_ID_BUSINESS_ANNUAL` | dashboard id | Plan-object id for the Business annual tier. |
| `RAZORPAY_LTD_PRICE_PAISE` | config int | LTD one-time Orders-API charge in paise (default `499900` = ₹4,999). No Plan object. Override only if the LTD price changes. |

### 2.2 [DASHBOARD PREREQUISITE] The 5 plan IDs are dashboard-generated — create them FIRST

The 5 `RAZORPAY_PLAN_ID_*` values are **opaque ids Razorpay generates** when you create a
Plan object — they are **NOT chosen by us**. Before any deploy where a real subscribe can
happen, in the Razorpay dashboard (**test mode first**, then **live mode** at real
go-live):

1. **Settings → … → Plans → Create Plan** for each of the 5 recurring tiers (Starter
   monthly, Pro monthly, Pro annual, Business monthly, Business annual). Set each Plan's
   amount/interval to match Pricing v2 §5 (the iam service layer owns the tier→plan map;
   the amounts must agree).
2. Copy each generated **Plan id** (`plan_…`).
3. LTD is **not** a Plan — it is a one-time Orders-API charge priced by
   `RAZORPAY_LTD_PRICE_PAISE`. No dashboard Plan to create for LTD.

> An empty plan id is NOT in `REQUIRED_FIELDS` (billing is flag-gated), so the app boots
> with blanks — but a real subscribe with the flag on will **fail loudly** against an empty
> plan id. Treat "all 5 plan ids populated" as a hard go-live precondition.

### 2.3 Test-mode vs live-mode key swap

- **Test mode** (current SM state): `razorpay-key-id` = `rzp_test_*`, `razorpay-key-secret`
  = its test pair, and **test-mode** Plan ids + a **test-mode** webhook secret. Use this
  for the §6 smoke (no real money moves).
- **Live mode** (real go-live): swap ALL of these to live values — `rzp_live_*` key id +
  live key secret, **live-mode** Plan ids (re-created in live mode; they are distinct ids
  from test mode), and a **live-mode** webhook signing secret. Add new SM versions (don't
  destroy the test versions — keep them for staging smokes), then re-materialize the K8s
  Secret and roll the pods.

> Current SM state (infra MEMORY): `razorpay-key-id` / `razorpay-key-secret` are at
> **version 2, TEST** keys; `razorpay-webhook-secret` is at version 1. The 5 plan-id
> values are **NOT yet in SM** — they ride in the K8s Secret directly (or add SM containers
> if you prefer SM as the source; see §2.4 note).

### 2.4 Create / update the secrets (SM → K8s, matching `secret-bootstrap.md`)

**Step A — SM (authoritative source; placeholders only, never a real value):**

Follow the `secret-bootstrap.md` idempotent pattern (`gcloud secrets describe` to skip an
existing container, then `versions add`). The three genuine secrets already exist as SM
containers:

```bash
PROJECT=project-1f5cbf72-2820-4cdb-949
# All three already exist (gcloud secrets describe <id> exits 0) — DO NOT recreate.
# To rotate / set the LIVE value, add a NEW version (old stays ENABLED; `latest` advances):
for ID in razorpay-key-id razorpay-key-secret razorpay-webhook-secret; do
  gcloud secrets describe "$ID" --project="$PROJECT" >/dev/null   # confirm exists
done
# Example (LIVE-mode swap — founder pastes the live value, never committed/echoed):
printf '%s' '<FOUNDER-PROVIDED: rzp_live_... key id>' \
  | gcloud secrets versions add razorpay-key-id --project="$PROJECT" --data-file=-
# Verify NO trailing newline (last byte must NOT be 0a — auth-secret-rotation.md §4):
gcloud secrets versions access latest --secret=razorpay-key-id --project="$PROJECT" | tail -c 1 | xxd
```

The 5 plan ids are dashboard ids, not confidential — you may either (i) keep them in the
K8s Secret directly (Step B), or (ii) add SM containers `razorpay-plan-id-<tier>` for a
single source of truth. This runbook uses (i) for simplicity (they are not secret); switch
to (ii) if you want SM to own every `RAZORPAY_*` value uniformly.

**Step B — K8s Secret (monolith `dev` today: patch `backend-secrets`):**

The live `dev`/`staging` pods read `backend-secrets` via `envFrom` (`k8s/worker.yaml`,
`k8s/api.yaml`, and the §1 beat). Materialize the 9 keys into it. `kubectl patch --type
merge` touches ONLY the listed keys and leaves the other ~20 keys untouched (the
auth-secret-rotation.md pattern):

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
PROJECT=project-1f5cbf72-2820-4cdb-949
NS=dev   # or staging
get(){ gcloud secrets versions access latest --secret="$1" --project="$PROJECT"; }

KEY_ID="$(get razorpay-key-id)"
KEY_SECRET="$(get razorpay-key-secret)"
WEBHOOK_SECRET="$(get razorpay-webhook-secret)"

# Plan ids: paste the 5 dashboard ids for this MODE (test vs live). Placeholders shown.
kubectl -n "$NS" patch secret backend-secrets --type merge -p "$(cat <<JSON
{"stringData":{
  "RAZORPAY_KEY_ID":"$KEY_ID",
  "RAZORPAY_KEY_SECRET":"$KEY_SECRET",
  "RAZORPAY_WEBHOOK_SECRET":"$WEBHOOK_SECRET",
  "RAZORPAY_PLAN_ID_STARTER_MONTHLY":"<FOUNDER-PROVIDED: plan_... starter monthly>",
  "RAZORPAY_PLAN_ID_PRO_MONTHLY":"<FOUNDER-PROVIDED: plan_... pro monthly>",
  "RAZORPAY_PLAN_ID_PRO_ANNUAL":"<FOUNDER-PROVIDED: plan_... pro annual>",
  "RAZORPAY_PLAN_ID_BUSINESS_MONTHLY":"<FOUNDER-PROVIDED: plan_... business monthly>",
  "RAZORPAY_PLAN_ID_BUSINESS_ANNUAL":"<FOUNDER-PROVIDED: plan_... business annual>"
}}
JSON
)"
unset KEY_ID KEY_SECRET WEBHOOK_SECRET
# RAZORPAY_LTD_PRICE_PAISE: has a code default (499900). Only set it if overriding —
# it belongs in meesell-config (non-secret) rather than the Secret if you do.
```

> **8-service split (V1.5 cutover):** the same 9 keys go into **`iam-svc-secrets`** (NOT
> `backend-secrets`) via the `secret-bootstrap.md` §3.6 / §3.9 bind pattern — iam is the
> only service that carries the Razorpay keys. The off-pattern name `iam-svc-secrets` is
> deliberate (Appendix B of that runbook).

**Step C — roll the pods so they pick up the new env:**

```bash
kubectl -n "$NS" rollout restart deployment/api deployment/worker deployment/beat
kubectl -n "$NS" rollout status  deployment/api    --timeout=120s
kubectl -n "$NS" rollout status  deployment/worker --timeout=120s
kubectl -n "$NS" rollout status  deployment/beat   --timeout=120s
```

> [DANGER] Never `kubectl get secret backend-secrets -o yaml` and share the output; never
> echo a key value to a log (playbook §10).

---

## 3. Webhook registration

The webhook endpoint is **`POST /api/v1/webhooks/razorpay`** (verified:
`backend/app/modules/iam/router.py` route `"/webhooks/razorpay"` under the `/api/v1`
prefix → handler `razorpay_webhook`).

### 3.1 Register in the Razorpay dashboard

1. **Settings → Webhooks → Add New Webhook.**
2. **Webhook URL:**
   - dev/test smoke: a publicly reachable tunnel to dev, OR `https://api.mesell.xyz/api/v1/webhooks/razorpay` if dev's API host is the registered one.
   - staging: `https://staging-api.mesell.xyz/api/v1/webhooks/razorpay`.
   - prod (V1.5): `https://api.mesell.xyz/api/v1/webhooks/razorpay`.
3. **Active events** — select the events the router actually handles (verified
   `_EVENT_HANDLERS` in `service.py`). Unhandled events are recorded + 200'd (no retry),
   but selecting only these keeps the dashboard clean:
   - `subscription.authenticated`
   - `subscription.activated`
   - `subscription.charged`
   - `subscription.pending`
   - `subscription.halted`
   - `subscription.cancelled`
   - `subscription.completed`
   - `subscription.updated`
   - `payment.captured`
   - `payment.failed`
   - `refund.processed`
4. **Secret** — Razorpay generates a webhook **signing secret** when you save. Copy it
   into SM `razorpay-webhook-secret` (§2.4 Step A) and re-materialize + roll (§2.4 B/C).

### 3.2 Signature verification is enforced server-side

The handler reads the **raw** request body and the `X-Razorpay-Signature` header and
calls `verify_webhook_signature(raw_body, signature)` **before** any JSON parse
(`service.py::capture_razorpay_webhook` step 1). An invalid signature → 401; the body is
never parsed on a bad signature. So `RAZORPAY_WEBHOOK_SECRET` **must match** the
dashboard's generated secret for the registered URL exactly — a mismatch 401s every
webhook (and subscriptions will silently never activate). Re-confirm the secret after any
test→live mode swap (the live-mode webhook has its own distinct secret).

---

## 4. CSP allowlist (checkout.js)

The Wave 5 checkout flow loads Razorpay's `checkout.js` in the browser. The CSP
**mechanism is infra-owned** (`frontend/docker/nginx.conf.template` emits the
`Content-Security-Policy` header; `frontend/docker/docker-entrypoint.sh` selects the
per-env value via `APP_ENV`); the **allowlist CONTENT** is frontend-owned
(`frontend/docker/csp-policy.env`). Razorpay needs three hosts added per environment:

| Razorpay host | CSP directive(s) | Why |
|---|---|---|
| `https://checkout.razorpay.com` | `script-src` (loads `checkout.js`), `frame-src` (checkout modal iframe) | The checkout script + its iframe. |
| `https://api.razorpay.com` | `connect-src` | XHR/fetch the checkout makes to Razorpay's API. |
| `https://lumberjack.razorpay.com` | `connect-src` | Razorpay's telemetry/analytics beacon host. |

> Current `csp-policy.env` has NO `frame-src` directive and NO Razorpay hosts — it is
> scoped to Native-Federation remotes only. Adding `checkout.razorpay.com` to `script-src`
> + a new `frame-src 'self' https://checkout.razorpay.com`, and the api/lumberjack hosts to
> `connect-src`, is the required change. **Frontend-owned edit** — flag it to the frontend
> lead; infra only confirms the mechanism renders it. Per the file header, confirm each
> token EMPIRICALLY on the dev smoke (open the browser console; any blocked
> `checkout.razorpay.com` / `api.razorpay.com` / `lumberjack.razorpay.com` request surfaces
> as a CSP violation). Apply the same three hosts to all three env values
> (`CSP_POLICY_dev` / `_staging` / `_prod`), using the `https://` forms in staging/prod.

Example of the directives to add (frontend lead authors the exact merge into each env
value):

```
script-src  … https://checkout.razorpay.com
frame-src   'self' https://checkout.razorpay.com
connect-src … https://api.razorpay.com https://lumberjack.razorpay.com
```

The CSP is re-rendered at container start by `docker-entrypoint.sh`, so a frontend image
rebuild + redeploy (or just a pod restart if the env value changed via the same image) is
what activates the new allowlist.

---

## 5. Federation full-fleet rebuild reminder (FE / master-owned — flag, don't execute)

> **This is NOT infra to execute** — it is FE/master-owned. It is in the go-live sequence
> because skipping it reintroduces a P0 logout bug.

Wave 3 widened `@mesell/core` (added the entitlement surface). Per the standing federation
singleton finding (master memory `finding-federation-auth-singleton-not-shared.md`), **ALL
7 micro-frontend remotes MUST be rebuilt from the same `libs/core` commit at deploy**. If
the shell and remotes are built from divergent `@mesell/core` versions, the Native
Federation singleton dedup fails → more than one `AuthService` instance → the remote's
token is `null` → `authGuard` bounces to `/login` (**logout on nav**). Give the shared
`@mesell/*` libs an explicit identical version and rebuild every remote from the same
commit. Owner: `meesell-frontend-coordinator` / master. Infra just sequences it (§6 step 5).

---

## 6. Go-live sequence checklist (ordered)

Do these in order. Each box is a hard gate for the next.

- [ ] **0. Pre-flight** — `gcloud auth list` = `vaishnaviramoorthy@gmail.com`;
      `gcloud config get-value project` = `project-1f5cbf72-2820-4cdb-949`; `kubectl`
      reaches the target namespace (playbook §1 / §12.3 if it times out).
- [ ] **1. Create the 5 dashboard Plan objects** (§2.2) in the target MODE (test for the
      smoke, live for real go-live); copy the 5 Plan ids. Create LTD price config if it
      differs from the default.
- [ ] **2. Set the 9 `RAZORPAY_*` secrets per namespace** (§2.4): SM versions for the 3
      genuine secrets (live-mode swap if applicable) → patch `backend-secrets`
      (monolith) / `iam-svc-secrets` (split) with all 9 keys.
- [ ] **3. Register the webhook** (§3): add the webhook URL for this env, select the 11
      handled events, copy the signing secret into `razorpay-webhook-secret`, re-materialize
      + roll. Confirm the secret matches (a bad secret 401s every webhook).
- [ ] **4. Deploy the beat process** (§1.4/§1.5): `kubectl apply -f k8s/beat.yaml`
      (`--dry-run=server` gate first); confirm exactly ONE beat pod Running + the two
      schedules in its log.
- [ ] **5. Rebuild the 7 federation remotes** from the same `libs/core` commit (§5) — FE /
      master. Verify shell→remote nav does not log out.
- [ ] **6. CSP allowlist** (§4): frontend adds the 3 Razorpay hosts (+ `frame-src`) to all
      env values; rebuild/redeploy the shell image; confirm zero CSP violations for the
      Razorpay hosts in the browser console.
- [ ] **7. Smoke test** (test mode): from the app, subscribe to a paid tier → Razorpay
      checkout opens (CSP OK) → complete the test payment → Razorpay fires
      `subscription.activated` / `payment.captured` → the webhook 200s (signature valid) →
      poll the user's entitlement and confirm the plan/entitlement is granted within a few
      seconds. Then leave it for one `billing.reconcile` cycle (or trigger one) and confirm
      no spurious downgrade.
- [ ] **8. (real go-live only) Repeat 1–7 in LIVE mode** — live keys, live Plan ids, live
      webhook secret. Test-mode SM versions stay ENABLED for staging.

### Rollback note

- **Beat:** `kubectl -n <ns> delete -f k8s/beat.yaml` — the periodic sweeps stop; webhook-
  driven state convergence continues. No data loss.
- **Billing surface:** set `FEATURE_BILLING_ENABLED=false` in `meesell-config` (or the iam
  ConfigMap) + roll the api → the four `/billing/*` routes 404 (billing dark) without
  touching secrets. The webhook route is unaffected (it lives on the iam router, not the
  flag-gated billing router) — webhooks keep being captured/verified.
- **Secrets / mode revert:** to roll back a live-mode swap, re-point the K8s Secret at the
  prior (test) SM versions (the `auth-secret-rotation.md` §1 rollback pattern — `versions
  list … | sed -n '2p'` for the previous version), re-materialize, roll the pods.
- **iam pod-level rollback:** see `docs/runbooks/svc-iam-rollback.md`.
- Never delete a Razorpay Plan object or webhook to "roll back" — disable the webhook in
  the dashboard and flip `FEATURE_BILLING_ENABLED` instead.

---

## 7. Verify (read-only)

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
NS=dev
# beat: exactly ONE pod, Running:
kubectl -n "$NS" get deployment beat -o jsonpath='{.status.replicas}/{.status.readyReplicas}'; echo
# the 9 RAZORPAY_* keys are present in the Secret (KEY NAMES only — never values):
kubectl -n "$NS" get secret backend-secrets -o jsonpath='{.data}' \
  | python3 -c 'import sys,json;print(sorted(k for k in json.load(sys.stdin) if k.startswith("RAZORPAY_")))'
# webhook secret has an ENABLED SM version (no value printed):
gcloud secrets versions list razorpay-webhook-secret \
  --project=project-1f5cbf72-2820-4cdb-949 --filter="state=ENABLED" --format="value(name,state)"
```

Expected: beat `1/1`; the key list shows the 8 string keys (`RAZORPAY_KEY_ID`,
`RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, + the 5 plan ids);
`razorpay-webhook-secret` lists ≥1 ENABLED version.
