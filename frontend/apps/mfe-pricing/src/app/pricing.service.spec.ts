/**
 * pricing.service.spec.ts — PricingApiService tests (§12.M forward estimator).
 *
 * CONTRACT CONFIRMED: backend/app/modules/pricing/schemas.py (PR #285, commit fd4331d).
 *
 * Validation requirements (§12.M):
 *   - URL asserted EXACTLY: /api/v1/products/{id}/price-calc
 *   - Request body required keys: meesho_price + input_cost (NEVER target_margin_pct)
 *   - Optional request keys: commission_pct, return_rate_pct, mrp (all pass-through)
 *   - Response maps §12.M NEW keys:
 *       estimated_payout, estimated_payout_wdrp, margin_pct, markup_pct,
 *       wdrp_price, total_deductions, referral_commission, shipping_charge,
 *       logistics_fee, fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss
 *   - §12.E DEAD keys NOT on type: seller_price, commission_amount, gst_amount, profit_pct
 *   - Alert codes: NEGATIVE_PAYOUT / LOW_MARGIN / SHIPPING_DOMINATES
 *     (§12.M dead: THIN_PROFIT / HIGH_MRP_MULTIPLIER)
 *   - Error matrix: 401→EMPTY / 404→unavailable / 400→validation / 5xx→server_error
 *   - NO 422 branch: 422 treated as server_error (§12.M (4): 422 path is dead)
 *   - NO retryOn503: exactly ONE request per call (POST non-idempotent, §3.2)
 *   - Decimal wire-type: all monetary/pct fields are string (R-W6-6)
 */

import { describe, it, expect, afterEach } from 'vitest';
import { TestBed }                          from '@angular/core/testing';
import { provideHttpClient, withFetch }     from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
}                                           from '@angular/common/http/testing';
import { firstValueFrom }                   from 'rxjs';

import { ApiClient } from '@mesell/core';

import { PricingApiService }                from './pricing.service';
import type { PriceCalcRequest, PriceCalcResponse } from './pricing.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PRODUCT_ID = 'prod-uuid-001';
const ENDPOINT   = `/api/v1/products/${PRODUCT_ID}/price-calc`;

/** Minimal valid request — only required fields. */
const VALID_REQUEST_MINIMAL: PriceCalcRequest = {
  meesho_price: '499.00',
  input_cost:   '300.00',
};

/** Request with optional seller-estimator fields. */
const VALID_REQUEST_FULL: PriceCalcRequest = {
  meesho_price:    '499.00',
  input_cost:      '300.00',
  commission_pct:  '4.00',
  return_rate_pct: '10.00',
  mrp:             '599.00',
};

/**
 * Server 200-OK response — §12.M field set (all Decimal fields as strings, R-W6-6).
 * NEW fields vs §12.E: wdrp_price, estimated_payout, estimated_payout_wdrp, margin_pct,
 *   markup_pct, total_deductions, referral_commission, shipping_charge, logistics_fee,
 *   fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss.
 * DEAD vs §12.E: seller_price, commission_amount, gst_amount, profit_pct.
 */
const MOCK_RESPONSE: PriceCalcResponse = {
  mrp:                   '599.00',
  meesho_price:          '499.00',
  wdrp_price:            '479.00',
  input_cost:            '300.00',
  commission_pct:        '4.00',
  referral_commission:   '19.96',
  shipping_charge:       '58.00',
  logistics_fee:         '12.00',
  fixed_fee:             '5.00',
  gst_pct:               '18.00',
  gst_on_fees:           '17.09',
  tcs:                   '1.00',
  tds:                   '1.00',
  return_rate_pct:       '0.00',
  rto_expected_loss:     '0.00',
  total_deductions:      '114.05',
  estimated_payout:      '384.95',
  estimated_payout_wdrp: '364.95',
  profit:                '84.95',
  margin_pct:            '17.02',
  markup_pct:            '28.32',
  alerts:                [],
  calculated_at:         '2026-06-18T10:00:00Z',
};

/** Response with NEGATIVE_PAYOUT alert — §12.M new alert; 200, not a 4xx. */
const MOCK_RESPONSE_NEGATIVE_PAYOUT: PriceCalcResponse = {
  ...MOCK_RESPONSE,
  estimated_payout: '-20.00',
  profit:           '-320.00',
  margin_pct:       '-4.01',
  markup_pct:       '-6.67',
  alerts: [
    { code: 'NEGATIVE_PAYOUT', message_id: 'pricing.alert.negative_payout', severity: 'warning' },
  ],
};

