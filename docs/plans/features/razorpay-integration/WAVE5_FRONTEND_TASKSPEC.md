# Razorpay Integration — Wave 5 Frontend Task Spec (Billing UI)

**Status:** SPEC — builder-ready (HYBRID dispatch step 1 output). NOT code. Awaits founder go on the §13 open decisions before specialist dispatch (step 2).
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Session:** mesell-razorpay-billing-frontend-session-1
**Date:** 2026-06-19
**Pairs with:** `RAZORPAY_INTEGRATION_SPEC.md` (APPROVED DESIGN §10), `WAVE3_ROUTES_TASKSPEC.md` (the BE→FE contract — authoritative for endpoints/schemas/errors), `docs/PRICING_LOCKED.md` v2 (the tiers to display).
**Consumes:** Wave 3 backend contract (4 `/billing/*` endpoints + widened `MeResponse`). Wave 5 is FE-only.

---

## 0. Why this spec exists / authoritative sources

The Razorpay design (`RAZORPAY_INTEGRATION_SPEC.md` §10) flags the FE surface but does not design it. The BE→FE contract memo `handoff_contract_razorpay.md` is **owed by backend at Wave 3 PR-merge but has NOT yet been written** (see Risk R1). This spec therefore lifts the contract **directly from the authoritative WAVE3 task spec** (the Pydantic schemas at WAVE3 lines 100–139 and the handler behaviour at lines 143–148). When the memo lands, reconcile field names against it before the builder starts; if there is drift, the memo wins and this spec is amended.

**The single most important contract rule (D-D / §10 / spec line 397):** subscribe does NOT grant the plan. The grant is webhook-driven and arrives asynchronously. After the Razorpay Checkout widget closes, the FE MUST POLL `GET /billing/subscription` (or re-fetch `/auth/me`) until the plan/entitlement reflects, showing a "processing your payment" pending state. NEVER assume optimistic success from the checkout callback.

---

## 1. The contract the FE consumes (lifted from WAVE3, authoritative)

### 1.1 Endpoints

All under `/api/v1`, all **JWT-Bearer** (NOT the cookie-credential `/auth/*` path — `withCredentials:false` for `/billing/*`, per spec line 398). All gated behind backend `FEATURE_BILLING_ENABLED` — when off, the four paths return **404** (WAVE3 §8.12). The FE must degrade gracefully on 404 (treat billing as unavailable; hide CTAs) — see §6.5.

| # | Method + path | Request body | Success response |
|---|---|---|---|
| 1 | `POST /api/v1/billing/subscribe` | `{ tier: "starter"\|"pro"\|"business"\|"pro_annual"\|"business_annual"\|"ltd" }` | `BillingSubscribeResponse` (advisory) |
| 2 | `POST /api/v1/billing/start-trial` | `{}` (empty) | `BillingStartTrialResponse` |
| 3 | `POST /api/v1/billing/cancel` | `{}` (empty) | `BillingCancelResponse` |
| 4 | `GET /api/v1/billing/subscription` | — | `BillingSubscriptionResponse` |

### 1.2 Response shapes (mirror exactly as TS interfaces)

```ts
// POST /billing/subscribe
interface BillingCheckout {
  key_id: string;                          // public Razorpay key — safe in browser
  razorpay_subscription_id?: string | null;// recurring tiers
  razorpay_order_id?: string | null;       // ltd
  short_url?: string | null;               // Razorpay-hosted checkout fallback
  amount_paise?: number | null;            // ltd display
  currency: string;                        // "INR"
  tier: string;
}
interface BillingSubscribeResponse { checkout: BillingCheckout; } // ADVISORY — do NOT treat as grant

// POST /billing/start-trial
interface BillingStartTrialResponse {
  trial_ends_at: string;                   // ISO-8601 TZ
  entitlement: 'pro';
}

// POST /billing/cancel
interface BillingCancelResponse {
  status: 'cancelled';
  entitled_until: string | null;           // current_period_end; null in odd states (e.g. ltd)
}

// GET /billing/subscription
interface BillingSubscriptionResponse {
  plan: 'free'|'starter'|'pro'|'pro_annual'|'business'|'business_annual'|'ltd';
  status: string | null;                   // subscriptions.status, null for free/trial
  current_period_end: string | null;       // null = perpetual (ltd) or no sub
  cancel_scheduled: boolean;
  tier_label: string;                      // "Pro", "Pro (Annual)", "Lifetime"
  trial_ends_at: string | null;
  entitlement: 'free'|'starter'|'pro'|'business'; // EFFECTIVE — GATE UI ON THIS, not `plan`
}
```

