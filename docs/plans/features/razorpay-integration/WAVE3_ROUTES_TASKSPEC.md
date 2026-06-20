# Wave 3 — Billing API Routes + Plan-Guard Entitlement Task Spec (Razorpay Integration, V1.5)

**Feature slug:** `razorpay-integration`
**Wave:** 3 of 5 (BILLING CONTRACT ENDPOINTS + ENTITLEMENT RESOLUTION + `MeResponse` WIDENING)
**Target specialists:** `meesell-api-routes-builder` (sonnet — routes + schemas) **AND** `meesell-auth-builder` (opus — `plan_guard`/entitlement + `MeResponse.plan`/`CurrentUser` widening). SEQUENCED — see §11.
**Session name (dispatch header):** `mesell-razorpay-integration-backend-session-3`
**Authored by:** `meesell-backend-coordinator` (HYBRID step 1 — spec only, no code)
**Date:** 2026-06-19
**Parent design (LOCKED):** `docs/plans/features/razorpay-integration/RAZORPAY_INTEGRATION_SPEC.md` rev v4 (APPROVED 2026-06-18) §3 (state machine), §3.7 (trial), §5 (adapter), §6 (API endpoints — THE WAVE-3 SOURCE OF TRUTH), §7.5/§7.4a (`trial_ends_at`), §14 Wave 3; `docs/PRICING_LOCKED.md` v2 §5 (tier caps) + §5.1 (trial schema).
**Predecessors (built):**
- Wave 1 — `WAVE1_DB_TASKSPEC.md` — 3 billing ORM models + migration `f8fa7a36383f` + `users.trial_ends_at` + `ck_users_plan`. Landed as PR #300 (founder-held to develop).
- Wave 2 — `WAVE2_ADAPTER_TASKSPEC.md` — adapter V1.5 surface (6 async methods + 3 frozen dataclasses) + idempotent webhook event router (11 handlers). Lives on branch `feature/razorpay-w2-adapter` tip `cb45f8e` (merge-gate PASS).

---

## 0. CRITICAL GROUND-TRUTH — read first (verified against the live tree 2026-06-19)

Five facts the design spec does NOT state correctly for Wave-3 execution. ALL verified against the live tree (`git show`/`git ls-tree` against the actual branches), not the dispatch summary.

1. **BRANCH: build STACKED on `feature/razorpay-w2-adapter` — NOT `develop`, NOT `feature/razorpay-integration/backend`.**
   The branch topology is a 3-way stack and is the #1 trap:
   - `feature/razorpay-integration/backend` tip = `7aca019` = **Wave 1 ONLY** (no Wave 2 adapter/router). Do NOT branch here — your route handlers that call `iam_service.create_subscription`/the adapter would not resolve.
   - `feature/razorpay-w2-adapter` tip = `cb45f8e` = **Wave 1 (squash `dd08a50` = PR #300) + Wave 2** (`adapters/razorpay.py` six async methods + `iam/service.py` webhook router). This is the Wave-3 base.
   - `develop` does NOT have Wave 1 or Wave 2 (the billing models, migration, adapter methods, and webhook router are all absent on develop — PR #300 is founder-held).
   **Cut Wave 3 directly on `feature/razorpay-w2-adapter` (continue the stack):** `git fetch origin && git checkout feature/razorpay-w2-adapter && git pull`. Before writing any import, confirm in your working tree that `backend/app/adapters/razorpay.py` contains `async def create_subscription`, `async def create_order`, `async def cancel_subscription`, `async def fetch_subscription` and that `backend/app/shared/models/{subscription,payment,webhook_event}.py` exist. If they do not, STOP and escalate to the lead — you are on the wrong branch.

2. **NO MIGRATION IN WAVE 3.** All schema Wave 3 needs already exists from Wave 1: `users.trial_ends_at`, the widened `ck_users_plan` CHECK (`free·starter·pro·pro_annual·business·business_annual·ltd`), and the 3 billing tables. Verified: the single alembic head on the `feature/razorpay-w2-adapter` chain is `f8fa7a36383f` (`935e55b4852c → a1b2c3d4e5f6 → f31c75438e61 → b7c2e1a9d3f4 → c2d3e4f5a6b7 → f8fa7a36383f`). **Do NOT create an Alembic revision.** If at your dispatch time you find you genuinely need a schema change (you should not), STOP and escalate — that is a Wave-1 gap and a re-gate, not a silent Wave-3 migration.

3. **`MeResponse.plan` and `CurrentUser.plan` are hard-coded `Literal["free"]` TODAY — and F7 changes HOW plan is read.** Verified live on the w2-adapter branch:
   - `iam/schemas.py` → `class MeResponse(BaseModel): ... plan: Literal["free"]`.
   - `iam/router.py` `me()` handler (~line 267) → `return MeResponse(... plan="free", # V1 narrow per §4.B CurrentUser ...)`. Hard-coded string, NOT sourced from the DB.
   - `core/auth.py` → `CurrentUser.plan: Literal["free"]`; `get_current_user(...)` hard-codes `plan_claim: Literal["free"] = "free"  # V1 narrow` and returns `CurrentUser(user_id=..., plan=plan_claim)`. The JWT `plan` claim is currently ignored (always set to "free" at issue too — `issue_access_token(..., plan="free")`).
   **Founder ruling F7 is decisive here: plan is read DB-FRESH, NOT from the JWT claim.** Therefore Wave 3 does NOT widen `CurrentUser.plan` to carry the real tier from the token. Instead, the **entitlement is resolved at the point of use** by reading the `users` row + `subscriptions` row + `trial_ends_at` fresh from the DB (see §6). The `/auth/me` handler resolves entitlement DB-fresh; `MeResponse.plan` widens to the full Literal but its VALUE comes from the DB, not the JWT. `CurrentUser.plan` MAY stay `Literal["free"]` as a vestigial advisory field OR be deprecated — the auth-builder decides, but it must NOT become the source of truth for gating (F7). Flag the chosen disposition in the PR.

4. **`core/plan_guard.py` is a free-only sliding-window/total-cap gate — it has NO tier dispatch today.** Verified: `enforce_plan_limit(user_id, plan: str, resource, requested=1, db=None)` accepts a `plan` arg but `if plan != "free": ... falls back to free`, and the only table is `V1_LIMITS_FREE = {product_count:(100,None), ai_autofill_hourly:(50,3600), smart_picker_hourly:(100,3600), create_product_hourly:(20,3600)}`. Wave 3 extends this to tier-aware entitlement resolution (§6). **DO NOT rip out the existing free-tier behaviour** — extend it.

5. **PRE-EXISTING DRIFT — `plan_guard` free `product_count` cap = 100, but PRICING_LOCKED v2 §5 says Free = 50 SKUs/mo.** This is a real, pre-existing inconsistency between `plan_guard.py` (`product_count:(100,None)`) and the locked pricing doc (Free = 50 SKUs/mo). It is NOT introduced by Wave 3. **Do NOT silently change it** — see §Risks (BE-PLANGUARD-FREECAP-1); it is a founder decision because the locked number is the authority and changing a live free-tier cap is a product/business call. Default for Wave 3: leave the free cap untouched (100) and ADD the new tier caps; flag the discrepancy to the lead for founder ruling. (If the founder rules at dispatch time, the auth-builder applies the ruled value.)

---

## 1. Scope of Wave 3 (exactly this, nothing more)

Per the design §6 (API endpoints) + §14 Wave 3, two coupled deliverables across two specialists:

**A) Billing API routes + Pydantic schemas (`meesell-api-routes-builder`)** — the four NEW contract endpoints under `/api/v1/billing/*` (the webhook route already exists from V1/Wave 2 and is NOT re-touched) + their request/response Pydantic models in `iam/schemas.py`, mounted on a new billing router (or the existing `iam_router` — see §3 decision), with `Depends(get_current_user)` + rate-limit decorators, OpenAPI regenerated. The route handlers call service functions (the service helpers `subscribe`/`start_trial`/`cancel`/`get_billing_status` are authored as part of this wave — see §3.5 ownership note).

**B) Entitlement resolution + `MeResponse`/plan widening (`meesell-auth-builder`)** — extend `core/plan_guard.py` to resolve entitlement from `(users.plan, subscriptions.status, current_period_end, users.trial_ends_at)` covering the `starter`/`pro`/`business`/annual/`ltd`/trial cases; widen `MeResponse.plan` Literal (sourced DB-fresh per F7); decide the `CurrentUser.plan` disposition (F7 — DB-fresh, not JWT); wire the `/auth/me` handler to surface plan/trial/subscription state for Wave 5 FE.

