import { Routes } from '@angular/router';
import { authGuard } from '@mesell/core';

import { loadRemoteWithFallback, loadRemoteRoutesWithFallback } from './core/load-remote';

export const routes: Routes = [
  // Root — public landing page
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then(m => m.LandingComponent),
    pathMatch: 'full',
  },

  // Auth pages — top-level routes (each page wraps itself in AuthLayoutComponent)
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./features/auth/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'otp-verify',
    loadComponent: () =>
      import('./features/auth/otp-verify/otp-verify.component').then(m => m.OtpVerifyComponent),
  },

  // Protected area — Shell layout (single empty-path parent, no ambiguity)
  {
    path: '',
    loadComponent: () =>
      import('./layouts/shell/shell.component').then(m => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
      {
        // MF Sub-Plan 05 — mfe-catalog remote (apps/mfe-catalog/). The 5-page catalog
        // funnel (list, new/smart-picker, :id/edit, :id/images, :id/preview) now lives in
        // one Native-Federation remote exposing a Routes ARRAY (./CatalogRoutes) — the
        // FIRST routes-expose (D31). The shell collapses its 5 separate catalogs* children
        // into this ONE loadChildren (the strangler-fig win). The :id param flows through
        // the shell outlet into the remote routes unchanged. CatalogFormApiService stays
        // route-scoped inside the remote's catalog.routes.ts (D32). D12 fallback degrades
        // the whole sub-tree to RemoteFailureComponent on remote-load failure.
        path: 'catalogs',
        loadChildren: loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes'),
      },
      {
        // MF Sub-Plan 03 — mfe-onboarding remote (apps/mfe-onboarding/). Profile +
        // onboarding now live in one Native-Federation remote exposing TWO components
        // (./ProfileComponent + ./OnboardingComponent). Loaded at runtime via the
        // manifest; D12 fallback on load failure. ProfileComponent injects the shared
        // AuthService singleton (@mesell/core) across the boundary — see D22 C1–C5.
        path: 'profile',
        loadComponent: loadRemoteWithFallback('mfe-onboarding', './ProfileComponent'),
      },
      {
        path: 'onboarding',
        loadComponent: loadRemoteWithFallback('mfe-onboarding', './OnboardingComponent'),
      },
      {
        // MF Sub-Plan 01 — first federated remote. Pricing now lives in the
        // `mfe-pricing` Native-Federation remote (apps/mfe-pricing/), loaded at
        // runtime via the manifest. The :id param flows through the shell router
        // outlet into the remote component unchanged. D12 fallback on load failure.
        path: 'catalogs/:id/pricing',
        loadComponent: loadRemoteWithFallback('mfe-pricing', './PricingComponent'),
      },
      {
        // MF Sub-Plan 02 — second federated remote. Export now lives in the
        // `mfe-export` Native-Federation remote (apps/mfe-export/), loaded at
        // runtime via the manifest. The :id param flows through the shell router
        // outlet into the remote component unchanged. The OnDestroy job-polling
        // timer is destroyed when the host unmounts the remote on navigate-away
        // (D18 — boundary does not alter lifecycle). D12 fallback on load failure.
        path: 'catalogs/:id/export',
        loadComponent: loadRemoteWithFallback('mfe-export', './ExportComponent'),
      },
    ],
  },

  { path: '**', redirectTo: 'login' },
];
