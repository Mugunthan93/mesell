/**
 * billing.model.ts — Wire-contract DTOs for the 4 billing endpoints.
 *
 * Source of truth: handoff_contract_razorpay.md §1-§3 + WAVE5_FRONTEND_TASKSPEC.md §1.2.
 * All interfaces are REMOTE-PRIVATE — only MeResponse/AuthUser widening crosses
 * the @mesell/core boundary (see libs/core/services/auth-api.service.ts).
 *
 * Key contract rules:
 *  - Gate UI on `entitlement` (4-value), NEVER on `plan` (7-value cadence field).
 *  - POST /billing/subscribe does NOT grant the plan (webhook-driven); poll getSubscription().
 *  - withCredentials MUST be false/default — billing endpoints use JWT Bearer (not cookie).
 *  - Tier 'free' is NOT subscribable (not in SubscribableTier union).
 */

// ─── Tiers ────────────────────────────────────────────────────────────────────

/** All possible raw plan values returned by /auth/me and /billing/subscription. */
export type PlanLiteral =
  | 'free'
  | 'starter'
  | 'pro'
  | 'pro_annual'
  | 'business'
  | 'business_annual'
  | 'ltd';

/** Subscribable tiers (passed as `tier` in POST /billing/subscribe request body). */
export type SubscribableTier =
  | 'starter'
  | 'pro'
  | 'pro_annual'
  | 'business'
  | 'business_annual'
  | 'ltd';

/** Resolved effective entitlement (4-value collapse). Gate UI on this. */
export type EntitlementLiteral = 'free' | 'starter' | 'pro' | 'business';

// ─── Request bodies ───────────────────────────────────────────────────────────

/** POST /api/v1/billing/subscribe — request body. */
export interface BillingSubscribeRequest {
  tier: SubscribableTier;
}

// ─── Response shapes ──────────────────────────────────────────────────────────

/**
 * Razorpay checkout handle returned inside BillingSubscribeResponse.
 * ADVISORY — the plan is NOT granted on this call (webhook-driven).
 *
 * key_id: the PUBLIC Razorpay key — safe to use in the browser widget.
 * razorpay_subscription_id: set for recurring tiers (starter/pro/pro_annual/business/business_annual).
 * razorpay_order_id: set for ltd (one-time order).
 * short_url: Razorpay-hosted checkout fallback (open in new tab if in-page widget fails).
 * amount_paise: integer paise (for ltd display and order amount); may be null for subscriptions.
 * currency: always "INR".
 * tier: echoes the requested tier.
 */
export interface BillingCheckout {
  key_id: string;
  razorpay_subscription_id?: string | null;
  razorpay_order_id?: string | null;
  short_url?: string | null;
  amount_paise?: number | null;
  currency: string;
  tier: string;
}

/**
 * POST /api/v1/billing/subscribe — 201 response.
 * The `checkout` object is ADVISORY: use it to open the Razorpay widget,
 * then POLL GET /billing/subscription to confirm activation (never optimistic).
 */
export interface BillingSubscribeResponse {
  checkout: BillingCheckout;
}

/**
 * POST /api/v1/billing/start-trial — 200 response.
 * App-side only. No Razorpay object, no charge. Grant is immediate
 * (unlike subscribe) — a single refreshUser() call is sufficient.
 */
export interface BillingStartTrialResponse {
  /** ISO-8601 UTC absolute expiry (now + 14 days). */
  trial_ends_at: string;
  /** Always "pro" for a live trial. */
  entitlement: 'pro';
}

/**
 * POST /api/v1/billing/cancel — 200 response.
 * Schedules cancel_at_cycle_end. Does NOT immediately downgrade.
 * LTD cannot be cancelled (backend returns 404; cancel button hidden for plan==='ltd').
 */
export interface BillingCancelResponse {
  /** Always "cancel_scheduled" on 200 success. */
  status: 'cancel_scheduled';
  /**
   * current_period_end — entitlement maintained until this datetime.
   * May be null for edge states (e.g. if the subscription has already ended).
   */
  entitled_until: string | null;
}

/**
 * GET /api/v1/billing/subscription — 200 response.
 * Poll this after the Razorpay widget closes to detect webhook-driven plan grant.
 * The canonical screen data for the account-billing view.
 */
export interface BillingSubscriptionResponse {
  /** Raw plan stored on users.plan. Use `entitlement` for feature gating. */
  plan: PlanLiteral;
  /**
   * Razorpay subscription status string (active/authenticated/created/cancelled/...).
   * null for free/trial users who have no Razorpay subscription.
   */
  status: string | null;
  /** Billing cycle end (subscription period end); null for free/ltd. */
  current_period_end: string | null;
  /** true once cancel-at-cycle-end has been scheduled. */
  cancel_scheduled: boolean;
  /** Human-readable label for the subscription management screen (e.g. "Pro", "Pro (Annual)"). */
  tier_label: string;
  /** ISO-8601 UTC trial expiry; null if no trial. */
  trial_ends_at: string | null;
  /**
   * RESOLVED effective entitlement — GATE UI ON THIS.
   * Computed by backend plan_guard.resolve_entitlement — FE never re-derives.
   */
  entitlement: EntitlementLiteral;
}

// ─── Error shapes ─────────────────────────────────────────────────────────────

/**
 * Billing error codes from the backend error envelope.
 * Switch on `validation_message_id` from the ApiErrorEnvelope (not `detail`).
 * Source: handoff_contract_razorpay.md §3.
 */
export type BillingErrorCode =
  | 'billing.trial.already_used'
  | 'billing.subscription.already_active'
  | 'billing.subscription.none_active';

/** Typed billing error emitted by BillingApiService methods on 409/404. */
export interface BillingError {
  kind: 'billing_error';
  code: BillingErrorCode | string; // string fallback for unexpected codes
  detail: string;
  status: number;
}

/** 502 Razorpay upstream unavailable. */
export interface BillingProviderUnavailableError {
  kind: 'provider_unavailable';
  status: 502;
}

/** Generic server / network error on billing calls. */
export interface BillingServerError {
  kind: 'server_error';
  status: number;
}

/** Union of typed non-throwing billing error shapes. */
export type BillingErrorShape =
  | BillingError
  | BillingProviderUnavailableError
  | BillingServerError;

// ─── Checkout / polling state machine ────────────────────────────────────────

/**
 * CheckoutState — the state-machine enum used by the Plans component.
 *
 * Transitions:
 *   idle → initiating (on Subscribe click)
 *   initiating → checkout-open (on 201 subscribe response) | error (on 409/502)
 *   checkout-open → pending (handler fired OR modal.ondismiss after payment)
 *   checkout-open → cancelled (modal.ondismiss with no payment started)
 *   pending → activated (poll detects entitlement upgrade)
 *   pending → pending-timeout (poll budget exhausted — NOT a failure)
 *   Any terminal → idle (on explicit reset or navigation)
 */
export type CheckoutState =
  | 'idle'
  | 'initiating'
  | 'checkout-open'
  | 'pending'
  | 'activated'
  | 'pending-timeout'
  | 'cancelled'
  | 'error';

/** Poll configuration constants. */
export const POLL_INTERVAL_MS  = 3_000;   // 3 seconds between polls
export const POLL_MAX_ATTEMPTS = 20;      // ~60 seconds total budget
