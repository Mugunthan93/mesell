# Wave 2 — Adapter + Webhook Event Router Task Spec (Razorpay Integration, V1.5)

**Feature slug:** `razorpay-integration`
**Wave:** 2 of 5 (ADAPTER V1.5 SURFACE + IDEMPOTENT WEBHOOK EVENT ROUTER)
**Target specialist:** `meesell-services-builder` (opus)
**Session name (dispatch header):** `mesell-razorpay-integration-backend-session-2`
**Authored by:** `meesell-backend-coordinator` (HYBRID step 1 — spec only, no code)
**Date:** 2026-06-19
**Parent design (LOCKED):** `docs/plans/features/razorpay-integration/RAZORPAY_INTEGRATION_SPEC.md` rev v4 (APPROVED 2026-06-18) §3 (state machine), §4 (webhook handling), §5 (adapter surface), §8 (idempotency/reconciliation), §14 Wave 2; `docs/PRICING_LOCKED.md` v2.
**Predecessor (built, merge-gate PASS, held-for-founder):** `WAVE1_DB_TASKSPEC.md` — the 3 billing ORM models + migration `f8fa7a36383f` + `users.trial_ends_at` landed on PR #300.

---

## 0. CRITICAL GROUND-TRUTH — read first (verified against the live tree 2026-06-19)

Three things the design spec does NOT state correctly for Wave 2 execution. All verified against the live tree, not the dispatch summary:

1. **BRANCH: build STACKED on `feature/razorpay-integration/backend` — do NOT branch off `develop`.** Wave 2 imports the Wave 1 ORM models (`Subscription`, `Payment`, `WebhookEvent`) which are **NOT yet on `develop`** — PR #300 (`feature/razorpay-integration/backend` → develop) is engineering-PASS but **HELD at the founder gate (D1)** and not merged. If Wave 2 branched off `develop`, the model imports would not resolve. Cut your Wave 2 work directly on the existing `feature/razorpay-integration/backend` branch (continue it) — the Wave 1 commit `7aca019` is its tip on the remote. `git fetch origin && git checkout feature/razorpay-integration/backend && git pull` before starting. Confirm `backend/app/shared/models/subscription.py` / `payment.py` / `webhook_event.py` are present in your working tree before writing any import.

2. **NO MIGRATION IN WAVE 2.** The billing tables already exist (Wave 1 migration `f8fa7a36383f`, parent `c2d3e4f5a6b7`). Wave 2 is adapter + service-layer logic ONLY. Verified: the migration chain on `feature/razorpay-integration/backend` is single-headed and linear — `935e55b4852c → a1b2c3d4e5f6 → f31c75438e61 → b7c2e1a9d3f4 → c2d3e4f5a6b7 → f8fa7a36383f`. **Do NOT create a new Alembic revision.** If, at your dispatch time, you find you genuinely need a schema change (you should not), STOP and escalate to the lead — it means a Wave 1 gap and a re-gate, not a silent Wave 2 migration.

3. **The official Razorpay Python SDK is NOT yet in `requirements.txt`** (only `httpx==0.27.0` is present). Per founder ruling **F9** (default to the official Razorpay Python SDK), Wave 2 ADDS `razorpay` to `backend/requirements.txt`. **The Razorpay SDK is SYNCHRONOUS** — it is `requests`-based, not async. Therefore the V1.5 adapter methods (which §6.G + the spec §5 require to be `async`) MUST wrap the sync SDK calls in `asyncio.to_thread(...)`, EXACTLY mirroring the established `adapters/gcs.py` pattern (which wraps the sync `google-cloud-storage` SDK). Do not introduce a second HTTP stack; follow the GCS precedent. `backend/requirements.txt` is a lead-owned root-wiring file — propose the exact pin in your PR (recommend `razorpay==1.4.2` or the then-current stable); the lead applies/confirms it at the merge gate.

---

## 1. Scope of Wave 2 (exactly this, nothing more)