**The collapse rule (gate on `entitlement`, never `plan`):** `starter→"starter"`; `pro`/`pro_annual`/`ltd`→`"pro"`; `business`/`business_annual`→`"business"`; trial (`plan='free'` + `now() < trial_ends_at`)→`"pro"`. The FE NEVER re-derives this — `entitlement` is server-resolved.

### 1.3 Widened `/auth/me` (`MeResponse`) — the cross-cutting change

WAVE3 §4.2 widens `MeResponse` (the existing `@mesell/core` AuthApiService interface). The FE must extend the EXISTING interface (currently `plan: 'free'`) to:

```ts
interface MeResponse {
  user_id: string;
  phone: string;
  plan: 'free'|'starter'|'pro'|'pro_annual'|'business'|'business_annual'|'ltd'; // WIDENED
  created_at: string;
  last_login_at: string | null;
  onboarding_complete: boolean;
  trial_ends_at?: string | null;          // ADDED (Wave 3)
  entitlement?: 'free'|'starter'|'pro'|'business'; // ADDED (Wave 3) — resolved effective
}
```

This propagates into `AuthUser` (`libs/core/services/auth.service.ts`) — see §4. **This is the auth-singleton-touching part of the wave** and is the highest-risk file (federation singleton; FE-D5 in-memory token).

### 1.4 The 3 error codes (i18n keys, from WAVE3 line 280)

Backend error envelope (the existing `ApiErrorEnvelope` in `@mesell/core`) carries a `validation_message_id` (3-segment key). The three billing errors:

| HTTP | `validation_message_id` | When | FE handling |
|---|---|---|---|
| 409 | `billing.already_subscribed` | subscribe when an active/created sub exists | toast/inline: "You already have an active plan." Refresh subscription view. |
| 409 | `billing.trial_already_used` | start-trial when already trialed / has trial / non-free | toast/inline: "You've already used your free trial." Hide the trial CTA. |
| 404 or 409 | `billing.no_active_subscription` | cancel when no active sub (the **LTD-is-perpetual** case lands here) | NOT an error to the user — show "Your Lifetime plan never expires; nothing to cancel." Treat 404 gracefully. |

> Note: the exact iam exception classes + final 404-vs-409 for cancel are a §7.G founder-gate item on the BACKEND side (WAVE3 R3). The FE must handle BOTH 404 and 409 for `billing.no_active_subscription` to be robust to the backend's final choice. Also: a Razorpay outage on subscribe surfaces as a clean **502** (adapter passthrough, WAVE3 line 279) — FE retries / shows "payment provider unavailable, try again".

The 3 i18n keys + any others (`billing.processing`, `billing.checkout_cancelled`, `billing.activation_pending`, success strings) must be registered in the FE i18n layer **IF** i18n is wired (see §13 D-FE2 — i18n is currently NOT in the FE per coordinator memory; default to plain strings until i18n lands, but namespace them so a later i18n pass is mechanical).

---

## 2. Where billing lives (placement decision — from the LIVE tree)

