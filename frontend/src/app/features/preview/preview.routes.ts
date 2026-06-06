// features/preview/preview.routes.ts
// Route: /catalogs/:id/preview — auth required per §23

import { Routes } from '@angular/router';

export const PREVIEW_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./preview/preview.component').then(m => m.PreviewComponent),
  },
];
