import { Routes } from '@angular/router';
import { authGuard } from '@mesell/core';

import { loadRemoteWithFallback, loadRemoteRoutesWithFallback } from './core/load-remote';

export const routes: Routes = [
  // MF Sub-Plan 04 — mfe-dashboard remote (apps/mfe-dashboard/). The PUBLIC landing
  // page now lives in the `mfe-dashboard` Native-Federation remote, loaded at runtime
  // via the manifest. NO authGuard (public, pre-auth); pathMatch:'full' preserved so it
  // matches ONLY the empty path. D12 fallback on load failure. The remoteEntry is a
  // static public asset — fetched with no Authorization header (D27/D29).
  {
    path: '',
    loadComponent: loadRemoteWithFallback('mfe-dashboard', './LandingComponent'),
    pathMatch: 'full',
  },

  // MF Sub-Plan 06 — mfe-auth remote (apps/mfe-auth/). The THREE auth pages (login,
  // signup, otp-verify) now live in one Native-Federation remote exposing THREE
  // components, loaded at runtime via the manifest. ALL THREE are PUBLIC top-level
  // routes — NO authGuard (reached pre-authentication, D37). otp-verify is the only
  // flow that WRITES the shell's auth state: its setSession() mutates the shared
  // @mesell/core AuthService singleton across the boundary (the C4 WRITE path, D38).
  // D12 fallback on remote-load failure. The '**' -> 'login' wildcard below now
  // resolves to this remote LoginComponent.
  {
    path: 'login',
    loadComponent: loadRemoteWithFallback('mfe-auth', './LoginComponent'),
  },
  {
    path: 'signup',
    loadComponent: loadRemoteWithFallback('mfe-auth', './SignupComponent'),
  },
  {
    path: 'otp-verify',
    loadComponent: loadRemoteWithFallback('mfe-auth', './OtpVerifyComponent'),
  },

  // Protected area — Shell layout (single empty-path parent, no ambiguity)
  {
    path: '',
    loadComponent: () =>
      import('./layouts/shell/shell.component').then(m => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      {
        // MF Sub-Plan 04 — mfe-dashboard remote (apps/mfe-dashboard/). The dashboard
        // page now lives in the `mfe-dashboard` Native-Federation remote, loaded at
        // runtime via the manifest. The parent's authGuard (canActivate on the shell
        // empty-path parent) UNCHANGED — the guard runs in the SHELL before the remote
        // is fetched (D27): an unauthenticated visitor is redirected to /login WITHOUT
        // downloading the dashboard remoteEntry. The remote does NOT self-guard and does
        // NOT inject AuthService. D12 fallback on load failure.
        path: 'dashboard',
        loadComponent: loadRemoteWithFallback('mfe-dashboard', './DashboardComponent'),
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
