import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * jwtInterceptor — attaches Authorization: Bearer <token> to all requests that need it.
 *
 * Skip rule (spec §3.1 — NAMED endpoints only):
 *   - POST /api/v1/auth/otp/send    — public, no token needed
 *   - POST /api/v1/auth/otp/verify  — OTP exchange, no prior token
 *   - POST /api/v1/auth/refresh     — cookie-auth, Bearer not needed/wanted
 *   - POST /api/v1/auth/logout      — cookie-auth, Bearer not needed/wanted
 *
 * NOT skipped:
 *   - GET /api/v1/auth/me           — Bearer-protected (Depends(get_current_user) in backend)
 *     The /me endpoint is the only /auth/* path that NEEDS a Bearer token.
 *
 * Prior implementation used a broad /api/v1/auth/* prefix skip which incorrectly
 * excluded /auth/me — causing 401 on /me in production (bootstrap + silent refresh flow).
 * Fixed to use explicit path matching per the spec's named list.
 *
 * Chain position: FIRST (jwt → refresh → error).
 * FE-D5: token is held in-memory by AuthService._token signal (never localStorage).
 */

/** Endpoints that must NOT receive a Bearer header (public or cookie-auth paths). */
const SKIP_BEARER_PATHS = [
  '/api/v1/auth/otp/send',
  '/api/v1/auth/otp/verify',
  '/api/v1/auth/refresh',
  '/api/v1/auth/logout',
];

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip the four explicitly named endpoints that don't want/need Bearer.
  // NOTE: /api/v1/auth/me is NOT in this list — it is Bearer-protected on the backend.
  if (SKIP_BEARER_PATHS.some((path) => req.url.includes(path))) {
    return next(req);
  }

  const token = inject(AuthService).getToken();
  if (!token) {
    return next(req);
  }

  return next(
    req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }),
  );
};
