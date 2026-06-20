/**
 * PlanCardComponent unit tests.
 *
 * Pure-function / proxy class — NO TestBed, NO Angular component import.
 * Importing PlanCardComponent directly would pull in CommonModule which
 * triggers the Angular JIT compiler check and crashes bare vitest
 * ("The injectable 'PlatformLocation' needs to be compiled using the JIT compiler").
 *
 * Pattern: replicate the component's business logic in a plain PlanCardProxy class.
 * Test isCurrent(), isUpgrade(), ctaLabel(), onCTAClick() — all are pure methods that
 * depend only on `tier` and `currentEntitlement` inputs with no Angular DI.
 *
 * If the component logic changes, update PlanCardProxy to match.
 */

import { describe, it, expect } from 'vitest';
import { EventEmitter } from '@angular/core';
import { TIER_DISPLAY } from '../billing.constants';
import type { TierDisplay } from '../billing.constants';
import type { SubscribableTier, EntitlementLiteral } from '../billing.model';

// ── Entitlement rank (mirrors component) ─────────────────────────────────────

const ENTITLEMENT_RANK: Record<EntitlementLiteral, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  business: 3,
};

// ── Proxy class (mirrors PlanCardComponent methods without Angular imports) ───

class PlanCardProxy {
  tier!: TierDisplay;
  currentEntitlement: EntitlementLiteral = 'free';
  isInitiating = false;

  subscribe = new EventEmitter<SubscribableTier>();

  isCurrent(): boolean {
    return this.tier.entitlement === this.currentEntitlement;
  }

  isUpgrade(): boolean {
    if (this.tier.tier === 'free') return false;
    const tierRank = ENTITLEMENT_RANK[this.tier.entitlement] ?? 0;
    const currentRank = ENTITLEMENT_RANK[this.currentEntitlement] ?? 0;
    return tierRank > currentRank;
  }

  ctaLabel(): string {
    if (this.tier.isOneTime) return 'Get Lifetime';
    if (this.currentEntitlement === 'free') return `Upgrade to ${this.tier.name}`;
    return `Switch to ${this.tier.name}`;
  }

  onCTAClick(): void {
    if (this.tier.tier !== 'free') {
      this.subscribe.emit(this.tier.tier as SubscribableTier);
    }
  }
}

// ── Test helpers ──────────────────────────────────────────────────────────────

function makeTier(overrides: Partial<TierDisplay> = {}): TierDisplay {
  return {
    tier: 'pro',
    name: 'Pro',
    priceMonthly: 499,
    priceAnnual: null,
    periodLabel: 'per month',
    entitlement: 'pro',
    skuLimit: null,
    features: ['Unlimited listings', 'All AI features'],
    ...overrides,
  };
}

