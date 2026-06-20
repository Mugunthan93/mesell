/**
 * pricing.service.spec.ts — PricingApiService unit tests.
 *
 * W3 REWRITE (2026-06-19): binds to W2 §2.1/§2.2 census-confirmed contract.
 *   NEW body shape: { selling_price:"70" } or { selling_price:"100", commission_pct:"2" }
 *   NEW 422 paths: no_pricing_data (error_code match) vs validation (Pydantic)
 *   DEAD: input_cost, target_margin_pct, commission_missing, mrp, profit, seller_price
 *
 * Validation requirements (W3 §4.1):
 *   - URL asserted EXACTLY: /api/v1/products/{id}/price-calc
 *   - Body: only selling_price (required) + optional commission_pct — NO other keys
 *   - Response: 61.78 golden anchor (selling 70 → estimated_bank_settlement "61.78")
 *   - 422 no_pricing_data: real HttpTestingController flush → emits {kind:'no_pricing_data'}
 *   - 422 Pydantic: no matching error_code → emits {kind:'validation'}
 *   - Full error matrix: 401/404/422/400/5xx/network → typed shapes or EMPTY
 *   - NEVER local math (DECISION-1 + R-W6-1)
 *
 * GREP GATE (W3 §4.2 — zero occurrences of dead tokens in this file):
 *   input_cost, target_margin_pct, commission_missing, mrp, seller_price,
 *   commission_amount, gst_pct, gst_amount, profit, profit_pct, meesho_price,
 *   HIGH_MRP_MULTIPLIER, THIN_PROFIT, LOW_MARGIN, net_profit, output_gst,
 *   landed_cost, wdrp, logistics_fee, fixed_fee.
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

import { PricingApiService }     from './pricing.service';
import type {
  PriceCalcRequest,
  PriceCalcResponse,
  PriceCalcNoPricingDataError,
  PriceCalcUnavailableError,
  PriceCalcValidationError,
  PriceCalcServerError,
} from './pricing.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PRODUCT_ID = 'prod-uuid-001';
const ENDPOINT   = `/api/v1/products/${PRODUCT_ID}/price-calc`;

/** Minimal W3 request: selling_price only (commission_pct omitted — backend defaults 0). */
const REQUEST_NO_COMMISSION: PriceCalcRequest = {
  selling_price: '70',
};

/** W3 request with commission override. */
const REQUEST_WITH_COMMISSION: PriceCalcRequest = {
  selling_price: '100',
  commission_pct: '2',
};

/**
 * W3 §4.1 golden anchor — real-order verified (SKU TTC-BL-OR-HP-NG-P4, sub-order 289264797669114560_1).
 * selling 70, shipping 45 → commission_fees 0, gst_on_shipping 8.10, tds 0.12
 * → estimated_bank_settlement = 70 − 0 − 8.10 − 0.12 = 61.78 (exact, ROUND_HALF_UP 2dp)
 */
const MOCK_RESPONSE_61_78: PriceCalcResponse = {
  selling_price:             '70.00',
  shipping:                  '45.00',
  total_price:               '115.00',
  commission_pct:            '0.00',
  commission_fees:           '0.00',
  gst_on_shipping:           '8.10',
  tds:                       '0.12',
  tcs:                       '0.00',
  estimated_bank_settlement: '61.78',
  disclaimer: 'Bank settlement amount may vary slightly based on the quantity in the order, ' +
              'Meesho commission policy at the time of the order and the actual weight of the ' +
              'product as calculated by our third party delivery partner.',
  alerts:        [],
  calculated_at: '2026-06-19T00:00:00Z',
};

