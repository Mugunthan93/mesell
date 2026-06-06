// features/dashboard/dashboard.routes.ts
// Route: /dashboard — auth required per §23
// DashboardApiService is provided here (feature-scoped, NOT providedIn: 'root' per §3.D)

import { Routes } from '@angular/router';
import { DashboardApiService } from './dashboard-api.service';

export const DASHBOARD_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
    providers: [DashboardApiService],
  },
];
