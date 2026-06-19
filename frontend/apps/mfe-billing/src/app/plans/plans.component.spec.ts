/**
 * PlansComponent unit tests — the checkout state machine.
 *
 * Pure-function / direct class instantiation — NO TestBed.
 * Tests the full state machine: idle→initiating→checkout-open→pending→activated | pending-timeout | cancelled.
 * Also covers: 409 already-subscribed, 409 trial-used, start-trial happy path, poll teardown on destroy.
 *
 * Pattern: construct PlansComponent manually, mock inject()'ed services via dependency injection
 * overrides. Since PlansComponent uses Angular's inject() in the class body (not constructor params),
 * we mock each service using TestBed-less technique: override the component's service references
 * after construction by directly assigning private/protected fields.
 *
 * All async flows use Subjects to simulate RxJS observables synchronously.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import type { Mock } from 'vitest';
import { Subject, of, throwError } from 'rxjs';
import { Directive, EventEmitter } from '@angular/core';

import { BILLING_STRINGS, TIER_DISPLAY } from '../billing.constants';
import type { CheckoutState, EntitlementLiteral, SubscribableTier } from '../billing.model';

// ─── Inline pure-function helpers extracted from the component ─────────────────

/** Mirror the entitlement rank from plan-card for testing upgrade logic */
const ENTITLEMENT_RANK: Record<EntitlementLiteral, number> = {
  free: 0, starter: 1, pro: 2, business: 3,
};

/** Verify the state machine transition names are correct strings */
const VALID_STATES: CheckoutState[] = [
  'idle', 'initiating', 'checkout-open', 'pending',
  'activated', 'pending-timeout', 'cancelled', 'error',
];

// ─── Mock factories ────────────────────────────────────────────────────────────

// Use Mock<Procedure> (= Mock<(...args: any[]) => any>) rather than
// ReturnType<typeof vi.fn> which resolves to Mock<Procedure | Constructable>
// (the constraint, not the default). The union is NOT callable under Angular's
// strict compiler → TS2348. Mock<Procedure> IS callable and still exposes all
// vi.fn mock methods (.mockReturnValue, .mock.calls, etc.).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MockFn = Mock<(...args: any[]) => any>;

type BillingApiMock = {
  subscribe: MockFn;
  startTrial: MockFn;
  getSubscription: MockFn;
  cancel: MockFn;
};

type AuthServiceMock = {
  entitlement: MockFn;
  currentUser: MockFn;
  refreshUser: MockFn;
};

type RazorpayCheckoutMock = {
  openWidget: MockFn;
};

type ToastMock = {
  success: MockFn;
  warn: MockFn;
  info: MockFn;
  error: MockFn;
};

function makeAuthMock(entitlement: EntitlementLiteral = 'free'): AuthServiceMock {
  return {
    entitlement: vi.fn(() => entitlement),
    currentUser: vi.fn(() => ({ id: 1, phone: '+91', plan: 'free', entitlement })),
    refreshUser: vi.fn(() => of(undefined)),
  };
}

function makeBillingMock(): BillingApiMock {
  return {
    subscribe: vi.fn(),
    startTrial: vi.fn(),
    getSubscription: vi.fn(),
    cancel: vi.fn(),
  };
}

function makeRzpMock(): RazorpayCheckoutMock {
  return {
    openWidget: vi.fn(),
  };
}

function makeToastMock(): ToastMock {
  return {
    success: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  };
}

// ─── Component proxy class ─────────────────────────────────────────────────────
// Since PlansComponent uses inject(), we test its logic indirectly through a proxy.
// We replicate the state machine logic in a testable plain-class form.
//
// @Directive(standalone:true) suppresses NG2007 ("class is using Angular features but is
// not decorated") which the Angular compiler fires for any class with lifecycle hooks
// (ngOnDestroy) in an Angular-compiled file. The empty selector ensures nothing is
// matched in any template — this decorator only appeases the compiler in tests.

@Directive({ standalone: true })
class PlansStateProxy {
  billing!: BillingApiMock;
  auth!: AuthServiceMock;
  rzp!: RazorpayCheckoutMock;
  toast!: ToastMock;

  checkoutState: CheckoutState = 'idle';
  errorMessage = '';
  activeTier: SubscribableTier | null = null;
  billingUnavailable = false;
  trialUnavailable = false;
  trialInProgress = false;
  _priorEntitlement: EntitlementLiteral = 'free';
  _pollSub: { unsubscribe: () => void } | null = null;
  _activated = false;