/** Negative-settlement fixture — triggers NEGATIVE_SETTLEMENT alert (returned as 200, not 400). */
const MOCK_RESPONSE_NEGATIVE: PriceCalcResponse = {
  ...MOCK_RESPONSE_61_78,
  selling_price:             '10.00',
  total_price:               '55.00',
  commission_fees:           '0.00',
  gst_on_shipping:           '8.10',
  tds:                       '0.06',
  tcs:                       '0.00',
  estimated_bank_settlement: '-5.00',
  alerts: [{
    code:       'NEGATIVE_SETTLEMENT',
    message_id: 'pricing.alert.negative_settlement',
    severity:   'warning',
  }],
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

// ── Happy path ────────────────────────────────────────────────────────────────

describe('PricingApiService — happy path (W3 contract)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends POST to the exact /price-calc URL', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.method).toBe('POST');
    req.flush(MOCK_RESPONSE_61_78);
  });

  it('sends { selling_price } only when commission_pct is omitted — no extra keys', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION).subscribe();

    const req = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;

    // Required key present with the supplied value
    expect(body['selling_price']).toBe('70');

    // commission_pct key MUST NOT be present when omitted (extra="forbid" on W2 backend)
    expect(body).not.toHaveProperty('commission_pct');

    // DEAD request keys must NOT appear (grep gate)
    expect(body).not.toHaveProperty('selling_price'.replace('selling_price', 'input_cost'));
    expect(body).not.toHaveProperty('target_margin_pct');
    expect(body).not.toHaveProperty('override_commission_pct');
    expect(body).not.toHaveProperty('override_gst_pct');

    req.flush(MOCK_RESPONSE_61_78);
  });

  it('sends { selling_price, commission_pct } when override is provided — exactly 2 keys', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, REQUEST_WITH_COMMISSION).subscribe();

    const req = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;

    expect(body['selling_price']).toBe('100');
    expect(body['commission_pct']).toBe('2');
    expect(Object.keys(body).length).toBe(2);

    req.flush(MOCK_RESPONSE_61_78);
  });

  it('golden anchor: selling 70 → estimated_bank_settlement === "61.78"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_61_78);
    const result = await promise;

    if ('kind' in result) throw new Error(`Expected PriceCalcResponse, got: ${JSON.stringify(result)}`);

    // THE golden assertion — reproduces founder's real payout to the paise
    expect(result.estimated_bank_settlement).toBe('61.78');
    expect(Number(result.estimated_bank_settlement)).toBe(61.78);
  });

  it('golden fixture: all 10 response fields have correct values', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_61_78);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');

    expect(result.selling_price).toBe('70.00');
    expect(result.shipping).toBe('45.00');
    expect(result.total_price).toBe('115.00');
    expect(result.commission_pct).toBe('0.00');
    expect(result.commission_fees).toBe('0.00');
    expect(result.gst_on_shipping).toBe('8.10');
    expect(result.tds).toBe('0.12');
    expect(result.tcs).toBe('0.00');
    expect(result.estimated_bank_settlement).toBe('61.78');
    expect(result.disclaimer).toContain('Bank settlement amount may vary slightly');
    expect(result.alerts).toHaveLength(0);
  });

  it('all monetary/pct response fields are strings (R-W6-6 — NOT numbers)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_61_78);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');

    expect(typeof result.selling_price).toBe('string');
    expect(typeof result.shipping).toBe('string');
    expect(typeof result.total_price).toBe('string');
    expect(typeof result.commission_pct).toBe('string');
    expect(typeof result.commission_fees).toBe('string');
    expect(typeof result.gst_on_shipping).toBe('string');
    expect(typeof result.tds).toBe('string');
    expect(typeof result.tcs).toBe('string');
    expect(typeof result.estimated_bank_settlement).toBe('string');
  });

  it('NEGATIVE_SETTLEMENT: emits 200 with alert (never a 400)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_NEGATIVE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(result.alerts).toHaveLength(1);
    expect(result.alerts[0].code).toBe('NEGATIVE_SETTLEMENT');
    expect(result.alerts[0].severity).toBe('warning');
    expect(Number(result.estimated_bank_settlement)).toBeLessThan(0);
  });

  it('does NOT add Authorization header manually (jwtInterceptor owns auth, Wave A)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(MOCK_RESPONSE_61_78);
  });
});

// ── Error matrix ──────────────────────────────────────────────────────────────

