import {
  HttpErrorResponse,
  HttpEvent,
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import {
  BehaviorSubject,
  Observable,
  throwError,
  filter,
  take,
  switchMap,
  catchError,
  tap,
} from 'rxjs';
import { AuthService } from '../services/auth.service';
import { AuthApiService } from '../services/auth-api.service';

/**
 * refreshInterceptor — single-flight 401→refresh→retry.
 *
 * Chain position: SECOND (jwt → refresh → error).
 *
 * Behaviour on 401 from a NON-/auth/* request:
 *   1. If a refresh is NOT already in-flight: call POST /auth/refresh (withCredentials).
 *      On success → setSession(newToken, currentUser) + retry original with new Bearer.
 *      On refresh-401 → logout() + navigate('/login') + rethrow.
 *   2. If a refresh IS already in-flight: queue this request; when refresh resolves,
 *      retry with the resulting token (single-flight gate — R-W6-4).
 *
 * Loop prevention (R-W6-11(e)):
 *   - /auth/* URLs are skipped (the jwtInterceptor also skips them; belt+suspenders here).
 *   - The `_isRefreshing` flag ensures a 401 on /auth/refresh itself does NOT re-enter.
 *
 * Module-level state is safe here because Angular's functional interceptors are called
 * within the same injector tree; the state is reset on logout().
 */

/**
 * In-flight refresh state (module-level singletons — one per app instance).
 * _isRefreshing: true while a /auth/refresh call is in flight.
 * _refreshToken$: BehaviorSubject whose null = "refresh pending"; non-null = new token.
 *   Queued requests filter(t => t !== null).take(1) to get the resolved token.
 */
let _isRefreshing = false;
const _refreshToken$ = new BehaviorSubject<string | null>(null);

function addBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  auth: AuthService,
  authApi: AuthApiService,
  router: Router,
): Observable<HttpEvent<unknown>> {
  if (_isRefreshing) {
    // Another refresh is in-flight — queue this request
    return _refreshToken$.pipe(
      filter((token): token is string => token !== null),
      take(1),
      switchMap((token) => next(addBearer(req, token))),
    );
  }

  _isRefreshing = true;
  _refreshToken$.next(null);

  return authApi.refresh().pipe(
    tap((resp) => {
      _isRefreshing = false;
      const newToken = resp.access_token;
      // Preserve existing user for the setSession call
      const currentUser = auth.currentUser();
      if (currentUser) {
        auth.setSession(newToken, currentUser);
      } else {
        // Edge case: no user in memory (can happen if /me failed at bootstrap)
        // Set the token directly via setSession with a minimal user stub
        auth.setSession(newToken, { phone: '' });
      }
      auth.scheduleRefresh(resp.expires_in);
      _refreshToken$.next(newToken);
    }),
    switchMap((resp) => next(addBearer(req, resp.access_token))),
    catchError((refreshErr: unknown) => {
      _isRefreshing = false;
      _refreshToken$.next(null);
      auth.logout();
      void router.navigate(['/login']);
      return throwError(() => refreshErr);
    }),
  );
}

/**
 * Paths whose 401s must NOT trigger a refresh attempt.
 * These are the cookie-auth or public endpoints — a 401 here means a genuinely invalid
 * OTP or expired refresh cookie, not a stale access token. Re-entering refresh on these
 * would create an infinite loop (R-W6-11(e)).
 *
 * NOTE: /api/v1/auth/me is NOT in this list because a 401 from /me IS recoverable via
 * a token refresh (if the access token expired between bootstrap and the /me call).
 * In practice /me is called immediately after a successful refresh so this is rare,
 * but correctness requires we handle it.
 */
const SKIP_REFRESH_PATHS = [
  '/api/v1/auth/otp/send',
  '/api/v1/auth/otp/verify',
  '/api/v1/auth/refresh',
  '/api/v1/auth/logout',
];

export const refreshInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip the four cookie-auth / public paths — a 401 here must NOT re-enter refresh
  if (SKIP_REFRESH_PATHS.some((path) => req.url.includes(path))) {
    return next(req);
  }

  const auth    = inject(AuthService);
  const authApi = inject(AuthApiService);
  const router  = inject(Router);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401) {
        return handle401(req, next, auth, authApi, router);
      }
      return throwError(() => err);
    }),
  );
};
