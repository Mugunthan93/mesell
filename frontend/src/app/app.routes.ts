import { Routes } from '@angular/router';
import { authGuard } from '@mesell/core';

import { loadRemoteWithFallback } from './core/load-remote';

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
        path: 'catalogs',
        loadComponent: () =>
          import('./features/catalogs/catalog-list.component').then(m => m.CatalogListComponent),
      },
      {
        path: 'catalogs/new',
        loadComponent: () =>
          import('./features/catalog-new/catalog-new.component').then(m => m.CatalogNewComponent),
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
        path: 'catalogs/:id/edit',
        loadChildren: () =>
          import('./features/catalog-form/catalog-form.routes')
            .then(m => m.CATALOG_FORM_ROUTES),
      },
      {
        path: 'catalogs/:id/images',
        loadComponent: () =>
          import('./features/images/image-uploader/image-uploader.component')
            .then(m => m.ImageUploaderComponent),
      },
      {
        path: 'catalogs/:id/preview',
        loadComponent: () =>
          import('./features/preview/preview/preview.component')
            .then(m => m.PreviewComponent),
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
        path: 'catalogs/:id/export',
        loadComponent: () =>
          import('./features/export/export/export.component')
            .then(m => m.ExportComponent),
      },
    ],
  },

  { path: '**', redirectTo: 'login' },
];
