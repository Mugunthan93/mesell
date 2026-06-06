// core/interceptors/jwt.interceptor.ts
// Interceptor #1 in chain — attaches Authorization: Bearer per §4.B.1

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '@core/auth/auth.service';

/** URL segments that do NOT need a Bearer token */
const SKIP_PATTERNS = ['/auth/otp/', '/auth/refresh', '/auth/logout'];

function shouldSkip(url: string): boolean {
  return SKIP_PATTERNS.some(pattern => url.includes(pattern));
}

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  if (shouldSkip(req.url)) {
    return next(req);
  }

  const token = inject(AuthService).accessToken();
  if (!token) {
    // No token — pass through; downstream 401 handled by RefreshInterceptor
    return next(req);
  }

  return next(req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  }));
};
