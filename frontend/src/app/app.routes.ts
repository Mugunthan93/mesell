// app.routes.ts — Top-level route table.
// AMENDMENT 2026-06-06 (Phase 2 app shell): Restructured into two layout groups.
// Auth layout (no sidebar): /, /signup, /login, /onboarding
// Shell layout (dark sidebar, authGuard): /dashboard, /catalogs/*, /profile
// Playground: flat route, no layout wrapper.

import { Routes } from '@angular/router';
import { authGuard } from '@core/auth/auth.guard';
import { MeeAuthLayoutComponent } from './layouts/auth/auth-layout.component';
import { MeeShellComponent } from './layouts/shell/shell.component';

export const routes: Routes = [
  // ── AUTH LAYOUT (no sidebar, centered card) ──────────────────────────
  // Mounts MeeAuthLayoutComponent as layout; children render inside the card.
  {
    path: '',
    component: MeeAuthLayoutComponent,
    children: [
      // Route 1 — Landing — /
      {
        path: '',
        loadChildren: () =>
          import('./features/landing/landing.routes').then(m => m.LANDING_ROUTES),
      },

      // Route 2 — Signup — /signup
      // Route 3 — Login  — /login
      // Route 4 — Onboarding — /onboarding (auth-guarded; served in auth layout before profile)
      // ACCOUNT_ROUTES internally defines path: 'signup' | 'login' | 'onboarding' | 'profile'
      // Mounting at path: '' so those relative paths resolve correctly.
      {
        path: '',
        loadChildren: () =>
          import('./features/account/account.routes').then(m => m.ACCOUNT_ROUTES),
      },
    ],
  },

  // ── SHELL LAYOUT (dark sidebar, all authenticated routes) ─────────────
  {
    path: '',
    component: MeeShellComponent,
    // canActivate: [authGuard], // TEMP: disabled for dev preview
    children: [
      // Route 5 — Dashboard — /dashboard
      {
        path: 'dashboard',
        loadChildren: () =>
          import('./features/dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES),
      },

      // Route 6 — Smart Picker — /catalogs/new
      {
        path: 'catalogs/new',
        loadChildren: () =>
          import('./features/smart-picker/smart-picker.routes').then(m => m.SMART_PICKER_ROUTES),
      },

      // Routes 7-10 — Catalog sub-routes
      {
        path: 'catalogs/:id/edit',
        loadChildren: () =>
          import('./features/catalog-form/catalog-form.routes').then(m => m.CATALOG_FORM_ROUTES),
      },
      {
        path: 'catalogs/:id/images',
        loadChildren: () =>
          import('./features/images/images.routes').then(m => m.IMAGES_ROUTES),
      },
      {
        path: 'catalogs/:id/preview',
        loadChildren: () =>
          import('./features/preview/preview.routes').then(m => m.PREVIEW_ROUTES),
      },
      {
        path: 'catalogs/:id/pricing',
        loadChildren: () =>
          import('./features/pricing/pricing.routes').then(m => m.PRICING_ROUTES),
      },

      // Route 11 — Export
      {
        path: 'catalogs/:id/export',
        loadChildren: () =>
          import('./features/export/export.routes').then(m => m.EXPORT_ROUTES),
      },

      // Route 12 — Profile — /profile
      {
        path: 'profile',
        loadChildren: () =>
          import('./features/account/account.routes').then(m => m.ACCOUNT_ROUTES),
      },
    ],
  },

  // ── Design System Playground — flat route, no layout, dev tool only ──
  {
    path: 'playground',
    loadComponent: () =>
      import('./playground/playground.component').then(m => m.PlaygroundComponent),
  },

  // Wildcard redirect — must be LAST
  {
    path: '**',
    redirectTo: '',
  },
];
