// features/images/images.routes.ts
// Route: /catalogs/:id/images — auth required per §23

import { Routes } from '@angular/router';

export const IMAGES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./images/images.component').then(m => m.ImageUploaderComponent),
  },
];
