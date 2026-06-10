// features/catalog-form/catalog-form.routes.ts
// Route: /catalogs/:id/edit — mounted via loadChildren in app.routes.ts
// Wave 5 — F8: Catalog Form page
// CatalogFormApiService is @Injectable() with no providedIn — scoped to this route.

import { Routes } from '@angular/router';
import { CatalogFormApiService } from './services/catalog-form-api.service';

export const CATALOG_FORM_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
    providers: [CatalogFormApiService],
  },
];
