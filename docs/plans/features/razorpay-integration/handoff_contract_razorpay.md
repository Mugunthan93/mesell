# Backend → Frontend contract memo — Razorpay billing (Wave 3)

**From:** meesell-backend-coordinator (backend lead)
**To:** meesell-frontend-coordinator (frontend lead)
**Date opened:** 2026-06-19
**Integration branch:** `feature/razorpay` (tip after Wave 3 squash-merge of PR #309 = `692345b`)
**Status:** OPEN — FE work tracked separately; integrates into `feature/razorpay` (NOT develop).
**Source of truth:** `docs/plans/features/razorpay-integration/RAZORPAY_INTEGRATION_SPEC.md` (rev v3),
`docs/PRICING_LOCKED.md` (v2), and the live code on `feature/razorpay`
(`backend/app/modules/iam/billing_router.py`, `.../schemas.py`, `.../exceptions.py`,
`backend/app/core/plan_guard.py`).

---

## 0. Flags & staging-gating (read first)

- **All 4 billing endpoints are gated behind `FEATURE_BILLING_ENABLED`.** `main.py` only
  `include_router(billing_router)` when the flag is on. In **dev the flag defaults True**;
  in staging/prod it is off until **Wave 0** clears (Razorpay plan-ids + KYC).
- **Razorpay plan IDs are empty until Wave 0.** `RAZORPAY_PLAN_ID_*` config fields exist but
  are unpopulated, so `POST /billing/subscribe` cannot produce a live checkout handle on
  staging/prod yet. **Live checkout is staging-gated** — build the FE flows now, but do not
  expect a working Razorpay widget on staging until Wave 0 founder checklist completes.
- The trial endpoint (`start-trial`) is **app-side only** (no Razorpay object, no charge) and
  works in dev today behind the same flag.
- FE should **feature-flag the billing UI** to mirror `FEATURE_BILLING_ENABLED` so the billing
  surface stays dark on environments where the routes are not mounted (a call to an unmounted
  route returns 404, not the documented 4xx).

---

## 1. `/auth/me` (`MeResponse`) contract change — ACTION REQUIRED

`GET /api/v1/auth/me` response was widened in Wave 3. This is a **non-breaking superset** —
existing fields are unchanged; `plan` gained more allowed values and two new optional fields
were added. The FE `AuthUser` / `MeResponse` model and the `@mesell/core` `AuthService` user
shape must be updated.

### 1.1 `plan` Literal — WIDENED

Previously `Literal["free"]` (V1 stub). Now the full Pricing-v2 vocabulary:

```
plan: "free" | "starter" | "pro" | "pro_annual" | "business" | "business_annual" | "ltd"
```

`plan` is the **raw** plan stored on `users.plan` (DB-fresh per founder ruling F7 — read from
the DB, not the JWT claim). The FE should generally **NOT** gate features directly on `plan`
(annual cadences and ltd/trial complicate it) — gate on `entitlement` (§1.3) instead.

### 1.2 NEW field: `trial_ends_at`

```
trial_ends_at: string | null   // nullable ISO-8601 UTC timestamp, e.g. "2026-07-03T09:15:00Z"
```

- `null` when the user has no active or past trial.
- When non-null and in the future → the user is in a **live 14-day Pro trial**; the FE should
  show a countdown ("Pro trial — N days left") and a "Subscribe to keep Pro" CTA.
- The trial **auto-drops to Free at expiry** with **no Razorpay object and no charge** — there
  is no webhook and no card. After expiry `trial_ends_at` may remain set (a past timestamp) but
  `entitlement` will have collapsed back to `"free"`.

### 1.3 NEW field: `entitlement` — the field to gate UI on

```
entitlement: "free" | "starter" | "pro" | "business"   // default "free"
```

This is the **RESOLVED effective tier** computed by `core.plan_guard.resolve_entitlement`. It
is a **4-value collapse** of the 7-value `plan` plus the trial state:

| Raw `plan` / state            | `entitlement` |
|-------------------------------|---------------|
| `free` (no live trial)        | `free`        |
| `free` + live trial           | `pro`         |
| `starter`                     | `starter`     |
| `pro`                         | `pro`         |
| `pro_annual`                  | `pro`         |  ← annual → base
| `business`                    | `business`    |
| `business_annual`             | `business`    |  ← annual → base
| `ltd`                         | `pro`         |  ← LTD = Pro-for-life

**Collapse rules:** annual cadences collapse to their base tier (`pro_annual → pro`,
`business_annual → business`); `ltd` and a live trial both resolve to `pro`. A paid plan
ALWAYS wins over a trial.

**FE guidance:** gate feature visibility and SKU caps on `entitlement`, not `plan`. Use `plan`
only for the billing/subscription-management screen (to show the exact cadence the user pays).

> Note: `entitlement` is also returned on `GET /api/v1/billing/subscription` (§2.4) with the
> same semantics, and on the trial-start response (§2.2, always `"pro"`).

---

## 2. New billing endpoints (4)

All under `/api/v1/billing`, all require auth (`Authorization: Bearer <access JWT>` per the
existing FE-D5 split-token flow). All gated behind `FEATURE_BILLING_ENABLED` (§0).
**None is plan-gated** — a `free` user must be able to subscribe or start a trial.

### 2.1 `POST /api/v1/billing/subscribe` — start a subscription or LTD purchase

- **Rate limit:** 10/h per user.
- **Request body:**
  ```json
  { "tier": "pro" }
  ```
  `tier` ∈ `"starter" | "pro" | "pro_annual" | "business" | "business_annual" | "ltd"`.
  (`"free"` is NOT subscribable.) Recurring tiers → Razorpay Subscriptions API; `ltd` →
  Razorpay Orders API (one-time).
- **Response `201`** (`BillingSubscribeResponse`):
  ```json
  {
    "checkout": {
      "key_id": "rzp_test_xxx",                       // Razorpay public key — safe to expose
      "razorpay_subscription_id": "sub_xxx | null",   // set for recurring tiers
      "razorpay_order_id": "order_xxx | null",        // set for LTD
      "short_url": "https://rzp.io/... | null",       // hosted-checkout fallback
      "amount_paise": 49900,                          // integer paise, may be null
      "tier": "pro"                                   // echoes request
    }
  }
  ```
  The FE hands `key_id` + `razorpay_subscription_id`/`razorpay_order_id` to the Razorpay
  Checkout widget (or opens `short_url` as a fallback).
- **IMPORTANT — plan is NOT granted on this call.** `users.plan` stays unchanged; the plan
  grant lands later via the Razorpay webhook (`subscription.activated` / `payment.captured`,
  Wave 2). After the widget closes, the FE should **poll `GET /billing/subscription`** (§2.4) /
  re-fetch `/auth/me` to observe the grant rather than assuming success on widget-close.
- **Errors:** `409 billing.subscription.already_active` (§3); `502` if Razorpay is unavailable.

### 2.2 `POST /api/v1/billing/start-trial` — start the 14-day app-side Pro trial

- **Rate limit:** 5/h per user.
- **Request body:** none (empty `POST`).
- **Response `200`** (`BillingStartTrialResponse`):
  ```json
  {
    "trial_ends_at": "2026-07-03T09:15:00Z",  // absolute UTC expiry (now + 14 days)
    "entitlement": "pro"                       // always "pro" for a live trial
  }
  ```
  App-side only — **no Razorpay call, no charge.** Sets `users.trial_ends_at`. The FE should
  display a Pro-trial countdown after this succeeds and re-hydrate the auth user.
- **Errors:** `409 billing.trial.already_used` (§3) — one trial per phone; also fires if the
  user already holds a non-free plan or a live subscription (redundant trial).

### 2.3 `POST /api/v1/billing/cancel` — cancel at end of billing cycle

- **Rate limit:** 10/h per user.
- **Request body:** none (empty `POST`).
- **Response `200`** (`BillingCancelResponse`):
  ```json
  {
    "status": "cancel_scheduled",              // always this literal on success
    "entitled_until": "2026-07-19T00:00:00Z"   // current_period_end; entitlement kept until then; may be null
  }
  ```
  Schedules `cancel_at_cycle_end=True`. The subscription stays active until `entitled_until`;
  the final `status → cancelled` transition is webhook-driven (`subscription.cancelled`,
  Wave 2). **LTD cannot be cancelled** — it is a perpetual one-time purchase (founder-ratified:
  LTD-cancel = block/perpetual); attempting to cancel a non-subscription returns the 404 below.
- **Errors:** `404 billing.subscription.none_active` (§3); `502` if Razorpay is unavailable.

### 2.4 `GET /api/v1/billing/subscription` — current billing/plan/trial status

- **Rate limit:** none (read-only; per-IP DDoS floor only).
- **Request:** none.
- **Response `200`** (`BillingSubscriptionResponse`), DB-fresh (F7):
  ```json
  {
    "plan": "pro",                              // raw users.plan (7-value Literal, same as §1.1)
    "status": "active | null",                  // Razorpay sub status (active/authenticated/created/cancelled/...)
    "current_period_end": "2026-07-19T00:00:00Z | null",
    "cancel_scheduled": false,                  // true once cancel-at-cycle-end is set
    "tier_label": "Pro",                        // human-readable label for display
    "trial_ends_at": "2026-07-03T09:15:00Z | null",
    "entitlement": "pro"                        // RESOLVED effective tier — gate UI on THIS (§1.3)
  }
  ```
  This is the canonical screen for the billing/subscription-management page. Poll it after a
  subscribe widget closes to detect the webhook-driven grant.

---

## 3. New error responses + i18n keys — FE MUST HANDLE

All errors use the locked envelope shape (`backend/app/core/errors.py`):

```json
{
  "detail": "Human-readable resolved message",
  "code": "iam.<slug>",
  "validation_message_id": "billing.<key>"
}
```

The FE should switch on `validation_message_id` (the i18n key) for user-facing copy, not on
`detail`. All three keys are **seeded in `backend/app/i18n/messages_en.py`**.

| HTTP | `code`                       | `validation_message_id` (i18n)      | Raised by      | FE handling |
|------|------------------------------|-------------------------------------|----------------|-------------|
| 409  | `iam.trial_already_used`     | `billing.trial.already_used`        | `start-trial`  | "You've already used your Pro trial." Hide/disable the start-trial CTA; offer Subscribe instead. |
| 409  | `iam.already_subscribed`     | `billing.subscription.already_active` | `subscribe`  | "You already have an active subscription." Redirect to the subscription-management page (§2.4). |
| 404  | `iam.no_active_subscription` | `billing.subscription.none_active`  | `cancel`       | "Nothing to cancel." Treat as a no-op; refresh the billing screen. |

Additional non-billing-specific statuses the FE should already handle generically: `401`
(re-auth via the existing FE-D5 refresh flow), `429` (rate-limited — back off / show "try again
shortly"), `502` (Razorpay upstream unavailable — "Payments are temporarily unavailable").

---

## 4. Coordination notes

- **Founder-gate provenance:** the 3 new iam exceptions above ADD to the `§7.G`-LOCKED iam
  inventory and were **founder-ratified** as part of the Wave 3 gate (along with 7 config
  fields, Free=50 SKU cap, and LTD-cancel = block/perpetual). They are now integrated on
  `feature/razorpay`.
- **`§17` endpoint inventory:** the 4 billing endpoints are flag-gated and therefore do **not**
  change the mounted-endpoint count while `FEATURE_BILLING_ENABLED` is off. When the flag flips
  on (Wave 0+), the inventory grows by 4 — that count change rides the founder gate, not this
  memo.
- **No develop merge implied by this memo.** `feature/razorpay` is the integration branch; the
  single founder gate remains `feature/razorpay → develop`. FE billing work should target
  `feature/razorpay` (or a `feature/razorpay/<group>` child) per the branch model.
- **Open dependency for live checkout:** Wave 0 (Razorpay dashboard plan-ids + KYC) must clear
  before `subscribe` returns a usable checkout handle on staging/prod. Until then, FE can build
  and test the flows in dev (flag default True), but the Razorpay widget will not transact on
  staging.

— meesell-backend-coordinator, 2026-06-19
