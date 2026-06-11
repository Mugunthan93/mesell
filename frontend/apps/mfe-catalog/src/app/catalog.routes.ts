// mfe-catalog — the remote-owned Routes array. The ONLY federation expose
// (./CatalogRoutes). Internalises all 5 funnel route targets so the shell mounts
// the whole catalog sub-tree with ONE loadChildren (D31). Route order: 'new' MUST
// precede ':id/edit' so the literal 'new' is not captured as an :id (R-SP5-2).
// The :id/edit route carries providers:[CatalogFormApiService] — the route-scoped
// service preserved EXACTLY from the subsumed catalog-form.routes.ts (D32/D34).
import { Routes } from '@angular/router';
import { CatalogFormApiService } from './catalog-form/services/catalog-form-api.service';

export const CATALOG_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./catalog-list.component').then(m => m.CatalogListComponent),
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./catalog-new/catalog-new.component').then(m => m.CatalogNewComponent),
  },
  {
    path: ':id/edit',
    loadComponent: () =>
      import('./catalog-form/catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
    providers: [CatalogFormApiService],
  },
  {
    path: ':id/images',
    loadComponent: () =>
      import('./images/image-uploader/image-uploader.component').then(m => m.ImageUploaderComponent),
  },
  {
    path: ':id/preview',
    loadComponent: () =>
      import('./preview/preview/preview.component').then(m => m.PreviewComponent),
  },
];
