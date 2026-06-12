import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpErrorResponse, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, retry, throwError, timer } from 'rxjs';

/**
 * Per-request options for ApiClient calls.
 * Pass retryOn503: true to opt-in to bounded retry (2× with exponential backoff).
 * All other options mirror HttpClient's standard typed options.
 */
export interface ApiClientOptions {
  headers?: HttpHeaders | Record<string, string | string[]>;
  params?:  HttpParams  | Record<string, string | number | boolean | ReadonlyArray<string | number | boolean>>;
  context?: HttpContext;
  withCredentials?: boolean;
  /**
   * When true, retries the call up to 2 times with backoff (1s, 2s) ONLY on
   * transient unavailability — 503, 504, or a connection-level failure
   * (status 0 / network error). NEVER retries on a 4xx (400/401/403/404/422,
   * etc.) or any other 5xx: those are deterministic and a retry would only
   * duplicate side effects / waste latency.
   */
  retryOn503?: boolean;
}

/**
 * Frozen-surface amendment (2026-06-12, founder-approved §7.3): retry must be
 * scoped to transient unavailability only. A bare `retry({count})` retries on
 * ANY error — including 4xx — which was the original defect. `isRetryable`
 * gates the retry to 503/504/network-status-0; everything else re-throws
 * immediately on the first failure.
 */
function isRetryable(err: unknown): boolean {
  if (err instanceof HttpErrorResponse) {
    // status 0 = network / connection failure (no HTTP response reached us).
    return err.status === 0 || err.status === 503 || err.status === 504;
  }
  return false;
}

/**
 * ApiClient — typed thin wrapper over HttpClient.
 *
 * Convention: callers pass the FULL /api/v1/... path (matching the existing
 * CategoryService literal) to minimise churn when migrating existing services.
 *
 * retryOn503: opt-in bounded retry per the graceful-degradation pattern (§4-LOCKED).
 * The retry is 2 attempts, exponential backoff 1s/2s. Fires ONLY on transient
 * unavailability (503/504/network); 4xx and other 5xx pass through immediately
 * on the first failure (see isRetryable).
 *
 * Wave B+ services use ApiClient; CategoryService keeps its raw HttpClient call
 * (re-point + de-header only per spec §5.4 resolution A7).
 */
@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);

  private applyRetry<T>(
    obs: Observable<T>,
    retryOn503?: boolean,
  ): Observable<T> {
    if (!retryOn503) return obs;
    return obs.pipe(
      retry({
        count: 2,
        // The delay callback doubles as the retry PREDICATE: returning a timer
        // schedules a retry; re-throwing aborts immediately. Only transient
        // unavailability (503/504/network) is retried — NEVER a 4xx.
        delay: (err, retryCount) =>
          isRetryable(err) ? timer(retryCount * 1000) : throwError(() => err),
      }),
    );
  }

  get<T>(path: string, options?: ApiClientOptions): Observable<T> {
    const { retryOn503, ...httpOpts } = options ?? {};
    return this.applyRetry(
      this.http.get<T>(path, httpOpts),
      retryOn503,
    );
  }

  post<T>(path: string, body: unknown, options?: ApiClientOptions): Observable<T> {
    const { retryOn503, ...httpOpts } = options ?? {};
    return this.applyRetry(
      this.http.post<T>(path, body, httpOpts),
      retryOn503,
    );
  }

  patch<T>(path: string, body: unknown, options?: ApiClientOptions): Observable<T> {
    const { retryOn503, ...httpOpts } = options ?? {};
    return this.applyRetry(
      this.http.patch<T>(path, body, httpOpts),
      retryOn503,
    );
  }

  delete<T>(path: string, options?: ApiClientOptions): Observable<T> {
    const { retryOn503, ...httpOpts } = options ?? {};
    return this.applyRetry(
      this.http.delete<T>(path, httpOpts),
      retryOn503,
    );
  }
}