/** Response with LOW_MARGIN + SHIPPING_DOMINATES (§12.M new alert codes). */
const MOCK_RESPONSE_WITH_ALERTS: PriceCalcResponse = {
  ...MOCK_RESPONSE,
  alerts: [
    { code: 'LOW_MARGIN',         message_id: 'pricing.alert.low_margin',          severity: 'warning' },
    { code: 'SHIPPING_DOMINATES', message_id: 'pricing.alert.shipping_dominates',   severity: 'info'    },
  ],
};

// ── TestBed setup ─────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
      ApiClient,
      PricingApiService,
    ],
  });
  return {
    service:    TestBed.inject(PricingApiService),
    controller: TestBed.inject(HttpTestingController),
  };
}

// ── Happy path ─────────────────────────────────────────────────────────────────

describe('PricingApiService — happy path (§12.M forward estimator)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends POST to the exact /price-calc URL', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.method).toBe('POST');
    req.flush(MOCK_RESPONSE);
  });

  it('sends body with meesho_price and input_cost — §12.M primary required fields', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe();

    const req  = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;
    expect(body['meesho_price']).toBe('499.00');
    expect(body['input_cost']).toBe('300.00');
    req.flush(MOCK_RESPONSE);
  });

  it('§12.M: NEVER sends target_margin_pct (dead field removed in §12.M)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe();

    const req  = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;
    // target_margin_pct is DEAD in §12.M — must never appear in the request body
    expect(body).not.toHaveProperty('target_margin_pct');
    req.flush(MOCK_RESPONSE);
  });

  it('passes optional commission_pct + return_rate_pct + mrp when provided', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_FULL).subscribe();

    const req  = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;
    expect(body['commission_pct']).toBe('4.00');
    expect(body['return_rate_pct']).toBe('10.00');
    expect(body['mrp']).toBe('599.00');
    req.flush(MOCK_RESPONSE);
  });

  it('emits PriceCalcResponse on 200 with §12.M NEW output fields', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse, got error shape');

    // §12.M primary outputs
    expect(result.estimated_payout).toBe('384.95');
    expect(result.estimated_payout_wdrp).toBe('364.95');
    expect(result.margin_pct).toBe('17.02');
    expect(result.markup_pct).toBe('28.32');
    expect(result.wdrp_price).toBe('479.00');
    expect(result.total_deductions).toBe('114.05');

    // §12.M new deduction breakdown fields
    expect(result.referral_commission).toBe('19.96');
    expect(result.shipping_charge).toBe('58.00');
    expect(result.logistics_fee).toBe('12.00');
    expect(result.fixed_fee).toBe('5.00');
    expect(result.gst_on_fees).toBe('17.09');
    expect(result.tcs).toBe('1.00');
    expect(result.tds).toBe('1.00');
    expect(result.rto_expected_loss).toBe('0.00');

    // Common fields still present
    expect(result.profit).toBe('84.95');
    expect(result.meesho_price).toBe('499.00');
    expect(result.input_cost).toBe('300.00');
    expect(result.mrp).toBe('599.00');
    expect(result.commission_pct).toBe('4.00');
    expect(result.alerts).toHaveLength(0);
  });

  it('§12.E dead fields not on response type (TypeScript enforces; runtime confirms fixture)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    // These keys do not exist on the §12.M interface or fixture
    const r = result as unknown as Record<string, unknown>;
    expect(r['seller_price']).toBeUndefined();
    expect(r['commission_amount']).toBeUndefined();
    expect(r['gst_amount']).toBeUndefined();
    expect(r['profit_pct']).toBeUndefined();
  });

  it('NEGATIVE_PAYOUT on negative payout returns 200 with alert — not a 4xx (§12.M (4))', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_NEGATIVE_PAYOUT);
    const result = await promise;

    // Must be PriceCalcResponse (not an error shape) — 200 with alert
    if ('kind' in result) throw new Error('Expected PriceCalcResponse, not an error');
    expect(result.estimated_payout).toBe('-20.00');
    expect(result.alerts).toHaveLength(1);
    expect(result.alerts[0].code).toBe('NEGATIVE_PAYOUT');
    expect(result.alerts[0].message_id).toBe('pricing.alert.negative_payout');
    expect(result.alerts[0].severity).toBe('warning');
  });

  it('emits §12.M new alert codes: LOW_MARGIN + SHIPPING_DOMINATES', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_WITH_ALERTS);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(result.alerts).toHaveLength(2);
    expect(result.alerts[0].code).toBe('LOW_MARGIN');
    expect(result.alerts[0].severity).toBe('warning');
    expect(result.alerts[1].code).toBe('SHIPPING_DOMINATES');
    expect(result.alerts[1].severity).toBe('info');
    // §12.M dead alert codes must not appear
    const codes = result.alerts.map((a) => a.code);
    expect(codes).not.toContain('THIN_PROFIT');
    expect(codes).not.toContain('HIGH_MRP_MULTIPLIER');
  });

  it('Decimal string fields are strings (R-W6-6 — NOT numbers)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    // All monetary/pct fields MUST be strings (Pydantic v2 Decimal → JSON string)
    expect(typeof result.meesho_price).toBe('string');
    expect(typeof result.wdrp_price).toBe('string');
    expect(typeof result.input_cost).toBe('string');
    expect(typeof result.estimated_payout).toBe('string');
    expect(typeof result.estimated_payout_wdrp).toBe('string');
    expect(typeof result.profit).toBe('string');
    expect(typeof result.margin_pct).toBe('string');
    expect(typeof result.markup_pct).toBe('string');
    expect(typeof result.total_deductions).toBe('string');
    expect(typeof result.commission_pct).toBe('string');
    expect(typeof result.referral_commission).toBe('string');
    expect(typeof result.shipping_charge).toBe('string');
  });

  it('mrp is null when not provided in request (nullable field)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    const responseWithNullMrp: PriceCalcResponse = { ...MOCK_RESPONSE, mrp: null };
    controller.expectOne(ENDPOINT).flush(responseWithNullMrp);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(result.mrp).toBeNull();
  });

  it('does NOT add Authorization header manually (jwtInterceptor owns auth)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(MOCK_RESPONSE);
  });
});

