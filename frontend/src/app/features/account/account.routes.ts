// features/account/account.routes.ts
// Routes: /signup, /login, /onboarding, /profile per §23 + §2.C.2

import { Routes } from '@angular/router';

export const ACCOUNT_ROUTES: Routes = [
  {
    path: 'signup',
    loadComponent: () => import('./signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'login',
    loadComponent: () => import('./login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'onboarding',
    loadComponent: () => import('./onboarding/onboarding.component').then(m => m.OnboardingWizardComponent),
  },
  {
    path: 'profile',
    loadComponent: () => import('./profile/profile.component').then(m => m.ProfileEditComponent),
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full',
  },
];
