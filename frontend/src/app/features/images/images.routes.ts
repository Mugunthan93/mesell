// features/images/images.routes.ts
// Route: /catalogs/:id/images — auth required per §23
// ImagesApiService provided here so it tree-shakes with this route chunk.

import { Routes } from '@angular/router';
import { ImagesApiService } from './images-api.service';

export const IMAGES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./images/images.component').then(m => m.ImagesComponent),
    providers: [ImagesApiService],
  },
];
