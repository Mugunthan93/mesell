import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * jwtInterceptor — attaches Authorization: Bearer <token> to all non-auth requests.
 *
 * Skip rule: requests to /api/v1/auth/* (send/verify/refresh/logout) must NOT carry
 * a stale Bearer. Those endpoints are public (send/verify) or cookie-auth (refresh/logout).
 * An explicit URL-pattern skip is safer than relying on the token being null pre-login.
 *
 * Chain position: FIRST (jwt → refresh → error).
 * FE-D5: token is held in-memory by AuthService._token signal (never localStorage).
 */
export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip auth-namespace routes — they use cookie credentials (withCredentials)
  // or are public (OTP send). A stale Bearer here is incorrect and rejected by the backend.
  if (req.url.includes('/api/v1/auth/')) {
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
