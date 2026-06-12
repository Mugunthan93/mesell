// mfe-pricing — dev-serve / standalone bootstrap entry ONLY.
// In federation the component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation
// (the §9.A "remote loads in shell" test serves this remote on its own port).
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { PricingComponent } from './app/pricing.component';

import { jwtInterceptor, refreshInterceptor, errorInterceptor } from '@mesell/core';

bootstrapApplication(PricingComponent, {
  providers: [
    provideRouter([]),
    provideAnimationsAsync(),
    // Wave 6 Wave A: interceptor chain for dev-serve standalone parity.
    // In federated mode the shell injector provides HttpClient (proven #101 ruling).
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]),
    ),
  ],
}).catch((err) => console.error(err));