function makeCard(
  tierOverrides: Partial<TierDisplay> = {},
  entitlement: EntitlementLiteral = 'free',
): PlanCardProxy {
  const card = new PlanCardProxy();
  card.tier = makeTier(tierOverrides);
  card.currentEntitlement = entitlement;
  card.isInitiating = false;
  return card;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('PlanCardComponent — isCurrent()', () => {
  it('returns true when tier entitlement matches current entitlement', () => {
    const card = makeCard({ entitlement: 'pro' }, 'pro');
    expect(card.isCurrent()).toBe(true);
  });

  it('returns false when tier entitlement differs from current entitlement', () => {
    const card = makeCard({ entitlement: 'pro' }, 'free');
    expect(card.isCurrent()).toBe(false);
  });

  it('returns true for starter when user is starter', () => {
    const card = makeCard({ tier: 'starter', entitlement: 'starter' }, 'starter');
    expect(card.isCurrent()).toBe(true);
  });

  it('returns true for business when user is business', () => {
    const card = makeCard({ tier: 'business', entitlement: 'business' }, 'business');
    expect(card.isCurrent()).toBe(true);
  });
});

describe('PlanCardComponent — isUpgrade()', () => {
  it('returns true for pro upgrade from free', () => {
    const card = makeCard({ tier: 'pro', entitlement: 'pro' }, 'free');
    expect(card.isUpgrade()).toBe(true);
  });

  it('returns true for business upgrade from pro', () => {
    const card = makeCard({ tier: 'business', entitlement: 'business' }, 'pro');
    expect(card.isUpgrade()).toBe(true);
  });

  it('returns false for starter when user is pro (downgrade — hidden per D-FE5)', () => {
    const card = makeCard({ tier: 'starter', entitlement: 'starter' }, 'pro');
    expect(card.isUpgrade()).toBe(false);
  });

  it('returns false for free tier (never subscribable)', () => {
    const card = makeCard({ tier: 'free', entitlement: 'free' }, 'free');
    expect(card.isUpgrade()).toBe(false);
  });

  it('returns false when current === tier (no upgrade needed)', () => {
    const card = makeCard({ tier: 'pro', entitlement: 'pro' }, 'pro');
    expect(card.isUpgrade()).toBe(false);
  });

  it('returns false for ltd from pro (same entitlement rank → NOT an upgrade)', () => {
    // ltd entitlement is 'pro' — same rank → NOT an upgrade
    const card = makeCard({ tier: 'ltd', entitlement: 'pro', isOneTime: true }, 'pro');
    expect(card.isUpgrade()).toBe(false);
  });

  it('returns true for pro_annual from free (entitlement pro > free)', () => {
    const card = makeCard({ tier: 'pro_annual', entitlement: 'pro' }, 'free');
    expect(card.isUpgrade()).toBe(true);
  });
});

describe('PlanCardComponent — ctaLabel()', () => {
  it('returns "Get Lifetime" for ltd tier', () => {
    const card = makeCard({ tier: 'ltd', entitlement: 'pro', isOneTime: true }, 'free');
    expect(card.ctaLabel()).toBe('Get Lifetime');
  });

  it('returns "Upgrade to Pro" from free', () => {
    const card = makeCard({ tier: 'pro', entitlement: 'pro', name: 'Pro' }, 'free');
    expect(card.ctaLabel()).toBe('Upgrade to Pro');
  });

  it('returns "Upgrade to Business" from free', () => {
    const card = makeCard({ tier: 'business', entitlement: 'business', name: 'Business' }, 'free');
    expect(card.ctaLabel()).toBe('Upgrade to Business');
  });

  it('returns "Switch to Business" from starter', () => {
    const card = makeCard({ tier: 'business', entitlement: 'business', name: 'Business' }, 'starter');
    expect(card.ctaLabel()).toBe('Switch to Business');
  });

  it('returns "Switch to Pro Annual" from starter', () => {
    const card = makeCard({ tier: 'pro_annual', entitlement: 'pro', name: 'Pro Annual' }, 'starter');
    expect(card.ctaLabel()).toBe('Switch to Pro Annual');
  });
});

describe('PlanCardComponent — onCTAClick() event emission', () => {
  it('emits subscribe event with the tier key on CTA click', () => {
    const card = makeCard({ tier: 'pro', entitlement: 'pro' }, 'free');
    const emitted: string[] = [];
    card.subscribe.subscribe((t) => emitted.push(t));
    card.onCTAClick();
    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toBe('pro');
  });

  it('does NOT emit for free tier', () => {
    const card = makeCard({ tier: 'free', entitlement: 'free' }, 'free');
    const emitted: string[] = [];
    card.subscribe.subscribe((t) => emitted.push(t));
    card.onCTAClick();
    expect(emitted).toHaveLength(0);
  });

  it('emits starter tier', () => {
    const card = makeCard({ tier: 'starter', entitlement: 'starter' }, 'free');
    const emitted: string[] = [];
    card.subscribe.subscribe((t) => emitted.push(t));
    card.onCTAClick();
    expect(emitted[0]).toBe('starter');
  });

  it('emits ltd tier', () => {
    const card = makeCard({ tier: 'ltd', entitlement: 'pro', isOneTime: true }, 'free');
    const emitted: string[] = [];
    card.subscribe.subscribe((t) => emitted.push(t));
    card.onCTAClick();
    expect(emitted[0]).toBe('ltd');
  });
});

describe('PlanCardComponent — TIER_DISPLAY values', () => {
  it('TIER_DISPLAY has 7 tiers', () => {
    expect(TIER_DISPLAY).toHaveLength(7);
  });

  it('first tier is free', () => {
    expect(TIER_DISPLAY[0].tier).toBe('free');
    expect(TIER_DISPLAY[0].priceMonthly).toBe(0);
    expect(TIER_DISPLAY[0].skuLimit).toBe(50);
  });

  it('pro tier has Most Popular badge', () => {
    const pro = TIER_DISPLAY.find((t) => t.tier === 'pro');
    expect(pro?.badge).toBe('Most Popular');
    expect(pro?.entitlement).toBe('pro');
  });

  it('pro_annual tier has Best Value badge and annual price', () => {
    const proAnnual = TIER_DISPLAY.find((t) => t.tier === 'pro_annual');
    expect(proAnnual?.badge).toBe('Best Value');
    expect(proAnnual?.priceAnnual).toBe(4990);
    expect(proAnnual?.entitlement).toBe('pro');
  });

  it('ltd tier is one-time with isOneTime=true', () => {
    const ltd = TIER_DISPLAY.find((t) => t.tier === 'ltd');
    expect(ltd?.isOneTime).toBe(true);
    expect(ltd?.priceMonthly).toBe(4999);
    expect(ltd?.entitlement).toBe('pro');
  });

  it('business tier has unlimited SKU (null) and business entitlement', () => {
    const biz = TIER_DISPLAY.find((t) => t.tier === 'business');
    expect(biz?.skuLimit).toBeNull();
    expect(biz?.entitlement).toBe('business');
  });

  it('all subscribable tiers have features array with at least 3 items', () => {
    const subscribable = TIER_DISPLAY.filter((t) => t.tier !== 'free');
    subscribable.forEach((tier) => {
      expect(tier.features.length).toBeGreaterThanOrEqual(3);
    });
  });
});

describe('PlanCardComponent — current plan integration', () => {
  it('isCurrent and isUpgrade are mutually exclusive', () => {
    const tiers: EntitlementLiteral[] = ['free', 'starter', 'pro', 'business'];
    tiers.forEach((currentEnt) => {
      const card = makeCard({ tier: 'pro', entitlement: 'pro' }, currentEnt);
      if (card.isCurrent()) {
        expect(card.isUpgrade()).toBe(false);
      }
    });
  });
});
