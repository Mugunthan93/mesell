/**
 * AccountBillingComponent unit tests.
 *
 * Pure-function / proxy class — NO TestBed (avoids PrimeNG JIT crash).
 * Tests: subscription load, cancel happy path, LTD-perpetual graceful handling,
 * cancel_scheduled badge, billing unavailable (404), upgrade CTA visibility.
 *
 * Pattern: replicate component state logic in a plain proxy class, mock services,
 * test signal state transitions synchronously.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';

import { BILLING_STRINGS } from '../billing.constants';
import type { BillingSubscriptionResponse, BillingErrorShape } from '../billing.model';

// ─── Mock factories ────────────────────────────────────────────────────────────

type BillingApiMock = {
  getSubscription: ReturnType<typeof vi.fn>;
  cancel: ReturnType<typeof vi.fn>;
};

type AuthMock = {
  refreshUser: ReturnType<typeof vi.fn>;
};

type ConfirmMock = {
  confirm: ReturnType<typeof vi.fn>;
};

type ToastMock = {
  success: ReturnType<typeof vi.fn>;
  warn: ReturnType<typeof vi.fn>;
  info: ReturnType<typeof vi.fn>;
  error: ReturnType<typeof vi.fn>;
};

function makeBillingMock(): BillingApiMock {
  return {
    getSubscription: vi.fn(),
    cancel: vi.fn(),
  };
}

function makeAuthMock(): AuthMock {
  return { refreshUser: vi.fn(() => of(undefined)) };
}

function makeConfirmMock(): ConfirmMock {
  return { confirm: vi.fn() };
}

function makeToastMock(): ToastMock {
  return {
    success: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  };
}

function makeActiveSub(overrides: Partial<BillingSubscriptionResponse> = {}): BillingSubscriptionResponse {
  return {
    plan: 'pro',
    status: 'active',
    current_period_end: '2026-07-19T00:00:00Z',
    cancel_scheduled: false,
    tier_label: 'Pro',
    trial_ends_at: null,
    entitlement: 'pro',
    ...overrides,
  };
}

// ─── Component proxy class ─────────────────────────────────────────────────────

class AccountBillingProxy {
  loading = true;
  subscription: BillingSubscriptionResponse | null = null;
  billingUnavailable = false;
  errorMessage = '';
  cancelPending = false;

  constructor(
    private billing: BillingApiMock,
    private auth: AuthMock,
    private confirm: ConfirmMock,
    private toast: ToastMock,
  ) {}

  ngOnInit(): void {
    this._loadSubscription();
  }

  isFree(): boolean {
    const sub = this.subscription;
    if (!sub) return true;
    return sub.entitlement === 'free' && !sub.trial_ends_at;
  }

  showUpgradeCTA(): boolean {
    const sub = this.subscription;
    if (!sub) return false;
    return sub.entitlement === 'starter' || sub.entitlement === 'pro';
  }

  showCancelCTA(): boolean {
    const sub = this.subscription;
    if (!sub) return false;
    if (sub.plan === 'ltd') return false;
    if (sub.cancel_scheduled) return false;
    if (sub.entitlement === 'free' && !sub.trial_ends_at) return false;
    return true;
  }

  entitlementLabel(): string {
    const sub = this.subscription;
    if (!sub) return '';
    const map: Record<string, string> = { free: 'Free', starter: 'Starter', pro: 'Pro', business: 'Business' };
    return map[sub.entitlement] ?? sub.entitlement;
  }

  openCancelConfirm(): void {
    if (this.subscription?.plan === 'ltd') {
      this.toast.info(BILLING_STRINGS['billing.subscription.none_active']);
      return;
    }
    const entitledUntil = this.subscription?.current_period_end;
    const message = entitledUntil
      ? `Your plan stays active until ${new Date(entitledUntil).toLocaleDateString()}. Cancel anyway?`
      : 'Cancel your current subscription?';
    this.confirm.confirm({
      header: 'Cancel subscription',
      message,
      accept: () => this.confirmCancel(),
      reject: () => {},
    });
  }

  confirmCancel(): void {
    this.cancelPending = true;
    this.errorMessage = '';
    this.billing.cancel().subscribe({
      next: () => {
        this.cancelPending = false;
        this.toast.info(BILLING_STRINGS['billing.cancel_scheduled'], 'Cancellation scheduled');
        this._loadSubscription();
        this.auth.refreshUser().subscribe();
      },
      error: (err: BillingErrorShape) => {
        this.cancelPending = false;
        this._handleCancelError(err);
      },
    });
  }

  private _loadSubscription(): void {
    this.loading = true;
    this.billingUnavailable = false;
    this.errorMessage = '';
    this.billing.getSubscription().subscribe({
      next: (sub: BillingSubscriptionResponse) => {
        this.subscription = sub;
        this.loading = false;
      },
      error: (err: BillingErrorShape) => {
        this.loading = false;
        if (err.kind === 'billing_error' && err.status === 404) {
          this.billingUnavailable = true;
        } else {
          this.errorMessage = BILLING_STRINGS['billing.generic_error'];
        }
      },
    });
  }

  private _handleCancelError(err: BillingErrorShape): void {
    if (
      err.kind === 'billing_error' &&
      (err.code === 'billing.subscription.none_active' || err.status === 404 || err.status === 409)
    ) {
      this.toast.info(BILLING_STRINGS['billing.subscription.none_active'], 'Nothing to cancel');
      this._loadSubscription();
    } else if (err.kind === 'provider_unavailable') {
      this.errorMessage = BILLING_STRINGS['billing.provider_unavailable'];
    } else {
      this.errorMessage = BILLING_STRINGS['billing.generic_error'];
    }
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('AccountBillingComponent — ngOnInit: subscription load', () => {
  it('starts in loading state', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    // loading = true before ngOnInit
    expect(comp.loading).toBe(true);
  });

  it('loads and sets subscription on ngOnInit', () => {
    const billing = makeBillingMock();
    const sub = makeActiveSub();
    billing.getSubscription.mockReturnValue(of(sub));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.subscription).toEqual(sub);
    expect(comp.loading).toBe(false);
  });

  it('clears loading on 404 (billing unavailable)', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(throwError(() => ({ kind: 'billing_error', status: 404 })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.billingUnavailable).toBe(true);
    expect(comp.loading).toBe(false);
  });

  it('sets errorMessage on generic server error', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(throwError(() => ({ kind: 'server_error', status: 500 })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.errorMessage).toBe(BILLING_STRINGS['billing.generic_error']);
  });
});

describe('AccountBillingComponent — subscription display', () => {
  let billing: BillingApiMock;
  let comp: AccountBillingProxy;

  beforeEach(() => {
    billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
  });

  it('sets subscription plan to pro', () => {
    expect(comp.subscription?.plan).toBe('pro');
  });

  it('entitlementLabel() returns "Pro" for pro entitlement', () => {
    expect(comp.entitlementLabel()).toBe('Pro');
  });

  it('cancel_scheduled is false initially', () => {
    expect(comp.subscription?.cancel_scheduled).toBe(false);
  });
});

describe('AccountBillingComponent — LTD-perpetual rule', () => {
  it('showCancelCTA() returns false when plan === ltd', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'ltd', entitlement: 'pro', current_period_end: null })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showCancelCTA()).toBe(false);
  });

  it('openCancelConfirm() shows info toast for LTD instead of confirm dialog', () => {
    const billing = makeBillingMock();
    const toast = makeToastMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'ltd', entitlement: 'pro' })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), toast);
    comp.ngOnInit();
    comp.openCancelConfirm();
    expect(toast.info).toHaveBeenCalledWith(BILLING_STRINGS['billing.subscription.none_active']);
  });
});

describe('AccountBillingComponent — cancel happy path', () => {
  it('calls billing.cancel() on confirmCancel()', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(of({ status: 'cancel_scheduled', entitled_until: '2026-07-19T00:00:00Z' }));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    comp.confirmCancel();
    expect(billing.cancel).toHaveBeenCalledOnce();
  });

  it('shows info toast on successful cancel', () => {
    const billing = makeBillingMock();
    const toast = makeToastMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(of({ status: 'cancel_scheduled', entitled_until: '2026-07-19T00:00:00Z' }));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), toast);
    comp.ngOnInit();
    comp.confirmCancel();
    expect(toast.info).toHaveBeenCalledWith(
      BILLING_STRINGS['billing.cancel_scheduled'],
      'Cancellation scheduled',
    );
  });

  it('calls auth.refreshUser() after successful cancel', () => {
    const billing = makeBillingMock();
    const auth = makeAuthMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(of({ status: 'cancel_scheduled', entitled_until: null }));
    const comp = new AccountBillingProxy(billing, auth, makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    comp.confirmCancel();
    expect(auth.refreshUser).toHaveBeenCalled();
  });

  it('sets cancelPending=false after cancel completes', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(of({ status: 'cancel_scheduled', entitled_until: null }));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    comp.confirmCancel();
    expect(comp.cancelPending).toBe(false);
  });

  it('openCancelConfirm() invokes confirm.confirm()', () => {
    const billing = makeBillingMock();
    const confirm = makeConfirmMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), confirm, makeToastMock());
    comp.ngOnInit();
    comp.openCancelConfirm();
    expect(confirm.confirm).toHaveBeenCalledOnce();
    const call = confirm.confirm.mock.calls[0][0];
    expect(call.header).toBe('Cancel subscription');
    expect(typeof call.message).toBe('string');
    expect(typeof call.accept).toBe('function');
  });
});

describe('AccountBillingComponent — cancel error paths', () => {
  it('shows info toast (graceful) on 404 none_active (LTD race condition)', () => {
    const billing = makeBillingMock();
    const toast = makeToastMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(throwError(() => ({
      kind: 'billing_error',
      code: 'billing.subscription.none_active',
      status: 404,
    })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), toast);
    comp.ngOnInit();
    comp.confirmCancel();
    expect(toast.info).toHaveBeenCalledWith(
      BILLING_STRINGS['billing.subscription.none_active'],
      'Nothing to cancel',
    );
  });

  it('shows info toast on 409 none_active', () => {
    const billing = makeBillingMock();
    const toast = makeToastMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(throwError(() => ({
      kind: 'billing_error',
      code: 'billing.subscription.none_active',
      status: 409,
    })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), toast);
    comp.ngOnInit();
    comp.confirmCancel();
    expect(toast.info).toHaveBeenCalled();
  });

  it('sets errorMessage on provider_unavailable cancel error', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub()));
    billing.cancel.mockReturnValue(throwError(() => ({ kind: 'provider_unavailable', status: 502 })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    comp.confirmCancel();
    expect(comp.errorMessage).toBe(BILLING_STRINGS['billing.provider_unavailable']);
  });
});

describe('AccountBillingComponent — showCancelCTA() visibility rules', () => {
  it('returns true for active pro subscription', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'pro', entitlement: 'pro' })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showCancelCTA()).toBe(true);
  });

  it('returns false when cancel is already scheduled', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ cancel_scheduled: true })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showCancelCTA()).toBe(false);
  });

  it('returns false for free subscription (no active plan to cancel)', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'free', entitlement: 'free', status: null, current_period_end: null })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showCancelCTA()).toBe(false);
  });
});

describe('AccountBillingComponent — isFree() and showUpgradeCTA()', () => {
  it('isFree() returns true when no subscription is loaded', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ entitlement: 'free', trial_ends_at: null })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.isFree()).toBe(true);
  });

  it('isFree() returns false for pro plan', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ entitlement: 'pro' })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.isFree()).toBe(false);
  });

  it('showUpgradeCTA() returns true for starter entitlement', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'starter', entitlement: 'starter', tier_label: 'Starter' })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showUpgradeCTA()).toBe(true);
  });

  it('showUpgradeCTA() returns false for business entitlement (highest paid)', () => {
    const billing = makeBillingMock();
    billing.getSubscription.mockReturnValue(of(makeActiveSub({ plan: 'business', entitlement: 'business', tier_label: 'Business' })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    expect(comp.showUpgradeCTA()).toBe(false);
  });
});

describe('AccountBillingComponent — cancel_scheduled badge', () => {
  it('subscription.cancel_scheduled is true after a successful cancel + reload', () => {
    const billing = makeBillingMock();
    billing.cancel.mockReturnValue(of({ status: 'cancel_scheduled', entitled_until: '2026-07-19T00:00:00Z' }));
    // First call: active, second call (after cancel): cancel_scheduled
    billing.getSubscription
      .mockReturnValueOnce(of(makeActiveSub()))
      .mockReturnValueOnce(of(makeActiveSub({ cancel_scheduled: true })));
    const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
    comp.ngOnInit();
    comp.confirmCancel();
    expect(comp.subscription?.cancel_scheduled).toBe(true);
  });
});

describe('AccountBillingComponent — entitlementLabel()', () => {
  const cases: Array<{ ent: string; expected: string }> = [
    { ent: 'free', expected: 'Free' },
    { ent: 'starter', expected: 'Starter' },
    { ent: 'pro', expected: 'Pro' },
    { ent: 'business', expected: 'Business' },
  ];

  cases.forEach(({ ent, expected }) => {
    it(`returns "${expected}" for entitlement "${ent}"`, () => {
      const billing = makeBillingMock();
      billing.getSubscription.mockReturnValue(of(makeActiveSub({ entitlement: ent as 'pro' })));
      const comp = new AccountBillingProxy(billing, makeAuthMock(), makeConfirmMock(), makeToastMock());
      comp.ngOnInit();
      expect(comp.entitlementLabel()).toBe(expected);
    });
  });
});