**Out of scope for Wave 3 (explicit — DO NOT build):**
- NO Alembic migration / model change — Wave 1 owns schema (see §0.2).
- NO webhook router changes, NO adapter method changes — Wave 2 owns those (`iam/service.py::capture_razorpay_webhook` + the per-event handlers + `adapters/razorpay.py` are FROZEN for this wave; you CALL the adapter methods from the new service helpers, you do not modify them).
- NO reconciliation Celery beat task, NO 14-day trial-expiry sweep — Wave 4 (lead). (The trial-expiry drop is already implicit in entitlement resolution — `plan_guard` compares `now()` to `trial_ends_at` live; the *sweep* that makes it observable is Wave 4. Wave 3 builds only the live comparison.)
- NO frontend, NO infra, NO legal, NO AI work.
- NO new `iam` typed exception unless genuinely unavoidable — see §7 (a 9th `iam` exception is a §7.G-LOCKED founder-gate item).
- NO change to the existing `enforce_plan_limit` CALL SITES in `catalog`/`category` services (those callers pass `plan` and `db` already; you extend the resolver, not the callers — though see §6.4 for how callers obtain the real plan now that F7 forbids the JWT claim).

---

## 2. Conventions to follow (verified against the live tree)

- **Route style** — match `iam/router.py`: `router = APIRouter(prefix="/api/v1", tags=[...])`; each handler `async def` with `Annotated[CurrentUser, Depends(get_current_user)]` + `Annotated[AsyncSession, Depends(get_db)]`; `@rate_limit(scope=..., limit=..., window=...)` from `app.core.middleware.rate_limit_mw` (NOTE the signature is `rate_limit(scope, limit:int, window:int)` — integer limit + integer window seconds, NOT the "3/h" string form the §7.B prose uses; verified at `iam/router.py:125`). `from __future__ import annotations`; stdlib → third-party → local import blocks.
- **Pydantic v2** — `iam/schemas.py` is the PRIVATE wire-shape surface per §16.C; add billing models there, export them in `__all__`. `model_config = ConfigDict(from_attributes=True)` where reading from ORM. Amounts in **paise** (F9) where money is surfaced.
- **Service style** — match `iam/service.py`: `async def` module functions (not a class), `logger = logging.getLogger(__name__)`, `AsyncSession` passed in, raise typed exceptions never raw strings. The new `subscribe`/`start_trial`/`cancel`/`get_billing_status` helpers live in `iam/service.py` alongside the Wave-2 webhook router (the iam module owns billing — design §Agent lineup).
- **Plan constant / config** — the `tier → RAZORPAY_PLAN_ID_*` map is read by the SERVICE/ROUTE layer, NOT the adapter (D-B; the adapter takes an opaque `plan_id: str`). Read plan-ids from `settings` (e.g. `settings.RAZORPAY_PLAN_ID_STARTER_MONTHLY`). **These settings fields likely do NOT exist yet** — see §5 (config) — propose them; the lead owns `config.py`/`requirements.txt` root-wiring.
- **Credentials/config via `settings` ONLY** — NEVER `os.getenv` (§19 import-linter rejects it under `app/`).
- **Cross-module discipline** — billing lives entirely in `iam` + reads `shared.models` + calls `adapters/razorpay` + uses `core/plan_guard`+`core/auth`. `iam` is the all-`✗` module in the §2.D matrix — **add NO new cross-module domain call** (no importing `catalog`/`category`/etc. service surfaces). The `/auth/me` handler's existing function-level `customer_service` import (for `onboarding_complete`) is the ONE sanctioned cross-module seam and is unchanged.
- **No secrets/PII in logs** — log `tier`/`event`/`user_id` only; never the Razorpay key, never customer email/phone/card.

---

## 3. Part A — Billing routes + schemas (`meesell-api-routes-builder`)

### 3.1 Router placement decision (DECISION — justified)

**Mount the billing endpoints on a NEW `billing_router = APIRouter(prefix="/api/v1", tags=["billing"])` in a new file `backend/app/modules/iam/billing_router.py`, exported from `iam/__init__.py` as `iam_billing_router`, and `include_router`'d in `main.py` next to `iam_router`.**

