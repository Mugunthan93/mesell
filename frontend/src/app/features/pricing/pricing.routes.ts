// features/pricing/pricing.routes.ts
// Route: /catalogs/:id/pricing — auth required per §23

import { Routes } from '@angular/router';
import { PricingApiService } from './pricing-api.service';

export const PRICING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pricing/pricing.component').then(m => m.PricingComponent),
    providers: [PricingApiService],
  },
];