The live frontend is fully federated: shell (`apps/shell`) + 6 remotes (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-catalog`, `mfe-dashboard`, `mfe-auth`) + shared libs (`@mesell/{core,ui-kit,composites,design-tokens,layout,env}`).

**CRITICAL: `mfe-pricing` is NOT free.** It is the per-catalog **P&L price calculator** at `/catalogs/:id/pricing` (the pricing-engine feature F11), NOT subscription billing. Do NOT put billing into `mfe-pricing` — the names collide but the concerns are unrelated.

**DECISION (recommended, founder to ratify — D-FE1):** create a **NEW 7th remote `mfe-billing`** (`apps/mfe-billing/`), exposing a **Routes array** (`./BillingRoutes`) following the catalog remote's `loadRemoteRoutesWithFallback` precedent (the only Routes-expose remote in V1). Rationale:

- Billing is a self-contained vertical (plans page + account-billing view) with its own service + Razorpay-SDK loading — it matches the "one remote per feature vertical" strangler-fig model exactly.
- It naturally hosts 2+ routes (`/billing/plans`, `/billing/account`) → a Routes-expose remote is the right shape (D31 precedent).
- It keeps the Razorpay `checkout.js` script-injection isolated to one remote, not leaked into the shell or an unrelated remote.
- The auth-singleton consumption (`@mesell/core` `AuthService`, the D22 C1–C5 contract) is identical to `mfe-onboarding`'s ProfileComponent — a proven cross-boundary pattern.

**Alternative (if founder prefers minimal surface):** add billing as routes inside `mfe-onboarding` (the account/profile remote) since billing is account-adjacent. Lower federation overhead (no 7th remoteEntry, no manifest/CI/CDN entry), but couples two concerns and grows that remote's bundle with the Razorpay SDK. The spec is written for the **new-remote** path; the in-onboarding path is a strict subset (same files, different `apps/` dir) and is noted where it diverges.

**Shell wiring (lead-owned root files):** the shell route table (`apps/shell/src/app/app.routes.ts`) gains a `billing` child under the authGuarded shell parent, and the federation manifest (`apps/shell/public/federation.manifest.json`) gains an `mfe-billing` entry. Both are MY files (frontend lead root-wiring) — I apply them at integration, the specialist proposes them.

### 2.1 Routes added

| Route | Guard | Component | Notes |
|---|---|---|---|
| `/billing/plans` | authGuard (shell parent) | `PlansComponent` | the pricing/upgrade page (Scope A+B+C) |
| `/billing/account` | authGuard (shell parent) | `AccountBillingComponent` | current subscription + cancel (Scope D+E) |

Both sit under the existing authGuarded shell empty-path parent (same as `dashboard`/`profile`) — billing requires login. The guard runs in the shell before the remote is fetched (D27). Entry points: a "Plans / Upgrade" sidebar item or a CTA from `profile`/`dashboard` when entitlement is `free`.

> If a PUBLIC pre-auth pricing marketing page is also wanted (unauthenticated visitors browsing tiers), that is a SEPARATE landing concern for `mfe-dashboard` (the public landing remote) and is **OUT OF SCOPE** here — Wave 5 is the authenticated billing surface. Flag to founder if a public pricing page is desired (D-FE3).

---

## 3. Components, services, routes to build

### 3.1 New remote `apps/mfe-billing/` (mirrors the `mfe-catalog`/`mfe-pricing` shape)

Scaffold files (copy the validated SP01/SP05 recipe from coordinator memory — angular.json N+1 project, `native-federation:build` delegating to an `esbuild` `@angular/build:application` target, **a remote REQUIRES its own `src/index.html`** with the remote selector as host element, test-discovery dual-include glob):

```
apps/mfe-billing/
├── federation.config.js          # name: 'mfe-billing'; exposes './BillingRoutes'; shareAll singleton:true strictVersion:false; skip @primeuix/themes (F-001 guard, copy from mfe-pricing)
├── src/
│   ├── index.html                # host element = remote selector (the remote-needs-index gotcha)
│   ├── main.ts                   # initFederation → bootstrap (copy recipe)
│   └── app/
│       ├── public-api.ts         # export { BILLING_ROUTES } from './billing.routes';  (Routes-array expose)
│       ├── billing.routes.ts     # BILLING_ROUTES: Routes — plans + account; route-scoped providers:[BillingApiService]
│       ├── plans/
│       │   ├── plans.component.ts        # PlansComponent — tier cards + CTAs + checkout state machine
│       │   ├── plans.component.spec.ts
│       │   ├── plan-card.component.ts     # one tier card (price, limits, CTA) — child of plans
│       │   └── plan-card.component.spec.ts
│       ├── account/
│       │   ├── account-billing.component.ts   # current sub view + cancel
│       │   └── account-billing.component.spec.ts
│       ├── checkout/
│       │   ├── razorpay-checkout.service.ts   # loads checkout.js, opens widget, resolves on close
│       │   └── razorpay-checkout.service.spec.ts
│       ├── billing-api.service.ts             # the 4 endpoint methods (route-scoped @Injectable(), NOT root — D32)
│       ├── billing-api.service.spec.ts
│       ├── billing.model.ts                   # the §1.2 TS interfaces (remote-private — D11/D17)
│       └── billing.constants.ts               # the static PRICING_LOCKED tier display table
```

- `BillingApiService` is `@Injectable()` route-scoped (provided in `billing.routes.ts` `providers:[]`), NOT `providedIn:'root'` — it is remote-private and travels with the Routes-array expose (D28a/D32 precedent). It consumes `ApiClient` from `@mesell/core`.
- `billing.model.ts` interfaces stay remote-private (no cross-boundary need — only `MeResponse`/`AuthUser` widening crosses, and those live in `@mesell/core` already).
- `billing.constants.ts` holds the **display** table from PRICING_LOCKED v2 §5 (tier name, price, period, limits copy, the "best value"/"most popular" badges). Prices are display-only; the real charge is the Razorpay plan-id config on the backend. Keep this table the single FE source for tier marketing copy.

### 3.2 `@mesell/core` widening (the cross-cutting, singleton-touching change)

`libs/core/services/auth-api.service.ts` — widen `MeResponse` per §1.3 (plan literal + add `trial_ends_at?`, `entitlement?`).
`libs/core/services/auth.service.ts` — widen `AuthUser`:
- `plan?: 'free'` → `plan?: 'free'|'starter'|'pro'|'pro_annual'|'business'|'business_annual'|'ltd'`
- add `trial_ends_at?: string | null` and `entitlement?: 'free'|'starter'|'pro'|'business'`
- update `meToUser(me)` to map the two new fields.
- OPTIONAL convenience: add a `readonly entitlement = computed(() => this._user()?.entitlement ?? 'free')` signal on `AuthService` so any remote can gate UI on `auth.entitlement()` without re-reading `currentUser()` shape. RECOMMENDED — it is the §6 gating primitive.

This is **additive-optional** (no breaking change — matches the existing DECISION-3 additive pattern in AuthUser). It does NOT touch the token, the refresh machinery, or FE-D5. It is still the riskiest file because `@mesell/core` is the federation singleton shared with EVERY remote (the empty-version/strictVersion singleton dedup is already a known live bug — master memory `finding-federation-auth-singleton-not-shared`); any change here must be rebuilt across all remotes consistently. Flag to infra/master at integration.

### 3.3 Shell root-wiring (LEAD-owned — specialist proposes, I apply)

- `apps/shell/src/app/app.routes.ts` — add the `billing` child route (loadChildren via `loadRemoteRoutesWithFallback('mfe-billing', './BillingRoutes')`).
- `apps/shell/public/federation.manifest.json` — add `"mfe-billing": "http://localhost:4207/remoteEntry.json"` (next free dev port; staging/prod URLs are infra-owned per Gate-4 C-RES-2).
- `apps/shell/src/app/layouts/shell/sidebar/sidebar.component.ts` — add a "Plans"/"Billing" nav item (entitlement-aware: emphasise "Upgrade" when `entitlement()==='free'`).
- `angular.json` + `tsconfig.spec.json` — register the `mfe-billing` project + the test-discovery globs (the recurring `../apps/**/*.spec.ts` cwd gotcha — copy SP01 recipe exactly).

---

## 4. AuthService / `@mesell/core` consumption (the C1–C5 contract)

Billing consumes the shared `AuthService` singleton exactly as `mfe-onboarding` ProfileComponent does (proven cross-boundary, D22 C1–C5):
- READ: `auth.currentUser()` / the new `auth.entitlement()` to gate the plans page CTAs and to know the current plan in the account view.
- WRITE: after a successful checkout activation poll OR a successful start-trial, call `auth.refreshUser()` (already exists — re-hydrates `/auth/me` without touching the token/timer) so the shell sidebar + all remotes see the new entitlement immediately. This is the billing-specific use of the existing `refreshUser()` — billing does NOT call `setSession` (that is auth's write path).
- The federation share contract (C1): `mfe-billing/federation.config.js` MUST `shareAll({singleton:true})` so `@mesell/core` resolves to the shell's single AuthService instance. Copy `mfe-pricing`'s config verbatim. **Build assertion (R-W5):** verify no duplicate `_mesell_core` chunk hash divergence vs the shell after build (the known live singleton bug) — see §11 acceptance.

---

## 5. Razorpay Checkout widget + the post-checkout polling state machine

### 5.1 SDK loading (`razorpay-checkout.service.ts`)

- Razorpay Checkout is a hosted script: `https://checkout.razorpay.com/v1/checkout.js`. Inject it lazily (append `<script>` on first use, cache the promise) — do NOT add it to `index.html` globally (keep it in the billing remote only; CSP allowlist impact — see §10/D-FE4).
- On `subscribe` success, open the widget with the returned handle:
  - recurring tiers: `new Razorpay({ key: checkout.key_id, subscription_id: checkout.razorpay_subscription_id, ... })`.
  - ltd: `new Razorpay({ key: checkout.key_id, order_id: checkout.razorpay_order_id, amount: checkout.amount_paise, ... })`.
  - `short_url` is the Razorpay-hosted fallback if the in-page widget cannot open (open in a new tab) — handle as a degraded path.
- Wire the widget callbacks: `handler` (payment submitted), `modal.ondismiss` (user closed/cancelled). **Neither callback is the source of truth** — both transition the FE into the POLLING state (D-D).

### 5.2 The post-checkout polling state machine (the heart of Scope B)

```
[idle]
  │ user clicks Subscribe(tier)
  ▼
[initiating]  ── POST /billing/subscribe ──┐
  │ 409 billing.already_subscribed → [error: already subscribed] → refresh account view
  │ 502 adapter → [error: provider unavailable, retry]
  ▼ (200 → BillingCheckout)
[checkout-open]  ── open Razorpay widget ──┐
  │ modal.ondismiss (no payment)  → [cancelled]  (user backed out; NOT an error; back to idle)
  │ handler fired (payment submitted) ───────┐
  ▼                                          ▼
[pending / "processing your payment"]  ◄─────┘
  │ POLL GET /billing/subscription every Ns, up to MAX attempts
  │   (RECOMMENDED: 3s interval, ~20 attempts ≈ 60s, exponential-ish backoff allowed)
  │ entitlement still 'free' / plan unchanged  → keep polling (show spinner + reassurance copy)
  │ entitlement upgraded (plan reflects tier)  → [activated]  → auth.refreshUser() → success toast → route to /billing/account
  │ poll budget exhausted, still not active    → [pending-timeout]  → "Payment received — activation may take a moment. We'll update automatically."
  │                                              (do NOT show failure; webhook may be delayed. Offer manual 'Refresh status' button + keep a slow background poll or stop and let /auth/me bootstrap catch it.)
  ▼
[activated | pending-timeout | cancelled | error]
```

Key rules:
- **NEVER optimistic.** The plan card does not flip to "active" on widget close — only on a poll that shows the upgraded `entitlement`.
- The pending state has reassuring, non-alarming copy ("This usually takes a few seconds"). A webhook delay is normal, not a failure.
- On `pending-timeout`, do NOT assert failure (the webhook is the truth and may still land). Provide a "Refresh status" button and/or rely on the next `/auth/me` bootstrap (AuthService.bootstrap on reload) to pick it up.
- Implement polling with RxJS (`timer` + `switchMap` + `takeWhile`/`take`), destroy on component teardown (the D18 timer-preserve discipline — a navigate-away must clear the poll, exactly like `mfe-export`'s OnDestroy).
- Use a single `signal`-based state enum on the component for the machine (`'idle'|'initiating'|'checkout-open'|'pending'|'activated'|'pending-timeout'|'cancelled'|'error'`).

### 5.3 Start-trial flow (Scope C)

- CTA visible only when `entitlement()==='free'` AND no `trial_ends_at` on the user. `POST /billing/start-trial` (empty body) → on 200 `auth.refreshUser()` → entitlement becomes `pro` → success toast → route to account view.
- On 409 `billing.trial_already_used` → toast + hide the trial CTA permanently for this user.
- No Razorpay, no widget, no polling — start-trial is synchronous app-side (the grant is immediate, unlike subscribe). After it returns 200 a single `refreshUser()` is enough.

### 5.4 Cancel flow (Scope E)

- In `account-billing.component`, a "Cancel plan" button → MeeConfirmDialog ("Your plan stays active until <entitled_until>. Cancel anyway?") → `POST /billing/cancel` (empty body).
- On 200 `BillingCancelResponse` → show "Cancelled — you keep access until <entitled_until>". `cancel_scheduled` will read true on the next subscription fetch. (The actual downgrade is webhook+sweep driven — do NOT flip to free in the UI; show "scheduled to cancel".)
- On 404/409 `billing.no_active_subscription` → **the LTD-perpetual case**: show "Your Lifetime plan never expires — there's nothing to cancel." Hide the cancel button entirely when `plan==='ltd'` (LTD has no `current_period_end`, perpetual) so the user never reaches this error in normal flow; handle the error defensively for race conditions.

---

## 6. Entitlement-based UI gating (Scope F)

- The gating primitive is `AuthService.entitlement()` (the new computed signal, §3.2) — sourced from `/auth/me` `entitlement`. Gate ON `entitlement`, NEVER `plan` (§1.2 collapse rule).
- **Plans page CTAs** are entitlement-aware:
  - `free` → show "Start free trial" (if not used) + "Upgrade" CTAs on Starter/Pro/Business/LTD.
  - `starter` → "Upgrade to Pro/Business" on higher tiers; current tier shows "Your plan".
  - `pro` → higher tiers upgradable; Starter shown as downgrade (or hidden — D-FE5).
  - `business` → all lower tiers are "Your plan or below"; CTAs hidden/disabled.
- **SKU-cap messaging:** surface the Free=50 SKUs/mo cap (and Starter=150) as a banner/inline note when `entitlement` is `free`/`starter`, with an "Upgrade for unlimited listings" CTA → routes to `/billing/plans`. The actual 402 `PlanLimitExceededError` enforcement is backend; the FE shows the cap proactively + reacts to a 402 (error interceptor surfaces it; the catalog flow shows an upgrade prompt). NOTE: the live Free cap is 100 in code vs 50 in PRICING_LOCKED (BE-PLANGUARD-FREECAP-1, founder-undecided) — the FE should display the value the backend reports, NOT hard-code 50; if no value is surfaced, use the PRICING_LOCKED tier display table copy and flag the discrepancy (D-FE6).
- This is gating for *display/CTA* only — feature access enforcement remains backend (plan_guard). The FE never grants entitlement.
- **`FEATURE_BILLING_ENABLED` off (404):** when `GET /billing/subscription` returns 404, treat billing as unavailable — hide the Plans nav item and all billing CTAs, do not error-toast. The plans page itself (if navigated to directly) shows a graceful "Billing is not available yet" state.

---

## 7. API client methods (mapping to the 4 endpoints)

`billing-api.service.ts` (route-scoped, consumes `@mesell/core` `ApiClient`):

```ts
subscribe(tier): Observable<BillingSubscribeResponse>   // ApiClient.post('/api/v1/billing/subscribe', { tier })
startTrial(): Observable<BillingStartTrialResponse>      // ApiClient.post('/api/v1/billing/start-trial', {})
cancel(): Observable<BillingCancelResponse>              // ApiClient.post('/api/v1/billing/cancel', {})
getSubscription(): Observable<BillingSubscriptionResponse> // ApiClient.get('/api/v1/billing/subscription')
```

- All calls go through `ApiClient` (which prepends `environment.apiBase` and routes via the JWT interceptor). **`withCredentials` MUST be false/default** for `/billing/*` (spec line 398 — billing is JWT-Bearer, NOT the cookie path). Do NOT pass `{ withCredentials: true }`.
- `catchError` in the service surfaces the typed `ApiErrorEnvelope` (`@mesell/core`) so components can switch on `validation_message_id` for the 3 codes + 402 + 502.
- Use `signal`s + RxJS in the component (no NgRx — locked D10). Poll via RxJS `timer`.

---

## 8. Loading / pending / error states (required, per merge-gate)

- Plans page: skeleton on initial `getSubscription()` load; per-card CTA spinner during `initiating`.
- Checkout: a full "Processing your payment…" pending panel during the poll (with the reassurance copy + spinner; never a blank screen).
- Account view: skeleton on load; inline confirm-dialog for cancel; clear "scheduled to cancel" badge when `cancel_scheduled`.
- All error states use a `mee-*` toast/inline (PrimeNG via the ui-kit wrappers ONLY — no direct primeng import outside ui-kit; the billing remote uses `@mesell/ui-kit` + `@mesell/composites` like every other remote).
- Mobile-first: the tier cards must work at 360px (stack vertically) and 1280px (grid). a11y: keyboard-operable CTAs, focus management on the checkout pending panel and confirm dialog, aria-live on the pending/poll status text, color-contrast on tier badges.

---

## 9. Required tests (Vitest via `@angular/build:unit-test`)

(Note: the repo uses Vitest 4 through the Angular builder, NOT Karma/Jasmine — the CLAUDE.md "Karma + Jasmine" line is superseded by the Wave 2B re-scaffold; follow the live toolchain.)

- `billing-api.service.spec.ts` — the 4 methods call the right path/verb/body; `withCredentials` NOT set; error envelopes for 409×2 / 404 / 502 map correctly.
- `razorpay-checkout.service.spec.ts` — SDK script injected once (cached); widget opened with subscription_id vs order_id per tier; `ondismiss`→cancelled, `handler`→pending (Razorpay global mocked).
- `plans.component.spec.ts` — CTA gating per entitlement (free/starter/pro/business); the full polling state machine (idle→initiating→checkout-open→pending→activated AND →pending-timeout AND →cancelled); 409 already-subscribed path; start-trial path + 409 trial-used; poll teardown on destroy (no leaked timer — the D18 assertion).
- `account-billing.component.spec.ts` — renders plan/status/period-end/trial-end; cancel happy path + 404 LTD-perpetual graceful path; cancel button hidden when `plan==='ltd'`.
- `plan-card.component.spec.ts` — renders PRICING_LOCKED display values; CTA label per relative entitlement.
- Shell: add 1–2 federation specs proving `mfe-billing` resolves (the SP01 shell-federation-spec pattern) — test count must NOT drop (the silent-non-discovery hard-reject guard).
- `@mesell/core` `auth.service.spec.ts` — extend to cover the new `entitlement()` computed + widened `AuthUser` mapping in `meToUser`.

Baseline discipline: total test file count must be ≥ current baseline + the new files (a DROP = silent test non-discovery = hard reject; re-confirm the `../apps/**/*.spec.ts` glob).

---

## 10. Federation / infra impact (cross-lead — memo owed)

- **Manifest:** +1 entry (`mfe-billing`) in `apps/shell/public/federation.manifest.json` (dev :4207). Staging/prod URLs are infra-owned (Gate-4 C-RES-2: remotes served off-cluster on GCS/CDN at `remotes.mesell.xyz`). Memo to infra.
- **CI:** the multi-remote cloudbuild matrix (C-CI-1: `cloudbuild.remote.yaml` + `dorny/paths-filter`) must include the new `mfe-billing` path. Memo to infra. A `@mesell/core` change rebuilds ALL remotes (shared lib) — note the billing wave touches `@mesell/core` so a full-fleet rebuild is required (R-W5 singleton consistency).
- **CSP (D-FE4 / C-CSP-1):** Razorpay `checkout.js` adds a NEW external origin (`https://checkout.razorpay.com` + Razorpay's `api.razorpay.com` + lumberjack/CDN origins it pulls). The production CSP (authored ADD-ONLY in MF Sub-plan 7, D42) MUST allowlist Razorpay's script/connect/frame origins. This is a joint FE↔infra item — FE owns the allowlist entries, infra owns the mechanism. Memo to infra. On dev there is no CSP today, so the build is unblocked; this is a staging/prod gate, not a Wave-5-build blocker.
- **Razorpay public key handling (D-FE7):** `key_id` is returned in the `subscribe` response (it is the PUBLIC key — safe in the browser by Razorpay design). The FE does NOT need a build-time Razorpay key; it uses the `key_id` from the API response per call. No FE secret. Confirm with founder that this is the intended pattern (it is the standard Razorpay Checkout pattern) — no `environment.razorpayKey` needed.

---

## 11. Step-3 merge-gate acceptance checklist (the lead's review gate)

The `feature/{name}/frontend` → `feature/{name}` PR is approved only when ALL are checked:

- [ ] `.github/PULL_REQUEST_TEMPLATE/frontend.md` filled COMPLETELY — no `<>` placeholders.
- [ ] `pnpm build` < 90s (CLAUDE.md Decision 12 — stop condition if exceeded). Bundle delta noted; `mfe-billing` is a new lazy remote (no shell initial-bundle regression); the `@mesell/core` widening is type-only/additive (near-zero chunk cost — types erase).
- [ ] Screenshots at 360px AND 1280px for: plans page, checkout pending state, account-billing view, cancel confirm dialog.
- [ ] a11y confirmed: keyboard nav on CTAs + confirm dialog, focus management on pending panel, aria-live on poll status, contrast on tier badges.
- [ ] CI gates 1 (unit) + 3 (lint) green; gates 4+5 advisory.
- [ ] `feature_board_frontend.md` row = IN REVIEW (specialist set it on PR open, D2).
- [ ] The 4 endpoints called via `ApiClient` with `withCredentials` NOT set (JWT-Bearer, not cookie). Verified.
- [ ] Subscribe NEVER optimistically grants — the poll-until-activated state machine is implemented; widget-close alone does not flip the UI. Verified in `plans.component.spec.ts`.
- [ ] All 3 error codes (`billing.already_subscribed`, `billing.trial_already_used`, `billing.no_active_subscription` for BOTH 404 and 409) handled; 402 SKU-cap + 502 adapter handled.
- [ ] LTD-perpetual cancel handled gracefully (no scary error; cancel hidden when `plan==='ltd'`).
- [ ] Gating is on `entitlement`, never `plan`. Verified.
- [ ] `FEATURE_BILLING_ENABLED` off (404) degrades gracefully (CTAs hidden, no error spam).
- [ ] No `primeng` import outside `@mesell/ui-kit` (boundary grep = 0).
- [ ] Test count ≥ baseline + new files (no silent non-discovery); `mfe-billing` specs discovered.
- [ ] `_mesell_core` chunk-hash consistency check across shell + all remotes after rebuild (the live singleton bug guard) — or explicit note that infra owns the fleet rebuild.
- [ ] PrimeNG/ui-kit a11y primitives not violated on the plans/account P0 routes at 360px.
- [ ] Session block = `mesell-razorpay-billing-frontend-session-N`.

---

## 12. OUT OF SCOPE (explicit)

- Backend: the 4 endpoints, entitlement resolver, `MeResponse` backend widening, webhook, i18n key registration on the BACKEND (Wave 3). FE only mirrors the contract.
- The reconciliation/trial-expiry sweep (Wave 4, backend).
- A PUBLIC pre-auth pricing marketing page (`mfe-dashboard` landing concern — D-FE3 flag).
- Dunning email content (legal-writer; FE only surfaces past_due/grace state IF the contract gives it — `status` field; no email UI in Wave 5).
- The per-catalog P&L price calculator (`mfe-pricing` / F11 — unrelated, do NOT touch).
- Multi-seat / team billing UI (V1.5 teams system — Business launches single-user; do NOT advertise seats).
- The production CSP mechanism (MF Sub-plan 7 / infra — FE only contributes the Razorpay allowlist entries).
- Starter Annual (deferred, P7 — not priced, not displayed).
- `feature/{name}` → `develop` approval (founder's gate, D1).

---

## 13. Open decisions / founder flags before build (step-2 gate)

| # | Flag | Recommendation |
|---|---|---|
| **D-FE1** | New `mfe-billing` remote vs routes inside `mfe-onboarding`? | **New remote** (isolates Razorpay SDK + CSP surface; matches one-vertical-per-remote; Routes-expose like catalog). Founder ratify (federation surface +1). |
| **D-FE2** | i18n is NOT wired in the FE (transloco dropped at Wave 2B). Billing strings: plain strings now, or block on i18n? | Plain strings, namespaced (`billing.*`) so a later i18n pass is mechanical. Do NOT block billing on i18n. |
| **D-FE3** | Public pre-auth pricing marketing page wanted? | OUT of Wave 5 (it's a landing/`mfe-dashboard` concern). Flag if desired as a follow-up. |
| **D-FE4** | Razorpay `checkout.js` external origins need a CSP allowlist (prod). | FE contributes the allowlist entries; infra owns the mechanism (MF SP7 / C-CSP-1). Dev unblocked (no CSP). |
| **D-FE5** | Show downgrade CTAs (e.g. Pro user sees Starter) or hide lower tiers? | Hide/disable lower tiers for the current entitlement; show only equal/upgrade. Confirm. |
| **D-FE6** | Free SKU cap: code=100 vs PRICING_LOCKED=50 (BE-PLANGUARD-FREECAP-1 undecided). | FE displays the backend-reported value if surfaced; else PRICING_LOCKED display copy + flag. Do NOT hard-code. |
| **D-FE7** | Razorpay key handling on FE. | Use the PUBLIC `key_id` returned per-call from `subscribe`; NO FE build-time Razorpay key/secret. Standard pattern — confirm. |
| **R1** | The BE→FE contract memo `handoff_contract_razorpay.md` is OWED at Wave 3 PR-merge but NOT yet written. This spec lifts the contract from WAVE3 directly. | Before step-2 dispatch, confirm Wave 3 is merged + reconcile field names against the memo when it lands (memo wins on drift). Do NOT build against an unmerged Wave 3 contract. |
| **R2** | `@mesell/core` (federation singleton) widening + known live singleton-dedup bug (empty version / strictVersion:false). | The widening is additive-optional (low risk) but requires a full-fleet remote rebuild for consistency; coordinate with infra/master (the auth-singleton finding is already open). |

---

## 14. Recommended specialist dispatch (step 2)

**Sequence (services/state first, then pages, then polish — the standard order):**

1. **`meesell-angular-service-builder`** (FIRST) — `@mesell/core` `MeResponse`/`AuthUser` widening + `entitlement()` computed; `billing-api.service.ts` (4 methods); `razorpay-checkout.service.ts` (SDK loading + widget open + close-resolution); `billing.model.ts`; the polling-state-machine logic primitives (RxJS poll util). These gate the components. Touches the riskiest file (`@mesell/core`) — most senior service work.
2. **`meesell-angular-component-builder`** (SECOND, stacks on #1) — `mfe-billing` remote scaffold (federation.config, index.html, main.ts, public-api, billing.routes); `plans.component` + `plan-card`; `account-billing.component`; the state-machine wiring in the component; entitlement gating; the shell route + manifest + sidebar nav-item PROPOSALS (I apply the root-wiring at integration). Most of the surface.
3. **`meesell-angular-ui-styler`** (THIRD, polish) — tier-card responsive grid (360/1280), pending-panel + confirm-dialog styling, a11y (focus/aria-live/contrast), badge/CTA states, the upgrade-banner styling. Final accessibility + responsive pass.

**Split vs sequence:** SEQUENCE, do not parallelise — #2 depends on #1's services/model and on the auth widening; #3 depends on #2's component shells. This is the same proven order used on every prior feature (service → component → styler).

---

## Document control

| Field | Value |
|---|---|
| Document | Razorpay Wave 5 — Frontend Billing UI Task Spec |
| Status | SPEC (HYBRID step-1) — awaits §13 founder go before step-2 dispatch |
| Owner | meesell-frontend-coordinator |
| Pairs with | RAZORPAY_INTEGRATION_SPEC.md §10, WAVE3_ROUTES_TASKSPEC.md (contract), PRICING_LOCKED.md v2 §5 |
| Blocking precondition | Wave 3 merged + `handoff_contract_razorpay.md` reconciled (R1) |