Two deliverables, both per the agent-lineup row in the design spec (§Agent lineup → `meesell-services-builder` primary):

**A) Razorpay adapter V1.5 surface** — extend `backend/app/adapters/razorpay.py` with the typed, async methods the design spec §5 defines, following the §6.G typed-exception pattern. Keep `verify_webhook_signature` byte-for-byte unchanged (LOCKED, D-E).

**B) Idempotent webhook event router** — evolve `backend/app/modules/iam/service.py::capture_razorpay_webhook` from V1 log-only into a signature-verified, idempotent, out-of-order-tolerant event router that drives subscription/payment/user.plan state per the §3 state machine and §4 event table — with the dedupe-INSERT and the state mutation committed in a SINGLE transaction.

**Out of scope for Wave 2 (explicit — DO NOT build):**
- NO Alembic migration / model change (Wave 1 owns the schema; see §0.2).
- NO API routes / routers / Pydantic request-response schemas — Wave 3 (`meesell-api-routes-builder`). The webhook handler is reached through the **existing** mounted route `POST /api/v1/webhooks/razorpay` (infrastructure surface, already wired in V1) — you evolve the *service function it calls*, not the route.
- NO `core/plan_guard.py` / entitlement-resolution change, NO `MeResponse.plan` widening — Wave 3 (`meesell-auth-builder`).
- NO reconciliation Celery beat task, NO 14-day trial-expiry sweep — Wave 4 (lead).
- NO `start-trial` / `subscribe` / `cancel` *endpoints* — Wave 3. (The webhook router does NOT create subscriptions; it reacts to them. The `subscribe` endpoint that calls `create_subscription` is Wave 3. You build `create_subscription` as an adapter method now; its *first caller* arrives in Wave 3.)
- NO frontend, NO infra, NO legal, NO AI work.

**Why `create_subscription` / `create_order` / `cancel_subscription` are in Wave 2 even though their endpoint callers are Wave 3:** the design spec §14 places the full adapter surface in Wave 2 (DB → adapter+service → routes+entitlement ordering). Wave 3's routes consume the Wave 2 adapter surface. Build all six adapter methods now so Wave 3 has a stable surface to call.

---

## 2. Conventions to follow (verified against the live tree)

- **Async wrapper over sync SDK** — model on `backend/app/adapters/gcs.py`: lazy module-level singleton client guarded by an `asyncio.Lock`, each public method `async def`, the actual SDK call dispatched via `await asyncio.to_thread(self._client.<resource>.<op>, ...)`.
- **Credentials via `app.shared.config.settings` ONLY** — NEVER `os.getenv`. The §19 import-linter (CI Contract) rejects `os.getenv` anywhere under `app/adapters/`. Use `settings.RAZORPAY_KEY_ID` + `settings.RAZORPAY_KEY_SECRET` for SDK auth (both already wired in `config.py:146-147`, in `REQUIRED_FIELDS`). Plan-id config (`RAZORPAY_PLAN_ID_*`) is read by the **Wave 3 routes / a pricing-or-iam constant**, NOT by the adapter — the adapter takes an opaque `plan_id: str` argument (D-B: the adapter is plan-agnostic).
- **Typed exceptions rooted at `RazorpayAdapterError`** (already defined in `adapters/__init__.py:80-87`, `code="razorpay.unavailable"`, status 502, inherits `AdapterError → MeesellError`). See §5 below for the exact taxonomy.
- **Vendor quirks never leak past the adapter file boundary** (Philosophy M10 / §6). Return **frozen dataclasses** defined in `adapters/razorpay.py` — never return raw Razorpay SDK dicts/objects to the service layer.
- **Transport-level retry inside the adapter only**; business retry (dunning) lives above it in `iam/service.py` (§6.G). The Razorpay SDK does minimal retry — a light transport retry (e.g. 1 retry on transient `requests`/connection error, NOT on 4xx) is acceptable inside the adapter; do not retry idempotency-unsafe creates.
- **No secrets in logs.** The webhook router logs `event_type` + `event_id` + selected non-PII payload fields only — NEVER the signature, NEVER full customer email/phone/card data (§9). The V1 handler already logs only `sorted(payload.keys())` — preserve that discipline; you may add `event_type`/`event_id` but no PII.
- **Service-layer style** — match the existing `iam/service.py`: `async def` module functions (not a class), `logger = logging.getLogger(__name__)`, `AsyncSession` passed in / acquired per the module's existing pattern, raise typed exceptions never raw strings.
- **`from __future__ import annotations`**; stdlib → third-party → local import blocks.