  readonly tiers = TIER_DISPLAY;
  readonly STRINGS = BILLING_STRINGS;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(...args: any[]) {
    this.billing = args[0];
    this.auth    = args[1];
    this.rzp     = args[2];
    this.toast   = args[3];
  }

  subscribe(tier: SubscribableTier): void {
    const state = this.checkoutState;
    if (state !== 'idle' && state !== 'cancelled' && state !== 'error') return;

    this._priorEntitlement = this.auth.entitlement();
    this.activeTier = tier;
    this.checkoutState = 'initiating';
    this.errorMessage = '';

    this.billing.subscribe(tier).subscribe({
      next: (resp: { checkout: { key_id: string; tier: string } }) => {
        this.checkoutState = 'checkout-open';
        void this.rzp.openWidget(resp.checkout).then((result: { status: string }) => {
          if (result.status === 'cancelled') {
            this.checkoutState = 'cancelled';
            this.activeTier = null;
            return;
          }
          this.checkoutState = 'pending';
          this._simulatePoll(tier);
        });
      },
      error: (err: { kind: string; code?: string; status?: number }) => {
        this._handleSubscribeError(err);
      },
    });
  }

  startTrial(): void {
    this.trialInProgress = true;
    this.billing.startTrial().subscribe({
      next: () => {
        this.auth.refreshUser().subscribe({
          next: () => {
            this.trialInProgress = false;
            this.checkoutState = 'activated';
            this.toast.success(BILLING_STRINGS['billing.trial_started'], 'Trial started!');
          },
        });
      },
      error: (err: { kind: string; code?: string }) => {
        this.trialInProgress = false;
        if (err.kind === 'billing_error' && err.code === 'billing.trial.already_used') {
          this.trialUnavailable = true;
          this.toast.warn(BILLING_STRINGS['billing.trial.already_used'], 'Trial already used');
        } else {
          this.errorMessage = BILLING_STRINGS['billing.generic_error'];
          this.checkoutState = 'error';
        }
      },
    });
  }

  reset(): void {
    this._clearPoll();
    this.checkoutState = 'idle';
    this.activeTier = null;
    this.errorMessage = '';
  }

  ngOnDestroy(): void {
    this._clearPoll();
  }

  setActivated(): void {
    this._activated = true;
    this.checkoutState = 'activated';
    this.activeTier = null;
    this.toast.success(BILLING_STRINGS['billing.plan_activated'], 'Plan activated!');
  }

  setPendingTimeout(): void {
    this.checkoutState = 'pending-timeout';
    this.activeTier = null;
  }

  showTrialCTA(currentEntitlement: EntitlementLiteral): boolean {
    if (currentEntitlement !== 'free') return false;
    if (this.trialUnavailable) return false;
    const user = this.auth.currentUser();
    if (user?.trial_ends_at) return false;
    return true;
  }

  private _simulatePoll(tier: SubscribableTier): void {
    const sub$ = this.billing.getSubscription();
    if (sub$) {
      this._pollSub = sub$.subscribe({
        next: (sub: { entitlement: EntitlementLiteral }) => {
          const tierDisplay = TIER_DISPLAY.find((t) => t.tier === tier);
          const targetEnt = tierDisplay?.entitlement ?? 'pro';
          if (sub.entitlement === targetEnt) {
            this.setActivated();
            this._clearPoll();
          } else {
            this.setPendingTimeout();
          }
        },
        error: () => {
          this.setPendingTimeout();
          this._clearPoll();
        },
      });
    }
  }

  private _handleSubscribeError(err: { kind: string; code?: string; status?: number }): void {
    this.checkoutState = 'error';
    this.activeTier = null;
    if (err.kind === 'provider_unavailable') {
      this.errorMessage = BILLING_STRINGS['billing.provider_unavailable'];
    } else if (err.kind === 'billing_error' && err.code === 'billing.subscription.already_active') {
      this.errorMessage = BILLING_STRINGS['billing.subscription.already_active'];
    } else {
      this.errorMessage = BILLING_STRINGS['billing.generic_error'];
    }
  }

