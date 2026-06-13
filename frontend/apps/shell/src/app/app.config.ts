import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideAppInitializer,
  inject,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
// F-001: barrel import — Native Federation maps only the root @mesell/ui-kit key
// in the import map; subpath imports resolve at compile time but not at runtime.
import { provideMeeUi } from '@mesell/ui-kit';

import {
  jwtInterceptor,
  refreshInterceptor,
  errorInterceptor,
  AuthService,
} from '@mesell/core';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideAnimationsAsync(),
    // Wave 6 Wave A — interceptor chain: jwt → refresh → error (FE-D5 split-token).
    // jwtInterceptor: attaches Bearer on non-/auth/* requests.
    // refreshInterceptor: single-flight 401→refresh→retry.
    // errorInterceptor: types the 4-field error envelope → pushes to ErrorService.
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]),
    ),
    // Bootstrap: page-reload token survival via HttpOnly refresh cookie (FE-D5).
    // Calls POST /auth/refresh on app init; on success hydrates AuthService (in-memory).
    // On 401 (no/expired cookie) — stays logged-out, NEVER rejects (app init must resolve).
    provideAppInitializer(() => inject(AuthService).bootstrap()),
    // PrimeNG theme + toast/confirm services, sealed behind the @mee/ui boundary.
    ...provideMeeUi(),
  ],
};
