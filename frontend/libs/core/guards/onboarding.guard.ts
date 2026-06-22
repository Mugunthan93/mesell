import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const onboardingGuard: CanActivateFn = () => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  // STRICT === false ONLY. undefined/null/true (legacy + Google users, and completed users) pass through.
  if (auth.currentUser()?.onboarding_complete === false) {
    return router.createUrlTree(['/onboarding']);
  }
  return true;
};