Justification: the existing `iam_router` owns auth (`/auth/*`, `/webhooks/razorpay`); billing is a distinct concern with its own `tags=["billing"]` OpenAPI group, and the google-auth feature already established the pattern of a SECOND router in the iam module (`iam_google_router`, mounted separately in `main.py` and feature-flag-gated). Mirror that pattern exactly. (Do NOT cram billing routes into the auth router — keep the OpenAPI tag clean for the FE.) If the builder judges a single `iam_router` cleaner, FLAG it — but default to the separate-router pattern that google-auth set.

**Feature flag:** add `FEATURE_BILLING_ENABLED` (bool, default per infra — recommend dev=True/staging+prod gated) and gate the `include_router(iam_billing_router)` in `main.py` exactly as google-auth gates `iam_google_router` (mount the router only when the flag is on). This keeps billing dark until Wave 0 (Razorpay plan-ids + KYC) clears. Propose the flag in `config.py` (lead-owned — see §5).

### 3.2 The four endpoints (EXACT, from design §6 — do NOT invent or rename)

All under `/api/v1`, all JWT-protected via `Depends(get_current_user)`. The webhook (`POST /api/v1/webhooks/razorpay`) is NOT in this wave — it exists already.

| # | Method + path | Auth | Rate limit (recommend) | Purpose |
|---|---|---|---|---|
| 1 | `POST /api/v1/billing/subscribe` | JWT | `scope="billing_subscribe", limit=10, window=3600` | Start a subscription (`starter`/`pro`/`business`/`pro_annual`/`business_annual` → Subscriptions API) OR an LTD purchase (`ltd` → Orders API). Returns the handle for the FE Razorpay Checkout widget. |
| 2 | `POST /api/v1/billing/start-trial` | JWT | `scope="billing_start_trial", limit=5, window=3600` | Start the 14-day app-side Pro trial (§3.7). NO Razorpay call. Idempotent: one trial per phone ever (409 if already used). |
| 3 | `POST /api/v1/billing/cancel` | JWT | `scope="billing_cancel", limit=10, window=3600` | Cancel the current subscription (at cycle end). |
| 4 | `GET /api/v1/billing/subscription` | JWT | none (read; per-IP DDoS floor) | Current subscription/plan/trial status. |

**None of the four is plan-gated** — a free user MUST be able to subscribe or start a trial. Do NOT wrap them in `enforce_plan_limit`. (The rate-limit decorators above are the only throttle; they prevent spam-creating Razorpay subscriptions / trial abuse.)

### 3.3 Request/response Pydantic schemas (`iam/schemas.py`)

Define these in `iam/schemas.py`, export in `__all__`. Tier vocabulary MUST match the locked set.

```
# ── Request models ──────────────────────────────────────────────
class BillingSubscribeRequest(BaseModel):
    tier: Literal["starter", "pro", "business", "pro_annual", "business_annual", "ltd"]
    # NOTE: "free" is NOT subscribable; the trial is a separate endpoint, NOT a tier here.

# start-trial and cancel take an EMPTY body — use no request model (or an empty BaseModel);
# do NOT require fields the design says are {}.

# ── Response models ─────────────────────────────────────────────
class BillingCheckout(BaseModel):
    """Handle the FE Razorpay Checkout widget needs."""
    key_id: str                          # settings.RAZORPAY_KEY_ID (public key — safe to expose)
    razorpay_subscription_id: str | None = None   # set for recurring tiers
    razorpay_order_id: str | None = None          # set for ltd
    short_url: str | None = None         # Razorpay-hosted checkout fallback (from create_subscription)
    amount_paise: int | None = None      # set for ltd order (display)
    currency: str = "INR"
    tier: str

class BillingSubscribeResponse(BaseModel):
    checkout: BillingCheckout
    # The actual entitlement grant happens via webhook (D-D) — this response is ADVISORY.

class BillingStartTrialResponse(BaseModel):
    trial_ends_at: datetime
    entitlement: Literal["pro"]          # the trial grants Pro-level entitlement

class BillingCancelResponse(BaseModel):
    status: Literal["cancelled"]
    entitled_until: datetime | None      # current_period_end; None only in odd states

class BillingSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    plan: Literal["free", "starter", "pro", "pro_annual", "business", "business_annual", "ltd"]
    status: str | None                   # subscriptions.status, or None if no sub row (free/trial)
    current_period_end: datetime | None  # None = perpetual (ltd) or no sub
    cancel_scheduled: bool
    tier_label: str                      # human label, e.g. "Pro", "Pro (Annual)", "Lifetime"
    trial_ends_at: datetime | None       # the §3.7 trial expiry; None if no trial
    entitlement: Literal["free", "starter", "pro", "business"]  # the EFFECTIVE entitlement (resolved)
```

The `entitlement` field on `BillingSubscriptionResponse` is the resolved EFFECTIVE tier (trial → "pro", ltd → "pro", annual → its base tier) and is the field the FE should gate UI on. It is computed by the entitlement resolver (Part B) and surfaced here. Coordinate the exact `entitlement` enum with the auth-builder so routes and resolver agree (this is the §11 sequencing dependency).

### 3.4 Handler behaviour per endpoint

