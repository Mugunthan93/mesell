// mfe-billing — dev-serve / standalone bootstrap entry ONLY.
// In federation the BILLING_ROUTES are mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 forward rule: BILLING_ROUTES must be reachable from this main.ts so
// Native Federation's Sheriff analyzer sees all shared-lib consumers and keeps
// them in the shared[] map. provideRouter(BILLING_ROUTES) here ensures both
// plans/account components (and thus @mesell/core AuthService, @mesell/ui-kit)
// are reachable. Do NOT trim BILLING_ROUTES to a subset here.
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { PlansComponent } from './app/plans/plans.component';
import { BILLING_ROUTES } from './app/billing.routes';

import { jwtInterceptor, refreshInterceptor, errorInterceptor } from '@mesell/core';
import { provideMeeUi } from '@mesell/ui-kit';

bootstrapApplication(PlansComponent, {
  providers: [
    provideRouter(BILLING_ROUTES),
    provideAnimationsAsync(),
    // PrimeNG theme + services — mirrors shell app.config.ts (dev-serve parity)
    ...provideMeeUi(),
    // HttpClient for standalone dev-serve (pnpm start:mfe-billing).
    // In federation the shell injector provides HttpClient (proven #101 ruling).
    // Interceptor chain: jwt sets Bearer header → refresh catches 401 →
    // error surfaces envelope. Matches every other remote's main.ts chain.
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]),
    ),
  ],
}).catch((err: unknown) => console.error(err));
