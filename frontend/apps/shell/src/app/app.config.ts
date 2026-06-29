import { ApplicationConfig, ErrorHandler, provideBrowserGlobalErrorListeners, provideAppInitializer, inject } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
// Root barrel import — required for Native Federation: shareAll() only registers the root
// package key in the shared import map; sub-paths like @mesell/ui-kit/providers are not
// registered and cause runtime resolution failures (F-002).
import { provideMeeUi } from '@mesell/ui-kit';
import {
  AuthService,
  GlobalErrorHandler,
  jwtInterceptor,
  retryInterceptor,
  refreshInterceptor,
  errorInterceptor,
} from '@mesell/core';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Global JS error → ErrorService normalisation (uncaught errors from zone.js path).
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    // P0 reload-survival (FE-D5): rehydrate the in-memory access token from the
    // HttpOnly refresh cookie BEFORE the router/authGuard evaluate. bootstrap()
    // resolves (never rejects) on a 401/no-cookie, so an unauthenticated first
    // visit still boots gracefully to /login. Routes through the same
    // refreshShared() single-flight as the interceptor — no refresh stampede.
    provideAppInitializer(() => inject(AuthService).bootstrap()),
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(
      withFetch(),
      // Chain order is load-bearing:
      //   jwt sets the Bearer header
      //   → retry backs off on network failures (status 0) + idempotent 5xx (GET/HEAD/OPTIONS/PUT)
      //   → refresh catches 401 and retries via the single-flight refreshShared() gate
      //   → error surfaces the envelope.
      // Mirrors every remote's main.ts.
      withInterceptors([jwtInterceptor, retryInterceptor, refreshInterceptor, errorInterceptor]),
    ),
    // PrimeNG theme + toast/confirm services, sealed behind the @mee/ui boundary.
    ...provideMeeUi(),
  ],
};
