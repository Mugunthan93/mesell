// core/api/api-client.service.ts
// Typed HttpClient wrapper per §4.E — the ONLY HTTP interface features import.
// Features MUST inject ApiClient; injecting HttpClient directly is a contract violation.

import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError, timer } from 'rxjs';
import { catchError, mergeMap, retry } from 'rxjs/operators';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';
import { normaliseHttpError } from './api-error';

export interface ApiOptions {
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  /** true for /auth/* requests — causes the browser to send the HttpOnly refresh cookie */
  withCredentials?: boolean;
  /**
   * Opt-in retry-with-backoff on 503 Service Unavailable (per §4.E Look 1).
   * Default: false.
   * When true: retries up to 3 times with exponential backoff (1s, 2s, 4s).
   * Recommended: autofill (Gemini cold start), image upload (GCS hiccup), export trigger.
   * NOT for: catalog autosave PATCH — loud failure is the correct UX for offline detection.
   */
  retryOn503?: boolean;
}

/** Exponential backoff: 1s → 2s → 4s */
const BACKOFF_DELAYS_MS = [1000, 2000, 4000] as const;

function buildParams(raw?: Record<string, string | number | boolean>): HttpParams {
  if (!raw) return new HttpParams();
  return Object.entries(raw).reduce(
    (acc, [k, v]) => acc.set(k, String(v)),
    new HttpParams(),
  );
}

function buildHeaders(raw?: Record<string, string>): HttpHeaders {
  if (!raw) return new HttpHeaders();
  return new HttpHeaders(raw);
}

@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  /** Applies withCredentials automatically for /auth/* paths per §4.E.3 */
  private resolveCredentials(path: string, opt?: ApiOptions): boolean {
    return opt?.withCredentials ?? path.startsWith('/auth/');
  }

  private applyRetry<T>(source$: Observable<T>, opt?: ApiOptions): Observable<T> {
    if (!opt?.retryOn503) return source$;
    let attempt = 0;
    return source$.pipe(
      retry({
        count: 3,
        delay: (err) => {
          if (err?.status !== 503 || attempt >= 3) return throwError(() => err);
          const delay = BACKOFF_DELAYS_MS[attempt] ?? 4000;
          attempt++;
          return timer(delay);
        },
      }),
    );
  }

  get<T>(path: string, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    const req$ = this.http.get<T>(url, {
      params: buildParams(options?.params),
      headers: buildHeaders(options?.headers),
      withCredentials: this.resolveCredentials(path, options),
    }).pipe(catchError(err => throwError(() => normaliseHttpError(err))));
    return this.applyRetry(req$, options);
  }

  post<T>(path: string, body: unknown, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    const req$ = this.http.post<T>(url, body, {
      params: buildParams(options?.params),
      headers: buildHeaders(options?.headers),
      withCredentials: this.resolveCredentials(path, options),
    }).pipe(catchError(err => throwError(() => normaliseHttpError(err))));
    return this.applyRetry(req$, options);
  }

  patch<T>(path: string, body: unknown, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    const req$ = this.http.patch<T>(url, body, {
      params: buildParams(options?.params),
      headers: buildHeaders(options?.headers),
      withCredentials: this.resolveCredentials(path, options),
    }).pipe(catchError(err => throwError(() => normaliseHttpError(err))));
    return this.applyRetry(req$, options);
  }

  put<T>(path: string, body: unknown, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    const req$ = this.http.put<T>(url, body, {
      params: buildParams(options?.params),
      headers: buildHeaders(options?.headers),
      withCredentials: this.resolveCredentials(path, options),
    }).pipe(catchError(err => throwError(() => normaliseHttpError(err))));
    return this.applyRetry(req$, options);
  }

  delete<T = void>(path: string, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    return this.http.delete<T>(url, {
      params: buildParams(options?.params),
      headers: buildHeaders(options?.headers),
      withCredentials: this.resolveCredentials(path, options),
    }).pipe(
      catchError(err => throwError(() => normaliseHttpError(err))),
      mergeMap(val => [val]),
    );
  }

  /** Specialized for multipart uploads (image upload per §12) */
  postMultipart<T>(path: string, formData: FormData, options?: ApiOptions): Observable<T> {
    const url = `${this.baseUrl}${path}`;
    const req$ = this.http.post<T>(url, formData, {
      params: buildParams(options?.params),
      withCredentials: this.resolveCredentials(path, options),
      // Do NOT set Content-Type — browser sets it with boundary for multipart
    }).pipe(catchError(err => throwError(() => normaliseHttpError(err))));
    return this.applyRetry(req$, options);
  }
}
