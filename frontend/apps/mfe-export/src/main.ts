// mfe-export — dev-serve / standalone bootstrap entry ONLY.
// In federation the component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation
// (the "remote loads in shell" test serves this remote on its own port).
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { ExportComponent } from './app/export.component';

bootstrapApplication(ExportComponent, {
  providers: [
    provideRouter([]),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));
