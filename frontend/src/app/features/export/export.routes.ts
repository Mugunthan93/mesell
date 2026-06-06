// features/export/export.routes.ts
// Route: /catalogs/:id/export — auth required per §23

import { Routes } from '@angular/router';

export const EXPORT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./export/export.component').then(m => m.ExportComponent),
  },
];
