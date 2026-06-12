import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, retry, timer } from 'rxjs';

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
  /** When true, retries the call on 503 up to 2 times with backoff (1s, 2s). */
  retryOn503?: boolean;
}

/**
 * ApiClient — typed thin wrapper over HttpClient.
 *
 * Convention: callers pass the FULL /api/v1/... path (matching the existing
 * CategoryService literal) to minimise churn when migrating existing services.
 *
 * retryOn503: opt-in bounded retry per the graceful-degradation pattern (§4-LOCKED).
 * The retry is 2 attempts, exponential backoff 1s/2s. Only fires on 503 (network
 * issue / pod restart); other errors pass through immediately.
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
        delay: (_, retryCount) => timer(retryCount * 1000),
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
