// features/smart-picker/smart-picker.routes.ts
// Route: /catalogs/new — lazy-loaded, scoped providers per AC-7 + §3.D
// Services provided here are tree-shaken with the route chunk (NOT in root).

import { Routes } from '@angular/router';
import { SmartPickerApiService } from './smart-picker-api.service';
import { SmartPickerStateService } from './smart-picker-state.service';

export const SMART_PICKER_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./smart-picker/smart-picker.component').then(
        (m) => m.SmartPickerComponent,
      ),
    providers: [SmartPickerApiService, SmartPickerStateService],
  },
];
