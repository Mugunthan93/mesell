import {
  HttpErrorResponse,
  HttpEvent,
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import {
  Observable,
  throwError,
  switchMap,
  catchError,
} from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * refreshInterceptor — single-flight 401=>refresh=>retry.
 *
 * Chain position: SECOND (jwt => refresh => error).
 *
 * Behaviour on 401 from a NON-/auth/* request:
 *   1. Delegates to AuthService.refreshForced() — bypasses the B03 cross-context
 *      debounce so a genuine 401 ALWAYS hits the network. (refreshShared() would
 *      return a cached token on the 2s debounce window, causing another 401.)
 *   2. refreshForced() still shares _refreshInFlight with refreshShared() so
 *      concurrent 401s from multiple requests produce exactly ONE POST /auth/refresh
 *      (stampede fix intact).
 *   3. On refresh-200 => retry original request with the new Bearer token.
 *   4. On refresh-401 => auth.forceLogout() (logout-once guard: navigate to /login
 *      exactly once regardless of how many 401s are cascading) + rethrow error.
 *
 * REMOVED (state hoisted to AuthService — D-A/D-B fixed by construction):
 *   - module-level _isRefreshing flag (was never reset after success — D-A)
 *   - module-level _refreshToken$ BehaviorSubject (was never reset on logout — D-B)
 *
 * Previously those were acceptable only because the interceptor was the sole caller
 * of refresh(). Now that bootstrap() and _doSilentRefresh() are also callers, the
 * gate must live in the shared singleton (AuthService) to be effective across all paths.
 *
 * Loop prevention (R-W6-11(e)):
 *   SKIP_REFRESH_PATHS are not retried on 401 — these are cookie-auth or public
 *   endpoints where a 401 means a genuinely invalid credential, not a stale token.
 *   jwtInterceptor also skips these paths (belt+suspenders).
 *
 * NO change to:
 *   - auth-api.service.ts (no HTTP calls added/removed)
 *   - jwt.interceptor.ts (skip-path lists + bearer logic unchanged)
 *   - SKIP_BEARER_PATHS / SKIP_REFRESH_PATHS lists
 */

function addBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * handle401 — thin: delegates to AuthService.refreshForced() (bypass-debounce gate).
 * Late concurrent 401s join the in-flight Subject Observable and all retry once
 * the one refresh completes. No module-level state lives here.
 *
 * Uses refreshForced() (not refreshShared()) because a 401 proves the server
 * has already rejected the current token — the B03 debounce must be bypassed or
 * the retry would use the same rejected token and immediately 401 again.
 */
function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  auth: AuthService,
): Observable<HttpEvent<unknown>> {
  return auth.refreshForced().pipe(
    switchMap((resp) => next(addBearer(req, resp.access_token))),
    catchError((err: unknown) => {
      // Refresh itself failed (401 from /auth/refresh — rotated/revoked cookie).
      // forceLogout() is a logout-once guard: navigate to /login exactly once,
      // no matter how many concurrent 401s call this path.
      auth.forceLogout();
      return throwError(() => err);
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

  const auth = inject(AuthService);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401) {
        return handle401(req, next, auth);
      }
      return throwError(() => err);
    }),
  );
};
