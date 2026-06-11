import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch } from '@angular/common/http';

import { routes } from './app.routes';
// Deep import (not the barrel) so the root bundle pulls only the PrimeNG
// providers + theme, never the full set of mee-* wrappers.
import { provideMeeUi } from '@mesell/ui-kit/providers';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideAnimationsAsync(),
    // First HttpClient wiring in the codebase (Wave 6 — smart-picker HTTP port).
    // withFetch() = Fetch API backend (Angular 18+).
    // NO interceptors this slice. When global JWT interceptor ships (Wave 7):
    //   provideHttpClient(withFetch(), withInterceptors([authInterceptor]))
    provideHttpClient(withFetch()),
    // PrimeNG theme + toast/confirm services, sealed behind the @mee/ui boundary.
    ...provideMeeUi(),
  ],
};
