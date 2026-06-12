import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { vi } from 'vitest';
import { ApiClient } from './api-client.service';

/**
 * ApiClient retry-filter regression suite (frozen-surface amendment 2026-06-12).
 *
 * The retry MUST fire ONLY on transient unavailability (503 / 504 / network /
 * status 0) and NEVER on a 4xx. These tests pin that contract so the original
 * defect (bare `retry({count})` retrying on every error including 4xx) cannot
 * regress. They also confirm POST semantics are unchanged.
 *
 * Zoneless project: fakeAsync() is NOT available — use vi.useFakeTimers() +
 * vi.advanceTimersByTime() to flush the RxJS timer() backoff (mirrors the
 * AuthService.scheduleRefresh spec pattern).
 */
describe('ApiClient (retry filter)', () => {
  let api: ApiClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ApiClient,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });
    api = TestBed.inject(ApiClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    vi.useRealTimers();
  });

  // ── Retries ONLY on transient unavailability ───────────────────────────────

  it('retries a GET on 503 (up to 2 times) then succeeds', () => {
    vi.useFakeTimers();
    let result: unknown;
    api.get<{ ok: boolean }>('/api/v1/thing', { retryOn503: true }).subscribe({
      next: (r) => (result = r),
    });

    // First attempt → 503.
    httpMock.expectOne('/api/v1/thing').flush('unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
    });
    vi.advanceTimersByTime(1_000); // backoff for retry #1

    // Second attempt → 503 again.
    httpMock.expectOne('/api/v1/thing').flush('unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
    });
    vi.advanceTimersByTime(2_000); // backoff for retry #2

    // Third attempt → success.
    httpMock.expectOne('/api/v1/thing').flush({ ok: true });

    expect(result).toEqual({ ok: true });
  });

  it('retries a GET on 504', () => {
    vi.useFakeTimers();
    let result: unknown;
    api.get<{ ok: boolean }>('/api/v1/thing', { retryOn503: true }).subscribe({
      next: (r) => (result = r),
    });

    httpMock.expectOne('/api/v1/thing').flush('gateway timeout', {
      status: 504,
      statusText: 'Gateway Timeout',
    });
    vi.advanceTimersByTime(1_000);
    httpMock.expectOne('/api/v1/thing').flush({ ok: true });

    expect(result).toEqual({ ok: true });
  });

  it('retries a GET on a connection-level failure (status 0)', () => {
    vi.useFakeTimers();
    let result: unknown;
    api.get<{ ok: boolean }>('/api/v1/thing', { retryOn503: true }).subscribe({
      next: (r) => (result = r),
    });

    httpMock
      .expectOne('/api/v1/thing')
      .error(new ProgressEvent('Network error')); // status 0
    vi.advanceTimersByTime(1_000);
    httpMock.expectOne('/api/v1/thing').flush({ ok: true });

    expect(result).toEqual({ ok: true });
  });

  // ── NEVER retries on a 4xx (the regression-critical cases) ──────────────────

  it('does NOT retry on 400 — single request, error surfaces immediately', () => {
    vi.useFakeTimers();
    let status: number | undefined;
    api.get('/api/v1/thing', { retryOn503: true }).subscribe({
      error: (e) => (status = e.status),
    });

    httpMock.expectOne('/api/v1/thing').flush('bad request', {
      status: 400,
      statusText: 'Bad Request',
    });
    vi.advanceTimersByTime(5_000); // advance well past any backoff window

    expect(status).toBe(400);
    httpMock.expectNone('/api/v1/thing'); // no second attempt
  });

  it('does NOT retry on 404', () => {
    vi.useFakeTimers();
    let status: number | undefined;
    api.get('/api/v1/thing', { retryOn503: true }).subscribe({
      error: (e) => (status = e.status),
    });

    httpMock.expectOne('/api/v1/thing').flush('not found', {
      status: 404,
      statusText: 'Not Found',
    });
    vi.advanceTimersByTime(5_000);

    expect(status).toBe(404);
    httpMock.expectNone('/api/v1/thing');
  });

  it('does NOT retry on 422', () => {
    vi.useFakeTimers();
    let status: number | undefined;
    api.get('/api/v1/thing', { retryOn503: true }).subscribe({
      error: (e) => (status = e.status),
    });

    httpMock.expectOne('/api/v1/thing').flush('unprocessable', {
      status: 422,
      statusText: 'Unprocessable Entity',
    });
    vi.advanceTimersByTime(5_000);

    expect(status).toBe(422);
    httpMock.expectNone('/api/v1/thing');
  });

  it('does NOT retry on a non-503 5xx (500)', () => {
    vi.useFakeTimers();
    let status: number | undefined;
    api.get('/api/v1/thing', { retryOn503: true }).subscribe({
      error: (e) => (status = e.status),
    });

    httpMock.expectOne('/api/v1/thing').flush('server error', {
      status: 500,
      statusText: 'Internal Server Error',
    });
    vi.advanceTimersByTime(5_000);

    expect(status).toBe(500);
    httpMock.expectNone('/api/v1/thing');
  });

  // ── Opt-in only: default path never retries ─────────────────────────────────

  it('does NOT retry when retryOn503 is omitted, even on 503', () => {
    vi.useFakeTimers();
    let status: number | undefined;
    api.get('/api/v1/thing').subscribe({
      error: (e) => (status = e.status),
    });

    httpMock.expectOne('/api/v1/thing').flush('unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
    });
    vi.advanceTimersByTime(5_000);

    expect(status).toBe(503);
    httpMock.expectNone('/api/v1/thing');
  });

  // ── POST semantics unchanged ────────────────────────────────────────────────

  it('POST forwards body + path and resolves (default = exactly one request)', () => {
    const body = { name: 'widget' };
    let result: unknown;
    api.post<{ id: number }>('/api/v1/widgets', body).subscribe((r) => (result = r));

    const req = httpMock.expectOne('/api/v1/widgets');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(body);
    req.flush({ id: 7 });

    expect(result).toEqual({ id: 7 });
  });

  it('POST with retryOn503 retries on 503 but NOT on 400', () => {
    vi.useFakeTimers();
    // 503 → retried
    let okResult: unknown;
    api
      .post<{ ok: boolean }>('/api/v1/widgets', { n: 1 }, { retryOn503: true })
      .subscribe((r) => (okResult = r));
    httpMock.expectOne('/api/v1/widgets').flush('unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
    });
    vi.advanceTimersByTime(1_000);
    httpMock.expectOne('/api/v1/widgets').flush({ ok: true });
    expect(okResult).toEqual({ ok: true });

    // 400 → NOT retried
    let status: number | undefined;
    api
      .post('/api/v1/widgets', { n: 2 }, { retryOn503: true })
      .subscribe({ error: (e) => (status = e.status) });
    httpMock.expectOne('/api/v1/widgets').flush('bad', {
      status: 400,
      statusText: 'Bad Request',
    });
    vi.advanceTimersByTime(5_000);
    expect(status).toBe(400);
    httpMock.expectNone('/api/v1/widgets');
  });
});