---

## 3. Part A — Adapter V1.5 surface (`backend/app/adapters/razorpay.py`)

Add the following to the **existing** file, BELOW the unchanged `verify_webhook_signature`. Update the module docstring's "V1 ONLY surface" note to reflect that the V1.5 surface now exists (keep the two LOCKED-exception paragraphs about `verify_webhook_signature` intact — it stays sync, bool-returning, never-raising).

### 3.1 Frozen return dataclasses (defined in this file)

Define `@dataclass(frozen=True)` return types so vendor shapes never leak. At minimum:

| Dataclass | Fields (minimum) | Source method |
|---|---|---|
| `RazorpaySubscription` | `id: str`, `status: str`, `plan_id: str`, `current_end: int \| None` (epoch secs from Razorpay), `short_url: str \| None`, `notes: dict` | create/fetch/cancel/update_subscription |
| `RazorpayOrder` | `id: str`, `amount: int` (paise), `currency: str`, `status: str`, `receipt: str \| None` | create_order |
| `RazorpayCustomer` | `id: str`, `email: str \| None`, `contact: str \| None` | get_customer |

Map Razorpay's epoch-seconds period fields to `int | None`; the service layer converts to `datetime` (UTC) when writing `current_period_end`. Keep PII (`email`/`contact`) in the dataclass only because `get_customer` needs it; the service must not log it.

### 3.2 The six async methods (signatures per design spec §5, refined)

All `async def`, all wrap the sync SDK via `asyncio.to_thread`, all raise `RazorpayAdapterError` (or a subclass, §5.3) on transport failure / non-2xx — NEVER leak a raw `razorpay.errors.*` or `requests` exception.

```
async def create_subscription(
    *, plan_id: str, customer_notify: bool = True,
    total_count: int | None = None, notes: dict | None = None,
) -> RazorpaySubscription
    # Razorpay Subscriptions API .subscription.create(...). Returns sub id +
    # short_url for the FE checkout widget. notes carries {user_id, tier}.

async def create_order(
    *, amount: int, currency: str = "INR",
    receipt: str, notes: dict | None = None,
) -> RazorpayOrder
    # One-time LTD purchase via Orders API .order.create(...). amount in PAISE (F9).

async def fetch_subscription(sub_id: str) -> RazorpaySubscription
    # .subscription.fetch(sub_id) — authoritative state pull for reconciliation (Wave 4).

async def cancel_subscription(
    sub_id: str, *, cancel_at_cycle_end: bool = True,
) -> RazorpaySubscription
    # .subscription.cancel(sub_id, {"cancel_at_cycle_end": 1|0}). Default cycle-end (§3.6).

async def update_subscription(
    sub_id: str, *, plan_id: str, schedule_change_at: str = "cycle_end",
) -> RazorpaySubscription
    # .subscription.update(...) for upgrade/downgrade (§3.3/§3.4). F4: upgrade-now / downgrade-cycle-end.

async def get_customer(customer_id: str) -> RazorpayCustomer
    # .customer.fetch(customer_id) — KYC/reconciliation lookup.
```

### 3.3 Lazy singleton SDK client

Mirror `gcs.py`: a module-level `_client: razorpay.Client | None = None` plus an `asyncio.Lock`, initialised on first use with `razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))`. Set `_client.set_app_details(...)` optionally for Razorpay request attribution. Reuse for process life.

