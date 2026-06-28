// mfe-billing — dev-serve / standalone bootstrap entry ONLY.
// In federation the BILLING_ROUTES are mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 forward rule: BILLING_ROUTES must be reachable from this main.ts so
// Native Federation's Sheriff analyzer sees all shared-lib consumers and keeps
// them in the shared[] map. provideRouter(BILLING_ROUTES) here ensures both
// plans/account components (and thus @mesell/core AuthService, @mesell/ui-kit)
// are reachable. Do NOT trim BILLING_ROUTES to a subset here.
import { ErrorHandler, provideBrowserGlobalErrorListeners } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { PlansComponent } from './app/plans/plans.component';
import { BILLING_ROUTES } from './app/billing.routes';

import {
  GlobalErrorHandler,
  jwtInterceptor,
  retryInterceptor,
  refreshInterceptor,
  errorInterceptor,
} from '@mesell/core';
import { provideMeeUi } from '@mesell/ui-kit';

bootstrapApplication(PlansComponent, {
  providers: [
    provideBrowserGlobalErrorListeners(),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    provideRouter(BILLING_ROUTES),
    provideAnimationsAsync(),
    // PrimeNG theme + services — mirrors shell app.config.ts (dev-serve parity)
    ...provideMeeUi(),
    // HttpClient for standalone dev-serve (pnpm start:mfe-billing).
    // In federation the shell injector provides HttpClient (proven #101 ruling).
    // Chain: jwt sets Bearer → retry backs off on network/5xx → refresh handles 401 → error records.
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor, retryInterceptor, refreshInterceptor, errorInterceptor]),
    ),
  ],
}).catch((err: unknown) => console.error(err));
