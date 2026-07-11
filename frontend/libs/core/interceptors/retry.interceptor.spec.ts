/**
 * retry.interceptor.spec.ts
 *
 * Tests retryInterceptor using Angular's HttpTestingController + vi fake timers.
 *
 * Zoneless project: fakeAsync()/tick() are NOT available (they require
 * zone.js/testing) — use vi.useFakeTimers() + vi.advanceTimersByTime() to flush
 * the RxJS timer() backoff (mirrors the ApiClient retry-filter spec pattern).
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
 *
 * Sustained-failure regression guard (resetOnSuccess hazard, see interceptor doc comment):
 *   HttpTestingController.flush() calls `observer.error(...)` directly — it never emits a
 *   preceding `HttpEventType.Sent` `next` value, so it CANNOT reproduce the bug where
 *   `resetOnSuccess: true` treated that per-attempt `Sent` event as a "success" and reset the
 *   retry counter before every failure was counted, defeating the count:3 cap entirely (the
 *   cap never trips → unbounded ~1 s-cadence retries). These cases call `retryInterceptor`
 *   directly (it injects nothing) with a hand-rolled `next: HttpHandlerFn` that emits
 *   `Sent` then errors on every invocation, so the hazard is actually exercised.
 *   (i) sustained status-0 (GET)      → exactly 4 attempts total, terminal error propagates
 *   (j) backoff progression (GET)     → 4th attempt not before ~7 s cumulative (1 s+2 s+4 s)
 *   (k) sustained 503 (GET, idempotent 5xx path) → exactly 4 attempts total
 */

import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpErrorResponse,
  HttpEventType,
  HttpRequest,
  provideHttpClient,
  withFetch,
  withInterceptors,
  type HttpHandlerFn,
  type HttpSentEvent,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { vi } from 'vitest';
import { concat, defer, of, throwError } from 'rxjs';

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
  // The sustained-failure regression guard cases below call retryInterceptor directly
  // (it injects nothing) and never configure TestBed's HttpClientTesting — guard the
  // verify() call so this shared hook doesn't NG0201 for those cases.
  try {
    TestBed.inject(HttpTestingController).verify();
  } catch {
    /* no HttpClientTesting configured for this test — nothing to verify */
  }
  TestBed.resetTestingModule();
  vi.useRealTimers();
});

// ── (a) GET + 503 → retried ──────────────────────────────────────────────────

describe('retryInterceptor — GET + 503 (server error, idempotent)', () => {
  it('retries once and succeeds on the second attempt', () => {
    vi.useFakeTimers();
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
    vi.advanceTimersByTime(1000);

    // Retry request — succeed this time
    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ items: [] });

    expect(errorCaught).toBe(false);
    expect(result).toEqual({ items: [] });
  });
});

// ── (b) POST + 503 → NOT retried ─────────────────────────────────────────────

describe('retryInterceptor — POST + 503 (non-idempotent, no retry)', () => {
  it('propagates the error immediately without retrying', () => {
    vi.useFakeTimers();
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
  });
});

// ── (c) GET + status 0 → retried ─────────────────────────────────────────────

describe('retryInterceptor — GET + status 0 (network failure)', () => {
  it('retries on a network failure (status 0) for GET', () => {
    vi.useFakeTimers();
    const { http, controller } = setup();

    let result: unknown = null;
    http.get('/api/v1/products').subscribe({
      next: (r) => { result = r; },
    });

    // First attempt: network error (status 0)
    const req1 = controller.expectOne('/api/v1/products');
    req1.flush(null, { status: 0, statusText: 'Unknown Error' });

    vi.advanceTimersByTime(1000); // first retry delay

    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ items: [] });

    expect(result).toEqual({ items: [] });
  });
});

// ── (d) POST + status 0 → retried (network failure is method-agnostic) ───────

describe('retryInterceptor — POST + status 0 (network failure, any method)', () => {
  it('retries on network failure even for POST', () => {
    vi.useFakeTimers();
    const { http, controller } = setup();

    let result: unknown = null;
    http.post('/api/v1/products', { name: 'test' }).subscribe({
      next: (r) => { result = r; },
    });

    const req1 = controller.expectOne('/api/v1/products');
    req1.flush(null, { status: 0, statusText: 'Unknown Error' });

    vi.advanceTimersByTime(1000);

    const req2 = controller.expectOne('/api/v1/products');
    req2.flush({ id: '1' });

    expect(result).toEqual({ id: '1' });
  });
});

// ── (e) GET + 404 → NOT retried (4xx) ────────────────────────────────────────

describe('retryInterceptor — GET + 404 (client error, no retry)', () => {
  it('does not retry on 4xx errors', () => {
    vi.useFakeTimers();
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
  });
});

// ── (f) GET + 401 → NOT retried ──────────────────────────────────────────────

describe('retryInterceptor — GET + 401 (auth error, no retry)', () => {
  it('does not retry on 401 (handled by refreshInterceptor in the full chain)', () => {
    vi.useFakeTimers();
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
  });
});

// ── (g) PUT + 500 → retried (idempotent method) ───────────────────────────────

describe('retryInterceptor — PUT + 500 (idempotent, retried)', () => {
  it('retries PUT on a 500 server error', () => {
    vi.useFakeTimers();
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

    vi.advanceTimersByTime(1000);

    const req2 = controller.expectOne('/api/v1/products/1');
    req2.flush({ id: '1', name: 'updated' });

    expect(result).toEqual({ id: '1', name: 'updated' });
  });
});