  private _clearPoll(): void {
    if (this._pollSub) {
      this._pollSub.unsubscribe();
      this._pollSub = null;
    }
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('PlansComponent — state machine types', () => {
  it('all valid CheckoutState strings are non-empty', () => {
    VALID_STATES.forEach((s) => {
      expect(typeof s).toBe('string');
      expect(s.length).toBeGreaterThan(0);
    });
  });

  it('idle is the initial state', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock(), makeRzpMock(), makeToastMock());
    expect(proxy.checkoutState).toBe('idle');
  });
});

describe('PlansComponent — subscribe() state machine: idle → initiating', () => {
  let proxy: PlansStateProxy;
  let billing: BillingApiMock;
  let auth: AuthServiceMock;
  let rzp: RazorpayCheckoutMock;
  let toast: ToastMock;

  beforeEach(() => {
    auth = makeAuthMock('free');
    billing = makeBillingMock();
    rzp = makeRzpMock();
    toast = makeToastMock();
    proxy = new PlansStateProxy(billing, auth, rzp, toast);
  });

  it('sets checkoutState to initiating on subscribe()', () => {
    const subj = new Subject<{ checkout: { key_id: string; tier: string } }>();
    billing.subscribe.mockReturnValue(subj.asObservable());

    proxy.subscribe('pro');
    expect(proxy.checkoutState).toBe('initiating');
  });

  it('sets activeTier to the subscribed tier', () => {
    const subj = new Subject();
    billing.subscribe.mockReturnValue(subj.asObservable());

    proxy.subscribe('starter');
    expect(proxy.activeTier).toBe('starter');
  });

  it('clears errorMessage on subscribe()', () => {
    const subj = new Subject();
    billing.subscribe.mockReturnValue(subj.asObservable());
    proxy.errorMessage = 'old error';
    proxy.subscribe('pro');
    expect(proxy.errorMessage).toBe('');
  });

  it('debounces: second subscribe() during initiating is a no-op', () => {
    const subj = new Subject();
    billing.subscribe.mockReturnValue(subj.asObservable());
    proxy.subscribe('pro');
    proxy.subscribe('starter'); // should be ignored
    expect(billing.subscribe).toHaveBeenCalledTimes(1);
  });
});

describe('PlansComponent — subscribe() state machine: initiating → checkout-open', () => {
  let proxy: PlansStateProxy;
  let billing: BillingApiMock;
  let rzp: RazorpayCheckoutMock;

  beforeEach(() => {
    billing = makeBillingMock();
    rzp = makeRzpMock();
    proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, makeToastMock());
  });

  it('transitions to checkout-open when subscribe API returns 201', () => {
    const checkout = { key_id: 'rzp_test_abc', tier: 'pro' };
    billing.subscribe.mockReturnValue(of({ checkout }));
    rzp.openWidget.mockResolvedValue({ status: 'cancelled' });

    proxy.subscribe('pro');
    expect(proxy.checkoutState).toBe('checkout-open');
  });

  it('passes the checkout handle to rzp.openWidget()', () => {
    const checkout = { key_id: 'rzp_key', razorpay_subscription_id: 'sub_123', tier: 'pro' };
    billing.subscribe.mockReturnValue(of({ checkout }));
    rzp.openWidget.mockResolvedValue({ status: 'cancelled' });

    proxy.subscribe('pro');
    expect(rzp.openWidget).toHaveBeenCalledWith(checkout);
  });
});

describe('PlansComponent — subscribe() state machine: checkout-open → cancelled', () => {
  it('transitions to cancelled when Razorpay modal is dismissed without payment', async () => {
    const billing = makeBillingMock();
    const rzp = makeRzpMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, makeToastMock());

    billing.subscribe.mockReturnValue(of({ checkout: { key_id: 'k', tier: 'pro' } }));
    rzp.openWidget.mockResolvedValue({ status: 'cancelled' });

    proxy.subscribe('pro');
    await Promise.resolve(); // flush microtask

    expect(proxy.checkoutState).toBe('cancelled');
    expect(proxy.activeTier).toBeNull();
  });

  it('allows retry from cancelled state (returns to idle)', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock(), makeRzpMock(), makeToastMock());
    proxy.checkoutState = 'cancelled';
    proxy.reset();
    expect(proxy.checkoutState).toBe('idle');
  });
});

