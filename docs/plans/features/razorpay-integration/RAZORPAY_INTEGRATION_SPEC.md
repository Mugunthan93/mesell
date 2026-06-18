# Feature Spec — Razorpay Subscriptions + Billing (V1.5)

**Feature slug:** `razorpay-integration`
**Session:** `mesell-razorpay-integration-planning-session-1`
**Date authored:** 2026-06-18
**Status:** **APPROVED DESIGN — execution gated on Wave 0** (founder ruled F1–F10 on 2026-06-18; §7.3 architecture amendment APPROVED). The deferral amendment is accepted; the V1.5 billing build is unlocked once the Wave 0 hard-blocker list (see "Wave 0 prerequisites") clears.
**Output of session:** This document. No production code, config, migration, or other doc was modified.

---

## Decision Log (founder-ruled 2026-06-18)

The 10 open decisions in §13 were ruled by the founder on **2026-06-18**. Summary (full text + consequences recorded inline in §13, now marked DECIDED):

| # | Ruling | Notes |
|---|---|---|
| **F1** | **ACCEPTED** — plan vocabulary = `free · pro · pro_annual · business · business_annual · ltd` | `ltd` is included because Lifetime ships at launch (F2). |
| **F2** | **OVERRIDE** of "defer LTD" — **Lifetime Deal SHIPS AT LAUNCH (Wave 1).** | The one-time Orders-API path for LTD is IN SCOPE from the start; build phasing re-sequenced (§14). |
| **F3** | **7-day money-back guarantee + pro-rated monthly.** | Locked as the policy the implementation + legal copy must reflect. |
| **F4** | **Upgrade = immediate (pay the difference now); downgrade = at end of current paid period.** | |
| **F5** | **Razorpay-generated GST invoices for V1.5** (Director default). | meesell-legal-writer flagged to CONFIRM this satisfies Indian GST/compliance obligations. |
| **F6** | **YES — annual tiers launch alongside monthly.** | |
| **F7** | **Plan read DB-fresh, NOT a JWT claim** (Director default). | Touches LOCKED §4.B/§7; part of the §7.3 amendment (F10). |
| **F8** | **Trust Razorpay's retry window; downgrade only on `halted`.** | No separate fixed grace period. |
| **F9** | **Amounts in paise, Razorpay-native; default to the official Razorpay Python SDK** over raw httpx unless a concrete reason is noted. | |
| **F10** | **§7.3 architecture amendment APPROVED.** | Spec status flipped to APPROVED DESIGN — execution gated on Wave 0. |

---

## Wave 0 prerequisites — HARD BLOCKER LIST (must clear before any code dispatch)

**No `feature/razorpay-integration/backend` branch is cut and no specialist is dispatched until ALL of the following are GREEN.** These are owner-assigned, non-code, and gate Wave 1. (Restated in build phasing §14 Wave 0.)

1. **[INFRA] Populate `RAZORPAY_WEBHOOK_SECRET` GCP Secret Manager version.** The SM container exists with NO version (`k8s/secrets.yaml.example:73-80`, exact `gcloud secrets versions add razorpay-webhook-secret` command inline). HARD blocker for any webhook testing. This is the webhook *signing* secret — DISTINCT from `RAZORPAY_KEY_SECRET` (§9).
2. **[FOUNDER/INFRA] Create Razorpay dashboard Plan objects + `RAZORPAY_PLAN_ID_*` config — now including the annual + lifetime SKUs.** One Plan per recurring tier×interval: `pro_monthly`, `pro_annual`, `business_monthly`, `business_annual` → `RAZORPAY_PLAN_ID_PRO_MONTHLY` / `_PRO_ANNUAL` / `_BUSINESS_MONTHLY` / `_BUSINESS_ANNUAL`. LTD (`ltd`) uses the Orders API (no Plan object) but its **price constant** (₹4,999 → paise) must be config-pinned. Plan IDs created in the dashboard (D-B), mirrored as opaque strings in config + SM.
3. **[INFRA] Register the webhook URL in the Razorpay dashboard** pointing at `https://<env>/api/v1/webhooks/razorpay`, subscribed to the full §4.1 event list (now including `payment.captured` for the LTD path). One per env; dev needs a publicly reachable URL (tunnel) or a staging-first test posture.
4. **[LEGAL] Finalize the 7-day refund policy text (F3) + Razorpay KYC pack.** Publish refund/ToS/privacy URLs over HTTPS (Razorpay KYC hard requirement, `LEGAL §5.1`). The 7-day money-back + pro-rated-monthly variant (F3) is the SELECTED policy — legal-writer adopts that variant. KYC pack: entity = OPC, legal name = Stellaxis, PAN=GST=bank exact name-match (`LEGAL §5.2`) gates activation (1–3 day, `LEGAL §5.3`).
5. **[LEGAL] GST-invoicing confirmation.** Founder defaulted to Razorpay-generated GST invoices for V1.5 (F5). meesell-legal-writer must CONFIRM this satisfies Indian GST/compliance obligations (SAC 998314, `LEGAL §6`) before charges go live. If legal flags a gap, escalate to founder before Wave 3 (the contract surface that would carry invoice metadata).

**Drives:** `meesell-backend-coordinator` (+ 4 backend specialists) · `meesell-frontend-coordinator` · `meesell-legal-writer` · `meesell-infra-builder`
**Prerequisite for:** the entire paid-tier business model (Pro ₹499/mo, Business ₹1,999/mo, LTD ₹4,999 one-time, optional annual ₹4,990/yr per `PRICING_LOCKED.md §5`). Until this lands, every seller is on `plan='free'` forever and the platform earns ₹0.

---

## Deferral amendment (read first)

Razorpay's full subscription / payment business logic was **deliberately LOCKED as deferred-to-V1.5** in three places:

- `MVP_ARCHITECTURE.md §14` (V1.5 list): *"Razorpay billing + tiered plans (free/pro divergence in product caps and AI rate limits — see §9.9)"*.
- `MVP_ARCHITECTURE.md §1.E` posture: V1 surface is webhook-capture-only (signature-verify + log).
- `backend/app/adapters/razorpay.py` header: *"Subscription / payment business logic is deferred to V1.5 per §1.E + MVP_ARCH §14. This adapter exposes exactly one synchronous helper for HMAC signature verification."* The adapter further notes the V1.5 surface (`create_subscription` / `cancel_subscription` / `get_customer`) will follow the §6.G typed-exception pattern via `RazorpayAdapterError`, which is already defined in `adapters/__init__.py` for forward compatibility.

