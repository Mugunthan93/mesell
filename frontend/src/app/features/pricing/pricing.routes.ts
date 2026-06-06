// features/pricing/pricing.routes.ts
// Route: /catalogs/:id/pricing — auth required per §23

import { Routes } from '@angular/router';

export const PRICING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pricing/pricing.component').then(m => m.PricingComponent),
  },
];
