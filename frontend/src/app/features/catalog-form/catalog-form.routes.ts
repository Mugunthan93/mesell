// features/catalog-form/catalog-form.routes.ts
// Route: /catalogs/:id/edit — auth required per §23.
// Parent (app.routes.ts) mounts this at path: 'catalogs/:id/edit' via loadChildren.
// This file therefore uses path: '' for the single child route.
//
// providers[] lists all 5 feature-scoped services so they:
//   (a) are NOT providedIn: 'root' (no global singleton)
//   (b) are tree-shaken with the lazy chunk when not on this route
//   (c) get a fresh instance per route activation (relevant for CatalogFormStateService)

import { Routes } from '@angular/router';
import { CatalogFormApiService } from './catalog-form-api.service';
import { DraftRecoveryService } from './draft-recovery.service';
import { CategorySchemaService } from './category-schema.service';
import { EnumLookupService } from './enum-lookup.service';
import { CatalogFormStateService } from './catalog-form-state.service';

export const CATALOG_FORM_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
    providers: [
      CatalogFormApiService,
      DraftRecoveryService,
      CategorySchemaService,
      EnumLookupService,
      CatalogFormStateService,
    ],
  },
];
