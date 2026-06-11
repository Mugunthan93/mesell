import type { Provider, EnvironmentProviders } from '@angular/core';
import { providePrimeNG } from 'primeng/config';
import { MessageService, ConfirmationService } from 'primeng/api';
import { MeeSellPreset } from './theme';

/**
 * Single root-bootstrap entry point for the MeeSell UI kit (Layer 2).
 *
 * Bundles every PrimeNG root provider — the configured theme (MeeSell preset),
 * the toast `MessageService`, and the confirm `ConfirmationService` that
 * `MeeToastService` / `MeeConfirmService` wrap. This keeps `app.config.ts` free
 * of any direct `primeng` import: the bootstrap surface lives behind `@mee/ui`
 * like every other PrimeNG dependency.
 */
export function provideMeeUi(): (Provider | EnvironmentProviders)[] {
  return [
    MessageService,
    ConfirmationService,
    providePrimeNG({
      theme: {
        preset: MeeSellPreset,
        options: {
          prefix: 'p',
          darkModeSelector: '.dark',
          cssLayer: {
            name: 'primeng',
            order: 'theme, base, primeng, components, utilities',
          },
        },
      },
      ripple: true,
    }),
  ];
}