1. **`POST /billing/subscribe`** — read `tier`. If a user already has an `active`/`authenticated`/`created` `subscriptions` row, reject with a typed conflict (see §7 — reuse `PlanLimitExceededError`? NO — that is 402; use a 409. The closest existing iam exception is none; default: return a domain conflict via the existing error machinery WITHOUT a new exception — see §7 decision). For `tier == "ltd"`: call `iam_service.subscribe(...)` which calls `adapter.create_order(amount=<ltd price paise from config>, ...)`, write a `subscriptions` row `{tier:'ltd', status:'created', razorpay_order_id:..., current_period_end:NULL}`, return `BillingCheckout` with `razorpay_order_id`+`amount_paise`. For recurring tiers: call `adapter.create_subscription(plan_id=<settings.RAZORPAY_PLAN_ID_* for tier>, notes={user_id, tier})`, write a `subscriptions` row `{tier, status:'created', razorpay_subscription_id:...}`, return `BillingCheckout` with `razorpay_subscription_id`+`short_url`. **The plan grant is NOT applied here** — it happens on the Wave-2 webhook (`subscription.activated`/`payment.captured`). This endpoint only initiates.
2. **`POST /billing/start-trial`** — idempotent one-per-phone. Reject 409 if the user (by verified phone identity) has ever had a trial OR currently has a non-null `trial_ends_at` OR has any non-free plan / active sub. On success set `users.trial_ends_at = now() + interval '14 days'`, write a business `audit_events` row (trial-start), return `BillingStartTrialResponse`. NO Razorpay call, NO `subscriptions`/`payments`/`webhook_events` row (§3.7).
3. **`POST /billing/cancel`** — look up the user's active/authenticated `subscriptions` row; if none → reject (404/409 — see §7). Call `adapter.cancel_subscription(sub_id, cancel_at_cycle_end=True)`; set `subscriptions.cancel_scheduled_at = now()`. The `status → cancelled` + eventual downgrade come via the Wave-2 `subscription.cancelled` webhook + Wave-4 sweep — this endpoint only requests the cancel and records `cancel_scheduled_at`. Return `BillingCancelResponse` with `entitled_until = current_period_end`.
4. **`GET /billing/subscription`** — read the user's row + latest `subscriptions` row + `trial_ends_at`; call the entitlement resolver (Part B) to compute `entitlement`+`tier_label`; return `BillingSubscriptionResponse`. No mutation.

### 3.5 Service-helper ownership (coordination)

The four endpoints need service helpers `subscribe`, `start_trial`, `cancel`, `get_billing_status` in `iam/service.py`. **These are authored in THIS wave** (they were NOT built in Wave 2 — Wave 2 built only the webhook router + adapter methods; verified `iam/service.py` has no `subscribe`/`start_trial`/`cancel` function). The api-routes-builder MAY author thin service helpers, OR they may be authored by the auth-builder alongside the entitlement resolver (since `start_trial`/`get_billing_status` are entitlement-adjacent). **DECISION:** api-routes-builder authors `subscribe`/`cancel` (Razorpay-adapter-calling, route-shaped); auth-builder authors `start_trial`/`get_billing_status` + the entitlement resolver (entitlement-shaped). Both touch `iam/service.py` — coordinate to avoid edit collisions (sequence per §11; auth-builder lands first so its resolver + `start_trial`/`get_billing_status` exist, then routes-builder adds `subscribe`/`cancel` + the routers).

### 3.6 OpenAPI

The four endpoints are NEW **contract** endpoints — they grow the §17 mounted-route count (currently 28 → 32). **Regenerate `openapi.json`** and review the diff (only the four new paths + their schemas should appear; the webhook route is unchanged). Paste the OpenAPI route-count delta in the PR.

---

## 4. Part B — Entitlement resolution + plan widening (`meesell-auth-builder`)

### 4.1 Entitlement resolver (`core/plan_guard.py`)

Add a pure resolution function that maps the raw billing facts to an effective entitlement, plus tier-aware limit tables. Recommended shape (refine names at build):

```
EffectiveEntitlement = Literal["free", "starter", "pro", "business"]

# tier → effective entitlement (annual/ltd/trial collapse to their feature-equivalent)
#   starter → "starter"; pro/pro_annual/ltd → "pro"; business/business_annual → "business"
#   trial (plan='free' + now()<trial_ends_at) → "pro"

async def resolve_entitlement(
    *, user_id: UUID, db: AsyncSession,
) -> EffectiveEntitlement:
    """DB-FRESH entitlement resolution (F7 — NOT from the JWT claim).

    Reads users.plan + users.trial_ends_at + the user's subscriptions row
    (status, current_period_end) and returns the EFFECTIVE entitlement.

    Resolution order (paid entitlement ALWAYS wins over trial — §3.7):
      1. If users.plan == 'ltd' (perpetual) → "pro".
      2. If users.plan in {pro, pro_annual} AND an active/within-period sub → "pro".
         If users.plan in {business, business_annual} AND active/within-period → "business".
         If users.plan == 'starter' AND active/within-period → "starter".
         (An active sub OR cancelled-but-current_period_end-in-future = entitled.
          A halted/expired sub OR past current_period_end with plan still set =
          treat as the live state — entitlement falls back to free for that sub;
          but note the webhook/sweep normally downgrades users.plan to 'free' on halt,
          so this branch is mostly defensive.)
      3. ELSE if users.plan == 'free' AND users.trial_ends_at is not None
         AND now() < users.trial_ends_at → "pro"  (the 14-day trial, §3.7).
      4. ELSE → "free".
    """
```

Then add tier-aware limit tables and a tier-aware `enforce_plan_limit`:

```
# Per PRICING_LOCKED v2 §5:
#   free      → product_count 50  (BUT see §0.5 / Risks BE-PLANGUARD-FREECAP-1: live code = 100;
#               DEFAULT: leave the existing free value untouched pending founder ruling)
#   starter   → product_count 150
#   pro       → product_count UNLIMITED (no cap)
#   business  → product_count UNLIMITED
#   AI hourly limits + smart_picker + create_product_hourly: same structure;
#     Q1 ruling — Starter gets the PRIORITY AI QUEUE too (same as Pro); the Starter→Pro
#     difference is PURELY the product_count cap (150 vs unlimited). So Starter's AI hourly
#     limits should match Pro's, NOT free's. Confirm the Pro AI hourly numbers with the
#     founder/PRICING — the locked doc states "all AI features" for Starter and "priority queue"
#     for both; it does NOT enumerate per-tier hourly AI numbers, so DEFAULT: keep the existing
#     free AI hourly limits as the floor and do NOT tighten paid tiers below free. Flag any
#     ambiguity rather than inventing numbers (see §7.G discipline).
```

**Extend `enforce_plan_limit` to be tier-aware:** keep the existing `(user_id, plan, resource, requested, db)` signature; when `plan` is a paid/entitled value, look up the tier's limit table instead of `V1_LIMITS_FREE`. **CRITICAL (F7):** the `plan` value passed to `enforce_plan_limit` by existing callers (catalog/category services) is today the JWT claim, which is hard-coded "free". Per F7 the truth is DB-fresh. Two options — pick and FLAG:
- **(a)** Resolve entitlement inside `enforce_plan_limit` (it already takes `db` for `product_count`) — ignore the passed `plan` arg, call `resolve_entitlement(user_id, db)` internally, gate on the resolved tier. Cleanest; callers do not change; matches F7 ("plan read DB-fresh"). **RECOMMENDED.** Requires `db` to be available at every call site (verify: `product_count` already requires `db`; the sliding-hour resources do not pass `db` today — if option (a) needs `db` for resolution on those too, the call sites must pass it. Audit the call sites and report).
- **(b)** Have callers resolve entitlement and pass the real tier in `plan`. More call-site churn; touches catalog/category which is borderline out-of-scope. NOT recommended.
Default to **(a)**; if a call site cannot supply `db`, FLAG the call-site list to the lead.

