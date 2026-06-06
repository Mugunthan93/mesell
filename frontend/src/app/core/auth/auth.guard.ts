// core/auth/auth.guard.ts
// CanActivateFn — bootstraps from /auth/refresh on reload, redirects to /login on failure

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs/operators';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = (_route, _state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  // Fast path: token already in memory
  if (auth.isAuthenticated()) return true;

  // Slow path: bootstrap via /auth/refresh (browser sends HttpOnly cookie automatically)
  return auth.bootstrap().pipe(
    map(success => success ? true : router.createUrlTree(['/login'])),
  );
};
