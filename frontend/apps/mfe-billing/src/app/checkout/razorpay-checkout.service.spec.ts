/**
 * razorpay-checkout.service.spec.ts — RazorpayCheckoutService unit tests.
 *
 * Covers:
 *   - SDK script injected once (cached — second call returns the same promise)
 *   - Widget opened with subscription_id for recurring tiers (pro/starter/business)
 *   - Widget opened with order_id + amount_paise for ltd
 *   - modal.ondismiss with no payment → 'cancelled'
 *   - handler fired (payment submitted) → 'payment_submitted'
 *   - short_url fallback when window.Razorpay is absent after SDK load
 *
 * Uses vi.fn() to mock the Razorpay global constructor and the script injection.
 */

import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { RazorpayCheckoutService } from './razorpay-checkout.service';
import type { BillingCheckout } from '../billing.model';

// ─── Mock Razorpay widget ──────────────────────────────────────────────────────

/** Recorded options passed to the Razorpay constructor. */
let capturedOptions: Record<string, unknown> | null = null;
/** Mock Razorpay instance. */
let mockRzpInstance: { open: ReturnType<typeof vi.fn> };

function installRazorpayMock(): void {
  mockRzpInstance = { open: vi.fn() };
  capturedOptions = null;

  (window as { Razorpay?: unknown }).Razorpay = function MockRazorpay(
    options: Record<string, unknown>,
  ) {
    capturedOptions = options;
    return mockRzpInstance;
  };
}

function removeRazorpayMock(): void {
  delete (window as { Razorpay?: unknown }).Razorpay;
}

// ─── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [RazorpayCheckoutService],
  });
  return TestBed.inject(RazorpayCheckoutService);
}

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const RECURRING_CHECKOUT: BillingCheckout = {
  key_id: 'rzp_test_key',
  razorpay_subscription_id: 'sub_abc123',
  razorpay_order_id: null,
  short_url: 'https://rzp.io/fallback',
  amount_paise: null,
  currency: 'INR',
  tier: 'pro',
};

const LTD_CHECKOUT: BillingCheckout = {
  key_id: 'rzp_test_key_ltd',
  razorpay_subscription_id: null,
  razorpay_order_id: 'order_ltd123',
  short_url: null,
  amount_paise: 499900,
  currency: 'INR',
  tier: 'ltd',
};

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('RazorpayCheckoutService', () => {

  beforeEach(() => {
    installRazorpayMock();
  });

  afterEach(() => {
    removeRazorpayMock();
    // Clean up any injected script tags
    document.querySelectorAll('script[src*="checkout.razorpay.com"]').forEach((s) => s.remove());
  });

  // ── SDK loading ──────────────────────────────────────────────────────────

  it('loadSdk() resolves immediately when window.Razorpay is already defined', async () => {
    const service = setup();
    // window.Razorpay is installed by installRazorpayMock()
    await expect(service.loadSdk()).resolves.toBeUndefined();
  });

  it('loadSdk() returns the SAME promise on repeated calls (cached — script injected once)', async () => {
    const service = setup();
    const p1 = service.loadSdk();
    const p2 = service.loadSdk();
    expect(p1).toBe(p2);
  });

  // ── Widget opening — recurring tier ─────────────────────────────────────

  it('openWidget() for recurring tier passes subscription_id to Razorpay constructor', async () => {
    const service = setup();

    // Start the widget open (will resolve when ondismiss is called)
    const resultPromise = service.openWidget(RECURRING_CHECKOUT);

    // Simulate modal dismiss (user cancelled)
    await new Promise<void>((r) => setTimeout(r, 0)); // let microtasks settle

    expect(capturedOptions?.['subscription_id']).toBe('sub_abc123');
    expect(capturedOptions?.['key']).toBe('rzp_test_key');
    expect(capturedOptions?.['order_id']).toBeUndefined();
    expect(mockRzpInstance.open).toHaveBeenCalledTimes(1);

    // Trigger ondismiss to resolve the promise
    const ondismiss = (capturedOptions?.['modal'] as { ondismiss?: () => void })?.ondismiss;
    ondismiss?.();

    const result = await resultPromise;
    expect(result.status).toBe('cancelled');
  });

  // ── Widget opening — LTD (order path) ────────────────────────────────────

  it('openWidget() for ltd tier passes order_id + amount_paise to Razorpay constructor', async () => {
    const service = setup();

    const resultPromise = service.openWidget(LTD_CHECKOUT);
    await new Promise<void>((r) => setTimeout(r, 0));

    expect(capturedOptions?.['order_id']).toBe('order_ltd123');
    expect(capturedOptions?.['amount']).toBe(499900);
    expect(capturedOptions?.['subscription_id']).toBeUndefined();

    // Trigger handler (payment submitted)
    const handler = capturedOptions?.['handler'] as ((_: unknown) => void) | undefined;
    handler?.({ razorpay_payment_id: 'pay_test' });

    const result = await resultPromise;
    expect(result.status).toBe('payment_submitted');
  });

  // ── Callbacks ────────────────────────────────────────────────────────────

  it('modal.ondismiss without handler → "cancelled"', async () => {
    const service = setup();
    const resultPromise = service.openWidget(RECURRING_CHECKOUT);
    await new Promise<void>((r) => setTimeout(r, 0));

    const ondismiss = (capturedOptions?.['modal'] as { ondismiss?: () => void })?.ondismiss;
    ondismiss?.();

    const result = await resultPromise;
    expect(result.status).toBe('cancelled');
  });

  it('handler fired then ondismiss → "payment_submitted" (handler wins, ondismiss no-ops)', async () => {
    const service = setup();
    const resultPromise = service.openWidget(RECURRING_CHECKOUT);
    await new Promise<void>((r) => setTimeout(r, 0));

    const handler = capturedOptions?.['handler'] as ((_: unknown) => void) | undefined;
    const ondismiss = (capturedOptions?.['modal'] as { ondismiss?: () => void })?.ondismiss;

    handler?.({ razorpay_payment_id: 'pay_001' });
    ondismiss?.(); // should be no-op since paymentSubmitted=true

    const result = await resultPromise;
    expect(result.status).toBe('payment_submitted');
  });

  // ── short_url fallback ────────────────────────────────────────────────────

  it('falls back to short_url when window.Razorpay is absent after loadSdk', async () => {
    const service = setup();
    // Remove Razorpay after "load" (simulate CSP stripping the constructor)
    removeRazorpayMock();
    // Reset the cached load promise so openWidget goes through the load path
    // (accessing private field directly in tests is acceptable for this scenario)
    (service as unknown as { _sdkLoadPromise: Promise<void> | null })._sdkLoadPromise = null;

    const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
    const checkout = { ...RECURRING_CHECKOUT, short_url: 'https://rzp.io/fb' };

    // Make loadSdk resolve immediately (window.Razorpay is gone, but promise resolves)
    vi.spyOn(service, 'loadSdk').mockResolvedValue(undefined);

    const result = await service.openWidget(checkout);
    expect(result.status).toBe('short_url_opened');
    expect(openSpy).toHaveBeenCalledWith('https://rzp.io/fb', '_blank', 'noopener,noreferrer');

    openSpy.mockRestore();
  });
});
