/**
 * pricing.service.spec.ts — PricingApiService tests.
 *
 * Validation §8 requirements:
 *   - URL asserted EXACTLY: /api/v1/products/{id}/price-calc
 *   - Request body keys: input_cost + target_margin_pct (NOT mrp / target_margin)
 *   - Response → breakdown mapping: real keys (commission_amount / seller_price / profit / profit_pct)
 *   - Full error matrix: 401/404/422/400/5xx → typed shapes or EMPTY; NEVER local math
 *   - NO retryOn503 usage
 *   - Decimal wire-type: string fields parsed correctly (R-W6-6)
 */

import { describe, it, expect, afterEach } from 'vitest';
import { TestBed }                          from '@angular/core/testing';
import { provideHttpClient, withFetch }     from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
}                                           from '@angular/common/http/testing';
import { firstValueFrom, EMPTY }            from 'rxjs';

import { ApiClient } from '@mesell/core';

import { PricingApiService }                from './pricing.service';
import type { PriceCalcRequest, PriceCalcResponse } from './pricing.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PRODUCT_ID = 'prod-uuid-001';
const ENDPOINT   = `/api/v1/products/${PRODUCT_ID}/price-calc`;

const VALID_REQUEST: PriceCalcRequest = {
  input_cost:        '300.00',
  target_margin_pct: '30.00',
};

/** Server 200-OK response (all Decimal fields as strings — R-W6-6). */
const MOCK_RESPONSE: PriceCalcResponse = {
  mrp:               '429.00',
  meesho_price:      '214.50',
  seller_price:      '193.05',
  commission_pct:    '10.00',
  commission_amount: '21.45',
  gst_pct:           '18.00',
  gst_amount:        '3.86',
  profit:            '90.00',
  profit_pct:        '30.00',
  alerts:            [],
  calculated_at:     '2026-06-12T06:00:00Z',
};

/** Server 200-OK with alerts. */
const MOCK_RESPONSE_WITH_ALERTS: PriceCalcResponse = {
  ...MOCK_RESPONSE,
  alerts: [
    { code: 'LOW_MARGIN', message_id: 'pricing.low_margin', severity: 'warning' },
    { code: 'THIN_PROFIT', message_id: 'pricing.thin_profit', severity: 'info' },
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

// ── Happy path ────────────────────────────────────────────────────────────────

describe('PricingApiService — happy path', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends POST to the exact /price-calc URL', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.method).toBe('POST');
    req.flush(MOCK_RESPONSE);
  });

  it('sends body with input_cost and target_margin_pct — NOT mrp or target_margin', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe();

    const req = controller.expectOne(ENDPOINT);
    expect(req.request.body).toEqual({
      input_cost:        '300.00',
      target_margin_pct: '30.00',
    });
    // Ensure retired keys are NOT present
    expect(req.request.body).not.toHaveProperty('mrp');
    expect(req.request.body).not.toHaveProperty('target_margin');
    req.flush(MOCK_RESPONSE);
  });

  it('emits PriceCalcResponse on 200 with correct real keys', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    expect(result).toMatchObject({
      mrp:               '429.00',
      meesho_price:      '214.50',
      seller_price:      '193.05',     // real key (not seller_payout)
      commission_pct:    '10.00',
      commission_amount: '21.45',       // real key (not commission_amt)
      gst_pct:           '18.00',
      gst_amount:        '3.86',        // real key (not gst_amt)
      profit:            '90.00',       // real key (not net_margin)
      profit_pct:        '30.00',       // real key (not net_margin_pct)
      alerts:            [],
    });
  });

  it('emits PriceCalcResponse with alerts on 200', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE_WITH_ALERTS);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse, got error shape');
    expect(result.alerts).toHaveLength(2);
    expect(result.alerts[0].code).toBe('LOW_MARGIN');
    expect(result.alerts[0].severity).toBe('warning');
    expect(result.alerts[1].code).toBe('THIN_PROFIT');
    expect(result.alerts[1].severity).toBe('info');
  });

  it('Decimal string fields are strings (R-W6-6 — NOT numbers)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    // All monetary/pct fields MUST be strings (Pydantic v2 Decimal → JSON string)
    expect(typeof result.mrp).toBe('string');
    expect(typeof result.meesho_price).toBe('string');
    expect(typeof result.seller_price).toBe('string');
    expect(typeof result.commission_pct).toBe('string');
    expect(typeof result.commission_amount).toBe('string');
    expect(typeof result.gst_pct).toBe('string');
    expect(typeof result.gst_amount).toBe('string');
    expect(typeof result.profit).toBe('string');
    expect(typeof result.profit_pct).toBe('string');
  });

  it('does NOT add Authorization header manually (jwtInterceptor owns auth, Wave A)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe();

    const req = controller.expectOne(ENDPOINT);
    // In TestBed without jwtInterceptor, no Authorization header should be set by the service itself
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(MOCK_RESPONSE);
  });
});

// ── Error matrix (R-W6-1, DECISION-1) ────────────────────────────────────────