**This spec is now founder-APPROVED (2026-06-18); it AMENDS that deferral and unlocks the V1.5 billing build.** Approval of this document was the trigger. It does NOT itself write code. Nothing in V1's capture-only posture is removed — the V1 webhook surface is *evolved* into an event router, not replaced (see §4, §5).

Because `BACKEND_ARCHITECTURE.md §6` (adapters) and §7 (`iam` module) are **LOCKED sections**, the adapter-surface additions in §5 and the `iam`-router additions in §6 required a founder-approved architecture amendment per repo management master plan §7.3 before any specialist is dispatched. **That amendment is APPROVED (F10, 2026-06-18.)** Execution remains gated on the Wave 0 hard-blocker list (see "Wave 0 prerequisites"). (Rulings recorded in the Decision Log + §13.)

---

## Pre-flight reality check (verified against the live tree, not the dispatch summary)

The execution dispatch summary contained two assumptions that the live code **does not** support. Both are corrected here so the build does not start from a false premise:

1. **`users` table has NO `razorpay_sub_id` and NO `plan_expires_at` columns.** The dispatch said *"User model has a razorpay_sub_id column."* It does not. Verified at `backend/app/shared/models/user.py` (lines 34–98) and `MVP_ARCHITECTURE.md §2.1` DDL — the `users` table is exactly `{id, phone, email, plan, created_at, last_login_at}`. `plan` is `VARCHAR(20) DEFAULT 'free'` with a comment `"free | pro"`. There is **no** subscription-id column, **no** expiry column anywhere in the 13-table schema. The billing data model (§7) is therefore net-new, not a column-addition to an existing billing surface.

2. **The V1 webhook does NOT persist anything.** The dispatch implied capture writes an audit row. It does **not**. `iam/service.py::capture_razorpay_webhook` (lines 590–644) verifies the signature, JSON-parses, then **only `logger.info(...)`s** — it returns `audit_event_id=0` as an explicit placeholder. The reason is a documented two-fold DDL conflict: `audit_events.user_id` is `NOT NULL` (a webhook has no user) and there is **no `payload_jsonb` column** (the live DDL has `diff_jsonb` + `metadata_jsonb`). This is logged in the service docstring as *"a §7.B.6 vs §11.2 DDL conflict that needs a V1.5 resolution (audit_events.user_id NULLability, or a separate webhook_events table)."* **This spec resolves it with a dedicated `webhook_events` table (§7) — not by relaxing `audit_events.user_id`.**

Other verified ground truth:

- **Config is wired.** `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` all exist in `backend/app/shared/config.py` (lines 146–148) and are listed in `REQUIRED_FIELDS` (lines 62–64). `RAZORPAY_WEBHOOK_SECRET` defaults to `""`.
- **Secret container exists, has no version.** `k8s/secrets.yaml.example` (lines 73–80): `razorpay-webhook-secret` SM container is CREATED but has NO VERSION — explicit FOUNDER ACTION REQUIRED with the exact `gcloud secrets versions add` command inline. `razorpay-key-id` / `razorpay-key-secret` ARE populated (`MVP_ARCH §16` secret table line ~2930).
- **Adapter surface is one sync function.** `verify_webhook_signature(payload, signature, *, secret=None) -> bool` — HMAC-SHA256, constant-time compare, never raises. Two LOCKED exceptions documented in its header (sync-not-async per §6.E; returns-bool-not-raises per §6.G).
- **`RazorpayAdapterError`** already exists in `adapters/__init__.py` (lines 80–87), `code="razorpay.unavailable"`, status 502, inherits `AdapterError → MeesellError`. Pre-wired for the V1.5 surface — the build does not invent it.
- **`/api/v1/webhooks/razorpay`** is mounted (router prefix `/api/v1`, path `/webhooks/razorpay`), reads RAW bytes (NOT JSON-parsed at dependency layer), and is counted as an INFRASTRUCTURE surface, NOT a contract endpoint (`MVP_ARCH §3` line ~317, and the 29-route reconciliation at line ~2653: "27 contract endpoints + 2 infrastructure: `/auth/me` + `/webhooks/razorpay`"). New billing endpoints in §6 are **contract** endpoints and grow that count.
- **Alembic head is `f31c75438e61`** (baseline `935e55b4852c` → pg_trgm/GIN `a1b2c3d4e5f6` → `f31c75438e61`). Single head. Confirmed live.
- **Plan field is binary today.** `users.plan ∈ {free, pro}` per the column comment and `MeResponse.plan: Literal["free"]` (the `/auth/me` response hard-codes `plan="free"` at `iam/router.py:265` — V1 narrow). Business + LTD + annual tiers in `PRICING_LOCKED.md` have **no plan-string representation yet** — that vocabulary is net-new (§3, §7, and founder decision F1).

---

## Decisions

