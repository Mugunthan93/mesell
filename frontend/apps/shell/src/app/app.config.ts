import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch } from '@angular/common/http';

import { routes } from './app.routes';
// Root barrel import — required for Native Federation: shareAll() only registers the root
// package key in the shared import map; sub-paths like @mesell/ui-kit/providers are not
// registered and cause runtime resolution failures (F-002).
import { provideMeeUi } from '@mesell/ui-kit';

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