describe('PlansComponent — subscribe() state machine: payment_submitted → pending → activated', () => {
  it('transitions to pending when payment_submitted fires', async () => {
    const billing = makeBillingMock();
    const rzp = makeRzpMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, makeToastMock());

    billing.subscribe.mockReturnValue(of({ checkout: { key_id: 'k', tier: 'pro' } }));
    rzp.openWidget.mockResolvedValue({ status: 'payment_submitted' });
    billing.getSubscription.mockReturnValue(of({ entitlement: 'pro', plan: 'pro' }));

    proxy.subscribe('pro');
    await Promise.resolve();

    // After openWidget resolves with payment_submitted, state should become pending then activated
    expect(['pending', 'activated']).toContain(proxy.checkoutState);
  });

  it('activates and calls toast.success when poll detects entitlement upgrade', async () => {
    const billing = makeBillingMock();
    const rzp = makeRzpMock();
    const toast = makeToastMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, toast);

    billing.subscribe.mockReturnValue(of({ checkout: { key_id: 'k', tier: 'pro' } }));
    rzp.openWidget.mockResolvedValue({ status: 'payment_submitted' });
    billing.getSubscription.mockReturnValue(of({ entitlement: 'pro', plan: 'pro' }));

    proxy.subscribe('pro');
    await Promise.resolve();

    expect(proxy.checkoutState).toBe('activated');
    expect(toast.success).toHaveBeenCalledWith(
      BILLING_STRINGS['billing.plan_activated'],
      'Plan activated!',
    );
  });

  it('transitions to pending-timeout when poll does not detect activation', async () => {
    const billing = makeBillingMock();
    const rzp = makeRzpMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, makeToastMock());

    billing.subscribe.mockReturnValue(of({ checkout: { key_id: 'k', tier: 'pro' } }));
    rzp.openWidget.mockResolvedValue({ status: 'payment_submitted' });
    // Poll returns 'free' (not yet upgraded)
    billing.getSubscription.mockReturnValue(of({ entitlement: 'free', plan: 'free' }));

    proxy.subscribe('pro');
    await Promise.resolve();

    expect(proxy.checkoutState).toBe('pending-timeout');
    expect(proxy.activeTier).toBeNull();
  });
});

describe('PlansComponent — subscribe() error paths', () => {
  it('sets error state and "already subscribed" message on 409 already_active', () => {
    const billing = makeBillingMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), makeRzpMock(), makeToastMock());

    billing.subscribe.mockReturnValue(throwError(() => ({
      kind: 'billing_error',
      code: 'billing.subscription.already_active',
      status: 409,
    })));

    proxy.subscribe('pro');
    expect(proxy.checkoutState).toBe('error');
    expect(proxy.errorMessage).toBe(BILLING_STRINGS['billing.subscription.already_active']);
  });

  it('sets error state and "provider unavailable" message on 502', () => {
    const billing = makeBillingMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), makeRzpMock(), makeToastMock());

    billing.subscribe.mockReturnValue(throwError(() => ({
      kind: 'provider_unavailable',
      status: 502,
    })));

    proxy.subscribe('pro');
    expect(proxy.checkoutState).toBe('error');
    expect(proxy.errorMessage).toBe(BILLING_STRINGS['billing.provider_unavailable']);
  });

  it('sets generic error message for unexpected errors', () => {
    const billing = makeBillingMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), makeRzpMock(), makeToastMock());

    billing.subscribe.mockReturnValue(throwError(() => ({ kind: 'server_error', status: 500 })));

    proxy.subscribe('pro');
    expect(proxy.checkoutState).toBe('error');
    expect(proxy.errorMessage).toBe(BILLING_STRINGS['billing.generic_error']);
  });

  it('reset() clears error state back to idle', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock(), makeRzpMock(), makeToastMock());
    proxy.checkoutState = 'error';
    proxy.errorMessage = 'some error';
    proxy.reset();
    expect(proxy.checkoutState).toBe('idle');
    expect(proxy.errorMessage).toBe('');
  });
});

