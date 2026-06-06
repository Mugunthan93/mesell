// core/interceptors/refresh.interceptor.ts
// Interceptor #3 in chain — catches 401, fires /auth/refresh, replays per §4.B.3
// Uses BehaviorSubject deduplication to prevent concurrent refresh storms.

import { HttpErrorResponse, HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject, runInInjectionContext, Injector } from '@angular/core';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { AuthService } from '@core/auth/auth.service';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';
import { HttpClient } from '@angular/common/http';

interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

// Module-level shared state for refresh deduplication across concurrent requests
let refreshing = false;
const refreshSubject = new BehaviorSubject<string | null>(null);

function doRefresh(
  http: HttpClient,
  auth: AuthService,
  baseUrl: string,
): Observable<string> {
  return http.post<RefreshResponse>(`${baseUrl}/auth/refresh`, null, {
    withCredentials: true,
  }).pipe(
    switchMap(response => {
      auth.setAccess(response);
      refreshing = false;
      refreshSubject.next(response.access_token);
      return [response.access_token];
    }),
    catchError(err => {
      refreshing = false;
      refreshSubject.next(null);
      return throwError(() => err);
    }),
  );
}

/** URL segments that are themselves auth endpoints — don't intercept their 401s */
const AUTH_PATHS = ['/auth/otp/', '/auth/refresh', '/auth/logout'];

function isAuthPath(url: string): boolean {
  return AUTH_PATHS.some(p => url.includes(p));
}

export const refreshInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  if (isAuthPath(req.url)) {
    return next(req);
  }

  const auth = inject(AuthService);
  const baseUrl = inject(API_BASE_URL);
  const injector = inject(Injector);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (!(err instanceof HttpErrorResponse) || err.status !== 401) {
        return throwError(() => err);
      }

      if (refreshing) {
        // Another refresh is already in flight — wait for it, then replay
        return refreshSubject.pipe(
          filter(token => token !== null),
          take(1),
          switchMap(token => {
            const retried = req.clone({
              setHeaders: { Authorization: `Bearer ${token as string}` },
            });
            return next(retried);
          }),
        );
      }

      // Start a new refresh
      refreshing = true;
      refreshSubject.next(null);

      const http = runInInjectionContext(injector, () => inject(HttpClient));

      return doRefresh(http, auth, baseUrl).pipe(
        switchMap(token => {
          const retried = req.clone({
            setHeaders: { Authorization: `Bearer ${token}` },
          });
          return next(retried);
        }),
        catchError(refreshErr => {
          // Refresh itself failed — propagate so ErrorInterceptor can route to /login
          auth.clear();
          return throwError(() => refreshErr);
        }),
      );
    }),
  );
};
