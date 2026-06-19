/**
 * billing-api.service.spec.ts — BillingApiService unit tests.
 *
 * Covers: happy paths (4 methods), withCredentials NOT set, error envelope
 * mapping for 409×2 / 404 / 502 / 401 pass-through.
 *
 * Uses Angular's HttpTestingController (via provideHttpClientTesting).
 * BillingApiService is route-scoped, so it is provided directly in TestBed.
 *
 * NOTE on testing framework: the project uses Vitest through @angular/build:unit-test
 * (not Karma/Jasmine — see WAVE5_FRONTEND_TASKSPEC.md §9 note). Import vi from 'vitest'.
 */

import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withFetch,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';

import { ApiClient } from '@mesell/core';
import { BillingApiService } from './billing-api.service';
import type {
  BillingSubscribeResponse,
  BillingStartTrialResponse,
  BillingCancelResponse,
  BillingSubscriptionResponse,
  BillingErrorShape,
} from './billing.model';

// ─── Setup ────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      BillingApiService,
      ApiClient,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
    ],
  });
  return {
    service:    TestBed.inject(BillingApiService),
    controller: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
});

// ─── Helper fixtures ──────────────────────────────────────────────────────────

const MOCK_SUBSCRIPTION: BillingSubscriptionResponse = {
  plan: 'pro',
  status: 'active',
  current_period_end: '2026-07-19T00:00:00Z',
  cancel_scheduled: false,
  tier_label: 'Pro',
  trial_ends_at: null,
  entitlement: 'pro',
};

const MOCK_CHECKOUT_RESPONSE: BillingSubscribeResponse = {
  checkout: {
    key_id: 'rzp_test_abc123',
    razorpay_subscription_id: 'sub_xyz',
    razorpay_order_id: null,
    short_url: 'https://rzp.io/test',
    amount_paise: null,
    currency: 'INR',
    tier: 'pro',
  },
};

const MOCK_TRIAL_RESPONSE: BillingStartTrialResponse = {
  trial_ends_at: '2026-07-03T09:15:00Z',
  entitlement: 'pro',
};