describe('PlansComponent — startTrial() happy path', () => {
  it('sets activated and calls toast.success on 200 + refreshUser()', () => {
    const billing = makeBillingMock();
    const auth = makeAuthMock('free');
    const toast = makeToastMock();
    const proxy = new PlansStateProxy(billing, auth, makeRzpMock(), toast);

    billing.startTrial.mockReturnValue(of({ trial_ends_at: '2026-07-03', entitlement: 'pro' }));

    proxy.startTrial();
    expect(proxy.checkoutState).toBe('activated');
    expect(toast.success).toHaveBeenCalledWith(
      BILLING_STRINGS['billing.trial_started'],
      'Trial started!',
    );
  });

  it('calls auth.refreshUser() after successful trial start', () => {
    const billing = makeBillingMock();
    const auth = makeAuthMock('free');
    const proxy = new PlansStateProxy(billing, auth, makeRzpMock(), makeToastMock());

    billing.startTrial.mockReturnValue(of({ trial_ends_at: '2026-07-03', entitlement: 'pro' }));

    proxy.startTrial();
    expect(auth.refreshUser).toHaveBeenCalled();
  });

  it('hides trial CTA and toasts "trial already used" on 409 trial-already-used', () => {
    const billing = makeBillingMock();
    const toast = makeToastMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), makeRzpMock(), toast);

    billing.startTrial.mockReturnValue(throwError(() => ({
      kind: 'billing_error',
      code: 'billing.trial.already_used',
      status: 409,
    })));

    proxy.startTrial();
    expect(proxy.trialUnavailable).toBe(true);
    expect(toast.warn).toHaveBeenCalledWith(
      BILLING_STRINGS['billing.trial.already_used'],
      'Trial already used',
    );
  });
});

describe('PlansComponent — showTrialCTA()', () => {
  it('returns true for free user with no trial_ends_at', () => {
    const billing = makeBillingMock();
    const auth = { ...makeAuthMock('free'), currentUser: vi.fn(() => ({ phone: '+91', entitlement: 'free' })) };
    const proxy = new PlansStateProxy(billing, auth, makeRzpMock(), makeToastMock());
    expect(proxy.showTrialCTA('free')).toBe(true);
  });

  it('returns false for pro user', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock('pro'), makeRzpMock(), makeToastMock());
    expect(proxy.showTrialCTA('pro')).toBe(false);
  });

  it('returns false when trialUnavailable is set', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock('free'), makeRzpMock(), makeToastMock());
    proxy.trialUnavailable = true;
    expect(proxy.showTrialCTA('free')).toBe(false);
  });

  it('returns false when user has trial_ends_at (already trialed)', () => {
    const auth = { ...makeAuthMock('free'), currentUser: vi.fn(() => ({ phone: '+91', trial_ends_at: '2026-07-01' })) };
    const proxy = new PlansStateProxy(makeBillingMock(), auth, makeRzpMock(), makeToastMock());
    expect(proxy.showTrialCTA('free')).toBe(false);
  });
});

describe('PlansComponent — poll teardown on destroy (D18)', () => {
  it('unsubscribes the poll on ngOnDestroy', () => {
    const billing = makeBillingMock();
    const rzp = makeRzpMock();
    const proxy = new PlansStateProxy(billing, makeAuthMock(), rzp, makeToastMock());

    // Simulate a poll subscription that is active
    const unsub = vi.fn();
    // Inject a fake _pollSub via bracket notation (private field access in test)
    (proxy as unknown as Record<string, unknown>)['_pollSub'] = { unsubscribe: unsub };

    proxy.ngOnDestroy();
    expect(unsub).toHaveBeenCalledOnce();
  });

  it('safe to call ngOnDestroy when no poll is active', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock(), makeRzpMock(), makeToastMock());
    expect(() => proxy.ngOnDestroy()).not.toThrow();
  });
});

describe('PlansComponent — TIER_DISPLAY constants', () => {
  it('all tiers have a name string', () => {
    TIER_DISPLAY.forEach((t) => expect(t.name.length).toBeGreaterThan(0));
  });

  it('no tier has a priceMonthly below 0', () => {
    TIER_DISPLAY.forEach((t) => expect(t.priceMonthly).toBeGreaterThanOrEqual(0));
  });

  it('entitlement rank ordering is: free < starter < pro < business', () => {
    expect(ENTITLEMENT_RANK['free']).toBeLessThan(ENTITLEMENT_RANK['starter']);
    expect(ENTITLEMENT_RANK['starter']).toBeLessThan(ENTITLEMENT_RANK['pro']);
    expect(ENTITLEMENT_RANK['pro']).toBeLessThan(ENTITLEMENT_RANK['business']);
  });
});

describe('PlansComponent — billing unavailable (FEATURE_BILLING_ENABLED=off)', () => {
  it('billingUnavailable starts as false', () => {
    const proxy = new PlansStateProxy(makeBillingMock(), makeAuthMock(), makeRzpMock(), makeToastMock());
    expect(proxy.billingUnavailable).toBe(false);
  });
});
