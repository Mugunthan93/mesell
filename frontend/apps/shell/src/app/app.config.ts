import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { routes } from './app.routes';
// Deep import (not the barrel) so the root bundle pulls only the PrimeNG
// providers + theme, never the full set of mee-* wrappers.
import { provideMeeUi } from '@mesell/ui-kit/providers';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideAnimationsAsync(),
    // PrimeNG theme + toast/confirm services, sealed behind the @mee/ui boundary.
    ...provideMeeUi(),
  ],
};
