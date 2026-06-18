// mfe-catalog — the remote-owned Routes array. The ONLY federation expose
// (./CatalogRoutes). Internalises all catalog route targets so the shell mounts
// the whole catalog sub-tree with ONE loadChildren (D31). Route order matters:
//   - Literal paths ('new', 'live') MUST precede ':id/*' patterns (R-SP5-2).
// The :id/edit route carries providers:[CatalogFormApiService] — the route-scoped
// service preserved EXACTLY from the subsumed catalog-form.routes.ts (D32/D34).
import { Routes } from '@angular/router';
import { CatalogFormApiService } from './catalog-form/services/catalog-form-api.service';
import { CatalogListApiService } from './catalog-list-api.service';

export const CATALOG_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./catalog-list.component').then(m => m.CatalogListComponent),
    providers: [CatalogListApiService],
  },
  {
    // /catalogs/new -> SmartPickerComponent (renamed from CatalogNewComponent per D4)
    path: 'new',
    loadComponent: () =>
      import('./smart-picker/smart-picker.component').then(m => m.SmartPickerComponent),
  },
  {
    // /catalogs/live -> LiveListingsComponent — literal BEFORE ':id/*' to avoid capture
    path: 'live',
    loadComponent: () =>
      import('./live-listings/live-listings.component').then(m => m.LiveListingsComponent),
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
];
