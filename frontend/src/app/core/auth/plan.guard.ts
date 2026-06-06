// core/auth/plan.guard.ts
// Wired-but-inert in V1 — no route uses planGuard('pro') yet.
// V1.5 adds canActivate: [planGuard('pro')] lines for bulk-ops, advanced exports.

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { ErrorService } from '@core/services/error.service';
import { PlanTier } from '@shared/enums/plan-tier.enum';

export const planGuard = (requiredPlan: PlanTier): CanActivateFn =>
  (_route, _state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const error = inject(ErrorService);

    if (!auth.plan()) return router.createUrlTree(['/login']);
    if (auth.plan() === 'pro' || requiredPlan === 'free') return true;

    error.showInfo('This feature is available on the Pro plan.');
    return router.createUrlTree(['/dashboard']);
  };