---

## 4. Part B — Idempotent webhook event router (`backend/app/modules/iam/service.py`)

Evolve `capture_razorpay_webhook(raw_payload: bytes, signature: str)` (currently lines ~590-644, log-only). Preserve the verify→parse ordering exactly; replace the "log only / `audit_event_id=0` placeholder" body with the real router. The route, the RAW-bytes-before-JSON ordering, and the two preserved exceptions (`WebhookSignatureInvalidError` 401, `MalformedWebhookPayloadError` 400) all stay.

### 4.1 Processing pipeline (the exact order — this is correctness-critical, §4.2)

1. **Verify signature** — `razorpay_adapter.verify_webhook_signature(raw_payload, signature)` on RAW bytes (unchanged). `False` → raise `WebhookSignatureInvalidError` (401). *(Optionally record a `webhook_events` row with `signature_valid=False` for ops triage before raising — see §4.4 note; but do NOT process it.)*
2. **Parse JSON** — `json.loads(raw_payload.decode("utf-8"))`; non-dict / decode error → raise `MalformedWebhookPayloadError` (400) (unchanged).
3. **Extract `event_id` and `event_type`** — `event_id` from the `x-razorpay-event-id` header (the router must pass the header through; if only the body `id` is available, document the fallback) and `event_type` from `payload["event"]` (e.g. `subscription.charged`). If `event_id` is absent, treat as malformed (400) — the dedupe key is mandatory.
4. **Open ONE transaction** and within it:
   a. `INSERT INTO webhook_events (event_id, event_type, payload_jsonb, signature_valid, received_at) VALUES (...) ON CONFLICT (event_id) DO NOTHING` — use SQLAlchemy's `postgresql.insert(...).on_conflict_do_nothing(index_elements=["event_id"])`. **If the insert affected 0 rows (conflict), this event was already processed → COMMIT (no-op) and return 200 immediately.** This is the dedupe gate.
   b. If the insert took (new event), **dispatch to the per-event handler (§4.3) inside the SAME transaction.** The dedupe-record write and the state mutation commit atomically.
   c. On handler success, set `webhook_events.processed_at = NOW()`.
   d. **Commit.** If the handler raises mid-processing, the WHOLE transaction rolls back (including the dedupe insert) → Razorpay retries → clean reprocess. (This atomic dedupe-insert-plus-mutation is the single most important property of this wave.)
5. **Unknown / unmodelled `event_type`** → record the `webhook_events` row (so it is observable + replayable), do NOT dispatch, return **200** (so Razorpay does not retry an event we deliberately ignore). Log at INFO.
6. **Return** the existing `WebhookCaptureResult` shape (keep the return type; populate `audit_event_id` with the real audit row id when a business-effect audit row is written, else keep a sentinel — see §4.5).

### 4.2 Idempotency + atomicity requirements (acceptance-critical)

- The dedupe `INSERT ... ON CONFLICT (event_id) DO NOTHING` and the state mutation MUST be in the SAME DB transaction. A handler exception MUST roll back BOTH.
- A replayed event MUST produce zero side effects (no double grant, no duplicate `payments` row) — proven by the ON CONFLICT gate + a test (§7 item 4).
- `payments` rows are also deduped by `razorpay_payment_id` UNIQUE — when writing a `payments` row, use `ON CONFLICT (razorpay_payment_id) DO NOTHING` (or check-then-insert in-tx) so a re-delivered `subscription.charged` cannot create a duplicate payment even in the unlikely case the event-id gate is bypassed.

### 4.3 Event → state-transition mapping table (the §4.1 / §3.1 matrix — implement exactly)

Each handler reads the current `subscriptions.status` and applies a **guarded** transition (the §3.1 table is the allowed-transition matrix). Illegal transitions are logged and no-op'd (return 200, mark processed). Out-of-order guards per §4.3 of the design.