// ── (h) PATCH + 500 → NOT retried (non-idempotent) ────────────────────────────

describe('retryInterceptor — PATCH + 500 (non-idempotent, no retry)', () => {
  it('does not retry PATCH on a 500 server error', () => {
    vi.useFakeTimers();
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
  });
});

// ── Sustained-failure regression guard (resetOnSuccess hazard) ───────────────
//
// These bypass HttpTestingController entirely: retryInterceptor injects nothing, so it can be
// called directly as a plain function with a hand-rolled `next: HttpHandlerFn` that simulates
// what HttpClient's real backend does on EVERY attempt — emit `HttpEventType.Sent` as a `next`
// value, then error. That `Sent` emission is exactly what a reintroduced `resetOnSuccess: true`
// would treat as a "success" and use to reset the retry counter before it's ever checked.
//
// IMPORTANT: `next(req)` is called exactly ONCE by retryInterceptor — `retry()` then
// RE-SUBSCRIBES to that single returned Observable on every attempt (this mirrors real
// HttpClient: the backend Observable performs the XHR/fetch inside its own subscribe callback,
// so resubscribing IS what fires a fresh request). The handler below therefore uses `defer()`
// so each retry's resubscription — not each call to `next` — increments the attempt counter and
// re-emits Sent-then-error.

/** Builds a `next: HttpHandlerFn` that always fails with `status`, counting attempts (subscriptions). */
function alwaysFailingHandler(status: number): {
  next: HttpHandlerFn;
  attempts: () => number;
} {
  let attempts = 0;
  const next: HttpHandlerFn = () =>
    defer(() => {
      attempts += 1;
      return concat(
        of({ type: HttpEventType.Sent } as HttpSentEvent),
        throwError(() => new HttpErrorResponse({ status, url: '/api/v1/products' })),
      );
    });
  return { next, attempts: () => attempts };
}

describe('retryInterceptor — sustained status-0 failure (GET), resetOnSuccess regression guard', () => {
  it('caps at exactly 4 attempts total and propagates the terminal error', () => {
    vi.useFakeTimers();
    const req = new HttpRequest('GET', '/api/v1/products');
    const { next, attempts } = alwaysFailingHandler(0);

    let terminalError: unknown = null;
    let errorStatus = -1;
    let completed = false;
    const sub = retryInterceptor(req, next).subscribe({
      error: (e: HttpErrorResponse) => { terminalError = e; errorStatus = e.status; },
      complete: () => { completed = true; },
    });

    // Sustained failure well beyond the 1 s + 2 s + 4 s = 7 s total backoff window.
    vi.advanceTimersByTime(30_000);

    expect(attempts()).toBe(4); // 1 initial + 3 retries — the hard cap
    expect(terminalError).toBeInstanceOf(HttpErrorResponse);
    expect(errorStatus).toBe(0);
    expect(completed).toBe(false);

    sub.unsubscribe();
  });
});

describe('retryInterceptor — backoff progression (GET, status 0)', () => {
  it('does not fire the 4th (final) attempt before ~7 s cumulative (1 s + 2 s + 4 s)', () => {
    vi.useFakeTimers();
    const req = new HttpRequest('GET', '/api/v1/products');
    const { next, attempts } = alwaysFailingHandler(0);

    const sub = retryInterceptor(req, next).subscribe({ error: () => {} });

    expect(attempts()).toBe(1); // initial attempt fires synchronously on subscribe

    vi.advanceTimersByTime(999);
    expect(attempts()).toBe(1); // still waiting out the 1 s delay (retryCount 1)

    vi.advanceTimersByTime(1); // cumulative 1 000 ms
    expect(attempts()).toBe(2); // 2nd attempt fires at +1 s

    vi.advanceTimersByTime(1999);
    expect(attempts()).toBe(2); // still waiting out the 2 s delay (retryCount 2)

    vi.advanceTimersByTime(1); // cumulative 3 000 ms (1 s + 2 s)
    expect(attempts()).toBe(3); // 3rd attempt fires at +2 s

    vi.advanceTimersByTime(3999);
    expect(attempts()).toBe(3); // still waiting out the 4 s delay (retryCount 3)

    vi.advanceTimersByTime(1); // cumulative 7 000 ms (1 s + 2 s + 4 s)
    expect(attempts()).toBe(4); // 4th (final) attempt fires at +4 s, terminal — no further delay

    sub.unsubscribe();
  });
});

describe('retryInterceptor — sustained 503 failure (GET, idempotent 5xx path), resetOnSuccess regression guard', () => {
  it('caps at exactly 4 attempts total and propagates the terminal error', () => {
    vi.useFakeTimers();
    const req = new HttpRequest('GET', '/api/v1/products');
    const { next, attempts } = alwaysFailingHandler(503);

    let terminalError: unknown = null;
    let errorStatus = -1;
    const sub = retryInterceptor(req, next).subscribe({
      error: (e: HttpErrorResponse) => { terminalError = e; errorStatus = e.status; },
    });

    vi.advanceTimersByTime(30_000);

    expect(attempts()).toBe(4);
    expect(terminalError).toBeInstanceOf(HttpErrorResponse);
    expect(errorStatus).toBe(503);

    sub.unsubscribe();
  });
});