// ── Error matrix ──────────────────────────────────────────────────────────────

describe('PricingApiService — error matrix (§12.M degradation matrix, DECISION-1)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('401 → EMPTY (refreshInterceptor logout path; no emission)', async () => {
    const { service, controller } = setup();
    let emitted   = false;
    let completed = false;

    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe({
      next:     () => { emitted = true; },
      complete: () => { completed = true; },
    });

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(emitted).toBe(false);
    expect(completed).toBe(true); // EMPTY completes silently
  });

  it('404 → emits PriceCalcUnavailableError with kind="unavailable"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Price Calculator is disabled in this environment' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise;
    expect(result).toMatchObject({ kind: 'unavailable' });
    // No breakdown keys — DECISION-1
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_payout']).toBeUndefined();
    expect(r['profit']).toBeUndefined();
  });

  it('404 with "not found" detail → reason="not_found" (cross-tenant ownership gate)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Product not found or access denied.' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise;
    if (!('kind' in result) || result.kind !== 'unavailable') {
      throw new Error('Expected unavailable error');
    }
    expect(result.reason).toBe('not_found');
  });

  it('404 without "not found" detail → reason="flag_off" (FEATURE_PRICE_CALCULATOR_ENABLED=false)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Price Calculator is disabled in this environment' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise;
    if (!('kind' in result) || result.kind !== 'unavailable') {
      throw new Error('Expected unavailable error');
    }
    expect(result.reason).toBe('flag_off');
  });

  it('400 → emits PriceCalcValidationError with kind="validation"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'meesho_price must be greater than 0.' },
      { status: 400, statusText: 'Bad Request' },
    );

    const result = await promise;
    expect(result).toMatchObject({
      kind:   'validation',
      detail: 'meesho_price must be greater than 0.',
    });
    // No breakdown keys — DECISION-1
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_payout']).toBeUndefined();
    expect(r['profit']).toBeUndefined();
  });

  it('400 with no error body → uses fallback detail string', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(null, { status: 400, statusText: 'Bad Request' });
    const result = await promise;

    if (!('kind' in result) || result.kind !== 'validation') {
      throw new Error('Expected validation error');
    }
    expect(result.detail).toBeTruthy(); // fallback string
  });

  it('§12.M (4): 422 is DEAD — treated as server_error (not commission_missing)', async () => {
    // 422 pricing.commission.missing removed in §12.M — commission is seller-entered.
    // If a 422 reaches the service (should never happen), it falls to catch-all → server_error.
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Unprocessable Entity (should never occur in §12.M).' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise;
    // Must be server_error — NOT commission_missing (type deleted in §12.M)
    expect(result).toMatchObject({ kind: 'server_error' });
    if ('kind' in result) {
      expect(result.kind).not.toBe('commission_missing');
    }
  });

  it('500 → emits {kind:"server_error"} — explicit shape, not EMPTY (spec §3.1 retry affordance)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Internal Server Error' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    const result = await promise;
    // Must emit server_error — NOT EMPTY (EMPTY would throw in firstValueFrom)
    expect(result).toMatchObject({ kind: 'server_error' });
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_payout']).toBeUndefined();
    expect(r['profit']).toBeUndefined();
  });

  it('503 → emits {kind:"server_error"} (5xx; no auto-retry — POST non-idempotent, §3.2)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Service Unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    const result = await promise;
    expect(result).toMatchObject({ kind: 'server_error' });
  });

  it('network/non-HTTP error → emits {kind:"server_error"} (spec §3.1 retry affordance)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    // Simulate network error via HttpTestingController.error()
    controller.expectOne(ENDPOINT).error(new ProgressEvent('error'));

    const result = await promise;
    expect(result).toMatchObject({ kind: 'server_error' });
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_payout']).toBeUndefined();
    expect(r['profit']).toBeUndefined();
  });
});