const MOCK_CANCEL_RESPONSE: BillingCancelResponse = {
  status: 'cancel_scheduled',
  entitled_until: '2026-07-19T00:00:00Z',
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('BillingApiService', () => {

  // ── subscribe() ────────────────────────────────────────────────────────────

  describe('subscribe()', () => {
    it('POST /api/v1/billing/subscribe with the tier body', () => {
      const { service, controller } = setup();
      let result: BillingSubscribeResponse | undefined;

      service.subscribe('pro').subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/billing/subscribe');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ tier: 'pro' });
      // CRITICAL: withCredentials must NOT be set (JWT Bearer, not cookie path)
      expect(req.request.withCredentials).toBe(false);
      req.flush(MOCK_CHECKOUT_RESPONSE, { status: 201, statusText: 'Created' });

      expect(result?.checkout.key_id).toBe('rzp_test_abc123');
      expect(result?.checkout.razorpay_subscription_id).toBe('sub_xyz');
    });

    it('emits BillingError on 409 already_active', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.subscribe('pro').subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/subscribe');
      req.flush(
        {
          detail: 'Already subscribed',
          validation_message_id: 'billing.subscription.already_active',
        },
        { status: 409, statusText: 'Conflict' },
      );

      expect(caught?.kind).toBe('billing_error');
      expect((caught as { code?: string })?.code).toBe('billing.subscription.already_active');
      expect((caught as { status?: number })?.status).toBe(409);
    });

    it('emits BillingProviderUnavailableError on 502', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.subscribe('pro').subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/subscribe');
      req.flush({ detail: 'Bad Gateway' }, { status: 502, statusText: 'Bad Gateway' });

      expect(caught?.kind).toBe('provider_unavailable');
      expect((caught as { status?: number })?.status).toBe(502);
    });

    it('passes through 401 as raw HttpErrorResponse (interceptor chain owns it)', () => {
      const { service, controller } = setup();
      let caught: unknown;

      service.subscribe('pro').subscribe({ error: (e: unknown) => (caught = e) });

      const req = controller.expectOne('/api/v1/billing/subscribe');
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

      // 401 must NOT be wrapped as BillingErrorShape
      expect(caught).toBeTruthy();
      expect((caught as { kind?: string })?.kind).toBeUndefined();
    });

    it('subscribes with ltd tier (order_id path)', () => {
      const { service, controller } = setup();
      const ltdResponse: BillingSubscribeResponse = {
        checkout: {
          key_id: 'rzp_test_ltd',
          razorpay_subscription_id: null,
          razorpay_order_id: 'order_abc',
          short_url: null,
          amount_paise: 499900,
          currency: 'INR',
          tier: 'ltd',
        },
      };
      let result: BillingSubscribeResponse | undefined;

      service.subscribe('ltd').subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/billing/subscribe');
      expect(req.request.body).toEqual({ tier: 'ltd' });
      req.flush(ltdResponse, { status: 201, statusText: 'Created' });

      expect(result?.checkout.razorpay_order_id).toBe('order_abc');
      expect(result?.checkout.amount_paise).toBe(499900);
    });
  });

  // ── startTrial() ───────────────────────────────────────────────────────────

  describe('startTrial()', () => {
    it('POST /api/v1/billing/start-trial with empty body', () => {
      const { service, controller } = setup();
      let result: BillingStartTrialResponse | undefined;

      service.startTrial().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/billing/start-trial');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      expect(req.request.withCredentials).toBe(false);
      req.flush(MOCK_TRIAL_RESPONSE, { status: 200, statusText: 'OK' });

      expect(result?.entitlement).toBe('pro');
      expect(result?.trial_ends_at).toBe('2026-07-03T09:15:00Z');
    });

    it('emits BillingError on 409 trial_already_used', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.startTrial().subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/start-trial');
      req.flush(
        { detail: 'Trial used', validation_message_id: 'billing.trial.already_used' },
        { status: 409, statusText: 'Conflict' },
      );

      expect(caught?.kind).toBe('billing_error');
      expect((caught as { code?: string })?.code).toBe('billing.trial.already_used');
    });
  });

  // ── cancel() ──────────────────────────────────────────────────────────────

  describe('cancel()', () => {
    it('POST /api/v1/billing/cancel with empty body', () => {
      const { service, controller } = setup();
      let result: BillingCancelResponse | undefined;

      service.cancel().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/billing/cancel');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      expect(req.request.withCredentials).toBe(false);
      req.flush(MOCK_CANCEL_RESPONSE, { status: 200, statusText: 'OK' });

      expect(result?.status).toBe('cancel_scheduled');
      expect(result?.entitled_until).toBe('2026-07-19T00:00:00Z');
    });

    it('emits BillingError on 404 none_active (LTD-perpetual path)', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.cancel().subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/cancel');
      req.flush(
        { detail: 'No active subscription', validation_message_id: 'billing.subscription.none_active' },
        { status: 404, statusText: 'Not Found' },
      );

      expect(caught?.kind).toBe('billing_error');
      expect((caught as { code?: string })?.code).toBe('billing.subscription.none_active');
      expect((caught as { status?: number })?.status).toBe(404);
    });
  });

  // ── getSubscription() ─────────────────────────────────────────────────────

  describe('getSubscription()', () => {
    it('GET /api/v1/billing/subscription — returns BillingSubscriptionResponse', () => {
      const { service, controller } = setup();
      let result: BillingSubscriptionResponse | undefined;

      service.getSubscription().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/billing/subscription');
      expect(req.request.method).toBe('GET');
      expect(req.request.withCredentials).toBe(false);
      req.flush(MOCK_SUBSCRIPTION, { status: 200, statusText: 'OK' });

      expect(result?.plan).toBe('pro');
      expect(result?.entitlement).toBe('pro');
      expect(result?.cancel_scheduled).toBe(false);
    });

    it('emits BillingError on 404 (FEATURE_BILLING_ENABLED off)', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.getSubscription().subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/subscription');
      req.flush(
        { detail: 'Not found' },
        { status: 404, statusText: 'Not Found' },
      );

      expect(caught?.kind).toBe('billing_error');
      expect((caught as { status?: number })?.status).toBe(404);
    });

    it('emits BillingServerError on 500', () => {
      const { service, controller } = setup();
      let caught: BillingErrorShape | undefined;

      service.getSubscription().subscribe({
        error: (e: BillingErrorShape) => (caught = e),
      });

      const req = controller.expectOne('/api/v1/billing/subscription');
      req.flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Server Error' });

      expect(caught?.kind).toBe('server_error');
      expect((caught as { status?: number })?.status).toBe(500);
    });
  });
});