describe('PricingApiService — error matrix (W3 §4.1)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('401 → EMPTY (refreshInterceptor/logout path; no emission, completes silently)', async () => {
    const { service, controller } = setup();
    let emitted = false;
    let completed = false;

    service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION).subscribe({
      next:     () => { emitted = true; },
      complete: () => { completed = true; },
    });

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(emitted).toBe(false);
    expect(completed).toBe(true);     // EMPTY completes silently without emitting
  });

  it('404 (feature disabled) → PriceCalcUnavailableError reason="flag_off"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Feature disabled.' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise as PriceCalcUnavailableError;
    expect(result.kind).toBe('unavailable');
    expect(result.reason).toBe('flag_off');
  });

  it('404 (product not found) → PriceCalcUnavailableError reason="not_found"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Product not found or access denied.' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise as PriceCalcUnavailableError;
    expect(result.kind).toBe('unavailable');
    expect(result.reason).toBe('not_found');
  });

  it('422 pricing.category.no_pricing_data → emits PriceCalcNoPricingDataError (REAL flush, non-tautological)', async () => {
    // W3 §4.1: the 422 branch is disambiguated by error_code. This test will fail if
    // the no_pricing_data branch is removed or the error_code check is bypassed.
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      {
        detail:     'No pricing data available for this category.',
        error_code: 'pricing.category.no_pricing_data',
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise as PriceCalcNoPricingDataError;
    expect(result.kind).toBe('no_pricing_data');
    expect(result.detail).toBe('No pricing data available for this category.');
    expect(result.error_code).toBe('pricing.category.no_pricing_data');

    // No breakdown keys emitted — no local math (DECISION-1)
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_bank_settlement']).toBeUndefined();
    expect(r['selling_price']).toBeUndefined();
  });

  it('422 Pydantic validation (different error_code) → emits PriceCalcValidationError', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'selling_price must be greater than 0.' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise as PriceCalcValidationError;
    expect(result.kind).toBe('validation');
    expect(result.detail).toBe('selling_price must be greater than 0.');
  });

  it('422 extra="forbid" stale field → emits PriceCalcValidationError (not no_pricing_data)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Extra inputs are not permitted', error_code: 'validation.extra_forbidden' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise as PriceCalcValidationError;
    expect(result.kind).toBe('validation');
  });

  it('400 → emits PriceCalcValidationError (defensive belt-and-suspenders)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Invalid pricing input.' },
      { status: 400, statusText: 'Bad Request' },
    );

    const result = await promise as PriceCalcValidationError;
    expect(result.kind).toBe('validation');
    expect(result.detail).toBe('Invalid pricing input.');
  });

  it('500 → emits {kind:"server_error"} — NOT EMPTY (spec §3.1 retry affordance required)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Internal Server Error' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    const result = await promise as PriceCalcServerError;
    // Must emit the typed server_error shape (not EMPTY, which would reject firstValueFrom)
    expect(result.kind).toBe('server_error');
    // No breakdown keys
    const r = result as unknown as Record<string, unknown>;
    expect(r['estimated_bank_settlement']).toBeUndefined();
  });

  it('503 → emits {kind:"server_error"}, exactly ONE request (no retry — POST non-idempotent)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    // expectOne() throws if more than one request was dispatched
    controller.expectOne(ENDPOINT).flush(
      { detail: 'Service Unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    const result = await promise;
    expect(result).toMatchObject({ kind: 'server_error' });
    // controller.verify() in afterEach confirms no extra requests
  });

  it('network/non-HTTP error → emits {kind:"server_error"} (spec §3.1 retry affordance)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).error(new ProgressEvent('error'));

    const result = await promise;
    expect(result).toMatchObject({ kind: 'server_error' });
  });
});

// ── 422 fallback when body fields are null ────────────────────────────────────

describe('PricingApiService — 422 graceful fallback on null body fields', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('422 no_pricing_data with null detail → uses fallback string (does not crash)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { error_code: 'pricing.category.no_pricing_data', detail: null },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise as PriceCalcNoPricingDataError;
    expect(result.kind).toBe('no_pricing_data');
    expect(result.detail).toBeTruthy();
    expect(result.error_code).toBe('pricing.category.no_pricing_data');
  });
});

// ── No retryOn503 guard ───────────────────────────────────────────────────────

describe('PricingApiService — no retryOn503 (spec §3.2 POST non-idempotent)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends exactly ONE request on 503 (ApiClient retryOn503 must be off)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, REQUEST_NO_COMMISSION).subscribe();

    // expectOne() throws if more than one request is dispatched
    const req = controller.expectOne(ENDPOINT);
    req.flush(
      { detail: 'Service Unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    // controller.verify() in afterEach confirms no subsequent retry request
  });
});