// ── No retryOn503 guard ───────────────────────────────────────────────────────

describe('PricingApiService — no retryOn503 (§3.2 POST non-idempotent)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends exactly ONE request on 503 (no auto-retry)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL).subscribe();

    // expectOne() throws if more than one request dispatched
    const req = controller.expectOne(ENDPOINT);
    req.flush({ detail: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });
    // controller.verify() in afterEach confirms no extra requests
  });
});

// ── §12.M request body contract ──────────────────────────────────────────────

describe('PricingApiService — §12.M request body contract (dead keys absent)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('minimal request has meesho_price + input_cost only — no extra fields injected', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, { meesho_price: '399.00', input_cost: '200.00' }).subscribe();

    const req  = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;

    // Required fields present
    expect(body['meesho_price']).toBe('399.00');
    expect(body['input_cost']).toBe('200.00');

    // §12.M DEAD key
    expect(body).not.toHaveProperty('target_margin_pct');

    // Optional fields not in minimal request
    expect(body).not.toHaveProperty('commission_pct');
    expect(body).not.toHaveProperty('return_rate_pct');
    expect(body).not.toHaveProperty('mrp');

    req.flush(MOCK_RESPONSE);
  });

  it('override_shipping (not override_shipping_fee) is the correct field name', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, {
      meesho_price:      '499.00',
      input_cost:        '300.00',
      override_shipping: '45.00',
    }).subscribe();

    const req  = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;
    expect(body['override_shipping']).toBe('45.00');
    // Incorrect alias must NOT be used
    expect(body).not.toHaveProperty('override_shipping_fee');

    req.flush(MOCK_RESPONSE);
  });
});

// ── Decimal string parsing (R-W6-6) ──────────────────────────────────────────

describe('PricingApiService — Decimal-string fields for arithmetic (R-W6-6)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('estimated_payout "384.95" is parseable to positive number', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    const payout = parseFloat(result.estimated_payout);
    expect(payout).toBeGreaterThan(0);
    expect(payout).toBeCloseTo(384.95, 2);
  });

  it('negative estimated_payout "-20.00" parses to negative (NEGATIVE_PAYOUT badge)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_NEGATIVE_PAYOUT);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(parseFloat(result.estimated_payout)).toBeLessThan(0);
  });

  it('margin_pct and markup_pct are distinct string fields (§12.M split from single profit_pct)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST_MINIMAL);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(typeof result.margin_pct).toBe('string');
    expect(typeof result.markup_pct).toBe('string');
    // They are distinct values: margin = % of meesho_price, markup = % of input_cost
    expect(result.margin_pct).not.toBe(result.markup_pct);
  });
});
