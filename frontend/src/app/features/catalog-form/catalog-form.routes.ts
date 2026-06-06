// features/catalog-form/catalog-form.routes.ts
// Route: /catalogs/:id/edit — auth required per §23

import { Routes } from '@angular/router';

export const CATALOG_FORM_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
  },
];
