/**
 * retry.interceptor.spec.ts
 *
 * Tests retryInterceptor using Angular's HttpTestingController + fakeAsync/tick.
 *
 * Retry policy under test:
 *   count: 3, delay: 2^(n-1) * 1000ms (1 s, 2 s, 4 s)
 *   Retriable:
 *     - status === 0 (any method — network failure)
 *     - status >= 500 AND method ∈ {GET, HEAD, OPTIONS, PUT} (idempotent server errors)
 *   Non-retriable:
 *     - 4xx (any method)
 *     - 401 specifically (refresh interceptor's territory — NOT in this chain)
 *     - POST/PATCH/DELETE 5xx (non-idempotent)
 *
 * Cases:
 *   (a) GET + 503 → retried (succeeds on second attempt)
 *   (b) POST + 503 → NOT retried (propagates immediately)
 *   (c) status 0 + GET → retried (network failure)
 *   (d) status 0 + POST → retried (network failure, any method)
 *   (e) GET + 404 → NOT retried (4xx)
 *   (f) GET + 401 → NOT retried (4xx; not retryInterceptor's concern)
 *   (g) PUT + 500 → retried (idempotent method + 5xx)
 *   (h) PATCH + 500 → NOT retried (non-idempotent)
 */

import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withFetch,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { retryInterceptor } from './retry.interceptor';

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch(), withInterceptors([retryInterceptor])),
      provideHttpClientTesting(),
    ],
  });

  return {
    http:       TestBed.inject(HttpClient),
    controller: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
  TestBed.resetTestingModule();
});

// ── (a) GET + 503 → retried ──────────────────────────────────────────────────

describe('retryInterceptor — GET + 503 (server error, idempotent)', () => {
  it('retries once and succeeds on the second attempt', fakeAsync(() => {
    const { http, controller } = setup();

    let result: unknown = null;
    let errorCaught = false;
    http.get('/api/v1/products').subscribe({
      next:  (r) => { result = r; },
      error: () => { errorCaught = true; },
    });

    // First attempt fails with 503
    const req1 = controller.expectOne('/api/v1/products');
    req1.flush(
      { detail: 'Service Unavailable', code: 'SERVICE_UNAVAILABLE', validation_message_id: '', request_id: '' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    // Advance past the first retry delay (2^0 * 1000 = 1000 ms)
    tick(1000);

    // Retry request — succeed this time
    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ items: [] });

    expect(errorCaught).toBe(false);
    expect(result).toEqual({ items: [] });
  }));
});

// ── (b) POST + 503 → NOT retried ─────────────────────────────────────────────

describe('retryInterceptor — POST + 503 (non-idempotent, no retry)', () => {
  it('propagates the error immediately without retrying', fakeAsync(() => {
    const { http, controller } = setup();

    let errorStatus = 0;
    http.post('/api/v1/products', { name: 'test' }).subscribe({
      error: (e: { status: number }) => { errorStatus = e.status; },
    });

    // Only one request fired — no retry for POST 5xx
    const req = controller.expectOne('/api/v1/products');
    req.flush(
      { detail: 'Error', code: 'ERROR', validation_message_id: '', request_id: '' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    // No tick needed — no retry delay scheduled
    expect(errorStatus).toBe(503);

    // Verify no second request was made
    controller.expectNone('/api/v1/products');
  }));
});

// ── (c) GET + status 0 → retried ─────────────────────────────────────────────

describe('retryInterceptor — GET + status 0 (network failure)', () => {
  it('retries on a network failure (status 0) for GET', fakeAsync(() => {
    const { http, controller } = setup();

    let result: unknown = null;
    http.get('/api/v1/products').subscribe({
      next: (r) => { result = r; },
    });

    // First attempt: network error (status 0)
    const req1 = controller.expectOne('/api/v1/products');
    req1.flush(null, { status: 0, statusText: 'Unknown Error' });

    tick(1000); // first retry delay

    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ items: [] });

    expect(result).toEqual({ items: [] });
  }));
});

// ── (d) POST + status 0 → retried (network failure is method-agnostic) ───────

describe('retryInterceptor — POST + status 0 (network failure, any method)', () => {
  it('retries on network failure even for POST', fakeAsync(() => {
    const { http, controller } = setup();

    let result: unknown = null;
    http.post('/api/v1/products', { name: 'test' }).subscribe({
      next: (r) => { result = r; },
    });

    const req1 = controller.expectOne('/api/v1/products');
    req1.flush(null, { status: 0, statusText: 'Unknown Error' });

    tick(1000);

    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ id: '1' });

    expect(result).toEqual({ id: '1' });
  }));
});

// ── (e) GET + 404 → NOT retried (4xx) ────────────────────────────────────────

describe('retryInterceptor — GET + 404 (client error, no retry)', () => {
  it('does not retry on 4xx errors', fakeAsync(() => {
    const { http, controller } = setup();

    let errorStatus = 0;
    http.get('/api/v1/products/nonexistent').subscribe({
      error: (e: { status: number }) => { errorStatus = e.status; },
    });

    const req = controller.expectOne('/api/v1/products/nonexistent');
    req.flush(
      { detail: 'Not found', code: 'NOT_FOUND', validation_message_id: '', request_id: '' },
      { status: 404, statusText: 'Not Found' },
    );

    expect(errorStatus).toBe(404);
    controller.expectNone('/api/v1/products/nonexistent');
  }));
});

// ── (f) GET + 401 → NOT retried ──────────────────────────────────────────────

describe('retryInterceptor — GET + 401 (auth error, no retry)', () => {
  it('does not retry on 401 (handled by refreshInterceptor in the full chain)', fakeAsync(() => {
    const { http, controller } = setup();

    let errorStatus = 0;
    http.get('/api/v1/products').subscribe({
      error: (e: { status: number }) => { errorStatus = e.status; },
    });

    const req = controller.expectOne('/api/v1/products');
    req.flush(
      { detail: 'Unauthorized', code: 'AUTH_REQUIRED', validation_message_id: '', request_id: '' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(errorStatus).toBe(401);
    controller.expectNone('/api/v1/products');
  }));
});

// ── (g) PUT + 500 → retried (idempotent method) ───────────────────────────────

describe('retryInterceptor — PUT + 500 (idempotent, retried)', () => {
  it('retries PUT on a 500 server error', fakeAsync(() => {
    const { http, controller } = setup();

    let result: unknown = null;
    http.put('/api/v1/products/1', { name: 'updated' }).subscribe({
      next: (r) => { result = r; },
    });

    const req1 = controller.expectOne('/api/v1/products/1');
    req1.flush(
      { detail: 'Internal Error', code: 'INTERNAL', validation_message_id: '', request_id: '' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    tick(1000);

    const req2 = controller.expectOne('/api/v1/products/1');
    req2.flush({ id: '1', name: 'updated' });

    expect(result).toEqual({ id: '1', name: 'updated' });
  }));
});

// ── (h) PATCH + 500 → NOT retried (non-idempotent) ────────────────────────────

describe('retryInterceptor — PATCH + 500 (non-idempotent, no retry)', () => {
  it('does not retry PATCH on a 500 server error', fakeAsync(() => {
    const { http, controller } = setup();

    let errorStatus = 0;
    http.patch('/api/v1/products/1', { name: 'x' }).subscribe({
      error: (e: { status: number }) => { errorStatus = e.status; },
    });

    const req = controller.expectOne('/api/v1/products/1');
    req.flush(
      { detail: 'Internal Error', code: 'INTERNAL', validation_message_id: '', request_id: '' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    expect(errorStatus).toBe(500);
    controller.expectNone('/api/v1/products/1');
  }));
});
