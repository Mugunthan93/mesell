// app.config.ts — ApplicationConfig per §4.B + §4.H + §16
// Interceptor registration order is LOAD-BEARING: Jwt → Locale → Refresh → Error

import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideServiceWorker } from '@angular/service-worker';
import { provideTransloco, TranslocoLoader } from '@jsverse/transloco';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { routes } from './app.routes';
import { environment } from '../environments/environment';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';
import { ENV_CONFIG } from '@core/tokens/env-config.token';

// Interceptors — ORDER IS LOAD-BEARING (per §4.B)
import { jwtInterceptor } from '@core/interceptors/jwt.interceptor';
import { localeInterceptor } from '@core/interceptors/locale.interceptor';
import { refreshInterceptor } from '@core/interceptors/refresh.interceptor';
import { errorInterceptor } from '@core/interceptors/error.interceptor';

@Injectable({ providedIn: 'root' })
export class TranslocoHttpLoader implements TranslocoLoader {
  private readonly http = inject(HttpClient);

  getTranslation(lang: string): Observable<Record<string, string>> {
    return this.http.get<Record<string, string>>(`/assets/i18n/${lang}.json`);
  }
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),

    // Router with lazy loadChildren per §23
    provideRouter(routes, withComponentInputBinding()),

    // HttpClient with 4-interceptor chain in canonical order
    provideHttpClient(
      withInterceptors([
        jwtInterceptor,       // 1. Attach Authorization: Bearer
        localeInterceptor,    // 2. Attach Accept-Language
        refreshInterceptor,   // 3. Catch 401, refresh, replay
        errorInterceptor,     // 4. Normalize 4xx/5xx → ApiError, snackbar surface
      ]),
    ),

    // Angular Material animations (async for initial bundle performance)
    provideAnimationsAsync(),

    // PWA Service Worker per §16
    provideServiceWorker('ngsw-worker.js', {
      enabled: environment.serviceWorkerEnabled,
      registrationStrategy: 'registerWhenStable:30000',
    }),

    // Transloco i18n per §6 pick #3
    provideTransloco({
      config: {
        availableLangs: ['en', 'ta', 'hi'],
        defaultLang: environment.defaultLocale,
        reRenderOnLangChange: true,
        prodMode: environment.production,
      },
      loader: TranslocoHttpLoader,
    }),

    // InjectionTokens per §4.H
    { provide: API_BASE_URL, useValue: environment.apiBaseUrl },
    { provide: ENV_CONFIG, useValue: environment },
  ],
};
