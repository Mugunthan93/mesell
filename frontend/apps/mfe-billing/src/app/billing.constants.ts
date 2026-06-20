/**
 * billing.constants.ts — Static display table for billing/plans page.
 *
 * Source: docs/PRICING_LOCKED.md v2 §5 (founder-approved 2026-06-18).
 * Prices are DISPLAY-ONLY — the real charge is the Razorpay plan-id config on
 * the backend. This table is the SINGLE FE source for tier marketing copy.
 *
 * NOTE: the Free SKU cap is displayed as 50 here per PRICING_LOCKED v2 §5.
 * A backend discrepancy (BE-PLANGUARD-FREECAP-1: code may enforce 100) is
 * flagged to the founder (D-FE6). The FE shows 50 (the locked spec value);
 * update only when BE-PLANGUARD-FREECAP-1 is resolved.
 *
 * Do NOT import this file from @mesell/core — it is remote-private (billing only).
 */

import type { SubscribableTier, EntitlementLiteral } from './billing.model';

/** Display descriptor for a single tier card on the Plans page. */
export interface TierDisplay {
  /** Tier key — matches SubscribableTier or 'free'. */
  tier: SubscribableTier | 'free';
  /** Display name shown in the card header. */
  name: string;
  /** Monthly display price in INR (integer). 0 for free/trial. */
  priceMonthly: number;
  /** Annual display price in INR (integer). null if not applicable. */
  priceAnnual: number | null;
  /** Billing period label (e.g. "per month", "per year"). */
  periodLabel: string;
  /** Effective entitlement granted by this tier. */
  entitlement: EntitlementLiteral;
  /** Short feature summary lines for the card body. */
  features: string[];
  /** Optional badge text shown on the card (e.g. "Most Popular", "Best Value"). */
  badge?: string;
  /** True when this is a one-time purchase (LTD). */
  isOneTime?: boolean;
  /** Maximum SKUs per month. null = unlimited. */
  skuLimit: number | null;
}

/**
 * TIER_DISPLAY — ordered list of tiers for the Plans page.
 * Display order: Free → Starter → Pro → Business → Pro Annual → Business Annual → LTD.
 * The component may filter/reorder based on the user's current entitlement (D-FE5).
 */
export const TIER_DISPLAY: TierDisplay[] = [
  {
    tier: 'free',
    name: 'Free',
    priceMonthly: 0,
    priceAnnual: null,
    periodLabel: 'forever free',
    entitlement: 'free',
    skuLimit: 50,
    features: [
      '50 SKUs / month',
      'AI catalog generation',
      'Core listing tools',
      'Meesho CSV export',
    ],
  },
  {
    tier: 'starter',
    name: 'Starter',
    priceMonthly: 199,
    priceAnnual: null,
    periodLabel: 'per month',
    entitlement: 'starter',
    skuLimit: 150,
    features: [
      '150 SKUs / month',
      'All AI features',
      'Priority AI queue',
      'Meesho CSV export',
      'Single user',
    ],
  },
  {
    tier: 'pro',
    name: 'Pro',
    priceMonthly: 499,
    priceAnnual: null,
    periodLabel: 'per month',
    entitlement: 'pro',
    skuLimit: null,
    badge: 'Most Popular',
    features: [
      'Unlimited listings',
      'All AI features',
      'Priority AI queue',
      'Meesho CSV export',
      'Single user',
    ],
  },
  {
    tier: 'business',
    name: 'Business',
    priceMonthly: 1999,
    priceAnnual: null,
    periodLabel: 'per month',
    entitlement: 'business',
    skuLimit: null,
    features: [
      'Unlimited SKUs',
      'All AI features',
      'Priority AI queue',
      'Bulk SKU operations',
      'Multi-marketplace prep',
      'Single user (teams V1.5)',
    ],
  },
  {
    tier: 'pro_annual',
    name: 'Pro Annual',
    priceMonthly: 499,  // monthly equivalent for display
    priceAnnual: 4990,
    periodLabel: 'per year',
    entitlement: 'pro',
    skuLimit: null,
    badge: 'Best Value',
    features: [
      'Unlimited listings',
      'All AI features',
      'Priority AI queue',
      'Meesho CSV export',
      '2 months free vs monthly',
    ],
  },
  {
    tier: 'business_annual',
    name: 'Business Annual',
    priceMonthly: 1999,  // monthly equivalent for display
    priceAnnual: 19990,
    periodLabel: 'per year',
    entitlement: 'business',
    skuLimit: null,
    features: [
      'Unlimited SKUs + bulk ops',
      'All AI features',
      'Priority AI queue',
      'Multi-marketplace prep',
      '2 months free vs monthly',
    ],
  },
  {
    tier: 'ltd',
    name: 'Lifetime',
    priceMonthly: 4999,  // one-time price displayed as monthly field for form
    priceAnnual: null,
    periodLabel: 'one-time',
    entitlement: 'pro',
    skuLimit: null,
    isOneTime: true,
    badge: 'Limited to 1,000 spots',
    features: [
      'Pro-for-life',
      'Unlimited listings',
      'All AI features',
      'Priority AI queue',
      'No recurring charge',
    ],
  },
];

/** Error message strings (plain, namespaced — i18n not yet wired, see WAVE5_FRONTEND_TASKSPEC §13 D-FE2). */
export const BILLING_STRINGS = {
  'billing.trial.already_used':
    "You've already used your free Pro trial. Upgrade to keep access.",
  'billing.subscription.already_active':
    'You already have an active subscription.',
  'billing.subscription.none_active':
    "Your Lifetime plan never expires — there's nothing to cancel.",
  'billing.processing':
    'Processing your payment…',
  'billing.activation_pending':
    'Payment received — activation may take a moment. We\'ll update automatically.',
  'billing.checkout_cancelled':
    'Checkout cancelled. You can try again anytime.',
  'billing.provider_unavailable':
    'Payments are temporarily unavailable. Please try again shortly.',
  'billing.generic_error':
    'Something went wrong. Please try again.',
  'billing.trial_started':
    'Your 14-day Pro trial has started! Explore everything Pro has to offer.',
  'billing.cancel_scheduled':
    'Plan cancellation scheduled. You keep full access until your billing period ends.',
  'billing.plan_activated':
    'Plan activated! Welcome to your new subscription.',
} as const;

export type BillingStringKey = keyof typeof BILLING_STRINGS;