### 4.2 `MeResponse.plan` + `/auth/me` widening (F1 + F7)

- Widen `MeResponse.plan` from `Literal["free"]` to `Literal["free","starter","pro","pro_annual","business","business_annual","ltd"]` (the F1/v2 set).
- In the `me()` handler (`iam/router.py`), source `plan` from the user's REAL `users.plan` (DB-fresh — the handler already has `db` and calls `iam_service.get_profile`; add the real plan to that profile read OR read it in the handler). Do NOT keep the hard-coded `plan="free"`.
- ADD trial/subscription fields to `MeResponse` so the FE (Wave 5) can render plan state from `/auth/me` (the design §10 says FE polls `/auth/me` OR `/billing/subscription`). Add `trial_ends_at: datetime | None = None` and `entitlement: Literal["free","starter","pro","business"]` (the resolved effective entitlement) to `MeResponse`. This is the §17 presentation-contract surface — coordinate the field names with the FE handoff (§Hand-offs). **This is an additive change to an existing contract endpoint — note it in the PR as a `MeResponse` shape change (FE-coordination memo required).**

### 4.3 `CurrentUser.plan` disposition (F7)

Per F7 (plan NOT a JWT claim), `CurrentUser.plan: Literal["free"]` must NOT become the gating source of truth. Options — pick and FLAG:
- Leave `CurrentUser.plan` as-is (vestigial "free"), and never read it for gating (gating uses `resolve_entitlement(user_id, db)`). Lowest-risk; matches F7. **RECOMMENDED.**
- Remove `CurrentUser.plan` entirely (touches `issue_access_token`/`get_current_user`/the claim shape — a LOCKED §4.B surface; would need founder approval). NOT recommended for Wave 3.
Default to leaving it; document the choice in the PR. Do NOT widen the JWT `plan` claim to carry the real tier (that would re-introduce the JWT-as-truth pattern F7 rejects).

---

## 5. Config / dependency changes (root-wiring — lead-owned, propose in PR)

Wave 3 needs NEW config fields (propose exact lines in the PR; the lead applies/confirms in `config.py`):
- `RAZORPAY_PLAN_ID_STARTER_MONTHLY: str = ""`
- `RAZORPAY_PLAN_ID_PRO_MONTHLY: str = ""`
- `RAZORPAY_PLAN_ID_PRO_ANNUAL: str = ""`
- `RAZORPAY_PLAN_ID_BUSINESS_MONTHLY: str = ""`
- `RAZORPAY_PLAN_ID_BUSINESS_ANNUAL: str = ""`
- `RAZORPAY_LTD_PRICE_PAISE: int = 499900` (₹4,999 in paise; the LTD Orders-API price constant, D-B — config-pinned, no Razorpay Plan object).
- `FEATURE_BILLING_ENABLED: bool = True` (dev default; staging/prod gated by infra) — gates the billing router mount in `main.py` (§3.1).

`RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/`RAZORPAY_WEBHOOK_SECRET` already exist (verified `config.py:146-148`, in `REQUIRED_FIELDS`). The plan-id fields default to `""` and should NOT go in `REQUIRED_FIELDS` (billing is flag-gated; an empty plan-id fails loudly only when a real subscribe is attempted with the flag on — acceptable for dev). NO `requirements.txt` change (Razorpay SDK already pinned in Wave 2).

The `tier → settings.RAZORPAY_PLAN_ID_*` map lives in a single constant in `iam/service.py` (or a small `iam` pricing constant) so `PRICING_LOCKED.md §5` stays the single source of truth and config only carries opaque Razorpay IDs (D-B).

---

## 6. Plan-guard enforcement table (mapped to PRICING_LOCKED v2 §5)

The authoritative caps the resolver/limit-tables must encode (PRICING_LOCKED v2 §5, with the Q1/Q2 rulings):

| Effective entitlement | product_count (SKU) cap | Priority AI queue | AI hourly limits | Source |
|---|---|---|---|---|
| `free` | 50 (locked-doc) / **100 live-code drift — see §0.5 / Risks** | no | existing `V1_LIMITS_FREE` | PRICING v2 §5 (Free 50 SKUs/mo) |
| `starter` (= plan `starter`) | 150 | **YES** (Q1 ruling — Starter gets priority too) | ≥ free; recommend = pro AI limits (Q1: Starter→Pro diff is PURELY the SKU cap) | PRICING v2 §5 + Q1 |
| `pro` (= plan `pro`/`pro_annual`/`ltd`/trial) | UNLIMITED (no cap) | YES | "priority AI queue" | PRICING v2 §5 |
| `business` (= plan `business`/`business_annual`) | UNLIMITED | YES | + bulk ops (bulk-op gating is NOT a Wave-3 plan_guard resource — no bulk-op endpoint exists yet; do NOT invent one) | PRICING v2 §5 + Q2 (single-user at launch) |

Notes the builder MUST honour:
- **UNLIMITED = skip the `product_count` cap entirely for pro/business** (do NOT encode a huge sentinel that could still trip; branch on "unlimited" and return without enforcing).
- **Trial → pro entitlement** while `now() < trial_ends_at` even though `plan='free'` and there is NO `subscriptions` row (§3.7). Paid entitlement always wins over trial if both present.
- **Annual collapses to its base tier** for entitlement (`pro_annual`→pro, `business_annual`→business) — annual is a billing-cadence axis, not an entitlement axis.
- **LTD → pro, perpetual** (`current_period_end IS NULL` sentinel).
- The AI hourly numbers for paid tiers are NOT enumerated in PRICING_LOCKED — DEFAULT to NOT tightening below free and NOT inventing new numbers; if the resolver needs concrete paid AI limits, FLAG to the lead for a founder number rather than guessing (§7.G discipline).

---

## 7. Typed-exception taxonomy to use (DO NOT expand the LOCKED iam inventory without a founder gate)

`iam/exceptions.py` carries a §7.G-LOCKED inventory (verified: 11 classes today — Iam base + InvalidPhoneFormat, InvalidOtpFormat, MalformedWebhookPayload, OtpInvalid, OtpAttemptsExceeded, RefreshInvalid, WebhookSignatureInvalid, Msg91Unavailable, Google{TokenInvalid,EmailUnverified,Unavailable,IdentityConflict}). Adding a NEW billing exception (e.g. `AlreadySubscribedError` 409, `NoActiveSubscriptionError` 404/409, `TrialAlreadyUsedError` 409, `AdapterUnavailable` passthrough) touches that LOCKED section and is a **founder-gate item per repo management master plan §7.3**.

Decision for Wave 3:
- The `start-trial` 409 (already-trialed), `subscribe` 409 (already-subscribed), `cancel` 404/409 (no active sub) DO need a distinct status. **Default approach: reuse the existing `MeesellError` machinery WITHOUT new iam subclasses where possible** — but a clean 409 for "already subscribed / already trialed" has no existing iam class. **This wave WILL likely need 2-3 new iam exceptions.** Treat this as a §7.G founder-gate item: the auth-builder/routes-builder PROPOSES the new exception classes (name, status, `validation_message_id` 3-segment key per §5A.H) in the PR, and the LEAD carries them to the founder gate. Do NOT silently add them; do NOT block the build on it — propose, flag, and the lead adjudicates at the merge gate.
- A `RazorpayAdapterError` raised by `create_subscription`/`create_order`/`cancel_subscription` inside a billing route MUST surface as the adapter's 502 envelope (it already maps via `MeesellError`); do NOT swallow it — a Razorpay outage on subscribe should be a clean 502 to the FE, which retries.
- New `validation_message_id` keys (e.g. `billing.already_subscribed`, `billing.trial_already_used`, `billing.no_active_subscription`) MUST follow the §5A.H 3-segment regex and be registered in `i18n/messages_en.py` (the same gap that bit auth/validation keys before — see master memory `finding-i18n-generic-missing-gap`). Register every new key.

---

## 8. Test requirements (must exist AND pass)

New test file(s): `backend/tests/test_billing_routes.py` (route tests) + extend/`test_plan_guard.py` (entitlement-resolution tests). Follow existing `tests/` conventions (rolled-back `AsyncSession` fixture; `pytestmark` integration where DB needed; conftest `*_test`-DB guard). Mock the Razorpay adapter (patch the lazy singleton / the adapter functions) so NO real Razorpay call is made — assert the adapter is CALLED with the right `plan_id`/`amount`, return a fake `RazorpaySubscription`/`RazorpayOrder` dataclass.

Required coverage:

**Routes (api-routes-builder):**
1. `POST /billing/subscribe` recurring tier (`pro`) → adapter `create_subscription` called with `settings.RAZORPAY_PLAN_ID_PRO_MONTHLY` + `notes={user_id,tier}`; a `subscriptions` row written `{tier:'pro', status:'created'}`; response carries `razorpay_subscription_id`+`short_url`+`key_id`. NO plan grant yet (`users.plan` unchanged).
2. `POST /billing/subscribe` `ltd` → adapter `create_order` called with `RAZORPAY_LTD_PRICE_PAISE`; `subscriptions` row `{tier:'ltd', status:'created', razorpay_order_id:..., current_period_end:NULL}`; response carries `razorpay_order_id`+`amount_paise`.
3. `POST /billing/subscribe` annual (`pro_annual`) → uses `RAZORPAY_PLAN_ID_PRO_ANNUAL`.
4. `POST /billing/subscribe` when an active sub already exists → 409 (the proposed `AlreadySubscribedError` or equivalent).
5. `POST /billing/start-trial` first time on a free user → `users.trial_ends_at` set ~14 days out, business `audit_events` row written, response `entitlement="pro"`; NO Razorpay call (assert adapter NOT called); NO `subscriptions`/`payments`/`webhook_events` row.
6. `POST /billing/start-trial` second time (already trialed / `trial_ends_at` set) → 409, idempotent (no second grant).
7. `POST /billing/cancel` with an active sub → adapter `cancel_subscription(cancel_at_cycle_end=True)` called; `cancel_scheduled_at` set; response `entitled_until=current_period_end`. (Status stays — the `cancelled` transition is webhook-driven.)
8. `POST /billing/cancel` with no active sub → 404/409.
9. `GET /billing/subscription` for free / trial / active-pro / ltd / cancelled-but-current users → correct `plan`/`status`/`entitlement`/`trial_ends_at`/`cancel_scheduled`/`current_period_end`.
10. All four routes require auth → 401 without a valid JWT.
11. Rate-limit decorators present (smoke: the decorator is applied; full rate-limit behaviour is covered by the existing rate_limit_mw tests).
12. `FEATURE_BILLING_ENABLED=False` → the billing router is NOT mounted (the four paths 404). Mirror the google-auth flag-gate test.

**Entitlement (auth-builder):**
13. `resolve_entitlement` truth table — free→free; starter active→starter; pro active→pro; pro_annual active→pro; business active→business; business_annual→business; ltd (current_period_end NULL)→pro; free+trial-active→pro; free+trial-expired→free; pro active + trial set → pro (paid wins); halted sub → free; cancelled sub before period end → still entitled; cancelled after period end → free.
14. `enforce_plan_limit` tier-aware — starter user at 150 products → 151st blocked (`PlanLimitExceededError`); pro user at 150 products → NOT blocked (unlimited); free user behaviour UNCHANGED from before (regression guard on the existing free path).
15. `/auth/me` returns the real `plan` (DB-fresh, not "free") for a non-free user + `trial_ends_at` + `entitlement`; returns `plan="free"`+`entitlement="free"` for a plain free user; returns `entitlement="pro"`+`plan="free"` for a trialist (the F7 DB-fresh proof — the JWT claim is still "free" but the response is not).
16. Regression: existing `/auth/me` fields (`onboarding_complete`, `user_id`, `phone`) unchanged; existing `enforce_plan_limit` free call sites still pass.

CI: Gates 1 (unit), 2 (smoke), 3 (lint) MUST be green. Gate 4 (integration) result pasted in PR "Test evidence". Paste the actual pytest run output. Regenerated OpenAPI route-count delta pasted (28 → 32).

---

## 9. Branch + PR

- **Branch:** continue on / branch off `feature/razorpay-w2-adapter` (the Wave-2 branch — STACKED, per §0.1). `git fetch && git checkout feature/razorpay-w2-adapter && git pull` first. Two specialists, two PRs — sequence per §11; the routes PR stacks on the entitlement PR (both target the integration flow). Confirm the exact target with the lead before opening (Wave 1/2 are founder-held; the lead will direct whether Wave 3 targets `feature/razorpay-w2-adapter` directly or a fresh integration branch). Default per design §Branch setup: group-branch → integration-branch → develop (founder gate).
- **PR template:** fill `.github/PULL_REQUEST_TEMPLATE/backend.md` COMPLETELY — no `<>` placeholders. Required: state "NO migration this wave" with the verified single head (`f8fa7a36383f`); list modules/files touched; contract changes in commit body (FOUR new `/billing/*` contract endpoints + `MeResponse` shape widened — OpenAPI regenerated, route count 28→32); cross-module check (billing is `iam`-only — confirm NO new `✗→✓` in §2.D; `iam` is the all-`✗` module); Test evidence pasted; "Session" block = `mesell-razorpay-integration-backend-session-3`.
- **First commit footer** carries the session name.
- **On PR open:** the specialist sets the `feature_board_backend.md` razorpay-integration row to `IN REVIEW` and clears `Current session` (per D2). The lead then runs the merge-gate review (HYBRID step 3).
- **OpenAPI:** REGENERATE (four new endpoints + `MeResponse` change). Review + paste the diff.

---

## 10. Files the builders will create/modify

**`meesell-api-routes-builder` (Part A):**
- CREATE `backend/app/modules/iam/billing_router.py` — the four `/billing/*` route handlers.
- MODIFY `backend/app/modules/iam/__init__.py` — export `iam_billing_router`.
- MODIFY `backend/app/modules/iam/schemas.py` — add the 6 billing Pydantic models + `__all__`.
- MODIFY `backend/app/modules/iam/service.py` — add `subscribe` + `cancel` service helpers (Razorpay-adapter-calling).
- MODIFY `backend/app/main.py` — `include_router(iam_billing_router)` gated on `FEATURE_BILLING_ENABLED` (lead-owned root-wiring — propose; the lead applies/confirms the `main.py` + flag).
- MODIFY `backend/app/modules/iam/exceptions.py` — PROPOSE the 2-3 new billing exceptions (§7 — founder-gate item, flag to lead).
- MODIFY `backend/app/i18n/messages_en.py` — register the new `billing.*` validation_message_id keys.
- CREATE `backend/tests/test_billing_routes.py`.
- REGENERATE `backend/app/openapi.json` (or wherever the committed OpenAPI lives — verify the path).

**`meesell-auth-builder` (Part B):**
- MODIFY `backend/app/core/plan_guard.py` — `resolve_entitlement` + tier-aware limit tables + tier-aware `enforce_plan_limit`.
- MODIFY `backend/app/modules/iam/schemas.py` — widen `MeResponse.plan` + add `trial_ends_at`/`entitlement` (COORDINATE with routes-builder — both edit schemas.py; sequence per §11).
- MODIFY `backend/app/modules/iam/router.py` — `me()` handler sources `plan`/`entitlement`/`trial_ends_at` DB-fresh.
- MODIFY `backend/app/modules/iam/service.py` — add `start_trial` + `get_billing_status` service helpers (COORDINATE with routes-builder).
- MODIFY `backend/app/core/auth.py` — `CurrentUser.plan` disposition decision (§4.3 — default: leave as-is, document).
- MODIFY/EXTEND `backend/tests/test_plan_guard.py` (or the existing plan_guard test file) — entitlement truth table + tier-aware enforcement.
- CONFIG proposals (lead applies): the `RAZORPAY_PLAN_ID_*` + `RAZORPAY_LTD_PRICE_PAISE` + `FEATURE_BILLING_ENABLED` fields in `config.py` (§5).

**Lead-owned root-wiring (propose, lead applies at merge gate):** `backend/app/config.py` (the 7 new settings), `backend/app/main.py` (the gated `include_router`).

---

## 11. Dispatch sequencing (the lead's step-2 plan)

**SEQUENCE, do not parallelize blindly** — both specialists edit `iam/schemas.py` AND `iam/service.py`, and routes depend on the entitlement-resolution contract:

1. **First: `meesell-auth-builder`** — lands `resolve_entitlement` + tier limit tables + tier-aware `enforce_plan_limit` + `MeResponse` widening + `/auth/me` rewire + `start_trial`/`get_billing_status` service helpers + the `EffectiveEntitlement` enum. This establishes the entitlement contract the routes consume.
2. **Then: `meesell-api-routes-builder`** — stacks on the auth-builder's commit; adds the `billing_router` + the 6 request/response schemas (consuming the now-defined `entitlement` enum) + `subscribe`/`cancel` service helpers + the `main.py` gated mount + OpenAPI regen + the new exceptions/i18n keys.
3. **Then: lead merge-gate review (HYBRID step 3)** — one combined review of the stacked Wave-3 contribution, or two sequential reviews; the lead decides. Founder owns integration→develop (D1).

Rationale: the `BillingSubscriptionResponse.entitlement` and `MeResponse.entitlement` fields are produced by the resolver — routes can't shape them until the resolver's enum exists. Sequencing auth-builder first avoids a contract-drift round-trip.

---

## 12. Acceptance criteria (the lead's merge-gate checklist for this PR)

- [ ] Four `/billing/*` contract endpoints exist EXACTLY per §3.2 (paths/verbs unchanged from design §6); none plan-gated; all `Depends(get_current_user)`; subscribe/start-trial/cancel rate-limited.
- [ ] Billing router mounted via the google-auth second-router pattern, gated on `FEATURE_BILLING_ENABLED`; flag-off → four paths 404 (test §8.12).
- [ ] `subscribe` calls the RIGHT adapter method per tier (`create_subscription` for recurring with the correct `RAZORPAY_PLAN_ID_*`; `create_order` for `ltd` with `RAZORPAY_LTD_PRICE_PAISE`); writes a `created`-status `subscriptions` row; does NOT grant the plan (grant is webhook-driven, D-D).
- [ ] `start-trial` is app-side only (NO Razorpay call — asserted), idempotent one-per-phone (409 on repeat), sets `trial_ends_at`, writes a trial-start `audit_events` row, no `subscriptions`/`payments`/`webhook_events` row.
- [ ] `cancel` calls `cancel_subscription(cancel_at_cycle_end=True)`, sets `cancel_scheduled_at`, returns `entitled_until`; status transition stays webhook-driven.
- [ ] `GET /billing/subscription` returns correct resolved state for free/trial/starter/pro/annual/ltd/cancelled.
- [ ] `resolve_entitlement` truth table correct (§8.13) — paid wins over trial; annual→base; ltd→pro perpetual; trial→pro while live, free after; halted/expired→free.
- [ ] `enforce_plan_limit` tier-aware (§8.14): starter 150 cap, pro/business unlimited (skip cap), free path UNCHANGED (regression). Plan read DB-FRESH per F7 (not the JWT claim) — option (a) used or call-site list flagged.
- [ ] `MeResponse.plan` widened to the F1/v2 Literal AND sourced DB-fresh (not hard-coded "free"); `trial_ends_at`+`entitlement` added; existing `/auth/me` fields unchanged. FE-coordination memo flagged (MeResponse shape change).
- [ ] `CurrentUser.plan` disposition decided + documented (default: left vestigial, NOT a gating source — F7); JWT `plan` claim NOT widened to carry the real tier.
- [ ] NO new Alembic migration; NO model change; head still `f8fa7a36383f`. NO webhook-router/adapter change (Wave 2 frozen). NO reconciliation/trial-sweep (Wave 4).
- [ ] New iam exceptions (if any) PROPOSED + flagged as §7.G founder-gate items (NOT silently added); new `billing.*` i18n keys registered (3-segment, §5A.H) in `messages_en.py`.
- [ ] Config fields (7) proposed for lead application; no `os.getenv`; credentials/plan-ids from `settings`.
- [ ] OpenAPI regenerated; route count 28 → 32; diff shows ONLY the four new paths + schemas (+ MeResponse change).
- [ ] Cross-module: billing is `iam`-only (+ `shared.models` + `adapters/razorpay` + `core`); NO new `✗→✓` in §2.D.
- [ ] Tests §8.1-16 present and PASSING; CI Gates 1/2/3 green; Gate 4 result pasted; OpenAPI delta pasted.
- [ ] PR template fully filled; session block = `mesell-razorpay-integration-backend-session-3`; board row `IN REVIEW`; branch/target coordination with the lead confirmed (§9).
- [ ] No secrets/PII in logs; zero out-of-scope changes.

---

## 13. Risks / founder decisions needed before (or carried through) the build

| # | Item | Owner / gate |
|---|---|---|
| **R1 — BE-PLANGUARD-FREECAP-1** | `plan_guard` free `product_count` cap = **100** in live code but PRICING_LOCKED v2 §5 says Free = **50** SKUs/mo. Pre-existing drift, NOT Wave-3-introduced. Changing a live free-tier cap is a product/business call. **FOUNDER decision needed.** Default: Wave 3 leaves the free cap at 100, adds the new tier caps, and flags this for a founder ruling. | Founder (via lead). NOT a build blocker. |
| **R2 — paid-tier AI hourly numbers** | PRICING_LOCKED enumerates SKU caps + "priority AI queue" but NOT per-tier hourly AI generation limits. The resolver needs concrete numbers if it tightens/loosens AI limits per tier. Q1 says Starter = Pro for AI. **Default: do NOT invent numbers — keep existing free AI limits as the floor, do not tighten paid below free; flag any concrete-number need.** | Founder (via lead) IF concrete paid AI numbers are required. |
| **R3 — new iam exceptions (9th+)** | `subscribe`/`start-trial`/`cancel` need 409/404 semantics with no existing iam class. Adding iam exceptions touches the §7.G-LOCKED inventory → §7.3 founder-gate. **Propose in PR, lead carries to founder.** | Founder (via lead) at merge gate. |
| **R4 — `MeResponse` contract shape change** | Widening `MeResponse.plan` + adding `trial_ends_at`/`entitlement` changes a LIVE contract endpoint the FE consumes. Additive (safe-ish) but the FE (Wave 5) must adopt the new fields and must NOT break on the widened `plan` Literal. **FE-coordination memo required** (`handoff_contract_razorpay.md`). | Backend↔FE memo (lead authors at PR-merge). |
| **R5 — Wave 0 infra (build vs test)** | Live `subscribe` needs `RAZORPAY_PLAN_ID_*` SM secrets + Razorpay dashboard Plan objects (Wave 0, infra/founder). The BUILD + all tests (mocked adapter) do NOT need them — Wave 3 can build and pass CI fully mocked. Only LIVE end-to-end subscribe testing is blocked on Wave 0. **Not a build blocker; flag that live verification is staging-gated on Wave 0.** | Infra/Founder (Wave 0) — for live test only. |
| **R6 — F7 call-site `db` availability** | Option (a) (resolve entitlement inside `enforce_plan_limit`) needs `db` at every call site; the sliding-hour resources may not pass `db` today. **Auth-builder audits the call sites; if any cannot supply `db`, flag the list to the lead.** | Lead (review call-site audit). NOT a founder gate. |
| **R7 — branch/target with Wave 1/2 founder-held** | Wave 1 (#300) + Wave 2 are NOT on develop (founder-held). Wave 3 stacks on `feature/razorpay-w2-adapter`. The eventual integration→develop merge order (Wave1→2→3) is the founder's to sequence. **Lead confirms the PR target before the specialist opens it.** | Lead (branch coordination). |

---

## 14. Memory / handoff protocol

- This spec's path + the branch-stack fact + R1 (free-cap drift) are appended to `meesell-backend-coordinator` MEMORY.md at dispatch.
- At step-2 dispatch the lead flips the `feature_board_backend.md` razorpay-integration row to `IN PROGRESS` with `Current session=mesell-razorpay-integration-backend-session-3` and adds a session-start STATUS_BACKEND block.
- Cross-lead memo owed at PR-merge: `handoff_contract_razorpay.md` to `meesell-frontend-coordinator` (the `/billing/*` contract + the `MeResponse` shape change + the async-truth polling rule from design §10). NOT owed now (spec-authoring step).