| Razorpay `event` | Handler action | Guards |
|---|---|---|
| `subscription.authenticated` | `subscriptions.status → authenticated` (lookup by `razorpay_subscription_id` from payload) | only from `created`/`authenticated` |
| `subscription.activated` | `status → active`; set `users.plan = subscription.tier`; set `current_period_end` from payload `current_end` (epoch→UTC datetime) | grant entitlement; write business `audit_events` row (§4.5) |
| `subscription.charged` | upsert a `payments` row (status `captured`, `event_type='subscription.charged'`, `amount_paise`); **extend `current_period_end` via `GREATEST(current_period_end, new_end)`**; ensure `status='active'` IF currently `active`/`past_due` (renewal heartbeat) | monotonic period guard (§4.3); a late `charged` on a `cancelled` sub does NOT re-activate |
| `subscription.pending` | `status → past_due` (grace = trust Razorpay retry window, F8); trigger dunning (trigger only — content is FE/legal, §Scope) | from `active` only |
| `subscription.halted` | `status → halted`; **downgrade `users.plan='free'`** (F8 — downgrade only on `halted`, no fixed grace timer); write business `audit_events` row | from `past_due`/`active` |
| `subscription.cancelled` | `status → cancelled`; keep `users.plan` at tier until `current_period_end` (the Wave-4 reconciliation sweep does the eventual downgrade) | a `cancelled` sub STAYS cancelled even if a late `charged` arrives |
| `subscription.completed` | `status → completed`; downgrade (not expected for open-ended plans) | terminal |
| `subscription.updated` | apply the landed plan change (upgrade/downgrade) — set `subscriptions.tier` + `users.plan` to the new tier on upgrade-immediate; downgrade lands at the next-cycle `charged` (F4) | per §3.3/§3.4 |
| `payment.captured` | **LTD path:** if the captured order is an LTD order (match `razorpay_order_id` on the `subscriptions` row, or the order `notes.tier=='ltd'`) → set `users.plan='ltd'` permanently, the LTD `subscriptions` row `status='active'` + `current_period_end=NULL` (perpetual sentinel); write a `payments` row; write business `audit_events` row | idempotent on `razorpay_payment_id` |
| `payment.failed` | write a `payments` row `status='failed'`; informs dunning (no state downgrade here — downgrade is `halted`-driven, F8) | — |
| `refund.processed` | write a `payments` refund row (`status='refunded'`); if a full refund of an active sub → downgrade per policy (F3 7-day money-back) | manual-refund reaction; out of scope to *issue* refunds (Razorpay dashboard does that) |

**Exact event-name strings** must be confirmed against Razorpay's then-current webhook docs at build time (Razorpay occasionally renames/adds events). Unknown event types → §4.1 step 5 (record + 200 + no dispatch).

### 4.4 Out-of-order / ordering guards (§4.3 of design — implement)