**Update 2026-06-18:** the founder has ruled F1–F10 (see Decision Log near the top + §13). The recommended positions below now read against those rulings; the only material override was **F2 — LTD ships at launch (Wave 1), not deferred** (D-A's "confirm LTD deferred" caveat is resolved IN FAVOUR of shipping). The locked-doc-derived positions below remain the spec's design rationale.

### D-A — Razorpay product: Subscriptions API for recurring; Orders API for LTD

**Recommendation (LOCKED-doc-derived, needs founder ratify — see F2):**

- **Pro (₹499/mo), Business (₹1,999/mo), annual (₹4,990/yr)** → **Razorpay Subscriptions API.** Recurring auto-debit (UPI AutoPay / e-mandate / card mandate) is exactly what Razorpay Subscriptions is built for, and `PRICING_LOCKED.md §2.1` already models the cost as *"Razorpay subscription module — 2% per txn"*. Subscriptions give us first-class `subscription.charged` / `.halted` / `.cancelled` lifecycle events, native dunning (retry on failed auto-debit), and a Razorpay-hosted mandate flow that keeps card data out of our system (PCI scope minimisation).
- **LTD (₹4,999 one-time)** → **Razorpay Orders API (one-time payment).** LTD is a single charge, not recurring. A Subscription with a 1-cycle plan is an anti-pattern; use a plain Order + `payment.captured` webhook → set `plan='ltd'` permanently. (Founder decision F2: confirm LTD ships in the first billing wave or is deferred — `PRICING_LOCKED.md` caps LTD at 1,000 spots, a scarcity lever the founder may want held back.)

**Why not Orders-only for everything:** one-time Orders would force us to build our own monthly re-charge scheduler, mandate management, and dunning — re-implementing the exact machinery Razorpay Subscriptions provides. Rejected.

### D-B — Razorpay Plan IDs created in the Razorpay dashboard, mirrored in config (not API-created)

**Recommendation (needs founder ratify):** Create the Razorpay Plan objects (one per billing tier × interval) **in the Razorpay dashboard**, then store their `plan_id` strings in config (`RAZORPAY_PLAN_ID_PRO_MONTHLY`, etc.) — do **not** create Plans via API at runtime. Rationale: plans change rarely, prices are founder-locked, and dashboard-created plans are auditable + KYC-linked. Runtime plan creation invites drift and accidental price changes. This mirrors the existing pattern where `RAZORPAY_KEY_ID` etc. are config-sourced, never `os.getenv` (per §6.G adapter rule). The plan→price map lives in a single backend constant (`pricing/` or `iam/` domain) so `PRICING_LOCKED.md §5` is the single source of truth and config only carries the opaque Razorpay IDs.

### D-C — Plan vocabulary expansion is required and is the first migration

**Recommendation (needs founder ratify — see F1):** `users.plan` must widen from `{free, pro}` to the full locked tier set. Proposed canonical plan strings:

`free` · `pro` · `pro_annual` · `business` · `business_annual` · `ltd`

Plus a separate **subscription status** concept (active / past_due / cancelled / expired — see §3 state machine) that is NOT the same axis as the plan tier. A user's *entitlement* = `(plan, subscription_status)`. The `MeResponse.plan: Literal["free"]` hard-code and the `users.plan` comment `"free | pro"` both become stale and must be widened (founder decision F1 confirms the exact string set, since `PRICING_LOCKED.md` does not name the strings).

### D-D — Webhook is the source of truth for plan state; checkout response is advisory

**Recommendation (LOCKED — payment-systems best practice, not negotiable):** A successful checkout/return from the frontend NEVER directly mutates `users.plan`. **Only a signature-verified, idempotency-checked webhook** transitions plan state. The checkout-initiation endpoint creates the Razorpay subscription/order and returns the handle for the frontend's Razorpay Checkout widget; the *actual* entitlement grant happens when `subscription.charged` / `subscription.activated` / `payment.captured` arrives via webhook. This is the only safe design: the client is untrusted, the webhook is signed. (This is why §4 is the heart of the spec.)

### D-E — Reuse the V1 signature verifier verbatim; evolve the handler, not the adapter's verify path

**Recommendation (LOCKED — preserves the §6.E locked exception):** The existing `verify_webhook_signature()` (sync, returns bool, never raises) is correct and stays **byte-for-byte unchanged**. The V1.5 work *adds* sibling async methods to the adapter (`create_subscription`, etc., which DO follow the typed-exception §6.G pattern), and *evolves the service layer* `capture_razorpay_webhook` from "log only" into a dispatching event router. The verify-then-parse ordering (verify RAW bytes BEFORE json.loads) is preserved exactly.

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-database-builder` | `shared/models/subscription.py`, `shared/models/payment.py`, `shared/models/webhook_event.py` ORM models + Alembic migration (parent = `f31c75438e61`); widen `users.plan` comment/CHECK; **NO** column added to `users` for sub-id (subscription row FK's to user instead — see §7) |
| | `meesell-services-builder` (primary, opus) | `adapters/razorpay.py` V1.5 async methods (`create_subscription`/`cancel_subscription`/`fetch_subscription`/`get_customer`/`create_order`) per §6.G; `modules/iam/service.py` evolution of `capture_razorpay_webhook` → event router + the per-event state-machine handlers; reconciliation Celery beat task; budget/entitlement write-back |
| | `meesell-api-routes-builder` | `modules/iam/router.py` new billing endpoints (§6) + `schemas.py` billing Pydantic models; OpenAPI regen; per-route `Depends(get_current_user)` + rate-limit decorators |
| | `meesell-auth-builder` | `core/plan_guard.py` extension: entitlement resolution from `(plan, subscription_status)`; widen `MeResponse.plan` Literal; any JWT-claim plan-embedding decision (see F7) |
| `meesell-frontend-coordinator` | (FE specialists) | Checkout/upgrade UI surface, Razorpay Checkout widget integration, plan-management page, cancel flow. **Flagged only — not designed here (§10).** |
| `meesell-legal-writer` | — | Refund/cancellation policy go-live text, Razorpay KYC pack finalisation, DPA sub-processor list confirmation. **Flagged only — not designed here (§11).** Note: most of this is ALREADY DRAFTED (see §11). |
| `meesell-infra-builder` (standalone) | — | `RAZORPAY_WEBHOOK_SECRET` SM version population, webhook URL registration in Razorpay dashboard, new `RAZORPAY_PLAN_ID_*` secrets, K8s env-var injection. **Flagged only (§12).** |

**AI track:** NO work — billing has zero AI call sites (`iam` is the all-`✗` module per `BACKEND_ARCHITECTURE.md §2.D` cross-module matrix; billing inherits that).
**Data track:** NO work — no XLSX/scraper surface.

---

## Scope

### In scope (what this unlocks)

1. Recurring subscription lifecycle for Pro / Business / annual via Razorpay Subscriptions API.
2. One-time LTD purchase via Razorpay Orders API (subject to F2).
3. Webhook event router: signature-verified, idempotent, replay-safe, out-of-order-tolerant handling of the full subscription + payment event set (§4).
4. Plan entitlement state machine driving `users.plan` + a new `subscriptions` table status (§3).
5. New data model: `subscriptions`, `payments`, `webhook_events` (§7).
6. Billing API endpoints: subscribe/checkout-init, cancel, current-status (§6).
7. V1.5 adapter methods following the §6.G async + typed-error pattern (§5).
8. Reconciliation job for webhook-loss / DB-divergence recovery (§8).
9. Dunning + grace-period handling (§3.5).

### Out of scope (stays deferred / future)

- **Proration math on mid-cycle upgrade/downgrade** beyond what Razorpay computes natively — see F4.
- **Admin billing UI** — `MVP_ARCH §14` keeps admin as read-only SQL in V1; a billing admin panel is V1.5+ and not built here. Refunds in V1.5 are issued from the **Razorpay dashboard manually**, with our system reacting to the resulting `refund.processed` webhook.
- **GST invoice generation** — Razorpay can emit GST invoices; whether we rely on that or generate our own is F5. The legal-writer has an invoice template drafted (§11) but the *automated* emit pipeline is out of this spec's build unless F5 says otherwise.
- **Team-account seat billing** — `PRICING_LOCKED.md` Business tier mentions "up to 5 seats" but `teams` table is V1.5+ per `MVP_ARCH §14`. Business tier in this spec is single-user-with-Business-entitlements; multi-seat billing is a later wave.
- **Tax/TDS, dunning email content** — email copy is legal-writer's; the *trigger* is in scope, the *content* is not.

---

## Detailed design

### 3. Subscription lifecycle state machine

Razorpay Subscription objects move through these states (Razorpay vocabulary): `created → authenticated → active → {pending → halted} → {cancelled | completed | expired}`. We mirror a **derived MeeSell entitlement** in our own `subscriptions` table so we never have to round-trip Razorpay to answer "is this user paid right now?".

#### 3.1 State table

| Razorpay subscription status | Our `subscriptions.status` | `users.plan` effect | Entitlement (can use paid features?) |
|---|---|---|---|
| `created` | `created` | unchanged (still prior plan) | NO — mandate not yet authorised |
| `authenticated` | `authenticated` | unchanged | NO — mandate authorised, first charge pending |
| `active` (first `charged`) | `active` | **set to target tier** | YES |
| `active` (renewal `charged`) | `active` | unchanged (already on tier) | YES — extend `current_period_end` |
| `pending` (a charge failed, retrying) | `past_due` | unchanged (grace) | YES during grace window (§3.5), then NO |
| `halted` (all retries exhausted) | `halted` | **downgrade to `free`** at grace end | NO |
| `cancelled` (user or system cancel) | `cancelled` | stays on tier until `current_period_end`, then `free` | YES until period end, then NO |
| `completed` (fixed-count plan ended) | `completed` | downgrade to `free` | NO (not used for our open-ended monthly plans; relevant only if F2 LTD-as-1-cycle is chosen — it is not) |
| `expired` | `expired` | downgrade to `free` | NO |

LTD (Orders path) is NOT a subscription — on `payment.captured` for an LTD order, set `users.plan='ltd'` permanently with no `current_period_end`. LTD has its own `subscriptions` row with `status='active'` and `current_period_end=NULL` (sentinel for "perpetual"). **Per F2 (DECIDED 2026-06-18), LTD ships at launch (Wave 1)** — this path is in scope from the first build wave.

#### 3.2 Transitions and triggers

Every transition is driven by a **webhook event** (§4), never by an API call from our frontend. The mapping event→transition is the §4 table. Internally:

- `subscribe` endpoint creates the Razorpay subscription (status `created`) and writes our `subscriptions` row with `status='created'`. No entitlement yet.
- `subscription.authenticated` webhook → `authenticated`.
- `subscription.activated` + first `subscription.charged` → `active` + grant entitlement + set `current_period_end` from the event payload.
- `subscription.charged` (renewal) → extend `current_period_end`; write a `payments` row.
- `subscription.pending` → `past_due`; start grace timer (§3.5).
- `subscription.halted` → `halted`; on grace expiry, downgrade to `free`.
- `subscription.cancelled` → `cancelled`; entitlement persists until `current_period_end`, then a reconciliation/cron sweep (§8) downgrades to `free`.

#### 3.3 Upgrade (e.g. Pro → Business)

Razorpay supports `update` on a subscription (change plan). Recommendation: call `subscription.update` with the new `plan_id`; Razorpay handles proration per its own rules (F4 decides whether we accept Razorpay's default proration or force change-at-period-end). On the resulting `subscription.charged` (or `subscription.updated`) webhook, set `users.plan` to the new tier. Entitlement on upgrade is **immediate** (better tier now); the charge difference is Razorpay's proration.

#### 3.4 Downgrade (e.g. Business → Pro)

Recommendation: downgrade takes effect at `current_period_end` (the user paid for Business this cycle; they keep it until the cycle ends). Schedule the plan change with Razorpay (`subscription.update` with `schedule_change_at: cycle_end`). `users.plan` does not change until the `subscription.charged` at the new tier arrives. F4 confirms.

#### 3.5 Renewal-failure (dunning) + grace period

When auto-debit fails, Razorpay moves the subscription to `pending` and retries on its own schedule (Razorpay default: several retries over ~N days — confirm exact retry cadence at build against Razorpay's then-current docs). We mirror as `past_due` and **keep the user entitled during a grace window** (recommendation: grace = until Razorpay halts, i.e. we trust Razorpay's retry window rather than inventing our own). On `subscription.halted` we end grace → downgrade to `free`. Dunning *emails* are triggered here (content = legal-writer / FE; trigger = backend). F8 confirms grace policy.

#### 3.6 Cancel

User-initiated cancel (§6 `cancel` endpoint) calls `adapter.cancel_subscription(sub_id, cancel_at_cycle_end=True)`. Razorpay emits `subscription.cancelled`. Per refund policy (`LEGAL §4.3`: *pro-rated cancellation for monthly, 7-day window for first purchase / LTD*), the **default is cancel-at-cycle-end** (no immediate refund); the user keeps entitlement until `current_period_end`. Immediate-refund cancels (within the 7-day window) are handled manually from the Razorpay dashboard in V1.5 (out of scope per §Scope), with our system reacting to `refund.processed`.

### 4. Webhook event handling

This is the security- and correctness-critical core. The V1 `capture_razorpay_webhook` (log-only) **evolves into an event router** (D-E). The route, signature verification, and RAW-bytes-before-JSON ordering are all preserved.

#### 4.1 Events to subscribe to (in the Razorpay dashboard)

| Razorpay event | Handler action |
|---|---|
| `subscription.authenticated` | `subscriptions.status → authenticated` |
| `subscription.activated` | `status → active`; grant entitlement; set `current_period_end` |
| `subscription.charged` | upsert `payments` row; extend `current_period_end`; ensure `status=active` (renewal heartbeat) |
| `subscription.pending` | `status → past_due`; start grace (§3.5); trigger dunning email |
| `subscription.halted` | `status → halted`; on grace end → `users.plan='free'` |
| `subscription.cancelled` | `status → cancelled`; keep entitlement until period end |
| `subscription.completed` | `status → completed` → downgrade (not expected for open-ended plans) |
| `subscription.updated` | apply plan change (upgrade/downgrade landing) |
| `payment.captured` | for LTD Orders: `users.plan='ltd'`; write `payments` row |
| `payment.failed` | log + `payments` row `status=failed`; informs dunning |
| `refund.processed` | write `payments` refund row; if full refund of an active sub → downgrade per policy (F3) |

(Exact event-name strings must be confirmed against Razorpay's then-current webhook docs at build time — Razorpay occasionally adds/renames events. The handler MUST ignore unknown event types gracefully, returning 200 so Razorpay does not retry an event we don't model.)

#### 4.2 Idempotency (event-id dedupe)

Every Razorpay webhook carries a unique event id (`x-razorpay-event-id` header / `id` in payload). The handler:

1. Verify signature (existing `verify_webhook_signature`, RAW bytes) → 401 on fail (preserved V1 behaviour, `WebhookSignatureInvalidError`).
2. Parse JSON → 400 on malformed (`MalformedWebhookPayloadError`, preserved).
3. **`INSERT ... ON CONFLICT (event_id) DO NOTHING` into `webhook_events`.** If the row already existed (conflict), this event was already processed → return 200 immediately, do nothing else. This is the dedupe gate.
4. Dispatch to the per-event handler inside the SAME transaction as the `webhook_events` insert, so "recorded" and "applied" commit atomically. If the handler raises, the whole tx rolls back (including the dedupe insert) → Razorpay retries → we reprocess cleanly. (This makes the dedupe insert + state mutation a single atomic unit — critical.)
5. Mark `webhook_events.processed_at = NOW()` on success.

#### 4.3 Ordering / out-of-order handling

Razorpay does not guarantee event ordering. Guards:

- Plan-state transitions are written **idempotently and monotonically** where possible: e.g. `subscription.charged` setting `current_period_end` uses `GREATEST(current_period_end, new_end)` so a late-arriving older `charged` cannot rewind the period.
- `subscription.cancelled` arriving before a stray late `charged` must not re-activate: the handler checks current status — a `cancelled` sub stays cancelled; a late `charged` only extends the period if status is still `active`/`past_due`.
- Each handler reads the current `subscriptions.status` and applies a guarded transition (the §3.1 table is the allowed-transition matrix); illegal transitions are logged and no-op'd (return 200).

#### 4.4 Replay safety

The §4.2 dedupe makes replays free — a replayed event hits the `ON CONFLICT DO NOTHING` and returns 200 without side effects. We also store the FULL raw payload in `webhook_events.payload_jsonb` (the column V1 lacked — see §7) so a buggy handler version can be fixed and events **reprocessed from our own store** without re-fetching from Razorpay (this was the V1 capture-only intent per `iam/service.py` docstring lines 603–605; now actually realised).

#### 4.5 Signature verification reuse

`verify_webhook_signature(raw_body, signature, secret=settings.RAZORPAY_WEBHOOK_SECRET)` — unchanged, sync, constant-time. The webhook secret MUST be the dashboard webhook signing secret (the pending SM version, §12), NOT `RAZORPAY_KEY_SECRET`. These are different secrets — a common integration bug. Flagged in §9.

### 5. Adapter surface (V1.5 additions to `adapters/razorpay.py`)

All new methods are **async** and **raise `RazorpayAdapterError`** on transport failure / non-2xx (§6.G typed-error pattern), in deliberate contrast to the two LOCKED V1 exceptions (the sync bool-returning `verify_webhook_signature`). Credentials come from `settings` only (no `os.getenv`, §6.G + §19 import-linter). Lazy singleton SDK client (Razorpay Python SDK or httpx — F9).

| Method | Signature (proposed) | Purpose |
|---|---|---|
| `create_subscription` | `async def create_subscription(*, plan_id: str, customer_notify: bool, total_count: int \| None, notes: dict) -> RazorpaySubscription` | Create a recurring subscription (returns sub id + short_url for checkout) |
| `create_order` | `async def create_order(*, amount: int, currency: str, receipt: str, notes: dict) -> RazorpayOrder` | One-time LTD order |
| `fetch_subscription` | `async def fetch_subscription(sub_id: str) -> RazorpaySubscription` | Reconciliation (§8) — pull authoritative state |
| `cancel_subscription` | `async def cancel_subscription(sub_id: str, *, cancel_at_cycle_end: bool = True) -> RazorpaySubscription` | Cancel flow (§3.6) |
| `get_customer` | `async def get_customer(customer_id: str) -> RazorpayCustomer` | Customer lookup (KYC/reconciliation) |
| `update_subscription` | `async def update_subscription(sub_id: str, *, plan_id: str, schedule_change_at: str) -> RazorpaySubscription` | Upgrade/downgrade (§3.3/§3.4) |

Return types are frozen dataclasses in `adapters/razorpay.py` (vendor quirks never leak past the file boundary, per §6 + Philosophy M10). Transport-level retry only inside the adapter; business retry (dunning) lives above it in `iam/service.py` (§6.G).

### 6. API endpoints

All under `/api/v1`, all JWT-protected via `Depends(get_current_user)` EXCEPT the webhook (which is signature-protected). New **contract** endpoints (grow the 28-mounted count; OpenAPI must be regenerated). Pydantic schemas live in `iam/schemas.py`.

| Method + path | Auth | Purpose | Request → Response |
|---|---|---|---|
| `POST /api/v1/billing/subscribe` | JWT | Start a subscription/LTD purchase | `{tier: "pro"\|"business"\|"pro_annual"\|"business_annual"\|"ltd"}` → `{razorpay_subscription_id \| razorpay_order_id, checkout: {key_id, ...}}` for the FE Razorpay widget |
| `POST /api/v1/billing/cancel` | JWT | Cancel current subscription (at cycle end) | `{}` → `{status: "cancelled", entitled_until: <ts>}` |
| `GET /api/v1/billing/subscription` | JWT | Current subscription/plan status | → `{plan, status, current_period_end, cancel_scheduled, tier_label}` |
| `POST /api/v1/webhooks/razorpay` | **signature** | **EVOLVED** from V1 capture-only → event router (§4) | RAW bytes → `{captured: true}` (200) |

Plan-guard implications: paid-feature gates (`MVP_ARCH §9.9` free/pro divergence in caps + AI rate limits) read entitlement from `core/plan_guard.py`, which resolves `(users.plan, subscriptions.status, current_period_end)`. The `subscribe`/`cancel`/`subscription` endpoints themselves are NOT plan-gated (a free user must be able to subscribe). Rate-limit the `subscribe` endpoint (e.g. per-user low limit) to prevent spam-creating Razorpay subscriptions.

The `MeResponse.plan: Literal["free"]` at `iam/router.py:265` (hard-coded) widens to the full plan Literal and is sourced from the user's real entitlement (F1, F7).

### 7. Data model changes

Three new tables, parent migration revision `f31c75438e61`. **No new column on `users`** — the subscription is its own entity FK'd to the user (cleaner, supports history, avoids bloating the hot `users` row). `users.plan` widens its CHECK/comment to the full tier set (D-C / F1).

#### 7.1 `subscriptions`

```
id                    UUID PK
user_id               UUID FK users(id) ON DELETE RESTRICT  -- billing survives user soft-delete
razorpay_subscription_id  VARCHAR  UNIQUE  NULL  -- NULL for LTD orders path
razorpay_order_id     VARCHAR  UNIQUE  NULL      -- set for LTD
tier                  VARCHAR(20) NOT NULL       -- pro|business|pro_annual|business_annual|ltd
status                VARCHAR(20) NOT NULL        -- created|authenticated|active|past_due|halted|cancelled|completed|expired
current_period_end    TIMESTAMPTZ NULL           -- NULL = perpetual (LTD)
cancel_scheduled_at   TIMESTAMPTZ NULL
created_at            TIMESTAMPTZ DEFAULT NOW()
updated_at            TIMESTAMPTZ DEFAULT NOW()
-- index on (user_id, status); unique partial index ensures ≤1 active sub per user
```

#### 7.2 `payments`

```
id                    UUID PK
subscription_id       UUID FK subscriptions(id) NULL
user_id               UUID FK users(id) ON DELETE RESTRICT
razorpay_payment_id   VARCHAR UNIQUE
amount_inr            INTEGER NOT NULL     -- paise or rupees — F (decide unit; recommend paise like Razorpay)
status                VARCHAR(20)          -- captured|failed|refunded
event_type            VARCHAR(40)          -- charged|payment.captured|refund.processed
occurred_at           TIMESTAMPTZ
raw_jsonb             JSONB                -- the charge/refund payload slice
```

#### 7.3 `webhook_events` (idempotency + audit + replay store)

This is the table that resolves the V1 capture-only conflict (§Pre-flight #2). It replaces the broken `audit_events`-with-NULL-user_id idea.

```
event_id              VARCHAR PK            -- Razorpay event id — the dedupe key (ON CONFLICT DO NOTHING)
event_type            VARCHAR(60) NOT NULL  -- subscription.charged etc.
payload_jsonb         JSONB NOT NULL        -- FULL raw payload (the column V1 lacked) — enables replay (§4.4)
signature_valid       BOOLEAN NOT NULL
received_at           TIMESTAMPTZ DEFAULT NOW()
processed_at          TIMESTAMPTZ NULL      -- NULL until handler succeeds
processing_error      TEXT NULL             -- last handler error for ops triage
-- index on (event_type, received_at); index on processed_at WHERE processed_at IS NULL (find stuck events)
```

**`audit_events` reuse decision:** business-meaningful billing transitions (plan grant, downgrade, cancel) ALSO write a normal `audit_events` row (with a real `user_id`, via the documented direct-ORM-write pattern used by `iam` for `verify_otp` / by §6A.D) for the seller activity log. The webhook *transport* record lives in `webhook_events` (no user_id needed); the *business effect* lives in `audit_events` (has user_id). Clean separation — neither table is abused.

#### 7.4 Migration plan (descriptive, not code)

One Alembic migration, parent `f31c75438e61`, descriptive message `add billing tables subscriptions payments webhook_events + widen users plan`. `upgrade()` creates 3 tables + indexes + widens the `users.plan` CHECK/comment; `downgrade()` drops the 3 tables + reverts the CHECK. Tested upgrade + downgrade locally; no head divergence dev↔staging (apply dev FIRST per infra ordering rule, never staging-first). Coordinate parent revision with the data-engineer if any other migration is in flight the same sprint (cross-lead memo per §7.5).

### 8. Idempotency, reconciliation & failure modes

| Failure | Behaviour |
|---|---|
| Webhook lost (Razorpay delivered, we 5xx'd / were down) | Razorpay retries on its own backoff schedule. Our handler is idempotent (§4.2) so retries are safe. For permanently-lost events, the **reconciliation job** (below) catches divergence. |
| Signature mismatch | 401, `WebhookSignatureInvalidError` (V1 behaviour preserved). `webhook_events.signature_valid=false` recorded for ops. Razorpay will retry; persistent failure = wrong secret (§9). |
| Duplicate charge / duplicate event | `ON CONFLICT (event_id) DO NOTHING` — no double-grant, no double `payments` row. |
| Razorpay ↔ our DB divergence | **Reconciliation Celery beat task** (daily): for each non-terminal `subscriptions` row, call `adapter.fetch_subscription(sub_id)` and reconcile our `status` / `current_period_end` to Razorpay's authoritative state. Also sweeps `cancelled`/`halted` subs past `current_period_end` → downgrade `users.plan='free'`. This is the safety net for any missed webhook. |
| Handler raises mid-processing | Tx rollback (incl. dedupe insert) → Razorpay retry → clean reprocess (§4.2 step 4). |
| `current_period_end` rewind from out-of-order event | `GREATEST(...)` monotonic guard (§4.3). |

### 9. Security & secrets

- **`RAZORPAY_WEBHOOK_SECRET` is a DISTINCT secret** from `RAZORPAY_KEY_SECRET` — it is the webhook signing secret configured in the Razorpay dashboard. Mixing them is the #1 integration bug. The SM container exists with NO version (§12, founder action pending per `k8s/secrets.yaml.example:73-80`).
- **No secrets in logs.** The webhook handler logs `event_type` + `event_id` + key payload fields only — NEVER the signature, NEVER full card/customer PII. (V1 already logs only `sorted(payload.keys())` — keep that discipline.)
- **Key rotation:** webhook secret rotation = add new SM version → roll pods → Razorpay supports a secret on the webhook config; rotation window where both old+new are valid is Razorpay-side. Document in a runbook (infra, §12).
- **PII handling (DPDP):** `webhook_events.payload_jsonb` may contain customer email/phone from Razorpay. This is PII under DPDP (§11). It is retained for replay; define a retention/purge policy (recommend: purge `payload_jsonb` of processed events older than N days, keeping the dedupe `event_id` + metadata). F (founder/legal) decides retention.
- **Verify RAW bytes before parse** (preserved). Pydantic parse happens only post-verify.
- **The `subscribe` endpoint** must not let a user create unlimited Razorpay subscriptions — rate-limit + check for an existing active sub before creating a new one.

### 10. Frontend dependencies (flag only — FE coordinator owns)

NOT designed here. Hand-off via memo to `meesell-frontend-coordinator`. The API contract they consume:

- `POST /api/v1/billing/subscribe` → render Razorpay Checkout widget with the returned `{key_id, subscription_id|order_id, ...}` (Razorpay's `checkout.js`).
- `GET /api/v1/billing/subscription` → plan-management / current-status page.
- `POST /api/v1/billing/cancel` → cancel confirmation flow.
- The FE must understand that **plan state updates arrive asynchronously via webhook**, NOT from the checkout callback — so the post-checkout UI should poll `GET /billing/subscription` (or `/auth/me`) until the plan reflects, with a "processing your payment" interim state. This async-truth contract is the single most important thing to communicate to FE (mirror of the D-D backend rule).
- `withCredentials` / auth: billing endpoints are normal JWT-Bearer calls (NOT the `/api/v1/auth/*` cookie-credential path) — FE-D5 `withCredentials:true` does NOT apply to `/billing/*`.

### 11. Legal/compliance dependencies (flag only — legal-writer owns)

NOT designed here. Hand-off via memo to `meesell-legal-writer`. **Most of this is ALREADY DRAFTED** (per legal-writer MEMORY.md: the V1 legal pack is complete — Privacy + ToS + Refund 3-variant + Cookie + DPA + Razorpay KYC + GST checklist + Invoice template + in-product strings, with 34 lawyer-review + 3 CA-verify markers). What billing go-live specifically needs:

- **Refund/Cancellation Policy** must be LIVE on the website with HTTPS (Razorpay KYC hard requirement, `LEGAL §5.1`). The 3-variant draft exists; founder must SELECT one (recommendation per `LEGAL §4.3`: 7-day money-back first purchase + pro-rated monthly cancel; 7-day window for LTD) — this is F3.
- **Razorpay KYC pack** finalised (entity = OPC per legal-writer §15.1 ruling 2026-06-11; legal business name = Stellaxis). The name-match rule (`LEGAL §5.2`, PAN=GST=bank exact) gates activation.
- **DPA sub-processor list** must include Razorpay (already in the drafted list per `LEGAL §6` line 291 + the legal-writer DPA draft).
- **GST invoicing** classification (SAC 998314, `LEGAL §6` line 297) — relevant to F5.
- **DPDP retention** of webhook PII (§9) — legal-writer to confirm retention text.

### 12. Infra dependencies (flag only — infra-builder owns)

NOT designed here. Hand-off via memo to `meesell-infra-builder`:

- **Populate `RAZORPAY_WEBHOOK_SECRET` SM version** (the pending founder action — `k8s/secrets.yaml.example:73-80` has the exact `gcloud secrets versions add razorpay-webhook-secret` command). This is a HARD blocker for any webhook testing.
- **Register the webhook URL** in the Razorpay dashboard pointing at `https://<env>/api/v1/webhooks/razorpay`, subscribed to the §4.1 event list. One per env (dev/staging) — note dev needs a publicly reachable URL (ngrok/cloudflared tunnel or a staging-first test posture).
- **New secrets** `RAZORPAY_PLAN_ID_*` (one per tier×interval, D-B) → SM + K8s env injection.
- **DB migration apply ordering:** dev before staging, never the reverse (standing rule).
- **Webhook secret rotation runbook** (§9).

### 13. Founder decisions — DECIDED 2026-06-18

All 10 ruled by the founder on **2026-06-18**. Status column reflects the locked ruling; the original recommendation is retained for traceability.

| # | Decision | Spec recommendation | **RULING (2026-06-18)** |
|---|---|---|---|
| **F1** | Exact `users.plan` string vocabulary. | `free · pro · pro_annual · business · business_annual · ltd` | **DECIDED — ACCEPTED as recommended.** `free · pro · pro_annual · business · business_annual · ltd`. `ltd` IS included because Lifetime ships at launch (F2). |
| **F2** | Does LTD (₹4,999, capped 1,000) ship in the first billing wave, or held back as a scarcity lever? | Defer LTD to a 2nd wave; ship Pro/Business/annual first. | **DECIDED — OVERRIDE.** Lifetime Deal **SHIPS AT LAUNCH (Wave 1).** The one-time Orders-API path for LTD is IN SCOPE from the start, not deferred. Build phasing re-sequenced (§14) so LTD purchase + entitlement is built alongside the subscription path across Waves 1–3. |
| **F3** | Which refund/cancellation policy variant goes live? | 7-day money-back + pro-rated monthly cancel-at-cycle-end. | **DECIDED — 7-day money-back guarantee + pro-rated monthly.** Locked as the policy the implementation + legal copy must reflect. |
| **F4** | Upgrade/downgrade proration. | Upgrade = immediate; downgrade = at cycle end. | **DECIDED — Upgrade applies immediately (pay the difference now); downgrade applies at end of current paid period.** |
| **F5** | GST invoicing: Razorpay-generated vs own pipeline. | Use Razorpay invoices for V1.5. | **DECIDED — Razorpay-generated for V1.5** (Director default). meesell-legal-writer flagged to CONFIRM this satisfies Indian GST/compliance obligations. |
| **F6** | Annual tier launch timing. | Launch annual with Pro. | **DECIDED — YES.** Annual tiers launch alongside monthly. |
| **F7** | Plan as JWT claim vs DB-fresh. | Read fresh from DB; JWT `plan` claim advisory only. | **DECIDED — Plan read DB-fresh, NOT carried as a JWT claim** (Director default). Touches LOCKED §4.B/§7; part of the §7.3 amendment (F10). |
| **F8** | Grace-period policy on failed renewal. | Trust Razorpay's retry window; downgrade on `halted`. | **DECIDED — Trust Razorpay's retry window; downgrade entitlement only on the `halted` event.** No separate fixed grace period. |
| **F9** | Razorpay SDK vs httpx; `amount` unit. | SDK if async-friendly else httpx; paise. | **DECIDED — Amounts in paise, Razorpay-native** (Director default). Default to the official Razorpay Python SDK over raw httpx unless a concrete reason against it is noted at build time. |
| **F10** | Architecture amendment approval (§7.3): §6 (adapters) + §7 (`iam`) are LOCKED. | Approve this spec = approve the amendment. | **DECIDED — APPROVED.** Spec status flipped from "proposed / amendment pending" to **APPROVED DESIGN — execution gated on Wave 0.** |

### 14. Build phasing (ordered, mergeable waves) — RE-SEQUENCED for LTD-at-launch (F2)

Dispatch order respects the backend rule of thumb (DB before services before routes; auth alongside). Each wave is an independently mergeable `feature/razorpay-integration/backend` → `feature/razorpay-integration` slice; the founder owns the integration→develop gate (D1).

**F2 re-sequencing note:** the v1 plan parked LTD in a "2nd wave." Per F2 (OVERRIDE — LTD ships at launch), the one-time **Orders-API / LTD path is now folded into Waves 1–3 alongside the subscription path**, NOT a later wave. Concretely: the LTD schema columns (`razorpay_order_id`, perpetual `current_period_end=NULL` sentinel, `ltd` tier value) land in Wave 1; the `create_order` adapter method + `payment.captured` handler land in Wave 2; the `subscribe` endpoint's `tier:"ltd"` branch + `ltd` entitlement land in Wave 3; LTD lifecycle tests land in Wave 4. There is no separate LTD wave. F6 (annual launches with monthly) is likewise built in-line — the `pro_annual` / `business_annual` plan strings + `RAZORPAY_PLAN_ID_*_ANNUAL` SKUs are first-class from Wave 1, not a follow-on.

**Wave 0 — Founder + infra + legal unblock (no code) — HARD BLOCKER, see "Wave 0 prerequisites" above:**
- ✅ Founder rules F1–F10 — **DONE 2026-06-18.**
- Infra populates `RAZORPAY_WEBHOOK_SECRET` SM version + creates `RAZORPAY_PLAN_ID_*` secrets (**now incl. `_PRO_ANNUAL` / `_BUSINESS_ANNUAL`**; LTD price-constant pinned) + registers webhook URL (staging-first; dev via tunnel) with the §4.1 event list incl. `payment.captured`.
- Legal-writer: adopt the F3-SELECTED variant (7-day money-back + pro-rated monthly); publish refund/ToS/privacy URLs over HTTPS; finalise Razorpay KYC pack → submit (1–3 day activation, `LEGAL §5.3`); **CONFIRM Razorpay-generated GST invoicing (F5) satisfies Indian GST/compliance.**
- Razorpay dashboard: create Plan objects for all recurring tiers×intervals incl. annual (D-B) → capture plan_ids.

**Wave 1 — Data model (`meesell-database-builder`) — subscription + LTD schema together:**
- Migration: `subscriptions` + `payments` + `webhook_events` tables; widen `users.plan` to the full F1 vocabulary (`free·pro·pro_annual·business·business_annual·ltd`). Parent `f31c75438e61`. Upgrade+downgrade tested.
- Schema is LTD-ready from the start: `razorpay_order_id UNIQUE NULL`, `current_period_end NULL`-as-perpetual sentinel, `tier` CHECK includes `ltd`. ORM models. NO `users` column add.

**Wave 2 — Adapter + webhook router core (`meesell-services-builder`) — recurring AND one-time paths:**
- `adapters/razorpay.py` async methods (§5) incl. `create_order` (LTD) + `create_subscription`/`update_subscription`/`cancel_subscription`/`fetch_subscription`/`get_customer`; frozen-dataclass return types; official Razorpay Python SDK per F9 (amounts in paise).
- `iam/service.py`: evolve `capture_razorpay_webhook` → idempotent event router (§4) with the dedupe-in-tx pattern; per-event state-machine handlers (§3) **including `payment.captured` → `users.plan='ltd'` permanent grant**; `audit_events` + `webhook_events` writes. F8: downgrade only on `subscription.halted` (no fixed grace timer).
- Depends on Wave 1 schema.

**Wave 3 — Billing endpoints (`meesell-api-routes-builder`) + entitlement (`meesell-auth-builder`), parallel — incl. LTD purchase branch:**
- Routes `POST /billing/subscribe` (tiers incl. `ltd` → Orders path; incl. `pro_annual`/`business_annual` → Subscriptions path), `POST /billing/cancel`, `GET /billing/subscription` + Pydantic schemas + OpenAPI regen (§6).
- `core/plan_guard.py` entitlement resolution from `(plan, status, current_period_end)` with the LTD perpetual case; **plan read DB-fresh per F7 (no JWT plan claim — JWT `plan` advisory only)**; widen `MeResponse.plan` Literal to the full F1 set. F4 proration: upgrade-immediate (pay difference now) / downgrade-at-period-end wired into the upgrade/downgrade flows (§3.3/§3.4).
- Both depend on Wave 2 service surface.

**Wave 4 — Reconciliation + integration tests (lead):**
- Reconciliation Celery beat task (§8).
- `backend/tests/test_razorpay_integration.py` — full lifecycle: subscribe→activate→charge→renew→pending→halt→downgrade; cancel; **LTD order→`payment.captured`→permanent `ltd` grant**; annual subscribe; upgrade-immediate / downgrade-at-period-end proration; idempotent replay; out-of-order guard; signature-fail 401. Webhook events simulated with signed fixtures.
- Lead merge-gate review of each group PR; founder owns integration→develop.

**Wave 5 — Frontend (`meesell-frontend-coordinator`, separate track):**
- Checkout widget (subscription AND one-time/LTD) + plan-management page + cancel flow + async-truth polling (§10). Consumes the Wave 3 contract.

---

## Branch setup

- Backend branches: `feature/razorpay-integration/backend` (per group) → `feature/razorpay-integration` (lead merge gate, squash) → `develop` (founder gate, D1).
- Frontend: `feature/razorpay-integration/frontend` → `feature/razorpay-integration`.
- Infra: `feature/razorpay-integration/infra` → `feature/razorpay-integration`.
- Session naming: `mesell-razorpay-integration-backend-session-{N}` (≤30-char slug OK: `razorpay-integration` = 20 chars).
- A `feature/razorpay-integration/backend` branch open >5 calendar days without merge → escalate to founder per repo management master plan §1.2.

---

## Memory protocol

- This spec's existence + path + key open questions are appended to `meesell-backend-coordinator` MEMORY.md.
- On dispatch (next session), the lead adds an `IN PROGRESS` row to `feature_board_backend.md` with the session name and a session-start UPDATE block to `STATUS_BACKEND.md`.
- Cross-lead memos to author at dispatch time: `handoff_contract_razorpay.md` (FE), `handoff_secret_razorpay_webhook.md` (infra), `handoff_refund_policy_razorpay.md` (legal — though legal pack is mostly drafted).

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-18 | `meesell-backend-coordinator` (`mesell-razorpay-integration-planning-session-1`) | Initial spec. Amends the §1.E/§14 V1.5 deferral. 14 spec sections, 5 spec-decisions (D-A..D-E), 10 founder decisions (F1–F10), 5-wave build phasing, 3 new tables. Two dispatch-summary errors corrected vs live tree (no `razorpay_sub_id`/`plan_expires_at` columns; V1 webhook logs only, persists nothing). |
| v2 | 2026-06-18 | `meesell-backend-coordinator` (`mesell-razorpay-integration-planning-session-1`) | Founder ruled F1–F10. Status flipped SPEC READY → **APPROVED DESIGN — execution gated on Wave 0**. §7.3 architecture amendment APPROVED (F10). Added Decision Log + prominent Wave 0 prerequisites hard-blocker list. **F2 OVERRIDE: LTD ships at launch (Wave 1)** — build phasing re-sequenced to fold the Orders-API/LTD path + annual SKUs into Waves 1–3 (no separate LTD wave). §13 marked DECIDED; F5 GST flagged to legal for confirmation. |