describe('PricingApiService — error matrix (DECISION-1: no local math fallback)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('401 → EMPTY (refreshInterceptor logout path; no emission)', async () => {
    const { service, controller } = setup();
    let emitted = false;
    let completed = false;

    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe({
      next:     () => { emitted = true; },
      complete: () => { completed = true; },
    });

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(emitted).toBe(false);
    expect(completed).toBe(true);  // EMPTY completes silently
  });

  it('404 → emits PriceCalcUnavailableError with kind="unavailable"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Feature disabled.' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise;
    expect(result).toMatchObject({ kind: 'unavailable' });
    // Breakdown key must NOT be present — no local math computed
    const resultAny = result as unknown as Record<string, unknown>;
    expect(resultAny['mrp']).toBeUndefined();
    expect(resultAny['profit']).toBeUndefined();
  });

  it('404 with "not found" in detail → reason="not_found"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
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

  it('404 without "not found" detail → reason="flag_off"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Feature disabled.' },
      { status: 404, statusText: 'Not Found' },
    );

    const result = await promise;
    if (!('kind' in result) || result.kind !== 'unavailable') {
      throw new Error('Expected unavailable error');
    }
    expect(result.reason).toBe('flag_off');
  });

  it('422 → emits PriceCalcCommissionMissingError with kind="commission_missing"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'No commission rate for category.', error_code: 'pricing.commission.missing' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const result = await promise;
    expect(result).toMatchObject({
      kind:       'commission_missing',
      detail:     'No commission rate for category.',
      error_code: 'pricing.commission.missing',
    });
    // No local math computed — no breakdown keys
    const resultAny = result as unknown as Record<string, unknown>;
    expect(resultAny['mrp']).toBeUndefined();
    expect(resultAny['profit']).toBeUndefined();
  });

  it('422 with no error body → uses fallback detail string', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(null, { status: 422, statusText: 'Unprocessable Entity' });

    const result = await promise;
    if (!('kind' in result) || result.kind !== 'commission_missing') {
      throw new Error('Expected commission_missing');
    }
    expect(result.detail).toBeTruthy();    // fallback string
    expect(result.error_code).toBeTruthy(); // fallback code
  });

  it('400 → emits PriceCalcValidationError with kind="validation"', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(
      { detail: 'input_cost must be greater than 0.' },
      { status: 400, statusText: 'Bad Request' },
    );

    const result = await promise;
    expect(result).toMatchObject({
      kind:   'validation',
      detail: 'input_cost must be greater than 0.',
    });
    // No local math computed — no breakdown keys
    const resultAny = result as unknown as Record<string, unknown>;
    expect(resultAny['mrp']).toBeUndefined();
    expect(resultAny['profit']).toBeUndefined();
  });

  it('500 → EMPTY (explicit 5xx error; component re-submit affordance)', async () => {
    const { service, controller } = setup();
    let emitted = false;
    let completed = false;

    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe({
      next:     () => { emitted = true; },
      complete: () => { completed = true; },
    });

    controller.expectOne(ENDPOINT).flush(
      { detail: 'Internal Server Error' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    expect(emitted).toBe(false);
    expect(completed).toBe(true); // EMPTY completes silently
  });

  it('503 → EMPTY (same as 5xx; no auto-retry — ApiClient retryOn503 is defective)', async () => {
    const { service, controller } = setup();
    let emitted = false;

    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe({
      next: () => { emitted = true; },
    });

    // Only ONE request expected — no retry (ApiClient retryOn503 is NOT used)
    controller.expectOne(ENDPOINT).flush(
      { detail: 'Service Unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    expect(emitted).toBe(false);
  });
});

// ── No retryOn503 guard ───────────────────────────────────────────────────────

describe('PricingApiService — no retryOn503 (spec §3.2)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('sends exactly ONE request on 503 (no auto-retry)', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, VALID_REQUEST).subscribe();

    // expectOne() would throw if more than one request is dispatched
    const req = controller.expectOne(ENDPOINT);
    req.flush({ detail: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });
    // controller.verify() in afterEach confirms no extra requests
  });
});

// ── Decimal string parsing (R-W6-6) ──────────────────────────────────────────

describe('PricingApiService — Decimal-string parsing for arithmetic (R-W6-6)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('profit as string "90.00" is parseable to 90 (parseDecimal)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    controller.expectOne(ENDPOINT).flush(MOCK_RESPONSE);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    // parseDecimal("90.00") === 90 (positive profit)
    const profit = parseFloat(result.profit);
    expect(profit).toBe(90);
    expect(profit).toBeGreaterThan(0); // marginIsPositive would be true
  });

  it('negative profit string "-50.00" parses to negative (NEGATIVE badge)', async () => {
    const { service, controller } = setup();
    const result$ = service.calc(PRODUCT_ID, VALID_REQUEST);
    const promise = firstValueFrom(result$);

    const negativeResponse: PriceCalcResponse = { ...MOCK_RESPONSE, profit: '-50.00' };
    controller.expectOne(ENDPOINT).flush(negativeResponse);
    const result = await promise;

    if ('kind' in result) throw new Error('Expected PriceCalcResponse');
    expect(parseFloat(result.profit)).toBeLessThan(0);
  });
});

// ── Request body contract (retired keys must NOT appear) ──────────────────────

describe('PricingApiService — request body contract (retired keys must be absent)', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('request body has ONLY input_cost and target_margin_pct', () => {
    const { service, controller } = setup();
    service.calc(PRODUCT_ID, { input_cost: '200.00', target_margin_pct: '25.00' }).subscribe();

    const req = controller.expectOne(ENDPOINT);
    const body = req.request.body as Record<string, unknown>;

    // REQUIRED keys present
    expect(body['input_cost']).toBe('200.00');
    expect(body['target_margin_pct']).toBe('25.00');

    // RETIRED keys must NOT be present
    expect(body).not.toHaveProperty('mrp');
    expect(body).not.toHaveProperty('target_margin');

    // V1.5 overrides must NOT be sent
    expect(body).not.toHaveProperty('override_commission_pct');
    expect(body).not.toHaveProperty('override_gst_pct');

    req.flush(MOCK_RESPONSE);
  });
});