- `subscription.charged` setting `current_period_end` uses `GREATEST(current_period_end, new_end)` so a late older `charged` cannot rewind the period.
- `subscription.cancelled` before a stray late `charged`: a `cancelled` sub stays cancelled; a late `charged` only extends the period if status is still `active`/`past_due`.
- Each handler reads current `subscriptions.status` first and applies the §4.3-table guarded transition; illegal transitions log + no-op + return 200.
- *(Signature-fail recording note: recording a `signature_valid=False` row before raising 401 is OPTIONAL for ops triage; if you do it, it must be its own committed write that does NOT block the 401 — keep it simple, a `logger.warning` is the minimum the spec requires. Builder's choice; flag which you did.)*

### 4.5 `audit_events` vs `webhook_events` (clean separation — §7.3 of design)

- `webhook_events` = the **transport** record (no `user_id`; PK = `event_id`; the dedupe + replay store). EVERY processed event writes here.
- `audit_events` = the **business effect** (has a real `user_id`). Business-meaningful transitions ONLY — plan grant (`activated`/`payment.captured`-LTD), downgrade (`halted`), cancel (`cancelled`) — ALSO write a normal `audit_events` row via the documented direct-ORM-write pattern (the same pattern `iam` already uses for `verify_otp`). Trial-start/trial-expiry audit rows are Wave 3/4 (no webhook). Do NOT relax `audit_events.user_id` NULLability — that was the rejected V1 idea; `webhook_events` exists precisely to avoid it.
- Update the `WebhookCaptureResult` return: populate `audit_event_id` with the real id when a business audit row was written; otherwise a documented sentinel (e.g. `None`/`0`) for transport-only events. Adjust the `WebhookCaptureResult` dataclass field type if needed (it lives in `iam/domain.py` or `iam/schemas.py` — locate it; a type-widening of an internal result object is in-scope, it is not a wire schema).

---

## 5. Typed-exception taxonomy to use

### 5.1 Adapter layer (`adapters/__init__.py` + raised from `adapters/razorpay.py`)

`RazorpayAdapterError` already exists (`code="razorpay.unavailable"`, status 502). For Wave 2 you MAY add narrow subclasses IF they carry distinct handling semantics; otherwise raise `RazorpayAdapterError` directly. Recommended minimal additions (add to `adapters/__init__.py` `__all__` if created):

- `RazorpayAdapterError` (base, exists) — transport failure / 5xx / connection error → 502 envelope.
- *(Optional)* a 4xx-from-Razorpay variant if the service must distinguish "Razorpay rejected our request (bad plan_id, etc.)" from "Razorpay is down". If you add one, keep it a subclass of `RazorpayAdapterError`, document the status, and note it in the PR. Default: do NOT over-engineer — one base class is acceptable for Wave 2 if the service does not branch on it.

The adapter NEVER leaks `razorpay.errors.*`, `requests.*`, or `httpx.*` — catch them and re-raise as `RazorpayAdapterError(...)`.

### 5.2 Service / webhook layer (`iam/exceptions.py`)

**DO NOT silently expand the LOCKED 8-class `iam` exception inventory.** `iam/exceptions.py` documents a §7.G-LOCKED 8-exception inventory (header lines ~21-37). The two webhook exceptions you NEED already exist:
- `WebhookSignatureInvalidError` (401, `auth.webhook.signature_invalid`) — reuse, unchanged.
- `MalformedWebhookPayloadError` (400, `validation.webhook.malformed_payload`) — reuse, unchanged.

If the router needs a NEW typed exception (it likely does not — unknown events return 200, not an error), STOP and flag it to the lead: adding a 9th `iam` exception touches a §7.G-LOCKED section and is a founder-gate item per repo management master plan §7.3. Default: handle all webhook outcomes with the two existing exceptions + 200-with-no-op, adding NO new exception class.

A `RazorpayAdapterError` raised by an adapter call inside a webhook handler should NOT escape as a 502 to Razorpay (a 502 makes Razorpay retry, which is correct for transient adapter failures during reconciliation calls — but the webhook router itself rarely calls the adapter; it mostly writes DB state). If a handler does call the adapter and it raises, let the transaction roll back and return the appropriate status so Razorpay retries.

---

## 6. Config / dependency changes (root-wiring — lead-owned, propose in PR)

- **`backend/requirements.txt`** — add the official Razorpay Python SDK pin (recommend `razorpay==1.4.2` or the then-current stable; F9). This file is lead-owned root-wiring — propose the exact line in the PR; the lead applies/confirms at the merge gate. Do NOT add `httpx`-based Razorpay calls (httpx is already pinned for other uses; use the SDK per F9).
- **`backend/app/shared/config.py`** — `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` already exist (lines 146-148, in `REQUIRED_FIELDS`). The adapter needs NO new config (plan-ids are Wave-3-consumed). If you find the SDK needs an additional setting, propose it; do not add silently.

---

## 7. Test requirements (must exist AND pass)

New test file: `backend/tests/test_razorpay_webhook_router.py` (Wave-2-scoped; the full lifecycle integration suite `test_razorpay_integration.py` is Wave 4, lead-owned). Follow the existing `tests/` conventions (the rolled-back `AsyncSession` fixture, `pytestmark` for integration where a DB is needed; conftest `*_test`-DB guard). Webhook events simulated with **signed fixtures** (HMAC-sign a known payload with a test `RAZORPAY_WEBHOOK_SECRET` so `verify_webhook_signature` passes).

Required coverage:

1. **Signature gate** — a payload with a bad signature → `WebhookSignatureInvalidError` (401) and NO `webhook_events`-processed / NO state mutation.
2. **Malformed payload** — verified-signature but non-JSON / non-dict body → `MalformedWebhookPayloadError` (400).
3. **Happy-path grant** — signed `subscription.activated` for an existing `created` sub → `subscriptions.status='active'`, `users.plan` set to tier, `current_period_end` set, a `webhook_events` row with `processed_at` set, a business `audit_events` row written.
4. **Idempotent replay** — POST the SAME signed event twice → second hit conflicts on `event_id`, returns 200, produces ZERO additional side effects (sub status unchanged, no duplicate `payments`/`audit_events` row). This is the headline test.
5. **Atomic rollback** — force the handler to raise mid-processing (monkeypatch a write to fail) → assert the `webhook_events` dedupe row is ALSO rolled back (so Razorpay retry reprocesses cleanly) — i.e. the dedupe insert + mutation are one transaction.
6. **Out-of-order period guard** — apply a `charged` with a later `current_end`, then a `charged` with an earlier `current_end` → `current_period_end` reflects the LATER value (GREATEST monotonic guard); a `charged` arriving after `cancelled` does NOT re-activate.
7. **LTD path** — signed `payment.captured` for an LTD order → `users.plan='ltd'`, the LTD `subscriptions` row `status='active'` + `current_period_end IS NULL`, a `payments` row written; replay is idempotent.
8. **Renewal** — `subscription.charged` on an `active` sub → a `payments` row + extended `current_period_end`, status stays `active`.
9. **Halt downgrade** — `subscription.halted` → `subscriptions.status='halted'`, `users.plan='free'` (F8).
10. **Unknown event type** — a signed event with an unmodelled `event` → recorded in `webhook_events`, returns 200, NO dispatch, NO state mutation.
11. **Adapter unit tests** (`test_razorpay_adapter.py` OR in the same file) — the six methods: mock the Razorpay SDK client (patch the lazy singleton), assert (a) success maps to the frozen dataclass with correct fields, (b) a raised `razorpay.errors.*` / `requests` error is caught and re-raised as `RazorpayAdapterError` (never leaks the raw vendor error), (c) `verify_webhook_signature` is UNCHANGED (a regression assert that it is still sync + returns bool).

CI: Gates 1 (unit), 2 (smoke), 3 (lint) MUST be green. Gate 4 (integration) result pasted in PR "Test evidence". Paste the actual pytest run output.

---

## 8. Branch + PR

- **Branch:** continue on `feature/razorpay-integration/backend` (the Wave 1 branch — STACKED, per §0.1). `git fetch && git checkout feature/razorpay-integration/backend && git pull` first. Do NOT branch off `develop`.
- **PR target:** `feature/razorpay-integration/backend` → **`feature/razorpay-integration`** (the lead merge gate, squash-merge — NOT directly to `develop`; the founder owns integration→develop per D1). **NOTE:** Wave 1's PR #300 targeted `develop` directly and is HELD at the founder gate. For Wave 2, confirm with the lead whether `feature/razorpay-integration` (the integration branch) exists yet; if Wave 1 has not been merged anywhere, the lead may have you target the same flow Wave 1 used — **flag the branching/target with the lead before opening the PR** (this is a known coordination point because Wave 1 is founder-held). Default expectation per the design §Branch setup: group-branch → integration-branch → develop.
- **PR template:** fill `.github/PULL_REQUEST_TEMPLATE/backend.md` COMPLETELY — no `<>` placeholders. Required: state "NO migration this wave" with the verified single head (`f8fa7a36383f`); list modules/files touched (`adapters/razorpay.py`, `adapters/__init__.py` if a subclass added, `modules/iam/service.py`, `modules/iam/domain.py`-or-`schemas.py` if `WebhookCaptureResult` widened, `requirements.txt`, the new test file(s)); contract changes in commit body (NONE — webhook is infrastructure surface, no contract endpoint added; OpenAPI NOT regenerated this wave); cross-module check — the webhook router lives in `iam` and touches only `iam` + `shared.models` + `adapters` (no new `✗ → ✓` in the §2.D matrix — `iam` is the all-`✗` module; confirm you add no cross-module domain call); Test evidence pasted; "Session" block = `mesell-razorpay-integration-backend-session-2`.
- **First commit footer** carries the session name.
- **On PR open:** YOU (the specialist) set the `feature_board_backend.md` row for `razorpay-integration` to `IN REVIEW` and clear `Current session` (per D2). The lead then runs the merge-gate review (HYBRID step 3).
- **OpenAPI:** NO regeneration (no endpoint shape change — Wave 2 evolves a service function behind an existing infrastructure route).

---

## 9. Acceptance criteria (the lead's merge-gate checklist for this PR)

- [ ] Six async adapter methods added to `adapters/razorpay.py` per §3.2, each wrapping the sync Razorpay SDK via `asyncio.to_thread` (GCS pattern), each raising `RazorpayAdapterError` on failure, none leaking a raw vendor/`requests` exception.
- [ ] `verify_webhook_signature` is BYTE-FOR-BYTE UNCHANGED (LOCKED, D-E) — confirm via diff; the two locked-exception docstring paragraphs intact.
- [ ] Frozen-dataclass return types defined in the adapter; no raw SDK object/dict returned to the service layer.
- [ ] `capture_razorpay_webhook` evolved into the §4.1 pipeline: verify→parse→`event_id`/`event_type`→ONE-transaction dedupe-INSERT-`ON CONFLICT (event_id) DO NOTHING`-plus-handler→`processed_at`.
- [ ] The dedupe insert + state mutation are in the SAME transaction; a handler raise rolls back BOTH (proven by test §7.5).
- [ ] Every §4.3 event handler implemented with the §4.4 out-of-order guards (`GREATEST` period monotonicity; `cancelled` not re-activated by late `charged`; guarded status transitions; unknown events → 200 + no-op).
- [ ] LTD `payment.captured` path → permanent `users.plan='ltd'`, perpetual `current_period_end=NULL`; halt → `users.plan='free'` (F8).
- [ ] `webhook_events` written for every processed event (incl. unknown); business `audit_events` written for grant/downgrade/cancel only; `audit_events.user_id` NULLability NOT relaxed.
- [ ] NO new Alembic migration; NO model/schema change; head still `f8fa7a36383f` (re-verify). NO routes/plan_guard/reconciliation/trial-endpoint changes (Wave 3/4).
- [ ] `iam/exceptions.py` 8-class LOCKED inventory NOT expanded (or, if a 9th was unavoidable, FLAGGED to lead as a §7.3 founder-gate item — default: not expanded).
- [ ] `requirements.txt` Razorpay SDK pin proposed; no `os.getenv` in the adapter; credentials from `settings` only.
- [ ] Tests §7 items 1–11 present and PASSING; CI Gates 1/2/3 green; Gate 4 result pasted.
- [ ] PR template fully filled; session block = `mesell-razorpay-integration-backend-session-2`; board row `IN REVIEW`; branch/target coordination with the lead confirmed (§8).
- [ ] No secrets/PII in logs (event_type + event_id + non-PII keys only).
- [ ] Zero out-of-scope changes.
```
