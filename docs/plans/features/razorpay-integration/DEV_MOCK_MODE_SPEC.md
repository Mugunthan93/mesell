# Razorpay Dev-Mock Mode — Builder-Ready Spec

**Author:** meesell-backend-coordinator (backend lead)
**Date:** 2026-06-20
**Status:** SPEC — awaiting founder approval to dispatch builders. Do NOT build from a draft.
**Base commit:** `8b5dce2` (Merge PR #323 — Razorpay Subscriptions Waves 1–5 → develop)
**Feature slug:** `razorpay-dev-mock`
**Scope:** dev-only, flag-gated mock path so the founder can exercise the full billing flow
locally with NO Razorpay account and NO network call — mirroring the existing
`DEV_OTP_BYPASS_CODE` / `000000` pattern (force-disabled when `APP_ENV == "production"`).

> ⚠️ **Working-tree note for builders.** As of this writing the master tree HEAD (`fa61a61`)
> is **behind** the merge commit `8b5dce2`. All line references below are against `8b5dce2`
> (the merged Razorpay code). Builders MUST branch off the integration tip that carries the
> merged Razorpay code (develop after the #323 merge), NOT the stale local HEAD. Verify with
> `git show <base>:backend/app/adapters/razorpay.py | grep -c "async def create_subscription"`
> → must be `1`. If `0`, you are on a stale base — STOP and re-base.

---

## 0. Design philosophy (read first)

The mock is **NOT a fake end-state.** It must drive the **real internal state machine** so
that every downstream read (`GET /billing/subscription`, `resolve_entitlement`, `/auth/me`)
returns the correct tier through the exact same code paths a real webhook would exercise.

Concretely:

1. The **adapter** returns realistic fake objects (`sub_mock_*`, `order_mock_*`, fake
   `short_url`, `created` status) with **zero network I/O**.
2. After the existing `subscribe()` / `start_trial()` / `cancel()` service helpers create the
   local `subscriptions` row, the mock **replays a synthetic Razorpay webhook** through the
   real `capture_razorpay_webhook(...)` → `_route_webhook_in_session(...)` →
   `_EVENT_HANDLERS[...]` dispatch path. That handler (`_handle_subscription_activated` /
   `_handle_payment_captured` / `_handle_subscription_cancelled`) performs the **real**
   `users.plan` grant + `current_period_end` set + `audit_events` write + `webhook_events`
   dedupe-INSERT.
3. The FE response carries a `mock: true` signal so the FE **skips opening checkout.js** and
   goes straight to the existing poll. Because the backend already granted entitlement
   synchronously, the very first poll of `GET /billing/subscription` flips to `active`.

This means: **no parallel "mock entitlement" code, no new route, no new Celery task, no
duplicate grant logic.** Everything funnels through the LOCKED transition helpers, so the mock
can never drift from production behaviour.

---

## 1. Config flag (`backend/app/shared/config.py`)

### 1.1 New field — copy the OTP-bypass idiom verbatim

Add directly **after** the `DEV_OTP_BYPASS_CODE` field (config.py line ~280 on `8b5dce2`):

```python
# ── Dev-only Razorpay mock (razorpay-dev-mock feature) ─────────────────────
# OFF by default (False == disabled). When True *and* APP_ENV != "production",
# the billing service short-circuits every Razorpay adapter call to a local
# fake (no network, no SDK, no account) AND immediately replays a synthetic
# activation/capture/cancel webhook through the REAL transition state machine
# so GET /billing/subscription flips to active on the first poll. The subscribe
# response carries `mock: true` so the FE skips checkout.js. FORCE-DISABLED in
# production by the APP_ENV guard at every call site (see iam/service.py), so a
# leaked True in a prod env never reaches Razorpay-bypass code. Dev sets True;
# PROD MUST leave False.
RAZORPAY_DEV_MOCK: bool = False
```

### 1.2 Force-disable property (defence-in-depth)

Add a read-only convenience property next to `is_dev` / `is_staging` / `is_prod`
(config.py line ~389):

```python
@property
def razorpay_mock_active(self) -> bool:
    """True only when the dev mock is enabled AND we are NOT in production.

    This is the single computed gate the service layer reads. It mirrors the
    OTP bypass's inline `bool(DEV_OTP_BYPASS_CODE) and APP_ENV != "production"`
    expression, centralised here so the production force-disable lives in ONE
    place that cannot be forgotten at a call site.
    """
    return self.RAZORPAY_DEV_MOCK and self.APP_ENV != "production"
```

Every call site reads `settings.razorpay_mock_active` — **never** `settings.RAZORPAY_DEV_MOCK`
directly (so the production guard is structurally impossible to bypass).

### 1.3 NOT added to `REQUIRED_FIELDS`

`RAZORPAY_DEV_MOCK` is a bool with a safe default (`False`) — it is **not** required and is
**not** added to the `REQUIRED_FIELDS` list. No new validator. Existing envs boot unchanged.

### 1.4 How the founder turns it on locally

Add to the local `backend/.env` (dev only):

```
APP_ENV=development
FEATURE_BILLING_ENABLED=true   # already defaults True in dev
RAZORPAY_DEV_MOCK=true
```

No `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_PLAN_ID_*` / `RAZORPAY_WEBHOOK_SECRET`
real values are needed when the mock is on — the adapter never reads them on the mock path, and
the synthetic webhook bypasses HMAC verification (see §3.4). The existing dev placeholders that
already satisfy `REQUIRED_FIELDS` are sufficient.

`.env.example` gets a documented `RAZORPAY_DEV_MOCK=false` line in the Razorpay block.

---

## 2. Backend mock behavior — adapter selection at the service seam

### 2.1 Where the branch lives (DECISION: service-seam, not adapter-internal)

The adapter module (`backend/app/adapters/razorpay.py`) imports the real `razorpay` SDK at
module top-level. The cleanest, lowest-risk place to branch is the **service layer call site**
(`iam/service.py`), NOT inside each adapter method. Rationale:

- The 6 async adapter methods stay pure transport wrappers (no flag-awareness leaking into the
  adapter — keeps §6 adapter discipline clean).
- The mock returns the **same frozen dataclasses** (`RazorpaySubscription`, `RazorpayOrder`,
  `RazorpayCustomer`) the real adapter returns, so the service code path downstream of the call
  is byte-identical between real and mock.

Implementation: add a tiny mock module `backend/app/adapters/razorpay_mock.py` that exposes the
same 6 coroutine signatures as the real adapter, returning fakes. In `iam/service.py`, select
the adapter at call time:

```python
# iam/service.py — replace the module-level binding usage.
# Existing (line 39):  from app.adapters import razorpay as razorpay_adapter
# Add:                 from app.adapters import razorpay_mock

def _rzp():
    """Return the active Razorpay adapter — real, or the dev mock when enabled.

    Read at CALL TIME (not import time) so a test/founder toggling the flag
    after import is honoured, and so the production force-disable in
    `razorpay_mock_active` is evaluated fresh on every call.
    """
    return razorpay_mock if settings.razorpay_mock_active else razorpay_adapter
```

Then every `razorpay_adapter.create_subscription(...)` / `.create_order(...)` /
`.cancel_subscription(...)` call in `subscribe()` and `cancel()` becomes
`_rzp().create_subscription(...)` etc. (3 call sites total: 2 in `subscribe`, 1 in `cancel`).

> **Why not patch the singleton?** The hermetic tests already `monkeypatch.setattr` the adapter
> functions; a module-swap via `_rzp()` is orthogonal and does not collide (the mock branch is
> only taken when `razorpay_mock_active` is True, which the hermetic tests never set — they run
> with `APP_ENV` defaulting to `development` but `RAZORPAY_DEV_MOCK` defaulting to `False`).

### 2.2 The 6 mock methods (`backend/app/adapters/razorpay_mock.py`)

Each returns the real frozen dataclass from `app.adapters.razorpay`, with deterministic fake
ids. No network, no SDK import. All `async def` to match the real signatures exactly.

| Method | Mock return |
|---|---|
| `create_subscription(*, plan_id, customer_notify=True, total_count=None, notes=None)` | `RazorpaySubscription(id=f"sub_mock_{uuid4().hex[:14]}", status="created", plan_id=plan_id or "plan_mock", current_end=None, short_url=f"https://mock.razorpay.local/sub/{id}", notes=notes or {})` |
| `create_order(*, amount, currency="INR", receipt, notes=None)` | `RazorpayOrder(id=f"order_mock_{uuid4().hex[:14]}", amount=amount, currency=currency, status="created", receipt=receipt)` |
| `fetch_subscription(sub_id)` | `RazorpaySubscription(id=sub_id, status="active", plan_id="plan_mock", current_end=<now+30d epoch>, short_url=None, notes={})` — used only by Wave-4 reconcile; mock returns an already-active sub |
| `cancel_subscription(sub_id, *, cancel_at_cycle_end=True)` | `RazorpaySubscription(id=sub_id, status="active" if cancel_at_cycle_end else "cancelled", plan_id="plan_mock", current_end=<now+30d epoch>, short_url=None, notes={})` |
| `update_subscription(sub_id, *, plan_id, schedule_change_at="cycle_end")` | `RazorpaySubscription(id=sub_id, status="active", plan_id=plan_id, current_end=<now+30d epoch>, short_url=None, notes={})` |
| `get_customer(customer_id)` | `RazorpayCustomer(id=customer_id, email=None, contact=None)` |

`verify_webhook_signature` is **NOT** re-implemented in the mock module — see §3.4.

### 2.3 Period-end value used by the synthetic webhook

For recurring tiers the synthetic `subscription.activated` event carries
`current_end = epoch(now + 30 days)` so `current_period_end` is set to a future timestamp and
`resolve_entitlement` step-2 (paid plan + live sub) passes. For LTD, the synthetic
`payment.captured` sets `current_period_end = NULL` (the perpetual sentinel the real handler
already sets — see `_handle_payment_captured` line ~1476).

---

## 3. Entitlement grant via the REAL state machine (KEY DESIGN)

The mock does **not** touch `users.plan` directly. It calls the existing service helpers to
create the local row, then replays a synthetic webhook through the real router.

### 3.1 `subscribe()` mock tail — recurring tiers

After the existing `subscribe()` body creates the `subscriptions` row (status `created`,
`razorpay_subscription_id` = the `sub_mock_*` id, `current_period_end` NULL), append a
mock-only tail BEFORE the `return SubscribeResult(...)`:

```python
if settings.razorpay_mock_active:
    await _mock_drive_activation(db, sub, tier=tier)
```

`_mock_drive_activation` builds a synthetic `subscription.activated` payload and routes it
through the real handler:

```python
async def _mock_drive_activation(db: AsyncSession, sub: Subscription, *, tier: str) -> None:
    """DEV-MOCK ONLY. Replay a synthetic subscription.activated webhook through
    the REAL router so the plan grant + period-end + audit + dedupe row all land
    via the LOCKED transition helpers (never a parallel path)."""
    assert settings.razorpay_mock_active  # never reachable in prod
    new_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    payload = {
        "event": "subscription.activated",
        "id": f"evt_mock_{uuid4().hex}",   # unique dedupe key per replay
        "payload": {
            "subscription": {
                "entity": {
                    "id": sub.razorpay_subscription_id,
                    "status": "active",
                    "current_end": new_end,
                    "plan_id": "plan_mock",
                    "notes": {"user_id": str(sub.user_id), "tier": tier},
                }
            }
        },
    }
    await _route_webhook_in_session(
        db,
        event_id=payload["id"],
        event_type="subscription.activated",
        payload=payload,
        owns_transaction=False,   # the request-scoped session owns the commit
    )
```

This invokes `_handle_subscription_activated` (service.py line ~1298), which sets
`sub.status="active"`, `sub.current_period_end=new_end`, and calls `_grant_plan_for_sub`
(line ~1196) → `users.plan = _TIER_TO_PLAN[tier]` + `billing.plan.granted` audit row.

> **Why call `_route_webhook_in_session` and not the handler directly?** Routing through
> `_route_webhook_in_session` also writes the `webhook_events` dedupe row via the real
> `INSERT ... ON CONFLICT (event_id) DO NOTHING` path, so the mock exercises the FULL idempotent
> pipeline — see §3.5. We pass `owns_transaction=False` because the route's `get_db` session
> owns the commit boundary (same as the Wave-3 webhook route path).

### 3.2 `subscribe()` mock tail — LTD

For `tier == "ltd"`, the real body creates the order + a `subscriptions` row with
`razorpay_order_id` = `order_mock_*` and `current_period_end=NULL`. The mock tail replays a
synthetic `payment.captured`:

```python
if settings.razorpay_mock_active:
    await _mock_drive_ltd_capture(db, sub, order_id=order.id)
```

```python
async def _mock_drive_ltd_capture(db, sub, *, order_id: str) -> None:
    assert settings.razorpay_mock_active
    payload = {
        "event": "payment.captured",
        "id": f"evt_mock_{uuid4().hex}",
        "payload": {
            "payment": {"entity": {
                "id": f"pay_mock_{uuid4().hex[:14]}",
                "order_id": order_id,
                "amount": settings.RAZORPAY_LTD_PRICE_PAISE,
                "currency": "INR",
                "notes": {"user_id": str(sub.user_id), "tier": "ltd"},
            }},
            "order": {"entity": {
                "id": order_id,
                "notes": {"user_id": str(sub.user_id), "tier": "ltd"},
            }},
        },
    }
    await _route_webhook_in_session(
        db, event_id=payload["id"], event_type="payment.captured",
        payload=payload, owns_transaction=False,
    )
```

This invokes `_handle_payment_captured` (line ~1446) → `users.plan = "ltd"`,
`current_period_end = NULL`, `payments` upsert, `billing.plan.granted` audit.

### 3.3 `start_trial()` — NO mock tail needed

`start_trial()` is **already** app-side only (no Razorpay call). It sets
`users.trial_ends_at = now()+14d` and `resolve_entitlement` step-3 already collapses
`free + live trial → pro`. The mock changes **nothing** here. (Listed explicitly so the builder
does not add a redundant tail.)

### 3.4 `cancel()` mock tail + the LOCKED `verify_webhook_signature`

`cancel()` calls `adapter.cancel_subscription(...)` (now `_rzp().cancel_subscription(...)`) which
the mock satisfies, then sets `cancel_scheduled_at`. In production the real
`subscription.cancelled` webhook is what flips `status → 'cancelled'`. For a faithful mock,
append a synthetic `subscription.cancelled` replay so the local row reaches the terminal state
the founder expects to see:

```python
if settings.razorpay_mock_active and sub.razorpay_subscription_id:
    await _mock_drive_cancel(db, sub)
```

```python
async def _mock_drive_cancel(db, sub) -> None:
    assert settings.razorpay_mock_active
    payload = {
        "event": "subscription.cancelled",
        "id": f"evt_mock_{uuid4().hex}",
        "payload": {"subscription": {"entity": {
            "id": sub.razorpay_subscription_id,
            "status": "cancelled",
            "notes": {"user_id": str(sub.user_id), "tier": sub.tier},
        }}},
    }
    await _route_webhook_in_session(
        db, event_id=payload["id"], event_type="subscription.cancelled",
        payload=payload, owns_transaction=False,
    )
```

This routes to `_handle_subscription_cancelled` (line ~1381) → `sub.status="cancelled"` +
`billing.subscription.cancelled` audit. Per the real contract, `users.plan` stays at tier until
`current_period_end` (the Wave-4 reconcile sweep does the eventual downgrade — the mock does
NOT fake that downgrade, matching production). So after a mock cancel the founder sees
`status="cancelled"`, `cancel_scheduled=true`, but `entitlement` still `pro` until period end —
which is the **correct** real behaviour and a useful thing to verify.

**`verify_webhook_signature` (LOCKED — §6.E exception #1/#2).** The mock must NOT touch this
function and must NOT route through the HTTP webhook endpoint (which calls it). The synthetic
replays call `_route_webhook_in_session(...)` **directly**, which begins AFTER the signature
check in `capture_razorpay_webhook` (the signature verify is the first step of
`capture_razorpay_webhook`, lines ~1632; `_route_webhook_in_session` is the post-verify core).
Therefore the mock never invokes HMAC verification, never needs a real `RAZORPAY_WEBHOOK_SECRET`,
and the LOCKED function is left byte-for-byte untouched. **Do NOT call
`capture_razorpay_webhook` from the mock** (it would force a signature path); call
`_route_webhook_in_session` directly.

### 3.5 Idempotency / `webhook_events` row (DECISION: WRITE the synthetic row)

The mock **writes a real `webhook_events` row** (via `_route_webhook_in_session`'s
`INSERT ... ON CONFLICT (event_id) DO NOTHING`) with a unique `evt_mock_<uuid>` event_id per
replay. Rationale:

- It exercises the real idempotent pipeline end-to-end (the whole point of the mock).
- A unique event_id per replay means re-subscribing after a cancel does not collide.
- The synthetic rows are harmless dev data; they are visibly prefixed `evt_mock_` for cleanup.
- This preserves the ON CONFLICT contract rather than special-casing it.

The synthetic `payload_jsonb` is stored as-is. `signature_valid=True` is set by the insert
statement (the mock asserts validity by construction since it never went through HMAC).

---

## 4. FE contract + minimal FE change

### 4.1 The mock signal (DECISION: `mock: bool` on `BillingCheckout`)

Add an optional `mock` boolean to the `BillingCheckout` payload. When the backend mock is
active, `subscribe()` → router sets `checkout.mock = True`.

**Backend — `iam/schemas.py` `BillingCheckout`** (add field after `tier`, line ~208):

```python
mock: bool = Field(
    default=False,
    description="DEV-ONLY. True when the dev mock granted entitlement synchronously "
                "(no real Razorpay object). The FE skips checkout.js and polls directly.",
)
```

**Backend — `billing_router.py` `billing_subscribe`** (the `BillingCheckout(...)` construction,
lines ~88-95): add `mock=settings.razorpay_mock_active`.

> Chose `mock: bool` over a sentinel `key_id="rzp_mock"` because (a) it is explicit and
> self-documenting, (b) it does not overload the public `key_id` field which the FE also logs,
> and (c) it survives a future change to the mock key naming.

### 4.2 FE model — `frontend/apps/mfe-billing/src/app/billing.model.ts`

Add to the `BillingCheckout` interface (after `tier`, line ~67):

```typescript
/** DEV-ONLY: backend already granted entitlement; skip checkout.js, poll directly. */
mock?: boolean;
```

### 4.3 FE branch point — `plans.component.ts` `subscribe()`

The single branch is at the `next:` handler (lines ~525-536). Wrap the `openWidget` call:

```typescript
this.billing.subscribe(tier).subscribe({
  next: (resp: BillingSubscribeResponse) => {
    // DEV-MOCK: backend granted entitlement synchronously — skip checkout.js,
    // go straight to PENDING + poll (the first poll flips to active).
    if (resp.checkout.mock) {
      this.checkoutState.set('pending');
      this._startPolling(tier);
      return;
    }
    this.checkoutState.set('checkout-open');
    void this.rzpCheckout.openWidget(resp.checkout).then((result: CheckoutResult) => {
      if (result.status === 'cancelled') {
        this.checkoutState.set('cancelled');
        this.activeTier.set(null);
        return;
      }
      this.checkoutState.set('pending');
      this._startPolling(tier);
    });
  },
  error: (err: BillingErrorShape) => {
    this._handleSubscribeError(err);
  },
});
```

**Everything else is identical.** The existing `_startPolling` → `pollUntilActivated` →
`GET /billing/subscription` flow is reused untouched. Because the backend granted entitlement
during `subscribe()`, the first poll returns the upgraded `entitlement` and the state machine
transitions `pending → activated` exactly as in the real flow. No change to
`razorpay-checkout.service.ts`, `billing-poll.util.ts`, the trial CTA, or cancel.

- **Cancel:** no FE change. `POST /billing/cancel` already returns `BillingCancelResponse`; the
  mock just makes the backend transition land synchronously. The FE re-reads status the same way.
- **Trial:** no FE change (no Razorpay involved either way).

---

## 5. Safety

1. **Production force-disable.** `settings.razorpay_mock_active` returns `False` whenever
   `APP_ENV == "production"`, regardless of `RAZORPAY_DEV_MOCK`. Every backend branch reads
   `razorpay_mock_active` (never the raw flag) AND every `_mock_drive_*` helper opens with
   `assert settings.razorpay_mock_active`. Mirrors the OTP-bypass `APP_ENV != "production"`
   guard exactly.
2. **No secrets in mock.** The mock path reads no `RAZORPAY_KEY_*`, no `RAZORPAY_PLAN_ID_*`, no
   `RAZORPAY_WEBHOOK_SECRET`. It never imports or constructs the `razorpay` SDK client.
3. **Never calls Razorpay.** `razorpay_mock.py` has zero `import razorpay`, zero `httpx`, zero
   `asyncio.to_thread`. A lint guard (grep) can assert `razorpay_mock.py` contains no network
   symbols.
4. **Clearly dev-only.** All ids are prefixed `sub_mock_` / `order_mock_` / `pay_mock_` /
   `evt_mock_`; the `short_url` host is `mock.razorpay.local`. Module + field docstrings say
   DEV-ONLY.
5. **Hermetic billing tests untouched.** The autouse hermetic fixtures in
   `tests/test_billing_routes.py` monkeypatch the real adapter and run with
   `RAZORPAY_DEV_MOCK` defaulting `False` → `razorpay_mock_active` is `False` → the `_rzp()`
   seam returns the real adapter → existing mock/monkeypatch behaviour is preserved. **Builders
   MUST add a dedicated mock-mode test that explicitly sets `RAZORPAY_DEV_MOCK=True` via
   `monkeypatch.setattr(settings, "RAZORPAY_DEV_MOCK", True)`** rather than relying on ambient
   env, so it does not leak into the other hermetic tests.
6. **Route inventory guard (`test_app_boot_integration.py`) untouched.** The mock adds **NO
   new route** — it reuses the existing 4 billing endpoints. Endpoint count stays at the merged
   value. Do NOT add a `/billing/mock/*` route.
7. **Celery include guard (`test_celery_app_include_list.py`) untouched.** The mock adds **NO
   new Celery task** — the synchronous replay happens inline in the request. `include=[...]`
   stays the locked 3 entries.
8. **`webhook_events` rows are synthetic but real-shaped** — `evt_mock_` prefix makes them
   trivially identifiable for a dev DB cleanup (`DELETE FROM webhook_events WHERE event_id LIKE
   'evt_mock_%'`).

---

## 6. Builder split & manual test

### 6.1 Who builds what

| Part | Specialist | Files |
|---|---|---|
| Config flag `RAZORPAY_DEV_MOCK` + `razorpay_mock_active` property + `.env.example` line | `meesell-services-builder` (owns `shared/config.py` shape changes via lead-reviewed PR; config is lead-owned root wiring — **lead authors the config field**, services-builder authors the service wiring) | `backend/app/shared/config.py`, `backend/.env.example` |
| Mock adapter module (6 methods) | `meesell-services-builder` | `backend/app/adapters/razorpay_mock.py` (new) |
| Service wiring: `_rzp()` seam, 3 call-site swaps, `_mock_drive_activation` / `_mock_drive_ltd_capture` / `_mock_drive_cancel` tails | `meesell-services-builder` | `backend/app/modules/iam/service.py` |
| `BillingCheckout.mock` schema field + router `mock=...` set | `meesell-api-routes-builder` | `backend/app/modules/iam/schemas.py`, `backend/app/modules/iam/billing_router.py` |
| Backend mock-mode test (flag ON, asserts plan grant via state machine) | `meesell-services-builder` | `backend/tests/test_billing_mock_mode.py` (new) |
| FE model `mock?: boolean` + `subscribe()` skip-modal branch | `meesell-angular-service-builder` (model is a shared DTO) + `meesell-angular-component-builder` (component branch) — coordinate via the frontend lead | `frontend/apps/mfe-billing/src/app/billing.model.ts`, `.../plans/plans.component.ts` |

> **Note on config ownership.** `backend/app/shared/config.py` is in the backend lead's
> root-wiring surface. Per the HYBRID dispatch rule the lead authors the single config field +
> property directly (docs/fast-mode chore), then dispatches `meesell-services-builder` for the
> adapter + service wiring (code-heavy). The schema/router field is `meesell-api-routes-builder`.
> FE changes route through the frontend lead via the standard cross-lead memo (a
> `handoff_contract_razorpay_dev_mock.md` memo should accompany this so the FE skip-modal branch
> is tracked on the frontend board).

### 6.2 Acceptance / manual test (founder runs locally)

Pre-req: `APP_ENV=development`, `FEATURE_BILLING_ENABLED=true`, `RAZORPAY_DEV_MOCK=true` in
`backend/.env`; backend running with `--reload`; FE billing remote rebuilt & served.

1. **Login.** Phone OTP, code `000000` (existing dev bypass) → authenticated.
2. **Subscribe (recurring).** Plans → "Subscribe" on Pro. Expect: **no Razorpay modal opens**;
   UI shows "processing your payment" (pending) briefly, then **flips to Pro active**. Verify
   `GET /api/v1/auth/me` → `plan="pro"`, `entitlement="pro"`. Verify shell sidebar reflects Pro.
3. **DB check (optional).** `subscriptions` row status `active`, `current_period_end` ~30d out;
   `users.plan='pro'`; one `audit_events` `billing.plan.granted`; one `webhook_events`
   `evt_mock_*`.
4. **Start trial (fresh user).** New phone → Plans → "Start free trial" → immediate Pro trial
   (`/auth/me` `plan="free"`, `entitlement="pro"`, `trial_ends_at` ~14d out). No Razorpay,
   no modal (already the case).
5. **Cancel.** With an active mock sub → "Cancel" → `status="cancel_scheduled"` /
   `cancel_scheduled=true`; `subscriptions` row `status='cancelled'`; entitlement stays Pro
   until period end (correct real behaviour). Verify a `billing.subscription.cancelled` audit row.
6. **LTD (if surfaced in UI).** Subscribe LTD → no modal → `plan="ltd"`, `entitlement="pro"`,
   `current_period_end=NULL`, a `payments` row, `billing.plan.granted` audit (`tier="ltd"`).
7. **Production guard smoke.** Set `APP_ENV=production` + `RAZORPAY_DEV_MOCK=true` in a throwaway
   env, boot, attempt subscribe → mock path is NOT taken (real adapter selected → 502 since no
   real Razorpay creds). Confirms force-disable. (Do this in a disposable env, not the dev DB.)

---

## 7. Open design questions (founder / lead to rule before build)

1. **Q1 — synthetic webhook_events rows in dev DB.** The spec writes real `evt_mock_*`
   `webhook_events` rows (§3.5). Acceptable to leave them as dev cruft (cleanup query provided),
   or do you want the mock to skip the dedupe-row write and call the per-event handler directly
   (loses the idempotency-path exercise but keeps the table clean)? **Recommendation: keep the
   row write** — it makes the mock a faithful end-to-end exercise of the real pipeline.

2. **Q2 — config field ownership.** I propose the lead authors the single `RAZORPAY_DEV_MOCK`
   field + `razorpay_mock_active` property directly (it is lead-owned `shared/config.py` root
   wiring), and `meesell-services-builder` does the adapter + service code. Confirm you are fine
   with the lead touching `config.py` in fast-mode rather than routing the field through a
   specialist PR.

3. **Q3 — should `update_subscription` (upgrade/downgrade) get a mock tail too?** The current
   billing UI/router does not expose plan-change (only subscribe/cancel/trial), and
   `update_subscription` is not called by any of the 4 endpoints. I left it as a pure mock fake
   with **no** synthetic webhook tail. If a future "change plan" UI lands, it will need its own
   `subscription.updated` replay. Confirm we scope the mock to subscribe/trial/cancel only for now.

4. **Q4 — `pollUntilActivated` timeout in mock.** Because the grant is synchronous, the first
   poll succeeds, so the existing poll timeout is irrelevant on the mock path. No change needed.
   Flagging only to confirm we are NOT shortening the poll interval for mock (we are not — the
   FE branch goes straight to `pending` + the unchanged poll, which resolves on attempt #1).
